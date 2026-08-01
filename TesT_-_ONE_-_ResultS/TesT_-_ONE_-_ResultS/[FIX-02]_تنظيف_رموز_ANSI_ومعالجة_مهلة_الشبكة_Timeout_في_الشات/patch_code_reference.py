# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
 🧪 FIX-02: كود الفلترة المرجعي الكامل لرموز ANSI والـ Circuit Breaker
 
 يحتوي هذا الملف على الأكواد التنفيذية المعتمدة من فيب كودج لـ:
 1. دالة strip_ansi في _WSAdapter داخل server.py
 2. فئة ProviderCircuitBreaker لتدبير التبديل المرن للمزودين (Half-Open logic)
═══════════════════════════════════════════════════════
"""

import re
import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any


# ── 1. باتش الـ ANSI Strip Guard في server.py ──

_ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
_USER_FACING_TEXT_KEYS = ("text", "message", "summary", "error")

def strip_ansi(text: Any) -> Any:
    """TSK-502: تنظيف أي تسلسلات ANSI ألوان وتنسيق تيرمنال من النصوص"""
    if not isinstance(text, str):
        return text
    return _ANSI_ESCAPE_RE.sub('', text)

def strip_ansi_from_frame(frame: dict) -> dict:
    """تنظيف الحقول النصية المتجهة للواجهة فقط"""
    for key in _USER_FACING_TEXT_KEYS:
        if key in frame and isinstance(frame[key], str):
            frame[key] = strip_ansi(frame[key])
    return frame


# ── 2. باتش الـ Circuit Breaker لشبكة أمان المزودين (providers/circuit_breaker.py) ──

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class BreakerConfig:
    failure_threshold: int = 2            # عتبة أقصى فشل قبل فتح الدائرة
    cooldown_seconds: float = 120.0       # مدة الانتظار بالثواني قبل إعادة التجربة
    cooldown_backoff_factor: float = 1.5  # مضاعفة التهدئة في حالة التكرار
    max_cooldown_seconds: float = 900.0   # سقف أقصى للانتظار (15 دقيقة)


@dataclass
class _BreakerState:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: float = 0.0
    current_cooldown: float = 0.0


class ProviderCircuitBreaker:
    """Circuit Breaker موحد ومحمي بـ Lock لكل مزود"""

    def __init__(self, config: BreakerConfig | None = None):
        self._config = config or BreakerConfig()
        self._states: dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def _get_state(self, provider_name: str) -> _BreakerState:
        if provider_name not in self._states:
            self._states[provider_name] = _BreakerState()
        return self._states[provider_name]

    def can_attempt(self, provider_name: str) -> bool:
        """فحص ما إذا كان مسموحاً للمزود بإجراء محاولة طلب جديدة"""
        with self._lock:
            st = self._get_state(provider_name)
            if st.state == CircuitState.CLOSED:
                return True
            if st.state == CircuitState.OPEN:
                elapsed = time.monotonic() - st.opened_at
                if elapsed >= st.current_cooldown:
                    st.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN

    def mark_success(self, provider_name: str) -> None:
        """تأكيد النجاح وتصفير العداد ليعود للحالة المغلقة CLOSED"""
        with self._lock:
            st = self._get_state(provider_name)
            st.state = CircuitState.CLOSED
            st.consecutive_failures = 0
            st.current_cooldown = 0.0

    def mark_failed(self, provider_name: str) -> None:
        """تسجيل فشل وزيادة العداد أو فتح الدائرة حالة تجاوز العتبة"""
        with self._lock:
            st = self._get_state(provider_name)
            st.consecutive_failures += 1

            if st.state == CircuitState.HALF_OPEN:
                new_cooldown = (st.current_cooldown or self._config.cooldown_seconds) * self._config.cooldown_backoff_factor
                st.current_cooldown = min(new_cooldown, self._config.max_cooldown_seconds)
                st.state = CircuitState.OPEN
                st.opened_at = time.monotonic()
                return

            if st.consecutive_failures >= self._config.failure_threshold:
                st.state = CircuitState.OPEN
                st.opened_at = time.monotonic()
                st.current_cooldown = self._config.cooldown_seconds

    def status(self, provider_name: str) -> dict:
        """تقرير تشخيصي لحالة المزود"""
        with self._lock:
            st = self._get_state(provider_name)
            remaining = 0.0
            if st.state == CircuitState.OPEN:
                remaining = max(0.0, st.current_cooldown - (time.monotonic() - st.opened_at))
            return {
                "provider": provider_name,
                "state": st.state.value,
                "consecutive_failures": st.consecutive_failures,
                "cooldown_remaining_seconds": round(remaining, 1),
            }
