# -*- coding: utf-8 -*-
"""AgentRunner (T-041, R-501): وضع agent خلف عقد Runner.

يلف AgentLoop الحالي — كل منطق الحلقة (أدوات/موافقات/معرفة تراكمية)
يبقى كما هو؛ الـ runner يضيف طبقة العقد فقط:

    started → [فحص إلغاء] → موافقة عبر البوابة إن وُجدت أفعال →
    [فحص إلغاء] → loop.run (إطاراته تُبث كأحداث حرة) →
    الرد النهائي يُبث كقطع run_output (حجم 80 — مطابق للمسار القديم) →
    finished + ticket.finish(status) → RunResult

حذف حلقة الاستطلاع (بند T-041): المسار القديم كان يستطلع WS داخل
ws_handler أثناء عمل الـ Agent (workaround). الآن الـ runner يعمل في
thread عامل وحلقة الـ WS تبقى حرة — agent_approval_response و
cancel_agent يصلان من المستوى الأعلى مباشرة إلى AgentLoop النشط.

دورة حياة التذكرة: AgentLoop.run(ticket=…) يُنهي التذكرة بنفسه
(completed/cancelled؛ الاستثناء ⇒ failed ثم إعادة رمي). نداء الإنهاء
الثاني هنا لا-عملية آمنة — الحالة النهائية تُشتق من التذكرة نفسها
(الإلغاء عبر loop.cancel() لا يرفع علم التذكرة، فقراءتها هي الصدق).

الحقن:
- ``loop_factory(frame_sink) → AgentLoop`` — يبني حلقة مهيأة لطلب
  واحد؛ frame_sink يستقبل إطارات WS القديمة (agent_thinking/agent_step/
  agent_done/chunk) ليعيد بثها كأحداث حرة بنفس أسمائها.
- ``on_loop``: يُستدعى بالحلقة فور بنائها — server.py ينشر بها
  _active_agent_loop حتى تصلها الموافقات والإلغاء من مستوى WS الأعلى.
- ``cancel_after_start``: hook اختباري (نفس نمط Direct/Chain).
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

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
    from chain.agent_loop import AgentLoop
    from core.execution import RunTicket

LoopFactory = Callable[[Callable[[dict], None]], "AgentLoop"]

#: نفس معرف الخطوة الثابت الذي كان المسار القديم يمرره لإطارات الموافقة.
AGENT_STEP_ID = "step-agent-execute"

#: نفس حجم تقطيع الرد النهائي في المسار القديم (chunk_size = 80).
AGENT_CHUNK_SIZE = 80


class AgentRunner:
    """يشغّل AgentLoop خلف العقد — يجتاز RunnerContractMixin كاملة."""

    def __init__(self, loop_factory: LoopFactory,
                 on_loop: "Callable[[AgentLoop], None] | None" = None,
                 chunk_size: int = AGENT_CHUNK_SIZE,
                 cancel_after_start: "Callable[[], None] | None" = None):
        self._loop_factory = loop_factory
        self._on_loop = on_loop
        self._chunk_size = chunk_size
        self.cancel_after_start = cancel_after_start

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        stream = EventStream(ticket.run_id, events)
        stream.started(mode=request.mode)
        # TSK-609 (PM-02): توقيت الحلقة كاملة end-to-end (نفس نمط chain).
        _t0 = time.monotonic()

        def _frame_sink(frame: dict) -> None:
            """إطارات AgentLoop تُبث كأحداث حرة بنفس أسمائها."""
            ftype = str(frame.get("type", "agent_frame"))
            data: dict[str, Any] = {k: v for k, v in frame.items()
                                    if k != "type"}
            try:
                stream.emit(ftype, **data)
            except RuntimeError:
                pass  # إطار متأخر بعد النهاية — يُهمل

        try:
            # hook اختباري: إلغاء حتمي بعد البداية
            if self.cancel_after_start is not None:
                self.cancel_after_start()

            # ── checkpoint إلغاء ──
            if ticket.is_cancelled:
                return self._finish(stream, ticket,
                                    RunResult(status=RESULT_CANCELLED), started_at=_t0)

            # ── الموافقة عبر البوابة حصريًا (T-012/T-013) ──
            if request.proposed_actions:
                if request.approval_gate is None:
                    stream.emit(EVENT_APPROVAL_VERDICT, approved=False,
                                reason="no_gate_wired")
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_FAILED,
                                  error="أفعال مقترحة بلا بوابة موافقة — رُفضت"), started_at=_t0)
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
                                  error=f"الموافقة رُفضت: {verdict.reason}"), started_at=_t0)
                for action in request.proposed_actions:
                    stream.emit(EVENT_ACTION_APPLIED, kind=action.kind,
                                target=action.target)

            # ── checkpoint إلغاء ثانٍ قبل العمل ──
            if ticket.is_cancelled:
                return self._finish(stream, ticket,
                                    RunResult(status=RESULT_CANCELLED), started_at=_t0)

            # ── العمل: الحلقة الكاملة (تُنهي التذكرة بنفسها) ──
            loop = self._loop_factory(_frame_sink)
            if self._on_loop is not None:
                self._on_loop(loop)

            response = loop.run(
                user_request=request.message,
                history=request.context.get("history"),
                project_context=request.context.get("project_context", ""),
                run_id=ticket.run_id,
                step_id=AGENT_STEP_ID,
                ticket=ticket,
            )

            # الرد النهائي كقطع — نفس تقطيع المسار القديم حرفيًا
            text = response or ""
            for i in range(0, len(text), self._chunk_size):
                stream.emit(EVENT_RUN_OUTPUT,
                            text=text[i:i + self._chunk_size])

            # الحالة من التذكرة نفسها: loop.cancel() لا يرفع علم التذكرة
            # لكن loop.run يُنهيها cancelled — قراءتها هي مصدر الصدق.
            status = ticket.state if ticket.is_terminal else RESULT_COMPLETED
            return self._finish(stream, ticket,
                                RunResult(status=status, text=text), started_at=_t0)

        except Exception as exc:  # لا استثناءات للخارج (بند 4)
            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_FAILED, error=str(exc)), started_at=_t0)

    @staticmethod
    def _finish(stream: EventStream, ticket: "RunTicket",
                result: RunResult,
                started_at: "float | None" = None) -> RunResult:
        """التذكرة تُنهى بنفس status النتيجة، والحدث الأخير finished.

        لو AgentLoop أنهى التذكرة بالفعل فالنداء هنا لا-عملية —
        الحالتان متطابقتان لأن النتيجة مشتقة من التذكرة نفسها.

        TSK-609 (PM-02): عند تمرير ``started_at`` يُضاف ``duration_ms``
        لبيانات الحدث — مفتاح إضافي فقط (العقود تفحص reason حصرًا).
        """
        if started_at is not None:
            stream.finished(
                reason=result.status,
                duration_ms=int((time.monotonic() - started_at) * 1000))
        else:
            stream.finished(reason=result.status)
        ticket.finish(result.status)
        return result
