# -*- coding: utf-8 -*-
"""TSK-732c (D-19-4): مقابض المهام الخلفية الأربعة end-to-end.

يغطي المقابض الجديدة (background_delegate_message / background_status /
background_approve / background_reject) بنمط
test_delegate_approve_handler.py حرفيًا: FakeProvider يقود دورة تفويض
حقيقية عبر ``server._handle_ws_message`` مع ``SessionContext(send=...)``.

معايير القبول المثبّتة (من مواصفة TSK-732):
1. الإطلاق يرجع إطار ``background_started`` فورًا (hand-off).
2. بعد اكتمال الدورة (wait بمهلة) الحالة waiting_approval —
   **بلا land تلقائي** (الثابت الصلب — لا YOLO).
3. ``background_status`` يعيد snapshot كاملًا (reconnect-safe).
4. ``background_approve`` يهبط ويبث done + actions (golden مشترك مع
   مسار delegate_approve).
5. ``background_reject`` يرفض ويحرر الخانة.
6. إطلاق ثانٍ فوق waiting_approval يُرفض برسالة واضحة.
7. تذكرة محجوزة → إطار busy (سياسة الـ run الواحد تبقى سيدة).

صفر نداءات AI خارجية — كل الردود مبرمجة (T-002).
"""
from __future__ import annotations

import pytest

import server
from chain.background_delegate import (
    BG_LANDED, BG_REJECTED, BG_RUNNING, BG_WAITING_APPROVAL,
)
from core.execution import ExecutionRegistry
from core.session_context import SessionContext
from tests.fakes.fake_provider import FakeProvider


# نفس مهلة test_background_delegate.py — حتمية عمليًا (الدورة مزيفة).
JOIN_TIMEOUT = 10.0

# ═══════════════════════ العدة ═══════════════════════

BRIEF_RESPONSE = "<brief>أنشئ صفحة ترحيب بسيطة</brief>"
FILE_RESPONSE = (
    "تم التنفيذ:\n\n"
    "```FILE: hello.html\n"
    "<h1>مرحبا</h1>\n"
    "```\n"
)
APPROVE_RESPONSE = "[VERDICT]: APPROVE\n[SUMMARY]: عمل سليم"


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """عزل كل اختبار بسجل تذاكر خاص (نمط test_run_slot_per_project)."""
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


def _sctx():
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    # المزود المبرمج عبر خيار التبويب (يتقدّم على provider_source)
    sctx.model_provider = FakeProvider(responses=[
        BRIEF_RESPONSE, FILE_RESPONSE, APPROVE_RESPONSE,
    ])
    return sctx, sent


def _frames(sent, ftype):
    return [f for f in sent if f.get("type") == ftype]


def _launch_and_wait(sctx, sent, text="أنشئ صفحة ترحيب"):
    """يطلق مهمة خلفية وينتظر اكتمال دورتها (حتى waiting_approval)."""
    server._handle_ws_message(None, sctx, {
        "type": "background_delegate_message", "text": text,
    })
    task = sctx.background_task
    assert task is not None, "المهمة لم تُنشأ"
    assert task.wait(JOIN_TIMEOUT), "خيط المهمة الخلفية لم ينتهِ في المهلة"
    return task


# ═══════════ (1) الإطلاق: background_started فورًا (hand-off) ═══════════

def test_launch_emits_background_started_immediately():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {
        "type": "background_delegate_message", "text": "أنشئ صفحة ترحيب",
    })
    # start() يبث background_started متزامنًا قبل إطلاق الخيط —
    # الإطار موجود لحظة عودة المقبض (hand-off حقيقي).
    started = _frames(sent, "background_started")
    assert len(started) == 1
    assert started[0]["task_id"] == sctx.background_task.task_id
    assert started[0]["request"] == "أنشئ صفحة ترحيب"
    sctx.background_task.wait(JOIN_TIMEOUT)  # تنظيف الخيط


def test_launch_empty_text_errors_without_task():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {
        "type": "background_delegate_message", "text": "   ",
    })
    assert _frames(sent, "error") == [
        {"type": "error", "text": "الرسالة فارغة"}]
    assert sctx.background_task is None


# ═══════════ (2) الثابت الصلب: waiting_approval بلا land تلقائي ═══════════

def test_cycle_ends_waiting_approval_no_auto_land():
    sctx, sent = _sctx()
    task = _launch_and_wait(sctx, sent)

    assert task.status == BG_WAITING_APPROVAL
    assert task.run is not None
    assert task.run.status == "waiting_approval"
    # لا أثر لأي هبوط: لا delegate_landed ولا done
    assert _frames(sent, "delegate_landed") == []
    assert _frames(sent, "done") == []
    # الدورة بثّت الختام بالحالة الصحيحة
    finished = _frames(sent, "background_finished")
    assert len(finished) == 1
    assert finished[0]["status"] == BG_WAITING_APPROVAL


# ═══════════ (3) background_status: snapshot كامل (reconnect-safe) ═══════════

def test_status_returns_full_snapshot():
    sctx, sent = _sctx()
    task = _launch_and_wait(sctx, sent)
    sent.clear()  # نحاكي اتصالًا أعاد فتح الصورة من الصفر

    server._handle_ws_message(None, sctx, {"type": "background_status"})

    frames = _frames(sent, "background_status")
    assert len(frames) == 1
    snap = frames[0]
    assert snap["task_id"] == task.task_id
    assert snap["status"] == BG_WAITING_APPROVAL
    assert snap["error"] == ""
    # سجل الأحداث الكامل داخل الـ snapshot (started + events + finished)
    kinds = [e["type"] for e in snap["events"]]
    assert kinds[0] == "background_started"
    assert kinds[-1] == "background_finished"
    assert snap["run"] is not None
    assert snap["run"]["status"] == "waiting_approval"


def test_status_without_task_reports_none():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "background_status"})
    assert _frames(sent, "background_status") == [
        {"type": "background_status", "task_id": None, "status": "none"}]


# ═══════════ (4) background_approve: هبوط + done + actions (golden) ═══════════

def test_approve_lands_and_emits_done_with_actions_golden():
    sctx, sent = _sctx()
    task = _launch_and_wait(sctx, sent)
    sent.clear()

    server._handle_ws_message(None, sctx, {"type": "background_approve"})

    assert task.status == BG_LANDED
    assert task.run.status == "landed"
    assert _frames(sent, "delegate_landed"), "حدث الهبوط يصل الواجهة"
    done = _frames(sent, "done")
    assert len(done) == 1
    # golden: نفس التحويل المشترك في مسار delegate_approve حرفيًا
    assert done[0]["actions"] == [{
        "action": "create_file",
        "path": "hello.html",
        "content": "<h1>مرحبا</h1>",
        "language": "html",
    }]
    assert done[0]["summary"] == (
        f"✅ تم اعتماد المهمة الخلفية (task #{task.task_id})")
    assert len(_frames(sent, "start")) == 1
    chunk = _frames(sent, "chunk")
    assert len(chunk) == 1 and chunk[0]["text"] == FILE_RESPONSE
    assert _frames(sent, "error") == []


def test_approve_without_waiting_task_errors():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "background_approve"})
    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert errors[0]["text"] == "لا توجد مهمة خلفية بانتظار الاعتماد"


def test_approve_conversion_failure_surfaces_error(monkeypatch):
    """UXF-02: فشل التحويل يُظهَر — لا صمت (مرآة مسار delegate_approve)."""
    sctx, sent = _sctx()
    _launch_and_wait(sctx, sent)
    sent.clear()

    def _boom(response, mode=None):
        raise ValueError("parser exploded")
    monkeypatch.setattr(server.parser, "parse", _boom)

    server._handle_ws_message(None, sctx, {"type": "background_approve"})

    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert "parser exploded" in errors[0]["text"]
    done = _frames(sent, "done")
    assert len(done) == 1 and done[0]["actions"] == []


# ═══════════ (5) background_reject: رفض + تحرير الخانة ═══════════

def test_reject_marks_rejected_and_frees_slot(fresh_registry):
    sctx, sent = _sctx()
    task = _launch_and_wait(sctx, sent)
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "background_reject", "reason": "غير مطلوب",
    })

    assert task.status == BG_REJECTED
    assert task.run.status == "rejected"
    assert _frames(sent, "error") == []
    # الخانة تحررت (الجسر أنهى التذكرة) — إطلاق جديد يمر بلا busy
    sctx.model_provider = FakeProvider(responses=[
        BRIEF_RESPONSE, FILE_RESPONSE, APPROVE_RESPONSE,
    ])
    task2 = _launch_and_wait(sctx, sent, text="مهمة ثانية")
    assert task2 is not task
    assert _frames(sent, "busy") == []
    assert task2.status == BG_WAITING_APPROVAL


def test_reject_without_waiting_task_errors():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "background_reject"})
    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert errors[0]["text"] == "لا توجد مهمة خلفية بانتظار الاعتماد"


# ═══════════ (6) إطلاق ثانٍ فوق waiting_approval → رفض واضح ═══════════

def test_second_launch_over_unresolved_task_is_refused():
    sctx, sent = _sctx()
    task = _launch_and_wait(sctx, sent)
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "background_delegate_message", "text": "مهمة ثانية",
    })

    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert "لم تُحسم" in errors[0]["text"]
    assert BG_WAITING_APPROVAL in errors[0]["text"]
    # المهمة الأصلية لم تُمسّ — «كائن جديد لكل مهمة» لم يُخرق
    assert sctx.background_task is task
    assert task.status == BG_WAITING_APPROVAL
    assert _frames(sent, "background_started") == []


# ═══════════ (7) تذكرة محجوزة → busy (سياسة الـ run الواحد) ═══════════

def test_busy_when_run_slot_already_held():
    sctx, sent = _sctx()
    # نحجز الخانة العالمية (لا مقبض مشروع) بتذكرة أخرى
    held = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
    assert held is not None
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "background_delegate_message", "text": "مهمة خلفية",
    })

    busy = _frames(sent, "busy")
    assert len(busy) == 1
    assert sctx.background_task is None, "لا مهمة تُنشأ عند busy"
    assert _frames(sent, "background_started") == []
