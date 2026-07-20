# -*- coding: utf-8 -*-
"""SemanticSource (R-206 / T-057): استرجاع دلالي مصغَّر — بذرة مبكرة.

═══════════════════ Design Note ═══════════════════

**المشكلة (R-206):** بلا استرجاع بالصلة (relevance) تبقى جودة السياق
مسقوفة بالمطابقة الحرفية — رسالة مثل «كيف عالجنا الـ auth المرة
الماضية؟» لا طريق لها إطلاقًا للكود أو القرار المعني إذا لم تتطابق
الكلمات نصًّا.

**الحل — بذرة صغيرة عمدًا** (النظام الطبقي الكامل يبقى R-802/Phase 8):

1. **واجهة embedding واحدة قابلة للتوصيل** (``EmbeddingBackend``) —
   backend افتراضي واحد: ``HashingEmbedder`` — bag-of-words مُهَشَّم
   (md5 مستقر عبر التشغيلات — ليس ``hash()`` المُملَّح) إلى متجه
   بأبعاد ثابتة مع تطبيع L2. صفر تبعيات، صفر شبكة، حتمي بالكامل —
   backend شبكي حقيقي يُوصَّل لاحقًا من نفس المقبس.
2. **الذخيرة (corpus):** مقاطع ملفات المشروع (``CHUNK_LINES`` سطرًا
   لكل مقطع، قراءة عبر SafeReader حصريًا — بوابة R-204) + آخر
   ``MAX_RECENT_TURNS`` رسالة مستخدم (تُسجَّل بعد الاسترجاع كي لا
   تسترجع الرسالة نفسها).
3. **الاسترجاع:** cosine similarity، أفضل ``top_k`` فوق عتبة صلة
   دنيا — عناصر بمسارات رمزية ``<semantic:...>`` لا تتنكر كملفات.
4. **مهلة صارمة skip-on-timeout:** كامل خط الاسترجاع يجري في خيط
   بمهلة ``timeout_seconds``؛ تجاوزها/أي فشل ⇒ **[] فورًا** — لا
   يعطّل الرد أبدًا (معيار قبول R-206 الصريح).
5. **علم config:** ``context.semantic.enabled`` (افتراضيًا on) —
   الإيقاف نظيف: المصدر يُبنى لكن ``collect`` يعيد [] دائمًا.

**الطبقة (tier):** ``SEMANTIC_TIER = "opportunistic"`` حصريًا —
«لو فيه مساحة»، أول ما يُضحَّى به (قاعدة R-203). الاسترجاع الخاطئ
رخيص بالتصميم: لا يزاحم ``must_have``/``high`` أبدًا (مثبَّت اختبارًا).

**اختيار الـ backend (وثيقة القرار):** hashing-BoW يلتقط تطابق
المفردات بالصلة التقريبية (يكفي «query about an early decision
retrieves the right chunk» — معيار T-057) بلا أي تكلفة تشغيلية؛
الدقة الدلالية العميقة (مرادفات/لغات متقاطعة) مجال ترقية R-802 حيث
يُستبدل الـ backend من نفس الواجهة دون لمس المصدر.

**الحالة:** لكل جذر ``_RootState`` على مستوى الوحدة (نفس نمط
SymbolSource/T-056 — المحرّك يُبنى لكل رسالة في الـ facade).
كاش متجهات المقاطع بتوقيع stat ``(mtime_ns, size)`` — الملف المتغير
وحده يُعاد تقطيعه وتضمينه. ``reset_semantic_state()`` لعزل الاختبارات.

**حدود صادقة:** ``MAX_CORPUS_FILES = 300`` ملفًا، ``CHUNK_LINES = 30``
سطرًا، ``MAX_RECENT_TURNS = 20`` رسالة، ``DEFAULT_TOP_K = 3`` عناصر.

قواعد AUTHORING.md ملتزَمة: لا مشي شجري (``scan.files`` فقط)،
provenance ثابت (``kind = "semantic"``)، حتمية، لا استثناءات للمستهلك.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import math
import pathlib
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Protocol, runtime_checkable

from actions.file_manager import WEB_EXTENSIONS
from context.engine import ContextItem, ContextRequest, ProjectScan
from context.safe_reader import SafeReader

#: طبقة ميزانية العناصر الدلالية (R-206) — opportunistic **حصريًا**:
#: أول ما يُسقطه ContextBudget؛ لا يزاحم must_have/high أبدًا.
SEMANTIC_TIER = "opportunistic"

MAX_CORPUS_FILES = 300    # سقف ملفات الذخيرة لكل جذر
CHUNK_LINES = 30          # أسطر المقطع الواحد
MAX_RECENT_TURNS = 20     # آخر N رسالة مستخدم تدخل الذخيرة
DEFAULT_TOP_K = 3         # عناصر مسترجعة لكل رسالة
DEFAULT_TIMEOUT = 2.0     # مهلة خط الاسترجاع كاملًا (ثوانٍ)
MIN_SIMILARITY = 0.05     # عتبة صلة دنيا — ما دونها ضجيج لا يُحقن
_EMBED_DIM = 128          # أبعاد متجه الـ hashing backend

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


# ═══════════════════ واجهة الـ embedding ═══════════════════

@runtime_checkable
class EmbeddingBackend(Protocol):
    """العقد الوحيد لأي backend — استبداله لا يلمس المصدر (R-802 لاحقًا)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """متجه لكل نص، بنفس الترتيب. يُسمح برفع الاستثناءات —
        الحارس الزمني في المصدر يحوّل أي فشل إلى skip."""
        ...


class HashingEmbedder:
    """الـ backend الافتراضي: bag-of-words مُهَشَّم + تطبيع L2.

    md5 (مستقر عبر التشغيلات) بدل ``hash()`` المُملَّح — الحتمية عقد
    (AUTHORING.md قاعدة 5). صفر تبعيات، صفر I/O — لا يفشل عمليًا،
    لكن الحارس الزمني يغطيه كأي backend آخر.
    """

    def __init__(self, dim: int = _EMBED_DIM) -> None:
        self._dim = dim

    def _bucket(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self._dim
            for token in _TOKEN_RE.findall(text.lower()):
                vec[self._bucket(token)] += 1.0
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


def _cosine(a: list[float], b: list[float]) -> float:
    """cosine على متجهات مطبَّعة L2 = حاصل الضرب النقطي."""
    return sum(x * y for x, y in zip(a, b))


# ═══════════════════ علم الـ config ═══════════════════

@dataclass(frozen=True)
class SemanticConfig:
    """قسم ``context.semantic`` من config.yaml — تسامحي بالكامل."""
    enabled: bool = True
    timeout_seconds: float = DEFAULT_TIMEOUT
    top_k: int = DEFAULT_TOP_K


def semantic_config_from(cfg: dict | None) -> SemanticConfig:
    """قراءة ``cfg["context"]["semantic"]`` — قيم شاذة ⇒ الافتراضات.

    العلم افتراضيًا **on** (معيار R-206: live behind a config flag,
    default on, cheap to disable).
    """
    section = ((cfg or {}).get("context") or {}).get("semantic") or {}
    if not isinstance(section, dict):
        return SemanticConfig()
    enabled = section.get("enabled", True)
    timeout = section.get("timeout_seconds", DEFAULT_TIMEOUT)
    top_k = section.get("top_k", DEFAULT_TOP_K)
    return SemanticConfig(
        enabled=bool(enabled) if isinstance(enabled, bool) else True,
        timeout_seconds=(float(timeout)
                         if isinstance(timeout, (int, float))
                         and timeout > 0 else DEFAULT_TIMEOUT),
        top_k=(int(top_k)
               if isinstance(top_k, int) and top_k > 0 else DEFAULT_TOP_K),
    )


# ═══════════════════ الحالة المشتركة لكل جذر ═══════════════════

@dataclass
class _Chunk:
    """مقطع ذخيرة واحد — نص + متجه + عنوان مصدره."""
    path: str            # مسار رمزي <semantic:...>
    text: str
    vector: list[float]


@dataclass
class _RootState:
    """ذخيرة جذر واحد — تعيش عبر الرسائل (نمط T-056)."""
    file_chunks: dict[str, list[_Chunk]] = field(default_factory=dict)
    file_sigs: dict[str, tuple[int, int]] = field(default_factory=dict)
    turns: Deque[tuple[int, str, list[float]]] = field(
        default_factory=lambda: deque(maxlen=MAX_RECENT_TURNS))
    turn_counter: int = 0


_STATES: dict[str, _RootState] = {}


def reset_semantic_state() -> None:
    """تفريغ الحالة المشتركة — عزل الاختبارات (لا يُستدعى إنتاجيًا)."""
    _STATES.clear()


def _state_for(root: pathlib.Path) -> _RootState:
    key = str(root)
    state = _STATES.get(key)
    if state is None:
        state = _RootState()
        _STATES[key] = state
    return state


# ═══════════════════ المصدر ═══════════════════

class SemanticSource:
    """مصدر الاسترجاع الدلالي — top-k بطبقة opportunistic فقط.

    **ملاحظة ترتيب التركيبة:** يُسجَّل بعد ``SymbolSource`` وقبل
    ``StructureSource`` — مساراته الرمزية (``<semantic:...>``) لا
    تدخل ``mentioned_files`` (الـ facade يرشّح mention/keyword فقط)
    ⇒ goldens T-017 غير متأثرة.
    """

    kind = "semantic"

    def __init__(self, enabled: bool = True,
                 backend: EmbeddingBackend | None = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT,
                 top_k: int = DEFAULT_TOP_K,
                 max_files: int = MAX_CORPUS_FILES) -> None:
        self._enabled = enabled
        self._backend: EmbeddingBackend = (backend if backend is not None
                                           else HashingEmbedder())
        self._timeout = timeout_seconds
        self._top_k = top_k
        self._max_files = max_files

    @classmethod
    def from_config(cls, cfg: dict | None,
                    backend: EmbeddingBackend | None = None
                    ) -> "SemanticSource":
        """بناء من config.yaml — قسم ``context.semantic`` (T-057)."""
        sc = semantic_config_from(cfg)
        return cls(enabled=sc.enabled, backend=backend,
                   timeout_seconds=sc.timeout_seconds, top_k=sc.top_k)

    # ── الذخيرة ──

    def _refresh_corpus(self, state: _RootState, scan: ProjectScan) -> None:
        """تحديث مقاطع الملفات المتغيرة فقط (توقيع stat) — كاش الباقي."""
        reader = SafeReader(scan.root)
        current: set[str] = set()
        count = 0
        for p in scan.files:                 # قائمة المسح — لا مشي شجري
            if p.suffix not in WEB_EXTENSIONS:
                continue
            count += 1
            if count > self._max_files:
                break
            rel = scan.rel(p)
            current.add(rel)
            try:
                st = p.stat()
            except OSError:
                continue
            sig = (st.st_mtime_ns, st.st_size)
            if state.file_sigs.get(rel) == sig:
                continue                     # غير متغير — الكاش يكفي
            state.file_sigs[rel] = sig
            result = reader.read_text(rel)
            if not result.ok or result.content is None or result.redacted:
                state.file_chunks[rel] = []  # سري/متعذر ⇒ خارج الذخيرة
                continue
            lines = result.content.splitlines()
            texts: list[str] = []
            spans: list[tuple[int, int]] = []
            for lo in range(0, len(lines), CHUNK_LINES):
                hi = min(lo + CHUNK_LINES, len(lines))
                chunk_text = "\n".join(lines[lo:hi]).strip()
                if chunk_text:
                    texts.append(chunk_text)
                    spans.append((lo + 1, hi))
            vectors = self._backend.embed(texts) if texts else []
            state.file_chunks[rel] = [
                _Chunk(path=f"<semantic:{rel}:{lo}-{hi}>",
                       text=text, vector=vec)
                for (lo, hi), text, vec in zip(spans, texts, vectors)
            ]
        # ملفات حُذفت/خرجت من السقف — إسقاط أثرها
        for rel in [r for r in state.file_sigs if r not in current]:
            state.file_sigs.pop(rel, None)
            state.file_chunks.pop(rel, None)

    # ── الاسترجاع (يجري داخل الحارس الزمني) ──

    def _retrieve(self, state: _RootState, scan: ProjectScan,
                  message: str) -> list[ContextItem]:
        self._refresh_corpus(state, scan)
        query_vec = self._backend.embed([message])[0]

        scored: list[tuple[float, str, str]] = []
        for rel in sorted(state.file_chunks):          # حتمية
            for chunk in state.file_chunks[rel]:
                sim = _cosine(query_vec, chunk.vector)
                if sim >= MIN_SIMILARITY:
                    scored.append((sim, chunk.path, chunk.text))
        for idx, text, vec in state.turns:
            sim = _cosine(query_vec, vec)
            if sim >= MIN_SIMILARITY:
                scored.append((sim, f"<semantic:turn:{idx}>", text))

        # الأعلى صلة أولًا؛ كسر التعادل بالمسار (حتمية كاملة)
        scored.sort(key=lambda t: (-t[0], t[1]))
        items = [ContextItem(source_kind=self.kind, path=path, content=text)
                 for _sim, path, text in scored[:self._top_k]]

        # تسجيل الرسالة كـ turn **بعد** الاسترجاع — لا تسترجع نفسها
        state.turn_counter += 1
        state.turns.append((state.turn_counter, message,
                            self._backend.embed([message])[0]))
        return items

    # ── الجمع (العقد: لا يرفع، لا يعطّل) ──

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        if not self._enabled:
            return []                        # الإيقاف النظيف (flag off)
        state = _state_for(scan.root)
        # المهلة الصارمة: خط الاسترجاع كاملًا في خيط واحد؛ تجاوز/فشل ⇒
        # skip فوري — لا يعطّل الرد أبدًا (معيار قبول R-206).
        # ⚠️ ممنوع ``with ThreadPoolExecutor``: خروجه = shutdown(wait=True)
        # ينتظر الخيط البطيء فيُبطل المهلة. shutdown(wait=False) يترك
        # الخيط المتأخر يُكمل في الخلفية ويُهمل ناتجه.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(self._retrieve, state, scan,
                                 request.message)
            return future.result(timeout=self._timeout)
        except Exception:
            return []                        # timeout / backend failure ⇒ skip
        finally:
            pool.shutdown(wait=False)
