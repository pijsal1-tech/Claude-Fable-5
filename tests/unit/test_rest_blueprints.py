# -*- coding: utf-8 -*-
"""TSK-613 (ADR-003) — تجميد سطح REST بعد التجميع في blueprints.

الضمانات المثبَّتة:
1. url_map ثابت: 31 قاعدة (29 route + /static + /ws) بنفس المسارات
   وmethods حرفيًا — معيار القبول «عدد routes ثابت».
   (TSK-621: +/api/permissions GET — توسيع عقد مقصود وموثّق:
   القبول ينص حرفيًا على «endpoint قراءة» — قرار المرحلة 2.)
2. smoke: كل endpoint يستجيب (لا 404/405) على app غير مهيأ.
3. الحقن الحي (_srv): monkeypatch على فضاء server ينعكس في الـ
   blueprint فورًا (نفس دلالة globals الأصلية — late binding).
4. لا دورة استيراد: وحدات routes/ لا تستورد server.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402

# سطح HTTP المجمّد قبل TSK-613 (المرجع: url_map عند 75b72f3^ —
# نفس القائمة حرفيًا؛ أي تغيير هنا تغيير عقد يحتاج قرارًا).
FROZEN_RULES = [
    ("/", ("GET",)),
    ("/api/backups", ("GET",)),
    ("/api/capacity", ("GET",)),
    ("/api/chat-history", ("GET",)),
    ("/api/clear", ("POST",)),
    ("/api/cwd", ("GET",)),
    ("/api/file/<path:filepath>", ("DELETE",)),
    ("/api/file/<path:filepath>", ("GET",)),
    ("/api/file/<path:filepath>", ("POST",)),
    ("/api/files", ("GET",)),
    ("/api/folder/<path:folderpath>", ("GET",)),
    ("/api/info", ("GET",)),
    ("/api/metrics/runs", ("GET",)),
    ("/api/models", ("GET",)),
    ("/api/permissions", ("GET",)),  # TSK-621 — قراءة فقط
    ("/api/new-file", ("POST",)),
    ("/api/new-folder", ("POST",)),
    ("/api/restore/<backup_name>", ("POST",)),
    ("/api/rollback/history", ("GET",)),
    ("/api/rollback/preview", ("GET",)),
    ("/api/run", ("POST",)),
    ("/api/run-file", ("POST",)),
    ("/api/search", ("GET",)),
    ("/api/session/<session_id>", ("DELETE",)),
    ("/api/session/<session_id>", ("GET",)),
    ("/api/session/new", ("POST",)),
    ("/api/sessions", ("GET",)),
    ("/api/switch-model", ("POST",)),
    ("/api/switch-project", ("POST",)),
    ("/static/<path:filename>", ("GET",)),
    ("/ws", ("GET",)),
]


def _current_rules():
    return sorted(
        (r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"})))
        for r in server.app.url_map.iter_rules()
    )


class TestRouteSurfaceFrozen:
    def test_rule_count_constant(self):
        assert len(_current_rules()) == 31

    def test_rules_bit_identical(self):
        assert _current_rules() == sorted(FROZEN_RULES)


class TestSmokeNo404:
    """كل مسار مسجّل يصل لمقبضه (لا 404/405) — smoke REST (بند القبول)."""

    CASES = [
        ("GET", "/api/files"), ("GET", "/api/search?q=x"),
        ("GET", "/api/chat-history"), ("POST", "/api/clear"),
        ("GET", "/api/sessions"), ("GET", "/api/backups"),
        ("GET", "/api/capacity"), ("GET", "/api/metrics/runs"),
        ("GET", "/api/rollback/history"), ("GET", "/api/info"),
        ("GET", "/api/cwd"), ("POST", "/api/run"),
        ("POST", "/api/new-file"), ("POST", "/api/new-folder"),
        ("POST", "/api/run-file"), ("POST", "/api/switch-project"),
    ]

    @pytest.mark.parametrize("method,url", CASES)
    def test_endpoint_reachable(self, method, url):
        c = server.app.test_client()
        r = c.open(url, method=method, json={} if method == "POST" else None)
        assert r.status_code not in (404, 405), (method, url, r.status_code)


class TestLiveInjection:
    """monkeypatch على فضاء server ينعكس في الـ blueprint (ADR-003 §2)."""

    def test_chat_history_read_live(self, monkeypatch):
        # TSK-709 (FI-01/3): المصدر القانوني صار conversation_state.
        from providers.base import Message
        from core.conversation_state import ConversationState
        cs = ConversationState()
        cs.append(Message(role="user", content="مرحبا"))
        monkeypatch.setattr(server, "conversation_state", cs)
        c = server.app.test_client()
        data = c.get("/api/chat-history").get_json()
        assert data["ok"] is True
        assert data["history"] == [{"role": "user", "content": "مرحبا"}]

    def test_clear_rebinds_server_global(self, monkeypatch):
        # TSK-709 (FI-01/3): المسح يقع على المخزن القانوني نفسه
        # (تكافؤ دلالة global القديمة — ADR-003 §2 محفوظ).
        from providers.base import Message
        from core.conversation_state import ConversationState
        cs = ConversationState()
        cs.append(Message(role="user", content="x"))
        cs.set_banner("قديم")
        monkeypatch.setattr(server, "conversation_state", cs)
        monkeypatch.setattr(server, "session_mgr", None)
        c = server.app.test_client()
        assert c.post("/api/clear").get_json()["ok"] is True
        assert server.conversation_state.snapshot() == []
        assert server.conversation_state.binding_banner == ""


class TestNoImportCycle:
    def test_routes_modules_do_not_import_server(self):
        for mod in ("files", "backups", "run", "sessions", "meta",
                    "rollback", "project", "__init__"):
            src = (ROOT / "routes" / f"{mod}.py").read_text(encoding="utf-8")
            assert "import server" not in src, mod
