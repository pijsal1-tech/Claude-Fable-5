# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ACP Governed FS — الجسر المُبوَّب للطلبات العكسية
  TSK-736b (القرار 8 من تسلسل D-19)

  يعالج طلبات الوكيل الخارجي العكسية بإنفاذ حوكمتنا **نفسها**
  (القراران الواعيان 2 و3 في مواصفة TSK-736 — حلّ قلقَي CP-15):

  - ``fs/read_text_file``: عبر ``resolve_workspace_path`` (حدود
    workspace + رفض symlink escape) **و** ``is_secret_file``
    (denylist الأسرار بتطبيع CEV-117) ⇒ الوكيل الخارجي **لا يقرأ**
    provider_keys.json/.env/أخواتها أبدًا — خطأ ERR_PATH_FORBIDDEN
    برسالة عامة (لا يؤكَّد وجود الملف ولا سبب الحجب).

  - ``fs/write_text_file``: يُترجم إلى ProposedAction (kind
    ``acp_write``) ويمر عبر **نفس** ApprovalGate (core/approval —
    نقطة القرار الوحيدة قبل أي كتابة). رفض/مهلة ⇒
    ERR_PERMISSION_DENIED (fail-closed — لا YOLO، Non-Goal §15.1).
    الكتابة المعتمدة تمر بنفس فحص المسار/denylist قبل اللمس.

  - ``session/request_permission``: يُترجم إلى طلب موافقة قياسي
    (kind ``acp_permission``) — النتيجة ``{"outcome": ...}`` حسب
    قرار البوابة، بلا رفع (البروتوكول يتوقع ردًّا لا خطأ).

  **عقد لا-بوابة ⇒ لا-تنفيذ** (سابقة AgentLoop/T-012): غياب
  ApprovalGate يعني رفض كل كتابة/إذن — آمن افتراضيًا.

  **عقد عدم-الترديد**: رسائل الأخطاء المعادة للوكيل عامة —
  لا مسارات محلولة ولا محتوى ولا تفاصيل استثناءات.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import pathlib
from typing import Any

from core.approval import ApprovalGate, ApprovalRequest, ProposedAction

from chain.path_policy import is_secret_file, resolve_workspace_path

from .connection import AcpProtocolError
from .protocol import (
    ERR_PATH_FORBIDDEN,
    ERR_PERMISSION_DENIED,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    Request,
)

logger = logging.getLogger(__name__)

# حد حجم القراءة — نفس فلسفة SafeReader (ملف عملاق لا يُغرق الجلسة)
MAX_READ_BYTES = 512 * 1024


class GovernedFsHandler:
    """معالج الطلبات العكسية — يُحقَن في AcpConnection(on_request=...).

    Args:
        workspace_root: جذر workspace — كل المسارات تُحلّ تحته حصرًا.
        approval_gate: بوابة الموافقة المشتركة (نفس كائن الجلسة) —
            ``None`` ⇒ كل كتابة/إذن يُرفض (لا بوابة ⇒ لا تنفيذ).
        source: وسم مصدر طلبات الموافقة (يظهر في سجل البوابة).
    """

    def __init__(
        self,
        workspace_root: str | pathlib.Path,
        approval_gate: ApprovalGate | None = None,
        source: str = "acp",
    ) -> None:
        self._root = pathlib.Path(workspace_root).resolve()
        self._gate = approval_gate
        self._source = source

    # ─── نقطة الدخول (عقد on_request في AcpConnection) ───

    def __call__(self, req: Request) -> Any:
        if req.method == "fs/read_text_file":
            return self._read_text_file(req.params)
        if req.method == "fs/write_text_file":
            return self._write_text_file(req.params)
        if req.method == "session/request_permission":
            return self._request_permission(req.params)
        raise AcpProtocolError(METHOD_NOT_FOUND,
                               f"طريقة غير مدعومة: {req.method}")

    # ─── المسار الآمن المشترك ───

    def _safe_path(self, raw: Any) -> pathlib.Path:
        """حلّ مسار الوكيل تحت workspace + إنفاذ denylist الأسرار.

        fail-closed: أي فشل (شكل/احتواء/symlink/سر) ⇒
        ERR_PATH_FORBIDDEN برسالة **عامة موحّدة** — لا نميّز
        «خارج الجذر» عن «سر» كي لا نؤكد وجود ملفات حساسة.
        """
        if not isinstance(raw, str) or not raw.strip():
            raise AcpProtocolError(INVALID_PARAMS, "path مطلوب")
        try:
            resolved = resolve_workspace_path(self._root, raw)
        except PermissionError:
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "مسار محظور")
        except Exception:
            # شكل مسار فاسد — لا تفاصيل (قد تعكس بنية القرص)
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "مسار محظور")
        if is_secret_file(resolved):
            logger.warning("acp: مُنعت محاولة وصول لملف سر (denylist)")
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "مسار محظور")
        return resolved

    # ─── fs/read_text_file ───

    def _read_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        path = self._safe_path(params.get("path"))
        try:
            data = path.read_bytes()
        except OSError:
            # غائب/مجلد/صلاحيات — رسالة عامة واحدة (لا تمييز)
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "تعذّرت القراءة")
        if len(data) > MAX_READ_BYTES:
            raise AcpProtocolError(ERR_PATH_FORBIDDEN,
                                   "الملف يتجاوز حد القراءة")
        return {"content": data.decode("utf-8", errors="replace")}

    # ─── fs/write_text_file (خلف ApprovalGate) ───

    def _write_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        content = params.get("content")
        if not isinstance(content, str):
            raise AcpProtocolError(INVALID_PARAMS, "content مطلوب")
        path = self._safe_path(params.get("path"))

        if self._gate is None:
            # لا بوابة ⇒ لا تنفيذ (سابقة T-012/AgentLoop)
            raise AcpProtocolError(ERR_PERMISSION_DENIED,
                                   "لا بوابة موافقة — الكتابة مرفوضة")
        rel = str(path.relative_to(self._root))
        action = ProposedAction(
            kind="acp_write",
            target=rel,
            payload=content,
            summary=f"وكيل ACP يطلب كتابة {rel}",
        )
        verdict = self._gate.request(
            ApprovalRequest(actions=[action], source=self._source))
        if not verdict.approved:
            # سبب البوابة (deny_mode/timeout/user_denied) آمن للترديد
            raise AcpProtocolError(ERR_PERMISSION_DENIED,
                                   f"رفضت البوابة الكتابة ({verdict.reason})")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError:
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "تعذّرت الكتابة")
        return {"written": True}

    # ─── session/request_permission (خلف ApprovalGate) ───

    def _request_permission(self, params: dict[str, Any]) -> dict[str, Any]:
        """إذن عام من الوكيل — البروتوكول يتوقع ردًّا بنتيجة لا خطأ:
        ``{"outcome": "approved" | "denied", "reason": ...}``."""
        title = params.get("title") or params.get("toolCall")
        summary = str(title)[:200] if title else "طلب إذن من وكيل ACP"
        if self._gate is None:
            return {"outcome": "denied", "reason": "no_gate"}
        action = ProposedAction(kind="acp_permission",
                                target="", payload="", summary=summary)
        verdict = self._gate.request(
            ApprovalRequest(actions=[action], source=self._source))
        return {"outcome": "approved" if verdict.approved else "denied",
                "reason": verdict.reason}
