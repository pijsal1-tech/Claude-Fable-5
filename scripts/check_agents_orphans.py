# -*- coding: utf-8 -*-
"""حارس اليتامى في agents_rules/ — TSK-CEV-106 (AIA-7 حارس 2).

يمنع عودة التراكم غير المصنَّف (خلفية AIA-1: 201 ملفًا جُردت
وصُنّفت — أي ملف جديد يجب أن يدخل مصنَّفًا لا متسللًا):

  ملف في agents_rules/ يُعد شرعيًا إذا كان واحدًا من:
    1. مذكورًا كـ`file:` في manifest.yaml (ACTIVE)، أو
    2. ضمن baseline المثبَّت `scripts/agents_rules_baseline.txt`
       (جرد AIA-1 المصنَّف — REFERENCE/CANDIDATE/تشغيلي)، أو
    3. تحت `_archive/` (مسار الأرشفة المعتمد).

  أي ملف خارج الثلاثة = **يتيم** = فشل. الإضافة الشرعية تمر بتحديث
  baseline بوعي (diff مرئي في المراجعة) أو بإدراج manifest.

  ويُبلَّغ أيضًا عن مسارات baseline التي اختفت من القرص (stale) —
  تحذير لا فشل (الحذف الشرعي يُنظَّف من baseline لاحقًا).

خروج 0 = لا يتامى. أي يتيم = خروج 1 بقائمة المسارات.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents_rules"
BASELINE = REPO_ROOT / "scripts" / "agents_rules_baseline.txt"
MANIFEST = AGENTS_DIR / "manifest.yaml"


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    manifest_files = {
        spec["file"] for spec in manifest.get("agents", {}).values()
        if isinstance(spec, dict) and "file" in spec
    }
    baseline = {
        line.strip() for line in
        BASELINE.read_text(encoding="utf-8").splitlines() if line.strip()
    }

    on_disk = {
        str(p.relative_to(AGENTS_DIR))
        for p in AGENTS_DIR.rglob("*") if p.is_file()
    }

    orphans = sorted(
        f for f in on_disk
        if f not in manifest_files
        and f not in baseline
        and not f.startswith("_archive/")
    )
    stale = sorted(f for f in baseline if f not in on_disk)

    for s in stale:
        print(f"  warning: baseline entry no longer on disk: {s}")

    if orphans:
        print(f"ORPHANS GUARD: {len(orphans)} unclassified file(s) in "
              "agents_rules/ (add to manifest, or classify + update "
              "scripts/agents_rules_baseline.txt, or move to _archive/):")
        for o in orphans:
            print(f"  - {o}")
        return 1

    print(f"agents_rules orphans guard OK "
          f"({len(on_disk)} files: {len(manifest_files)} manifest / "
          f"baseline {len(baseline)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
