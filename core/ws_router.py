"""TSK-611 (QG-01 §R8، ADR-001): راوتر رسائل WebSocket — جدول dispatch نقي.

المشكلة: توجيه رسائل WS كان سلسلة شرطية من 23 فرعًا (506 أسطر) داخل
``_handle_ws_message`` في server.py (g1 god-module) — التوجيه ممزوج
بأجسام المقابض ولا يُختبر بمعزل.

الحل: فصل «التوجيه» كبيانات — قاموس ``msg_type → handler`` تبنيه
composition root (server.py) وتمرّره إلى :func:`dispatch`. المقابض
نفسها بقيت في server.py — QG-02..04 (TSK-612..614 ✅) نقلت مسار
الإرسال والـblueprints وبوابة mypy لا أجسام مقابض WS؛ نقلها
المتبقي backlog مُسعَّر: FI-02 (تفكيك server.py — قرار مالك).

القرارات (ADR-001):
- الوحدة نقية: لا تستورد server.py ولا Flask — لا دورة استيراد،
  تُختبر بقاموس مقابض وهمية.
- البحث القاموسي يكافئ دلالة أول-تطابق-يفوز للسلسلة الأصلية لأن
  كل نوع كان يظهر في فرع واحد فقط (أدلة §TSK-611).
- **حفظ السلوك حرفيًا**: نوع مجهول → no-op صامت (السلسلة الأصلية
  بلا else) — لا log ولا استثناء.
- توقيع المقابض الموحّد ``handler(ctx, sctx, msg)`` — نفس عقد
  ``_handle_ws_message`` (T-048/R-701: حالة المحادثة عبر sctx فقط).
"""


def dispatch(handlers, ctx, sctx, msg):
    """وجّه رسالة WS واحدة إلى مقبضها من جدول ``handlers``.

    ``handlers``: قاموس ``msg_type → callable(ctx, sctx, msg)``.
    نوع غير معروف = لا شيء يحدث (سلوك السلسلة الأصلية بلا else).
    يعيد ما يعيده المقبض (المقابض الحالية تعيد None).
    """
    handler = handlers.get(msg.get("type", ""))
    if handler is None:
        return None
    return handler(ctx, sctx, msg)
