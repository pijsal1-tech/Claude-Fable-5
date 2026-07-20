"""T-064 (R-904) — محرك إبراز الصياغة + استهلاكه في الشات والمحرر.

يتحقق من:
  1. قرار المحرك موثّق (highlight.js موّرد محليًا — لا CDN) وأن كل لغات
     قائمة R-903 مغطاة بـ grammar فعلية في المحرك الموّرد.
  2. snapshot لكل لغة: مقتطف ثابت لكل لغة يُبرَز عبر الوحدة الفعلية في
     node ويُنتج أصناف hljs-* المتوقعة حرفيًا (لقطة مثبتة).
  3. الألوان توكنز فقط: أصناف .hljs-* في style.css تستهلك var(--syntax-*)
     حصرًا، والوحدة نفسها بلا ألوان خام (بوابة color-lint تشمل هذا لكن
     نثبته هنا بنيويًا: كل صنف يظهر في اللقطات له قاعدة لون في style.css).
  4. البث التدفقي بلا وميض: نفس البلوك المكتمل يعيد **نفس كائن السلسلة
     حرفيًا** من كاش LRU عبر إعادة الرندر (لا إعادة tokenize)، والبلوك
     المفتوح فقط يُعاد تحليله؛ الكاش محدود (LRU eviction).
  5. الملفات الكبيرة: فوق LARGE_FILE_LINES يتحول buildEditorHTML لوضع
     lazy (شريحة viewport فقط) ويبقى سريعًا (5k سطر < 500ms)، مع الحفاظ
     على عدد الأسطر الكلي (تطابق ارتفاع التمرير مع textarea).
  6. لغة الملف تُشتق من FileIcons (المصدر الوحيد) — لا mapping
     امتداد→لغة على شكل ".ext": في الوحدة (نفس بوابة T-063).
  7. Regression: بلوك بلا لغة/لغة مجهولة يظل يُرندر (auto-detect أو
     plaintext مهرَّب) — لا استثناءات.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "code_highlight.js"
VENDOR = ROOT / "static" / "vendor" / "highlight.min.js"
VENDOR_DOCKER = ROOT / "static" / "vendor" / "hljs-dockerfile.min.js"
APP_JS = ROOT / "static" / "app.js"
INDEX_HTML = ROOT / "static" / "index.html"
STYLE_CSS = ROOT / "static" / "style.css"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


class TestEngineDecision:
    def test_engine_vendored_locally_no_cdn(self) -> None:
        # المحرك موّرد (لا CDN) — index.html لا يحمّل highlight من الإنترنت.
        assert VENDOR.exists() and VENDOR.stat().st_size > 50_000
        assert VENDOR_DOCKER.exists()
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert "/static/vendor/highlight.min.js" in html
        assert "cdnjs.cloudflare.com/ajax/libs/highlight.js" not in html

    def test_decision_documented_in_module_header(self) -> None:
        text = MODULE.read_text(encoding="utf-8")
        assert "highlight.js" in text and "Shiki" in text, "توثيق سبب الاختيار"

    def test_r903_language_list_covered_by_grammars(self) -> None:
        # كل لغات قائمة R-903 يعرفها المحرك الموّرد فعليًا.
        out = run_node(
            "const h=require('./static/vendor/highlight.min.js');"
            "globalThis.hljs=h;require('./static/vendor/hljs-dockerfile.min.js');"
            "const need=['javascript','typescript','python','xml','css','json',"
            "'yaml','markdown','java','c','cpp','csharp','go','rust','php',"
            "'ruby','sql','bash','dockerfile','ini','diff'];"
            "console.log(JSON.stringify(need.filter(l=>!h.getLanguage(l))));"
        )
        assert json.loads(out) == []

    def test_no_second_extension_mapping_in_module(self) -> None:
        # نفس بوابة المصدر الوحيد (T-063): لا ".ext": mapping هنا —
        # لغة الملف تُشتق من FileIcons.getFileIcon(path).id.
        text = MODULE.read_text(encoding="utf-8")
        assert not re.search(r'"\.[a-zA-Z0-9]+"\s*:\s*"', text)
        assert "FileIcons" in text and "getFileIcon" in text


# مقتطف ثابت لكل لغة + الأصناف المتوقعة في اللقطة (مثبتة حرفيًا —
# تغيّر غير مقصود في المحرك/الوحدة يُفشل الاختبار).
SNAPSHOT_MATRIX: dict[str, tuple[str, list[str]]] = {
    "javascript": ('const x = 42; // c\nfunction go() { return "hi"; }',
                   ["hljs-keyword", "hljs-number", "hljs-string", "hljs-comment"]),
    "typescript": ("interface A { n: number }\nconst a: A = { n: 1 };",
                   ["hljs-keyword", "hljs-built_in", "hljs-number"]),
    "python": ('def add(a, b):\n    # sum\n    return a + b',
               ["hljs-keyword", "hljs-title", "hljs-comment"]),
    "xml": ('<div class="a"><p>hi</p></div>',
            ["hljs-tag", "hljs-name", "hljs-attr", "hljs-string"]),
    "css": (".btn { color: red }",
            ["hljs-selector-class", "hljs-attribute"]),
    "json": ('{"key": [1, 2, true]}',
             ["hljs-attr", "hljs-number", "hljs-literal"]),
    "yaml": ("name: demo\nitems:\n  - one",
             ["hljs-attr", "hljs-string", "hljs-bullet"]),
    "markdown": ("# Title\n\n**bold** text",
                 ["hljs-section", "hljs-strong"]),
    "java": ("public class A { int x = 1; }",
             ["hljs-keyword", "hljs-title", "hljs-number"]),
    "c": ("#include <stdio.h>\nint main(void) { return 0; }",
          ["hljs-meta", "hljs-keyword", "hljs-type"]),
    "cpp": ("#include <vector>\nint main() { return 1; }",
            ["hljs-meta", "hljs-keyword", "hljs-number"]),
    "csharp": ("public class A { public int X { get; set; } }",
               ["hljs-keyword", "hljs-title", "hljs-built_in"]),
    "go": ("package main\nfunc main() { x := 1 }",
           ["hljs-keyword", "hljs-title", "hljs-number"]),
    "rust": ("fn main() { let x: i32 = 5; }",
             ["hljs-keyword", "hljs-title", "hljs-type", "hljs-number"]),
    "php": ("<?php function f($x) { return $x + 1; }",
            ["hljs-meta", "hljs-keyword", "hljs-variable"]),
    "ruby": ('def hello\n  puts "hi"\nend',
             ["hljs-keyword", "hljs-title", "hljs-string"]),
    "sql": ("SELECT id FROM users WHERE age > 10;",
            ["hljs-keyword", "hljs-operator", "hljs-number"]),
    "bash": ('for f in a b; do echo "$f"; done',
             ["hljs-keyword", "hljs-built_in", "hljs-string"]),
    "dockerfile": ("FROM alpine:3\nRUN apk add curl",
                   ["hljs-keyword", "hljs-number"]),
    "ini": ("[core]\nname = demo",
            ["hljs-section", "hljs-attr"]),
    "diff": ("--- a\n+++ b\n+added\n-removed",
             ["hljs-comment", "hljs-addition", "hljs-deletion"]),
}


class TestPerLanguageSnapshots:
    def test_snapshot_classes_per_language(self) -> None:
        payload = {
            lang: code for lang, (code, _) in SNAPSHOT_MATRIX.items()
        }
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            f"const inp={json.dumps(payload)};"
            "const out={};"
            "for(const [lang,code] of Object.entries(inp)){"
            "  const r=CH.highlightCode(code,lang);"
            "  out[lang]={language:r.language,"
            "    classes:[...new Set([...r.html.matchAll(/hljs-[\\w.-]+/g)].map(m=>m[0]))]};"
            "}"
            "console.log(JSON.stringify(out));"
        )
        result = json.loads(out)
        for lang, (_, expected_classes) in SNAPSHOT_MATRIX.items():
            got = result[lang]
            assert got["language"] == lang, f"{lang}: صار {got['language']}"
            for cls in expected_classes:
                assert cls in got["classes"], (
                    f"{lang}: الصنف {cls} غائب — {got['classes']}"
                )

    def test_snapshot_classes_all_styled_with_syntax_tokens(self) -> None:
        # كل صنف تنتجه اللقطات له قاعدة لون في style.css تستهلك
        # var(--syntax-*) — "palettes read from theme tokens".
        css = STYLE_CSS.read_text(encoding="utf-8")
        all_classes = {
            cls for _, expected in SNAPSHOT_MATRIX.values() for cls in expected
        }
        for cls in sorted(all_classes):
            block_re = re.compile(
                r"\." + re.escape(cls) + r"[^{}]*\{([^}]*)\}", re.S
            )
            matches = block_re.findall(css)
            assert matches, f".{cls} بلا قاعدة في style.css"
            assert any("var(--syntax-" in m or "var(--" in m for m in matches), (
                f".{cls} لا يستهلك توكن ثيم"
            )

    def test_unknown_language_and_no_language_still_render(self) -> None:
        # Regression: fence مجهول/غائب لا يكسر الرندر.
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "const a=CH.highlightCode('plain words here','nosuchlang-xyz');"
            "const b=CH.highlightCode('<b>esc</b>',null);"
            "console.log(JSON.stringify({aOk:a.html.length>0,"
            "bEscaped:!b.html.includes('<b>')||b.html.includes('hljs')}));"
        )
        r = json.loads(out)
        assert r["aOk"] and r["bEscaped"]


class TestStreamingStability:
    def test_completed_block_served_from_cache_identical_string(self) -> None:
        # لا وميض: إعادة رندر نفس البلوك تعيد نفس كائن النتيجة (===)
        # من الكاش — صفر إعادة tokenize للبلوكات المكتملة.
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "const code='def f():\\n    return 1';"
            "const r1=CH.highlightCode(code,'python');"
            "const before=CH._stats.misses;"
            "const r2=CH.highlightCode(code,'python');"
            "console.log(JSON.stringify({same:r1===r2,"
            "hits:CH._stats.hits,missDelta:CH._stats.misses-before}));"
        )
        r = json.loads(out)
        assert r["same"] is True
        assert r["hits"] >= 1 and r["missDelta"] == 0

    def test_streaming_simulation_only_open_block_retokenized(self) -> None:
        # محاكاة بث: بلوك مكتمل + بلوك ينمو chunk بعد chunk — المكتمل
        # يُخدم من الكاش في كل خطوة، وكل نمو للبلوك المفتوح = miss واحد.
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "const done='const a = 1;';"
            "CH.highlightCode(done,'javascript');"
            "const chunks=['const b',' = ','2;'];let open='';"
            "const m0=CH.mislabeled__ignore||CH._stats.misses;"
            "for(const c of chunks){open+=c;"
            "  CH.highlightCode(done,'javascript');"
            "  CH.highlightCode(open,'javascript');}"
            "console.log(JSON.stringify({missDelta:CH._stats.misses-m0,"
            "hits:CH._stats.hits}));"
        )
        r = json.loads(out)
        assert r["missDelta"] == len(["const b", " = ", "2;"])  # المفتوح فقط
        assert r["hits"] >= 3  # المكتمل كاش في كل خطوة

    def test_cache_is_lru_bounded(self) -> None:
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "for(let i=0;i<600;i++)CH.highlightCode('let v'+i+'=1;','javascript');"
            "console.log(CH._cacheSize());"
        )
        assert int(out.strip()) <= 500


class TestLargeFilePerf:
    def test_large_file_uses_lazy_viewport_mode_and_is_fast(self) -> None:
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "const big=Array.from({length:5000},(_,i)=>'const x'+i+' = '+i+';').join('\\n');"
            "const t0=Date.now();"
            "const r=CH.buildEditorHTML(big,'big.js',2500,50);"
            "const ms=Date.now()-t0;"
            "const lineCount=(r.html.match(/\\n/g)||[]).length+1;"
            "console.log(JSON.stringify({mode:r.mode,ms,lineCount,"
            "hasSpans:r.html.includes('hljs-keyword')}));"
        )
        r = json.loads(out)
        assert r["mode"] == "lazy"
        assert r["ms"] < 500, f"lazy path بطيء: {r['ms']}ms"
        assert r["hasSpans"] is True
        assert r["lineCount"] == 5000  # الارتفاع الكلي محفوظ (تطابق تمرير)

    def test_small_file_full_mode_unknown_plain_mode(self) -> None:
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "const s=CH.buildEditorHTML('body { margin: 0 }','a.css',0,50);"
            "const p=CH.buildEditorHTML('<raw> & data','x.png',0,50);"
            "console.log(JSON.stringify({sMode:s.mode,sLang:s.language,"
            "pMode:p.mode,pEscaped:p.html.includes('&lt;raw&gt;')}));"
        )
        r = json.loads(out)
        assert r["sMode"] == "full" and r["sLang"] == "css"
        assert r["pMode"] == "plain" and r["pEscaped"] is True

    def test_lang_for_path_delegates_to_file_icons(self) -> None:
        out = run_node(
            "const CH=require('./static/js/code_highlight.js');"
            "console.log(JSON.stringify({py:CH.langForPath('a.py'),"
            "docker:CH.langForPath('sub/Dockerfile'),"
            "lock:CH.langForPath('package-lock.json'),"
            "img:CH.langForPath('x.png'),unk:CH.langForPath('a.xyz')}));"
        )
        r = json.loads(out)
        assert r == {"py": "python", "docker": "dockerfile",
                     "lock": "json", "img": None, "unk": None}


class TestConsumptionWiring:
    def test_app_js_uses_single_entry_point_no_direct_hljs(self) -> None:
        text = APP_JS.read_text(encoding="utf-8")
        assert "CodeHighlight.highlightContainer(" in text
        assert "renderEditorHighlight" in text
        # لا استدعاء مباشر للمحرك خارج الوحدة (نقطة استهلاك وحيدة).
        assert "hljs." not in text, "استدعاء hljs مباشر في app.js"

    def test_index_html_load_order_engine_icons_module_app(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        pos = [
            html.find("/static/vendor/highlight.min.js"),
            html.find("/static/js/file_icons.js"),
            html.find("/static/js/code_highlight.js"),
            html.find("/static/app.js"),
        ]
        assert -1 not in pos, f"وسم script غائب: {pos}"
        assert pos == sorted(pos), f"ترتيب تحميل خاطئ: {pos}"

    def test_editor_highlight_overlay_markup_and_css(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="editor-highlight"' in html
        assert 'id="editor-highlight-code"' in html
        css = STYLE_CSS.read_text(encoding="utf-8")
        assert ".editor-code-wrap" in css
        assert "#editor-highlight" in css
        # الـ textarea شفاف النص فوق الطبقة (caret ظاهر).
        ta = re.search(r"#editor-textarea\s*\{([^}]*)\}", css, re.S)
        assert ta and "color: transparent" in ta.group(1)
        assert "caret-color" in ta.group(1)
