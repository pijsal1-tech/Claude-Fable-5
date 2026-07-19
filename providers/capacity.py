# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  CapacityModel — سعة صادقة من حالة حية (T-038 / R-403)

  دلالات السعة (capacity semantics):

  - «صحي» (healthy): قاطع الدائرة يسمح بالطلبات — أي ليس OPEN
    (CLOSED أو HALF_OPEN probe). مزود قاطعه مفتوح يساهم بصفر
    في الإجمالي مهما ادّعى من أرقام.

  - «متبقٍ» (remaining_calls): إجابة المزود الخام عن
    get_remaining_calls()؛ القيمة -1 تعني أن الاستعلام نفسه فشل.

  - «تقديري» (estimated): الرقم تخمين لا قياس:
      * remaining_calls < 0  → الاستعلام فشل (نساهم بصفر لكن
        الإجمالي أقل من الحقيقة — يجب تعليمه).
      * remaining_calls >= UNLIMITED_SENTINEL → افتراض
        BaseProvider «999 = غير محدود» الموثّق في base.py —
        رقم خيالي وليس عدّاً فعلياً.
    أرقام دقيقة (< 999 من override حقيقي مثل use_ai) ليست تقديرية.

  - «إجمالي» (total_available): مجموع المساهمات الفعلية
    (effective_calls) للمزودين الأصحاء فقط. لا ثوابت حدود
    حسابات صلبة هنا — الأرقام كلها قابلة للتتبع إلى
    حالة pool/breaker لحظة الطلب.

  يُستخدم من:
  - server.py: طباعة الإقلاع + /api/capacity (أرقام الـ UI).
  - مستقبلاً (بقية R-403): الراوتر يستهلك CapacityReport بدل
    عدّ الحسابات الخام.
═══════════════════════════════════════════════════════
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pool import BreakerState

if TYPE_CHECKING:
    from .pool import ProviderPool


# افتراض BaseProvider.get_remaining_calls «غير محدود» — أي رقم بهذا
# الحجم فأكثر خيال معلن لا قياس (انظر providers/base.py L285).
UNLIMITED_SENTINEL = 999


# ═══════════════════════════════════════════════════════
#   ProviderCapacity — سعة مزود واحد
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProviderCapacity:
    """لقطة سعة مزود واحد — كل حقل قابل للتتبع لمصدره."""
    name: str
    healthy: bool           # القاطع يسمح (ليس OPEN)
    breaker_state: str      # closed / open / half_open — من BreakerState
    remaining_calls: int    # إجابة المزود الخام (-1 = فشل الاستعلام)
    estimated: bool         # الرقم تخمين (sentinel أو فشل استعلام)

    @property
    def effective_calls(self) -> int:
        """المساهمة الفعلية في الإجمالي — صفر لغير الصحي أو المجهول."""
        if not self.healthy or self.remaining_calls < 0:
            return 0
        return self.remaining_calls

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "healthy": self.healthy,
            "breaker_state": self.breaker_state,
            "remaining_calls": self.remaining_calls,
            "effective_calls": self.effective_calls,
            "estimated": self.estimated,
        }


# ═══════════════════════════════════════════════════════
#   CapacityReport — لقطة السعة الكاملة
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class CapacityReport:
    """لقطة سعة كاملة — قيمة نقية، بلا side effects."""
    providers: tuple[ProviderCapacity, ...] = ()

    @property
    def total_available(self) -> int:
        """مجموع المساهمات الفعلية للمزودين الأصحاء فقط."""
        return sum(p.effective_calls for p in self.providers)

    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self.providers if p.healthy)

    @property
    def estimated(self) -> bool:
        """هل الإجمالي مبني على تخمين؟ — تقديري لو أي مزود صحي
        (مساهم في الإجمالي) رقمه تقديري. غير الصحي مساهمته صفر
        بالتعريف (دقيقة) فلا يلوّث العلم."""
        return any(p.estimated for p in self.providers if p.healthy)

    def to_dict(self) -> dict:
        return {
            "total_available": self.total_available,
            "healthy_count": self.healthy_count,
            "estimated": self.estimated,
            "providers": [p.to_dict() for p in self.providers],
        }


# ═══════════════════════════════════════════════════════
#   CapacityModel
# ═══════════════════════════════════════════════════════

class CapacityModel:
    """
    يشتق السعة من حالة الـ pool الحية (مزودون + قواطع T-037).

    القراءة عبر ``ProviderPool.get_pool_status()`` العلني —
    لا وصول لحقول خاصة، ولا تعديل على الـ pool (report نقي).

    الاستخدام:
        model = CapacityModel(pool)
        report = model.report()
        report.total_available   # رقم قابل للتتبع
        report.estimated         # هل هو تخمين؟
    """

    def __init__(self, pool: "ProviderPool | None"):
        self._pool = pool

    def report(self) -> CapacityReport:
        """لقطة سعة الآن — نقية، سريعة، بلا اتصالات خارجية."""
        if self._pool is None:
            return CapacityReport()

        caps: list[ProviderCapacity] = []
        for name, st in self._pool.get_pool_status().items():
            breaker = st.get("breaker") or {}
            state_raw = breaker.get("state", BreakerState.CLOSED.value)
            try:
                state = BreakerState(state_raw)
            except ValueError:  # حالة مجهولة → الأسوأ افتراضاً
                state = BreakerState.OPEN
            remaining = int(st.get("remaining_calls", -1))
            caps.append(ProviderCapacity(
                name=name,
                healthy=state is not BreakerState.OPEN,
                breaker_state=state.value,
                remaining_calls=remaining,
                estimated=(remaining < 0
                           or remaining >= UNLIMITED_SENTINEL),
            ))
        return CapacityReport(tuple(caps))
