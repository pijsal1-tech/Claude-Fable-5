/* TSK-621 (CP-5/UXF-04 §R9): لوحة الصلاحيات (glass box)
 * + TSK-734d (القرار 6 من تسلسل D-19): وضع تحرير صريح.
 * منطق نقي (UMD-lite، قابل للاختبار في node بنمط memory_panel.js).
 * الـ DOM glue في app.js فقط.
 *
 * المصدر: GET /api/permissions (routes/meta.py) — يعيد
 * { ok, permissions: { command_allowlist: {enforce, entries, timeout_seconds,
 *   output_max_chars}, agent_tools: {safe, approval},
 *   terminal_commands: {safe, dangerous}, force_command_approval,
 *   approval_gate: {mode, auto_whitelist, timeout_seconds} | null } }
 *
 * العرض (renderPanelHTML) ما زال بلا أي أداة كتابة — التحرير في
 * نموذج منفصل صريح (renderEditFormHTML) بزر حفظ واحد
 * (data-perm-action="save")؛ الحفظ POST /api/permissions عبر الـ glue
 * واللوحة تعيد الرسم من الحقيقة المعادة (لا افتراض تفاؤلي).
 * المفتاحان القابلان للتحرير فقط (whitelist الخادم):
 * force_command_approval + agent.command_allowlist — الباقي عرض-فقط.
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // تسميات أوضاع ApprovalGate — نفس VALID_MODES في core/approval.py
    var GATE_MODE_LABELS = {
        auto: "تلقائي (auto)",
        interactive: "تفاعلي (interactive)",
        deny: "رفض الكل (deny)",
    };

    function gateModeLabel(mode) {
        return GATE_MODE_LABELS[mode] || String(mode);
    }

    function renderChips(items, cls) {
        if (!items || !items.length) {
            return '<span class="pp-none">— لا شيء —</span>';
        }
        return items.map(function (it) {
            return '<span class="pp-chip ' + cls + '">' +
                escapeHtml(it) + "</span>";
        }).join("");
    }

    function renderAllowlistSection(al) {
        var html = '<div class="pp-section"><div class="pp-title">' +
            "🗂 قائمة أوامر الـ Agent (command_allowlist)</div>";
        if (!al) {
            return html + '<div class="pp-none">UNKNOWN — ' +
                "القسم غائب من الاستجابة</div></div>";
        }
        html += '<div class="pp-row"><span class="pp-key">الإنفاذ</span>' +
            '<span class="pp-val">' +
            (al.enforce
                ? "مفعّل — الأوامر المذكورة فقط"
                : "legacy — بوابة الموافقة وحدها تحكم") +
            "</span></div>";
        var entries = al.entries || {};
        var names = Object.keys(entries).sort();
        if (names.length) {
            names.forEach(function (name) {
                html += '<div class="pp-row"><span class="pp-key">' +
                    escapeHtml(name) + '</span><code class="pp-cmd">' +
                    escapeHtml(entries[name]) + "</code></div>";
            });
        } else {
            html += '<div class="pp-none">قائمة فارغة</div>';
        }
        html += '<div class="pp-row"><span class="pp-key">المهلة</span>' +
            '<span class="pp-val">' + escapeHtml(al.timeout_seconds) +
            " ثانية</span></div>" +
            '<div class="pp-row"><span class="pp-key">سقف المخرجات</span>' +
            '<span class="pp-val">' + escapeHtml(al.output_max_chars) +
            " حرف</span></div></div>";
        return html;
    }

    function renderToolsSection(tools) {
        var t = tools || {};
        return '<div class="pp-section"><div class="pp-title">' +
            "🔧 أدوات الـ Agent</div>" +
            '<div class="pp-row"><span class="pp-key">آمنة (فورية)</span>' +
            '<span class="pp-val">' + renderChips(t.safe, "pp-safe") +
            "</span></div>" +
            '<div class="pp-row"><span class="pp-key">تتطلب موافقة</span>' +
            '<span class="pp-val">' + renderChips(t.approval, "pp-danger") +
            "</span></div></div>";
    }

    function renderCommandsSection(cmds) {
        var c = cmds || {};
        return '<div class="pp-section"><div class="pp-title">' +
            "⌨️ أوامر الطرفية</div>" +
            '<div class="pp-row"><span class="pp-key">آمنة (SAFE)</span>' +
            '<span class="pp-val">' + renderChips(c.safe, "pp-safe") +
            "</span></div>" +
            '<div class="pp-row"><span class="pp-key">خطرة (DANGEROUS)</span>' +
            '<span class="pp-val">' + renderChips(c.dangerous, "pp-danger") +
            "</span></div></div>";
    }

    function renderGateSection(perms) {
        var html = '<div class="pp-section"><div class="pp-title">' +
            "🛡 بوابة الموافقة (ApprovalGate)</div>" +
            '<div class="pp-row"><span class="pp-key">إلزام موافقة ' +
            'الأوامر</span><span class="pp-val">' +
            (perms.force_command_approval
                ? "مفعّل (force_command_approval)"
                : "غير مفعّل (افتراضي)") +
            "</span></div>";
        var gate = perms.approval_gate;
        if (!gate) {
            return html + '<div class="pp-none">البوابة غير مهيأة بعد ' +
                "(قبل الإقلاع)</div></div>";
        }
        html += '<div class="pp-row"><span class="pp-key">الوضع</span>' +
            '<span class="pp-val">' + escapeHtml(gateModeLabel(gate.mode)) +
            "</span></div>" +
            '<div class="pp-row"><span class="pp-key">اعتماد تلقائي لـ</span>' +
            '<span class="pp-val">' +
            renderChips(gate.auto_whitelist, "pp-safe") + "</span></div>" +
            '<div class="pp-row"><span class="pp-key">مهلة القرار</span>' +
            '<span class="pp-val">' + escapeHtml(gate.timeout_seconds) +
            " ثانية</span></div></div>";
        return html;
    }

    /** HTML اللوحة كاملة من JSON الاستجابة — نقي، عرض-فقط. */
    function renderPanelHTML(perms) {
        if (!perms) {
            return '<div class="pp-none">⚠️ تعذّر تحميل السياسة</div>';
        }
        return renderAllowlistSection(perms.command_allowlist) +
            renderToolsSection(perms.agent_tools) +
            renderCommandsSection(perms.terminal_commands) +
            renderGateSection(perms);
    }

    // ── TSK-734d: وضع التحرير — نموذج صريح بزر حفظ واحد ──

    /** نص allowlist للنموذج: سطر لكل مدخل بصيغة `name = command`. */
    function allowlistToText(entries) {
        var e = entries || {};
        return Object.keys(e).sort().map(function (name) {
            return name + " = " + e[name];
        }).join("\n");
    }

    /** تحليل نص النموذج → {ok, entries} | {ok:false, error} — نقي.
     * سطور فارغة تُتجاهل؛ سطر بلا `=` أو باسم/أمر فارغ ⇒ خطأ صريح
     * (fail-closed محليًا — الخادم يتحقق مجددًا على أي حال). */
    function parseAllowlistText(text) {
        var entries = {};
        var lines = String(text || "").split("\n");
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) { continue; }
            var eq = line.indexOf("=");
            if (eq < 0) {
                return { ok: false,
                         error: "سطر " + (i + 1) + ": الصيغة name = command" };
            }
            var name = line.slice(0, eq).trim();
            var cmd = line.slice(eq + 1).trim();
            if (!name || !cmd) {
                return { ok: false,
                         error: "سطر " + (i + 1) + ": اسم وأمر غير فارغين" };
            }
            entries[name] = cmd;
        }
        return { ok: true, entries: entries };
    }

    /** جسم POST من قيم النموذج — نقي. يعيد {ok, payload} | {ok:false,
     * error}. المفتاحان المسموحان فقط (whitelist الخادم هو الحكم). */
    function buildOverridesPayload(forceChecked, allowlistText) {
        var parsed = parseAllowlistText(allowlistText);
        if (!parsed.ok) { return parsed; }
        return {
            ok: true,
            payload: { overrides: {
                "force_command_approval": !!forceChecked,
                "agent.command_allowlist": parsed.entries,
            } },
        };
    }

    /** HTML نموذج التحرير — نقي. زر حفظ واحد + إلغاء؛ الـ glue يلتقط
     * data-perm-action (save/cancel) ويرسل POST ويعيد الرسم من
     * الحقيقة المعادة. */
    function renderEditFormHTML(perms) {
        var p = perms || {};
        var al = p.command_allowlist || {};
        return '<div class="pp-section"><div class="pp-title">' +
            "✏️ تحرير الأذونات (overrides فوق config.yaml)</div>" +
            '<label class="pp-edit-row">' +
            '<input type="checkbox" id="pp-edit-force"' +
            (p.force_command_approval ? " checked" : "") + "> " +
            "إلزام الموافقة على كل أمر (force_command_approval)</label>" +
            '<div class="pp-edit-row"><span class="pp-key">' +
            "قائمة أوامر الـ Agent</span>" +
            '<textarea id="pp-edit-allowlist" class="pp-edit-text" rows="6" ' +
            'dir="ltr" spellcheck="false" placeholder="name = command">' +
            escapeHtml(allowlistToText(al.entries)) + "</textarea></div>" +
            '<div class="pp-none">المفتاحان أعلاه فقط قابلان للتحرير — ' +
            "تُحفظ كـ overrides جانبية؛ config.yaml لا يُمس.</div>" +
            '<div class="pp-edit-actions">' +
            '<button class="pp-edit-btn pp-edit-save" ' +
            'data-perm-action="save">💾 حفظ</button>' +
            '<button class="pp-edit-btn" data-perm-action="cancel">' +
            "إلغاء</button></div>" +
            '<div id="pp-edit-error" class="pp-edit-error hidden"></div>' +
            "</div>";
    }

    var api = {
        gateModeLabel: gateModeLabel,
        renderPanelHTML: renderPanelHTML,
        allowlistToText: allowlistToText,
        parseAllowlistText: parseAllowlistText,
        buildOverridesPayload: buildOverridesPayload,
        renderEditFormHTML: renderEditFormHTML,
    };

    global.PermissionsPanel = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
