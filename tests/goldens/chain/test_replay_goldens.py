# -*- coding: utf-8 -*-
"""T-020 (R-201): replay the chain-prompt goldens against ContextBuilder.

عقد الـ parity لمسار الـ chain: أي تعديل على ContextBuilder (بما فيه
تقارب T-020 مع ContextEngine) يجب أن يعيد إنتاج هذه الـ goldens
بايت-بايت — items وprogress events (إطارات WS في _auto_prefetch)
وsummary (نص إطار auto_prefetch) وprompt section (مسار CLI).
"""
from __future__ import annotations

import json
import pathlib
import shutil

import pytest

from tests.goldens.chain.harness import SCENARIOS, collect_builder_snapshot

GOLDENS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = GOLDENS_DIR.parents[2]
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "sample_project"

SCENARIO_NAMES = sorted(SCENARIOS.keys())


def _load_golden(name: str) -> dict:
    path = GOLDENS_DIR / f"{name}.golden.json"
    assert path.exists(), (
        f"golden مفقود: {path.name} — شغّل "
        "python3 -m tests.goldens.chain.capture_goldens"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _replay(name: str, tmp_path: pathlib.Path) -> dict:
    spec = SCENARIOS[name]
    project = tmp_path / "sample_project"
    shutil.copytree(FIXTURE_PROJECT, project)
    if spec["setup"] is not None:
        spec["setup"](project)
    return collect_builder_snapshot(project, spec["message"])


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_items_match_golden(name, tmp_path):
    """العناصر (kind/source/success/size/content) بايت-بايت."""
    golden = _load_golden(name)
    snapshot = _replay(name, tmp_path)
    assert snapshot["items"] == golden["items"]


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_progress_events_match_golden(name, tmp_path):
    """تسلسل on_progress — هو نفسه تسلسل إطارات WS في _auto_prefetch."""
    golden = _load_golden(name)
    snapshot = _replay(name, tmp_path)
    assert snapshot["progress_events"] == golden["progress_events"]


@pytest.mark.parametrize("name", SCENARIO_NAMES)
def test_summary_and_prompt_match_golden(name, tmp_path):
    """summary (إطار auto_prefetch) + prompt section (مسار CLI)."""
    golden = _load_golden(name)
    snapshot = _replay(name, tmp_path)
    assert snapshot["summary"] == golden["summary"]
    assert snapshot["prompt_section"] == golden["prompt_section"]


def test_all_scenarios_have_goldens():
    """كل سيناريو له golden وكل golden له سيناريو — لا يتامى."""
    on_disk = {p.name[: -len(".golden.json")]
               for p in GOLDENS_DIR.glob("*.golden.json")}
    assert on_disk == set(SCENARIO_NAMES)
