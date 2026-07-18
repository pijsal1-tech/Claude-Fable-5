# -*- coding: utf-8 -*-
"""T-020 (R-201): ContextBuilder أصبح مُكيّفًا فوق ContextEngine.

يفرض معيار القبول هيكليًا وسلوكيًا:
- «grep shows one context-reading path»: لا rglob في chain/context_builder.py —
  كل مشيات القراءة عبر ProjectScan (context/engine.py).
- مسح واحد فقط لكل gather() مهما تعددت المراحل (mention/dir/overview/search).
- _auto_prefetch يحمل توثيق التفويض ولا يقرأ الملفات بنفسه.
"""
from __future__ import annotations

import pathlib

import pytest

from chain.context_builder import ContextBuilder, gather_context
from context.engine import ProjectScan

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ═══════════════════════ هيكلي: مسار قراءة واحد ═══════════════════════

def _code_lines(path: pathlib.Path) -> list[str]:
    """أسطر الكود فقط — بلا تعليقات (التعليقات توثّق الماضي المحذوف)."""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # قص التعليق الذيلي
        lines.append(line.split("#", 1)[0])
    return lines


def test_no_rglob_left_in_context_builder():
    """كل مشيات rglob المكررة حُذفت — المسح الوحيد في ProjectScan."""
    src = REPO_ROOT / "chain" / "context_builder.py"
    offenders = [ln for ln in _code_lines(src) if ".rglob(" in ln]
    assert offenders == [], f"rglob عاد إلى context_builder: {offenders}"


def test_builder_imports_project_scan():
    src = (REPO_ROOT / "chain" / "context_builder.py").read_text(encoding="utf-8")
    assert "from context.engine import ProjectScan" in src


def test_prefetch_documents_delegation():
    src = (REPO_ROOT / "chain" / "agent_loop.py").read_text(encoding="utf-8")
    assert "T-020" in src and "ContextEngine" in src


# ═══════════════════════ سلوكي: مسح واحد لكل gather ═══════════════════════

@pytest.fixture()
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def main():\n    pass\n",
                                             encoding="utf-8")
    (tmp_path / "src" / "util.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    return tmp_path


def _count_scans(monkeypatch):
    """عدّاد إنشاءات ProjectScan داخل context_builder."""
    import chain.context_builder as cb
    counter = {"n": 0}

    class CountingScan(ProjectScan):
        def __init__(self, root):
            counter["n"] += 1
            super().__init__(root)

    monkeypatch.setattr(cb, "ProjectScan", CountingScan)
    return counter


def test_single_scan_per_gather(project, monkeypatch):
    """طلب يفعّل كل المراحل الأربع → ProjectScan واحد بالضبط."""
    counter = _count_scans(monkeypatch)
    builder = ContextBuilder(str(project))
    # ملف مذكور + مجلد + كلمة عامة + نمط كود — كل المراحل تعمل
    result = builder.gather("اشرح المشروع واقرأ app.py في مجلد src ودالة main")
    assert counter["n"] == 1
    assert result.has_context


def test_single_scan_via_cli_shortcut(project, monkeypatch):
    """gather_context (مسار CLI) يمر من نفس المسح الواحد."""
    counter = _count_scans(monkeypatch)
    text = gather_context(str(project), "اقرأ README.md")
    assert counter["n"] == 1
    assert "README.md" in text


def test_missing_file_fallback_uses_scan(project, monkeypatch):
    """البحث الاحتياطي بالاسم (كان rglob(basename)) يعمل عبر المسح."""
    counter = _count_scans(monkeypatch)
    builder = ContextBuilder(str(project))
    # اسم بلا مسار صحيح → resolve يفشل كملف مباشر → fallback بالاسم
    result = builder.gather("شوف wrong/dir/util.py")
    assert counter["n"] == 1
    utils = [i for i in result.items if i.kind == "file" and i.success]
    assert any("VALUE = 1" in i.content for i in utils)
