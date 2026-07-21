# -*- coding: utf-8 -*-
"""T-110 (R-804): Worker Process + Per-Project Lease — أدلة القبول.

Acceptance Criteria (حرفيًّا):
- chain run dispatched to a worker completes with events arriving at
  the server — E2E: WorkerDispatchClient يضع الطلب، Worker حقيقي في
  خيط منفصل (يحاكي عملية أخرى — نفس نموذج T-109) يستهلكه وينفّذ
  EchoRunner ويبث الأحداث، والعميل يعيد بثّها على الـ sink المحلي.
- two workers + one project → exactly one holds the lease.
- lease TTL expiry after worker kill lets the second worker take over
  — «القتل» = عدم تجديد (العامل الميت لا يجدد بالتعريف).
- ``dispatch: in-proc`` (default) byte-identical to pre-task behavior
  — resolve_dispatch_mode(None) = in-proc، والمنفّذ المُختار هو
  ChainRunner التاريخي **نفسه** (النوع لا غلاف).

كل اختبارات Redis ضد خدمة **حقيقية** (نفس نمط skipif من T-109) بعزل
مفاتيح uuid لكل اختبار — لا flushdb.
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest

from core.execution import ExecutionRegistry
from core.lease import ProjectLease
from core.runner import (
    EVENT_RUN_FINISHED,
    EVENT_RUN_OUTPUT,
    EVENT_RUN_STARTED,
    RESULT_COMPLETED,
    RunEvent,
    RunRequest,
)
from worker import (
    DEFAULT_DISPATCH,
    KNOWN_DISPATCH_MODES,
    Worker,
    WorkerDispatchClient,
    resolve_dispatch_mode,
)


def _redis_available() -> bool:
    try:
        import redis
        redis.Redis.from_url("redis://localhost:6379/0",
                             socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


REDIS_UP = _redis_available()
needs_redis = pytest.mark.skipif(
    not REDIS_UP, reason="Redis غير متاح محليًّا — يعمل في CI (service)")


def _client():
    from core.backends_redis import redis_client_from_env
    return redis_client_from_env("redis://localhost:6379/0")


def _fresh_names() -> tuple[str, str, str]:
    """أسماء معزولة لكل اختبار: (stream_prefix, queue_stream, project)."""
    tag = uuid.uuid4().hex[:12]
    return f"ev-{tag}:", f"wq-{tag}:runs", f"proj-{tag}"


class _CollectSink:
    """EventSink مجمّع — نفس أداة عدة عقود الـ Runner."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def emit(self, event: RunEvent) -> None:
        self.events.append(event)


# ═══════════ 1) درزة config: resolve_dispatch_mode ═══════════


class TestDispatchConfigSeam:
    """يعمل **بلا** Redis — عقد الدرزة فقط."""

    def test_absent_is_default_in_proc(self):
        """بند القبول: غياب المفتاح = in-proc (الافتراضي التاريخي)."""
        assert resolve_dispatch_mode(None) == "in-proc"
        assert DEFAULT_DISPATCH == "in-proc"

    def test_explicit_in_proc_equals_absent(self):
        assert resolve_dispatch_mode("in-proc") == resolve_dispatch_mode(None)

    def test_worker_mode_accepted(self):
        assert resolve_dispatch_mode("worker") == "worker"
        assert set(KNOWN_DISPATCH_MODES) == {"in-proc", "worker"}

    @pytest.mark.parametrize("bad", [
        "redis", "inproc", "WORKER", "", 7, ["worker"], {"mode": "worker"}])
    def test_unknown_value_is_loud_boot_failure(self, bad):
        """اسم مجهول/نوع خاطئ = ValueError صاخب — نفس عقد backend:."""
        with pytest.raises(ValueError):
            resolve_dispatch_mode(bad)

    def test_no_top_level_redis_import_in_worker_module(self):
        """عقد T-109 يمتد: worker.py بلا ``import redis`` علوي."""
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[2]
               / "worker.py").read_text(encoding="utf-8")
        bad = [ln for ln in src.splitlines()
               if ln.startswith(("import redis", "from redis"))]
        assert bad == []


class TestInProcDefaultParity:
    """بند القبول: dispatch الافتراضي يختار ChainRunner التاريخي نفسه."""

    def test_default_dispatch_selects_historical_chain_runner(self):
        """المنفّذ المُختار **نوعه** ChainRunner — لا غلاف ولا بديل."""
        import server
        from runners.chain import ChainRunner
        assert server._dispatch_mode == "in-proc"
        runner = server._chain_runner_for_dispatch(bridge=object())
        assert type(runner) is ChainRunner

    def test_config_yaml_default_is_in_proc(self):
        """قيمة المستودع المشحونة = in-proc — الافتراضي محفوظ."""
        import pathlib

        import yaml
        cfg = yaml.safe_load(
            (pathlib.Path(__file__).resolve().parents[2]
             / "config.yaml").read_text(encoding="utf-8"))
        assert resolve_dispatch_mode(cfg.get("dispatch")) == "in-proc"


# ═══════════ 2) ProjectLease ضد Redis حقيقي ═══════════


@needs_redis
class TestProjectLease:
    """دلالات الحجز من docs/phase8_plan.md §3 — SET NX PX + Lua."""

    def test_acquire_release_cycle(self):
        _, _, project = _fresh_names()
        lease = ProjectLease(_client(), project, "w1")
        assert lease.acquire() is True
        assert lease.holder() == "w1"
        assert lease.release() is True
        assert lease.holder() is None

    def test_exclusivity_two_workers_one_project(self):
        """بند القبول: عاملان + مشروع واحد ⇒ واحد فقط يحمل الحجز."""
        _, _, project = _fresh_names()
        client = _client()
        a = ProjectLease(client, project, "worker-a")
        b = ProjectLease(client, project, "worker-b")
        results = [a.acquire(), b.acquire()]
        assert results.count(True) == 1
        assert a.holder() == "worker-a"
        a.release()

    def test_renew_is_ownership_checked(self):
        """التجديد مشروط بالملكية — غير الحائز لا يجدد."""
        _, _, project = _fresh_names()
        client = _client()
        owner = ProjectLease(client, project, "owner")
        intruder = ProjectLease(client, project, "intruder")
        assert owner.acquire()
        assert owner.renew() is True
        assert intruder.renew() is False       # ليس الحائز
        assert owner.holder() == "owner"       # الحجز لم يُمس
        owner.release()

    def test_release_is_ownership_checked(self):
        """التحرير مشروط بالملكية — غير الحائز لا يحرر."""
        _, _, project = _fresh_names()
        client = _client()
        owner = ProjectLease(client, project, "owner")
        intruder = ProjectLease(client, project, "intruder")
        assert owner.acquire()
        assert intruder.release() is False
        assert owner.holder() == "owner"
        assert owner.release() is True

    def test_ttl_expiry_frees_project_for_takeover(self):
        """بند القبول: انقضاء TTL بعد «قتل» العامل ⇒ الثاني يستحوذ.

        القتل = التوقف عن التجديد (العامل الميت لا يجدد بالتعريف) —
        TTL قصير حتى لا نبطئ العدة.
        """
        _, _, project = _fresh_names()
        client = _client()
        dead = ProjectLease(client, project, "dead-worker", ttl_ms=150)
        survivor = ProjectLease(client, project, "survivor", ttl_ms=30_000)
        assert dead.acquire()
        assert survivor.acquire() is False     # الحجز قائم بعد
        time.sleep(0.3)                        # > TTL — انقضى
        assert survivor.acquire() is True      # الاستحواذ بعد الانقضاء
        assert survivor.holder() == "survivor"
        assert dead.renew() is False           # الميت فقد الملكية نهائيًا
        survivor.release()

    def test_invalid_ttl_is_loud(self):
        with pytest.raises(ValueError):
            ProjectLease(_client(), "p", "w", ttl_ms=0)


# ═══════════ 3) E2E: تشغيلة عبر worker مع وصول الأحداث ═══════════


def _make_pair(stream_prefix: str, queue_stream: str,
               worker_id: str = "w1", lease_ttl_ms: int = 30_000
               ) -> tuple[WorkerDispatchClient, Worker]:
    """عميل خادم + عامل يتشاركان نفس المفاتيح المعزولة."""
    from core.backends_redis import RedisEventBusBackend, RedisWorkQueue
    client = _client()
    server_q = RedisWorkQueue(client=client, stream=queue_stream)
    worker_q = RedisWorkQueue(client=client, stream=queue_stream)
    dispatch = WorkerDispatchClient(server_q, client,
                                    stream_prefix=stream_prefix,
                                    timeout_s=15.0)
    worker = Worker(worker_q,
                    RedisEventBusBackend(client=client,
                                         stream_prefix=stream_prefix),
                    client, worker_id, lease_ttl_ms=lease_ttl_ms)
    return dispatch, worker


@needs_redis
class TestWorkerE2E:
    """بند القبول: التشغيلة تكتمل على worker والأحداث تصل الخادم."""

    def test_run_completes_with_events_arriving(self):
        prefix, qstream, project = _fresh_names()
        dispatch, worker = _make_pair(prefix, qstream)
        # العامل في خيط منفصل — يحاكي عملية مستقلة (نموذج T-109)
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()

        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        sink = _CollectSink()
        result = dispatch.run(
            RunRequest(mode="chain", message="مرحبا يا worker"),
            ticket, sink)
        t.join(timeout=10)

        assert result.status == RESULT_COMPLETED
        assert result.text == "ECHO: مرحبا يا worker"
        types = [e.type for e in sink.events]
        assert types[0] == EVENT_RUN_STARTED
        assert EVENT_RUN_OUTPUT in types
        assert types[-1] == EVENT_RUN_FINISHED
        chunk = next(e for e in sink.events if e.type == EVENT_RUN_OUTPUT)
        assert chunk.data["text"] == "ECHO: مرحبا يا worker"

    def test_ticket_finished_with_result_status(self):
        """عقد الـ Runner (بند 5) محفوظ عبر التفويض: التذكرة تُنهى."""
        prefix, qstream, project = _fresh_names()
        dispatch, worker = _make_pair(prefix, qstream)
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        dispatch.run(RunRequest(mode="chain", message="x"), ticket,
                     _CollectSink())
        t.join(timeout=10)
        assert ticket.state == RESULT_COMPLETED

    def test_worker_failure_arrives_as_failed_result(self):
        """runner فاشل داخل العامل ⇒ RunResult(failed) تصل الخادم —
        لا استثناءات مبتلعة بصمت ولا انتظار حتى المهلة."""
        prefix, qstream, project = _fresh_names()
        from core.backends_redis import (RedisEventBusBackend,
                                         RedisWorkQueue)
        from tests.fakes.echo_runner import EchoRunner
        client = _client()
        dispatch = WorkerDispatchClient(
            RedisWorkQueue(client=client, stream=qstream), client,
            stream_prefix=prefix, timeout_s=15.0)
        worker = Worker(
            RedisWorkQueue(client=client, stream=qstream),
            RedisEventBusBackend(client=client, stream_prefix=prefix),
            client, "w-fail",
            runner_factory=lambda p: EchoRunner(
                fail_with=RuntimeError("عطل مزروع")))
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        result = dispatch.run(RunRequest(mode="chain", message="x"),
                              ticket, _CollectSink())
        t.join(timeout=10)
        assert result.status == "failed"
        assert "عطل مزروع" in result.error

    def test_queue_drained_after_completion(self):
        """الدورة كاملة: بعد الاكتمال لا معلّق في المجموعة (ack تم)."""
        prefix, qstream, project = _fresh_names()
        dispatch, worker = _make_pair(prefix, qstream)
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        dispatch.run(RunRequest(mode="chain", message="x"), ticket,
                     _CollectSink())
        t.join(timeout=10)
        assert dispatch._queue.pending_count() == 0


# ═══════════ 4) الحجز داخل حلقة العامل ═══════════


@needs_redis
class TestWorkerLeaseIntegration:
    """الحجز مربوط فعلًا في الحلقة — لا يكفي وجود الصنف."""

    def test_busy_project_requeues_entry(self):
        """مشروع محجوز لعامل آخر ⇒ requeue (المدخلة لا تُفقد ولا تُنفَّذ)."""
        prefix, qstream, project = _fresh_names()
        dispatch, worker = _make_pair(prefix, qstream, worker_id="w-blocked")
        # عامل «آخر» يحمل حجز المشروع مسبقًا
        foreign = ProjectLease(_client(), project, "foreign-holder")
        assert foreign.acquire()
        dispatch._queue.enqueue({"run_id": "r1", "project_id": project,
                                 "mode": "chain", "message": "x"})
        assert worker.run_once(block_ms=1000) == "requeued"
        # المدخلة عادت للقائمة (مُعادة لا مفقودة) والحجز الأجنبي سليم
        assert foreign.holder() == "foreign-holder"
        reclaimed = worker._queue.claim("verifier", count=1, block_ms=500)
        assert len(reclaimed) == 1
        assert reclaimed[0].payload["run_id"] == "r1"
        foreign.release()

    def test_lease_released_after_run(self):
        """بعد اكتمال التشغيلة يُحرَّر الحجز — المشروع متاح فورًا."""
        prefix, qstream, project = _fresh_names()
        dispatch, worker = _make_pair(prefix, qstream)
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        dispatch.run(RunRequest(mode="chain", message="x"), ticket,
                     _CollectSink())
        t.join(timeout=10)
        probe = ProjectLease(_client(), project, "probe")
        assert probe.acquire() is True   # الحجز تحرر
        probe.release()

    def test_takeover_after_dead_worker_ttl(self):
        """بند القبول E2E: عامل «يموت» حاملًا الحجز ⇒ بعد TTL يستحوذ
        الثاني وينفّذ التشغيلة فعلًا."""
        prefix, qstream, project = _fresh_names()
        # الميت: حجز قصير TTL بلا تجديد (لا حلقة له أصلًا)
        dead = ProjectLease(_client(), project, "dead", ttl_ms=200)
        assert dead.acquire()
        dispatch, survivor = _make_pair(prefix, qstream,
                                        worker_id="survivor")

        def _persistent_worker():
            # يعيد المحاولة: أول دورة تُعيد المدخلة (الحجز قائم)،
            # وبعد الانقضاء يستحوذ وينفّذ.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                status = survivor.run_once(block_ms=500)
                if status not in ("idle", "requeued"):
                    return

        t = threading.Thread(target=_persistent_worker, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        result = dispatch.run(RunRequest(mode="chain", message="نجونا"),
                              ticket, _CollectSink())
        t.join(timeout=12)
        assert result.status == RESULT_COMPLETED
        assert result.text == "ECHO: نجونا"

    def test_renew_keeps_lease_alive_during_long_run(self):
        """خيط التجديد يبقي الحجز حيًّا لتشغيلة أطول من TTL."""
        prefix, qstream, project = _fresh_names()
        from core.backends_redis import (RedisEventBusBackend,
                                         RedisWorkQueue)
        from tests.fakes.echo_runner import EchoRunner
        client = _client()
        holder_seen: list[str | None] = []

        def _slow_factory(payload):
            class _SlowEcho(EchoRunner):
                def run(self, request, ticket, events):
                    time.sleep(0.9)  # ~3× الـ TTL
                    holder_seen.append(
                        ProjectLease(client, project, "probe").holder())
                    return super().run(request, ticket, events)
            return _SlowEcho()

        dispatch = WorkerDispatchClient(
            RedisWorkQueue(client=client, stream=qstream), client,
            stream_prefix=prefix, timeout_s=15.0)
        worker = Worker(
            RedisWorkQueue(client=client, stream=qstream),
            RedisEventBusBackend(client=client, stream_prefix=prefix),
            client, "w-slow", lease_ttl_ms=300,
            runner_factory=_slow_factory)
        t = threading.Thread(target=worker.run_once,
                             kwargs={"block_ms": 5000}, daemon=True)
        t.start()
        registry = ExecutionRegistry()
        ticket = registry.register("chain", project_id=project)
        result = dispatch.run(RunRequest(mode="chain", message="بطيء"),
                              ticket, _CollectSink())
        t.join(timeout=12)
        assert result.status == RESULT_COMPLETED
        assert holder_seen == ["w-slow"]  # الحجز حي بعد تجاوز TTL الأصلي
