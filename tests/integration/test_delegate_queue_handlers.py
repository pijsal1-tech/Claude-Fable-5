# -*- coding: utf-8 -*-
"""TSK-733c (D-19-5): مقابض طابور التفويض الأربعة end-to-end.

يغطي المقابض الجديدة (queue_delegate_start / queue_status /
queue_land / queue_reject) بنمط test_background_delegate_handlers.py
حرفيًا: FakeProvider يقود دورات تفويض حقيقية عبر
``server._handle_ws_message`` مع ``SessionContext(send=...)``.

معايير القبول المثبّتة (من مواصفة TSK-733):
1. الإطلاق يبث ``queue_started`` ويقف عند أول waiting_approval —
   **التتابع الصارم**: المهمة 2 لا تنطلق قبل land المهمة 1
   (3 نداءات مزود فقط بعد الدورة الأولى).
2. ``queue_status`` يعيد to_dict كاملًا (reconnect-safe) + حالة none.
3. ``queue_land`` يهبط ويبث done + actions (golden مشترك مع مسار
   delegate_approve) ثم يُطلق المهمة التالية تلقائيًا.
4. اكتمال كل المهام ⇒ ``queue_completed`` والتذكرة تُحرَّر
   (لا خانة معلقة — الغلاف _queue_event_wrapper يديرها).
5. ``queue_reject`` يوقف الطابور كاملًا (halted) ويحرر التذكرة.
6. إطلاق ثانٍ فوق طابور غير محسوم يُرفض برسالة واضحة.
7. تذكرة محجوزة → إطار busy (سياسة الـ run الواحد تبقى سيدة).
8. قائمة مهام فارغة → خطأ بلا إنشاء طابور.

**قرار واعٍ** (المواصفة): DelegateQueue بلا wait() — الانتظار عبر
حلقة استقصاء (poll) على الحالة/الإطارات بمهلة — حتمي عمليًا لأن
الدورات مزيفة (صفر نداءات AI خارجية — T-002).
"""
from __future__ import annotations

import time

import pytest

import server
from chain.delegate_queue import (
    QUEUE_COMPLETED, QUEUE_HALTED, QUEUE_WAITING_APPROVAL,
    TASK_LANDED, TASK_QUEUED, TASK_REJECTED, TASK_WAITING_APPROVAL,
)
from core.execution import ExecutionRegistry
from core.session_context import SessionContext
from tests.fakes.fake_provider import FakeProvider


# نفس مهلة test_background_delegate_handlers.py — حتمية عمليًا.
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

# كل مهمة تستهلك 3 ردود (بريف + تنفيذ + مراجعة) — نمط
# tests/unit/test_delegate_queue.py حرفيًا.
ONE_TASK_RESPONSES = [BRIEF_RESPONSE, FILE_RESPONSE, APPROVE_RESPONSE]


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """عزل كل اختبار بسجل تذاكر خاص (نمط test_run_slot_per_project)."""
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


def _sctx(tasks_count=1):
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    # المزود المبرمج عبر خيار التبويب (يتقدّم على provider_source)
    sctx.model_provider = FakeProvider(
        responses=ONE_TASK_RESPONSES * tasks_count)
    return sctx, sent


def _frames(sent, ftype):
    return [f for f in sent if f.get("type") == ftype]


def _wait_until(predicate, timeout=JOIN_TIMEOUT, interval=0.02):
    """استقصاء بمهلة — بديل wait() الغائبة عن DelegateQueue."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def _launch_and_wait(sctx, sent, tasks=("أنشئ صفحة ترحيب",)):
    """يطلق طابورًا وينتظر توقفه عند أول waiting_approval."""
    server._handle_ws_message(None, sctx, {
        "type": "queue_delegate_start", "tasks": list(tasks),
    })
    q = sctx.delegate_queue
    assert q is not None, "الطابور لم يُنشأ"
    assert _wait_until(lambda: q.status in (
        QUEUE_WAITING_APPROVAL, QUEUE_COMPLETED, QUEUE_HALTED,
    )), "دورة المهمة الأولى لم تنتهِ في المهلة"
    return q


def _land_and_wait(sctx, sent, done_count):
    """يعتمد المهمة الحالية وينتظر إطار done رقم ``done_count``."""
    server._handle_ws_message(None, sctx, {"type": "queue_land"})
    q = sctx.delegate_queue
    assert _wait_until(lambda: len(_frames(sent, "done")) >= done_count
                       and q.status in (QUEUE_WAITING_APPROVAL,
                                        QUEUE_COMPLETED, QUEUE_HALTED)), \
        "دورة الهبوط لم تنتهِ في المهلة"


# ═══════ (1) الإطلاق: queue_started + توقف عند waiting_approval ═══════

def test_launch_emits_queue_started_and_stops_at_waiting_approval():
    sctx, sent = _sctx(tasks_count=2)
    q = _launch_and_wait(sctx, sent, tasks=["مهمة أولى", "مهمة ثانية"])

    started = _frames(sent, "queue_started")
    assert len(started) == 1
    assert started[0]["tasks_count"] == 2
    assert started[0]["task_ids"] == [t.task_id for t in q.tasks]

    # التتابع الصارم: المهمة 1 فقط استهلكت المزود (3 نداءات) —
    # المهمة 2 لم تنطلق قبل land (المرجع multi-task-queues.md).
    assert q.status == QUEUE_WAITING_APPROVAL
    assert len(sctx.model_provider.calls) == 3
    assert q.tasks[0].status == TASK_WAITING_APPROVAL
    assert q.tasks[1].status == TASK_QUEUED
    waiting = _frames(sent, "queue_task_waiting_approval")
    assert len(waiting) == 1
    assert waiting[0]["task_id"] == q.tasks[0].task_id
    # الثابت الصلب (لا YOLO): لا هبوط تلقائي — لا done ولا landed
    assert _frames(sent, "done") == []
    assert _frames(sent, "queue_task_landed") == []


def test_launch_empty_tasks_errors_without_queue():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {
        "type": "queue_delegate_start", "tasks": ["   ", ""],
    })
    assert _frames(sent, "error") == [
        {"type": "error",
         "text": "قائمة المهام فارغة — مهمة واحدة على الأقل"}]
    assert sctx.delegate_queue is None


# ═══════ (2) queue_status: صورة to_dict كاملة (reconnect-safe) ═══════

def test_status_returns_full_to_dict():
    sctx, sent = _sctx()
    q = _launch_and_wait(sctx, sent)
    sent.clear()  # نحاكي اتصالًا أعاد فتح الصورة من الصفر

    server._handle_ws_message(None, sctx, {"type": "queue_status"})

    frames = _frames(sent, "queue_status")
    assert len(frames) == 1
    snap = frames[0]
    assert snap["status"] == QUEUE_WAITING_APPROVAL
    assert snap["current_index"] == 0
    assert snap["halt_reason"] == ""
    assert len(snap["tasks"]) == 1
    assert snap["tasks"][0]["task_id"] == q.tasks[0].task_id
    assert snap["tasks"][0]["status"] == TASK_WAITING_APPROVAL
    assert snap["tasks"][0]["run"]["status"] == "waiting_approval"


def test_status_without_queue_reports_none():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "queue_status"})
    assert _frames(sent, "queue_status") == [
        {"type": "queue_status", "status": "none", "tasks": []}]


# ═══════ (3) queue_land: done + actions ثم انطلاق المهمة التالية ═══════

def test_land_emits_done_actions_golden_then_next_task_starts():
    sctx, sent = _sctx(tasks_count=2)
    q = _launch_and_wait(sctx, sent, tasks=["مهمة أولى", "مهمة ثانية"])
    first_task_id = q.tasks[0].task_id
    sent.clear()

    _land_and_wait(sctx, sent, done_count=1)

    # الهبوط: golden — نفس التحويل المشترك في مسار delegate_approve
    assert q.tasks[0].status == TASK_LANDED
    done = _frames(sent, "done")
    assert len(done) == 1
    assert done[0]["actions"] == [{
        "action": "create_file",
        "path": "hello.html",
        "content": "<h1>مرحبا</h1>",
        "language": "html",
    }]
    assert done[0]["summary"] == (
        f"✅ اعتُمدت مهمة الطابور (task #{first_task_id})")
    assert len(_frames(sent, "start")) == 1
    chunk = _frames(sent, "chunk")
    assert len(chunk) == 1 and chunk[0]["text"] == FILE_RESPONSE
    landed = _frames(sent, "queue_task_landed")
    assert len(landed) == 1 and landed[0]["task_id"] == first_task_id

    # التتابع: المهمة 2 انطلقت تلقائيًا بعد الهبوط ووقفت بدورها
    assert q.status == QUEUE_WAITING_APPROVAL
    assert q.tasks[1].status == TASK_WAITING_APPROVAL
    assert len(sctx.model_provider.calls) == 6
    assert _frames(sent, "error") == []


def test_land_without_waiting_queue_errors():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "queue_land"})
    assert _frames(sent, "error") == [
        {"type": "error", "text": "لا طابور بمهمة بانتظار الاعتماد"}]


# ═══════ (4) الاكتمال: queue_completed + تحرير التذكرة ═══════

def test_full_completion_emits_queue_completed_and_frees_ticket():
    sctx, sent = _sctx(tasks_count=2)
    q = _launch_and_wait(sctx, sent, tasks=["مهمة أولى", "مهمة ثانية"])

    _land_and_wait(sctx, sent, done_count=1)
    _land_and_wait(sctx, sent, done_count=2)

    assert q.status == QUEUE_COMPLETED
    assert [t.status for t in q.tasks] == [TASK_LANDED, TASK_LANDED]
    completed = _frames(sent, "queue_completed")
    assert len(completed) == 1
    assert completed[0]["tasks_count"] == 2

    # التذكرة تحررت (الغلاف أنهاها completed) — لا خانة معلقة:
    # حجز جديد يمر بلا busy (معيار قبول المواصفة).
    sent.clear()
    new_ticket = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
    assert new_ticket is not None
    assert _frames(sent, "busy") == []
    new_ticket.finish("completed")


# ═══════ (5) queue_reject: إيقاف كامل + تحرير التذكرة ═══════

def test_reject_halts_queue_and_frees_ticket():
    sctx, sent = _sctx(tasks_count=2)
    q = _launch_and_wait(sctx, sent, tasks=["مهمة أولى", "مهمة ثانية"])
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "queue_reject", "reason": "غير مطلوب",
    })

    # stop-and-ask: الرفض يوقف الطابور كاملًا — المهمة 2 تبقى queued
    assert q.status == QUEUE_HALTED
    assert q.tasks[0].status == TASK_REJECTED
    assert q.tasks[1].status == TASK_QUEUED
    assert "غير مطلوب" in q.halt_reason
    halted = _frames(sent, "queue_halted")
    assert len(halted) == 1
    assert halted[0]["remaining"] == [q.tasks[1].task_id]
    assert _frames(sent, "error") == []

    # التذكرة تحررت (الغلاف أنهاها failed) — حجز جديد يمر بلا busy
    sent.clear()
    new_ticket = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
    assert new_ticket is not None
    assert _frames(sent, "busy") == []
    new_ticket.finish("completed")


def test_reject_without_waiting_queue_errors():
    sctx, sent = _sctx()
    server._handle_ws_message(None, sctx, {"type": "queue_reject"})
    assert _frames(sent, "error") == [
        {"type": "error", "text": "لا طابور بمهمة بانتظار الاعتماد"}]


# ═══════ (6) إطلاق ثانٍ فوق طابور غير محسوم → رفض واضح ═══════

def test_second_launch_over_unresolved_queue_is_refused():
    sctx, sent = _sctx()
    q = _launch_and_wait(sctx, sent)
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "queue_delegate_start", "tasks": ["خطة ثانية"],
    })

    errors = _frames(sent, "error")
    assert len(errors) == 1
    assert "لم يُحسم" in errors[0]["text"]
    assert QUEUE_WAITING_APPROVAL in errors[0]["text"]
    # الطابور الأصلي لم يُمسّ — «طابور جديد لخطة جديدة» لم يُخرق
    assert sctx.delegate_queue is q
    assert q.status == QUEUE_WAITING_APPROVAL
    assert _frames(sent, "queue_started") == []


# ═══════ (7) تذكرة محجوزة → busy (سياسة الـ run الواحد) ═══════

def test_busy_when_run_slot_already_held():
    sctx, sent = _sctx()
    # نحجز الخانة العالمية (لا مقبض مشروع) بتذكرة أخرى
    held = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
    assert held is not None
    sent.clear()

    server._handle_ws_message(None, sctx, {
        "type": "queue_delegate_start", "tasks": ["مهمة"],
    })

    busy = _frames(sent, "busy")
    assert len(busy) == 1
    assert sctx.delegate_queue is None, "لا طابور يُنشأ عند busy"
    assert _frames(sent, "queue_started") == []
