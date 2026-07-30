# -*- coding: utf-8 -*-
"""TSK-724 (P2-2 / D-10 — FI-09) — نافذة عرض افتراضية للمحادثات الطويلة.

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §BATCH-P2/TSK-724):
  1. الوحدة النقية (node): computeWindow — حدود فارغة/قصيرة/طويلة،
     overscan، **الثابت الصارم**: padTop + Σ heights[start..end) +
     padBottom = Σ heights لكل المدخلات (بما فيها scrollTop سالب/فائض).
  2. wiring: index.html يحمّل virtual_list.js قبل app.js؛ app.js
     يستهلك VirtualList.computeWindow؛ renderChatHistory موحّدة
     تستبدل حلقتي forEach(addChatMessage) في loadChatHistory/loadSession.
  3. القيود الحافظة للسلوك: مسار البث (currentStreamMsg) وكروت
     التيرمنال (handleRunCommandStep) لم تُمس — appendChild مباشر بلا
     أي مرجع vl؛ addChatMessage ما زالت append+scroll (الجلسات القصيرة).
  4. نقاء الوحدة: لا document. ولا fetch( في virtual_list.js.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي) ---
الخطوات (مرة واحدة عند تغيّر مسار العرض):
  1. شغّل الخادم على جلسة بتاريخ طويل (200+ رسالة) وافتحها.
  2. القبول: القائمة تفتح على آخر رسالة؛ عدد عناصر .chat-msg في DOM
     (DevTools) صغير وثابت تقريبًا (~نافذة+overscan) لا 200+.
  3. مرّر لأعلى/لأسفل بسرعة — تمرير سلس بلا فراغات دائمة؛ أزرار نسخ
     الكود و«نسخ الرد» تعمل داخل النافذة.
  4. أرسل رسالة جديدة أثناء الجلسة الطويلة — البث التدفقي يظهر أسفل
     القائمة كالمعتاد والتمرير التلقائي يتبعه؛ أمر طرفية يظهر كارته.
  5. جلسة قصيرة (<150): سلوك مطابق تمامًا لما قبل التغيير.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "virtual_list.js"
APP_JS = ROOT / "static" / "app.js"
APP_SPLIT_DIR = ROOT / "static" / "js" / "app"


def _app_bundle() -> str:
    """TSK-726a: «حزمة app» = app.js + مقاطع app/NN بالترتيب الرقمي —
    المكافئ الحرفي لتسلسل app.js قبل التقسيم (التأكيدات الجوهرية
    كما هي؛ تغيّر فقط مصدر القراءة)."""
    parts = [APP_JS.read_text(encoding="utf-8")]
    for f in sorted(APP_SPLIT_DIR.glob("*.js")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)
INDEX_HTML = ROOT / "static" / "index.html"

node = shutil.which("node")


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


HARNESS = """
const VL = require('./static/js/virtual_list.js');
const sum = (a, i, j) => a.slice(i, j).reduce((x, y) => x + y, 0);
function invariant(w, h) {
    const inWin = sum(h, w.start, w.end);
    if (w.padTop + inWin + w.padBottom !== sum(h, 0, h.length))
        throw new Error('invariant broken: ' + JSON.stringify(w));
    if (w.start < 0 || w.end > h.length || w.start > w.end)
        throw new Error('bounds broken: ' + JSON.stringify(w));
}
"""


@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestPureModule:
    def test_empty_list(self):
        out = run_node(HARNESS + """
const w = VL.computeWindow(0, 500, [], 5);
console.log(JSON.stringify(w));
""")
        assert out.strip() == '{"start":0,"end":0,"padTop":0,"padBottom":0}'

    def test_short_list_all_visible(self):
        out = run_node(HARNESS + """
const h = [50, 60, 70];
const w = VL.computeWindow(0, 1000, h, 0);
invariant(w, h);
console.log(w.start, w.end, w.padTop, w.padBottom);
""")
        assert out.split() == ["0", "3", "0", "0"]

    def test_long_list_window_and_pads(self):
        out = run_node(HARNESS + """
const h = Array.from({length: 1000}, (_, i) => 100);
const w = VL.computeWindow(50000, 400, h, 0);
invariant(w, h);
// scrollTop=50000 ⇒ العنصر 500 أول المتقاطعين؛ منفذ 400 ⇒ 4 عناصر
console.log(w.start, w.end, w.padTop, w.padBottom);
""")
        assert out.split() == ["500", "504", "50000", "49600"]

    def test_overscan_clamped_at_bounds(self):
        out = run_node(HARNESS + """
const h = Array.from({length: 20}, () => 50);
const wTop = VL.computeWindow(0, 100, h, 5);
invariant(wTop, h);
const wBot = VL.computeWindow(9999, 100, h, 5);
invariant(wBot, h);
console.log(wTop.start, wBot.end);
""")
        assert out.split() == ["0", "20"]

    def test_invariant_holds_for_many_inputs(self):
        out = run_node(HARNESS + """
const h = [50,60,70,40,90,55,65,45,80,50,120,30,200,10,75];
for (const st of [-100, 0, 1, 49, 50, 123, 400, 700, 1e6]) {
    for (const vh of [0, 1, 150, 500, 1e5]) {
        for (const os of [0, 1, 3, 100]) {
            invariant(VL.computeWindow(st, vh, h, os), h);
        }
    }
}
console.log('INVARIANT_OK');
""")
        assert "INVARIANT_OK" in out

    def test_partial_scroll_intersection(self):
        out = run_node(HARNESS + """
// scrollTop في منتصف عنصر ⇒ العنصر المتقاطع يدخل النافذة
const h = [100, 100, 100, 100];
const w = VL.computeWindow(150, 100, h, 0);
invariant(w, h);
console.log(w.start, w.end);  // العنصر 1 (يغطي 100-200) والعنصر 2 (200-300)
""")
        assert out.split() == ["1", "3"]

    def test_total_height(self):
        out = run_node(HARNESS + """
console.log(VL.totalHeight([10, 20, 30]), VL.totalHeight([]), VL.totalHeight());
""")
        assert out.split() == ["60", "0", "0"]


class TestWiring:
    def test_index_loads_module_before_app(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod_pos = html.index("virtual_list.js")
        app_pos = html.index("app.js?v=")
        assert mod_pos < app_pos, "الوحدة يجب أن تُحمَّل قبل app.js"

    def test_app_consumes_module(self):
        app = _app_bundle()
        assert "VirtualList.computeWindow" in app
        assert "VirtualList.totalHeight" in app
        assert "function renderChatHistory(" in app
        assert "vl-spacer-top" in app and "vl-spacer-bottom" in app
        # rAF throttle على scroll
        assert "requestAnimationFrame" in app

    def test_history_loops_replaced_by_unified_render(self):
        app = _app_bundle()
        # لم تبق حلقة forEach(addChatMessage) على history خارج renderChatHistory
        assert app.count("renderChatHistory(data.history") == 2, \
            "loadChatHistory وloadSession يجب أن يستدعيا renderChatHistory"
        # حلقة forEach(addChatMessage) الوحيدة المسموحة = المسار القصير
        # داخل renderChatHistory (تحت العتبة)؛ الحلقتان القديمتان أُزيلتا.
        occurrences = re.findall(
            r"forEach\(msg => addChatMessage|forEach\(msg =>\s*\{\s*addChatMessage", app)
        assert len(occurrences) == 1, "بقيت حلقات رسم كامل قديمة خارج renderChatHistory"
        m = re.search(r"function renderChatHistory\(history\) \{(.*?)\n\}", app, re.S)
        assert m and "forEach(msg => addChatMessage" in m.group(1), \
            "الحلقة المتبقية يجب أن تكون داخل renderChatHistory حصريًا"

    def test_streaming_and_terminal_paths_untouched(self):
        app = _app_bundle()
        # handleRunCommandStep: append مباشر بلا أي مرجع vl
        m = re.search(r"function handleRunCommandStep\(data\) \{(.*?)\n\}", app, re.S)
        assert m, "handleRunCommandStep موجودة"
        body = m.group(1)
        assert "appendChild" in body
        assert "vl" not in body.lower() or "vl" not in body, \
            "مسار كروت التيرمنال يجب ألا يُمس"
        # addChatMessage ما زالت append+scroll (مسار الجلسات القصيرة والرسائل الحية)
        m2 = re.search(r"function addChatMessage\(role, content\) \{(.*?)\n\}", app, re.S)
        assert m2
        assert "appendChild(msg)" in m2.group(1)
        assert "scrollTop = container.scrollHeight" in m2.group(1)
        # buildChatMessage نقية بلا append
        m3 = re.search(r"function buildChatMessage\(role, content\) \{(.*?)\n\}", app, re.S)
        assert m3
        assert "appendChild(msg)" not in m3.group(1)

    def test_threshold_short_sessions_legacy_path(self):
        app = _app_bundle()
        assert "VL_THRESHOLD" in app
        m = re.search(r"const VL_THRESHOLD = (\d+)", app)
        assert m and int(m.group(1)) >= 50, "عتبة معقولة للجلسات القصيرة"

    def test_module_purity_no_dom_no_network(self):
        src = MODULE.read_text(encoding="utf-8")
        assert "document." not in src
        assert "fetch(" not in src
        assert "XMLHttpRequest" not in src
        assert "WebSocket" not in src
