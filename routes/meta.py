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
        # TSK-716 (P0-4/D-8): رقم الإصدار القانوني — إضافة مفتاح فقط
        # (core/version.py المصدر الوحيد؛ صفر تغيير في المفاتيح القائمة).
        "version": _srv.APP_VERSION,
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


@bp.route("/api/diagnostics")
def api_diagnostics():
    """TSK-721 (P1-2 / D-9): حزمة تشخيص — قراءة فقط، **مُطهَّرة**.

    الغرض: support bundle يحمّله المستخدم عند طلب مساعدة — يجيب
    «ما إصدارك؟ ما منصتك؟ هل التبعيات سليمة؟ ما حالة المزود؟» بلا
    جولات أسئلة. **عقد التطهير الصارم**: صفر أسرار/مفاتيح، صفر مسارات
    مطلقة (اسم جذر المشروع فقط — لا المسار)، معلومات المزود تقتصر على
    مفاتيح get_info الوصفية (name/model/available/initialized —
    لا config خام). GET بلا آثار جانبية.
    """
    import importlib.util
    import platform as _platform
    import sys as _sys

    deps = {}
    for mod in ("flask", "flask_sock", "requests", "yaml"):
        deps[mod] = importlib.util.find_spec(mod) is not None

    prov_info = {}
    if _srv.provider is not None:
        raw = _srv.provider.get_info() or {}
        # تطهير: مفاتيح وصفية معلومة فقط — أي مفتاح آخر (urls/tokens
        # المحتملة في overrides) لا يمر.
        for k in ("name", "description", "model", "available",
                  "initialized"):
            if k in raw:
                prov_info[k] = raw[k]

    metrics_summary = None
    if _srv.run_metrics_store is not None:
        try:
            metrics_summary = _srv.run_metrics_store.summary()
        except Exception:
            metrics_summary = None      # التشخيص لا يفشل بسبب المقاييس

    return jsonify({
        "ok": True,
        "diagnostics": {
            "version": _srv.APP_VERSION,
            "platform": {
                "system": _platform.system(),
                "release": _platform.release(),
                "python": _sys.version.split()[0],
            },
            "dependencies": deps,
            "project_name": _srv.fm.root.name,   # الاسم فقط — لا مسار
            "provider": prov_info,
            "metrics_summary": metrics_summary,
        },
    })


@bp.route("/api/settings")
def api_settings():
    """TSK-722a (P1-4 / D-9): الإعدادات الفعالة — قراءة فقط، **مُطهَّرة**.

    glass box (سابقة TSK-621): يعرض قيم config الحية كما تُطبَّق فعلًا.
    **عقد التطهير — whitelist أقسام صريح** (لا blacklist): قسم
    ``providers`` مُستبعد كليًا (قد يحمل api_key/base_url)؛
    ``project_root`` لا يُعرض كمسار — راية ``project_root_set`` فقط
    (نفس عقد لا-مسارات-مطلقة في TSK-721)؛ ``retention.pinned`` تُعرض
    كعدد فقط (قد تحوي مسارات). ``force_command_approval`` قيمة **فعالة**
    من ``_srv._force_command_approval()`` (افتراضي fail-closed True عند
    الغياب — D-1/TSK-617) مع راية ``explicit_in_config``.
    **لا مسار كتابة** — GET بلا آثار جانبية؛ التعديل عبر config.yaml
    وإعادة التشغيل (القارئ مُكاش — موثَّق).
    """
    cfg = _srv._load_config() or {}

    # whitelist المفاتيح العلوية البسيطة (قيم عددية/نصية/منطقية)
    _SIMPLE_KEYS = ("default_provider", "language", "auto_execute",
                    "backup_before_edit", "max_context_files",
                    "planner", "backend", "dispatch")
    settings: dict = {}
    for key in _SIMPLE_KEYS:
        settings[key] = cfg.get(key)

    # أقسام مركبة مسموحة — تمرَّر بمفاتيحها الفرعية المعلومة فقط
    def _section(name: str, allowed: tuple) -> dict | None:
        sec = cfg.get(name)
        if not isinstance(sec, dict):
            return None
        return {k: sec[k] for k in allowed if k in sec}

    settings["agent"] = _section("agent", (
        "command_allowlist", "command_timeout_seconds",
        "command_output_max_chars"))
    settings["context_budget"] = _section("context_budget", (
        "model_window", "reserved_output", "safety_margin"))
    settings["history"] = _section("history", ("payload_last_n",))
    ctx = cfg.get("context")
    sem = ctx.get("semantic") if isinstance(ctx, dict) else None
    if isinstance(sem, dict):
        settings["context_semantic"] = {
            k: sem[k] for k in ("enabled", "timeout_seconds", "top_k")
            if k in sem}
    else:
        settings["context_semantic"] = None
    settings["session_binding"] = _section("session_binding",
                                           ("warn_only", "policy"))
    settings["execution"] = _section("execution", ("stale_ttl_seconds",))
    settings["routing"] = _section("routing", (
        "direct_max", "auto_chain_max", "full_chain_max",
        "min_accounts_auto_chain", "min_accounts_full_chain",
        "min_accounts_delegate", "version"))

    # retention: pinned قد تحوي مسارات — عدد فقط (عقد لا-مسارات)
    ret = cfg.get("retention")
    if isinstance(ret, dict):
        pinned = ret.get("pinned")
        settings["retention"] = {
            "max_count": ret.get("max_count"),
            "max_age_days": ret.get("max_age_days"),
            "dry_run": ret.get("dry_run"),
            "pinned_count": len(pinned) if isinstance(pinned, list) else 0,
        }
    else:
        settings["retention"] = None

    # مسار الجذر: راية فقط — لا المسار (عقد التطهير)
    settings["project_root_set"] = bool(cfg.get("project_root"))

    # القيمة الفعالة (fail-closed عند الغياب — D-1/TSK-617)
    settings["force_command_approval"] = {
        "effective": _srv._force_command_approval(),
        "explicit_in_config": "force_command_approval" in cfg,
    }

    return jsonify({"ok": True, "settings": settings})
