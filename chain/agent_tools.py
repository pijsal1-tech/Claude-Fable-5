# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🔧 AgentTools — أدوات الـ Agent
  
  كل أداة تُنفذ محلياً وترجع النتيجة كنص.
  الأوامر (run_command) تحتاج موافقة المستخدم.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import logging
import os
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FuturesTimeout
from dataclasses import dataclass, field
from typing import Callable
from chain.path_policy import resolve_workspace_path, is_secret_file
from core.execution import RunTicket
import hashlib
import json

_LOG = logging.getLogger("chain.agent_tools")

def compute_payload_hash(tool: str, args: dict, cwd: str, env: dict | None) -> str:
    # Sort keys for deterministic serialization
    args_json = json.dumps(args or {}, sort_keys=True)
    env_json = json.dumps(env or {}, sort_keys=True)
    payload_str = f"{tool}||{args_json}||{cwd}||{env_json}"
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

# أنواع الأدوات: safe = تنفيذ فوري, approval = تحتاج موافقة
SAFE_TOOLS = {"read_file", "list_dir", "search_code", "get_file_info", "get_project_tree"}
APPROVAL_TOOLS = {"run_command"}
ALL_TOOLS = SAFE_TOOLS | APPROVAL_TOOLS


# ═══════════════ سياسة أوامر الـ Agent (T-058 / R-504) ═══════════════

DEFAULT_COMMAND_TIMEOUT = 60.0       # ثوانٍ — مهلة تنفيذ الأمر الواحد
DEFAULT_OUTPUT_MAX_CHARS = 8000      # سقف كل مجرى مخرجات (stdout/stderr)
_TIMEOUT_GRACE_SECONDS = 2.0         # سماحية فوق مهلة subprocess قبل التخلي
_CANCEL_POLL_SECONDS = 0.05          # فترة استطلاع إلغاء التذكرة


@dataclass(frozen=True)
class CommandPolicy:
    """سياسة تنفيذ run_command — القائمة ملكية المشروع لا الـ agent.

    R-504: الـ allowlist تأتي من config.yaml حصريًا؛ الـ agent لا يختار
    أوامره الحرة أبدًا. ``enforce=False`` (قسم config غائب / بناء بلا
    سياسة) = وضع legacy: بوابة الموافقة وحدها تحكم (سلوك ما قبل T-058).
    ``enforce=True`` مع قائمة فارغة = رفض كل الأوامر (إغلاق صريح).

    ملاحظة: الـ allowlist طبقة **إضافية** فوق ApprovalGate (T-013) —
    لا تتجاوزها؛ أمر مسموح لا يزال يحتاج موافقة المستخدم.
    """

    enforce: bool = False
    allowlist: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT
    output_max_chars: int = DEFAULT_OUTPUT_MAX_CHARS

    def resolve(self, command: str) -> tuple[str, str] | None:
        """مطابقة الطلب مع القائمة — بنص الأمر الحرفي أو باسم المدخل.

        المطابقة بعد توحيد الفراغات (لا مطابقة جزئية/بادئة — أمر يبدأ
        بنص مسموح ليس مسموحًا). ترجع (اسم المدخل، الأمر المُحلّ) أو None.
        """
        requested = " ".join((command or "").split())
        if not requested:
            return None
        for name, allowed in self.allowlist.items():
            normalized = " ".join(allowed.split())
            if requested == normalized or requested == name:
                return name, normalized
        return None


def command_policy_from(cfg: dict | None) -> CommandPolicy:
    """قراءة ``cfg["agent"]`` — تسامحية في الأنواع، صارمة في الدلالة.

    قسم ``command_allowlist`` غائب أو ليس dict ⇒ ``enforce=False``
    (legacy). موجود ⇒ ``enforce=True`` بالمداخل النصية الصالحة فقط
    (قيم فارغة/غير نصية تُسقط — قائمة أقصر أأمن من قائمة أوسع).
    """
    section = (cfg or {}).get("agent") or {}
    if not isinstance(section, dict):
        return CommandPolicy()
    raw = section.get("command_allowlist")
    if not isinstance(raw, dict):
        return CommandPolicy()
    entries = {
        str(k): v.strip()
        for k, v in raw.items()
        if isinstance(k, str) and isinstance(v, str) and v.strip()
    }
    timeout = section.get("command_timeout_seconds", DEFAULT_COMMAND_TIMEOUT)
    cap = section.get("command_output_max_chars", DEFAULT_OUTPUT_MAX_CHARS)
    return CommandPolicy(
        enforce=True,
        allowlist=entries,
        timeout_seconds=(
            float(timeout)
            if isinstance(timeout, (int, float))
            and not isinstance(timeout, bool) and timeout > 0
            else DEFAULT_COMMAND_TIMEOUT
        ),
        output_max_chars=(
            int(cap)
            if isinstance(cap, int) and not isinstance(cap, bool) and cap > 0
            else DEFAULT_OUTPUT_MAX_CHARS
        ),
    )


@dataclass
class ToolCall:
    """طلب أداة مستخرج من رد AI"""
    tool: str
    args: dict
    reason: str = ""  # سبب (مطلوب لـ run_command)
    
    @property
    def needs_approval(self) -> bool:
        return self.tool in APPROVAL_TOOLS
    
    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "reason": self.reason,
            "needs_approval": self.needs_approval,
        }


class AgentTools:
    """
    تنفيذ الأدوات المتاحة للـ Agent.
    
    Args:
        file_manager: FileManager instance
        command_runner: CommandRunner instance (optional)
        project_root: مسار المشروع
    """
    
    def __init__(self, file_manager=None, command_runner=None,
                 project_root: str = ".", ctx=None,
                 command_policy: CommandPolicy | None = None,
                 checkpoint=None):
        # R-102 (T-007) — pattern: "resolve at call time".
        # When ctx (AppContext) is provided, fm/cmd/project_root are
        # properties resolving ctx.project.* on EVERY access — never cached —
        # so a project switch is observed immediately. The static values are
        # only a fallback for ctx-less construction (tests / legacy).
        self._ctx = ctx
        self._static_fm = file_manager
        self._static_cmd = command_runner
        self._static_root = str(project_root)
        self._max_file_size = 100 * 1024  # 100KB
        self._max_dir_depth = 3
        # T-058 (R-504): سياسة الأوامر — بلا سياسة = legacy (لا فرض allowlist)
        self.command_policy = command_policy or CommandPolicy()
        # T-058: تذكرة التنفيذ الحالية — يضبطها AgentLoop.run قبل كل تشغيل؛
        # tool_run_command يستطلع is_cancelled أثناء الأمر الطويل.
        self.run_ticket: RunTicket | None = None
        # T-059 (R-504/R-106): CheckpointManager — كتابات الأوامر الجانبية
        # (autoformatter مثلاً) تُلتقط snapshot قبل الأمر وseal بعده —
        # لا مسار طفرة بلا بوابة: الأمر نفسه لا يصل هنا إلا بعد موافقة
        # ApprovalGate (T-013)، وآثاره على الملفات قابلة للاستعادة (T-053).
        self._checkpoint = checkpoint

    # حدود مسح الملفات قبل/بعد الأمر (T-059) — مشاريع أكبر من
    # السقف تفقد التغطية للزائد فقط (لا فشل) — موثّق في docstring.
    _CKPT_MAX_FILES = 400
    _CKPT_MAX_FILE_BYTES = 512 * 1024
    _CKPT_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv",
                       "venv", ".ai_runs", ".next", "dist", ".cache",
                       ".idea", ".vscode"}

    @property
    def fm(self):
        if self._ctx is not None:
            return self._ctx.project.fm
        return self._static_fm

    @property
    def cmd(self):
        if self._ctx is not None:
            return self._ctx.project.cmd_runner
        return self._static_cmd

    @property
    def project_root(self) -> str:
        if self._ctx is not None:
            return str(self._ctx.project.root)
        return self._static_root
    
    def execute(self, call: ToolCall) -> str:
        """تنفيذ أداة — يرجع النتيجة كنص"""
        handler = self._handlers.get(call.tool)
        if not handler:
            return f"❌ أداة غير معروفة: {call.tool}"
        try:
            return handler(self, **call.args)
        except Exception as e:
            return f"❌ خطأ في {call.tool}: {e}"
    
    # ──── الأدوات ────
    
    def tool_read_file(self, path: str, start_line: int = 0,
                       end_line: int = 0) -> str:
        """قراءة ملف — مع دعم نطاق سطور"""
        try:
            resolved = self._resolve_path(path)
        except PermissionError as e:
            return f"❌ خطأ: {e}"
        if not resolved:
            return f"❌ ملف غير موجود: {path}"
        
        try:
            content = pathlib.Path(resolved).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"❌ فشل قراءة {path}: {e}"
        
        # حد الحجم
        if len(content) > self._max_file_size:
            content = content[:self._max_file_size] + \
                f"\n... (تم اقتطاع الملف — {len(content)} حرف إجمالي)"
        
        # نطاق سطور
        if start_line > 0 or end_line > 0:
            lines = content.split("\n")
            s = max(0, start_line - 1)
            end_idx = end_line if end_line > 0 else len(lines)
            selected = lines[s:end_idx]
            # أرقام السطور
            numbered = []
            for i, line in enumerate(selected, start=s + 1):
                numbered.append(f"{i:4d}: {line}")
            return "\n".join(numbered)
        
        return content
    
    def tool_list_dir(self, path: str = ".", depth: int = 2) -> str:
        """استعراض محتويات مجلد"""
        try:
            resolved = self._resolve_path(path)
        except PermissionError as e:
            return f"❌ خطأ: {e}"
        if not resolved or not os.path.isdir(resolved):
            return f"❌ مجلد غير موجود: {path}"
        
        depth = min(depth, self._max_dir_depth)
        lines: list[str] = []
        self._tree(resolved, "", depth, lines, max_items=200)
        
        if not lines:
            return f"(مجلد فارغ: {path})"
        return "\n".join(lines)
    
    def tool_search_code(self, query: str, path: str = ".",
                         max_results: int = 20) -> str:
        """بحث في الكود (مثل grep)"""
        try:
            resolved = self._resolve_path(path)
        except PermissionError as e:
            return f"❌ خطأ: {e}"
        if not resolved:
            return f"❌ مسار غير موجود: {path}"
        
        results = []
        search_path = pathlib.Path(resolved)
        
        # ملفات النص فقط
        text_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
            ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg",
            ".sh", ".bat", ".ps1", ".env", ".gitignore",
        }
        
        files = []
        if search_path.is_file():
            if is_secret_file(search_path):
                return "❌ الوصول مرفوض: ملف محمي"
            files = [search_path]
        else:
            for ext in text_exts:
                files.extend(search_path.rglob(f"*{ext}"))
        
        for fpath in files:
            # تخطي node_modules, .git, __pycache__
            parts = fpath.parts
            if any(p in (".git", "node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue
            if is_secret_file(fpath):
                continue
            
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.split("\n"), 1):
                    if query.lower() in line.lower():
                        rel = fpath.relative_to(search_path) if search_path.is_dir() else fpath.name
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= max_results:
                            break
            except Exception:
                continue
            
            if len(results) >= max_results:
                break
        
        if not results:
            return f"(لا نتائج لـ '{query}' في {path})"
        return "\n".join(results)
    
    def tool_get_file_info(self, path: str) -> str:
        """معلومات ملف — حجم، نوع، تاريخ"""
        try:
            resolved = self._resolve_path(path)
        except PermissionError as e:
            return f"❌ خطأ: {e}"
        if not resolved or not os.path.exists(resolved):
            return f"❌ غير موجود: {path}"
        
        stat = os.stat(resolved)
        is_dir = os.path.isdir(resolved)
        
        info = []
        info.append(f"المسار: {path}")
        info.append(f"النوع: {'مجلد' if is_dir else 'ملف'}")
        info.append(f"الحجم: {stat.st_size:,} bytes")
        
        import time
        info.append(f"آخر تعديل: {time.ctime(stat.st_mtime)}")
        
        if is_dir:
            try:
                count = len(os.listdir(resolved))
                info.append(f"المحتويات: {count} عنصر")
            except Exception:
                pass
        else:
            ext = pathlib.Path(resolved).suffix
            info.append(f"الامتداد: {ext}")
            # عدد السطور
            try:
                lines = pathlib.Path(resolved).read_text(
                    encoding="utf-8", errors="replace"
                ).count("\n")
                info.append(f"السطور: {lines + 1}")
            except Exception:
                pass
        
        return "\n".join(info)
    
    def tool_get_project_tree(self, max_depth: int = 3) -> str:
        """شجرة المشروع كاملة"""
        return self.tool_list_dir(".", depth=max_depth)
    
    def tool_run_command(self, command: str, reason: str = "") -> str:
        """تنفيذ أمر في Terminal — موافقة + allowlist (T-058 / R-504).

        المسار: فحص allowlist (فرضها من config — رفض مهيكل ومسجَّل، لا
        تنفيذ صامت أبدًا) → تنفيذ عبر cmd_runner في خيط عامل مع استطلاع
        إلغاء RunTicket ومهلة قصوى → التقاط stdout/stderr/exit code
        بسقف حجم. نمط المهلة نمط T-057: بلا ``with ThreadPoolExecutor``
        (خروجه ينتظر الخيط البطيء فيهزم المهلة) — ``shutdown(wait=False)``.
        """
        if not self.cmd:
            return "❌ CommandRunner غير متاح"

        policy = self.command_policy
        entry_name = ""
        actual = command
        if policy.enforce:
            resolved = policy.resolve(command)
            if resolved is None:
                entries = ", ".join(sorted(policy.allowlist)) or "(فارغة)"
                _LOG.warning(
                    "run_command REJECTED (not allowlisted): %r — "
                    "available entries: %s", command, entries)
                return (
                    "❌ أمر مرفوض — غير موجود في قائمة الأوامر المسموحة "
                    "(agent.command_allowlist في config.yaml).\n"
                    f"الأمر المطلوب: {command}\n"
                    f"المداخل المتاحة: {entries}"
                )
            entry_name, actual = resolved
            _LOG.info("run_command allowed via entry %r: %r",
                      entry_name, actual)

        # ── T-059 (R-106): snapshot ما-قبل-الأمر — كتابات الأمر الجانبية
        # (منسّق تلقائي، سكريبت بناء...) تصبح قابلة للاستعادة مثل أي
        # كتابة agent أخرى. blobs مُعنونة بالمحتوى ⇒ التكرار شبه مجاني.
        ticket0 = self.run_ticket
        ckpt_run_id = ticket0.run_id if ticket0 is not None else ""
        pre_sigs: dict[str, tuple[int, int]] | None = None
        if self._checkpoint is not None and ckpt_run_id:
            try:
                pre_sigs = self._workspace_signatures()
                if pre_sigs:
                    self._checkpoint.snapshot(ckpt_run_id,
                                              sorted(pre_sigs))
            except Exception:
                _LOG.exception("pre-command checkpoint failed — "
                               "continuing without side-effect capture")
                pre_sigs = None

        pool = ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(
                self.cmd.run, actual,
                need_approval=False,
                timeout=int(max(1, policy.timeout_seconds)),
                retries=0,
            )
            deadline = (time.monotonic() + policy.timeout_seconds
                        + _TIMEOUT_GRACE_SECONDS)
            while True:
                try:
                    result = future.result(timeout=_CANCEL_POLL_SECONDS)
                    break
                except _FuturesTimeout:
                    ticket = self.run_ticket
                    if ticket is not None and ticket.is_cancelled:
                        _LOG.warning(
                            "run_command cancelled via RunTicket %s: %r",
                            ticket.run_id, actual)
                        return (f"❌ أُلغي الأمر (تذكرة التنفيذ أُلغيت): "
                                f"{actual}")
                    if time.monotonic() >= deadline:
                        _LOG.warning("run_command timeout after %.1fs: %r",
                                     policy.timeout_seconds, actual)
                        return (f"❌ انتهت مهلة الأمر "
                                f"({policy.timeout_seconds:g}s): {actual}")
        except Exception as e:
            return f"❌ خطأ: {e}"
        finally:
            pool.shutdown(wait=False)

        report = self._format_command_result(
            actual, entry_name, result, policy.output_max_chars)

        # ── T-059: seal ما-بعد-الأمر للملفات التي غيّرها الأمر ──
        if pre_sigs is not None and self._checkpoint is not None:
            try:
                changed = self._changed_paths(pre_sigs)
                if changed:
                    self._checkpoint.seal(ckpt_run_id, changed)
                    _LOG.info("run_command side-effects checkpointed: "
                              "%d file(s) under run %s",
                              len(changed), ckpt_run_id)
                    report += (f"\n🧷 [checkpoint]: الأمر غيّر "
                               f"{len(changed)} ملف — قابلة للاستعادة "
                               f"(run: {ckpt_run_id})")
            except Exception:
                _LOG.exception("post-command seal failed")
        return report

    def _workspace_signatures(self) -> dict[str, tuple[int, int]]:
        """مسح محدود لملفات المشروع: مسار ← (size, mtime_ns).

        حدود: تخطي مجلدات الضجيج، سقف عدد وحجم — مشروع أكبر من
        السقف يفقد تغطية الزائد فقط (الخطر المتبقي موثّق، لا فشل).
        """
        sigs: dict[str, tuple[int, int]] = {}
        root = self.project_root
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in self._CKPT_SKIP_DIRS]
            for name in filenames:
                if len(sigs) >= self._CKPT_MAX_FILES:
                    return sigs
                full = os.path.join(dirpath, name)
                if is_secret_file(pathlib.Path(full)):
                    continue
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if st.st_size > self._CKPT_MAX_FILE_BYTES:
                    continue
                sigs[full] = (st.st_size, st.st_mtime_ns)
        return sigs

    def _changed_paths(self, pre: dict[str, tuple[int, int]]) -> list[str]:
        """مقارنة بعدية: مُعدّل + جديد + محذوف (كلها طفرات تُختم)."""
        post = self._workspace_signatures()
        changed = [p for p, sig in post.items() if pre.get(p) != sig]
        changed.extend(p for p in pre if p not in post)  # محذوف
        return sorted(changed)

    def _format_command_result(self, command: str, entry_name: str,
                               result: dict, max_chars: int) -> str:
        """تقرير نتيجة مهيكل: الأمر + exit code + مخرجات مسقوفة الحجم."""
        stdout = self._cap_output(str(result.get("output") or ""), max_chars)
        stderr = self._cap_output(str(result.get("error") or ""), max_chars)
        code = result.get("code", -1)
        header = f"$ {command}"
        if entry_name:
            header += f"  [allowlist: {entry_name}]"
        parts = [header, f"exit code: {code}"]
        if stdout:
            parts.append(f"── stdout ──\n{stdout}")
        if stderr:
            parts.append(f"── stderr ──\n{stderr}")
        if not stdout and not stderr:
            parts.append("(لا مخرجات)")
        body = "\n".join(parts)
        if result.get("success"):
            return body
        return "❌ فشل الأمر:\n" + body

    @staticmethod
    def _cap_output(text: str, max_chars: int) -> str:
        """سقف حجم مجرى مخرجات واحد — مع علامة اقتطاع صريحة."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + f"\n... (اقتُطع — {len(text)} حرف إجمالي)"
    
    # ──── مساعدات ────
    
    def _resolve_path(self, path: str) -> str | None:
        """تحويل مسار نسبي لمسار كامل ضمن المشروع"""
        try:
            resolved = resolve_workspace_path(self.project_root, path, must_exist=False, allow_symlinks=False)
            if resolved.exists():
                return str(resolved)
        except PermissionError:
            raise
        except Exception:
            pass
        return None
    
    def _tree(self, root: str, prefix: str, depth: int,
              lines: list, max_items: int = 200):
        """بناء شجرة مجلد"""
        if depth <= 0 or len(lines) >= max_items:
            return
        
        try:
            entries = sorted(os.listdir(root))
        except PermissionError:
            return
        
        # تخطي المجلدات المخفية والمشهورة
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv",
                ".next", ".cache", "dist", ".idea", ".vscode"}
        entries = [e for e in entries if e not in skip and not is_secret_file(pathlib.Path(root) / e)]
        
        dirs = [e for e in entries if os.path.isdir(os.path.join(root, e))]
        files = [e for e in entries if not os.path.isdir(os.path.join(root, e))]
        
        for f in files:
            if len(lines) >= max_items:
                lines.append(f"{prefix}... (تم الاقتطاع)")
                return
            lines.append(f"{prefix}📄 {f}")
        
        for d in dirs:
            if len(lines) >= max_items:
                lines.append(f"{prefix}... (تم الاقتطاع)")
                return
            lines.append(f"{prefix}📁 {d}/")
            self._tree(
                os.path.join(root, d),
                prefix + "  ",
                depth - 1,
                lines,
                max_items,
            )
    
    # ──── تسجيل الأدوات ────
    
    _handlers: dict[str, Callable[..., str]] = {
        "read_file": tool_read_file,
        "list_dir": tool_list_dir,
        "search_code": tool_search_code,
        "get_file_info": tool_get_file_info,
        "get_project_tree": tool_get_project_tree,
        "run_command": tool_run_command,
    }


def parse_tool_calls(ai_response: str) -> list[ToolCall]:
    """
    استخراج tool calls من رد AI مع تجنب أي استدعاءات داخل بلوكات كود ( ``` )
    """
    if not ai_response:
        return []
        
    lines = ai_response.splitlines()
    in_code_fence = False
    calls = []
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Check code fence toggle
        # It is a code fence if it starts with ``` but NOT ```TOOL:
        if line.startswith("```"):
            if line.startswith("```TOOL:"):
                pass
            else:
                in_code_fence = not in_code_fence
                i += 1
                continue
                
        if in_code_fence:
            if line.startswith("```TOOL:"):
                i += 1
                while i < len(lines):
                    sub_line = lines[i].rstrip()
                    if sub_line.strip() == "```":
                        i += 1
                        break
                    i += 1
                continue
            i += 1
            continue
            
        # Look for tool block start
        if line.startswith("```TOOL:") or line.startswith("TOOL:"):
            is_ticked = line.startswith("```")
            if is_ticked:
                tool_name = line[8:].strip()
            else:
                tool_name = line[5:].strip()
                
            if not tool_name:
                i += 1
                continue
                
            body_lines = []
            i += 1
            
            while i < len(lines):
                sub_line = lines[i].rstrip()
                if is_ticked:
                    if sub_line.strip() == "```":
                        i += 1
                        break
                    if sub_line.startswith("```TOOL:") or sub_line.startswith("TOOL:"):
                        break
                else:
                    if not sub_line.strip():
                        i += 1
                        break
                    if sub_line.startswith("TOOL:") or sub_line.startswith("```"):
                        break
                        
                body_lines.append(sub_line)
                i += 1
                
            if tool_name in ALL_TOOLS:
                args, reason = _parse_args_body("\n".join(body_lines))
                calls.append(ToolCall(tool=tool_name, args=args, reason=reason))
            continue
            
        i += 1
        
    return calls


def _parse_args_body(body: str) -> tuple[dict, str]:
    args: dict[str, int | str] = {}
    reason = ""
    for line in body.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if key == "reason":
            reason = val
        else:
            if val.isdigit():
                args[key] = int(val)
            else:
                args[key] = val
    return args, reason


def has_tool_calls(ai_response: str) -> bool:
    """فحص سريع كود-فنس-أوير — هل الرد يحتوي tool calls؟"""
    return len(parse_tool_calls(ai_response)) > 0
