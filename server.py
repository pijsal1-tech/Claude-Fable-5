# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🖥️ WebDev AI Editor — Web Server
  Flask + WebSocket backend للواجهة
  الاستخدام: python server.py --project ./my_site
═══════════════════════════════════════════════════════
"""
import sys
import os
import json
import argparse
import pathlib
import threading
import queue
import time
import uuid
from types import SimpleNamespace  # TSK-612 (ADR-002)
# ── إجبار UTF-8 ──
if hasattr(sys.stdout, "reconfigure"):
    # NF-14 §1 (ابتلاع مقصود — تجميلي): فشل ضبط الترميز لا يعطل الإقلاع.
    # TSK-305: ضُيّقت من except العارية (كانت تبتلع حتى KeyboardInterrupt).
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

_DIR = pathlib.Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock

from actions.file_manager import FileManager
from actions.command_runner import CommandRunner
from actions.response_parser import ResponseParser
from actions.session_manager import SessionManager
from prompts.templates import build_prompt, fence_attached, get_system_prompt
from providers.registry import register_provider, get_provider, list_providers
from providers.use_ai import UseAIProvider, UseAIConfig
from providers.genspark import GensparkProvider, GensparkConfig, GENSPARK_MODELS
from providers.deepseek import DeepSeekProvider, DeepSeekConfig
from providers.alle_ai import AlleAIProvider, AlleAIConfig
from providers.openai_shelby import OpenAIShelbyProvider, OpenAIShelbyConfig
from providers.base import Message
from sessions.memory import WindowPolicy, select_history
from context.budget import CharsPerTokenEstimator  # TSK-609 (PM-01)
from context.facade import gather_message_context
from chain.bridge import ChainBridge
from chain.delegate import DelegateBridge
from chain.orchestrator import SmartOrchestrator
from chain.router import RequestRouter
from core.strategy import RoutingTier
from chain.action_applier import ActionApplier
from providers.budget import AccountAwareBudget
from providers.capacity import CapacityModel
from providers.pool import ProviderPool
from chain.agent_loop import AgentLoop
from chain.agent_tools import AgentTools, command_policy_from
from core.runner import (
    EVENT_RUN_FINISHED,
    EVENT_RUN_OUTPUT,
    EVENT_RUN_STARTED,
    RESULT_COMPLETED,
    RESULT_FAILED,
    RunEvent,
    RunRequest,
)
from runners.agent import AgentRunner
from runners.chain import ChainRunner
from runners.delegate import DelegateRunner
from runners.direct import DirectRunner
from core.approval import ApprovalGate
from core.run_metrics import RunMetricsRecorder, RunMetricsStore  # TSK-610
from core.ws_router import dispatch as ws_dispatch  # TSK-611 (ADR-001)
from core.chat_dispatch import dispatch_chat_message  # TSK-612 (ADR-002)
from core.project_memory import (
    ProjectMemoryStore, CorruptMemoryError, is_stale as _memory_is_stale,
)
from chain.knowledge import KnowledgeAccumulator
from core.execution import ExecutionRegistry
from core.execution import RunBusyError
from core.session_context import SessionContext
from core.events import (
    ApprovalRequested,
    BudgetChanged,
    EventBus,
    RoutingDecided,
    RunFinished,
    RunStarted,
    StepProgress,
)
from core.app_context import AppContext, ProjectHandle

# ════════════════════════════════════════════════════
# Flask App
# ════════════════════════════════════════════════════
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # ← لا cache للملفات الـ static
sock = Sock(app)


@app.after_request
def add_no_cache_headers(response):
    """منع الـ cache أثناء التطوير — يضمن تحميل آخر نسخة دائماً"""
    if "text/html" in response.content_type or \
       "javascript" in response.content_type or \
       "text/css" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _clean_expired_pending_requests() -> None:
    """تنظيف طلبات المسارات المعلقة منتهية الصلاحية (TTL = 5 دقائق).
    يُستدعى تلقائياً قبل كل إضافة جديدة لمنع تسريب الذاكرة.

    TSK-301 (NF-01): يجب أن يُستدعى والمستدعي ممسكًا
    بـ ``_pending_path_lock`` — كان يطوف/يطفر القاموس خارج القفل
    (سباق مع store/pop: RuntimeError «dictionary changed size during
    iteration» تحت الضغط). الآن الطوفان والحذف كلاهما داخل القفل
    (عبر store_pending_path_request).
    """
    now = time.time()
    expired = [k for k, v in pending_path_requests.items()
               if now - v.get("timestamp", 0) > _PENDING_PATH_TTL]
    for k in expired:
        pending_path_requests.pop(k, None)



# ── Globals (يتم تعيينها في main) ──
fm: FileManager = None  # type: ignore[assignment]  # sentinel يُملأ في main (ADR-004)
cmd_runner: CommandRunner = None  # type: ignore[assignment]  # sentinel يُملأ في main (ADR-004)
parser = ResponseParser()
provider = None
chat_history: list[Message] = []
session_mgr: SessionManager = None  # type: ignore[assignment]
# R-303 (T-031): بانر تنبيه ربط الجلسة — يُملأ عند تبديل المشروع تحت
# سياسة warn ويُحقن في project_context لكل رسالة حتى بدء جلسة جديدة.
_binding_banner: str = ""
# TSK-203 (NF-23.2): التعريف الوحيد للثابت — النسخة المكررة أسفل
# الملف أُزيلت (كانت تطغى على هذه بصمت بنفس القيمة).
MAX_SMART_FILE_SIZE = 100 * 1024  # حد أقصى لحجم ملف يقرأه Smart Path (100KB)


# ── قارئ config الموحّد (TSK-203 / NF-23.3) ──
# مصدر واحد لقراءة config.yaml بدل ستة مواضع yaml.safe_load متفرقة.
# مُكاش بمفتاح المسار (يحترم monkeypatch لـ _DIR في الاختبارات) —
# config يُقرأ مرة واحدة لكل مسار؛ تغييره يتطلب إعادة تشغيل (موثّق).
# تسامحي: فشل القراءة يعيد {} — لا يمنع الإقلاع (نفس عقد _read_config
# التاريخي)؛ صخب الـ schema المكسورة يبقى في المحلّلات المتخصصة
# (thresholds_from_config / planner_from_config …) لا في القارئ.
_config_cache: dict = {}


def _load_config() -> dict:
    """قراءة config.yaml مُكاشة — تسامحية: فشل القراءة يعيد {}."""
    key = str(_DIR / "config.yaml")
    if key in _config_cache:
        return _config_cache[key]
    try:
        import yaml as _yaml
        with open(key, encoding="utf-8") as _cf:
            cfg = _yaml.safe_load(_cf) or {}
    except Exception:
        # NF-14 §2 (ابتلاع مقصود — fallback موثّق): config غير مقروء → إعدادات فارغة.
        cfg = {}
    _config_cache[key] = cfg
    return cfg


# الاسم التاريخي — alias للتوافق الخلفي (تستهلكه الاختبارات وmain).
_read_config = _load_config


def _force_command_approval() -> bool:
    """TSK-502 (NF-16): راية إلزام الموافقة على كل أمر.

    تُقرأ من config.yaml (مفتاح ``force_command_approval``، الافتراضي
    False = توافق سلوكي كامل مع ما قبل TSK-502). مفعّلة ⇒ كل مواضع
    التنفيذ ذات ``need_approval=False`` (REST /api/run، /api/run-file،
    وapply-actions) تمر ببوابة الموافقة إلزاميًا — حارس
    DANGEROUS_COMMANDS الساكن لم يعد الخط الوحيد. تُقرأ عند كل طلب
    (القارئ مُكاش — لا كلفة)؛ القيمة تُطبّع بـ bool تسامحيًا.
    راجع قسم «حدود النشر» في README — الراية إلزامية عند أي ربط
    خارج localhost.
    """
    try:
        return bool(_load_config().get("force_command_approval", False))
    except Exception:
        # NF-14 §2 (ابتلاع مقصود — fallback موثّق): config غير مقروء →
        # الافتراضي المتوافق سلوكيًا (لا إلزام).
        return False

# ── نظام المسارات المعلقة: منع التبديل التلقائي ──
# بدلاً من تغيير المجلد فوراً، نحفظ الطلب هنا وننتظر قرار المستخدم.
pending_path_requests: dict = {}   # {req_id: {"path": ..., "timestamp": ...}}
_pending_path_lock = threading.Lock()
_PENDING_PATH_TTL = 300  # ثواني (5 دقائق)


def store_pending_path_request(req_id: str, data: dict) -> None:
    """تنظيف وتخزين طلب مسار معلق مع بيانات الرسالة الأصلية.

    TSK-301 (NF-01): التنظيف انتقل داخل القفل — كان يجري قبله
    فيسابق store/pop من خيوط أخرى على نفس القاموس.
    """
    with _pending_path_lock:
        _clean_expired_pending_requests()
        pending_path_requests[req_id] = data


def pop_pending_path_request(req_id: str) -> dict | None:
    """استخراج وإزالة طلب مسار معلق"""
    with _pending_path_lock:
        return pending_path_requests.pop(req_id, None)



# ── Chain System Infrastructure (M0 + M5) ──
# T-108 (R-804): درزة الـ backends — السجل والناقل الرصدي العام يُبنيان
# من مفتاح ``backend:`` في config (غائب/memory = الافتراضيان التاريخيان
# حرفيًّا؛ اسم مجهول = فشل إقلاع صاخب). ملاحظة نطاق: buses الاتصالات
# (_json_sender/ws_handler) نقلٌ محلي داخل-العملية بطبيعته — تبقى
# EventBus() مباشرة خارج الدرزة (T-109 يوزّع الرصد لا النقل).
from core.backends import backends_from_config, resolve_stale_ttl
# TSK-203 (NF-23.3): القراءة عبر القارئ الموحّد — قراءة متعذرة ⇒ {}
# ⇒ الافتراضيان (نفس تسامح الإقلاع السابق حرفيًا).
_cfg_root = _load_config()
_backend_cfg = _cfg_root.get("backend")
_dispatch_cfg = _cfg_root.get("dispatch")
# TSK-608 (RF-02): TTL الحصاد من config (execution.stale_ttl_seconds —
# غائب = 900s، null = تعطيل، غير صالح = فشل إقلاع صاخب).
_stale_ttl = resolve_stale_ttl(_cfg_root.get("execution"))
_backends = backends_from_config(_backend_cfg, ttl_seconds=_stale_ttl)

# T-110 (R-804): درزة الإرسال — ``dispatch:`` من config (غائب/in-proc =
# السلوك التاريخي حرفيًّا؛ اسم مجهول = فشل إقلاع صاخب — نفس عقد
# ``backend:``). عند worker: تشغيلات السلسلة تُفوَّض عبر
# WorkerDispatchClient (worker.py) — نفس توقيع Runner ونفس موقع
# الإرسال، فالإطارات تُعاد كما هي عبر _RunnerWSAdapter.
from worker import WorkerDispatchClient, resolve_dispatch_mode
_dispatch_mode = resolve_dispatch_mode(_dispatch_cfg)


def _chain_runner_for_dispatch(bridge):
    """T-110: اختيار منفّذ السلسلة حسب وضع الإرسال.

    in-proc (الافتراضي) = ``RUNNERS["chain"]`` التاريخي حرفيًّا؛
    worker = عميل التفويض (enqueue + متابعة أحداث ذيلية) — نفس توقيع
    ``Runner.run`` فيبقى موقع الإرسال (thread + _RunnerWSAdapter) كما هو.
    """
    if _dispatch_mode == "worker":
        from core.backends_redis import (RedisWorkQueue,
                                         redis_client_from_env)
        _wq_client = redis_client_from_env()
        return WorkerDispatchClient(RedisWorkQueue(client=_wq_client),
                                    _wq_client)
    return RUNNERS["chain"](bridge=bridge)

# R-105 (T-015): ExecutionRegistry supersedes the R-101 interim
# ActiveRunHolder (deleted). Every dispatch — chain / agent / delegate —
# registers a RunTicket; the registry enforces the single-run policy and
# ticket cancellation reaches the loops at their checkpoints.
execution_registry = _backends.registry

# T-047 (R-604): الـ bus الرصدي العام — RunStarted/RunFinished/
# RoutingDecided/BudgetChanged تُنشر هنا لأي مستهلك داخلي (logging/
# metrics/سجلات R-402) دون أي علاقة بالنقل. إطارات الواجهة تمشي على
# bus خاص بكل اتصال يستهلكه _WSAdapter وحده.
event_bus = _backends.event_bus

# أنواع إطارات الموافقة — تُنشر ApprovalRequested (بقية الإطارات StepProgress)
_APPROVAL_FRAME_TYPES = ("approval_request", "chain_approval_request",
                         "agent_approval_request")


class _WSAdapter:
    """T-047 (R-604): بوابة النقل الوحيدة — **موقع ws.send الأوحد**.

    يشترك في bus الاتصال ويحوّل الأحداث المكتوبة الأنواع إلى إطارات
    الواجهة القديمة حرفيًّا: ``{"type": frame_type, **payload}``.
    الأحداث الرصدية (RunStarted/RunFinished/RoutingDecided/
    BudgetChanged) لا تُنتج إطارًا — نفس دلالة القديم.
    check.sh يمنع بالـ grep أي ``ws.send`` خارج هذا الصنف.
    """

    def __init__(self, ws, bus: EventBus):
        self._ws = ws
        self._lock = threading.Lock()
        self._unsubscribe = bus.subscribe(self._on_event)

    def close(self) -> None:
        self._unsubscribe()

    def _on_event(self, event) -> None:
        if isinstance(event, (StepProgress, ApprovalRequested)):
            self._send({"type": event.frame_type, **event.payload})
        # RunStarted/RunFinished/RoutingDecided/BudgetChanged → لا إطار

    def _send(self, frame: dict) -> None:
        try:
            with self._lock:
                self._ws.send(json.dumps(frame, ensure_ascii=False))
        except Exception:
            # NF-14 §3 (ابتلاع مقصود): WS مقفول/معطوب — نفس ابتلاع القديم (عقد T-047).
            pass


def _frame_publisher(bus: EventBus, conn_key: str | None = None):
    """T-047: يحوّل إطار dict قديم → حدث مكتوب النوع على الـ bus.

    الإطار لا يُعاد تشكيله: ``type`` يصبح ``frame_type`` والبقية
    ``payload`` كما هي — المحوّل يعيد بناءه بايت-بايت. إطارات الموافقة
    تُنشر :class:`ApprovalRequested`؛ أي إطار يحمل ``budget`` يُشتق منه
    :class:`BudgetChanged` رصدي على الـ bus العام.
    """
    key = conn_key or f"ws-{uuid.uuid4().hex[:8]}"

    def _publish_frame(msg: dict) -> None:
        ftype = str(msg.get("type", ""))
        payload = {k: v for k, v in msg.items() if k != "type"}
        rid = str(msg.get("run_id") or key)
        if ftype in _APPROVAL_FRAME_TYPES:
            bus.publish(ApprovalRequested(run_id=rid, frame_type=ftype,
                                          payload=payload))
        else:
            bus.publish(StepProgress(run_id=rid, frame_type=ftype,
                                     payload=payload))
        if isinstance(msg.get("budget"), dict):
            event_bus.publish(BudgetChanged(run_id=rid,
                                            payload={"budget": msg["budget"]}))

    return _publish_frame


class _RunnerWSAdapter:
    """T-040/T-041: EventSink يترجم أحداث Runner → إطارات WS حرفيًا.

    - run_output → ``{"type": "chunk", "text": ...}`` (رد direct/agent).
    - أحداث الإطارات الحرة (chain_* / agent_* / delegate_*) → الإطار
      الأصلي كما كان: ``{"type": <event.type>, **event.data}`` — بايت-بايت.
    - run_started / run_finished → لا إطار (الواجهة لا تعرفهما؛
      إطار ``start`` يُرسل من موقع الإرسال المشترك نفسه).
    """

    def __init__(self, send_fn):
        self._send = send_fn

    def emit(self, event: RunEvent) -> None:
        # TSK-608 (RF-02): كل حدث من الـ runner = نبضة حياة للتذكرة —
        # بدونها تبقى _last_heartbeat = created_at فيحصد reap_stale الـ
        # runs الحية الطويلة زورًا. lookup مجهول/منتهٍ → لا-عملية آمنة
        # (heartbeat على تذكرة غير running يعيد False بلا أثر).
        _hb_ticket = execution_registry.lookup(event.run_id)
        if _hb_ticket is not None:
            _hb_ticket.heartbeat()
        if event.type == EVENT_RUN_STARTED:
            # T-047: لا إطار واجهة (كما كان) — حدث رصدي على الـ bus العام
            event_bus.publish(RunStarted(run_id=event.run_id,
                                         mode=str(event.data.get("mode", "")),
                                         payload=dict(event.data)))
            return
        if event.type == EVENT_RUN_FINISHED:
            event_bus.publish(RunFinished(
                run_id=event.run_id,
                status=str(event.data.get("reason", "")),
                payload=dict(event.data)))
            return
        if event.type == EVENT_RUN_OUTPUT:
            self._send({"type": "chunk", "text": event.data.get("text", "")})
            return
        self._send({"type": event.type, **event.data})


# T-041 (R-501): مسار إرسال واحد — علم LEGACY_DISPATCH والسلم القديم
# (stream-worker المباشر، start_chain المباشر، حلقة استطلاع الـ Agent)
# حُذفوا جميعًا. كل وضع يُرسل عبر runner موحّد يجتاز RunnerContractMixin.
# القيم مصانع لأن كل runner يُبنى بسياق طلبه (جسر/مزوّد/إغلاقات WS)؛
# الإرسال دائمًا: ``RUNNERS[strategy](**deps).run(request, ticket, sink)``.
RUNNERS = {
    "direct": lambda **d: DirectRunner(d["stream_fn"]),
    "chain": lambda **d: ChainRunner(d["bridge"]),
    "agent": lambda **d: AgentRunner(d["loop_factory"],
                                     on_loop=d.get("on_loop")),
    "delegate": lambda **d: DelegateRunner(d["bridge"]),
}


def _begin_run_ticket(kind, send_fn, sctx=None):
    """T-015 (R-105): register a run of `kind` or emit a `busy` frame.

    Returns the RunTicket on success, None when another run is active
    (in which case a `busy` frame was already sent via send_fn).

    TSK-302 (NF-02) — سياسة خانة الـ run: السجل يستبعد لكل مشروع
    (``exclusive_per_project``)، لكن كل النداءات كانت تمرر الخانة
    العالمية ``""`` — فتبويبان على مشروعين مختلفين كانا يتزاحمان
    زورًا. الآن: عند تمرير ``sctx`` وله مقبض مشروع، تُستخدم
    ``sctx.project.project_id`` (المسار المُطبّع) — مشروعان مختلفان
    يشغّلان معًا، ونفس المشروع → busy. **قرار موثّق عند الغياب**:
    بلا sctx أو بلا مقبض مشروع → الخانة العالمية ``""`` (السلوك
    التاريخي — أأمن من تخمين هوية؛ عقود contracts/ القائمة تبقى
    الحارس الانحداري لدورة حياة التذكرة نفسها).

    TSK-303 (NF-06) — قبل كل تسجيل جديد نستدعي
    ``execution_registry.purge_terminal()`` لحذف أقدم التذاكر
    المنتهية (يبقى آخر 50) — فلا ينمو ``_tickets`` بلا سقف مع
    مئات الـ runs المتتابعة، ويبقى إطار ``runs_list`` مسقوفًا.
    """
    project_id = ""
    if sctx is not None and getattr(sctx, "project", None) is not None:
        try:
            project_id = sctx.project.project_id
        except Exception:
            # NF-14 §4 (ابتلاع مقصود — قرار TSK-302): مقبض بلا هوية → الخانة العالمية.
            project_id = ""
    # TSK-608 (RF-02): حصاد التذاكر اليتيمة (خيط مات بلا finish) قبل
    # كل تسجيل — أرخص نقطة تغطي كل الأنواع (نفس نمط TSK-303 أدناه).
    # قبل purge عمدًا: المحصود يصير terminal فيخضع لسقف الطَهْر فورًا.
    # No-op حرفيًّا عند تعطيل TTL (execution.stale_ttl_seconds: null).
    for _reaped in execution_registry.reap_stale():
        print(f"  ⚰️ reap_stale: {_reaped.run_id} ({_reaped.kind}) — "
              f"خانة المشروع {_reaped.project_id or 'global'!r} تحررت")
    # TSK-303 (NF-06): طَهْر التذاكر المنتهية القديمة عند كل تسجيل جديد
    # — يمنع تسرّب الذاكرة وتضخّم إطار runs_list (السقف: آخر 50 منتهية).
    execution_registry.purge_terminal()
    try:
        return execution_registry.register(kind, project_id)
    except RunBusyError as e:
        send_fn({
            "type": "busy",
            "text": "⚠️ في run نشط حالياً. ألغيه أولاً أو استنى يخلص.",
            "active_run": e.active_run_id,
        })
        return None


def _json_sender(ws):
    """T-047 (R-604): كان يلفّ ws.send مباشرة — الآن يبني خط أنابيب
    كامل لنفس الاتصال: bus → :class:`_WSAdapter` (موقع الإرسال الأوحد)
    → ناشر إطارات. نفس العقد القديم بالضبط: JSON فقط، ابتلاع أخطاء
    الإرسال، ولا مساس بدورة حياة التذكرة (T-015)."""
    bus = EventBus()
    _WSAdapter(ws, bus)   # يبقى حيًّا عبر اشتراكه في الـ bus
    return _frame_publisher(bus)


def _list_runs_frame():
    """T-016 (R-105): ``runs_list`` frame — every run the registry knows.

    Each entry: id / mode / state / started_at (per spec) plus the
    cancellation & finish metadata the UI needs for honest state.
    """
    runs = []
    for _t in execution_registry.list_all():
        snap = _t.to_dict()
        runs.append({
            "id": snap["run_id"],
            "mode": snap["kind"],
            "state": snap["state"],
            "started_at": snap["created_at"],
            "is_cancelled": snap["is_cancelled"],
            "cancel_reason": snap["cancel_reason"],
            "finished_at": snap["finished_at"],
        })
    return {"type": "runs_list", "runs": runs}


def _cancel_run_frame(run_id, reason=""):
    """T-016 (R-105): ``cancel_run_result`` frame.

    Raises the cooperative cancel flag on the target ticket — the loop
    observes it at its next checkpoint (T-015); no mid-request abort.
    acknowledged=False + error="not_found" for unknown/terminal runs.
    """
    run_id = (run_id or "").strip()
    if not run_id:
        return {
            "type": "cancel_run_result",
            "acknowledged": False,
            "error": "missing_run_id",
        }
    acknowledged = execution_registry.cancel(
        run_id, reason or "cancelled via cancel_run")
    frame = {
        "type": "cancel_run_result",
        "run_id": run_id,
        "acknowledged": acknowledged,
    }
    if not acknowledged:
        frame["error"] = "not_found"
    return frame


# ── Memory Panel frames (T-114, R-805) — الذاكرة ملك المستخدم ──
# نفس نمط _list_runs_frame/_cancel_run_frame (T-016): دوال وحدوية نقية
# تعيد dicts؛ الـ handler ينشر عبر sctx.send فقط. إطارات **إضافية** —
# لا مساس بأي إطار قائم. متسامحة: لا مخزن/لا مشروع ⇒ حقل error، لا رفع.


def _memory_project_id(project_root):
    """اشتقاق project_id من جذر المشروع — نفس هوية sessions/store."""
    if not project_root:
        return ""
    from sessions.store import project_fingerprint
    return project_fingerprint(str(project_root))


def _memory_list_frame(project_root, index=None):
    """T-114: ``memory_list_result`` — كل مدخلات ذاكرة المشروع.

    كل مدخلة: entry_id/kind/text/created_at/source/run_id (provenance
    كاملة) + ``stale`` عبر is_stale ضد الفهرس الحي (غياب أي بصمة =
    «لا حكم» ⇒ False — نفس دلالات core/project_memory).
    """
    frame: dict[str, Any] = {"type": "memory_list_result", "entries": []}
    project_id = _memory_project_id(project_root)
    if project_memory is None or not project_id:
        frame["error"] = "memory_unavailable"
        return frame
    frame["project_id"] = project_id
    try:
        entries = project_memory.entries(project_id)
    except CorruptMemoryError as e:
        frame["error"] = f"corrupt_memory: {e}"
        return frame
    for entry in entries:
        frame["entries"].append({
            "entry_id": entry.entry_id,
            "kind": entry.kind,
            "text": entry.text,
            "created_at": entry.created_at,
            "source": entry.source,
            "run_id": entry.run_id,
            "stale": _memory_is_stale(entry, index),
        })
    return frame


def _memory_edit_frame(project_root, entry_id, text=None, kind=None,
                       index=None):
    """T-114: ``memory_edit_result`` — تعديل يعاد فورًا للمخزن.

    provenance تصبح ``user`` (يفرضه المخزن)؛ الفهرس الحي يعيد ختم
    index_hash (تعديل المستخدم إعادة تأكيد ⇒ يمسح staleness عمدًا).
    """
    frame = {"type": "memory_edit_result", "acknowledged": False}
    project_id = _memory_project_id(project_root)
    if project_memory is None or not project_id:
        frame["error"] = "memory_unavailable"
        return frame
    entry_id = (entry_id or "").strip()
    if not entry_id:
        frame["error"] = "missing_entry_id"
        return frame
    frame["entry_id"] = entry_id
    try:
        updated = project_memory.edit(
            project_id, entry_id, text=text, kind=kind, index=index)
    except (ValueError, CorruptMemoryError) as e:
        frame["error"] = str(e)
        return frame
    if updated is None:
        frame["error"] = "not_found"
        return frame
    frame["acknowledged"] = True
    frame["entry"] = {
        "entry_id": updated.entry_id,
        "kind": updated.kind,
        "text": updated.text,
        "created_at": updated.created_at,
        "source": updated.source,
        "run_id": updated.run_id,
        "stale": _memory_is_stale(updated, index),
    }
    return frame


def _memory_delete_frame(project_root, entry_id):
    """T-114: ``memory_delete_result`` — حذف نهائي من المخزن.

    ContextEngine source يقرأ المخزن عند كل collect ⇒ المدخلة المحذوفة
    لا تظهر في أي bundle تالٍ فورًا (شرط القبول R-805).
    """
    frame = {"type": "memory_delete_result", "acknowledged": False}
    project_id = _memory_project_id(project_root)
    if project_memory is None or not project_id:
        frame["error"] = "memory_unavailable"
        return frame
    entry_id = (entry_id or "").strip()
    if not entry_id:
        frame["error"] = "missing_entry_id"
        return frame
    frame["entry_id"] = entry_id
    try:
        deleted = project_memory.delete(project_id, entry_id)
    except CorruptMemoryError as e:
        frame["error"] = str(e)
        return frame
    if not deleted:
        frame["error"] = "not_found"
        return frame
    frame["acknowledged"] = True
    return frame


# ── AppContext — Composition Root (T-006, R-102) ──
# Migration note: during R-102 the legacy module globals (fm, cmd_runner,
# provider, provider_pool, session_mgr, account_budget) remain assigned but
# are one-way ALIASES of the AppContext fields — both paths see identical
# objects. T-007 migrates consumers to resolve ctx.project.* at call time;
# T-008 deletes the private-attribute pokes and the dead aliases.
ctx: AppContext = None  # type: ignore[assignment]  # sentinel يُملأ في main (ADR-004)


def _active_provider():
    """R-102 (T-008): resolve the active provider at call time.

    Reads ctx.active_provider (single source of truth after switch_model);
    falls back to the legacy module global for ctx-less paths (tests).
    """
    if ctx is not None and ctx.active_provider is not None:
        return ctx.active_provider
    return provider


def _server_handle_factory(root: str) -> ProjectHandle:
    """T-007 (R-102): server flavor of the handle factory.

    Matches main()'s wiring (auto_approve=True) so ctx.switch_project()
    produces handles identical in behavior to the boot-time ones.

    T-049 (R-702): builds the ProjectIndex at project open, attaches its
    write-through hook to the FileManager, and fills the handle's
    ``index`` slot — per-message context queries hit the inverted index
    instead of walking the tree.
    """
    from context.index import ProjectIndex
    fm = FileManager(root)
    index = ProjectIndex(root)
    index.attach(fm)
    return ProjectHandle(
        root=root,
        fm=fm,
        cmd_runner=CommandRunner(cwd=root, auto_approve=True),
        index=index,
    )


def _build_ctx(project_path: str) -> AppContext:
    """Build the composition root from the already-constructed globals.

    Called by main() after wiring; kept as a separate function so tests can
    verify the aliasing (ctx.project.fm IS fm, etc.) without booting Flask.

    T-049 (R-702): the boot-time handle also gets a ProjectIndex attached
    to the (global) FileManager — same shape as _server_handle_factory.
    """
    from context.index import ProjectIndex
    _index = ProjectIndex(project_path)
    _index.attach(fm)
    return AppContext(
        project=ProjectHandle(root=project_path, fm=fm, cmd_runner=cmd_runner,
                              index=_index),
        provider_pool=provider_pool,
        session_manager=session_mgr,
        budget=account_budget,
        handle_factory=_server_handle_factory,
    )
chain_bridge: ChainBridge = None  # type: ignore[assignment]   # M5: جسر السلسلة → WebSocket
delegate_bridge: DelegateBridge = None  # type: ignore[assignment]  # M6: جسر التفويض

# ── Smart Request Pipeline (Phase 1-5) ──
provider_pool: ProviderPool = None  # type: ignore[assignment]          # إدارة مزودين متعددين
account_budget: AccountAwareBudget = None  # type: ignore[assignment]   # ميزانية واعية بالحسابات
capacity_model: CapacityModel = None  # type: ignore[assignment]        # سعة صادقة من pool+breakers (T-038)
request_router: RequestRouter = None  # type: ignore[assignment]        # توجيه ذكي للطلبات
action_applier: ActionApplier = None  # type: ignore[assignment]        # تطبيق نتائج Chain
orchestrator: SmartOrchestrator = None  # type: ignore[assignment]      # تحليل التعقيد
plugin_registry = None                       # T-102 (R-801): سجل الإضافات — يُملأ عند الإقلاع

# ── Agent System ──
agent_tools: AgentTools = None  # type: ignore[assignment]              # أدوات الـ Agent

# ── Project Memory (T-114, R-805) — نفس المخزن المحقون في AgentTools ──
# service global (نمط execution_registry): الـ handlers لا تلمسه مباشرة؛
# دوال الإطارات الوحدوية أدناه هي الوسيط الوحيد.
project_memory: ProjectMemoryStore = None  # type: ignore[assignment]

# ── ApprovalGate (T-012, R-104) — نقطة الموافقة الوحيدة قبل أي كتابة ──
approval_gate: ApprovalGate = None  # type: ignore[assignment]

# ── Run Metrics (TSK-610, PM-03 §R6) — تجميع مقاييس الـ runs ──
# service global (نفس نمط project_memory): مشترك على bus الرصد
# يُلحق سطر JSONL لكل run منتهٍ؛ REST القراءة أدناه هو الوسيط الوحيد.
run_metrics_store: RunMetricsStore = None  # type: ignore[assignment]


# ════════════════════════════════════════════════════
# Static Pages
# ════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ════════════════════════════════════════════════════
# API — Files
# ════════════════════════════════════════════════════
def _search_service():
    """TSK-501 (NF-20): خدمة البحث المشتركة فوق ProjectIndex.

    المسار الأساسي: فهرس المقبض الحي ``ctx.project.index`` (يُبنى عند
    فتح المشروع، طازج بخطافات write-through + refresh_if_stale).
    مسار ctx-less (اختبارات/تراث): فهرس كسول يُكاشى على كائن fm
    نفسه (لا حالة وحدوية جديدة) — نفس العمر: مشروع جديد = fm جديد.
    """
    from context.index import ProjectIndex
    from context.search import shared_search
    if ctx is not None and getattr(ctx.project, "index", None) is not None:
        return shared_search(ctx.project.index)
    index = getattr(fm, "_api_search_index", None)
    if index is None or pathlib.Path(index.root) != pathlib.Path(fm.root):
        index = ProjectIndex(fm.root)
        index.attach(fm)
        fm._api_search_index = index  # type: ignore[attr-defined]  # كاش ديناميكي متعمد (TSK-410)
    return shared_search(index)


# ════════════════════════════════════════════════════
# API — Terminal
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# API — Info
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# API — Rollback history (T-066, R-902) — قراءة فقط
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# API — Sessions
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# API — Backups
# ════════════════════════════════════════════════════
def _zip_member_violations(zf, root) -> list:
    """TSK-105 (NF-15): فحص أعضاء ZIP قبل الاستعادة — Zip-Slip guard.

    يعيد قائمة انتهاكات (اسم العضو + السبب). أي عضو:
    - مساره مطلق (أو drive-relative على Windows)، أو
    - يحلّ خارج ``root`` بعد التطبيع (أعضاء ``../``)، أو
    - symlink داخل الأرشيف (قد يوجَّه خارج الجذر بعد الفك)،
    = انتهاك. الرفض كامل (لا فك جزئي) — نفس دلالة الاحتواء في
    ``chain/path_policy.py:resolve_workspace_path``.
    """
    import pathlib as _pl
    violations = []
    root_resolved = _pl.Path(root).resolve()
    for info in zf.infolist():
        name = info.filename
        p = _pl.PurePosixPath(name.replace("\\", "/"))
        # مسار مطلق أو drive letter (نمط Windows داخل الأرشيف)
        if p.is_absolute() or (len(name) >= 2 and name[1] == ":"):
            violations.append({"member": name, "reason": "absolute_path"})
            continue
        # symlink داخل الأرشيف (external_attr: أعلى 16 بت = st_mode)
        mode = (info.external_attr >> 16) & 0xFFFF
        if (mode & 0o170000) == 0o120000:
            violations.append({"member": name, "reason": "symlink_member"})
            continue
        # الاحتواء بعد التطبيع — يمسك أعضاء ../
        target = (root_resolved / _pl.Path(*p.parts)).resolve()
        try:
            target.relative_to(root_resolved)
        except ValueError:
            violations.append({"member": name, "reason": "escapes_root"})
    return violations


# ════════════════════════════════════════════════════
# API — Model Switching
# ════════════════════════════════════════════════════
@app.route("/api/models")
def api_models():
    """قائمة المزودين والنماذج المتاحة"""
    providers_list = [
        {
            "id": "genspark",
            "name": "🌟 Genspark",
            "models": list(GENSPARK_MODELS.keys()),
        },
        {
            "id": "deepseek",
            "name": "🧠 DeepSeek",
            "models": ["deepseek-r1"],
        },
        {
            "id": "openai_shelby",
            "name": "⚡ OpenAI Shelby",
            "models": ["gpt-5-3-high", "gpt-5-3-mini", "gpt-5-3-pro"],
        },
        {
            "id": "alle_ai",
            "name": "🌐 Alle-AI",
            "models": ["gemini-3-1-pro", "nova-pro"],
        },
        {
            "id": "use_ai",
            "name": "🤖 Use.ai",
            "models": ["gateway-claude-sonnet-5", "gateway-claude-sonnet-4-6", "gateway-glm-5-2", "gateway-grok-4-3", "gateway-gpt-5-5"],
        },
    ]
    _prov = _active_provider()
    current = {
        "provider": getattr(_prov, 'name', 'unknown') if _prov else 'none',
        "model": _prov.config.model if _prov else '',
    }
    return jsonify({"ok": True, "providers": providers_list, "current": current})


@app.route("/api/switch-model", methods=["POST"])
def api_switch_model():
    """تغيير المزود/النموذج"""
    # R-102 (T-008): no `global` re-pointing — ctx.switch_model() is the
    # single publication; every runtime reader resolves _active_provider().
    # (The dead `provider` alias write was removed; pool/budget/router are
    # mutated through their public APIs, not reassigned.)

    # ── حماية: منع التبديل أثناء run نشط (R-101 → R-105) ──
    _active_runs = execution_registry.list_active()
    if _active_runs:
        return jsonify({
            "ok": False,
            "error": "لا يمكن تغيير المزود أثناء تشغيل run نشط",
            "chain_run_id": _active_runs[0].run_id
        }), 409

    data = request.get_json()
    prov_id = data.get("provider", "")
    model_name = data.get("model", "")

    if not prov_id or not model_name:
        return jsonify({"ok": False, "error": "المزود والنموذج مطلوبين"}), 400

    try:
        if prov_id == "genspark":
            cfg = GensparkConfig(model=model_name)
            provider = GensparkProvider(cfg)
        elif prov_id == "deepseek":
            cfg = DeepSeekConfig(model=model_name)
            provider = DeepSeekProvider(cfg)
        elif prov_id == "openai_shelby":
            cfg = OpenAIShelbyConfig(model=model_name)
            provider = OpenAIShelbyProvider(cfg)
        elif prov_id == "alle_ai":
            cfg = AlleAIConfig(model=model_name)
            provider = AlleAIProvider(cfg)
        elif prov_id == "use_ai":
            cfg = UseAIConfig(model=model_name, ws_timeout=90, accounts_dir=str(_DIR))
            provider = UseAIProvider(cfg)
        else:
            return jsonify({"ok": False, "error": f"مزود غير معروف: {prov_id}"}), 400

        provider.initialize()

        # ── R-102 (T-008): single atomic publication — no private pokes.
        # ChainBridge/DelegateBridge resolve ctx.active_provider at call
        # time; RequestRouter is updated through its public property.
        if ctx is not None:
            ctx.switch_model(provider)

        if provider_pool:
            provider_pool.add(prov_id, provider)
            provider_pool.active_name = prov_id

        if account_budget:
            account_budget.register(prov_id, provider)

        if request_router:
            request_router.active_provider_name = prov_id

        print(f"✅ تم التغيير: {prov_id} / {model_name}")
        return jsonify({
            "ok": True,
            "provider": prov_id,
            "model": model_name,
            "message": f"تم التغيير لـ: {prov_id} / {model_name}"
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _session_binding_policy() -> str:
    """R-303 (T-031): قراءة سياسة ربط الجلسة من config.yaml.

    ``session_binding.warn_only: true`` (الافتراضي) → "warn" دائمًا.
    ``warn_only: false`` → تُفعَّل ``session_binding.policy``
    (warn / fork / block). أي خطأ في القراءة → "warn" (أأمن سلوك).
    """
    try:
        _sb = _load_config().get("session_binding") or {}
        if not isinstance(_sb, dict):
            return "warn"
        if _sb.get("warn_only", True):
            return "warn"
        return str(_sb.get("policy", "warn"))
    except Exception:
        return "warn"


# ════════════════════════════════════════════════════
# WebSocket — AI Streaming
# ════════════════════════════════════════════════════
# ════════════════════════════════════════════════════
# REST Blueprints — TSK-613 (ADR-003)
# 25 route انتقلت إلى حزمة routes/ (أجسام حرفية)؛ تبقى هنا: index
# (app-level) + api_models/api_switch_model (provider-routing — خارج
# النطاق §0.8) والمساعدات المشتركة. كل blueprint يستلم كائن هذه
# الوحدة (sys.modules[__name__]) ويقرأ الحالة (fm/session_mgr/…)
# حيًّا وقت النداء — نفس دلالة globals الأصلية (late binding).
# ════════════════════════════════════════════════════
from routes import (  # noqa: E402  — بعد تعريف app (TSK-613)
    files as _routes_files,
    backups as _routes_backups,
    run as _routes_run,
    sessions as _routes_sessions,
    meta as _routes_meta,
    rollback as _routes_rollback,
    project as _routes_project,
)

_SERVER_MODULE = sys.modules[__name__]
for _routes_mod in (_routes_files, _routes_backups, _routes_run,
                    _routes_sessions, _routes_meta, _routes_rollback,
                    _routes_project):
    _routes_mod.register(app, _SERVER_MODULE)


def _build_session_context(ws):
    """T-048 (R-701): موقع التركيب — يبني SessionContext لاتصال WS جديد.

    هذا **ليس** handler: قراءات globals الوحدة هنا هي نقطة الربط
    الوحيدة المسموحة (بذر الحالة المشتركة وقت الاتصال) — بعدها كل
    وصول الـ handlers للحالة عبر sctx حصريًا (يفرضه
    scripts/lint_handler_state.py). قواعد نطاق الحالة كاملة في
    core/session_context.py.
    """
    bus = EventBus()
    adapter = _WSAdapter(ws, bus)
    project = None
    if ctx is not None:
        project = ctx.project
    elif fm is not None:
        project = ProjectHandle(root=str(fm.root), fm=fm,
                                cmd_runner=cmd_runner)
    return SessionContext(
        send=_frame_publisher(bus),
        ctx=ctx,
        bus=bus,
        adapter=adapter,
        project=project,
        chat_history=list(chat_history),
        session_mgr=session_mgr,
        chain_bridge=chain_bridge,
        delegate_bridge=delegate_bridge,
        provider_source=_active_provider,
        banner_source=lambda: _binding_banner,
    )


def _history_payload_policy(cfg: dict | None = None) -> WindowPolicy:
    """TSK-104 (NF-07): سياسة سقف تاريخ الحمولة من config.yaml.

    يقرأ ``history.payload_last_n``: عدد الرسائل الأخيرة التي تمر للموديل
    عند نقطة الإرسال. غياب المفتاح أو ``null`` = بلا سقف — الافتراضي
    متوافق سلوكيًا مع ما قبل TSK-104 (موثّق). أي قيمة غير صالحة ⇒
    سقوط متسامح على بلا سقف (لا يعطّل الرد أبدًا).
    """
    try:
        section = (cfg if cfg is not None else _read_config()).get("history") or {}
        last_n = section.get("payload_last_n")
        if last_n is None:
            return WindowPolicy()
        return WindowPolicy(last_n=int(last_n))
    except Exception:
        return WindowPolicy()


def _payload_history(sctx, cfg: dict | None = None) -> list:
    """TSK-104 (NF-07 — جزء الحمولة): تاريخ المحادثة المرسل للموديل.

    استبعاد بنيوي للرسالة الحالية (``[:-1]`` — تمر في الـ prompt نفسه)
    ثم سقف السياسة المسماة عبر ``select_history`` (لا قصّ خام — بوابة
    test_history_consumers). يُستهلك في مساري agent/direct كليهما.
    """
    return select_history(sctx.chat_history[:-1], _history_payload_policy(cfg))


#: TSK-607 (RP-03): وسم اقتطاع ظاهر لسياق التفويض — لا إسقاط صامت.
DELEGATE_DROP_MARKER_KEY = "__context_budget_drop_marker__"
_DELEGATE_DROP_MARKER = ("[⚠️ أُسقطت ملفات من سياق التفويض وفق ميزانية "
                         "السياق (context_budget) — الأكبر أولًا]")


def _budget_delegate_files(files_context: dict, cfg: dict | None = None,
                           budget=None) -> tuple[dict, list]:
    """TSK-607 (RP-03): سقف ContextBudget على ملفات سياق التفويض.

    كان معالج ``delegate_message`` يقرأ أول 10 ملفات **كاملة بلا سقف**
    ويمررها لـ DelegateBridge.write_brief الذي يُلحقها حرفيًا — آخر
    جيب برومبت خارج توحيد الميزانية (T-024/TSK-103). هنا: كل ملف
    BudgetItem بطبقة high (كامل-أو-إسقاط — لا قصّ منتصف؛ الأكبر أولًا
    عند الفيض)، وأي إسقاط يضيف وسمًا ظاهرًا داخل files_context
    (يظهر في البريف) — لا تدهور صامت. المشاريع الصغيرة: المحتوى
    يصل بايت-بايت كما كان (حفظ السلوك).

    نقية وحدويًا: ``(kept_dict, dropped_keys)`` — الترتيب الأصلي محفوظ.
    """
    if not files_context:
        return files_context, []
    from context.budget import BudgetItem, ContextBudget
    b = budget or ContextBudget.from_config(
        cfg if cfg is not None else _read_config())
    result = b.pack([BudgetItem(path, content, tier="high")
                     for path, content in files_context.items()])
    kept_keys = {it.key for it in result.kept}
    dropped = [d.key for d in result.dropped]
    kept = {path: content for path, content in files_context.items()
            if path in kept_keys}
    if dropped:
        kept[DELEGATE_DROP_MARKER_KEY] = (
            f"{_DELEGATE_DROP_MARKER}\nالمُسقط: {', '.join(dropped)}")
    return kept, dropped


def _parsed_to_actions(parsed) -> list[dict]:
    """TSK-601 (RP-01): تحويل ``ParsedResponse`` إلى قائمة actions للواجهة.

    استخراج للتحويل المكرر حرفيًا في مساري agent وdirect — ويستهلكه الآن
    مقبض ``delegate_approve`` أيضًا (كان ينادي دالتين غير موجودتين
    غير موجودتين في ResponseParser فيبتلع AttributeError ويرسل
    actions=[] دائمًا). لا API جديد — دالة وحدة خاصة.
    """
    actions: list[dict] = []
    for fb in parsed.files:
        actions.append({
            "action": "create_file",
            "path": fb.path,
            "content": fb.content,
            "language": fb.language,
        })
    for eb in parsed.edits:
        actions.append({
            "action": "edit_file",
            "path": eb.path,
            "old_text": eb.old_text,
            "new_text": eb.new_text,
        })
    for cb in parsed.commands:
        actions.append({
            "action": "run_command",
            "command": cb.command,
        })
    return actions


def _parsed_options(parsed) -> list[str]:
    """TSK-601: خيارات المتابعة من ``ParsedResponse`` (النمط المكرر ذاته)."""
    return [opt.text for opt in parsed.options] if hasattr(parsed, 'options') and parsed.options else []


def _dispatch_chat_message(ctx, sctx, user_text: str, mode: str, msg: dict, skip_path_detection: bool = False, attached_context: list | None = None):
    """إرسال ومعالجة رسالة الشات مع الـ AI (جمع السياق والتوجيه).

    TSK-612 (QG-02، ADR-002): الجسم في core/chat_dispatch.py؛ هذا
    الغلاف يرسل إشارة scan_start الفورية (TSK-403) ثم يبني ``deps``
    وقت النداء من رموز فضاء server (late binding — يحفظ monkeypatch
    الاختبارات وقراءة request_router/agent_tools المربوطين في main).

    TSK-103 (BUG-03): ``attached_context`` = قائمة ``(key, text)`` لمحتوى
    مرفق (مجلد attach من confirm_path_action) — يمر لـ
    gather_message_context ليُحزم تحت ContextBudget بدل الإلحاق الخام."""
    # TSK-403 (NF-12 / A3 — طلب المستخدم التاريخي): إشارة فورية قبل أي
    # عمل (كشف المسارات + بناء السياق قد يستغرقان ثواني) — أول إطار
    # مرئي كان "start" بعد اكتمال الجمع، فتبدو الواجهة صامتة. الواجهة
    # تعرض "جاري التفكير…" فور وصول هذا الإطار (≤200ms من الإرسال).
    sctx.send({"type": "scan_start"})
    deps = SimpleNamespace(
        RUNNERS=RUNNERS,
        MAX_SMART_FILE_SIZE=MAX_SMART_FILE_SIZE,
        parser=parser,
        event_bus=event_bus,
        request_router=request_router,
        agent_tools=agent_tools,
        # NF-25 (S69): كانا globals في الجسم الأصلي وسقطا من خريطة
        # حقن TSK-612 — استعادة دلالة ما قبل 612 (لقطة وقت النداء).
        provider_pool=provider_pool,
        approval_gate=approval_gate,
        gather_message_context=gather_message_context,
        store_pending_path_request=store_pending_path_request,
        _RunnerWSAdapter=_RunnerWSAdapter,
        _begin_run_ticket=_begin_run_ticket,
        _chain_runner_for_dispatch=_chain_runner_for_dispatch,
        _parsed_options=_parsed_options,
        _parsed_to_actions=_parsed_to_actions,
        _payload_history=_payload_history,
    )
    return dispatch_chat_message(deps, ctx, sctx, user_text, mode, msg,
                                 skip_path_detection, attached_context)

def _ws_ping(ctx, sctx, msg):
    # T-006 (R-102): ctx (composition root) is reachable in the WS
    # handler; extra field is ignored by the frontend.
    sctx.send({"type": "pong", "ctx": ctx is not None})
    return


# ── Agent: المستخدم وافق/رفض أمر terminal ──
def _ws_agent_approval_response(ctx, sctx, msg):
    if sctx.active_agent_loop:
        approved = msg.get("approved", False)
        approval_id = msg.get("approval_request_id", "")
        payload_hash = msg.get("payload_hash", "")
        sctx.active_agent_loop.approve_command(approved, approval_id, payload_hash)
    return


# ── Agent: إلغاء من المستخدم (T-041: كان يُلتقط داخل حلقة
# الاستطلاع المحذوفة — الآن يصل مباشرة لأن الـ Agent يعمل في
# thread عامل وحلقة WS الرئيسية حرة دائمًا) ──
def _ws_cancel_agent(ctx, sctx, msg):
    if sctx.active_agent_loop:
        sctx.active_agent_loop.cancel()
        print("    🛑 Agent cancelled by user")
    return


# ── معالجة قرار المسار: المستخدم اختار switch / attach / continue ──
def _ws_confirm_path_action(ctx, sctx, msg):
    req_id = msg.get("request_id", "")
    action = msg.get("action", "continue")  # switch | attach | continue
    req = pop_pending_path_request(req_id)
    if not req:
        sctx.send({"type": "confirm_path_failed",
                   "request_id": req_id,
                   "error": "طلب غير صالح أو انتهت صلاحيته."})
        return
    detected_path = req.get("path", "")
    user_text = req.get("user_text", "")
    mode = req.get("mode", "chat")
    orig_msg = req.get("msg", {})

    if action == "switch":
        try:
            sctx.switch_project(detected_path)
            scan = sctx.fm.scan_project()
            if sctx.session_mgr:
                sctx.session_mgr.update_project_path(detected_path)
            sctx.send({
                "type": "project_switched",
                "project": {
                    "root": str(sctx.fm.root),
                    "name": sctx.fm.root.name,
                    "total_files": scan["total_files"],
                    "total_size_kb": scan["total_size_kb"],
                }
            })
        except Exception as e:
            sctx.send({"type": "error", "text": f"فشل فتح المجلد: {e}"})
            return
    attached_context = []
    if action == "attach":
        # TSK-103 (BUG-03): لا إلحاق خام في user_text — كل ملف يدخل
        # attached_context كعنصر مستقل ليُحزم تحت ContextBudget.
        try:
            from chain.bridge import scan_folder_for_chain
            scanned_files = scan_folder_for_chain(detected_path)
            header = (f"[📂 سياق المجلد المرفق: {detected_path} "
                      f"({len(scanned_files)} ملفات)]")
            attached_context.append((f"attach_folder:{detected_path}", header))
            # TSK-404 (NF-18): كل محتوى ملف مرفق يدخل مسيّجًا
            # بأغلفة حدود صريحة — بيانات لا أوامر (تعليمة system).
            # NF-26 (S69): scan_folder_for_chain يرجع dict[str, str]
            # {rel_path: content} — تقطيع dict القديم كان يرمي
            # TypeError يبتلعه except أدناه (تدهور صامت بلا محتوى).
            for rel_p, content in list(scanned_files.items())[:15]:
                content_preview = (content or "")[:2000]
                attached_context.append((
                    f"attach_file:{rel_p}",
                    fence_attached(f"attach_file:{rel_p}",
                                   f"--- {rel_p} ---\n{content_preview}"),
                ))
        except Exception as e:
            print(f"⚠️ فشل إرفاق المجلد كسياق: {e}")

    # استئناف تنفيذ الرسالة للـ AI بعد اتخاذ القرار
    if user_text:
        _dispatch_chat_message(ctx, sctx, user_text, mode, orig_msg,
                               skip_path_detection=True,
                               attached_context=attached_context or None)
    return


# ── Chain: رد المستخدم على إطار chain_approval_request (T-012) ──
# السلسلة معلّقة في thread منفصل على gate.request — هذا يفكها.
def _ws_chain_approval_response(ctx, sctx, msg):
    if sctx.chain_bridge:
        matched = sctx.chain_bridge.resolve_approval(
            request_id=msg.get("request_id", ""),
            approved=msg.get("approved", False),
            payload_hash=msg.get("payload_hash", ""),
        )
        if not matched:
            print(f"⚠️ Chain approval غير مطابق: {msg.get('request_id', '')}")
    return


# ── Rollback (T-054, R-106): استعادة ملفات run مُطبَّق ──
# يتحقق hash الملف الحالي أولًا — تعديل خارجي ⇒ رفض بتقرير تعارض
# (success/partial/refused في إطار rollback_result).
def _ws_rollback(ctx, sctx, msg):
    msg_type = msg.get("type", "")
    run_id = str(msg.get("run_id", "")).strip()
    if not run_id:
        sctx.send({"type": "rollback_result", "status": "refused",
                   "run_id": "", "restored": [],
                   "conflicts": [{"path": "", "reason": "missing_run_id"}]})
        return
    bridge = sctx.chain_bridge
    if bridge is None:
        sctx.send({"type": "rollback_result", "status": "refused",
                   "run_id": run_id, "restored": [],
                   "conflicts": [{"path": "",
                                  "reason": "no_chain_bridge"}]})
        return
    mgr = bridge.checkpoint_manager
    if msg_type == "rollback_file":
        path = str(msg.get("path", "")).strip()
        if not path:
            sctx.send({"type": "rollback_result", "status": "refused",
                       "run_id": run_id, "restored": [],
                       "conflicts": [{"path": "",
                                      "reason": "missing_path"}]})
            return
        report = mgr.restore_file(run_id, path)
    else:
        report = mgr.restore_run(run_id)
    sctx.send({"type": "rollback_result", **report.to_dict()})
    return


def _ws_message(ctx, sctx, msg):
    user_text = msg.get("text", "").strip()
    mode = msg.get("mode", "chat")

    if not user_text:
        sctx.send({"type": "error", "text": "رسالة فارغة"})
        return

    _dispatch_chat_message(ctx, sctx, user_text, mode, msg, skip_path_detection=False)
    return


def _ws_apply_action(ctx, sctx, msg):
    # تطبيق إجراء محدد (مع باك-أب تلقائي)
    action = msg.get("action", {})
    result = _apply_single_action(action, sctx)
    sctx.send({"type": "action_result", **result})


def _ws_apply_batch(ctx, sctx, msg):
    # TSK-201 (NF-23.1): كان هنا بلوكان متطابقان بايت-بايت
    # (apply_all_actions / execute_plan) — دُمجا في _apply_batch
    # الواحدة. السلوك مقفول بالـ golden:
    # tests/goldens/apply_batch_frames.json
    # TSK-606 (RF-01/RP-02/UXF-03): النداء صار على خيط عامل — كان
    # متزامنًا على خيط حلقة استقبال WS فلا يُقرأ إطار cancel_run من
    # نفس الاتصال أثناء الدفعة أبدًا. _apply_batch نفسها بلا تغيير
    # (التذكرة + نقطة تفتيش الإلغاء موجودتان منذ TSK-304)؛ نمط
    # الخيوط نفسه المستعمل لـ chain/agent/delegate.
    threading.Thread(
        target=_apply_batch,
        args=(sctx, msg.get("actions", [])),
        daemon=True,
        name="runner-apply-batch",
    ).start()

# ═══════════════════════════════════════════
#  M5: Chain System — WebSocket Handlers
# ═══════════════════════════════════════════


def _ws_chain_message(ctx, sctx, msg):
    # تشغيل chain ذكي (بديل لـ message العادية للمهام المعقدة)
    user_text = msg.get("text", "").strip()
    if not user_text:
        sctx.send({"type": "error", "text": "رسالة فارغة"})
        return

    # TSK-403 (NF-12 / A3): مؤشر فوري هنا أيضًا — قراءة المجلد/الملفات
    # قبل أول إطار chain قد تستغرق ثواني ("كل الأوضاع" في Accept).
    sctx.send({"type": "scan_start"})

    force_strategy = msg.get("strategy", None)  # اختياري

    # تحضير المحتوى
    file_content = msg.get("file_content", None)
    file_path = msg.get("file_path", "")
    folder_path = msg.get("folder_path", "")  # مسار مجلد كامل
    files = msg.get("files", None)  # {path: content}

    # ── قراءة مجلد كامل ──
    if folder_path and os.path.isdir(folder_path):
        from chain.bridge import scan_folder_for_chain, get_folder_summary

        # ملخص أولاً
        summary = get_folder_summary(folder_path)
        sctx.send({
            "type": "folder_scanned",
            "folder": summary,
            "text": f"📂 تم مسح المجلد: {summary.get('name', '')} "
                    f"({summary.get('total_files', 0)} ملف، "
                    f"{summary.get('total_size_kb', 0)}KB)",
        })

        # قراءة المحتوى
        files = scan_folder_for_chain(folder_path)

        if not files:
            sctx.send({
                "type": "error",
                "text": "المجلد فاضي أو مفيش ملفات نصية قابلة للقراءة",
            })
            return

    # ── قراءة ملف واحد ──
    elif not file_content and file_path:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                file_content = f.read(MAX_SMART_FILE_SIZE)
        except Exception as e:
            # NF-14 §10 (يحتاج log — أضيف): فشل قراءة ملف الـ chain كان
            # صامتًا — الـ chain تكمل بلا محتوى لكن السبب يُسجّل.
            print(f"  ⚠️ فشل قراءة ملف للـ chain {file_path}: {e}")

    if not sctx.chain_bridge:
        sctx.send({"type": "error", "text": "Chain system غير مفعّل"})
        return

    # T-015 (R-105): registry ticket — single-run policy (لكل مشروع — TSK-302)
    chain_ticket = _begin_run_ticket(
        "chain",
        lambda m: sctx.send(m), sctx=sctx)
    if chain_ticket is None:
        return
    _ws_send = sctx.send

    run_id = sctx.chain_bridge.start_chain(
        ws_send_fn=_ws_send,
        user_request=user_text,
        file_content=file_content,
        file_path=file_path,
        files=files,
        force_strategy=force_strategy,
        ticket=chain_ticket,
    )

    if not run_id:
        # start_chain already sent error via _ws_send
        chain_ticket.finish("failed")


def _ws_chain_cancel(ctx, sctx, msg):
    # إلغاء chain نشط
    reason = msg.get("reason", "User cancelled")
    if sctx.chain_bridge:
        ok = sctx.chain_bridge.cancel(reason)
        if ok:
            # T-015 (R-105): ارفع علم الإلغاء على التذاكر النشطة —
            # التذكرة تُنهى بدقة في finally الخاص بالـ bridge
            for _t in execution_registry.list_active():
                _t.cancel(reason)
        sctx.send({
            "type": "chain_cancel_result",
            "ok": ok,
            "text": "تم إلغاء السلسلة" if ok else "مفيش سلسلة نشطة",
        })
    else:
        sctx.send({"type": "error", "text": "Chain system غير مفعّل"})


def _ws_chain_status(ctx, sctx, msg):
    # حالة chain النشط
    if sctx.chain_bridge:
        status = sctx.chain_bridge.get_status()
        sctx.send({"type": "chain_status", **status})
    else:
        sctx.send({"type": "chain_status", "active": False})


# ── T-044 (R-601): Crash Resume surface ──
def _ws_resume_scan(ctx, sctx, msg):
    # مسح runs_dir عن runs منقطعة قابلة للاستكمال
    if sctx.chain_bridge:
        sctx.send({
            "type": "resumable_runs",
            "runs": sctx.chain_bridge.list_resumable(),
        })
    else:
        sctx.send({"type": "resumable_runs", "runs": []})


def _ws_resume_run(ctx, sctx, msg):
    # استكمال run منقطع — تحقق انجراف البصمات قبل أي تنفيذ
    if not sctx.chain_bridge:
        sctx.send({"type": "error",
                            "text": "Chain system غير مفعّل"})
        return
    resume_id = msg.get("run_id", "").strip()
    if not resume_id:
        sctx.send({"type": "error", "text": "run_id مطلوب"})
        return
    resume_ticket = _begin_run_ticket(
        "chain",
        lambda m: sctx.send(m), sctx=sctx)
    if resume_ticket is None:
        return

    # TSK-608 (RF-02): مسار الاستكمال يرسل عبر الجسر مباشرة (لا يمر
    # بـ _RunnerWSAdapter) — غلاف نبض حياة حول الإرسال كي لا يُحصد
    # run مستأنَف حي (نفس دلالة نبضة-لكل-حدث في المحوّل).
    def _resume_send_with_heartbeat(m):
        resume_ticket.heartbeat()
        sctx.send(m)

    ok = sctx.chain_bridge.resume_run(
        resume_id, _resume_send_with_heartbeat, ticket=resume_ticket)
    if not ok:
        # الرفض/الخطأ أُرسل من الجسر — حرّر التذكرة
        resume_ticket.finish("failed")


def _ws_discard_run(ctx, sctx, msg):
    # حذف حالة run منقطع نهائيًا
    if not sctx.chain_bridge:
        sctx.send({"type": "error",
                            "text": "Chain system غير مفعّل"})
        return
    discard_id = msg.get("run_id", "").strip()
    ok = sctx.chain_bridge.discard_run(discard_id)
    sctx.send({
        "type": "discard_result",
        "run_id": discard_id,
        "ok": ok,
        "text": ("🗑️ حُذفت حالة الـ run" if ok
                 else "⚠️ لا يوجد run بهذا المعرّف"),
    })


# ── T-016 (R-105): Registry control surface ──
def _ws_list_runs(ctx, sctx, msg):
    # كل الـ runs التي يعرفها السجل (نشطة ومنتهية) — id/mode/state/started_at
    sctx.send(_list_runs_frame())


def _ws_cancel_run(ctx, sctx, msg):
    # إلغاء تعاوني لـ run محدد بمعرّفه — acknowledged / not_found
    # TSK-606 (اكتشاف جانبي BUG): كان النداء يمرر ensure_ascii=False
    # لكن توقيع sctx.send هو Callable[[dict], None] — TypeError عند
    # أول cancel_run حقيقي عبر WS (الاختبارات كانت تنادي
    # _cancel_run_frame مباشرة فلم تكشفه). أُزيل الوسيط الدخيل.
    sctx.send(
        _cancel_run_frame(msg.get("run_id", ""), msg.get("reason", "")),
    )


# ── M6: Delegate System ──
def _ws_delegate_message(ctx, sctx, msg):
    # تفويض مهمة معقدة
    user_text = msg.get("text", "").strip()
    if not user_text:
        sctx.send({"type": "error", "text": "الرسالة فارغة"})
        return

    if not sctx.delegate_bridge:
        sctx.delegate_bridge = DelegateBridge(sctx.active_provider(), ctx=ctx)

    # جمع ملفات السياق
    files_context = {}
    try:
        scan = sctx.fm.scan_project()
        for f in scan.get("files", [])[:10]:
            try:
                content = sctx.fm.read_file(f["path"])
                files_context[f["path"]] = content
            except Exception:
                # NF-14 §11 (ابتلاع مقصود): ملف سياق غير مقروء — التفويض
                # يكمل ببقية الملفات (إثراء اختياري).
                pass
    except Exception as e:
        # NF-14 §12 (يحتاج log — أضيف): فشل scan المشروع كله كان صامتًا.
        print(f"  ⚠️ فشل جمع سياق التفويض: {e}")

    # TSK-607 (RP-03): سقف الميزانية على ملفات السياق — كانت تمر
    # كاملة بلا سقف (آخر جيب خارج توحيد T-024/TSK-103). أي إسقاط
    # موسوم داخل البريف + مرصود في اللوج.
    files_context, _dropped_delegate = _budget_delegate_files(
        files_context)
    if _dropped_delegate:
        print(f"  ⚖️ ContextBudget (delegate): أُسقط: {_dropped_delegate}")

    project_context = ""
    try:
        project_context = sctx.fm.get_project_context()
    except Exception:
        # NF-14 §13 (ابتلاع مقصود): سياق المشروع إثراء اختياري للتفويض.
        pass

    # T-041 (R-501): نفس مسار الإرسال الموحّد — DelegateRunner فوق
    # الجسر (كان النداء المباشر هنا بلا تذكرة — الآن التفويض من هذا
    # المدخل أيضًا تحت سياسة الـ run الواحد وقابل للإلغاء).
    delegate_msg_ticket = _begin_run_ticket("delegate", sctx.send,
                                            sctx=sctx)
    if delegate_msg_ticket is None:
        return

    threading.Thread(
        target=RUNNERS["delegate"](bridge=sctx.delegate_bridge).run,
        args=(
            RunRequest(
                mode="delegate",
                message=user_text,
                context={
                    "files": files_context,
                    "project_context": project_context,
                },
            ),
            delegate_msg_ticket,
            _RunnerWSAdapter(sctx.send),
        ),
        daemon=True,
        name=f"runner-delegate-{delegate_msg_ticket.run_id}",
    ).start()


def _ws_delegate_approve(ctx, sctx, msg):
    # المستخدم وافق على التعديلات
    if sctx.delegate_bridge and sctx.delegate_bridge.is_active:
        def approval_handler(et, ed):
            try:
                sctx.send({"type": et, **ed})
            except Exception:
                # NF-14 §14 (ابتلاع مقصود): WS مقفول أثناء حدث اعتماد —
                # نفس سياسة §3 (الإرسال لا يعطل الهبوط).
                pass

        landed = sctx.delegate_bridge.land(on_event=approval_handler)
        if landed and sctx.delegate_bridge.current_run:
            # أرسل الرد للمعالجة العادية
            run = sctx.delegate_bridge.current_run
            if run.result:
                sctx.send({
                    "type": "start",
                })
                sctx.send({
                    "type": "chunk",
                    "text": run.result.response,
                })
                # تحليل الأكشنز — TSK-601 (RP-01): كان النداء هنا لدالتين
                # غير موجودتين في ResponseParser فيُبتلع
                # AttributeError ⇒ actions=[] دائمًا. الآن: parse() الحقيقية
                # + التحويل المشترك، وفشل التحويل يُظهَر للمستخدم (UXF-02).
                try:
                    parsed = parser.parse(run.result.response)
                    actions = _parsed_to_actions(parsed)
                    options = _parsed_options(parsed)
                    sctx.send({
                        "type": "done",
                        "actions": actions,
                        "options": options,
                        "summary": f"✅ تم اعتماد التعديلات (delegation #{run.run_id})",
                    })
                except Exception as e:
                    # TSK-601: الفشل لم يعد صامتًا (NF-14 §15 كان log فقط) —
                    # إطار error يصل الواجهة قبل fallback الـ done الفارغ.
                    print(f"  ⚠️ فشل تحليل رد التفويض بعد الاعتماد: {e}")
                    sctx.send({
                        "type": "error",
                        "text": f"تعذّر تحويل رد التفويض إلى إجراءات: {e}",
                    })
                    sctx.send({
                        "type": "done",
                        "actions": [],
                        "options": [],
                        "summary": f"✅ تم اعتماد التعديلات",
                    })
    else:
        sctx.send({"type": "error", "text": "لا يوجد تفويض نشط"})


def _ws_delegate_reject(ctx, sctx, msg):
    # المستخدم رفض التعديلات
    reason = msg.get("reason", "")
    if sctx.delegate_bridge and sctx.delegate_bridge.is_active:
        sctx.delegate_bridge.reject(reason, on_event=lambda et, ed: sctx.send(
            {"type": et, **ed}
        ))
    else:
        sctx.send({"type": "error", "text": "لا يوجد تفويض نشط"})


# ── Memory Panel (T-114, R-805) — إطارات إضافية عبر الوسطاء الوحدويين ──
def _ws_memory_list(ctx, sctx, msg):
    _root = sctx.project.root if sctx.project else None
    _index = sctx.project.index if sctx.project else None
    sctx.send(_memory_list_frame(_root, _index))


def _ws_memory_edit(ctx, sctx, msg):
    _root = sctx.project.root if sctx.project else None
    _index = sctx.project.index if sctx.project else None
    sctx.send(_memory_edit_frame(
        _root, msg.get("entry_id", ""),
        text=msg.get("text"), kind=msg.get("kind"), index=_index))


def _ws_memory_delete(ctx, sctx, msg):
    _root = sctx.project.root if sctx.project else None
    sctx.send(_memory_delete_frame(_root, msg.get("entry_id", "")))


# TSK-611 (ADR-001): جدول dispatch — التوجيه كبيانات؛ الأنواع المركّبة
# مفتاحان لنفس المقبض. يُمرَّر إلى core.ws_router.dispatch.
WS_HANDLERS = {
    "ping": _ws_ping,
    "agent_approval_response": _ws_agent_approval_response,
    "cancel_agent": _ws_cancel_agent,
    "confirm_path_action": _ws_confirm_path_action,
    "chain_approval_response": _ws_chain_approval_response,
    "rollback_run": _ws_rollback,
    "rollback_file": _ws_rollback,
    "message": _ws_message,
    "apply_action": _ws_apply_action,
    "apply_all_actions": _ws_apply_batch,
    "execute_plan": _ws_apply_batch,
    "chain_message": _ws_chain_message,
    "chain_cancel": _ws_chain_cancel,
    "chain_status": _ws_chain_status,
    "resume_scan": _ws_resume_scan,
    "resume_run": _ws_resume_run,
    "discard_run": _ws_discard_run,
    "list_runs": _ws_list_runs,
    "cancel_run": _ws_cancel_run,
    "delegate_message": _ws_delegate_message,
    "delegate_approve": _ws_delegate_approve,
    "delegate_reject": _ws_delegate_reject,
    "memory_list": _ws_memory_list,
    "memory_edit": _ws_memory_edit,
    "memory_delete": _ws_memory_delete,
}


def _handle_ws_message(ctx, sctx, msg):
    """T-048 (R-701): معالجة رسالة WS واحدة — كل حالة المحادثة عبر sctx.

    TSK-611 (QG-01، ADR-001): التوجيه صار جدول dispatch (WS_HANDLERS
    أعلاه + core/ws_router.py)؛ المقابض ``_ws_*`` أدناه/أعلاه تبقى
    مؤقتًا في server.py (نقلها موضوع QG-02..04). نوع مجهول = no-op
    صامت (سلوك السلسلة الأصلية محفوظ). ممنوع ``global`` وأي كتابة
    حالة محادثة وحدوية في المقابض — تفرضه بوابة
    scripts/lint_handler_state.py في check.sh.
    """
    ws_dispatch(WS_HANDLERS, ctx, sctx, msg)


def ws_handler(ws):
    """WebSocket للتواصل الحي مع AI — T-048: الحالة في SessionContext."""
    sctx = _build_session_context(ws)
    try:
        while True:
            try:
                raw = ws.receive()
                if not raw:
                    break
                data = json.loads(raw)
            except Exception:
                # NF-14 §16 (ابتلاع مقصود): انقطاع WS/إطار تالف — إنهاء
                # الحلقة هو السلوك الصحيح (التنظيف في finally).
                break
            _handle_ws_message(ctx, sctx, data)
    finally:
        # ── WebSocket Disconnected Cleanup (T-048: idempotent عبر sctx) ──
        print("🔌 WebSocket disconnected. Cleaning up and cancelling active tasks...")
        sctx.close()



# Explicit registration (T-006): flask-sock's decorator returns None, which
# would erase the module-level name and make the handler untestable. Register
# without the decorator so `server.ws_handler` stays a plain callable.
sock.route("/ws")(ws_handler)


# TSK-203 (NF-23.2): التعريف المكرر لـ MAX_SMART_FILE_SIZE أُزيل —
# التعريف الوحيد أعلى الملف (قسم Globals).
def _apply_batch(sctx, actions: list) -> None:
    """TSK-201 (NF-23.1): المسار الموحّد لتطبيق دفعة إجراءات.

    يحل محل البلوكين المتطابقين apply_all_actions / execute_plan.
    السلوك (الإطارات المُرسلة، الترتيب، رسائل الفشل، إعادة ضبط علم
    الباك-أب) مقفول بالـ golden: tests/goldens/apply_batch_frames.json.

    TSK-304 (NF-04) — الدفعة مُخيّطة الآن تحت تذكرة run (kind
    ``apply``) مع نقطة تفتيش إلغاء بين كل action: طلب ``cancel_run``
    أثناء دفعة طويلة (مثلا 20 ملفًا) يوقفها قبل اكتمالها — لا تُطبّق
    الإجراءات المتبقية. مسارا النجاح/الفشل يرسلان نفس الإطارات
    المقفولة بالـ golden بلا تغيير؛ مسار الإلغاء فقط يضيف إطار
    ``error`` توضيحيًا قبل ``all_actions_done``. التذكرة تُنهى دائمًا
    (finally) بالحالة المطابقة: completed / failed / cancelled.
    """
    # TSK-304 (NF-04): تخييط الدفعة تحت ticket — يجعلها مرئية لـ
    # list_runs وقابلة للإلغاء عبر cancel_run (إلغاء تعاوني).
    apply_ticket = _begin_run_ticket("apply", sctx.send, sctx=sctx)
    if apply_ticket is None:
        return  # busy frame أُرسل بالفعل — نفس سياسة بقية الـ runs
    ticket_status = "completed"
    try:
        sctx.backup_done_for_batch = False
        total = len(actions)
        for i, action in enumerate(actions):
            # TSK-304 (NF-04): نقطة تفتيش الإلغاء بين كل action —
            # الإجراءات المتبقية لا تُطبّق بعد رفع العلم.
            # TSK-608 (RF-02): نبضة لكل action — دفعة طويلة حية لا تُحصد.
            apply_ticket.heartbeat()
            if apply_ticket.is_cancelled:
                ticket_status = "cancelled"
                sctx.send({
                    "type": "error",
                    "text": (f"⛔ أُلغيت الدفعة عند الخطوة {i+1}/{total}: "
                             f"{apply_ticket.cancel_reason or 'إلغاء المستخدم'}"),
                })
                break
            sctx.send({"type": "task_progress", "current": i + 1, "total": total, "action": action, "status": "running"})
            result = _apply_single_action(action, sctx)
            sctx.send({"type": "task_progress", "current": i + 1, "total": total, "action": action,
                       "status": "done" if result["ok"] else "error", "message": result.get("message", "")})
            if not result["ok"]:
                ticket_status = "failed"
                sctx.send({"type": "error", "text": f"فشل في الخطوة {i+1}: {result.get('message', '')}"})
                break
        sctx.backup_done_for_batch = False
        sctx.send({"type": "all_actions_done", "total": total})
    finally:
        apply_ticket.finish(ticket_status)


def _apply_single_action(action: dict, sctx) -> dict:
    """تطبيق إجراء واحد — مع باك-أب إلزامي قبل أي تعديل.

    T-048 (R-701): يعمل على مشروع الاتصال (sctx.fm/cmd_runner) وعلم
    الباك-أب لكل اتصال — لا حالة وحدوية.
    """
    act_type = action.get("action", "")

    try:
        # باك-أب كامل قبل أول تعديل في الـ batch
        if not sctx.backup_done_for_batch and act_type in ("create_file", "edit_file"):
            try:
                backup_path = sctx.fm.create_full_backup()
                sctx.backup_done_for_batch = True
                if backup_path:
                    print(f"🛡️ Full backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup warning: {e}")
                sctx.backup_done_for_batch = True  # لا نوقف التنفيذ بسبب فشل الباك-أب

        if act_type == "create_file":
            path = action["path"]
            content = action["content"]
            saved = sctx.fm.write_file(path, content)
            return {"ok": True, "message": f"تم حفظ: {saved}"}

        elif act_type == "edit_file":
            path = action["path"]
            sctx.fm.edit_file(path, action["old_text"], action["new_text"])
            return {"ok": True, "message": f"تم تعديل: {path}"}

        elif act_type == "run_command":
            # TSK-502 (NF-16): نفس راية إلزام الموافقة — مسار apply-actions.
            result = sctx.cmd_runner.run(
                action["command"], need_approval=False,
                force_approval=_force_command_approval())
            return {"ok": result["success"], "message": result["output"] or result["error"]}

        return {"ok": False, "message": f"إجراء غير معروف: {act_type}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════
# TSK-203 (NF-23.3): تعريف _read_config انتقل أعلى الملف كـ alias
# للقارئ الموحّد المُكاش _load_config (قرب تعريف _DIR).
def _resolve_default_provider(cli_model, cfg):
    """T-051 (R-703): حل (مزود، موديل) الإقلاع — **config يفوز**.

    الأولوية (من الأعلى):
    1. ``--model prov:model`` الصريح — نية المستخدم المباشرة.
    2. ``--model model`` بلا مزود — الموديل للمزود الافتراضي **من
       config** (كان hardcoded "genspark" — التناقض الذي أزاله T-051).
    3. بلا ``--model``: المزود = ``config.default_provider``، والموديل =
       ``config.providers.<id>.model`` إن وُجد وإلا None (افتراضي صنف
       المزود نفسه — مصدر واحد للقيمة، لا نسخة ثانية هنا).
    4. config غير مقروء/بلا default_provider: "use_ai" — مرآة قيمة
       config.yaml المشحونة (ملاذ أخير للإقلاع فقط، ليس تفضيلًا).

    يعيد (prov_id: str, model_name: str | None).
    """
    cfg = cfg or {}
    cfg_provider = str(cfg.get("default_provider") or "use_ai")

    if cli_model:
        if ":" in cli_model:
            prov_id, model_name = cli_model.split(":", 1)
            return prov_id, model_name
        return cfg_provider, cli_model

    providers_cfg = cfg.get("providers") or {}
    section = providers_cfg.get(cfg_provider) or {}
    model_name = section.get("model") or None
    return cfg_provider, model_name


def main():
    global fm, cmd_runner, provider, session_mgr, chain_bridge, ctx
    global provider_pool, account_budget, request_router, action_applier, orchestrator
    global capacity_model
    global agent_tools
    global project_memory
    global run_metrics_store

    arg_parser = argparse.ArgumentParser(description="WebDev AI Editor — Web Server")
    arg_parser.add_argument("--project", "-p", type=str, default=".",
                            help="مسار المشروع")
    arg_parser.add_argument("--port", type=int, default=5000,
                            help="منفذ السيرفر")
    arg_parser.add_argument("--host", type=str, default="127.0.0.1",
                            help="عنوان السيرفر")
    arg_parser.add_argument("--model", "-m", type=str, default=None)
    arg_parser.add_argument("--debug", action="store_true")
    args = arg_parser.parse_args()

    # مسار المشروع
    project_path = os.path.abspath(args.project)
    if not os.path.isdir(project_path):
        os.makedirs(project_path, exist_ok=True)
        print(f"📁 تم إنشاء مجلد المشروع: {project_path}")

    fm = FileManager(project_path)
    cmd_runner = CommandRunner(cwd=project_path, auto_approve=True)

    # إعداد مدير الجلسات
    sessions_dir = str(_DIR / "sessions")
    session_mgr = SessionManager(sessions_dir)

    # استعادة آخر جلسة أو بدء جلسة جديدة
    existing = session_mgr.list_sessions()
    if existing:
        latest = existing[0]
        session_mgr.load_session(latest["id"])
        print(f"📋 تم استعادة الجلسة: {latest['id']} ({latest['message_count']} رسالة)")
        # استعادة الـ chat_history
        global chat_history
        msgs = session_mgr.get_current_messages()
        chat_history = [Message(role=m["role"], content=m["content"]) for m in msgs]
    else:
        session_mgr.new_session(project_path)
        print("📋 تم بدء جلسة جديدة")

    # تسجيل كل المزودين
    register_provider("use_ai", UseAIProvider)
    register_provider("genspark", GensparkProvider)
    register_provider("deepseek", DeepSeekProvider)
    register_provider("alle_ai", AlleAIProvider)

    # المزود الافتراضي — T-051 (R-703): **config يفوز**. الـ hardcode
    # القديم ("genspark:claude-sonnet-5") كان يناقض config.yaml — محذوف.
    prov_id, model_name = _resolve_default_provider(args.model, _read_config())

    _model_kw = {"model": model_name} if model_name else {}
    if prov_id == "genspark":
        provider_config = GensparkConfig(**_model_kw)
        provider = GensparkProvider(provider_config)
    elif prov_id == "deepseek":
        provider_config = DeepSeekConfig(**_model_kw)
        provider = DeepSeekProvider(provider_config)
    elif prov_id == "alle_ai":
        provider_config = AlleAIConfig(**_model_kw)
        provider = AlleAIProvider(provider_config)
    else:
        provider_config = UseAIConfig(
            ws_timeout=90,
            accounts_dir=str(_DIR),
            **_model_kw,
        )
        provider = UseAIProvider(provider_config)

    provider.initialize()

    # ── AppContext (T-006/T-007, R-102) — composition root, built BEFORE
    # consumers so they resolve ctx.project.* at call time (never caching).
    # provider_pool/budget fields are attached below once constructed.
    ctx = _build_ctx(project_path)
    ctx.switch_model(provider)

    # ── ApprovalGate (T-012, R-104) ──
    # auto_execute:false (الافتراضي) ⇒ interactive — كل كتابة تحتاج موافقة صريحة.
    # auto_execute:true ⇒ auto مع whitelist لأنواع السلسلة (write/edit/command)
    # — إعادة للسلوك القديم لكن بقرار مسجّل ومن مسار النجاح فقط (لا finally).
    _auto_execute = False
    try:
        _auto_execute = bool(_load_config().get("auto_execute", False))
    except Exception:
        # NF-14 §17 (ابتلاع مقصود): config غير مقروء → الوضع التفاعلي الآمن.
        pass
    global approval_gate
    approval_gate = ApprovalGate(
        mode="auto" if _auto_execute else "interactive",
        auto_whitelist={"write", "edit", "command"} if _auto_execute else None,
        timeout_seconds=120.0,
    )
    print(f"  🛡️ ApprovalGate: {approval_gate.mode}")

    # ── Strategy Plugins (T-102, R-801) ──
    # تحميل واحد عند الإقلاع؛ المحجورون يُسجَّلون ويُعرَضون — المضيف
    # يقلع دائمًا (بوابة التحقق في chain/plugin_registry.py تعزل أي فشل).
    from chain.plugin_registry import StrategyPluginRegistry
    global plugin_registry
    plugin_registry = StrategyPluginRegistry()
    plugin_registry.discover()
    if plugin_registry.loaded:
        print(f"  🧩 Strategy plugins: {', '.join(sorted(plugin_registry.loaded))}")
    for _q in plugin_registry.quarantined:
        print(f"  ⚠️ Plugin quarantined: {_q.name} [{_q.stage}] {_q.reason}")

    # ── Planner seam (T-106/T-107, R-803) ──
    # اختيار المخطِّط من مفتاح ``planner:`` في config — تحقق صارم
    # (اسم مجهول = فشل إقلاع صاخب، نفس فلسفة routing_config)؛ مفتاح
    # غائب = heuristic. T-107: llm/hybrid يستهلكان المزود النشط —
    # التبديل بينها = تعديل config فقط، صفر تعديل كود (بند القبول).
    from chain.planner import planner_from_config
    _planner_cfg = _load_config().get("planner")
    chain_planner = planner_from_config(
        _planner_cfg,
        SmartOrchestrator(plugin_registry=plugin_registry),
        provider=provider)
    print(f"  🧭 Planner: {chain_planner.name}")
    # T-108 (R-804): بانر backend — الاختيار تم عند تحميل الوحدة
    # (الدرزة أعلى الملف)؛ هنا الإفصاح عند الإقلاع فقط.
    print(f"  🗄 Backend: {_backends.name}")
    # T-110 (R-804): بانر dispatch — in-proc افتراضيًّا؛ worker يتطلب
    # Redis + عامل يعمل (docs/worker_runbook.md).
    print(f"  📮 Dispatch: {_dispatch_mode}")

    # ── Chain Bridge (M5) ──
    chain_bridge = ChainBridge(
        provider=provider,
        project_root=project_path,
        approval_gate=approval_gate,
        ctx=ctx,
        plugin_registry=plugin_registry,
        planner=chain_planner,
    )
    print(f"  🔗 Chain System: active")

    # ── Crash-resume startup scan (T-044, R-601) ──
    # يفحص runs_dir عن runs منقطعة (state.json بحالة غير نهائية) —
    # إعلام فقط عند الإقلاع؛ القرار (resume_run/discard_run) عبر WS.
    try:
        _resumable = chain_bridge.list_resumable()
        if _resumable:
            print(f"  ♻️ Resumable runs: {len(_resumable)} — "
                  + ", ".join(
                      f"{r['run_id']} ({r['steps_done']}/{r['steps_total']})"
                      for r in _resumable[:5]))
            print("     استخدم resume_run / discard_run من الواجهة (WS).")
    except Exception as _exc:
        print(f"  ⚠️ Resume scan skipped: {_exc}")

    # ── Retention GC pass (T-033, R-305) ──
    # مسح artifacts الـ runs عند الإقلاع حسب config.retention —
    # dry-run افتراضيًّا (تسجيل فقط، لا حذف) حتى يفعّله المستخدم.
    try:
        from sessions.retention import policy_from_config, sweep
        _retention_cfg = _load_config().get("retention")
        _rp = policy_from_config(_retention_cfg)
        if project_path:
            _report = sweep(pathlib.Path(project_path) / ".ai_runs", _rp,
                            log=print)
            _mode = "dry-run" if _report.dry_run else "live"
            print(f"  🧹 Retention ({_mode}): "
                  f"{len(_report.kept)} باقٍ / {len(_report.deleted)} "
                  f"{'مرشح للحذف' if _report.dry_run else 'محذوف'}")
            # T-054 (R-106): تقليم checkpoints بنفس سياسة الـ sweep —
            # الـ runs الناجية تُبقي checkpoints-ها؛ المحذوفة تُقلَّم
            # (log + blob GC). في dry-run لا تقليم (نفس أمان الـ sweep).
            if not _report.dry_run:
                from core.checkpoint import CheckpointManager as _CkptMgr
                _ck = _CkptMgr(pathlib.Path(project_path) / ".ai_runs"
                               / "checkpoints")
                _pruned = _ck.prune(set(_report.kept))
                if _pruned:
                    print(f"  🧹 Checkpoints: {_pruned} run مُقلَّم")
    except Exception as _exc:
        print(f"  ⚠️ Retention sweep skipped: {_exc}")

    # ── Smart Request Pipeline ──
    provider_pool = ProviderPool()
    provider_pool.add(prov_id, provider)
    # تسجيل المزودين الآخرين كـ fallback (يتم تهيئتهم عند الحاجة)
    _fallback_providers = {
        "genspark": (GensparkProvider, GensparkConfig),
        "deepseek": (DeepSeekProvider, DeepSeekConfig),
        "use_ai": (UseAIProvider, UseAIConfig),
        "alle_ai": (AlleAIProvider, AlleAIConfig),
    }
    for fb_name, (fb_cls, fb_cfg_cls) in _fallback_providers.items():
        if fb_name != prov_id:
            try:
                fb_provider = fb_cls(fb_cfg_cls())
                fb_provider.initialize()
                provider_pool.add(fb_name, fb_provider)
            except Exception:
                # NF-14 §18 (ابتلاع مقصود): مزود احتياطي فشل تهيئته — غير حرج.
                pass

    account_budget = AccountAwareBudget(provider_pool.all_providers)
    # T-102: نفس سجل الإضافات المُحمَّل عند الإقلاع (لا اكتشاف ثانٍ).
    orchestrator = SmartOrchestrator(plugin_registry=plugin_registry)
    # T-036 (R-402): عتبات التوجيه من config.routing — صاخبة على schema
    # مكسورة (لا نبتلع الخطأ: عتبات خاطئة صامتة أسوأ من فشل إقلاع واضح)؛
    # قسم مفقود فقط = الافتراضات التاريخية.
    from chain.routing_config import thresholds_from_config
    _routing_cfg = _load_config().get("routing")
    routing_thresholds = thresholds_from_config(_routing_cfg)
    request_router = RequestRouter(
        orchestrator=orchestrator,
        budget=account_budget,
        active_provider_name=prov_id,
        thresholds=routing_thresholds,
    )
    ctx.provider_pool = provider_pool
    ctx.budget = account_budget
    action_applier = ActionApplier(
        parser=parser,
        file_manager=fm,
        command_runner=cmd_runner,
        ctx=ctx,
    )
    if chain_bridge:
        chain_bridge.action_applier = action_applier
    print(f"  🧠 Smart Router: active ({len(provider_pool.names)} providers)")
    # T-038 (R-403): أرقام السعة من CapacityModel — قابلة للتتبع لحالة
    # pool/breaker، والتخمينات مُعلّمة بدل تقديمها كحقائق.
    capacity_model = CapacityModel(provider_pool)
    _cap = capacity_model.report()
    _est = " (تقديري)" if _cap.estimated else ""
    print(f"  💰 Capacity: {_cap.total_available} calls · "
          f"{_cap.healthy_count} healthy providers{_est}")

    # ── Agent Tools ──
    # T-058 (R-504): سياسة أوامر الـ agent من config.yaml — الـ allowlist
    # ملكية المشروع لا الـ agent؛ قسم غائب = وضع legacy (بوابة الموافقة فقط).
    _cmd_policy = command_policy_from(_read_config())
    # T-112 (R-805): ذاكرة المشاريع الدائمة — مخزن JSONL لكل project_id
    # تحت projects/ بجانب sessions/ (نفس جذر بيانات التطبيق).
    # T-114: صار service global — إطارات لوحة الذاكرة تصل له عبر
    # الوسطاء الوحدويين (_memory_*_frame)؛ نفس الكائن محقون في AgentTools.
    project_memory = ProjectMemoryStore(str(_DIR / "projects"))
    # TSK-610 (PM-03): مخزن مقاييس الـ runs + مشترك التجميع على
    # bus الرصد — إضافة صرفة (الـ bus يعزل أعطال المشتركين؛ فشل
    # الكتابة لا يمس الـ run — قرار موثّق في §TSK-610).
    run_metrics_store = RunMetricsStore(str(_DIR / "metrics" / "runs.jsonl"))
    event_bus.subscribe(RunMetricsRecorder(run_metrics_store))
    print("  📈 Run Metrics: مفعّل — metrics/runs.jsonl")
    agent_tools = AgentTools(
        file_manager=fm,
        command_runner=cmd_runner,
        project_root=project_path,
        ctx=ctx,
        command_policy=_cmd_policy,
        # T-059 (R-106): كتابات الأوامر الجانبية تُلتقط في نفس مخزن
        # checkpoints الذي يخدم كتابات السلسلة (T-054) — مسار استعادة واحد.
        checkpoint=chain_bridge.checkpoint_manager,
        # T-112 (R-805): أداة remember_fact تكتب هنا — provenance كاملة.
        memory_store=project_memory,
    )
    if _cmd_policy.enforce:
        print(f"  🤖 Agent System: active "
              f"(allowlist: {len(_cmd_policy.allowlist)} أمر)")
    else:
        print("  🤖 Agent System: active (allowlist: legacy/off)")

    # ── AppContext final config (T-006/T-007, R-102) ──
    ctx.config.update({"host": args.host, "port": args.port, "provider_id": prov_id})
    print(f"  🧩 AppContext: composition root active")

    print(f"""
═══════════════════════════════════════════════════════
  🖥️  WebDev AI Editor — Web Interface
  📂 المشروع: {project_path}
  🌐 الرابط: http://{args.host}:{args.port}
  🤖 المزود: {prov_id} / {model_name}
  📋 الجلسة: {session_mgr.current_session_id}
═══════════════════════════════════════════════════════
    """)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
