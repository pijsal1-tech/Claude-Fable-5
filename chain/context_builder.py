# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🧠 ContextBuilder — جمع سياق ذكي من المشروع

  موديول مشترك يستخدمه:
  ├── server.py (الويب) → عبر AgentLoop
  └── Genspark_sonnet-5.py (CLI) → عبر build_prompt()

  يحلل طلب المستخدم ويجمع المعلومات المحتاجة تلقائياً:
  - ملفات مذكورة بالاسم → يقرأها
  - مجلدات → يعرض محتوياتها
  - طلب عام → شجرة المشروع + README + dependencies
  - أنماط كود → يبحث عنها
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import os
import re
import pathlib
from dataclasses import dataclass, field
from typing import Optional, Callable
from chain.path_policy import resolve_workspace_path, is_secret_file


# ════════════════════════════════════════════════════
# 📦 ContextItem — عنصر سياق واحد
# ════════════════════════════════════════════════════

@dataclass
class ContextItem:
    """قطعة سياق مجمعة من المشروع"""
    kind: str         # "file", "dir", "search", "tree", "info"
    source: str       # المسار أو الاستعلام
    content: str      # المحتوى
    success: bool = True
    size: int = 0     # حجم المحتوى الأصلي (قبل القطع)

    def to_prompt_block(self, max_len: int = 8000) -> str:
        """تحويل لبلوك يُضاف للـ prompt"""
        icons = {
            "file": "📄", "dir": "📁", "search": "🔍",
            "tree": "🌳", "info": "ℹ️", "deps": "📦",
        }
        icon = icons.get(self.kind, "📎")
        content = self.content[:max_len]
        if len(self.content) > max_len:
            content += f"\n... (مقطوع — {len(self.content)} حرف إجمالي)"
        return f"{icon} [{self.kind}: {self.source}]:\n{content}"


# ════════════════════════════════════════════════════
# 🔍 ContextResult — نتيجة جمع السياق
# ════════════════════════════════════════════════════

@dataclass
class ContextResult:
    """نتيجة عملية جمع السياق"""
    items: list[ContextItem] = field(default_factory=list)

    @property
    def has_context(self) -> bool:
        return len(self.items) > 0

    @property
    def files_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "file" and i.success)

    @property
    def dirs_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "dir" and i.success)

    @property
    def searches_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "search" and i.success)

    @property
    def total_success(self) -> int:
        return sum(1 for i in self.items if i.success)

    def build_prompt_section(self, max_total: int = 50000) -> str:
        """بناء قسم السياق للـ prompt"""
        if not self.items:
            return ""

        parts = [
            f"[✅ تم جمع {self.total_success} معلومة تلقائياً من المشروع الفعلي "
            f"({self.files_count} ملفات، {self.dirs_count} مجلدات، {self.searches_count} بحث)]:\n"
        ]

        total_len = 0
        per_item_max = max_total // max(len(self.items), 1)

        for item in self.items:
            if not item.success:
                continue
            block = item.to_prompt_block(max_len=per_item_max)
            if total_len + len(block) > max_total:
                parts.append(f"\n... (وقف الإرفاق — وصلنا للحد: {max_total} حرف)")
                break
            parts.append(block)
            total_len += len(block)

        parts.append(
            "\n[تعليمات مهمة]: المعلومات أعلاه مقروءة من الملفات الفعلية في نظام الملفات. "
            "أنت تملك وصولاً حقيقياً للمشروع — لا تقل 'مش عارف أوصل للملفات' أو 'ابعتلي الملف'. "
            "استخدم المعلومات المرفقة لتحليل الطلب والرد بشكل كامل."
        )

        return "\n\n".join(parts)

    def get_summary(self) -> dict:
        return {
            "total": len(self.items),
            "files": self.files_count,
            "dirs": self.dirs_count,
            "searches": self.searches_count,
            "success": self.total_success,
        }


# ════════════════════════════════════════════════════
# 🧠 ContextBuilder — المحرك الرئيسي
# ════════════════════════════════════════════════════

class ContextBuilder:
    """
    يحلل طلب المستخدم ويجمع المعلومات المحتاجة من المشروع.

    يعمل مع أي project_root — لا يحتاج FileManager أو AgentTools.

    الاستخدام:
        builder = ContextBuilder("/path/to/project")
        result = builder.gather(user_request)
        enriched_prompt = result.build_prompt_section()
    """

    # ── امتدادات الملفات المدعومة ──
    FILE_EXTS = (
        "py", "js", "ts", "jsx", "tsx", "html", "css", "scss",
        "json", "md", "txt", "yml", "yaml", "toml", "cfg", "ini",
        "sh", "bat", "env", "sql", "go", "rs", "java", "c", "cpp", "h",
        "vue", "svelte", "php", "rb", "swift", "kt",
    )

    # ── كلمات عامة تعني "اشرح المشروع" ──
    GENERAL_KEYWORDS = [
        "المشروع", "هيكل", "بنية", "اشرح", "حلل", "شرح", "ملخص",
        "structure", "project", "analyze", "explain", "overview",
        "architecture", "كل الملفات", "all files", "codebase",
        "راجع", "review", "inspect", "فحص",
    ]

    # ── ملفات مهمة تُقرأ تلقائياً ──
    README_NAMES = ["README.md", "readme.md", "README.txt", "README.rst", "README"]
    DEP_FILES = [
        "package.json", "requirements.txt", "pyproject.toml",
        "Cargo.toml", "go.mod", "Gemfile", "pom.xml",
        "build.gradle", "composer.json",
    ]
    CONFIG_FILES = [
        "tsconfig.json", "vite.config.ts", "vite.config.js",
        "webpack.config.js", ".env", ".env.example",
        "next.config.js", "next.config.mjs",
    ]

    def __init__(self, project_root: str,
                 max_file_size: int = 100 * 1024,
                 max_files: int = 10,
                 on_progress: Optional[Callable] = None):
        """
        Args:
            project_root: مسار جذر المشروع
            max_file_size: حد أقصى لحجم ملف واحد (bytes)
            max_files: حد أقصى لعدد الملفات المقروءة
            on_progress: callback اختياري: fn(kind, source, status)
        """
        self.root = pathlib.Path(project_root).resolve()
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.on_progress = on_progress or (lambda *a: None)

    # ════════════════════════════════════════
    # 🎯 الواجهة الرئيسية
    # ════════════════════════════════════════

    def gather(self, user_request: str) -> ContextResult:
        """
        تحليل طلب المستخدم وجمع كل المعلومات المحتاجة.

        Returns:
            ContextResult يحتوي كل المعلومات المجمعة
        """
        result = ContextResult()
        request_lower = user_request.lower()

        # 1. ملفات مذكورة بالاسم
        self._gather_mentioned_files(user_request, result)

        # 2. مجلدات مذكورة
        self._gather_mentioned_dirs(user_request, result)

        # 3. طلب عام → شجرة + README + deps
        if self._is_general_request(request_lower) and result.files_count == 0 and result.dirs_count == 0:
            self._gather_project_overview(result)

        # 4. أنماط بحث كود
        self._gather_code_searches(user_request, result)

        # ── ملخص ──
        if result.has_context:
            s = result.get_summary()
            try:
                print(f"  🔍 ContextBuilder: {s['files']} files, "
                      f"{s['dirs']} dirs, {s['searches']} searches")
            except Exception:
                try:
                    print(f"  [ContextBuilder] {s['files']} files, "
                          f"{s['dirs']} dirs, {s['searches']} searches")
                except Exception:
                    pass

        return result

    # ════════════════════════════════════════
    # 🔧 عمليات الجمع الفرعية
    # ════════════════════════════════════════

    def _gather_mentioned_files(self, request: str, result: ContextResult):
        """كشف وقراءة ملفات مذكورة بالاسم في الطلب"""
        ext_pattern = "|".join(self.FILE_EXTS)
        file_matches = re.findall(
            rf'[\w\-/\\]+\.(?:{ext_pattern})',
            request,
            re.IGNORECASE,
        )

        seen: set[str] = set()
        for fp in file_matches:
            fp_clean = fp.replace("\\", "/")
            if fp_clean in seen or len(seen) >= self.max_files:
                break
            seen.add(fp_clean)

            self.on_progress("file", fp_clean, "reading")
            content = self._read_file(fp_clean)
            success = content is not None
            result.items.append(ContextItem(
                kind="file",
                source=fp_clean,
                content=content or f"❌ ملف غير موجود: {fp_clean}",
                success=success,
                size=len(content) if content else 0,
            ))
            if success:
                self.on_progress("file", fp_clean, "done")

    def _gather_mentioned_dirs(self, request: str, result: ContextResult):
        """كشف وعرض مجلدات مذكورة"""
        dir_matches = re.findall(
            r'(?:مجلد|folder|directory|dir|path)\s*[:\s]*["\']?([/\w\-\\.]+)["\']?',
            request,
            re.IGNORECASE,
        )
        # مسارات تنتهي بـ /
        dir_matches += re.findall(r'([\w\-]+/)', request)
        
        # كشف مجلدات مذكورة والكلمة التوضيحية بعدها (مثال: actions folder)
        dir_matches += re.findall(
            r'["\']?([/\w\-\\.]+?)["\']?\s*(?:مجلد|folder|directory|dir)',
            request,
            re.IGNORECASE,
        )

        seen = set()
        for dp in dir_matches:
            dp_clean = dp.strip("/").replace("\\", "/")
            if not dp_clean or len(dp_clean) < 2 or dp_clean in seen:
                continue
            seen.add(dp_clean)
            if len(seen) > 3:
                break

            self.on_progress("dir", dp_clean, "listing")
            listing = self._list_dir(dp_clean, depth=2)
            success = listing is not None
            result.items.append(ContextItem(
                kind="dir",
                source=dp_clean,
                content=listing or f"❌ مجلد غير موجود: {dp_clean}",
                success=success,
            ))
            
            # قراءة ملفات الكود الموجودة داخل المجلد تلقائياً لو عددها معقول لتمكين الـ AI من تحليلها
            if success:
                try:
                    dir_path = (self.root / dp_clean).resolve()
                    if dir_path.is_dir():
                        supported_exts = {f".{e}" for e in self.FILE_EXTS}
                        sub_files = []
                        # T-020 determinism fix (order-only): iterdir order is
                        # filesystem-dependent — sorted() يثبّت ترتيب القراءة
                        for entry in sorted(dir_path.iterdir()):
                            if entry.is_file() and entry.suffix in supported_exts:
                                sub_files.append(entry)
                        
                        for sf in sub_files:
                            if result.files_count >= self.max_files:
                                break
                            rel_sf = str(sf.relative_to(self.root)).replace("\\", "/")
                            # تجنب القراءة المكررة
                            if any(item.source == rel_sf for item in result.items):
                                continue
                            
                            self.on_progress("file", rel_sf, "reading")
                            content = self._read_file(rel_sf)
                            if content:
                                result.items.append(ContextItem(
                                    kind="file",
                                    source=rel_sf,
                                    content=content,
                                    success=True,
                                    size=len(content),
                                ))
                                self.on_progress("file", rel_sf, "done")
                except Exception:
                    pass

    def _gather_project_overview(self, result: ContextResult):
        """جمع نظرة عامة على المشروع: شجرة + README + dependencies + config"""

        # 1. شجرة المشروع
        self.on_progress("tree", ".", "scanning")
        tree = self._build_tree(max_depth=2)
        if tree:
            result.items.append(ContextItem(
                kind="tree", source="project_root", content=tree, success=True
            ))

        # 2. README
        for readme in self.README_NAMES:
            content = self._read_file(readme)
            if content:
                result.items.append(ContextItem(
                    kind="file", source=readme, content=content, success=True,
                    size=len(content),
                ))
                break

        # 3. Dependencies (package.json, requirements.txt, etc.)
        for dep in self.DEP_FILES:
            content = self._read_file(dep)
            if content:
                result.items.append(ContextItem(
                    kind="deps", source=dep, content=content, success=True,
                    size=len(content),
                ))
                break

        # 4. Config files
        for cfg in self.CONFIG_FILES:
            content = self._read_file(cfg)
            if content:
                result.items.append(ContextItem(
                    kind="file", source=cfg, content=content, success=True,
                    size=len(content),
                ))
                break  # واحد يكفي

    def _gather_code_searches(self, request: str, result: ContextResult):
        """بحث عن أنماط كود مذكورة"""
        # أنماط Python/JS
        search_patterns = re.findall(
            r'(?:def|function|class|import|from)\s+(\w+)',
            request,
        )
        # أسماء بالعربي
        code_names = re.findall(
            r'(?:دالة|فانكشن|كلاس|ميثود|function|class|method)\s+[`"\']?(\w+)[`"\']?',
            request,
            re.IGNORECASE,
        )

        seen = set()
        for pattern in search_patterns + code_names:
            if len(pattern) < 3 or pattern in seen:
                continue
            seen.add(pattern)
            if len(seen) > 3:
                break

            self.on_progress("search", pattern, "searching")
            results = self._search_in_files(pattern, max_results=10)
            if results:
                result.items.append(ContextItem(
                    kind="search", source=pattern, content=results, success=True
                ))

    def _is_general_request(self, request_lower: str) -> bool:
        """هل الطلب عام (يحتاج نظرة شاملة على المشروع)؟"""
        return any(kw in request_lower for kw in self.GENERAL_KEYWORDS)

    # ════════════════════════════════════════
    # 🔧 عمليات I/O الأساسية
    # ════════════════════════════════════════

    def _read_file(self, rel_path: str) -> Optional[str]:
        """قراءة ملف من المشروع بأمان"""
        try:
            full = resolve_workspace_path(self.root, rel_path, must_exist=False, allow_symlinks=False)
            if not full.is_file():
                # محاولة بحث بالاسم
                basename = pathlib.Path(rel_path).name
                # T-020 determinism fix (order-only): sorted() يثبّت أي مرشح يُختار
                found = sorted(self.root.rglob(basename))
                if found:
                    for candidate in found:
                        try:
                            candidate_resolved = resolve_workspace_path(self.root, str(candidate), must_exist=True, allow_symlinks=False)
                            full = candidate_resolved
                            break
                        except Exception:
                            continue
                if not full or not full.is_file():
                    return None
            if full.stat().st_size > self.max_file_size:
                return f"(ملف كبير: {full.stat().st_size // 1024}KB — تم تخطيه)"
            return full.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def _list_dir(self, rel_path: str, depth: int = 2) -> Optional[str]:
        """عرض محتويات مجلد"""
        try:
            target = resolve_workspace_path(self.root, rel_path, must_exist=True, allow_symlinks=False)
            if not target.is_dir():
                return None
            return self._tree_from(target, depth=depth, prefix="")
        except Exception:
            return None

    def _build_tree(self, max_depth: int = 2) -> Optional[str]:
        """بناء شجرة المشروع"""
        try:
            return self._tree_from(self.root, depth=max_depth, prefix="")
        except Exception:
            return None

    def _tree_from(self, path: pathlib.Path, depth: int, prefix: str,
                   _max_items: int = 200) -> str:
        """بناء شجرة من مسار معين"""
        SKIP = {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
            ".next", ".nuxt", ".cache", ".idea", ".vscode",
        }

        lines = []
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return f"{prefix}(permission denied)"

        count = 0
        for entry in entries:
            if is_secret_file(entry):
                continue
            if entry.name.startswith(".") and entry.name not in (".env", ".env.example"):
                continue
            if entry.name in SKIP:
                continue
            count += 1
            if count > _max_items:
                lines.append(f"{prefix}... (+{len(entries) - _max_items} more)")
                break

            if entry.is_dir():
                # عدد الملفات داخله
                try:
                    sub_count: int | str = sum(1 for _ in entry.iterdir())
                except Exception:
                    sub_count = "?"
                lines.append(f"{prefix}📁 {entry.name}/ ({sub_count} items)")
                if depth > 1:
                    sub = self._tree_from(entry, depth - 1, prefix + "  ", _max_items)
                    if sub:
                        lines.append(sub)
            else:
                size_kb = entry.stat().st_size / 1024
                lines.append(f"{prefix}📄 {entry.name} ({size_kb:.1f}KB)")

        return "\n".join(lines)

    def _search_in_files(self, query: str, max_results: int = 10) -> Optional[str]:
        """بحث نصي بسيط في ملفات المشروع"""
        SKIP_DIRS = {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            "dist", "build", ".next",
        }
        SEARCH_EXTS = {f".{e}" for e in self.FILE_EXTS}

        results = []
        try:
            # T-020 determinism fix (order-only): sorted() يثبّت ترتيب النتائج
            for fp in sorted(self.root.rglob("*")):
                if not fp.is_file():
                    continue
                if fp.suffix not in SEARCH_EXTS:
                    continue
                # تخطي مجلدات
                if any(skip in fp.parts for skip in SKIP_DIRS):
                    continue
                if is_secret_file(fp):
                    continue
                if fp.stat().st_size > self.max_file_size:
                    continue

                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for i, line in enumerate(text.splitlines(), 1):
                    if query.lower() in line.lower():
                        rel = str(fp.relative_to(self.root)).replace("\\", "/")
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= max_results:
                            return "\n".join(results)
        except Exception:
            pass

        if not results:
            return None
        return "\n".join(results)


# ════════════════════════════════════════════════════
# 🎯 دالة مختصرة — للاستخدام السريع
# ════════════════════════════════════════════════════

def gather_context(project_root: str, user_request: str,
                   max_prompt_size: int = 50000,
                   on_progress: Optional[Callable] = None) -> str:
    """
    دالة مختصرة: جمع سياق + بناء نص جاهز للإضافة للـ prompt.

    الاستخدام:
        context_text = gather_context("/path/to/project", "حلل المشروع")
        full_prompt = user_request + "\\n\\n" + context_text

    Returns:
        نص جاهز يُضاف للـ prompt (أو "" لو مفيش سياق)
    """
    builder = ContextBuilder(project_root, on_progress=on_progress)
    result = builder.gather(user_request)
    return result.build_prompt_section(max_total=max_prompt_size)
