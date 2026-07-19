# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  T-043 (R-503): Knowledge كـ view فوق ContextBundle
  + برومبتات delta لكل iteration

  يغطي:
  - dedup عند الإدراج: نفس المسار بنفس المحتوى يُبتلع؛
    جسد مطابق لمسار آخر = إحالة لا نسخة
  - delta: لا إعادة حقن لجسد كامل بعد أول إرسال —
    ما سبق إرساله سطر إحالة `path (hash…)`
  - recent-k: آخر k عناصر verbatim دائمًا
  - retention: اكتشاف iteration-1 ما زال حاضرًا
    (كإحالة) في iteration-8
  - منحنى التكلفة: 8 iterations — تكلفة الجولة مسطّحة
    ضمن 15% رغم نمو الجسم المتراكم
  - عنصر أسقطته الميزانية لا يُعلَّم مُرسلًا — يُعاد كاملًا
  - build_context (بلا حالة) باقٍ بنفس الأقسام — parity
    الاختبارات القديمة في test_budget_wiring / goldens
═══════════════════════════════════════════════════════
"""
import pytest

from chain.knowledge import KnowledgeAccumulator
from context.budget import CharsPerTokenEstimator


def _add_file(k: KnowledgeAccumulator, path: str, body: str) -> None:
    k.add_tool_result("read_file", {"path": path}, body)


# ═══════════════════════════════════════════════════════
#   Dedup عند الإدراج
# ═══════════════════════════════════════════════════════

class TestInsertDedup:

    def test_same_path_same_content_swallowed(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "body-A")
        _add_file(k, "a.py", "body-A")     # إعادة قراءة بلا تغيير
        assert len(k._bundle) == 1
        assert k.files_count == 1

    def test_same_content_other_path_is_reference(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "shared-body")
        _add_file(k, "copy.py", "shared-body")
        entries = k._bundle.entries
        assert len(entries) == 2
        assert entries[1].is_reference
        assert entries[1].duplicate_of == "a.py"
        # العرض الكامل: الجسد مرة واحدة + ملاحظة إحالة
        ctx = k.build_context()
        assert ctx.count("shared-body") == 1
        assert "copy.py" in ctx and "مطابق" in ctx

    def test_same_path_new_content_creates_revision(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "v1")
        _add_file(k, "a.py", "v2-changed")
        assert len(k._bundle) == 2
        ctx = k.build_context()
        assert "v2-changed" in ctx          # النسخة الجديدة تُعرض
        assert k.files_count == 1           # نفس الملف منطقيًا

    def test_summary_counts_deduped(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "x")
        _add_file(k, "a.py", "x")
        k.add_tool_result("list_dir", {"path": "src"}, "listing")
        k.add_tool_result("search_code", {"query": "q"}, "hits")
        k.add_tool_result("run_command", {"command": "ls"}, "out")
        s = k.get_summary()
        assert s["files_read"] == 1
        assert s["dirs_listed"] == 1
        assert s["searches"] == 1
        assert s["commands"] == 1
        assert s["tools_used"] == 5         # سجل الأدوات الخام كامل


# ═══════════════════════════════════════════════════════
#   Delta rendering + recent-k
# ═══════════════════════════════════════════════════════

class TestDeltaRendering:

    def test_first_send_verbatim_second_send_reference(self):
        k = KnowledgeAccumulator()
        _add_file(k, "core.py", "CORE-BODY-" * 20)
        first = k.build_iteration_context(recent_k=0)
        assert "CORE-BODY-" in first        # أول إرسال: جسد كامل

        second = k.build_iteration_context(recent_k=0)
        assert "CORE-BODY-" not in second   # لا إعادة حقن
        assert "core.py" in second          # إحالة سطرية
        assert "سبق إرساله" in second

    def test_reference_line_carries_hash(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "hash-me")
        k.build_iteration_context(recent_k=0)
        ref = k.build_iteration_context(recent_k=0)
        from context.bundle import content_hash
        assert content_hash("hash-me")[:8] in ref

    def test_recent_k_floor_keeps_latest_verbatim(self):
        k = KnowledgeAccumulator()
        for i in range(5):
            _add_file(k, f"f{i}.py", f"BODY-{i}-" * 10)
        k.build_iteration_context(recent_k=2)      # الكل أُرسل
        out = k.build_iteration_context(recent_k=2)
        # آخر عنصرين verbatim رغم سبق إرسالهما
        assert "BODY-4-" in out and "BODY-3-" in out
        # الأقدم إحالات
        assert "BODY-0-" not in out and "BODY-1-" not in out
        assert "f0.py" in out and "f1.py" in out

    def test_new_item_between_iterations_rendered_full(self):
        k = KnowledgeAccumulator()
        _add_file(k, "old.py", "OLD-BODY-" * 10)
        k.build_iteration_context(recent_k=0)
        _add_file(k, "new.py", "NEW-BODY-" * 10)
        out = k.build_iteration_context(recent_k=0)
        assert "NEW-BODY-" in out           # الجديد كامل
        assert "OLD-BODY-" not in out       # القديم إحالة
        assert "old.py" in out

    def test_dropped_by_budget_not_marked_sent(self):
        k = KnowledgeAccumulator()
        big = "G" * 40000                   # ≈10k توكن — فوق الميزانية
        _add_file(k, "giant.py", big)
        out1 = k.build_iteration_context(max_tokens=1000, recent_k=0)
        assert big not in out1              # أُسقط
        # الجولة التالية بميزانية كافية — يُعرض كاملًا (لم يُعلَّم مُرسلًا)
        out2 = k.build_iteration_context(max_tokens=20000, recent_k=0)
        assert big in out2

    def test_observations_and_errors_always_attached(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "body")
        k.add_observation("الملف يستخدم Flask")
        k.add_error("فشل أمر سابق")
        k.build_iteration_context(recent_k=0)
        out = k.build_iteration_context(recent_k=0)
        assert "الملف يستخدم Flask" in out  # النواة الثابتة في كل إرسال
        assert "فشل أمر سابق" in out

    def test_clear_resets_sent_state(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "AGAIN-" * 5)
        k.build_iteration_context(recent_k=0)
        k.clear()
        _add_file(k, "a.py", "AGAIN-" * 5)
        out = k.build_iteration_context(recent_k=0)
        assert "AGAIN-" in out              # بعد clear يُرسل من جديد


# ═══════════════════════════════════════════════════════
#   Retention — اكتشاف الجولة 1 حاضر في الجولة 8
# ═══════════════════════════════════════════════════════

class TestRetention:

    def test_iteration1_finding_present_at_iteration8(self):
        k = KnowledgeAccumulator()
        _add_file(k, "finding.py", "IMPORTANT-FINDING-" * 10)
        k.next_iteration()
        first = k.build_iteration_context(recent_k=2)
        assert "IMPORTANT-FINDING-" in first

        last = ""
        for i in range(2, 9):               # iterations 2..8
            k.next_iteration()
            _add_file(k, f"later{i}.py", f"LATER-{i}-" * 10)
            last = k.build_iteration_context(recent_k=2)

        # في الجولة 8: الاكتشاف الأول ما زال مُشارًا إليه بالاسم + hash
        assert "finding.py" in last
        from context.bundle import content_hash
        assert content_hash("IMPORTANT-FINDING-" * 10)[:8] in last
        # لكن جسده غير مُعاد
        assert "IMPORTANT-FINDING-" not in last

    def test_observation_from_iteration1_still_verbatim_at_8(self):
        k = KnowledgeAccumulator()
        k.add_observation("خلاصة الجولة الأولى: البنية MVC")
        for i in range(8):
            k.next_iteration()
            _add_file(k, f"f{i}.py", f"B{i}" * 5)
            out = k.build_iteration_context(recent_k=2)
        assert "خلاصة الجولة الأولى: البنية MVC" in out


# ═══════════════════════════════════════════════════════
#   منحنى التكلفة — 8 iterations مسطّح ضمن 15%
# ═══════════════════════════════════════════════════════

class TestTokenCostCurve:

    def test_iteration_cost_flat_within_15_percent(self):
        """
        بوابة قبول T-043: كل جولة يُقرأ فيها ملف جديد (~500 توكن).
        قديمًا: الجولة n تعيد حقن n أجساد ⇒ تكلفة خطية متصاعدة.
        الآن: جسد الجولة الجديد + إحالات سطرية ⇒ مسطّح ضمن 15%.
        """
        k = KnowledgeAccumulator()
        est = CharsPerTokenEstimator()
        body = "x" * 2000                   # ≈500 توكن لكل ملف
        costs: list[int] = []
        for i in range(8):
            k.next_iteration()
            _add_file(k, f"module_{i}.py", f"# file {i}\n{body}")
            ctx = k.build_iteration_context(max_tokens=8000, recent_k=1)
            costs.append(est.estimate(ctx))

        # الاستقرار بعد الجولة الأولى (الجولة 1 بلا إحالات أصلًا):
        steady = costs[1:]
        lo, hi = min(steady), max(steady)
        assert hi <= lo * 1.15, \
            f"منحنى التكلفة غير مسطّح: {costs} (تفاوت {hi/lo:.2f}x)"

    def test_legacy_full_reinjection_would_grow(self):
        """
        توثيق تنفيذي للمشكلة المُصلحة: العرض الكامل (بلا حالة)
        ينمو خطيًا مع الجولات — وهو ما كان يُرسل كل جولة قديمًا.
        """
        k = KnowledgeAccumulator()
        est = CharsPerTokenEstimator()
        body = "y" * 2000
        full_costs = []
        for i in range(8):
            _add_file(k, f"m{i}.py", f"# {i}\n{body}")
            full_costs.append(est.estimate(k.build_context(max_tokens=50000)))
        assert full_costs[-1] > full_costs[0] * 4   # نموّ خطي واضح

    def test_no_full_content_reinjection_after_first_send(self):
        """معيار قبول R-503 حرفيًا: لا إعادة حقن جسد كامل بعد أول إرسال."""
        k = KnowledgeAccumulator()
        marker = "UNIQUE-CONTENT-MARKER-12345"
        _add_file(k, "once.py", marker * 3)
        sends = [k.build_iteration_context(recent_k=0) for _ in range(4)]
        assert marker in sends[0]
        for later in sends[1:]:
            assert marker not in later


# ═══════════════════════════════════════════════════════
#   Parity — build_context بلا حالة (سلوك T-024 محفوظ)
# ═══════════════════════════════════════════════════════

class TestFullViewParity:

    def test_build_context_is_stateless(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "STATELESS-BODY")
        c1 = k.build_context()
        c2 = k.build_context()
        assert c1 == c2
        assert "STATELESS-BODY" in c2       # لا يتأثر بحالة الإرسال

    def test_build_context_not_affected_by_iteration_sends(self):
        k = KnowledgeAccumulator()
        _add_file(k, "a.py", "FULL-VIEW-BODY")
        k.build_iteration_context(recent_k=0)   # يعلّم كمُرسل
        assert "FULL-VIEW-BODY" in k.build_context()

    def test_sections_render_all_kinds(self):
        k = KnowledgeAccumulator()
        _add_file(k, "f.py", "file-body")
        k.add_tool_result("list_dir", {"path": "src"}, "dir-listing")
        k.add_tool_result("search_code", {"query": "needle"}, "search-hits")
        k.add_tool_result("run_command", {"command": "make"}, "cmd-out")
        ctx = k.build_context()
        assert "📂 [ملفات تم قراءتها]" in ctx and "--- f.py ---" in ctx
        assert "📁 [مجلدات تم استعراضها]" in ctx and "src/:" in ctx
        assert "🔍 [نتائج بحث]" in ctx and "بحث: needle" in ctx
        assert "⚡ [أوامر تم تنفيذها]" in ctx and "$ make" in ctx

    def test_empty_accumulator_returns_empty(self):
        k = KnowledgeAccumulator()
        assert k.build_context() == ""
        assert k.build_iteration_context() == ""

    def test_raw_files_read_store_removed(self):
        """معيار قبول R-503: مخزن _files_read الخام محذوف."""
        import pathlib
        src = pathlib.Path("chain/knowledge.py").read_text(encoding="utf-8")
        assert "_files_read: dict" not in src
        assert "_dirs_listed: dict" not in src
        k = KnowledgeAccumulator()
        assert not hasattr(k, "_files_read")
