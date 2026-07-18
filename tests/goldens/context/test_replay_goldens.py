# -*- coding: utf-8 -*-
"""T-017 (R-201): replay the 6 legacy-context goldens — parity net.

Each test copies the fixture project fresh, runs the harness (verbatim
port of server.py's inline context block), and asserts byte-exact equality
with the stored golden. Any drift in what the model *sees* fails loudly —
this is the safety net R-201's ContextEngine extraction must stay green
against.

Regenerate (only on intentional legacy-behavior change):
    python3 -m tests.goldens.context.capture_goldens
"""
from __future__ import annotations

import json
import pathlib
import shutil

import pytest

from tests.goldens.context.harness import SCENARIOS, collect_legacy_context

GOLDENS_DIR = pathlib.Path(__file__).resolve().parent

COMPARED_KEYS = (
    "message",
    "mentioned_files",
    "user_text_with_files",
    "project_context",
)


def _load_golden(name: str) -> dict:
    path = GOLDENS_DIR / f"{name}.golden.json"
    assert path.exists(), (
        f"golden مفقود: {path.name} — شغّل "
        f"`python3 -m tests.goldens.context.capture_goldens`"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_replay_matches_golden(scenario, sample_project, tmp_path):
    spec = SCENARIOS[scenario]
    if spec["setup"] is not None:
        spec["setup"](sample_project)

    golden = _load_golden(scenario)
    live = collect_legacy_context(sample_project, spec["message"])

    for key in COMPARED_KEYS:
        assert live[key] == golden[key], (
            f"[{scenario}] drift in {key!r} — الموديل بقى يشوف حاجة مختلفة."
        )


# ═══════════════ pinned quirks (خصائص يجب ألا تتغير بصمت) ═══════════════

@pytest.mark.integration
def test_huge_file_quirk_pinned():
    """>MAX_FILE_SIZE: مذكور في القائمة والعنوان يدّعي القراءة — بلا محتوى."""
    golden = _load_golden("huge_file")
    assert golden["mentioned_files"] == ["src/big_data.js"]
    assert "تم قراءة 1 ملف" in golden["user_text_with_files"]
    assert "📄" not in golden["user_text_with_files"]      # لا كتلة محتوى
    assert "```" not in golden["user_text_with_files"]


@pytest.mark.integration
def test_no_context_leaves_message_untouched():
    golden = _load_golden("no_context")
    assert golden["mentioned_files"] == []
    assert golden["user_text_with_files"] == golden["message"]


@pytest.mark.integration
def test_goldens_have_no_machine_paths():
    """المسارات مطبَّعة بـ <ROOT> — الـ goldens قابلة للنقل بين الأجهزة."""
    for name in SCENARIOS:
        golden = _load_golden(name)
        blob = golden["user_text_with_files"] + golden["project_context"]
        assert "/tmp/" not in blob and "\\Users\\" not in blob
        if golden["project_context"]:
            assert "<ROOT>" in golden["project_context"]


@pytest.mark.integration
def test_six_scenarios_exactly():
    """T-017 spec: الستة التمثيلية بالضبط."""
    assert sorted(SCENARIOS) == [
        "arabic_filename", "huge_file", "keyword_only",
        "mention_only", "mixed", "no_context",
    ]
