# -*- coding: utf-8 -*-
"""ContextBundle (R-202 / T-021): حاوية سياق بلا تكرار محتوى + provenance.

المشكلة (roadmap R-202): نفس محتوى الملف كان يُحقن أكثر من مرة في
البرومبت (mention + keyword يقرآن نفس الملف؛ map_reduce يعيد تضمين كل
الملفات؛ الـ Knowledge يعيد الحقن كل iteration) — هدر توكنز مضاعف وغير
قابل للرصد.

الحل هنا:
- كل عنصر يُفتاح بـ **sha256 لمحتواه** إضافة لمفتاح الهوية
  ``(source_kind, path)``.
- أول حامل لمحتوى معين يملك «الجسد»؛ أي إدخال لاحق بنفس الـ hash يُقبل
  لكن كـ **reference** (``is_reference=True`` + ``duplicate_of``) —
  الـ renderer يطبع الجسد مرة واحدة وملاحظة إحالة للبقية.
- provenance كامل لكل عنصر (``BundleEntry``): من أي مصدر جاء، hash
  محتواه، هل هو إحالة ولمن — قابل للفحص عبر ``debug_dump()``.

عقد الـ parity: ``items`` / ``paths`` / ``__len__`` / ``add`` (بمفتاح
الهوية) بنفس دلالات T-018 حرفيًا — الـ facade وgoldens T-017 لا تتأثر
(الإحالة تحتفظ بالـ ``ContextItem`` كاملًا بمحتواه؛ فقط الـ renderer
الجديد هو من يستبدل الجسد المكرر بملاحظة).

huge-file quirk محفوظ: ``content=None`` لا يُهَش أبدًا ولا يكون إحالة.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable


# ═══════════════════════════ نموذج البيانات ═══════════════════════════

@dataclass(frozen=True)
class ContextItem:
    """عنصر سياق واحد بمصدر معروف (provenance).

    content=None = العنصر مذكور لكن محتواه غير متاح (مثل ملف أكبر من
    MAX_FILE_SIZE — راجع quirk الـ huge_file المثبّت في goldens T-017).
    """
    source_kind: str
    path: str
    content: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.source_kind, self.path)


def content_hash(text: str) -> str:
    """sha256 hex لمحتوى نصي — مفتاح دلالة «نفس الجسد»."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


@dataclass(frozen=True)
class BundleEntry:
    """عنصر + provenance داخل الحزمة (T-021).

    - ``content_hash``: sha256 للمحتوى (None = بلا محتوى / huge-file).
    - ``is_reference``: True = الجسد موجود عند عنصر سابق — لا يُطبع ثانية.
    - ``duplicate_of``: مسار العنصر الحامل للجسد (قد يكون نفس المسار لو
      نفس الملف جاء من مصدرين — mention ثم keyword).
    """
    item: ContextItem
    content_hash: str | None
    is_reference: bool = False
    duplicate_of: str | None = None


# ═══════════════════════════ الحاوية ═══════════════════════════

class ContextBundle:
    """حاوية مرتّبة بلا تكرار — هوية **ومحتوى** (T-021).

    مستويا الـ dedupe:
    1. هوية ``(source_kind, path)``: الإضافة الأولى تكسب، المكرر يُرفض
       (``add`` ترجع False) — نفس دلالات T-018.
    2. محتوى (sha256): إدخال بمفتاح هوية جديد لكن بجسد سبق تخزينه
       يُقبل كـ reference — يظهر في ``items``/``paths`` (عقد الـ facade)
       لكن ``render_prompt_block`` يطبع ملاحظة إحالة بدل الجسد.
    """

    def __init__(self) -> None:
        self._entries: list[BundleEntry] = []
        self._seen_keys: set[tuple[str, str]] = set()
        self._hash_owner: dict[str, str] = {}   # content_hash → مسار حامل الجسد
        # TSK-609 (PM-04 §R6): توقيت collect لكل مصدر بالميلي ثانية —
        # يملؤه ContextEngine.gather؛ حقل رصد إضافي بحت (لا يؤثر على
        # الهوية/المحتوى/الترتيب — عقود T-018/T-021 محفوظة بالبناء).
        self.source_timings_ms: dict[str, int] = {}

    def add(self, item: ContextItem) -> bool:
        """إضافة عنصر. False لو مكرر الهوية (لم يُضف).

        تكرار المحتوى (hash موجود) لا يمنع الإضافة — يسجَّل reference.
        """
        if item.key in self._seen_keys:
            return False
        self._seen_keys.add(item.key)

        h: str | None = None
        is_ref = False
        dup_of: str | None = None
        if item.content is not None:
            h = content_hash(item.content)
            owner = self._hash_owner.get(h)
            if owner is not None:
                is_ref = True
                dup_of = owner
            else:
                self._hash_owner[h] = item.path

        self._entries.append(BundleEntry(
            item=item, content_hash=h,
            is_reference=is_ref, duplicate_of=dup_of,
        ))
        return True

    def extend(self, items: Iterable[ContextItem]) -> int:
        """إضافة عدة عناصر؛ يرجع عدد ما أُضيف فعلًا."""
        return sum(1 for it in items if self.add(it))

    # ── واجهة T-018 (عقد الـ facade — بلا تغيير) ──

    @property
    def items(self) -> list[ContextItem]:
        return [e.item for e in self._entries]

    def paths(self, source_kind: str | None = None) -> list[str]:
        """مسارات العناصر بالترتيب — كلها أو لمصدر محدد."""
        return [
            e.item.path for e in self._entries
            if source_kind is None or e.item.source_kind == source_kind
        ]

    def __len__(self) -> int:
        return len(self._entries)

    # ── provenance + rendering (T-021) ──

    @property
    def entries(self) -> list[BundleEntry]:
        """العناصر مع provenance كاملة — بترتيب الإدخال."""
        return list(self._entries)

    def render_prompt_block(self, max_item_len: int = 8000) -> str:
        """بناء بلوك البرومبت: **كل جسد مرة واحدة**، المكرر ملاحظة إحالة.

        العناصر بلا محتوى (huge-file) تُتخطى — نفس quirk حقن legacy.
        """
        if not self._entries:
            return ""
        parts: list[str] = []
        for e in self._entries:
            it = e.item
            if it.content is None:
                continue
            if e.is_reference:
                parts.append(
                    f"📎 [{it.source_kind}: {it.path}] — المحتوى مطابق "
                    f"لملف مرفق أعلاه ({e.duplicate_of})، لم يُكرَّر."
                )
                continue
            body = it.content[:max_item_len]
            if len(it.content) > max_item_len:
                body += f"\n... (مقطوع — {len(it.content)} حرف إجمالي)"
            parts.append(f"📄 [{it.source_kind}: {it.path}]:\n{body}")
        return "\n\n".join(parts)

    def debug_dump(self) -> list[dict]:
        """provenance dump للتشخيص: «ليه الموديل شاف X؟».

        الاستخدام:
            for row in bundle.debug_dump():
                print(row)   # index/source_kind/path/hash/chars/reference

        كل صف JSON-serializable — يصلح للـ logging المباشر.
        """
        return [
            {
                "index": i,
                "source_kind": e.item.source_kind,
                "path": e.item.path,
                "content_hash": e.content_hash,
                "chars": (len(e.item.content)
                          if e.item.content is not None else None),
                "is_reference": e.is_reference,
                "duplicate_of": e.duplicate_of,
            }
            for i, e in enumerate(self._entries)
        ]
