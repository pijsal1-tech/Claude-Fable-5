# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🧠 KnowledgeAccumulator — ذاكرة تراكمية للـ Agent
  
  تجمع كل المعلومات المكتشفة أثناء agent loop.
  لا تضيع عند تبديل الحساب أو إعادة المحاولة.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """نتيجة أداة واحدة"""
    tool: str                    # اسم الأداة (read_file, list_dir, ...)
    args: dict                   # المعاملات
    result: str                  # الناتج (نص)
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    iteration: int = 0          # في أي iteration تمت

    def to_summary(self, max_len: int = 500) -> str:
        """ملخص مختصر — يُستخدم في prompt"""
        preview = self.result[:max_len]
        if len(self.result) > max_len:
            preview += f"\n... ({len(self.result) - max_len} حرف إضافي)"
        
        status = "✅" if self.success else "❌"
        args_str = ", ".join(f"{k}={v!r}" for k, v in self.args.items())
        return f"{status} {self.tool}({args_str}):\n{preview}"

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "result": self.result[:1000],
            "success": self.success,
            "iteration": self.iteration,
        }


class KnowledgeAccumulator:
    """
    ذاكرة تراكمية — تجمع كل ما يكتشفه الـ Agent.
    
    المعرفة لا تُفقد عند:
    - تبديل الحساب (account switch)
    - إعادة المحاولة (retry)
    - انتهاء الـ iteration
    
    تُمرر كسياق مع كل prompt → AI يبني عليها.
    """
    
    def __init__(self):
        self._tool_results: list[ToolResult] = []
        self._files_read: dict[str, str] = {}      # {path: content}
        self._dirs_listed: dict[str, str] = {}      # {path: listing}
        self._searches: list[dict] = []             # نتائج البحث
        self._commands: list[dict] = []             # أوامر نُفذت
        self._observations: list[str] = []          # ملاحظات AI
        self._errors: list[str] = []                # أخطاء حصلت
        self._iteration: int = 0
    
    # ──── إضافة معرفة ────
    
    def add_tool_result(self, tool: str, args: dict, result: str,
                        success: bool = True) -> ToolResult:
        """إضافة نتيجة أداة"""
        tr = ToolResult(
            tool=tool,
            args=args,
            result=result,
            success=success,
            iteration=self._iteration,
        )
        self._tool_results.append(tr)
        
        # تصنيف تلقائي
        if tool == "read_file" and success:
            path = args.get("path", "")
            self._files_read[path] = result
        elif tool == "list_dir" and success:
            path = args.get("path", "")
            self._dirs_listed[path] = result
        elif tool == "search_code" and success:
            self._searches.append({"query": args.get("query", ""), "result": result})
        elif tool == "run_command":
            self._commands.append({
                "command": args.get("command", ""),
                "result": result,
                "success": success,
            })
        
        return tr
    
    def add_observation(self, text: str):
        """إضافة ملاحظة من AI (مثل: 'الملف يستخدم React hooks')"""
        self._observations.append(text)
    
    def add_error(self, text: str):
        """تسجيل خطأ"""
        self._errors.append(text)
    
    def next_iteration(self):
        """انتقال لـ iteration جديدة"""
        self._iteration += 1
    
    # ──── بناء سياق للـ prompt ────
    
    def build_context(self, max_tokens: int = 8000) -> str:
        """
        بناء سياق مختصر يُضاف للـ prompt.
        يحافظ على أهم المعلومات ضمن حد الـ tokens.
        """
        if not self._tool_results and not self._observations:
            return ""
        
        sections = []
        
        # ── ملفات مقروءة ──
        if self._files_read:
            sec = "📂 [ملفات تم قراءتها]:\n"
            for path, content in self._files_read.items():
                # نختصر المحتوى الطويل
                preview = content[:2000] if len(content) > 2000 else content
                sec += f"\n--- {path} ---\n{preview}\n"
                if len(content) > 2000:
                    sec += f"... ({len(content)} حرف إجمالي)\n"
            sections.append(sec)
        
        # ── مجلدات ──
        if self._dirs_listed:
            sec = "📁 [مجلدات تم استعراضها]:\n"
            for path, listing in self._dirs_listed.items():
                sec += f"\n{path}/:\n{listing}\n"
            sections.append(sec)
        
        # ── نتائج بحث ──
        if self._searches:
            sec = "🔍 [نتائج بحث]:\n"
            for s in self._searches[-5:]:  # آخر 5
                sec += f"\nبحث: {s['query']}\n{s['result'][:500]}\n"
            sections.append(sec)
        
        # ── أوامر نُفذت ──
        if self._commands:
            sec = "⚡ [أوامر تم تنفيذها]:\n"
            for c in self._commands:
                status = "✅" if c["success"] else "❌"
                sec += f"\n{status} $ {c['command']}\n{c['result'][:300]}\n"
            sections.append(sec)
        
        # ── ملاحظات ──
        if self._observations:
            sec = "💡 [ملاحظات سابقة]:\n"
            for obs in self._observations[-10:]:
                sec += f"- {obs}\n"
            sections.append(sec)
        
        # ── أخطاء ──
        if self._errors:
            sec = "⚠️ [أخطاء]:\n"
            for err in self._errors[-5:]:
                sec += f"- {err}\n"
            sections.append(sec)
        
        context = "\n".join(sections)
        
        # قص لو طويل
        if len(context) > max_tokens * 4:  # تقدير: 4 chars/token
            context = context[:max_tokens * 4] + "\n... (تم اختصار السياق)"
        
        return context
    
    # ──── معلومات ────
    
    @property
    def iteration(self) -> int:
        return self._iteration
    
    @property
    def total_results(self) -> int:
        return len(self._tool_results)
    
    @property
    def files_count(self) -> int:
        return len(self._files_read)
    
    @property
    def has_knowledge(self) -> bool:
        return bool(self._tool_results or self._observations)
    
    def get_summary(self) -> dict:
        """ملخص لعرضه في الـ UI"""
        return {
            "iterations": self._iteration,
            "tools_used": self.total_results,
            "files_read": self.files_count,
            "dirs_listed": len(self._dirs_listed),
            "searches": len(self._searches),
            "commands": len(self._commands),
            "observations": len(self._observations),
            "errors": len(self._errors),
        }
    
    def clear(self):
        """مسح كل المعرفة (بداية جديدة)"""
        self._tool_results.clear()
        self._files_read.clear()
        self._dirs_listed.clear()
        self._searches.clear()
        self._commands.clear()
        self._observations.clear()
        self._errors.clear()
        self._iteration = 0
