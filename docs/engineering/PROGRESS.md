# PROGRESS.md — editor_v4 Engineering Program (CORE-ONLY SCOPE v4.1)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.
> النطاق محكوم بـ SECTION 0.8: النظام الأساسي فقط — Provider Layer خارج النطاق كليًا.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-07-30 (Session 98 — تخطيط D-9 ✅ + TSK-718..721 ✅ (FI-05 🏁 + تدوير + تشخيص) — 1956P/34S ALL GREEN؛ المتبقي: TSK-722 تفصيل ثم تنفيذ) |
| stage | **V3-STAGE 4 OPEN — BATCH-P1 (D-9) قيد التنفيذ** — سوابق مُقفلة: BATCH-P0 🏁 6/6 (v1.0.0-rc.1)؛ سوابق مُقفلة: BATCH-FI01 🏁 5/5 + BATCH-SHORT 🏁 5/5 + D-6 ✅ 5/5 |
| current-phase | BATCH-P2 (دفعة D-10 تحت تفويض D-8-ج): Command Palette + FI-09 + Workspace Trust + FI-07 + غلاف سطح مكتب → TSK-723..727؛ DAG: 723→724→726؛ 725 مستقلة؛ 727 آخرًا؛ 725/726/727 تُفصَّل قبل تنفيذها (D-7)؛ سابقتها BATCH-P1 🏁 (D-9) |
| current-task | **TSK-730 مغلقة 🏁 (BATCH-P3/D-11)**: plugins توسيع (إظهار /api/diagnostics + إثراء PluginContext بـ run_id/metadata + توثيق) — التالي تفصيل TSK-731 (auto-update، مرهونة جزئيًا بتأشير المالك)؛ خط الأساس الجديد: **2120P/34S** |
| completion % (v4.1 archive) | Planning 100% (40/40) · Execution 100% (19/19 TSK) — مُقفل 🏁 |
| completion % (new lifecycle) | Stage 1: **12/12 ✅** · Stage 2: **3/3 ✅** · Stage 3: **26/26 TSK ✅ 🏁** (آخر المُغلقة S83: 605←D-2، 617←D-1، 622←D-4، 623←D-3) |
| repository | pijsal1-tech/Claude-Fable-5 (working branch: main @ 9a3aed0 عند فتح S95) |
| governing prompt | **MASTER ENGINEERING CONSTITUTION V3** (CONSTITUTION_V3.md — تبنّي مالك 2026-07-30، قيد V3-ADOPT؛ حلّ محل FINAL-GOVERNED الموسوم [SUPERSEDED]) |

### Completion formula
- Planning stage: completed IN-SCOPE phase-checkpoints ÷ total in-scope checkpoints (= 40).
- Execution stage: completed TSK ÷ total TSK (after P5 fills the task table).

---

## 🏛 NEW LIFECYCLE — MASTER ENGINEERING CONSTITUTION (FINAL-GOVERNED) — Session 24+

> البرنامج السابق (v4.1 CORE-ONLY) مُقفل 100% ويبقى أدناه كأرشيف مرجعي كامل.
> من هذه النقطة، الحوكمة للدستور الجديد: Stage 1 REVIEW → Stage 2 PLANNING → Stage 3 EXECUTION.
> وثيقة المراجعة المركزية الجديدة: `docs/engineering/MASTER_REVIEW.md`
> (تحوي CONTINUITY MAP يربط كل مرحلة R-x بمخرجات v4.1 الموجودة — لا إعادة عمل).
> الدستور الكامل محفوظ في `docs/engineering/prompet_28_7_final.md` (snapshot مرفوع — لا يُعدَّل).

### Current Stage
**V3 — BATCH-P0 مُقفلة 🏁 6/6 — v1.0.0-rc.1** — التالي: دفعة P1 (تفويض D-8-ج قائم؛ تخطيط TSK أولًا) — دفعة بوابة الإنتاج بقرار مالك D-8
(«ابدأ الآن من P0 حتى النهاية»)؛ التعريفات: DEVELOPMENT_TASKS §BATCH-P0

### Current Position
- Stage: V3 — BATCH-P2 (D-10) قيد التنفيذ؛ الموضع: TSK-723 (Command Palette) الأولى؛ سوابق مُقفلة: BATCH-P1 🏁 6/6 (FI-05 🏁 + تدوير + تشخيص + Settings UI) وBATCH-P0 🏁 (v1.0.0-rc.1)
- خط أساس الدفعة (حي @ 9a3aed0): 1911P/34S + check.sh ALL GREEN rc=0
- برنامج ما-بعد-P0 المفوَّض (D-8-ج): P1 (FI-05، لوحة تشخيص، تدوير سجلات، Settings UI) → P2 (FI-09، FI-07، Command Palette، Workspace Trust، غلاف سطح مكتب) → P3 (FI-04، CP-4، توسيع plugins، auto-update) — كل دفعة بتخطيط TSK مسبق وقيد قرار
- بند ختامي مُرحَّل: EOP-1 (حذف engineering_constitution/ — آخر المشروع، قرار D-8-أ)
- [أرشيف موضع BATCH-SHORT عند فتحها] خط أساسها (حي @ 4e87d6b): 1866P/34S/0F (+ search_perf البيئي 1.036s>1.0s على هذا العتاد — flaky موثَّق)
- [أرشيف الموضع السابق] Stage: EXECUTION (Stage 3 — **مُقفلة 🏁 26/26** — M6–M10 كلها مغلقة؛ IR-1 ✅ + IR-2 ✅)
- Phase/Task: **البرنامج مُقفل — لا مهمة متبقية** (S83 أغلقت الأربع
  الأخيرة بقرارات المالك: 605←D-2، 617←D-1، 622←D-4، 623←D-3)؛
  مسح الديون النهائي = صفر (تفصيله في قيد الجلسة S83 أدناه)
- Last completed step: **S83 — إقفال البرنامج**: TSK-622 ✅ (RRR §5
  re-vote — G1–G5 كلها PASS، الحكم GO ضمن عقد localhost) +
  TSK-623 ✅ (أرشفة improvements/ 892KB → tar.gz متتبع في
  test---results/، diff -r متطابق قبل الحذف) + IR-2 مسجلة +
  مسح ديون نظيف. خط الانحدار الختامي: **1901 = 0F/1867P/34S** +
  check.sh ALL GREEN exit 0.
- Previous milestone step: **TSK-626 ✅ DONE (Session 79 — M10: 3/4)** —
  قرار proposed_actions (RP-04): توثيق الفرع **test-only**
  (تعليقات فقط — صفر منطق): سطر عقد موحَّد فوق كتلة الموافقة في
  الـ runners الأربعة (agent:103/chain:90/delegate:99/direct:76)
  يثبت أن مواقع بناء RunRequest الإنتاجية الخمسة (server.py:1540 +
  chat_dispatch.py:245/280/343/449) لا تمرر proposed_actions وأن
  المستهلك الوحيد RunnerContractMixin — «لا يُحسب طبقة أمان
  فعلية؛ يُصان كمجال توسعة (worker.py T-110)» + تعليق مقابل في
  server.py:1533 + تعليق جامع في chat_dispatch.py:26. «التوصيل
  بمستهلك» تغيير سلوكي منتج = قرار مالك لم يُتخذ ذاتيًا. Gates:
  pyflakes دلتا صفر (stash-diff) · lint · mypy 81 · contracts+parity
  113 · goldens 32 · regression **1900 = 1F/1865P/34S** بلا تغيير.
  **RP-04 مغلق** (آخر بند RP المفتوح).
- Previous step: **TSK-624 ✅ DONE (Session 78 — M10: 2/4)** —
  retro-ADR لإعادة تصميم v25 (TD-04): مقطع **ADR-005** مُلحق بـ
  ARCHITECTURE_DECISIONS.md (بنية بيتية؛ موسوم «retroactive
  record»؛ الدوافع الأصلية UNKNOWN) — النطاق بالأدلة من git
  (0d74dad/2ed794f/8235147/454f7ac — 1877 insertions في static/)،
  الأثر (كسر TF-01/TF-03/TF-04 + تعمية البوابة TF-05)، كيف أُصلحت
  (TF-01/03 → TSK-604 ✅ زرا وكيلان + سطر الترخيص؛ TF-04 معلّق
  D-2 موثَّقًا كحدّ صريح) + قيد استرجاعي موسوم retro في
  DECISION_LOG.md. توثيق صرف — صفر لمس كود؛ regression بلا تغيير
  **1900 = 1F/1865P/34S** (theme_tokens/TF-04/D-2 حصرًا).
  **TD-04 مغلق** (آخر بند R10.3 المفتوح).
- Previous step: **TSK-625 ✅ DONE (Session 77 — M10: 1/4)** —
  صلابة _parse_args_body (ASF-06): تفكيك متسامح — سطر يبدأ بمفتاح
  شرعي يفتح وسيطًا؛ أي سطر آخر يُطوى في قيمة المفتاح السابق (بدل
  البتر الصامت/الوسيط الزائف المثبتين بالتشغيل في §TSK-625)؛
  المفاتيح الشرعية تُشتق حيًّا من تواقيع _handlers
  (_known_arg_keys — inspect + cache)؛ parse_tool_calls وexecute
  بلا لمس. 18 اختبارًا (golden 6 + متعدد الأسطر 5 + عدائية 5 +
  اشتقاق حي 1 + e2e 2). regression **1900 = 1F/1865P/34S**
  (theme_tokens/TF-04/D-2 حصرًا؛ 1882+18=1900 ✓) — **خط انحدار
  جديد: 1900**.
- Previous step: **TSK-621 ✅ DONE (Session 76 — M9: 6/8)** —
  Permissions UI قراءة (CP-5/UXF-04): endpoint قراءة جديد
  `GET /api/permissions` في blueprint meta القائم (routes/meta.py —
  ADR-003؛ **server.py صفر تعديل**) يعيد السياسة الفعالة الحية:
  command_allowlist عبر command_policy_from على config الحي +
  SAFE/APPROVAL tools + SAFE/DANGEROUS commands +
  force_command_approval + حالة ApprovalGate (null قبل الإقلاع —
  لا اختراع). وحدة نقية `static/js/permissions_panel.js`
  (renderPanelHTML — 4 أقسام، تهريب HTML، صفر أدوات كتابة) +
  لوحة #permissions-panel + زر Activity Bar 🔒 + غراء fetch/render
  في app.js. سطح REST المجمّد 30→31 (توسيع عقد موثَّق — القبول
  ينص على «endpoint قراءة»). 12 اختبارًا (endpoint قيم حية +
  405 للكتابة + لا تحوّل حالة + node 5 + wiring 2 + سيناريو يدوي
  موثَّق). regression **1882 = 1F/1847P/34S** (theme_tokens/TF-04/D-2
  حصرًا؛ 1870+12=1882 ✓) — **خط انحدار جديد: 1882**.
- Previous step: **TSK-620 ✅ DONE (Session 75 — M9: 5/8)** —
  سرد الجلسة (CP-8/UXF-05): وحدة نقية جديدة
  `static/js/session_narrative.js` (UMD-lite) — timeline من أطر WS
  الحية بالتقاط استهلاك-فقط (نفس عقد StatusChip.noteFrame)؛
  محطات: طلب (noteRequest من sendMessage) / خطة / موافقات
  (طلب+حكم) / تنفيذ (دمج المتتالية بعدّاد) / نتائج / استعادة؛
  سقف 200 أقدم-يُطرد؛ القسم يُحقن فوق قائمة RunHistory داخل
  اللوحة عند الفتح — القائمة/الاستعادة بلا لمس؛ **server.py بلا
  لمس**. 10 اختبارات node (test_session_narrative.py): القبول
  حرفيًا (run معتمد → 5 محطات بترتيبها) + تصنيف/دمج/سقف/تهريب
  + wiring + سيناريو يدوي موثَّق. إصلاح أثناء البوابات: توكن
  var(--border) غير معرّف (كشفه TestTokenParity) → var(--surface-0).
  Gates: contracts+parity 113 · goldens+ws_router 32 · mypy 81
  Success · lint نظيف · regression junitxml **1870 = 1F/1835P/34S**
  (theme_tokens/TF-04/D-2 حصرًا؛ 1860+10=1870 ✓) — **خط انحدار
  جديد: 1870**. Commits: 3e0abd8 (أدلة قبل الكود) + التنفيذ غير
  الملتزم — كلاهما التقطه دمج المستخدم 4777a0a بعد reset منتصف
  الجلسة · 1d82491 (إصلاح التوكن) · ba7f331 (Close-out+جدول+
  CHANGELOG).
  وقبلها: **TSK-619 ✅ DONE (Session 74 — M9: 4/8)** —
  بطاقة الخطة التفاعلية (CP-1/UXF-01): وحدة نقية جديدة
  `static/js/plan_card.js` (UMD-lite — أعلام تفعيل لكل خطوة، كلها
  مفعّلة افتراضيًا؛ enabledActions = subset بترتيبه الأصلي)؛
  showPlanCard يرسم checkbox لكل خطوة ويربطها بالحالة النقية؛
  executePlan يرسل المفعّل فقط (منع الإرسال + toast عند صفر مفعّل)؛
  cancelPlan يصفّر الحالة؛ index.html يحمّل الوحدة قبل app.js؛
  style.css tokens فقط. **server.py بلا لمس** (subset شفاف لـ
  _apply_batch golden-locked). 10 اختبارات node جديدة
  (test_plan_card.py): القبول حرفيًا (تعطيل خطوة → payload بدونها) +
  بوابة حفظ السلوك حرفيًا (كل-الخطوات-مفعلة = مطابق بايتًا) + wiring
  + سيناريو يدوي موثَّق في docstring. Gates: contracts+parity 113 ·
  goldens+ws_router 32 · mypy 81 Success · lint نظيف · regression
  junitxml **1860 = 2F/1824P/34S** (theme_tokens/TF-04/D-2 المعروف +
  search_perf flaky يمر معزولًا ×2؛ 1850+10=1860 ✓) — **خط انحدار
  جديد: 1860**. Commits: 33fe114 (أدلة قبل الكود — دمجه المستخدم
  5f59764) · 309ecdb (التنفيذ+الاختبارات) · 686ac90 (Close-out+
  جدول+CHANGELOG).
  وقبلها: **TSK-618 ✅ DONE (Session 73 — M9: 3/8)** —
  تضييق except الابتلاعي في path_policy (ASF-07): أدلة S73
  كشفت **NF-28** (C4/S2) — `raise PermissionError` كان داخل نفس
  الـ try الذي يبتلع Exception ⇒ فحص symlink **ميت بالكامل**
  منذ كتابته (تجربة حية: symlink داخلي ومجلد symlink يمران؛
  الخطان الصلبان — الاحتواء والأسرار على المحلول — يصمدان)
  [SUPERSEDES جزئيًا توصيف ASF-07]. الإصلاح: فصل القياس عن
  القرار — is_symlink داخل try ضيق يلتقط OSError وحده مع
  `_LOG.warning` موسوم؛ الرفض خارجه ⇒ حي الآن. 9 اختبارات
  جديدة (أول تغطية مباشرة لـ path_policy) منها خطأ FS محقون →
  تحذير caplog + الاحتواء يعمل (القبول حرفيًا) + حارس بنيوي
  ضد عودة النمط. Gates: contracts+parity 113 · goldens+ws_router
  32 · mypy 81 Success · lint نظيف · regression junitxml
  **1850 = 1F/1815P/34S** (theme_tokens/TF-04 حصرًا؛ 1841+9=1850 ✓؛
  test_search_perf فشل مرة ثم ثبت flaky — يمر معزولًا ×2 وفي
  الإعادة الكاملة) — **خط انحدار جديد: 1850**. Commits: 94c92ce
  (أدلة+NF-28 قبل الكود) · 7ebc5b9 (التنفيذ+الاختبارات — دمج
  المستخدم b0f4da5) · 4893403 (CHANGELOG+جدول الحالة).
  وقبلها: **TSK-616 ✅ DONE (Session 72 — M9: 2/8)** —
  إظهار سقف snapshot (ASF-03): اقتطاع مسح الـ checkpoint
  (`_CKPT_MAX_FILES`/`_CKPT_MAX_FILE_BYTES`) لم يعد صامتًا —
  العلم يُشتق حيث تحدث الحقيقة (`_workspace_signatures` →
  tuple مع علم اقتطاع) ويصعد: سطر ⚠️ صريح في تقرير الأداة
  («التراجع عن آثار هذا الأمر سيكون جزئيًا») + حقل
  `partial_rollback` في إطار agent_step/done + إظهار في الواجهة
  (toast تحذيري + نص دائم على كارت التيرمنال) — السقفان
  نفساهما لم يتغيرا («إظهار لا رفع سقف» MASTER_REVIEW:722).
  10 اختبارات جديدة (test_snapshot_cap_visibility.py) بما فيها
  E2E عبر AgentLoop حقيقي + سلبيان. Gates: contracts+parity 113 ·
  goldens+ws_router 32 · mypy بوابة 81 ملفًا Success · lint نظيف ·
  regression junitxml **1841 = 1F/1806P/34S** (theme_tokens/TF-04
  حصرًا؛ 1831+10=1841 ✓) — **خط انحدار جديد: 1841**. Commits:
  2911a90 (أدلة+pre-checks قبل الكود — دمج 51a0a1b) · 39bbc64
  (التنفيذ+الاختبارات — دمج 088c2d3) · cdf06c8 (CHANGELOG).
  وقبلها: **TSK-615 ✅ DONE (Session 71 — أولى M9)** —
  ApprovalGate طلبات متزامنة (ASF-05): الخانة المفردة
  (`_pending_id` + Event مشترك) استُبدلت بخريطة
  `request_id → _PendingEntry` (Event مستقل لكل طلب؛ الخيط
  المالك يزيل مدخله في finally). أدلة S71 كشفت **NF-27**
  (C5/S2): التجربة الحية أثبتت أن الكسر كان fail-OPEN لا
  fail-closed كما وصف ASF-05 — اعتماد طلب كان يعتمد المتداخل
  معه زورًا (Event مشترك + نتيجة مشتركة). الإصلاح: حلّ مستقل
  لكل طلب + مهلة لكل طلب (fail-closed يبقى) + تدقيق ينسب كل
  قرار لطلبه. التواقيع العامة بلا تغيير (صفر تعديل في
  المستهلكين)؛ +قراءة `pending_request_ids()`. 9 اختبارات
  تزامن جديدة + الـ19 القائمة تمر بلا تعديل. Gates: contracts+
  parity 113 · goldens+ws_router 32 · mypy بوابة 81 ملفًا Success ·
  lint نظيف · regression junitxml **1831 = 1F/1796P/34S**
  (theme_tokens/TF-04 حصرًا؛ 1822+9=1831 ✓). Commits: a55267f
  (أدلة+pre-checks+NF-27 قبل الكود) · f37be66 (التنفيذ+الاختبارات —
  دمج خارجي 84b58d9) · 63e51ec (CHANGELOG).
  وقبلها: **TSK-614 ✅ DONE (Sessions 68–70) ⇒ M8 مكتملة 4/4 ⇒ IR-1 مسجلة في DECISION_LOG** —
  QG-04 (§R8): توسيع بوابة mypy — **ADR-004** (قبل الكود):
  `--check-untyped-defs` (الأدلة أثبتت أن الافتراضي لا يفحص
  أجسام الدوال غير المُعنونة — النداء المدسوس يفلت والقبول
  يسقط) + استبعاد `providers/openai_shelby.py` وحده (خطأ قائم
  §0.8) + ضم routes/ + server.py ⇒ **Success — 81 ملفًا،
  exit=0**؛ تصفير 129 خطأ لا-سلوكيًا (`_srv: Any` ×7؛ 16
  sentinel ignore؛ RUNNERS/frame/cfg/provider تعنوينات)؛ الفحص
  الموسع كشف علّتين حقيقيتين أُصلحتا: **NF-25** (انحدار 612:
  provider_pool/approval_gate غير معرّفتين في chat_dispatch ⇒
  NameError بمسار agent — حُقنا في deps) و**NF-26** (منذ
  0d74dad: تقطيع dict بـ attach المجلد ⇒ تدهور صامت — أُصلح
  بـ items())؛ إكمال Protocol RegistryBackend بـ purge_terminal؛
  الاختبار السلبي الموثق نُفّذ بطريقتين (دائم في
  test_mypy_gate_614.py + زرع فعلي في routes/meta.py → exit=1
  ثم استعيد)؛ +10 اختبارات؛ gates: check.sh أخضر حتى color
  lint (TF-04/D-2 حصرًا) · contracts+parity 113 · goldens 32 ·
  متأثرة 104 · regression junitxml **1822 = 1F/1787P/34S**
  (theme_tokens حصرًا؛ 1812+10=1822 ✓)؛ QF-02 مغلقة. **IR-1**:
  السؤال المحوري — التفكيك كافٍ، لا worker/process (المنتج
  local-first أحادي المستخدم؛ server.py 3045→2132 = −30%؛
  الخيوط محكومة بـ ExecutionRegistry)؛ CP-4 يبقى مؤجلًا؛ CP-6
  محسوم بـ RP-01 ✅ (TSK-601) — مسجلة في DECISION_LOG.
  وقبلها: **TSK-613 ✅ DONE (Sessions 64–67)** —
  QG-03 (§R8): تجميع REST blueprints — **ADR-003** (حقن كائن وحدة
  server عبر `register(app, srv)`؛ قراءة `_srv.fm`… حيّة وقت
  النداء — يحيّد خطر تجميد ازدواجية g5؛ ADR + DECISION_LOG
  **قبل الكود**)؛ تحقق مسبق من شرط «استقرار g5»: مستقر
  بصيغة «مقبول موثّق» (NF-03؛ التوحيد مؤجل FI-01) — لا حاجب.
  حزمة `routes/` (8 ملفات، 633 سطرًا): 7 blueprints موضوعية
  (files 8 · backups 2 · run 3 · sessions 6 · meta 3 · rollback 2 ·
  project 1) — **25 دالة بأجسام حرفية** (نقل آلي tokenize —
  السلاسل النصية مصونة؛ تحقق عكسي سطرًا-بسطر 25/25 = 0
  فروق)؛ إعادة ربط globals → تعيين سمة (تكافؤ حرفي)؛ تبقى
  index + api_models + api_switch_model (§0.8) والمساعدات. تكافؤ:
  smoke 28/28 متطابق قبل/بعد + url_map **30 قاعدة bit-identical**
  (القبول ✓)؛ **server.py 2596→2118 (−478؛ M8 إجمالي −927)**؛
  +21 اختبارًا (test_rest_blueprints — تجميد القواعد + الحقن الحي
  + لا دورة)؛ 4 فحوص بنيوية حُدّثت لنفس الضمانات في routes/
  (force_approval/search_perf/rollback_ui/capacity_model — الأخير
  تقوية)؛ gates: mypy نظيف **70 ملفًا** (يشمل routes/) · lint
  clean · contracts+parity 113 · goldens 32 · عدة التأثير 89/89؛
  regression junitxml **1812 = 1F/1777P/34S** (theme_tokens/TF-04
  حصرًا؛ 1791+21=1812 ✓)؛ انحرافات موثّقة (25≠«27»؛ لا memory
  REST — WS فقط).
  وقبلها: **TSK-612 ✅ DONE (Sessions 61–63)** —
  QG-02 (§R8): استخراج مسار الإرسال — **ADR-002** (حقن التبعيات
  عبر deps=SimpleNamespace يُبنى في الغلاف **عند كل نداء** — late
  binding يحافظ على monkeypatching الاختبارات على فضاء server
  ويقرأ globals المتغيّرة وقت النداء؛ ADR + قيد DECISION_LOG
  **قبل الكود** وفق الدستور :1038)؛ `core/chat_dispatch.py` جديدة
  (513 سطرًا) — جسم `_dispatch_chat_message` **حرفيًا** (كان
  server.py:1549..2034 = 486 سطرًا؛ النص قال ~477 — انحراف موثّق)
  كدالة `dispatch_chat_message(deps, ctx, sctx, ...)`؛ 14 رمز
  server عبر deps؛ الاستيرادات النقية مباشرة في الوحدة؛ لا
  استيراد server (لا دورة)؛ الغلاف يحتفظ بالاسم/التوقيع ويرسل
  scan_start (TSK-403) ثم يبني deps ويفوّض؛ **server.py 3045 →
  2596 (−449)**؛ خطر الإعادة الآلية تحقق (تلف سلسلة نصية واحدة
  — أُصلح وثبت بمقارنة آلية سطرًا-بسطر مقابل الأصل: 0 فروق
  متبقية)؛ 4 فحوص بنيوية حُدّثت بنفس الضمانات في الموقع الجديد
  (prompt_fencing/context_engine/config_consolidation/run_slot)؛
  gates: mypy نظيف (62 ملفًا core+chain+context+sessions؛ خطأ
  providers قائم مسبقًا خارج النطاق §0.8 — أُثبت عبر git diff)
  · goldens 32 · contracts+parity 113 · مثبّتات الإرسال 76 · lint
  clean؛ regression عبر junitxml **1791 = 1F/1756P/34S**
  (theme_tokens/TF-04 حصرًا)؛ الوحدة تدخل بوابة mypy تلقائيًا
  (check.sh:12 يغطي core/).
  وقبلها: **TSK-611 ✅ DONE (Sessions 58–60)** —
  QG-01 (§R8): استخراج راوتر WS — **ADR-001** (أول ADR؛
  ARCHITECTURE_DECISIONS.md + DECISION_LOG.md أُنشئا **قبل الكود**
  وفق الدستور :1038)؛ `core/ws_router.py` جديدة (dispatch نقية —
  نوع مجهول no-op صامت حرفيًا)؛ الفروع الـ23 (506 أسطر) استُخرجت
  آليًا إلى 23 دالة `_ws_<type>` بأجسام حرفية + جدول WS_HANDLERS
  (25 مفتاحًا؛ المركّبات → مقبض مشترك)؛ **الكتلة 506 → 13 سطرًا
  (−493 ≥ 300 ✓)**؛ lint_handler_state وُسّع لبادئة `_ws_`؛
  فحصان بنيويان حُدّثا (scan_start/rollback_ui) بنفس الضمانات؛
  +10 اختبارات (test_ws_router.py — تجميد الأنواع الـ25 + pong
  bit-identical)؛ gates: goldens 22 · contracts+parity 113 · lint
  clean؛ regression **1F/1756P/34S** (theme_tokens/TF-04 حصرًا؛
  1746+10=1756 ✓)؛ انحرافات المواصفة موثقة (506≠469؛ 23≠16؛
  «goldens routing» = توجيه سلسلة لا WS — فُسِّر وأُغلقت الفجوة).
  وقبلها: **TSK-610 ✅ DONE (Sessions 55–57)** —
  Metrics aggregation (PM-03 §R6): `core/run_metrics.py` جديدة —
  `RunMetricsStore` (JSONL ملحق-فقط نمط ProjectMemoryStore؛ قارئ
  يتخطى الأسطر الممزّقة؛ p50/p95 nearest-rank بلا تبعيات؛ ملخّص
  كليًا ولكل mode) + `RunMetricsRecorder` (مشترك bus الرصد يقرن
  RunStarted↔RunFinished بـ run_id، سقف pending 256 أقدم-يُطرد،
  فشل الكتابة يُبتلع مع log/NF-14)؛ ربط server.py: global +
  REST قراءة `/api/metrics/runs` (503 قبل التهيئة) + اشتراك في
  main() — الملف `metrics/runs.jsonl` (قرار موثّق: ملف تطبيقي
  واحد + حقل project_id)؛ انحراف موثّق: context_chars/project_id
  بلا ناشر اليوم — يُسجّلان None ويُلتقطان تلقائيًا متى نُشرا؛
  +17 اختبارًا (test_run_metrics.py — معيار القبول الحرفي
  «3 runs → 3 أسطر صالحة» + e2e بـ DirectRunner حقيقي)؛ gates:
  contracts+parity 113 · goldens+609 50 · lint clean · Performance
  append 0.039ms/سجل؛ regression **1F/1746P/34S** (theme_tokens/TF-04
  حصرًا — 1729+17=1746 ✓). **🏁 M7 Observability مُقفلة (5/5)**.
  وقبلها: **TSK-609 ✅ DONE (Sessions 49–54)** —
  Instrumentation (PM-01/02/04 §R6): `duration_ms` في حدث
  `run_finished` للمسارات direct/agent/delegate (نفس نمط chain —
  تغطية القياس 1/4 → 4/4)؛ توقيت collect لكل مصدر سياق في
  `ContextEngine.gather` محمولًا على ContextBundle ومكشوفًا في
  `MessageContext.source_timings_ms` (حقل افتراضي + compare=False —
  انحراف موثّق: اختبارات parity تقارن بالمساواة والتوقيت غير
  حتمي)؛ `duration_ms` + `token_estimate` (CharsPerTokenEstimator
  المركزي) على إطاري plan/done للمسارين direct/agent — حقول
  إضافية فقط؛ +11 اختبارًا (test_instrumentation_609.py)؛ gates:
  contracts+parity+goldens 153/153 · lint clean · Performance
  ميكروثوانٍ/رسالة؛ regression **1F/1729P/34S** (theme_tokens/TF-04
  حصرًا — 1718+11=1729 ✓).
  وقبلها: **TSK-608 ✅ DONE (Sessions 47–48)** — تفعيل
  `ExecutionRegistry.reap_stale` إنتاجيًا (RF-02 §R5): درزة
  `resolve_stale_ttl` (غائب = 900s، null = تعطيل، غير صالح =
  فشل إقلاع صاخب) + تمرير TTL عبر backends_from_config؛ نداء
  reap_stale قبل purge_terminal في _begin_run_ticket (نمط TSK-303)؛
  وسد مخاطرة الحصد الزائف: نبض حياة في _RunnerWSAdapter.emit
  (كل المسارات) + _apply_batch (لكل action) + غلاف resume؛
  +17 اختبارًا (test_reap_stale_wiring.py)؛ عدة التأثير 108/108؛
  Performance: 0.0066ms/تسجيل؛ regression (S47+S48):
  **1F/1718P/34S** — المتبقي الوحيد theme_tokens (TF-04/D-2).
  وقبلها: **TSK-607 ✅ DONE (Sessions 45–46)** — ضم آخر
  جيب برومبت خارج الميزانية: معالج delegate_message كان يمرر
  أول 10 ملفات كاملة بلا سقف للبريف — الآن دالة نقية
  `_budget_delegate_files` (BudgetItem/high تحت
  ContextBudget.from_config؛ كامل-أو-إسقاط، الأكبر أولًا؛ وسم
  اقتطاع ظاهر + log — لا تدهور صامت)؛ +6 اختبارات
  (TestDelegateFilesBudget) — test_budget_wiring 30/30؛ Performance
  0.03ms/نداء؛ regression (S45): **1F/1701P/34S** — المتبقي الوحيد
  theme_tokens (TF-04/D-2).
  وقبلها: **TSK-606 ✅ DONE (Sessions 43–44)** — تخييط
  نداء `_apply_batch` (خيط `runner-apply-batch`) وبلوك direct
  runner (خيط `runner-direct-{run_id}`) — cancel_run من نفس
  الاتصال صار فعّالًا (كان مستحيلًا بنيويًا: التنفيذ المتزامن كان
  يحتجز خيط حلقة استقبال WS). `_apply_batch` نفسها لم تُمس؛
  goldens QA-T08 مطابقة (ملف golden بلا تغيير، الـ harness فقط
  يَـjoin)؛ +2 اختبارات (TestSameConnectionCancel)؛ اكتشاف جانبي
  مصحح: معالج cancel_run كان يمرر ensure_ascii=False لـ
  sctx.send (TypeError عند أول إلغاء حقيقي عبر WS)؛ Performance:
  أول task_progress وسيط 0.18ms — لا تدهور؛ regression (S43):
  **1F/1695P/34S** — المتبقي الوحيد theme_tokens (TF-04/D-2).
  وقبلها: **TSK-605 جزء TF-02 ✅ (Sessions 40–41)** —
  تصحيح نطاق حارس التاريخ: إخراج `providers/` من مسح
  test_history_consumers (§0.8 — المزودات خارج النطاق) بتعليق
  معلّل؛ 41/41 في الملف؛ regression (S41): **1F/1693P/34S** —
  المتبقي الوحيد test_theme_tokens (TF-04)؛ إخفاقات البوابة 2→1؛
  فشل test_search_perf العابر (S39) لم يتكرر في S40 ولا S41.
  وقبلها: **TSK-604 ✅ DONE (Sessions 38–39)** — إصلاح TF-03
  (العيب الحي): زرا وكيلان مخفيان `run-history-btn`/`memory-panel-btn`
  في index.html — أهداف ربط app.js وتفويض Activity Bar، بلا تغيير
  مرئي ولا لمس app.js؛ + إعادة سطر «رخصة المشروع» لـ sprite.svg
  (TF-01)؛ القبول: 25/25 في ملفي القبول + فحص يدوي حي موثق (صفر
  أخطاء JS، /api/capacity يُستطلع)؛ إخفاقات البوابة 4→2؛ Regression:
  2F دائم (ملك TSK-605) /1692P/33S.
  وقبلها: **TSK-603 ✅ DONE (Session 37)** — بوابة موافقة
  fail-closed بنيويًا (ASF-02 · ALT-603→A): sentinel وحدوي
  `APPROVAL_GRANTED = object()` يُقارن بـ `is` — لا يمكن لنص AI
  إنتاجه؛ `tool_run_command` يرفض أي نداء بلا الرمز قبل أي فحص؛
  `execute(call, approved=True)` (الحلقة بعد ApprovalGate) يحقنه
  ويسقط أي `_approval` مزوّر من بلوك TOOL؛ 7 اختبارات جديدة
  (منها حارسان بنيويان) + تحديث 21 نداءً مباشرًا في الاختبارات؛
  القبول 3/3 ✅؛ Regression: 4F/1690P/34S (المعروفة فقط)؛ CHANGELOG
  مدخلة TSK-603.
  وقبلها: **TSK-602 ✅ DONE (Sessions 35–36)** — تسييج
  نتائج الأدوات والمعرفة (ASF-01) عبر fence_attached بمصدر موسوم —
  6 اختبارات (test_context_fencing.py)؛ القبول 3/3 ✅.
  وقبلها: **TSK-601 ✅ DONE (Sessions 33–34)** — إصلاح
  delegate_approve: استخراج `_parsed_to_actions`/`_parsed_options`
  (server.py:1439–1474) يستهلكهما مسارا agent/direct + المقبض؛
  النداءان الوهميان استُبدلا بـ parse() الحقيقية؛ فشل التحويل يُظهَر
  بإطار error (UXF-02)؛ اختبار جديد 6 حالات E2E
  (tests/integration/test_delegate_approve_handler.py) — القبول 4/4 ✅؛
  Regression: 4F/1677P/34S (الأربعة المعروفة فقط — لا جديد)؛
  CHANGELOG_ENGINEERING.md أُنشئ + سجل إغلاق كامل في DEVELOPMENT_TASKS.md.
  وقبلها: **Stage 2 PLANNING مكتمل ✅ (Session 31)** — §P.1
  تصنيف P0–P3 (لا P0؛ 6×P1) + §P.2 كتل ALT-601..604 بـ Competitive check
  وVision لكل P1 + §P.3 قرارات D-1..D-4 معلّقة للمالك؛ DEVELOPMENT_TASKS.md
  أُنشئ (TSK-601..626 عبر M6–M10 بقالب الدستور)؛ MASTER_ROADMAP مُمدد
  (M6–M10 + IR-1/IR-2).
  وقبلها: R10 Testing & Docs delta ✅ (Session 30) — §R10 في
  MASTER_REVIEW.md: (1) تشغيل كامل جديد 1709 = 4F/1671P/34S في ~70s —
  مجموعة الفشل مطابقة لـ S24 (حتمية، ليست flaky)؛ (2) فرز TF-01..04:
  ثلاثة كسرتها إعادة تصميم v25 غير الموثّقة — أخطرها TF-03 عيب حي:
  عنصرا run-history-btn/memory-panel-btn محذوفان من index.html بينما
  app.js:3639–3643 يربطهما ⇒ TypeError يقطع DOMContentLoaded فيعطّل
  status-chip وrefreshCapacity أيضًا؛ TF-02 تسرّب نطاق (الانتهاك الوحيد في
  providers/ المحظورة)؛ TF-05: بوابة check.sh حمراء دائمًا؛ (3) TD-01:
  صفر اختبارات لمقبض delegate_approve — يفسر نجاة RP-01 من الطبقتين
  (مع QF-02)؛ TD-02: خطة QA مجسدة (17 ملفًا)؛ (4) TD-03: RRR متجمد على
  «0/19 TSK» وG1–G3 FAIL رغم اكتمال التنفيذ — يحتاج release re-vote؛
  TD-04: v25 بلا أي توثيق هندسي.
  وقبلها: R9 UX & Agentic Capability ✅ (Session 29) — §R9 في
  MASTER_REVIEW.md: (1) تضييق SR-1 بالدليل — لوحة diff موجودة فعلًا (T-065،
  app.js:428/1689–1717) فالفجوة الحقيقية = خطة-تفاعلية + سرد جلسة فقط؛
  (2) أحكام CP النهائية: CP-2/3/7/9 مُغلقة، CP-1/CP-8 ADOPT→PLANNING،
  CP-4 مؤجل، CP-6 محسوم بإصلاح RP-01، CP-5 ⇒ UXF-04؛ (3) مصفوفة القدرة:
  3 خضراء (memory/multi-file/rollback)، 5 صفراء ترجع لثلاثة جذور (RP-01،
  RP-02+RF-01، فجوة الإظهار)، 0 غائبة؛ (4) UXF-01..05 (أبرزها UXF-02 C2:
  موافقة delegate صامتة الفشل — تُضم لمهمة RP-01).
  وقبلها: R8 Engineering Quality delta ✅ (Session 28) — NF-23.1/2/3
  VERIFIED-FIXED + NF-24 أُعيد فحصه آليًا (81 موديول، 0 دورات)؛ بوابة mypy
  خضراء (59 ملفًا)؛ تشخيص g1: ـ_dispatch_chat_message ~477 سطرًا +
  ـ_handle_ws_message ~469 + main ~281؛ خطة تفكيك QG-01..04 (راوتر WS →
  مسارات الإرسال → REST بعد قرار g5 → ضم mypy)؛ QF-01 improvements/ تلوث،
  QF-02 فجوة بوابة mypy (RP-01 كان قابلًا للالتقاط الساكن) — §R8.
  وقبلها بنفس الجلسة: R7 ✅ (خريطة المسارات + RP-01..04، أبرزها RP-01
  اعتماد التفويض مكسور — runtime-verified، server.py:2337–2338)
- Files/areas already covered: R-1..R6 (سابقًا) + R7 (قراءة كاملة runners/direct+
  agent+chain ورأس delegate؛ مقاطع server.py L1560–1900 توجيه/إرسال،
  L2312–2368 delegate_approve/reject، L2385–2403 ws_handler؛ chain/delegate.py
  land/reject L588–640؛ app.js معالجات delegate 615–637/3279+) + R8 (فحص
  دورات آلي، scripts/check.sh كامل، إحصاء بنيوي لـ server.py، mypy run)
  + R9 (greps مصوَّبة فقط: showPlanCard app.js:3099–3128 + plan handler
  219–223؛ إطارا plan server.py:1804/1898؛ verify-step
  chain/agent_loop.py:343–408؛ remember_fact chain/agent_tools.py:38 +
  ProjectMemoryStore server.py:2786–2797؛ Memory Panel app.js:3492–3546؛
  RunHistory app.js:3391–3420؛ diff panel app.js:428/1689–1717 (T-065)؛
  chain_cancel app.js:1153؛ جرد agents_rules/) + R10 (تشغيل كامل للعدة؛
  فحص الإخفاقات الأربعة بالدليل: sprite.svg رأس، index.html:212/220،
  app.js:3638–3645، tests/unit/test_rollback_ui.py:424–434،
  test_file_icons.py:143؛ QA_MASTER_PLAN كامل + RELEASE_READINESS_REPORT
  كامل؛ جرد استشهادات QA-T في tests/ وغياب delegate_approve منها)
- Next action: **لا شيء — البرنامج مُقفل 🏁** (Stage 3 = 26/26؛ مسح
  الديون S83 = صفر؛ توجيه المالك S83 مُنفَّذ بالكامل — لا دين حتمي
  بقي ليُشرح). أي عمل قادم = دفعة جديدة تبدأ بمراجعة الـ backlog
  الاختياري الموثَّق مع المالك (قرار IR-2): FUTURE_IMPROVEMENTS
  (FI-01/03/04/05/06/07/09/10/11/12) + CP-4 hooks (ADOPT-CANDIDATE
  مؤجل بقرار IR-1). خط الانحدار المرجعي: **1901 = 0F/1867P/34S**
  (test_search_perf معروف flaky — معزولًا عند فشله).
  ملاحظة تشغيلية: دمجُ المستودع يعيد أحيانًا شجرة improvements/
  المحذوفة (TSK-623) — عند ظهورها: تحقق `diff -r` مقابل الأرشيف ثم
  أعد `git rm -r improvements/` (حدث S83 مرتين).
- Current blocker: **لا شيء**. الخريطة السابقة [محلولة S83 كاملة]:
  D-2←605 ✅؛ D-1←617 ✅؛ D-4←622 ✅؛ D-3←623 ✅ (قيود DECISION_LOG
  S83: قرارات المالك + IR-2).

### Stage Checklists (Definition of Done — الدستور الجديد)
#### Stage 1 — REVIEW
- [x] R-1 Repository Inventory *(Session 24 — MASTER_REVIEW.md §R-1)*
- [x] R0 Strategic Architecture Assessment *(Session 25 — MASTER_REVIEW.md §R0)*
- [x] R1 Repository Understanding *(Session 25 — delta متحقق، MASTER_REVIEW.md §R1)*
- [x] R2 Strengths Preservation *(Session 25 — Strengths Register S-01..S-14، MASTER_REVIEW.md §R2)*
- [x] R3 Architecture Audit + Architecture Scorecard *(Session 25 — MASTER_REVIEW.md §R3)*
- [x] R4 Security Review (+ Agent Safety) *(Session 26 — MASTER_REVIEW.md §R4: NF-15..18 مُرحّلة + ASF-01..08 + حكم المحاور الستة)*
- [x] R5 Reliability Review *(delta)* *(Session 26 — MASTER_REVIEW.md §R5: NF-01..14 مُرحّلة + RF-01..03)*
- [x] R6 Performance Review (with baseline metrics) *(Session 27 — MASTER_REVIEW.md §R6: NF-20/21/22 VERIFIED-FIXED + baselines + PM-01..04 NOT INSTRUMENTED)*
- [x] R7 Runtime Pipeline Review *(Session 28 — MASTER_REVIEW.md §R7: خريطة المسارات الأربعة + RP-01..04، أبرزها RP-01 اعتماد التفويض مكسور)*
- [x] R8 Engineering Quality Review *(delta)* *(Session 28 — MASTER_REVIEW.md §R8: NF-23/24 مُرحّلة + خطة تفكيك g1 (QG-01..04) + QF-01/02)*
- [x] R9 UX & Agentic Capability Review *(Session 29 — MASTER_REVIEW.md §R9: تضييق SR-1 (diff panel موجودة T-065) + أحكام CP-1..9 النهائية + مصفوفة القدرة الوكلية (8 قدرات، 0 غائبة) + UXF-01..05)*
- [x] R10 Testing & Documentation Review *(delta)* *(Session 30 — MASTER_REVIEW.md §R10: خط أساس مُعاد قياسه 4F/1671P/34S (مطابق S24 — حتمي) + فرز TF-01..05 (TF-03 عيب حي C3: أزرار محذوفة تقطع DOMContentLoaded) + TD-01 صفر تغطية لمقبض delegate_approve + TD-03 RRR متجمد يحتاج re-vote)*
#### Stage 2 — PLANNING
- [x] Findings prioritized (P0–P3) with Engineering Alternatives *(Session 31 — MASTER_REVIEW.md §P.1 جدول كامل (لا P0؛ 6×P1) + §P.2 أربع كتل ALT لكل P1 مع Competitive check وVision line)*
- [x] DEVELOPMENT_TASKS.md populated (all tasks meet template) *(Session 31 — TSK-601..626 عبر M6–M10؛ قالب كامل لكل مهمة + جدول حالة؛ 3 مهام BLOCKED على قرارات D-1/D-2/D-3)*
- [x] MASTER_ROADMAP.md extended (milestones + innovation reviews) *(Session 31 — M6–M10 + IR-1 بعد M8 وIR-2 بعد M10)*
#### Stage 3 — EXECUTION
- [ ] (auto-tracked per task)

### Architecture Scorecard (R3 — Session 25؛ يُعاد حسابه بعد كل milestone)
| Subsystem | Score /10 | Last updated | Trend |
|---|---|---|---|
| Core runtime | 8.5 | 2026-07-28 | baseline |
| Server composition (server.py) | 5.5 | 2026-07-28 | baseline (g1 مفتوح) |
| WS lifecycle & dispatch | 7 | 2026-07-28 | baseline |
| Chain system | 7 | 2026-07-28 | R4 غطّت الأمن (ASF-01..08)؛ يتبقى R7 للتدفق |
| Context engine | 8.5 | 2026-07-28 | baseline |
| Actions | 8 | 2026-07-28 | baseline |
| Runners contract | 8 | 2026-07-28 | baseline |
| Sessions & retention | 8 | 2026-07-28 | baseline |
| Frontend | 6 | 2026-07-28 | baseline (فجوة Phase 9) |
| Prompts & injection surface | 7.5 | 2026-07-28 | baseline |
| Security posture (in-scope) | 7 | 2026-07-28 | baseline |
| Testing infra | 8.5 | 2026-07-28 | baseline |
| Observability (AI-runtime) | 3 | 2026-07-28 | baseline (فجوة رئيسية → R6) |
| Workspace/git integration | UNKNOWN | 2026-07-28 | يُثبَّت في R5/R8 |

### Pending Git Actions (awaiting owner instruction)
- Session 24 commit `1b2a7b0` (MASTER_REVIEW.md + PROGRESS header) — **مدفوع بالفعل إلى main** (تم خارجيًا).
- commits هذه الجلسة: ستُنشأ محليًا فقط — لا push دون تعليمات صريحة.
- ملاحظة: `origin/genspark_ai_developer` متأخر عن `main` (توقف عند ac43f6c/P8) —
  قرار المزامنة بانتظار المالك.

### Baseline snapshot (Session 24 — بيئة جديدة)
| Metric | Value | How measured | Date |
|---|---|---|---|
| Full test suite | 1709 tests: 4 failed / 1671 passed / 34 skipped | pytest --junitxml (تشغيل كامل) | 2026-07-28 |
| Suite wall time | ~82s | تشغيل مباشر | 2026-07-28 |
| `import server` | OK | تشغيل مباشر | 2026-07-28 |
| Legacy failure #5 (test_symbol_index…missing_file) | **PASSES الآن** [SUPERSEDED — 2026-07-28 — grammars متوفرة في البيئة الحالية] | pytest -k | 2026-07-28 |

### Session Log — New Lifecycle (append-only)
> **تدوير §6.4 (2026-07-30, S89/D-6)**: قيود Sessions 24–83 (حقبة V1)
> وأرشيف v4.1 المضمَّن رُحِّلا إلى `PROGRESS_ARCHIVE_1.md` — المقاطع
> الحاكمة أعلاه لم تُمَس. أدناه قيود حقبة V3 فقط (S84+).
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

### إقفال TSK-726c — نقل الجلسات/النماذج/المرفقات/drag-drop ⇒ app/30 🏁
- **ما نُفِّذ:** نقل حرفي (verbatim) لـ 496 سطرًا من app.js (الأسطر 1953–2448) إلى
  `static/js/app/30_sessions_models_attachments.js`: إدارة الجلسات
  (toggleSessions/loadSessions/loadSession/newSession/deleteSession)،
  النماذج (loadModels/renderModelList/switchModel)، الثوابت
  (_TEXT_EXTENSIONS/_IGNORE_DIRS/_MAX_*)، والمرفقات + drag-drop
  (initDragDrop/readDirectoryRecursive/attachFile/attachFolder/renderAttachments).
- **app.js:** 3131 → 2636 سطرًا.
- **الربط:** index.html — المقطع 30 بعد app.js وقبل 90 (ترتيب رقمي محفوظ).
- **الحارس:** test_app_split 7/7 نجحت دون تعديل — العقد (التقييم بعد app.js) سليم.
- **البوابة:** `bash scripts/check.sh` — **2050 passed / 34 skipped — ALL GREEN** (rc=0).
- **Commit:** 472dca9 على origin/main.
- **الحالة:** 726c 🏁 — التالي 726d (اللوحات: plan/delegate/memory/history/status-chip/settings/permissions + diagnostics).

### إقفال TSK-726d — نقل اللوحات ⇒ app/40 🏁
- **ما نُفِّذ:** نقل حرفي (verbatim) لـ 682 سطرًا من app.js (الأسطر 1954–2635) إلى
  `static/js/app/40_panels.js`: Plan Card (showPlanCard/executePlan/revisePlan/
  reviewPlan/cancelPlan/updateTaskProgress)، Delegate UI، sendPathAction،
  renderSessionNarrative، Run-History/Rollback (toggleRunHistory/confirmRollback/
  consumeRollbackDecision/handleRollbackResult)، Memory Panel، downloadDiagnostics،
  Permissions/Settings panels، Status Chip (+CAPACITY_POLL_MS/refreshCapacity)،
  setActivityView.
- **app.js:** 2636 → 1951 سطرًا.
- **الربط:** index.html — المقطع 40 بعد 30 وقبل 90 (ترتيب رقمي محفوظ).
- **ترحيل اختبارات:** كشفت البوابة 5 ملفات wiring تقرأ APP_JS مباشرة
  (permissions/plan_card/rollback_ui/session_narrative/settings) — رُحِّلت إلى
  قارئ الحزمة `_app_bundle()` بالنمط المعتمد (التوكيدات لم تتغير).
- **الحارس:** test_app_split 7/7 نجحت دون تعديل.
- **البوابة:** `bash scripts/check.sh` — **2050 passed / 34 skipped — ALL GREEN** (rc=0).
  (تشغيلة أولى أظهرت فشلًا عابرًا واحدًا في test_no_save_churn_when_list_unchanged
  — mtime flake بيئي؛ نجح منفردًا وفي إعادة البوابة كاملة.)
- **ملاحظة بيئية:** الحادثة رقم 13 لتدمير البيئة — بوت الرفع التلقائي أنقذ
  استخراج 40_panels @ a3d355f (تُحقِّق منه حرفيًا: 684-/690+ ونحو node --check سليم).
- **Commits:** a3d355f (استخراج+ربط، بوت) + 34050aa (ترحيل الاختبارات).
- **الحالة:** 726d 🏁 — التالي 726e (قلب الدردشة/WS/البث — الأخطر، آخر شريحة؛ هدف app.js < 800 سطر… الوضع الحالي 1951).

### إقفال TSK-726e — قلب الدردشة/WS/البث ⇒ app/10 🏁 (وإقفال TSK-726 بالكامل 🏁)
- **ما نُفِّذ:** نقل حرفي (verbatim) لـ 1237 سطرًا من app.js
  (الأسطر 141–1221: WebSocket initWebSocket/handleWSMessage + بطاقات الطرفية
  handleRunCommandStep/renderTerminalCard/respondAgentApproval + قلب الدردشة
  sendMessage/buildChatMessage/البث TSK-401 startStreaming→finalize +
  streamThrottler + الإيقاف stopGeneration؛ والأسطر 1296–1452:
  Apply Buttons/Actions Bar) إلى `static/js/app/10_chat_ws_stream.js`.
- **أمان eval-time:** `const wsReconnectBackoff = WSBackoff.createBackoff()`
  و`StreamRender.createThrottler()` — الوحدتان UMD تسبقان app.js فتقييم
  المقطع بعده آمن (العقد المُعدَّل في S103 محفوظ).
- **app.js:** 1951 → **712 سطرًا** — الهدف (< 800) مُحقَّق. المتبقي:
  state + boot + الثيمات + أدوات (escapeHtml/toast/markdown/direction/
  quick-replies/resize/openFolder/…).
- **الحارس:** تعديل توكيد sendMessage — قلب الدردشة يعيش حصريًا في
  10_chat_ws_stream.js (كان «قبل 726e»)؛ 7/7 نجحت.
- **ترحيل اختبارات:** 3 وحدات (snapshot_cap_visibility/stream_render/
  ws_backoff ⇒ _app_bundle) + 2 تكامل (scan_start ثابت APP_JS المجمَّع؛
  except_narrowing قراءة داخلية مجمَّعة).
- **البوابة:** `bash scripts/check.sh` — **2050 passed / 34 skipped — ALL GREEN** (rc=0).
- **ملاحظة بيئية:** الحادثة رقم 14 — بوت الرفع أنقذ ترحيل التكامل @ 9000760
  (تُحقِّق منه ثم أُعيدت البوابة كاملة خضراء بعد الاستنساخ).
- **Commits:** c45dfa2 (استخراج app/10 + حارس + 3 ترحيلات) + 9000760 (ترحيل التكامل، بوت).

**TSK-726 مُقفلة بالكامل 🏁 (a+b+c+d+e)** — FI-07 مُنجزة:
app.js 4204 ⇒ 712 سطرًا + 6 مقاطع مجالية (10/20/30/40/90/91 = 3527 سطرًا)
بنطاق عام مشترك وترتيب تحميل رقمي محروس باختبار test_app_split الدائم.
التالي حسب DAG D-10: تفصيل TSK-727 (الغلاف المكتبي) — آخر مهام P2.

### إقفال TSK-727 — غلاف سطح المكتب Windows-أولًا (a+b+c) 🏁 (كود + وثائق؛ تحقق المالك معلَّق)
- **727a (القرار):** موازنة pywebview/Tauri/Electron مكتوبة في §TSK-727
  (S104) — **القرار: pywebview + PyInstaller** (نفس اللغة، صفر سلاسل
  أدوات جديدة، صفر لمس للكود المُختبر)؛ قيد S104 في DECISION_LOG +
  **ADR-006** في ARCHITECTURE_DECISIONS.md — قبل أي كود (D-7).
- **727b (المُطلِق):** `desktop.py` — منفذ حر (bind 0) → server.main()
  بخيط خلفي daemon (صفر تعديل على server.py؛ غلاف signal.signal يبتلع
  ValueError خارج الخيط الرئيسي حصريًا) → انتظار جاهزية HTTP →
  webview.create_window؛ pywebview اختيارية محروسة import (غيابها ⇒
  رسالة عربية إرشادية + إحالة لوضع المتصفح). **8 اختبارات بنيوية**
  (test_desktop_launcher: import-safe/رسالة الغياب/منفذ حر/جاهزية/
  عقد ADR-006 نصيًا: server.py غير ممسوس + 127.0.0.1 حصريًا)؛
  pywebview في requirements كتعليق اختياري؛ desktop.py ضُم لبوابة mypy.
- **727c (التغليف):** `desktop.spec` (datas: static + agents_rules +
  chain/prompts + config.yaml؛ hiddenimports: flask_sock/simple_websocket/
  yaml؛ console=False) + `docs/desktop/WINDOWS_BUILD.md` (أمرًا-بأمر)
  + `docs/desktop/OWNER_CHECKLIST.md` (7 محاور/20 بندًا).
- **البوابة:** `bash scripts/check.sh` — **2058 passed / 34 skipped —
  ALL GREEN** (rc=0) — خط الأساس الجديد (+8 اختبارات المُطلِق).
- **ملاحظة بيئية:** الحادثة رقم 15 — البوت أنقذ desktop.spec @ 36cfb35
  (تُحقِّق منه وأُصلح: ضم chain/prompts المقروءة وقت التشغيل).
- **Commits:** 13338d2 (a) + 8bf8e45 (b) + 36cfb35/5479b1e (c).
- **بند خارجي معلَّق (لا يمنع P3):** تأشير المالك على OWNER_CHECKLIST
  على Windows (D-8-ب) — إقفال P2 النهائي الرسمي عنده.

**دفعة D-10 (P2) مكتملة الكود 🏁**: 723 ✅ 724 ✅ 725 ✅ 726 ✅ 727 ✅.

### إغلاق TSK-728 🏁 (2026-07-31 — BATCH-P3/D-11، CP-4)
- **core/hooks.py (728a):** HookRunner بعقد «تشديد-فقط»: pre_command
  fail-closed (فشل/مهلة/خروج ≠0 ⇒ حجب)؛ post_write/post_run تحذير فقط؛
  غياب قسم hooks: ⇒ صفر subprocess (سلوك اليوم حرفيًا)؛ لا واجهة
  موافقة بالبناء (محروس باختبار سطح-الواجهة).
- **الحقن (728b):** pre_command في CommandRunner.run **قبل** كل فحوص
  الموافقة (يغطي المسارين الكلاسيكي والوكيلي — tool_run_command يفوّض
  التنفيذ إليه)؛ _hook_runner() مُكاش في server.py موصول بموضعَي البناء.
- **728c:** post_run بعد كل تنفيذ فعلي + post_write عبر درز T-049
  (add_write_hook — يغطي write_file/edit_file بلا مسّ الكتابة الذرّية)
  + مثال معلَّق في config.yaml (الافتراضي بلا خطّافات — محروس باختبار
  yaml.safe_load).
- **العقد محروس بـ 34 اختبارًا** (19 وحدة نقية بsubprocess حقيقي +
  15 عقد/توصيل) — أبرزها: «hook ناجح لا يتجاوز بوابة الموافقة» و«حتى
  الأمر الآمن يُحجب لو رفضه الـ hook».
- **إصلاح بوابة:** تلميح نوع _hook_runner_cache (mypy) @ aa276ba.
- **البوابة:** **2092P/34S** ALL GREEN rc=0 (خط أساس جديد، +34)؛
  إعادة واحدة لرجفة mtime المعروفة (test_no_save_churn — نجحت منفردة
  وفي الإعادة الكاملة؛ نفس رجفة 726d البيئية).
- **ملاحظة بيئية:** الحادثتان 16 و17 — البوت أنقذ 8c4dbd6 (728b جزئيًا،
  تُحقِّق منه)؛ وثائق الإغلاق أُعيدت بعد التصفير (هذا القيد).
- **Commits:** 4b2a4f5 (a) + 13863e6 (b) + 30b772a (c) + aa276ba (mypy).

**TSK-729 مغلقة 🏁 (BATCH-P3/D-11 — FI-04 مُكيَّفة، 2026-07-31):**
- **729a**: توافق fakeredis — `tests/unit/test_redis_seam_fake.py` يشغّل عدة T-108 (EventBusBackendContractMixin) كاملة فوق `fakeredis.FakeRedis(decode_responses=True)` في **كل** بوابة محلية (كانت 9 اختبارات تُتخطى دائمًا محليًا)، + إعادة قراءة مرتبة/رؤية عبر backend ثانٍ/سقف MAXLEN + دورة قائمة العمل (enqueue/claim/ack + استرداد مستهلك ميت min_idle).
- **729b**: حارس عدم التسرّب — بنيوي (كل استيراد backends_redis في server.py محروس بفرع worker) + تشغيلي (استيراد server لا يحمّل مكتبة redis — فحص subprocess معزول لأن fakeredis نفسها تستورد redis)؛ `worker.DEFAULT_DISPATCH == "in-proc"` مُثبَّت.
- **729c**: مقطع §7 في `docs/deployment_threat_model.md` (FI-12) — تفعيل الوضع الموزَّع الاختياري بإحالة إلى worker_runbook + اتساع حدود الثقة + إعادة تأكيد قيد D-11 (الافتراضي لا يتغير).
- **البوابة**: `bash scripts/check.sh` = **2109 passed / 34 skipped — ALL GREEN** (خط أساس جديد؛ +17 عن 2092P).
- **Commits:** 4b442bf (a+b) + 8c91c30 (c).

**TSK-730 مغلقة 🏁 (BATCH-P3/D-11 — plugins توسيع، 2026-07-31):**
- **730a**: إظهار glass-box — مفتاح `plugins = {loaded مفروزة, quarantined عبر to_dict()}` في `/api/diagnostics` (routes/meta.py) من plugin_registry؛ None/انفجار السجل ⇒ قوائم فارغة (التشخيص لا يفشل أبدًا)؛ عقد التطهير TSK-721 صامد — 4 اختبارات.
- **730b**: إثراء PluginContext في المسار الحقيقي — `PlanRequest.run_id` (bridge يمرّر المعرّف المُنشأ) → select_strategy → `_build_via_plugin` يمرّر run_id + `metadata={"complexity": analysis.to_dict()}`؛ الافتراضي "" = سلوك تاريخي حرفي (goldens الـ planner صامدة)؛ قيد موثَّق: emit تبقى noop وقت التخطيط — 7 اختبارات (tests/unit/test_plugin_context_enrichment.py).
- **730c**: توثيق مؤلّف الإضافات — examples/demo_strategy/README.md (سطحا run_id/metadata + قيد emit + ظهور التشخيص).
- **البوابة**: `bash scripts/check.sh` = **2120 passed / 34 skipped — ALL GREEN** (خط أساس جديد؛ +11)؛ فشل search_perf البيئي المعروف ظهر مرة وزال على إعادة نظيفة.
- **Commits:** fde6eca (تفصيل) + 3df2247 (a) + 4b588a9 (b) + 2a72147 (c).

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
---
- **[مؤشر أرشيف]** كل ما قبل S84 (بما فيه برنامج v4.1 Sessions 1–23):
  انظر `docs/engineering/PROGRESS_ARCHIVE_1.md` (append-only، لا يُعدَّل).
