/* TSK-402 (NF-11): backoff+jitter لإعادة اتصال WS + حماية onmessage.
 *
 * المشكلة (NEW_FINDINGS.md#NF-11 — C4/S3):
 *   1. `setTimeout(initWebSocket, 3000)` ثابت دائمًا — لا backoff ولا
 *      jitter ولا سقف → عند سقوط الخادم كل التبويبات تقصفه بإيقاع
 *      متزامن كل 3 ثوانٍ (thundering herd).
 *   2. `JSON.parse(event.data)` بلا try/catch — إطار مشوّه واحد يرمي
 *      استثناءً يقتل معالجة الرسالة كلها.
 *
 * الحل (وحدة UMD-lite نقية قابلة للاختبار في node — نفس نمط
 * stream_render.js/TSK-401 و code_highlight.js/T-064):
 *   - createBackoff(): مولّد فواصل أُسّية بسقف + jitter نسبي —
 *     next() يعيد الفاصل التالي ويزيد العدّاد، reset() عند نجاح
 *     الاتصال. random قابل للحقن للاختبار الحتمي.
 *   - safeParseFrame(): JSON.parse محمي — إطار مشوّه أو غير كائن →
 *     log عبر دالة محقونة + إرجاع null (تجاهل بلا استثناء).
 *
 * صفر DOM/ألوان هنا — منطق نقي فقط.
 */
(function (global) {
    "use strict";

    // فواصل افتراضية: 1s → 2s → 4s → 8s → 16s → 30s (سقف) + jitter ±30%.
    var BASE_DELAY_MS = 1000;
    var MAX_DELAY_MS = 30000;
    var FACTOR = 2;
    var JITTER_RATIO = 0.3;

    function createBackoff(opts) {
        opts = opts || {};
        var base = (opts.base == null) ? BASE_DELAY_MS : opts.base;
        var max = (opts.max == null) ? MAX_DELAY_MS : opts.max;
        var factor = (opts.factor == null) ? FACTOR : opts.factor;
        var jitterRatio = (opts.jitterRatio == null)
            ? JITTER_RATIO : opts.jitterRatio;
        var random = opts.random || Math.random;

        var attempt = 0;

        return {
            /** الفاصل التالي (ms): أُسّي بسقف + jitter نسبي [0..ratio). */
            next: function () {
                var pure = Math.min(base * Math.pow(factor, attempt), max);
                attempt += 1;
                var jitter = pure * jitterRatio * random();
                return Math.round(pure + jitter);
            },
            /** صفّر العدّاد — يُستدعى عند نجاح الاتصال (onopen). */
            reset: function () { attempt = 0; },
            /** عدد المحاولات منذ آخر reset (للاختبار/التشخيص). */
            attempts: function () { return attempt; },
        };
    }

    /**
     * JSON.parse محمي لإطار WS: يعيد الكائن أو null (log + تجاهل).
     * أي شيء ليس كائن JSON (مصفوفة/رقم/نص/null) يُعد إطارًا مشوّهًا
     * أيضًا — handleWSMessage يتوقع `data.type`.
     */
    function safeParseFrame(raw, log) {
        log = log || function () {};
        var data;
        try {
            data = JSON.parse(raw);
        } catch (err) {
            log("WS: إطار JSON مشوّه — تم تجاهله", err);
            return null;
        }
        if (data === null || typeof data !== "object"
            || Array.isArray(data)) {
            log("WS: إطار ليس كائنًا — تم تجاهله", raw);
            return null;
        }
        return data;
    }

    var api = {
        createBackoff: createBackoff,
        safeParseFrame: safeParseFrame,
        BASE_DELAY_MS: BASE_DELAY_MS,
        MAX_DELAY_MS: MAX_DELAY_MS,
        FACTOR: FACTOR,
        JITTER_RATIO: JITTER_RATIO,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
    if (global) global.WSBackoff = api;
})(typeof window !== "undefined" ? window : globalThis);
