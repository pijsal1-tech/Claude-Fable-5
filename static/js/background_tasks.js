/* TSK-732d (D-19-4): شارة المهام الخلفية — منطق نقي (UMD-lite بنمط
 * status_chip.js، قابل للاختبار في node). الـ DOM glue في
 * 10_chat_ws_stream.js فقط.
 *
 * ── مصادر البيانات (استهلاك فقط — صفر endpoints جديدة) ──────────────
 * 1. إطارات المقابض الجديدة (TSK-732a):
 *    - background_started  { task_id, request }
 *    - background_event    { task_id, event, data } — أحداث الجسر ملفوفة
 *    - background_finished { task_id, status } — running انتهت إلى
 *      waiting_approval / landed / rejected / failed / cancelled
 *    - background_status   { task_id, status, error, events, run, ... }
 *      — snapshot كامل reconnect-safe (يُطلب عند onopen).
 * 2. الحسم: الشارة تُصدر نيّة approve/reject عبر data-bg-action —
 *    الإرسال الفعلي مسؤولية الغراء (الثابت الصلب: لا كتابة إلا بعد
 *    background_approve صريح، والأفعال نفسها تبقى خلف أزرار Apply —
 *    طبقتا موافقة، لا اختزال).
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function createState() {
        return {
            taskId: null,       // معرّف المهمة الحالية (null = لا مهمة)
            status: "none",     // none|running|waiting_approval|landed|rejected|failed|cancelled
            request: "",        // نص الطلب (للتلميح)
            lastEvent: "",      // آخر حدث جسر (للعرض الحي أثناء running)
            error: "",
        };
    }

    // الحالات النهائية — الشارة تختفي بعد toast (الغراء يقرر التوقيت).
    var TERMINAL = { landed: 1, rejected: 1, failed: 1, cancelled: 1 };

    function isTerminal(status) {
        return TERMINAL[status] === 1;
    }

    // يلتقط ما يهم الشارة من أي إطار WS وارد — يرجع true لو تغيّر شيء.
    function noteFrame(state, frame) {
        if (!frame || !frame.type) return false;
        switch (frame.type) {
            case "background_started":
                state.taskId = frame.task_id || null;
                state.status = "running";
                state.request = frame.request || "";
                state.lastEvent = "";
                state.error = "";
                return true;
            case "background_event":
                if (frame.task_id && frame.task_id !== state.taskId) {
                    return false; // حدث مهمة أخرى (دفاعي)
                }
                state.lastEvent = frame.event || "";
                return true;
            case "background_finished":
                if (frame.task_id && frame.task_id !== state.taskId) {
                    return false;
                }
                state.status = frame.status || "failed";
                return true;
            case "background_status":
                // snapshot كامل (reconnect) — الحقيقة من الكائن الحي،
                // لا من ذاكرة جلسة قد تكون انقطعت.
                if (!frame.task_id || frame.status === "none") {
                    state.taskId = null;
                    state.status = "none";
                    state.request = "";
                    state.lastEvent = "";
                    state.error = "";
                    return true;
                }
                state.taskId = frame.task_id;
                state.status = frame.status;
                state.error = frame.error || "";
                if (frame.events && frame.events.length) {
                    var first = frame.events[0];
                    if (first && first.request) state.request = first.request;
                }
                return true;
        }
        return false;
    }

    // هل تُعرض الشارة؟ (none والحالات النهائية بعد الـ toast = لا)
    function chipVisible(state) {
        return state.status === "running"
            || state.status === "waiting_approval";
    }

    function chipLabel(state) {
        if (state.status === "running") {
            return "⏳ تفويض خلفي يعمل" +
                (state.lastEvent
                    ? " · " + escapeHtml(state.lastEvent) : "");
        }
        if (state.status === "waiting_approval") {
            return "✋ مهمة خلفية بانتظارك";
        }
        return "";
    }

    // HTML الشارة — أزرار الحسم تظهر فقط عند waiting_approval.
    // الأزرار تحمل data-bg-action (approve|reject) — الغراء يفوّض النقر.
    function renderChipHTML(state) {
        if (!chipVisible(state)) return "";
        var html = '<span class="bg-chip-label" title="' +
            escapeHtml(state.request) + '">' + chipLabel(state) + "</span>";
        if (state.status === "waiting_approval") {
            html += '<button class="bg-chip-btn bg-approve"' +
                ' data-bg-action="approve" title="اعتماد نتيجة المهمة' +
                ' (الأفعال تبقى خلف أزرار Apply)">✔ اعتماد</button>' +
                '<button class="bg-chip-btn bg-reject"' +
                ' data-bg-action="reject" title="رفض النتيجة">✖ رفض</button>';
        }
        return html;
    }

    // رسالة الـ toast عند بلوغ حالة نهائية (يستهلكها الغراء مرة واحدة).
    function terminalToast(status, error) {
        switch (status) {
            case "landed":
                return { text: "✅ هبطت المهمة الخلفية — راجع الإجراءات",
                         kind: "success" };
            case "rejected":
                return { text: "❌ رُفضت المهمة الخلفية", kind: "info" };
            case "failed":
                return { text: "⚠️ فشلت المهمة الخلفية" +
                         (error ? ": " + error : ""), kind: "error" };
            case "cancelled":
                return { text: "🛑 أُلغيت المهمة الخلفية", kind: "info" };
        }
        return null;
    }

    var api = {
        createState: createState,
        noteFrame: noteFrame,
        isTerminal: isTerminal,
        chipVisible: chipVisible,
        chipLabel: chipLabel,
        renderChipHTML: renderChipHTML,
        terminalToast: terminalToast,
    };

    global.BackgroundTasks = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
