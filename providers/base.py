# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  BaseProvider — الكلاس المجرد لمزودي نماذج AI
  كل مزود جديد (Use.ai, Gemini, OpenAI, ...) يرث منه

  M1a: Provider Contract
  - ProviderCapabilities / ProviderRequest / ProviderResponse
  - ProviderMessage (يحل محل history lists)
  - Error Taxonomy (retryable vs permanent)
  - MockProvider للاختبارات
  - Backward-compatible مع send()/stream() الحالية
═══════════════════════════════════════════════════════
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator
import re
import time


# ═══════════════════════════════════════════════════════
#   Data Models
# ═══════════════════════════════════════════════════════

@dataclass
class Message:
    """رسالة واحدة في المحادثة (التوافق الخلفي)"""
    role: str          # "user" | "assistant" | "system"
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderMessage:
    """رسالة موحدة للـ Provider Contract الجديد"""
    role: str          # "user" | "assistant" | "system"
    content: str


@dataclass
class ProviderConfig:
    """إعدادات المزود — كل مزود يوسعها حسب حاجته"""
    model: str = ""
    timeout: int = 90
    max_retries: int = 2
    extra: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════
#   Provider Capabilities
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProviderCapabilities:
    """
    قدرات المزود — كل مزود يعلن عنها.
    frozen=True لأنها snapshot ثابتة.
    """
    streaming: bool = False                  # يدعم streaming حقيقي؟
    structured_output: bool = False          # يدعم JSON native؟
    file_upload: bool = False                # يدعم رفع ملفات؟
    parallel_requests: bool = False          # يدعم طلبات متوازية؟
    persistent_sessions: bool = False        # يدعم محادثة مستمرة؟
    supports_cancellation: bool = False      # يدعم إلغاء طلب جاري؟
    max_context_tokens: int | None = None    # None = غير معروف
    max_output_tokens: int | None = None
    max_parallel_requests: int = 1


# ═══════════════════════════════════════════════════════
#   Provider Request / Response
# ═══════════════════════════════════════════════════════

@dataclass
class ProviderRequest:
    """طلب موحد — يشتغل مع أي مزود"""
    prompt: str
    system_prompt: str | None = None
    messages: list[ProviderMessage] = field(default_factory=list)
    response_schema: dict | None = None      # للـ structured output
    session_id: str | None = None            # للجلسات المستمرة
    timeout_seconds: int = 120
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """نتيجة موحدة"""
    text: str
    provider_name: str
    model_name: str | None = None
    session_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    raw_response: object | None = None


# ═══════════════════════════════════════════════════════
#   Error Taxonomy
# ═══════════════════════════════════════════════════════

class ProviderError(Exception):
    """خطأ أساسي من المزود"""
    retryable: bool = False
    retry_after_seconds: float | None = None

    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message)
        if retry_after is not None:
            self.retry_after_seconds = retry_after


class ProviderRateLimitError(ProviderError):
    """تجاوز الحد المسموح — يمكن إعادة المحاولة بعد انتظار"""
    retryable = True


class ProviderTimeoutError(ProviderError):
    """انتهاء المهلة — يمكن إعادة المحاولة"""
    retryable = True


class ProviderTransientError(ProviderError):
    """خطأ مؤقت (شبكة، 5xx) — يمكن إعادة المحاولة"""
    retryable = True


class ProviderContextTooLargeError(ProviderError):
    """السياق أكبر من المسموح — لا يمكن إعادة المحاولة بنفس الطلب"""
    retryable = False


class ProviderAuthenticationError(ProviderError):
    """خطأ في المصادقة — لا يمكن إعادة المحاولة"""
    retryable = False


class ProviderCreditExhaustedError(ProviderError):
    """نفذ الرصيد — لا يمكن إعادة المحاولة مع نفس الحساب"""
    retryable = False


class ProviderSessionExpiredError(ProviderError):
    """الجلسة انتهت — يمكن إعادة المحاولة بجلسة جديدة"""
    retryable = True


class ProviderInvalidResponseError(ProviderError):
    """رد غير صالح من المزود — يمكن إعادة المحاولة"""
    retryable = True


class ProviderRefusalError(ProviderError):
    """الرفض المتعلق بالسياسات أو الأمان — لا يمكن إعادة المحاولة لمنع provider shopping"""
    retryable = False


class EmptyProviderResponseError(ProviderError):
    """استجابة فارغة أو فارغة من المحتوى — يمكن إعادة المحاولة"""
    retryable = True


class MalformedProviderResponseError(ProviderError):
    """رد غير متوافق مع الصيغة المطلوبة أو تالف — يمكن إعادة المحاولة"""
    retryable = True


# ═══════════════════════════════════════════════════════
#   Helper: convert old history to messages
# ═══════════════════════════════════════════════════════

def history_to_messages(history: list[Message] | None) -> list[ProviderMessage]:
    """تحويل الـ history القديمة (list[Message]) إلى list[ProviderMessage]"""
    if not history:
        return []
    return [ProviderMessage(role=m.role, content=m.content) for m in history]


# ═══════════════════════════════════════════════════════
#   BaseProvider — الكلاس المجرد
# ═══════════════════════════════════════════════════════

class BaseProvider(ABC):
    """
    الكلاس المجرد — أي مزود AI يجب أن ينفذ هذه الدوال.

    === Provider Contract (M1a) ===

    كل مزود يجب أن ينفذ:
    1. capabilities (property) → ProviderCapabilities
    2. generate(request) → ProviderResponse

    الباقي (send, stream) موجود للتوافق الخلفي ويستدعي generate() تلقائياً.
    المزودات الحالية لسه بتستخدم send()/stream() — ده مقبول في v1.

    الاستخدام الجديد:
        provider = MyProvider(config)
        response = provider.generate(ProviderRequest(prompt="سؤالي"))

    الاستخدام القديم (لسه شغال):
        provider = MyProvider(config)
        reply = provider.send("سؤالي", history=[...])
    """

    name: str = "base"
    description: str = "Base AI Provider"

    def __init__(self, config: ProviderConfig | None = None):
        self.config = config or ProviderConfig()
        self._initialized = False

    # ── Provider Contract (الجديد) ──────────────────────

    @property
    def capabilities(self) -> ProviderCapabilities:
        """
        قدرات المزود — يمكن override في المزودات الفرعية.
        الافتراضي: لا شيء مدعوم.
        """
        return ProviderCapabilities()

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        الواجهة الموحدة الجديدة.

        الـ default implementation بتستدعي send() القديمة — عشان المزودات
        الحالية تشتغل بدون تعديل. المزودات الجديدة ممكن تعمل override مباشرة.
        """
        # تحويل messages → history للتوافق الخلفي
        history = None
        if request.messages:
            history = [Message(role=m.role, content=m.content) for m in request.messages]

        start_ms = time.monotonic()
        text = self.send(
            prompt=request.prompt,
            history=history,
            system_prompt=request.system_prompt or ""
        )
        duration_ms = int((time.monotonic() - start_ms) * 1000)

        return ProviderResponse(
            text=text,
            provider_name=self.name,
            model_name=self.config.model if self.config else None,
            duration_ms=duration_ms,
        )

    # ── Legacy API (التوافق الخلفي) ────────────────────

    @abstractmethod
    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        """إرسال رسالة وانتظار الرد الكامل"""
        ...

    @abstractmethod
    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """إرسال رسالة واستقبال الرد كـ stream (قطعة قطعة)"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """هل المزود جاهز للاستخدام؟ (مثلاً: حسابات متاحة / API key موجود)"""
        ...

    def initialize(self) -> bool:
        """تهيئة المزود (مرة واحدة) — يمكن override"""
        self._initialized = True
        return True

    def get_info(self) -> dict:
        """معلومات عن المزود"""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.config.model,
            "available": self.is_available(),
            "initialized": self._initialized,
        }

    def get_remaining_calls(self) -> int:
        """
        كم طلب يقدر المزود يستقبل قبل ما ينفد.
        يُستخدم من AccountAwareBudget و RequestRouter لتخطيط الـ chain.

        الافتراضي: 999 (غير محدود).
        المزودات اللي عندها حسابات محدودة تعمل override.
        """
        return 999



# ═══════════════════════════════════════════════════════
#   MockProvider — للاختبارات بدون استهلاك حسابات
# ═══════════════════════════════════════════════════════

class MockProvider(BaseProvider):
    """
    مزود مزيف يرجع ردود مسجلة (fixtures) حسب pattern في الـ prompt.

    الاستخدام:
        provider = MockProvider(script=[
            {"match": "تحليل", "response": '{"symbols": [...]}', "delay": 0.1},
            {"match": "fix",   "response": "```EDIT: ...```", "fail_times": 1},
        ])

    كل عنصر في الـ script:
        - match: regex pattern يُطابق في الـ prompt
        - response: النص المُرجع
        - delay: تأخير بالثواني (اختياري، افتراضي 0)
        - fail_times: عدد مرات الفشل قبل النجاح (اختياري، افتراضي 0)
    """

    name = "mock"
    description = "Mock Provider for testing"

    def __init__(self, script: list[dict] | None = None,
                 config: ProviderConfig | None = None,
                 mock_capabilities: ProviderCapabilities | None = None,
                 remaining_calls: int = 999):
        super().__init__(config or ProviderConfig(model="mock-model"))
        self.script = script or []
        self._call_counts: dict[str, int] = {}
        self._call_log: list[dict] = []
        self._remaining_calls = remaining_calls
        self._mock_capabilities = mock_capabilities or ProviderCapabilities(
            streaming=False,
            structured_output=True,
            parallel_requests=True,
            max_parallel_requests=5,
            max_context_tokens=100_000,
        )
        self._initialized = True

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._mock_capabilities

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        """يبحث في الـ script عن أول match ويرجع الـ response"""
        self._call_log.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "history_len": len(history) if history else 0,
        })

        for item in self.script:
            pattern = item.get("match", "")
            if re.search(pattern, prompt, re.IGNORECASE):
                key = pattern
                self._call_counts[key] = self._call_counts.get(key, 0) + 1

                # محاكاة الفشل
                fail_times = item.get("fail_times", 0)
                if self._call_counts[key] <= fail_times:
                    error_type = item.get("error_type", "transient")
                    if error_type == "rate_limit":
                        raise ProviderRateLimitError(
                            f"Mock rate limit #{self._call_counts[key]}",
                            retry_after=item.get("retry_after", 1.0)
                        )
                    elif error_type == "timeout":
                        raise ProviderTimeoutError(
                            f"Mock timeout #{self._call_counts[key]}"
                        )
                    elif error_type == "credit":
                        raise ProviderCreditExhaustedError(
                            f"Mock credit exhausted #{self._call_counts[key]}"
                        )
                    elif error_type == "context_too_large":
                        raise ProviderContextTooLargeError(
                            f"Mock context too large #{self._call_counts[key]}"
                        )
                    elif error_type == "auth":
                        raise ProviderAuthenticationError(
                            f"Mock auth error #{self._call_counts[key]}"
                        )
                    else:
                        raise ProviderTransientError(
                            f"Mock transient error #{self._call_counts[key]}"
                        )

                # محاكاة التأخير
                delay = item.get("delay", 0)
                if delay > 0:
                    time.sleep(delay)

                return item.get("response", "")

        # لو مفيش match → رد فاضي
        return "[MockProvider] No matching fixture for prompt"

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """streaming مزيف — يقطّع الرد"""
        full = self.send(prompt, history, system_prompt)
        chunk_size = 50
        for i in range(0, len(full), chunk_size):
            yield full[i:i + chunk_size]

    def is_available(self) -> bool:
        return True

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        """generate مباشر — بدون المرور بالـ legacy wrapper"""
        history = [Message(role=m.role, content=m.content) for m in request.messages] if request.messages else None

        start_ms = time.monotonic()
        text = self.send(
            prompt=request.prompt,
            history=history,
            system_prompt=request.system_prompt or ""
        )
        duration_ms = int((time.monotonic() - start_ms) * 1000)

        return ProviderResponse(
            text=text,
            provider_name=self.name,
            model_name=self.config.model,
            duration_ms=duration_ms,
        )

    # ── Test Helpers ──

    @property
    def total_calls(self) -> int:
        return len(self._call_log)

    def get_last_prompt(self) -> str:
        if self._call_log:
            return self._call_log[-1]["prompt"]
        return ""

    def reset(self):
        """إعادة تعيين العدادات"""
        self._call_counts.clear()
        self._call_log.clear()

    def get_remaining_calls(self) -> int:
        """عدد الطلبات المتبقية (قابل للتعيين للاختبارات)"""
        return self._remaining_calls

    def set_remaining_calls(self, n: int):
        """تعيين عدد الطلبات المتبقية (للاختبارات)"""
        self._remaining_calls = n

