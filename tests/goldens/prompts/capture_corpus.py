# -*- coding: utf-8 -*-
"""AIA-R8: (re)generate the assembled-prompt golden corpus.

Usage:
    python3 -m tests.goldens.prompts.capture_corpus

إعادة الالتقاط عمل مقصود حصرًا: كل diff ناتج يُصنَّف يدويًا
(تحسين مقصود / محايد / انحدار) قبل التقييد — AIA-R8.
"""
from __future__ import annotations

import json

from tests.goldens.prompts.harness import (
    GOLDEN_PATH,
    SCENARIOS,
    run_scenario,
)


def main() -> None:
    corpus = {name: run_scenario(name) for name in sorted(SCENARIOS)}
    GOLDEN_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    total_steps = sum(len(s["steps"]) for s in corpus.values())
    print(f"captured {len(corpus)} scenarios / {total_steps} steps "
          f"-> {GOLDEN_PATH.name}")


if __name__ == "__main__":
    main()
