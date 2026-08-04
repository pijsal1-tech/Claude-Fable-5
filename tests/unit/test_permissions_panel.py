"""TSK-621 (CP-5/UXF-04 §R9) — لوحة الصلاحيات (glass box)
+ TSK-734d (القرار 6 من تسلسل D-19) — وضع التحرير الصريح.

يتحقق آليًا من:
  1. **القبول الحرفي — endpoint قراءة**: GET /api/permissions يعيد
     القيم الحية (allowlist من config عبر command_policy_from،
     SAFE/APPROVAL tools، SAFE/DANGEROUS commands، force_approval،
     حالة ApprovalGate). (TSK-734/D-19-6: أضيف POST للتحرير —
     مثبَّت في test_permissions_editing؛ PUT/DELETE ما زالا 405.)
  2. **حفظ السلوك**: النداء لا يغيّر السياسة المطبَّقة (config/globals
     كما هي قبل وبعد)؛ البوابة غير المهيأة تُعرض null لا اختراع.
  3. الوحدة النقية (node): renderPanelHTML يعرض الأقسام الأربعة
     بالقيم الواردة حرفيًا + تهريب HTML + حالات الغياب (UNKNOWN
     صريح لا اختراع)؛ TSK-734d: نموذج التحرير (زر حفظ واحد،
     تعبئة مسبقة من الفعال، تهريب) + التحليل fail-closed محليًا
     + جسم POST بالمفتاحين المسموحين فقط.
  4. wiring: app.js يستهلك PermissionsPanel فعليًا (التحميل GET
     بلا كتابة؛ الحفظ POST في handlePermAction ويعيد الرسم من
     الحقيقة المعادة)، وindex.html يحمّل permissions_panel.js
     **قبل** app.js ويحوي اللوحة والزر الوكيل.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي،
نفس سابقة test_plan_card/test_session_narrative) ---
الخطوات (مرة واحدة عند تغيّر مسار اللوحة):
  1. شغّل الخادم وافتح الواجهة في Chrome.
  2. اضغط زر «Permissions» 🔒 في Activity Bar — تظهر لوحة
     «الصلاحيات».
  3. القبول: اللوحة تعرض الأقسام الأربعة بقيم حيّة: قائمة أوامر
     الـ agent (test/lint/typecheck/build كما في config.yaml + المهلة
     وسقف المخرجات) → أدوات الـ agent (آمنة/تتطلب موافقة) → أوامر
     الطرفية (SAFE/DANGEROUS) → بوابة الموافقة (الوضع + راية
     force_command_approval + المهلة).
  4. TSK-734d — التحرير: اضغط «✏️ تحرير الأذونات» — يظهر نموذج
     صريح (checkbox للراية + textarea للـ allowlist بصيغة
     name = command) بزر حفظ واحد. عدّل واضغط 💾 حفظ — اللوحة
     تعيد الرسم بالقيم الجديدة (من استجابة الخادم)؛ DevTools →
     Network: POST واحد لـ /api/permissions؛ افحص config.yaml —
     لم يتغير بايتًا (الكتابة في permissions_overrides.json).
     أدخل سطرًا مكسورًا (بلا =) واضغط حفظ — رسالة خطأ محلية
     بلا أي POST. زر «إلغاء» يعيد العرض بلا حفظ.
  5. أغلق اللوحة (✕) وافتح لوحات أخرى (History/Memory) — تعمل كما
     قبل؛ لا أخطاء console.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "permissions_panel.js"
APP_JS = ROOT / "static" / "app.js"
APP_SPLIT_DIR = ROOT / "static" / "js" / "app"


def _app_bundle() -> str:
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
const PP = require('./static/js/permissions_panel.js');
const PERMS = {
    command_allowlist: {
        enforce: true,
        entries: { test: "python -m pytest -q",
                   build: "python -m compileall -q ." },
        timeout_seconds: 60,
        output_max_chars: 8000,
    },
    agent_tools: { safe: ["list_dir", "read_file"],
                   approval: ["run_command"] },
    terminal_commands: { safe: ["ls", "pwd"],
                         dangerous: ["rm", "sudo"] },
    force_command_approval: false,
    approval_gate: { mode: "interactive",
                     auto_whitelist: ["format", "read"],
                     timeout_seconds: 120 },
};
"""


# ═══════════════════ 1. endpoint القراءة (القبول الحرفي) ═══════════════════

class TestRestEndpoint:
    @pytest.fixture()
    def server(self):
        import server as srv
        return srv

    def test_live_values_served(self, server):
        """القبول: endpoint قراءة يعيد القيم الحية من config والكود."""
        with server.app.test_client() as c:
            data = c.get("/api/permissions").get_json()
        assert data["ok"] is True
        p = data["permissions"]
        # allowlist الحية من config.yaml (command_policy_from)
        al = p["command_allowlist"]
        assert al["enforce"] is True
        assert al["entries"]["test"] == "python -m pytest -q"
        assert al["timeout_seconds"] == 60
        assert al["output_max_chars"] == 8000
        # أدوات الـ agent — نفس ثوابت chain/agent_tools.py
        from chain.agent_tools import SAFE_TOOLS, APPROVAL_TOOLS
        assert p["agent_tools"]["safe"] == sorted(SAFE_TOOLS)
        assert p["agent_tools"]["approval"] == sorted(APPROVAL_TOOLS)
        # أوامر الطرفية — نفس ثوابت actions/command_runner.py
        from actions.command_runner import SAFE_COMMANDS, DANGEROUS_COMMANDS
        assert p["terminal_commands"]["safe"] == sorted(SAFE_COMMANDS)
        assert p["terminal_commands"]["dangerous"] == sorted(
            DANGEROUS_COMMANDS)
        # راية force_approval — نفس القارئ الحي
        assert p["force_command_approval"] == server._force_command_approval()

    def test_gate_none_before_boot(self, server, monkeypatch):
        """البوابة غير المهيأة ⇒ null صريح — لا اختراع (UNKNOWN)."""
        monkeypatch.setattr(server, "approval_gate", None)
        with server.app.test_client() as c:
            data = c.get("/api/permissions").get_json()
        assert data["ok"] is True
        assert data["permissions"]["approval_gate"] is None

    def test_gate_state_reflected_live(self, server, monkeypatch):
        """حالة ApprovalGate الحية (mode/whitelist/timeout) تُعرض كما هي."""
        from core.approval import ApprovalGate
        gate = ApprovalGate(mode="auto", auto_whitelist={"write", "read"},
                            timeout_seconds=99.0)
        monkeypatch.setattr(server, "approval_gate", gate)
        with server.app.test_client() as c:
            g = c.get("/api/permissions").get_json()[
                "permissions"]["approval_gate"]
        assert g["mode"] == "auto"
        assert g["auto_whitelist"] == ["read", "write"]
        assert g["timeout_seconds"] == 99.0

    def test_no_unexpected_write_methods(self, server):
        """PUT/DELETE مرفوضة (405) — TSK-734/D-19-6 أضاف POST فقط
        (مغطى في test_permissions_editing)؛ لا مسارات أخرى."""
        with server.app.test_client() as c:
            for method in ("put", "delete"):
                resp = getattr(c, method)("/api/permissions")
                assert resp.status_code == 405, method

    def test_call_does_not_mutate_policy(self, server):
        """حفظ السلوك: النداء لا يغيّر السياسة المطبَّقة."""
        gate_before = server.approval_gate
        force_before = server._force_command_approval()
        with server.app.test_client() as c:
            c.get("/api/permissions")
        assert server.approval_gate is gate_before
        assert server._force_command_approval() == force_before


# ═══════════════════ 2. الوحدة النقية (node) ═══════════════════

@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestPureModule:
    def test_renders_all_four_sections_with_live_values(self):
        out = run_node(HARNESS + """
const html = PP.renderPanelHTML(PERMS);
const checks = [
    html.includes("command_allowlist"),
    html.includes("python -m pytest -q"),
    html.includes("run_command"),
    html.includes("sudo"),
    html.includes("ApprovalGate"),
    html.includes("interactive"),
];
console.log(JSON.stringify(checks));
""")
        assert out.strip() == "[true,true,true,true,true,true]"

    def test_escapes_html_in_values(self):
        out = run_node(HARNESS + """
PERMS.command_allowlist.entries = { evil: '<script>x</script>' };
const html = PP.renderPanelHTML(PERMS);
console.log(JSON.stringify([html.includes("<script>x"),
                            html.includes("&lt;script&gt;x")]));
""")
        assert out.strip() == "[false,true]"

    def test_missing_gate_and_null_perms_explicit(self):
        """الغياب ⇒ عرض صريح (UNKNOWN/غير مهيأة) — لا اختراع قيم."""
        out = run_node(HARNESS + """
PERMS.approval_gate = null;
const html = PP.renderPanelHTML(PERMS);
const nullHtml = PP.renderPanelHTML(null);
console.log(JSON.stringify([
    html.includes("غير مهيأة"),
    nullHtml.includes("تعذّر تحميل"),
]));
""")
        assert out.strip() == "[true,true]"

    def test_legacy_mode_and_empty_lists(self):
        out = run_node(HARNESS + """
PERMS.command_allowlist = { enforce: false, entries: {},
                            timeout_seconds: 60, output_max_chars: 8000 };
PERMS.agent_tools = { safe: [], approval: [] };
const html = PP.renderPanelHTML(PERMS);
console.log(JSON.stringify([html.includes("legacy"),
                            html.includes("لا شيء")]));
""")
        assert out.strip() == "[true,true]"

    def test_no_write_affordances_in_output(self):
        """العرض ما زال نقيًا: لا أزرار/مداخل تعديل في renderPanelHTML
        — التحرير (TSK-734d) في نموذج منفصل صريح (renderEditFormHTML)."""
        out = run_node(HARNESS + """
const html = PP.renderPanelHTML(PERMS);
console.log(JSON.stringify([/<button/.test(html), /<input/.test(html),
                            /<select/.test(html), /<textarea/.test(html)]));
""")
        assert out.strip() == "[false,false,false,false]"


# ═══════ 2ب. TSK-734d — وضع التحرير (المنطق النقي) ═══════

@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestEditMode:
    def test_edit_form_single_save_button_and_prefill(self):
        """نموذج صريح: زر حفظ واحد (data-perm-action=save) + إلغاء؛
        القيم الحالية معبأة مسبقًا من السياسة الفعالة."""
        out = run_node(HARNESS + """
const html = PP.renderEditFormHTML(PERMS);
const saves = (html.match(/data-perm-action="save"/g) || []).length;
console.log(JSON.stringify([
    saves,
    html.includes('data-perm-action="cancel"'),
    html.includes('id="pp-edit-force"'),
    html.includes("test = python -m pytest -q"),
    html.includes("config.yaml لا يُمس"),
]));
""")
        assert out.strip() == '[1,true,true,true,true]'

    def test_edit_form_force_checkbox_reflects_state(self):
        """checkbox الراية يعكس القيمة الفعالة (لا افتراض)."""
        out = run_node(HARNESS + """
const off = PP.renderEditFormHTML(PERMS);              // false في PERMS
PERMS.force_command_approval = true;
const on = PP.renderEditFormHTML(PERMS);
console.log(JSON.stringify([/pp-edit-force"[^>]*checked/.test(off),
                            /pp-edit-force"[^>]*checked/.test(on)]));
""")
        assert out.strip() == "[false,true]"

    def test_edit_form_escapes_html(self):
        """تهريب HTML في قيم الـ allowlist المعبأة (نفس عقد العرض)."""
        out = run_node(HARNESS + """
PERMS.command_allowlist.entries = { evil: '<script>x</script>' };
const html = PP.renderEditFormHTML(PERMS);
console.log(JSON.stringify([html.includes("<script>x"),
                            html.includes("&lt;script&gt;x")]));
""")
        assert out.strip() == "[false,true]"

    def test_parse_allowlist_text_valid_and_roundtrip(self):
        """name = command لكل سطر؛ سطور فارغة تُتجاهل؛ round-trip مع
        allowlistToText."""
        out = run_node(HARNESS + """
const r = PP.parseAllowlistText("a = echo 1\\n\\n  b = x --flag=2  \\n");
const rt = PP.parseAllowlistText(PP.allowlistToText(r.entries));
console.log(JSON.stringify([r.ok, r.entries,
    JSON.stringify(rt.entries) === JSON.stringify(r.entries)]));
""")
        assert out.strip() == (
            '[true,{"a":"echo 1","b":"x --flag=2"},true]')

    def test_parse_allowlist_text_rejects_bad_lines(self):
        """fail-closed محليًا: سطر بلا = أو باسم/أمر فارغ ⇒ خطأ صريح."""
        out = run_node(HARNESS + """
console.log(JSON.stringify([
    PP.parseAllowlistText("no equals here").ok,
    PP.parseAllowlistText("= cmd").ok,
    PP.parseAllowlistText("name =").ok,
    PP.parseAllowlistText("").ok,           // فارغ = قائمة فارغة (صالح)
]));
""")
        assert out.strip() == "[false,false,false,true]"

    def test_build_overrides_payload_shape(self):
        """جسم POST = المفتاحان المسموحان فقط (whitelist الخادم)؛
        تحليل فاشل يمرر الخطأ بلا payload."""
        out = run_node(HARNESS + """
const good = PP.buildOverridesPayload(true, "t = pytest -q");
const bad = PP.buildOverridesPayload(false, "broken line");
console.log(JSON.stringify([
    good.ok, Object.keys(good.payload.overrides).sort(),
    good.payload.overrides["force_command_approval"],
    good.payload.overrides["agent.command_allowlist"],
    bad.ok, "payload" in bad,
]));
""")
        assert out.strip() == (
            '[true,["agent.command_allowlist","force_command_approval"],'
            'true,{"t":"pytest -q"},false,false]')


# ═══════════════════ 3. wiring ═══════════════════

class TestWiring:
    def test_app_js_consumes_module_read_only(self):
        src = _app_bundle()
        assert 'fetch("/api/permissions")' in src
        assert "PermissionsPanel.renderPanelHTML" in src
        assert "togglePermissionsPanel" in src
        # التحميل نفسه ما زال قراءة فقط — الكتابة حصرًا في
        # handlePermAction (TSK-734d)، لا في مسار الفتح/العرض.
        glue = src[src.index("async function togglePermissionsPanel"):]
        glue = glue[:glue.index("\n}") + 2]
        assert "ws.send" not in glue and "POST" not in glue

    def test_app_js_edit_glue_posts_and_rerenders_from_truth(self):
        """TSK-734d: غراء التحرير يرسل POST للمسار الصحيح ويعيد
        الرسم من الحقيقة المعادة (data.permissions) — لا تفاؤل."""
        src = _app_bundle()
        assert "handlePermAction" in src
        glue = src[src.index("async function handlePermAction"):]
        glue = glue[:glue.index("\n}") + 2]
        assert 'fetch("/api/permissions"' in glue
        assert '"POST"' in glue
        assert "PermissionsPanel.buildOverridesPayload" in glue
        # إعادة الرسم من استجابة الخادم لا من قيم النموذج
        assert "renderPermissionsView(data.permissions)" in glue
        # زر التحرير والنموذج مربوطان عبر data-perm-action
        assert 'data-perm-action="edit"' in src
        assert "PermissionsPanel.renderEditFormHTML" in src

    def test_index_html_loads_module_before_app_js(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod_pos = html.index("permissions_panel.js?v=1")
        app_pos = html.index("app.js?v=")
        assert mod_pos < app_pos
        assert 'id="permissions-panel"' in html
        assert 'id="permissions-panel-btn"' in html
