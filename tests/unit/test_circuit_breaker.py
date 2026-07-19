# -*- coding: utf-8 -*-
"""T-037 (R-403): قاطع الدائرة لكل مزود — بديل القائمة السوداء الدائمة.

يغطي:
- مصفوفة الانتقالات الكاملة: CLOSED → OPEN → HALF_OPEN → (CLOSED | OPEN).
- الـ cooldown الأسّي مع السقف (cooldown_cap_s).
- تكامل التعافي: FakeProvider يفشل ثم يتعافى عبر ProviderPool
  بدون restart — المزود يُستبعد أثناء OPEN ويُعاد استخدامه بعد الـ cooldown.
- انحدار المسار السليم: بدون أعطال، سلوك الـ pool مطابق للقديم.
- بوابة grep: reset_failures اختفت من كود الإنتاج.

نمط الساعة الوهمية: clock=lambda: now[0] مع قائمة قابلة للتغيير —
تقدُّم الزمن حتمي بالكامل (لا sleep ولا timers).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from providers.pool import BreakerState, CircuitBreaker, ProviderPool  # noqa: E402
from tests.fakes.fake_provider import FakeProvider  # noqa: E402


# ═══════════════════════════════════════════════════════
#   أدوات
# ═══════════════════════════════════════════════════════

def make_breaker(threshold=3, base=30.0, cap=600.0, jitter_fn=None):
    """قاطع بساعة وهمية — يرجع (breaker, now) حيث now[0] هو الزمن."""
    now = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=threshold,
        cooldown_base_s=base,
        cooldown_cap_s=cap,
        clock=lambda: now[0],
        jitter_fn=jitter_fn,
    )
    return breaker, now


# ═══════════════════════════════════════════════════════
#   1) مصفوفة الانتقالات
# ═══════════════════════════════════════════════════════

class TestTransitionMatrix:

    def test_initial_state_is_closed_and_available(self):
        breaker, _ = make_breaker()
        assert breaker.state is BreakerState.CLOSED
        assert breaker.available() is True

    def test_closed_stays_closed_below_threshold(self):
        breaker, _ = make_breaker(threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state is BreakerState.CLOSED
        assert breaker.available() is True

    def test_success_resets_consecutive_failure_counter(self):
        breaker, _ = make_breaker(threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()  # يصفّر العداد
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state is BreakerState.CLOSED  # 2 < 3 بعد التصفير

    def test_n_failures_open_the_breaker(self):
        breaker, _ = make_breaker(threshold=3)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state is BreakerState.OPEN
        assert breaker.available() is False

    def test_threshold_one_opens_on_first_failure(self):
        breaker, _ = make_breaker(threshold=1)
        breaker.record_failure()
        assert breaker.state is BreakerState.OPEN

    def test_open_blocks_until_cooldown_elapses(self):
        breaker, now = make_breaker(threshold=1, base=30.0)
        breaker.record_failure()
        now[0] += 29.9
        assert breaker.state is BreakerState.OPEN
        assert breaker.available() is False

    def test_cooldown_elapsed_moves_to_half_open(self):
        breaker, now = make_breaker(threshold=1, base=30.0)
        breaker.record_failure()
        now[0] += 30.0
        assert breaker.state is BreakerState.HALF_OPEN
        assert breaker.available() is True  # probe مسموح

    def test_half_open_probe_success_closes_and_resets_backoff(self):
        breaker, now = make_breaker(threshold=1, base=30.0)
        breaker.record_failure()          # trip 1 → cooldown 30
        now[0] += 30.0                     # HALF_OPEN
        breaker.record_success()           # probe نجح
        assert breaker.state is BreakerState.CLOSED
        # الـ backoff تصفّر: فشل جديد → cooldown يبدأ من base مجدداً
        breaker.record_failure()
        assert breaker.to_dict()["cooldown_s"] == 30.0

    def test_half_open_probe_failure_reopens_with_doubled_cooldown(self):
        breaker, now = make_breaker(threshold=1, base=30.0)
        breaker.record_failure()          # trip 1 → 30s
        now[0] += 30.0                     # HALF_OPEN
        breaker.record_failure()           # probe فشل → trip 2 فوراً
        assert breaker.state is BreakerState.OPEN
        assert breaker.to_dict()["cooldown_s"] == 60.0
        # ما زال OPEN بعد 59s من إعادة الفتح
        now[0] += 59.9
        assert breaker.state is BreakerState.OPEN
        now[0] += 0.1
        assert breaker.state is BreakerState.HALF_OPEN

    def test_state_property_has_no_side_effects(self):
        breaker, now = make_breaker(threshold=1, base=30.0)
        breaker.record_failure()
        now[0] += 30.0
        for _ in range(5):  # قراءات متكررة لا تغيّر شيئاً
            assert breaker.state is BreakerState.HALF_OPEN
        assert breaker.to_dict()["trip_count"] == 1


# ═══════════════════════════════════════════════════════
#   2) الـ cooldown الأسّي والسقف
# ═══════════════════════════════════════════════════════

class TestExponentialCooldown:

    def test_cooldown_doubles_each_trip(self):
        breaker, now = make_breaker(threshold=1, base=10.0, cap=600.0)
        expected = [10.0, 20.0, 40.0, 80.0]
        for exp in expected:
            breaker.record_failure()
            assert breaker.to_dict()["cooldown_s"] == exp
            now[0] += exp  # ننتظر → HALF_OPEN → الفشل التالي probe

    def test_cooldown_capped_at_cap(self):
        breaker, now = make_breaker(threshold=1, base=10.0, cap=35.0)
        seq = []
        for _ in range(4):
            breaker.record_failure()
            cd = breaker.to_dict()["cooldown_s"]
            seq.append(cd)
            now[0] += cd
        assert seq == [10.0, 20.0, 35.0, 35.0]  # مقصوص عند السقف

    def test_jitter_fn_applied_and_capped(self):
        breaker, now = make_breaker(threshold=1, base=10.0, cap=12.0,
                                    jitter_fn=lambda: 5.0)
        breaker.record_failure()
        # 10 + 5 = 15 → مقصوص عند السقف 12
        assert breaker.to_dict()["cooldown_s"] == 12.0

    def test_success_after_recovery_fully_heals_backoff(self):
        breaker, now = make_breaker(threshold=1, base=10.0, cap=600.0)
        for _ in range(3):  # ثلاث فتحات متتالية → cooldown 40
            breaker.record_failure()
            now[0] += breaker.to_dict()["cooldown_s"]
        breaker.record_success()
        d = breaker.to_dict()
        assert (d["state"], d["trip_count"], d["consecutive_failures"]) == \
            ("closed", 0, 0)


# ═══════════════════════════════════════════════════════
#   3) التحقق من المُنشئ + to_dict
# ═══════════════════════════════════════════════════════

class TestConstructorAndDict:

    def test_threshold_below_one_rejected(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0)

    @pytest.mark.parametrize("base,cap", [
        (0.0, 10.0),      # base يجب > 0
        (-1.0, 10.0),
        (20.0, 10.0),     # base يجب <= cap
    ])
    def test_invalid_cooldown_bounds_rejected(self, base, cap):
        with pytest.raises(ValueError):
            CircuitBreaker(cooldown_base_s=base, cooldown_cap_s=cap)

    def test_to_dict_snapshot_keys_and_values(self):
        breaker, _ = make_breaker(threshold=2, base=30.0)
        breaker.record_failure()
        assert breaker.to_dict() == {
            "state": "closed",
            "consecutive_failures": 1,
            "trip_count": 0,
            "cooldown_s": 0.0,
        }
        breaker.record_failure()
        d = breaker.to_dict()
        assert d["state"] == "open"
        assert d["trip_count"] == 1
        assert d["cooldown_s"] == 30.0


# ═══════════════════════════════════════════════════════
#   4) تكامل التعافي — FakeProvider عبر ProviderPool
# ═══════════════════════════════════════════════════════

class TestRecoveryIntegration:

    def _make_pool(self, threshold=2, base=30.0):
        """Pool بمزودَين وساعة وهمية مشتركة بين كل القواطع."""
        now = [0.0]
        pool = ProviderPool(
            breaker_factory=lambda: CircuitBreaker(
                failure_threshold=threshold,
                cooldown_base_s=base,
                clock=lambda: now[0],
            )
        )
        primary = FakeProvider(default_response="PRIMARY")
        backup = FakeProvider(default_response="BACKUP")
        pool.add("genspark", primary)   # active + أعلى جودة
        pool.add("deepseek", backup)
        return pool, primary, backup, now

    def test_provider_excluded_while_open_then_reused_after_cooldown(self):
        pool, primary, backup, now = self._make_pool(threshold=2, base=30.0)

        # مرحلة الفشل: primary يفشل دائماً → fallback إلى backup
        primary.fail_always = RuntimeError("provider down")
        for _ in range(2):  # فشلان → القاطع يفتح
            text, name = pool.send_with_fallback("hi")
            assert (text, name) == ("BACKUP", "deepseek")

        # OPEN: primary مستبعد تماماً — لا يُستدعى أصلاً
        calls_before = primary.call_count
        text, name = pool.send_with_fallback("hi")
        assert (text, name) == ("BACKUP", "deepseek")
        assert primary.call_count == calls_before  # صفر محاولات أثناء OPEN

        # التعافي: المزود يصلح + الـ cooldown ينقضي → probe ينجح
        primary.fail_always = None
        now[0] += 30.0
        text, name = pool.send_with_fallback("hi")
        assert (text, name) == ("PRIMARY", "genspark")  # رجع بدون restart

        # وبعد النجاح القاطع CLOSED بالكامل
        status = pool.get_pool_status()["genspark"]
        assert status["failed_recently"] is False
        assert status["breaker"]["state"] == "closed"

    def test_failed_probe_reopens_and_doubles_cooldown(self):
        pool, primary, backup, now = self._make_pool(threshold=1, base=30.0)
        primary.fail_always = RuntimeError("down")

        pool.send_with_fallback("x")            # trip 1 → OPEN 30s
        now[0] += 30.0                           # HALF_OPEN
        pool.send_with_fallback("x")            # probe فشل → OPEN 60s

        st = pool.get_pool_status()["genspark"]["breaker"]
        assert (st["state"], st["cooldown_s"]) == ("open", 60.0)

        now[0] += 59.0                           # لسه OPEN
        calls_before = primary.call_count
        pool.send_with_fallback("x")
        assert primary.call_count == calls_before

        primary.fail_always = None
        now[0] += 1.0                            # انقضى الـ 60
        text, name = pool.send_with_fallback("x")
        assert name == "genspark"

    def test_transient_failures_below_threshold_never_open(self):
        pool, primary, backup, now = self._make_pool(threshold=3, base=30.0)
        # فشل واحد عابر ثم نجاح — القاطع لا يفتح أبداً
        primary.fail_next(TimeoutError("blip"))
        text, name = pool.send_with_fallback("a")
        assert name == "deepseek"                # fallback لهذه الرسالة فقط
        text, name = pool.send_with_fallback("b")
        assert name == "genspark"                # رجع فوراً — CLOSED
        assert pool.get_pool_status()["genspark"]["breaker"]["state"] == "closed"

    def test_stream_with_fallback_uses_breaker_too(self):
        pool, primary, backup, now = self._make_pool(threshold=1, base=30.0)
        primary.fail_always = RuntimeError("down")

        chunks = list(pool.stream_with_fallback("hi"))
        assert "".join(chunks) == "BACKUP"
        assert pool.get_pool_status()["genspark"]["breaker"]["state"] == "open"

        primary.fail_always = None
        now[0] += 30.0
        chunks = list(pool.stream_with_fallback("hi"))
        assert "".join(chunks) == "PRIMARY"      # تعافى في مسار الـ stream أيضاً

    def test_all_providers_open_raises_with_last_error(self):
        pool, primary, backup, now = self._make_pool(threshold=1, base=30.0)
        primary.fail_always = RuntimeError("p-dead")
        backup.fail_always = RuntimeError("b-dead")
        with pytest.raises(RuntimeError):
            pool.send_with_fallback("x")
        # الكل OPEN → get_best يرجع النشط رغم مرضه (سلوك قديم محفوظ)
        assert pool.get_best() is primary


# ═══════════════════════════════════════════════════════
#   5) انحدار المسار السليم — بدون أعطال، لا شيء يتغيّر
# ═══════════════════════════════════════════════════════

class TestHealthyPathRegression:

    def _healthy_pool(self):
        pool = ProviderPool()  # القاطع الافتراضي (time.monotonic) — لا يتدخل
        pool.add("use_ai", FakeProvider(default_response="U"))
        pool.add("genspark", FakeProvider(default_response="G"))
        pool.add("deepseek", FakeProvider(default_response="D"))
        return pool

    def test_fallback_chain_order_unchanged(self):
        pool = self._healthy_pool()
        # النشط (use_ai أول من أُضيف) أولاً ثم الباقي حسب الجودة
        names = [n for n, _ in pool.get_fallback_chain()]
        assert names == ["use_ai", "genspark", "deepseek"]

    def test_get_best_quality_and_cost_unchanged(self):
        pool = self._healthy_pool()
        assert pool.get_best(prefer_quality=True) is pool.get("genspark")
        assert pool.get_cheapest() is pool.get("deepseek")

    def test_send_uses_active_first_and_no_breaker_noise(self):
        pool = self._healthy_pool()
        text, name = pool.send_with_fallback("hi")
        assert (text, name) == ("U", "use_ai")
        status = pool.get_pool_status()
        for entry in status.values():
            assert entry["failed_recently"] is False
            assert entry["breaker"]["state"] == "closed"
        # مفاتيح العقد القديم كلها حاضرة
        assert set(status["use_ai"]) >= {
            "active", "available", "remaining_calls",
            "failed_recently", "model"}

    def test_remove_provider_cleans_breaker(self):
        pool = self._healthy_pool()
        pool.remove("use_ai")
        assert "use_ai" not in pool.names
        assert "use_ai" not in pool.get_pool_status()
        # النشط انتقل لأول متبقٍ
        assert pool.active_name in pool.names


# ═══════════════════════════════════════════════════════
#   6) بوابة grep — reset_failures اختفت من كود الإنتاج
# ═══════════════════════════════════════════════════════

class TestResetFailuresGone:

    def test_grep_gate_reset_failures_removed(self):
        """بند القبول (R-403): reset_failures محذوفة — القاطع يملك
        دورة حياة الفشل. نفحص التعريفات/الاستدعاءات/الحقل الفعلي
        (التعليقات التوثيقية تذكر `(_failed_names)` بلا self — مسموحة)."""
        cmd = ["grep", "-rn", "--include=*.py",
               "-e", r"def reset_failures", "-e", r"reset_failures(",
               "-e", r"self\._failed_names",
               "chain/", "core/", "providers/", "context/",
               "sessions/", "server.py"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT,
                              capture_output=True, text=True)
        assert proc.returncode == 1, (
            f"بقايا reset_failures/_failed_names في كود الإنتاج:\n{proc.stdout}")
