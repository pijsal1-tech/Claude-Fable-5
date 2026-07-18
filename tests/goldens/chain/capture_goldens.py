# -*- coding: utf-8 -*-
"""T-020 (R-201): (re)generate the chain-prompt golden files.

Usage (from repo root):
    python3 -m tests.goldens.chain.capture_goldens

نفس نمط T-017: نسخ الـ fixture لمجلد مؤقت (+ setup hook إن وجد)، تشغيل
ContextBuilder عبر الـ harness، وكتابة ``<scenario>.golden.json`` بجوار
هذا الملف.

⚠️ إعادة التوليد تعيد كتابة هدف الـ parity — لا تفعلها إلا لو سلوك
ContextBuilder نفسه تغيّر عمدًا (T-020 refactor يجب أن يبقيها خضراء).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.goldens.chain.harness import (  # noqa: E402
    SCENARIOS,
    collect_builder_snapshot,
)

GOLDENS_DIR = pathlib.Path(__file__).resolve().parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "sample_project"


def capture_one(name: str, spec: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        project = pathlib.Path(td) / "sample_project"
        shutil.copytree(FIXTURE_PROJECT, project)
        if spec["setup"] is not None:
            spec["setup"](project)
        snapshot = collect_builder_snapshot(project, spec["message"])
    snapshot["scenario"] = name
    snapshot["description"] = spec["description"]
    return snapshot


def main() -> None:
    for name, spec in SCENARIOS.items():
        snapshot = capture_one(name, spec)
        out = GOLDENS_DIR / f"{name}.golden.json"
        out.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2,
                       sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"  📌 {out.name}: {len(snapshot['items'])} items, "
              f"{len(snapshot['progress_events'])} events")
    print("== chain goldens captured ==")


if __name__ == "__main__":
    main()
