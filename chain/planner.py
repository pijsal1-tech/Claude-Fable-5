# -*- coding: utf-8 -*-
"""T-106 (R-803): بروتوكول Planner + استخراج HeuristicPlanner.

╔═══════════════════════════════════════════════════════════════╗
║  عقد الـ Planner (Planner contract)                            ║
╠═══════════════════════════════════════════════════════════════╣
║  plan(request, context, capacity) -> ExecutionPlan             ║
║                                                                ║
║  1. request: PlanRequest مجمّدة — المخطِّط لا يعدّلها أبدًا.   ║
║  2. context / capacity: اختياريان (None مسموح دائمًا) —        ║
║     HeuristicPlanner يتجاهلهما؛ مخطِّطات T-107 (LLM/Hybrid)    ║
║     تستهلكهما عبر نفس التوقيع بلا تغيير عند المستدعين.         ║
║  3. الناتج ExecutionPlan (= StrategyResult): strategy_name +   ║
║     خطوات غير فارغة + policy + metadata["complexity"] —        ║
║     جاهز للتنفيذ عبر to_chain_run(run_id).                     ║
║  4. حتمية: نفس المدخل ⇒ نفس الخطة بايت-بايت (لا عشوائية،       ║
║     لا حالة بين النداءات).                                     ║
║  5. force_strategy يُحترم دائمًا (تجاوز يدوي = قرار مستخدم)؛   ║
║     النص المجهول يسقط لـ direct (سلوك corpus T-034 المثبَّت).  ║
╚═══════════════════════════════════════════════════════════════╝

**الاستخراج صفر-تغيير-سلوك**: HeuristicPlanner غلاف رقيق فوق
``SmartOrchestrator.select_strategy`` — لا يعيد تنفيذ أي منطق
(regex/عتبات/إضافات T-102 كلها تبقى في الأوركستريتور)، فالتطابق
البايتي pre/post مضمون **بالبناء** ومثبَّت بالـ goldens في
``tests/unit/test_planner.py``. مسار LLM/Hybrid (T-107) يضيف
أصنافًا جديدة خلف نفس البروتوكول بلا لمس هذا الملف أو المستدعين.

**درزة الاختيار من config** (T-106): مفتاح ``planner:`` الأعلى في
config.yaml — ``planner_from_config`` تتحقق بصرامة (قيمة مجهولة =
ValueError صاخب عند الإقلاع، نفس فلسفة routing_config: ضبط خاطئ
صامت أسوأ من فشل إقلاع واضح)؛ المفتاح الغائب/None = ``heuristic``
(الافتراضي التاريخي — المسار الصريح والافتراضي متكافئان، مثبَّت
بالاختبار).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .orchestrator import SmartOrchestrator
from .strategies import StrategyResult

# الناتج الموحّد للتخطيط — نفس شكل T-011 الجاهز للتنفيذ حرفيًّا
# (tier/strategy عبر strategy_name، مخطط الخطوات عبر steps،
# والسياسات عبر policy) — alias لا صنف جديد: صفر تحويل = صفر انحراف.
ExecutionPlan = StrategyResult

#: أسماء المخطِّطات المعروفة — T-107 يضيف "llm"/"hybrid" هنا فقط.
KNOWN_PLANNERS: tuple[str, ...] = ("heuristic",)

DEFAULT_PLANNER = "heuristic"


# ═══════════════════════════════════════════════════════
#   PlanRequest — مدخل التخطيط الموحّد
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class PlanRequest:
    """طلب تخطيط واحد — مجمّد: المخطِّط يقرأ ولا يكتب.

    الحقول تطابق توقيع ``select_strategy`` التاريخي واحدًا-لواحد
    كي يكون الاستخراج تمريرًا خالصًا بلا إعادة تفسير.
    """
    user_request: str
    files: dict[str, str] | None = None
    file_content: str | None = None
    file_path: str = ""
    force_strategy: str | None = None


# ═══════════════════════════════════════════════════════
#   Planner Protocol
# ═══════════════════════════════════════════════════════

@runtime_checkable
class Planner(Protocol):
    """بروتوكول المخطِّط — انظر عقد الموديول أعلاه.

    ``context``/``capacity`` بـ ``Any`` عمدًا: ContextBundle و
    CapacityReport يعيشان في حزم أخرى، وربطهما بالنوع هنا يستورد
    ما لا يحتاجه HeuristicPlanner — T-107 يضيّق النوع عند مستهلكه.
    """

    #: اسم المخطِّط — معرّف الاختيار في config وسجلات قرار T-107
    #: لاحقًا (A/B). لا يُكتب في metadata هنا: T-106 تطابق بايتي.
    name: str

    def plan(self, request: PlanRequest,
             context: Any = None,
             capacity: Any = None) -> ExecutionPlan:
        """يبني خطة تنفيذ جاهزة من الطلب — انظر العقد أعلاه."""
        ...


# ═══════════════════════════════════════════════════════
#   HeuristicPlanner — المنطق الحالي خلف البروتوكول
# ═══════════════════════════════════════════════════════

class HeuristicPlanner:
    """المخطِّط الاستدلالي — منطق ``select_strategy`` القائم حرفيًّا.

    غلاف تمرير خالص: التحليل والعتبات وترشيح إضافات T-102 كلها
    تبقى في ``SmartOrchestrator`` — هذا الصنف لا يملك منطق تخطيط
    خاصًّا به إطلاقًا (ضمانة التطابق البايتي pre/post بالبناء).
    """

    name = "heuristic"

    def __init__(self,
                 orchestrator: SmartOrchestrator | None = None) -> None:
        """orchestrator: الأوركستريتور المُهيّأ (بسجل إضافاته إن وُجد)
        — None = أوركستريتور افتراضي بلا إضافات."""
        self._orchestrator = orchestrator or SmartOrchestrator()

    def plan(self, request: PlanRequest,
             context: Any = None,
             capacity: Any = None) -> ExecutionPlan:
        """تمرير خالص لـ select_strategy — context/capacity يُتجاهلان
        (الاستدلال الحالي لا يستهلكهما؛ T-107 يفعل)."""
        return self._orchestrator.select_strategy(
            user_request=request.user_request,
            files=request.files,
            file_content=request.file_content,
            file_path=request.file_path,
            force_strategy=request.force_strategy,
        )


# ═══════════════════════════════════════════════════════
#   درزة الاختيار من config
# ═══════════════════════════════════════════════════════

def resolve_planner_name(value: Any) -> str:
    """تحقق صارم لقيمة ``planner:`` من config.yaml.

    None/غائب = الافتراضي التاريخي؛ قيمة غير نصية أو اسم مجهول =
    ValueError صاخب عند الإقلاع (لا سقوط صامت لمخطِّط آخر).
    """
    if value is None:
        return DEFAULT_PLANNER
    if not isinstance(value, str) or value not in KNOWN_PLANNERS:
        raise ValueError(
            f"planner: قيمة مجهولة {value!r} — المعروف: {KNOWN_PLANNERS}")
    return value


def planner_from_config(value: Any,
                        orchestrator: SmartOrchestrator | None = None,
                        ) -> Planner:
    """بناء المخطِّط من قيمة ``planner:`` — درزة الإقلاع الوحيدة.

    orchestrator: يُمرَّر لـ HeuristicPlanner (سجل الإضافات المُحمَّل
    عند الإقلاع يعيش فيه) — None = افتراضي بلا إضافات.
    """
    name = resolve_planner_name(value)
    # T-106: heuristic هو الوحيد — T-107 يوسّع الفصل هنا.
    assert name == "heuristic"
    return HeuristicPlanner(orchestrator)
