# -*- coding: utf-8 -*-
"""QA-T11 §4 (جزء NF-12 / A3 / TSK-403) — إطار scan_start ومؤشر فوري.

Validates: TSK-403.

معيار القبول الحرفي: "مؤشر مرئي ≤200ms من الإرسال في كل الأوضاع" —
يُثبت آليًا من الجهتين:
  1. الخادم: `_dispatch_chat_message` يرسل `{"type":"scan_start"}`
     **كأول إطار** فور الاستلام وقبل أي عمل (كشف مسارات/بناء سياق) —
     نقيسه بإيقاف التنفيذ عند أول عمل فعلي والتحقق أن الإطار سبقه.
     المسار الثاني ("كل الأوضاع"): `chain_message` يرسل الإطار قبل
     قراءة المجلد/الملفات أيضًا.
  2. زمن الوصول: إرسال الإطار قبل أي I/O يعني وصوله خلال زمن
     round-trip الشبكة فقط (ميلي‌ثوانٍ) — نثبت بنيويًا أنه لا يوجد أي
     استدعاء حاجب (كشف مسارات/قراءة ملفات/AI) قبله في الدالة، وهو
     ما يضمن ≤200ms بلا قياس ساعة هش.
  3. الواجهة: `handleWSMessage` فيها case لـ scan_start تعرض
     "جاري التفكير…" فورًا، وأي إطار تالٍ يزيل المؤشر
     (start/chunk/error/…) — grep-asserts على app.js.

صفر نداءات AI خارجية — التنفيذ يُوقف قبل أي مسار AI.
"""
import json
import pathlib
import re

import pytest

import server

SERVER_SRC = pathlib.Path(server.__file__).read_text(encoding="utf-8")
ROOT = pathlib.Path(server.__file__).resolve().parent
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


class _Stop(BaseException):
    """يوقف التنفيذ عند أول عمل فعلي — BaseException كي لا تبتلعه
    except Exception."""


class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


class _StubFM:
    def __init__(self, root):
        self.root = root


def _sctx(root="/tmp/x"):
    from core.app_context import ProjectHandle
    from core.session_context import SessionContext
    ws = FakeWS()
    send = lambda m: ws.send(json.dumps(m, ensure_ascii=False))
    sctx = SessionContext(
        send=send,
        project=ProjectHandle(root=str(root), fm=_StubFM(pathlib.Path(root))))
    return sctx, ws


def _frames(ws):
    return [json.loads(p) for p in ws.sent]


class TestServerSendsScanStartFirst:
    def test_scan_start_is_first_frame_before_context_build(
            self, monkeypatch):
        """الإطار يسبق gather_message_context (بناء السياق)."""
        def _raiser(*a, **k):
            raise _Stop()

        monkeypatch.setattr(server, "gather_message_context", _raiser)
        sctx, ws = _sctx()
        with pytest.raises(_Stop):
            server._dispatch_chat_message(None, sctx, "اشرح المشروع",
                                          "chat", {})
        frames = _frames(ws)
        assert frames, "لا إطارات — scan_start لم يُرسل"
        assert frames[0] == {"type": "scan_start"}

    def test_scan_start_precedes_path_detection(self, monkeypatch,
                                                tmp_path):
        """الإطار يسبق حتى كشف المسارات: نوقف التنفيذ عند **أول**
        استدعاء isdir ونتحقق أن scan_start أُرسل قبله بالفعل."""
        def _stopping_isdir(p):
            raise _Stop()

        monkeypatch.setattr(server.os.path, "isdir", _stopping_isdir)
        sctx, ws = _sctx()
        with pytest.raises(_Stop):
            server._dispatch_chat_message(None, sctx, f'اشرح "{tmp_path}"',
                                          "chat", {})
        # عند لحظة أول كشف مسار كان scan_start قد أُرسل مسبقًا:
        assert _frames(ws) == [{"type": "scan_start"}]

    def test_no_blocking_work_before_scan_start_structurally(self):
        """≤200ms بنيويًا: لا يوجد بين رأس الدالة وسطر scan_start أي
        استدعاء حاجب (isdir/isfile/open/findall/gather/AI)."""
        m = re.search(
            r"def _dispatch_chat_message\(.*?\n(.*?)sctx\.send\(\{\"type\": \"scan_start\"\}\)",
            SERVER_SRC, re.S)
        assert m, "سطر scan_start غير موجود في _dispatch_chat_message"
        before = m.group(1)
        # استدعاءات فعلية فقط (بقوس) — ذكر الأسماء في docstring/تعليق
        # مسموح (docstring الدالة يذكر gather_message_context توثيقًا).
        for banned in ("os.path.isdir(", "os.path.isfile(", "open(",
                       "re.findall(", "gather_message_context(",
                       "request_router."):
            assert banned not in before, f"عمل حاجب قبل scan_start: {banned}"

    def test_chain_message_mode_also_sends_scan_start(self):
        """"كل الأوضاع": مسار chain_message يرسل الإطار قبل قراءة
        المجلد/الملفات (بنيويًا — الإرسال قبل folder_path/isdir)."""
        # TSK-611: البلوك صار دالة _ws_chain_message (جدول dispatch —
        # ADR-001)؛ نفس الفحص البنيوي على جسم الدالة.
        m = re.search(
            r"def _ws_chain_message\(ctx, sctx, msg\):(.*?)\ndef ",
            SERVER_SRC, re.S)
        assert m, "بلوك chain_message غير موجود"
        block = m.group(1)
        send_pos = block.find('sctx.send({"type": "scan_start"})')
        assert send_pos != -1, "chain_message بلا scan_start"
        read_pos = block.find("os.path.isdir(folder_path)")
        assert read_pos == -1 or send_pos < read_pos, \
            "scan_start يجب أن يسبق قراءة المجلد"


class TestFrontendIndicator:
    def test_handle_ws_message_has_scan_start_case(self):
        assert 'case "scan_start":' in APP_JS
        assert "showScanIndicator()" in APP_JS

    def test_indicator_shows_thinking_text(self):
        assert "جاري التفكير" in APP_JS

    def test_any_subsequent_frame_removes_indicator(self):
        """أي إطار تالٍ (start/chunk/error/…) يزيل المؤشر — الإزالة
        قبل الـ switch مباشرة لكل الأنواع عدا scan_start نفسه."""
        assert re.search(
            r'if \(data\.type !== "scan_start"\) removeScanIndicator\(\);',
            APP_JS)
        assert "function removeScanIndicator()" in APP_JS

    def test_indicator_is_idempotent(self):
        """وصول scan_start مكرر (وضعا chat وchain في طلب واحد مستقبلًا)
        لا يكدّس مؤشرات — حارس المرجع الموجود."""
        m = re.search(r"function showScanIndicator\(\) \{(.*?)\n\}",
                      APP_JS, re.S)
        assert m and "if (scanIndicatorEl) return" in m.group(1)


class TestNoBehaviorChange:
    def test_scan_start_frame_is_minimal(self):
        """الإطار حمولة دنيا {"type":"scan_start"} — لا بيانات إضافية
        تكسر مستهلكين آخرين (StatusChip.noteFrame يتجاهله)."""
        assert 'sctx.send({"type": "scan_start"})' in SERVER_SRC
