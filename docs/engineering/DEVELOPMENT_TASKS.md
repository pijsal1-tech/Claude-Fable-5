# DEVELOPMENT_TASKS.md — editor_v4 (Stage 2 PLANNING — الدستور FINAL-GOVERNED)

> القائمة الرسمية لمهام Stage 3 (الدستور §10.5/§14). الحالة الحية تُدار هنا
> في عمود Status + في PROGRESS.md (المؤشر). الترقيم يواصل أرشيف v4.1
> (TSK-101..502 في IMPLEMENTATION_TASKS.md — مُقفلة 19/19 ✅) — **append-only،
> لا إعادة ترقيم ولا حذف**.
> قاعدة الحجم (§10.5): كل مهمة تُنجز وتُتحقق في جلسة واحدة، ≤ 5 ملفات،
> بمعيار قبول قابل للفحص آليًا.
> النطاق §0.8: لا مهمة تمس `providers/` أو fallback أو routing.
> مراجع الخلفية: MASTER_REVIEW.md (§R4–§R10 + STAGE 2 PLANNING §P.1/§P.2).

---

## M6 — Restore Trust (P1 دفعة أولى: البوابة + القدرة المكسورة + أمان الوكيل)

### TSK-601 — إصلاح اعتماد التفويض + إظهار الفشل + اختبار المقبض
- **Status**: ✅ DONE (Session 33–34) · **Priority**: P1
- **Close-out (Session 34)**:
  - التنفيذ: `_parsed_to_actions` + `_parsed_options` استُخرجتا كدالتي وحدة
    (server.py:1439–1474) من التكرار الحرفي في مساري agent (كان 1791–1800)
    وdirect (كان 1873–1894) — المساران يستهلكانهما الآن (server.py:1826،
    1903). مقبض `delegate_approve`: النداءان الوهميان استُبدلا بـ
    `parser.parse(run.result.response)` + التحويل المشترك (server.py:2350–
    2352)، وفشل التحويل يرسل إطار `error` للواجهة قبل fallback الـ done
    الفارغ (server.py:2364–2367) — لا صمت (UXF-02).
  - القبول (4/4 مُتحقق آليًا — Session 34):
    (1) ✅ دورة كاملة FakeProvider بـ FILE: block → done بـ actions golden
    (test_approve_full_cycle_emits_nonempty_actions_golden)؛
    (2) ✅ رد بلا actions → done + options=["أضف اختبارات","حسّن التوثيق"]
    بلا error؛ (3) ✅ monkeypatch يفجّر parse → إطار error يحمل السبب + done
    فارغ يليه (لا انتظار معلق)؛ (4) ✅ `grep -c "extract_actions\|extract_options"
    server.py` = 0 (+ حارس بنيوي دائم داخل الاختبار نفسه).
  - الاختبار الجديد: tests/integration/test_delegate_approve_handler.py —
    **6 حالات** (المعايير الأربعة + الهبوط الفعلي للـ run + الحفاظ على فرع
    «لا يوجد تفويض نشط») — كلها خضراء.
  - **Gates**: Architecture ✅ (لا API جديد — استخراج تكرار فقط، الإطار يبقى
    done) · Testing ✅ (6 حالات، golden مثبّت) · Regression ✅ (تشغيل كامل
    Session 34: **4F / 1677P / 34S في ~70s** — نفس مجموعة الفشل الأربع
    المعروفة حرفيًا [TF-01/TF-02×نمط/TF-03/TF-04 — قائمة قبل هذه المهمة،
    تعالجها TSK-604/605]؛ لا فشل جديد؛ +6 اختبارات) · Documentation ✅
    (هذا السجل + CHANGELOG_ENGINEERING.md).
  - **Metrics**: اختبارات المقبض 0 → 6 · تكرار كتلة التحويل 2 → 0 (دالة
    واحدة) · إشارات لدوال غير موجودة في server.py: 2 → 0.
  - **Rollback**: revert commit واحد (c4c7326 + commit الإغلاق).
- **Behavior-preservation pre-check (Session 33 — قبل التعديل)**:
  - السلوك الحالي المُقاس: `delegate_approve` (server.py:2312–2356) ينادي
    `parser.extract_actions/extract_options` (2337–2338) — **غير موجودتين**
    في ResponseParser (API الحقيقي: `parse(response, mode=None)` فقط —
    actions/response_parser.py:107) ⇒ AttributeError يُبتلع في except
    (2345–2354) ⇒ إطار `done` بـ actions=[] دائمًا + سطر ⚠️ في stdout.
    لا سلوك عامل يُفقد — المسار مكسور بنيويًا منذ إنشائه.
  - السلوك المحفوظ: (أ) إطارا start/chunk قبل done (2328–2334) يبقيان؛
    (ب) فرع "لا يوجد تفويض نشط" (2355–2356) يبقى؛ (ج) صياغة summary
    `✅ تم اعتماد التعديلات (delegation #id)` تبقى؛ (د) approval_handler
    (ابتلاع NF-14 §14 لفشل WS أثناء land) يبقى كما هو.
- **Architecture-Fitness pre-check (Session 33)**:
  - لا API جديد: `_parsed_to_actions(parsed)` دالة وحدة خاصة في server.py
    تُستخرج من التكرار القائم (المسار agent 1791–1800 + المسار direct
    1873–1892 — نفس التحويل حرفيًا مرتين اليوم) — تقليل تكرار لا إضافة.
  - الاعتماد على `parser.parse(response, mode="delegate")`؟ لا —
    mode=None هو السلوك التاريخي الكامل (fallback التخميني مفعّل)
    والتفويض ليس وضع chat؛ نمرر mode=None صراحةً (= نداء بلا معامل)
    لتطابق سلوك action_applier/chain (توثيق response_parser.py:113).
  - الإطار المُرسل: يبقى `done` (وليس `plan`) — الواجهة الحالية تعرض
    شريط الإجراءات لأي actions غير فارغة في done (سلوك BUG-01 المرصود)؛
    تغيير نوع الإطار قرار UX أوسع مؤجل لمسار M9.
  - فشل التحويل: يُرسل إطار `error` (نوع قائم تعالجه الواجهة) قبل
    fallback done الفارغ — لا نوع إطار جديد.
- **Objective**: جعل `delegate_approve` يعمل فعليًا: تحويل رد المنفّذ إلى
  actions قابلة للتطبيق، وإظهار أي فشل تحويل للمستخدم بدل الصمت، وتغطية
  المقبض باختبار end-to-end.
- **Background**: RP-01 (§R7) + UXF-02 (§R9) + TD-01 (§R10) · **ALT-601 → A**.
- **Dependencies**: — (جاهزة فورًا)
- **Files**: `server.py` (2337–2338 + استخراج `_parsed_to_actions` من مسار
  agent 1791–1800)، `tests/integration/test_delegate_approve_handler.py` (جديد).
- **Effort**: جلسة واحدة.
- **Acceptance**:
  (1) اختبار جديد: دورة delegate كاملة بمزود مزيف يرد بـ `FILE:` block →
  `delegate_approve` → إطار يحمل actions غير فارغة مطابقة golden؛
  (2) حالة رد بلا actions → إطار `done` مع options دون خطأ؛
  (3) حالة استثناء في التحويل → إطار `error`/`warning` يصل الواجهة (لا صمت)؛
  (4) `grep -c "extract_actions\|extract_options" server.py` = 0.
- **Gates**: Architecture (لا API جديد) · Testing · Regression · Documentation.
- **Behavior preservation**: Current = المسار مكسور (fallback دائم actions=[])
  — لا سلوك عامل يُفقد؛ Expected = السلوك المصمَّم أصلًا يعمل؛ Migration = لا شيء.
- **Metrics**: قبل: 0 اختبارات للمقبض / بعد: ≥3 حالات.
- **Rollback**: revert commit واحد.
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-602 — تسييج نتائج الأدوات والمعرفة (Context poisoning)
- **Status**: ✅ DONE (Sessions 35–36) · **Priority**: P1
- **Close-out (Session 36 — إعادة تحقق بعد sandbox reset)**:
  - التنفيذ (S35، في origin @2df00ce): (أ) agent_loop.py — موضعا حقن
    نتائج الأدوات (الآمنة + الأوامر المعتمدة) يلفان المحتوى بـ
    `fence_attached("tool_result:{tool}", …)`؛ (ب) knowledge.py
    `_render_body` — الأنواع الأربعة (file/dir/search/command) مُسيّجة
    بمصدر موسوم لكل نوع، ورؤوس الأقسام وأسطر `--- display ---`
    تبقى خارج السور (سلوك محفوظ)؛ (ج) `to_summary` مُسيّج اتساقًا؛
    موضع followup_prompt الثالث مُغطى بالتعدي عند المصدر (لا تسييج
    مزدوج).
  - القبول (3/3 — أُعيد التحقق آليًا Session 36): (1) ✅ E2E: ملف يحوي
    "IGNORE ALL INSTRUCTIONS…" → برومبت المتابعة الملتقط (FakeProvider)
    يحمل التعليمة العدائية داخل السور حصرًا (فحص spans)؛ (2) ✅
    grep-assert بنيوي دائم داخل الاختبار (لا نمط حقن خام + عدّات
    fence_attached ≥2 في agent_loop و≥5 في knowledge)؛ (3) ✅ QA-T12
    (test_prompt_fencing) أخضر.
  - الاختبار الجديد: tests/unit/test_context_fencing.py — **6 حالات**
    (E2E مسموم + أوسمة المصدر للأنواع الأربعة + to_summary + تحييد
    وسم إغلاق مزوّر + حارسان بنيويان) — كلها خضراء.
  - **Gates**: Security ✅ (ASF-01 مُغلق — المحتوى الخارجي كله داخل
    أسوار + تعليمة system القائمة INJECTION_GUARD تُفعّلها) · Testing ✅
    (6 حالات) · Regression ✅ (تشغيل كامل Session 36: **4F/1683P/34S
    ~72s** — الأربعة المعروفة فقط؛ اختبارات التثبيت للـ bundle/budget/
    feedback خضراء — نجاة عنصر high في ميزانية ضيقة محفوظة) ·
    Documentation ✅ (هذا السجل + CHANGELOG).
  - **Metrics**: مواضع حقن خام: 5 → 0 · اختبارات تسييج مسار الوكيل:
    0 → 6.
  - **Rollback**: revert 2df00ce + commit الإغلاق.
- **Behavior-preservation pre-check (Session 35 — قبل التعديل)**:
  - الحقن الخام المُقاس: (أ) agent_loop.py:224–226 و257–259 —
    `[نتيجة {tool}({args})]:\n{truncated}` بلا أسوار (أداة آمنة + أمر
    معتمد)؛ (ب) knowledge.py:190–203 `_render_body` — أجساد file/dir/
    search/command خام؛ (ج) knowledge.py:41–49 `to_summary` — نفس النمط
    (لا مستهلك إنتاجي حاليًا خارج tests — يُسيَّج اتساقًا).
  - موضع agent_loop الثالث (350–381 `_build_followup_prompt`): يحقن
    knowledge_ctx + tool_results — كلاهما يصبح مسيَّجًا **عند المصدر**
    (أ+ب) ⇒ تغطية متعدية، لا تسييج مزدوج (double-fence يشوه المحتوى).
  - سلوك محفوظ يُتحقق منه: (1) رؤوس الأقسام `📂 [ملفات تم قراءتها]` +
    سطر `--- {display} ---` تبقى خارج السور (test_knowledge_bundle:275
    يثبّتها)؛ (2) دلالة delta/dedup في build_iteration_context لا تمس
    (السور يلتف حول المحتوى داخل `_render_body` فقط)؛ (3) نجاة عنصر
    الأمر high في ميزانية ضيقة (test_agent_feedback:171 max_tokens=60) —
    السور يضيف ~90 حرفًا: يُراقب في التشغيل؛ (4) QA-T12 (تسييج مسار
    الإرفاق server.py:1543/2011) لا يُمس.
  - تغيير سلوك مقصود ومُعلن (وفق ALT-602): نص البرومبت الواصل للموديل
    يتغير (أسوار `<attached-content source="…">` حول كل محتوى خارجي) —
    قد يؤثر هامشيًا في سلوك الموديل؛ هذا هو الهدف الأمني (ASF-01).
- **Architecture-Fitness pre-check (Session 35)**:
  - إعادة استخدام `fence_attached` القائمة (templates.py:39 — مُختبرة
    TSK-404/QA-T12) — لا آلية جديدة؛ يوافق سلّم Preserve→Wrap→Extend.
  - لا طبقة ContextSanitizer (Alt B مرفوض في §P.2) — الضمان البنيوي
    يتحقق بديلًا عبر grep-assert دائم في الاختبار الجديد.
  - chain/knowledge.py يستورد من prompts/templates — اتجاه استيراد سليم
    (chain يعتمد على prompts أصلًا عبر agent_loop).
- **Objective**: كل نص خارجي يُحقن في برومبت المتابعة يمر عبر
  `fence_attached` (أو مكافئها) — مواضع agent_loop الثلاثة + knowledge.
- **Background**: ASF-01 (§R4) · **ALT-602 → A**.
- **Dependencies**: —
- **Files**: `chain/agent_loop.py` (224–226, 256–259, 350–381)،
  `chain/knowledge.py` (41–49, 191–205)، `tests/unit/test_context_fencing.py` (جديد).
- **Effort**: جلسة واحدة.
- **Acceptance**: (1) اختبار: ملف يحوي "IGNORE ALL INSTRUCTIONS" → البرومبت
  الملتقط (Stub) يحمله داخل أغلفة حدود موسومة المصدر؛ (2) grep-assert يفرض
  استدعاء fence عند مواضع الحقن (حارس بنيوي)؛ (3) QA-T12 القائم يبقى أخضر.
- **Gates**: Security · Testing · Regression · Documentation.
- **Behavior preservation**: Current = حقن خام؛ Expected = نفس المحتوى داخل
  أسوار — قد يغيّر سلوك الموديل هامشيًا (مقصود، يُوثَّق)؛ Migration = لا شيء.
- **Metrics**: مواضع حقن خام: 5 → 0.
- **Rollback**: revert.
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-603 — بوابة موافقة fail-closed بنيويًا
- **Status**: ✅ DONE (Session 37) · **Priority**: P1
- **Objective**: قلب افتراض `need_approval` في `tool_run_command` إلى True؛
  الحلقة (المسار المُدقَّق) تمرر قرارها صراحة.
- **Background**: ASF-02 (§R4) · **ALT-603 → A**.
- **Dependencies**: —
- **Files**: `chain/agent_tools.py` (432–538)، `chain/agent_loop.py` (466–522)،
  اختبار جديد أو توسيع `test_agent_gated_approvals.py`.
- **Effort**: جلسة واحدة.
- **Acceptance**: (1) نداء مباشر لـ `tool_run_command` بلا معامل → يطلب
  موافقة (أو يرفض بلا gate)؛ (2) مسار الحلقة الحالي يعمل كما قبل (goldens
  QA-T القائمة خضراء)؛ (3) grep: لا `need_approval=False` إلا بقرار صريح موثق.
- **Gates**: Security · Architecture · Testing · Regression.
- **Behavior preservation**: Current = الأداة تنفذ بلا موافقة إن استُدعيت
  مباشرة؛ Expected = مسارات الإنتاج الحالية بلا تغيير (الحلقة تمرر القرار)،
  المستدعي الجديد فقط يواجه fail-closed؛ Migration = لا شيء للمسارات الحية.
- **Metrics**: مسارات تنفيذ أمر بلا بوابة: 1 → 0.
- **Rollback**: revert.
- **Behavior-preservation pre-check (Session 37)**:
  - Current (بدليل): `tool_run_command` (chain/agent_tools.py:432) يمرر
    `need_approval=False` حرفيًا إلى `cmd.run` (:485) — أي مستدعٍ مباشر
    ينفّذ أوامر بلا أي بوابة (ASF-02). المسار المُدقَّق الوحيد: الحلقة
    تبوّب عبر `_request_approval`/ApprovalGate (agent_loop.py:236) **قبل**
    `tools.execute(call)` (:246)؛ الفرع الآمن (:196/:204) لا يصل أبدًا
    لـ run_command (`needs_approval` = عضوية APPROVAL_TOOLS، :130).
  - مستدعو `tools.execute` الوحيدون في الإنتاج: agent_loop.py:204 و:246
    (grep شامل — لا غيرهما). مستدعو `tool_run_command` المباشرون: اختبارات
    فقط (tests/unit/test_run_command.py ×20، tests/integration/
    test_agent_feedback.py:189).
  - Expected بعد التعديل: مسار الحلقة يعمل حرفيًا كما قبل (القرار يُمرَّر
    صراحة out-of-band)؛ النداء المباشر بلا قرار → رفض مهيكل «❌» بلا تنفيذ؛
    الاختبارات المباشرة تُحدَّث لتمرير رمز القرار الصريح (تعاقد جديد مقصود
    — هو جوهر التاسك، ليس كسر سلوك).
- **Architecture-Fitness pre-check (Session 37)**:
  - قلب `need_approval` إلى True عند مستوى CommandRunner **غير صالح**:
    (أ) الخادم يبني `CommandRunner(auto_approve=True)` في المواضع الثلاثة
    (server.py:625/:1283/:2585) ⇒ فرع البوابة
    `need_approval and not is_safe and not auto_approve`
    (command_runner.py:112) مُحيَّد بنيويًا؛ (ب) `_ask_approval`
    (command_runner.py:260) هو `input()` كونسولي حاجب — استدعاؤه من خيط
    عامل في خادم ويب تعليق دائم. ⇒ التنفيذ الأمين لروح ALT-603→A:
    **fail-closed عند طبقة الأداة نفسها**.
  - خطر التزوير: `execute()` يفكّ `handler(self, **call.args)` ووسائط
    الـ AI نصوص من `parse_tool_calls` ⇒ قرار الموافقة يجب ألا يكون قابلًا
    للتمثيل كنص. الحل: **sentinel object** وحدوي (`APPROVAL_GRANTED =
    object()`) يُقارَن بـ `is` — لا يمكن لنص AI إنتاجه؛ `execute` يسقط أي
    مفتاح `approval` قادم من النص ويحقن الكائن الحارس فقط عندما يمرر
    المستدعي `approved=True` (الحلقة بعد ApprovalGate).
  - `need_approval=False` المتبقي في :485 يصبح صحيحًا بالبناء (القرار
    حُسم أعلاه) ويُوثَّق بتعليق TSK-603 + حارس بنيوي (استيفاء معيار
    القبول 3)؛ مواضع server.py الثلاثة موثقة سلفًا عبر TSK-502
    (test_force_approval::TestStructural) و`run_safe` واجهة داخلية آمنة.
  - لا طبقة جديدة، لا تبعية جديدة — تعديل موضعي في agent_tools + سطر واحد
    في الحلقة (اتساق مع خريطة الطبقات).
- **Close-out (Session 37)**:
  - **Implementation**: `chain/agent_tools.py` — sentinel وحدوي
    `APPROVAL_GRANTED = object()` (:41-46 بعد APPROVAL_TOOLS)؛
    `execute(call, approved=False)` يسقط أي مفتاح `_approval` نصي من
    وسائط الـ AI ثم يحقن الكائن الحارس فقط عند `approved=True` لأدوات
    APPROVAL_TOOLS؛ `tool_run_command(..., _approval=None)` يرفض
    fail-closed (`_approval is not APPROVAL_GRANTED` → «❌ رفض بنيوي»
    + WARNING مسجَّل) قبل أي فحص آخر؛ `need_approval=False` في نداء
    `cmd.run` بقي موثقًا بتعليق TSK-603 (صحيح بالبناء — القرار حُسم
    أعلاه؛ بوابة CommandRunner الكونسولية `_ask_approval=input()` غير
    صالحة لخادم ويب). `chain/agent_loop.py:249` — فرع الموافقة يمرر
    `execute(call, approved=True)` صراحة.
  - **Tests**: توسيع `tests/integration/test_agent_gated_approvals.py`
    بـ 7 اختبارات (TestFailClosedToolLayer ×5: نداء مباشر بلا رمز؛
    تزوير نصي/كائن غريب؛ إسقاط `_approval` من بلوك TOOL؛ تعاقد الحلقة
    approved=True ينفّذ؛ SAFE_TOOLS غير متأثرة + حارسان بنيويان:
    `test_no_undocumented_need_approval_false` و
    `test_sentinel_wiring_structural`). تحديث النداءات المباشرة في
    tests/unit/test_run_command.py (×20) و test_agent_feedback.py (×1)
    لتمرير الرمز الصريح (جوهر التعاقد الجديد).
  - **Acceptance**: (1) ✅ نداء مباشر بلا معامل → رفض مهيكل بلا تنفيذ
    (test_direct_call_without_token_rejected)؛ (2) ✅ goldens الحلقة
    خضراء (الـ 8 اختبارات القائمة في test_agent_gated_approvals +
    test_agent_feedback كلها pass)؛ (3) ✅ grep: كل مواضع
    `need_approval=False` موثقة (agent_tools بتعليق TSK-603 + حارس؛
    server.py ×3 بحارس TSK-502؛ run_safe واجهة داخلية).
  - **Gates**: Security ✅ (fail-closed + منع التزوير النصي بـ sentinel
    يُقارن بـ is) · Architecture ✅ (لا طبقة جديدة؛ القرار out-of-band
    عن وسائط النص) · Testing ✅ (65 اختبار impact-scope أخضر) ·
    Regression ✅ (4F/1690P/34S — الأربعة المعروفة فقط، +7 اختبارات).
  - **Metrics**: مسارات تنفيذ أمر بلا بوابة: 1 → 0 ✅.
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-604 — إصلاح TF-03 (اللوحات المعطلة) + TF-01 (sprite)
- **Status**: ✅ DONE (Sessions 38–39) · **Priority**: P1
- **Objective**: إعادة عنصرَي `run-history-btn` و`memory-panel-btn` إلى
  index.html (أو ربط آمن null-checked في app.js مع أهداف Activity Bar) بحيث
  تعمل لوحات Run-History/Memory/status-chip من الواجهة؛ وإعادة سطر «رخصة
  المشروع» إلى sprite.svg.
- **Background**: TF-03 + TF-01 (§R10.1) · **ALT-604 → A**.
- **Dependencies**: —
- **Files**: `static/index.html`، `static/icons/sprite.svg`،
  (احتياطًا `static/app.js` إن لزم null-guard).
- **Effort**: جلسة واحدة.
- **Acceptance**: `pytest tests/unit/test_rollback_ui.py tests/unit/test_file_icons.py`
  أخضر كاملًا؛ فحص يدوي موثق: أزرار Activity Bar الثلاثة تفتح لوحاتها.
- **Gates**: Testing · Regression · Documentation.
- **Behavior preservation**: Current = 3 لوحات معطلة الفتح + TypeError عند
  التحميل؛ Expected = عودة الوظيفة المصمَّمة (T-054/T-114)؛ Migration = تحسّن
  مرئي فقط.
- **Metrics**: إخفاقات البوابة: 4 → 2.
- **Rollback**: revert.
- **Behavior-preservation pre-check (Session 38)**:
  - Current (بدليل): v25 حذفت عنصرَي `id="run-history-btn"`
    و`id="memory-panel-btn"` من index.html (grep = 0 كعناصر؛ كانا
    زرَي header في 755ca94:73–74) وأبقتهما فقط كأهداف `.click()` في
    أزرار Activity Bar (index.html:212/220)؛ app.js:3639–3641 يربط
    الثلاثة في DOMContentLoaded ⇒ `getElementById(...)=null` → TypeError
    يقطع المعالج: لا يُربط status-chip (3641) ولا يبدأ refreshCapacity
    والاستطلاع الدوري (3642–3643). اللوحات نفسها (run-history-panel/
    memory-panel/status-chip-panel) ودوال toggle* موجودة سليمة.
    sprite.svg v25 أسقط عبارة «رخصة المشروع» من تعليق الرأس
    (كانت في 3d4801d سطر 3–4)؛ الاختبار test_file_icons.py:143 يثبّتها.
  - Expected: استعادة الوظيفة المصمَّمة (T-054/T-066/T-114) مع الحفاظ
    على تصميم v25 البصري (Activity Bar بدل أزرار header): إضافة
    الزرين كعنصرين وكيلين مخفيين (class="hidden") — أهداف ربط
    app.js القائم وتفويض Activity Bar، بلا تغيير مرئي ولا تعديل
    app.js؛ Migration = تحسّن وظيفي فقط.
- **Architecture-Fitness pre-check (Session 38)**:
  - الخيار المختار من مساري ALT-604→A: إعادة العنصرين لـ index.html
    (لا null-guard في app.js) — يصلّح الجذر (العنصران مفقودان) لا
    العرض (الربط يرمي)، ويُبقي app.js بلا لمس (أقل سطح تغيير).
  - لا يصح إعطاء زري Activity Bar أنفسهما المعرفين: onclick الحالي
    يستدعي `.click()` على المعرف ⇒ استدعاء ذاتي لا نهائي.
  - زرا وكيلان مخفيان = نمط v25 القائم نفسه (التفويض بـ .click()
    موجود أصلًا في :212/:220) — لا نمط جديد؛ class="hidden" مستعمل
    سلفًا في الملف. sprite: إعادة جملة الترخيص للتعليق — صفر أثر تنفيذي.
- **Close-out (Session 39)**:
  - **Implementation**: `static/index.html` — زرا وكيلان مخفيان
    (`id="run-history-btn"` + `id="memory-panel-btn"`، class="hidden"،
    بتعليق TSK-604 موثّق) قبل run-history-panel مباشرة — أهداف ربط
    app.js:3639–3640 وتفويض Activity Bar `.click()` (:212/:220) بلا
    تغيير مرئي ولا لمس app.js. `static/icons/sprite.svg` — إعادة
    عبارة «رخصة المشروع» لتعليق الرأس (TF-01).
  - **Acceptance**: (1) ✅ `pytest tests/unit/test_rollback_ui.py
    tests/unit/test_file_icons.py` → **25 passed** كاملًا؛ (2) ✅ فحص
    يدوي موثق: الخادم الحي (port 5000) — الصفحة تُحمّل بـ **صفر
    أخطاء JS** (قبل الإصلاح: TypeError في app.js:3639 يقطع
    DOMContentLoaded)؛ الأثر الوحيد في الكونسول = favicon.ico 404
    موروث غير ذي صلة (خطأ مورد لا سكربت)؛ /api/capacity يُستطلع
    (200) — دليل اكتمال المعالج؛ تحقق سكوني كامل: المعرفات الثلاثة
    مربوطة وموجودة + دوال toggle* الثلاث قائمة + وكيلا Activity Bar
    سليمان.
  - **Gates**: Testing ✅ (25/25 في ملفي القبول) · Regression ✅
    (**2F/1692P/33S** — المتبقيان ملك TSK-605 حصرًا؛
    test_search_perf فشل عابر تحت حمل التوازي — معزولًا 18/18 ✅) ·
    Documentation ✅ (تعليق TSK-604 في index.html + هذا السجل +
    CHANGELOG).
  - **Metrics**: إخفاقات البوابة المعروفة: 4 → **2** ✅ (بقي
    test_history_consumers + test_theme_tokens — TSK-605).
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-605 — استعادة خضرة البوابة: TF-02 (نطاق) + TF-04 (baseline ألوان)
- **Status**: IN-PROGRESS — جزء TF-02 (Session 40)؛ TF-04 BLOCKED (ينتظر D-2) · **Priority**: P1
- **Objective**: استثناء `providers/` من مسح test_history_consumers (حارس
  core لا مزودات)؛ وتطبيق قرار D-2 لألوان v25 (التوصية: baseline-allowlist
  مؤرَّخ + تسجيل دين tokenization).
- **Background**: TF-02 + TF-04 + TF-05 (§R10.1) · **ALT-604 → A** · قرار D-2.
- **Dependencies**: TSK-604 (لاكتمال خضرة البوابة معًا)؛ قرار المالك D-2.
- **Files**: `tests/unit/test_history_consumers.py`،
  `tests/unit/test_theme_tokens.py` (آلية baseline)، `docs/engineering/TECHNICAL_DEBT.md`.
- **Effort**: جلسة واحدة.
- **Acceptance**: `python -m pytest tests` = **0 failed** (أول خضرة كاملة
  للبوابة في البرنامج)؛ سطر دين مؤرَّخ لـ TF-04 في TECHNICAL_DEBT.md.
- **Gates**: Testing · Regression · Documentation.
- **Behavior preservation**: اختبارات فقط — لا سلوك منتج.
- **Metrics**: إخفاقات البوابة: 2 → 0؛ حجم baseline الألوان يُسجَّل رقمًا.
- **Rollback**: revert.
- **Resume notes**: TF-02 يمكن تنفيذها فورًا حتى قبل رد D-2؛ TF-04 هي المعلقة.
- **Behavior-preservation pre-check — جزء TF-02 (Session 40)**:
  - Current (بدليل): حارس test_history_consumers::
    test_no_raw_history_slices_outside_sessions (:223) يمسح 6 مجلدات
    بينها `providers/` + server.py؛ الانتهاك الوحيد الفعلي (مسح مُعاد
    Session 40): `providers/openai_shelby.py:105` — `history[-6:]` داخل
    طبقة المزودات المُعلنة خارج النطاق كليًا (§0.8: لا تُراجع، لا
    تُخطّط، لا تُكلّف). باقي المجلدات core وserver.py نظيفة = الحارس
    يؤدي غرضه الأصلي (T-030) فيما عدا ضجيج المزودات.
  - Expected: إزالة `providers` من قائمة المسح — اختبار فقط، صفر سلوك
    منتج؛ تغطية core (chain/core/context/actions/prompts/server.py)
    محفوظة كما هي.
- **Architecture-Fitness pre-check — جزء TF-02 (Session 40)**:
  - الحارس ملكيّته core (T-030: ترحيل مستهلكي التاريخ لـ
    select_history) — إدراج `providers/` فيه يناقض §0.8 ذاته (المزودات
    خارج النطاق لا تُفحص ولا تُصلَّح) — تصحيح النطاق لا إضعاف للحارس؛
    يُوثَّق بتعليق معلّل في الاختبار نفسه لا بحذف صامت. لا مساس
    بـ providers/openai_shelby.py نفسه (خارج النطاق).
  - TF-04 (test_theme_tokens) لا تُلمس — محجوبة بقرار المالك D-2.
- **Partial close-out — جزء TF-02 ✅ (Session 40)**:
  - **Implementation**: `tests/unit/test_history_consumers.py:229` —
    إخراج `providers` من قائمة مسح الحارس بتعليق معلّل موثّق
    (الانتهاك الوحيد وقت القرار مُسجَّل في التعليق)؛ لا مساس بأي
    ملف إنتاج ولا بـ providers/.
  - **Verification**: test_history_consumers → **41 passed** كاملًا؛
    regression كامل (Session 40): **1F/1693P/34S** — المتبقي الوحيد
    test_theme_tokens (TF-04 — محجوب بـ D-2)؛ فشل test_search_perf
    العابر (S39) لم يتكرر — تأكَّد أنه بيئي.
  - **Metrics**: إخفاقات البوابة: 2 → **1** (الهدف 0 يكتمل مع TF-04
    بعد رد D-2).
  - **المتبقي لإغلاق التاسك**: TF-04 — تطبيق قرار D-2 (التوصية:
    baseline-allowlist مؤرَّخ في test_theme_tokens + سطر دين tokenization
    في TECHNICAL_DEBT.md) — ثم القبول الكامل: pytest tests = 0 failed.

## M7 — Responsiveness & Guardrails (P2 الجذور التشغيلية)

### TSK-606 — تخييط _apply_batch والمسار المباشر (إلغاء مستجيب)
- **Status**: ✅ DONE (S43) · **Priority**: P2
- **Objective**: نقل `_apply_batch` (server.py:2081/2415–2462) وتشغيل direct
  runner (1846–1858) إلى خيوط كما chain/agent/delegate — فيصبح cancel من نفس
  الاتصال فعّالًا.
- **Background**: RF-01 + RP-02 + UXF-03 · نمط الخيوط الموجود L1662/L1818/L2294.
- **Dependencies**: — · **Files**: `server.py`، توسيع `test_apply_cancel.py`.
- **Acceptance**: اختبار: cancel_run أثناء دفعة 20-action من نفس الاتصال
  يوقفها؛ goldens تسلسل الإطارات (QA-T08) تبقى مطابقة.
- **Gates**: Architecture · Testing · Regression · Performance (زمن أول إطار
  لا يتدهور).
- **Behavior preservation**: ترتيب الإطارات ومحتواها ثابتان (golden)؛
  المتغير الوحيد = استجابة الإلغاء.
- **Metrics**: قبل/بعد: استجابة cancel أثناء دفعة (مستحيل → ≤ خطوة واحدة).
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Pre-checks (S43 — مسجّلة قبل أي تعديل)**:
  - **تشخيص الجذر (بالدليل)**: `_apply_batch` (server.py:2433) مُخيّطة
    فعلًا تحت ticket مع نقطة تفتيش `apply_ticket.is_cancelled` بين كل
    action (TSK-304 — server.py:2460). المشكلة ليست غياب الإلغاء
    التعاوني بل **التنفيذ المتزامن على خيط حلقة استقبال WS**: النداء
    `_apply_batch(sctx, msg.get("actions", []))` (server.py:2091) يجري
    داخل `_handle_ws_message`، وحلقة `ws_handler` (server.py:2403–2417)
    لا تقرأ الإطار التالي إلا بعد عودة المعالج — فإطار `cancel_run` من
    **نفس الاتصال** لا يُقرأ أبدًا أثناء الدفعة. الشيء نفسه للمسار
    المباشر: بلوك direct runner (server.py:1876–1923 داخل
    `_dispatch_chat_message`) يجري متزامنًا على نفس الخيط.
  - **حفظ السلوك**:
    1. `_apply_batch` نفسها **لا تُمس** (مقفولة بالـ golden
       `tests/goldens/apply_batch_frames.json` — QA-T08) — يُخيَّط
       **نداؤها** فقط عند :2091 بنمط الخيوط القائم (daemon Thread
       مسمّى، كما chain :1698 / agent :1848 / delegate :2304).
       الإطارات: نفس المحتوى والترتيب النسبي بالضبط (منتِج وحيد =
       خيط الدفعة)؛ ملف الـ golden JSON يبقى بلا تغيير — يُعدَّل فقط
       harness الالتقاط (`_run_batch_via_ws`) ليَـjoin خيط الدفعة قبل
       قراءة الإطارات (قفل السلوك هو ملف الـ golden لا تزامنية الـ harness).
    2. المسار المباشر: `chat_history.append(user)` + `session_mgr` +
       إطار `start` + إنشاء `direct_ticket` (فحص busy المتزامن — يحفظ
       ترتيب إطار busy) تبقى على خيط النداء؛ ما بعدها (runner.run،
       parse، إطار plan/done، chat_history.append(assistant)) ينتقل
       لخيط `runner-direct-{run_id}` — كما يفعل agent حرفيًا (:1841–1852).
    3. اختبارات `test_apply_cancel.py` القائمة تنادي `_apply_batch`
       مباشرة (متزامنة) — لا تتأثر. اختبارات `_dispatch_chat_message`
       القائمة (test_scan_start / test_prompt_fencing /
       test_except_narrowing) توقف التنفيذ **قبل** بلوك الـ runner
       (عند gather_message_context أو isdir) — لا تتأثر. لا اختبار
       قائم يستهلك إطارات المسار المباشر بعد `_handle_ws_message`
       تزامنيًا (تحقق grep S43: الوحيد test_session_context يرسل
       "type":"message" لكن نصّه مسار مجلد → يسلك فرع project_switched
       قبل بلوك الـ runner).
  - **Architecture-Fitness**: يوحّد الأنماط لا يضيف نمطًا جديدًا — كل
    الـ runs (chain/agent/delegate/direct/apply) تصير على خيوط عاملة
    daemon مسمّاة `runner-*`، وحلقة استقبال WS تبقى حرة دائمًا (مبدأ
    R-701: المعالج لا يحتجز الحلقة). صفر حالة جديدة في globals؛
    التذاكر تبقى مملوكة لـ ExecutionRegistry كما هي.
- **Close-out (Session 43)**:
  - **Implementation**: `server.py` — (1) نداء `_apply_batch` عند معالج
    `apply_all_actions`/`execute_plan` صار على خيط عامل daemon باسم
    `runner-apply-batch` (كان :2091 متزامنًا)؛ `_apply_batch` نفسها لم
    تُمس. (2) بلوك direct runner داخل `_dispatch_chat_message` (من
    `RUNNERS["direct"].run` حتى إطار plan/done) انتقل لدالة داخلية
    `_run_direct` على خيط `runner-direct-{run_id}` — إطار `start`
    وفحص busy للتذكرة بقيا متزامنين حفاظًا على ترتيب الإطارات (نمط
    agent حرفيًا). (3) **اكتشاف جانبي BUG مصحح**: معالج `cancel_run`
    كان يمرر `ensure_ascii=False` لـ `sctx.send` وتوقيعه
    `Callable[[dict], None]` → TypeError عند أول cancel_run حقيقي عبر
    WS (الاختبارات القائمة كانت تنادي `_cancel_run_frame` مباشرة فلم
    تكشفه) — أُزيل الوسيط الدخيل بتعليق موثق. `tests/integration/`
    `test_apply_batch_golden.py` — الـ harness يَـjoin خيط الدفعة قبل
    قراءة الإطارات (ملف الـ golden JSON نفسه **بلا تغيير**).
    `test_apply_cancel.py` — صنف `TestSameConnectionCancel` (+2):
    (أ) معيار القبول الحرفي — إطار دفعة 20-action ثم إطار `cancel_run`
    عبر `_handle_ws_message` على **نفس sctx** أثناء الدفعة (بوابتا
    Event تضبطان التزامن حتميًا): توقفت عند 5/20، إقرار
    `cancel_run_result acknowledged=True` وصل أثناء الدفعة، عقد إطارات
    الإلغاء المقفول (error ثم all_actions_done) محفوظ، التذكرة
    cancelled والخانة تحررت؛ (ب) التحرر البنيوي — `_handle_ws_message`
    يعود قبل اكتمال الدفعة.
  - **Acceptance**: (1) ✅ cancel_run أثناء دفعة 20-action من نفس
    الاتصال يوقفها (الاختبار أ أعلاه)؛ (2) ✅ goldens QA-T08 مطابقة —
    `test_apply_batch_golden.py` 3/3 وملف الـ golden لم يُلمس.
  - **Gates**: Architecture ✅ (`scripts/lint_handler_state.py` →
    handler state clean؛ نمط خيوط موحّد) · Testing ✅ (اختبارا
    الملفين المستهدفين 11/11) · Regression ✅ (**1F/1695P/34S** —
    الإخفاق الوحيد theme_tokens/TF-04 المحجوب بـ D-2؛ +2 اختبارات
    جديدة خضراء) · Performance ✅ (زمن أول task_progress بعد التخييط:
    وسيط 0.18ms / p95 0.28ms — كلفة spawn لا تُذكر، لا تدهور).
  - **Metrics**: استجابة cancel أثناء دفعة من نفس الاتصال:
    **مستحيل بنيويًا → ≤ خطوة واحدة** ✅ (المقياس المستهدف حرفيًا).
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-607 — ضم جمع سياق delegate إلى ContextBudget
- **Status**: ✅ DONE (S45) · **Priority**: P2
- **Objective**: إخضاع القراءة المباشرة لأول 10 ملفات (server.py:2265–2284)
  لسقوف ContextBudget (آخر جيب خارج توحيد TSK-103).
- **Background**: RP-03 (§R7). · **Files**: `server.py`، اختبار budget قائم يوسَّع.
- **Acceptance**: برومبت delegate الملتقط ≤ سقف الميزانية مع مشروع اصطناعي
  كبير؛ وسم اقتطاع ظاهر لا صامت.
- **Gates**: Testing · Regression · Performance.
- **Behavior preservation**: مشاريع صغيرة = لا تغيير؛ الكبيرة = اقتطاع موسوم
  بدل تضخم غير مسقوف.
- **Metrics**: حجم برومبت delegate الأقصى قبل/بعد.
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Pre-checks (S45 — مسجّلة قبل أي تعديل)**:
  - **الموقع الفعلي (تزحزح بعد TSK-606)**: بلوك جمع سياق delegate هو
    server.py:2299–2313 داخل معالج `delegate_message` — يقرأ أول 10
    ملفات من `scan_project()` **كاملة بلا أي سقف** في
    `files_context = {path: content}` ثم يمررها لـ
    `RUNNERS["delegate"]` عبر `RunRequest.context["files"]`؛
    `DelegateBridge.write_brief` (chain/delegate.py:288–310) يُلحق كل
    محتوى في `files_block` حرفيًا — تضخم برومبت غير مسقوف (RP-03).
    ملاحظة: `build_delegate` في chain/strategies **سبق ضمه** للميزانية
    (T-024) — هذا المدخل (delegate_message عبر الجسر) هو الجيب الأخير.
  - **حفظ السلوك**:
    1. المشاريع الصغيرة (المحتوى ≤ الميزانية): `files_context` يصل
       بالمحتويات نفسها بايت-بايت — الحزم لا يغيّر نص عنصر مقبول
       (ContextBudget.pack كامل-أو-إسقاط، لا قصّ منتصف).
    2. الحقول والترتيب: dict يحافظ على ترتيب الإدراج؛ يُعاد بناؤه
       بترتيب المسح الأصلي للملفات المقبولة فقط.
    3. عند الفيض: إسقاط الأكبر أولًا (tier=high — نفس سياسة مرفقات
       TSK-103) مع **وسم ظاهر** يدخل files_context كعنصر باسم ثابت
       (لا اقتطاع صامت) + سطر log «⚖️ ContextBudget» كنمط :1608.
    4. رسالة المستخدم لا تمر بالميزانية هنا (تبقى كما هي — الميزانية
       تسقف الملفات فقط؛ user_text صغير ولا يصح إسقاطه = must_have
       ضمنيًا خارج الحزمة).
    5. `project_context` (get_project_context) يبقى كما هو — نفس
       دلالة TSK-103 حيث بقي خارج حزمة المرفقات.
  - **Architecture-Fitness**: يعيد استعمال `ContextBudget.from_config`
    (config.yaml:context_budget — نفس السقف المركزي) + `BudgetItem`
    القائمين — صفر مفاهيم جديدة؛ الدالة مساعدة وحدوية نقية في server.py
    (قابلة للاختبار بلا WS) على نمط `_payload_history` (TSK-104)؛
    توسيع `tests/unit/test_budget_wiring.py` القائم (يغطي المواقع
    الموصولة بالميزانية) لا ملف جديد.
- **Close-out (Session 45–46)**:
  - **Implementation**: `server.py` — دالة وحدوية نقية
    `_budget_delegate_files(files_context, cfg=None, budget=None)`
    (نمط `_payload_history`): كل ملف `BudgetItem` بطبقة high تحت
    `ContextBudget.from_config` (config.yaml:context_budget — نفس
    السقف المركزي)؛ كامل-أو-إسقاط، الأكبر أولًا؛ أي إسقاط يضيف وسمًا
    ظاهرًا (`DELEGATE_DROP_MARKER_KEY`) داخل files_context يصل البريف
    + سطر log «⚖️ ContextBudget (delegate)». موصولة في معالج
    `delegate_message` بعد الجمع مباشرة.
    `tests/unit/test_budget_wiring.py` — صنف `TestDelegateFilesBudget`
    (+6): حفظ السلوك بايت-بايت للصغير، فارغ، إسقاط الأكبر أولًا + وسم
    ظاهر، لا بتر منتصف، الحمولة ≤ السقف (معيار القبول)، حفظ الترتيب.
  - **Acceptance**: (1) ✅ مشروع اصطناعي كبير (10×2000 حرف مقابل
    ميزانية 1000 توكن) ⇒ الحمولة ≤ budget_tokens
    (test_result_within_budget)؛ (2) ✅ وسم اقتطاع ظاهر لا صامت
    (test_oversized_drops_largest_first_with_visible_marker + log).
  - **Gates**: Testing ✅ (test_budget_wiring **30/30** كاملًا؛ ملفات
    التأثير delegate_approve + context_budget + injection_budget
    76/76) · Architecture ✅ (lint_handler_state clean؛ إعادة استعمال
    الميزانية المركزية — صفر مفاهيم جديدة) · Regression ✅ (S45:
    **1F/1701P/34S** — الوحيد theme_tokens/TF-04 المحجوب بـ D-2؛
    +6 اختبارات جديدة خضراء) · Performance ✅ (0.03ms/نداء شاملًا
    قراءة config — لا أثر).
  - **Metrics**: حجم برومبت delegate الأقصى: **غير مسقوف (10 ملفات
    كاملة أيًا كان حجمها) → ≤ budget_tokens المركزي** ✅.
  - ملاحظة توثيقية (S46): انقطاع S45 أسقط عنوان §TSK-608 سهوًا أثناء
    تحرير الـ pre-checks — أُعيد العنوان في S46 (لا أثر على المحتوى).
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-608 — تفعيل reap_stale إنتاجيًا
- **Status**: ✅ DONE (S47–48) · **Priority**: P2
- **Objective**: استدعاء دوري (أو عند كل run جديد) لـ
  `ExecutionRegistry.reap_stale` كي لا تبقى خانة مشروع محجوزة بعد موت خيط.
- **Background**: RF-02 (§R5) — الآلية موجودة ومختبرة بلا مستدعٍ (execution.py:322).
- **Files**: `server.py` (نقطة تشغيل واحدة)، اختبار تكامل.
  **انحراف موثّق (S47)**: + `core/backends.py` (تمرير TTL عبر الدرزة —
  docstring الموديول نفسه ينص: «in-mem يأخذ ttl/clock … المستهلكون لا
  يبنون مباشرة بل عبر backends_from_config») + سطر config.yaml.
- **Acceptance**: محاكاة تذكرة يتيمة (بلا finish) → run جديد لنفس المشروع
  يُقبل بعد TTL؛ لا reap لتذاكر حية.
- **Gates**: Testing · Regression.
- **Behavior preservation**: المسارات السليمة (finally) بلا تغيير.
- **Metrics**: زمن تحرير الخانة بعد انهيار: ∞ → TTL.
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Evidence (S47)**:
  - التسجيل يُبنى بلا وسائط: `backends_from_config` (core/backends.py:150)
    → `InMemoryRegistryBackend()` → `_ttl is None` → `reap_stale()` no-op
    (execution.py:328). اختبار مثبِّت: test_backends.py:203 يفرض أن نداء
    المصنع **بلا وسائط** يعطي `_ttl is None` — التفعيل يجب أن يمرر TTL
    صراحةً لا أن يغيّر الافتراضي التاريخي.
  - **صفر مستدعين إنتاجيين لـ `ticket.heartbeat()`** (grep شامل: توثيق
    execution.py:51 + اختبارات فقط) → `_last_heartbeat = created_at`
    للأبد → TTL ساذج يحصد runs حية طويلة زورًا. الحل داخل server.py:
    كل أحداث الـ runners تمر عبر `_RunnerWSAdapter.emit` (يحمل
    `event.run_id` → lookup + heartbeat)؛ مسار resume يرسل مباشرة عبر
    `sctx.send` (server.py:2288 — يحتاج غلاف heartbeat)؛ حلقة
    `_apply_batch` محلية (نبضة لكل action بجوار نقطة تفتيش الإلغاء).
  - **Pre-check حفظ السلوك**: reap_stale لا يُصدر أي إطار WS (goldens
    سليمة)؛ heartbeat على تذكرة منتهية يعيد False بلا أثر (execution.py:171)؛
    `finish` على تذكرة محصودة يعيد False بلا استثناء (execution.py:294) —
    فمسار delegate land/reject بعد الحصد آمن (chain/delegate.py:614/635)؛
    الاختبارات القائمة تحقن `ExecutionRegistry()` بلا TTL → reap no-op
    فيها حرفيًا. مسارات finally السليمة بلا أي تغيير.
  - **Pre-check ملاءمة معمارية**: نقطة التفعيل داخل `_begin_run_ticket`
    بجوار `purge_terminal()` (نفس نمط TSK-303 — أرخص نقطة تغطي كل
    الأنواع)؛ الترتيب reap ثم purge (المحصود يصير terminal فيخضع للسقف).
    TTL من config (`execution.stale_ttl_seconds`، الافتراضي عند غياب
    المفتاح 900s؛ null صريح = تعطيل؛ قيمة غير موجبة/غير رقمية = فشل
    إقلاع صاخب — نفس فلسفة resolve_backend_name).
  - **قيد معروف (موثّق)**: تذكرة delegate في `waiting_approval` لا تبث
    إطارات أثناء انتظار قرار المستخدم → صمت > TTL يحصدها ويحرر الخانة؛
    land/reject اللاحقان يعملان بلا كسر (finish no-op). سلوك مقصود
    (الهدف نفسه: لا خانة محجوزة للأبد) وقابل للتعطيل عبر null.
- **Close-out (S47–48)**:
  - **التنفيذ** (5 لمسات — merged @ e111f8e):
    1. `core/backends.py`: `resolve_stale_ttl(execution_cfg)` (تحقق صارم:
       غائب → 900s افتراضي `DEFAULT_STALE_TTL_SECONDS`؛ null → تعطيل؛
       غير صالح → ValueError صاخب) + وسيط `ttl_seconds` اختياري في
       `backends_from_config` (الافتراضي None = التاريخي بايت-بايت —
       اختبار الثبات القائم test_backends.py:203 يمر بلا تعديل).
    2. `server.py` إقلاع: `_stale_ttl = resolve_stale_ttl(_cfg_root.get("execution"))`
       → `backends_from_config(_backend_cfg, ttl_seconds=_stale_ttl)`.
    3. `server.py::_begin_run_ticket`: نداء `reap_stale()` قبل
       `purge_terminal()` (المحصود يصير terminal فيخضع للسقف فورًا) +
       سطر log لكل تذكرة محصودة. no-op حرفيًا عند التعطيل.
    4. **نبض الحياة** (سد المخاطرة المرصودة — صفر مستدعين سابقين):
       `_RunnerWSAdapter.emit` ينبض تذكرة `event.run_id` عند كل حدث
       (يغطي chain/agent/direct/delegate)؛ `_apply_batch` ينبض لكل
       action؛ مسار resume يغلّف الإرسال بـ `_resume_send_with_heartbeat`.
    5. `config.yaml`: قسم `execution.stale_ttl_seconds: 900` موثّق كاملًا.
  - **الاختبارات**: `tests/integration/test_reap_stale_wiring.py` جديد —
    **17 اختبارًا** (درزة resolve_stale_ttl 7 + معيار القبول الحرفي 3:
    يتيمة تُقبل بديلتها بعد TTL / حية تنبض لا تُحصد / تعطيل null =
    السلوك القديم + نبض المحوّل والدفعة 3 + تمرير المصنع + TTL الخادم
    الحي مفعّل).
  - **Quality Gates**: Testing ✅ (17/17 جديدة + عدة التأثير 108/108:
    backends/execution/purge/slot/ws_run_control/ticket_cancellation/
    apply_cancel/apply_batch_golden/concurrent_guard/dispatch_parity) ·
    Architecture ✅ (lint_handler_state clean؛ التمرير عبر درزة
    backends_from_config كما ينص عقدها لا بناء مباشر) · Regression ✅
    (S47 وS48 على merged: **1F/1718P/34S** — الوحيد theme_tokens/TF-04
    المحجوب بـ D-2) · Performance ✅ (reap+purge: 0.0066ms لكل تسجيل؛
    نبضة المحوّل: 0.0008ms لكل حدث — لا أثر).
  - **Metrics**: زمن تحرير خانة المشروع بعد انهيار خيط:
    **∞ (busy للأبد) → ≤ TTL (900s افتراضيًا)** ✅.
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-609 — Instrumentation: توقيت المسارات + التوكنز
- **Status**: ✅ DONE (S49–54) · **Priority**: P2
- **Evidence (S49)**:
  - PM-02 مؤكد حيًا: صفر `monotonic` في runners/ (direct.py وagent.py
    وdelegate.py بلا أي توقيت)؛ chain وحده يقيس (executor.py:352
    `duration_ms=int((time.monotonic()-start_time)*1000)` ويبثه في
    الإطارات — bridge.py:107).
  - PM-04 مؤكد: `ContextEngine.gather` (engine.py:123–133) حلقة
    مصادر بلا أي توقيت لكل مصدر.
  - PM-01: مقدّر توكنز مركزي جاهز — `CharsPerTokenEstimator`
    (context/budget.py:58، chars÷4) — يُعاد استعماله لا يُخترع جديد.
  - إطارا الختام للمسارين direct/agent يُبنيان في إغلاقي server.py
    `_run_direct` (:1929+) و`_run_agent` (:1838+) — `plan`/`done`.
    delegate يبث إطاراته من الجسر (خارج قائمة ملفات المهمة).
- **Pre-check حفظ السلوك**:
  - حقول إضافية فقط في إطاري `plan`/`done` — app.js يتجاهل المجهول.
  - `run_finished` لا يُنتج إطار WS أبدًا (المحوّل يعيد مبكرًا) →
    إضافة duration_ms لبيانات `stream.finished` تصل bus الرصد فقط؛
    اختبارات العقود تفحص `data["reason"]` حصرًا (runner_contract.py:96)
    — مفاتيح إضافية آمنة.
  - goldens: apply_batch بلا إطار done (all_actions_done كما هو)؛
    goldens السياق تقارن مفاتيح golden الموجودة فقط
    (test_replay_goldens.py:53 `live[key] == golden[key]`) — حقل
    MessageContext إضافي لا يُقارن؛ goldens chain لا تُمس (chain
    خارج التعديل). dispatch_parity يقارن إطارات المحوّل فقط —
    run_finished لا يظهر فيها.
  - dataclasses مجمّدة تبقى مجمّدة: القياس بمتغيرات محلية لا طفرات.
- **Pre-check ملاءمة معمارية**: التوقيت بجوار النداء (نفس نمط chain
  executor — time.monotonic → int ms)؛ التقدير عبر المقدّر المركزي
  القائم (T-024) لا ثابت جديد؛ توقيت المصادر داخل ContextEngine.gather
  نفسه (النقطة الوحيدة التي تمر بها المصادر السبعة) محمولًا على
  ContextBundle، والكشف في MessageContext بحقل افتراضي متوافق.
- **انحراف موثّق (S49) عن قائمة الملفات**: `chain/agent_loop.py` لا
  يُعدَّل — توقيت الحلقة يُلتقط عند نداء `_agent_runner.run` في
  server.py (يغطي الحلقة كاملة end-to-end وهو تعريف PM-02: زمن
  الطلب المفرد)؛ توقيت لكل دورة داخلية خارج نطاق القبول. كذلك
  `runners/delegate.py` يُضاف له duration_ms في finished (تغطية bus
  للمسار الرابع — المقياس 4/4) رغم غيابه من القائمة.
- **Objective**: التقاط duration للمسار المباشر وحلقة الوكيل وبناء السياق
  (لكل مصدر من مصادر ContextBuilder السبعة)، وتقدير توكنز محلي للمخرج —
  يُبث في الإطارات الختامية كما يفعل chain.
- **Background**: PM-01/02/04 (§R6). · **Files**: `runners/direct.py`،
  `chain/agent_loop.py`، `context/` (نقطة توقيت)، `server.py` (تمرير)، اختبار.
- **Acceptance**: إطار finished/done يحمل duration_ms (وtoken_estimate حيث
  ينطبق) للمسارات الثلاثة؛ goldens القائمة تُحدَّث بحقل إضافي فقط (لا كسر بنية).
- **Gates**: Performance · Testing · Regression.
- **Behavior preservation**: حقول إضافية فقط — الواجهة تتجاهل المجهول.
- **Metrics**: تغطية القياس: 1/4 مسارات → 4/4.
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Close-out (S53–54)**:
  - **المنفّذ**:
    - PM-02 (runner-level): `runners/direct.py` و`runners/agent.py`
      و`runners/delegate.py` — `_t0 = time.monotonic()` بعد
      `stream.started()`، و`_finish(..., started_at)` يضيف
      `duration_ms=int((time.monotonic()-started_at)*1000)` لبيانات
      `stream.finished` (نفس نمط chain/executor.py:352) — كل
      مواضع النداء (7+6+6) مُرّرت بـ `started_at=_t0` ⇒ تغطية
      القياس 4/4 مسارات على bus الرصد (المقياس تحقق).
    - PM-04: `ContextEngine.gather` (context/engine.py) يوقّت collect
      لكل مصدر (الفاشل يُرصد أيضًا والاستثناء يُبتلع كما كان)؛
      محمول على `ContextBundle.source_timings_ms` (bundle.py) ومكشوف
      في `MessageContext.source_timings_ms` (facade.py) — حقل افتراضي
      **و`compare=False`** (انظر الانحراف أدناه).
    - PM-01/02 (server-level): إغلاقا `_run_direct`/`_run_agent` في
      server.py يوقّتان النداء محليًا (RunResult مجمّد بلا حقل مدة)
      ويضيفان `duration_ms` + `token_estimate`
      (`CharsPerTokenEstimator().estimate(full_response)` — المقدّر
      المركزي، لا ثوابت جديدة) لإطاري `plan`/`done` — حقول إضافية فقط.
  - **انحراف موثّق إضافي (S53)**: `source_timings_ms` بـ `compare=False`
    — التشغيل الأول للمجموعة كشف 4 اختبارات parity قائمة تقارن
    MessageContext بالمساواة الكاملة (مع/بدون فهرس، ذاكرة فارغة
    ≡ بلا ذاكرة: test_project_index/test_layered_memory/
    test_project_memory_source) — التوقيت غير حتمي فيكسرها؛
    استبعاده من المساواة يحفظ دلالات المقارنة التاريخية (الرصد
    لا يغيّر السلوك) — مثبّت باختبار default-compat.
  - **الاختبارات**: `tests/integration/test_instrumentation_609.py`
    (+11): duration_ms في run_finished للمسارات الثلاثة (نجاح +
    فشل direct)؛ توقيت المصادر (كلها/بطيء ≥ 40ms/فاشل مرصود
    ومُبتلَع)؛ كشف الـ facade + توافق الحقل الافتراضي؛ e2e إطار
    done في chat يحمل الحقلين + المفاتيح التاريخية باقية؛ لا
    ثوابت تقريب جديدة في server.py (بنيوي).
  - **Gates**:
    - Testing: ‏11/11 اختبارًا جديدًا ناجحة.
    - Regression: `pytest tests` → **1 failed، 1729 passed، 34 skipped**
      — الإخفاق الوحيد هو المعروف (theme_tokens — TF-04/D-2)؛
      ‏1718 + 11 = 1729 ✓ (لا انحدار).
    - Architecture: `lint_handler_state.py` → “handler state clean”؛
      contracts + dispatch_parity + goldens (142) كلها خضراء.
    - Performance: عبء التوقيت ≈ ‏173ns × ~14 نداء monotonic/رسالة =
      ميكروثوانٍ (لا يُذكر)؛ `gather_message_context` ≈ ‏20.6ms/نداء
      (متوسط 50، مشروع مؤقت صغير) — لا تدهور.

### TSK-610 — Metrics aggregation (سجل runs بمقاييسه)
- **Status**: ✅ DONE (S55–57) · **Priority**: P2
- **Evidence (S55)**:
  - PM-03 مؤكد (MASTER_REVIEW.md:433): القياسات لحظية «تُبث وتُنسى» —
    `RunFinished` يُنشر على bus الرصد (server.py:362 من
    `_RunnerWSAdapter.emit`) وبعد TSK-609 حمولته تحوي `duration_ms`
    لكل المسارات 4/4 — **ولا مشترك يجمعها**: `event_bus.subscribe`
    بلا أي مشترك تجميع في server.py.
  - `RunStarted` يحمل `mode` (server.py:357)؛ `RunFinished` يحمل
    `status` + payload (reason، duration_ms) — لا mode فيه.
  - نمط تخزين قائم يُحتذى: `ProjectMemoryStore` (core/project_memory.py)
    — JSONL ملحق-فقط تحت جذر بيانات التطبيق (`_DIR / "projects"`)،
    يُبنى في main() كخدمة global (server.py:686/2925).
  - نمط REST قائم: `@app.route("/api/...")` + jsonify (مثل
    /api/capacity :884).
- **Pre-check حفظ السلوك**:
  - إضافة صرفة: مشترك bus جديد (استثناءاته معزولة — EventBus يبتلع
    أعطال المشتركين بالتصميم، core/events.py) + وحدة جديدة + مسار
    REST جديد — صفر تعديل على أي مسار قائم عدا سطر بيانات إضافي.
  - حقل إضافي في بيانات `stream.finished` (`output_chars`) — نفس
    فئة أمان TSK-609 المثبتة: العقود تفحص `data["reason"]` بالمفتاح
    (runner_contract.py:96)؛ اختبار المساواة الحرفية على EventStream
    خام لا يمر بالـ runners (test_runner_contracts.py:186)؛
    `run_finished` لا يصير إطار WS أبدًا (المحوّل يعيد مبكرًا) —
    goldens/parity غير متأثرة.
  - فشل الكتابة (قرص/صلاحيات) لا يُسقط الـ run: الالتقاط داخل
    المشترك المعزول + try داخلي مع log (نمط NF-14 مصنّف).
- **Pre-check ملاءمة معمارية**:
  - التجميع مشترك على bus الرصد (الغرض المعلن للـ bus — T-047) لا
    حقن في مسارات الإرسال؛ نقطة التقاط واحدة تغطي المسارات الأربعة.
  - مخزن JSONL ملحق-فقط بنمط ProjectMemoryStore (نفس دلالات
    الإلحاق/الأمان) في وحدة نقية `core/run_metrics.py` قابلة
    للاختبار بلا Flask؛ الربط في composition root (main) فقط.
  - **قرار موثّق (سؤال «ملف بيانات المشروع»)**: ملف واحد على مستوى
    التطبيق `metrics/runs.jsonl` (بجانب sessions/ وprojects/) مع حقل
    `project_id` في كل سطر (متاح من RunStarted payload عند وجوده) —
    التقسيم لكل مشروع قابل لاحقًا بالفلترة؛ RunFinished لا يحمل هوية
    مشروع فربط سطر-لكل-مشروع كان سيتطلب حالة إضافية هشة.
  - p50/p95 بأسلوب nearest-rank (بلا تبعيات جديدة)؛ تقدير التوكنز
    في القارئ عبر `CharsPerTokenEstimator` المركزي (لا ثوابت جديدة).
  - الكشف عبر REST قراءة `/api/metrics/runs` (الخيار الثاني في نص
    المهمة — أرخص من status-chip ولا يمس app.js).
- **Objective**: إلحاق سطر JSONL لكل run منتهٍ (mode، duration، حجم سياق،
  نتيجة) في ملف بيانات المشروع + قارئ بسيط (p50/p95) يُعرض في status-chip
  أو REST قراءة.
- **Background**: PM-03 (§R6). **Dependencies**: TSK-609.
- **Files**: وحدة جديدة `core/run_metrics.py`، `server.py`، اختبار وحدة.
- **Acceptance**: 3 runs → 3 أسطر صالحة؛ p50/p95 محسوبة صحيحًا في الاختبار.
- **Gates**: Performance · Testing · Documentation.
- **Behavior preservation**: إضافة صرفة.
- **Metrics**: أساس تاريخي للأداء: لا شيء → JSONL لكل run.
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Close-out (S55–57)**:
  - **ما نُفّذ**:
    - `core/run_metrics.py` (جديد): `RunMetricsStore` — JSONL
      ملحق-فقط (نمط ProjectMemoryStore: mkdir للأب، قفل كتابة،
      flush)؛ `read_records` يتخطى الأسطر الممزّقة (ذيل مقطوع
      بانهيار لا يعطّل الملخّص) وملف غائب = []؛ `percentile`
      nearest-rank ⌈p/100·N⌉ (بلا تبعيات جديدة)؛ `summary()` —
      count + status_counts + p50/p95 كليًا ولكل mode (سقف قراءة
      MAX_TAIL_LINES=5000). `RunMetricsRecorder` — مشترك قابل
      للنداء على bus الرصد: يقرن RunStarted (mode/project_id/
      context_chars) بـ RunFinished (status/duration_ms) بمفتاح
      run_id عبر OrderedDict `_pending` بسقف MAX_PENDING=256
      (أقدم-يُطرد — انهيارات لا تراكم ذاكرة)؛ finished يتيم →
      سطر بحقول فارغة (لا اختراع)؛ فشل الكتابة يُبتلع مع log
      (NF-14 — دفاع مزدوج فوق عزل الـ bus).
    - `server.py`: import + global `run_metrics_store` + مسار REST
      قراءة `@app.route("/api/metrics/runs")` (503 قبل التهيئة)
      + البناء والاشتراك في main() بعد project_memory (composition
      root فقط) — الملف `_DIR / "metrics" / "runs.jsonl"`.
  - **انحراف موثّق (حجم السياق/هوية المشروع)**: نص الهدف يذكر
    «حجم سياق»؛ `RunStarted` على bus الرصد يُنشر من
    `_RunnerWSAdapter.emit` (server.py:357) بحمولة الـ runner
    (`stream.started(mode=...)` فقط) — **لا ناشر لـ
    `context_chars`/`project_id` اليوم**. المسجّل يقرأهما من
    payload عند وجودهما ويسجّل None حاليًا (لا اختراع — UNKNOWN)؛
    نشرهما إضافة مستقبلية آمنة (العقود تفحص بالمفتاح؛ اختبار
    المساواة الحرفية test_runner_contracts.py:192 على EventStream
    خام لا يمر بمسار النشر) لكنها خارج نطاق «إضافة صرفة» هنا —
    تُلتقط تلقائيًا متى نُشرت دون تعديل المسجّل.
  - **الاختبارات**: `tests/unit/test_run_metrics.py` (+17):
    المخزن (3: أسطر صالحة/ملف غائب/ذيل ممزّق)؛ percentile (4:
    فارغ/مفرد/1..10 معلوم/غير مرتب)؛ المسجّل (5: **معيار القبول
    الحرفي «3 runs → 3 أسطر صالحة»** عبر EventBus حقيقي، يتيم،
    تجاهل StepProgress، سقف الطرد، ابتلاع فشل الكتابة)؛ الملخّص
    (2: p50=300/p95=1000 على [100,200,300,400,1000] + by_mode،
    duration=None يُعد ولا يُجمع)؛ REST (2: 503 + ملخّص عبر
    test_client)؛ e2e مصغّر (1: DirectRunner حقيقي عبر
    `_RunnerWSAdapter` → سطر بمدة TSK-609 الحقيقية — تقاطع
    609↔610).
  - **Gates**:
    - Testing: ‏17/17 اختبارًا جديدًا ناجحة (يشمل معيار القبول
      الحرفي وp50/p95 بقيم معلومة يدويًا).
    - Regression: `pytest tests` → **1 failed، 1746 passed،
      34 skipped** — الإخفاق الوحيد هو المعروف (theme_tokens —
      TF-04/D-2)؛ ‏1729 + 17 = 1746 ✓ (لا انحدار).
    - Architecture: `lint_handler_state.py` → “handler state
      clean”؛ contracts + dispatch_parity (113) + goldens +
      اختبارات 609 (50) كلها خضراء؛ الربط في composition root
      فقط والوحدة نقية (تُختبر بلا Flask).
    - Performance: `store.append` ≈ **0.039ms/سجل** (متوسط 1000)
      — لا يُذكر أمام مدد runs بالثواني؛ `summary()` على 1001
      سجل ≈ 11.4ms (مسار REST قراءة عند الطلب فقط، بسقف 5000
      سطرًا).
    - Documentation: docstring وحدة كامل (المشكلة/الحل/القرارات)
      + سجل REST في boot print.
  - **Commits**: 108eca9 (الوحدة) · afa600c (ربط server) ·
    a495921 (دمج خارجي شمل الاختبارات) · 4c027be (حقل project_id
    تنفيذًا لقرار §TSK-610).

## M8 — Decompose g1 (خطة R8: QG-01→04)

### TSK-611 — QG-01: استخراج راوتر WS
- **Status**: ✅ DONE (S58–60) · **Priority**: P2
- **Objective**: نقل توجيه 16 نوع رسالة من `_handle_ws_message` (~469 سطرًا)
  إلى جدول dispatch في وحدة جديدة، مع بقاء المقابض نفسها مؤقتًا في server.py.
- **Background**: QG-01 (§R8 خطة التفكيك — ترتيب المخاطرة الصريح).
- **Files**: `server.py`، `core/ws_router.py` (جديد)، اختبار routing golden قائم.
- **Acceptance**: goldens routing كاملة خضراء؛ `wc -l` للكتلة يهبط ≥ 300 سطر؛
  صفر تغيير في أي إطار.
- **Gates**: Architecture (ADR) · Testing · Regression.
- **Behavior preservation**: بنية الإطارات bit-identical (goldens).
- **Metrics**: server.py قبل/بعد (سطور).
- **Rollback**: revert. · **Resume notes / Blocker**: —
- **Evidence (S58–59، قبل أي تعديل كود)**:
  - **الكتلة الفعلية**: `_handle_ws_message(ctx, sctx, msg)` —
    server.py:2034..2539 = **506 سطرًا** (انحراف مواصفة #1: النص يقول
    ~469). `msg_type = msg.get("type", "")` عند :2042.
  - **خريطة الفروع — 23 فرعًا أعلى-مستوى / 25 نوع نصي** (انحراف
    مواصفة #2: النص يقول 16): ping:2045 ·
    agent_approval_response:2052 · cancel_agent:2063 ·
    confirm_path_action:2070 (الأكبر مبكرًا —
    pop_pending_path_request/switch/attach/dispatch) ·
    chain_approval_response:2134 ·
    `in ("rollback_run","rollback_file")`:2148 (تفرع داخلي
    rollback_file:2163) · message:2177 · apply_action:2188 ·
    `in ("apply_all_actions","execute_plan")`:2194 (‏_apply_batch
    في thread) · chain_message:2215 (الأكبر — scan_start/قراءة
    مجلد-ملف/_begin_run_ticket/start_chain) · chain_cancel:2294 ·
    chain_status:2312 · resume_scan:2321 · resume_run:2331 (غلاف
    heartbeat) · discard_run:2360 · list_runs:2377 ·
    cancel_run:2381 · delegate_message:2392 (‏DelegateRunner في
    thread + _budget_delegate_files) · delegate_approve:2459
    (land+parse+_parsed_to_actions) · delegate_reject:2513 ·
    memory_list:2524 · memory_edit:2529 · memory_delete:2536.
  - **نمط مختلط**: أول ~7 أنواع `if...return` مبكرة (:2045–:2148)،
    ثم سلسلة `if/elif` واحدة (:2177–:2536). **لا فرع else** —
    نوع مجهول = سقوط صامت (no-op) — سلوك قائم يجب حفظه.
  - **المستدعي الوحيد**: `ws_handler(ws)` :2540 → استدعاء عند :2554.
  - **انحراف مواصفة #3 — تفسير «goldens routing»**:
    `tests/goldens/routing/` (harness.py + routing_corpus.golden.json،
    ‏30 سيناريو) يغطي توجيه **استراتيجية السلسلة**
    (RequestRouter.route / SmartOrchestrator.select_strategy /
    build_delegate) — **ليس** توجيه رسائل WS. لا golden مخصص
    لتوجيه WS؛ السلوك مثبّت **غير مباشرة** عبر 9 ملفات اختبار
    تستدعي `_handle_ws_message` (apply_batch_golden، apply_cancel،
    delegate_approve_handler، memory_panel، rollback، scan_start،
    session_context، rollback_ui، fixture الـ lint). القبول يُفسَّر:
    goldens routing القائمة + الاختبارات التكاملية التسعة خضراء
    + اختبار جدول dispatch جديد يغطي التوجيه المستخرج.
  - **قيد lint قائم**: `scripts/lint_handler_state.py` (بوابة
    T-048/R-701 المذكورة في docstring المقبض) يجب أن يبقى أخضر.
- **Behavior-preservation pre-check**:
  - بنية كل إطار WS bit-identical — الاستخراج يعيد توجيه الاستدعاء
    فقط؛ أجسام المقابض تبقى حرفيًا في server.py.
  - دلالة **أول-تطابق-يفوز** والترتيب الحالي (returns مبكرة ثم
    سلسلة elif) يُحفظان حرفيًا — جدول dispatch يُقيَّم بنفس الترتيب
    الفعلي (بحث قاموسي بمفتاح msg_type يكافئه لأن الأنواع فريدة —
    تحقق: لا نوع يظهر في فرعين).
  - نوع مجهول → no-op صامت (لا else يُضاف).
  - الأنواع المركّبة (`rollback_run|rollback_file`،
    `apply_all_actions|execute_plan`) تُسجَّل كمفتاحين لنفس المقبض.
  - توقيع المقابض الموحّد `(ctx, sctx, msg)` — لا تغيير في العقد.
- **Architecture-Fitness pre-check**: يقلّص g1 (server.py god-module)
  دون مساس بالحدود القائمة؛ `core/ws_router.py` نقي (جدول + دالة
  dispatch، بلا Flask/IO) يُختبر بمعزل؛ التسجيل في composition
  root؛ **تغيير معماري ⇒ ADR-001 + قيد Decision Log قبل الكود**
  (الدستور :1038 — ARCHITECTURE_DECISIONS.md وDECISION_LOG.md
  يُنشآن الآن، أول ADR في M8 وفق الخارطة :127).
- **Close-out (S59–60)**:
  - **ما نُفّذ** (ADR-001):
    - `core/ws_router.py` (جديد): وحدة نقية — دالة
      `dispatch(handlers, ctx, sctx, msg)` تبحث في جدول
      `msg_type → handler` وتستدعي بتوقيع `(ctx, sctx, msg)`؛
      نوع مجهول = no-op صامت (حفظ حرفي — السلسلة الأصلية بلا
      else)؛ لا استيراد server/Flask (لا دورة).
    - `server.py`: الفروع الـ23 استُخرجت **آليًا** (سكربت يقطع
      الجسم عند حدود الفروع مع التعليقات القائدة، dedent 4) إلى
      23 دالة `_ws_<type>(ctx, sctx, msg)` بنفس الأجسام حرفيًا
      (‏`_ws_rollback` تعيد اشتقاق msg_type محليًا لتفرعها
      الداخلي)؛ جدول `WS_HANDLERS` (25 مفتاحًا؛ المركّبان
      rollback_run/rollback_file وapply_all_actions/execute_plan
      → مقبض مشترك)؛ `_handle_ws_message` صار غلافًا يستدعي
      `ws_dispatch(WS_HANDLERS, ctx, sctx, msg)` + import :73.
    - `scripts/lint_handler_state.py`: إضافة البادئة `"_ws_"` إلى
      HANDLER_NAMES — قاعدة T-048 (منع الحالة الوحدوية) تتبع
      المقابض المستخرجة؛ fixture الانتهاك ما يزال يفشل (exit 1) ✓.
    - تحديث فحصين بنيويين كانا يثبّتان نص السلسلة القديمة:
      test_scan_start.py:119 (regex → جسم `_ws_chain_message`)
      وtest_rollback_ui.py:418 (سطر `in (...)` → مفتاحا الجدول
      لنفس المقبض) — نفس الضمانات على البنية الجديدة.
  - **فجوة التغطية أُغلقت**: `tests/unit/test_ws_router.py` (+10)
    — dispatch النقية (5: توجيه بالتوقيع الكامل، نوع مجهول
    no-op، غياب مفتاح type → ""، قيمة الإرجاع، مقبض واحد فقط
    يُستدعى)؛ جدول server (5: **المفاتيح == الأنواع الـ25
    الأصلية حرفيًا** (تجميد التوجيه)، كلها `_ws_*` قابلة
    للنداء، المركّبات تتشارك المقبض بالهوية، نوع مجهول عبر
    `_handle_ws_message` لا يرسل شيئًا، إطار pong bit-identical).
  - **Gates**:
    - Architecture: **ADR-001** + قيد DECISION_LOG قبل الكود ✓؛
      `lint_handler_state.py` → "handler state clean" (بنطاق
      موسّع يشمل `_ws_*`)؛ contracts + dispatch_parity (113)
      خضراء؛ الوحدة نقية بلا تبعيات.
    - Testing: goldens (chain replay + apply_batch + routing) =
      ‏22 خضراء؛ +10 اختبارات راوتر جديدة؛ الاختبارات الثمانية
      المثبّتة لسلوك WS كلها خضراء.
    - Regression: `pytest` → **1 failed، 1756 passed، 34 skipped**
      (‏72.9s) — الإخفاق الوحيد هو المعروف (theme_tokens —
      TF-04/D-2)؛ ‏1746 + 10 = 1756 ✓ (لا انحدار).
  - **Metrics (القبول)**: كتلة `_handle_ws_message` هبطت
    **506 → 13 سطرًا (−493 ≥ 300 ✓)**؛ server.py إجمالًا
    2987 → 3045 (+58: 23 توقيع دالة + جدول 29 سطرًا + docstrings
    — الكتلة تفككت، الإجمالي ينخفض في QG-02..04 عند نقل المقابض).
    صفر تغيير في أي إطار (bit-identical — تثبته الاختبارات).
  - **انحرافات المواصفة الموثقة**: 506≠~469 سطرًا؛ 23≠16 نوعًا؛
    «goldens routing» = توجيه السلسلة لا WS (فسّرناه: goldens
    القائمة + الاختبارات المثبّتة + اختبار جدول جديد).
  - **Commits**: e3f13e2 (الأدلة) · 28398d1 (ADR-001 + سجل
    القرارات) · 41cc87a (دمج خارجي — الكود + الاختبارات).

### TSK-612 — QG-02: استخراج مسارات الإرسال
- **Status**: ✅ DONE (S61–63) · **Priority**: P2 · **Dependencies**: TSK-611 ✅, TSK-601 ✅.
- **Objective**: نقل `_dispatch_chat_message` (~477 سطرًا) إلى وحدة إرسال
  مستقلة تستهلك `_parsed_to_actions` الموحدة (من TSK-601).
- **Background**: QG-02 (§R8). · **Files**: `server.py`، وحدة جديدة، goldens.
- **Acceptance**: goldens dispatch parity خضراء؛ mypy على الوحدة الجديدة نظيف.
- **Gates**: Architecture (ADR) · Testing · Regression.
- **Behavior preservation**: bit-identical frames.
- **Metrics**: سطور server.py. · **Rollback**: revert.
- **Evidence (S61، قبل أي تعديل كود)**:
  - **الكتلة الفعلية**: `_dispatch_chat_message(ctx, sctx, user_text,
    mode, msg, skip_path_detection=False, attached_context=None)` —
    server.py:1549..2034 = **486 سطرًا** (انحراف مواصفة: النص ~477).
  - **البنية (4 مراحل)**: scan_start فوري :1559 → كشف المسارات
    (:1561–1670 — quoted/Windows/كلمات + قراءة ملف مكتشف مسيّجة
    fence_attached + مجلد مكتشف → store_pending_path_request +
    path_confirmation_request) → جمع السياق :1671
    (gather_message_context/T-019) → توجيه :1701
    (`request_router.route` + RoutingDecided على bus + مستويات
    RoutingTier: chain عبر `_chain_runner_for_dispatch`/RUNNERS،
    delegate) → Agent :1815 (`agent_tools` + AgentLoop في thread)
    → direct fallback :1948 (build_prompt + `_begin_run_ticket` +
    RunRequest + RUNNERS["direct"] في thread).
  - **المستدعيان (كلاهما بعد استخراج 611)**: `_ws_confirm_path_action`
    :2120 (بـ skip_path_detection=True + attached_context) و
    `_ws_message` :2182.
  - **26 رمزًا خارجيًا** تستعملها الدالة — التصنيف:
    - مستوردات نقية (تُستورد في الوحدة الجديدة مباشرة): AgentLoop،
      CharsPerTokenEstimator، Message، RoutingTier، RunRequest،
      RESULT_COMPLETED/RESULT_FAILED، RoutingDecided، build_prompt،
      fence_attached، get_system_prompt، gather_message_context،
      os/re/threading/time/uuid.
    - **معرّفة في server.py** (الحاجز الحقيقي): RUNNERS :380،
      `_RunnerWSAdapter` :336، `_begin_run_ticket` :389،
      `_chain_runner_for_dispatch` :245، `_parsed_options` :1544،
      `_parsed_to_actions` :1513، `_payload_history` :1466،
      `parser` :133، `store_pending_path_request` :201،
      MAX_SMART_FILE_SIZE، event_bus :270.
    - **globals متغيّرة تُقرأ وقت النداء**: `request_router` :677
      (تُربط في main() :2969) و`agent_tools` :683 (:3009) —
      واجهات None-safe (`if request_router and ...`).
  - **قيد الاختبارات الحرج (seam constraint)**: 4 ملفات اختبار
    تستدعي `server._dispatch_chat_message` وتعتمد monkeypatch على
    **فضاء أسماء server**: `setattr(server, "gather_message_context",…)`
    (except_narrowing:67، prompt_fencing:82، scan_start:76) و
    `setattr(server.os.path, "isdir",…)` (scan_start:92) و
    `setattr(server, "execution_registry",…)` (instrumentation_609:225)
    — **لو نُقل الجسم إلى وحدة تقرأ رموزها من فضائها الخاص انكسر
    الـ monkeypatch بصمت** (يرقّع server بينما الوحدة تستعمل
    مرجعها). فحص بنيوي إضافي: scan_start:104 regex على
    `def _dispatch_chat_message` (يبقى صالحًا لو بقي غلاف بنفس
    الاسم يُرقّع)؛ prompt_fencing:170 regex على استدعاء attach.
  - **بوابة mypy القائمة**: scripts/check.sh:12 —
    `mypy --ignore-missing-imports --follow-imports=silent
    providers/ chain/ core/ context/ sessions/` — وحدة جديدة تحت
    `core/` تدخل النطاق تلقائيًا (يحقق «mypy على الوحدة الجديدة
    نظيف» بلا توسيع يدوي).
- **Behavior-preservation pre-check**:
  - bit-identical frames: كل sctx.send كما هو حرفيًا (scan_start،
    path_confirmation_request، تحذير الملف غير المقروء، إطارات
    الـ runners عبر `_RunnerWSAdapter` دون مساس).
  - `server._dispatch_chat_message` يبقى موجودًا بنفس الاسم
    والتوقيع (غلاف) — المستدعيان الداخليان والاختبارات الأربعة
    وregex البنيوي scan_start:104 كلها تستمر دون تعديل.
  - **التبعيات القابلة للترقيع تُحقن وقت النداء** (تمرير مراجع
    server الحية عند كل استدعاء — late binding) كي يبقى
    monkeypatch على فضاء server فعّالًا؛ `request_router`/
    `agent_tools` تُقرآن وقت النداء (لا تُلتقطان عند الاستيراد —
    تُربطان في main() بعد الاستيراد).
  - NF-14: مواضع الابتلاع المقصود (قراءة ملف مذكور :1711،
    قراءة الملف المكتشف) تبقى بتعليقاتها حرفيًا.
- **Architecture-Fitness pre-check**: يقلّص g1؛ الوحدة الجديدة
  `core/chat_dispatch.py` تدخل بوابة mypy تلقائيًا (نطاق core/
  في check.sh:12)؛ الحقن عبر معاملات صريحة (لا استيراد server —
  لا دورة)؛ **تغيير معماري ⇒ ADR-002 + قيد Decision Log قبل
  الكود** (الدستور :1038).
- **Close-out (S61–63)**:
  - **ما نُفّذ** (ADR-002):
    - `core/chat_dispatch.py` (جديدة، 513 سطرًا): جسم
      `_dispatch_chat_message` حرفيًا (475 سطر جسم — تحقق آلي
      سطرًا-بسطر مقابل الأصل: الفرق الوحيد إدراج `deps.`
      خارج النصوص؛ تلوّث وحيد لنص log أُصلح وتحقّق الفحص
      الآلي من صفر مشاكل متبقية) كـ `dispatch_chat_message(deps,
      ctx, sctx, …)`؛ المستوردات النقية مباشرة؛ 14 رمز server
      عبر deps.
    - `server.py`: `_dispatch_chat_message` صار غلافًا (نفس الاسم
      والتوقيع) يرسل scan_start الفوري (TSK-403) ثم يبني
      `deps = SimpleNamespace(…)` **وقت كل نداء** من فضاء server
      (late binding — monkeypatch الاختبارات وglobals المتغيّرة
      محفوظة)؛ import :75 + SimpleNamespace :18.
    - 4 فحوص بنيوية كانت تثبّت نص server القديم حُدّثت لنفس
      الضمانات في الموقع الجديد: prompt_fencing:176 (موضع
      تسييج detected_file → الوحدة)، context_engine (النداء
      الموحّد + غياب المنطق القديم على الملفين معًا)،
      config_consolidation (تعريف MAX_SMART_FILE_SIZE أعلى-مستوى
      فقط — kwarg الحقن ليس تعريفًا)، run_slot_per_project
      (مواضع `_begin_run_ticket` على الملفين — 4 انتقلت، كلها
      تمرر sctx=sctx).
  - **Gates**:
    - Architecture: **ADR-002** + قيد DECISION_LOG قبل الكود ✓؛
      lint_handler_state → clean؛ لا دورة استيراد (الوحدة لا
      تستورد server).
    - Testing: **mypy على الوحدة الجديدة نظيف** (وعلى نطاق
      core/+chain/+context/+sessions/ كاملًا: 62 ملفًا — ملاحظة:
      بوابة check.sh الكاملة تُظهر خطأ واحدًا قائمًا مسبقًا في
      providers/openai_shelby.py:166 — خارج النطاق §0.8، الملف لم
      يُمس — diff 77ca23a..HEAD يخلو من providers/)؛ goldens
      dispatch parity + كل goldens: 32؛ الملفات السبعة المثبّتة
      لمسار الإرسال: 76؛ contracts+parity: 113.
    - Regression: junitxml — **1791 اختبارًا = 1 failed، 1756
      passed، 34 skipped** (69.8s) — الإخفاق الوحيد هو المعروف
      (theme_tokens — TF-04/D-2)؛ لا انحدار (لا اختبارات جديدة —
      نقل سلوك-محفوظ؛ التثبيت القائم يغطي المسار).
  - **Metrics (القبول)**: server.py **3045 → 2596 سطرًا (−449
      صافيًا)**؛ الكتلة 486 → غلاف ~37 سطرًا؛ المنطق دخل بوابة
      mypy (كان خارجها في server.py)؛ صفر تغيير في أي إطار.
  - **انحراف موثّق**: الكتلة الفعلية 486 سطرًا (النص ~477).
  - **تصويب لاحق (S69 — NF-25)**: خريطة الـ14 رمزًا أسقطت
    `provider_pool` و`approval_gate` (chat_dispatch.py:306,307,332 —
    كانتا globals في 77ca23a:server.py:1827,1853) ⇒ NameError بمسار
    agent عبر dispatch. التحقق العكسي سطرًا-بسطر لم يلتقطه (السطر لم
    يُعدَّل فالفرق صفر رغم تغيّر سياق الوحدة) ولا اختبار يقود agent
    حتى نداء الإرسال. مسجَّل NEW_FINDINGS §NF-25؛ يُصلح ضمن TSK-614.
  - **Commits**: 49178dd (الأدلة) · fcc34ce (ADR-002) · 4dbc9ff
    (دمج خارجي — الاستخراج) · 133e0d5 (دمج خارجي — إصلاح نص
    log + تحديث الفحوص البنيوية).

### TSK-613 — QG-03: تجميع REST blueprints
- **Status**: ✅ DONE (S64–67) · **Priority**: P2 · **Dependencies**: TSK-612 ✅.
- **Objective**: تجميع 27 route في Flask Blueprints موضوعية (rollback/memory/
  project/…) — بعد استقرار قرار g5.
- **Background**: QG-03 (§R8). · **Acceptance**: كل endpoints تستجيب كما قبل
  (اختبار smoke REST)، عدد routes ثابت.
- **Gates**: Architecture · Testing · Regression. · **Rollback**: revert.
- **حالة قرار g5 (تحقق مسبق — شرط نص المهمة)**: القرار **مستقر بصيغة
  «مقبول موثَّق»** — NF-03 (تثبيت g5) مسجل «مفتوح — مقبول موثَّق»
  (MASTER_REVIEW.md:364)؛ الازدواجية REST-globals/WS-SessionContext قرار
  واعٍ موثَّق في core/session_context.py:14–27 (NEW_FINDINGS.md §NF-03)؛
  التوحيد مؤجل كتحسين مستقبلي **FI-01** (FUTURE_IMPROVEMENTS.md:16–26،
  شرطه المسبق TSK-302). سبب تأجيل QG-03 الأصلي (MASTER_REVIEW.md:543:
  «الاقتطاع قبله يجمّد الازدواجية في الواجهات») **يُحيَّد** بنمط الحقن
  الحي (ADR-002): كل blueprint يستلم كائن وحدة server نفسه (`srv`)
  كنقطة وصول وحيدة للحالة — قراءة `srv.fm` وقت النداء؛ FI-01 لاحقًا
  يستبدل هذه النقطة الواحدة بمحلّ جلسة دون مسّ الأجسام. ⇒ لا حاجب؛
  التنفيذ يمضي (قرار هندسي ضمن الاستقلالية — لا تغيير سلوك منتج).
- **Evidence (S64–65 — قبل أي تعديل)**:
  - الجرد الفعلي: **28 مزيّن `@app.route`** في server.py:704..1385
    (≠27 في النص — انحراف موثَّق؛ ربما 27 = بلا `index`). url_map =
    **30 قاعدة** (28 + `/static/<path:filename>` + `/ws`). لا
    `@app.before_request`؛ `@app.after_request` واحد :102 (مستوى app —
    يسري على blueprints تلقائيًا).
  - خريطة globals لكل route (AST): fm×15، session_mgr×7، cmd_runner×4،
    ctx×4، chat_history×3، chain_bridge×2 (rollback)، provider×2،
    _binding_banner×2، execution_registry×2، capacity_model،
    run_metrics_store، provider_pool، request_router، account_budget.
  - **4 routes تعيد ربط globals** (عبارة `global`): api_clear:983،
    api_load_session:1007، api_new_session:1030، api_switch_project:1264
    — النقل يتطلب `srv.chat_history = []` (تعيين سمة على كائن الوحدة =
    دلالة `global` الحرفية نفسها).
  - **قيد النطاق §0.8**: `api_models`:1131 + `api_switch_model`:1169
    provider-routing خارج النطاق — **تبقيان في server.py دون لمس**
    (انحراف موثَّق عن «تجميع الكل»). كذلك `index`:704 (app-level،
    3 أسطر) تبقى.
  - مساعدات مشتركة تبقى في server.py (تستدعى عبر srv):
    `_search_service`:723، `_zip_member_violations`:1069،
    `_session_binding_policy`:1241، `_force_command_approval`:177 —
    test_config_consolidation.py:109 يرقّع `server._session_binding_policy`.
  - **لا اقتران باسم endpoint**: صفر نتائج `url_for`/`view_functions`
    في server.py/static/templates/tests ⇒ إعادة تسمية endpoints بواسطة
    Blueprint (`files.api_files`) محايدة لسطح HTTP.
  - اختبارات بنيوية ستتأثر (سابقة «نفس الضمانة في الموقع الجديد»):
    (1) test_force_approval.py:141 — 3 مواضع `need_approval=False` في
    server.py؛ موضعا api_run:879/api_run_file:1411 ينتقلان؛ (2)
    test_search_perf.py:270 — يقرأ `def api_search()` من server.py؛
    (3) test_capacity_model.py:215 — بوابة grep تُوسَّع بـ `routes/`
    (تقوية). اختبارات E2E عبر test_client (switch_handlers،
    restore_zip_slip، session_binding، rollback_ui، run_metrics،
    capacity_model) سلوكية — لا تعديل.
  - **Baseline smoke (S65)**: 28 حالة HTTP مسجلة على app غير مهيأ
    (globals=None): أبرزها `/`=200، chat-history=200، clear=200،
    models=200، capacity/metrics/rollback-history=503،
    rollback-preview=400، switch-model/switch-project/new-file/
    new-folder/run-file=400، والباقي 500 (حتمي). url_map الكامل
    (30 قاعدة، مسار+methods) مجمّد كمرجع تكافؤ.
- **Behavior-preservation pre-check**: نقل ميكانيكي بأجسام حرفية؛
  الحالة عبر `srv.<name>` وقت النداء (تحافظ على monkeypatch الاختبارات
  على فضاء server وقراءة globals المتغيّرة — نمط ADR-002)؛ إعادة الربط
  عبر تعيين سمة على كائن الوحدة (تكافؤ حرفي لـ `global`)؛ المسارات/
  methods/الأجسام/رموز الحالة كلها بلا تغيير؛ **العدد الكلي للقواعد
  ثابت = 30** (معيار القبول)؛ smoke قبل/بعد متطابق.
- **Architecture-Fitness pre-check**: يفكك g1 (server.py يفقد ~640
  سطر routes)؛ لا دورة استيراد (server يستورد routes/ ويمرر نفسه —
  routes/ لا تستورد server)؛ لا حالة جديدة في routes/ (النقطة الوحيدة
  `_srv` تُعيَّن مرة عند التسجيل)؛ لا يجمّد g5 (نقطة وصول واحدة قابلة
  للاستبدال بـ FI-01)؛ خارج bلوك mypy الحالي (check.sh يغطيه TSK-614)
  — يُفحص يدويًا هنا.
- **التقسيم الموضوعي (25 route تنتقل)**: `routes/files.py` (8:
  files/read/folder/write/delete/new-file/new-folder/search) ·
  `routes/backups.py` (2: backups/restore) · `routes/run.py` (3:
  run/cwd/run-file) · `routes/sessions.py` (6: sessions/load/new/
  delete/chat-history/clear) · `routes/meta.py` (3: info/capacity/
  metrics-runs) · `routes/rollback.py` (2: history/preview) ·
  `routes/project.py` (1: switch-project). تبقى في server.py: index +
  api_models + api_switch_model (§0.8) = 28 ✓.
- **Close-out (S65–67)**:
  - **التنفيذ**: حزمة `routes/` (8 ملفات، 633 سطرًا): `__init__.py` +
    7 blueprints — كل وحدة تحمل `bp = Blueprint(...)` + `_srv = None` +
    `register(app, srv)` (حقن كائن وحدة server — قراءة حيّة وقت
    النداء، ADR-003). النقل آلي بـ tokenize (أسماء SRV → `_srv.X`
    خارج السلاسل النصية — درس تلف TSK-612 مُطبَّق وقائيًا)؛ عبارات
    `global` حُذفت وإعادة الربط صارت تعيين سمة (`_srv.chat_history
    = []` — تكافؤ حرفي). server.py: حذف 25 دالة + كتلة تسجيل
    `register(app, sys.modules[__name__])` قبل `_build_session_context`.
  - **تحقق الحرفية آليًا**: مقارنة سطرًا-بسطر معكوسة التحويل
    (`_srv.` تُنزع + global تُسقط من الأصل) لكل الدوال الـ25 —
    **0 فروق**. إصلاح وحيد: حذف `import zipfile` وحدوي زائد في
    backups.py (الجسم الحرفي يستورده محليًا) — pyflakes نظيف.
  - **تكافؤ سلوكي**: smoke 28 حالة HTTP قبل/بعد (شجرة HEAD^ مقابل
    الجديدة) — **متطابق 28/28**؛ url_map **30 قاعدة bit-identical**
    (rule+methods) = معيار القبول «عدد routes ثابت» ✓.
  - **اختبارات**: +21 (test_rest_blueprints.py — تجميد القواعد الـ30
    حرفيًا + smoke لا-404/405 + الحقن الحي/إعادة الربط على فضاء
    server + لا `import server` في routes/)؛ 4 فحوص بنيوية حُدّثت
    لنفس الضمانات في الموقع الجديد: force_approval (server+routes/run
    معًا، 3 مواضع)، search_perf (api_search في routes/files)،
    rollback_ui (GET-only في routes/rollback)، capacity_model
    (بوابة MIN_ACCOUNTS تشمل routes/ — تقوية).
  - **Gates (S67 على الشجرة المدموجة f5e0fa3)**: lint clean ·
    mypy **نظيف 70 ملفًا** (chain+core+context+sessions+**routes**) ·
    contracts+parity **113/113** · goldens **32/32** · عدة التأثير
    (blueprints+البنيوية الأربعة+switch+zip_slip) **89/89** ·
    regression junitxml **1812 = 1F/1777P/34S** (theme_tokens/TF-04
    حصرًا؛ 1791+21=1812 ✓؛ ملاحظة: test_search_perf::TestPerf5k
    رسب مرة واحدة في عدة جزئية وينجح منفردًا وفي الكامل — flaky
    توقيت معروف الطبيعة، ليس بنيويًا).
  - **Metrics**: server.py **2596 → 2118 (−478)**؛ إجمالي M8 حتى
    الآن: 3045 → 2118 (**−927**). routes/ = 633 سطرًا.
  - **انحرافات موثَّقة**: (1) العدد 25 منقولة ≠ «27» النصية —
    28 فعليًا منها index+models+switch-model تبقى (§0.8)؛ (2) لا
    «memory» blueprint رغم ذكره في النص — memory REST غير موجود
    (الذاكرة عبر WS فقط)؛ (3) أسماء endpoints تتغير داخليًا
    (`files.api_files`) — صفر url_for في المستودع، سطح HTTP ثابت.
  - **Commits**: 41908fe (أدلة+pre-checks) · a860d44 (ADR-003 +
    DECISION_LOG قبل الكود) · 75b72f3 (الاستخراج) · ed59219
    (الاختبارات) — دمج خارجي c534c4c + f5e0fa3.

### TSK-614 — QG-04: ضم server.py (والوحدات المستخرجة) لبوابة mypy
- **Status**: ✅ DONE (S69–70) · **Priority**: P2 · **Dependencies**: TSK-611..613.
- **Objective**: توسيع نطاق mypy في check.sh ليشمل الوحدات المستخرجة ثم
  server.py المتبقي — إغلاق QF-02 (عيوب كـ RP-01 تُلتقط ساكنًا).
- **Background**: QG-04 + QF-02 (§R8)؛ RP-01 كدليل الكلفة.
- **Acceptance**: `mypy` أخضر على النطاق الموسع في check.sh؛ البوابة تفشل
  عند دس نداء لدالة غير موجودة (اختبار سلبي موثق).
- **Gates**: Architecture · Testing · Documentation. · **Rollback**: revert سطر البوابة.
- **Evidence (S69 — mypy 2.3.0 / Python 3.13.13، كل الأرقام مُعادة
  التحقق على clone نظيف عند fa9382b)**:
  - **بوابة check.sh:13 الحالية حمراء اليوم**: `mypy … providers/ chain/
    core/ context/ sessions/` → exit=1 — خطأ واحد
    (`providers/openai_shelby.py:166 [union-attr]`) في 73 ملفًا. مع
    `set -euo pipefail` (check.sh:4) السكريبت كله يفشل ⇒ نقطة الدخول
    الموحدة معطّلة فعليًا بخطأ خارج نطاق البرنامج (§0.8).
  - **حدّ mypy الافتراضي**: أجسام الدوال غير المُعنونة لا تُفحص —
    تجربة موثّقة: نداء `nonexistent_function_abc()` داخل def غير
    مُعنون → **Success** بدون `--check-untyped-defs` و**error
    [name-defined]** معه. دوال routes الـ25 وأغلب دوال server.py غير
    مُعنونة (routes: 0/32 لها `->`؛ server: 15/61 فقط) ⇒ توسيع
    قائمة الملفات وحده **لا يحقق شرط القبول** (النداء المدسوس في
    جسم route لن يُلتقط). العلم مطلوب.
  - **كلفة `--check-untyped-defs` بالأرقام**:
    - النطاق القائم (providers+chain+core+context+sessions): 1→**4**
      أخطاء — الثلاثة الجديدة كلها `[name-defined]` في
      `core/chat_dispatch.py` = **علة فعلية NF-25** (أدناه).
    - routes/: نظيفة بدون العلم؛ معه **79** خطأ كلها `[union-attr]`
      من استنتاج `_srv = None` كنوع None — تُصفَّر جميعًا بتعنوين
      `_srv: Any = None` في 7 ملفات (مُجرَّب في نسخة scratch →
      Success 8 ملفات). صفر تغيير سلوكي (تعنوين فقط).
    - server.py: **16** خطأ بدون العلم (`X: Type = None` — نمط
      sentinel للـ globals تُملأ في main، :133..:698)؛ معه **47** =
      30 [assignment] (الـ16 + سلاسل cfg/provider في if/elif
      بأنواع config مختلفة :851..:861، :1891..:1902) + 9 [arg-type]
      (نفس السلاسل) + 6 [attr-defined] + 1 [union-attr] + 1 [index].
    - سطر البوابة المرشّح كاملًا (+علم +exclude): **129** خطأ في 9
      ملفات (47+79+3) — كلها مُصنّفة أعلاه، لا مفاجآت.
  - **علة NF-25 (انحدار من TSK-612 — يُكتشف بالعلم)**:
    `core/chat_dispatch.py:306,307` (`provider_pool`) و`:332`
    (`approval_gate`) أسماء **غير معرّفة** في الوحدة — كانت globals
    في server الأصلي (77ca23a:server.py:1827,1853) ولم تكن ضمن
    خريطة الـ14 رمزًا المحقونة في deps (§TSK-612). pyflakes يؤكد.
    الأثر: `NameError` وقت تنفيذ `_agent_send_fn` أو مصنع AgentLoop
    ⇒ **مسار agent عبر dispatch مكسور منذ دمج 612**. لماذا لم يُرَ:
    (1) التحقق العكسي سطرًا-بسطر لا يراه — التحويل لم يلمس هذه
    الأسماء أصلًا فالفروق صفر رغم تغيّر سياق الوحدة؛ (2) لا اختبار
    يقود مسار agent حتى نداء الإرسال. التسجيل: NEW_FINDINGS §NF-25
    + ملاحظة تصويب على تحقق TSK-612.
  - **علة NF-26 (قائمة مسبقًا — عصر TSK-404، أصلها 0d74dad)**:
    `server.py:1180` يقطّع dict — `scan_folder_for_chain` يرجع
    `dict[str, str]` (chain/bridge.py:666–681 والتوثيق
    `{relative_path: content}`) بينما الكود يعامله كقائمة dicts
    (`scanned_files[:15]` ثم `sf.get("rel_path")`) ⇒ `TypeError:
    unhashable type 'slice'` وقت التشغيل يبتلعه `except
    Exception` (:1188) ⇒ إرفاق مجلد كسياق يتدهور صامتًا (header
    فقط بلا محتوى ملفات) — عكس قبول TSK-404/BUG-03 الموثّق.
    التسجيل: NEW_FINDINGS §NF-26.
  - **معالجة خطأ providers القائم (§0.8 — لا يُصلح)**: الخيار
    المُجرَّب `--exclude 'providers/openai_shelby\.py'` → providers/
    وحدها به = **Success في 10 ملفات** (يُستبعد الملف المعطوب وحده
    ويبقى فحص بقية providers). البديل المرفوض: إخراج providers/
    كلها من البوابة (خسارة تغطية 10 ملفات دون مبرر).
- **Behavior-preservation pre-check (S69)**:
  1. سطر check.sh + تعنوينات النوع + `# type: ignore` المعلَّق: صفر
     أثر runtime بالبناء (تعليقات وتعنوينات فقط).
  2. إصلاح NF-25: إضافة `provider_pool` و`approval_gate` لكائن deps
     (server.py:1089) + بادئة `deps.` في المواضع الثلاثة — **استعادة
     دلالة ما قبل 612 حرفيًا**: القيمتان تُربطان في main مرة واحدة
     قبل الخدمة ولا يُعاد ربطهما بعدها (api_switch_model لا يعيد
     تعيين pool — server.py:826–829 صراحة)؛ deps يُبنى عند كل نداء
     dispatch ⇒ لقطة وقت النداء ≡ قراءة global وقت النداء بعد
     الإقلاع. متسق مع ADR-002 (بقية الـ14 رمزًا لقطات مماثلة).
  3. إصلاح NF-26: التكرار على `list(scanned_files.items())[:15]` —
     يستعيد السلوك المقصود الموثّق (TSK-404)؛ الحالي مكسور صامتًا
     (لا سلوك مشروع يعتمد على الكسر). يُغطى باختبار جديد.
  4. إكمال Protocol `RegistryBackend` بـ`purge_terminal` — السطح
     الفعلي المستخدم (server.py:428 منذ TSK-303) والتنفيذان
     الوحيدان (ExecutionRegistry + alias) يملكانه؛ isinstance
     الـruntime_checkable يبقى ناجحًا (test_backends:138).
- **Architecture-Fitness pre-check (S69)**: تشديد بوابة جودة +
  إصلاح عقد وحدة مستخرجة = مع اتجاه القوس (§R8/QF-02)؛ لا حالة
  جديدة ولا اتجاه استيراد جديد؛ providers/ لا يُمس (استبعاد ملف
  واحد من الفحص فقط). تغيير تصميم البوابة (علم + استبعاد + نطاق)
  قرار بنيوي يلزمه **ADR-004 + قيد DECISION_LOG قبل الكود**.
- **Close-out (S69–70)**:
  - **ما نُفّذ** (ADR-004):
    - **check.sh (سطر البوابة)**: `--check-untyped-defs` +
      `--exclude 'providers/openai_shelby\.py'` + ضم `routes/
      server.py` — تعليق موسّع يوثّق لماذا العلم إلزامي ولماذا
      الاستبعاد مفرد (§0.8) ومتى يُرفع.
    - **تصفير الأخطاء الـ129 (لا-سلوكيًا)**: `_srv: Any = None` +
      استيراد typing في 7 ملفات routes (يصفّر 79)؛
      `# type: ignore[assignment]` معلَّق على 16 sentinel global
      في server.py (نمط `X: Type = None` تُملأ في main)؛
      `RUNNERS: dict[str, Any]`؛ `frame: dict[str, Any]`؛
      `cfg: Any` (api_switch_model) + `provider_config: Any`
      (main)؛ `provider: Any = None` عند التعريف الوحدوي :137
      (تعنوينه محليًا في main مستحيل — SyntaxError «annotated
      name can't be global»، اكتُشف وأُصلح أثناء التنفيذ)؛
      ignore مفرد لكاش `fm._api_search_index` الديناميكي المتعمد.
    - **إصلاح NF-25** (استعادة دلالة ما قبل 612): حقن
      `provider_pool` و`approval_gate` في deps (server.py:1097)
      + `deps.` في chat_dispatch.py:306,307,332 — pyflakes نظيف.
    - **إصلاح NF-26** (استعادة سلوك TSK-404 المقصود):
      `for rel_p, content in list(scanned_files.items())[:15]` —
      المحتوى يصل مسيَّجًا بدل التدهور الصامت.
    - **إكمال Protocol RegistryBackend**: `purge_terminal(keep_last
      =50) -> int` (core/backends.py) — السطح المستخدم منذ TSK-303.
  - **الاختبار السلبي الموثق (القبول)**:
    `tests/unit/test_mypy_gate_614.py::TestNegativePlantedCall` —
    نداء `_tsk614_nonexistent_function()` داخل def غير مُعنون
    (نمط دوال routes الفعلي): بأعلام البوابة **exit=1 +
    [name-defined]**؛ بدون العلم **exit=0** (يوثّق لماذا العلم
    شرط القبول). نُفّذ أيضًا يدويًا بزرع النداء في routes/meta.py
    الحقيقي: البوابة الكاملة exit=1 على 81 ملفًا ثم استُعيد الملف.
  - **اختبارات جديدة (10)**: بنية سطر البوابة (3) + السلبي (2) +
    NF-25 حقن واستهلاك وAST-لا-أسماء-عارية (3) + NF-26 وظيفيًا:
    attach يسلّم المحتوى مسيَّجًا + سقف 15 ملفًا (2).
  - **Gates (S70، على الشجرة المدموجة 3c516b6)**:
    - **mypy (سطر البوابة الجديد): Success — 81 ملفًا، exit=0**.
    - check.sh كاملًا: كل الأقسام خضراء حتى color lint (TF-04/D-2
      المعروف — 127 لونًا خامًا في style.css، خارج هذه المهمة).
    - lint_handler_state نظيف · contracts+parity **113** ·
      goldens+ws_router **32** · المتأثرة (614+blueprints+
      force_approval+fencing+scan_start+instr609+backends+
      except_narrowing) **104** — صفر إخفاقات.
    - Regression junitxml: **1822 = 1 failed / 1787 passed / 34
      skipped** (69.7s) — الإخفاق الوحيد theme_tokens (TF-04/D-2)؛
      1812+10 = 1822 ✓ لا انحدار.
  - **Metrics (القبول)**: نطاق mypy 73→**81 ملفًا مفحوصًا** (+routes/
    +server.py −openai_shelby) وبعمق أكبر (أجسام غير مُعنونة تُفحص
    أول مرة)؛ QF-02 مغلقة — عيوب كـ RP-01/NF-25/NF-26 تُلتقط
    ساكنًا (وقد التقط الفحصُ علّتين فعليتين قبل أي مستخدم)؛
    check.sh قابل للنجاح حتى بوابة الألوان أول مرة منذ دخول خطأ
    providers القائم.
  - **انحرافات موثّقة**: (1) القبول تطلّب علمًا لا مجرد توسيع قائمة
    (الأدلة أثبتت أن التوسيع وحده بوابة شكلية)؛ (2) علّتان حقيقيتان
    أُصلحتا ضمن المهمة (NF-25 انحدار 612، NF-26 قائمة منذ 0d74dad)
    — كلاهما ضمن سطح المهمة (أخطاء كشفها الفحص الموسع نفسه).
  - **Commits**: db46952 (أدلة+pre-checks+NF-25/26) · ea28700
    (ADR-004 + DECISION_LOG قبل الكود) · 151f2e0 (التنفيذ
    والاختبارات — دمج خارجي 3c516b6).

## M9 — Exposure & Consent Surface (حزمة الإظهار + بقايا الأمان)

### TSK-615 — ApprovalGate: طلبات متزامنة
- **Status**: ✅ DONE (S71) · **Priority**: P2
- **Objective**: خريطة طلبات معلقة بمفاتيح بدل `_pending_id` المفرد — طلبان
  متزامنان يُحلان مستقلين.
- **Background**: ASF-05 (§R4، approval.py:170–175/238–247).
- **Acceptance**: اختبار: طلبان متداخلان → كلاهما قابل للحل بلا موت بمهلة؛
  fail-closed يبقى (مهلة لكل طلب).
- **Gates**: Security · Testing · Regression. · **Rollback**: revert.
- **Evidence (S71 — قراءة core/approval.py كاملة 286 سطرًا + تجارب
  تزامن حية)**:
  - **الخانة المفردة**: `_pending_id/_pending_hash/_pending_event/
    _pending_result/_pending_reason` (approval.py:171–175)؛
    `_interactive` يكتب فوقها بلا شرط (:242–247)؛ `resolve` يطابق
    الخانة الوحيدة (:214–222)؛ أول خيط يخرج **يصفّر الخانة للجميع**
    (:258–260).
  - **تجارب حية (4 سيناريوهات، طلبان متداخلان r1 ثم r2)**:
    - **A — resolve(r2, approve) ⇒ r1 اعتُمد أيضًا** (`user_approved`
      للاثنين): `_pending_event` واحد مشترك — `set()` يوقظ كل
      المنتظرين وكلهم يقرأون `_pending_result=True` ⇒ **موافقة زائفة
      fail-OPEN** — أسوأ من توصيف ASF-05 («fail-closed، استنزاف
      فقط») ⇒ **NF-27** (C5/S2 — NEW_FINDINGS).
    - B — resolve(r1) بعد الكتابة فوقه ⇒ matched=False والاثنان
      يموتان بمهلة (الاستنزاف الموثق في ASF-05).
    - C — resolve(r2, deny) ⇒ الاثنان `user_denied` (fail-closed لكن
      تلويث تدقيق: r1 سُجّل قرار مستخدم لم يصدر بحقه).
    - D — resolve متأخر بعد المهلة ⇒ False (سليم).
  - **المستهلكون (لا تغيير عقد مطلوب)**: نسخة بوابة واحدة مشتركة
    (server.py:1937، mode من auto_execute، مهلة 120s) تُحقن في deps
    (server.py:1104 — NF-25) وChainBridge (:1979) وحلقات agent ·
    `resolve` يُستدعى من bridge.resolve_approval (chain/bridge.py:289
    ← WS server.py:1214) وagent_loop (:305 cancel، :318
    approve_command ← WS server.py:1130) — كلاهما يمرر request_id +
    payload_hash فالخريطة المفتاحية تحفظ التحقق لكل مدخل ·
    `request()` يُستدعى من bridge:567 وagent_loop:524 وrunners
    direct:88/chain:102/agent:115/delegate:111 · `pending_request_id()`
    لا يستهلكه إنتاج إطلاقًا — اختبارات فقط
    (test_approval.py:98/121/138/189/207) · agent_loop يحتفظ بمرجعيه
    `_pending_approval_id/_hash` (:504–505/:527–528) للإلغاء فقط —
    لا يمسّه التغيير الداخلي.
  - **حكم ADR**: لا يلزم — بنية بيانات داخلية لصنف واحد يمليها نص
    المهمة حرفيًا؛ التواقيع العامة (request/resolve/pending_request_id/
    audit_entries) بلا تغيير؛ لا حدود وحدات جديدة.
- **Behavior-preservation pre-check (S71 — قبل التعديل)**:
  1. السطح العام دون تغيير: تواقيع request/resolve/pending_request_id/
     audit_entries وشكل قيد التدقيق كما هي.
  2. مسارات الطلب الواحد (كل ما تمارسه الاختبارات الـ19 القائمة
     والإنتاج أحادي المستخدم) متطابقة دلاليًا: تسجيل → انتظار →
     حل/مهلة → قيد؛ رفض hash خاطئ يبقى؛ المهلة تبقى deny (fail-closed).
  3. `pending_request_id()` يعيد الأحدث تسجيلًا (مع ≤1 معلّق =
     السلوك الحالي حرفيًا — يكفي الاختبارات القائمة).
  4. التغيير السلوكي **المقصود والمحصور**: عزل الطلبات المتداخلة
     (إصلاح A/B/C أعلاه) — هذا هو نص القبول لا انحرافًا عنه.
  5. التحقق: test_approval.py الـ19 تمرّ بلا تعديل + الانحدار الكامل
     عند خط 1822 = 1F/1787P/34S (theme_tokens/TF-04 حصرًا).
- **Architecture-Fitness pre-check (S71)**:
  - التغيير محصور في core/approval.py (صنف واحد)؛ صفر تبعيات جديدة؛
    صفر تغيير في bridge/agent_loop/runners/server.
  - النمط: خريطة `request_id → مدخل (hash, Event, result, reason)`
    مع Event لكل مدخل — نفس نمط التذاكر المفتاحية في
    ExecutionRegistry (المعيار القائم في المستودع).
  - لا نموّ غير محدود: المدخل يزيله خيطه المالك في finally ⇒ حجم
    الخريطة = عدد الخيوط المنتظرة آنيًا (محدود بخيوط runners).
  - إضافة قراءة `pending_request_ids()` (جمع) للاختبارات/الرصد —
    توسعة لا كسر.
- **Close-out (S71)**:
  - **التنفيذ (core/approval.py — ملف واحد، صفر تغيير في
    المستهلكين)**: dataclass جديد `_PendingEntry(payload_hash,
    event, result, reason)` — Event مستقل لكل طلب؛ الخانات
    الخمس المفردة (`_pending_id/_hash/_event/_result/_reason`)
    استُبدلت بـ `self._pending: dict[str, _PendingEntry]` ·
    `_interactive`: تسجيل المدخل تحت القفل ثم try/finally —
    الخيط المالك يزيل مدخله حصرًا (`pop(req.request_id)`) — لا
    تصفير جماعي ولا تسرّب · `resolve`: مطابقة
    `_pending.get(request_id)` + hash للمدخل نفسه ·
    `pending_request_id()`: يرجع الأحدث (`next(reversed(dict))`)؛
    مع ≤1 معلّق = السلوك القديم حرفيًا · جديد:
    `pending_request_ids()` (الأقدم أولاً).
  - **القبول محقق بالتجربة والاختبار**: طلبان متداخلان — اعتماد
    r2 + رفض r1 مستقلين (سيناريو A الذي كان موافقة زائفة) ·
    حلّ الأقدم أولاً (سيناريو B الذي كان مستحيلاً) · fail-closed:
    مهلة لكل طلب على حدة + رفض hash متقاطع + رفض الرد المتأخر
    بعد المهلة · التدقيق ينسب كل قرار لطلبه الصحيح (سيناريو C).
  - **اختبارات جديدة**: tests/unit/test_approval_concurrent.py —
    **9 اختبارات** (TestConcurrentResolution 3: حلّ مستقل /
    لا-موافقة-زائفة-NF-27 / حلّ-الأقدم-ASF-05؛
    TestFailClosedPreserved 3: مهلة لكل طلب + خريطة نظيفة /
    رفض hash متقاطع / نسبة التدقيق؛
    TestSingleRequestBehaviorUnchanged 3: pending_request_id القديم /
    resolve بلا معلّق noop / رد متأخر مرفوض).
  - **البوابات (S71)**: test_approval.py الـ**19 القائمة تمر بلا
    تعديل** + 9 جديدة = 28 · pyflakes نظيف · lint_handler_state
    نظيف · contracts+parity **113** · goldens+ws_router **32** · mypy
    بوابة TSK-614 **Success 81 ملفًا** · regression عبر `--junitxml`:
    **1831 = 1F/1796P/34S 79.9s** (theme_tokens/TF-04 حصرًا؛
    1822+9 = 1831 ✓).
  - **Commits**: a55267f (أدلة + pre-checks + NF-27 قبل الكود — دمج
    خارجي b825afc) · f37be66 (التنفيذ + الاختبارات).

### TSK-616 — إظهار سقف snapshot (rollback جزئي)
- **Status**: ✅ DONE (S72) · **Priority**: P2
- **Objective**: عند تجاوز `_CKPT_MAX_FILES`/سقف الحجم — تحذير صريح في إطار
  الموافقة/النتيجة («التراجع سيكون جزئيًا») بدل الصمت.
- **Background**: ASF-03 (§R4). · **Acceptance**: اختبار بحد مصغّر → إطار
  يحمل علم partial_rollback؛ الواجهة تعرضه (toast/نص).
- **Gates**: Security · Testing · Documentation. · **Rollback**: revert.
- **Evidence (S72)**:
  - **السقفان**: `_CKPT_MAX_FILES = 400` + `_CKPT_MAX_FILE_BYTES =
    512*1024` (chain/agent_tools.py:190–191، سمتا صنف قابلتان للتطويع
    في الاختبار). نقطة الصمت: `_workspace_signatures`
    (:578–603) — عند بلوغ السقف `return sigs` مبكرًا (:590–591)
    **بلا أي إشارة**؛ الملف الأكبر من 512KB يُتخطى `continue`
    (:599–600) بلا إشارة. النتيجة ترجع dict فقط — **معلومة الاقتطاع
    تُفقد في المصدر** ⇒ كل ما فوقها لا يعلم.
  - **المسار الصامت (ASF-03 حرفيًا)**: tool_run_command يلتقط
    `pre_sigs = _workspace_signatures()` ثم `snapshot(...)` (:506–509)؛
    بعد الأمر `_changed_paths(pre)` يقارن post-scan بـ pre (:604–608) —
    ملف رقم 401 الذي غيّره الأمر **غير موجود في أي من المسحين** ⇒ لا
    snapshot ولا seal ⇒ التراجع جزئي، والتقرير الحالي يطبع
    `🧷 [checkpoint]: الأمر غيّر N ملف — قابلة للاستعادة` (:571–573)
    وهو **مضلِّل إيجابيًا** عند الاقتطاع (يوحي بتغطية كاملة).
  - **قنوات الإظهار المتاحة (بلا تغيير عقد)**: AgentTools **لا يملك
    ws_send** (تحقق: صفر مطابقات ws_send/emit/callback في الملف) —
    القناة الوحيدة هي **نص التقرير المرجَع** من tool_run_command،
    وAgentLoop يبثه `agent_step/done` بـ `preview: result[:200]`
    (agent_loop.py:257–263 للمعتمد، :212–218 للآمن) وتعرضه الواجهة
    في كارت التيرمنال (`updateTerminalCardStatus(..., data.preview)`
    app.js:674). إطار الموافقة (`awaiting_approval` agent_loop.py:512–521)
    يُبنى **قبل** معرفة عدد الملفات المتغيرة ⇒ الإظهار الصادق يكون في
    إطار **النتيجة** (بعد المسح البعدي) لا الموافقة — يوافق نص المهمة
    («إطار الموافقة/النتيجة»).
  - **مسار apply (action_applier.py:188–207)**: يلقط snapshot لملفات
    الـ batch المعروفة بأسمائها (لا مسح workspace) ⇒ سقفا المسح لا
    ينطبقان عليه — خارج نطاق ASF-03.
  - **fixtures قائمة**: test_run_command.py FakeCmd/_tools (:34–57)؛
    test_rollback_ui.py يقرأ app.js نصيًا للتحقق من الواجهة (:37، :405).
- **Behavior-preservation pre-check (S72 — قبل التعديل)**:
  1. لا تغيير في السقفين نفسيهما (ASF-03: «الإصلاح إظهار لا رفع سقف»
    — MASTER_REVIEW:722) ولا في منطق snapshot/seal/الاستعادة.
  2. تحت السقف (المسار الشائع): التقرير والسلوك حرفيًا كما هما —
    العلم/التحذير يظهران **فقط** عند اقتطاع فعلي.
  3. توقيع `_workspace_signatures` يتغير داخليًا (إرجاع علم اقتطاع
    إضافي) — دالة خاصة `_` لا يستهلكها أحد خارج الصنف (تحقق: صفر
    مطابقات في tests/ وبقية المستودع) ⇒ لا كسر عقد.
  4. الإظهار إضافة نصية للتقرير + حقل جديد في إطار agent_step القائم
    (حقول إضافية لا تكسر مستهلكي JS الحاليين — قراءة بحقول مسماة).
  5. التحقق: اختبارات test_run_command/test_checkpoint القائمة تمر بلا
    تعديل + خط الانحدار 1831 = 1F/1796P/34S (theme_tokens حصرًا).
- **Architecture-Fitness pre-check (S72)**:
  - التغيير محصور: chain/agent_tools.py (مصدر الحقيقة للاقتطاع) +
    chain/agent_loop.py (تمرير العلم في إطار النتيجة) + static/app.js
    (عرض) — لا وحدات جديدة ولا تبعيات.
  - النمط: العلم يُشتق حيث تحدث الحقيقة (المسح) ويُمرَّر صراحة —
    لا استنتاج لاحق هش (عدّ الملفات ≥400 مثلًا).
  - الواجهة تعرض حالة قائمة فقط (إظهار) — ضمن قرار المهمة المقررة،
    ليس تغيير سلوك منتج.
- **Close-out (S72)**:
  - **التنفيذ (كما صُمم في التحقق المسبق)**:
    1. `chain/agent_tools.py`: علم `self.last_partial_rollback` (يُصفَّر
       مطلع كل tool_run_command)؛ `_workspace_signatures` →
       `tuple[dict, bool]` (True عند سقف العدد أو تخطي ملف فوق سقف
       الحجم — الحقيقة تُشتق حيث تحدث)؛ `_changed_paths` →
       `tuple[list, bool]`؛ عند `pre_truncated or post_truncated`:
       العلم True + `_LOG.warning` + سطر ⚠️ عربي صريح في التقرير
       («التراجع عن آثار هذا الأمر سيكون جزئيًا» مع قيم السقفين) —
       موضوع **خارج** `if changed:` عمدًا (تغييرات فوق السقف غير مرئية
       للمقارنة أصلًا؛ قد يكون changed فارغًا زورًا).
    2. `chain/agent_loop.py`: إطار `agent_step/done` للمسار المعتمد
       يحمل `"partial_rollback": bool(getattr(self.tools,
       "last_partial_rollback", False))` — حقل إضافي لا يكسر أحدًا.
    3. `static/app.js`: `handleRunCommandStep` عند done يستدعي
       `showPartialRollbackWarning` لو العلم مرفوع — toast تحذيري
       + نص دائم `.terminal-partial-rollback` على كارت التيرمنال
       («⚠️ التراجع سيكون جزئيًا — المشروع تجاوز سقف مسح snapshot»).
    4. `static/style.css`: `.toast.warning` + `.terminal-partial-rollback`
       بتوكنز الثيم فقط (`var(--warning)` — منضبط TF-04).
  - **الاختبارات**: `tests/unit/test_snapshot_cap_visibility.py`
    (10 اختبارات): سقف عدد مصغّر → علم + ⚠️ في التقرير؛ سقف حجم
    مصغّر → نفس السلوك؛ تحت السقفين → لا علم ولا ⚠️ (سلبي)؛ بلا
    checkpoint → لا علم (سلبي)؛ تصفير العلم بين الأوامر؛ E2E عبر
    AgentLoop حقيقي (FakeProvider + بوابة auto) → إطار done يحمل
    partial_rollback=True فوق السقف / False تحته؛ فحص نصي لـ app.js
    (قراءة العلم + toast + نص دائم) وstyle.css (توكنز فقط).
  - **البوابات**: pyflakes نظيف (تحذيرات agent_loop الأربعة قائمة
    بأصل المستودع قبل التعديل — تحقق بـ git stash)؛
    lint_handler_state نظيف؛ mypy Success 81 ملفًا؛ contracts+parity
    113 ✓؛ goldens+ws_router 32 ✓؛ الانحدار الكامل **1841 = 1F/1806P/34S**
    (1831+10؛ الفشل الوحيد theme_tokens — TF-04/D-2 معروف).
  - **خط انحدار جديد: 1841**.

### TSK-617 — أمان الافتراضات البرمجية (ينتظر D-1)
- **Status**: BLOCKED (قرار منتج D-1) · **Priority**: P2
- **Objective**: قلب `enforce` (ASF-04) و`force_command_approval` (NF-16)
  إلى افتراض آمن في الكود لا في config فقط.
- **Acceptance**: حذف المفاتيح من config → السلوك الآمن؛ config الحالي بلا
  تغيير سلوكي.
- **Gates**: Security · Regression · Documentation. · **Rollback**: revert.

### TSK-618 — تضييق except الابتلاعي في path_policy
- **Status**: ✅ DONE (S73) · **Priority**: P2
- **Objective**: استبدال `except Exception: pass` (path_policy.py:107–108)
  بمعالجة OSError موسومة (سجل تحذير) — الفحص لا يُتخطى بصمت.
- **Background**: ASF-07 (§R4). · **Acceptance**: اختبار symlink خطأ FS →
  تحذير مسجل والاحتواء النهائي يعمل؛ عدّاد NF-14 لا يرتفع.
- **Gates**: Security · Testing. · **Rollback**: revert.
- **Evidence (S73)**:
  - **الموضع**: `chain/path_policy.py:98–109` — حلقة فحص symlink تصعد
    من `raw_path` (غير المحلول) نحو الجذر؛ `try:` (:102) يضم
    `curr.is_symlink()` (:103) **و`raise PermissionError`** (:104–106)
    معًا؛ `except Exception: pass` (:107–108).
  - **NF-28 (تجربة حية S73 — أشد من توصيف ASF-07)**: لأن `raise
    PermissionError` داخل الـ try نفسه، **الرفض ذاته يُبتلع**
    (PermissionError ⊂ OSError ⊂ Exception) ⇒ فحص symlink **ميت
    بالكامل** لا «يُتخطى عند خطأ FS» فقط: تجربة A (symlink داخل الجذر
    لملف داخل الجذر → **يمر**) وB (ملف عبر مجلد symlink → **يمر**).
    الخطوط الصلبة تصمد: C (symlink يشير خارج الجذر → يُرفض بالاحتواء
    على المسار المحلول :89–95) وD (symlink يخفي ملف سر داخلي → يُرفض
    بفحص الأسرار على المحلول :109–113). [SUPERSEDES جزئيًا توصيف
    ASF-07 «تخطٍّ صامت عند خطأ FS» — الواقع أسوأ: الفحص لا يرفض شيئًا
    أبدًا] — مسجل NF-28 في NEW_FINDINGS.md.
  - **المستهلكون**: كل النداءات تمرر `allow_symlinks=False`
    (action_applier:200، agent_tools:678، context_builder:475/486/502،
    file_manager:267، safe_reader:210) — لا نداء بـ True في الشيفرة
    الحية. لا استخدام مشروع لـ symlinks داخل workspace في الاختبارات
    (grep: test_restore_zip_slip فقط — وهو يرفضها في طبقة أخرى).
  - **الملف بلا logging حاليًا** (imports: os/pathlib/typing فقط) —
    يحتاج logger جديد. `PermissionError ⊂ OSError` (تحقق runtime) ⇒
    التقاط OSError وحده مع بقاء raise خارجه يتطلب فصل الفحص عن الرفض.
- **Behavior-preservation pre-check (S73 — قبل التعديل)**:
  1. المسار الشائع (لا symlinks): سلوك مطابق حرفيًا — لا فرق.
  2. **تغيير سلوك مقصود ضمن نص المهمة**: فحص symlink الميت يعود
     للعمل (symlink داخلي يُرفض الآن) — هذا استعادة السلوك الموثق
     المقصود (نص الرفض موجود في الشيفرة منذ البداية؛ المهمة P2 أمنية
     مقررة في Stage 2) وليس قرار منتج جديدًا.
  3. خطأ FS حقيقي أثناء is_symlink: كان صمتًا مطلقًا → يصبح تحذير
     log + متابعة (القبول حرفيًا: «تحذير مسجل والاحتواء النهائي
     يعمل») — لا رفع استثناء جديد في هذا الفرع ⇒ لا كسر مستهلكين.
  4. عدّاد NF-14 (نمط الابتلاع المقصود الموسوم في server.py) لا
     يرتفع — المعالجة هنا موسومة بسجل لا `pass` صامت.
  5. التحقق: regression كامل (خط 1841) — أي اختبار قائم يعتمد على
     مرور symlink داخلي سيُكشف (grep المسبق: لا شيء).
- **Architecture-Fitness pre-check (S73)**:
  - التغيير محصور في chain/path_policy.py + اختبارات جديدة — لا
    وحدات ولا تبعيات جديدة (logging قياسي).
  - النمط: فصل «القياس» (is_symlink داخل try ضيق يلتقط OSError
    وحده) عن «القرار» (raise خارج الـ try) — نفس مبدأ TSK-616
    (الحقيقة تُشتق حيث تحدث ولا تُبتلع في الطريق).
- **Close-out (S73)**:
  - **التنفيذ**: `chain/path_policy.py` — logger جديد
    `chain.path_policy`؛ حلقة الفحص: `is_link = curr.is_symlink()`
    داخل try ضيق يلتقط **OSError وحده** مع `_LOG.warning` موسوم
    (المقطع + المسار المطلوب + الخطأ + تذكير بأن الاحتواء/الأسرار
    النهائيين ما زالا يطبقان)؛ `raise PermissionError` انتقل خارج
    الـ try ⇒ الرفض لم يعد يُبتلع (إصلاح NF-28) وخطأ FS لم يعد
    صامتًا (إصلاح ASF-07). تحقق حي قبل/بعد: A/B (symlink داخلي /
    مجلد symlink) كانا يمران → يُرفضان؛ المسار العادي وallow_symlinks
    =True بلا تغيير؛ C/D (الخطوط الصلبة) محفوظة.
  - **الاختبارات**: `tests/unit/test_path_policy_symlink.py` (9، أول
    تغطية مباشرة لـ path_policy): إحياء الرفض (ملف/مجلد)؛
    allow_symlinks=True يمر؛ المسار العادي بلا تغيير؛ **خطأ FS
    محقون (monkeypatch is_symlink→OSError) → تحذير مسجل (caplog)
    والاحتواء النهائي يعمل** (القبول حرفيًا)؛ سلبي بلا ضجيج؛ الخطان
    الصلبان محفوظان؛ حارس بنيوي regex ضد عودة `except
    Exception: pass` للملف (عدّاد NF-14 لا يرتفع).
  - **البوابات**: pyflakes نظيف · lint_handler_state نظيف · mypy
    Success 81 ملفًا · contracts+parity 113 ✓ · goldens+ws_router 32 ✓ ·
    الانحدار الكامل **1850 = 1F/1815P/34S** (1841+9؛ theme_tokens/TF-04
    حصرًا — فشل test_search_perf في التمريرة الأولى ثبت أنه flaky:
    يمر معزولًا ×2 وفي إعادة التمريرة الكاملة — حد زمني 1s على
    عتاد مشترك؛ لا علاقة للتغيير بمساره).
  - **خط انحدار جديد: 1850**.

### TSK-619 — بطاقة الخطة التفاعلية (CP-1)
- **Status**: TODO · **Priority**: P2
- **Objective**: ترقية `showPlanCard` إلى artifact تفاعلي: تعطيل/تفعيل خطوة
  (checkbox) قبل «نفّذ» — executePlan يرسل المفعّل فقط.
- **Background**: UXF-01 + CP-1 ADOPT (§R9، app.js:3099–3128).
- **Files**: `static/app.js`، وحدة نقية جديدة `static/js/plan_card.js` +
  اختبار node لها، `server.py` لا يتغير (actions المرسلة subset).
- **Acceptance**: اختبار وحدة: تعطيل خطوة → payload التنفيذ بدونها؛ سيناريو
  يدوي موثق.
- **Gates**: Testing · Regression (كل-الخطوات-مفعلة = السلوك القديم حرفيًا).
- **Behavior preservation**: الافتراضي (لا لمس) = تنفيذ كامل كما اليوم.
- **Rollback**: revert. · **Resume notes / Blocker**: —

### TSK-620 — سرد الجلسة (CP-8)
- **Status**: TODO · **Priority**: P2 · **Dependencies**: TSK-610 (سجل runs).
- **Objective**: عرض timeline يجمع (طلب → خطة → موافقات → تنفيذ → نتائج)
  فوق RunHistory القائمة — محليًا، بلا cloud (Non-Goal §15.2).
- **Background**: UXF-05 + CP-8 ADOPT (§R9).
- **Acceptance**: جلسة بها run واحد معتمد → السرد يعرض ≥ 4 محطات بترتيبها؛
  وحدة نقية مختبرة node.
- **Gates**: Testing · Documentation. · **Rollback**: revert.

### TSK-621 — Permissions UI قراءة (CP-5)
- **Status**: TODO · **Priority**: P2
- **Objective**: لوحة قراءة تعرض سياسة الأمان الفعالة (allowlist،
  SAFE/DANGEROUS، force_approval) من config عبر REST قراءة — glass box.
- **Background**: UXF-04 + CP-5 (§R9). · **Acceptance**: endpoint قراءة +
  لوحة تعرض القيم الحية؛ لا مسار كتابة.
- **Gates**: Security (قراءة فقط) · Testing. · **Rollback**: revert.

### TSK-622 — إعادة تصويت RELEASE_READINESS (ينتظر إغلاق M6)
- **Status**: TODO · **Priority**: P2 · **Dependencies**: M6 كاملًا (601–605).
- **Objective**: إعادة تقييم G1–G5 على الكود الحالي (TD-03) بمدخلات ما بعد
  التنفيذ + RP-01/TF-03 المصلحة؛ تحديث RRR بقسم re-vote مؤرَّخ (append).
- **Acceptance**: قسم جديد في RRR بحكم لكل بوابة بدليل حي؛ لا حذف للنص القديم.
- **Gates**: Documentation. · **Rollback**: revert.

## M10 — Hygiene (P3)

### TSK-623 — أرشفة improvements/ (ينتظر D-3) — P3, BLOCKED
حذف/نقل من الشجرة = عملية destructive → تنتظر موافقة D-3. Acceptance:
grep/wc نظيفة من 892KB التلوث؛ المحتوى محفوظ في أرشيف.
### TSK-624 — retro-ADR لإعادة تصميم v25 — P3, TODO
توثيق قرار v25 (TD-04) في ADR + Decision Log. Acceptance: ملف ADR يشرح
النطاق والأثر والحرّاس المكسورة وكيف أُصلحت.
### TSK-625 — صلابة _parse_args_body — P3, TODO
تفكيك متسامح مع قيم متعددة الأسطر (ASF-06) + اختبارات حالات عدائية.
### TSK-626 — قرار proposed_actions — P3, TODO
توثيق الفرع test-only أو توصيله بمستهلك (RP-04)؛ Acceptance: سطر عقد موثق
في runners + تعليق في server.py.

---

## جدول تتبّع الحالة (المصدر الوحيد للحالة مع PROGRESS.md)

| TSK | M | P | Status | ملاحظة |
|---|---|---|---|---|
| 601 | M6 | P1 | ✅ DONE (S33–34) | 6 اختبارات جديدة خضراء؛ regression نظيف (4F المعروفة فقط) |
| 602 | M6 | P1 | ✅ DONE (S35–36) | 6 اختبارات جديدة؛ مواضع الحقن الخام 5→0؛ regression نظيف |
| 603 | M6 | P1 | ✅ DONE (S37) | fail-closed بـ sentinel؛ 7 اختبارات جديدة؛ regression نظيف |
| 604 | M6 | P1 | ✅ DONE (S38–39) | زرا وكيلان مخفيان + سطر الترخيص؛ إخفاقات البوابة 4→2 |
| 605 | M6 | P1 | TF-02 ✅ (S40) · TF-04 BLOCKED(D-2) | إخفاقات البوابة 2→1؛ المتبقي ينتظر رد المالك |
| 606 | M7 | P2 | ✅ DONE (S43) | تخييط apply/direct + إصلاح BUG جانبي في معالج cancel_run؛ +2 اختبارات |
| 607 | M7 | P2 | ✅ DONE (S45–46) | آخر جيب برومبت خارج الميزانية ضُم؛ +6 اختبارات |
| 608 | M7 | P2 | ✅ DONE (S47–48) | reap_stale مفعّل + نبض حياة في المحوّل/الدفعة/الاستكمال؛ +17 اختبارًا |
| 609 | M7 | P2 | ✅ DONE (S49–54) | duration_ms على bus للمسارات 4/4 + توقيت المصادر + duration/token في plan/done؛ +11 اختبارًا |
| 610 | M7 | P2 | ✅ DONE (S55–57) | سجل JSONL لكل run منتهٍ + p50/p95 (nearest-rank) + REST قراءة /api/metrics/runs؛ +17 اختبارًا |
| 611 | M8 | P2 | ✅ DONE (S58–60) | استخراج راوتر WS إلى core/ws_router.py (ADR-001)؛ الكتلة 506→13 سطرًا؛ +10 اختبارات |
| 612 | M8 | P2 | ✅ DONE (S61–63) | استخراج مسار الإرسال إلى core/chat_dispatch.py (ADR-002)؛ server.py −449 سطرًا؛ mypy نظيف |
| 613 | M8 | P2 | ✅ DONE (S64–67) | تجميع 25 REST route في routes/ (7 blueprints، ADR-003)؛ server.py −478 سطرًا؛ mypy نظيف 70 ملفًا |
| 614 | M8 | P2 | ✅ DONE (S69–70) | بوابة mypy موسعة (+routes/ +server.py، --check-untyped-defs، ADR-004)؛ 81 ملفًا Success؛ أغلقت QF-02 وكشفت NF-25/NF-26 وأصلحتهما |
| 615 | M9 | P2 | ✅ DONE (S71) | خريطة طلبات معلّقة بمفاتيح + Event لكل طلب؛ أصلحت ASF-05 (استنزاف) وNF-27 (موافقة زائفة)؛ 9 اختبارات تزامن جديدة |
| 616 | M9 | P2 | ✅ DONE (S72) | علم partial_rollback يُشتق عند المسح ويصل الإطار والواجهة (⚠️ toast + نص على الكارت)؛ 10 اختبارات جديدة؛ خط الانحدار 1841 |
| 617 | M9 | P2 | BLOCKED(D-1) | |
| 618 | M9 | P2 | ✅ DONE (S73) | فصل القياس عن القرار أحيا فحص symlink الميت (NF-28) وضيّق الالتقاط إلى OSError موسوم؛ 9 اختبارات (أول تغطية لـ path_policy)؛ خط الانحدار 1850 |
| 619 | M9 | P2 | TODO | CP-1 |
| 620 | M9 | P2 | TODO | بعد 610 — CP-8 |
| 621 | M9 | P2 | TODO | CP-5 |
| 622 | M9 | P2 | TODO | بعد M6 — TD-03 |
| 623 | M10 | P3 | BLOCKED(D-3) | destructive |
| 624 | M10 | P3 | TODO | |
| 625 | M10 | P3 | TODO | |
| 626 | M10 | P3 | TODO | |
