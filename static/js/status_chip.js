/* T-066 (R-906): شريحة حالة التوجيه والسعة — منطق نقي (UMD-lite،
 * قابل للاختبار في node). الـ DOM glue في app.js فقط.
 *
 * ── مصادر البيانات (عرض قراءة فقط — صفر منطق/endpoints جديدة) ────────
 * 1. قرار التوجيه: إطار `chain_started` الموجود يحمل حقل
 *    "routing" = RoutingDecision.to_dict() (T-036):
 *    { strategy, provider_name, chain_strategy, max_steps,
 *      downgraded, downgrade_reason, complexity_score }
 *    — يصل عبر نفس محوّل الـ WS الوحيد (T-047)؛ الشريحة تستهلكه فقط.
 * 2. السعة/القواطع: GET /api/capacity الموجود منذ T-038 —
 *    CapacityReport.to_dict(): { total_available, healthy_count,
 *    estimated, providers: [{name, healthy, breaker_state
 *    (closed|open|half_open), remaining_calls, effective_calls,
 *    estimated}] } — استطلاع خامل مُخفَّض التردد.
 * 3. الميزانية: أي إطار يحمل "budget" (عرض اختياري في اللوحة الموسعة).
 *
 * ── الخنق (Throttling) ────────────────────────────────────────────────
 * noteFrame/updateCapacity يحدّثان الحالة فورًا لكن الرسم مُخنوق:
 * shouldRender يسمح برسمة كل MIN_RENDER_INTERVAL_MS على الأكثر ويعلّم
 * pending للرسم اللاحق — عاصفة أحداث لا تعني عاصفة رسومات (بند قبول
 * R-906: عدد الرسومات مقيّد تحت الدفقات).
 */
(function (global) {
    "use strict";

    var MIN_RENDER_INTERVAL_MS = 500;

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function createState() {
        return {
            routing: null,      // آخر RoutingDecision.to_dict()
            capacity: null,     // آخر CapacityReport.to_dict()
            budget: null,       // آخر حمولة budget
            expanded: false,
            _lastRenderMs: 0,
            _pending: false,
            renderCount: 0,     // للاختبارات — يزيده الغراء عند كل رسم فعلي
        };
    }

    // يلتقط ما يهم الشريحة من أي إطار WS وارد — يرجع true لو تغيّر شيء.
    function noteFrame(state, frame) {
        var changed = false;
        if (frame && frame.type === "chain_started" && frame.routing) {
            state.routing = frame.routing;
            changed = true;
        }
        if (frame && frame.budget && typeof frame.budget === "object") {
            state.budget = frame.budget;
            changed = true;
        }
        return changed;
    }

    function updateCapacity(state, capacityDict) {
        state.capacity = capacityDict || null;
        return true;
    }

    // بوابة الخنق — nowMs من الغراء (قابلة للحقن في الاختبارات).
    function shouldRender(state, nowMs) {
        if (nowMs - state._lastRenderMs >= MIN_RENDER_INTERVAL_MS) {
            state._lastRenderMs = nowMs;
            state._pending = false;
            return true;
        }
        state._pending = true;
        return false;
    }

    function hasPending(state) { return state._pending; }

    // ── مشتقات العرض ──
    function breakerSummary(capacity) {
        if (!capacity || !capacity.providers) return { open: 0, half: 0 };
        var open = 0, half = 0;
        capacity.providers.forEach(function (p) {
            if (p.breaker_state === "open") open++;
            else if (p.breaker_state === "half_open") half++;
        });
        return { open: open, half: half };
    }

    // الشريحة المطوية — سطر واحد: استراتيجية + صحة المزودين + تحذير قواطع.
    function renderChipHTML(state) {
        var parts = [];
        if (state.routing) {
            parts.push("🧭 " + escapeHtml(state.routing.strategy || "?"));
            if (state.routing.downgraded) parts.push("⬇");
        }
        if (state.capacity) {
            var total = state.capacity.providers
                ? state.capacity.providers.length : 0;
            parts.push("🔌 " + state.capacity.healthy_count + "/" + total);
            var b = breakerSummary(state.capacity);
            if (b.open) parts.push("🔴 " + b.open);
            else if (b.half) parts.push("🟡 " + b.half);
            if (state.capacity.estimated) parts.push("≈");
        }
        if (!parts.length) parts.push("📊 الحالة");
        return parts.join(" · ");
    }

    // اللوحة الموسعة — التوجيه ثم المزودون ثم الميزانية. كل القيم من
    // السجلات المهيكلة نفسها (لا اختراع نصوص حالة جديدة).
    function renderPanelHTML(state) {
        var html = "";
        if (state.routing) {
            var r = state.routing;
            html += '<div class="sc-section"><div class="sc-title">🧭 آخر قرار توجيه</div>' +
                '<div class="sc-row"><span>الاستراتيجية</span><b>' +
                escapeHtml(r.strategy || "?") + "</b></div>" +
                (r.chain_strategy
                    ? '<div class="sc-row"><span>استراتيجية السلسلة</span><b>' +
                      escapeHtml(r.chain_strategy) + "</b></div>" : "") +
                '<div class="sc-row"><span>التعقيد</span><b>' +
                Number(r.complexity_score || 0).toFixed(1) + "</b></div>" +
                (r.provider_name
                    ? '<div class="sc-row"><span>المزوّد</span><b>' +
                      escapeHtml(r.provider_name) + "</b></div>" : "") +
                (r.downgraded
                    ? '<div class="sc-row sc-warn"><span>⬇ منزَّل</span><b>' +
                      escapeHtml(r.downgrade_reason || "") + "</b></div>" : "") +
                "</div>";
        } else {
            html += '<div class="sc-section sc-dim">لا قرار توجيه بعد — ' +
                "يظهر مع أول طلب.</div>";
        }
        if (state.capacity) {
            var c = state.capacity;
            html += '<div class="sc-section"><div class="sc-title">🔌 السعة والقواطع' +
                (c.estimated ? ' <span class="sc-badge">تقديري</span>' : "") +
                "</div>" +
                '<div class="sc-row"><span>الإجمالي المتاح</span><b>' +
                c.total_available + "</b></div>";
            (c.providers || []).forEach(function (p) {
                var dot = p.breaker_state === "open" ? "🔴"
                    : p.breaker_state === "half_open" ? "🟡" : "🟢";
                html += '<div class="sc-row"><span>' + dot + " " +
                    escapeHtml(p.name) + "</span><b>" +
                    (p.breaker_state === "open"
                        ? "قاطع مفتوح"
                        : p.effective_calls + " نداء" +
                          (p.estimated ? " ≈" : "")) + "</b></div>";
            });
            html += "</div>";
        }
        if (state.budget) {
            // حقول BudgetTracker.to_dict الفعلية (chain/models.py)
            var att = state.budget.attempted_calls,
                rem = state.budget.remaining_calls;
            if (att !== undefined) {
                html += '<div class="sc-section"><div class="sc-title">💰 الميزانية</div>' +
                    '<div class="sc-row"><span>نداءات مُحاوَلة</span><b>' +
                    att + "</b></div>" +
                    (rem !== undefined
                        ? '<div class="sc-row"><span>المتبقي</span><b>' +
                          rem + "</b></div>" : "") +
                    "</div>";
            }
        }
        return html;
    }

    var api = {
        MIN_RENDER_INTERVAL_MS: MIN_RENDER_INTERVAL_MS,
        createState: createState,
        noteFrame: noteFrame,
        updateCapacity: updateCapacity,
        shouldRender: shouldRender,
        hasPending: hasPending,
        breakerSummary: breakerSummary,
        renderChipHTML: renderChipHTML,
        renderPanelHTML: renderPanelHTML,
    };

    global.StatusChip = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
