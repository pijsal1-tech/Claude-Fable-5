# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ChainBridge — ربط chain system بـ server.py

  M4: Server Integration
  - ChainBridge: يحوّل chain events → WebSocket messages
  - يدير ChainRun lifecycle (start / cancel / status)
  - يحفظ state في مجلد sessions/
  - Thread-safe: chain يعمل في thread منفصل
═══════════════════════════════════════════════════════
"""
import hashlib
import json
import os
import pathlib
import threading
import time
import uuid

import sys
_EDITOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EDITOR_DIR not in sys.path:
    sys.path.insert(0, _EDITOR_DIR)

from providers.base import BaseProvider
from .models import ChainRun, ChainStep, ExecutionPolicy, ProviderSnapshot, ProjectSnapshot
from .executor import ChainExecutor, ChainEvent
from .orchestrator import SmartOrchestrator
from .agent_loader import AgentLoader
from .action_applier import ActionApplier
from core.approval import ApprovalGate, ApprovalRequest, ProposedAction
from core.execution import RunTicket
from .path_policy import is_secret_file  # T-025 (R-204): فلتر حدود الماسح


def _build_project_snapshot(project_root: str,
                            files: dict[str, str] | None,
                            file_path: str = "",
                            file_content: str = "") -> ProjectSnapshot | None:
    """R-305 (T-033): لقطة مشروع صادقة — بصمات محتوى حقيقية أو لا لقطة.

    العقد (قبول R-305): اللقطة إما غير فارغة أو غائبة — أبدًا
    ليست موجودة-وفارغة (الـ artifact الكاذب القديم: خريطة
    ``relevant_file_hashes`` فارغة دائمًا). البصمات = ``sha256``
    لمحتوى الملفات التي يلمسها الـ run (ما مُرّر لـ ``start_chain``
    من ملفات مذكورة/مجموعة) — المحتوى في الذاكرة أصلًا، فلا
    قراءة قرص إضافية ولا سباق مع تعديلات لاحقة (متطلب R-601).
    """
    if not project_root:
        return None
    hashes: dict[str, str] = {}
    for rel_path, content in (files or {}).items():
        hashes[rel_path] = hashlib.sha256(
            content.encode("utf-8", errors="replace")).hexdigest()
    if file_path and file_content:
        hashes.setdefault(file_path, hashlib.sha256(
            file_content.encode("utf-8", errors="replace")).hexdigest())
    if not hashes:
        return None   # لا ملفات ملموسة ⇒ لا لقطة — ليس لقطة فارغة كاذبة
    return ProjectSnapshot(
        project_root=project_root,
        project_id=os.path.basename(project_root),
        relevant_file_hashes=hashes,
    )


# ═══════════════════════════════════════════════════════
#   Event → WebSocket Message Mapping
# ═══════════════════════════════════════════════════════

def _event_to_ws_message(event: ChainEvent) -> dict | None:
    """
    يحوّل ChainEvent → رسالة WebSocket.
    يرجع None لو الحدث ما يحتاج إرسال.
    """
    etype = event.event_type

    if etype == "run_started":
        total = event.data.get("total_steps", 0)
        return {
            "type": "chain_started",
            "run_id": event.data.get("run_id", ""),
            "total_steps": total,
            "text": f"🔗 بدأ chain ({total} خطوات)...",
        }

    elif etype == "step_started":
        return {
            "type": "chain_step",
            "step_id": event.step_id,
            "status": "running",
            "name": event.data.get("name", ""),
            "stage": event.data.get("stage", ""),
            "text": f"⏳ {event.data.get('name', event.step_id)}...",
        }

    elif etype == "step_completed":
        return {
            "type": "chain_step",
            "step_id": event.step_id,
            "status": "success",
            "duration_ms": event.data.get("duration_ms", 0),
            "result_size": event.data.get("result_size", 0),
            "text": f"✅ {event.step_id} ({event.data.get('duration_ms', 0)}ms)",
        }

    elif etype == "step_failed":
        return {
            "type": "chain_step",
            "step_id": event.step_id,
            "status": "error",
            "error": event.data.get("error", ""),
            "text": f"❌ {event.step_id}: {event.data.get('error', '')}",
        }

    elif etype == "step_skipped":
        return {
            "type": "chain_step",
            "step_id": event.step_id,
            "status": "skipped",
            "text": f"⏭️ {event.step_id}: {event.data.get('reason', 'skipped')}",
        }

    elif etype == "step_retry":
        return {
            "type": "chain_retry",
            "step_id": event.step_id,
            "attempt": event.data.get("attempt", 0),
            "error_type": event.data.get("error_type", ""),
            "text": f"🔄 Retry #{event.data.get('attempt', 0)}: {event.data.get('error_type', '')}",
        }

    elif etype == "budget_exhausted":
        return {
            "type": "chain_warning",
            "text": "⚠️ الميزانية خلصت — الخطوات المتبقية اتخطت",
        }

    elif etype == "run_cancelled":
        return {
            "type": "chain_cancelled",
            "reason": event.data.get("reason", ""),
            "text": f"🛑 Chain ألغي: {event.data.get('reason', '')}",
        }

    elif etype == "run_finished":
        status = event.data.get("status", "")
        budget = event.data.get("budget", {})
        result = event.data.get("result", None)
        emoji = "✅" if status == "completed" else "❌"
        return {
            "type": "chain_finished",
            "status": status,
            "budget": budget,
            "result": result,
            "text": f"{emoji} Chain {status} ({budget.get('successful_calls', 0)} calls, "
                    f"{budget.get('elapsed_seconds', 0):.1f}s)",
        }

    elif etype == "run_error":
        return {
            "type": "chain_error",
            "error": event.data.get("error", ""),
            "text": f"💥 Chain error: {event.data.get('error', '')}",
        }

    return None


# ═══════════════════════════════════════════════════════
#   ChainBridge
# ═══════════════════════════════════════════════════════

class ChainBridge:
    """
    يربط chain system بـ server.py.

    Usage:
        bridge = ChainBridge(provider)
        bridge.start_chain(ws, user_request, file_content, file_path)
        # chain يعمل في thread منفصل
        # events تُرسل عبر WebSocket
        bridge.cancel()  # لو المستخدم أراد الإلغاء
    """

    def __init__(self, provider: BaseProvider,
                 project_root: str = "",
                 runs_dir: str | pathlib.Path | None = None,
                 action_applier: ActionApplier | None = None,
                 approval_gate: ApprovalGate | None = None,
                 ctx=None):
        """
        provider: المزود الحالي
        project_root: مجلد المشروع
        runs_dir: مجلد حفظ الـ runs (اختياري)
        approval_gate: ApprovalGate (T-012, R-104) — نقطة الموافقة الوحيدة
            قبل تطبيق نتائج السلسلة. بدونها **لا تطبيق إطلاقًا** — لا عودة
            للـ auto-apply الصامت.
        ctx: AppContext — لو موجود، project_root/runs_dir يُحلّان وقت الاستدعاء (R-102)
        """
        # R-102 (T-008): provider also resolves at call time via ctx —
        # api_switch_model publishes once on the context; no private pokes.
        self._static_provider = provider
        # R-102 (T-007) — pattern: "resolve at call time". With ctx set,
        # _project_root/_runs_dir are properties reading ctx.project.root per
        # access, so a project switch is observed by the next run. Static
        # values remain a fallback for ctx-less construction.
        # (provider stays a plain attribute until T-008 migrates the pokes.)
        self._ctx = ctx
        self._static_project_root = project_root
        self._explicit_runs_dir = pathlib.Path(runs_dir) if runs_dir else None
        self._orchestrator = SmartOrchestrator()
        self._agent_loader = AgentLoader()
        self._action_applier = action_applier
        self._approval_gate = approval_gate

        self._active_run: ChainRun | None = None
        self._active_thread: threading.Thread | None = None
        self._lock = threading.RLock()  # RLock: re-entrant (is_running called from start_chain)

    @property
    def _provider(self):
        if self._ctx is not None and self._ctx.active_provider is not None:
            return self._ctx.active_provider
        return self._static_provider

    @property
    def _project_root(self) -> str:
        if self._ctx is not None:
            return str(self._ctx.project.root)
        return self._static_project_root

    @property
    def _runs_dir(self) -> pathlib.Path:
        if self._explicit_runs_dir is not None:
            return self._explicit_runs_dir
        return pathlib.Path(self._project_root or ".") / ".ai_runs"

    @property
    def action_applier(self) -> ActionApplier | None:
        return self._action_applier

    @action_applier.setter
    def action_applier(self, val: ActionApplier | None):
        self._action_applier = val

    @property
    def approval_gate(self) -> ApprovalGate | None:
        return self._approval_gate

    @approval_gate.setter
    def approval_gate(self, val: ApprovalGate | None):
        self._approval_gate = val

    def resolve_approval(self, request_id: str, approved: bool,
                         payload_hash: str = "") -> bool:
        """تمرير رد المستخدم (من WS handler) للبوابة (T-012)."""
        if self._approval_gate is None:
            return False
        return self._approval_gate.resolve(request_id, approved, payload_hash)

    @property
    def is_running(self) -> bool:
        with self._lock:
            return (self._active_run is not None
                    and self._active_run.status == "running")

    @property
    def active_run(self) -> ChainRun | None:
        return self._active_run

    def start_chain(self, ws_send_fn,
                    user_request: str,
                    file_content: str | None = None,
                    file_path: str = "",
                    files: dict[str, str] | None = None,
                    force_strategy: str | None = None,
                    ticket: RunTicket | None = None) -> str:
        """
        يبدأ chain في thread منفصل.

        ws_send_fn: callable(dict) → يرسل JSON عبر WebSocket
        ticket: RunTicket (T-015, R-105) — تذكرة التنفيذ من ExecutionRegistry.
            تُمرّر للمنفّذ (إلغاء التذكرة يوقف السلسلة عند حد الخطوة التالي)
            وتُنهى هنا في finally بحالة الـ run النهائية.
        Returns: run_id
        """
        with self._lock:
            if self.is_running:
                ws_send_fn({
                    "type": "chain_error",
                    "text": "⚠️ في chain نشط حالياً. ألغيه أولاً.",
                })
                return ""

        # ── Create run ──
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        run = self._orchestrator.create_run(
            user_request=user_request,
            files=files,
            file_content=file_content,
            file_path=file_path,
            force_strategy=force_strategy,
            run_id=run_id,
        )

        # ── Snapshots ──
        run.provider_snapshot = ProviderSnapshot(
            provider_name=self._provider.name,
            model_name=getattr(self._provider, "model", None),
            configuration_hash="",
        )
        # R-305 (T-033): بصمات محتوى حقيقية أو لا لقطة إطلاقًا —
        # اللقطة الموجودة-والفارغة كانت تحققًا أجوف (راجع الخارطة).
        run.project_snapshot = _build_project_snapshot(
            self._project_root, files, file_path or "", file_content or "")

        # ── Run dir ──
        run_dir = self._runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # ── Store ──
        with self._lock:
            self._active_run = run

        # ── Event callback ──
        def on_event(event: ChainEvent):
            msg = _event_to_ws_message(event)
            if msg:
                try:
                    ws_send_fn(msg)
                except Exception:
                    pass

        # ── Execute in thread ──
        # T-012 (R-104): apply خرج من finally إلى مسار النجاح فقط (else)
        # وصار يمر عبر ApprovalGate. انهيار/فشل منتصف السلسلة ⇒ صفر كتابات.
        # الـ finally الآن ينظف الـ slot فقط — لا أثر جانبي على workspace.
        def _run_chain():
            try:
                executor = ChainExecutor(
                    self._provider,
                    self._agent_loader,
                    run_dir=str(run_dir),
                )
                executor.execute(run, on_event=on_event, ticket=ticket)
            except Exception:
                pass  # الركض فشل — لا تطبيق، التنظيف في finally
            else:
                if run.status == "completed":
                    try:
                        self._gated_apply(run, ws_send_fn)
                    except Exception:
                        pass  # فشل التطبيق لا يفجّر الـ thread
            finally:
                # T-015 (R-105): إنهاء تذكرة السجل بالحالة النهائية الفعلية
                # (تنظيف حالة فقط — لا أي كتابة للـ workspace هنا)
                if ticket is not None:
                    final = run.status if run.status in (
                        "completed", "failed", "cancelled") else "failed"
                    ticket.finish(final)
                with self._lock:
                    self._active_run = None

        thread = threading.Thread(target=_run_chain, daemon=True, name=f"chain-{run_id}")
        self._active_thread = thread
        thread.start()

        return run_id

    def _gated_apply(self, run: ChainRun, ws_send_fn) -> None:
        """T-012 (R-104): التطبيق الوحيد لنتائج السلسلة — عبر ApprovalGate فقط.

        يُستدعى حصراً من مسار النجاح (else) في _run_chain — غير قابل
        للوصول من أي مسار فشل. بدون بوابة: **stage فقط، صفر كتابات**
        (auto_execute:false يصبح صادقًا — لا عودة للـ auto-apply الصامت).
        """
        if self._action_applier is None:
            return

        # نتيجة الركض من الـ frozen snapshot (لا اعتماد على _active_run)
        frozen = run.get_frozen_result()
        result_text = None
        for step in reversed(run.steps):
            if step.stage == "execute" and step.status == "success":
                result_text = frozen.get_result(step.id)
                break
        if not result_text:
            for step in reversed(run.steps):
                if step.status == "success":
                    result_text = frozen.get_result(step.id)
                    break
        if not result_text:
            return

        # ما الذي سيُطبق؟ (parse بلا تطبيق)
        parsed = self._action_applier.get_parsed_actions(result_text)
        if not parsed:
            return  # لا أفعال في الرد — لا شيء يحتاج موافقة

        _KIND_MAP = {"create_file": "write", "edit_file": "edit",
                     "run_command": "command"}
        actions = [
            ProposedAction(
                kind=_KIND_MAP.get(a.get("action", ""), a.get("action", "?")),
                target=a.get("path", a.get("command", "")),
                payload=a.get("content", a.get("new_text", "")),
                summary=f"{a.get('action', '?')}: "
                        f"{a.get('path', a.get('command', ''))}",
            )
            for a in parsed
        ]

        def _safe_send(msg: dict) -> None:
            try:
                ws_send_fn(msg)
            except Exception:
                pass

        # بلا بوابة ⇒ stage فقط (الواجهة تعرض الأفعال؛ apply_action اليدوي متاح)
        if self._approval_gate is None:
            _safe_send({
                "type": "chain_actions_staged",
                "run_id": run.run_id,
                "actions_count": len(actions),
                "reason": "no_approval_gate",
            })
            return

        req = ApprovalRequest(actions=actions, source="chain",
                              run_id=run.run_id)

        def _emit_approval_frame(frame: dict) -> None:
            _safe_send({"type": "chain_approval_request", **frame})

        verdict = self._approval_gate.request(req,
                                              on_request=_emit_approval_frame)
        _safe_send({"type": "chain_approval_verdict", **verdict.to_dict()})

        if not verdict.approved:
            return  # مرفوض/مهلة/deny — صفر كتابات

        apply_result = self._action_applier.apply_step(
            step_id="mr_execute",
            ai_response=result_text,
            dry_run=False,
        )
        _safe_send({
            "type": "chain_apply_result",
            "run_id": run.run_id,
            **apply_result.to_dict(),
        })

    def cancel(self, reason: str = "User cancelled") -> bool:
        """إلغاء chain النشط"""
        with self._lock:
            if self._active_run and self._active_run.status == "running":
                self._active_run.cancellation_token.cancel(reason)
                return True
        return False

    def get_status(self) -> dict:
        """حالة chain النشط"""
        with self._lock:
            if not self._active_run:
                return {"active": False}

            run = self._active_run
            return {
                "active": True,
                "run_id": run.run_id,
                "status": run.status,
                "steps": [s.to_dict() for s in run.steps],
                "budget": run.budget.to_dict() if run.budget else {},
            }

    def get_final_result(self) -> str | None:
        """يرجع نتيجة آخر خطوة ناجحة"""
        with self._lock:
            run = self._active_run
        if not run:
            return None

        # Get immutable frozen result
        frozen = run.get_frozen_result()

        # آخر خطوة execute ناجحة
        for step in reversed(run.steps):
            if step.stage == "execute" and step.status == "success":
                return frozen.get_result(step.id)
        # أو آخر خطوة ناجحة
        for step in reversed(run.steps):
            if step.status == "success":
                return frozen.get_result(step.id)
        return None


# ═══════════════════════════════════════════════════════
#   Folder Scanner — قراءة مجلد كامل للـ chain
# ═══════════════════════════════════════════════════════

# امتدادات نصية آمنة للقراءة
# T-025 (R-204): ".env" حُذفت — كانت تقرأ مفاتيح حية داخل سياق
# السلسلة وتشحنها لمزودي موديلات طرف ثالث. الأسرار تُحجب أيضًا
# بفلتر is_secret_file في _collect_files (تحته) — راجع
# context/safe_reader.py للسياسة الكاملة وإجراء التجاوز.
_TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".json", ".yaml", ".yml", ".toml",
    ".py", ".sh", ".bat", ".ps1",
    ".md", ".txt", ".gitignore",
    ".svg", ".xml", ".vue", ".svelte",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".dart",
    ".sql", ".graphql", ".proto",
    ".dockerfile", ".tf", ".hcl",
}

# مجلدات يجب تجاهلها
_IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", ".cache", ".vscode", ".idea",
    "venv", ".venv", "env", ".env", ".tox",
    "target", "bin", "obj", ".gradle",
    ".ai_runs",  # مجلد الـ chain runs نفسه
}

# حدود
_MAX_FILE_SIZE = 200 * 1024   # 200KB per file
_MAX_TOTAL_SIZE = 2 * 1024 * 1024  # 2MB total
_MAX_FILES = 50


def scan_folder_for_chain(folder_path: str,
                          max_files: int = _MAX_FILES,
                          max_file_size: int = _MAX_FILE_SIZE,
                          max_total_size: int = _MAX_TOTAL_SIZE) -> dict[str, str]:
    """
    يقرأ مجلد كامل ويرجع {relative_path: content}.

    - يتجاهل مجلدات node_modules, .git, __pycache__ إلخ
    - يقرأ ملفات نصية فقط (WEB_EXTENSIONS + لغات برمجة)
    - حد أقصى 50 ملف / 200KB per file / 2MB total
    - يرتب الملفات بالأهمية (py/js/ts أولاً)

    Returns:
        dict: {relative_path: file_content}
        Empty dict if folder doesn't exist or no files found.
    """
    root = pathlib.Path(folder_path).resolve()
    if not root.is_dir():
        return {}

    files: dict[str, str] = {}
    total_size = 0

    # جمع كل الملفات المؤهلة
    candidates: list[pathlib.Path] = []
    _collect_files(root, root, candidates, max_files * 3)  # جمع أكتر وننقي بعدين

    # ترتيب بالأهمية: كود أولاً، config ثانياً، docs آخراً
    priority_ext = {".py": 0, ".js": 0, ".ts": 0, ".jsx": 0, ".tsx": 0,
                    ".vue": 0, ".svelte": 0, ".rs": 0, ".go": 0,
                    ".html": 1, ".css": 1, ".scss": 1,
                    ".json": 2, ".yaml": 2, ".yml": 2, ".toml": 2,
                    ".md": 3, ".txt": 3}

    candidates.sort(key=lambda p: (
        priority_ext.get(p.suffix.lower(), 2),
        len(str(p)),  # أقصر paths أولاً (أقرب للـ root)
    ))

    for file_path in candidates:
        if len(files) >= max_files:
            break

        try:
            size = file_path.stat().st_size
            if size > max_file_size or size == 0:
                continue
            if total_size + size > max_total_size:
                break

            content = file_path.read_text(encoding="utf-8", errors="replace")
            rel_path = str(file_path.relative_to(root)).replace("\\", "/")
            files[rel_path] = content
            total_size += size
        except (PermissionError, OSError, UnicodeDecodeError):
            continue

    return files


def _collect_files(root: pathlib.Path, current: pathlib.Path,
                   result: list, limit: int):
    """مسح recursive مع تجاهل المجلدات"""
    if len(result) >= limit:
        return
    try:
        for item in sorted(current.iterdir()):
            if len(result) >= limit:
                return
            if item.is_dir():
                name = item.name
                if name in _IGNORE_DIRS or name.startswith("."):
                    continue
                _collect_files(root, item, result, limit)
            elif item.is_file():
                if item.suffix.lower() in _TEXT_EXTENSIONS:
                    # T-025 (R-204): فلتر الأسرار عند الحدود — ملف سري
                    # لا يدخل قائمة المرشحين أصلًا (مثل keys.pem
                    # أو credentials.json رغم أن امتدادهما مسموح).
                    if is_secret_file(item):
                        continue
                    result.append(item)
    except PermissionError:
        pass


def get_folder_summary(folder_path: str) -> dict:
    """
    ملخص سريع عن مجلد (بدون قراءة المحتوى).
    """
    root = pathlib.Path(folder_path).resolve()
    if not root.is_dir():
        return {"exists": False}

    files: list[pathlib.Path] = []
    _collect_files(root, root, files, 200)

    ext_counts: dict[str, int] = {}
    total_size = 0
    for f in files:
        ext = f.suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        try:
            total_size += f.stat().st_size
        except OSError:
            pass

    return {
        "exists": True,
        "path": str(root),
        "name": root.name,
        "total_files": len(files),
        "total_size_kb": total_size // 1024,
        "extensions": dict(sorted(ext_counts.items(), key=lambda x: -x[1])),
        "can_chain": len(files) > 0,
    }

