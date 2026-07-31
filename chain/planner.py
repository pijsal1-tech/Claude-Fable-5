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

#: أسماء المخطِّطات المعروفة (T-107 أضاف llm/hybrid كما خُطط).
KNOWN_PLANNERS: tuple[str, ...] = ("heuristic", "llm", "hybrid")

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
    # TSK-730b: معرّف التشغيلة — يصل للإضافات عبر PluginContext.
    # "" (الافتراضي) = السلوك التاريخي حرفيًّا (goldens تثبته).
    run_id: str = ""


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
            run_id=request.run_id,           # TSK-730b
        )


# ═══════════════════════════════════════════════════════
#   T-107 (R-803): LLMPlanner — خطة من الموديل خلف حراسة صلبة
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class PlannerDecisionRecord:
    """سجل قرار تخطيط واحد (نمط R-402 RoutingRecord) — الإجابة الكاملة
    على «لماذا هذه الخطة؟»: أي مخطِّط اختير، هل سقط ولماذا.

    يعيش في ``plan.metadata["planner_record"]`` (dict عبر to_dict) —
    خارج عقود السلك القديمة (corpus T-034 لا يلمس metadata الجديدة).
    """
    planner: str                    # llm / hybrid
    used: str                       # llm / heuristic — من أنتج الخطة فعلًا
    fallback_reason: str | None     # None = خطة LLM قُبلت
    strategy: str                   # strategy_name النهائية
    steps_count: int
    capacity_available: int | None  # total_available وقت القرار (None = بلا فحص)

    def to_dict(self) -> dict:
        return {
            "planner": self.planner,
            "used": self.used,
            "fallback_reason": self.fallback_reason,
            "strategy": self.strategy,
            "steps_count": self.steps_count,
            "capacity_available": self.capacity_available,
        }


#: برومبت طلب الخطة — عقد الإخراج JSON فقط (يطابق chain/plan_schema.py).
PLAN_PROMPT_TEMPLATE = """أنت مخطِّط مهام برمجية. حلّل الطلب وأنتج خطة تنفيذ.

أخرج JSON فقط (بلا أي نص خارجه) بهذا الشكل حرفيًّا:
{{"strategy": "<direct|context_window|chunk_chain|map_reduce|pipeline>",
 "steps": [{{"id": "s1", "name": "...", "stage": "<analyze|plan|execute|review>",
            "agent_role": "...", "prompt": "...", "depends_on": []}}]}}

القواعد: خطوات ≤ {max_steps}؛ depends_on تشير لخطوات سابقة فقط؛
الطلبات البسيطة = خطوة execute واحدة.

الطلب:
{user_request}
"""


class LLMPlanner:
    """T-107: الموديل يقترح الخطة — الحراسة تقرر قبولها.

    المسار: برومبت → ``provider.send`` → ``parse_plan_json`` →
    ``validate_plan_payload`` → فحص السعة (خطوات الخطة مقابل
    ``capacity.total_available``) → ExecutionPlan. **أي عائق** في أي
    مرحلة ⇒ خطة ``HeuristicPlanner`` (بند القبول: خطة LLM فاسدة لا
    تصل التنفيذ أبدًا) وسجل قرار يسمّي السبب — انظر مصفوفة السقوط في
    رأس ``chain/plan_schema.py``.

    ``force_strategy``: تجاوز يدوي = قرار مستخدم — لا يُستشار الموديل
    أصلًا (heuristic مباشرة بسجل ``forced_heuristic``): يوفّر نداءً
    ويحفظ دلالة الفرض المثبتة في corpus T-034 حرفيًّا.
    """

    name = "llm"

    def __init__(self, provider: Any,
                 orchestrator: SmartOrchestrator | None = None) -> None:
        """provider: كائن بـ ``send(prompt) -> str`` (عقد BaseProvider).
        orchestrator: يُمرَّر لمخطِّط السقوط — نفس دلالة T-106."""
        self._provider = provider
        self._fallback = HeuristicPlanner(orchestrator)

    # ── مراحل الحراسة (كل مرحلة ترفع PlanSchemaError بسبب مسمّى) ──

    def _propose(self, request: PlanRequest) -> str:
        from .plan_schema import MAX_PLAN_STEPS, PlanSchemaError
        prompt = PLAN_PROMPT_TEMPLATE.format(
            max_steps=MAX_PLAN_STEPS, user_request=request.user_request)
        try:
            return str(self._provider.send(prompt))
        except Exception as exc:  # لا استثناء مزود يهرب للطلب أبدًا
            raise PlanSchemaError(
                f"provider_error: {type(exc).__name__}: {exc}") from exc

    @staticmethod
    def _capacity_check(steps_count: int, capacity: Any) -> int | None:
        """خطة تحتاج أكثر من السعة المتاحة تُرفض **قبل** التنفيذ.

        capacity: ``CapacityReport`` (T-038) أو None = لا فحص (مسموح —
        الفحص فرصة إضافية لا شرط تشغيل).
        """
        from .plan_schema import PlanSchemaError
        if capacity is None:
            return None
        available = int(capacity.total_available)
        if steps_count > available:
            raise PlanSchemaError(
                f"capacity: needs {steps_count} > {available}")
        return available

    def plan(self, request: PlanRequest,
             context: Any = None,
             capacity: Any = None) -> ExecutionPlan:
        from .plan_schema import (PlanSchemaError, parse_plan_json,
                                  validate_plan_payload)

        if request.force_strategy:
            plan = self._fallback.plan(request, context, capacity)
            plan.metadata["planner_record"] = PlannerDecisionRecord(
                planner=self.name, used="heuristic",
                fallback_reason="forced_heuristic",
                strategy=plan.strategy_name,
                steps_count=len(plan.steps),
                capacity_available=None).to_dict()
            return plan

        try:
            raw = self._propose(request)
            validated = validate_plan_payload(parse_plan_json(raw))
            available = self._capacity_check(len(validated.steps), capacity)
            plan = validated.to_strategy_result()
            plan.metadata["planner_record"] = PlannerDecisionRecord(
                planner=self.name, used="llm", fallback_reason=None,
                strategy=plan.strategy_name,
                steps_count=len(plan.steps),
                capacity_available=available).to_dict()
            return plan
        except PlanSchemaError as exc:
            plan = self._fallback.plan(request, context, capacity)
            plan.metadata["planner_record"] = PlannerDecisionRecord(
                planner=self.name, used="heuristic",
                fallback_reason=exc.reason,
                strategy=plan.strategy_name,
                steps_count=len(plan.steps),
                capacity_available=None).to_dict()
            return plan


class HybridPlanner:
    """T-107: بوابة استدلالية → صقل LLM (heuristic gate → LLM refine).

    التوصية الاستدلالية أولًا (صفر كلفة): إن كانت بسيطة
    (direct/context_window) تُعتمد خطتها كما هي — لا نداء موديل
    لطلب لا يحتاجه؛ المعقدة (chunk_chain/map_reduce/pipeline) تمر
    لـ LLMPlanner بكل حراسته (فساد خطته ⇒ سقوط heuristic بسجل).
    ``force_strategy`` يمر للـ LLM planner الذي يحوّله heuristic
    بسجل ``forced_heuristic`` (مسار الفرض واحد لا مساران).
    """

    name = "hybrid"

    #: الاستراتيجيات «البسيطة» — توصيتها تُعتمد بلا موديل.
    SIMPLE_STRATEGIES: frozenset[str] = frozenset(
        {"direct", "context_window"})

    def __init__(self, provider: Any,
                 orchestrator: SmartOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or SmartOrchestrator()
        self._heuristic = HeuristicPlanner(self._orchestrator)
        self._llm = LLMPlanner(provider, self._orchestrator)

    def plan(self, request: PlanRequest,
             context: Any = None,
             capacity: Any = None) -> ExecutionPlan:
        if request.force_strategy:
            plan = self._llm.plan(request, context, capacity)
            plan.metadata["planner_record"]["planner"] = self.name
            return plan

        recommended = self._orchestrator.analyze_complexity(
            user_request=request.user_request,
            files=request.files,
            file_content=request.file_content,
            file_path=request.file_path,
        ).recommended.value

        if recommended in self.SIMPLE_STRATEGIES:
            plan = self._heuristic.plan(request, context, capacity)
            plan.metadata["planner_record"] = PlannerDecisionRecord(
                planner=self.name, used="heuristic",
                fallback_reason=f"simple_tier: {recommended}",
                strategy=plan.strategy_name,
                steps_count=len(plan.steps),
                capacity_available=None).to_dict()
            return plan

        plan = self._llm.plan(request, context, capacity)
        plan.metadata["planner_record"]["planner"] = self.name
        return plan


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
                        provider: Any = None) -> Planner:
    """بناء المخطِّط من قيمة ``planner:`` — درزة الإقلاع الوحيدة.

    orchestrator: يُمرَّر للمخطِّط (سجل الإضافات المُحمَّل عند
    الإقلاع يعيش فيه) — None = افتراضي بلا إضافات.
    provider: مطلوب لـ llm/hybrid (عقد ``send``) — طلبهما بدونه =
    ValueError صاخب (ضبط ناقص لا يُسكت عنه)؛ heuristic يتجاهله.
    """
    name = resolve_planner_name(value)
    if name == "heuristic":
        return HeuristicPlanner(orchestrator)
    if provider is None:
        raise ValueError(
            f"planner: {name!r} يحتاج provider — الضبط ناقص")
    if name == "llm":
        return LLMPlanner(provider, orchestrator)
    assert name == "hybrid"
    return HybridPlanner(provider, orchestrator)
