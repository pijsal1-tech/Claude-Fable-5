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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chain.orchestrator import SmartOrchestrator, ComplexityAnalysis
    from providers.budget import AccountAwareBudget, BudgetSnapshot
    from providers.base import BaseProvider


# ═══════════════════════════════════════════════════════
#   RoutingDecision — نتيجة التوجيه
# ═══════════════════════════════════════════════════════

@dataclass
class RoutingDecision:
    """نتيجة قرار التوجيه"""
    strategy: str                      # direct | auto_chain | full_chain | delegate
    provider_name: str = ""            # اسم الـ provider المختار
    chain_strategy: str | None = None  # context_window | chunk_chain | map_reduce | pipeline
    max_steps: int = 1                 # أقصى عدد خطوات مسموح
    downgraded: bool = False           # هل تم تنزيل التعقيد بسبب نقص حسابات؟
    downgrade_reason: str = ""         # سبب التنزيل
    complexity_score: float = 0.0      # النتيجة الأصلية للتعقيد

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


# ═══════════════════════════════════════════════════════
#   Strategy Thresholds
# ═══════════════════════════════════════════════════════

# حدود التعقيد لاختيار الاستراتيجية
DIRECT_THRESHOLD = 2.0        # ≤ 2.0 → direct
AUTO_CHAIN_THRESHOLD = 5.0    # 2.1 - 5.0 → auto_chain (2-3 steps)
FULL_CHAIN_THRESHOLD = 8.0    # 5.1 - 8.0 → full_chain (3-4 steps)
# > 8.0 → delegate (brief + implement + review)

# الحد الأدنى من الحسابات لكل استراتيجية
MIN_ACCOUNTS_AUTO_CHAIN = 2
MIN_ACCOUNTS_FULL_CHAIN = 3
MIN_ACCOUNTS_DELEGATE = 4


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
        if decision.strategy == "direct":
            # المسار العادي
        elif decision.strategy in ("auto_chain", "full_chain"):
            # chain_bridge.start_chain(...)
        elif decision.strategy == "delegate":
            # delegate_bridge.run_delegation(...)
    """

    def __init__(self,
                 orchestrator: "SmartOrchestrator",
                 budget: "AccountAwareBudget",
                 active_provider_name: str = ""):
        self._orchestrator = orchestrator
        self._budget = budget
        self._active_provider_name = active_provider_name

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
            return self._forced_route(
                force_strategy, score, analysis, budget_snapshot
            )

        # ── Mode Override: chat mode = always direct ──
        if mode == "chat":
            return RoutingDecision(
                strategy="direct",
                provider_name=self._select_provider(budget_snapshot, 1),
                max_steps=1,
                complexity_score=score,
            )

        # ── 4. التوجيه بناءً على التعقيد + الحسابات ──
        ideal = self._ideal_strategy(score, analysis)
        decision = self._apply_budget_constraints(ideal, score, analysis, budget_snapshot)

        return decision

    def _ideal_strategy(self, score: float,
                        analysis: "ComplexityAnalysis") -> str:
        """الاستراتيجية المثالية بدون قيود حسابات"""
        if score <= DIRECT_THRESHOLD:
            return "direct"
        elif score <= AUTO_CHAIN_THRESHOLD:
            return "auto_chain"
        elif score <= FULL_CHAIN_THRESHOLD:
            return "full_chain"
        else:
            return "delegate"

    def _apply_budget_constraints(self,
                                  ideal: str,
                                  score: float,
                                  analysis: "ComplexityAnalysis",
                                  budget: "BudgetSnapshot") -> RoutingDecision:
        """يطبق قيود الحسابات — يعمل downgrade لو لازم"""

        # ── Direct → لا يحتاج أكثر من حساب واحد ──
        if ideal == "direct":
            return RoutingDecision(
                strategy="direct",
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                complexity_score=score,
            )

        # ── Delegate → يحتاج ≥ 4 حسابات ──
        if ideal == "delegate":
            if budget.can_afford(MIN_ACCOUNTS_DELEGATE):
                return RoutingDecision(
                    strategy="delegate",
                    provider_name=budget.best_provider_for(MIN_ACCOUNTS_DELEGATE),
                    chain_strategy="pipeline",
                    max_steps=MIN_ACCOUNTS_DELEGATE,
                    complexity_score=score,
                )
            # Downgrade → full_chain
            ideal = "full_chain"

        # ── Full Chain → يحتاج ≥ 3 حسابات ──
        if ideal == "full_chain":
            if budget.can_afford(MIN_ACCOUNTS_FULL_CHAIN):
                chain_strat = analysis.recommended_strategy
                if chain_strat == "direct":
                    chain_strat = "context_window"  # upgrade minimum
                return RoutingDecision(
                    strategy="full_chain",
                    provider_name=budget.best_provider_for(MIN_ACCOUNTS_FULL_CHAIN),
                    chain_strategy=chain_strat,
                    max_steps=min(4, budget.total_available),
                    complexity_score=score,
                )
            # Downgrade → auto_chain
            ideal = "auto_chain"

        # ── Auto Chain → يحتاج ≥ 2 حسابات ──
        if ideal == "auto_chain":
            if budget.can_afford(MIN_ACCOUNTS_AUTO_CHAIN):
                return RoutingDecision(
                    strategy="auto_chain",
                    provider_name=budget.best_provider_for(MIN_ACCOUNTS_AUTO_CHAIN),
                    chain_strategy="context_window",
                    max_steps=min(3, budget.total_available),
                    complexity_score=score,
                )
            # Downgrade → direct
            return RoutingDecision(
                strategy="direct",
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                downgraded=True,
                downgrade_reason=(
                    f"الحسابات المتاحة ({budget.total_available}) أقل من "
                    f"المطلوب ({MIN_ACCOUNTS_AUTO_CHAIN}) — تم تنزيل الاستراتيجية لـ direct"
                ),
                complexity_score=score,
            )

        # Fallback
        return RoutingDecision(
            strategy="direct",
            provider_name=self._select_provider(budget, 1),
            max_steps=1,
            complexity_score=score,
        )

    def _forced_route(self, force: str, score: float,
                      analysis: "ComplexityAnalysis",
                      budget: "BudgetSnapshot") -> RoutingDecision:
        """فرض استراتيجية معينة"""
        if force == "direct":
            return RoutingDecision(
                strategy="direct",
                provider_name=self._select_provider(budget, 1),
                max_steps=1,
                complexity_score=score,
            )

        steps_needed = {
            "auto_chain": 2,
            "full_chain": 3,
            "delegate": 4,
        }.get(force, 1)

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
                strategy="direct",
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
