# -*- coding: utf-8 -*-
"""T-108 (R-804): درزات الـ Backend — أدلة القبول.

Acceptance Criteria (حرفيًّا):
- frame-sequence goldens byte-identical pre/post extraction —
  التنفيذان الافتراضيان **aliases** للصنفين التاريخيين (تطابق هوية
  لا تطابق سلوك مُقاس فحسب) + golden تسلسل إطارات عبر خط
  bus → _WSAdapter المبني من الدرزة يطابق التسجيل القديم بايت-بايت.
- backend conformance suite runs against the in-mem implementations —
  عدة توافق قابلة للوراثة (نمط PlannerContractMixin من T-106):
  T-109 يشغّل Redis backends عبرها بلا اختبارات مكررة.
- config default ``memory`` requires no new deps — بناء الدرزة لا
  يستورد أي شيء خارج stdlib + core (grep في الاختبار).
"""
from __future__ import annotations

import json
import pathlib
import threading

import pytest

import server
from core.backends import (
    DEFAULT_BACKEND,
    KNOWN_BACKENDS,
    BackendPair,
    EventBusBackend,
    InMemoryEventBusBackend,
    InMemoryRegistryBackend,
    RegistryBackend,
    backends_from_config,
    resolve_backend_name,
)
from core.events import BusEvent, EventBus, StepProgress
from core.execution import ExecutionRegistry, RunBusyError

ROOT = pathlib.Path(__file__).resolve().parents[2]


# ═══════════ 1) عدة التوافق — EventBusBackend ═══════════


class EventBusBackendContractMixin:
    """عدة توافق ناقل الأحداث — ورث وعرّف ``make_bus()``.

    T-109 (Redis) يشغّل backend-ه عبر نفس العدة — الضمانات
    (pub/sub، إلغاء الاشتراك، العزل، FIFO لكل run، التاريخ) عقدٌ
    لا تفاصيل تنفيذ.
    """

    def make_bus(self) -> EventBusBackend:  # pragma: no cover - يورَّث
        raise NotImplementedError

    def test_satisfies_protocol(self):
        assert isinstance(self.make_bus(), EventBusBackend)

    def test_subscribe_publish_unsubscribe(self):
        bus = self.make_bus()
        got: list[BusEvent] = []
        unsub = bus.subscribe(got.append)
        ev = StepProgress(run_id="r1", frame_type="chunk",
                          payload={"i": 1})
        bus.publish(ev)
        assert got == [ev]
        unsub()
        bus.publish(StepProgress(run_id="r1", frame_type="chunk"))
        assert got == [ev]
        assert bus.subscriber_count == 0

    def test_broken_subscriber_isolated(self):
        bus = self.make_bus()
        got: list[BusEvent] = []

        def broken(_ev):
            raise RuntimeError("boom")

        bus.subscribe(broken)
        bus.subscribe(got.append)
        ev = StepProgress(run_id="r1", frame_type="chunk")
        bus.publish(ev)          # لا استثناء يتسرب
        assert got == [ev]

    def test_per_run_fifo_under_concurrency(self):
        bus = self.make_bus()
        received: dict[str, list[int]] = {f"r{t}": [] for t in range(3)}
        rec_lock = threading.Lock()

        def collector(ev: BusEvent):
            with rec_lock:
                received[ev.run_id].append(ev.payload["seq"])  # type: ignore[attr-defined]

        bus.subscribe(collector)

        def producer(rid: str):
            for i in range(40):
                bus.publish(StepProgress(run_id=rid, frame_type="x",
                                         payload={"seq": i}))

        threads = [threading.Thread(target=producer, args=(f"r{t}",))
                   for t in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for rid, seqs in received.items():
            assert seqs == list(range(40)), f"{rid} خارج الترتيب"

    def test_history_per_run(self):
        bus = self.make_bus()
        for i in range(3):
            bus.publish(StepProgress(run_id="rA", frame_type="x",
                                     payload={"i": i}))
        hist = bus.history("rA")
        assert [e.payload["i"] for e in hist] == [0, 1, 2]  # type: ignore[attr-defined]
        assert bus.history("missing") == []


class TestInMemoryEventBusConformance(EventBusBackendContractMixin):
    def make_bus(self) -> EventBusBackend:
        return InMemoryEventBusBackend()


# ═══════════ 2) عدة التوافق — RegistryBackend ═══════════


class RegistryBackendContractMixin:
    """عدة توافق سجل التنفيذ — ورث وعرّف ``make_registry()``.

    تغطي دورة الحياة الكاملة: تسجيل → استعلام → إلغاء تعاوني →
    إنهاء ذري (بتحرير خانة المشروع) → لا double-finish.
    """

    def make_registry(self) -> RegistryBackend:  # pragma: no cover
        raise NotImplementedError

    def test_satisfies_protocol(self):
        assert isinstance(self.make_registry(), RegistryBackend)

    def test_register_lookup_lifecycle(self):
        reg = self.make_registry()
        t = reg.register("chain", project_id="p1")
        assert reg.lookup(t.run_id) is t
        assert t in reg.list_active() and t in reg.list_all()
        assert reg.finish(t.run_id, "completed") is True
        assert t.state == "completed"
        assert t not in reg.list_active() and t in reg.list_all()

    def test_exclusive_per_project_and_slot_release(self):
        reg = self.make_registry()
        t = reg.register("chain", project_id="p1")
        with pytest.raises(RunBusyError):
            reg.register("agent", project_id="p1")
        reg.finish(t.run_id, "completed")
        t2 = reg.register("agent", project_id="p1")   # الخانة تحررت
        assert t2.state == "running"

    def test_cooperative_cancel(self):
        reg = self.make_registry()
        t = reg.register("agent", project_id="p2")
        assert reg.cancel(t.run_id, "user asked") is True
        assert t.is_cancelled and t.state == "running"   # تعاوني: لا نقل حالة
        assert t.finish("cancelled") is True
        assert t.state == "cancelled"

    def test_no_double_finish_and_unknown_ids(self):
        reg = self.make_registry()
        t = reg.register("direct", project_id="p3")
        assert reg.finish(t.run_id, "failed") is True
        assert reg.finish(t.run_id, "completed") is False   # نهائي لا يطفر
        assert t.state == "failed"
        assert reg.finish("missing", "completed") is False
        assert reg.cancel("missing") is False
        assert reg.lookup("missing") is None

    def test_reap_stale_noop_without_ttl(self):
        reg = self.make_registry()
        reg.register("chain", project_id="p4")
        assert reg.reap_stale() == []   # TTL معطّل افتراضيًا


class TestInMemoryRegistryConformance(RegistryBackendContractMixin):
    def make_registry(self) -> RegistryBackend:
        return InMemoryRegistryBackend()


# ═══════════ 3) صفر انحراف: aliases + goldens ═══════════


class TestZeroDrift:
    """بند القبول: byte-identical pre/post — بالهوية لا بالقياس فقط."""

    def test_in_memory_backends_are_the_historical_classes(self):
        """aliases لا أغلفة: أي إصلاح مستقبلي في الأصلين يسري تلقائيًا."""
        assert InMemoryEventBusBackend is EventBus
        assert InMemoryRegistryBackend is ExecutionRegistry

    def test_config_built_pair_is_historical_defaults(self):
        pair = backends_from_config("memory")
        assert type(pair.event_bus) is EventBus
        assert type(pair.registry) is ExecutionRegistry
        # نفس المعاملات التاريخية (بلا وسائط): TTL معطّل، حصري للمشروع
        assert pair.registry._ttl is None
        assert pair.registry._exclusive is True

    def test_server_globals_built_via_seam(self):
        """server.py يستهلك ناتج الدرزة — والأنواع = التاريخية حرفيًّا."""
        assert isinstance(server._backends, BackendPair)
        assert server.execution_registry is server._backends.registry
        assert server.event_bus is server._backends.event_bus
        assert type(server.execution_registry) is ExecutionRegistry
        assert type(server.event_bus) is EventBus

    def test_frame_sequence_golden_via_backend_bus(self):
        """golden تسلسل الإطارات: خط bus → _WSAdapter فوق bus مبني من
        الدرزة يطابق التسجيل القديم (ws.send(json.dumps(...))) بايت-بايت."""
        frames = [
            {"type": "start"},
            {"type": "chunk", "text": "مرحبا — قطعة"},
            {"type": "chain_step", "step_id": "s1", "status": "running"},
            {"type": "chain_finished", "status": "completed",
             "budget": {"successful_calls": 1}},
            {"type": "done", "actions": [], "summary": "تم"},
        ]
        legacy = [json.dumps(f, ensure_ascii=False) for f in frames]

        sent: list[str] = []

        class FakeWS:
            def send(self, payload: str):
                sent.append(payload)

        bus = backends_from_config(None).event_bus
        server._WSAdapter(FakeWS(), bus)
        publish = server._frame_publisher(bus)
        for f in frames:
            publish(f)
        assert sent == legacy


# ═══════════ 4) درزة config ═══════════


class TestConfigSeam:

    def test_known_backends_and_default(self):
        assert KNOWN_BACKENDS == ("memory",)
        assert DEFAULT_BACKEND == "memory"

    def test_absent_key_means_memory(self):
        assert resolve_backend_name(None) == "memory"
        pair = backends_from_config(None)
        assert pair.name == "memory"

    def test_explicit_equals_default(self):
        d, e = backends_from_config(None), backends_from_config("memory")
        assert type(d.registry) is type(e.registry)
        assert type(d.event_bus) is type(e.event_bus)

    @pytest.mark.parametrize("bad", [
        "redis", "MEMORY", "", 3, ["memory"],
    ])
    def test_unknown_values_fail_loud(self, bad):
        with pytest.raises(ValueError):
            resolve_backend_name(bad)
        with pytest.raises(ValueError):
            backends_from_config(bad)

    def test_actual_config_yaml_value_resolves(self):
        import yaml
        cfg = yaml.safe_load(
            (ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
        assert resolve_backend_name(cfg.get("backend")) == "memory"

    def test_memory_backend_needs_no_new_deps(self):
        """بند القبول: memory بلا تبعيات جديدة — لا استيراد خارج
        stdlib + core في core/backends.py (grep، نمط بوابات check.sh)."""
        src = (ROOT / "core" / "backends.py").read_text(encoding="utf-8")
        import_lines = [
            ln.strip() for ln in src.splitlines()
            if ln.strip().startswith(("import ", "from "))
        ]
        allowed = ("from __future__", "from dataclasses", "from typing",
                   "from core.")
        for ln in import_lines:
            assert ln.startswith(allowed), f"تبعية دخيلة في backends.py: {ln}"
