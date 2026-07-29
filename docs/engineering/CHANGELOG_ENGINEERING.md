# CHANGELOG_ENGINEERING.md — editor_v4 (Stage 3 EXECUTION)

> سجل تغييرات هندسي لكل مهمة TSK مُغلقة في Stage 3 (الدستور §12).
> append-only — لا حذف ولا إعادة صياغة لمدخلات سابقة.
> المرجع التفصيلي: DEVELOPMENT_TASKS.md (سجل المهمة) + MASTER_REVIEW.md (الخلفية).

---

## [TSK-601] — 2026-07-28 (Sessions 33–34) — إصلاح اعتماد التفويض

**العائلات المُغلقة**: RP-01 (§R7) · UXF-02 جزئيًا (§R9 — هذا المسار) · TD-01 (§R10)

### Fixed
- `delegate_approve` (server.py): كان ينادي `parser.extract_actions` /
  `parser.extract_options` — دالتين **غير موجودتين** في ResponseParser —
  فيُبتلع AttributeError ويصل الواجهةَ دائمًا `done` بـ `actions=[]`
  (اعتماد التفويض معطّل بصمت منذ إنشائه). الآن: `parser.parse()` الحقيقية
  + التحويل المشترك.
- فشل تحويل رد التفويض لم يعد صامتًا: إطار `error` بنص السبب يصل الواجهة
  قبل fallback الـ `done` الفارغ (كان print فقط في stdout الخادم).

### Changed
- استخراج `_parsed_to_actions(parsed)` + `_parsed_options(parsed)`
  (server.py:1439–1474): التحويل ParsedResponse→actions كان مكررًا حرفيًا
  في مساري agent وdirect — الآن دالة واحدة يستهلكها المساران + مقبض
  الاعتماد. لا API جديد ولا تغيير في شكل أي إطار قائم.

### Added
- `tests/integration/test_delegate_approve_handler.py` — أول تغطية للمقبض
  (كانت صفرًا — TD-01): 6 حالات E2E عبر `_handle_ws_message` بجسر تفويض
  حقيقي يقوده FakeProvider (دورة brief→implement→review→approve كاملة)،
  تشمل golden للـ actions، حالة بلا actions، إظهار فشل التحويل، الهبوط
  الفعلي، وحارسًا بنيويًا دائمًا ضد عودة الدالتين الوهميتين.

### Verification
- الاختبارات الجديدة: 6/6 خضراء.
- Regression كامل (Session 34): `4 failed, 1677 passed, 34 skipped` (~70s) —
  مجموعة الفشل هي الأربعة المعروفة قبل المهمة حرفيًا (test_file_icons /
  test_history_consumers / test_rollback_ui / test_theme_tokens — تعالجها
  TSK-604/605)؛ لا فشل جديد.
- `grep -c "extract_actions\|extract_options" server.py` = **0**.

---

## [TSK-602] — 2026-07-28 (Sessions 35–36) — تسييج نتائج الأدوات والمعرفة

**العائلة المُغلقة**: ASF-01 (§R4 — Context poisoning عبر نتائج الأدوات)

### Fixed
- نتائج الأدوات كانت تُحقن **خامًا** في برومبت متابعة الوكيل
  (`[نتيجة {tool}(...)]:\n{نص}` — chain/agent_loop.py، موضعا الأدوات
  الآمنة والأوامر المعتمدة) وكذلك أجساد المعرفة المجمعة
  (chain/knowledge.py `_render_body` بأنواعه الأربعة + `to_summary`) —
  أي ملف/مخرجات أمر تحوي تعليمات عدائية ("IGNORE ALL INSTRUCTIONS")
  كانت تصل الموديل كأنها جزء من التعليمات.

### Changed
- كل موضع حقن يمر الآن عبر `fence_attached` القائمة (prompts/templates.py
  — الآلية المختبرة TSK-404/QA-T12) بمصدر موسوم لكل نوع:
  `tool_result:{tool}` / `file:` / `dir:` / `search:` / `command:`.
- رؤوس الأقسام (`📂 [ملفات تم قراءتها]`، `--- display ---`، …) تبقى خارج
  السور — بنية البرومبت محفوظة؛ المحتوى الخارجي وحده داخل الأغلفة.
- موضع `_build_followup_prompt` الثالث مُغطى بالتعدي عند المصدر —
  لا تسييج مزدوج.

### Added
- `tests/unit/test_context_fencing.py` — 6 حالات: E2E بملف مسموم عبر
  AgentLoop+FakeProvider (فحص spans: التعليمة العدائية داخل السور حصرًا)،
  أوسمة المصدر للأنواع الأربعة، تسييج to_summary، تحييد وسم إغلاق مزوّر،
  وحارسان بنيويان (grep-assert) ضد عودة الحقن الخام.

### Verification
- الاختبارات الجديدة 6/6 + QA-T12 + test_knowledge_bundle +
  test_agent_feedback كلها خضراء (47 اختبارًا في نطاق الأثر).
- Regression كامل (Session 36): `4 failed, 1683 passed, 34 skipped` (~72s)
  — الأربعة المعروفة فقط (TSK-604/605)؛ لا فشل جديد.

---

## TSK-603 — بوابة موافقة fail-closed بنيويًا (ASF-02 · ALT-603→A) — Session 37

### Fixed
- **ASF-02**: `tool_run_command` كان ينفّذ أي أمر بلا بوابة إن استُدعي
  مباشرة — `need_approval=False` حرفيًا في نداء `cmd.run`
  (chain/agent_tools.py) والمسار المُدقَّق الوحيد كان بوابة الحلقة
  (ApprovalGate) القائمة على «انضباط المستدعي» لا على بنية الكود.

### Changed
- التنفيذ الآن يتطلب رمز قرار **sentinel** وحدويًا
  (`APPROVAL_GRANTED = object()` — يُقارَن بـ `is`): لا يمكن لنص AI
  إنتاجه، فلا تزوير موافقة عبر بلوك TOOL.
- `AgentTools.execute(call, approved=False)`: يسقط أي مفتاح `_approval`
  قادم من وسائط النص، ويحقن الكائن الحارس فقط عند `approved=True`
  لأدوات APPROVAL_TOOLS.
- `AgentLoop` (فرع الموافقة :249): يمرر قراره صراحة —
  `execute(call, approved=True)` بعد حكم ApprovalGate. سلوك الحلقة
  محفوظ حرفيًا.
- نداء مباشر بلا الرمز → رفض مهيكل «❌ رفض بنيوي…» + WARNING مسجَّل،
  قبل أي فحص allowlist — لا تنفيذ صامت أبدًا.
- `need_approval=False` المتبقي في `cmd.run` موثق بتعليق TSK-603
  (صحيح بالبناء: القرار حُسم أعلاه؛ بوابة CommandRunner الكونسولية
  `input()` غير صالحة لخادم ويب — auto_approve=True يحيّدها أصلًا في
  مواضع الخادم الثلاثة).

### Added
- 7 اختبارات في `tests/integration/test_agent_gated_approvals.py`:
  TestFailClosedToolLayer ×5 (نداء مباشر مرفوض؛ تزوير نصي/كائن غريب؛
  إسقاط `_approval` المزوّر من بلوك TOOL؛ تعاقد الحلقة ينفّذ؛
  SAFE_TOOLS غير متأثرة) + حارسان بنيويان
  (`test_no_undocumented_need_approval_false`،
  `test_sentinel_wiring_structural`).
- تحديث 21 نداءً مباشرًا في الاختبارات القائمة
  (test_run_command ×20، test_agent_feedback ×1) لتمرير الرمز الصريح.

### Verification
- نطاق الأثر: 65 اختبارًا أخضر (gated_approvals + run_command +
  agent_feedback + force_approval).
- Regression كامل (Session 37): `4 failed, 1690 passed, 34 skipped`
  (~71s) — الأربعة المعروفة فقط (TSK-604/605)؛ لا فشل جديد؛ +7 اختبارات.
- Metrics: مسارات تنفيذ أمر بلا بوابة 1 → 0.

---

## TSK-604 — إصلاح TF-03 (اللوحات المعطلة) + TF-01 (sprite) — Sessions 38–39

### Fixed
- **TF-03 (عيب C3/S2 حي)**: v25 حذفت عنصرَي `id="run-history-btn"`
  و`id="memory-panel-btn"` من index.html بينما app.js:3639–3641 يربطهما
  في DOMContentLoaded ⇒ TypeError يقطع المعالج: لوحتا Run-History
  وMemory معطلتا الفتح، status-chip غير مربوطة، refreshCapacity
  والاستطلاع الدوري لا يبدآن، وأزرار Activity Bar ترمي عند النقر.
- **TF-01**: إعادة كتابة sprite.svg (v25) أسقطت عبارة «رخصة المشروع»
  التي يثبّتها test_file_icons.py:143.

### Changed
- `static/index.html`: زرا وكيلان مخفيان (`class="hidden"`) بتعليق
  TSK-604 — أهداف ربط app.js وتفويض Activity Bar `.click()` القائم
  (:212/:220)؛ بلا تغيير مرئي وبلا لمس app.js (إصلاح الجذر لا العرض؛
  إعطاء زري Activity Bar المعرفين مباشرة كان سيخلق استدعاء `.click()`
  ذاتيًا لا نهائيًا).
- `static/icons/sprite.svg`: سطر «رخصة المشروع نفسها — لا مجموعة
  خارجية» أُعيد لتعليق الرأس — صفر أثر تنفيذي.

### Verification
- القبول: `pytest tests/unit/test_rollback_ui.py
  tests/unit/test_file_icons.py` → **25 passed** كاملًا.
- فحص يدوي موثق (خادم حي port 5000 + متصفح Playwright): الصفحة تُحمّل
  بصفر أخطاء JS (الأثر الوحيد favicon.ico 404 موروث غير ذي صلة)؛
  /api/capacity يُستطلع (200) — دليل اكتمال معالج DOMContentLoaded
  الذي كان ينقطع قبل الإصلاح؛ تحقق سكوني: المعرفات الثلاثة مربوطة
  وموجودة + دوال toggle* الثلاث + وكيلا Activity Bar سليمان.
- Regression كامل (Session 39): `3 failed, 1692 passed, 33 skipped`
  (~72s) — منها test_search_perf فشل عابر تحت حمل التوازي (معزولًا
  18/18 ✅)؛ الفشلان الدائمان المتبقيان (test_history_consumers +
  test_theme_tokens) ملك TSK-605 حصرًا.
- Metrics: إخفاقات البوابة المعروفة **4 → 2**.

---

## TSK-605 — جزء TF-02: تصحيح نطاق حارس التاريخ — Session 40 (جزئي)

### Fixed
- **TF-02**: حارس test_history_consumers::test_no_raw_history_slices_outside_sessions
  كان يمسح `providers/` رغم أن طبقة المزودات خارج النطاق كليًا (§0.8) —
  الانتهاك الوحيد (providers/openai_shelby.py:105 — `history[-6:]`)
  ضجيج مزودات لا انحدار core، وكان يُبقي البوابة حمراء دائمًا.

### Changed
- `tests/unit/test_history_consumers.py:229`: إخراج `providers` من
  قائمة المسح بتعليق معلّل موثّق (تصحيح نطاق لا إضعاف — تغطية core
  الكاملة chain/core/context/actions/prompts/server.py محفوظة كما هي؛
  لا مساس بأي ملف إنتاج ولا بـ providers/).

### Verification
- test_history_consumers → **41 passed** كاملًا.
- Regression كامل (Session 40): `1 failed, 1693 passed, 34 skipped`
  (~72s) — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بقرار
  المالك D-2)؛ فشل test_search_perf العابر (S39) لم يتكرر.
- Metrics: إخفاقات البوابة **2 → 1**.

### Pending
- TF-04 ينتظر D-2 — عند الرد: baseline-allowlist مؤرَّخ + سطر دين في
  TECHNICAL_DEBT.md ⇒ `pytest tests` = 0 failed (أول خضرة كاملة).

---

## TSK-606 — تخييط _apply_batch والمسار المباشر (إلغاء مستجيب) — Session 43

### Fixed
- **RF-01 + RP-02 + UXF-03**: `cancel_run` من نفس الاتصال أثناء دفعة
  apply أو رد direct كان مستحيلًا بنيويًا — `_handle_ws_message` كانت
  تنفّذهما متزامنَين على خيط حلقة استقبال WS فلا يُقرأ أي إطار تالٍ
  (بما فيه الإلغاء) قبل الاكتمال. آلية الإلغاء التعاوني نفسها كانت
  موجودة منذ TSK-304 بلا جدوى من نفس الاتصال.
- **اكتشاف جانبي (BUG)**: معالج `cancel_run` (server.py) كان يمرر
  `ensure_ascii=False` لـ `sctx.send` وتوقيعه `Callable[[dict], None]`
  → TypeError عند أول cancel_run حقيقي عبر WS. أُزيل الوسيط الدخيل.

### Changed
- `server.py`: نداء `_apply_batch` صار على خيط daemon باسم
  `runner-apply-batch`؛ بلوك direct runner انتقل لدالة `_run_direct`
  على خيط `runner-direct-{run_id}` (إطار start + فحص busy بقيا
  متزامنين — ترتيب الإطارات محفوظ). نفس نمط خيوط chain/agent/delegate
  حرفيًا — `_apply_batch` نفسها لم تُمس.
- `tests/integration/test_apply_batch_golden.py`: الـ harness يَـjoin
  خيط الدفعة قبل قراءة الإطارات — ملف الـ golden JSON **بلا تغيير**.
- `tests/integration/test_apply_cancel.py`: +2 اختبارات
  (TestSameConnectionCancel) — معيار القبول الحرفي: cancel_run أثناء
  دفعة 20-action من نفس الاتصال يوقفها عند 5/20 مع إقرار
  acknowledged=True أثناء الدفعة؛ + اختبار التحرر البنيوي للحلقة.

### Verification
- الملفان المستهدفان: **11 passed** (منها goldens QA-T08 مطابقة).
- بوابة العمارة: `scripts/lint_handler_state.py` → clean.
- Performance: أول task_progress بعد التخييط وسيط 0.18ms / p95
  0.28ms (20 عينة) — لا تدهور.
- Regression كامل (Session 43): `1 failed, 1695 passed, 34 skipped`
  (~71s) — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بـ D-2).
- Metrics: استجابة cancel أثناء دفعة من نفس الاتصال:
  **مستحيل → ≤ خطوة واحدة** (الهدف حرفيًا).

---

## TSK-607 — ضم جمع سياق delegate إلى ContextBudget — Sessions 45–46

### Fixed
- **RP-03 (§R7)**: معالج `delegate_message` كان يقرأ أول 10 ملفات من
  `scan_project()` **كاملة بلا أي سقف** ويمررها لـ
  `DelegateBridge.write_brief` الذي يُلحقها حرفيًا في البريف — آخر
  جيب برومبت خارج توحيد الميزانية (T-024/TSK-103): تضخم غير مسقوف
  مع المشاريع الكبيرة.

### Changed
- `server.py`: دالة وحدوية نقية `_budget_delegate_files` — كل ملف
  `BudgetItem` بطبقة high تحت `ContextBudget.from_config`
  (config.yaml:context_budget — نفس السقف المركزي)؛ كامل-أو-إسقاط
  (لا قصّ منتصف)، الأكبر أولًا عند الفيض؛ أي إسقاط يضيف وسمًا ظاهرًا
  (`DELEGATE_DROP_MARKER_KEY`) داخل files_context يصل البريف + سطر
  log «⚖️ ContextBudget (delegate)» — لا تدهور صامت. موصولة في
  المعالج بعد الجمع مباشرة.
- `tests/unit/test_budget_wiring.py`: +6 اختبارات
  (TestDelegateFilesBudget) — حفظ السلوك بايت-بايت للمشاريع الصغيرة،
  فارغ، إسقاط الأكبر أولًا + وسم ظاهر، لا بتر منتصف، الحمولة ≤ السقف
  (معيار القبول)، حفظ ترتيب الإدراج.

### Verification
- test_budget_wiring → **30 passed** كاملًا؛ ملفات التأثير
  (delegate_approve + context_budget + injection_budget) 76/76.
- بوابة العمارة: lint_handler_state → clean.
- Performance: 0.03ms/نداء (شاملًا قراءة config) — لا أثر.
- Regression كامل (Session 45): `1 failed, 1701 passed, 34 skipped`
  (~72s) — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بـ D-2).
- Metrics: حجم برومبت delegate الأقصى: **غير مسقوف → ≤ budget_tokens
  المركزي**.

---

## TSK-608 — تفعيل reap_stale إنتاجيًا — Sessions 47–48

### Fixed
- **RF-02 (§R5)**: `ExecutionRegistry.reap_stale` كانت موجودة ومختبرة
  **بلا أي مستدعٍ إنتاجي** (execution.py:322) — خيط runner يموت دون
  `finish()` كان يحجز خانة مشروعه للأبد (busy دائم حتى إعادة تشغيل
  الخادم). كذلك `ticket.heartbeat()` كان بلا مستدعٍ إنتاجي —
  `_last_heartbeat` تبقى = `created_at` فأي TTL ساذج كان سيحصد
  الـ runs الحية الطويلة زورًا.

### Changed
- `core/backends.py`: `resolve_stale_ttl` (تحقق صارم — غائب = 900s،
  null = تعطيل، غير صالح = فشل إقلاع صاخب) + وسيط `ttl_seconds`
  اختياري في `backends_from_config` (الافتراضي None = التاريخي
  بايت-بايت — اختبار الثبات القائم يمر بلا تعديل).
- `server.py`: الإقلاع يمرر `resolve_stale_ttl(cfg.execution)` للدرزة؛
  `_begin_run_ticket` يستدعي `reap_stale()` قبل `purge_terminal()`
  (نفس نمط TSK-303 — أرخص نقطة تغطي كل الأنواع) + log لكل محصودة؛
  **نبض الحياة**: `_RunnerWSAdapter.emit` ينبض تذكرة كل حدث
  (chain/agent/direct/delegate)، `_apply_batch` ينبض لكل action،
  ومسار resume يغلّف إرساله بنبضة.
- `config.yaml`: قسم `execution.stale_ttl_seconds: 900` موثّق.

### Verification
- `tests/integration/test_reap_stale_wiring.py` جديد → **17 passed**
  (معيار القبول الحرفي: يتيمة → بديلتها تُقبل بعد TTL؛ حية تنبض لا
  تُحصد؛ null = السلوك القديم حرفيًا).
- عدة التأثير 108/108 (backends/execution/purge/slot/ws_run_control/
  ticket_cancellation/apply_cancel/apply_batch_golden/concurrent_guard/
  dispatch_parity) — goldens بلا تغيير.
- بوابة العمارة: lint_handler_state → clean.
- Performance: reap+purge 0.0066ms/تسجيل؛ نبضة المحوّل 0.0008ms/حدث.
- Regression كامل (S47 وS48 على merged): `1 failed, 1718 passed,
  34 skipped` (~72s) — المتبقي الوحيد test_theme_tokens (TF-04 —
  محجوب بـ D-2).
- Metrics: زمن تحرير خانة المشروع بعد انهيار خيط: **∞ → ≤ TTL (900s)**.
- قيد موثّق: delegate في `waiting_approval` الصامت > TTL يُحصد وتتحرر
  الخانة؛ land/reject اللاحقان آمنان (finish no-op على المحصودة).

---

## TSK-609 — Instrumentation: توقيت المسارات + التوكنز — Sessions 49–54

### Fixed
- **PM-02 (§R6)**: صفر قياس زمن للمسارات direct/agent/delegate —
  chain وحده كان يقيس (executor.py:352). الآن الأربعة تبث
  `duration_ms` في حدث `run_finished` (bus الرصد) — تغطية 1/4 → 4/4.
- **PM-04 (§R6)**: لا توقيت لكل مصدر في ContextBuilder — الآن
  `ContextEngine.gather` يوقّت `collect` لكل مصدر (حتى الفاشل).
- **PM-01 (§R6)**: لا تقدير توكنز للمخرج — الآن `token_estimate`
  (المقدّر المركزي `CharsPerTokenEstimator`، chars÷4 — لا ثوابت
  جديدة) على إطاري `plan`/`done`.

### Changed
- `runners/direct.py` / `runners/agent.py` / `runners/delegate.py`:
  `_t0 = time.monotonic()` بعد `stream.started()`؛
  `_finish(..., started_at)` يضيف `duration_ms` لبيانات
  `stream.finished` (نفس نمط chain) — كل مواضع النداء (7+6+6) مُرّرت.
- `context/engine.py` + `context/bundle.py`:
  `ContextBundle.source_timings_ms` (kind → ms) يملؤه gather.
- `context/facade.py`: `MessageContext.source_timings_ms` — حقل
  افتراضي **بـ `compare=False`** (انحراف موثّق: 4 اختبارات parity
  قائمة تقارن MessageContext بالمساواة الكاملة والتوقيت غير حتمي —
  الرصد لا يغيّر دلالات المساواة).
- `server.py`: إغلاقا `_run_direct`/`_run_agent` يوقّتان النداء
  محليًا (RunResult مجمّد) ويضيفان `duration_ms` + `token_estimate`
  لإطاري `plan`/`done` — حقول إضافية فقط (الواجهة تتجاهل المجهول).

### Verification
- `tests/integration/test_instrumentation_609.py` جديد → **11 passed**
  (معيار القبول الحرفي: إطار finished/done يحمل duration_ms
  وtoken_estimate للمسارات الثلاثة؛ goldens بحقل إضافي فقط).
- contracts + dispatch_parity + goldens: 142 passed — `run_finished`
  لا يُنتج إطار WS (المحوّل يعيد مبكرًا) والعقود تفحص بالمفتاح.
- بوابة العمارة: lint_handler_state → clean.
- Performance: عبء التوقيت ≈ 173ns × ~14 نداء monotonic/رسالة =
  ميكروثوانٍ؛ gather_message_context ≈ 20.6ms/نداء — لا تدهور.
- Regression كامل (S53): `1 failed, 1729 passed, 34 skipped` (~70s)
  — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بـ D-2)؛
  1718 + 11 = 1729 ✓.
- Metrics: تغطية قياس المدة: **1/4 مسارات → 4/4**.

## TSK-610 — Metrics aggregation: سجل runs بمقاييسه — Sessions 55–57

### Fixed
- **PM-03 (§R6)**: القياسات لحظية «تُبث وتُنسى» (MASTER_REVIEW.md:433)
  — بعد TSK-609 كل مسار يبث `duration_ms` على bus الرصد لكن لا مشترك
  يجمعها. الآن: سجل JSONL دائم لكل run منتهٍ + ملخّص p50/p95 —
  أساس تاريخي لرصد تدهور الأداء بين الإصدارات.

### Added
- `core/run_metrics.py` (وحدة نقية جديدة — تُختبر بلا Flask):
  - `RunMetricsStore`: JSONL ملحق-فقط (نمط ProjectMemoryStore)؛
    قارئ يتخطى الأسطر الممزّقة؛ `percentile` nearest-rank (بلا
    تبعيات جديدة)؛ `summary()` — count + status_counts + p50/p95
    كليًا ولكل mode (سقف قراءة 5000 سطرًا).
  - `RunMetricsRecorder`: مشترك قابل للنداء على bus الرصد — يقرن
    RunStarted↔RunFinished بمفتاح run_id (OrderedDict بسقف 256،
    أقدم-يُطرد)؛ finished يتيم → حقول فارغة (لا اختراع)؛ فشل
    الكتابة يُبتلع مع log (NF-14 — الـ run لا يتأثر أبدًا).
- `server.py`: global `run_metrics_store` + REST قراءة
  `/api/metrics/runs` (503 قبل التهيئة) + البناء والاشتراك في
  main() (composition root فقط) — الملف `metrics/runs.jsonl`
  (قرار موثّق: ملف واحد على مستوى التطبيق + حقل project_id —
  RunFinished لا يحمل هوية مشروع).

### Deviation (موثّق في §TSK-610)
- «حجم سياق» في نص الهدف: لا ناشر لـ `context_chars`/`project_id`
  على RunStarted اليوم (الـ runners تبث mode فقط) — يُسجَّلان None
  ويُلتقطان تلقائيًا متى نُشرا (خارج نطاق «إضافة صرفة» هنا).

### Verification
- `tests/unit/test_run_metrics.py` جديد → **17 passed** — يشمل
  معيار القبول الحرفي («3 runs → 3 أسطر صالحة») وp50/p95 بقيم
  معلومة يدويًا (nearest-rank على [100,200,300,400,1000]:
  p50=300/p95=1000) + e2e مصغّر بـ DirectRunner حقيقي (تقاطع
  609↔610: المدة الحقيقية تصل السجل).
- contracts + dispatch_parity: 113 passed؛ goldens + اختبارات
  609: 50 passed؛ lint_handler_state → clean.
- Performance: `store.append` ≈ 0.039ms/سجل (متوسط 1000)؛
  `summary()` على 1001 سجل ≈ 11.4ms (REST قراءة عند الطلب فقط).
- Regression كامل (S57): `1 failed, 1746 passed, 34 skipped` (~69s)
  — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بـ D-2)؛
  1729 + 17 = 1746 ✓.
- Metrics: سجل runs التاريخي: **لا شيء → JSONL لكل run + p50/p95**.

## TSK-611 — QG-01: استخراج راوتر WS إلى جدول dispatch — Sessions 58–60

### Added
- `docs/engineering/ARCHITECTURE_DECISIONS.md` (جديد — أول ADR):
  **ADR-001** — راوتر WS بجدول dispatch في وحدة نقية، المقابض تبقى
  مؤقتًا في server.py (بدائل مرفوضة: نقل الأجسام الآن / راوتر صنفي /
  تقسيم داخلي بلا فصل).
- `docs/engineering/DECISION_LOG.md` (جديد — يُنشأ عند أول ADR في M8
  وفق MASTER_ROADMAP:127) + قيد TSK-611 **قبل تعديل الكود**
  (الدستور :1038).
- `core/ws_router.py` (جديد): `dispatch(handlers, ctx, sctx, msg)` —
  بحث قاموسي بـ `msg.get("type", "")`؛ نوع مجهول = no-op صامت
  (حفظ حرفي)؛ بلا استيراد server/Flask.
- `tests/unit/test_ws_router.py` (+10): dispatch النقية (5) + جدول
  server (5 — تجميد المفاتيح على الأنواع الـ25 الأصلية، تشارك
  المقبض للمركّبات بالهوية، pong bit-identical، نوع مجهول صامت).

### Changed
- `server.py`: الفروع الـ23 (‏506 أسطر — :2034..2539) استُخرجت آليًا
  إلى 23 دالة `_ws_<type>(ctx, sctx, msg)` بأجسام حرفية + جدول
  `WS_HANDLERS` (25 مفتاحًا)؛ `_handle_ws_message` صار غلافًا
  (‏**506 → 13 سطرًا، −493 ≥ 300 ✓**) يستدعي `ws_dispatch`.
- `scripts/lint_handler_state.py`: بادئة `"_ws_"` في HANDLER_NAMES —
  قاعدة T-048 تتبع المقابض المستخرجة (fixture الانتهاك ما يزال
  يفشل exit 1 ✓).
- فحصان بنيويان حُدّثا لنفس الضمانات على البنية الجديدة:
  `test_scan_start.py` (جسم `_ws_chain_message` بدل regex السلسلة)
  و`test_rollback_ui.py` (مفتاحا rollback → مقبض مشترك).

### Deviations (موثقة في §TSK-611)
- الكتلة الفعلية 506 أسطر (النص: ~469)؛ 23 فرعًا/25 نوعًا (النص: 16)؛
  «goldens routing» في القبول = توجيه استراتيجية السلسلة لا WS —
  فُسِّر: goldens القائمة + 8 ملفات اختبار مثبّتة لسلوك WS +
  اختبار جدول جديد يغلق الفجوة.

### Verification
- goldens (chain replay + apply_batch + routing): **22 passed**؛
  contracts + dispatch_parity: **113 passed**؛
  `lint_handler_state.py` → clean (بنطاق موسّع).
- Regression كامل (S60): `1 failed, 1756 passed, 34 skipped` (72.9s)
  — المتبقي الوحيد test_theme_tokens (TF-04 — محجوب بـ D-2)؛
  1746 + 10 = 1756 ✓.
- Metrics: كتلة التوجيه **506 → 13** (−493)؛ server.py إجمالًا
  2987 → 3045 (+58 توقيعات/جدول — ينخفض في QG-02..04)؛ صفر تغيير
  في أي إطار.

## TSK-612 — QG-02: استخراج مسار الإرسال إلى chat_dispatch — Sessions 61–63

### Added
- `docs/engineering/ARCHITECTURE_DECISIONS.md` → **ADR-002**: استخراج
  `_dispatch_chat_message` بحقن التبعيات وقت النداء (deps يُبنى في
  الغلاف من فضاء server عند كل استدعاء — يحفظ monkeypatch الاختبارات
  الأربعة على server وقراءة request_router/agent_tools المربوطين في
  main())؛ + قيد DECISION_LOG — كلاهما **قبل الكود** (الدستور :1038).
- `core/chat_dispatch.py` (513 سطرًا): جسم الدالة حرفيًا (تحقق آلي
  سطرًا-بسطر — الفرق الوحيد إدراج `deps.` خارج النصوص) كـ
  `dispatch_chat_message(deps, ctx, sctx, …)`؛ لا استيراد server.

### Changed
- `server.py`: `_dispatch_chat_message` صار غلافًا (نفس الاسم/التوقيع)
  يرسل scan_start الفوري ثم يبني deps وقت النداء —
  **3045 → 2596 سطرًا (−449 صافيًا)**.
- 4 فحوص بنيوية حُدّثت لنفس الضمانات في الموقع الجديد:
  prompt_fencing (تسييج detected_file)، context_engine (النداء
  الموحّد على الملفين)، config_consolidation (تعريف أعلى-مستوى
  فقط)، run_slot_per_project (مواضع _begin_run_ticket على الملفين).

### Verification
- mypy على الوحدة الجديدة **نظيف** (ونطاق core/+chain/+context/+
  sessions/ كاملًا 62 ملفًا — خطأ providers/openai_shelby.py:166
  قائم مسبقًا وخارج النطاق §0.8، الملف لم يُمس).
- goldens (chain+apply_batch+routing+ws_router): 32؛ contracts+
  dispatch_parity: 113؛ الملفات السبعة المثبّتة للمسار: 76؛
  lint_handler_state → clean.
- Regression (junitxml): **1791 = 1 failed، 1756 passed، 34 skipped**
  (69.8s) — الإخفاق الوحيد theme_tokens (TF-04/D-2)؛ لا انحدار.
- Metrics: الكتلة 486 → غلاف ~37؛ صفر تغيير في أي إطار.

## TSK-613 — QG-03: تجميع REST routes في blueprints — Sessions 64–67

### Added
- حزمة `routes/` (8 ملفات، 633 سطرًا): 7 blueprints موضوعية —
  files (8 routes)، backups (2)، run (3)، sessions (6)، meta (3)،
  rollback (2)، project (1) — أجسام **حرفية** من server.py (تحقق
  آلي 25/25 دالة، 0 فروق)؛ نمط `register(app, srv)` بحقن كائن وحدة
  server وقراءة حيّة `_srv.fm`… وقت النداء (ADR-003 — يحيّد خطر
  «تجميد ازدواجية g5»؛ إعادة ربط globals = تعيين سمة مكافئ حرفيًا).
- ADR-003 + قيد DECISION_LOG (قبل الكود — الدستور :1038).
- `tests/unit/test_rest_blueprints.py` (+21): تجميد url_map الثلاثين
  حرفيًا + smoke لا-404/405 + الحقن الحي/إعادة الربط + لا دورة.

### Changed
- server.py: **2596 → 2118 (−478)** — حذف 25 دالة route + كتلة تسجيل
  blueprints؛ تبقى index + api_models + api_switch_model (§0.8
  provider-routing — لا تُلمس) والمساعدات المشتركة.
- 4 فحوص بنيوية → نفس الضمانات في الموقع الجديد: force_approval
  (server+routes/run، 3 مواضع)، search_perf (routes/files)،
  rollback_ui (routes/rollback GET-only)، capacity_model (+routes/
  في بوابة MIN_ACCOUNTS — تقوية).

### Verification
- تكافؤ سلوكي: smoke 28 حالة HTTP قبل/بعد متطابق 28/28؛ url_map
  30 قاعدة bit-identical (معيار القبول «عدد routes ثابت» ✓).
- Gates: mypy نظيف **70 ملفًا** (يشمل routes/) · lint clean ·
  contracts+parity 113 · goldens 32 · عدة التأثير 89/89.
- Regression (junitxml): **1812 = 1 failed، 1777 passed، 34 skipped**
  (73.0s) — الإخفاق الوحيد theme_tokens (TF-04/D-2)؛ 1791+21=1812 ✓.
- انحرافات موثَّقة: 25 منقولة ≠ «27» النصية (28 فعليًا − 3 باقية)؛
  لا memory blueprint (لا memory REST — عبر WS فقط).

## TSK-614 — QG-04: توسيع بوابة mypy إلى routes/ + server.py — Sessions 69–70

### Added
- `tests/unit/test_mypy_gate_614.py` (10 اختبارات): بنية سطر البوابة؛
  **الاختبار السلبي الموثق** (نداء مدسوس في def غير مُعنون = exit 1
  بأعلام البوابة / يفلت بدونها)؛ NF-25 (حقن واستهلاك deps + فحص AST)؛
  NF-26 وظيفيًا (attach يسلّم محتوى مسيَّجًا + سقف 15).
- ADR-004 + قيد DECISION_LOG (قبل الكود): تصميم البوابة —
  `--check-untyped-defs` (بدونه أجسام غير مُعنونة لا تُفحص والقبول
  يسقط) + استبعاد `providers/openai_shelby.py` وحده (خطأ قائم §0.8).
- `RegistryBackend.purge_terminal` في العقد (core/backends.py) —
  السطح مستخدم فعليًا منذ TSK-303.

### Changed
- `scripts/check.sh`: سطر البوابة الجديد (علم + استبعاد + نطاق كامل).
- تعنوينات لا-سلوكية: `_srv: Any` في 7 ملفات routes (يصفّر 79 خطأ)؛
  16 sentinel `# type: ignore[assignment]` + `RUNNERS`/`frame`/`cfg`/
  `provider_config`/`provider` في server.py (يصفّر 28).
- **إصلاح NF-25** (انحدار TSK-612): `provider_pool`/`approval_gate`
  حُقنا في deps واستُهلكا عبر `deps.` — مسار agent عبر dispatch كان
  يرمي NameError.
- **إصلاح NF-26** (قائم منذ 0d74dad): استهلاك dict الصحيح في attach
  المجلد (`list(scanned_files.items())[:15]`) — كان يتدهور صامتًا.

### Verification
- mypy بسطر البوابة: **Success — 81 ملفًا، exit=0**؛ الاختبار السلبي
  زُرع فعليًا في routes/meta.py → exit=1 ثم استُعيد.
- check.sh: أخضر حتى color lint (TF-04/D-2 المعروف حصرًا).
- contracts+parity 113 · goldens+ws_router 32 · متأثرة 104 · lint
  نظيف · Regression junitxml: **1822 = 1F/1787P/34S** (69.7s؛
  theme_tokens حصرًا؛ 1812+10=1822 ✓).

## TSK-615 — ApprovalGate: طلبات متزامنة (ASF-05/NF-27) — Session 71

### Added
- `core/approval.py`: `_PendingEntry` (dataclass — hash/Event/result/reason
  لكل طلب) + `pending_request_ids()` (جمع المعلّقين، الأقدم أولًا).
- `tests/unit/test_approval_concurrent.py`: 9 اختبارات تزامن (حلّ مستقل،
  لا موافقة زائفة NF-27، حلّ الأقدم ASF-05، مهلة لكل طلب، رفض hash
  متقاطع، نسبة تدقيق صحيحة، حفظ سلوك الطلب الواحد).

### Changed
- `core/approval.py`: الخانة المفردة (`_pending_id` + Event مشترك)
  استُبدلت بخريطة `request_id → _PendingEntry`؛ `_interactive` يسجّل
  مدخلًا مستقلًا ويزيله في finally (لا تصفير جماعي/تسرّب)؛ `resolve`
  يطابق مدخل الخريطة (id + hash)؛ `pending_request_id()` يرجع الأحدث
  (سلوك مطابق مع ≤1 معلّق). التواقيع العامة بلا تغيير — صفر تعديل في
  bridge/agent_loop/runners/server.

### Verification
- تجربة حية قبل/بعد: سيناريو A (اعتماد r2 كان يعتمد r1 زورًا — NF-27
  fail-OPEN) وB (حلّ الأول مستحيل — استنزاف ASF-05) وC (تلويث تدقيق)
  كلها مُصلحة؛ D (رد متأخر مرفوض) محفوظ.
- test_approval.py الـ19 القائمة تمر **بلا تعديل** · pyflakes نظيف ·
  lint_handler_state نظيف · contracts+parity 113 · goldens+ws_router 32 ·
  بوابة mypy: Success 81 ملفًا · Regression junitxml:
  **1831 = 1F/1796P/34S** (79.9s؛ theme_tokens/TF-04 حصرًا؛ 1822+9=1831 ✓).

---

## TSK-616 — إظهار سقف snapshot (rollback جزئي — ASF-03) — Session 72

**العائلة المُغلقة**: ASF-03 (§R4 — «الإصلاح: إظهار لا رفع سقف» MASTER_REVIEW:722)

### Fixed
- اقتطاع مسح snapshot لم يعد صامتًا: `_workspace_signatures` كانت تعيد
  dict فقط وتُسقط معلومة بلوغ `_CKPT_MAX_FILES` (return مبكر) أو تخطي
  ملف فوق `_CKPT_MAX_FILE_BYTES` (continue) — أمر معتمد يلمس >400 ملف
  كان يحصل على rollback جزئي **بصمت**، وسطر `🧷 [checkpoint]` القائم
  كان مضلِّلًا إيجابيًا (يوحي بتغطية كاملة).

### Changed
- `chain/agent_tools.py`: `_workspace_signatures` → `tuple[dict, bool]`
  و`_changed_paths` → `tuple[list, bool]` (علم الاقتطاع يُشتق حيث تحدث
  الحقيقة — دالتان خاصتان بلا مستهلك خارجي)؛ `tool_run_command` يرفع
  `self.last_partial_rollback` + `_LOG.warning` + سطر ⚠️ عربي صريح في
  التقرير («التراجع عن آثار هذا الأمر سيكون جزئيًا» مع قيم السقفين) —
  خارج `if changed:` عمدًا (تغييرات فوق السقف غير مرئية للمقارنة أصلًا).
  السقفان نفساهما لم يتغيرا (إظهار لا رفع).
- `chain/agent_loop.py`: إطار `agent_step/done` للمسار المعتمد يحمل
  حقل `partial_rollback` (getattr-آمن؛ حقل إضافي لا يكسر مستهلكين).
- `static/app.js`: `showPartialRollbackWarning` — toast تحذيري + نص
  دائم `.terminal-partial-rollback` على كارت التيرمنال.
- `static/style.css`: `.toast.warning` + `.terminal-partial-rollback`
  بتوكنز الثيم فقط (`var(--warning)` — منضبط TF-04).

### Added
- `tests/unit/test_snapshot_cap_visibility.py` — 10 اختبارات: سقفا
  عدد/حجم مصغّران → علم + ⚠️ في التقرير؛ سلبيان (تحت السقف / بلا
  checkpoint)؛ تصفير العلم بين الأوامر؛ E2E عبر AgentLoop حقيقي →
  إطار done يحمل partial_rollback=True/False؛ فحص نصي لواجهة العرض
  (app.js + style.css).

### Verification
- الاختبارات الجديدة 10/10 خضراء؛ test_run_command/test_checkpoint
  القائمة تمر بلا تعديل · pyflakes نظيف (تحذيرات agent_loop الأربعة
  قائمة بأصل المستودع — تحقق git stash) · lint_handler_state نظيف ·
  contracts+parity 113 · goldens+ws_router 32 · بوابة mypy: Success
  81 ملفًا · Regression junitxml: **1841 = 1F/1806P/34S** (80.2s؛
  theme_tokens/TF-04 حصرًا؛ 1831+10=1841 ✓) — **خط انحدار جديد: 1841**.

---

## TSK-618 — تضييق except الابتلاعي في path_policy (ASF-07/NF-28) — Session 73

**العائلة المُغلقة**: ASF-07 (§R4) + NF-28 (المكتشفة أثناء الأدلة)

### Fixed
- **NF-28 (C4/S2 — أشد من توصيف ASF-07)**: `raise PermissionError`
  (رفض symlink) كان **داخل نفس الـ try** الذي يلتقط
  `except Exception: pass` (path_policy.py:102–108) —
  وPermissionError ⊂ Exception ⇒ الرفض يُبتلع فور رفعه والفحص **ميت
  بالكامل** منذ كتابته (تجربة حية: symlink داخلي وملف عبر مجلد
  symlink كانا يمران). [SUPERSEDES جزئيًا توصيف ASF-07 «تخطٍّ عند
  خطأ FS»]. الخطان الصلبان (الاحتواء على المحلول + فحص الأسرار على
  المحلول) كانا وما زالا يصمدان — المفقود طبقة الدفاع الإضافية.

### Changed
- `chain/path_policy.py`: فصل القياس عن القرار — `is_symlink()` وحده
  داخل try ضيق يلتقط **OSError حصرًا** مع `_LOG.warning` موسوم
  (المقطع + المسار + الخطأ + تذكير بأن الاحتواء/الأسرار النهائيين
  يطبقان)؛ `raise PermissionError` خارج الـ try ⇒ الرفض حي وخطأ FS
  لم يعد صامتًا. logger جديد `chain.path_policy`. نفس مبدأ TSK-616:
  الحقيقة تُشتق حيث تحدث ولا تُبتلع في الطريق.

### Added
- `tests/unit/test_path_policy_symlink.py` — 9 اختبارات (أول تغطية
  مباشرة لـ path_policy): إحياء الرفض (ملف/مجلد)؛ allow_symlinks=True
  يمر؛ المسار العادي بلا تغيير؛ خطأ FS محقون (monkeypatch) → تحذير
  caplog + الاحتواء النهائي يعمل (القبول حرفيًا)؛ سلبي بلا ضجيج؛
  الخطان الصلبان محفوظان؛ حارس بنيوي regex ضد عودة
  `except Exception: pass` (عدّاد NF-14 لا يرتفع).

### Verification
- تحقق حي قبل/بعد: A/B (fail-open) → يُرفضان؛ C/D محفوظان؛ المسار
  العادي وallow_symlinks=True بلا تغيير · pyflakes نظيف ·
  lint_handler_state نظيف · mypy Success 81 ملفًا · contracts+parity
  113 · goldens+ws_router 32 · Regression junitxml:
  **1850 = 1F/1815P/34S** (77.5s؛ theme_tokens/TF-04 حصرًا؛
  1841+9=1850 ✓؛ فشل test_search_perf بالتمريرة الأولى ثبت أنه flaky —
  يمر معزولًا ×2 وفي الإعادة الكاملة؛ حد 1s على عتاد مشترك) —
  **خط انحدار جديد: 1850**.

## [TSK-619] — 2026-07-29 — بطاقة الخطة التفاعلية (CP-1/UXF-01)

### Added
- `static/js/plan_card.js` — وحدة نقية جديدة (UMD-lite، نمط
  status_chip): حالة أعلام تفعيل لكل خطوة (كلها مفعّلة افتراضيًا)؛
  createState / toggle / setEnabled / isEnabled / enabledActions
  (subset بترتيبه الأصلي) / enabledCount. رأس الوحدة يوثق ضمان حفظ
  السلوك: كل-الخطوات-مفعلة = payload التنفيذ القديم حرفيًا.
- `tests/unit/test_plan_card.py` — 10 اختبارات node: تعطيل خطوة →
  payload بدونها (القبول حرفيًا)؛ كل-الخطوات-مفعلة → مطابق بايتًا
  للقائمة الأصلية (بوابة حفظ السلوك)؛ منطق الأعلام + حدود النطاق +
  صفر مفعّل + مدخلات فارغة؛ wiring (app.js/index.html)؛ سيناريو
  يدوي موثَّق في docstring (DevTools → WS Messages) كـ Accept رسمي.

### Changed
- `static/app.js`: showPlanCard يرسم checkbox لكل خطوة
  (plan-step-toggle، checked افتراضيًا) ويربط change بحالة PlanCard
  النقية (DOM glue فقط)؛ executePlan يرسل
  `PlanCard.enabledActions(...)` بدل القائمة الكاملة مع منع الإرسال
  + toast عند صفر مفعّل؛ cancelPlan يصفّر planCardState.
- `static/index.html`: تحميل `plan_card.js?v=1` قبل app.js.
- `static/style.css`: .plan-step-label / .plan-step-toggle /
  .plan-step-disabled — tokens فقط (TF-04).
- **server.py بلا لمس**: actions المرسلة subset من نفس البنية —
  شفاف لـ `_apply_batch` (أُطره golden-locked).

### Verification
- node --check نظيف · pyflakes نظيف · lint_handler_state نظيف ·
  mypy Success 81 ملفًا · contracts+parity 113 · goldens+ws_router 32 ·
  Regression junitxml: **1860 = 2F/1824P/34S** (81.7s؛ 1850+10=1860 ✓؛
  theme_tokens/TF-04/D-2 المعروف + test_search_perf flaky الموثق S73 —
  يمر معزولًا ×2) — **خط انحدار جديد: 1860**.

## [TSK-620] — 2026-07-29 — سرد الجلسة (CP-8/UXF-05)

### Added
- `static/js/session_narrative.js` — وحدة نقية جديدة (UMD-lite):
  timeline يجمع محطات الجلسة (طلب → خطة → موافقات → تنفيذ → نتائج →
  استعادة) من أطر WS الحية الموجودة — التقاط استهلاك-فقط بنفس عقد
  StatusChip.noteFrame حرفيًا (لا إطار يُعدَّل ولا مسار case يتغير)؛
  دمج خطوات التنفيذ المتتالية بعدّاد؛ سقف MAX_ENTRIES=200 أقدم-يُطرد
  (نفس مبدأ MAX_PENDING في run_metrics)؛ renderTimelineHTML نقي
  بتهريب HTML. محلي بالكامل، بلا cloud (Non-Goal §15.2).
- `tests/unit/test_session_narrative.py` — 10 اختبارات node: القبول
  حرفيًا (run معتمد واحد → 5 محطات بترتيبها في الحالة والـ HTML)؛
  تجاهل الأطر غير المعروفة؛ الرفض/الخطأ sn-bad؛ rollback؛ دمج
  التنفيذ + كسره بعد نتيجة؛ السقف؛ حالة فارغة + تهريب HTML؛
  wiring؛ سيناريو يدوي موثَّق في docstring (بوابة Documentation).

### Changed
- `static/app.js`: التقاط الأطر في handleWSMessage بجوار StatusChip؛
  noteRequest في sendMessage (يغطي message/chain_message)؛
  renderSessionNarrative يحقن `#session-narrative` قبل قائمة
  RunHistory داخل اللوحة عند الفتح — القائمة/التقرير/الاستعادة بلا
  أي تغيير.
- `static/index.html`: تحميل `session_narrative.js?v=1` قبل app.js.
- `static/style.css`: أصناف #session-narrative/.sn-* — tokens فقط؛
  إصلاح أثناء البوابات: var(--border) غير معرّف (كشفه TestTokenParity)
  → var(--surface-0) (نمط المنزل لفواصل اللوحات).
- **server.py بلا لمس** — لا endpoints ولا أطر WS جديدة.

### Verification
- node --check نظيف · lint_handler_state نظيف · mypy Success 81
  ملفًا · contracts+parity 113 · goldens+ws_router 32 · Regression
  junitxml: **1870 = 1F/1835P/34S** (82.4s؛ 1860+10=1870 ✓؛
  theme_tokens/TF-04/D-2 حصرًا؛ search_perf مرّ في التمريرة
  النهائية) — **خط انحدار جديد: 1870**.

## [TSK-621] — 2026-07-29 — Permissions UI قراءة (CP-5/UXF-04 §R9)
### Added
- endpoint قراءة `GET /api/permissions` في blueprint meta القائم
  (routes/meta.py — ADR-003؛ server.py صفر تعديل): السياسة الفعالة
  الحية — command_allowlist (command_policy_from على config الحي:
  enforce/entries/timeout/output_max_chars)، SAFE/APPROVAL tools،
  SAFE/DANGEROUS commands، force_command_approval، وحالة ApprovalGate
  (mode/auto_whitelist/timeout؛ null قبل الإقلاع — لا اختراع).
- وحدة نقية `static/js/permissions_panel.js` (UMD-lite):
  renderPanelHTML نقي — الأقسام الأربعة من JSON، تهريب HTML، غياب
  صريح (UNKNOWN)، صفر أدوات كتابة في المخرجات.
- لوحة `#permissions-panel` قراءة-فقط + زر Activity Bar 🔒 (تفويض
  .click() لزر وكيل مخفي — نمط TF-03) في index.html؛ الغراء
  togglePermissionsPanel (fetch GET + render فقط) في app.js؛
  أصناف pp-* في style.css (tokens فقط — var(--surface-0)).
- `tests/unit/test_permissions_panel.py` (12): القبول حرفيًا (قيم
  حية مطابقة للثوابت الحقيقية) + لا مسار كتابة (405 + لا تحوّل
  حالة) + بوابة حية/null + وحدة node (5) + wiring (2) + سيناريو
  يدوي موثَّق (Accept).
### Changed
- سطح REST المجمّد 30→31 قاعدة (tests/unit/test_rest_blueprints.py —
  FROZEN_RULES + `/api/permissions GET` بتعليق مؤرَّخ): **توسيع عقد
  مقصود** — قبول TSK-621 ينص حرفيًا على «endpoint قراءة».
### Verification
- node --check نظيف؛ pyflakes نظيف؛ lint_handler_state نظيف؛ mypy
  Success 81 ملفًا؛ العقود+parity 113 ✓؛ goldens+ws_router 32 ✓؛
  junitxml: **1882 = 1F/1847P/34S** (80.0s؛ 1870+12=1882 ✓؛
  theme_tokens/TF-04/D-2 حصرًا) — **خط انحدار جديد: 1882**.

## [TSK-625] — 2026-07-29 — صلابة _parse_args_body (ASF-06)
### Changed
- `_parse_args_body` (chain/agent_tools.py): تفكيك متسامح مع القيم
  متعددة الأسطر — سطر يبدأ بمفتاح شرعي يفتح وسيطًا؛ أي سطر آخر
  (بلا `:` أو مفتاحه غير شرعي) يُطوى في قيمة المفتاح السابق (يشمل
  reason) بدل البتر الصامت/الوسيط الزائف (إثبات ما-قبل بالتشغيل في
  §TSK-625). لا مفتاح سابق ⇒ يُهمَل كما قبل. نفس التوقيع؛
  parse_tool_calls (fence-aware) وexecute بلا لمس.
### Added
- `_known_arg_keys()`: اشتقاق المفاتيح الشرعية **حيًّا** من تواقيع
  `AgentTools._handlers` (inspect + reason، cache) — لا قائمة يدوية.
- `tests/unit/test_parse_args_body.py` (18): golden حفظ السلوك (6)
  + قبول متعدد الأسطر (5) + عدائية (5 — تشمل بقاء إسقاط _approval
  ASF-02) + اشتقاق حي (1) + e2e (2).
### Verification
- pyflakes + lint نظيفة؛ mypy Success 81 ملفًا؛ العقود+parity 113 ✓؛
  goldens+ws_router 32 ✓؛ junitxml: **1900 = 1F/1865P/34S** (81.4s؛
  1882+18=1900 ✓؛ theme_tokens/TF-04/D-2 حصرًا) —
  **خط انحدار جديد: 1900**.

## [TSK-624] — 2026-07-29 — retro-ADR لإعادة تصميم v25 (TD-04)
### Added
- **ADR-005** في `ARCHITECTURE_DECISIONS.md`: توثيق استرجاعي لإعادة
  تصميم الواجهة v25 (0d74dad/2ed794f/8235147/454f7ac — 1877
  insertions في static/) — النطاق بالأدلة من git، الأثر (كسر
  TF-01/TF-03/TF-04 + تعمية البوابة TF-05)، كيف أُصلحت
  (TF-01/03 → TSK-604 ✅؛ TF-04 معلّق D-2)؛ الدوافع الأصلية UNKNOWN.
- قيد استرجاعي موسوم retro في `DECISION_LOG.md` (Task = TSK-624).
### Verification
- مهمة توثيقية صرفة (صفر لمس كود)؛ junitxml بعد التوثيق:
  **1900 = 1F/1865P/34S** (80.4s؛ theme_tokens/TF-04/D-2 حصرًا) —
  خط الانحدار بلا تغيير. **TD-04 مغلق**.

## [TSK-626] — 2026-07-29 — قرار proposed_actions: توثيق الفرع test-only (RP-04)
### Changed
- **تعليقات فقط — صفر منطق**: سطر عقد موحَّد فوق كتلة الموافقة
  المتناظرة في الـ runners الأربعة (agent.py:103/chain.py:90/
  delegate.py:99/direct.py:76): الفرع test-only — مواقع بناء
  RunRequest الإنتاجية الخمسة (server.py:1540 +
  chat_dispatch.py:245/280/343/449) لا تمرر proposed_actions؛
  المستهلك الوحيد RunnerContractMixin؛ لا يُحسب طبقة أمان فعلية؛
  يُصان كمجال توسعة (worker.py T-110).
- تعليق مقابل عند موقع RunRequest في server.py:1533 + تعليق جامع في
  core/chat_dispatch.py:26 (المواقع الأربعة المنقولة في M8/ADR-002).
- القرار المنفَّذ: **توثيق** (الخيار الأول في نص المهمة)؛ «التوصيل
  بمستهلك» تغيير سلوكي منتج = قرار مالك لم يُتخذ ذاتيًا.
### Verification
- pyflakes دلتا صفر (stash-diff) · lint نظيفة · mypy Success 81 ·
  contracts+parity 113 ✓ · goldens+ws_router 32 ✓ · junitxml:
  **1900 = 1F/1865P/34S** (82.0s؛ theme_tokens/TF-04/D-2 حصرًا) —
  خط الانحدار بلا تغيير. **RP-04 مغلق**.

## [TSK-605] — 2026-07-29 — TF-04: tokenization كاملة لألوان v25 (قرار D-2) — أول خضرة كاملة للبوابة
### Added
- 37 توكنًا جديدًا (26 `--v25-*` + 11 `--tango-*`) بنفس القيم الحرفية في
  ملفات اللوحات الأربعة (dark/light/high-contrast/monokai: 68→105 توكنًا؛
  التكافؤ الرباعي الصارم محفوظ) + امتداد عقد التسمية في رأس tokens.css.
- `scripts/_tokenize_v25.py` — سكربت الترحيل الآلي (يُحتفظ به للتدقيق).
### Changed
- `static/style.css` — 127 سطرًا مخالفًا (138 موضع لون خام): hex →
  `var(--token)`؛ rgba() → `color-mix(in srgb, var(--token) N%, transparent)`
  (مكافئ حسابيًا)؛ حذف 6 fallbacks ميتة `var(--accent, #7c6af7)`.
- `static/index.html:95/96/99/100` — SVG stops: `stop-color="#hex"` →
  `style="stop-color:var(--v25-purple|--v25-cyan-deep)"`.
- سجلات: §TSK-605 (قرار D-2 + Evidence S83 + pre-checks + Close-out)،
  DECISION_LOG (قيد وصول قرار المالك D-2)، جدول الحالة (605 ✅، M6 مغلقة 5/5).
### Verification
- ألوان خام خارج static/themes/: 131 سطرًا → **0** (نفس regex الحارس).
- test_theme_tokens → 28 passed؛ snapshot الـ dark لم يُمَسّ (إضافات فقط).
- **regression كامل: 1900 = 0 failed / 1866 passed / 34 skipped (79.9s)
  — أول خضرة كاملة في تاريخ البرنامج**؛ `bash scripts/check.sh` →
  **ALL GREEN (exit 0) لأول مرة** = معيار خروج M6 الأخير؛ pyflakes نظيف.

## [TSK-617] — 2026-07-29 — أمان الافتراضات البرمجية (قرار D-1): قلب enforce وforce_command_approval إلى fail-closed
### Changed
- `server.py:_force_command_approval` — غياب المفتاح أو تعذّر قراءة config
  ⇒ **True** (إلزام الموافقة)؛ القيمة الصريحة تُحترم (false الصريح في
  config المشحون = السلوك التاريخي كما هو).
- `chain/agent_tools.py:command_policy_from` — غياب/فساد قسم
  `agent.command_allowlist` ⇒ `enforce=True` بقائمة فارغة = رفض كل أوامر
  الـ agent برسالة مهيكلة (لا legacy صامت)؛ البناء المباشر بلا سياسة
  (مسار الاختبارات) يبقى legacy موثَّقًا.
- توثيق: config.yaml (تعليقا NF-16 + agent) + README (:422 + «حدود
  النشر» بند 4).
- اختبارات الافتراضي القديم حُدِّثت معلنةً القلب: test_force_approval
  (flag_absent→True + flag_absent_api_run_gated + explicit_false جديد)؛
  test_run_command (missing_section/garbage_types → fail-closed).
### Verification
- الملفات المتأثرة الخمسة خضراء كاملة؛ regression: 1F/1866P/34S —
  الفشل الوحيد test_search_perf العابر الموثَّق (معزولًا 18 passed)؛
  القبول مُثبَت تنفيذيًا (حذف المفاتيح ⇒ آمن؛ config الحالي ⇒ صفر تغيير)؛
  pyflakes delta صفر (stash-diff)؛ mypy Success 81 ملفًا.
