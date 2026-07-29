"""routes/run.py — TSK-613 (ADR-003): blueprint تنفيذ الأوامر.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from flask import Blueprint, jsonify, request
import os

bp = Blueprint("run", __name__)
_srv = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/run", methods=["POST"])
def api_run():
    """تنفيذ أمر في الطرفية — يدعم CMD و PowerShell + cd"""
    data = request.get_json()
    command = data.get("command", "").strip()
    shell_type = data.get("shell", "cmd")  # cmd | powershell
    if not command:
        return jsonify({"ok": False, "error": "أمر فارغ", "cwd": _srv.cmd_runner.cwd}), 400

    # ── معالجة cd بشكل خاص (لأن subprocess.run مش بتحفظ الـ cwd) ──
    stripped = command.strip()
    if stripped.lower() == "cd" or stripped.lower() == "cd.":
        return jsonify({"ok": True, "success": True, "output": _srv.cmd_runner.cwd, "error": "", "code": 0, "cwd": _srv.cmd_runner.cwd})

    if stripped.lower().startswith("cd ") or stripped.lower().startswith("cd\\"):
        target = stripped[3:].strip().strip('"').strip("'")
        try:
            new_cwd = os.path.abspath(os.path.join(_srv.cmd_runner.cwd, target))
            if os.path.isdir(new_cwd):
                _srv.cmd_runner.cwd = new_cwd
                return jsonify({"ok": True, "success": True, "output": "", "error": "", "code": 0, "cwd": _srv.cmd_runner.cwd})
            else:
                return jsonify({"ok": False, "success": False, "output": "", "error": f"المسار غير موجود: {new_cwd}", "code": 1, "cwd": _srv.cmd_runner.cwd})
        except Exception as e:
            return jsonify({"ok": False, "success": False, "output": "", "error": str(e), "code": 1, "cwd": _srv.cmd_runner.cwd})

    # ── تحضير الأمر حسب نوع الشل ──
    if shell_type == "powershell":
        # PowerShell محتاج wrapper لأن subprocess بيستخدم cmd.exe افتراضياً
        full_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{command}"'
    else:
        # CMD: subprocess.run(shell=True) بيستخدم cmd.exe مباشرة — مش محتاج تغليف
        full_cmd = command

    # TSK-502 (NF-16): راية force_command_approval تقلب التجاوز —
    # مفعّلة ⇒ كل أمر REST يمر ببوابة الموافقة إلزاميًا.
    result = _srv.cmd_runner.run(full_cmd, need_approval=False, timeout=30,
                            force_approval=_srv._force_command_approval())
    result["cwd"] = _srv.cmd_runner.cwd
    return jsonify({"ok": result["success"], **result})


@bp.route("/api/cwd")
def api_cwd():
    """الحصول على المسار الحالي"""
    return jsonify({"cwd": _srv.cmd_runner.cwd})


@bp.route("/api/run-file", methods=["POST"])
def api_run_file():
    """تشغيل ملف (Python / Node.js / etc)"""
    data = request.get_json()
    filepath = data.get("path", "").strip()
    if not filepath:
        return jsonify({"ok": False, "error": "مسار الملف مطلوب"}), 400

    # تحديد الأمر حسب الامتداد
    ext = os.path.splitext(filepath)[1].lower()
    runners = {
        ".py": "python",
        ".js": "node",
        ".ts": "npx ts-node",
        ".sh": "bash",
        ".bat": "cmd /c",
        ".ps1": "powershell -File",
    }

    runner = runners.get(ext)
    if not runner:
        return jsonify({"ok": False, "error": f"لا يمكن تشغيل ملفات {ext}"}), 400

    command = f"{runner} {filepath}"
    # TSK-502 (NF-16): نفس راية إلزام الموافقة — راجع _force_command_approval.
    result = _srv.cmd_runner.run(command, need_approval=False, timeout=30,
                            force_approval=_srv._force_command_approval())
    return jsonify({"ok": result["success"], **result, "command": command})
