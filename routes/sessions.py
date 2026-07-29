"""routes/sessions.py — TSK-613 (ADR-003): blueprint الجلسات وسجل المحادثة.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from flask import Blueprint, jsonify

from providers.base import Message

bp = Blueprint("sessions", __name__)
_srv = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/chat-history")
def api_chat_history():
    """الحصول على تاريخ المحادثة بالكامل"""
    history_data = [{"role": msg.role, "content": msg.content} for msg in _srv.chat_history]
    return jsonify({"ok": True, "history": history_data})


@bp.route("/api/clear", methods=["POST"])
def api_clear():
    """مسح المحادثة وبدء جلسة جديدة"""
    _srv.chat_history = []
    _srv._binding_banner = ""  # R-303: جلسة جديدة = زوال تنبيه الربط
    # بدء جلسة جديدة
    if _srv.session_mgr:
        _srv.session_mgr.new_session(str(_srv.fm.root) if _srv.fm else "")
    return jsonify({"ok": True})


@bp.route("/api/sessions")
def api_sessions():
    """قائمة الجلسات المحفوظة"""
    if not _srv.session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500
    sessions = _srv.session_mgr.list_sessions()
    return jsonify({"ok": True, "sessions": sessions, "current": _srv.session_mgr.current_session_id})


@bp.route("/api/session/<session_id>")
def api_load_session(session_id):
    """تحميل جلسة محددة"""
    if not _srv.session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500

    session = _srv.session_mgr.load_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "جلسة غير موجودة"}), 404

    # استعادة الـ chat_history
    _srv.chat_history = [
        Message(role=m["role"], content=m["content"])
        for m in session.get("messages", [])
    ]
    return jsonify({
        "ok": True,
        "session": session,
        "history": [{"role": m["role"], "content": m["content"]} for m in session.get("messages", [])]
    })


@bp.route("/api/session/new", methods=["POST"])
def api_new_session():
    """بدء جلسة جديدة"""
    if not _srv.session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500

    _srv.chat_history = []
    _srv._binding_banner = ""  # R-303: جلسة جديدة = زوال تنبيه الربط
    session = _srv.session_mgr.new_session(str(_srv.fm.root) if _srv.fm else "")
    return jsonify({"ok": True, "session": session})


@bp.route("/api/session/<session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    """حذف جلسة"""
    if not _srv.session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500
    deleted = _srv.session_mgr.delete_session(session_id)
    return jsonify({"ok": deleted})
