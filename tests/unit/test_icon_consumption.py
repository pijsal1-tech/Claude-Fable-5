"""T-063 (R-903) — استهلاك getFileIcon في الشجرة/التبويبات/المرفقات.

يتحقق من:
  1. مصدر وحيد: لا يوجد أي extension→icon mapping ثانٍ في static/*.js
     خارج static/js/file_icons.js نفسها (grep عبر كل الـ .js المخدومة).
  2. الدالة المشتركة fileIconHTML() في app.js تستهلك FileIcons.getFileIcon
     فعليًا (لا تعيد تعريف الـ mapping) وتُخرج <svg><use> يشير لصنف
     sprite.svg الصحيح لكل نوع ملف — "visual snapshot" لشجرة تجريبية
     تغطي كل الأصناف المطلوبة في T-062، منفَّذة عبر node الحقيقي
     (بدون متصفح، بنفس نمط tests/unit/test_file_icons.py).
  3. نقاط الاستهلاك الثلاث المطلوبة في T-063 (tree/tabs/attachments)
     تستدعي fileIconHTML فعلاً، ولا تستخدم أيقونات إيموجي مضمّنة
     لأنواع الملفات (المجلدات مستثناة — لا تُعتبر "filenames").
  4. getFileBadgeHTML (شارات نشاط الأدوات في الشات) موجودة وموثّقة
     كخارج نطاق T-063 عن قصد — نظام مختلف تمامًا (SRC/TREE/DIR + أدوات
     بلا امتداد ملف)، وليس من ضمن tree/tabs/mentions/diff/run-history.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "app.js"
MODULE = ROOT / "static" / "js" / "file_icons.js"
SPRITE = ROOT / "static" / "icons" / "sprite.svg"
INDEX_HTML = ROOT / "static" / "index.html"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")

# كل ملفات .js المخدومة تحت static/ (تُفحص بحثًا عن mapping ثانٍ).
SERVED_JS = sorted(
    p for p in ROOT.glob("static/**/*.js") if p.is_file()
)

# نمط object-literal يربط امتداد بقيمة نصية: ".ext": "value" أو ".ext": "emoji"
# — هذا هو شكل الـ mapping الممنوع تكراره خارج file_icons.js.
EXT_MAP_LITERAL = re.compile(r'"\.[a-zA-Z0-9]+"\s*:\s*"')


class TestSingleSourceMapping:
    def test_no_second_extension_icon_mapping_outside_module(self) -> None:
        violations = []
        for path in SERVED_JS:
            if path == MODULE:
                continue
            text = path.read_text(encoding="utf-8")
            if EXT_MAP_LITERAL.search(text):
                hits = EXT_MAP_LITERAL.findall(text)
                violations.append(f"{path.relative_to(ROOT)}: {hits[:5]}")
        assert not violations, (
            "extension→icon mapping مكرر خارج file_icons.js:\n"
            + "\n".join(violations)
        )

    def test_old_duplicate_get_file_icon_function_removed(self) -> None:
        # الدالة القديمة كانت تعرّف ext→emoji محليًا في app.js — يجب أن تُحذف
        # تمامًا (الاسم القديم getFileIcon(ext) لم يعد موجودًا في app.js).
        text = APP_JS.read_text(encoding="utf-8")
        assert "function getFileIcon(" not in text
        # جسم الـ mapping القديم بالذات (امتداد → إيموجي) غير موجود —
        # نفحص التوقيعات الحرفية الفريدة لجداول الإيموجي القديمة (بعضها
        # مثل ⚡ مُستخدَم أيضًا في مكان آخر غير مرتبط، فالفحص بالتوقيع
        # الحرفي الدقيق لا بالإيموجي المفرد لتجنّب false positive).
        for old_literal in (
            '".html": "🌐"', '".css": "🎨"', '".js": "⚡"',
            '".ts": "💠"', '".py": "🐍"', '".json": "📋"',
            '".md": "📝"', '".env": "🔒"',
        ):
            assert old_literal not in text, f"توقيع mapping قديم باقٍ: {old_literal}"

    def test_app_js_consumes_file_icons_module(self) -> None:
        text = APP_JS.read_text(encoding="utf-8")
        assert "function fileIconHTML(" in text
        assert "FileIcons.getFileIcon(" in text
        # نقاط الاستهلاك الثلاث المطلوبة في T-063.
        assert re.search(r"\$\{fileIconHTML\(val\.path\)\}", text), "الشجرة (tree)"
        assert re.search(r"\$\{fileIconHTML\(t\.path\)\}", text), "التبويبات (tabs)"
        assert re.search(r"\$\{fileIconHTML\(att\.name\)\}", text), "المرفقات (attachments)"

    def test_file_icons_script_tag_loaded_before_app_js(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        icons_pos = html.find("/static/js/file_icons.js")
        app_pos = html.find("/static/app.js")
        assert icons_pos != -1, "file_icons.js غير محمَّل في index.html"
        assert app_pos != -1
        assert icons_pos < app_pos, "file_icons.js يجب أن يُحمَّل قبل app.js"

    def test_get_file_badge_html_is_intentionally_out_of_scope(self) -> None:
        # نظام منفصل بالكامل لشارات نشاط الأدوات في الشات (SRC/TREE/DIR
        # + شارات نصية قصيرة لأدوات بلا امتداد ملف) — ليس من tree/tabs/
        # mentions/diff-panel/run-history المذكورة في نطاق T-063. موجود
        # ومُبقى دون تغيير، ونؤكد هنا فقط أنه لم يُحذف بالخطأ.
        text = APP_JS.read_text(encoding="utf-8")
        assert "function getFileBadgeHTML(" in text


class TestFixtureTreeSnapshot:
    """"visual snapshot" لشجرة تجريبية تغطي كل الأصناف — عبر fileIconHTML
    الحقيقية من app.js (مستخرجة كوحدة قابلة للتشغيل في node،
    بنفس أسلوب test_file_icons.py دون حاجة لمتصفح)."""

    @staticmethod
    def _extract_file_icon_html_fn() -> str:
        text = APP_JS.read_text(encoding="utf-8")
        match = re.search(
            r"function fileIconHTML\(path\) \{.*?\n\}\n", text, re.S
        )
        assert match, "تعذّر استخراج fileIconHTML من app.js"
        return match.group(0)

    def _render(self, paths: list[str]) -> dict[str, str]:
        fn_src = self._extract_file_icon_html_fn()
        script = (
            f"global.FileIcons = require({json.dumps(str(MODULE))});"
            f"{fn_src}"
            f"const out = {{}};"
            f"for (const p of {json.dumps(paths)}) out[p] = fileIconHTML(p);"
            f"console.log(JSON.stringify(out));"
        )
        proc = subprocess.run(
            [node, "-e", script], capture_output=True, text=True, timeout=30
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    FIXTURE_TREE = [
        "src/app.js", "src/types.ts", "src/View.jsx",
        "backend/main.py", "index.html", "style.css",
        "data/config.json", "ci/config.yaml", "README.md",
        "Main.java", "lib/defs.h", "lib/impl.cpp", "Program.cs",
        "main.go", "lib.rs", "index.php", "app.rb", "schema.sql",
        "run.sh", "Dockerfile", ".env", ".gitignore",
        "logo.png", "package-lock.json", "unknown.xyz",
    ]

    def test_fixture_tree_all_types_render_expected_symbol(self) -> None:
        rendered = self._render(self.FIXTURE_TREE)
        for path in self.FIXTURE_TREE:
            html = rendered[path]
            assert "<svg class=\"file-icon\"" in html, path
            assert "<use href=\"/static/icons/sprite.svg#icon-" in html, path
            assert "style=\"color: var(--icon-" in html, path

    def test_fixture_tree_snapshot_matches_module_ids(self) -> None:
        # كل مسار في الشجرة التجريبية يجب أن يُظهر نفس id الذي تُعيده
        # FileIcons.getFileIcon() مباشرة — أي fileIconHTML لا "تخترع"
        # تصنيفًا مختلفًا، بل تعرض نفس مصدر الحقيقة الوحيد بأمانة.
        script = (
            f"const fi = require({json.dumps(str(MODULE))});"
            f"const out = {{}};"
            f"for (const p of {json.dumps(self.FIXTURE_TREE)}) "
            f"out[p] = fi.getFileIcon(p).symbol;"
            f"console.log(JSON.stringify(out));"
        )
        proc = subprocess.run(
            [node, "-e", script], capture_output=True, text=True, timeout=30
        )
        assert proc.returncode == 0, proc.stderr
        expected_symbols = json.loads(proc.stdout)

        rendered = self._render(self.FIXTURE_TREE)
        for path in self.FIXTURE_TREE:
            expected = expected_symbols[path]
            assert f'sprite.svg{expected}"' in rendered[path], (
                f"{path}: توقعنا {expected} داخل {rendered[path]!r}"
            )

    def test_fixture_tree_snapshot_stable(self) -> None:
        # لقطة (snapshot) نصية ثابتة لكل رموز الشجرة التجريبية — أي تغيير
        # غير مقصود بالـ mapping أو بشكل الـ HTML يُفشل هذا الاختبار.
        rendered = self._render(self.FIXTURE_TREE)
        symbols = {
            path: re.search(r"#icon-[\w-]+", html).group(0)
            for path, html in rendered.items()
        }
        expected = {
            "src/app.js": "#icon-js",
            "src/types.ts": "#icon-ts",
            "src/View.jsx": "#icon-jsx",
            "backend/main.py": "#icon-python",
            "index.html": "#icon-html",
            "style.css": "#icon-css",
            "data/config.json": "#icon-json",
            "ci/config.yaml": "#icon-yaml",
            "README.md": "#icon-markdown",
            "Main.java": "#icon-java",
            "lib/defs.h": "#icon-c",
            "lib/impl.cpp": "#icon-cpp",
            "Program.cs": "#icon-csharp",
            "main.go": "#icon-go",
            "lib.rs": "#icon-rust",
            "index.php": "#icon-php",
            "app.rb": "#icon-ruby",
            "schema.sql": "#icon-sql",
            "run.sh": "#icon-shell",
            "Dockerfile": "#icon-docker",
            ".env": "#icon-config",
            ".gitignore": "#icon-config",
            "logo.png": "#icon-image",
            "package-lock.json": "#icon-lock",
            "unknown.xyz": "#icon-file",
        }
        assert symbols == expected
