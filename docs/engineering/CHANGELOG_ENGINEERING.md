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
