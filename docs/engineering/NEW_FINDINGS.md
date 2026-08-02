# NEW_FINDINGS.md — editor_v4 (P3 — CORE-ONLY SCOPE v4.1)

> الحالة تُدار في PROGRESS.md فقط. النطاق محكوم بـ SECTION 0.8 — Provider Layer مستبعد.
> كل اقتباس ملف:دالة:سطر مُتحقق منه ساكنًا بهذه الجلسة. المعرّفات NF-xx تُغذي P4/P5.
> سلّم الثقة C1–C4 والشدة S1–S4 كما في VERIFIED_BUGS.md.

---

## (a) Race conditions & Threading

### NF-01 — تنظيف `pending_path_requests` يمشي خارج القفل — سباق تكرار/طفر
**C3 / S3.** `server.py:_clean_expired_pending_requests:L106–114` يبني قائمة المنتهين
بتكرار على `pending_path_requests.items()` **دون** حمل `_pending_path_lock`، بينما
`pop_pending_path_request:L146–148` يطفّر القاموس تحت القفل من خيوط أخرى؛
`store_pending_path_request:L136–139` يستدعي التنظيف **قبل** دخول القفل.
تكرار متزامن مع pop → احتمال `RuntimeError: dictionary changed size during iteration`
أو حذف مزدوج. الإصلاح: نقل التنظيف داخل القفل. → TSK (P5).

### NF-02 — خانة الـ run الحصرية عالمية عبر كل التبويبات (project_id="")
**C3 / S3.** `_begin_run_ticket` (`server.py:L319–331`) يستدعي
`execution_registry.register(kind)` **بلا project_id** → الافتراضي `""`
(`core/execution.py:register:L233`)، والسجل `exclusive_per_project=True` افتراضيًا
(`backends_from_config` core/backends.py:L126–139 يبني `ExecutionRegistry()` بلا وسائط).
النتيجة: **كل الاتصالات/التبويبات تتنافس على خانة واحدة** — تبويب يشغّل chain يمنع
تبويبًا آخر على مشروع مختلف من أي run (يستلم `busy`). يتقاطع مع هدف T-048
(عزل الجلسات). قد يكون سياسة مقصودة لعملية واحدة، لكن الدلالة "لكل مشروع"
في التسمية لا تتحقق فعليًا. → TSK توضيح/تمرير project_id.

### NF-03 — ازدواجية حالة REST-globals مقابل WS-SessionContext (تثبيت g5)
**C4 / S3.** موثَّق عمدًا في `core/session_context.py:L14–27`: تبديل مشروع عبر
REST `/api/switch-project` (`server.py:L1096–1189`) يبدّل `fm`/globals عالميًّا،
بينما WS يبدّل لكل تبويب. REST `api_search`/`api_restore_backup` تعمل على
`fm` العالمي حتى لو كان تبويب المستخدم على مشروع آخر → نتائج/استعادة على
مشروع غير المقصود. سطح التباس مؤكد وإن كان قرارًا واعيًا. → P4 (توحيد لاحق).

### NF-04 — حلقة ws_handler متزامنة: أي handler غير مُخيَّط يحجب الاتصال (تثبيت g6)
**C4 / S3.** `ws_handler` (`server.py:L2213–2229`) حلقة `ws.receive()` تسلسلية.
المسارات الثقيلة مُخيَّطة (chain L1469، agent L1619، delegate L2127 — كلها
`daemon=True`)، لكن `apply_all_actions`/`execute_plan` (L1862–1925) تعمل
**داخل الحلقة**: تطبيق 17 ملفًا + أوامر يجمّد استقبال أي رسالة (ومنها `cancel`)
حتى النهاية. → TSK.

## (b) Async issues

### NF-05 — لا طبقة async؛ خيوط daemon تُقتل بلا join عند الإيقاف
**C3 / S4.** المشروع sync بالكامل (flask_sock + threads) — لا asyncio (grep: صفر
`async def` في server.py). كل خيوط الـ runners `daemon=True` (L1469/L1619/L2127)
بلا join عند shutdown → إيقاف العملية أثناء كتابة إجراءات قد يقطعها في المنتصف
(تخفف الكتابة الذرية أثر الملف الواحد — انظر NF-13). ملاحظة معمارية أكثر منها
عيبًا؛ تُسجَّل لـ P7.

## (c) Memory leaks

### NF-06 — `ExecutionRegistry._tickets` لا يُطهَّر أبدًا — نمو غير محدود
**C4 / S3.** `core/execution.py` كامل: لا يوجد أي `pop/del` على `_tickets`
(grep صفر نتائج)؛ `finish()` يحرر خانة المشروع فقط ويُبقي التذكرة؛ `reap_stale()`
يعلّم `failed` ويُبقيها. كل run (وكل رسالة chat = run "direct" منذ T-040)
يضيف تذكرة تعيش حتى نهاية العملية. جلسة طويلة بمئات الرسائل = نمو خطي دائم،
و`_list_runs_frame` (`server.py:L348`) يكبر معها. → TSK (طَهْر terminal الأقدم).

### NF-07 — `chat_history` بلا حد أعلى (لكل جلسة + العالمي)
**C3 / S3.** `sctx.chat_history` يُلحق به كل دور (L1638، L1667) ويُمرَّر كاملًا
لكل طلب (`L1654: {"history": sctx.chat_history[:-1]}`، وكذلك L1559) — لا اقتطاع
في نقطة الإرسال (grep: لا MAX_HISTORY/trim في server.py وprompts/templates.py).
يتضافر مع BUG-03 (حمولة) ويشكّل نموًا ذاكريًا لكل اتصال معمّر.

### NF-08 — TTL `pending_path_requests` يعمل عند الإضافة فقط
**C2 / S4.** التنظيف يُستدعى حصريًا من `store_pending_path_request:L137` —
بلا إضافات جديدة تبقى المداخل المنتهية (300s) بالذاكرة إلى أجل غير مسمى.
أثر ضئيل (مداخل صغيرة) لكنه نمط "تنظيف مشروط بالنشاط".

## (d) Large-context handling

### NF-09 — (تقاطع BUG-03) مسارات الحقن المباشر خارج الميزانية
مُوثَّق ومصنَّف C4/S2 في `VERIFIED_BUGS.md#BUG-03` — لا يُكرَّر هنا؛ الفئة
تُحال بالكامل إليه + NF-07 (التاريخ الكامل).

## (e) In-app streaming (server→frontend)

### NF-10 — `appendStreamChunk` يعيد بناء الرسالة كاملة عند كل chunk — O(n²)
**C4 / S3.** `static/app.js:appendStreamChunk:L928–962`: كل chunk →
`currentStreamText += text` ثم `parseResponseChannels(النص الكامل)` ثم
`content.innerHTML = renderMarkdown(النص الكامل)` ثم `highlightContainer`.
رد بطول 50KB على chunks صغيرة = آلاف عمليات parse/render التراكمية —
تجمّد الواجهة مع الردود الطويلة (يضخّمه BUG-03). التخفيف الجزئي الوحيد هو
كاش الإبراز (T-064). → TSK (append تدريجي/throttle).

### NF-11 — إعادة اتصال WS بثابت 3s بلا backoff + `JSON.parse` بلا حماية (تثبيت g10)
**C4 / S3.** `static/app.js:initWebSocket:L154–159` — `setTimeout(initWebSocket, 3000)`
دائمًا (لا jitter/backoff/حد أقصى → قصف الخادم عند سقوطه)؛
`onmessage:L166–169` — `JSON.parse(event.data)` بلا try/catch: إطار مشوّه واحد
يرمي استثناء يقتل معالجة الرسالة. → TSK.

### NF-12 — لا إشارة `scan_start` قبل بناء السياق (تقاطع A3)
مُصنَّف C3/S4 في `VERIFIED_BUGS.md#P2e-A3` — أول إطار مرئي هو `start`
(`server.py:L1645`) بعد اكتمال الجمع؛ طلب المستخدم التاريخي (Spinner) قائم.

## (f) Parser ambiguity & mode handling

### تقاطع BUG-01 (C4/S2)
الفئة محكومة بالكامل بـ `VERIFIED_BUGS.md#BUG-01` (parser mode-agnostic +
fallback عدواني + إطار done يحمل actions في chat + الواجهة تعرض بلا فحص وضع).
إضافة واحدة:

### NF-13 — fallback الأوامر يحوّل أسطر بلوكات bash التوضيحية لأوامر قابلة للتنفيذ
**C3 / S2.** `actions/response_parser.py:L153–161`: داخل الـ fallback، كل سطر
غير-تعليق في أي بلوك ```bash يصبح `CommandBlock` — شرح تعليمي يعرض
`rm -rf build/` كمثال يتحول لعنصر قابل للنقر "تشغيل". يقيّده جزئيًا فحص
`DANGEROUS_COMMANDS` (`actions/command_runner.py:L37–42`) لكن مواقع
`need_approval=False` (`server.py:L769, L1246, L2275`) تضعف البوابة. → TSK مع BUG-01.

## (g) Error handling

### NF-14 — ابتلاع صامت واسع النطاق للاستثناءات
**C4 / S3.** 41 موضع `except Exception` في server.py وحده؛ الأنماط الأخطر:
- `server.py:L1338–1339` — فشل قراءة ملف مكتشف → `pass` صامت (المستخدم يظن
  المحتوى أُرفق وهو لم يُرفق).
- `_WSAdapter._send` (`server.py:L233–238`) — أي فشل إرسال يُبتلع (مقصود
  للاتصال المقفول، لكنه يخفي أيضًا أخطاء serialization).
- أثر واجهة: NF-11 (JSON.parse). التوصية: تضييق الأنواع + log موحّد. → TSK.

## (h) Path traversal & Security

### NF-15 — استعادة الباك-أب تفك ZIP بلا فحص أعضاء (Zip-Slip) (تثبيت g8)
**C4 / S2.** `server.py:api_restore_backup:L947–960` — `zf.extractall(fm.root)`
مباشرة: عضو باسم `../../x` أو مسار مطلق يكتب خارج جذر المشروع. الخطر مشروط
بمصدر الـ ZIP (ينشئه `create_full_backup` file_manager.py:L213–236 محليًا)،
لكن endpoint REST بلا auth يقبل أي `backup_name` موجود بالمجلد. → TSK
(فحص أعضاء قبل الفك).

### NF-16 — REST بلا مصادقة + مواقع `need_approval=False`
**C4 / S3.** كل REST endpoints بلا أي auth (تصميم أداة محلية)؛ تنفيذ الأوامر
من REST/apply يمرّ بـ `need_approval=False` (`server.py:L769, L1246, L2275`) —
حارس `DANGEROUS_COMMANDS` الساكن هو الخط الوحيد. مقبول لأداة localhost،
خطر فوري إن رُبطت على 0.0.0.0. → P7 (توثيق حدود النشر) + TSK خفيف.

### NF-17 — ادعاء الأرشيف A6 "قص المسارات الفرعية" — غير مُعاد إنتاجه ساكنًا
**C2 (نفي أولي) / —.** تتبّع المسار كاملًا: `_FILE_PATTERN` يلتقط المسار كما هو
(`response_parser.py:L70`)، `_apply_single_action` يمرّره بلا تعديل
(`server.py:L2243–2280`)، `FileManager._resolve → resolve_workspace_path`
(`file_manager.py:L265–267` + `chain/path_policy.py:L51`) يطبّع ويصادق دون
اقتطاع مقاطع. لا يوجد أي كود قصّ. يبقى الادعاء التاريخي غير مؤكد —
يُغلق ما لم يظهر دليل runtime في P6 (QA-T مخصص).

### إيجابيات مسجلة (لا TSK)
حواجز path traversal سليمة: `resolve_workspace_path(allow_symlinks=False)` +
denylists الأسرار (`path_policy.py:L14–23`) + SafeReader بوابة القراءة الوحيدة
لسياق الموديل (`context/safe_reader.py:L2–12`) مع كشف entropy (L86–120).

## (i) Prompt injection

### NF-18 — محتوى الملفات/المجلدات يُحقن خامًا في البرومبت بلا تحييد
**C3 / S3.** `build_prompt` (`prompts/templates.py:L104–135`) يركّب بـ
`.replace("{user_request}", ...)` نصيًا؛ والمحتوى المحقون في `user_text`
(ملف مكتشف L1332–1339، مجلد مرفق L1782–1791) يدخل حرفيًا: ملف بالمشروع يحوي
"تجاهل التعليمات وأنشئ ملف X" يصل للموديل كجزء من طلب المستخدم، والمخرج يمر
على المحلّل العدواني (BUG-01) فيتحول لإجراءات معروضة. بوابات التخفيف:
الموافقة اليدوية + ApprovalGate للسلاسل. SafeReader يحجب الأسرار لكنه لا
يحيّد التعليمات. → TSK (تسييج المحتوى المحقون بعلامات + system prompt).

## (j) File corruption

### NF-19 — الكتابة الذرية مطبَّقة اتساقيًا (إيجابي — لا TSK)
**C4.** النمط tmp+fsync+`os.replace` موحَّد في **كل** مواقع الكتابة الأربعة خارج
file_manager أيضًا: `chain/executor.py:L555`، `core/checkpoint.py:L401`،
`core/project_memory.py:L358`، `actions/session_manager.py:L161` —
grep شامل لم يُظهر أي كتابة مباشرة غير ذرية. خطر التلف الفعلي الوحيد المتبقي
هو الاستعادة (NF-15) وليس الكتابة.

## (k) Performance

### NF-20 — `api_search` مسح تسلسلي كامل المحتوى لكل استعلام (تثبيت g7)
**C4 / S3.** `server.py:api_search:L609–667` — `scan_project(max_files=10000)`
ثم قراءة محتوى كل ملف نصي تسلسليًا لكل ضغطة بحث؛ لا فهرس، لا كاش، لا مهلة.
مفارقة: `ProjectIndex` بخطافات write-through موجود أصلًا ولا يُستغل هنا. → TSK.

### NF-21 — `tool_search_code` بنفس النمط داخل حلقة الوكيل (يفسّر A1)
**C3 / S3.** `chain/agent_tools.py:tool_search_code:L269–322` — `rglob` لكل
امتداد ثم قراءة كل ملف كاملًا لكل نداء أداة؛ داخل AgentLoop (حتى 6 تكرارات ×
عدة بحثات) يتضاعف. يفسّر بنيويًا "فشل/بطء search_code ×8" التاريخي (A1). → TSK
(مشاركة فهرس واحد مع NF-20).

### NF-22 — واجهة: O(n²) rendering أثناء البث = NF-10 (تقاطع).

## (l) Dead / Duplicate code

### NF-23 — حزمة التكرارات (تثبيت g2/g3/g4 + BUG-04)
**C4 / S3–S4.**
1. كتلتا `apply_all_actions` / `execute_plan` شبه متطابقتين (`server.py:L1862–1893`
   vs `L1895–1925`) — أي إصلاح (مثل BUG-01) يجب أن يُطبَّق مرتين.
2. `MAX_SMART_FILE_SIZE` معرَّف مرتين (`L128`, `L2240`) — تعديل أحدهما فقط = سلوك متشعب.
3. config.yaml يُقرأ inline ≥6 مواضع (`L159, L1083, L2412, L2444, L2489, L2539`).
4. **ثلاث قوائم تجاهل مستقلة غير متزامنة** (file_manager L27–31 / bridge L655–662 /
   agent_tools L300–302) — هي نفسها آلية BUG-04. → TSK توحيد (يفكّ 4 مشاكل معًا).

## (m) Circular dependencies

### NF-24 — لا دورات استيراد (إيجابي — لا TSK)
**C3.** فحص AST آلي هذه الجلسة على 82 موديول داخلي (استبعاد providers/tests/static):
**صفر دورات**. يتسق مع الانضباط المعلن (`core/execution.py:L37`: "core stays
dependency-free of chain") ونمط الحقن في AppContext. يُعاد التحقق في P6 بأداة
CI (pycycle/grimp) ضمن QA-T.

## (n) اكتشافات Stage 3 (أثناء التنفيذ)

### NF-25 — أسماء غير معرّفة في core/chat_dispatch.py (انحدار من TSK-612)
**C4 / S2 — اكتُشف S69 (أدلة TSK-614، mypy --check-untyped-defs + pyflakes).**
`core/chat_dispatch.py:306,307` (`provider_pool`) و`:332` (`approval_gate`)
غير معرّفة في الوحدة — كانتا globals في server الأصلي
(77ca23a:server.py:1827,1853) وسقطتا من خريطة الـ14 رمزًا المحقونة في
deps (§TSK-612). الأثر: `NameError` عند تنفيذ `_agent_send_fn` أو مصنع
AgentLoop ⇒ مسار agent عبر dispatch مكسور منذ دمج 612. لم يُكتشف لأن
التحقق العكسي سطرًا-بسطر لا يلتقط تغيّر سياق الوحدة لسطر لم يُعدَّل،
ولا اختبار يقود agent حتى نداء الإرسال. → يُصلح ضمن TSK-614 (استعادة
دلالة ما قبل 612: حقنهما في deps + بادئة `deps.`).

### NF-26 — تقطيع dict في إرفاق مجلد كسياق (server.py:1180)
**C4 / S3 — اكتُشف S69 (نفس الفحص)؛ قائم منذ 0d74dad (عصر TSK-404).**
`scan_folder_for_chain` يرجع `dict[str, str]` (chain/bridge.py:666–681،
التوثيق `{relative_path: content}`) بينما `server.py:1180–1184` يعامله
كقائمة dicts (`scanned_files[:15]` ثم `sf.get("rel_path")`) ⇒
`TypeError: unhashable type 'slice'` يبتلعه `except Exception` (:1188)
⇒ إرفاق المجلد يتدهور صامتًا (header بلا محتوى) — عكس قبول
TSK-404/BUG-03. → يُصلح ضمن TSK-614 (`list(scanned_files.items())[:15]`)
مع اختبار تغطية جديد.

### NF-27 — موافقة زائفة عبر Event مشترك عند التزامن (approval.py:173/256)
**C5 / S2 — اكتُشف S71 (أدلة TSK-615، تجربة حية موثقة في §TSK-615).**
توصيف ASF-05 (MASTER_REVIEW:327) قال «fail-closed — استنزاف موافقات
فقط». التجربة الحية تُظهر الأسوأ: `_pending_event` **واحد مشترك** بين
كل المنتظرين — عند طلبين متداخلين r1/r2 واعتماد المستخدم r2،
`resolve` يطابق r2 ويضبط `_pending_result=True` ثم `set()` يوقظ
**الخيطين معًا** وكلاهما يقرأ النتيجة المشتركة ⇒ **r1 يُعتمد دون أن
يوافق المستخدم عليه** (`user_approved` في التدقيق للاثنين). أي أن
الكسر عند التزامن fail-OPEN لا fail-closed (يشمل رفض r2 ⇒ r1 يسجَّل
`user_denied` زورًا — تلويث تدقيق). حصر الأثر: يتطلب طلبين تفاعليين
متداخلين زمنيًا (chain + agent مثلًا) — نادر في الاستخدام أحادي
المستخدم لكنه بوابة الموافقات = أعلى حساسية. [SUPERSEDES جزئيًا
توصيف ASF-05 «fail-closed» — الاستنزاف (سيناريو B) يبقى صحيحًا].
→ يُصلح في TSK-615 (Event لكل طلب في خريطة مفتاحية) مع اختبارات
السيناريوهات A/B/C/D.

### NF-28 — فحص symlink ميت بالكامل: الرفض نفسه يُبتلع (path_policy.py:102–108)
**C4 / S2 — اكتُشف S73 (أدلة TSK-618، تجربة حية موثقة في §TSK-618).**
توصيف ASF-07 (MASTER_REVIEW:329) قال «خطأ FS أثناء is_symlink ⇒
تخطٍّ صامت للفحص». التجربة الحية تُظهر الأسوأ: `raise
PermissionError` (الرفض ذاته) يقع **داخل نفس الـ try** الذي يلتقط
`except Exception: pass` — وPermissionError ⊂ OSError ⊂ Exception ⇒
**كل رفض symlink يُبتلع فور رفعه**: الفحص لا يرفض شيئًا منذ
كتابته، لا فقط عند خطأ FS. تجربة حية: symlink داخلي لملف داخلي
**يمر** (A)؛ ملف عبر مجلد symlink **يمر** (B). حصر الأثر: الخطان
الصلبان يصمدان — الاحتواء على المسار المحلول يرفض الهروب خارج
الجذر (C)، وفحص الأسرار على المحلول يرفض ألياس السر الداخلي
(D) ⇒ المفقود هو طبقة الدفاع الإضافية (رفض symlinks الداخلية
كسياسة) لا الاحتواء ذاته. [SUPERSEDES جزئيًا توصيف ASF-07
«تخطٍّ عند خطأ FS» — الفحص ميت دائمًا].
→ يُصلح في TSK-618 (فصل القياس عن القرار: is_symlink داخل try
ضيق يلتقط OSError موسومًا بسجل؛ raise خارجه) مع اختبارات A–D.

---

## جدول تجميعي (مدخل P4/P5)

| NF | الفئة | C | S | TSK مطلوب؟ |
|---|---|---|---|---|
| NF-01 | سباق تنظيف pending | C3 | S3 | نعم |
| NF-02 | خانة run عالمية | C3 | S3 | نعم (توضيح/إصلاح) |
| NF-03 | ازدواجية REST/WS | C4 | S3 | P4 قرار معماري |
| NF-04 | حلقة WS محجوبة بـ apply | C4 | S3 | نعم |
| NF-05 | خيوط daemon بلا join | C3 | S4 | P7 |
| NF-06 | تذاكر السجل لا تُطهَّر | C4 | S3 | نعم |
| NF-07 | تاريخ بلا حد | C3 | S3 | نعم (مع BUG-03) |
| NF-08 | TTL مشروط بالنشاط | C2 | S4 | لا (ملاحظة) |
| NF-10 | بث O(n²) بالواجهة | C4 | S3 | نعم |
| NF-11 | reconnect ثابت + JSON.parse | C4 | S3 | نعم |
| NF-13 | fallback الأوامر | C3 | S2 | نعم (مع BUG-01) |
| NF-14 | ابتلاع استثناءات | C4 | S3 | نعم |
| NF-15 | Zip-Slip بالاستعادة | C4 | S2 | نعم |
| NF-16 | REST بلا auth / need_approval=False | C4 | S3 | P7 + TSK خفيف |
| NF-17 | ادعاء A6 غير مُعاد إنتاجه | C2 | — | QA-T فقط |
| NF-18 | حقن برومبت خام | C3 | S3 | نعم |
| NF-19 | كتابة ذرية متسقة | C4 | ✅ | لا |
| NF-20 | api_search تسلسلي | C4 | S3 | نعم |
| NF-21 | tool_search_code تسلسلي | C3 | S3 | نعم (مع NF-20) |
| NF-23 | حزمة التكرارات | C4 | S3 | نعم |
| NF-24 | لا دورات استيراد | C3 | ✅ | لا |
| NF-25 | أسماء غير معرّفة في chat_dispatch (انحدار 612) | C4 | S2 | ضمن TSK-614 |
| NF-26 | تقطيع dict بإرفاق المجلد (منذ 0d74dad) | C4 | S3 | ضمن TSK-614 |
| NF-27 | موافقة زائفة بتزامن الطلبات (Event مشترك) | C5 | S2 | ضمن TSK-615 |
| NF-28 | فحص symlink ميت — الرفض نفسه يُبتلع | C4 | S2 | ضمن TSK-618 |

(NF-09/12/22 تقاطعات مُحالة — بلا صفوف مستقلة.)

## DoD
كل بند باقتباس ملف:دالة:سطر فعلي؛ صفر أسرار؛ `providers/` لم يُمس؛
كل C4 غير-إيجابي مُعلَّم "نعم TSK" ويُستوفى في P5.

---

## CEV Findings — برنامج CEV (D-12، فتح 2026-08-01/S106) — append-only

> معرّفات هذا البرنامج: CEV-F-xxx (استمرار سلالم C/S نفسها — لا سلالم جديدة).

### CEV-F-001 — بوابة mypy غير مثبتة النسخة: mypy 2.3.0 يكسر check.sh على clone نظيف
**C1 / S2.** الدليل المعاد إنتاجه حيًّا (S106 @ b7c5b41): `pip install -r
requirements-dev.txt` على بيئة جديدة يجلب **mypy 2.3.0** (القيد الحالي
`requirements-dev.txt:5` = `mypy>=1.10` بلا سقف)، فتفشل بوابة check.sh
بـ9 أخطاء كلها في `providers/you_com.py:30-31` + `perplexity.py:30-31` +
`blackbox.py:30-31` (نمط واحد: `module_from_spec(spec)` حيث
`spec: ModuleSpec | None` — تشديد استدلال في mypy 2.x). الملفات نفسها
**خارج النطاق بالاتجاهين (§0.8)** فلا تُصلح؛ الجذر بيئي: غياب سقف نسخة.
التحقق: التثبيت `mypy>=1.10,<2` (⇒ 1.20.2) يعيد البوابة إلى سلوكها
الموثَّق. **الأثر**: أي استئناف بيئة-تتصفّر (سيناريو D-8-ج المتكرر —
7+ تصفيرات موثقة) يبدأ ببوابة حمراء زائفة ⇒ يهدد صحة كل خطوط الأساس
القادمة. **الإصلاح المقترح (TSK صغيرة)**: إضافة سقف `,<2` في
requirements-dev.txt + سطر تعليل (خطأ providers قائم خارج النطاق —
يُرفع السقف يوم يُحسم خارجيًا). لا مساس بـproviders/ ولا بإعدادات mypy.
→ TSK ضمن BATCH-CEV-G1.

### CEV-F-001 [تحديث الجذر — S106ب] — الجذر الحقيقي ليس نسخة mypy بل كود جديد خارج الحوكمة
**C1 / S2 → يتفرع.** التحقيق الأعمق نفى فرضية «انجراف نسخة mypy»: الأخطاء
التسعة تُعاد إنتاجها حتى بـ mypy==1.10.0 (الحد الأدنى المعلن). الجذر
المُثبت: **commit `c9ab00c` (المالك، 2026-08-01 18:14) أضاف 3 مزودات
جديدة** `providers/{you_com,perplexity,blackbox}.py` (+ إعادة ترتيب
pool.py) **بعد** آخر خط أساس أخضر (S105/2168P) — بنمط
`module_from_spec(spec)` بلا حارس None (`:30-31` في الثلاثة). ومعه
**commit `8dd9e8a` (المالك) عدّل server.py (+92 سطرًا — داخل النطاق)**
لتسجيل المزودات الثلاثة. يبقى من CEV-F-001 الأصلي بندان صالحان:
(أ) mypy بلا سقف نسخة في requirements-dev/CI (هشاشة قائمة وإن لم تكن
جذر هذا الفشل)؛ (ب) types-requests/types-PyYAML غائبتان عن
requirements-dev — بيئة نظيفة تفشل بـ`Library stubs not installed`
(أُعيد إنتاجها S106). **المعالجة**: providers/ خارج النطاق §0.8 —
لا يُصلح الكود؛ الخيارات للمالك: (1) إصلاح النمط بنفسه (3 أسطر حارس
spec-None لكل ملف)، أو (2) توسيع استثناء mypy الموجود
(`--exclude 'providers/openai_shelby\.py'`) ليشمل الثلاثة بقرار موثَّق
(سابقة ADR-004 القائمة). تعديل server.py الوارد يُدقَّق ضمن G6/G8.

### CEV-F-002 — بوابة check.sh حمراء على HEAD: خط الأساس 2168P/34S غير قابل لإعادة الإنتاج حاليًا
**C1 / S2.** على clone نظيف @ ba2d9f0 (ثم 4ebd965): `bash scripts/check.sh`
= RC=1 عند بوابة mypy (أخطاء CEV-F-001 التسعة) قبل الوصول لـpytest.
البرنامج CEV يشترط (G9) خط أساس أخضر حيًّا — **حاجز يجب فكه قبل إقفال
أي TSK**. → BATCH-CEV-G1 أول أولوية.

### CEV-F-003 — قيد التنظيف ba2d9f0 حذف fixture مطلوبة: tests/fixtures/sample_project/.env
**C1 / S2.** الدليل الحي (S106ب): `pytest -k sample_project_fixture_isolated`
= FAILED — `test_fake_provider.py:62` يشترط وجود `.env` بمحتوى FAKE
(fixture أضيفت مع TSK-730-era @ a9f52b5، محتواها **مزيف موثَّق**:
«FAKE credentials — NOT real secrets»). قيد البوت ba2d9f0 («تنظيف بيئة
الاختبار») اجتث الـfixture ضمن تنظيف ملفات Qwen الدخيلة — إيجابية
كاذبة في التنظيف. **الإصلاح المفوَّض** (استرجاع محتوى تاريخي، لا ملف
جديد): استعادة `.env` من `git show a9f52b5:...` — منفَّذ S106ب.

### CEV-F-004 — أصول واردة خارج الحوكمة تنتظر التدقيق (سجل حصر)
**C2 / S3.** وردت على main بين S105 وS106 بلا دورة TSK: (1) المزودات
الثلاثة + pool.py (خارج النطاق — تُحصر فقط)؛ (2) **server.py +92 سطرًا
@ 8dd9e8a (داخل النطاق!)** — قائمة نماذج hardcoded ضخمة في
`/api/providers` (أسماء نماذج مثل gateway-claude-sonnet-5 …) تُدقَّق
في G6 (تضخم/تكرار بنية) وG8؛ (3) `docs/docs/Zizo_Maestro…/cont22.md`
(نسخة مالك من تكليف CEV — توثيقية، لا فعل)؛ (4) موجة ملفات جذر
(tasks.md/live_test_v100.py/test_qwen_integration.py/user_feature_test.py)
أضيفت وحُذفت 3 مرات — زالت من HEAD؛ أثرها الوحيد الباقي كان حذف
الـfixture (CEV-F-003). لا حاجة TSK لـ(3)/(4) — حُصرا.

### CEV-F-005 — استيرادات/معاملات ميتة مؤكدة (G1، vulture ≥90% + تحقق يدوي)
**C2 / S4.** مسح vulture مع فرز يدوي شامل (grep على كامل الشجرة لكل
مرشح — CEV-R3). **ميت مؤكد (8+1):**
(1) `chain/executor.py:35` — خمسة استيرادات من providers.base بلا أي
استخدام: `history_to_messages, MalformedProviderResponseError,
MockProvider, ProviderContextTooLargeError, ProviderMessage`
(مستهلكو MockProvider الأربعة الخارجيون يستوردون مباشرة من
providers.base، لا عبر executor).
(2) `server.py:16` — `import queue` (صفر استخدام في 2358 سطرًا).
(3) `server.py:40` — `get_provider, list_providers` (صفر استخدام في
server/routes/tests).
(4) `chain/delegate.py:660` — معامل `original_files` في
`_extract_touched_files` لا يُلمَس في الجسم (regex على `response`
فقط)؛ المستدعي الوحيد `delegate.py:364` يمرر `brief.files_context`
بلا أثر. إزالته = تغيير توقيع دالة خاصة بمستدعٍ واحد — آمن.
**إيجابيات كاذبة مستبعدة:** `chain/router.py:27 BudgetSnapshot` —
داخل `if TYPE_CHECKING:` ومستخدم كتوصيف نصي ×4
(`:195/:246/:325/:372`) — يبقى. المعالجة: BATCH-CEV-G1 (إزالة
الاستيرادات الميتة + سقف mypy + stubs في requirements-dev) — تنتظر
فك حاصر CEV-F-002.

### CEV-F-002 — تحديث الإغلاق (S106د): الحاصر انفكّ بقرار D-13
**مُغلق.** أمر المالك «أفتح BATCH-CEV-G1 وأتابع بوابات CEV» + تحقق حي
أن الخيار 1 لم يُنفَّذ (providers بلا حارس None @ e6c9100) ⇒ تفويض
الخيار 2. نُفِّذ TSK-CEV-102: توسيع استثناء mypy في check.sh إلى
`providers/(openai_shelby|you_com|perplexity|blackbox)\.py` بسابقة
ADR-004 + تحديث الحارس test_mypy_gate_614 (يثبّت الاستثناءات الموثقة
حصريًا + `--exclude` واحد + لا استثناء داخلي). **البوابة الكاملة:
check.sh ALL GREEN RC=0 — 2189P/34S/0F.** يُرفع الاستثناء يوم يُصلح
المالك نمط module_from_spec (حارس None قبل :30-31 في الملفات الثلاثة).

### CEV-F-006 — اختباران flaky حمل-بيئي موثَّقان (ليسا انحدارًا)
**C3 / S4.** أثناء بوابات إقفال BATCH-CEV-G1 (S106د) فشل — كلٌّ مرة
واحدة غير متكررة — (1) `test_index_snapshot_wiring.py::
test_no_save_churn_when_list_unchanged` (فرق mtime_ns 4ms تحت حمل
الحزمة الكاملة؛ دقة mtime على tmpfs الساندبوكس تسمح دلتا-صفر بين
كتابتين متتاليتين — probe موثَّق) و(2) `test_search_perf.py::
TestPerf5k::test_tool_search_code_path_under_1s` (سابقة S84 الموثقة:
عتبة 1s على عتاد متغير). كلاهما يمر معزولًا ×3 ومعًا وفي التشغيلة
النظيفة (ALL GREEN ×2 هذه الجلسة). لا فعل الآن؛ مرشحان لتقسية عتبات
في بوابة لاحقة (G7 اختبارات) إن تكررا.

### CEV-F-007 — favicon.ico مفقود (404 وحيد في التحميل الحي)
**C4 / S5.** فحص G2 الحي (Playwright على خادم فعلي): تحميل الواجهة
كامل بصفر أخطاء JS؛ الطلب الفاشل الوحيد `GET /favicon.ico = 404`
(server log). لا favicon في المشروع أصلًا. تجميلي بحت — إضافة أصل
بصري (هوية) قرار مالك (CEV-R11: لا اختراع أصول). لا فعل الآن.

### CEV-F-003 — تحديث تكرار (S106و): البوت حذف الـ fixture مرة ثانية
**متكرر — يرقى لنمط.** Auto-Uploader حذف
`tests/fixtures/sample_project/.env` مجددًا @ 37a371f (2026-08-02
03:49 — «حذف ملف البيئة الوهمي من بيانات الاختبار الثابتة»)، بعد
استعادتها الموثقة في S106ب. أُعيدت الاستعادة من a9f52b5 والاختبار
الحارس يمر. **السلوك منهجي**: منطق تنظيف البوت يعامل أي `.env` كسر
حقيقي رغم ترويسة «FAKE credentials — NOT real secrets». **خياران
للمالك (قرار مطلوب — التكرار سيستمر بدونه):** (أ) استثناء المسار
`tests/fixtures/` من منطق تنظيف البوت (البوت خارج المستودع — بيد
المالك)؛ (ب) تفويض إعادة تسمية الـ fixture إلى `env.fixture` أو
`dot_env.txt` مع تحديث المستهلكين (`tests/unit/test_fake_provider.py`
+ أي مسار SafeReader يقرأها) — تغيير كود داخل النطاق يقفل الثغرة
نهائيًا لكن يلزمه TSK صغير.
