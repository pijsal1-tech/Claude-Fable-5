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
from dataclasses import dataclass, field
from typing import Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider, Message


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

    def __init__(self):
        self._providers: dict[str, "BaseProvider"] = {}
        self._active_name: str = ""
        self._failed_names: set[str] = set()  # مزودين فشلوا مؤخراً

    def add(self, name: str, provider: "BaseProvider"):
        """إضافة مزود"""
        self._providers[name] = provider
        if not self._active_name:
            self._active_name = name

    def remove(self, name: str):
        """إزالة مزود"""
        self._providers.pop(name, None)
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
                # نجح — نشيله من الفاشلين
                self._failed_names.discard(name)
                return result, name
            except Exception as e:
                last_error = f"{name}: {e}"
                self._failed_names.add(name)
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
                self._failed_names.discard(name)
                return

            except Exception as e:
                self._failed_names.add(name)
                continue

        # كل المزودين فشلوا
        yield "❌ فشل الاتصال بكل المزودين"

    def reset_failures(self):
        """إعادة تعيين قائمة الفاشلين"""
        self._failed_names.clear()

    def get_pool_status(self) -> dict:
        """حالة كل المزودين"""
        status = {}
        for name, provider in self._providers.items():
            try:
                remaining = provider.get_remaining_calls()
            except Exception:
                remaining = -1
            status[name] = {
                "active": name == self._active_name,
                "available": provider.is_available(),
                "remaining_calls": remaining,
                "failed_recently": name in self._failed_names,
                "model": provider.config.model if provider.config else "",
            }
        return status

    # ═══════════════════════════════════════════════════
    #   Internal
    # ═══════════════════════════════════════════════════

    def _get_available(self) -> list[str]:
        """المزودين المتاحين (مش فاشلين)"""
        return [
            name for name in self._providers
            if name not in self._failed_names
        ]
