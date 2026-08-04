# -*- coding: utf-8 -*-
"""TSK-613 (ADR-003) — تجميد سطح REST بعد التجميع في blueprints.

الضمانات المثبَّتة:
1. url_map ثابت: 31 قاعدة (29 route + /static + /ws) بنفس المسارات
   وmethods حرفيًا — معيار القبول «عدد routes ثابت».
   (TSK-621: +/api/permissions GET — توسيع عقد مقصود وموثّق:
   القبول ينص حرفيًا على «endpoint قراءة» — قرار المرحلة 2.)
   (TSK-721/D-9: +/api/diagnostics GET — توسيع عقد مقصود ثانٍ:
   نقطة تشخيص قراءة-فقط مُطهَّرة — معرَّفة في DEVELOPMENT_TASKS
   §BATCH-P1 ومفوَّضة بقرار D-9.)
   (TSK-722a/D-9: +/api/settings GET — توسيع عقد مقصود ثالث:
   إعدادات فعالة قراءة-فقط مُطهَّرة [whitelist أقسام؛ لا providers
   ولا مسارات] — معرَّفة في DEVELOPMENT_TASKS §BATCH-P1/TSK-722a.)
   (TSK-731b/D-11: +/api/update-check GET — توسيع عقد مقصود خامس:
   فحص تحديث يدوي opt-in معطَّل افتراضيًا [صفر شبكة على المسار
   الافتراضي] — معرَّف في DEVELOPMENT_TASKS §BATCH-P3/TSK-731.)
   (TSK-734/D-19-6: /api/permissions GET → GET+POST — توسيع عقد
   مقصود سادس: تحرير الأذونات من الواجهة عبر ملف overrides جانبي
   [config.yaml لا يُكتب؛ whitelist صارم fail-closed؛ إعادة ربط
   حي] — معرَّف في DEVELOPMENT_TASKS §TSK-734، قرار المالك D-19.)
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
    ("/api/diagnostics", ("GET",)),  # TSK-721/D-9 — قراءة فقط مُطهَّرة
    ("/api/file/<path:filepath>", ("DELETE",)),
    ("/api/file/<path:filepath>", ("GET",)),
    ("/api/file/<path:filepath>", ("POST",)),
    ("/api/files", ("GET",)),
    ("/api/folder/<path:folderpath>", ("GET",)),
    ("/api/info", ("GET",)),
    ("/api/metrics/runs", ("GET",)),
    ("/api/models", ("GET",)),
    ("/api/permissions", ("GET", "POST")),  # TSK-621 قراءة + TSK-734/D-19-6 تحرير
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
    ("/api/settings", ("GET",)),  # TSK-722a/D-9 — قراءة فقط مُطهَّرة
    ("/api/switch-model", ("POST",)),
    ("/api/trust", ("GET", "POST")),  # TSK-725b/D-10 — قرار ثقة المستخدم
    ("/api/update-check", ("GET",)),  # TSK-731b/D-11 — فحص تحديث يدوي opt-in
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
        assert len(_current_rules()) == 35   # 31 + diagnostics(721) + settings(722a) + trust(725b) + update-check(731b)

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


class TestErrStatusContractF009:
    """TSK-CEV-121 (CEV-F-009, D-18): العقد الرقمي الموحد لأخطاء العميل.

    كان انتهاك حدود المشروع نفسه يرجع 404 قراءةً و500 كتابةً
    (except Exception شامل). الآن `_err_status` يميّز:
    PermissionError⇒403، FileNotFoundError⇒404، ValueError⇒400،
    والباقي (عطل خادم حقيقي)⇒500. fail-closed لم يتغير — الرمز فقط.
    """

    def test_err_status_mapping_unit(self):
        from routes.files import _err_status
        assert _err_status(PermissionError("x")) == 403
        assert _err_status(FileNotFoundError("x")) == 404
        assert _err_status(ValueError("x")) == 400
        assert _err_status(RuntimeError("x")) == 500

    def test_write_traversal_returns_4xx_not_500(self, monkeypatch, tmp_path):
        """مجس G6 الأصلي: POST بكتابة خارج الجذر — كان 500، الآن 403.
        fail-closed يبقى: لا ملف يُكتب خارج الجذر."""
        from actions.file_manager import FileManager
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setattr(server, "fm", FileManager(str(proj)))
        c = server.app.test_client()
        r = c.post("/api/file/..%2fpwned.txt", json={"content": "x"})
        assert r.status_code == 403, r.status_code
        assert r.get_json()["ok"] is False
        assert not (tmp_path / "pwned.txt").exists()   # fail-closed محفوظ

    def test_read_traversal_returns_403(self, monkeypatch, tmp_path):
        """القراءة عبر الحدود: كانت 404 شاملة — الآن 403 (نفس عقد الكتابة)."""
        from actions.file_manager import FileManager
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setattr(server, "fm", FileManager(str(proj)))
        c = server.app.test_client()
        r = c.get("/api/file/..%2f..%2fetc%2fpasswd")
        assert r.status_code == 403, r.status_code
        assert r.get_json()["ok"] is False

    def test_read_missing_file_still_404(self, monkeypatch, tmp_path):
        """الملف غير الموجود داخل الحدود يبقى 404 — لا كسر للعقد القديم."""
        from actions.file_manager import FileManager
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setattr(server, "fm", FileManager(str(proj)))
        c = server.app.test_client()
        r = c.get("/api/file/no_such_file.txt")
        assert r.status_code == 404, r.status_code
