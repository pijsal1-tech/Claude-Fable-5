# -*- coding: utf-8 -*-
"""TSK-718 (FI-05/1) — snapshot فهرس المشروع: صيغة v1 + حفظ/تحميل ذرّي.

═══════════════════ Design Note ═══════════════════

**المشكلة (FI-05 / NF-20-21):** فتح المشروع يبني ``ProjectIndex`` بمشية
شجرية كاملة (``os.walk`` — context/index.py:82). على مشروع 5k+ ملف
(هدف QA-T13) هذا زمن فتح ملموس *في كل إقلاع/تبديل مشروع*.

**الحل (على شطرين — قرار D-9):** هذه الوحدة = الشطر الأول: **ورقة نقية**
(صفر توصيل) تعرّف صيغة snapshot على القرص + حفظًا ذرّيًا + تحميلًا
متشككًا. الشطر الثاني (TSK-719) يوصلها بـ ``ProjectIndex``: تحميل ناجح
⇒ بذر ``_files`` بلا مشية؛ الطزاجة تبقى على عقد T-049 القائم
(write-through hooks + sweep الـ 2s) — الـ snapshot **تحسين زمن-فتح
فقط، ليس مصدر حقيقة**.

**الصيغة (v1):** JSON واحد::

    {"version": 1, "root": "<resolved root as posix str>",
     "files": ["rel/path1", "rel/path2", ...]}

- المسارات **نسبية** وبفواصل ``/`` (محايدة المنصة — قرار D-8-ب
  Windows-أولًا: snapshot مكتوب على فاصل واحد يعمل على كليهما).
- ``root`` يُخزَّن للتحقق فقط: snapshot لجذر آخر (مشروع نُقل/نُسخ)
  يُرفض ⇒ rebuild نظيف — لا فهرس لمسارات غير موجودة.

**عقود صارمة:**
- ``save_snapshot`` **لا يرفع أبدًا** — يعيد False عند أي فشل (قرص
  ممتلئ/صلاحيات/...). فشل الحفظ يُبتلع لأن الـ snapshot تحسين لا صحّة
  (نمط NF-14: الابتلاع معلَّل + أثر عبر structured_log.swallowed).
- الكتابة ذرّية بنمط NF-19 الحرفي: tmp بجوار الملف → fsync →
  ``os.replace`` (سابقة core/project_memory.py:356 — ذرّي على Windows
  أيضًا، تدقيق TSK-714).
- ``load_snapshot`` **متشكك**: أي عدم-تطابق (نسخة/جذر/JSON فاسد/شكل
  شاذ/عنصر غير نصي/مسار مطلق أو هارب ``..``) ⇒ ``None`` — الساقط
  يذهب لـ rebuild، أبدًا لا فهرس مشوّه.
- الوحدة تسكن ``core/`` **وليس** ``context/``: بوابة SafeReader grep
  (scripts/check.sh:24-27) تمنع ``open()`` الخام داخل context/ —
  والـ snapshot ملف تشغيلي داخلي لا يمر من SafeReader بالتصميم
  (ليس محتوى مستخدم؛ نفس معاملة memory.jsonl وmetrics/runs.jsonl).
═══════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
import pathlib

from core.structured_log import swallowed as _slog_swallowed

#: نسخة الصيغة — أي تغيير مكسِّر يرفعها فيسقط القديم لـ rebuild تلقائيًا.
SNAPSHOT_VERSION = 1


def _canon_root(root: str | pathlib.Path) -> str:
    """التمثيل القانوني للجذر في الملف: resolve + فواصل posix."""
    return pathlib.Path(root).resolve().as_posix()


def save_snapshot(path: str | pathlib.Path,
                  root: str | pathlib.Path,
                  rel_files: list[str]) -> bool:
    """حفظ ذرّي (نمط NF-19) — يعيد True عند النجاح، **لا يرفع أبدًا**.

    ``rel_files``: مسارات نسبية بفواصل ``/`` (كما يعيدها
    ``ProjectIndex.rel``). الترتيب يُحفظ كما ورد — التحميل لا يعيد
    الفرز (مسؤولية الفرز على الباذر في TSK-719).
    """
    try:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": SNAPSHOT_VERSION,
            "root": _canon_root(root),
            "files": list(rel_files),
        }
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        return True
    except Exception as _exc:
        # ابتلاع معلَّل (NF-14): الـ snapshot تحسين زمن-فتح فقط — فشل
        # حفظه لا يمس صحّة الفهرس الحي؛ الأثر عبر مسجّل الابتلاع.
        _slog_swallowed("core/index_snapshot.py:save_snapshot", _exc)
        return False


def load_snapshot(path: str | pathlib.Path,
                  root: str | pathlib.Path) -> list[str] | None:
    """تحميل متشكك — يعيد قائمة المسارات النسبية أو ``None``.

    ``None`` عند **أي** انحراف: ملف غائب، JSON فاسد، نسخة مغايرة،
    جذر مغاير (مشروع نُقل)، شكل شاذ (files ليست قائمة نصوص)، مسار
    مطلق أو هارب (``..``). الساقط يذهب لـ rebuild — لا فهرس مشوّه.
    """
    try:
        raw = pathlib.Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as _exc:
        _slog_swallowed("core/index_snapshot.py:load_snapshot:read", _exc)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("version") != SNAPSHOT_VERSION:
        return None
    if data.get("root") != _canon_root(root):
        return None
    files = data.get("files")
    if not isinstance(files, list):
        return None
    out: list[str] = []
    for item in files:
        if not isinstance(item, str) or not item:
            return None
        # رفض المطلق والهارب — snapshot لا يشير خارج الجذر أبدًا.
        if item.startswith("/") or item.startswith("\\"):
            return None
        parts = item.replace("\\", "/").split("/")
        if ".." in parts or any(p == "" for p in parts[:-1]):
            return None
        if ":" in parts[0]:          # مسار Windows مطلق (C:/...)
            return None
        out.append(item)
    return out
