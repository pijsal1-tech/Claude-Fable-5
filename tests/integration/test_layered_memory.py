# -*- coding: utf-8 -*-
"""T-105 (R-802): اختبارات الاسترجاع الطبقي — برهان القيمة السببية
(100 دور، سؤال عن قرار الدور-10 في الاتجاهين)، skip-on-timeout مع
اكتمال الحزمة، وقصر الطبقة على opportunistic نصًّا.
"""
from __future__ import annotations

import pathlib
import sys
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from context.engine import ContextEngine, ContextRequest  # noqa: E402
from context.facade import gather_message_context          # noqa: E402
from context.memory_layers import EpisodicLayer, RunDigest  # noqa: E402
from context.semantic_index import SemanticIndex            # noqa: E402
from context.sources.memory import (                        # noqa: E402
    MEMORY_TIER,
    MemorySource,
)
from sessions.store import SessionStore                     # noqa: E402


class KeywordAxisEmbedder:
    """مُضمِّن حتمي بمحاور كلمات مفتاحية — نفس نمط T-104."""
    AXES = ("postgres", "sqlite", "login", "css", "cache")

    def embed(self, texts):
        out = []
        for text in texts:
            vec = [1.0 if a in text.lower() else 0.0 for a in self.AXES]
            vec.append(0.0 if any(vec) else 1.0)
            out.append(vec)
        return out


class SlowEmbedder(KeywordAxisEmbedder):
    """مُضمِّن بطيء — لاختبار skip-on-timeout."""

    def __init__(self, delay: float):
        self._delay = delay

    def embed(self, texts):
        time.sleep(self._delay)
        return super().embed(texts)


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


@pytest.fixture()
def session_id(store: SessionStore) -> str:
    return store.create().id


@pytest.fixture()
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    return root


DECISION_TEXT = ("قررنا استخدام postgres بدل sqlite لقاعدة البيانات "
                 "بسبب الحاجة للتزامن")
QUERY = "ما هي قاعدة البيانات التي قررنا استخدامها — postgres أم غيرها؟"


def _hundred_turn_session(store, session_id, embedder=None):
    """جلسة 100 دور: القرار المهم عند الدور 10 ثم ثرثرة تدفنه.

    يبني الطبقتين: الدلالية تفهرس الأدوار، والحلقية تسجل حلقة الـ run
    الذي نفّذ القرار.
    """
    semantic = SemanticIndex(store, session_id,
                             embedder or KeywordAxisEmbedder())
    episodic = EpisodicLayer(store, session_id)
    items = []
    for i in range(100):
        text = (DECISION_TEXT if i == 10
                else f"دردشة عامة رقم {i} عن تنسيق الواجهة والألوان")
        store.append_message(session_id, "user", text)
        items.append((f"turn-{i}", text, "turn"))
    semantic.add_texts(items)
    episodic.summarize_and_record(RunDigest(
        run_id="run-db", goal="اختيار قاعدة البيانات",
        outcome="completed",
        files_touched=("db/schema.sql",),
        step_results=(("decide", DECISION_TEXT),),
    ))
    return semantic, episodic


# ═════════════ برهان القيمة السببية (بند القبول) ═════════════

@pytest.mark.integration
class TestCausalValue:

    def test_turn10_decision_retrieved_with_memory_on(self, store,
                                                      session_id, project):
        semantic, episodic = _hundred_turn_session(store, session_id)
        source = MemorySource(episodic=episodic, semantic=semantic)
        ctx = gather_message_context(project, QUERY, memory_source=source)
        # الاسترجاع لا يظهر في mentioned_files (مسارات رمزية) — نفحص
        # الحزمة نفسها عبر المحرك
        engine = ContextEngine([source])
        bundle = engine.gather(ContextRequest(message=QUERY,
                                              project_root=project))
        # المؤشر "sqlite" فريد لنص القرار — لا يظهر في الاستعلام نفسه
        texts = [it.content or "" for it in bundle.items]
        assert any("sqlite" in t for t in texts), \
            "قرار الدور-10 يجب أن يُسترجع مع الذاكرة مفعّلة"
        # الطبقتان حاضرتان: دلالي (turn-10) + حلقي (run-db)
        paths = [it.path for it in bundle.items]
        assert any(p.startswith("<memory:sem:") for p in paths)
        assert any(p == "<memory:episode:run-db>" for p in paths)
        # واجهة الـ facade سليمة (العقد القديم لم ينكسر)
        assert ctx.mentioned_files == []

    def test_turn10_decision_absent_with_memory_off(self, store,
                                                    session_id, project):
        """الاتجاه الثاني (بند القبول): بلا استرجاع السؤال يفشل."""
        _hundred_turn_session(store, session_id)
        ctx = gather_message_context(project, QUERY)   # بلا memory_source
        # المؤشر "sqlite" فريد لنص القرار (الاستعلام يحوي "postgres"
        # أصلًا فلا يصلح مؤشرًا سالبًا)
        assert "sqlite" not in ctx.user_text_with_files
        assert "sqlite" not in ctx.project_context
        # وحتى بمصدر خامل (طبقتان None) — لا شيء يُسترجع
        empty = ContextEngine([MemorySource()]).gather(
            ContextRequest(message=QUERY, project_root=project))
        assert list(empty.items) == []


# ═════════════ skip-on-timeout (بند القبول) ═════════════

@pytest.mark.integration
class TestTimeoutSkip:

    def test_forced_timeout_skips_source_bundle_still_built(
            self, store, session_id, project):
        semantic, episodic = _hundred_turn_session(
            store, session_id, embedder=SlowEmbedder(5.0))
        source = MemorySource(episodic=episodic, semantic=semantic,
                              timeout_seconds=0.2)
        start = time.monotonic()
        ctx = gather_message_context(project, QUERY, memory_source=source)
        elapsed = time.monotonic() - start
        # المصدر تخطى نفسه سريعًا — لم ينتظر المُضمِّن البطيء
        assert elapsed < 2.0, f"المهلة لم تُحترم: {elapsed:.2f}s"
        # الحزمة اكتملت: بنية المشروع حاضرة رغم غياب الذاكرة
        assert "app.py" in ctx.project_context

    def test_semantic_unavailable_episodic_still_contributes(
            self, store, session_id, project):
        """سقوط المزوّد يُسقط الجزء الدلالي فقط — الحلقي يستمر."""
        from context.embedding import EmbedderUnavailable

        class DownEmbedder:
            def embed(self, texts):
                raise EmbedderUnavailable("down")

        _, episodic = _hundred_turn_session(store, session_id)
        semantic = SemanticIndex(store, session_id, DownEmbedder())
        source = MemorySource(episodic=episodic, semantic=semantic)
        bundle = ContextEngine([source]).gather(
            ContextRequest(message=QUERY, project_root=project))
        paths = [it.path for it in bundle.items]
        assert not any(p.startswith("<memory:sem:") for p in paths)
        assert "<memory:episode:run-db>" in paths


# ═════════════ قصر الطبقة (بند القبول: tier grep) ═════════════

@pytest.mark.integration
class TestTierRestriction:

    def test_tier_constant_is_opportunistic_only(self):
        assert MEMORY_TIER == "opportunistic"

    def test_source_grep_no_other_tier_assignment(self):
        """grep نصّي: وحدة المصدر لا تذكر أي tier آخر كقيمة."""
        src = (REPO_ROOT / "context/sources/memory.py").read_text("utf-8")
        assert 'MEMORY_TIER = "opportunistic"' in src
        for banned in ('"must_have"', '"high"', '"normal"'):
            assert banned not in src, \
                f"tier {banned} مذكور في MemorySource — القصر انكسر"

    def test_budget_never_displaces_must_have_or_high(self, store,
                                                      session_id, project):
        """عناصر الذاكرة على opportunistic تُسقط أولًا تحت ضغط الميزانية."""
        from context.budget import BudgetItem, ContextBudget

        semantic, episodic = _hundred_turn_session(store, session_id)
        source = MemorySource(episodic=episodic, semantic=semantic)
        bundle = ContextEngine([source]).gather(
            ContextRequest(message=QUERY, project_root=project))
        items = [BudgetItem("user_request", "طلب المستخدم " * 5,
                            tier="must_have"),
                 BudgetItem("core.py", "كود جوهري " * 20, tier="high")]
        items += [BudgetItem(it.path, (it.content or "") * 10,
                             tier=MEMORY_TIER) for it in bundle.items]
        # 80 → ميزانية 72 توكن: تتسع للأساسيين (16+50=66) فقط،
        # فتُسقط عناصر الذاكرة (opportunistic) أولًا دون المساس بهما.
        packed = ContextBudget(model_window=80).pack(items)
        kept = {i.key for i in packed.kept}
        assert "user_request" in kept and "core.py" in kept
        dropped = {d.key for d in packed.dropped}
        assert any(k.startswith("<memory:") for k in dropped)


# ═════════════ انحدار goldens (الذاكرة الفارغة) ═════════════

@pytest.mark.integration
class TestGoldensRegression:

    def test_default_call_without_memory_source_identical(self, project):
        """بند الانحدار: بلا memory_source التركيبة القديمة حرفيًا —
        نفس مخرجات gather_message_context قبل T-105."""
        ctx_default = gather_message_context(project, "اشرح app.py")
        ctx_none = gather_message_context(project, "اشرح app.py",
                                          memory_source=None)
        assert ctx_default == ctx_none
        assert "app.py" in ctx_default.user_text_with_files

    def test_empty_memory_source_adds_nothing_to_outputs(self, store,
                                                         session_id,
                                                         project):
        """ذاكرة فارغة (جلسة بلا حلقات ولا فهرس) ⇒ المخرجات الثلاث
        مطابقة بايت-بايت للنداء بلا مصدر."""
        source = MemorySource(
            episodic=EpisodicLayer(store, session_id),
            semantic=SemanticIndex(store, session_id,
                                   KeywordAxisEmbedder()))
        with_mem = gather_message_context(project, "اشرح app.py",
                                          memory_source=source)
        without = gather_message_context(project, "اشرح app.py")
        assert with_mem == without
