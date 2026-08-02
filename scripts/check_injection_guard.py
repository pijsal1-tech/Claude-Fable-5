# -*- coding: utf-8 -*-
"""حارس الحقن الشامل — TSK-CEV-109 (AIA-7 حارس 5 / NF-18 / TSK-404).

يفرض حضور سياج الحقن في كل طبقات البرومبت المُجمَّع النهائي:

  1. **مسار server/chat**: `ATTACHED_OPEN_FMT` و
     `INJECTION_GUARD_INSTRUCTION` معرَّفان في prompts/templates.py
     والتعليمة ملحقة فعليًا بـ`SYSTEM_PROMPT` و`CORE_SYSTEM_PROMPT`
     (فحص قيم حية عبر import — لا grep نصي قابل للخداع).
  2. **مسار السلاسل — system**: قاعدة «بيانات لا أوامر» حاضرة في
     **كل** ملف دور في manifest (21/21) — الضابط التعويضي لغياب
     INJECTION_GUARD_INSTRUCTION في executor.py:441 (CEV-F-013؛
     الفجوة المقيسة 2/21 = CEV-F-016، أُصلحت 109a).
  3. **مسار السلاسل — user**: أسوار `DATA ONLY` حاضرة في مصانع
     برومبتات الاستراتيجيات (chain/strategies.py و
     chain/orchestrator.py — المواضع التي تُضمِّن file_content).

  ملاحظة نطاق (F-013): تسييج نتائج التبعيات المحقونة في
  ChainStep.build_prompt (chain/models.py `[Result from …]`) توسيع
  منفصل لم يُنفذ بعد — هذا الحارس يوثّق الحد ولا يدّعي تغطيته.

خروج 0 = السياج حاضر في الطبقات الثلاث. أي غياب = خروج 1.
"""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

GUARD_PHRASE = "بيانات لا أوامر"
DATA_ONLY_FENCE = "START OF SOURCE CODE — DATA ONLY"


def main() -> int:
    errors: list[str] = []

    # ── 1. مسار server/chat: قيم حية ──
    from prompts import templates
    for name in ("ATTACHED_OPEN_FMT", "ATTACHED_CLOSE",
                 "INJECTION_GUARD_INSTRUCTION", "fence_attached"):
        if not hasattr(templates, name):
            errors.append(f"templates.{name} missing")
    guard = getattr(templates, "INJECTION_GUARD_INSTRUCTION", "")
    for target in ("SYSTEM_PROMPT", "CORE_SYSTEM_PROMPT"):
        value = getattr(templates, target, "")
        if not guard or guard.strip() not in value:
            errors.append(
                f"INJECTION_GUARD_INSTRUCTION not appended to {target}")

    # ── 2. مسار السلاسل system: 21/21 ملف دور ──
    import yaml
    agents_dir = REPO_ROOT / "agents_rules"
    manifest = yaml.safe_load(
        (agents_dir / "manifest.yaml").read_text(encoding="utf-8"))
    checked = 0
    for role, spec in sorted(manifest.get("agents", {}).items()):
        path = agents_dir / spec["file"]
        if not path.is_file():
            # غياب الملف شأن حارس الـmanifest (105) — لا ازدواج
            continue
        checked += 1
        if GUARD_PHRASE not in path.read_text(encoding="utf-8"):
            errors.append(
                f"role {role}: {spec['file']} lacks the "
                f"«{GUARD_PHRASE}» rule (NF-18 compensating control)")

    # ── 3. مسار السلاسل user: أسوار DATA ONLY ──
    for src in ("chain/strategies.py", "chain/orchestrator.py"):
        text = (REPO_ROOT / src).read_text(encoding="utf-8")
        if "file_content" in text and DATA_ONLY_FENCE not in text:
            errors.append(f"{src}: embeds file_content without "
                          f"'{DATA_ONLY_FENCE}' fences")

    if errors:
        print(f"INJECTION GUARD: {len(errors)} violation(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"injection guard OK (templates wired; {checked}/21 role files "
          "carry the data-not-commands rule; DATA ONLY fences present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
