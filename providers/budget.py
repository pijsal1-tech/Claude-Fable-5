# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  AccountAwareBudget — ميزانية واعية بالحسابات

  يربط بين BudgetTracker (في Chain) وعدد الحسابات الفعلية
  المتاحة في كل Provider.

  يُستخدم من RequestRouter لتقرير:
  - هل نقدر نشغل chain من N خطوات؟
  - أي provider الأنسب لهذا الطلب؟
  - هل لازم downgrade لأن الحسابات قليلة؟
═══════════════════════════════════════════════════════
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider


# ═══════════════════════════════════════════════════════
#   BudgetSnapshot — لقطة من الحالة الحالية
# ═══════════════════════════════════════════════════════

@dataclass
class BudgetSnapshot:
    """لقطة من حالة الميزانية في لحظة معينة"""
    total_available: int = 0
    per_provider: dict[str, int] = field(default_factory=dict)
    best_provider: str = ""           # الأكتر حسابات
    cheapest_provider: str = ""       # الأقل تكلفة (anonymous = أرخص)

    @property
    def can_chain(self) -> bool:
        """هل عندنا حسابات كافية لأي chain (≥ 2 calls)"""
        return self.total_available >= 2

    def can_afford(self, steps: int) -> bool:
        """هل عندنا حسابات كافية لـ chain من N خطوات"""
        return self.total_available >= steps

    def best_provider_for(self, steps: int) -> str:
        """أي provider يقدر يتحمل N خطوات (الأكتر حسابات أولاً)"""
        for name, remaining in sorted(
            self.per_provider.items(), key=lambda x: -x[1]
        ):
            if remaining >= steps:
                return name
        return self.cheapest_provider or self.best_provider

    def to_dict(self) -> dict:
        return {
            "total_available": self.total_available,
            "per_provider": self.per_provider,
            "best_provider": self.best_provider,
            "cheapest_provider": self.cheapest_provider,
        }


# ═══════════════════════════════════════════════════════
#   Provider Cost Profile
# ═══════════════════════════════════════════════════════

# ترتيب التكلفة — الأقل تكلفة أولاً
# DeepSeek = مجاني بلا حدود (anonymous sessions)
# Genspark = حسابات كثيرة مع rotation
# AlleAI = حسابات مع daily limit
# UseAI = حساب واحد = رسالة واحدة (الأغلى)
_COST_RANK = {
    "deepseek": 0,    # مجاني — anonymous
    "genspark": 1,    # رخيص — rotation كبير
    "alle_ai": 2,     # متوسط — daily limit
    "use_ai": 3,      # غالي — 1 حساب = 1 رسالة
}


# ═══════════════════════════════════════════════════════
#   AccountAwareBudget
# ═══════════════════════════════════════════════════════

class AccountAwareBudget:
    """
    يسأل كل Provider: كم حساب/رسالة متاح؟
    يحسب: هل نقدر نشغل chain من N خطوات؟

    الاستخدام:
        budget = AccountAwareBudget({"genspark": provider1, "use_ai": provider2})
        snapshot = budget.check()
        if snapshot.can_afford(4):
            # نقدر نشغل pipeline
        else:
            # downgrade لـ direct
    """

    def __init__(self, providers: dict[str, "BaseProvider"] | None = None):
        self._providers: dict[str, "BaseProvider"] = providers or {}

    def register(self, name: str, provider: "BaseProvider"):
        """تسجيل مزود جديد"""
        self._providers[name] = provider

    def unregister(self, name: str):
        """إلغاء تسجيل مزود"""
        self._providers.pop(name, None)

    @property
    def provider_names(self) -> list[str]:
        return list(self._providers.keys())

    def check(self) -> BudgetSnapshot:
        """
        يفحص كل provider ويرجع لقطة كاملة.
        هذه العملية سريعة — لا تتصل بأي API خارجي.
        """
        per_provider: dict[str, int] = {}

        for name, provider in self._providers.items():
            try:
                remaining = provider.get_remaining_calls()
            except Exception:
                remaining = 0
            per_provider[name] = remaining

        total = sum(per_provider.values())

        # أكتر provider عنده حسابات
        best = max(per_provider, key=lambda n: per_provider[n], default="") if per_provider else ""

        # أرخص provider (حسب ترتيب التكلفة) — بشرط إنه متاح
        available_providers = [n for n, r in per_provider.items() if r > 0]
        cheapest = ""
        if available_providers:
            cheapest = min(
                available_providers,
                key=lambda n: _COST_RANK.get(n, 99)
            )

        return BudgetSnapshot(
            total_available=total,
            per_provider=per_provider,
            best_provider=best,
            cheapest_provider=cheapest,
        )

    def reserve_for_chain(self, steps: int) -> tuple[bool, str]:
        """
        هل عندنا حسابات كفاية لـ chain من N خطوات؟

        Returns:
            (can_afford, best_provider_name)
        """
        snapshot = self.check()
        if snapshot.can_afford(steps):
            best = snapshot.best_provider_for(steps)
            return True, best
        return False, snapshot.cheapest_provider

    def suggest_max_steps(self) -> int:
        """
        أقصى عدد خطوات ممكن بالحسابات المتاحة.
        مفيد للـ downgrade: لو عندنا 3 حسابات بس → max 3 steps.
        """
        snapshot = self.check()
        return max(snapshot.per_provider.values(), default=0)

    def get_fallback_order(self) -> list[str]:
        """
        ترتيب الـ providers للـ fallback — الأرخص أولاً.
        يستبعد providers بدون حسابات.
        """
        snapshot = self.check()
        available = [
            (name, remaining)
            for name, remaining in snapshot.per_provider.items()
            if remaining > 0
        ]
        return [
            name for name, _ in sorted(
                available,
                key=lambda x: _COST_RANK.get(x[0], 99)
            )
        ]
