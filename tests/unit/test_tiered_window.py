# -*- coding: utf-8 -*-
"""T-032 (R-304): Tiered Windowing + Async Summarizer — tests.

Covers (per task card + R-304 required tests):
- tier assembly math: pinned deducted first, contiguous recent strip,
  summary enters only when it covers actually-dropped turns
- floor enforcement: recent_floor survives a zero/tiny budget
- 100-turn simulation: window stays within budget AND a turn-5 fact
  remains represented (in summary) at turn 100
- degradation: summarizer failure → hard-cutoff window, degraded=True,
  error recorded in last_summary_error, nothing raised on hot path
- timing: maybe_update_summary_async returns immediately even with a
  slow summarizer (hot path never awaits summarization)
- regression: short sessions unchanged (no summary, no degradation)
- summary artifacts live in the JSONL stream and survive replay
"""
import time

import pytest

from sessions.memory import (
    SUMMARY_LABEL,
    ConversationMemory,
    SummaryArtifact,
    TieredPolicy,
    TieredWindow,
)
from sessions.store import SessionStore


class _FixedEstimator:
    """توكن واحد لكل حرف — حساب طبقات حتمي في الاختبارات."""

    def estimate(self, text: str) -> int:
        return len(text)


@pytest.fixture()
def mem(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    meta = store.create(str(tmp_path))
    return ConversationMemory(store, meta.id, estimator=_FixedEstimator())


def _fill(mem, n, width=10, prefix="m"):
    """n أدوار بمحتوى ثابت العرض — التكلفة = width لكل دور."""
    ids = []
    for i in range(n):
        ids.append(mem.append("user", f"{prefix}{i:03d}".ljust(width, ".")))
    return ids


def _concat_summarizer(turns, prev):
    """ملخّص حتمي تراكمي: يدمج النص السابق + معرفات الشريحة."""
    part = ",".join(t.content.split(".")[0] for t in turns)
    return f"{prev}|{part}" if prev else part


# ── tier assembly math ─────────────────────────────────────────────

def test_policy_validation():
    with pytest.raises(ValueError):
        TieredPolicy(token_budget=-1)
    with pytest.raises(ValueError):
        TieredPolicy(token_budget=10, recent_floor=0)


def test_all_turns_fit_no_summary_no_degradation(mem):
    _fill(mem, 5, width=10)                      # 50 توكن إجمالًا
    win = mem.tiered_window(TieredPolicy(token_budget=100, recent_floor=2))
    assert [t.content[:4] for t in win.turns] == [
        "m000", "m001", "m002", "m003", "m004"]
    assert win.summary is None and win.degraded is False
    assert win.summary_block() == ""


def test_recent_strip_is_contiguous_from_newest(mem):
    _fill(mem, 8, width=10)                      # ميزانية 35 → 3 أدوار
    win = mem.tiered_window(TieredPolicy(token_budget=35, recent_floor=1))
    assert [t.content[:4] for t in win.turns] == ["m005", "m006", "m007"]
    assert win.degraded is True                  # سقط 5 بلا ملخص


def test_pinned_deducted_first_and_always_kept(mem):
    ids = _fill(mem, 6, width=10)
    mem.pin(ids[0])                              # المثبت الأقدم يبقى
    win = mem.tiered_window(TieredPolicy(token_budget=30, recent_floor=1))
    kept = [t.content[:4] for t in win.turns]
    assert "m000" in kept                        # المثبت داخل
    # الميزانية بعد خصم المثبت (30-10=20) → دوران حديثان
    assert kept == ["m000", "m004", "m005"]
    assert win.turns[0].pinned is True


def test_summary_enters_only_when_covering_dropped(mem):
    _fill(mem, 10, width=10)
    mem.update_summary(_concat_summarizer, upto=6)   # يغطي [0,6)
    win = mem.tiered_window(TieredPolicy(token_budget=30, recent_floor=1))
    # 3 أدوار حديثة — أسقط 7 والملخص يغطي 6 منها
    assert len(win.turns) == 3
    assert win.summary is not None
    assert win.summary.covers_until == 6
    assert win.degraded is True                  # m006 سقط بلا تغطية
    assert SUMMARY_LABEL in win.summary_block()


def test_summary_fully_covering_dropped_not_degraded(mem):
    _fill(mem, 10, width=10)
    mem.update_summary(_concat_summarizer)           # يغطي الكل [0,10)
    win = mem.tiered_window(TieredPolicy(token_budget=30, recent_floor=1))
    assert win.summary is not None and win.degraded is False


def test_summary_excluded_when_dropped_turns_all_uncovered(mem):
    _fill(mem, 4, width=10)
    mem.update_summary(_concat_summarizer, upto=4)   # يغطي [0,4)
    _fill(mem, 6, width=10, prefix="n")              # أدوار جديدة 4..9
    # ميزانية تسع 3 → يسقط 4..6 فقط (كلها بعد التغطية)... لكن 0..3
    # أيضًا تسقط وهي مغطاة — نتحقق من الحالة المعاكسة بميزانية أوسع:
    win = mem.tiered_window(TieredPolicy(token_budget=65, recent_floor=1))
    # 6 أدوار حديثة تدخل (60) — يسقط 0..3 وكلها مغطاة
    assert len(win.turns) == 6
    assert win.summary is not None and win.degraded is False


# ── floor enforcement ──────────────────────────────────────────────

def test_floor_survives_zero_budget(mem):
    _fill(mem, 10, width=10)
    win = mem.tiered_window(TieredPolicy(token_budget=0, recent_floor=3))
    assert [t.content[:4] for t in win.turns] == ["m007", "m008", "m009"]


def test_floor_larger_than_history_keeps_all(mem):
    _fill(mem, 2, width=10)
    win = mem.tiered_window(TieredPolicy(token_budget=0, recent_floor=5))
    assert len(win.turns) == 2 and win.degraded is False


# ── incremental summarization ──────────────────────────────────────

def test_update_summary_is_incremental(mem):
    _fill(mem, 6, width=10)
    a1 = mem.update_summary(_concat_summarizer, upto=3)
    assert a1.covers_until == 3 and a1.text == "m000,m001,m002"
    _fill(mem, 2, width=10, prefix="x")
    a2 = mem.update_summary(_concat_summarizer)
    assert a2.covers_until == 8
    assert a2.text == "m000,m001,m002|m003,m004,m005,x000,x001"


def test_update_summary_noop_when_no_new_slice(mem):
    _fill(mem, 3)
    a1 = mem.update_summary(_concat_summarizer)
    a2 = mem.update_summary(_concat_summarizer)
    assert a2 == a1                              # لا artifact مكرر


def test_summary_artifact_survives_replay(mem, tmp_path):
    _fill(mem, 5)
    mem.update_summary(_concat_summarizer)
    # ذاكرة جديدة فوق نفس المخزن — الفعال من السجل لا من الكاش
    fresh = ConversationMemory(mem._store, mem._session_id,
                               estimator=_FixedEstimator())
    art = fresh.summary_artifact()
    assert art is not None and art.covers_until == 5
    assert fresh.summary() == art.text           # العقب وُصّل


def test_summary_records_skipped_by_turns(mem):
    _fill(mem, 3)
    mem.update_summary(_concat_summarizer)
    assert len(mem.turns()) == 3                 # الملخص ليس دورًا


# ── async: hot path never awaits ───────────────────────────────────

def test_async_returns_immediately_with_slow_summarizer(mem):
    _fill(mem, 12, width=10)

    def slow(turns, prev):
        time.sleep(0.5)
        return _concat_summarizer(turns, prev)

    t0 = time.monotonic()
    launched = mem.maybe_update_summary_async(slow, every_n=10)
    elapsed = time.monotonic() - t0
    assert launched is True
    assert elapsed < 0.2                         # لم ننتظر الـ 0.5s
    mem.wait_for_summary()
    assert mem.summary_artifact() is not None


def test_async_dedup_single_inflight(mem):
    _fill(mem, 12)
    import threading
    gate = threading.Event()

    def blocking(turns, prev):
        gate.wait(2)
        return "s"

    assert mem.maybe_update_summary_async(blocking, every_n=10) is True
    assert mem.maybe_update_summary_async(blocking, every_n=10) is False
    gate.set()
    mem.wait_for_summary()


def test_async_skips_when_slice_not_ripe(mem):
    _fill(mem, 5)
    assert mem.maybe_update_summary_async(_concat_summarizer,
                                          every_n=10) is False
    assert mem.summary_artifact() is None


def test_async_every_n_validation(mem):
    with pytest.raises(ValueError):
        mem.maybe_update_summary_async(_concat_summarizer, every_n=0)


# ── degradation ────────────────────────────────────────────────────

def test_summarizer_failure_degrades_to_hard_cutoff(mem):
    _fill(mem, 15, width=10)

    def boom(turns, prev):
        raise RuntimeError("summarizer down")

    launched = mem.maybe_update_summary_async(boom, every_n=10)
    assert launched is True
    mem.wait_for_summary()                       # لا استثناء يصلنا
    assert isinstance(mem.last_summary_error, RuntimeError)
    assert mem.summary_artifact() is None        # لا artifact كاذب
    win = mem.tiered_window(TieredPolicy(token_budget=40, recent_floor=1))
    assert win.summary is None and win.degraded is True   # قصّة صريحة
    assert len(win.turns) == 4


def test_sync_update_summary_fails_loudly(mem):
    _fill(mem, 3)
    with pytest.raises(RuntimeError):
        mem.update_summary(lambda t, p: (_ for _ in ()).throw(
            RuntimeError("x")))


# ── 100-turn simulation (acceptance) ───────────────────────────────

def test_100_turn_sim_within_budget_retaining_turn5_fact(mem):
    """قبول R-304: 100 دور تحت الميزانية وحقيقة الدور 5 ما زالت ممثلة."""
    fact = "كلمة-السر-هي-برتقالة"
    budget = 200
    policy = TieredPolicy(token_budget=budget, recent_floor=4)

    for i in range(100):
        content = fact if i == 5 else f"دور رقم {i} بمحتوى حشو إضافي"
        mem.append("user" if i % 2 == 0 else "assistant", content)
        # خطاف المسار الساخن كل رسالة — كما سيفعل الـ server
        mem.maybe_update_summary_async(_concat_summarizer_ar, every_n=10)
        mem.wait_for_summary(timeout=5)          # حتمية الاختبار فقط

    win = mem.tiered_window(policy)

    # 1) تحت الميزانية: كل الأدوار الحرفية ≤ الميزانية (الأرضية هنا
    #    أرخص من الميزانية فلا تفيض — عقد R-304 الفعلي: ما فوق
    #    الأرضية لا يتجاوز الميزانية أبدًا)
    est = _FixedEstimator()
    verbatim_cost = sum(est.estimate(t.content) for t in win.turns)
    assert verbatim_cost <= budget
    assert len(win.turns) < 100                  # قُصّ فعلًا

    # 2) حقيقة الدور 5 ممثلة: سقطت حرفيًّا لكنها داخل الملخص
    assert all(fact not in t.content for t in win.turns)
    assert win.summary is not None
    assert fact in win.summary.text
    assert win.degraded is False                 # الملخص يغطي كل الساقط
    assert SUMMARY_LABEL in win.summary_block()


def _concat_summarizer_ar(turns, prev):
    """ملخّص المحاكاة: يراكم المحتوى الكامل (يحفظ الحقائق)."""
    part = " • ".join(t.content for t in turns)
    return f"{prev} • {part}" if prev else part


# ── regression: short sessions unchanged ───────────────────────────

def test_short_session_identical_to_plain_window(mem):
    _fill(mem, 4, width=10)
    win = mem.tiered_window(TieredPolicy(token_budget=1000, recent_floor=2))
    assert [t.turn_id for t in win.turns] == [0, 1, 2, 3]
    assert win.summary is None and win.degraded is False
    # ولا خيط تلخيص أُطلق لجلسة قصيرة
    assert mem.maybe_update_summary_async(_concat_summarizer,
                                          every_n=10) is False


def test_agent_visibility_respected(mem):
    mem.append("user", "a" * 10)
    mem.append("tool", "b" * 10, visibility="agent")
    mem.append("user", "c" * 10)
    win = mem.tiered_window(TieredPolicy(token_budget=100, recent_floor=1))
    assert [t.role for t in win.turns] == ["user", "user"]
    win2 = mem.tiered_window(TieredPolicy(token_budget=100, recent_floor=1,
                                          include_agent=True))
    assert [t.role for t in win2.turns] == ["user", "tool", "user"]
