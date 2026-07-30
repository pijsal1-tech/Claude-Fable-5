"""routes/meta.py — TSK-613 (ADR-003): blueprint معلومات الخادم والسعة والمقاييس.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from typing import Any
from flask import Blueprint, jsonify

bp = Blueprint("meta", __name__)
_srv: Any = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/info")
def api_info():
    """معلومات المشروع والمزود"""
    scan = _srv.fm.scan_project()
    return jsonify({
        "ok": True,
        "project": {
            "root": str(_srv.fm.root),
            "name": _srv.fm.root.name,
            "total_files": scan["total_files"],
            "total_size_kb": scan["total_size_kb"],
        },
        "provider": _srv.provider.get_info() if _srv.provider else {},
        # TSK-709 (FI-01/3): الطول من المخزن القانوني — نفس المفتاح/القيمة.
        "history_length": len(_srv.conversation_state),
    })


@bp.route("/api/capacity")
def api_capacity():
    """T-038 (R-403): سعة صادقة — أرقام الـ UI مشتقة من CapacityModel
    (حالة pool + قواطع T-037 الحية)، مع أعلام estimated للتخمينات؛
    لا ثوابت حدود حسابات صلبة — كل رقم قابل للتتبع لحالة الموديل."""
    if _srv.capacity_model is None:
        return jsonify({"ok": False,
                        "error": "capacity model غير مهيأ بعد"}), 503
    return jsonify({"ok": True,
                    "capacity": _srv.capacity_model.report().to_dict()})


@bp.route("/api/metrics/runs")
def api_metrics_runs():
    """TSK-610 (PM-03 §R6): ملخّص مقاييس الـ runs — قراءة فقط.

    عدّادات + p50/p95 للمدة (كليًا ولكل mode) من سجل JSONL
    الملحق-فقط الذي يملؤه مشترك bus الرصد (RunMetricsRecorder)."""
    if _srv.run_metrics_store is None:
        return jsonify({"ok": False,
                        "error": "مخزن المقاييس غير مهيأ بعد"}), 503
    return jsonify({"ok": True, "summary": _srv.run_metrics_store.summary()})


@bp.route("/api/permissions")
def api_permissions():
    """TSK-621 (CP-5/UXF-04 §R9): سياسة الأمان الفعالة — قراءة فقط.

    glass box: يعرض القيم الحية كما تُطبَّق فعلًا (لا نسخ ثابتة):
    allowlist أوامر الـ agent (command_policy_from على config الحي)،
    SAFE/APPROVAL tools، SAFE/DANGEROUS commands، راية
    force_command_approval، وحالة ApprovalGate (mode/whitelist/timeout).
    **لا مسار كتابة** — GET بلا آثار جانبية؛ السياسة المطبَّقة لا تُمس.
    """
    from chain.agent_tools import (SAFE_TOOLS, APPROVAL_TOOLS,
                                   command_policy_from)
    from actions.command_runner import SAFE_COMMANDS, DANGEROUS_COMMANDS

    policy = command_policy_from(_srv._load_config())
    gate = _srv.approval_gate
    gate_info = None
    if gate is not None:
        gate_info = {
            "mode": gate.mode,
            "auto_whitelist": sorted(gate.auto_whitelist),
            "timeout_seconds": gate.timeout_seconds,
        }
    return jsonify({
        "ok": True,
        "permissions": {
            "command_allowlist": {
                "enforce": policy.enforce,
                "entries": dict(policy.allowlist),
                "timeout_seconds": policy.timeout_seconds,
                "output_max_chars": policy.output_max_chars,
            },
            "agent_tools": {
                "safe": sorted(SAFE_TOOLS),
                "approval": sorted(APPROVAL_TOOLS),
            },
            "terminal_commands": {
                "safe": sorted(SAFE_COMMANDS),
                "dangerous": sorted(DANGEROUS_COMMANDS),
            },
            "force_command_approval": _srv._force_command_approval(),
            "approval_gate": gate_info,
        },
    })
