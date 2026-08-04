/* TSK-733d (D-19-5): لوحة مهام طابور التفويض — منطق نقي (UMD-lite
 * بنمط background_tasks.js، قابل للاختبار في node). الـ DOM glue في
 * 10_chat_ws_stream.js فقط.
 *
 * ── مصادر البيانات (استهلاك فقط — صفر endpoints جديدة) ──────────────
 * 1. إطارات مقابض TSK-733a (أحداث DelegateQueue ملفوفة):
 *    - queue_started                { tasks_count, task_ids }
 *    - queue_task_started           { task_id, index, description }
 *    - queue_task_waiting_approval  { task_id, run_id }
 *    - queue_task_landed            { task_id, carried_facts }
 *    - queue_halted                 { reason, remaining }
 *    - queue_completed              { tasks_count }
 *    - queue_status                 { status, current_index, halt_reason,
 *                                     tasks: [...] } — snapshot كامل
 *      to_dict() reconnect-safe (يُطلب عند onopen).
 * 2. الحسم: اللوحة تُصدر نيّة land/reject عبر data-queue-action —
 *    الإرسال الفعلي مسؤولية الغراء (الثابت الصلب: لا كتابة إلا بعد
 *    queue_land صريح، والأفعال نفسها تبقى خلف أزرار Apply —
 *    طبقتا موافقة، لا اختزال). رفض = halt كامل (stop-and-ask).
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
            status: "none",   // none|running|waiting_approval|halted|completed
            haltReason: "",
            // مهام مرتبة: { taskId, description, status }
            // status: queued|running|waiting_approval|landed|rejected|
            //         failed|cancelled
            tasks: [],
        };
    }

    function _findTask(state, taskId) {
        for (var i = 0; i < state.tasks.length; i++) {
            if (state.tasks[i].taskId === taskId) return state.tasks[i];
        }
        return null;
    }

    // يلتقط ما يهم اللوحة من أي إطار WS وارد — يرجع true لو تغيّر شيء.
    function noteFrame(state, frame) {
        if (!frame || !frame.type) return false;
        switch (frame.type) {
            case "queue_started":
                state.status = "running";
                state.haltReason = "";
                state.tasks = (frame.task_ids || []).map(function (id) {
                    return { taskId: id, description: "", status: "queued" };
                });
                return true;
            case "queue_task_started": {
                var t1 = _findTask(state, frame.task_id);
                if (!t1) return false;
                t1.status = "running";
                if (frame.description) t1.description = frame.description;
                state.status = "running";
                return true;
            }
            case "queue_task_waiting_approval": {
                var t2 = _findTask(state, frame.task_id);
                if (!t2) return false;
                t2.status = "waiting_approval";
                state.status = "waiting_approval";
                return true;
            }
            case "queue_task_landed": {
                var t3 = _findTask(state, frame.task_id);
                if (!t3) return false;
                t3.status = "landed";
                state.status = "running";
                return true;
            }
            case "queue_halted":
                state.status = "halted";
                state.haltReason = frame.reason || "";
                // المهمة المنتظرة/الجارية صارت محسومة سلبًا — الخادم
                // هو الحقيقة؛ snapshot لاحق يصحح التفاصيل إن لزم.
                state.tasks.forEach(function (t) {
                    if (t.status === "waiting_approval"
                        || t.status === "running") {
                        t.status = "rejected";
                    }
                });
                return true;
            case "queue_completed":
                state.status = "completed";
                return true;
            case "queue_status":
                // snapshot كامل (reconnect) — الحقيقة من to_dict الحي.
                if (!frame.tasks || frame.status === "none") {
                    state.status = "none";
                    state.haltReason = "";
                    state.tasks = [];
                    return true;
                }
                state.status = frame.status;
                state.haltReason = frame.halt_reason || "";
                state.tasks = frame.tasks.map(function (t) {
                    return {
                        taskId: t.task_id,
                        description: t.description || "",
                        status: t.status,
                    };
                });
                return true;
        }
        return false;
    }

    // هل تُعرض اللوحة؟ (none = لا؛ الحالات النهائية تبقى معروضة حتى
    // يبدأ طابور جديد — المستخدم يرى خلاصة الخطة).
    function panelVisible(state) {
        return state.status !== "none";
    }

    var STATUS_ICONS = {
        queued: "⏸",
        running: "⏳",
        waiting_approval: "✋",
        landed: "✅",
        rejected: "❌",
        failed: "❌",
        cancelled: "🛑",
    };

    function taskIcon(status) {
        return STATUS_ICONS[status] || "•";
    }

    function panelTitle(state) {
        switch (state.status) {
            case "running": return "📋 طابور المهام — يعمل";
            case "waiting_approval": return "📋 طابور المهام — بانتظارك";
            case "halted": return "📋 طابور المهام — متوقف";
            case "completed": return "📋 طابور المهام — اكتمل ✅";
        }
        return "📋 طابور المهام";
    }

    // HTML اللوحة — زرّا الحسم يظهران فقط عند waiting_approval.
    // الأزرار تحمل data-queue-action (land|reject) — الغراء يفوّض النقر.
    function renderPanelHTML(state) {
        if (!panelVisible(state)) return "";
        var html = '<div class="queue-panel-title">' +
            escapeHtml(panelTitle(state)) + "</div>";
        html += '<ul class="queue-task-list">';
        state.tasks.forEach(function (t, i) {
            html += '<li class="queue-task queue-task-' +
                escapeHtml(t.status) + '">' +
                '<span class="queue-task-icon">' + taskIcon(t.status) +
                "</span> " +
                '<span class="queue-task-desc" title="' +
                escapeHtml(t.taskId) + '">' +
                (i + 1) + ". " +
                escapeHtml(t.description || t.taskId) + "</span>";
            if (t.status === "waiting_approval") {
                html += '<span class="queue-task-actions">' +
                    '<button class="queue-btn queue-land"' +
                    ' data-queue-action="land" title="اعتماد المهمة' +
                    ' (الأفعال تبقى خلف أزرار Apply)">✔ اعتماد</button>' +
                    '<button class="queue-btn queue-reject"' +
                    ' data-queue-action="reject" title="رفض — يوقف' +
                    ' الطابور كاملًا">✖ رفض</button></span>';
            }
            html += "</li>";
        });
        html += "</ul>";
        if (state.status === "halted" && state.haltReason) {
            html += '<div class="queue-halt-reason">⚠️ ' +
                escapeHtml(state.haltReason) + "</div>";
        }
        return html;
    }

    // رسالة toast عند حدث مفصلي (يستهلكها الغراء مرة واحدة لكل إطار).
    function frameToast(frame) {
        if (!frame || !frame.type) return null;
        switch (frame.type) {
            case "queue_task_landed":
                return { text: "✅ هبطت مهمة من الطابور — التالية تنطلق",
                         kind: "success" };
            case "queue_completed":
                return { text: "🏁 اكتمل طابور المهام كاملًا",
                         kind: "success" };
            case "queue_halted":
                return { text: "🛑 توقف الطابور" +
                         (frame.reason ? ": " + frame.reason : ""),
                         kind: "error" };
        }
        return null;
    }

    // تقسيم نص الإدخال إلى مهام (سطر = مهمة) — يتجاهل الأسطر الفارغة.
    function splitTasks(text) {
        return String(text || "").split("\n")
            .map(function (line) { return line.trim(); })
            .filter(function (line) { return line.length > 0; });
    }

    var api = {
        createState: createState,
        noteFrame: noteFrame,
        panelVisible: panelVisible,
        panelTitle: panelTitle,
        taskIcon: taskIcon,
        renderPanelHTML: renderPanelHTML,
        frameToast: frameToast,
        splitTasks: splitTasks,
    };

    global.QueuePanel = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
