# -*- coding: utf-8 -*-
"""T-047 (R-604): EventBus + WS Adapter — أدلة القبول.

Acceptance Criteria (حرفيًّا):
- frame snapshots vs legacy recordings identical (المحوّل يعيد بناء
  الإطار القديم بايت-بايت).
- FIFO test under concurrent emission (ترتيب التسليم لكل run =
  ترتيب النشر).
- CI grep green (لا ws.send خارج المحوّل — منسوخ هنا كاختبار أيضًا).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading

import pytest

import server
from core.events import (
    ApprovalRequested,
    BudgetChanged,
    BusEvent,
    EventBus,
    RoutingDecided,
    RunFinished,
    RunStarted,
    StepProgress,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]


class FakeWS:
    def __init__(self):
        self.sent: list[str] = []

    def send(self, payload: str):
        self.sent.append(payload)

    def frames(self) -> list[dict]:
        return [json.loads(p) for p in self.sent]


# ═══════════════════ 1) pub/sub الأساسي ═══════════════════

class TestPubSub:

    def test_subscribe_receive_unsubscribe(self):
        bus = EventBus()
        got: list[BusEvent] = []
        unsub = bus.subscribe(got.append)

        e1 = StepProgress(run_id="r1", frame_type="chunk",
                          payload={"text": "hi"})
        bus.publish(e1)
        assert got == [e1]

        unsub()
        bus.publish(StepProgress(run_id="r1", frame_type="chunk",
                                 payload={"text": "bye"}))
        assert got == [e1]                       # لا تسليم بعد إلغاء الاشتراك
        assert bus.subscriber_count == 0

    def test_multiple_subscribers_all_receive(self):
        bus = EventBus()
        a: list[BusEvent] = []
        b: list[BusEvent] = []
        bus.subscribe(a.append)
        bus.subscribe(b.append)
        ev = RunStarted(run_id="r1", mode="chain")
        bus.publish(ev)
        assert a == [ev] and b == [ev]

    def test_broken_subscriber_is_isolated(self):
        """مشترك يرمي استثناء ⇒ بقية المشتركين والناشر لا يتأثرون."""
        bus = EventBus()
        got: list[BusEvent] = []

        def broken(_ev):
            raise RuntimeError("boom")

        bus.subscribe(broken)
        bus.subscribe(got.append)
        ev = RunFinished(run_id="r1", status="completed")
        bus.publish(ev)                          # لا استثناء يخرج
        assert got == [ev]

    def test_history_records_per_run(self):
        bus = EventBus(history_per_run=3)
        for i in range(5):
            bus.publish(StepProgress(run_id="rA", frame_type="chunk",
                                     payload={"i": i}))
        bus.publish(StepProgress(run_id="rB", frame_type="chunk"))

        hist_a = bus.history("rA")
        assert len(hist_a) == 3                  # سقف التاريخ يُحترم
        assert [e.payload["i"] for e in hist_a] == [2, 3, 4]
        assert len(bus.history("rB")) == 1
        assert bus.history("missing") == []

    def test_event_types_catalog(self):
        """كتالوج R-604 كامل: الأنواع الست كلها BusEvent وتحمل run_id."""
        events = [
            RunStarted(run_id="r", mode="agent"),
            StepProgress(run_id="r", frame_type="chain_step"),
            ApprovalRequested(run_id="r", frame_type="chain_approval_request"),
            RunFinished(run_id="r", status="failed"),
            RoutingDecided(run_id="r", strategy="pipeline"),
            BudgetChanged(run_id="r", payload={"budget": {}}),
        ]
        for e in events:
            assert isinstance(e, BusEvent)
            assert e.run_id == "r"


# ═══════════════════ 2) FIFO تحت النشر المتزامن ═══════════════════

class TestFifo:

    def test_per_run_fifo_under_concurrent_emission(self):
        """4 خيوط تنشر 50 حدثًا لكل run خاص بها — ترتيب كل run محفوظ."""
        bus = EventBus()
        received: dict[str, list[int]] = {f"r{t}": [] for t in range(4)}
        rec_lock = threading.Lock()

        def collector(ev: BusEvent):
            with rec_lock:
                received[ev.run_id].append(ev.payload["seq"])  # type: ignore[attr-defined]

        bus.subscribe(collector)

        def producer(rid: str):
            for i in range(50):
                bus.publish(StepProgress(run_id=rid, frame_type="chunk",
                                         payload={"seq": i}))

        threads = [threading.Thread(target=producer, args=(f"r{t}",))
                   for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        for rid, seqs in received.items():
            assert seqs == list(range(50)), f"{rid} out of order: {seqs[:8]}…"

    def test_history_order_matches_publish_order(self):
        bus = EventBus()

        def producer(rid):
            for i in range(30):
                bus.publish(StepProgress(run_id=rid, frame_type="x",
                                         payload={"seq": i}))

        ts = [threading.Thread(target=producer, args=(f"h{t}",))
              for t in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=10)
        for t in range(3):
            hist = bus.history(f"h{t}")
            assert [e.payload["seq"] for e in hist] == list(range(30))  # type: ignore[attr-defined]


# ═══════════════════ 3) المحوّل: مطابقة الإطارات ═══════════════════

LEGACY_FRAMES = [
    {"type": "start"},
    {"type": "chunk", "text": "مرحبا — قطعة أولى"},
    {"type": "chain_step", "step_id": "s1", "status": "running",
     "name": "تحليل"},
    {"type": "chain_approval_request", "request_id": "req-1",
     "actions": [{"kind": "write", "target": "a.py"}],
     "payload_hash": "abc123"},
    {"type": "chain_finished", "status": "completed",
     "budget": {"successful_calls": 3, "elapsed_seconds": 1.5},
     "text": "✅ Chain completed (3 calls, 1.5s)"},
    {"type": "done", "actions": [], "options": ["كمل"], "summary": "تم"},
]


class TestWSAdapterParity:

    def test_frames_identical_to_legacy_recording(self):
        """التسجيل القديم (ws.send(json.dumps(frame, ensure_ascii=False)))
        مقابل خط bus → _WSAdapter: تطابق حرفي بايت-بايت."""
        legacy_ws = FakeWS()
        for f in LEGACY_FRAMES:
            legacy_ws.send(json.dumps(f, ensure_ascii=False))   # المسار المحذوف

        new_ws = FakeWS()
        publish = server._json_sender(new_ws)                   # bus → _WSAdapter
        for f in LEGACY_FRAMES:
            publish(f)

        assert new_ws.sent == legacy_ws.sent                    # بايت-بايت

    def test_json_sender_swallows_send_errors(self):
        """عقد T-015 محفوظ: WS معطوب لا يرمي للخارج."""
        class BrokenWS:
            def send(self, _):
                raise ConnectionError("closed")

        publish = server._json_sender(BrokenWS())
        publish({"type": "chunk", "text": "x"})                 # لا استثناء

    def test_approval_frames_publish_typed_event(self):
        """إطار موافقة ⇒ ApprovalRequested على bus الاتصال (لا StepProgress)."""
        bus = EventBus()
        seen: list[BusEvent] = []
        bus.subscribe(seen.append)
        publish = server._frame_publisher(bus, conn_key="c1")
        publish({"type": "chain_approval_request", "request_id": "q1"})
        publish({"type": "chunk", "text": "t"})
        assert isinstance(seen[0], ApprovalRequested)
        assert isinstance(seen[1], StepProgress)

    def test_budget_frames_derive_budget_changed(self, monkeypatch):
        """إطار يحمل budget ⇒ BudgetChanged رصدي على الـ bus العام."""
        observed: list[BusEvent] = []
        obs_bus = EventBus()
        obs_bus.subscribe(observed.append)
        monkeypatch.setattr(server, "event_bus", obs_bus)

        publish = server._frame_publisher(EventBus(), conn_key="c2")
        publish({"type": "chain_finished", "status": "completed",
                 "budget": {"successful_calls": 2}})
        assert len(observed) == 1
        assert isinstance(observed[0], BudgetChanged)
        assert observed[0].payload["budget"] == {"successful_calls": 2}

    def test_runner_lifecycle_publishes_observability_events(self, monkeypatch):
        """_RunnerWSAdapter: run_started/run_finished ⇒ أحداث رصدية على
        الـ bus العام — ولا إطار واجهة منهما (نفس القديم)."""
        from core.runner import RunEvent

        observed: list[BusEvent] = []
        obs_bus = EventBus()
        obs_bus.subscribe(observed.append)
        monkeypatch.setattr(server, "event_bus", obs_bus)

        frames: list[dict] = []
        sink = server._RunnerWSAdapter(frames.append)
        sink.emit(RunEvent(type="run_started", run_id="run-x", seq=0,
                           data={"mode": "chain"}))
        sink.emit(RunEvent(type="chain_step", run_id="run-x", seq=1,
                           data={"step_id": "s1"}))
        sink.emit(RunEvent(type="run_finished", run_id="run-x", seq=2,
                           data={"reason": "completed"}))

        assert frames == [{"type": "chain_step", "step_id": "s1"}]
        assert [type(e) for e in observed] == [RunStarted, RunFinished]
        assert observed[0].mode == "chain"          # type: ignore[attr-defined]
        assert observed[1].status == "completed"    # type: ignore[attr-defined]


# ═══════════════════ 4) CI grep — حدود النقل ═══════════════════

class TestTransportBoundary:

    def test_no_ws_send_outside_adapter(self):
        """بند القبول الحرفي: grep لا يجد ws.send خارج _WSAdapter._send
        (نفس بوابة check.sh — منسوخة هنا لتفشل الحزمة لا السكريبت فقط)."""
        proc = subprocess.run(
            ["grep", "-rn", r"ws\.send(", "--include=*.py",
             "server.py", "chain/", "core/", "runners/", "actions/",
             "context/", "sessions/"],
            cwd=str(ROOT), capture_output=True, text=True)
        violations = [ln for ln in proc.stdout.splitlines()
                      if "self._ws.send(" not in ln]
        assert violations == [], f"ws.send outside adapter: {violations}"

    def test_runners_import_zero_transport_modules(self):
        """بند القبول: الـ runners لا تستورد أي وحدة نقل."""
        for mod in ("runners.direct", "runners.chain", "runners.agent",
                    "runners.delegate", "core.events", "core.runner"):
            src = (ROOT / (mod.replace(".", "/") + ".py")).read_text(
                encoding="utf-8")
            for banned in ("import flask", "from flask", "import websocket",
                           "flask_sock"):
                assert banned not in src, f"{mod} imports transport: {banned}"
