# -*- coding: utf-8 -*-
"""T-058 (R-504): run_command Agent Tool + Allowlist.

المصفوفة:
- allowlist enforcement: أمر حرفي مسموح / اسم مدخل منطقي / رفض مهيكل
  مسجَّل (never silent) / قائمة فارغة مع الفرض = رفض الكل / وضع legacy
  (بلا قسم config) = لا فرض.
- command_policy_from: قسم صالح / غائب / أنواع خاطئة / قيم غير نصية تُسقط.
- مهلة أمر معلّق: العودة برسالة مهلة صريحة قبل انتهاء الأمر الحقيقي.
- إلغاء عبر RunTicket أثناء أمر معلّق: العودة برسالة إلغاء فورًا.
- سقف حجم المخرجات: اقتطاع بعلامة صريحة + بقاء exit code في التقرير.
"""
from __future__ import annotations

import logging
import threading
import time

import pytest

from chain.agent_tools import (
    AgentTools,
    CommandPolicy,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_OUTPUT_MAX_CHARS,
    command_policy_from,
)
from core.execution import ExecutionRegistry


# ═══════════════════ مساعدات ═══════════════════

class FakeCmd:
    """CommandRunner مزيف — يسجل النداءات ويعيد نتيجة مُعدّة سلفًا."""

    def __init__(self, result: dict | None = None, delay: float = 0.0):
        self.calls: list[str] = []
        self.delay = delay
        self.result = result or {
            "success": True, "output": "ok", "error": "", "code": 0,
        }

    def run(self, command: str, **kwargs) -> dict:
        self.calls.append(command)
        if self.delay:
            time.sleep(self.delay)
        return self.result


def _tools(policy: CommandPolicy | None = None,
           cmd: FakeCmd | None = None) -> tuple[AgentTools, FakeCmd]:
    runner = cmd or FakeCmd()
    tools = AgentTools(command_runner=runner, project_root=".",
                       command_policy=policy)
    return tools, runner


POLICY = CommandPolicy(
    enforce=True,
    allowlist={
        "test": "python -m pytest -q",
        "lint": "python -m mypy .",
    },
)


# ═══════════════════ allowlist matrix ═══════════════════

class TestAllowlistMatrix:
    def test_literal_allowed_command_executes(self):
        tools, runner = _tools(POLICY)
        out = tools.tool_run_command("python -m pytest -q")
        assert runner.calls == ["python -m pytest -q"]
        assert "exit code: 0" in out

    def test_entry_name_resolves_to_command(self):
        tools, runner = _tools(POLICY)
        out = tools.tool_run_command("test")
        assert runner.calls == ["python -m pytest -q"]
        assert "[allowlist: test]" in out

    def test_whitespace_normalized_before_match(self):
        tools, runner = _tools(POLICY)
        tools.tool_run_command("  python   -m  pytest   -q ")
        assert runner.calls == ["python -m pytest -q"]

    def test_non_allowlisted_rejected_never_executed(self):
        tools, runner = _tools(POLICY)
        out = tools.tool_run_command("rm -rf /")
        assert runner.calls == []          # لا تنفيذ صامت أبدًا
        assert out.startswith("❌")
        assert "rm -rf /" in out           # الرفض يذكر الأمر المطلوب
        assert "command_allowlist" in out  # ويوجه للمصدر

    def test_prefix_of_allowed_command_is_rejected(self):
        # أمر يبدأ بنص مسموح ليس مسموحًا — مطابقة تامة لا بادئة
        tools, runner = _tools(POLICY)
        out = tools.tool_run_command("python -m pytest -q --deadly-flag")
        assert runner.calls == []
        assert out.startswith("❌")

    def test_rejection_is_logged(self, caplog):
        tools, _ = _tools(POLICY)
        with caplog.at_level(logging.WARNING, logger="chain.agent_tools"):
            tools.tool_run_command("curl http://evil.example")
        assert any("REJECTED" in r.message for r in caplog.records)

    def test_rejection_lists_available_entries(self):
        tools, _ = _tools(POLICY)
        out = tools.tool_run_command("whatever")
        assert "test" in out and "lint" in out

    def test_enforced_empty_allowlist_rejects_everything(self):
        tools, runner = _tools(CommandPolicy(enforce=True, allowlist={}))
        out = tools.tool_run_command("echo hi")
        assert runner.calls == []
        assert out.startswith("❌")

    def test_legacy_mode_no_enforcement(self):
        # بلا سياسة (قسم config غائب) — سلوك ما قبل T-058: التنفيذ يمر
        # (بوابة الموافقة T-013 تبقى الحاكم في المسار الحقيقي)
        tools, runner = _tools(policy=None)
        out = tools.tool_run_command("echo anything")
        assert runner.calls == ["echo anything"]
        assert "exit code: 0" in out

    def test_no_runner_available(self):
        tools = AgentTools(command_runner=None, project_root=".",
                           command_policy=POLICY)
        assert "غير متاح" in tools.tool_run_command("test")


# ═══════════════════ command_policy_from ═══════════════════

class TestPolicyFromConfig:
    def test_valid_section(self):
        cfg = {"agent": {
            "command_allowlist": {"test": "pytest -q", "build": "make"},
            "command_timeout_seconds": 30,
            "command_output_max_chars": 500,
        }}
        p = command_policy_from(cfg)
        assert p.enforce is True
        assert p.allowlist == {"test": "pytest -q", "build": "make"}
        assert p.timeout_seconds == 30.0
        assert p.output_max_chars == 500

    def test_missing_section_means_legacy(self):
        for cfg in (None, {}, {"agent": {}}, {"agent": None}):
            p = command_policy_from(cfg)
            assert p.enforce is False

    def test_garbage_types_tolerated(self):
        p = command_policy_from({"agent": "not-a-dict"})
        assert p.enforce is False
        p2 = command_policy_from({"agent": {"command_allowlist": ["a", "b"]}})
        assert p2.enforce is False

    def test_non_string_and_empty_entries_dropped(self):
        p = command_policy_from({"agent": {"command_allowlist": {
            "ok": "pytest", "bad": 42, "empty": "  ", 7: "x",
        }}})
        assert p.enforce is True
        assert p.allowlist == {"ok": "pytest"}

    def test_bad_timeout_and_cap_fall_back(self):
        p = command_policy_from({"agent": {
            "command_allowlist": {"t": "x"},
            "command_timeout_seconds": -5,
            "command_output_max_chars": "big",
        }})
        assert p.timeout_seconds == DEFAULT_COMMAND_TIMEOUT
        assert p.output_max_chars == DEFAULT_OUTPUT_MAX_CHARS

    def test_bool_not_accepted_as_numeric(self):
        p = command_policy_from({"agent": {
            "command_allowlist": {"t": "x"},
            "command_timeout_seconds": True,
            "command_output_max_chars": True,
        }})
        assert p.timeout_seconds == DEFAULT_COMMAND_TIMEOUT
        assert p.output_max_chars == DEFAULT_OUTPUT_MAX_CHARS


# ═══════════════════ timeout + ticket cancellation ═══════════════════

HUNG = CommandPolicy(enforce=True, allowlist={"hang": "sleep-forever"},
                     timeout_seconds=0.2)


class TestTimeoutAndCancel:
    def test_hung_command_times_out(self):
        # FakeCmd ينام 5 ثوانٍ — السياسة مهلتها 0.2s + سماحية 2s
        tools, _ = _tools(HUNG, FakeCmd(delay=5.0))
        start = time.monotonic()
        out = tools.tool_run_command("hang")
        elapsed = time.monotonic() - start
        assert out.startswith("❌")
        assert "مهلة" in out
        assert elapsed < 4.0  # عاد قبل انتهاء الأمر الحقيقي (5s)

    def test_ticket_cancellation_unblocks_hung_command(self):
        registry = ExecutionRegistry()
        ticket = registry.register("agent", "proj-t058")
        tools, _ = _tools(
            CommandPolicy(enforce=True,
                          allowlist={"hang": "sleep-forever"},
                          timeout_seconds=30.0),  # مهلة طويلة — الإلغاء أولاً
            FakeCmd(delay=5.0),
        )
        tools.run_ticket = ticket

        timer = threading.Timer(0.3, lambda: ticket.cancel("user stop"))
        timer.start()
        start = time.monotonic()
        out = tools.tool_run_command("hang")
        elapsed = time.monotonic() - start
        timer.cancel()

        assert out.startswith("❌")
        assert "أُلغي" in out
        assert elapsed < 3.0  # الإلغاء لوحظ فورًا، لا انتظار المهلة/الأمر

    def test_cancelled_before_start_short_circuits(self):
        registry = ExecutionRegistry()
        ticket = registry.register("agent", "proj-t058-pre")
        ticket.cancel("early")
        tools, _ = _tools(HUNG, FakeCmd(delay=5.0))
        tools.run_ticket = ticket
        start = time.monotonic()
        out = tools.tool_run_command("hang")
        assert out.startswith("❌")
        assert time.monotonic() - start < 3.0

    def test_no_ticket_means_timeout_still_applies(self):
        tools, _ = _tools(HUNG, FakeCmd(delay=5.0))
        assert tools.run_ticket is None
        out = tools.tool_run_command("hang")
        assert "مهلة" in out


# ═══════════════════ output capture + size cap ═══════════════════

class TestOutputCapture:
    def test_stdout_stderr_and_exit_code_reported(self):
        fake = FakeCmd(result={"success": False, "output": "line-out",
                               "error": "line-err", "code": 7})
        tools, _ = _tools(CommandPolicy(enforce=True,
                                        allowlist={"t": "cmd"}), fake)
        out = tools.tool_run_command("t")
        assert "exit code: 7" in out
        assert "line-out" in out
        assert "line-err" in out
        assert out.startswith("❌")  # فشل = مُعلَّم صراحة

    def test_success_report_without_failure_marker(self):
        fake = FakeCmd(result={"success": True, "output": "all good",
                               "error": "", "code": 0})
        tools, _ = _tools(CommandPolicy(enforce=True,
                                        allowlist={"t": "cmd"}), fake)
        out = tools.tool_run_command("t")
        assert not out.startswith("❌")
        assert "all good" in out

    def test_large_output_is_capped_with_marker(self):
        big = "x" * 10_000
        fake = FakeCmd(result={"success": True, "output": big,
                               "error": "", "code": 0})
        policy = CommandPolicy(enforce=True, allowlist={"t": "cmd"},
                               output_max_chars=100)
        tools, _ = _tools(policy, fake)
        out = tools.tool_run_command("t")
        assert "اقتُطع" in out
        assert "10000" in out            # الحجم الأصلي مذكور
        assert len(out) < 1_000          # التقرير نفسه صغير

    def test_each_stream_capped_independently(self):
        fake = FakeCmd(result={"success": False, "output": "o" * 300,
                               "error": "e" * 300, "code": 1})
        policy = CommandPolicy(enforce=True, allowlist={"t": "cmd"},
                               output_max_chars=50)
        tools, _ = _tools(policy, fake)
        out = tools.tool_run_command("t")
        assert out.count("اقتُطع") == 2

    def test_empty_output_reported_explicitly(self):
        fake = FakeCmd(result={"success": True, "output": "",
                               "error": "", "code": 0})
        tools, _ = _tools(CommandPolicy(enforce=True,
                                        allowlist={"t": "cmd"}), fake)
        assert "لا مخرجات" in tools.tool_run_command("t")


# ═══════════════════ real CommandRunner integration (fast) ═══════════════════

class TestRealRunner:
    def test_real_command_captured_end_to_end(self, tmp_path):
        from actions.command_runner import CommandRunner
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True)
        policy = CommandPolicy(
            enforce=True,
            allowlist={"hello": 'python -c "print(42)"'},
            timeout_seconds=20.0,
        )
        tools = AgentTools(command_runner=runner,
                           project_root=str(tmp_path),
                           command_policy=policy)
        out = tools.tool_run_command("hello")
        assert "exit code: 0" in out
        assert "42" in out
