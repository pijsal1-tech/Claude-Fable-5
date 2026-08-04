# -*- coding: utf-8 -*-
"""T-048 (R-701): SessionContext — حالة المحادثة لكل اتصال WebSocket.

المشكلة: تبويبان مفتوحان كانا يتشاركان globals المحادثة في server.py
(chat_history، مقبض المشروع، الموديل، صندوق الموافقات) فيخرّب كلٌّ
منهما حالة الآخر. الحل: كل اتصال WS يحصل عند فتحه على SessionContext
خاصّ به، مركّب فوق خدمات AppContext المشتركة (pool/registry/engines).

═══════════════ قواعد نطاق الحالة (State-Scoping Rules) ═══════════════

1. **مشترك على مستوى العملية (AppContext / خدمات main())**:
   provider_pool، execution_registry، approval_gate، request_router،
   orchestrator، agent_tools، event_bus الرصدي — تُقرأ من الـ handlers
   كخدمات لا كحالة، ولا يُعاد ربطها أبدًا من داخل handler.

2. **خاص بالاتصال (SessionContext — هذا الملف)**:
   - ``project``: مقبض ProjectHandle خاص بالتبويب. تبديل المشروع من
     تبويب لا يمس ``ctx.project`` المشترك ولا يُبطل مقابض التبويبات
     الأخرى (خلافًا لـ REST ``/api/switch-project`` الذي يبدّل عالميًّا).
   - ``chat_history``: قائمة رسائل مستقلة (تُبذر بنسخة من التاريخ
     المحمّل وقت الاتصال ثم تتباعد).
   - ``model_provider``: اختيار موديل خاص بالتبويب — يتقدّم على
     المصدر المشترك عند ضبطه.
   - ``active_agent_loop`` / ``delegate_bridge`` / ``chain_bridge``:
     صندوق الموافقات — ردود approval/cancel تصل لحلقات هذا الاتصال فقط.
   - ``bus`` / ``adapter`` / ``send``: اشتراك الأحداث (R-604) — إطارات
     هذا الاتصال تصل لعميله فقط.
   - ``backup_done_for_batch``: علم الباك-أب لكل batch — لكل تبويب.

3. **ممنوع (يفرضه scripts/lint_handler_state.py عبر check.sh)**:
   دوال الـ handlers (``ws_handler`` / ``_handle_ws_message``) لا
   تحتوي ``global`` ولا تلمس أسماء حالة المحادثة الوحدوية ولا أي اسم
   وحدوي مربوط بقيمة قابلة للتغيير (list/dict/set) — الاستثناء الوحيد
   أسماء UPPER_CASE الثابتة ومراجع الخدمات.

4. **التنظيف عند القطع**: ``close()`` تُلغي الحلقة النشطة وجسر
   السلسلة وتفك اشتراك المحوّل — idempotent.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable
from core.structured_log import swallowed as _slog_swallowed


def _no_provider() -> Any:
    """مصدر مزوّد افتراضي — لا شيء (يُستبدل عند التركيب في server)."""
    return None


def _no_banner() -> str:
    """مصدر بانر افتراضي — فارغ (يُستبدل عند التركيب في server)."""
    return ""


@dataclass
class SessionContext:
    """حالة محادثة اتصال WS واحد — تُبنى عند الاتصال وتُغلق عند القطع.

    ``send`` هو ناشر إطارات هذا الاتصال (dict → bus → _WSAdapter →
    ws.send)؛ كل ما عداه حالة محادثة أو مراجع خدمات مثبّتة وقت الاتصال.
    """

    send: Callable[[dict], None]
    ctx: Any = None                      # AppContext المشترك (قد يكون None في الاختبارات)
    bus: Any = None                      # EventBus خاص بالاتصال (R-604)
    adapter: Any = None                  # _WSAdapter — يُغلق عند القطع
    project: Any = None                  # ProjectHandle خاص بالاتصال
    chat_history: list = field(default_factory=list)
    session_mgr: Any = None              # ربط الجلسة (مرجع مثبّت وقت الاتصال)
    chain_bridge: Any = None             # جسر السلسلة (موافقات chain لهذا الاتصال)
    delegate_bridge: Any = None          # جسر التفويض (يُنشأ كسولًا لكل اتصال)
    background_task: Any = None          # مهمة تفويض خلفية (TSK-732/D-19-4 — كائن جديد لكل مهمة)
    active_agent_loop: Any = None        # حلقة الـ Agent النشطة لهذا الاتصال
    model_provider: Any = None           # اختيار موديل خاص بالتبويب (يتقدّم عند ضبطه)
    provider_source: Callable[[], Any] = _no_provider
    banner_source: Callable[[], str] = _no_banner
    backup_done_for_batch: bool = False
    closed: bool = False

    # ── مقبض المشروع ─────────────────────────────────────
    @property
    def fm(self) -> Any:
        """FileManager مشروع هذا الاتصال (None قبل الربط)."""
        return self.project.fm if self.project is not None else None

    @property
    def cmd_runner(self) -> Any:
        """CommandRunner مشروع هذا الاتصال (None قبل الربط)."""
        return self.project.cmd_runner if self.project is not None else None

    def switch_project(self, path: str) -> Any:
        """تبديل مشروع **هذا الاتصال فقط** — R-701.

        يبني مقبضًا جديدًا عبر ``ctx.handle_factory`` دون تبديل
        ``ctx.project`` المشترك ودون إبطال مقابض الاتصالات الأخرى —
        تبويب B يبدّل ومقبض تبويب A يبقى صالحًا بنفس الهوية.
        """
        if self.ctx is None:
            raise RuntimeError("SessionContext.switch_project يتطلب AppContext")
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            raise NotADirectoryError(abs_path)
        handle = self.ctx.handle_factory(abs_path)
        self.project = handle
        return handle

    # ── اختيار الموديل ───────────────────────────────────
    def active_provider(self) -> Any:
        """المزوّد الفعّال: اختيار التبويب أولًا ثم المصدر المشترك."""
        if self.model_provider is not None:
            return self.model_provider
        return self.provider_source()

    # ── البانر (R-303) ───────────────────────────────────
    @property
    def binding_banner(self) -> str:
        """بانر تنبيه الربط — يُقرأ عبر المصدر (تملكه مسارات REST)."""
        return self.banner_source()

    # ── التنظيف عند القطع ────────────────────────────────
    def close(self) -> None:
        """تنظيف القطع — idempotent: إلغاء الحلقة والجسر وفك الاشتراك."""
        if self.closed:
            return
        self.closed = True
        loop, self.active_agent_loop = self.active_agent_loop, None
        if loop is not None:
            try:
                loop.cancel()
            except Exception as _exc:
                _slog_swallowed("core/session_context.py:130", _exc)
                pass
        if self.chain_bridge is not None:
            try:
                self.chain_bridge.cancel("WebSocket disconnected")
            except Exception as _exc:
                _slog_swallowed("core/session_context.py:135", _exc)
                pass
        if self.adapter is not None:
            try:
                self.adapter.close()
            except Exception as _exc:
                _slog_swallowed("core/session_context.py:140", _exc)
                pass
