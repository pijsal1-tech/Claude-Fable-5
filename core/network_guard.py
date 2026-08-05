# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Network Guard — حارس التعريض الشبكي
  TSK-737a (القرار 9 من تسلسل D-19 — الأخير)

  **نموذج التهديد الحاكم** (المواصفة — DEVELOPMENT_TASKS §TSK-737):
  لا مصادقة على REST/WS إطلاقًا ⇒ من يصل للمنفذ يملك المشروع
  والطرفية. الحكم الحاسم T4: قناة الموافقة نفسها WS غير مُصادَق —
  المهاجم الشبكي «يوافق على أفعاله بنفسه»، فلا قيمة أمنية لأي تقسية
  سلوكية طالما القناة مفتوحة ⇒ الحل الوحيد السليم منع الربط المكشوف
  نفسه. المسار الموصى للوصول عن بُعد: نفق SSH / VPN / reverse-proxy
  بمصادقة — كلها تنتهي إلى loopback فتعمل مع الافتراضي 127.0.0.1.

  **fail-closed** (القرار الواعي 6): loopback = تعريف صريح حصري —
  ``127.0.0.0/8`` كاملة + ``::1`` + ``localhost`` (حرفيًا،
  case-insensitive). كل ما عداه — بما فيه ``0.0.0.0`` و``::``
  وأسماء المضيفين وعناوين LAN وأي مدخل غير قابل للتحليل — **مكشوف**
  (ما لم يثبت أنه loopback فهو مكشوف).

  **الحكم بواقعة الربط لا بعنوان الطالب** (القرار الواعي 5): هذه
  الوحدة تُقيِّم قيمة ``--host`` المُمرَّرة للإقلاع (واقعة زمن-إقلاع
  ثابتة)، لا ``remote_addr`` لكل طلب (قابل للتضليل خلف proxy —
  ألاعيب X-Forwarded-For خارجة عن النموذج).

  وحدة نقية: صفر شبكة، صفر Flask، صفر حالة — دوال فقط.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import ipaddress

# راية opt-in الصريحة — اسمها يصرّح بالخطر (القرار الواعي 2؛
# سابقة force_command_approval: الافتراض البرمجي آمن دائمًا).
EXPOSE_FLAG = "--unsafe-expose-network"


def is_loopback_host(host: object) -> bool:
    """هل قيمة ``--host`` تربط على loopback حصرًا؟

    True فقط لـ: ``127.0.0.0/8`` كاملة (IPv4)، ``::1`` (IPv6)،
    و``localhost`` الحرفية (case-insensitive). أي شيء آخر ⇒ False:

    - ``0.0.0.0`` / ``::`` (كل الواجهات) ⇒ مكشوف.
    - عناوين LAN/عامة وأسماء مضيفين ⇒ مكشوف (لا استعلام DNS —
      اسم غير ``localhost`` قد يشير لأي واجهة؛ fail-closed).
    - غير-نص / فارغ / قمامة غير قابلة للتحليل ⇒ مكشوف
      (fail-closed: ما لم يثبت loopback فهو مكشوف).
    """
    if not isinstance(host, str):
        return False
    value = host.strip()
    if not value:
        return False
    if value.lower() == "localhost":
        return True
    # صيغة URL/IPv6 بأقواس ``[::1]`` تُطبَّع قبل التحليل.
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        # ليس عنوان IP صالحًا (hostname/قمامة) ⇒ لا يثبت loopback.
        return False
    # is_loopback تغطي 127.0.0.0/8 كاملة و::1 معًا؛ عنوان IPv6
    # المُخرَّط ::ffff:127.x.y.z يُقبل أيضًا (loopback فعليًا).
    return bool(addr.is_loopback)


def exposure_refusal_message(host: str) -> str:
    """نص رسالة رفض الإقلاع الموحّد عند ربط غير loopback بلا راية.

    تشرح الخطر (لا مصادقة — من يصل للمنفذ يملك المشروع والطرفية)،
    وتذكر المسار السليم (نفق SSH/VPN/proxy ينتهي إلى loopback)،
    والراية الصريحة لمن يُصرّ (على مسؤوليته الواعية).
    """
    return (
        f"⛔ رفض الإقلاع: --host {host} يربط خارج loopback.\n"
        f"   هذه أداة تطوير محلية **بلا مصادقة** على REST/WebSocket —\n"
        f"   من يصل للمنفذ يملك مشروعك وطرفيّتك (تنفيذ أوامر عن بُعد).\n"
        f"   للوصول عن بُعد الآمن: نفق SSH (ssh -L)، أو VPN، أو\n"
        f"   reverse-proxy بمصادقة — كلها تعمل مع الافتراضي 127.0.0.1\n"
        f"   بلا أي راية.\n"
        f"   للمتابعة رغم ذلك (على مسؤوليتك): أضف {EXPOSE_FLAG}\n"
        f"   — وحتى معها تُقفَل مسارات: POST /api/permissions،\n"
        f"   وأوامر وكلاء ACP، ويُقسَر force_command_approval=true."
    )
