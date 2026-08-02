# -*- coding: utf-8 -*-
"""حارس الـmanifest الدائم — TSK-CEV-105 (AIA-7 حارس 1).

يفحص ضد agents_rules/manifest.yaml **الحقيقي**:
  1. schema صالح: بناء AgentLoader الفعلي (fail-fast — ManifestError
     عند البناء = خروج ≠0 برسالة الأخطاء ذاتها).
  2. كل `file:` موجود فعليًا على القرص — لا اعتماد على fallback
     الصامت (حتى للأدوار المعلنة `fallback: base`: غياب الملف مع
     إعلان fallback مقصود يُسمح لكن يُطبع تحذيرًا صريحًا).
  3. كل ملف تحت حدود اللودر: MAX_PROMPT_SIZE و MAX_PROMPT_LINES —
     تجاوز الأسطر يُقتطع صامتًا وقت التشغيل (agent_loader.py:668)؛
     هذا الحارس يجعله **صاخبًا** وقت الفحص.
  4. `load(role)` ينجح لكل دور ويعود من مصدر agents_rules
     (لا fallback) ما دام الملف موجودًا.

خروج 0 = كل الفحوص خضراء. أي فشل = خروج 1 بقائمة مفصلة.
"""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from chain.agent_loader import (  # noqa: E402
    MAX_PROMPT_LINES,
    MAX_PROMPT_SIZE,
    AgentLoader,
    ManifestError,
)

AGENTS_DIR = REPO_ROOT / "agents_rules"


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. schema + بناء السجل (fail-fast الحقيقي) ──
    try:
        loader = AgentLoader()
    except ManifestError as e:
        print(f"MANIFEST GUARD: schema/registry FAILED:\n{e}")
        return 1

    roles = sorted(loader.get_available_roles())

    for role in roles:
        definition = loader.definition(role)
        rel = definition.file
        path = AGENTS_DIR / rel

        # ── 2. وجود الملف ──
        if not path.is_file():
            if definition.fallback == "base":
                warnings.append(
                    f"{role}: file missing ({rel}) — declared fallback: base")
            else:
                errors.append(f"{role}: file MISSING: {rel}")
            continue

        # ── 3. حدود اللودر (صاخبة هنا، صامتة وقت التشغيل) ──
        size = path.stat().st_size
        if size > MAX_PROMPT_SIZE:
            errors.append(
                f"{role}: {rel} exceeds MAX_PROMPT_SIZE "
                f"({size} > {MAX_PROMPT_SIZE})")
        content = path.read_text(encoding="utf-8", errors="replace")
        line_count = content.count("\n") + 1
        if line_count > MAX_PROMPT_LINES:
            errors.append(
                f"{role}: {rel} exceeds MAX_PROMPT_LINES "
                f"({line_count} > {MAX_PROMPT_LINES}) — "
                "runtime would truncate SILENTLY")
        if not content.strip():
            errors.append(f"{role}: {rel} is empty")

        # ── 4. التحميل الفعلي من المصدر الصحيح ──
        try:
            prompt = loader.load(role)
        except Exception as e:  # noqa: BLE001 — حارس: أي فشل = أحمر
            errors.append(f"{role}: load() raised {type(e).__name__}: {e}")
            continue
        if prompt.source != "agents_rules":
            errors.append(
                f"{role}: load() fell back to source={prompt.source!r} "
                f"despite existing file {rel}")

    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        print(f"MANIFEST GUARD: {len(errors)} violation(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"manifest guard OK ({len(roles)} roles, "
          f"limits {MAX_PROMPT_SIZE}B/{MAX_PROMPT_LINES}L)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
