"""routes/meta.py — TSK-613 (ADR-003): blueprint معلومات الخادم والسعة والمقاييس.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from flask import Blueprint, jsonify

bp = Blueprint("meta", __name__)
_srv = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


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
        "history_length": len(_srv.chat_history),
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
