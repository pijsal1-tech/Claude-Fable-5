/* TSK-401 (NF-10): بث تدريجي بدل إعادة render كاملة — أدوات الـ throttle
 * والـ memo المقطعي لبث الشات.
 *
 * المشكلة: appendStreamChunk كان يعيد marked.parse + innerHTML للرد
 * **كاملًا مع كل chunk** — بث 100KB = مئات عمليات parse كاملة متتالية
 * (long tasks متكررة وتجمّد ملموس).
 *
 * الحل جزءان (كلاهما هنا كوحدة UMD-lite قابلة للاختبار في node —
 * نفس نمط code_highlight.js/T-064):
 *   1. createThrottler(): تجميع طلبات الرندر تحت rAF + حد أدنى زمني
 *      (MIN_INTERVAL_MS) — آخر طلب فقط يُنفَّذ (الرندر يقرأ الحالة
 *      الكاملة فلا يضيع شيء)، فيصير عدد الرندرات O(زمن البث) لا
 *      O(عدد الـ chunks).
 *   2. createSectionMemo(): كاش لكل مقطع (other/thinking/result/plain)
 *      بهوية السلسلة — المقاطع المغلقة تُخدم من الكاش، والمقطع المفتوح
 *      الأخير فقط هو ما يُعاد تحليله (marked.parse) — بالاتساق مع كاش
 *      الإبراز T-064 الذي يفعل المثل لبلوكات الكود.
 *
 * صفر ألوان/DOM هنا — الوحدة نقية قابلة للاختبار بلا متصفح.
 */
(function (global) {
    "use strict";

    // ~20 رندر/ثانية كحد أقصى — أقل من عتبة long-task (50ms) بهامش،
    // وأسرع من أن تلاحظه العين كتقطيع.
    var MIN_INTERVAL_MS = 50;

    function createThrottler(opts) {
        opts = opts || {};
        var schedule = opts.schedule
            || (typeof requestAnimationFrame === "function"
                ? function (cb) { return requestAnimationFrame(cb); }
                : function (cb) { return setTimeout(cb, 16); });
        var cancelSchedule = opts.cancel
            || (typeof cancelAnimationFrame === "function"
                ? function (h) { cancelAnimationFrame(h); }
                : function (h) { clearTimeout(h); });
        var now = opts.now
            || (typeof performance !== "undefined" && performance.now
                ? function () { return performance.now(); }
                : function () { return Date.now(); });
        var minInterval = (opts.minInterval == null)
            ? MIN_INTERVAL_MS : opts.minInterval;

        var handle = null;
        var pendingFn = null;
        var lastRender = -Infinity;

        function fire() {
            handle = null;
            if (!pendingFn) return;
            var t = now();
            if (t - lastRender < minInterval) {
                // مبكر — أعد الجدولة لإطار تالٍ حتى ينقضي الفاصل.
                handle = schedule(fire);
                return;
            }
            lastRender = t;
            var fn = pendingFn;
            pendingFn = null;
            fn();
        }

        return {
            /** اطلب رندر — آخر دالة فقط تُنفَّذ (تقرأ الحالة الكاملة). */
            request: function (fn) {
                pendingFn = fn;
                if (handle === null) handle = schedule(fire);
            },
            /** نفّذ المعلّق فورًا (نهاية البث) — يتجاوز الفاصل الزمني. */
            flush: function () {
                if (handle !== null) { cancelSchedule(handle); handle = null; }
                var fn = pendingFn;
                pendingFn = null;
                if (fn) { lastRender = now(); fn(); }
            },
            /** أسقط المعلّق بلا تنفيذ (finalize يرندر بنفسه رندرًا كاملًا). */
            cancel: function () {
                if (handle !== null) { cancelSchedule(handle); handle = null; }
                pendingFn = null;
            },
            hasPending: function () { return pendingFn !== null; },
        };
    }

    function createSectionMemo() {
        var cache = Object.create(null);
        /**
         * أعد HTML المقطع من الكاش لو مصدره لم يتغير — وإلا أعد تحليله.
         * المقاطع المغلقة أثناء البث لا تتغير سلسلتها → cache hit دائم؛
         * المقطع المفتوح الأخير فقط هو من يتغير فيُعاد تحليله.
         */
        return function memo(key, src, renderFn) {
            var hit = cache[key];
            if (hit && hit.src === src) return hit.html;
            var html = renderFn(src);
            cache[key] = { src: src, html: html };
            return html;
        };
    }

    var api = {
        createThrottler: createThrottler,
        createSectionMemo: createSectionMemo,
        MIN_INTERVAL_MS: MIN_INTERVAL_MS,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
    if (global) global.StreamRender = api;
})(typeof window !== "undefined" ? window : globalThis);
