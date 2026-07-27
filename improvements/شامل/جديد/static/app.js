/* ═══════════════════════════════════════════════════════
   🚀 WebDev AI Editor — Frontend Logic
   WebSocket + Chat + File Explorer + Editor + Terminal
   ═══════════════════════════════════════════════════════ */

// إعدادات وضع الطي: "full" لانكماش السايدبار لـ 40px، أو "tree" لطي الشجرة فقط
const SIDEBAR_COLLAPSE_MODE = "full";

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
    currentRequestId: null,
    activeGenerationKind: null,
    _stopFallbackTimer: null,
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
});

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
        if (state.streaming) {
            resetStreamingUI();
        }
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
    const generationEvents = [
        "start", "chunk", "done", "plan", "error",
        "chain_started", "chain_step", "chain_retry", "chain_warning",
        "chain_finished", "chain_cancelled", "chain_cancel_result", "chain_error"
    ];
    if (generationEvents.includes(data.type)) {
        if (data.request_id && data.request_id !== state.currentRequestId) {
            return;
        }
    }

    switch (data.type) {
        case "start":
            state.streaming = true;
            updateSendButtonState();
            startStreamingMessage();
            break;

        case "chunk":
            appendStreamChunk(data.text);
            break;

        case "done":
            resetStreamingUI();
            break;

        case "plan":
            resetStreamingUI();
            showPlanCard(data.actions, data.summary);
            break;

        case "error":
            resetStreamingUI();
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

        case "path_detected_options":
            showPathDetectedOptions(data.request_id, data.path);
            break;

        case "confirm_path_failed":
            handleConfirmPathFailed(data.request_id, data.error);
            break;

        // ── Chain System Events ──

        case "folder_scanned":
            addChatMessage("assistant", data.text);
            break;

        case "chain_started":
            addChatMessage("assistant", data.text || `🔗 Chain بدأ (${data.total_steps || "?"} خطوات)...`);
            break;

        case "chain_step":
            if (data.status === "running") {
                addChatMessage("assistant", data.text || `⏳ ${data.step_id}...`);
            } else if (data.status === "success") {
                addChatMessage("assistant", data.text || `✅ ${data.step_id}`);
            } else if (data.status === "error") {
                addChatMessage("assistant", data.text || `❌ ${data.step_id}: ${data.error || "failed"}`);
            } else if (data.status === "skipped") {
                addChatMessage("assistant", data.text || `⏭️ ${data.step_id} (skipped)`);
            }
            break;

        case "chain_retry":
            addChatMessage("assistant", data.text || `🔄 Retry...`);
            break;

        case "chain_warning":
            addChatMessage("assistant", data.text || `⚠️ تحذير`);
            break;

        case "chain_finished":
            resetStreamingUI();
            addChatMessage("assistant", data.text || `✅ Chain انتهى`);
            // If there's a final result, show it
            if (data.result) {
                addChatMessage("assistant", data.result);
            }
            break;

        case "chain_cancelled":
            resetStreamingUI();
            addChatMessage("assistant", data.text || `🛑 Chain تم إلغاؤه`);
            break;

        case "chain_error":
            resetStreamingUI();
            addChatMessage("assistant", data.text || `❌ Chain حدث خطأ فيه`);
            break;

        case "chain_cancel_result":
            toast(data.text, data.ok ? "success" : "info");
            break;

        case "chain_status":
            if (data.active) {
                toast(`🔗 Chain نشط: ${data.step || "..."}`, "info");
            } else {
                toast("مفيش chain نشط حالياً", "info");
            }
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
// Chat
// ═══════════════════════════════════════════
function addUserChatMessage(text, attachments) {
    const container = document.getElementById("chat-messages");
    if (!container) return null;

    const msg = document.createElement("div");
    msg.className = "chat-msg user";

    // Label
    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = "👤 أنت";
    msg.appendChild(label);

    // Content wrapper
    const content = document.createElement("div");
    content.className = "msg-content";
    content.setAttribute("dir", detectDirection(text));

    // Text span
    const textSpan = document.createElement("span");
    textSpan.className = "msg-text";
    textSpan.textContent = text;
    content.appendChild(textSpan);

    // Attachments container
    if (attachments && attachments.length > 0) {
        const attachContainer = document.createElement("div");
        attachContainer.className = "msg-attachments-timeline";

        attachments.forEach(att => {
            const pres = getAttachmentPresentation(att.name, att.isFolder);
            const pill = document.createElement("span");
            pill.className = `attached-file ${pres.className}`;
            pill.title = att.name;

            // Icon
            const iconSpan = document.createElement("span");
            iconSpan.className = "attach-icon";
            iconSpan.textContent = pres.icon;
            pill.appendChild(iconSpan);

            // Name
            const nameSpan = document.createElement("span");
            nameSpan.className = "attach-name";
            nameSpan.textContent = att.name.split("/").pop();
            pill.appendChild(nameSpan);

            // Meta
            const metaSpan = document.createElement("span");
            metaSpan.className = "attach-meta";
            if (att.isFolder) {
                const fileCount = att.fileCount || (att.files ? Object.keys(att.files).length : 0);
                metaSpan.textContent = ` (${fileCount} ملف)`;
            }
            pill.appendChild(metaSpan);

            // Click handler to focus path in tree/editor
            pill.addEventListener("click", () => {
                if (att.isFolder) {
                    focusPathInTree(att.name);
                } else {
                    openFile(att.name);
                    focusPathInTree(att.name);
                }
            });

            attachContainer.appendChild(pill);
        });
        content.appendChild(attachContainer);
    }

    msg.appendChild(content);
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
}

function getSafeMarkdownFence(content) {
    const matches = content.match(/`+/g);
    if (!matches) return "```";
    let maxLen = 3;
    for (const match of matches) {
        if (match.length >= maxLen) {
            maxLen = match.length + 1;
        }
    }
    return "`".repeat(maxLen);
}

function buildMergedAttachmentFiles(attachments) {
    const mergedFiles = Object.create(null);
    const collisionRegistry = Object.create(null);
    
    let totalCount = 0;
    let totalSize = 0;

    for (const att of attachments) {
        if (att.isFolder) {
            const normalizedFolderName = normalizeAttachmentPath(att.name);
            const folderCollisionKey = getAttachmentCollisionKey(normalizedFolderName);

            if (collisionRegistry.hasOwnProperty(folderCollisionKey)) {
                throw new Error(`⚠️ تعارض هيكلي: المسار ${normalizedFolderName} مسجل بالفعل كملف!`);
            }

            for (const [relPath, content] of Object.entries(att.files || {})) {
                if (typeof content !== 'string') {
                    throw new Error(`⚠️ محتوى الملف ${relPath} غير صالح!`);
                }

                const normalizedFilePath = normalizeAttachmentPath(relPath);
                const fullPath = `${normalizedFolderName}/${normalizedFilePath}`;
                const fileCollisionKey = getAttachmentCollisionKey(fullPath);

                if (collisionRegistry.hasOwnProperty(fileCollisionKey)) {
                    throw new Error(`⚠️ تعارض مسارات: الملف ${fullPath} مكرر عبر المرفقات!`);
                }

                const pathSegments = fullPath.split('/');
                let cumulativePath = "";
                for (let i = 0; i < pathSegments.length - 1; i++) {
                    cumulativePath = cumulativePath ? `${cumulativePath}/${pathSegments[i]}` : pathSegments[i];
                    const parentKey = getAttachmentCollisionKey(cumulativePath);
                    if (collisionRegistry.hasOwnProperty(parentKey)) {
                        throw new Error(`⚠️ تعارض هيكلي: المسار ${cumulativePath} مستخدم كملف ومجلد معاً!`);
                    }
                }

                for (const existingKey of Object.keys(collisionRegistry)) {
                    if (existingKey.startsWith(fileCollisionKey + "/")) {
                        throw new Error(`⚠️ تعارض هيكلي: المسار ${fullPath} مستخدم كملف ومجلد معاً!`);
                    }
                }

                const byteSize = getUtf8ByteLength(content);
                if (byteSize > _MAX_FILE_SIZE) {
                    throw new Error(`⚠️ الملف ${fullPath} يتجاوز الحد الأقصى للملَف الواحد (${formatByteSize(byteSize)})`);
                }

                mergedFiles[fullPath] = content;
                collisionRegistry[fileCollisionKey] = fullPath;
                totalCount += 1;
                totalSize += byteSize;
            }
        } else {
            const normalizedName = normalizeAttachmentPath(att.name);
            const fileCollisionKey = getAttachmentCollisionKey(normalizedName);

            if (collisionRegistry.hasOwnProperty(fileCollisionKey)) {
                throw new Error(`⚠️ تعارض مسارات: الملف ${normalizedName} مكرر عبر المرفقات!`);
            }

            const pathSegments = normalizedName.split('/');
            let cumulativePath = "";
            for (let i = 0; i < pathSegments.length - 1; i++) {
                cumulativePath = cumulativePath ? `${cumulativePath}/${pathSegments[i]}` : pathSegments[i];
                const parentKey = getAttachmentCollisionKey(cumulativePath);
                if (collisionRegistry.hasOwnProperty(parentKey)) {
                    throw new Error(`⚠️ تعارض هيكلي: المسار ${cumulativePath} مستخدم كملف ومجلد معاً!`);
                }
            }

            for (const existingKey of Object.keys(collisionRegistry)) {
                if (existingKey.startsWith(fileCollisionKey + "/")) {
                    throw new Error(`⚠️ تعارض هيكلي: المسار ${normalizedName} مستخدم كملف ومجلد معاً!`);
                }
            }

            const byteSize = getUtf8ByteLength(att.content || "");
            if (byteSize > _MAX_FILE_SIZE) {
                throw new Error(`⚠️ الملف ${normalizedName} يتجاوز الحد الأقصى للملَف الواحد (${formatByteSize(byteSize)})`);
            }

            mergedFiles[normalizedName] = att.content;
            collisionRegistry[fileCollisionKey] = normalizedName;
            totalCount += 1;
            totalSize += byteSize;
        }
    }

    if (totalCount > _MAX_FILES) {
        throw new Error(`⚠️ إجمالي عدد الملفات يتجاوز الحد الأقصى (${totalCount} > ${_MAX_FILES})`);
    }
    if (totalSize > _MAX_TOTAL_SIZE) {
        throw new Error(`⚠️ إجمالي حجم الملفات يتجاوز الحد الأقصى (${formatByteSize(totalSize)} > ${formatByteSize(_MAX_TOTAL_SIZE)})`);
    }

    return mergedFiles;
}

function sendMessage() {
    const input = document.getElementById("chat-input");
    let text = input.value.trim();
    if (!text || state.streaming || !state.connected) return;

    if (!isWebSocketOpen()) {
        toast("❌ فشل الإرسال: لا يوجد اتصال نشط بالسيرفر", "error");
        return;
    }

    const attachmentsSnapshot = [...state.attachments];
    const hasFolder = attachmentsSnapshot.some(a => a.isFolder);
    const requestId = generateUUID();

    if (hasFolder) {
        let mergedFiles;
        try {
            mergedFiles = buildMergedAttachmentFiles(attachmentsSnapshot);
        } catch (err) {
            toast(err.message, "error");
            return;
        }

        try {
            state.ws.send(JSON.stringify({
                type: "chain_message",
                text: text,
                files: mergedFiles,
                mode: state.mode,
                request_id: requestId,
            }));
        } catch (err) {
            console.error("WS Send Error:", err);
            toast(`❌ فشل إرسال البيانات: ${err.message}`, "error");
            return;
        }

        addUserChatMessage(text, attachmentsSnapshot);
        input.value = "";
        autoResizeInput(input);
        state.currentRequestId = requestId;
        state.activeGenerationKind = "chain";
        clearAttachments();
        state.streaming = true;
        updateSendButtonState();
        return;
    }

    // دمج المرفقات العادية
    let textToSend = text;
    if (attachmentsSnapshot.length > 0) {
        let attachText = "\n\n[📎 ملفات مرفقة]:";
        attachmentsSnapshot.forEach(att => {
            const ext = getAttachmentExtension(att.name).replace(".", "");
            const content = att.content || "";
            const fence = getSafeMarkdownFence(content);
            attachText += `\n\n📄 **${att.name}**\n${fence}${ext}\n${content}\n${fence}`;
        });
        textToSend += attachText;
    }

    try {
        state.ws.send(JSON.stringify({
            type: "message",
            text: textToSend,
            mode: state.mode,
            request_id: requestId,
        }));
    } catch (err) {
        console.error("WS Send Error:", err);
        toast(`❌ فشل إرسال البيانات: ${err.message}`, "error");
        return;
    }

    addUserChatMessage(text, attachmentsSnapshot);
    input.value = "";
    autoResizeInput(input);
    state.currentRequestId = requestId;
    state.activeGenerationKind = "chat";
    clearAttachments();
    state.streaming = true;
    updateSendButtonState();
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
        msg.innerHTML = `
            <div class="msg-label">${label}</div>
            <div class="msg-content" dir="${dir}">${renderMarkdown(content)}</div>
        `;
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
    content.innerHTML = renderMarkdown(currentStreamText);

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
        content.innerHTML = renderMarkdown(currentStreamText);
        content.classList.remove("streaming-content");

        // تطبيق اتجاه النص (RTL/LTR)
        const dir = detectDirection(currentStreamText);
        content.setAttribute("dir", dir);
        // Apply direction to individual paragraphs for mixed content
        applyParagraphDirections(content);

        // highlight code blocks
        content.querySelectorAll("pre code").forEach(block => {
            hljs.highlightElement(block);
        });

        // إضافة أزرار Apply على الأكواد
        addApplyButtons(content, currentStreamText);

        // إضافة زرار نسخ الرد الكامل
        const copyBtn = document.createElement("button");
        copyBtn.className = "copy-response-btn";
        copyBtn.innerHTML = "📋 نسخ الرد";
        const responseText = currentStreamText;
        copyBtn.onclick = () => copyFullResponse(copyBtn, responseText);
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
        .catch(() => {});
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

function renderTreeNode(container, node, depth, parentPath = "") {
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
        const currentPath = parentPath ? `${parentPath}/${key}` : key;

        const item = document.createElement("div");
        item.className = `tree-item ${isFile ? "file" : "dir"}`;
        item.setAttribute("data-path", currentPath);

        let indent = "";
        for (let i = 0; i < depth; i++) indent += '<span class="tree-indent"></span>';

        if (isFile) {
            const icon = getFileIcon(val.ext);
            item.innerHTML = `${indent}<span class="icon">${icon}</span><span class="name">${key}</span>`;
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
            // Make folder draggable to chat (using the full relative path)
            item.draggable = true;
            item.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", "folder:" + currentPath);
                e.dataTransfer.effectAllowed = "copy";
            });
        }

        container.appendChild(item);

        if (!isFile) {
            const childContainer = document.createElement("div");
            childContainer.className = "tree-children hidden";
            renderTreeNode(childContainer, val, depth + 1, currentPath);
            container.appendChild(childContainer);
        }
    });
}

function getFileIcon(ext) {
    const icons = {
        ".html": "🌐", ".htm": "🌐",
        ".css": "🎨", ".scss": "🎨",
        ".js": "⚡", ".jsx": "⚡", ".mjs": "⚡",
        ".ts": "💠", ".tsx": "💠",
        ".py": "🐍",
        ".json": "📋", ".yaml": "📋", ".yml": "📋",
        ".md": "📝", ".txt": "📄",
        ".svg": "🖼️", ".xml": "📃",
        ".sh": "🖥️", ".bat": "🖥️",
        ".env": "🔒", ".gitignore": "🔒",
    };
    return icons[ext] || "📄";
}

function focusPathInTree(path) {
    if (!path) return;

    // 1. فتح وتطهير حالتي الطي تلقائياً
    const sidebar = document.getElementById("sidebar");
    const tree = document.getElementById("file-tree");
    if (sidebar) sidebar.classList.remove("collapsed-full");
    if (tree) tree.classList.remove("hidden");
    setExplorerExpanded(true);

    const normalizedPath = path.replace(/\\/g, "/");
    const parts = normalizedPath.split("/");
    let current = "";

    // 2. توسيع المجلدات الأبوية خطوة بخطوة
    parts.forEach((part, index) => {
        current = current ? current + "/" + part : part;
        if (index < parts.length - 1) {
            const folderNode = Array.from(document.querySelectorAll(".tree-item"))
                .find(el => el.dataset.path === current);
            if (folderNode && folderNode.classList.contains("dir")) {
                const children = folderNode.nextElementSibling;
                if (children && children.classList.contains("tree-children")) {
                    children.classList.remove("hidden");
                    const icon = folderNode.querySelector(".icon");
                    if (icon) icon.textContent = "📂";
                }
            }
        }
    });

    // 3. العثور الآمن على الملف وتظليله
    const targetNode = Array.from(document.querySelectorAll(".tree-item"))
        .find(el => el.dataset.path === normalizedPath);

    if (targetNode) {
        // إزالة التظليل القديم
        document.querySelectorAll(".tree-item").forEach(el => el.classList.remove("active-focus"));
        
        // تظليل العنصر الجديد
        targetNode.classList.add("active-focus");

        // 4. تمرير ناعم ومؤمن داخل requestAnimationFrame
        requestAnimationFrame(() => {
            targetNode.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    }
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

    // تحديث أرقام الأسطر
    updateLineNumbers();

    // ربط أحداث التعديل
    textarea.oninput = () => {
        const isDirty = textarea.value !== state.editorOriginal;
        dirtyEl.classList.toggle("hidden", !isDirty);
        // تحديث dirty في التاب
        const tab = state.openTabs.find(t => t.path === state.activeTab);
        if (tab) tab.dirty = isDirty;
        renderTabs();
        updateLineNumbers();
    };

    // مزامنة scroll أرقام الأسطر
    textarea.onscroll = () => {
        document.getElementById("line-numbers").scrollTop = textarea.scrollTop;
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
    addStandaloneAttachment(name, text);
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
                if (data.provider.model) {
                    document.getElementById("provider-name").textContent = data.provider.model;
                }
            }
        })
        .catch(() => {});
}

function parseUserHistoryMessage(content) {
    if (typeof content !== 'string') {
        return { text: "", attachments: [] };
    }
    // 1. التحقق من صيغة المجلد المرفق في الرسائل التاريخية
    const folderRegex = /\s📂\s(.*?)\s\((\d+)\sملف\)$/;
    const folderMatch = content.match(folderRegex);
    if (folderMatch) {
        const text = content.replace(folderRegex, "");
        return {
            text: text,
            attachments: [{ name: folderMatch[1], isFolder: true, fileCount: parseInt(folderMatch[2], 10), historyOnly: true }]
        };
    }

    // 2. التحقق من صيغة الملفات المرفقة
    const separator = "\n\n[📎 ملفات مرفقة]:";
    const index = content.lastIndexOf(separator);
    if (index === -1) {
        return { text: content, attachments: [] };
    }
    const text = content.slice(0, index);
    const attachmentsPart = content.slice(index + separator.length);
    const attachments = [];

    const regex = /📄 \*\*(.*?)\*\*/g;
    let match;
    while ((match = regex.exec(attachmentsPart)) !== null) {
        attachments.push({ name: match[1], isFolder: false, historyOnly: true });
    }
    return { text, attachments };
}

function loadChatHistory() {
    fetch("/api/chat-history")
        .then(r => r.json())
        .then(data => {
            if (data.ok && data.history) {
                const container = document.getElementById("chat-messages");
                container.innerHTML = "";
                data.history.forEach(msg => {
                    if (msg.role === "user") {
                        const parsed = parseUserHistoryMessage(msg.content);
                        addUserChatMessage(parsed.text, parsed.attachments);
                    } else {
                        addChatMessage(msg.role, msg.content);
                    }
                });
            }
        })
        .catch((err) => {
            console.error("Failed to load chat history:", err);
        });
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

// ═══════════════════════════════════════════
// Markdown Rendering
// ═══════════════════════════════════════════
function renderMarkdown(text) {
    if (!text) return "";
    try {
        // Configure marked
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            }
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
        .catch(() => {});
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
                    if (msg.role === "user") {
                        const parsed = parseUserHistoryMessage(msg.content);
                        addUserChatMessage(parsed.text, parsed.attachments);
                    } else {
                        addChatMessage(msg.role, msg.content);
                    }
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
        .catch(() => {});
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
        .catch(() => {});
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

const _MAX_FILE_SIZE = 200 * 1024 * 1024;   // 200MB per file
const _MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB total
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

    chatPanel.addEventListener("drop", async (e) => {
        e.preventDefault();
        dragCounter = 0;
        overlay.classList.add("hidden");
        console.log("[DROP] event fired");

        const items = e.dataTransfer.items;
        const filesList = e.dataTransfer.files;

        // طابور معالجة متسلسل (Sequential Queue)
        const entries = [];
        try {
            if (items && items.length > 0) {
                for (let i = 0; i < items.length; i++) {
                    const entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null;
                    if (entry) {
                        entries.push(entry);
                    }
                }
            }
        } catch (err) {
            console.log("[DROP] webkitGetAsEntry failed:", err);
        }

        if (entries.length > 0) {
            for (const entry of entries) {
                if (entry.isDirectory) {
                    const folderName = entry.name;
                    toast(`📂 جاري قراءة المجلد: ${folderName}...`, "info");
                    try {
                        const remaining = getRemainingAttachmentBudget();
                        const result = await readDirectoryRecursive(entry, "", remaining);
                        if (result.error) {
                            toast(`❌ فشل قراءة المجلد ${folderName}: ${result.error}`, "error");
                        } else if (Object.keys(result.files).length === 0) {
                            toast(`⚠️ المجلد ${folderName} فارغ أو لا يحتوي على ملفات نصية مدعومة`, "warning");
                        } else {
                            setFolderAttachment(folderName, result.files);
                        }
                    } catch (err) {
                        console.error("[DROP] folder read error:", err);
                        toast(`❌ فشل قراءة المجلد ${folderName}: ${err.message}`, "error");
                    }
                } else if (entry.isFile) {
                    const ext = getAttachmentExtension(entry.name);
                    if (!_TEXT_EXTENSIONS.has(ext)) {
                        toast(`⚠️ الملف ${entry.name} غير مدعوم لأنه ليس ملفاً نصياً`, "warning");
                        continue;
                    }
                    try {
                        const fileContent = await readFileEntry(entry);
                        addStandaloneAttachment(entry.name, fileContent);
                    } catch (err) {
                        toast(`❌ فشل قراءة الملف ${entry.name}: ${err.message}`, "error");
                    }
                }
            }
        } else if (filesList && filesList.length > 0) {
            for (const file of Array.from(filesList)) {
                const ext = getAttachmentExtension(file.name);
                if (!_TEXT_EXTENSIONS.has(ext)) {
                    toast(`⚠️ الملف ${file.name} غير مدعوم لأنه ليس ملفاً نصياً`, "warning");
                    continue;
                }
                const reader = new FileReader();
                reader.onload = (ev) => {
                    if (typeof ev.target.result === 'string') {
                        addStandaloneAttachment(file.name, ev.target.result);
                    }
                };
                reader.readAsText(file);
            }
        } else {
            // محاولة 3: ملف/مجلد من الـ file tree (data-path)
            const filePath = e.dataTransfer.getData("text/plain");
            if (filePath) {
                console.log("[DROP] file tree drag:", filePath);

                if (filePath.startsWith("folder:")) {
                    const folderName = filePath.slice(7);
                    toast(`📂 جاري قراءة المجلد: ${folderName}...`, "info");
                    fetch(`/api/folder/${encodeURIComponent(folderName)}`)
                        .then(r => r.json())
                        .then(data => {
                            if (data.ok && data.files) {
                                setFolderAttachment(folderName, data.files);
                            } else {
                                toast(`❌ فشل قراءة المجلد: ${data.error || "خطأ"}`, "error");
                            }
                        })
                        .catch(err => toast(`❌ ${err.message}`, "error"));
                } else {
                    fetch(`/api/file/${encodeURIComponent(filePath)}`)
                        .then(r => r.json())
                        .then(data => {
                            if (data.ok && typeof data.content === 'string') {
                                addStandaloneAttachment(filePath.split("/").pop(), data.content);
                            } else {
                                toast(`❌ فشل قراءة الملف: ${data.error || "خطأ"}`, "error");
                            }
                        })
                        .catch(err => toast(`❌ ${err.message}`, "error"));
                }
            }
        }
    });
}

async function readDirectoryRecursive(dirEntry, basePath, budget) {
    const files = Object.create(null);
    let totalSize = 0;
    let fileCount = 0;
    let errorMsg = null;

    async function readDir(entry, path) {
        if (errorMsg) return;
        const reader = entry.createReader();
        const entries = await new Promise((resolve, reject) => {
            const allEntries = [];
            function readBatch() {
                reader.readEntries(batch => {
                    if (batch.length === 0) {
                        resolve(allEntries);
                    } else {
                        allEntries.push(...batch);
                        readBatch();
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
            if (errorMsg) break;
            if (child.isDirectory) {
                if (_IGNORE_DIRS.has(child.name) || child.name.startsWith(".")) continue;
                await readDir(child, path ? `${path}/${child.name}` : child.name);
            } else if (child.isFile) {
                const ext = getAttachmentExtension(child.name);
                if (!_TEXT_EXTENSIONS.has(ext)) continue;

                try {
                    const fileContent = await readFileEntry(child);
                    const byteLength = getUtf8ByteLength(fileContent);

                    if (byteLength > _MAX_FILE_SIZE) {
                        errorMsg = `الملف ${child.name} يتجاوز الحد الأقصى للملف الواحد (${formatByteSize(byteLength)} > ${formatByteSize(_MAX_FILE_SIZE)})`;
                        break;
                    }

                    if (fileCount + 1 > budget.maxFiles) {
                        errorMsg = `عدد الملفات المرفقة يتجاوز الحد الأقصى للملفات المسموح بها وهو ${_MAX_FILES}`;
                        break;
                    }
                    if (totalSize + byteLength > budget.maxSize) {
                        errorMsg = `إجمالي حجم المرفقات يتجاوز الحد الأقصى المسموح به وهو ${formatByteSize(_MAX_TOTAL_SIZE)}`;
                        break;
                    }

                    const relPath = path ? `${path}/${child.name}` : child.name;
                    const normPath = normalizeAttachmentPath(relPath);
                    files[normPath] = fileContent;
                    totalSize += byteLength;
                    fileCount += 1;
                } catch (err) {
                    // skip unreadable files
                }
            }
        }
    }

    try {
        await readDir(dirEntry, basePath);
    } catch (err) {
        errorMsg = err.message;
    }

    if (errorMsg) {
        return { files: Object.create(null), fileCount: 0, byteSize: 0, error: errorMsg };
    }
    return { files, fileCount, byteSize };
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
    if (!container) return;
    if (state.attachments.length === 0) {
        container.classList.add("hidden");
        container.innerHTML = "";
        return;
    }
    container.classList.remove("hidden");
    container.innerHTML = ""; // Clear first

    state.attachments.forEach((att, i) => {
        const pres = getAttachmentPresentation(att.name, att.isFolder);
        const pill = document.createElement("div");
        pill.className = `attached-file ${pres.className}`;
        pill.title = att.name;

        // Icon
        const iconSpan = document.createElement("span");
        iconSpan.className = "attach-icon";
        iconSpan.textContent = pres.icon;
        pill.appendChild(iconSpan);

        // Name
        const nameSpan = document.createElement("span");
        nameSpan.className = "attach-name";
        nameSpan.textContent = att.name.split("/").pop(); // Show basename for clean look
        pill.appendChild(nameSpan);

        // Meta
        const metaSpan = document.createElement("span");
        metaSpan.className = "attach-meta";
        if (att.isFolder) {
            metaSpan.textContent = `(${att.fileCount} ملف، ${formatByteSize(att.byteSize)})`;
        } else {
            metaSpan.textContent = `(${formatByteSize(att.byteSize)})`;
        }
        pill.appendChild(metaSpan);

        // Remove Button
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "remove-attach";
        removeBtn.textContent = "×";
        removeBtn.title = "إزالة المرفق";
        removeBtn.setAttribute("aria-label", `إزالة ${att.name}`);
        removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            removeAttachment(i);
        });
        pill.appendChild(removeBtn);

        // Click handler to focus path in tree/editor
        pill.addEventListener("click", () => {
            if (att.isFolder) {
                focusPathInTree(att.name);
            } else {
                openFile(att.name);
                focusPathInTree(att.name);
            }
        });

        container.appendChild(pill);
    });
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
        statusEl.textContent = durationMs ? `${(durationMs/1000).toFixed(1)}s` : "تم";
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

// ── Path Decision Card (v3.9) ──

function showPathDetectedOptions(request_id, path) {
    const container = document.getElementById("chat-messages");
    const card = document.createElement("div");
    card.className = "path-decision-card";
    card.setAttribute("data-request-id", request_id);

    // 1. Header
    const header = document.createElement("div");
    header.className = "path-decision-header";
    header.textContent = "📂 مسار خارجي مكتشف";
    card.appendChild(header);

    // 2. Description
    const desc1 = document.createElement("div");
    desc1.className = "path-decision-desc";
    desc1.textContent = "تم العثور على مسار مجلد خارج المشروع الحالي في رسالتك:";
    card.appendChild(desc1);

    // 3. Path Display Box
    const pathBox = document.createElement("div");
    pathBox.className = "path-decision-path";
    pathBox.setAttribute("dir", "ltr");

    const pathSpan = document.createElement("span");
    pathSpan.textContent = path;
    pathBox.appendChild(pathSpan);

    const copyBtn = document.createElement("button");
    copyBtn.className = "path-copy-btn";
    copyBtn.title = "نسخ المسار";
    copyBtn.textContent = "📋";
    copyBtn.type = "button";
    copyBtn.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(path);
            toast("تم نسخ المسار بنجاح", "success");
        } catch (err) {
            toast("فشل نسخ المسار", "error");
        }
    });
    pathBox.appendChild(copyBtn);
    card.appendChild(pathBox);

    // 4. Description 2
    const desc2 = document.createElement("div");
    desc2.className = "path-decision-desc";
    desc2.textContent = "اختر طريقة التعامل مع هذا المجلد لمواصلة طلبك:";
    card.appendChild(desc2);

    // 5. Actions Container
    const actionsContainer = document.createElement("div");
    actionsContainer.className = "path-decision-actions";

    // Primary: Switch Project
    const btnSwitch = document.createElement("button");
    btnSwitch.className = "path-decision-btn path-decision-btn--primary";
    btnSwitch.textContent = "📂 فتح كمشروع";
    btnSwitch.type = "button";
    btnSwitch.addEventListener("click", () => {
        sendPathAction(request_id, "switch", btnSwitch);
    });
    actionsContainer.appendChild(btnSwitch);

    // Secondary: Attach as Context
    const btnAttach = document.createElement("button");
    btnAttach.className = "path-decision-btn path-decision-btn--secondary";
    btnAttach.textContent = "📎 استخدامه كسياق";
    btnAttach.type = "button";
    btnAttach.addEventListener("click", () => {
        sendPathAction(request_id, "attach", btnAttach);
    });
    actionsContainer.appendChild(btnAttach);

    // Ghost: Ignore & Continue
    const btnIgnore = document.createElement("button");
    btnIgnore.className = "path-decision-btn path-decision-btn--ghost";
    btnIgnore.textContent = "اعتباره نصاً فقط";
    btnIgnore.type = "button";
    btnIgnore.addEventListener("click", () => {
        sendPathAction(request_id, "continue", btnIgnore);
    });
    actionsContainer.appendChild(btnIgnore);

    card.appendChild(actionsContainer);
    container.appendChild(card);
    container.scrollTop = container.scrollHeight;
    
    state.streaming = false;
    document.getElementById("send-btn").disabled = false;
}

function sendPathAction(request_id, action, btn) {
    // 1. فحص الاتصال أولاً
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        toast("❌ فشل الإرسال: لا يوجد اتصال نشط بالسيرفر!", "error");
        return;
    }

    const card = btn.closest(".path-decision-card");
    const btnGroup = card.querySelector(".path-decision-actions");
    
    // تعطيل الأزرار لمنع النقرات المتكررة
    btnGroup.querySelectorAll("button").forEach(b => {
        b.disabled = true;
    });
    btnGroup.style.opacity = "0.5";
    btnGroup.style.pointerEvents = "none";

    // إظهار مؤشر التحميل
    btn.setAttribute("data-original-text", btn.textContent);
    btn.textContent = "⏳ جاري تنفيذ الإجراء...";

    try {
        state.ws.send(JSON.stringify({
            type: "confirm_path_action",
            request_id: request_id,
            action: action
        }));
    } catch (err) {
        toast("❌ فشل في إرسال الطلب: " + err.message, "error");
        btnGroup.querySelectorAll("button").forEach(b => {
            b.disabled = false;
        });
        btnGroup.style.opacity = "1";
        btnGroup.style.pointerEvents = "auto";
        btn.textContent = btn.getAttribute("data-original-text") || btn.textContent;
    }
}

function handleConfirmPathFailed(request_id, error) {
    const card = document.querySelector(`.path-decision-card[data-request-id="${request_id}"]`);
    if (card) {
        const btnGroup = card.querySelector(".path-decision-actions");
        if (btnGroup) {
            btnGroup.querySelectorAll("button").forEach(b => {
                b.disabled = false;
                const orig = b.getAttribute("data-original-text");
                if (orig) {
                    b.textContent = orig;
                    b.removeAttribute("data-original-text");
                }
            });
            btnGroup.style.opacity = "1";
            btnGroup.style.pointerEvents = "auto";
        }
    }
    toast(`❌ فشل معالجة الإجراء: ${error}`, "error");
}

function handleSendBtnClick() {
    if (state.streaming) {
        stopGeneration();
    } else {
        sendMessage();
    }
}

function stopGeneration() {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        if (state.stopRequested) return;
        state.stopRequested = true;

        if (state.activeGenerationKind === "chain") {
            state.ws.send(JSON.stringify({ type: "chain_cancel", request_id: state.currentRequestId, reason: "User cancelled" }));
        } else {
            state.ws.send(JSON.stringify({ type: "stop", request_id: state.currentRequestId }));
        }

        toast("⏳ جاري إيقاف التوليد...", "info");

        // مؤقت أمان 6 ثوانٍ محمي بـ Request ID
        const reqIdAtStop = state.currentRequestId;
        clearStopFallbackTimer();
        state._stopFallbackTimer = setTimeout(() => {
            if (state.streaming && state.currentRequestId === reqIdAtStop) {
                resetStreamingUI();
                toast("⚠️ لم يصل تأكيد الإيقاف من السيرفر — تم استعادة الواجهة محلياً", "warning");
            }
        }, 6000);
    } else {
        resetStreamingUI();
    }
}

function resetStreamingUI() {
    clearStopFallbackTimer();
    state.streaming = false;
    state.currentRequestId = null;
    state.activeGenerationKind = null;
    state.stopRequested = false;
    updateSendButtonState();
    
    // إنهاء الرسالة الجزئية الموجودة بدلاً من تركها معلقة
    if (typeof currentStreamMsg !== 'undefined' && currentStreamMsg) {
        finalizeStreamMessage();
    }
}

function clearStopFallbackTimer() {
    if (state._stopFallbackTimer) {
        clearTimeout(state._stopFallbackTimer);
        state._stopFallbackTimer = null;
    }
}

function updateSendButtonState() {
    const btn = document.getElementById("send-btn");
    if (!btn) return;
    if (state.streaming) {
        btn.textContent = "■";
        btn.classList.add("stop-mode");
        btn.title = "إيقاف التوليد";
    } else {
        btn.textContent = "▶";
        btn.classList.remove("stop-mode");
        btn.title = "إرسال";
    }
}

function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    // Fallback using crypto.getRandomValues
    const array = new Uint32Array(4);
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
        crypto.getRandomValues(array);
    } else {
        for (let i = 0; i < 4; i++) array[i] = Math.floor(Math.random() * 0x100000000);
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (array[0] & 0xf);
        array[0] = array[0] >> 4;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function getUtf8ByteLength(content) {
    if (typeof content !== 'string') return 0;
    return new TextEncoder().encode(content).byteLength;
}

function formatByteSize(byteSize) {
    if (byteSize < 1024) return `${byteSize} B`;
    return `${(byteSize / 1024).toFixed(1)} KB`;
}

function normalizeAttachmentPath(path) {
    if (typeof path !== 'string') return "";
    let normalized = path.replace(/\\/g, '/');
    normalized = normalized.normalize("NFC");
    normalized = normalized.replace(/\/+/g, '/');
    normalized = normalized.trim();
    if (normalized.startsWith('/')) {
        normalized = normalized.slice(1);
    }
    if (normalized.endsWith('/')) {
        normalized = normalized.slice(0, -1);
    }
    if (/^[A-Za-z]:/i.test(normalized) || normalized.startsWith('/') || normalized.includes('\0')) {
        throw new Error(`⚠️ مسار غير صالح أو مطلق: ${path}`);
    }
    const segments = normalized.split('/');
    for (const segment of segments) {
        if (segment === '.' || segment === '..') {
            throw new Error(`⚠️ مسار غير آمن (يحتوي على .. أو .): ${path}`);
        }
    }
    return normalized;
}

function normalizeAttachmentName(name) {
    try {
        return normalizeAttachmentPath(name);
    } catch {
        return "";
    }
}

function getAttachmentCollisionKey(path) {
    return normalizeAttachmentPath(path).toLowerCase();
}

function getAttachmentTotals(attachments) {
    let fileCount = 0;
    let byteSize = 0;
    attachments.forEach(a => {
        if (a.isFolder) {
            const folderFiles = a.files || {};
            fileCount += Object.keys(folderFiles).length;
            for (const content of Object.values(folderFiles)) {
                byteSize += getUtf8ByteLength(content);
            }
        } else {
            fileCount += 1;
            byteSize += getUtf8ByteLength(a.content || "");
        }
    });
    return { fileCount, byteSize };
}

function getRemainingAttachmentBudget() {
    const totals = getAttachmentTotals(state.attachments);
    return {
        maxFiles: _MAX_FILES - totals.fileCount,
        maxSize: _MAX_TOTAL_SIZE - totals.byteSize
    };
}


function getAttachmentExtension(name) {
    const normalized = normalizeAttachmentName(name);
    const basename = normalized.split('/').pop() || "";
    if (basename.startsWith('.') && basename.split('.').length === 2) {
        return "";
    }
    const parts = basename.split('.');
    if (parts.length < 2) return "";
    return parts.pop().toLowerCase();
}

function getAttachmentPresentation(name, isFolder) {
    if (isFolder) {
        return { icon: "📂", className: "folder-attach" };
    }
    const ext = getAttachmentExtension(name);
    switch (ext) {
        case 'py': return { icon: "🐍", className: "py-attach" };
        case 'js':
        case 'jsx':
        case 'mjs':
        case 'cjs': return { icon: "⚡", className: "js-attach" };
        case 'ts':
        case 'tsx': return { icon: "💠", className: "ts-attach" };
        case 'html':
        case 'htm': return { icon: "🌐", className: "html-attach" };
        case 'css':
        case 'scss':
        case 'sass':
        case 'less': return { icon: "🎨", className: "css-attach" };
        case 'md': return { icon: "📝", className: "md-attach" };
        case 'json':
        case 'yaml':
        case 'yml':
        case 'toml': return { icon: "⚙️", className: "data-attach" };
        case 'sh':
        case 'bat':
        case 'ps1':
        case 'cmd': return { icon: "🖥️", className: "shell-attach" };
        default: return { icon: "📄", className: "generic-attach" };
    }
}

function validateStandaloneAttachment(name, content) {
    let normPath;
    try {
        normPath = normalizeAttachmentPath(name);
    } catch (err) {
        toast(err.message, "error");
        return false;
    }

    if (typeof content !== 'string') {
        toast("⚠️ محتوى الملف غير صالح", "error");
        return false;
    }

    const collisionKey = getAttachmentCollisionKey(normPath);

    // 1. منع الملفات المكررة والتعارض مع المجلدات
    for (const a of state.attachments) {
        if (a.isFolder) {
            const folderFiles = a.files || {};
            for (const relPath of Object.keys(folderFiles)) {
                const fullPath = `${a.name}/${relPath}`;
                if (getAttachmentCollisionKey(fullPath) === collisionKey) {
                    toast(`⚠️ تعارض: الملف ${normPath} يتعارض مع ملف داخل المجلد ${a.name}`, "warning");
                    return false;
                }
            }
            if (getAttachmentCollisionKey(a.name) === collisionKey) {
                toast(`⚠️ تعارض هيكلي: الملف ${normPath} يتعارض مع اسم مجلد مرفق`, "warning");
                return false;
            }
        } else {
            if (getAttachmentCollisionKey(a.name) === collisionKey) {
                toast(`⚠️ الملف ${normPath} مرفق بالفعل`, "warning");
                return false;
            }
        }
    }

    // 2. التحقق من حجم الملف الفردي
    const byteSize = getUtf8ByteLength(content);
    if (byteSize > _MAX_FILE_SIZE) {
        toast(`⚠️ ${normPath} يتجاوز الحد الأقصى للملف الواحد (${formatByteSize(byteSize)} > ${formatByteSize(_MAX_FILE_SIZE)})`, "error");
        return false;
    }

    // 3. التحقق التراكمي الإجمالي
    const totals = getAttachmentTotals(state.attachments);
    const newCount = totals.fileCount + 1;
    const newSize = totals.byteSize + byteSize;

    if (newCount > _MAX_FILES) {
        toast(`⚠️ لا يمكن إرفاق أكثر من ${_MAX_FILES} ملف إجمالاً`, "error");
        return false;
    }
    if (newSize > _MAX_TOTAL_SIZE) {
        toast(`⚠️ إجمالي حجم الملفات يتجاوز الحد الأقصى (${formatByteSize(_MAX_TOTAL_SIZE)})`, "error");
        return false;
    }

    return true;
}

function validateFolderAttachment(name, files) {
    let normalizedFolderName;
    try {
        normalizedFolderName = normalizeAttachmentPath(name);
    } catch (err) {
        toast(err.message, "error");
        return false;
    }

    if (!files || typeof files !== 'object' || Object.keys(files).length === 0) {
        toast("⚠️ المجلد فارغ أو غير صالح", "error");
        return false;
    }

    const folderCollisionKey = getAttachmentCollisionKey(normalizedFolderName);

    // منع المجلدات المكررة بنفس الاسم المعياري
    if (state.attachments.some(a => a.isFolder && getAttachmentCollisionKey(a.name) === folderCollisionKey)) {
        toast(`⚠️ المجلد ${normalizedFolderName} مرفق بالفعل`, "warning");
        return false;
    }

    const fileList = Object.keys(files);
    let folderSize = 0;

    for (const relPath of fileList) {
        let normRelPath;
        try {
            normRelPath = normalizeAttachmentPath(relPath);
        } catch (err) {
            toast(err.message, "error");
            return false;
        }

        const fullPath = `${normalizedFolderName}/${normRelPath}`;
        const newCollisionKey = getAttachmentCollisionKey(fullPath);

        // التحقق من تعارض مسارات الملفات داخل المجلد الجديد مع الملفات المرفقة حالياً
        for (const a of state.attachments) {
            if (a.isFolder) {
                const existingFolderKey = getAttachmentCollisionKey(a.name);
                if (existingFolderKey === folderCollisionKey) {
                    toast(`⚠️ تعارض هيكلي مع المجلد المرفق ${a.name}`, "error");
                    return false;
                }

                for (const existingRelPath of Object.keys(a.files || {})) {
                    const existingFullPath = `${a.name}/${existingRelPath}`;
                    if (getAttachmentCollisionKey(existingFullPath) === newCollisionKey) {
                        toast(`⚠️ تعارض مسارات: الملف ${fullPath} مكرر عبر المرفقات`, "error");
                        return false;
                    }
                }
            } else {
                if (getAttachmentCollisionKey(a.name) === newCollisionKey) {
                    toast(`⚠️ تعارض مسارات: الملف ${fullPath} يتعارض مع ملف منفرد مرفق`, "error");
                    return false;
                }
                if (getAttachmentCollisionKey(a.name) === folderCollisionKey) {
                    toast(`⚠️ تعارض هيكلي: اسم المجلد ${normalizedFolderName} يتعارض مع ملف منفرد مرفق`, "error");
                    return false;
                }
            }
        }

        const content = files[relPath];
        if (typeof content !== 'string') {
            toast(`⚠️ محتوى الملف ${relPath} غير صالح`, "error");
            return false;
        }
        const byteSize = getUtf8ByteLength(content);
        if (byteSize > _MAX_FILE_SIZE) {
            toast(`⚠️ الملف ${relPath} يتجاوز الحد الأقصى للملف الواحد (${formatByteSize(byteSize)} > ${formatByteSize(_MAX_FILE_SIZE)})`, "error");
            return false;
        }
        folderSize += byteSize;
    }

    // التحقق التراكمي الإجمالي
    const totals = getAttachmentTotals(state.attachments);
    const newCount = totals.fileCount + fileList.length;
    const newSize = totals.byteSize + folderSize;

    if (newCount > _MAX_FILES) {
        toast(`⚠️ المجلد الجديد مع المرفقات الحالية يتجاوز الحد الأقصى للملفات (${newCount} > ${_MAX_FILES})`, "error");
        return false;
    }
    if (newSize > _MAX_TOTAL_SIZE) {
        toast(`⚠️ إجمالي حجم الملفات مع المجلد الجديد يتجاوز الحد الأقصى (${formatByteSize(newSize)} > ${formatByteSize(_MAX_TOTAL_SIZE)})`, "error");
        return false;
    }

    return true;
}

function addStandaloneAttachment(name, content) {
    if (!validateStandaloneAttachment(name, content)) return false;
    let normalizedName;
    try {
        normalizedName = normalizeAttachmentPath(name);
    } catch {
        return false;
    }
    const byteSize = getUtf8ByteLength(content);
    state.attachments.push({
        name: normalizedName,
        content: content,
        isFolder: false,
        byteSize: byteSize
    });
    renderAttachments();
    toast(`📎 تم إرفاق: ${normalizedName}`, "info");
    return true;
}

function setFolderAttachment(name, files) {
    if (!validateFolderAttachment(name, files)) return false;
    let normalizedName;
    try {
        normalizedName = normalizeAttachmentPath(name);
    } catch {
        return false;
    }
    const fileCount = Object.keys(files).length;
    const byteSize = Object.values(files).reduce((sum, content) => sum + getUtf8ByteLength(content), 0);

    // إضافة المجلد تراكمياً بـ push
    state.attachments.push({
        name: normalizedName,
        files: files,
        isFolder: true,
        fileCount: fileCount,
        byteSize: byteSize
    });
    renderAttachments();
    toast(`📁 تم قراءة ${fileCount} ملف من المجلد ${normalizedName}`, "success");
    return true;
}

function isWebSocketOpen() {
    return state.ws && state.connected && state.ws.readyState === WebSocket.OPEN;
}

function setExplorerExpanded(expanded) {
    const arrow = document.querySelector("#explorer-title .tree-arrow");
    const title = document.getElementById("explorer-title");
    if (title) title.setAttribute("aria-expanded", expanded ? "true" : "false");
    if (arrow) arrow.textContent = expanded ? "▼" : "▶";
}

function toggleFileTree() {
    const sidebar = document.getElementById("sidebar");
    const tree = document.getElementById("file-tree");
    if (!sidebar || !tree) return;

    const mode = (typeof SIDEBAR_COLLAPSE_MODE === "string" && (SIDEBAR_COLLAPSE_MODE === "full" || SIDEBAR_COLLAPSE_MODE === "tree")) ? SIDEBAR_COLLAPSE_MODE : "full";

    if (mode === "tree") {
        const isHidden = tree.classList.toggle("hidden");
        setExplorerExpanded(!isHidden);
        sidebar.classList.remove("collapsed-full");
    } else {
        const isCollapsed = sidebar.classList.toggle("collapsed-full");
        setExplorerExpanded(!isCollapsed);
        tree.classList.remove("hidden");
    }
}

