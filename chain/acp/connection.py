# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ACP Connection — مراسلة request/response فوق transport مُحقَن
  TSK-736a (القرار 8 من تسلسل D-19)

  ``AcpConnection`` تدير حلقة المراسلة فوق transport **مُحقَن**
  (بروتوكول بسيط: ``read_line() -> str | None`` حاجبة حتى سطر أو
  EOF، و``write_line(str) -> None``) — في الإنتاج (736b) يكون
  الغلاف حول stdio العملية الفرعية؛ في الاختبارات ``FakeTransport``
  (القرار الواعي 5: صفر subprocess في اختبارات الوحدة).

  **الخيطية**: القراءة في خيط واحد (خيط ضخ يملكه المستدعي عبر
  ``pump_once``/``pump_forever``)؛ ``request()`` من أي خيط —
  المزامنة بقاموس أحداث لكل id (نمط ApprovalGate._pending
  TSK-615: مدخل مستقل بـ Event خاص؛ لا خانة مشتركة).

  **fail-closed**: مهلة انتظار الرد ⇒ ``AcpTimeoutError``؛
  EOF (موت العملية) ⇒ توقظ كل المنتظرين بـ ``AcpConnectionClosed``؛
  سطر غير مفهوم ⇒ يُسجَّل ويُتجاهَل (protocol.parse_line).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Protocol, Union

from .protocol import (
    ErrorResponse,
    Message,
    Notification,
    Request,
    Response,
    parse_line,
    serialize,
)

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = 60.0


class Transport(Protocol):
    """عقد النقل المُحقَن — سطر نصي في كل اتجاه.

    ``read_line`` تحجب حتى يتوفر سطر، وتعيد ``None`` عند EOF
    (انتهاء التدفق/موت العملية). ``write_line`` ترسل سطرًا واحدًا
    (بلا ``\\n`` — الإلحاق مسؤوليتها).
    """

    def read_line(self) -> str | None: ...  # pragma: no cover — عقد

    def write_line(self, line: str) -> None: ...  # pragma: no cover — عقد


class AcpError(Exception):
    """أساس أخطاء طبقة ACP."""


class AcpTimeoutError(AcpError):
    """مهلة انتظار رد — لا يحمل تفاصيل الطلب (قد تحوي مسارات)."""


class AcpConnectionClosed(AcpError):
    """التدفق أُغلق (EOF/موت عملية) قبل اكتمال المراسلة."""


class AcpProtocolError(AcpError):
    """رد خطأ JSON-RPC من الطرف الآخر — يحمل code وmessage فقط."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"JSON-RPC error {code}: {message}")
        self.code = code
        self.message = message


class _Pending:
    """مدخل انتظار مستقل لكل طلب (نمط TSK-615 — لا خانة مشتركة)."""

    __slots__ = ("event", "result", "error")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.result: Any = None
        self.error: AcpError | None = None


class AcpConnection:
    """مراسلة JSON-RPC فوق transport مُحقَن.

    Args:
        transport: عقد النقل (حقيقي في 736b، مزيف في الاختبارات).
        on_request: معالج الطلبات العكسية من الوكيل
            ``(Request) -> Any`` — القيمة المعادة تُرسل ردَّ نجاح؛
            رفعه ``AcpProtocolError`` يُرسل ردَّ خطأ بكوده؛ أي
            استثناء آخر ⇒ INTERNAL_ERROR بلا تفاصيل (لا تسريب).
        on_notification: معالج الإشعارات ``(Notification) -> None``
            — استثناؤه يُسجَّل ولا يقتل الضخ.
        timeout_seconds: مهلة انتظار الرد الافتراضية.
    """

    def __init__(
        self,
        transport: Transport,
        on_request: Callable[[Request], Any] | None = None,
        on_notification: Callable[[Notification], None] | None = None,
        timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self._transport = transport
        self._on_request = on_request
        self._on_notification = on_notification
        self._timeout = timeout_seconds

        self._lock = threading.Lock()
        self._pending: dict[Union[int, str], _Pending] = {}
        self._next_id = 1
        self._closed = False

    # ─── الإرسال ───

    def _send(self, msg: Message) -> None:
        if self._closed:
            raise AcpConnectionClosed("الاتصال مغلق")
        self._transport.write_line(serialize(msg))

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        """إرسال إشعار (بلا انتظار رد)."""
        self._send(Notification(method=method, params=params or {}))

    def request(self, method: str, params: dict[str, Any] | None = None,
                timeout: float | None = None) -> Any:
        """طلب مع انتظار الرد — يرفع AcpTimeoutError/AcpConnectionClosed/
        AcpProtocolError (fail-closed: لا انتظار أبديًّا)."""
        with self._lock:
            if self._closed:
                raise AcpConnectionClosed("الاتصال مغلق")
            req_id = self._next_id
            self._next_id += 1
            entry = _Pending()
            self._pending[req_id] = entry
        try:
            self._send(Request(id=req_id, method=method, params=params or {}))
            if not entry.event.wait(timeout if timeout is not None
                                    else self._timeout):
                raise AcpTimeoutError(
                    f"مهلة انتظار رد '{method}' انقضت")
            if entry.error is not None:
                raise entry.error
            return entry.result
        finally:
            with self._lock:
                self._pending.pop(req_id, None)

    # ─── الاستقبال (خيط الضخ — يملكه المستدعي) ───

    def pump_once(self) -> bool:
        """قراءة سطر واحد ومعالجته. ``False`` عند EOF (بعد إيقاظ
        كل المنتظرين بـ AcpConnectionClosed)."""
        line = self._transport.read_line()
        if line is None:
            self.close()
            return False
        msg = parse_line(line)
        if msg is None:
            # ضجيج على stdout (banner/log) — يُسجَّل ويُتجاهَل
            logger.debug("acp: سطر غير مفهوم تم تجاهله (%d بايت)",
                         len(line))
            return True
        self._dispatch(msg)
        return True

    def pump_forever(self) -> None:
        """حلقة ضخ حتى EOF — للاستخدام كهدف خيط في 736b."""
        while self.pump_once():
            pass

    def _dispatch(self, msg: Message) -> None:
        if isinstance(msg, Response):
            self._resolve(msg.id, result=msg.result, error=None)
        elif isinstance(msg, ErrorResponse):
            if msg.id is None:
                logger.warning("acp: خطأ بلا id من الوكيل (code=%s)",
                               msg.code)
                return
            self._resolve(msg.id, result=None,
                          error=AcpProtocolError(msg.code, msg.message))
        elif isinstance(msg, Request):
            self._handle_incoming_request(msg)
        elif isinstance(msg, Notification):
            self._handle_incoming_notification(msg)

    def _resolve(self, msg_id: Union[int, str], result: Any,
                 error: AcpError | None) -> None:
        with self._lock:
            entry = self._pending.get(msg_id)
        if entry is None:
            logger.debug("acp: رد لطلب غير معروف/منتهٍ id=%r", msg_id)
            return
        entry.result = result
        entry.error = error
        entry.event.set()

    def _handle_incoming_request(self, req: Request) -> None:
        from .protocol import INTERNAL_ERROR, METHOD_NOT_FOUND
        if self._on_request is None:
            self._send(ErrorResponse(id=req.id, code=METHOD_NOT_FOUND,
                                     message="لا معالج طلبات"))
            return
        try:
            result = self._on_request(req)
        except AcpProtocolError as exc:
            # رفض مقصود من المعالج (بوابة/denylist) — الكود والرسالة
            # يبنيهما المعالج بلا تفاصيل حساسة
            self._send(ErrorResponse(id=req.id, code=exc.code,
                                     message=exc.message))
            return
        except Exception as exc:
            # لا تسريب تفاصيل (قد تحوي مسارات/محتوى) — النوع فقط
            # (سابقة openai_compat: type(exc).__name__ حصرًا)
            logger.exception("acp: معالج الطلب فشل")
            self._send(ErrorResponse(id=req.id, code=INTERNAL_ERROR,
                                     message=type(exc).__name__))
            return
        self._send(Response(id=req.id, result=result))

    def _handle_incoming_notification(self, note: Notification) -> None:
        if self._on_notification is None:
            return
        try:
            self._on_notification(note)
        except Exception:
            logger.exception("acp: معالج الإشعار فشل — الضخ مستمر")

    # ─── الإغلاق ───

    def close(self) -> None:
        """إغلاق: يوقظ كل المنتظرين بـ AcpConnectionClosed (fail-closed —
        لا خيط يبقى معلّقًا على عملية ميتة)."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            entries = list(self._pending.values())
        closed_err = AcpConnectionClosed("الاتصال أُغلق قبل وصول الرد")
        for entry in entries:
            entry.error = closed_err
            entry.event.set()

    @property
    def closed(self) -> bool:
        return self._closed
