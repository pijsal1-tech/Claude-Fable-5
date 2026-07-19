# -*- coding: utf-8 -*-
"""اختبارات T-024: توصيل ContextBudget بمسارات البرومبت (R-203).

المواقع الثلاثة المستبدلة:
1. ``chain/context_builder.py`` — build_prompt_section (كان per_item_max +
   max_total بالحروف).
2. ``chain/knowledge.py`` — build_context (كان content[:2000] + [:500] +
   [:300] + قص نهائي max_tokens*4).
3. ``chain/orchestrator.py`` — _split_content (كان len//4 مبعثرًا؛ الآن
   المقدّر المركزي CharsPerTokenEstimator).
+ ``build_delegate`` في strategies (كان content[:2000] لكل ملف).
+ مفتاح الضبط ``context_budget`` في config.yaml عبر ``from_config``.
"""
import pathlib

import pytest

from chain.context_builder import ContextBuilder, ContextItem, ContextResult
from chain.knowledge import KnowledgeAccumulator
from chain.orchestrator import SmartOrchestrator
from chain.strategies import build_delegate
from context.budget import (
    DEFAULT_MODEL_WINDOW,
    DEFAULT_RESERVED_OUTPUT,
    DEFAULT_SAFETY_MARGIN,
    CharsPerTokenEstimator,
    ContextBudget,
)


# ═══════════════ Site 1: ContextResult.build_prompt_section ═══════════════

class TestContextBuilderWiring:
    def _result(self, items):
        r = ContextResult()
        r.items.extend(items)
        return r

    def test_no_mid_truncation_marker(self):
        """العنصر يدخل كاملًا أو يسقط — لا قصّ في المنتصف."""
        r = self._result([
            ContextItem("file", "a.py", "x" * 20000, size=20000),
        ])
        section = r.build_prompt_section(max_total=100000)
        assert "مقطوع" not in section
        assert "وقف الإرفاق" not in section
        assert "x" * 20000 in section  # المحتوى كامل

    def test_drop_by_tier_tree_before_file(self):
        """opportunistic (شجرة) تسقط قبل high (ملف) عند ضيق الميزانية."""
        file_body = "F" * 4000     # ≈1000 توكن
        tree_body = "T" * 4000
        r = self._result([
            ContextItem("file", "main.py", file_body, size=len(file_body)),
            ContextItem("tree", "project_root", tree_body),
        ])
        # ميزانية تكفي عنصرًا واحدًا فقط (بالحروف legacy: 1500*4=6000 حرف)
        section = r.build_prompt_section(max_total=6000)
        assert file_body in section          # الملف المذكور سليم كاملًا
        assert tree_body not in section      # الشجرة أُسقطت
        assert "أُسقط 1 عنصر سياق" in section

    def test_explicit_budget_overrides_max_total(self):
        body = "y" * 4000
        r = self._result([ContextItem("file", "b.py", body, size=len(body))])
        tiny = ContextBudget(model_window=10, reserved_output=0,
                             safety_margin=0.0)
        section = r.build_prompt_section(max_total=10**9, budget=tiny)
        assert body not in section
        assert "أُسقط 1 عنصر سياق" in section

    def test_everything_fits_all_present(self):
        r = self._result([
            ContextItem("file", "a.py", "AAA", size=3),
            ContextItem("dir", "src", "listing"),
            ContextItem("search", "main", "src/a.py:1: def main"),
        ])
        section = r.build_prompt_section(max_total=50000)
        assert "AAA" in section and "listing" in section
        assert "أُسقط" not in section

    def test_failed_items_excluded(self):
        r = self._result([
            ContextItem("file", "missing.py", "❌ ملف غير موجود",
                        success=False),
            ContextItem("file", "ok.py", "OK", size=2),
        ])
        section = r.build_prompt_section()
        assert "OK" in section and "غير موجود" not in section

    def test_tier_map_covers_known_kinds(self):
        for kind in ("file", "dir", "search", "deps", "tree", "info"):
            assert ContextResult.TIER_BY_KIND[kind] in (
                "must_have", "high", "normal", "opportunistic")


# ═══════════════ Site 2: KnowledgeAccumulator.build_context ═══════════════

class TestKnowledgeWiring:
    def test_no_mid_truncation_of_file_content(self):
        """كان content[:2000] — الآن المحتوى كامل أو القسم يسقط."""
        k = KnowledgeAccumulator()
        body = "z" * 9000
        k.add_tool_result("read_file", {"path": "big.py"}, body)
        ctx = k.build_context(max_tokens=8000)
        assert body in ctx                      # كامل — لا [:2000]
        assert "حرف إجمالي" not in ctx
        assert "تم اختصار السياق" not in ctx    # القص النهائي حُذف

    def test_search_results_not_sliced(self):
        """كان s['result'][:500] — الآن النتيجة كاملة."""
        k = KnowledgeAccumulator()
        res = "R" * 1200
        k.add_tool_result("search_code", {"query": "q"}, res)
        ctx = k.build_context(max_tokens=8000)
        assert res in ctx

    def test_command_results_not_sliced(self):
        """كان c['result'][:300] — الآن النتيجة كاملة."""
        k = KnowledgeAccumulator()
        res = "C" * 900
        k.add_tool_result("run_command", {"command": "ls"}, res)
        ctx = k.build_context(max_tokens=8000)
        assert res in ctx

    def test_drops_normal_before_high_under_pressure(self):
        """المجلدات (normal) تسقط قبل الملفات المقروءة (high)."""
        k = KnowledgeAccumulator()
        file_body = "F" * 4000    # ≈1000 توكن
        k.add_tool_result("read_file", {"path": "core.py"}, file_body)
        k.add_tool_result("list_dir", {"path": "src"}, "D" * 4000)
        ctx = k.build_context(max_tokens=1200)
        assert file_body in ctx
        assert "D" * 4000 not in ctx
        assert "أُسقط" in ctx

    def test_total_within_budget_when_not_overflowed(self):
        k = KnowledgeAccumulator()
        for i in range(6):
            k.add_tool_result("read_file", {"path": f"f{i}.py"}, "b" * 2000)
        max_tokens = 1500
        ctx = k.build_context(max_tokens=max_tokens)
        est = CharsPerTokenEstimator()
        # الميزانية = max_tokens بهامش 10% — المخرج المحزوم لا يتعداها
        # (الفواصل \n والملاحظة الختامية هامشية)
        limit = ContextBudget(model_window=max_tokens).budget_tokens
        assert est.estimate(ctx) <= limit + 50

    def test_empty_knowledge_returns_empty(self):
        assert KnowledgeAccumulator().build_context() == ""


# ═══════════════ Site 3: SmartOrchestrator._split_content ═══════════════

class TestSplitContentWiring:
    def test_small_content_single_chunk(self):
        o = SmartOrchestrator()
        assert o._split_content("hello", 100) == ["hello"]

    def test_empty_content(self):
        o = SmartOrchestrator()
        assert o._split_content("", 100) == [""]

    def test_chunks_respect_budget_via_central_estimator(self):
        o = SmartOrchestrator()
        content = "\n".join(f"line {i} " + "x" * 40 for i in range(400))
        budget = 500
        chunks = o._split_content(content, budget)
        assert len(chunks) > 1
        est = CharsPerTokenEstimator()
        # كل chunk ضمن الميزانية (+ سماحية سطر واحد كالسلوك القديم)
        for ch in chunks:
            assert est.estimate(ch) <= budget + 60
        # لا فقد للمحتوى: كل الأسطر موجودة
        joined = "\n".join(chunks)
        for i in (0, 199, 399):
            assert f"line {i} " in joined

    def test_file_boundary_split_preserved(self):
        o = SmartOrchestrator()
        B = "======== END OF SOURCE CODE ========"
        seg = "s" * 4000
        content = f"{seg}\n{B}\n{seg}\n{B}\n{seg}"
        chunks = o._split_content(content, 1200)
        assert len(chunks) >= 2
        assert sum(c.count("s" * 100) for c in chunks) > 0


# ═══════════════ build_delegate files_block ═══════════════

class TestDelegateWiring:
    def test_small_files_intact_no_truncation(self):
        """ملفات صغيرة → نفس الشكل legacy لكن بالمحتوى الكامل."""
        body = "print('hi')\n" * 100   # 1200 حرف — كان يمر < 2000 قديمًا
        result = build_delegate("عدّل", files={"app.py": body})
        brief = result.steps[0].prompt_template
        assert f"\n\n📄 app.py:\n```\n{body}\n```" in brief

    def test_large_file_full_not_cut_at_2000(self):
        """كان content[:2000] — الآن الملف كامل ضمن الميزانية."""
        body = "L" * 12000
        result = build_delegate("عدّل", files={"big.py": body})
        brief = result.steps[0].prompt_template
        assert body in brief             # 12000 حرف كاملة (كان يُبتر عند 2000)

    def test_oversized_files_dropped_with_note(self):
        """ملفات تتجاوز الميزانية → إسقاط الأكبر أولًا مع ملاحظة مرصودة."""
        window = DEFAULT_MODEL_WINDOW    # الميزانية الافتراضية
        huge = "H" * (window * 4)        # وحده يتجاوز budget_tokens
        small = "s" * 100
        result = build_delegate("عدّل", files={"huge.py": huge,
                                               "small.py": small})
        brief = result.steps[0].prompt_template
        assert small in brief
        assert huge not in brief
        assert "أُسقطت ملفات لتجاوز ميزانية" in brief
        assert "huge.py" in brief        # الاسم مذكور في الملاحظة

    def test_no_files_empty_block(self):
        result = build_delegate("عدّل")
        assert "📄" not in result.steps[0].prompt_template


# ═══════════════ config knob: from_config ═══════════════

class TestFromConfig:
    def test_reads_section(self):
        b = ContextBudget.from_config({"context_budget": {
            "model_window": 1000, "reserved_output": 100,
            "safety_margin": 0.0}})
        assert b.budget_tokens == 900

    def test_defaults_when_missing(self):
        for cfg in (None, {}, {"context_budget": {}}):
            b = ContextBudget.from_config(cfg)
            assert b.model_window == DEFAULT_MODEL_WINDOW
            assert b.reserved_output == DEFAULT_RESERVED_OUTPUT
            assert b.safety_margin == DEFAULT_SAFETY_MARGIN

    def test_repo_config_yaml_section_parses(self):
        """قسم context_budget في config.yaml الفعلي صالح للبناء."""
        yaml = pytest.importorskip("yaml")
        cfg_path = pathlib.Path(__file__).resolve().parents[2] / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert "context_budget" in cfg
        b = ContextBudget.from_config(cfg)
        assert b.budget_tokens > 0


# ═══════════════ Oversize E2E (معيار قبول) ═══════════════

class TestOversizeE2E:
    def test_oversized_project_under_budget_mentions_intact(self, tmp_path):
        """مشروع ضخم: القسم النهائي داخل الميزانية والملف المذكور كامل."""
        (tmp_path / "app.py").write_text("def main():\n    return 42\n",
                                         encoding="utf-8")
        # ضجيج ضخم يستفز الإسقاط: ملف مذكور ~80KB (< max_file_size=100KB)
        # ≈20000 توكن — وحده يتجاوز الميزانية أدناه (4500 توكن).
        (tmp_path / "noise.py").write_text("# noise\n" + "n" * 80000,
                                           encoding="utf-8")
        builder = ContextBuilder(str(tmp_path))
        result = builder.gather("اقرأ app.py و noise.py")
        assert result.files_count >= 2

        max_total = 20000    # ميزانية ضيقة (حروف legacy → توكنز)
        section = result.build_prompt_section(max_total=max_total)

        est = CharsPerTokenEstimator()
        limit = ContextBudget(model_window=max(1, max_total // 4),
                              reserved_output=0).budget_tokens
        # الرأس + التذييل + ملاحظة الإسقاط خارج الحزم — سماحية صغيرة
        assert est.estimate(section) <= limit + 200
        # الملف المذكور موجود كاملًا — بلا بتر في المنتصف
        assert "def main():" in section and "return 42" in section
        assert "مقطوع" not in section
        # الضجيج الضخم أُسقط مرصودًا
        assert "أُسقط" in section
