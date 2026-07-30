# -*- coding: utf-8 -*-
"""ExecutionRegistry + RunTicket (T-014, R-105): real run lifecycle tracking.

Why this exists
---------------
There is no authoritative record of what is executing: chain runs, agent
loops, and delegate flows each manage their own ad-hoc state; the WS layer
cannot enumerate or cancel work it started, and delegate has no cancellation
support at all. This module is the shared lifecycle abstraction: every run
acquires a :class:`RunTicket` from the one :class:`ExecutionRegistry`, which
becomes the single source of truth for "what is running right now".

State diagram (Documentation requirement, T-014)
------------------------------------------------
::

                 register(kind, project_id)
                            │
                            ▼
                      ┌───────────┐   cancel(reason)      ┌──────────────────┐
                      │  running  │──────────────────────►│ running          │
                      └───────────┘  (cooperative flag —  │ + is_cancelled   │
                            │         run must observe)   └──────────────────┘
                            │                                       │
                            │ finish("completed"|"failed")          │ finish("cancelled")
                            ▼                                       ▼
                ┌────────────────────────────────────────────────────────────┐
                │        completed  /  failed  /  cancelled  (terminal)      │
                │  immutable: finish/cancel on a terminal ticket is a no-op  │
                └────────────────────────────────────────────────────────────┘

Cancellation is **cooperative**: ``cancel()`` only raises the ticket's flag
(and records the reason); the executing code checks ``is_cancelled`` at its
own checkpoints and then calls ``finish("cancelled")``. Until it does, the
run honestly remains in ``list_active()`` — the registry never lies about
liveness. (This mirrors ``chain.models.CancellationToken`` semantics so
T-015 can adapt tickets into the existing chain path without behavior
change; ``core`` stays dependency-free of ``chain``.)

Concurrency model
-----------------
One ``threading.Lock`` protects every registry mutation (register / finish /
cancel / heartbeat / reap). Per-project **mutual exclusion** is configurable:
with ``exclusive_per_project=True`` (default) a second ``register()`` for a
project that already has an active run raises :class:`RunBusyError` — the
lock guarantees exactly one winner even under a thundering-herd race.
``finish()`` frees the project slot atomically.

Staleness (TTL)
---------------
Long-running executors call ``ticket.heartbeat()``; if the registry is built
with ``ttl_seconds``, ``reap_stale()`` force-finishes any *running* ticket
whose last heartbeat is older than the TTL as ``failed`` (a crashed worker
must not hold a project slot forever). ``clock`` is injectable for tests.

.. note::
   T-014 ships this standalone (unit-tested, unwired). T-015 threads tickets
   through all three execution modes and **deletes** ``ActiveRunHolder``
   (R-101 interim guard), which this registry supersedes.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Callable, Protocol

# ── الأنواع والحالات المسموحة ──
# T-040 (R-501): "direct" انضم — المسار المباشر صار run مسجّلًا
# بتذكرة عبر DirectRunner (كان الوحيد خارج السجل).
# TSK-304 (NF-04): "apply" انضم — دفعة _apply_batch صارت run مسجّلًا
# بتذكرة (قابلة للإلغاء عبر cancel_run بين كل action).
VALID_KINDS = ("direct", "chain", "agent", "delegate", "apply")
TERMINAL_STATES = ("completed", "failed", "cancelled")
STATE_RUNNING = "running"


class RunBusyError(Exception):
    """مشروع لديه run نشط بالفعل والسجل في وضع الاستبعاد المتبادل."""

    def __init__(self, project_id: str, active_run_id: str) -> None:
        self.project_id = project_id
        self.active_run_id = active_run_id
        super().__init__(
            f"project {project_id!r} already has active run {active_run_id!r}"
        )


class RunTicket:
    """هوية وسطح تحكم لعملية تنفيذ واحدة.

    يُنشأ حصريًا عبر :meth:`ExecutionRegistry.register` — كل الطفرات
    (cancel/finish/heartbeat) تمر عبر قفل السجل نفسه، فقراءة الخصائص
    آمنة من أي خيط.
    """

    def __init__(
        self,
        run_id: str,
        kind: str,
        project_id: str,
        registry: "ExecutionRegistry",
        created_at: float,
    ) -> None:
        self._run_id = run_id
        self._kind = kind
        self._project_id = project_id
        self._registry = registry
        self._created_at = created_at
        # الحقول التالية يملكها السجل ويطفّرها تحت قفله فقط
        self._state: str = STATE_RUNNING
        self._cancel_flag = threading.Event()
        self._cancel_reason: str = ""
        self._last_heartbeat: float = created_at
        self._finished_at: float | None = None

    # ── هوية للقراءة فقط ──
    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def created_at(self) -> float:
        return self._created_at

    # ── الحالة ──
    @property
    def state(self) -> str:
        """``running`` أو إحدى الحالات النهائية (انظر مخطط الحالات أعلاه)."""
        with self._registry._lock:
            return self._state

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def finished_at(self) -> float | None:
        with self._registry._lock:
            return self._finished_at

    # ── الإلغاء التعاوني ──
    @property
    def is_cancelled(self) -> bool:
        """علم الإلغاء مرفوع — سواء لوحظ بعد أم لا (Event → قراءة آمنة بلا قفل)."""
        return self._cancel_flag.is_set()

    @property
    def cancel_reason(self) -> str:
        with self._registry._lock:
            return self._cancel_reason

    def cancel(self, reason: str = "") -> bool:
        """رفع علم الإلغاء (تعاوني). انظر :meth:`ExecutionRegistry.cancel`."""
        return self._registry.cancel(self._run_id, reason)

    # ── نبض الحياة ──
    @property
    def last_heartbeat(self) -> float:
        with self._registry._lock:
            return self._last_heartbeat

    def heartbeat(self) -> bool:
        """تحديث آخر نبضة. False لو الـ run انتهى (نبضة متأخرة لا تُحييه)."""
        with self._registry._lock:
            if self._state != STATE_RUNNING:
                return False
            self._last_heartbeat = self._registry._clock()
            return True

    def finish(self, status: str) -> bool:
        """إنهاء الـ run بحالة نهائية. انظر :meth:`ExecutionRegistry.finish`."""
        return self._registry.finish(self._run_id, status)

    def to_dict(self) -> dict:
        """لقطة قابلة للإرسال عبر WS (تُستخدم في T-015+ لأمر ``list_runs``)."""
        with self._registry._lock:
            return {
                "run_id": self._run_id,
                "kind": self._kind,
                "project_id": self._project_id,
                "state": self._state,
                "is_cancelled": self._cancel_flag.is_set(),
                "cancel_reason": self._cancel_reason,
                "created_at": self._created_at,
                "last_heartbeat": self._last_heartbeat,
                "finished_at": self._finished_at,
            }

    def __repr__(self) -> str:  # pragma: no cover - تسهيل تشخيصي فقط
        return (
            f"RunTicket(run_id={self._run_id!r}, kind={self._kind!r}, "
            f"project_id={self._project_id!r}, state={self.state!r})"
        )


class ExecutionRegistry:
    """السجل المركزي لدورة حياة كل عمليات التنفيذ.

    Args:
        exclusive_per_project: عند True (الافتراضي) يُرفض ``register()``
            ثانٍ لمشروع لديه run نشط بـ :class:`RunBusyError`.
        ttl_seconds: عمر أقصى بلا نبضة قبل أن يعتبر ``reap_stale()``
            الـ run ميتًا (None = تعطيل الحصاد).
        clock: حقن الوقت للاختبارات (افتراضي ``time.time``).
    """

    def __init__(
        self,
        exclusive_per_project: bool = True,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive or None")
        self._exclusive = exclusive_per_project
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._tickets: dict[str, RunTicket] = {}          # run_id → ticket
        self._active_by_project: dict[str, str] = {}      # project_id → run_id

    # ── التسجيل ──
    def register(self, kind: str, project_id: str = "") -> RunTicket:
        """تسجيل run جديد وإرجاع تذكرته (حالتها ``running`` فورًا).

        Raises:
            ValueError: نوع غير معروف (``VALID_KINDS``).
            RunBusyError: المشروع مشغول والسجل في وضع الاستبعاد المتبادل.
        """
        if kind not in VALID_KINDS:
            raise ValueError(f"unknown kind {kind!r}; expected one of {VALID_KINDS}")
        with self._lock:
            if self._exclusive:
                active = self._active_by_project.get(project_id)
                if active is not None:
                    raise RunBusyError(project_id, active)
            run_id = uuid.uuid4().hex
            ticket = RunTicket(
                run_id=run_id,
                kind=kind,
                project_id=project_id,
                registry=self,
                created_at=self._clock(),
            )
            self._tickets[run_id] = ticket
            if self._exclusive:
                self._active_by_project[project_id] = run_id
            return ticket

    # ── الاستعلام ──
    def lookup(self, run_id: str) -> RunTicket | None:
        """التذكرة بمعرّفها، أو None."""
        with self._lock:
            return self._tickets.get(run_id)

    def list_active(self) -> list[RunTicket]:
        """كل التذاكر في حالة ``running`` (بترتيب الإنشاء)."""
        with self._lock:
            return [
                t for t in self._tickets.values() if t._state == STATE_RUNNING
            ]

    def list_all(self) -> list[RunTicket]:
        """كل التذاكر بما فيها المنتهية (بترتيب الإنشاء)."""
        with self._lock:
            return list(self._tickets.values())

    # ── الإنهاء ──
    def finish(self, run_id: str, status: str) -> bool:
        """نقل run إلى حالة نهائية وتحرير خانة مشروعه ذريًا.

        Returns:
            True عند الانتقال؛ False لو الـ run مجهول أو منتهٍ بالفعل
            (الحالات النهائية غير قابلة للطفر — لا double-finish).

        Raises:
            ValueError: حالة ليست من ``TERMINAL_STATES``.
        """
        if status not in TERMINAL_STATES:
            raise ValueError(
                f"invalid terminal status {status!r}; expected one of {TERMINAL_STATES}"
            )
        with self._lock:
            ticket = self._tickets.get(run_id)
            if ticket is None or ticket._state != STATE_RUNNING:
                return False
            ticket._state = status
            ticket._finished_at = self._clock()
            if self._active_by_project.get(ticket._project_id) == run_id:
                del self._active_by_project[ticket._project_id]
            return True

    # ── الإلغاء ──
    def cancel(self, run_id: str, reason: str = "") -> bool:
        """رفع علم الإلغاء التعاوني على run نشط.

        لا ينقل الحالة — الـ run يبقى ``running`` (بصدق) حتى يلاحظ العلم
        عند نقطة تفتيش ويستدعي ``finish("cancelled")`` بنفسه.

        Returns:
            True عند رفع العلم؛ False لو الـ run مجهول أو منتهٍ.
        """
        with self._lock:
            ticket = self._tickets.get(run_id)
            if ticket is None or ticket._state != STATE_RUNNING:
                return False
            if not ticket._cancel_flag.is_set():
                ticket._cancel_reason = reason
                ticket._cancel_flag.set()
            return True

    # ── حصاد الموتى ──
    def reap_stale(self) -> list[RunTicket]:
        """إنهاء كل run نشط تجاوزت آخر نبضته ``ttl_seconds`` كـ ``failed``.

        عامل انهار دون ``finish()`` يجب ألا يحجز خانة مشروعه للأبد.
        No-op (قائمة فارغة) عند تعطيل TTL.
        """
        if self._ttl is None:
            return []
        reaped: list[RunTicket] = []
        with self._lock:
            now = self._clock()
            for ticket in self._tickets.values():
                if ticket._state != STATE_RUNNING:
                    continue
                if now - ticket._last_heartbeat > self._ttl:
                    ticket._state = "failed"
                    ticket._finished_at = now
                    if not ticket._cancel_flag.is_set():
                        ticket._cancel_reason = "stale: heartbeat TTL exceeded"
                        ticket._cancel_flag.set()
                    if (
                        self._active_by_project.get(ticket._project_id)
                        == ticket.run_id
                    ):
                        del self._active_by_project[ticket._project_id]
                    reaped.append(ticket)
        return reaped

    # ── طَهْر التذاكر المنتهية (TSK-303 / NF-06) ──
    def purge_terminal(self, keep_last: int = 50) -> int:
        """حذف أقدم التذاكر المنتهية مع إبقاء آخر ``keep_last`` منها.

        NF-06 (+جزء ذاكرة NF-07): ``_tickets`` كان ينمو بلا سقف — كل run
        منتهٍ يبقى للأبد (تسريب ذاكرة + ``list_all``/``runs_list`` frame
        يتضخمان). الطَهْر يمس التذاكر **المنتهية فقط** (الحالات النهائية
        من ``TERMINAL_STATES``) — التذاكر النشطة لا تُحذف أبدًا مهما كان
        عددها؛ والاحتفاظ بأحدث ``keep_last`` منتهية يُبقي تاريخًا كافيًا
        للواجهة (``_list_runs_frame``) وللتشخيص.

        Args:
            keep_last: عدد التذاكر المنتهية المُبقاة (الأحدث إنشاءً).
                0 = حذف كل المنتهية. قيمة سالبة ⇒ ValueError.

        Returns:
            عدد التذاكر المحذوفة.
        """
        if keep_last < 0:
            raise ValueError("keep_last must be >= 0")
        with self._lock:
            terminal_ids = [
                rid for rid, t in self._tickets.items()
                if t._state in TERMINAL_STATES
            ]
            excess = len(terminal_ids) - keep_last
            if excess <= 0:
                return 0
            # dict يحفظ ترتيب الإدراج (= ترتيب الإنشاء) — الأقدم أولًا.
            for rid in terminal_ids[:excess]:
                del self._tickets[rid]
            return excess


# ── الإيقاف الرشيق (TSK-705 / FI-03) ──
class _ShutdownRegistry(Protocol):
    """السطح البنيوي الأدنى الذي يحتاجه الإيقاف الرشيق.

    لماذا Protocol محلي وليس ``ExecutionRegistry`` صلبًا: مدخل
    server.py يمرر ``RegistryBackend`` (core/backends.py — Protocol
    منذ T-108)، ولا يمكن لـ core/execution استيراد core/backends
    (دورة: backends يستورد execution). الدالة تستخدم ``list_active``
    فقط (الإلغاء يمر عبر التذكرة نفسها) — فهذا كامل السطح المطلوب،
    وكلا النوعين يطابقه بنيويًّا.
    """

    def list_active(self) -> list[RunTicket]: ...


def graceful_shutdown(
    registry: _ShutdownRegistry,
    timeout: float,
    poll_interval: float = 0.05,
) -> list[RunTicket]:
    """إلغاء تعاوني لكل التذاكر الحية ثم انتظار محدود حتى بلوغها حالة نهائية.

    FI-03 (NF-05): خيوط daemon في server.py تموت بلا join عند الخروج —
    قد يقطع SIGTERM/SIGINT عملية تنفيذ في منتصف كتابة ملف. هذه الدالة هي
    نصف "الانضباط" القابل للاختبار: ترفع علم الإلغاء على **كل** run نشط
    (نفس مسار ``cancel_run`` تمامًا — لا آلية إنهاء جديدة) ثم تنتظر بحدّ
    زمني صارم أن تلاحظ العمليات العلمَ وتُنهي نفسها عبر
    ``finish("cancelled")``. لا إنهاء قسري: احترامًا لعقد السجل
    ("السجل لا يكذب بشأن الحياة")، ما لم يُنهِ نفسه خلال المهلة يُعاد
    للمستدعي كما هو — القرار (خروج رغم ذلك/تسجيل) مسؤولية طبقة الإقلاع.

    Args:
        registry: السجل المركزي (يُمرَّر صراحة — الدالة بلا حالة عالمية).
        timeout: أقصى انتظار بالثواني بعد رفع أعلام الإلغاء. 0 = إلغاء
            ثم فحص واحد فوري بلا نوم. قيمة سالبة ⇒ ValueError.
        poll_interval: فاصل الاستطلاع بالثواني (يُقصَّر تلقائيًا كي لا
            يتجاوز النوم الموعدَ النهائي). غير موجب ⇒ ValueError.

    Returns:
        قائمة التذاكر التي ما تزال ``running`` عند انقضاء المهلة
        (فارغة = إيقاف نظيف). **صفر تذاكر حية = عودة فورية** بلا أي نوم.
    """
    if timeout < 0:
        raise ValueError("timeout must be >= 0")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be positive")
    live = registry.list_active()
    if not live:
        return []
    for ticket in live:
        ticket.cancel("graceful shutdown")
    deadline = time.monotonic() + timeout
    while True:
        remaining = registry.list_active()
        if not remaining:
            return []
        now = time.monotonic()
        if now >= deadline:
            return remaining
        time.sleep(min(poll_interval, deadline - now))
