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
- **Status**: TODO · **Priority**: P1
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
- **Status**: TODO · **Priority**: P1
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
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-604 — إصلاح TF-03 (اللوحات المعطلة) + TF-01 (sprite)
- **Status**: TODO · **Priority**: P1
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
- **Resume notes / Checkpoint / Blocker / Next action**: —

### TSK-605 — استعادة خضرة البوابة: TF-02 (نطاق) + TF-04 (baseline ألوان)
- **Status**: BLOCKED (ينتظر D-2) · **Priority**: P1
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

## M7 — Responsiveness & Guardrails (P2 الجذور التشغيلية)

### TSK-606 — تخييط _apply_batch والمسار المباشر (إلغاء مستجيب)
- **Status**: TODO · **Priority**: P2
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

### TSK-607 — ضم جمع سياق delegate إلى ContextBudget
- **Status**: TODO · **Priority**: P2
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

### TSK-608 — تفعيل reap_stale إنتاجيًا
- **Status**: TODO · **Priority**: P2
- **Objective**: استدعاء دوري (أو عند كل run جديد) لـ
  `ExecutionRegistry.reap_stale` كي لا تبقى خانة مشروع محجوزة بعد موت خيط.
- **Background**: RF-02 (§R5) — الآلية موجودة ومختبرة بلا مستدعٍ (execution.py:322).
- **Files**: `server.py` (نقطة تشغيل واحدة)، اختبار تكامل.
- **Acceptance**: محاكاة تذكرة يتيمة (بلا finish) → run جديد لنفس المشروع
  يُقبل بعد TTL؛ لا reap لتذاكر حية.
- **Gates**: Testing · Regression.
- **Behavior preservation**: المسارات السليمة (finally) بلا تغيير.
- **Metrics**: زمن تحرير الخانة بعد انهيار: ∞ → TTL.
- **Rollback**: revert. · **Resume notes / Blocker**: —

### TSK-609 — Instrumentation: توقيت المسارات + التوكنز
- **Status**: TODO · **Priority**: P2
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

### TSK-610 — Metrics aggregation (سجل runs بمقاييسه)
- **Status**: TODO · **Priority**: P2
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
| 602 | M6 | P1 | TODO | |
| 603 | M6 | P1 | TODO | |
| 604 | M6 | P1 | TODO | |
| 605 | M6 | P1 | BLOCKED(D-2) | TF-02 جزؤها قابل للتنفيذ فورًا |
| 606 | M7 | P2 | TODO | |
| 607 | M7 | P2 | TODO | |
| 608 | M7 | P2 | TODO | |
| 609 | M7 | P2 | TODO | |
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
