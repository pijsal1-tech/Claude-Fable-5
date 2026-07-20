# -*- coding: utf-8 -*-
"""T-102 (R-801): Demo strategy package + routing integration — E2E.

بنود قبول T-102:
- الحزمة التجريبية (مثبتة pip فعليًا في venv مؤقت معزول) تُكتشف عبر
  importlib.metadata وتوجّه طلبًا مطابقًا وتنفَّذ حتى الاكتمال عبر
  ChainBridge الحقيقي (بوابة موافقة + كتابة ملف فعلية).
- حزمة معطوبة عمدًا: الإقلاع أخضر والحجر الصحي مُبلَّغ — المضيف لا
  ينهار أبدًا.
- بلا إضافات: السلوك الأساسي **بايت-بايت** (نفس StrategyResult
  حرفيًا مع/بدون registry فارغ).

ملاحظة عزل: اختبار الـ pip الحقيقي يبني venv مؤقتًا (--system-site-packages
للوصول لبيئة المضيف) ويثبّت examples/demo_strategy فيه ثم يشغّل
الاكتشاف بسطر بايثون داخل الـ venv — بيئة الاختبار الرئيسية لا
تتلوث أبدًا (uninstall يعيدها حرفيًا لأنها لم تُمس أصلًا).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from actions.file_manager import FileManager  # noqa: E402
from actions.response_parser import ResponseParser  # noqa: E402
from chain.action_applier import ActionApplier  # noqa: E402
from chain.bridge import ChainBridge  # noqa: E402
from chain.orchestrator import SmartOrchestrator  # noqa: E402
from chain.plugin_registry import StrategyPluginRegistry  # noqa: E402
from core.approval import ApprovalGate  # noqa: E402
from tests.fakes.fake_provider import FakeProvider  # noqa: E402

DEMO_PKG = REPO_ROOT / "examples" / "demo_strategy"
JOIN_TIMEOUT = 10.0

AI_RESPONSE_WITH_FILE = (
    "تم التنفيذ:\n"
    "```FILE: echoed.txt\n"
    "demo plugin output\n"
    "```\n"
)


class FrameSink:
    """يجمع إطارات WS (نفس نمط test_chain_gated_apply)."""

    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def of_type(self, frame_type: str) -> list[dict]:
        with self._lock:
            return [f for f in self.frames if f.get("type") == frame_type]


def _demo_registry() -> StrategyPluginRegistry:
    """سجل بإضافة demo الحقيقية (استيراد مباشر من examples/)."""
    sys.path.insert(0, str(DEMO_PKG))
    try:
        from demo_strategy import DemoEchoStrategy
    finally:
        sys.path.remove(str(DEMO_PKG))

    class EP:
        name = "demo_echo"

        def load(self):
            return DemoEchoStrategy

    reg = StrategyPluginRegistry(entry_points_fn=lambda *, group: [EP()])
    reg.discover()
    assert reg.get("demo_echo") is not None, reg.quarantined
    return reg


# ═══════════════ 1) route + execute E2E ═══════════════

@pytest.mark.integration
class TestRouteAndExecute:
    def test_matching_request_routes_to_plugin_and_executes(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        fm = FileManager(str(project))
        applier = ActionApplier(parser=ResponseParser(), file_manager=fm,
                                auto_backup=False)
        gate = ApprovalGate(mode="auto",
                            auto_whitelist={"write", "edit", "command"})
        bridge = ChainBridge(
            provider=FakeProvider(responses=[AI_RESPONSE_WITH_FILE]),
            project_root=str(project),
            runs_dir=tmp_path / "runs",
            action_applier=applier,
            approval_gate=gate,
            plugin_registry=_demo_registry(),
        )
        sink = FrameSink()
        run_id = bridge.start_chain(sink, "please demo echo this request")
        assert run_id
        thread = bridge._active_thread
        assert thread is not None
        thread.join(timeout=JOIN_TIMEOUT)
        assert not thread.is_alive()

        # وجّه فعلاً للإضافة: إطارات chain_step تحمل خطوة الإضافة
        # حرفيًا (step_id="demo-echo" من DemoEchoStrategy.build).
        step_ids = {f.get("step_id") for f in sink.of_type("chain_step")}
        assert step_ids == {"demo-echo"}
        finished = sink.of_type("chain_finished")
        assert finished and finished[0]["status"] == "completed"
        # ونفّذ حتى الاكتمال عبر مسار Runner الطبيعي (كتابة فعلية):
        assert (project / "echoed.txt").read_text(
            encoding="utf-8").strip() == "demo plugin output"

    def test_non_matching_request_uses_builtins(self, tmp_path):
        orch = SmartOrchestrator(plugin_registry=_demo_registry())
        result = orch.select_strategy("اكتب ملف hello")
        assert result.strategy_name == "direct"
        assert "plugin_name" not in result.metadata

    def test_force_strategy_overrides_plugin(self):
        orch = SmartOrchestrator(plugin_registry=_demo_registry())
        result = orch.select_strategy("please demo echo this",
                                      force_strategy="direct")
        assert result.strategy_name == "direct"

    def test_crashing_plugin_build_falls_back_safely(self):
        class Crashy:
            routing_hints = {"keywords": ["demo echo"]}

            def build(self, ctx, **kwargs):
                raise RuntimeError("runtime bomb")

        class EP:
            name = "crashy_ok_at_dryrun"

            def load(self):
                return Crashy

        # نمرر بوابة dry-run بإضافة تنجح عليها ثم تنهار وقت التشغيل؟
        # الأبسط والأصدق: سجل مزروع يدويًا (نفس الشكل) — build ينهار
        # وقت الاختيار الحقيقي ⇒ سقوط آمن للمدمج.
        reg = StrategyPluginRegistry(entry_points_fn=lambda *, group: [])
        reg.discover()
        reg._loaded["crashy"] = Crashy  # زرع مباشر بعد بوابة فارغة
        orch = SmartOrchestrator(plugin_registry=reg)
        result = orch.select_strategy("please demo echo this")
        assert result.strategy_name == "direct"  # المدمج، لا انهيار


# ═══════════════ 2) real pip install (isolated venv) ═══════════════

@pytest.mark.integration
class TestRealPipInstall:
    def test_pip_installed_package_discovered_via_entry_points(self, tmp_path):
        """التثبيت الحقيقي عبر pip في venv معزول + اكتشاف importlib."""
        venv_dir = tmp_path / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages",
             str(venv_dir)],
            check=True, capture_output=True, timeout=120)
        vpy = venv_dir / "bin" / "python"
        proc = subprocess.run(
            [str(vpy), "-m", "pip", "install", "-q", "--no-build-isolation",
             str(DEMO_PKG)],
            capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            pytest.skip(f"pip install unavailable here: {proc.stderr[-300:]}")

        probe = subprocess.run(
            [str(vpy), "-c",
             "import sys; sys.path.insert(0, %r)\n"
             "from chain.plugin_registry import StrategyPluginRegistry\n"
             "r = StrategyPluginRegistry(); r.discover()\n"
             "import json\n"
             "print(json.dumps({'loaded': sorted(r.loaded),"
             " 'quarantined': [q.to_dict() for q in r.quarantined]}))"
             % str(REPO_ROOT)],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT)
        assert probe.returncode == 0, probe.stderr
        state = json.loads(probe.stdout.strip().splitlines()[-1])
        assert "demo_echo" in state["loaded"]
        # البيئة الرئيسية لم تُمس: الاكتشاف هنا لا يرى الحزمة.
        host_reg = StrategyPluginRegistry()
        host_reg.discover()
        assert "demo_echo" not in host_reg.loaded


# ═══════════════ 3) broken plugin boot survival ═══════════════

@pytest.mark.integration
class TestBrokenPluginBootSurvival:
    def test_broken_plugin_boots_green_and_reports_quarantine(self, capsys):
        """محاكاة تسلسل إقلاع server.py حرفيًا مع إضافة معطوبة."""
        class EP:
            name = "broken"

            def load(self):
                raise ImportError("deliberately broken package")

        reg = StrategyPluginRegistry(entry_points_fn=lambda *, group: [EP()])
        # نفس أسطر server.py boot (discover + طباعة الحجر):
        reg.discover()
        for q in reg.quarantined:
            print(f"  ⚠️ Plugin quarantined: {q.name} [{q.stage}] {q.reason}")
        out = capsys.readouterr().out
        assert "Plugin quarantined: broken [import]" in out
        assert "deliberately broken" in out
        # والمضيف حي: orchestrator يعمل بالسجل نفسه.
        orch = SmartOrchestrator(plugin_registry=reg)
        assert orch.select_strategy("اكتب ملف hello").strategy_name == "direct"

    def test_server_boot_sequence_wires_registry(self):
        """بوابة نصية: server.py يحمّل السجل مرة عند الإقلاع ويمرره
        للجسر والأوركستريتور (لا اكتشاف ثانٍ)."""
        src = (REPO_ROOT / "server.py").read_text(encoding="utf-8")
        assert "plugin_registry = StrategyPluginRegistry()" in src
        assert "plugin_registry.discover()" in src
        assert src.count("plugin_registry.discover()") == 1
        assert "plugin_registry=plugin_registry" in src
        assert "SmartOrchestrator(plugin_registry=plugin_registry)" in src
        assert "Plugin quarantined" in src


# ═══════════════ 4) baseline unchanged ═══════════════

@pytest.mark.integration
class TestBaselineUnchanged:
    def test_no_registry_and_empty_registry_identical(self):
        """بلا سجل = سجل فارغ = السلوك الأساسي بايت-بايت (R-402
        regression: قرارات التوجيه للمدمجين لا تتغير)."""
        empty = StrategyPluginRegistry(entry_points_fn=lambda *, group: [])
        empty.discover()
        requests = [
            "اكتب ملف hello",
            "refactor the architecture across all files",
            "please demo echo this request",  # لا إضافة ⇒ مدمج
        ]
        for req in requests:
            r_none = SmartOrchestrator().select_strategy(req)
            r_empty = SmartOrchestrator(
                plugin_registry=empty).select_strategy(req)
            assert r_none.strategy_name == r_empty.strategy_name
            assert r_none.metadata == r_empty.metadata
            assert [s.prompt_template for s in r_none.steps] == \
                   [s.prompt_template for s in r_empty.steps]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
