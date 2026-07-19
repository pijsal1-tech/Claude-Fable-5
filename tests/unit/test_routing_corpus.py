# -*- coding: utf-8 -*-
"""T-034 (R-401): الـ corpus الذهبي لقرارات التوجيه — إعادة + تغطية.

- **الإعادة على الكود القديم (corpus replays on legacy):** كل سيناريو من
  الثلاثين يعاد تشغيله عبر الـ harness ويجب أن يطابق المدخل المسجل في
  ``routing_corpus.golden.json`` **بالقاموس كاملًا** (dict-equality).
  بعد T-035 (توحيد المفردات) يجب أن يبقى هذا الملف أخضر بلا تعديل
  على الـ golden.

- **مصفوفة التغطية (corpus coverage matrix):** الـ corpus يغطي مفردات
  الراوتر الأربع ومفردات الأوركستريتور الست — بما فيها delegate عبر
  builder المباشر، والـ misroute-ان الصامتان الموثَّقان.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.goldens.routing.harness import (  # noqa: E402
    SCENARIOS,
    run_scenario,
)

GOLDEN_PATH = (REPO_ROOT / "tests" / "goldens" / "routing"
               / "routing_corpus.golden.json")

ROUTER_VOCAB = {"direct", "auto_chain", "full_chain", "delegate"}
ORCHESTRATOR_VOCAB = {"direct", "context_window", "chunk_chain",
                      "map_reduce", "pipeline", "delegate"}


@pytest.fixture(scope="module")
def corpus() -> dict:
    assert GOLDEN_PATH.exists(), (
        "routing_corpus.golden.json مفقود — أعد توليده:\n"
        "  python3 -m tests.goldens.routing.capture_corpus"
    )
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ═══════════════ بنية الـ corpus ═══════════════

def test_corpus_has_exactly_30_entries(corpus):
    assert corpus["format"] == 1
    assert corpus["count"] == 30
    assert len(corpus["entries"]) == 30


def test_corpus_and_scenarios_have_same_names(corpus):
    assert set(corpus["entries"]) == set(SCENARIOS)


# ═══════════════ corpus replays on legacy ═══════════════

@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_replays_identically(corpus, name):
    """إعادة تشغيل السيناريو الآن تطابق القرار المسجل حرفيًّا."""
    fresh = run_scenario(SCENARIOS[name])
    assert fresh == corpus["entries"][name], (
        f"سيناريو {name!r} لم يعد يطابق الـ golden — سلوك التوجيه تغيّر.\n"
        "لو التغيير مقصود أعد التوليد؛ لو أثناء T-035 فهذا كسر parity."
    )


# ═══════════════ corpus coverage matrix ═══════════════

def test_router_vocabulary_fully_covered(corpus):
    """المفردات الأربع للراوتر كلها تظهر كقرارات فعلية."""
    seen = {e["decision"]["strategy"]
            for e in corpus["entries"].values() if e["layer"] == "router"}
    assert ROUTER_VOCAB <= seen, f"مفردات راوتر ناقصة: {ROUTER_VOCAB - seen}"


def test_orchestrator_vocabulary_fully_covered(corpus):
    """المفردات الست للأوركستريتور كلها تظهر — delegate عبر الـ builder."""
    seen = {e["decision"]["strategy_name"]
            for e in corpus["entries"].values()
            if e["layer"] in ("orchestrator", "builder_delegate")}
    assert ORCHESTRATOR_VOCAB <= seen, (
        f"مفردات أوركستريتور ناقصة: {ORCHESTRATOR_VOCAB - seen}"
    )


def test_corpus_includes_budget_downgrade_decisions(corpus):
    """downgrades الميزانية ملتقطة — على الأقل قرار واحد downgraded=True."""
    flagged = [n for n, e in corpus["entries"].items()
               if e["layer"] == "router" and e["decision"]["downgraded"]]
    assert "router_auto_chain_downgrades_to_direct_flagged" in flagged
    assert "router_forced_delegate_unaffordable_downgrades" in flagged


def test_corpus_captures_silent_delegate_to_full_chain_downgrade(corpus):
    """صادق: تنزيل delegate→full_chain بالميزانية لا يرفع downgraded —
    quirk موثَّق يلتقطه الـ corpus كما هو (T-035/R-401 قد يصلحه لاحقًا)."""
    d = corpus["entries"]["router_delegate_downgrades_to_full_chain"]["decision"]
    assert d["strategy"] == "full_chain"
    assert d["downgraded"] is False  # الـ flag يُرفع فقط عند السقوط لـ direct


def test_corpus_captures_documented_silent_misroutes(corpus):
    """الـ misroute-ان الصامتان — يجب أن يظلا مسجلين بصدق قبل الإصلاح."""
    # (أ) force_strategy="delegate" في الأوركستريتور يسقط لـ direct بصمت
    orch = corpus["entries"]["orch_forced_delegate_falls_back_to_direct"]
    assert orch["decision"]["strategy_name"] == "direct"

    # (ب) force_strategy غير معروفة تمر حرفيًّا في strategy
    router = corpus["entries"]["router_forced_unknown_string_passes_through"]
    assert router["decision"]["strategy"] == "banana"
    assert router["decision"]["downgraded"] is False


def test_corpus_layer_distribution(corpus):
    """16 راوتر + 13 أوركستريتور + 1 builder = 30."""
    from collections import Counter
    layers = Counter(e["layer"] for e in corpus["entries"].values())
    assert layers == {"router": 16, "orchestrator": 13,
                      "builder_delegate": 1}
