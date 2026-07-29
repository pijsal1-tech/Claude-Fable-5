"""TSK-619 (CP-1/UXF-01 §R9) — بطاقة الخطة التفاعلية.

يتحقق آليًا (وحدة JS نقية في node — نفس نمط test_stream_render) من:
  1. **القبول الحرفي**: تعطيل خطوة → payload التنفيذ (enabledActions)
     بدونها؛ بقية الخطوات بترتيبها الأصلي.
  2. **بوابة حفظ السلوك الحرفية**: كل-الخطوات-مفعلة (الافتراضي بلا لمس)
     → enabledActions تعيد نفس عناصر القائمة الأصلية بنفس الترتيب
     ⇒ payload التنفيذ مطابق للسلوك القديم حرفيًا.
  3. toggle/setEnabled/isEnabled/enabledCount: قلب/ضبط/قراءة الأعلام،
     خارج النطاق آمن، صفر مفعّل ⇒ الغراء يمنع الإرسال.
  4. wiring: app.js يستهلك PlanCard فعليًا (createState في showPlanCard،
     setEnabled في مستمع الـ checkbox، enabledActions في executePlan)،
     و index.html يحمّل plan_card.js **قبل** app.js.

--- السيناريو اليدوي الموثَّق (بند القبول «سيناريو يدوي موثق» — Accept
الرسمي، نفس سابقة test_stream_render §QA-T11) ---
الخطوات (مرة واحدة عند تغيّر مسار بطاقة الخطة):
  1. شغّل الخادم وافتح الواجهة في Chrome، افتح DevTools → تبويب Network
     → فلتر WS → افتح اتصال الـ WebSocket → تبويب Messages.
  2. أرسل طلبًا يولّد خطة متعددة الخطوات (مثلًا: «أنشئ ملفين a.txt
     وb.txt واكتب فيهما سطرًا») — تظهر بطاقة الخطة وكل خطوة بجانبها
     checkbox مفعّلة افتراضيًا.
  3. عطّل خطوة واحدة (أزل علامة الاختيار — يظهر عليها شطب وخفوت)
     ثم اضغط «✅ موافق — نفّذ».
  4. القبول: رسالة WS الصادرة {"type":"execute_plan","actions":[...]}
     تحوي الخطوات المفعّلة فقط (الخطوة المعطّلة غائبة)، والتنفيذ
     الفعلي (task-progress + الملفات الناتجة) يطابق المفعّل فقط.
  5. تحقق حفظ السلوك: أعد التجربة بلا أي لمس للـ checkboxes —
     الرسالة الصادرة تحوي كل الخطوات (السلوك القديم حرفيًا).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "plan_card.js"
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


HARNESS = """
const PC = require('./static/js/plan_card.js');
const ACTIONS = [
    {action: 'create_file', path: 'a.txt', content: 'A'},
    {action: 'edit_file', path: 'b.txt', content: 'B'},
    {action: 'run_command', command: 'echo hi'},
];
function assert(cond, msg) { if (!cond) { console.error('FAIL: ' + msg); process.exit(1); } }
"""


class TestAcceptance:
    def test_disable_step_excluded_from_payload(self) -> None:
        """القبول الحرفي: تعطيل خطوة → payload التنفيذ بدونها."""
        run_node(HARNESS + """
const st = PC.createState(ACTIONS);
PC.setEnabled(st, 1, false);            // عطّل الخطوة الوسطى
const out = PC.enabledActions(st);
assert(out.length === 2, 'length after disable');
assert(out[0] === ACTIONS[0], 'first kept');
assert(out[1] === ACTIONS[2], 'third kept, order preserved');
assert(out.indexOf(ACTIONS[1]) === -1, 'disabled step absent from payload');
console.log('OK');
""")

    def test_all_enabled_identical_to_original(self) -> None:
        """بوابة حفظ السلوك: كل-الخطوات-مفعلة = السلوك القديم حرفيًا."""
        run_node(HARNESS + """
const st = PC.createState(ACTIONS);     // الافتراضي: لا لمس
const out = PC.enabledActions(st);
assert(out.length === ACTIONS.length, 'same length');
for (let i = 0; i < ACTIONS.length; i++)
    assert(out[i] === ACTIONS[i], 'same element same order at ' + i);
assert(JSON.stringify(out) === JSON.stringify(ACTIONS),
       'serialized payload byte-identical');
console.log('OK');
""")


class TestStateLogic:
    def test_toggle_and_isenabled(self) -> None:
        run_node(HARNESS + """
const st = PC.createState(ACTIONS);
assert(PC.isEnabled(st, 0) === true, 'default enabled');
PC.toggle(st, 0);
assert(PC.isEnabled(st, 0) === false, 'toggled off');
PC.toggle(st, 0);
assert(PC.isEnabled(st, 0) === true, 'toggled back on');
console.log('OK');
""")

    def test_out_of_range_safe(self) -> None:
        run_node(HARNESS + """
const st = PC.createState(ACTIONS);
PC.toggle(st, -1); PC.toggle(st, 99); PC.setEnabled(st, 99, false);
assert(PC.enabledActions(st).length === 3, 'out-of-range is a no-op');
assert(PC.isEnabled(st, 99) === false, 'out-of-range reads false');
assert(PC.isEnabled(st, -1) === false, 'negative reads false');
console.log('OK');
""")

    def test_enabled_count_and_zero_enabled(self) -> None:
        """صفر مفعّل: الوحدة تعيد []؛ الغراء (executePlan) يمنع الإرسال."""
        run_node(HARNESS + """
const st = PC.createState(ACTIONS);
assert(PC.enabledCount(st) === 3, 'count all');
PC.setEnabled(st, 0, false); PC.setEnabled(st, 1, false); PC.setEnabled(st, 2, false);
assert(PC.enabledCount(st) === 0, 'count zero');
assert(PC.enabledActions(st).length === 0, 'empty payload when none enabled');
console.log('OK');
""")

    def test_empty_and_invalid_input(self) -> None:
        run_node(HARNESS + """
const st = PC.createState([]);
assert(PC.enabledActions(st).length === 0, 'empty actions');
const st2 = PC.createState(null);
assert(PC.enabledActions(st2).length === 0, 'null actions tolerated');
assert(PC.enabledActions(null).length === 0, 'null state tolerated');
assert(PC.enabledCount(null) === 0, 'null state count 0');
console.log('OK');
""")


class TestWiring:
    def test_app_js_consumes_plan_card(self) -> None:
        src = APP_JS.read_text(encoding="utf-8")
        assert "PlanCard.createState(" in src, "showPlanCard ينشئ الحالة"
        assert "PlanCard.setEnabled(" in src, "مستمع checkbox يضبط العلم"
        assert "PlanCard.enabledActions(" in src, "executePlan يرسل subset"
        assert 'class="plan-step-toggle"' in src, "checkbox مرسوم لكل خطوة"

    def test_index_loads_module_before_app_js(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod = html.index("/static/js/plan_card.js")
        app = html.index("/static/app.js")
        assert mod < app, "plan_card.js يجب أن يسبق app.js"

    def test_module_header_documents_behavior_preservation(self) -> None:
        src = MODULE.read_text(encoding="utf-8")
        assert "حفظ السلوك" in src, "رأس الوحدة يوثق ضمان حفظ السلوك"

    def test_manual_scenario_documented(self) -> None:
        # Accept الرسمي: «سيناريو يدوي موثق» — موثَّق في docstring هذا
        # الملف بخطوات DevTools/WS Messages قابلة للتنفيذ.
        doc = __doc__ or ""
        assert "DevTools" in doc and "execute_plan" in doc
