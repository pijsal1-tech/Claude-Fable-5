# -*- coding: utf-8 -*-
"""MemorySource (R-802 / T-105): مصدر الاسترجاع الطبقي — حلقي + دلالي.

يُكمل R-802: الطبقتان المبنيتان في T-103 (الحلقية —
``context/memory_layers.EpisodicLayer``) وT-104 (الدلالية —
``context/semantic_index.SemanticIndex``) تدخلان ContextEngine كمصدر
واحد عبر مقعد R-201 القياسي (``collect(request, scan) → items``) —
لا شيء آخر يتغير (نص التصميم في الروادماب حرفيًا).

مخطط تدفق الاسترجاع الكامل في ``docs/phase8_plan.md`` §2.1.

**الطبقة (tier):** ``MEMORY_TIER = "opportunistic"`` **حصريًا** —
نفس قاعدة R-203/R-206: «لو فيه مساحة»، أول ما يُضحَّى به؛ الاسترجاع
الخاطئ رخيص بالتصميم ولا يزاحم ``must_have``/``high`` أبدًا.

**الاسترجاع (داخل خيط المهلة):**

1. **دلالي:** ``SemanticIndex.search(message, top_k)`` — النتائج
   بمسارات رمزية ``<memory:sem:chunk_id>``؛ ``available=False``
   (مزوّد ساقط) ⇒ الجزء الدلالي يسهم بلا شيء — الحلقي يستمر.
2. **حلقي:** تسجيل تداخل كلمات الاستعلام (طول ≥3، lower) مع
   goal/outcome/key_decisions لكل حلقة — حتمي بلا موديل؛ الأعلى
   تداخلًا فالأحدث، بحد ``MAX_EPISODES``، بمسارات
   ``<memory:episode:run_id>`` ومحتوى مضغوط مُعنوَن.

المسارات الرمزية لا تتنكر كملفات: facade يرشّح ``mention``/``keyword``
فقط لقائمة ``mentioned_files`` ⇒ goldens T-017 غير متأثرة (مثبَّت
اختبارًا في الاتجاهين).

**المهلة async fallback-to-skip (بند القبول):** كامل خط الاسترجاع في
خيط عامل واحد بمهلة ``timeout_seconds``؛ تجاوز/أي فشل ⇒ ``[]`` فورًا
والحزمة تُبنى بدوننا — نفس نمط R-206 حرفيًا: **ممنوع**
``with ThreadPoolExecutor`` (خروجه ``shutdown(wait=True)`` ينتظر الخيط
البطيء فيُبطل المهلة)؛ ``shutdown(wait=False)`` يترك الخيط المتأخر
يُكمل ويُهمل ناتجه.

قواعد AUTHORING.md: لا مشي شجري (لا نلمس ``scan`` إطلاقًا — الذاكرة
ليست ملفات)، provenance ثابت (``kind = "memory"``)، حتمية كاملة،
لا استثناءات تعبر للمستهلك.
"""
from __future__ import annotations

import concurrent.futures
import re
from typing import Optional

from context.engine import ContextItem, ContextRequest, ProjectScan
from context.memory_layers import EpisodeRecord, EpisodicLayer
from context.semantic_index import SemanticIndex

#: طبقة ميزانية عناصر الذاكرة — opportunistic **حصريًا** (قاعدة R-203):
#: أول ما يُسقطه ContextBudget؛ لا يزاحم must_have/high أبدًا.
MEMORY_TIER = "opportunistic"

MAX_EPISODES = 2          # حد الحلقات المسترجعة لكل رسالة
DEFAULT_TOP_K = 3         # حد نتائج الطبقة الدلالية
DEFAULT_TIMEOUT = 1.0     # ثوانٍ — ميزانية زمن opportunistic

_WORD_RE = re.compile(r"[\w\u0600-\u06FF]{3,}", re.UNICODE)


def _query_words(message: str) -> frozenset[str]:
    return frozenset(w.lower() for w in _WORD_RE.findall(message))


def _episode_text(episode: EpisodeRecord) -> str:
    return " ".join((episode.goal, episode.outcome)
                    + episode.key_decisions).lower()


def _render_episode(episode: EpisodeRecord) -> str:
    """تصيير مضغوط مُعنوَن — الحلقة تُعلن نفسها، لا تتنكر كدور محادثة."""
    lines = [f"[EPISODE run={episode.run_id} outcome={episode.outcome}]",
             f"goal: {episode.goal}"]
    lines.extend(f"- {d}" for d in episode.key_decisions)
    if episode.files_touched:
        lines.append("files: " + ", ".join(episode.files_touched))
    return "\n".join(lines)


class MemorySource:
    """مصدر ذاكرة طبقي لجلسة واحدة — راجع docstring الوحدة.

    يُبنى بطبقتين جاهزتين (حقن صريح — لا يبني مخازن بنفسه):
    ``episodic`` قد تكون ``None`` (جلسة بلا حلقات) وكذلك ``semantic``
    (بلا فهرس) — الغائب يسهم بلا شيء، والاثنان معًا ``None`` = مصدر
    خامل يعيد ``[]`` دائمًا (نفس دلالة الذاكرة الفارغة).
    """

    kind = "memory"

    def __init__(self, episodic: Optional[EpisodicLayer] = None,
                 semantic: Optional[SemanticIndex] = None,
                 top_k: int = DEFAULT_TOP_K,
                 timeout_seconds: float = DEFAULT_TIMEOUT) -> None:
        self._episodic = episodic
        self._semantic = semantic
        self._top_k = top_k
        self._timeout = timeout_seconds

    # ── الاسترجاع (يجري داخل خيط المهلة) ──

    def _retrieve(self, message: str) -> list[ContextItem]:
        items: list[ContextItem] = []

        # 1) الطبقة الدلالية (T-104) — غير متاحة ⇒ تسهم بلا شيء فقط
        if self._semantic is not None:
            result = self._semantic.search(message, top_k=self._top_k)
            for hit in result.hits:
                items.append(ContextItem(
                    source_kind=self.kind,
                    path=f"<memory:sem:{hit.chunk_id}>",
                    content=hit.text,
                ))

        # 2) الطبقة الحلقية (T-103) — تداخل كلمات حتمي بلا موديل
        if self._episodic is not None:
            words = _query_words(message)
            if words:
                scored: list[tuple[float, int, EpisodeRecord]] = []
                for idx, ep in enumerate(self._episodic.episodes()):
                    text = _episode_text(ep)
                    overlap = sum(1 for w in words if w in text)
                    if overlap:
                        scored.append((overlap / len(words), idx, ep))
                # الأعلى تداخلًا أولًا؛ كسر التعادل بالأحدث (idx الأكبر)
                scored.sort(key=lambda t: (-t[0], -t[1]))
                for _score, _idx, ep in scored[:MAX_EPISODES]:
                    items.append(ContextItem(
                        source_kind=self.kind,
                        path=f"<memory:episode:{ep.run_id}>",
                        content=_render_episode(ep),
                    ))
        return items

    # ── الجمع (العقد: لا يرفع، لا يعطّل) ──

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        if self._episodic is None and self._semantic is None:
            return []                       # مصدر خامل — لا خيط أصلًا
        # المهلة الصارمة — نفس نمط R-206 (انظر docstring الوحدة):
        # لا ``with`` (خروجه ينتظر)، وshutdown(wait=False) يهمل المتأخر.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(self._retrieve, request.message)
            return future.result(timeout=self._timeout)
        except Exception:
            return []                       # timeout / أي فشل ⇒ skip
        finally:
            pool.shutdown(wait=False)
