# -*- coding: utf-8 -*-
"""DelegateRunner (T-041, R-501): وضع delegate خلف عقد Runner.

يلف DelegateBridge الحالي — دورة Brief → Implement → Review تبقى كما
هي؛ الـ runner يضيف طبقة العقد فقط:

    started → [فحص إلغاء] → موافقة عبر البوابة إن وُجدت أفعال →
    [فحص إلغاء] → run_delegation (أحداثه تُبث كأحداث حرة) →
    ترجمة الحالة النهائية → finished (+ ticket.finish عند الحسم) → RunResult

دلالة waiting_approval (القرار التصميمي المركزي — مثبّت في
tests/integration/test_ticket_cancellation.py): وصول المراجعة لحكم
APPROVE يسلّم القرار للمستخدم — الـ runner يُغلق أحداثه (finished)
ويرجع completed لكن **لا يُنهي التذكرة**؛ إنهاؤها مسؤولية
land()/reject() حصريًا (كلاهما يُنهيها completed — المستخدم حسم).
هكذا سياسة الـ run الواحد تظل صادقة: لا run جديد قبل حسم التفويض.

بقية الحالات حاسمة والجسر يُنهي التذكرة بنفسه في finally
(rejected/landed → completed، cancelled → cancelled، failed → failed)؛
نداء الإنهاء الثاني هنا لا-عملية آمنة.

أحداث الجسر (delegate_started/delegate_phase/delegate_review/…)
تُبث كأحداث حرة بنفس أسمائها — المحوّل في server.py يعيد بثها
كإطارات WS مطابقة حرفيًا للمسار القديم ``{"type": et, **ed}``.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable

from core.approval import ApprovalRequest
from core.runner import (
    EVENT_ACTION_APPLIED,
    EVENT_APPROVAL_REQUEST,
    EVENT_APPROVAL_VERDICT,
    RESULT_CANCELLED,
    RESULT_COMPLETED,
    RESULT_FAILED,
    EventSink,
    EventStream,
    RunRequest,
    RunResult,
)

if TYPE_CHECKING:
    from chain.delegate import DelegateBridge, DelegateRun
    from core.execution import RunTicket

#: حالة التسليم للمستخدم — التذكرة تبقى حية حتى land/reject.
_WAITING_APPROVAL = "waiting_approval"

#: ترجمة حالة DelegateRun الحاسمة → status العقد (نفس _map الجسر).
_STATUS_MAP = {
    "rejected": RESULT_COMPLETED,   # قرار مسجَّل — الدورة اكتملت
    "landed": RESULT_COMPLETED,
    "cancelled": RESULT_CANCELLED,
    "failed": RESULT_FAILED,
}


class DelegateRunner:
    """يشغّل DelegateBridge خلف العقد — يجتاز RunnerContractMixin كاملة."""

    def __init__(self, bridge: "DelegateBridge",
                 cancel_after_start: "Callable[[], None] | None" = None):
        self._bridge = bridge
        self.cancel_after_start = cancel_after_start

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        stream = EventStream(ticket.run_id, events)
        stream.started(mode=request.mode)
        frames: list[dict] = []
        frames_lock = threading.Lock()

        def _on_event(event_type: str, event_data: dict) -> None:
            """أحداث الجسر تُبث كأحداث حرة بنفس أسمائها (وتُجمع للترجمة)."""
            with frames_lock:
                frames.append({"type": event_type, **event_data})
            try:
                stream.emit(str(event_type), **event_data)
            except RuntimeError:
                pass  # حدث متأخر بعد النهاية — يُهمل

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

            # ── العمل: دورة التفويض الكاملة (الجسر يدير التذكرة) ──
            run = self._bridge.run_delegation(
                user_request=request.message,
                files_context=request.context.get("files") or {},
                project_context=request.context.get("project_context", ""),
                on_event=_on_event,
                ticket=ticket,
            )

            text = (run.result.response if run.result is not None else "")

            if run.status == _WAITING_APPROVAL:
                # تسليم للمستخدم: الأحداث تُغلق، التذكرة تبقى حية —
                # land()/reject() (عبر إطارات WS) يُنهيانها لاحقًا.
                stream.finished(reason=RESULT_COMPLETED,
                                handoff=_WAITING_APPROVAL)
                return RunResult(status=RESULT_COMPLETED, text=text)

            status = _STATUS_MAP.get(run.status, RESULT_FAILED)
            error = ""
            if status == RESULT_FAILED:
                with frames_lock:
                    errs = [str(f.get("error", "")) for f in frames
                            if f.get("type") == "delegate_error"]
                error = "; ".join(e for e in errs if e) or "delegation failed"
            return self._finish(stream, ticket,
                                RunResult(status=status, text=text,
                                          error=error))

        except Exception as exc:  # لا استثناءات للخارج (بند 4)
            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_FAILED, error=str(exc)))

    @staticmethod
    def _finish(stream: EventStream, ticket: "RunTicket",
                result: RunResult) -> RunResult:
        """التذكرة تُنهى بنفس status النتيجة، والحدث الأخير finished.

        الجسر يُنهي التذكرة في finally للحالات الحاسمة — النداء هنا
        لا-عملية آمنة لأن النتيجة مشتقة من حالته نفسها.
        """
        stream.finished(reason=result.status)
        ticket.finish(result.status)
        return result
