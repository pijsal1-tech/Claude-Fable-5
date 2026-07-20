# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  FileManager — إدارة ملفات المشروع
  قراءة / كتابة / تعديل / مسح / نسخ احتياطي
═══════════════════════════════════════════════════════
"""
import os
import shutil
import pathlib
import zipfile
from datetime import datetime
from chain.path_policy import resolve_workspace_path, is_secret_file


# ── امتدادات الملفات المدعومة ──
WEB_EXTENSIONS = {
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".json", ".yaml", ".yml", ".toml",
    ".py", ".sh", ".bat", ".ps1",
    ".md", ".txt", ".env", ".gitignore",
    ".svg", ".xml",
}

# ── مجلدات يجب تجاهلها ──
IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", ".cache", ".vscode", ".idea",
    "venv", ".venv", "env", ".env",
}

# ── حد أقصى لحجم الملف (500 KB) ──
MAX_FILE_SIZE = 500 * 1024


class FileManager:
    """مدير ملفات المشروع"""

    def __init__(self, project_root: str):
        self.root = pathlib.Path(project_root).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"مسار المشروع غير موجود: {self.root}")
        # T-049 (R-702): خطافات write-through — تُنادى بالمسار النسبي
        # بعد كل كتابة ذرّية ناجحة (ProjectIndex يسجّل نفسه هنا).
        self._write_hooks: list = []

    def add_write_hook(self, fn) -> None:
        """تسجيل خطاف يُنادى بـ (rel_path: str) بعد كل كتابة ناجحة.

        T-049 (R-702): يغطي write_file وedit_file معًا (edit_file يفوّض
        إلى write_file). فشل خطاف لا يُفشل الكتابة نفسها.
        """
        self._write_hooks.append(fn)

    # ════════════════════════════════════════════
    # قراءة
    # ════════════════════════════════════════════
    def read_file(self, path: str, with_line_numbers: bool = True) -> str:
        """قراءة ملف مع ترقيم الأسطر (اختياري)"""
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {path}")
        if full_path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"الملف كبير جداً ({full_path.stat().st_size // 1024} KB)")

        content = full_path.read_text(encoding="utf-8", errors="replace")
        if with_line_numbers:
            lines = content.splitlines()
            width = len(str(len(lines)))
            numbered = [f"{i+1:>{width}}: {line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)
        return content

    def read_file_lines(self, path: str, start: int = 1, end: int = -1) -> str:
        """قراءة أسطر محددة من ملف"""
        full_path = self._resolve(path)
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if end == -1:
            end = len(lines)
        start = max(1, start)
        end = min(len(lines), end)
        width = len(str(end))
        selected = [f"{i:>{width}}: {lines[i-1]}" for i in range(start, end + 1)]
        return "\n".join(selected)

    # ════════════════════════════════════════════
    # كتابة
    # ════════════════════════════════════════════
    def write_file(self, path: str, content: str, backup: bool = True) -> str:
        """كتابة ملف (atomic write مع نسخ احتياطي)"""
        full_path = self._resolve(path)

        # نسخ احتياطي إن كان الملف موجود
        if backup and full_path.exists():
            self.create_backup(path)

        # إنشاء المجلد الأب إن لم يكن موجود
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # كتابة آمنة
        tmp = full_path.with_suffix(full_path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, full_path)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

        rel_path = str(full_path.relative_to(self.root))
        # T-049: إبلاغ الخطافات بعد نجاح os.replace — طزاجة فورية للفهرس.
        for hook in getattr(self, "_write_hooks", ()):
            try:
                hook(rel_path)
            except Exception:
                pass   # خطاف معطوب لا يُفشل الكتابة
        return rel_path

    # ════════════════════════════════════════════
    # تعديل جراحي
    # ════════════════════════════════════════════
    def edit_file(self, path: str, old_text: str, new_text: str,
                  backup: bool = True) -> bool:
        """تعديل جراحي — استبدال نص محدد في ملف"""
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {path}")

        content = full_path.read_text(encoding="utf-8")
        if old_text not in content:
            raise ValueError(f"النص المطلوب استبداله غير موجود في {path}")

        if backup:
            self.create_backup(path)

        new_content = content.replace(old_text, new_text, 1)
        self.write_file(path, new_content, backup=False)
        return True

    # ════════════════════════════════════════════
    # مسح المشروع
    # ════════════════════════════════════════════
    def scan_project(self, max_files: int = 10000) -> dict:
        """مسح بنية المشروع — يرجع ملخص الملفات والمجلدات"""
        files = []
        dirs = set()
        total_size = 0

        for item in self._walk(self.root, max_files):
            rel = item.relative_to(self.root)
            size = item.stat().st_size
            files.append({
                "path": str(rel).replace("\\", "/"),
                "ext": item.suffix,
                "size": size,
                "lines": self._count_lines(item),
            })
            dirs.add(str(rel.parent).replace("\\", "/"))
            total_size += size

        return {
            "root": str(self.root),
            "total_files": len(files),
            "total_size_kb": round(total_size / 1024, 1),
            "directories": sorted(dirs),
            "files": files,
        }

    def get_project_tree(self, max_depth: int = 3) -> str:
        """عرض شجرة المشروع كنص"""
        lines = [f"📁 {self.root.name}/"]
        self._build_tree(self.root, lines, prefix="", depth=0, max_depth=max_depth)
        return "\n".join(lines)

    def get_project_context(self, max_files: int = 15) -> str:
        """بناء سياق المشروع للبرومبت"""
        scan = self.scan_project(max_files)
        parts = [
            f"مسار المشروع: {scan['root']}",
            f"عدد الملفات: {scan['total_files']}",
            f"الحجم الإجمالي: {scan['total_size_kb']} KB",
            "",
            "بنية الملفات:",
        ]
        for f in scan["files"]:
            parts.append(f"  - {f['path']} ({f['lines']} سطر)")
        return "\n".join(parts)

    # ════════════════════════════════════════════
    # نسخ احتياطي
    # ════════════════════════════════════════════
    def create_backup(self, path: str) -> str:
        """إنشاء نسخة احتياطية"""
        full_path = self._resolve(path)
        if not full_path.exists():
            return ""

        backup_dir = self.root / ".webdev_backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{full_path.stem}_{timestamp}{full_path.suffix}"
        backup_path = backup_dir / backup_name

        shutil.copy2(full_path, backup_path)
        return str(backup_path.relative_to(self.root))

    def create_full_backup(self, max_backups: int = 5) -> str:
        """إنشاء نسخة احتياطية كاملة (ZIP) للمشروع بالكامل"""
        backup_dir = self.root / ".webdev_backups" / "full"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"project_{timestamp}.zip"
        zip_path = backup_dir / zip_name

        # إنشاء ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in self._walk_for_backup(self.root):
                rel = item.relative_to(self.root)
                zf.write(item, rel)

        # حذف النسخ القديمة (أبقي آخر max_backups)
        existing = sorted(backup_dir.glob("project_*.zip"), reverse=True)
        for old in existing[max_backups:]:
            try:
                old.unlink()
            except Exception:
                pass

        return str(zip_path.relative_to(self.root))

    def _walk_for_backup(self, root: pathlib.Path) -> list[pathlib.Path]:
        """مسح كل الملفات للنسخ الاحتياطي (مع تجاهل المجلدات الكبيرة)"""
        # مجلدات إضافية يجب تجاهلها في الـ backup
        backup_ignore = IGNORE_DIRS | {".webdev_backups"}
        result = []
        try:
            for item in sorted(root.iterdir()):
                if item.is_dir():
                    if item.name in backup_ignore or item.name.startswith("."):
                        continue
                    result.extend(self._walk_for_backup(item))
                elif item.is_file():
                    if is_secret_file(item):
                        continue
                    # تجاهل الملفات الكبيرة جداً (> 5MB)
                    try:
                        if item.stat().st_size <= 5 * 1024 * 1024:
                            result.append(item)
                    except Exception:
                        pass
        except PermissionError:
            pass
        return result

    # ════════════════════════════════════════════
    # أدوات داخلية
    # ════════════════════════════════════════════
    def _resolve(self, path: str) -> pathlib.Path:
        """تحويل مسار نسبي لمسار كامل (مع حماية من traversal)"""
        return resolve_workspace_path(self.root, path, must_exist=False, allow_symlinks=False)

    def _walk(self, root: pathlib.Path, max_files: int) -> list[pathlib.Path]:
        """مسح recursive مع تجاهل المجلدات غير المرغوبة"""
        result = []
        try:
            for item in sorted(root.iterdir()):
                if len(result) >= max_files:
                    break
                if item.is_dir():
                    if item.name in IGNORE_DIRS or item.name.startswith("."):
                        continue
                    result.extend(self._walk(item, max_files - len(result)))
                elif item.is_file():
                    if is_secret_file(item):
                        continue
                    if item.suffix in WEB_EXTENSIONS and item.stat().st_size <= MAX_FILE_SIZE:
                        result.append(item)
        except PermissionError:
            pass
        return result

    def _build_tree(self, root: pathlib.Path, lines: list, prefix: str,
                    depth: int, max_depth: int):
        if depth >= max_depth:
            return
        try:
            entries = sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in IGNORE_DIRS
                and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file() and e.suffix in WEB_EXTENSIONS and not is_secret_file(e)]

        items = dirs + files
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            if item.is_dir():
                lines.append(f"{prefix}{connector}📁 {item.name}/")
                extension = "    " if is_last else "│   "
                self._build_tree(item, lines, prefix + extension, depth + 1, max_depth)
            else:
                lines.append(f"{prefix}{connector}📄 {item.name}")

    def _count_lines(self, path: pathlib.Path) -> int:
        try:
            return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            return 0
