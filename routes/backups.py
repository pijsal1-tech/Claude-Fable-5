"""routes/backups.py — TSK-613 (ADR-003): blueprint النسخ الاحتياطية والاستعادة.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from flask import Blueprint, jsonify

bp = Blueprint("backups", __name__)
_srv = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/backups")
def api_backups():
    """قائمة النسخ الاحتياطية الكاملة"""
    backup_dir = _srv.fm.root / ".webdev_backups" / "full"
    if not backup_dir.exists():
        return jsonify({"ok": True, "backups": []})

    backups = []
    for f in sorted(backup_dir.glob("*.zip"), reverse=True):
        backups.append({
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "created": f.stem.split("_", 1)[-1] if "_" in f.stem else "",
        })
    return jsonify({"ok": True, "backups": backups})


@bp.route("/api/restore/<backup_name>", methods=["POST"])
def api_restore_backup(backup_name):
    """استعادة نسخة احتياطية"""
    import zipfile
    backup_path = _srv.fm.root / ".webdev_backups" / "full" / backup_name
    if not backup_path.exists():
        return jsonify({"ok": False, "error": "النسخة غير موجودة"}), 404

    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            # TSK-105 (NF-15): Zip-Slip guard — فحص كل الأعضاء قبل أي فك.
            # أي انتهاك ⇒ 400 ورفض كامل (لا فك جزئي).
            violations = _srv._zip_member_violations(zf, _srv.fm.root)
            if violations:
                return jsonify({
                    "ok": False,
                    "error": "أرشيف مرفوض: أعضاء خارج جذر المشروع أو غير آمنة",
                    "violations": violations,
                }), 400
            zf.extractall(_srv.fm.root)
        return jsonify({"ok": True, "message": f"تم استعادة: {backup_name}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
