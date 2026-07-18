# -*- coding: utf-8 -*-
"""T-017 (R-201): (re)generate the legacy-context golden files.

Usage (from repo root):
    python3 -m tests.goldens.context.capture_goldens

Copies the fixture project to a temp dir (running scenario ``setup`` hooks
where needed), runs the legacy pipeline via the harness, and writes one
``<scenario>.golden.json`` per scenario next to this script.

⚠️ Regenerating goldens rewrites the parity target — only do it when the
*legacy* behavior itself intentionally changes (it shouldn't: R-201 is a
behavior-preserving extraction).
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

from tests.goldens.context.harness import SCENARIOS, collect_legacy_context  # noqa: E402

GOLDENS_DIR = pathlib.Path(__file__).resolve().parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "sample_project"


def capture_one(name: str, spec: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        project = pathlib.Path(td) / "sample_project"
        shutil.copytree(FIXTURE_PROJECT, project)
        if spec["setup"] is not None:
            spec["setup"](project)
        snapshot = collect_legacy_context(project, spec["message"])
    snapshot["scenario"] = name
    snapshot["description"] = spec["description"]
    return snapshot


def main() -> None:
    for name, spec in SCENARIOS.items():
        snapshot = capture_one(name, spec)
        out = GOLDENS_DIR / f"{name}.golden.json"
        out.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"✅ {out.relative_to(REPO_ROOT)}  "
              f"(mentioned: {len(snapshot['mentioned_files'])})")


if __name__ == "__main__":
    main()
