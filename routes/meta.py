"""routes/meta.py — TSK-613 (ADR-003): blueprint معلومات الخادم والسعة والمقاييس.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from typing import Any
from flask import Blueprint, jsonify, request

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


def _permissions_payload():
    """TSK-621/TSK-734: جسم استجابة الأذونات الفعالة — يبنى من الحقيقة
    الحية (config الفعال + agent_tools/gate المربوطين) عند كل نداء."""
    from chain.agent_tools import (SAFE_TOOLS, APPROVAL_TOOLS,
                                   command_policy_from)
    from actions.command_runner import SAFE_COMMANDS, DANGEROUS_COMMANDS

    # TSK-734 (القرار 6): من الـ config الفعال — overrides الواجهة
    # (permissions_overrides.json) تعلو على config.yaml.
    policy = command_policy_from(_srv._effective_config())
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


@bp.route("/api/permissions", methods=["GET", "POST"])
def api_permissions():
    """TSK-621 (قراءة) + TSK-734 (القرار 6 من تسلسل D-19 — كتابة).

    GET ⇒ glass box: السياسة الفعالة الحية (TSK-621) — من TSK-734
    تُبنى فوق الـ config الفعال (config.yaml + overrides الواجهة).

    POST {overrides} ⇒ تحرير الأذونات من الواجهة (توسيع سادس موثَّق
    للسطح المجمّد — تعليق D-19-6 في test_rest_blueprints):
    - whitelist صارم fail-closed: ``force_command_approval`` (bool)
      و``agent.command_allowlist`` (dict str→str غير فارغ) **فقط**؛
      أي مفتاح/نوع آخر ⇒ 400 مع **صفر تغيير حالة** (لا لمس للقرص).
    - ``null`` لمفتاح = مسح ذلك الـ override (العودة لقيمة config.yaml)؛
      overrides ناتجة فارغة ⇒ حذف الملف الجانبي كليًا.
    - config.yaml **لا يُكتب أبدًا** (تعليقاته العربية محفوظة) —
      الكتابة الذرية NF-19 تذهب لـ permissions_overrides.json.
    - إعادة الربط الحي: بعد نجاح الكتابة تُبنى CommandPolicy جديدة
      وتُسند مباشرة لـ ``agent_tools.command_policy`` (كائن حي — بلا
      إعادة تشغيل)؛ ``_force_command_approval()`` يقرأ الفعال أصلًا.
    - أداة localhost-only (النشر الشبكي = القرار 9 الأخير — مراجعته
      الأمنية **يجب** أن تعيد فحص هذا المسار).
    الاستجابة = نفس شكل GET (السياسة الفعالة الجديدة) — اللوحة تعيد
    الرسم من الحقيقة المعادة لا من افتراض تفاؤلي.
    """
    if request.method == "GET":
        return _permissions_payload()

    # POST — تحرير الأذونات (TSK-734b)
    from core.permissions_overrides import (ALLOWED_KEYS, read_overrides,
                                            write_overrides)

    data = request.get_json(silent=True) or {}
    patch = data.get("overrides")
    if not isinstance(patch, dict) or not patch:
        return jsonify({"ok": False,
                        "error": "overrides يجب أن يكون dict غير فارغ"}), 400
    unknown = set(patch) - ALLOWED_KEYS
    if unknown:
        return jsonify({
            "ok": False,
            "error": f"مفاتيح غير مسموحة: {sorted(unknown)} — "
                     f"المسموح: {sorted(ALLOWED_KEYS)}"}), 400

    # الدمج فوق الحالة المخزنة: null = مسح المفتاح (عودة لـ config.yaml).
    merged = read_overrides(_srv._DIR)
    for k, v in patch.items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    # write_overrides يتحقق قبل أي لمس للقرص — رفضها = 400 بصفر تغيير.
    if not write_overrides(_srv._DIR, merged):
        return jsonify({"ok": False,
                        "error": "قيم overrides غير صالحة — "
                                 "force_command_approval: bool؛ "
                                 "agent.command_allowlist: "
                                 "dict[str, str غير فارغ]"}), 400

    # إعادة الربط الحي لسياسة أوامر الـ agent (بلا إعادة تشغيل).
    from chain.agent_tools import command_policy_from
    new_policy = command_policy_from(_srv._effective_config())
    if getattr(_srv, "agent_tools", None) is not None:
        _srv.agent_tools.command_policy = new_policy

    return _permissions_payload()


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

    # TSK-730a (BATCH-P3): إظهار الإضافات — glass-box. حتى الآن كان
    # المُحمَّلون/المحجورون يُطبعون عند الإقلاع فقط (server.py) بلا أثر
    # في حزمة التشخيص. عقد التطهير يبقى: أسماء/مراحل/أسباب فقط —
    # QuarantineRecord.to_dict() لا يحمل مسارات ولا أسرارًا.
    plugins_info: dict = {"loaded": [], "quarantined": []}
    _reg = getattr(_srv, "plugin_registry", None)
    if _reg is not None:
        try:
            plugins_info["loaded"] = sorted(_reg.loaded)
            plugins_info["quarantined"] = [
                q.to_dict() for q in _reg.quarantined]
        except Exception:
            # التشخيص لا يفشل بسبب سجل الإضافات — نفس فلسفة المقاييس.
            plugins_info = {"loaded": [], "quarantined": []}

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
            "plugins": plugins_info,             # TSK-730a
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


@bp.route("/api/trust", methods=["GET", "POST"])
def api_trust():
    """TSK-725b (Workspace Trust): قراءة/قرار ثقة المجلد الحالي.

    GET ⇒ {ok, trust: {trusted, decided_at?, decided_by?}} — **بلا
    مسارات** (عقد التطهير — TSK-621/721/722a). غياب/عطب السجل ⇒
    trusted=False (fail-closed — core/workspace_trust).
    POST {trusted: bool} ⇒ تخزين **قرار مستخدم صريح** ذريًا (NF-19)
    — كتابة قرار لا كتابة config (مسموحة ضمن عقد 722a). توسيع رابع
    موثَّق للسطح المجمّد: 33→34 (test_rest_blueprints).
    """
    from core.workspace_trust import read_trust_record, set_trust

    fm_ = _srv.fm
    if fm_ is None:
        return jsonify({"ok": False, "error": "لا مشروع مفتوح"}), 503

    if request.method == "GET":
        rec = read_trust_record(fm_.root)
        trust: dict[str, object] = {
            "trusted": bool(rec is not None and rec["trusted"] is True)}
        if rec is not None:
            trust["decided_at"] = rec.get("decided_at")
            trust["decided_by"] = rec.get("decided_by")
        return jsonify({"ok": True, "trust": trust})

    # POST — قرار المستخدم الصريح
    data = request.get_json(silent=True) or {}
    trusted = data.get("trusted")
    if not isinstance(trusted, bool):
        return jsonify({"ok": False,
                        "error": "trusted يجب أن تكون bool"}), 400
    if not set_trust(fm_.root, trusted, decided_by="user"):
        return jsonify({"ok": False, "error": "فشل تخزين قرار الثقة"}), 500
    return jsonify({"ok": True, "trust": {"trusted": trusted}})


@bp.route("/api/update-check")
def api_update_check():
    """TSK-731b (BATCH-P3/D-11): فحص تحديث يدوي — **opt-in، معطَّل افتراضيًا**.

    العقد الأمني (IR-1 لا-phone-home):
    - قسم config ``updates: {check_enabled, manifest_url}`` — غيابه أو
      ``check_enabled`` ليست True حرفيًا أو ``manifest_url`` فارغة ⇒
      ``{ok, enabled: false}`` مع **صفر لمس شبكة** (لا استيراد فحص أصلًا).
    - لا polling خلفي أبدًا — الاستدعاء يدوي من المستخدم فقط.
    - التطهير: ``manifest_url`` لا تُردَّد في الاستجابة (قد تحمل
      tokens في query)؛ ``url`` القادمة من الـ manifest تمر (وجهة
      تحميل مقصودة للمستخدم).
    - فشل الفحص صامت (check_for_update ⇒ None): ``latest: null``
      و``update_available: false`` — لا 5xx ولا تفاصيل خطأ.
    توسيع خامس موثَّق للسطح المجمّد: 34→35 (test_rest_blueprints).
    """
    cfg = _srv._load_config() or {}
    upd = cfg.get("updates")
    if not isinstance(upd, dict) or upd.get("check_enabled") is not True:
        return jsonify({"ok": True, "enabled": False})
    manifest_url = upd.get("manifest_url")
    if not isinstance(manifest_url, str) or not manifest_url.strip():
        return jsonify({"ok": True, "enabled": False})

    # استيراد كسول — لا يُحمَّل إطلاقًا على المسار الافتراضي المعطَّل
    from core.update_check import check_for_update

    current = str(_srv.APP_VERSION)
    info = check_for_update(manifest_url.strip(), current)
    if info is None:                       # فشل صامت — عقد update_check
        return jsonify({"ok": True, "enabled": True, "current": current,
                        "latest": None, "update_available": False,
                        "url": ""})
    return jsonify({"ok": True, "enabled": True, "current": info.current,
                    "latest": info.latest,
                    "update_available": info.update_available,
                    "url": info.url})
