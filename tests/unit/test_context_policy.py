# -*- coding: utf-8 -*-
"""T-045 (R-602): context_policy enforced in build_prompt.

الأدلة المطلوبة (acceptance):
- three-mode goldens: مصفوفة عرض full / summary / minimal ثابتة حرفيًّا.
- ≥50%: برومبت الخطوة 5 تحت ``summary`` أصغر بـ ≥50% من الأساس غير
  المحدود على fixture الخمس خطوات (بالتوكنز — المقدّر المركزي).
- minimal completeness: كل تبعية معلنة تظهر بالاسم والحالة (لا محتوى).
- fail fast: قيمة مجهولة ⇒ ValueError وقت الخطة قبل أي استدعاء مزود.
- regression: الافتراضي القديم ``selective`` = تكافؤ بايت-ببايت مع
  السلوك القديم غير المشروط.
"""
from __future__ import annotations

import pytest

from chain.executor import ChainExecutor
from chain.models import (
    ChainRun, ChainStep, ExecutionPolicy,
    SUMMARY_TOKENS_PER_DEP, canonical_context_policy, summarize_for_context,
)
from context.budget import CharsPerTokenEstimator
from tests.fakes.fake_provider import FakeProvider

EST = CharsPerTokenEstimator()

#: ناتج خطوة كبير (~1250 توكن) — فوق ميزانية الملخص بوضوح
BIG_RESULT = "line of analysis output\n" * 200
SMALL_RESULT = "tiny result"


def _step(policy: str, deps: list[str] | None = None,
          template: str = "do the work") -> ChainStep:
    return ChainStep(id="sX", name="Step X", stage="execute",
                     agent_role="executor", prompt_template=template,
                     depends_on=deps or ["s1"], context_policy=policy)


# ═══════════════ canonical_context_policy ═══════════════

class TestCanonicalPolicy:

    @pytest.mark.parametrize("raw,expected", [
        ("full", "full"),
        ("selective", "full"),      # الافتراضي القديم — legacy alias
        ("summary", "summary"),
        ("summaries", "summary"),   # تهجئة تعليق الموديل القديمة
        ("minimal", "minimal"),
    ])
    def test_aliases(self, raw, expected):
        assert canonical_context_policy(raw) == expected

    @pytest.mark.parametrize("bad", ["", "verbose", "Full", "SUMMARY", "none"])
    def test_unknown_raises(self, bad):
        with pytest.raises(ValueError, match="Unknown context_policy"):
            canonical_context_policy(bad)


# ═══════════════ three-mode render goldens ═══════════════

class TestModeGoldens:
    """مصفوفة العرض الثلاثية — goldens حرفية على مدخلات ثابتة."""

    DEPS_RESULTS = {"s1": "alpha result", "s2": "beta result"}
    DEPS_META = {"s1": {"name": "Analyze", "status": "success"},
                 "s2": {"name": "Plan", "status": "success"}}

    def test_full_golden(self):
        step = _step("full", deps=["s1", "s2"])
        assert step.build_prompt(self.DEPS_RESULTS, self.DEPS_META) == (
            "\n\n[Result from s1]:\nalpha result"
            "\n\n[Result from s2]:\nbeta result"
            "\n\ndo the work"
        )

    def test_summary_golden_small_results_verbatim(self):
        # ضمن الميزانية ⇒ summary يمرر النص حرفيًّا (لا تشويه مجاني)
        step = _step("summary", deps=["s1", "s2"])
        assert step.build_prompt(self.DEPS_RESULTS, self.DEPS_META) == (
            "\n\n[Result from s1]:\nalpha result"
            "\n\n[Result from s2]:\nbeta result"
            "\n\ndo the work"
        )

    def test_summary_golden_big_result_truncated(self):
        step = _step("summary", deps=["s1"])
        prompt = step.build_prompt({"s1": BIG_RESULT})
        assert "[Result from s1]:" in prompt
        assert "chars omitted — summary mode" in prompt
        # الرأس والذيل كلاهما حاضران
        assert prompt.count("line of analysis output") >= 2
        assert EST.estimate(prompt) < EST.estimate(BIG_RESULT) / 2

    def test_minimal_golden(self):
        step = _step("minimal", deps=["s1", "s2"])
        assert step.build_prompt(self.DEPS_RESULTS, self.DEPS_META) == (
            "\n\n[Dependency s1: Analyze — success]"
            "\n\n[Dependency s2: Plan — success]"
            "\n\ndo the work"
        )

    def test_minimal_without_meta_falls_back_to_ids(self):
        step = _step("minimal", deps=["s1"])
        assert step.build_prompt(self.DEPS_RESULTS) == (
            "\n\n[Dependency s1: s1 — unknown]\n\ndo the work"
        )

    def test_minimal_carries_zero_result_content(self):
        """minimal completeness: كل تبعية تُذكر — ولا بايت من نتائجها."""
        step = _step("minimal", deps=["s1", "s2"])
        prompt = step.build_prompt(
            {"s1": "SECRET_PAYLOAD_1", "s2": "SECRET_PAYLOAD_2"},
            self.DEPS_META)
        for dep_id in step.depends_on:          # completeness
            assert f"[Dependency {dep_id}:" in prompt
        assert "SECRET_PAYLOAD_1" not in prompt  # zero content
        assert "SECRET_PAYLOAD_2" not in prompt

    def test_previous_context_placeholder_respected_in_all_modes(self):
        for policy in ("full", "summary", "minimal"):
            step = _step(policy, deps=["s1"],
                         template="HEAD {previous_context} TAIL")
            prompt = step.build_prompt({"s1": SMALL_RESULT}, self.DEPS_META)
            assert prompt.startswith("HEAD ") and prompt.endswith(" TAIL")


# ═══════════════ legacy parity (regression) ═══════════════

class TestLegacyParity:

    def test_selective_default_is_byte_identical_to_legacy(self):
        """الافتراضي القديم selective ⇒ نفس النص القديم غير المشروط بايت-ببايت."""
        step = ChainStep(id="s3", name="S3", stage="execute",
                         agent_role="executor", prompt_template="run it",
                         depends_on=["s1", "s2"])  # policy الافتراضي
        results = {"s1": BIG_RESULT, "s2": "beta"}

        # السلوك القديم حرفيًّا (المنطق القديم قبل T-045):
        legacy_context = ""
        for dep_id in step.depends_on:
            if dep_id in results:
                legacy_context += f"\n\n[Result from {dep_id}]:\n{results[dep_id]}"
        legacy = legacy_context + "\n\n" + step.prompt_template

        assert step.build_prompt(results) == legacy

    def test_missing_dep_result_skipped_like_legacy(self):
        step = _step("full", deps=["s1", "ghost"])
        prompt = step.build_prompt({"s1": "alpha"})
        assert "[Result from s1]:" in prompt
        assert "ghost" not in prompt


# ═══════════════ summarize_for_context ═══════════════

class TestSummarize:

    def test_within_budget_verbatim(self):
        assert summarize_for_context(SMALL_RESULT) == SMALL_RESULT

    def test_over_budget_truncates_deterministically(self):
        s1 = summarize_for_context(BIG_RESULT)
        s2 = summarize_for_context(BIG_RESULT)
        assert s1 == s2                              # حتمي (+lru cache)
        assert EST.estimate(s1) <= SUMMARY_TOKENS_PER_DEP + 32  # هامش العلامة
        assert "chars omitted" in s1

    def test_head_and_tail_preserved(self):
        text = "HEAD_MARK " + ("x" * 5000) + " TAIL_MARK"
        s = summarize_for_context(text)
        assert s.startswith("HEAD_MARK")
        assert s.endswith("TAIL_MARK")


# ═══════════════ 5-step fixture: ≥50% reduction ═══════════════

def _five_step_pipeline(policy: str) -> tuple[ChainRun, ChainStep]:
    """خط أنابيب 1→2→3→4→5 — الخطوة 5 تعتمد على كل الأسلاف (worst case)."""
    steps = [
        ChainStep(id=f"s{i}", name=f"Step {i}", stage="execute",
                  agent_role="executor", prompt_template=f"step {i} work",
                  depends_on=[f"s{j}" for j in range(1, i)],
                  context_policy=policy)
        for i in range(1, 6)
    ]
    run = ChainRun(run_id="run-fixture1", steps=steps,
                   policy=ExecutionPolicy())
    # نتائج الأسلاف 1–4: مخرجات كبيرة واقعية
    for i in range(1, 5):
        run.results[f"s{i}"] = f"== output of step {i} ==\n" + BIG_RESULT
    return run, steps[4]


class TestFiveStepReduction:

    def test_step5_summary_prompt_at_least_50pct_smaller(self):
        """القبول الحرفي: برومبت الخطوة 5 تحت summary أصغر ≥50% من الأساس."""
        run_full, step5_full = _five_step_pipeline("full")
        run_sum, step5_sum = _five_step_pipeline("summary")
        results = run_full.results

        baseline = EST.estimate(step5_full.build_prompt(results))
        summary = EST.estimate(step5_sum.build_prompt(results))

        assert summary <= baseline * 0.5, (
            f"summary prompt {summary}tok > 50% of baseline {baseline}tok")

    def test_step5_minimal_is_smallest(self):
        run, _ = _five_step_pipeline("full")
        results = run.results
        sizes = {}
        for policy in ("full", "summary", "minimal"):
            _, s5 = _five_step_pipeline(policy)
            meta = {f"s{i}": {"name": f"Step {i}", "status": "success"}
                    for i in range(1, 5)}
            sizes[policy] = EST.estimate(s5.build_prompt(results, meta))
        assert sizes["minimal"] < sizes["summary"] < sizes["full"]


# ═══════════════ executor integration ═══════════════

class TestExecutorEnforcement:

    def test_unknown_policy_fails_fast_before_any_provider_call(self):
        """تحقق وقت الخطة: قيمة مجهولة ⇒ run فشل وصفر استدعاءات مزود."""
        steps = [ChainStep(id="s1", name="S1", stage="execute",
                           agent_role="executor", prompt_template="go",
                           context_policy="bogus_mode")]
        run = ChainRun(run_id="run-badpol01", steps=steps,
                       policy=ExecutionPolicy())
        provider = FakeProvider(responses=["R1"])

        result = ChainExecutor(provider).execute(run)

        assert result.status == "failed"
        assert provider.call_count == 0

    def test_summary_policy_shrinks_provider_prompt(self):
        """المزود يستلم فعليًا برومبتًا ملخّصًا تحت summary (لا ديكور)."""
        def make_run(policy: str) -> ChainRun:
            steps = [
                ChainStep(id="s1", name="S1", stage="execute",
                          agent_role="executor", prompt_template="produce"),
                ChainStep(id="s2", name="S2", stage="execute",
                          agent_role="executor", prompt_template="consume",
                          depends_on=["s1"], context_policy=policy),
            ]
            return ChainRun(run_id=f"run-{policy}", steps=steps,
                            policy=ExecutionPolicy())

        prompts: dict[str, int] = {}
        for policy in ("full", "summary"):
            provider = FakeProvider(responses=[BIG_RESULT, "done"])
            run = make_run(policy)
            assert ChainExecutor(provider).execute(run).status == "completed"
            consume_call = provider.calls[-1]
            prompts[policy] = len(consume_call.prompt)

        assert prompts["summary"] < prompts["full"] / 2

    def test_minimal_policy_provider_sees_no_dep_content(self):
        steps = [
            ChainStep(id="s1", name="S1", stage="execute",
                      agent_role="executor", prompt_template="produce"),
            ChainStep(id="s2", name="S2", stage="execute",
                      agent_role="executor", prompt_template="consume",
                      depends_on=["s1"], context_policy="minimal"),
        ]
        run = ChainRun(run_id="run-minimal1", steps=steps,
                       policy=ExecutionPolicy())
        provider = FakeProvider(responses=["UNIQUE_DEP_OUTPUT", "done"])

        assert ChainExecutor(provider).execute(run).status == "completed"
        final_prompt = provider.calls[-1].prompt
        assert "UNIQUE_DEP_OUTPUT" not in final_prompt
        assert "[Dependency s1: S1 — success]" in final_prompt

    def test_default_policy_runs_unchanged(self):
        """regression: سلسلة بالافتراضي القديم تعمل كما كانت تمامًا."""
        steps = [
            ChainStep(id="s1", name="S1", stage="execute",
                      agent_role="executor", prompt_template="produce"),
            ChainStep(id="s2", name="S2", stage="execute",
                      agent_role="executor", prompt_template="consume",
                      depends_on=["s1"]),
        ]
        run = ChainRun(run_id="run-default1", steps=steps,
                       policy=ExecutionPolicy())
        provider = FakeProvider(responses=["FULL_DEP_BODY", "done"])

        assert ChainExecutor(provider).execute(run).status == "completed"
        assert "FULL_DEP_BODY" in provider.calls[-1].prompt
