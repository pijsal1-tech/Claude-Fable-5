# -*- coding: utf-8 -*-
"""T-015 (R-105): tickets in all three modes — cancellation reaches the loops.

Cancel matrix (Acceptance Criteria):
- chain:    cancel mid-run → stops before next step; run `cancelled`;
            ticket finished `cancelled`; zero applies.
- agent:    cancel via ticket → loop exits at iteration checkpoint;
            ticket finished `cancelled`.
- delegate: cancel between stages → run ends `cancelled`, **no Land**;
            ticket finished `cancelled` (delegate is cancellable at last).

Regression: uncancelled runs finish their tickets `completed` and behave
identically. Structural: core/active_run.py deleted.
"""
from __future__ import annotations

import pathlib
import threading
import time

import pytest

from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import AgentTools
from chain.bridge import ChainBridge
from chain.delegate import DelegateBridge
from core.execution import ExecutionRegistry
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 10.0


# ═══════════════════════ chain: cancel mid-run ═══════════════════════

def _make_bridge(tmp_path, provider):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return ChainBridge(
        provider=provider,
        project_root=str(project),
        runs_dir=tmp_path / "runs",
    )


def test_chain_ticket_cancel_stops_before_next_step(tmp_path):
    """إلغاء التذكرة أثناء الخطوة الأولى ⇒ لا خطوة ثانية، run=cancelled."""
    reg = ExecutionRegistry()
    ticket = reg.register("chain")
    release = threading.Event()

    def slow_responder(prompt, history, sys):
        release.wait(timeout=5)     # الخطوة 1 معلقة حتى نلغي
        return "step response"

    provider = FakeProvider(responder=slow_responder)
    bridge = _make_bridge(tmp_path, provider)

    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, "اعمل تحليل وخطة كاملة",
                                force_strategy="full_chain", ticket=ticket)
    assert run_id
    time.sleep(0.2)                  # الخطوة 1 بدأت (معلقة في المزود)

    ticket.cancel("user clicked stop")
    release.set()                    # الخطوة 1 ترجع — التفتيش قبل التالية

    bridge._active_thread.join(timeout=JOIN_TIMEOUT)
    assert not bridge._active_thread.is_alive()

    assert ticket.state == "cancelled"           # bridge finally finished it
    # الخطوة الثانية لم تُنفذ أبدًا: استدعاء مزوّد واحد فقط
    assert len(provider.calls) == 1
    assert any(f.get("type") == "chain_cancelled" for f in frames)


def test_chain_uncancelled_finishes_completed(tmp_path):
    """Regression: بدون إلغاء — التذكرة تنتهي completed والسلوك كما هو."""
    reg = ExecutionRegistry()
    ticket = reg.register("chain")
    bridge = _make_bridge(tmp_path, FakeProvider(responses=["ok done"]))

    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, "اكتب سطر",
                                force_strategy="direct", ticket=ticket)
    assert run_id
    bridge._active_thread.join(timeout=JOIN_TIMEOUT)

    assert ticket.state == "completed"
    assert reg.list_active() == []
    assert any(f.get("type") == "chain_finished" for f in frames)


def test_chain_without_ticket_unchanged(tmp_path):
    """Regression: عدم تمرير تذكرة = المسار القديم بلا أي تغيير سلوك."""
    bridge = _make_bridge(tmp_path, FakeProvider(responses=["ok"]))
    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, "اكتب سطر",
                                force_strategy="direct")
    assert run_id
    bridge._active_thread.join(timeout=JOIN_TIMEOUT)
    assert any(f.get("type") == "chain_finished" for f in frames)


# ═══════════════════════ agent: ticket cancel ═══════════════════════

AGENT_TOOL_CALL = (
    "سأقرأ الملف:\n"
    "```TOOL: read_file\n"
    "path: notes.txt\n"
    "```\n"
)


def _make_agent(tmp_path, provider):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "notes.txt").write_text("hello", encoding="utf-8")
    tools = AgentTools(
        file_manager=FileManager(str(project)),
        command_runner=CommandRunner(cwd=str(project), auto_approve=True),
        project_root=str(project),
    )
    return AgentLoop(
        tools=tools,
        send_fn=lambda p, h, s: provider.send(p, h, s),
        ws_send_fn=lambda m: None,
        max_iterations=4,
    )


def test_agent_ticket_cancel_exits_at_iteration_boundary(tmp_path):
    """إلغاء التذكرة بعد الرد الأول ⇒ الحلقة تخرج عند رأس الدورة التالية."""
    reg = ExecutionRegistry()
    ticket = reg.register("agent")

    def responder(prompt, history, sys):
        ticket.cancel("stop")        # يُلغى أثناء أول استدعاء
        return AGENT_TOOL_CALL       # يطلب أداة — لكن الدورة التالية تُفحص أولاً

    loop = _make_agent(tmp_path, FakeProvider(responder=responder))
    result = loop.run("اقرأ الملف", ticket=ticket)

    assert "إلغاء" in result         # خرجت من نقطة التفتيش
    assert ticket.state == "cancelled"


def test_agent_uncancelled_finishes_completed(tmp_path):
    reg = ExecutionRegistry()
    ticket = reg.register("agent")
    loop = _make_agent(tmp_path, FakeProvider(responses=["الرد النهائي"]))
    result = loop.run("سؤال بسيط", ticket=ticket)
    assert result == "الرد النهائي"
    assert ticket.state == "completed"
    assert reg.list_active() == []


# ═══════════════════ delegate: cancel between stages ═══════════════════

BRIEF_RESPONSE = "<brief>planned work</brief>"
IMPL_RESPONSE = "done implementation"
REVIEW_APPROVE = "[VERDICT]: APPROVE\n[SUMMARY]: جيد"


def test_delegate_cancel_between_stages_no_land(tmp_path):
    """معيار قبول R-105: إلغاء بين المراحل ⇒ run=cancelled ولا Land أبدًا."""
    reg = ExecutionRegistry()
    ticket = reg.register("delegate")

    calls = {"n": 0}

    def responder(prompt, history, sys):
        calls["n"] += 1
        if calls["n"] == 1:          # مرحلة Brief
            ticket.cancel("stop delegation")
            return BRIEF_RESPONSE
        return IMPL_RESPONSE         # يجب ألا نصل هنا

    bridge = DelegateBridge(FakeProvider(responder=responder))
    events: list[str] = []
    run = bridge.run_delegation(
        "نفذ مهمة", {"a.py": "x=1"},
        on_event=lambda et, ed: events.append(et), ticket=ticket)

    assert run.status == "cancelled"
    assert ticket.state == "cancelled"
    assert calls["n"] == 1           # توقف عند نقطة تفتيش Implement
    assert "delegate_cancelled" in events
    assert "delegate_landed" not in events
    # Land مرفوض بعد الإلغاء (ليس waiting_approval)
    assert bridge.land() is False


def test_delegate_uncancelled_reaches_waiting_approval_then_land(tmp_path):
    """Regression: بدون إلغاء — الدورة الكاملة تعمل والتذكرة تُنهى عند land."""
    reg = ExecutionRegistry()
    ticket = reg.register("delegate")
    bridge = DelegateBridge(FakeProvider(
        responses=[BRIEF_RESPONSE, IMPL_RESPONSE, REVIEW_APPROVE]))

    run = bridge.run_delegation("نفذ مهمة", {"a.py": "x=1"}, ticket=ticket)
    assert run.status == "waiting_approval"
    assert ticket.state == "running"           # المستخدم لم يحسم بعد — بصدق

    assert bridge.land() is True
    assert run.status == "landed"
    assert ticket.state == "completed"
    assert reg.list_active() == []


def test_delegate_reject_finishes_ticket(tmp_path):
    reg = ExecutionRegistry()
    ticket = reg.register("delegate")
    bridge = DelegateBridge(FakeProvider(
        responses=[BRIEF_RESPONSE, IMPL_RESPONSE, REVIEW_APPROVE]))
    run = bridge.run_delegation("نفذ", {"a.py": "x=1"}, ticket=ticket)
    assert run.status == "waiting_approval"
    assert bridge.reject("مش عاجبني") is True
    assert ticket.state == "completed"
    assert reg.list_active() == []


# ═══════════════════════ structural ═══════════════════════

def test_active_run_holder_deleted():
    """T-015: حذف ActiveRunHolder — الملف نفسه لم يعد موجودًا."""
    root = pathlib.Path(__file__).parents[2]
    assert not (root / "core" / "active_run.py").exists()
    # ولا أي استيراد له في server.py
    src = (root / "server.py").read_text(encoding="utf-8")
    assert "from core.active_run import" not in src
    assert "execution_registry" in src
