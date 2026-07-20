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
from typing import Any

from context.engine import ContextEngine, ContextItem, ContextRequest
from context.sources.keyword import KeywordSource
from context.sources.mention import (
    MAX_MENTIONED_FILES,
    MentionSource,
    render_legacy_injection,
)
from context.semantic_source import SemanticSource
from context.sources.structure import STRUCTURE_PATH, StructureSource
from context.sources.symbol import SymbolSource


def _app_config() -> dict:
    """قراءة config.yaml من جذر التطبيق — تسامحية (فشل ⇒ {}).

    T-057: علم ``context.semantic`` يعيش في config.yaml بجوار الحزمة
    (نفس الملف الذي يقرؤه server._read_config — جذر التطبيق هو أبو
    مجلد context/). القراءة عبر **SafeReader** — بوابة R-204 هي مسار
    القراءة الوحيد داخل context/ (بوابة grep في check.sh)، وتسامحها
    المرصود (فشل/حجب ⇒ لا محتوى) هو نفس دلالة "فشل ⇒ {}" هنا.
    """
    try:
        import yaml
        from context.safe_reader import SafeReader
        app_root = pathlib.Path(__file__).resolve().parent.parent
        reader = SafeReader(app_root)
        result = reader.read_text("config.yaml")
        if not result.ok or result.content is None or result.redacted:
            return {}
        loaded = yaml.safe_load(result.content)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


@dataclass(frozen=True)
class MessageContext:
    """ما كانت الكتلة المضمّنة تنتجه — بنفس الدلالات حرفيًا."""
    mentioned_files: list[str]
    user_text_with_files: str
    project_context: str


def _default_engine(index: Any = None,
                    memory_source: Any = None) -> ContextEngine:
    """التركيبة القياسية — T-049: مع فهرس اختياري (R-702).

    إذا مُرّر ``index`` (ProjectIndex من ``ProjectHandle.index``) يصبح
    الـ scan_factory هو ``index.scan()`` — sweep طزاجة + صفر مشيات
    شجرية. بدونه (مسارات الاختبارات/ctx-less) يبقى ProjectScan.
    """
    # T-056 (R-205): SymbolSource بعد Keyword وقبل Structure — عناصره
    # بمسارات رمزية <symbol:...> فلا تدخل قائمة mentioned_files (الـ
    # facade يرشّح mention/keyword فقط) ⇒ goldens T-017 غير متأثرة.
    # T-057 (R-206): SemanticSource بعد Symbol — مساراته <semantic:...>
    # رمزية كذلك؛ العلم context.semantic.enabled (config.yaml) يوقفه
    # نظيفًا؛ المهلة الصارمة تضمن ألا يعطّل الرد أبدًا.
    sources: list = [MentionSource(), KeywordSource(), SymbolSource(),
                     SemanticSource.from_config(_app_config()),
                     StructureSource()]
    # T-105 (R-802): MemorySource اختياري — يُحقن بطبقتي جلسة حيّة
    # (حلقي + دلالي) من المستدعي؛ غيابه (الافتراضي) = التركيبة
    # القديمة بايت-بايت (goldens T-017 محفوظة بالبناء). مساراته
    # <memory:...> رمزية فلا تدخل mentioned_files بنفس القاعدة.
    if memory_source is not None:
        sources.insert(len(sources) - 1, memory_source)
    if index is not None:
        return ContextEngine(sources, scan_factory=lambda _root: index.scan())
    return ContextEngine(sources)


def gather_message_context(project_root: str | pathlib.Path, user_text: str,
                           engine: ContextEngine | None = None,
                           max_files: int = MAX_MENTIONED_FILES,
                           index: Any = None,
                           memory_source: Any = None) -> MessageContext:
    """النداء الوحيد الذي يحتاجه معالج WS (معيار قبول T-019).

    T-049: مرّر ``index=sctx.project.index`` لاستعلام الفهرس المقلوب
    بدل مشية شجرية لكل رسالة. ``engine`` الصريح يتقدّم على الفهرس.
    T-105: ``memory_source`` (MemorySource محقون بطبقتي الجلسة) يُضاف
    للتركيبة عند تمريره — الافتراضي None = السلوك القديم حرفيًا."""
    eng = engine or _default_engine(index, memory_source=memory_source)
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
