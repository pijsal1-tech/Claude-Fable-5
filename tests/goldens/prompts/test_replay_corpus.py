# -*- coding: utf-8 -*-
"""AIA-R8 (G8.5/S108): إعادة corpus البرومبتات المجمَّعة — حارس دائم.

- **الإعادة (replay):** كل سيناريو يعاد تجميعه حيًا (توجيه + تحميل
  أدوار manifest + بناء برومبتات الخطوات) ويجب أن يطابق الـ golden
  **بالقاموس كاملًا** — أي فرق = انحدار برومبتات حتى يُصنَّف يدويًا
  (تحسين مقصود يسبقه ADR / محايد / انحدار).
- **بلا نموذج حقيقي (P-11):** كل شيء حتمي — التوجيه والتحميل والبناء.
- **مصفوفة التغطية:** الـ corpus يمس 5 استراتيجيات (direct/
  context_window/chunk_chain/map_reduce/pipeline) و6 أدوار manifest
  (executor/code_analyzer/planner/deep_debugger/architect/
  code_reviewer) — كل الأدوار القابلة للوصول آليًا اليوم (F-014).
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.goldens.prompts.harness import (  # noqa: E402
    GOLDEN_PATH,
    SCENARIOS,
    run_scenario,
)


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_replay_matches_golden(scenario: str) -> None:
    """إعادة حية = golden بالقاموس كاملًا (dict-equality)."""
    golden = _load_golden()
    assert scenario in golden, (
        f"سيناريو {scenario!r} غائب عن الـ golden — أعد الالتقاط "
        "(python3 -m tests.goldens.prompts.capture_corpus) وصنّف الفرق"
    )
    live = run_scenario(scenario)
    assert live == golden[scenario], (
        f"انحدار برومبتات في {scenario!r}: التجميع الحي يخالف الـ "
        "golden. صنّف الفرق (تحسين مقصود/محايد/انحدار) قبل أي إعادة "
        "التقاط — AIA-R8."
    )


def test_no_orphan_golden_scenarios() -> None:
    """كل سيناريو في الـ golden له تعريف حي (لا بقايا محذوفة)."""
    assert set(_load_golden()) == set(SCENARIOS)


def test_coverage_matrix_strategies() -> None:
    """الـ corpus يغطي المفردات الخمس القابلة للبناء آليًا."""
    strategies = {s["strategy"] for s in _load_golden().values()}
    assert {"direct", "context_window", "chunk_chain",
            "map_reduce", "pipeline"} <= strategies


def test_coverage_matrix_roles() -> None:
    """الـ corpus يغطي كل الأدوار القابلة للوصول آليًا (F-014)."""
    roles = {
        step["agent_role"]
        for s in _load_golden().values()
        for step in s["steps"]
    }
    assert {"executor", "code_analyzer", "planner",
            "deep_debugger", "architect", "code_reviewer"} <= roles
