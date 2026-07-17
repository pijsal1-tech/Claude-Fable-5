# -*- coding: utf-8 -*-
"""FakeProvider (T-002): deterministic, scriptable provider for tests.

Conforms to providers.base.BaseProvider:
- Scriptable responses (queue or callable)
- Full call recording (prompt, history, system_prompt, timestamp)
- Injectable failures (exception instances) and latency
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Generator

from providers.base import BaseProvider, Message, ProviderConfig


@dataclass
class RecordedCall:
    """One recorded send()/stream() invocation."""
    method: str                     # "send" | "stream"
    prompt: str
    history: list[Message] | None
    system_prompt: str
    ts: float = field(default_factory=time.monotonic)


class FakeProvider(BaseProvider):
    """Deterministic provider double.

    Usage:
        fp = FakeProvider(responses=["first reply", "second reply"])
        fp.send("hi")                      -> "first reply"
        fp.send("again")                   -> "second reply"
        fp.send("more")                    -> default_response (queue empty)

        # dynamic responses:
        fp = FakeProvider(responder=lambda prompt, history, sys: f"echo:{prompt}")

        # failure injection:
        fp.fail_next(TimeoutError("boom"))       # next call raises
        fp.fail_always = ValueError("dead")      # every call raises

        # latency injection:
        fp.latency_s = 0.05
    """

    name = "fake"
    description = "Deterministic test provider (T-002)"

    def __init__(
        self,
        responses: list[str] | None = None,
        responder: Callable[[str, list[Message] | None, str], str] | None = None,
        config: ProviderConfig | None = None,
        default_response: str = "FAKE_DEFAULT_RESPONSE",
        available: bool = True,
    ):
        super().__init__(config)
        self._queue: list[str] = list(responses or [])
        self._responder = responder
        self.default_response = default_response
        self._available = available

        self.calls: list[RecordedCall] = []
        self.latency_s: float = 0.0
        self.fail_always: Exception | None = None
        self._fail_next: list[Exception] = []

    # ── scripting helpers ────────────────────────────────
    def queue_response(self, text: str) -> "FakeProvider":
        self._queue.append(text)
        return self

    def fail_next(self, exc: Exception) -> "FakeProvider":
        """Raise `exc` on the next call only (FIFO if called repeatedly)."""
        self._fail_next.append(exc)
        return self

    def reset(self) -> None:
        self.calls.clear()
        self._queue.clear()
        self._fail_next.clear()
        self.fail_always = None
        self.latency_s = 0.0

    # ── assertion helpers ────────────────────────────────
    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def last_call(self) -> RecordedCall | None:
        return self.calls[-1] if self.calls else None

    # ── internals ────────────────────────────────────────
    def _next_text(self, prompt: str, history: list[Message] | None,
                   system_prompt: str) -> str:
        if self.latency_s:
            time.sleep(self.latency_s)
        if self.fail_always is not None:
            raise self.fail_always
        if self._fail_next:
            raise self._fail_next.pop(0)
        if self._responder is not None:
            return self._responder(prompt, history, system_prompt)
        if self._queue:
            return self._queue.pop(0)
        return self.default_response

    # ── BaseProvider contract ────────────────────────────
    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        self.calls.append(RecordedCall("send", prompt, history, system_prompt))
        return self._next_text(prompt, history, system_prompt)

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        self.calls.append(RecordedCall("stream", prompt, history, system_prompt))
        text = self._next_text(prompt, history, system_prompt)
        # yield in small chunks to exercise streaming consumers
        chunk = 8
        for i in range(0, len(text), chunk):
            yield text[i:i + chunk]

    def is_available(self) -> bool:
        return self._available
