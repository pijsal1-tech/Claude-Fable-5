/* T-064 (R-904): إبراز الصياغة — نقطة الاستهلاك الوحيدة لمحرك highlight.js.
 *
 * قرار المحرك (Documentation gate): **highlight.js 11.11.1** وليس Shiki:
 *   - Shiki يحتاج WASM (oniguruma) + خطوة bundling ولا يعمل كـ <script> مفرد،
 *     بينما المشروع كله UMD-lite بلا build step (نفس نمط file_icons.js).
 *   - hljs ملف واحد مورَّد محليًا (static/vendor/highlight.min.js — BSD-3)
 *     يغطي كل لغات قائمة R-903 (JS/TS/Python/HTML/CSS/JSON/YAML/MD/Java/
 *     C/C++/C#/Go/Rust/PHP/Ruby/SQL/Shell/ini/diff) + dockerfile كـ grammar
 *     إضافية مورَّدة (static/vendor/hljs-dockerfile.min.js).
 *   - يعمل في node مباشرة → الاختبارات تشغّل المحرك الفعلي بلا متصفح.
 *
 * الألوان: صفر ألوان هنا — style.css يلوّن أصناف .hljs-* عبر توكنز
 * var(--syntax-*) من الثيمات (R-905)، فتبديل الثيم يعيد تلوين الكود فورًا.
 *
 * البث التدفقي (incremental): كاش LRU على مستوى البلوك — أثناء الـ streaming
 * تُعاد كتابة الـ HTML لكن كل بلوك كود اكتمل يُخدم من الكاش بلا إعادة
 * tokenize (نفس السلسلة حرفيًا = لا وميض)؛ البلوك الأخير المفتوح فقط
 * هو ما يُعاد تحليله مع كل chunk.
 *
 * الملفات الكبيرة (lazy): فوق LARGE_FILE_LINES يُبرَز مقطع النافذة المرئية
 * فقط (± VIEWPORT_BUFFER سطرًا) والباقي نص مهرَّب خام — O(viewport) لا O(file).
 *
 * لغة الملف تُشتق من FileIcons.getFileIcon(path).id (مصدر تصنيف أسماء
 * الملفات الوحيد — T-062/T-063): لا يوجد أي mapping امتداد→شيء هنا
 * (بوابة tests/unit/test_icon_consumption.py تفحص هذا الملف أيضًا).
 */
(function (global) {
    "use strict";

    // المتصفح: hljs + FileIcons مُحمَّلان قبل هذه الوحدة (ترتيب index.html
    // مفحوص باختبار). node (الاختبارات): نحمّل النسخ المورَّدة الفعلية.
    var hljs, FileIconsRef;
    if (typeof window !== "undefined" && window.hljs) {
        hljs = window.hljs;
        FileIconsRef = window.FileIcons;
    } else {
        hljs = require("../vendor/highlight.min.js");
        globalThis.hljs = hljs; // تسجيل الـ grammar الإضافية عبر UMD
        require("../vendor/hljs-dockerfile.min.js");
        FileIconsRef = require("./file_icons.js");
    }

    // صنف الأيقونة (وليس الامتداد) → لغة hljs. المفاتيح أصناف FileIcons.
    var ICON_ID_TO_LANG = {
        js: "javascript", ts: "typescript", jsx: "javascript",
        python: "python", html: "xml", css: "css", json: "json",
        yaml: "yaml", markdown: "markdown", java: "java", c: "c",
        cpp: "cpp", csharp: "csharp", go: "go", rust: "rust",
        php: "php", ruby: "ruby", sql: "sql", shell: "bash",
        docker: "dockerfile", config: "ini", lock: "json",
        image: null, file: null,
    };

    var LARGE_FILE_LINES = 2000; // فوقها: المسار الكسول بالـ viewport
    var VIEWPORT_BUFFER = 200;   // أسطر إضافية حول النافذة المرئية

    // كاش LRU للبلوكات المكتملة (streaming بلا إعادة tokenize).
    var CACHE_MAX = 500;
    var cache = new Map();
    var stats = { hits: 0, misses: 0 };

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // يقبل وسم السياج (fence tag) ويعيد لغة يعرفها المحرك (بما فيها
    // الأسماء البديلة py/sh/yml/html...) أو null للمجهول.
    function normalizeLang(tag) {
        if (!tag) return null;
        var lang = String(tag).trim().toLowerCase();
        return hljs.getLanguage(lang) ? lang : null;
    }

    // لغة ملف من مساره — عبر تصنيف FileIcons (المصدر الوحيد).
    function langForPath(path) {
        if (!path) return null;
        var id = FileIconsRef.getFileIcon(path).id;
        return ICON_ID_TO_LANG[id] || null;
    }

    // tokenize مباشر بلا كاش (للمقاطع الكسولة المتغيرة مع كل scroll).
    function rawHighlight(code, lang) {
        try {
            if (lang) {
                return {
                    html: hljs.highlight(code, { language: lang, ignoreIllegals: true }).value,
                    language: lang,
                };
            }
            var auto = hljs.highlightAuto(code);
            return { html: auto.value, language: auto.language || "plaintext" };
        } catch (e) {
            return { html: escapeHtml(code), language: "plaintext" };
        }
    }

    // الإبراز المُكاش — واجهة بلوكات الشات. lang قد يكون وسم سياج خام.
    function highlightCode(code, lang) {
        var norm = normalizeLang(lang);
        var key = (norm || "") + "\u0000" + code;
        if (cache.has(key)) {
            stats.hits += 1;
            var hit = cache.get(key);
            cache.delete(key);
            cache.set(key, hit); // LRU refresh
            return hit;
        }
        stats.misses += 1;
        var result = rawHighlight(code, norm);
        cache.set(key, result);
        if (cache.size > CACHE_MAX) {
            cache.delete(cache.keys().next().value);
        }
        return result;
    }

    // يبرز كل بلوكات <pre><code> داخل حاوية DOM (الشات: رسائل/بث/نهائي).
    // نفس المحتوى = نفس الكاش = نفس السلسلة حرفيًا → لا وميض أثناء البث.
    function highlightContainer(container) {
        var blocks = container.querySelectorAll("pre code");
        for (var i = 0; i < blocks.length; i++) {
            var block = blocks[i];
            var m = block.className.match(/language-([\w+-]+)/);
            var res = highlightCode(block.textContent, m ? m[1] : null);
            block.innerHTML = res.html;
            block.classList.add("hljs");
            block.setAttribute("data-lang", res.language);
        }
    }

    // حساب شريحة النافذة المرئية لملف كبير.
    function viewportSlice(text, firstVisibleLine, visibleCount) {
        var lines = text.split("\n");
        var start = Math.max(0, (firstVisibleLine || 0) - VIEWPORT_BUFFER);
        var end = Math.min(lines.length, (firstVisibleLine || 0) + (visibleCount || 60) + VIEWPORT_BUFFER);
        return { lines: lines, start: start, end: end };
    }

    // HTML خلفية المحرر (overlay خلف الـ textarea):
    //   - plain: لا لغة معروفة → نص مهرَّب فقط.
    //   - full : ملف صغير/متوسط → إبراز كامل (مُكاش).
    //   - lazy : ملف كبير → tokenize لشريحة الـ viewport فقط،
    //            وقبلها/بعدها نص مهرَّب خام (الارتفاع/التمرير مضبوطان).
    function buildEditorHTML(text, path, firstVisibleLine, visibleCount) {
        var lang = langForPath(path);
        if (!lang) {
            return { html: escapeHtml(text), mode: "plain", language: null };
        }
        var v = viewportSlice(text, firstVisibleLine, visibleCount);
        if (v.lines.length <= LARGE_FILE_LINES) {
            return { html: highlightCode(text, lang).html, mode: "full", language: lang };
        }
        var before = v.start > 0 ? escapeHtml(v.lines.slice(0, v.start).join("\n")) + "\n" : "";
        var after = v.end < v.lines.length ? "\n" + escapeHtml(v.lines.slice(v.end).join("\n")) : "";
        var mid = rawHighlight(v.lines.slice(v.start, v.end).join("\n"), lang).html;
        return { html: before + mid + after, mode: "lazy", language: lang };
    }

    var api = {
        highlightCode: highlightCode,
        highlightContainer: highlightContainer,
        buildEditorHTML: buildEditorHTML,
        normalizeLang: normalizeLang,
        langForPath: langForPath,
        LARGE_FILE_LINES: LARGE_FILE_LINES,
        VIEWPORT_BUFFER: VIEWPORT_BUFFER,
        // للاختبارات فقط.
        _stats: stats,
        _cacheSize: function () { return cache.size; },
    };

    global.CodeHighlight = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
