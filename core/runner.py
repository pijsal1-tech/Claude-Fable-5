# -*- coding: utf-8 -*-
"""Runner Protocol (T-039, R-501): واجهة واحدة لكل أوضاع التنفيذ.

لماذا
-----
direct / ChainBridge / AgentLoop / DelegateBridge — أربع نقاط دخول
بأربعة توقيعات وأربعة أشكال نتائج وأربع معالجات إلغاء/موافقة مختلفة.
هذا الموديول يعرّف **العقد المشترك** الذي ستُهاجَر إليه الأوضاع واحدًا
تلو الآخر (T-040..T-042): المرسِل يصبح
``runner.run(request, ticket, events) -> RunResult`` مهما كان الوضع.

T-039 يشحن العقد + عدة الاختبار المرجعية فقط — **لا توصيل بعد**
(server.py لا يتغير؛ الـ runners الحقيقية تأتي خلف علم LEGACY_DISPATCH
في T-040).

دليل تأليف Runner (runner-authoring guide)
------------------------------------------
عقد أي Runner — تفرضه عدة العقود المشتركة
(``tests/contracts/runner_contract.py`` — ورِثها وعرّف ``make_runner``):

1. **الأحداث جيدة التشكيل**: استخدم :class:`EventStream` (يختم run_id
   وseq المتصاعد تلقائيًا). أول حدث ``run_started`` وآخر حدث
   ``run_finished`` وبينهما ما تشاء؛ ممنوع أي حدث بعد ``run_finished``
   (الـ stream يرمي RuntimeError — لا أحداث شبحية بعد النهاية).

2. **الإلغاء تعاوني ويُحترم**: افحص ``ticket.is_cancelled`` عند كل
   checkpoint (قبل كل خطوة مكلفة على الأقل). لو رُفع العلم: أنهِ
   مبكرًا بـ ``finish_reason="cancelled"`` وأعد
   ``RunResult(status="cancelled")``.

3. **الموافقة عبر البوابة حصريًا**: أي فعل مقترح على workspace
   (``request.proposed_actions``) يمر عبر ``ApprovalGate.request``
   قبل تطبيقه — والقرار يُبث حدثَي ``approval_request`` ثم
   ``approval_verdict``. **لا بوابة موصولة ⇒ رفض آمن** (نمط T-012/T-013
   نفسه: لا تنفيذ صامتًا أبدًا).

4. **لا استثناءات للخارج**: التقط أعطالك وأعد
   ``RunResult(status="failed", error=...)`` — المرسِل لا يجب أن يحتاج
   try/except خاصًا بكل وضع.

5. **أنهِ التذكرة قبل العودة**: ``ticket.finish(result.status)`` —
   حالة التذكرة النهائية تطابق ``RunResult.status`` دائمًا
   (السجل لا يكذب عن الحيوية — عقد T-014).

المرجع التنفيذي: ``tests/fakes/echo_runner.py`` — أصغر Runner يجتاز
العدة كاملة؛ انسخ هيكله عند تأليف runner جديد.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.approval import ApprovalGate, ProposedAction
    from core.execution import RunTicket


# ═══════════════════════════════════════════════════════
#   أنواع الأحداث القانونية
# ═══════════════════════════════════════════════════════

EVENT_RUN_STARTED = "run_started"
EVENT_RUN_OUTPUT = "run_output"
EVENT_APPROVAL_REQUEST = "approval_request"
EVENT_APPROVAL_VERDICT = "approval_verdict"
EVENT_ACTION_APPLIED = "action_applied"
EVENT_RUN_FINISHED = "run_finished"

# الحالات النهائية — تطابق core.execution.TERMINAL_STATES عمدًا
RESULT_COMPLETED = "completed"
RESULT_FAILED = "failed"
RESULT_CANCELLED = "cancelled"


# ═══════════════════════════════════════════════════════
#   RunRequest / RunEvent / RunResult
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class RunRequest:
    """طلب تنفيذ واحد — يحمل كل ما يحتاجه أي Runner (لا globals).

    ``approval_gate`` جزء من الطلب لا الـ Runner: نفس الـ Runner يخدم
    طلبات بسياسات موافقة مختلفة (نمط البوابة الواحدة من T-012/T-013).
    """
    mode: str                                   # "direct" | "chain" | "agent" | "delegate" | ...
    message: str
    system_prompt: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    proposed_actions: "tuple[ProposedAction, ...]" = ()
    approval_gate: "ApprovalGate | None" = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunEvent:
    """حدث واحد في مجرى التشغيلة — مختوم بهوية التشغيلة وترتيبه."""
    type: str
    run_id: str
    seq: int
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type, "run_id": self.run_id,
                "seq": self.seq, "data": dict(self.data)}


@dataclass(frozen=True)
class RunResult:
    """نتيجة موحّدة لكل الأوضاع — status يطابق حالات التذكرة النهائية."""
    status: str                                 # completed | failed | cancelled
    text: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        if self.status not in (RESULT_COMPLETED, RESULT_FAILED,
                               RESULT_CANCELLED):
            raise ValueError(
                f"status غير معروف: {self.status!r} — المسموح: "
                f"{(RESULT_COMPLETED, RESULT_FAILED, RESULT_CANCELLED)}")

    def to_dict(self) -> dict:
        return {"status": self.status, "text": self.text,
                "error": self.error}


# ═══════════════════════════════════════════════════════
#   EventSink + EventStream
# ═══════════════════════════════════════════════════════

@runtime_checkable
class EventSink(Protocol):
    """مستقبِل الأحداث — لاحقًا: مرسل WS frames؛ في الاختبارات: مجمّع."""

    def emit(self, event: RunEvent) -> None: ...


class EventStream:
    """غلاف يضمن جودة تشكيل الأحداث — يستخدمه كل Runner.

    - يختم كل حدث بـ run_id التذكرة و seq متصاعد يبدأ من 0.
    - يفرض البروتوكول: ``started()`` أولًا (مرة واحدة)، ثم أحداث حرة،
      ثم ``finished(reason)`` (مرة واحدة) — أي emit بعد النهاية أو قبل
      البداية = RuntimeError (عقد، لا سلوك صامت).
    """

    def __init__(self, run_id: str, sink: EventSink) -> None:
        self._run_id = run_id
        self._sink = sink
        self._seq = 0
        self._started = False
        self._finished = False

    def started(self, **data: Any) -> None:
        if self._started:
            raise RuntimeError("run_started أُرسل بالفعل")
        self._started = True
        self._emit(EVENT_RUN_STARTED, data)

    def emit(self, event_type: str, **data: Any) -> None:
        if not self._started:
            raise RuntimeError("emit قبل run_started — ابدأ بـ started()")
        if self._finished:
            raise RuntimeError("emit بعد run_finished — لا أحداث شبحية")
        if event_type in (EVENT_RUN_STARTED, EVENT_RUN_FINISHED):
            raise RuntimeError(
                f"{event_type} يُرسل عبر started()/finished() حصريًا")
        self._emit(event_type, data)

    def finished(self, reason: str, **data: Any) -> None:
        if not self._started:
            raise RuntimeError("finished قبل run_started")
        if self._finished:
            raise RuntimeError("run_finished أُرسل بالفعل")
        self._finished = True
        self._emit(EVENT_RUN_FINISHED, {"reason": reason, **data})

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        self._sink.emit(RunEvent(type=event_type, run_id=self._run_id,
                                 seq=self._seq, data=data))
        self._seq += 1


# ═══════════════════════════════════════════════════════
#   Runner Protocol
# ═══════════════════════════════════════════════════════

@runtime_checkable
class Runner(Protocol):
    """العقد الموحّد — كل أوضاع التنفيذ تصبح تطبيقات له (R-501).

    الالتزامات الكاملة في دليل التأليف أعلى الموديول؛ تفرضها
    ``RunnerContractMixin`` في tests/contracts/runner_contract.py.
    """

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult: ...
