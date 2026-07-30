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
- **Status**: ✅ DONE (TF-02: S40 · TF-04: S83 — قرار D-2 = tokenization كاملة) · **Priority**: P1
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
- **قرار المالك D-2 وصل (Session 83)**: **tokenization كاملة** — يتجاوز
  توصية الـ baseline-allowlist صراحةً («Complete the full v25 color
  tokenization instead of creating a baseline allowlist»). تكييف القبول:
  بند «سطر دين مؤرَّخ لـ TF-04 في TECHNICAL_DEBT.md» كان خاصًا بمسار
  الـ baseline (الدين = tokenization مؤجَّلة)؛ مع مسار tokenization
  الكامل **لا يوجد دين ليُسجَّل** — الملف TECHNICAL_DEBT.md غير موجود
  في المستودع أصلًا (ls S78) ولن يُنشأ لدينٍ غير قائم. بند «حجم baseline
  يُسجَّل رقمًا» يسقط بالمثل (لا baseline). مسجَّل في DECISION_LOG.
- **Evidence (Session 83) — إحصاء المخالفات والقيود**:
  - المخالفون (نفس regex الحارس `#hex|rgba?(|hsla?(`): **131 سطرًا** —
    static/style.css **127** (138 موضع لونٍ خام، **72 قيمة فريدة**) +
    static/index.html **4** (:95/:96/:99/:100 —
    `stop-color="#8b5cf6"`/`"#06b6d4"` في تدرّجي SVG).
  - لا ملفات أخرى مخالفة تحت static/ أو public/ (grep -rl مطابق للحارس).
  - قيود الحارس (tests/unit/test_theme_tokens.py): tokens.css بنيوية
    فقط بلا ألوان خام (:52)؛ تكافؤ التوكنز الصارم (ناقص **وزائد**) بين
    dark.css و**كل** الثيمات الأربعة light/high-contrast/monokai
    (:59، :203)؛ snapshot حرفي لـ 23 قيمة dark قائمة (:83 —
    الإضافة مسموحة، تغيير القائم ممنوع)؛ style.css يجوز أن يعرّف
    توكنز محلية (:73) لكن بلا ألوان خام؛ WCAG AA يفحص أزواج
    text/bg الأساسية فقط (:225) — التوكنز الجديدة خارج أزواجه.
  - كل ثيم من الأربعة يعرّف 68 توكنًا حاليًا (grep -c S83).
  - 6 من مواضع `#7c6af7` كلها fallbacks ميتة `var(--accent, #7c6af7)`
    (style.css:2965/2966/3022/3023/3039/3048) — `--accent` معرَّف دومًا
    في tokens.css:57 فالـ fallback لا يُقرأ أبدًا؛ حذفه صفر سلوك.
  - بوابة check.sh:102–106 تنص على صيغتي الاستهلاك المسموحتين:
    `var(--token)` أو `color-mix(in srgb, var(--token) N%, transparent)`
    — وcolor-mix مستعملة فعلًا في style.css (2966/3023/3048).
- **Behavior-preservation pre-check — جزء TF-04 (Session 83)**:
  - Current: 138 لونًا خامًا في style.css + 4 في index.html تُصيَّر
    بقيمها الحرفية في **كل** الثيمات (أقسام v25 داكنة الشكل حتى تحت
    الثيم الفاتح — هذا هو السلوك القائم).
  - Expected: **تطابق بصري bit-identical في كل ثيم** — التوكنز الجديدة
    تُعرَّف **بنفس القيم الحرفية في الملفات الأربعة** (لوحة v25 ليست
    theme-aware اليوم؛ جعلها كذلك = قرار تصميم منتج خارج الاستقلالية —
    لا يُتَّخذ هنا). الشفافيات تتحول إلى
    `color-mix(in srgb, var(--x) N%, transparent)` وهي مكافئة حسابيًا
    لـ `rgba(r,g,b,N/100)` في srgb (نفس القناة اللونية بألفا N%).
    fallbacks `var(--accent, #7c6af7)` تُحذف (ميتة). SVG stops تتحول
    من السمة `stop-color="#hex"` إلى `style="stop-color:var(--x)"` —
    نفس الخاصية التقديمية بنفس القيمة عبر CSS بدل السمة.
  - snapshot الـ dark (23 قيمة) لا يُمَسّ — إضافات فقط.
- **Architecture-Fitness pre-check — جزء TF-04 (Session 83)**:
  - مخطط التسمية (يمتد عقد tokens.css الرأسي): مجموعة `--v25-*`
    (لوحة إعادة تصميم v25: slate scale/purples/cyans/greens/danger/
    أسطح داكنة/white/black) + مجموعة `--tango-*` (11 لون GNOME Tango
    لتدرّجات إشعارات الطرفية — تُستهلك بـ 14%/35% فقط). يُضاف السطران
    لعقد التسمية في رأس tokens.css (تعليق بلا ألوان).
  - موضع التعريف: ملفات اللوحات الأربعة (وليس tokens.css — بنيوية
    فقط بأمر الحارس)، بنفس القيم، فيبقى التكافؤ الصارم قائمًا
    (68 → 105 توكنًا لكل ثيم).
  - لا ADR جديد: لا قرار معماري — تطبيق آلي لعقد T-060 القائم على
    بقايا v25؛ سجلات التاسك + DECISION_LOG (قيد قرار المالك D-2) تكفي.
  - المخاطرة الوحيدة: خطأ نقل قيمة → يلتقطه العرض لا الاختبارات؛
    التخفيف: تحويل آلي بجدول قيمة→توكن + مراجعة grep صفرية بعده.
- **Close-out — جزء TF-04 ✅ (Session 83)**:
  - **Implementation**: التحويل الآلي بسكربت التدقيق
    `scripts/_tokenize_v25.py` (مُحتفَظ به للمراجعة؛ pyflakes نظيف):
    (1) 37 توكنًا جديدًا (26 ‎--v25-*‎ + 11 ‎--tango-*‎) أُضيفت **بنفس
    القيم الحرفية** إلى ملفات اللوحات الأربعة dark/light/high-contrast/
    monokai (68 → **105** توكنًا لكل ثيم — التكافؤ الرباعي الصارم قائم)؛
    (2) static/style.css: 6 fallbacks ميتة `var(--accent, #7c6af7)` →
    `var(--accent)`؛ كل rgba() → `color-mix(in srgb, var(--token) N%,
    transparent)` (مكافئ حسابيًا)؛ كل hex → `var(--token)` (الأطول أولًا
    كي لا يبتلع ‎#fff‎ ‎#ffffff‎)؛ (3) static/index.html:95/96/99/100:
    `stop-color="#hex"` → `style="stop-color:var(--v25-purple|
    --v25-cyan-deep)"`؛ (4) عقد التسمية في رأس tokens.css امتد بسطرَي
    ‎--v25-*‎/‎--tango-*‎ (تعليق بلا ألوان). snapshot الـ dark (23 قيمة)
    لم يُمَسّ — إضافات فقط.
  - **Verification (S83)**: مخالفو regex الحارس خارج themes/: 131 → **0**
    (grep -rl مطابق للحارس)؛ test_theme_tokens → **28 passed** كاملًا؛
    **regression كامل: 1900 = 0F/1866P/34S (79.9s) — أول خضرة كاملة
    للبوابة في تاريخ البرنامج (EXIT=0)**؛ `bash scripts/check.sh` →
    **ALL GREEN (exit 0) — لأول مرة** = معيار خروج M6 الأخير تحقق.
  - **Metrics**: إخفاقات البوابة 1 → **0**؛ ألوان خام خارج themes/
    138+4 → **0**؛ توكنز لكل ثيم 68 → 105؛ حجم baseline: لا ينطبق
    (قرار D-2 = tokenization، لا baseline)؛ دين TF-04: **لا شيء يُسجَّل**.
  - **M6 مغلقة 5/5**: 601 ✅ 602 ✅ 603 ✅ 604 ✅ 605 ✅ —
    «check.sh أخضر كاملًا لأول مرة» (MASTER_ROADMAP:114) مُتحقَّق بدليل.

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

### TSK-617 — أمان الافتراضات البرمجية (قرار D-1: قلبهما)
- **Status**: ✅ DONE (S83 — قرار D-1 وصل ضمن التوجيه الشامل:
  «continue with the remaining owner-gated tasks…»؛ التوصية المسجَّلة
  MASTER_REVIEW:810 «نعم — قلبهما، أمان زائد لا كسر» صارت نافذة) ·
  **Priority**: P2
- **Objective**: قلب `enforce` (ASF-04) و`force_command_approval` (NF-16)
  إلى افتراض آمن في الكود لا في config فقط.
- **Acceptance**: حذف المفاتيح من config → السلوك الآمن؛ config الحالي بلا
  تغيير سلوكي.
- **Gates**: Security · Regression · Documentation. · **Rollback**: revert.
- **Evidence (Session 83) — خريطة المواضع**:
  - NF-16: القارئ `server.py:178–195 _force_command_approval` —
    الافتراضي `False` في `.get(..., False)` (:191) **وفي fallback
    الـ except** (:193–195)؛ مواضع التمرير الثلاثة (يفرضها الاختبار
    البنيوي test_force_approval.py:145–161): server.py:1802 +
    routes/run.py:59/:96 — كلها `force_approval=_force_command_approval()`.
    معامل `CommandRunner.run(force_approval=False)`
    (actions/command_runner.py:57) **خارج نطاق القلب**: كل مواضع
    `need_approval=False` الإنتاجية تمرر الراية صراحةً من القارئ
    الموحّد (الحارس البنيوي يفرض ذلك) — قلبه يضاعف البوابة على مسارات
    chain/agent المحكومة أصلًا بـ ApprovalGate (T-013).
  - ASF-04: `chain/agent_tools.py:72` — `enforce: bool = False`
    (افتراضي dataclass)؛ `command_policy_from` يعيد `CommandPolicy()`
    (legacy) عند غياب/فساد قسم agent (:102/:105)؛
    `AgentTools.__init__:176` — `command_policy or CommandPolicy()`.
    موضع الإنشاء الإنتاجي الوحيد: server.py:2100 يمرر السياسة من
    config (:2088) — الافتراضي البرمجي لا يُستهلك إنتاجيًا إلا عند
    config فاسد/غائب.
  - config.yaml الحالي: `force_command_approval: false` صريح (:25) +
    قسم `agent.command_allowlist` موجود (⇒ enforce=True) — فبعد القلب
    **صفر تغيير سلوكي على config الحالي** (بند القبول الثاني).
  - حقن خطوة التحقق (chain/agent_loop.py:418–419) يتطلب enforce
    **وallowlist غير فارغة** معًا ⇒ enforce=True بقائمة فارغة لا يحقن.
- **Behavior-preservation pre-check (S83)**:
  - Current: حذف `force_command_approval` من config ⇒ لا إلزام موافقة؛
    حذف `agent.command_allowlist` ⇒ legacy (تنفيذ أي أمر بموافقة
    ApprovalGate فقط)؛ config غير مقروء ⇒ لا إلزام.
  - Expected (التغيير المقصود بقرار D-1 — يمس حالة «المفتاح غائب» فقط):
    غياب المفتاح/فشل القراءة ⇒ `force_command_approval=True`؛ غياب/فساد
    قسم allowlist ⇒ `enforce=True` بقائمة فارغة = **رفض كل أوامر
    الـ agent برسالة مهيكلة** تسمّي `agent.command_allowlist` (نمط
    fail-closed كسابقة TSK-603). **القيم الصريحة في config تُحترم كما
    هي** (`false` صريح = تعطيل واعٍ) — config الحالي بلا تغيير.
  - اختبارات تفترض الافتراضي القديم تُحدَّث معلنةً القلب (وليس كسرًا):
    test_force_approval::test_flag_absent_defaults_false (:86–89)
    وtest_default_api_run_not_gated (:126–133)؛
    test_run_command::test_legacy_mode_no_enforcement (:120–126)
    وtest_missing_section_means_legacy (:149–152)
    وtest_garbage_types_tolerated (:154–157).
    test_agent_feedback:202–211 (غياب الحقن بلا سياسة) يبقى أخضر
    (قائمة فارغة ⇒ لا حقن — بدليل agent_loop.py:419).
- **Architecture-Fitness pre-check (S83)**:
  - القلب في **نقطتي المصدر** فقط (القارئ الموحّد + مصنع السياسة) لا
    في المستهلكين — المستهلكون يبقون أغبياء؛ الحارس البنيوي القائم
    يستمر يفرض التمرير.
  - fallback الـ except في القارئ يُقلب إلى True (config غير مقروء =
    أخطر الحالات — fail-closed)، مع إبقاء وسم NF-14 §2 محدثًا.
  - التوثيق: تعليقا config.yaml (NF-16 + agent) + قسم «حدود النشر»
    في README إن ذكر الافتراضي القديم؛ docstrings المواضع الثلاثة.
  - لا ADR: تنفيذ قرار مالك مسجَّل (D-1) بلا بدائل معمارية — قيد
    DECISION_LOG S83 (التوجيه الشامل) يغطيه، وسجل التاسك هذا هو الأثر.
- **Close-out ✅ (Session 83)**:
  - **Implementation**: (1) NF-16 — `server.py:_force_command_approval`:
    الافتراضي `.get(..., True)` + fallback الـ except → True
    (fail-closed؛ وسم NF-14 §2 محدَّث)؛ docstring يوثّق القلب.
    (2) ASF-04 — `chain/agent_tools.py:command_policy_from`: مسارا
    غياب/فساد القسم يعيدان `CommandPolicy(enforce=True, allowlist={})`
    (رفض الكل برسالة مهيكلة قائمة) بدل `CommandPolicy()` (legacy)؛
    افتراضي الـ dataclass و`AgentTools.__init__` بقيا legacy للبناء
    المباشر (اختبارات) — موثَّق في docstring الصنف.
    (3) التوثيق: config.yaml (تعليقا NF-16 + agent) + README
    (:422 + قسم حدود النشر بند 4). (4) اختبارات الافتراضي القديم
    حُدّثت معلنةً القلب: test_force_approval (flag_absent→True +
    flag_absent_api_run_gated + explicit_false_not_gated جديد)؛
    test_run_command (missing_section/garbage_types → fail_closed).
  - **Verification (S83)**: الملفات المتأثرة الخمسة → خضراء كاملة؛
    regression كامل: 1F/1866P/34S — الفشل الوحيد test_search_perf
    العابر الموثَّق بيئيًا (معزولًا: 18 passed — نفس إجراء S79)؛
    القبول مُثبَت تنفيذيًا (حذف المفاتيح ⇒ True/enforce؛ config
    الحالي ⇒ false صريح مُحترم + enforce=True بـ 4 مداخل كما قبل)؛
    pyflakes delta صفر (stash-diff)؛ mypy Success 81 ملفًا.
  - **Metrics**: الافتراضات config-dependent الخطرة 2 → **0**؛
    ASF-04 + NF-16 مغلقان بقرار D-1.

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
- **Status**: ✅ DONE (S74) · **Priority**: P2
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
- **Evidence (S74)**:
  - **showPlanCard** `static/app.js:3122–3150`: يضبط
    `state.planActions = actions` (:3123)؛ يبني `.plan-card` وصفوف
    `<div class="task-item pending"><span class="task-icon">⬜</span>
    ${icon} ${escapeHtml(label)}</div>` (:3129–3133؛ icon حسب
    a.action: create_file 📄 / edit_file ✏️ / غيره ⚡؛ label =
    a.path || a.command)؛ `.plan-controls` بأربعة أزرار onclick:
    executePlan(this) / revisePlan() / reviewPlan() / cancelPlan(this)
    (:3140–3145). يُستدعى من محوّل WS الوحيد case "plan" (:222).
  - **executePlan** `:3152–3162`: حارس `if (!state.planActions.length)
    return;` (:3153) → استبدال controls بمؤشر تنفيذ →
    `state.ws.send(JSON.stringify({type: "execute_plan",
    actions: state.planActions}))` (:3158–3161). **شكل الـ payload
    الحالي**: `{type, actions}` — قائمة actions كما وصلت من إطار plan.
  - **cancelPlan** `:3176–3182`: يصفّر `state.planActions = []`؛
    `state.planActions` مُهيأ `[]` عند `:18`.
  - **الخادم لا يتغير**: `server.py:1651` — `"execute_plan":
    _ws_apply_batch`؛ `_apply_batch` (:1712) يمر على القائمة المرسلة
    كما هي (أُطره golden-locked في apply_batch_frames.json) — subset
    من نفس البنية شفاف تمامًا له.
  - **CSS قائم — لا ألوان خام جديدة مطلوبة**: `.plan-card` (:1558)،
    `.plan-header` (:1566)، `.plan-content` (:1576)، `.plan-controls`
    (+أزرارها :1582–1638)، `.task-item` وحالاتها (:1676–1700) —
    كلها في style.css بالفعل؛ checkbox عنصر HTML أصلي.
  - **نمط اختبار node قائم كسابقة**: `tests/unit/test_diff_panel.py`
    (run_node subprocess + `pytestmark skipif(node is None)` +
    ROOT=parents[2]، cwd=ROOT) و`tests/unit/test_stream_render.py`
    (فحوص wiring نصية: app.js يستهلك الوحدة + index.html يحمّلها قبل
    app.js :182–194؛ **سيناريو يدوي موثَّق في docstring كـ Accept
    رسمي** :205–209 — سابقة لبند «سيناريو يدوي موثق» هنا).
    node v22.23.1 متوفر.
  - **نمط UMD-lite قائم**: `static/js/status_chip.js` — `(function
    (global) { "use strict"; ... createState() ... })` منطق نقي،
    الـ DOM glue في app.js فقط؛ 8 وحدات في index.html (:45–69)
    كلها `?v=1` قبل app.js.
- **Behavior-preservation pre-check (S74 — قبل التعديل)**:
  1. **الافتراضي (لا لمس) = السلوك القديم حرفيًا**: كل الخطوات تبدأ
     مفعّلة؛ `enabledActions(state)` على حالة كاملة التفعيل تعيد
     نفس القائمة بنفس الترتيب ⇒ payload التنفيذ مطابق بايتًا لِما
     يُرسل اليوم (`{type:"execute_plan", actions:[...كلها...]}`).
  2. **server.py لا يُمس**: subset من نفس بنية العناصر — _apply_batch
     يمر على ما وصله؛ الأُطر الذهبية لا تتأثر.
  3. أزرار revisePlan/reviewPlan/cancelPlan ومساراتها بلا تغيير؛
     cancelPlan يظل يصفّر planActions.
  4. توقيع showPlanCard(actions, summary) ونقطة الاستدعاء (:222)
     بلا تغيير؛ لا endpoints ولا أطر WS جديدة.
  5. التحقق: اختبار node «كل-الخطوات-مفعلة → payload مطابق للقائمة
     الكاملة» (بند Gates حرفيًا) + الانحدار الكامل (خط 1850).
- **Architecture-Fitness pre-check (S74)**:
  - وحدة نقية جديدة `static/js/plan_card.js` (منطق الحالة:
    actions + أعلام enabled؛ toggle؛ enabledActions ⇒ subset) —
    قابلة للاختبار في node بلا متصفح؛ الـ DOM glue (رسم checkboxes
    وربط الأحداث وقراءة subset عند الإرسال) في app.js فقط —
    نفس نمط المنزل الثابت (status_chip/diff_panel/stream_render).
  - لا تبعيات جديدة؛ script tag واحد `?v=1` قبل app.js في
    index.html؛ لا لمس لـ providers/ (§0.8) ولا server.py.
- **Close-out (S74)**:
  - **التنفيذ**: وحدة نقية جديدة `static/js/plan_card.js` (UMD-lite،
    نمط status_chip): createState (كل الخطوات مفعّلة افتراضيًا) /
    toggle / setEnabled / isEnabled / enabledActions (subset بترتيبه
    الأصلي) / enabledCount. `static/app.js`: showPlanCard يرسم
    checkbox لكل خطوة (`plan-step-toggle` مع data-step، checked
    افتراضيًا) ويربط change بالحالة النقية (DOM glue فقط)؛
    executePlan يرسل `PlanCard.enabledActions(...)` بدل القائمة
    الكاملة، مع منع الإرسال + toast تحذيري عند صفر مفعّل؛
    cancelPlan يصفّر planCardState. `static/index.html`: script tag
    `plan_card.js?v=1` قبل app.js. `static/style.css`:
    .plan-step-label/.plan-step-toggle/.plan-step-disabled —
    tokens فقط (var(--accent)/var(--text-muted)) — TF-04.
    **server.py بلا لمس** (subset شفاف لـ _apply_batch).
  - **الاختبارات**: `tests/unit/test_plan_card.py` (10، نمط node):
    **القبول حرفيًا** — تعطيل خطوة → enabledActions بدونها وبقية
    الترتيب محفوظ؛ **بوابة حفظ السلوك حرفيًا** — كل-الخطوات-مفعلة
    → مطابق بايتًا (JSON.stringify) للقائمة الأصلية؛ toggle/حدود
    النطاق/صفر مفعّل/مدخلات فارغة وnull؛ wiring (app.js يستهلك
    createState/setEnabled/enabledActions + index.html يحمّل الوحدة
    قبل app.js)؛ **السيناريو اليدوي موثَّق في docstring** (خطوات
    DevTools → WS Messages → التحقق من actions المرسلة) — نفس سابقة
    test_stream_render كـ Accept رسمي.
  - **البوابات**: node --check نظيف · pyflakes نظيف (تحذيرات
    agent_loop الأربعة سابقة الوجود) · lint_handler_state نظيف ·
    mypy Success 81 ملفًا · contracts+parity 113 ✓ · goldens+ws_router
    32 ✓ · الانحدار الكامل **1860 = 2F/1824P/34S** (1850+10؛
    theme_tokens/TF-04/D-2 المعروف + test_search_perf flaky —
    يمر معزولًا ×2، سبق توثيقه S73؛ لا علاقة للتغيير بمساره).
  - **خط انحدار جديد: 1860**.

### TSK-620 — سرد الجلسة (CP-8)
- **Status**: ✅ DONE (S75) · **Priority**: P2 · **Dependencies**: TSK-610 (سجل runs).
- **Objective**: عرض timeline يجمع (طلب → خطة → موافقات → تنفيذ → نتائج)
  فوق RunHistory القائمة — محليًا، بلا cloud (Non-Goal §15.2).
- **Background**: UXF-05 + CP-8 ADOPT (§R9).
- **Acceptance**: جلسة بها run واحد معتمد → السرد يعرض ≥ 4 محطات بترتيبها؛
  وحدة نقية مختبرة node.
- **Gates**: Testing · Documentation. · **Rollback**: revert.
- **Evidence (S75)**:
  - **مصدر المحطات = أطر WS الحية عبر المعالج الوحيد**:
    `handleWSMessage` (app.js:192) — **سابقة الاستهلاك-فقط قائمة**:
    `StatusChip.noteFrame(statusChipState, data)` (:195) يلتقط من
    الإطارات دون تغيير مسار أيٍّ منها. الأطر الحاملة للمحطات:
    «طلب» — `sendMessage` (:836، يرسل message/chain_message)؛
    «خطة» — case "plan" (:220)؛ «موافقات» — chain_approval_request
    (:430) / chain_approval_verdict (:434، يحمل approved/reason) +
    respondAgentApproval (:795، agent_approval_response)؛
    «تنفيذ» — task_progress (:241) / chain_step (:325) /
    agent_step (:504)؛ «نتائج» — all_actions_done (:245) /
    done (:215) / chain_finished (:365) / agent_done (:583) /
    error (:226) + «استعادة» rollback_result (:443).
  - **سجل runs (التبعية TSK-610)**: core/run_metrics.py — JSONL
    ملحق-فقط `{ts, run_id, mode, status, duration_ms, ...}` + REST
    قراءة `/api/metrics/runs` (routes/meta.py:50) — **مقاييس مجمّعة
    بلا تفصيل محطات لكل جلسة** ⇒ السرد يُشتق من الأطر الحية
    في الذاكرة (محلي، لا cloud — Non-Goal §15.2)؛ سجل runs يبقى
    مصدر p50/p95 لا السرد.
  - **موضع العرض «فوق RunHistory القائمة»**: لوحة
    `#run-history-panel` (index.html:464–472: head/report/list)؛
    الغراء القائم: toggleRunHistory (app.js:3445 — fetch
    /api/rollback/history ثم renderRunHistory :3463)؛ الوحدة
    النقية run_history.js تبني/ترسم القائمة. قسم سرد جديد يُحقن
    قبل القائمة داخل نفس اللوحة.
  - **أنماط قائمة**: UMD-lite (status_chip.js — createState +
    noteFrame + render نقي) + اختبار node
    (test_plan_card/test_stream_render — run_node + wiring +
    سيناريو يدوي موثَّق كـ Accept). node v22.23.1.
- **Behavior-preservation pre-check (S75 — قبل التعديل)**:
  1. الالتقاط استهلاك-فقط في handleWSMessage (نفس عقد StatusChip
     :193–195 حرفيًا): لا إطار يُعدَّل ولا مسار case يتغير.
  2. RunHistory القائمة (بيانات/أزرار/استعادة) بلا أي تغيير —
     السرد قسم عرض جديد داخل اللوحة لا يلمس list/report.
  3. لا endpoints جديدة ولا أطر WS جديدة ولا server.py؛
     sendMessage يضيف نداء التقاط واحدًا لا يغيّر الإرسال.
  4. سقف مدخلات في الذاكرة (أقدم-يُطرد) — جلسة طويلة لا تراكم
     ذاكرة بلا حد (نفس مبدأ MAX_PENDING في run_metrics).
  5. التحقق: regression كامل (خط 1860) + wiring tests.
- **Architecture-Fitness pre-check (S75)**:
  - وحدة نقية جديدة `static/js/session_narrative.js` (حالة +
    noteFrame تصنيفي + entries + renderTimelineHTML نقي) —
    قابلة للاختبار في node؛ الـ DOM glue (نداء الالتقاط + حقن
    القسم عند فتح اللوحة) في app.js فقط — نفس نمط المنزل
    (status_chip/plan_card).
  - لا تبعيات جديدة؛ script tag واحد `?v=1` قبل app.js؛
    لا لمس لـ providers/ (§0.8).
- **Close-out (S75)**:
  - **التنفيذ**: وحدة نقية جديدة `static/js/session_narrative.js`
    (UMD-lite): createState / noteRequest (محطة الطلب من الغراء) /
    noteFrame (تصنيف استهلاك-فقط: plan / approval طلب+حكم /
    execution بدمج المتتالية بعدّاد / result / rollback؛ غير
    المعروف → false) / entries / renderTimelineHTML نقي (الأقدم
    أولًا، تهريب HTML، sn-bad للرفض/الخطأ)؛ سقف MAX_ENTRIES=200
    أقدم-يُطرد. `static/app.js`: التقاط في handleWSMessage بجوار
    StatusChip.noteFrame (نفس العقد) + noteRequest في sendMessage
    (يغطي فرعَي message/chain_message) + renderSessionNarrative
    يحقن قسم `#session-narrative` قبل القائمة داخل
    `#run-history-panel` عند الفتح — القائمة/التقرير بلا لمس.
    `static/index.html`: script tag `?v=1` قبل app.js.
    `static/style.css`: أصناف #session-narrative/.sn-* — tokens
    فقط (إصلاح أثناء البوابات: var(--border) غير معرّف — كشفه
    TestTokenParity — استُبدل بـ var(--surface-0) نمط المنزل).
    لا endpoints ولا أطر WS جديدة؛ server.py بلا لمس.
  - **الاختبارات**: `tests/unit/test_session_narrative.py` (10، نمط
    node): **القبول حرفيًا** — run معتمد واحد → 5 محطات بترتيبها
    (request→plan→approval→execution→result) في الحالة والـ HTML
    المرسوم؛ تجاهل الأطر غير المعروفة؛ الرفض/الخطأ sn-bad؛
    rollback؛ دمج التنفيذ المتتالي ×5 + كسر الدمج بعد نتيجة؛
    سقف أقدم-يُطرد؛ حالة فارغة + تهريب HTML؛ wiring (app.js
    يستهلك noteFrame/noteRequest/renderTimelineHTML + index.html
    يحمّل الوحدة قبل app.js)؛ **السيناريو اليدوي موثَّق في
    docstring** (بوابة Documentation — نفس سابقة test_plan_card).
  - **البوابات**: node --check نظيف · lint_handler_state نظيف ·
    mypy Success 81 ملفًا · contracts+parity 113 ✓ · goldens+ws_router
    32 ✓ · الانحدار الكامل **1870 = 1F/1835P/34S** (1860+10؛
    theme_tokens/TF-04/D-2 حصرًا — وفي تمريرة وسيطة كشف
    TestTokenParity توكن --border غير المعرّف فأُصلح فورًا؛
    search_perf مرّ في التمريرة النهائية).
  - **خط انحدار جديد: 1870**.

### TSK-621 — Permissions UI قراءة (CP-5)
- **Status**: ✅ DONE (S76) · **Priority**: P2
- **Objective**: لوحة قراءة تعرض سياسة الأمان الفعالة (allowlist،
  SAFE/DANGEROUS، force_approval) من config عبر REST قراءة — glass box.
- **Background**: UXF-04 + CP-5 (§R9). · **Acceptance**: endpoint قراءة +
  لوحة تعرض القيم الحية؛ لا مسار كتابة.
- **Gates**: Security (قراءة فقط) · Testing. · **Rollback**: revert.
- **Evidence (S76)** — مصادر السياسة الفعالة بأرقام أسطر:
  - **allowlist أوامر الـ agent**: config.yaml:58 `command_allowlist:`
    {test/lint/typecheck/build} + `command_timeout_seconds: 60` +
    `command_output_max_chars: 8000`؛ التوثيق :33–56 (القائمة طبقة
    إضافية فوق ApprovalGate؛ حذف القسم = وضع legacy).
    القارئ: `command_policy_from(cfg)` (chain/agent_tools.py:92) →
    `CommandPolicy` dataclass (:59 — enforce/allowlist/timeout/
    output_max_chars؛ قسم غائب/غير dict ⇒ enforce=False legacy).
  - **أدوات الـ agent**: chain/agent_tools.py:37 `SAFE_TOOLS`
    {read_file, list_dir, search_code, get_file_info,
    get_project_tree, remember_fact}؛ :39 `APPROVAL_TOOLS`
    {run_command}.
  - **أوامر الطرفية**: actions/command_runner.py:29 `SAFE_COMMANDS`
    (ls/cat/echo/pwd/node/python/git status…)؛ :37
    `DANGEROUS_COMMANDS` {rm, rmdir, del, format, drop, delete,
    truncate, sudo, chmod, chown}.
  - **راية force_approval**: server.py:178 `_force_command_approval()`
    — تقرأ `force_command_approval` من config.yaml (افتراضي False،
    تطبيع bool تسامحي، ابتلاع NF-14 §2 موثَّق)؛ الاستهلاك :1798
    (apply-actions run_command).
  - **بوابة الموافقة**: server.py:1937 `ApprovalGate(mode="auto" if
    _auto_execute else "interactive", auto_whitelist={"write","edit",
    "command"} if _auto_execute else None, timeout_seconds=120.0)` —
    global `approval_gate` (:694، None قبل الإقلاع)؛ core/approval.py:54
    `DEFAULT_AUTO_WHITELIST = frozenset({"read","format"})`؛ :151
    ApprovalGate (VALID_MODES auto|interactive|deny).
  - **نمط endpoint القراءة (ADR-003)**: routes/meta.py — `bp =
    Blueprint("meta")` + `_srv: Any = None` + `register(app, srv)`
    حقن كائن الوحدة (late binding)؛ endpoints قراءة قائمة: /api/info،
    /api/capacity (:40 — نمط 503 قبل التهيئة)، /api/metrics/runs (:50)؛
    التسجيل في server.py:928–943 (حلقة `_routes_mod.register`).
  - **نمط اختبار endpoint**: tests/unit/test_run_metrics.py:188–204
    (`server.app.test_client()` + monkeypatch على global).
  - **نمط اللوحات**: index.html:464–465 زران وكيلان مخفيان
    (#run-history-btn/#memory-panel-btn) + Activity Bar يفوّض بـ
    .click() (:219–236)؛ لوحات #run-history-panel (:468 —
    head/report/list) و#memory-panel (:479)؛ الغراء: toggleMemoryPanel
    (app.js:3571 — toggle hidden + جلب + placeholder ⏳) وربط الأزرار
    في DOMContentLoaded (:3711–3712). وحدات UMD-lite نقية + node tests
    (test_plan_card/test_session_narrative). node v22.23.1.
- **Behavior-preservation pre-check (S76 — قبل التعديل)**:
  1. **قراءة فقط**: endpoint جديد GET بلا أي مسار كتابة — لا يعدّل
     config ولا globals؛ يقرأ `_load_config()` المُكاش +
     `command_policy_from` + الثوابت المستوردة + حالة `approval_gate`
     الحية. السياسة المطبَّقة نفسها (الحرّاس/البوابة/القوائم) لا تُمس.
  2. **لا لمس لأي endpoint أو WS frame قائم**؛ server.py لا يُعدَّل
     إلا إن لزم سطر تسجيل blueprint (لا — endpoint يُضاف في
     routes/meta.py المسجَّل أصلًا ⇒ صفر تعديل على server.py).
  3. اللوحة عرض-فقط (لا أزرار تعديل)؛ زر وكيل + قسم لوحة جديدان في
     index.html لا يغيّران أي عنصر قائم.
  4. التحقق: regression كامل (خط 1870) + بوابات العقود/goldens.
- **Architecture-Fitness pre-check (S76)**:
  - endpoint في routes/meta.py القائم (blueprint ADR-003 — لا blueprint
    جديد لطلب قراءة واحد؛ meta هو موضع «معلومات الخادم» الطبيعي).
  - وحدة نقية جديدة `static/js/permissions_panel.js` (renderHTML نقي
    من JSON السياسة — قابلة للاختبار node)؛ DOM glue (fetch + toggle)
    في app.js فقط — نفس نمط المنزل (memory_panel/run_history).
  - CSS tokens فقط (فواصل اللوحات = var(--surface-0) — درس TSK-620:
    --border غير معرّف)؛ script tag واحد `?v=1` قبل app.js؛
    لا تبعيات جديدة؛ لا لمس لـ providers/ (§0.8).
- **Close-out (S76)**:
  - **التنفيذ**: endpoint قراءة جديد `GET /api/permissions`
    (routes/meta.py — blueprint meta القائم، ADR-003؛ server.py صفر
    تعديل): يعيد القيم الحية — command_allowlist عبر
    `command_policy_from(_srv._load_config())` (enforce/entries/
    timeout/output_max_chars)، SAFE/APPROVAL tools، SAFE/DANGEROUS
    commands، `_srv._force_command_approval()`، وحالة `approval_gate`
    الحية (mode/auto_whitelist/timeout — null قبل الإقلاع، لا اختراع).
    وحدة نقية جديدة `static/js/permissions_panel.js` (UMD-lite):
    renderPanelHTML نقي يرسم الأقسام الأربعة من JSON — تهريب HTML،
    UNKNOWN صريح عند الغياب، **صفر أدوات كتابة** (لا button/input).
    الغراء في app.js فقط: `togglePermissionsPanel` (fetch GET + render)
    + ربط زر وكيل في DOMContentLoaded. index.html: script tag `?v=1`
    قبل app.js + زر Activity Bar 🔒 (يفوّض بـ .click() — نمط TF-03) +
    زر وكيل مخفي + لوحة #permissions-panel (نمط memory-panel).
    style.css: أصناف pp-* — tokens فقط (فواصل var(--surface-0)).
  - **توسيع عقد مقصود**: سطح REST المجمّد 30→31 قاعدة
    (tests/unit/test_rest_blueprints.py — FROZEN_RULES +
    `/api/permissions GET` بتعليق مؤرَّخ) — القبول ينص حرفيًا على
    «endpoint قراءة» (قرار المرحلة 2، ليس انحرافًا).
  - **الاختبارات**: `tests/unit/test_permissions_panel.py` (12):
    **القبول حرفيًا** — endpoint يعيد القيم الحية من config والكود
    (مطابقة مع الثوابت الحقيقية لا نسخ)؛ **لا مسار كتابة** —
    POST/PUT/DELETE ⇒ 405 + النداء لا يغيّر السياسة (نفس الكائنات
    قبل/بعد)؛ حالة البوابة الحية تنعكس (monkeypatch)؛ null قبل
    الإقلاع؛ وحدة node (5): الأقسام الأربعة بالقيم الواردة + تهريب
    HTML + غياب صريح + legacy/فارغ + صفر أدوات كتابة في HTML؛
    wiring (2): app.js يستهلك fetch+render بلا إرسال كتابة +
    index.html يحمّل الوحدة قبل app.js. سيناريو يدوي موثَّق في
    docstring (Accept الرسمي — نفس السابقة).
  - **البوابات (S76)**: node --check نظيف؛ pyflakes نظيف؛
    lint_handler_state نظيف؛ mypy Success 81 ملفًا؛ العقود+parity
    113 ✓؛ goldens+ws_router 32 ✓؛ regression كامل:
    **1882 = 1F/1847P/34S (~80s)** — الإخفاق الوحيد theme_tokens
    (TF-04/D-2 المعروف). **خط الانحدار الجديد: 1882**.
  - **Security gate (قراءة فقط)**: GET وحيد بلا آثار جانبية؛ لا
    كشف أسرار (لا مفاتيح/tokens في الاستجابة — سياسة أوامر وأدوات
    فقط)؛ localhost-فقط كسائر الخادم (حدود النشر في README قائمة).
  - **Rollback**: revert (commits معزولة).

### TSK-622 — إعادة تصويت RELEASE_READINESS (ينتظر إغلاق M6)
- **Status**: ✅ DONE (S83) · **Priority**: P2 · **Dependencies**: M6 كاملًا (601–605) ✅ (S83).
- **Objective**: إعادة تقييم G1–G5 على الكود الحالي (TD-03) بمدخلات ما بعد
  التنفيذ + RP-01/TF-03 المصلحة؛ تحديث RRR بقسم re-vote مؤرَّخ (append).
- **Acceptance**: قسم جديد في RRR بحكم لكل بوابة بدليل حي؛ لا حذف للنص القديم.
- **Gates**: Documentation. · **Rollback**: revert.
- **Evidence (S83) — خريطة رافعات البوابات، كل استشهاد مُتحقق حيًّا**:
  - **G1** (كان CONDITIONAL FAIL على BUG-01): parser أصبح mode-aware —
    `actions/response_parser.py:107` `def parse(self, response, mode=None)`
    (TSK-201→101→102، QA-T05)؛ RP-01 (اعتماد التفويض المكسور) أُصلح TSK-601؛
    TF-03 أُصلح TSK-604.
  - **G2** (كان CONDITIONAL FAIL على NF-15/NF-18): Zip-Slip —
    `server.py:753` `_zip_member_violations` (TSK-105، MASTER_REVIEW:304
    VERIFIED-FIXED)؛ التسييج — `fence_attached` يُستدعى الآن في مسار الحلقة
    والمعرفة أيضًا: `chain/agent_loop.py:230/:274`،
    `chain/knowledge.py:54/:204/:207` (TSK-404 + TSK-602/ASF-01)؛ البوابة
    البنيوية ASF-02 → TSK-603 (`chain/agent_tools.py:535` صحيح بالبناء)؛
    D-1/TSK-617: `server.py:195` غياب المفتاح ⇒ True و`agent_tools.py:68/:100`
    غياب القسم ⇒ enforce=True (fail-closed code-defaults).
  - **G3** (كان CONDITIONAL FAIL على BUG-03/NF-06/07/01/04): ميزانية موحّدة —
    `context/facade.py:113` `gather_message_context` (TSK-103) + TSK-607 ضم
    جيب delegate الأخير (RP-03)؛ NF-06 — `core/execution.py:351`
    `purge_terminal` + نداء `server.py:434` (MASTER_REVIEW:367)؛ NF-07 —
    `select_history` بسياسة مسماة `server.py:46/:1004` (MASTER_REVIEW:368)؛
    NF-01 — داخل القفل (MASTER_REVIEW:362 VERIFIED-FIXED)؛ NF-04 — الإلغاء
    FIXED (TSK-304) والحجب حُلّ بالتخييط TSK-606 ✅ (S43، RF-01).
  - **G4** (كان FAIL non-blocking على g1/NF-23/BUG-04/NF-14): server.py الآن
    2141 سطرًا (كان 2613) بعد M8 (TSK-611–613: راوتر WS + dispatch +
    blueprints routes/ 8 ملفات) + TSK-614 mypy Success 81 ملفًا؛ NF-23.1–.4
    VERIFIED-FIXED (MASTER_REVIEW:506–509)؛ BUG-04 مُغلق
    (`core/ignore_rules.py`، MASTER_REVIEW:194)؛ NF-14 جزئي منضبط بنمط
    "ابتلاع مقصود §N" الموثّق + TSK-618 ضيّق path_policy.
  - **G5** (كان PASS): تعزّز — خط الانحدار 1900 اختبارًا =
    0F/1866P/34S (S83، أول 0-failed) + `check.sh` ALL GREEN exit 0 أول مرة
    (M6 مغلقة 5/5).
- **Behavior-preservation pre-check**: المهمة توثيقية بحتة — لا يُلمس أي ملف
  كود؛ التعديل الوحيد إلحاق قسم في RRR (append-only) وسجلّات الإغلاق. صفر
  تأثير سلوكي بالبناء.
- **Architecture-Fitness pre-check**: لا بنية كود متأثرة؛ يحترم قاعدة RRR
  "Status fields live ONLY in PROGRESS.md" — القسم الجديد حُكم/دليل لا حالة
  مهام؛ §0.8 (providers/ مستثنى) يبقى ساريًا في إعادة التقييم.
- **Close-out (S83)**: قسم §5 "Re-vote — Session 83" أُلحق بـ RRR
  (112→197 سطرًا؛ append فقط — §1–§4 محفوظة حرفيًا). الأحكام: G1 ✅ PASS
  (BUG-01 mode-aware + RP-01/TF-03 مصلحة)، G2 ✅ PASS (NF-15/NF-18 على
  المسارين + ASF-01/02 + D-1 fail-closed؛ متبقٍّ موثَّق: localhost-only)،
  G3 ✅ PASS (BUG-03/NF-06/07/01/04 كلها مرفوعة حيًّا)، G4 ✅ PASS
  (server.py 2141 بعد M8 + mypy 81 ملفًا)، G5 ✅ PASS معزَّز
  (1900 = 0F/1866P/34S + check.sh ALL GREEN). الحكم الإجمالي:
  **GO ضمن عقد localhost أحادي-المستخدم الموثَّق** (كان NO-GO). Gates:
  Documentation — لا كود مُس؛ لا اختبار مطلوب. TD-03 وD-4 مغلقان.
  **M9 مغلقة كاملة** (615–622 كلها ✅).

## M10 — Hygiene (P3)

### TSK-623 — أرشفة improvements/ (D-3 وصل S83) — P3
حذف/نقل من الشجرة = عملية destructive → كانت تنتظر موافقة D-3. Acceptance:
grep/wc نظيفة من 892KB التلوث؛ المحتوى محفوظ في أرشيف.
- **Status**: ✅ DONE (S83) · **Priority**: P3 · **Dependencies**: قرار D-3 ✅ وصل S83
  (توجيه المالك الشامل + توصية MASTER_REVIEW:811 "نقل إلى أرشيف خارج جذر
  الفحص"؛ العملية الـ destructive معتمدة بهذا التوجيه).
- **Evidence (S83) — جرد ما قبل النقل**:
  - `du -sh improvements/` = **892K** · `find -type f | wc -l` = **40** ملفًا
    · `git ls-files improvements/ | wc -l` = **40** (كلها متتبعة — لا ملفات
    غير متتبعة تضيع).
  - أكبر الملوثات: `improvements/شامل/جديد/server.py` (1670 سطرًا) +
    `improvements/شامل/قديم/server.py` (1100 سطرًا) — نسخ server.py تاريخية
    (QF-01، MASTER_REVIEW:551).
  - **صفر مراجع حية**: grep عبر `*.py/*.sh/*.js/*.html/*.yaml/*.ini/*.cfg`
    (باستثناء improvements/ نفسها و.git) = لا نتائج؛ لا ذكر في pytest.ini
    ولا scripts/check.sh ولا core/ignore_rules.py.
  - وجهة الأرشيف: `test---results/` — منطقة الأرشيف القائمة المستثناة
    أصلًا من كل مسارات المسح عبر `IGNORED_DIRS` الموحّدة
    (`core/ignore_rules.py`، TSK-202/BUG-04).
  - صيغة الأرشيف: **tar.gz واحد** داخل `test---results/` — يحقق «grep/wc
    نظيفة» حرفيًا (ملف ثنائي واحد لا يطابقه grep نصيًا ولا يلوث wc) مع
    حفظ المحتوى كاملًا. `.gitignore` يستثني `*.tar.gz` ⇒ يلزم سطر استثناء
    `!` ليبقى الأرشيف متتبعًا في المستودع (وإلا ضاع المحتوى عن remote).
- **Behavior-preservation pre-check**: لا كود منتج يُمس — المجلد ورقة ميتة
  (صفر imports إليها، ثابت أعلاه). سلوك التطبيق متطابق بالبناء. حارس
  السلامة: `tar -tzf` يُعدّ 40 ملفًا قبل أي `git rm`؛ الحذف يقع فقط بعد
  التحقق من سلامة الأرشيف.
- **Architecture-Fitness pre-check**: يحقق QF-01 (إزالة التلوث من جذر
  الفحص) دون توسيع IGNORED_DIRS ولا لمس أي وحدة كود؛ الوجهة منطقة أرشيف
  قائمة لا مجلد جديد في الجذر؛ تعديل .gitignore سطر استثناء واحد موثَّق.
- **Rollback**: `tar -xzf` يستعيد الشجرة كاملة، أو revert للكوميت.
- **Close-out (S83)**: الأرشيف
  `test---results/improvements_archive_2026-07-29.tar.gz` (176KB مضغوطًا،
  40 ملفًا) أُنشئ وتُحُقّق منه **قبل** الحذف: `tar -tzf` = 40 ملفًا +
  فكّ لـ /tmp و`diff -r` مقابل الأصل = **متطابق بايتًا**. ثم
  `git rm -r improvements/` (40 حذفًا) + سطر استثناء `!` في .gitignore
  ليبقى الأرشيف متتبعًا (لأن `*.tar.gz` متجاهَل عمومًا). Acceptance
  محقّق: `ls improvements` غير موجود؛ `git ls-files | grep ^improvements/`
  = 0؛ حجم الشجرة (بلا .git) = 16MB نظيفة من التلوث؛ المحتوى محفوظ.
  بوابة ما بعد النقل: `check.sh` **ALL GREEN exit 0** — خط الانحدار
  الجديد **1901 = 0F/1867P/34S** (+1 اختبار من TSK-617؛ test_search_perf
  العابر مرّ هذه المرة). QF-01 وD-3 مغلقان؛ **M10 مغلقة كاملة**
  (623–626 كلها ✅) ⇒ استحقاق IR-2.
### TSK-624 — retro-ADR لإعادة تصميم v25 — P3, ✅ DONE (S78)
توثيق قرار v25 (TD-04) في ADR + Decision Log. Acceptance: ملف ADR يشرح
النطاق والأثر والحرّاس المكسورة وكيف أُصلحت.
- **Evidence (S78)**:
  - **الدين**: TD-04 — MASTER_REVIEW.md:679 («لا توثيق لإعادة تصميم v25
    في أي وثيقة هندسية: التغيير لمس index.html/style.css/sprite وكسر
    3 بوابات حارسة بلا سجل قرار أو تحديث للاختبارات») + :730 (خريطة
    TD-04 → P3 → TSK-624).
  - **نطاق v25 من git** (تحقق S78):
    - `0d74dad` (2026-07-27) — نواة إعادة التصميم: index.html
      +638/−…، style.css +819، sprite.svg 441 سطرًا معاد كتابته،
      app.js +420 (إجمالي static/: 1877 insertions / 441 deletions).
    - `2ed794f` (2026-07-28) — index.html +4 (متابعة v25).
    - `8235147` (2026-07-28) — index.html +4، app.js +18 (ws_backoff
      wiring ضمن نفس الموجة).
    - `454f7ac` — تحديث sprite.svg لاحق ضمن نفس الخط.
    - الوسوم الحية الآن: `?v=25` في index.html:32 (style.css) و:555
      (app.js)؛ sprite.svg:3 «v25 Modern Edition».
  - **الحرّاس المكسورة الثلاثة** (MASTER_REVIEW §R10.1:651 — «ثلاثة
    من أربعة كسرها إعادة تصميم الواجهة v25»؛ TF-02 ليس منها —
    تسرّب نطاق providers مستقل):
    1. **TF-01** (:657) — sprite.svg v25 أسقط عبارة «رخصة المشروع»
       المثبّتة في test_file_icons.py:143.
    2. **TF-03** (:659) — v25 حذفت عنصرَي `run-history-btn`/
       `memory-panel-btn` من index.html بينما app.js يربطهما في
       DOMContentLoaded ⇒ TypeError يقطع المعالج ⇒ 3 لوحات معطلة
       (عيب C3/S2 حي، لا انجراف اختبار).
    3. **TF-04** (:660) — مئات الألوان الخام في style.css (976–3633+)
       وindex.html:83–84 متجاوزةً بوابة color-tokens.
    - أثر جانبي: **TF-05** (:663) — بوابة check.sh حمراء دائمًا
      فذابت دلالة الانحدار.
  - **الإصلاحات الموثقة**:
    - TF-01 + TF-03 → **TSK-604 ✅ (S38–39)** — زرا وكيلان مخفيان
      (نمط تفويض `.click()` الموجود في v25 نفسها؛ التعليق الحي
      index.html:472) + إعادة سطر الترخيص للـ sprite؛ إخفاقات
      البوابة 4→2 (سجل §TSK-604 الكامل بأدلته).
    - TF-02 → **TSK-605 جزء أول ✅ (S40)** — استثناء providers/
      من مسح الحارس (تسرّب نطاق، ليس كسر v25).
    - TF-04 → **TSK-605 BLOCKED على قرار المالك D-2**
      (tokenization كاملة أم baseline مؤرَّخ — MASTER_REVIEW:810)؛
      هو الفشل الوحيد المتبقي في خط الانحدار 1900 = 1F.
      *[تحديث S83: D-2 وصل (tokenization كاملة) — TSK-605 ✅ وأول 0F؛
      البيان أعلاه تاريخي بلحظة كتابة ADR-005 في S78.]*
  - **نمط ADR البيتي**: لا مجلد `docs/engineering/adr/` — الـ ADRs
    مقاطع داخل `ARCHITECTURE_DECISIONS.md` (ADR-001:9، ADR-002:66،
    ADR-003:120، ADR-004:178) ببنية Context / Decision /
    Alternatives rejected / Trade-offs / Status. سجل القرارات =
    جدول `DECISION_LOG.md` بصيغة
    `Date, What changed, Why, Evidence, Task`.
- **Behavior-preservation pre-check (S78)**: مهمة توثيقية صرفة —
  الملفات الملموسة حصرًا `ARCHITECTURE_DECISIONS.md` +
  `DECISION_LOG.md` + سجلات المهمة/التقدم/التغييرات؛ **صفر لمس
  كود/اختبارات/أصول**؛ خط الانحدار متوقَّع بلا تغيير (1900 =
  1F/1865P/34S — الفشل الوحيد theme_tokens/TF-04 المعروف).
- **Architecture-Fitness pre-check (S78)**:
  - «ملف ADR» في القبول يُلبّى بمقطع **ADR-005** داخل
    `ARCHITECTURE_DECISIONS.md` — هو ملف الـ ADRs البيتي الوحيد؛
    إنشاء ملف/مجلد منفصل يكسر النمط القائم (ADR-001..004 كلها
    مقاطع) بلا مقابل.
  - الـ ADR **استرجاعي (retroactive)**: القرار وقع خارج حوكمة
    البرنامج (0d74dad قبل بدء Stage 1) — يوثَّق الواقع والدروس، لا
    يُخترع رشيد لم يُسجَّل: دوافع v25 غير المسجلة تُعلَّم **UNKNOWN**.
  - قيد Decision Log يُؤرَّخ بتاريخ التوثيق مع وسم retro واضح +
    إسناد TSK-624 — لا تزوير تاريخ القرار الأصلي.
- **Close-out (S78)**:
  - **Implementation**: مقطع **ADR-005** مُلحق بـ
    `ARCHITECTURE_DECISIONS.md` (بنية Context/Decision-كيف-أُصلحت/
    Alternatives rejected/Trade-offs/Status البيتية؛ موسوم صراحةً
    «retroactive record»؛ الدوافع الأصلية معلَّمة UNKNOWN) + قيد
    استرجاعي موسوم retro في جدول `DECISION_LOG.md` (14 سطرًا الآن).
    صفر لمس كود/اختبارات/أصول.
  - **Acceptance** ✅: ملف الـ ADRs يشرح **النطاق** (جدول commits
    الأربعة بالأدلة من git)، **الأثر** (TF-01/TF-03/TF-04 + TF-05
    تعمية البوابة)، **الحرّاس المكسورة وكيف أُصلحت** (جدول:
    TF-01/03 → TSK-604 ✅؛ TF-04 → معلّق D-2 موثَّقًا كحدّ صريح)؛
    + قيد Decision Log — نصّا القبول محقَّقان حرفيًا.
  - **Gates**: Documentation ✅ (ADR-005 + Decision Log + هذا
    السجل + CHANGELOG) · Regression ✅ — خط الانحدار **بلا تغيير**:
    `{'tests': '1900', 'failures': '1', 'errors': '0',
    'skipped': '34', 'time': '80.377'}` — الفشل الوحيد
    theme_tokens/TF-04 المعروف (docs-only كما في pre-check).
  - **Metrics**: TD-04 **مغلق** (آخر بند R10.3 المفتوح)؛
    ADRs: 4 → **5**؛ قيود Decision Log: 5 → **6**.
  - **Commits**: c3ebfc2 (أدلة قبل الملف) → f23ed91 (ADR-005 +
    Decision Log).
- **Resume notes / Checkpoint / Blocker / Next action**: —
### TSK-625 — صلابة _parse_args_body — P3, ✅ DONE (S77)
تفكيك متسامح مع قيم متعددة الأسطر (ASF-06) + اختبارات حالات عدائية.
- **Evidence (S77)**:
  - **الموضع**: `_parse_args_body` (chain/agent_tools.py:818–835) —
    تفكيك key:value سطرًا-سطرًا: سطر بلا `:` يُهمَل صامتًا؛ أي نص
    قبل `:` يصبح مفتاحًا؛ `val.isdigit()` ⇒ int؛ `reason` يُفصل.
    المستدعي الوحيد: `parse_tool_calls` (:809 — body البلوك بعد
    فصل الأسطر fence-aware). المستهلك: `execute` (:219 —
    `handler(self, **args)`؛ مفتاح غريب ⇒ TypeError ملتقط ⇒
    «❌ خطأ في …»).
  - **مفاتيح الوسائط الشرعية** (تواقيع tool_* :241–:454 — المصدر
    الحي): path/start_line/end_line/depth/query/max_depth/kind/
    text/command/reason — كلها معرّفات ASCII؛ عقد الصيغة المحقون
    في برومبت الـ agent (agent_loop.py:438–476) يستخدمها حرفيًا.
  - **إثبات ASF-06 بالتشغيل (S77)**:
    (1) قيمة متعددة الأسطر تُبتَر صامتًا:
    `text: سطر أول\\nوسطر ثانٍ بلا نقطتين\\nkind: fact` ⇒
    `{'text': 'سطر أول', 'kind': 'fact'}` — السطر الثاني ضاع.
    (2) سطر داخل القيمة يشبه مفتاحًا يُفسَّر مفتاحًا:
    `text: البداية\\nملاحظة عربية: أيضًا` ⇒
    `{'text': 'البداية', 'ملاحظة عربية': 'أيضًا'}` — وسيط زائف
    ⇒ TypeError في execute (فشل الأداة كلها).
    (3) e2e: بلوك remember_fact بنص سطرين ⇒ ToolCall بنص مبتور.
  - **الاختبارات القائمة**: لا اختبار مباشر لـ _parse_args_body؛
    parse_tool_calls مغطاة عرضيًا (test_project_memory.py:254،
    test_project_memory_source.py) بمفاتيح سليمة سطرًا-واحدًا فقط.
- **Behavior-preservation pre-check (S77 — قبل التعديل)**:
  1. **golden للحالات السليمة**: أجسام key:value المعرّفة (مفاتيح
     ASCII معروفة، قيم سطر واحد، أرقام ⇒ int، reason مفصول) تفكَّك
     **حرفيًا كما قبل** — تُثبَّت باختبارات قبل أي تعديل.
  2. التغيير المتعمَّد (غرض المهمة): سطر بلا `:` أو سطر مفتاحه ليس
     وسيطًا شرعيًا يُطوى في قيمة المفتاح السابق (بـ \\n) بدل
     الإهمال/التزييف — تحسين صلابة منصوص عليه في ASF-06.
  3. قائمة المفاتيح الشرعية تُشتق **حيًّا** من تواقيع _handlers
     (inspect) + reason — لا قائمة يدوية تتقادم عند إضافة أداة.
  4. parse_tool_calls (fence-awareness المؤكد جيدًا في ASF-06)
     لا تُمس؛ execute لا يُمس؛ لا أطر/endpoints.
  5. التحقق: regression كامل (خط 1882) + اختبارات عدائية جديدة.
- **Architecture-Fitness pre-check (S77)**: تعديل موضعي في دالة
  التفكيك النقية وحدها (نفس الوحدة، نفس التوقيع tuple[dict, str])؛
  لا تبعيات جديدة؛ لا لمس لـ providers/ (§0.8).
- **Close-out (S77)**:
  - **التنفيذ**: `_parse_args_body` (chain/agent_tools.py) أعيدت
    كتابتها متسامحة: سطر يبدأ بمفتاح **شرعي** يفتح وسيطًا؛ أي سطر
    آخر (بلا `:` أو مفتاحه غير شرعي) **يُطوى** في قيمة المفتاح
    السابق بسطر جديد (يشمل reason)؛ لا مفتاح سابق ⇒ يُهمَل كما
    قبل. المفاتيح الشرعية تُشتق **حيًّا** من تواقيع
    `AgentTools._handlers` عبر `_known_arg_keys()` (inspect +
    reason، cache) — لا قائمة يدوية تتقادم. نفس التوقيع
    tuple[dict, str]؛ parse_tool_calls وexecute بلا لمس.
  - **الاختبارات**: `tests/unit/test_parse_args_body.py` (18):
    golden حفظ السلوك (6 — الحالات السليمة الموثَّقة في برومبت
    الـ agent حرفيًا كما قبل) + القبول متعدد الأسطر (5 — طي
    التكملة/مفتاح-شبيه/قيمة فارغة/reason متعدد) + عدائية (5 —
    يتيم/تزوير _approval يبقى مُسقَطًا/تكرار مفتاح/أسطر قمامة/
    قيمة 50 سطرًا بلا فقد) + الاشتقاق الحي (1) + e2e (2 —
    remember_fact متعدد الأسطر يصل كاملًا + fence-awareness
    بلا تغيير).
  - **البوابات (S77)**: pyflakes + lint_handler_state نظيفة؛ mypy
    Success 81 ملفًا؛ العقود+parity 113 ✓؛ goldens+ws_router 32 ✓؛
    regression كامل: **1900 = 1F/1865P/34S (~81s)** —
    theme_tokens/TF-04/D-2 حصرًا (1882+18=1900 ✓).
    **خط الانحدار الجديد: 1900**.
  - **Rollback**: revert.
### TSK-626 — قرار proposed_actions — P3, ✅ DONE (S79)
توثيق الفرع test-only أو توصيله بمستهلك (RP-04)؛ Acceptance: سطر عقد موثق
في runners + تعليق في server.py.
- **Evidence (S79)**:
  - **النتيجة الأصلية**: RP-04 — MASTER_REVIEW:476 («فرع
    proposed_actions في الـ runners الأربعة خامل إنتاجيًا … سطح عقد
    يُصان بلا مستهلك، ويجب ألا يُحسب كطبقة أمان فعلية») + :732
    (خريطة RP-04 → P3 → TSK-626).
  - **الفرع** (تحقق S79): كتلة الموافقة المتناظرة
    `if request.proposed_actions:` في **الأربعة**: runners/agent.py:103،
    runners/chain.py:90، runners/delegate.py:99، runners/direct.py:76
    (+ المرجع الاختباري tests/fakes/echo_runner.py:64). الحقل:
    `RunRequest.proposed_actions: tuple[ProposedAction, ...] = ()`
    (core/runner.py:90؛ العقد السلوكي موثق :31–35 — «لا بوابة
    موصولة ⇒ رفض آمن»).
  - **صفر مستهلك إنتاجي** (grep شامل S79): مواقع بناء RunRequest
    الإنتاجية الخمسة كلها **بلا** proposed_actions —
    server.py:1536 (delegate thread) +
    core/chat_dispatch.py:240 (chain) /:275 (delegate) /:338 (agent)
    /:444 (direct). **تحديث لأدلة RP-04 الأصلية**: المواقع المذكورة
    فيها (server.py:1652/1754/1849/2297) انتقلت إلى chat_dispatch.py
    في M8 (ADR-002) — الواقع الوظيفي نفسه بلا تغيير.
  - **المستهلكون الاختباريون حصرًا**: RunnerContractMixin —
    tests/contracts/runner_contract.py:142–177 (3 عقود: موافقة
    مقبولة تُطبَّق بالترتيب request→verdict→applied + مرفوضة لا
    تُطبِّق + بلا بوابة ⇒ رفض آمن) + tests/fakes/echo_runner.py.
  - **حدود موثقة قائمة**: worker.py:32–34 يعلن صراحةً أن
    proposed_actions/approval_gate «مجال توسعة لاحق» خارج حمولة
    العامل (T-110) — سابقة توثيق للحالة نفسها.
- **Behavior-preservation pre-check (S79)**:
  - **القرار**: توثيق الفرع test-only (الخيار الأول في نص المهمة) —
    «توصيله بمستهلك» تغيير سلوكي منتج (تفعيل مسار موافقة قبل-العمل
    في الإنتاج) = **قرار مالك** لا يُتخذ ذاتيًا؛ التوثيق يحقق القبول
    حرفيًا بلا لمس سلوك.
  - التغيير = **تعليقات فقط**: سطر عقد فوق كتلة الموافقة في
    الـ runners الأربعة + تعليق عند موقع RunRequest في server.py:1536
    + تعليق مقابل في chat_dispatch.py (المواقع الإنتاجية الأربعة
    الأخرى — بدونه التوثيق ينقض الواقع بعد M8)؛ صفر تغيير منطق/
    تواقيع/سلاسل نصية مبثوثة ⇒ خط الانحدار متوقَّع بلا تغيير
    (1900 = 1F/1865P/34S).
- **Architecture-Fitness pre-check (S79)**:
  - الفرع **يبقى ولا يُزال**: عقود RunnerContractMixin الثلاثة
    تصونه حيًّا، وworker.py يعلنه «مجال توسعة لاحق» — إزالته تكسر
    العقود وتغلق باب التوسعة؛ المطلوب (نص RP-04 حرفيًا) هو ألا
    يُحسب طبقة أمان فعلية عند تقييم المسارات — وهذا يتحقق بالتوثيق.
  - سطر العقد يُصاغ موحَّدًا في الأربعة (نمط الكتلة المتناظرة
    القائم نفسه) ويشير إلى RP-04/TSK-626 + مواقع البناء الخمسة —
    قارئ أي runner يعرف الحالة دون بحث.
  - لا توثيق في echo_runner (fake اختباري — هو المستهلك المقصود).
- **Close-out (S79)**:
  - **Implementation** (تعليقات فقط — صفر منطق): سطر عقد موحَّد
    «عقد (RP-04/TSK-626): هذا الفرع test-only حاليًا…» فوق كتلة
    الموافقة في الأربعة — runners/agent.py:103، runners/chain.py:90،
    runners/delegate.py:99، runners/direct.py:76 — يشير إلى مواقع
    البناء الخمسة (server.py:1540 + chat_dispatch.py:245/280/343/449
    — أرقام ما-بعد-التعليقات، مصحَّحة) والمستهلك الاختباري الوحيد
    (RunnerContractMixin) و«لا يُحسب طبقة أمان فعلية؛ يُصان كمجال
    توسعة (worker.py T-110)». + تعليق مقابل عند موقع RunRequest في
    server.py:1533–1536 + تعليق جامع في chat_dispatch.py:26–31
    (المواقع الإنتاجية الأربعة الأخرى بعد نقل M8/ADR-002).
  - **Acceptance** ✅: «سطر عقد موثق في runners» (الأربعة) +
    «تعليق في server.py» — نصّا القبول محقَّقان حرفيًا؛ الخيار
    المنفَّذ = توثيق test-only (التوصيل بمستهلك = قرار منتج لم
    يُتخذ ذاتيًا — مسجَّل في pre-check).
  - **Gates**: pyflakes — دلتا الملفات الملموسة صفر مقابل HEAD
    (تحقق stash-diff S79: نفس النتائج القائمة، إزاحة أرقام أسطر
    فقط) · lint_handler_state نظيفة · mypy Success 81 ملفًا ·
    contracts+parity 113 ✓ · goldens+ws_router 32 ✓ · regression
    junitxml **1900 = 1F/1865P/34S** (82.0s — بلا تغيير؛
    theme_tokens/TF-04/D-2 حصرًا).
  - **Metrics**: RP-04 **مغلق** (آخر بند RP المفتوح)؛ M10 3/4؛
    Stage 3 **22/26** — كل المتبقي محجوب على قرارات المالك.
  - **Commits**: 8893a8f (أدلة قبل الكود؛ التنفيذ التقطه دمج
    المستخدم a74ca08) → commit الإغلاق الحالي.
- **Resume notes / Checkpoint / Blocker / Next action**: —

---

## جدول تتبّع الحالة (المصدر الوحيد للحالة مع PROGRESS.md)

| TSK | M | P | Status | ملاحظة |
|---|---|---|---|---|
| 601 | M6 | P1 | ✅ DONE (S33–34) | 6 اختبارات جديدة خضراء؛ regression نظيف (4F المعروفة فقط) |
| 602 | M6 | P1 | ✅ DONE (S35–36) | 6 اختبارات جديدة؛ مواضع الحقن الخام 5→0؛ regression نظيف |
| 603 | M6 | P1 | ✅ DONE (S37) | fail-closed بـ sentinel؛ 7 اختبارات جديدة؛ regression نظيف |
| 604 | M6 | P1 | ✅ DONE (S38–39) | زرا وكيلان مخفيان + سطر الترخيص؛ إخفاقات البوابة 4→2 |
| 605 | M6 | P1 | ✅ DONE (TF-02 S40 · TF-04 S83) | tokenization كاملة (قرار D-2)؛ إخفاقات البوابة 1→0؛ **أول regression صفري-الإخفاق + check.sh ALL GREEN؛ M6 مغلقة 5/5** |
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
| 617 | M9 | P2 | ✅ DONE (S83) | قرار D-1: الافتراضان الآمنان في الكود (fail-closed)؛ config الحالي بلا تغيير سلوكي |
| 618 | M9 | P2 | ✅ DONE (S73) | فصل القياس عن القرار أحيا فحص symlink الميت (NF-28) وضيّق الالتقاط إلى OSError موسوم؛ 9 اختبارات (أول تغطية لـ path_policy)؛ خط الانحدار 1850 |
| 619 | M9 | P2 | ✅ DONE (S74) | بطاقة الخطة التفاعلية: checkbox لكل خطوة عبر وحدة نقية plan_card.js وexecutePlan يرسل المفعّل فقط؛ server.py بلا لمس؛ 10 اختبارات node؛ خط الانحدار 1860 |
| 620 | M9 | P2 | ✅ DONE (S75) | سرد الجلسة: timeline من الأطر الحية (استهلاك-فقط) عبر وحدة نقية session_narrative.js فوق قائمة RunHistory؛ server.py بلا لمس؛ 10 اختبارات node؛ خط الانحدار 1870 |
| 621 | M9 | P2 | ✅ DONE (S76) | endpoint قراءة /api/permissions (blueprint meta) + لوحة قراءة-فقط بوحدة نقية permissions_panel.js؛ سطح REST 30→31 (توسيع عقد موثَّق)؛ 12 اختبارًا؛ خط الانحدار 1882 |
| 622 | M9 | P2 | ✅ DONE (S83) | قرار D-4: re-vote مؤرَّخ أُلحق بـ RRR (§5) — G1–G5 كلها PASS بدليل حي؛ الحكم GO ضمن عقد localhost؛ TD-03 مغلق؛ M9 مغلقة كاملة |
| 623 | M10 | P3 | ✅ DONE (S83) | قرار D-3: أرشفة improvements/ (892KB، 40 ملفًا) إلى tar.gz متتبع داخل test---results/ بعد تحقّق diff -r متطابق؛ الشجرة نظيفة؛ check.sh ALL GREEN؛ خط الانحدار 1901؛ QF-01 مغلق؛ M10 مغلقة كاملة |
| 624 | M10 | P3 | ✅ DONE (S78) | ADR-005 استرجاعي لإعادة تصميم v25 (النطاق/الأثر/الحرّاس الثلاثة وإصلاحاتها) + قيد retro في DECISION_LOG؛ TD-04 مغلق؛ خط الانحدار بلا تغيير (1900) |
| 625 | M10 | P3 | ✅ DONE (S77) | _parse_args_body متسامح متعدد الأسطر (طي التكملة، مفاتيح شرعية حيّة من التواقيع)؛ ASF-06 مغلق؛ 18 اختبارًا؛ خط الانحدار 1900 |
| 626 | M10 | P3 | ✅ DONE (S79) | فرع proposed_actions موثَّق test-only: سطر عقد موحَّد في الـ runners الأربعة + تعليق عند مواقع بناء RunRequest الخمسة (server.py + chat_dispatch.py)؛ RP-04 مغلق؛ خط الانحدار بلا تغيير (1900) |

---

# BATCH-SHORT — دفعة المالك D-5 (تحت حكم V3) — 2026-07-30

> مرآة غير حاكمة — المرجع PROGRESS.md (حالة المهام هناك حصريًا).
> التفويض: قرار مالك D-5 (DECISION_LOG @ bc3fa7a): «دفعة SHORT كاملة» =
> FI-03 + FI-06 + FI-10 + FI-11 + FI-12. خط أساس الدفعة (مُعاد تشغيله حيًا
> هذه الجلسة @ 4e87d6b): **1866P/34S/0F** + test_search_perf البيئي
> (موثَّق flaky — فشل 1.036s>1.0s على هذا العتاد فقط).

## TSK-701 — FI-11: مواصفة بروتوكول إطارات WS [توثيق فقط]
- **Fixes**: FI-11. **Deps**: لا شيء.
- **Evidence**: أشكال الإطارات ضمنية عبر `core/ws_router.py` (جدول 25 نوعًا @ 03c7eab)
  + مواقع الإرسال في server.py/chat_dispatch + `static/app.js` onmessage.
- **Change**: ملف جديد `docs/ws_frame_protocol.md` — جرد كل أنواع الإطارات
  (اتجاهين)، الحقول الإلزامية، الترتيب، إطارات الخطأ/الإنهاء — من الكود الحي.
- **Accept (آلي)**: كل نوع إطار في المواصفة موجود في الكود والعكس (grep تحقق
  مزدوج الاتجاه يُرفق في Close-out)؛ صفر تغيير كود؛ الانحدار 1866P ثابت.

## TSK-702 — FI-12: دليل النشر ونموذج التهديد [توثيق فقط]
- **Fixes**: FI-12. **Deps**: لا شيء (TSK-502 مدموجة سلفًا).
- **Evidence**: عقد RRR §5 (localhost أحادي المستخدم)؛ `force_command_approval`
  في config.yaml؛ تحصينات ZIP (TSK-105/_zip_member_violations).
- **Change**: ملف جديد `docs/deployment_threat_model.md` — حدود الثقة،
  الافتراضي localhost-only، ماذا يعني أي تعريض أبعد (قرار واعٍ موثَّق).
- **Accept (آلي)**: كل ادعاء أمني فيه مرساة `file:line @ commit`؛ صفر تغيير كود.

## TSK-703 — FI-10: تعقيم عرض Markdown (DOMPurify) [كود]
- **Fixes**: FI-10 (سطح XSS client-side المتمم لـ TSK-404). **Deps**: لا شيء.
- **Evidence**: `renderMarkdown` @ app.js:2389 يعيد `marked.parse(text)` خامًا؛
  يُحقن عبر innerHTML في ≥8 مواقع (:928..:1043).
- **Change**: (1) vendoring `static/vendor/purify.min.js` (2) تحميله في
  index.html قبل app.js (3) تغليف ناتج renderMarkdown الوحيد:
  `DOMPurify.sanitize(...)` مع fallback آمن إن غاب الرمز (سلوك fail-open
  للعرض النصي المهرَّب — لا كسر إن فشل التحميل).
- **Accept (آلي)**: `<img onerror>`/`<script>` في نص نموذجي لا ينجو من التعقيم
  (اختبار DOM بسيط عبر node إن توفر، وإلا فحص سلسلة التغليف بـ grep-guard)؛
  الانحدار 1866P ثابت (لا اختبارات python تمس app.js).

## TSK-704 — FI-06: السجلات المهيكلة [كود]
- **Fixes**: FI-06 (NF-14: مواقع ابتلاع صامتة). **Deps**: لا شيء (TSK-305 مقفلة).
- **Evidence**: 91 موقع `except Exception` (منها ~31 صامتة pass/continue)
  عبر server.py(23)/chain(51)/core(17) @ 4e87d6b.
- **Change** (محكوم الحجم §9.1): وحدة جديدة `core/structured_log.py`
  (JSON formatter على stdlib logging؛ صفر تبعية جديدة) + توصيل المواقع
  **الصامتة** في core/ وchain/ بسطر `log.debug/warning(event=...)` —
  **إضافة سجل فقط، صفر تغيير تدفق تحكم** (bit-identical سلوكيًا).
  server.py المواقع الـ23 تُوصَّل في نفس النمط إن اتسعت الجلسة وإلا انحراف
  موثَّق يقصرها على core/+chain/.
- **Accept (آلي)**: اختبارات جديدة لـ structured_log (صيغة JSON، الحقول)؛
  grep يثبت صفر `except Exception:` متبوعة بـ pass صامت في core/+chain/
  (كل موقع إما يسجل أو يعلَّق بتعليل)؛ الانحدار كامل أخضر.

## TSK-705 — FI-03: انضباط الإيقاف الرشيق [كود]
- **Fixes**: FI-03 (NF-05: خيوط daemon بلا join عند الخروج). **Deps**: TSK-304 مقفلة ✅.
- **Evidence**: خيوط daemon في server.py؛ `ExecutionRegistry` يملك
  cancel تعاوني + `list_active` (core/execution.py:161/:265 @ 4e87d6b).
- **Change**: دالة `graceful_shutdown(registry, timeout)` في core/execution.py
  (cancel لكل التذاكر الحية + انتظار محدود حتى terminal/انقضاء المهلة) +
  ربط SIGTERM/SIGINT في مدخل server.py (`main`) فقط — لا تغيير في مسار الطلبات.
- **Accept (آلي)**: اختبارات وحدة للدالة (تذاكر حية → cancelled؛ احترام المهلة؛
  صفر تذاكر = عودة فورية)؛ الانحدار كامل أخضر؛ check.sh أخضر.

## ترتيب التنفيذ (DAG بلا دورات)
701 → 702 → 703 → 704 → 705 (مستقلة كلها؛ الترتيب بالمخاطرة تصاعديًا).

# BATCH-FI01 — دفعة المالك D-7 (تحت حكم V3) — 2026-07-30

> FI-01: توحيد حالة الجلسة REST/WS (FUTURE_IMPROVEMENTS.md:16-27).
> شرط المالك الملزم: **تاسكات صغيرة** — كل TSK قابلة للإغلاق في جلسة واحدة.
> Prerequisite (FI-01:26): TSK-302 ✅ مقفلة منذ S14 (PROGRESS_ARCHIVE_1.md:860).
> قرار نطاق ملزم (يُسجَّل في DECISION_LOG عند البدء): التوحيد = مخزن
> قانوني واحد `ConversationState` تمر عبره كل كتابات/قراءات REST؛
> عزل التبويبات لكل اتصال WS (T-048) **يبقى كما هو** — إزالته نكوص
> مقصود ضده lint_handler_state. ما يُستأصل: طفرات globals الخام
> (`chat_history` @ server.py:141، `_binding_banner` @ server.py:145
> و12 موقع كتابة/قراءة في routes/*).

## TSK-707 — FI-01/1: إنشاء core/conversation_state.py [كود — صغيرة]
- **Fixes**: جزء FI-01 (NF-03 dual-state، خطر g5). **Deps**: لا شيء.
- **Change**: ملف جديد `core/conversation_state.py` — `ConversationState`
  (dataclass/class): `history: list[Message]`، `binding_banner: str` +
  عمليات مسماة (append/replace_all/clear/snapshot/set_banner/clear_banner)
  خلف قفل RLock واحد. **صفر توصيل** — الملف مستقل.
- **Accept (آلي)**: اختبارات وحدة جديدة (سلوك العمليات + العزل بالنسخ
  في snapshot)؛ حارس الدورات 0 cycles؛ mypy نظيف.

## TSK-708 — FI-01/2: توصيل server.py بالمخزن القانوني [كود — صغيرة]
- **Fixes**: جزء FI-01. **Deps**: TSK-707.
- **Evidence**: `chat_history` @ server.py:141؛ `_binding_banner` @ :145؛
  بذر WS @ :977 (`chat_history=list(chat_history)`) و:982
  (`banner_source=lambda: _binding_banner`)؛ استعادة الإقلاع @ :1896-1898.
- **Change**: إنشاء `conversation_state = ConversationState()` في server.py؛
  `_build_session_context` يبذر من `conversation_state.snapshot()` والبانر
  من `conversation_state.binding_banner`؛ مسار الإقلاع في main() يكتب عبر
  المخزن. globals القديمة تبقى **كأسماء توافق للقراءة فقط** مؤقتًا إن لزم
  لعدم كسر الاختبارات القائمة (يُوثَّق أي إبقاء).
- **Accept (آلي)**: الانحدار كامل أخضر (سلوك مطابق)؛ صفر تغيير في أشكال
  إطارات WS (مواصفة TSK-701 مرجع).

## TSK-709 — FI-01/3: ترحيل routes/sessions.py + meta.py [كود — صغيرة]
- **Fixes**: جزء FI-01. **Deps**: TSK-708.
- **Evidence**: كتابات `_srv.chat_history` @ routes/sessions.py:33/:61/:78؛
  `_srv._binding_banner` @ :34/:79؛ قراءة @ :26؛ قراءة meta.py:34.
- **Change**: استبدال كل قراءة/كتابة مباشرة باستدعاءات
  `_srv.conversation_state.*` — **صفر تغيير في أشكال JSON** (نفس المفاتيح
  والقيم حرفيًا).
- **Accept (آلي)**: test_rest_blueprints أخضر؛ الانحدار كامل أخضر.

## TSK-710 — FI-01/4: ترحيل routes/project.py (فرعا warn/fork) [كود — صغيرة]
- **Fixes**: جزء FI-01. **Deps**: TSK-708.
- **Evidence**: `_srv._binding_banner` @ routes/project.py:93/:102؛
  `_srv.chat_history = []` @ :100.
- **Change**: نفس نمط TSK-709 على مسار switch-project (R-303) — دلالة
  warn/fork/block تبقى حرفيًا.
- **Accept (آلي)**: test_session_binding + test_switch_project_stale_refs
  أخضران؛ الانحدار كامل أخضر.

## TSK-711 — FI-01/5: اختبار عقد التكافؤ REST↔WS + إغلاق الدفعة [اختبار — صغيرة]
- **Fixes**: إغلاق FI-01. **Deps**: TSK-709 + TSK-710.
- **Change**: اختبار عقد جديد: (1) كتابة عبر مسار REST ثم بذر SessionContext
  جديد ⇒ يرى نفس التاريخ/البانر؛ (2) ماسح ثابت يمنع عودة الكتابة المباشرة
  على `chat_history`/`_binding_banner` خارج المخزن (نمط اختبار
  test_no_remaining_silent_sites). تحديث FUTURE_IMPROVEMENTS غير مطلوب
  (الحالة في PROGRESS فقط).
- **Accept (آلي)**: check.sh كامل ALL GREEN rc=0؛ الانحدار vs خط الأساس
  1891P/34S (+ الاختبارات الجديدة).

## ترتيب التنفيذ (DAG بلا دورات)
707 → 708 → (709 ∥ 710) → 711. كل واحدة صغيرة ومغلقة في جلسة.

# BATCH-P0 — دفعة المالك D-8: بوابة الإنتاج (تحت حكم V3) — 2026-07-30

> المصدر: Evolution Gap Report §10 (P0) + قرارات مالك D-8 (DECISION_LOG).
> شرط المالك الدائم (D-7): تاسكات صغيرة، كل TSK قابلة للإغلاق في جلسة واحدة.
> سياق المنصات (D-8-ب): **Windows أولًا، Linux مستقبلًا**.
> P0-1 (مصير engineering_constitution/) خرج من الدفعة: مؤجَّل بقرار D-8-أ إلى
> بند ختامي **EOP-1** (حذف المجلد قبل الوسم النهائي للمشروع).

## TSK-712 — P0-5: مصالحة ترويسة PROGRESS (CI-2/CI-3/CI-4) [توثيق — صغيرة]
- **Fixes**: CI-2 (last-updated متجمدة على S90) + CI-3 (أقسام Current Stage/
  Position/Next action متجمدة على حقبة S83/S84) + CI-4 (سطر repository @ 35c05d7).
- **Deps**: لا شيء.
- **Change**: تحديث حقول الترويسة الحاكمة فقط (last-updated/stage/current-phase/
  current-task/repository) + أقسام Current Stage/Position/Next وفق الواقع
  (BATCH-P0 جارية)؛ سجل الجلسات append-only لا يُمس؛ قيد جلسة جديد S95.
- **Accept (آلي)**: صفر تعديل كود؛ diff محصور في PROGRESS.md؛ الترويسة
  تطابق DECISION_LOG (D-8) حرفيًا.

## TSK-713 — P0-3: requirements.txt تشغيلي + تحقق تثبيت نظيف [تغليف — صغيرة]
- **Fixes**: فجوة «لا مسار تثبيت» (Gap Report §3-ب).
- **Deps**: TSK-712.
- **Evidence**: الصلبة (import أعلى الموديول): flask @ server.py:32،
  flask_sock @ :33، requests @ providers/use_ai.py:18 + alle_ai.py:15 +
  openai_shelby.py:12، yaml @ chain/agent_loader.py. الاختيارية المحروسة:
  websocket-client (use_ai.py:25-29)، cloudscraper (deepseek.py:15-19)،
  colorama (command_runner.py:18-20)، redis (backends_redis.py:72-76 كسول)،
  tree-sitter (symbol_index.py — تدهور رشيق موثق في requirements-dev.txt).
- **Change**: ملف `requirements.txt` جديد: 4 تبعيات صلبة مُسقَّفة الإصدار +
  قسم معلّق للاختيارية مع سبب كل واحدة؛ تحديث README §التشغيل السريع
  (pip install -r requirements.txt).
- **Accept (آلي)**: venv نظيف + `pip install -r requirements.txt` +
  `python -c "import server"` ينجح (بلا dev deps)؛ الانحدار الكامل أخضر
  في بيئة dev المعتادة.

## TSK-714 — P0-7: تدقيق توافق Windows [تدقيق + إصلاحات طفيفة — صغيرة]
- **Fixes**: D-8-ب (Windows أولًا). **Deps**: TSK-713.
- **Scope**: تدقيق ساكن (البيئة الحالية Linux): (1) الإشارات — SIGTERM لا
  يُطلق عمليًا على Windows وsignal.signal(SIGTERM) قانوني لكن CTRL_C يمر
  عبر SIGINT (مسار TSK-705 يعمل)؛ (2) المسارات — pathlib عمومًا،
  server.py:780 يطبّع '\\'→'/' أصلًا؛ (3) subprocess/encoding (cp1256!)؛
  (4) القفل/الملفات المفتوحة (rename فوق ملف مفتوح يفشل على Windows —
  مراجعة project_memory/checkpoint)؛ (5) سلوك flask-sock.
- **Change**: تقرير `docs/WINDOWS_COMPAT.md` (نتائج + قائمة فحص تشغيل
  للمالك على جهاز Windows حقيقي) + إصلاحات كود **طفيفة فقط** إن وُجدت
  مواقع قاطعة (كل إصلاح بقيد دليل)؛ أي إصلاح غير طفيف → TSK مستقلة.
- **Accept (آلي)**: check.sh ALL GREEN؛ التقرير يغطي المحاور الخمسة
  بأدلة file:line؛ قائمة فحص المالك مُسلَّمة.

## TSK-715 — P0-6: دليل المستخدم النهائي (عربي، Windows-أولًا) [توثيق — صغيرة]
- **Fixes**: فجوة «لا دليل مستخدم». **Deps**: TSK-713 (يستشهد بمسار التثبيت)
  + TSK-714 (يستشهد بقائمة Windows).
- **Change**: `docs/USER_GUIDE.md` بالعربية: المتطلبات → التثبيت (Windows
  خطوة-بخطوة + Linux مختصر) → التشغيل → الواجهة → **عقد localhost الأمني
  بلغة مستخدم** (deployment_threat_model.md §5 مصدرًا: لا تعرض المنفذ
  خارج جهازك أبدًا) → الأسئلة الشائعة/الاستكشاف.
- **Accept (آلي)**: صفر تعديل كود؛ كل أمر مذكور في الدليل منسوخ من
  مصدر متحقق (README/WINDOWS_COMPAT)؛ روابط داخلية سليمة.

## TSK-716 — P0-4: رقم الإصدار + سياسة الإصدارات [كود طفيف + توثيق — صغيرة]
- **Fixes**: فجوة «لا نسخة». **Deps**: TSK-712.
- **Change**: (1) `core/version.py` — ثابت `__version__ = "1.0.0-rc.1"`
  (SemVer؛ rc حتى تحقق Windows الفعلي من المالك)؛ (2) server.py يعرضه في
  سطر الإقلاع + `--version`؛ (3) `/api/meta` يضيف حقل version (إضافة مفتاح
  فقط — لا كسر شكل)؛ (4) قسم «سياسة الإصدارات» في README (متى يرتفع
  major/minor/patch، الوسم = بعد إغلاق كل دفعة إنتاج).
- **Accept (آلي)**: اختبار وحدة جديد (استيراد الثابت + وجوده في meta)؛
  الانحدار كامل أخضر؛ صفر تغيير في مفاتيح JSON القائمة.

## TSK-717 — P0-2 + إغلاق الدفعة: LICENSE + وسم v1.0.0-rc.1 [قانوني/إغلاق — صغيرة]
- **Fixes**: فجوة «لا LICENSE». **Deps**: TSK-713..716 كلها.
- **قرار مطلوب**: المالك لم يحدد الرخصة بعد. **الافتراضي الآمن المؤقت**:
  LICENSE «All Rights Reserved — © 2026 pijsal1-tech» (ملكية خاصة؛ الخيار
  الوحيد القانوني الآمن لمستودع خاص بلا قرار) — قابل للاستبدال بـ MIT/
  Apache-2.0 بكلمة واحدة من المالك، ويُسجَّل الاستبدال قيد قرار.
- **Change**: ملف LICENSE + إشارة في README + إغلاق الدفعة: CHANGELOG
  قيد [TSK-712..717/D-8] + PROGRESS + **git tag v1.0.0-rc.1** (تفويض
  D-8-ج) + الحفظ على origin.
- **Accept (آلي)**: check.sh ALL GREEN rc=0 (بوابة الإغلاق)؛ الانحدار vs
  خط الأساس 1911P/34S؛ tag موجود على origin.

## ترتيب التنفيذ (DAG بلا دورات)
712 → 713 → 714 → (715 ∥ 716) → 717. كل واحدة صغيرة ومغلقة في جلسة.

## بند ختامي مُرحَّل (خارج BATCH-P0)
- **EOP-1** (قرار D-8-أ): حذف `docs/engineering_constitution/` — يُنفَّذ في
  **آخر المشروع** قبل الوسم النهائي؛ إلى حينها المجلد HISTORICAL-INERT.

# BATCH-P1 — دفعة التطوير الأولى بعد الإنتاج (D-9 تحت تفويض D-8-ج)

**المصدر**: برنامج ما-بعد-P0 المفوَّض (D-8-ج، PROGRESS §Current Position):
P1 = FI-05 (فهرس بحث دائم) + لوحة تشخيص/support bundle + تدوير سجلات +
Settings UI. **التقسيم صغيرًا** إجراء دائم (D-7). خط الأساس: **1914P/34S**
+ check.sh ALL GREEN @ 78dac87 (v1.0.0-rc.1).

## TSK-718 — FI-05/1: وحدة snapshot الفهرس (صيغة + حفظ/تحميل ذرّي) [صغيرة ~30د]
- **Fixes**: FI-05 (النصف الأول). **Deps**: TSK-501 ✅ (Completed S22 —
  PROGRESS_ARCHIVE_1.md:868). **بلا أي توصيل** — وحدة ورقة + اختباراتها فقط.
- **Change**: `core/index_snapshot.py` جديدة (تسكن core/ **وليس** context/ —
  بوابة SafeReader grep في check.sh:24-27 تمنع open() داخل context/):
  (1) صيغة v1: JSON `{version, root, files: [rel...]}`؛
  (2) `save_snapshot(path, root, rel_files) -> bool` — نمط NF-19 حرفيًا
  (tmp بجوار الملف → fsync → os.replace؛ سابقة project_memory.py:356)،
  **لا يرفع أبدًا** (فشل الحفظ = False + تجاهل — الـ snapshot تحسين لا صحّة)؛
  (3) `load_snapshot(path, root) -> list[str] | None` — None عند أي
  عدم-تطابق (نسخة/جذر/JSON فاسد/شكل شاذ) — التحميل الفاشل يسقط للـ rebuild.
- **Accept (آلي)**: اختبارات وحدة جديدة (roundtrip؛ جذر مغاير→None؛ نسخة
  مغايرة→None؛ ملف فاسد→None؛ مجلد غير قابل للكتابة→False بلا استثناء)؛
  الانحدار كامل أخضر vs 1914P/34S؛ بوابات grep سليمة (الوحدة خارج context/).

## TSK-719 — FI-05/2: توصيل التحميل عند الفتح + الحفظ بعد rebuild [صغيرة ~45د]
- **Fixes**: FI-05 (الإغلاق). **Deps**: TSK-718.
- **Change**: (1) `ProjectIndex.__init__` يقبل `snapshot_path` اختياريًا؛
  تحميل ناجح ⇒ بذر `_files` + `_reindex()` **بلا مشية شجرية** (الفتح فوري)؛
  فاشل ⇒ rebuild() كالسابق؛ (2) حفظ بعد rebuild **فقط عند تغيّر القائمة**
  (لا churn من sweep الـ 2s)؛ (3) التوصيل في `_server_handle_factory` +
  `_build_ctx` (server.py:661/681) بمسار `<root>/.ai_runs/project_index.json`
  (ضمن IGNORED_DIRS — لا يلوث البحث).
- **عقد الطزاجة محفوظ**: snapshot قديم = نافذة staleness واحدة ≤2s حتى أول
  sweep (نفس عقد T-049 للتعديلات الخارجية — لا تغيير دلالي)؛ خطافات
  write-through تعمل فورًا؛ ملف محذوف في القائمة المبذورة ⇒ stat يفشل في
  read_lines ⇒ يُتخطى (سلوك قائم).
- **Accept (آلي)**: تكافؤ ذهبي (نتائج lookup/search متطابقة بين بناء طازج
  وتحميل snapshot)؛ snapshot قديم يتقارب بعد refresh_if_stale(force=True)؛
  الانحدار كامل أخضر.

## TSK-720 — P1-3: تدوير سجل metrics/runs.jsonl [صغيرة ~30د]
- **Fixes**: نمو غير محدود للملف الملحق-فقط الوحيد على مستوى التطبيق
  (server.py:2128 — RunMetricsStore بلا سقف). **Deps**: لا شيء.
- **Change**: تدوير بالحجم عند الإقلاع (نمط تدوير PROGRESS في D-6):
  تجاوز السقف (افتراضي 5MB) ⇒ `runs.jsonl` → `runs.jsonl.1` (os.replace،
  جيل واحد يكفي للنطاق) وبدء ملف جديد؛ القارئ (الملخّص) يبقى كما هو
  (يقرأ الحالي فقط — فقدان تاريخ الجيل السابق من الملخص مقبول وموثَّق).
- **Accept (آلي)**: اختبار وحدة (ملف فوق السقف يُدوَّر؛ تحته لا يُمس؛
  idempotent)؛ الانحدار كامل أخضر.

## TSK-721 — P1-2: نقطة تشخيص + Support Bundle [صغيرة~متوسطة ~60د]
- **Fixes**: لا أداة تشخيص للمستخدم (فجوة Evolution Gap §10). **Deps**:
  TSK-716 ✅ (version). **Change**: `/api/diagnostics` (routes/meta.py —
  نمط ADR-003): version + platform + سلامة التبعيات الأربع + ملخص مقاييس +
  حالة المزود — **مُطهَّر** (صفر أسرار/مفاتيح/مسارات مطلقة خارج الجذر)؛
  زر في الواجهة يحمّل الحصيلة JSON (support bundle).
- **Accept (آلي)**: اختبار عقد (المفاتيح موجودة + فحص عدم-تسريب: لا نمط
  sk-/ghp_/api_key في الحصيلة)؛ الانحدار كامل أخضر.

## TSK-722 — P1-4: Settings UI [مُفصَّلة — S99/D-9] (تنقسم إلى 722a + 722b)

**جرد التفصيل (S99)**: config.yaml = 221 سطرًا، يُقرأ عبر `_load_config()`
(server.py:170 — مُكاش، تسامحي، فشل ⇒ {})؛ زر «الإعدادات» في activity bar
(index.html:271) يستدعي `toggleThemePicker()` فقط — لا لوحة إعدادات فعلية.
السابقة المعتمدة: TSK-621 (لوحة الصلاحيات glass box قراءة-فقط).

**قرار النطاق (D-7)**: قراءة-فقط حصريًا. **أي مسار كتابة config عبر
HTTP مؤجَّل صراحةً كقرار مالكٍ منفصل** — لأسباب أمنية (وضعية localhost؛
مفاتيح fail-closed مثل `force_command_approval` لا يجوز أن تُقلب من
متصفح؛ config مُكاش ⇒ الكتابة تتطلب عقد invalidation جديد).

### TSK-722a — endpoint `/api/settings` قراءة-فقط مُطهَّر [صغيرة]
- **ماذا**: `GET /api/settings` في routes/meta.py (نمط api_permissions
  حرفيًا) يعيد **القيم الفعالة** (effective، لا الخام فقط) من config الحي.
- **عقد التطهير — whitelist أقسام صريح** (لا blacklist): تُعرض فقط:
  `default_provider, language, auto_execute, backup_before_edit,
  max_context_files, agent{command_allowlist,command_timeout_seconds,
  command_output_max_chars}, context_budget, history, context.semantic,
  session_binding, retention, planner, backend, dispatch,
  execution, routing`. **يُستبعد كليًا**: قسم `providers` (قد يحمل
  api_key/base_url مستقبلًا) و`project_root` (مسار مطلق — يُعرض فقط
  كراية `project_root_set: bool`). لا مسارات مطلقة في الاستجابة
  (نفس عقد TSK-721).
- **القيم الفعالة**: `force_command_approval` تُقرأ من
  `_srv._force_command_approval()` (تعكس الافتراضي fail-closed عند
  الغياب — D-1/TSK-617) مع راية `explicit_in_config: bool`.
- **قراءة-فقط**: GET بلا آثار جانبية؛ لا POST/PUT — توسيع سطح REST
  المجمَّد 32→33 موثَّق (سابقة TSK-621/721) في test_rest_blueprints.
- **قبول آلي**: tests/unit/test_settings_endpoint.py — (1) المفاتيح
  المسموحة تظهر بقيم config الحية؛ (2) **عدم-تسريب**: config مزروع
  بقسم providers يحوي `api_key: "sk-LEAKED"` ⇒ لا `sk-`/`api_key`/
  `providers` في الاستجابة كاملة؛ (3) لا مسارات مطلقة (project_root
  مضبوط ⇒ فقط `project_root_set: true`)؛ (4) config فارغ/معطوب ⇒
  استجابة سليمة بالقيم الفعالة الافتراضية (force_command_approval
  = true fail-closed)؛ (5) GET فقط (POST ⇒ 405).

### TSK-722b — لوحة الإعدادات (عرض-فقط) [صغيرة]
- **ماذا**: `static/js/settings_panel.js` (UMD-lite نقي — نمط
  permissions_panel.js حرفيًا: `renderPanelHTML` + escapeHtml، صفر DOM
  glue داخل الوحدة)؛ زر «الإعدادات» في activity bar يفتح اللوحة
  (toggleSettingsPanel في app.js: fetch `/api/settings` + render)؛
  زر الثيم الحالي يبقى كما هو (سلوك toggleThemePicker لا يُمس —
  يُضاف زر لوحة مستقل أو تُعاد تسمية الحالي بوضوح).
- **عرض-فقط**: لا أزرار تعديل/حفظ ولا أي طلب كتابة؛ الغائب يُعرض
  UNKNOWN صريحًا (لا اختراع)؛ ملاحظة ظاهرة في اللوحة: «التعديل عبر
  config.yaml + إعادة تشغيل».
- **قبول آلي**: tests/unit/test_settings_panel.py (نمط
  test_permissions_panel node): (1) renderPanelHTML يعرض الأقسام
  بالقيم الواردة حرفيًا + تهريب HTML؛ (2) حالات الغياب ⇒ UNKNOWN؛
  (3) wiring: app.js يستهلك SettingsPanel (fetch + render، بلا كتابة)
  وindex.html يحمّل settings_panel.js قبل app.js + الزر موجود.
- **سيناريو يدوي موثَّق** (بند Documentation): فتح اللوحة ⇒ قيم
  config.yaml الحية تظهر؛ تعديل config + إعادة تشغيل ⇒ القيم الجديدة؛
  DevTools: GET واحد ولا POST.

**ترتيب**: 722a → 722b (اللوحة تستهلك الـ endpoint).

## ترتيب التنفيذ (DAG بلا دورات)
718 → 719؛ 720 ∥ 721 (مستقلتان)؛ 722 آخرًا بعد تفصيلها.
**الأولى**: TSK-718 (أعلى قيمة [MID] وجاهزيتها كاملة).

---

# BATCH-P2 (قرار D-10 — تحت تفويض D-8-ج) — S100

**النطاق من برنامج D-8-ج**: FI-09 (تمرير افتراضي) + FI-07 (تفكيك app.js)
+ Command Palette + Workspace Trust + غلاف سطح مكتب.
**جرد التخطيط (S100)**: app.js = 3948 سطرًا / ~150 دالة؛ Ctrl+K Quick
Open قائم (app.js:3821-3900 — modal + fetch /api/search)؛ ApprovalGate
يُبنى من auto_execute (server.py:1972-1985: false ⇒ interactive)؛
force_command_approval افتراضي fail-closed (D-1)؛ FI-07 شرطه «لا تفكيك
أثناء إعادة كتابة المُصيِّر» ⇒ يأتي بعد FI-09؛ الغلاف يتطلب تحققًا على
Windows من المالك (D-8-ب) ⇒ آخرًا.

## TSK-723 — P2-1: Command Palette (Ctrl+Shift+P) [صغيرة]
- **ماذا**: لوحة أوامر فوق نمط Quick Open القائم: وحدة نقية
  `static/js/command_palette.js` (UMD-lite — سجل أوامر ساكن
  {id, label عربي, hint اختصار, action اسم دالة} + `filterCommands(query,
  commands)` ترشيح نصي بسيط + `renderListHTML(items, selected)` مع
  escapeHtml)؛ الغراء في app.js: modal جديد (نفس أصناف quick-open
  في style.css قدر الإمكان)، Ctrl+Shift+P يفتح، أسهم/Enter/Escape،
  تنفيذ = استدعاء دوال UI **القائمة فقط** (فتح لوحات Permissions/
  Settings/History، تنزيل التشخيص، مجلد جديد، جلسة جديدة، Quick Open،
  الثيم…) — **صفر endpoints جديدة** (سطح REST يبقى 33) وصفر منطق أعمال.
- **قبول آلي** (tests/unit/test_command_palette.py — نمط
  test_settings_panel): node: الترشيح (استعلام فارغ = الكل؛ جزئي؛
  لا-نتائج)، render بقيم حرفية + تهريب HTML + مؤشر التحديد، السجل
  يحوي فقط أفعالًا معرَّفة (لا سلاسل eval)؛ wiring: index.html يحمّل
  الوحدة قبل app.js + modal موجود؛ app.js يستهلك CommandPalette +
  مستمع Ctrl+Shift+P؛ نقاء الوحدة (صفر document/fetch).

## TSK-724 — P2-2: FI-09 تمرير افتراضي للمحادثات الطويلة [متوسطة]
- **ماذا**: نافذة عرض (windowing) لقائمة رسائل المحادثة — DOM ثابت
  الحجم لجلسات 1000+ رسالة: وحدة نقية `static/js/virtual_list.js`
  (حساب النافذة: `computeWindow(scrollTop, viewportH, itemHeights,
  overscan)` ⇒ {start, end, padTop, padBottom} — منطق أعمدة صرف قابل
  للاختبار في node) + غراء في app.js يستبدل الرسم الكامل بالنافذة؛
  **قيود حافظة للسلوك**: أزرار نسخ الكود وأشرطة الإجراءات تعمل داخل
  النافذة؛ البث التدفقي الحالي (TSK-401) لا يُمس — الرسالة الجارية
  تُرسم دومًا؛ التمرير لأسفل التلقائي محفوظ.
- **قبول آلي**: node لوحدة computeWindow (حدود فارغة/قصيرة/طويلة،
  overscan، ثبات المجموع padTop+حجم النافذة+padBottom)؛ wiring؛
  سيناريو يدوي موثَّق (جلسة طويلة، تمرير سلس، النسخ يعمل).
- **Prerequisite**: TSK-401 ✅ (قائم).

## TSK-725 — P2-3: Workspace Trust — بوابة ثقة عند فتح مجلد [متوسطة]
- **ماذا**: مجلد يُفتح لأول مرة = **غير موثوق افتراضيًا (fail-closed)**:
  في الوضع غير الموثوق يُجبَر سلوك interactive (كأن auto_execute=false
  وforce_command_approval=true) بصرف النظر عن config؛ قرار الثقة يُخزَّن
  في `<root>/.ai_runs/trust.json` (نمط NF-19 الذري؛ داخل IGNORED_DIRS)
  ويُقرأ عند التبديل/الإقلاع؛ الواجهة: شريط/نافذة «هل تثق بهذا المجلد؟»
  عند الفتح + شارة حالة؛ endpoint قراءة/قرار (توسيع REST 33→34/35
  يُوثَّق — POST قرار الثقة هو **كتابة قرار مستخدم صريح** لا كتابة
  config، ومسموح ضمن العقد).
- **قبول آلي**: وحدة python للتخزين (قراءة معدومة/معطوبة ⇒ غير موثوق؛
  كتابة ذرية لا-ترفع)؛ اختبار أن غير-موثوق يجبر interactive رغم
  auto_execute:true؛ frozen surface يُحدَّث موثقًا؛ عدم-تسريب مسارات.
- **يُفصَّل نهائيًا قبل التنفيذ** (نقاط الإنفاذ الدقيقة في server.py
  تتطلب جردًا — جلسة التفصيل تسبق التنفيذ، D-7).

## TSK-726 — P2-4: FI-07 تفكيك app.js إلى ES modules [كبيرة — Placeholder]
- **Placeholder مقصود** (سابقة TSK-722): يتطلب جرد ~150 دالة وخريطة
  تبعياتها أولًا؛ يُفصَّل إلى شرائح استخراج صغيرة (وحدة/جلسة) بعد
  إغلاق TSK-724 (شرط FI-07: لا تفكيك أثناء تعديل المُصيِّر).
## TSK-727 — P2-5: غلاف سطح مكتب Windows-أولًا [كبيرة — Placeholder]
- **Placeholder مقصود**: خيار التقنية (pywebview/Tauri/Electron) قرار
  معماري يحتاج موازنة مكتوبة؛ التحقق النهائي على Windows بيد المالك
  (D-8-ب — قائمة فحص تُسلَّم)؛ يُفصَّل آخر الدفعة.

## ترتيب التنفيذ (DAG بلا دورات)
723 → 724 → 726(بعد تفصيله)؛ 725 مستقلة (بعد تفصيلها النهائي)؛ 727 آخرًا.
**الأولى**: TSK-723 — جاهزيتها كاملة: نمط Quick Open قائم (app.js:3821)،
سابقة الوحدات النقية (permissions/settings panel)، معايير قبول آلية
مكتوبة، صفر تبعيات.

