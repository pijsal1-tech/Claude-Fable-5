# -*- coding: utf-8 -*-
"""TSK-731a (BATCH-P3): فحص التحديث اليدوي — مقارنة إصدارات + جلب manifest.

**العقد** (قرار النطاق في DEVELOPMENT_TASKS §TSK-731 — امتداد روح D-11):
- **لا تحديث تلقائي ولا phone-home صامت** (IR-1 محلي-أولًا): هذه الوحدة
  تُنادى فقط من نقطة REST عند-الطلب `/api/update-check`، وهي بدورها
  معطَّلة افتراضيًا في config. لا polling، لا تنزيل، لا استبدال ملفات.
- **الفحص لا يكسر شيئًا أبدًا**: أي فشل (شبكة/timeout/schema فاسد/
  إصدار غير قابل للتفسير) ⇒ ``None`` صامت — المستدعي يعرض «تعذّر
  الفحص» ولا شيء آخر يتأثر.
- **صفر استيراد وقت-تحميل لـ requests** (نمط T-109): الاستيراد كسول
  داخل ``check_for_update`` حصريًا — استيراد هذه الوحدة (ومنها عبر
  routes/meta.py) لا يجرّ مكتبة الشبكة.

صيغة الإصدارات المدعومة (semver-مبسّطة تغطي إصداراتنا الفعلية —
core/version.py = "1.0.0"؛ تدعم لاحقة -rc.N تاريخيًا):
``MAJOR.MINOR.PATCH`` مع لاحقة اختيارية ``-rc.N``. القاعدة: النهائي
أحدث من كل rc لنفس الثلاثية (1.0.0 > 1.0.0-rc.9)، وrc أعلى رقمًا أحدث.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 5.0

# MAJOR.MINOR.PATCH مع -rc.N اختيارية — تطابق تام (لا لواحق أخرى).
_VERSION_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$")


@dataclass(frozen=True)
class UpdateInfo:
    """نتيجة فحص ناجح — للقراءة فقط."""
    current: str
    latest: str
    update_available: bool
    url: str = ""


def parse_version(text: str) -> tuple[int, int, int, int] | None:
    """يفسّر إصدارًا إلى رباعية قابلة للمقارنة — None للنص الفاسد.

    الرباعية: (major, minor, patch, rc_rank) حيث rc_rank لإصدار نهائي
    = عدد كبير (أحدث من أي rc)، ولإصدار rc = رقمه.
    """
    if not isinstance(text, str):
        return None
    m = _VERSION_RE.match(text.strip())
    if m is None:
        return None
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    rc = m.group(4)
    # النهائي أحدث من كل rc: رتبته أعلى من أي رقم rc واقعي.
    rc_rank = 10**9 if rc is None else int(rc)
    return (major, minor, patch, rc_rank)


def compare_versions(a: str, b: str) -> int | None:
    """‏-1 لو a أقدم، 0 مساوٍ، +1 أحدث — None لو أي طرف فاسد."""
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        return None
    return (pa > pb) - (pa < pb)


def check_for_update(manifest_url: str, current: str,
                     timeout: float = DEFAULT_TIMEOUT_SECONDS
                     ) -> UpdateInfo | None:
    """يجلب manifest التحديث ويقارن — None عند أي فشل (صامت بالتصميم).

    شكل الـ manifest المتوقع: ``{"latest": "1.0.1", "url": "https://.."}``
    — مفتاح ``latest`` إلزامي، ``url`` اختياري (يُطهَّر إلى str).
    """
    if not manifest_url or parse_version(current) is None:
        return None
    try:
        import requests  # lazy — نمط T-109: لا استيراد وقت-تحميل
        resp = requests.get(manifest_url, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    latest = data.get("latest")
    cmp_result = compare_versions(current, str(latest or ""))
    if cmp_result is None:
        return None
    url = data.get("url")
    return UpdateInfo(
        current=current,
        latest=str(latest),
        update_available=(cmp_result < 0),
        url=str(url) if isinstance(url, str) else "",
    )
