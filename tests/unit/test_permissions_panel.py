"""TSK-621 (CP-5/UXF-04 §R9) — لوحة الصلاحيات قراءة فقط (glass box).

يتحقق آليًا من:
  1. **القبول الحرفي — endpoint قراءة**: GET /api/permissions يعيد
     القيم الحية (allowlist من config عبر command_policy_from،
     SAFE/APPROVAL tools، SAFE/DANGEROUS commands، force_approval،
     حالة ApprovalGate) — وبلا أي مسار كتابة (GET فقط، لا POST/PUT).
  2. **حفظ السلوك**: النداء لا يغيّر السياسة المطبَّقة (config/globals
     كما هي قبل وبعد)؛ البوابة غير المهيأة تُعرض null لا اختراع.
  3. الوحدة النقية (node): renderPanelHTML يعرض الأقسام الأربعة
     بالقيم الواردة حرفيًا + تهريب HTML + حالات الغياب (UNKNOWN
     صريح لا اختراع).
  4. wiring: app.js يستهلك PermissionsPanel فعليًا (fetch للـ endpoint
     + renderPanelHTML، بلا أي إرسال كتابة)، وindex.html يحمّل
     permissions_panel.js **قبل** app.js ويحوي اللوحة والزر الوكيل.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي،
نفس سابقة test_plan_card/test_session_narrative) ---
الخطوات (مرة واحدة عند تغيّر مسار اللوحة):
  1. شغّل الخادم وافتح الواجهة في Chrome.
  2. اضغط زر «Permissions» 🔒 في Activity Bar — تظهر لوحة
     «الصلاحيات (قراءة فقط)».
  3. القبول: اللوحة تعرض الأقسام الأربعة بقيم حيّة: قائمة أوامر
     الـ agent (test/lint/typecheck/build كما في config.yaml + المهلة
     وسقف المخرجات) → أدوات الـ agent (آمنة/تتطلب موافقة) → أوامر
     الطرفية (SAFE/DANGEROUS) → بوابة الموافقة (الوضع + راية
     force_command_approval + المهلة).
  4. تحقق قراءة-فقط: لا أزرار تعديل/حفظ في اللوحة؛ DevTools →
     Network: نداء GET واحد لـ /api/permissions ولا أي POST؛ عدّل
     config.yaml (مثلًا أضف مدخل allowlist) وأعد فتح اللوحة —
     القيمة الجديدة تظهر (حيّة لا نسخة).
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

    def test_read_only_no_write_methods(self, server):
        """لا مسار كتابة: POST/PUT/DELETE على المسار مرفوضة (405)."""
        with server.app.test_client() as c:
            for method in ("post", "put", "delete"):
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
        """قراءة فقط: لا أزرار/مداخل تعديل في HTML اللوحة."""
        out = run_node(HARNESS + """
const html = PP.renderPanelHTML(PERMS);
console.log(JSON.stringify([/<button/.test(html), /<input/.test(html),
                            /<select/.test(html), /<textarea/.test(html)]));
""")
        assert out.strip() == "[false,false,false,false]"


# ═══════════════════ 3. wiring ═══════════════════

class TestWiring:
    def test_app_js_consumes_module_read_only(self):
        src = _app_bundle()
        assert 'fetch("/api/permissions")' in src
        assert "PermissionsPanel.renderPanelHTML" in src
        assert "togglePermissionsPanel" in src
        # قراءة فقط: غراء اللوحة لا يرسل أي كتابة
        glue = src[src.index("async function togglePermissionsPanel"):]
        glue = glue[:glue.index("\n}") + 2]
        assert "ws.send" not in glue and "POST" not in glue

    def test_index_html_loads_module_before_app_js(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod_pos = html.index("permissions_panel.js?v=1")
        app_pos = html.index("app.js?v=")
        assert mod_pos < app_pos
        assert 'id="permissions-panel"' in html
        assert 'id="permissions-panel-btn"' in html
