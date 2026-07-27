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
from chain.bridge import ChainBridge
from chain.delegate import DelegateBridge

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
MAX_SMART_FILE_SIZE = 100 * 1024  # حد أقصى لحجم ملف يقرأه Smart Path (100KB)

# ── Chain System Infrastructure (M0 + M5) ──
_active_chain_run = None           # ChainRun النشط حالياً (None = مفيش)
_active_chain_lock = threading.Lock()  # حماية من تبديل الموديل/المشروع أثناء chain
chain_bridge: ChainBridge = None   # M5: جسر السلسلة → WebSocket
delegate_bridge: DelegateBridge = None  # M6: جسر التفويض

# ── تخزين مؤقت لطلبات المسارات المعلقة (v3.9) ──
pending_path_requests = {}
pending_path_lock = threading.Lock()

def _clean_expired_pending_requests():
    """تنظيف الطلبات التي انتهت صلاحيتها (5 دقائق) أو تجاوزت السعة القصوى (50 طلب)"""
    global pending_path_requests
    now = time.time()
    # 1. تنظيف بالوقت (TTL)
    expired = [rid for rid, req in pending_path_requests.items() if now - req["created_at"] > 300]
    for rid in expired:
        pending_path_requests.pop(rid, None)
    # 2. تنظيف بالحد الأقصى (الأقدم أولاً)
    if len(pending_path_requests) > 50:
        sorted_reqs = sorted(pending_path_requests.items(), key=lambda x: x[1]["created_at"])
        to_remove = len(pending_path_requests) - 50
        for i in range(to_remove):
            pending_path_requests.pop(sorted_reqs[i][0], None)

def _detect_external_directory(user_text: str):
    """يكتشف وجود مسار مجلد خارجي صالح وموجود في الرسالة ويعيد تفاصيل الماتش وموضع الحذف"""
    global fm
    import re
    # لا نبحث في المرفقات المدمجة
    text_to_search = user_text.split("\n\n[📎 ملفات مرفقة]:")[0].split("\n\n[📄 محتوى الملف:")[0]

    current_norm = os.path.normcase(os.path.realpath(str(fm.root))) if fm else ""

    def is_valid_project_path(p_clean):
        p = p_clean.strip().replace('\\', '/').rstrip('/')
        if p in ['', '/', '\\', '.', '..']:
            return False
        if re.match(r'^[A-Za-z]:$', p):
            return False
        return True

    # 1. البحث في التنصيص
    quoted_matches = list(re.finditer(r'["\']([^"\']+)["\']', text_to_search))
    for match in quoted_matches:
        p = match.group(1).strip()
        if is_valid_project_path(p):
            abs_p = os.path.normcase(os.path.realpath(p))
            if os.path.isdir(abs_p) and abs_p != current_norm:
                start, end = match.span()
                return {
                    "path": os.path.abspath(p),
                    "matched_text": match.group(0),
                    "start": start,
                    "end": end
                }

    # 2. البحث في مسارات Windows الكاملة
    win_matches = list(re.finditer(r'[A-Za-z]:[\\/][^\s,;"\'>]+', text_to_search))
    for match in win_matches:
        p = match.group(0).strip().rstrip('.,;?)')
        if is_valid_project_path(p):
            abs_p = os.path.normcase(os.path.realpath(p))
            if os.path.isdir(abs_p) and abs_p != current_norm:
                start, end = match.span()
                actual_len = len(p)
                return {
                    "path": os.path.abspath(p),
                    "matched_text": match.group(0)[:actual_len],
                    "start": start,
                    "end": start + actual_len
                }

    # 3. البحث في الكلمات الفردية
    for match in re.finditer(r'[^\s,;"\'>()\[\]{}]+', text_to_search):
        p = match.group(0).strip('.,;?()[]{}"\'')
        if is_valid_project_path(p):
            abs_p = os.path.normcase(os.path.realpath(p))
            if os.path.isdir(abs_p) and abs_p != current_norm:
                start, end = match.span()
                return {
                    "path": os.path.abspath(p),
                    "matched_text": p,
                    "start": start + match.group(0).find(p),
                    "end": start + match.group(0).find(p) + len(p)
                }

    return None


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
    global chat_history
    chat_history = []
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
    global chat_history
    if not session_mgr:
        return jsonify({"ok": False, "error": "Session manager not initialized"}), 500

    chat_history = []
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
    current = {
        "provider": getattr(provider, 'name', 'unknown') if provider else 'none',
        "model": provider.config.model if provider else '',
    }
    return jsonify({"ok": True, "providers": providers_list, "current": current})


@app.route("/api/switch-model", methods=["POST"])
def api_switch_model():
    """تغيير المزود/النموذج"""
    global provider

    # ── حماية: منع التبديل أثناء chain نشط ──
    with _active_chain_lock:
        if _active_chain_run is not None:
            return jsonify({
                "ok": False,
                "error": "لا يمكن تغيير المزود أثناء تشغيل chain نشط",
                "chain_run_id": getattr(_active_chain_run, 'run_id', 'unknown')
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
        print(f"✅ تم التغيير: {prov_id} / {model_name}")
        return jsonify({
            "ok": True,
            "provider": prov_id,
            "model": model_name,
            "message": f"تم التغيير لـ: {prov_id} / {model_name}"
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _switch_project_internal(new_path: str):
    """تقوم بتبديل مجلد المشروع بشكل مركزي وآمن مع الحماية وتحديث الـ Session والـ Bridges"""
    global fm, cmd_runner, session_mgr, chain_bridge
    abs_path = os.path.normcase(os.path.realpath(new_path))
    if not os.path.isdir(abs_path):
        raise ValueError(f"المسار ليس مجلداً صالحاً: {abs_path}")

    # حماية الـ Chain
    with _active_chain_lock:
        if _active_chain_run is not None:
            raise PermissionError("لا يمكن تغيير المشروع أثناء تشغيل Chain نشط!")

    # إنشاء الموارد محلياً للتأكد من نجاحها قبل الاستبدال (Atomic Swap)
    new_fm = FileManager(abs_path)
    new_cmd_runner = CommandRunner(cwd=abs_path, auto_approve=True)
    scan = new_fm.scan_project()

    # التبديل الذري
    fm = new_fm
    cmd_runner = new_cmd_runner

    if session_mgr:
        session_mgr.update_project_path(abs_path)

    if chain_bridge:
        chain_bridge._project_root = abs_path
        chain_bridge._runs_dir = pathlib.Path(abs_path) / ".ai_runs"

    return {
        "root": str(fm.root),
        "name": fm.root.name,
        "total_files": scan["total_files"],
        "total_size_kb": scan["total_size_kb"],
    }

def _read_folder_text_context(folder_path: str) -> str:
    """تقرأ الملفات النصية من المجلد الخارجي وتدمجها كـ Context مؤقت بحدود بايتات صارمة"""
    from pathlib import Path
    try:
        from actions.file_manager import WEB_EXTENSIONS
    except ImportError:
        WEB_EXTENSIONS = {'.py', '.js', '.html', '.css', '.json', '.md', '.txt'}

    context = []
    files_read = 0
    total_bytes = 0
    max_files = 10
    max_file_bytes = 20000
    max_total_bytes = 100000
    
    ignored_parts = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}

    paths_sorted = sorted(Path(folder_path).rglob("*"), key=lambda p: str(p))

    for p in paths_sorted:
        if files_read >= max_files or total_bytes >= max_total_bytes:
            break
        if p.is_file() and p.suffix.lower() in WEB_EXTENSIONS:
            # تجاهل المجلدات المهملة بصيغة casefold()
            if any(part.casefold() in [x.casefold() for x in p.parts] for part in ignored_parts):
                continue
            try:
                # قراءة الملف كـ Bytes أولاً للتحقق من الحجم
                file_size = p.stat().st_size
                read_size = min(file_size, max_file_bytes)
                with open(p, 'rb') as f:
                    content_bytes = f.read(read_size)
                
                content = content_bytes.decode('utf-8', errors='replace')
                rel_path = p.relative_to(Path(folder_path)).as_posix()
                file_text = f"📄 ملف: {rel_path}\n```\n{content}\n```"
                context.append(file_text)
                files_read += 1
                total_bytes += len(content_bytes)
            except Exception:
                pass
                
    return "\n\n".join(context) if context else "⚠️ لم يتم العثور على ملفات نصية صالحة في هذا المجلد لإرفاقها."

def _safe_ws_send(ws, payload: dict) -> bool:
    """يرسل رسالة JSON عبر الـ WebSocket بأمان — يمتص أي استثناء ناتج عن اتصال مقطوع
    (كحالة الإيقاف اليدوي أو انقطاع الشبكة) بدل تفجير خطأ في منتصف المعالجة."""
    try:
        ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False

def _process_ai_chat(ws, user_text, mode, project_switch_prefix="", extra_context="", ws_msg_queue=None, request_id=None):
    """تقوم بمعالجة الطلب بالكامل وإرساله للـ AI وإرجاع الردود بصورة نظيفة"""
    global chat_history, _backup_done_for_batch, fm, provider, session_mgr
    
    mentioned_files = []
    MAX_MENTIONED = 10
    try:
        import re
        from actions.file_manager import WEB_EXTENSIONS
        words = re.findall(r'[\w\-/\\]+(?:\.[\w]+)?', user_text)
        subpaths = re.findall(r'[\w\-]+/[\w\-]+(?:\.[\w]+)?', user_text)
        exact_names_to_search = set()
        stems_to_search = set()
        for w in words + subpaths:
            if '.' in w:
                exact_names_to_search.add(w.replace('\\', '/'))
            else:
                stem_w = w.split('/')[-1]
                if len(stem_w) >= 3 and not stem_w.isdigit() and stem_w not in ('the', 'and', 'for', 'من', 'في', 'على'):
                    stems_to_search.add(stem_w)

        for name in exact_names_to_search:
            basename = name.split('/')[-1] if '/' in name else name
            for p in fm.root.rglob(basename):
                if p.is_file() and p.suffix in WEB_EXTENSIONS:
                    rel_path = str(p.relative_to(fm.root)).replace("\\", "/")
                    if rel_path not in mentioned_files:
                        mentioned_files.append(rel_path)
            if len(mentioned_files) >= MAX_MENTIONED:
                break

        if len(mentioned_files) < MAX_MENTIONED:
            for stem in stems_to_search:
                for p in fm.root.rglob(f"*{stem}*"):
                    if p.is_file() and p.suffix in WEB_EXTENSIONS:
                        rel_path = str(p.relative_to(fm.root)).replace("\\", "/")
                        if rel_path not in mentioned_files:
                            mentioned_files.append(rel_path)
                            if len(mentioned_files) >= MAX_MENTIONED:
                                break
                if len(mentioned_files) >= MAX_MENTIONED:
                    break
    except Exception:
        pass

    user_text_with_files = user_text
    if mentioned_files:
        target_files_content = f"\n\n[✅ تم قراءة {len(mentioned_files)} ملف من المشروع]:"
        for f_path in mentioned_files[:MAX_MENTIONED]:
            try:
                content = fm.read_file(f_path, with_line_numbers=True)
                target_files_content += f"\n\n📄 **ملف: {f_path}**\n```\n{content}\n```"
            except Exception:
                pass
        user_text_with_files = user_text + target_files_content

    if extra_context:
        user_text_with_files += f"\n\n[📎 سياق مجلد خارجي مرفق للطلب]:\n{extra_context}"

    project_context = ""
    try:
        project_context = fm.get_project_context()
    except Exception:
        pass

    prompt = build_prompt(mode=mode, user_request=user_text_with_files, project_context=project_context)

    chat_history.append(Message(role="user", content=user_text))
    if session_mgr:
        session_mgr.append_message("user", user_text)

    system_prompt = get_system_prompt()
    _safe_ws_send(ws, {"type": "start", "request_id": request_id})

    full_response = ""
    if project_switch_prefix:
        _safe_ws_send(ws, {"type": "chunk", "request_id": request_id, "text": project_switch_prefix})
        full_response += project_switch_prefix

    try:
        import queue, threading
        chunk_queue = queue.Queue()
        cancel_event = threading.Event()
        
        def _stream_worker():
            try:
                for chunk in provider.stream(prompt, chat_history[:-1], system_prompt):
                    if cancel_event.is_set():
                        break
                    chunk_queue.put(("chunk", chunk))
                chunk_queue.put(("done", None))
            except Exception as e:
                chunk_queue.put(("error", str(e)))

        t = threading.Thread(target=_stream_worker, daemon=True)
        t.start()

        termination = None
        buffered_msgs = []
        while True:
            # التحقق من وجود رسالة إيقاف في الـ Queue القادمة من الـ WebSocket
            if ws_msg_queue is not None:
                try:
                    while not ws_msg_queue.empty():
                        ws_raw = ws_msg_queue.get_nowait()
                        if ws_raw is None:
                            termination = {"kind": "disconnected"}
                            cancel_event.set()
                            break
                        ws_data = json.loads(ws_raw)
                        if ws_data.get("type") == "stop":
                            ws_req_id = ws_data.get("request_id")
                            if ws_req_id == request_id:
                                _safe_ws_send(ws, {"type": "chunk", "request_id": request_id, "text": "\n\n🛑 [تم إيقاف التوليد بواسطة المستخدم]"})
                                cancel_event.set()
                                termination = {"kind": "stopped"}
                                break
                            else:
                                buffered_msgs.append(ws_raw)
                        else:
                            buffered_msgs.append(ws_raw)
                except queue.Empty:
                    pass

            if termination:
                break

            try:
                # نستخدم timeout قصير جداً (50ms) عشان اللوب يلف ويشيك على الـ WS queue
                msg_type, payload = chunk_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if msg_type == "chunk":
                full_response += payload
                if not _safe_ws_send(ws, {"type": "chunk", "request_id": request_id, "text": payload}):
                    termination = {"kind": "disconnected"}
                    cancel_event.set()
                    break
            elif msg_type == "done":
                break
            elif msg_type == "error":
                termination = {"kind": "error", "message": payload}
                cancel_event.set()
                break

        # إعادة الرسائل غير الـ stop المخزنة مؤقتاً إلى الـ queue بالترتيب الأصلي (FIFO)
        if ws_msg_queue is not None and buffered_msgs:
            for msg in buffered_msgs:
                ws_msg_queue.put(msg)

        if termination:
            kind = termination["kind"]
            if kind == "stopped":
                if full_response.strip():
                    chat_history.append(Message(role="assistant", content=full_response))
                    if session_mgr:
                        session_mgr.append_message("assistant", full_response)
                
                _safe_ws_send(ws, {
                    "type": "done",
                    "request_id": request_id,
                    "status": "stopped",
                    "partial": True,
                    "actions": [],
                    "options": [],
                    "summary": "تم إيقاف التوليد بواسطة المستخدم"
                })
            elif kind == "error":
                _safe_ws_send(ws, {
                    "type": "error",
                    "request_id": request_id,
                    "code": "provider_error",
                    "text": termination.get("message", "خطأ غير معروف في المزود"),
                    "retryable": False
                })
            elif kind == "disconnected":
                pass
            return

    except Exception as e:
        _safe_ws_send(ws, {
            "type": "error",
            "request_id": request_id,
            "code": "server_error",
            "text": str(e),
            "retryable": False
        })
        return

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
    _backup_done_for_batch = False

    if mode in ("plan", "build", "edit") and actions:
        _safe_ws_send(ws, {
            "type": "plan",
            "request_id": request_id,
            "status": "completed",
            "actions": actions,
            "options": options,
            "summary": parsed.summary()
        })
    else:
        _safe_ws_send(ws, {
            "type": "done",
            "request_id": request_id,
            "status": "completed",
            "actions": actions,
            "options": options,
            "summary": parsed.summary()
        })


@app.route("/api/switch-project", methods=["POST"])
def api_switch_project():
    """تغيير مسار المشروع"""
    data = request.get_json()
    new_path = data.get("path", "").strip()
    if not new_path:
        return jsonify({"ok": False, "error": "مسار فارغ"}), 400

    abs_path = os.path.abspath(new_path)
    if not os.path.isdir(abs_path):
        try:
            os.makedirs(abs_path, exist_ok=True)
        except Exception as e:
            return jsonify({"ok": False, "error": f"فشل إنشاء المجلد: {e}"}), 400

    try:
        proj_info = _switch_project_internal(abs_path)
        return jsonify({"ok": True, "project": proj_info})
    except PermissionError as pe:
        return jsonify({
            "ok": False,
            "error": str(pe),
            "chain_run_id": getattr(_active_chain_run, 'run_id', 'unknown')
        }), 409
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


def validate_attachment_files(files) -> tuple[bool, str]:
    if not isinstance(files, dict):
        return False, "تنسيق المرفقات غير صالح (يجب أن يكون Object)"
    
    if len(files) > 50:
        return False, "عدد الملفات يتجاوز الحد الأقصى المسموح به (50 ملف)"
        
    total_size = 0
    collision_registry = {}
    
    for path, content in files.items():
        if not isinstance(content, str):
            return False, f"محتوى الملف {path} غير صالح (يجب أن يكون نصياً)"
            
        # 1. تطبيع المسار
        norm_path = path.replace('\\', '/')
        import unicodedata
        norm_path = unicodedata.normalize('NFC', norm_path)
        
        # إزالة الشرطات المكررة وتنظيف الأطراف
        import re
        norm_path = re.sub(r'/+', '/', norm_path).strip()
        if norm_path.startswith('/'):
            norm_path = norm_path[1:]
        if norm_path.endswith('/'):
            norm_path = norm_path[:-1]
            
        # 2. فحص الأمان ومنع Path Traversal
        if (re.match(r'^[A-Za-z]:', norm_path) or 
            norm_path.startswith('/') or 
            '\0' in norm_path):
            return False, f"مسار ملف غير صالح أو مطلق: {path}"
            
        segments = norm_path.split('/')
        for segment in segments:
            if segment in ('.', '..'):
                return False, f"مسار غير آمن (يحتوي على .. أو .): {path}"
                
        # 3. التحقق من التعارض الهيكلي وتعارض الأسماء (Windows Case-insensitive)
        collision_key = norm_path.lower()
        if collision_key in collision_registry:
            return False, f"تعارض مسارات: الملف {norm_path} مكرر عبر المرفقات"
            
        # فحص التعارض الهيكلي (Prefix conflicts)
        for i in range(len(segments) - 1):
            parent_path = "/".join(segments[:i+1])
            parent_key = parent_path.lower()
            if parent_key in collision_registry:
                return False, f"تعارض هيكلي: المسار {parent_path} مستخدم كملف ومجلد معاً"
                
        for existing_key in collision_registry:
            if existing_key.startswith(collision_key + "/"):
                return False, f"تعارض هيكلي: المسار {norm_path} مستخدم كملف ومجلد معاً"
                
        # 4. حساب وفحص الحجم
        byte_size = len(content.encode('utf-8'))
        if byte_size > 200 * 1024 * 1024:
            return False, f"الملف {path} يتجاوز الحد الأقصى للملَف الواحد (200MB)"
            
        total_size += byte_size
        collision_registry[collision_key] = norm_path
        
    if total_size > 200 * 1024 * 1024:
        return False, "إجمالي حجم المرفقات يتجاوز الحد الأقصى المسموح به (200MB)"
        
    return True, ""


# ════════════════════════════════════════════════════
# WebSocket — AI Streaming
# ════════════════════════════════════════════════════
@sock.route("/ws")
def ws_handler(ws):
    """WebSocket للتواصل الحي مع AI — مع دعم الجلسات والخطط"""
    global chat_history, _backup_done_for_batch, fm, cmd_runner, delegate_bridge, chain_bridge

    ws_msg_queue = queue.Queue()

    def _recv_worker():
        while True:
            try:
                raw = ws.receive()
                if not raw:
                    ws_msg_queue.put(None)
                    break
                # T2.0.2: Limit WebSocket payload to 250MB (utf-8 bytes size)
                if isinstance(raw, str) and len(raw.encode('utf-8')) > 250 * 1024 * 1024:
                    try:
                        ws.send(json.dumps({
                            "type": "error",
                            "text": "حجم الرسالة يتجاوز الحد الأقصى المسموح به (250 ميجابايت)"
                        }, ensure_ascii=False))
                    except Exception:
                        pass
                    continue
                ws_msg_queue.put(raw)
            except Exception:
                ws_msg_queue.put(None)
                break

    recv_thread = threading.Thread(target=_recv_worker, daemon=True)
    recv_thread.start()

    while True:
        try:
            raw = ws_msg_queue.get()
            if raw is None:
                break
            data = json.loads(raw)
        except Exception:
            break

        msg_type = data.get("type", "")

        if msg_type == "ping":
            ws.send(json.dumps({"type": "pong"}))
            continue

        if msg_type == "confirm_path_action":
            req_id = data.get("request_id")
            action = data.get("action")
            
            if action not in ("switch", "attach", "continue"):
                ws.send(json.dumps({"type": "error", "text": "إجراء غير صالح"}))
                continue

            with pending_path_lock:
                req = pending_path_requests.get(req_id)
                
            if not req:
                ws.send(json.dumps({
                    "type": "confirm_path_failed",
                    "request_id": req_id,
                    "error": "طلب تأكيد غير صالح أو انتهت صلاحيته."
                }))
                continue

            if req.get("ws") != ws:
                ws.send(json.dumps({
                    "type": "confirm_path_failed",
                    "request_id": req_id,
                    "error": "غير مصرح لك بتأكيد هذا الطلب."
                }))
                continue

            detected_dir = req["path"]
            user_text = req["user_text"]
            mode = req["mode"]
            generation_request_id = req.get("generation_request_id")

            if action == "switch":
                try:
                    proj_info = _switch_project_internal(detected_dir)
                    
                    with pending_path_lock:
                        pending_path_requests.pop(req_id, None)

                    ws.send(json.dumps({
                        "type": "project_switched",
                        "project": proj_info
                    }))

                    # فحص إذا كان مسار فقط
                    match_info = _detect_external_directory(user_text)
                    is_path_only = False
                    if match_info:
                        clean_text = user_text[:match_info["start"]] + user_text[match_info["end"]:]
                        if not re.sub(r'[^\w\s]', '', clean_text).strip():
                            is_path_only = True

                    if is_path_only:
                        _safe_ws_send(ws, {"type": "start", "request_id": generation_request_id})
                        _safe_ws_send(ws, {
                            "type": "chunk",
                            "request_id": generation_request_id,
                            "text": f"حاضر يا صاحبي! أنا غيرت مجلد العمل دلوقتي للمجلد ده: `{detected_dir}` 📂\n\nلقيت فيه {proj_info['total_files']} ملف. تقدر تطلب مني أي حاجة بخصوصهم دلوقتي! 👍"
                        })
                        _safe_ws_send(ws, {
                            "type": "done",
                            "reason": "completed",
                            "request_id": generation_request_id,
                            "actions": [],
                            "options": [],
                            "summary": "Switched project directory"
                        })
                    else:
                        clean_query = user_text
                        if match_info:
                            clean_query = user_text[:match_info["start"]] + user_text[match_info["end"]:]
                        prefix = f"حاضر يا صاحبي! أنا غيرت مجلد العمل دلوقتي للمجلد ده: `{detected_dir}` 📂\n\nهجاوبك على سؤالك حالاً: 👇\n\n---\n\n"
                        _process_ai_chat(ws, user_text=clean_query, mode=mode, project_switch_prefix=prefix, ws_msg_queue=ws_msg_queue, request_id=generation_request_id)

                except PermissionError as pe:
                    ws.send(json.dumps({
                        "type": "confirm_path_failed",
                        "request_id": req_id,
                        "error": str(pe)
                    }))
                except Exception as e:
                    ws.send(json.dumps({
                        "type": "confirm_path_failed",
                        "request_id": req_id,
                        "error": f"فشل فتح المجلد: {e}"
                    }))
                    
            elif action == "attach":
                try:
                    extra_ctx = _read_folder_text_context(detected_dir)
                    
                    with pending_path_lock:
                        pending_path_requests.pop(req_id, None)

                    prefix = f"حاضر يا صاحبي! تم إرفاق سياق المجلد الخارجي للطلب الحالي... هجاوبك على سؤالك حالاً: 👇\n\n---\n\n"
                    _process_ai_chat(ws, user_text=user_text, mode=mode, project_switch_prefix=prefix, extra_context=extra_ctx, ws_msg_queue=ws_msg_queue, request_id=generation_request_id)
                except Exception as e:
                    ws.send(json.dumps({
                        "type": "confirm_path_failed",
                        "request_id": req_id,
                        "error": f"فشل إرفاق السياق: {e}"
                    }))
                
            elif action == "continue":
                with pending_path_lock:
                    pending_path_requests.pop(req_id, None)
                _process_ai_chat(ws, user_text=user_text, mode=mode, ws_msg_queue=ws_msg_queue, request_id=generation_request_id)
                
            continue

        if msg_type == "message":

            user_text = data.get("text", "").strip()
            mode = data.get("mode", "chat")
            project_switch_prefix = ""

            if not user_text:
                ws.send(json.dumps({"type": "error", "text": "رسالة فارغة"}))
                continue

            # ── 1. كشف ذكي للملفات والمجلدات (v3.9) ──
            import re
            detected_file = None
            
            # لا نبحث في المرفقات المدمجة لتفادي الكشف الخاطئ
            text_to_search = user_text.split("\n\n[📎 ملفات مرفقة]:")[0].split("\n\n[📄 محتوى الملف:")[0]

            def is_valid_project_path(p_clean):
                p = p_clean.strip().replace('\\', '/').rstrip('/')
                if p in ['', '/', '\\', '.', '..']:
                    return False
                if re.match(r'^[A-Za-z]:$', p):
                    return False
                return True

            # كشف المجلدات الخارجية باستخدام دالة الكشف الموضعي
            match_info = _detect_external_directory(user_text)
            
            # كشف الملفات (إذا لم يكن هناك مجلد مكتشف)
            if not match_info:
                quoted = re.findall(r'["\']([^"\']+)["\']', text_to_search)
                for p in quoted:
                    p_clean = p.strip()
                    if os.path.isfile(p_clean):
                        detected_file = os.path.abspath(p_clean)
                        break
                if not detected_file:
                    win_paths = re.findall(r'[A-Za-z]:[\\/][^\s,;"\'>]+', text_to_search)
                    for wp in win_paths:
                        wp = wp.strip().rstrip('.,;?)')
                        if os.path.isfile(wp):
                            detected_file = os.path.abspath(wp)
                            break
                if not detected_file:
                    for w in text_to_search.split():
                        w_clean = w.strip('.,;?()[]{}"\'')
                        if os.path.isfile(w_clean):
                            detected_file = os.path.abspath(w_clean)
                            break
                if not detected_file and os.path.isfile(user_text.strip()):
                    detected_file = os.path.abspath(user_text.strip())

            # معالجة ملف مكتشف: قراءة محتواه وإرفاقه
            if detected_file:
                try:
                    with open(detected_file, 'r', encoding='utf-8', errors='replace') as df:
                        file_content = df.read(MAX_SMART_FILE_SIZE)
                    file_ext = os.path.splitext(detected_file)[1]
                    user_text += f"\n\n[📄 محتوى الملف: {detected_file}]:\n```{file_ext.lstrip('.')}\n{file_content}\n```"
                except Exception:
                    pass

            # معالجة مجلد مكتشف: إرسال خيارات التأكيد بدلاً من التغيير التلقائي
            if match_info:
                detected_dir = match_info["path"]
                # تنظيف الطلبات القديمة
                _clean_expired_pending_requests()
                
                generation_request_id = data.get("request_id")
                request_id = str(uuid.uuid4())
                with pending_path_lock:
                    pending_path_requests[request_id] = {
                        "path": detected_dir,
                        "user_text": user_text,
                        "mode": mode,
                        "created_at": time.time(),
                        "ws": ws,
                        "generation_request_id": generation_request_id
                    }
                
                ws.send(json.dumps({
                    "type": "path_detected_options",
                    "request_id": request_id,
                    "path": detected_dir
                }))
                continue

            generation_request_id = data.get("request_id")
            # ── 2. معالجة طلب الـ AI والشات الموحد ──
            _process_ai_chat(ws, user_text=user_text, mode=mode, ws_msg_queue=ws_msg_queue, request_id=generation_request_id)


        elif msg_type == "apply_action":
            # تطبيق إجراء محدد (مع باك-أب تلقائي)
            action = data.get("action", {})
            result = _apply_single_action(action)
            ws.send(json.dumps({"type": "action_result", **result}))

        elif msg_type == "apply_all_actions":
            # تطبيق كل الإجراءات خطوة بخطوة
            actions = data.get("actions", [])
            _backup_done_for_batch = False
            total = len(actions)
            for i, action in enumerate(actions):
                # إرسال progress
                ws.send(json.dumps({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "running",
                }))
                result = _apply_single_action(action)
                ws.send(json.dumps({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "done" if result["ok"] else "error",
                    "message": result.get("message", ""),
                }))
                if not result["ok"]:
                    ws.send(json.dumps({
                        "type": "error",
                        "text": f"فشل في الخطوة {i+1}: {result.get('message', '')}"
                    }))
                    break

            _backup_done_for_batch = False
            ws.send(json.dumps({"type": "all_actions_done", "total": total}))

        elif msg_type == "execute_plan":
            # تنفيذ خطة معتمدة (نفس apply_all_actions)
            actions = data.get("actions", [])
            _backup_done_for_batch = False
            total = len(actions)
            for i, action in enumerate(actions):
                ws.send(json.dumps({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "running",
                }))
                result = _apply_single_action(action)
                ws.send(json.dumps({
                    "type": "task_progress",
                    "current": i + 1,
                    "total": total,
                    "action": action,
                    "status": "done" if result["ok"] else "error",
                    "message": result.get("message", ""),
                }))
                if not result["ok"]:
                    ws.send(json.dumps({
                        "type": "error",
                        "text": f"فشل في الخطوة {i+1}: {result.get('message', '')}"
                    }))
                    break

            _backup_done_for_batch = False
            ws.send(json.dumps({"type": "all_actions_done", "total": total}))

        # ═══════════════════════════════════════════
        #  M5: Chain System — WebSocket Handlers
        # ═══════════════════════════════════════════

        elif msg_type == "chain_message":
            # تشغيل chain ذكي (بديل لـ message العادية للمهام المعقدة)
            user_text = data.get("text", "").strip()
            if not user_text:
                ws.send(json.dumps({"type": "error", "text": "رسالة فارغة"}))
                continue

            force_strategy = data.get("strategy", None)  # اختياري

            # تحضير المحتوى
            file_content = data.get("file_content", None)
            file_path = data.get("file_path", "")
            folder_path = data.get("folder_path", "")  # مسار مجلد كامل
            files = data.get("files", None)  # {path: content}

            # T2.0.1: Server-side validation matching the client bounds
            if files is not None:
                ok, err_msg = validate_attachment_files(files)
                if not ok:
                    request_id = data.get("request_id")
                    ws.send(json.dumps({
                        "type": "error",
                        "request_id": request_id,
                        "text": f"❌ فشل التحقق من المرفقات على السيرفر: {err_msg}"
                    }, ensure_ascii=False))
                    continue

            # ── قراءة مجلد كامل ──
            if folder_path and os.path.isdir(folder_path):
                from chain.bridge import scan_folder_for_chain, get_folder_summary

                # ملخص أولاً
                summary = get_folder_summary(folder_path)
                ws.send(json.dumps({
                    "type": "folder_scanned",
                    "folder": summary,
                    "text": f"📂 تم مسح المجلد: {summary.get('name', '')} "
                            f"({summary.get('total_files', 0)} ملف، "
                            f"{summary.get('total_size_kb', 0)}KB)",
                }, ensure_ascii=False))

                # قراءة المحتوى
                files = scan_folder_for_chain(folder_path)

                if not files:
                    ws.send(json.dumps({
                        "type": "error",
                        "text": "المجلد فاضي أو مفيش ملفات نصية قابلة للقراءة",
                    }))
                    continue

            # ── قراءة ملف واحد ──
            elif not file_content and file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read(MAX_SMART_FILE_SIZE)
                except Exception:
                    pass

            if not chain_bridge:
                ws.send(json.dumps({"type": "error", "text": "Chain system غير مفعّل"}))
                continue

            request_id = data.get("request_id")
            def _ws_send(msg):
                if isinstance(msg, dict):
                    msg["request_id"] = request_id
                try:
                    ws.send(json.dumps(msg, ensure_ascii=False))
                except Exception:
                    pass

            run_id = chain_bridge.start_chain(
                ws_send_fn=_ws_send,
                user_request=user_text,
                file_content=file_content,
                file_path=file_path,
                files=files,
                force_strategy=force_strategy,
            )

            if not run_id:
                # start_chain already sent error via _ws_send
                pass

        elif msg_type == "chain_cancel":
            # إلغاء chain نشط
            reason = data.get("reason", "User cancelled")
            request_id = data.get("request_id")
            if chain_bridge:
                ok = chain_bridge.cancel(reason)
                _safe_ws_send(ws, {
                    "type": "chain_cancel_result",
                    "request_id": request_id,
                    "ok": ok,
                    "text": "تم إلغاء السلسلة" if ok else "مفيش سلسلة نشطة",
                })
            else:
                _safe_ws_send(ws, {
                    "type": "error",
                    "request_id": request_id,
                    "text": "Chain system غير مفعّل"
                })

        elif msg_type == "chain_status":
            # حالة chain النشط
            if chain_bridge:
                status = chain_bridge.get_status()
                ws.send(json.dumps({"type": "chain_status", **status}))
            else:
                ws.send(json.dumps({"type": "chain_status", "active": False}))

        # ── M6: Delegate System ──
        elif msg_type == "delegate_message":
            # تفويض مهمة معقدة
            user_text = data.get("text", "").strip()
            if not user_text:
                ws.send(json.dumps({"type": "error", "text": "الرسالة فارغة"}))
                continue

            if not delegate_bridge:
                delegate_bridge = DelegateBridge(provider)

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

            def delegate_event_handler(event_type, event_data):
                try:
                    ws.send(json.dumps({
                        "type": event_type,
                        **event_data,
                    }))
                except Exception:
                    pass

            # تشغيل في thread منفصل
            def run_delegate():
                try:
                    delegate_bridge.run_delegation(
                        user_request=user_text,
                        files_context=files_context,
                        project_context=project_context,
                        on_event=delegate_event_handler,
                    )
                except Exception as e:
                    try:
                        ws.send(json.dumps({
                            "type": "delegate_error",
                            "error": str(e),
                        }))
                    except Exception:
                        pass

            t = threading.Thread(target=run_delegate, daemon=True)
            t.start()

        elif msg_type == "delegate_approve":
            # المستخدم وافق على التعديلات
            if delegate_bridge and delegate_bridge.is_active:
                def approval_handler(et, ed):
                    try:
                        ws.send(json.dumps({"type": et, **ed}))
                    except Exception:
                        pass

                landed = delegate_bridge.land(on_event=approval_handler)
                if landed and delegate_bridge.current_run:
                    # أرسل الرد للمعالجة العادية
                    run = delegate_bridge.current_run
                    if run.result:
                        ws.send(json.dumps({
                            "type": "start",
                        }))
                        ws.send(json.dumps({
                            "type": "chunk",
                            "text": run.result.response,
                        }))
                        # تحليل الأكشنز
                        try:
                            actions = parser.extract_actions(run.result.response)
                            options = parser.extract_options(run.result.response)
                            ws.send(json.dumps({
                                "type": "done",
                                "actions": actions,
                                "options": options,
                                "summary": f"✅ تم اعتماد التعديلات (delegation #{run.run_id})",
                            }))
                        except Exception:
                            ws.send(json.dumps({
                                "type": "done",
                                "actions": [],
                                "options": [],
                                "summary": f"✅ تم اعتماد التعديلات",
                            }))
            else:
                ws.send(json.dumps({"type": "error", "text": "لا يوجد تفويض نشط"}))

        elif msg_type == "delegate_reject":
            # المستخدم رفض التعديلات
            reason = data.get("reason", "")
            if delegate_bridge and delegate_bridge.is_active:
                delegate_bridge.reject(reason, on_event=lambda et, ed: ws.send(
                    json.dumps({"type": et, **ed})
                ))
            else:
                ws.send(json.dumps({"type": "error", "text": "لا يوجد تفويض نشط"}))


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
    global fm, cmd_runner, provider, session_mgr, chain_bridge

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

    # ── Chain Bridge (M5) ──
    chain_bridge = ChainBridge(
        provider=provider,
        project_root=project_path,
    )
    print(f"  🔗 Chain System: active")

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
