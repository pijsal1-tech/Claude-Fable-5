# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Provider Keys — قارئ مفاتيح API الجانبي
  TSK-735a (القرار 7 من تسلسل D-19 — قيد D-20)

  **قرار واعٍ** (المواصفة + قيد D-20): config.yaml **متتبَّع في git**
  والشجرة تُعامل كمنشورة دائمًا (V3 §0 قيد 5) ⇒ لا مفتاح API يُكتب
  فيه أو في أي ملف متتبَّع أبدًا (V3 §0 قيد 6). السر يعيش حصرًا في
  ملف جانبي مُتجاهَل ``provider_keys.json`` بجوار config.yaml
  (سابقة accounts_use_ai.json المُتجاهَل)، وهو مُدرَج في
  SECRETS_DENYLIST_NAMES (chain/path_policy) فلا تقرؤه أدوات
  الوكيل ولا SafeReader.

  الشكل على القرص::

      {"version": 1, "keys": {"<provider_id>": "<api_key>"}}

  **قراءة طازجة عند كل استهلاك** (سابقة TSK-734: الملف صغير —
  لا cache ⇒ تعديل المفتاح ينفذ عند التبديل التالي بلا إعادة تشغيل).

  **fail-closed**: غياب/عطب/أنواع خاطئة ⇒ {} أو إسقاط صامت للإدخال
  المعطوب — لا يرفع أبدًا (غياب المفتاح حالة مشروعة: المزود يظهر
  بـ key_configured:false).

  **لا دالة كتابة** (قرار واعٍ): الملف يُنشئه المستخدم يدويًا؛
  لا مسار كتابة أسرار من الكود. **حُسم في TSK-737 (القرار 9)**:
  تحرير المفاتيح من UI **مؤجَّل بلا أجل** — الحكم T4 (قناة الموافقة
  WS غير مُصادَقة) يجعل أي مسار كتابة أسرار عبر قناة غير مُصادَقة
  خطأً تصميميًا؛ يُسجَّل FI إن طلبه المالك مستقبلًا.

  **عقد عدم-الترديد**: هذه الوحدة تعيد المفتاح للمستدعي (حقن وقت
  إنشاء المزود) ولا تسجّله في أي log/خطأ — ولا يجوز لأي مستهلك
  إدراج القيمة المعادة في استجابة أو سجل (اختبار العقد في 735c).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import pathlib

KEYS_FILENAME = "provider_keys.json"
KEYS_VERSION = 1


def keys_path(config_dir: str | pathlib.Path) -> pathlib.Path:
    """مسار ملف المفاتيح — بجوار config.yaml."""
    return pathlib.Path(config_dir) / KEYS_FILENAME


def read_provider_keys(config_dir: str | pathlib.Path) -> dict[str, str]:
    """قراءة طازجة لخريطة provider_id → api_key.

    fail-closed بلا استثناءات:
    - الملف غائب/غير قابل للقراءة/JSON معطوب ⇒ {}.
    - الجذر ليس dict أو ``keys`` ليست dict ⇒ {}.
    - أي إدخال مفتاحه أو قيمته ليست نصًّا غير فارغ ⇒ يُسقَط صامتًا
      (الإدخالات السليمة الأخرى تبقى — عطب إدخال لا يعطّل البقية).

    ملاحظة عقد: القيم أسرار — لا تُسجَّل ولا تُردَّد (V3 §0 قيد 6).
    """
    path = keys_path(config_dir)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    keys = data.get("keys")
    if not isinstance(keys, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in keys.items():
        if not isinstance(k, str) or not k.strip():
            continue
        if not isinstance(v, str) or not v.strip():
            continue
        out[k] = v
    return out


def key_for(config_dir: str | pathlib.Path,
            provider_id: str) -> str | None:
    """مفتاح مزود واحد — None عند الغياب (حالة مشروعة، لا خطأ)."""
    return read_provider_keys(config_dir).get(provider_id)
