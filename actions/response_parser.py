# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ResponseParser — تحليل رد الـ AI واستخراج الإجراءات
  يستخرج: بلوكات الكود، أوامر الطرفية، التعديلات
═══════════════════════════════════════════════════════
"""
import re
from dataclasses import dataclass, field


@dataclass
class FileBlock:
    """بلوك كود مع اسم الملف"""
    path: str
    content: str
    language: str = ""


@dataclass
class EditBlock:
    """تعديل جراحي"""
    path: str
    old_text: str
    new_text: str


@dataclass
class CommandBlock:
    """أمر طرفية"""
    command: str


@dataclass
class OptionBlock:
    """خيار مقترح من AI"""
    text: str


@dataclass
class ParsedResponse:
    """نتيجة التحليل"""
    text: str                              # النص الكامل
    explanation: str = ""                   # الشرح (بدون كود)
    files: list[FileBlock] = field(default_factory=list)
    edits: list[EditBlock] = field(default_factory=list)
    commands: list[CommandBlock] = field(default_factory=list)
    options: list[OptionBlock] = field(default_factory=list)

    @property
    def has_actions(self) -> bool:
        return bool(self.files or self.edits or self.commands)

    def summary(self) -> str:
        parts = []
        if self.files:
            parts.append(f"📄 {len(self.files)} ملف جديد/معدل")
        if self.edits:
            parts.append(f"✏️ {len(self.edits)} تعديل جراحي")
        if self.commands:
            parts.append(f"⚡ {len(self.commands)} أمر")
        return " | ".join(parts) if parts else "💬 رد نصي فقط"


class ResponseParser:
    """تحليل رد الـ AI واستخراج الإجراءات"""

    # ── أنماط الاستخراج ──
    # ```FILE: path/to/file.ext
    _FILE_PATTERN = re.compile(
        r'```FILE:\s*(.+?)\n(.*?)```',
        re.DOTALL
    )

    # ```CMD
    _CMD_PATTERN = re.compile(
        r'```CMD\n(.*?)```',
        re.DOTALL
    )

    # ```EDIT: path/to/file.ext
    # <<<< OLD
    # old code
    # ====
    # new code
    # >>>> NEW
    _EDIT_PATTERN = re.compile(
        r'```EDIT:\s*(.+?)\n<<<< OLD\n(.*?)\n====\n(.*?)\n>>>> NEW\n```',
        re.DOTALL
    )

    # Fallback: ```language\n...\n``` بدون FILE:
    _CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)\n(.*?)```',
        re.DOTALL
    )

    # [OPTIONS] block — اقتراحات ذكية
    _OPTIONS_PATTERN = re.compile(
        r'\[OPTIONS\]\s*\n((?:- \[\d+\].+\n?)+)',
        re.MULTILINE
    )
    _OPTION_LINE_PATTERN = re.compile(
        r'- \[\d+\]\s*(.+)',
    )

    def parse(self, response: str, mode: str | None = None) -> ParsedResponse:
        """تحليل الرد الكامل.

        TSK-101 (BUG-01): المحلل أصبح mode-aware — في وضع ``chat``
        يُعطّل fallback التخميني (بلوكات الكود العادية → ملفات/أوامر)،
        وتبقى الوسوم الصريحة (FILE:/EDIT:/```CMD) تعمل في كل الأوضاع.
        ``mode=None`` = السلوك التاريخي الكامل (مسارات chain/action_applier).
        """
        result = ParsedResponse(text=response)

        # استخراج بلوكات الملفات
        for match in self._FILE_PATTERN.finditer(response):
            path = match.group(1).strip()
            content = match.group(2).strip()
            lang = self._detect_language(path)
            result.files.append(FileBlock(path=path, content=content, language=lang))

        # استخراج التعديلات
        for match in self._EDIT_PATTERN.finditer(response):
            path = match.group(1).strip()
            old_text = match.group(2).strip()
            new_text = match.group(3).strip()
            result.edits.append(EditBlock(path=path, old_text=old_text, new_text=new_text))

        # استخراج الأوامر
        for match in self._CMD_PATTERN.finditer(response):
            cmd = match.group(1).strip()
            if cmd:
                result.commands.append(CommandBlock(command=cmd))

        # Fallback: بلوكات كود عادية (```python ... ```) لم تُلتقط كـ FILE/CMD/EDIT
        # TSK-101 (BUG-01): وضع chat لا يدخل fallback التخميني إطلاقًا.
        if mode != "chat" and not result.files and not result.edits:
            # نبحث عن بلوكات كود قد تكون ملفات
            already_matched = set()
            for p in [self._FILE_PATTERN, self._EDIT_PATTERN, self._CMD_PATTERN]:
                for m in p.finditer(response):
                    already_matched.add((m.start(), m.end()))

            for match in self._CODE_BLOCK_PATTERN.finditer(response):
                # تخطي البلوكات اللي اتلقطت من الأنماط السابقة
                pos = (match.start(), match.end())
                if any(s <= pos[0] and pos[1] <= e for s, e in already_matched):
                    continue

                lang = match.group(1).strip().lower()
                content = match.group(2).strip()

                # تخطي البلوكات الفاضية أو القصيرة جداً
                if not content or len(content) < 5:
                    continue
                # تخطي بلوكات الأوامر
                if lang in ("bash", "sh", "cmd", "powershell", "bat", "shell", "console"):
                    # TSK-102 (NF-13): بلوكات bash في الـ fallback لا تتحول
                    # لأوامر إلا بوسم صريح لكل سطر: "CMD: <الأمر>".
                    # أي سطر آخر = عرض فقط (display-only). بلوك ```CMD
                    # الصريح يبقى كما هو أعلاه.
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith("CMD:"):
                            tagged = line[len("CMD:"):].strip()
                            if tagged:
                                result.commands.append(CommandBlock(command=tagged))
                    continue

                # اقتراح اسم ملف
                suggested_name = self._suggest_filename(lang, content)
                if suggested_name:
                    result.files.append(FileBlock(
                        path=suggested_name,
                        content=content,
                        language=lang
                    ))

        # الشرح = كل شيء ما عدا بلوكات الكود
        explanation = response
        for pattern in [self._FILE_PATTERN, self._EDIT_PATTERN,
                        self._CMD_PATTERN, self._CODE_BLOCK_PATTERN]:
            explanation = pattern.sub("", explanation)
        result.explanation = explanation.strip()

        # استخراج الاقتراحات الذكية [OPTIONS]
        options_match = self._OPTIONS_PATTERN.search(response)
        if options_match:
            options_text = options_match.group(1)
            for opt_match in self._OPTION_LINE_PATTERN.finditer(options_text):
                opt_text = opt_match.group(1).strip()
                if opt_text:
                    result.options.append(OptionBlock(text=opt_text))

        return result

    def _suggest_filename(self, lang: str, content: str) -> str:
        """اقتراح اسم ملف من لغة البرمجة"""
        lang_to_ext = {
            "python": ".py", "py": ".py",
            "javascript": ".js", "js": ".js",
            "typescript": ".ts", "ts": ".ts",
            "html": ".html",
            "css": ".css", "scss": ".scss", "sass": ".sass",
            "jsx": ".jsx", "tsx": ".tsx",
            "json": ".json",
            "yaml": ".yaml", "yml": ".yaml",
            "markdown": ".md", "md": ".md",
            "xml": ".xml", "svg": ".svg",
        }
        ext = lang_to_ext.get(lang)
        if not ext:
            return ""

        # محاولة استخراج اسم من التعليقات أو المحتوى
        first_line = content.splitlines()[0].strip() if content else ""

        # Python: # filename.py أو اسم الكلاس/الدالة
        if ext == ".py":
            if first_line.startswith("# ") and "." in first_line:
                name = first_line[2:].strip().split()[0]
                if name.endswith(".py"):
                    return name
            return f"script{ext}"

        # HTML: اسم من <title>
        if ext == ".html":
            import re
            title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip().lower().replace(" ", "_")[:20]
                return f"{title}.html" if title else "index.html"
            return "index.html"

        # CSS
        if ext == ".css":
            return "style.css"

        # JS
        if ext in (".js", ".ts"):
            return f"main{ext}"

        return f"output{ext}"

    def _detect_language(self, path: str) -> str:
        """تحديد لغة البرمجة من الامتداد"""
        ext_map = {
            ".html": "html", ".htm": "html",
            ".css": "css", ".scss": "scss", ".sass": "sass",
            ".js": "javascript", ".jsx": "jsx",
            ".ts": "typescript", ".tsx": "tsx",
            ".py": "python",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash", ".bat": "batch", ".ps1": "powershell",
        }
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return ""

