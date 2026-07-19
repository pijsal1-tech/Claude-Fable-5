# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Chain Models — Data structures for the ChainAgent system

  M2: DAG ChainExecutor
  - ChainStep: خطوة واحدة في السلسلة
  - ChainRun: تشغيل واحد (معزول + قابل للاستكمال)
  - ExecutionPolicy: سياسة التنفيذ
  - CancellationToken: إلغاء cooperative
  - BudgetTracker: حجز ذري للميزانية
  - ProviderSnapshot / ProjectSnapshot: لقطات serializable
═══════════════════════════════════════════════════════
"""
import threading
import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════
#   CancellationToken — إلغاء cooperative
# ═══════════════════════════════════════════════════════

class CancellationToken:
    """
    يتفحص: قبل كل خطوة، بعد كل retry، عند طلب الإلغاء.

    Semantics (4 قواعد صريحة):
    1. الإلغاء يمنع بدء خطوات جديدة
    2. يلغي retries القادمة
    3. ينتظر الطلب الجاري حتى timeout
    4. يتجاهل نتيجته عند وصولها لو الـ run ألغي
    """

    def __init__(self):
        self._cancelled = threading.Event()
        self._reason: str = ""

    def cancel(self, reason: str = ""):
        """إلغاء السلسلة"""
        self._reason = reason
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def raise_if_cancelled(self):
        if self._cancelled.is_set():
            raise ChainCancelled(self._reason or "Chain cancelled")


class ChainCancelled(Exception):
    """تم إلغاء السلسلة"""
    pass


# ═══════════════════════════════════════════════════════
#   ExecutionPolicy — سياسة التنفيذ
# ═══════════════════════════════════════════════════════

@dataclass
class ExecutionPolicy:
    """
    سياسة التنفيذ — يقررها الـ Orchestrator، ينفذها الـ Executor.
    يمكن تحميلها من execution_policy.json.
    """
    # ── Session Mode ──
    session_mode: str = "isolated"    # isolated | shared | provider_default

    # ── Parallelism ──
    max_parallel_steps: int = 3

    # ── Retries ──
    max_retries: int = 2
    step_timeout_seconds: int = 180
    continue_on_optional_failure: bool = True

    # ── Budget ──
    max_provider_calls: int = 30
    max_total_input_tokens: int | None = None
    max_total_time_seconds: int = 3600
    confirm_user_above: int = 8       # اسأل المستخدم لو > N استدعاءات

    # ── Stop Condition ──
    stop_condition: str = "all_required"  # all_required | first_success | quorum

    # ── WS Disconnect ──
    cancel_on_ws_disconnect: bool = False

    def to_dict(self) -> dict:
        """تحويل للـ serialization"""
        return {
            "session_mode": self.session_mode,
            "max_parallel_steps": self.max_parallel_steps,
            "max_retries": self.max_retries,
            "step_timeout_seconds": self.step_timeout_seconds,
            "continue_on_optional_failure": self.continue_on_optional_failure,
            "max_provider_calls": self.max_provider_calls,
            "max_total_input_tokens": self.max_total_input_tokens,
            "max_total_time_seconds": self.max_total_time_seconds,
            "confirm_user_above": self.confirm_user_above,
            "stop_condition": self.stop_condition,
            "cancel_on_ws_disconnect": self.cancel_on_ws_disconnect,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionPolicy":
        """تحميل من dict/JSON"""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════
#   Snapshots — لقطات serializable
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProviderSnapshot:
    """لقطة المزود وقت إنشاء الـ run"""
    provider_name: str
    model_name: str | None
    configuration_hash: str
    capabilities_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "configuration_hash": self.configuration_hash,
            "capabilities_snapshot": self.capabilities_snapshot,
        }


@dataclass(frozen=True)
class ProjectSnapshot:
    """لقطة المشروع وقت إنشاء الـ run"""
    project_root: str
    project_id: str
    relevant_file_hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_root": self.project_root,
            "project_id": self.project_id,
            "relevant_file_hashes": dict(self.relevant_file_hashes),
        }


@dataclass(frozen=True)
class ChainExecutionResult:
    """لقطة غير قابلة للتعديل للنتائج النهائية للتشغيل"""
    run_id: str
    status: str
    results: dict[str, str]
    completed_at: float

    def get_result(self, step_id: str) -> str | None:
        return self.results.get(step_id)


# ═══════════════════════════════════════════════════════
#   ChainStep — خطوة واحدة
# ═══════════════════════════════════════════════════════

@dataclass
class ChainStep:
    """
    خطوة واحدة في السلسلة.

    stage: المرحلة (analyze | plan | execute | review)
    agent_role: الدور المتخصص (code_analyzer | planner | executor ...)
    depends_on: IDs الخطوات المطلوبة (DAG — مصدر الحقيقة)
    critical: لو فشلت → وقف السلسلة
    """
    id: str
    name: str
    stage: str                       # analyze | plan | execute | review
    agent_role: str                  # code_analyzer | planner | executor...
    prompt_template: str = ""
    depends_on: list[str] = field(default_factory=list)
    context_policy: str = "selective"  # summaries | full | selective
    critical: bool = True
    result: str = ""
    status: str = "pending"          # pending | running | success | error | skipped
    error_message: str = ""
    duration_ms: int = 0
    provider_calls: int = 0          # عدد الاستدعاءات (مع retries)

    def build_prompt(self, dependency_results: dict[str, str]) -> str:
        """بناء البرومبت مع حقن نتائج الخطوات المطلوبة فقط"""
        context = ""
        for dep_id in self.depends_on:
            if dep_id in dependency_results:
                context += f"\n\n[Result from {dep_id}]:\n{dependency_results[dep_id]}"

        prompt = self.prompt_template
        if "{previous_context}" in prompt:
            prompt = prompt.replace("{previous_context}", context)
        elif context:
            prompt = context + "\n\n" + prompt

        return prompt

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "stage": self.stage,
            "agent_role": self.agent_role,
            "depends_on": list(self.depends_on),
            "context_policy": self.context_policy,
            "critical": self.critical,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "provider_calls": self.provider_calls,
        }

    @property
    def is_ready(self) -> bool:
        """هل الخطوة جاهزة للتنفيذ؟ (كل الـ dependencies ناجحة)"""
        return self.status == "pending"

    @property
    def is_terminal(self) -> bool:
        """هل الخطوة انتهت (نجاح أو فشل أو skip)؟"""
        return self.status in ("success", "error", "skipped")


# ═══════════════════════════════════════════════════════
#   BudgetTracker — حجز ذري للميزانية
# ═══════════════════════════════════════════════════════

class BudgetTracker:
    """
    يتبع ويحجز الميزانية بشكل thread-safe.

    Pattern: reserve → provider call → commit/release on failure

    يتتبع:
    - attempted_calls: كل المحاولات
    - successful_calls: المحاولات الناجحة
    - retry_calls: إعادات المحاولة
    - cached_steps: خطوات من الـ cache
    """

    def __init__(self, policy: ExecutionPolicy):
        self._lock = threading.Lock()
        self._max_calls = policy.max_provider_calls
        self._max_time = policy.max_total_time_seconds
        self._max_tokens = policy.max_total_input_tokens
        self._start_time = time.monotonic()

        # Counters
        self.attempted_calls: int = 0
        self.successful_calls: int = 0
        self.retry_calls: int = 0
        self.cached_steps: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._reserved: int = 0  # حجوزات قيد التنفيذ

    def reserve_call(self, is_retry: bool = False) -> bool:
        """
        حجز استدعاء واحد. يرجع True لو الحجز نجح.
        لازم يُتبع بـ commit() أو release().
        """
        with self._lock:
            effective_used = self.attempted_calls + self._reserved
            if effective_used >= self._max_calls:
                return False

            if self._is_time_exceeded():
                return False

            self._reserved += 1
            return True

    def commit(self, success: bool, is_retry: bool = False,
               input_tokens: int = 0, output_tokens: int = 0):
        """تأكيد الاستدعاء بعد انتهائه"""
        with self._lock:
            self._reserved = max(0, self._reserved - 1)
            self.attempted_calls += 1
            if success:
                self.successful_calls += 1
            if is_retry:
                self.retry_calls += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def release(self):
        """إلغاء الحجز (الاستدعاء لم يحدث)"""
        with self._lock:
            self._reserved = max(0, self._reserved - 1)

    def record_cache_hit(self):
        """تسجيل خطوة من الـ cache"""
        with self._lock:
            self.cached_steps += 1

    @property
    def remaining_calls(self) -> int:
        with self._lock:
            return max(0, self._max_calls - self.attempted_calls - self._reserved)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def is_budget_exhausted(self) -> bool:
        with self._lock:
            return (self.attempted_calls >= self._max_calls
                    or self._is_time_exceeded())

    def _is_time_exceeded(self) -> bool:
        return (time.monotonic() - self._start_time) > self._max_time

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "attempted_calls": self.attempted_calls,
                "successful_calls": self.successful_calls,
                "retry_calls": self.retry_calls,
                "cached_steps": self.cached_steps,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "remaining_calls": max(0, self._max_calls - self.attempted_calls - self._reserved),
                "elapsed_seconds": round(time.monotonic() - self._start_time, 1),
            }


# ═══════════════════════════════════════════════════════
#   ChainRun — تشغيل واحد
# ═══════════════════════════════════════════════════════

@dataclass
class ChainRun:
    """
    تشغيل واحد — معزول وقابل للاستكمال.

    الـ run بيأخذ snapshot من الـ provider والمشروع وقت الإنشاء
    وبيتابع الميزانية والأحداث.
    """
    run_id: str
    steps: list[ChainStep]
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    status: str = "pending"          # pending | running | completed | failed | cancelled

    # ── Snapshots ──
    provider_snapshot: ProviderSnapshot | None = None
    project_snapshot: ProjectSnapshot | None = None

    # ── Results (step_id → result text) ──
    results: dict[str, str] = field(default_factory=dict)

    # ── Timing ──
    started_at: float = 0
    completed_at: float = 0

    # ── Runtime (not serialized) ──
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    # T-010: كان BudgetTracker | None فسبّب 7 أخطاء union-attr في executor.
    # لا أحد يمرر budget عند الإنشاء — يُبنى دائمًا في __post_init__ من الـ policy.
    budget: BudgetTracker = field(init=False, repr=False)
    _state_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self):
        self.budget = BudgetTracker(self.policy)

    def transition_to(self, new_state: str):
        """Thread-safe state transition with validation"""
        valid_transitions = {
            "pending": {"running", "failed", "cancelled"},
            "running": {"completed", "failed", "cancelled"},
            "completed": set(),
            "failed": set(),
            "cancelled": set()
        }
        with self._state_lock:
            current = self.status
            if new_state not in valid_transitions.get(current, set()):
                if current == new_state:
                    return
                raise ValueError(f"Invalid state transition from {current} to {new_state}")
            self.status = new_state

    def get_step(self, step_id: str) -> ChainStep | None:
        """يرجع خطوة بالـ ID"""
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def get_ready_steps(self) -> list[ChainStep]:
        """
        يرجع الخطوات الجاهزة للتنفيذ:
        - status == "pending"
        - كل depends_on ناجحة
        """
        ready = []
        for step in self.steps:
            if step.status != "pending":
                continue
            deps_met = all(
                (dep := self.get_step(dep_id)) is not None
                and dep.status == "success"
                for dep_id in step.depends_on
            )
            if deps_met:
                ready.append(step)
        return ready

    def is_complete(self) -> bool:
        """هل كل الخطوات انتهت؟"""
        return all(s.is_terminal for s in self.steps)

    def has_critical_failure(self) -> bool:
        """هل فيه خطوة critical فشلت؟"""
        return any(s.status == "error" and s.critical for s in self.steps)

    def get_frozen_result(self) -> ChainExecutionResult:
        """إرجاع نسخة غير قابلة للتعديل من نتائج التشغيل"""
        with self._state_lock:
            return ChainExecutionResult(
                run_id=self.run_id,
                status=self.status,
                results=dict(self.results),
                completed_at=self.completed_at
            )

    def to_state_dict(self) -> dict:
        """State snapshot للـ state.json (ذري)"""
        return {
            "run_id": self.run_id,
            "status": self.status,
            # T-044 (R-601): prompt_template يُحمل في الـ state (ليس في
            # to_dict الموجه للواجهة) — بدونه الاستكمال ينفّذ الخطوات
            # المتبقية ببرومبتات فارغة.
            "steps": [{**s.to_dict(), "prompt_template": s.prompt_template}
                      for s in self.steps],
            "results": dict(self.results),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "provider_snapshot": self.provider_snapshot.to_dict() if self.provider_snapshot else None,
            "project_snapshot": self.project_snapshot.to_dict() if self.project_snapshot else None,
            "policy": self.policy.to_dict(),
            "budget": self.budget.to_dict() if self.budget else None,
        }
