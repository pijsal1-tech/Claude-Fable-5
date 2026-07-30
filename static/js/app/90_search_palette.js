/* TSK-726a (P2-4 / FI-07 / D-10): مقطع منقول حرفيًا من ذيل app.js —
 * تقسيم-تسلسلي محافظ (نطاق عمومي مشترك؛ يُحمَّل **بعد** app.js
 * بالترتيب الرقمي — المكافئ الحرفي للتسلسل الأصلي). لا تغيير سلوكي.
 */
// ═══════════════════════════════════════════
// Global Project Search (Ctrl+K Quick Open)
// ═══════════════════════════════════════════
let quickOpenSearchTimer = null;
let quickOpenSelectedIndex = 0;

function openQuickOpenModal() {
    const modal = document.getElementById("quick-open-modal");
    const input = document.getElementById("quick-open-input");
    if (!modal || !input) return;
    modal.classList.remove("hidden");
    input.value = "";
    input.focus();
    quickOpenSelectedIndex = 0;
    performQuickOpenSearch("");
}

function closeQuickOpenModal() {
    const modal = document.getElementById("quick-open-modal");
    if (modal) modal.classList.add("hidden");
}

function closeQuickOpenOnOutside(e) {
    if (e.target.id === "quick-open-modal") {
        closeQuickOpenModal();
    }
}

function performQuickOpenSearch(query) {
    const resultsContainer = document.getElementById("quick-open-results");
    if (!resultsContainer) return;

    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => {
            if (!data.ok || !data.results) {
                resultsContainer.innerHTML = '<div class="quick-open-empty">لا توجد نتائج</div>';
                return;
            }
            if (data.results.length === 0) {
                resultsContainer.innerHTML = '<div class="quick-open-empty">لا توجد نتائج مطابقة</div>';
                return;
            }

            resultsContainer.innerHTML = data.results.map((res, idx) => {
                const isSelected = idx === quickOpenSelectedIndex ? "selected" : "";
                const icon = fileIconHTML(res.path);
                const snippet = res.type === "content" 
                    ? `<div class="quick-open-snippet">Line ${res.line}: <code>${escapeHTML(res.snippet)}</code></div>` 
                    : "";
                return `
                    <div class="quick-open-item ${isSelected}" data-index="${idx}" onclick="selectQuickOpenResult('${res.path}', ${res.line || 0})">
                        ${icon}
                        <div class="quick-open-info">
                            <span class="quick-open-name">${res.name || res.path}</span>
                            <span class="quick-open-path">${res.path}</span>
                            ${snippet}
                        </div>
                    </div>
                `;
            }).join("");
        })
        .catch(() => {
            resultsContainer.innerHTML = '<div class="quick-open-empty">خطأ أثناء البحث</div>';
        });
}

function selectQuickOpenResult(path, line) {
    closeQuickOpenModal();
    openFile(path);
}

function escapeHTML(str) {
    return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Shortcut listener for Ctrl+K
document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openQuickOpenModal();
    } else if (e.key === "Escape") {
        closeQuickOpenModal();
    }
});

// Input & Keyboard navigation inside Quick Open
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("quick-open-input");
    if (input) {
        input.addEventListener("input", (e) => {
            clearTimeout(quickOpenSearchTimer);
            quickOpenSearchTimer = setTimeout(() => {
                quickOpenSelectedIndex = 0;
                performQuickOpenSearch(e.target.value);
            }, 150);
        });

        input.addEventListener("keydown", (e) => {
            const items = document.querySelectorAll(".quick-open-item");
            if (items.length === 0) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                quickOpenSelectedIndex = (quickOpenSelectedIndex + 1) % items.length;
                updateQuickOpenSelection(items);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                quickOpenSelectedIndex = (quickOpenSelectedIndex - 1 + items.length) % items.length;
                updateQuickOpenSelection(items);
            } else if (e.key === "Enter") {
                e.preventDefault();
                const activeItem = items[quickOpenSelectedIndex];
                if (activeItem) activeItem.click();
            }
        });
    }
});

function updateQuickOpenSelection(items) {
    items.forEach((item, idx) => {
        item.classList.toggle("selected", idx === quickOpenSelectedIndex);
        if (idx === quickOpenSelectedIndex) {
            item.scrollIntoView({ block: "nearest" });
        }
    });
}


// ═══════════════════════════════════════════
// TSK-723 (P2-1/D-10): Command Palette (Ctrl+Shift+P) — DOM glue فقط.
// المنطق النقي في command_palette.js؛ التنفيذ عبر lookup صريح في جدول
// أفعال UI قائمة (لا eval ولا سلاسل كود) — صفر endpoints جديدة.
// ═══════════════════════════════════════════
let cpSelectedIndex = 0;
let cpFiltered = [];

// جدول الأفعال المسموحة: action من السجل ⇒ الدالة القائمة حرفيًا.
const CP_ACTIONS = {
    openQuickOpenModal, toggleSettingsPanel, togglePermissionsPanel,
    downloadDiagnostics, toggleRunHistory, toggleMemoryPanel,
    toggleSessions, newSession, openFolder, createNewFile,
    createNewFolder, toggleThemePicker, toggleModelPicker,
    toggleStatusChip, clearChat,
};

function openCommandPalette() {
    const modal = document.getElementById("command-palette-modal");
    const input = document.getElementById("command-palette-input");
    if (!modal || !input) return;
    modal.classList.remove("hidden");
    input.value = "";
    cpSelectedIndex = 0;
    renderCommandPalette("");
    input.focus();
}

function closeCommandPalette() {
    const modal = document.getElementById("command-palette-modal");
    if (modal) modal.classList.add("hidden");
}

function closeCommandPaletteOnOutside(e) {
    if (e.target.id === "command-palette-modal") closeCommandPalette();
}

function renderCommandPalette(query) {
    const listEl = document.getElementById("command-palette-results");
    if (!listEl) return;
    cpFiltered = CommandPalette.filterCommands(query);
    if (cpSelectedIndex >= cpFiltered.length) cpSelectedIndex = 0;
    listEl.innerHTML = CommandPalette.renderListHTML(
        cpFiltered, cpSelectedIndex);
}

function executeCommandPaletteItem(cmd) {
    closeCommandPalette();
    if (!cmd) return;
    const fn = CP_ACTIONS[cmd.action];   // lookup صريح — لا eval
    if (typeof fn === "function") fn();
}

document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey &&
        e.key.toLowerCase() === "p") {
        e.preventDefault();
        openCommandPalette();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("command-palette-input");
    const listEl = document.getElementById("command-palette-results");
    if (!input || !listEl) return;
    input.addEventListener("input", () => {
        cpSelectedIndex = 0;
        renderCommandPalette(input.value);
    });
    input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { closeCommandPalette(); return; }
        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (cpFiltered.length) {
                cpSelectedIndex = (cpSelectedIndex + 1) % cpFiltered.length;
                renderCommandPalette(input.value);
            }
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (cpFiltered.length) {
                cpSelectedIndex = (cpSelectedIndex - 1 + cpFiltered.length)
                    % cpFiltered.length;
                renderCommandPalette(input.value);
            }
        } else if (e.key === "Enter") {
            e.preventDefault();
            executeCommandPaletteItem(cpFiltered[cpSelectedIndex]);
        }
    });
    // تفويض النقر: data-cmd-id من الوحدة النقية ⇒ تنفيذ عبر الجدول.
    listEl.addEventListener("click", (e) => {
        const item = e.target.closest("[data-cmd-id]");
        if (!item) return;
        const cmd = cpFiltered[parseInt(item.dataset.index, 10)];
        executeCommandPaletteItem(cmd);
    });
});
