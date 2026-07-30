"""TSK-620 (CP-8/UXF-05 §R9) — سرد الجلسة.

يتحقق آليًا (وحدة JS نقية في node — نفس نمط test_plan_card) من:
  1. **القبول الحرفي**: جلسة بها run واحد معتمد (طلب → خطة → موافقة →
     تنفيذ → نتيجة) → السرد يعرض **≥ 4 محطات بترتيبها**.
  2. تصنيف الأطر: plan/approval(طلب+حكم)/execution/result/rollback؛
     الإطارات غير المعروفة تعيد false بلا محطة.
  3. دمج خطوات التنفيذ المتتالية بعدّاد (سرد لا سجل خام)؛
     سقف MAX_ENTRIES أقدم-يُطرد (لا تراكم ذاكرة).
  4. renderTimelineHTML نقي: المحطات بترتيبها + حالة فارغة +
     تهريب HTML للنصوص الواردة.
  5. wiring: app.js يستهلك SessionNarrative فعليًا (noteFrame في
     handleWSMessage، noteRequest في sendMessage، renderTimelineHTML
     في غراء اللوحة)، وindex.html يحمّل session_narrative.js **قبل**
     app.js.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي،
نفس سابقة test_stream_render/test_plan_card) ---
الخطوات (مرة واحدة عند تغيّر مسار السرد):
  1. شغّل الخادم وافتح الواجهة في Chrome.
  2. أرسل طلبًا يولّد خطة (مثلًا «أنشئ ملف a.txt واكتب فيه سطرًا»)،
     اعتمد الخطة («✅ موافق — نفّذ») وانتظر اكتمال التنفيذ.
  3. افتح لوحة تاريخ الـ runs (زر التاريخ) — يظهر قسم «سرد الجلسة»
     فوق قائمة الـ runs.
  4. القبول: السرد يعرض ≥ 4 محطات بترتيبها الزمني: 💬 الطلب →
     📋 الخطة (بعدد خطواتها) → ⚙️ التنفيذ → 🏁 اكتمل؛ وقائمة
     الـ runs تحتها تعمل كما قبل (استعادة/معاينة بلا تغيير).
  5. تحقق حفظ السلوك: أغلق اللوحة وافتحها — القائمة والتقرير كما
     هما؛ DevTools → لا أخطاء console ولا طلبات شبكة جديدة للسرد
     (يُبنى من الأطر الحية في الذاكرة).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "session_narrative.js"
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


HARNESS = """
const SN = require('./static/js/session_narrative.js');
function assert(cond, msg) { if (!cond) { console.error('FAIL: ' + msg); process.exit(1); } }
"""


class TestAcceptance:
    def test_approved_run_shows_four_stations_in_order(self) -> None:
        """القبول الحرفي: run واحد معتمد → ≥ 4 محطات بترتيبها."""
        run_node(HARNESS + """
const st = SN.createState();
SN.noteRequest(st, 'أنشئ ملف a.txt', 100);
SN.noteFrame(st, {type: 'plan', summary: 'إنشاء ملف',
                  actions: [{action: 'create_file', path: 'a.txt'}]}, 101);
SN.noteFrame(st, {type: 'chain_approval_verdict', approved: true}, 102);
SN.noteFrame(st, {type: 'task_progress', current: 1, total: 1,
                  action: {action: 'create_file', path: 'a.txt'}}, 103);
SN.noteFrame(st, {type: 'all_actions_done'}, 104);
const es = SN.entries(st);
assert(es.length >= 4, 'at least 4 stations, got ' + es.length);
const order = es.map(e => e.station).join(',');
assert(order === 'request,plan,approval,execution,result',
       'stations in order, got: ' + order);
const html = SN.renderTimelineHTML(st);
for (const s of ['sn-request','sn-plan','sn-approval','sn-execution','sn-result'])
    assert(html.indexOf(s) !== -1, s + ' rendered');
assert(html.indexOf('sn-request') < html.indexOf('sn-plan') &&
       html.indexOf('sn-plan') < html.indexOf('sn-approval') &&
       html.indexOf('sn-approval') < html.indexOf('sn-execution') &&
       html.indexOf('sn-execution') < html.indexOf('sn-result'),
       'rendered order matches chronology');
console.log('OK');
""")


class TestClassification:
    def test_unknown_frames_ignored(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
assert(SN.noteFrame(st, {type: 'pong'}, 1) === false, 'pong ignored');
assert(SN.noteFrame(st, {type: 'chunk', text: 'x'}, 1) === false, 'chunk ignored');
assert(SN.noteFrame(st, null, 1) === false, 'null tolerated');
assert(SN.noteFrame(null, {type: 'plan'}, 1) === false, 'null state tolerated');
assert(SN.entries(st).length === 0, 'no stations added');
console.log('OK');
""")

    def test_rejection_and_error_marked_bad(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
SN.noteFrame(st, {type: 'chain_approval_verdict', approved: false,
                  reason: 'denied'}, 1);
SN.noteFrame(st, {type: 'error', text: 'boom'}, 2);
const es = SN.entries(st);
assert(es[0].verdict === false, 'rejection verdict false');
assert(es[1].ok === false, 'error ok false');
const html = SN.renderTimelineHTML(st);
assert((html.match(/sn-bad/g) || []).length === 2, 'both marked sn-bad');
console.log('OK');
""")

    def test_rollback_station(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
SN.noteFrame(st, {type: 'rollback_result', status: 'success'}, 1);
const es = SN.entries(st);
assert(es[0].station === 'rollback' && es[0].ok === true, 'rollback ok');
console.log('OK');
""")


class TestAggregationAndBounds:
    def test_consecutive_execution_steps_merged(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
for (let i = 0; i < 5; i++)
    SN.noteFrame(st, {type: 'agent_step'}, 10 + i);
const es = SN.entries(st);
assert(es.length === 1, 'merged into one station');
assert(es[0].count === 5, 'counter = 5');
assert(SN.renderTimelineHTML(st).indexOf('×5') !== -1, 'counter rendered');
// محطة نتيجة تكسر الدمج — تنفيذ جديد بعدها = محطة جديدة
SN.noteFrame(st, {type: 'done'}, 20);
SN.noteFrame(st, {type: 'chain_step'}, 21);
assert(SN.entries(st).length === 3, 'result breaks merging');
console.log('OK');
""")

    def test_max_entries_oldest_evicted(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
SN.noteRequest(st, 'first', 1);
for (let i = 0; i < SN.MAX_ENTRIES + 10; i++) {
    SN.noteFrame(st, {type: 'plan', summary: 's' + i, actions: []}, 2 + i);
}
const es = SN.entries(st);
assert(es.length === SN.MAX_ENTRIES, 'capped at MAX_ENTRIES');
assert(es[0].station !== 'request', 'oldest (request) evicted');
console.log('OK');
""")


class TestRendering:
    def test_empty_state_and_html_escaping(self) -> None:
        run_node(HARNESS + """
const st = SN.createState();
assert(SN.renderTimelineHTML(st).indexOf('sn-empty') !== -1, 'empty note');
SN.noteRequest(st, '<script>alert(1)</script>', 1);
const html = SN.renderTimelineHTML(st);
assert(html.indexOf('<script>') === -1, 'HTML escaped');
assert(html.indexOf('&lt;script&gt;') !== -1, 'escaped form present');
console.log('OK');
""")


class TestWiring:
    def test_app_js_consumes_session_narrative(self) -> None:
        src = _app_bundle()
        assert "SessionNarrative.noteFrame(" in src, \
            "handleWSMessage يلتقط الأطر"
        assert "SessionNarrative.noteRequest(" in src, \
            "sendMessage يسجل محطة الطلب"
        assert "SessionNarrative.renderTimelineHTML(" in src, \
            "غراء اللوحة يرسم السرد"
        assert "renderSessionNarrative(panel)" in src, \
            "toggleRunHistory يحقن السرد فوق القائمة"

    def test_index_loads_module_before_app_js(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod = html.index("/static/js/session_narrative.js")
        app = html.index("/static/app.js")
        assert mod < app, "session_narrative.js يجب أن يسبق app.js"

    def test_manual_scenario_documented(self) -> None:
        # Accept الرسمي (بوابة Documentation): سيناريو يدوي موثَّق في
        # docstring هذا الملف بخطوات قابلة للتنفيذ.
        doc = __doc__ or ""
        assert "سرد الجلسة" in doc and "محطات" in doc and "DevTools" in doc
