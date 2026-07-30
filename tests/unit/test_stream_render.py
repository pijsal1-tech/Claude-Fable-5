"""QA-T11 (جزء NF-10 / TSK-401) — بث تدريجي بدل إعادة render كاملة.

يتحقق آليًا (وحدات JS في node — نفس نمط T-064) من:
  1. الـ throttler: تجميع N طلبات → تنفيذ واحد (آخر دالة فقط)، احترام
     الحد الأدنى الزمني MIN_INTERVAL_MS، flush ينفّذ المعلّق فورًا،
     cancel يُسقطه بلا تنفيذ.
  2. الـ section memo: نفس المصدر → نفس كائن السلسلة من الكاش (صفر
     إعادة تحليل)؛ تغيّر مقطع واحد → إعادة تحليل ذلك المقطع فقط.
  3. سيناريو بث 100KB محاكى: عدد الرندرات مقيّد بعدد الأُطر الزمنية
     (O(زمن البث)) لا بعدد الـ chunks — أقل بكثير من عدد الـ chunks.
  4. wiring: app.js يستهلك StreamRender فعليًا (request في
     appendStreamChunk، cancel في finalize، إعادة إنشاء memo في start)،
     و index.html يحمّل stream_render.js **قبل** app.js.

--- سيناريو DevTools اليدوي الموثَّق (QA-T11 §1 — Accept الرسمي) ---
الخطوات (مرة واحدة عند تغيّر مسار البث):
  1. شغّل الخادم وافتح الواجهة في Chrome، افتح DevTools → تبويب
     Performance، فعّل "Web Vitals"/long tasks.
  2. ابدأ التسجيل ثم أرسل رسالة يولّد ردّها بثًا طويلًا (~100KB —
     مثلًا "اكتب شرحًا مفصلًا جدًا..." أو عبر stub بث محلي).
  3. أوقف التسجيل بعد اكتمال البث.
  4. القبول: لا مهام (Tasks) متكررة > 100ms أثناء البث في مسار
     appendStreamChunk/renderStreamContent؛ الرندر يظهر كومضات
     متباعدة ≥ MIN_INTERVAL_MS (50ms) لا كسيل متصل.
قبل TSK-401 كان كل chunk يعيد marked.parse للرد كاملًا (مئات المهام
الطويلة لبث 100KB)؛ بعده آخر طلب فقط يُنفَّذ لكل إطار والمقاطع
المغلقة تُخدم من الكاش.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "stream_render.js"
APP_JS = ROOT / "static" / "app.js"
APP_SPLIT_DIR = ROOT / "static" / "js" / "app"


def _app_bundle() -> str:
    parts = [APP_JS.read_text(encoding="utf-8")]
    for f in sorted(APP_SPLIT_DIR.glob("*.js")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)

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


# جدولة/ساعة قابلة للحقن: نتحكم بالزمن والأُطر يدويًا بلا متصفح.
HARNESS = """
const SR = require('./static/js/stream_render.js');
let t = 0;                     // ساعة افتراضية (ms)
let queue = [];                // أُطر مجدولة
let nextH = 1;
const schedule = (cb) => { const h = nextH++; queue.push([h, cb]); return h; };
const cancel = (h) => { queue = queue.filter(([qh]) => qh !== h); };
const now = () => t;
// شغّل إطارًا واحدًا مع تقدّم الزمن بمقدار dt
function frame(dt) {
    t += dt;
    const q = queue; queue = [];
    for (const [, cb] of q) cb();
}
"""


class TestThrottler:
    def test_coalesces_n_requests_into_one_last_wins(self) -> None:
        out = run_node(HARNESS + """
const th = SR.createThrottler({schedule, cancel, now});
const calls = [];
for (let i = 0; i < 200; i++) th.request(() => calls.push(i));
frame(16);
console.log(JSON.stringify(calls));
""")
        assert out.strip() == "[199]", out  # تنفيذ واحد — آخر دالة فقط

    def test_min_interval_enforced(self) -> None:
        # طلبات متلاحقة عبر أُطر 16ms: الرندر لا يتكرر قبل مرور 50ms.
        out = run_node(HARNESS + """
const th = SR.createThrottler({schedule, cancel, now});
const times = [];
for (let i = 0; i < 20; i++) {
    th.request(() => times.push(t));
    frame(16);
}
while (queue.length) frame(16);
console.log(JSON.stringify(times));
""")
        times = [float(x) for x in out.strip().strip("[]").split(",") if x]
        assert len(times) >= 2
        gaps = [b - a for a, b in zip(times, times[1:])]
        assert all(g >= 50 for g in gaps), gaps

    def test_flush_executes_pending_immediately(self) -> None:
        out = run_node(HARNESS + """
const th = SR.createThrottler({schedule, cancel, now});
let ran = 0;
th.request(() => ran++);
th.flush();                       // بلا انتظار إطار
const pendingAfter = th.hasPending();
frame(16);                        // لا شيء متبقٍ
console.log(ran, pendingAfter, queue.length);
""")
        assert out.split() == ["1", "false", "0"], out

    def test_cancel_drops_pending_without_running(self) -> None:
        out = run_node(HARNESS + """
const th = SR.createThrottler({schedule, cancel, now});
let ran = 0;
th.request(() => ran++);
th.cancel();
frame(16); frame(16);
console.log(ran, th.hasPending());
""")
        assert out.split() == ["0", "false"], out


class TestSectionMemo:
    def test_unchanged_source_served_from_cache(self) -> None:
        out = run_node(HARNESS + """
const memo = SR.createSectionMemo();
let renders = 0;
const render = (s) => { renders++; return '<p>' + s + '</p>'; };
const a = memo('result', 'ثابت', render);
const b = memo('result', 'ثابت', render);
console.log(renders, a === b);   // هوية السلسلة نفسها (صفر parse ثانٍ)
""")
        assert out.split() == ["1", "true"], out

    def test_only_changed_section_rerendered(self) -> None:
        out = run_node(HARNESS + """
const memo = SR.createSectionMemo();
const counts = {thinking: 0, result: 0};
const mk = (k) => (s) => { counts[k]++; return s; };
memo('thinking', 'فكرة مغلقة', mk('thinking'));
memo('result', 'ج', mk('result'));
// chunks جديدة تطيل المقطع المفتوح (result) فقط:
memo('thinking', 'فكرة مغلقة', mk('thinking'));
memo('result', 'جزء أطول', mk('result'));
memo('thinking', 'فكرة مغلقة', mk('thinking'));
memo('result', 'جزء أطول بعد', mk('result'));
console.log(counts.thinking, counts.result);
""")
        assert out.split() == ["1", "3"], out


class TestHundredKBStream:
    def test_render_count_bounded_by_frames_not_chunks(self) -> None:
        # بث 100KB على chunks بحجم 64B (~1600 chunk) بأُطر 16ms:
        # عدد الرندرات مقيّد بعدد فترات 50ms لا بعدد الـ chunks.
        out = run_node(HARNESS + """
const th = SR.createThrottler({schedule, cancel, now});
const memo = SR.createSectionMemo();
let parses = 0, renders = 0, buf = '';
const parse = (s) => { parses++; return s; };
const CHUNK = 'x'.repeat(64);
const N = Math.ceil((100 * 1024) / 64);
for (let i = 0; i < N; i++) {
    buf += CHUNK;
    th.request(() => { renders++; memo('plain', buf, parse); });
    if (i % 4 === 3) frame(16);   // ~4 chunks لكل إطار
}
th.flush();
console.log(N, renders, parses);
""")
        n, renders, parses = (int(x) for x in out.split())
        assert n >= 1600
        # قبل TSK-401: renders == parses == N. بعده: مقيّد بالأُطر الزمنية.
        assert renders < n / 8, (n, renders)
        assert parses == renders  # المقطع المفتوح يُعاد تحليله عند كل رندر فقط


class TestWiring:
    def test_app_js_consumes_stream_render(self) -> None:
        app = _app_bundle()
        assert "StreamRender.createThrottler()" in app
        assert "StreamRender.createSectionMemo()" in app
        assert "streamThrottler.request(" in app, "appendStreamChunk مُخنَّق"
        assert "streamThrottler.cancel()" in app, "finalize/start يُسقط المعلّق"
        assert "renderStreamContent" in app

    def test_index_loads_module_before_app_js(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod = html.index("/static/js/stream_render.js")
        app = html.index("/static/app.js")
        assert mod < app, "stream_render.js يجب أن يسبق app.js"

    def test_module_is_umd_lite_node_requireable(self) -> None:
        assert MODULE.exists()
        out = run_node(
            "const m=require('./static/js/stream_render.js');"
            "console.log(typeof m.createThrottler, typeof m.createSectionMemo,"
            " m.MIN_INTERVAL_MS);"
        )
        assert out.split() == ["function", "function", "50"], out

    def test_manual_devtools_scenario_documented(self) -> None:
        # Accept الرسمي: "سيناريو يدوي موثَّق في QA-T11" — موثَّق في
        # docstring هذا الملف بخطوات DevTools قابلة للتنفيذ.
        doc = __doc__ or ""
        assert "DevTools" in doc and "Performance" in doc
        assert "100ms" in doc and "100KB" in doc
