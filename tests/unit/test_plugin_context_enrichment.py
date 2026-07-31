# -*- coding: utf-8 -*-
"""TSK-730b (BATCH-P3) — إثراء PluginContext في المسار الحقيقي.

الفجوة المسدودة: العقد (chain/plugin_api.py) يكشف run_id/metadata
لكن ``SmartOrchestrator._build_via_plugin`` كان يبنيهما فارغَين.
معايير القبول:
- إضافة مرشَّحة ترى run_id الممرَّر إلى select_strategy وترى
  metadata["complexity"] (نتيجة analyze_complexity).
- الافتراضي run_id="" لا يغيّر أي سلوك (goldens الـ planner تثبته
  في test_planner.py — هنا نثبت التوافق الخلفي للواجهات).
- bridge.start_chain يمرّر run_id المُنشأ إلى PlanRequest.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chain.orchestrator import SmartOrchestrator  # noqa: E402
from chain.planner import HeuristicPlanner, PlanRequest  # noqa: E402
from chain.plugin_registry import StrategyPluginRegistry  # noqa: E402
from chain.strategies import build_direct  # noqa: E402


# ─────────────── إضافة تجسسية: تلتقط الـ ctx وتبني خطة صالحة ───────────────

_captured: list = []


class _SpyStrategy:
    """إضافة صالحة الشكل — تسجّل الـ PluginContext المستلَم."""

    routing_hints = {"keywords": ["spyword"]}

    def build(self, ctx):
        _captured.append(ctx)
        return build_direct(ctx.user_request)


def _registry_with_spy() -> StrategyPluginRegistry:
    class EP:
        name = "spy_plugin"

        def load(self):
            return _SpyStrategy

    reg = StrategyPluginRegistry(entry_points_fn=lambda *, group: [EP()])
    reg.discover()
    assert reg.get("spy_plugin") is not None, reg.quarantined
    return reg


def _fresh():
    _captured.clear()
    return SmartOrchestrator(plugin_registry=_registry_with_spy())


class TestRunIdReachesPlugin:
    def test_run_id_passed_via_select_strategy(self):
        orch = _fresh()
        result = orch.select_strategy("افعل spyword الآن", run_id="run-730b")
        assert result.metadata.get("plugin_name") == "spy_plugin"
        # آخر التقاط هو نداء البناء الحقيقي (dry_run في discover يسبقه).
        ctx = _captured[-1]
        assert ctx.run_id == "run-730b"

    def test_default_run_id_is_empty_string(self):
        orch = _fresh()
        orch.select_strategy("افعل spyword الآن")
        assert _captured[-1].run_id == ""

    def test_run_id_flows_through_heuristic_planner(self):
        orch = _fresh()
        planner = HeuristicPlanner(orch)
        planner.plan(PlanRequest("افعل spyword الآن", run_id="run-planner"))
        assert _captured[-1].run_id == "run-planner"


class TestComplexityMetadataReachesPlugin:
    def test_metadata_contains_complexity_dict(self):
        orch = _fresh()
        orch.select_strategy("افعل spyword الآن", run_id="r1")
        meta = _captured[-1].metadata
        assert "complexity" in meta
        assert isinstance(meta["complexity"], dict)
        # نفس شكل analyze_complexity().to_dict() — مفاتيح جوهرية موجودة.
        assert "total" in meta["complexity"]

    def test_metadata_is_defensive_copy(self):
        """تعديل نسخة metadata عند الإضافة لا يمس شيئًا (عقد T-101)."""
        orch = _fresh()
        orch.select_strategy("افعل spyword الآن")
        meta = _captured[-1].metadata
        meta["injected"] = True
        assert "injected" not in _captured[-1].metadata


class TestBackwardCompatibility:
    def test_plan_request_run_id_default_empty(self):
        assert PlanRequest("x").run_id == ""

    def test_bridge_passes_generated_run_id(self, tmp_path):
        """bridge.start_chain يبني PlanRequest بـ run_id المُنشأ نفسه."""
        from chain.bridge import ChainBridge

        seen: dict = {}

        class _CapturingPlanner:
            name = "capturing"

            def plan(self, request, context=None, capacity=None):
                seen["run_id"] = request.run_id
                return build_direct(request.user_request)

        class _FakeProvider:
            name = "fake"
            model = "m"

        bridge = ChainBridge(provider=_FakeProvider(),
                             project_root=str(tmp_path),
                             runs_dir=str(tmp_path / "runs"),
                             planner=_CapturingPlanner())
        run_id = bridge.start_chain(lambda msg: None, "أنشئ ملفًا")
        try:
            assert run_id and seen["run_id"] == run_id
        finally:
            # لا ننتظر السلسلة — يكفي التقاط الـ PlanRequest؛ ننظّف الخيط.
            import time
            for _ in range(100):
                if not bridge.is_running:
                    break
                time.sleep(0.05)
