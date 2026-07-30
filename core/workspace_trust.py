# -*- coding: utf-8 -*-
"""TSK-725a (P2-3/D-10): Workspace Trust — وحدة تخزين قرار الثقة.

العقد (fail-closed — سابقة D-1/TSK-617):
- المجلد **غير موثوق افتراضيًا**: ملف معدوم، JSON معطوب، قيمة غير
  bool، أو أي استثناء ⇒ ``is_trusted`` تعيد **False ولا ترمي أبدًا**.
- التخزين في ``<root>/.ai_runs/trust.json`` — داخل IGNORED_DIRS
  (core/ignore_rules.py) فلا يظهر في الفهرس/البحث.
- الكتابة ذرية بنمط NF-19 (tmp + fsync + os.replace — سابقة
  core/index_snapshot.py): ``set_trust`` تعيد True/False ولا ترفع.
- لا منطق إنفاذ هنا — الإنفاذ في server.py (شريحة 725b)؛ هذه وحدة
  تخزين نقية قابلة للاختبار بمعزل.
"""

from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone

TRUST_VERSION = 1
_FILE_NAME = "trust.json"
_DIR_NAME = ".ai_runs"


def trust_path(root: str | pathlib.Path) -> pathlib.Path:
    """مسار ملف الثقة لجذر مشروع: ``<root>/.ai_runs/trust.json``."""
    return pathlib.Path(root) / _DIR_NAME / _FILE_NAME


def read_trust_record(root: str | pathlib.Path) -> dict | None:
    """السجل الخام إن وُجد وصحّ شكله — وإلا None (لا يرمي أبدًا).

    الصحة: JSON dict به مفتاح ``trusted`` من نوع bool حقيقي
    (isinstance صارم — 1/"true" لا تُقبل).
    """
    try:
        raw = trust_path(root).read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("trusted"), bool):
            return data
        return None
    except Exception:
        return None


def is_trusted(root: str | pathlib.Path) -> bool:
    """هل المجلد موثوق؟ **fail-closed**: أي غياب/عطب/شك ⇒ False."""
    rec = read_trust_record(root)
    return bool(rec is not None and rec["trusted"] is True)


def set_trust(root: str | pathlib.Path, trusted: bool,
              decided_by: str = "user") -> bool:
    """تخزين قرار الثقة ذريًا (NF-19). يعيد True عند النجاح، لا يرفع.

    السجل: {version, trusted, decided_at(ISO-8601 UTC), decided_by}.
    """
    try:
        p = trust_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": TRUST_VERSION,
            "trusted": bool(trusted),
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "decided_by": str(decided_by),
        }
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        return True
    except Exception:
        return False
