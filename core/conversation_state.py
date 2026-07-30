# -*- coding: utf-8 -*-
"""TSK-707 (FI-01/1 — دفعة D-7): ConversationState — المخزن القانوني الموحد.

المشكلة (NF-03 / خطر g5 — FUTURE_IMPROVEMENTS.md FI-01): حالة المحادثة
المشتركة كانت globals خام في server.py (``chat_history`` @ :141،
``_binding_banner`` @ :145) تُطفَّر مباشرة من 12 موقعًا في routes/*
بينما مسار WS يبذر ``SessionContext`` نسخةً وقت الاتصال — مساران
منفصلان لنفس الحالة = فئة كاملة من أخطاء الحالة المتقادمة.

الحل: مخزن واحد بعمليات مسماة خلف قفل RLock — كل كتابات/قراءات REST
وبذر WS تمر عبره (التوصيل في TSK-708..710؛ هذا الملف مستقل عمدًا).

═══════════════ قواعد النطاق (ملزمة — قرار D-7) ═══════════════

1. **هذا المخزن هو الحالة القانونية المشتركة** (process-wide):
   ما كان globals يصبح خلف عمليات مسماة — لا وصول خام بعد التوصيل.
2. **عزل التبويبات (T-048) يبقى كما هو**: كل اتصال WS يبذر *نسخة*
   عبر ``snapshot()`` ثم يتباعد — هذا المخزن لا يلغي SessionContext
   ولا يمس قواعد lint_handler_state.
3. **لا منطق أعمال هنا**: المخزن يحفظ ويعيد فقط — دلالة الجلسات
   (warn/fork/block، التحميل، المسح) تبقى في مواقعها.
4. **العقد**: localhost مستخدم واحد — القفل يحمي من سباق
   REST-thread/WS-thread لا من تعدد مستخدمين.

الاستيرادات: providers.base فقط (اتجاه قائم سلفًا —
core/chat_dispatch.py:34 يستورده) — صفر دورات (حارس FI-08).
"""
from __future__ import annotations

import threading

from providers.base import Message


class ConversationState:
    """حالة المحادثة المشتركة: التاريخ + بانر ربط الجلسة (R-303).

    كل العمليات ذرّية خلف ``RLock`` واحد. القوائم المُعادة نسخ
    معزولة دائمًا (لا تسريب مرجع داخلي — الطفرة الخارجية لا تمس
    المخزن، والعكس).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: list[Message] = []
        self._binding_banner: str = ""

    # ── التاريخ ──────────────────────────────────────────────

    def append(self, message: Message) -> None:
        """إلحاق رسالة واحدة بنهاية التاريخ."""
        with self._lock:
            self._history.append(message)

    def replace_all(self, messages: list[Message]) -> None:
        """استبدال التاريخ كاملًا (مسار تحميل جلسة) — يُخزَّن كنسخة."""
        with self._lock:
            self._history = list(messages)

    def clear(self) -> None:
        """مسح التاريخ (جلسة جديدة / clear / fork)."""
        with self._lock:
            self._history = []

    def snapshot(self) -> list[Message]:
        """نسخة معزولة من التاريخ — لبذر SessionContext ولقراءات REST.

        الطفرة على الناتج لا تمس المخزن (عقد T-048: التبويب يتباعد).
        """
        with self._lock:
            return list(self._history)

    def __len__(self) -> int:
        """طول التاريخ (يخدم ``history_length`` في /api/status)."""
        with self._lock:
            return len(self._history)

    # ── بانر ربط الجلسة (R-303) ──────────────────────────────

    @property
    def binding_banner(self) -> str:
        """قراءة بانر تنبيه الربط الحالي ("" = لا تنبيه)."""
        with self._lock:
            return self._binding_banner

    def set_banner(self, text: str) -> None:
        """ضبط بانر تنبيه الربط (سياسة warn)."""
        with self._lock:
            self._binding_banner = text

    def clear_banner(self) -> None:
        """إزالة البانر (جلسة جديدة / fork / clear)."""
        with self._lock:
            self._binding_banner = ""
