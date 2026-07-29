"""routes/rollback.py — TSK-613 (ADR-003): blueprint تاريخ التراجع ومعاينته.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from typing import Any
from flask import Blueprint, jsonify, request
import pathlib

bp = Blueprint("rollback", __name__)
_srv: Any = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/rollback/history")
def api_rollback_history():
    """T-066 (R-902): تاريخ الـ runs المُطبَّقة من مخزن checkpoints نفسه
    (T-054) — قراءة فقط؛ التنفيذ يبقى عبر أمرَي rollback_run/rollback_file
    على الـ WS. كل مدخل يحمل ملفاته + أعلام صلاحية الاستعادة:
    الـ runs المُقلَّمة بالـ retention تختفي تلقائيًا (المصدر هو السجل)."""
    if _srv.chain_bridge is None:
        return jsonify({"ok": False, "error": "chain bridge غير مهيأ بعد",
                        "runs": []}), 503
    mgr = _srv.chain_bridge.checkpoint_manager
    return jsonify({"ok": True, "runs": mgr.run_summaries()})


@bp.route("/api/rollback/preview")
def api_rollback_preview():
    """T-066 (R-902): نص snapshot ما-قبل-الكتابة لملف داخل run — لعرض
    diff تأكيد الاستعادة (الحالي على القرص → الـ snapshot) في لوحة T-065.
    absent=true يعني الملف أنشأه الـ run (الاستعادة تحذفه)."""
    run_id = request.args.get("run_id", "").strip()
    path = request.args.get("path", "").strip()
    if not run_id or not path:
        return jsonify({"ok": False, "error": "run_id وpath مطلوبان"}), 400
    if _srv.chain_bridge is None:
        return jsonify({"ok": False, "error": "chain bridge غير مهيأ بعد"}), 503
    mgr = _srv.chain_bridge.checkpoint_manager
    entry = next((e for e in mgr.entries_for_run(run_id)
                  if e.path == str(pathlib.Path(path).resolve())), None)
    if entry is None:
        return jsonify({"ok": False,
                        "error": f"لا snapshot لهذا الملف في {run_id}"}), 404
    text = mgr.snapshot_text(run_id, path)
    return jsonify({"ok": True, "run_id": run_id, "path": path,
                    "absent": entry.sha256 is None,
                    "snapshot": text if text is not None else ""})
