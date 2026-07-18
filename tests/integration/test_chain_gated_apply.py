# -*- coding: utf-8 -*-
"""T-012 (R-104): chain apply goes through ApprovalGate — end of silent auto-apply.

Approval matrix E2E against a real ChainBridge + ActionApplier + FileManager
on a tmp project (FakeProvider supplies the AI output):

- auto mode (whitelisted)      → file written, no prompt
- interactive + user accepts   → file written after chain_approval_request frame
- interactive + user rejects   → zero writes
- deny mode                    → zero writes
- interactive + timeout        → zero writes
- crash mid-chain              → zero writes (apply unreachable from failure)
- no gate wired                → stage-only (zero writes) — no silent fallback

Plus the structural guarantee: no `apply_step` reachable from `finally` (grep).
"""
from __future__ import annotations

import pathlib
import threading
import time

import pytest

from actions.file_manager import FileManager
from actions.response_parser import ResponseParser
from chain.action_applier import ActionApplier
from chain.bridge import ChainBridge
from core.approval import ApprovalGate
from tests.fakes.fake_provider import FakeProvider

# رد AI يحتوي فعل كتابة ملف واحد — صيغة ```FILE: التي يفهمها ResponseParser
AI_RESPONSE_WITH_FILE = (
    "تم التنفيذ:\n"
    "```FILE: hello.txt\n"
    "gated content\n"
    "```\n"
)

JOIN_TIMEOUT = 10.0


class FrameSink:
    """يجمع إطارات WS ويوفر انتظار إطار بنوع معيّن."""

    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def wait_for(self, frame_type: str, timeout: float = 5.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for f in self.frames:
                    if f.get("type") == frame_type:
                        return f
            time.sleep(0.01)
        return None

    def of_type(self, frame_type: str) -> list[dict]:
        with self._lock:
            return [f for f in self.frames if f.get("type") == frame_type]


def _make_bridge(tmp_path: pathlib.Path, gate: ApprovalGate | None,
                 provider: FakeProvider | None = None) -> tuple[ChainBridge, pathlib.Path]:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    fm = FileManager(str(project))
    applier = ActionApplier(parser=ResponseParser(), file_manager=fm,
                            auto_backup=False)
    bridge = ChainBridge(
        provider=provider or FakeProvider(responses=[AI_RESPONSE_WITH_FILE]),
        project_root=str(project),
        runs_dir=tmp_path / "runs",
        action_applier=applier,
        approval_gate=gate,
    )
    return bridge, project


def _run_and_join(bridge: ChainBridge, sink: FrameSink) -> str:
    run_id = bridge.start_chain(sink, "اكتب ملف hello",
                                force_strategy="direct")
    assert run_id
    thread = bridge._active_thread
    assert thread is not None
    thread.join(timeout=JOIN_TIMEOUT)
    assert not thread.is_alive(), "chain thread لم ينتهِ في المهلة"
    return run_id


# ═══════════════ auto mode ═══════════════

def test_auto_mode_writes_without_prompt(tmp_path):
    gate = ApprovalGate(mode="auto", auto_whitelist={"write", "edit", "command"})
    bridge, project = _make_bridge(tmp_path, gate)
    sink = FrameSink()
    _run_and_join(bridge, sink)

    assert (project / "hello.txt").read_text(encoding="utf-8").strip() == "gated content"
    assert sink.of_type("chain_approval_request") == []          # لا سؤال
    verdicts = sink.of_type("chain_approval_verdict")
    assert len(verdicts) == 1 and verdicts[0]["approved"] is True
    assert verdicts[0]["reason"] == "auto_whitelist"
    assert len(sink.of_type("chain_apply_result")) == 1


# ═══════════════ interactive: accept / reject ═══════════════

def test_interactive_accept_writes_after_frame(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=8.0)
    bridge, project = _make_bridge(tmp_path, gate)
    sink = FrameSink()

    def approver():
        frame = sink.wait_for("chain_approval_request", timeout=8.0)
        assert frame is not None
        # قبل الموافقة: لا كتابة بعد
        assert not (project / "hello.txt").exists()
        assert bridge.resolve_approval(frame["request_id"], True,
                                       payload_hash=frame["payload_hash"])

    t = threading.Thread(target=approver)
    t.start()
    _run_and_join(bridge, sink)
    t.join(timeout=5.0)

    assert (project / "hello.txt").exists()
    v = sink.of_type("chain_approval_verdict")[0]
    assert v["approved"] is True and v["reason"] == "user_approved"


def test_interactive_reject_zero_writes(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=8.0)
    bridge, project = _make_bridge(tmp_path, gate)
    sink = FrameSink()

    def rejecter():
        frame = sink.wait_for("chain_approval_request", timeout=8.0)
        assert frame is not None
        bridge.resolve_approval(frame["request_id"], False,
                                payload_hash=frame["payload_hash"])

    t = threading.Thread(target=rejecter)
    t.start()
    _run_and_join(bridge, sink)
    t.join(timeout=5.0)

    assert not (project / "hello.txt").exists()
    v = sink.of_type("chain_approval_verdict")[0]
    assert v["approved"] is False and v["reason"] == "user_denied"
    assert sink.of_type("chain_apply_result") == []


# ═══════════════ deny / timeout ═══════════════

def test_deny_mode_zero_writes(tmp_path):
    gate = ApprovalGate(mode="deny")
    bridge, project = _make_bridge(tmp_path, gate)
    sink = FrameSink()
    _run_and_join(bridge, sink)

    assert not (project / "hello.txt").exists()
    v = sink.of_type("chain_approval_verdict")[0]
    assert v["approved"] is False and v["reason"] == "deny_mode"


def test_interactive_timeout_zero_writes(tmp_path):
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.2)
    bridge, project = _make_bridge(tmp_path, gate)
    sink = FrameSink()
    _run_and_join(bridge, sink)

    assert not (project / "hello.txt").exists()
    v = sink.of_type("chain_approval_verdict")[0]
    assert v["approved"] is False and v["reason"] == "timeout"


# ═══════════════ crash mid-chain ⇒ zero writes ═══════════════

def test_crash_mid_chain_leaves_tree_untouched(tmp_path):
    """المزود يفشل دائمًا ⇒ الركض failed ⇒ apply غير قابل للوصول."""
    provider = FakeProvider()
    provider.fail_always = RuntimeError("provider dead")
    # بوابة auto كاملة الصلاحية — حتى مع أوسع بوابة، الفشل = صفر كتابات
    gate = ApprovalGate(mode="auto", auto_whitelist={"write", "edit", "command"})
    bridge, project = _make_bridge(tmp_path, gate, provider=provider)
    sink = FrameSink()
    _run_and_join(bridge, sink)

    assert list(project.iterdir()) == []                # الشجرة لم تُمس
    assert sink.of_type("chain_approval_verdict") == [] # البوابة لم تُسأل أصلاً
    assert sink.of_type("chain_apply_result") == []


# ═══════════════ no gate ⇒ stage-only (no silent fallback) ═══════════════

def test_no_gate_stages_only_never_writes(tmp_path):
    bridge, project = _make_bridge(tmp_path, gate=None)
    sink = FrameSink()
    _run_and_join(bridge, sink)

    assert not (project / "hello.txt").exists()
    staged = sink.of_type("chain_actions_staged")
    assert len(staged) == 1
    assert staged[0]["reason"] == "no_approval_gate"
    assert staged[0]["actions_count"] == 1


# ═══════════════ structural: apply unreachable from finally ═══════════════

def test_no_apply_in_finally_block():
    """يضمن (بالنص) أن finally في _run_chain لا يحتوي أي apply."""
    src = pathlib.Path(__file__).parents[2].joinpath("chain", "bridge.py") \
        .read_text(encoding="utf-8")
    # اعزل جسد _run_chain
    start = src.index("def _run_chain():")
    end = src.index("thread = threading.Thread", start)
    body = src[start:end]
    fin = body.index("finally:")
    finally_part = body[fin:]
    assert "apply_step" not in finally_part
    assert "_gated_apply" not in finally_part
    # والتطبيق موجود في مسار النجاح (else) فقط
    else_part = body[body.index("else:"):fin]
    assert "_gated_apply" in else_part
