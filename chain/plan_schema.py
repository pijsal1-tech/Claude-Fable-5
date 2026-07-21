# -*- coding: utf-8 -*-
"""T-107 (R-803): مخطط خطة الـ LLM + التحقق الصارم.

╔═══════════════════════════════════════════════════════════════╗
║  مخطط الخطة (plan schema) — ما يُطلب من الموديل إنتاجه         ║
╠═══════════════════════════════════════════════════════════════╣
║  {                                                             ║
║    "strategy": "direct|context_window|chunk_chain|             ║
║                 map_reduce|pipeline",                          ║
║    "steps": [                                                  ║
║      {"id": "s1", "name": "...", "stage": "analyze|plan|       ║
║        execute|review", "agent_role": "...",                   ║
║       "prompt": "...", "depends_on": ["s0", ...]}              ║
║    ]                                                           ║
║  }                                                             ║
║                                                                ║
║  قواعد التحقق (بالترتيب، أول كسر = PlanSchemaError):           ║
║  1. الحمولة dict.                                              ║
║  2. strategy نص من الخمسة أعلاه — delegate ممنوع               ║
║     (مساره DelegateBridge لا خطة LLM).                         ║
║  3. steps قائمة غير فارغة، ≤ MAX_PLAN_STEPS (سقف صاخب).        ║
║  4. لكل خطوة: id/name/stage/agent_role/prompt نصوص غير         ║
║     فارغة؛ stage من {analyze, plan, execute, review}.          ║
║  5. ids فريدة؛ depends_on يشير لخطوات **سابقة فقط**            ║
║     (لا ذاتي/أمامي ⇒ DAG بلا دورات بالبناء).                   ║
╠═══════════════════════════════════════════════════════════════╣
║  مصفوفة السقوط (fallback matrix) — يستهلكها LLMPlanner:        ║
║  ┌──────────────────────────┬─────────────────────────────┐   ║
║  │ العائق                   │ fallback_reason في السجل     │   ║
║  ├──────────────────────────┼─────────────────────────────┤   ║
║  │ force_strategy موجود     │ (لا سقوط) forced_heuristic   │   ║
║  │ استثناء المزود           │ provider_error: <النوع>      │   ║
║  │ رد ليس JSON              │ invalid_json: <تفصيل>        │   ║
║  │ JSON يكسر المخطط أعلاه   │ schema: <تفصيل>              │   ║
║  │ خطوات > السعة المتاحة    │ capacity: needs N > M        │   ║
║  └──────────────────────────┴─────────────────────────────┘   ║
║  كل الصفوف ⇒ خطة HeuristicPlanner + سجل قرار يسمّي السبب —     ║
║  خطة LLM فاسدة لا تصل التنفيذ أبدًا (قبول R-803).              ║
╚═══════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .models import ChainStep, ExecutionPolicy
from .strategies import StrategyResult

#: الاستراتيجيات المسموح للموديل اقتراحها — delegate خارجها عمدًا.
ALLOWED_STRATEGIES: frozenset[str] = frozenset(
    {"direct", "context_window", "chunk_chain", "map_reduce", "pipeline"})

#: مراحل الخطوة المعروفة (نفس مفردات ChainStep.stage).
ALLOWED_STAGES: frozenset[str] = frozenset(
    {"analyze", "plan", "execute", "review"})

#: سقف الخطوات — خطة أطول = مؤشر هلوسة، رفض صاخب لا اقتطاع صامت.
MAX_PLAN_STEPS = 12


class PlanSchemaError(ValueError):
    """كسر مخطط الخطة — reason نصي يدخل سجل القرار حرفيًّا."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ValidatedStep:
    """خطوة اجتازت التحقق — جاهزة للتحويل لـ ChainStep."""
    id: str
    name: str
    stage: str
    agent_role: str
    prompt: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidatedPlan:
    """خطة اجتازت التحقق كاملة — النقطة الوحيدة لبناء ExecutionPlan
    من مخرجات موديل (لا مسار تحويل آخر)."""
    strategy: str
    steps: tuple[ValidatedStep, ...]

    def to_strategy_result(self) -> StrategyResult:
        """تحويل لخطة تنفيذ قياسية — policy افتراضية (ضبطها من الخطة
        مجال توسعة لاحق؛ الحقن الحر من الموديل في السياسات = مخاطرة)."""
        return StrategyResult(
            strategy_name=self.strategy,
            steps=[ChainStep(
                id=s.id, name=s.name, stage=s.stage,
                agent_role=s.agent_role, prompt_template=s.prompt,
                depends_on=list(s.depends_on),
            ) for s in self.steps],
            policy=ExecutionPolicy(),
            metadata={},
        )


def parse_plan_json(text: str) -> dict:
    """استخراج JSON الخطة من رد الموديل — يتسامح مع أسوار ```json فقط.

    أي شيء آخر (نص حر، JSON مبتور، قائمة بدل dict) = PlanSchemaError
    بسبب يبدأ بـ ``invalid_json:``.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # أسوار كود: أزل السطر الأول (``` أو ```json) والسور الأخير.
        lines = stripped.splitlines()
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines[1:]).strip()
    try:
        payload = json.loads(stripped)
    except (json.JSONDecodeError, ValueError) as exc:
        raise PlanSchemaError(f"invalid_json: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanSchemaError(
            f"invalid_json: expected object, got {type(payload).__name__}")
    return payload


def _require_str(step: dict, key: str, idx: int) -> str:
    val = step.get(key)
    if not isinstance(val, str) or not val.strip():
        raise PlanSchemaError(
            f"schema: steps[{idx}].{key} يجب أن يكون نصًّا غير فارغ")
    return val


def validate_plan_payload(payload: dict) -> ValidatedPlan:
    """التحقق الصارم — انظر قواعد رأس الموديول (أول كسر = رفض)."""
    strategy = payload.get("strategy")
    if not isinstance(strategy, str) or strategy not in ALLOWED_STRATEGIES:
        raise PlanSchemaError(
            f"schema: strategy مجهولة {strategy!r} — "
            f"المسموح: {sorted(ALLOWED_STRATEGIES)}")

    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PlanSchemaError("schema: steps يجب أن تكون قائمة غير فارغة")
    if len(raw_steps) > MAX_PLAN_STEPS:
        raise PlanSchemaError(
            f"schema: {len(raw_steps)} خطوة > السقف {MAX_PLAN_STEPS}")

    seen: set[str] = set()
    steps: list[ValidatedStep] = []
    for idx, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise PlanSchemaError(f"schema: steps[{idx}] ليست object")
        sid = _require_str(raw, "id", idx)
        if sid in seen:
            raise PlanSchemaError(f"schema: id مكرر {sid!r}")
        stage = _require_str(raw, "stage", idx)
        if stage not in ALLOWED_STAGES:
            raise PlanSchemaError(
                f"schema: steps[{idx}].stage مجهولة {stage!r} — "
                f"المسموح: {sorted(ALLOWED_STAGES)}")
        deps_raw = raw.get("depends_on", [])
        if not isinstance(deps_raw, list):
            raise PlanSchemaError(
                f"schema: steps[{idx}].depends_on ليست قائمة")
        deps: list[str] = []
        for dep in deps_raw:
            # سابقة فقط: الذاتي والأمامي والمجهول كلها ترفض هنا —
            # DAG بلا دورات **بالبناء** لا بفحص لاحق.
            if not isinstance(dep, str) or dep not in seen:
                raise PlanSchemaError(
                    f"schema: steps[{idx}].depends_on تشير لخطوة "
                    f"غير سابقة {dep!r}")
            deps.append(dep)
        steps.append(ValidatedStep(
            id=sid,
            name=_require_str(raw, "name", idx),
            stage=stage,
            agent_role=_require_str(raw, "agent_role", idx),
            prompt=_require_str(raw, "prompt", idx),
            depends_on=tuple(deps),
        ))
        seen.add(sid)

    return ValidatedPlan(strategy=strategy, steps=tuple(steps))
