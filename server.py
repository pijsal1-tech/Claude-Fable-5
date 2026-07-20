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
# ── إجبار UTF-8 ──
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

_DIR = pathlib.Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock

from actions.file_manager import FileManager
from actions.command_runner import CommandRunner
from actions.response_parser import ResponseParser
from actions.session_manager import SessionManager
from prompts.templates import build_prompt, get_system_prompt
from providers.registry import register_provider, get_provider, list_providers
from providers.use_ai import UseAIProvider, UseAIConfig
from providers.genspark import GensparkProvider, GensparkConfig, GENSPARK_MODELS
from providers.deepseek import DeepSeekProvider, DeepSeekConfig
from providers.alle_ai import AlleAIProvider, AlleAIConfig
from providers.base import Message
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
from chain.agent_tools import AgentTools
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
from chain.knowledge import KnowledgeAccumulator
from core.execution import ExecutionRegistry, RunBusyError
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


# ── Globals (يتم تعيينها في main) ──
fm: FileManager = None
cmd_runner: CommandRunner = None
parser = ResponseParser()
provider = None
chat_history: list[Message] = []
session_mgr: SessionManager = None
_backup_done_for_batch = False  # علامة لمنع تكرار الباك-أب في نفس الـ batch
# R-303 (T-031): بانر تنبيه ربط الجلسة — يُملأ عند تبديل المشروع تحت
# سياسة warn ويُحقن في project_context لكل رسالة حتى بدء جلسة جديدة.
_binding_banner: str = ""
MAX_SMART_FILE_SIZE = 100 * 1024  # حد أقصى لحجم ملف يقرأه Smart Path (100KB)

# ── Chain System Infrastructure (M0 + M5) ──
# R-105 (T-015): ExecutionRegistry supersedes the R-101 interim
# ActiveRunHolder (deleted). Every dispatch — chain / agent / delegate —
# registers a RunTicket; the registry enforces the single-run policy and
# ticket cancellation reaches the loops at their checkpoints.
execution_registry = ExecutionRegistry()

# T-047 (R-604): الـ bus الرصدي العام — RunStarted/RunFinished/
# RoutingDecided/BudgetChanged تُنشر هنا لأي مستهلك داخلي (logging/
# metrics/سجلات R-402) دون أي علاقة بالنقل. إطارات الواجهة تمشي على
# bus خاص بكل اتصال يستهلكه _WSAdapter وحده.
event_bus = EventBus()

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
            pass  # WS مقفول/معطوب — نفس ابتلاع القديم


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


def _begin_run_ticket(kind, send_fn):
    """T-015 (R-105): register a run of `kind` or emit a `busy` frame.

    Returns the RunTicket on success, None when another run is active
    (in which case a `busy` frame was already sent via send_fn).
    """
    try:
        return execution_registry.register(kind)
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


# ── AppContext — Composition Root (T-006, R-102) ──
# Migration note: during R-102 the legacy module globals (fm, cmd_runner,
# provider, provider_pool, session_mgr, account_budget) remain assigned but
# are one-way ALIASES of the AppContext fields — both paths see identical
# objects. T-007 migrates consumers to resolve ctx.project.* at call time;
# T-008 deletes the private-attribute pokes and the dead aliases.
ctx: AppContext = None


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
    """
    return ProjectHandle(
        root=root,
        fm=FileManager(root),
        cmd_runner=CommandRunner(cwd=root, auto_approve=True),
    )


def _build_ctx(project_path: str) -> AppContext:
    """Build the composition root from the already-constructed globals.

    Called by main() after wiring; kept as a separate function so tests can
    verify the aliasing (ctx.project.fm IS fm, etc.) without booting Flask.
    """
    return AppContext(
        project=ProjectHandle(root=project_path, fm=fm, cmd_runner=cmd_runner),
        provider_pool=provider_pool,
        session_manager=session_mgr,
        budget=account_budget,
        handle_factory=_server_handle_factory,
    )
chain_bridge: ChainBridge = None   # M5: جسر السلسلة → WebSocket
delegate_bridge: DelegateBridge = None  # M6: جسر التفويض

# ── Smart Request Pipeline (Phase 1-5) ──
provider_pool: ProviderPool = None          # إدارة مزودين متعددين
account_budget: AccountAwareBudget = None   # ميزانية واعية بالحسابات
capacity_model: CapacityModel = None        # سعة صادقة من pool+breakers (T-038)
request_router: RequestRouter = None        # توجيه ذكي للطلبات
action_applier: ActionApplier = None        # تطبيق نتائج Chain
orchestrator: SmartOrchestrator = None      # تحليل التعقيد

# ── Agent System ──
agent_tools: AgentTools = None              # أدوات الـ Agent
_active_agent_loop: AgentLoop = None        # Agent Loop النشط حالياً

# ── ApprovalGate (T-012, R-104) — نقطة الموافقة الوحيدة قبل أي كتابة ──
approval_gate: ApprovalGate = None


# ════════════════════════════════════════════════════
# Static Pages
# ════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ════════════════════════════════════════════════════
# API — Files
# ════════════════════════════════════════════════════
@app.route("/api/files")
def api_files():
    """قائمة ملفات المشروع"""
    try:
        scan = fm.scan_project(max_files=10000)
        tree = fm.get_project_tree(max_depth=4)
        return jsonify({"ok": True, "scan": scan, "tree": tree})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/file/<path:filepath>")
def api_read_file(filepath):
    """قراءة محتوى ملف"""
    try:
        content = fm.read_file(filepath, with_line_numbers=False)
        content_numbered = fm.read_file(filepath, with_line_numbers=True)
        return jsonify({
            "ok": True,
            "path": filepath,
            "content": content,
            "content_numbered": content_numbered,
            "lines": len(content.splitlines())
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 404


@app.route("/api/folder/<path:folderpath>")
def api_read_folder(folderpath):
    """قراءة محتوى مجلد كامل — للـ drag and drop"""
    try:
        from chain.bridge import scan_folder_for_chain
        full_path = fm._resolve(folderpath)
        if not os.path.isdir(str(full_path)):
            return jsonify({"ok": False, "error": "ليس مجلداً"}), 404
        files = scan_folder_for_chain(str(full_path))
        return jsonify({
            "ok": True,
            "path": folderpath,
            "files": files,
            "count": len(files),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/file/<path:filepath>", methods=["POST"])
def api_write_file(filepath):
    """كتابة/تعديل ملف"""
    data = request.get_json()
    content = data.get("content", "")
    try:
        saved_path = fm.write_file(filepath, content)
        return jsonify({"ok": True, "path": saved_path})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/file/<path:filepath>", methods=["DELETE"])
def api_delete_file(filepath):
    """حذف ملف (مع backup)"""
    try:
        full = fm._resolve(filepath)
        if full.exists():
            fm.create_backup(filepath)
            full.unlink()
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "ملف غير موجود"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ════════════════════════════════════════════════════
# API — Terminal
# ════════════════════════════════════════════════════
@app.route("/api/run", methods=["POST"])
def api_run():
    """تنفيذ أمر في الطرفية — يدعم CMD و PowerShell + cd"""
    data = request.get_json()
    command = data.get("command", "").strip()
    shell_type = data.get("shell", "cmd")  # cmd | powershell
    if not command:
        return jsonify({"ok": False, "error": "أمر فارغ", "cwd": cmd_runner.cwd}), 400

    # ── معالجة cd بشكل خاص (لأن subprocess.run مش بتحفظ الـ cwd) ──
    stripped = command.strip()
    if stripped.lower() == "cd" or stripped.lower() == "cd.":
        return jsonify({"ok": True, "success": True, "output": cmd_runner.cwd, "error": "", "code": 0, "cwd": cmd_runner.cwd})

    if stripped.lower().startswith("cd ") or stripped.lower().startswith("cd\\"):
        target = stripped[3:].strip().strip('"').strip("'")
        try:
            new_cwd = os.path.abspath(os.path.join(cmd_runner.cwd, target))
            if os.path.isdir(new_cwd):
                cmd_runner.cwd = new_cwd
                return jsonify({"ok": True, "success": True, "output": "", "error": "", "code": 0, "cwd": cmd_runner.cwd})
            else:
                return jsonify({"ok": False, "success": False, "output": "", "error": f"المسار غير موجود: {new_cwd}", "code": 1, "cwd": cmd_runner.cwd})
        except Exception as e:
            return jsonify({"ok": False, "success": False, "output": "", "error": str(e), "code": 1, "cwd": cmd_runner.cwd})

    # ── تحضير الأمر حسب نوع الشل ──
    if shell_type == "powershell":
        # PowerShell محتاج wrapper لأن subprocess بيستخدم cmd.exe افتراضياً
        full_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{command}"'
    else:
        # CMD: subprocess.run(shell=True) بيستخدم cmd.exe مباشرة — مش محتاج تغليف
        full_cmd = command

    result = cmd_runner.run(full_cmd, need_approval=False, timeout=30)
    result["cwd"] = cmd_runner.cwd
    return jsonify({"ok": result["success"], **result})


@app.route("/api/cwd")
def api_cwd():
    """الحصول على المسار الحالي"""
    return jsonify({"cwd": cmd_runner.cwd})


# ════════════════════════════════════════════════════
# API — Info
# ════════════════════════════════════════════════════
@app.route("/api/capacity")
def api_capacity():
    """T-038 (R-403): سعة صادقة — أرقام الـ UI مشتقة من CapacityModel
    (حالة pool + قواطع T-037 الحية)، مع أعلام estimated للتخمينات؛
    لا ثوابت حدود حسابات صلبة — كل رقم قابل للتتبع لحالة الموديل."""
    if capacity_model is None:
        return jsonify({"ok": False,
                        "error": "capacity model غير مهيأ بعد"}), 503
    return jsonify({"ok": True,
                    "capacity": capacity_model.report().to_dict()})


@app.route("/api/info")
def api_info():
    """معلومات المشروع والمزود"""
    scan = fm.scan_project()
    return jsonify({
        "ok": True,
        "project": {
            "root": str(fm.root),
            "name": fm.root.name,
            "total_files": scan["total_files"],
            "total_size_kb": scan["total_size_kb"],
        },
        "provider": provider.get_info() if provider else {},
        "history_length": len(chat_history),
    })


@app.route("/api/chat-history")
def api_chat_history():
    """الحصول على تاريخ المحادثة بالكامل"""
    history_data = [{"role": msg.role, "content": msg.content} for msg in chat_history]
    return jsonify({"ok": True, "history": history_data})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """مسح المحادثة وبدء جلسة جديدة"""
    global chat_history, _binding_banner
    chat_history = []
    _binding_banner = ""  # R-303: جلسة جديدة = زوال تنبيه الربط
    # بدء جلسة جديدة
    if session_mgr:
        session_mgr.new_session(str(fm.root) if fm else "")
    return jsonify({"ok": True})


# ════════════════════════════════════════════════════
# API — Sessions
# ════════════════════════════════════════════════════
@app.route("/api/sessions")
def api_sessions():
    """قائمة الجلسات المحفوظة"""
    if not session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500
    sessions = session_mgr.list_sessions()
    return jsonify({"ok": True, "sessions": sessions, "current": session_mgr.current_session_id})


@app.route("/api/session/<session_id>")
def api_load_session(session_id):
    """تحميل جلسة محددة"""
    global chat_history
    if not session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500

    session = session_mgr.load_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "جلسة غير موجودة"}), 404

    # استعادة الـ chat_history
    chat_history = [
        Message(role=m["role"], content=m["content"])
        for m in session.get("messages", [])
    ]
    return jsonify({
        "ok": True,
        "session": session,
        "history": [{"role": m["role"], "content": m["content"]} for m in session.get("messages", [])]
    })


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    """بدء جلسة جديدة"""
    global chat_history, _binding_banner
    if not session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500

    chat_history = []
    _binding_banner = ""  # R-303: جلسة جديدة = زوال تنبيه الربط
    session = session_mgr.new_session(str(fm.root) if fm else "")
    return jsonify({"ok": True, "session": session})


@app.route("/api/session/<session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    """حذف جلسة"""
    if not session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500
    deleted = session_mgr.delete_session(session_id)
    return jsonify({"ok": deleted})


# ════════════════════════════════════════════════════
# API — Backups
# ════════════════════════════════════════════════════
@app.route("/api/backups")
def api_backups():
    """قائمة النسخ الاحتياطية الكاملة"""
    backup_dir = fm.root / ".webdev_backups" / "full"
    if not backup_dir.exists():
        return jsonify({"ok": True, "backups": []})

    backups = []
    for f in sorted(backup_dir.glob("*.zip"), reverse=True):
        backups.append({
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "created": f.stem.split("_", 1)[-1] if "_" in f.stem else "",
        })
    return jsonify({"ok": True, "backups": backups})


@app.route("/api/restore/<backup_name>", methods=["POST"])
def api_restore_backup(backup_name):
    """استعادة نسخة احتياطية"""
    import zipfile
    backup_path = fm.root / ".webdev_backups" / "full" / backup_name
    if not backup_path.exists():
        return jsonify({"ok": False, "error": "النسخة غير موجودة"}), 404

    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            zf.extractall(fm.root)
        return jsonify({"ok": True, "message": f"تم استعادة: {backup_name}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


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
        import yaml as _yaml
        with open(_DIR / "config.yaml", encoding="utf-8") as _cf:
            _sb = (_yaml.safe_load(_cf) or {}).get("session_binding") or {}
        if not isinstance(_sb, dict):
            return "warn"
        if _sb.get("warn_only", True):
            return "warn"
        return str(_sb.get("policy", "warn"))
    except Exception:
        return "warn"


@app.route("/api/switch-project", methods=["POST"])
def api_switch_project():
    """تغيير مسار المشروع"""
    global fm, cmd_runner, chat_history, _binding_banner

    # ── حماية: منع التبديل أثناء run نشط (R-101 → R-105) ──
    _active_runs = execution_registry.list_active()
    if _active_runs:
        return jsonify({
            "ok": False,
            "error": "لا يمكن تغيير المشروع أثناء تشغيل run نشط",
            "chain_run_id": _active_runs[0].run_id
        }), 409

    data = request.get_json()
    new_path = data.get("path", "").strip()
    if not new_path:
        return jsonify({"ok": False, "error": "مسار فارغ"}), 400

    abs_path = os.path.abspath(new_path)
    if not os.path.isdir(abs_path):
        # محاولة إنشاء المجلد
        try:
            os.makedirs(abs_path, exist_ok=True)
        except Exception as e:
            return jsonify({"ok": False, "error": f"فشل إنشاء المجلد: {e}"}), 400

    # ── R-303 (T-031): فحص ربط الجلسة بالمشروع قبل التبديل ──
    # الجلسة المرتبطة ببصمة مشروع مختلف تُعالَج حسب السياسة:
    # warn (بانر سياق) / fork (جلسة جديدة مرتبطة) / block (409 رفض).
    _bind_check = None
    _bound_path = ""
    if session_mgr and getattr(session_mgr, "current_session_id", None):
        from sessions.store import check_project_binding, project_fingerprint
        try:
            _cur = session_mgr.load_session(session_mgr.current_session_id)
            _bound_path = (_cur or {}).get("project_path", "") or ""
            _bind_check = check_project_binding(
                project_fingerprint(_bound_path), abs_path,
                _session_binding_policy())
        except ValueError:
            # سياسة غير معروفة في config = خطأ تهيئة — نفشل بصوت عالٍ
            raise
        except Exception:
            _bind_check = None  # جلسات قديمة/تالفة → تسامح (غير مرتبطة)
    if _bind_check is not None and _bind_check.action == "block":
        return jsonify({
            "ok": False,
            "error": "الجلسة الحالية مرتبطة بمشروع آخر — التبديل مرفوض (سياسة block)",
            "binding": {"policy": "block", "bound_project_path": _bound_path},
        }), 409

    try:
        # R-102 (T-008): the switch IS ctx.switch_project() — one atomic
        # swap; every consumer resolves the new handle at its next call.
        # Legacy globals are re-pointed at the ctx-owned objects (one-way
        # aliases) until the remaining direct readers migrate.
        if ctx is not None:
            handle = ctx.switch_project(abs_path)
            fm = handle.fm
            cmd_runner = handle.cmd_runner
        else:  # ctx-less fallback (tests / legacy boot)
            fm = FileManager(abs_path)
            cmd_runner = CommandRunner(cwd=abs_path, auto_approve=True)
        scan = fm.scan_project()

        # ── R-303 (T-031): تطبيق نتيجة فحص الربط بعد نجاح التبديل ──
        _binding_info = None
        if _bind_check is not None and _bind_check.action == "warn":
            _binding_banner = (
                f"⚠️ [تنبيه ربط الجلسة]: هذه الجلسة بدأت على المشروع "
                f"{_bound_path} وتم التبديل إلى {abs_path} — "
                f"التاريخ السابق قد يخص مشروعًا آخر."
            )
            _binding_info = {"policy": "warn", "banner": _binding_banner}
        elif _bind_check is not None and _bind_check.action == "fork":
            chat_history = []
            _new_sess = session_mgr.new_session(abs_path)
            _binding_banner = ""
            _binding_info = {"policy": "fork",
                             "new_session_id": _new_sess["id"]}

        return jsonify({
            "ok": True,
            "binding": _binding_info,
            "project": {
                "root": str(fm.root),
                "name": fm.root.name,
                "total_files": scan["total_files"],
                "total_size_kb": scan["total_size_kb"],
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/new-file", methods=["POST"])
def api_new_file():
    """إنشاء ملف جديد فارغ"""
    data = request.get_json()
    filepath = data.get("path", "").strip()
    content = data.get("content", "")
    if not filepath:
        return jsonify({"ok": False, "error": "اسم الملف مطلوب"}), 400
    try:
        saved = fm.write_file(filepath, content, backup=False)
        return jsonify({"ok": True, "path": saved})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/new-folder", methods=["POST"])
def api_new_folder():
    """إنشاء مجلد جديد"""
    data = request.get_json()
    folder_name = data.get("path", "").strip()
    if not folder_name:
        return jsonify({"ok": False, "error": "اسم المجلد مطلوب"}), 400
    try:
        full = fm._resolve(folder_name)
        full.mkdir(parents=True, exist_ok=True)
        return jsonify({"ok": True, "path": folder_name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/run-file", methods=["POST"])
def api_run_file():
    """تشغيل ملف (Python / Node.js / etc)"""
    data = request.get_json()
    filepath = data.get("path", "").strip()
    if not filepath:
        return jsonify({"ok": False, "error": "مسار الملف مطلوب"}), 400

    # تحديد الأمر حسب الامتداد
    ext = os.path.splitext(filepath)[1].lower()
    runners = {
        ".py": "python",
        ".js": "node",
        ".ts": "npx ts-node",
        ".sh": "bash",
        ".bat": "cmd /c",
        ".ps1": "powershell -File",
    }

    runner = runners.get(ext)
    if not runner:
        return jsonify({"ok": False, "error": f"لا يمكن تشغيل ملفات {ext}"}), 400

    command = f"{runner} {filepath}"
    result = cmd_runner.run(command, need_approval=False, timeout=30)
    return jsonify({"ok": result["success"], **result, "command": command})


# ════════════════════════════════════════════════════
# WebSocket — AI Streaming
# ════════════════════════════════════════════════════
def ws_handler(ws):
    """WebSocket للتواصل الحي مع AI — مع دعم الجلسات والخطط"""
    global chat_history, _backup_done_for_batch, fm, cmd_runner, delegate_bridge
    global _active_agent_loop

    # T-047 (R-604): كل إطارات هذا الاتصال تمر عبر bus الاتصال →
    # _WSAdapter (موقع ws.send الأوحد). _ws_frame = ناشر الإطارات.
    _ws_frame = _json_sender(ws)

    while True:
        try:
            raw = ws.receive()
            if not raw:
                break
            data = json.loads(raw)
        except Exception:
            break

        msg_type = data.get("type", "")

        if msg_type == "ping":
            # T-006 (R-102): ctx (composition root) is reachable in the WS
            # handler; extra field is ignored by the frontend.
            _ws_frame({"type": "pong", "ctx": ctx is not None})
            continue

        # ── Agent: المستخدم وافق/رفض أمر terminal ──
        if msg_type == "agent_approval_response":
            if _active_agent_loop:
                approved = data.get("approved", False)
                approval_id = data.get("approval_request_id", "")
                payload_hash = data.get("payload_hash", "")
                _active_agent_loop.approve_command(approved, approval_id, payload_hash)
            continue

        # ── Agent: إلغاء من المستخدم (T-041: كان يُلتقط داخل حلقة
        # الاستطلاع المحذوفة — الآن يصل مباشرة لأن الـ Agent يعمل في
        # thread عامل وحلقة WS الرئيسية حرة دائمًا) ──
        if msg_type == "cancel_agent":
            if _active_agent_loop:
                _active_agent_loop.cancel()
                print("    🛑 Agent cancelled by user")
            continue

        # ── Chain: رد المستخدم على إطار chain_approval_request (T-012) ──
        # السلسلة معلّقة في thread منفصل على gate.request — هذا يفكها.
        if msg_type == "chain_approval_response":
            if chain_bridge:
                matched = chain_bridge.resolve_approval(
                    request_id=data.get("request_id", ""),
                    approved=data.get("approved", False),
                    payload_hash=data.get("payload_hash", ""),
                )
                if not matched:
                    print(f"⚠️ Chain approval غير مطابق: {data.get('request_id', '')}")
            continue

        if msg_type == "message":
            user_text = data.get("text", "").strip()
            mode = data.get("mode", "chat")

            if not user_text:
                _ws_frame({"type": "error", "text": "رسالة فارغة"})
                continue

            # ── 1. كشف ذكي للمسارات (ملفات + مجلدات) ──
            import re
            detected_dir = None
            detected_file = None

            # البحث عن مسارات بين علامات التنصيص
            quoted = re.findall(r'["\']([^"\']+)["\']', user_text)
            for p in quoted:
                p_clean = p.strip()
                if os.path.isdir(p_clean):
                    detected_dir = os.path.abspath(p_clean)
                    break
                elif os.path.isfile(p_clean):
                    detected_file = os.path.abspath(p_clean)
                    break

            # البحث في الكلمات عن مسارات (مع دعم Windows backslash)
            if not detected_dir and not detected_file:
                # كشف مسارات Windows مثل D:\path\to\file
                win_paths = re.findall(r'[A-Za-z]:[\\/ ][^\s,;"\'>]+', user_text)
                for wp in win_paths:
                    wp = wp.strip().rstrip('.,;?)')
                    if os.path.isdir(wp):
                        detected_dir = os.path.abspath(wp)
                        break
                    elif os.path.isfile(wp):
                        detected_file = os.path.abspath(wp)
                        break

            if not detected_dir and not detected_file:
                for w in user_text.split():
                    w_clean = w.strip('.,;?()[]{}"\'')
                    if os.path.isdir(w_clean):
                        detected_dir = os.path.abspath(w_clean)
                        break
                    elif os.path.isfile(w_clean):
                        detected_file = os.path.abspath(w_clean)
                        break

            if not detected_dir and not detected_file and os.path.isdir(user_text.strip()):
                detected_dir = os.path.abspath(user_text.strip())
            elif not detected_dir and not detected_file and os.path.isfile(user_text.strip()):
                detected_file = os.path.abspath(user_text.strip())

            # ── معالجة ملف مكتشف: قراءة محتواه وإرفاقه ──
            if detected_file:
                try:
                    with open(detected_file, 'r', encoding='utf-8', errors='replace') as df:
                        file_content = df.read(MAX_SMART_FILE_SIZE)
                    file_ext = os.path.splitext(detected_file)[1]
                    user_text += f"\n\n[📄 محتوى الملف: {detected_file}]:\n```{file_ext.lstrip('.')}\n{file_content}\n```"
                except Exception:
                    pass  # تجاهل أخطاء القراءة
                detected_file = None  # لا نغير المجلد

            # ── معالجة مجلد مكتشف: تغيير المشروع ──
            if detected_dir:
                try:
                    # R-102 (T-008): switch through the composition root.
                    if ctx is not None:
                        _handle = ctx.switch_project(detected_dir)
                        fm = _handle.fm
                        cmd_runner = _handle.cmd_runner
                    else:
                        fm = FileManager(detected_dir)
                        cmd_runner = CommandRunner(cwd=detected_dir, auto_approve=True)
                    scan = fm.scan_project()
                    if session_mgr:
                        session_mgr.update_project_path(detected_dir)

                    _ws_frame({
                        "type": "project_switched",
                        "project": {
                            "root": str(fm.root),
                            "name": fm.root.name,
                            "total_files": scan["total_files"],
                            "total_size_kb": scan["total_size_kb"],
                        }
                    })

                    _ws_frame({"type": "start"})
                    _ws_frame({
                        "type": "chunk",
                        "text": f"حاضر يا صاحبي! أنا غيرت مجلد العمل دلوقتي للمجلد ده: `{detected_dir}` 📂\n\nلقيت فيه {scan['total_files']} ملف. تقدر تطلب مني أي حاجة بخصوصهم دلوقتي! 👍"
                    })
                    _ws_frame({
                        "type": "done",
                        "actions": [],
                        "options": [],
                        "summary": "Switched project directory"
                    })
                    continue
                except Exception as e:
                    _ws_frame({"type": "error", "text": f"فشل فتح المجلد: {e}"})
                    continue

            # ── 2. جمع السياق — ContextEngine (T-019, R-201) ──
            # الكتلة المضمّنة القديمة (mention regex → rglob لكل كلمة →
            # حقن المحتوى → get_project_context) استُخرجت إلى حزمة context/
            # بمسح نظام ملفات واحد لكل رسالة. الـ parity مضمون بـ goldens
            # T-017 عبر tests/unit/test_context_engine.py.
            try:
                _msg_ctx = gather_message_context(fm.root, user_text)
                mentioned_files = _msg_ctx.mentioned_files
                user_text_with_files = _msg_ctx.user_text_with_files
                project_context = _msg_ctx.project_context
            except Exception:
                mentioned_files = []
                user_text_with_files = user_text
                project_context = ""

            # R-303 (T-031): حقن بانر تنبيه الربط (سياسة warn) في السياق
            if _binding_banner:
                project_context = (
                    f"{_binding_banner}\n\n{project_context}"
                    if project_context else _binding_banner
                )

            # ═══════════════════════════════════════
            # 🧠 Smart Routing — RequestRouter يقرر المسار
            # ═══════════════════════════════════════
            if request_router and mode != "chat":
                try:
                    # جمع محتوى الملفات المذكورة كـ dict
                    files_dict = None
                    if mentioned_files:
                        files_dict = {}
                        for f_path in mentioned_files[:5]:
                            try:
                                files_dict[f_path] = fm.read_file(f_path)
                            except Exception:
                                pass

                    # اتخاذ القرار
                    file_content_for_routing = None
                    if mentioned_files and len(mentioned_files) == 1:
                        try:
                            file_content_for_routing = fm.read_file(mentioned_files[0])
                        except Exception:
                            pass

                    routing = request_router.route(
                        user_request=user_text,
                        file_content=file_content_for_routing,
                        files=files_dict,
                        mode=mode,
                    )

                    # ── إبلاغ المستخدم بالقرار ──
                    # T-035 (R-401): الفصل على الطبقة (tier) لا النص —
                    # الترجمة label→tier تعيش في RoutingDecision.tier وحدها.
                    routing_tier = routing.tier
                    # T-047 (R-604): قرار التوجيه حدث رصدي على الـ bus
                    # العام (سجلات R-402) — لا إطار واجهة منه.
                    event_bus.publish(RoutingDecided(
                        run_id=f"route-{uuid.uuid4().hex[:8]}",
                        strategy=str(routing.strategy),
                        payload=routing.to_dict()))
                    if routing_tier is not RoutingTier.DIRECT:
                        _ws_frame({
                            "type": "chain_started",
                            "text": (
                                f"🧠 Smart Router: اختار **{routing.strategy}** "
                                f"(complexity: {routing.complexity_score:.1f})"
                                + (f"\n⚠️ {routing.downgrade_reason}" if routing.downgraded else "")
                            ),
                            "routing": routing.to_dict(),
                        })

                    # ── توجيه لـ chain_bridge ──
                    if routing_tier is RoutingTier.CHAINED:
                        # T-015 (R-105): registry ticket — single-run policy
                        chain_ticket = _begin_run_ticket(
                            "chain",
                            lambda m: _ws_frame(m))
                        if chain_ticket is None:
                            continue
                        _ws_send = _json_sender(ws)

                        # حفظ في history
                        chat_history.append(Message(role="user", content=user_text))
                        if session_mgr:
                            session_mgr.append_message("user", user_text)

                        # T-041 (R-501): المسار الوحيد — runner فوق نفس
                        # الجسر، نفس الإطارات (عبر _RunnerWSAdapter)، نفس
                        # التذكرة. الـ runner يعمل في thread حتى تبقى حلقة
                        # WS مستقبِلة (chain_approval_response تصل للبوابة).
                        _chain_req = RunRequest(
                            mode="chain",
                            message=user_text_with_files,
                            context={
                                "file_content": file_content_for_routing,
                                "files": files_dict,
                            },
                            metadata={
                                "force_strategy": routing.chain_strategy,
                            },
                        )
                        threading.Thread(
                            target=RUNNERS["chain"](bridge=chain_bridge).run,
                            args=(_chain_req, chain_ticket,
                                  _RunnerWSAdapter(_ws_send)),
                            daemon=True,
                            name=f"runner-chain-{chain_ticket.run_id}",
                        ).start()
                        continue  # الـ runner يتكفل بالرد

                    # ── توجيه لـ delegate_bridge ──
                    if routing_tier is RoutingTier.DELEGATE and delegate_bridge:
                        # T-041: إطارات {"type": et, **ed} تُبنى الآن داخل
                        # _RunnerWSAdapter من أحداث DelegateRunner الحرة —
                        # هنا الإرسال الخام فقط (نفس الحماية من WS مقفول).
                        _delegate_event_frame = _json_sender(ws)

                        # حفظ في history
                        chat_history.append(Message(role="user", content=user_text))
                        if session_mgr:
                            session_mgr.append_message("user", user_text)

                        # T-015 (R-105): registry ticket — delegate أصبح قابلاً للإلغاء
                        delegate_ticket = _begin_run_ticket(
                            "delegate",
                            lambda m: _ws_frame(m))
                        if delegate_ticket is None:
                            continue
                        # T-041 (R-501): عبر DelegateRunner — نفس الجسر ونفس
                        # الأحداث (تصل الواجهة حرفيًا عبر _RunnerWSAdapter).
                        # نداء متزامن كما كان: run_delegation يعود عند
                        # waiting_approval — لا انتظار مستخدم داخل النداء.
                        RUNNERS["delegate"](bridge=delegate_bridge).run(
                            RunRequest(
                                mode="delegate",
                                message=user_text,
                                context={
                                    "files": files_dict or {},
                                    "project_context": project_context,
                                },
                            ),
                            delegate_ticket,
                            _RunnerWSAdapter(_delegate_event_frame),
                        )
                        continue  # الـ delegate يتكفل بالرد

                except Exception as e:
                    # لو الـ router فشل — نكمل بالمسار العادي
                    print(f"  ⚠️ Router error: {e}")

            # ═══════════════════════════════════════
            # 🤖 Agent Loop — لكل الأوضاع
            # ═══════════════════════════════════════
            if agent_tools and mode in ("build", "edit", "chat", "plan"):
                try:
                    _ws_lock = threading.Lock()

                    def _agent_ws_send(msg_dict):
                        """إرسال WebSocket thread-safe"""
                        try:
                            with _ws_lock:
                                _ws_frame(msg_dict)
                        except Exception as e:
                            print(f"  ⚠️ Agent WS send error: {e}")

                    def _agent_send_fn(prompt_text, hist, sys_prompt):
                        """إرسال عبر provider_pool — مع fallback"""
                        if provider_pool:
                            result, used_name = provider_pool.send_with_fallback(
                                prompt_text, hist, sys_prompt
                            )
                            return result
                        return _active_provider().send(prompt_text, hist, sys_prompt)

                    # T-041 (R-501): AgentRunner في thread عامل — حلقة الـ WS
                    # الرئيسية تبقى حرة دائمًا، فرسائل agent_approval_response
                    # وcancel_agent تصل من المستوى الأعلى مباشرة (حلقة
                    # الاستطلاع القديمة workaround حُذفت بالكامل).

                    # حفظ في history
                    chat_history.append(Message(role="user", content=user_text))
                    if session_mgr:
                        session_mgr.append_message("user", user_text)

                    # إرسال بداية
                    _ws_frame({"type": "start"})
                    print(f"  🤖 Agent Loop started (mode={mode})")

                    # T-015 (R-105): registry ticket — agent تحت نفس السجل
                    agent_ticket = _begin_run_ticket("agent", _agent_ws_send)
                    if agent_ticket is None:
                        continue

                    def _agent_loop_factory(frame_sink):
                        """يبني AgentLoop لهذا الطلب — الإطارات عبر sink الـ runner."""
                        return AgentLoop(
                            tools=agent_tools,
                            send_fn=_agent_send_fn,
                            ws_send_fn=frame_sink,
                            system_prompt=get_system_prompt(),
                            max_iterations=6,
                            # T-013 (R-104): نفس بوابة الموافقة الموحدة لكل الأوضاع
                            approval_gate=approval_gate,
                        )

                    def _publish_agent_loop(loop):
                        """ينشر الحلقة النشطة — الموافقات/الإلغاء من مستوى WS الأعلى."""
                        global _active_agent_loop
                        _active_agent_loop = loop

                    _agent_req = RunRequest(
                        mode="agent",
                        message=user_text_with_files,
                        context={
                            "history": chat_history[:-1],
                            "project_context": project_context,
                        },
                    )
                    _agent_runner = RUNNERS["agent"](
                        loop_factory=_agent_loop_factory,
                        on_loop=_publish_agent_loop,
                    )
                    _agent_sink = _RunnerWSAdapter(_agent_ws_send)

                    def _run_agent():
                        global _active_agent_loop
                        try:
                            result = _agent_runner.run(
                                _agent_req, agent_ticket, _agent_sink)
                        finally:
                            _active_agent_loop = None

                        if result.status == RESULT_FAILED:
                            print(f"  ❌ Agent Loop error: {result.error}")
                            _agent_ws_send({"type": "error", "text": result.error})
                            _agent_ws_send({"type": "done", "options": []})
                            return

                        full_response = result.text or ""
                        print(f"  ✅ Agent Loop done — {len(full_response)} chars")

                        if not full_response:
                            _agent_ws_send({"type": "error", "text": "لم يتم الحصول على رد من الـ AI"})
                            _agent_ws_send({"type": "done", "options": []})
                            return

                        # الرد نفسه وصل الواجهة كـ chunks من الـ runner —
                        # هنا الحفظ + التحليل + إطار plan/done الختامي فقط.
                        chat_history.append(Message(role="assistant", content=full_response))
                        if session_mgr:
                            session_mgr.append_message("assistant", full_response)

                        parsed = parser.parse(full_response)
                        actions = []
                        for fb in parsed.files:
                            actions.append({"action": "create_file", "path": fb.path, "content": fb.content, "language": fb.language})
                        for eb in parsed.edits:
                            actions.append({"action": "edit_file", "path": eb.path, "old_text": eb.old_text, "new_text": eb.new_text})
                        for cb in parsed.commands:
                            actions.append({"action": "run_command", "command": cb.command})

                        options = [opt.text for opt in parsed.options] if hasattr(parsed, 'options') and parsed.options else []

                        if actions:
                            _agent_ws_send({
                                "type": "plan",
                                "actions": actions,
                                "options": options,
                                "summary": parsed.summary(),
                            })
                        else:
                            _agent_ws_send({
                                "type": "done",
                                "options": options,
                            })

                    _backup_done_for_batch = False
                    threading.Thread(
                        target=_run_agent,
                        daemon=True,
                        name=f"runner-agent-{agent_ticket.run_id}",
                    ).start()
                    continue  # الـ runner يتكفل بالرد

                except Exception as e:
                    _active_agent_loop = None
                    print(f"  ⚠️ Agent Loop error: {e}")
                    import traceback
                    traceback.print_exc()
                    # fallback للمسار العادي

            # المسار العادي (direct/chat) — بناء البرومبت
            prompt = build_prompt(
                mode=mode,
                user_request=user_text_with_files,
                project_context=project_context
            )

            # نحفظ النص الأصلي في الـ history (بدون سياق المشروع لتوفير مساحة)
            chat_history.append(Message(role="user", content=user_text))
            # حفظ فوري في الجلسة (crash-safe)
            if session_mgr:
                session_mgr.append_message("user", user_text)

            system_prompt = get_system_prompt()

            # إرسال بداية
            _ws_frame({"type": "start"})

            # T-041 (R-501): المسار الوحيد — DirectRunner (نفس النداء stream
            # ونفس إطارات chunk/error عبر _RunnerWSAdapter؛ التذكرة بنوع
            # "direct"). المطابقة مع stream-worker المحذوف مثبتة في
            # tests/integration/test_dispatch_parity.py (بايت-بايت).
            direct_ticket = _begin_run_ticket("direct", _json_sender(ws))
            if direct_ticket is None:
                continue
            _direct_req = RunRequest(
                mode="direct",
                message=prompt,
                system_prompt=system_prompt,
                context={"history": chat_history[:-1]},
            )
            _direct_result = RUNNERS["direct"](
                stream_fn=lambda p, h, s: _active_provider().stream(p, h, s)
            ).run(_direct_req, direct_ticket, _RunnerWSAdapter(_json_sender(ws)))
            # دلالة المسار القديم حرفيًا: الفشل يرسل إطار error ثم يُكمل
            # للتحليل بالنص الجزئي (لا continue) — نفس فرع "error" القديم.
            full_response = _direct_result.text
            if _direct_result.status != RESULT_COMPLETED:
                _ws_frame({
                    "type": "error",
                    "text": _direct_result.error or "الرد لم يكتمل",
                })

            # تحليل الرد
            chat_history.append(Message(role="assistant", content=full_response))
            # حفظ فوري في الجلسة (crash-safe)
            if session_mgr:
                session_mgr.append_message("assistant", full_response)

            parsed = parser.parse(full_response)

            actions = []
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

            # استخراج الاقتراحات الذكية (Quick Replies)
            options = [opt.text for opt in parsed.options] if hasattr(parsed, 'options') and parsed.options else []

            # إعادة تعيين علامة الباك-أب
            _backup_done_for_batch = False

            # ── نظام Plan First ──
            if mode in ("plan", "build", "edit") and actions:
                _ws_frame({
                    "type": "plan",
                    "actions": actions,
                    "options": options,
                    "summary": parsed.summary(),
                })
            else:
                _ws_frame({
                    "type": "done",
                    "actions": actions,
                    "options": options,
                    "summary": parsed.summary(),
                })

        elif msg_type == "apply_action":
            # تطبيق إجراء محدد (مع باك-أب تلقائي)
            action = data.get("action", {})
            result = _apply_single_action(action)
            _ws_frame({"type": "action_result", **result})

        elif msg_type == "apply_all_actions":
            # تطبيق كل الإجراءات خطوة بخطوة
            actions = data.get("actions", [])
            _backup_done_for_batch = False
            total = len(actions)
            for i, action in enumerate(actions):
                # إرسال progress
                _ws_frame({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "running",
                })
                result = _apply_single_action(action)
                _ws_frame({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "done" if result["ok"] else "error",
                    "message": result.get("message", ""),
                })
                if not result["ok"]:
                    _ws_frame({
                        "type": "error",
                        "text": f"فشل في الخطوة {i+1}: {result.get('message', '')}"
                    })
                    break

            _backup_done_for_batch = False
            _ws_frame({"type": "all_actions_done", "total": total})

        elif msg_type == "execute_plan":
            # تنفيذ خطة معتمدة (نفس apply_all_actions)
            actions = data.get("actions", [])
            _backup_done_for_batch = False
            total = len(actions)
            for i, action in enumerate(actions):
                _ws_frame({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "running",
                })
                result = _apply_single_action(action)
                _ws_frame({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "done" if result["ok"] else "error",
                    "message": result.get("message", ""),
                })
                if not result["ok"]:
                    _ws_frame({
                        "type": "error",
                        "text": f"فشل في الخطوة {i+1}: {result.get('message', '')}"
                    })
                    break

            _backup_done_for_batch = False
            _ws_frame({"type": "all_actions_done", "total": total})

        # ═══════════════════════════════════════════
        #  M5: Chain System — WebSocket Handlers
        # ═══════════════════════════════════════════

        elif msg_type == "chain_message":
            # تشغيل chain ذكي (بديل لـ message العادية للمهام المعقدة)
            user_text = data.get("text", "").strip()
            if not user_text:
                _ws_frame({"type": "error", "text": "رسالة فارغة"})
                continue

            force_strategy = data.get("strategy", None)  # اختياري

            # تحضير المحتوى
            file_content = data.get("file_content", None)
            file_path = data.get("file_path", "")
            folder_path = data.get("folder_path", "")  # مسار مجلد كامل
            files = data.get("files", None)  # {path: content}

            # ── قراءة مجلد كامل ──
            if folder_path and os.path.isdir(folder_path):
                from chain.bridge import scan_folder_for_chain, get_folder_summary

                # ملخص أولاً
                summary = get_folder_summary(folder_path)
                _ws_frame({
                    "type": "folder_scanned",
                    "folder": summary,
                    "text": f"📂 تم مسح المجلد: {summary.get('name', '')} "
                            f"({summary.get('total_files', 0)} ملف، "
                            f"{summary.get('total_size_kb', 0)}KB)",
                })

                # قراءة المحتوى
                files = scan_folder_for_chain(folder_path)

                if not files:
                    _ws_frame({
                        "type": "error",
                        "text": "المجلد فاضي أو مفيش ملفات نصية قابلة للقراءة",
                    })
                    continue

            # ── قراءة ملف واحد ──
            elif not file_content and file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read(MAX_SMART_FILE_SIZE)
                except Exception:
                    pass

            if not chain_bridge:
                _ws_frame({"type": "error", "text": "Chain system غير مفعّل"})
                continue

            # T-015 (R-105): registry ticket — single-run policy
            chain_ticket = _begin_run_ticket(
                "chain",
                lambda m: _ws_frame(m))
            if chain_ticket is None:
                continue
            _ws_send = _json_sender(ws)

            run_id = chain_bridge.start_chain(
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

        elif msg_type == "chain_cancel":
            # إلغاء chain نشط
            reason = data.get("reason", "User cancelled")
            if chain_bridge:
                ok = chain_bridge.cancel(reason)
                if ok:
                    # T-015 (R-105): ارفع علم الإلغاء على التذاكر النشطة —
                    # التذكرة تُنهى بدقة في finally الخاص بالـ bridge
                    for _t in execution_registry.list_active():
                        _t.cancel(reason)
                _ws_frame({
                    "type": "chain_cancel_result",
                    "ok": ok,
                    "text": "تم إلغاء السلسلة" if ok else "مفيش سلسلة نشطة",
                })
            else:
                _ws_frame({"type": "error", "text": "Chain system غير مفعّل"})

        elif msg_type == "chain_status":
            # حالة chain النشط
            if chain_bridge:
                status = chain_bridge.get_status()
                _ws_frame({"type": "chain_status", **status})
            else:
                _ws_frame({"type": "chain_status", "active": False})

        # ── T-044 (R-601): Crash Resume surface ──
        elif msg_type == "resume_scan":
            # مسح runs_dir عن runs منقطعة قابلة للاستكمال
            if chain_bridge:
                _ws_frame({
                    "type": "resumable_runs",
                    "runs": chain_bridge.list_resumable(),
                })
            else:
                _ws_frame({"type": "resumable_runs", "runs": []})

        elif msg_type == "resume_run":
            # استكمال run منقطع — تحقق انجراف البصمات قبل أي تنفيذ
            if not chain_bridge:
                _ws_frame({"type": "error",
                                    "text": "Chain system غير مفعّل"})
                continue
            resume_id = data.get("run_id", "").strip()
            if not resume_id:
                _ws_frame({"type": "error", "text": "run_id مطلوب"})
                continue
            resume_ticket = _begin_run_ticket(
                "chain",
                lambda m: _ws_frame(m))
            if resume_ticket is None:
                continue
            ok = chain_bridge.resume_run(
                resume_id, _json_sender(ws), ticket=resume_ticket)
            if not ok:
                # الرفض/الخطأ أُرسل من الجسر — حرّر التذكرة
                resume_ticket.finish("failed")

        elif msg_type == "discard_run":
            # حذف حالة run منقطع نهائيًا
            if not chain_bridge:
                _ws_frame({"type": "error",
                                    "text": "Chain system غير مفعّل"})
                continue
            discard_id = data.get("run_id", "").strip()
            ok = chain_bridge.discard_run(discard_id)
            _ws_frame({
                "type": "discard_result",
                "run_id": discard_id,
                "ok": ok,
                "text": ("🗑️ حُذفت حالة الـ run" if ok
                         else "⚠️ لا يوجد run بهذا المعرّف"),
            })

        # ── T-016 (R-105): Registry control surface ──
        elif msg_type == "list_runs":
            # كل الـ runs التي يعرفها السجل (نشطة ومنتهية) — id/mode/state/started_at
            _ws_frame(_list_runs_frame())

        elif msg_type == "cancel_run":
            # إلغاء تعاوني لـ run محدد بمعرّفه — acknowledged / not_found
            _ws_frame(
                _cancel_run_frame(data.get("run_id", ""), data.get("reason", "")),
                ensure_ascii=False,
            )

        # ── M6: Delegate System ──
        elif msg_type == "delegate_message":
            # تفويض مهمة معقدة
            user_text = data.get("text", "").strip()
            if not user_text:
                _ws_frame({"type": "error", "text": "الرسالة فارغة"})
                continue

            if not delegate_bridge:
                delegate_bridge = DelegateBridge(_active_provider(), ctx=ctx)

            # جمع ملفات السياق
            files_context = {}
            try:
                scan = fm.scan_project()
                for f in scan.get("files", [])[:10]:
                    try:
                        content = fm.read_file(f["path"])
                        files_context[f["path"]] = content
                    except Exception:
                        pass
            except Exception:
                pass

            project_context = ""
            try:
                project_context = fm.get_project_context()
            except Exception:
                pass

            # T-041 (R-501): نفس مسار الإرسال الموحّد — DelegateRunner فوق
            # الجسر (كان النداء المباشر هنا بلا تذكرة — الآن التفويض من هذا
            # المدخل أيضًا تحت سياسة الـ run الواحد وقابل للإلغاء).
            delegate_msg_ticket = _begin_run_ticket("delegate", _json_sender(ws))
            if delegate_msg_ticket is None:
                continue

            threading.Thread(
                target=RUNNERS["delegate"](bridge=delegate_bridge).run,
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
                    _RunnerWSAdapter(_json_sender(ws)),
                ),
                daemon=True,
                name=f"runner-delegate-{delegate_msg_ticket.run_id}",
            ).start()

        elif msg_type == "delegate_approve":
            # المستخدم وافق على التعديلات
            if delegate_bridge and delegate_bridge.is_active:
                def approval_handler(et, ed):
                    try:
                        _ws_frame({"type": et, **ed})
                    except Exception:
                        pass

                landed = delegate_bridge.land(on_event=approval_handler)
                if landed and delegate_bridge.current_run:
                    # أرسل الرد للمعالجة العادية
                    run = delegate_bridge.current_run
                    if run.result:
                        _ws_frame({
                            "type": "start",
                        })
                        _ws_frame({
                            "type": "chunk",
                            "text": run.result.response,
                        })
                        # تحليل الأكشنز
                        try:
                            actions = parser.extract_actions(run.result.response)
                            options = parser.extract_options(run.result.response)
                            _ws_frame({
                                "type": "done",
                                "actions": actions,
                                "options": options,
                                "summary": f"✅ تم اعتماد التعديلات (delegation #{run.run_id})",
                            })
                        except Exception:
                            _ws_frame({
                                "type": "done",
                                "actions": [],
                                "options": [],
                                "summary": f"✅ تم اعتماد التعديلات",
                            })
            else:
                _ws_frame({"type": "error", "text": "لا يوجد تفويض نشط"})

        elif msg_type == "delegate_reject":
            # المستخدم رفض التعديلات
            reason = data.get("reason", "")
            if delegate_bridge and delegate_bridge.is_active:
                delegate_bridge.reject(reason, on_event=lambda et, ed: _ws_frame(
                    {"type": et, **ed}
                ))
            else:
                _ws_frame({"type": "error", "text": "لا يوجد تفويض نشط"})

    # ── WebSocket Disconnected Cleanup ──
    print("🔌 WebSocket disconnected. Cleaning up and cancelling active tasks...")
    if _active_agent_loop:
        try:
            _active_agent_loop.cancel()
        except Exception:
            pass
    if chain_bridge:
        try:
            chain_bridge.cancel("WebSocket disconnected")
        except Exception:
            pass


# Explicit registration (T-006): flask-sock's decorator returns None, which
# would erase the module-level name and make the handler untestable. Register
# without the decorator so `server.ws_handler` stays a plain callable.
sock.route("/ws")(ws_handler)


# ── حد أقصى لحجم ملف يقرأه Smart Path (100KB) ──
MAX_SMART_FILE_SIZE = 100 * 1024


def _apply_single_action(action: dict) -> dict:
    """تطبيق إجراء واحد — مع باك-أب إلزامي قبل أي تعديل"""
    global _backup_done_for_batch
    act_type = action.get("action", "")

    try:
        # باك-أب كامل قبل أول تعديل في الـ batch
        if not _backup_done_for_batch and act_type in ("create_file", "edit_file"):
            try:
                backup_path = fm.create_full_backup()
                _backup_done_for_batch = True
                if backup_path:
                    print(f"🛡️ Full backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup warning: {e}")
                _backup_done_for_batch = True  # لا نوقف التنفيذ بسبب فشل الباك-أب

        if act_type == "create_file":
            path = action["path"]
            content = action["content"]
            saved = fm.write_file(path, content)
            return {"ok": True, "message": f"تم حفظ: {saved}"}

        elif act_type == "edit_file":
            path = action["path"]
            fm.edit_file(path, action["old_text"], action["new_text"])
            return {"ok": True, "message": f"تم تعديل: {path}"}

        elif act_type == "run_command":
            result = cmd_runner.run(action["command"], need_approval=False)
            return {"ok": result["success"], "message": result["output"] or result["error"]}

        return {"ok": False, "message": f"إجراء غير معروف: {act_type}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════
def main():
    global fm, cmd_runner, provider, session_mgr, chain_bridge, ctx
    global provider_pool, account_budget, request_router, action_applier, orchestrator
    global capacity_model
    global agent_tools

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

    # المزود الافتراضي — Genspark Sonnet 5
    default_provider = args.model or "genspark:claude-sonnet-5"
    if ":" in default_provider:
        prov_id, model_name = default_provider.split(":", 1)
    else:
        # لو المستخدم حط اسم موديل بس
        prov_id = "genspark"
        model_name = default_provider

    if prov_id == "genspark":
        provider_config = GensparkConfig(model=model_name)
        provider = GensparkProvider(provider_config)
    elif prov_id == "deepseek":
        provider_config = DeepSeekConfig(model=model_name)
        provider = DeepSeekProvider(provider_config)
    elif prov_id == "alle_ai":
        provider_config = AlleAIConfig(model=model_name)
        provider = AlleAIProvider(provider_config)
    else:
        provider_config = UseAIConfig(
            model=model_name,
            ws_timeout=90,
            accounts_dir=str(_DIR),
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
        import yaml as _yaml
        with open(_DIR / "config.yaml", encoding="utf-8") as _cf:
            _auto_execute = bool((_yaml.safe_load(_cf) or {}).get("auto_execute", False))
    except Exception:
        pass
    global approval_gate
    approval_gate = ApprovalGate(
        mode="auto" if _auto_execute else "interactive",
        auto_whitelist={"write", "edit", "command"} if _auto_execute else None,
        timeout_seconds=120.0,
    )
    print(f"  🛡️ ApprovalGate: {approval_gate.mode}")

    # ── Chain Bridge (M5) ──
    chain_bridge = ChainBridge(
        provider=provider,
        project_root=project_path,
        approval_gate=approval_gate,
        ctx=ctx,
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
        import yaml as _yaml
        with open(_DIR / "config.yaml", encoding="utf-8") as _cf:
            _retention_cfg = (_yaml.safe_load(_cf) or {}).get("retention")
        _rp = policy_from_config(_retention_cfg)
        if project_path:
            _report = sweep(pathlib.Path(project_path) / ".ai_runs", _rp,
                            log=print)
            _mode = "dry-run" if _report.dry_run else "live"
            print(f"  🧹 Retention ({_mode}): "
                  f"{len(_report.kept)} باقٍ / {len(_report.deleted)} "
                  f"{'مرشح للحذف' if _report.dry_run else 'محذوف'}")
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
                pass  # Fallback providers — not critical

    account_budget = AccountAwareBudget(provider_pool.all_providers)
    orchestrator = SmartOrchestrator()
    # T-036 (R-402): عتبات التوجيه من config.routing — صاخبة على schema
    # مكسورة (لا نبتلع الخطأ: عتبات خاطئة صامتة أسوأ من فشل إقلاع واضح)؛
    # قسم مفقود فقط = الافتراضات التاريخية.
    from chain.routing_config import thresholds_from_config
    import yaml as _yaml
    with open(_DIR / "config.yaml", encoding="utf-8") as _cf:
        _routing_cfg = (_yaml.safe_load(_cf) or {}).get("routing")
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
    agent_tools = AgentTools(
        file_manager=fm,
        command_runner=cmd_runner,
        project_root=project_path,
        ctx=ctx,
    )
    print(f"  🤖 Agent System: active")

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
