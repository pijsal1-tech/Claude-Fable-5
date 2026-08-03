# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  DelegateQueue — طوابير تفويض متعددة المهام
  TSK-CEV-112 (ينفّذ FI-13، بموجب D-16 البند 5)

  ترقية REFERENCE→ACTIVE لانضباط
  newskells/skills/*-delegate/references/multi-task-queues.md:
  «Run sequentially, one commit per task» — تتابع صارم لا fan-out؛
  المهمة التالية لا تُرسل إلا بعد هبوط (land) السابقة؛ القيود
  المقررة أثناء التنفيذ تُرحَّل نصيًا لبريفات المهام اللاحقة
  (البريف self-contained — المنفّذ بلا ذاكرة بين المهام).

  حدود واعية (من مواصفة TSK-CEV-112):
  - صفر تعديل على DelegateBridge — كل ضمانات T-009/T-015 تُورَث كما هي.
  - بوابة الموافقة تبقى سيدة: waiting_approval يوقف الطابور حتى يحسم
    المستخدم عبر land_current()/reject_current().
  - رفض/فشل/إلغاء أي مهمة = إيقاف الطابور (halted) — انضباط
    «stop and ask» (multi-task-queues.md §When to stop and ask).
  - التوازي مرفوض بنص المرجع (يضحّي بخاصية الشجرة النظيفة لكل مهمة).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from chain.delegate import DelegateBridge, DelegateRun
from core.structured_log import swallowed as _slog_swallowed

# ── حالات المهمة/الطابور ──
TASK_QUEUED = "queued"
TASK_RUNNING = "running"
TASK_WAITING_APPROVAL = "waiting_approval"
TASK_LANDED = "landed"
TASK_REJECTED = "rejected"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"

QUEUE_IDLE = "idle"
QUEUE_RUNNING = "running"
QUEUE_WAITING_APPROVAL = "waiting_approval"
QUEUE_HALTED = "halted"
QUEUE_COMPLETED = "completed"

# عنوان كتلة الترحيل المحقونة في project_context للمهام اللاحقة —
# مثبَّت هنا وتستشهد به الاختبارات (تغييره = كسر واعٍ للتثبيت).
CARRY_HEADER = "[قيود مقررة من مهام سابقة]"


@dataclass
class QueuedTask:
    """مهمة واحدة في الطابور."""
    task_id: str
    description: str
    files_context: dict[str, str] = field(default_factory=dict)
    status: str = TASK_QUEUED
    run: DelegateRun | None = None
    # حقائق ما بعد الهبوط تُستخرج لترحيلها للمهام اللاحقة
    carried_facts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "files": list(self.files_context.keys()),
            "status": self.status,
            "run": self.run.to_dict() if self.run else None,
            "carried_facts": list(self.carried_facts),
        }


class DelegateQueue:
    """يدير سلسلة مهام تفويض فوق DelegateBridge القائم — تتابعيًا حصرًا.

    Events (تمر عبر on_event بنمط DelegateBridge._emit نفسه):
    - queue_started: بدأ الطابور
    - queue_task_started: مهمة أُرسلت للجسر
    - queue_task_waiting_approval: مهمة بانتظار حسم المستخدم
    - queue_task_landed: مهمة هبطت (بعد land_current)
    - queue_halted: الطابور توقف (رفض/فشل/إلغاء) — لا تقدّم صامت
    - queue_completed: كل المهام هبطت
    """

    def __init__(self, bridge: DelegateBridge):
        self._bridge = bridge
        self._tasks: list[QueuedTask] = []
        self._status = QUEUE_IDLE
        self._current_index: int = -1
        self._project_context_base: str = ""
        self._on_event: Callable | None = None
        self._halt_reason: str = ""

    # ── تكوين الطابور ──

    def add_task(self, description: str,
                 files_context: dict[str, str] | None = None) -> QueuedTask:
        """إضافة مهمة — قبل start() فقط (الطابور ثابت أثناء التشغيل:
        تعديل خطة جارية = قرار إنساني لا إلحاق صامت)."""
        if self._status not in (QUEUE_IDLE,):
            raise RuntimeError(
                f"لا إضافة بعد البدء (الحالة: {self._status}) — "
                "طابور جديد لخطة جديدة")
        task = QueuedTask(
            task_id=str(uuid.uuid4())[:8],
            description=description,
            files_context=dict(files_context or {}),
        )
        self._tasks.append(task)
        return task

    # ── خصائص القراءة ──

    @property
    def status(self) -> str:
        return self._status

    @property
    def tasks(self) -> list[QueuedTask]:
        return list(self._tasks)

    @property
    def current_task(self) -> QueuedTask | None:
        if 0 <= self._current_index < len(self._tasks):
            return self._tasks[self._current_index]
        return None

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def to_dict(self) -> dict:
        return {
            "status": self._status,
            "current_index": self._current_index,
            "halt_reason": self._halt_reason,
            "tasks": [t.to_dict() for t in self._tasks],
        }

    # ── التشغيل ──

    def start(self, project_context: str = "",
              on_event: Callable | None = None) -> None:
        """يبدأ الطابور: يشغّل المهمة الأولى ويقف عند أول
        waiting_approval (بوابة الموافقة سيدة — لا تقدّم بلا حسم)."""
        if self._status != QUEUE_IDLE:
            raise RuntimeError(f"الطابور بدأ فعلًا (الحالة: {self._status})")
        if not self._tasks:
            raise RuntimeError("طابور فارغ — add_task() أولًا")
        self._project_context_base = project_context
        self._on_event = on_event
        self._status = QUEUE_RUNNING
        self._emit("queue_started", {
            "tasks_count": len(self._tasks),
            "task_ids": [t.task_id for t in self._tasks],
        })
        self._dispatch_next()

    def land_current(self) -> bool:
        """المستخدم اعتمد المهمة الحالية: land عبر الجسر ثم استخراج
        حقائق الترحيل ثم إرسال المهمة التالية (أو إتمام الطابور)."""
        task = self.current_task
        if (self._status != QUEUE_WAITING_APPROVAL or task is None
                or task.status != TASK_WAITING_APPROVAL):
            return False
        if not self._bridge.land(on_event=self._on_event):
            return False
        task.status = TASK_LANDED
        task.carried_facts = self._extract_facts(task)
        self._emit("queue_task_landed", {
            "task_id": task.task_id,
            "carried_facts": list(task.carried_facts),
        })
        self._status = QUEUE_RUNNING
        self._dispatch_next()
        return True

    def reject_current(self, reason: str = "") -> bool:
        """المستخدم رفض المهمة الحالية ⇒ إيقاف الطابور كاملًا —
        المهام اللاحقة تفترض هبوط السابقة (multi-task-queues.md:12-13)؛
        المتابعة حول افتراض مكسور ممنوعة."""
        task = self.current_task
        if (self._status != QUEUE_WAITING_APPROVAL or task is None
                or task.status != TASK_WAITING_APPROVAL):
            return False
        if not self._bridge.reject(reason=reason, on_event=self._on_event):
            return False
        task.status = TASK_REJECTED
        self._halt(f"رفض المستخدم للمهمة {task.task_id}"
                   + (f": {reason}" if reason else ""))
        return True

    # ── الداخليات ──

    def _dispatch_next(self) -> None:
        """يرسل المهمة التالية للجسر — أو يُتم الطابور إن انتهت كلها."""
        next_index = self._current_index + 1
        if next_index >= len(self._tasks):
            self._status = QUEUE_COMPLETED
            self._emit("queue_completed", {
                "tasks_count": len(self._tasks),
            })
            return
        self._current_index = next_index
        task = self._tasks[next_index]
        task.status = TASK_RUNNING
        self._emit("queue_task_started", {
            "task_id": task.task_id,
            "index": next_index,
            "description": task.description,
        })
        run = self._bridge.run_delegation(
            user_request=task.description,
            files_context=task.files_context,
            project_context=self._compose_context(),
            on_event=self._on_event,
        )
        task.run = run
        if run.status == "waiting_approval":
            task.status = TASK_WAITING_APPROVAL
            self._status = QUEUE_WAITING_APPROVAL
            self._emit("queue_task_waiting_approval", {
                "task_id": task.task_id,
                "run_id": run.run_id,
            })
            return
        # rejected / failed / cancelled — إيقاف لا تقدّم صامت
        task.status = {
            "rejected": TASK_REJECTED,
            "failed": TASK_FAILED,
            "cancelled": TASK_CANCELLED,
        }.get(run.status, TASK_FAILED)
        self._halt(f"المهمة {task.task_id} انتهت بحالة {run.status}")

    def _halt(self, reason: str) -> None:
        self._status = QUEUE_HALTED
        self._halt_reason = reason
        # المهام المتبقية تبقى queued — قرار الاستئناف إنساني
        self._emit("queue_halted", {
            "reason": reason,
            "remaining": [t.task_id for t in self._tasks
                          if t.status == TASK_QUEUED],
        })

    def _compose_context(self) -> str:
        """project_context للمهمة التالية = الأساس + كتلة القيود المقررة
        من كل المهام الهابطة (carry-forward — multi-task-queues.md:27-31:
        قيد ظهر في المهمة 2 يجب أن يُعاد نصًا في بريف المهمة 5)."""
        facts: list[str] = []
        for t in self._tasks:
            if t.status == TASK_LANDED and t.carried_facts:
                facts.extend(
                    f"- ({t.task_id}) {f}" for f in t.carried_facts)
        if not facts:
            return self._project_context_base
        block = CARRY_HEADER + "\n" + "\n".join(facts)
        if self._project_context_base:
            return f"{self._project_context_base}\n\n{block}"
        return block

    @staticmethod
    def _extract_facts(task: QueuedTask) -> list[str]:
        """حقائق التنفيذ التي تُرحَّل: الملفات الملموسة + ملخص المنفّذ +
        ملاحظات الحكم — ما قرره التنفيذ ولم تكن الخطة تعرفه."""
        facts: list[str] = []
        run = task.run
        if run is None:
            return facts
        if run.result is not None:
            if run.result.touched_files:
                facts.append(
                    "ملفات هبطت: " + ", ".join(run.result.touched_files))
            if run.result.summary:
                facts.append("ملخص التنفيذ: " + run.result.summary)
        if run.verdict is not None and run.verdict.summary:
            facts.append("خلاصة المراجعة: " + run.verdict.summary)
        return facts

    def _emit(self, event_type: str, data: dict) -> None:
        """نفس نمط DelegateBridge._emit — لا ينفجر على callback معطوب."""
        if self._on_event:
            try:
                self._on_event(event_type, dict(data, ts=time.time()))
            except Exception as _exc:
                _slog_swallowed("chain/delegate_queue.py:_emit", _exc)
