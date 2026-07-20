/* T-065 (R-901): لوحة مراجعة الـ Diff — منطق اللوحة كوحدة نقية (UMD-lite،
 * قابلة للاختبار في node بنفس نمط file_icons/code_highlight). الـ DOM glue
 * في app.js فقط.
 *
 * ── Payload schema (مثبّت — اختبار يفحص هذا التوثيق) ──────────────────
 * الإطار الوارد `chain_approval_request` (من ApprovalGate عبر bridge):
 *   {
 *     "type": "chain_approval_request",
 *     "request_id": "<uuid>",
 *     "source": "chain",
 *     "run_id": "<run id>",
 *     "payload_hash": "<sha256 حتمي للأفعال>",
 *     "actions": [ {"kind": "write|delete|command|...",
 *                   "target": "<path or command>",
 *                   "payload": "<new content / args>",
 *                   "summary": "<وصف مقروء>"} ]
 *   }
 * الإطار الصادر `chain_approval_response` (إلى server.py → gate.resolve):
 *   { "type": "chain_approval_response",
 *     "request_id": "<نفس القيمة حرفيًا>",
 *     "approved": true|false,
 *     "payload_hash": "<نفس القيمة حرفيًا>" }
 *
 * ── دلالة القرار (1:1 مع البوابة) ─────────────────────────────────────
 * ApprovalGate ذرّية على مستوى الطلب: إطار واحد approved: true/false —
 * لا قبول جزئيًا في البروتوكول. لذلك toggles الملفات أداة مراجعة:
 * "تأكيد القرار" يرسل approved:true فقط إذا كانت **كل** الملفات مقبولة؛
 * أي ملف مرفوض ⇒ approved:false للدفعة كلها (المحافظ الأمين للبروتوكول).
 * أزرار الدفعة (قبول الكل/رفض الكل) ترسل القرار مباشرة.
 *
 * الإبراز: ألوان الصياغة عبر CodeHighlight (كاش LRU يجعل الأسطر المكررة
 * رخيصة) مطبّقة سطرًا بسطر **تحت** خلفيات add/del (توكنز --diff-*).
 */
(function (global) {
    "use strict";

    var CodeHighlightRef, FileIconsRef;
    if (typeof window !== "undefined" && window.CodeHighlight) {
        CodeHighlightRef = window.CodeHighlight;
        FileIconsRef = window.FileIcons;
    } else {
        CodeHighlightRef = require("./code_highlight.js");
        FileIconsRef = require("./file_icons.js");
    }

    var MAX_MYERS_D = 1500; // سقف مسافة التحرير قبل السقوط للبديل الخطي

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // ── Myers O(ND) على مستوى الأسطر (بعد قصّ البادئة/اللاحقة المشتركة) ──
    function myersOps(a, b) {
        var n = a.length, m = b.length;
        if (n === 0) return b.map(function (_, j) { return ["+", 0, j]; });
        if (m === 0) return a.map(function (_, i) { return ["-", i, 0]; });
        var max = Math.min(n + m, MAX_MYERS_D);
        var offset = max;
        var v = new Array(2 * max + 1).fill(0);
        var trace = [];
        for (var d = 0; d <= max; d++) {
            trace.push(v.slice());
            for (var k = -d; k <= d; k += 2) {
                var x;
                if (k === -d || (k !== d && v[offset + k - 1] < v[offset + k + 1])) {
                    x = v[offset + k + 1];
                } else {
                    x = v[offset + k - 1] + 1;
                }
                var y = x - k;
                while (x < n && y < m && a[x] === b[y]) { x++; y++; }
                v[offset + k] = x;
                if (x >= n && y >= m) {
                    return backtrack(a, b, trace, d, offset);
                }
            }
        }
        // تجاوز السقف: بديل خطي (حذف الكل + إضافة الكل) — يظل صحيحًا.
        var ops = [];
        for (var i = 0; i < n; i++) ops.push(["-", i, 0]);
        for (var j = 0; j < m; j++) ops.push(["+", 0, j]);
        return ops;
    }

    function backtrack(a, b, trace, d, offset) {
        var ops = [];
        var x = a.length, y = b.length;
        for (var depth = d; depth > 0; depth--) {
            var v = trace[depth];
            var k = x - y;
            var prevK;
            if (k === -depth || (k !== depth && v[offset + k - 1] < v[offset + k + 1])) {
                prevK = k + 1;
            } else {
                prevK = k - 1;
            }
            var prevX = v[offset + prevK];
            var prevY = prevX - prevK;
            while (x > prevX && y > prevY) {
                ops.push(["=", x - 1, y - 1]); x--; y--;
            }
            if (x === prevX) { ops.push(["+", x, y - 1]); y--; }
            else { ops.push(["-", x - 1, y]); x--; }
        }
        while (x > 0 && y > 0) { ops.push(["=", x - 1, y - 1]); x--; y--; }
        while (x > 0) { ops.push(["-", x - 1, 0]); x--; }
        while (y > 0) { ops.push(["+", 0, y - 1]); y--; }
        return ops.reverse();
    }

    // diff أسطر كامل → صفوف {type: "ctx"|"add"|"del", oldNo, newNo, text}
    function computeLineDiff(oldText, newText) {
        var a = oldText === "" ? [] : String(oldText).split("\n");
        var b = newText === "" ? [] : String(newText).split("\n");
        var start = 0;
        while (start < a.length && start < b.length && a[start] === b[start]) start++;
        var endA = a.length, endB = b.length;
        while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
            endA--; endB--;
        }
        var rows = [];
        for (var p = 0; p < start; p++) {
            rows.push({ type: "ctx", oldNo: p + 1, newNo: p + 1, text: a[p] });
        }
        var ops = myersOps(a.slice(start, endA), b.slice(start, endB));
        for (var i = 0; i < ops.length; i++) {
            var op = ops[i];
            if (op[0] === "=") {
                rows.push({ type: "ctx", oldNo: start + op[1] + 1,
                            newNo: start + op[2] + 1, text: a[start + op[1]] });
            } else if (op[0] === "-") {
                rows.push({ type: "del", oldNo: start + op[1] + 1,
                            newNo: null, text: a[start + op[1]] });
            } else {
                rows.push({ type: "add", oldNo: null,
                            newNo: start + op[2] + 1, text: b[start + op[2]] });
            }
        }
        var tail = a.length - endA;
        for (var t = 0; t < tail; t++) {
            rows.push({ type: "ctx", oldNo: endA + t + 1,
                        newNo: endB + t + 1, text: a[endA + t] });
        }
        return rows;
    }

    // ملف واحد من ProposedAction → نموذج عرض جاهز.
    // command/أنواع بلا ملف: بلوك payload بلا diff (rows=null).
    function buildFile(action, oldText) {
        var kind = action.kind || "";
        var target = action.target || "";
        var isFileKind = kind === "write" || kind === "delete";
        var file = {
            kind: kind, target: target, summary: action.summary || "",
            rows: null, addCount: 0, delCount: 0, lang: null,
            payload: action.payload || "",
        };
        if (!isFileKind) return file;
        var newText = kind === "delete" ? "" : (action.payload || "");
        file.rows = computeLineDiff(oldText || "", newText);
        file.lang = CodeHighlightRef.langForPath(target);
        for (var i = 0; i < file.rows.length; i++) {
            if (file.rows[i].type === "add") file.addCount++;
            else if (file.rows[i].type === "del") file.delCount++;
        }
        return file;
    }

    // حالة اللوحة من إطار الطلب + خريطة المحتوى القديم {target: oldText}.
    function openState(frame, oldContents) {
        var files = (frame.actions || []).map(function (a) {
            return buildFile(a, (oldContents || {})[a.target] || "");
        });
        return {
            request_id: frame.request_id || "",
            payload_hash: frame.payload_hash || "",
            run_id: frame.run_id || "",
            source: frame.source || "",
            files: files,
            accepted: files.map(function () { return true; }),
            collapsed: files.map(function () { return false; }),
            mode: "unified",     // "unified" | "split"
            activeFile: 0,
        };
    }

    function setFileDecision(state, idx, accepted) {
        if (idx >= 0 && idx < state.accepted.length) state.accepted[idx] = !!accepted;
    }

    // إطار القرار — 1:1 مع gate.resolve(request_id, approved, payload_hash).
    // overrideAll: true/false لأزرار الدفعة؛ null = مِن toggles الملفات
    // (approved فقط لو كانت كلها مقبولة — انظر دلالة القرار أعلى الملف).
    function decisionFrame(state, overrideAll) {
        var approved;
        if (overrideAll === true || overrideAll === false) {
            approved = overrideAll;
        } else {
            approved = state.accepted.every(function (x) { return x; });
        }
        return {
            type: "chain_approval_response",
            request_id: state.request_id,
            approved: approved,
            payload_hash: state.payload_hash,
        };
    }

    function highlightLine(text, lang) {
        if (!text) return "";
        if (!lang) return escapeHtml(text);
        return CodeHighlightRef.highlightCode(text, lang).html;
    }

    // رأس ملف: أيقونة النوع (T-063) + المسار + عدادات ± + toggles.
    function renderFileHeaderHTML(file, idx, state) {
        var icon = "";
        if (file.kind === "write" || file.kind === "delete") {
            var ic = FileIconsRef.getFileIcon(file.target);
            icon = '<svg class="file-icon" style="color: var(' + ic.colorToken +
                ')" aria-hidden="true"><use href="' + FileIconsRef.SPRITE_URL +
                ic.symbol + '"></use></svg>';
        }
        var counts = file.rows
            ? '<span class="diff-count-add">+' + file.addCount + "</span>" +
              '<span class="diff-count-del">−' + file.delCount + "</span>"
            : '<span class="diff-kind-badge">' + escapeHtml(file.kind) + "</span>";
        var acc = state.accepted[idx];
        return '<div class="diff-file-header' +
            (idx === state.activeFile ? " active" : "") + '" data-idx="' + idx + '">' +
            '<button class="diff-collapse-btn" data-idx="' + idx + '">' +
            (state.collapsed[idx] ? "▸" : "▾") + "</button>" +
            icon +
            '<span class="diff-file-path">' + escapeHtml(file.target) + "</span>" +
            counts +
            '<button class="diff-file-decision ' + (acc ? "accepted" : "rejected") +
            '" data-idx="' + idx + '">' + (acc ? "✓ مقبول" : "✗ مرفوض") + "</button>" +
            "</div>";
    }

    // صفوف unified داخل نافذة virtualization [winStart, winStart+winCount).
    function renderUnifiedRowsHTML(file, winStart, winCount) {
        var rows = file.rows || [];
        var end = Math.min(rows.length, winStart + winCount);
        var html = "";
        for (var i = Math.max(0, winStart); i < end; i++) {
            var r = rows[i];
            var sign = r.type === "add" ? "+" : r.type === "del" ? "−" : " ";
            html += '<div class="diff-row ' + r.type + '">' +
                '<span class="diff-gutter">' + (r.oldNo === null ? "" : r.oldNo) + "</span>" +
                '<span class="diff-gutter">' + (r.newNo === null ? "" : r.newNo) + "</span>" +
                '<span class="diff-sign">' + sign + "</span>" +
                '<code class="diff-line-code">' + highlightLine(r.text, file.lang) +
                "</code></div>";
        }
        return html;
    }

    // أزواج split (يسار قديم/يمين جديد) — تُبنى مرة وتُكاش على الملف.
    function splitPairs(file) {
        if (file._splitPairs) return file._splitPairs;
        var rows = file.rows || [];
        var pairs = [];
        var i = 0;
        while (i < rows.length) {
            if (rows[i].type === "ctx") {
                pairs.push({ left: rows[i], right: rows[i] });
                i++;
                continue;
            }
            var dels = [];
            var adds = [];
            while (i < rows.length && rows[i].type === "del") { dels.push(rows[i]); i++; }
            while (i < rows.length && rows[i].type === "add") { adds.push(rows[i]); i++; }
            var span = Math.max(dels.length, adds.length);
            for (var s = 0; s < span; s++) {
                pairs.push({ left: dels[s] || null, right: adds[s] || null });
            }
        }
        file._splitPairs = pairs;
        return pairs;
    }

    function renderSplitRowsHTML(file, winStart, winCount) {
        var pairs = splitPairs(file);
        var end = Math.min(pairs.length, winStart + winCount);
        var html = "";
        function cell(row, side) {
            if (!row) return '<span class="diff-gutter"></span>' +
                '<code class="diff-line-code diff-empty"></code>';
            var cls = row.type === "ctx" ? "ctx" : (side === "left" ? "del" : "add");
            var no = side === "left" ? row.oldNo : row.newNo;
            return '<span class="diff-gutter">' + (no === null ? "" : no) + "</span>" +
                '<code class="diff-line-code ' + cls + '">' +
                highlightLine(row.text, file.lang) + "</code>";
        }
        for (var i = Math.max(0, winStart); i < end; i++) {
            var p = pairs[i];
            html += '<div class="diff-row split">' +
                '<span class="diff-split-side">' + cell(p.left, "left") + "</span>" +
                '<span class="diff-split-side">' + cell(p.right, "right") + "</span>" +
                "</div>";
        }
        return html;
    }

    // عدد صفوف الملف في الوضع الحالي (لحساب spacers الـ virtualization).
    function rowCount(file, mode) {
        if (!file.rows) return 0;
        return mode === "split" ? splitPairs(file).length : file.rows.length;
    }

    // اختصارات لوحة المفاتيح — خريطة نقية (الربط الفعلي في app.js).
    function handleKey(state, key) {
        switch (key) {
            case "a": return { action: "approve_all" };
            case "r": return { action: "reject_all" };
            case "Enter": return { action: "confirm" };
            case "Escape": return { action: "reject_all" };
            case "u": return { action: "toggle_mode" };
            case "x": return { action: "toggle_file", idx: state.activeFile };
            case "j": return {
                action: "focus_file",
                idx: Math.min(state.files.length - 1, state.activeFile + 1),
            };
            case "k": return {
                action: "focus_file",
                idx: Math.max(0, state.activeFile - 1),
            };
            default: return null;
        }
    }

    var api = {
        computeLineDiff: computeLineDiff,
        buildFile: buildFile,
        openState: openState,
        setFileDecision: setFileDecision,
        decisionFrame: decisionFrame,
        renderFileHeaderHTML: renderFileHeaderHTML,
        renderUnifiedRowsHTML: renderUnifiedRowsHTML,
        renderSplitRowsHTML: renderSplitRowsHTML,
        rowCount: rowCount,
        handleKey: handleKey,
        ROW_HEIGHT: 20, // px — مطابق لـ .diff-row في style.css (virtualization)
    };

    global.DiffPanel = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
