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

## [TSK-622] — 2026-07-29 — إعادة تصويت RELEASE_READINESS (قرار المالك D-4)
### Added
- قسم §5 "Re-vote — Session 83" في RELEASE_READINESS_REPORT.md
  (append فقط، 112→197 سطرًا): إعادة تقييم G1–G5 على الكود الحالي
  بدليل حي لكل بوابة — كلها ✅ PASS؛ الحكم الإجمالي انقلب من NO-GO إلى
  **GO ضمن عقد localhost أحادي-المستخدم الموثَّق**؛ الشروط المرفقة:
  نموذج التهديد 127.0.0.1 يبقى عقد المنتج (والافتراضات البرمجية الآن
  fail-closed بقرار D-1).
### Changed
- DEVELOPMENT_TASKS: §TSK-622 (Evidence/pre-checks/Close-out) + صف الجدول
  ✅؛ **M9 مغلقة كاملة** (615–622).
### Verification
- Documentation gate: لا كود مُس؛ grep يؤكد بقاء النص الأصلي §1–§4 حرفيًا؛
  كل استشهاد file:line في القسم الجديد تُحقق منه حيًّا قبل الكتابة
  (parse:107، _zip_member_violations:753، fence_attached في agent_loop
  :230/:274 وknowledge :54/:204/:207، purge_terminal:351، facade:113،
  server.py wc -l = 2141).

## [TSK-623] — 2026-07-29 — أرشفة improvements/ (قرار المالك D-3)
### Changed
- نُقل `improvements/` (892KB، 40 ملفًا — كلها كانت متتبعة) إلى أرشيف
  مضغوط متتبع `test---results/improvements_archive_2026-07-29.tar.gz`
  (176KB) داخل منطقة الأرشيف المستثناة أصلًا من كل مسارات المسح
  (IGNORED_DIRS/TSK-202) — QF-01 مغلق: grep/wc نظيفة من نسخ server.py
  التاريخية (1670+1100 سطرًا) وبقية التلوث.
- `.gitignore`: سطر استثناء `!` واحد ليبقى الأرشيف متتبعًا رغم قاعدة
  `*.tar.gz` العامة.
### Verification
- سلامة قبل الحذف: `tar -tzf` = 40 ملفًا + فكّ لـ /tmp + `diff -r` مقابل
  الأصل = متطابق بايتًا؛ الحذف بعد التحقق فقط.
- Acceptance: `improvements/` غير موجودة؛ `git ls-files` = صفر تحتها؛
  صفر مراجع حية في الكود (ثابت في pre-checks).
- بوابة ما بعد النقل: `check.sh` ALL GREEN exit 0 — خط الانحدار الجديد
  **1901 = 0F/1867P/34S**. Rollback: `tar -xzf` أو revert.

---

## [TSK-701] — 2026-07-30 (Sessions 84–85) — FI-11: مواصفة بروتوكول إطارات WS (توثيق)

**الدفعة**: BATCH-SHORT (قرار المالك D-5 «دفعة SHORT كاملة») — المهمة 1/5.

### Added
- `docs/ws_frame_protocol.md` — أول توثيق كامل للعقد الضمني لإطارات WS
  (كان موزعًا عبر server.py/bridge.py/delegate.py/agent_loop.py/app.js):
  - §1 طبقة النقل: `/ws` (server.py:1716)، موقع الإرسال الأوحد
    `_WSAdapter._send` (T-047)، سلوك الإطار التالف بالاتجاهين.
  - §2 قاعدة النوع المجهول: no-op صامت متماثل (ws_router بلا else /
    switch الواجهة بلا default).
  - §3 جدول C2S: كل مفاتيح `WS_HANDLERS` الـ 25 + الحقول المقروءة فعليًا
    لكل مقبض (استخراج آلي) + مرسل الواجهة لكل نوع.
  - §3.1 توثيق عدم تماثل قائم: الواجهة ترسل `stop` (app.js:1188) بلا
    مقبض خادمي → no-op + مؤقت أمان 6ث واجهيًا. **محفوظ كما هو**.
  - §4 جداول S2C: 49 نوعًا مبثوثًا مبوبة (أساسي/runs/chain/agent/
    delegate/memory) بمواقع الإصدار المؤرخة؛ الواجهة تستهلك 38؛
    §4.7 يعدّد الـ 11 المتجاهلة صامتًا.
  - §4.4 كشف توثيقي: لا إطار `agent_approval_request` يُبث فعليًا —
    طلب موافقة الطرفية يصل `agent_step` بـ `status: "awaiting_approval"`
    (agent_loop.py:513–526)؛ الاسم محجوز تصنيفيًا في
    `_APPROVAL_FRAME_TYPES` فقط.
  - §5 إزالة لبس: `create_file`/`edit_file`/`run_command` أنواع كائنات
    إجراء (action_applier.py:164–178)، `snapshot`/`seal` سجلات journal
    (checkpoint.py:24/29)، `ctx`/`add`/`del` صفوف diff واجهية — ليست
    إطارات WS.

### Verified (Acceptance)
- تحقق مزدوج الاتجاه آلي (§6): 25/25 مقبض في المواصفة؛ 16/16 نوع مرسل
  واجهيًا موثق؛ 42/42 نوع مبثوث خادميًا موثق؛ 44/44 حالة case موثقة —
  **PASS** صفر فجوات.
- صفر تغيير كود (doc-only): `git diff --stat` = ملفا docs فقط.
- الانحدار: **1866 passed, 34 skipped, 1 deselected** (الأساس ثابت؛
  المُستبعَد = flaky بيئي موثق test_search_perf.py:250).
- check.sh: الفشل الوحيد هو نفس الـ flaky البيئي (1.018s > 1.0s) —
  ALL GREEN عدا المستثنى الموثق.

---

## [TSK-702] — 2026-07-30 (Session 85) — FI-12: دليل النشر ونموذج التهديد (توثيق)

**الدفعة**: BATCH-SHORT — المهمة 2/5.

### Added
- `docs/deployment_threat_model.md` — أول بيان صريح لحدود الثقة:
  - §1 العقد الحاكم: localhost أحادي المستخدم (127.0.0.1:5000 افتراضيًا،
    **لا مصادقة، لا TLS** — server.py:1863/2137).
  - §3 خريطة الدفاعات القائمة بمراسيها: احتواء المسارات
    (resolve_workspace_path)، حجب الأسرار (is_secret_file)، بوابة
    الأوامر بطبقتيها (CommandPolicy fail-closed منذ TSK-617 +
    ApprovalGate)، تحصين ZIP (TSK-105)، دفاعات الواجهة (TSK-402/404).
  - §4 نموذج التهديد: المعالَج / المقبول بالتصميم / المستبعد صراحة —
    مع توثيق أن CSRF/Origin غير معالجين صراحة (مخفَّفان بنيويًا فقط).
  - §5 **القاعدة المركزية (هدف FI-12)**: أي `--host` غير loopback يكسر
    العقد وينقل RCE بلا مصادقة (`/api/run` مع force_command_approval:
    false الحالية = تنفيذ مباشر) + ملفات + WS كاملة إلى السطح المكشوف؛
    الحد الأدنى قبل أي تعريض معدَّد وكله غير موجود اليوم = قرار مالك.
  - §6 قائمة فحص التشغيل الآمن — تتضمن التنبيه أن حذف مفتاح
    `force_command_approval` أأمن من ضبطه false (الافتراض عند الغياب
    True — server.py:195 مقابل config.yaml:28 = false حاليًا).

### Verified (Acceptance)
- كل ادعاء أمني بمرساة `file:line @ 7d39e9f` — تحقق آلي لـ 23 مرساة
  ضد الشجرة الفعلية: **23/23 PASS**.
- صفر تغيير كود: `git diff --stat` نظيف (ملف doc جديد فقط).
- الانحدار: نفس شجرة تشغيل 1866P/34S هذه الجلسة (doc-only، لا إعادة
  تشغيل مطلوبة بعد التغيير الوثائقي).

---

## [TSK-703] — 2026-07-30 (Session 86) — FI-10: تعقيم عرض Markdown عبر DOMPurify [كود]

**الدفعة**: BATCH-SHORT — المهمة 3/5. **أول تغيير كود تحت V3.**

### Added
- `static/vendor/purify.min.js` — DOMPurify **3.2.6** vendored محليًا
  (22,305 بايت، ترخيص Apache-2.0/MPL-2.0، التحقق: يبدأ بترويسة الترخيص
  الرسمية ويُحمَّل بنجاح في node/jsdom).
- تحميله في index.html بعد marked وقبل app.js (index.html:43–46) —
  محلي لا CDN (اتساقًا مع سياسة vendor القائمة لـ highlight.js).

### Changed
- `renderMarkdown` (app.js:2389): كان يعيد `marked.parse(text)` **خامًا**
  فيُحقن عبر innerHTML في ≥8 مواقع (:928..:1043) — سطح XSS من محتوى
  النموذج (`<script>`, `<img onerror>`, `javascript:` …). الآن:
  `DOMPurify.sanitize(rawHtml)` على الناتج الوحيد؛ وإن غاب DOMPurify
  (فشل تحميل vendor) ⇒ **fail-safe**: نفس fallback التهريب النصي
  الموجود في catch — لا HTML خام يصل الواجهة في أي مسار.
- cache-bust: `app.js?v=25` → `v=26` (index.html:560).
- لا مواقع أخرى: `marked.parse` الفعلي موقع وحيد (app.js:2403)؛
  stream_render.js يستهلك renderMarkdown ولا ينادي marked مباشرة.

### Verified (Acceptance)
- اختبار DOM فعلي (node + jsdom ضد الملف الـ vendored نفسه): 6/6 PASS —
  `<script>` يُنزع، `onerror` يُنزع، `javascript:` href يُجرَّد،
  `<iframe>` يُحذف، `svg onload` يُنزع، وmarkdown سليم (strong/
  code language-js) **يُحفظ كما هو**.
- grep-guards: `DOMPurify.sanitize` @ app.js:2405، تحميل
  `purify.min.js` @ index.html:46، `node --check app.js` OK.
- الانحدار: **1866 passed, 34 skipped, 1 deselected** — ثابت (لا
  اختبارات python تمس app.js، البوابة كاملة رغم ذلك).

---

## [TSK-704] — 2026-07-30 (Sessions 86–87) — FI-06: السجلات المهيكلة [كود]

**الدفعة**: BATCH-SHORT — المهمة 4/5.

### Added
- `core/structured_log.py` — JSON formatter على stdlib logging (صفر
  تبعيات جديدة): `JsonFormatter` (حقول ثابتة ts/level/logger/event +
  دمج `record.structured`؛ فشل التسلسل لا يرفع)، `get_logger` (جذر
  `webdev`)، `configure` (التفعيل الصريح الوحيد — idempotent، بلا
  propagate للجذر العام)، و`swallowed(event, exc, **fields)` —
  **لا يرفع أبدًا**، DEBUG على `webdev.swallowed`، **صامت افتراضيًا**
  (صفر مخرجات ما لم يُفعَّل).
- `tests/unit/test_structured_log.py` — 16 اختبارًا: الصيغة/الحقول/
  سطر واحد/تسلسل قيم عدائية/عربية بلا escaping/idempotency/الصمت
  الافتراضي/عدم الرفع مع استثناء `__str__` منفجر/ثبات التدفق +
  **اختبار عقد** يفحص المستودع آليًا: صفر مواقع ابتلاع صامتة غير
  موصولة في core/+chain/ (يمنع الانحدار مستقبلًا).

### Changed (log-only — صفر تغيير تدفق تحكم)
- توصيل **32 موقع ابتلاع صامت** (`except Exception` → pass/continue)
  عبر 12 ملفًا بسطر `_slog_swallowed("path:line", exc)` قبل
  pass/continue القائمَين (تبقى كما هي حرفيًا):
  core/: approval(1)، backends_redis(1)، chat_dispatch(2)، events(1)،
  project_memory(1)، session_context(3) — chain/: action_applier(3)،
  agent_tools(4)، bridge(5)، context_builder(5)، delegate(1)،
  executor(5).
- **انحراف موثَّق (نص TSK-704 يجيزه)**: مواقع server.py الـ23 لم
  تُوصَّل هذه الجلسة — النطاق قُصر على core/+chain/ (بيئة الجلسات
  متقطعة بـ resets متكررة)؛ التوصيل المكمل مهمة لاحقة اختيارية.

### Verified (Acceptance)
- اختبارات structured_log: **16/16 PASS**؛ mypy على الوحدة: نظيف.
- grep القبول: صفر `except Exception` متبوعة بـ pass/continue صامتين
  في core/+chain/ (الاستثناء الوحيد المصرح: حارس swallowed نفسه —
  منع العودية؛ مغطى باختبار العقد).
- الانحدار: **1882 passed** (1866 أساس + 16 جديدة)، 34 skipped —
  و**check.sh: ALL GREEN rc=0** (1883P — الـ flaky نجح في هذا التشغيل).
- خط الأساس الجديد للدفعة: **1882P/34S** (مع deselect الـ flaky).

## [TSK-705] — 2026-07-30 (Sessions 87–88) — FI-03: انضباط الإيقاف الرشيق [كود]

**الدفعة**: BATCH-SHORT — المهمة 5/5 (**الأخيرة — الدفعة مكتملة**).

### Added
- `graceful_shutdown(registry, timeout, poll_interval=0.05)` في
  `core/execution.py` — إلغاء تعاوني لكل التذاكر الحية
  (`list_active()` → `ticket.cancel("graceful shutdown")` — نفس مسار
  `cancel_run`، لا آلية إنهاء جديدة) ثم انتظار محدود حتى بلوغها حالة
  نهائية أو انقضاء المهلة. **صفر تذاكر حية = عودة فورية** بلا نوم.
  لا إنهاء قسري: ما لم يُنهِ نفسه خلال المهلة يُعاد للمستدعي كما هو
  (عقد السجل: «السجل لا يكذب بشأن الحياة»). المدخل بنيوي —
  Protocol محلي `_ShutdownRegistry` بسطح `list_active` فقط (server.py
  يمرر `RegistryBackend`؛ استيراد core/backends من core/execution
  دورة محظورة).
- ربط SIGTERM/SIGINT في `server.py` — داخل `main()` **حصريًا** قبل
  `app.run` (لا تغيير في مسار الطلبات؛ استيراد الوحدة كـ module في
  الاختبارات لا يلمس المعالجات): إشارة أولى = إيقاف رشيق (مهلة 5ث +
  تقرير المتبقي) ثم SystemExit(0)؛ إشارة ثانية = خروج فوري
  SystemExit(1).
- 9 اختبارات وحدة جديدة (`TestGracefulShutdown` في
  tests/unit/test_execution.py): صفر تذاكر = فورية (<0.5s رغم
  timeout=60)؛ منتهية-فقط = فورية؛ رفع العلم على كل الحية + السبب؛
  سبب سابق يُحترم؛ **احترام المهلة** مع runs متعنتة (رجوع ≥timeout
  و<2s، الحالة تبقى running بصدق)؛ عودة مبكرة عند الملاحظة التعاونية؛
  خليط مُنهٍ/متعنت؛ timeout=0 = إلغاء+فحص واحد؛ ValueError للوسائط
  الباطلة.

### Verified (Acceptance)
- اختبارات الوحدة: **31/31 PASS** في test_execution.py (22 قائمة + 9
  جديدة)؛ mypy على core/execution.py وserver.py (بأعلام البوابة): نظيف.
- **اختبار دخاني وظيفي** (سيرفر حقيقي): إقلاع على 127.0.0.1:5599 →
  HTTP 200 → `kill -TERM` → خرجت العملية خلال ≤2ث مع
  «⏹️ SIGTERM: إيقاف رشيق…» ثم «✅ إيقاف نظيف».
- الانحدار: **1892 passed, 33 skipped, 1 deselected** — التسوية
  الحسابية مقابل الأساس 1882P/34S: +9 اختبارات TSK-705 +1 skip شرطي
  بيئي تحول إلى pass (الـ33 المتبقية كلها Redis-مشروطة، تعمل في CI).
- **check.sh: ALL GREEN rc=0** (1893P/33S — الـ flaky المعروف نجح في
  التشغيل النظيف؛ فشل مرتين سابقتين تحت تنافس CPU من تشغيلات موازية —
  نفس النمط الموثق منذ فتح الدفعة).
- خط الأساس الجديد: **1892P/33S** (مع deselect الـ flaky).

**BATCH-SHORT مكتملة 5/5**: TSK-701 ✅ TSK-702 ✅ TSK-703 ✅ TSK-704 ✅
TSK-705 ✅ — كل بنود FI-11/FI-12/FI-10/FI-06/FI-03 مقفلة.

## [TSK-706 / D-6] — 2026-07-30 (Sessions 88–89) — دفعة التصفير (CLEANUP) [كود + حوكمة]

**الدفعة**: D-6 «دفعة التصفير» — قرار مالك معتمد (DECISION_LOG).
البنود: (أ) حرّاس FI-08 في check.sh؛ (ب) توصيل المواقع الصامتة في
server.py (إغلاق انحراف TSK-704 الموثق)؛ (ج) تدوير PROGRESS §6.4؛
(د) G-10؛ (هـ) G-11.

### Added
- `scripts/check_import_cycles.py` (FI-08) — فاحص دورات استيراد
  stdlib/AST خالص: 9 حزم + server كوحدة عليا، يحلّ الاستيرادات
  النسبية وfrom-X-import-submodule، DFS ثلاثي الألوان يعيد مسار
  الدورة عند وجودها. النتيجة: **94 وحدة، 245 حافة، 0 دورات**؛
  ضابط سلبي (a→b→c→a اصطناعية) يكتشف الدورة ✅.
- حارسان جديدان في `scripts/check.sh` قبل قسم pytest:
  فحص دورات الاستيراد (NF-24) + حارس ازدواج الثابت
  `MAX_SMART_FILE_SIZE` (مصدر وحيد). (البند الثالث في FI-08 —
  حارس ws.send — كان موجودًا سلفًا منذ T-047.)
- `docs/engineering/PROGRESS_ARCHIVE_1.md` (1832 سطرًا) — تدوير §6.4:
  Sessions 24–83 + أرشيف v4.1 CORE-ONLY المضمَّن (Sessions 1–23).
  append-only. PROGRESS.md: 2389 → 572 سطرًا مع مؤشر أرشيف؛
  المقاطع الحاكمة (Stage/Position/Checklists/Pending Git) لم تُمَس.

### Changed
- `server.py` — توصيل **6 مواقع صامتة فعليًا** (من أصل 23
  `except Exception` — البقية تسجّل/تعالج سلفًا) بـ
  `_slog_swallowed("server.py:<سطر>", _exc)` مع الحفاظ على التعليقات
  وعبارة pass القائمة. مواقع except: 315، 1511، 1531، 1573، 1949،
  2060. **صفر مواقع صامتة متبقية** (تحقق الماسح).
- `tests/unit/test_structured_log.py` — توسيع اختبار العقد
  `test_no_remaining_silent_sites` ليشمل server.py إضافة إلى
  core/+chain/ — يمنع النكوص مستقبلًا. 16/16 PASS.

### Governance (G-10 / G-11)
- G-10 **محلولة**: المالك حذف `docs/engineering_constitution/` بنفسه
  (commit 626fd1d — 13 ملفًا: 11 صفرية الحجم + PRODUCT_VISION.md
  + ENGINEERING_WORKSPACE.md). شرط المالك (1) مُنفَّذ قبل الاعتماد:
  فحص مرجعي شامل = **صفر إشارات في الكود/الاختبارات**؛ الإشارات
  المتبقية في 4 وثائق حوكمة append-only فقط (تاريخية، آمنة دلاليًا
  لأن V3 أعلن الفصول «خاملة» سلفًا).
- G-11 **سقطت بالتبعية**: PRODUCT_VISION.md القديم كان داخل المجلد
  المحذوف. قيد D-6 مسجَّل في DECISION_LOG.

### Verified (Acceptance)
- **check.sh كامل بالحرّاس الجدد أول مرة end-to-end: ALL GREEN
  rc=0** — «import graph acyclic: 94 modules, 245 edges, 0 cycles»
  + «constants single-sourced» + mypy نظيف + كل أقسام grep +
  **1892 passed, 34 skipped in 83.01s**.
- انحدار ما-بعد-حذف-المالك (تشغيل سابق ضمن الدفعة):
  1891P/34S مع deselect الـ flaky — الأساس سليم.
- سلامة التدوير مُتحقَّق منها على origin: PROGRESS.md = 572 سطرًا
  والمقاطع الحاكمة كاملة + مؤشر الأرشيف؛ ARCHIVE_1 = 1832 سطرًا
  برأس §6.4 وذيل مكتمل.

**D-6 مكتملة 5/5 بنود (أ–هـ)**: الأرضية نظيفة — لا مواقع صامتة،
لا دورات استيراد، لا ملفات دستور قديمة، PROGRESS مُدوَّر، حرّاس
دائمون في البوابة. جاهزون لدفعات MID (FI-01/FI-02…).

## [TSK-707..711 / D-7] — 2026-07-30 (Sessions 90–94) — FI-01: توحيد حالة الجلسة REST/WS [كود]

**الدفعة**: BATCH-FI01 (قرار مالك D-7) — 5 تاسكات صغيرة بشرط المالك،
مخطَّطة أولًا (S90) ومنفَّذة بعد «ابدأ» الصريحة (الإجراء الدائم الجديد).

### Added
- `core/conversation_state.py` (TSK-707) — المخزن القانوني الموحد:
  `ConversationState` (history + binding_banner خلف RLock) بعمليات
  مسماة وعزل بالنسخ في الاتجاهين + 13 اختبار وحدة (منها أمان خيوط:
  4×50 كتابة متزامنة بلا فقد).
- `tests/integration/test_rest_ws_state_parity.py` (TSK-711) — عقد
  التكافؤ: بذر WS ≡ قراءة REST حرفيًا؛ /api/clear ينعكس على الاتصال
  الجديد والقائم يبقى معزولًا (T-048)؛ البانر حي للاتصالات القائمة؛
  history_length من المخزن + **ماسح نكوص دائم** (صفر وصول خام
  `_srv.chat_history|_srv._binding_banner` في routes/ + بذر
  _build_session_context من المخزن حصريًا) — ضابط سلبي تحقق (زرع
  انتهاك → فشل).

### Changed
- `server.py` (TSK-708): بذر WS من `conversation_state.snapshot()`
  والبانر من `conversation_state.binding_banner`؛ مسار الإقلاع يكتب
  عبر `replace_all()`. globals القديمة (:142/:146) أسماء توافق غير
  مستهلكة من routes.
- `routes/sessions.py` + `routes/meta.py` (TSK-709) و
  `routes/project.py` (TSK-710): كل قراءة/كتابة عبر المخزن — نفس
  مفاتيح/قيم JSON ونص بانر R-303 حرفيًا؛ دلالة warn/fork/block كما هي.
- اختباران مقترنان رُحِّلا لمصدر الحقيقة الجديد بنفس الدلالة
  (test_session_binding + test_rest_blueprints — عقد ADR-003 §2 محفوظ).

### Verified (Acceptance)
- **check.sh كامل: ALL GREEN rc=0 — 1911 passed, 34 skipped** (أساس
  1892 + 13 اختبار 707 + 6 اختبارات 711)؛ 0 دورات (95 وحدة/247 حافة)؛
  mypy نظيف 83 ملفًا؛ صفر تغيير في أشكال JSON/إطارات WS (مواصفة
  TSK-701).
- انحدارات وسيطة بعد كل TSK: 1904P/34S ثابتة عبر 708/709/710.

**FI-01 مُغلقة — BATCH-FI01 مكتملة 🏁 5/5**: مصدر حقيقة واحد لحالة
المحادثة المشتركة، NF-03/g5 مستأصلة بنيويًّا، وماسح دائم يمنع النكوص.

## [TSK-712..717 / D-8] — 2026-07-30 (Sessions 95–97) — BATCH-P0: بوابة الإنتاج [تغليف + توثيق + كود طفيف]

### Context
قرارات مالك D-8 (DECISION_LOG): (أ) حذف engineering_constitution/ مؤجَّل
لآخر المشروع → EOP-1؛ (ب) **Windows أولًا، Linux مستقبلًا**؛ (ج) تفويض
تنفيذ خارطة P0→P3 كاملة (مصدرها Evolution Gap Report §10) باستئناف
موثق بين الجلسات. هذه أول دفعة: سد فجوات الإنتاج السبع المتحقق منها
(لا LICENSE / لا requirements.txt / لا إصدار / لا دليل مستخدم / ترويسة
PROGRESS متقادمة / Windows غير مدقق).

### Added
- `requirements.txt` (TSK-713) — القائمة القانونية للتشغيل: 4 تبعيات
  صلبة مُسقَّفة (flask/flask-sock/requests/pyyaml — أدلة file:line في
  رأس الملف) + 5 اختيارية معلّقة بأسبابها. **قبول متحقق**: venv نظيف
  + التثبيت + `import server` ينجح بلا dev deps.
- `docs/WINDOWS_COMPAT.md` (TSK-714) — تدقيق ساكن على 5 محاور
  (إشارات/مسارات/كتابة ذرّية/subprocess+ترميز/flask-sock):
  **AUDITED-STATIC PASS، صفر إصلاحات كود** (الكود عابر للمنصات أصلًا:
  shlex posix-switch @ command_runner.py:82، cmd.exe /c @ :140،
  os.replace ذرّي في 6 مواقع)؛ تدهوران موثقان → دليل المستخدم؛
  قائمة فحص §6 بيد المالك = شرط رفع -rc.
- `docs/USER_GUIDE.md` (TSK-715) — دليل عربي Windows-أولًا: تثبيت
  خطوة-بخطوة + عقد localhost بلغة مستخدم (المصدر:
  deployment_threat_model §5) + استكشاف أخطاء Windows (cp1256،
  إغلاق النافذة، PATH).
- `core/version.py` (TSK-716) — المصدر الوحيد للإصدار:
  `__version__ = "1.0.0-rc.1"` (rc حتى تحقق Windows الفعلي).
- `tests/unit/test_version.py` (TSK-716) — 3 اختبارات: SemVer صالح +
  server.APP_VERSION يطابق + /api/info يعرض المفتاح والمفاتيح القائمة
  سليمة.
- `LICENSE` (TSK-717) — «All Rights Reserved © 2026 pijsal1-tech»
  (الافتراضي الآمن الموثق؛ استبداله برخصة مفتوحة = قيد قرار مالك).

### Changed
- `docs/engineering/PROGRESS.md` (TSK-712) — مصالحة الترويسة الحاكمة:
  CI-2 (last-updated) + CI-3 (Current Stage/Position) + CI-4
  (repository @ 9a3aed0)؛ سجل الجلسات append-only لم يُمس.
- `server.py` (TSK-716) — 3 لمسات: import الإصدار + راية `--version`
  + الإصدار في ترويسة الإقلاع. صفر تغيير سلوكي آخر.
- `routes/meta.py` (TSK-716) — `/api/info` يضيف مفتاح `version`
  (إضافة مفتاح فقط — تجميد السطح في test_rest_blueprints قائم).
- `README.md` — §التثبيت يشير لـ requirements.txt (TSK-713) +
  قسم «سياسة الإصدارات» جديد (TSK-716) + §الرخصة يشير لـ LICENSE
  (TSK-717).

### Verified (Acceptance)
- **check.sh كامل: ALL GREEN rc=0 — 1914 passed, 34 skipped**
  (أساس 1911 + 3 اختبارات version)؛ بوابة وسيطة S96 بعد 713+714:
  1911P/34S.
- وسم `v1.0.0-rc.1` مدفوع على origin (تفويض D-8-ج).

**BATCH-P0 مكتملة 🏁 6/6** — فجوات الإنتاج السبع مسدودة (السابعة:
تحقق Windows الفعلي بيد المالك — WINDOWS_COMPAT §6). التالي بالتفويض
القائم: دفعة P1 (FI-05 فهرس البحث، لوحة تشخيص، تدوير سجلات،
Settings UI) — تخطيط TSK قبل التنفيذ كالعادة.

## [TSK-718 / D-9] — 2026-07-30 — FI-05/1: وحدة snapshot الفهرس
- **Context**: افتتاح BATCH-P1 (قيد D-9 تحت تفويض D-8-ج). FI-05 على
  شطرين؛ هذا الشطر الورقة النقية بلا أي توصيل.
- **Added**: `core/index_snapshot.py` (صيغة v1 + save ذرّي NF-19 لا-يرفع
  + load متشكك يرفض النسخ/الجذور المغايرة والمسارات الخبيثة) +
  `tests/unit/test_index_snapshot.py` (19 اختبار عقد).
- **Changed**: لا شيء قائم مُس — إضافة صافية (صفر توصيل بالتصميم).
- **Verified**: check.sh ALL GREEN rc=0 — **1933P/34S** (خط أساس 1914 +
  19 الجديدة بالضبط؛ بوابات grep سليمة — الوحدة خارج context/).

## [TSK-719 / D-9] — 2026-07-30 — FI-05/2: توصيل snapshot ⇒ FI-05 مُقفل 🏁
- **Context**: الشطر الثاني من FI-05 — فتح المشروع المفهرس سابقًا يصير
  تحميل+delta بدل مشية شجرية كاملة (هدف QA-T13: مشاريع 5k+ ملف).
- **Changed**: `context/index.py` (snapshot_path اختياري + _seed_from_snapshot
  + _save_snapshot_if_changed — التوقيع القديم يعمل حرفيًا كما كان) +
  `server.py` (_index_snapshot_path → `<root>/.ai_runs/project_index.json`
  موصول في _server_handle_factory + _build_ctx).
- **Added**: `tests/unit/test_index_snapshot_wiring.py` (10 اختبارات:
  تكافؤ ذهبي fresh≡seeded، بذر بلا rebuild، تقارب snapshot قديم بعد
  force sweep، سقوط نظيف للفاسد/الجذر المغاير، no-churn، خطاف T-049
  فوق فهرس مبذور، مسار الخادم داخل .ai_runs).
- **Verified**: check.sh ALL GREEN rc=0 — **1943P/34S** (1933+10 بالضبط)؛
  عقد الطزاجة T-049 بلا تغيير دلالي (نافذة ≤2s موثقة في التعريف).

## [TSK-720 / D-9] — 2026-07-30 — P1-3: تدوير metrics/runs.jsonl
- **Context**: الملف الملحق-فقط الوحيد على مستوى التطبيق كان بلا سقف
  (server.py — قرار TSK-610 وثّق الملف الواحد لكن ليس النمو).
- **Added**: `RunMetricsStore.rotate_if_oversized()` (سقف 5MB افتراضيًا؛
  os.replace → جيل .1 واحد؛ لا-يرفع تحت قفل الكتابة) + 7 اختبارات.
- **Changed**: server.py — استدعاء التدوير عند الإقلاع قبل subscribe.
- **Verified**: check.sh ALL GREEN rc=0 — **1950P/34S** (1943+7 بالضبط).

## [TSK-721 / D-9] — 2026-07-30 — P1-2: /api/diagnostics + Support Bundle
- **Context**: فجوة «لا أداة تشخيص للمستخدم» (Evolution Gap §10).
- **Added**: `/api/diagnostics` قراءة-فقط مُطهَّرة (version/platform/deps/
  project_name-بلا-مسار/provider-وصفي-فقط/metrics) + زر Diagnostics في
  شريط الأنشطة + `downloadDiagnostics()` (Blob تنزيل JSON) + 6 اختبارات
  عقد أبرزها فحص عدم-التسريب بمزود leaky مزروع الأسرار.
- **Changed**: توسيع سطح REST المجمَّد 31→32 (توثيق القرار داخل
  test_rest_blueprints — سابقة TSK-621).
- **Verified**: check.sh ALL GREEN rc=0 — **1956P/34S** (1950+6 بالضبط).

## [TSK-722a/D-9] — 2026-07-30
- **`GET /api/settings` — الإعدادات الفعالة قراءة-فقط مُطهَّرة** (glass
  box، سابقة TSK-621): whitelist أقسام صريح — قسم providers مُستبعد
  كليًا، project_root راية فقط، retention.pinned عدد فقط،
  force_command_approval قيمة فعالة fail-closed (D-1/TSK-617) + راية
  explicit_in_config. لا مسار كتابة (POST ⇒ 405)؛ التعديل عبر
  config.yaml + إعادة تشغيل (موثَّق).
- توسيع سطح REST المجمَّد 32→33 (توسيع مقصود ثالث — موثَّق في
  test_rest_blueprints).
- 6 اختبارات (test_settings_endpoint.py) — عقد عدم-التسريب بنمط
  الـ config المزروع (TSK-721). البوابة: **1962P/34S** ALL GREEN rc=0.

## [TSK-722b/D-9] — 2026-07-30 — **BATCH-P1 مُقفلة 🏁 6/6**
- **لوحة الإعدادات — عرض فقط** (glass box، نمط TSK-621):
  settings_panel.js وحدة نقية (renderPanelHTML؛ UNKNOWN صريح للغائب؛
  تهريب HTML؛ صفر أزرار كتابة + ملاحظة «التعديل عبر config.yaml»)
  + toggleSettingsPanel (fetch /api/settings + render فقط) + زر
  Settings في activity bar يفتح اللوحة (زر الثيم بالهيدر كما هو).
- 9 اختبارات (test_settings_panel.py) — node + wiring + نقاء الوحدة.
  البوابة: **1971P/34S** ALL GREEN rc=0.
- **إقفال الدفعة**: BATCH-P1 = 718 (وحدة snapshot) → 719 (توصيلها —
  FI-05 🏁) ∥ 720 (تدوير metrics) ∥ 721 (تشخيص) → 722a (endpoint
  إعدادات مُطهَّر) → 722b (اللوحة). مسار خط الأساس عبر الدفعة:
  1914 → 1933 → 1943 → 1950 → 1956 → 1962 → **1971P/34S**.
  التالي: تخطيط BATCH-P2 بقيد قرار جديد (D-7).

## [TSK-723/D-10] — 2026-07-30 — Command Palette (Ctrl+Shift+P) — أولى BATCH-P2
- وحدة نقية `static/js/command_palette.js`: سجل ساكن COMMANDS ×15
  (action = اسم دالة UI قائمة — لا سلاسل eval) + filterCommands +
  renderListHTML (تهريب HTML، مؤشر تحديد، data-cmd-id).
- غراء app.js: جدول CP_ACTIONS (lookup صريح ×15 مرجع دالة مباشر)،
  فتح/إغلاق/عرض/تنفيذ، اختصار Ctrl/Meta+Shift+P، تنقّل ↑↓/Enter/Esc
  مع التفاف، تفويض نقر closest("[data-cmd-id]").
- index.html: تحميل الوحدة قبل app.js + command-palette-modal (إعادة
  استخدام أنماط quick-open)؛ style.css: غلاف الـ modal + .cp-item.
- **صفر endpoints جديدة — سطح REST المجمّد يبقى 33.**
- 12 اختبارًا (test_command_palette.py): node + سجل-الأفعال-قائمة +
  wiring + نقاء الوحدة. البوابة: **1983P/34S** ALL GREEN rc=0.
  التالي حسب DAG D-10: TSK-724 (FI-09 computeWindow).

## [TSK-724/D-10] — 2026-07-30 — FI-09 نافذة عرض افتراضية للمحادثات الطويلة
- وحدة نقية `static/js/virtual_list.js`: computeWindow (ثابت صارم:
  padTop + Σنافذة + padBottom = Σالكل؛ overscan مقصوص) + totalHeight.
- غراء app.js: buildChatMessage نقية مستخرجة من addChatMessage (التي
  بقيت حرفيًا)؛ renderChatHistory موحّدة (عتبة 150 — دونها المسار
  القديم)؛ spacers + rAF + قياس ارتفاعات فعلية؛ الفتح على آخر رسالة.
- **قيود حافظة محقَّقة آليًا**: البث التدفقي (TSK-401) وكروت التيرمنال
  بلا مساس — appendChild بعد spacer-bottom؛ التمرير التلقائي محفوظ.
- index.html: virtual_list.js قبل app.js. صفر endpoints — السطح 33.
- 13 اختبارًا (test_virtual_list.py). البوابة: **1996P/34S** ALL GREEN
  rc=0. التالي: تفصيل TSK-725 (Workspace Trust) ثم تفصيل TSK-726.

## [TSK-725/D-10] — 2026-07-30 — Workspace Trust — بوابة ثقة fail-closed (شرائح a+b+c)
- **725a — التخزين**: `core/workspace_trust.py` — trust.json في
  `<root>/.ai_runs/` (داخل IGNORED_DIRS)؛ قراءة صارمة (trusted يجب أن
  تكون bool حرفيًا؛ عطب/غياب ⇒ غير موثوق)؛ كتابة ذرية NF-19
  (tmp+fsync+os.replace) لا-ترفع أبدًا. 16 اختبارًا.
- **725b — الإنفاذ**: `ApprovalGate(interactive_override=...)` —
  تقييم ديناميكي عند الطلب؛ استثناء ⇒ فرض تفاعلي؛ deny يبقى deny.
  `_force_command_approval()` يعيد True عند عدم الثقة **قبل** قراءة
  config (يتجاوز false الصريح). `/api/trust` GET (بلا مسارات) +
  POST {trusted: bool} (قرار مستخدم صريح) — **التوسيع الرابع الموثَّق
  للسطح المجمّد: 33→34**. 17 اختبار إنفاذ + ترحيل 3 اختبارات تاريخية.
- **725c — الواجهة**: وحدة نقية `trust_banner.js` (parseTrust
  fail-closed + renderBanner/renderBadge) + غراء app.js (fetch
  /api/trust حصرًا — لا منطق قرار في المتصفح) + لافتة «هل تثق بهذا
  المجلد؟» (تظهر فقط بلا قرار مسجَّل) + شارة دائمة بجوار اسم المشروع
  + تحديث عند switch-project؛ CSS بتوكنز الثيم فقط. 13 اختبارًا.
- البوابات: 2012P (a) → 2030P (b) → **2043P/34S** ALL GREEN rc=0 (c).
  التالي حسب DAG D-10: تفصيل TSK-726 (FI-07 تفكيك app.js).

## [TSK-726/D-10] — FI-07: تفكيك app.js إلى مقاطع مجالية (a+b+c+d+e) 🏁
- **القرار (S103، DECISION_LOG):** لا ES modules (24 دالة onclick مضمّنة
  + لا bundler) — تقسيم مكافئ للسَّلسلة الحرفية: نقل verbatim إلى
  `static/js/app/NN_*.js` بنطاق عام مشترك، تُحمَّل بعد app.js بترتيب
  رقمي (عقد eval-time: مراجع دوال app.js في كائنات literal تُقيَّم
  عند التحميل ⇒ المقاطع بعده حصريًا).
- **الشرائح:** a) بنية + حارس test_app_split (7 اختبارات دائمة) +
  90_search_palette + 91_vl_trust؛ b) 20_editor_files_terminal (691 سطرًا)؛
  c) 30_sessions_models_attachments (496)؛ d) 40_panels (682)؛
  e) 10_chat_ws_stream (1237 — قلب الدردشة/WS/البث، الأخطر آخرًا).
- **النتيجة:** app.js **4204 ⇒ 712 سطرًا** (الهدف < 800 مُحقَّق)؛
  6 مقاطع مجالية؛ صفر تغيير سلوكي (نقل حرفي مكافئ).
- **ترحيل اختبارات:** 13 ملفًا يقرأ app.js مباشرة ⇒ قارئ الحزمة
  `_app_bundle()` (المكافئ الحرفي) — التوكيدات لم تتغير.
- **البوابات:** 2050P/34S ثابتة عبر كل الشرائح — ALL GREEN rc=0.

## [TSK-727/D-10] — غلاف سطح المكتب Windows-أولًا: pywebview + PyInstaller (a+b+c) 🏁
- **القرار (S104، ADR-006):** pywebview + PyInstaller لا Tauri/Electron —
  نفس اللغة، صفر سلاسل أدوات جديدة، صفر لمس للكود المُختبر؛ وضع
  المتصفح يبقى المسار الأول.
- **desktop.py:** منفذ حر → server.main() بخيط خلفي (صفر تعديل على
  server.py) → نافذة WebView؛ pywebview اختيارية محروسة import؛
  8 اختبارات بنيوية + ضم لبوابة mypy.
- **التغليف:** desktop.spec + WINDOWS_BUILD.md + OWNER_CHECKLIST.md
  (20 بندًا) — التحقق التشغيلي النهائي بيد المالك (D-8-ب).
- **البوابة:** **2058P/34S** ALL GREEN rc=0 (خط أساس جديد، +8).
- **بهذا تكتمل دفعة D-10 (P2) كودًا: 723/724/725/726/727** —
  البند الخارجي الوحيد: تأشير المالك على القائمة.

## [TSK-728/BATCH-P3] — 2026-07-31
نظام hooks المالك (CP-4) بعقد «تشديد-فقط»: core/hooks.py (HookRunner —
pre_command fail-closed، post_write/post_run تحذير فقط، غياب القسم =
سلوك اليوم حرفيًا، لا قناة إضعاف بالبناء)؛ الحقن في CommandRunner.run
(قبل كل فحوص الموافقة — يغطي المسارين) وfile_manager عبر درز T-049؛
مثال معلَّق في config.yaml. 34 اختبار عقد. بوابة **2092P/34S** خط أساس جديد.

## [TSK-729/BATCH-P3] — 2026-07-31
تصليب درز redis (FI-04 مُكيَّفة بقرار D-11 — لا معمارية worker؛ الافتراضي in-proc لا يتغير):
توافق fakeredis في كل بوابة محلية (عدة T-108 كاملة + إعادة قراءة مرتبة + دورة قائمة
العمل/reclaim — 17 اختبارًا في tests/unit/test_redis_seam_fake.py، fakeredis>=2.20 في
requirements-dev)؛ حارس عدم التسرّب بنيوي وتشغيلي (subprocess معزول)؛ مقطع §7 في دليل
FI-12 لتفعيل الوضع الموزَّع الاختياري. بوابة **2109P/34S** خط أساس جديد.

## [TSK-730/BATCH-P3] — 2026-07-31
plugins توسيع فوق بنية T-100/101/102 القائمة (لا معمارية جديدة):
إظهار glass-box في /api/diagnostics (مفتاح plugins — أسماء/مراحل/أسباب
فقط، عقد التطهير TSK-721 صامد)؛ إثراء PluginContext في المسار الحقيقي
(run_id عبر PlanRequest من bridge + metadata[complexity] — الافتراضي ""
سلوك تاريخي حرفي)؛ توثيق مؤلّف الإضافات في demo_strategy/README.
11 اختبارًا جديدًا. بوابة **2120P/34S** خط أساس جديد.

## [TSK-731/BATCH-P3] — 2026-07-31

auto-update مُكيَّفة (IR-1/تأشير-727) إلى **فحص تحديث يدوي opt-in معطَّل
افتراضيًا**: `core/update_check.py` (parse/compare semver-مبسّط + fetch
صامت-الفشل + requests كسول نمط T-109) + `GET /api/update-check`
(الافتراضي ⇒ صفر شبكة بحارس مُرقَّع؛ لا polling؛ manifest_url لا تُردَّد؛
السطح المجمّد 34→35) + مثال config معلَّق + «قناة التحديث» في
WINDOWS_BUILD.md. 48 اختبارًا جديدًا. بوابة **2168P/34S** خط أساس جديد
— **BATCH-P3 مكتملة 🏁** (728+729+730+731، +110 اختبارات عبر الحزمة).

## [EOP-1] — 2026-07-31

تنفيذ البند الختامي المُرحَّل (قرار D-8-أ) **بأمر مالك صريح**: حذف
`docs/engineering_constitution/` (13 ملف MD — HISTORICAL-INERT منذ
D-8-أ). صفر مراجع في الكود/الاختبارات/السكربتات؛ مراجع السجلات الهندسية
تاريخية وتبقى (append-only). V3 هو الدستور الحاكم الوحيد ولا يتأثر.
بوابة ALL GREEN بعد الحذف (تغيير وثائقي بحت). خريطة P0→P3 + EOP-1
مكتملة — المتبقي الخارجي الوحيد: تأشير المالك على OWNER_CHECKLIST (727).

## [DOC-README] — 2026-07-31

تحديث README.md بأمر مالك ليعكس حالة ما-بعد P0→P3: شارة إصدار
1.0.0-rc.1، صفوف ميزات جديدة (سطح مكتب/إضافات/خطّافات/فهرس بحث/
تشخيص/Trust/فحص تحديث opt-in)، قسم نسخة سطح المكتب، قسم «سطح REST
(مختارات)»، هيكل مشروع محدَّث (core/routes/context/examples/docs)،
أقسام config الاختيارية (hooks/updates)، صفوف أمان (Trust/Hooks/
لا-phone-home)، دليل تأليف الإضافات، ومرجع rc إلى OWNER_CHECKLIST.
تغيير وثائقي بحت — بوابة ALL GREEN.

## [RELEASE-v1.0.0] — 2026-08-04

**إصدار v1.0.0 النهائي (القرار 2 من تسلسل D-19 — أمر مالك صريح)**:
`core/version.py` = `"1.0.0"` (كان `1.0.0-rc.1` منذ TSK-716/BATCH-P0).
شرط «rc حتى تحقق Windows الفعلي» (D-8-ب، هذا السجل :1174) **أُلغي
بقرار مالك D-19** — نص المالك: «يثبّت Baseline واضح يمكن الرجوع إليه.
لا يغيّر السلوك. يجعل أي Regression لاحقًا أسهل في القياس».
تحديثات مرافقة (وثائقية بحتة): README §سياسة الإصدارات،
docs/USER_GUIDE.md (الإصدار المرجعي)، docstring في core/update_check.py
(المرجع التوضيحي فقط — `_VERSION_RE` والدلالات `1.0.0 > 1.0.0-rc.N`
بلا مساس؛ اختبارات test_update_check.py تغطيها بسلاسل حرفية مستقلة
عن `__version__`). صفر تغيير سلوك: server.py يستورد APP_VERSION من
المصدر الوحيد؛ اختبارات الإصدار (test_version.py/test_diagnostics.py/
test_update_endpoint.py) تقارن ضد `__version__` ديناميكيًا لا ضد سلسلة
مثبتة. بوابة `check.sh` ALL GREEN شرط الإغلاق. وسم `v1.0.0` يُدفع على
origin (سابقة وسم rc.1 تحت تفويض D-8-ج — هذا السجل :1197؛ Auto-Uploader
لا يحمل الوسوم). ملاحظة استئناف: التعديلات الخمسة المرافقة وقيد D-19
وصلت origin عبر commit 0787619 (Auto-Uploader) قبل تصفير بيئة #49؛
هذا القيد أُعيد إلحاقه بعد الاستئناف (كان الجزء الوحيد المقطوع).

## [D19-DEC3] — 2026-08-04

**القرار 3 من تسلسل D-19 — تغطية mypy 100% بلا استثناءات**: إصلاح
الخطأ القائم مسبقًا في `providers/openai_shelby.py:166` (union-attr:
`data.get("v").get("message")` — isinstance على استدعاء `.get()` أول
لا يضيّق نوع استدعاء ثانٍ؛ الإصلاح ربط `v_obj = data.get("v")` محليًا
ثم `isinstance(v_obj, dict)` — **صفر تغيير سلوك**، نفس الدلالات تمامًا).
رُفع آخر `--exclude` من بوابة mypy في `scripts/check.sh` (كان الاستثناء
الوحيد الباقي منذ ADR-004، وأبقاه D-18 نصًّا «يبقى مستثنى» — قرار
المالك D-19 القرار 3 أمر برفعه). النتيجة: **mypy Success على 95 ملفًا**
(النطاق الكامل providers/ + chain/ + core/ + context/ + sessions/ +
routes/ + server.py + desktop.py). حارس البوابة
`test_mypy_gate_614.py::test_documented_excludes_only` حُدِّث: يمنع الآن
**أي** `--exclude` في check.sh (كان يثبّت وجود استبعاد shelby حرفيًا —
انحدار مقلوب). البوابة الكاملة ALL GREEN rc=0: 2586P/34S/0F (90.1s).

---

## [TSK-732] — 2026-08-04 (Session 112 تكملة) — القرار 4 من تسلسل D-19: مؤشر واجهة المهام الخلفية (يستهلك FI-15) 🏁

**بموجب قرار مالك D-19 (القرار 4: «أول تغيير يراه المستخدم فعليًا»)** —
BackgroundDelegateTask (TSK-CEV-113) كان بنية خلفية كاملة بلا أي أثر
مرئي («مؤشر الواجهة خارج النطاق عمدًا»). الآن: توصيل WS كامل + شارة.

### Added
- **732a — التوصيل الخلفي**: حقل `background_task` في SessionContext
  (+ KNOWN_CONVERSATION_STATE في lint_handler_state.py) + استخراج
  `_gather_delegate_context(sctx)` مساعدًا مشتركًا (نقل حرفي من
  `_ws_delegate_message` — صفر تغيير سلوك) + 4 مقابض WS جديدة:
  `background_delegate_message` (تذكرة عبر `_begin_run_ticket` — **قرار
  واعٍ**: المهمة الخلفية تحجز خانة المشروع حتى الحسم؛ مهمة سابقة
  waiting_approval تمنع إطلاق جديدة — «كائن جديد لكل مهمة»)،
  `background_status` (snapshot كامل reconnect-safe)،
  `background_approve` (**الثابت الصلب — لا YOLO**: land ثم نفس تحليل
  الأكشنز في delegate_approve؛ الأفعال تبقى خلف أزرار Apply — طبقتا
  موافقة)، `background_reject`.
- **732b — التثبيتات**: ORIGINAL_MSG_TYPES في test_ws_router.py
  25 → 29 بتعليق D-19-4 (إضافة مقصودة موثقة).
- **732c — اختبارات**: `tests/integration/test_background_delegate_handlers.py`
  — 12 اختبار تكامل حتميًّا (نمط test_delegate_approve_handler:
  FakeProvider + `_handle_ws_message`): started فوري (hand-off)؛
  waiting_approval **بلا land تلقائي**؛ snapshot كامل؛ approve →
  done+actions (golden مشترك) + فشل التحويل يُظهَر (UXF-02)؛ reject
  يحرر الخانة؛ إطلاق ثانٍ مرفوض؛ busy عند تذكرة محجوزة.
- **732d — الواجهة**: `static/js/background_tasks.js` (UMD-lite بنمط
  status_chip.js — منطق نقي، smoke بـ14 تأكيدًا في node) + شارة
  `#bg-task-chip` في الهيدر (⏳ يعمل → ✋ بانتظارك مع زرّي اعتماد/رفض)
  + زر «⏱️ تفويض خلفي» في شريط أدوات الإدخال + onopen يرسل
  background_status (استعادة بعد reconnect) + 4 حالات في
  handleWSMessage + أنماط CSS بتوكنز فقط.

### حدود واعية (من المواصفة — كلها محفوظة)
صفر تعديل على chain/background_delegate.py وdelegate.py
وdelegate_queue.py؛ مقابض delegate_* القديمة كما هي (الاستخراج نقل
حرفي)؛ لا طوابير (FI-13 UI = القرار 5 لاحقًا).

### ملاحظة بيئة
تصفيرا بيئة (#52 و#53) وقعا أثناء التنفيذ؛ الرافع التلقائي أنقذ 732a+b
(commits 6222e17 + a2bb858) — أُعيد فقط ملف الواجهة المفقود. البوابة
الكاملة بعد كل شريحة: **ALL GREEN rc=0 — 2598P/34S/0F** (+12 اختبارًا).
