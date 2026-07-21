/* T-114 (R-805): لوحة ذاكرة المشروع — فحص + تحرير. منطق نقي
 * (UMD-lite، قابل للاختبار في node بنمط run_history.js).
 * الـ DOM glue في app.js فقط.
 *
 * ── أطر WS (T-114 — إضافية، لا مساس بأي إطار قائم) ──────────────────
 * طلب:  { "type": "memory_list" }
 *       { "type": "memory_edit", "entry_id", "text"?, "kind"? }
 *       { "type": "memory_delete", "entry_id" }
 * ردّ:  memory_list_result   = { type, project_id?, entries: [
 *           {entry_id, kind, text, created_at, source, run_id, stale} ],
 *           error? }
 *       memory_edit_result   = { type, acknowledged, entry_id?, entry?, error? }
 *       memory_delete_result = { type, acknowledged, entry_id?, error? }
 *
 * ── الدلالات ─────────────────────────────────────────────────────────
 * provenance: source (agent_tool/distillation/user) + run_id + created_at.
 * staleness: stale=true فقط عند بصمتي فهرس حاضرتين مختلفتين — الشارة
 * «بنية المشروع تغيّرت» لا «المدخلة خاطئة». تعديل المستخدم يعيد ختم
 * البصمة (المخزن يفرضه) ⇒ الشارة تُمسح بعد الحفظ.
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // تسميات الأنواع — نفس ENTRY_KINDS في core/project_memory.py
    var KIND_LABELS = {
        fact: "حقيقة",
        convention: "اصطلاح",
        decision: "قرار",
        run_summary: "ملخّص run",
    };

    // تسميات المصادر — نفس KNOWN_SOURCES (provenance)
    var SOURCE_LABELS = {
        agent_tool: "أداة الـ agent",
        distillation: "تقطير آلي",
        user: "المستخدم",
    };

    function kindLabel(kind) {
        return KIND_LABELS[kind] || kind || "?";
    }

    function sourceLabel(source) {
        return SOURCE_LABELS[source] || source || "?";
    }

    // مدخلات اللوحة من إطار memory_list_result — كما وصلت (المخزن
    // append-only ⇒ الترتيب زمني أصلًا).
    function buildEntries(frameEntries) {
        return (frameEntries || []).map(function (e) {
            return {
                entry_id: e.entry_id || "",
                kind: e.kind || "",
                text: e.text || "",
                created_at: e.created_at || "",
                source: e.source || "",
                run_id: e.run_id || "",
                stale: !!e.stale,
            };
        });
    }

    function renderEntryHTML(entry, idx) {
        var stale = entry.stale
            ? '<span class="mp-badge mp-stale" title="بنية المشروع تغيّرت ' +
              'منذ حفظ هذه المدخلة — قد تكون قديمة">⚠ قديمة</span>'
            : "";
        var prov = '<span class="mp-prov" title="المصدر">' +
            escapeHtml(sourceLabel(entry.source)) + "</span>" +
            (entry.run_id
                ? '<span class="mp-prov mp-run" title="run الأصل">' +
                  escapeHtml(entry.run_id) + "</span>"
                : "") +
            (entry.created_at
                ? '<span class="mp-prov mp-ts" title="وقت الإنشاء">' +
                  escapeHtml(entry.created_at) + "</span>"
                : "");
        return '<div class="mp-entry" data-eid="' +
            escapeHtml(entry.entry_id) + '">' +
            '<div class="mp-entry-head">' +
            '<span class="mp-badge mp-kind">' + escapeHtml(kindLabel(entry.kind)) +
            "</span>" + stale +
            '<span class="spacer"></span>' +
            '<button class="mp-edit-btn" data-idx="' + idx +
            '" title="تحرير المدخلة">✏</button>' +
            '<button class="mp-delete-btn" data-idx="' + idx +
            '" title="حذف نهائي — لن تظهر في أي سياق تالٍ">🗑</button>' +
            "</div>" +
            '<div class="mp-text">' + escapeHtml(entry.text) + "</div>" +
            '<div class="mp-provenance">' + prov + "</div>" +
            "</div>";
    }

    // نموذج التحرير داخل بطاقة المدخلة — textarea + اختيار النوع.
    function renderEditFormHTML(entry, idx) {
        var options = Object.keys(KIND_LABELS).map(function (k) {
            return '<option value="' + k + '"' +
                (k === entry.kind ? " selected" : "") + ">" +
                escapeHtml(KIND_LABELS[k]) + "</option>";
        }).join("");
        return '<div class="mp-entry mp-editing" data-eid="' +
            escapeHtml(entry.entry_id) + '">' +
            '<div class="mp-entry-head">' +
            '<select class="mp-kind-select" data-idx="' + idx + '">' +
            options + "</select>" +
            '<span class="spacer"></span>' +
            '<button class="mp-save-btn" data-idx="' + idx +
            '" title="حفظ — provenance تصبح: المستخدم">💾 حفظ</button>' +
            '<button class="mp-cancel-btn" data-idx="' + idx +
            '" title="إلغاء التحرير">✕</button>' +
            "</div>" +
            '<textarea class="mp-text-edit" data-idx="' + idx + '">' +
            escapeHtml(entry.text) + "</textarea>" +
            "</div>";
    }

    function renderPanelHTML(entries, editingIdx) {
        if (!entries.length) {
            return '<div class="mp-empty">لا ذاكرة محفوظة لهذا المشروع بعد — ' +
                "تُملأ من أداة remember_fact أو تقطير ما-بعد-الـ run.</div>";
        }
        return entries.map(function (e, i) {
            return i === editingIdx
                ? renderEditFormHTML(e, i)
                : renderEntryHTML(e, i);
        }).join("");
    }

    // ── أطر الطلب — تُبنى هنا حصريًا (لا بناء يدوي في app.js) ──
    function listFrame() {
        return { type: "memory_list" };
    }

    function editFrame(entry, text, kind) {
        var frame = { type: "memory_edit", entry_id: entry.entry_id };
        if (text !== null && text !== undefined) frame.text = text;
        if (kind !== null && kind !== undefined) frame.kind = kind;
        return frame;
    }

    function deleteFrame(entry) {
        return { type: "memory_delete", entry_id: entry.entry_id };
    }

    // تحديث المدخلات من إطار memory_edit_result — مصدر الحقيقة الردّ
    // (المخزن أعاد ختم provenance/staleness). يعيد المدخلة أو null.
    function applyEditResult(entries, frame) {
        if (!frame.acknowledged || !frame.entry) return null;
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].entry_id === frame.entry.entry_id) {
                entries[i] = buildEntries([frame.entry])[0];
                return entries[i];
            }
        }
        return null;
    }

    // حذف من القائمة المحلية عند إطار memory_delete_result مؤكَّد.
    function applyDeleteResult(entries, frame) {
        if (!frame.acknowledged) return entries;
        return entries.filter(function (e) {
            return e.entry_id !== frame.entry_id;
        });
    }

    var api = {
        kindLabel: kindLabel,
        sourceLabel: sourceLabel,
        buildEntries: buildEntries,
        renderPanelHTML: renderPanelHTML,
        listFrame: listFrame,
        editFrame: editFrame,
        deleteFrame: deleteFrame,
        applyEditResult: applyEditResult,
        applyDeleteResult: applyDeleteResult,
    };

    global.MemoryPanel = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
