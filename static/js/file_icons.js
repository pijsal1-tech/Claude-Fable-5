/* ═══════════════════════════════════════════════════════════════
   📁 File-Type Icon System — T-062 (R-903)
   ═══════════════════════════════════════════════════════════════
   الوحدة الوحيدة لتحويل مسار ملف → أيقونة (extension→icon mapping).
   T-063 يستهلكها في شجرة الملفات/التبويبات/@mention — استيراد واحد،
   ممنوع أي mapping ثانٍ (grep-gated هناك).

   الاستخدام:
     const icon = FileIcons.getFileIcon("src/app.py");
     // → { id: "python", symbol: "#icon-python",
     //     colorToken: "--icon-py", label: "Python" }
     // <svg class="file-icon" style="color: var(--icon-py)">
     //   <use href="/static/icons/sprite.svg#icon-python"/></svg>

   الترخيص: كل الرموز في sprite.svg أشكال أصلية رُسمت لهذا المشروع
   (لا مجموعة أيقونات خارجية) — تخضع لرخصة المشروع نفسها.

   الألوان: currentColor في الرموز + colorToken من توكنز الثيم
   (static/themes/) — الأيقونات تُعاد تلوينها مع تبديل الثيم تلقائيًا.

   جدول التغطية (كل صنف مطلوب في T-062 له رمز مميّز):
   ┌──────────────┬───────────────────────────────────────────────┐
   │ id           │ الامتدادات / أسماء الملفات                    │
   ├──────────────┼───────────────────────────────────────────────┤
   │ js           │ .js .mjs .cjs                                 │
   │ ts           │ .ts .mts .cts                                 │
   │ jsx          │ .jsx .tsx                                     │
   │ python       │ .py .pyw .pyi                                 │
   │ html         │ .html .htm                                    │
   │ css          │ .css .scss .sass .less                        │
   │ json         │ .json .jsonc                                  │
   │ yaml         │ .yaml .yml .toml                              │
   │ markdown     │ .md .markdown .rst                            │
   │ java         │ .java .jar                                    │
   │ c            │ .c .h                                         │
   │ cpp          │ .cpp .cc .cxx .hpp .hh                        │
   │ csharp       │ .cs .csx                                      │
   │ go           │ .go                                           │
   │ rust         │ .rs                                           │
   │ php          │ .php                                          │
   │ ruby         │ .rb .erb                                      │
   │ sql          │ .sql .db .sqlite                              │
   │ shell        │ .sh .bash .zsh .bat .ps1                      │
   │ docker       │ Dockerfile docker-compose.yml .dockerfile     │
   │ config       │ .env .ini .cfg .conf .editorconfig .gitignore │
   │ image        │ .png .jpg .jpeg .gif .svg .webp .ico .bmp     │
   │ lock         │ package-lock.json yarn.lock poetry.lock       │
   │              │ Cargo.lock Pipfile.lock uv.lock .lock         │
   │ file         │ (fallback — أي امتداد غير معروف)              │
   └──────────────┴───────────────────────────────────────────────┘
   ═══════════════════════════════════════════════════════════════ */

(function (global) {
    "use strict";

    // بيانات كل أيقونة: رمز الـ sprite + توكن اللون + تسمية بشرية.
    const ICONS = {
        js:       { colorToken: "--icon-js",     label: "JavaScript" },
        ts:       { colorToken: "--icon-ts",     label: "TypeScript" },
        jsx:      { colorToken: "--icon-jsx",    label: "React JSX/TSX" },
        python:   { colorToken: "--icon-py",     label: "Python" },
        html:     { colorToken: "--icon-html",   label: "HTML" },
        css:      { colorToken: "--icon-css",    label: "CSS/SCSS" },
        json:     { colorToken: "--icon-json",   label: "JSON" },
        yaml:     { colorToken: "--icon-yaml",   label: "YAML/TOML" },
        markdown: { colorToken: "--icon-md",     label: "Markdown" },
        java:     { colorToken: "--icon-java",   label: "Java" },
        c:        { colorToken: "--icon-c",      label: "C" },
        cpp:      { colorToken: "--icon-cpp",    label: "C++" },
        csharp:   { colorToken: "--icon-csharp", label: "C#" },
        go:       { colorToken: "--icon-go",     label: "Go" },
        rust:     { colorToken: "--icon-rust",   label: "Rust" },
        php:      { colorToken: "--icon-php",    label: "PHP" },
        ruby:     { colorToken: "--icon-ruby",   label: "Ruby" },
        sql:      { colorToken: "--icon-sql",    label: "SQL" },
        shell:    { colorToken: "--icon-shell",  label: "Shell" },
        docker:   { colorToken: "--icon-docker", label: "Dockerfile" },
        config:   { colorToken: "--icon-config", label: "Config" },
        image:    { colorToken: "--icon-image",  label: "Image" },
        lock:     { colorToken: "--icon-lock",   label: "Lock file" },
        file:     { colorToken: "--icon-file",   label: "File" },
    };

    // امتداد (بنقطة، lowercase) → id
    const EXT_MAP = {
        ".js": "js", ".mjs": "js", ".cjs": "js",
        ".ts": "ts", ".mts": "ts", ".cts": "ts",
        ".jsx": "jsx", ".tsx": "jsx",
        ".py": "python", ".pyw": "python", ".pyi": "python",
        ".html": "html", ".htm": "html",
        ".css": "css", ".scss": "css", ".sass": "css", ".less": "css",
        ".json": "json", ".jsonc": "json",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "yaml",
        ".md": "markdown", ".markdown": "markdown", ".rst": "markdown",
        ".java": "java", ".jar": "java",
        ".c": "c", ".h": "c",
        ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
        ".cs": "csharp", ".csx": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby", ".erb": "ruby",
        ".sql": "sql", ".db": "sql", ".sqlite": "sql",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".bat": "shell", ".ps1": "shell",
        ".dockerfile": "docker",
        ".env": "config", ".ini": "config", ".cfg": "config",
        ".conf": "config", ".editorconfig": "config", ".gitignore": "config",
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
        ".svg": "image", ".webp": "image", ".ico": "image", ".bmp": "image",
        ".lock": "lock",
    };

    // اسم ملف كامل (lowercase) → id — أولوية أعلى من الامتداد
    // (package-lock.json يجب ألا يسقط إلى json).
    const FILENAME_MAP = {
        "dockerfile": "docker",
        "docker-compose.yml": "docker",
        "docker-compose.yaml": "docker",
        "package-lock.json": "lock",
        "yarn.lock": "lock",
        "pnpm-lock.yaml": "lock",
        "poetry.lock": "lock",
        "cargo.lock": "lock",
        "pipfile.lock": "lock",
        "uv.lock": "lock",
        "composer.lock": "lock",
        "gemfile.lock": "lock",
        ".env": "config",
        ".gitignore": "config",
        ".editorconfig": "config",
        "makefile": "shell",
    };

    /**
     * مسار ملف → وصف أيقونته.
     * @param {string} path مسار أو اسم ملف (يقبل "/" و "\\").
     * @returns {{id: string, symbol: string, colorToken: string, label: string}}
     */
    function getFileIcon(path) {
        let id = "file";
        if (typeof path === "string" && path.length > 0) {
            const base = path.split(/[\\/]/).pop().toLowerCase();
            if (Object.prototype.hasOwnProperty.call(FILENAME_MAP, base)) {
                id = FILENAME_MAP[base];
            } else {
                // ".env.local" وأمثالها: جرّب أطول لاحقة معروفة أولًا.
                const dot = base.indexOf(".");
                const lastDot = base.lastIndexOf(".");
                const ext = lastDot >= 0 ? base.slice(lastDot) : "";
                const fullSuffix = dot >= 0 ? base.slice(dot) : "";
                if (Object.prototype.hasOwnProperty.call(EXT_MAP, ext)) {
                    id = EXT_MAP[ext];
                } else if (
                    Object.prototype.hasOwnProperty.call(EXT_MAP, fullSuffix)
                ) {
                    id = EXT_MAP[fullSuffix];
                } else if (base.startsWith(".env.")) {
                    id = "config";
                }
            }
        }
        const meta = ICONS[id];
        return {
            id: id,
            symbol: "#icon-" + id,
            colorToken: meta.colorToken,
            label: meta.label,
        };
    }

    const api = {
        getFileIcon: getFileIcon,
        ICONS: ICONS,
        EXT_MAP: EXT_MAP,
        FILENAME_MAP: FILENAME_MAP,
        SPRITE_URL: "/static/icons/sprite.svg",
    };

    // Browser global + Node (للاختبارات).
    global.FileIcons = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
