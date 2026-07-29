# ARCHITECTURE_DECISIONS — سجل قرارات المعمارية (ADRs)

> يُدار وفق الدستور (prompet_28_7_final.md:1038، :1102): كل تغيير معماري
> يتطلب ADR + قيدًا في DECISION_LOG.md **قبل** تعديل الكود.
> الصيغة: `ADR-NNN: Context, Decision, Alternatives rejected, Trade-offs, Status`.

---

## ADR-001: استخراج راوتر رسائل WS إلى `core/ws_router.py` (جدول dispatch)

- **Task**: TSK-611 (M8 — QG-01 §R8) · **Date**: 2026-07-29 (S59)

### Context
`server.py` هو god-module (المعرَّف g1 في المراجعة المعمارية). أكبر كتلة
توجيه فيه هي `_handle_ws_message` (server.py:2034..2539 — **506 أسطر**،
**23 فرعًا** أعلى-مستوى على `msg_type` / 25 نوعًا نصيًا؛ الأدلة الكاملة في
§TSK-611 بـ DEVELOPMENT_TASKS.md). الكتلة تمزج التوجيه (أي مقبض لأي نوع)
مع أجسام المقابض نفسها، بنمط مختلط: `if...return` مبكرة لأول ~7 أنواع ثم
سلسلة `if/elif` واحدة، وبدون `else` (نوع مجهول = no-op صامت).
خطة M8 (MASTER_ROADMAP.md:116) تفكك g1 على 4 خطوات (QG-01→04) بترتيب
مخاطرة صريح، وQG-01 هو الأقل خطرًا: فصل التوجيه فقط.

### Decision
إنشاء وحدة نقية `core/ws_router.py` تحوي:
1. **جدول dispatch**: قاموس `msg_type → handler` يُبنى مرة واحدة عبر
   دالة تسجيل تستقبل المقابض من server.py (حقن — الوحدة لا تستورد
   server.py، لا دورة استيراد).
2. **دالة `dispatch(handlers, ctx, sctx, msg)`**: تستخرج
   `msg.get("type", "")`، تبحث في الجدول، تستدعي المقبض الموجود
   بتوقيع `(ctx, sctx, msg)`، وتعيد no-op صامتًا للنوع المجهول
   (حفظ السلوك القائم حرفيًا — لا else، لا log جديد).

المقابض نفسها تبقى **مؤقتًا** في server.py كدوال بأسماء
`_ws_<msg_type>(...)`، تُسجَّل في الجدول عند تعريفها. الأنواع المركّبة
(`rollback_run`/`rollback_file`، `apply_all_actions`/`execute_plan`)
تُسجَّل كمفتاحين لنفس المقبض. البحث القاموسي يكافئ دلالة
أول-تطابق-يفوز الحالية لأن كل نوع يظهر في فرع واحد فقط (تحقق بالأدلة).

### Alternatives rejected
1. **نقل أجسام المقابض كاملة إلى الوحدة الآن**: يخالف نص المهمة
   («بقاء المقابض نفسها مؤقتًا في server.py») ويضخّم المخاطرة —
   المقابض تلمس عشرات رموز server الداخلية (RUNNERS،
   execution_registry، `_dispatch_chat_message`…)؛ نقلها موضوع
   QG-02..04 اللاحقة.
2. **راوتر صنفي (class-based Router مع تسجيل decorator)**: يضيف حالة
   وصنفًا دون حاجة — جدول قاموسي + دالة نقية أبسط وأسهل اختبارًا
   ويحقق نفس الفصل.
3. **إبقاء السلسلة الشرطية مع تقسيمها لدوال داخل server.py فقط**:
   يقلّص الكتلة لكنه لا يفصل التوجيه عن الوحدة الضخمة — لا يحقق
   هدف QG-01 المعماري (وحدة توجيه مستقلة قابلة للاختبار بمعزل).

### Trade-offs
- (+) كتلة `_handle_ws_message` تهبط ≥ 300 سطر؛ التوجيه يصبح بيانات
  (جدولًا) قابلة للفحص والاختبار بمعزل عن Flask/WS.
- (+) يمهد QG-02..04: نقل المقابض لاحقًا يصبح تحريك دوال مسجّلة.
- (−) مستوى غير مباشرة إضافي (قفزة عبر الجدول) — مقروئية التتبع
  تتطلب النظر في الجدول؛ يُخفَّف بتسمية موحّدة `_ws_<type>`.
- (−) مرحلة انتقالية: المقابض ما تزال في server.py — الفصل الكامل
  مؤجل عمدًا (ترتيب المخاطرة §R8).

### Status
**Accepted** (S59) — يُنفَّذ في TSK-611.

---

## ADR-002: استخراج `_dispatch_chat_message` إلى `core/chat_dispatch.py` بحقن التبعيات وقت النداء

- **Task**: TSK-612 (M8 — QG-02 §R8) · **Date**: 2026-07-29 (S61)

### Context
بعد QG-01 (ADR-001) بقيت أكبر كتلة في server.py هي
`_dispatch_chat_message` (:1549..2034 — **486 سطرًا**): كشف مسارات +
جمع سياق + توجيه (router/chain/delegate) + Agent + direct fallback.
تستعمل 26 رمزًا خارجيًا: مستوردات نقية، و11 رمزًا معرّفًا في server.py
(RUNNERS، `_begin_run_ticket`، parser، event_bus…)، وglobals متغيّرة
تُربط في main() (`request_router`، `agent_tools`).
**قيد حرج**: 4 ملفات اختبار ترقّع رموزًا على فضاء أسماء server
(`monkeypatch.setattr(server, "gather_message_context", …)` إلخ) —
نقل ساذج يقرأ الرموز من فضاء الوحدة الجديدة يكسر الترقيع بصمت.

### Decision
1. وحدة جديدة `core/chat_dispatch.py` تحوي جسم الدالة كـ
   `dispatch_chat_message(deps, ctx, sctx, user_text, mode, msg,
   skip_path_detection=False, attached_context=None)` حيث `deps`
   كائن بسيط (SimpleNamespace/dataclass) يحمل **مراجع server الحية**.
2. `server._dispatch_chat_message` يبقى بنفس الاسم والتوقيع كغلاف
   يبني `deps` **وقت كل نداء** من رموز فضاء server (late binding):
   `deps.gather_message_context = gather_message_context` إلخ —
   فيبقى monkeypatch على server فعّالًا حرفيًا، وتبقى globals
   المتغيّرة (`request_router`/`agent_tools`) مقروءة وقت النداء.
3. الوحدة لا تستورد server (لا دورة)؛ المستوردات النقية
   (build_prompt، RoutingTier، AgentLoop…) تُستورد فيها مباشرة —
   **عدا** `gather_message_context` و`os` (يُرقّعان في الاختبارات
   على server) فيمرّان عبر deps.
4. الوحدة تحت `core/` فتدخل بوابة mypy القائمة (check.sh:12)
   تلقائيًا — يحقق شرط القبول.

### Alternatives rejected
1. **نقل حرفي مع `import server` داخل الوحدة**: دورة استيراد +
   يبقي الاقتران بالوحدة الضخمة — عكس هدف QG-02.
2. **تحديث الاختبارات الأربعة لترقيع الوحدة الجديدة**: يعدّل
   اختبارات مثبّتة للسلوك أثناء تغيير بنيوي (خلط إشارات) ويكسر
   نمط «الاختبارات تثبت server كواجهة» المعتمد في 611.
3. **تمرير كل رمز كمعامل منفصل (14+ معاملًا)**: توقيع هش؛ كائن
   deps واحد أوضح ويتوسع في QG-03/04.

### Trade-offs
- (+) server.py يفقد ~470 سطرًا صافيًا (أكبر كتلة متبقية)؛ المنطق
  يدخل نطاق mypy؛ الاختبارات القائمة تعمل دون تعديل.
- (−) مستوى غير مباشرة (deps) — يُخفَّف بأسماء حقول مطابقة لأسماء
  رموز server حرفيًا.
- (−) الغلاف يبقى في server.py (~30 سطرًا) — مقبول؛ يُزال عند
  QG-03/04 حين تنتقل الرموز المشتركة نفسها.

### Status
**Accepted** (S61) — يُنفَّذ في TSK-612.

---

## ADR-003 — تجميع REST routes في Flask Blueprints بحقن كائن الوحدة (TSK-613)

### Context
QG-03 (§R8): server.py يحوي 28 مزيّن `@app.route` (:704..1385، ~640
سطرًا) — آخر كتلة g1 الكبرى بعد QG-01/02. المهمة مشروطة بـ«استقرار
قرار g5»: NF-03 (الازدواجية REST-globals/WS-SessionContext) مسجل
«مفتوح — مقبول موثَّق» والتوحيد مؤجل FI-01 (FUTURE_IMPROVEMENTS:16) —
أي أن الوضع الراهن للـ globals هو القرار المستقر. خطر «تجميد
الازدواجية في الواجهات» (MASTER_REVIEW:543) يُحيَّد بألا تُمرَّر
globals كقيم وقت التسجيل بل تُقرأ حيًّا من نقطة واحدة.

### Decision
1. حزمة `routes/` جديدة: 7 وحدات موضوعية (files، backups، run،
   sessions، meta، rollback، project) تنقل **25 route بأجسام حرفية**.
2. نمط الوصول للحالة: كل وحدة تحمل `_srv = None` ودالة
   `register(app, srv)` — server.py يستدعيها بـ `register(app,
   sys.modules[__name__])` فتقرأ الأجسام `_srv.fm`/`_srv.session_mgr`…
   **وقت كل نداء** (late binding — نفس مبدأ ADR-002): monkeypatch
   الاختبارات على فضاء server يبقى فعّالًا، وglobals المتغيّرة
   (switch-project يستبدل fm/cmd_runner) تُقرأ طازجة.
3. إعادة ربط globals (api_clear/load_session/new_session/
   switch_project) عبر تعيين سمة: `_srv.chat_history = []` —
   التكافؤ الحرفي لعبارة `global` (كلاهما يعيد ربط اسم على كائن
   الوحدة).
4. تبقى في server.py: `index` (app-level)، `api_models` +
   `api_switch_model` (provider-routing — خارج النطاق §0.8)،
   والمساعدات المشتركة (`_search_service`، `_zip_member_violations`،
   `_session_binding_policy`، `_force_command_approval`) تستدعى عبر
   `_srv.<name>` — تُرقَّع اليوم على server في الاختبارات.
5. routes/ لا تستورد server (لا دورة)؛ المستوردات النقية
   (jsonify/request/Message/FileManager/CommandRunner/os/pathlib)
   تُستورد مباشرة في كل وحدة.
6. أسماء endpoints تتغير تلقائيًا (`files.api_files`…) — مثبت
   بالأدلة: صفر استخدام لـ `url_for`/`view_functions` في المستودع؛
   سطح HTTP (rule+methods) هو العقد ويبقى بلا تغيير (30 قاعدة).

### Alternatives rejected
1. **تمرير globals كوسائط عند التسجيل**: يجمّد قيم لحظة الإقلاع —
   يكسر switch-project (يعيد ربط fm) وهو بالضبط خطر MASTER_REVIEW:543.
2. **انتظار FI-01 (توحيد الحالة) قبل التجميع**: FI-01 تحسين مستقبلي
   بلا موعد؛ الحقن الحي يجعل الترتيب غير مقيِّد — نقطة `_srv` الواحدة
   تُستبدل لاحقًا بمحلّ جلسة دون مسّ الأجسام.
3. **Blueprint واحد كبير**: يحقق النقل لا التنظيم الموضوعي المطلوب
   نصًّا (rollback/memory/project/…).
4. **نقل api_models/api_switch_model معهما**: provider-routing
   خارج النطاق §0.8 — لا تُلمسان.

### Trade-offs
- (+) server.py يفقد ~640 سطرًا؛ كل مجال REST قابل للقراءة/الاختبار
  منفردًا؛ يمهد TSK-614 (mypy) وFI-01.
- (−) مستوى غير مباشرة `_srv` — مخفَّف بأسماء مطابقة حرفيًا لرموز
  server.
- (−) 3 اختبارات بنيوية تُحدَّث لنفس الضمانة في الموقع الجديد
  (سابقة TSK-611/612).

### Status
**Accepted** (S65) — يُنفَّذ في TSK-613.
