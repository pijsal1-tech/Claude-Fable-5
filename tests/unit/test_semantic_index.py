# -*- coding: utf-8 -*-
"""T-104 (R-802): اختبارات الفهرس الدلالي — top-k بمُضمِّن زائف، ثبات
round-trip، مسار «غير متاح» بلا تسريب استثناء، وحد أداء 1k قطعة <1s.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from context.embedding import (              # noqa: E402
    Embedder,
    EmbedderUnavailable,
    ProviderEmbedder,
)
from context.semantic_index import (         # noqa: E402
    EMBEDDING_FORMAT,
    EMBEDDING_KIND,
    MAX_VECTORS,
    SearchResult,
    SemanticIndex,
    cosine_similarity,
)
from sessions.store import SessionStore      # noqa: E402


# ═════════════════ مُضمِّنات زائفة ═════════════════

class AxisEmbedder:
    """مُضمِّن حتمي: كلمات مفتاحية ⇒ محاور مستقلة — ترتيب top-k متوقع.

    التشابه = تداخل الكلمات المفتاحية؛ نص بلا مفاتيح يأخذ محورًا
    مستقلًا أخيرًا (لا صفرًا — cosine مع صفر = 0 دائمًا فتضيع الرتب).
    """
    AXES = ("login", "database", "css", "deploy")

    def embed(self, texts):
        vectors = []
        for text in texts:
            vec = [1.0 if axis in text.lower() else 0.0
                   for axis in self.AXES]
            vec.append(0.0 if any(vec) else 1.0)   # محور "غير ذلك"
            vectors.append(vec)
        return vectors


class FlakyEmbedder:
    """يفشل عند رفع الراية — لاختبار مسارَي الإضافة والاستعلام."""

    def __init__(self):
        self.down = False
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        if self.down:
            raise EmbedderUnavailable("provider down")
        return AxisEmbedder().embed(texts)


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


@pytest.fixture()
def session_id(store: SessionStore) -> str:
    return store.create().id


def _index(store, session_id, embedder=None) -> SemanticIndex:
    return SemanticIndex(store, session_id, embedder or AxisEmbedder())


CHUNKS = [
    ("c1", "the login page validates credentials", "file"),
    ("c2", "database schema for users table", "file"),
    ("c3", "css styling for the login form", "turn"),
    ("c4", "deploy pipeline configuration", "episode"),
]


# ═════════════════ cosine ═════════════════

class TestCosine:

    def test_identical_and_orthogonal(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_or_mismatched_vectors_are_zero_not_crash(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
        assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0
        assert cosine_similarity([], []) == 0.0


# ═════════════════ top-k (بند القبول) ═════════════════

class TestTopKOrdering:

    def test_most_similar_first_and_k_respected(self, store, session_id):
        idx = _index(store, session_id)
        assert idx.add_texts(CHUNKS) == 4
        result = idx.search("login form css", top_k=2)
        assert result.available is True
        assert [h.chunk_id for h in result.hits] == ["c3", "c1"]
        assert result.hits[0].score > result.hits[1].score
        assert result.hits[0].source == "turn"

    def test_deterministic_tie_break_by_chunk_id(self, store, session_id):
        idx = _index(store, session_id)
        idx.add_texts([("b", "login", "f"), ("a", "login", "f")])
        result = idx.search("login", top_k=2)
        assert [h.chunk_id for h in result.hits] == ["a", "b"]

    def test_empty_index_available_but_no_hits(self, store, session_id):
        result = _index(store, session_id).search("anything")
        assert result == SearchResult(hits=(), available=True)

    def test_duplicate_chunk_id_newest_wins(self, store, session_id):
        idx = _index(store, session_id)
        idx.add_texts([("c1", "database stuff", "file")])
        idx.add_texts([("c1", "login page", "file")])
        assert idx.size() == 1
        result = idx.search("login", top_k=1)
        assert result.hits[0].text == "login page"


# ═════════════════ الثبات round-trip (بند القبول) ═════════════════

class TestPersistenceRoundTrip:

    def test_reload_from_disk_same_results(self, store, session_id):
        _index(store, session_id).add_texts(CHUNKS)
        # عملية جديدة: مخزن + فهرس جديدان فوق نفس المجلد
        fresh = SemanticIndex(SessionStore(store.sessions_dir), session_id,
                              AxisEmbedder())
        assert fresh.size() == 4
        result = fresh.search("database users", top_k=1)
        assert result.hits[0].chunk_id == "c2"

    def test_on_disk_record_matches_schema(self, store, session_id):
        _index(store, session_id).add_texts([CHUNKS[0]])
        raw = store.embeddings_path(session_id).read_text("utf-8").strip()
        rec = json.loads(raw)
        assert rec["kind"] == EMBEDDING_KIND
        assert rec["format"] == EMBEDDING_FORMAT
        assert set(rec) == {"kind", "format", "chunk_id", "text",
                            "source", "vector", "ts"}
        assert all(isinstance(x, float) for x in rec["vector"])

    def test_unknown_kind_and_future_format_skipped(self, store,
                                                    session_id):
        store.append_embedding_record(session_id, {"kind": "other", "x": 1})
        store.append_embedding_record(session_id, {
            "kind": EMBEDDING_KIND, "format": EMBEDDING_FORMAT + 1,
            "chunk_id": "future", "vector": [1.0]})
        idx = _index(store, session_id)
        idx.add_texts([CHUNKS[0]])
        assert idx.size() == 1

    def test_delete_session_removes_embidx_sidecar(self, store, session_id):
        _index(store, session_id).add_texts([CHUNKS[0]])
        assert store.delete(session_id) is True
        assert not store.embeddings_path(session_id).exists()


# ═════════════════ «غير متاح» (بند القبول) ═════════════════

class TestUnavailability:

    def test_add_texts_returns_zero_no_partial_write(self, store,
                                                     session_id):
        flaky = FlakyEmbedder()
        idx = _index(store, session_id, flaky)
        flaky.down = True
        assert idx.add_texts(CHUNKS) == 0
        assert idx.last_error is not None
        assert "provider down" in idx.last_error
        assert idx.size() == 0
        # لا سجل جزئي على القرص
        assert not store.embeddings_path(session_id).exists() or \
            store.embeddings_path(session_id).stat().st_size == 0

    def test_search_reports_unavailable_cleanly(self, store, session_id):
        flaky = FlakyEmbedder()
        idx = _index(store, session_id, flaky)
        idx.add_texts(CHUNKS)
        flaky.down = True
        result = idx.search("login")
        assert result.available is False and result.hits == ()
        # التعافي: المزوّد عاد ⇒ البحث يعمل بلا إعادة فهرسة
        flaky.down = False
        recovered = idx.search("login", top_k=1)
        assert recovered.available is True
        assert recovered.hits[0].chunk_id in ("c1", "c3")

    def test_unconfigured_provider_embedder_is_unavailable_no_network(self):
        with pytest.raises(EmbedderUnavailable):
            ProviderEmbedder(base_url="").embed(["x"])

    def test_provider_embedder_empty_input_short_circuits(self):
        assert ProviderEmbedder(base_url="").embed([]) == []


# ═════════════════ ProviderEmbedder (HTTP زائف) ═════════════════

class TestProviderEmbedder:

    def _fake_requests(self, monkeypatch, status=200, payload=None,
                       raise_exc=None):
        import requests

        class FakeResp:
            status_code = status
            text = "boom"

            def json(self):
                return payload

        def fake_post(url, json=None, headers=None, timeout=None):
            fake_post.captured = {"url": url, "json": json,
                                  "headers": headers}
            if raise_exc:
                raise raise_exc
            return FakeResp()

        monkeypatch.setattr(requests, "post", fake_post)
        return fake_post

    def test_success_orders_by_index(self, monkeypatch):
        # data معكوسة عمدًا — المواصفة لا تضمن الترتيب
        fake = self._fake_requests(monkeypatch, payload={"data": [
            {"index": 1, "embedding": [0.0, 1.0]},
            {"index": 0, "embedding": [1.0, 0.0]},
        ]})
        emb = ProviderEmbedder(base_url="http://x/v1", api_key="k",
                               model="m")
        vectors = emb.embed(["a", "b"])
        assert vectors == [[1.0, 0.0], [0.0, 1.0]]
        assert fake.captured["url"] == "http://x/v1/embeddings"
        assert fake.captured["json"] == {"model": "m", "input": ["a", "b"]}
        assert fake.captured["headers"]["Authorization"] == "Bearer k"

    def test_http_error_and_transport_error_wrapped(self, monkeypatch):
        self._fake_requests(monkeypatch, status=500, payload={})
        with pytest.raises(EmbedderUnavailable):
            ProviderEmbedder(base_url="http://x").embed(["a"])
        self._fake_requests(monkeypatch,
                            raise_exc=ConnectionError("refused"))
        with pytest.raises(EmbedderUnavailable):
            ProviderEmbedder(base_url="http://x").embed(["a"])

    def test_malformed_response_wrapped(self, monkeypatch):
        self._fake_requests(monkeypatch, payload={"data": [
            {"index": 0, "embedding": [1.0]}]})   # ناقص متجه للنص الثاني
        with pytest.raises(EmbedderUnavailable):
            ProviderEmbedder(base_url="http://x").embed(["a", "b"])


# ═════════════════ حد الأداء + سقف السعة ═════════════════

class TestPerformanceBound:

    def test_build_and_search_1k_chunks_under_1s(self, store, session_id):
        """بند القبول: بناء فهرس فوق 1k قطعة <1s (بمُضمِّن زائف فوري)."""
        items = [(f"c{i}", f"chunk number {i} about login topic {i % 7}",
                  "file") for i in range(1000)]
        idx = _index(store, session_id)
        start = time.monotonic()
        assert idx.add_texts(items) == 1000
        result = idx.search("login topic 3", top_k=5)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"1k build+search استغرق {elapsed:.2f}s"
        assert len(result.hits) == 5

    def test_capacity_cap_is_loud(self, store, session_id):
        idx = _index(store, session_id)
        too_many = [(f"c{i}", "x", "f") for i in range(MAX_VECTORS + 1)]
        with pytest.raises(ValueError):
            idx.add_texts(too_many)


# ═════════════════ بوابة لا-اعتماد-صلب ═════════════════

class TestNoHardDependency:

    def test_no_heavy_imports_at_module_level(self):
        """بند الانحدار: لا numpy/faiss/torch — واستيراد requests كسول
        داخل النداء لا في رأس الوحدة (grep على المصدر)."""
        for mod in ("context/embedding.py", "context/semantic_index.py"):
            src = (REPO_ROOT / mod).read_text("utf-8")
            head = "\n".join(  # الأسطر خارج الدوال (بلا مسافة بادئة)
                line for line in src.splitlines()
                if line.startswith(("import ", "from ")))
            for banned in ("numpy", "faiss", "chromadb", "torch",
                           "requests"):
                assert banned not in head, f"{banned} مستورد صلبًا في {mod}"

    def test_docs_pointer_present(self):
        """بند التوثيق: إشارة قرار الخلفية إلى phase8_plan §2."""
        src = (REPO_ROOT / "context/embedding.py").read_text("utf-8")
        assert "phase8_plan" in src and "§2" in src
