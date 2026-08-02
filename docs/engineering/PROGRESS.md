# PROGRESS.md — editor_v4 Engineering Program (CORE-ONLY SCOPE v4.1)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.
> النطاق محكوم بـ SECTION 0.8: النظام الأساسي فقط — Provider Layer خارج النطاق كليًا.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-08-02 (Session 107 — **CEV-G8 🏁 PASS (طبقة تنفيذ AI)** @ 5d083d5: عزل providers تام (عقد base فقط)، سقف حلقة صلب 8، إلغاء ثنائي المصدر مفحوص عند كل حد، retry بميزانية، بث أحادي المسار، ابتلاع منضبط ×29؛ 394/394 حارس مركّز + check.sh ALL GREEN؛ اكتشافان: F-010 (hh.har دخيل 7.2MB) + F-011 (42 استيرادًا ميتًا + تصحيح دليل pyflakes)؛ G7 مؤجلة D-14) |
| stage | **V3-STAGE 4 → برنامج CEV مفتوح (D-12)** — سوابق مُقفلة كلها 🏁: BATCH-P0 6/6 (v1.0.0-rc.1) + BATCH-FI01 5/5 + BATCH-SHORT 5/5 + D-6 5/5 + BATCH-P1 6/6 (D-9) + BATCH-P2 5/5 (D-10) + BATCH-P3 4/4 (D-11) + EOP-1 |
| current-phase | **CEV (D-12)**: بوابات G1..G12 (+G8.5 AIA) — وثيقة التكليف: `CEV_PROGRAM_PROMPT.md`؛ **G1→G6 + G8 كلها 🏁 PASS** (سبعة تقارير مؤرخة في MASTER_REVIEW)؛ **G7 (الأمان/Red Team) مؤجلة DEFERRED بقرار مالك D-14** (تُستأنف بأمر لاحق — تسبق G12 وجوبًا)؛ البوابة المفتوحة: **G8.5 (AIA — حوكمة طبقة الذكاء)** |
| current-task | **CEV-G8.5 OPEN (AIA — حوكمة طبقة الذكاء، §4-B)**: agents_rules/ + prompts/ + chain/prompts/ + newskells/ ككود إنتاجي — مراسي AIA-0 (manifest.yaml/agent_loader حصريًا، router+routing_config، حارس الحقن NF-18 خط أحمر، newskells غير محمَّل، لا إعادة هيكلة مجلدات) + قواعد AIA-R1..R13 + مراحل AIA-1..7؛ خط الأساس (حي S107): **2189P/34S/0F ALL GREEN rc=0**؛ قرارات مالك معلَّقة: F-003 (أ/ب — الحذف ×9) + F-010 (حذف hh.har)؛ معلَّق خارجي: OWNER_CHECKLIST (727) + رفع استثناء providers |
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
**CEV مفتوح (قرار مالك D-12 — 2026-08-01)** — برنامج تدقيق جودة صفر-ميزات
تحت حكم V3؛ الوثيقة: `CEV_PROGRAM_PROMPT.md`؛ البوابات G1..G12 (+G8.5
AIA) بالترتيب؛ المفتوحة الآن: **CEV-G1 (البنية)**.
[أرشيف المرحلة السابقة] BATCH-P0 🏁 6/6 (v1.0.0-rc.1) → … → BATCH-P3 🏁 4/4
(D-11) + EOP-1 🏁 — برنامج D-8-ج مكتمل؛ التعريفات: DEVELOPMENT_TASKS

### Current Position
- Stage: **CEV (D-12) — G1→G6 + G8 كلها 🏁 PASS؛ G7 مؤجلة DEFERRED (D-14)؛ المفتوحة: G8.5 (AIA)** — Stage 1 REVIEW؛ الاكتشافات → NEW_FINDINGS (المفتوحة: F-003 قرار مالك ×9؛ F-010 حذف hh.har قرار مالك؛ F-011 TSK مقترحة؛ F-006/F-007/F-008/F-009 لا فعل الآن)؛ سوابق مُقفلة كلها: P0→P3 🏁 + EOP-1 🏁
- خط أساس البرنامج (أُعيد تثبيته حيًّا S106ي @ 5e77751): **2189P/34S/0F** + check.sh ALL GREEN rc=0
- [أرشيف] خط أساس فتح CEV (موثَّق S105): 2168P/34S + check.sh ALL GREEN rc=0
- [أرشيف موضع BATCH-P2 عند فتحها] خط أساسها (حي @ 9a3aed0): 1911P/34S + check.sh ALL GREEN rc=0
- برنامج ما-بعد-P0 المفوَّض (D-8-ج): P1 (FI-05، لوحة تشخيص، تدوير سجلات، Settings UI) → P2 (FI-09، FI-07، Command Palette، Workspace Trust، غلاف سطح مكتب) → P3 (FI-04، CP-4، توسيع plugins، auto-update) — كل دفعة بتخطيط TSK مسبق وقيد قرار
- بند ختامي مُرحَّل: EOP-1 — **مُنفَّذ 🏁 2026-07-31 بأمر مالك صريح** (حذف engineering_constitution/، قرار D-8-أ)
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
- **2026-08-02 — Session 107 — قرار مالك D-14 (تأجيل G7/Red Team) ⇒ بوابة CEV G8 🏁 PASS (طبقة تنفيذ AI) — G8.5 (AIA) مفتوحة**:
  تصفيرات بيئة #24/#25 (§3.1: استنساخ + TOKEN_SCRUB_DONE؛ اعتماد
  لُصق بنص التكليف ×2 — تذكير §3.2 مُبلَّغ)؛ انقطاع منتصف S107 الأول:
  D-14 + F-010 + فتح G8 نجت عبر البوت @ 5d083d5، تقرير G8 فُقد
  وأُعيدت كتابته بأدلة معاد تثبيتها حيًّا. `.env` fixture أُعيدت
  (×8/×9 — F-003 بلا قرار بعد). **D-14 مقيَّد في DECISION_LOG**:
  G7 مؤجلة DEFERRED (ليست PASS) — تسبق G12 وجوبًا؛ الترتيب المعدل:
  G8→G8.5→G9→G10→G11→[G7]→G12. **تنفيذ G8 @ 5d083d5**: عزل
  providers تام (استيرادات chain/ من العقد المجرد base حصريًا؛ صفر
  مزود ملموس)؛ سقف حلقة صلب MAX_ITERATIONS=8 مزدوج؛ إلغاء ثنائي
  المصدر (علم + تذكرة) مفحوص رأس كل دورة وقبل كل أداة، cancel()
  يفك الموافقة المعلّقة؛ إنهاء تذكرة مضمون بكل المسارات؛ retry
  محكوم بميزانية reserve_call مع فحص إلغاء قبل كل محاولة؛ بث
  ChainEvent أحادي المسار (callback+jsonl)؛ ميزانية سياق عبر
  ContextBudget.pack حصريًا؛ ابتلاع منضبط ×29 عبر structured_log؛
  NF-18 قائم (تدقيقه الكامل في G8.5). **394/394 حارس مركّز يمر**
  (goldens bit-identical + cancellation + parity + gated approvals
  + crash_resume + contracts 113). **اكتشافان**: CEV-F-010 (C3 —
  chain/hh.har دخيل 7.2MB، صفر اعتمادات/مراجع، حذفه قرار مالك) +
  CEV-F-011 (C3 — 42 استيرادًا ميتًا عبر النطاق، pyflakes خارج
  البوابة؛ + تصحيح دليل ملزم: ادعاء «pyflakes نظيف» في جولة أولى
  كان زائفًا لغياب الأداة — أُعيد الفحص بعد تثبيتها). ⇒ **تقرير
  CEV-G8 PASS مؤرخ في MASTER_REVIEW**. بوابة الإقفال: check.sh
  كاملة (النتيجة بذيل هذا القيد). **الموقع: G8.5 (AIA) مفتوحة؛
  صفر تغيير كود — وثائق + استعادة fixture حصرًا.**
- **2026-08-02 — Session 106ي — سدّ فجوة اتساق (أمر مالك صريح: «سد فجوة الاتساق فقط») — CEV-G6 🏁 مُسجّلة في السلطة الوحيدة للحالة**:
  تصفيرا بيئة #21/#22 (§3.1 ×2: استنساخ + TOKEN_SCRUB_DONE؛ اعتماد
  لُصق في نص التكليف ×2 — تذكير التدوير §3.2 مُبلَّغ للمالك).
  **الفجوة المكتشفة**: S106ط وثّقت تقرير CEV-G6 🏁 PASS في
  MASTER_REVIEW (التقطه البوت @ 5e77751 مع F-009 في NEW_FINDINGS)
  لكنها انقطعت قبل تحديث PROGRESS.md — الترويسة بقيت G6 OPEN
  وCurrent Position بقي عند G1. **السد**: تحديث الترويسة
  (G1→G6 كلها 🏁) + Current Position (التالية G7 بانتظار أمر
  فتح — لم تُفتح ذاتيًّا؛ أمر المالك كان السد فقط) + هذا القيد.
  **إعادة تثبيت خط الأساس حيًّا @ 5e77751**: `bash scripts/check.sh`
  كاملة ⇒ **2189 passed / 34 skipped / 0 failed — ALL GREEN rc=0**
  (91.3s؛ مطابق للموثَّق — صفر انحدار؛ متقلبا F-006 لم يظهرا).
  `.env` fixture كانت محذوفة مجددًا على origin قبل هذه الجلسة
  (F-003 النمط المستمر @ 37a371f — الاستعادة ×7) — أُعيدت من
  a9f52b5 قبل البوابة؛ قرار المالك أ/ب ما زال معلَّقًا. **صفر
  تغيير كود — وثائق + استعادة fixture حصرًا. الموقع: G1→G6
  مُقفلة؛ G7 (الأمان) التالية بانتظار توجيه المالك.**
- **2026-08-02 — Session 106ح — بوابة CEV G5 🏁 PASS (الأداء) — G6 (الخلفية) مفتوحة + تدوير §6.4 (دفعة 3)**:
  تصفيرا بيئة #19/#20 (§3.1 ×2: TOKEN_SCRUB_DONE؛ البوت التقط عمل
  S106ز @ 0e959cd — تقرير G4 + F-008 كاملان على origin)؛ `.env`
  fixture أُعيد (×5/×6) والحارس يمر. **تدوير §6.4 دفعة ثالثة**:
  مدخلات S102–S103 المؤرخة (107 أسطر) → PROGRESS_ARCHIVE_2 —
  السجل 280/400. **تنفيذ G5 بأرقام موحدة في بيئة واحدة @ 0e959cd**:
  استيراد بارد 357ms؛ إقلاع→200 = 635ms؛ RSS خامل 52.4MiB → بعد
  200 طلب 52.7MiB (Δ+0.3 — لا تسريب، 3.2ms/طلب)؛ TSK-724
  computeWindow 0.036ms/نداء ويصيّر 18 من 5000 عنصر (ثابت المجموع
  محروس)؛ بث 100KB (1600 chunk بأُطر 16ms) حارس يمر؛ بحث 5k
  QA-T13: api 156ms / tool 129ms (سقف 1000ms — هامش ×6-7)؛
  ProjectIndex snapshot (TSK-719): بارد 164ms → دافئ 125ms،
  rebuilds 1→0، snapshot 97KB. **71/71 حارس أداء يمر** في تشغيل
  نظيف (المتقلب F-006 ظهر مرة في أول تشغيل ثم مرّ ×3 معزولًا —
  مطابق للتوثيق). ⇒ **تقرير CEV-G5 PASS مؤرخ في MASTER_REVIEW**.
  **الموقع: G6 (الخلفية — blueprints + server.py + worker seam)
  مفتوحة؛ صفر تغيير كود.**
- **2026-08-02 — Session 106ز — بوابة CEV G4 🏁 PASS (البصريات) — G5 (الأداء) مفتوحة**:
  تصفير بيئة #18 (§3.1: استنساخ + TOKEN_SCRUB_DONE)؛ البوت التقط
  عمل S106و @ 2e1d273 (تقرير G3 + تحديث F-003 + ترويسة)؛ `.env`
  fixture أُعيدت استعادته (×4) والحارس يمر. **تنفيذ G4** (مسح ثابت
  كمّي 4557 سطر CSS + حراس + تحميل حي): عقد الألوان T-060/R-905
  **مثالي** — صفر خام خارج themes (بوابة check.sh:106-118)، ظلال
  color-mix توكنية، 28/28 حارس تكافؤ/WCAG يمر؛ أيقونات R-903 توكنية
  بالكامل (file_icons.js colorToken + sprite)؛ radius: 19 إعلانًا
  خام يكرر --radius/--radius-lg حرفيًا + 9×0.15s مدة بلا توكن ⇒
  **CEV-F-008 (C3)** مع TSK اختياري (استبدال + --transition-fast)؛
  ثانويات C4 (bold×2، أحجام 11.5/12.5px، !important قلب ×36)؛ تحميل
  حي: كل CSS 200 + صفر أخطاء JS (404 الوحيد = favicon F-007) ⇒
  **تقرير CEV-G4 PASS مؤرخ في MASTER_REVIEW**. **الموقع: G5 (الأداء
  — أرقام قبل/بعد إلزامية) مفتوحة؛ خط الأساس 2189P/34S/0F بلا
  تغيير كود.**
- **2026-08-02 — Session 106و — بوابة CEV G3 🏁 PASS (تجربة الاستخدام) — G4 (البصريات) مفتوحة**:
  استئناف عبر تصفيرات بيئة (#16/#17/#18؛ §3.1: TOKEN_SCRUB_DONE في
  كلٍّ منها). **حادثة متكررة**: Auto-Uploader حذف
  `tests/fixtures/sample_project/.env` مرة **ثانية** @ 37a371f (بعد
  استعادة S106ب) — أُعيدت الاستعادة من a9f52b5 (×4 إجمالًا) والاختبار
  الحارس `test_sample_project_fixture_isolated` يمر؛ ⇒ **تحديث تكرار
  CEV-F-003** في NEW_FINDINGS مع خياري مالك (أ: استثناء
  `tests/fixtures/` من تنظيف البوت — خارج المستودع؛ ب: تفويض إعادة
  تسمية الـfixture إلى `env.fixture` + تحديث المستهلكين — TSK صغير
  يقفل الثغرة نهائيًا). **قرار مالك مطلوب — التكرار سيستمر بدونه.**
  **إقفال G3**: تمشية مستخدم أول مرة على خادم حي (127.0.0.1:5000)
  — **17/17 خطوة خضراء**: Trust fail-closed (تشغيل قبل الثقة يُرفض
  «رفض المستخدم»)، عزل الثقة لكل مشروع (decided_at/decided_by)،
  فتح/حفظ ملف، Ctrl+K، لوحة الأوامر، دردشة/خطة/موافقات، الجلسات،
  الذاكرة، WS pong ctx:true، طزاجة البحث write-through، desktop.py
  استيراد headless سليم، صفر احتكاك ⇒ **تقرير CEV-G3 PASS مؤرخ في
  MASTER_REVIEW** (التقطه البوت @ 2e1d273 مع تحديث F-003 وترويسة
  PROGRESS). **الموقع: G4 (البصريات —
  padding/margins/ألوان/radius/ظلال/hover/transitions) مفتوحة؛ خط
  الأساس 2189P/34S/0F ALL GREEN بلا تغيير كود منذ BATCH-CEV-G1.**
- **2026-08-02 — Session 106هـ — بوابتا CEV G1 🏁 وG2 🏁 PASS — تقريران مؤرخان في MASTER_REVIEW**:
  استئناف عبر تصفيرَي بيئة (#14/#15؛ §3.1 ×2: TOKEN_SCRUB_DONE؛ عمل
  106د كله مؤكد على origin @ 3618920/5e168a2). **إقفال G1** بعد
  استكمال محوري التكرار/فصل الاهتمامات: مسح AST ×58 تصادم اسم عبر
  الملفات — الغالب تعددية أشكال مشروعة (backends/events واجهة واحدة؛
  register نمط blueprints؛ to_dict على dataclasses)؛ `_search_service`
  ازدواج مقصود موثَّق (TSK-501/NF-20/21 — كلاهما يفوّض shared_search)؛
  `_now_iso` سطران ×3 (تافه، لا يبرر اقترانًا)؛ server.py يحوي 3
  routes فقط (ADR-003 يصمد) ⇒ **تقرير G1 PASS** في MASTER_REVIEW.
  **فتح G2 وإقفالها في الجلسة نفسها**: جرد 15 وحدة UMD + 6 غراء +
  مودالان + 4 ثيمات؛ تكافؤ tokens رباعي مثالي (105 متطابقة، فرق
  مجموعات ∅)؛ RTL/LTR سليم بالتصميم (قشرة LTR كـVSCode + dir ديناميكي
  للرسائل)؛ حالات empty 6/6 لوحات + error/loading في الغراء + toast
  موحَّد؛ **فحص حي Playwright على خادم فعلي (port 5000): صفر أخطاء
  JS**، و404 وحيد = favicon.ico ⇒ CEV-F-007 (C4 تجميلي، قرار مالك)
  ⇒ **تقرير G2 PASS** في MASTER_REVIEW. **الموقع: G3 مفتوحة (تمشية
  مستخدم أول مرة — الجرد التالي).**
- **2026-08-02 — Session 106د — قرار مالك D-13 ⇒ BATCH-CEV-G1 مُقفلة 🏁 3/3 — check.sh ALL GREEN لأول مرة في CEV**:
  أمر مالك حرفي «أفتح BATCH-CEV-G1 (سقف mypy + stubs + إزالة الميت
  F-005) وأتابع بوابات CEV» ⇒ D-13 (تفسير موثَّق: الخيار 1 لم يُنفَّذ —
  providers بلا حارس None @ e6c9100 — فالأمر بالمتابعة = تفويض الخيار
  2). الخطة أُلحقت بـ DEVELOPMENT_TASKS §BATCH-CEV-G1 قبل التنفيذ
  (D-7). **الجلسة عبرت تصفيرَي بيئة (#11/#12؛ §3.1 ×2:
  TOKEN_SCRUB_DONE)**؛ البوت أنقذ 9 ملفات @ 8e4def3 لكنه التقط حالة
  ممزقة: مستدعي delegate محدَّث بلا توقيعه (TypeError كامن) + شظية
  6 أسطر تالفة بذيل delegate.py (`p()`… syntax error) — أُصلحا فور
  الجرد. **الإقفالات:** TSK-CEV-101 ✅ (requirements-dev: mypy>=1.10,<2
  + types-requests/types-PyYAML؛ ci.yml يثبّت من requirements-dev —
  مصدر حقيقة واحد)؛ TSK-CEV-102 ✅ (check.sh استثناء موسَّع
  `providers/(openai_shelby|you_com|perplexity|blackbox)\.py` بسابقة
  ADR-004 + حارس test_mypy_gate_614 محدَّث: استثناءات موثقة حصرًا،
  `--exclude` واحد، لا استثناء داخلي — CEV-F-002 مُغلق)؛ TSK-CEV-103 ✅
  (حذف الميت المؤكد F-005: executor.py ×5 استيرادات + server.py
  `queue`/`get_provider,list_providers` + delegate.py معامل
  `original_files` من التوقيع والمستدعي معًا). **البوابة النهائية:
  check.sh ALL GREEN RC=0 — 2189P/34S/0F** (mypy: 89 ملفًا Success؛
  فشلان عابران أثناء المحاولات وُثِّقا CEV-F-006: snapshot-mtime
  وsearch-perf — flaky حمل بيئي، يمران معزولين وفي التشغيلة النظيفة).
  **الموقع: G1 REVIEW تستكمل بقية محاورها (تكرار/فصل اهتمامات/تدقيق
  server.py +92 يُحال G6/G8) ثم تقرير بوابة G1 في MASTER_REVIEW.**
- **2026-08-01/02 — Session 106 — فتح برنامج CEV (قرار مالك D-12) — البوابة G1 مفتوحة؛ 5 اكتشافات + استعادة fixture**:
  تفويض مالك صريح (وثيقة CEV الكاملة + «ابدأ التدقيق») ⇒ D-12 في
  DECISION_LOG + مرجع `CEV_PROGRAM_PROMPT.md` (253 سطرًا) + إصلاح
  ترويسة PROGRESS البائتة (§0.5). الجلسة عبرت **ثلاثة تصفيرات بيئة
  (#8/#9/#10؛ طقس §3.1 كل مرة: clone → TOKEN_SCRUB_DONE → إعادة بناء)**؛
  Auto-Uploader أنقذ العمل @ ba2d9f0 وdbb7f5c. **محاولة خط الأساس:**
  check.sh **RC=1** عند mypy — 9 أخطاء ×3 ملفات
  (`providers/{you_com,perplexity,blackbox}.py:30-31` —
  module_from_spec على `ModuleSpec | None` بلا حارس). **سلسلة تفنيد
  الجذر (CEV-R4):** فرضية انجراف إصدار mypy **سقطت** بالتجربة
  (mypy 1.10.0 = نفس 9 الأخطاء) ⇒ الجذر الحقيقي = كود مالك جديد خارج
  الحوكمة @ c9ab00c (2026-08-01) — خارج نطاق الوكيل §0.8 ⇒ **حاصر
  قرار مالك** (CEV-F-002). **الاكتشافات المسجَّلة (NEW_FINDINGS §CEV):**
  F-001 (+تحديث الجذر بصدق)، F-002 (البوابة حمراء تحجز كل الإقفالات)،
  F-003 (بوت ba2d9f0 حذف fixture ‎`.env`‎ — **الإصلاح المفوَّض نُفِّذ:**
  استعادة المحتوى التاريخي من a9f52b5 حرفيًا، والاختبار الحارس
  `test_fake_provider.py::test_sample_project_fixture_isolated` يمرّ)،
  F-004 (حصر الوارد خارج الحوكمة: مزودات+pool خارج النطاق؛ **server.py
  ‎+92 @ 8dd9e8a داخل النطاق** — يُدقَّق في G6/G8؛ cont22.md توثيقي؛
  موجة ملفات الجذر زالت)، F-005 (ميت مؤكد بعد فرز vulture يدوي:
  executor.py:35 ×5 استيرادات + server.py:16 `queue` + :40
  `get_provider,list_providers` + delegate.py:660 معامل
  `original_files`؛ إيجابية كاذبة مستبعدة: router.py:27 BudgetSnapshot
  تحت TYPE_CHECKING مستخدمة ×4). **خط الأساس الحي (بتجاوز مرحلة mypy):**
  pytest كامل **2189P/34S/0F RC=0** (من 2168P الموثَّق — +21 مع وارد
  المالك؛ أُكِّد مرتين في بيئتين). أدلة G1 الجزئية: صفر دورات استيراد
  (NF-24)، FI-07 صامد (app.js=712<800 + حارس test_app_split)،
  ازدواج add_write_hook ‎:722/:2038 مبرَّر (كائنان مختلفان). **الموقع:
  G1 REVIEW مستمرة — بانتظار قرار المالك في حاصر المزودات (خيار 1:
  يصلح نمط الحارس بنفسه ×3 ملفات؛ خيار 2: يأذن بتوسيع استثناء mypy في
  check.sh بسابقة ADR-004) ⇒ بعده BATCH-CEV-G1 (سقف mypy + stubs +
  إزالة الميت F-005).**
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

### TSK-731 — auto-update مُكيَّفة: فحص تحديث يدوي opt-in (BATCH-P3/D-11) 🏁
- **التكييف (موثَّق في TASKS):** التحديث الآلي الكامل (تنزيل/استبدال exe صامت)
  يصطدم بـ IR-1 (لا phone-home) وبشكل التوزيع المعلَّق على تأشير المالك (727)،
  ويستحدث سطحًا أمنيًا جديدًا — كُيِّفت المهمة إلى **فحص تحديث يدوي opt-in
  معطَّل افتراضيًا**.
- **a:** `core/update_check.py` — parse/compare إصدارات semver-مبسّطة
  (`MAJOR.MINOR.PATCH[-rc.N]`؛ النهائي > أي rc) + `check_for_update` صامت-الفشل
  (أي فشل ⇒ None؛ url فارغة/إصدار معطوب ⇒ None **قبل أي شبكة**) + استيراد
  requests كسول (نمط T-109، مع اختبار بنيوي + subprocess معزول). 29 اختبارًا.
- **b:** `GET /api/update-check` في routes/meta.py — قسم config
  `updates: {check_enabled, manifest_url}`؛ الافتراضي معطَّل ⇒ `{enabled: false}`
  **بصفر لمس شبكة** (حارس: requests.get مُرقَّع ليرمي لا يُلمَس)؛ لا polling
  خلفي؛ manifest_url لا تُردَّد (تطهير)؛ مثال معلَّق في config.yaml (حارس
  نمط 728c)؛ توسيع خامس موثَّق للسطح المجمّد 34→35. 19 اختبارًا.
- **c:** «قناة التحديث» في docs/desktop/WINDOWS_BUILD.md — التثبيت/التحديث
  يدويان بالكامل؛ الأتمتة مؤجلة لتأشير المالك (727).
- **البوابة:** `bash scripts/check.sh` ⇒ **2168 passed / 34 skipped — ALL
  GREEN** (خط أساس جديد: 2120 + 29 + 19).
- **Commits:** bee4c07 (تفصيل) + 9bfee1c (a) + fe8f1f3 (b) + eb61bf1 (c).

### BATCH-P3 — إقفال الحزمة (D-11/S105) 🏁
- **المسار:** TSK-728 (خطّافات المالك CP-4) 🏁 → TSK-729 (تصليب seam
  redis) 🏁 → TSK-730 (توسيع الإضافات) 🏁 → TSK-731 (فحص التحديث اليدوي —
  مُكيَّفة) 🏁.
- **الحصيلة:** من خط أساس 2058P/34S (قبل 728) إلى **2168P/34S** — +110
  اختبارات عبر الحزمة؛ كل مهمة أُقفلت ببوابة ALL GREEN مستقلة.
- **معلَّق خارجي (غير حاجز):** تأشير المالك على OWNER_CHECKLIST (727)
  يقفل P2 رسميًا ويفتح أي أتمتة تحديث مستقبلية.

### EOP-1 — حذف docs/engineering_constitution/ (قرار D-8-أ) 🏁
- **المُشغِّل:** أمر مالك صريح («نفذ ده EOP-1») — 2026-07-31.
- **التحقق قبل الحذف:** صفر مراجع في الكود/الاختبارات/السكربتات
  (grep على *.py/*.sh/*.yaml/*.js + tests/ + scripts/ = لا شيء)؛
  مراجع الوثائق الهندسية تاريخية (سجلات append-only) وتبقى كما هي.
- **المحذوف:** 13 ملف MD (AGENT_CONSTITUTION..UX_PRINCIPLES) — كانت
  HISTORICAL-INERT منذ D-8-أ؛ V3 (docs/engineering/CONSTITUTION_V3.md)
  هو الدستور الحاكم الوحيد ولا يتأثر.
- **البوابة بعد الحذف:** check.sh ALL GREEN (الحذف وثائقي بحت).

---
- **[مؤشر أرشيف — تدوير §6.4 (2026-08-02, S106/CEV + دفعة ثانية S106هـ)]** قيود Sessions
  84–103 رُحِّلت (ثلاث دفعات؛ الثالثة S106ح: مدخلات S102–S103 المؤرخة) إلى `docs/engineering/PROGRESS_ARCHIVE_2.md`
  (append-only، لا يُعدَّل).
- **[مؤشر أرشيف]** كل ما قبل S84 (بما فيه برنامج v4.1 Sessions 1–23):
  انظر `docs/engineering/PROGRESS_ARCHIVE_1.md` (append-only، لا يُعدَّل).
