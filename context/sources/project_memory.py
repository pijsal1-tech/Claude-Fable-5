# -*- coding: utf-8 -*-
"""ProjectMemorySource (R-805 / T-113): ذاكرة المشروع كمصدر سياق مُدرَج بميزانية.

يُكمل R-805: مدخلات ``ProjectMemoryStore`` (T-112 — حقائق/أعراف/قرارات/
ملخصات runs عبر الجلسات) تدخل ContextEngine كمصدر عبر مقعد R-201
القياسي (``collect(request, scan) → items``) — الجلسة الثانية تجيب عن
سؤال الأعراف **من الذاكرة** بدل إعادة قراءة الملفات (بند القبول:
tool-call count أقل مع الذاكرة مفعّلة — مثبَّت اختبارًا).

**الطبقة (tier):** ``PROJECT_MEMORY_TIER = "opportunistic"`` **حصريًا**
— نفس قصر MemorySource (T-105) حرفيًا: «لو فيه مساحة»، أول ما يُسقطه
ContextBudget؛ الذاكرة المقترحة لا تزاحم طلب المستخدم أو ملفاته أبدًا.
(بوابة grep في الاختبارات: لا tier آخر يُذكر كقيمة في هذه الوحدة.)

**الاسترجاع:** تسجيل تداخل كلمات الاستعلام (طول ≥3، lower — نفس
``_WORD_RE`` من T-105) مع نص كل مدخلة — حتمي بلا موديل؛ الأعلى تداخلًا
فالأحدث، بحد ``MAX_ENTRIES``، بمسارات رمزية
``<memory:project:entry_id>`` لا تتنكر كملفات (facade يرشّح
``mention``/``keyword`` فقط لقائمة ``mentioned_files`` ⇒ goldens
T-017 غير متأثرة).

═══════════════ دلالات الـ staleness (بند القبول) ═══════════════

مدخلة رابطها (``index_hash``) يخالف بصمة الفهرس الحي = **قديمة**:

1. **تُعلَّم**: محتواها المصيَّر يبدأ بـ ``[STALE ...]`` — المستهلك
   (الموديل/اللوحة) يرى الحكم صراحة، **لا تُقدَّم كطازجة بصمت أبدًا**.
2. **تُنزَّل رتبتها**: كل القديمات بعد كل الطازجات مهما بلغ تداخلها —
   فتحت ضغط الحد (``MAX_ENTRIES``) أو الميزانية تسقط أولًا.
3. **لا تُحذف**: الحكم النهائي للمستخدم (لوحة الذاكرة — T-114).

الحكم عبر ``core.project_memory.is_stale`` (بصمة غائبة من أي طرف =
لا حكم ⇒ طازجة). ``index`` يُحقن في البناء — duck-typed.

**المهلة async fallback-to-skip:** كامل الاسترجاع (بما فيه قراءة
المخزن) في خيط عامل واحد بمهلة؛ تجاوز/أي فشل (وضمنه
``CorruptMemoryError``) ⇒ ``[]`` والحزمة تُبنى بدوننا — نفس نمط
R-206/T-105 حرفيًا: **ممنوع** ``with ThreadPoolExecutor`` (خروجه
ينتظر)؛ ``shutdown(wait=False)`` يهمل المتأخر.

**حدود SafeReader (R-204):** هذه الوحدة لا تقرأ أي ملف — قراءة
``memory.jsonl`` كلها داخل ``core.project_memory.ProjectMemoryStore``
(المحقون جاهزًا)؛ صفر ``open``/``read_text`` هنا (بوابة grep في
check.sh على context/ تبقى نظيفة).

قواعد AUTHORING.md: لا مشي شجري (لا نلمس ``scan`` — الذاكرة ليست
ملفات)، provenance ثابت (``kind = "project_memory"``)، حتمية كاملة،
لا استثناءات تعبر للمستهلك.
"""
from __future__ import annotations

import concurrent.futures
import re
from typing import Any

from context.engine import ContextItem, ContextRequest, ProjectScan
from core.project_memory import MemoryEntry, is_stale

#: طبقة ميزانية مدخلات ذاكرة المشروع — opportunistic **حصريًا**
#: (نفس قصر R-203/T-105): أول ما يُسقطه ContextBudget.
PROJECT_MEMORY_TIER = "opportunistic"

MAX_ENTRIES = 5           # حد المدخلات المسترجعة لكل رسالة
DEFAULT_TIMEOUT = 1.0     # ثوانٍ — ميزانية زمن opportunistic

_WORD_RE = re.compile(r"[\w\u0600-\u06FF]{3,}", re.UNICODE)


def _query_words(message: str) -> frozenset[str]:
    return frozenset(w.lower() for w in _WORD_RE.findall(message))


def render_entry(entry: MemoryEntry, stale: bool) -> str:
    """تصيير مُعنوَن — المدخلة تعلن نوعها وprovenance، والقديمة تعلن
    قِدمها صراحة (بند القبول: flagged, never silently served as fresh)."""
    flag = "STALE " if stale else ""
    header = (f"[{flag}MEMORY kind={entry.kind}"
              f" source={entry.source} at={entry.created_at}]")
    if stale:
        header += " (بنية المشروع تغيّرت منذ تسجيلها — تحقق قبل الاعتماد)"
    return f"{header}\n{entry.text}"


class ProjectMemorySource:
    """مصدر ذاكرة المشروع الدائمة — راجع docstring الوحدة.

    يُبنى بمخزن جاهز (حقن صريح — لا يبني مخازن ولا يقرأ ملفات):
    ``store`` هو ``ProjectMemoryStore`` وقراءته داخل خيط المهلة؛
    ``index`` (ProjectIndex حي، اختياري) مرجع حكم الـ staleness —
    غيابه = لا حكم (كل المدخلات تُعامل طازجة).
    """

    kind = "project_memory"

    def __init__(self, store: Any, project_id: str,
                 index: Any = None,
                 max_entries: int = MAX_ENTRIES,
                 timeout_seconds: float = DEFAULT_TIMEOUT) -> None:
        self._store = store
        self._project_id = project_id
        self._index = index
        self._max_entries = max_entries
        self._timeout = timeout_seconds

    # ── الاسترجاع (يجري داخل خيط المهلة) ──

    def _retrieve(self, message: str) -> list[ContextItem]:
        words = _query_words(message)
        if not words:
            return []
        entries = self._store.entries(self._project_id)
        scored: list[tuple[int, float, int, MemoryEntry]] = []
        for idx, entry in enumerate(entries):
            text = entry.text.lower()
            overlap = sum(1 for w in words if w in text)
            if not overlap:
                continue
            stale = is_stale(entry, self._index)
            # مفتاح الفرز: الطازج قبل القديم (down-rank مطلق — بند
            # القبول)، ثم الأعلى تداخلًا، ثم الأحدث (idx الأكبر).
            scored.append((1 if stale else 0, overlap / len(words),
                           idx, entry))
        scored.sort(key=lambda t: (t[0], -t[1], -t[2]))
        items: list[ContextItem] = []
        for stale_rank, _score, _idx, entry in scored[:self._max_entries]:
            items.append(ContextItem(
                source_kind=self.kind,
                path=f"<memory:project:{entry.entry_id}>",
                content=render_entry(entry, stale=bool(stale_rank)),
            ))
        return items

    # ── الجمع (العقد: لا يرفع، لا يعطّل) ──

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        if self._store is None:
            return []                       # مصدر خامل — لا خيط أصلًا
        # المهلة الصارمة — نفس نمط R-206/T-105 (انظر docstring الوحدة):
        # لا ``with`` (خروجه ينتظر)، وshutdown(wait=False) يهمل المتأخر.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(self._retrieve, request.message)
            return future.result(timeout=self._timeout)
        except Exception:
            return []                       # timeout / تلف / أي فشل ⇒ skip
        finally:
            pool.shutdown(wait=False)
