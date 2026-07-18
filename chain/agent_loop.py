# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🔄 AgentLoop — حلقة الـ Agent الذكي
  
  بدل one-shot (prompt → response):
  loop: prompt → AI يطلب أدوات → ينفذها → يكمل → يرد
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import json
import time
import threading
from typing import Callable, Any

from chain.knowledge import KnowledgeAccumulator
from chain.agent_tools import (
    AgentTools, ToolCall, parse_tool_calls, has_tool_calls,
    SAFE_TOOLS, APPROVAL_TOOLS,
)


class AgentLoop:
    """
    Agent Loop — يحول الـ AI من chat wrapper لـ agent متكامل.
    
    المسار:
    1. يبني prompt مع context + tools description
    2. يرسل للـ AI عبر provider
    3. يحلل الرد — لو فيه tool_calls → ينفذها → يعيد
    4. لو الرد نهائي (بدون tool_calls) → يرجعه
    
    Args:
        tools: AgentTools instance
        send_fn: دالة إرسال للـ AI (prompt, history, system) → response
        ws_send_fn: دالة إرسال WebSocket (لإبلاغ المستخدم)
        system_prompt: System prompt
        max_iterations: حد أقصى لعدد الدورات
    """
    
    MAX_ITERATIONS = 8
    TOOL_RESULT_MAX_LEN = 3000  # حد نتيجة أداة في prompt
    
    def __init__(
        self,
        tools: AgentTools,
        send_fn: Callable,
        ws_send_fn: Callable | None = None,
        system_prompt: str = "",
        max_iterations: int = 8,
    ):
        self.tools = tools
        self.send_fn = send_fn
        self.ws_send_fn = ws_send_fn or (lambda x: None)
        self.system_prompt = system_prompt
        self.max_iterations = min(max_iterations, self.MAX_ITERATIONS)
        
        self.knowledge = KnowledgeAccumulator()
        self._cancelled = False
        self._approval_event = threading.Event()
        self._approval_result = False
        self._pending_approval: ToolCall | None = None
        self._pending_approval_id: str | None = None
        self._pending_approval_hash: str | None = None
    
    def run(self, user_request: str, history: list | None = None,
            project_context: str = "", run_id: str = "", step_id: str = "") -> str:
        """
        تشغيل الـ Agent Loop.
        
        Returns:
            الرد النهائي من AI (بعد جمع كل المعلومات)
        """
        history = history or []
        self._cancelled = False
        
        # ═══════════════════════════════════════
        # 🔍 Phase 0: Auto-Context Injection
        # جمع المعلومات ذاتياً قبل إرسال للـ AI
        # ═══════════════════════════════════════
        self._auto_prefetch(user_request)
        
        # ── بناء prompt أولي مع context مُجمّع ──
        agent_prompt = self._build_initial_prompt(user_request, project_context)
        
        for iteration in range(self.max_iterations):
            if self._cancelled:
                return "⚠️ تم إلغاء الطلب."
            
            self.knowledge.next_iteration()
            
            # إبلاغ المستخدم
            self.ws_send_fn({
                "type": "agent_thinking",
                "iteration": iteration + 1,
                "max": self.max_iterations,
                "knowledge": self.knowledge.get_summary(),
            })
            
            # ── إرسال prompt للـ AI ──
            try:
                ai_response = self.send_fn(
                    agent_prompt,
                    history,
                    self.system_prompt,
                )
            except Exception as e:
                self.knowledge.add_error(f"فشل الاتصال بالـ AI: {e}")
                # نحاول مرة تانية بدون tool context
                continue
            
            if not ai_response:
                continue
            
            # ── هل الرد يحتوي tool calls؟ ──
            if not has_tool_calls(ai_response):
                # رد نهائي — خلاص عنده كل المعلومات
                self.ws_send_fn({
                    "type": "agent_done",
                    "iterations": iteration + 1,
                    "knowledge": self.knowledge.get_summary(),
                })
                return ai_response
            
            # ── استخراج وتنفيذ الأدوات ──
            tool_calls = parse_tool_calls(ai_response)
            
            if not tool_calls:
                # فيه ```TOOL: بس الـ parsing فشل → نعتبره رد نهائي
                return ai_response
            
            # ── أيضاً: استخراج أي نص عادي قبل الأدوات ──
            # (AI ممكن يكتب ملاحظات + tool calls)
            plain_text = self._extract_plain_text(ai_response)
            if plain_text:
                self.knowledge.add_observation(plain_text[:500])
                # نرسل النص للمستخدم كـ streaming
                self.ws_send_fn({
                    "type": "chunk",
                    "text": plain_text + "\n\n",
                })
            
            # ── تنفيذ كل أداة ──
            tool_results_text = []
            
            for call in tool_calls:
                if self._cancelled:
                    break
                
                # أدوات آمنة → تنفيذ فوري
                if not call.needs_approval:
                    self.ws_send_fn({
                        "type": "agent_step",
                        "tool": call.tool,
                        "args": call.args,
                        "status": "running",
                    })
                    
                    result = self.tools.execute(call)
                    success = not result.startswith("❌")
                    
                    self.knowledge.add_tool_result(
                        call.tool, call.args, result, success
                    )
                    
                    # Preview للمستخدم
                    self.ws_send_fn({
                        "type": "agent_step",
                        "tool": call.tool,
                        "args": call.args,
                        "status": "done",
                        "preview": result[:200],
                        "success": success,
                    })
                    
                    # نختصر النتيجة للـ prompt
                    truncated = result[:self.TOOL_RESULT_MAX_LEN]
                    if len(result) > self.TOOL_RESULT_MAX_LEN:
                        truncated += f"\n... ({len(result)} حرف إجمالي)"
                    tool_results_text.append(
                        f"[نتيجة {call.tool}({self._args_str(call.args)})]:\n{truncated}"
                    )
                
                else:
                    # أداة تحتاج موافقة (run_command)
                    approved = self._request_approval(call, run_id, step_id)
                    
                    if approved:
                        self.ws_send_fn({
                            "type": "agent_step",
                            "tool": call.tool,
                            "args": call.args,
                            "status": "running",
                        })
                        
                        result = self.tools.execute(call)
                        success = not result.startswith("❌")
                        
                        self.knowledge.add_tool_result(
                            call.tool, call.args, result, success
                        )
                        
                        self.ws_send_fn({
                            "type": "agent_step",
                            "tool": call.tool,
                            "args": call.args,
                            "status": "done",
                            "preview": result[:200],
                            "success": success,
                        })
                        
                        truncated = result[:self.TOOL_RESULT_MAX_LEN]
                        tool_results_text.append(
                            f"[نتيجة {call.tool}({self._args_str(call.args)})]:\n{truncated}"
                        )
                    else:
                        self.knowledge.add_observation(
                            f"المستخدم رفض تنفيذ: {call.args.get('command', '')}"
                        )
                        tool_results_text.append(
                            f"[{call.tool}: رفض المستخدم — '{call.args.get('command', '')}']"
                        )
            
            # ── بناء prompt جديد مع النتائج ──
            agent_prompt = self._build_followup_prompt(
                user_request, tool_results_text, project_context
            )
        
        # ── وصلنا لحد الـ iterations ──
        self.ws_send_fn({
            "type": "agent_done",
            "iterations": self.max_iterations,
            "knowledge": self.knowledge.get_summary(),
            "max_reached": True,
        })
        
        # محاولة أخيرة — نطلب من AI يرد بالمعرفة الموجودة
        final_prompt = self._build_final_prompt(user_request, project_context)
        try:
            return self.send_fn(final_prompt, history, self.system_prompt)
        except Exception:
            return "⚠️ وصلت لحد المحاولات. النتائج المجمعة:\n" + \
                   self.knowledge.build_context(max_tokens=4000)
    
    def cancel(self):
        """إلغاء الـ loop"""
        self._cancelled = True
        self._approval_event.set()  # فك أي انتظار
    
    def approve_command(self, approved: bool, approval_request_id: str = "", payload_hash: str = ""):
        """استجابة المستخدم لطلب موافقة محدد ومؤمن"""
        if (hasattr(self, "_pending_approval_id") and self._pending_approval_id == approval_request_id and
            hasattr(self, "_pending_approval_hash") and self._pending_approval_hash == payload_hash):
            self._approval_result = approved
            self._approval_event.set()
        else:
            # Reject mismatching responses
            print(f"Approval validation failed: expected ID={getattr(self, '_pending_approval_id', '')}, got {approval_request_id}")
    
    # ──── بناء Prompts ────
    
    def _build_initial_prompt(self, user_request: str,
                               project_context: str) -> str:
        """Prompt أولي — مع المعلومات المُجمّعة مسبقاً"""
        parts = []
        
        parts.append(f"[طلب المستخدم]:\n{user_request}")
        
        if project_context:
            parts.append(f"\n[سياق المشروع]:\n{project_context}")
        
        # ═══ المعرفة المُجمّعة تلقائياً (pre-fetch) ═══
        knowledge_ctx = self.knowledge.build_context(max_tokens=8000)
        if knowledge_ctx:
            parts.append(
                f"\n[✅ تم جمع المعلومات التالية تلقائياً من المشروع الفعلي]:\n"
                f"{knowledge_ctx}"
            )
            parts.append(
                "\n[تعليمات مهمة]: المعلومات أعلاه مقروءة من الملفات الفعلية في نظام الملفات. "
                "أنت تملك وصولاً حقيقياً للمشروع — لا تقل 'مش عارف أوصل للملفات'. "
                "استخدم المعلومات المرفقة لتحليل الطلب والرد بشكل كامل."
            )
        
        # وصف الأدوات (لو AI يدعمها)
        parts.append(self._tools_instruction())
        
        return "\n\n".join(parts)
    
    def _build_followup_prompt(self, user_request: str,
                                tool_results: list[str],
                                project_context: str) -> str:
        """Prompt متابعة — بعد تنفيذ أدوات"""
        parts = []
        
        parts.append(f"[طلب المستخدم الأصلي]:\n{user_request}")
        
        # المعرفة التراكمية
        knowledge_ctx = self.knowledge.build_context(max_tokens=6000)
        if knowledge_ctx:
            parts.append(f"\n[المعرفة المجمعة حتى الآن]:\n{knowledge_ctx}")
        
        # نتائج آخر جولة
        if tool_results:
            parts.append("\n[نتائج الأدوات الأخيرة]:\n" + "\n\n".join(tool_results))
        
        parts.append(
            "\n[تعليمات]: بناءً على المعلومات أعلاه، "
            "إما أجب على طلب المستخدم مباشرة "
            "أو استخدم أدوات إضافية إذا كنت تحتاج معلومات أكثر."
        )
        
        parts.append(self._tools_instruction())
        
        return "\n\n".join(parts)
    
    def _build_final_prompt(self, user_request: str,
                             project_context: str) -> str:
        """Prompt نهائي — أجب بالمعرفة الموجودة"""
        knowledge_ctx = self.knowledge.build_context(max_tokens=6000)
        
        return (
            f"[طلب المستخدم]:\n{user_request}\n\n"
            f"[المعرفة المجمعة]:\n{knowledge_ctx}\n\n"
            f"[تعليمات]: أجب على طلب المستخدم بناءً على المعلومات المتاحة أعلاه. "
            f"لا تستخدم أي أدوات — أعط الرد النهائي الآن."
        )
    
    def _tools_instruction(self) -> str:
        """وصف الأدوات المتاحة"""
        return """
[الأدوات المتاحة]:
لجمع المعلومات، ضع كل طلب في بلوك:

```TOOL: read_file
path: مسار/الملف
start_line: 1 (اختياري)
end_line: 50 (اختياري)
```

```TOOL: list_dir
path: مسار/المجلد (افتراضي .)
depth: 2 (اختياري)
```

```TOOL: search_code
query: نص البحث
path: مجلد البحث (افتراضي .)
```

```TOOL: get_file_info
path: مسار/الملف
```

```TOOL: get_project_tree
max_depth: 3 (اختياري)
```

```TOOL: run_command
command: الأمر لتنفيذه
reason: سبب تشغيل الأمر
```

[تعليمات مهمة]:
1. استخدم الأدوات فقط عند الحاجة الحقيقية.
2. لا تشغل run_command إلا إذا كنت متأكدًا تمامًا وتريد بناء، اختبار، أو تثبيت حزم.
3. التزم تمامًا بالصيغة المذكورة.
"""

    def _request_approval(self, call: ToolCall, run_id: str = "", step_id: str = "") -> bool:
        """طلب موافقة المستخدم على تنفيذ أمر"""
        import uuid
        import time
        from chain.agent_tools import compute_payload_hash
        
        approval_id = str(uuid.uuid4())
        expires_at = time.time() + 60.0
        
        cwd = self.tools.project_root
        env: dict[str, str] = {}
        payload_hash = compute_payload_hash(call.tool, call.args, cwd, env)
        
        self._pending_approval_id = approval_id
        self._pending_approval_hash = payload_hash
        self._pending_approval = call
        self._approval_event.clear()
        self._approval_result = False
        
        self.ws_send_fn({
            "type": "agent_step",
            "tool": call.tool,
            "args": call.args,
            "status": "awaiting_approval",
            "reason": call.reason,
            "approval_request_id": approval_id,
            "run_id": run_id,
            "step_id": step_id,
            "payload_hash": payload_hash,
            "expires_at": expires_at,
        })
        
        # الانتظار حتى موافقة أو رفض المستخدم مع مهلة 60 ثانية
        success = self._approval_event.wait(timeout=60.0)
        
        if not success:
            self.knowledge.add_observation(
                f"انتهت مهلة موافقة المستخدم لتنفيذ: {call.args.get('command', '')}"
            )
            self._pending_approval = None
            self._pending_approval_id = None
            self._pending_approval_hash = None
            return False
            
        self._pending_approval = None
        self._pending_approval_id = None
        self._pending_approval_hash = None
        return self._approval_result

    def _extract_plain_text(self, ai_response: str) -> str:
        """استخراج النص العادي من رد الـ AI قبل أو بين استدعاءات الأدوات"""
        import re
        clean = re.sub(r'```TOOL:\s*\w+.*?(?:```|$)', '', ai_response, flags=re.DOTALL)
        clean = re.sub(r'(?:^|\n)TOOL:\s*\w+.*?(?=\n\n|\nTOOL:|$)', '', clean, flags=re.DOTALL)
        return clean.strip()

    def _args_str(self, args: dict) -> str:
        """تحويل arguments لـ string مقروء"""
        if not args:
            return ""
        return ", ".join(f"{k}={v}" for k, v in args.items())

    # ──── Auto Pre-fetch (via ContextBuilder) ────
    
    def _auto_prefetch(self, user_request: str):
        """
        🔍 جمع معلومات ذاتياً قبل إرسال الـ prompt.
        يستخدم ContextBuilder المشترك.
        """
        from chain.context_builder import ContextBuilder
        
        def _on_progress(kind, source, status):
            self.ws_send_fn({
                "type": "agent_step",
                "tool": f"auto_{kind}",
                "args": {"source": source},
                "status": status,
            })
        
        builder = ContextBuilder(
            project_root=self.tools.project_root,
            on_progress=_on_progress,
        )
        result = builder.gather(user_request)
        
        # نقل النتائج للـ Knowledge
        for item in result.items:
            if item.success:
                self.knowledge.add_tool_result(
                    f"auto_{item.kind}",
                    {"source": item.source},
                    item.content,
                    success=True,
                )
        

        if result.has_context:
            s = result.get_summary()
            self.ws_send_fn({
                "type": "agent_step",
                "tool": "auto_prefetch",
                "args": {},
                "status": "done",
                "preview": f"جمعت {s['success']} معلومة تلقائياً "
                           f"({s['files']} ملفات، {s['dirs']} مجلدات)",
                "success": True,
            })
