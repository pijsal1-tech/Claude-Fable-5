# -*- coding: utf-8 -*-
"""T-013 (R-104): agent-mode approvals go through the same ApprovalGate.

The agent path's separate ad-hoc mechanism (threading.Event + manual
compute_payload_hash + private 60s timeout) is deleted; `_request_approval`
delegates entirely to the gate, and `approve_command` (the WS entry point)
is a thin wrapper over `gate.resolve`.

Matrix (E2E against a real AgentTools + CommandRunner on a tmp project;
FakeProvider scripts the AI turns):
- interactive + approve  → command runs, result fed to next iteration
- interactive + reject   → command NOT run
- interactive + timeout  → command NOT run
- deny mode              → command NOT run, no prompt frame needed
- auto mode (command whitelisted) → runs without prompt
- no gate wired          → auto-reject (safe default), zero execution
- stale/forged hash via approve_command → not accepted → timeout path
- cancel() while awaiting → unblocks as denial

Unified-consent proof: ONE gate instance serves chain (T-012) and agent
modes — both verdicts land in the same audit log.
"""
from __future__ import annotations

import pathlib
import threading
import time

from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import AgentTools
from core.approval import ApprovalGate, ApprovalRequest, ProposedAction
from tests.fakes.fake_provider import FakeProvider

# دور واحد: AI يطلب أمرًا ثم (بعد النتيجة) يرد نهائيًا
MARKER = "T013_MARKER"
AI_TOOL_CALL = (
    "سأنفذ الأمر المطلوب:\n"
    "```TOOL: run_command\n"
    f"command: echo {MARKER}\n"
    "reason: اختبار البوابة\n"
    "```\n"
)
AI_FINAL = "انتهيت — التنفيذ تم."


class FrameSink:
    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def wait_for(self, predicate, timeout: float = 5.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for f in self.frames:
                    if predicate(f):
                        return f
            time.sleep(0.01)
        return None

    def awaiting_approval(self) -> list[dict]:
        with self._lock:
            return [f for f in self.frames
                    if f.get("status") == "awaiting_approval"]


def _make_loop(tmp_path: pathlib.Path, gate: ApprovalGate | None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    tools = AgentTools(
        file_manager=FileManager(str(project)),
        command_runner=CommandRunner(cwd=str(project), auto_approve=True),
        project_root=str(project),
    )
    provider = FakeProvider(responses=[AI_TOOL_CALL, AI_FINAL])
    sink = FrameSink()
    loop = AgentLoop(
        tools=tools,
        send_fn=lambda p, h, s: provider.send(p, h, s),
        ws_send_fn=sink,
        max_iterations=3,
        approval_gate=gate,
    )
    return loop, sink


def _run_in_thread(loop: AgentLoop) -> tuple[threading.Thread, list]:
    result: list = []
    t = threading.Thread(target=lambda: result.append(loop.run("نفذ الأمر")))
    t.start()
    return t, result


def _command_ran(loop: AgentLoop) -> bool:
    """هل نُفذ الأمر فعلاً؟ نفحص سجل CommandRunner."""
    history = loop.tools.cmd._history
    return any(MARKER in (h.get("command") or "") for h in history)


# ═══════════════ interactive: approve / reject / timeout ═══════════════

def test_interactive_approve_runs_command(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=8.0)
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)

    frame = sink.wait_for(lambda f: f.get("status") == "awaiting_approval",
                          timeout=8.0)
    assert frame is not None
    assert not _command_ran(loop)          # لا تنفيذ قبل الموافقة
    # المسار الحقيقي: WS handler → approve_command
    loop.approve_command(True, frame["approval_request_id"],
                         frame["payload_hash"])
    t.join(timeout=10.0)
    assert not t.is_alive()
    assert _command_ran(loop)
    v = gate.audit_entries()[-1]
    assert v["approved"] is True and v["source"] == "agent"


def test_interactive_reject_blocks_command(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=8.0)
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)

    frame = sink.wait_for(lambda f: f.get("status") == "awaiting_approval",
                          timeout=8.0)
    assert frame is not None
    loop.approve_command(False, frame["approval_request_id"],
                         frame["payload_hash"])
    t.join(timeout=10.0)
    assert not _command_ran(loop)
    assert gate.audit_entries()[-1]["reason"] == "user_denied"


def test_interactive_timeout_blocks_command(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.2)
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)
    t.join(timeout=10.0)
    assert not _command_ran(loop)
    assert gate.audit_entries()[-1]["reason"] == "timeout"


# ═══════════════ deny / auto ═══════════════

def test_deny_mode_blocks_without_prompt(tmp_path):
    gate = ApprovalGate(mode="deny")
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)
    t.join(timeout=10.0)
    assert not _command_ran(loop)
    assert sink.awaiting_approval() == []   # لا إطار موافقة في وضع deny
    assert gate.audit_entries()[-1]["reason"] == "deny_mode"


def test_auto_mode_with_command_whitelisted_runs(tmp_path):
    gate = ApprovalGate(mode="auto", auto_whitelist={"command"})
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)
    t.join(timeout=10.0)
    assert _command_ran(loop)
    assert sink.awaiting_approval() == []
    assert gate.audit_entries()[-1]["reason"] == "auto_whitelist"


# ═══════════════ no gate ⇒ safe auto-reject ═══════════════

def test_no_gate_auto_rejects(tmp_path):
    loop, sink = _make_loop(tmp_path, gate=None)
    t, _ = _run_in_thread(loop)
    t.join(timeout=10.0)
    assert not _command_ran(loop)
    assert sink.awaiting_approval() == []


# ═══════════════ stale/forged + cancel ═══════════════

def test_forged_hash_not_accepted(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.5)
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)

    frame = sink.wait_for(lambda f: f.get("status") == "awaiting_approval",
                          timeout=8.0)
    assert frame is not None
    loop.approve_command(True, frame["approval_request_id"], "deadbeef")
    t.join(timeout=10.0)
    assert not _command_ran(loop)           # الرد المزوّر لم يُحتسب
    assert gate.audit_entries()[-1]["reason"] == "timeout"


def test_cancel_unblocks_pending_approval_as_denial(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=8.0)
    loop, sink = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)

    frame = sink.wait_for(lambda f: f.get("status") == "awaiting_approval",
                          timeout=8.0)
    assert frame is not None
    start = time.time()
    loop.cancel()
    t.join(timeout=10.0)
    assert not t.is_alive()
    assert time.time() - start < 5.0        # فُكّ فورًا — لم ينتظر المهلة
    assert not _command_ran(loop)


# ═══════════════ unified consent: one gate, one audit log ═══════════════

def test_single_gate_serves_agent_and_chain_audit(tmp_path):
    """نفس instance يخدم المسارين — سجل تدقيق واحد بمصدرين."""
    gate = ApprovalGate(mode="deny")

    # مسار agent
    loop, _ = _make_loop(tmp_path, gate)
    t, _ = _run_in_thread(loop)
    t.join(timeout=10.0)

    # مسار chain (طلب مباشر بنفس صيغة T-012)
    gate.request(ApprovalRequest(
        actions=[ProposedAction(kind="write", target="a.py", payload="x")],
        source="chain", run_id="run-c",
    ))

    sources = [e["source"] for e in gate.audit_entries()]
    assert "agent" in sources and "chain" in sources


# ═══════════════ structural: ad-hoc mechanism deleted ═══════════════

def test_ad_hoc_approval_machinery_deleted():
    src = pathlib.Path(__file__).parents[2].joinpath("chain", "agent_loop.py") \
        .read_text(encoding="utf-8")
    assert "_approval_event" not in src
    assert "_approval_result" not in src
    assert "compute_payload_hash" not in src   # الـ hash مسؤولية البوابة الآن
    assert "approval_gate.resolve" in src or "gate.request" in src
