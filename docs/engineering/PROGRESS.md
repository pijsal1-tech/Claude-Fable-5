# PROGRESS.md — editor_v4 Engineering Program (CORE-ONLY SCOPE v4.1)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.
> النطاق محكوم بـ SECTION 0.8: النظام الأساسي فقط — Provider Layer خارج النطاق كليًا.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-08-04 (Session 109 **تكملة 15** — **برنامج CEV مُغلق: إقرار CEV-R12 صادر وG12 🏁 PASS**. بإذن المالك D-17 (المسار «أ») نُفِّذت **TSK-CEV-117**: CEV-F-018 (C1/S2) **أُغلقت** بتطبيع مركزي في `chain/path_policy.py` (محارف خفية + قصّ NTFS ADS + تقليم بالتناوب حتى نقطة الثبات) + **290 اختبار انحدار لكل فئة** (`tests/unit/test_path_policy_secret_normalization.py`، 7 فئات) + **تحقُّق طَفَري** يُثبت أن الحزمة تكتشف العودة + **صفر نطاق أثر** على 692 ملفًا. **تصحيحات ذاتية ضد المصلحة (CEV-R3)**: سُحب ادعاء «تسريب فعلي على POSIX» المُبالَغ في تقرير G7، وصُحِّح خطأ «`.env.` مكشوف» (كان محجوبًا سلفًا)، واكتُشف ناقل جديد **NTFS ADS** (`.env::$DATA`) + ZWSP/BOM، و**رُفعت** شدة CEV-F-006 من S4 إلى S3 بدليل A/B (خط الأساس يفشل 3/3 مقابل 2/3 مع الإصلاح ⇒ الرجفة بيئية سابقة لا انحدار — بلا رفع عتبة ولا xfail ولا حذف اختبار). **تدقيق S1/S2**: صفر S1 في تاريخ المشروع وكل S2 التاريخية مُغلقة بدليل حي (منها تحقُّق حي لـF-012: صفر إرث AI_PROVIDERS في `prompts/`) ⇒ حاجب §6 انفكّ. **البطاقة كاملة: 90/90 (محاور 1–9) + 9/10 (المحور 10) = 99/100 ≥ 95** ⇒ **RRR النهائي: GO** ضمن عقد localhost أحادي المستخدم حصرًا (NO-GO لأي تعريض شبكي). الانحدار الختامي: **2576P/0F/34S — ALL GREEN rc=0** (91.80s). كوميت محلي فقط — لا push/branch/tag/PR) |
| stage | **V3-STAGE 4 → برنامج CEV مفتوح (D-12)** — سوابق مُقفلة كلها 🏁: BATCH-P0 6/6 (v1.0.0-rc.1) + BATCH-FI01 5/5 + BATCH-SHORT 5/5 + D-6 5/5 + BATCH-P1 6/6 (D-9) + BATCH-P2 5/5 (D-10) + BATCH-P3 4/4 (D-11) + EOP-1 |
| current-phase | **CEV (D-12 → D-17) — 🏁 مُكتمل ومُغلق**: G1→G6 + G8 + G8.5 + G9 + G10 + G11 🏁 PASS؛ **G7 ⚠️ COMPLETED-WITH-FINDING** (الاكتشاف أُغلق بـTSK-CEV-117)؛ **G12 🏁 PASS** — البطاقة 99/100 + إقرار CEV-R12 صادر (`RELEASE_READINESS_REPORT.md`). صفر S1/S2 مفتوحة |
| current-task | **لا مهمة تنفيذية مفتوحة — كل مُخرَجات D-17 الأربعة سُلِّمت**: (1) TSK-CEV-117 ✅ إصلاح F-018 + انحدار لكل فئة؛ (2) المحور 10 ✅ **9/10** (الخصم مُبرَّر: دفاع من ستة انكسر فعليًا ولم تغطّه الحُرّاس قبل G7؛ الكمال مرفوض بـCEV-R3)؛ (3) العتبة ✅ **99/100 ≥ 95** + RRR النهائي **GO**؛ (4) ✅ إقرار CEV-R12 وإغلاق G12. **قيود مالك مفتوحة غير حاجبة** (لم تُنفَّذ ذاتيًّا التزامًا بقيد «فقط»): تقسية عقد أداء `test_search_perf` (CEV-F-006 S3، `tests/integration/test_search_perf.py:250`) · توسيع معجم التعقيد (CEV-F-017 S4، `chain/orchestrator.py:110-121` — النمط مُقترح ومُتحقَّق منه) · FI-17 وبقية بنود FI · **EOP-1** (حذف `docs/engineering_constitution/` قبل الوسم النهائي — D-8-أ) · تدوير سجل PROGRESS §6.4 |
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
- Stage: **CEV (D-12/D-16) — G1→G6 + G8 + G8.5 + G9 + G10 + G11 كلها 🏁 PASS؛ G7 (Red Team) ⚠️ COMPLETED-WITH-FINDING (S109 تكملة 14 — نُفِّذت بمحاورها الأربعة، 44 مجسًّا)؛ G12 ⚙️ PARTIAL (المحور 10 محجوب)** — الاكتشافات → NEW_FINDINGS (المفتوحة الحاجبة: **CEV-F-018 C1/S2** — تجاوز حجب الأسرار بمِحارف بيضاء لاحقة؛ غير حاجبة: F-017 S4 موسَّعة، F-006/F-007/F-008/F-009 لا فعل الآن)؛ سوابق مُقفلة كلها: P0→P3 🏁 + EOP-1 🏁
- [أرشيف — صُحِّح S109 تكملة 14] كان يُقرأ: «G7 مؤجلة DEFERRED (D-14)؛ المفتوحة: G8.5 (AIA)» — تقادُم توثيقي (D-16 نقلت G7 من DEFERRED إلى آخر مرحلة، وG8.5 أُغلقت 🏁)، لا ادعاء كاذب.
- خط أساس البرنامج (أُعيد تثبيته حيًّا S109 تكملة 14 @ 65e4f30، بعد تحرير التوثيق): **2286P/0F/34S — ALL GREEN rc=0** (تشغيلان متتاليان مطابقان، 89.79s). ملاحظة: التشغيل الأول في هذه التكملة (قبل الهجوم) أظهر 2285P/1F/34S بفشل `test_no_save_churn_when_list_unchanged` = الرجفة البيئية الموثَّقة **CEV-F-006** (فرق mtime_ns تحت حمل الحزمة على tmpfs) ولم تتكرر في التشغيلين الختاميين ⇒ تأكيد إضافي لتصنيفها رجفة بيئية لا انحدارًا
- [أرشيف] خط أساس (S106ي @ 5e77751): **2189P/34S/0F** + check.sh ALL GREEN rc=0
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
- **2026-08-03 — Session 109 (تكملة 14) — تنفيذ G7 (Red Team) بمحاورها الأربعة + كتابة جسم التقرير ⇒ ⚠️ COMPLETED-WITH-FINDING**:
  (Wipe #63 ثم Wipe #64 خلال الجلسة — البوت التقط كل عمل المحاور في
  `65e4f30` (MASTER_REVIEW +123، NEW_FINDINGS +59) قبل المسح الثاني ⇒
  **صفر عمل ضائع**؛ استرجاع V3 §3.1: clone → تعقيم remote فورًا →
  هوية git → تحقق HEAD؛ TOKEN_SCRUB_DONE؛ fixture `.env` لم يُحتَج
  استعادته — صار مُولَّدًا وقت الاختبار منذ TSK-CEV-111؛ SETUP_DONE.)
  **تفويض المالك لهذه التكملة (حصري)**: «إكمال محاور G7 المتبقية +
  كتابة جسم التقرير **فقط**» — التزمتُ حرفيًا بـ«فقط»: لم أُنفِّذ
  إكمال G12، ولا المحور 10، ولا إقرار CEV-R12، ولا FI-17، ولا إصلاح
  F-018، ولا تدوير §6.4 — كلها بقيت خارج النطاق بلا مساس.
  **الطبيعة**: جولة **قراءة-فقط** بموجب §6+§7 — **صفر تغيير في كود
  الإنتاج** (المتغيّر: 3 ملفات توثيق فقط). سكربتات الهجوم كُتبت خارج
  الشجرة عمدًا (`/tmp/g7/*.py`) لئلا تنمو الشجرة أو تتأثر البوابات.
  **خط الأساس قبل الهجوم** (تحقق حي @ 78a185c): 2285P/1F/34S = 2286 —
  الفشل الوحيد رجفة CEV-F-006 البيئية (منفردًا 10 passed).
  **المحور 1 — مهاجمة الاكتشافات المغلقة (عينة 5) والدفاعات القائمة**:
  (أ) Zip-Slip (`server.py:828 _zip_member_violations`) — **صامد 12/12**؛
  (ب) احتواء المسارات (`resolve_workspace_path`) — **صامد 11/11**، وescape
  عبر symlink محجوب حتى مع `allow_symlinks=True`؛ (ج) بوابة الموافقة
  (`core/approval.py:152/199`) — **صامدة 9/9** بما فيها رفض تلاعب
  `payload_hash` و fail-closed عند استثناء `interactive_override`؛
  (د) **حجب الأسرار — ⚠️ مكسور** ⇒ **CEV-F-018 (C1/S2)**: `is_secret_file`
  (`chain/path_policy.py:28`) يقارن `path.name.lower()` بلا تطبيع، فـ
  `read('.env ')` (مسافة لاحقة) **سرّب المحتوى فعليًا** عبر أداة الوكيل
  الإنتاجية `tool_read_file`؛ نطاق الانفجار يغطي الفئات الثلاث
  (`SECRETS_DENYLIST_NAMES` / `_EXTENSIONS` / فرع `.env`)؛ يتفاقم على
  Windows (NTFS يقلّم المسافات اللاحقة ⇒ `.env ` **هو** `.env`) والمشروع
  يشحن Windows-first (TSK-727). خرق مباشر للأصل المحمي #2 و§3.2 من
  نموذج التهديد. **الإصلاح لم يُنفَّذ — خارج تفويض «قراءة-فقط»**.
  **المحور 2 — البرومبتات (حقن على مستوى stub)**: سياج الحقن
  (`prompts/templates.py:48 fence_attached` / `:60 guarded_system`) —
  **صامد 12/12**: كل وسوم الإغلاق المُزيَّفة عُطِّلت إلى
  `</attached\u200bcontent>`؛ لا-تكرارية `guarded_system` سُجِّلت
  **إعلاميًا فقط** (لا شدة — الاستدعاء أحادي في كل المواقع الأربعة).
  **المحور 3 — التوجيه (3 طلبات خبيثة الغموض)**: CEV-F-017 **أُعيد
  إنتاجها وتوسَّع نطاقها** (`chain/orchestrator.py:110-121`): `يعيد كتابة`
  و`نعيد تصميم` لا يُلتقطان أيضًا (نمط موسَّع مُقترح ومُتحقَّق منه في
  NEW_FINDINGS) — S4 لا يحجب؛ المجسّان الآخران («أصلحه»، تنظيف مبهم)
  ذهبا إلى `direct` = سلوك **مقبول** لا خلل.
  **المحور 4 — تحقق عيّني من ادعاءات PROGRESS ضد الكود**: **4/4 دقيقة
  تمامًا** (REST 35 قاعدة @ `tests/unit/test_rest_blueprints.py:83`؛
  17 اختبار `delegate_queue`؛ `guarded_system` عند 4 مواقع نداء؛ حارس
  الحقن 21/21) ⇒ **صفر ادعاء مُبالَغ في سجل الحالة**.
  **نزاهة (V3 append-only)**: ترويسة مقطع G7 في MASTER_REVIEW كانت
  كُتبت في تكملة 13 بوسم «🏁 PASS» **قبل** التنفيذ (المسح قطع الكتابة
  فبقيت 5 أسطر بلا جسم) — **صُحِّحت إلى ⚠️ COMPLETED-WITH-FINDING** مع
  تدوين التصحيح صراحةً، لأن §6 يمنع PASS مع S2 مفتوحة. كذلك سطر 44
  المتقادم («G7 مؤجلة DEFERRED (D-14)») صُحِّح هنا — تقادُم توثيقي لا
  ادعاء كاذب، والنص الأصلي حُفظ كأرشيف.
  **الحصيلة**: 44 مجسًّا (12 ZIP + 11 احتواء + 2 symlink + 9 موافقة +
  12 سياج) + 3 توجيه + 4 تحقق ادعاءات. تجنُّب إيجابيات زائفة بموجب
  CEV-R3: `．．/evil` (homoglyph) و`%2e%2e%2f` بدتا تجاوزًا ثم ثبت أنهما
  تُحلّان **داخل** الجذر ⇒ سلبيات صحيحة، لم تُقيَّد كثغرات.
  **الأثر على البطاقة**: **المحور 10 لا يُمنح درجة، وحسم المجموع ≥95
  وإقرار CEV-R12 يبقيان محجوبين — الآن بـF-018 بدل «تأجيل G7»**.
  **قيد قرار مالك (§7)**: إما (أ) إذن بدورة TSK لإصلاح F-018 ثم إعادة
  تقييم المحور 10، أو (ب) إعادة تصنيف الشدة بقرار موثَّق. **لم يُتخذ
  أيٌّ منهما ذاتيًا.**
  **الانحدار الختامي بعد التحرير**: **2286 passed / 0 failed / 34 skipped
  — ALL GREEN rc=0** (تشغيلان متتاليان مطابقان، 89.79s) ⇒ **صفر انحدار**
  (التغييرات توثيقية بحتة). تصحيح مقابل التشغيل الأول (2285P/1F): رجفة
  CEV-F-006 لم تتكرر ختامًا — يؤكد بيئيّتها. **كوميت محلي فقط — لا push
  ولا tag ولا PR** (محظور دون أمر مالك صريح، §7 + D-16-د).
- **2026-08-03 — Session 109 (تكملة 13) — قرار مالك D-16 مستلَم وموثَّق + بدء تنفيذ الطابور المعلّق**:
  (Wipe #52: البوت التقط كل عمل تكملة 12 في 3315e62 — صفر عمل ضائع؛
  TOKEN_SCRUB_DONE؛ fixture .env أُعيد ×35؛ SETUP_DONE.)
  نص المالك: «ابدأ القرارات المعلقه بالترتيب واجعل red tem اخر مرحله
  تماما بعد إغلاق جميع المراحل الاخري» — قُيِّد **D-16** في DECISION_LOG
  بالتفسير الملزم الكامل: (أ) تفويض تنفيذي للطابور بترتيب تقرير تكملة 12:
  F-003 → F-010 → F-014 → STALE-175 → FI-13 → FI-14 → FI-15 → FI-16 →
  توحيد حارس NF-18 في system السلاسل؛ (ب) G7 (Red Team) تنتقل من DEFERRED
  إلى **آخر مرحلة مطلقًا** — تُنفَّذ وفق §6 (cont22.md:394-401) بعد إغلاق
  كل البنود؛ (ج) بعد G7: إكمال G12 (المحور 10 → حسم ≥95 → التصويت النهائي
  → إقرار CEV-R12)؛ (د) يبقى محظورًا: push/tag/PR + providers/ + الدستور.
  حالة الانطلاق: HEAD محلي = origin = 3315e62؛ الشجرة نظيفة عدا .env
  غير المتتبَّع (بند F-003 نفسه). بدء البند 1 فورًا.
  **تنفيذ البنود 1–4 (هذه التكملة، عبر Wipes #53–#55 — البوت التقط كل
  شيء: 2d0c45e، 4296f12، صفر عمل ضائع)**: (1) F-003 ✅ TSK-CEV-111 —
  `.env` يُولَّد وقت الاختبار (SAMPLE_ENV_BODY + write_sample_env في
  conftest، يستورده المجمّعان وreplay)؛ استثناء .gitignore أُزيل؛ صفر
  ملف يحذفه البوت بعد الآن. (2) F-010 ✅ — `git rm chain/hh.har`
  (218,007 سطرًا؛ إعادة تحقق: صفر مراجع/أسرار). (3) F-014 ✅ — الأدوار
  الـ15 مُسندة **أدوار مكتبة** (load(role) API)؛ TestLibraryRolesF014
  (تجزئة 15+6=21 + تحميل فعلي + حارس strategies.py)؛ المصفوفة R9
  = 21/21؛ تعليق توثيقي لـmax_iterations=6. (4) STALE-175 ✅ —
  175 ملفًا نُقلت git mv إلى agents_rules/_archive/ (مسار الحارس
  المعتمد)؛ baseline نُظِّف (26 قيدًا باقيًا)؛ الحارس أخضر. كل بند
  أُقفل ببوابة check.sh ALL GREEN (أحدثها 2248P/34S/0F) وحسم موثق
  في NEW_FINDINGS. flakes توقيتية أحادية عابرة موثقة بنزاهة.
  **تنفيذ البندين 5–6 (عبر Wipes #56–#57 — البوت التقط كل شيء:
  5066e56، b9f0f8b؛ صفر عمل ضائع)**: (5) FI-13 ✅ TSK-CEV-112 —
  وحدة جديدة `chain/delegate_queue.py` (DelegateQueue/QueuedTask)
  فوق DelegateBridge **بلا أي تعديل عليه** (مثبَّت باختبار مصدر):
  تتابع صارم (لا إرسال قبل land السابقة — بعدّ نداءات المزود)؛
  بوابة الموافقة سيدة؛ رفض/فشل/إلغاء = halt (stop-and-ask)؛
  ترحيل القيود `[قيود مقررة من مهام سابقة]` للبريف التالي؛ أحداث
  WS كاملة؛ 17 اختبارًا حتميًا (P-11). (6) FI-14 ✅ TSK-CEV-114
  (الرقم 113 محجوز لـFI-15 — قرار ترقيم واعٍ) — قسم «🧪 افحص
  الاختبارات قبل أن تثق بالبوابات» في delegate_review.md: تعديل
  غير مُكلَّف به على اختبارات قائمة / إضافة skip-تعطيل / تليين
  تأكيدات = **تغيير عقد ⇒ REWORK أو REJECT، لا يُمتص صامتًا**
  (review-and-land.md:8-19)؛ اختبار تسييج (3 اختبارات) عبر مسار
  الإنتاج `_load_prompt` يحمي المعايير + سطر `[VERDICT]:` حرفيًا؛
  فحص مُسبق أثبت صفر تثبيت بايتي للـprompt في goldens/حراس ⇒ صفر
  إعادة التقاط. البوابة: check.sh ALL GREEN rc=0 (2268P/34S/0F).
  **تنفيذ البند 7 (عبر Wipes #58–#59 — البوت التقط كل شيء: 7b8d0ba
  المواصفة، b1bd5ff الوحدة+الاختبارات؛ صفر عمل ضائع)**: (7) FI-15 ✅
  TSK-CEV-113 — وحدة جديدة `chain/background_delegate.py`
  (BackgroundDelegateTask) فوق DelegateBridge بلا مساس به ولا
  بـdelegate_queue.py (مثبَّت باختبار مصدر): hand-off (start يرجع
  فورًا، الدورة في خيط daemon بكل نقاط تفتيش T-015)؛ **الثابت
  الصلب لا-YOLO**: صفر land تلقائي — waiting_approval نهائية حتى
  land()/reject() صريحين؛ snapshot() آمن لإعادة الاتصال (الحالة +
  سجل الأحداث كاملين من الكائن الحي تحت قفل، نسخ دفاعية)؛ فشل
  المزود = failed بلا استثناء هارب؛ 12 اختبارًا حتميًا (تزامن
  بـthreading.Event). البوابة: check.sh ALL GREEN (2280P/34S/0F).
  **تنفيذ البند 8 (عبر Wipe #60 — البوت التقط كل شيء: 2f2dcdd؛
  صفر عمل ضائع)**: (8) FI-16 ✅ TSK-CEV-115 — قسم «حلقة الأدلة
  التشغيلية» في برومبت deep_debugger (تشغيل الاختبار الفاشل وحده +
  قراءة مخرجات الخطأ الفعلية + تتبّع مؤقت يُزال + تنزيل الثقة عند
  تعذر الدليل — كله عبر SAFE+ApprovalGate، صفر قدرات جديدة، DAP
  مرفوض)؛ قاعدة «بيانات لا أوامر» باقية (حارس الحقن 21/21 أخضر)؛
  إعادة التقاط corpus واعية بتصنيف برمجي: خطوة واحدة متغيرة
  (pl_scout/deep_debugger sha+len فقط، صفر تغيير توجيه) = تحسين
  مقصود؛ سيناريو crash_investigation_pipeline جديد (10 سيناريوهات/
  28 خطوة). البوابة: check.sh ALL GREEN (2281P/34S/0F).
  **تنفيذ البند 9 — الأخير (عبر Wipes #61–#62 — البوت التقط كل
  شيء: 4623344 توثيق FI-16، 22aa68c المواصفة+التوصيل+إعادة
  الالتقاط؛ صفر عمل ضائع)**: (9) توحيد NF-18 ✅ TSK-CEV-116 —
  `guarded_system(content)` في templates.py (نفس فاصل
  SYSTEM_PROMPT) مُوصَّلة عند 4 مواقع نداء (executor._call_provider
  + delegate الثلاثة planner/executor/code_reviewer — التعديل
  مأذون ببند المالك؛ نقطة الحقن عند التركيب لا AgentLoader كي
  يبقى content نقيًّا)؛ ترقية check_injection_guard (فحص سلوكي +
  مواقع النداء + docstring يغلق الحد الموثق؛ «بيانات لا أوامر»
  باقية 21/21)؛ harness يقيس النص المركّب؛ إعادة التقاط واعية:
  28/28 خطوة بدلتا موحدة 362B (فاصل+حارس) وصفر تغيير
  user_prompt/توجيه ⇒ تحسين مقصود؛ 5 اختبارات سياج
  (test_injection_guard_unification). البوابة: check.sh ALL GREEN
  (2286P/34S/0F؛ flake توقيتي أحادي عابر موثق). **طابور D-16
  مُقفل 9/9 — الانتقال إلى G7 (آخر مرحلة مطلقًا)**.
- **2026-08-02 — Session 108 (تكملة 12) — CEV-G12 ⚙️ PARTIAL/CONDITIONAL + استنفاد خطة D-15 بالكامل**:
  (Wipe #51: البوت التقط كل عمل TSK-CEV-110 وتكملة 11 في ddd84b4 —
  صفر عمل ضائع؛ TOKEN_SCRUB_DONE؛ fixture .env أُعيد ×34... راجع
  لاحقًا ×35 إن مُسحت البيئة مجددًا). **سند فتح G12 جزئيًا**: D-15
  حدّث قيد D-14 («لا تُفتح قبل G7») صراحة — scorecards/reports/
  release preparation مأمور بها. **المنفَّذ**: (1) تشغيلة بوابة
  طازجة على الشجرة الحالية: check.sh ALL GREEN rc=0 (2231P/34S/0F،
  86.48s، 17 قسمًا مسمى)؛ (2) **Scorecard §5 كمقطع CEV في
  RELEASE_READINESS_REPORT.md (per D-12)**: محاور 1–9 كلها 10/10 =
  **90/90 موضوعيًا** — كل درجة بمثبت آلي أو دليل file:line (mypy
  --check-untyped-defs بوابة؛ حارس حقن 4 طبقات؛ REST مجمَّد 35
  بمثبت test_rest_blueprints.py:83 الحي؛ FI-01..16 مُسعَّرة؛
  استئناف معاش ×51 مسحًا؛ desktop.spec يُفسَّر ast.parse؛ AIA-C
  كاملة)؛ المحور 10 **DEFERRED BY OWNER (D-15)** بلا درجة (دليله
  النصي «§6 بلا S1/S2 مفتوحة» = نتيجة G7 ذاتها — تقييمه بدونها
  اختلاق)؛ (3) **إعادة تصويت RRR مشروطة**: GO-conditional (الشرط
  المعلَّق الوحيد G7؛ الأدلة كلها تحسّنت منذ S83: 1900→2231
  اختبارًا + 5 حراس + تسييج NF-18 مكتمل المسارات) + Fully supported
  لعقد localhost؛ **إقرار CEV-R12 لا يُصدَر** (يوثّق اكتمال G1..G12
  نصًا — البرنامج 11/12)؛ (4) تقرير **CEV-G12 PARTIAL/CONDITIONAL**
  في MASTER_REVIEW (الثاني عشر المؤرخ) بمنهجية أمانة صريحة: صفر
  نشاط هجومي (D-15-ج)، صفر درجة تقديرية. **قائمة المحجوب حصرًا
  بـG7 (مطلب D-15-د — رسمية في RRR)**: المحور 10؛ حسم المجموع ≥95
  (المدى بعد G7: 90–100)؛ ترقية GO-conditional لقرار نهائي؛ إقرار
  CEV-R12. **المحجوب بقرارات مالك أخرى (خارج D-15)**: F-003 (fixture
  .env ×34)؛ F-010 (hh.har)؛ F-014 (15 دورًا بلا توجيه)؛ STALE-175؛
  FI-13..FI-16 (تنفيذ حصري للمالك)؛ توحيد حارس NF-18 في system
  السلاسل (يغيّر 21 لقطة sha256). **الحالة: توقف مشروع — كل شرطي
  التوقف في D-15 تحققا** («Every non-Red-Team task has been
  completed»).
- **2026-08-02 — Session 108 (تكملة 11) — TSK-CEV-110 ✅ مقفلة: التسييج الدفاعي لمسار السلاسل (CEV-F-013 محسومة بحدّ موثق)**:
  (Wipes #49/#50: البوت التقط كل شيء — bc8f842 شمل حتى تعديل 110a
  غير الملتزم + تكملة 10 + المواصفة؛ صفر عمل ضائع؛ TOKEN_SCRUB_DONE
  ×2؛ fixture .env أُعيد ×33/×34). **بموجب D-15 — هندسة دفاعية لا
  Red Team**: 110a سيّجت نتائج التبعيات (`fence_attached("dep_result:
  {id}", body)` في ChainStep.build_prompt — العنوان خارج السياج)؛
  110b سيّجت محتوى سياق الملفات (ContextItem.to_prompt_block — نفس
  آلية knowledge.py)؛ 110c حدّثت المثبتات وعيًا (AIA-R8): goldens
  test_context_policy الحرفية معادة الصوغ (اختبار التكافؤ البايتي مع
  legacy صار يقارن مع legacy مسيَّج — التكافؤ المثبَّت: نفس السلوك
  عبر السياسات لا بايتات ما قبل NF-18) + إعادة التقاط
  prompt_corpus.golden.json (8 مواضع) وgoldens السلاسل (4 ملفات)
  بتصنيف diff **برمجي صارم**: نزع أغلفة السياج يعيد القديم
  بايت-ببايت في الملفات الخمسة (FENCE_ONLY_VERIFIED) — تحسين مقصود،
  صفر حذف/تغيير توجيه؛ dedup ≥40% (map_reduce) صمد بلا تعديل +
  حارس الحقن اكتسب طبقة رابعة سلوكية (probe عدائي حي عبر الدالتين
  يجب أن يخرج محصورًا بين وسمي attached-content) — كسر متعمد لأيٍّ
  من التسييجين = أحمر باسم صريح (جُرّب فعليًا واستُعيد)؛ قاعدة
  «بيانات لا أوامر» 21/21 صارت ترتبط فعليًا بمحتوى مسيَّج. check.sh
  **ALL GREEN rc=0 (2231P/34S، 98.51s)**. F-013 مُقفلة في
  NEW_FINDINGS بحدّ موثق: إلحاق INJECTION_GUARD_INSTRUCTION بـsystem
  السلاسل يغيّر 21 لقطة sha256 = قرار مالك منفصل (الضابط التعويضي
  يغطي وظيفيًا). التالي: G12 جزئية (Scorecard §5 محاور 1–9 +
  المحور 10 DEFERRED) ثم قائمة المحجوب حصرًا بـG7.
- **2026-08-02 — Session 108 (تكملة 10) — قرار مالك D-15 (تأجيل G7 غير حاصر) + TSK-CEV-104 ✅ مقفلة (فجوة المعجم F-015 مسدودة)**:
  (Wipes #47/#48/#49 عبر هذه التكملة: البوت التقط كل الملتزم —
  7285915 = 104a+D-15، 2f1b790 = 104b+تحديث اختباري الغموض+حسم F-015؛
  الخسارة الوحيدة كانت 104b غير الملتزمة في #48 وأُعيدت فورًا —
  الالتزام المبكر أثبت جدواه مجددًا؛ TOKEN_SCRUB_DONE ×3؛ fixture
  .env أُعيد ×31/×32/×33). **D-15 (مسجل DECISION_LOG)**: المالك يؤكد
  تأجيل G7 مقصود وغير حاصر — «Continue executing every remaining CEV
  activity that does not depend on Red Team»؛ التفسير الملزم: (أ) G7
  = DEFERRED BY OWNER، (ب) تنفيذ كل ما هو موضوعي بلا G7 (مهام جاهزة
  + F-013 دفاعيًا + G12 جزئيًا: محاور 1–9 والمحور 10 DEFERRED)، (ج)
  صفر اختبار هجومي، (د) الناتج النهائي يعدّد المحجوب حصرًا بـG7.
  **TSK-CEV-104 ✅**: 104a وسّعت `_COMPLEX_REQUEST_PATTERNS` (فعل
  الأمر «أعد/أعيدي… هيكلة/كتابة/تصميم» + «ريفاكتور») و
  `_HIGH_RISK_PATTERNS` («تسجيل الدخول»، «كلمة السر/المرور») في
  chain/orchestrator.py؛ 104b عكست `TestLexiconGapF015` (auto_chain
  → full_chain + matched_signals) — خضراوان. أثر جانبي متوقع
  ومفحوص: اختبارا `TestIntentAmbiguousMultiIntent` كانا يثبّتان
  الفجوة ذاتها («تسجيل الدخول» = 0 إشارات) فحُدّثا (+0.5 إشارة خطر
  موثقة، **الاستراتيجيتان لم تتغيرا**: direct/delegate ثابتتان).
  **الحارس التنظيمي سليم**: corpus T-034 أخضر بصفر تعديل goldens
  (`git status --porcelain tests/goldens/` فارغ — لا سيناريو قديم
  تغيّرت درجته، فلا حاجة لقرار مالك بموجب حارس المهمة)؛ check.sh
  **ALL GREEN rc=0 (2231P/34S، 92.76s، بلا أي flake هذه المرة)**.
  F-015 مُقفلة بقيد حسم في NEW_FINDINGS (صفوف 5a/7a/7b في
  AIA_ROUTING_MATRIX صارت تاريخية). التالي: F-013 (TSK-CEV-110 —
  تسييج نتائج التبعيات models.py:307 + حارس NF-18 لمسار السلاسل،
  الحد الموثق في 109b) ثم G12 جزئية.
- **2026-08-02 — Session 108 (تكملة 9) — CEV-G11 🏁 PASS: بوابة الدين التقني — صفر دين خفي + الادعاء يصمد**:
  (بعد Wipe #46: البوت التقط كل عمل G10 حتى 4b9f1d6 — صفر عمل ضائع؛
  TOKEN_SCRUB_DONE؛ fixture .env أُعيد ×30). المسح: grep حساس-الكلمة
  على كل الكود التشغيلي + tests + scripts بالوسوم الستة المطلوبة
  (TODO/FIXME/HACK/temporary/deprecated/placeholder) + توسعة طوعية
  (XXX/TBD/WIP/workaround/kludge/BLOCKED + «مؤقت» العربي) = **صفر دين
  خفي** — كل الإصابات مصنفة (مكتبة موردة vendor/ + بيانات اختبار +
  سمات HTML placeholder مشروعة + مُجانس «مؤقت»=timer في app.js:30).
  **الاكتشاف الوحيد**: مرجعان توثيقيان بائتان (core/ws_router.py:9 +
  server.py:1841 يَعِدان بنقل مقابض _ws_* «موضوع QG-02..04» بينما
  TSK-612..614 ✅ DONE بنطاق آخر) — أُصلحا بتصويب المرجع إلى FI-02
  (backlog مُسعَّر قائم) — تعليقات فقط، صفر سلوك (commit db3f8ae).
  **إعادة التحقق من «صفر دين» @03c7eab**: يصمد — صفر TODO/BLOCKED
  قائم حرفيًا + غياب TECHNICAL_DEBT.md ما زال معلَّلًا (P-13) لأن كل
  شبيه-دين مُدار في سجل معلَن (FI-01..16 / F-013..015 / D-14)؛
  الصياغة الأصدق: «صفر دين غير مُدار». تدقيق تكميلي: 7 pragma no
  cover كلها معلَّلة نصًا. **بوابة الانحدار على الإصلاح**: check.sh
  ALL GREEN rc=0 (2231P/34S/0F، 17 قسمًا)؛ التشغيلة الأولى الباردة
  أسقطت بنشًا توقيتيًا واحدًا (session_store ≤3× قاس 3.17×) يمر
  معزولًا — وُثِّق كعضو ثالث في فئة CEV-F-006 (append-only) بنفس
  العقد. تقرير CEV-G11 في MASTER_REVIEW (حادي عشر — f2c355e).
  **الحكم: G11 PASS — تسلسل أمر التتابع D-14 استُنفد**: المتبقي في
  CEV حصرًا G7 (مؤجلة بقرار مالك، تسبق G12 وجوبًا) ثم G12 (Scorecard
  §5 + RRR). توقف بانتظار توجيه المالك.
- **2026-08-02 — Session 108 (تكملة 8) — CEV-G10 🏁 PASS: بوابة المنافسين — جدول مقارنة بالدليل للمنصات الخمس + FI-15/FI-16**:
  (بعد Wipe #45: استنساخ نظيف — البوت التقط كل شيء حتى 0a24d1b، صفر
  عمل ضائع؛ TOKEN_SCRUB_DONE؛ fixture .env أُعيد ×29 — F-003 بانتظار
  قرار مالك). المنهجية: المقارنة السابقة R0.2 (CP-1..9، فُحصت
  2026-07-28) + أحكام R9.1 استُهلكتا بالإحالة لا بالتكرار — أُعيد
  التحقق أن الواقع لم ينقلب (RP-01 مُصلَح TSK-601؛ بطاقة الخطة لا
  تزال قراءة-فقط). فجوتا المواصفة (VSCode/JetBrains) غُطيتا بأدلة
  رسمية جديدة (فُحصت 2026-08-02): 8 صفوف CP-10..17 في تقرير CEV-G10
  (MASTER_REVIEW، عاشر تقرير). النتائج: CP-10 أوضاع chat/agent/chain
  = ALREADY-HAVE (`core/chat_dispatch.py:496,609`)؛ CP-14 plan-first
  مُستهلَك سلفًا في CP-1 (تأكيد خارجي ثانٍ)؛ CP-17 جوهره عندنا في
  بوابة delegate review. **المستحق ⇒ بندا FI بكلفة/عائد (قرار
  التنفيذ للمالك — ليس لي)**: FI-15 مهمة مفوَّضة بالخلفية governed
  [MID، من CP-11، شرط صلب: كل كتابة خلف ApprovalGate + يسبقه قرار
  FI-13] وFI-16 حلقة أدلة تشغيلية لدور deep_debugger [SHORT، من
  CP-16، بلا تكامل DAP]. **غير المستحق موثَّق لماذا (G10.4)**:
  CP-12 لوحة جلسات (تفترض multi-session لا نملكه)؛ CP-13/CP-15
  ACP/وكلاء خارجيون (يمس طبقة providers المستثناة SECTION 0.8
  ويكسر governed-fleet — رهان مراقبة بقرار مالك يعدّل النطاق، ليس
  FI)؛ CP-16 تكامل DAP كامل (وزن غير متناسب)؛ CP-17 تدفق PR
  (cloud-pivot، Non-Goal §15.2). الخلاصة: R0.2 تصمد بعد توسيع
  العينة — لا انعطاف معماري؛ كل الجدير Extend والمرفوض يرفضه مبدأ
  معلن لا ذوق. **الحكم: G10 PASS — التالي بالترتيب المعدل (D-14):
  G11 (الدين التقني)**. (commit 9dd890f: التقرير + FI-15/FI-16)
- **2026-08-02 — Session 108 (تكملة 7) — CEV-G9 🏁 PASS: بوابة الانحدار — ALL GREEN حي 2231P/34S/0F rc=0 + goldens مطابقة بتية + خط الأساس ثابت**:
  تشغيل حي كامل في بيئة التقرير نفسها (لا استشهاد بتشغيلات قديمة):
  check.sh ALL GREEN rc=0 شامل الحُرّاس الـ16 (11 قديمًا + 5 AIA-7).
  goldens: 99 اختبار replay/parity أخضر + `git status --porcelain
  tests/goldens/` = صفر — مطابقة بتية بالأداتين. خط الأساس من
  PROGRESS (2231P/34S) = القياس الحي بالضبط. الرجفتان الموثقتان
  (S84/mtime) مرّتا داخل التشغيلة هذه المرة — عوملتا بنص المواصفة
  (لا إخفاء، لا فشل جديد). صفر تعديل كود بالبوابة. التقرير التاسع
  في MASTER_REVIEW (dd8f1ac).
  **الموقع: G9 🏁 PASS؛ التالي G10 (المنافسون) بالتتابع.**
- **2026-08-02 — Session 108 (تكملة 6) — CEV-G8.5 🏁 PASS: AIA-C مقفلة — تقرير البوابة + خطوط إثبات R1..R13 في MASTER_REVIEW؛ التالي G9**:
  تصفيرا بيئة #43/#44 (§3.1؛ البوت التقط تقرير G8.5 وقيد إقفال
  AIA-7 في 5dea8d0 — المفقود الوحيد بعد #44 = هذا القيد نفسه، أُعيد).
  **تقرير CEV-G8.5 في MASTER_REVIEW.md** (ثامن تقرير مؤرخ):
  جدول المراحل الثماني AIA-0..7 بقيودها + خطوط إثبات R1..R13 كلٌّ
  بدليل مستشهَد (المفتوح منها = Findings مُسعَّرة بمسار حسم:
  F-013 C2/S3 تسييج التبعيات، F-014 C3/S4 الأدوار الـ15، F-015
  C3/S3 المعجم→TSK-104) + معايير AIA-C السبعة كلها ☑: AIA-1..7
  ببوابات PROGRESS، 226/226 مصنَّفة (+حارس دائم)، 27/27 برومبتًا
  ≥70 + corpus + snapshots، مصفوفة 20/20 خضراء (6 نوايا + ثلاثي
  الصياغات)، سيناريوهات الفحص اليدوي في QA_MASTER_PLAN §P6f.
  **خط النهاية (توثيق أمين)**: ALL GREEN rc=0 (2231P/34S/0F) تحقق
  على الشجرة الحاملة للحُرّاس الخمسة (قبل تصفير #43؛ كل تغيير لاحق
  وثائق فقط — صفر كود). بعد التصفير: بيئة الساندبوكس الجديدة
  (2 vCPU) تُسقط في كل تشغيلة كاملة اختبارًا زمنيًا واحدًا متناوبًا
  بين سابقتين موثقتين (test_search_perf تحت حمل = سابقة S84
  NEW_FINDINGS:400-401؛ test_no_save_churn رجفة mtime 4ms =
  NEW_FINDINGS:397-398) — ×4 تشغيلات، كلاهما يمر معزولًا، والحُرّاس
  الخمسة الجدد + كل الأقسام المسماة خضراء في كل تشغيلة. لا ادعاء
  زائف: البوابة مقبولة بسابقة S84 المعتمدة (بيئي لا كودي).
  **الموقع: G8.5 🏁 PASS؛ التالي G9 (الانحدار) بالتتابع (أمر المالك
  القائم — G7 تبقى DEFERRED وتسبق G12 وجوبًا).**
- **2026-08-02 — Session 108 (تكملة 5) — AIA-7 ✅ مقفلة: الحُرّاس الدائمون الخمسة داخل check.sh (TSK-CEV-105..109) + CEV-F-016 مكتشفة ومُصلحة + ALL GREEN 2231P/34S/0F**:
  تصفيرا بيئة #42/#43 (§3.1؛ البوت التقط افتتاح AIA-7 وكل شرائحها
  الست في 3bdfeaa — المفقود الوحيد بعد #43 = هذا القيد نفسه، أُعيد).
  **اكتشاف بالقياس الحي (منهجية AIA-6)**: مسح آلي لملفات manifest
  الـ21 كشف دورين (`api_analyzer`/`evidence_reviewer`) بلا قاعدة
  «بيانات لا أوامر» — الضابط التعويضي الوحيد لمسار السلاسل الذي يمرر
  system خامًا (F-013) → **CEV-F-016** (C3/S3) → أُصلحا بالصياغة
  القياسية (109a) قبل تفعيل الحارس. **الحُرّاس الخمسة** (TSK لكل
  حارس حسب مواصفة cont22):
  (1) **manifest** — `scripts/check_manifest.py`: schema عبر
  AgentLoader الفعلي + كل `file:` موجود + حدود اللودر صاخبة
  (50KB/1000 سطر؛ التجاوز runtime يُقتطع صامتًا agent_loader.py:668
  — الحارس يرفضه) + `load()` من مصدر agents_rules لكل الأدوار الـ21.
  (2) **اليتامى** — baseline مثبَّت (`agents_rules_baseline.txt`،
  201 مسارًا = جرد AIA-1) + `check_agents_orphans.py`: ملف خارج
  (manifest ∪ baseline ∪ `_archive/`) = فشل.
  (3) **corpus التوجيه** — قسم pytest مسمى fail-fast: T-034 الـ30 +
  مصفوفة AIA-6 الـ20 + goldens التوجيه (كانت التغطية ضمنية فقط).
  (4) **snapshots البرومبتات** — قسم مسمى: إعادة R8 الحية
  بمطابقة القاموس كاملًا.
  (5) **الحقن** — `check_injection_guard.py` بثلاث طبقات: templates
  قيمًا حية (INJECTION_GUARD_INSTRUCTION ملحقة فعلًا بـ
  SYSTEM_PROMPT/CORE_SYSTEM_PROMPT) + قاعدة «بيانات لا أوامر» في
  **21/21** ملف دور + أسوار DATA ONLY في الاستراتيجيات؛ حدّ موثق:
  تسييج نتائج التبعيات (F-013 models.py) خارج التغطية عمدًا.
  **تحقق كسر متعمد لكل حارس**: حذف ملف/ملف يتيم/إزالة القاعدة =
  أحمر، ثم استعادة = أخضر. **بوابة الإقفال مستوفاة**: الحراس داخل
  check.sh (أقسام مسماة قبل السويت) + `bash scripts/check.sh` →
  **ALL GREEN rc=0 (2231P/34S/0F — حتى اختبار الأداء المتقلب مرّ)**
  + موثقون في QA_MASTER_PLAN.md §P6f (جدول + حدود + 3 سيناريوهات
  فحص يدوي لـAIA-C بلا ادعاء أتمتة زائف).
  **الموقع: AIA-7 مقفلة؛ التالي AIA-C (إقفال G8.5).**
- **2026-08-02 — Session 108 (تكملة 4) — AIA-6 ✅ مقفلة: مصفوفة التوجيه كاملة (19 صفًا) + 20 اختبارًا دائمًا + R9/R10 مُثبتان جدوليًا وتنفيذيًا + CEV-F-015/TSK-CEV-104 + ALL GREEN 2231P/34S/0F**:
  تصفيرات بيئة #39/#40/#41 (§3.1؛ البوت التقط AIA-5 في 440f10e ثم
  AIA-6 كاملة في 1ce8b45؛ المفقود الوحيد بعد #41 = هذا القيد نفسه —
  أُعيد)؛ `.env` أُعيدت ×23/×24/×25 (F-003 بلا قرار). **AIA-6 بترتيب
  المواصفة**: (1) **مسابر حية أولًا** على الراوتر الحقيقي بميزانية
  ثابتة — النوايا الست كلها قيست قبل التثبيت (لا اختبار يُخترع من
  الرأس). (2) **corpus دائم جديد** `tests/unit/test_routing_matrix.py`
  (20 اختبارًا، نمط T-034 stub): مصرية صريحة (+حياد لهجة مُثبت:
  فصحى=عامية درجةً ووجهةً)، مختلط عربي/EN (نمط refactor يُلتقط داخل
  الجملة العربية → delegate 9.5)، غير-ويب CLI/توثيق/بيانات (حياد
  مجالي: الحجم يحكم)، أمني (risk signals من الطلب والملف →
  auto_chain 3.5)، غامض متعدد النوايا (قرار مبرر: RoutingRecord يفسر
  delegate 9.0 بنيويًا — صفر أنماط)، ونية ×3 صياغات فصحى/مصري/EN →
  **نفس الوجهة تمامًا** full_chain/6.0/chunk_chain ونفس تسلسل الأدوار
  (R12 جزء CI مُثبت). (3) **فجوتان حقيقيتان اكتُشفتا بالقياس**
  وحُوِّلتا كاملًا: «أعد هيكلة» (فعل أمر) و«ريفاكتور» (معرَّبة) لا
  تلتقطهما الأنماط → auto_chain بدل full_chain = **CEV-F-015**
  (NEW_FINDINGS) + **TSK-CEV-104** (DEVELOPMENT_TASKS — توسيع المعجم؛
  الاختباران المثبتان stub هما معيار القبول الجاهز) — صفر ❌ غير
  مُحوَّل. (4) وثيقة `AIA_ROUTING_MATRIX.md`: المصفوفة 19 صفًا
  (المدخل|الوجهة المتوقعة|القرار الفعلي|RoutingRecord|✅/❌)، R9
  جدوليًا (الاتجاهان — الستة المسندة بمساراتها المستشهدة؛ الـ15
  الباقية = F-014 قرار مالك بلا ادعاء تغطية)، R10 جدوليًا (مفردات
  السلك 4 + الأوركستريتور 6 كلها مغطاة)، و**قرار depends_on/
  conflicts_with المدلَّل** (تكليف AIA-4): الدليل (ChainStep.depends_on
  سياقي بالاستراتيجية — executor يتبع code_analyzer في cw لكن planner
  في cc) يثبت أن القيمة الصحيحة على مستوى manifest = **فارغة عمدًا**؛
  إعادة النظر مشروطة بحسم F-014. (5) corpus T-034 القديم أخضر بلا لمس
  (79P). **بوابة الإغلاق**: check.sh **ALL GREEN rc=0: 2231P/34S/0F**
  (خط أساس جديد = 2211+20). **الموقع: AIA-6 مقفلة؛ التالي AIA-7
  (حراس check.sh الدائمون الخمسة).**
- **2026-08-02 — Session 108 (تكملة 3) — AIA-5 ✅ مقفلة: بطاقات newskells 17/17 + دورة حياة المهارات + ترشيحان CANDIDATE ببندي FI-13/FI-14 (الترقية قرار مالك حصريًا)**:
  تصفير بيئة #38 (§3.1: استنساخ + TOKEN_SCRUB_DONE + جرد نجاة — البوت
  التقط كوميتات AIA-4 الثلاثة كلها في e7d66e2؛ لا شيء مفقود)؛ `.env`
  أُعيدت ×22 (F-003 بلا قرار). **AIA-5 بترتيب المواصفة**: (1) الدليل
  الحي أُعيد إثباته: grep -rn newskells على *.py = تعليقا «مستوحى من»
  فقط (delegate.py:6، strategies.py:419) — صفر import/تحميل. (2) وثيقة
  جديدة `AIA_SKILLS_LIFECYCLE.md`: دورة الحياة الرباعية
  REFERENCE→CANDIDATE→ACTIVE→DEPRECATED (الترقيتان الأخيرتان قرار مالك
  حصريًا)؛ بطاقتا المهارتين codex-delegate/opencode-delegate بالحقول
  السبعة المطلوبة وكل اقتباس بالاستشهاد المزدوج (مصدر newskells ↔ موقع
  editor_v4: الـloop في delegate.py:163–168، «العامل بلا سياق» في
  delegate_brief.md:5، بنية XML، حدود التوسع، أحكام scope/creep في
  delegate_review.md:18–35، التقرير المهيكل)؛ جدول 17/17 ملفًا بحالة
  وتسويغ لكل ملف. (3) **4 ملفات CANDIDATE** (توأما multi-task-queues +
  توأما review-and-land §test-gates) ببندين قياسيين في
  FUTURE_IMPROVEMENTS.md: **FI-13** (طوابير تفويض متسلسلة — منفعة/كلفة
  متوسطة/متطلب: قرار مالك + AIA-6) و**FI-14** (حراس العبث بالاختبارات
  في delegate_review — كلفة منخفضة/متطلب: قرار مالك)؛ relay.mjs
  وdispatch-and-poll بقيا REFERENCE مدلَّلًا (CLI خارجي يناقض
  delegate.py:9 «بدون CLI خارجي»). (4) إحالة مرجعية في AIA_INVENTORY.md
  (منع تضارب السجلّين). **بوابة الإغلاق**: 17/17 بطاقة وحالة ✓؛ FI لكل
  CANDIDATE ✓؛ صفر تحميل runtime جديد ✓ (تغييرات وثائقية بحتة)؛
  check.sh: 2210P/34S + فشل وحيد = test_search_perf الـflaky البيئي
  الموثَّق (سابقة S84 — يمر معزولًا هنا أيضًا؛ التشغيلة الأولى كشفت
  requirements-dev غير مثبَّتة بعد الـwipe → ثُبِّتت فعاد التوزيع
  الطبيعي 34S). كوميتات: eb7f48b (البطاقات + FI) ثم إحالة الجرد ثم هذا
  القيد. **الموقع: AIA-5 مقفلة؛ التالي AIA-6 (مصفوفة التوجيه — 6 فئات
  نوايا إلزامية + نية ×3 صياغات؛ يحل F-014 ويملأ depends_on/
  conflicts_with بالأدلة).**
- **2026-08-02 — Session 108 (تكملة 2) — AIA-4 ✅ مقفلة: schema الـmanifest موسَّع بثمانية حقول توجيه (ADR-007) + 21/21 دورًا مملوء الحقول + check.sh ALL GREEN 2211P/34S/0F**:
  تصفيرات بيئة #36/#37 (§3.1: استنساخ + TOKEN_SCRUB_DONE + جرد نجاة
  — البوت التقط كل شيء في fc5b7b8/950b898؛ الإصلاح الوحيد المفقود:
  loader.roles()→get_available_roles() بالاختبار المقاطَع)؛ `.env`
  أُعيدت ×20/×21 (F-003 بلا قرار). **AIA-4 بترتيب المواصفة الحرفي**:
  (1) **ADR-007 + سطر DECISION_LOG قبل أي سطر كود** — توسيع schema
  v1 نفسه (لا version bump — إضافي بحت) بثمانية حقول اختيارية:
  when_to_use/when_not_to_use/languages/domains/model_notes/
  depends_on/conflicts_with/last_reviewed؛ البدائل المرفوضة مدلَّلة
  (v2 bump / routing.yaml موازٍ / حشو description). (2) **التنفيذ
  في chain/agent_loader.py**: VALID_AGENT_KEYS موسَّعة؛
  AgentDefinition موسَّعة بقيم افتراضية محايدة (grep: صفر إنشاء
  خارج اللودر)؛ _str_list موحّدة بعقد capabilities؛ **تحقق مرجعي**
  لـdepends_on/conflicts_with بعد بناء السجل (مرجع ميت/مرجع ذاتي =
  ManifestError مرقّم السطر)؛ accessor عام جديد definition(role)
  (يحتاجه router في AIA-6). (3) **الاختبارات** (صنف
  TestADR007RoutingFields — 10 اختبارات): قديم يمر بقيم محايدة /
  جديد كامل الحقول يمر / الـmanifest الحقيقي يمر دون تعديل /
  مفتاح مجهول يُرفض مرقّمًا / قائمة بنوع خاطئ تُرفض / scalar فارغ
  يُرفض / مرجع ميت depends_on+conflicts_with يُرفض / مرجع ذاتي
  يُرفض / مرجع صالح يمر. (4) **ملء تدريجي**: 21/21 دورًا مُلئت
  حقوله (when_to_use/when_not_to_use/languages/domains/
  last_reviewed) — depends_on/conflicts_with أُرجئت عمدًا لأدلة
  AIA-6 (لا اختراع قيود بلا دليل) + توثيق schema الموسَّع برأس
  manifest.yaml. **بوابة الإغلاق كلها خضراء**: test_agent_manifest
  58/58 + mypy نظيف (دون إضعاف) + goldens/routing 79/79 +
  **check.sh ALL GREEN rc=0: 2211P/34S/0F** (خط الأساس 2189 + 22
  جديدة). الموقع: AIA-4 مقفلة؛ التالي **AIA-5** (بطاقات newskells
  ودورة الحياة — 17 ملفًا). قرارات مالك معلَّقة: F-003 (×21) +
  F-010 + STALE-175 + F-014.
- **2026-08-02 — Session 108 (تكملة) — AIA-2 ✅ + AIA-3 ✅ مقفلتان: 27/27 برومبتًا ≥70 (22 منها = 100/100) + شق web_system إلى نواة+overlay — معيار AIA-C للبرومبتات مُحقَّق**:
  تصفيرات بيئة #28→#35 (§3.1 في كل مرة: استنساخ + TOKEN_SCRUB_DONE +
  جرد نجاة مقابل آخر commit للبوت — تذكير التدوير §3.2 قائم، اللصق
  تجاوز ×12)؛ `.env` fixture أُعيدت حتى **×19** (F-003 بلا قرار).
  **AIA-2 ✅**: تدقيق تعارض القواعد مكتمل (وثيقة سابقة بالجلسة).
  **AIA-3 ✅ (إعادة كتابة البرومبتات)**: corpus R8 الذهبي قُيِّد
  **قبل** أول إعادة كتابة (9 سيناريوهات/24 خطوة، sha256 لكل system
  prompt)؛ أداة القياس `scripts/prompt_quality_score.py` (10 معايير
  ×10 — regex حتمي)؛ خط الأساس والحالة النهائية موثقان في
  `AIA_PROMPT_SCORES.md`. **5 دفعات إعادة كتابة** (كل دفعة اتبعت
  بروتوكول AIA-R8: replay يفشل بالفشل المتوقع → إعادة تقييد عمدًا →
  12/12 → commit «تحسين مقصود»): د1 مخطط/محقق أخطاء عميق/محلل
  طلبات/مراجع أخطاء/مراجع توافق/مهندس أمان (52-55→100)؛ د2 أدوار
  السلسلة الحية: محلل جودة (مشترك code_analyzer+quality_reviewer)/
  مهندس معماري/MICRO_WORKER (executor، 325→70 سطرًا، بروتوكول
  «منع الرفض» حُذف)/مراجع الكود الآمن (522→~95 مع حفظ جوهر Safety
  Triage) → إعادة تقييد كاملة (executor في كل السيناريوهات)؛ د3
  base_analyze/base_review/delegate_review (جراحي)؛ د4 Frontend/
  Backend (سطر `model:` حُذف — AIA-R4) + محلل أداء (جداول مزودين
  وهمية→تحليل تعقيد ساكن) + حارس الجودة؛ د5 مدير فريق (اعتماد
  ai_team.py الميت أُزيل) + مراجع Vibe + مدير الأوركسترا (14 وكيلًا
  إرثيًا→أدوار manifest الحية + نظام Waves) + مدير المراجعة (516→
  ~95 مع حفظ جوهر FUSION: 5 مراجعين إلزاميين + dedup + حسم
  بالأدلة). **بند §4-B الصريح — شق web_system.md نُفِّذ**:
  core_system.md (نواة عامة: هوية editor_v4 + نواة إلزامية + صيغ
  FILE/CMD/EDIT + أدوات) + web_overlay.md (تخصص ويب) يُركَّبان عبر
  `templates.py._load_system_prompt(web=)` — لا ملف تجميع جديد؛
  الواجهات العامة لم تتغير، اختبارات التسييج خضراء بلا تعديل؛
  المُقيّم يقيس المركّب النهائي: 72→**100**. **النتيجة النهائية
  (على 84c766a): 27/27 ≥70 — 0 تحت العتبة (شرط AIA-C) + replay
  12/12 + حزمة تسييج/ذهبيات/توجيه 95 passed.** الموقع: AIA-3
  مقفلة؛ التالي **AIA-4** (توسيع schema الـmanifest — ADR أولًا).
  قرارات مالك معلَّقة: F-003 (×19) + F-010 + STALE-175 + F-014.
- **2026-08-02 — Session 108 — CEV-G8.5 (AIA) التنفيذ يبدأ: AIA-0 مراسٍ مثبتة حيًا + AIA-1 جرد اليتامى مكتمل (226 ملفًا، صفر غير مصنَّف)**:
  تصفير بيئة #27 (§3.1: استنساخ + TOKEN_SCRUB_DONE؛ اعتماد لُصق في
  نص التكليف — تذكير التدوير §3.2 قائم). نجاة S107 كاملة: البوت
  التقط ذيل الإقفال في cd7260f (HEAD الجديد)؛ `.env` محذوفة مجددًا
  وأُعيدت (**×11** — F-003 بلا قرار بعد). **AIA-0 (تحقق حي لا
  افتراض)**: manifest v1 = **21 دورًا / 20 ملفًا فريدًا** («أنت محلل
  جودة.md» مشترك بين code_analyzer وquality_reviewer) يستهلكه
  agent_loader.py حصريًا (رفض صاخب :46-56، منع path traversal :387)؛
  router.py+routing_config.py قائمان (RoutingThresholds :41)؛ حارس
  الحقن NF-18 سليم (templates.py:29,51)؛ newskells غير محمَّلة
  runtime (grep = تعليقان فقط delegate.py:6/strategies.py:419)؛
  desktop.spec يحزم agents_rules+chain/prompts (:20-21 — يرسّخ منع
  إعادة الهيكلة AIA-X). **AIA-1 (جرد برمجي — وثيقة جديدة
  `AIA_INVENTORY.md`)**: النطاقات الأربعة = 226 ملفًا (agents_rules
  201 مطابقة للمواصفة + prompts 2 + chain/prompts 6 + newskells 17)؛
  التصنيف: **ACTIVE 29 / REFERENCE 17 (newskells كلها) / STALE 175 /
  DUMP 5 — صفر غير مصنَّف** (شرط AIA-C). جوهر STALE: إرث مشاريع
  سابقة بأدلة رؤوس صريحة — «AI_PROVIDERS / C__cursor»
  (memory/PROJECT_VISION.md:1، skills/00-SKILLS.md:1، AGENT.md:2)،
  «AI_MDULE» (GEMINI.md:1 — 135KB)، «.agents عام» (AGENTS.md:2،
  tools/vibe_bridge.py:4 غير مستورد)؛ + 32 برومبت دور غير مسجل
  بالمانيفست (مرشّح تسجيل/أرشفة). DUMP = .bak ×2 + .resolved +
  لصق محادثات ×2 («تشغيل ملف»، «من جينيص»). **الأرشفة/الحذف كلها
  قرار مالك حصري (AIA-R7/EOP-1) — الجرد لا يحذف شيئًا.** الموقع:
  AIA-1 مقفلة؛ التالي AIA-2 (تدقيق تعارض القواعد). صفر تغيير كود.
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
  [ذيل S107 — إكمال بوابة الإقفال بعد تصفير #26 @ 7979fc5]: عمل
  S107 كله نجا عبر البوت (تقرير G8 + F-010/F-011 + D-14 + هذا
  القيد)؛ `.env` أُعيدت (×10). بوابة الإقفال الأولى أظهرت المتقلب
  الموثَّق F-006 (search_perf 1F) — البروتوكول طُبِّق: عزل ×3 يمر
  (1.50-1.65s) ثم **إعادة البوابة كاملة: check.sh ALL GREEN rc=0 =
  2189P/34S/0F** (90.9s) — **إقفال G8 رسمي مكتمل الأدلة**.
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
