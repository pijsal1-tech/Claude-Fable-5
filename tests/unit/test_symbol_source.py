# -*- coding: utf-8 -*-
"""اختبارات SymbolSource (T-056 / R-205).

التغطية (معايير قبول T-056):
- golden «من ينادي X؟»: مجموعة مواقع الاستدعاء الدقيقة بلا زيادة.
- تعريفات X عبر الملفات + سياق استيرادات الملف المذكور.
- تدهور: ملف بلا رموز ⇒ SymbolSource صامت والتركيبة تكافئ سلوك
  keyword حرفيًا (نفس mentioned_files مع/بدون المصدر).
- امتثال الطبقات: عناصر الرموز بطبقة high — must_have لا يُزاح أبدًا.
- تسجيل المصدر في تركيبة المحرّك القياسية (facade).
- طزاجة stat-guard: تعديل ملف بين رسالتين يظهر في الرموز.
- لا مشي شجري (عقد AUTHORING.md).
"""
from __future__ import annotations

import pathlib

import pytest

from context.budget import BudgetItem, ContextBudget
from context.engine import ContextEngine, ContextRequest, ProjectScan
from context.facade import _default_engine, gather_message_context
from context.sources.symbol import (
    MAX_SYMBOL_ITEMS,
    SYMBOL_TIER,
    SymbolSource,
    reset_symbol_state,
)
from context.symbol_index import SymbolIndex

requires_grammars = pytest.mark.skipif(
    not SymbolIndex.available(),
    reason="tree-sitter grammars not installed (optional dependency)",
)


@pytest.fixture(autouse=True)
def _isolate_symbol_state():
    """عزل الحالة المشتركة (module-level) بين الاختبارات."""
    reset_symbol_state()
    yield
    reset_symbol_state()


def _collect(root: pathlib.Path, message: str):
    src = SymbolSource()
    return src.collect(
        ContextRequest(message=message, project_root=root),
        ProjectScan(root))


# ═══════════════════ goldens: تعريف/مستدعون/استيرادات ═══════════════════

@requires_grammars
class TestFindUsagesGolden:
    """معيار قبول T-056: «من ينادي X؟» يعيد مجموعة المواقع الدقيقة."""

    def test_callers_exact_call_site_set(self, tmp_path):
        (tmp_path / "a.py").write_text(
            "def process():\n    pass\n", encoding="utf-8")
        (tmp_path / "b.py").write_text(
            "def x():\n    process()\n", encoding="utf-8")
        (tmp_path / "c.py").write_text(
            "def y():\n    pass\n\ndef z():\n    process()\n",
            encoding="utf-8")
        (tmp_path / "d.py").write_text(
            "def unrelated():\n    other()\n", encoding="utf-8")

        items = _collect(tmp_path, "who calls process function?")
        callers = [it for it in items
                   if it.path == "<symbol:callers:process>"]
        assert len(callers) == 1
        # المجموعة الدقيقة: b.py:2 و c.py:5 — لا d.py ولا تعريف a.py
        assert callers[0].content == "b.py:2\nc.py:5"

    def test_definition_locations(self, tmp_path):
        (tmp_path / "svc.py").write_text(
            "class UserService:\n    pass\n", encoding="utf-8")
        items = _collect(tmp_path, "explain UserService please")
        defs = [it for it in items
                if it.path == "<symbol:definition:UserService>"]
        assert len(defs) == 1
        assert defs[0].content == "svc.py:1 class UserService"

    def test_imports_context_for_mentioned_file(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "import os\nfrom pkg.mod import thing\n", encoding="utf-8")
        items = _collect(tmp_path, "refactor app.py")
        imports = [it for it in items
                   if it.path == "<symbol:imports:app.py>"]
        assert len(imports) == 1
        assert imports[0].content == "os\npkg.mod"

    def test_provenance_and_determinism(self, tmp_path):
        (tmp_path / "m.py").write_text("def alpha():\n    beta()\n",
                                       encoding="utf-8")
        first = _collect(tmp_path, "alpha beta")
        second = _collect(tmp_path, "alpha beta")
        assert [ (i.path, i.content) for i in first ] == \
               [ (i.path, i.content) for i in second ]
        assert all(i.source_kind == "symbol" for i in first)

    def test_max_items_cap_is_honest(self, tmp_path):
        for i in range(30):
            (tmp_path / f"f{i:02d}.py").write_text(
                f"def sym{i:02d}():\n    pass\n", encoding="utf-8")
        msg = " ".join(f"sym{i:02d}" for i in range(30))
        items = _collect(tmp_path, msg)
        assert len(items) <= MAX_SYMBOL_ITEMS


# ═══════════════════ التدهور = سلوك keyword ═══════════════════

class TestDegradation:
    """معيار قبول: ملف بلا رموز ⇒ التركيبة تكافئ سلوك keyword."""

    def test_unparsed_file_source_stays_silent(self, tmp_path):
        (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")
        (tmp_path / "data.bin").write_bytes(b"\x00")
        items = _collect(tmp_path, "check notes.txt and data please")
        assert items == []                      # صمت — لا ضجيج بديل

    @requires_grammars
    def test_facade_mentioned_files_unchanged_by_symbol_source(
            self, tmp_path):
        """نفس mentioned_files مع/بدون SymbolSource — fallback حرفي."""
        (tmp_path / "index.html").write_text("<div id='a'></div>",
                                             encoding="utf-8")
        (tmp_path / "style.css").write_text(".a { top: 0 }",
                                            encoding="utf-8")
        msg = "update index.html and style"
        with_symbol = gather_message_context(tmp_path, msg)
        reset_symbol_state()
        from context.sources.keyword import KeywordSource
        from context.sources.mention import MentionSource
        from context.sources.structure import StructureSource
        without = gather_message_context(tmp_path, msg, engine=ContextEngine(
            [MentionSource(), KeywordSource(), StructureSource()]))
        assert with_symbol.mentioned_files == without.mentioned_files
        assert with_symbol.user_text_with_files == \
            without.user_text_with_files

    def test_missing_grammars_returns_empty(self, tmp_path, monkeypatch):
        (tmp_path / "a.py").write_text("def f(): pass", encoding="utf-8")
        monkeypatch.setattr(SymbolIndex, "available",
                            staticmethod(lambda: False))
        assert _collect(tmp_path, "f a.py") == []


# ═══════════════════ امتثال الطبقات ═══════════════════

@requires_grammars
class TestTierCompliance:
    """معيار قبول: high tier — must_have لا يُزاح أبدًا."""

    def test_symbol_tier_is_high(self):
        assert SYMBOL_TIER == "high"

    def test_must_have_never_displaced_by_symbol_items(self, tmp_path):
        (tmp_path / "big.py").write_text(
            "\n".join(f"def fn{i}():\n    pass" for i in range(50)),
            encoding="utf-8")
        items = _collect(tmp_path, "fn0 fn1 fn2 fn3 big.py")
        assert items                            # فيه عناصر رموز فعلًا

        budget_items = [
            BudgetItem("user_request", "the actual user request",
                       tier="must_have"),
        ] + [
            BudgetItem(it.path, (it.content or "") * 50, tier=SYMBOL_TIER)
            for it in items
        ]
        packed = ContextBudget(model_window=30).pack(budget_items)
        kept_keys = {it.key for it in packed.kept}
        assert "user_request" in kept_keys       # must_have باقٍ دائمًا
        dropped_keys = {d.key for d in packed.dropped}
        assert "user_request" not in dropped_keys


# ═══════════════════ التسجيل في المحرّك ═══════════════════

class TestEngineRegistration:
    def test_default_engine_includes_symbol_source(self):
        kinds = [s.kind for s in _default_engine().sources]
        assert "symbol" in kinds
        # الترتيب: بعد keyword وقبل structure (وثيقة التركيبة)
        assert kinds.index("keyword") < kinds.index("symbol") \
            < kinds.index("structure")

    def test_sources_package_exports_symbol_source(self):
        from context.sources import SymbolSource as exported
        assert exported is SymbolSource


# ═══════════════════ الطزاجة + عقد AUTHORING ═══════════════════

@requires_grammars
class TestFreshnessAndContract:
    def test_stat_guard_picks_up_file_edit_between_messages(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def old_name():\n    pass\n", encoding="utf-8")
        assert any(it.path == "<symbol:definition:old_name>"
                   for it in _collect(tmp_path, "old_name new_name"))
        import os
        f.write_text("def new_name():\n    pass\n", encoding="utf-8")
        st = f.stat()
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
        items = _collect(tmp_path, "old_name new_name")
        assert any(it.path == "<symbol:definition:new_name>"
                   for it in items)
        assert not any(it.path == "<symbol:definition:old_name>"
                       for it in items)

    def test_deleted_file_drops_out(self, tmp_path):
        f = tmp_path / "gone.py"
        f.write_text("def vanish():\n    pass\n", encoding="utf-8")
        assert any(it.path == "<symbol:definition:vanish>"
                   for it in _collect(tmp_path, "vanish"))
        f.unlink()
        assert _collect(tmp_path, "vanish") == []

    def test_no_tree_walk(self, tmp_path, monkeypatch):
        """المصدر يعمل على scan.files فقط — أي rglob داخله = فشل."""
        (tmp_path / "a.py").write_text("def f(): pass", encoding="utf-8")
        scan = ProjectScan(tmp_path)            # المسح قبل الفخ

        def _boom(self, pattern):
            raise AssertionError(f"source walked the tree: rglob({pattern!r})")
        monkeypatch.setattr(pathlib.Path, "rglob", _boom)

        SymbolSource().collect(
            ContextRequest(message="f a.py", project_root=tmp_path), scan)

    def test_collect_never_raises_on_weird_input(self, tmp_path):
        _collect(tmp_path, "")                  # رسالة فارغة
        _collect(tmp_path, "€€€ 🎉 \\\\ ..")      # رموز غريبة — لا استثناء
