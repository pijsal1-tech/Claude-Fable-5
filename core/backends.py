# -*- coding: utf-8 -*-
"""درزات الـ Backend (T-108, R-804): RegistryBackend + EventBusBackend.

لماذا
-----
R-804 (worker pool) يحتاج Registry وEventBus بواجهات خلفية قابلة
للتبديل (in-mem → Redis Streams في T-109) دون أي تغيير على المستهلكين.
هذا الموديول يستخرج **العقد** فقط: بروتوكولان بنيويان يطابقان السطح
الفعلي للصنفين الحاليين واحدًا-لواحد، والتنفيذان داخل-العملية يصيران
الافتراضيين عبر **aliases لا أصناف جديدة** — صفر تحويل = صفر انحراف،
والتطابق البايتي pre/post مضمون بالبناء (نفس فلسفة استخراج
HeuristicPlanner في T-106).

عقد الـ Backend (Backend contract)
----------------------------------
- :class:`EventBusBackend` — سطح :class:`core.events.EventBus` الحالي:
  ``subscribe`` (يعيد دالة إلغاء)، ``publish`` (FIFO لكل run + عزل
  المشتركين)، ``history`` (آخر الأحداث لكل run)، ``subscriber_count``.
  ضمانات الدلالة (FIFO/العزل/سقف التاريخ) جزء من العقد — عدة التوافق
  في tests/unit/test_backends.py تفرضها على **كل** backend.
- :class:`RegistryBackend` — سطح :class:`core.execution.ExecutionRegistry`
  الحالي: ``register/lookup/list_active/list_all/finish/cancel/
  reap_stale``. مخطط الحالات والإلغاء التعاوني وTTL كما هي موثقة في
  core/execution.py — العقد يرث تلك الدلالة حرفيًّا.
- **البناء خارج العقد**: كل backend له مُنشئه الخاص (in-mem يأخذ
  ttl/clock/history caps؛ Redis سيأخذ URL) — المستهلكون لا يبنون
  مباشرة بل عبر :func:`backends_from_config`.

درزة الاختيار
-------------
مفتاح ``backend:`` أعلى config.yaml — ``resolve_backend_name`` بتحقق
صارم (اسم مجهول/نوع خاطئ = ValueError صاخب عند الإقلاع، نفس فلسفة
routing_config وplanner)؛ None/غائب = ``memory`` (الافتراضي التاريخي،
**صفر تبعيات جديدة** — بند قبول T-108). ``KNOWN_BACKENDS = ("memory",)``
هي نقطة توسعة T-109 الوحيدة (Redis). أحادي-العملية يبقى درجة أولى:
نفس الواجهات، backends داخل-العملية.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

from core.events import BusEvent, EventBus, Subscriber
from core.execution import ExecutionRegistry, RunTicket


# ═══════════════════════════════════════════════════════
#   العقود (Protocols — مطابقة بنيوية)
# ═══════════════════════════════════════════════════════

@runtime_checkable
class EventBusBackend(Protocol):
    """سطح ناقل الأحداث — انظر «عقد الـ Backend» في رأس الموديول."""

    def subscribe(self, fn: Subscriber) -> Callable[[], None]: ...

    def publish(self, event: BusEvent) -> None: ...

    def history(self, run_id: str) -> list[BusEvent]: ...

    @property
    def subscriber_count(self) -> int: ...


@runtime_checkable
class RegistryBackend(Protocol):
    """سطح سجل التنفيذ — دلالة الحالات/الإلغاء/TTL في core/execution.py."""

    def register(self, kind: str, project_id: str = "") -> RunTicket: ...

    def lookup(self, run_id: str) -> RunTicket | None: ...

    def list_active(self) -> list[RunTicket]: ...

    def list_all(self) -> list[RunTicket]: ...

    def finish(self, run_id: str, status: str) -> bool: ...

    def cancel(self, run_id: str, reason: str = "") -> bool: ...

    def reap_stale(self) -> list[RunTicket]: ...


# ═══════════════════════════════════════════════════════
#   التنفيذان داخل-العملية = aliases (صفر انحراف بالبناء)
# ═══════════════════════════════════════════════════════

#: الافتراضي التاريخي حرفيًّا — alias لا صنف جديد ولا wrapper:
#: أي سلوك (FIFO/عزل/تاريخ/TTL) يبقى في مكانه الأصلي الوحيد.
InMemoryEventBusBackend = EventBus
InMemoryRegistryBackend = ExecutionRegistry


# ═══════════════════════════════════════════════════════
#   درزة الاختيار من config
# ═══════════════════════════════════════════════════════

DEFAULT_BACKEND = "memory"

#: نقطة توسعة T-109 الوحيدة (Redis Streams).
KNOWN_BACKENDS: tuple[str, ...] = ("memory",)

#: TSK-608 (RF-02): الافتراضي عند غياب مفتاح ``execution.stale_ttl_seconds``
#: — 15 دقيقة صمتٍ بلا نبضة = run ميت. أطول بكثير من أي مهلة provider
#: (ws_timeout: 90s) ومن مهلة الموافقة (120s) — فلا حصد زائف لخطوة بطيئة.
DEFAULT_STALE_TTL_SECONDS = 900.0


def resolve_stale_ttl(execution_cfg: Any) -> float | None:
    """TSK-608: تحقق صارم لمفتاح ``execution.stale_ttl_seconds``.

    - قسم ``execution:`` غائب أو ليس mapping فيه المفتاح → الافتراضي (900).
    - المفتاح موجود بقيمة null صريحة → None (تعطيل الحصاد).
    - رقم موجب → float. أي شيء آخر (نص/سالب/صفر) → ValueError صاخب
      عند الإقلاع — نفس فلسفة :func:`resolve_backend_name`.
    """
    if not isinstance(execution_cfg, dict) \
            or "stale_ttl_seconds" not in execution_cfg:
        return DEFAULT_STALE_TTL_SECONDS
    value = execution_cfg["stale_ttl_seconds"]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or value <= 0:
        raise ValueError(
            f"execution.stale_ttl_seconds: قيمة غير صالحة {value!r} — "
            "المطلوب رقم موجب أو null (تعطيل)")
    return float(value)


@dataclass(frozen=True)
class BackendPair:
    """ناتج درزة الإقلاع — السجل والناقل المبنيان من نفس الاختيار."""
    name: str
    registry: RegistryBackend
    event_bus: EventBusBackend


def resolve_backend_name(value: Any) -> str:
    """تحقق صارم لقيمة ``backend:`` من config.yaml.

    None/غائب = الافتراضي التاريخي؛ قيمة غير نصية أو اسم مجهول =
    ValueError صاخب عند الإقلاع (لا سقوط صامت لـ backend آخر).
    """
    if value is None:
        return DEFAULT_BACKEND
    if not isinstance(value, str) or value not in KNOWN_BACKENDS:
        raise ValueError(
            f"backend: قيمة مجهولة {value!r} — المعروف: {KNOWN_BACKENDS}")
    return value


def backends_from_config(value: Any,
                         ttl_seconds: float | None = None) -> BackendPair:
    """بناء السجل والناقل من قيمة ``backend:`` — درزة الإقلاع الوحيدة.

    ``memory`` يبني الافتراضيين داخل-العملية بنفس معاملاتهما التاريخية
    (بلا وسائط = نفس ``ExecutionRegistry()`` و``EventBus()`` حرفيًّا).
    T-109 يضيف فرع ``redis`` هنا — المستهلكون لا يتغيرون.

    TSK-608 (RF-02): ``ttl_seconds`` اختياري يمرَّر حرفيًّا لمُنشئ السجل
    — الافتراضي None يبقي النداء بلا وسائط مطابقًا للتاريخي بايت-بايت
    (يثبّته test_backends.py::test_config_built_pair_is_historical_defaults).
    server.py يمرر ناتج :func:`resolve_stale_ttl` هنا عند الإقلاع.
    """
    name = resolve_backend_name(value)
    assert name == "memory"  # نقطة توسعة T-109 — الفحص أعلاه حصر الأسماء
    return BackendPair(
        name=name,
        registry=InMemoryRegistryBackend(ttl_seconds=ttl_seconds),
        event_bus=InMemoryEventBusBackend(),
    )
