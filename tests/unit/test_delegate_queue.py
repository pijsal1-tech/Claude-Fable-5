# -*- coding: utf-8 -*-
"""اختبارات TSK-CEV-112 (FI-13): DelegateQueue — طوابير التفويض.

حتمية بالكامل (P-11: FakeProvider مبرمج — صفر نداء نموذج حقيقي).
تثبت الانضباط المرجعي (multi-task-queues.md):
- تتابع صارم: المهمة 2 لا ترى أي provider call قبل land المهمة 1.
- carry-forward: بريف المهمة اللاحقة يحمل كتلة القيود بحقائق السابقة.
- بوابة الموافقة سيدة: waiting_approval يوقف الطابور حتى الحسم.
- رفض/فشل = halt — لا تقدّم صامت حول افتراض مكسور.
- صفر تعديل على DelegateBridge (يُستعمل كما هو).
"""
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.delegate import DelegateBridge                     # noqa: E402
from chain.delegate_queue import (                            # noqa: E402
    CARRY_HEADER,
    DelegateQueue,
    QUEUE_COMPLETED,
    QUEUE_HALTED,
    QUEUE_IDLE,
    QUEUE_WAITING_APPROVAL,
    TASK_LANDED,
    TASK_QUEUED,
    TASK_REJECTED,
    TASK_WAITING_APPROVAL,
)
from tests.fakes.fake_provider import FakeProvider            # noqa: E402


# كل مهمة تستهلك 3 ردود: brief ثم implement ثم review.
APPROVE_REVIEW = "[VERDICT]: APPROVE\n[SUMMARY]: عمل سليم"
REJECT_REVIEW = "[VERDICT]: REJECT\n[SUMMARY]: خارج النطاق"

IMPL_T1 = (
    "نفذت المهمة الأولى: أضفت الدالة helper_alpha في utils.py\n"
    "[TOUCHED]: src/utils.py"
)
IMPL_T2 = "نفذت المهمة الثانية باستخدام helper_alpha\n[TOUCHED]: src/app.py"


def _queue_with(responses):
    provider = FakeProvider(responses=responses)
    bridge = DelegateBridge(provider)
    return DelegateQueue(bridge), provider


def _two_task_queue(responses):
    q, provider = _queue_with(responses)
    q.add_task("مهمة 1: أضف helper", {"src/utils.py": "def x(): pass"})
    q.add_task("مهمة 2: استخدم الـ helper", {"src/app.py": "print(1)"})
    return q, provider


class TestSequencing:
    def test_starts_first_task_and_stops_at_approval_gate(self):
        q, provider = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start()
        # 3 نداءات فقط (مهمة 1) — المهمة 2 لم تُرسل
        assert len(provider.calls) == 3
        assert q.status == QUEUE_WAITING_APPROVAL
        assert q.tasks[0].status == TASK_WAITING_APPROVAL
        assert q.tasks[1].status == TASK_QUEUED

    def test_second_task_dispatches_only_after_land(self):
        q, provider = _two_task_queue([
            "brief-1", IMPL_T1, APPROVE_REVIEW,
            "brief-2", IMPL_T2, APPROVE_REVIEW,
        ])
        q.start()
        calls_before_land = len(provider.calls)
        assert q.land_current() is True
        # المهمة 2 انطلقت بعد الهبوط فقط
        assert len(provider.calls) == calls_before_land + 3
        assert q.tasks[0].status == TASK_LANDED
        assert q.tasks[1].status == TASK_WAITING_APPROVAL
        assert q.status == QUEUE_WAITING_APPROVAL

    def test_queue_completes_after_all_land(self):
        q, _ = _two_task_queue([
            "brief-1", IMPL_T1, APPROVE_REVIEW,
            "brief-2", IMPL_T2, APPROVE_REVIEW,
        ])
        q.start()
        assert q.land_current() is True
        assert q.land_current() is True
        assert q.status == QUEUE_COMPLETED
        assert all(t.status == TASK_LANDED for t in q.tasks)


class TestCarryForward:
    def test_second_brief_contains_carry_block_with_task1_facts(self):
        q, provider = _two_task_queue([
            "brief-1", IMPL_T1, APPROVE_REVIEW,
            "brief-2", IMPL_T2, APPROVE_REVIEW,
        ])
        q.start(project_context="مشروع بايثون صغير")
        q.land_current()
        # النداء الرابع = brief المهمة 2 — يجب أن يحمل كتلة الترحيل
        brief2_prompt = provider.calls[3].prompt
        assert CARRY_HEADER in brief2_prompt
        assert "src/utils.py" in brief2_prompt          # touched files
        assert "helper_alpha" in brief2_prompt          # implementer summary
        assert "مشروع بايثون صغير" in brief2_prompt      # الأساس محفوظ

    def test_no_carry_block_for_first_task(self):
        q, provider = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start(project_context="سياق أساسي")
        brief1_prompt = provider.calls[0].prompt
        assert CARRY_HEADER not in brief1_prompt
        assert "سياق أساسي" in brief1_prompt

    def test_carried_facts_recorded_on_task(self):
        q, _ = _two_task_queue([
            "brief-1", IMPL_T1, APPROVE_REVIEW,
            "brief-2", IMPL_T2, APPROVE_REVIEW,
        ])
        q.start()
        q.land_current()
        facts = q.tasks[0].carried_facts
        assert any("src/utils.py" in f for f in facts)


class TestHaltDiscipline:
    def test_user_reject_halts_queue(self):
        q, provider = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start()
        assert q.reject_current("لا أريد هذا التغيير") is True
        assert q.status == QUEUE_HALTED
        assert q.tasks[0].status == TASK_REJECTED
        assert q.tasks[1].status == TASK_QUEUED       # بقيت بلا إرسال
        assert len(provider.calls) == 3               # صفر نداء إضافي
        assert "لا أريد هذا التغيير" in q.halt_reason

    def test_reviewer_reject_halts_queue(self):
        q, provider = _two_task_queue(
            ["brief-1", IMPL_T1, REJECT_REVIEW])
        q.start()
        assert q.status == QUEUE_HALTED
        assert q.tasks[0].status == TASK_REJECTED
        assert q.tasks[1].status == TASK_QUEUED
        assert len(provider.calls) == 3

    def test_land_current_invalid_when_not_waiting(self):
        q, _ = _two_task_queue(
            ["brief-1", IMPL_T1, REJECT_REVIEW])
        q.start()
        assert q.land_current() is False
        assert q.reject_current() is False


class TestQueueLifecycle:
    def test_add_after_start_rejected(self):
        q, _ = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start()
        with pytest.raises(RuntimeError):
            q.add_task("مهمة متسللة")

    def test_empty_queue_start_rejected(self):
        q, _ = _queue_with([])
        with pytest.raises(RuntimeError):
            q.start()

    def test_double_start_rejected(self):
        q, _ = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start()
        with pytest.raises(RuntimeError):
            q.start()

    def test_initial_state(self):
        q, _ = _queue_with([])
        assert q.status == QUEUE_IDLE
        assert q.current_task is None
        assert q.to_dict()["tasks"] == []


class TestEvents:
    def test_event_order_full_happy_path(self):
        events = []
        q, _ = _two_task_queue([
            "brief-1", IMPL_T1, APPROVE_REVIEW,
            "brief-2", IMPL_T2, APPROVE_REVIEW,
        ])
        q.start(on_event=lambda t, d: events.append(t))
        q.land_current()
        q.land_current()
        queue_events = [e for e in events if e.startswith("queue_")]
        assert queue_events == [
            "queue_started",
            "queue_task_started",
            "queue_task_waiting_approval",
            "queue_task_landed",
            "queue_task_started",
            "queue_task_waiting_approval",
            "queue_task_landed",
            "queue_completed",
        ]

    def test_halt_event_carries_remaining(self):
        captured = {}

        def sink(t, d):
            if t == "queue_halted":
                captured.update(d)

        q, _ = _two_task_queue(
            ["brief-1", IMPL_T1, REJECT_REVIEW])
        q.start(on_event=sink)
        assert captured["remaining"] == [q.tasks[1].task_id]

    def test_broken_callback_does_not_crash(self):
        def bomb(t, d):
            raise ValueError("boom")

        q, _ = _two_task_queue(
            ["brief-1", IMPL_T1, APPROVE_REVIEW])
        q.start(on_event=bomb)          # لا انفجار
        assert q.status == QUEUE_WAITING_APPROVAL


class TestBridgeUntouched:
    def test_delegate_module_not_modified_by_queue_import(self):
        """TSK-CEV-112 حد واعٍ: الطابور طبقة فوق الجسر — delegate.py
        لا يعرف شيئًا عن الطوابير (صفر ذكر queue فيه)."""
        src = (REPO_ROOT / "chain" / "delegate.py").read_text(
            encoding="utf-8")
        assert "delegate_queue" not in src
        assert "DelegateQueue" not in src
