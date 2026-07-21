# -*- coding: utf-8 -*-
"""T-107 (R-803): تبديل المخطِّط عبر config — صفر تعديل كود.

بند القبول المركزي: «planner swap via config with zero core edits —
asserted by touching only config in the test». الاختبارات هنا تحاكي
درزة الإقلاع (نفس أسطر server.py حرفيًّا: قراءة المفتاح ثم
``planner_from_config``) وتبدّل **قيمة config فقط** بين الحالات —
لا monkeypatch على وحدات الإنتاج، لا صنف مشتق، لا تعديل كود.

+ انحدار T-106: ضبط heuristic-only ⇒ خطط بايت-مطابقة لِما قبل T-107.
"""
from __future__ import annotations

import json

import pytest

from chain.bridge import ChainBridge
from chain.orchestrator import SmartOrchestrator
from chain.planner import (
    HeuristicPlanner,
    HybridPlanner,
    LLMPlanner,
    PlanRequest,
    planner_from_config,
)
from tests.fakes.fake_provider import FakeProvider
from tests.unit.test_llm_planner import ScriptedProvider, good_payload


def boot_planner(cfg: dict, provider):
    """درزة الإقلاع كما في server.py حرفيًّا — قراءة المفتاح ثم البناء.

    المدخل الوحيد المتغير بين الاختبارات = dict الـ config (يحاكي
    yaml.safe_load(config.yaml)) — هذا هو «تعديل config فقط».
    """
    planner_cfg = (cfg or {}).get("planner")
    return planner_from_config(planner_cfg, SmartOrchestrator(),
                               provider=provider)


# طلب «معقّد» مثبّت (نفس نص وحدة LLM): توصية المحلل chunk_chain
# ⇒ بوابة Hybrid تمرّره لمسار LLM فعليًّا.
REQ = PlanRequest(
    "إعادة هيكلة معمارية المصادقة عبر كل الملفات "
    "مع حذف قاعدة البيانات القديمة وتشفير كل token")


@pytest.mark.integration
class TestConfigSwapZeroEdit:
    """التبديل بين المخطِّطات الثلاثة بتغيير قيمة المفتاح فقط."""

    def test_three_way_swap_by_config_value_only(self):
        provider = ScriptedProvider(json.dumps(good_payload(3)))
        # نفس الاستدعاء ثلاث مرات — الفرق الوحيد قيمة config:
        built = {name: boot_planner({"planner": name}, provider)
                 for name in ("heuristic", "llm", "hybrid")}
        assert isinstance(built["heuristic"], HeuristicPlanner)
        assert isinstance(built["llm"], LLMPlanner)
        assert isinstance(built["hybrid"], HybridPlanner)
        # والخطط تعمل فعلًا عبر البروتوكول الواحد:
        for name, planner in built.items():
            plan = planner.plan(REQ)
            assert plan.steps, f"{name}: خطة بلا خطوات"

    def test_missing_key_equals_heuristic(self):
        provider = ScriptedProvider("")
        default = boot_planner({}, provider)
        explicit = boot_planner({"planner": "heuristic"}, provider)
        assert type(default) is type(explicit) is HeuristicPlanner
        assert default.plan(REQ) == explicit.plan(REQ)

    def test_unknown_name_fails_boot_loudly(self):
        with pytest.raises(ValueError):
            boot_planner({"planner": "quantum"}, ScriptedProvider(""))

    def test_swapped_planner_reaches_bridge_dispatch(self, tmp_path):
        """المخطِّط المبدَّل من config يصل مسار الـ bridge نفسه —
        الحقن كما في server.py (ChainBridge(planner=...))."""
        provider = ScriptedProvider(json.dumps(good_payload(2)))
        planner = boot_planner({"planner": "llm"}, provider)
        bridge = ChainBridge(FakeProvider(responses=["ok"]),
                             project_root=str(tmp_path), planner=planner)
        assert bridge._planner is planner


@pytest.mark.integration
class TestHeuristicOnlyRegression:
    """انحدار T-106: ضبط heuristic ⇒ التركيبة القديمة بايت-بايت."""

    CASES = [
        PlanRequest("أصلح الخطأ الإملائي"),
        PlanRequest("راجع الملف", file_content="x = 1\n" * 300,
                    file_path="app.py"),
        PlanRequest("حلل المشروع",
                    files={f"m{i}.py": "def f():\n    pass\n" * 200
                           for i in range(5)}),
        PlanRequest("أي طلب", force_strategy="pipeline"),
    ]

    @pytest.mark.parametrize("req", CASES,
                             ids=["small", "file", "files", "forced"])
    def test_plans_byte_identical_to_pre_t107(self, req):
        """المرجع = select_strategy المباشر (مسار ما قبل الاستخراج
        كله) — heuristic من config يطابقه بمساواة dataclass كاملة."""
        orch = SmartOrchestrator()
        legacy = orch.select_strategy(
            user_request=req.user_request, files=req.files,
            file_content=req.file_content, file_path=req.file_path,
            force_strategy=req.force_strategy)
        configured = boot_planner({"planner": "heuristic"},
                                  provider=None)
        assert configured.plan(req) == legacy

    def test_heuristic_plans_carry_no_planner_record(self):
        """heuristic النقي لا يلمس metadata الجديدة — عقود T-106
        (والـ goldens) محفوظة حرفيًّا."""
        plan = boot_planner({"planner": "heuristic"}, None).plan(REQ)
        assert "planner_record" not in plan.metadata


@pytest.mark.integration
class TestDecisionRecordsEndToEnd:
    """بند القبول: كل خطة llm/hybrid تحمل سجل قرار قابلًا للتتبع."""

    def test_llm_records_across_outcomes(self):
        ok = boot_planner({"planner": "llm"},
                          ScriptedProvider(json.dumps(good_payload(2))))
        bad = boot_planner({"planner": "llm"}, ScriptedProvider("هلوسة"))
        rec_ok = ok.plan(REQ).metadata["planner_record"]
        rec_bad = bad.plan(REQ).metadata["planner_record"]
        assert (rec_ok["used"], rec_ok["fallback_reason"]) == ("llm", None)
        assert rec_bad["used"] == "heuristic"
        assert rec_bad["fallback_reason"].startswith("invalid_json:")

    def test_hybrid_gate_recorded_both_sides(self):
        provider = ScriptedProvider(json.dumps(good_payload(2)))
        hybrid = boot_planner({"planner": "hybrid"}, provider)
        simple = hybrid.plan(PlanRequest("أصلح الإملاء"))
        complex_ = hybrid.plan(REQ)
        assert simple.metadata["planner_record"]["used"] == "heuristic"
        assert simple.metadata["planner_record"]["fallback_reason"] \
            .startswith("simple_tier:")
        assert complex_.metadata["planner_record"]["used"] == "llm"
        assert provider.calls == 1  # البسيط لم يستدعِ الموديل
