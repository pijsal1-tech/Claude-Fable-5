/* TSK-723 (P2-1/D-10): Command Palette (Ctrl+Shift+P) — منطق نقي.
 * (UMD-lite، قابل للاختبار في node — نمط settings_panel.js).
 * الـ DOM glue في app.js فقط.
 *
 * العقد: سجل أوامر **ساكن** — كل عنصر {id, label, hint, action} حيث
 * action = **اسم دالة UI قائمة** في app.js (لا سلاسل eval ولا كود)؛
 * الغراء ينفّذ عبر lookup صريح في جدول أفعال مسموحة. صفر endpoints
 * جديدة وصفر منطق أعمال — اللوحة تستدعي أفعال الواجهة القائمة فقط.
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    /** سجل الأوامر الساكن — action = اسم دالة UI قائمة في app.js. */
    var COMMANDS = [
        { id: "quick-open", label: "بحث سريع في المشروع (Quick Open)",
          hint: "Ctrl+K", action: "openQuickOpenModal" },
        { id: "settings", label: "الإعدادات (عرض فقط)",
          hint: "", action: "toggleSettingsPanel" },
        { id: "permissions", label: "الصلاحيات (عرض فقط)",
          hint: "", action: "togglePermissionsPanel" },
        { id: "diagnostics", label: "تنزيل حزمة التشخيص (JSON)",
          hint: "", action: "downloadDiagnostics" },
        { id: "run-history", label: "سجل التشغيلات (Run History)",
          hint: "", action: "toggleRunHistory" },
        { id: "memory", label: "ذاكرة المشروع",
          hint: "", action: "toggleMemoryPanel" },
        { id: "sessions", label: "الجلسات (فتح/تبديل)",
          hint: "", action: "toggleSessions" },
        { id: "new-session", label: "جلسة محادثة جديدة",
          hint: "", action: "newSession" },
        { id: "open-folder", label: "فتح مجلد مشروع",
          hint: "", action: "openFolder" },
        { id: "new-file", label: "ملف جديد",
          hint: "", action: "createNewFile" },
        { id: "new-folder", label: "مجلد جديد",
          hint: "", action: "createNewFolder" },
        { id: "theme", label: "تغيير الثيم",
          hint: "", action: "toggleThemePicker" },
        { id: "model", label: "تبديل النموذج (Model)",
          hint: "", action: "toggleModelPicker" },
        { id: "status", label: "شريحة الحالة (التوجيه/السعة)",
          hint: "", action: "toggleStatusChip" },
        { id: "clear-chat", label: "مسح المحادثة الحالية",
          hint: "", action: "clearChat" },
    ];

    /** ترشيح نصي بسيط: استعلام فارغ ⇒ الكل؛ وإلا احتواء غير حساس
     *  لحالة الأحرف في label أو id. */
    function filterCommands(query, commands) {
        var list = commands || COMMANDS;
        var q = String(query || "").trim().toLowerCase();
        if (!q) { return list.slice(); }
        return list.filter(function (c) {
            return c.label.toLowerCase().indexOf(q) !== -1 ||
                c.id.toLowerCase().indexOf(q) !== -1;
        });
    }

    /** HTML قائمة الأوامر — نقي؛ التنفيذ عبر data-cmd-id لا onclick
     *  بسلاسل مضمّنة (الغراء يربط النقر عبر التفويض). */
    function renderListHTML(items, selectedIndex) {
        if (!items || !items.length) {
            return '<div class="quick-open-empty">لا أوامر مطابقة</div>';
        }
        return items.map(function (c, idx) {
            var sel = idx === selectedIndex ? " selected" : "";
            var hint = c.hint
                ? '<kbd class="quick-open-kbd">' + escapeHtml(c.hint) +
                  "</kbd>"
                : "";
            return '<div class="quick-open-item cp-item' + sel +
                '" data-index="' + idx + '" data-cmd-id="' +
                escapeHtml(c.id) + '">' +
                '<div class="quick-open-info">' +
                '<span class="quick-open-name">' + escapeHtml(c.label) +
                "</span></div>" + hint + "</div>";
        }).join("");
    }

    var api = {
        COMMANDS: COMMANDS,
        filterCommands: filterCommands,
        renderListHTML: renderListHTML,
    };

    global.CommandPalette = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
