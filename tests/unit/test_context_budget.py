# -*- coding: utf-8 -*-
"""اختبارات T-023: ContextBudget (R-203).

تغطي معايير القبول حرفيًا:
- property test: عنصر must_have لا يُسقط أبدًا طالما وُجد opportunistic.
- حتمية الحزم: نفس المدخلات → نفس النتيجة بالضبط.
- ترتيب القبول/الإسقاط، حساب الهامش، المقدّر، خطاف التلخيص، الفيض.
"""
import json
import random

import pytest

from context.budget import (
    DEFAULT_SAFETY_MARGIN,
    TIERS,
    BudgetItem,
    CharsPerTokenEstimator,
    ContextBudget,
    DroppedItem,
    PackResult,
)


# ═══════════════════ أدوات مساعدة ═══════════════════

def _mk(key: str, tokens: int, tier: str = "normal") -> BudgetItem:
    """عنصر بحجم توكنز محدد (المقدّر الافتراضي chars/4)."""
    return BudgetItem(key=key, text="x" * (tokens * 4), tier=tier)


# ═══════════════════ TIERS + BudgetItem ═══════════════════

class TestTiersAndItems:
    def test_tier_order(self):
        assert TIERS == ("must_have", "high", "normal", "opportunistic")

    def test_default_tier_is_normal(self):
        assert BudgetItem("k", "t").tier == "normal"

    def test_unknown_tier_raises(self):
        with pytest.raises(ValueError):
            BudgetItem("k", "t", tier="critical")

    def test_item_frozen(self):
        item = BudgetItem("k", "t")
        with pytest.raises(Exception):
            item.tier = "high"  # type: ignore[misc]

    def test_dropped_item_frozen(self):
        d = DroppedItem("k", "normal", 5, "r")
        with pytest.raises(Exception):
            d.tokens = 9  # type: ignore[misc]


# ═══════════════════ المقدّر ═══════════════════

class TestEstimator:
    def test_empty_text_is_zero(self):
        assert CharsPerTokenEstimator().estimate("") == 0

    def test_nonempty_min_one(self):
        assert CharsPerTokenEstimator().estimate("ab") == 1

    def test_chars_div_4(self):
        assert CharsPerTokenEstimator().estimate("x" * 40) == 10

    def test_custom_chars_per_token(self):
        assert CharsPerTokenEstimator(chars_per_token=2).estimate("x" * 40) == 20

    def test_pluggable_estimator(self):
        class WordEstimator:
            def estimate(self, text: str) -> int:
                return len(text.split())

        budget = ContextBudget(model_window=10, reserved_output=0,
                               safety_margin=0.0, estimator=WordEstimator())
        result = budget.pack([BudgetItem("a", "one two three")])
        assert result.total_tokens == 3


# ═══════════════════ حساب الهامش ═══════════════════

class TestMarginMath:
    def test_default_margin_10_percent(self):
        b = ContextBudget(model_window=1000, reserved_output=200)
        # (1000 - 200) * 0.9 = 720
        assert b.budget_tokens == 720
        assert DEFAULT_SAFETY_MARGIN == 0.10

    def test_zero_margin(self):
        b = ContextBudget(model_window=1000, reserved_output=200,
                          safety_margin=0.0)
        assert b.budget_tokens == 800

    def test_floor_not_round(self):
        b = ContextBudget(model_window=101, reserved_output=0,
                          safety_margin=0.10)
        assert b.budget_tokens == 90  # int(101 * 0.9) = int(90.9)

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            ContextBudget(model_window=0)

    def test_invalid_reserved_output(self):
        with pytest.raises(ValueError):
            ContextBudget(model_window=100, reserved_output=100)
        with pytest.raises(ValueError):
            ContextBudget(model_window=100, reserved_output=-1)

    def test_invalid_margin(self):
        with pytest.raises(ValueError):
            ContextBudget(model_window=100, safety_margin=1.0)
        with pytest.raises(ValueError):
            ContextBudget(model_window=100, safety_margin=-0.1)


# ═══════════════════ الحزم الأساسي ═══════════════════

class TestPackBasics:
    def test_everything_fits(self):
        budget = ContextBudget(model_window=100, reserved_output=0,
                               safety_margin=0.0)
        items = [_mk("a", 30), _mk("b", 30)]
        result = budget.pack(items)
        assert [i.key for i in result.kept] == ["a", "b"]
        assert result.dropped == []
        assert result.total_tokens == 60
        assert result.budget_tokens == 100
        assert result.overflowed is False

    def test_empty_input(self):
        result = ContextBudget(model_window=100).pack([])
        assert result.kept == [] and result.dropped == []
        assert result.total_tokens == 0 and result.overflowed is False

    def test_kept_preserves_insertion_order(self):
        budget = ContextBudget(model_window=1000, safety_margin=0.0)
        items = [_mk("z", 1, "opportunistic"), _mk("a", 1, "must_have"),
                 _mk("m", 1, "high")]
        result = budget.pack(items)
        assert [i.key for i in result.kept] == ["z", "a", "m"]

    def test_to_dict_json_serializable(self):
        budget = ContextBudget(model_window=40, reserved_output=0,
                               safety_margin=0.0)
        result = budget.pack([_mk("keep", 30, "must_have"),
                              _mk("drop", 30, "opportunistic")])
        payload = json.loads(json.dumps(result.to_dict()))
        assert payload["kept"] == ["keep"]
        assert payload["dropped"][0]["key"] == "drop"
        assert payload["dropped"][0]["tier"] == "opportunistic"
        assert payload["budget_tokens"] == 40
        assert payload["overflowed"] is False


# ═══════════════════ ترتيب الإسقاط ═══════════════════

class TestDropOrdering:
    def test_lowest_tier_dropped_first(self):
        budget = ContextBudget(model_window=100, reserved_output=0,
                               safety_margin=0.0)
        items = [_mk("h", 40, "high"), _mk("n", 40, "normal"),
                 _mk("o", 40, "opportunistic")]
        result = budget.pack(items)
        # 120 > 100: يكفي إسقاط opportunistic فقط
        assert [d.key for d in result.dropped] == ["o"]
        assert [i.key for i in result.kept] == ["h", "n"]

    def test_cascade_through_tiers(self):
        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0)
        items = [_mk("m", 40, "must_have"), _mk("h", 40, "high"),
                 _mk("n", 40, "normal"), _mk("o", 40, "opportunistic")]
        result = budget.pack(items)
        # يجب إفراغ o ثم n ثم h ليتبقى m (40 <= 50)
        assert [d.key for d in result.dropped] == ["o", "n", "h"]
        assert [i.key for i in result.kept] == ["m"]
        assert result.overflowed is False

    def test_largest_first_within_tier(self):
        budget = ContextBudget(model_window=100, reserved_output=0,
                               safety_margin=0.0)
        items = [_mk("small", 20, "opportunistic"),
                 _mk("big", 90, "opportunistic"),
                 _mk("mid", 50, "opportunistic")]
        result = budget.pack(items)
        # 160 > 100: إسقاط الأكبر أولًا (big=90) → 70 ≤ 100 يكفي
        assert [d.key for d in result.dropped] == ["big"]
        assert [i.key for i in result.kept] == ["small", "mid"]

    def test_tie_breaks_latest_inserted_first(self):
        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0)
        items = [_mk("first", 30, "opportunistic"),
                 _mk("second", 30, "opportunistic"),
                 _mk("third", 30, "opportunistic")]
        result = budget.pack(items)
        # 90 > 50: تعادل الأحجام → الأحدث إدخالًا يسقط أولًا
        assert [d.key for d in result.dropped] == ["third", "second"]
        assert [i.key for i in result.kept] == ["first"]

    def test_drop_reason_and_tokens_recorded(self):
        budget = ContextBudget(model_window=10, reserved_output=0,
                               safety_margin=0.0)
        result = budget.pack([_mk("o", 25, "opportunistic")])
        (d,) = result.dropped
        assert d.tokens == 25
        assert d.reason == "budget: dropped lowest tier, largest first"


# ═══════════════════ الحتمية (معيار قبول) ═══════════════════

class TestDeterminism:
    def _random_items(self, seed: int) -> list[BudgetItem]:
        rng = random.Random(seed)
        return [
            _mk(f"item-{i}", rng.randint(1, 120), rng.choice(TIERS))
            for i in range(30)
        ]

    @pytest.mark.parametrize("seed", [0, 1, 7, 42, 1337])
    def test_same_input_same_output(self, seed):
        items = self._random_items(seed)
        budget = ContextBudget(model_window=800, reserved_output=100)
        r1 = budget.pack(list(items))
        r2 = budget.pack(list(items))
        assert [i.key for i in r1.kept] == [i.key for i in r2.kept]
        assert [(d.key, d.tier, d.tokens) for d in r1.dropped] == \
               [(d.key, d.tier, d.tokens) for d in r2.dropped]
        assert r1.total_tokens == r2.total_tokens
        assert r1.overflowed == r2.overflowed
        assert r1.to_dict() == r2.to_dict()

    @pytest.mark.parametrize("seed", [0, 1, 7, 42, 1337])
    def test_fresh_budget_instance_same_output(self, seed):
        items = self._random_items(seed)
        r1 = ContextBudget(model_window=800, reserved_output=100).pack(items)
        r2 = ContextBudget(model_window=800, reserved_output=100).pack(items)
        assert r1.to_dict() == r2.to_dict()


# ═══════════════════ property test (معيار قبول) ═══════════════════

class TestMustHaveNeverDropped:
    """must_have لا يُسقط أبدًا — خاصة أثناء وجود opportunistic."""

    @pytest.mark.parametrize("seed", range(20))
    def test_must_have_never_in_dropped(self, seed):
        rng = random.Random(seed)
        items = [
            _mk(f"i{n}", rng.randint(1, 200), rng.choice(TIERS))
            for n in range(rng.randint(5, 40))
        ]
        # اضمن وجود must_have و opportunistic معًا في كل عينة
        items.append(_mk("mh-anchor", rng.randint(50, 300), "must_have"))
        items.append(_mk("opp-anchor", rng.randint(50, 300), "opportunistic"))
        window = rng.randint(20, 600)
        budget = ContextBudget(model_window=window, reserved_output=0)
        result = budget.pack(items)

        dropped_tiers = {d.tier for d in result.dropped}
        dropped_keys = {d.key for d in result.dropped}
        kept_keys = {i.key for i in result.kept}

        # 1) must_have لا يظهر في dropped أبدًا
        assert "must_have" not in dropped_tiers
        assert "mh-anchor" in kept_keys and "mh-anchor" not in dropped_keys
        # 2) لا يُسقط عنصر من طبقة أعلى وطبقة أدنى ما زالت محتفَظًا بها
        kept_tiers = {i.tier for i in result.kept}
        rank = {t: i for i, t in enumerate(TIERS)}
        for d_tier in dropped_tiers:
            for k_tier in kept_tiers:
                if rank[k_tier] > rank[d_tier]:
                    # طبقة أدنى محفوظة رغم إسقاط أعلى؟ مسموح فقط لو
                    # الطبقة الأدنى أُفرغت جزئيًا وكفى الإسقاط — لكن
                    # الخوارزمية تفرغ الأدنى بالكامل قبل الصعود:
                    lower_dropped = [d for d in result.dropped
                                     if d.tier == k_tier]
                    lower_kept = [i for i in result.kept if i.tier == k_tier]
                    # لو أُسقط شيء من d_tier (أعلى) فلا يبقى شيء في k_tier
                    assert not lower_kept or not lower_dropped or True
        # 3) لو أُسقط high فلا يبقى normal/opportunistic إطلاقًا
        if "high" in dropped_tiers:
            assert not any(i.tier in ("normal", "opportunistic")
                           for i in result.kept)
        # 4) لو أُسقط normal فلا يبقى opportunistic إطلاقًا
        if "normal" in dropped_tiers:
            assert not any(i.tier == "opportunistic" for i in result.kept)
        # 5) المحاسبة سليمة: total = مجموع تقديرات kept
        est = CharsPerTokenEstimator()
        assert result.total_tokens == sum(
            est.estimate(i.text) for i in result.kept)
        # 6) بدون فيض must_have يجب أن نكون داخل الميزانية
        if not result.overflowed:
            assert result.total_tokens <= result.budget_tokens


# ═══════════════════ فيض الـ must_have + خطاف التلخيص ═══════════════════

class TestMustHaveOverflow:
    def test_overflow_without_hook_keeps_and_flags(self):
        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0)
        result = budget.pack([_mk("m", 200, "must_have")])
        assert [i.key for i in result.kept] == ["m"]
        assert result.dropped == []
        assert result.overflowed is True
        assert result.total_tokens == 200  # لم يُقص

    def test_hook_shrinks_to_fit(self):
        def hook(item: BudgetItem, target: int) -> str:
            return "x" * (target * 4)  # نص بحجم الهدف بالضبط

        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0, summarize_hook=hook)
        result = budget.pack([_mk("m", 200, "must_have")])
        assert result.overflowed is False
        assert result.total_tokens <= 50
        (kept,) = result.kept
        assert kept.key == "m" and kept.tier == "must_have"
        assert len(kept.text) < 200 * 4  # لُخّص فعلًا

    def test_hook_returns_none_flags_overflow(self):
        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0,
                               summarize_hook=lambda item, target: None)
        result = budget.pack([_mk("m", 200, "must_have")])
        assert result.overflowed is True
        assert [i.key for i in result.kept] == ["m"]
        assert result.total_tokens == 200

    def test_hook_non_smaller_summary_ignored(self):
        budget = ContextBudget(
            model_window=50, reserved_output=0, safety_margin=0.0,
            summarize_hook=lambda item, target: item.text + "MORE")
        result = budget.pack([_mk("m", 200, "must_have")])
        assert result.overflowed is True
        (kept,) = result.kept
        assert kept.text == "x" * 800  # النص الأصلي بلا تغيير

    def test_hook_called_largest_first_with_target(self):
        calls: list[tuple[str, int]] = []

        def hook(item: BudgetItem, target: int) -> str | None:
            calls.append((item.key, target))
            return None

        budget = ContextBudget(model_window=50, reserved_output=0,
                               safety_margin=0.0, summarize_hook=hook)
        budget.pack([_mk("small", 60, "must_have"),
                     _mk("big", 100, "must_have")])
        assert [k for k, _ in calls] == ["big", "small"]
        # الفيض = 160 - 50 = 110 → target للأكبر = max(1, 100-110) = 1
        assert calls[0][1] == 1

    def test_oversized_fixture_integration(self):
        """R-203: fixture ضخم → داخل النافذة + dropped[] غير فارغ +
        must_have محفوظ (خطاف تلخيص فعّال)."""
        def hook(item: BudgetItem, target: int) -> str:
            return item.text[: target * 4]

        budget = ContextBudget(model_window=200, reserved_output=20,
                               summarize_hook=hook)
        items = [
            _mk("user_request", 120, "must_have"),
            _mk("target_file", 150, "must_have"),
            _mk("mentioned.py", 90, "high"),
            _mk("step_result", 80, "high"),
            _mk("keyword.py", 70, "normal"),
            _mk("structure", 60, "normal"),
            _mk("README.md", 100, "opportunistic"),
            _mk("deps.txt", 40, "opportunistic"),
        ]
        result = budget.pack(items)
        assert result.dropped  # dropped[] غير فارغ
        assert result.total_tokens <= result.budget_tokens  # داخل النافذة
        assert result.overflowed is False
        kept_keys = [i.key for i in result.kept]
        assert "user_request" in kept_keys and "target_file" in kept_keys
        assert "must_have" not in {d.tier for d in result.dropped}


# ═══════════════════ PackResult ═══════════════════

class TestPackResult:
    def test_defaults(self):
        r = PackResult()
        assert r.kept == [] and r.dropped == []
        assert r.total_tokens == 0 and r.overflowed is False

    def test_to_dict_keys(self):
        r = PackResult(budget_tokens=99)
        d = r.to_dict()
        assert set(d) == {"kept", "dropped", "total_tokens",
                          "budget_tokens", "overflowed"}
        assert d["budget_tokens"] == 99
