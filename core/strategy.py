# -*- coding: utf-8 -*-
"""T-035 (R-401): المفردات الموحّدة للتوجيه — المصدر الوحيد للحقيقة.

قبل هذا الملف كانت هناك مفردتان متداخلتان: الأوركستريتور يتكلم
{direct, context_window, chunk_chain, map_reduce, pipeline, delegate}
والراوتر يتكلم {direct, auto_chain, full_chain, delegate}، والترجمة
بينهما مبعثرة في شروط نصية حرة — إضافة استراتيجية كانت تتطلب لمس
المفردتين + نقاط الترجمة، والأخطاء توجّه بصمت لبانيات خاطئة.

الآن طبقتان **صريحتان** (تصميم R-401):

- ``RoutingTier`` — قرار الراوتر: *كم* من الجهد (direct / chained /
  delegate). لا يعرف شيئًا عن البانيات.
- ``ExecutionStrategy`` — قرار الأوركستريتور *داخل* الطبقة: *أي* باني
  من الستة ينفّذ.
- ``RouteLabel`` — مفردات السلك (wire) لحقل ``RoutingDecision.strategy``:
  الأسماء الأربعة التاريخية ثابتة بايت-بايت (الـ corpus الذهبي لـ T-034
  + عملاء الـ WS يعتمدون عليها). ``auto_chain``/``full_chain`` هما
  متغيّرا عمق لنفس الطبقة ``CHAINED`` — الخاصية ``tier`` تحسم ذلك في
  مكان واحد بدل شرطي server.py النصيين.

┌────────────────── STRATEGY_TABLE (المرجع الوحيد) ──────────────────┐
│ ExecutionStrategy   │ RoutingTier │ الباني              │ متى؟      │
│ DIRECT              │ DIRECT      │ build_direct         │ score ≤2  │
│ CONTEXT_WINDOW      │ CHAINED     │ build_context_window │ ≤4 ملف≤3  │
│ CHUNK_CHAIN         │ CHAINED     │ build_chunk_chain    │ ≤7 ملف 1  │
│ MAP_REDUCE          │ CHAINED     │ build_map_reduce     │ ملفات ≥2  │
│ PIPELINE            │ CHAINED     │ build_pipeline       │ score >7  │
│ DELEGATE            │ DELEGATE    │ build_delegate       │ DelegateBridge│
└────────────────────────────────────────────────────────────────────┘

إضافة استراتيجية جديدة = عضو enum + سطر واحد في الجدول؛ فحص الاكتمال
عند الاستيراد + ``assert_never`` في نقاط الفصل يفشلان بصوت عالٍ لو
نسي أحدٌ فرعًا.

ملاحظة صدق (لا دورات استيراد): البانيات في ``chain/strategies.py``
تسمّي نفسها بنصوصها التاريخية (``strategy_name="direct"`` …) — جعلها
تستورد هذا الملف كان سيخلق دورة (هذا الملف يستورد البانيات للجدول).
التطابق نص-الباني ↔ قيمة-الـ enum مثبَّت باختبار وحدة بدل الاقتران.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import Callable

from chain.strategies import (
    StrategyResult,
    build_chunk_chain,
    build_context_window,
    build_delegate,
    build_direct,
    build_map_reduce,
    build_pipeline,
)


# ═══════════════════════════════════════════════════════
#   الطبقة 1: RoutingTier — قرار الراوتر (كم من الجهد؟)
# ═══════════════════════════════════════════════════════

@unique
class RoutingTier(StrEnum):
    """طبقة التوجيه — يقررها الراوتر بالتعقيد + الميزانية."""
    DIRECT = "direct"      # رسالة واحدة → رد واحد
    CHAINED = "chained"    # سلسلة خطوات (auto_chain / full_chain)
    DELEGATE = "delegate"  # brief → implement → review → land


# ═══════════════════════════════════════════════════════
#   الطبقة 2: ExecutionStrategy — قرار الأوركستريتور (أي باني؟)
# ═══════════════════════════════════════════════════════

@unique
class ExecutionStrategy(StrEnum):
    """استراتيجية التنفيذ — البانيات الستة في chain/strategies.py."""
    DIRECT = "direct"
    CONTEXT_WINDOW = "context_window"
    CHUNK_CHAIN = "chunk_chain"
    MAP_REDUCE = "map_reduce"
    PIPELINE = "pipeline"
    DELEGATE = "delegate"

    @classmethod
    def parse(cls, name: object) -> "ExecutionStrategy | None":
        """تحويل نص حر إلى عضو — None للمجهول (نقطة العبور الوحيدة)."""
        try:
            return cls(name)  # type: ignore[arg-type]
        except ValueError:
            return None


# ═══════════════════════════════════════════════════════
#   مفردات السلك: RouteLabel — RoutingDecision.strategy
# ═══════════════════════════════════════════════════════

@unique
class RouteLabel(StrEnum):
    """الأسماء الأربعة التاريخية على السلك — ثابتة بايت-بايت
    (corpus T-034 الذهبي + عملاء WS). AUTO_CHAIN/FULL_CHAIN متغيّرا
    عمق لطبقة CHAINED الواحدة."""
    DIRECT = "direct"
    AUTO_CHAIN = "auto_chain"
    FULL_CHAIN = "full_chain"
    DELEGATE = "delegate"

    @classmethod
    def parse(cls, name: object) -> "RouteLabel | None":
        """تحويل نص حر إلى عضو — None للمجهول."""
        try:
            return cls(name)  # type: ignore[arg-type]
        except ValueError:
            return None

    @property
    def tier(self) -> RoutingTier:
        """الترجمة label→tier — كانت شرطين نصيين في server.py."""
        if self is RouteLabel.DIRECT:
            return RoutingTier.DIRECT
        if self is RouteLabel.AUTO_CHAIN or self is RouteLabel.FULL_CHAIN:
            return RoutingTier.CHAINED
        if self is RouteLabel.DELEGATE:
            return RoutingTier.DELEGATE
        raise AssertionError(f"RouteLabel بلا tier: {self!r}")  # pragma: no cover


# ═══════════════════════════════════════════════════════
#   STRATEGY_TABLE — السجل الوحيد للبانيات
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class StrategySpec:
    """مواصفة استراتيجية واحدة — صف في السجل."""
    strategy: ExecutionStrategy
    tier: RoutingTier
    builder: Callable[..., StrategyResult]
    summary: str  # توثيق سطر واحد (الجدول كوثيقة)


STRATEGY_TABLE: dict[ExecutionStrategy, StrategySpec] = {
    ExecutionStrategy.DIRECT: StrategySpec(
        ExecutionStrategy.DIRECT, RoutingTier.DIRECT, build_direct,
        "خطوة واحدة — الطلب (+ سياق اختياري) في رسالة واحدة"),
    ExecutionStrategy.CONTEXT_WINDOW: StrategySpec(
        ExecutionStrategy.CONTEXT_WINDOW, RoutingTier.CHAINED,
        build_context_window,
        "تحليل ثم تنفيذ — الملف كاملًا يدخل نافذة السياق"),
    ExecutionStrategy.CHUNK_CHAIN: StrategySpec(
        ExecutionStrategy.CHUNK_CHAIN, RoutingTier.CHAINED,
        build_chunk_chain,
        "ملف ضخم مقسّم chunks متسلسلة ثم دمج"),
    ExecutionStrategy.MAP_REDUCE: StrategySpec(
        ExecutionStrategy.MAP_REDUCE, RoutingTier.CHAINED,
        build_map_reduce,
        "ملفات متعددة — map لكل ملف ثم reduce موحِّد"),
    ExecutionStrategy.PIPELINE: StrategySpec(
        ExecutionStrategy.PIPELINE, RoutingTier.CHAINED, build_pipeline,
        "plan → implement (→ review عند المخاطر) → finalize"),
    ExecutionStrategy.DELEGATE: StrategySpec(
        ExecutionStrategy.DELEGATE, RoutingTier.DELEGATE, build_delegate,
        "brief → implement → review → land — مسار DelegateBridge"),
}


# فحص الاكتمال عند الاستيراد — عضو بلا صف في الجدول = انفجار مبكر،
# لا misroute صامت وقت التشغيل.
_missing = [m for m in ExecutionStrategy if m not in STRATEGY_TABLE]
if _missing:  # pragma: no cover — يستحيل الوصول والجدول كامل
    raise RuntimeError(
        f"STRATEGY_TABLE ناقص أعضاء: {[m.value for m in _missing]}")
del _missing
