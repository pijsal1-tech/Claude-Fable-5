# -*- coding: utf-8 -*-
"""T-017 (R-201): capture harness for the legacy inline context block.

Replicates — line for line — the context-collection logic embedded in
``server.py`` (the ``message`` handler: mention extraction → rglob search →
file-content injection → ``fm.get_project_context()``) so its exact output
can be pinned as golden files *before* R-201 extracts it into a
``ContextEngine``. The future engine must reproduce these goldens.

⚠️ Two determinism fixes (ORDER-only, set semantics and rendering
unchanged — documented per T-017 review):

1. ``rglob`` results are wrapped in ``sorted(...)`` — filesystem iteration
   order is platform/inode dependent.
2. ``exact_names_to_search`` / ``stems_to_search`` are iterated in
   ``sorted(...)`` order — legacy iterates raw ``set``s whose order changes
   per process (string-hash randomization). The legacy *order* is therefore
   genuinely nondeterministic; the *set* of included files is not. Goldens
   pin the sorted order as the canonical parity target.

Every other quirk is preserved deliberately, including:
- ``MAX_MENTIONED = 100`` while the comment claims 10 (the lying constant —
  removed only in R-201 itself).
- mention search does NOT filter secret files and does NOT check file size:
  a >MAX_FILE_SIZE file is *mentioned* but its ``read_file`` raises and is
  silently skipped — the header still claims it was read.
- stopword list is exactly ``('the','and','for','من','في','على')``.
"""
from __future__ import annotations

import pathlib
import re

from actions.file_manager import FileManager, WEB_EXTENSIONS

MAX_MENTIONED = 100  # حد أقصى 10 ملفات  ← نسخة حرفية من الثابت الكاذب

ROOT_TOKEN = "<ROOT>"


def collect_mentioned_files(fm: FileManager, user_text: str) -> list[str]:
    """Verbatim port of server.py mention extraction (order-stabilised)."""
    mentioned_files: list[str] = []
    try:
        # استخراج الكلمات والمسارات
        words = re.findall(r'[\w\-/\\]+(?:\.[\w]+)?', user_text)
        # استخراج مسارات فرعية مثل actions/file_manager.py
        subpaths = re.findall(r'[\w\-]+/[\w\-]+(?:\.[\w]+)?', user_text)

        exact_names_to_search = set()
        stems_to_search = set()

        for w in words + subpaths:
            if '.' in w:
                exact_names_to_search.add(w.replace('\\', '/'))
                stem_w = w.split('.')[0].split('/')[-1]
            else:
                stem_w = w.split('/')[-1]

            if len(stem_w) >= 3 and not stem_w.isdigit() and stem_w not in ('the', 'and', 'for', 'من', 'في', 'على'):
                stems_to_search.add(stem_w)

        # 1. البحث بالاسم الكامل أو المسار الفرعي
        for name in sorted(exact_names_to_search):          # determinism fix #2
            basename = name.split('/')[-1] if '/' in name else name
            for p in sorted(fm.root.rglob(basename)):       # determinism fix #1
                if p.is_file() and p.suffix in WEB_EXTENSIONS:
                    rel_path = str(p.relative_to(fm.root)).replace("\\", "/")
                    if rel_path not in mentioned_files:
                        mentioned_files.append(rel_path)
                        if len(mentioned_files) >= MAX_MENTIONED:
                            break
            if len(mentioned_files) >= MAX_MENTIONED:
                break

        # 2. البحث بالـ stem للماتش المرن
        if len(mentioned_files) < MAX_MENTIONED:
            for stem in sorted(stems_to_search):            # determinism fix #2
                for p in sorted(fm.root.rglob(f"*{stem}*")):  # determinism fix #1
                    if p.is_file() and p.suffix in WEB_EXTENSIONS:
                        rel_path = str(p.relative_to(fm.root)).replace("\\", "/")
                        if rel_path not in mentioned_files:
                            mentioned_files.append(rel_path)
                            if len(mentioned_files) >= MAX_MENTIONED:
                                break
                if len(mentioned_files) >= MAX_MENTIONED:
                    break
    except Exception:
        pass
    return mentioned_files


def render_user_text_with_files(fm: FileManager, user_text: str,
                                mentioned_files: list[str]) -> str:
    """Verbatim port of the injection/rendering block."""
    user_text_with_files = user_text
    if mentioned_files:
        target_files_content = f"\n\n[✅ تم قراءة {len(mentioned_files)} ملف من المشروع — المحتوى الفعلي مرفق أدناه]:"
        for f_path in mentioned_files[:MAX_MENTIONED]:
            try:
                content = fm.read_file(f_path, with_line_numbers=True)
                target_files_content += f"\n\n📄 **ملف: {f_path}** ({len(content)} حرف)\n```\n{content}\n```"
            except Exception:
                pass
        user_text_with_files = user_text + target_files_content
    return user_text_with_files


def collect_legacy_context(project_root: pathlib.Path, user_text: str) -> dict:
    """Full legacy pipeline → normalized, JSON-serialisable snapshot."""
    fm = FileManager(str(project_root))
    mentioned = collect_mentioned_files(fm, user_text)
    rendered = render_user_text_with_files(fm, user_text, mentioned)

    try:
        project_context = fm.get_project_context()
    except Exception:
        project_context = ""

    root_str = str(fm.root)
    return {
        "message": user_text,
        "mentioned_files": mentioned,
        "user_text_with_files": rendered.replace(root_str, ROOT_TOKEN),
        "project_context": project_context.replace(root_str, ROOT_TOKEN),
    }


# ═══════════════════ scenarios (T-017: the 6 representatives) ═══════════════

def _setup_huge_file(root: pathlib.Path) -> None:
    """>MAX_FILE_SIZE (500KB) file: mentioned by rglob, read_file raises."""
    line = "export const filler_%06d = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx';\n"
    big = "".join(line % i for i in range(9000))   # ~63 bytes × 9000 ≈ 553KB
    (root / "src" / "big_data.js").write_text(big, encoding="utf-8")


def _setup_arabic_file(root: pathlib.Path) -> None:
    (root / "src" / "وحدة_المصادقة.py").write_text(
        "def تحقق_من_المستخدم(اسم, كلمة_السر):\n"
        "    \"\"\"مصادقة تجريبية للـ fixture.\"\"\"\n"
        "    return bool(اسم) and len(كلمة_السر) >= 8\n",
        encoding="utf-8",
    )


SCENARIOS: dict[str, dict] = {
    "mention_only": {
        "description": "اسم ملف صريح بامتداده — مسار الـ exact-match فقط.",
        "message": "اقرأ config.json وقولي ايه المشكلة",
        "setup": None,
    },
    "keyword_only": {
        "description": "كلمة مفتاحية بلا امتداد — مسار الـ stem-match المرن.",
        "message": "فيه مشكلة في database",
        "setup": None,
    },
    "mixed": {
        "description": "مسار فرعي صريح + كلمة مفتاحية معًا — المساران يتعاونان.",
        "message": "قارن بين src/app.js و auth بالتفصيل",
        "setup": None,
    },
    "no_context": {
        "description": "رسالة عامة لا تطابق أي ملف — لا حقن، النص كما هو.",
        "message": "اشرح لي مفهوم الـ closures في جافاسكريبت",
        "setup": None,
    },
    "huge_file": {
        "description": ("ملف أكبر من MAX_FILE_SIZE: يُذكر في القائمة لكن "
                        "read_file يفشل بصمت — العنوان يدّعي القراءة بلا محتوى "
                        "(quirk مقصود تثبيته)."),
        "message": "افتح big_data.js وشوف المشكلة",
        "setup": _setup_huge_file,
    },
    "arabic_filename": {
        "description": "اسم ملف عربي بامتداده — \\w في re يلتقط العربية.",
        "message": "حدث وحدة_المصادقة.py وأضف تحقق",
        "setup": _setup_arabic_file,
    },
}
