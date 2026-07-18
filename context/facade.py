# -*- coding: utf-8 -*-
"""facade (R-201 / T-019): نداء واحد يعوّض كتلة server.py المضمّنة.

``gather_message_context(project_root, user_text)`` يعيد بالضبط الثلاثية
التي كانت الكتلة القديمة تنتجها (عقد goldens T-017):

- ``mentioned_files``  — exact-matches أولًا ثم stem-matches، بلا تكرار،
  بحد إجمالي واحد (``MAX_MENTIONED_FILES`` الصادق).
- ``user_text_with_files`` — الرسالة + حقن legacy الحرفي
  (``render_legacy_injection``: العنوان يعدّ كل المذكور، والمحتوى المتعذر
  يُتخطى بصمت — huge-file quirk).
- ``project_context`` — مخرجات ``get_project_context()`` (StructureSource).

الترتيب [Mention → Keyword → Structure] + path-dedupe هنا يعيدان إنتاج
سلوك الكتلة القديمة بمسح نظام ملفات **واحد** بدل rglob لكل كلمة.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from context.engine import ContextEngine, ContextItem, ContextRequest
from context.sources.keyword import KeywordSource
from context.sources.mention import (
    MAX_MENTIONED_FILES,
    MentionSource,
    render_legacy_injection,
)
from context.sources.structure import STRUCTURE_PATH, StructureSource


@dataclass(frozen=True)
class MessageContext:
    """ما كانت الكتلة المضمّنة تنتجه — بنفس الدلالات حرفيًا."""
    mentioned_files: list[str]
    user_text_with_files: str
    project_context: str


def _default_engine() -> ContextEngine:
    return ContextEngine([MentionSource(), KeywordSource(), StructureSource()])


def gather_message_context(project_root: str | pathlib.Path, user_text: str,
                           engine: ContextEngine | None = None,
                           max_files: int = MAX_MENTIONED_FILES) -> MessageContext:
    """النداء الوحيد الذي يحتاجه معالج WS (معيار قبول T-019)."""
    eng = engine or _default_engine()
    bundle = eng.gather(ContextRequest(
        message=user_text,
        project_root=pathlib.Path(project_root),
    ))

    # exact (mention) أولًا ثم stem (keyword) — dedupe بالمسار + حد إجمالي،
    # نفس دلالات المرور المزدوج في الكتلة القديمة.
    file_items: list[ContextItem] = []
    seen: set[str] = set()
    for item in bundle.items:
        if item.source_kind not in ("mention", "keyword"):
            continue
        if item.path in seen:
            continue
        seen.add(item.path)
        file_items.append(item)
        if len(file_items) >= max_files:
            break

    structure = ""
    for item in bundle.items:
        if item.source_kind == "structure" and item.path == STRUCTURE_PATH:
            structure = item.content or ""
            break

    return MessageContext(
        mentioned_files=[it.path for it in file_items],
        user_text_with_files=render_legacy_injection(user_text, file_items),
        project_context=structure,
    )
