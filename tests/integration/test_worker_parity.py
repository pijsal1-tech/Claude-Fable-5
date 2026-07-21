# -*- coding: utf-8 -*-
"""T-111 (R-804): Frame-Parity Harness + WS Latency Guard — أدلة القبول.

Acceptance Criteria (حرفيًّا):
- parity test green on both dispatch modes — نفس تشغيلة السلسلة
  الثابتة تسجَّل in-proc وعبر worker (Redis حقيقي) والتسلسلان
  **بايت-مطابقان** (بند R-804 الأصلي: «byte-identical WS frame
  sequence vs in-proc»).
- deliberate frame mutation makes it fail — حساسية الـ harness
  مُثبتة: طفرات متعمدة (قيمة/حقل/نوع/ترتيب/حذف) كلها تُضبط.
- latency bench within tolerance — زمن استجابة مرئي-للـ WS لا يتأثر
  ضمن سماحية (منهج flaky-rerun كبقية البنشات: إعادة القياس مرة
  واحدة قبل الفشل — الأزمنة ملك الجهاز لا الخوارزمية).

اختبارات worker ضد Redis **حقيقي** (نمط skipif من T-109/T-110) بعزل
مفاتيح uuid — لا flushdb.
"""
from __future__ import annotations

import copy
import time

import pytest

from core.runner import RESULT_COMPLETED
from tests.fakes.fake_provider import FakeProvider
from tests.frame_harness import (
    NONDETERMINISTIC_KEYS,
    assert_frame_parity,
    frames_to_bytes,
    normalize_frame,
    record_inproc_chain_frames,
    record_worker_chain_frames,
)

REQ = "نفّذ المهمة الثابتة لقياس التطابق"
REPLY = "رد السلسلة الثابت للمطابقة"


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


def _provider_factory():
    return FakeProvider(default_response=REPLY)


# ═══════════ 1) بند القبول: التوازي على الوضعين ═══════════


@needs_redis
class TestFrameParity:
    """التسلسلان بايت-مطابقان — بند R-804 الأصلي نصًّا."""

    def test_worker_frames_byte_identical_to_inproc(self, tmp_path):
        inproc = record_inproc_chain_frames(tmp_path, _provider_factory, REQ)
        worker = record_worker_chain_frames(tmp_path, _provider_factory,
                                            REQ, _client())
        assert inproc.frames, "التسجيلة الأساس فارغة — الـ harness معطوب"
        assert_frame_parity(inproc.frames, worker.frames)

    def test_results_match_across_modes(self, tmp_path):
        """النتيجة النهائية (status/text) متطابقة أيضًا لا الإطارات فقط."""
        inproc = record_inproc_chain_frames(tmp_path, _provider_factory, REQ)
        worker = record_worker_chain_frames(tmp_path, _provider_factory,
                                            REQ, _client())
        assert inproc.result is not None and worker.result is not None
        assert inproc.result.status == worker.result.status \
            == RESULT_COMPLETED
        assert inproc.result.text == worker.result.text == REPLY

    def test_parity_holds_on_failure_path(self, tmp_path):
        """مسار الفشل متوازٍ أيضًا — إطارات الخطأ نفسها بايت-بايت."""
        def failing_factory():
            p = FakeProvider()
            p.fail_always = RuntimeError("provider dead for parity")
            return p

        inproc = record_inproc_chain_frames(tmp_path, failing_factory, REQ)
        worker = record_worker_chain_frames(tmp_path, failing_factory,
                                            REQ, _client())
        assert_frame_parity(inproc.frames, worker.frames)
        assert inproc.result is not None and worker.result is not None
        assert inproc.result.status == worker.result.status == "failed"


# ═══════════ 2) بند القبول: حساسية الـ harness ═══════════


class TestHarnessSensitivity:
    """طفرة متعمدة = فشل — تعمل **بلا** Redis (تسجيلة أساس in-proc
    منسوخة ثم مطفَّرة: الحساسية خاصية المقارن لا مسار النقل)."""

    @pytest.fixture()
    def baseline(self, tmp_path):
        rec = record_inproc_chain_frames(tmp_path, _provider_factory, REQ)
        assert rec.frames
        return rec.frames

    def test_identical_copy_passes(self, baseline):
        """الضبط: نسخة مطابقة تمر — الحساسية ليست فشلًا دائمًا."""
        assert_frame_parity(baseline, copy.deepcopy(baseline))

    def test_mutated_value_caught(self, baseline):
        """تغيير حرف واحد في قيمة حقل يُضبط."""
        mutated = copy.deepcopy(baseline)
        frame = mutated[-1]
        key = next(k for k in frame
                   if k != "type" and k not in NONDETERMINISTIC_KEYS)
        frame[key] = str(frame[key]) + "X"
        with pytest.raises(AssertionError, match="غير مطابق بايت-بايت"):
            assert_frame_parity(baseline, mutated)

    def test_extra_field_caught(self, baseline):
        """حقل دخيل في إطار واحد يُضبط."""
        mutated = copy.deepcopy(baseline)
        mutated[0]["smuggled"] = True
        with pytest.raises(AssertionError):
            assert_frame_parity(baseline, mutated)

    def test_frame_type_change_caught(self, baseline):
        """تبديل نوع إطار يُضبط."""
        mutated = copy.deepcopy(baseline)
        mutated[0]["type"] = "impostor_frame"
        with pytest.raises(AssertionError):
            assert_frame_parity(baseline, mutated)

    def test_dropped_frame_caught(self, baseline):
        """إسقاط إطار (عدد مختلف) يُضبط برسالة العدد."""
        with pytest.raises(AssertionError, match="عدد الإطارات مختلف"):
            assert_frame_parity(baseline, baseline[:-1])

    def test_reordered_frames_caught(self, baseline):
        """قلب الترتيب يُضبط — التسلسل جزء من العقد لا الإطارات فقط."""
        if len(baseline) < 2:
            pytest.skip("تسجيلة بإطارين على الأقل مطلوبة للقلب")
        mutated = list(reversed(copy.deepcopy(baseline)))
        with pytest.raises(AssertionError):
            assert_frame_parity(baseline, mutated)

    def test_nondeterministic_fields_are_normalized(self, baseline):
        """الحقول غير الحتمية **وحدها** مسموح اختلافها — لا فشل زائف."""
        mutated = copy.deepcopy(baseline)
        for frame in mutated:
            for key in NONDETERMINISTIC_KEYS:
                if key in frame:
                    frame[key] = "different-value"
        assert_frame_parity(baseline, mutated)   # يجب أن تمر

    def test_normalize_strips_only_declared_keys(self):
        """التطبيع جراحي: يزيل المفاتيح المعلنة فقط ويبقي البقية حرفيًّا."""
        frame = {"type": "chain_step", "status": "ok",
                 "run_id": "r1", "budget": {"x": 1}, "duration_ms": 42}
        out = normalize_frame(frame)
        assert out == {"type": "chain_step", "status": "ok"}

    def test_bytes_are_canonical_and_order_insensitive_within_frame(self):
        """ترتيب مفاتيح dict داخل الإطار لا يهم (JSON مفروز) —
        المقارنة تضبط الدلالة لا عرَض ترتيب الإدراج في بايثون."""
        a = [{"type": "t", "alpha": 1, "beta": 2}]
        b = [{"beta": 2, "alpha": 1, "type": "t"}]
        assert frames_to_bytes(a) == frames_to_bytes(b)


# ═══════════ 3) بند القبول: حارس زمن الاستجابة ═══════════


def _first_frame_latency_inproc(tmp_path, tag: str) -> float:
    """زمن الوصول من الإرسال حتى **أول إطار** — المقياس المرئي للـ WS."""
    import pathlib
    base = pathlib.Path(tmp_path) / tag
    t0 = time.monotonic()
    holder: dict = {}

    import server
    from core.execution import ExecutionRegistry
    from core.runner import RunRequest
    from runners.chain import ChainRunner
    from tests.frame_harness import JOIN_TIMEOUT, _make_bridge

    def _capture(frame: dict) -> None:
        holder.setdefault("t_first", time.monotonic())

    bridge = _make_bridge(base, _provider_factory())
    ticket = ExecutionRegistry().register("chain")
    ChainRunner(bridge, force_strategy="direct",
                join_timeout_s=JOIN_TIMEOUT).run(
        RunRequest(mode="chain", message=REQ), ticket,
        server._RunnerWSAdapter(_capture))
    return holder["t_first"] - t0


@needs_redis
class TestLatencyGuard:
    """WS-visible latency غير متأثر ضمن سماحية — flaky-rerun مرة."""

    #: سماحية سخية عمدًا: الفارق المسموح لوصول أول إطار عبر worker
    #: (enqueue + claim + XADD + XREAD ذيلي) مقابل in-proc. القيمة
    #: تحمي من **الانحدارات الفادحة** (ثوانٍ من polling معطوب) لا
    #: تفرض أرقام microbenchmark — الأزمنة ملك الجهاز.
    TOLERANCE_S = 2.0

    def _measure_worker_first_frame(self, tmp_path) -> float:
        t0 = time.monotonic()
        holder: dict = {}
        orig_frames_append: list = []

        rec = record_worker_chain_frames(
            tmp_path, _provider_factory, REQ, _client())
        # record_worker يعيد الإطارات مجمعة — نقيس بالمجرى الكامل:
        # الزمن الكلي حتى النتيجة ثم نطرح كلفة التشغيلة نفسها لاحقًا
        # في الحارس (المقارنة النسبية أدناه).
        assert rec.frames
        return time.monotonic() - t0

    def test_worker_first_frame_within_tolerance(self, tmp_path):
        """وصول أول إطار عبر worker خلال in-proc + سماحية —
        يُعاد القياس مرة واحدة قبل الحكم بالفشل (نمط البنشات)."""
        def _attempt(idx: int) -> tuple[float, float]:
            inproc = _first_frame_latency_inproc(tmp_path,
                                                 f"lat-in-{idx}")
            t0 = time.monotonic()
            rec = record_worker_chain_frames(
                tmp_path / f"lat-w-{idx}", _provider_factory, REQ,
                _client())
            worker_total = time.monotonic() - t0
            assert rec.result is not None \
                and rec.result.status == RESULT_COMPLETED
            return inproc, worker_total

        inproc_t, worker_t = _attempt(0)
        if worker_t > inproc_t + self.TOLERANCE_S:   # flaky-rerun مرة
            inproc_t, worker_t = _attempt(1)
        assert worker_t <= inproc_t + self.TOLERANCE_S, (
            f"زمن worker {worker_t:.3f}s تجاوز in-proc {inproc_t:.3f}s "
            f"بأكثر من {self.TOLERANCE_S}s — انحدار في مسار التفويض")

    def test_heavy_frame_stream_does_not_stall_delivery(self, tmp_path):
        """تشغيلة بإطارات كثيرة: المتابعة الذيلية توصلها كلها دون
        توقف (XREAD بدفعات) — الحارس ضد polling معطوب/بطيء."""
        many = "\n".join(f"سطر {i}" for i in range(40))

        def _chatty():
            return FakeProvider(default_response=many)

        t0 = time.monotonic()
        rec = record_worker_chain_frames(
            tmp_path / "heavy", _chatty, REQ, _client())
        elapsed = time.monotonic() - t0
        if elapsed >= 10.0:   # flaky-rerun مرة
            t0 = time.monotonic()
            rec = record_worker_chain_frames(
                tmp_path / "heavy2", _chatty, REQ, _client())
            elapsed = time.monotonic() - t0
        assert rec.result is not None \
            and rec.result.status == RESULT_COMPLETED
        assert elapsed < 10.0, (
            f"تشغيلة الإطارات الكثيفة استغرقت {elapsed:.1f}s — "
            "المتابعة الذيلية متوقفة/متعثرة")
