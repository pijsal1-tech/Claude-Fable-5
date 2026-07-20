# -*- coding: utf-8 -*-
"""SymbolSource (R-205 / T-056): سياق رمزي فوق SymbolIndex.

يحوّل فهرس T-055 إلى جودة برومبت فعلية: مصطلحات الرسالة تُحل إلى
**تعريفات** (أين عُرّف X؟) و**مواقع الاستدعاء** (من ينادي X؟)
و**سياق الاستيرادات** (ماذا يستورد الملف المذكور؟) — بدقة نحوية بدل
ضجيج مطابقة النصوص.

## ما يُصدره المصدر (عناصر بمسارات رمزية — لا تتنكر كملفات)

| العنصر                       | المحتوى                                  |
|------------------------------|------------------------------------------|
| ``<symbol:definition:X>``    | أسطر ``rel:line kind X`` لكل تعريف       |
| ``<symbol:callers:X>``       | أسطر ``rel:line`` لكل موقع استدعاء       |
| ``<symbol:imports:rel>``     | استيرادات الملف المذكور، سطرًا لكل وحدة  |

## fallback (معيار قبول T-056)

ملف بلا بيانات رموز (امتداد غير مدعوم / مكتبة غائبة / حجب سري /
تحليل فاشل) ⇒ المصدر **لا يُصدر شيئًا عنه** — يبقى مغطى بسلوك
``KeywordSource`` القائم في التركيبة القياسية. أي أن التدهور =
"نفس مخرجات keyword حرفيًا" لا "خطأ" ولا "ضجيج بديل".

## الطبقة (tier) — التزام الميزانية

عناصر الرموز تُحزم بطبقة ``SYMBOL_TIER = "high"`` عند تمريرها لـ
``ContextBudget`` (دلالة "مرجّح الحاجة بشدة" — راجع context/budget.py).
``must_have`` لا تُزاح أبدًا مهما تضخمت عناصر الرموز — هذا عقد
الميزانية نفسه، ومثبَّت باختبار امتثال في test_symbol_source.py.

## الطزاجة والتكلفة

فهرس SymbolIndex **مشترك لكل جذر عبر الرسائل** (module-level state —
المحرّك يُبنى لكل رسالة في الـ facade فلا يصلح التخزين على المصدر).
الطزاجة بحارس stat لكل collect: توقيع ``(mtime_ns, size)`` لكل ملف
مدعوم؛ تغيُّر/ملف جديد ⇒ ``notify_write`` (إبطال كسول)؛ ملف محذوف ⇒
إبطال + إسقاط الأثر. تكلفة stat لآلاف الملفات ميلي-ثوانٍ؛ إعادة
التحليل تلمس المتغير فقط (كاش T-055).

## الحدود الصادقة

- ``MAX_SYMBOL_FILES = 2000``: سقف الملفات المفهرسة لكل جذر — نفس
  حجم عيّنة أداء T-055 (≤10s بناء أول، ~0 بعده).
- ``MAX_SYMBOL_ITEMS = 12``: سقف عناصر السياق لكل رسالة.
- ``MAX_HITS_PER_ITEM = 20``: سقف الأسطر داخل العنصر الواحد.

قواعد AUTHORING.md ملتزَمة: لا مشي شجري (نعمل على ``scan.files``)،
provenance ثابت (``kind = "symbol"``)، حتمية (كل تكرار مفروز)،
لا استثناءات للمستهلك.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from context.engine import ContextItem, ContextRequest, ProjectScan
from context.sources.mention import extract_search_terms
from context.symbol_index import SymbolIndex

#: طبقة ميزانية عناصر الرموز (T-056) — "مرجّح الحاجة بشدة".
#: ``must_have`` لا تُزاح أبدًا (عقد ContextBudget — مثبَّت اختبارًا).
SYMBOL_TIER = "high"

MAX_SYMBOL_FILES = 2000   # سقف الملفات المفهرسة لكل جذر (حجم عيّنة T-055)
MAX_SYMBOL_ITEMS = 12     # سقف عناصر السياق الرمزي لكل رسالة
MAX_HITS_PER_ITEM = 20    # سقف الأسطر داخل العنصر الواحد

DEFINITION_PATH = "<symbol:definition:{term}>"
CALLERS_PATH = "<symbol:callers:{term}>"
IMPORTS_PATH = "<symbol:imports:{rel}>"


# ═══════════════════ الحالة المشتركة لكل جذر ═══════════════════

@dataclass
class _RootState:
    """فهرس + توقيعات stat لجذر واحد — يعيش عبر الرسائل."""
    index: SymbolIndex
    seen: dict[str, tuple[int, int]] = field(default_factory=dict)


_STATES: dict[str, _RootState] = {}


def reset_symbol_state() -> None:
    """تفريغ الحالة المشتركة — عزل الاختبارات (لا يُستدعى إنتاجيًا)."""
    _STATES.clear()


def _state_for(root: pathlib.Path) -> _RootState:
    key = str(root)
    state = _STATES.get(key)
    if state is None:
        state = _RootState(index=SymbolIndex(root))
        _STATES[key] = state
    return state


# ═══════════════════ المصدر ═══════════════════

class SymbolSource:
    """مصدر السياق الرمزي — تعريفات/مستدعون/استيرادات عبر SymbolIndex.

    **ملاحظة ترتيب التركيبة:** يُسجَّل بعد ``KeywordSource`` وقبل
    ``StructureSource`` — مساراته الرمزية (``<symbol:...>``) لا تصطدم
    بمسارات الملفات، والـ facade يرشّح ``mention``/``keyword`` فقط
    لقائمة الملفات المذكورة ⇒ عقد goldens T-017 غير متأثر بندًا بندًا.
    """

    kind = "symbol"

    def __init__(self, max_files: int = MAX_SYMBOL_FILES,
                 max_items: int = MAX_SYMBOL_ITEMS,
                 max_hits: int = MAX_HITS_PER_ITEM) -> None:
        self._max_files = max_files
        self._max_items = max_items
        self._max_hits = max_hits

    # ── الطزاجة + الفهرسة ──

    def _refresh_and_index(self, state: _RootState,
                           scan: ProjectScan) -> None:
        """حارس stat: إبطال المتغير/الجديد/المحذوف ثم فهرسة كسولة."""
        supported: list[tuple[str, pathlib.Path]] = []
        for p in scan.files:                     # قائمة المسح — لا مشي شجري
            if SymbolIndex.language_for(p.name):
                supported.append((scan.rel(p), p))
                if len(supported) >= self._max_files:
                    break

        current: set[str] = set()
        for rel, p in supported:
            try:
                st = p.stat()
            except OSError:
                continue
            current.add(rel)
            sig = (st.st_mtime_ns, st.st_size)
            if state.seen.get(rel) != sig:
                state.index.notify_write(rel)    # إبطال — إعادة تحليل كسولة
                state.seen[rel] = sig
        for rel in [r for r in state.seen if r not in current]:
            state.index.notify_write(rel)        # ملف حُذف/خرج من السقف
            del state.seen[rel]

        state.index.index_files(sorted(current))

    # ── الجمع ──

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        if not SymbolIndex.available():
            return []                            # تدهور: لا مكتبة ⇒ لا عناصر

        state = _state_for(scan.root)
        self._refresh_and_index(state, scan)
        idx = state.index

        exact_names, stems = extract_search_terms(request.message)
        items: list[ContextItem] = []

        # 1) تعريفات + مستدعون — لكل جذع بترتيب مفروز (حتمية)
        for term in sorted(stems):
            if len(items) >= self._max_items:
                break
            defs = idx.lookup_definition(term)
            if defs:
                lines = [f"{rel}:{sym.line} {sym.kind} {sym.name}"
                         for rel, sym in defs[:self._max_hits]]
                items.append(ContextItem(
                    source_kind=self.kind,
                    path=DEFINITION_PATH.format(term=term),
                    content="\n".join(lines)))
            if len(items) >= self._max_items:
                break
            refs = idx.lookup_references(term)
            if refs:
                lines = [f"{rel}:{sym.line}"
                         for rel, sym in refs[:self._max_hits]]
                items.append(ContextItem(
                    source_kind=self.kind,
                    path=CALLERS_PATH.format(term=term),
                    content="\n".join(lines)))

        # 2) سياق استيرادات الملفات المذكورة بالاسم الكامل
        seen_rels: set[str] = set()
        for name in sorted(exact_names):
            if len(items) >= self._max_items:
                break
            basename = name.replace("\\", "/").split("/")[-1]
            for p in scan.lookup_name(basename):
                rel = scan.rel(p)
                if rel in seen_rels:
                    continue
                seen_rels.add(rel)
                table = idx.symbols_for(rel)
                if table.imports:                # ملف بلا رموز ⇒ لا عنصر
                    items.append(ContextItem(
                        source_kind=self.kind,
                        path=IMPORTS_PATH.format(rel=rel),
                        content="\n".join(table.imports[:self._max_hits])))
                if len(items) >= self._max_items:
                    break

        return items[:self._max_items]
