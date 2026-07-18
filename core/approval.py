# -*- coding: utf-8 -*-
"""ApprovalGate (T-011, R-104): the single consent checkpoint for mutations.

Why this exists
---------------
``ChainBridge._run_chain`` applies chain output in a ``finally`` block with
**no approval** (even on failed runs), while ``AgentLoop`` has its own
separate hash-verified approval flow. Two consent models; one is "none".
This service unifies them: every mutation request goes through
``ApprovalGate.request()`` and gets an explicit :class:`Verdict`.

Mode semantics
--------------
==============  ==============================================================
Mode            Behavior of ``request()``
==============  ==============================================================
``auto``        Approve **iff** every action's ``kind`` is in
                ``auto_whitelist``; any non-whitelisted kind falls back to
                interactive when a callback is wired, else **deny**.
``interactive`` Emit the request via ``on_request`` callback (WS wiring in
                T-012+) and block until :meth:`resolve` is called with the
                matching ``request_id`` **and** ``payload_hash``, or until
                ``timeout_seconds`` elapses → **deny** (reason ``timeout``).
``deny``        Deny everything immediately (kill-switch).
==============  ==============================================================

Every verdict — approved or denied, whatever the path — is appended to the
in-memory audit log (:meth:`audit_entries`).

Thread model: ``request()`` is expected on a worker thread (chain/agent
executor); ``resolve()`` arrives from the WS handler thread. The same
``threading.Event`` mechanics as ``AgentLoop.approve_command`` are used,
including payload-hash verification to defeat stale/forged approvals.

.. note::
   T-011 ships the gate standalone (unit-tested, unused). T-012 routes
   ``ChainBridge`` through it; the agent loop follows.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

# ── الأوضاع المسموحة ──
VALID_MODES = ("auto", "interactive", "deny")

# whitelist افتراضية للوضع auto — أنواع قراءة/غير مدمّرة فقط.
# الكتابة والحذف وأوامر الشيل لا تُعتمد تلقائيًا إلا بقرار صريح من config.
DEFAULT_AUTO_WHITELIST = frozenset({"read", "format"})


def compute_actions_hash(actions: list["ProposedAction"]) -> str:
    """Hash حتمي لحمولة الطلب — نفس فكرة compute_payload_hash في agent_tools:
    ترتيب مفاتيح JSON ثابت ⇒ نفس الأفعال = نفس الـ hash دائمًا."""
    canonical = json.dumps(
        [
            {"kind": a.kind, "target": a.target, "payload": a.payload}
            for a in actions
        ],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════
#   نماذج البيانات
# ═══════════════════════════════════════════════════════

@dataclass
class ProposedAction:
    """فعل واحد مقترح على workspace (كتابة ملف/حذف/أمر شيل...)."""
    kind: str                    # "write" | "delete" | "command" | "read" | "format" | ...
    target: str = ""             # مسار الملف أو الأمر
    payload: str = ""            # المحتوى الجديد / وسائط الأمر
    summary: str = ""            # وصف مقروء للمستخدم (لواجهة المراجعة لاحقًا)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "target": self.target,
            "payload": self.payload,
            "summary": self.summary,
        }


@dataclass
class ApprovalRequest:
    """طلب موافقة على مجموعة أفعال — يُنشأ hash الحمولة تلقائيًا."""
    actions: list[ProposedAction]
    source: str = ""             # "chain" | "agent" | ...
    run_id: str = ""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.actions:
            raise ValueError("ApprovalRequest يتطلب فعلًا واحدًا على الأقل")
        self.payload_hash = compute_actions_hash(self.actions)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "source": self.source,
            "run_id": self.run_id,
            "payload_hash": self.payload_hash,
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class Verdict:
    """قرار البوابة — دائمًا صريح ومسجَّل."""
    approved: bool
    mode: str                    # الوضع الذي أنتج القرار
    reason: str                  # "auto_whitelist" | "user_approved" | "user_denied" | "timeout" | "deny_mode" | "non_whitelisted_kind" | "hash_mismatch"
    request_id: str = ""
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "mode": self.mode,
            "reason": self.reason,
            "request_id": self.request_id,
            "decided_at": self.decided_at,
        }


# ═══════════════════════════════════════════════════════
#   ApprovalGate
# ═══════════════════════════════════════════════════════

class ApprovalGate:
    """نقطة القرار الوحيدة قبل أي كتابة على workspace.

    Args:
        mode: "auto" | "interactive" | "deny".
        auto_whitelist: أنواع الأفعال المعتمدة تلقائيًا في وضع auto.
        on_request: callback يُستدعى بطلب interactive (لاحقًا: إرسال WS frame).
        timeout_seconds: مهلة انتظار قرار المستخدم قبل deny.
        clock: حقن الوقت للاختبارات (افتراضي time.time).
    """

    def __init__(
        self,
        mode: str = "interactive",
        auto_whitelist: frozenset[str] | set[str] | None = None,
        on_request: Callable[[dict], None] | None = None,
        timeout_seconds: float = 60.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"وضع غير معروف: {mode!r} — المسموح: {VALID_MODES}")
        self.mode = mode
        self.auto_whitelist = frozenset(auto_whitelist if auto_whitelist is not None
                                        else DEFAULT_AUTO_WHITELIST)
        self.on_request = on_request
        self.timeout_seconds = timeout_seconds
        self._clock = clock

        self._lock = threading.Lock()
        self._audit: list[dict] = []

        # حالة الطلب التفاعلي المعلّق (طلب واحد في كل مرة — نفس نموذج AgentLoop)
        self._pending_id: str | None = None
        self._pending_hash: str | None = None
        self._pending_event = threading.Event()
        self._pending_result: bool = False
        self._pending_reason: str = ""

    # ──── الواجهة الرئيسية ────

    def request(self, req: ApprovalRequest,
                on_request: Callable[[dict], None] | None = None) -> Verdict:
        """قرار صريح لكل طلب — لا يرمي أبدًا، يرجع Verdict دائمًا.

        Args:
            on_request: (T-012) قناة إشعار خاصة بهذا الاستدعاء تطغى على
                self.on_request — تسمح للـ bridge بتوجيه إطار الموافقة إلى
                WebSocket التشغيلة الحالية دون تحوير حالة البوابة المشتركة.
        """
        channel = on_request if on_request is not None else self.on_request

        if self.mode == "deny":
            return self._record(req, approved=False, reason="deny_mode")

        if self.mode == "auto":
            kinds = {a.kind for a in req.actions}
            if kinds <= self.auto_whitelist:
                return self._record(req, approved=True, reason="auto_whitelist")
            # نوع غير معتمد: نسقط للوضع التفاعلي إن وُجدت قناة، وإلا نرفض
            if channel is None:
                return self._record(req, approved=False,
                                    reason="non_whitelisted_kind")
            return self._interactive(req, channel)

        # interactive
        return self._interactive(req, channel)

    def resolve(self, request_id: str, approved: bool,
                payload_hash: str = "") -> bool:
        """استجابة المستخدم (من WS handler لاحقًا).

        يُقبل فقط إذا طابق request_id **و** payload_hash الطلبَ المعلّق —
        نفس آلية AgentLoop.approve_command ضد الردود القديمة/المزوّرة.
        Returns True لو طابق وفكّ الانتظار؛ False للردود غير المطابقة.
        """
        with self._lock:
            if (self._pending_id is not None
                    and request_id == self._pending_id
                    and payload_hash == self._pending_hash):
                self._pending_result = approved
                self._pending_reason = "user_approved" if approved else "user_denied"
                self._pending_event.set()
                return True
        return False

    def pending_request_id(self) -> str | None:
        """الطلب التفاعلي المعلّق حاليًا (أو None)."""
        with self._lock:
            return self._pending_id

    # ──── سجل التدقيق ────

    def audit_entries(self) -> list[dict]:
        """نسخة من سجل التدقيق (الأقدم أولاً)."""
        with self._lock:
            return list(self._audit)

    # ──── داخلي ────

    def _interactive(self, req: ApprovalRequest,
                     channel: Callable[[dict], None] | None = None) -> Verdict:
        if channel is None:
            channel = self.on_request
        with self._lock:
            self._pending_id = req.request_id
            self._pending_hash = req.payload_hash
            self._pending_event.clear()
            self._pending_result = False
            self._pending_reason = ""

        # إشعار القناة (WS) — فشل الـ callback لا يعلّق البوابة
        if channel is not None:
            try:
                channel(req.to_dict())
            except Exception:
                pass

        got_answer = self._pending_event.wait(timeout=self.timeout_seconds)

        with self._lock:
            self._pending_id = None
            self._pending_hash = None
            if not got_answer:
                approved, reason = False, "timeout"
            else:
                approved, reason = self._pending_result, self._pending_reason

        return self._record(req, approved=approved, reason=reason)

    def _record(self, req: ApprovalRequest, approved: bool,
                reason: str) -> Verdict:
        verdict = Verdict(approved=approved, mode=self.mode, reason=reason,
                          request_id=req.request_id, decided_at=self._clock())
        entry = {
            "request_id": req.request_id,
            "source": req.source,
            "run_id": req.run_id,
            "payload_hash": req.payload_hash,
            "action_kinds": sorted({a.kind for a in req.actions}),
            "action_count": len(req.actions),
            "mode": self.mode,
            "approved": approved,
            "reason": reason,
            "decided_at": verdict.decided_at,
        }
        with self._lock:
            self._audit.append(entry)
        return verdict
