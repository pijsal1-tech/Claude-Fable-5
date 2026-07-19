# -*- coding: utf-8 -*-
"""T-034 (R-401): (re)generate the routing golden corpus.

Usage (from repo root):
    python3 -m tests.goldens.routing.capture_corpus

يشغّل الثلاثين سيناريو من الـ harness على الراوتر/الأوركستريتور
الحقيقيَّين ويكتب ``routing_corpus.golden.json`` بجوار هذا الملف.

⚠️ إعادة التوليد تعيد كتابة هدف الـ parity الخاص بـ T-035 (توحيد
مفردات التوجيه) — لا تفعلها إلا لو تغيّر سلوك التوجيه **عمدًا**؛
الـ refactor نفسه يجب أن يبقي هذا الملف بايت-بايت كما هو.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.goldens.routing.harness import capture_corpus  # noqa: E402

GOLDENS_DIR = pathlib.Path(__file__).resolve().parent
OUT_PATH = GOLDENS_DIR / "routing_corpus.golden.json"


def main() -> None:
    corpus = capture_corpus()
    OUT_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2,
                   sort_keys=True) + "\n",
        encoding="utf-8",
    )
    layers = Counter(e["layer"] for e in corpus["entries"].values())
    print(f"  📌 {OUT_PATH.name}: {corpus['count']} decisions")
    for layer, n in sorted(layers.items()):
        print(f"     - {layer}: {n}")
    print("== routing corpus captured ==")


if __name__ == "__main__":
    main()
