/* TSK-724 (P2-2/D-10 — FI-09): نافذة عرض افتراضية — منطق نقي.
 * (UMD-lite، قابل للاختبار في node — نمط command_palette.js).
 * الـ DOM glue في app.js فقط.
 *
 * العقد: `computeWindow(scrollTop, viewportH, itemHeights, overscan)`
 * ⇒ {start, end, padTop, padBottom} حيث end حصري (exclusive)،
 * والثابت الصارم: padTop + Σ heights[start..end) + padBottom
 * = Σ heights (المجموع الكلي) — دومًا، لكل المدخلات.
 * لا DOM ولا شبكة هنا — حساب أعداد صرف.
 */
(function (global) {
    "use strict";

    /** مجموع ارتفاعات [0..n) — مساعد داخلي. */
    function sumRange(heights, from, to) {
        var s = 0;
        for (var i = from; i < to; i++) s += heights[i];
        return s;
    }

    /**
     * حساب نافذة العرض.
     * @param {number} scrollTop  إزاحة التمرير (تُقصّ إلى [0..])
     * @param {number} viewportH  ارتفاع منفذ العرض (>= 0)
     * @param {number[]} itemHeights  ارتفاعات العناصر بالبكسل
     * @param {number} overscan  عناصر إضافية قبل/بعد النافذة (>= 0)
     * @returns {{start:number,end:number,padTop:number,padBottom:number}}
     */
    function computeWindow(scrollTop, viewportH, itemHeights, overscan) {
        var n = itemHeights ? itemHeights.length : 0;
        if (!n) return { start: 0, end: 0, padTop: 0, padBottom: 0 };

        var top = Math.max(0, Number(scrollTop) || 0);
        var vh = Math.max(0, Number(viewportH) || 0);
        var os = Math.max(0, Math.floor(Number(overscan) || 0));

        // أول عنصر يتقاطع مع أعلى المنفذ.
        var start = 0;
        var acc = 0;
        while (start < n && acc + itemHeights[start] <= top) {
            acc += itemHeights[start];
            start++;
        }
        // آخر عنصر يتقاطع مع أسفل المنفذ (end حصري).
        var end = start;
        var acc2 = acc;
        var bottom = top + vh;
        while (end < n && acc2 < bottom) {
            acc2 += itemHeights[end];
            end++;
        }
        // overscan مع القصّ للحدود.
        start = Math.max(0, start - os);
        end = Math.min(n, end + os);
        if (start > end) start = end; // حارس (لا يحدث نظريًا)

        var padTop = sumRange(itemHeights, 0, start);
        var padBottom = sumRange(itemHeights, end, n);
        return { start: start, end: end, padTop: padTop, padBottom: padBottom };
    }

    /** المجموع الكلي — يُستخدم للتحقق ولتقدير spacer الأولي. */
    function totalHeight(itemHeights) {
        return sumRange(itemHeights || [], 0, (itemHeights || []).length);
    }

    var api = { computeWindow: computeWindow, totalHeight: totalHeight };

    global.VirtualList = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
