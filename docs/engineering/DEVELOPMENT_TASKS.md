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
- **Status**: IN-PROGRESS (S55) · **Priority**: P2
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

## M8 — Decompose g1 (خطة R8: QG-01→04)

### TSK-611 — QG-01: استخراج راوتر WS
- **Status**: TODO · **Priority**: P2
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

### TSK-612 — QG-02: استخراج مسارات الإرسال
- **Status**: TODO · **Priority**: P2 · **Dependencies**: TSK-611, TSK-601.
- **Objective**: نقل `_dispatch_chat_message` (~477 سطرًا) إلى وحدة إرسال
  مستقلة تستهلك `_parsed_to_actions` الموحدة (من TSK-601).
- **Background**: QG-02 (§R8). · **Files**: `server.py`، وحدة جديدة، goldens.
- **Acceptance**: goldens dispatch parity خضراء؛ mypy على الوحدة الجديدة نظيف.
- **Gates**: Architecture (ADR) · Testing · Regression.
- **Behavior preservation**: bit-identical frames.
- **Metrics**: سطور server.py. · **Rollback**: revert.

### TSK-613 — QG-03: تجميع REST blueprints
- **Status**: TODO · **Priority**: P2 · **Dependencies**: TSK-612.
- **Objective**: تجميع 27 route في Flask Blueprints موضوعية (rollback/memory/
  project/…) — بعد استقرار قرار g5.
- **Background**: QG-03 (§R8). · **Acceptance**: كل endpoints تستجيب كما قبل
  (اختبار smoke REST)، عدد routes ثابت.
- **Gates**: Architecture · Testing · Regression. · **Rollback**: revert.

### TSK-614 — QG-04: ضم server.py (والوحدات المستخرجة) لبوابة mypy
- **Status**: TODO · **Priority**: P2 · **Dependencies**: TSK-611..613.
- **Objective**: توسيع نطاق mypy في check.sh ليشمل الوحدات المستخرجة ثم
  server.py المتبقي — إغلاق QF-02 (عيوب كـ RP-01 تُلتقط ساكنًا).
- **Background**: QG-04 + QF-02 (§R8)؛ RP-01 كدليل الكلفة.
- **Acceptance**: `mypy` أخضر على النطاق الموسع في check.sh؛ البوابة تفشل
  عند دس نداء لدالة غير موجودة (اختبار سلبي موثق).
- **Gates**: Architecture · Testing · Documentation. · **Rollback**: revert سطر البوابة.

## M9 — Exposure & Consent Surface (حزمة الإظهار + بقايا الأمان)

### TSK-615 — ApprovalGate: طلبات متزامنة
- **Status**: TODO · **Priority**: P2
- **Objective**: خريطة طلبات معلقة بمفاتيح بدل `_pending_id` المفرد — طلبان
  متزامنان يُحلان مستقلين.
- **Background**: ASF-05 (§R4، approval.py:170–175/238–247).
- **Acceptance**: اختبار: طلبان متداخلان → كلاهما قابل للحل بلا موت بمهلة؛
  fail-closed يبقى (مهلة لكل طلب).
- **Gates**: Security · Testing · Regression. · **Rollback**: revert.

### TSK-616 — إظهار سقف snapshot (rollback جزئي)
- **Status**: TODO · **Priority**: P2
- **Objective**: عند تجاوز `_CKPT_MAX_FILES`/سقف الحجم — تحذير صريح في إطار
  الموافقة/النتيجة («التراجع سيكون جزئيًا») بدل الصمت.
- **Background**: ASF-03 (§R4). · **Acceptance**: اختبار بحد مصغّر → إطار
  يحمل علم partial_rollback؛ الواجهة تعرضه (toast/نص).
- **Gates**: Security · Testing · Documentation. · **Rollback**: revert.

### TSK-617 — أمان الافتراضات البرمجية (ينتظر D-1)
- **Status**: BLOCKED (قرار منتج D-1) · **Priority**: P2
- **Objective**: قلب `enforce` (ASF-04) و`force_command_approval` (NF-16)
  إلى افتراض آمن في الكود لا في config فقط.
- **Acceptance**: حذف المفاتيح من config → السلوك الآمن؛ config الحالي بلا
  تغيير سلوكي.
- **Gates**: Security · Regression · Documentation. · **Rollback**: revert.

### TSK-618 — تضييق except الابتلاعي في path_policy
- **Status**: TODO · **Priority**: P2
- **Objective**: استبدال `except Exception: pass` (path_policy.py:107–108)
  بمعالجة OSError موسومة (سجل تحذير) — الفحص لا يُتخطى بصمت.
- **Background**: ASF-07 (§R4). · **Acceptance**: اختبار symlink خطأ FS →
  تحذير مسجل والاحتواء النهائي يعمل؛ عدّاد NF-14 لا يرتفع.
- **Gates**: Security · Testing. · **Rollback**: revert.

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
| 610 | M7 | P2 | TODO | بعد 609 |
| 611 | M8 | P2 | TODO | ADR |
| 612 | M8 | P2 | TODO | بعد 611+601 |
| 613 | M8 | P2 | TODO | بعد 612 |
| 614 | M8 | P2 | TODO | بعد 611..613 — يغلق QF-02 |
| 615 | M9 | P2 | TODO | |
| 616 | M9 | P2 | TODO | |
| 617 | M9 | P2 | BLOCKED(D-1) | |
| 618 | M9 | P2 | TODO | |
| 619 | M9 | P2 | TODO | CP-1 |
| 620 | M9 | P2 | TODO | بعد 610 — CP-8 |
| 621 | M9 | P2 | TODO | CP-5 |
| 622 | M9 | P2 | TODO | بعد M6 — TD-03 |
| 623 | M10 | P3 | BLOCKED(D-3) | destructive |
| 624 | M10 | P3 | TODO | |
| 625 | M10 | P3 | TODO | |
| 626 | M10 | P3 | TODO | |
