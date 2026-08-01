# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ChainExecutor — Sequential DAG Executor

  M2: DAG ChainExecutor
  - Executes ChainSteps sequentially (topological order)
  - Retries with Error Taxonomy awareness
  - Cooperative cancellation
  - Events logging (events.jsonl)
  - State persistence (state.json — atomic writes)
  - Resume support with state verification
═══════════════════════════════════════════════════════
"""
import json
import time
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from .models import (
    ChainRun, ChainStep, ExecutionPolicy, CancellationToken,
    BudgetTracker, ChainCancelled,
)
from core.execution import RunTicket

# ── Import providers (sibling package) ──
import sys
import os
_EDITOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EDITOR_DIR not in sys.path:
    sys.path.insert(0, _EDITOR_DIR)

# TSK-CEV-103a (CEV-F-005): أزيلت 5 استيرادات ميتة (ProviderMessage/
# ProviderContextTooLargeError/MalformedProviderResponseError/MockProvider/
# history_to_messages) — صفر استخدام هنا وصفر مستهلك عبر هذه الوحدة.
from providers.base import (
    BaseProvider, ProviderRequest, ProviderResponse,
    ProviderError, ProviderRateLimitError, ProviderTimeoutError,
    ProviderTransientError,
    ProviderRefusalError, EmptyProviderResponseError,
)
from .agent_loader import AgentLoader, AgentPrompt
from core.structured_log import swallowed as _slog_swallowed


# ═══════════════════════════════════════════════════════
#   Event Types
# ═══════════════════════════════════════════════════════

class ChainEvent:
    """حدث في السلسلة — يُسجَّل في events.jsonl"""

    def __init__(self, event_type: str, step_id: str | None = None,
                 data: dict | None = None):
        self.timestamp = time.time()
        self.event_type = event_type
        self.step_id = step_id
        self.data = data or {}

    def to_dict(self) -> dict:
        d = {
            "ts": self.timestamp,
            "type": self.event_type,
        }
        if self.step_id:
            d["step_id"] = self.step_id
        if self.data:
            d["data"] = self.data
        return d


# ═══════════════════════════════════════════════════════
#   ChainExecutor
# ═══════════════════════════════════════════════════════

class ChainExecutor:
    """
    Sequential DAG Executor.

    يأخذ ChainRun ويتنفذه خطوة بخطوة حسب الـ depends_on (topological).

    Usage:
        executor = ChainExecutor(provider, agent_loader)
        run = ChainRun(run_id="run-001", steps=[...])
        executor.execute(run, on_event=callback)

    Events:
        on_event(event: ChainEvent) — callback لكل حدث
    """

    def __init__(self, provider: BaseProvider,
                 agent_loader: AgentLoader | None = None,
                 run_dir: str | pathlib.Path | None = None):
        """
        provider: المزود لاستدعاء AI
        agent_loader: محمّل الأدوار (اختياري)
        run_dir: مجلد لحفظ events.jsonl + state.json + results/
        """
        self._provider = provider
        self._agent_loader = agent_loader or AgentLoader()
        self._run_dir = pathlib.Path(run_dir) if run_dir else None
        self._state_lock = threading.Lock()
        self._ticket: RunTicket | None = None
        # T-046 (R-603): كل اندماج نتائج في ChainRun يمر عبر
        # _apply_step_result/_apply_step_failure تحت هذا القفل —
        # نقطة الدمج الوحيدة (لا كتابة حالة متفرقة من worker threads).
        self._merge_lock = threading.Lock()
        self._events_lock = threading.Lock()

    def _check_cancelled(self, run: ChainRun) -> None:
        """T-015 (R-105): نقطة تفتيش موحّدة — تذكرة السجل + token السلسلة.

        إلغاء التذكرة (من WS/سجل التنفيذ) يُترجم إلى token السلسلة ثم
        يُرفع ChainCancelled — نفس مسار الإلغاء القديم بالضبط، فلا تغيير
        في السلوك عند عدم تمرير تذكرة.
        """
        ticket = self._ticket
        if ticket is not None and ticket.is_cancelled:
            run.cancellation_token.cancel(
                ticket.cancel_reason or "execution ticket cancelled")
        run.cancellation_token.raise_if_cancelled()

    def execute(self, run: ChainRun,
                on_event: Callable[[ChainEvent], None] | None = None,
                ticket: RunTicket | None = None) -> ChainRun:
        """
        ينفذ السلسلة بالكامل.

        Returns: ChainRun محدّث بالنتائج والحالات.

        Cancellation: run.cancellation_token.cancel("reason") — أو إلغاء
        الـ ticket (T-015, R-105): يُفحص عند حدود الخطوات وقبل كل retry.
        """
        self._ticket = ticket

        # ── تحقق وقت الخطة (T-045, R-602): context_policy مجهولة ⇒ فشل
        # فوري قبل أي استدعاء مزود — لا اكتشاف متأخر منتصف السلسلة.
        from .models import canonical_context_policy
        try:
            for _step in run.steps:
                canonical_context_policy(_step.context_policy)
        except ValueError as e:
            run.transition_to("failed")
            self._emit(run, on_event, ChainEvent("run_error", data={
                "error": f"ValueError: {e}",
            }))
            self._save_state(run)
            return run

        run.transition_to("running")
        run.started_at = time.time()

        # ── تجهيز مجلد التشغيل ──
        if self._run_dir:
            self._run_dir.mkdir(parents=True, exist_ok=True)
            (self._run_dir / "results").mkdir(exist_ok=True)

        self._emit(run, on_event, ChainEvent("run_started", data={
            "run_id": run.run_id,
            "total_steps": len(run.steps),
            "policy": run.policy.to_dict(),
        }))

        try:
            self._execute_loop(run, on_event)
        except ChainCancelled as e:
            run.transition_to("cancelled")
            self._emit(run, on_event, ChainEvent("run_cancelled", data={
                "reason": str(e),
            }))
        except Exception as e:
            run.transition_to("failed")
            self._emit(run, on_event, ChainEvent("run_error", data={
                "error": f"{type(e).__name__}: {e}",
            }))

        if run.status == "running":
            if run.has_critical_failure():
                run.transition_to("failed")
            else:
                run.transition_to("completed")

        # ── Get final result to send to UI ──
        result_text = None
        for step in reversed(run.steps):
            if step.stage == "execute" and step.status == "success":
                result_text = run.results.get(step.id)
                break
        if not result_text:
            for step in reversed(run.steps):
                if step.status == "success":
                    result_text = run.results.get(step.id)
                    break

        run.completed_at = time.time()
        self._emit(run, on_event, ChainEvent("run_finished", data={
            "status": run.status,
            "budget": run.budget.to_dict(),
            "result": result_text,
        }))
        self._save_state(run)

        return run

    # ═══════════════════════════════════════════════════
    #   Internal: Execution Loop
    # ═══════════════════════════════════════════════════

    def _execute_loop(self, run: ChainRun,
                      on_event: Callable | None):
        """DAG topological execution loop — bounded parallel (T-046, R-603).

        ``max_parallel_steps=1`` ⇒ نفس المسار القديم حرفيًّا (خطوة
        واحدة لكل دورة). ‏>1 ⇒ دفعة من المجموعة الجاهزة (بسقف
        ``max_parallel_steps`` — capacity cap) تُنفَّذ على
        ThreadPoolExecutor؛ الدمج كله عبر ``_apply_step_result``/
        ``_apply_step_failure`` تحت قفل الدمج.
        """
        max_iterations = len(run.steps) * 3  # Safety: prevent infinite loops
        iteration = 0
        max_workers = max(1, run.policy.max_parallel_steps)

        while not run.is_complete() and iteration < max_iterations:
            iteration += 1

            # ── Check cancellation (step boundary — ticket + token) ──
            self._check_cancelled(run)

            # ── Check budget ──
            if run.budget.is_budget_exhausted:
                self._emit(run, on_event, ChainEvent("budget_exhausted", data={
                    "budget": run.budget.to_dict(),
                }))
                # Mark remaining pending steps as skipped
                for step in run.steps:
                    if step.status == "pending":
                        step.status = "skipped"
                        step.error_message = "Budget exhausted"
                break

            # ── Find ready steps ──
            ready = run.get_ready_steps()

            if not ready:
                # Check if blocked (dependencies failed)
                has_pending = any(s.status == "pending" for s in run.steps)
                if has_pending:
                    # Some steps still pending but no ready ones → blocked deps
                    self._skip_blocked_steps(run, on_event)
                break

            if max_workers == 1 or len(ready) == 1:
                # ── Legacy lane: parallel=1 → ready[0] بالضبط كما كان ──
                self._execute_step(run, ready[0], on_event)
            else:
                self._execute_batch(run, ready[:max_workers], max_workers,
                                    on_event)

            # ── Check stop condition ──
            if run.policy.stop_condition == "all_required":
                if run.has_critical_failure():
                    # Critical step failed → skip remaining pending
                    for s in run.steps:
                        if s.status == "pending":
                            s.status = "skipped"
                            s.error_message = "Critical dependency failed"
                    break

    def _execute_batch(self, run: ChainRun, batch: list[ChainStep],
                       max_workers: int, on_event: Callable | None) -> None:
        """T-046 (R-603): تنفيذ دفعة جاهزة على pool محدود.

        - نقطة تفتيش إلغاء قبل كل submit (per-task checkpoint) —
          الإلغاء منتصف الدفعة يوقف الإرسال فورًا.
        - كل worker ينفّذ ``_execute_step`` (الذي يفحص الإلغاء قبل كل
          retry) — إلغاء token يوقف الإخوة عند أقرب حد retry.
        - الـ pool يُصرَّف بالكامل (drain) قبل تمرير ChainCancelled —
          لا worker يتيم يكتب حالة بعد خروج الحلقة.
        """
        cancelled: ChainCancelled | None = None
        with ThreadPoolExecutor(max_workers=max_workers,
                                thread_name_prefix=f"step-{run.run_id}") as pool:
            futures = []
            for step in batch:
                try:
                    self._check_cancelled(run)   # pre-submit checkpoint
                except ChainCancelled as e:
                    cancelled = e
                    break
                futures.append(pool.submit(self._execute_step, run, step,
                                           on_event))
            for f in as_completed(futures):
                try:
                    f.result()
                except ChainCancelled as e:
                    cancelled = e      # نُكمل التصريف — لا رفع مبكر
        if cancelled is not None:
            raise cancelled

    def _execute_step(self, run: ChainRun, step: ChainStep,
                      on_event: Callable | None):
        """Execute a single step with retries"""
        step.status = "running"
        self._emit(run, on_event, ChainEvent("step_started", step_id=step.id, data={
            "name": step.name,
            "stage": step.stage,
            "agent_role": step.agent_role,
        }))

        # ── Build prompt (T-045, R-602: context_policy enforced) ──
        agent_prompt = self._agent_loader.load(step.agent_role)
        dependency_results = {
            dep_id: run.results.get(dep_id, "")
            for dep_id in step.depends_on
        }
        dependency_meta = {
            dep_id: {"name": dep.name, "status": dep.status}
            for dep_id in step.depends_on
            if (dep := run.get_step(dep_id)) is not None
        }
        user_prompt = step.build_prompt(dependency_results,
                                        dependency_meta=dependency_meta)

        # ── Retry loop ──
        last_error = None
        max_retries = run.policy.max_retries
        start_time = time.monotonic()

        for attempt in range(1 + max_retries):
            # Check cancellation before each retry (ticket + token)
            self._check_cancelled(run)

            # Reserve budget
            is_retry = attempt > 0
            if not run.budget.reserve_call(is_retry=is_retry):
                last_error = "Budget exhausted during retries"
                break

            try:
                response = self._call_provider(
                    user_prompt, agent_prompt,
                    timeout=run.policy.step_timeout_seconds
                )

                # ── Success ──
                run.budget.commit(success=True, is_retry=is_retry,
                                  input_tokens=response.input_tokens or 0,
                                  output_tokens=response.output_tokens or 0)

                self._apply_step_result(
                    run, step, response.text,
                    provider_calls=attempt + 1,
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                    on_event=on_event)
                return

            except ProviderError as e:
                run.budget.commit(success=False, is_retry=is_retry)
                last_error = str(e)

                self._emit(run, on_event, ChainEvent("step_retry", step_id=step.id, data={
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "retryable": e.retryable,
                    "error": str(e),
                }))

                # Non-retryable → stop immediately
                if not e.retryable:
                    break

                # Rate limit → wait
                if isinstance(e, ProviderRateLimitError) and e.retry_after_seconds:
                    time.sleep(min(e.retry_after_seconds, 10))
                elif isinstance(e, (ProviderTimeoutError, ProviderTransientError)):
                    time.sleep(min(2 ** attempt, 10))

            except Exception as e:
                run.budget.commit(success=False, is_retry=is_retry)
                last_error = f"{type(e).__name__}: {e}"
                break  # Unknown errors are not retryable

        # ── All retries failed ──
        self._apply_step_failure(
            run, step, last_error or "Unknown error",
            provider_calls=min(attempt + 1, 1 + max_retries),
            duration_ms=int((time.monotonic() - start_time) * 1000),
            on_event=on_event)

    # ═══════════════════════════════════════════════════
    #   Guarded State Merge — T-046 (R-603)
    # ═══════════════════════════════════════════════════
    # كل تحوّل حالة/نتيجة على ChainRun بعد انتهاء خطوة يمر من هنا
    # حصريًّا — تحت _merge_lock. الـ workers المتوازية لا تلمس
    # step.status/run.results مباشرة في مسار الإنهاء.

    def _apply_step_result(self, run: ChainRun, step: ChainStep,
                           result_text: str, *, provider_calls: int,
                           duration_ms: int,
                           on_event: Callable | None) -> None:
        """اندماج نجاح خطوة — نقطة الدمج الوحيدة (lock-guarded)."""
        with self._merge_lock:
            step.status = "success"
            step.result = result_text
            step.provider_calls = provider_calls
            step.duration_ms = duration_ms
            run.results[step.id] = result_text

        self._emit(run, on_event, ChainEvent("step_completed", step_id=step.id, data={
            "duration_ms": duration_ms,
            "provider_calls": provider_calls,
            "result_size": len(result_text),
        }))
        self._save_result(run, step)
        self._save_state(run)

    def _apply_step_failure(self, run: ChainRun, step: ChainStep,
                            error_message: str, *, provider_calls: int,
                            duration_ms: int,
                            on_event: Callable | None) -> None:
        """اندماج فشل خطوة — نفس نقطة الدمج المحروسة."""
        with self._merge_lock:
            step.status = "error"
            step.error_message = error_message
            step.provider_calls = provider_calls
            step.duration_ms = duration_ms

        self._emit(run, on_event, ChainEvent("step_failed", step_id=step.id, data={
            "error": error_message,
            "attempts": provider_calls,
        }))
        self._save_state(run)

    def _call_provider(self, user_prompt: str, agent_prompt: AgentPrompt,
                       timeout: int = 180) -> ProviderResponse:
        """Provider call with optional agent system prompt"""
        request = ProviderRequest(
            prompt=user_prompt,
            system_prompt=agent_prompt.content,
            timeout_seconds=timeout,
        )
        response = self._provider.generate(request)
        
        # 1. Whitespace/empty checks
        text = response.text.strip() if response.text else ""
        if not text:
            raise EmptyProviderResponseError("Provider response is empty or contains only whitespace.")
            
        # 2. Check for safety refusal
        if self._is_safety_refusal(text, response.raw_response):
            raise ProviderRefusalError(
                f"Safety refusal detected in provider response. Response: {text[:100]}"
            )
            
        # 3. Normalize whitespace, keeping tool blocks intact
        # Collapse 3+ consecutive newlines to 2 newlines
        import re
        normalized_text = re.sub(r'\n{3,}', '\n\n', text)
        response.text = normalized_text
        
        return response

    def _is_safety_refusal(self, text: str, raw_response: Any = None) -> bool:
        # Check raw_response finish_reason if available
        if raw_response:
            try:
                if isinstance(raw_response, dict):
                    choices = raw_response.get("choices", [])
                    if choices and choices[0].get("finish_reason") in ("safety", "content_filter"):
                        return True
                elif hasattr(raw_response, "choices") and raw_response.choices:
                    if getattr(raw_response.choices[0], "finish_reason", None) in ("safety", "content_filter"):
                        return True
            except Exception as _exc:
                _slog_swallowed("chain/executor.py:473", _exc)
                pass

        refusal_phrases = [
            "as an ai",
            "i cannot fulfill",
            "against my safety guidelines",
            "against my programming",
            "i am unable to assist",
            "not allowed to execute",
            "cannot write a script that",
            "cannot help with this request",
            "i'm sorry, but i cannot",
            "i cannot comply",
            "violates my safety policy",
            "violates the safety policy",
        ]
        text_lower = text.lower()
        for phrase in refusal_phrases:
            if phrase in text_lower:
                return True
        return False

    # ═══════════════════════════════════════════════════
    #   DAG: Skip Blocked Steps
    # ═══════════════════════════════════════════════════

    def _skip_blocked_steps(self, run: ChainRun, on_event: Callable | None):
        """Mark pending steps whose dependencies cannot be met"""
        changed = True
        while changed:
            changed = False
            for step in run.steps:
                if step.status != "pending":
                    continue
                for dep_id in step.depends_on:
                    dep_step = run.get_step(dep_id)
                    if dep_step and dep_step.status in ("error", "skipped"):
                        if step.critical or not run.policy.continue_on_optional_failure:
                            step.status = "skipped"
                            step.error_message = f"Dependency {dep_id} failed"
                            self._emit(run, on_event, ChainEvent(
                                "step_skipped", step_id=step.id,
                                data={"reason": step.error_message}
                            ))
                            changed = True
                            break

    # ═══════════════════════════════════════════════════
    #   Persistence
    # ═══════════════════════════════════════════════════

    def _emit(self, run: ChainRun, on_event: Callable | None, event: ChainEvent):
        """Emit event: callback + events.jsonl"""
        if on_event:
            try:
                on_event(event)
            except Exception as _exc:
                _slog_swallowed("chain/executor.py:530", _exc)
                pass

        if self._run_dir:
            try:
                # T-046: قفل الأحداث — workers متوازية تُلحق بنفس الملف
                events_file = self._run_dir / "events.jsonl"
                with self._events_lock:
                    with open(events_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(event.to_dict(),
                                           ensure_ascii=False) + "\n")
            except Exception as _exc:
                _slog_swallowed("chain/executor.py:541", _exc)
                pass

    def _save_state(self, run: ChainRun):
        """Atomic state save to state.json"""
        if not self._run_dir:
            return

        with self._state_lock:
            try:
                state = run.to_state_dict()
                tmp_file = self._run_dir / "state.json.tmp"
                final_file = self._run_dir / "state.json"

                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)

                # Atomic rename
                tmp_file.replace(final_file)
            except Exception as _exc:
                _slog_swallowed("chain/executor.py:560", _exc)
                pass

    def _save_result(self, run: ChainRun, step: ChainStep):
        """Save step result to results/{step_id}.txt"""
        if not self._run_dir or not step.result:
            return

        try:
            result_file = self._run_dir / "results" / f"{step.id}.txt"
            result_file.write_text(step.result, encoding="utf-8")
        except Exception as _exc:
            _slog_swallowed("chain/executor.py:571", _exc)
            pass

    # ═══════════════════════════════════════════════════
    #   Resume
    # ═══════════════════════════════════════════════════

    @classmethod
    def can_resume(cls, run_dir: str | pathlib.Path) -> bool:
        """Check if a run can be resumed from state.json"""
        state_file = pathlib.Path(run_dir) / "state.json"
        if not state_file.exists():
            return False
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            return state.get("status") in ("running", "failed")
        except Exception:
            return False

    @classmethod
    def load_state(cls, run_dir: str | pathlib.Path) -> dict | None:
        """Load state.json"""
        state_file = pathlib.Path(run_dir) / "state.json"
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
