# -*- coding: utf-8 -*-
"""TSK-711 (FI-01/5 — إغلاق دفعة D-7): عقد تكافؤ REST↔WS + ماسح النكوص.

العقد الذي تثبته الدفعة: حالة المحادثة المشتركة (التاريخ + بانر الربط)
مصدرها الوحيد ``server.conversation_state`` —
- كل كتابة REST تنعكس فورًا على بذر أي اتصال WS جديد.
- عزل التبويبات (T-048) محفوظ: الاتصال القائم يحتفظ بنسخته.
- البانر يُقرأ حيًّا (banner_source) فيتغير للاتصالات القائمة أيضًا.
- ماسح نكوص دائم: لا كتابة/قراءة خام على globals القديمة من routes/.
"""
import json
import pathlib
import re

import server
from core.conversation_state import ConversationState
from providers.base import Message

ROOT = pathlib.Path(__file__).resolve().parents[2]


class FakeWS:
    """قناة WS زائفة — نفس نمط test_session_context.py."""

    def __init__(self):
        self.sent: list[str] = []

    def receive(self):
        return None

    def send(self, payload: str):
        self.sent.append(payload)


def _fresh_store(monkeypatch, messages=(), banner=""):
    cs = ConversationState()
    for m in messages:
        cs.append(m)
    if banner:
        cs.set_banner(banner)
    monkeypatch.setattr(server, "conversation_state", cs)
    return cs


# ═══════════════ عقد التكافؤ REST ↔ WS ═══════════════

class TestRestToWsParity:
    def test_ws_seed_equals_rest_read(self, monkeypatch):
        """اتصال WS جديد يُبذر بنفس ما تعيده /api/chat-history حرفيًا."""
        _fresh_store(monkeypatch, [Message(role="user", content="س"),
                                   Message(role="assistant", content="ج")])
        rest = server.app.test_client().get("/api/chat-history").get_json()
        sctx = server._build_session_context(FakeWS())
        try:
            ws_view = [{"role": m.role, "content": m.content}
                       for m in sctx.chat_history]
            assert rest["ok"] is True
            assert ws_view == rest["history"]
        finally:
            sctx.close()

    def test_rest_clear_reflected_in_new_ws_connection(self, monkeypatch):
        """كتابة REST (/api/clear) ⇒ الاتصال الجديد يرى الحالة الجديدة،
        والاتصال القائم يحتفظ بنسخته (عزل T-048)."""
        _fresh_store(monkeypatch, [Message(role="user", content="قديم")],
                     banner="⚠️ قديم")
        monkeypatch.setattr(server, "session_mgr", None)

        old_sctx = server._build_session_context(FakeWS())
        try:
            assert len(old_sctx.chat_history) == 1

            assert server.app.test_client().post(
                "/api/clear").get_json()["ok"] is True

            new_sctx = server._build_session_context(FakeWS())
            try:
                assert new_sctx.chat_history == []          # الجديد يرى المسح
                assert len(old_sctx.chat_history) == 1      # القائم معزول
            finally:
                new_sctx.close()
        finally:
            old_sctx.close()

    def test_banner_is_live_for_existing_connections(self, monkeypatch):
        """البانر يُقرأ حيًّا: مسح REST يصل للاتصال القائم عبر banner_source."""
        _fresh_store(monkeypatch, banner="⚠️ [تنبيه ربط الجلسة]: X")
        monkeypatch.setattr(server, "session_mgr", None)

        sctx = server._build_session_context(FakeWS())
        try:
            assert "تنبيه ربط الجلسة" in sctx.banner_source()
            server.app.test_client().post("/api/clear")
            assert sctx.banner_source() == ""               # قراءة حية
        finally:
            sctx.close()

    def test_info_history_length_matches_store(self, monkeypatch, tmp_path):
        """history_length في /api/info = طول المخزن القانوني."""
        from actions.file_manager import FileManager
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "a.py").write_text("x=1\n", encoding="utf-8")
        monkeypatch.setattr(server, "fm", FileManager(str(proj)))
        monkeypatch.setattr(server, "provider", None)
        _fresh_store(monkeypatch, [Message(role="user", content=str(i))
                                   for i in range(3)])
        body = server.app.test_client().get("/api/info").get_json()
        assert body["ok"] is True
        assert body["history_length"] == 3


# ═══════════════ ماسح النكوص (دائم — نمط TSK-704/706) ═══════════════

class TestNoRawStateAccessContract:
    """يمنع للأبد عودة الوصول الخام لحالة المحادثة خارج المخزن."""

    _RAW = re.compile(r"_srv\.(chat_history|_binding_banner)")

    def test_routes_never_touch_raw_globals(self):
        offenders: list[str] = []
        for path in sorted((ROOT / "routes").glob("*.py")):
            src = path.read_text(encoding="utf-8")
            for i, line in enumerate(src.splitlines(), 1):
                if self._RAW.search(line):
                    offenders.append(f"{path.name}:{i}: {line.strip()}")
        assert offenders == [], (
            "وصول خام لحالة المحادثة خارج ConversationState:\n"
            + "\n".join(offenders))

    def test_ws_seeding_reads_only_from_store(self):
        """_build_session_context لا يقرأ globals الخام بعد TSK-708."""
        src = (ROOT / "server.py").read_text(encoding="utf-8")
        m = re.search(r"def _build_session_context\(.*?\n(?=\ndef |\nclass )",
                      src, re.DOTALL)
        assert m, "تعذر عزل جسم _build_session_context"
        body = m.group(0)
        assert "conversation_state.snapshot()" in body
        assert "conversation_state.binding_banner" in body
        assert "list(chat_history)" not in body
        assert re.search(r"lambda: _binding_banner\b", body) is None
