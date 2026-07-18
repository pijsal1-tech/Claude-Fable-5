# -*- coding: utf-8 -*-
"""T-020 (R-201): capture harness for the legacy ContextBuilder path.

يثبّت — قبل التقارب مع ContextEngine — كل ما ينتجه مسار الـ chain:

1. ``ContextBuilder.gather()``: قائمة العناصر (kind/source/success/size/content).
2. ``on_progress`` events: نفس التسلسل الذي يترجمه ``AgentLoop._auto_prefetch``
   إلى إطارات WS (``agent_step`` بـ ``tool=f"auto_{kind}"``).
3. ``get_summary()``: مصدر نص إطار الملخص ``tool="auto_prefetch"``.
4. ``build_prompt_section()``: النص الذي يراه الموديل في مسار CLI
   (``gather_context``).

بعد T-020، أي refactor يجب أن يعيد إنتاج هذه الـ goldens بايت-بايت —
نفس عقد parity الذي طبّقته goldens T-017 على كتلة server.py.

⚠️ إصلاحات حتمية (ORDER-only، موثقة في T-020 مثل نظيراتها في T-017):
``sorted()`` أُضيفت في context_builder على iterdir/rglob لأن ترتيب
نظام الملفات غير حتمي عبر المنصات — المجموعة نفسها لم تتغير.
"""
from __future__ import annotations

import pathlib

from chain.context_builder import ContextBuilder

ROOT_TOKEN = "<ROOT>"


def collect_builder_snapshot(project_root: pathlib.Path,
                             user_request: str) -> dict:
    """تشغيل ContextBuilder كاملًا → snapshot قابل للتسلسل JSON."""
    progress_events: list[list[str]] = []

    def _on_progress(kind: str, source: str, status: str) -> None:
        progress_events.append([kind, source, status])

    builder = ContextBuilder(str(project_root), on_progress=_on_progress)
    result = builder.gather(user_request)
    prompt_section = result.build_prompt_section(max_total=50000)

    root_str = str(builder.root)

    def _norm(text: str) -> str:
        return text.replace(root_str, ROOT_TOKEN)

    return {
        "message": user_request,
        "items": [
            {
                "kind": it.kind,
                "source": it.source,
                "success": it.success,
                "size": it.size,
                "content": _norm(it.content),
            }
            for it in result.items
        ],
        "progress_events": progress_events,
        "summary": result.get_summary(),
        "prompt_section": _norm(prompt_section),
    }


# ═══════════════ scenarios (T-020: مسارات ContextBuilder الأربعة) ═══════════════

def _setup_deps_file(root: pathlib.Path) -> None:
    """dep-file branch في _gather_project_overview (الـ fixture بلا deps)."""
    (root / "requirements.txt").write_text(
        "flask==3.0.0\nrequests>=2.31\n", encoding="utf-8"
    )


SCENARIOS: dict[str, dict] = {
    "mention_file": {
        "description": "اسم ملف صريح → _gather_mentioned_files يقرأه.",
        "message": "اقرأ config.json وقولي ايه المشكلة",
        "setup": None,
    },
    "mention_dir": {
        "description": ("مجلد مذكور → listing + قراءة تلقائية لملفات الكود "
                        "داخله (بترتيب مفروز)."),
        "message": "اعرض مجلد src وحلل الملفات",
        "setup": None,
    },
    "general_overview": {
        "description": "طلب عام بلا ملفات/مجلدات → شجرة + README (+deps لو وجدت).",
        "message": "اشرح المشروع",
        "setup": None,
    },
    "overview_with_deps": {
        "description": "نفس الطلب العام مع requirements.txt → فرع الـ deps يعمل.",
        "message": "حلل هيكل المشروع",
        "setup": _setup_deps_file,
    },
    "code_search": {
        "description": "اسم دالة بالعربي → _gather_code_searches يبحث نصيًا.",
        "message": "فين دالة hash_password وامتى بتتنادى",
        "setup": None,
    },
    "no_context": {
        "description": "رسالة لا تطابق شيئًا → نتيجة فارغة وقسم prompt فارغ.",
        "message": "ايه رايك نبدأ نكتب اختبارات اكتر",
        "setup": None,
    },
}
