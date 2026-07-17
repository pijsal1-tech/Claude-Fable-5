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
from typing import Callable

from .models import (
    ChainRun, ChainStep, ExecutionPolicy, CancellationToken,
    BudgetTracker, ChainCancelled,
)

# ── Import providers (sibling package) ──
import sys
import os
_EDITOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EDITOR_DIR not in sys.path:
    sys.path.insert(0, _EDITOR_DIR)

from providers.base import (
    BaseProvider, ProviderRequest, ProviderResponse, ProviderMessage,
    ProviderError, ProviderRateLimitError, ProviderTimeoutError,
    ProviderTransientError, ProviderContextTooLargeError,
    ProviderRefusalError, EmptyProviderResponseError, MalformedProviderResponseError,
    MockProvider, history_to_messages,
)
from .agent_loader import AgentLoader, AgentPrompt


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

    def execute(self, run: ChainRun,
                on_event: Callable[[ChainEvent], None] | None = None) -> ChainRun:
        """
        ينفذ السلسلة بالكامل.

        Returns: ChainRun محدّث بالنتائج والحالات.

        Cancellation: run.cancellation_token.cancel("reason")
        """
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
        """DAG topological execution loop"""
        max_iterations = len(run.steps) * 3  # Safety: prevent infinite loops
        iteration = 0

        while not run.is_complete() and iteration < max_iterations:
            iteration += 1

            # ── Check cancellation ──
            run.cancellation_token.raise_if_cancelled()

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

            # ── Execute first ready step (sequential) ──
            step = ready[0]
            self._execute_step(run, step, on_event)

            # ── Check stop condition ──
            if run.policy.stop_condition == "all_required":
                if run.has_critical_failure():
                    # Critical step failed → skip remaining pending
                    for s in run.steps:
                        if s.status == "pending":
                            s.status = "skipped"
                            s.error_message = "Critical dependency failed"
                    break

    def _execute_step(self, run: ChainRun, step: ChainStep,
                      on_event: Callable | None):
        """Execute a single step with retries"""
        step.status = "running"
        self._emit(run, on_event, ChainEvent("step_started", step_id=step.id, data={
            "name": step.name,
            "stage": step.stage,
            "agent_role": step.agent_role,
        }))

        # ── Build prompt ──
        agent_prompt = self._agent_loader.load(step.agent_role)
        dependency_results = {
            dep_id: run.results.get(dep_id, "")
            for dep_id in step.depends_on
        }
        user_prompt = step.build_prompt(dependency_results)

        # ── Retry loop ──
        last_error = None
        max_retries = run.policy.max_retries
        start_time = time.monotonic()

        for attempt in range(1 + max_retries):
            # Check cancellation before each retry
            run.cancellation_token.raise_if_cancelled()

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

                step.status = "success"
                step.result = response.text
                step.provider_calls = attempt + 1
                step.duration_ms = int((time.monotonic() - start_time) * 1000)
                run.results[step.id] = response.text

                self._emit(run, on_event, ChainEvent("step_completed", step_id=step.id, data={
                    "duration_ms": step.duration_ms,
                    "provider_calls": step.provider_calls,
                    "result_size": len(response.text),
                }))

                # Save result to file
                self._save_result(run, step)
                self._save_state(run)
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
        step.status = "error"
        step.error_message = last_error or "Unknown error"
        step.provider_calls = min(attempt + 1, 1 + max_retries)
        step.duration_ms = int((time.monotonic() - start_time) * 1000)

        self._emit(run, on_event, ChainEvent("step_failed", step_id=step.id, data={
            "error": step.error_message,
            "attempts": step.provider_calls,
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

    def _is_safety_refusal(self, text: str, raw_response: any = None) -> bool:
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
            except Exception:
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
            except Exception:
                pass

        if self._run_dir:
            try:
                events_file = self._run_dir / "events.jsonl"
                with open(events_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            except Exception:
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
            except Exception:
                pass

    def _save_result(self, run: ChainRun, step: ChainStep):
        """Save step result to results/{step_id}.txt"""
        if not self._run_dir or not step.result:
            return

        try:
            result_file = self._run_dir / "results" / f"{step.id}.txt"
            result_file.write_text(step.result, encoding="utf-8")
        except Exception:
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
