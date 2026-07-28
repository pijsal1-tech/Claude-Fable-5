# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ignore_rules — قائمة التجاهل الموحّدة للمشروع
  TSK-202 (BUG-04 + NF-23(4)) — بوابة QA-T09
═══════════════════════════════════════════════════════

المصدر الوحيد للحقيقة لمجلدات التجاهل عبر كل مواقع
الفحص/المسح (file_manager, bridge, agent_tools).

BUG-04: مجلد `test---results` (بثلاث شرطات — مخرجات تقييم QA)
كان يتسرب إلى المسح والبحث لأن القوائم المكررة لم تشمله.
NF-23(4): توحيد القوائم المكررة في مصدر واحد.

القاعدة: المجموعة = قائمة actions/file_manager.py:IGNORE_DIRS
∪ قائمة chain/bridge.py:_IGNORE_DIRS
∪ {"test---results", "test-results", ".ai_runs", ".webdev_backups"}.

لا imports هنا إطلاقًا — الوحدة ورقة (leaf) لتجنب أي دورة استيراد.
"""

IGNORED_DIRS = frozenset({
    # ── من actions/file_manager.py (القائمة الأصلية) ──
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", ".cache", ".vscode", ".idea",
    "venv", ".venv", "env", ".env",
    # ── من chain/bridge.py (الإضافات الخاصة بها) ──
    ".tox", "target", "bin", "obj", ".gradle",
    # ── إضافات TSK-202 الإلزامية (BUG-04) ──
    "test---results", "test-results", ".ai_runs", ".webdev_backups",
})


def is_ignored_dir(name: str) -> bool:
    """هل اسم المجلد ضمن قائمة التجاهل الموحّدة؟ (مطابقة اسم حرفية)"""
    return name in IGNORED_DIRS
