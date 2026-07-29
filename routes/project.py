"""routes/project.py — TSK-613 (ADR-003): blueprint تبديل المشروع.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from typing import Any
from flask import Blueprint, jsonify, request
import os

from actions.file_manager import FileManager
from actions.command_runner import CommandRunner

bp = Blueprint("project", __name__)
_srv: Any = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/switch-project", methods=["POST"])
def api_switch_project():
    """تغيير مسار المشروع"""

    # ── حماية: منع التبديل أثناء run نشط (R-101 → R-105) ──
    _active_runs = _srv.execution_registry.list_active()
    if _active_runs:
        return jsonify({
            "ok": False,
            "error": "لا يمكن تغيير المشروع أثناء تشغيل run نشط",
            "chain_run_id": _active_runs[0].run_id
        }), 409

    data = request.get_json()
    new_path = data.get("path", "").strip()
    if not new_path:
        return jsonify({"ok": False, "error": "مسار فارغ"}), 400

    abs_path = os.path.abspath(new_path)
    if not os.path.isdir(abs_path):
        # محاولة إنشاء المجلد
        try:
            os.makedirs(abs_path, exist_ok=True)
        except Exception as e:
            return jsonify({"ok": False, "error": f"فشل إنشاء المجلد: {e}"}), 400

    # ── R-303 (T-031): فحص ربط الجلسة بالمشروع قبل التبديل ──
    # الجلسة المرتبطة ببصمة مشروع مختلف تُعالَج حسب السياسة:
    # warn (بانر سياق) / fork (جلسة جديدة مرتبطة) / block (409 رفض).
    _bind_check = None
    _bound_path = ""
    if _srv.session_mgr and getattr(_srv.session_mgr, "current_session_id", None):
        from sessions.store import check_project_binding, project_fingerprint
        try:
            _cur = _srv.session_mgr.load_session(_srv.session_mgr.current_session_id)
            _bound_path = (_cur or {}).get("project_path", "") or ""
            _bind_check = check_project_binding(
                project_fingerprint(_bound_path), abs_path,
                _srv._session_binding_policy())
        except ValueError:
            # سياسة غير معروفة في config = خطأ تهيئة — نفشل بصوت عالٍ
            raise
        except Exception:
            _bind_check = None  # جلسات قديمة/تالفة → تسامح (غير مرتبطة)
    if _bind_check is not None and _bind_check.action == "block":
        return jsonify({
            "ok": False,
            "error": "الجلسة الحالية مرتبطة بمشروع آخر — التبديل مرفوض (سياسة block)",
            "binding": {"policy": "block", "bound_project_path": _bound_path},
        }), 409

    try:
        # R-102 (T-008): the switch IS ctx.switch_project() — one atomic
        # swap; every consumer resolves the new handle at its next call.
        # Legacy globals are re-pointed at the ctx-owned objects (one-way
        # aliases) until the remaining direct readers migrate.
        if _srv.ctx is not None:
            handle = _srv.ctx.switch_project(abs_path)
            _srv.fm = handle.fm
            _srv.cmd_runner = handle.cmd_runner
        else:  # ctx-less fallback (tests / legacy boot)
            _srv.fm = FileManager(abs_path)
            _srv.cmd_runner = CommandRunner(cwd=abs_path, auto_approve=True)
        scan = _srv.fm.scan_project()

        # ── R-303 (T-031): تطبيق نتيجة فحص الربط بعد نجاح التبديل ──
        _binding_info = None
        if _bind_check is not None and _bind_check.action == "warn":
            _srv._binding_banner = (
                f"⚠️ [تنبيه ربط الجلسة]: هذه الجلسة بدأت على المشروع "
                f"{_bound_path} وتم التبديل إلى {abs_path} — "
                f"التاريخ السابق قد يخص مشروعًا آخر."
            )
            _binding_info = {"policy": "warn", "banner": _srv._binding_banner}
        elif _bind_check is not None and _bind_check.action == "fork":
            _srv.chat_history = []
            _new_sess = _srv.session_mgr.new_session(abs_path)
            _srv._binding_banner = ""
            _binding_info = {"policy": "fork",
                             "new_session_id": _new_sess["id"]}

        return jsonify({
            "ok": True,
            "binding": _binding_info,
            "project": {
                "root": str(_srv.fm.root),
                "name": _srv.fm.root.name,
                "total_files": scan["total_files"],
                "total_size_kb": scan["total_size_kb"],
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
