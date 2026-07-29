# DECISION_LOG — سجل القرارات

> يُدار وفق الدستور (prompet_28_7_final.md): قيد لكل تغيير معماري **قبل**
> تعديل الكود. الصيغة: `Date, What changed, Why, Evidence, Task`.
> أُنشئ عند أول ADR في M8 (MASTER_ROADMAP.md:127).

| Date | What changed | Why | Evidence | Task |
|------|--------------|-----|----------|------|
| 2026-07-29 | استخراج توجيه رسائل WS من `_handle_ws_message` إلى جدول dispatch في وحدة جديدة `core/ws_router.py` (المقابض تبقى مؤقتًا في server.py) — ADR-001 | تفكيك g1 (QG-01 §R8) — الخطوة الأقل مخاطرة: فصل التوجيه فقط، بحفظ سلوك bit-identical (بما فيه no-op الصامت للنوع المجهول) | server.py:2034..2539 = 506 أسطر، 23 فرعًا/25 نوعًا؛ خريطة الفروع الكاملة في §TSK-611 (DEVELOPMENT_TASKS.md)؛ لا فرع else؛ المستدعي الوحيد ws_handler:2554 | TSK-611 |
| 2026-07-29 | نقل جسم `_dispatch_chat_message` (486 سطرًا) إلى `core/chat_dispatch.py` مع كائن deps يُبنى وقت النداء في غلاف server — ADR-002 | QG-02 §R8 — أكبر كتلة متبقية في g1؛ الحقن الحي يحفظ monkeypatch الاختبارات على فضاء server وقراءة globals المتغيّرة وقت النداء | server.py:1549..2034؛ 26 رمزًا خارجيًا مصنّفة في §TSK-612؛ 4 ملفات اختبار ترقّع server (except_narrowing:67، prompt_fencing:82، scan_start:76/92، instrumentation_609:225) | TSK-612 |
