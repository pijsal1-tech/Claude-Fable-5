/* ═══════════════════════════════════════════════════════
   🚀 WebDev AI Editor — Frontend Logic
   WebSocket + Chat + File Explorer + Editor + Terminal
   ═══════════════════════════════════════════════════════ */

// ═══════════════════════════════════════════
// State
// ═══════════════════════════════════════════
const state = {
    ws: null,
    connected: false,
    mode: "chat",
    streaming: false,
    openTabs: [],       // [{path, content, language, dirty}]
    activeTab: null,    // path string
    pendingActions: [], // from last AI response
    currentSessionId: null,
    planActions: [],    // actions from pending plan
    planCardState: null, // TSK-619: PlanCard.createState — أعلام تفعيل الخطوات
    attachments: [],    // [{name, content}]
    editorOriginal: "", // original content for dirty tracking
    // Multi-terminal
    terminals: [],      // [{id, name, shell, output}]
    activeTerminal: null,
    terminalIdCounter: 0,
    // ── إدارة البث والإيقاف ──
    currentRequestId: null,       // UUID الطلب الحالي لمطابقة ردود الـ WS
    activeGenerationKind: null,   // "chat" | "chain" — نوع التوليد النشط
    stopRequested: false,         // منع تكرار إرسال طلب الإيقاف
    _stopFallbackTimer: null,     // مؤقت أمان 6 ثوانٍ لإعادة واجهة العميل
};


// ═══════════════════════════════════════════
// Init
// ═══════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    initWebSocket();
    loadProjectInfo();
    loadChatHistory();
    loadFiles();
    loadModels();
    initModes();
    initTerminal();
    initChatInput();
    initResizeHandle();
    initDragDrop();
    initEditorShortcuts();
    initThemePicker();
});

// ═══════════════════════════════════════════
// Theme Switcher — T-061 (R-905)
// السجل = مصدر الحقيقة الوحيد للثيمات المتاحة — إضافة ثيم =
// ملف CSS جديد تحت static/themes/ + إدخال هنا — صفر تعديل مكوّنات.
// المفتاح في localStorage ("webdev-ai-theme") يقرأه أيضًا سكربت
// الـ bootstrap في <head> قبل أول paint (T-060 — لا FOUC).
// ═══════════════════════════════════════════
const THEME_STORAGE_KEY = "webdev-ai-theme";
const THEMES = [
    { id: "dark", label: "🌙 Dark", desc: "الافتراضي — True Black" },
    { id: "light", label: "☀️ Light", desc: "فاتح — Latte" },
    { id: "high-contrast", label: "♿ High Contrast", desc: "تباين عالٍ — AAA" },
    { id: "monokai", label: "🎹 Monokai", desc: "لوحة محرر كلاسيكية" },
];

function getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
}

function setTheme(themeId) {
    if (!THEMES.some(t => t.id === themeId)) themeId = "dark";
    // تبديل حي: سمة واحدة تعيد تلوين كل شيء (التوكنز) — بلا reload.
    document.documentElement.setAttribute("data-theme", themeId);
    try { localStorage.setItem(THEME_STORAGE_KEY, themeId); } catch (e) { /* private mode */ }
    updateThemeLabel();
    renderThemeList();
}

function updateThemeLabel() {
    const label = document.getElementById("current-theme-label");
    if (!label) return;
    const cur = THEMES.find(t => t.id === getCurrentTheme());
    label.textContent = cur ? cur.label : "Theme";
}

function renderThemeList() {
    const list = document.getElementById("theme-list");
    if (!list) return;
    const current = getCurrentTheme();
    list.innerHTML = "";
    THEMES.forEach(t => {
        const item = document.createElement("div");
        item.className = "theme-item" + (t.id === current ? " active" : "");
        item.setAttribute("data-theme-id", t.id);
        item.onclick = () => {
            setTheme(t.id);
            document.getElementById("theme-dropdown").classList.add("hidden");
            document.removeEventListener("click", closeThemeOnOutside);
        };
        const name = document.createElement("div");
        name.className = "theme-item-name";
        name.textContent = t.label + (t.id === current ? " ✓" : "");
        const desc = document.createElement("div");
        desc.className = "theme-item-desc";
        desc.textContent = t.desc;
        item.appendChild(name);
        item.appendChild(desc);
        list.appendChild(item);
    });
}

function toggleThemePicker() {
    const dropdown = document.getElementById("theme-dropdown");
    if (dropdown.classList.contains("hidden")) {
        renderThemeList();
        dropdown.classList.remove("hidden");
        setTimeout(() => {
            document.addEventListener("click", closeThemeOnOutside);
        }, 100);
    } else {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeThemeOnOutside);
    }
}

function closeThemeOnOutside(e) {
    const dropdown = document.getElementById("theme-dropdown");
    const btn = document.getElementById("theme-btn");
    if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeThemeOnOutside);
    }
}

function initThemePicker() {
    // data-theme مضبوطة مسبقًا من bootstrap الـ <head> — نزامن الـ UI فقط.
    updateThemeLabel();
}

// ═══════════════════════════════════════════
// File Tree Toggle
// ═══════════════════════════════════════════

function toggleFileTree() {
    const sidebar = document.getElementById('sidebar');
    const title = document.getElementById('explorer-title');
    const arrow = title ? title.querySelector('.tree-arrow') : null;
    const fileTree = document.getElementById('file-tree');
    if (!sidebar || !fileTree) return;
    const isCollapsed = sidebar.classList.toggle('collapsed-full');
    if (arrow) arrow.style.transform = isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
    if (title) title.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
}

function focusPathInTree(filePath) {
    const treeItems = document.querySelectorAll('[data-path]');
    let targetNode = null;
    for (const item of treeItems) {
        if (item.dataset.path === filePath) {
            targetNode = item;
            break;
        }
    }
    if (!targetNode) return;
    // فتح المجلدات الأبوية
    let parent = targetNode.parentElement;
    while (parent) {
        if (parent.classList.contains('tree-folder-children')) {
            parent.style.display = 'block';
        }
        parent = parent.parentElement;
    }
    targetNode.classList.add('tree-item-highlight');
    requestAnimationFrame(() => {
        if (document.body.contains(targetNode)) {
            targetNode.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
    setTimeout(() => targetNode.classList.remove('tree-item-highlight'), 2000);
}

function showErrorInChat(text) {
    const container = document.getElementById("chat-messages");

    if (currentStreamMsg) {
        const content = currentStreamMsg.querySelector(".streaming-content");
        if (content) {
            content.innerHTML += `<br><span style="color:var(--error)">❌ ${escapeHtml(text)}</span>`;
        }
        const label = currentStreamMsg.querySelector(".msg-label");
        if (label) label.innerHTML = "🤖 AI";
        currentStreamMsg = null;
        currentStreamText = "";
    } else {
        const msg = document.createElement("div");
        msg.className = "chat-msg assistant";
        msg.innerHTML = `
            <div class="msg-label">🤖 AI</div>
            <div class="msg-content" style="color:var(--error)">❌ ${escapeHtml(text)}</div>
        `;
        container.appendChild(msg);
    }

    document.getElementById("send-btn").disabled = false;
    container.scrollTop = container.scrollHeight;
}

function clearChat() {
    document.getElementById("chat-messages").innerHTML = "";
    fetch("/api/clear", { method: "POST" });
    toast("تم مسح المحادثة", "info");
}


// ═══════════════════════════════════════════
// Mode Switcher
// ═══════════════════════════════════════════
function initModes() {
    document.querySelectorAll(".mode-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.mode = btn.dataset.mode;
        });
    });
}

// ═══════════════════════════════════════════
// Chat Input
// ═══════════════════════════════════════════
function initChatInput() {
    const input = document.getElementById("chat-input");

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    input.addEventListener("input", () => autoResizeInput(input));
}

function autoResizeInput(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ═══════════════════════════════════════════
// Project Info
// ═══════════════════════════════════════════
// ── مساعد: تحديث breadcrumb المشروع في الـ titlebar الجديد ──
function setProjectCrumb(name, filesCount) {
    const el = document.getElementById('project-name');
    if (!el) return;
    // الـ span الداخلي في .project-crumb
    const span = el.querySelector('span') || el;
    span.textContent = filesCount !== undefined
        ? `${name}  (${filesCount} files)`
        : name;
    el.title = `اضغط لتغيير المجلد\n${name}`;
}

function loadProjectInfo() {
    fetch("/api/info")
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                setProjectCrumb(data.project.name, data.project.total_files);
                // T-066: جذر المشروع — لاختصار المسارات المطلقة في لوحة التاريخ
                state.projectRoot = data.project.root || "";
                if (data.provider.name || data.provider.model) {
                    const provBadge = document.getElementById("provider-name");
                    if (provBadge && !provBadge.dataset.userSwitched) {
                        provBadge.textContent = data.provider.name || data.provider.model;
                    }
                }
            }
        })
        .catch(() => { });
}

function loadChatHistory() {
    fetch("/api/chat-history")
        .then(r => r.json())
        .then(data => {
            if (data.ok && data.history) {
                renderChatHistory(data.history);
            }
        })
        .catch(() => { });
}

// ═══════════════════════════════════════════
// Resize Handle
// ═══════════════════════════════════════════
function initResizeHandle() {
    const handle = document.getElementById("terminal-resize");
    const terminal = document.getElementById("terminal-panel");
    const editor = document.getElementById("editor-area");
    let startY, startH;

    handle.addEventListener("mousedown", (e) => {
        startY = e.clientY;
        startH = terminal.offsetHeight;
        handle.classList.add("active");

        const onMove = (e) => {
            const delta = startY - e.clientY;
            const newH = Math.max(80, Math.min(500, startH + delta));
            terminal.style.height = newH + "px";
        };

        const onUp = () => {
            handle.classList.remove("active");
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
        };

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });
}

function parseResponseChannels(text) {
    let thinking = "";
    let result = "";
    let other = "";

    const hasThinking = text.includes("<thinking>");
    const hasResult = text.includes("<result>");

    if (!hasThinking && !hasResult) {
        other = text;
        return { thinking, result, other, hasChannels: false };
    }

    if (hasThinking) {
        const startIdx = text.indexOf("<thinking>") + 10;
        const endIdx = text.indexOf("</thinking>");
        if (endIdx !== -1) {
            thinking = text.substring(startIdx, endIdx);
        } else {
            thinking = text.substring(startIdx);
        }
    }

    if (hasResult) {
        const startIdx = text.indexOf("<result>") + 8;
        const endIdx = text.indexOf("</result>");
        if (endIdx !== -1) {
            result = text.substring(startIdx, endIdx);
        } else {
            result = text.substring(startIdx);
        }
    }

    const firstTagIdx = Math.min(
        hasThinking ? text.indexOf("<thinking>") : Infinity,
        hasResult ? text.indexOf("<result>") : Infinity
    );
    if (firstTagIdx > 0 && firstTagIdx !== Infinity) {
        other = text.substring(0, firstTagIdx);
    }

    return { thinking, result, other, hasChannels: true };
}

function getToolFriendlyName(tool) {
    const names = {
        "read_file": "قراءة ملف",
        "write_file": "كتابة ملف",
        "edit_file": "تعديل ملف",
        "list_dir": "استعراض مجلد",
        "search_code": "بحث في الكود",
        "get_file_info": "خصائص ملف",
        "get_project_tree": "شجرة المشروع",
        "run_command": "تشغيل أمر",
        "auto_file": "قراءة ملف تلقائي",
        "auto_dir": "استعراض مجلد تلقائي",
        "auto_overview": "نظرة عامة تلقائية",
        "auto_overview_dir": "نظرة عامة مجلد تلقائي",
        "auto_search": "بحث تلقائي",
        "auto_prefetch": "الجمع التلقائي للمعلومات",
        "auto_tree": "فحص شجرة المشروع",
        "auto_deps": "قراءة الاعتماديات",
        "auto_config": "قراءة ملفات الإعدادات"
    };
    return names[tool] || tool;
}

function getFileBadgeHTML(path, tool) {
    if (tool === "auto_search" || tool === "search_code") {
        return `<span class="file-badge search">SRC</span>`;
    }
    if (tool === "auto_tree" || tool === "get_project_tree") {
        return `<span class="file-badge tree">TREE</span>`;
    }
    if (tool === "list_dir" || tool === "auto_dir" || tool === "auto_overview_dir") {
        return `<span class="file-badge dir">DIR</span>`;
    }

    const ext = path.split('.').pop().toLowerCase();
    let badgeText = ext.toUpperCase();
    let badgeClass = ext;

    if (ext === "js" || ext === "jsx") badgeClass = "js";
    else if (ext === "ts" || ext === "tsx") badgeClass = "ts";
    else if (ext === "py") badgeClass = "py";
    else if (ext === "css" || ext === "scss" || ext === "sass") badgeClass = "css";
    else if (ext === "html") badgeClass = "html";
    else if (ext === "json") badgeClass = "json";
    else if (ext === "md") badgeClass = "md";
    else {
        badgeClass = "generic";
        if (badgeText.length > 4) badgeText = "FILE";
    }

    return `<span class="file-badge ${badgeClass}">${badgeText}</span>`;
}

function renderExploringAccordion(items) {
    const runningCount = items.filter(i => i.status === "running").length;
    const totalCount = items.length;

    let title = "";
    if (runningCount > 0) {
        title = `🔍 Exploring ${totalCount} file${totalCount > 1 ? 's' : ''}`;
    } else {
        title = `✅ Explored ${totalCount} file${totalCount > 1 ? 's' : ''}`;
    }

    let html = `
        <details class="exploring-accordion" ${runningCount > 0 ? "open" : ""}>
            <summary>
                <span class="exploring-title">${title}</span>
            </summary>
            <div class="exploring-list">
    `;

    items.forEach(item => {
        const badge = getFileBadgeHTML(item.path, item.tool);
        const statusText = item.status === "running" ? "Analyzing..." : "Analyzed";
        const linesText = item.lines ? ` #L${item.lines}` : "";

        html += `
            <div class="exploring-item ${item.status}">
                ${badge}
                <span class="file-name">${escapeHtml(item.path)}${linesText}</span>
                <span class="file-status">${statusText}</span>
            </div>
        `;
    });

    html += `
            </div>
        </details>
    `;

    return html;
}

// ═══════════════════════════════════════════
// Markdown Rendering
// ═══════════════════════════════════════════
function renderMarkdown(text) {
    if (!text) return "";
    try {
        // Configure marked — T-064: خيار highlight أُزيل (محذوف من marked v5+
        // أصلًا فكان صامتًا)؛ الإبراز الآن عبر CodeHighlight.highlightContainer
        // بعد كل innerHTML (مُكاش — لا وميض أثناء البث).
        marked.setOptions({
            breaks: true,
            gfm: true,
        });
        // TSK-703 (FI-10): تعقيم ناتج marked قبل أي innerHTML — يغلق سطح
        // XSS المتمم لـ TSK-404 (نص النموذج قد يحوي <script>/<img onerror>).
        // غياب DOMPurify (فشل تحميل vendor) ⇒ fallback العرض النصي المهرَّب
        // نفسه المستخدم في catch — لا HTML خام يصل الواجهة أبدًا.
        const rawHtml = marked.parse(text);
        if (typeof DOMPurify !== "undefined" && DOMPurify.sanitize) {
            return DOMPurify.sanitize(rawHtml);
        }
        return escapeHtml(text).replace(/\n/g, "<br>");
    } catch (e) {
        return escapeHtml(text).replace(/\n/g, "<br>");
    }
}

// ═══════════════════════════════════════════
// RTL / LTR Detection
// ═══════════════════════════════════════════
function detectDirection(text) {
    if (!text) return "ltr";
    // Strip markdown/code blocks to detect natural language
    const cleaned = text.replace(/```[\s\S]*?```/g, "").replace(/`[^`]+`/g, "").trim();
    // Find first meaningful character (skip spaces, numbers, punctuation, emoji)
    const match = cleaned.match(/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0590-\u05FF]/)
        || cleaned.match(/[a-zA-Z]/);
    if (match) {
        const char = match[0];
        // Arabic/Hebrew range
        if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0590-\u05FF]/.test(char)) {
            return "rtl";
        }
    }
    return "ltr";
}

function applyParagraphDirections(container) {
    // Apply individual direction to each paragraph for mixed content
    container.querySelectorAll("p, li, h1, h2, h3, h4, h5, h6").forEach(el => {
        const dir = detectDirection(el.textContent);
        el.setAttribute("dir", dir);
    });
    // Code blocks always LTR
    container.querySelectorAll("pre, code").forEach(el => {
        el.setAttribute("dir", "ltr");
    });
}

// ═══════════════════════════════════════════
// Copy Full Response
// ═══════════════════════════════════════════
function copyFullResponse(btn, text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            const original = btn.innerHTML;
            btn.innerHTML = "✅ تم النسخ!";
            btn.classList.add("copied");
            toast("تم نسخ الرد بالكامل", "success");
            setTimeout(() => {
                btn.innerHTML = original;
                btn.classList.remove("copied");
            }, 2000);
        })
        .catch(err => {
            toast("فشل النسخ: " + err, "error");
        });
}

// ═══════════════════════════════════════════
// Quick Replies
// ═══════════════════════════════════════════
function showQuickReplies(options) {
    const container = document.getElementById("chat-messages");
    const wrapper = document.createElement("div");
    wrapper.className = "quick-replies";

    options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "quick-reply-btn";
        btn.textContent = opt;
        btn.onclick = () => {
            // Remove quick replies
            wrapper.remove();
            // Send as user message
            const input = document.getElementById("chat-input");
            input.value = opt;
            sendMessage();
        };
        wrapper.appendChild(btn);
    });

    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

// ═══════════════════════════════════════════
// Utilities
// ═══════════════════════════════════════════
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function toast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${escapeHtml(message)}</span>`;
    container.appendChild(t);

    setTimeout(() => {
        t.style.opacity = "0";
        t.style.transform = "translateX(20px)";
        setTimeout(() => t.remove(), 300);
    }, 3000);
}

// ═══════════════════════════════════════════
// Open Folder / New File / New Folder
// ═══════════════════════════════════════════
function openFolder() {
    const path = prompt("أدخل مسار المجلد:\n\nمثال:\n  D:\\projects\\my_site\n  ./new_project\n  C:\\Users\\Belal\\Desktop\\website");
    if (!path) return;

    fetch("/api/switch-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                setProjectCrumb(data.project.name, data.project.total_files);
                // مسح tabs + editor
                state.openTabs = [];
                state.activeTab = null;
                document.getElementById("tabs").innerHTML = "";
                document.getElementById("editor-welcome").style.display = "flex";
                document.getElementById("editor-content").style.display = "none";
                document.getElementById("run-btn").classList.add("hidden");
                // تحديث الملفات
                refreshFiles();
                // إعادة تقييم ثقة المجلد الجديد — TSK-725c
                refreshTrustUI();
                toast(`تم فتح: ${data.project.name}`, "success");
            } else {
                toast(data.error, "error");
            }
        })
        .catch(e => toast("فشل تغيير المجلد", "error"));
}

function createNewFile() {
    const name = prompt("اسم الملف الجديد:\n\nمثال: index.html, script.py, src/app.js");
    if (!name) return;

    fetch("/api/new-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: name, content: "" }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast(`تم إنشاء: ${name}`, "success");
                refreshFiles();
                openFile(name);
            } else {
                toast(data.error, "error");
            }
        })
        .catch(e => toast("فشل إنشاء الملف", "error"));
}

function createNewFolder() {
    const name = prompt("اسم المجلد الجديد:\n\nمثال: src, components, assets/images");
    if (!name) return;

    fetch("/api/new-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: name }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast(`تم إنشاء مجلد: ${name}`, "success");
                refreshFiles();
            } else {
                toast(data.error, "error");
            }
        })
        .catch(e => toast("فشل إنشاء المجلد", "error"));
}

// ═══════════════════════════════════════════
// Run Current File
// ═══════════════════════════════════════════
function runCurrentFile() {
    if (!state.activeTab) {
        toast("لا يوجد ملف مفتوح", "error");
        return;
    }

    const path = state.activeTab;
    const output = document.getElementById("terminal-output");

    output.innerHTML += `<div class="cmd">$ ▶ Running: ${escapeHtml(path)}</div>`;
    output.scrollTop = output.scrollHeight;

    fetch("/api/run-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.command) {
                output.innerHTML += `<div class="cmd">$ ${escapeHtml(data.command)}</div>`;
            }
            if (data.output) {
                output.innerHTML += `<div class="out">${escapeHtml(data.output)}</div>`;
            }
            if (data.error) {
                output.innerHTML += `<div class="err">${escapeHtml(data.error)}</div>`;
            }
            if (data.ok) {
                output.innerHTML += `<div class="success">✅ exit code: ${data.code}</div>`;
            } else {
                output.innerHTML += `<div class="err">❌ exit code: ${data.code || 'N/A'}</div>`;
            }
            output.scrollTop = output.scrollHeight;
        })
        .catch(e => {
            output.innerHTML += `<div class="err">❌ ${e.message}</div>`;
        });
}
