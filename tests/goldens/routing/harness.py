# -*- coding: utf-8 -*-
"""T-034 (R-401): harness تسجيل قرارات التوجيه الحقيقية — corpus الـ 30.

«الـ instrumentation» هنا بالكامل داخل tests/ (نمط T-017/T-020) —
**صفر تعديل على كود الإنتاج**، فبند «إزالة الـ instrumentation» محقق
بالبناء: لا شيء يُزال لأن لا شيء أُضيف للراوتر/الأوركستريتور نفسيهما.

كل سيناريو ينفَّذ على الكود الحقيقي (`RequestRouter.route` /
`SmartOrchestrator.select_strategy` / `build_delegate`) بمدخلات حتمية
(محتوى ملفات مولّد، ميزانيات ثابتة) ويُسجَّل ناتجه حرفيًّا — هذا هو
الـ golden الذي يجب أن يعيد T-035 إنتاجه بايت-بايت بعد توحيد المفردات.

⚠️ ملاحظتان صادقتان عن السلوك الحالي (تُلتقطان عمدًا — R-401 يصلحهما):
- ``select_strategy(force_strategy="delegate")`` يسقط في else →
  fallback إلى direct **بصمت** (المفردة السادسة غير موصولة هناك؛
  builder الـ delegate يُستدعى فقط عبر DelegateBridge).
- ``route(force_strategy="<غير معروف>")`` يمرّر النص الغريب كما هو في
  ``RoutingDecision.strategy`` (misroute صامت).

تغطية المفردات (مصفوفة التغطية في الاختبار):
- راوتر (4): direct / auto_chain / full_chain / delegate — طبيعية
  ومفروضة ومع downgrade.
- أوركستريتور (6): direct / context_window / chunk_chain / map_reduce /
  pipeline عبر select_strategy + delegate عبر build_delegate المباشر.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.orchestrator import SmartOrchestrator          # noqa: E402
from chain.router import RequestRouter                    # noqa: E402
from chain.strategies import build_delegate               # noqa: E402
from providers.budget import BudgetSnapshot               # noqa: E402


# ═══════════════ مدخلات حتمية ═══════════════

def _lines(n: int, stem: str = "line") -> str:
    """محتوى ملف حتمي بعدد أسطر محدد."""
    return "\n".join(f"{stem} {i}: pass" for i in range(n))


class _FixedBudget:
    """ميزانية ثابتة — check() تعيد BudgetSnapshot حتمية."""

    def __init__(self, per_provider: dict[str, int]):
        total = sum(per_provider.values())
        best = max(per_provider, key=lambda k: per_provider[k]) \
            if per_provider else ""
        self._snap = BudgetSnapshot(
            total_available=total,
            per_provider=dict(per_provider),
            best_provider=best,
            cheapest_provider=best,
        )

    def check(self) -> BudgetSnapshot:
        return self._snap


PLENTY = {"use_ai": 10, "genspark": 6}       # كل الاستراتيجيات متاحة
THREE = {"use_ai": 3}                        # يكفي full_chain لا delegate
TWO = {"use_ai": 2}                          # يكفي auto_chain فقط
ONE = {"use_ai": 1}                          # direct فقط

_COMPLEX_REQ = ("refactor the whole architecture and rewrite then "
                "migrate every module across files")
_RISKY_COMPLEX_REQ = (_COMPLEX_REQ +
                      " with auth password token database migration")
_LONG_REQ = "أضف توثيقًا شاملًا لكل الدوال " * 10   # >200 حرف، بلا أنماط

_FILES_4_SMALL = {f"src/mod_{i}.py": _lines(100) for i in range(4)}
_FILES_2_MEDIUM = {"src/a.py": _lines(1200), "src/b.py": _lines(1300)}


# ═══════════════ السيناريوهات — 30 قرارًا ═══════════════
# layer: "router" → RequestRouter.route (المفردات الأربع)
#        "orchestrator" → SmartOrchestrator.select_strategy (خمس مفردات)
#        "builder_delegate" → build_delegate المباشر (المفردة السادسة)

SCENARIOS: dict[str, dict[str, Any]] = {
    # ── router: القرارات الطبيعية (بالتعقيد) ──
    "router_chat_mode_always_direct": dict(
        layer="router", budget=PLENTY, mode="chat",
        request="اشرح لي الفرق بين list و tuple",
    ),
    "router_low_score_direct": dict(
        layer="router", budget=PLENTY, mode="build",
        request="أضف تعليقًا هنا",
    ),
    "router_mid_score_auto_chain": dict(
        layer="router", budget=PLENTY, mode="build",
        request=_LONG_REQ, file_content=_lines(500),
    ),
    "router_high_score_full_chain": dict(
        layer="router", budget=PLENTY, mode="build",
        request="refactor this module carefully",
        file_content=_lines(2000),
    ),
    "router_very_high_score_delegate": dict(
        layer="router", budget=PLENTY, mode="build",
        request=_COMPLEX_REQ, file_content=_lines(4500),
    ),
    # ── router: downgrades بالميزانية ──
    "router_delegate_downgrades_to_full_chain": dict(
        layer="router", budget=THREE, mode="build",
        request=_COMPLEX_REQ, file_content=_lines(4500),
    ),
    "router_full_chain_downgrades_to_auto_chain": dict(
        layer="router", budget=TWO, mode="build",
        request="refactor this module carefully",
        file_content=_lines(2000),
    ),
    "router_auto_chain_downgrades_to_direct_flagged": dict(
        layer="router", budget=ONE, mode="build",
        request=_LONG_REQ, file_content=_lines(500),
    ),
    "router_borderline_auto_chain_below_full_threshold": dict(
        # حدّي: ملف 3900 سطر (score حجم = 4.0) بطلب خفيف بلا أنماط —
        # المجموع 4.0 يبقى داخل نطاق auto_chain (≤5.0) رغم ضخامة الملف.
        # ملاحظة توثيقية: مسار «upgrade recommended=direct → context_window»
        # داخل فرع full_chain **غير قابل للوصول** رياضيًّا (نفس الـ score
        # يقرر النطاقين)، لذا لا سيناريو له — chain_strategy يتبع
        # recommended_strategy دائمًا.
        layer="router", budget=PLENTY, mode="build",
        request="tidy this large file", file_content=_lines(3900),
    ),
    "router_delegate_pins_pipeline_chain_strategy": dict(
        layer="router", budget=PLENTY, mode="build",
        request=_RISKY_COMPLEX_REQ, file_content=_lines(4500),
    ),
    # ── router: القرارات المفروضة ──
    "router_forced_direct": dict(
        layer="router", budget=PLENTY, mode="build",
        request=_COMPLEX_REQ, force="direct",
    ),
    "router_forced_auto_chain_affordable": dict(
        layer="router", budget=PLENTY, mode="build",
        request="أضف تعليقًا", force="auto_chain",
    ),
    "router_forced_full_chain_affordable": dict(
        layer="router", budget=PLENTY, mode="build",
        request="أضف تعليقًا", force="full_chain",
    ),
    "router_forced_delegate_affordable": dict(
        layer="router", budget=PLENTY, mode="build",
        request="أضف تعليقًا", force="delegate",
    ),
    "router_forced_delegate_unaffordable_downgrades": dict(
        layer="router", budget=TWO, mode="build",
        request="أضف تعليقًا", force="delegate",
    ),
    "router_forced_unknown_string_passes_through": dict(
        # misroute صامت موثَّق: strategy="banana" تخرج كما هي
        layer="router", budget=PLENTY, mode="build",
        request="أضف تعليقًا", force="banana",
    ),
    # ── orchestrator: القرارات الطبيعية (بالتعقيد) ──
    "orch_trivial_direct_no_context": dict(
        layer="orchestrator", request="أضف تعليقًا",
    ),
    "orch_direct_wraps_file_content": dict(
        layer="orchestrator", request="أضف تعليقًا",
        file_content=_lines(50), file_path="src/tiny.py",
    ),
    "orch_direct_wraps_files_dict": dict(
        layer="orchestrator", request="أضف تعليقًا",
        files={"src/one.py": _lines(30)},
    ),
    "orch_context_window_single_file": dict(
        layer="orchestrator", request=_LONG_REQ,
        file_content=_lines(500), file_path="src/mid.py",
    ),
    "orch_context_window_folds_files": dict(
        layer="orchestrator", request="حسّن الأداء هنا",
        files={"src/a.py": _lines(400), "src/b.py": _lines(50),
               "src/c.py": _lines(50)},
    ),
    "orch_chunk_chain_large_single_file": dict(
        layer="orchestrator", request="tidy this large file",
        file_content=_lines(4500), file_path="src/huge.py",
    ),
    "orch_map_reduce_many_small_files": dict(
        layer="orchestrator", request="راجع الملفات",
        files=_FILES_4_SMALL,
    ),
    "orch_map_reduce_two_medium_files": dict(
        layer="orchestrator", request="حسّن البنية",
        files=_FILES_2_MEDIUM,
    ),
    "orch_pipeline_no_review": dict(
        layer="orchestrator", request=_COMPLEX_REQ,
        file_content=_lines(4500), file_path="src/big.py",
    ),
    "orch_pipeline_with_review_on_risk": dict(
        layer="orchestrator", request=_RISKY_COMPLEX_REQ,
        file_content=_lines(4500), file_path="src/auth.py",
    ),
    # ── orchestrator: القرارات المفروضة ──
    "orch_forced_context_window": dict(
        layer="orchestrator", request="أضف تعليقًا",
        file_content=_lines(50), file_path="src/tiny.py",
        force="context_window",
    ),
    "orch_forced_map_reduce": dict(
        layer="orchestrator", request="أضف تعليقًا",
        files={"src/one.py": _lines(30)}, force="map_reduce",
    ),
    "orch_forced_delegate_falls_back_to_direct": dict(
        # misroute صامت موثَّق: المفردة السادسة غير موصولة في
        # select_strategy — تسقط في else → build_direct
        layer="orchestrator", request="نفّذ عبر delegate",
        file_content=_lines(50), file_path="src/tiny.py",
        force="delegate",
    ),
    # ── builder: مفردة delegate السادسة (مسار DelegateBridge) ──
    "builder_delegate_brief_implement_review_land": dict(
        layer="builder_delegate", request="أنشئ API كامل مع auth",
        context="مشروع Flask قائم",
        files={"src/app.py": _lines(80)},
    ),
}


# ═══════════════ التنفيذ والتسجيل ═══════════════

def run_scenario(spec: dict[str, Any]) -> dict[str, Any]:
    """تنفيذ سيناريو واحد على الكود الحقيقي وإرجاع القرار المسجل."""
    layer = spec["layer"]
    orchestrator = SmartOrchestrator()

    if layer == "router":
        router = RequestRouter(
            orchestrator=orchestrator,
            budget=_FixedBudget(spec["budget"]),
            active_provider_name="use_ai",
        )
        decision = router.route(
            user_request=spec["request"],
            file_content=spec.get("file_content"),
            files=spec.get("files"),
            mode=spec.get("mode", "chat"),
            force_strategy=spec.get("force"),
        )
        return {"layer": layer, "decision": decision.to_dict()}

    if layer == "orchestrator":
        result = orchestrator.select_strategy(
            user_request=spec["request"],
            files=spec.get("files"),
            file_content=spec.get("file_content"),
            file_path=spec.get("file_path", ""),
            force_strategy=spec.get("force"),
        )
        return {
            "layer": layer,
            "decision": {
                "strategy_name": result.strategy_name,
                "step_ids": [s.id for s in result.steps],
                "step_stages": [s.stage for s in result.steps],
                "complexity": result.metadata["complexity"],
            },
        }

    if layer == "builder_delegate":
        result = build_delegate(
            spec["request"], spec.get("context", ""), spec.get("files"),
        )
        return {
            "layer": layer,
            "decision": {
                "strategy_name": result.strategy_name,
                "step_ids": [s.id for s in result.steps],
                "step_stages": [s.stage for s in result.steps],
            },
        }

    raise ValueError(f"طبقة غير معروفة: {layer!r}")


def capture_corpus() -> dict[str, Any]:
    """تشغيل كل السيناريوهات وإرجاع الـ corpus الكامل."""
    entries = {}
    for name, spec in SCENARIOS.items():
        entries[name] = run_scenario(spec)
    return {
        "format": 1,
        "task": "T-034 (R-401) — golden corpus of 30 real routing decisions",
        "count": len(entries),
        "entries": entries,
    }
