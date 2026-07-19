# -*- coding: utf-8 -*-
"""T-035 (R-401): توحيد مفردات التوجيه — الاكتمال + المصفوفة + assert_never.

الطبقتان الصريحتان:
- ``RoutingTier`` (direct/chained/delegate) — قرار الراوتر.
- ``ExecutionStrategy`` (البانيات الستة) — قرار الأوركستريتور داخل الطبقة.
- ``RouteLabel`` — مفردات السلك التاريخية الأربع (ثابتة بايت-بايت
  لأجل corpus T-034 وعملاء الـ WS).

بوابة الـ parity الحقيقية هي ``test_routing_corpus.py`` (الثلاثون قرارًا
تُعاد حرفيًّا) — هذا الملف يغطي ما لا يغطيه الـ corpus: اكتمال السجل،
مصفوفة tier↔strategy، تطابق أسماء البانيات، والاستنفاد الصريح.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.orchestrator import ComplexityAnalysis, SmartOrchestrator  # noqa: E402
from chain.router import RoutingDecision  # noqa: E402
from core.strategy import (  # noqa: E402
    STRATEGY_TABLE,
    ExecutionStrategy,
    RouteLabel,
    RoutingTier,
    StrategySpec,
)


# ═══════════════ الاكتمال (completeness) ═══════════════

class TestTableCompleteness:
    def test_every_execution_strategy_has_a_table_row(self):
        """كل عضو enum له صف — إضافة عضو بلا صف تفشل عند الاستيراد أصلًا،
        وهذا الاختبار يوثّق العقد ويحرسه لو خُفِّف فحص الاستيراد يومًا."""
        assert set(STRATEGY_TABLE) == set(ExecutionStrategy)

    def test_every_row_is_consistent_spec(self):
        for member, spec in STRATEGY_TABLE.items():
            assert isinstance(spec, StrategySpec)
            assert spec.strategy is member, f"صف {member} يشير لعضو آخر"
            assert callable(spec.builder)
            assert spec.summary.strip(), f"صف {member} بلا توثيق"

    def test_builders_are_the_six_distinct_builders(self):
        builders = {spec.builder for spec in STRATEGY_TABLE.values()}
        assert len(builders) == 6, "بانيان يتشاركان صفًا — misroute كامن"

    def test_builder_names_match_strategy_values(self):
        """تثبيت التطابق نص-الباني ↔ قيمة-الـ enum بدل استيراد دائري:
        build_direct ينتج strategy_name=="direct" وهكذا."""
        for member, spec in STRATEGY_TABLE.items():
            assert spec.builder.__name__ == f"build_{member.value}"

    def test_enum_values_are_unique_and_frozen(self):
        assert len({m.value for m in ExecutionStrategy}) == 6
        assert len({m.value for m in RouteLabel}) == 4
        assert len({m.value for m in RoutingTier}) == 3


# ═══════════════ مصفوفة tier ↔ strategy ═══════════════

class TestTierMapping:
    def test_table_tier_assignment_matrix(self):
        expected = {
            ExecutionStrategy.DIRECT: RoutingTier.DIRECT,
            ExecutionStrategy.CONTEXT_WINDOW: RoutingTier.CHAINED,
            ExecutionStrategy.CHUNK_CHAIN: RoutingTier.CHAINED,
            ExecutionStrategy.MAP_REDUCE: RoutingTier.CHAINED,
            ExecutionStrategy.PIPELINE: RoutingTier.CHAINED,
            ExecutionStrategy.DELEGATE: RoutingTier.DELEGATE,
        }
        actual = {m: spec.tier for m, spec in STRATEGY_TABLE.items()}
        assert actual == expected

    @pytest.mark.parametrize("label,tier", [
        (RouteLabel.DIRECT, RoutingTier.DIRECT),
        (RouteLabel.AUTO_CHAIN, RoutingTier.CHAINED),
        (RouteLabel.FULL_CHAIN, RoutingTier.CHAINED),
        (RouteLabel.DELEGATE, RoutingTier.DELEGATE),
    ])
    def test_route_label_tier_property(self, label, tier):
        assert label.tier is tier

    def test_decision_tier_follows_label(self):
        assert RoutingDecision(strategy="auto_chain").tier \
            is RoutingTier.CHAINED
        assert RoutingDecision(strategy="full_chain").tier \
            is RoutingTier.CHAINED
        assert RoutingDecision(strategy="delegate").tier \
            is RoutingTier.DELEGATE
        assert RoutingDecision(strategy="direct").tier is RoutingTier.DIRECT

    def test_decision_unknown_strategy_dispatches_direct(self):
        """الـ quirk المثبَّت في corpus T-034: نص مجهول يمر حرفيًّا في
        strategy — والمرسِل القديم كان يتجاهله (لا يطابق أي شرط) فيسلك
        المسار العادي. tier يحافظ على نفس السلوك صراحةً."""
        assert RoutingDecision(strategy="banana").tier is RoutingTier.DIRECT


# ═══════════════ parse — نقطة العبور نص→enum ═══════════════

class TestParse:
    def test_execution_strategy_parse_roundtrip(self):
        for m in ExecutionStrategy:
            assert ExecutionStrategy.parse(m.value) is m

    def test_route_label_parse_roundtrip(self):
        for m in RouteLabel:
            assert RouteLabel.parse(m.value) is m

    @pytest.mark.parametrize("junk", ["banana", "", None, "DIRECT", 3])
    def test_parse_unknown_returns_none(self, junk):
        assert ExecutionStrategy.parse(junk) is None
        assert RouteLabel.parse(junk) is None


# ═══════════════ استنفاد صريح — لا fallback صامت ═══════════════

class TestExhaustiveness:
    def test_orchestrator_unknown_force_falls_to_direct_explicitly(self):
        """السلوك القديم لفرع else محفوظ (corpus) لكنه الآن قرار صريح
        عبر parse→None لا سقوطًا صامتًا من سلّم شروط نصية."""
        result = SmartOrchestrator().select_strategy(
            "أضف تعليقًا", force_strategy="no_such_strategy")
        assert result.strategy_name == "direct"

    def test_orchestrator_forced_delegate_still_falls_to_direct(self):
        """quirk موثَّق (corpus T-034): delegate غير موصول في
        select_strategy — مساره DelegateBridge."""
        result = SmartOrchestrator().select_strategy(
            "نفّذ عبر delegate", force_strategy="delegate")
        assert result.strategy_name == "direct"

    def test_recommended_is_enum_and_wire_property_matches(self):
        analysis = ComplexityAnalysis(size_score=6.0, risk_score=3.0)
        assert analysis.recommended is ExecutionStrategy.PIPELINE
        assert analysis.recommended_strategy == "pipeline"
        assert analysis.to_dict()["recommended_strategy"] == "pipeline"

    def test_grep_gate_no_free_string_comparisons(self):
        """بند القبول grep — صفر مقارنات نصية حرة في كود الإنتاج
        (نفس فحص check.sh، هنا ليعمل تحت pytest وحده أيضًا)."""
        patterns = [f'== "{m.value}"' for m in ExecutionStrategy]
        patterns += ['== "auto_chain"', '== "full_chain"',
                     'in ("auto_chain"']
        cmd = ["grep", "-rn", "--include=*.py"]
        for p in patterns:
            cmd += ["-e", p]
        cmd += ["chain/", "core/", "providers/", "context/",
                "sessions/", "server.py"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT,
                              capture_output=True, text=True)
        assert proc.returncode == 1, (
            f"مقارنات نصية حرة ما زالت موجودة:\n{proc.stdout}")
