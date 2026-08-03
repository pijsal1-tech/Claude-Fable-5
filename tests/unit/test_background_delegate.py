# -*- coding: utf-8 -*-
"""اختبارات TSK-CEV-113 (FI-15): BackgroundDelegateTask — التفويض الخلفي.

حتمية بالكامل (P-11: FakeProvider مبرمج — صفر نداء نموذج حقيقي؛
التزامن مضبوط بـthreading.Event لا بأزمنة نوم اعتباطية).
تثبت الانضباط المرجعي (dispatch-and-poll.md) والثابت الصلب:
- hand-off: start() يرجع قبل اكتمال الدورة (الدورة محجوزة بحدث).
- **لا YOLO (Non-Goal §15.1)**: الوصول لـwaiting_approval يبقى بلا
  أي land تلقائي — الكتابة خلف land()/reject() الصريحين حصريًا.
- reconnect-safe: snapshot() يعيد الحالة والأحداث كاملة من الكائن الحي.
- فشل المزود = failed بلا استثناء هارب من الخيط.
- صفر تعديل على DelegateBridge (يُستعمل كما هو).
"""
import pathlib
import sys
import threading

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.delegate import DelegateBridge                     # noqa: E402
from chain.background_delegate import (                       # noqa: E402
    BG_FAILED,
    BG_IDLE,
    BG_LANDED,
    BG_REJECTED,
    BG_RUNNING,
    BG_WAITING_APPROVAL,
    BackgroundDelegateTask,
)
from tests.fakes.fake_provider import FakeProvider            # noqa: E402

# دورة تفويض واحدة تستهلك 3 ردود: brief ثم implement ثم review.
APPROVE_REVIEW = "[VERDICT]: APPROVE\n[SUMMARY]: عمل سليم"
IMPL = "نفذت المطلوب\n[TOUCHED]: src/utils.py"

#: مهلة join سخية — الاختبار حتمي (الحدث يُطلق صراحة)، المهلة
#: مجرد سياج ضد جمود لا-نهائي في حال كسر مستقبلي.
JOIN_TIMEOUT = 10.0


def _task_with(responses=None, responder=None):
    provider = FakeProvider(responses=responses, responder=responder)
    bridge = DelegateBridge(provider)
    return BackgroundDelegateTask(bridge), provider


class TestHandOff:
    def test_start_returns_before_cycle_completes(self):
        """hand-off حقيقي: الدورة محجوزة بحدث — start() يرجع والحالة
        running والخيط حي؛ ثم يُطلق الحدث وتكتمل الدورة."""
        gate = threading.Event()
        replies = iter(["brief-1", IMPL, APPROVE_REVIEW])

        def responder(prompt, history, system_prompt):
            gate.wait(JOIN_TIMEOUT)  # يحجز الدورة حتى يأذن الاختبار
            return next(replies)

        task, provider = _task_with(responder=responder)
        task.start("أضف helper", {"src/utils.py": "def x(): pass"})
        # رجعنا فورًا والدورة معلقة على الحدث
        assert task.status == BG_RUNNING
        assert task.is_running is True
        gate.set()
        assert task.wait(JOIN_TIMEOUT) is True
        assert task.status == BG_WAITING_APPROVAL

    def test_start_twice_rejected(self):
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("مهمة")
        task.wait(JOIN_TIMEOUT)
        with pytest.raises(RuntimeError):
            task.start("مهمة ثانية")


class TestHardInvariantNoYolo:
    def test_waiting_approval_is_terminal_without_explicit_land(self):
        """الثابت الصلب: بعد انتهاء الخيط عند waiting_approval لا يحدث
        أي land تلقائي — حالة الجسر والمهمة تبقيان معلّقتين."""
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("أضف helper")
        assert task.wait(JOIN_TIMEOUT) is True
        assert task.status == BG_WAITING_APPROVAL
        assert task.run is not None
        assert task.run.status == "waiting_approval"
        # لا حدث delegate_landed في السجل — صفر هبوط تلقائي
        snap = task.snapshot()
        bridge_events = [e["event"] for e in snap["events"]
                         if e["type"] == "background_event"]
        assert "delegate_landed" not in bridge_events

    def test_explicit_land_works(self):
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("أضف helper")
        task.wait(JOIN_TIMEOUT)
        assert task.land() is True
        assert task.status == BG_LANDED
        assert task.run.status == "landed"

    def test_explicit_reject_works(self):
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("أضف helper")
        task.wait(JOIN_TIMEOUT)
        assert task.reject("قرار المستخدم") is True
        assert task.status == BG_REJECTED
        assert task.run.status == "rejected"

    def test_land_before_waiting_is_noop(self):
        """لا يمكن الهبوط قبل وصول الدورة للبوابة (يورث حماية الجسر)."""
        task, _ = _task_with(responses=[])
        assert task.land() is False
        assert task.status == BG_IDLE


class TestReconnectSafeSnapshot:
    def test_snapshot_has_full_state_and_events(self):
        """عميل أعاد الاتصال يقرأ الصورة كاملة من الكائن الحي —
        بلا اعتماد على ما بثّته الجلسة المقطوعة."""
        # الجلسة "الأولى" مرَّرت on_event؛ ثم "انقطعت" — snapshot
        # يعوض كل ما فات.
        seen_live: list[str] = []
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("أضف helper", {"src/utils.py": "x"},
                    on_event=lambda et, d: seen_live.append(et))
        task.wait(JOIN_TIMEOUT)

        snap = task.snapshot()
        assert snap["task_id"] == task.task_id
        assert snap["status"] == BG_WAITING_APPROVAL
        assert snap["run"] is not None
        assert snap["run"]["status"] == "waiting_approval"
        types = [e["type"] for e in snap["events"]]
        assert types[0] == "background_started"
        assert types[-1] == "background_finished"
        # أحداث الجسر مسجلة (started/phase/review/waiting...)
        bridge_events = [e["event"] for e in snap["events"]
                         if e["type"] == "background_event"]
        assert "delegate_started" in bridge_events
        # الجسر يبثّ الحكم عبر delegate_review (لا حدث waiting مستقل)
        assert "delegate_review" in bridge_events
        # snapshot أوسع أو مساوٍ لما بُثّ حيًّا — لا فقد
        assert len(snap["events"]) >= len(seen_live)

    def test_snapshot_events_are_copies(self):
        """طفر نسخة الـsnapshot لا يلوث السجل الداخلي."""
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("مهمة")
        task.wait(JOIN_TIMEOUT)
        snap1 = task.snapshot()
        snap1["events"][0]["type"] = "tampered"
        snap2 = task.snapshot()
        assert snap2["events"][0]["type"] == "background_started"


class TestFailurePath:
    def test_provider_failure_becomes_failed_no_escape(self):
        """فشل المزود = failed — لا استثناء يهرب من الخيط الخلفي."""
        task, provider = _task_with(responses=[])
        provider.fail_always = ValueError("dead provider")
        task.start("مهمة")
        assert task.wait(JOIN_TIMEOUT) is True
        assert task.status == BG_FAILED
        snap = task.snapshot()
        assert snap["events"][-1]["type"] == "background_finished"
        assert snap["events"][-1]["status"] == BG_FAILED

    def test_listener_failure_does_not_break_cycle(self):
        """فشل مستمع الأحداث لا يفجّر الدورة (نمط _emit القائم)."""
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])

        def bad_listener(et, d):
            raise RuntimeError("listener boom")

        task.start("مهمة", on_event=bad_listener)
        assert task.wait(JOIN_TIMEOUT) is True
        assert task.status == BG_WAITING_APPROVAL


class TestEventOrder:
    def test_wrapper_event_order(self):
        task, _ = _task_with(responses=["b", IMPL, APPROVE_REVIEW])
        task.start("مهمة")
        task.wait(JOIN_TIMEOUT)
        types = [e["type"] for e in task.snapshot()["events"]]
        # started أولًا، finished أخيرًا، وبينهما أحداث جسر فقط
        assert types[0] == "background_started"
        assert types[-1] == "background_finished"
        assert set(types[1:-1]) == {"background_event"}


class TestBridgeAndQueueUntouched:
    def test_delegate_module_not_modified(self):
        """TSK-CEV-113 حد واعٍ: صفر مساس بـdelegate.py وdelegate_queue.py."""
        src_bridge = (REPO_ROOT / "chain" / "delegate.py").read_text(
            encoding="utf-8")
        assert "background_delegate" not in src_bridge
        assert "BackgroundDelegateTask" not in src_bridge
        src_queue = (REPO_ROOT / "chain" / "delegate_queue.py").read_text(
            encoding="utf-8")
        assert "background_delegate" not in src_queue
        assert "BackgroundDelegateTask" not in src_queue
