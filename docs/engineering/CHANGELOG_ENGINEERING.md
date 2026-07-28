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
