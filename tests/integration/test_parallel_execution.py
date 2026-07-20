# -*- coding: utf-8 -*-
"""T-046 (R-603): Parallel Ready-Set Execution — أدلة القبول.

Acceptance Criteria (حرفيًّا من DEVELOPMENT_TASKS.md):
- parallel=1 byte-identical to legacy (المسار التسلسلي القديم حرفيًّا).
- ≥3× speedup on 8-step map at parallel=4 (FakeProvider latency).
- stress consistent — 20 map steps with injected random failures.
- cancellation stops siblings.

ملاحظة تصميمية (متسقة مع العقد القديم و T-044):
خطوة كانت داخل نداء المزود لحظة الإلغاء قد تبقى بحالة "running" في
الـ run الملغى — محدودة بحجم الدفعة (≤ max_parallel_steps)؛
`rebuild_run` (T-044) يعيد كل خطوة غير ناجحة إلى pending عند الاستكمال.
"""
from __future__ import annotations

import threading
import time

import pytest

from chain.executor import ChainExecutor
from chain.models import ChainRun, ChainStep, ExecutionPolicy
from providers.base import ProviderTransientError
from tests.fakes.fake_provider import FakeProvider, RecordedCall


# ═══════════════════════ helpers ═══════════════════════

def _map_steps(n: int, prefix: str = "m") -> list[ChainStep]:
    """خطوات map مستقلة (بلا تبعيات) — الحمل النمطي للتوازي."""
    return [
        ChainStep(id=f"{prefix}{i}", name=f"Map {i}", stage="execute",
                  agent_role="executor", prompt_template=f"map work {i}",
                  critical=True)
        for i in range(1, n + 1)
    ]


def _run_of(steps: list[ChainStep], parallel: int, run_id: str,
            **policy_kw) -> ChainRun:
    policy_kw.setdefault("max_retries", 0)
    policy_kw.setdefault("max_provider_calls", 200)
    return ChainRun(run_id=run_id, steps=steps,
                    policy=ExecutionPolicy(max_parallel_steps=parallel,
                                           **policy_kw))


class ThreadSafeProvider(FakeProvider):
    """FakeProvider بحماية خيوط + عدّادات تزامن.

    - `concurrent_now` / `concurrent_peak`: كم نداء مزود يعمل الآن/كذروة —
      دليل مباشر على أن الـ pool يوازي فعلًا ويحترم السقف.
    - تسجيل النداءات وطابور الردود وحقن الفشل كلها تحت قفل واحد —
      FakeProvider الأصلي غير آمن للخيوط (list.pop إلخ).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ts_lock = threading.Lock()
        self.concurrent_now = 0
        self.concurrent_peak = 0
        self.on_first_call: callable | None = None
        self._first_fired = False

    def send(self, prompt, history=None, system_prompt=""):
        with self._ts_lock:
            self.calls.append(
                RecordedCall("send", prompt, history, system_prompt))
            self.concurrent_now += 1
            self.concurrent_peak = max(self.concurrent_peak,
                                       self.concurrent_now)
            fire_first = not self._first_fired
            self._first_fired = True
        try:
            if fire_first and self.on_first_call is not None:
                self.on_first_call()
            if self.latency_s:
                time.sleep(self.latency_s)
            with self._ts_lock:
                if self.fail_always is not None:
                    raise self.fail_always
                if self._fail_next:
                    raise self._fail_next.pop(0)
                if self._responder is not None:
                    responder = self._responder
                else:
                    responder = None
                if responder is None and self._queue:
                    return self._queue.pop(0)
            if responder is not None:
                return responder(prompt, history, system_prompt)
            return self.default_response
        finally:
            with self._ts_lock:
                self.concurrent_now -= 1


def _collect(frames: list):
    def on_event(ev):
        frames.append(ev.to_dict())
    return on_event


def _events(frames: list, etype: str) -> list[dict]:
    return [f for f in frames if f.get("type") == etype]


# ═══════════════ 1) parallel=1 — المسار القديم حرفيًّا ═══════════════

class TestSequentialParity:

    def test_parallel_1_start_order_and_results_identical(self):
        """parallel=1 ⇒ ready[0] بالضبط: ترتيب بدء حتمي + نتائج كاملة."""
        steps = _map_steps(2) + [
            ChainStep(id="join", name="Join", stage="execute",
                      agent_role="executor", prompt_template="join",
                      depends_on=["m1", "m2"]),
        ]
        provider = ThreadSafeProvider(
            responder=lambda p, h, s: f"R:{p[:12]}")
        run = _run_of(steps, parallel=1, run_id="run-par1seq1")

        frames: list[dict] = []
        result = ChainExecutor(provider).execute(run, _collect(frames))

        assert result.status == "completed"
        started = [f["step_id"] for f in _events(frames, "step_started")]
        assert started == ["m1", "m2", "join"]      # declaration order — legacy
        assert set(result.results) == {"m1", "m2", "join"}

    def test_parallel_1_single_worker_never_overlaps(self):
        """parallel=1 لا يفتح pool إطلاقًا — ذروة التزامن = 1."""
        provider = ThreadSafeProvider(default_response="ok")
        provider.latency_s = 0.02
        run = _run_of(_map_steps(6), parallel=1, run_id="run-par1seq2")

        assert ChainExecutor(provider).execute(run).status == "completed"
        assert provider.concurrent_peak == 1


# ═══════════════ 2) speedup — ≥3× على 8 خطوات @ parallel=4 ═══════════════

LATENCY = 0.15


class TestSpeedup:

    def test_8_map_steps_at_parallel_4_at_least_3x(self):
        """القبول الحرفي: ‏8 خطوات map، ‏parallel=4 ⇒ تسريع ≥3×."""
        def timed(parallel: int) -> float:
            provider = ThreadSafeProvider(default_response="ok")
            provider.latency_s = LATENCY
            run = _run_of(_map_steps(8), parallel=parallel,
                          run_id=f"run-speed-p{parallel}")
            t0 = time.monotonic()
            assert ChainExecutor(provider).execute(run).status == "completed"
            return time.monotonic() - t0

        sequential = timed(1)      # 8 × LATENCY
        parallel4 = timed(4)       # دفعتان × LATENCY تقريبًا
        assert sequential / parallel4 >= 3.0, (
            f"speedup {sequential / parallel4:.2f}× < 3×")

    def test_pool_respects_capacity_cap(self):
        """‏12 خطوة جاهزة @ parallel=3 ⇒ ‏1 < الذروة ≤ 3 (capacity cap)."""
        provider = ThreadSafeProvider(default_response="ok")
        provider.latency_s = 0.05
        run = _run_of(_map_steps(12), parallel=3, run_id="run-cap3")

        assert ChainExecutor(provider).execute(run).status == "completed"
        assert 1 < provider.concurrent_peak <= 3


# ═══════════════ 3) stress — 20 خطوة مع فشل عشوائي محقون ═══════════════

class TestStress:

    @pytest.mark.parametrize("seed", [7, 21, 1337])
    def test_20_map_random_failures_state_consistent(self, seed):
        """‏20 map @ parallel=4، ‏~30% فشل محقون بالبذرة ⇒ حالة متسقة."""
        import random
        rng = random.Random(seed)
        fail_ids = {f"m{i}" for i in range(1, 21) if rng.random() < 0.30}

        def responder(prompt, history, sys):
            # الرقم من ذيل قالب البرومبت "map work {i}"
            idx = prompt.rsplit("map work ", 1)[1].split()[0].strip()
            if f"m{idx}" in fail_ids:
                raise ProviderTransientError(f"injected failure m{idx}")
            return f"OK-m{idx}"

        steps = _map_steps(20)
        for s in steps:
            s.critical = False        # الفشل لا يوقف السلسلة
        provider = ThreadSafeProvider(responder=responder)
        run = _run_of(steps, parallel=4, run_id=f"run-stress-{seed}")

        result = ChainExecutor(provider).execute(run)

        # كل خطوة نُفِّذت مرة واحدة بالضبط (لا ازدواج تحت التوازي)
        for i in range(1, 21):
            hits = sum(1 for c in provider.calls
                       if c.prompt.endswith(f"map work {i}"))
            assert hits == 1, f"m{i} executed {hits} times"

        for s in result.steps:
            if s.id in fail_ids:
                assert s.status == "error"
                assert s.id not in result.results
            else:
                assert s.status == "success"
                assert result.results[s.id] == f"OK-{s.id}"

        assert result.status == "completed"
        assert result.is_complete()

    def test_critical_failure_skips_remaining(self):
        """فشل خطوة critical تحت التوازي ⇒ run فشل ولا خطوة تبقى pending."""
        def responder(prompt, history, sys):
            if prompt.endswith("map work 1"):
                raise ProviderTransientError("critical boom")
            time.sleep(0.02)
            return "ok"

        steps = _map_steps(8)       # كلها critical=True
        provider = ThreadSafeProvider(responder=responder)
        run = _run_of(steps, parallel=4, run_id="run-critfail1")

        result = ChainExecutor(provider).execute(run)
        assert result.status == "failed"
        assert not any(s.status == "pending" for s in result.steps)


# ═══════════════ 4) cancellation — الإلغاء يوقف الإخوة ═══════════════

class TestCancellation:

    def test_cancel_mid_batch_stops_siblings(self):
        """إلغاء منتصف الدفعة الأولى ⇒ لا إرسال جديد، الـ pool يُصرَّف.

        الخطوات التي كانت داخل نداء المزود لحظة الإلغاء قد تبقى
        "running" (تُرفَض عند نقطة تفتيش الـ retry قبل الدمج) —
        محدودة بحجم الدفعة ≤ 3. T-044 يعيدها pending عند الاستكمال.
        """
        provider = ThreadSafeProvider(default_response="ok")
        provider.latency_s = 0.1
        run = _run_of(_map_steps(12), parallel=3, run_id="run-cancelmid1")
        provider.on_first_call = lambda: run.cancellation_token.cancel(
            "user stop")

        result = ChainExecutor(provider).execute(run)

        assert result.status == "cancelled"
        done = sum(1 for s in result.steps if s.status == "success")
        assert done < 12                       # الإخوة توقفوا — لا سلسلة كاملة
        mid_flight = sum(1 for s in result.steps if s.status == "running")
        assert mid_flight <= 3                 # محدود بحجم الدفعة
        assert provider.concurrent_now == 0    # الـ pool صُرِّف فعلًا

    def test_no_submissions_after_cancel(self):
        """token ملغى مسبقًا ⇒ صفر إرسال — نقطة تفتيش ما قبل الـ submit."""
        provider = ThreadSafeProvider(default_response="ok")
        run = _run_of(_map_steps(6), parallel=3, run_id="run-precancel1")
        run.cancellation_token.cancel("cancelled before start")

        result = ChainExecutor(provider).execute(run)

        assert result.status == "cancelled"
        assert provider.concurrent_peak == 0   # لا نداء مزود إطلاقًا


# ═══════════════ 5) DAG waves — التبعيات تُحترم تحت التوازي ═══════════════

class TestDagWaves:

    def test_map_reduce_shape_runs_in_waves(self):
        """‏4 map + reduce يعتمد عليها كلها ⇒ reduce آخر خطوة تكتمل."""
        steps = _map_steps(4) + [
            ChainStep(id="reduce", name="Reduce", stage="execute",
                      agent_role="executor", prompt_template="reduce all",
                      depends_on=["m1", "m2", "m3", "m4"]),
        ]
        provider = ThreadSafeProvider(default_response="ok")
        provider.latency_s = 0.02
        run = _run_of(steps, parallel=4, run_id="run-waves1")

        frames: list[dict] = []
        result = ChainExecutor(provider).execute(run, _collect(frames))

        assert result.status == "completed"
        completed = [f["step_id"] for f in _events(frames, "step_completed")]
        assert completed[-1] == "reduce"
        assert set(completed[:4]) == {"m1", "m2", "m3", "m4"}
