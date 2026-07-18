# -*- coding: utf-8 -*-
"""T-018 (R-201): ContextEngine skeleton + MentionSource.

المعايير:
1. mention goldens (T-017) خضراء عبر المصدر الجديد — parity بايت-بايت.
2. **مسح واحد** لنظام الملفات لكل gather مهما تعددت المصادر.
3. الثابت الكاذب أُصلح: الحد الحقيقي 10 بتعليق صادق.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from context.engine import (
    ContextBundle,
    ContextEngine,
    ContextItem,
    ContextRequest,
    ContextSource,
    ProjectScan,
)
from context.sources.mention import (
    MAX_MENTIONED_FILES,
    MentionSource,
    extract_search_terms,
    render_legacy_injection,
)
from tests.goldens.context.harness import SCENARIOS

GOLDENS_DIR = (pathlib.Path(__file__).resolve().parents[1]
               / "goldens" / "context")


def _load_golden(name: str) -> dict:
    return json.loads(
        (GOLDENS_DIR / f"{name}.golden.json").read_text(encoding="utf-8"))


def _gather_mentions(project_root, message):
    engine = ContextEngine([MentionSource()])
    return engine.gather(ContextRequest(message=message,
                                        project_root=project_root))


# ═══════════════ 1) parity: goldens عبر المصدر الجديد ═══════════════

@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_mention_source_matches_goldens(scenario, sample_project):
    """كل golden من T-017 يُعاد إنتاجه بايت-بايت عبر MentionSource."""
    spec = SCENARIOS[scenario]
    if spec["setup"] is not None:
        spec["setup"](sample_project)
    golden = _load_golden(scenario)

    bundle = _gather_mentions(sample_project, spec["message"])

    assert bundle.paths("mention") == golden["mentioned_files"]

    rendered = render_legacy_injection(spec["message"], bundle.items)
    expected = golden["user_text_with_files"].replace(
        "<ROOT>", str(sample_project.resolve()))
    assert rendered == expected


def test_huge_file_item_has_none_content(sample_project):
    """quirk مثبّت: الملف الضخم يُذكر لكن content=None (لا كتلة محتوى)."""
    SCENARIOS["huge_file"]["setup"](sample_project)
    bundle = _gather_mentions(sample_project, "افتح big_data.js وشوف المشكلة")
    assert bundle.paths() == ["src/big_data.js"]
    assert bundle.items[0].content is None


# ═══════════════ 2) مسح واحد لكل gather ═══════════════

class _CountingScanFactory:
    def __init__(self):
        self.count = 0

    def __call__(self, root):
        self.count += 1
        return ProjectScan(root)


class _PathsOnlySource:
    """مصدر ثانٍ للتأكد أن تعدد المصادر لا يضاعف المسح."""
    kind = "paths_only"

    def collect(self, request, scan):
        return [ContextItem(source_kind=self.kind, path=scan.rel(p))
                for p in scan.files[:2]]


def test_single_scan_per_gather(sample_project):
    """معيار القبول: gather واحد = ProjectScan واحد مهما تعددت المصادر."""
    factory = _CountingScanFactory()
    engine = ContextEngine([MentionSource(), _PathsOnlySource()],
                           scan_factory=factory)
    engine.gather(ContextRequest(
        message="قارن بين src/app.js و auth و database و config.json",
        project_root=sample_project))
    assert factory.count == 1

    engine.gather(ContextRequest(message="تاني", project_root=sample_project))
    assert factory.count == 2          # مسح جديد لكل طلب — لا staleness


def test_mention_source_does_no_tree_walk(sample_project, monkeypatch):
    """المصدر يعمل على scan.files فقط — أي rglob داخله = فشل."""
    scan = ProjectScan(sample_project)     # المسح المسموح (قبل الحقن)

    def _boom(self, pattern):
        raise AssertionError(f"source walked the tree: rglob({pattern!r})")

    monkeypatch.setattr(pathlib.Path, "rglob", _boom)
    items = MentionSource().collect(
        ContextRequest(message="اقرأ config.json", project_root=sample_project),
        scan)
    assert [i.path for i in items] == ["config.json"]


# ═══════════════ 3) الثابت الكاذب أُصلح ═══════════════

def test_lying_constant_fixed():
    """الحد الحقيقي 10 — الكود والتعليق متطابقان أخيرًا."""
    import re as _re
    assert MAX_MENTIONED_FILES == 10
    src = (pathlib.Path(__file__).resolve().parents[2]
           / "context" / "sources" / "mention.py").read_text(encoding="utf-8")
    # لا سطر كود (غير التعليقات التي توثّق الـ legacy) يعيّن 100
    code_lines = [ln for ln in src.splitlines()
                  if not ln.lstrip().startswith("#")]
    assert not any(_re.match(r"\s*MAX_MENTIONED\w*\s*=\s*100", ln)
                   for ln in code_lines)


def test_max_files_enforced(sample_project):
    """الحد يُطبَّق فعلًا: مصدر بحد 2 لا يرجع أكثر من عنصرين."""
    bundle = ContextEngine([MentionSource(max_files=2)]).gather(
        ContextRequest(
            message="راجع config.json و index.html و run.sh و settings.yaml",
            project_root=sample_project))
    assert len(bundle) == 2


# ═══════════════ سلوكيات الهيكل ═══════════════

def test_bundle_dedupes_first_wins():
    b = ContextBundle()
    assert b.add(ContextItem("mention", "a.py", "v1")) is True
    assert b.add(ContextItem("mention", "a.py", "v2")) is False
    assert b.add(ContextItem("keyword", "a.py", "v3")) is True   # مصدر مختلف
    assert len(b) == 2
    assert b.items[0].content == "v1"


def test_engine_isolates_broken_source(sample_project):
    """مصدر يرمي استثناء لا يُسقط بقية المصادر — نفس تسامح legacy."""
    class _Broken:
        kind = "broken"

        def collect(self, request, scan):
            raise RuntimeError("boom")

    bundle = ContextEngine([_Broken(), MentionSource()]).gather(
        ContextRequest(message="اقرأ config.json",
                       project_root=sample_project))
    assert bundle.paths("mention") == ["config.json"]


def test_mention_source_satisfies_protocol():
    assert isinstance(MentionSource(), ContextSource)


def test_extract_search_terms_legacy_rules():
    exact, stems = extract_search_terms(
        "قارن src/app.js مع auth و the و 123 و في")
    assert "src/app.js" in exact
    assert "auth" in stems
    assert "app" in stems              # جذع الاسم الكامل يدخل أيضًا
    assert "the" not in stems          # stopword
    assert "123" not in stems          # أرقام فقط
    assert "في" not in stems           # stopword عربي
