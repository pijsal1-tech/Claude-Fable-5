# -*- coding: utf-8 -*-
"""TSK-610 (PM-03 §R6) — تجميع مقاييس الـ runs عبر الزمن.

Validates: TSK-610.

معيار القبول الحرفي: «3 runs → 3 أسطر صالحة؛ p50/p95 محسوبة صحيحًا
في الاختبار».

يتحقق من:
  1. المخزن: إلحاق JSONL سطر-لكل-سجل؛ قارئ يتخطى الأسطر الممزّقة
     (ذيل مقطوع بانهيار لا يعطّل الملخّص)؛ ملف غائب = [] لا استثناء.
  2. percentile (nearest-rank): حالات معلومة يدويًا + p50/p95.
  3. المسجّل: 3 دورات RunStarted→RunFinished عبر EventBus حقيقي →
     3 أسطر صالحة بحقولها (mode من started، status/duration_ms من
     finished)؛ finished يتيم → سطر بحقول فارغة (لا اختراع)؛ سقف
     _pending يطرد الأقدم؛ فشل الكتابة يُبتلع (الـ run لا يتأثر).
  4. الملخّص: عدّادات + p50/p95 كليًا ولكل mode.
  5. REST: /api/metrics/runs يعيد الملخّص؛ 503 قبل التهيئة.
  6. e2e مصغّر: DirectRunner حقيقي عبر _RunnerWSAdapter → سطر مقاييس
     بمدة TSK-609 الحقيقية (تقاطع 609↔610).

صفر نداءات AI خارجية — FakeProvider/أحداث مركّبة فقط.
"""
from __future__ import annotations

import json

import pytest

import server
from core.events import EventBus, RunFinished, RunStarted, StepProgress
from core.execution import ExecutionRegistry
from core.run_metrics import (
    MAX_PENDING,
    RunMetricsRecorder,
    RunMetricsStore,
)
from core.runner import RunRequest
from runners.direct import DirectRunner
from tests.fakes.fake_provider import FakeProvider


# ═══════════════════ 1. المخزن: إلحاق وقراءة ═══════════════════

class TestStoreAppendRead:
    def test_append_creates_parent_and_valid_lines(self, tmp_path):
        store = RunMetricsStore(tmp_path / "metrics" / "runs.jsonl")
        store.append({"run_id": "r1", "duration_ms": 5})
        store.append({"run_id": "r2", "duration_ms": 7})
        lines = store.path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert all(json.loads(ln)["run_id"] for ln in lines)

    def test_missing_file_reads_empty(self, tmp_path):
        store = RunMetricsStore(tmp_path / "nope.jsonl")
        assert store.read_records() == []
        assert store.summary()["count"] == 0

    def test_torn_tail_skipped(self, tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        store.append({"run_id": "r1", "duration_ms": 5})
        with open(store.path, "a", encoding="utf-8") as f:
            f.write('{"run_id": "torn", "durat')  # سطر ممزّق بلا \n
        records = store.read_records()
        assert [r["run_id"] for r in records] == ["r1"]


# ═══════════════════ 2. percentile (nearest-rank) ═══════════════════

class TestPercentile:
    def test_empty_is_none(self):
        assert RunMetricsStore.percentile([], 50) is None

    def test_single_value(self):
        assert RunMetricsStore.percentile([42], 50) == 42.0
        assert RunMetricsStore.percentile([42], 95) == 42.0

    def test_known_values(self):
        # nearest-rank على 1..10: p50 = العنصر رقم ⌈5⌉ = 5؛
        # p95 = العنصر رقم ⌈9.5⌉ = 10.
        vals = list(range(1, 11))
        assert RunMetricsStore.percentile(vals, 50) == 5.0
        assert RunMetricsStore.percentile(vals, 95) == 10.0

    def test_unsorted_input(self):
        assert RunMetricsStore.percentile([30, 10, 20], 50) == 20.0


# ═══════════════════ 3. المسجّل عبر bus حقيقي ═══════════════════

def _cycle(bus, run_id, mode="direct", status="completed", duration=100):
    bus.publish(RunStarted(run_id=run_id, mode=mode))
    bus.publish(RunFinished(run_id=run_id, status=status,
                            payload={"reason": status,
                                     "duration_ms": duration}))


class TestRecorder:
    def test_three_runs_three_valid_lines(self, tmp_path):
        """معيار القبول الحرفي: 3 runs → 3 أسطر صالحة."""
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        bus = EventBus()
        bus.subscribe(RunMetricsRecorder(store))
        _cycle(bus, "r1", mode="direct", duration=100)
        _cycle(bus, "r2", mode="agent", status="failed", duration=200)
        _cycle(bus, "r3", mode="delegate", duration=300)
        records = store.read_records()
        assert len(records) == 3
        assert [(r["run_id"], r["mode"], r["status"], r["duration_ms"])
                for r in records] == [
            ("r1", "direct", "completed", 100),
            ("r2", "agent", "failed", 200),
            ("r3", "delegate", "completed", 300),
        ]
        assert all("ts" in r for r in records)

    def test_orphan_finished_recorded_with_empty_mode(self, tmp_path):
        """finished بلا started مقترن (إعادة تشغيل مثلًا) — يُسجَّل
        بحقول فارغة، لا اختراع ولا استثناء."""
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        rec = RunMetricsRecorder(store)
        rec(RunFinished(run_id="ghost", status="completed",
                        payload={"duration_ms": 9}))
        r = store.read_records()[0]
        assert r["mode"] == "" and r["duration_ms"] == 9

    def test_other_events_ignored(self, tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        rec = RunMetricsRecorder(store)
        rec(StepProgress(run_id="r1"))
        assert store.read_records() == []

    def test_pending_capped_oldest_evicted(self, tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        rec = RunMetricsRecorder(store, max_pending=2)
        rec(RunStarted(run_id="old", mode="direct"))
        rec(RunStarted(run_id="mid", mode="agent"))
        rec(RunStarted(run_id="new", mode="chain"))  # يطرد old
        rec(RunFinished(run_id="old", status="completed",
                        payload={"duration_ms": 1}))
        assert store.read_records()[0]["mode"] == ""  # old أُطرد
        assert MAX_PENDING == 256  # السقف الافتراضي موثّق

    def test_write_failure_swallowed(self, tmp_path, capsys):
        """فشل الكتابة لا يهرب من المسجّل (الـ run لا يتأثر)."""
        class _BoomStore(RunMetricsStore):
            def append(self, record):
                raise OSError("قرص ممتلئ")

        rec = RunMetricsRecorder(_BoomStore(tmp_path / "x.jsonl"))
        rec(RunFinished(run_id="r1", status="completed", payload={}))
        assert "فشل إلحاق سطر المقاييس" in capsys.readouterr().out


# ═══════════════════ 4. الملخّص ═══════════════════

class TestSummary:
    def test_counts_and_percentiles(self, tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        bus = EventBus()
        bus.subscribe(RunMetricsRecorder(store))
        for i, d in enumerate([100, 200, 300, 400], start=1):
            _cycle(bus, f"r{i}", mode="direct", duration=d)
        _cycle(bus, "r5", mode="agent", status="failed", duration=1000)
        s = store.summary()
        assert s["count"] == 5
        assert s["status_counts"] == {"completed": 4, "failed": 1}
        # nearest-rank على [100,200,300,400,1000]: p50=⌈2.5⌉=3→300؛
        # p95=⌈4.75⌉=5→1000.
        assert s["p50_duration_ms"] == 300.0
        assert s["p95_duration_ms"] == 1000.0
        assert s["by_mode"]["direct"]["count"] == 4
        assert s["by_mode"]["direct"]["p50_duration_ms"] == 200.0
        assert s["by_mode"]["agent"]["p95_duration_ms"] == 1000.0

    def test_records_without_duration_counted_not_aggregated(self,
                                                             tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        store.append({"run_id": "r1", "mode": "direct",
                      "status": "completed", "duration_ms": None})
        s = store.summary()
        assert s["count"] == 1
        assert s["p50_duration_ms"] is None


# ═══════════════════ 5. REST قراءة ═══════════════════

class TestRestEndpoint:
    def test_503_before_boot(self, monkeypatch):
        monkeypatch.setattr(server, "run_metrics_store", None)
        with server.app.test_client() as c:
            resp = c.get("/api/metrics/runs")
        assert resp.status_code == 503

    def test_summary_served(self, monkeypatch, tmp_path):
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        store.append({"run_id": "r1", "mode": "direct",
                      "status": "completed", "duration_ms": 50})
        monkeypatch.setattr(server, "run_metrics_store", store)
        with server.app.test_client() as c:
            data = c.get("/api/metrics/runs").get_json()
        assert data["ok"] is True
        assert data["summary"]["count"] == 1
        assert data["summary"]["p50_duration_ms"] == 50.0


# ═══════════════ 6. e2e مصغّر: runner حقيقي → سطر مقاييس ═══════════════

class TestEndToEndWithRunner:
    def test_direct_runner_produces_metrics_line(self, tmp_path,
                                                 monkeypatch):
        """تقاطع 609↔610: duration_ms الحقيقية من الـ runner تصل السجل
        عبر _RunnerWSAdapter → event_bus → RunMetricsRecorder."""
        store = RunMetricsStore(tmp_path / "runs.jsonl")
        bus = EventBus()
        bus.subscribe(RunMetricsRecorder(store))
        monkeypatch.setattr(server, "event_bus", bus)

        registry = ExecutionRegistry()
        ticket = registry.register("direct", project_id="tsk610")
        sink = server._RunnerWSAdapter(lambda frame: None)
        provider = FakeProvider(default_response="رد مباشر")
        result = DirectRunner(provider.stream).run(
            RunRequest(mode="direct", message="اشرح"), ticket, sink)

        assert result.status == "completed"
        records = store.read_records()
        assert len(records) == 1
        r = records[0]
        assert r["run_id"] == ticket.run_id
        assert r["mode"] == "direct"
        assert r["status"] == "completed"
        assert isinstance(r["duration_ms"], int) and r["duration_ms"] >= 0
