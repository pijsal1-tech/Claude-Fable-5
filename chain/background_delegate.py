# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  BackgroundDelegateTask — مهمة تفويض خلفية محكومة
  TSK-CEV-113 (ينفّذ FI-15، بموجب D-16 البند 7)

  ترقية REFERENCE→ACTIVE لانضباط
  newskells/skills/*-delegate/references/dispatch-and-poll.md
  §Waiting for completion: «background and poll… Trust the working
  tree and the process state over any progress display» —
  المستخدم يسلّم مهمة self-contained ويواصل عمله (hand-off)،
  والحالة تُقرأ من الكائن الحي لا من ذاكرة جلسة قد تنقطع.

  حدود واعية (من مواصفة TSK-CEV-113):
  - صفر تعديل على DelegateBridge وDelegateQueue — كل ضمانات
    T-009/T-015 تُورَث كما هي.
  - **الثابت الصلب (Non-Goal §15.1 — لا YOLO)**: كل كتابة تبقى خلف
    بوابة الموافقة. هذا الغلاف لا يملك أي مسار land تلقائي —
    waiting_approval نهائية من منظوره حتى land()/reject() صريحين.
  - مؤشر الواجهة خارج النطاق — الواجهة الخلفية فقط.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Callable

from chain.delegate import DelegateBridge, DelegateRun
from core.structured_log import swallowed as _slog_swallowed

# ── حالات المهمة الخلفية ──
BG_IDLE = "idle"
BG_RUNNING = "running"
BG_WAITING_APPROVAL = "waiting_approval"
BG_LANDED = "landed"
BG_REJECTED = "rejected"
BG_FAILED = "failed"
BG_CANCELLED = "cancelled"

#: حالات الجسر الحاسمة → حالة المهمة الخلفية
_TERMINAL_MAP = {
    "waiting_approval": BG_WAITING_APPROVAL,
    "rejected": BG_REJECTED,
    "failed": BG_FAILED,
    "cancelled": BG_CANCELLED,
    "landed": BG_LANDED,
}


class BackgroundDelegateTask:
    """تسليم-وتتبّع (hand-off-and-track) فوق DelegateBridge القائم.

    Events (تمر عبر on_event بنمط DelegateBridge._emit نفسه):
    - background_started: المهمة انطلقت في الخلفية
    - background_event: تمرير حدث جسر كما هو (event/data متداخلان)
    - background_finished: الخيط انتهى (الحالة قد تكون
      waiting_approval — القرار للمستخدم، لا land تلقائي أبدًا)

    reconnect-safe: `snapshot()` يرجع الحالة الراهنة + سجل الأحداث
    المتراكم كاملًا تحت قفل — عميل أعاد الاتصال يستعيد الصورة من
    الكائن الحي (dispatch-and-poll.md: الثقة بحالة العملية لا بآخر
    إطار عرض).
    """

    def __init__(self, bridge: DelegateBridge):
        self._bridge = bridge
        self.task_id: str = str(uuid.uuid4())[:8]
        self._status: str = BG_IDLE
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._on_event: Callable | None = None
        self._error: str = ""
        self._started_at: float | None = None
        self._finished_at: float | None = None

    # ── خصائص القراءة ──

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def is_running(self) -> bool:
        return self.status == BG_RUNNING

    @property
    def run(self) -> DelegateRun | None:
        return self._bridge.current_run

    # ── الإطلاق (hand-off) ──

    def start(self, user_request: str,
              files_context: dict[str, str] | None = None,
              project_context: str = "",
              on_event: Callable | None = None,
              ticket=None) -> None:
        """يطلق دورة التفويض في خيط daemon ويرجع فورًا.

        الدورة نفسها (Brief → Implement → Review) هي run_delegation
        القائم حرفيًا — كل نقاط تفتيش الإلغاء (T-015) تُورَث.
        """
        with self._lock:
            if self._status != BG_IDLE:
                raise RuntimeError(
                    f"المهمة انطلقت من قبل (الحالة: {self._status}) — "
                    "كائن جديد لمهمة جديدة")
            self._status = BG_RUNNING
            self._on_event = on_event
            self._started_at = time.monotonic()

        self._record_and_emit("background_started", {
            "task_id": self.task_id,
            "request": user_request,
        })

        def _work() -> None:
            try:
                run = self._bridge.run_delegation(
                    user_request=user_request,
                    files_context=dict(files_context or {}),
                    project_context=project_context,
                    on_event=self._bridge_event,
                    ticket=ticket,
                )
                final = _TERMINAL_MAP.get(run.status, BG_FAILED)
            except Exception as exc:  # لا استثناءات تهرب من الخيط
                _slog_swallowed("chain/background_delegate.py:_work", exc)
                with self._lock:
                    self._error = str(exc)
                final = BG_FAILED
            with self._lock:
                self._status = final
                self._finished_at = time.monotonic()
            self._record_and_emit("background_finished", {
                "task_id": self.task_id,
                "status": final,
            })

        thread = threading.Thread(
            target=_work, daemon=True,
            name=f"bg-delegate-{self.task_id}")
        self._thread = thread
        thread.start()

    # ── حسم المستخدم (الثابت الصلب: لا مسار كتابة بلا هذين) ──

    def land(self, on_event: Callable | None = None) -> bool:
        """يغلّف bridge.land القائم — يُستدعى بعد موافقة صريحة فقط."""
        ok = self._bridge.land(on_event=on_event or self._on_event)
        if ok:
            with self._lock:
                self._status = BG_LANDED
        return ok

    def reject(self, reason: str = "",
               on_event: Callable | None = None) -> bool:
        """يغلّف bridge.reject القائم."""
        ok = self._bridge.reject(reason=reason,
                                 on_event=on_event or self._on_event)
        if ok:
            with self._lock:
                self._status = BG_REJECTED
        return ok

    # ── حالة إعادة الاتصال (reconnect-safe) ──

    def wait(self, timeout: float | None = None) -> bool:
        """ينتظر انتهاء خيط العمل (للاختبارات/الاستهلاك المتزامن).

        Returns: True لو الخيط انتهى ضمن المهلة."""
        t = self._thread
        if t is None:
            return True
        t.join(timeout)
        return not t.is_alive()

    def snapshot(self) -> dict:
        """الصورة الكاملة الراهنة — تُقرأ من الكائن الحي تحت قفل.

        عميل أعاد الاتصال يستدعيها فيستعيد الحالة وسجل الأحداث
        كاملين بلا اعتماد على ما بثّته الجلسة المقطوعة."""
        snap: dict[str, object]
        with self._lock:
            snap = {
                "task_id": self.task_id,
                "status": self._status,
                "error": self._error,
                "events": [dict(e) for e in self._events],
                "started_at": self._started_at,
                "finished_at": self._finished_at,
            }
        run = self._bridge.current_run
        snap["run"] = run.to_dict() if run is not None else None
        return snap

    # ── داخلي ──

    def _bridge_event(self, event_type: str, event_data: dict) -> None:
        """تمرير أحداث الجسر كما هي + تسجيلها للـsnapshot."""
        self._record_and_emit("background_event", {
            "task_id": self.task_id,
            "event": str(event_type),
            "data": dict(event_data),
        })

    def _record_and_emit(self, event_type: str, data: dict) -> None:
        entry = {"type": event_type, **data}
        with self._lock:
            self._events.append(entry)
        cb = self._on_event
        if cb is None:
            return
        try:
            cb(event_type, data)
        except Exception as _exc:
            # نفس نمط DelegateBridge._emit: فشل مستمع لا يفجّر الدورة
            _slog_swallowed("chain/background_delegate.py:_record_and_emit",
                            _exc)
