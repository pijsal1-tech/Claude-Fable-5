/* TSK-620 (CP-8/UXF-05 §R9): سرد الجلسة — منطق نقي (UMD-lite،
 * قابل للاختبار في node). الـ DOM glue في app.js فقط.
 *
 * ── الفكرة ─────────────────────────────────────────────────────────────
 * timeline يجمع محطات الجلسة (طلب → خطة → موافقات → تنفيذ → نتائج →
 * استعادة) من **أطر WS الحية الموجودة** عبر المعالج الوحيد — التقاط
 * استهلاك-فقط بنفس عقد StatusChip.noteFrame حرفيًا: لا إطار يُعدَّل
 * ولا مسار case يتغير. محلي بالكامل، بلا cloud (Non-Goal §15.2).
 * سجل runs (TSK-610) يبقى مصدر p50/p95 المجمّعة — السرد طبقة عرض
 * فوق الأطر الحية في الذاكرة.
 *
 * ── تصنيف الأطر → محطات ────────────────────────────────────────────────
 * request (من الغراء عند الإرسال) · plan · approval (طلب/حكم) ·
 * execution (task_progress/chain_step/agent_step — تُدمج المتتالية
 * بعدّاد) · result (all_actions_done/done/chain_finished/agent_done/
 * error) · rollback (rollback_result).
 *
 * ── الحدود ─────────────────────────────────────────────────────────────
 * سقف MAX_ENTRIES (أقدم-يُطرد) — جلسة طويلة لا تراكم ذاكرة بلا حد
 * (نفس مبدأ MAX_PENDING في core/run_metrics).
 */
(function (global) {
    "use strict";

    var MAX_ENTRIES = 200;

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function createState() {
        return { entries: [] };
    }

    function _push(state, entry) {
        entry.ts = entry.ts || 0;
        state.entries.push(entry);
        while (state.entries.length > MAX_ENTRIES) state.entries.shift();
    }

    // محطة «طلب» — يستدعيها الغراء عند الإرسال (sendMessage).
    function noteRequest(state, text, nowSec) {
        if (!state) return false;
        var t = String(text || "").slice(0, 120);
        _push(state, { station: "request", label: t, ts: nowSec || 0 });
        return true;
    }

    // التقاط استهلاك-فقط من الأطر — يعيد true لو أُضيفت/حُدّثت محطة.
    function noteFrame(state, frame, nowSec) {
        if (!state || !frame || !frame.type) return false;
        var ts = nowSec || 0;
        switch (frame.type) {
            case "plan":
                _push(state, {
                    station: "plan",
                    label: String(frame.summary || "").slice(0, 120),
                    count: (frame.actions || []).length,
                    ts: ts,
                });
                return true;
            case "chain_approval_request":
                _push(state, { station: "approval", label: "طلب موافقة",
                               verdict: null, ts: ts });
                return true;
            case "chain_approval_verdict":
                _push(state, {
                    station: "approval",
                    label: frame.approved ? "موافقة" :
                        ("رفض" + (frame.reason ? " — " +
                            String(frame.reason).slice(0, 60) : "")),
                    verdict: !!frame.approved,
                    ts: ts,
                });
                return true;
            case "task_progress":
            case "chain_step":
            case "agent_step": {
                // دمج المتتالية: عدّاد بدل صف لكل خطوة (سرد لا سجل خام).
                var last = state.entries[state.entries.length - 1];
                if (last && last.station === "execution") {
                    last.count = (last.count || 1) + 1;
                    last.ts = ts;
                    return true;
                }
                _push(state, { station: "execution", label: "تنفيذ",
                               count: 1, ts: ts });
                return true;
            }
            case "all_actions_done":
            case "done":
            case "chain_finished":
            case "agent_done":
                _push(state, { station: "result", label: "اكتمل",
                               ok: true, ts: ts });
                return true;
            case "error":
                _push(state, {
                    station: "result",
                    label: "خطأ" + (frame.text ? " — " +
                        String(frame.text).slice(0, 60) : ""),
                    ok: false, ts: ts,
                });
                return true;
            case "rollback_result":
                _push(state, {
                    station: "rollback",
                    label: "استعادة — " + String(frame.status || ""),
                    ok: frame.status === "success", ts: ts,
                });
                return true;
            default:
                return false;
        }
    }

    function entries(state) {
        return state ? state.entries.slice() : [];
    }

    var STATION_ICON = {
        request: "💬", plan: "📋", approval: "🔏",
        execution: "⚙️", result: "🏁", rollback: "↩️",
    };

    // HTML نقي للسرد — الأقدم أولًا (قراءة زمنية طبيعية).
    function renderTimelineHTML(state) {
        var list = state ? state.entries : [];
        if (!list.length) {
            return '<div class="sn-empty">لا محطات بعد — أرسل طلبًا' +
                ' لبدء السرد</div>';
        }
        var out = ['<div class="sn-timeline">'];
        for (var i = 0; i < list.length; i++) {
            var e = list[i];
            var cls = "sn-item sn-" + e.station;
            if (e.ok === false || e.verdict === false) cls += " sn-bad";
            var label = escapeHtml(e.label || "");
            if (e.station === "execution" && e.count > 1) {
                label += " ×" + e.count;
            }
            if (e.station === "plan" && e.count) {
                label += " (" + e.count + " خطوة)";
            }
            out.push('<div class="' + cls + '"><span class="sn-icon">' +
                (STATION_ICON[e.station] || "•") + '</span> ' +
                label + "</div>");
        }
        out.push("</div>");
        return out.join("");
    }

    var SessionNarrative = {
        MAX_ENTRIES: MAX_ENTRIES,
        createState: createState,
        noteRequest: noteRequest,
        noteFrame: noteFrame,
        entries: entries,
        renderTimelineHTML: renderTimelineHTML,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = SessionNarrative;
    }
    global.SessionNarrative = SessionNarrative;
})(typeof globalThis !== "undefined" ? globalThis : this);
