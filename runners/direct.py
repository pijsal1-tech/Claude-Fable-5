# -*- coding: utf-8 -*-
"""DirectRunner (T-040, R-501): وضع direct خلف عقد Runner.

يلف منطق المسار المباشر الحالي في server.py — نداء provider واحد
يُبث كقطع — وراء البروتوكول الموحّد:

    started → [فحص إلغاء] → موافقة عبر البوابة إن وُجدت أفعال →
    [فحص إلغاء] → بث القطع (فحص إلغاء بين كل قطعة) →
    finished + ticket.finish(status) → RunResult

الحقن:
- ``stream_fn(prompt, history, system_prompt) → Iterator[str]`` —
  في الإنتاج: ``_active_provider().stream``؛ في الاختبارات:
  ``FakeProvider.stream``. الفشل يُحاكى بأعطال المزود نفسه
  (fail_always) — لا hook فشل خاص.
- ``cancel_after_start``: hook اختباري يُستدعى بعد run_started —
  تستخدمه عدة العقود لرفع علم الإلغاء حتميًا.

التاريخ (history) يصل عبر ``request.context["history"]`` — الـ Runner
لا يقرأ globals (بند RunRequest في core/runner.py).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator

from core.approval import ApprovalRequest
from core.runner import (
    EVENT_ACTION_APPLIED,
    EVENT_APPROVAL_REQUEST,
    EVENT_APPROVAL_VERDICT,
    EVENT_RUN_OUTPUT,
    RESULT_CANCELLED,
    RESULT_COMPLETED,
    RESULT_FAILED,
    EventSink,
    EventStream,
    RunRequest,
    RunResult,
)

if TYPE_CHECKING:
    from core.execution import RunTicket

StreamFn = Callable[[str, "list | None", str], "Iterator[str]"]


class DirectRunner:
    """رد provider واحد يُبث كقطع — يجتاز RunnerContractMixin كاملة."""

    def __init__(self, stream_fn: StreamFn,
                 cancel_after_start: "Callable[[], None] | None" = None):
        self._stream_fn = stream_fn
        self.cancel_after_start = cancel_after_start

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        stream = EventStream(ticket.run_id, events)
        stream.started(mode=request.mode)
        collected: list[str] = []

        try:
            # hook اختباري: إلغاء حتمي بعد البداية
            if self.cancel_after_start is not None:
                self.cancel_after_start()

            # ── checkpoint إلغاء ──
            if ticket.is_cancelled:
                return self._finish(stream, ticket,
                                    RunResult(status=RESULT_CANCELLED))

            # ── الموافقة عبر البوابة حصريًا (T-012/T-013) ──
            if request.proposed_actions:
                if request.approval_gate is None:
                    stream.emit(EVENT_APPROVAL_VERDICT, approved=False,
                                reason="no_gate_wired")
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_FAILED,
                                  error="أفعال مقترحة بلا بوابة موافقة — رُفضت"))
                req = ApprovalRequest(
                    actions=list(request.proposed_actions),
                    source=request.mode, run_id=ticket.run_id)
                stream.emit(EVENT_APPROVAL_REQUEST, **req.to_dict())
                verdict = request.approval_gate.request(req)
                stream.emit(EVENT_APPROVAL_VERDICT, **verdict.to_dict())
                if not verdict.approved:
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_FAILED,
                                  error=f"الموافقة رُفضت: {verdict.reason}"))
                for action in request.proposed_actions:
                    stream.emit(EVENT_ACTION_APPLIED, kind=action.kind,
                                target=action.target)

            # ── checkpoint إلغاء ثانٍ قبل العمل ──
            if ticket.is_cancelled:
                return self._finish(stream, ticket,
                                    RunResult(status=RESULT_CANCELLED))

            # ── العمل: بث القطع (فحص إلغاء بين كل قطعة) ──
            history = request.context.get("history")
            for chunk in self._stream_fn(request.message, history,
                                         request.system_prompt):
                if ticket.is_cancelled:
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_CANCELLED,
                                  text="".join(collected)))
                collected.append(chunk)
                stream.emit(EVENT_RUN_OUTPUT, text=chunk)

            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_COMPLETED, text="".join(collected)))

        except Exception as exc:  # لا استثناءات للخارج (بند 4)
            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_FAILED, text="".join(collected),
                          error=str(exc)))

    @staticmethod
    def _finish(stream: EventStream, ticket: "RunTicket",
                result: RunResult) -> RunResult:
        """التذكرة تُنهى بنفس status النتيجة، والحدث الأخير finished."""
        stream.finished(reason=result.status)
        ticket.finish(result.status)
        return result
