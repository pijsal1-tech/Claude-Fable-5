# -*- coding: utf-8 -*-
"""Worker Process (T-110, R-804): مضيف تنفيذ الـ runs خارج عملية الخادم.

لماذا
-----
عملية Flask الواحدة سقف صلب: run ثقيل يجوّع حلقة الـ WS ولا مسار
scale-out. هذا الموديول يكمل درزات T-108/T-109: الخادم يضع الطلب في
قائمة العمل (``wq:runs``)، وworker منفصل يستهلكه وينفّذ الـ Runner
ويبث الأحداث رجوعًا عبر ناقل Redis Streams — الخادم يعيد بناء نفس
إطارات الواجهة عبر ``_RunnerWSAdapter`` كما لو كان التنفيذ محليًّا.

الأدوار الثلاثة
---------------
- :func:`resolve_dispatch_mode` — درزة config: ``dispatch:`` في
  config.yaml (غائب/in-proc = السلوك التاريخي حرفيًّا؛ اسم مجهول =
  فشل إقلاع صاخب — نفس عقد ``backend:``).
- :class:`WorkerDispatchClient` — **جهة الخادم**: Runner-متوافق
  (نفس توقيع ``run(request, ticket, events)``) يضع الطلب في القائمة
  ثم يتابع stream الأحداث ``ev:<run_id>`` (XREAD ذيلي — لا فقدان
  إطارات مهما طال الـ run، بعكس إعادة قراءة history المسقوفة)
  ويعيد بث كل حدث على الـ sink المحلي — المرسِل في server.py لا
  يفرّق بينه وبين runner محلي.
- :class:`Worker` — **جهة العامل**: حلقة الاستهلاك
  claim → lease → execute → stream → ack. حجز المشروع عبر
  :class:`core.lease.ProjectLease` («مشروع واحد = worker واحد» عابر
  للعمليات) مع خيط تجديد أثناء التنفيذ؛ فشل الاستحواذ = إعادة
  المدخلة للقائمة (requeue+ack — لا تجويع PEL ولا فقدان)، وانقضاء
  الحجز بعد موت العامل يحرر المشروع لعامل آخر تلقائيًّا.

حدود النطاق (T-110)
-------------------
- بوابات الموافقة لا تعبر العمليات بعد: الحمولة تحمل الحقول
  JSON-الآمنة فقط (mode/message/system_prompt/context/metadata) —
  ``proposed_actions``/``approval_gate`` مجال توسعة لاحق.
- إلغاء الخادم أثناء الانتظار يُنهي انتظار العميل محليًّا؛ العامل
  يكمل مدخلته (تسليم at-least-once — نشر الإلغاء عبر العمليات
  توسعة لاحقة).
- توازي الإطارات بايت-بايت يُثبته T-111 (frame-parity harness).

الاستيراد الكسول لـ redis محفوظ: هذا الموديول يستورد من
core.backends_redis (صفر ``import redis`` علوي هناك) — استيراد
worker.py بلا الـ extra آمن حتى أول استخدام فعلي.
"""
from __future__ import annotations

import argparse
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, Callable

from core.backends_redis import (
    QueueEntry,
    RedisEventBusBackend,
    RedisWorkQueue,
    _decode_event,  # فك ترميز الكتالوج الموحّد — نفس مسار history
    redis_client_from_env,
)
from core.events import (
    ApprovalRequested,
    BusEvent,
    RunFinished,
    RunStarted,
    StepProgress,
)
from core.execution import VALID_KINDS, ExecutionRegistry
from core.lease import ProjectLease
from core.runner import (
    EVENT_APPROVAL_REQUEST,
    EVENT_RUN_FINISHED,
    EVENT_RUN_OUTPUT,
    EVENT_RUN_STARTED,
    RESULT_CANCELLED,
    RESULT_FAILED,
    EventSink,
    RunEvent,
    RunRequest,
    RunResult,
    Runner,
)

if TYPE_CHECKING:
    from core.execution import RunTicket


# ═══════════════════════════════════════════════════════
#   درزة config: dispatch mode
# ═══════════════════════════════════════════════════════

#: أوضاع الإرسال المعروفة — in-proc هو الافتراضي التاريخي حرفيًّا.
KNOWN_DISPATCH_MODES = ("in-proc", "worker")
DEFAULT_DISPATCH = "in-proc"


def resolve_dispatch_mode(value: Any) -> str:
    """قيمة ``dispatch:`` من config → وضع معتمد.

    غائب (None) = الافتراضي؛ اسم مجهول/نوع خاطئ = ValueError صاخب
    عند الإقلاع — نفس عقد ``resolve_backend_name`` (T-108): لا سقوط
    صامت لوضع آخر.
    """
    if value is None:
        return DEFAULT_DISPATCH
    if not isinstance(value, str) or value not in KNOWN_DISPATCH_MODES:
        raise ValueError(
            f"وضع dispatch مجهول: {value!r} — المسموح: {KNOWN_DISPATCH_MODES}")
    return value


# ═══════════════════════════════════════════════════════
#   جهة العامل: sink يبث أحداث الـ Runner على ناقل Redis
# ═══════════════════════════════════════════════════════

class _BusEventSink:
    """EventSink يترجم أحداث Runner → أحداث الكتالوج على الـ bus.

    نفس خريطة ``_RunnerWSAdapter`` (server.py) بالضبط — حتى يعيد
    الخادم بناء الإطارات القديمة حرفيًّا من StepProgress/
    ApprovalRequested:

    - run_started → RunStarted (رصدي — لا إطار).
    - run_output → StepProgress(frame_type="chunk") (إطار الرد).
    - approval_request → ApprovalRequested (إطار الموافقة كما هو).
    - أحداث حرة → StepProgress(frame_type=<النوع>) (الإطار الأصلي).
    - run_finished → **مؤجَّل**: يُحفظ ثم يُنشر عبر
      :meth:`publish_finished` بعد عودة الـ Runner — حتى تركب
      ``RunResult`` كاملة (status/text/error) في الحمولة ويعيد
      العميل بناءها في جهة الخادم.
    """

    def __init__(self, bus: RedisEventBusBackend, run_id: str) -> None:
        self._bus = bus
        self._run_id = run_id
        self._finished_data: dict[str, Any] | None = None

    def emit(self, event: RunEvent) -> None:
        data = dict(event.data)
        if event.type == EVENT_RUN_STARTED:
            self._bus.publish(RunStarted(
                run_id=self._run_id,
                mode=str(data.get("mode", "")), payload=data))
        elif event.type == EVENT_RUN_FINISHED:
            self._finished_data = data  # مؤجَّل — انظر docstring
        elif event.type == EVENT_RUN_OUTPUT:
            self._bus.publish(StepProgress(
                run_id=self._run_id, frame_type="chunk",
                payload={"text": data.get("text", "")}))
        elif event.type == EVENT_APPROVAL_REQUEST:
            self._bus.publish(ApprovalRequested(
                run_id=self._run_id, frame_type=event.type, payload=data))
        else:
            self._bus.publish(StepProgress(
                run_id=self._run_id, frame_type=event.type, payload=data))

    def publish_finished(self, result: RunResult) -> None:
        """نشر RunFinished الختامي حاملًا النتيجة الكاملة."""
        data = dict(self._finished_data or {"reason": result.status})
        data["result"] = result.to_dict()
        self._bus.publish(RunFinished(
            run_id=self._run_id, status=result.status, payload=data))


def _default_runner_factory(payload: dict[str, Any]) -> Runner:
    """المصنع الافتراضي — EchoRunner المرجعي (T-039).

    ربط runners الإنتاج (ChainRunner فوق ChainBridge كامل) يتطلب
    إقلاع سياق المشروع داخل العامل — مجال نشر لاحق (انظر
    docs/worker_runbook.md)؛ حقن المصنع هو الدرزة.
    """
    from tests.fakes.echo_runner import EchoRunner
    return EchoRunner()


class Worker:
    """حلقة استهلاك العامل: claim → lease → execute → stream → ack.

    Args:
        queue: قائمة العمل (T-109).
        bus: ناقل الأحداث الرجعي — يجب أن يشارك الخادم نفس البادئة.
        client: عميل Redis للحجوزات (نفس نقطة البناء
            ``redis_client_from_env``).
        worker_id: هوية العامل (تلقائي إن غاب) — قيمة الحجز واسم
            المستهلك في المجموعة.
        lease_ttl_ms: عمر الحجز — موت العامل يحرر المشروع بعده.
        runner_factory: حمولة → Runner (الافتراضي EchoRunner المرجعي).
        registry: سجل تنفيذ محلي للعامل (تذاكر الإلغاء/الإنهاء).
    """

    def __init__(self, queue: RedisWorkQueue, bus: RedisEventBusBackend,
                 client: Any, worker_id: str | None = None, *,
                 lease_ttl_ms: int = 30_000,
                 runner_factory: Callable[[dict[str, Any]], Runner]
                 | None = None,
                 registry: ExecutionRegistry | None = None) -> None:
        self._queue = queue
        self._bus = bus
        self._client = client
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._lease_ttl_ms = lease_ttl_ms
        self._runner_factory = runner_factory or _default_runner_factory
        self._registry = registry or ExecutionRegistry()

    # ── دورة واحدة ────────────────────────────────────
    def run_once(self, block_ms: int = 1000) -> str:
        """معالجة مدخلة واحدة (أو الانتظار حتى ``block_ms``).

        Returns:
            ``"idle"`` لا عمل · ``"requeued"`` المشروع محجوز لعامل
            آخر (أُعيدت المدخلة) · وإلا حالة النتيجة النهائية
            (completed/failed/cancelled).
        """
        entries = self._queue.claim(self.worker_id, count=1,
                                    block_ms=block_ms)
        if not entries:
            return "idle"
        return self._process(entries[0])

    def run_forever(self, *, poll_block_ms: int = 1000,
                    stop: threading.Event | None = None) -> None:
        """حلقة الاستهلاك — تدور حتى يُرفع علم ``stop``."""
        stop = stop or threading.Event()
        while not stop.is_set():
            self.run_once(block_ms=poll_block_ms)

    # ── المعالجة ──────────────────────────────────────
    def _process(self, entry: QueueEntry) -> str:
        payload = entry.payload
        project_id = str(payload.get("project_id", ""))
        lease = ProjectLease(self._client, project_id, self.worker_id,
                             ttl_ms=self._lease_ttl_ms)
        if not lease.acquire():
            # مشروع محجوز لعامل آخر: أعد المدخلة وأكّد القديمة —
            # لا تجويع PEL ولا فقدان (at-least-once محفوظ).
            self._queue.enqueue(payload)
            self._queue.ack(entry.entry_id)
            return "requeued"
        stop_renew = threading.Event()
        renewer = threading.Thread(
            target=self._renew_loop, args=(lease, stop_renew),
            daemon=True, name=f"lease-renew-{self.worker_id}")
        renewer.start()
        try:
            result = self._execute(payload)
            self._queue.ack(entry.entry_id)
            return result.status
        finally:
            stop_renew.set()
            renewer.join(timeout=1.0)
            lease.release()

    def _renew_loop(self, lease: ProjectLease,
                    stop: threading.Event) -> None:
        """تجديد دوري (ثلث الـ TTL) — فشل التجديد = فقدنا الحجز، نتوقف."""
        interval = self._lease_ttl_ms / 3000.0
        while not stop.wait(interval):
            if not lease.renew():
                break

    def _execute(self, payload: dict[str, Any]) -> RunResult:
        run_id = str(payload.get("run_id", ""))
        sink = _BusEventSink(self._bus, run_id)
        mode = str(payload.get("mode", ""))
        if mode not in VALID_KINDS:
            result = RunResult(status=RESULT_FAILED,
                               error=f"وضع مجهول في الحمولة: {mode!r}")
            sink.publish_finished(result)
            return result
        ticket = self._registry.register(
            mode, project_id=str(payload.get("project_id", "")))
        request = RunRequest(
            mode=mode,
            message=str(payload.get("message", "")),
            system_prompt=str(payload.get("system_prompt", "")),
            context=dict(payload.get("context") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )
        runner = self._runner_factory(payload)
        # عقد الـ Runner (بند 4): لا استثناءات للخارج — لكن العامل
        # يحتزم runner مخالفًا حتى لا تسقط حلقته.
        try:
            result = runner.run(request, ticket, sink)
        except Exception as exc:
            result = RunResult(status=RESULT_FAILED, error=str(exc))
            self._registry.finish(ticket.run_id, RESULT_FAILED)
        sink.publish_finished(result)
        return result


# ═══════════════════════════════════════════════════════
#   جهة الخادم: WorkerDispatchClient (Runner-متوافق)
# ═══════════════════════════════════════════════════════

class WorkerDispatchClient:
    """Runner يفوّض التنفيذ لعامل: enqueue ثم متابعة ذيلية للأحداث.

    نفس توقيع ``Runner.run`` — المرسِل في server.py يبدّله مكان
    الـ runner المحلي عندما ``dispatch: worker`` بلا أي تغيير آخر.

    المتابعة عبر XREAD الذيلي على ``ev:<run_id>`` (آخر معرّف مقروء
    → التالي): لا فقدان إطارات مهما تجاوز الـ run سقف MAXLEN — بعكس
    إعادة قراءة ``history`` المسقوفة. الأحداث تُفك بكتالوج T-109
    نفسه ثم تُعاد لـ RunEvent بالخريطة **العكسية** لخريطة العامل —
    فيوصلها ``_RunnerWSAdapter`` كما لو صدرت محليًّا.
    """

    def __init__(self, queue: RedisWorkQueue, client: Any, *,
                 stream_prefix: str = "ev:",
                 timeout_s: float = 120.0,
                 poll_block_ms: int = 100) -> None:
        self._queue = queue
        self._client = client
        self._stream_prefix = stream_prefix
        self._timeout_s = timeout_s
        self._poll_block_ms = poll_block_ms

    def run(self, request: RunRequest, ticket: "RunTicket",
            events: EventSink) -> RunResult:
        self._queue.enqueue({
            "run_id": ticket.run_id,
            "project_id": ticket.project_id,
            "mode": request.mode,
            "message": request.message,
            "system_prompt": request.system_prompt,
            "context": dict(request.context),
            "metadata": dict(request.metadata),
        })
        stream_key = f"{self._stream_prefix}{ticket.run_id}"
        last_id = "0-0"
        seq = 0
        deadline = time.monotonic() + self._timeout_s
        while time.monotonic() < deadline:
            if ticket.is_cancelled:
                # إنهاء الانتظار محليًّا — العامل يكمل مدخلته
                # (at-least-once؛ نشر الإلغاء عبر العمليات لاحق).
                result = RunResult(status=RESULT_CANCELLED)
                ticket.finish(RESULT_CANCELLED)
                return result
            resp = self._client.xread({stream_key: last_id},
                                      count=64, block=self._poll_block_ms)
            for _key, items in resp or []:
                for entry_id, fields in items:
                    last_id = str(entry_id)
                    bus_event = _decode_event(fields)
                    run_event = self._to_run_event(bus_event, ticket.run_id,
                                                   seq)
                    if run_event is not None:
                        events.emit(run_event)
                        seq += 1
                    if isinstance(bus_event, RunFinished):
                        result = self._result_from(bus_event)
                        ticket.finish(result.status)
                        return result
        result = RunResult(
            status=RESULT_FAILED,
            error=f"مهلة انتظار العامل انقضت ({self._timeout_s}s)")
        ticket.finish(RESULT_FAILED)
        return result

    @staticmethod
    def _to_run_event(event: BusEvent, run_id: str,
                      seq: int) -> RunEvent | None:
        """حدث الكتالوج → RunEvent — عكس خريطة ``_BusEventSink``.

        ``seq`` يُختم محليًّا (ترتيب الـ stream = ترتيب النشر —
        الإطارات لا تحمل seq فالأرقام المحلية لا تمس بايتاتها).
        """
        if isinstance(event, RunStarted):
            return RunEvent(type=EVENT_RUN_STARTED, run_id=run_id,
                            seq=seq, data=dict(event.payload))
        if isinstance(event, RunFinished):
            data = {k: v for k, v in event.payload.items() if k != "result"}
            return RunEvent(type=EVENT_RUN_FINISHED, run_id=run_id,
                            seq=seq, data=data)
        if isinstance(event, (StepProgress, ApprovalRequested)):
            if event.frame_type == "chunk":
                return RunEvent(type=EVENT_RUN_OUTPUT, run_id=run_id,
                                seq=seq,
                                data={"text": event.payload.get("text", "")})
            return RunEvent(type=event.frame_type, run_id=run_id,
                            seq=seq, data=dict(event.payload))
        return None  # أحداث رصدية أخرى — لا مقابل لها في مجرى الـ Runner

    @staticmethod
    def _result_from(event: RunFinished) -> RunResult:
        raw = event.payload.get("result")
        if isinstance(raw, dict):
            try:
                return RunResult(status=str(raw.get("status", "")),
                                 text=str(raw.get("text", "")),
                                 error=str(raw.get("error", "")))
            except ValueError:
                pass  # status مشوّه — نسقط لحالة الحدث نفسه
        status = event.status if event.status in (
            "completed", "failed", "cancelled") else RESULT_FAILED
        return RunResult(status=status)


# ═══════════════════════════════════════════════════════
#   نقطة الدخول
# ═══════════════════════════════════════════════════════

def main(argv: list[str] | None = None) -> None:
    """تشغيل عامل واحد: ``python worker.py [--redis-url ...]``.

    الافتراضي ينفّذ EchoRunner المرجعي — ربط runners الإنتاج مجال
    نشر لاحق (docs/worker_runbook.md).
    """
    parser = argparse.ArgumentParser(description="R-804 worker process")
    parser.add_argument("--redis-url", default=None,
                        help="عنوان Redis (الافتراضي: REDIS_URL أو localhost)")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--lease-ttl-ms", type=int, default=30_000)
    parser.add_argument("--once", action="store_true",
                        help="دورة واحدة ثم خروج (للاختبار اليدوي)")
    args = parser.parse_args(argv)

    client = redis_client_from_env(args.redis_url)
    worker = Worker(
        RedisWorkQueue(client=client),
        RedisEventBusBackend(client=client),
        client,
        args.worker_id,
        lease_ttl_ms=args.lease_ttl_ms,
    )
    print(f"👷 worker {worker.worker_id} — يستهلك wq:runs (Ctrl-C للإيقاف)")
    if args.once:
        print(f"   → {worker.run_once()}")
        return
    worker.run_forever()


if __name__ == "__main__":
    main()
