/* TSK-725c (P2-3 / D-10): Workspace Trust — واجهة الثقة (لافتة + شارة).
 *
 * منطق نقي (UMD-lite، قابل للاختبار في node) — **لا منطق قرار هنا**:
 * القرار الوحيد يتخذه المستخدم (زرّا اللافتة) ويُخزَّن عبر
 * POST /api/trust؛ الإنفاذ في الخادم (fail-closed — TSK-725a/b).
 * هذه الوحدة تُطبّع الاستجابة وتُصيّر HTML حرفيًا فقط.
 * الـ DOM/fetch glue في app.js حصرًا (سابقة status_chip/T-066).
 *
 * ── عقد العرض ─────────────────────────────────────────────────────────
 * parseTrust(data): تطبيع GET /api/trust — **fail-closed**: أي شكل غير
 *   متوقع ⇒ {trusted:false, decided:false}. decided=true عند وجود سجل
 *   قرار (trusted صراحةً أو decided_at/decided_by في الحمولة) — تتحكم
 *   في إظهار اللافتة: تظهر فقط عند «غير موثوق **ولا قرار مسجَّل**».
 * renderBanner(): سؤال + زرّان بـ data-trust-action (trust|keep) —
 *   تفويض نقر في الغراء، لا onclick مضمّن (سابقة TSK-723).
 * renderBadge(trusted): شارة حالة دائمة (موثوق/غير موثوق).
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // fail-closed: لا يرفع أبدًا؛ أي شكل غير متوقع ⇒ غير موثوق بلا قرار.
    function parseTrust(data) {
        var ok = !!(data && data.ok === true &&
            data.trust && typeof data.trust === "object");
        var trusted = !!(ok && data.trust.trusted === true);
        var decided = !!(ok && (trusted ||
            typeof data.trust.decided_at === "string" ||
            typeof data.trust.decided_by === "string"));
        return { trusted: trusted, decided: decided };
    }

    function renderBanner() {
        return '<span class="trust-banner-icon">🛡️</span>' +
            '<span class="trust-banner-question">هل تثق بهذا المجلد؟ ' +
            'الأوامر تتطلب موافقة يدوية لكل أمر حتى تقرر ' +
            '(fail-closed).</span>' +
            '<button class="trust-btn trust-btn-yes" type="button" ' +
            'data-trust-action="trust">أثق بهذا المجلد</button>' +
            '<button class="trust-btn trust-btn-no" type="button" ' +
            'data-trust-action="keep">أبقِه غير موثوق</button>';
    }

    function renderBadge(trusted) {
        if (trusted === true) {
            return '<span class="trust-badge trust-badge-trusted" ' +
                'title="مجلد موثوق — قرار مستخدم صريح">✓ موثوق</span>';
        }
        return '<span class="trust-badge trust-badge-untrusted" ' +
            'title="غير موثوق — كل أمر يتطلب موافقة يدوية ' +
            '(fail-closed)">⛔ غير موثوق</span>';
    }

    var api = {
        parseTrust: parseTrust,
        renderBanner: renderBanner,
        renderBadge: renderBadge,
        escapeHtml: escapeHtml,
    };
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    } else {
        global.TrustBanner = api;
    }
})(typeof globalThis !== "undefined" ? globalThis : this);
