"""T-060 (R-905) — طبقة توكنز التصميم + ثيمات Dark/Light.

يتحقق من:
  1. صفر ألوان خام خارج static/themes/ (نفس بوابة check.sh — هنا كوحدة).
  2. تكافؤ التوكنز: light.css يعرّف نفس مجموعة توكنز dark.css كاملة —
     إضافة ثيم = ملف بيانات، ولا يجوز أن ينقص توكنًا فيسقط للوحة الأخرى.
  3. regression: قيم اللوحة الداكنة مطابقة لما قبل الترحيل (snapshot).
  4. سكربت الـ bootstrap في index.html يضبط data-theme قبل أول
     stylesheet (لا FOUC) ويحترم prefers-color-scheme و localStorage.
  5. tokens.css بنيوية فقط — لا يعرّف ألوانًا خامًا (الألوان في اللوحات).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "static" / "themes"

RAW_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
TOKEN_DEF = re.compile(r"^\s*(--[\w-]+)\s*:", re.MULTILINE)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _defined_tokens(css: str) -> set[str]:
    return set(TOKEN_DEF.findall(css))


class TestColorLint:
    """بوابة "صفر ألوان خام" — مرآة اختبارية لبوابة check.sh."""

    def test_no_raw_colors_outside_themes(self) -> None:
        offenders: list[str] = []
        for base in (ROOT / "static", ROOT / "public"):
            for path in base.rglob("*"):
                if path.suffix not in (".css", ".html", ".js"):
                    continue
                if THEMES in path.parents:
                    continue
                for i, line in enumerate(_read(path).splitlines(), 1):
                    if RAW_COLOR.search(line):
                        offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
        assert not offenders, "\n".join(offenders)

    def test_tokens_css_is_structural_only(self) -> None:
        # tokens.css = بنيوية + aliases — الألوان الخام في ملفات اللوحات فقط.
        assert not RAW_COLOR.search(_read(THEMES / "tokens.css"))


class TestTokenParity:
    """كل ثيم يعرّف نفس مجموعة التوكنز — لا سقوط صامت للوحة الأخرى."""

    def test_light_defines_every_dark_token(self) -> None:
        dark = _defined_tokens(_read(THEMES / "dark.css"))
        light = _defined_tokens(_read(THEMES / "light.css"))
        assert dark, "dark.css بلا توكنز؟"
        missing = dark - light
        extra = light - dark
        assert not missing, f"light.css ينقصه: {sorted(missing)}"
        assert not extra, f"light.css يزيد بـ: {sorted(extra)}"

    def test_style_css_consumes_only_defined_tokens(self) -> None:
        defined = (
            _defined_tokens(_read(THEMES / "tokens.css"))
            | _defined_tokens(_read(THEMES / "dark.css"))
        )
        style = _read(ROOT / "static" / "style.css")
        defined |= _defined_tokens(style)  # توكنز محلية للمكوّنات إن وُجدت
        used = set(re.findall(r"var\((--[\w-]+)", style))
        undefined = used - defined
        assert not undefined, f"توكنز مستهلكة غير معرّفة: {sorted(undefined)}"


class TestDarkRegression:
    """قيم dark مطابقة لما قبل الترحيل — snapshot حرفي للوحة الأصلية."""

    EXPECTED = {
        "--bg-base": "#0d0d12",
        "--bg-surface": "#111117",
        "--bg-overlay": "#08080c",
        "--bg-mantle": "#0a0a10",
        "--bg-crust": "#060609",
        "--surface-0": "#1a1a24",
        "--surface-1": "#252530",
        "--surface-2": "#32323e",
        "--text": "#e2e4f0",
        "--text-dim": "#9598ad",
        "--text-muted": "#555770",
        "--subtext": "#c0c3d8",
        "--blue": "#6ea1ff",
        "--green": "#5cff8a",
        "--red": "#ff5f7e",
        "--yellow": "#ffd866",
        "--mauve": "#bf8aff",
        "--teal": "#5cecc4",
        "--peach": "#ff9e64",
        "--pink": "#ff7eb6",
        "--sky": "#6ad7f9",
        "--lavender": "#9faeff",
        "--flamingo": "#ff9ebc",
    }

    def test_dark_palette_matches_premigration_values(self) -> None:
        css = _read(THEMES / "dark.css")
        for token, value in self.EXPECTED.items():
            m = re.search(rf"{re.escape(token)}\s*:\s*([^;]+);", css)
            assert m, f"{token} غير معرّف في dark.css"
            assert m.group(1).strip() == value, (
                f"{token}: {m.group(1).strip()!r} != {value!r}"
            )

    def test_dark_is_default_without_attribute(self) -> None:
        # اللوحة الداكنة تُطبّق على :root بلا سمة (الافتراضي للمستخدمين الحاليين).
        css = _read(THEMES / "dark.css")
        assert re.search(r":root\s*,", css), "dark.css يجب أن يستهدف :root افتراضيًا"

    def test_functional_aliases_present(self) -> None:
        tokens = _read(THEMES / "tokens.css")
        for alias in ("--accent", "--success", "--error", "--warning",
                      "--syntax-keyword", "--syntax-string", "--syntax-comment",
                      "--diff-add-fg", "--diff-del-fg"):
            assert f"{alias}:" in tokens, f"{alias} غائب من tokens.css"


class TestBootstrap:
    """index.html: ضبط data-theme قبل أول paint — لا FOUC."""

    @pytest.fixture()
    def html(self) -> str:
        return _read(ROOT / "static" / "index.html")

    def test_bootstrap_runs_before_first_stylesheet(self, html: str) -> None:
        script_pos = html.index('data-theme')
        first_css = html.index('rel="stylesheet"')
        assert script_pos < first_css, "سكربت الثيم يجب أن يسبق أول stylesheet"

    def test_bootstrap_reads_localstorage_then_media_query(self, html: str) -> None:
        assert "webdev-ai-theme" in html
        assert "prefers-color-scheme" in html

    def test_theme_stylesheets_linked_in_order(self, html: str) -> None:
        i_tokens = html.index("themes/tokens.css")
        i_dark = html.index("themes/dark.css")
        i_light = html.index("themes/light.css")
        i_style = html.index("/static/style.css")
        assert i_tokens < i_dark < i_light < i_style


class TestPrefersColorScheme:
    """اللوحات تعلن color-scheme الصحيح للمتصفح."""

    def test_color_scheme_declared(self) -> None:
        assert "color-scheme: dark" in _read(THEMES / "dark.css")
        assert "color-scheme: light" in _read(THEMES / "light.css")
