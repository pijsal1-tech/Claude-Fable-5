/* T-066 (R-902): لوحة تاريخ الـ runs + الاستعادة بنقرة — منطق نقي
 * (UMD-lite، قابل للاختبار في node بنمط file_icons/diff_panel).
 * الـ DOM glue في app.js فقط.
 *
 * ── مصادر البيانات (قراءة فقط — صفر endpoints تنفيذية جديدة) ─────────
 * GET /api/rollback/history → { ok, runs: [ {run_id, ts,
 *     files: [{path, pre_sha256, post_sha256, size}]} ] }  (الأحدث أولًا)
 * GET /api/rollback/preview?run_id=&path= → { ok, absent, snapshot }
 *
 * ── أوامر التنفيذ (أطر WS الموجودة منذ T-054 — بلا أي تغيير) ─────────
 * { "type": "rollback_run",  "run_id": "<id>" }
 * { "type": "rollback_file", "run_id": "<id>", "path": "<مسار مطلق>" }
 * والنتيجة إطار rollback_result = RestoreReport.to_dict():
 * { "type": "rollback_result", "run_id", "status": "success|partial|refused",
 *   "restored": [paths], "conflicts": [{path, expected_sha256,
 *   actual_sha256, reason}] }
 *
 * ── تأكيد الاستعادة (يعيد استخدام لوحة T-065) ────────────────────────
 * confirmActions يبني أفعالًا صناعية بصيغة DiffPanel.openState نفسها:
 * write بمحتوى الـ snapshot (القرص الحالي → ما-قبل-الكتابة) أو delete
 * لملف أنشأه الـ run (absent) — فالمستخدم يرى بايتات الاستعادة قبلها.
 * الاستعادة كلها في نقرتين: (1) زر الاستعادة → (2) تأكيد فوق الـ diff.
 */
(function (global) {
    "use strict";

    var FileIconsRef;
    if (typeof window !== "undefined" && window.FileIcons) {
        FileIconsRef = window.FileIcons;
    } else {
        FileIconsRef = require("./file_icons.js");
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function fileIconSVG(path) {
        var icon = FileIconsRef.getFileIcon(path);
        return '<svg class="file-icon" style="color: var(' + icon.colorToken +
            ')" aria-hidden="true"><use href="/static/icons/sprite.svg' +
            icon.symbol + '"></use></svg>';
    }

    // عمر مقروء — "الآن" / "منذ 5 د" / "منذ 3 س" / "منذ 2 يوم"
    function humanAge(tsSec, nowSec) {
        if (!tsSec) return "";
        var s = Math.max(0, nowSec - tsSec);
        if (s < 60) return "الآن";
        if (s < 3600) return "منذ " + Math.floor(s / 60) + " د";
        if (s < 86400) return "منذ " + Math.floor(s / 3600) + " س";
        return "منذ " + Math.floor(s / 86400) + " يوم";
    }

    // مدخلات اللوحة من رد /api/rollback/history — الأحدث أولًا كما وصل.
    // state لكل مدخل: "available" → "rolled_back" | "partial" | "refused".
    function buildEntries(runs, nowSec) {
        return (runs || []).map(function (r) {
            return {
                run_id: r.run_id,
                ts: r.ts || 0,
                age: humanAge(r.ts || 0, nowSec),
                files: (r.files || []).map(function (f) {
                    return { path: f.path, size: f.size || 0,
                             created: f.pre_sha256 === null,
                             state: "available" };
                }),
                state: "available",
            };
        });
    }

    // اسم قصير للعرض — الـ checkpoints تخزن مسارات مطلقة.
    function shortPath(path, projectRoot) {
        var p = String(path);
        if (projectRoot && p.indexOf(projectRoot) === 0) {
            p = p.slice(projectRoot.length).replace(/^[/\\]+/, "");
        }
        return p;
    }

    function renderEntryHTML(entry, idx, projectRoot) {
        var stateBadge = {
            available: "",
            rolled_back: '<span class="rh-badge rh-ok">مُستعاد</span>',
            partial: '<span class="rh-badge rh-warn">جزئي</span>',
            refused: '<span class="rh-badge rh-err">مرفوض</span>',
        }[entry.state] || "";
        var disabled = entry.state === "rolled_back" ? " disabled" : "";
        var html =
            '<div class="rh-entry" data-run="' + escapeHtml(entry.run_id) + '">' +
            '<div class="rh-entry-head">' +
            '<span class="rh-run-id">' + escapeHtml(entry.run_id) + '</span>' +
            '<span class="rh-age">' + escapeHtml(entry.age) + '</span>' +
            stateBadge +
            '<span class="spacer"></span>' +
            '<button class="rh-rollback-run" data-idx="' + idx + '"' + disabled +
            ' title="استعادة كل ملفات الـ run">↩ استعادة الكل</button>' +
            '</div><div class="rh-files">';
        entry.files.forEach(function (f, fi) {
            var fstate = f.state === "restored"
                ? '<span class="rh-badge rh-ok">✓</span>'
                : f.state === "conflict"
                    ? '<span class="rh-badge rh-err">تعارض</span>' : "";
            html += '<div class="rh-file">' + fileIconSVG(f.path) +
                '<span class="rh-file-path" title="' + escapeHtml(f.path) + '">' +
                escapeHtml(shortPath(f.path, projectRoot)) + '</span>' +
                (f.created ? '<span class="rh-badge rh-new">أنشأه الـ run</span>' : "") +
                fstate +
                '<span class="spacer"></span>' +
                '<button class="rh-rollback-file" data-idx="' + idx +
                '" data-fidx="' + fi + '"' + disabled +
                ' title="استعادة هذا الملف فقط">↩</button></div>';
        });
        return html + "</div></div>";
    }

    function renderPanelHTML(entries, projectRoot) {
        if (!entries.length) {
            return '<div class="rh-empty">لا توجد runs مُطبَّقة بعد — ' +
                "المدخلات المُقلَّمة بسياسة الاحتفاظ لا تُعرض.</div>";
        }
        return entries.map(function (e, i) {
            return renderEntryHTML(e, i, projectRoot);
        }).join("");
    }

    // ── أطر التنفيذ — تُبنى هنا حصريًا (لا بناء يدوي في app.js) ──
    function rollbackFrame(entry, fileIdx) {
        if (fileIdx === null || fileIdx === undefined) {
            return { type: "rollback_run", run_id: entry.run_id };
        }
        return { type: "rollback_file", run_id: entry.run_id,
                 path: entry.files[fileIdx].path };
    }

    // أفعال تأكيد الاستعادة — بصيغة DiffPanel.openState (إعادة استخدام
    // لوحة T-065): القرص الحالي (old) → نص الـ snapshot (payload).
    // previews: { path: {absent, snapshot} }، currents: { path: نص القرص }.
    function confirmActions(entry, fileIdx, previews, currents) {
        var files = fileIdx === null || fileIdx === undefined
            ? entry.files : [entry.files[fileIdx]];
        var actions = [], oldContents = {};
        files.forEach(function (f) {
            var pv = (previews || {})[f.path] || {};
            oldContents[f.path] = (currents || {})[f.path] || "";
            actions.push(pv.absent
                ? { kind: "delete", target: f.path, payload: "",
                    summary: "الاستعادة تحذفه (أنشأه الـ run)" }
                : { kind: "write", target: f.path,
                    payload: pv.snapshot || "",
                    summary: "استعادة لبايتات ما-قبل-الكتابة" });
        });
        return { actions: actions, oldContents: oldContents };
    }

    // تحديث المدخلات من إطار rollback_result — مصدر الحقيقة التقرير.
    function applyRollbackResult(entries, frame) {
        var entry = null;
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].run_id === frame.run_id) { entry = entries[i]; break; }
        }
        if (!entry) return null;
        var restored = frame.restored || [];
        var conflicts = (frame.conflicts || []).map(function (c) { return c.path; });
        entry.files.forEach(function (f) {
            if (restored.indexOf(f.path) >= 0) f.state = "restored";
            else if (conflicts.indexOf(f.path) >= 0) f.state = "conflict";
        });
        if (frame.status === "success") {
            // per-file لا يقلب حالة الـ run كله إلا لو استُعيدت كل الملفات
            var allRestored = entry.files.every(function (f) {
                return f.state === "restored";
            });
            entry.state = allRestored ? "rolled_back" : "available";
        } else {
            entry.state = frame.status; // partial | refused
        }
        return entry;
    }

    // تقرير تعارض مقروء — أبدًا ليس JSON خامًا (بند قبول R-902).
    function conflictReportHTML(frame) {
        var conflicts = frame.conflicts || [];
        if (!conflicts.length) return "";
        var html = '<div class="rh-conflict-report"><div class="rh-conflict-title">' +
            "⚠️ رفض الاستعادة — الملفات التالية تغيّرت خارج الـ run:</div>";
        conflicts.forEach(function (c) {
            html += '<div class="rh-conflict">' +
                (c.path ? fileIconSVG(c.path) : "") +
                '<span class="rh-file-path">' + escapeHtml(c.path || "(عام)") +
                "</span><span class=\"rh-conflict-reason\">" +
                escapeHtml(c.reason || "") + "</span></div>";
        });
        return html + "</div>";
    }

    var api = {
        humanAge: humanAge,
        buildEntries: buildEntries,
        shortPath: shortPath,
        renderPanelHTML: renderPanelHTML,
        rollbackFrame: rollbackFrame,
        confirmActions: confirmActions,
        applyRollbackResult: applyRollbackResult,
        conflictReportHTML: conflictReportHTML,
    };

    global.RunHistory = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
