# -*- coding: utf-8 -*-
"""T-107 (R-803): اختبارات LLMPlanner + HybridPlanner + المخطط + السقوط.

الحزم:
1. plan_schema: التحقق الصارم (استراتيجية/خطوات/DAG/سقف) + parse.
2. LLMPlanner: قبول الخطة الصالحة؛ كل صف من مصفوفة السقوط ⇒ خطة
   heuristic + سجل قرار بالسبب؛ فحص السعة قبل التنفيذ.
3. HybridPlanner: بوابة بسيطة بلا موديل، معقدة عبر LLM بحراسته.
4. عدة توافق T-106 (PlannerContractMixin) على المخطِّطين الجديدين.
"""
from __future__ import annotations

import json

import pytest

from chain.plan_schema import (
    ALLOWED_STAGES,
    ALLOWED_STRATEGIES,
    MAX_PLAN_STEPS,
    PlanSchemaError,
    parse_plan_json,
    validate_plan_payload,
)
from chain.planner import (
    HeuristicPlanner,
    HybridPlanner,
    LLMPlanner,
    Planner,
    PlanRequest,
    planner_from_config,
)
from tests.unit.test_planner import PlannerContractMixin

# ═════════════ أدوات ═════════════


def good_payload(steps: int = 2, strategy: str = "pipeline") -> dict:
    """حمولة خطة صالحة قياسية — خطوات متسلسلة التبعية."""
    return {
        "strategy": strategy,
        "steps": [
            {"id": f"s{i}", "name": f"خطوة {i}", "stage": "execute",
             "agent_role": "executor", "prompt": f"نفّذ {i}",
             "depends_on": [f"s{i - 1}"] if i else []}
            for i in range(steps)
        ],
    }


class ScriptedProvider:
    """مزود مكتوب السيناريو — رد ثابت أو استثناء، مع عدّاد نداءات."""

    def __init__(self, response: str = "", raises: Exception | None = None):
        self.response = response
        self.raises = raises
        self.calls = 0
        self.last_prompt = ""

    def send(self, prompt: str, history=None, system_prompt: str = "") -> str:
        self.calls += 1
        self.last_prompt = prompt
        if self.raises is not None:
            raise self.raises
        return self.response


class FakeCapacity:
    """قناع CapacityReport — total_available فقط (كل ما يفحصه المخطِّط)."""

    def __init__(self, total: int):
        self.total_available = total


# طلب «معقّد» مثبّت: يطابق أنماط التعقيد (إعادة.*هيكلة/معمارية/عبر.*ملفات)
# والمخاطر ⇒ توصية المحلل chunk_chain — يعبر بوابة Hybrid لمسار LLM.
REQ = PlanRequest(
    "إعادة هيكلة معمارية المصادقة عبر كل الملفات "
    "مع حذف قاعدة البيانات القديمة وتشفير كل token")


def record_of(plan) -> dict:
    rec = plan.metadata.get("planner_record")
    assert rec is not None, "سجل القرار غائب — كل خطة T-107 تحمله"
    return rec


# ═════════════ 1) plan_schema ═════════════


class TestParsePlanJson:

    def test_plain_json(self):
        assert parse_plan_json(json.dumps(good_payload()))["strategy"] \
            == "pipeline"

    def test_fenced_json(self):
        text = "```json\n" + json.dumps(good_payload()) + "\n```"
        assert parse_plan_json(text)["strategy"] == "pipeline"

    @pytest.mark.parametrize("bad", [
        "ليست JSON إطلاقًا", "{broken json", "[1, 2, 3]", '"نص"', ""])
    def test_garbage_rejected_as_invalid_json(self, bad):
        with pytest.raises(PlanSchemaError) as ei:
            parse_plan_json(bad)
        assert ei.value.reason.startswith("invalid_json:")


class TestValidatePlanPayload:

    def test_good_payload_roundtrip(self):
        plan = validate_plan_payload(good_payload(3))
        assert plan.strategy == "pipeline" and len(plan.steps) == 3
        sr = plan.to_strategy_result()
        assert sr.strategy_name == "pipeline"
        assert [s.id for s in sr.steps] == ["s0", "s1", "s2"]
        assert sr.steps[2].depends_on == ["s1"]

    @pytest.mark.parametrize("strategy", ["delegate", "magic", "", None, 5])
    def test_bad_strategy_rejected(self, strategy):
        payload = good_payload()
        payload["strategy"] = strategy
        with pytest.raises(PlanSchemaError) as ei:
            validate_plan_payload(payload)
        assert ei.value.reason.startswith("schema:")

    @pytest.mark.parametrize("steps", [[], None, "steps", {}])
    def test_bad_steps_container_rejected(self, steps):
        payload = good_payload()
        payload["steps"] = steps
        with pytest.raises(PlanSchemaError):
            validate_plan_payload(payload)

    def test_step_cap_loud(self):
        with pytest.raises(PlanSchemaError) as ei:
            validate_plan_payload(good_payload(MAX_PLAN_STEPS + 1))
        assert "السقف" in ei.value.reason
        # الحد نفسه يمر
        validate_plan_payload(good_payload(MAX_PLAN_STEPS))

    @pytest.mark.parametrize("key", ["id", "name", "stage", "agent_role",
                                     "prompt"])
    def test_missing_or_empty_field_rejected(self, key):
        payload = good_payload()
        payload["steps"][0][key] = "   "
        with pytest.raises(PlanSchemaError):
            validate_plan_payload(payload)

    def test_unknown_stage_rejected(self):
        payload = good_payload()
        payload["steps"][0]["stage"] = "deploy"
        with pytest.raises(PlanSchemaError):
            validate_plan_payload(payload)

    def test_duplicate_id_rejected(self):
        payload = good_payload(2)
        payload["steps"][1]["id"] = "s0"
        with pytest.raises(PlanSchemaError):
            validate_plan_payload(payload)

    @pytest.mark.parametrize("dep", ["s1", "s9", "s0"])
    def test_non_prior_dependency_rejected(self, dep):
        """ذاتي (s0 لنفسها عبر خطوة 0)/أمامي/مجهول — DAG بالبناء."""
        payload = good_payload(2)
        payload["steps"][0]["depends_on"] = [dep]
        with pytest.raises(PlanSchemaError):
            validate_plan_payload(payload)

    def test_vocab_constants_locked(self):
        assert ALLOWED_STRATEGIES == {"direct", "context_window",
                                      "chunk_chain", "map_reduce",
                                      "pipeline"}
        assert "delegate" not in ALLOWED_STRATEGIES
        assert ALLOWED_STAGES == {"analyze", "plan", "execute", "review"}


# ═════════════ 2) LLMPlanner — القبول والسقوط ═════════════


class TestLLMPlannerAccepts:

    def test_valid_plan_used_with_record(self):
        provider = ScriptedProvider(json.dumps(good_payload(3)))
        plan = LLMPlanner(provider).plan(REQ)
        assert plan.strategy_name == "pipeline" and len(plan.steps) == 3
        rec = record_of(plan)
        assert rec["planner"] == "llm" and rec["used"] == "llm"
        assert rec["fallback_reason"] is None
        assert provider.calls == 1
        assert REQ.user_request in provider.last_prompt

    def test_capacity_recorded_when_checked(self):
        provider = ScriptedProvider(json.dumps(good_payload(3)))
        plan = LLMPlanner(provider).plan(REQ, capacity=FakeCapacity(10))
        assert record_of(plan)["capacity_available"] == 10


class TestLLMPlannerFallbacks:
    """كل صف من مصفوفة السقوط (plan_schema رأس الموديول) بالاتجاهين:
    خطة heuristic فعلًا + سجل يسمّي السبب."""

    def _assert_heuristic_fallback(self, plan, reason_prefix: str):
        rec = record_of(plan)
        assert rec["used"] == "heuristic"
        assert rec["fallback_reason"].startswith(reason_prefix)
        # الخطة هي خطة heuristic حرفيًّا (نفس المدخل نفس الناتج)
        expected = HeuristicPlanner().plan(REQ)
        assert plan.strategy_name == expected.strategy_name
        assert plan.steps == expected.steps

    def test_provider_error_falls_back(self):
        provider = ScriptedProvider(raises=ConnectionError("down"))
        plan = LLMPlanner(provider).plan(REQ)
        self._assert_heuristic_fallback(plan, "provider_error:")

    def test_invalid_json_falls_back(self):
        plan = LLMPlanner(ScriptedProvider("هلوسة نصية حرة")).plan(REQ)
        self._assert_heuristic_fallback(plan, "invalid_json:")

    def test_schema_violation_falls_back(self):
        payload = good_payload()
        payload["strategy"] = "delegate"
        plan = LLMPlanner(ScriptedProvider(json.dumps(payload))).plan(REQ)
        self._assert_heuristic_fallback(plan, "schema:")

    def test_capacity_exceeded_rejected_pre_execution(self):
        """بند القبول: خطة فوق السعة تُرفض قبل التنفيذ."""
        provider = ScriptedProvider(json.dumps(good_payload(5)))
        plan = LLMPlanner(provider).plan(REQ, capacity=FakeCapacity(2))
        self._assert_heuristic_fallback(plan, "capacity: needs 5 > 2")

    def test_forced_strategy_skips_model_entirely(self):
        provider = ScriptedProvider(json.dumps(good_payload()))
        req = PlanRequest("أي طلب", force_strategy="pipeline")
        plan = LLMPlanner(provider).plan(req)
        assert provider.calls == 0, "الفرض قرار مستخدم — لا نداء موديل"
        rec = record_of(plan)
        assert rec["fallback_reason"] == "forced_heuristic"
        assert plan.strategy_name == "pipeline"

    def test_no_capacity_report_means_no_check(self):
        plan = LLMPlanner(
            ScriptedProvider(json.dumps(good_payload(5)))).plan(REQ)
        rec = record_of(plan)
        assert rec["used"] == "llm" and rec["capacity_available"] is None


# ═════════════ 3) HybridPlanner — البوابة ═════════════


class TestHybridPlanner:

    def test_simple_request_never_calls_model(self):
        provider = ScriptedProvider(json.dumps(good_payload()))
        plan = HybridPlanner(provider).plan(PlanRequest("أصلح الإملاء"))
        assert provider.calls == 0
        rec = record_of(plan)
        assert rec["planner"] == "hybrid" and rec["used"] == "heuristic"
        assert rec["fallback_reason"].startswith("simple_tier:")

    def test_complex_request_goes_through_llm(self):
        provider = ScriptedProvider(json.dumps(good_payload(3)))
        plan = HybridPlanner(provider).plan(REQ)
        assert provider.calls == 1
        rec = record_of(plan)
        assert rec["planner"] == "hybrid" and rec["used"] == "llm"

    def test_complex_with_bad_llm_falls_back_guarded(self):
        provider = ScriptedProvider("هلوسة")
        plan = HybridPlanner(provider).plan(REQ)
        rec = record_of(plan)
        assert rec["planner"] == "hybrid" and rec["used"] == "heuristic"
        assert rec["fallback_reason"].startswith("invalid_json:")

    def test_forced_goes_single_path(self):
        provider = ScriptedProvider(json.dumps(good_payload()))
        plan = HybridPlanner(provider).plan(
            PlanRequest("أي طلب", force_strategy="map_reduce"))
        assert provider.calls == 0
        rec = record_of(plan)
        assert rec["planner"] == "hybrid"
        assert rec["fallback_reason"] == "forced_heuristic"
        assert plan.strategy_name == "map_reduce"


# ═════════════ 4) عدة توافق T-106 على الجديدين ═════════════


class TestLLMPlannerContract(PlannerContractMixin):
    """LLMPlanner يجتاز عدة T-106 — بمزود فاسد عمدًا (كل خطة تمر
    بمسار السقوط ⇒ نفس ضمانات heuristic: حتمية/فرض/direct)."""

    def make_planner(self) -> Planner:
        return LLMPlanner(ScriptedProvider("ليست خطة"))


class TestHybridPlannerContract(PlannerContractMixin):

    def make_planner(self) -> Planner:
        return HybridPlanner(ScriptedProvider("ليست خطة"))


# ═════════════ درزة config للجديدين ═════════════


class TestConfigSeamT107:

    def test_llm_and_hybrid_buildable(self):
        provider = ScriptedProvider("")
        assert isinstance(planner_from_config("llm", provider=provider),
                          LLMPlanner)
        assert isinstance(planner_from_config("hybrid", provider=provider),
                          HybridPlanner)

    @pytest.mark.parametrize("name", ["llm", "hybrid"])
    def test_missing_provider_fails_loudly(self, name):
        with pytest.raises(ValueError):
            planner_from_config(name)

    def test_heuristic_ignores_provider(self):
        p = planner_from_config("heuristic", provider=ScriptedProvider(""))
        assert isinstance(p, HeuristicPlanner)
