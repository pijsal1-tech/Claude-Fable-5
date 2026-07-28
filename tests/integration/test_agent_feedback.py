# -*- coding: utf-8 -*-
"""T-059 (R-504): Verification Feedback Loop.

المصفوفة:
- fail-then-fix: أول تشغيل لأمر الاختبار يفشل؛ الـ iteration التالية
  تستلم مخرجات الفشل في الـ prompt (الحلقة مغلقة) وتعيد التشغيل فينجح؛
  الرد النهائي يصدر بعد رؤية النجاح.
- gated + checkpointed command-writes: أمر يكتب ملفًا — الكتابة تمر
  ببوابة الموافقة (T-013) وتُلتقط snapshot/seal في CheckpointManager
  (T-053) — لا مسار طفرة بلا بوابة.
- budget compliance: نتيجة run_command طبقة high في سياق الـ iteration —
  تنجو من ميزانية ضيقة بينما تسقط عناصر normal؛ وحجمها مسقوف أصلًا
  بـ output_max_chars (T-058).
- verification instruction: تُحقن فقط عند وجود أوامر تحقق مهيأة.
"""
from __future__ import annotations

import pathlib
import textwrap

from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import APPROVAL_GRANTED, AgentTools, CommandPolicy
from chain.knowledge import KnowledgeAccumulator
from core.approval import ApprovalGate
from core.checkpoint import CheckpointManager
from core.execution import ExecutionRegistry
from tests.fakes.fake_provider import FakeProvider

# سكريبت تحقق stateful: أول تشغيل يفشل (ويترك marker)، الثاني ينجح —
# يجسّد "المحاولة الأولى تفشل الاختبار والثانية (المستنيرة بالفشل) تنجح".
VERIFY_SCRIPT = textwrap.dedent("""\
    import pathlib, sys
    m = pathlib.Path("marker.txt")
    if m.exists():
        print("PASS: all tests green")
        sys.exit(0)
    m.write_text("ran", encoding="utf-8")
    print("FAIL: assertion failed in test_feature - expected 2 got 1")
    sys.exit(1)
""")

RUN_TEST = (
    "سأشغل الاختبارات:\n"
    "```TOOL: run_command\n"
    "command: test\n"
    "reason: تحقق من التعديل\n"
    "```\n"
)
FINAL = "تم — الاختبارات نجحت والمهمة مكتملة."


def _make_loop(tmp_path: pathlib.Path, responses: list[str],
               checkpoint: CheckpointManager | None = None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "verify.py").write_text(VERIFY_SCRIPT, encoding="utf-8")
    tools = AgentTools(
        file_manager=FileManager(str(project)),
        command_runner=CommandRunner(cwd=str(project), auto_approve=True),
        project_root=str(project),
        command_policy=CommandPolicy(
            enforce=True,
            allowlist={"test": "python verify.py"},
            timeout_seconds=25.0,
        ),
        checkpoint=checkpoint,
    )
    provider = FakeProvider(responses=responses)
    loop = AgentLoop(
        tools=tools,
        send_fn=lambda p, h, s: provider.send(p, h, s),
        ws_send_fn=lambda m: None,
        max_iterations=4,
        # أمر مسموح في allowlist لا يزال يمر بالبوابة — auto+whitelist
        # يجعل الاختبار حتميًا بلا انتظار تفاعلي
        approval_gate=ApprovalGate(mode="auto", auto_whitelist={"command"}),
    )
    return loop, provider, project


# ═══════════════════ fail-then-fix fixture ═══════════════════

class TestFailThenFix:
    def test_second_iteration_sees_failure_and_passes(self, tmp_path):
        loop, provider, _ = _make_loop(
            tmp_path, [RUN_TEST, RUN_TEST, FINAL])
        result = loop.run("عدّل الميزة ثم تحقق")

        assert result == FINAL
        assert provider.call_count == 3

        # الحلقة مغلقة: prompt الجولة الثانية يحمل مخرجات فشل الأولى
        second_prompt = provider.calls[1].prompt
        assert "FAIL: assertion failed" in second_prompt
        assert "exit code: 1" in second_prompt

        # والجولة الثالثة (النهائية) ترى النجاح قبل إعلان الاكتمال
        third_prompt = provider.calls[2].prompt
        assert "PASS: all tests green" in third_prompt

    def test_failure_output_reaches_knowledge_as_command(self, tmp_path):
        loop, _, _ = _make_loop(tmp_path, [RUN_TEST, FINAL])
        loop.run("شغل الاختبار")
        summary = loop.knowledge.get_summary()
        assert summary.get("commands", 0) >= 1


# ═══════════════════ gated + checkpointed command writes ═══════════════════

class TestGatedCheckpointedWrites:
    def test_command_side_effect_snapshotted_and_sealed(self, tmp_path):
        ckpt = CheckpointManager(tmp_path / "ckpt")
        loop, _, project = _make_loop(tmp_path, [RUN_TEST, FINAL],
                                      checkpoint=ckpt)
        registry = ExecutionRegistry()
        ticket = registry.register("agent", "proj-t059")
        loop.run("شغل الاختبار", ticket=ticket)

        # الأمر أنشأ marker.txt — يجب أن يكون مُلتقطًا ومختومًا
        marker = str((project / "marker.txt").resolve())
        entries = {e.path for e in ckpt.entries_for_run(ticket.run_id)}
        seals = ckpt.seals_for_run(ticket.run_id)
        assert marker in entries          # snapshot ما-قبل (غياب = sha None)
        assert marker in seals            # seal ما-بعد
        assert seals[marker] is not None  # الملف موجود بعد الأمر

        # snapshot الغياب يجعل الاستعادة تحذف الملف — طفرة قابلة للتراجع
        pre = {e.path: e.sha256 for e in ckpt.entries_for_run(ticket.run_id)}
        assert pre[marker] is None

    def test_no_checkpoint_means_no_capture_but_command_runs(self, tmp_path):
        loop, _, project = _make_loop(tmp_path, [RUN_TEST, FINAL],
                                      checkpoint=None)
        loop.run("شغل الاختبار")
        assert (project / "marker.txt").exists()  # الأمر عمل

    def test_no_gate_blocks_command_entirely(self, tmp_path):
        # لا بوابة ⇒ رفض آمن (T-013) — الـ allowlist لا تتجاوز الموافقة
        project = tmp_path / "project"
        project.mkdir(exist_ok=True)
        (project / "verify.py").write_text(VERIFY_SCRIPT, encoding="utf-8")
        tools = AgentTools(
            file_manager=FileManager(str(project)),
            command_runner=CommandRunner(cwd=str(project),
                                         auto_approve=True),
            project_root=str(project),
            command_policy=CommandPolicy(
                enforce=True, allowlist={"test": "python verify.py"}),
        )
        provider = FakeProvider(responses=[RUN_TEST, FINAL])
        loop = AgentLoop(tools=tools,
                         send_fn=lambda p, h, s: provider.send(p, h, s),
                         ws_send_fn=lambda m: None,
                         max_iterations=3, approval_gate=None)
        loop.run("شغل الاختبار")
        assert not (project / "marker.txt").exists()  # لم يُنفذ شيء


# ═══════════════════ budget compliance ═══════════════════

class TestFeedbackBudget:
    def test_command_result_is_high_tier_survives_tight_budget(self):
        k = KnowledgeAccumulator()
        # عنصر normal كبير (dir) + نتيجة أمر (الآن high — T-059)
        k.add_tool_result("list_dir", {"path": "src"},
                          "file-listing " * 120)
        k.add_tool_result("run_command", {"command": "test"},
                          "FAIL: assertion failed in test_feature")
        ctx = k.build_iteration_context(max_tokens=60)
        assert "FAIL: assertion failed" in ctx      # التغذية الراجعة نجت
        assert "file-listing" not in ctx            # normal أُسقط أولًا

    def test_command_result_size_already_capped_upstream(self, tmp_path):
        # T-058: output_max_chars يسقف النتيجة قبل وصولها للمعرفة —
        # عنصر التغذية الراجعة لا يتضخم بلا حد مهما أسهب الأمر
        from chain.agent_tools import AgentTools as AT

        class Spew:
            def run(self, command, **kw):
                return {"success": True, "output": "y" * 50_000,
                        "error": "", "code": 0}

        tools = AT(command_runner=Spew(), project_root=str(tmp_path),
                   command_policy=CommandPolicy(
                       enforce=True, allowlist={"t": "cmd"},
                       output_max_chars=200))
        out = tools.tool_run_command("t", _approval=APPROVAL_GRANTED)
        assert len(out) < 1_000
        assert "اقتُطع" in out


# ═══════════════════ verification instruction injection ═══════════════════

class TestVerificationInstruction:
    def test_injected_when_test_command_configured(self, tmp_path):
        loop, provider, _ = _make_loop(tmp_path, [FINAL])
        loop.run("اعمل حاجة")
        assert "خطوة التحقق" in provider.calls[0].prompt

    def test_absent_without_policy(self, tmp_path):
        project = tmp_path / "p2"
        project.mkdir()
        tools = AgentTools(project_root=str(project))  # بلا سياسة = legacy
        provider = FakeProvider(responses=[FINAL])
        loop = AgentLoop(tools=tools,
                         send_fn=lambda p, h, s: provider.send(p, h, s),
                         ws_send_fn=lambda m: None, max_iterations=2)
        loop.run("اعمل حاجة")
        assert "خطوة التحقق" not in provider.calls[0].prompt

    def test_absent_when_allowlist_has_no_verify_entries(self, tmp_path):
        project = tmp_path / "p3"
        project.mkdir()
        tools = AgentTools(
            project_root=str(project),
            command_policy=CommandPolicy(
                enforce=True, allowlist={"deploy": "make deploy"}))
        provider = FakeProvider(responses=[FINAL])
        loop = AgentLoop(tools=tools,
                         send_fn=lambda p, h, s: provider.send(p, h, s),
                         ws_send_fn=lambda m: None, max_iterations=2)
        loop.run("اعمل حاجة")
        assert "خطوة التحقق" not in provider.calls[0].prompt
