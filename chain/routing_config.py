# -*- coding: utf-8 -*-
"""T-036 (R-402): عتبات التوجيه من config + سجل قرار قابل للتفسير.

قبل هذا الملف كانت العتبات أرقامًا سحرية داخل ``chain/router.py``
(2.0/5.0/8.0 + حدود الحسابات 2/3/4) والقرار غير قابل للتفسير: «لماذا
اختار full_chain؟» بلا إجابة — لا للمستخدم ولا لاختبارات الانحدار.

الآن:
- ``RoutingThresholds`` — العتبات **كلها** في مكان واحد، تُقرأ من قسم
  ``routing:`` في config.yaml عبر ``thresholds_from_config`` مع تحقق
  صارم (schema): مفتاح مجهول أو نوع خاطئ أو ترتيب مكسور = ValueError
  صاخب عند الإقلاع، لا سلوك صامت خاطئ.
- ``RoutingRecord`` — سجل كامل يرافق **كل** ``RoutingDecision``:
  درجات الأبعاد الخمسة الخام، الإشارات المطابقة (أي أنماط أشعلت
  الدرجة)، العتبات المطبَّقة، الطبقة المثالية مقابل النهائية، مسار
  التنزيل إن حدث، وإصدار الإعدادات — الإجابة الكاملة على «لماذا؟».

⚠️ حدود السلك (corpus T-034): ``RoutingDecision.to_dict()`` و
``ComplexityAnalysis.to_dict()`` **لا يتغيّران** — السجل يعيش في حقل
منفصل (``decision.record``) وله ``to_dict()`` خاص به.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# القيم التاريخية — نفس أرقام router.py القديمة حرفيًّا (بوابة parity:
# corpus T-034 يعيد الإنتاج بايت-بايت مع الافتراضات هذه).
_DEFAULTS: dict[str, Any] = {
    "direct_max": 2.0,
    "auto_chain_max": 5.0,
    "full_chain_max": 8.0,
    "min_accounts_auto_chain": 2,
    "min_accounts_full_chain": 3,
    "min_accounts_delegate": 4,
    "version": 1,
}


@dataclass(frozen=True)
class RoutingThresholds:
    """عتبات التوجيه — مصدر وحيد، قابلة للضبط من config.yaml.

    الدلالة (score = مجموع أبعاد التعقيد الخمسة):
      score ≤ direct_max      → direct
      score ≤ auto_chain_max  → auto_chain  (يحتاج ≥ min_accounts_auto_chain)
      score ≤ full_chain_max  → full_chain  (يحتاج ≥ min_accounts_full_chain)
      score > full_chain_max  → delegate    (يحتاج ≥ min_accounts_delegate)
    """
    direct_max: float = 2.0
    auto_chain_max: float = 5.0
    full_chain_max: float = 8.0
    min_accounts_auto_chain: int = 2
    min_accounts_full_chain: int = 3
    min_accounts_delegate: int = 4
    version: int = 1

    def __post_init__(self) -> None:
        if not (self.direct_max < self.auto_chain_max
                < self.full_chain_max):
            raise ValueError(
                "routing: العتبات يجب أن تتصاعد بصرامة — "
                f"direct_max ({self.direct_max}) < auto_chain_max "
                f"({self.auto_chain_max}) < full_chain_max "
                f"({self.full_chain_max})")
        accounts = (self.min_accounts_auto_chain,
                    self.min_accounts_full_chain,
                    self.min_accounts_delegate)
        if any(a < 1 for a in accounts):
            raise ValueError(
                f"routing: حدود الحسابات يجب أن تكون ≥ 1 — {accounts}")
        if not (self.min_accounts_auto_chain
                <= self.min_accounts_full_chain
                <= self.min_accounts_delegate):
            raise ValueError(
                "routing: حدود الحسابات يجب ألا تتناقص — "
                f"auto_chain ({self.min_accounts_auto_chain}) ≤ "
                f"full_chain ({self.min_accounts_full_chain}) ≤ "
                f"delegate ({self.min_accounts_delegate})")
        if self.version < 1:
            raise ValueError(f"routing: version يجب أن يكون ≥ 1 — {self.version}")

    def to_dict(self) -> dict:
        return {
            "direct_max": self.direct_max,
            "auto_chain_max": self.auto_chain_max,
            "full_chain_max": self.full_chain_max,
            "min_accounts_auto_chain": self.min_accounts_auto_chain,
            "min_accounts_full_chain": self.min_accounts_full_chain,
            "min_accounts_delegate": self.min_accounts_delegate,
            "version": self.version,
        }


def thresholds_from_config(section: object) -> RoutingThresholds:
    """قراءة قسم ``routing:`` — صاخبة على أي انحراف عن الـ schema.

    قسم مفقود (None) = الافتراضات التاريخية (سلوك ما قبل T-036 حرفيًّا).
    """
    if section is None:
        return RoutingThresholds()
    if not isinstance(section, dict):
        raise ValueError(
            f"routing: القسم يجب أن يكون خريطة، وجدت {type(section).__name__}")

    unknown = set(section) - set(_DEFAULTS)
    if unknown:
        raise ValueError(
            f"routing: مفاتيح مجهولة {sorted(unknown)} — "
            f"المسموح: {sorted(_DEFAULTS)}")

    kwargs: dict[str, Any] = {}
    for key, default in _DEFAULTS.items():
        if key not in section:
            continue
        value = section[key]
        if isinstance(default, float):
            # عتبة: عدد (int مقبول ويُرقّى) — لا نصوص ولا bool
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"routing.{key}: يجب أن يكون عددًا، وجدت {value!r}")
            kwargs[key] = float(value)
        else:
            # حد حسابات / إصدار: عدد صحيح فقط
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"routing.{key}: يجب أن يكون عددًا صحيحًا، وجدت {value!r}")
            kwargs[key] = value

    return RoutingThresholds(**kwargs)


# ═══════════════════════════════════════════════════════
#   RoutingRecord — «لماذا اختار هذا المسار؟»
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class RoutingRecord:
    """سجل قرار توجيه واحد — كامل وقابل لإعادة الإنتاج.

    يرافق كل ``RoutingDecision`` في الحقل ``record`` (خارج ``to_dict``
    الخاص بالسلك — corpus T-034 محفوظ بايت-بايت).
    """
    mode: str                                  # chat / plan / build / edit
    forced: str | None                         # force_strategy إن وُجد
    scores: dict[str, float]                   # الأبعاد الخمسة + total
    matched_signals: dict[str, list[str]]      # الأنماط التي أشعلت الدرجات
    ideal: str                                 # الطبقة قبل قيود الميزانية
    final: str                                 # strategy النهائية على السلك
    tier: str                                  # RoutingTier النهائية
    downgrade_path: list[str] = field(default_factory=list)
    #   [] = لا تنزيل؛ ["delegate", "full_chain"] = نزل خطوة — أصدق من
    #   علم downgraded (الذي لا يُرفع إلا عند السقوط حتى direct).
    budget_total: int = 0                      # الحسابات المتاحة وقت القرار
    thresholds: dict = field(default_factory=dict)   # العتبات المطبَّقة
    config_version: int = 1                    # إصدار قسم routing

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "forced": self.forced,
            "scores": dict(self.scores),
            "matched_signals": {k: list(v)
                                for k, v in self.matched_signals.items()},
            "ideal": self.ideal,
            "final": self.final,
            "tier": self.tier,
            "downgrade_path": list(self.downgrade_path),
            "budget_total": self.budget_total,
            "thresholds": dict(self.thresholds),
            "config_version": self.config_version,
        }
