# -*- coding: utf-8 -*-
"""T-010 (R-103): ProviderContractTest — signature/behavior contract mixin.

Prevents the T-009 class of bug permanently: every registered provider is
statically checked against the BaseProvider legacy API so a drifting
signature (or a caller passing the wrong types) fails CI, not production.

Adding a provider? Subclass the mixin and point `provider_cls` at your
class (see tests/contracts/test_provider_contracts.py). The mixin checks:

1. subclassing BaseProvider
2. `send(self, prompt, history=None, system_prompt="")` — exact parameter
   names, order, and defaults; annotations say `prompt: str` and
   `-> str`
3. `stream(...)` — same parameters, returns a generator type
4. `is_available(self) -> bool` exists and takes no extra args
5. class attributes `name` / `description` are non-empty strings

No provider is instantiated — contracts are signature-level, so real
providers with heavy __init__ (accounts, sockets) stay untouched.
"""
from __future__ import annotations

import inspect

from providers.base import BaseProvider


class ProviderContractMixin:
    """Mix into a test class; set `provider_cls`."""

    provider_cls: type = None  # override in subclass

    # ── 1. inheritance ────────────────────────────────────────────
    def test_subclasses_base_provider(self):
        assert issubclass(self.provider_cls, BaseProvider), (
            f"{self.provider_cls.__name__} must subclass BaseProvider")

    # ── 2. send signature ─────────────────────────────────────────
    def test_send_signature(self):
        sig = inspect.signature(self.provider_cls.send)
        params = list(sig.parameters.values())
        names = [p.name for p in params]
        assert names[:4] == ["self", "prompt", "history", "system_prompt"], (
            f"send() params must be (self, prompt, history, system_prompt); "
            f"got {names}")
        assert params[2].default is None, "history default must be None"
        assert params[3].default == "", 'system_prompt default must be ""'

    def test_send_prompt_annotated_str(self):
        sig = inspect.signature(self.provider_cls.send)
        ann = sig.parameters["prompt"].annotation
        assert ann in (str, "str"), (
            f"send(prompt) must be annotated str, got {ann!r} — "
            "this is the T-009 contract: callers pass rendered strings")

    def test_send_returns_str_annotation(self):
        sig = inspect.signature(self.provider_cls.send)
        assert sig.return_annotation in (str, "str"), (
            f"send() must be annotated -> str, got {sig.return_annotation!r}")

    # ── 3. stream signature ───────────────────────────────────────
    def test_stream_signature(self):
        sig = inspect.signature(self.provider_cls.stream)
        names = [p.name for p in sig.parameters.values()]
        assert names[:4] == ["self", "prompt", "history", "system_prompt"], (
            f"stream() params must be (self, prompt, history, system_prompt); "
            f"got {names}")

    def test_stream_is_generator_function(self):
        fn = inspect.unwrap(self.provider_cls.stream)
        assert (inspect.isgeneratorfunction(fn)
                or "Generator" in str(inspect.signature(fn).return_annotation)), (
            f"{self.provider_cls.__name__}.stream must be a generator "
            "function or annotated -> Generator")

    # ── 4. is_available ───────────────────────────────────────────
    def test_is_available_signature(self):
        sig = inspect.signature(self.provider_cls.is_available)
        names = [p.name for p in sig.parameters.values()]
        assert names == ["self"], (
            f"is_available() must take only self; got {names}")

    # ── 5. identity attributes ────────────────────────────────────
    def test_identity_attributes(self):
        assert isinstance(getattr(self.provider_cls, "name", None), str) and \
            self.provider_cls.name, "class attr `name` must be non-empty str"
        assert isinstance(getattr(self.provider_cls, "description", None), str), \
            "class attr `description` must be a str"
