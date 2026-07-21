# -*- coding: utf-8 -*-
"""T-106 (R-803): اختبارات بروتوكول Planner + استخراج HeuristicPlanner.

ثلاث حزم (بنود القبول الثلاثة):
1. Goldens: خطط HeuristicPlanner ≡ select_strategy القديم **بايت-بايت**
   عبر سيناريوهات تغطي الاستراتيجيات كلها + الفرض + المجهول.
2. عدة توافق البروتوكول (PlannerContractMixin — نفس نمط
   RunnerContractMixin من T-039): ترثها وتعرّف make_planner.
3. درزة config: heuristic الصريح ≡ الغائب؛ الاسم المجهول = فشل صاخب.
"""
from __future__ import annotations

import pytest

from chain.orchestrator import SmartOrchestrator
from chain.planner import (
    DEFAULT_PLANNER,
    ExecutionPlan,
    HeuristicPlanner,
    KNOWN_PLANNERS,
    Planner,
    PlanRequest,
    planner_from_config,
    resolve_planner_name,
)
from chain.strategies import StrategyResult


# ═══════════════════════════════════════════════════════
#   سيناريوهات الـ goldens — تغطي كل فروع select_strategy
# ═══════════════════════════════════════════════════════

_BIG = "\n".join(f"line {i}: value = compute({i})" for i in range(1500))
_HUGE_FILES = {f"mod_{i}.py": _BIG for i in range(6)}

GOLDEN_SCENARIOS: list[tuple[str, PlanRequest]] = [
    ("direct_small", PlanRequest("أصلح الخطأ الإملائي في العنوان")),
    ("direct_with_file", PlanRequest(
        "غيّر اسم الدالة", file_content="def foo():\n    return 1\n",
        file_path="app.py")),
    ("direct_with_files", PlanRequest(
        "علّق على الكود", files={"a.py": "x = 1\n", "b.py": "y = 2\n"})),
    ("context_window_medium", PlanRequest(
        "أعد هيكلة الوحدة وحسّن الأداء وفسّر القرارات",
        file_content="\n".join(f"row_{i} = {i}" for i in range(600)),
        file_path="medium.py")),
    ("chunk_chain_large", PlanRequest(
        "راجع الملف الضخم كاملًا وأصلح الأخطاء",
        file_content=_BIG, file_path="big.py")),
    ("map_reduce_many_files", PlanRequest(
        "حلل المشروع كاملًا واكتب تقريرًا عن البنية",
        files=_HUGE_FILES)),
    ("pipeline_risky", PlanRequest(
        "أعد تصميم نظام auth والصلاحيات وقاعدة البيانات مع migration "
        "كامل للمستخدمين وتشفير كلمات المرور وحماية من SQL injection",
        files=_HUGE_FILES)),
    ("forced_direct", PlanRequest(
        "حلل المشروع كاملًا", files=_HUGE_FILES,
        force_strategy="direct")),
    ("forced_pipeline", PlanRequest(
        "أصلح خطأ إملائيًا", force_strategy="pipeline")),
    # فرض صريح يضمن المرور بفروع البناء الستة كلها في select_strategy
    # مهما تحركت عتبات التوصية (التغطية بالفرض لا بالصدفة):
    ("forced_context_window", PlanRequest(
        "راجع", file_content=_BIG, file_path="big.py",
        force_strategy="context_window")),
    ("forced_context_window_files", PlanRequest(
        "راجع", files={"a.py": "x = 1\n", "b.py": "y = 2\n"},
        force_strategy="context_window")),
    ("forced_chunk_chain", PlanRequest(
        "راجع الملف الضخم", file_content=_BIG, file_path="big.py",
        force_strategy="chunk_chain")),
    ("forced_chunk_chain_files", PlanRequest(
        "راجع", files=_HUGE_FILES, force_strategy="chunk_chain")),
    ("forced_map_reduce", PlanRequest(
        "حلل", files=_HUGE_FILES, force_strategy="map_reduce")),
    ("forced_pipeline_with_file", PlanRequest(
        "أعد تصميم auth", file_content=_BIG, file_path="auth.py",
        force_strategy="pipeline")),
    ("forced_unknown_falls_direct", PlanRequest(
        "أي طلب", force_strategy="no_such_strategy")),
    ("forced_delegate_falls_direct", PlanRequest(
        "أي طلب", force_strategy="delegate")),
]


def _legacy_plan(orch: SmartOrchestrator, req: PlanRequest) -> StrategyResult:
    """المسار القديم حرفيًّا — select_strategy مباشرة (pre-extraction)."""
    return orch.select_strategy(
        user_request=req.user_request,
        files=req.files,
        file_content=req.file_content,
        file_path=req.file_path,
        force_strategy=req.force_strategy,
    )


@pytest.mark.parametrize(
    "req", [s[1] for s in GOLDEN_SCENARIOS],
    ids=[s[0] for s in GOLDEN_SCENARIOS])
class TestGoldenParity:
    """بند القبول 1: الخطة عبر البروتوكول ≡ المسار القديم بايت-بايت."""

    def test_plan_identical_pre_post_extraction(self, req: PlanRequest):
        orch = SmartOrchestrator()
        legacy = _legacy_plan(orch, req)
        extracted = HeuristicPlanner(orch).plan(req)
        # dataclasses بمساواة قيمية كاملة: strategy_name + steps
        # (بكل حقول ChainStep) + policy + metadata — تطابق تام.
        assert extracted == legacy

    def test_chain_run_identical(self, req: PlanRequest):
        """to_chain_run بنفس run_id ⇒ نفس الـ ChainRun (مسار bridge)."""
        orch = SmartOrchestrator()
        legacy_run = _legacy_plan(orch, req).to_chain_run("run-golden01")
        planned_run = (HeuristicPlanner(orch).plan(req)
                       .to_chain_run("run-golden01"))
        assert planned_run.run_id == legacy_run.run_id
        assert planned_run.steps == legacy_run.steps
        assert planned_run.policy == legacy_run.policy


class TestGoldenCoverage:
    """قفل التغطية: السيناريوهات تمر فعلًا بالبنّائين الخمسة كلهم
    (delegate خارجها — مساره DelegateBridge لا select_strategy)."""

    def test_scenarios_cover_all_builder_strategies(self):
        p = HeuristicPlanner()
        seen = {p.plan(req).strategy_name for _, req in GOLDEN_SCENARIOS}
        assert seen == {"direct", "context_window", "chunk_chain",
                        "map_reduce", "pipeline"}


class TestGoldenParityWithPlugins:
    """الاستخراج يحافظ على مسار إضافات T-102 حرفيًّا (نفس السجل)."""

    def test_plugin_routing_preserved(self):
        class _FakeRegistry:
            loaded: dict[str, type] = {}
            quarantined: list = []

        orch = SmartOrchestrator(plugin_registry=_FakeRegistry())
        req = PlanRequest("أصلح الخطأ")
        assert HeuristicPlanner(orch).plan(req) == _legacy_plan(orch, req)


# ═══════════════════════════════════════════════════════
#   عدة توافق البروتوكول — نمط T-039 (ورث + make_planner)
# ═══════════════════════════════════════════════════════

class PlannerContractMixin:
    """ورِثها وعرّف make_planner — تحصل على عقد Planner كاملًا.

    (نفس فلسفة RunnerContractMixin من T-039: T-107 يشغّل LLMPlanner
    وHybridPlanner عبر هذه العدة نفسها بلا اختبارات مكررة.)
    """

    def make_planner(self) -> Planner:
        raise NotImplementedError("عرّف make_planner في الصنف الوارث")

    # ── العقد ──

    def test_satisfies_protocol(self):
        assert isinstance(self.make_planner(), Planner)

    def test_has_stable_name(self):
        p = self.make_planner()
        assert isinstance(p.name, str) and p.name
        assert p.name == self.make_planner().name

    def test_plan_returns_executable_plan(self):
        plan = self.make_planner().plan(PlanRequest("اشرح الكود"))
        assert isinstance(plan, ExecutionPlan)
        assert plan.strategy_name
        assert plan.steps, "خطة بلا خطوات غير قابلة للتنفيذ"
        run = plan.to_chain_run("run-contract1")
        assert run.run_id == "run-contract1" and run.steps

    def test_plan_carries_complexity_metadata(self):
        plan = self.make_planner().plan(PlanRequest("اشرح الكود"))
        assert "complexity" in plan.metadata

    def test_deterministic_same_input_same_plan(self):
        p = self.make_planner()
        req = PlanRequest("راجع الملف", file_content="x = 1\n",
                          file_path="a.py")
        assert p.plan(req) == p.plan(req)

    def test_force_strategy_respected(self):
        plan = self.make_planner().plan(
            PlanRequest("أي طلب", force_strategy="pipeline"))
        assert plan.strategy_name == "pipeline"

    def test_unknown_force_falls_back_to_direct(self):
        """قفل سلوك corpus T-034: النص المجهول ⇒ direct لا انفجار."""
        plan = self.make_planner().plan(
            PlanRequest("أي طلب", force_strategy="???"))
        assert plan.strategy_name == "direct"

    def test_context_and_capacity_optional(self):
        """None مسموح دائمًا — التوقيع الثلاثي عقد لا زخرفة."""
        p = self.make_planner()
        req = PlanRequest("اشرح")
        assert p.plan(req, context=None, capacity=None) == p.plan(req)


class TestHeuristicPlannerContract(PlannerContractMixin):
    """بند القبول 2: HeuristicPlanner يجتاز عدة العقود كاملة."""

    def make_planner(self) -> Planner:
        return HeuristicPlanner()


class TestPlanRequestShape:

    def test_frozen(self):
        req = PlanRequest("اشرح")
        with pytest.raises(Exception):
            req.user_request = "غيّر"  # type: ignore[misc]

    def test_defaults_match_legacy_signature(self):
        req = PlanRequest("اشرح")
        assert (req.files, req.file_content, req.file_path,
                req.force_strategy) == (None, None, "", None)


# ═══════════════════════════════════════════════════════
#   درزة config — بند القبول 3
# ═══════════════════════════════════════════════════════

class TestConfigSeam:

    def test_missing_key_defaults_to_heuristic(self):
        assert resolve_planner_name(None) == DEFAULT_PLANNER == "heuristic"

    def test_explicit_heuristic_accepted(self):
        assert resolve_planner_name("heuristic") == "heuristic"

    @pytest.mark.parametrize("bad", ["magic", "LLM", "", 3, ["heuristic"]])
    def test_unknown_value_fails_loudly(self, bad):
        with pytest.raises(ValueError):
            resolve_planner_name(bad)

    def test_known_planners_is_single_source(self):
        # T-107 وسّعها كما خُطّط — heuristic يبقى الافتراضي.
        assert KNOWN_PLANNERS == ("heuristic", "llm", "hybrid")

    def test_factory_builds_heuristic_over_given_orchestrator(self):
        orch = SmartOrchestrator()
        p = planner_from_config("heuristic", orch)
        assert isinstance(p, HeuristicPlanner)
        assert p._orchestrator is orch

    def test_explicit_and_default_paths_equivalent(self):
        """بند القبول: planner: heuristic الصريح ≡ المفتاح الغائب —
        نفس الصنف ونفس الخطط بايت-بايت."""
        req = PlanRequest("راجع الملف", file_content="x = 1\n",
                          file_path="a.py")
        explicit = planner_from_config("heuristic")
        default = planner_from_config(None)
        assert type(explicit) is type(default)
        assert explicit.plan(req) == default.plan(req)

    def test_config_yaml_carries_explicit_default(self):
        """config.yaml يوثّق الافتراضي صراحة — ولا يكسر الإقلاع."""
        import pathlib
        import yaml
        root = pathlib.Path(__file__).resolve().parents[2]
        cfg = yaml.safe_load((root / "config.yaml").read_text("utf-8"))
        assert resolve_planner_name(cfg.get("planner")) == "heuristic"


# ═══════════════════════════════════════════════════════
#   درزة الـ bridge — الافتراضي يمر عبر البروتوكول بلا تغيير سلوك
# ═══════════════════════════════════════════════════════

class TestBridgeSeam:

    def test_bridge_default_planner_is_heuristic_over_own_orchestrator(
            self, tmp_path):
        from chain.bridge import ChainBridge
        from tests.fakes.fake_provider import FakeProvider

        bridge = ChainBridge(FakeProvider(responses=["ok"]),
                             project_root=str(tmp_path))
        assert isinstance(bridge._planner, HeuristicPlanner)
        # نفس الأوركستريتور (بسجل إضافاته) — لا تركيبة ثانية منفصلة.
        assert bridge._planner._orchestrator is bridge._orchestrator

    def test_bridge_accepts_injected_planner(self, tmp_path):
        from chain.bridge import ChainBridge
        from tests.fakes.fake_provider import FakeProvider

        marker = HeuristicPlanner()
        bridge = ChainBridge(FakeProvider(responses=["ok"]),
                             project_root=str(tmp_path), planner=marker)
        assert bridge._planner is marker
