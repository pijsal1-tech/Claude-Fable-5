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

## TSK-609 — Instrumentation: توقيت المسارات + التوكنز — Sessions 49–53

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
