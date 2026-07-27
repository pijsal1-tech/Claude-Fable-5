# IMPLEMENTATION_TASKS.md — editor_v4 (P5 — CORE-ONLY SCOPE v4.1)

> الحالة تُدار في PROGRESS.md فقط (جدول TASK TABLE هناك يحمل عمود Status الوحيد).
> كل TSK ذرّية: هدف واحد، ملفات محددة، معيار قبول قابل للفحص، وتتبّع ثنائي
> الاتجاه: `Fixes:` (BUG/NF) و`Validated-by:` (QA-T — تُثبَّت معرّفاتها في P6).
> النطاق SECTION 0.8 — لا مهمة تمس providers/ أو fallback أو routing.

---

## M1 — Safety First

### TSK-101 — تمرير الوضع للمحلّل وفلترة actions في chat
- **Fixes**: BUG-01 · **Validated-by**: QA-T05
- **Files**: `actions/response_parser.py` (توقيع `parse(response, mode=None)` L107)،
  `server.py` (موقعا النداء L1671 + كتلة agent L1580–1616؛ إسقاط actions من إطار
  `done` عندما `mode == "chat"` في L1698–1711)
- **Change**: في chat: تعطيل الـ fallback العدواني (L131–169) كليًا، والاحتفاظ
  بالبلوكات الصريحة `FILE:/EDIT:/CMD:` كعرض للمستخدم فقط دون شريط تنفيذ
  (أزرار Apply اليدوية على البلوكات تبقى — هي opt-in أصلًا).
- **Accept**: رد chat يحوي ```python توضيحي → إطار `done` بلا `actions`;
  أوضاع plan/build/edit بلا تغيير سلوكي (goldens خضراء).
- **Deps**: TSK-201 (أو تجميد مؤقت للكتلة المكررة L1895–1925 مع TODO مُرقَّم).

### TSK-102 — تهذيب fallback الأوامر
- **Fixes**: NF-13 · **Validated-by**: QA-T05
- **Files**: `actions/response_parser.py:L153–161`
- **Change**: بلوكات bash داخل الـ fallback لا تتحول لأوامر إلا بوسم صريح `CMD:`؛
  خارج ذلك تبقى بلوك عرض.
- **Accept**: بلوك ```bash يحوي `rm -rf build/` كمثال شرح → لا CommandBlock.
- **Deps**: TSK-101 (نفس الدالة — يُشحنان معًا).

### TSK-103 — توحيد مسارات حقن السياق تحت ContextBudget
- **Fixes**: BUG-03 (+يُغلق NF-09) · **Validated-by**: QA-T06
- **Files**: `server.py:L1332–1339` (ملف مكتشف)، `L1782–1791` (attach مجلد)،
  `context/facade.py` / `context/budget.py:pack:L131`
- **Change**: تمرير المحتوى المكتشف/المرفق كمصدر إلى `gather_message_context`
  بدل الإلحاق الخام بـ `user_text`؛ ميزانية `config.yaml:context_budget` تسقف الكل.
- **Accept**: إرفاق مجلد 15 ملفًا + ملف 100KB → الحمولة النهائية ≤ سقف الميزانية
  (قياس بطول prompt قبل الإرسال — stub، صفر نداءات AI خارجية).
- **Deps**: —

### TSK-104 — سقف تاريخ المحادثة عند نقطة الإرسال
- **Fixes**: NF-07 (جزء الحمولة؛ جزء الذاكرة في TSK-303) · **Validated-by**: QA-T06
- **Files**: `server.py:L1559, L1654`؛ مفتاح config جديد
- **Change**: تمرير آخر N رسالة/حرف من `sctx.chat_history` وفق config
  (افتراضي متوافق سلوكيًا موثَّق).
- **Accept**: جلسة 200 رسالة → حمولة history مسقوفة؛ اختبار وحدة على القصّ.
- **Deps**: TSK-103 (نفس منظومة الميزانية).

### TSK-105 — فحص أعضاء ZIP قبل الاستعادة (Zip-Slip guard)
- **Fixes**: NF-15 · **Validated-by**: QA-T07
- **Files**: `server.py:api_restore_backup:L947–960`
- **Change**: قبل `extractall`: رفض أي عضو مساره مطلق أو يحلّ خارج `fm.root`
  (إعادة استخدام منطق `chain/path_policy.py:resolve_workspace_path:L51`).
- **Accept**: ZIP مُصنَّع بعضو `../evil.txt` → 400 ورفض كامل (لا فك جزئي).
- **Deps**: —

## M2 — Single Source Consolidation

### TSK-201 — دمج كتلتي apply_all_actions / execute_plan
- **Fixes**: NF-23(1) · **Validated-by**: QA-T08
- **Files**: `server.py:L1862–1893` + `L1895–1925` → دالة واحدة `_apply_batch`
- **Accept**: سلوك بايت-بايت مطابق للإطارات الصادرة (golden capture قبل/بعد).
- **Deps**: — (يمهّد لـ TSK-101 وTSK-304)

### TSK-202 — قائمة تجاهل موحّدة تشمل test---results
- **Fixes**: BUG-04 + NF-23(4) · **Validated-by**: QA-T09 (إعادة سيناريو T02)
- **Files**: موديول جديد `core/ignore_rules.py`؛ استهلاك في
  `actions/file_manager.py:L27–31`, `chain/bridge.py:L655–662`,
  `chain/agent_tools.py:L300–302` (+ توسيع فلتر tool_search_code ليستخدمها)
- **Change**: مجموعة واحدة = القائمتان الحاليتان ∪ `{"test---results",
  "test-results", ".ai_runs", ".webdev_backups"}`.
- **Accept**: `tool_search_code` و`scan_folder_for_chain` و`list_dir` الثلاثة
  لا تُرجع أي ملف من المجلدين؛ grep واحد للمصدر الموحّد.
- **Deps**: —

### TSK-203 — توحيد MAX_SMART_FILE_SIZE وقارئ config
- **Fixes**: NF-23(2)+(3) · **Validated-by**: QA-T08
- **Files**: `server.py:L128, L2240` (تعريف واحد)؛ مواضع قراءة config الست
  (L159, L1083, L2412, L2444, L2489, L2539) → helper `_load_config()` مُكاش
- **Accept**: grep: تعريف واحد للثابت؛ ≤1 موضع `yaml.safe_load` في server.py.
- **Deps**: —

## M3 — Runtime Robustness

### TSK-301 — تنظيف pending_path_requests داخل القفل
- **Fixes**: NF-01 · **Validated-by**: QA-T10 (وحدة سباق)
- **Files**: `server.py:L106–148`
- **Accept**: اختبار خيطين (store متكرر + pop متكرر) 10k دورة بلا استثناء.
- **Deps**: —

### TSK-302 — سياسة خانة الـ run: project_id فعلي أو توثيق العالمية
- **Fixes**: NF-02 · **Validated-by**: QA-T10
- **Files**: `server.py:_begin_run_ticket:L319–331` (+ نداءاته)؛ docstring السجل
- **Change**: تمرير `sctx.project.project_id` عند توفره؛ قرار موثَّق عند غيابه.
  عقود contracts/ القائمة هي الحارس الانحداري.
- **Accept**: تبويبان على مشروعين مختلفين يشغّلان معًا؛ نفس المشروع → busy.
- **Deps**: —

### TSK-303 — طَهْر تذاكر terminal من السجل
- **Fixes**: NF-06 (+جزء ذاكرة NF-07) · **Validated-by**: QA-T10
- **Files**: `core/execution.py` (طريقة `purge_terminal(keep_last=N)`)؛
  استدعاء عند register في `server.py`
- **Accept**: 500 run متتابع → `len(list_all())` مسقوف؛ `_list_runs_frame` سليم.
- **Deps**: —

### TSK-304 — استجابة الإلغاء أثناء apply الطويل
- **Fixes**: NF-04 · **Validated-by**: QA-T10
- **Files**: `server.py:_apply_batch` (بعد TSK-201)
- **Change**: نقطة تفتيش إلغاء بين كل action (أو تخييط الدفعة تحت ticket).
- **Accept**: `cancel` أثناء دفعة 20 ملفًا يوقفها قبل اكتمالها.
- **Deps**: TSK-201.

### TSK-305 — تضييق مواضع except الحرجة + log
- **Fixes**: NF-14 · **Validated-by**: QA-T08
- **Files**: `server.py:L1338–1339` (إطار warning بدل pass الصامت)؛ جرد المواضع
  الـ41 وتصنيفها (ابتلاع مشروع / يحتاج log) بتعليقات مرقَّمة
- **Accept**: فشل قراءة ملف مكتشف → المستخدم يرى تنبيهًا؛ لا تغيير سلوك آخر.
- **Deps**: —

## M4 — Frontend & Streaming UX

### TSK-401 — بث تدريجي بدل إعادة render كاملة
- **Fixes**: NF-10 · **Validated-by**: QA-T11
- **Files**: `static/app.js:appendStreamChunk:L928–962`
- **Change**: throttle (rAF/زمن) + إعادة render للمقطع المفتوح الأخير فقط،
  بالاتساق مع كاش الإبراز T-064 القائم.
- **Accept**: بث 100KB بلا تجمّد قابل للقياس (long-task في DevTools — سيناريو
  يدوي موثَّق في QA-T11).
- **Deps**: —

### TSK-402 — backoff+jitter للاتصال + حماية onmessage
- **Fixes**: NF-11 · **Validated-by**: QA-T11
- **Files**: `static/app.js:L154–169`
- **Accept**: سقوط الخادم → فواصل متزايدة بسقف؛ إطار JSON مشوّه → log وتجاهل.
- **Deps**: —

### TSK-403 — إطار scan_start ومؤشر فوري
- **Fixes**: NF-12 / A3 (طلب المستخدم التاريخي) · **Validated-by**: QA-T11
- **Files**: `server.py:_dispatch_chat_message` (إرسال `{"type":"scan_start"}`
  فور الاستلام قبل بناء السياق)؛ `static/app.js:handleWSMessage` (case جديدة →
  "جاري التفكير…")
- **Accept**: مؤشر مرئي ≤200ms من الإرسال في كل الأوضاع.
- **Deps**: —

### TSK-404 — تسييج المحتوى المحقون في البرومبت
- **Fixes**: NF-18 · **Validated-by**: QA-T12
- **Files**: `prompts/templates.py:build_prompt:L104–135`، مواضع الحقن بعد TSK-103
- **Change**: أغلفة حدود صريحة (مثل `<attached-content …>`) + تعليمة system
  بأن المحتوى المرفق بيانات لا أوامر.
- **Accept**: ملف يحوي تعليمة حقن → تصل مسيَّجة؛ فحص نصي للبرومبت المبني (stub).
- **Deps**: TSK-103.

## M5 — Performance & Search

### TSK-501 — فهرس بحث مشترك فوق ProjectIndex
- **Fixes**: NF-20 + NF-21 · **Validated-by**: QA-T13
- **Files**: `server.py:api_search:L609–667`،
  `chain/agent_tools.py:tool_search_code:L269–322`،
  ProjectIndex (خطافات write-through القائمة)
- **Accept**: بحث مستودع 5k ملف < 1s؛ نتائج مطابقة للسلوك القديم على عينة ذهبية.
- **Deps**: TSK-202 (قائمة التجاهل الموحدة يستهلكها الفهرس).

### TSK-502 — توثيق حدود النشر + راية إلزام الموافقة
- **Fixes**: NF-16 · **Validated-by**: QA-T13
- **Files**: قسم deployment في التوثيق؛ مفتاح config `force_command_approval`
  يقلب مواضع `need_approval=False` (`server.py:L769, L1246, L2275`)
- **Accept**: الراية مفعّلة → كل أمر يمر بالموافقة؛ الافتراضي متوافق سلوكيًا.
- **Deps**: —

---

## P5c — رسم تبعيات المهام (لا دورات)

```
TSK-201 ──► TSK-101 ──► TSK-102        TSK-103 ──► TSK-104
   │                                       │
   └──────► TSK-304                        └──────► TSK-404
TSK-202 ──► TSK-501
(جذور مستقلة: 105, 203, 301, 302, 303, 305, 401, 402, 403, 502)
```
كل الحواف باتجاه واحد بلا رجوع → **DAG، صفر دورات**. ✔

## P5b — مصفوفة التتبّع الثنائي الاتجاه

| BUG/NF → TSK | | TSK → Fixes |
|---|---|---|
| BUG-01 → 101 | | 101 → BUG-01 |
| NF-13 → 102 | | 102 → NF-13 |
| BUG-03/NF-09 → 103 | | 103 → BUG-03 |
| NF-07 → 104+303 | | 104 → NF-07(payload) |
| NF-15 → 105 | | 105 → NF-15 |
| NF-23(1) → 201 | | 201 → NF-23(1) |
| BUG-04/NF-23(4) → 202 | | 202 → BUG-04 |
| NF-23(2,3) → 203 | | 203 → NF-23(2,3) |
| NF-01 → 301 | | 301 → NF-01 |
| NF-02 → 302 | | 302 → NF-02 |
| NF-06 → 303 | | 303 → NF-06+NF-07(mem) |
| NF-04 → 304 | | 304 → NF-04 |
| NF-14 → 305 | | 305 → NF-14 |
| NF-10 → 401 | | 401 → NF-10 |
| NF-11 → 402 | | 402 → NF-11 |
| NF-12/A3 → 403 | | 403 → NF-12/A3 |
| NF-18 → 404 | | 404 → NF-18 |
| NF-20/21 → 501 | | 501 → NF-20/21 |
| NF-16 → 502 | | 502 → NF-16 |

**فحص اكتمال C4**: كل C4 غير-إيجابي من P2/P3 (BUG-01, BUG-03-آلية, BUG-04,
NF-04, NF-06, NF-10, NF-11, NF-14, NF-15, NF-16, NF-20, NF-23) له TSK ✔.
الإيجابيات NF-19/NF-24 وNF-17 → QA-T انحداري فقط (P6).
NF-03/05/08 → P7/ملاحظات (قرار P4 موثَّق).
