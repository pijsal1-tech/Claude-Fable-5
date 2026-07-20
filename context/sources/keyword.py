# -*- coding: utf-8 -*-
"""KeywordSource (R-201 / T-019): مطابقة الجذوع المرنة (stem-match).

النصف الثاني من كتلة legacy: كلمات الرسالة بلا امتداد (≥3 أحرف، ليست
أرقامًا ولا stopwords) تُطابَق كجذوع ضد **أسماء** الملفات — مكافئ
``rglob(f"*{stem}*")`` لكن فلترة في الذاكرة على ``scan.files``.

الترتيب في التركيبة القياسية ``[MentionSource, KeywordSource]`` مع
path-dedupe في الـ facade يعيد إنتاج قائمة legacy حرفيًا
(exact-matches أولًا ثم stem-matches، بلا تكرار، بحد إجمالي واحد).
"""
from __future__ import annotations

from actions.file_manager import WEB_EXTENSIONS
from context.engine import ContextItem, ContextRequest, ProjectScan
from context.sources.mention import (
    MAX_MENTIONED_FILES,
    build_items,
    extract_search_terms,
)


class KeywordSource:
    """مصدر الكلمات المفتاحية — stem-match المرن على أسماء الملفات."""

    kind = "keyword"

    def __init__(self, max_files: int = MAX_MENTIONED_FILES) -> None:
        self._max_files = max_files

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        _exact_names, stems = extract_search_terms(request.message)

        matched: list[str] = []
        # البحث بالجذع للماتش المرن — T-049: عبر ``scan.lookup_stem``
        # (مسح ذاكرة على الأسماء في الفهرس) بدل المسح الخطي المباشر.
        # النتائج بالترتيب العالمي المفروز — نفس ترتيب legacy تمامًا.
        for stem in sorted(stems):
            for p in scan.lookup_stem(stem):
                if p.suffix in WEB_EXTENSIONS:
                    rel_path = scan.rel(p)
                    if rel_path not in matched:
                        matched.append(rel_path)
                        if len(matched) >= self._max_files:
                            break
            if len(matched) >= self._max_files:
                break

        return build_items(scan, matched, self.kind)
