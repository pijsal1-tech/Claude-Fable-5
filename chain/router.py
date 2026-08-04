# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  RequestRouter — موجّه الطلبات الذكي

  الطبقة المحورية بين المستخدم والنظام.
  يربط: SmartOrchestrator + AccountAwareBudget + Provider

  يقرر تلقائياً:
  - direct: رسالة واحدة → رد واحد (الأسرع)
  - auto_chain: 2-3 خطوات (analyze + execute)
  - full_chain: 3-4 خطوات (pipeline كامل)
  - delegate: brief → implement → review → land

  ويعمل downgrade ذكي لما الحسابات قليلة.
═══════════════════════════════════════════════════════
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, assert_never

from core.strategy import ExecutionStrategy, RouteLabel, RoutingTier

from .routing_config import RoutingRecord, RoutingThresholds

if TYPE_CHECKING:
    from chain.orchestrator import SmartOrchestrator, ComplexityAnalysis
    from providers.budget import AccountAwareBudget, BudgetSnapshot
    from providers.base import BaseProvider  # noqa: F401 — hint نوعي للوثائق (F-011: إيجابية كاذبة مقصودة)


# ═══════════════════════════════════════════════════════
#   RoutingDecision — نتيجة التوجيه
# ═══════════════════════════════════════════════════════

@dataclass
class RoutingDecision:
    """نتيجة قرار التوجيه"""
    strategy: str                      # مفردات السلك — RouteLabel قيمًا (T-035)
    provider_name: str = ""            # اسم الـ provider المختار
    chain_strategy: str | None = None  # قيمة ExecutionStrategy للأوركستريتور
    max_steps: int = 1                 # أقصى عدد خطوات مسموح
    downgraded: bool = False           # هل تم تنزيل التعقيد بسبب نقص حسابات؟
    downgrade_reason: str = ""         # سبب التنزيل
    complexity_score: float = 0.0      # النتيجة الأصلية للتعقيد
    # T-036 (R-402): سجل القرار الكامل — خارج to_dict عمدًا (السلك
    # وcorpus T-034 محفوظان بايت-بايت)؛ للقراءة: decision.record.to_dict()
    record: RoutingRecord | None = field(default=None, compare=False)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "provider_name": self.provider_name,
            "chain_strategy": self.chain_strategy,
            "max_steps": self.max_steps,
            "downgraded": self.downgraded,
            "downgrade_reason": self.downgrade_reason,
            "complexity_score": self.complexity_score,
        }

    @property
    def tier(self) -> "RoutingTier":
        """T-035 (R-401): طبقة التوجيه — نقطة الفصل الوحيدة للمرسِل.

        كانت شرطين نصيين في server.py. النص المجهول (ممرّر حرفيًّا
        من force_strategy — quirk مثبَّت في corpus T-034) يُرسَل direct،
        وهو نفس سلوك الإرسال القديم (لا يطابق أي شرط → المسار العادي).
        """
        label = RouteLabel.parse(self.strategy)
        if label is None:
            return RoutingTier.DIRECT
        return label.tier


# ═══════════════════════════════════════════════════════
#   Strategy Thresholds
# ═══════════════════════════════════════════════════════

# T-036 (R-402): الأرقام السحرية انتقلت إلى chain/routing_config.py
# (RoutingThresholds) وتُقرأ من قسم routing: في config.yaml — هنا لا
# توجد عتبات مضمّنة (بوابة grep في check.sh تفرض ذلك).


# ═══════════════════════════════════════════════════════
#   RequestRouter
# ═══════════════════════════════════════════════════════

class RequestRouter:
    """
    يحلل الطلب ويقرر المسار الأنسب تلقائياً.

    المعادلة:
    1. يحسب complexity_score (من SmartOrchestrator)
    2. يفحص الحسابات المتاحة (من AccountAwareBudget)
    3. يختار أعلى استراتيجية ممكنة
    4. يعمل downgrade لو الحسابات مش كفاية

    الاستخدام:
        router = RequestRouter(orchestrator, budget)
        decision = router.route("أنشئ API كامل مع auth", file_content, files, "build")
        if decision.tier is RoutingTier.DIRECT:
            # المسار العادي
        elif decision.tier is RoutingTier.CHAINED:
            # chain_bridge.start_chain(...)
        elif decision.tier is RoutingTier.DELEGATE:
            # delegate_bridge.run_delegation(...)
    """

    def __init__(self,
                 orchestrator: "SmartOrchestrator",
                 budget: "AccountAwareBudget",
                 active_provider_name: str = "",
                 thresholds: RoutingThresholds | None = None):
        self._orchestrator = orchestrator
        self._budget = budget
        self._active_provider_name = active_provider_name
        # T-036 (R-402): العتبات محقونة — الافتراضات = القيم التاريخية
        self._thresholds = thresholds or RoutingThresholds()

    # R-102 (T-008): public API — switch handlers must not poke the private
    # attribute; they call this property instead.
    @property
    def active_provider_name(self) -> str:
        return self._active_provider_name

    @active_provider_name.setter
    def active_provider_name(self, name: str):
        self._active_provider_name = name

    def route(self,
              user_request: str,
              file_content: str | None = None,
              files: dict[str, str] | None = None,
              mode: str = "chat",
              force_strategy: str | None = None) -> RoutingDecision:
        """
        يحلل الطلب ويرجع RoutingDecision.

        Args:
            user_request: نص طلب المستخدم
            file_content: محتوى ملف واحد (اختياري)
            files: {path: content} — ملفات متعددة (اختياري)
            mode: الوضع الحالي (chat/plan/build/edit)
            force_strategy: فرض استراتيجية معينة (اختياري)

        Returns:
            RoutingDecision مع كل التفاصيل
        """
        # ── 1. حساب التعقيد ──
        analysis = self._orchestrator.analyze_complexity(
            user_request=user_request,
            files=files,
            file_content=file_content,
        )
        score = analysis.total

        # ── 2. فحص الميزانية ──
        budget_snapshot = self._budget.check()

        # ── 3. اختيار أعلى استراتيجية ممكنة (أو فرض واحدة) ──
        if force_strategy:
            decision = self._forced_route(
                force_strategy, score, analysis, budget_snapshot
            )
            return self._attach_record(
                decision, mode=mode, forced=force_strategy,
                analysis=analysis, ideal=decision.strategy,
                budget=budget_snapshot)

        # ── Mode Override: chat mode = always direct ──
        if mode == "chat":
            decision = RoutingDecision(
                strategy=RouteLabel.DIRECT.value,
                provider_name=self._select_provider(budget_snapshot, 1),
                max_steps=1,
                complexity_score=score,
            )
            return self._attach_record(
                decision, mode=mode, forced=None, analysis=analysis,
                ideal=RouteLabel.DIRECT.value, budget=budget_snapshot)

        # ── 4. التوجيه بناءً على التعقيد + الحسابات ──
        ideal = self._ideal_strategy(score, analysis)
        decision = self._apply_budget_constraints(ideal, score, analysis, budget_snapshot)

        return self._attach_record(
            decision, mode=mode, forced=None, analysis=analysis,
            ideal=ideal.value, budget=budget_snapshot)

    # ═══ T-036 (R-402): بناء السجل — كل المسارات تمر من هنا ═══

    def _attach_record(self, decision: RoutingDecision, *,
                       mode: str, forced: str | None,
                       analysis: "ComplexityAnalysis",
                       ideal: str,
                       budget: "BudgetSnapshot") -> RoutingDecision:
        """يبني RoutingRecord ويعلّقه — الإجابة الكاملة على «لماذا؟».

        مسار التنزيل يُستنتج من (ideal → final) عبر سلّم الطبقات —
        أصدق من علم downgraded الذي لا يُرفع إلا عند السقوط حتى direct
        (quirk مثبَّت في corpus T-034 — السجل يوثّقه بدل أن يغيّره).
        """
        ladder = [RouteLabel.DELEGATE.value, RouteLabel.FULL_CHAIN.value,
                  RouteLabel.AUTO_CHAIN.value, RouteLabel.DIRECT.value]
        downgrade_path: list[str] = []
        if (ideal != decision.strategy
                and ideal in ladder and decision.strategy in ladder):
            i, j = ladder.index(ideal), ladder.index(decision.strategy)
            if j > i:  # نزل فعليًّا (لا مسار للفرض غير المعروف — يمر حرفيًّا)
                downgrade_path = ladder[i:j + 1]

        scores = analysis.to_dict()
        scores.pop("recommended_strategy", None)  # ليس درجة

        decision.record = RoutingRecord(
            mode=mode,
            forced=forced,
            scores=scores,
            matched_signals=dict(analysis.matched_signals),
            ideal=ideal,
            final=decision.strategy,
            tier=decision.tier.value,
            downgrade_path=downgrade_path,
            budget_total=budget.total_available,
            thresholds=self._thresholds.to_dict(),
            config_version=self._thresholds.version,
        )
        return decision

    def _ideal_strategy(self, score: float,
                        analysis: "ComplexityAnalysis") -> RouteLabel:
        """الاستراتيجية المثالية بدون قيود حسابات — عتبات config (T-036)"""
        th = self._thresholds
        if score <= th.direct_max:
            return RouteLabel.DIRECT
        elif score <= th.auto_chain_max:
            return RouteLabel.AUTO_CHAIN
        elif score <= th.full_chain_max:
            return RouteLabel.FULL_CHAIN
        else:
            return RouteLabel.DELEGATE

    def _apply_budget_constraints(self,
                                  ideal: RouteLabel,
                                  score: float,
                                  analysis: "ComplexityAnalysis",
                                  budget: "BudgetSnapshot") -> RoutingDecision:
        """يطبق قيود الحسابات — يعمل downgrade لو لازم.

        T-035 (R-401): السلسلة على أعضاء RouteLabel بدل النصوص الحرة؛
        فرع else الأخير أصبح assert_never — عضو جديد بلا معالجة =
        خطأ types عند mypy، لا fallback صامت.
        """

        # ── Direct → لا يحتاج أكثر من حساب واحد ──
        if ideal is RouteLabel.DIRECT:
            return RoutingDecision(
                strategy=RouteLabel.DIRECT.value,
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                complexity_score=score,
            )

        # ── Delegate → يحتاج ≥ 4 حسابات (وإلا يسقط لسلسلة full_chain) ──
        if ideal is RouteLabel.DELEGATE:
            need = self._thresholds.min_accounts_delegate
            if budget.can_afford(need):
                return RoutingDecision(
                    strategy=RouteLabel.DELEGATE.value,
                    provider_name=budget.best_provider_for(need),
                    chain_strategy=ExecutionStrategy.PIPELINE.value,
                    max_steps=need,
                    complexity_score=score,
                )
            # Downgrade → يواصل لفحص full_chain أدناه

        # ── Full Chain → يحتاج ≥ 3 حسابات (delegate المنزَّل يمر من هنا) ──
        if ideal is RouteLabel.DELEGATE or ideal is RouteLabel.FULL_CHAIN:
            if budget.can_afford(self._thresholds.min_accounts_full_chain):
                chain_strat = analysis.recommended
                if chain_strat is ExecutionStrategy.DIRECT:
                    chain_strat = ExecutionStrategy.CONTEXT_WINDOW  # upgrade minimum
                return RoutingDecision(
                    strategy=RouteLabel.FULL_CHAIN.value,
                    provider_name=budget.best_provider_for(
                        self._thresholds.min_accounts_full_chain),
                    chain_strategy=chain_strat.value,
                    max_steps=min(4, budget.total_available),
                    complexity_score=score,
                )
            # Downgrade → يواصل لفحص auto_chain أدناه

        # ── Auto Chain → يحتاج ≥ 2 حسابات (نهاية السلسلة قبل direct) ──
        if (ideal is RouteLabel.DELEGATE
                or ideal is RouteLabel.FULL_CHAIN
                or ideal is RouteLabel.AUTO_CHAIN):
            if budget.can_afford(self._thresholds.min_accounts_auto_chain):
                return RoutingDecision(
                    strategy=RouteLabel.AUTO_CHAIN.value,
                    provider_name=budget.best_provider_for(
                        self._thresholds.min_accounts_auto_chain),
                    chain_strategy=ExecutionStrategy.CONTEXT_WINDOW.value,
                    max_steps=min(3, budget.total_available),
                    complexity_score=score,
                )
            # Downgrade → direct
            return RoutingDecision(
                strategy=RouteLabel.DIRECT.value,
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                downgraded=True,
                downgrade_reason=(
                    f"الحسابات المتاحة ({budget.total_available}) أقل من "
                    f"المطلوب ({self._thresholds.min_accounts_auto_chain}) "
                    f"— تم تنزيل الاستراتيجية لـ direct"
                ),
                complexity_score=score,
            )

        # T-035: استنفاد إلزامي — كل أعضاء RouteLabel عولجوا أعلاه
        # (mypy يضيّق ideal إلى Never هنا؛ عضو جديد بلا فرع = خطأ types)
        assert_never(ideal)

    def _forced_route(self, force: str, score: float,
                      analysis: "ComplexityAnalysis",
                      budget: "BudgetSnapshot") -> RoutingDecision:
        """فرض استراتيجية معينة.

        T-035: المقارنات عبر RouteLabel.parse — لكن النص المجهول لا
        يزال يمر حرفيًّا في strategy (quirk مثبَّت في corpus T-034
        — router_forced_unknown_string_passes_through؛ إصلاحه قرار
        سلوكي لاحق خارج نطاق توحيد المفردات هذا).
        """
        label = RouteLabel.parse(force)
        if label is RouteLabel.DIRECT:
            return RoutingDecision(
                strategy=RouteLabel.DIRECT.value,
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                complexity_score=score,
            )

        th = self._thresholds
        steps_needed = {
            RouteLabel.AUTO_CHAIN: th.min_accounts_auto_chain,
            RouteLabel.FULL_CHAIN: th.min_accounts_full_chain,
            RouteLabel.DELEGATE: th.min_accounts_delegate,
        }.get(label, 1) if label is not None else 1

        can_afford = budget.can_afford(steps_needed)
        if can_afford:
            return RoutingDecision(
                strategy=force,
                provider_name=budget.best_provider_for(steps_needed),
                chain_strategy=analysis.recommended_strategy,
                max_steps=steps_needed,
                complexity_score=score,
            )
        else:
            # فرض مطلوب لكن مفيش حسابات كفاية
            return RoutingDecision(
                strategy=RouteLabel.DIRECT.value,
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                downgraded=True,
                downgrade_reason=(
                    f"طلبت {force} لكن الحسابات ({budget.total_available}) "
                    f"أقل من المطلوب ({steps_needed})"
                ),
                complexity_score=score,
            )

    def _select_provider(self, budget: "BudgetSnapshot", min_calls: int) -> str:
        """يختار أفضل provider بناءً على الحسابات المتاحة"""
        # لو عندنا active provider name → نستخدمه لو متاح
        if self._active_provider_name:
            remaining = budget.per_provider.get(self._active_provider_name, 0)
            if remaining >= min_calls:
                return self._active_provider_name

        # نختار الأكتر حسابات
        return budget.best_provider_for(min_calls) or self._active_provider_name
