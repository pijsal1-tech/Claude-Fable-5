# PROGRESS_ARCHIVE_2 — قيود سجل الجلسات S84–S99 (حقبة V3 المبكرة)
> رُحِّلت من PROGRESS.md بتدوير §6.4 (2026-08-02, S106/CEV) — append-only، لا يُعدَّل.

- **2026-07-30 — Session 99 — تفصيل TSK-722 (D-7) — Settings UI تنقسم 722a+722b قراءة-فقط**:
  استئناف بعد تصفير بيئة ×2 (طقس §3.1: clone @ f34d376 ثم f7830ea، تطهير
  remote، الهوية). **جرد التفصيل**: config.yaml قُرئ كاملًا (221 سطرًا —
  17 قسمًا فعالًا)؛ معمارية القراءة: `_load_config()` @ server.py:170
  (مُكاش، تسامحي ⇒ {})، alias `_read_config` @ :187،
  `_force_command_approval` @ :190 (افتراضي fail-closed True — D-1/TSK-617)؛
  الواجهة: زر «الإعدادات» @ index.html:271 يستدعي toggleThemePicker()
  فقط — لا لوحة إعدادات. **قرار النطاق**: قراءة-فقط حصريًا على سابقة
  TSK-621 (glass box)؛ **أي مسار كتابة config عبر HTTP مؤجَّل صراحةً
  كقرار مالك منفصل** (مفاتيح fail-closed لا تُقلب من متصفح + config
  مُكاش يتطلب عقد invalidation). **التقسيم (D-7 — مهام صغيرة)**:
  TSK-722a = `GET /api/settings` مُطهَّر (whitelist أقسام صريح؛ استبعاد
  كلي لقسم providers وproject_root — راية project_root_set فقط؛ توسيع
  سطح REST 32→33 موثَّق) → TSK-722b = لوحة عرض-فقط (settings_panel.js
  نمط permissions_panel.js + اختبارات node). التعريف الكامل حلّ محل
  الـ placeholder في DEVELOPMENT_TASKS §BATCH-P1 (كتبه هذا التفصيل؛
  وصل origin عبر Auto-Uploader @ f7830ea أثناء تصفير البيئة — تحقّق
  المحتوى بعد الاستنساخ). هذا القيد يسبق التنفيذ (D-7).
  **TSK-722a ✅ (نفس الجلسة)**: `GET /api/settings` (routes/meta.py —
  نمط api_permissions): whitelist أقسام صريح (8 مفاتيح بسيطة + agent/
  context_budget/history/context.semantic/session_binding/execution/
  routing بمفاتيح فرعية معلومة فقط — المفتاح غير المعلوم يُسقط)؛
  استبعاد كلي لقسم providers؛ project_root ⇒ راية project_root_set
  فقط؛ retention.pinned ⇒ pinned_count عدد فقط؛ force_command_approval
  = {effective من _force_command_approval() fail-closed, explicit_in_config}.
  توسيع سطح REST المجمَّد 32→33 موثَّق (test_rest_blueprints — توسيع
  مقصود ثالث بعد 621/721). 6 اختبارات جديدة
  (test_settings_endpoint.py): whitelist حي + عدم-تسريب (config مزروع
  بـ sk-/ghp_ في providers ⇒ صفر أنماط في الحصيلة) + لا-مسارات +
  راية fail-closed عند config فارغ + GET-فقط (POST/PUT ⇒ 405).
  **البوابة**: check.sh ALL GREEN rc=0 — **1962P/34S** (1956+6).
  **TSK-722b ✅ (نفس الجلسة — بعد تصفير بيئة ثالث؛ كود اللوحة نجا عبر
  Auto-Uploader @ b3218e1 وتحقّق بعد الاستنساخ)**: لوحة الإعدادات
  عرض-فقط — settings_panel.js (UMD-lite نقي، نمط permissions_panel.js:
  renderPanelHTML + escapeHtml + fmtValue؛ الغائب ⇒ UNKNOWN صريح؛
  ملاحظة «التعديل عبر config.yaml + إعادة تشغيل» ظاهرة؛ الأقسام تعيد
  استخدام أصناف pp-*) + toggleSettingsPanel في app.js (fetch + render
  فقط) + زر Settings في activity bar تحوَّل من toggleThemePicker إلى
  اللوحة (زر الثيم في الهيدر @ :166 لم يُمس) + هيكل اللوحة في
  style.css. 9 اختبارات (test_settings_panel.py): node ×6 (قيم حية/
  fail-closed مصدرًا/تهريب HTML/UNKNOWN/لا-أزرار-كتابة+ملاحظة config/
  راية project_root) + wiring ×3 (app.js قراءة-فقط، ترتيب التحميل،
  نقاء الوحدة صفر DOM). **البوابة**: check.sh ALL GREEN rc=0 —
  **1971P/34S** (1962+9؛ إخفاق عابر وحيد لـ test_no_save_churn
  [دقة mtime] زال في إعادة تشغيل منفردة وفي البوابة الكاملة الثانية —
  بيئي لا انحدار). **⇒ BATCH-P1 مُقفلة 🏁 6/6** — إنجازها: FI-05
  (فتح فوري بلا مشية شجرية) + تدوير المقاييس + حزمة تشخيص + Settings
  UI قراءة-فقط؛ التالي: تخطيط BATCH-P2 بقيد قرار (D-7).
- **2026-07-30 — Session 98 — تخطيط BATCH-P1 (D-9) — TSK-718..722 موثقة؛ TSK-718 جاهزة للتنفيذ**:
  استئناف بعد تصفير بيئة (طقس V3 §3.1: clone @ 78dac87، تطهير remote،
  الهوية، v1.0.0-rc.1 حاضرة). **بروتوكول المالك (4 خطوات)**: (1) استئناف ✅؛
  (2) تحقق إغلاق P0 ✅ — رأس PROGRESS 6/6 🏁 + كل artifacts الدفعة الخمسة على
  القرص + DECISION_LOG/DEVELOPMENT_TASKS/CHANGELOG متسقة ⇒ المتابعة مأذونة؛
  (3) **تخطيط P1 ✅ (قيد D-9)**: مراجعة الأولويات (FI-05 [MID] / تشخيص [SHORT]
  / تدوير سجلات [SHORT] / Settings UI [MID])؛ قراءات تصميمية:
  context/index.py (rebuild :82 / notify_write :124 / سياق ProjectHandle.index)
  + context/search.py (كاش mtime — لا حالة تحتاج حفظًا هناك) + مواقع البناء
  server.py:661/681/745 + نمط NF-19 (project_memory.py:356) + بوابة SafeReader
  (check.sh:24-27 ⇒ الوحدة الجديدة تسكن core/ لا context/)؛
  §BATCH-P1 أُلحق بـ DEVELOPMENT_TASKS: TSK-718 (وحدة snapshot ورقة) →
  TSK-719 (التوصيل: تحميل عند الفتح + حفظ بعد rebuild، مسار
  `<root>/.ai_runs/project_index.json` ضمن IGNORED_DIRS) ∥ TSK-720 (تدوير
  metrics/runs.jsonl — النمو غير المحدود @ server.py:2128) ∥ TSK-721
  (/api/diagnostics + support bundle مُطهَّر) ثم TSK-722 (Settings UI —
  placeholder يُفصَّل بعد 718-721)؛
  (4) **جاهزية TSK-718 متحققة**: Prerequisite FI-05 = TSK-501 ✅ Completed
  S22 (PROGRESS_ARCHIVE_1.md:868)؛ معايير قبول آلية مكتوبة؛ صفر deps معلقة
  ⇒ بدء التنفيذ (أمر البروتوكول: «إذا كانت جميع الشروط مستوفاة، ابدأ
  بتنفيذ المهمة الأولى»).
  **TSK-718 ✅ (نفس الجلسة)**: `core/index_snapshot.py` — صيغة v1
  (JSON: version/root/files-نسبية-بفواصل-posix)؛ `save_snapshot` ذرّي
  بنمط NF-19 الحرفي (tmp→fsync→os.replace) **لا يرفع أبدًا** (فشل⇒False
  + أثر NF-14 عبر _slog_swallowed)؛ `load_snapshot` متشكك — None عند أي
  انحراف (نسخة/جذر/فساد/شكل شاذ/مسارات مطلقة-هاربة-Windows drive)؛
  الوحدة في core/ عمدًا (بوابة SafeReader grep تمنع open() في context/).
  + `tests/unit/test_index_snapshot.py` — 19 اختبارًا. **البوابة**:
  check.sh ALL GREEN rc=0 — **1933P/34S** (1914+19 بالضبط؛ ملاحظة
  بيئية: فشل عابر واحد قبل تثبيت requirements-dev كان غياب tree-sitter
  — ليس انحدارًا). ملاحظة انقطاع: الكود نجا على origin عبر قيد
  Auto-Uploader e58f6c1؛ هذا الإغلاق التوثيقي أُعيد بعد تصفير البيئة.
  **TSK-719 ✅ (نفس الجلسة) ⇒ FI-05 مُقفل 🏁**: توصيل snapshot —
  (1) `ProjectIndex.__init__` يقبل `snapshot_path` اختياريًا؛ تحميل صالح
  ⇒ `_seed_from_snapshot()` يبذر `_files` + `_reindex()` **بلا مشية
  شجرية** (rebuild_count=0 مُثبَت اختباريًا)؛ فاشل/فاسد/جذر مغاير ⇒
  rebuild كالسابق؛ (2) `_save_snapshot_if_changed()` بعد كل rebuild —
  **فقط عند تغيّر القائمة** (اختبار no-churn: mtime لا يتحرك على sweep
  لشجرة ساكنة)؛ (3) التوصيل في server.py `_index_snapshot_path()` →
  `<root>/.ai_runs/project_index.json` (ضمن IGNORED_DIRS) موصول في
  `_server_handle_factory` + `_build_ctx`. عقد الطزاجة محفوظ: نافذة
  staleness واحدة ≤2s حتى أول sweep (اختبار التقارب بعد force=True)؛
  خطاف write-through يعمل فوق فهرس مبذور. + 10 اختبارات
  (`test_index_snapshot_wiring.py`) منها التكافؤ الذهبي fresh≡seeded
  والتوقيع القديم بلا snapshot_path يعمل حرفيًا كما كان.
  **البوابة**: check.sh ALL GREEN rc=0 — **1943P/34S** (1933+10).
  **TSK-720 ✅ (نفس الجلسة)**: تدوير metrics/runs.jsonl —
  `RunMetricsStore.rotate_if_oversized(max_bytes=5MB)` (core/run_metrics.py،
  تحت قفل الكتابة؛ os.replace → `runs.jsonl.1` جيل واحد؛ **لا يرفع
  أبدًا** — تصنيف NF-14 لمسار رصد اختياري) + استدعاء عند الإقلاع في
  server.py قبل subscribe (سطر banner ♻️ عند التدوير). القارئ يقرأ
  الحالي فقط — فقد تاريخ الجيل السابق من الملخص مقبول وموثَّق.
  + 7 اختبارات (`test_run_metrics_rotation.py`): فوق السقف يُدوَّر
  ويبدأ ملف نظيف؛ تحته لا يُمس؛ idempotent؛ غائب noop؛ الجيل الأسبق
  يُستبدل؛ السقف 5MB؛ الملخّص من الحالي فقط.
  **البوابة**: check.sh ALL GREEN rc=0 — **1950P/34S** (1943+7).
  **TSK-721 ✅ (نفس الجلسة)**: `/api/diagnostics` (routes/meta.py —
  نمط ADR-003): version + platform (system/release/python) + سلامة
  التبعيات الأربع (find_spec) + project_name (**الاسم فقط — لا مسار**)
  + provider مُطهَّر (مفاتيح get_info الوصفية الخمسة فقط — أي مفتاح
  غريب كـ api_key/base_url يُسقط) + metrics_summary (فشله لا يُفشل
  التشخيص). واجهة: زر Diagnostics في شريط الأنشطة →
  `downloadDiagnostics()` (fetch + Blob → webdev-diagnostics-<ts>.json).
  + 6 اختبارات (`test_diagnostics.py`) منها **فحص عدم-التسريب** (مزود
  leaky بمفاتيح sk-/ghp_ مزروعة ⇒ لا نمط سري ولا مسار مطلق في
  الحصيلة كاملة). توسيع سطح REST المجمَّد 31→32 موثَّق داخل
  test_rest_blueprints (توسيع عقد مقصود بقرار D-9 — نفس سابقة TSK-621).
  **البوابة**: check.sh ALL GREEN rc=0 — **1956P/34S** (1950+6).
- **2026-07-30 — Session 97 — TSK-715 ✅ + TSK-716 ✅ + TSK-717 ✅ ⇒ BATCH-P0 مُقفلة 🏁 6/6 — v1.0.0-rc.1**:
  استئنافان بعد تصفيري بيئة (S96→S97؛ كل عمل سابق نجا على origin —
  آلية D-8-ج تعمل كما صُممت). **TSK-716 ✅** (كان قد اكتمل كودًا قبل
  التصفير ونجا @ 21eb8a9): `core/version.py` = 1.0.0-rc.1 (rc حتى
  تحقق Windows بيد المالك) + `--version` + الإصدار في ترويسة الإقلاع
  + مفتاح version في /api/info (إضافة فقط) + سياسة الإصدارات في README
  + 3 اختبارات جديدة (SemVer/التطابق/السطح). **TSK-715 ✅**:
  `docs/USER_GUIDE.md` عربي Windows-أولًا — تثبيت خطوة-بخطوة + القاعدة
  الذهبية (لا 0.0.0.0 أبدًا — مصدرها threat model §5) + استكشاف أخطاء
  Windows (التدهوران الموثقان من TSK-714)؛ قبول المراجع الأربعة تحقق.
  **TSK-717 ✅**: LICENSE «All Rights Reserved © 2026 pijsal1-tech»
  (الافتراضي الآمن — الاستبدال برخصة مفتوحة قيد قرار مالك متى شاء) +
  قيد إغلاق الدفعة في CHANGELOG + **وسم v1.0.0-rc.1**.
  **البوابة النهائية**: check.sh ALL GREEN rc=0 — **1914P/34S**
  (أساس 1911 + 3 version) — هذا خط الأساس الجديد.
  - **حصيلة BATCH-P0**: فجوات الإنتاج السبع (Gap Report §3-ب) مسدودة؛
    المتبقي خارج أيدينا: تنفيذ المالك قائمة WINDOWS_COMPAT §6 على
    جهاز Windows حقيقي (شرط رفع -rc).
  - **الموضع** → تخطيط دفعة P1 (تفويض D-8-ج قائم): FI-05 فهرس بحث
    دائم + لوحة تشخيص/support bundle + تدوير سجلات + Settings UI.
- **2026-07-30 — Session 96 — TSK-713 ✅ + TSK-714 ✅ (P0-3 التغليف + P0-7 تدقيق Windows)**:
  استئناف بعد تصفير بيئة (طقس V3 §3.1؛ عمل S95 نجا كاملًا على origin
  @ bcd3224). **TSK-713 ✅**: `requirements.txt` تشغيلي جديد — 4 تبعيات
  صلبة مُسقَّفة (flask/flask-sock/requests/pyyaml، الأدلة file:line في
  رأس الملف) + الاختيارية الخمس معلّقة بأسبابها؛ README §التثبيت يشير
  إليه بدل قائمة pip اليدوية. **القبول تحقق**: venv نظيف +
  `pip install -r requirements.txt` + `import server` ينجح بلا dev deps.
  **TSK-714 ✅**: `docs/WINDOWS_COMPAT.md` — تدقيق ساكن على المحاور
  الخمسة (إشارات/مسارات/كتابة ذرّية/subprocess+ترميز/flask-sock):
  **AUDITED-STATIC PASS، صفر إصلاحات كود مطلوبة** (الكود عابر للمنصات
  أصلًا: shlex posix-switch @ command_runner.py:82، cmd.exe /c @ :140،
  تطبيع '\\' @ server.py:780، os.replace ذرّي في 6 مواقع)؛ تدهوران
  موثقان (إغلاق النافذة ≠ رشيق؛ cp1256 في مخرجات cmd) → لدليل
  المستخدم؛ قائمة فحص §6 للمالك على Windows حقيقي = شرط رفع -rc.
  **البوابة**: check.sh ALL GREEN — **1911P/34S** (82.71s) — خط الأساس ثابت.
  - **الموضع** → TSK-715 (دليل المستخدم) ∥ TSK-716 (الإصدار).
- **2026-07-30 — Session 95 — Evolution Gap Report + قرارات مالك D-8 + فتح BATCH-P0 + TSK-712 ✅**:
  جلسة كبرى: (1) **Evolution Gap Report** سُلِّم (10 أسئلة: الحالة/المكتمل/
  الفجوات/التناقضات CI-1..CI-6/الدين=صفر غير موثق/المخاطر/الجاهزية/مقارنة
  7 منافسين/مصفوفة 16 بُعدًا/خارطة P0→P3) — تحليل فقط، مبني على قراءة
  كاملة سابقة + بوابة حية 1911P/34S @ 9a3aed0. (2) **قرارات مالك D-8**
  (ثلاثة قيود في DECISION_LOG): (أ) CI-1 محسومة — حذف engineering_constitution/
  مؤجَّل لآخر المشروع → بند ختامي EOP-1؛ إلى حينها HISTORICAL-INERT.
  (ب) **Windows أولًا مبدئيًا، Linux مستقبلًا**. (ج) تفويض تنفيذ P0→P3
  حتى النهاية، استئناف موثق بين الجلسات — يشمل تفويض الحفظ على origin
  (سابقة فناء العمل مع تصفير البيئة موثقة S84/S86). (3) **تخطيط BATCH-P0**:
  TSK-712..717 معرّفة في DEVELOPMENT_TASKS §BATCH-P0 (مصالحة PROGRESS /
  requirements.txt / تدقيق Windows / دليل مستخدم / إصدار+version.py /
  LICENSE+tag v1.0.0-rc.1) — DAG: 712→713→714→(715∥716)→717.
  (4) **TSK-712 ✅ مُغلقة (هذه الجلسة)**: مصالحة الترويسة الحاكمة —
  last-updated/stage/current-phase/current-task (CI-2) + repository
  9a3aed0 (CI-4) + أقسام Current Stage/Position (CI-3)؛ سجل الجلسات
  لم يُمس (append-only). صفر تعديل كود ⇒ الانحدار غير مطلوب منطقيًا،
  وسيجري كاملًا عند أول TSK كودية (713+).
  - **الموضع** → TSK-713 (requirements.txt تشغيلي).
- **2026-07-30 — Session 94 — TSK-711 ✅ ⇒ BATCH-FI01 مكتملة 🏁 5/5 — FI-01 مُغلقة**:
  - **التغيير**: `tests/integration/test_rest_ws_state_parity.py` جديد —
    6 اختبارات: (1) بذر WS ≡ قراءة /api/chat-history حرفيًا؛ (2) /api/clear
    ينعكس على اتصال WS جديد بينما القائم يحتفظ بنسخته (عزل T-048)؛
    (3) البانر حي للاتصالات القائمة (banner_source)؛ (4) history_length
    في /api/info من المخزن؛ (5) **ماسح نكوص دائم**: صفر وصول خام
    `_srv.chat_history|_srv._binding_banner` في routes/*؛ (6) بذر
    `_build_session_context` من المخزن حصريًا (لا `list(chat_history)`
    ولا `lambda: _binding_banner`).
  - **ضابط سلبي**: زرع `_srv.chat_history = []` مؤقتًا في routes/rollback.py
    → الماسح فشل كما يجب → أُزيل الزرع → أخضر.
  - **القبول (إغلاق الدفعة)**: **check.sh كامل ALL GREEN rc=0 —
    1911 passed, 34 skipped** (أساس 1892 + 13 اختبار 707 + 6 اختبارات
    711)؛ 0 دورات (95/247)؛ mypy نظيف؛ CHANGELOG قيد [TSK-707..711/D-7].
  - **خط الأساس الجديد**: **1910P/34S** (مع deselect الـ flaky)؛
    check.sh = 1911P/34S.
  - **NF-03/g5 مستأصلة بنيويًّا**: مصدر حقيقة واحد (ConversationState)
    لكل حالة المحادثة المشتركة + ماسح دائم يمنع النكوص للأبد.
- **2026-07-30 — Session 93 — TSK-709 ✅ + TSK-710 ✅ (FI-01/3+4: ترحيل routes/* للمخزن) — النافذة الانتقالية مُغلقة**:
  - **TSK-709 (routes/sessions.py + meta.py)**: القراءة في
    api_chat_history من `snapshot()`؛ api_clear وapi_new_session عبر
    `clear()+clear_banner()`؛ استعادة api_load_session عبر
    `replace_all()`؛ meta.py `history_length` من `len(conversation_state)`
    — **نفس مفاتيح/قيم JSON حرفيًا**.
  - **TSK-710 (routes/project.py)**: فرع warn عبر `set_banner()` (نفس
    نص البانر حرفيًا، والاستجابة تقرأه من المخزن)؛ فرع fork عبر
    `clear()+clear_banner()` — دلالة R-303 كما هي.
  - **تحقق الاستئصال**: grep على `_srv.chat_history|_srv._binding_banner`
    في routes/ = **صفر مواقع** — كل حالة المحادثة المشتركة تمر الآن
    عبر ConversationState (REST كتابة/قراءة + بذر WS) ⇒ **النافذة
    الانتقالية الموثقة في S92 مُغلقة**؛ globals server.py:141/:145
    بقيتا اسمَي توافق غير مستهلكَين من routes (يحرسهما ماسح 711).
  - **ترحيل الاختبارات المقترنة** (نفس الدلالة، مصدر الحقيقة الجديد):
    test_session_binding.py (9 مواضع — المخزن يُحقن معزولًا لكل اختبار)
    وtest_rest_blueprints.py (اختبارا TestLiveInjection — عقد ADR-003 §2
    live-injection محفوظ عبر monkeypatch على conversation_state).
  - **القبول**: الحماية المستهدفة (binding + blueprints + session_context
    + conversation_state + switch_handlers + stale_refs) **70/70 PASS**؛
    mypy نظيف (83 ملفًا)؛ حارس الدورات 95/247/0.
  - **الانحدار**: **1904 passed, 34 skipped** — مطابق (صفر انحدار،
    صفر تغيير أشكال JSON).
  - **التالي**: TSK-711 (عقد التكافؤ + ماسح النكوص + إغلاق الدفعة).
- **2026-07-30 — Session 92 — TSK-708 ✅ مُغلقة (FI-01/2: توصيل server.py بالمخزن)**:
  - **التغيير** (4 مواضع في server.py حصريًا — على origin @ e3ed8b4):
    (1) استيراد ConversationState @ :86؛ (2) `conversation_state =
    ConversationState()` @ :152؛ (3) بذر WS في `_build_session_context`:
    `chat_history=conversation_state.snapshot()` @ :987 و
    `banner_source=lambda: conversation_state.binding_banner` @ :992
    (كانا يقرآن globals الخام)؛ (4) مسار الإقلاع في main():
    `conversation_state.replace_all(chat_history)` @ :1911 بعد استعادة
    الجلسة — الـ global يبقى اسم توافق انتقاليًّا.
  - **⚠️ نافذة انتقالية موثقة (تُغلق في 709/710)**: كتابات routes/*
    ما زالت على globals الخام بينما بذر WS صار من المخزن ⇒ بين 708
    و709/710 تحميلُ جلسة عبر REST لا ينعكس على اتصالات WS الجديدة.
    مقبولة عمدًا: (أ) الدفعة تكتمل قبل أي استخدام إنتاجي (localhost
    مفرد)؛ (ب) لا اختبار قائم يعتمد الاقتران REST→WS (عقده يُضاف في
    711 بعد الترحيل)؛ (ج) البديل (تاسك واحدة كبيرة) يخالف شرط المالك.
  - **القبول**: mypy بوابة كاملة نظيف (83 ملفًا)؛ اختبارات الحماية
    المستهدفة (test_session_context + test_session_binding +
    test_rest_blueprints + test_conversation_state) 60/60 PASS؛
    حارس الدورات: 95 وحدة/**247** حافة/0 دورات (+1 حافة =
    server→conversation_state). أُعيد التحقق من الثلاثة في بيئة ثانية
    بعد reset (S92b) — كود 708 نجا على origin، وهذا القيد أُعيد بناؤه
    (كان في أمر مقطوع لم يُلتزم — الدرس المعتاد: الالتزام ينجو فقط).
  - **الانحدار**: **1904 passed, 34 skipped** — مطابق تمامًا لخط أساس
    ما-بعد-707 (صفر انحدار، صفر تغيير أشكال).
  - **التالي**: TSK-709 + TSK-710 (ترحيل كتابات routes/*).
- **2026-07-30 — Session 91 — «ابدأ» صدرت ⇒ D-7 نافذة؛ TSK-707 ✅ مُغلقة (FI-01/1)**:
  - **الحوكمة**: قيد D-7 أُلحق بـ DECISION_LOG (قرار النطاق الملزم +
    الإجراء الدائم الجديد) قبل أول سطر كود — حسب تعليمات المالك.
  - **التغيير**: `core/conversation_state.py` جديد (95 سطرًا) —
    `ConversationState`: history + binding_banner خلف RLock واحد؛
    عمليات مسماة (append/replace_all/clear/snapshot/__len__/
    set_banner/clear_banner/binding_banner)؛ عزل بالنسخ في الاتجاهين
    (snapshot يعيد نسخة، replace_all يخزّن نسخة). استيراده الوحيد:
    providers.base (اتجاه قائم سلفًا — core/chat_dispatch.py:34).
    **صفر توصيل** — server.py وroutes/ لم يُمسّا (التوصيل TSK-708..710).
  - **القبول**: 13 اختبارًا جديدًا (tests/unit/test_conversation_state.py:
    العمليات 4 + عزل النسخ 3 + البانر 4 + أمان الخيوط 2 بكتابات
    متزامنة 4×50 بلا فقد) — 13/13 PASS؛ mypy نظيف؛ حارس الدورات:
    **95 وحدة/246 حافة/0 دورات** (الوحدة الجديدة دخلت الرسم نظيفة).
  - **الانحدار**: **1904 passed, 34 skipped** (أساس 1891 + 13 الجديدة
    بالضبط — صفر انحدار، مع deselect الـ flaky المعتاد).
  - **التالي**: TSK-708 (توصيل server.py) — جلسة قادمة.
- **2026-07-30 — Session 90 — BATCH-FI01 (D-7): تخطيط FI-01 📋 PLANNED — صفر تنفيذ**:
  - **قرار المالك**: البدء بـ FI-01 (توحيد حالة REST/WS) + **إجراء ثابت
    جديد ملزم لكل مهمة قادمة**: (1) خطة مكتوبة أولًا؛ (2) TSK موثقة قبل
    أي سطر كود؛ (3) تحديث PROGRESS قبل التنفيذ لا بعده؛ (4) تقدير مجهود؛
    (5) لا تنفيذ إلا بكلمة «ابدأ» صريحة. + شرط: **تاسكات صغيرة**.
  - **تشخيص الازدواج (بالدليل)**: REST يطفّر globals الوحدة —
    `chat_history` (server.py:141) و`_binding_banner` (:145) تُكتبان من
    routes/sessions.py:33/:34/:61/:78/:79 وroutes/project.py:93/:100/:102
    وتُقرآن من routes/sessions.py:26 وmeta.py:34؛ بينما WS يبذر
    `SessionContext` (T-048) نسخةً وقت الاتصال (server.py:977/:982) —
    مساران لنفس الحالة = NF-03/خطر g5.
  - **الخطة**: مخزن قانوني واحد `core/conversation_state.py`
    (ConversationState خلف RLock) تمر عبره كل كتابات REST وبذر WS؛
    عزل التبويبات (T-048) يبقى كما هو. 5 تاسكات صغيرة معرّفة في
    DEVELOPMENT_TASKS §BATCH-FI01: TSK-707 (المخزن، مستقل) →
    TSK-708 (توصيل server.py) → TSK-709 (routes/sessions+meta) ∥
    TSK-710 (routes/project — warn/fork) → TSK-711 (اختبار عقد تكافؤ
    REST↔WS + ماسح نكوص + إغلاق).
  - **الضمانات**: صفر تغيير في أشكال JSON/إطارات WS (مواصفة TSK-701
    مرجع)؛ خط الأساس 1891P/34S + check.sh ALL GREEN شرط إغلاق كل TSK؛
    حرّاس D-6 (دورات + ازدواج) فعّالون. Prerequisite TSK-302 ✅ (S14).
  - **تقدير المجهود**: 3–5 جلسات (TSK/جلسة؛ 709+710 قد تُدمجان في جلسة).
  - **الحالة**: PLANNED — بانتظار «ابدأ» من المالك. صفر ملفات كود مُست.
- **2026-07-30 — Sessions 88–89 — D-6 «دفعة التصفير» مكتملة ✅ 5/5 (أ–هـ) — TSK-706**:
  - **(د) G-10 محلولة**: المالك حذف `docs/engineering_constitution/` بنفسه
    (626fd1d — 13 ملفًا). شرط المالك (1) نُفِّذ قبل الاعتماد: فحص مرجعي
    شامل (*.py/*.js/*.md/*.yaml/*.sh) = **صفر إشارات كود/اختبارات**؛
    المتبقي 4 وثائق حوكمة append-only تاريخية فقط. انحدار ما-بعد-الحذف:
    1891P/34S نظيف. **(هـ) G-11 سقطت بالتبعية** (PRODUCT_VISION.md القديم
    كان داخل المجلد). قيد D-6 في DECISION_LOG.
  - **(ب) توصيل server.py**: 6 مواقع صامتة فعليًا (من 23 except Exception)
    وُصلت بـ `_slog_swallowed("server.py:<سطر>", _exc)` — مواقع except:
    315/1511/1531/1573/1949/2060؛ صفر صامت متبقٍ (الماسح). اختبار العقد
    `test_no_remaining_silent_sites` وُسِّع ليشمل server.py — 16/16 PASS.
    انحراف TSK-704 الموثق **مُغلق**.
  - **(أ) FI-08**: `scripts/check_import_cycles.py` (AST/stdlib، DFS ثلاثي
    الألوان) — **94 وحدة/245 حافة/0 دورات** + ضابط سلبي ✅؛ حارسان في
    check.sh قبل pytest (دورات الاستيراد NF-24 + ازدواج
    MAX_SMART_FILE_SIZE)؛ حارس ws.send قائم سلفًا (T-047).
  - **(ج) تدوير §6.4**: PROGRESS.md 2389→572 سطرًا؛ Sessions 24–83 +
    أرشيف v4.1 المضمَّن → `PROGRESS_ARCHIVE_1.md` (1832 سطرًا،
    append-only)؛ المقاطع الحاكمة لم تُمَس؛ سلامة التدوير مُتحقَّقة على
    origin (S89).
  - **القبول (S89)**: **check.sh كامل بالحرّاس الجدد أول تشغيل end-to-end:
    ALL GREEN rc=0** — «import graph acyclic: 94 modules, 245 edges,
    0 cycles» + «constants single-sourced» + **1892 passed, 34 skipped
    in 83.01s** (الـ flaky نجح في التشغيل النظيف). CHANGELOG قيد
    [TSK-706/D-6] مُلحَق.
  - **النتيجة**: الأرضية نظيفة 100% — لا مواقع صامتة، لا دورات استيراد،
    لا بقايا دستور قديم، سجل مُدوَّر، حرّاس دائمون. جاهزون لـ FI-01/FI-02
    (MID) بلا معوقات.
- **2026-07-30 — Sessions 87–88 — إغلاق TSK-705 ✅ (FI-03: الإيقاف الرشيق) — BATCH-SHORT مكتملة 🏁 5/5**:
  - **التغيير**: `graceful_shutdown(registry, timeout, poll_interval)` في
    core/execution.py (إلغاء تعاوني لكل الحية عبر list_active→cancel +
    انتظار محدود؛ صفر تذاكر = عودة فورية؛ لا إنهاء قسري — المتبقي يُعاد
    للمستدعي؛ المدخل Protocol بنيوي `_ShutdownRegistry` لتوافق
    RegistryBackend دون دورة استيراد) + ربط SIGTERM/SIGINT في server.py
    داخل `main()` حصريًا قبل app.run (إشارة أولى = رشيق 5ث + SystemExit(0)؛
    ثانية = خروج فوري) — **صفر تغيير في مسار الطلبات**.
  - **القبول**: 9 اختبارات جديدة (TestGracefulShutdown: حية→cancelled؛
    احترام المهلة ≥timeout مع متعنتة تبقى running بصدق؛ صفر = فورية <0.5s؛
    عودة مبكرة تعاونية؛ خليط؛ timeout=0؛ ValueError) → 31/31 في
    test_execution.py؛ mypy (بأعلام البوابة) نظيف؛ **دخاني وظيفي**: سيرفر
    حقيقي 127.0.0.1:5599 → HTTP 200 → kill -TERM → خروج ≤2ث برسالتي
    «⏹️ إيقاف رشيق» ثم «✅ إيقاف نظيف» (أعيد التحقق في بيئتين بعد reset).
  - **الانحدار**: **1891P/34S** (أساس 1882 + 9 = 1891 ✓، مع deselect
    الـ flaky) و**check.sh ALL GREEN rc=0** (1892P/34S — الـ flaky نجح).
    ملاحظة بيئية: في بيئة سابقة (S88 قبل reset #15) القراءة كانت
    1892P/33S — skip شرطي واحد تحول pass هناك (السبب البيئي الدقيق غير
    محسوم — ليس node، فهو حاضر في البيئتين)؛ التسوية سليمة في الحالتين.
  - **ملاحظة تشغيلية**: خلال S87 فشلت بوابة mypy أول مرة (تمرير
    RegistryBackend إلى توقيع ExecutionRegistry الصلب) — أُصلحت بالـ
    Protocol المحلي (commit fc6ebff عبر الرافع الآلي)؛ وreset منتصف
    الجلسة (#14–#15) أخّر الإغلاق — الكود والـ CHANGELOG كانا على
    origin، وهذا القيد أُكمل في S88.
  - **خط الأساس الجديد**: **1891P/34S** (قراءة بيئة الإغلاق النهائية).
  - **الدفعة**: TSK-701✅ 702✅ 703✅ 704✅ 705✅ — FI-11/12/10/06/03 كلها
    مقفلة. الموقع → **CLOSED-AWAITING-OWNER-DIRECTION (V3 §8)**.
- **2026-07-30 — Sessions 86–87 — إغلاق TSK-704 ✅ (FI-06: السجلات المهيكلة)**:
  - **التغيير**: `core/structured_log.py` (JsonFormatter + get_logger +
    configure + swallowed — لا يرفع أبدًا، صامت افتراضيًا، stdlib فقط) +
    توصيل **32 موقع ابتلاع صامت** عبر 12 ملفًا في core/+chain/ بسطر
    `_slog_swallowed("path:line", exc)` — **log-only، pass/continue
    باقية حرفيًا، صفر تغيير تدفق**.
  - **القبول**: 16/16 اختبارًا جديدًا (منها اختبار عقد آلي يمنع عودة
    المواقع الصامتة)؛ mypy نظيف؛ grep = صفر مواقع صامتة متبقية
    (الاستثناء المصرح: حارس swallowed)؛ الانحدار **1882P/34S** (أساس
    1866 + 16)؛ **check.sh ALL GREEN rc=0**.
  - **انحراف موثَّق**: مواقع server.py الـ23 خارج نطاق هذه الجلسة
    (يجيزه نص TSK-704) — توصيلها مهمة لاحقة اختيارية.
  - **خط أساس الدفعة الجديد**: 1882P/34S (مع deselect الـ flaky).
  - **التالي**: TSK-705 (FI-03: graceful_shutdown) — الأخيرة في الدفعة.
- **2026-07-30 — Session 86 — إغلاق TSK-703 ✅ (FI-10: DOMPurify) — أول كود تحت V3**:
  - **التغيير**: (1) `static/vendor/purify.min.js` = DOMPurify 3.2.6
    vendored (تحقق ترويسة الترخيص + تحميل node/jsdom ناجح)؛ (2) تحميله
    index.html:46 قبل app.js؛ (3) `renderMarkdown` يغلّف ناتج marked
    الوحيد بـ `DOMPurify.sanitize` — وغيابه ⇒ fallback التهريب النصي
    (fail-safe، لا HTML خام بأي مسار)؛ (4) cache-bust v=26.
  - **القبول**: اختبار DOM فعلي jsdom 6/6 PASS (script/onerror/
    javascript:/iframe/svg-onload تُنزع، markdown سليم يُحفظ)؛
    node --check OK؛ grep-guards موجودة؛ الانحدار **1866P/34S** ثابت.
  - **التالي**: TSK-704 (FI-06: structured logging).
- **2026-07-30 — Session 85 (تابع) — إغلاق TSK-702 ✅ (FI-12: دليل النشر ونموذج التهديد)**:
  - **الناتج**: `docs/deployment_threat_model.md` (وصفية، صفر كود):
    §1 عقد localhost (لا مصادقة/لا TLS بالتصميم) · §3 خريطة الدفاعات
    (احتواء مسارات/حجب أسرار/CommandPolicy fail-closed + ApprovalGate/
    Zip-Slip guard/escapeHtml) · §4 نموذج التهديد الثلاثي · §5 القاعدة:
    أي host غير loopback = كسر العقد و‎RCE بلا مصادقة عبر /api/run —
    الحد الأدنى قبل التعريض معدَّد وغير موجود = قرار مالك · §6 checklist
    (منها: حذف force_command_approval أأمن من false — الغياب=True).
  - **القبول**: 23/23 مرساة `file:line @ 7d39e9f` تحقق آلي PASS؛
    git diff نظيف (doc-only)؛ الانحدار = نفس شجرة 1866P/34S الخضراء.
  - **التالي**: TSK-703 (FI-10: DOMPurify).
- **2026-07-30 — Session 85 — إغلاق TSK-701 ✅ (FI-11: مواصفة إطارات WS)**:
  - **الناتج**: `docs/ws_frame_protocol.md` (وثيقة وصفية، صفر تغيير كود):
    §1 نقل (/ws، `_WSAdapter._send` الموقع الأوحد T-047) · §2 نوع مجهول =
    no-op صامت متماثل بالاتجاهين · §3 جدول C2S كامل (25 مقبض WS_HANDLERS +
    الحقول المقروءة فعليًا + مرسل الواجهة) · §3.1 عدم تماثل `stop` موثق
    ومحفوظ · §4 جداول S2C (49 مبثوث / 38 مستهلك / 11 متجاهل §4.7) ·
    §4.4 كشف: لا إطار `agent_approval_request` فعلي — الموافقة تصل
    `agent_step` بـ awaiting_approval · §5 إزالة لبس (أنواع الإجراءات/
    journal/صفوف diff ليست إطارات).
  - **القبول (تحقق مزدوج الاتجاه آلي)**: 25/25 + 16/16 + 42/42 + 44/44 —
    PASS صفر فجوات. الانحدار: **1866P/34S/1deselected** (الأساس ثابت).
    check.sh: الفشل الوحيد = flaky البيئي الموثق (1.018s>1.0s).
  - **ملاحظة بيئية**: انقطاعان (resets 9+10) بين كتابة المواصفة والإغلاق؛
    Auto-Uploader حفظ المواصفة على origin @ 5102111 — أُعيد بناء الإغلاق
    (CHANGELOG + PROGRESS) هذه الجلسة فقط.
  - **التالي**: TSK-702 (FI-12: docs/deployment_threat_model.md).
- **2026-07-30 — Session 84 — تبنّي V3 ✅ + فتح BATCH-SHORT (قرار مالك D-5)**:
  جلسة كبرى (أولى بعد الإقفال) تحت V3_RESUME_SESSION: اكتشاف حالة مضغوط
  §7.2 (جرد 20 ملفًا متسقًا؛ G-11 قائم؛ تدوير PROGRESS مستحق لاحقًا) ·
  تبنّي V3 نافذ (قيد V3-ADOPT + وسم V1 [SUPERSEDED by V3 — 2026-07-30]) ·
  قرار المالك D-5: «دفعة SHORT كاملة» = FI-03/06/10/11/12 · تخطيط
  TSK-701..705 في DEVELOPMENT_TASKS §BATCH-SHORT (قبول آلي + DAG خطي) ·
  خط أساس حي: **1866P/34S/0F** (deselect لـ search_perf البيئي — 1.036s
  على هذا العتاد، flaky موثَّق) · انقطاع بيئي قبل حفظ PROGRESS —
  أُعيد بناء هذا القيد في الدور التالي (قيود 5e41b04 نجت عبر origin) ·
  الموقع → **TSK-701** (مواصفة إطارات WS).

<!-- تدوير §6.4 دفعة ثانية (2026-08-02, S106هـ): قيود S100–S101 -->
- **2026-07-30 — Session 101 — بدء تنفيذ TSK-724 (FI-09) — جرد مسار العرض قبل التنفيذ (D-7)**:
  استئناف بعد تصفير بيئة (السادس؛ طقس §3.1: clone @ a44d16c، تطهير،
  الهوية — إقفال TSK-723 مؤكد على origin). **جرد التصميم (يسبق
  التنفيذ)**: مسار عرض الرسائل في app.js: `addChatMessage(role,
  content)` @ :909 (يبني العنصر + append + scroll — نقطة الفصل:
  استخراج `buildChatMessage` يُرجع العنصر بلا append)؛ **حلقتا الرسم
  الكامل** المستهدفتان بالنافذة: `loadChatHistory` @ :2202
  (`history.forEach(addChatMessage)`) و`loadSession` @ :2694 (نفس
  النمط)؛ البث (TSK-401) عبر `currentStreamMsg` append مباشر —
  **لا يُمس**؛ كروت التيرمنال (`handleRunCommandStep` @ :654) append
  مباشر — لا تُمس. **خطة الغراء الحافظة للسلوك**: النافذة تُفعَّل فقط
  عند تحميل تاريخ ≥ عتبة (VL_THRESHOLD)؛ بنية الحاوية في وضع النافذة:
  [spacer-top][رسائل النافذة][spacer-bottom][إلحاقات حية لاحقة] —
  الإلحاقات الحية (بث/كروت/رسائل جديدة) تقع بعد spacer-bottom فتبقى
  آخر القائمة بصريًا والتمرير التلقائي محفوظ؛ إعادة الرسم على scroll
  (rAF) تستبدل ما بين الـ spacers فقط؛ ارتفاعات مقدَّرة ثم تُقاس بعد
  الرسم وتُصحَّح. الوحدة النقية: `computeWindow(scrollTop, viewportH,
  itemHeights, overscan)` ⇒ {start, end, padTop, padBottom} بثبات
  المجموع. هذا القيد يسبق التنفيذ (D-7).
  **TSK-724 ✅ (نفس الجلسة)**: FI-09 نافذة عرض افتراضية: وحدة نقية
  `static/js/virtual_list.js` (`computeWindow` — end حصري، قصّ
  scrollTop/overscan للحدود، **الثابت الصارم** padTop + Σنافذة +
  padBottom = Σالكل لكل المدخلات؛ + `totalHeight`). الغراء (app.js):
  استخراج `buildChatMessage` نقية من `addChatMessage` (التي بقيت
  append+scroll حرفيًا — مسار الرسائل الحية والجلسات القصيرة)؛
  `renderChatHistory(history)` موحّدة حلّت محل حلقتي
  `forEach(addChatMessage)` في loadChatHistory/loadSession — تحت
  عتبة VL_THRESHOLD=150 المسارُ القديم حرفيًا، وفوقها وضع النافذة:
  [vl-spacer-top][نافذة][vl-spacer-bottom][إلحاقات حية] — البث
  (currentStreamMsg) وكروت التيرمنال appendChild كما هي بعد
  spacer-bottom فتبقى آخر القائمة والتمرير التلقائي محفوظ؛ `vlRender`
  يستبدل ما بين الـ spacers فقط (rAF throttle على scroll) + قياس
  الارتفاعات الفعلية بعد الرسم وتصحيح التقدير (VL_EST_HEIGHT=120)؛
  الفتح على آخر رسالة (scrollTop=scrollHeight ثم إعادة رسم). صفر
  endpoints. 13 اختبارًا (test_virtual_list.py): node ×7 (فارغة/
  قصيرة/طويلة 1000 عنصر/overscan مقصوص/ثابت المجموع على شبكة مدخلات
  تشمل سالبًا وفائضًا/تقاطع جزئي/totalHeight) + wiring ×6 (ترتيب
  التحميل/الاستهلاك/الحلقة الوحيدة داخل renderChatHistory/مسارا البث
  والتيرمنال بلا مساس/العتبة/نقاء الوحدة). **البوابة: 1996P/34S ALL
  GREEN rc=0** (من 1983). TSK-724 🏁. **التالي حسب DAG D-10: تفصيل
  TSK-725 (Workspace Trust — جرد نقاط الإنفاذ في server.py) ثم
  تنفيذها؛ يليها تفصيل TSK-726 (جرد دوال app.js)**.
- **2026-07-30 — Session 100 — تخطيط BATCH-P2 (قرار D-10) — TSK-723..727 موثقة؛ TSK-723 جاهزة**:
  استئناف بعد تصفير بيئة (طقس §3.1: clone @ b31f47c، تطهير، الهوية؛
  BATCH-P1 🏁 6/6 مؤكدة على origin). **تخطيط قبل تنفيذ (D-7)** — قراءات
  تصميمية: FUTURE_IMPROVEMENTS §FI-07 (شرط: لا تفكيك أثناء تعديل
  المُصيِّر ⇒ بعد FI-09) و§FI-09 (Prerequisite TSK-401 ✅)؛ app.js =
  3948 سطرًا/~150 دالة؛ نمط Quick Open Ctrl+K قائم (app.js:3821-3900)؛
  ApprovalGate من auto_execute (server.py:1972-1985). §BATCH-P2 أُلحق
  بـ DEVELOPMENT_TASKS: TSK-723 (Command Palette — صفر endpoints،
  سجل أفعال معرَّفة لا eval) → TSK-724 (FI-09 — computeWindow نقية +
  قيود حافظة: البث/النسخ/التمرير التلقائي لا تُمس) → TSK-726 (FI-07 —
  placeholder، جرد الدوال أولًا)؛ TSK-725 (Workspace Trust — fail-closed
  غير موثوق افتراضيًا، trust.json ذري في .ai_runs، يُفصَّل نهائيًا قبل
  التنفيذ)؛ TSK-727 (غلاف سطح مكتب — placeholder، موازنة تقنية مكتوبة +
  تحقق Windows بيد المالك D-8-ب). DAG: 723→724→726؛ 725 مستقلة؛ 727
  آخرًا. قيد D-10 في DECISION_LOG. **جاهزية الأولى (TSK-723)**: نمط
  قائم + سابقة وحدات نقية + معايير آلية + صفر تبعيات ⇒ التنفيذ مأذون
  (بروتوكول S98 + D-8-ج). هذا القيد يسبق التنفيذ (D-7).
  **TSK-723 ✅ (نفس الجلسة — عبر تصفيرَي بيئة إضافيين)**: Command
  Palette (Ctrl+Shift+P): وحدة نقية `static/js/command_palette.js`
  (UMD-lite نمط settings_panel): سجل ساكن COMMANDS ×15
  `{id,label(ar),hint,action}` حيث action = اسم دالة UI قائمة؛
  `filterCommands` (فارغ⇒نسخة الكل؛ وإلا احتواء label|id غير حساس
  لحالة الأحرف) + `renderListHTML` (تهريب HTML، مؤشر selected،
  data-cmd-id/data-index، حالة «لا أوامر مطابقة»). الغراء (app.js):
  جدول `CP_ACTIONS` = 15 مرجع دالة مباشر — التنفيذ lookup صريح
  `CP_ACTIONS[cmd.action]` (**لا eval ولا onclick مضمّن**)؛ تفويض
  نقر عبر `closest("[data-cmd-id]")`؛ لوحة مفاتيح ↑↓ (التفاف) /
  Enter / Esc؛ modal يعيد استخدام أنماط quick-open. index.html:
  الوحدة تُحمَّل قبل app.js + بنية command-palette-modal؛ style.css:
  غلاف الـ modal + .cp-item. **صفر endpoints — السطح المجمّد يبقى
  33** (test_rest_blueprints بلا تعديل). 12 اختبارًا
  (test_command_palette.py): node (ترشيح ×3/render حرفي+تحديد+kbd/
  تهريب/شكل السجل) + سجل-الأفعال (كل action دالة قائمة في app.js +
  مفتاح في CP_ACTIONS + لا eval) + wiring (ترتيب التحميل/الاستهلاك/
  الاختصار/التفويض) + نقاء الوحدة. **البوابة: 1983P/34S ALL GREEN
  rc=0** (من 1971). ملاحظات بيئة: تصفير ×2 أثناء التنفيذ —
  Auto-Uploader أنقذ الوحدة @ c862331 والغراء أُعيدت كتابته ثم دُفع
  فورًا @ 9b3c955 (درس: دفع الغراء قبل الاختبارات). TSK-723 🏁.
  **التالي: TSK-724 (FI-09 — computeWindow)** حسب DAG D-10.

<!-- تدوير §6.4 — دفعة ثالثة (2026-08-02, S106ح): Sessions 102–103 (المدخلات المؤرخة) -->

- **2026-07-30 — Session 102 — التفصيل النهائي لـ TSK-725 (Workspace Trust) — جرد الإنفاذ مكتمل (D-7)**:
  استئناف بعد تصفير بيئة (السابع؛ طقس §3.1: clone @ 81d28b1 — إقفال
  TSK-724 مؤكد على origin). جرد نقاط الإنفاذ:
  `_force_command_approval` @ server.py:190 (مستهلَكة في run.py:59/:96
  وserver.py:1837)؛ ApprovalGate يُبنى مرة عند الإقلاع @ :1983 من
  auto_execute ⇒ الإنفاذ ديناميكي وقت request() عبر معامل اختياري
  `interactive_override` (تغيير core صغير قابل للاختبار)؛ الذرية
  بسابقة NF-19 (os.replace)؛ .ai_runs ضمن IGNORED_DIRS. **التفصيل
  النهائي أُلحق بـ DEVELOPMENT_TASKS §TSK-725**: شرائح 725a (وحدة
  تخزين نقية fail-closed لا-ترمي) → 725b (إنفاذ + `/api/trust`
  GET/POST — توسيع رابع موثَّق 33→34) → 725c (شريط + شارة، glue
  فقط). هذا القيد يسبق التنفيذ (D-7).
  **TSK-725a ✅ (نفس الجلسة)**: `core/workspace_trust.py` — trust_path
  (`<root>/.ai_runs/trust.json`)، read_trust_record (isinstance صارم
  على bool)، is_trusted (**fail-closed: أي غياب/عطب/نوع خاطئ/استثناء
  ⇒ False بلا رفع**)، set_trust (سجل version/trusted/decided_at ISO
  UTC/decided_by؛ ذرية NF-19 tmp+fsync+os.replace + mkdir). 16
  اختبارًا (test_workspace_trust.py): fail-closed ×6 + دورة القرار ×4
  + ذرية/موقع/فشل-كتابة-بلا-رفع ×3 (+ معلمات). **البوابة: 2012P/34S
  ALL GREEN rc=0** (من 1996). 725a 🏁 — التالي 725b (الإنفاذ +
  /api/trust).
- **2026-07-30 — Session 103 — إقفال TSK-725b 🏁 — إنفاذ Workspace Trust + /api/trust (33→34)**:
  استئناف بعد تصفيرَي بيئة (الثامن والتاسع؛ طقس §3.1 ×2؛ Auto-Uploader
  أنقذ تغييرات النواة @ 3742325 وملف الاختبارات @ f8c17d2 — تحقّق كامل
  من المحتوى قبل المتابعة). التسليم: (1) `ApprovalGate` معلمة جديدة
  `interactive_override: Callable[[], bool] | None` — تقييم **ديناميكي
  عند الطلب** لا عند الإقلاع؛ استثناء المُستدعى ⇒ فرض تفاعلي
  (fail-closed)؛ deny يبقى deny؛ توافق خلفي كامل عند None.
  (2) `server._workspace_trusted()` (fm=None أو استثناء ⇒ False) +
  `_force_command_approval()` يعيد True عند عدم الثقة **قبل** قراءة
  config (يتجاوز false الصريح) + تمرير lambda للبوابة. (3) `/api/trust`
  GET (بلا مسارات — عقد التطهير) + POST {trusted: bool} (قرار مستخدم
  صريح، NF-19) في routes/meta.py = **التوسيع الرابع الموثَّق للسطح
  المجمّد 33→34** (test_rest_blueprints مُحدَّث). (4) ترحيل 3 اختبارات
  تاريخية بتثبيت `_workspace_trusted→True` (monkeypatch) + اختبار جديد
  يقنّن السلوك fail-closed (untrusted يتجاوز false الصريح). (5) حزمة
  إنفاذ جديدة test_workspace_trust_enforcement.py — 17 اختبارًا:
  override ×5 (فرض تفاعلي رغم auto+whitelist، ثقة تمرّر auto، توافق
  خلفي، استثناء fail-closed، deny ثابت) + force ×5 + endpoint ×7
  (GET fail-closed + لا-مسارات، دورة POST→GET + إبطال + ثبات على
  القرص، 400 ×4 معلمات، 503 بلا fm). إصلاح mypy (تعليق نوع dict).
  **البوابة: 2030P/34S ALL GREEN rc=0** (من 2012). 725b 🏁 — التالي
  725c (لافتة/شارة الثقة UI ثم إقفال TSK-725 الكامل + CHANGELOG).
- **2026-07-30 — Session 103 — إقفال TSK-725c 🏁 ⇒ TSK-725 كاملة 🏁 — واجهة Workspace Trust**:
  استئناف بعد تصفير بيئة (العاشر؛ طقس §3.1؛ Auto-Uploader أنقذ ترميز
  CSS الجزئي @ e00b993 — أُكمل التحقق ثم الإصلاح). التسليم:
  (1) وحدة نقية `static/js/trust_banner.js` (UMD-lite): parseTrust
  **fail-closed** (أي شكل غير متوقع ⇒ غير موثوق بلا قرار؛ trusted
  يستلزم decided؛ decided عبر decided_at/decided_by) + renderBanner
  (زرّا data-trust-action=trust|keep — تفويض، لا onclick) +
  renderBadge (موثوق/غير موثوق؛ غير-bool ⇒ غير موثوق حتى في العرض).
  (2) غراء app.js (fetch/DOM فقط — **لا منطق قرار في المتصفح**):
  applyTrustUI (اللافتة فقط عند «غير موثوق ولا قرار مسجَّل») +
  refreshTrustUI (GET /api/trust؛ فشل الشبكة ⇒ عرض fail-closed) +
  decideTrust (POST {trusted} حرفي) + تفويض نقر + نداء عند
  DOMContentLoaded وعند نجاح switch-project. (3) index.html: الوحدة
  قبل app.js + #trust-banner (hidden افتراضيًا) + #trust-badge بجوار
  project-crumb؛ style.css بتوكنز الثيم فقط (surface-1/green-soft/
  red-soft — أصلح lint الألوان بعد ضبطة أولى بألوان خام). (4) صفر
  endpoints جديدة — /api/trust من 725b؛ السطح يبقى 34. 13 اختبارًا
  (test_trust_banner.py): node fail-closed ×5 + نقاء ×2 + wiring ×6
  (بينها «لا منطق قرار» و«كل fetch يستهدف /api/trust حصرًا») +
  سيناريو يدوي موثَّق. **البوابة: 2043P/34S ALL GREEN rc=0** (من
  2030). **TSK-725 كاملة 🏁 (a+b+c)** — التالي حسب DAG D-10:
  تفصيل TSK-726 (FI-07: جرد ~150 دالة في app.js) ثم تنفيذه شرائحيًا.
- **2026-07-30 — Session 103 — تفصيل TSK-726 نهائيًا (D-7 — الجرد يسبق التنفيذ)**:
  الجرد: app.js = 4204 سطرًا / **162 دالة** / state مركزي + ثوابت
  مجالية / **24 دالة onclick عمومية** في index.html. **قرار معماري
  موثَّق (يعدّل FI-07)**: لا ES modules الآن (تكسر onclick الـ 24 ولا
  bundler) — بل **تقسيم-تسلسلي محافظ** إلى static/js/app/NN_*.js
  بنطاق عمومي مشترك = صفر تغيير سلوكي؛ المنطق النقي مستخرج فعلًا
  (14 وحدة UMD-lite). الشرائح: 726a (بنية + حارس test_app_split +
  نقل theme/quick-open/palette/غراء VL+Trust) → 726b (محرر/ملفات/
  تيرمنال) → 726c (جلسات/نماذج/مرفقات) → 726d (لوحات) → 726e (قلب
  الدردشة/البث/WS — الأخطر آخرًا؛ هدف app.js < 800 سطر). قبول: حارس
  الترتيب/العمومية/اللاازدواج بعد كل شريحة + wiring القائمة + سطح 34.
- **2026-07-30 — Session 103 — إقفال TSK-726a 🏁 — بنية التقسيم + الحارس + أول نقل**:
  استئناف بعد تصفير بيئة (الحادي عشر؛ §3.1؛ Auto-Uploader أنقذ ملفات
  التقسيم @ 6f422aa — تحقّق node --check قبل المتابعة؛ ربط index.html
  كان مفقودًا فأُكمل). التسليم: (1) استخراج حرفي لذيل app.js:
  Quick Open + Command Palette ⇒ `static/js/app/90_search_palette.js`
  (230 سطرًا) وغراء VL + Trust ⇒ `91_vl_trust.js` (166) — app.js
  4204→3815 سطرًا؛ diff = حذف+إضافة متطابقان. (2) index.html يحمّل
  المقاطع **بعد** app.js بالترتيب الرقمي (عقد eval-time — CP_ACTIONS
  تقيّم مراجع دوال app.js عند التحميل). (3) الحارس الدائم
  test_app_split.py — 7 اختبارات: ترتيب UMD→app→مقاطع + لا-يتيم +
  onclick الـ 24 معرَّفة في الحزمة + لا-ازدواج تعريف + لا-إعادة-state
  + node --check للحزمة كاملة. (4) ترحيل اختبارات wiring الثلاثة
  (palette/vl/trust) إلى قارئ الحزمة `_app_bundle()` — التأكيدات
  الجوهرية بلا تغيير (تغيّر مصدر القراءة فقط). **البوابة: 2050P/34S
  ALL GREEN rc=0** (من 2043). 726a 🏁 — التالي 726b (المحرر/الملفات/
  التيرمنال).
- **2026-07-30 — Session 103 — إقفال TSK-726b 🏁 — نقل مجال المحرر/الملفات/التيرمنال**:
  استئناف بعد تصفير بيئة (الثاني عشر؛ §3.1 — النقل ذاته كان على origin
  @ b7e7234؛ ترحيل اختبارات wiring الثلاثة الإضافية أُعيد محليًا).
  التسليم: (1) نقل حرفي لمقطع File Explorer→المحرر→التبويبات→diff
  panel→التيرمنال (loadFiles/openFile/saveFile/renderDiffPanel/
  initTerminal/runCommand/diagnoseTerminal — 684 سطرًا) ⇒
  `static/js/app/20_editor_files_terminal.js`؛ app.js 3815→3131.
  (2) الربط قبل 90/91 بالترتيب الرقمي بعد app.js (الاستدعاءات
  التمهيدية كلها داخل DOMContentLoaded — آمنة). (3) حارس
  test_app_split اجتاز بلا تعديل. (4) ترحيل test_code_highlight/
  test_diff_panel/test_icon_consumption إلى `_app_bundle()` —
  التأكيدات الجوهرية بلا تغيير. **البوابة: 2050P/34S ALL GREEN rc=0**
  (ثابتة — الترحيل لا يضيف اختبارات). 726b 🏁 — التالي 726c
  (الجلسات/النماذج/المرفقات/drag-drop).

