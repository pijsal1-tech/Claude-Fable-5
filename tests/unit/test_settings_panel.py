# -*- coding: utf-8 -*-
"""TSK-722b (P1-4 / D-9) — لوحة الإعدادات عرض-فقط (glass box).

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §BATCH-P1/TSK-722b):
  1. الوحدة النقية (node): renderPanelHTML يعرض الأقسام بالقيم
     الواردة حرفيًا + تهريب HTML + حالات الغياب (UNKNOWN صريح).
  2. عرض-فقط: لا أزرار/مداخل تعديل في HTML اللوحة + ملاحظة
     «التعديل عبر config.yaml» ظاهرة.
  3. wiring: app.js يستهلك SettingsPanel فعليًا (fetch للـ endpoint
     + renderPanelHTML، بلا أي إرسال كتابة)، وindex.html يحمّل
     settings_panel.js **قبل** app.js ويحوي اللوحة والزر.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي،
نفس سابقة test_permissions_panel) ---
الخطوات (مرة واحدة عند تغيّر مسار اللوحة):
  1. شغّل الخادم وافتح الواجهة في Chrome.
  2. اضغط زر «Settings» ⚙️ أسفل Activity Bar — تظهر لوحة
     «الإعدادات (عرض فقط)».
  3. القبول: اللوحة تعرض قيم config.yaml الحية (default_provider،
     language، أقسام agent/context_budget/routing/retention...) +
     قسم إلزام الموافقة بالقيمة الفعالة ومصدرها + ملاحظة «التعديل
     عبر config.yaml ثم إعادة تشغيل».
  4. تحقق عرض-فقط: لا أزرار تعديل/حفظ؛ DevTools → Network: نداء
     GET واحد لـ /api/settings ولا أي POST؛ عدّل config.yaml وأعد
     تشغيل الخادم وافتح اللوحة — القيمة الجديدة تظهر.
  5. أغلق اللوحة (✕) وافتح لوحات أخرى (Permissions/History) — تعمل
     كما قبل؛ لا أخطاء console.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "settings_panel.js"
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
const SP = require('./static/js/settings_panel.js');
const S = {
    default_provider: "use_ai",
    language: "mix",
    auto_execute: false,
    backup_before_edit: true,
    max_context_files: 15,
    planner: "heuristic",
    backend: "memory",
    dispatch: "in-proc",
    project_root_set: false,
    agent: { command_allowlist: { test: "python -m pytest -q" },
             command_timeout_seconds: 60,
             command_output_max_chars: 8000 },
    context_budget: { model_window: 128000, reserved_output: 8000,
                      safety_margin: 0.10 },
    history: { payload_last_n: 40 },
    context_semantic: { enabled: true, timeout_seconds: 2.0, top_k: 3 },
    session_binding: { warn_only: true, policy: "warn" },
    execution: { stale_ttl_seconds: 900 },
    routing: { direct_max: 2.0, version: 1 },
    retention: { max_count: null, max_age_days: null, dry_run: true,
                 pinned_count: 0 },
    force_command_approval: { effective: true, explicit_in_config: false },
};
"""


# ═══════════════════ 1. الوحدة النقية (node) ═══════════════════

@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestPureModule:
    def test_renders_sections_with_live_values(self):
        out = run_node(HARNESS + """
const html = SP.renderPanelHTML(S);
const checks = [
    html.includes("use_ai"),
    html.includes("python -m pytest -q"),
    html.includes("128000"),
    html.includes("heuristic"),
    html.includes("in-proc"),
    html.includes("stale_ttl_seconds"),
    html.includes("pinned_count"),
];
console.log(JSON.stringify(checks));
""")
        assert out.strip() == "[true,true,true,true,true,true,true]"

    def test_force_approval_effective_and_source_shown(self):
        out = run_node(HARNESS + """
const h1 = SP.renderPanelHTML(S);   // effective=true من fail-closed
S.force_command_approval = { effective: false, explicit_in_config: true };
const h2 = SP.renderPanelHTML(S);
console.log(JSON.stringify([
    h1.includes("fail-closed"),
    h2.includes("صريحة في config.yaml"),
]));
""")
        assert out.strip() == "[true,true]"

    def test_escapes_html_in_values(self):
        out = run_node(HARNESS + """
S.default_provider = '<script>x</script>';
S.agent.command_allowlist = { evil: '<img onerror=1>' };
const html = SP.renderPanelHTML(S);
console.log(JSON.stringify([
    html.includes("<script>x"), html.includes("&lt;script&gt;x"),
    html.includes("<img onerror"), html.includes("&lt;img onerror"),
]));
""")
        assert out.strip() == "[false,true,false,true]"

    def test_missing_values_explicit_unknown(self):
        """الغياب ⇒ UNKNOWN صريح — لا اختراع قيم."""
        out = run_node(HARNESS + """
S.default_provider = null;
S.agent = null;
S.retention = undefined;
const html = SP.renderPanelHTML(S);
const nullHtml = SP.renderPanelHTML(null);
console.log(JSON.stringify([
    html.includes("UNKNOWN"),
    nullHtml.includes("تعذّر تحميل"),
]));
""")
        assert out.strip() == "[true,true]"

    def test_read_only_no_write_affordances_and_note(self):
        """عرض فقط: لا أزرار/مداخل تعديل + ملاحظة التعديل عبر config."""
        out = run_node(HARNESS + """
const html = SP.renderPanelHTML(S);
console.log(JSON.stringify([
    /<button/.test(html), /<input/.test(html),
    /<select/.test(html), /<textarea/.test(html),
    html.includes("config.yaml"),
]));
""")
        assert out.strip() == "[false,false,false,false,true]"

    def test_project_root_flag_only_no_path(self):
        out = run_node(HARNESS + """
S.project_root_set = true;
const html = SP.renderPanelHTML(S);
console.log(JSON.stringify([html.includes("لا يُعرض")]));
""")
        assert out.strip() == "[true]"


# ═══════════════════ 2. wiring ═══════════════════

class TestWiring:
    def test_app_js_consumes_module_read_only(self):
        src = APP_JS.read_text(encoding="utf-8")
        assert 'fetch("/api/settings")' in src
        assert "SettingsPanel.renderPanelHTML" in src
        assert "toggleSettingsPanel" in src
        # عرض فقط: غراء اللوحة لا يرسل أي كتابة
        glue = src[src.index("async function toggleSettingsPanel"):]
        glue = glue[:glue.index("\n}") + 2]
        assert "ws.send" not in glue and "POST" not in glue

    def test_index_html_loads_module_before_app_js(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        mod_pos = html.index("settings_panel.js?v=1")
        app_pos = html.index("app.js?v=")
        assert mod_pos < app_pos
        # اللوحة والزر موجودان
        assert 'id="settings-panel"' in html
        assert 'id="settings-panel-list"' in html
        assert 'onclick="toggleSettingsPanel()"' in html

    def test_module_file_pure_no_dom_calls(self):
        """الوحدة نقية — صفر DOM glue (document/fetch) داخلها."""
        src = MODULE.read_text(encoding="utf-8")
        assert "document." not in src
        assert "fetch(" not in src
