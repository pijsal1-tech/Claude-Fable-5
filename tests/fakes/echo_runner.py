# -*- coding: utf-8 -*-
"""EchoRunner (T-039): الـ Runner المرجعي — أصغر تطبيق يجتاز عدة العقود.

يعيد الرسالة كصدى، ويطبّق كل بند من بنود دليل التأليف في core/runner.py
حرفيًا — انسخ هذا الهيكل عند تأليف runner حقيقي (T-040+):

    started → [فحص إلغاء] → موافقة عبر البوابة إن وُجدت أفعال →
    [فحص إلغاء] → عمل → finished + ticket.finish(status) → RunResult

أدوات اختبار إضافية (لا تخص العقد):
- fail_with: استثناء يُزرع في مرحلة العمل — يثبت أن الأعطال تتحول
  إلى RunResult(failed) لا استثناءات للخارج.
- cancel_after_start: hook يُستدعى بعد run_started — يسمح للعدة
  برفع علم الإلغاء في منتصف التشغيلة بشكل حتمي.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

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


class EchoRunner:
    """صدى مرجعي — يجتاز RunnerContractMixin كاملة."""

    def __init__(self,
                 fail_with: Exception | None = None,
                 cancel_after_start: "Callable[[], None] | None" = None):
        self.fail_with = fail_with
        self.cancel_after_start = cancel_after_start

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        stream = EventStream(ticket.run_id, events)
        stream.started(mode=request.mode)

        try:
            # hook اختباري: إلغاء حتمي بعد البداية
            if self.cancel_after_start is not None:
                self.cancel_after_start()

            # ── checkpoint إلغاء (بند 2 من الدليل) ──
            if ticket.is_cancelled:
                return self._finish(stream, ticket,
                                    RunResult(status=RESULT_CANCELLED))

            # ── الموافقة عبر البوابة حصريًا (بند 3) ──
            if request.proposed_actions:
                if request.approval_gate is None:
                    # لا بوابة ⇒ رفض آمن — لا تنفيذ صامتًا أبدًا
                    stream.emit(EVENT_APPROVAL_VERDICT, approved=False,
                                reason="no_gate_wired")
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_FAILED,
                                  error="أفعال مقترحة بلا بوابة موافقة — رُفضت"))
                req = ApprovalRequest(
                    actions=list(request.proposed_actions),
                    source="echo", run_id=ticket.run_id)
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

            # ── العمل: صدى ──
            if self.fail_with is not None:
                raise self.fail_with
            text = f"ECHO: {request.message}"
            stream.emit(EVENT_RUN_OUTPUT, text=text)
            return self._finish(stream, ticket,
                                RunResult(status=RESULT_COMPLETED, text=text))

        except Exception as exc:  # بند 4: لا استثناءات للخارج
            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_FAILED, error=str(exc)))

    @staticmethod
    def _finish(stream: EventStream, ticket: "RunTicket",
                result: RunResult) -> RunResult:
        """بند 5: التذكرة تُنهى بنفس status النتيجة، والحدث الأخير finished."""
        stream.finished(reason=result.status)
        ticket.finish(result.status)
        return result
