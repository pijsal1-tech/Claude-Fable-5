"""QA-T11 (جزء NF-11 / TSK-402) — backoff+jitter للاتصال + حماية onmessage.

يتحقق آليًا (وحدات JS في node — نفس نمط TSK-401/T-064) من:
  1. سيناريو QA-T11 §2 — قطع الخادم → فواصل إعادة اتصال **متزايدة
     بسقف**: بلا jitter تكون 1s→2s→4s→8s→16s→30s ثم تثبت عند السقف؛
     مع jitter تبقى داخل [pure, pure*(1+ratio)) ولا تتجاوز
     السقف*(1+ratio)؛ reset() عند نجاح الاتصال يعيد البداية.
  2. سيناريو QA-T11 §3 — إطار JSON مشوّه → **log وتجاهل** بلا استثناء
     غير معالج: safeParseFrame يعيد null لكل إطار مشوّه (نص مكسور،
     مصفوفة، رقم، null) ويستدعي الـ log المحقون، ويعيد الكائن السليم
     كما هو.
  3. jitter فعلي: random مختلفة → فواصل مختلفة (لا قصف متزامن من
     تبويبات متعددة — thundering herd).
  4. wiring: app.js يستهلك WSBackoff فعليًا (createBackoff + reset في
     onopen + next في onclose + safeParseFrame في onmessage، وزوال
     JSON.parse العاري وثابت 3000ms)، و index.html يحمّل ws_backoff.js
     **قبل** app.js، والوحدة UMD-lite قابلة للـ require في node.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "ws_backoff.js"
APP_JS = ROOT / "static" / "app.js"
INDEX_HTML = ROOT / "static" / "index.html"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


REQ = "const WB = require('./static/js/ws_backoff.js');\n"


class TestBackoff:
    def test_exponential_with_cap_no_jitter(self) -> None:
        # random=0 → فواصل نقية حتمية: 1s→2s→4s→8s→16s→30s→30s→30s.
        out = run_node(REQ + """
const b = WB.createBackoff({random: () => 0});
const seq = [];
for (let i = 0; i < 8; i++) seq.push(b.next());
console.log(JSON.stringify(seq));
""")
        assert out.strip() == "[1000,2000,4000,8000,16000,30000,30000,30000]", out

    def test_delays_increase_then_plateau_at_cap_with_jitter(self) -> None:
        # مع jitter كامل (random=0.999) الفواصل داخل الحدود ولا تتجاوز
        # السقف*(1+ratio) — «فواصل متزايدة بسقف» (Accept الحرفي).
        out = run_node(REQ + """
const b = WB.createBackoff({random: () => 0.999});
const seq = [];
for (let i = 0; i < 10; i++) seq.push(b.next());
console.log(JSON.stringify(seq));
""")
        seq = [int(x) for x in out.strip().strip("[]").split(",")]
        cap_with_jitter = 30000 * (1 + 0.3)
        assert all(d <= cap_with_jitter for d in seq), seq
        pures = [min(1000 * 2 ** i, 30000) for i in range(10)]
        for d, p in zip(seq, pures):
            assert p <= d < p * 1.3 + 1, (d, p)
        # متزايدة قبل السقف:
        assert seq[0] < seq[1] < seq[2] < seq[3] < seq[4] < seq[5]

    def test_reset_on_successful_connect_restarts_ladder(self) -> None:
        out = run_node(REQ + """
const b = WB.createBackoff({random: () => 0});
b.next(); b.next(); b.next();          // 1s, 2s, 4s
b.reset();                              // onopen
console.log(b.next(), b.attempts());
""")
        assert out.split() == ["1000", "1"], out

    def test_jitter_desynchronizes_multiple_tabs(self) -> None:
        # تبويبان بنفس المرحلة لكن random مختلفة → فاصلان مختلفان
        # (كسر التزامن — لا thundering herd).
        out = run_node(REQ + """
const a = WB.createBackoff({random: () => 0.1});
const b = WB.createBackoff({random: () => 0.9});
console.log(a.next() !== b.next());
""")
        assert out.strip() == "true", out


class TestSafeParseFrame:
    def test_malformed_json_logged_and_ignored_no_throw(self) -> None:
        out = run_node(REQ + """
let logs = 0;
const log = () => logs++;
const bad = ['{not json', '', '[1,2]', '42', '"نص"', 'null'];
const results = bad.map((raw) => WB.safeParseFrame(raw, log));
console.log(results.every((r) => r === null), logs);
""")
        assert out.split() == ["true", "6"], out

    def test_valid_frame_passes_through_untouched(self) -> None:
        out = run_node(REQ + """
let logs = 0;
const d = WB.safeParseFrame('{"type":"chunk","text":"مرحبا"}', () => logs++);
console.log(d.type, d.text, logs);
""")
        assert out.split() == ["chunk", "مرحبا", "0"], out

    def test_default_log_is_noop_never_throws(self) -> None:
        # بلا log محقون — لا استثناء أيضًا.
        out = run_node(REQ + """
console.log(WB.safeParseFrame('xxx') === null);
""")
        assert out.strip() == "true", out


class TestWiring:
    def test_app_js_consumes_ws_backoff(self) -> None:
        app = APP_JS.read_text(encoding="utf-8")
        assert "WSBackoff.createBackoff()" in app
        assert "wsReconnectBackoff.reset()" in app, "reset عند onopen"
        assert "wsReconnectBackoff.next()" in app, "next عند onclose"
        assert "WSBackoff.safeParseFrame(" in app, "onmessage محمي"

    def test_bare_json_parse_and_fixed_3s_removed(self) -> None:
        app = APP_JS.read_text(encoding="utf-8")
        # لا JSON.parse عارٍ على event.data في مسار WS:
        assert "JSON.parse(event.data)" not in app
        # لا إعادة اتصال بثابت 3s:
        assert not re.search(r"setTimeout\(initWebSocket,\s*3000\)", app)

    def test_index_loads_module_before_app_js(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod = html.index("/static/js/ws_backoff.js")
        app = html.index("/static/app.js")
        assert mod < app, "ws_backoff.js يجب أن يسبق app.js"

    def test_module_is_umd_lite_node_requireable(self) -> None:
        assert MODULE.exists()
        out = run_node(
            "const m=require('./static/js/ws_backoff.js');"
            "console.log(typeof m.createBackoff, typeof m.safeParseFrame,"
            " m.BASE_DELAY_MS, m.MAX_DELAY_MS);"
        )
        assert out.split() == ["function", "function", "1000", "30000"], out
