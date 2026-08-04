// ═══════════════════════════════════════════
// app/40_panels.js — TSK-726d
// نقل حرفي من app.js (أسطر 1954–2635 قبل النقل):
// Plan Card + Delegate + Rollback/Run-History + Memory Panel
// + Diagnostics + Permissions/Settings + Status Chip + setActivityView
// العقد: نطاق عام مشترك؛ يُحمَّل بعد app.js وقبل 90 (ترتيب رقمي).
// ═══════════════════════════════════════════

// ═══════════════════════════════════════════
// Plan Card & Task Progress
// ═══════════════════════════════════════════
function showPlanCard(actions, summary) {
    state.planActions = actions;
    // TSK-619 (CP-1): حالة تفاعلية نقية — كل الخطوات تبدأ مفعّلة
    // (الافتراضي بلا لمس = تنفيذ كامل كما اليوم).
    state.planCardState = PlanCard.createState(actions);
    const container = document.getElementById("chat-messages");

    const card = document.createElement("div");
    card.className = "plan-card";

    let actionsList = actions.map((a, i) => {
        const icon = a.action === "create_file" ? "📄" : a.action === "edit_file" ? "✏️" : "⚡";
        const label = a.path || a.command || "";
        return `<div class="task-item pending"><label class="plan-step-label"><input type="checkbox" class="plan-step-toggle" data-step="${i}" checked> ${icon} ${escapeHtml(label)}</label></div>`;
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

    // TSK-619: ربط الـ checkboxes بالحالة النقية (DOM glue فقط —
    // المنطق في PlanCard). change فقط؛ لا لمس = الأعلام كلها true.
    card.querySelectorAll(".plan-step-toggle").forEach((cb) => {
        cb.addEventListener("change", () => {
            const idx = parseInt(cb.getAttribute("data-step"), 10);
            PlanCard.setEnabled(state.planCardState, idx, cb.checked);
            cb.closest(".task-item").classList.toggle("plan-step-disabled", !cb.checked);
        });
    });
}

function executePlan(btn) {
    if (!state.planActions.length) return;
    // TSK-619: أرسل المفعّل فقط — كل-الخطوات-مفعلة (الافتراضي) تعيد
    // نفس القائمة بنفس الترتيب = السلوك القديم حرفيًا.
    const enabled = state.planCardState
        ? PlanCard.enabledActions(state.planCardState)
        : state.planActions;
    if (!enabled.length) {
        toast("لا خطوات مفعّلة — فعّل خطوة واحدة على الأقل أو ألغِ الخطة", "warning");
        return;
    }
    const planCard = btn.closest(".plan-card");
    const controls = planCard.querySelector(".plan-controls");
    controls.innerHTML = '<span style="color:var(--accent);font-size:12px">⏳ جاري التنفيذ...</span>';

    state.ws.send(JSON.stringify({
        type: "execute_plan",
        actions: enabled,
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
    state.planCardState = null; // TSK-619: تصفير حالة البطاقة التفاعلية
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
        state.ws.send(JSON.stringify({
            type: "delegate_approve",
            request_id: state.currentRequestId  // ربط الموافقة بالـ request_id النشط
        }));
        document.querySelectorAll(".review-btn").forEach(b => b.disabled = true);
        toast("⏳ جاري تطبيق التعديلات...", "info");
    }
}

function delegateReject() {
    const reason = prompt("سبب الرفض (اختياري):");
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({
            type: "delegate_reject",
            request_id: state.currentRequestId,  // ربط الرفض بالـ request_id النشط
            reason: reason || ""
        }));
        document.querySelectorAll(".review-btn").forEach(b => b.disabled = true);
    }
}

function sendPathAction(reqId, action, btnEl) {
    // تعطيل جميع أزرار بطاقة القرار المحددة
    const card = btnEl ? btnEl.closest('.path-decision-card') : null;
    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);

    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        toast('⚠️ الاتصال مقطوع', 'error');
        return;
    }
    state.ws.send(JSON.stringify({
        type: 'confirm_path_action',
        request_id: reqId,
        action: action   // 'switch' | 'attach' | 'continue'
    }));
    if (action === 'switch') {
        toast('⏳ جاري تغيير مجلد العمل...', 'info');
    } else if (action === 'attach') {
        toast('📎 سيتم إرفاق المجلد كسياق', 'info');
    } else {
        if (card) card.style.opacity = '0.5';
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

// TSK-620 (CP-8): حالة سرد الجلسة — تُملأ من الأطر الحية (استهلاك
// فقط في handleWSMessage) وتُعرض فوق قائمة RunHistory عند فتح اللوحة.
const sessionNarrativeState = SessionNarrative.createState();

function renderSessionNarrative(panel) {
    let sn = panel.querySelector("#session-narrative");
    if (!sn) {
        sn = document.createElement("div");
        sn.id = "session-narrative";
        const listEl = panel.querySelector("#run-history-list");
        panel.insertBefore(sn, listEl); // قبل القائمة — القائمة بلا لمس
    }
    sn.innerHTML = SessionNarrative.renderTimelineHTML(sessionNarrativeState);
}

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
    renderSessionNarrative(panel); // TSK-620: السرد فوق القائمة
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
// T-114 (R-805): لوحة ذاكرة المشروع — DOM glue فوق وحدة MemoryPanel
// (المنطق النقي في static/js/memory_panel.js). كل الطلبات عبر أطر WS
// الإضافية memory_list/memory_edit/memory_delete — صفر endpoints جديدة.
// ═══════════════════════════════════════════
let memoryPanelEntries = [];
let memoryEditingIdx = null; // فهرس المدخلة قيد التحرير (null = لا تحرير)

function toggleMemoryPanel() {
    const panel = document.getElementById("memory-panel");
    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        return;
    }
    memoryEditingIdx = null;
    state.ws.send(JSON.stringify(MemoryPanel.listFrame()));
    panel.classList.remove("hidden");
    document.getElementById("memory-panel-list").innerHTML =
        '<div class="mp-empty">⏳ جارٍ تحميل الذاكرة...</div>';
}

function renderMemoryPanel() {
    const listEl = document.getElementById("memory-panel-list");
    listEl.innerHTML = MemoryPanel.renderPanelHTML(
        memoryPanelEntries, memoryEditingIdx);
    listEl.querySelectorAll(".mp-edit-btn").forEach(btn => {
        btn.onclick = () => {
            memoryEditingIdx = +btn.dataset.idx;
            renderMemoryPanel();
        };
    });
    listEl.querySelectorAll(".mp-delete-btn").forEach(btn => {
        btn.onclick = () => {
            const entry = memoryPanelEntries[+btn.dataset.idx];
            if (!entry) return;
            state.ws.send(JSON.stringify(MemoryPanel.deleteFrame(entry)));
        };
    });
    listEl.querySelectorAll(".mp-save-btn").forEach(btn => {
        btn.onclick = () => {
            const idx = +btn.dataset.idx;
            const entry = memoryPanelEntries[idx];
            if (!entry) return;
            const text = listEl.querySelector(
                `.mp-text-edit[data-idx="${idx}"]`).value;
            const kind = listEl.querySelector(
                `.mp-kind-select[data-idx="${idx}"]`).value;
            if (!text.trim()) {
                toast("نص المدخلة فارغ — لا تُحفظ ذاكرة بلا محتوى", "info");
                return;
            }
            state.ws.send(JSON.stringify(
                MemoryPanel.editFrame(entry, text, kind)));
        };
    });
    listEl.querySelectorAll(".mp-cancel-btn").forEach(btn => {
        btn.onclick = () => {
            memoryEditingIdx = null;
            renderMemoryPanel();
        };
    });
}

function handleMemoryListResult(frame) {
    if (frame.error) {
        document.getElementById("memory-panel-list").innerHTML =
            '<div class="mp-empty">⚠️ الذاكرة غير متاحة</div>';
        return;
    }
    memoryPanelEntries = MemoryPanel.buildEntries(frame.entries);
    memoryEditingIdx = null;
    renderMemoryPanel();
}

function handleMemoryEditResult(frame) {
    if (!frame.acknowledged) {
        toast(`❌ فشل التعديل: ${frame.error || "غير معروف"}`, "info");
        return;
    }
    MemoryPanel.applyEditResult(memoryPanelEntries, frame);
    memoryEditingIdx = null;
    renderMemoryPanel();
    toast("✅ حُفظ التعديل — provenance: المستخدم", "success");
}

function handleMemoryDeleteResult(frame) {
    if (!frame.acknowledged) {
        toast(`❌ فشل الحذف: ${frame.error || "غير معروف"}`, "info");
        return;
    }
    memoryPanelEntries = MemoryPanel.applyDeleteResult(
        memoryPanelEntries, frame);
    memoryEditingIdx = null;
    renderMemoryPanel();
    toast("🗑 حُذفت المدخلة — لن تظهر في أي سياق تالٍ", "success");
}

// ── TSK-621 (CP-5/UXF-04): لوحة الصلاحيات — قراءة فقط (glass box) ──
// المنطق النقي في permissions_panel.js؛ هنا fetch + toggle فقط —
// لا أي مسار كتابة للسياسة.
// ── TSK-721 (P1-2/D-9): تنزيل حزمة التشخيص — fetch + Blob download فقط.
// الحصيلة مُطهَّرة في الخادم (/api/diagnostics)؛ الواجهة لا تضيف شيئًا.
async function downloadDiagnostics() {
    try {
        const resp = await fetch("/api/diagnostics");
        const data = await resp.json();
        if (!data.ok) throw new Error("diagnostics failed");
        const blob = new Blob(
            [JSON.stringify(data.diagnostics, null, 2)],
            { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
        a.download = `webdev-diagnostics-${ts}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
    } catch (e) {
        alert("⚠️ تعذّر توليد حزمة التشخيص");
    }
}

async function togglePermissionsPanel() {
    const panel = document.getElementById("permissions-panel");
    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        return;
    }
    panel.classList.remove("hidden");
    const listEl = document.getElementById("permissions-panel-list");
    listEl.innerHTML =
        '<div class="pp-none">⏳ جارٍ تحميل السياسة...</div>';
    try {
        const resp = await fetch("/api/permissions");
        const data = await resp.json();
        renderPermissionsView(data.ok ? data.permissions : null);
    } catch (e) {
        listEl.innerHTML =
            '<div class="pp-none">⚠️ تعذّر تحميل السياسة</div>';
    }
}

// ── TSK-734d (القرار 6 من تسلسل D-19): وضع تحرير الأذونات ──
// المنطق النقي (النمذجة/التحليل/بناء الجسم) في permissions_panel.js؛
// هنا الـ glue فقط: زر «تحرير» يفتح النموذج، زر الحفظ الواحد يرسل
// POST /api/permissions، واللوحة تعيد الرسم من الحقيقة المعادة
// (استجابة الخادم = السياسة الفعالة الجديدة — لا افتراض تفاؤلي).
let permsLastLoaded = null;

function renderPermissionsView(perms) {
    permsLastLoaded = perms;
    const listEl = document.getElementById("permissions-panel-list");
    let html = PermissionsPanel.renderPanelHTML(perms);
    if (perms) {
        html = '<div class="pp-edit-actions"><button class="pp-edit-btn" ' +
            'data-perm-action="edit">✏️ تحرير الأذونات</button></div>' + html;
    }
    listEl.innerHTML = html;
    bindPermActions(listEl);
}

function bindPermActions(listEl) {
    listEl.querySelectorAll("[data-perm-action]").forEach((btn) => {
        btn.onclick = () => handlePermAction(btn.dataset.permAction);
    });
}

async function handlePermAction(action) {
    const listEl = document.getElementById("permissions-panel-list");
    if (action === "edit") {
        listEl.innerHTML =
            PermissionsPanel.renderEditFormHTML(permsLastLoaded);
        bindPermActions(listEl);
        return;
    }
    if (action === "cancel") {
        renderPermissionsView(permsLastLoaded);
        return;
    }
    if (action !== "save") return;
    const errEl = document.getElementById("pp-edit-error");
    const built = PermissionsPanel.buildOverridesPayload(
        document.getElementById("pp-edit-force").checked,
        document.getElementById("pp-edit-allowlist").value);
    if (!built.ok) {
        errEl.textContent = "⚠️ " + built.error;
        errEl.classList.remove("hidden");
        return;
    }
    try {
        const resp = await fetch("/api/permissions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(built.payload),
        });
        const data = await resp.json();
        if (!data.ok) {
            errEl.textContent = "⚠️ " + (data.error || "رفض الخادم التحديث");
            errEl.classList.remove("hidden");
            return;
        }
        // إعادة الرسم من الحقيقة المعادة (السياسة الفعالة الجديدة).
        renderPermissionsView(data.permissions);
        toast("💾 حُفظت الأذونات — السياسة الفعالة مطبّقة حيًّا", "success");
    } catch (e) {
        errEl.textContent = "⚠️ تعذّر الاتصال بالخادم";
        errEl.classList.remove("hidden");
    }
}

// ── TSK-722b (P1-4/D-9): لوحة الإعدادات — عرض فقط (glass box) ──
// المنطق النقي في settings_panel.js؛ هنا fetch + toggle فقط —
// لا أي مسار كتابة للإعدادات (التعديل عبر config.yaml + إعادة تشغيل).
async function toggleSettingsPanel() {
    const panel = document.getElementById("settings-panel");
    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        return;
    }
    panel.classList.remove("hidden");
    const listEl = document.getElementById("settings-panel-list");
    listEl.innerHTML =
        '<div class="pp-none">⏳ جارٍ تحميل الإعدادات...</div>';
    try {
        const resp = await fetch("/api/settings");
        const data = await resp.json();
        listEl.innerHTML = SettingsPanel.renderPanelHTML(
            data.ok ? data.settings : null);
    } catch (e) {
        listEl.innerHTML =
            '<div class="pp-none">⚠️ تعذّر تحميل الإعدادات</div>';
    }
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
    document.getElementById("memory-panel-btn").onclick = toggleMemoryPanel;
    document.getElementById("permissions-panel-btn").onclick = togglePermissionsPanel;
    document.getElementById("status-chip-label").onclick = toggleStatusChip;
    refreshCapacity();
    setInterval(refreshCapacity, CAPACITY_POLL_MS);
});

// ═══════════════════════════════════════════
// Activity Bar Navigation
// ═══════════════════════════════════════════

function setActivityView(view) {
    // تحديث حالة الأزرار
    document.querySelectorAll('.activity-btn').forEach(b => b.classList.remove('active'));

    const sidebar = document.getElementById('sidebar');
    const chatPanel = document.getElementById('chat-panel');

    if (view === 'explorer') {
        const btn = document.getElementById('act-explorer');
        if (btn) btn.classList.add('active');
        // إظهار الـ sidebar لو كان مخفياً
        if (sidebar) {
            sidebar.classList.remove('collapsed', 'collapsed-full');
        }
    } else if (view === 'chat') {
        const btn = document.getElementById('act-chat');
        if (btn) btn.classList.add('active');
    }
}
