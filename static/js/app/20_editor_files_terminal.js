/* TSK-726b (P2-4 / FI-07 / D-10): مقطع منقول حرفيًا من app.js —
 * مجال المحرر/الملفات/التبويبات + التيرمنال (loadFiles → openFile →
 * saveFile → diff panel → initTerminal → runCommand → diagnose).
 * تقسيم-تسلسلي محافظ: نطاق عمومي مشترك؛ يُحمَّل بعد app.js —
 * الاستدعاءات التمهيدية كلها داخل DOMContentLoaded فتقع بعد تحميل
 * كل السكربتات المتزامنة. لا تغيير سلوكي.
 */
// ═══════════════════════════════════════════
// File Explorer
// ═══════════════════════════════════════════
function loadFiles() {
    fetch("/api/files")
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                renderFileTree(data.scan);
            }
        })
        .catch(() => { });
}

function refreshFiles() {
    loadFiles();
}

function renderFileTree(scan) {
    const container = document.getElementById("file-tree");
    container.innerHTML = "";

    // Group files by directory
    const tree = {};
    scan.files.forEach(f => {
        const parts = f.path.split("/");
        let node = tree;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!node[parts[i]]) node[parts[i]] = {};
            node = node[parts[i]];
        }
        node[parts[parts.length - 1]] = f;
    });

    renderTreeNode(container, tree, 0);
}

function renderTreeNode(container, node, depth) {
    const entries = Object.keys(node).sort((a, b) => {
        const aIsDir = typeof node[a] === "object" && !node[a].path;
        const bIsDir = typeof node[b] === "object" && !node[b].path;
        if (aIsDir && !bIsDir) return -1;
        if (!aIsDir && bIsDir) return 1;
        return a.localeCompare(b);
    });

    entries.forEach(key => {
        const val = node[key];
        const isFile = val && val.path;

        const item = document.createElement("div");
        item.className = `tree-item ${isFile ? "file" : "dir"}`;

        let indent = "";
        for (let i = 0; i < depth; i++) indent += '<span class="tree-indent"></span>';

        if (isFile) {
            item.innerHTML = `${indent}${fileIconHTML(val.path)}<span class="name">${key}</span>`;
            item.onclick = () => openFile(val.path);
            // Make file draggable to chat
            item.draggable = true;
            item.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", val.path);
                e.dataTransfer.effectAllowed = "copy";
            });
        } else {
            item.innerHTML = `${indent}<svg class="file-icon" style="color:var(--yellow)" aria-hidden="true"><use href="/static/icons/sprite.svg#icon-folder"></use></svg><span class="name">${key}</span>`;
            item.onclick = (e) => {
                e.stopPropagation();
                const children = item.nextElementSibling;
                if (children && children.classList.contains("tree-children")) {
                    children.classList.toggle("hidden");
                    const isOpen = !children.classList.contains("hidden");
                    item.querySelector("use").setAttribute("href",
                        `/static/icons/sprite.svg#icon-folder${isOpen ? "-open" : ""}`);
                }
            };
            // Make folder draggable to chat
            item.draggable = true;
            item.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", "folder:" + key);
                e.dataTransfer.effectAllowed = "copy";
            });
        }

        container.appendChild(item);

        if (!isFile) {
            const childContainer = document.createElement("div");
            childContainer.className = "tree-children";
            renderTreeNode(childContainer, val, depth + 1);
            container.appendChild(childContainer);
        }
    });
}

// T-063 (R-903): مصدر وحيد لأيقونة نوع الملف — يستهلك FileIcons.getFileIcon
// (وحدة file_icons.js) في الشجرة/التبويبات/المرفقات. ممنوع أي mapping ثانٍ
// (grep-gated في tests/unit/test_icon_consumption.py).
function fileIconHTML(path) {
    const icon = FileIcons.getFileIcon(path);
    return `<svg class="file-icon" style="color: var(${icon.colorToken})" aria-hidden="true">` +
        `<use href="/static/icons/sprite.svg${icon.symbol}"></use></svg>`;
}

// ═══════════════════════════════════════════
// Editor
// ═══════════════════════════════════════════
function openFile(path) {
    fetch(`/api/file/${path}`)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                toast(data.error, "error");
                return;
            }

            // إضافة Tab
            if (!state.openTabs.find(t => t.path === path)) {
                state.openTabs.push({ path: path, content: data.content });
            } else {
                // تحديث المحتوى
                const tab = state.openTabs.find(t => t.path === path);
                tab.content = data.content;
            }

            state.activeTab = path;
            renderTabs();
            showEditor(path, data.content);
        })
        .catch(e => toast("فشل فتح الملف", "error"));
}

function renderTabs() {
    const tabBar = document.getElementById("tabs");
    tabBar.innerHTML = state.openTabs.map(t => {
        const name = t.path.split("/").pop();
        const active = t.path === state.activeTab ? "active" : "";
        const dirty = t.dirty ? "dirty" : "";
        return `
            <div class="tab ${active} ${dirty}" onclick="switchTab('${t.path}')">
                ${fileIconHTML(t.path)}
                <span>${name}</span>
                <button class="close-btn" onclick="event.stopPropagation(); closeTab('${t.path}')">×</button>
            </div>
        `;
    }).join("");
}

function switchTab(path) {
    const tab = state.openTabs.find(t => t.path === path);
    if (tab) {
        state.activeTab = path;
        renderTabs();
        showEditor(path, tab.content);
    }
}

function closeTab(path) {
    state.openTabs = state.openTabs.filter(t => t.path !== path);
    if (state.activeTab === path) {
        state.activeTab = state.openTabs.length > 0 ? state.openTabs[state.openTabs.length - 1].path : null;
    }
    renderTabs();

    if (state.activeTab) {
        const tab = state.openTabs.find(t => t.path === state.activeTab);
        if (tab) showEditor(tab.path, tab.content);
    } else {
        document.getElementById("editor-welcome").style.display = "flex";
        document.getElementById("editor-content").style.display = "none";
    }
}

function showEditor(path, content) {
    document.getElementById("editor-welcome").style.display = "none";
    document.getElementById("editor-content").style.display = "flex";

    const textarea = document.getElementById("editor-textarea");
    const filenameEl = document.getElementById("editor-filename");
    const dirtyEl = document.getElementById("editor-dirty");

    // حفظ المحتوى الأصلي للمقارنة
    state.editorOriginal = content;
    textarea.value = content;
    
    // Breadcrumb formatting (VSCode style)
    const pathParts = path.split(/[\/\\]/);
    const breadcrumbHtml = pathParts.map((part, idx) => {
        const isLast = idx === pathParts.length - 1;
        const icon = isLast ? fileIconHTML(path) : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
        return `<span class="crumb-item">${icon} <span>${part}</span></span>`;
    }).join('<span class="crumb-sep">›</span>');
    filenameEl.innerHTML = breadcrumbHtml;
    dirtyEl.classList.add("hidden");

    // تحديث أرقام الأسطر + طبقة الإبراز (T-064)
    textarea.scrollTop = 0;
    updateLineNumbers();
    renderEditorHighlight();

    // ربط أحداث التعديل
    textarea.oninput = () => {
        const isDirty = textarea.value !== state.editorOriginal;
        dirtyEl.classList.toggle("hidden", !isDirty);
        // تحديث dirty في التاب
        const tab = state.openTabs.find(t => t.path === state.activeTab);
        if (tab) tab.dirty = isDirty;
        renderTabs();
        updateLineNumbers();
        renderEditorHighlight();
    };

    // مزامنة scroll أرقام الأسطر + طبقة الإبراز
    textarea.onscroll = () => {
        document.getElementById("line-numbers").scrollTop = textarea.scrollTop;
        const pre = document.getElementById("editor-highlight");
        pre.scrollTop = textarea.scrollTop;
        pre.scrollLeft = textarea.scrollLeft;
        // المسار الكسول للملفات الكبيرة: إعادة إبراز شريحة الـ viewport
        // فقط عند التمرير (rAF-throttled — لا تكديس أعمال).
        if (state.editorHighlightMode === "lazy" && !state.editorLazyRaf) {
            state.editorLazyRaf = requestAnimationFrame(() => {
                state.editorLazyRaf = null;
                renderEditorHighlight();
            });
        }
    };

    // Tab key inserts real tab
    textarea.onkeydown = (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + "    " + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 4;
            textarea.dispatchEvent(new Event('input'));
        }
    };

    // إظهار/إخفاء زر Run حسب نوع الملف
    const ext = "." + path.split(".").pop();
    const runBtn = document.getElementById("run-btn");
    const runnableExts = [".py", ".js", ".ts", ".sh", ".bat", ".ps1"];
    if (runnableExts.includes(ext)) {
        runBtn.classList.remove("hidden");
    } else {
        runBtn.classList.add("hidden");
    }

    // Active في file tree
    document.querySelectorAll(".tree-item.active").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tree-item.file").forEach(el => {
        if (el.querySelector(".name")?.textContent === path.split("/").pop()) {
            el.classList.add("active");
        }
    });
}

function updateLineNumbers() {
    const textarea = document.getElementById("editor-textarea");
    const lineNumEl = document.getElementById("line-numbers");
    const lines = textarea.value.split("\n").length;
    let html = "";
    for (let i = 1; i <= lines; i++) {
        html += i + "\n";
    }
    lineNumEl.textContent = html;
}

// ═══════════════════════════════════════════
// T-065 (R-901): لوحة مراجعة الـ Diff — DOM glue فوق وحدة DiffPanel
// (المنطق النقي في static/js/diff_panel.js — مُختبَر في node).
// القرار ذرّي على مستوى الطلب (بروتوكول ApprovalGate): toggles الملفات
// أداة مراجعة؛ "تأكيد القرار" يرسل approved:true فقط لو كلها مقبولة.
// ═══════════════════════════════════════════
let diffPanelState = null;
const DIFF_WINDOW_ROWS = 80; // صفوف مرسومة لكل ملف (virtualization)

async function openDiffPanel(frame) {
    // المحتوى القديم لكل ملف write/delete — لحساب diff حقيقي.
    const oldContents = {};
    const fileActions = (frame.actions || []).filter(
        a => a.kind === "write" || a.kind === "delete");
    await Promise.all(fileActions.map(async a => {
        try {
            const r = await fetch(`/api/file/${a.target}`);
            const d = await r.json();
            oldContents[a.target] = d.ok ? d.content : "";
        } catch (e) {
            oldContents[a.target] = "";
        }
    }));
    diffPanelState = DiffPanel.openState(frame, oldContents);
    document.getElementById("diff-panel-overlay").classList.remove("hidden");
    renderDiffPanel();
}

function closeDiffPanel() {
    diffPanelState = null;
    document.getElementById("diff-panel-overlay").classList.add("hidden");
}

function sendDiffDecision(overrideAll) {
    if (!diffPanelState) return;
    // T-066 (R-902): اللوحة قد تكون مفتوحة كتأكيد استعادة — يُستهلك
    // القرار محليًا (إطار rollback من وحدة RunHistory) بدل رد الموافقة.
    if (consumeRollbackDecision(overrideAll)) return;
    state.ws.send(JSON.stringify(DiffPanel.decisionFrame(diffPanelState, overrideAll)));
    // الإغلاق الفعلي عند وصول chain_approval_verdict (مصدر الحقيقة البوابة).
}

function renderDiffPanel() {
    if (!diffPanelState) return;
    const st = diffPanelState;
    document.getElementById("diff-mode-toggle").textContent =
        st.mode === "unified" ? "↔ Split" : "≡ Unified";
    const filesEl = document.getElementById("diff-panel-files");
    let html = "";
    st.files.forEach((file, idx) => {
        html += DiffPanel.renderFileHeaderHTML(file, idx, st);
        if (st.collapsed[idx]) return;
        if (!file.rows) {
            html += `<pre class="diff-command-payload"><code>${escapeHtml(file.payload || file.summary)}</code></pre>`;
            return;
        }
        const total = DiffPanel.rowCount(file, st.mode);
        const winStart = file._winStart || 0;
        const render = st.mode === "split"
            ? DiffPanel.renderSplitRowsHTML : DiffPanel.renderUnifiedRowsHTML;
        // virtualization: spacers تحفظ ارتفاع التمرير، والنافذة فقط تُرسم.
        html += `<div class="diff-file-body" data-idx="${idx}" data-total="${total}">` +
            `<div style="height:${winStart * DiffPanel.ROW_HEIGHT}px"></div>` +
            render(file, winStart, DIFF_WINDOW_ROWS) +
            `<div style="height:${Math.max(0, total - winStart - DIFF_WINDOW_ROWS) * DiffPanel.ROW_HEIGHT}px"></div>` +
            `</div>`;
    });
    filesEl.innerHTML = html;

    // أحداث الرؤوس/الأزرار (delegation بسيط بعد كل رسم)
    filesEl.querySelectorAll(".diff-collapse-btn").forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            const i = +btn.dataset.idx;
            st.collapsed[i] = !st.collapsed[i];
            renderDiffPanel();
        };
    });
    filesEl.querySelectorAll(".diff-file-decision").forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            const i = +btn.dataset.idx;
            DiffPanel.setFileDecision(st, i, !st.accepted[i]);
            renderDiffPanel();
        };
    });
    filesEl.querySelectorAll(".diff-file-header").forEach(h => {
        h.onclick = () => { st.activeFile = +h.dataset.idx; renderDiffPanel(); };
    });
    // virtualization scroll — rAF-throttled لكل body
    filesEl.querySelectorAll(".diff-file-body").forEach(body => {
        body.onscroll = () => {
            const file = st.files[+body.dataset.idx];
            const newStart = Math.floor(body.scrollTop / DiffPanel.ROW_HEIGHT);
            if (Math.abs(newStart - (file._winStart || 0)) < DIFF_WINDOW_ROWS / 4) return;
            if (file._raf) return;
            file._raf = requestAnimationFrame(() => {
                file._raf = null;
                const keep = body.scrollTop;
                file._winStart = Math.max(0, newStart - DIFF_WINDOW_ROWS / 4);
                renderDiffPanel();
                const nb = document.querySelector(`.diff-file-body[data-idx="${body.dataset.idx}"]`);
                if (nb) nb.scrollTop = keep;
            });
        };
    });
}

// أزرار اللوحة + اختصارات اللوحة (تعمل فقط واللوحة مفتوحة)
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("diff-approve-all").onclick = () => sendDiffDecision(true);
    document.getElementById("diff-reject-all").onclick = () => sendDiffDecision(false);
    document.getElementById("diff-confirm").onclick = () => sendDiffDecision(null);
    document.getElementById("diff-mode-toggle").onclick = () => {
        if (!diffPanelState) return;
        diffPanelState.mode = diffPanelState.mode === "unified" ? "split" : "unified";
        renderDiffPanel();
    };
});

document.addEventListener("keydown", (e) => {
    if (!diffPanelState) return;
    if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
    const act = DiffPanel.handleKey(diffPanelState, e.key);
    if (!act) return;
    e.preventDefault();
    switch (act.action) {
        case "approve_all": sendDiffDecision(true); break;
        case "reject_all": sendDiffDecision(false); break;
        case "confirm": sendDiffDecision(null); break;
        case "toggle_mode":
            diffPanelState.mode = diffPanelState.mode === "unified" ? "split" : "unified";
            renderDiffPanel(); break;
        case "toggle_file":
            DiffPanel.setFileDecision(diffPanelState, act.idx,
                !diffPanelState.accepted[act.idx]);
            renderDiffPanel(); break;
        case "focus_file":
            diffPanelState.activeFile = act.idx;
            renderDiffPanel(); break;
    }
});

// T-064 (R-904): طبقة إبراز المحرر — <pre> خلف الـ textarea (نصه شفاف)
// تُرسم عبر CodeHighlight.buildEditorHTML: إبراز كامل للملفات الصغيرة،
// وشريحة viewport فقط للكبيرة (>2000 سطر)، ونص خام للمجهول.
const EDITOR_LINE_HEIGHT = 20.8; // 13px × 1.6 — مطابق لـ CSS المحرر
function renderEditorHighlight() {
    const textarea = document.getElementById("editor-textarea");
    const codeEl = document.getElementById("editor-highlight-code");
    const pre = document.getElementById("editor-highlight");
    if (!state.activeTab) {
        codeEl.innerHTML = "";
        state.editorHighlightMode = null;
        return;
    }
    const firstLine = Math.floor(textarea.scrollTop / EDITOR_LINE_HEIGHT);
    const visible = Math.ceil(textarea.clientHeight / EDITOR_LINE_HEIGHT) || 60;
    const res = CodeHighlight.buildEditorHTML(
        textarea.value, state.activeTab, firstLine, visible
    );
    // سطر أخير فارغ يحافظ على تطابق ارتفاع التمرير مع الـ textarea.
    codeEl.innerHTML = res.html + "\n";
    state.editorHighlightMode = res.mode;
    pre.scrollTop = textarea.scrollTop;
    pre.scrollLeft = textarea.scrollLeft;
}

function saveFile() {
    if (!state.activeTab) return;
    const textarea = document.getElementById("editor-textarea");
    const content = textarea.value;

    fetch(`/api/file/${state.activeTab}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast("✅ تم الحفظ: " + state.activeTab.split("/").pop(), "success");
                state.editorOriginal = content;
                document.getElementById("editor-dirty").classList.add("hidden");
                const tab = state.openTabs.find(t => t.path === state.activeTab);
                if (tab) {
                    tab.content = content;
                    tab.dirty = false;
                }
                renderTabs();
            } else {
                toast("❌ فشل الحفظ: " + (data.error || ""), "error");
            }
        })
        .catch(e => toast("❌ خطأ: " + e.message, "error"));
}

function initEditorShortcuts() {
    document.addEventListener("keydown", (e) => {
        // Ctrl+S → Save
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
            e.preventDefault();
            if (state.activeTab) saveFile();
        }
    });
}

// ═══════════════════════════════════════════
// Terminal — Multi-tab System
// ═══════════════════════════════════════════
function initTerminal() {
    // إنشاء تيرمنال CMD افتراضي
    newTerminal("cmd");

    const input = document.getElementById("terminal-input");
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const cmd = input.value.trim();
            if (!cmd) return;
            input.value = "";
            runCommand(cmd);
        }
    });
}

function newTerminal(shell) {
    const id = state.terminalIdCounter++;
    const name = shell === "powershell" ? `PS ${id + 1}` : `CMD ${id + 1}`;
    state.terminals.push({
        id,
        name,
        shell,
        output: "",
        cwd: "",  // يتحدث من السيرفر
    });
    // جلب المسار الحالي
    fetch("/api/cwd").then(r => r.json()).then(data => {
        const t = state.terminals.find(t => t.id === id);
        if (t) {
            t.cwd = data.cwd || "";
            updateTerminalPrompt();
        }
    });
    switchTerminal(id);
    toast(`🖥️ ${name} (جديد)`, "info");
}

function switchTerminal(id) {
    // حفظ output التيرمنال الحالي
    if (state.activeTerminal !== null) {
        const current = state.terminals.find(t => t.id === state.activeTerminal);
        if (current) {
            current.output = document.getElementById("terminal-output").innerHTML;
        }
    }

    state.activeTerminal = id;
    const term = state.terminals.find(t => t.id === id);
    if (!term) return;

    // تحميل output التيرمنال الجديد
    document.getElementById("terminal-output").innerHTML = term.output;

    updateTerminalPrompt();
    renderTerminalTabs();
    document.getElementById("terminal-output").scrollTop = document.getElementById("terminal-output").scrollHeight;
}

function closeTerminal(id) {
    const idx = state.terminals.findIndex(t => t.id === id);
    if (idx === -1) return;
    // لازم يكون فيه تيرمنال واحد على الأقل
    if (state.terminals.length <= 1) {
        toast("⚠️ لازم يكون فيه تيرمنال واحد على الأقل", "error");
        return;
    }
    state.terminals.splice(idx, 1);
    if (state.activeTerminal === id) {
        switchTerminal(state.terminals[Math.max(0, idx - 1)].id);
    } else {
        renderTerminalTabs();
    }
}

function renderTerminalTabs() {
    const container = document.getElementById("terminal-tabs");
    container.innerHTML = state.terminals.map(t => {
        const active = t.id === state.activeTerminal ? "active" : "";
        const shellClass = `shell-${t.shell}`;
        const icon = t.shell === "powershell" ? "⚡" : "⌨️";
        return `
            <div class="terminal-tab ${active} ${shellClass}" onclick="switchTerminal(${t.id})">
                <span class="shell-icon">${icon}</span>
                <span>${t.name}</span>
                <span class="close-term" onclick="event.stopPropagation(); closeTerminal(${t.id})">×</span>
            </div>
        `;
    }).join("");
}

function updateTerminalPrompt() {
    const term = state.terminals.find(t => t.id === state.activeTerminal);
    if (!term) return;
    const prompt = document.getElementById("terminal-prompt");
    const shortPath = shortenPath(term.cwd);
    if (term.shell === "powershell") {
        prompt.innerHTML = `<span class="term-path">${escapeHtml(shortPath)}</span> PS>`;
        prompt.style.color = "var(--mauve)";
    } else {
        prompt.innerHTML = `<span class="term-path">${escapeHtml(shortPath)}</span> ❯`;
        prompt.style.color = "var(--blue)";
    }
}

function shortenPath(p) {
    if (!p) return "~";
    // حول backslashes لـ forward slashes
    p = p.replace(/\\/g, "/");
    // لو المسار طويل، اعرض آخر 3 folders
    const parts = p.split("/").filter(Boolean);
    if (parts.length <= 3) return p;
    return "..." + "/" + parts.slice(-3).join("/");
}

function runCommand(cmd) {
    const term = state.terminals.find(t => t.id === state.activeTerminal);
    if (!term) return;

    const output = document.getElementById("terminal-output");
    const shortPath = shortenPath(term.cwd);
    const promptChar = term.shell === "powershell" ? "PS>" : "❯";
    output.innerHTML += `<div class="cmd"><span class="cmd-path">${escapeHtml(shortPath)}</span> ${promptChar} ${escapeHtml(cmd)}</div>`;
    output.scrollTop = output.scrollHeight;

    fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, shell: term.shell }),
    })
        .then(r => r.json())
        .then(data => {
            // تحديث المسار
            if (data.cwd) {
                term.cwd = data.cwd;
                updateTerminalPrompt();
            }
            if (data.output) {
                output.innerHTML += `<div class="out">${escapeHtml(data.output)}</div>`;
            }
            if (data.error) {
                output.innerHTML += `<div class="err">${escapeHtml(data.error)}</div>`;
            }
            if (data.ok) {
                output.innerHTML += `<div class="success">✅ exit code: ${data.code}</div>`;
            }
            output.scrollTop = output.scrollHeight;
            term.output = output.innerHTML;
        })
        .catch(e => {
            output.innerHTML += `<div class="err">❌ ${e.message}</div>`;
            term.output = output.innerHTML;
        });
}

function clearTerminal() {
    document.getElementById("terminal-output").innerHTML = "";
    const term = state.terminals.find(t => t.id === state.activeTerminal);
    if (term) term.output = "";
}

function sendTerminalToChat() {
    const output = document.getElementById("terminal-output");
    const text = output.innerText.trim();
    if (!text) {
        toast("⚠️ التيرمنال فاضي", "error");
        return;
    }
    // إرفاق كملف
    const term = state.terminals.find(t => t.id === state.activeTerminal);
    const name = term ? `terminal_${term.name.replace(/\s/g, '_')}.log` : "terminal.log";
    attachFile(name, text);
    // Focus على الشات
    document.getElementById("chat-input").focus();
    toast("💬 تم إرسال محتوى التيرمنال للشات", "success");
}

function diagnoseTerminal() {
    const output = document.getElementById("terminal-output");
    // جمع الأخطاء
    const errorEls = output.querySelectorAll(".err");
    if (errorEls.length === 0) {
        toast("✅ مفيش أخطاء في التيرمنال", "success");
        return;
    }

    let errorText = "";
    errorEls.forEach(el => {
        errorText += el.textContent.trim() + "\n";
    });

    // أيضاً نجيب آخر أمر
    const cmds = output.querySelectorAll(".cmd");
    const lastCmd = cmds.length > 0 ? cmds[cmds.length - 1].textContent.trim() : "";

    // إنشاء رسالة تشخيص
    const diagMsg = `🔍 شخّص المشكلة دي في التيرمنال واقترح حل:\n\nالأمر: ${lastCmd}\n\nالخطأ:\n\`\`\`\n${errorText.trim()}\n\`\`\``;

    // حقن في الشات وإرسال
    const chatInput = document.getElementById("chat-input");
    chatInput.value = diagMsg;
    sendMessage();
    toast("🔍 جاري تشخيص المشكلة...", "info");
}
