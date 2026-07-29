# -*- coding: utf-8 -*-
"""TSK-616 (ASF-03 §R4): إظهار سقف snapshot — rollback جزئي لم يعد صامتًا.

الخلفية (MASTER_REVIEW:325، الإصلاح «إظهار لا رفع سقف» :722):
مسح snapshot في tool_run_command محدود بـ `_CKPT_MAX_FILES` وسقف حجم
`_CKPT_MAX_FILE_BYTES`. قبل TSK-616 كان تجاوز السقفين يُفقد التغطية
صامتًا — المستخدم يوافق على أمر ثم يكتشف (أو لا يكتشف) أن التراجع جزئي.

المصفوفة (القبول: اختبار بحد مصغّر → إطار يحمل علم partial_rollback؛
الواجهة تعرضه):
- سقف العدد المصغّر → التقرير يحمل ⚠️ + last_partial_rollback=True
- سقف الحجم المصغّر → نفس السلوك (ملف واحد فوق السقف يكفي)
- تحت السقفين (سلبي) → لا ⚠️ ولا علم — المسار القديم حرفيًا
- بلا checkpoint/تذكرة (سلبي) → لا علم (لا مسح أصلًا)
- إطار agent_step النهائي (E2E عبر AgentLoop) يحمل partial_rollback
- app.js يقرأ العلم ويعرضه (toast + نص على الكارت) — فحص نصي
  بنمط test_rollback_ui.py
"""
from __future__ import annotations

import pathlib
import threading

from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import (
    APPROVAL_GRANTED,
    AgentTools,
    CommandPolicy,
)
from core.approval import ApprovalGate
from core.checkpoint import CheckpointManager
from core.execution import ExecutionRegistry
from tests.fakes.fake_provider import FakeProvider

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "app.js"
STYLE_CSS = ROOT / "static" / "style.css"

WARNING_MARK = "⚠️ [checkpoint]: تغطية snapshot جزئية"

POLICY = CommandPolicy(enforce=True, allowlist={"ok": "echo ok"})


class FakeCmd:
    """CommandRunner مزيف — نجاح فوري (نمط test_run_command.py)."""

    def run(self, command: str, **kwargs) -> dict:
        return {"success": True, "output": "ok", "error": "", "code": 0}


def _project(tmp_path: pathlib.Path, n_files: int = 6) -> pathlib.Path:
    project = tmp_path / "project"
    project.mkdir()
    for i in range(n_files):
        (project / f"f{i}.txt").write_text(f"content-{i}", encoding="utf-8")
    return project


def _tools_with_ckpt(tmp_path: pathlib.Path,
                     project: pathlib.Path) -> AgentTools:
    tools = AgentTools(command_runner=FakeCmd(),
                       project_root=str(project),
                       command_policy=POLICY,
                       checkpoint=CheckpointManager(tmp_path / "ckpt"))
    registry = ExecutionRegistry()
    tools.run_ticket = registry.register("agent", "proj-tsk616")
    return tools


# ═══════════════ سقف مصغّر → علم + تحذير في التقرير ═══════════════

class TestReportAndFlag:

    def test_file_count_cap_sets_flag_and_warns(self, tmp_path):
        project = _project(tmp_path, n_files=6)
        tools = _tools_with_ckpt(tmp_path, project)
        tools._CKPT_MAX_FILES = 3  # حد مصغّر — المشروع (6 ملفات) يتجاوزه

        out = tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)

        assert tools.last_partial_rollback is True
        assert WARNING_MARK in out
        assert "التراجع عن آثار هذا الأمر سيكون جزئيًا" in out

    def test_file_size_cap_sets_flag_and_warns(self, tmp_path):
        project = _project(tmp_path, n_files=2)
        (project / "big.bin").write_bytes(b"x" * 64)
        tools = _tools_with_ckpt(tmp_path, project)
        tools._CKPT_MAX_FILE_BYTES = 32  # big.bin (64B) فوق السقف

        out = tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)

        assert tools.last_partial_rollback is True
        assert WARNING_MARK in out

    def test_under_caps_no_flag_no_warning(self, tmp_path):
        """سلبي: تحت السقفين المسار القديم حرفيًا — لا ضجيج زائف."""
        project = _project(tmp_path, n_files=3)
        tools = _tools_with_ckpt(tmp_path, project)

        out = tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)

        assert tools.last_partial_rollback is False
        assert WARNING_MARK not in out
        assert not out.startswith("❌")

    def test_no_checkpoint_no_flag(self, tmp_path):
        """سلبي: بلا checkpoint لا مسح أصلًا ⇒ العلم يبقى False."""
        project = _project(tmp_path, n_files=6)
        tools = AgentTools(command_runner=FakeCmd(),
                           project_root=str(project),
                           command_policy=POLICY)
        tools._CKPT_MAX_FILES = 3

        out = tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)

        assert tools.last_partial_rollback is False
        assert WARNING_MARK not in out

    def test_flag_resets_between_commands(self, tmp_path):
        """أمر مقتطع ثم أمر تحت السقف — العلم لآخر أمر لا تراكمي."""
        project = _project(tmp_path, n_files=6)
        tools = _tools_with_ckpt(tmp_path, project)
        tools._CKPT_MAX_FILES = 3
        tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)
        assert tools.last_partial_rollback is True

        tools._CKPT_MAX_FILES = 400  # السقف الافتراضي — لا اقتطاع
        out = tools.tool_run_command("ok", _approval=APPROVAL_GRANTED)
        assert tools.last_partial_rollback is False
        assert WARNING_MARK not in out


# ═══════════════ الإطار يحمل العلم (E2E عبر AgentLoop) ═══════════════

AI_TOOL_CALL = (
    "سأنفذ الأمر:\n"
    "```TOOL: run_command\n"
    "command: echo TSK616\n"
    "reason: اختبار سقف snapshot\n"
    "```\n"
)
AI_FINAL = "انتهيت."


class FrameSink:
    """نمط tests/integration/test_agent_gated_approvals.py"""

    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def done_frames(self) -> list[dict]:
        with self._lock:
            return [f for f in self.frames
                    if f.get("tool") == "run_command"
                    and f.get("status") == "done"]


def _run_loop_e2e(tmp_path, project, mini_caps: bool) -> list[dict]:
    tools = AgentTools(
        file_manager=FileManager(str(project)),
        command_runner=CommandRunner(cwd=str(project), auto_approve=True),
        project_root=str(project),
        checkpoint=CheckpointManager(tmp_path / "ckpt"),
    )
    if mini_caps:
        tools._CKPT_MAX_FILES = 3
    provider = FakeProvider(responses=[AI_TOOL_CALL, AI_FINAL])
    sink = FrameSink()
    gate = ApprovalGate(mode="auto", auto_whitelist={"command"})
    loop = AgentLoop(
        tools=tools,
        send_fn=lambda p, h, s: provider.send(p, h, s),
        ws_send_fn=sink,
        max_iterations=3,
        approval_gate=gate,
    )
    registry = ExecutionRegistry()
    ticket = registry.register("agent", "proj-tsk616-e2e")
    result: list = []
    t = threading.Thread(
        target=lambda: result.append(loop.run("نفذ", ticket=ticket)))
    t.start()
    t.join(timeout=15.0)
    assert not t.is_alive()
    return sink.done_frames()


class TestFrameCarriesFlag:

    def test_done_frame_partial_rollback_true_over_cap(self, tmp_path):
        project = _project(tmp_path, n_files=6)
        frames = _run_loop_e2e(tmp_path, project, mini_caps=True)
        assert frames, "لا إطار done لأداة run_command"
        assert frames[-1].get("partial_rollback") is True

    def test_done_frame_partial_rollback_false_under_cap(self, tmp_path):
        project = _project(tmp_path, n_files=2)
        frames = _run_loop_e2e(tmp_path, project, mini_caps=False)
        assert frames, "لا إطار done لأداة run_command"
        assert frames[-1].get("partial_rollback") is False


# ═══════════════ الواجهة تعرض العلم (فحص نصي — نمط test_rollback_ui) ═══

class TestUiSurfacesFlag:

    def test_app_js_reads_partial_rollback_flag(self):
        src = APP_JS.read_text(encoding="utf-8")
        assert "data.partial_rollback" in src
        assert "showPartialRollbackWarning" in src

    def test_app_js_shows_toast_and_persistent_card_text(self):
        src = APP_JS.read_text(encoding="utf-8")
        fn = src.split("function showPartialRollbackWarning", 1)[1]
        fn = fn.split("\n}", 1)[0]
        assert "toast(" in fn                      # إظهار مؤقت
        assert "terminal-partial-rollback" in fn   # نص دائم على الكارت
        assert "التراجع سيكون جزئيًا" in fn        # الصياغة المطلوبة

    def test_style_css_has_warning_styles(self):
        css = STYLE_CSS.read_text(encoding="utf-8")
        assert ".toast.warning" in css
        block = css.split(".terminal-partial-rollback", 1)[1].split("}", 1)[0]
        assert "var(--warning)" in block  # ألوان بالتوكنز فقط (TF-04)
