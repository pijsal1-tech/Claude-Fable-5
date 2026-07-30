# -*- coding: utf-8 -*-
"""EventBus (T-047, R-604): مجرى الأحداث الداخلي الموحّد.

لماذا
-----
أحداث التقدم/الحالة/الموافقة كانت تصل الواجهة عبر نداءات ``ws.send``
مبعثرة حسب الوضع؛ المستهلكون الداخليون (logging/metrics/سجلات التوجيه
R-402) لم يملكوا نقطة اشتراك. هذا الموديول يفصل **التنفيذ عن النقل**:
المنفّذون ينشرون أحداثًا مكتوبة الأنواع على الـ bus، وطبقة الـ WS تشترك
وتحوّلها لإطارات مطابقة للقديم (wire compatibility محفوظة — المحوّل
الوحيد يعيش في server.py).

كتالوج الأحداث (Event Catalog)
------------------------------
كل الأحداث frozen dataclasses تحمل ``run_id`` (مفتاح ترتيب FIFO):

- :class:`RunStarted`   — بدأت تشغيلة. ``mode`` = direct/chain/agent/
  delegate. **لا إطار WS** (الواجهة لا تعرف run_started — إطار
  ``start`` يُرسل من موقع الإرسال كما كان).
- :class:`StepProgress` — أي تقدّم حر أثناء التشغيلة. ``frame_type``
  يحمل اسم الإطار القديم حرفيًّا (``chunk`` / ``chain_step`` /
  ``agent_*`` / ``delegate_*`` ...) و``payload`` حمولته — المحوّل
  يعيد بناء الإطار القديم ``{"type": frame_type, **payload}`` بايت-بايت.
- :class:`ApprovalRequested` — طلب موافقة معلّق (``approval_request``
  أو ``chain_approval_request``) — يُرسل للواجهة بنفس شكله القديم.
- :class:`RunFinished`  — انتهت التشغيلة. ``status`` =
  completed/failed/cancelled. **لا إطار WS** (نفس القديم).
- :class:`RoutingDecided` — قرار الراوتر (R-402): الاستراتيجية +
  التفاصيل. حدث رصدي إضافي — **لا إطار WS** (إطار ``chain_started``
  القديم يُرسل من موقعه كما كان).
- :class:`BudgetChanged` — تغيّر ميزانية التشغيلة (يُشتق من الإطارات
  الحاملة لمفتاح ``budget``). حدث رصدي — **لا إطار WS**.

ضمانات الـ Bus
--------------
- **FIFO لكل run**: النشر لنفس ``run_id`` متسلسل تحت قفل الـ run —
  ترتيب التسليم لكل مشترك = ترتيب النشر (أحداث الـ runs المختلفة قد
  تتداخل — لا ضمان ترتيب عابر للـ runs).
- **عزل المشتركين**: استثناء مشترك لا يمس بقية المشتركين ولا الناشر.
- **تاريخ لكل run**: آخر ``history_per_run`` حدثًا تُحفظ للتشخيص
  (``history(run_id)``)؛ عدد الـ runs المحفوظة مسقوف (LRU).

الاشتراك يعيد دالة إلغاء الاشتراك — لا حاجة لتذكر مرجع المشترك.
"""
from __future__ import annotations

import threading
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any, Callable
from core.structured_log import swallowed as _slog_swallowed


# ═══════════════════════════════════════════════════════
#   الأحداث المكتوبة الأنواع
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class BusEvent:
    """الأساس — كل حدث مربوط بتشغيلة (run_id = مفتاح ترتيب FIFO)."""
    run_id: str


@dataclass(frozen=True)
class RunStarted(BusEvent):
    """بدأت تشغيلة — mode = direct | chain | agent | delegate."""
    mode: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepProgress(BusEvent):
    """تقدّم حر — frame_type = اسم الإطار القديم، payload = حمولته."""
    frame_type: str = "step_progress"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalRequested(BusEvent):
    """طلب موافقة معلّق — يُحوَّل لإطاره القديم حرفيًّا."""
    frame_type: str = "approval_request"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunFinished(BusEvent):
    """انتهت تشغيلة — status = completed | failed | cancelled."""
    status: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingDecided(BusEvent):
    """قرار توجيه (R-402) — حدث رصدي، لا إطار واجهة."""
    strategy: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BudgetChanged(BusEvent):
    """تغيّرت الميزانية — حدث رصدي، لا إطار واجهة."""
    payload: dict[str, Any] = field(default_factory=dict)


Subscriber = Callable[[BusEvent], None]


# ═══════════════════════════════════════════════════════
#   EventBus
# ═══════════════════════════════════════════════════════

class EventBus:
    """ناقل أحداث داخل-العملية — تسليم متزامن، FIFO لكل run.

    - ``subscribe(fn)`` يعيد دالة إلغاء الاشتراك.
    - ``publish(event)`` يسلّم لكل المشتركين تحت قفل الـ run —
      استثناءات المشتركين تُبتلع (عزل).
    - ``history(run_id)`` يعيد الأحداث المسجلة (للتشخيص/الاختبار).
    """

    def __init__(self, history_per_run: int = 256,
                 max_runs: int = 512) -> None:
        self._history_per_run = history_per_run
        self._max_runs = max_runs
        self._subs: list[Subscriber] = []
        self._subs_lock = threading.Lock()
        # قفل لكل run (RLock — نشر متسلسل من داخل مشترك لا يقفل نفسه)
        self._run_locks: dict[str, threading.RLock] = {}
        self._runs_lock = threading.Lock()
        self._history: "OrderedDict[str, deque[BusEvent]]" = OrderedDict()

    # ── الاشتراك ──────────────────────────────────────
    def subscribe(self, fn: Subscriber) -> Callable[[], None]:
        """يسجّل مشتركًا؛ يعيد دالة إلغاء الاشتراك (idempotent)."""
        with self._subs_lock:
            self._subs.append(fn)

        def _unsubscribe() -> None:
            with self._subs_lock:
                if fn in self._subs:
                    self._subs.remove(fn)

        return _unsubscribe

    @property
    def subscriber_count(self) -> int:
        with self._subs_lock:
            return len(self._subs)

    # ── النشر ─────────────────────────────────────────
    def publish(self, event: BusEvent) -> None:
        """ينشر حدثًا — FIFO لكل run، عزل المشتركين، تسجيل بالتاريخ."""
        lock = self._lock_for(event.run_id)
        with lock:
            self._record(event)
            with self._subs_lock:
                subs = list(self._subs)
            for fn in subs:
                try:
                    fn(event)
                except Exception as _exc:
                    _slog_swallowed("core/events.py:160", _exc)
                    # عزل: مشترك معطوب لا يوقف البث ولا الناشر
                    pass

    # ── التاريخ ───────────────────────────────────────
    def history(self, run_id: str) -> list[BusEvent]:
        with self._runs_lock:
            events = self._history.get(run_id)
            return list(events) if events is not None else []

    # ── الداخلي ───────────────────────────────────────
    def _lock_for(self, run_id: str) -> threading.RLock:
        with self._runs_lock:
            lock = self._run_locks.get(run_id)
            if lock is None:
                lock = threading.RLock()
                self._run_locks[run_id] = lock
            return lock

    def _record(self, event: BusEvent) -> None:
        with self._runs_lock:
            dq = self._history.get(event.run_id)
            if dq is None:
                dq = deque(maxlen=self._history_per_run)
                self._history[event.run_id] = dq
                # سقف عدد الـ runs المحفوظة (LRU على الأقدم)
                while len(self._history) > self._max_runs:
                    old_run, _ = self._history.popitem(last=False)
                    self._run_locks.pop(old_run, None)
            dq.append(event)
