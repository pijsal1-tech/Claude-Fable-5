/* TSK-722b (P1-4/D-9): لوحة الإعدادات — عرض فقط (glass box).
 * منطق نقي (UMD-lite، قابل للاختبار في node — نمط permissions_panel.js).
 * الـ DOM glue في app.js فقط.
 *
 * المصدر: GET /api/settings (routes/meta.py — TSK-722a) — يعيد
 * { ok, settings: { default_provider, language, auto_execute,
 *   backup_before_edit, max_context_files, planner, backend, dispatch,
 *   agent, context_budget, history, context_semantic, session_binding,
 *   execution, routing, retention, project_root_set,
 *   force_command_approval: {effective, explicit_in_config} } }
 *
 * عرض-فقط: لا أزرار تعديل ولا أي طلب كتابة — القيم تُرسم من JSON
 * الحي كما هي؛ الغائب (null/undefined) ⇒ UNKNOWN صريح لا اختراع.
 * التعديل عبر config.yaml + إعادة تشغيل (القارئ مُكاش — ملاحظة ظاهرة).
 * الأنماط تعيد استخدام أصناف pp-* القائمة (TSK-621) — صفر CSS جديدة.
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    /** قيمة للعرض: null/undefined ⇒ UNKNOWN صريح؛ bool ⇒ نعم/لا. */
    function fmtValue(v) {
        if (v === null || v === undefined) {
            return '<span class="pp-none">UNKNOWN — غير مضبوط</span>';
        }
        if (v === true) { return "نعم (true)"; }
        if (v === false) { return "لا (false)"; }
        return escapeHtml(v);
    }

    function row(key, valueHtml) {
        return '<div class="pp-row"><span class="pp-key">' +
            escapeHtml(key) + '</span><span class="pp-val">' +
            valueHtml + "</span></div>";
    }

    /** قسم من كائن مفاتيح⇒قيم؛ الكائن الغائب ⇒ UNKNOWN للقسم كله. */
    function renderObjectSection(title, obj, keys) {
        var html = '<div class="pp-section"><div class="pp-title">' +
            escapeHtml(title) + "</div>";
        if (!obj || typeof obj !== "object") {
            return html + '<div class="pp-none">UNKNOWN — ' +
                "القسم غائب من config</div></div>";
        }
        keys.forEach(function (k) {
            var v = obj[k];
            if (k === "command_allowlist" && v && typeof v === "object") {
                var names = Object.keys(v).sort();
                if (!names.length) {
                    html += row(k, '<span class="pp-none">قائمة فارغة</span>');
                } else {
                    names.forEach(function (name) {
                        html += '<div class="pp-row"><span class="pp-key">' +
                            escapeHtml(name) + '</span><code class="pp-cmd">' +
                            escapeHtml(v[name]) + "</code></div>";
                    });
                }
            } else {
                html += row(k, fmtValue(v));
            }
        });
        return html + "</div>";
    }

    function renderGeneralSection(s) {
        var html = '<div class="pp-section"><div class="pp-title">' +
            "⚙️ عام</div>";
        html += row("default_provider", fmtValue(s.default_provider));
        html += row("language", fmtValue(s.language));
        html += row("auto_execute", fmtValue(s.auto_execute));
        html += row("backup_before_edit", fmtValue(s.backup_before_edit));
        html += row("max_context_files", fmtValue(s.max_context_files));
        html += row("planner", fmtValue(s.planner));
        html += row("backend", fmtValue(s.backend));
        html += row("dispatch", fmtValue(s.dispatch));
        html += row("project_root", s.project_root_set
            ? "مضبوط (المسار لا يُعرض — عقد التطهير)"
            : "غير مضبوط — مجلد الخادم");
        return html + "</div>";
    }

    function renderApprovalSection(fca) {
        var html = '<div class="pp-section"><div class="pp-title">' +
            "🛡 إلزام الموافقة (force_command_approval)</div>";
        if (!fca || typeof fca !== "object") {
            return html + '<div class="pp-none">UNKNOWN — ' +
                "غائب من الاستجابة</div></div>";
        }
        html += row("القيمة الفعالة", fca.effective
            ? "مفعّل — كل أمر يمر بالبوابة"
            : "غير مفعّل (false صريح في config)");
        html += row("مصدرها", fca.explicit_in_config
            ? "صريحة في config.yaml"
            : "الافتراضي الآمن (fail-closed — غياب المفتاح)");
        return html + "</div>";
    }

    /** HTML اللوحة كاملة من JSON الاستجابة — نقي، عرض-فقط. */
    function renderPanelHTML(s) {
        if (!s) {
            return '<div class="pp-none">⚠️ تعذّر تحميل الإعدادات</div>';
        }
        return '<div class="pp-section"><div class="pp-none">' +
            "📖 عرض فقط — التعديل عبر config.yaml ثم إعادة تشغيل الخادم" +
            "</div></div>" +
            renderGeneralSection(s) +
            renderApprovalSection(s.force_command_approval) +
            renderObjectSection("🤖 Agent", s.agent,
                ["command_allowlist", "command_timeout_seconds",
                 "command_output_max_chars"]) +
            renderObjectSection("🧮 ميزانية السياق (context_budget)",
                s.context_budget,
                ["model_window", "reserved_output", "safety_margin"]) +
            renderObjectSection("🕘 التاريخ (history)", s.history,
                ["payload_last_n"]) +
            renderObjectSection("🔍 البحث الدلالي (context.semantic)",
                s.context_semantic,
                ["enabled", "timeout_seconds", "top_k"]) +
            renderObjectSection("🔗 ربط الجلسة (session_binding)",
                s.session_binding, ["warn_only", "policy"]) +
            renderObjectSection("⏱ التنفيذ (execution)", s.execution,
                ["stale_ttl_seconds"]) +
            renderObjectSection("🧭 التوجيه (routing)", s.routing,
                ["direct_max", "auto_chain_max", "full_chain_max",
                 "min_accounts_auto_chain", "min_accounts_full_chain",
                 "min_accounts_delegate", "version"]) +
            renderObjectSection("🗄 الاحتفاظ (retention)", s.retention,
                ["max_count", "max_age_days", "dry_run", "pinned_count"]);
    }

    var api = {
        fmtValue: fmtValue,
        renderPanelHTML: renderPanelHTML,
    };

    global.SettingsPanel = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
