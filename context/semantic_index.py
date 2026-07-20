# -*- coding: utf-8 -*-
"""الفهرس الدلالي (R-802 / T-104): متجهات ثابتة + cosine top-k بايثون-صرف.

الطبقة الدلالية الوسطى بين الـ Embedder (بروتوكول ``context/embedding``
— اختيار الخلفية موثّق في ``docs/phase8_plan.md`` §2) ومصدر الاسترجاع
(T-105). **مستقل حتى T-105** — لا يلمس ContextEngine ولا الراوتر.

═══════════════ مخطط سجل المتجه (format=1) ═══════════════

سطر JSON واحد في ``session_<id>.embidx.jsonl`` (الكتابة/القراءة عبر
``SessionStore.append_embedding_record`` / ``replay_embeddings`` حصريًا
— نفس ضمانات sidecar الحلقات؛ لا قراءة خام في context/):

    {"kind": "embedding", "format": 1,
     "chunk_id": str,   # معرّف القطعة — تكراره = استبدال (الأحدث يفوز)
     "text": str,       # النص المفهرس نفسه (يُعاد للمُسترجِع)
     "source": str,     # منشأ القطعة (turn/episode/file) — provenance
     "vector": [float], # المتجه — أبعاده يحددها الـ embedder
     "ts": str}

سجل بـ ``kind`` مختلف أو ``format`` أحدث يُتخطى (توافق T-029).
الفهرس **مشتق قابل لإعادة البناء** — فقدان الـ sidecar ليس فقدان بيانات.

═══════════════ عقد «غير متاح» (بند القبول) ═══════════════

كل نداء embedding يمر عبر الـ Embedder؛ ``EmbedderUnavailable`` (مزوّد
غير مهيأ/ساقط/رد مشوه) **لا يتسرب أبدًا**: ``add_texts`` تعيد 0 وترفع
راية ``unavailable`` مع ``last_error``، و``search`` تعيد
``SearchResult(available=False, hits=[])`` — المستهلك (T-105) يتخطى
الطبقة بنظافة. الحساب: cosine بايثون-صرف فوق ≤5k متجه — لا numpy ولا
vector DB (مبررات §2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence

from context.embedding import Embedder, EmbedderUnavailable
from sessions.store import SessionStore

EMBEDDING_KIND = "embedding"
EMBEDDING_FORMAT = 1

# سقف التصميم (phase8_plan §2): brute-force cosine مقبول تحت هذا الحد
MAX_VECTORS = 5000


def _now_iso() -> str:
    return datetime.now().isoformat()


# ═══════════════════ أشكال البيانات ═══════════════════

@dataclass(frozen=True)
class IndexedChunk:
    """قطعة مفهرسة — انعكاس سطر الـ sidecar."""
    chunk_id: str
    text: str
    source: str
    vector: tuple[float, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": EMBEDDING_KIND,
            "format": EMBEDDING_FORMAT,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "vector": list(self.vector),
            "ts": _now_iso(),
        }


@dataclass(frozen=True)
class SearchHit:
    """نتيجة استرجاع واحدة — القطعة + درجة تشابهها."""
    chunk_id: str
    text: str
    source: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    """نتيجة بحث كاملة — ``available=False`` = المزوّد غير قابل للوصول
    (القائمة فارغة عندها بالتعريف؛ الفهرس الفارغ *المتاح* يعيد
    ``available=True`` مع لا نتائج — حالتان مختلفتان عمدًا)."""
    hits: tuple[SearchHit, ...] = ()
    available: bool = True


# ═══════════════════ cosine بايثون-صرف ═══════════════════

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """cosine كلاسيكي — أطوال مختلفة أو متجه صفري ⇒ 0.0 (لا انفجار)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = norm_a = norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


# ═══════════════════ الفهرس ═══════════════════

class SemanticIndex:
    """فهرس دلالي لجلسة واحدة فوق ``SessionStore`` (T-104).

    الحالة في الذاكرة = ``chunk_id → IndexedChunk`` (الأحدث يفوز —
    نفس دلالة replay للعلامات في T-029)؛ تُبنى كسولًا من الـ sidecar
    عند أول استعمال وتبقى متزامنة مع كل ``add_texts``.
    """

    def __init__(self, store: SessionStore, session_id: str,
                 embedder: Embedder) -> None:
        self._store = store
        self._session_id = session_id
        self._embedder = embedder
        self._chunks: dict[str, IndexedChunk] = {}
        self._loaded = False
        self.last_error: Optional[str] = None

    # ── التحميل من الثبات ──

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        result = self._store.replay_embeddings(self._session_id)
        for rec in result.records:
            if rec.get("kind") != EMBEDDING_KIND:
                continue
            if int(rec.get("format", 0)) > EMBEDDING_FORMAT:
                continue
            chunk = IndexedChunk(
                chunk_id=str(rec.get("chunk_id", "")),
                text=str(rec.get("text", "")),
                source=str(rec.get("source", "")),
                vector=tuple(float(x) for x in rec.get("vector", []) or []),
            )
            if chunk.chunk_id and chunk.vector:
                self._chunks[chunk.chunk_id] = chunk

    # ── الكتابة ──

    def add_texts(self, items: Sequence[tuple[str, str, str]]) -> int:
        """فهرسة قطع ``(chunk_id, text, source)`` — تعيد عدد المفهرس.

        نداء embedding **واحد مجمّع** لكل الدفعة (لا نداء لكل قطعة).
        ``EmbedderUnavailable`` ⇒ 0 + ``last_error`` — لا استثناء يتسرب
        ولا سجل جزئي يُكتب. تجاوز ``MAX_VECTORS`` = خطأ استعمال صريح
        (ValueError) — سقف التصميم لا يُتجاوز بصمت.
        """
        self._ensure_loaded()
        if not items:
            return 0
        new_ids = {cid for cid, _, _ in items}
        if len(set(self._chunks) | new_ids) > MAX_VECTORS:
            raise ValueError(
                f"تجاوز سقف الفهرس ({MAX_VECTORS} متجهًا) — "
                "قسّم/قلّم القطع قبل الفهرسة")
        try:
            vectors = self._embedder.embed([text for _, text, _ in items])
        except EmbedderUnavailable as exc:
            self.last_error = str(exc)
            return 0
        count = 0
        for (chunk_id, text, source), vector in zip(items, vectors):
            chunk = IndexedChunk(chunk_id=chunk_id, text=text,
                                 source=source, vector=tuple(vector))
            self._store.append_embedding_record(self._session_id,
                                                chunk.to_json())
            self._chunks[chunk_id] = chunk
            count += 1
        self.last_error = None
        return count

    # ── الاسترجاع ──

    def search(self, query: str, top_k: int = 3) -> SearchResult:
        """cosine top-k فوق الفهرس — مرتبة تنازليًّا بالدرجة.

        ``EmbedderUnavailable`` على الاستعلام ⇒
        ``SearchResult(available=False)`` — بند القبول: «يبلّغ غير متاح
        بنظافة»، لا استثناء يتسرب.
        """
        self._ensure_loaded()
        if top_k <= 0 or not self._chunks:
            return SearchResult()
        try:
            query_vec = self._embedder.embed([query])[0]
        except EmbedderUnavailable as exc:
            self.last_error = str(exc)
            return SearchResult(available=False)
        scored = [
            SearchHit(chunk_id=c.chunk_id, text=c.text, source=c.source,
                      score=cosine_similarity(query_vec, c.vector))
            for c in self._chunks.values()
        ]
        scored.sort(key=lambda h: (-h.score, h.chunk_id))
        return SearchResult(hits=tuple(scored[:top_k]))

    # ── الفحص ──

    def size(self) -> int:
        self._ensure_loaded()
        return len(self._chunks)
