# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  OpenAICompatProvider — مزود API-key عام (OpenAI-متوافق)
  TSK-735b (القرار 7 من تسلسل D-19 — قيد D-20)

  **قرار واعٍ** (المواصفة): مزود عام واحد لا فرع لكل بائع —
  بروتوكول ``/chat/completions`` القياسي يغطي OpenAI الرسمي
  وGemini (openai-compat endpoint) وDeepSeek الرسمي وollama
  وأي خادم محلي متوافق، عبر ``base_url`` فقط.

  **عقد السر (V3 §0 قيد 6)**:
  - ``api_key`` يُحقن وقت الإنشاء (من core/provider_keys —
    الملف الجانبي المُتجاهَل) ولا يُقرأ هنا من أي ملف.
  - المفتاح لا يظهر أبدًا في get_info/repr/رسائل الأخطاء —
    رسائل 401/403 تُبنى من status_code حصرًا (نص استجابة
    الخادم قد يردّد الترويسة ⇒ لا يُضمَّن).
  - غياب المفتاح حالة مشروعة: is_available()=False
    وinitialize()=False بلا استثناء (المزود يظهر في القائمة
    بـ key_configured:false — التوصيل في 735c).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from typing import Generator

import requests

from .base import (
    BaseProvider,
    Message,
    ProviderAuthenticationError,
    ProviderCapabilities,
    ProviderConfig,
    ProviderTimeoutError,
    ProviderTransientError,
    history_to_messages,
)


class OpenAICompatConfig(ProviderConfig):
    """إعدادات المزود العام.

    ``base_url`` من config.yaml (ليس سرًّا)؛ ``api_key`` يُحقن من
    القارئ الجانبي — **لا يُخزَّن في config.yaml أبدًا** (قيد D-20).
    """

    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", ""),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 2),
        )
        self.base_url: str = str(kwargs.get("base_url", "")).rstrip("/")
        self.api_key: str = kwargs.get("api_key", "") or ""
        # اسم عرض اختياري (id من providers.api_providers)
        self.provider_id: str = kwargs.get("provider_id", "openai_compat")


def _auth_error(status: int) -> ProviderAuthenticationError:
    """خطأ مصادقة مبني من status_code حصرًا — بلا أي نص من الطلب
    أو الاستجابة (قد يردّد المفتاح/الترويسة — V3 §0 قيد 6)."""
    return ProviderAuthenticationError(
        f"فشل مصادقة المزود (HTTP {status}) — راجع provider_keys.json")


class OpenAICompatProvider(BaseProvider):
    """مزود عام لأي خادم OpenAI-متوافق (``/chat/completions``)."""

    name = "openai_compat"
    description = "OpenAI-compatible API (bring your own key)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=False,
            parallel_requests=True,
            max_parallel_requests=3,
        )

    def __init__(self, config: OpenAICompatConfig | None = None):
        self.config: OpenAICompatConfig = config or OpenAICompatConfig()
        self._initialized = False

    # ── دورة الحياة ──────────────────────────────────────

    def is_available(self) -> bool:
        """جاهز فقط بمفتاح وbase_url — غياب أيهما حالة مشروعة لا خطأ."""
        return bool(self.config.api_key) and bool(self.config.base_url)

    def initialize(self) -> bool:
        """لا استثناء عند الإقلاع — الغياب يُعبَّر عنه بـ False."""
        self._initialized = self.is_available()
        return self._initialized

    def get_info(self) -> dict:
        """معلومات المزود — **بلا المفتاح** (راية key_configured فقط)."""
        return {
            "name": self.config.provider_id,
            "description": self.description,
            "model": self.config.model,
            "available": self.is_available(),
            "initialized": self._initialized,
            "key_configured": bool(self.config.api_key),
        }

    def __repr__(self) -> str:  # المفتاح لا يظهر في repr/str أبدًا
        return (f"<OpenAICompatProvider id={self.config.provider_id!r} "
                f"model={self.config.model!r} "
                f"key_configured={bool(self.config.api_key)}>")

    # ── بناء الطلب ───────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, prompt: str, history: list[Message] | None,
                 system_prompt: str, stream: bool) -> dict:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for m in history_to_messages(history):
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
        }

    def _url(self) -> str:
        return f"{self.config.base_url}/chat/completions"

    def _raise_for_status(self, status: int) -> None:
        if status in (401, 403):
            raise _auth_error(status)
        if status == 429:
            # نص الاستجابة لا يُضمَّن (نفس عقد عدم-الترديد)
            raise ProviderTransientError(
                f"حد المعدل تجاوز (HTTP {status})")
        if status >= 500:
            raise ProviderTransientError(
                f"خطأ خادم المزود (HTTP {status})")
        if status >= 400:
            raise ProviderTransientError(
                f"طلب مرفوض من المزود (HTTP {status})")

    # ── العقد القديم (send/stream) ───────────────────────

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        if not self.is_available():
            raise _auth_error(0)
        try:
            resp = requests.post(
                self._url(),
                json=self._payload(prompt, history, system_prompt,
                                   stream=False),
                headers=self._headers(),
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise ProviderTimeoutError(
                f"مهلة المزود انتهت ({self.config.timeout}s)") from exc
        except requests.RequestException as exc:
            # لا نمرر نص الاستثناء الخام (قد يحمل الترويسات) —
            # نوع الخطأ يكفي للتشخيص.
            raise ProviderTransientError(
                f"خطأ شبكة نحو المزود ({type(exc).__name__})") from exc
        self._raise_for_status(resp.status_code)
        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderTransientError(
                "استجابة غير متوافقة مع شكل chat/completions") from exc
        return content or ""

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        if not self.is_available():
            raise _auth_error(0)
        try:
            resp = requests.post(
                self._url(),
                json=self._payload(prompt, history, system_prompt,
                                   stream=True),
                headers=self._headers(),
                stream=True,
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise ProviderTimeoutError(
                f"مهلة المزود انتهت ({self.config.timeout}s)") from exc
        except requests.RequestException as exc:
            raise ProviderTransientError(
                f"خطأ شبكة نحو المزود ({type(exc).__name__})") from exc
        self._raise_for_status(resp.status_code)
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if not decoded.startswith("data: "):
                continue
            chunk = decoded[6:].strip()
            if chunk == "[DONE]":
                break
            try:
                data = json.loads(chunk)
                delta = data["choices"][0].get("delta", {})
                piece = delta.get("content")
            except (ValueError, KeyError, IndexError, TypeError):
                continue  # سطر SSE معطوب — نتجاوزه (نمط shelby)
            if isinstance(piece, str) and piece:
                yield piece
