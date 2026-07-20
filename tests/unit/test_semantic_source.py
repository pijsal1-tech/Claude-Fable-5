# -*- coding: utf-8 -*-
"""اختبارات SemanticSource (T-057 / R-206).

التغطية (معايير قبول T-057):
- precision fixture: سؤال عن قرار مبكر يسترجع المقطع الصحيح.
- timeout-skip: backend بطيء مُحاكى ⇒ [] خلال المهلة، لا انتظار.
- امتثال الطبقات: opportunistic — must_have/high لا يُزاحان أبدًا.
- flag off: الإيقاف نظيف (collect يعيد [] دائمًا).
- قراءة config (semantic_config_from) + التسجيل في التركيبة القياسية.
- استرجاع الأدوار (turns) + عدم استرجاع الرسالة نفسها.
- عقد AUTHORING: لا مشي شجري، لا استثناءات، حتمية.
"""
from __future__ import annotations

import pathlib
import time

import pytest

from context.budget import BudgetItem, ContextBudget
from context.engine import ContextRequest, ProjectScan
from context.facade import _default_engine
from context.semantic_source import (
    SEMANTIC_TIER,
    HashingEmbedder,
    SemanticSource,
    reset_semantic_state,
    semantic_config_from,
)


@pytest.fixture(autouse=True)
def _isolate_semantic_state():
    """عزل الحالة المشتركة (module-level) بين الاختبارات."""
    reset_semantic_state()
    yield
    reset_semantic_state()


def _collect(source: SemanticSource, root: pathlib.Path, message: str):
    return source.collect(
        ContextRequest(message=message, project_root=root),
        ProjectScan(root))


# ═══════════════════ precision fixture ═══════════════════

class TestRetrievalPrecision:
    """معيار قبول: سؤال عن قرار مبكر يسترجع المقطع الصحيح."""

    def test_early_decision_chunk_retrieved(self, tmp_path):
        (tmp_path / "auth_decision.md").write_text(
            "Decision: we handle authentication with JWT tokens\n"
            "stored in httpOnly cookies, refreshed every hour.\n",
            encoding="utf-8")
        (tmp_path / "styles.css").write_text(
            ".button { color: blue; }\n.card { margin: 4px; }\n",
            encoding="utf-8")
        (tmp_path / "math.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8")

        items = _collect(SemanticSource(), tmp_path,
                         "how did we handle authentication tokens?")
        assert items, "المقطع الصحيح لم يُسترجع"
        top = items[0]
        assert top.path.startswith("<semantic:auth_decision.md:")
        assert "JWT" in (top.content or "")

    def test_irrelevant_query_returns_nothing_over_threshold(self, tmp_path):
        (tmp_path / "a.py").write_text("def add(a, b):\n    return a + b\n",
                                       encoding="utf-8")
        items = _collect(SemanticSource(), tmp_path,
                         "zzz qqq xxx unrelated gibberish")
        assert items == []                    # لا ضجيج تحت العتبة

    def test_turn_recall_and_no_self_retrieval(self, tmp_path):
        src = SemanticSource()
        # الرسالة الأولى تُسجَّل كـ turn — ولا تسترجع نفسها
        first = _collect(src, tmp_path,
                         "we decided to use PostgreSQL for storage")
        assert first == []                    # ذخيرة فارغة وقتها
        # الرسالة الثانية تسترجع القرار من الـ turn السابق
        second = _collect(src, tmp_path, "what storage PostgreSQL decided?")
        assert any(it.path.startswith("<semantic:turn:") and
                   "PostgreSQL" in (it.content or "") for it in second)

    def test_determinism(self, tmp_path):
        (tmp_path / "doc.md").write_text(
            "caching strategy uses redis with TTL of one minute\n",
            encoding="utf-8")
        a = _collect(SemanticSource(), tmp_path, "redis caching strategy")
        reset_semantic_state()
        b = _collect(SemanticSource(), tmp_path, "redis caching strategy")
        assert [(i.path, i.content) for i in a] == \
               [(i.path, i.content) for i in b]

    def test_provenance_and_top_k_cap(self, tmp_path):
        for i in range(8):
            (tmp_path / f"n{i}.md").write_text(
                f"shared topic keyword banana file {i}\n", encoding="utf-8")
        items = _collect(SemanticSource(top_k=3), tmp_path,
                         "banana topic keyword")
        assert 0 < len(items) <= 3
        assert all(it.source_kind == "semantic" for it in items)


# ═══════════════════ timeout-skip ═══════════════════

class TestTimeoutSkip:
    """معيار قبول: backend بطيء ⇒ skip خلال المهلة — لا يعطّل الرد."""

    def test_slow_backend_skipped_within_deadline(self, tmp_path):
        (tmp_path / "a.md").write_text("hello world content",
                                       encoding="utf-8")

        class SlowBackend:
            def embed(self, texts):
                time.sleep(5.0)              # أبطأ بكثير من المهلة
                return [[0.0] * 8 for _ in texts]

        src = SemanticSource(backend=SlowBackend(), timeout_seconds=0.2)
        start = time.perf_counter()
        items = _collect(src, tmp_path, "hello world")
        elapsed = time.perf_counter() - start
        assert items == []                   # skip — لا نتيجة جزئية
        assert elapsed < 2.0, f"timeout لم يُحترم: {elapsed:.2f}s"

    def test_raising_backend_skipped_silently(self, tmp_path):
        (tmp_path / "a.md").write_text("content", encoding="utf-8")

        class BoomBackend:
            def embed(self, texts):
                raise RuntimeError("embedding service down")

        items = _collect(SemanticSource(backend=BoomBackend()),
                         tmp_path, "content query")
        assert items == []                   # فشل الـ backend ⇒ skip صامت


# ═══════════════════ امتثال الطبقات ═══════════════════

class TestTierCompliance:
    """معيار قبول: opportunistic — must_have/high لا يُزاحان أبدًا."""

    def test_semantic_tier_is_opportunistic(self):
        assert SEMANTIC_TIER == "opportunistic"

    def test_must_have_and_high_never_displaced(self, tmp_path):
        (tmp_path / "doc.md").write_text(
            "topic banana " * 200, encoding="utf-8")
        items = _collect(SemanticSource(), tmp_path, "banana topic")
        assert items                         # فيه عناصر دلالية فعلًا

        budget_items = [
            BudgetItem("user_request", "the user request", tier="must_have"),
            BudgetItem("target_file", "important file body", tier="high"),
        ] + [
            BudgetItem(it.path, (it.content or "") * 20, tier=SEMANTIC_TIER)
            for it in items
        ]
        packed = ContextBudget(model_window=40).pack(budget_items)
        kept = {it.key for it in packed.kept}
        assert "user_request" in kept        # must_have باقٍ دائمًا
        assert "target_file" in kept         # high يتقدم على opportunistic
        dropped = {d.key for d in packed.dropped}
        assert dropped <= {it.path for it in items}   # الدلالي وحده يُسقط


# ═══════════════════ علم الـ config ═══════════════════

class TestConfigFlag:
    def test_flag_off_disables_cleanly(self, tmp_path):
        (tmp_path / "doc.md").write_text("banana topic keyword",
                                         encoding="utf-8")
        src = SemanticSource.from_config(
            {"context": {"semantic": {"enabled": False}}})
        assert _collect(src, tmp_path, "banana topic") == []

    def test_default_is_enabled(self):
        assert semantic_config_from(None).enabled is True
        assert semantic_config_from({}).enabled is True

    def test_config_values_parsed(self):
        sc = semantic_config_from({"context": {"semantic": {
            "enabled": True, "timeout_seconds": 0.5, "top_k": 7}}})
        assert (sc.enabled, sc.timeout_seconds, sc.top_k) == (True, 0.5, 7)

    def test_garbage_config_falls_back_to_defaults(self):
        sc = semantic_config_from({"context": {"semantic": {
            "enabled": "yes", "timeout_seconds": -3, "top_k": "many"}}})
        assert sc.enabled is True
        assert sc.timeout_seconds > 0
        assert sc.top_k > 0

    def test_shipped_config_yaml_has_semantic_section(self):
        import yaml
        cfg_path = pathlib.Path(__file__).resolve().parents[2] / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        section = cfg["context"]["semantic"]
        assert section["enabled"] is True    # الافتراضي المشحون: on


# ═══════════════════ التسجيل + عقد AUTHORING ═══════════════════

class TestEngineRegistrationAndContract:
    def test_default_engine_includes_semantic_source(self):
        kinds = [s.kind for s in _default_engine().sources]
        assert "semantic" in kinds
        # الترتيب: بعد symbol وقبل structure (وثيقة التركيبة)
        assert kinds.index("symbol") < kinds.index("semantic") \
            < kinds.index("structure")

    def test_no_tree_walk(self, tmp_path, monkeypatch):
        (tmp_path / "a.md").write_text("hello content", encoding="utf-8")
        scan = ProjectScan(tmp_path)         # المسح قبل الفخ

        def _boom(self, pattern):
            raise AssertionError(f"source walked the tree: rglob({pattern!r})")
        monkeypatch.setattr(pathlib.Path, "rglob", _boom)

        SemanticSource().collect(
            ContextRequest(message="hello", project_root=tmp_path), scan)

    def test_secret_files_excluded_from_corpus(self, tmp_path):
        # مفتاح AWS معروف النمط ⇒ SafeReader يحجبه ⇒ خارج الذخيرة
        (tmp_path / "config.py").write_text(
            'KEY = "AKIAIOSFODNN7EXAMPLE"\n# banana topic keyword\n',
            encoding="utf-8")
        items = _collect(SemanticSource(), tmp_path, "banana topic keyword")
        assert all("config.py" not in it.path for it in items)

    def test_collect_never_raises_on_weird_input(self, tmp_path):
        src = SemanticSource()
        _collect(src, tmp_path, "")
        _collect(src, tmp_path, "€€€ 🎉 \\\\ ..")

    def test_hashing_embedder_is_stable_and_normalized(self):
        emb = HashingEmbedder()
        v1 = emb.embed(["hello world hello"])[0]
        v2 = emb.embed(["hello world hello"])[0]
        assert v1 == v2                      # حتمية عبر النداءات
        norm = sum(x * x for x in v1) ** 0.5
        assert abs(norm - 1.0) < 1e-9        # تطبيع L2
