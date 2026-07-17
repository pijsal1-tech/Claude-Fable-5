# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🔧 AgentTools — أدوات الـ Agent
  
  كل أداة تُنفذ محلياً وترجع النتيجة كنص.
  الأوامر (run_command) تحتاج موافقة المستخدم.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import os
import pathlib
from dataclasses import dataclass
from typing import Callable
from chain.path_policy import resolve_workspace_path, is_secret_file
import hashlib
import json

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
                 project_root: str = "."):
        self.fm = file_manager
        self.cmd = command_runner
        self.project_root = str(project_root)
        self._max_file_size = 100 * 1024  # 100KB
        self._max_dir_depth = 3
    
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
            e = end_line if end_line > 0 else len(lines)
            selected = lines[s:e]
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
        lines = []
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
        """تنفيذ أمر في Terminal — يحتاج موافقة"""
        if not self.cmd:
            return "❌ CommandRunner غير متاح"
        
        try:
            result = self.cmd.run(command, need_approval=False, timeout=30)
            output = result.get("output", "") or result.get("error", "")
            if result.get("success"):
                return output or "(تم التنفيذ بنجاح — لا مخرجات)"
            return f"❌ فشل: {output}"
        except Exception as e:
            return f"❌ خطأ: {e}"
    
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
    
    _handlers = {
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
    args = {}
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
