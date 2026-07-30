# -*- coding: utf-8 -*-
"""
TSK-704 (FI-06 / NF-14) — السجلات المهيكلة: JSON formatter على stdlib
logging + مسجّل الابتلاع المقصود.

المشكلة (NF-14): عشرات مواقع ``except Exception`` الصامتة (pass/continue)
عبر core/ وchain/ — الابتلاع **مقصود ومصون** (كل موقع له تعليل موثق)،
لكن غياب أي أثر يجعل التشخيص مستحيلًا عند الحاجة.

العقد الصارم (bit-identical سلوكيًا):
- ``swallowed()`` **لا يرفع استثناءً أبدًا** — فشل التسجيل نفسه يُبتلع.
- المستوى DEBUG على logger ``webdev.swallowed`` — **صفر مخرجات افتراضيًا**
  (stdlib lastResort يمرر WARNING+ فقط، ولا handler يُركَّب تلقائيًا).
  التفعيل قرار صريح عبر :func:`configure`.
- صفر تبعيات جديدة — stdlib فقط (json/logging/time).
- صفر تغيير تدفق تحكم في المواقع الموصولة: سطر السجل يسبق pass/continue
  القائمَين ولا يستبدل أي شيء.

الاستهلاك النمطي في موقع ابتلاع::

    except Exception as _exc:
        _slog_swallowed("chain/bridge.py:_run_thread", _exc)
        pass  # التعليل الأصلي يبقى كما هو

التفعيل الاختياري (أداة محلية — stderr يكفي)::

    from core import structured_log
    structured_log.configure()          # DEBUG → stderr بصيغة JSON
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

#: اسم الجذر لكل مسجلات الوحدة.
ROOT_LOGGER_NAME = "webdev"

#: مسجّل الابتلاع المقصود (NF-14) — DEBUG، صامت ما لم يُفعَّل صراحة.
_SWALLOWED = logging.getLogger(ROOT_LOGGER_NAME + ".swallowed")


class JsonFormatter(logging.Formatter):
    """صياغة سطر JSON واحد لكل سجل — حقول ثابتة + حقول إضافية.

    الحقول الثابتة: ``ts`` (epoch ثوانٍ، float)، ``level``، ``logger``،
    ``event`` (نص الرسالة). أي مفاتيح في ``record.structured`` (dict)
    تُدمج كما هي. القيم غير القابلة للتسلسل تُحوَّل بـ ``str`` —
    الصياغة **لا ترفع** (نفس عقد swallowed).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        extra = getattr(record, "structured", None)
        if isinstance(extra, dict):
            payload.update(extra)
        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            # حتى فشل التسلسل لا يرفع — سطر إنقاذ أدنى.
            return json.dumps({"ts": time.time(), "level": "ERROR",
                               "logger": record.name,
                               "event": "structured_log_format_failed"})


def get_logger(name: str = ROOT_LOGGER_NAME) -> logging.Logger:
    """مسجّل تحت جذر الوحدة — ``get_logger("chain")`` → ``webdev.chain``."""
    if name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(ROOT_LOGGER_NAME + "." + name)


def configure(level: int = logging.DEBUG, stream=None) -> logging.Handler:
    """تركيب handler بصيغة JSON على جذر الوحدة — **التفعيل الصريح الوحيد**.

    idempotent: نداء ثانٍ يعيد الـ handler القائم دون تكرار.
    يعيد الـ handler (لأغراض الاختبار/الفك).
    """
    root = logging.getLogger(ROOT_LOGGER_NAME)
    for h in root.handlers:
        if getattr(h, "_webdev_structured", False):
            root.setLevel(level)
            return h
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler._webdev_structured = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)
    # لا propagate للجذر العام — لا نلوث logging تطبيقات أخرى بنفس العملية.
    root.propagate = False
    return handler


def swallowed(event: str, exc: BaseException | None = None,
              **fields: Any) -> None:
    """أثر ابتلاع مقصود (NF-14) — **لا يرفع أبدًا، لا يغيّر التدفق أبدًا**.

    ``event``: معرف الموقع الثابت (``"path.py:function"``).
    ``exc``: الاستثناء المبتلَع (يُسجَّل نوعه ونصه فقط — لا traceback،
    الابتلاع مقصود والموقع معلَّل في الكود).
    """
    try:
        if not _SWALLOWED.isEnabledFor(logging.DEBUG):
            return
        structured: dict[str, Any] = dict(fields)
        if exc is not None:
            structured["exc_type"] = type(exc).__name__
            structured["exc_msg"] = str(exc)
        _SWALLOWED.debug(event, extra={"structured": structured})
    except Exception:
        # فشل التسجيل نفسه يُبتلع — العقد فوق كل شيء.
        pass
