# -*- coding: utf-8 -*-
"""T-039 (R-501): RunnerContractMixin — عدة العقود المشتركة لكل Runner.

الاستخدام (نفس نمط ProviderContractMixin من T-010):

    class TestMyRunnerContract(RunnerContractMixin):
        def make_runner(self, *, fail_with=None, cancel_after_start=None):
            return MyRunner(...)   # مهيأ ليحاكي الفشل/الإلغاء عند الطلب

الـ mixin يشغّل الـ runner الحقيقي عبر ExecutionRegistry حقيقي ويفحص:
1. الأحداث جيدة التشكيل: run_started أولًا، run_finished أخيرًا،
   seq متصاعد من 0 بلا فجوات، run_id موحّد، لا أحداث بعد النهاية.
2. النجاح: RunResult(completed) + التذكرة completed.
3. الفشل: الاستثناء لا يهرب — RunResult(failed) + التذكرة failed.
4. الإلغاء يُحترم: علم يُرفع بعد البداية ⇒ cancelled مبكرًا.
5. الموافقة عبر البوابة: interactive-approve يطبّق، deny لا يطبّق،
   ولا بوابة ⇒ رفض آمن (لا تنفيذ صامتًا).
6. حالة التذكرة النهائية == RunResult.status في كل السيناريوهات.
"""
from __future__ import annotations

import threading
from typing import Any

import pytest

from core.approval import ApprovalGate, ProposedAction
from core.execution import ExecutionRegistry
from core.runner import (
    EVENT_ACTION_APPLIED,
    EVENT_APPROVAL_REQUEST,
    EVENT_APPROVAL_VERDICT,
    EVENT_RUN_FINISHED,
    EVENT_RUN_STARTED,
    RESULT_CANCELLED,
    RESULT_COMPLETED,
    RESULT_FAILED,
    RunEvent,
    Runner,
    RunRequest,
    RunResult,
)


class CollectingSink:
    """EventSink اختباري — يجمع الأحداث بالترتيب."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def emit(self, event: RunEvent) -> None:
        self.events.append(event)

    @property
    def types(self) -> list[str]:
        return [e.type for e in self.events]


class RunnerContractMixin:
    """ورِثها وعرّف make_runner — تحصل على عدة العقود كاملة."""

    def make_runner(self, *, fail_with: Exception | None = None,
                    cancel_after_start: Any = None) -> Runner:
        raise NotImplementedError("عرّف make_runner في صنف الاختبار الوارث")

    # ── أدوات ──────────────────────────────────────────────

    def _execute(self, runner: Runner,
                 request: RunRequest | None = None,
                 cancel_midway: bool = False):
        """تشغيلة كاملة عبر registry حقيقي — ترجع (result, ticket, sink)."""
        registry = ExecutionRegistry()
        ticket = registry.register("agent", project_id="contract-proj")
        sink = CollectingSink()
        req = request or RunRequest(mode="echo", message="hello contract")
        if cancel_midway:
            # الإلغاء يُحقن عبر hook الـ runner إن دعمه (EchoRunner نمطًا)
            pass
        result = runner.run(req, ticket, sink)
        return result, ticket, sink

    # ── 1. الأحداث جيدة التشكيل ─────────────────────────────

    def test_events_well_formed(self):
        result, ticket, sink = self._execute(self.make_runner())
        types = sink.types
        assert types, "لا أحداث — الـ runner صامت"
        assert types[0] == EVENT_RUN_STARTED, "أول حدث يجب أن يكون run_started"
        assert types[-1] == EVENT_RUN_FINISHED, "آخر حدث يجب أن يكون run_finished"
        assert types.count(EVENT_RUN_STARTED) == 1
        assert types.count(EVENT_RUN_FINISHED) == 1
        # seq متصاعد من 0 بلا فجوات + run_id موحّد
        assert [e.seq for e in sink.events] == list(range(len(sink.events)))
        assert {e.run_id for e in sink.events} == {ticket.run_id}
        # حدث النهاية يحمل reason == status النتيجة
        assert sink.events[-1].data["reason"] == result.status

    # ── 2. النجاح ───────────────────────────────────────────

    def test_success_completes_result_and_ticket(self):
        result, ticket, sink = self._execute(self.make_runner())
        assert isinstance(result, RunResult)
        assert result.status == RESULT_COMPLETED
        assert result.error == ""
        assert ticket.state == RESULT_COMPLETED
        assert ticket.is_terminal

    # ── 3. الفشل لا يهرب ────────────────────────────────────

    def test_failure_returns_failed_result_not_exception(self):
        runner = self.make_runner(fail_with=RuntimeError("planted crash"))
        result, ticket, sink = self._execute(runner)  # يجب ألا يرمي
        assert result.status == RESULT_FAILED
        assert "planted crash" in result.error
        assert ticket.state == RESULT_FAILED
        # حتى في الفشل: الأحداث مغلقة بشكل جيد
        assert sink.types[-1] == EVENT_RUN_FINISHED
        assert sink.events[-1].data["reason"] == RESULT_FAILED

    # ── 4. الإلغاء يُحترم ───────────────────────────────────

    def test_cancellation_honored(self):
        registry = ExecutionRegistry()
        ticket = registry.register("agent", project_id="contract-proj")
        sink = CollectingSink()
        # العلم يُرفع بعد run_started — عبر hook حتمي
        runner = self.make_runner(
            cancel_after_start=lambda: ticket.cancel("contract test"))
        result = runner.run(
            RunRequest(mode="echo", message="to be cancelled"), ticket, sink)
        assert result.status == RESULT_CANCELLED
        assert ticket.state == RESULT_CANCELLED
        assert sink.types[-1] == EVENT_RUN_FINISHED
        assert sink.events[-1].data["reason"] == RESULT_CANCELLED

    # ── 5. الموافقة عبر البوابة ─────────────────────────────

    def _action(self) -> ProposedAction:
        return ProposedAction(kind="write", target="a.txt",
                              payload="x", summary="اكتب a.txt")

    def test_approval_gated_approved_applies(self):
        gate = ApprovalGate(mode="auto", auto_whitelist={"write"})
        req = RunRequest(mode="echo", message="apply it",
                         proposed_actions=(self._action(),),
                         approval_gate=gate)
        result, ticket, sink = self._execute(self.make_runner(), request=req)
        assert result.status == RESULT_COMPLETED
        assert EVENT_APPROVAL_REQUEST in sink.types
        assert EVENT_APPROVAL_VERDICT in sink.types
        assert EVENT_ACTION_APPLIED in sink.types
        # الطلب قبل القرار قبل التطبيق — بالترتيب
        assert (sink.types.index(EVENT_APPROVAL_REQUEST)
                < sink.types.index(EVENT_APPROVAL_VERDICT)
                < sink.types.index(EVENT_ACTION_APPLIED))
        # القرار مسجَّل في audit البوابة (نقطة القرار الوحيدة)
        assert gate.audit_entries()[-1]["approved"] is True

    def test_approval_denied_does_not_apply(self):
        gate = ApprovalGate(mode="deny")
        req = RunRequest(mode="echo", message="deny it",
                         proposed_actions=(self._action(),),
                         approval_gate=gate)
        result, ticket, sink = self._execute(self.make_runner(), request=req)
        assert result.status == RESULT_FAILED
        assert EVENT_ACTION_APPLIED not in sink.types  # صفر تطبيق
        assert ticket.state == RESULT_FAILED

    def test_no_gate_wired_safe_reject(self):
        """أفعال مقترحة بلا بوابة ⇒ رفض آمن — لا تنفيذ صامتًا (T-012/T-013)."""
        req = RunRequest(mode="echo", message="orphan actions",
                         proposed_actions=(self._action(),),
                         approval_gate=None)
        result, ticket, sink = self._execute(self.make_runner(), request=req)
        assert result.status == RESULT_FAILED
        assert EVENT_ACTION_APPLIED not in sink.types

    # ── 6. التذكرة تطابق النتيجة دائمًا ─────────────────────

    @pytest.mark.parametrize("scenario", ["success", "failure"])
    def test_ticket_state_always_matches_result(self, scenario):
        runner = (self.make_runner() if scenario == "success"
                  else self.make_runner(fail_with=ValueError("boom")))
        result, ticket, _ = self._execute(runner)
        assert ticket.state == result.status
