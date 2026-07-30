# -*- coding: utf-8 -*-
"""Redis Backends عبر Streams (T-109, R-804) — إضافة اختيارية.

لماذا
-----
R-804 يحتاج توزيع الرصد وقائمة العمل عبر عمليات (workers) — هذا
الموديول يقدّم backend ناقل الأحداث وقائمة العمل فوق Redis Streams،
**إضافةً** لا استبدالًا: الافتراضيان داخل-العملية (T-108) يبقيان
الافتراضيين وأحادي-العملية درجة أولى. سجل التنفيذ على Redis وحجز
المشاريع (lease) نطاق T-110 — هنا الرصد وقائمة العمل فقط.

قرارات الشكل (المسوَّغة في docs/phase8_plan.md §3)
--------------------------------------------------
- **العميل**: ``redis-py`` (``redis>=5.0``) — الرسمي؛ aioredis اندمج
  فيه. **extra اختياري**: لا ``import redis`` أعلى الموديول أبدًا —
  استيراد كسول داخل الأصناف فقط (grep + اختبار استيراد يفرضانه)،
  فاستيراد هذا الموديول بلا الـ extra آمن دائمًا.
- **شكل النشر**: نسخة Redis واحدة standalone عبر ``REDIS_URL``
  (متغير بيئة؛ الافتراضي ``redis://localhost:6379/0``) — لا Cluster
  ولا Sentinel في v1 (مضيف واحد يخدم حفنة workers لا يبررهما؛
  المفتاح يترك المجال لإضافتهما لاحقًا).
- **ناقل الأحداث**: Stream لكل run (``ev:<run_id>``) — XADD/XRANGE
  يعطيان ترتيبًا محفوظًا وإعادة قراءة (replay) — مطلوبان لبند R-804
  «تسلسل إطارات WS بايت-مطابق». Pub/Sub مرفوض (fire-and-forget:
  يُسقط الإطارات عند المستهلك البطيء).
- **قائمة العمل**: Stream ‏``wq:runs`` + مجموعة مستهلكين ``workers`` —
  XADD/XREADGROUP/XACK = تسليم at-least-once، وXAUTOCLAIM يستعيد
  مدخلات worker منهار — أفضل بدقة من LPUSH/BRPOP (يفقد ما في-الطيران).

عقد التوافق
-----------
:class:`RedisEventBusBackend` يحقق :class:`core.backends.EventBusBackend`
بنفس ضمانات الدلالة (FIFO لكل run، عزل المشتركين، تاريخ مسقوف) —
عدة التوافق `EventBusBackendContractMixin` من T-108 تعمل عليه كما هي.
التسليم للمشتركين المحليين متزامن تحت قفل الـ run (نفس داخل-العملية)؛
الجديد أن كل حدث يُكتب أيضًا للـ Stream فيقرأه أي مشترك في عملية أخرى
(``history`` تقرأ من Redis — إعادة القراءة عابرة للعمليات).
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from typing import Any, Callable

from core.events import (
    ApprovalRequested,
    BudgetChanged,
    BusEvent,
    RoutingDecided,
    RunFinished,
    RunStarted,
    StepProgress,
    Subscriber,
)
from core.structured_log import swallowed as _slog_swallowed

#: متغير البيئة + افتراضه — انظر «قرارات الشكل» أعلاه.
REDIS_URL_ENV = "REDIS_URL"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

#: كتالوج فك الترميز — أنواع R-604 الستة (core/events.py).
_EVENT_TYPES: dict[str, type[BusEvent]] = {
    cls.__name__: cls
    for cls in (RunStarted, StepProgress, ApprovalRequested,
                RunFinished, RoutingDecided, BudgetChanged)
}


def _require_redis() -> Any:
    """الاستيراد الكسول الوحيد — extra غائب = خطأ صاخب مفهوم."""
    try:
        import redis  # local import: optional extra (T-109 contract)
    except ImportError as exc:  # pragma: no cover - يتطلب بيئة بلا extra
        raise RuntimeError(
            "Redis backend يحتاج الـ extra الاختياري: "
            "pip install 'redis>=5.0'") from exc
    return redis


def redis_client_from_env(url: str | None = None) -> Any:
    """عميل Redis من ``REDIS_URL`` (أو url صريح) — نقطة البناء الوحيدة.

    ``decode_responses=True``: كل القيم نصوص UTF-8 (حمولاتنا JSON).
    """
    redis = _require_redis()
    return redis.Redis.from_url(
        url or os.environ.get(REDIS_URL_ENV, DEFAULT_REDIS_URL),
        decode_responses=True)


# ═══════════════════════════════════════════════════════
#   ترميز الأحداث (JSON على حقل واحد)
# ═══════════════════════════════════════════════════════

def _encode_event(event: BusEvent) -> dict[str, str]:
    """حدث → حقول Stream: النوع بالاسم + الحقول JSON (يشمل run_id)."""
    return {
        "kind": type(event).__name__,
        "data": json.dumps(asdict(event), ensure_ascii=False),
    }


def _decode_event(fields: dict[str, str]) -> BusEvent:
    """حقول Stream → حدث مكتوب النوع — نوع مجهول = خطأ صاخب لا تخمين."""
    kind = fields.get("kind", "")
    cls = _EVENT_TYPES.get(kind)
    if cls is None:
        raise ValueError(f"نوع حدث مجهول في الـ stream: {kind!r}")
    return cls(**json.loads(fields["data"]))


# ═══════════════════════════════════════════════════════
#   RedisEventBusBackend
# ═══════════════════════════════════════════════════════

class RedisEventBusBackend:
    """ناقل أحداث فوق Redis Streams — stream لكل run (``ev:<run_id>``).

    Args:
        url: عنوان Redis (افتراضي ``REDIS_URL`` من البيئة).
        client: عميل جاهز (حقن للاختبارات) — يتجاوز url.
        stream_prefix: بادئة مفاتيح الـ streams (عزل الاختبارات).
        history_per_run: سقف مدخلات كل stream (MAXLEN دقيق — نفس
            دلالة سقف التاريخ داخل-العملية).
    """

    def __init__(self, url: str | None = None, *,
                 client: Any = None,
                 stream_prefix: str = "ev:",
                 history_per_run: int = 256) -> None:
        self._client = client if client is not None \
            else redis_client_from_env(url)
        self._prefix = stream_prefix
        self._history_per_run = history_per_run
        self._subs: list[Subscriber] = []
        self._subs_lock = threading.Lock()
        # قفل لكل run — نفس نموذج داخل-العملية: FIFO تسليم + كتابة
        self._run_locks: dict[str, threading.RLock] = {}
        self._runs_lock = threading.Lock()

    def _key(self, run_id: str) -> str:
        return f"{self._prefix}{run_id}"

    # ── الاشتراك (محلي — نفس عقد T-047) ──────────────
    def subscribe(self, fn: Subscriber) -> Callable[[], None]:
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
        """XADD للـ stream ثم تسليم محلي — كلاهما تحت قفل الـ run:
        ترتيب الـ stream = ترتيب التسليم = ترتيب النشر (FIFO)."""
        lock = self._lock_for(event.run_id)
        with lock:
            self._client.xadd(
                self._key(event.run_id),
                _encode_event(event),
                maxlen=self._history_per_run,
                approximate=False,
            )
            with self._subs_lock:
                subs = list(self._subs)
            for fn in subs:
                try:
                    fn(event)
                except Exception as _exc:
                    _slog_swallowed("core/backends_redis.py:179", _exc)
                    # عزل: مشترك معطوب لا يوقف البث ولا الناشر
                    pass

    # ── التاريخ (من Redis — عابر للعمليات) ────────────
    def history(self, run_id: str) -> list[BusEvent]:
        """إعادة قراءة مرتبة من الـ stream — أي عملية ترى نفس التسلسل."""
        entries = self._client.xrange(self._key(run_id))
        return [_decode_event(fields) for _entry_id, fields in entries]

    # ── الداخلي ───────────────────────────────────────
    def _lock_for(self, run_id: str) -> threading.RLock:
        with self._runs_lock:
            lock = self._run_locks.get(run_id)
            if lock is None:
                lock = threading.RLock()
                self._run_locks[run_id] = lock
            return lock


# ═══════════════════════════════════════════════════════
#   قائمة العمل — Stream + مجموعة مستهلكين
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class QueueEntry:
    """مدخلة عمل مُستلَمة — ``entry_id`` مطلوب لـ ``ack``."""
    entry_id: str
    payload: dict[str, Any]


class RedisWorkQueue:
    """قائمة عمل الـ runs — Stream ‏``wq:runs`` + مجموعة ``workers``.

    الدورة: ``enqueue`` (الموزّع) → ``claim`` (worker يقرأ الجديد عبر
    XREADGROUP) → تنفيذ → ``ack`` (XACK). worker انهار قبل ack ⇒
    مدخلته تبقى معلّقة (PEL) حتى يستعيدها آخر بـ ``reclaim``
    (XAUTOCLAIM بعد ``min_idle_ms``) — تسليم at-least-once بالبناء.

    Args:
        url/client: كما في :class:`RedisEventBusBackend`.
        stream: مفتاح الـ stream (افتراضي ``wq:runs``).
        group: اسم مجموعة المستهلكين (تُنشأ إن غابت — idempotent).
    """

    def __init__(self, url: str | None = None, *,
                 client: Any = None,
                 stream: str = "wq:runs",
                 group: str = "workers") -> None:
        self._client = client if client is not None \
            else redis_client_from_env(url)
        self._stream = stream
        self._group = group
        self._ensure_group()

    def _ensure_group(self) -> None:
        """إنشاء المجموعة (mkstream) — BUSYGROUP = موجودة، لا خطأ."""
        redis = _require_redis()
        try:
            self._client.xgroup_create(
                self._stream, self._group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    # ── الإدخال ───────────────────────────────────────
    def enqueue(self, payload: dict[str, Any]) -> str:
        """إضافة مهمة — تعيد entry_id (ترتيب Redis الذري)."""
        return str(self._client.xadd(
            self._stream, {"data": json.dumps(payload, ensure_ascii=False)}))

    # ── الاستلام ──────────────────────────────────────
    def claim(self, consumer: str, count: int = 1,
              block_ms: int = 0) -> list[QueueEntry]:
        """قراءة مدخلات **جديدة** للمستهلك (XREADGROUP ‏``>``) —
        المُستلَم يدخل قائمة المعلّق (PEL) حتى ``ack``."""
        resp = self._client.xreadgroup(
            self._group, consumer, {self._stream: ">"},
            count=count, block=block_ms or None)
        entries: list[QueueEntry] = []
        for _stream_key, items in resp or []:
            for entry_id, fields in items:
                entries.append(QueueEntry(
                    entry_id=str(entry_id),
                    payload=json.loads(fields["data"])))
        return entries

    def ack(self, entry_id: str) -> int:
        """تأكيد إنجاز مدخلة — يزيلها من قائمة المعلّق."""
        return int(self._client.xack(self._stream, self._group, entry_id))

    # ── الاستعادة (worker منهار) ──────────────────────
    def reclaim(self, consumer: str, min_idle_ms: int = 60_000,
                count: int = 10) -> list[QueueEntry]:
        """استعادة مدخلات معلّقة خمل أصحابها ≥ ``min_idle_ms``
        (XAUTOCLAIM) — ملكيتها تنتقل لـ ``consumer`` ليكمل أو يعيد."""
        _cursor, items, _deleted = self._client.xautoclaim(
            self._stream, self._group, consumer,
            min_idle_time=min_idle_ms, start_id="0", count=count)
        return [
            QueueEntry(entry_id=str(entry_id),
                       payload=json.loads(fields["data"]))
            for entry_id, fields in items
        ]

    def pending_count(self) -> int:
        """عدد المدخلات المعلّقة (مُستلَمة بلا ack) في المجموعة."""
        info = self._client.xpending(self._stream, self._group)
        return int(info["pending"])
