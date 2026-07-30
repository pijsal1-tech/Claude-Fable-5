# -*- coding: utf-8 -*-
"""TSK-725c (P2-3 / D-10) — واجهة Workspace Trust (لافتة قرار + شارة).

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §TSK-725/725c):
  1. الوحدة النقية (node): parseTrust fail-closed (null/شكل غريب/‏ok
     زائف ⇒ غير موثوق بلا قرار)، decided عبر trusted/decided_at/
     decided_by، renderBanner يحمل زرّي data-trust-action
     (trust|keep)، renderBadge بحالتيه.
  2. نقاء الوحدة: لا document. ولا fetch( داخل trust_banner.js —
     الغراء في app.js حصرًا (سابقة status_chip/command_palette).
  3. wiring: index.html يحمّل trust_banner.js قبل app.js ويحوي
     عنصري trust-banner (hidden افتراضيًا) وtrust-badge؛ app.js
     يستهلك TrustBanner + تفويض data-trust-action (لا onclick
     مضمّن) + refreshTrustUI عند DOMContentLoaded وعند
     switch-project.
  4. لا منطق قرار في المتصفح: الغراء لا يقرر — POST يحمل قرار
     المستخدم الحرفي فقط ({trusted: bool}).
  5. صفر endpoints جديدة — /api/trust قائمة منذ 725b (يحرس العدد 34
     test_rest_blueprints).

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي) ---
الخطوات (مرة واحدة عند تغيّر مسار الثقة UI):
  1. احذف <root>/.ai_runs/trust.json وشغّل الخادم وافتح الواجهة.
  2. تظهر لافتة «هل تثق بهذا المجلد؟» تحت الشريط العلوي والشارة
     «⛔ غير موثوق» بجوار اسم المشروع.
  3. اطلب من الوكيل أمر طرفية — تظهر بطاقة موافقة رغم auto_execute
     (إنفاذ 725b).
  4. انقر «أثق بهذا المجلد» — تختفي اللافتة، الشارة تصبح «✓ موثوق»،
     وtrust.json يحوي trusted:true وdecided_by:"user".
  5. انقر «أبقِه غير موثوق» (بعد حذف trust.json وإعادة التحميل) —
     تختفي اللافتة (قرار مسجَّل) والشارة تبقى «⛔ غير موثوق».
  6. بدّل المجلد (Open Folder) — تُعاد القراءة للمجلد الجديد.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "trust_banner.js"
APP_JS = ROOT / "static" / "app.js"
INDEX_HTML = ROOT / "static" / "index.html"

node = shutil.which("node")


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


NODE_PRELUDE = f"const T = require({json.dumps(str(MODULE))});\n"


@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestParseTrustPure:
    """parseTrust — تطبيع fail-closed (وحدة نقية في node)."""

    def test_fail_closed_on_garbage(self):
        out = run_node(NODE_PRELUDE + """
const cases = [null, undefined, {}, {ok: false}, {ok: true},
    {ok: true, trust: null}, {ok: true, trust: "yes"},
    {ok: 1, trust: {trusted: true}},
    {ok: true, trust: {trusted: "true"}},
    {ok: true, trust: {trusted: 1}}];
console.log(JSON.stringify(cases.map(c => T.parseTrust(c))));
""")
        for parsed in json.loads(out):
            assert parsed == {"trusted": False, "decided": False}

    def test_trusted_implies_decided(self):
        out = run_node(NODE_PRELUDE + """
console.log(JSON.stringify(T.parseTrust(
    {ok: true, trust: {trusted: true}})));
""")
        assert json.loads(out) == {"trusted": True, "decided": True}

    def test_explicit_untrusted_decision_recorded(self):
        # قرار «أبقِه غير موثوق» مسجَّل ⇒ اللافتة لا تظهر لكن يبقى غير موثوق
        out = run_node(NODE_PRELUDE + """
console.log(JSON.stringify([
    T.parseTrust({ok: true, trust: {trusted: false,
        decided_at: "2026-07-30T00:00:00Z", decided_by: "user"}}),
    T.parseTrust({ok: true, trust: {trusted: false,
        decided_by: "user"}}),
]));
""")
        for parsed in json.loads(out):
            assert parsed == {"trusted": False, "decided": True}

    def test_render_banner_buttons(self):
        out = run_node(NODE_PRELUDE + """
const h = T.renderBanner();
console.log(JSON.stringify({
    trust: /data-trust-action="trust"/.test(h),
    keep: /data-trust-action="keep"/.test(h),
    onclick: /onclick=/.test(h),
    question: h.includes("\\u0647\\u0644 \\u062a\\u062b\\u0642"),
}));
""")
        d = json.loads(out)
        assert d["trust"] is True and d["keep"] is True
        assert d["onclick"] is False  # تفويض فقط — لا onclick مضمّن
        assert d["question"] is True  # «هل تثق…»

    def test_render_badge_both_states(self):
        out = run_node(NODE_PRELUDE + """
console.log(JSON.stringify({
    t: T.renderBadge(true), u: T.renderBadge(false),
    nonBool: T.renderBadge("true"),
}));
""")
        d = json.loads(out)
        assert "trust-badge-trusted" in d["t"]
        assert "trust-badge-untrusted" in d["u"]
        # fail-closed حتى في العرض: غير-bool ⇒ شارة «غير موثوق»
        assert "trust-badge-untrusted" in d["nonBool"]


class TestModulePurity:
    def test_no_dom_no_network_in_module(self):
        src = MODULE.read_text(encoding="utf-8")
        assert "document." not in src
        assert "fetch(" not in src

    def test_umd_lite_export(self):
        src = MODULE.read_text(encoding="utf-8")
        assert "module.exports" in src
        assert "global.TrustBanner" in src


class TestWiring:
    def test_index_loads_module_before_app_js(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        pos_mod = html.find("trust_banner.js")
        pos_app = html.find("app.js?")
        assert pos_mod != -1 and pos_app != -1
        assert pos_mod < pos_app

    def test_index_has_banner_hidden_and_badge(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        m = re.search(r'<div id="trust-banner" class="([^"]*)"', html)
        assert m is not None
        assert "hidden" in m.group(1)  # مخفية افتراضيًا حتى يقرر الغراء
        assert 'id="trust-badge"' in html

    def test_app_js_consumes_trust_banner_glue_only(self):
        src = APP_JS.read_text(encoding="utf-8")
        assert "TrustBanner.parseTrust" in src
        assert "TrustBanner.renderBanner" in src
        assert "TrustBanner.renderBadge" in src
        # تفويض النقر — لا onclick مضمّن للأزرار
        assert "data-trust-action" in src

    def test_app_js_refresh_on_boot_and_switch(self):
        src = APP_JS.read_text(encoding="utf-8")
        # نداء عند الإقلاع (داخل DOMContentLoaded) + عند نجاح switch-project
        assert src.count("refreshTrustUI()") >= 2
        # التبديل: النداء داخل نجاح openFolder (قرب refreshFiles)
        m = re.search(r"refreshFiles\(\);\s*\n\s*//[^\n]*\n\s*refreshTrustUI\(\);", src)
        assert m is not None

    def test_no_decision_logic_in_browser(self):
        """POST يحمل قرار المستخدم الحرفي فقط — لا اشتقاق/قلب في الغراء."""
        src = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"function decideTrust\(trusted\) \{(.*?)\n\}",
                      src, re.DOTALL)
        assert m is not None
        body = m.group(1)
        assert 'JSON.stringify({ trusted: trusted })' in body
        # لا قراءة config ولا منطق ثقة محلي في الغراء
        assert "auto_execute" not in body
        assert "localStorage" not in body

    def test_glue_get_and_post_target_api_trust_only(self):
        src = APP_JS.read_text(encoding="utf-8")
        # كل نداءات الثقة تستهدف /api/trust حصرًا (GET افتراضي + POST)
        section = src[src.find("Workspace Trust glue"):]
        urls = re.findall(r'fetch\("([^"]+)"', section)
        assert urls and set(urls) == {"/api/trust"}
