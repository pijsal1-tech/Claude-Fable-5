# -*- coding: utf-8 -*-
"""TSK-723 (P2-1 / D-10) — Command Palette (Ctrl+Shift+P).

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §BATCH-P2/TSK-723):
  1. الوحدة النقية (node): الترشيح (فارغ = الكل / جزئي / لا نتائج)،
     render بقيم حرفية + تهريب HTML + مؤشر التحديد (selected).
  2. السجل الساكن يحوي فقط أفعالًا معرَّفة — كل action هو اسم دالة
     UI **قائمة فعلًا** في app.js ومفتاح في جدول CP_ACTIONS
     (lookup صريح — لا سلاسل eval ولا onclick مضمّن).
  3. wiring: index.html يحمّل command_palette.js **قبل** app.js
     والـ modal موجود؛ app.js يستهلك CommandPalette + مستمع
     Ctrl+Shift+P + تفويض نقر عبر data-cmd-id.
  4. نقاء الوحدة: لا document. ولا fetch( داخل command_palette.js.
  5. صفر endpoints جديدة — السطح المجمّد (33) لا يُمسّ (يحرسه
     test_rest_blueprints؛ هنا نتأكد أن الوحدة لا تنادي الشبكة).

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي،
نفس سابقة test_permissions_panel/test_settings_panel) ---
الخطوات (مرة واحدة عند تغيّر مسار اللوحة):
  1. شغّل الخادم وافتح الواجهة في Chrome.
  2. اضغط Ctrl+Shift+P — تظهر لوحة الأوامر فوق المحرر مع حقل
     الإدخال مركَّزًا وقائمة كاملة (15 أمرًا).
  3. اكتب «إعدادات» — تنحصر القائمة؛ ↑↓ تنقّل مع التفاف؛ Enter
     ينفّذ (تفتح لوحة الإعدادات) وتُغلق اللوحة.
  4. أعد الفتح وانقر عنصرًا بالفأرة — ينفَّذ الأمر؛ Esc أو نقر
     الخلفية يغلق بلا تنفيذ.
  5. DevTools → Network: لا أي نداء شبكة صادر عن فتح/ترشيح اللوحة
     نفسها؛ لا أخطاء console.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "command_palette.js"
APP_JS = ROOT / "static" / "app.js"
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
const CP = require('./static/js/command_palette.js');
"""


@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestPureModule:
    def test_registry_shape(self):
        out = run_node(HARNESS + """
console.log(CP.COMMANDS.length);
for (const c of CP.COMMANDS) {
    if (!c.id || !c.label || typeof c.action !== 'string')
        throw new Error('bad entry: ' + JSON.stringify(c));
    if (!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(c.action))
        throw new Error('action ليس اسم دالة صِرفًا (لا eval): ' + c.action);
}
console.log('SHAPE_OK');
""")
        assert "SHAPE_OK" in out
        assert int(out.splitlines()[0]) >= 10

    def test_filter_empty_returns_all_copy(self):
        out = run_node(HARNESS + """
const all = CP.filterCommands('', CP.COMMANDS);
console.log(all.length === CP.COMMANDS.length);
console.log(all !== CP.COMMANDS);  // نسخة، لا نفس المرجع
""")
        assert out.splitlines() == ["true", "true"]

    def test_filter_partial_and_case_insensitive(self):
        out = run_node(HARNESS + """
const byId = CP.filterCommands('QUICK', CP.COMMANDS);
console.log(byId.some(c => c.id === 'quick-open'));
const byLabel = CP.filterCommands('الإعدادات', CP.COMMANDS);
console.log(byLabel.length >= 1 && byLabel.every(
    c => (c.label + c.id).includes('عداد') || c.id.includes('settings')));
""")
        assert out.splitlines() == ["true", "true"]

    def test_filter_no_results_and_render_empty(self):
        out = run_node(HARNESS + """
const none = CP.filterCommands('zzz-no-such-cmd-777', CP.COMMANDS);
console.log(none.length);
console.log(CP.renderListHTML(none, 0));
""")
        lines = out.splitlines()
        assert lines[0] == "0"
        assert "quick-open-empty" in lines[1]
        assert "لا أوامر مطابقة" in lines[1]

    def test_render_literal_values_selection_and_hint(self):
        out = run_node(HARNESS + """
const items = [
    {id: 'a', label: 'أمر أول', hint: 'Ctrl+K', action: 'x'},
    {id: 'b', label: 'أمر ثانٍ', hint: '', action: 'y'},
];
console.log(CP.renderListHTML(items, 1));
""")
        html = out.strip()
        assert "أمر أول" in html and "أمر ثانٍ" in html
        assert 'data-cmd-id="a"' in html and 'data-cmd-id="b"' in html
        assert 'data-index="0"' in html and 'data-index="1"' in html
        # مؤشر التحديد على العنصر الثاني فقط
        assert html.count("cp-item selected") == 1
        first, second = html.split('data-cmd-id="b"')
        assert "selected" not in first.split("cp-item")[1].split('"')[0]
        # التلميح داخل kbd للعنصر الأول فقط
        assert '<kbd class="quick-open-kbd">Ctrl+K</kbd>' in html
        assert html.count("<kbd") == 1

    def test_render_escapes_html(self):
        out = run_node(HARNESS + """
const items = [{id: 'x"y', label: '<img src=x onerror=alert(1)>',
                hint: '<b>', action: 'z'}];
console.log(CP.renderListHTML(items, 0));
""")
        html = out.strip()
        assert "<img" not in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html
        assert "&lt;b&gt;" in html
        assert 'data-cmd-id="x&quot;y"' in html


class TestRegistryActionsExist:
    """كل action في السجل = دالة قائمة في app.js + مفتاح في CP_ACTIONS."""

    def _actions(self) -> list[str]:
        src = MODULE.read_text(encoding="utf-8")
        return re.findall(r'action:\s*"([A-Za-z0-9_$]+)"', src)

    def test_every_action_is_existing_app_function(self):
        app = APP_JS.read_text(encoding="utf-8")
        actions = self._actions()
        assert len(actions) >= 10
        for name in actions:
            assert re.search(
                r"function\s+" + re.escape(name) + r"\s*\(", app
            ), f"action بلا دالة قائمة في app.js: {name}"

    def test_every_action_in_cp_actions_lookup(self):
        app = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"const CP_ACTIONS = \{(.*?)\};", app, re.S)
        assert m, "جدول CP_ACTIONS غير موجود في app.js"
        table = m.group(1)
        for name in self._actions():
            assert re.search(
                r"\b" + re.escape(name) + r"\b", table
            ), f"action غائب عن جدول CP_ACTIONS: {name}"

    def test_no_eval_no_inline_onclick(self):
        for path in (MODULE,):
            src = path.read_text(encoding="utf-8")
            assert "eval(" not in src
            assert "new Function" not in src
            assert "onclick=" not in src
        # الغراء: التنفيذ عبر lookup صريح فقط
        app = APP_JS.read_text(encoding="utf-8")
        glue = app[app.index("const CP_ACTIONS"):]
        assert "eval(" not in glue and "new Function" not in glue
        assert "CP_ACTIONS[cmd.action]" in glue


class TestWiring:
    def test_index_loads_module_before_app_and_has_modal(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod_pos = html.index("command_palette.js")
        app_pos = html.index("app.js?v=")
        assert mod_pos < app_pos, "الوحدة يجب أن تُحمَّل قبل app.js"
        assert 'id="command-palette-modal"' in html
        assert 'id="command-palette-input"' in html
        assert 'id="command-palette-results"' in html

    def test_app_consumes_module_and_shortcut(self):
        app = APP_JS.read_text(encoding="utf-8")
        assert "CommandPalette.filterCommands" in app
        assert "CommandPalette.renderListHTML" in app
        # اختصار Ctrl/Meta+Shift+P
        assert re.search(
            r'key\.toLowerCase\(\)\s*===\s*["\']p["\']', app)
        assert "shiftKey" in app
        # تفويض النقر عبر data-cmd-id (لا onclick لكل عنصر)
        assert 'closest("[data-cmd-id]")' in app or \
            "closest('[data-cmd-id]')" in app

    def test_module_purity_no_dom_no_network(self):
        src = MODULE.read_text(encoding="utf-8")
        assert "document." not in src
        assert "fetch(" not in src
        assert "XMLHttpRequest" not in src
        assert "WebSocket" not in src
