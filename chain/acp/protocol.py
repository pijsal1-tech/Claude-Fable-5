# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ACP Protocol — تأطير JSON-RPC 2.0 النقي
  TSK-736a (القرار 8 من تسلسل D-19)

  ACP (agentclientprotocol.com) يمرّر رسائل JSON-RPC 2.0 مفصولة
  بأسطر (newline-delimited) عبر stdio. هذه الوحدة **نقية**:
  بناء/تحليل الرسائل فقط — صفر I/O وصفر subprocess وصفر شبكة
  (القرار الواعي 5 في المواصفة).

  **fail-closed في التحليل**: سطر ليس JSON صالحًا أو ليس رسالة
  JSON-RPC معروفة الشكل ⇒ ``None`` (المستهلك يتجاهله مُسجِّلًا) —
  لا انهيار أبدًا: عملية خارجية قد تكتب ضجيجًا على stdout.

  أكواد الأخطاء القياسية (JSON-RPC 2.0 §5.1) مُصدَّرة كثوابت؛
  أخطاء التطبيق (رفض بوابة/denylist في 736b) تستخدم النطاق
  المخصص -32000..-32099.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, TypeGuard, Union

JSONRPC_VERSION = "2.0"

# ─── أكواد JSON-RPC 2.0 القياسية ───
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
# ─── نطاق التطبيق (server-defined) — تستهلكه 736b ───
ERR_PERMISSION_DENIED = -32000   # رفض ApprovalGate / مهلة موافقة
ERR_PATH_FORBIDDEN = -32001      # خارج workspace أو denylist أسرار
ERR_AGENT_UNAVAILABLE = -32002   # العملية ماتت / غير مهيأة


@dataclass
class Request:
    """طلب JSON-RPC (له id — ينتظر ردًّا)."""
    id: Union[int, str]
    method: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    """إشعار JSON-RPC (بلا id — لا رد)."""
    method: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """رد نجاح JSON-RPC."""
    id: Union[int, str]
    result: Any = None


@dataclass
class ErrorResponse:
    """رد خطأ JSON-RPC. ``id=None`` مشروع لخطأ تحليل (§5)."""
    id: Union[int, str, None]
    code: int
    message: str
    data: Any = None


Message = Union[Request, Notification, Response, ErrorResponse]


# ─── البناء (serialize) ───

def _dump(payload: dict[str, Any]) -> str:
    """سطر JSON واحد — ensure_ascii=False يمرر العربية كما هي
    (الأنبوب bytes UTF-8؛ فك الترميز مسؤولية transport)."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def serialize(msg: Message) -> str:
    """رسالة → سطر JSON (بلا ``\\n`` — الإلحاق مسؤولية transport)."""
    payload: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION}
    if isinstance(msg, Request):
        payload["id"] = msg.id
        payload["method"] = msg.method
        if msg.params:
            payload["params"] = msg.params
    elif isinstance(msg, Notification):
        payload["method"] = msg.method
        if msg.params:
            payload["params"] = msg.params
    elif isinstance(msg, Response):
        payload["id"] = msg.id
        payload["result"] = msg.result
    elif isinstance(msg, ErrorResponse):
        payload["id"] = msg.id
        err: dict[str, Any] = {"code": msg.code, "message": msg.message}
        if msg.data is not None:
            err["data"] = msg.data
        payload["error"] = err
    else:  # pragma: no cover — عقد الأنواع يمنعه
        raise TypeError(f"رسالة غير معروفة: {type(msg).__name__}")
    return _dump(payload)


# ─── التحليل (parse — fail-closed) ───

def _valid_id(value: Any) -> TypeGuard[Union[int, str]]:
    """معرّف JSON-RPC مقبول: int أو str (بدون bool — هي int في بايثون).

    TypeGuard: يضيّق النوع لدى mypy في فروع parse_line."""
    return (isinstance(value, int) and not isinstance(value, bool)) \
        or isinstance(value, str)


def parse_line(line: str) -> Message | None:
    """سطر → رسالة، أو ``None`` لأي شكل غير صالح (fail-closed).

    لا ترفع أبدًا: الوكيل الخارجي قد يطبع ضجيجًا (logs/banners)
    على stdout — سطر غير مفهوم يُتجاهَل ولا يقتل الجلسة.
    """
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    if obj.get("jsonrpc") != JSONRPC_VERSION:
        return None

    has_id = "id" in obj
    msg_id = obj.get("id")

    # رد خطأ (قد يكون id=None لخطأ تحليل عند الطرف الآخر)
    if "error" in obj:
        err = obj["error"]
        if not isinstance(err, dict) or not isinstance(err.get("code"), int):
            return None
        if msg_id is not None and not _valid_id(msg_id):
            return None
        return ErrorResponse(
            id=msg_id,
            code=err["code"],
            message=str(err.get("message", "")),
            data=err.get("data"),
        )

    # رد نجاح
    if "result" in obj:
        if not has_id or not _valid_id(msg_id):
            return None
        return Response(id=msg_id, result=obj["result"])

    # طلب / إشعار
    method = obj.get("method")
    if not isinstance(method, str) or not method:
        return None
    params = obj.get("params", {})
    if not isinstance(params, dict):
        # ACP يستخدم named params حصرًا؛ positional تُرفض fail-closed
        return None
    if has_id:
        if not _valid_id(msg_id):
            return None
        return Request(id=msg_id, method=method, params=params)
    return Notification(method=method, params=params)
