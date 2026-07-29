#!/usr/bin/env python3
"""TSK-605/TF-04 (Session 83) — one-shot v25 tokenization transform.

Adds --v25-*/--tango-* tokens (identical values, all 4 themes) and
rewrites static/style.css + static/index.html to consume var()/color-mix.
Behavior-preserving: same computed colors (see §TSK-605 pre-checks).
This script is a build-time migration tool, run once; kept for audit.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = ROOT / "static" / "themes"

# ── Token block (identical in all 4 themes — v25 palette is not
#    theme-aware today; making it so = product design decision, not taken) ──
NEW_TOKENS = """
    /* ── v25 redesign palette — TSK-605/TF-04 (S83): tokenized from
       raw literals in style.css/index.html; same values in every theme
       (behavior preservation — v25 sections were never theme-aware) ── */
    --v25-bg-deep: #090910;
    --v25-bg-panel: #0d0d14;
    --v25-bg-raised: #11111a;
    --v25-bg-input: #11111b;
    --v25-bg-header: #161624;
    --v25-bg-elevated: #181824;
    --v25-slate-900: #0f172a;
    --v25-slate-600: #475569;
    --v25-slate-500: #64748b;
    --v25-slate-400: #94a3b8;
    --v25-slate-300: #cbd5e1;
    --v25-slate-200: #e2e8f0;
    --v25-slate-100: #f1f5f9;
    --v25-slate-50: #f8fafc;
    --v25-purple: #8b5cf6;
    --v25-purple-light: #a78bfa;
    --v25-purple-bright: #c084fc;
    --v25-purple-vivid: #a855f7;
    --v25-cyan: #38bdf8;
    --v25-cyan-deep: #06b6d4;
    --v25-green: #10b981;
    --v25-green-light: #6ee7b7;
    --v25-danger: #c0392b;
    --v25-danger-hover: #e74c3c;
    --v25-white: #ffffff;
    --v25-black: #000000;

    /* ── Tango palette — terminal notification gradients (14%/35%) ── */
    --tango-green-dark: #4e9a06;
    --tango-blue: #3465a4;
    --tango-blue-light: #729fcf;
    --tango-blue-dark: #204a87;
    --tango-yellow: #edd400;
    --tango-yellow-light: #fce94f;
    --tango-orange-light: #fcaf3e;
    --tango-orange-dark: #e2491f;
    --tango-plum: #75507b;
    --tango-plum-light: #ad7fa8;
    --tango-plum-dark: #5c3566;
"""

# rgb triple -> token (for rgba(...) -> color-mix conversion)
RGB_TO_TOKEN = {
    (255, 255, 255): "--v25-white",
    (0, 0, 0): "--v25-black",
    (139, 92, 246): "--v25-purple",
    (168, 85, 247): "--v25-purple-vivid",
    (16, 185, 129): "--v25-green",
    (6, 182, 212): "--v25-cyan-deep",
    (78, 154, 6): "--tango-green-dark",
    (52, 101, 164): "--tango-blue",
    (114, 159, 207): "--tango-blue-light",
    (32, 74, 135): "--tango-blue-dark",
    (252, 233, 79): "--tango-yellow-light",
    (237, 212, 0): "--tango-yellow",
    (252, 175, 62): "--tango-orange-light",
    (226, 73, 31): "--tango-orange-dark",
    (173, 127, 168): "--tango-plum-light",
    (92, 53, 102): "--tango-plum-dark",
    (117, 80, 123): "--tango-plum",
}

# hex literal -> token (longest first at replace time)
HEX_TO_TOKEN = {
    "#090910": "--v25-bg-deep",
    "#0d0d14": "--v25-bg-panel",
    "#11111a": "--v25-bg-raised",
    "#11111b": "--v25-bg-input",
    "#161624": "--v25-bg-header",
    "#181824": "--v25-bg-elevated",
    "#0f172a": "--v25-slate-900",
    "#475569": "--v25-slate-600",
    "#64748b": "--v25-slate-500",
    "#94a3b8": "--v25-slate-400",
    "#cbd5e1": "--v25-slate-300",
    "#e2e8f0": "--v25-slate-200",
    "#f1f5f9": "--v25-slate-100",
    "#f8fafc": "--v25-slate-50",
    "#a78bfa": "--v25-purple-light",
    "#c084fc": "--v25-purple-bright",
    "#38bdf8": "--v25-cyan",
    "#10b981": "--v25-green",
    "#6ee7b7": "--v25-green-light",
    "#c0392b": "--v25-danger",
    "#e74c3c": "--v25-danger-hover",
    "#ffffff": "--v25-white",
    "#fff": "--v25-white",
}

RGBA_RE = re.compile(
    r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(0?\.\d+|1|0)\s*\)"
)


def rgba_sub(m: re.Match[str]) -> str:
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    alpha = float(m.group(4))
    token = RGB_TO_TOKEN.get((r, g, b))
    assert token, f"unmapped rgba base: {m.group(0)}"
    pct = alpha * 100
    assert abs(pct - round(pct)) < 1e-9, f"non-integer alpha: {m.group(0)}"
    return f"color-mix(in srgb, var({token}) {round(pct)}%, transparent)"


def main() -> None:
    # 1) theme files — append token block inside the closing brace
    for name in ("dark", "light", "high-contrast", "monokai"):
        p = THEMES / f"{name}.css"
        css = p.read_text(encoding="utf-8")
        assert css.rstrip().endswith("}"), name
        idx = css.rstrip().rfind("}")
        css = css.rstrip()[:idx] + NEW_TOKENS + "}\n"
        p.write_text(css, encoding="utf-8")

    # 2) style.css
    sp = ROOT / "static" / "style.css"
    style = sp.read_text(encoding="utf-8")
    # dead fallbacks: var(--accent, #7c6af7) -> var(--accent)
    n_fb = style.count("var(--accent, #7c6af7)")
    style = style.replace("var(--accent, #7c6af7)", "var(--accent)")
    assert "#7c6af7" not in style, "non-fallback #7c6af7 remains"
    # rgba -> color-mix
    style = RGBA_RE.sub(rgba_sub, style)
    # hex -> var() (longest keys first so #fff doesn't eat #ffffff)
    for hx in sorted(HEX_TO_TOKEN, key=len, reverse=True):
        style = re.sub(
            re.escape(hx) + r"\b", f"var({HEX_TO_TOKEN[hx]})", style
        )
    sp.write_text(style, encoding="utf-8")
    print(f"style.css: {n_fb} dead fallbacks removed")

    # 3) index.html — SVG gradient stops: attribute -> style var
    hp = ROOT / "static" / "index.html"
    html = hp.read_text(encoding="utf-8")
    html = html.replace(
        'stop-color="#8b5cf6"', 'style="stop-color:var(--v25-purple)"'
    ).replace(
        'stop-color="#06b6d4"', 'style="stop-color:var(--v25-cyan-deep)"'
    )
    hp.write_text(html, encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
