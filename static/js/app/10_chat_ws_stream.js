// ═══════════════════════════════════════════
// app/10_chat_ws_stream.js — TSK-726e
// نقل حرفي من app.js (أسطر 141–1221 + 1296–1452 قبل النقل):
// WebSocket (initWebSocket/handleWSMessage) + بطاقات الطرفية
// + قلب الدردشة (sendMessage/البث TSK-401/الإيقاف)
// + أزرار Apply/Actions Bar.
// العقد: نطاق عام مشترك؛ يُحمَّل بعد app.js (UMDs: WSBackoff/StreamRender
// تسبق app.js فمراجع eval-time هنا آمنة).
// ═══════════════════════════════════════════

// ═══════════════════════════════════════════
// WebSocket
// ═══════════════════════════════════════════
// TSK-402 (NF-11): فواصل إعادة اتصال أُسّية بسقف + jitter بدل 3s
// الثابتة (قصف الخادم عند سقوطه) — المنطق في ws_backoff.js.
const wsReconnectBackoff = WSBackoff.createBackoff();

function initWebSocket() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws`;

    state.ws = new WebSocket(url);

    state.ws.onopen = () => {
        state.connected = true;
        updateConnectionDot(true);
        wsReconnectBackoff.reset();
        // TSK-732d (D-19-4): استعادة صورة المهمة الخلفية بعد
        // إعادة اتصال — snapshot من الكائن الحي (reconnect-safe).
        state.ws.send(JSON.stringify({ type: "background_status" }));
    };

    state.ws.onclose = () => {
        state.connected = false;
        updateConnectionDot(false);
        // TSK-402 (NF-11): فاصل متزايد بسقف بدل ثابت 3s.
        const delay = wsReconnectBackoff.next();
        console.warn(`WS: انقطع الاتصال — إعادة المحاولة بعد ${delay}ms`);
        setTimeout(initWebSocket, delay);
    };

    state.ws.onerror = () => {
        state.connected = false;
        updateConnectionDot(false);
    };

    state.ws.onmessage = (event) => {
        // TSK-402 (NF-11): إطار مشوّه → log وتجاهل — لا استثناء يقتل
        // معالجة الرسائل.
        const data = WSBackoff.safeParseFrame(
            event.data, (msg, detail) => console.error(msg, detail)
        );
        if (!data) return;
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
    // TSK-620 (CP-8): سرد الجلسة يلتقط محطاته من الإطارات الموجودة —
    // استهلاك فقط (نفس عقد StatusChip)، ولا يغيّر مسار أي إطار.
    SessionNarrative.noteFrame(
        sessionNarrativeState, data, Math.floor(Date.now() / 1000));
    // TSK-403 (NF-12 / A3): أي إطار تالٍ لـ scan_start يعني أن العمل
    // الفعلي بدأ (start/chunk/error/…) — أزل مؤشر "جاري التفكير…".
    if (data.type !== "scan_start") removeScanIndicator();
    switch (data.type) {
        case "scan_start":
            // TSK-403 (NF-12 / A3): إشارة فورية من الخادم قبل بناء
            // السياق — مؤشر مرئي ≤200ms بدل صمت الواجهة.
            showScanIndicator();
            break;

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

        case "warning":
            // TSK-305 (NF-14): تنبيه غير معطّل — toast فقط، لا يوقف البث
            // (مثال: فشل قراءة ملف مكتشف — الطلب يكمل بدون محتواه).
            toast(data.text || "⚠️ تحذير", "error");
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
            setProjectCrumb(data.project.name, data.project.total_files);
            state.openTabs = [];
            state.activeTab = null;
            document.getElementById("tabs").innerHTML = "";
            document.getElementById("editor-welcome").style.display = "flex";
            document.getElementById("editor-content").style.display = "none";
            document.getElementById("run-btn").classList.add("hidden");
            refreshFiles();
            toast(`تم فتح: ${data.project.name}`, "success");
            break;

        case "path_detected_options": {
            const reqId = data.request_id;
            const detectedPath = data.path;
            const container = document.getElementById("chat-messages");
            const card = document.createElement("div");
            card.className = "chat-msg assistant path-decision-card";
            card.dataset.reqId = reqId;
            card.innerHTML = `
                <div class="msg-label">📂 مسار مكتشف</div>
                <div class="msg-content">
                    <p>اكتشفت مسار مجلد في رسالتك:<br>
                       <code style="word-break:break-all">${escapeHtml(detectedPath)}</code></p>
                    <p>ماذا تريد أن أفعل؟</p>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
                        <button class="action-btn" onclick="sendPathAction('${reqId}','switch',this)">🔄 تغيير مجلد العمل</button>
                        <button class="action-btn" onclick="sendPathAction('${reqId}','attach',this)">📎 إرفاق كسياق فقط</button>
                        <button class="action-btn" style="background:var(--surface-1)" onclick="sendPathAction('${reqId}','continue',this)">💬 تجاهل والمتابعة</button>
                    </div>
                </div>`;
            container.appendChild(card);
            container.scrollTop = container.scrollHeight;
            break;
        }

        case "confirm_path_failed":
            toast(`⚠️ ${data.error || "فشل تأكيد المسار"}`, "error");
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

        // ── T-114 (R-805): لوحة ذاكرة المشروع — إطارات إضافية ──
        case "memory_list_result":
            handleMemoryListResult(data);
            break;

        case "memory_edit_result":
            handleMemoryEditResult(data);
            break;

        case "memory_delete_result":
            handleMemoryDeleteResult(data);
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

        // ── TSK-732d (D-19-4): المهام الخلفية — الشارة تلتقط الإطارات
        // الأربعة (منطق الحالة نقي في BackgroundTasks؛ الغراء هنا
        // يرسم/يُطلق toast فقط — لا منطق جديد). ──
        case "background_started":
        case "background_event":
        case "background_finished":
        case "background_status":
            if (BackgroundTasks.noteFrame(backgroundTasksState, data)) {
                renderBackgroundChip();
            }
            break;
    }
}

// ═══════════════════════════════════════════
// TSK-732d (D-19-4): غراء شارة المهام الخلفية — DOM فوق
// BackgroundTasks (المنطق النقي في static/js/background_tasks.js).
// الثابت الصلب: زر الاعتماد يرسل background_approve الصريح فقط —
// والأفعال الناتجة تبقى خلف أزرار Apply القائمة (طبقتا موافقة).
// ═══════════════════════════════════════════
const backgroundTasksState = BackgroundTasks.createState();
let _bgLastToastStatus = "";   // منع تكرار toast لنفس الحالة النهائية

function renderBackgroundChip() {
    const chip = document.getElementById("bg-task-chip");
    if (!chip) return;
    const st = backgroundTasksState;
    if (BackgroundTasks.chipVisible(st)) {
        chip.innerHTML = BackgroundTasks.renderChipHTML(st);
        chip.classList.remove("hidden");
        _bgLastToastStatus = "";
    } else {
        chip.classList.add("hidden");
        chip.innerHTML = "";
        // حالة نهائية → toast واحد (لا تكرار عند إعادة snapshot).
        if (BackgroundTasks.isTerminal(st.status)
            && st.status !== _bgLastToastStatus) {
            const t = BackgroundTasks.terminalToast(st.status, st.error);
            if (t) toast(t.text, t.kind);
            _bgLastToastStatus = st.status;
        }
    }
}

function launchBackgroundDelegate() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) {
        toast("اكتب وصف المهمة أولًا ثم اضغط تفويض خلفي", "info");
        return;
    }
    if (!state.connected) {
        toast("⚠️ الاتصال مقطوع", "error");
        return;
    }
    addChatMessage("user", text + " ⏱️ (تفويض خلفي)");
    state.ws.send(JSON.stringify({
        type: "background_delegate_message",
        text: text,
    }));
    input.value = "";
    autoResizeInput(input);
}

// تفويض نقر أزرار الحسم داخل الشارة (data-bg-action).
document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-bg-action]");
    if (!btn) return;
    if (!state.connected) {
        toast("⚠️ الاتصال مقطوع", "error");
        return;
    }
    if (btn.dataset.bgAction === "approve") {
        state.ws.send(JSON.stringify({ type: "background_approve" }));
    } else if (btn.dataset.bgAction === "reject") {
        state.ws.send(JSON.stringify({ type: "background_reject",
                                       reason: "" }));
    }
});

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
        // TSK-616 (ASF-03): إظهار سقف snapshot — لو الخادم رفع علم
        // partial_rollback (المشروع تجاوز سقوف مسح snapshot) نعرض
        // تحذيرًا صريحًا: toast + نص دائم على الكارت.
        if (data.partial_rollback) {
            showPartialRollbackWarning(currentTerminalCardEl);
        }
        currentTerminalCardEl = null;
    } else if (data.status === "error" || data.status === "failed") {
        updateTerminalCardStatus(currentTerminalCardEl, "error", data.preview || data.error || "");
        currentTerminalCardEl = null;
    }

    container.scrollTop = container.scrollHeight;
}

/**
 * TSK-616 (ASF-03): تحذير «rollback جزئي» — تغطية snapshot تجاوزت
 * سقوف المسح، فالتراجع عن آثار هذا الأمر سيكون جزئيًا.
 * إظهار مزدوج: toast مؤقت + نص دائم داخل كارت التيرمنال.
 */
function showPartialRollbackWarning(cardEl) {
    const msg = "⚠️ التراجع سيكون جزئيًا — المشروع تجاوز سقف مسح snapshot";
    toast(msg, "warning");
    if (!cardEl) return;
    const card = cardEl.querySelector(".terminal-card");
    if (!card || card.querySelector(".terminal-partial-rollback")) return;
    const note = document.createElement("div");
    note.className = "terminal-partial-rollback";
    note.textContent = msg;
    card.appendChild(note);
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

    // TSK-620 (CP-8): محطة «طلب» في سرد الجلسة — التقاط فقط،
    // لا يغيّر مسار الإرسال (يغطي فرعَي message وchain_message).
    SessionNarrative.noteRequest(
        sessionNarrativeState, text, Math.floor(Date.now() / 1000));

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
    // TSK-501 (عيب 3): علم صريح للسيرفر — مرفق موجود ⇐ لا بحث نصي
    // مكرر عن مسارات داخل محتوى المرفق (يُقرأ مباشرة كبيانات).
    const hasAttachments = state.attachments.length > 0;
    if (hasAttachments) {
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
        has_attachments: hasAttachments,  // TSK-501
    }));

    // تعطيل الزر أثناء الـ streaming
    document.getElementById("send-btn").disabled = true;
}

function buildChatMessage(role, content) {
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

    return msg;
}

function addChatMessage(role, content) {
    const container = document.getElementById("chat-messages");
    const msg = buildChatMessage(role, content);
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
let scanIndicatorEl = null; // TSK-403 (NF-12 / A3): مؤشر "جاري التفكير…"

// TSK-403 (NF-12 / A3): مؤشر فوري عند وصول إطار scan_start — يظهر
// قبل بناء السياق (الذي قد يستغرق ثواني) ويُزال مع أول إطار تالٍ.
function showScanIndicator() {
    if (scanIndicatorEl) return; // موجود بالفعل
    const container = document.getElementById("chat-messages");
    if (!container) return;
    scanIndicatorEl = document.createElement("div");
    scanIndicatorEl.className = "chat-msg assistant scan-indicator";
    scanIndicatorEl.innerHTML = `
        <div class="msg-label">🤖 AI <span class="streaming-dot"></span></div>
        <div class="msg-content">🔎 جاري التفكير…</div>
    `;
    container.appendChild(scanIndicatorEl);
    container.scrollTop = container.scrollHeight;
}

function removeScanIndicator() {
    if (!scanIndicatorEl) return;
    scanIndicatorEl.remove();
    scanIndicatorEl = null;
}

function startStreamingMessage() {
    const container = document.getElementById("chat-messages");
    currentStreamText = "";
    // TSK-401 (NF-10): memo جديد لكل رسالة + إسقاط أي رندر معلّق
    // من بث سابق (يمسك مرجع رسالة قديمة).
    streamSectionMemo = StreamRender.createSectionMemo();
    streamThrottler.cancel();

    currentStreamMsg = document.createElement("div");
    currentStreamMsg.className = "chat-msg assistant";
    currentStreamMsg.innerHTML = `
        <div class="msg-label">🤖 AI <span class="streaming-dot"></span></div>
        <div class="msg-content streaming-content"></div>
    `;
    container.appendChild(currentStreamMsg);
    container.scrollTop = container.scrollHeight;
}

// TSK-401 (NF-10): حالة البث التدريجي — throttler واحد + memo مقطعي
// لكل رسالة بث (يُعاد إنشاء الـ memo في startStreamingMessage).
const streamThrottler = StreamRender.createThrottler();
let streamSectionMemo = StreamRender.createSectionMemo();

function renderStreamContent(content, fullText, memo, open) {
    // الرندر الفعلي — يُستدعى من الـ throttler (أثناء البث) أو مباشرة
    // (finalize). memo يخدم المقاطع المغلقة من الكاش — المقطع المفتوح
    // الأخير فقط يُعاد تحليله (marked.parse) — بالاتساق مع كاش T-064.
    const channels = parseResponseChannels(fullText);
    if (channels.hasChannels) {
        let html = "";
        if (channels.other) {
            html += `<div class="other-section">${memo("other", channels.other, renderMarkdown)}</div>`;
        }
        if (channels.thinking) {
            html += `
                <details class="thinking-accordion"${open ? " open" : ""}>
                    <summary>💭 التفكير (Thinking Stream)</summary>
                    <div class="thinking-content">${memo("thinking", channels.thinking, renderMarkdown)}</div>
                </details>
            `;
        }
        if (channels.result) {
            html += `<div class="result-section">${memo("result", channels.result, renderMarkdown)}</div>`;
        }
        content.innerHTML = html;
    } else {
        content.innerHTML = memo("plain", fullText, renderMarkdown);
    }

    // T-064: إبراز تدفقي — البلوكات المكتملة تُخدم من كاش LRU (نفس
    // السلسلة حرفيًا = لا وميض)، والبلوك المفتوح الأخير فقط يُعاد تحليله.
    CodeHighlight.highlightContainer(content);
}

function appendStreamChunk(text) {
    if (!currentStreamMsg) return;
    currentStreamText += text;

    // TSK-401 (NF-10): كان هنا parse + innerHTML للرد كاملًا مع كل
    // chunk (بث 100KB = مئات الرندرات الكاملة — تجمّد). الآن:
    // الرندر مُجمّع تحت rAF + فاصل زمني — آخر طلب فقط يُنفّذ ويقرأ
    // currentStreamText الكامل (لا فقد لأي محتوى).
    streamThrottler.request(() => {
        if (!currentStreamMsg) return; // انتهى البث قبل الإطار — finalize تولى الرندر
        const content = currentStreamMsg.querySelector(".streaming-content");
        renderStreamContent(content, currentStreamText, streamSectionMemo, true);
        // Auto scroll
        const container = document.getElementById("chat-messages");
        container.scrollTop = container.scrollHeight;
    });
}

function finalizeStreamMessage(data = {}) {
    // TSK-401 (NF-10): أسقط أي رندر معلّق — الرندر النهائي الكامل أدناه
    // يتكفل بكل شيء (لا سباق بين إطار مؤجل والـ finalize).
    streamThrottler.cancel();
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

// ═══════════════════════════════════════════
// UUID + Stop Generation + Send Button
// ═══════════════════════════════════════════

function generateUUID() {
    if (typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }
    // Fallback قوي مبني على crypto.getRandomValues
    const arr = new Uint8Array(16);
    crypto.getRandomValues(arr);
    arr[6] = (arr[6] & 0x0f) | 0x40; // UUID Version 4
    arr[8] = (arr[8] & 0x3f) | 0x80; // Variant 10xx
    return [...arr].map((b, i) => {
        const s = b.toString(16).padStart(2, '0');
        return (i === 4 || i === 6 || i === 8 || i === 10) ? '-' + s : s;
    }).join('');
}

function updateSendButtonState() {
    const btn = document.getElementById('send-btn');
    if (!btn) return;
    if (state.streaming) {
        btn.innerHTML = '■';
        btn.title = 'إيقاف التوليد';
        btn.classList.add('stop-mode');
    } else {
        btn.innerHTML = '▶';
        btn.title = 'إرسال';
        btn.classList.remove('stop-mode');
    }
}

function clearStopFallbackTimer() {
    if (state._stopFallbackTimer) {
        clearTimeout(state._stopFallbackTimer);
        state._stopFallbackTimer = null;
    }
}

function stopGeneration() {
    if (state.stopRequested || !state.streaming) return;
    state.stopRequested = true;
    const kind = state.activeGenerationKind;
    const reqId = state.currentRequestId;
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        if (kind === 'chain') {
            state.ws.send(JSON.stringify({ type: 'chain_cancel', request_id: reqId }));
        } else {
            state.ws.send(JSON.stringify({ type: 'stop', request_id: reqId }));
        }
    }
    // مؤقت أمان: إعادة الواجهة بعد 6 ثوانٍ إذا لم يرد السيرفر
    state._stopFallbackTimer = setTimeout(() => {
        resetStreamingUI();
    }, 6000);
}

function resetStreamingUI() {
    clearStopFallbackTimer();
    state.streaming = false;
    state.currentRequestId = null;
    state.activeGenerationKind = null;
    state.stopRequested = false;
    updateSendButtonState();
    if (typeof currentStreamMsg !== 'undefined' && currentStreamMsg) {
        finalizeStreamMessage({});
    }
}

function handleSendBtnClick() {
    if (state.streaming) {
        stopGeneration();
    } else {
        sendMessage();
    }
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
