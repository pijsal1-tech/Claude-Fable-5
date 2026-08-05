# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Permissions Overrides — تحرير الأذونات من الواجهة
  TSK-734a (القرار 6 من تسلسل D-19 — فوق TSK-621)

  **قرار واعٍ** (المواصفة): config.yaml لا يُكتب أبدًا — تعليقاته
  العربية الشارحة تسلم. التحرير عبر ملف جانبي
  ``permissions_overrides.json`` بجواره، كتابة ذرية بنمط NF-19
  الحرفي (tmp + fsync + os.replace — سابقة core/workspace_trust)،
  وقراءة طازجة عند كل استهلاك (الملف صغير — لا cache ⇒ حيوية بلا
  إبطال _config_cache).

  **whitelist صارم — fail-closed**: المفتاحان المسموحان حصرًا:
  - ``force_command_approval``: bool
  - ``agent.command_allowlist``: dict نص→نص غير فارغ
  أي مفتاح آخر أو نوع خاطئ ⇒ الملف كله يُرفض عند القراءة ({})
  والكتابة تُرفض (False) — قائمة أقصر أأمن من قائمة أوسع.

  حدود واعية: localhost-only — **فُحص وحُسم في TSK-737 (القرار 9)**:
  T1 في نموذج التهديد صنّف هذا المسار الأخطر (قلب force + توسيع
  allowlist عن بُعد = RCE) ⇒ POST /api/permissions يُقفَل 403 عند
  التعريض الشبكي حتى تحت راية --unsafe-expose-network (GET يبقى).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
import pathlib

OVERRIDES_FILENAME = "permissions_overrides.json"
OVERRIDES_VERSION = 1

# المفتاحان المسموحان حصرًا (whitelist — fail-closed على أي زيادة)
ALLOWED_KEYS = frozenset({"force_command_approval",
                          "agent.command_allowlist"})


def overrides_path(config_dir: str | pathlib.Path) -> pathlib.Path:
    """مسار ملف الـ overrides — بجوار config.yaml."""
    return pathlib.Path(config_dir) / OVERRIDES_FILENAME


def _valid_allowlist(value: object) -> bool:
    """dict نص→نص غير فارغ حصرًا (نفس صرامة command_policy_from)."""
    if not isinstance(value, dict):
        return False
    for k, v in value.items():
        if not isinstance(k, str) or not k.strip():
            return False
        if not isinstance(v, str) or not v.strip():
            return False
    return True


def validate_overrides(overrides: object) -> bool:
    """تحقق whitelist الصارم — True فقط لمحتوى مسموح بالكامل.

    fail-closed: أي مفتاح خارج ALLOWED_KEYS أو نوع خاطئ ⇒ False
    (لا قبول جزئي — الكل أو لا شيء).
    """
    if not isinstance(overrides, dict):
        return False
    for key, value in overrides.items():
        if key not in ALLOWED_KEYS:
            return False
        if key == "force_command_approval":
            if not isinstance(value, bool):
                return False
        elif key == "agent.command_allowlist":
            if not _valid_allowlist(value):
                return False
    return True


def read_overrides(config_dir: str | pathlib.Path) -> dict:
    """قراءة طازجة — fail-closed: {} عند غياب/عطب/محتوى غير مسموح.

    **لا يرفع أبدًا** (نفس عقد read_trust_record) — عطب الملف يعيد
    السياسة الأصلية (config.yaml وحده) لا سياسة مكسورة.
    """
    p = overrides_path(config_dir)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # NF-14 §2 (ابتلاع مقصود — fallback موثّق): غياب/عطب ⇒ لا overrides.
        return {}
    if not isinstance(data, dict):
        return {}
    overrides = data.get("overrides")
    if not isinstance(overrides, dict) or not validate_overrides(overrides):
        return {}
    return dict(overrides)


def write_overrides(config_dir: str | pathlib.Path,
                    overrides: dict) -> bool:
    """كتابة ذرية NF-19 بعد تحقق صارم. يعيد True عند النجاح، لا يرفع.

    overrides فارغ ⇒ حذف الملف (العودة الكاملة لـ config.yaml).
    محتوى غير مسموح ⇒ False بلا أي لمس للقرص (صفر تغيير حالة).
    """
    if not validate_overrides(overrides):
        return False
    p = overrides_path(config_dir)
    try:
        if not overrides:
            # مسح كامل — غياب الملف = لا overrides (حالة أصلية نظيفة)
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
            return True
        payload = {"version": OVERRIDES_VERSION, "overrides": overrides}
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        return True
    except Exception:
        # NF-14 §2 (ابتلاع مقصود): فشل قرص ⇒ False — المستهلك يبلّغ.
        return False


def apply_to_config(cfg: dict, overrides: dict) -> dict:
    """دمج الـ overrides فوق config — **نسخة جديدة، لا تحوير للمدخلات**.

    الأسبقية: overrides > config.yaml للمفتاحين المسموحين حصرًا؛
    باقي config يمر كما هو. overrides غير صالح ⇒ نسخة config كما هي
    (fail-closed — لا دمج جزئي).
    """
    merged = dict(cfg or {})
    if not validate_overrides(overrides) or not overrides:
        return merged
    if "force_command_approval" in overrides:
        merged["force_command_approval"] = overrides[
            "force_command_approval"]
    if "agent.command_allowlist" in overrides:
        agent = dict(merged.get("agent") or {}) \
            if isinstance(merged.get("agent"), dict) \
            else {}
        agent["command_allowlist"] = dict(
            overrides["agent.command_allowlist"])
        merged["agent"] = agent
    return merged
