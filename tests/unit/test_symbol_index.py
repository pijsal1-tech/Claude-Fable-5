# -*- coding: utf-8 -*-
"""اختبارات SymbolIndex (T-055 / R-205).

التغطية:
- goldens لكل لغة (PY/JS/TS/HTML/CSS): تعريفات/مراجع/استيرادات.
- امتداد غير مدعوم ⇒ جدول فارغ بلا استثناء (معيار قبول صريح).
- ملف مفقود / ملف سري (SafeReader) ⇒ جدول فارغ مرصود، لا استثناء.
- طزاجة write-hook: notify_write يُبطل الكاش، attach يوصله بـ FM.
- سقف الأداء: بناء فهرس 2000 ملف ≤ 10s (السقف المتفق عليه —
  القياس المحلي ~1-2s؛ الهامش لعتاد CI البارد).
"""
from __future__ import annotations

import pathlib
import time

import pytest

from context.symbol_index import (
    EXTENSION_LANGUAGES,
    FileSymbols,
    Symbol,
    SymbolIndex,
)

requires_grammars = pytest.mark.skipif(
    not SymbolIndex.available(),
    reason="tree-sitter grammars not installed (optional dependency)",
)


def _names(symbols, kind=None):
    return [s.name for s in symbols if kind is None or s.kind == kind]


# ═══════════════════ goldens لكل لغة ═══════════════════

@requires_grammars
class TestPythonExtraction:
    def test_definitions_references_imports(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "import os\n"
            "import json as j\n"
            "from pkg.mod import thing\n"
            "\n"
            "class UserService:\n"
            "    def get_user(self, uid):\n"
            "        return fetch(uid)\n"
            "\n"
            "def main():\n"
            "    svc = UserService()\n"
            "    svc.get_user(1)\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("app.py")
        assert table.language == "python"
        assert table.error is None
        assert _names(table.definitions, "class") == ["UserService"]
        assert set(_names(table.definitions, "function")) == {
            "get_user", "main"}
        assert set(table.imports) == {"os", "json", "pkg.mod"}
        ref_names = _names(table.references)
        assert "fetch" in ref_names
        assert "UserService" in ref_names       # الاستدعاء البنّاء مرجع
        assert "get_user" in ref_names          # استدعاء عبر attribute

    def test_line_numbers_are_one_based(self, tmp_path):
        (tmp_path / "m.py").write_text("def first():\n    pass\n",
                                       encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("m.py")
        assert table.definitions[0] == Symbol("first", "function", 1)


@requires_grammars
class TestJavaScriptExtraction:
    def test_definitions_references_imports(self, tmp_path):
        (tmp_path / "app.js").write_text(
            "import { helper } from './utils';\n"
            "const render = () => {};\n"
            "function init() { helper(); }\n"
            "class Widget {\n"
            "  draw() { this.render(); }\n"
            "}\n"
            "const fs = require('fs');\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("app.js")
        assert table.language == "javascript"
        assert set(_names(table.definitions, "function")) == {
            "render", "init"}
        assert _names(table.definitions, "class") == ["Widget"]
        assert _names(table.definitions, "method") == ["draw"]
        assert set(table.imports) == {"./utils", "fs"}
        assert "helper" in _names(table.references)
        # require ليس مرجعًا — التُقط كاستيراد
        assert "require" not in _names(table.references)

    def test_all_js_extensions_map_to_javascript(self):
        for ext in (".js", ".mjs", ".cjs", ".jsx"):
            assert SymbolIndex.language_for(f"x{ext}") == "javascript"


@requires_grammars
class TestTypeScriptExtraction:
    def test_interfaces_and_type_aliases(self, tmp_path):
        (tmp_path / "types.ts").write_text(
            "import { Base } from './base';\n"
            "interface User { id: number }\n"
            "type Handler = (u: User) => void;\n"
            "function process(u: User): void { log(u); }\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("types.ts")
        assert table.language == "typescript"
        assert _names(table.definitions, "interface") == ["User"]
        assert _names(table.definitions, "type") == ["Handler"]
        assert _names(table.definitions, "function") == ["process"]
        assert table.imports == ("./base",)
        assert "log" in _names(table.references)

    def test_tsx_uses_tsx_grammar(self, tmp_path):
        (tmp_path / "view.tsx").write_text(
            "export function App() { return <div id=\"root\" />; }\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("view.tsx")
        assert table.language == "tsx"
        assert "App" in _names(table.definitions, "function")


@requires_grammars
class TestHtmlCssExtraction:
    def test_html_ids_and_classes(self, tmp_path):
        (tmp_path / "page.html").write_text(
            '<div id="main" class="box big">\n'
            '  <span id="title">hi</span>\n'
            "</div>\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("page.html")
        assert table.language == "html"
        assert set(_names(table.definitions, "id")) == {"main", "title"}
        assert set(_names(table.definitions, "css_class")) == {"box", "big"}

    def test_css_selectors_and_imports(self, tmp_path):
        (tmp_path / "style.css").write_text(
            '@import "base.css";\n'
            ".card { color: red; }\n"
            "#hero h1 { top: 0; }\n"
            "@media screen { .inner { left: 1px; } }\n",
            encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("style.css")
        assert table.language == "css"
        assert set(_names(table.definitions, "css_class")) == {
            "card", "inner"}
        assert _names(table.definitions, "id") == ["hero"]
        assert table.imports == ("base.css",)


# ═══════════════════ التدهور الرشيق ═══════════════════

class TestGracefulDegradation:
    """معيار قبول صريح: غير مدعوم ⇒ جدول فارغ، لا استثناء أبدًا."""

    def test_unsupported_extension_empty_table_no_exception(self, tmp_path):
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        idx = SymbolIndex(tmp_path)
        for name in ("data.bin", "notes.txt"):
            table = idx.symbols_for(name)
            assert isinstance(table, FileSymbols)
            assert table.language == ""
            assert table.empty
            assert table.error is None

    def test_missing_file_empty_table_with_reason(self, tmp_path):
        table = SymbolIndex(tmp_path).symbols_for("ghost.py")
        assert table.empty
        assert table.error == "not_found"

    @requires_grammars
    def test_secret_file_redacted_not_parsed(self, tmp_path):
        # ملف بامتداد مدعوم لكن denylist بالاسم (SafeReader R-204)
        (tmp_path / "credentials.py").write_text(
            "SECRET = 'x'\ndef leak(): pass\n", encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("credentials.py")
        assert table.empty                      # المحتوى المحجوب لا يُفهرَس
        assert table.error == "redacted"

    @requires_grammars
    def test_broken_syntax_never_raises(self, tmp_path):
        (tmp_path / "broken.py").write_text(
            "def f(:\n  ((((\nclass ", encoding="utf-8")
        table = SymbolIndex(tmp_path).symbols_for("broken.py")
        assert isinstance(table, FileSymbols)   # لا استثناء — هذا العقد

    def test_available_is_boolean(self):
        assert isinstance(SymbolIndex.available(), bool)

    def test_supported_language_matrix_documented(self):
        # وثيقة المصفوفة: كل الامتدادات المعلنة تحل للغة معروفة
        for ext, lang in EXTENSION_LANGUAGES.items():
            assert SymbolIndex.language_for(f"f{ext}") == lang
        assert SymbolIndex.language_for("f.unknown") == ""


# ═══════════════════ الطزاجة (write-hook) ═══════════════════

@requires_grammars
class TestWriteHookFreshness:
    def test_notify_write_invalidates_cache(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def old(): pass\n", encoding="utf-8")
        idx = SymbolIndex(tmp_path)
        assert _names(idx.symbols_for("mod.py").definitions) == ["old"]
        f.write_text("def new(): pass\n", encoding="utf-8")
        # بلا إبطال: الكاش يخدم القديم (كسول بالتصميم)
        assert _names(idx.symbols_for("mod.py").definitions) == ["old"]
        idx.notify_write("mod.py")
        assert _names(idx.symbols_for("mod.py").definitions) == ["new"]

    def test_attach_registers_hook_on_file_manager(self, tmp_path):
        class FakeFM:
            def __init__(self):
                self.hooks = []

            def add_write_hook(self, fn):
                self.hooks.append(fn)

        idx = SymbolIndex(tmp_path)
        fm = FakeFM()
        idx.attach(fm)
        assert idx.notify_write in fm.hooks

    def test_attach_tolerates_fm_without_hooks(self, tmp_path):
        SymbolIndex(tmp_path).attach(object())      # لا استثناء

    def test_windows_style_paths_normalized(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "m.py").write_text("def a(): pass\n", encoding="utf-8")
        idx = SymbolIndex(tmp_path)
        idx.symbols_for("pkg/m.py")
        idx.notify_write("pkg\\m.py")               # نفس مفتاح الكاش
        assert idx.indexed_count == 0


# ═══════════════════ الاستعلام ═══════════════════

@requires_grammars
class TestLookup:
    def test_lookup_definition_across_files(self, tmp_path):
        (tmp_path / "a.py").write_text("def shared(): pass\n",
                                       encoding="utf-8")
        (tmp_path / "b.py").write_text("class Shared: pass\n"
                                       "def shared(): pass\n",
                                       encoding="utf-8")
        idx = SymbolIndex(tmp_path)
        idx.index_files(["a.py", "b.py"])
        hits = idx.lookup_definition("shared")
        assert [(p, s.kind) for p, s in hits] == [
            ("a.py", "function"), ("b.py", "function")]

    def test_lookup_references(self, tmp_path):
        (tmp_path / "u.py").write_text("def caller():\n    target()\n",
                                       encoding="utf-8")
        idx = SymbolIndex(tmp_path)
        idx.index_files(["u.py"])
        hits = idx.lookup_references("target")
        assert hits == [("u.py", Symbol("target", "call", 2))]


# ═══════════════════ سقف الأداء (2k ملف) ═══════════════════

@requires_grammars
class TestPerformanceCeiling:
    #: السقف المتفق عليه (T-055): 2000 ملف ≤ 10 ثوانٍ.
    #: القياس المحلي ~1-2s — الهامش الكبير لعتاد CI البارد
    #: (نفس فلسفة سقوف T-049: قياس سلوك لا microbenchmark هش).
    CEILING_SECONDS = 10.0
    FILE_COUNT = 2000

    def test_2k_file_index_build_under_ceiling(self, tmp_path):
        py_body = ("import os\n"
                   "class C{i}:\n"
                   "    def m{i}(self):\n"
                   "        helper{i}()\n")
        js_body = ("import {{ x }} from './dep{i}';\n"
                   "function f{i}() {{ g{i}(); }}\n")
        rel_paths = []
        for i in range(self.FILE_COUNT):
            if i % 2 == 0:
                name = f"mod_{i}.py"
                (tmp_path / name).write_text(py_body.format(i=i),
                                             encoding="utf-8")
            else:
                name = f"mod_{i}.js"
                (tmp_path / name).write_text(js_body.format(i=i),
                                             encoding="utf-8")
            rel_paths.append(name)

        idx = SymbolIndex(tmp_path)
        start = time.perf_counter()
        count = idx.index_files(rel_paths)
        elapsed = time.perf_counter() - start

        assert count == self.FILE_COUNT
        assert idx.indexed_count == self.FILE_COUNT
        assert elapsed < self.CEILING_SECONDS, (
            f"2k-file index took {elapsed:.2f}s — ceiling "
            f"{self.CEILING_SECONDS}s exceeded")
        # عيّنة صحة: الرموز فعلًا استُخرجت لا مجرد جداول فارغة
        sample = idx.symbols_for("mod_0.py")
        assert "C0" in _names(sample.definitions, "class")
        assert idx.lookup_definition("f1")[0][0] == "mod_1.js"
