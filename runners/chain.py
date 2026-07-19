# -*- coding: utf-8 -*-
"""ChainRunner (T-040, R-501): وضع chain خلف عقد Runner.

يلف ChainBridge الحالي — كل منطق السلاسل (orchestrator/executor/
gated-apply) يبقى كما هو؛ الـ runner يضيف طبقة العقد فقط:

    started → [فحص إلغاء] → موافقة عبر البوابة إن وُجدت أفعال →
    [فحص إلغاء] → start_chain + join → ترجمة الحالة النهائية →
    finished + ticket.finish(status) → RunResult

إطارات الجسر (chain_started/chain_step/…) تُبث كأحداث حرة بنفس
أسمائها — المحوّل في server.py يعيد بثها كإطارات WS مطابقة حرفيًا
للمسار القديم (بند المطابقة في T-040).

التذكرة تُمرَّر للجسر نفسه (كما في المسار القديم) — الجسر يُنهيها
في finally بحالة الـ run الفعلية؛ نداء الإنهاء الثاني هنا لا-عملية
آمنة (الحالات النهائية غير قابلة للطفر في ExecutionRegistry).

الوصول لخيط الجسر عبر ``_active_thread`` — نفس النمط المعتمد في
tests/integration/test_chain_gated_apply.py حتى يوفّر T-041 واجهة
انتظار عامة عند حذف المسار القديم.
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
    from chain.bridge import ChainBridge
    from core.execution import RunTicket

_CHAIN_COMPLETED = "completed"   # حالة ChainRun النهائية الناجحة


class ChainRunner:
    """يشغّل ChainBridge خلف العقد — يجتاز RunnerContractMixin كاملة."""

    def __init__(self, bridge: "ChainBridge",
                 force_strategy: str | None = None,
                 join_timeout_s: float = 600.0,
                 cancel_after_start: "Callable[[], None] | None" = None):
        self._bridge = bridge
        self._force_strategy = force_strategy
        self._join_timeout_s = join_timeout_s
        self.cancel_after_start = cancel_after_start

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        stream = EventStream(ticket.run_id, events)
        stream.started(mode=request.mode)
        frames: list[dict] = []
        frames_lock = threading.Lock()

        def _frame_sink(frame: dict) -> None:
            """يجمع إطارات الجسر ويبثها كأحداث حرة بنفس أسمائها."""
            with frames_lock:
                frames.append(frame)
            ftype = str(frame.get("type", "chain_frame"))
            data = {k: v for k, v in frame.items() if k != "type"}
            try:
                stream.emit(ftype, **data)
            except RuntimeError:
                pass  # إطار متأخر بعد النهاية (join timeout) — يُهمل

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

            # ── العمل: السلسلة عبر الجسر ──
            force = request.metadata.get("force_strategy",
                                         self._force_strategy)
            run_id = self._bridge.start_chain(
                ws_send_fn=_frame_sink,
                user_request=request.message,
                file_content=request.context.get("file_content"),
                files=request.context.get("files"),
                force_strategy=force,
                ticket=ticket,
            )
            if not run_id:
                # run آخر نشط — الجسر أرسل chain_error بالفعل
                return self._finish(
                    stream, ticket,
                    RunResult(status=RESULT_FAILED,
                              error="chain لم يبدأ — run آخر نشط"))

            thread = self._bridge._active_thread
            if thread is not None:
                thread.join(timeout=self._join_timeout_s)
                if thread.is_alive():
                    return self._finish(
                        stream, ticket,
                        RunResult(status=RESULT_FAILED,
                                  error="chain timeout — الخيط لم ينتهِ"))

            with frames_lock:
                snapshot = list(frames)
            return self._finish(stream, ticket,
                                self._result_from_frames(snapshot))

        except Exception as exc:  # لا استثناءات للخارج (بند 4)
            return self._finish(
                stream, ticket,
                RunResult(status=RESULT_FAILED, error=str(exc)))

    # ── ترجمة إطارات الجسر → RunResult ──────────────────────

    @staticmethod
    def _result_from_frames(frames: list[dict]) -> RunResult:
        """الحالة النهائية من إطارات الجسر — نفس دلالات المسار القديم."""
        finished = next((f for f in frames
                         if f.get("type") == "chain_finished"), None)
        cancelled = any(f.get("type") == "chain_cancelled" for f in frames)
        errors = [str(f.get("error", "")) for f in frames
                  if f.get("type") == "chain_step"
                  and f.get("status") == "error"]
        errors += [str(f.get("error", "")) for f in frames
                   if f.get("type") == "chain_error"]
        error_text = "; ".join(e for e in errors if e)

        if cancelled:
            return RunResult(status=RESULT_CANCELLED)
        if finished is not None and finished.get("status") == _CHAIN_COMPLETED:
            return RunResult(status=RESULT_COMPLETED,
                             text=str(finished.get("result") or ""))
        return RunResult(status=RESULT_FAILED,
                         error=error_text or "chain failed")

    @staticmethod
    def _finish(stream: EventStream, ticket: "RunTicket",
                result: RunResult) -> RunResult:
        """التذكرة تُنهى بنفس status النتيجة، والحدث الأخير finished.

        لو الجسر أنهى التذكرة بالفعل (finally الخاص به) فالنداء هنا
        لا-عملية — الحالتان متطابقتان لأن النتيجة مشتقة من إطاراته.
        """
        stream.finished(reason=result.status)
        ticket.finish(result.status)
        return result
