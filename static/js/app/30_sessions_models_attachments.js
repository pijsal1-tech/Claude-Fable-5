/* TSK-726c (P2-4 / FI-07 / D-10): مقطع منقول حرفيًا من app.js —
 * مجال الجلسات/النماذج/المرفقات + drag-drop (toggleSessions →
 * loadSessions/loadSession → loadModels/switchModel → initDragDrop →
 * attachments). تقسيم-تسلسلي محافظ: نطاق عمومي مشترك؛ يُحمَّل بعد
 * app.js؛ الاستدعاءات التمهيدية داخل DOMContentLoaded. لا تغيير سلوكي.
 */
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
            renderChatHistory(data.history || []);
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
            if (!data.ok || !data.current) return;
            const label = document.getElementById("current-model-label");
            const btn = document.getElementById("model-btn");
            const provBadge = document.getElementById("provider-name");

            const currModel = data.current.model || "Default";
            const currProv = data.current.provider || "";

            if (label) label.textContent = currModel;
            if (btn) btn.title = `المزود: ${currProv} | النموذج: ${currModel}`;
            if (provBadge && currProv) {
                provBadge.textContent = currProv;
                provBadge.dataset.userSwitched = "true";
            }
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
                toast(`✅ تم التغيير: ${modelName}`, "success");
                const label = document.getElementById("current-model-label");
                const btn = document.getElementById("model-btn");
                const provBadge = document.getElementById("provider-name");
                if (label) label.textContent = modelName;
                if (btn) btn.title = `المزود: ${providerId} | النموذج: ${modelName}`;
                if (provBadge) {
                    provBadge.textContent = providerId;
                    provBadge.dataset.userSwitched = "true";
                }
                const dropdown = document.getElementById("model-dropdown");
                if (dropdown) dropdown.classList.add("hidden");
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
