# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  DelegateBridge — نمط التفويض الداخلي
  
  مستوحى من delegate-skills (newskells/)
  يطبق الـ loop: Brief → Implement → Review → Land
  
  بدون CLI خارجي — يستخدم المزودين الموجودين مباشرة
═══════════════════════════════════════════════════════
"""
import pathlib
import time
import json
from dataclasses import dataclass, field
from typing import Callable

from core.execution import RunTicket
from core.structured_log import swallowed as _slog_swallowed


class DelegateCancelled(Exception):
    """T-015 (R-105): ألغي التفويض عند حد مرحلة (نقطة تفتيش تعاونية)."""
    pass

# ── تحميل prompts ──
_PROMPTS_DIR = pathlib.Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    """تحميل prompt template من chain/prompts/"""
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


# ═══════════════════════════════════════════════════════
#   Data Models
# ═══════════════════════════════════════════════════════

@dataclass
class DelegateBrief:
    """Brief مُهيكل — ما يُرسل للـ implementer"""
    task_description: str
    files_context: dict[str, str]     # {path: content}
    constraints: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    raw_brief: str = ""               # الـ brief الكامل (XML)

    def to_dict(self) -> dict:
        return {
            "task_description": self.task_description,
            "files": list(self.files_context.keys()),
            "constraints": self.constraints,
            "verification_commands": self.verification_commands,
            "brief_length": len(self.raw_brief),
        }


@dataclass
class DelegateResult:
    """نتيجة الـ implementer"""
    status: str = "pending"           # pending | success | error
    response: str = ""                # الرد الكامل من الـ implementer
    touched_files: list[str] = field(default_factory=list)
    summary: str = ""
    actions: list[dict] = field(default_factory=list)  # FILE/EDIT/CMD parsed
    duration_ms: int = 0
    provider_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "touched_files": self.touched_files,
            "summary": self.summary,
            "actions_count": len(self.actions),
            "duration_ms": self.duration_ms,
            "provider_calls": self.provider_calls,
        }


@dataclass
class ReviewVerdict:
    """حكم المراجع"""
    verdict: str = "pending"          # approve | rework | reject | pending
    summary: str = ""
    scope_check: str = ""
    quality: str = ""
    risks: list[str] = field(default_factory=list)
    rework_notes: list[str] = field(default_factory=list)
    approved_actions: list[dict] = field(default_factory=list)
    raw_review: str = ""

    @property
    def is_approved(self) -> bool:
        return self.verdict == "approve"

    @property
    def needs_rework(self) -> bool:
        return self.verdict == "rework"

    @property
    def is_rejected(self) -> bool:
        return self.verdict == "reject"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "summary": self.summary,
            "scope_check": self.scope_check,
            "quality": self.quality,
            "risks": self.risks,
            "rework_notes": self.rework_notes,
            "approved_actions_count": len(self.approved_actions),
        }


# ═══════════════════════════════════════════════════════
#   DelegatePhase — مرحلة التفويض
# ═══════════════════════════════════════════════════════

@dataclass
class DelegatePhase:
    """تتبع حالة كل مرحلة"""
    name: str
    status: str = "pending"   # pending | running | success | error | waiting_approval
    result: str = ""
    started_at: float = 0
    completed_at: float = 0

    @property
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at) * 1000)
        return 0


# ═══════════════════════════════════════════════════════
#   DelegateRun — تشغيل تفويض كامل
# ═══════════════════════════════════════════════════════

@dataclass
class DelegateRun:
    """تشغيل تفويض واحد كامل"""
    run_id: str
    user_request: str
    status: str = "pending"   # pending | briefing | implementing | reviewing | waiting_approval | landed | rejected | failed
    
    brief: DelegateBrief | None = None
    result: DelegateResult | None = None
    verdict: ReviewVerdict | None = None
    
    phases: list[DelegatePhase] = field(default_factory=list)
    rework_count: int = 0
    max_reworks: int = 2
    
    started_at: float = 0
    completed_at: float = 0
    
    def __post_init__(self):
        if not self.phases:
            self.phases = [
                DelegatePhase(name="brief"),
                DelegatePhase(name="implement"),
                DelegatePhase(name="review"),
                DelegatePhase(name="approval"),
                DelegatePhase(name="land"),
            ]
    
    def get_phase(self, name: str) -> DelegatePhase:
        """يرجع المرحلة بالاسم — المراحل تُنشأ دائمًا في __post_init__،
        لذا الاسم غير الموجود يعتبر خطأ برمجيًا (KeyError) وليس حالة عادية.
        (T-010: كان يرجع None فسبّب 17 خطأ union-attr في mypy)"""
        for p in self.phases:
            if p.name == name:
                return p
        raise KeyError(f"مرحلة غير معروفة: {name!r}")
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "rework_count": self.rework_count,
            "brief": self.brief.to_dict() if self.brief else None,
            "result": self.result.to_dict() if self.result else None,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "phases": [
                {"name": p.name, "status": p.status, "duration_ms": p.duration_ms}
                for p in self.phases
            ],
        }


# ═══════════════════════════════════════════════════════
#   DelegateBridge — المحرك الرئيسي
# ═══════════════════════════════════════════════════════

class DelegateBridge:
    """
    يدير دورة التفويض الكاملة:
    1. Brief Writer (planner) → يكتب brief شامل
    2. Implementer (executor) → ينفذ المهمة
    3. Reviewer (code_reviewer) → يراجع ويحكم
    4. Land (بعد موافقة المستخدم) → يطبق التعديلات
    
    Events:
    - delegate_started: بداية التفويض
    - delegate_phase: تحديث مرحلة
    - delegate_review: نتيجة المراجعة (تنتظر موافقة)
    - delegate_landed: تم اعتماد التعديلات
    - delegate_rejected: تم رفض التعديلات
    - delegate_error: خطأ
    """
    
    def __init__(self, provider, agent_loader=None, ctx=None):
        """
        provider: أي مزود AI يدعم send()
        agent_loader: AgentLoader (اختياري)
        ctx: AppContext — لو موجود، المزود يُحلّ وقت الاستدعاء (R-102/T-008)
        """
        # R-102 (T-008) — resolve at call time: with ctx set, _provider is a
        # property reading ctx.active_provider per access; no private pokes.
        self._ctx = ctx
        self._static_provider = provider
        self._agent_loader = agent_loader
        self._current_run: DelegateRun | None = None
        self._brief_prompt = _load_prompt("delegate_brief.md")
        self._review_prompt = _load_prompt("delegate_review.md")
        # T-015 (R-105): تذكرة الـ run الحالي — تُحفظ لينهيها land/reject
        # عندما يحسم المستخدم بعد waiting_approval.
        self._current_ticket: RunTicket | None = None
    
    @property
    def _provider(self):
        if self._ctx is not None and self._ctx.active_provider is not None:
            return self._ctx.active_provider
        return self._static_provider

    @staticmethod
    def _to_prompt_history(messages) -> str:
        """R-103 (T-009): render a message list to the ``send(prompt: str)`` contract.

        Format spec:
        - Single user message → its content verbatim (no wrapper), matching
          what providers expect for a plain prompt.
        - Multiple messages → role-tagged blocks, one per message::

              [USER]:
              <content>

              [ASSISTANT]:
              <content>

          joined by a blank line, role uppercased. Unknown/missing role
          renders as ``[USER]``.

        This replaces passing ``list[Message]`` where ``str`` is required —
        a latent crash on any contract-conforming provider.

        T-030 (R-302): the full-list pass is now an explicit named policy
        (``POLICY_DELEGATE_RENDER`` = full window) instead of an implicit
        "just iterate whatever you were handed" — same values, one owner.
        """
        from sessions.memory import POLICY_DELEGATE_RENDER, select_history
        messages = select_history(messages, POLICY_DELEGATE_RENDER)
        if not messages:
            return ""
        if len(messages) == 1 and getattr(messages[0], "role", "user") == "user":
            return messages[0].content
        blocks = []
        for m in messages:
            role = (getattr(m, "role", "") or "user").upper()
            blocks.append(f"[{role}]:\n{m.content}")
        return "\n\n".join(blocks)

    @property
    def is_active(self) -> bool:
        return self._current_run is not None and self._current_run.status not in (
            "landed", "rejected", "failed"
        )
    
    @property
    def current_run(self) -> DelegateRun | None:
        return self._current_run
    
    # ── Phase 1: Write Brief ──
    
    def write_brief(self, user_request: str, files_context: dict[str, str],
                    project_context: str = "", on_event: Callable | None = None) -> DelegateBrief:
        """
        يكتب brief مُهيكل باستخدام planner agent.
        
        Args:
            user_request: طلب المستخدم الأصلي
            files_context: {path: content} — الملفات المرتبطة
            project_context: سياق المشروع العام
            on_event: callback للأحداث
        """
        from providers.base import Message
        
        # بناء prompt للـ brief writer
        files_block = ""
        for path, content in files_context.items():
            files_block += f"\n\n📄 {path}:\n```\n{content}\n```"
        
        prompt = (
            f"اكتب brief مهيكل (XML) للمهمة التالية:\n\n"
            f"[طلب المستخدم]: {user_request}\n\n"
            f"[سياق المشروع]: {project_context}\n\n"
            f"[الملفات المتاحة]:{files_block}\n\n"
            f"اتبع هذا القالب:\n{self._brief_prompt}"
        )
        
        system = ""
        if self._agent_loader:
            agent_prompt = self._agent_loader.load("planner")
            system = agent_prompt.content
        
        messages = [Message(role="user", content=prompt)]
        response = self._provider.send(
            self._to_prompt_history(messages), system_prompt=system)
        
        brief = DelegateBrief(
            task_description=user_request,
            files_context=files_context,
            raw_brief=response,
        )
        
        return brief
    
    # ── Phase 2: Dispatch to Implementer ──
    
    def dispatch(self, brief: DelegateBrief, on_event: Callable | None = None) -> DelegateResult:
        """
        يرسل الـ brief للـ implementer (executor agent).
        العامل يرى الـ brief فقط — لا history ولا context خارجي.
        """
        from providers.base import Message
        
        # العامل يرى الـ brief فقط — بالضبط مثل codex delegate
        prompt = brief.raw_brief
        
        system = ""
        if self._agent_loader:
            agent_prompt = self._agent_loader.load("executor")
            system = agent_prompt.content
        
        start = time.monotonic()
        messages = [Message(role="user", content=prompt)]
        response = self._provider.send(
            self._to_prompt_history(messages), system_prompt=system)
        elapsed = time.monotonic() - start
        
        result = DelegateResult(
            status="success",
            response=response,
            duration_ms=int(elapsed * 1000),
            provider_calls=1,
        )
        
        # استخراج الملخص والملفات المتغيرة من الرد
        result.summary = self._extract_summary(response)
        result.touched_files = self._extract_touched_files(response, brief.files_context)
        
        return result
    
    # ── Phase 3: Review ──
    
    def review(self, brief: DelegateBrief, result: DelegateResult,
               on_event: Callable | None = None) -> ReviewVerdict:
        """
        يراجع عمل الـ implementer ويصدر حكم.
        """
        from providers.base import Message
        
        prompt = (
            f"راجع العمل التالي:\n\n"
            f"[الـ BRIEF الأصلي]:\n{brief.raw_brief}\n\n"
            f"[نتيجة العامل]:\n{result.response}\n\n"
            f"اتبع معايير المراجعة:\n{self._review_prompt}"
        )
        
        system = ""
        if self._agent_loader:
            agent_prompt = self._agent_loader.load("code_reviewer")
            system = agent_prompt.content
        
        messages = [Message(role="user", content=prompt)]
        response = self._provider.send(
            self._to_prompt_history(messages), system_prompt=system)
        
        verdict = self._parse_verdict(response)
        return verdict
    
    # ── Full Delegation Loop ──
    
    @staticmethod
    def _checkpoint(ticket: "RunTicket | None") -> None:
        """T-015 (R-105): نقطة تفتيش إلغاء عند حدود المراحل.

        التفويض لم يكن قابلاً للإلغاء إطلاقاً قبل R-105. الآن: حدود المراحل
        (قبل Brief / Implement / Review وقبل كل rework) هي نقاط التفتيش —
        لا إجهاض لطلب جارٍ في منتصفه (Phase 1 حسب الخارطة).
        """
        if ticket is not None and ticket.is_cancelled:
            raise DelegateCancelled(
                ticket.cancel_reason or "delegation cancelled")

    def run_delegation(self, user_request: str, files_context: dict[str, str],
                       project_context: str = "",
                       on_event: Callable | None = None,
                       ticket: "RunTicket | None" = None) -> DelegateRun:
        """
        يشغل الدورة الكاملة: Brief → Implement → Review → (wait approval)
        
        ملاحظة: الـ land يحتاج موافقة المستخدم — الدالة تتوقف عند waiting_approval.

        ticket (T-015, R-105): تذكرة التنفيذ — إلغاؤها يُلاحَظ عند حدود
        المراحل (≥3 نقاط تفتيش) فينتهي الـ run بحالة cancelled ولا يصل
        أبداً لمرحلة Land.
        """
        import uuid
        
        run = DelegateRun(
            run_id=str(uuid.uuid4())[:8],
            user_request=user_request,
            status="briefing",
            started_at=time.monotonic(),
        )
        self._current_run = run
        self._current_ticket = ticket
        
        self._emit(on_event, "delegate_started", {
            "run_id": run.run_id,
            "request": user_request,
            "files_count": len(files_context),
        })
        
        try:
            # ── Checkpoint #1: قبل Brief ──
            self._checkpoint(ticket)

            # ── Phase 1: Brief ──
            phase = run.get_phase("brief")
            phase.status = "running"
            phase.started_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {"phase": "brief", "status": "running"})
            
            run.brief = self.write_brief(user_request, files_context, project_context, on_event)
            
            phase.status = "success"
            phase.completed_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {
                "phase": "brief", "status": "success",
                "brief_length": len(run.brief.raw_brief),
            })
            
            # ── Checkpoint #2: قبل Implement ──
            self._checkpoint(ticket)

            # ── Phase 2: Implement ──
            run.status = "implementing"
            phase = run.get_phase("implement")
            phase.status = "running"
            phase.started_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {"phase": "implement", "status": "running"})
            
            run.result = self.dispatch(run.brief, on_event)
            
            phase.status = "success"
            phase.completed_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {
                "phase": "implement", "status": "success",
                "touched_files": run.result.touched_files,
            })
            
            # ── Checkpoint #3: قبل Review ──
            self._checkpoint(ticket)

            # ── Phase 3: Review ──
            run.status = "reviewing"
            phase = run.get_phase("review")
            phase.status = "running"
            phase.started_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {"phase": "review", "status": "running"})
            
            run.verdict = self.review(run.brief, run.result, on_event)
            
            phase.status = "success"
            phase.completed_at = time.monotonic()
            self._emit(on_event, "delegate_phase", {
                "phase": "review", "status": "success",
                "verdict": run.verdict.verdict,
                "summary": run.verdict.summary,
            })
            
            # ── انتظار موافقة المستخدم ──
            if run.verdict.is_approved:
                run.status = "waiting_approval"
                approval_phase = run.get_phase("approval")
                approval_phase.status = "waiting_approval"
                self._emit(on_event, "delegate_review", {
                    "run_id": run.run_id,
                    "verdict": run.verdict.to_dict(),
                    "result": run.result.to_dict(),
                    "implementer_response": run.result.response,
                    "needs_approval": True,
                })
            elif run.verdict.needs_rework:
                if run.rework_count < run.max_reworks:
                    run.rework_count += 1
                    run.status = "implementing"
                    # Delta brief — إعادة مع ملاحظات المراجع
                    rework_brief = DelegateBrief(
                        task_description=user_request,
                        files_context=files_context,
                        raw_brief=(
                            f"{run.brief.raw_brief}\n\n"
                            f"[ملاحظات المراجع — أصلح هذه النقاط]:\n" +
                            "\n".join(f"- {n}" for n in run.verdict.rework_notes)
                        ),
                    )
                    run.brief = rework_brief
                    
                    # ── Checkpoint #4: قبل كل rework iteration ──
                    self._checkpoint(ticket)

                    # Re-implement
                    run.result = self.dispatch(run.brief, on_event)
                    run.verdict = self.review(run.brief, run.result, on_event)
                    
                    if run.verdict.is_approved:
                        run.status = "waiting_approval"
                        self._emit(on_event, "delegate_review", {
                            "run_id": run.run_id,
                            "verdict": run.verdict.to_dict(),
                            "result": run.result.to_dict(),
                            "implementer_response": run.result.response,
                            "needs_approval": True,
                            "rework_count": run.rework_count,
                        })
                    else:
                        run.status = "rejected"
                        self._emit(on_event, "delegate_rejected", {
                            "run_id": run.run_id,
                            "reason": "فشل بعد rework",
                            "verdict": run.verdict.to_dict(),
                        })
                else:
                    run.status = "rejected"
                    self._emit(on_event, "delegate_rejected", {
                        "run_id": run.run_id,
                        "reason": f"فشل بعد {run.max_reworks} محاولات rework",
                    })
            else:
                # Rejected
                run.status = "rejected"
                self._emit(on_event, "delegate_rejected", {
                    "run_id": run.run_id,
                    "verdict": run.verdict.to_dict(),
                })
            
        except DelegateCancelled as e:
            # T-015 (R-105): إلغاء تعاوني عند حد مرحلة — لا Land أبداً
            run.status = "cancelled"
            self._emit(on_event, "delegate_cancelled", {
                "run_id": run.run_id,
                "reason": str(e),
            })
        except Exception as e:
            run.status = "failed"
            self._emit(on_event, "delegate_error", {
                "run_id": run.run_id,
                "error": str(e),
            })
        finally:
            # T-015 (R-105): إنهاء تذكرة السجل — waiting_approval يبقى حيّاً
            # (المستخدم لم يحسم بعد)؛ الحالات الحاسمة تُنهى بدقة.
            if ticket is not None and run.status != "waiting_approval":
                _map = {"rejected": "completed", "landed": "completed",
                        "cancelled": "cancelled", "failed": "failed"}
                ticket.finish(_map.get(run.status, "failed"))
        
        return run
    
    # ── Phase 4: Land (بعد موافقة المستخدم) ──
    
    def land(self, on_event: Callable | None = None) -> bool:
        """
        يطبق التعديلات المعتمدة.
        يُستدعى فقط بعد موافقة المستخدم.
        
        Returns: True لو النتيجة قابلة للتطبيق
        """
        run = self._current_run
        if not run or run.status != "waiting_approval":
            return False
        
        land_phase = run.get_phase("land")
        land_phase.status = "running"
        land_phase.started_at = time.monotonic()
        
        run.status = "landed"
        land_phase.status = "success"
        land_phase.completed_at = time.monotonic()
        run.completed_at = time.monotonic()
        
        self._emit(on_event, "delegate_landed", {
            "run_id": run.run_id,
            "implementer_response": run.result.response if run.result else "",
        })
        
        # T-015 (R-105): المستخدم حسم — أنهِ التذكرة وحرّر خانة المشروع
        if self._current_ticket is not None:
            self._current_ticket.finish("completed")
            self._current_ticket = None
        
        return True
    
    def reject(self, reason: str = "", on_event: Callable | None = None) -> bool:
        """رفض التعديلات (المستخدم قرر عدم التطبيق)"""
        run = self._current_run
        if not run or run.status != "waiting_approval":
            return False
        
        run.status = "rejected"
        run.completed_at = time.monotonic()
        
        self._emit(on_event, "delegate_rejected", {
            "run_id": run.run_id,
            "reason": reason or "رفض المستخدم",
        })
        
        # T-015 (R-105): المستخدم حسم بالرفض — أنهِ التذكرة
        if self._current_ticket is not None:
            self._current_ticket.finish("completed")
            self._current_ticket = None
        
        return True
    
    # ── Helpers ──
    
    def _emit(self, on_event, event_type: str, data: dict):
        """إرسال حدث"""
        if on_event:
            try:
                on_event(event_type, data)
            except Exception as _exc:
                _slog_swallowed("chain/delegate.py:648", _exc)
                pass
    
    def _extract_summary(self, response: str) -> str:
        """استخراج ملخص من رد الـ implementer"""
        lines = response.strip().split("\n")
        # أول 3 أسطر غير فارغة
        summary_lines = [l.strip() for l in lines if l.strip()][:3]
        return " ".join(summary_lines)[:500]
    
    def _extract_touched_files(self, response: str, original_files: dict) -> list[str]:
        """استخراج الملفات المعدلة من الرد"""
        import re
        touched = []
        
        # FILE: path/to/file
        for m in re.finditer(r'```FILE:\s*(.+?)$', response, re.MULTILINE):
            path = m.group(1).strip()
            if path not in touched:
                touched.append(path)
        
        # EDIT: path/to/file
        for m in re.finditer(r'```EDIT:\s*(.+?)$', response, re.MULTILINE):
            path = m.group(1).strip()
            if path not in touched:
                touched.append(path)
        
        return touched
    
    def _parse_verdict(self, response: str) -> ReviewVerdict:
        """تحليل حكم المراجع من الرد"""
        import re
        
        verdict = ReviewVerdict(raw_review=response)
        
        # Check if the response indicates empty/whitespace or provider/safety issues
        resp_lower = response.lower() if response else ""
        if not response or not response.strip():
            verdict.verdict = "rework"
            verdict.rework_notes = ["Empty or whitespace-only review response."]
            return verdict
            
        if "provider_error" in resp_lower or "provider error" in resp_lower:
            verdict.verdict = "rework"
            verdict.rework_notes = ["Provider error encountered during review."]
            return verdict
            
        if "safety refusal" in resp_lower or "safety_refusal" in resp_lower or "refused" in resp_lower:
            verdict.verdict = "rework"
            verdict.rework_notes = ["Safety refusal detected in review response."]
            return verdict
        
        # [VERDICT]: APPROVE | REWORK | REJECT
        m = re.search(r'\[VERDICT\]\s*:\s*(APPROVE|REWORK|REJECT)', response, re.IGNORECASE)
        if m:
            verdict.verdict = m.group(1).lower()
        else:
            # تخمين من المحتوى
            if "approve" in resp_lower or "اعتمد" in resp_lower or "✅" in resp_lower:
                verdict.verdict = "approve"
            elif "rework" in resp_lower or "إعادة" in resp_lower or "rework needed" in resp_lower:
                verdict.verdict = "rework"
            elif "reject" in resp_lower or "ارفض" in resp_lower:
                verdict.verdict = "reject"
            else:
                verdict.verdict = "rework"  # default to rework if unclear (fail-closed)
                verdict.rework_notes = ["Verdict was unparseable. Falling back to REWORK."]
        
        # [SUMMARY]
        m = re.search(r'\[SUMMARY\]\s*:\s*(.+?)(?:\n\[|$)', response, re.DOTALL)
        if m:
            verdict.summary = m.group(1).strip()[:500]
        
        # [SCOPE_CHECK]
        m = re.search(r'\[SCOPE_CHECK\]\s*:\s*(.+?)(?:\n|$)', response)
        if m:
            verdict.scope_check = m.group(1).strip()
        
        # [QUALITY]
        m = re.search(r'\[QUALITY\]\s*:\s*(.+?)(?:\n|$)', response)
        if m:
            verdict.quality = m.group(1).strip()
        
        # [RISKS]
        m = re.search(r'\[RISKS\]\s*:\s*(.+?)(?:\n\[|$)', response, re.DOTALL)
        if m:
            risks_text = m.group(1).strip()
            verdict.risks = [
                line.lstrip("- ").strip()
                for line in risks_text.split("\n")
                if line.strip() and line.strip() != "-"
            ]
        
        # [REWORK_NOTES]
        m = re.search(r'\[REWORK_NOTES\]\s*:\s*(.+?)(?:\n\[|$)', response, re.DOTALL)
        if m:
            notes_text = m.group(1).strip()
            verdict.rework_notes = [
                line.lstrip("- ").strip()
                for line in notes_text.split("\n")
                if line.strip() and line.strip() != "-"
            ]
        
        return verdict
