# -*- coding: utf-8 -*-
"""T-036 (R-402): سجل قرار التوجيه + عتبات config — الاختبارات.

- **اكتمال السجل:** كل مسار توجيه (chat / طبيعي / downgrade / forced)
  يعلّق ``RoutingRecord`` كاملًا على القرار.
- **schema:** ``thresholds_from_config`` يرفض بصوت عالٍ المفاتيح
  المجهولة والأنواع الخاطئة والترتيب المكسور؛ قسم مفقود = الافتراضات
  التاريخية حرفيًّا.
- **الرتابة (monotonicity):** score أعلى لا يوجَّه أبدًا لطبقة أخف —
  في غياب downgrade الميزانية.
- **حدود السلك:** to_dict لا يتغيّر — corpus T-034 يبقى بايت-بايت.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.orchestrator import SmartOrchestrator  # noqa: E402
from chain.router import RequestRouter  # noqa: E402
from chain.routing_config import (  # noqa: E402
    RoutingRecord,
    RoutingThresholds,
    thresholds_from_config,
)
from providers.budget import BudgetSnapshot  # noqa: E402


class _FixedBudget:
    def __init__(self, per_provider: dict[str, int]):
        total = sum(per_provider.values())
        best = max(per_provider, key=lambda k: per_provider[k]) \
            if per_provider else ""
        self._snap = BudgetSnapshot(
            total_available=total, per_provider=dict(per_provider),
            best_provider=best, cheapest_provider=best)

    def check(self) -> BudgetSnapshot:
        return self._snap


def _router(budget: dict[str, int] | None = None,
            thresholds: RoutingThresholds | None = None) -> RequestRouter:
    return RequestRouter(
        orchestrator=SmartOrchestrator(),
        budget=_FixedBudget(budget or {"use_ai": 10}),
        active_provider_name="use_ai",
        thresholds=thresholds,
    )


_COMPLEX = ("refactor the whole architecture and rewrite then "
            "migrate every module across files")
_LONG = "أضف توثيقًا شاملًا لكل الدوال " * 10


def _lines(n: int) -> str:
    return "\n".join(f"line {i}: pass" for i in range(n))


# ═══════════════ اكتمال السجل (record completeness) ═══════════════

class TestRecordCompleteness:
    REQUIRED_KEYS = {"mode", "forced", "scores", "matched_signals",
                     "ideal", "final", "tier", "downgrade_path",
                     "budget_total", "thresholds", "config_version"}

    def _assert_complete(self, decision, *, mode):
        assert isinstance(decision.record, RoutingRecord)
        d = decision.record.to_dict()
        assert set(d) == self.REQUIRED_KEYS
        assert d["mode"] == mode
        assert d["final"] == decision.strategy
        assert d["tier"] == decision.tier.value
        # الدرجات الخمسة + total حاضرة
        assert {"size_score", "file_count_score", "cross_file_score",
                "request_complexity", "risk_score", "total"} <= set(d["scores"])
        assert d["thresholds"] == RoutingThresholds().to_dict()

    def test_chat_mode_path_carries_record(self):
        decision = _router().route("اشرح لي شيئًا", mode="chat")
        self._assert_complete(decision, mode="chat")
        assert decision.record.ideal == "direct"
        assert decision.record.downgrade_path == []

    def test_natural_path_carries_record_with_signals(self):
        decision = _router().route(_COMPLEX, file_content=_lines(4500),
                                   mode="build")
        self._assert_complete(decision, mode="build")
        assert decision.record.forced is None
        # الطلب المعقد يشعل أنماط request_complexity + risk
        assert "request_complexity" in decision.record.matched_signals
        assert "risk" in decision.record.matched_signals

    def test_forced_path_carries_record(self):
        decision = _router().route("أضف تعليقًا", mode="build",
                                   force_strategy="full_chain")
        self._assert_complete(decision, mode="build")
        assert decision.record.forced == "full_chain"

    def test_downgrade_path_recorded_step_by_step(self):
        """delegate→full_chain (ميزانية 3): يوثّق التنزيل الصامت الذي
        لا يرفعه علم downgraded (quirk مثبَّت في corpus)."""
        decision = _router({"use_ai": 3}).route(
            _COMPLEX, file_content=_lines(4500), mode="build")
        assert decision.strategy == "full_chain"
        assert decision.downgraded is False  # الـ quirk كما هو
        assert decision.record.downgrade_path == ["delegate", "full_chain"]

    def test_downgrade_to_direct_full_ladder(self):
        decision = _router({"use_ai": 1}).route(
            _LONG, file_content=_lines(500), mode="build")
        assert decision.strategy == "direct"
        assert decision.downgraded is True
        assert decision.record.downgrade_path == ["auto_chain", "direct"]

    def test_no_downgrade_means_empty_path(self):
        decision = _router().route(_LONG, file_content=_lines(500),
                                   mode="build")
        assert decision.strategy == "auto_chain"
        assert decision.record.downgrade_path == []

    def test_wire_dict_unchanged_record_outside(self):
        """حدود السلك: to_dict بلا مفتاح record — corpus T-034 محفوظ."""
        decision = _router().route("أضف تعليقًا", mode="build")
        assert "record" not in decision.to_dict()


# ═══════════════ schema — الرفض الصاخب ═══════════════

class TestSchemaValidation:
    def test_missing_section_gives_historical_defaults(self):
        th = thresholds_from_config(None)
        assert th == RoutingThresholds()
        assert (th.direct_max, th.auto_chain_max, th.full_chain_max) \
            == (2.0, 5.0, 8.0)
        assert (th.min_accounts_auto_chain, th.min_accounts_full_chain,
                th.min_accounts_delegate) == (2, 3, 4)

    def test_partial_section_fills_defaults(self):
        th = thresholds_from_config({"direct_max": 1.5})
        assert th.direct_max == 1.5
        assert th.auto_chain_max == 5.0

    def test_int_threshold_promoted_to_float(self):
        assert thresholds_from_config({"direct_max": 1}).direct_max == 1.0

    @pytest.mark.parametrize("bad,msg", [
        ({"banana": 1}, "مفاتيح مجهولة"),
        ({"direct_max": "high"}, "عددًا"),
        ({"direct_max": True}, "عددًا"),
        ({"min_accounts_delegate": 2.5}, "صحيحًا"),
        ({"min_accounts_delegate": True}, "صحيحًا"),
        ([1, 2], "خريطة"),
    ])
    def test_bad_section_raises_loudly(self, bad, msg):
        with pytest.raises(ValueError, match=msg):
            thresholds_from_config(bad)

    @pytest.mark.parametrize("bad", [
        {"direct_max": 6.0},                       # ≥ auto_chain_max
        {"auto_chain_max": 9.0},                   # ≥ full_chain_max
        {"min_accounts_auto_chain": 5},            # > full_chain
        {"min_accounts_delegate": 0},              # < 1
    ])
    def test_broken_ordering_rejected(self, bad):
        with pytest.raises(ValueError):
            thresholds_from_config(bad)

    def test_custom_thresholds_change_routing(self):
        """العتبات تعمل فعلًا: خفض direct_max يحوّل طلبًا كان direct."""
        tight = RoutingThresholds(direct_max=0.1, auto_chain_max=5.0,
                                  full_chain_max=8.0)
        decision = _router(thresholds=tight).route(
            "أضف تعليقًا هنا", file_content=_lines(50), mode="build")
        assert decision.strategy == "auto_chain"
        assert decision.record.thresholds["direct_max"] == 0.1


# ═══════════════ الرتابة (monotonicity property) ═══════════════

class TestMonotonicity:
    TIER_ORDER = {"direct": 0, "auto_chain": 1, "full_chain": 2,
                  "delegate": 3}

    def test_higher_complexity_never_routes_lighter(self):
        """R-402: بميزانية وفيرة (لا downgrade)، تصاعد التعقيد لا يهبط
        بالطبقة أبدًا — نبني سلّم مدخلات متصاعد التعقيد ونتحقق."""
        inputs = [
            ("أضف تعليقًا", None),                       # تافه
            ("حسّن الأداء هنا", _lines(300)),            # صغير
            (_LONG, _lines(500)),                        # متوسط
            ("refactor this module carefully", _lines(2000)),
            (_COMPLEX, _lines(2000)),
            (_COMPLEX, _lines(4500)),                    # أقصى
        ]
        router = _router({"use_ai": 10, "genspark": 6})
        last_rank = -1
        last_score = -1.0
        for request, content in inputs:
            decision = router.route(request, file_content=content,
                                    mode="build")
            score = decision.complexity_score
            rank = self.TIER_ORDER[decision.strategy]
            assert score >= last_score, "سلّم المدخلات نفسه غير متصاعد"
            if score > last_score:
                assert rank >= last_rank, (
                    f"انتهاك الرتابة: score {score} > {last_score} "
                    f"لكن {decision.strategy} أخف")
            last_rank, last_score = rank, score

    def test_budget_downgrade_is_the_only_exception(self):
        """التوثيق بالمثال: نفس الطلب، ميزانية أقل → طبقة أخف لكن
        السجل يحمل downgrade_path — الاستثناء معلَّل دائمًا."""
        rich = _router({"use_ai": 10}).route(
            _COMPLEX, file_content=_lines(4500), mode="build")
        poor = _router({"use_ai": 2}).route(
            _COMPLEX, file_content=_lines(4500), mode="build")
        assert self.TIER_ORDER[poor.strategy] \
            < self.TIER_ORDER[rich.strategy]
        assert poor.record.downgrade_path, "التنزيل بلا مسار مسجَّل"
