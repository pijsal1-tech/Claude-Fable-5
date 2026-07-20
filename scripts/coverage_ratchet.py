#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coverage ratchet (T-050 / R-703): بوابة تغطية تصاعدية-فقط.

المبدأ: ``coverage_baseline.txt`` يحمل أرضية التغطية المسجّلة (بدأت 40.0
حسب مواصفة R-703 ثم رُفعت للقيمة المقاسة الحقيقية). أي تشغيل تنخفض فيه
التغطية تحت الأرضية **يفشل** — والأرضية لا تنخفض أبدًا (increase-only):
رفعها يتم حصرًا عبر ``--update`` بعد قياس أعلى، وخفضها يدويًا مرفوض
بالمراجعة (الملف متتبَّع في git فأي خفض ظاهر في الـ diff).

الاستخدام:
    python3 scripts/coverage_ratchet.py check   # بوابة CI — exit 1 لو انخفضت
    python3 scripts/coverage_ratchet.py update  # رفع الأرضية بعد قياس أعلى

يقرأ النسبة من ``coverage.json`` (مخرجات ``coverage json`` /
``pytest --cov --cov-report=json``). البرمجية قابلة للاختبار:
``ratchet(current, baseline)`` نقية، والقراءة/الكتابة معزولتان.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE_FILE = REPO_ROOT / "coverage_baseline.txt"
COVERAGE_JSON = REPO_ROOT / "coverage.json"

# هامش رفع الأرضية عند --update: نُبقي 0.5 نقطة تحت المقاس لامتصاص
# اهتزاز القياس بين البيئات (خطوط منفّذة شرطيًا بحسب OS/توقيت).
UPDATE_MARGIN = 0.5


def read_baseline(path: pathlib.Path = BASELINE_FILE) -> float:
    """قراءة الأرضية — سطر واحد بنسبة عشرية."""
    return float(path.read_text(encoding="utf-8").strip())


def read_current(path: pathlib.Path = COVERAGE_JSON) -> float:
    """قراءة التغطية الحالية من coverage.json (totals.percent_covered)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return float(data["totals"]["percent_covered"])


def ratchet(current: float, baseline: float) -> tuple[bool, str]:
    """قرار البوابة — نقي وقابل للاختبار.

    يعيد (ok, message): ok=False يعني انخفاضًا تحت الأرضية ⇒ فشل CI.
    """
    if current < baseline:
        return False, (
            f"coverage ratchet FAIL: {current:.1f}% < baseline "
            f"{baseline:.1f}% — coverage may never decrease. Add tests "
            f"for the new code or remove dead code."
        )
    return True, (
        f"coverage ratchet OK: {current:.1f}% >= baseline {baseline:.1f}%"
    )


def next_baseline(current: float, baseline: float,
                  margin: float = UPDATE_MARGIN) -> float:
    """أرضية جديدة عند --update: تصاعدية-فقط، بهامش أمان تحت المقاس."""
    candidate = max(baseline, round(current - margin, 1))
    return candidate


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "check"
    if mode not in ("check", "update"):
        print(f"usage: {argv[0]} [check|update]", file=sys.stderr)
        return 2

    # نمرر المسارات من globals الموديول وقت النداء (لا القيم الافتراضية
    # المربوطة وقت التعريف) — يتيح للاختبارات حقن fixture بتبديل الـ globals.
    if not COVERAGE_JSON.exists():
        print("coverage.json not found — run: "
              "python3 -m pytest --cov=. --cov-report=json", file=sys.stderr)
        return 2

    baseline = read_baseline(BASELINE_FILE)
    current = read_current(COVERAGE_JSON)

    if mode == "update":
        new_val = next_baseline(current, baseline)
        if new_val > baseline:
            BASELINE_FILE.write_text(f"{new_val}\n", encoding="utf-8")
            print(f"baseline ratcheted up: {baseline:.1f}% -> {new_val:.1f}%")
        else:
            print(f"baseline unchanged: {baseline:.1f}% "
                  f"(current {current:.1f}%)")
        return 0

    ok, message = ratchet(current, baseline)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
