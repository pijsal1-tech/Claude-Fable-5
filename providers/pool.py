# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ProviderPool — تجميع وإدارة مزودين متعددين

  يدير مجموعة مزودين — يختار الأنسب لكل طلب.
  يوفر Fallback تلقائي عند فشل/نفاد provider معين.

  يُستخدم من:
  - server.py: بدلاً من provider واحد global
  - RequestRouter: للاستعلام عن الأنسب
  - ChainExecutor: للتبديل أثناء التنفيذ
═══════════════════════════════════════════════════════
"""
import time
from enum import StrEnum, unique
from typing import Callable, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider, Message


# ═══════════════════════════════════════════════════════
#   Circuit Breaker (R-403)
# ═══════════════════════════════════════════════════════

@unique
class BreakerState(StrEnum):
    """
    حالات قاطع الدائرة لكل مزود.

    مخطط الانتقالات (breaker states diagram):

        ┌──────────────────────────────────────────────────┐
        │                                                  │
        │   success / failures < N                         │
        │   ┌────┐                                         │
        │   ▼    │                                         │
        │ ┌────────┐  N consecutive   ┌────────┐           │
        │ │ CLOSED │ ───failures────▶ │  OPEN  │           │
        │ └────────┘                  └────────┘           │
        │   ▲    ▲                      │    ▲             │
        │   │    │        cooldown      │    │ probe fails │
        │   │    │        elapses       ▼    │ (cooldown   │
        │   │    │                 ┌───────────┐  ×2, cap) │
        │   │    └──probe succeeds─│ HALF_OPEN │──────┘    │
        │   │      (backoff reset) └───────────┘           │
        └──────────────────────────────────────────────────┘

    - CLOSED:    المزود سليم — الطلبات تمر عادي.
    - OPEN:      المزود مستبعد حتى انقضاء الـ cooldown.
    - HALF_OPEN: انقضى الـ cooldown — يُسمح بطلب probe واحد؛
                 نجاحه → CLOSED (وتصفير الـ backoff)،
                 فشله → OPEN فوراً بـ cooldown مضاعف (بسقف).
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    قاطع دائرة لمزود واحد — يستبدل القائمة السوداء الدائمة
    (_failed_names) التي كانت تُبقي المزود ميتاً حتى restart.

    الحالة تُحسب lazily من الطوابع الزمنية — لا timers ولا threads:
    - _opened_at is None                          → CLOSED
    - clock() - _opened_at < _current_cooldown    → OPEN
    - غير ذلك                                     → HALF_OPEN

    الـ cooldown أسّي: min(base * 2**(trip_count-1), cap).
    jitter_fn حقن اختياري (معطّل افتراضياً عمداً — حتمية الاختبارات؛
    الـ roadmap يذكر jitter كتخفيف للـ thundering herd، ويمكن
    تفعيله production بتمرير jitter_fn=random.random مثلاً).
    """

    def __init__(self,
                 failure_threshold: int = 3,
                 cooldown_base_s: float = 30.0,
                 cooldown_cap_s: float = 600.0,
                 clock: Callable[[], float] = time.monotonic,
                 jitter_fn: "Callable[[], float] | None" = None):
        if failure_threshold < 1:
            raise ValueError(
                f"failure_threshold يجب أن يكون >= 1 — وصل: {failure_threshold}")
        if not (0 < cooldown_base_s <= cooldown_cap_s):
            raise ValueError(
                "يجب أن يكون 0 < cooldown_base_s <= cooldown_cap_s — "
                f"وصل: base={cooldown_base_s}, cap={cooldown_cap_s}")
        self._failure_threshold = failure_threshold
        self._cooldown_base_s = cooldown_base_s
        self._cooldown_cap_s = cooldown_cap_s
        self._clock = clock
        self._jitter_fn = jitter_fn
        self._consecutive_failures = 0
        self._trip_count = 0
        self._opened_at: float | None = None
        self._current_cooldown = 0.0

    @property
    def state(self) -> BreakerState:
        """الحالة الحالية — محسوبة من الطوابع الزمنية (بدون side effects)"""
        if self._opened_at is None:
            return BreakerState.CLOSED
        if self._clock() - self._opened_at < self._current_cooldown:
            return BreakerState.OPEN
        return BreakerState.HALF_OPEN

    def available(self) -> bool:
        """هل يُسمح بمحاولة؟ (CLOSED أو HALF_OPEN probe)"""
        return self.state is not BreakerState.OPEN

    def record_success(self) -> None:
        """نجاح — يعيد القاطع إلى CLOSED ويصفّر الـ backoff بالكامل"""
        self._consecutive_failures = 0
        self._trip_count = 0
        self._opened_at = None
        self._current_cooldown = 0.0

    def record_failure(self) -> None:
        """
        فشل — في HALF_OPEN فشل الـ probe يفتح القاطع فوراً
        بـ cooldown مضاعف؛ في CLOSED يزيد العداد ويفتح عند بلوغ N.
        """
        now = self._clock()
        if self.state is BreakerState.HALF_OPEN:
            self._trip(now)
            return
        self._consecutive_failures += 1
        if (self._consecutive_failures >= self._failure_threshold
                and self._opened_at is None):
            self._trip(now)

    def _trip(self, now: float) -> None:
        """فتح القاطع — cooldown أسّي بسقف cooldown_cap_s"""
        self._trip_count += 1
        cooldown = min(
            self._cooldown_base_s * (2 ** (self._trip_count - 1)),
            self._cooldown_cap_s,
        )
        if self._jitter_fn is not None:
            cooldown = min(cooldown + self._jitter_fn(), self._cooldown_cap_s)
        self._current_cooldown = cooldown
        self._opened_at = now

    def to_dict(self) -> dict:
        """لقطة حالة للـ status/debugging"""
        return {
            "state": str(self.state),
            "consecutive_failures": self._consecutive_failures,
            "trip_count": self._trip_count,
            "cooldown_s": self._current_cooldown,
        }


# ═══════════════════════════════════════════════════════
#   Provider Priority / Cost
# ═══════════════════════════════════════════════════════

# ترتيب الأولوية (الأفضل أولاً — context + quality)
_QUALITY_RANK = {
    "genspark": 1,    # Claude/GPT via Genspark — أفضل جودة
    "use_ai": 2,      # Claude via Use.ai — streaming حقيقي
    "alle_ai": 3,     # Gemini + Nova — dual response
    "deepseek": 4,    # DeepSeek R1 — free fallback
}

# ترتيب التكلفة (الأرخص أولاً)
_COST_RANK = {
    "deepseek": 0,    # مجاني — anonymous
    "genspark": 1,    # رخيص — rotation كبير
    "alle_ai": 2,     # متوسط — daily limit
    "use_ai": 3,      # غالي — 1 حساب = 1 رسالة
}


# ═══════════════════════════════════════════════════════
#   ProviderPool
# ═══════════════════════════════════════════════════════

class ProviderPool:
    """
    مجموعة مزودين مع:
    - اختيار الأنسب لكل طلب
    - Fallback تلقائي عند الفشل
    - تبديل أثناء chain

    الاستخدام:
        pool = ProviderPool()
        pool.add("genspark", genspark_provider)
        pool.add("use_ai", use_ai_provider)
        pool.add("deepseek", deepseek_provider)

        # اختيار الأفضل
        provider = pool.get_best()

        # send مع fallback تلقائي
        result = pool.send_with_fallback(prompt, history, system_prompt)
    """

    def __init__(self,
                 breaker_factory: "Callable[[], CircuitBreaker] | None" = None):
        self._providers: dict[str, "BaseProvider"] = {}
        self._active_name: str = ""
        # قاطع دائرة لكل مزود (R-403) — يستبدل _failed_names الدائمة
        self._breaker_factory: Callable[[], CircuitBreaker] = (
            breaker_factory or CircuitBreaker)
        self._breakers: dict[str, CircuitBreaker] = {}

    def add(self, name: str, provider: "BaseProvider"):
        """إضافة مزود"""
        self._providers[name] = provider
        self._breakers.setdefault(name, self._breaker_factory())
        if not self._active_name:
            self._active_name = name

    def remove(self, name: str):
        """إزالة مزود"""
        self._providers.pop(name, None)
        self._breakers.pop(name, None)
        if self._active_name == name:
            self._active_name = next(iter(self._providers), "")

    @property
    def active_name(self) -> str:
        return self._active_name

    @active_name.setter
    def active_name(self, name: str):
        if name in self._providers:
            self._active_name = name

    @property
    def active(self) -> "BaseProvider | None":
        """المزود النشط حالياً"""
        return self._providers.get(self._active_name)

    @property
    def names(self) -> list[str]:
        return list(self._providers.keys())

    @property
    def all_providers(self) -> dict[str, "BaseProvider"]:
        return dict(self._providers)

    def get(self, name: str) -> "BaseProvider | None":
        return self._providers.get(name)

    def get_best(self, prefer_quality: bool = True) -> "BaseProvider | None":
        """
        يختار الأفضل — حسب الجودة أو التكلفة.

        Args:
            prefer_quality: True = الأفضل جودة أولاً، False = الأرخص أولاً
        """
        available = self._get_available()
        if not available:
            return self.active  # fallback to active even if unhealthy

        rank = _QUALITY_RANK if prefer_quality else _COST_RANK
        sorted_providers = sorted(
            available,
            key=lambda n: rank.get(n, 99)
        )
        return self._providers[sorted_providers[0]]

    def get_cheapest(self) -> "BaseProvider | None":
        """الأرخص (أقل استهلاك حسابات)"""
        return self.get_best(prefer_quality=False)

    def get_fallback_chain(self) -> list[tuple[str, "BaseProvider"]]:
        """
        ترتيب الـ providers للـ fallback.
        يبدأ بالنشط → ثم الباقي حسب الجودة.
        يستبعد المزودين الفاشلين مؤخراً.
        """
        result = []
        available = self._get_available()

        # النشط أولاً
        if self._active_name in available:
            result.append((self._active_name, self._providers[self._active_name]))
            available.remove(self._active_name)

        # الباقي حسب الجودة
        for name in sorted(available, key=lambda n: _QUALITY_RANK.get(n, 99)):
            result.append((name, self._providers[name]))

        return result

    def send_with_fallback(self, prompt: str,
                           history: "list[Message] | None" = None,
                           system_prompt: str = "") -> tuple[str, str]:
        """
        يرسل رسالة مع fallback تلقائي.
        يجرب كل provider بالترتيب حتى ينجح.

        Returns:
            (response_text, provider_name_used)

        Raises:
            RuntimeError: لو كل المزودين فشلوا
        """
        chain = self.get_fallback_chain()
        last_error = ""

        for name, provider in chain:
            try:
                result = provider.send(prompt, history, system_prompt)
                # نجح — القاطع يرجع CLOSED والـ backoff يتصفّر
                self._breakers[name].record_success()
                return result, name
            except Exception as e:
                last_error = f"{name}: {e}"
                self._breakers[name].record_failure()
                continue

        raise RuntimeError(f"كل المزودين فشلوا — آخر خطأ: {last_error}")

    def stream_with_fallback(self, prompt: str,
                             history: "list[Message] | None" = None,
                             system_prompt: str = "") -> Generator[str, None, None]:
        """
        Stream مع fallback — يجرب أول provider متاح.
        لو فشل أثناء الـ stream → ما يقدر يحول (بنات بالنسبة للـ stream).
        فبنجرب الـ fallback قبل ما نبدأ.
        """
        chain = self.get_fallback_chain()

        for name, provider in chain:
            try:
                # نجرب نبدأ stream
                gen = provider.stream(prompt, history, system_prompt)
                # yield من الـ generator
                first_chunk = None
                try:
                    first_chunk = next(gen)
                except StopIteration:
                    # Stream فاضي — نجرب التالي
                    continue

                # نجح — yield all
                yield first_chunk
                yield from gen
                self._breakers[name].record_success()
                return

            except Exception:
                self._breakers[name].record_failure()
                continue

        # كل المزودين فشلوا
        yield "❌ فشل الاتصال بكل المزودين"

    # ملاحظة (R-403): الدالة reset_failures حُذفت — كانت لا تُستدعى أبداً،
    # وقاطع الدائرة يملك دورة حياة الفشل بالكامل الآن
    # (cooldown → half-open probe → recovery تلقائياً).

    def get_pool_status(self) -> dict:
        """حالة كل المزودين"""
        status = {}
        for name, provider in self._providers.items():
            try:
                remaining = provider.get_remaining_calls()
            except Exception:
                remaining = -1
            breaker = self._breakers[name]
            status[name] = {
                "active": name == self._active_name,
                "available": provider.is_available(),
                "remaining_calls": remaining,
                # مفتاح متوافق مع العقد القديم — True لو القاطع مش CLOSED
                "failed_recently": breaker.state is not BreakerState.CLOSED,
                "breaker": breaker.to_dict(),
                "model": provider.config.model if provider.config else "",
            }
        return status

    # ═══════════════════════════════════════════════════
    #   Internal
    # ═══════════════════════════════════════════════════

    def _get_available(self) -> list[str]:
        """المزودين المتاحين (القاطع يسمح — CLOSED أو HALF_OPEN)"""
        return [
            name for name in self._providers
            if self._breakers[name].available()
        ]
