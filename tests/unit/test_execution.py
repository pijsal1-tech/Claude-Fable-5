# -*- coding: utf-8 -*-
"""T-014: ExecutionRegistry + RunTicket unit tests (R-105).

يغطي: دورة الحياة register/cancel/finish، الاستبعاد المتبادل لكل مشروع،
التسجيل المتزامن (فائز واحد بالضبط)، النبض وحصاد TTL، وثبات الحالات
النهائية.
"""
import threading

import pytest

from core.execution import (
    STATE_RUNNING,
    TERMINAL_STATES,
    ExecutionRegistry,
    RunBusyError,
    RunTicket,
)


class FakeClock:
    """ساعة قابلة للتقديم اليدوي — لاختبارات TTL بلا نوم حقيقي."""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ═══════════════════════ دورة الحياة الأساسية ═══════════════════════

def test_register_returns_running_ticket():
    reg = ExecutionRegistry()
    t = reg.register("chain", "proj-A")
    assert isinstance(t, RunTicket)
    assert t.state == STATE_RUNNING
    assert t.kind == "chain"
    assert t.project_id == "proj-A"
    assert t.run_id  # non-empty unique id
    assert t.is_cancelled is False
    assert t.is_terminal is False
    assert t.finished_at is None


def test_register_rejects_unknown_kind():
    reg = ExecutionRegistry()
    with pytest.raises(ValueError):
        reg.register("banana", "proj-A")


def test_finish_completed_lifecycle():
    reg = ExecutionRegistry()
    t = reg.register("agent", "proj-A")
    assert t.finish("completed") is True
    assert t.state == "completed"
    assert t.is_terminal is True
    assert t.finished_at is not None
    assert reg.list_active() == []


def test_finish_rejects_invalid_status():
    reg = ExecutionRegistry()
    t = reg.register("chain", "proj-A")
    with pytest.raises(ValueError):
        t.finish("exploded")
    assert t.state == STATE_RUNNING  # untouched


def test_terminal_state_is_immutable():
    """لا double-finish ولا cancel بعد النهاية — الحالات النهائية صخر."""
    reg = ExecutionRegistry()
    t = reg.register("chain", "proj-A")
    assert t.finish("failed") is True
    assert t.finish("completed") is False        # no re-finish
    assert t.state == "failed"
    assert reg.cancel(t.run_id) is False         # no cancel-after-finish
    assert t.is_cancelled is False
    assert t.heartbeat() is False                # late heartbeat can't revive


def test_finish_unknown_run_returns_false():
    reg = ExecutionRegistry()
    assert reg.finish("no-such-run", "completed") is False


# ═══════════════════════ الإلغاء التعاوني ═══════════════════════

def test_cancel_raises_flag_but_keeps_running():
    """الإلغاء تعاوني: العلم يُرفع لكن الحالة تبقى running حتى يلاحظه المنفّذ."""
    reg = ExecutionRegistry()
    t = reg.register("delegate", "proj-A")
    assert t.cancel("user clicked stop") is True
    assert t.is_cancelled is True
    assert t.cancel_reason == "user clicked stop"
    assert t.state == STATE_RUNNING              # honest: still executing
    assert t in reg.list_active()
    # المنفّذ يلاحظ العلم عند نقطة تفتيش وينهي بنفسه
    assert t.finish("cancelled") is True
    assert t.state == "cancelled"
    assert reg.list_active() == []


def test_cancel_first_reason_wins():
    reg = ExecutionRegistry()
    t = reg.register("chain", "proj-A")
    assert t.cancel("first") is True
    assert t.cancel("second") is True            # still running → True
    assert t.cancel_reason == "first"            # reason not overwritten


def test_cancel_unknown_or_finished_returns_false():
    reg = ExecutionRegistry()
    assert reg.cancel("ghost") is False
    t = reg.register("chain", "proj-A")
    t.finish("completed")
    assert reg.cancel(t.run_id) is False


# ═══════════════════ الاستعلام: lookup / list ═══════════════════

def test_lookup_and_list_reflect_live_state():
    """معيار القبول: list يعكس الحالة الحية."""
    reg = ExecutionRegistry(exclusive_per_project=False)
    t1 = reg.register("chain", "proj-A")
    t2 = reg.register("agent", "proj-A")
    t3 = reg.register("delegate", "proj-B")
    assert reg.lookup(t2.run_id) is t2
    assert reg.lookup("missing") is None
    assert set(t.run_id for t in reg.list_active()) == {
        t1.run_id, t2.run_id, t3.run_id
    }
    t2.finish("completed")
    t3.finish("failed")
    assert [t.run_id for t in reg.list_active()] == [t1.run_id]
    # list_all يحتفظ بالمنتهين للتدقيق
    assert len(reg.list_all()) == 3


def test_to_dict_snapshot():
    reg = ExecutionRegistry(clock=FakeClock(500.0))
    t = reg.register("chain", "proj-A")
    t.cancel("why")
    d = t.to_dict()
    assert d["run_id"] == t.run_id
    assert d["kind"] == "chain"
    assert d["project_id"] == "proj-A"
    assert d["state"] == STATE_RUNNING
    assert d["is_cancelled"] is True
    assert d["cancel_reason"] == "why"
    assert d["created_at"] == 500.0
    assert d["finished_at"] is None


# ═══════════════ الاستبعاد المتبادل لكل مشروع ═══════════════

def test_exclusive_second_register_same_project_busy():
    reg = ExecutionRegistry()  # exclusive by default
    t1 = reg.register("chain", "proj-A")
    with pytest.raises(RunBusyError) as exc:
        reg.register("agent", "proj-A")
    assert exc.value.project_id == "proj-A"
    assert exc.value.active_run_id == t1.run_id


def test_exclusive_different_projects_coexist():
    reg = ExecutionRegistry()
    t1 = reg.register("chain", "proj-A")
    t2 = reg.register("chain", "proj-B")
    assert {t.run_id for t in reg.list_active()} == {t1.run_id, t2.run_id}


def test_finish_frees_project_slot():
    reg = ExecutionRegistry()
    t1 = reg.register("chain", "proj-A")
    t1.finish("completed")
    t2 = reg.register("agent", "proj-A")         # slot freed → allowed
    assert t2.state == STATE_RUNNING


def test_non_exclusive_mode_allows_parallel_runs():
    reg = ExecutionRegistry(exclusive_per_project=False)
    reg.register("chain", "proj-A")
    reg.register("chain", "proj-A")              # no RunBusyError
    assert len(reg.list_active()) == 2


# ═══════════════════ التسجيل المتزامن ═══════════════════

def test_concurrent_registration_exactly_one_winner():
    """اختبار متطلب T-014: تحت سباق حقيقي فائز واحد بالضبط لكل مشروع."""
    reg = ExecutionRegistry()
    winners: list[RunTicket] = []
    busy_count = [0]
    lock = threading.Lock()
    barrier = threading.Barrier(16)

    def worker():
        barrier.wait()                            # thundering herd
        try:
            t = reg.register("chain", "proj-race")
            with lock:
                winners.append(t)
        except RunBusyError:
            with lock:
                busy_count[0] += 1

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(winners) == 1
    assert busy_count[0] == 15
    assert reg.list_active() == [winners[0]]


def test_concurrent_cancel_and_finish_consistent():
    """cancel وfinish من خيطين — النتيجة دائمًا حالة نهائية واحدة سليمة."""
    reg = ExecutionRegistry()
    t = reg.register("chain", "proj-A")
    barrier = threading.Barrier(2)

    def do_cancel():
        barrier.wait()
        reg.cancel(t.run_id, "race")

    def do_finish():
        barrier.wait()
        reg.finish(t.run_id, "completed")

    th1 = threading.Thread(target=do_cancel)
    th2 = threading.Thread(target=do_finish)
    th1.start(); th2.start(); th1.join(); th2.join()

    assert t.state == "completed"                # finish won the transition
    assert reg.list_active() == []


# ═══════════════════ النبض وحصاد TTL ═══════════════════

def test_heartbeat_updates_timestamp():
    clock = FakeClock(100.0)
    reg = ExecutionRegistry(clock=clock)
    t = reg.register("chain", "proj-A")
    assert t.last_heartbeat == 100.0
    clock.advance(5)
    assert t.heartbeat() is True
    assert t.last_heartbeat == 105.0


def test_reap_stale_force_fails_dead_runs():
    clock = FakeClock(0.0)
    reg = ExecutionRegistry(ttl_seconds=30.0, clock=clock)
    dead = reg.register("chain", "proj-A")
    alive = reg.register("agent", "proj-B")
    clock.advance(20)
    alive.heartbeat()                             # alive keeps beating
    clock.advance(15)                             # dead: 35s silent > 30 TTL
    reaped = reg.reap_stale()
    assert reaped == [dead]
    assert dead.state == "failed"
    assert dead.cancel_reason.startswith("stale")
    assert alive.state == STATE_RUNNING
    # خانة المشروع تحررت — يمكن تسجيل run جديد لنفس المشروع
    replacement = reg.register("chain", "proj-A")
    assert replacement.state == STATE_RUNNING


def test_reap_noop_without_ttl():
    clock = FakeClock(0.0)
    reg = ExecutionRegistry(clock=clock)          # ttl=None
    reg.register("chain", "proj-A")
    clock.advance(10_000)
    assert reg.reap_stale() == []
    assert len(reg.list_active()) == 1


def test_registry_rejects_nonpositive_ttl():
    with pytest.raises(ValueError):
        ExecutionRegistry(ttl_seconds=0)
    with pytest.raises(ValueError):
        ExecutionRegistry(ttl_seconds=-5)


def test_terminal_states_constant_shape():
    """عقد ثابت للطبقات الأعلى (T-015): الحالات النهائية الثلاث فقط."""
    assert set(TERMINAL_STATES) == {"completed", "failed", "cancelled"}
