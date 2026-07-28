# -*- coding: utf-8 -*-
"""TSK-601 (RP-01 + UXF-02 + TD-01): مقبض ``delegate_approve`` end-to-end.

كان المقبض ينادي ``parser.extract_actions/extract_options`` — دالتين غير
موجودتين في ResponseParser — فيُبتلع AttributeError ويصل الواجهةَ دائمًا
إطار done بـ actions=[] (القدرة معطلة بصمت). هذا الملف يغطي المقبض لأول
مرة (TD-01: كانت التغطية صفرًا) ويثبّت معايير القبول الأربعة:

1. دورة تفويض كاملة بمزود مزيف يرد بـ ``FILE:`` block →
   ``delegate_approve`` → إطار done يحمل actions غير فارغة (golden).
2. رد بلا actions → إطار done مع options دون خطأ.
3. استثناء في التحويل → إطار ``error`` يصل الواجهة (لا صمت) ثم done فارغ.
4. لا أثر للدالتين الوهميتين في server.py (grep بنيوي).

النمط: E2E عبر ``server._handle_ws_message(None, sctx, {...})`` مع
``SessionContext(send=sent.append)`` (نمط test_memory_panel/test_rollback)
وجسر تفويض حقيقي يُقاد بـ FakeProvider (نمط test_delegate_contract).
"""
from __future__ import annotations

import pathlib
import re

import pytest

import server
from chain.delegate import DelegateBridge
from core.session_context import SessionContext
from tests.fakes.fake_provider import FakeProvider


# ═══════════════════════ العدة ═══════════════════════

BRIEF_RESPONSE = "<brief>أنشئ صفحة ترحيب بسيطة</brief>"
FILE_RESPONSE = (
    "تم التنفيذ:\n\n"
    "```FILE: hello.html\n"
    "<h1>مرحبا</h1>\n"
    "```\n"
)
APPROVE_RESPONSE = "[VERDICT]: APPROVE\n[SUMMARY]: عمل سليم"
NO_ACTIONS_RESPONSE = (
    "لا حاجة لأي تعديل — الكود الحالي يفي بالغرض.\n\n"
    "[OPTIONS]\n"
    "- [1] أضف اختبارات\n"
    "- [2] حسّن التوثيق\n"
)


def _sctx():
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    return sctx, sent


def _bridge_at_waiting_approval(implementer_response: str) -> DelegateBridge:
    """يقود دورة تفويض كاملة (brief → implement → review) حتى waiting_approval."""
    bridge = DelegateBridge(FakeProvider(responses=[
        BRIEF_RESPONSE, implementer_response, APPROVE_RESPONSE,
    ]))
    run = bridge.run_delegation("أنشئ صفحة ترحيب", files_context={})
    assert run.status == "waiting_approval", (
        f"العدة نفسها معطوبة — الحالة: {run.status}")
    return bridge


def _frames(sent, ftype):
    return [f for f in sent if f.get("type") == ftype]


# ═══════════ (1) دورة كاملة → actions غير فارغة (golden) ═══════════

def test_approve_full_cycle_emits_nonempty_actions_golden():
    sctx, sent = _sctx()
    sctx.delegate_bridge = _bridge_at_waiting_approval(FILE_RESPONSE)

    server._handle_ws_message(None, sctx, {"type": "delegate_approve"})

    done = _frames(sent, "done")
    assert len(done) == 1
    # golden: التحويل المشترك _parsed_to_actions كما في مساري agent/direct
    assert done[0]["actions"] == [{
        "action": "create_file",
        "path": "hello.html",
        "content": "<h1>مرحبا</h1>",
        "language": "html",
    }]
    run_id = sctx.delegate_bridge.current_run.run_id
    assert done[0]["summary"] == f"✅ تم اعتماد التعديلات (delegation #{run_id})"
    # start/chunk المحفوظان قبل done (سلوك قائم — لا يتغير)
    assert len(_frames(sent, "start")) == 1
    chunk = _frames(sent, "chunk")
    assert len(chunk) == 1 and chunk[0]["text"] == FILE_RESPONSE
    # لا إطار error في المسار السعيد
    assert _frames(sent, "error") == []


def test_approve_lands_the_run():
    sctx, sent = _sctx()
    sctx.delegate_bridge = _bridge_at_waiting_approval(FILE_RESPONSE)
    server._handle_ws_message(None, sctx, {"type": "delegate_approve"})
    assert sctx.delegate_bridge.current_run.status == "landed"
    assert _frames(sent, "delegate_landed"), "حدث الهبوط يصل الواجهة"


# ═══════════ (2) رد بلا actions → done مع options دون خطأ ═══════════

def test_approve_no_actions_reply_yields_done_with_options():
    sctx, sent = _sctx()
    sctx.delegate_bridge = _bridge_at_waiting_approval(NO_ACTIONS_RESPONSE)

    server._handle_ws_message(None, sctx, {"type": "delegate_approve"})

    done = _frames(sent, "done")
    assert len(done) == 1
    assert done[0]["actions"] == []
    assert done[0]["options"] == ["أضف اختبارات", "حسّن التوثيق"]
    assert _frames(sent, "error") == []


# ═══════════ (3) استثناء في التحويل → error يصل الواجهة ═══════════

def test_conversion_failure_surfaces_error_frame(monkeypatch):
    sctx, sent = _sctx()
    sctx.delegate_bridge = _bridge_at_waiting_approval(FILE_RESPONSE)

    def _boom(response, mode=None):
        raise ValueError("parser exploded")
    monkeypatch.setattr(server.parser, "parse", _boom)

    server._handle_ws_message(None, sctx, {"type": "delegate_approve"})

    errors = _frames(sent, "error")
    assert len(errors) == 1, "الفشل يجب أن يُظهَر — لا صمت (UXF-02)"
    assert "parser exploded" in errors[0]["text"]
    # fallback الـ done الفارغ يبقى — الواجهة لا تُترك منتظرة
    done = _frames(sent, "done")
    assert len(done) == 1
    assert done[0]["actions"] == []


# ═══════════ سلوك محفوظ: لا تفويض نشط ═══════════

def test_no_active_delegation_still_errors():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "delegate_approve"})
    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert errors[0]["text"] == "لا يوجد تفويض نشط"


# ═══════════ (4) حارس بنيوي: لا أثر للدالتين الوهميتين ═══════════

def test_no_phantom_parser_methods_in_server():
    src = (pathlib.Path(server.__file__).read_text(encoding="utf-8"))
    assert not re.search(r"extract_actions|extract_options", src), (
        "server.py يجب ألا يشير لدوال المحلل غير الموجودة (RP-01)")
