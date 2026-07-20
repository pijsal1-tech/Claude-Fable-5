# -*- coding: utf-8 -*-
"""T-048 (R-701): fixture انتهاك — يجب أن تفشل عليه بوابة
scripts/lint_handler_state.py (يُستخدم في الاختبارات فقط، ليس إنتاجًا).

يعيد إنتاج الخلل القديم حرفيًا: handler يقرأ/يكتب حالة محادثة وحدوية
(قائمة قابلة للتغيير + ``global``) — تبويبان يخربان حالة بعضهما.
"""

chat_history = []          # حالة وحدوية متغيّرة — ممنوعة في الـ handlers
_pending_approvals = {}    # dict وحدوي متغيّر
MAX_FRAMES = 100           # ثابت UPPER_CASE — مسموح


def ws_handler(ws):
    """handler ينتهك القاعدة بثلاث طرق."""
    global chat_history                      # انتهاك 1: global
    chat_history.append("msg")               # انتهاك 2: قراءة اسم وحدوي متغيّر
    _pending_approvals["x"] = ws             # انتهاك 3: dict وحدوي
    return MAX_FRAMES                        # مسموح — ثابت


def _handle_ws_message(ctx, sctx, msg):
    """التوقيع الصحيح لكن يقرأ حالة وحدوية — انتهاك أيضًا."""
    return len(chat_history)
