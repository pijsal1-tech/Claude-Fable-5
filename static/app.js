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
    attachments: [],    // [{name, content}]
    editorOriginal: "", // original content for dirty tracking
    // Multi-terminal
    terminals: [],      // [{id, name, shell, output}]
    activeTerminal: null,
    terminalIdCounter: 0,
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
// WebSocket
// ═══════════════════════════════════════════
function initWebSocket() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws`;

    state.ws = new WebSocket(url);

    state.ws.onopen = () => {
        state.connected = true;
        updateConnectionDot(true);
    };

    state.ws.onclose = () => {
        state.connected = false;
        updateConnectionDot(false);
        // إعادة اتصال بعد 3 ثواني
        setTimeout(initWebSocket, 3000);
    };

    state.ws.onerror = () => {
        state.connected = false;
        updateConnectionDot(false);
    };

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWSMessage(data);
    };
}

function updateConnectionDot(connected) {
    const dot = document.querySelector(".provider-badge .dot");
    if (dot) {
        dot.style.background = connected ? "var(--success)" : "var(--error)";
    }
}

function handleWSMessage(data) {
    // T-066 (R-906): شريحة الحالة تلتقط routing/budget من الإطارات
    // الموجودة — استهلاك فقط، ولا تغيّر مسار أي إطار.
    if (StatusChip.noteFrame(statusChipState, data)) scheduleStatusChipRender();
    switch (data.type) {
        case "start":
            state.streaming = true;
            startStreamingMessage();
            break;

        case "chunk":
            appendStreamChunk(data.text);
            break;

        case "done":
            state.streaming = false;
            finalizeStreamMessage(data);
            break;

        case "plan":
            state.streaming = false;
            finalizeStreamMessage(data);
            showPlanCard(data.actions, data.summary);
            break;

        case "error":
            state.streaming = false;
            showErrorInChat(data.text);
            break;

        case "action_result":
            handleActionResult(data);
            break;

        case "task_progress":
            updateTaskProgress(data);
            break;

        case "all_actions_done":
            toast(`✅ تم تنفيذ ${data.total} خطوة بنجاح`, "success");
            setTimeout(() => refreshFiles(), 500);
            break;

        case "project_switched":
            document.getElementById("project-name").textContent =
                `📂 ${data.project.name} (${data.project.total_files} files)`;
            state.openTabs = [];
            state.activeTab = null;
            document.getElementById("tabs").innerHTML = "";
            document.getElementById("editor-welcome").style.display = "flex";
            document.getElementById("editor-content").style.display = "none";
            document.getElementById("run-btn").classList.add("hidden");
            refreshFiles();
            toast(`تم فتح: ${data.project.name}`, "success");
            break;

        case "pong":
            break;

        // ── Chain System Events ──

        case "folder_scanned":
            addChatMessage("assistant", data.text);
            break;

        case "chain_started":
            state.streaming = true;
            document.getElementById("send-btn").disabled = true;

            const chatContainer = document.getElementById("chat-messages");
            currentChainMsg = document.createElement("div");
            currentChainMsg.className = "chat-msg assistant chain-progress-msg";

            currentChainText = data.text || `🔗 بدأ chain (${data.total_steps || "?"} خطوات)...`;

            currentChainMsg.innerHTML = `
                <div class="msg-label">🤖 AI</div>
                <div class="msg-content">
                    <details class="thinking-accordion" open>
                        <summary>💭 التفكير (Thinking Stream — خطوات التنفيذ)</summary>
                        <div class="thinking-content">
                            <p>${escapeHtml(currentChainText)}</p>
                        </div>
                    </details>
                </div>
            `;
            chatContainer.appendChild(currentChainMsg);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            break;

        case "chain_step":
            if (currentChainMsg) {
                const stepText = data.text || `${data.status === "running" ? "⏳" : data.status === "success" ? "✅" : "❌"} ${data.step_id}`;
                const thinkingContent = currentChainMsg.querySelector(".thinking-content");
                if (thinkingContent) {
                    const p = document.createElement("p");
                    p.textContent = stepText;
                    thinkingContent.appendChild(p);
                    const chatContainer = document.getElementById("chat-messages");
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            break;

        case "chain_retry":
            if (currentChainMsg) {
                const thinkingContent = currentChainMsg.querySelector(".thinking-content");
                if (thinkingContent) {
                    const p = document.createElement("p");
                    p.textContent = data.text || `🔄 Retry...`;
                    thinkingContent.appendChild(p);
                    const chatContainer = document.getElementById("chat-messages");
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            break;

        case "chain_warning":
            if (currentChainMsg) {
                const thinkingContent = currentChainMsg.querySelector(".thinking-content");
                if (thinkingContent) {
                    const p = document.createElement("p");
                    p.textContent = data.text || `⚠️ تحذير`;
                    thinkingContent.appendChild(p);
                    const chatContainer = document.getElementById("chat-messages");
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            break;

        case "chain_finished":
            state.streaming = false;
            document.getElementById("send-btn").disabled = false;

            if (currentChainMsg) {
                const thinkingContent = currentChainMsg.querySelector(".thinking-content");
                if (thinkingContent) {
                    const p = document.createElement("p");
                    p.textContent = data.text || `✅ Chain انتهى`;
                    thinkingContent.appendChild(p);

                    const details = currentChainMsg.querySelector("details");
                    if (details) {
                        details.removeAttribute("open");
                    }

                    // Add copy response button to copy the execution log
                    const copyBtn = document.createElement("button");
                    copyBtn.className = "copy-response-btn";
                    copyBtn.innerHTML = "📋 نسخ الرد";
                    const allText = Array.from(thinkingContent.querySelectorAll("p")).map(p => p.textContent).join("\n");
                    copyBtn.onclick = () => copyFullResponse(copyBtn, allText);
                    currentChainMsg.appendChild(copyBtn);
                }
            }
            currentChainMsg = null;

            if (data.result) {
                addChatMessage("assistant", data.result);
            }

            // Refresh files and reload active tab to reflect changes on disk
            setTimeout(() => {
                refreshFiles();
                if (state.activeTab) {
                    openFile(state.activeTab);
                }
            }, 500);
            break;

        case "chain_cancelled":
            state.streaming = false;
            document.getElementById("send-btn").disabled = false;

            if (currentChainMsg) {
                const thinkingContent = currentChainMsg.querySelector(".thinking-content");
                if (thinkingContent) {
                    const p = document.createElement("p");
                    p.textContent = data.text || `🛑 Chain تم إلغاؤه`;
                    thinkingContent.appendChild(p);

                    const details = currentChainMsg.querySelector("details");
                    if (details) {
                        details.removeAttribute("open");
                    }
                }
            }
            currentChainMsg = null;
            break;

        case "chain_cancel_result":
            toast(data.text, data.ok ? "success" : "info");
            break;

        // ── T-065 (R-901): لوحة مراجعة الـ diff لطلبات الموافقة ──
        case "chain_approval_request":
            openDiffPanel(data);
            break;

        case "chain_approval_verdict":
            closeDiffPanel();
            toast(data.approved
                ? "✅ تمت الموافقة — جارٍ التطبيق"
                : `❌ مرفوض (${data.reason || "denied"}) — لا كتابات`,
                data.approved ? "success" : "info");
            break;

        // ── T-066 (R-902): نتيجة الاستعادة — تقرير RestoreReport حرفيًا ──
        case "rollback_result":
            handleRollbackResult(data);
            break;

        case "chain_status":
            if (data.active) {
                toast(`🔗 Chain نشط: ${data.step || "..."}`, "info");
            } else {
                toast("مفيش chain نشط حالياً", "info");
            }
            break;

        case "agent_thinking":
            state.streaming = true;
            document.getElementById("send-btn").disabled = true;

            if (!currentAgentProgressMsg) {
                const container = document.getElementById("chat-messages");
                currentAgentProgressMsg = document.createElement("div");
                currentAgentProgressMsg.className = "chat-msg assistant agent-progress-msg";
                currentAgentProgressMsg.innerHTML = `
                    <div class="msg-label">🤖 AI</div>
                    <div class="msg-content"></div>
                `;
                container.appendChild(currentAgentProgressMsg);
            }

            agentStatusLogs.push(`💭 جاري التحليل والتفكير (جولة ${data.iteration} من ${data.max})...`);

            const thinkingContent = currentAgentProgressMsg.querySelector(".msg-content");
            if (thinkingContent) {
                let html = "";
                if (exploredItems.length > 0) {
                    html += renderExploringAccordion(exploredItems);
                }
                if (agentStatusLogs.length > 0) {
                    html += `<div class="agent-status-logs" style="margin-top: 10px; font-size: 12px; color: var(--text-muted);">`;
                    agentStatusLogs.forEach(log => {
                        html += `<p style="margin: 4px 0;">${log}</p>`;
                    });
                    html += `</div>`;
                }
                thinkingContent.innerHTML = html;
                const container = document.getElementById("chat-messages");
                container.scrollTop = container.scrollHeight;
            }
            break;

        case "agent_step":
            state.streaming = true;
            document.getElementById("send-btn").disabled = true;

            // ── Terminal Approval Flow (run_command) ──
            // أوامر التيرمنال ليها دورة حياة مختلفة عن باقي الأدوات:
            // awaiting_approval → (المستخدم يوافق/يرفض) → running → done/error
            // لذلك تُعرض في Terminal Card منفصل بدل ما تدخل ضمن exploring/status logs العادية.
            if (data.tool === "run_command") {
                handleRunCommandStep(data);
                break;
            }

            if (!currentAgentProgressMsg) {
                const container = document.getElementById("chat-messages");
                currentAgentProgressMsg = document.createElement("div");
                currentAgentProgressMsg.className = "chat-msg assistant agent-progress-msg";
                currentAgentProgressMsg.innerHTML = `
                    <div class="msg-label">🤖 AI</div>
                    <div class="msg-content"></div>
                `;
                container.appendChild(currentAgentProgressMsg);
            }

            const target = data.args ? (data.args.path || data.args.source || data.args.dir || data.args.command || "") : "";

            // Check if file/directory/search/tree/deps activity
            const isFileActivity = (data.tool.startsWith("auto_") || ["read_file", "write_file", "edit_file", "list_dir", "get_file_info", "get_project_tree"].includes(data.tool)) && target;
            const isRunning = ["running", "reading", "listing", "searching", "scanning"].includes(data.status);

            if (isFileActivity) {
                let item = exploredItems.find(i => i.path === target);
                if (!item) {
                    item = { path: target, status: isRunning ? "running" : "done", tool: data.tool };
                    if (data.args && data.args.start_line && data.args.end_line) {
                        item.lines = `${data.args.start_line}-${data.args.end_line}`;
                    }
                    exploredItems.push(item);
                } else {
                    item.status = isRunning ? "running" : "done";
                    if (data.args && data.args.start_line && data.args.end_line) {
                        item.lines = `${data.args.start_line}-${data.args.end_line}`;
                    }
                }
            } else {
                // Regular status log
                let stepText = "";
                const friendlyName = getToolFriendlyName(data.tool);
                const targetText = target ? `: ${target}` : "";

                if (isRunning) {
                    stepText = `⏳ جاري ${friendlyName}${targetText}...`;
                } else if (data.status === "done" || data.status === "success") {
                    stepText = `✅ تم ${friendlyName}${targetText}`;
                } else {
                    stepText = `❌ فشل ${friendlyName}${targetText}`;
                }
                agentStatusLogs.push(stepText);
            }

            const stepContent = currentAgentProgressMsg.querySelector(".msg-content");
            if (stepContent) {
                let html = "";
                if (exploredItems.length > 0) {
                    html += renderExploringAccordion(exploredItems);
                }
                if (agentStatusLogs.length > 0) {
                    html += `<div class="agent-status-logs" style="margin-top: 10px; font-size: 12px; color: var(--text-muted);">`;
                    agentStatusLogs.forEach(log => {
                        html += `<p style="margin: 4px 0;">${log}</p>`;
                    });
                    html += `</div>`;
                }
                stepContent.innerHTML = html;
                const container = document.getElementById("chat-messages");
                container.scrollTop = container.scrollHeight;
            }
            break;

        case "agent_done":
            if (currentAgentProgressMsg) {
                exploredItems.forEach(i => i.status = "done");
                const stepContent = currentAgentProgressMsg.querySelector(".msg-content");
                if (stepContent) {
                    let html = "";
                    if (exploredItems.length > 0) {
                        html += renderExploringAccordion(exploredItems);
                    }
                    if (agentStatusLogs.length > 0) {
                        html += `<div class="agent-status-logs" style="margin-top: 10px; font-size: 12px; color: var(--text-muted);">`;
                        agentStatusLogs.forEach(log => {
                            html += `<p style="margin: 4px 0;">${log}</p>`;
                        });
                        html += `<p style="margin: 4px 0;"><strong>✅ اكتمل الاستكشاف والتحليل بنجاح!</strong></p>`;
                        html += `</div>`;
                    } else {
                        html += `<div class="agent-status-logs" style="margin-top: 10px; font-size: 12px; color: var(--text-muted);">`;
                        html += `<p style="margin: 4px 0;"><strong>✅ اكتمل الاستكشاف والتحليل بنجاح!</strong></p>`;
                        html += `</div>`;
                    }
                    stepContent.innerHTML = html;
                }
            }
            currentAgentProgressMsg = null;
            exploredItems = [];
            agentStatusLogs = [];
            break;

        // ── M6: Delegate System ──
        case "delegate_started":
            addDelegateProgress("started", data);
            break;

        case "delegate_phase":
            updateDelegateProgress(data.phase, data.status, data);
            break;

        case "delegate_review":
            showDelegateReview(data);
            break;

        case "delegate_landed":
            toast("✅ تم اعتماد التعديلات", "success");
            break;

        case "delegate_rejected":
            toast(`❌ تم رفض التعديلات: ${data.reason || ""}`, "info");
            break;

        case "delegate_error":
            addChatMessage("assistant", `❌ خطأ في التفويض: ${data.error}`);
            state.streaming = false;
            document.getElementById("send-btn").disabled = false;
            break;
    }
}

// ═══════════════════════════════════════════
// Terminal Approval Card (run_command lifecycle)
// awaiting_approval → [قرار المستخدم] → running → done/error
// ═══════════════════════════════════════════

/**
 * راوتر لكل أحداث agent_step الخاصة بـ tool === "run_command".
 * بيمسك الكارت الحالي في currentTerminalCardEl ويحدّثه حسب data.status.
 */
function handleRunCommandStep(data) {
    const container = document.getElementById("chat-messages");
    const command = (data.args && data.args.command) || "";
    const reason = data.reason || data.text || "";

    if (data.status === "awaiting_approval") {
        currentTerminalCardEl = document.createElement("div");
        currentTerminalCardEl.className = "chat-msg system terminal-approval-msg";
        currentTerminalCardEl.innerHTML = renderTerminalCard(command, reason, "pending");
        container.appendChild(currentTerminalCardEl);
        container.scrollTop = container.scrollHeight;
        return;
    }

    // لو وصلت حالة running/done بدون ما نمر على awaiting_approval (احتياطي)
    if (!currentTerminalCardEl) {
        currentTerminalCardEl = document.createElement("div");
        currentTerminalCardEl.className = "chat-msg system terminal-approval-msg";
        currentTerminalCardEl.innerHTML = renderTerminalCard(command, reason, "running");
        container.appendChild(currentTerminalCardEl);
    }

    if (data.status === "running") {
        updateTerminalCardStatus(currentTerminalCardEl, "running");
    } else if (data.status === "done" || data.status === "success") {
        updateTerminalCardStatus(currentTerminalCardEl, "success", data.preview || data.output || "");
        currentTerminalCardEl = null;
    } else if (data.status === "error" || data.status === "failed") {
        updateTerminalCardStatus(currentTerminalCardEl, "error", data.preview || data.error || "");
        currentTerminalCardEl = null;
    }

    container.scrollTop = container.scrollHeight;
}

/** يبني HTML كارت التيرمنال بحالته الأولية (pending/running) */
function renderTerminalCard(command, reason, status) {
    const dotClass = status === "running" ? "running"
        : status === "success" ? "success"
            : status === "error" ? "error"
                : "pending";

    const title = status === "pending" ? "طلب تنفيذ أمر — بانتظار موافقتك"
        : status === "running" ? "جاري التنفيذ..."
            : status === "success" ? "تم التنفيذ بنجاح"
                : "فشل التنفيذ";

    const actionsHtml = status === "pending"
        ? `
            <div class="terminal-actions">
                <button class="terminal-btn accept" onclick="respondAgentApproval(true, this)">▶ تنفيذ</button>
                <button class="terminal-btn reject" onclick="respondAgentApproval(false, this)">✕ رفض</button>
            </div>
        `
        : `<div class="terminal-actions"><span class="terminal-spinner">⏳ جاري التنفيذ...</span></div>`;

    return `
        <div class="terminal-card" data-status="${status}">
            <div class="terminal-card-header">
                <span class="terminal-status-dot ${dotClass}"></span>
                <span class="terminal-card-title">🖥️ ${escapeHtml(title)}</span>
            </div>
            <div class="terminal-command-line"><span class="prompt">$</span> ${escapeHtml(command)}</div>
            ${reason ? `<div class="terminal-reason">${escapeHtml(reason)}</div>` : ""}
            ${actionsHtml}
            <div class="terminal-output-wrap hidden"></div>
        </div>
    `;
}

/** يحدّث حالة كارت موجود (pending/running/success/error/rejected) + الناتج لو موجود */
function updateTerminalCardStatus(cardEl, status, output) {
    if (!cardEl) return;
    const card = cardEl.querySelector(".terminal-card");
    if (!card) return;

    card.setAttribute("data-status", status);

    const dot = card.querySelector(".terminal-status-dot");
    const title = card.querySelector(".terminal-card-title");
    const actions = card.querySelector(".terminal-actions");
    const outputWrap = card.querySelector(".terminal-output-wrap");

    if (dot) dot.className = `terminal-status-dot ${status === "rejected" ? "error" : status}`;

    if (status === "running") {
        if (title) title.textContent = "🖥️ جاري التنفيذ...";
        if (actions) actions.innerHTML = `<span class="terminal-spinner">⏳ جاري التنفيذ...</span>`;
    } else if (status === "success") {
        if (title) title.textContent = "🖥️ ✅ تم التنفيذ بنجاح";
        if (actions) actions.remove();
        if (outputWrap) {
            outputWrap.classList.remove("hidden");
            outputWrap.innerHTML = `
                <pre class="terminal-output">${escapeHtml(output || "(بدون ناتج)")}</pre>
                <button class="terminal-copy-btn" onclick="copyTerminalOutput(this)">📋 نسخ الناتج</button>
            `;
        }
    } else if (status === "error") {
        if (title) title.textContent = "🖥️ ❌ فشل التنفيذ";
        if (actions) actions.remove();
        if (outputWrap) {
            outputWrap.classList.remove("hidden");
            outputWrap.innerHTML = `
                <pre class="terminal-output error">${escapeHtml(output || "(بدون تفاصيل)")}</pre>
                <button class="terminal-copy-btn" onclick="copyTerminalOutput(this)">📋 نسخ الناتج</button>
            `;
        }
    } else if (status === "rejected") {
        if (title) title.textContent = "🖥️ تم رفض التنفيذ";
        if (actions) actions.remove();
    }

    const container = document.getElementById("chat-messages");
    if (container) container.scrollTop = container.scrollHeight;
}

/**
 * بترسل قرار المستخدم (موافقة/رفض) للسيرفر عبر WebSocket:
 * { type: "agent_approval_response", approved: true/false }
 * وده بيفك approve_command() في agent_loop.py على الباك إند.
 */
function respondAgentApproval(approved, btn) {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        toast("⚠️ الاتصال غير متاح حالياً", "error");
        return;
    }

    state.ws.send(JSON.stringify({ type: "agent_approval_response", approved: approved }));

    if (btn) {
        const actions = btn.closest(".terminal-actions");
        if (actions) {
            actions.querySelectorAll("button").forEach(b => (b.disabled = true));
        }
    }

    if (currentTerminalCardEl) {
        if (approved) {
            updateTerminalCardStatus(currentTerminalCardEl, "running");
        } else {
            updateTerminalCardStatus(currentTerminalCardEl, "rejected");
            currentTerminalCardEl = null;
        }
    }
}

/** نسخ ناتج التيرمنال (stdout/stderr) من كارت الموافقة بعد التنفيذ */
function copyTerminalOutput(btn) {
    const pre = btn.previousElementSibling;
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent)
        .then(() => {
            const original = btn.innerHTML;
            btn.innerHTML = "✅ تم النسخ!";
            setTimeout(() => { btn.innerHTML = original; }, 2000);
        })
        .catch(() => toast("فشل النسخ", "error"));
}

// ═══════════════════════════════════════════
// Chat
// ═══════════════════════════════════════════
function sendMessage() {
    const input = document.getElementById("chat-input");
    let text = input.value.trim();
    if (!text || state.streaming || !state.connected) return;

    // Reset progress arrays
    exploredItems = [];
    agentStatusLogs = [];
    currentAgentProgressMsg = null;
    currentTerminalCardEl = null;
    currentChainMsg = null;
    currentChainText = "";

    // هل في مجلد مرفق؟ → chain_message
    const folderAttach = state.attachments.find(a => a.isFolder);

    if (folderAttach) {
        // عرض رسالة المستخدم
        const displayText = input.value.trim();
        addChatMessage("user", displayText + ` 📂 ${folderAttach.name} (${Object.keys(folderAttach.files).length} ملف)`);
        input.value = "";
        autoResizeInput(input);

        // إرسال chain_message مع الملفات
        state.ws.send(JSON.stringify({
            type: "chain_message",
            text: text,
            files: folderAttach.files,
            mode: state.mode,
        }));

        clearAttachments();
        document.getElementById("send-btn").disabled = true;
        return;
    }

    // دمج المرفقات العادية في النص
    if (state.attachments.length > 0) {
        let attachText = "\n\n[📎 ملفات مرفقة]:";
        state.attachments.forEach(att => {
            const ext = att.name.split(".").pop() || "";
            attachText += `\n\n📄 **${att.name}**\n\`\`\`${ext}\n${att.content}\n\`\`\``;
        });
        text += attachText;
        clearAttachments();
    }

    // عرض رسالة المستخدم (بدون محتوى الملفات الطويل)
    const displayText = input.value.trim();
    addChatMessage("user", displayText + (state.attachments.length > 0 ? " 📎" : ""));
    input.value = "";
    autoResizeInput(input);

    // إرسال عبر WebSocket
    state.ws.send(JSON.stringify({
        type: "message",
        text: text,
        mode: state.mode,
    }));

    // تعطيل الزر أثناء الـ streaming
    document.getElementById("send-btn").disabled = true;
}

function addChatMessage(role, content) {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = `chat-msg ${role}`;

    const label = role === "user" ? "👤 أنت" : "🤖 AI";
    const dir = detectDirection(content);

    if (role === "user") {
        msg.innerHTML = `
            <div class="msg-label">${label}</div>
            <div class="msg-content" dir="${dir}">${escapeHtml(content)}</div>
        `;
    } else {
        const channels = parseResponseChannels(content);
        if (channels.hasChannels) {
            let html = `<div class="msg-label">${label}</div>`;
            html += `<div class="msg-content" dir="${dir}">`;
            if (channels.other) {
                html += `<div class="other-section">${renderMarkdown(channels.other)}</div>`;
            }
            if (channels.thinking) {
                html += `
                    <details class="thinking-accordion">
                        <summary>💭 التفكير (Thinking Stream)</summary>
                        <div class="thinking-content">${renderMarkdown(channels.thinking)}</div>
                    </details>
                `;
            }
            if (channels.result) {
                html += `<div class="result-section">${renderMarkdown(channels.result)}</div>`;
            }
            html += `</div>`;
            msg.innerHTML = html;
        } else {
            msg.innerHTML = `
                <div class="msg-label">${label}</div>
                <div class="msg-content" dir="${dir}">${renderMarkdown(content)}</div>
            `;
        }
        // T-064: إبراز بلوكات الكود في الرسالة (fence-tag أو auto-detect).
        CodeHighlight.highlightContainer(msg);

        // Add copy response button for assistant messages
        const copyBtn = document.createElement("button");
        copyBtn.className = "copy-response-btn";
        copyBtn.innerHTML = "📋 نسخ الرد";
        copyBtn.onclick = () => copyFullResponse(copyBtn, content);
        msg.appendChild(copyBtn);
    }

    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
}

let currentStreamMsg = null;
let currentStreamText = "";
let currentChainMsg = null;
let currentChainText = "";
let currentAgentProgressMsg = null;
let exploredItems = [];
let agentStatusLogs = [];
let currentTerminalCardEl = null; // كارت التيرمنال الحالي (pending/running) لأمر run_command

function startStreamingMessage() {
    const container = document.getElementById("chat-messages");
    currentStreamText = "";

    currentStreamMsg = document.createElement("div");
    currentStreamMsg.className = "chat-msg assistant";
    currentStreamMsg.innerHTML = `
        <div class="msg-label">🤖 AI <span class="streaming-dot"></span></div>
        <div class="msg-content streaming-content"></div>
    `;
    container.appendChild(currentStreamMsg);
    container.scrollTop = container.scrollHeight;
}

function appendStreamChunk(text) {
    if (!currentStreamMsg) return;
    currentStreamText += text;

    const content = currentStreamMsg.querySelector(".streaming-content");
    const channels = parseResponseChannels(currentStreamText);
    if (channels.hasChannels) {
        let html = "";
        if (channels.other) {
            html += `<div class="other-section">${renderMarkdown(channels.other)}</div>`;
        }
        if (channels.thinking) {
            html += `
                <details class="thinking-accordion" open>
                    <summary>💭 التفكير (Thinking Stream)</summary>
                    <div class="thinking-content">${renderMarkdown(channels.thinking)}</div>
                </details>
            `;
        }
        if (channels.result) {
            html += `<div class="result-section">${renderMarkdown(channels.result)}</div>`;
        }
        content.innerHTML = html;
    } else {
        content.innerHTML = renderMarkdown(currentStreamText);
    }

    // T-064: إبراز تدفقي — البلوكات المكتملة تُخدم من كاش LRU (نفس
    // السلسلة حرفيًا = لا وميض)، والبلوك المفتوح الأخير فقط يُعاد تحليله.
    CodeHighlight.highlightContainer(content);

    // Auto scroll
    const container = document.getElementById("chat-messages");
    container.scrollTop = container.scrollHeight;
}

function finalizeStreamMessage(data) {
    if (currentStreamMsg) {
        // إزالة streaming dot
        const label = currentStreamMsg.querySelector(".msg-label");
        label.innerHTML = "🤖 AI";

        // Render النهائي مع syntax highlighting
        const content = currentStreamMsg.querySelector(".streaming-content");
        const channels = parseResponseChannels(currentStreamText);
        if (channels.hasChannels) {
            let html = "";
            if (channels.other) {
                html += `<div class="other-section">${renderMarkdown(channels.other)}</div>`;
            }
            if (channels.thinking) {
                html += `
                    <details class="thinking-accordion">
                        <summary>💭 التفكير (Thinking Stream)</summary>
                        <div class="thinking-content">${renderMarkdown(channels.thinking)}</div>
                    </details>
                `;
            }
            if (channels.result) {
                html += `<div class="result-section">${renderMarkdown(channels.result)}</div>`;
            }
            content.innerHTML = html;
        } else {
            content.innerHTML = renderMarkdown(currentStreamText);
        }
        content.classList.remove("streaming-content");

        // تطبيق اتجاه النص (RTL/LTR)
        const dir = detectDirection(currentStreamText);
        content.setAttribute("dir", dir);
        // Apply direction to individual paragraphs for mixed content
        applyParagraphDirections(content);

        // highlight code blocks — T-064: عبر نقطة الاستهلاك الوحيدة (مُكاش).
        CodeHighlight.highlightContainer(content);

        // إضافة أزرار Apply على الأكواد
        addApplyButtons(content, currentStreamText);

        // إضافة زرار نسخ الرد الكامل
        const copyBtn = document.createElement("button");
        copyBtn.className = "copy-response-btn";
        copyBtn.innerHTML = "📋 نسخ الرد";
        copyBtn.onclick = () => copyFullResponse(copyBtn, currentStreamText);
        currentStreamMsg.appendChild(copyBtn);
    }

    // عرض شريط الإجراءات
    if (data.actions && data.actions.length > 0) {
        state.pendingActions = data.actions;
        showActionsBar(data.actions, data.summary);
    }

    // عرض أزرار الاقتراحات الذكية (Quick Replies)
    if (data.options && data.options.length > 0) {
        showQuickReplies(data.options);
    }

    document.getElementById("send-btn").disabled = false;
    currentStreamMsg = null;
    currentStreamText = "";
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
// Apply Buttons & Actions
// ═══════════════════════════════════════════
function addApplyButtons(container, fullText) {
    // نبحث عن بلوكات الكود في الرد
    const codeBlocks = container.querySelectorAll("pre");
    codeBlocks.forEach((pre, idx) => {
        const code = pre.querySelector("code");
        if (!code) return;

        // نحاول نحدد اسم الملف من الكلاس
        const lang = (code.className.match(/language-(\w+)/) || [])[1] || "";
        const codeText = code.textContent;

        // إنشاء header مع زر Apply وزر Copy
        const header = document.createElement("div");
        header.className = "code-block-header";
        header.innerHTML = `
            <span>${lang || "code"}</span>
            <div class="code-block-actions">
                <button class="copy-btn" onclick="copyCodeBlock(this, ${idx})">🧲 Copy</button>
                <button class="apply-btn" onclick="applyCodeBlock(this, '${lang}', ${idx})">📋 Apply</button>
            </div>
        `;

        pre.parentNode.insertBefore(header, pre);
        // ربط الـ pre بالـ header بصرياً
        pre.style.borderTopLeftRadius = "0";
        pre.style.borderTopRightRadius = "0";
        pre.style.marginTop = "0";
    });
}

function copyCodeBlock(btn, idx) {
    const pre = btn.closest(".code-block-header").nextElementSibling;
    const code = pre ? pre.querySelector("code") : null;
    if (code) {
        navigator.clipboard.writeText(code.textContent)
            .then(() => {
                const originalText = btn.innerHTML;
                btn.innerHTML = "✅ Copied!";
                toast("تم نسخ الكود بنجاح", "success");
                setTimeout(() => { btn.innerHTML = originalText; }, 2000);
            })
            .catch(err => {
                toast("فشل النسخ: " + err, "error");
            });
    }
}

function applyCodeBlock(btn, lang, idx) {
    // نبحث عن الإجراء المقابل في pendingActions
    const fileActions = state.pendingActions.filter(a => a.action === "create_file");
    const action = fileActions[idx];

    if (action) {
        // تطبيق عبر WebSocket
        state.ws.send(JSON.stringify({ type: "apply_action", action: action }));
        btn.textContent = "✅ Applied";
        btn.classList.add("applied");
    } else {
        // لو مفيش action مربوط — نسأل عن اسم الملف
        const codeEl = btn.closest(".code-block-header").nextElementSibling;
        const code = codeEl ? codeEl.textContent : "";
        const filename = prompt("اسم الملف:", suggestFilename(lang));
        if (filename && code) {
            fetch(`/api/file/${filename}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: code }),
            })
                .then(r => r.json())
                .then(d => {
                    if (d.ok) {
                        btn.textContent = "✅ Applied";
                        btn.classList.add("applied");
                        toast(`تم حفظ: ${filename}`, "success");
                        refreshFiles();
                        openFile(filename);
                    } else {
                        toast(`فشل: ${d.error}`, "error");
                    }
                });
        }
    }
}

function suggestFilename(lang) {
    const map = {
        python: "script.py", py: "script.py",
        javascript: "main.js", js: "main.js",
        typescript: "main.ts", ts: "main.ts",
        html: "index.html",
        css: "style.css",
        json: "data.json",
    };
    return map[lang] || "output.txt";
}

function showActionsBar(actions, summary) {
    const container = document.getElementById("chat-messages");
    const bar = document.createElement("div");
    bar.className = "actions-bar";

    let chips = actions.map((a, i) => {
        const icon = a.action === "create_file" ? "📄" : a.action === "edit_file" ? "✏️" : "⚡";
        const label = a.path || a.command || "";
        return `<span class="action-chip" onclick="applySingleAction(${i}, this)">${icon} ${escapeHtml(label)}</span>`;
    }).join("");

    bar.innerHTML = `
        <span class="label">📋 ${summary}</span>
        ${chips}
        <button class="apply-all-btn" onclick="applyAllActions(this)">✨ تطبيق الكل</button>
    `;

    container.appendChild(bar);
    container.scrollTop = container.scrollHeight;
}

function applySingleAction(idx, chipEl) {
    const action = state.pendingActions[idx];
    if (!action) return;

    state.ws.send(JSON.stringify({ type: "apply_action", action: action }));
    chipEl.classList.add("done");
    chipEl.textContent = "✅ " + (action.path || action.command || "done");
}

function applyAllActions(btn) {
    state.pendingActions.forEach((action, idx) => {
        state.ws.send(JSON.stringify({ type: "apply_action", action: action }));
    });
    btn.textContent = "✅ تم التطبيق";
    btn.disabled = true;

    // تحديث كل الـ chips
    document.querySelectorAll(".action-chip:not(.done)").forEach(c => {
        c.classList.add("done");
    });

    setTimeout(() => refreshFiles(), 500);
}

function handleActionResult(data) {
    if (data.ok) {
        toast(data.message, "success");
        refreshFiles();
        // فتح الملف لو كان create
        if (data.message && data.message.includes("حفظ")) {
            const match = data.message.match(/حفظ: (.+)/);
            if (match) openFile(match[1]);
        }
    } else {
        toast(data.message, "error");
    }
}

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
            item.innerHTML = `${indent}<span class="icon">📁</span><span class="name">${key}</span>`;
            item.onclick = (e) => {
                e.stopPropagation();
                const children = item.nextElementSibling;
                if (children && children.classList.contains("tree-children")) {
                    children.classList.toggle("hidden");
                    item.querySelector(".icon").textContent = children.classList.contains("hidden") ? "📁" : "📂";
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
    filenameEl.textContent = path;
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
function loadProjectInfo() {
    fetch("/api/info")
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                document.getElementById("project-name").textContent =
                    `📂 ${data.project.name} (${data.project.total_files} files)`;
                // T-066: جذر المشروع — لاختصار المسارات المطلقة في لوحة التاريخ
                state.projectRoot = data.project.root || "";
                if (data.provider.model) {
                    document.getElementById("provider-name").textContent = data.provider.model;
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
                const container = document.getElementById("chat-messages");
                container.innerHTML = "";
                data.history.forEach(msg => {
                    addChatMessage(msg.role, msg.content);
                });
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
        return marked.parse(text);
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
                document.getElementById("project-name").textContent =
                    `📂 ${data.project.name} (${data.project.total_files} files)`;
                // مسح tabs + editor
                state.openTabs = [];
                state.activeTab = null;
                document.getElementById("tabs").innerHTML = "";
                document.getElementById("editor-welcome").style.display = "flex";
                document.getElementById("editor-content").style.display = "none";
                document.getElementById("run-btn").classList.add("hidden");
                // تحديث الملفات
                refreshFiles();
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

// ═══════════════════════════════════════════
// Sessions Management
// ═══════════════════════════════════════════
function toggleSessions() {
    const dropdown = document.getElementById("sessions-dropdown");
    if (dropdown.classList.contains("hidden")) {
        loadSessions();
        dropdown.classList.remove("hidden");
        // Close on outside click
        setTimeout(() => {
            document.addEventListener("click", closeSessionsOnOutside);
        }, 100);
    } else {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeSessionsOnOutside);
    }
}

function closeSessionsOnOutside(e) {
    const dropdown = document.getElementById("sessions-dropdown");
    const btn = document.getElementById("sessions-btn");
    if (!dropdown.contains(e.target) && e.target !== btn) {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeSessionsOnOutside);
    }
}

function loadSessions() {
    fetch("/api/sessions")
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const list = document.getElementById("sessions-list");
            state.currentSessionId = data.current;

            if (data.sessions.length === 0) {
                list.innerHTML = '<div class="sessions-empty">📋 لا توجد جلسات سابقة</div>';
                return;
            }

            list.innerHTML = data.sessions.map(s => {
                const isActive = s.id === data.current ? "active" : "";
                const date = s.updated_at ? new Date(s.updated_at).toLocaleDateString("ar-EG", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                }) : "";
                return `
                    <div class="session-item ${isActive}" onclick="loadSession('${s.id}')">
                        <span class="session-icon">💬</span>
                        <div class="session-info">
                            <div class="session-name">${escapeHtml(s.title || 'محادثة بدون عنوان')}</div>
                            <div class="session-meta">${s.message_count} رسالة • ${date}</div>
                        </div>
                        <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.id}')" title="حذف">🗑️</button>
                    </div>
                `;
            }).join("");
        })
        .catch(() => { });
}

function loadSession(sessionId) {
    fetch(`/api/session/${sessionId}`)
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                toast(data.error || "فشل تحميل الجلسة", "error");
                return;
            }
            state.currentSessionId = sessionId;
            const container = document.getElementById("chat-messages");
            container.innerHTML = "";
            if (data.history) {
                data.history.forEach(msg => {
                    addChatMessage(msg.role, msg.content);
                });
            }
            toast(`تم تحميل الجلسة`, "success");
            document.getElementById("sessions-dropdown").classList.add("hidden");
        })
        .catch(() => toast("فشل تحميل الجلسة", "error"));
}

function newSession() {
    fetch("/api/session/new", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                state.currentSessionId = data.session.id;
                document.getElementById("chat-messages").innerHTML = "";
                addChatMessage("assistant", "مرحباً! 👋 جلسة جديدة. اكتب سؤالك أو اطلب مني أي حاجة!");
                toast("تم بدء محادثة جديدة", "success");
                document.getElementById("sessions-dropdown").classList.add("hidden");
            }
        })
        .catch(() => toast("فشل إنشاء الجلسة", "error"));
}

function deleteSession(sessionId) {
    if (!confirm("حذف هذه الجلسة؟")) return;
    fetch(`/api/session/${sessionId}`, { method: "DELETE" })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast("تم حذف الجلسة", "info");
                loadSessions();
            }
        })
        .catch(() => { });
}

// ═══════════════════════════════════════════
// Model Picker
// ═══════════════════════════════════════════
function loadModels() {
    fetch("/api/models")
        .then(r => r.json())
        .then(data => {
            if (!data.ok) return;
            const label = document.getElementById("current-model-label");
            label.textContent = `${data.current.provider}/${data.current.model}`;
            renderModelList(data.providers, data.current);
        })
        .catch(() => { });
}

function renderModelList(providers, current) {
    const list = document.getElementById("model-list");
    let html = "";

    providers.forEach(prov => {
        html += `<div style="padding:6px 12px;font-size:11px;color:var(--text-muted);font-weight:600;">${prov.name}</div>`;
        prov.models.forEach(model => {
            const isActive = (prov.id === current.provider && model === current.model) ? "active" : "";
            html += `
                <div class="session-item ${isActive}" onclick="switchModel('${prov.id}', '${model}')">
                    <span class="session-icon">${isActive ? '✅' : '○'}</span>
                    <div class="session-info">
                        <div class="session-name">${model}</div>
                    </div>
                </div>
            `;
        });
    });

    list.innerHTML = html;
}

function toggleModelPicker() {
    const dropdown = document.getElementById("model-dropdown");
    if (dropdown.classList.contains("hidden")) {
        loadModels();
        dropdown.classList.remove("hidden");
        setTimeout(() => {
            document.addEventListener("click", closeModelOnOutside);
        }, 100);
    } else {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeModelOnOutside);
    }
}

function closeModelOnOutside(e) {
    const dropdown = document.getElementById("model-dropdown");
    const btn = document.getElementById("model-btn");
    if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
        dropdown.classList.add("hidden");
        document.removeEventListener("click", closeModelOnOutside);
    }
}

function switchModel(providerId, modelName) {
    toast(`جاري التغيير لـ: ${modelName}...`, "info");
    fetch("/api/switch-model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: providerId, model: modelName }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast(`✅ تم التغيير: ${providerId}/${modelName}`, "success");
                document.getElementById("current-model-label").textContent = `${providerId}/${modelName}`;
                document.getElementById("model-dropdown").classList.add("hidden");
                loadModels();
            } else {
                toast(`❌ فشل: ${data.error}`, "error");
            }
        })
        .catch(err => toast(`❌ خطأ: ${err}`, "error"));
}

// ═══════════════════════════════════════════
// Drag & Drop Files + Folders to Chat
// ═══════════════════════════════════════════
const _TEXT_EXTENSIONS = new Set([
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".json", ".yaml", ".yml", ".toml",
    ".py", ".sh", ".bat", ".ps1",
    ".md", ".txt", ".env", ".gitignore",
    ".svg", ".xml", ".vue", ".svelte",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".dart",
    ".sql", ".graphql", ".proto",
]);

const _IGNORE_DIRS = new Set([
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", ".cache", ".vscode", ".idea",
    "venv", ".venv", "env", ".env", ".tox",
    "target", "bin", "obj", ".gradle", ".ai_runs",
]);

const _MAX_FILE_SIZE = 200 * 1024;   // 200KB per file
const _MAX_TOTAL_SIZE = 2 * 1024 * 1024; // 2MB total
const _MAX_FILES = 50;

function initDragDrop() {
    const chatPanel = document.getElementById("chat-panel");
    const overlay = document.getElementById("drag-overlay");
    let dragCounter = 0;

    chatPanel.addEventListener("dragenter", (e) => {
        e.preventDefault();
        dragCounter++;
        overlay.classList.remove("hidden");
    });

    chatPanel.addEventListener("dragleave", (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            overlay.classList.add("hidden");
        }
    });

    chatPanel.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
    });

    chatPanel.addEventListener("drop", (e) => {
        e.preventDefault();
        dragCounter = 0;
        overlay.classList.add("hidden");
        console.log("[DROP] event fired");

        // ── محاولة 1: فحص مجلدات (webkitGetAsEntry) ──
        let hasFolder = false;
        let folderEntry = null;
        try {
            const items = e.dataTransfer.items;
            if (items && items.length > 0) {
                for (let i = 0; i < items.length; i++) {
                    const entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null;
                    if (entry && entry.isDirectory) {
                        hasFolder = true;
                        folderEntry = entry;
                        break;
                    }
                }
            }
        } catch (err) {
            console.log("[DROP] webkitGetAsEntry not supported:", err);
        }

        if (hasFolder && folderEntry) {
            // ── مجلد: قراءة recursive ──
            const folderName = folderEntry.name;
            console.log("[DROP] folder detected:", folderName);
            toast(`📂 جاري قراءة المجلد: ${folderName}...`, "info");

            readDirectoryRecursive(folderEntry, "").then(files => {
                if (Object.keys(files).length === 0) {
                    toast("⚠️ المجلد فاضي أو مفيش ملفات نصية", "error");
                    return;
                }
                attachFolder(folderName, files);
            }).catch(err => {
                console.error("[DROP] folder read error:", err);
                toast(`❌ فشل قراءة المجلد: ${err.message}`, "error");
            });
            return;
        }

        // ── محاولة 2: ملفات من سطح المكتب / المتصفح (الطريقة المضمونة) ──
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            console.log("[DROP] files detected:", e.dataTransfer.files.length);
            Array.from(e.dataTransfer.files).forEach(file => {
                if (file.size > 500 * 1024) {
                    toast(`⚠️ ${file.name} كبير جداً (> 500KB)`, "error");
                    return;
                }
                const reader = new FileReader();
                reader.onload = (ev) => {
                    attachFile(file.name, ev.target.result);
                };
                reader.readAsText(file);
            });
            return;
        }

        // ── محاولة 3: ملف/مجلد من الـ file tree (data-path) ──
        const filePath = e.dataTransfer.getData("text/plain");
        if (filePath) {
            console.log("[DROP] file tree drag:", filePath);

            if (filePath.startsWith("folder:")) {
                // ── مجلد من الـ file tree ──
                const folderName = filePath.slice(7);
                toast(`📂 جاري قراءة المجلد: ${folderName}...`, "info");
                fetch(`/api/folder/${folderName}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.ok && data.files) {
                            attachFolder(folderName, data.files);
                        } else {
                            toast(`❌ فشل قراءة المجلد: ${data.error || "خطأ"}`, "error");
                        }
                    })
                    .catch(err => toast(`❌ ${err.message}`, "error"));
            } else {
                // ── ملف من الـ file tree ──
                fetch(`/api/file/${filePath}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.ok) {
                            attachFile(filePath.split("/").pop(), data.content);
                        }
                    })
                    .catch(() => { });
            }
        }
    });
}

// ── قراءة مجلد recursive ──
async function readDirectoryRecursive(dirEntry, basePath) {
    const files = {};
    let totalSize = 0;

    async function readDir(entry, path) {
        if (Object.keys(files).length >= _MAX_FILES) return;
        if (totalSize >= _MAX_TOTAL_SIZE) return;

        const reader = entry.createReader();
        const entries = await new Promise((resolve, reject) => {
            const allEntries = [];
            function readBatch() {
                reader.readEntries(batch => {
                    if (batch.length === 0) {
                        resolve(allEntries);
                    } else {
                        allEntries.push(...batch);
                        readBatch(); // Chrome returns max 100 per batch
                    }
                }, reject);
            }
            readBatch();
        });

        // Sort: files first by extension priority
        entries.sort((a, b) => {
            if (a.isDirectory !== b.isDirectory) return a.isDirectory ? 1 : -1;
            return a.name.localeCompare(b.name);
        });

        for (const child of entries) {
            if (Object.keys(files).length >= _MAX_FILES) break;
            if (totalSize >= _MAX_TOTAL_SIZE) break;

            if (child.isDirectory) {
                if (_IGNORE_DIRS.has(child.name) || child.name.startsWith(".")) continue;
                await readDir(child, path ? `${path}/${child.name}` : child.name);
            } else if (child.isFile) {
                const ext = "." + child.name.split(".").pop().toLowerCase();
                if (!_TEXT_EXTENSIONS.has(ext)) continue;

                try {
                    const fileContent = await readFileEntry(child);
                    if (fileContent.length > _MAX_FILE_SIZE) continue;
                    if (totalSize + fileContent.length > _MAX_TOTAL_SIZE) break;

                    const relPath = path ? `${path}/${child.name}` : child.name;
                    files[relPath] = fileContent;
                    totalSize += fileContent.length;
                } catch {
                    // skip unreadable files
                }
            }
        }
    }

    await readDir(dirEntry, basePath);
    return files;
}

function readFileEntry(fileEntry) {
    return new Promise((resolve, reject) => {
        fileEntry.file(file => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsText(file);
        }, reject);
    });
}

// ── Attachment Functions ──
function attachFile(name, content) {
    console.log("[ATTACH] attachFile called:", name, "size:", content.length);
    state.attachments.push({ name, content, isFolder: false });
    renderAttachments();

    // ── رسالة مرئية في الشات ──
    const sizeKB = (content.length / 1024).toFixed(1);
    const lines = content.split("\n").length;
    const ext = name.split(".").pop() || "";
    console.log("[ATTACH] calling addChatMessage for file:", name);
    addChatMessage("user", `📄 تم إرفاق: ${name}\n${lines} سطر • ${sizeKB}KB • ${ext}\n💡 اكتب سؤالك عن الملف واضغط Send`);
    toast(`📎 تم إرفاق: ${name}`, "info");
}

function attachFolder(name, files) {
    console.log("[ATTACH] attachFolder called:", name, "files:", Object.keys(files).length);
    // Remove any previous folder attachment
    state.attachments = state.attachments.filter(a => !a.isFolder);
    state.attachments.push({ name, files, isFolder: true });
    renderAttachments();

    // ── رسالة مرئية في الشات ──
    const fileList = Object.keys(files);
    const totalSize = Object.values(files).reduce((s, c) => s + c.length, 0);
    const sizeKB = (totalSize / 1024).toFixed(1);
    const preview = fileList.slice(0, 6).map(f => `  📄 ${f}`).join("\n");
    const more = fileList.length > 6 ? `\n  ... و${fileList.length - 6} ملف آخر` : "";
    console.log("[ATTACH] calling addChatMessage for folder:", name);
    addChatMessage("user", `📂 تم إرفاق مجلد: ${name}\n${fileList.length} ملف • ${sizeKB}KB\n${preview}${more}\n\n💡 اكتب طلبك واضغط Send — الملفات ستُرسل تلقائياً`);
    toast(`📂 تم قراءة ${fileList.length} ملف من ${name}`, "success");
}


function removeAttachment(idx) {
    state.attachments.splice(idx, 1);
    renderAttachments();
}

function clearAttachments() {
    state.attachments = [];
    renderAttachments();
}

function renderAttachments() {
    const container = document.getElementById("attached-files");
    if (state.attachments.length === 0) {
        container.classList.add("hidden");
        container.innerHTML = "";
        return;
    }
    container.classList.remove("hidden");
    container.innerHTML = state.attachments.map((att, i) => {
        if (att.isFolder) {
            const count = Object.keys(att.files).length;
            const size = Object.values(att.files).reduce((s, c) => s + c.length, 0);
            const sizeKB = (size / 1024).toFixed(1);
            return `
                <div class="attached-file folder-attach">
                    📂 ${escapeHtml(att.name)} <span class="attach-meta">(${count} ملف، ${sizeKB}KB)</span>
                    <span class="remove-attach" onclick="removeAttachment(${i})">×</span>
                </div>
            `;
        }
        return `
            <div class="attached-file">
                ${fileIconHTML(att.name)}
                ${escapeHtml(att.name)}
                <span class="remove-attach" onclick="removeAttachment(${i})">×</span>
            </div>
        `;
    }).join("");
}

// ═══════════════════════════════════════════
// Plan Card & Task Progress
// ═══════════════════════════════════════════
function showPlanCard(actions, summary) {
    state.planActions = actions;
    const container = document.getElementById("chat-messages");

    const card = document.createElement("div");
    card.className = "plan-card";

    let actionsList = actions.map((a, i) => {
        const icon = a.action === "create_file" ? "📄" : a.action === "edit_file" ? "✏️" : "⚡";
        const label = a.path || a.command || "";
        return `<div class="task-item pending"><span class="task-icon">⬜</span> ${icon} ${escapeHtml(label)}</div>`;
    }).join("");

    card.innerHTML = `
        <div class="plan-header">📋 خطة التنفيذ — ${escapeHtml(summary)}</div>
        <div class="plan-content">
            ${actionsList}
        </div>
        <div class="plan-controls">
            <button class="btn-approve" onclick="executePlan(this)">✅ موافق — نفّذ</button>
            <button class="btn-revise" onclick="revisePlan()">🔄 حدّث الكود</button>
            <button class="btn-review" onclick="reviewPlan()">📝 راجع تاني</button>
            <button class="btn-cancel" onclick="cancelPlan(this)">❌ إلغاء</button>
        </div>
    `;

    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
}

function executePlan(btn) {
    if (!state.planActions.length) return;
    const planCard = btn.closest(".plan-card");
    const controls = planCard.querySelector(".plan-controls");
    controls.innerHTML = '<span style="color:var(--accent);font-size:12px">⏳ جاري التنفيذ...</span>';

    state.ws.send(JSON.stringify({
        type: "execute_plan",
        actions: state.planActions,
    }));
}

function revisePlan() {
    const input = document.getElementById("chat-input");
    input.value = "حدّث الكود وعدّل الخطة";
    sendMessage();
}

function reviewPlan() {
    const input = document.getElementById("chat-input");
    input.value = "راجع الكود تاني وتأكد من كل حاجة";
    sendMessage();
}

function cancelPlan(btn) {
    state.planActions = [];
    const planCard = btn.closest(".plan-card");
    planCard.querySelector(".plan-controls").innerHTML =
        '<span style="color:var(--error);font-size:12px">❌ تم إلغاء الخطة</span>';
    toast("تم إلغاء الخطة", "info");
}

function updateTaskProgress(data) {
    const container = document.getElementById("chat-messages");
    let progress = container.querySelector(".task-progress");

    if (!progress) {
        progress = document.createElement("div");
        progress.className = "task-progress";
        progress.innerHTML = `
            <div class="progress-header">
                <span>⚡ جاري التنفيذ...</span>
                <span class="progress-count">0/${data.total}</span>
            </div>
            <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:0%"></div></div>
            <div class="task-list"></div>
        `;
        container.appendChild(progress);
    }

    // Update progress bar
    const pct = Math.round((data.current / data.total) * 100);
    progress.querySelector(".progress-bar-fill").style.width = pct + "%";
    progress.querySelector(".progress-count").textContent = `${data.current}/${data.total}`;

    // Update task list
    const taskList = progress.querySelector(".task-list");
    const icon = data.action.action === "create_file" ? "📄" : data.action.action === "edit_file" ? "✏️" : "⚡";
    const label = data.action.path || data.action.command || "";

    let taskEl = taskList.querySelector(`[data-task="${data.current}"]`);
    if (!taskEl) {
        taskEl = document.createElement("div");
        taskEl.className = "task-item running";
        taskEl.setAttribute("data-task", data.current);
        taskEl.innerHTML = `<span class="task-icon">🔄</span> ${icon} ${escapeHtml(label)}`;
        taskList.appendChild(taskEl);
    }

    if (data.status === "done") {
        taskEl.className = "task-item done";
        taskEl.querySelector(".task-icon").textContent = "✅";
    } else if (data.status === "error") {
        taskEl.className = "task-item error";
        taskEl.querySelector(".task-icon").textContent = "❌";
    }

    container.scrollTop = container.scrollHeight;
}

// ═══════════════════════════════════════════
// M6: Delegate System UI
// ═══════════════════════════════════════════

let _delegateProgressEl = null;

function addDelegateProgress(status, data) {
    const container = document.getElementById("chat-messages");
    _delegateProgressEl = document.createElement("div");
    _delegateProgressEl.className = "chat-msg system delegate-progress";

    const phases = [
        { id: "brief", label: "📝 كتابة Brief", status: "pending" },
        { id: "implement", label: "⚡ التنفيذ", status: "pending" },
        { id: "review", label: "🔍 المراجعة", status: "pending" },
        { id: "approval", label: "✋ الموافقة", status: "pending" },
    ];

    _delegateProgressEl.innerHTML = `
        <div class="delegate-card">
            <div class="delegate-header">
                <span class="delegate-icon">🔗</span>
                <div>
                    <strong>تفويض مهمة</strong>
                    <span class="delegate-meta">${data.files_count || 0} ملف</span>
                </div>
            </div>
            <div class="delegate-phases" id="delegate-phases">
                ${phases.map(p => `
                    <div class="delegate-phase" id="dp-${p.id}" data-status="pending">
                        <span class="dp-indicator">○</span>
                        <span class="dp-label">${p.label}</span>
                        <span class="dp-status"></span>
                    </div>
                `).join("")}
            </div>
        </div>
    `;

    container.appendChild(_delegateProgressEl);
    container.scrollTop = container.scrollHeight;
}

function updateDelegateProgress(phase, status, data) {
    const el = document.getElementById(`dp-${phase}`);
    if (!el) return;

    el.setAttribute("data-status", status);
    const indicator = el.querySelector(".dp-indicator");
    const statusEl = el.querySelector(".dp-status");

    if (status === "running") {
        indicator.textContent = "⏳";
        indicator.classList.add("spinning");
        statusEl.textContent = "جاري...";
    } else if (status === "success") {
        indicator.textContent = "✅";
        indicator.classList.remove("spinning");
        const durationMs = data.duration_ms || 0;
        statusEl.textContent = durationMs ? `${(durationMs / 1000).toFixed(1)}s` : "تم";
    } else if (status === "error") {
        indicator.textContent = "❌";
        indicator.classList.remove("spinning");
        statusEl.textContent = "فشل";
    } else if (status === "waiting_approval") {
        indicator.textContent = "✋";
        statusEl.textContent = "بانتظارك";
    }
}

function showDelegateReview(data) {
    // Update approval phase
    updateDelegateProgress("approval", "waiting_approval", {});

    const container = document.getElementById("chat-messages");
    const card = document.createElement("div");
    card.className = "chat-msg system delegate-review-card";

    const verdict = data.verdict || {};
    const result = data.result || {};
    const reworkCount = data.rework_count || 0;

    const verdictEmoji = verdict.verdict === "approve" ? "✅" :
        verdict.verdict === "rework" ? "🔄" : "❌";

    const risksHtml = (verdict.risks || []).map(r =>
        `<div class="review-risk">⚠️ ${escapeHtml(r)}</div>`
    ).join("") || '<div class="review-risk" style="opacity:0.5">لا توجد مخاطر</div>';

    card.innerHTML = `
        <div class="delegate-review">
            <div class="review-header">
                <span class="review-verdict-badge">${verdictEmoji} ${verdict.verdict || "?"}</span>
                <strong>نتيجة المراجعة</strong>
                ${reworkCount ? `<span class="review-rework-badge">🔄 rework #${reworkCount}</span>` : ""}
            </div>

            <div class="review-summary">${escapeHtml(verdict.summary || "")}</div>

            <div class="review-details">
                <div class="review-detail">
                    <span class="review-label">النطاق:</span>
                    <span>${escapeHtml(verdict.scope_check || "—")}</span>
                </div>
                <div class="review-detail">
                    <span class="review-label">الجودة:</span>
                    <span>${escapeHtml(verdict.quality || "—")}</span>
                </div>
                <div class="review-detail">
                    <span class="review-label">ملفات متأثرة:</span>
                    <span>${result.touched_files?.length || 0} ملف</span>
                </div>
            </div>

            <div class="review-risks">
                ${risksHtml}
            </div>

            <div class="review-actions">
                <button class="review-btn approve" onclick="delegateApprove()">
                    ✅ اعتمد وطبّق
                </button>
                <button class="review-btn reject" onclick="delegateReject()">
                    ❌ ارفض
                </button>
            </div>
        </div>
    `;

    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
    state.streaming = false;
    document.getElementById("send-btn").disabled = false;
}

function delegateApprove() {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: "delegate_approve" }));
        // Update UI
        document.querySelectorAll(".review-btn").forEach(b => b.disabled = true);
        toast("⏳ جاري تطبيق التعديلات...", "info");
    }
}

function delegateReject() {
    const reason = prompt("سبب الرفض (اختياري):");
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: "delegate_reject", reason: reason || "" }));
        document.querySelectorAll(".review-btn").forEach(b => b.disabled = true);
    }
}
// ═══════════════════════════════════════════
// T-066 (R-902): لوحة تاريخ الـ runs + الاستعادة بنقرة — DOM glue فوق
// وحدة RunHistory (المنطق النقي في static/js/run_history.js).
// التنفيذ عبر أمرَي WS الموجودين rollback_run/rollback_file (T-054)؛
// التأكيد يعيد استخدام لوحة T-065 (diff من snapshot المخزن).
// ═══════════════════════════════════════════
let runHistoryEntries = [];
let pendingRollback = null; // { entry, fileIdx } بانتظار تأكيد الـ diff

async function toggleRunHistory() {
    const panel = document.getElementById("run-history-panel");
    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        return;
    }
    try {
        const r = await fetch("/api/rollback/history");
        const d = await r.json();
        runHistoryEntries = RunHistory.buildEntries(
            d.runs || [], Math.floor(Date.now() / 1000));
    } catch (e) {
        runHistoryEntries = [];
    }
    renderRunHistory();
    panel.classList.remove("hidden");
}

function renderRunHistory() {
    const listEl = document.getElementById("run-history-list");
    listEl.innerHTML = RunHistory.renderPanelHTML(
        runHistoryEntries, state.projectRoot || "");
    listEl.querySelectorAll(".rh-rollback-run").forEach(btn => {
        btn.onclick = () => confirmRollback(+btn.dataset.idx, null);
    });
    listEl.querySelectorAll(".rh-rollback-file").forEach(btn => {
        btn.onclick = () => confirmRollback(+btn.dataset.idx, +btn.dataset.fidx);
    });
}

// النقرة الأولى: جلب snapshots وفتح لوحة T-065 كتأكيد بصري.
async function confirmRollback(entryIdx, fileIdx) {
    const entry = runHistoryEntries[entryIdx];
    if (!entry) return;
    const files = fileIdx === null ? entry.files : [entry.files[fileIdx]];
    const previews = {}, currents = {};
    await Promise.all(files.map(async f => {
        try {
            const r = await fetch(`/api/rollback/preview?run_id=${
                encodeURIComponent(entry.run_id)}&path=${encodeURIComponent(f.path)}`);
            const d = await r.json();
            previews[f.path] = d.ok ? d : { absent: false, snapshot: "" };
        } catch (e) { previews[f.path] = { absent: false, snapshot: "" }; }
        try {
            const short = RunHistory.shortPath(f.path, state.projectRoot || "");
            const r2 = await fetch(`/api/file/${short}`);
            const d2 = await r2.json();
            currents[f.path] = d2.ok ? d2.content : "";
        } catch (e) { currents[f.path] = ""; }
    }));
    const built = RunHistory.confirmActions(entry, fileIdx, previews, currents);
    pendingRollback = { entry, fileIdx };
    // لوحة T-065 كعارض تأكيد محلي: إطار صناعي بلا request_id — أزرارها
    // تُحوَّل لمسار rollback عبر pendingRollback في sendDiffDecision.
    diffPanelState = DiffPanel.openState(
        { request_id: "", payload_hash: "", run_id: entry.run_id,
          actions: built.actions }, built.oldContents);
    document.getElementById("diff-panel-overlay").classList.remove("hidden");
    renderDiffPanel();
}

// يعترض قرار لوحة الـ diff عندما تكون مفتوحة كتأكيد استعادة (النقرة
// الثانية): قبول ⇒ إرسال إطار rollback من الوحدة؛ رفض ⇒ إغلاق فقط.
// يرجع true لو استُهلك القرار (فلا يُرسَل رد الموافقة للبوابة).
function consumeRollbackDecision(overrideAll) {
    if (!pendingRollback) return false;
    const { entry, fileIdx } = pendingRollback;
    pendingRollback = null;
    const approved = overrideAll === null
        ? diffPanelState.accepted.every(a => a)
        : overrideAll;
    closeDiffPanel();
    if (approved) {
        state.ws.send(JSON.stringify(RunHistory.rollbackFrame(entry, fileIdx)));
        toast("⏳ جارٍ الاستعادة...", "info");
    }
    return true;
}

function handleRollbackResult(frame) {
    const entry = RunHistory.applyRollbackResult(runHistoryEntries, frame);
    if (frame.status === "success") {
        toast(`✅ استُعيد ${(frame.restored || []).length} ملف`, "success");
    } else {
        toast(frame.status === "partial"
            ? "⚠️ استعادة جزئية — بعض الملفات تعارضت"
            : "❌ رُفضت الاستعادة", "info");
    }
    const reportEl = document.getElementById("run-history-report");
    reportEl.innerHTML = RunHistory.conflictReportHTML(frame);
    if (entry) renderRunHistory();
}

// ═══════════════════════════════════════════
// T-066 (R-906): شريحة حالة التوجيه/السعة — DOM glue فوق StatusChip.
// عرض قراءة فقط من إطارات موجودة + /api/capacity — صفر endpoints جديدة.
// الرسم مُخنوق عبر StatusChip.shouldRender (عاصفة أحداث ≠ عاصفة رسومات).
// ═══════════════════════════════════════════
const statusChipState = StatusChip.createState();
const CAPACITY_POLL_MS = 30000;

function scheduleStatusChipRender() {
    if (StatusChip.shouldRender(statusChipState, Date.now())) {
        renderStatusChip();
    } else if (!statusChipState._timer) {
        statusChipState._timer = setTimeout(() => {
            statusChipState._timer = null;
            if (StatusChip.hasPending(statusChipState)) scheduleStatusChipRender();
        }, StatusChip.MIN_RENDER_INTERVAL_MS);
    }
}

function renderStatusChip() {
    statusChipState.renderCount++;
    document.getElementById("status-chip-label").innerHTML =
        StatusChip.renderChipHTML(statusChipState);
    if (statusChipState.expanded) {
        document.getElementById("status-chip-panel").innerHTML =
            StatusChip.renderPanelHTML(statusChipState);
    }
}

function toggleStatusChip() {
    statusChipState.expanded = !statusChipState.expanded;
    const panel = document.getElementById("status-chip-panel");
    panel.classList.toggle("hidden", !statusChipState.expanded);
    if (statusChipState.expanded) {
        refreshCapacity();
        renderStatusChip();
    }
}

async function refreshCapacity() {
    try {
        const r = await fetch("/api/capacity");
        const d = await r.json();
        if (d.ok) {
            StatusChip.updateCapacity(statusChipState, d.capacity);
            scheduleStatusChipRender();
        }
    } catch (e) { /* خامل — الشريحة عرض فقط */ }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("run-history-btn").onclick = toggleRunHistory;
    document.getElementById("status-chip-label").onclick = toggleStatusChip;
    refreshCapacity();
    setInterval(refreshCapacity, CAPACITY_POLL_MS);
});
