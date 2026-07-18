# -*- coding: utf-8 -*-
"""T-009 (R-103): DelegateBridge honors the provider send() contract.

`send(prompt: str, ...)` used to receive `list[Message]` at the three
delegate call sites (write_brief / dispatch / review) — a latent crash on
any conforming provider. Now every site renders via
`DelegateBridge._to_prompt_history()` first.

A strict-typed FakeProvider subclass (raises TypeError on non-str prompt)
proves the fix end-to-end; the rendering format is pinned as golden.
"""
import pytest

from providers.base import Message
from chain.delegate import DelegateBridge
from tests.fakes.fake_provider import FakeProvider


class StrictFakeProvider(FakeProvider):
    """Contract-conforming provider: rejects non-str prompts loudly."""

    def send(self, prompt, history=None, system_prompt=""):
        if not isinstance(prompt, str):
            raise TypeError(
                f"send() contract violation: prompt must be str, "
                f"got {type(prompt).__name__}"
            )
        return super().send(prompt, history=history, system_prompt=system_prompt)


# ── rendering golden ───────────────────────────────────────────────

def test_single_user_message_renders_verbatim():
    out = DelegateBridge._to_prompt_history(
        [Message(role="user", content="hello world")])
    assert out == "hello world"


def test_multi_message_golden():
    msgs = [
        Message(role="user", content="سؤال"),
        Message(role="assistant", content="جواب"),
        Message(role="user", content="متابعة"),
    ]
    golden = "[USER]:\nسؤال\n\n[ASSISTANT]:\nجواب\n\n[USER]:\nمتابعة"
    assert DelegateBridge._to_prompt_history(msgs) == golden


def test_empty_and_missing_role():
    assert DelegateBridge._to_prompt_history([]) == ""
    m1 = Message(role="", content="x")
    m2 = Message(role="assistant", content="y")
    out = DelegateBridge._to_prompt_history([m1, m2])
    assert out.startswith("[USER]:\nx")  # empty role -> USER


# ── delegate integration vs strict provider ───────────────────────

def _strict_bridge(responses):
    return DelegateBridge(StrictFakeProvider(responses=responses))


def test_write_brief_passes_str_prompt():
    bridge = _strict_bridge(["<brief>planned</brief>"])
    brief = bridge.write_brief("build a page", {"a.py": "print(1)"})
    assert brief.raw_brief == "<brief>planned</brief>"
    call = bridge._provider.calls[0]
    assert isinstance(call.prompt, str)
    assert "build a page" in call.prompt


def test_dispatch_passes_str_prompt():
    bridge = _strict_bridge(["<brief>b</brief>", "IMPLEMENTED"])
    brief = bridge.write_brief("task", {})
    result = bridge.dispatch(brief)
    assert result.response == "IMPLEMENTED"
    assert all(isinstance(c.prompt, str) for c in bridge._provider.calls)


def test_review_passes_str_prompt():
    bridge = _strict_bridge(["<brief>b</brief>", "IMPL", "VERDICT: APPROVE"])
    brief = bridge.write_brief("task", {})
    result = bridge.dispatch(brief)
    bridge.review(brief, result)  # must not raise TypeError
    assert len(bridge._provider.calls) == 3
    assert all(isinstance(c.prompt, str) for c in bridge._provider.calls)
