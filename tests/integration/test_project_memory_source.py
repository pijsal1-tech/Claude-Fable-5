# -*- coding: utf-8 -*-
"""T-113 (R-805): تقطير ما-بعد-الـ-run + مصدر ذاكرة المشروع بميزانية.

بنود القبول: **الاختبار الرئيس** — جلسة ثانية تجيب عن سؤال أعراف بلا
إعادة قراءة الملفات (عدد نداءات الأدوات أقل مع الذاكرة مفعّلة)؛
الميزانية محترمة تحت حزمة مزدحمة؛ مدخلة قديمة تُعلَّم بعد تغيير ملف
الـ fixture؛ وانحدار goldens: الذاكرة الفارغة لا تغيّر شيئًا.
"""
from __future__ import annotations

import pathlib
import sys
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from context.engine import ContextEngine, ContextRequest      # noqa: E402
from context.facade import gather_message_context             # noqa: E402
from context.index import ProjectIndex                        # noqa: E402
from context.memory_layers import EpisodeRecord               # noqa: E402
from context.sources.project_memory import (                  # noqa: E402
    MAX_ENTRIES,
    PROJECT_MEMORY_TIER,
    ProjectMemorySource,
)
from core.project_memory import (                             # noqa: E402
    MAX_DISTILLED_DECISIONS,
    ProjectMemoryStore,
    distill_and_record,
    distill_episode,
    index_fingerprint,
    is_stale,
)

PID = "proj0123abcd"

CONVENTION = ("كل اختبارات المشروع تعيش في مجلد tests/unit حصريًا "
              "وتُشغَّل عبر pytest")
QUERY = "في أي مجلد تعيش اختبارات المشروع وكيف تُشغَّل؟"


@pytest.fixture()
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "CONVENTIONS.md").write_text(
        CONVENTION + "\n", encoding="utf-8")
    return root


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> ProjectMemoryStore:
    return ProjectMemoryStore(tmp_path / "projects")


# ═════════════ التقطير ما-بعد-الـ-run ═════════════

@pytest.mark.integration
class TestDistillation:

    EPISODE = EpisodeRecord(
        run_id="run-t113", goal="توحيد مكان الاختبارات",
        outcome="completed",
        files_touched=("tests/unit/test_app.py",),
        key_decisions=("الاختبارات في tests/unit",
                       "التشغيل عبر pytest فقط"),
    )

    def test_proposals_summary_plus_decisions(self):
        proposals = distill_episode(self.EPISODE)
        kinds = [k for k, _ in proposals]
        assert kinds == ["run_summary", "decision", "decision"]
        summary = proposals[0][1]
        # ملخص T-103 يُعاد استخدامه: الهدف → النتيجة + الملفات
        assert "توحيد مكان الاختبارات" in summary
        assert "completed" in summary
        assert "tests/unit/test_app.py" in summary

    def test_decisions_capped(self):
        ep = EpisodeRecord(run_id="r", goal="g", outcome="ok",
                           key_decisions=tuple(f"قرار {i}"
                                               for i in range(10)))
        proposals = distill_episode(ep)
        decisions = [t for k, t in proposals if k == "decision"]
        assert len(decisions) == MAX_DISTILLED_DECISIONS

    def test_empty_episode_no_proposals(self):
        assert distill_episode(EpisodeRecord(
            run_id="r", goal="", outcome="")) == []

    def test_record_stamps_distillation_provenance(self, store, project):
        index = ProjectIndex(project)
        written = distill_and_record(store, PID, self.EPISODE, index=index)
        entries = store.entries(PID)
        assert len(entries) == len(written) == 3
        for e in entries:
            assert e.source == "distillation"          # provenance: من
            assert e.run_id == "run-t113"              # provenance: أي run
            assert e.created_at                        # provenance: متى
            assert e.index_hash == index_fingerprint(index)  # hash-link

    def test_record_never_raises(self, project):
        """عقد التدهور: فشل الكتابة ⇒ لا استثناء يتسرب (مشتق اختياري)."""
        class BoomStore:
            def remember(self, *a, **k):
                raise OSError("disk full")
        assert distill_and_record(BoomStore(), PID, self.EPISODE) == []


# ═════════════ الاختبار الرئيس (R-805 headline) ═════════════

def _make_agent(project: pathlib.Path, answered: str):
    """AgentLoop حقيقي بـ send_fn مبرمج: يجيب فورًا إن رأى الإجابة في
    الـ prompt، وإلا يطلب قراءة ملف الأعراف (نفس مسار الإنتاج —
    parse_tool_calls → execute). يعيد (loop, tools, executed_tools)."""
    from chain.agent_loop import AgentLoop
    from chain.agent_tools import AgentTools

    tools = AgentTools(project_root=str(project))
    executed: list[str] = []
    orig_execute = tools.execute

    def counting_execute(call):
        executed.append(call.tool)
        return orig_execute(call)

    tools.execute = counting_execute  # type: ignore[method-assign]

    def send_fn(prompt, history, system_prompt):
        if answered in prompt:
            return "الإجابة: الاختبارات تعيش في tests/unit وتُشغَّل عبر pytest."
        return ("سأقرأ ملف الأعراف أولًا.\n"
                "```TOOL: read_file\n"
                "path: CONVENTIONS.md\n"
                "```")

    loop = AgentLoop(tools=tools, send_fn=send_fn, max_iterations=4)
    return loop, executed


@pytest.mark.integration
class TestHeadlineSecondSession:

    def test_second_session_answers_without_rereading_files(
            self, store, project):
        """بند القبول نصًّا: الجلسة الثانية تجيب عن سؤال الأعراف بلا
        إعادة قراءة الملفات — عدد نداءات الأدوات أقل مع الذاكرة."""
        # ── الجلسة الأولى: بلا ذاكرة — الوكيل مضطر يقرأ الملف ──
        loop1, executed1 = _make_agent(project, answered="tests/unit")
        reply1 = loop1.run(QUERY, project_context="")
        assert "tests/unit" in reply1
        assert executed1.count("read_file") >= 1     # دفع ثمن الاستكشاف

        # الجلسة الأولى تحفظ العرف (نفس ما تفعله remember_fact/التقطير)
        store.remember(PID, "convention", CONVENTION,
                       index=ProjectIndex(project))

        # ── الجلسة الثانية: الذاكرة تُقدَّم في السياق قبل السؤال ──
        source = ProjectMemorySource(store, PID,
                                     index=ProjectIndex(project))
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        memory_context = "\n\n".join(it.content or "" for it in bundle.items)
        assert "tests/unit" in memory_context        # الذاكرة استرجعت العرف

        loop2, executed2 = _make_agent(project, answered="tests/unit")
        reply2 = loop2.run(QUERY, project_context=memory_context)
        assert "tests/unit" in reply2
        # الحكم: صفر قراءة ملفات — أقل صراحةً من الجلسة الأولى
        assert executed2.count("read_file") == 0
        assert executed2.count("read_file") < executed1.count("read_file")

    def test_symbolic_paths_stay_out_of_mentioned_files(self, store,
                                                        project):
        """العقد القديم سليم: مسارات <memory:project:...> رمزية لا
        تدخل mentioned_files عبر الـ facade."""
        store.remember(PID, "convention", CONVENTION)
        source = ProjectMemorySource(store, PID)
        ctx = gather_message_context(project, QUERY, memory_source=source)
        assert all(not p.startswith("<memory:")
                   for p in ctx.mentioned_files)


# ═════════════ الميزانية تحت حزمة مزدحمة (بند القبول) ═════════════

@pytest.mark.integration
class TestBudgetBound:

    def test_memory_dropped_first_under_pressure(self, store, project):
        """عناصر الذاكرة (opportunistic) تسقط أولًا — must_have/high
        لا يُمسّان تحت ميزانية ضيقة."""
        from context.budget import BudgetItem, ContextBudget

        for i in range(4):
            store.remember(PID, "fact",
                           f"حقيقة {i}: اختبارات المشروع في tests/unit")
        source = ProjectMemorySource(store, PID)
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        assert bundle.items                          # الحزمة مزدحمة فعلًا
        items = [BudgetItem("user_request", "طلب المستخدم " * 5,
                            tier="must_have"),
                 BudgetItem("core.py", "كود جوهري " * 20, tier="high")]
        items += [BudgetItem(it.path, (it.content or "") * 10,
                             tier=PROJECT_MEMORY_TIER)
                  for it in bundle.items]
        packed = ContextBudget(model_window=80).pack(items)
        kept = {i.key for i in packed.kept}
        assert "user_request" in kept and "core.py" in kept
        dropped = {d.key for d in packed.dropped}
        assert any(k.startswith("<memory:project:") for k in dropped)

    def test_max_entries_cap_respected(self, store, project):
        for i in range(MAX_ENTRIES + 5):
            store.remember(PID, "fact",
                           f"حقيقة {i} عن اختبارات المشروع")
        source = ProjectMemorySource(store, PID)
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        assert len(bundle.items) == MAX_ENTRIES


# ═════════════ الـ staleness (بند القبول: flip بعد تغيير ملف) ═════════════

@pytest.mark.integration
class TestStaleness:

    def test_flag_flips_after_fixture_file_change(self, store, project):
        """بند القبول نصًّا: تغيير ملف fixture (إضافة) يقلب العلم —
        المدخلة تُعلَّم [STALE] ولا تُقدَّم كطازجة بصمت."""
        index = ProjectIndex(project)
        entry = store.remember(PID, "convention", CONVENTION, index=index)
        assert not is_stale(entry, index)            # طازجة وقت التسجيل

        source = ProjectMemorySource(store, PID, index=index)
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        assert "[MEMORY" in (bundle.items[0].content or "")
        assert "STALE" not in (bundle.items[0].content or "")

        # تغيير البنية: ملف جديد ⇒ بصمة الفهرس تنحرف
        (project / "new_module.py").write_text("x = 1\n", encoding="utf-8")
        index.rebuild()
        assert is_stale(entry, index)                # العلم انقلب

        bundle2 = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        content = bundle2.items[0].content or ""
        assert content.startswith("[STALE ")         # مُعلَّمة صراحة
        assert CONVENTION in content                 # لكنها لم تُحذف

    def test_stale_down_ranked_below_fresh(self, store, project):
        """down-rank مطلق: القديمة بعد الطازجة مهما بلغ تداخلها."""
        index = ProjectIndex(project)
        # قديمة بتداخل أعلى (نص السؤال كله تقريبًا)
        store.remember(PID, "fact",
                       "مجلد اختبارات المشروع تعيش وتُشغَّل هنا",
                       index=index)
        (project / "drift.py").write_text("y = 2\n", encoding="utf-8")
        index.rebuild()
        # طازجة بتداخل أدنى — مسجّلة على البصمة الحالية
        store.remember(PID, "convention",
                       "اختبارات المشروع عبر pytest", index=index)

        source = ProjectMemorySource(store, PID, index=index)
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        contents = [it.content or "" for it in bundle.items]
        assert len(contents) == 2
        assert not contents[0].startswith("[STALE")  # الطازجة أولًا
        assert contents[1].startswith("[STALE ")     # القديمة نُزّلت

    def test_no_link_or_no_index_means_no_verdict(self, store, project):
        """بصمة غائبة من أي طرف = لا حكم (ليست staleness)."""
        index = ProjectIndex(project)
        no_link = store.remember(PID, "fact", "حقيقة بلا فهرس")
        assert no_link.index_hash == ""
        assert not is_stale(no_link, index)          # لا رابط أصلًا
        linked = store.remember(PID, "fact", "حقيقة مربوطة", index=index)
        assert not is_stale(linked, None)            # لا فهرس حي


# ═════════════ عقود المصدر (tier + مهلة + تدهور) ═════════════

@pytest.mark.integration
class TestSourceContracts:

    def test_tier_constant_is_opportunistic_only(self):
        assert PROJECT_MEMORY_TIER == "opportunistic"

    def test_source_grep_no_other_tier_assignment(self):
        """grep نصّي: وحدة المصدر لا تذكر أي tier آخر كقيمة —
        نفس بوابة T-105 حرفيًا."""
        src = (REPO_ROOT / "context/sources/project_memory.py"
               ).read_text("utf-8")
        assert 'PROJECT_MEMORY_TIER = "opportunistic"' in src
        for banned in ('"must_have"', '"high"', '"normal"'):
            assert banned not in src, \
                f"tier {banned} مذكور في ProjectMemorySource — القصر انكسر"

    def test_source_grep_no_raw_reads(self):
        """حدود SafeReader: المصدر لا يقرأ ملفات — I/O كله في core/."""
        src = (REPO_ROOT / "context/sources/project_memory.py"
               ).read_text("utf-8")
        for banned in ("open(", ".read_text(", ".read_bytes("):
            assert banned not in src, \
                f"قراءة خام {banned} في مصدر context/ — حدود R-204 انكسرت"

    def test_slow_store_skipped_bundle_still_built(self, store, project):
        """المهلة async fallback-to-skip: مخزن بطيء ⇒ [] سريعًا."""
        class SlowStore:
            def entries(self, pid):
                time.sleep(5.0)
                return []
        source = ProjectMemorySource(SlowStore(), PID, timeout_seconds=0.2)
        start = time.monotonic()
        ctx = gather_message_context(project, QUERY, memory_source=source)
        assert time.monotonic() - start < 2.0
        assert "app.py" in ctx.project_context       # الحزمة اكتملت بدوننا

    def test_corrupt_store_contributes_nothing(self, store, project):
        """CorruptMemoryError داخل الاسترجاع ⇒ skip لا انفجار."""
        from core.project_memory import CorruptMemoryError

        class CorruptStore:
            def entries(self, pid):
                raise CorruptMemoryError("tampered")
        source = ProjectMemorySource(CorruptStore(), PID)
        bundle = ContextEngine([source]).gather(ContextRequest(
            message=QUERY, project_root=project))
        assert list(bundle.items) == []


# ═════════════ انحدار goldens (الذاكرة الفارغة) ═════════════

@pytest.mark.integration
class TestGoldensRegression:

    def test_empty_memory_identical_to_no_memory(self, store, project):
        """بند الانحدار نصًّا: goldens السياق لا تتغير والذاكرة فارغة —
        مصدر فوق مخزن فارغ = غياب المصدر بايت-بايت."""
        source = ProjectMemorySource(store, PID)     # مخزن بلا مدخلات
        ctx_with = gather_message_context(project, "اشرح app.py",
                                          memory_source=source)
        ctx_without = gather_message_context(project, "اشرح app.py")
        assert ctx_with == ctx_without
