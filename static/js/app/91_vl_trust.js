/* TSK-726a (P2-4 / FI-07 / D-10): مقطع منقول حرفيًا من ذيل app.js —
 * تقسيم-تسلسلي محافظ (نطاق عمومي مشترك؛ يُحمَّل **بعد** app.js
 * بالترتيب الرقمي — المكافئ الحرفي للتسلسل الأصلي). لا تغيير سلوكي.
 */
// ═══════════════════════════════════════════
// TSK-724 (P2-2/D-10 — FI-09): نافذة عرض افتراضية — DOM glue فقط.
// المنطق النقي في static/js/virtual_list.js (VirtualList.computeWindow).
// قيود حافظة للسلوك: البث (currentStreamMsg) وكروت التيرمنال والرسائل
// الحية تُلحق appendChild كما هي — تقع بعد spacer-bottom فتبقى آخر
// القائمة؛ التمرير التلقائي لأسفل محفوظ؛ النافذة تُفعَّل فقط عند تحميل
// تاريخ ≥ VL_THRESHOLD (الجلسات القصيرة = المسار القديم حرفيًا).
// ═══════════════════════════════════════════

const VL_THRESHOLD = 150;   // أقل عدد رسائل يفعّل النافذة
const VL_OVERSCAN = 8;      // عناصر إضافية قبل/بعد المنفذ
const VL_EST_HEIGHT = 120;  // تقدير أولي للارتفاع (يُقاس ويُصحَّح)
let vlMessages = [];
let vlHeights = [];
let vlActive = false;
let vlPending = false;

function vlDeactivate() {
    vlActive = false;
    vlMessages = [];
    vlHeights = [];
}

/** نقطة الدخول الموحدة لرسم تاريخ محادثة كامل (تحميل/تبديل جلسة). */
function renderChatHistory(history) {
    const container = document.getElementById("chat-messages");
    container.innerHTML = "";
    vlDeactivate();
    if (!history || history.length < VL_THRESHOLD) {
        // المسار القديم كما هو — جلسات قصيرة
        (history || []).forEach(msg => addChatMessage(msg.role, msg.content));
        return;
    }
    vlMessages = history.slice();
    vlHeights = vlMessages.map(() => VL_EST_HEIGHT);
    vlActive = true;
    const top = document.createElement("div");
    top.id = "vl-spacer-top";
    const bottom = document.createElement("div");
    bottom.id = "vl-spacer-bottom";
    container.appendChild(top);
    container.appendChild(bottom);
    // سلوك التحميل الحالي: ابدأ من آخر القائمة
    top.style.height = VirtualList.totalHeight(vlHeights) + "px";
    container.scrollTop = container.scrollHeight;
    vlRender();
    container.scrollTop = container.scrollHeight;
    vlRender();
}

/** إعادة رسم ما بين الـ spacers فقط حسب computeWindow. */
function vlRender() {
    if (!vlActive) return;
    const container = document.getElementById("chat-messages");
    const top = document.getElementById("vl-spacer-top");
    const bottom = document.getElementById("vl-spacer-bottom");
    if (!container || !top || !bottom) {
        // الحاوية مُسحت (clearChat/newSession) — تعطيل آمن
        vlDeactivate();
        return;
    }
    const w = VirtualList.computeWindow(
        container.scrollTop, container.clientHeight, vlHeights, VL_OVERSCAN);
    let node = top.nextSibling;
    while (node && node !== bottom) {
        const next = node.nextSibling;
        container.removeChild(node);
        node = next;
    }
    const frag = document.createDocumentFragment();
    const els = [];
    for (let i = w.start; i < w.end; i++) {
        const el = buildChatMessage(vlMessages[i].role, vlMessages[i].content);
        el.dataset.vlIndex = i;
        els.push(el);
        frag.appendChild(el);
    }
    container.insertBefore(frag, bottom);
    top.style.height = w.padTop + "px";
    bottom.style.height = w.padBottom + "px";
    // قياس الارتفاعات الفعلية وتصحيح التقدير تدريجيًا
    for (const el of els) {
        const h = el.offsetHeight;
        if (h > 0) vlHeights[parseInt(el.dataset.vlIndex, 10)] = h;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const chatEl = document.getElementById("chat-messages");
    if (!chatEl) return;
    chatEl.addEventListener("scroll", () => {
        if (!vlActive || vlPending) return;
        vlPending = true;
        requestAnimationFrame(() => {
            vlPending = false;
            vlRender();
        });
    });
});


// ═══════════════════════════════════════════
// Workspace Trust glue — TSK-725c (P2-3/D-10)
// غراء fetch/DOM فقط — لا منطق قرار في المتصفح: العرض من
// TrustBanner (وحدة نقية)، القرار للمستخدم (زرّا اللافتة)،
// الإنفاذ في الخادم (fail-closed — TSK-725a/b).
// ═══════════════════════════════════════════
function applyTrustUI(parsed) {
    const badge = document.getElementById("trust-badge");
    const banner = document.getElementById("trust-banner");
    if (badge) badge.innerHTML = TrustBanner.renderBadge(parsed.trusted);
    if (!banner) return;
    // اللافتة فقط عند «غير موثوق ولا قرار مسجَّل» (عقد parseTrust)
    if (!parsed.trusted && !parsed.decided) {
        banner.innerHTML = TrustBanner.renderBanner();
        banner.classList.remove("hidden");
    } else {
        banner.classList.add("hidden");
        banner.innerHTML = "";
    }
}

function refreshTrustUI() {
    fetch("/api/trust")
        .then(r => r.json())
        .then(data => applyTrustUI(TrustBanner.parseTrust(data)))
        .catch(() => applyTrustUI({ trusted: false, decided: false }));
}

function decideTrust(trusted) {
    fetch("/api/trust", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trusted: trusted }),
    })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                toast(trusted ? "✓ تم توثيق المجلد" :
                    "⛔ بقي المجلد غير موثوق — كل أمر يتطلب موافقة",
                    trusted ? "success" : "error");
            } else {
                toast(data.error || "فشل تخزين قرار الثقة", "error");
            }
            refreshTrustUI();
        })
        .catch(() => refreshTrustUI());
}

document.addEventListener("DOMContentLoaded", () => {
    const banner = document.getElementById("trust-banner");
    if (banner) {
        // تفويض نقر عبر data-trust-action — لا onclick مضمّن (سابقة 723)
        banner.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-trust-action]");
            if (!btn) return;
            decideTrust(btn.dataset.trustAction === "trust");
        });
    }
    refreshTrustUI();
});

