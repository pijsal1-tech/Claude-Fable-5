# -*- coding: utf-8 -*-
"""
🧪 TSK-502 / FIX-02: Unit Tests لـ strip_ansi و ProviderCircuitBreaker
"""

import time
import pytest
from patch_code_reference import (
    strip_ansi,
    strip_ansi_from_frame,
    ProviderCircuitBreaker,
    BreakerConfig,
    CircuitState,
)

# ── 1. اختبارات strip_ansi ──

def test_strips_color_codes():
    raw = "\x1b[91m❌ خطأ\x1b[0m"
    assert strip_ansi(raw) == "❌ خطأ"


def test_leaves_plain_text_untouched():
    assert strip_ansi("نص عادي بدون ألوان") == "نص عادي بدون ألوان"


def test_non_string_passthrough():
    assert strip_ansi(123) == 123
    assert strip_ansi(None) is None


def test_frame_cleaning_only_targets_known_keys():
    frame = {"type": "chunk", "text": "\x1b[91mError\x1b[0m", "other": "\x1b[91mkeep\x1b[0m"}
    cleaned = strip_ansi_from_frame(frame)
    assert cleaned["text"] == "Error"
    assert cleaned["other"] == "\x1b[91mkeep\x1b[0m"


# ── 2. اختبارات Circuit Breaker ──

def test_closed_by_default():
    cb = ProviderCircuitBreaker()
    assert cb.can_attempt("deepseek") is True


def test_opens_after_threshold_failures():
    cb = ProviderCircuitBreaker(BreakerConfig(failure_threshold=2))
    cb.mark_failed("blackbox")
    assert cb.can_attempt("blackbox") is True
    cb.mark_failed("blackbox")
    assert cb.can_attempt("blackbox") is False


def test_half_open_after_cooldown():
    cb = ProviderCircuitBreaker(BreakerConfig(failure_threshold=1, cooldown_seconds=0.05))
    cb.mark_failed("blackbox")
    assert cb.can_attempt("blackbox") is False
    time.sleep(0.06)
    assert cb.can_attempt("blackbox") is True


def test_success_resets_to_closed():
    cb = ProviderCircuitBreaker(BreakerConfig(failure_threshold=1))
    cb.mark_failed("blackbox")
    cb.mark_success("blackbox")
    st = cb._get_state("blackbox")
    assert st.state == CircuitState.CLOSED
    assert st.consecutive_failures == 0


def test_healthy_stable_provider_never_blocked():
    cb = ProviderCircuitBreaker()
    for _ in range(50):
        assert cb.can_attempt("genspark") is True
        cb.mark_success("genspark")
