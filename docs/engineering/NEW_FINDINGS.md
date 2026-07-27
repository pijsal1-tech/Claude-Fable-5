# NEW_FINDINGS.md — editor_v4 (P3 — CORE-ONLY SCOPE v4.1)

> الحالة تُدار في PROGRESS.md فقط. النطاق محكوم بـ SECTION 0.8 — Provider Layer مستبعد.
> كل اقتباس ملف:دالة:سطر أُخذ من قراءة فعلية بهذه الجلسة (Session 4).
> ترقيم الاكتشافات: NF-XX. سلّم الثقة C1–C4 والشدة S1–S4 كما في VERIFIED_BUGS.md.

---

## (a) Race conditions & threading

### NF-01 — سباق تنظيف `pending_path_requests` خارج القفل — **C4 / S3**
- `server.py:_clean_expired_pending_requests:L106–114` — الدالة **تمشي على القاموس
  وتحذف منه بلا أي قفل**، بينما `store_pending_path_request:L138–141`
  و`pop_pending_path_request:L144–147` يطفّران نفس القاموس تحت
  `_pending_path_lock` (L133). التنظيف يُستدعى من `store_...` **قبل** دخول القفل.
- السيناريو: خيطا WS (تبويبان) — أحدهما يخزّن (فيُنظّف بلا قفل: comprehension على
  `items()`) والآخر يعمل `pop` تحت القفل → `RuntimeError: dictionary changed size
  during iteration` أو حذف مزدوج صامت.
- الإصلاح البديهي: نقل جسم التنظيف داخل `with _pending_path_lock`. → TSK (P5).

### NF-02 — Lost-update في `SessionManager.append_message` (قراءة-تعديل-كتابة كاملة بلا قفل) — **C4 / S3**
- `actions/session_manager.py:append_message:L53–75` — النمط: `_load` الملف كاملًا
  → append في الذاكرة → `_save_full` (ذري بحد ذاته L156–169). **لا قفل حول
  السلسلة**.
- من يستدعيها بالتوازي فعليًا: خيط الـ agent المنبثق
  (`server.py:_run_agent:L1590–1592` عبر `sctx.session_mgr.append_message`)
  وخيط حلقة WS نفسه (L1455–1456, L1531–1532, L1640–1641) — نفس `session_mgr`
  مرجع مشترك مثبّت وقت الاتصال، وتبويبان قد يشيران لنفس الجلسة.
- النتيجة: رسالة تُفقد بصمت (الكتابة الأخيرة تفوز). ليست إفسادًا للملف
  (الكتابة ذرية) بل فقدان سجل. → TSK.
- ملاحظة نطاق: `sessions/store.py:append_message:L294–299` (المخزن الأحدث JSONL)
  إلحاقي بطبيعته وأقل عرضة — الخطر في `actions/session_manager.py` القديم.

### NF-03 — `sctx.chat_history` يُطفَّر من خيطين بلا انضباط معلن — **C3 / S3**
- الإلحاق يحدث من خيط WS (`server.py:L1454, L1483, L1531, L1639`) **ومن خيط
  الـ agent المنبثق** (`_run_agent:L1590`)، والقراءة بنسخ شريحة
  `sctx.chat_history[:-1]` (L1559, L1654) من خيط WS.
- `list.append` ذري تحت GIL فلا انهيار، لكن الترتيب غير محدد: رسالة مستخدم
  جديدة (حلقة WS تستقبل أثناء عمل agent) قد تسبق رد assistant للطلب الأقدم →
  تاريخ محادثة مُشوّه التسلسل يصل للنموذج التالي. → TSK (توثيق/تسلسل لكل جلسة).

### NF-04 — ازدواجية الحالة REST-globals مقابل WS-SessionContext (ترقية g5) — **C4 / S3**
- REST يعمل على globals: `server.py:L119–124` (`fm`, `cmd_runner`, `chat_history`)
  و`api_switch_project:L1096–1189` يبدّل **عالميًّا** (`global fm, cmd_runner,
  chat_history` L1099)، بينما WS معزول لكل اتصال
  (`core/session_context.py:L14–27` — سلوك مقصود T-048/R-701 وموثَّق).
- الخطر المتبقي رغم القصدية: `api_restore_backup:L947–960` وendpoints القراءة
  (L847, L852–854) تقرأ/تكتب حالة عالمية قد لا تطابق ما يراه أي تبويب —
  التباس تشغيلي وليس عيب تزامن خالص. → TSK توثيق + تحذير UI.

### NF-05 — حلقة `ws_handler` متزامنة: `apply_all_actions` يحجب الاتصال (ترقية g6) — **C4 / S3**
- `server.py:ws_handler:L2213–2225` — حلقة `receive→handle` متزامنة واحدة.
  المسارات الثقيلة (chain L1469، agent L1619، بث مباشر L2127) مُخيَّطة، لكن
  `apply_all_actions`/`execute_plan` (L1862–1893, L1895–1925) تنفّذ الكتابات
  والأوامر **داخل الحلقة**: أمر بطيء (`cmd_runner.run` مهلة 120s) يجمّد
  استقبال أي إطار — بما فيها `cancel`. → TSK.

## (b) Async issues

### NF-06 — لا طبقة async فعلية؛ التوقف الوحيد القابل للأذى هو NF-05 — **C3 / ملاحظة**
- الخادم flask_sock خيطي متزامن بالكامل (لا asyncio). لا كوروتينات معلّقة ولا
  await-races. البند يُغلق بإحالة إلى NF-05 (حجب الحلقة) وNF-13 (الواجهة).
  لا TSK مستقل.

## (c) Memory leaks

### NF-07 — `ExecutionRegistry._tickets` ينمو بلا حدود (لا حصاد للتذاكر المنتهية) — **C4 / S3**
- `core/execution.py:ExecutionRegistry` — `_tickets: dict` (L227) يُضاف إليه في
  `register()` (L246) **ولا يوجد أي مسار حذف**: `finish()` L281–299 يحرّر خانة
  المشروع فقط ويبقي التذكرة؛ `reap_stale()` L320–346 يغيّر الحالة ولا يحذف؛
  grep على `del self._tickets|pop|clear` = موضع واحد فقط لـ `_active_by_project`.
- عملية خادم طويلة العمر = تذكرة لكل رسالة direct/chain/agent → نمو خطي دائم.
  `list_all()` موثّقة كميزة (runs_list) فالحل اقتطاع بحد أقصى للمنتهية. → TSK.

### NF-08 — نمو غير محدود لتواريخ المحادثة (global + per-session) — **C4 / S3**
- `server.py:L123` — `chat_history` العالمي بلا أي حد؛ `sctx.chat_history`
  (session_context) كذلك؛ ويُمرَّر كاملًا لكل طلب (L1559, L1654 —
  تقاطع مع BUG-03). لا اقتطاع في أي موضع إلحاق. → TSK (حد + نافذة).

### NF-09 — `RetentionPolicy` مشحونة بوضع dry_run افتراضيًا → `.ai_runs/` يتراكم فعليًا — **C3 / S4**
- `sessions/retention.py:L38–48` — `dry_run: bool = True` («الافتراضي الآمن»)؛
  التنظيف الحقيقي يتطلب `retention.dry_run: false` يدويًا في config. سلوك مقصود
  وموثَّق، لكن أثره العملي = التسريب مستمر حتى تفعيل صريح. → P7 (تفعيل موجَّه).

## (d) Large-context handling

### NF-10 — (مُغطى جوهريًا بـ BUG-03) + ثغرة تفتيش الأسرار في مسارات الحقن المباشر — **C4 / S2**
- `context/safe_reader.py:L86–120` — تفتيش الأسرار بالإنتروبيا يعمل **فقط** في
  مسار `context/` (`facade.py:L46–48` هو المستهلك). أما مسارا الحقن المباشر في
  الخادم — قراءة ملف مكتشف `server.py:L1332–1339` وإرفاق مجلد L1782–1791 —
  فيقرآن **بلا SafeReader**: ملف أسرار يذكره المستخدم بمساره يُحقن نصه في
  البرومبت متجاوزًا بوابة R-204 (و`is_secret_file` في path_policy تُطبَّق على
  أدوات الوكيل لا على هذا المسار). تقاطع مع (i). → TSK.

## (e) In-app streaming (server→frontend)

### NF-11 — انضباط الإرسال سليم بنيويًا (موقع send أوحد بقفل) — لا اكتشاف سلبي
- `server.py:_WSAdapter:L210–238` — قفل لكل اتصال حول `ws.send`، وcheck.sh
  يمنع بالـ grep أي send خارجه؛ `_agent_ws_send` L1516–1522 يضيف قفلًا ثانيًا
  متداخلًا (زائد عن الحاجة لكنه غير ضار). يُسجَّل كنقطة قوة.

### NF-12 — غياب أي إشارة مبكرة قبل إطار `start` (ترقية A3) — **C3 / S4**
- لا يوجد إطار `scan_start`/typing في `server.py` (grep صفر)؛ أول إطار مرئي
  `{"type": "start"}` يُرسل **بعد** اكتمال بناء السياق (L1645) الذي قد يستغرق
  ثواني (فحص ملفات + فهرسة). المستخدم يرى صمتًا (شكوى «اول برومت» حرفيًا). → TSK.

### NF-13 — إعادة اتصال الواجهة بثابت 3s بلا backoff + `JSON.parse` بلا حماية — **C4 / S3**
- `static/app.js:initWebSocket:L154–159` — `setTimeout(initWebSocket, 3000)`
  ثابت بلا jitter/حد محاولات (عاصفة إعادة اتصال عند سقوط الخادم)؛
  `onmessage:L166–169` — `JSON.parse(event.data)` بلا try/catch: إطار مشوّه
  واحد يرمي استثناءً ويُسقط معالجة الرسالة. → TSK.

## (f) Parser ambiguity & mode handling

### NF-14 — (مُغطى بـ BUG-01) + حقن قوالب في `build_prompt` عبر `.replace` المتسلسل — **C3 / S3**
- `prompts/templates.py:build_prompt:L104–135` — القوالب تُملأ بسلسلة
  `.replace("{user_request}", user_request).replace("{project_context}", context)`.
  إذا احتوى **نص المستخدم نفسه** الرمز `{project_context}` (أو
  `{target_files}` في وضع edit) فإن الاستبدال اللاحق يستبدله أيضًا →
  حقن سياق المشروع في موضع من اختيار المستخدم/النموذج (template injection).
  الإصلاح: استبدال واحد ممرّر بقاموس أو `str.format_map` محصّن. → TSK.

## (g) Error handling

### NF-15 — ابتلاع أخطاء واسع وصامت في server.py — **C4 / S3**
- إحصاء هذه الجلسة: **41 موضع `except Exception` + 1 `except:` عارٍ** في
  server.py وحده؛ مواضع حرجة تبتلع بـ `pass` بلا أي log:
  `_WSAdapter._send:L233–238` (كل أخطاء الإرسال)، قراءة الملف المكتشف
  L1338–1339 («تجاهل أخطاء القراءة»)، L1092، L1975. فشل صامت = تشخيص مستحيل
  ميدانيًا (نمط T01 التاريخي: «فشلت الأداة 8 مرات» بلا أثر). → TSK (سياسة log
  دنيا موحّدة على الأقل).

## (h) Path traversal & security

### NF-16 — إعادة فحص ادعاء A6 «قص المسارات»: **لم يُعثر على قصّ في مسار الكتابة — Refuted (ساكنًا)**
- المسار الكامل: `parser` يحافظ على `path` كما التُقط (`response_parser.py:L112–117`
  — `match.group(1).strip()` فقط) → `_apply_single_action:L2265–2270` يمرّره
  حرفيًا → `fm.write_file` → `_resolve` (`file_manager.py:L265–267`) →
  `resolve_workspace_path` (`chain/path_policy.py:L51`) الذي يطبّع ويقيّد داخل
  الجذر **دون بتر مقاطع فرعية**. الادعاء التاريخي يبقى غير مُثبت؛ إن ظهر
  ميدانيًا فمصدره المرجّح fallback التسمية المقترحة (BUG-01: اسم بلا مسار فرعي
  أصلًا) لا «قص». يُسجَّل Refuted-static + توصية QA-T لإعادة السيناريو. → P6.

### NF-17 — استعادة الباك-أب بـ `extractall` بلا فحص أعضاء (Zip-Slip) (ترقية g8-1) — **C4 / S2**
- `server.py:api_restore_backup:L947–960` — `zf.extractall(fm.root)` مباشرة:
  أرشيف يحوي عضوًا `../../x` أو مسارًا مطلقًا يكتب خارج الجذر. الأرشيفات
  ينتجها النظام نفسه عادة (`create_full_backup` file_manager.py:L213–236) لكن
  الـ endpoint يقبل أي اسم ملف موجود في مجلد الباك-أب، وREST كله بلا
  مصادقة (NF-18) — سطح هجوم فعلي إن كان المنفذ مكشوفًا. → TSK (فحص أعضاء
  قبل الاستخراج).

### NF-18 — REST بلا أي مصادقة + تنفيذ أوامر بـ `need_approval=False` (ترقية g8-2/3) — **C4 / S2 (بافتراض تشغيل محلي، S1 إن كُشف المنفذ)**
- لا يوجد أي فحص auth على مسارات REST (تصفح P1 الكامل + grep على
  auth/token/session في تسجيل المسارات — صفر)؛ ومواقع تنفيذ الأوامر تمرّر
  `need_approval=False` صراحة: `server.py:L769, L1246, L2275` — بوابة
  `DANGEROUS_COMMANDS` (`command_runner.py:L37–42`) تبقى، لكن أي أمر غير
  مُدرج فيها ينفَّذ ف
