# -*- coding: utf-8 -*-
"""MentionSource (R-201 / T-018): الملفات المذكورة صراحةً في الرسالة.

نقل سلوك كتلة legacy المثبّت في goldens T-017 — لكن على **قائمة المسح
الواحدة** بدل rglob لكل كلمة:

- legacy: لكل اسم كامل ``rglob(basename)`` + لكل جذع ``rglob(f"*{stem}*")``
  ⇒ O(files × words) مشيات شجرية لكل رسالة.
- هنا: فلترة في الذاكرة على ``scan.files`` (المفروزة) — صفر مشيات إضافية.

المطابقة مكافئة تمامًا: نمط ``rglob(X)`` يطابق **اسم** الملف الأخير، ففلترة
القائمة المفروزة عالميًا بنفس المعيار تعطي نفس مجموعة وترتيب
``sorted(rglob(X))`` الذي ثبّتته goldens T-017.

كل quirks الـ legacy محفوظة عمدًا (عقد الـ parity):
- لا فلترة ملفات سرية ولا فحص حجم في مرحلة الـ mention نفسها؛ ملف أكبر من
  ``MAX_FILE_SIZE`` يُذكر لكن قراءته تفشل بصمت ⇒ ``content=None``
  (quirk الـ huge_file المثبّت).
- قائمة الاستبعاد حرفيًا: ``('the', 'and', 'for', 'من', 'في', 'على')``.
- ``\\w`` في الـ regex يلتقط أسماء الملفات العربية.
"""
from __future__ import annotations

import re

from actions.file_manager import MAX_FILE_SIZE, WEB_EXTENSIONS
from context.engine import ContextItem, ContextRequest, ProjectScan
from context.safe_reader import SafeReader

# T-018: إصلاح الثابت الكاذب.
# legacy: ``MAX_MENTIONED = 100  # حد أقصى 10 ملفات`` — الكود يقول 100
# والتعليق يدّعي 10. القصد الأصلي (والمعقول لحجم البرومبت) هو 10:
# عشرة ملفات كاملة بمحتواها المرقّم حدٌ سخي لرسالة واحدة، و100 كان
# يعني إغراق البرومبت. الحد الآن **10 فعلًا** والتعليق صادق.
# ملاحظة parity: كل goldens T-017 تتضمن ≤2 ملف، فالتخفيض لا يغيّر أيًا منها.
MAX_MENTIONED_FILES = 10

_STOPWORDS = ('the', 'and', 'for', 'من', 'في', 'على')

_WORD_RE = re.compile(r'[\w\-/\\]+(?:\.[\w]+)?')
_SUBPATH_RE = re.compile(r'[\w\-]+/[\w\-]+(?:\.[\w]+)?')


def extract_search_terms(message: str) -> tuple[set[str], set[str]]:
    """استخراج (أسماء كاملة، جذوع) من الرسالة — حرفي من legacy."""
    words = _WORD_RE.findall(message)
    subpaths = _SUBPATH_RE.findall(message)

    exact_names: set[str] = set()
    stems: set[str] = set()

    for w in words + subpaths:
        if '.' in w:
            exact_names.add(w.replace('\\', '/'))
            stem_w = w.split('.')[0].split('/')[-1]
        else:
            stem_w = w.split('/')[-1]

        if len(stem_w) >= 3 and not stem_w.isdigit() and stem_w not in _STOPWORDS:
            stems.add(stem_w)

    return exact_names, stems


def _number_lines(text: str) -> str:
    """ترقيم الأسطر — حرفيًا نفس ``FileManager.read_file`` (عقد goldens
    T-017: نفس المحاذاة ``{i+1:>{width}}: `` ونفس "" للملف الفارغ)."""
    lines = text.splitlines()
    width = len(str(len(lines)))
    return "\n".join(f"{i + 1:>{width}}: {line}"
                     for i, line in enumerate(lines))


def build_items(scan: ProjectScan, paths: list[str],
                kind: str) -> list[ContextItem]:
    """قراءة المحتوى المرقّم لكل مسار — عبر **SafeReader** (T-026 / R-204):
    الملف السري يصل كـ stub حجب (بلا ترقيم)، وفشل القراءة = content=None
    (huge-file quirk المثبّت — ``max_file_size=MAX_FILE_SIZE`` يحفظ نفس
    سقف legacy البالغ 500KB بايت-بايت). مشترك بين Mention/Keyword (T-019)."""
    reader = SafeReader(scan.root, max_file_size=MAX_FILE_SIZE)
    items: list[ContextItem] = []
    for rel_path in paths:
        result = reader.read_text(rel_path)
        content: str | None
        if result.redacted:
            # stub الحجب يمر كما هو — بلا ترقيم أسطر (ليس "محتوى ملف")
            content = result.content
        elif result.ok and result.content is not None:
            content = _number_lines(result.content)
        else:
            # not_found / too_large / policy / read_error — نفس تسامح
            # legacy: content=None يُتخطى بصمت في الحقن
            content = None
        items.append(ContextItem(source_kind=kind, path=rel_path,
                                 content=content))
    return items


class MentionSource:
    """مصدر الملفات المذكورة صراحةً — مسار الـ **exact-name** فقط.

    T-019: مسار الـ stem المرن انتقل إلى ``KeywordSource`` — التركيبة
    [MentionSource, KeywordSource] بالترتيب + path-dedupe في الـ facade
    تعيد إنتاج قائمة legacy (exact ثم stem) حرفيًا.
    """

    kind = "mention"

    def __init__(self, max_files: int = MAX_MENTIONED_FILES) -> None:
        self._max_files = max_files

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        exact_names, _stems = extract_search_terms(request.message)

        mentioned: list[str] = []
        # البحث بالاسم الكامل أو المسار الفرعي (يطابق rglob(basename))
        for name in sorted(exact_names):
            basename = name.split('/')[-1] if '/' in name else name
            for p in scan.files:
                if p.name == basename and p.suffix in WEB_EXTENSIONS:
                    rel_path = scan.rel(p)
                    if rel_path not in mentioned:
                        mentioned.append(rel_path)
                        if len(mentioned) >= self._max_files:
                            break
            if len(mentioned) >= self._max_files:
                break

        return build_items(scan, mentioned, self.kind)


def render_legacy_injection(message: str, items: list[ContextItem]) -> str:
    """قالب حقن legacy حرفيًا — يعيد إنتاج ``user_text_with_files``.

    يُستخدم في اختبارات الـ parity الآن، وفي التوصيل الفعلي لاحقًا
    (المهام التالية من R-201) حتى يظل ما يراه الموديل بايت-بايت كما هو.
    العناصر بلا محتوى تُتخطى بصمت — نفس quirk العنوان الكاذب للـ huge_file.
    """
    if not items:
        return message
    target = f"\n\n[✅ تم قراءة {len(items)} ملف من المشروع — المحتوى الفعلي مرفق أدناه]:"
    for item in items:
        if item.content is None:
            continue
        target += (f"\n\n📄 **ملف: {item.path}** ({len(item.content)} حرف)"
                   f"\n```\n{item.content}\n```")
    return message + target
