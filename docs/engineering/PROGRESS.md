# PROGRESS.md — editor_v4 Engineering Program (CORE-ONLY SCOPE v4.1)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.
> النطاق محكوم بـ SECTION 0.8: النظام الأساسي فقط — Provider Layer خارج النطاق كليًا.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-08-05 (Session 112 تكملة 13 — **خطة اختبار قبول المرحلة مُسلَّمة بإدارة المنفّذ** بطلب مالك مباشر: `docs/ACCEPTANCE_TEST_PLAN.md` — تقسيم عمل صريح (المنفّذ = كل الآلي/Sandbox، المالك = جهاز حقيقي/متصفح/نموذج حقيقي — P-11) + 5 اختبارات منفّذ نُفِّذت فعلًا (بوابة ALL GREEN 2872P/33S على مستنسخ طازج، حارس التعريض حيًا rc=2 ✅، REST دخاني 200 ✅، POST /api/permissions بالعقد الصحيح `{"overrides":{...}}` = قلب حي ✅، خط أساس أداء) + 6 اختبارات مالك مرتّبة بالأولوية بعقد حكم؛ سابقًا في نفس اليوم: تكملة 12 — **القراران 10/11 مُغلقان 🏁 = D-19 مكتمل بكل بنوده**: المالك سلَّم نصّيهما (D-21 يرسّخهما) ففُك انسداد تكملة 11 ونُفِّذت TSK-738: (10) فرع genspark_ai_developer زومن fast-forward إلى main — الفرعان على نفس SHA (كان 0 أمام / 154 خلف)؛ (11) عدة قياس CEV-F-006 مُسلَّمة: scripts/perf_probe.py (نفس مواصفة big_project 5k + عقد أفضل-من-3 + عتبة 1.0s الحرفية) + docs/perf_probe_runbook.md بخط أساس Sandbox مُرسَّخ (import 0.89s / api_search 0.160s / tool_search 0.134s — كلها ✅) وعقد حكم + قياسات FPS اليدوية؛ تشغيلها على جهاز المالك = فعل مالك تُلحق نتيجته؛ البوابة ALL GREEN rc=0 — 2871P/34S/0F) |
| stage | **V3-STAGE 4 — برنامج CEV مُغلق (D-12→D-17) + دفعة D-18 BATCH-CLOSEOUT مُقفلة 🏁** — سوابق مُقفلة كلها 🏁: BATCH-P0 6/6 (v1.0.0-rc.1) + BATCH-FI01 5/5 + BATCH-SHORT 5/5 + D-6 5/5 + BATCH-P1 6/6 (D-9) + BATCH-P2 5/5 (D-10) + BATCH-P3 4/4 (D-11) + EOP-1 + CEV 99/100 GO + D-18 |
| current-phase | **تسلسل D-19 مكتمل كاملًا 🏁**: القرارات 2 (v1.0.0) + 3 (mypy 100%) + 4 (TSK-732) + 5 (TSK-733) + 6 (TSK-734) + 7 (TSK-735) + 8 (TSK-736 ACP) + 9 (TSK-737 network exposure) — **كلها مُغلقة 🏁**؛ والقراران المستقلان 10/11 **مُغلقان 🏁** (D-21 + TSK-738 — تكملة 12) ⇒ **قائمة D-19 الكاملة (2→9 + 10/11) مستوفاة** |
| current-task | **إدارة دورة اختبار القبول (توجيه مالك — تكملة 13)**: الخطة مُسلَّمة في `docs/ACCEPTANCE_TEST_PLAN.md`؛ نصيب المنفّذ (5 اختبارات) نُفِّذ ✅؛ بانتظار مخرجات المالك بالترتيب (1: perf_probe على جهازه = القرار 11 → 2: إقلاع متصفح → 3: FPS → 4/5/6 مستقلة) — كل نتيجة تُحلَّل ويُحكم عليها وفق §3 من الخطة؛ قد تفتح TSK إصلاح |
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
- Stage: **CEV (D-12 → D-17) — 🏁 البرنامج مُكتمل ومُغلق**: G1→G6 + G8 + G8.5 + G9 + G10 + G11 كلها 🏁 PASS؛ **G7 (Red Team) ⚠️ COMPLETED-WITH-FINDING** (تكملة 14 — 44 مجسًّا؛ اكتشافها CEV-F-018 أُغلق بـTSK-CEV-117 في تكملة 15)؛ **G12 🏁 PASS** — بطاقة كاملة **99/100** + **إقرار CEV-R12 صادر** + RRR النهائي **GO** (ضمن عقد localhost أحادي المستخدم حصرًا؛ NO-GO لأي تعريض شبكي). **صفر S1/S2 مفتوحة** بتدقيق موثَّق بالاقتباسات. المفتوح غير الحاجب: CEV-F-006 (S3) · CEV-F-017 (S4) · F-007/F-008/F-009/F-011 (تجميلي/دين مُدار) · FI-01..FI-17 مُسعَّرة · **EOP-1** (بند ختامي D-8-أ). سوابق مُقفلة كلها: P0→P3 🏁
- [أرشيف — النص السابق لهذا السطر، صُحِّح S109 تكملة 15 بعد إغلاق البرنامج] كان يُقرأ: «Stage: **CEV (D-12/D-16) — G1→G6 + G8 + G8.5 + G9 + G10 + G11 كلها 🏁 PASS؛ G7 (Red Team) ⚠️ COMPLETED-WITH-FINDING (S109 تكملة 14 — نُفِّذت بمحاورها الأربعة، 44 مجسًّا)؛ G12 ⚙️ PARTIAL (المحور 10 محجوب)** — الاكتشافات → NEW_FINDINGS (المفتوحة الحاجبة: **CEV-F-018 C1/S2** — تجاوز حجب الأسرار بمِحارف بيضاء لاحقة؛ غير حاجبة: F-017 S4 موسَّعة، F-006/F-007/F-008/F-009 لا فعل الآن)؛ سوابق مُقفلة كلها: P0→P3 🏁 + EOP-1 🏁»
- [أرشيف — صُحِّح S109 تكملة 14] كان يُقرأ: «G7 مؤجلة DEFERRED (D-14)؛ المفتوحة: G8.5 (AIA)» — تقادُم توثيقي (D-16 نقلت G7 من DEFERRED إلى آخر مرحلة، وG8.5 أُغلقت 🏁)، لا ادعاء كاذب.
- خط أساس البرنامج (أُعيد تثبيته حيًّا S109 تكملة 15 عبر `bash scripts/check.sh`): **2576P/0F/34S — ALL GREEN rc=0** (91.80s) — نمو **+290 اختبارًا** عن خط أساس تكملة 14 (2286)، كلها من حزمة انحدار F-018. **ملاحظة أمانة**: الرجفة البيئية **CEV-F-006 (S3)** (`tests/integration/test_search_perf.py:250`) لم تظهر في هذه التشغيلة لكنها **قائمة ومتكررة**؛ قياس A/B أثبت أنها **سابقة** لإصلاح F-018 و**أسوأ بدونه** (خط الأساس يفشل 3/3 مقابل 2/3 مع الإصلاح) ⇒ **ليست انحدارًا**؛ تقسية العتبة **قرار مالك منفصل لم يُنفَّذ ذاتيًّا** (قيد «فقط» في D-17)
- [أرشيف] خط أساس (S109 تكملة 14 @ 65e4f30): **2286P/0F/34S — ALL GREEN rc=0** (تشغيلان متطابقان، 89.79s)
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
- **2026-08-05 — Session 112 (تكملة 13) — خطة اختبار قبول المرحلة مُسلَّمة + نصيب المنفّذ مُنفَّذ ✅ (بوابة + فحص دخاني حي)**:
  المالك طلب صراحةً أن يحدد المنفّذ خطة الاختبار كاملة ويديرها («عايزك
  تحدد أنت خطة الاختبار المناسبة للمرحلة دي... أريدك تدير عملية الاختبار
  بالكامل») وسأل مباشرة عن تقسيم العمل. **التسليم**:
  `docs/ACCEPTANCE_TEST_PLAN.md` — (§0) تقسيم عمل صريح محكوم بـ P-11:
  المنفّذ = كل ما يُؤتمت في Sandbox، المالك = ما يستحيل آليًا (عتاد
  حقيقي/متصفح/نموذج حقيقي)؛ (§1) خمسة اختبارات منفّذ **نُفِّذت فعلًا**
  قبل تسليم الخطة: A1 بوابة كاملة على مستنسخ طازج @6355db9 = **ALL
  GREEN rc=0 — 2872P/33S/0F**؛ A2 حارس الإقلاع حيًا (`--host 0.0.0.0`
  ⇒ rc=2 + رسالة الرفض العربية — TSK-737a يعمل خارج الاختبارات)؛
  A3 REST دخاني (/، diagnostics، GET permissions = 200 ✅)؛ A4 **POST
  /api/permissions بالعقد الصحيح** `{"overrides":{...}}` ⇒ 200 + قلب حي
  (رفض 400 الأولي كان حمولة ناقصة الغلاف — رفض صحيح لا عطب؛ ودرس ثانٍ:
  في مساحة غير موثوقة force تبقى True دائمًا — علوّ Workspace Trust
  fail-closed مقصود، server.py `_force_command_approval`)؛ A5 خط أساس
  الأداء المُرسَّخ سلفًا. (§2) ستة اختبارات مالك مرتّبة بالأولوية —
  لكلٍّ: لماذا/الهدف/الخطوات على جهازه/نجاح/فشل/أخطاء شائعة — الأول
  perf_probe (القرار 11)؛ (§3) عقد حكم يحدد التصرف بكل نتيجة.
  *ملاحظة بيئية*: تشغيل أولي للبوابة على بيئة ناقصة requirements-dev
  أسقط test_symbol_index (غياب tree-sitter grammars) — أُصلح بتثبيت
  dev-deps وأُعيدت البوابة كاملة؛ **درس مرسَّخ في الخطة**: البوابة تتطلب
  البيئة الكاملة. (تصفيران #78/#79 هذا اليوم — استرداد قياسي، صفر فقد.)
- **2026-08-05 — Session 112 (تكملة 12) — القراران المستقلان 10/11 مُغلقان 🏁 (D-21 + TSK-738) ⇒ قائمة D-19 الكاملة مستوفاة**:
  المالك سلَّم نصَّي القرارين (فك انسداد تكملة 11) — رُسِّخا قيدًا
  **D-21** في DECISION_LOG (append-only، بالنص الحرفي) ثم نُفِّذت
  **TSK-738** (مواصفة أولًا وفق D-7) بقيد صارم: صفر تغيير في سلوك
  المحرر. **(738a — القرار 10: فرع genspark_ai_developer)**: الواقع
  المقيس 0 أمام main / 154 خلفه (رأسه 2fe610d 2026-08-01)؛ الاختيار
  المفوَّض حُسم **مزامنةً لا حذفًا** — fast-forward نقي
  (`git push origin main:genspark_ai_developer`) لأربعة مسوغات موثقة
  في المواصفة (0-أمام = لا فقد؛ أدوات البيئة قد تفترض وجوده؛ يحقق
  عين مقصد المالك «منع العمل بالخطأ على كود قديم»؛ غير هدّام)؛ القبول
  متحقق: `git ls-remote` = الفرعان على نفس SHA. **(738b — القرار 11:
  عدة قياس CEV-F-006)**: حد واعٍ — التشغيل على جهاز المالك فعل مالك؛
  المُسلَّم: `scripts/perf_probe.py` (يقيس: زمن استيراد server.py
  كبديل آلي لـ«فتح المحرر» + مساري البحث على مستودع 5k مطابق حرفيًا
  لـfixture big_project وبنفس عقد أفضل-من-3 من TSK-CEV-119 وعتبة
  1.0s الحرفية بلا مساس + لقطة عتاد/RSS؛ نظيف تحت flake8-F وmypy
  بأعلام البوابة) + `docs/perf_probe_runbook.md` (خطوات
  Windows/Linux + جدول خط أساس Sandbox + عقد الحكم + قياسات FPS
  اليدوية عبر DevTools — لا ادعاء قياسها آليًا، روح P-11). **خط أساس
  Sandbox مُرسَّخ** (2 vCPU/985MB/Py3.13): import server = 0.89s؛
  api_search = 0.160s ✅؛ tool_search_code = 0.134s ✅؛ ذروة RSS
  41MB — القياس المعزول أدنى من العتبة بـ~7× (متسق مع تشخيص
  TSK-CEV-119: الرجفة كانت مزاحمة حمل الحزمة). **بند متابعة غير
  حاجب**: نتيجة تشغيل المالك على جهازه الحقيقي تُلحق عند ورودها
  (اختفت ⇒ CEV-F-006 بيئية وتُغلق نهائيًا؛ ظهرت ⇒ تُفتح TSK إصلاح).
  البيئة: تصفيرا #75/#76 (متضمنًا كتابة perf_probe.py المقطوعة —
  أُعيدت بعد تحقق الغياب). البوابة الكاملة: **ALL GREEN rc=0 —
  2871 passed / 34 skipped / 0 failed** (صفر تعديل على أي اختبار).
  **قائمة D-19 الكاملة (2→9 + 10/11) مستوفاة 🏁 — لا مهمة جارية.**
  *[ملحق تصفير #77 — نفس اليوم]*: كوميت الإغلاق الوثائقي قُطع
  بتصفير بيئة؛ الرافع التلقائي أنقذ المحتوى كاملًا (**690e9fa** —
  perf_probe.py + runbook + قيدا CHANGELOG/PROGRESS بلا نقص، تحقق
  ast.parse + grep)؛ أُعيد fast-forward للفرع genspark_ai_developer
  إلى 690e9fa (كان توقف عند 3e5e96d قبل الإنقاذ) — الفرعان متطابقان
  مجددًا؛ البوابة أُعيد تشغيلها كاملة على الحالة المنقذة:
  **ALL GREEN rc=0 — 2871P/34S/0F**.
- **2026-08-05 — Session 112 (تكملة 11) — توجيه مالك: تنفيذ القرارين 10/11 ⇒ انسداد موثَّق (BLOCKED-ON-OWNER): نصّاهما غير مُدوَّنين في أي أثر دائم**:
  المالك وجَّه صراحةً «كمل باقي فيه 10/11». قبل أي تنفيذ أُجري **استطلاع
  استرجاع شامل** لتحديد محتوى القرارين: (1) grep متعدد الصياغات
  («القرار 10/11»، «العاشر/الحادي عشر»، «مستقلان/مستقلين»، «لا يغيّران
  سلوك»، «قائمة القرارات الـ11») عبر **كل** وثائق docs/engineering
  (DECISION_LOG، PROGRESS + الأرشيفان 1/2، CHANGELOG، RRR،
  MASTER_REVIEW، NEW_FINDINGS، FUTURE_IMPROVEMENTS، V3_RESUME_SESSION)
  ووثائق الجذر وcont22.md. (2) **pickaxe عبر كامل تاريخ git**
  (`git log --all -S` بأربع صياغات) — كل الإصابات تعود حصريًا لقيد D-19
  نفسه (0787619 وذريته). **النتيجة الحاسمة**: الأثر الدائم الوحيد هو وصف
  D-19 الفوقي (DECISION_LOG:38): القراران «مستقلان يُنفَّذان في أي وقت
  مناسب لأنهما لا يغيّران سلوك المنتج»، وعمود الدليل يحيل إلى «قائمة
  القرارات الـ11 في **تقرير الجلسة السابقة**» — أي تقرير محادثة لم
  يُرسَّخ في المستودع؛ التفصيل الملزم داخل D-19 يعدّد القرارات 2–9 فقط.
  **الحكم بموجب V3**: لا اختلاق نطاق — تخمين محتوى قرارين «لا يغيّران
  سلوك المنتج» ثم تنفيذ المخمَّن يخالف حرفية قرارات المالك وأمانة السجل؛
  ⇒ **التنفيذ محجوب حتى يسلِّم المالك نص القرارين 10 و11 حرفيًا**
  (عندها يُلحقان بـ DECISION_LOG قيدًا جديدًا append-only ثم يُنفَّذان
  بإجراء D-7 المعتاد). **إجراء موازٍ منجز**: بيئة جديدة (تصفير #74/#75 —
  استنساخ + تعقيم SCRUB=0 + HEAD=f279ecd بلا إنقاذات جديدة) والبوابة
  الكاملة `bash scripts/check.sh` أُعيد تثبيتها: **ALL GREEN rc=0 —
  2871 passed / 34 skipped / 0 failed** (mypy Success على 104 ملفات) —
  الشجرة سليمة تمامًا عند خط أساس إغلاق D-19 «2→…→9».
- **2026-08-05 — Session 112 (تكملة 10) — القرار 9 من تسلسل D-19 مُغلق 🏁: TSK-737 التعريض الشبكي ⇒ التسلسل D-19 «2→…→9» مكتمل كاملًا 🏁**: تنفيذ الشرائح الثلاث بعد تخطيط تكملة 9. (1) **737a** (522f12f): core/network_guard.py نقية — is_loopback_host (ipaddress.is_loopback: 127/8 كاملة + ::1 + ::ffff:127.x المُخرَّط؛ + localhost حرفية case-insensitive + تطبيع أقواس [::1]؛ غير-نص/hostname/قمامة ⇒ مكشوف بلا رفع — fail-closed: ما لم يثبت loopback فهو مكشوف) + exposure_refusal_message (الخطر + نفق SSH + الراية + المسارات المقسّاة) + ثابتة EXPOSE_FLAG؛ 39 اختبار وحدة بارامتريًا. (2) **737b** (908c3df): حارس الإقلاع في main قبل أي تهيئة ثقيلة (host غير loopback بلا راية ⇒ رسالة الوحدة + SystemExit(2)؛ مع --unsafe-expose-network ⇒ تحذير مطبوع بالمسارات المقسّاة) + _network_exposed() بالحكم بواقعة الربط (ctx.config['host'] — كاتبه الوحيد main؛ ctx غائب/بلا مفتاح = محلي ⇒ صفر تغيير سلوك للانحدار؛ دالة بلا حالة — امتثال lint_handler_state) + قسر _force_command_approval()=True عند التعريض (يعلو على overrides وfalse الصريحة — نمط علو Workspace Trust؛ حدوده T4 موثَّقة) + قفل POST /api/permissions=403 (T1 أخطر مسار RCE؛ GET glass-box يبقى) + رفض _ws_acp_prompt بـ acp_error (T3)؛ 19 اختبار تكامل بحقن ctx وهمي — صفر شبكة/ربط فعلي (رفض الإقلاع in-process؛ القسر يعلو على override جانبي مكتوب فعلًا؛ 403 بصفر لمس قرص؛ الانحدار المحلي POST/acp يعملان كما كانا). (3) **737c** (تعديلات الكود أنقذها الرافع c921b94؛ الإغلاق هذا القيد): README §حدود النشر — البند 2 صار إنفاذًا كوديًا بدل التحذير النصي + T4 في البند 1 + بند 6 جديد يحيل لنموذج التهديد الكامل وملاحظة CSRF (T6 — دفاع ضمني قائم)؛ تحديث التعهدات الثلاثة من «القرار 9 سيعيد الفحص» إلى «فُحص وحُسم في TSK-737» (core/permissions_overrides.py + core/provider_keys.py + routes/meta.py)؛ CHANGELOG §TSK-737. **حسم مُسجَّل**: تحرير provider_keys من UI («بعد القرار 9») يبقى **مؤجَّلًا بلا أجل** — T4 يجعل كتابة أسرار عبر قناة غير مُصادَقة خطأً تصميميًا (يُسجَّل FI إن طلبه المالك). **حدود واعية**: لا مصادقة/TLS/rate-limiting (لوازم خدمة ويب — المنتج أداة localhost بعقد CEV)؛ خادم ACP عن بُعد يبقى REJECT؛ السطحان المجمّدان بلا تغيير (36 REST/34 WS). البيئة: تصفيرات #71–#73؛ إنقاذ الرافع c921b94. البوابة النهائية: **ALL GREEN rc=0 — 2871P/34S/0F** (+58 فوق أساس TSK-736). **تسلسل D-19 «2→3→4→5→6→7→8→9» مكتمل كاملًا 🏁 — المتبقي: القراران المستقلان 10/11 بانتظار توجيه المالك**.
- **2026-08-05 — Session 112 (تكملة 9) — القرار 9 من تسلسل D-19 (الأخير): التخطيط مُنجَز (نموذج التهديد + مواصفة TSK-737)**: إجراء D-7 الدائم (تخطيط أولًا). **الوفاء بثلاثة تعهدات مرحَّلة**: (أ) TSK-734 «القرار 9 يعيد فحص مسار permissions_overrides» — فُحص: T1 أخطر مسار (قلب force_command_approval + توسيع allowlist عن بُعد = RCE) ⇒ POST /api/permissions يُقفَل 403 عند التعريض حتى تحت الراية (GET يبقى)؛ (ب) TSK-735 «تحرير المفاتيح من UI بعد القرار 9» — حُسم: **يبقى مؤجَّلًا بلا أجل** (T4 يجعل كتابة أسرار عبر قناة غير مُصادَقة خطأً تصميميًا؛ عقد عدم-الترديد القائم يصمد)؛ (جـ) TSK-736 «يعيد فحص مسارَي ACP» — فُحص: T3 ⇒ WS acp_prompt يُرفض بـ acp_error عند التعريض (لا subprocess بقيادة نظير شبكي). **الحكم الحاسم T4**: قناة الموافقة نفسها WS غير مُصادَق — المهاجم الشبكي يوافق على أفعاله بنفسه ⇒ ApprovalGate صفر حماية ضد نظير شبكي ⇒ الحل الوحيد السليم منع الربط المكشوف نفسه (المسار الموصى للبُعد: نفق SSH/VPN/proxy ينتهي إلى loopback — يعمل اليوم بلا تعديل). **7 قرارات واعية** (المواصفة DEVELOPMENT_TASKS EOF): لا مصادقة تُبنى (REJECT نطاق — خارج R0.1)؛ حارس إقلاع fail-closed (host غير loopback ⇒ رفض إلا بـ --unsafe-expose-network — تغيير سلوك مقصود بقرار D-19-9)؛ قفل المسارات الثلاثة حتى تحت الراية؛ قسر force_command_approval=True عند التعريض (defense-in-depth بحدود موثَّقة)؛ الحكم بواقعة الربط (ctx.config['host']) لا بـ remote_addr (تضليل proxy)؛ loopback تعريف صريح (127/8 + ::1 + localhost — كل ما عداه مكشوف)؛ صفر تغيير بالسطحين المجمّدين (36/34) وصفر شبكة في الاختبارات. **T6 (CSRF محلي)**: دفاع ضمني قائم (JSON Content-Type بلا CORS) — يُوثَّق فقط. 3 شرائح: 737a (core/network_guard.py نقية + اختبارات بارامترية) → 737b (توصيل server/meta + اختبارات تكامل بحقن config) → 737c (README §حدود النشر + تحديث تعليقات «القرار 9 سيفحص» إلى «حُسم في TSK-737» + CHANGELOG + إقفال تسلسل D-19 🏁). استطلاع مُسنَد: server.py:2589 (--host افتراضي 127.0.0.1) و:2920 (app.run بلا حارس) و:2881 (ctx.config كاتب host الوحيد) و:356 (سابقة علو Workspace Trust)؛ routes/meta.py:107-171 (POST permissions)؛ server.py:2326 (_ws_acp_prompt)؛ README:530-562 (§حدود النشر — تحذير نصي بلا إنفاذ)؛ core/provider_keys.py:26 (لا دالة كتابة). التالي: تنفيذ 737a.
- **2026-08-05 — Session 112 (تكملة 8) — القرار 8 من تسلسل D-19 مُغلق 🏁: TSK-736 ACP كاملًا (736a+736b+736c + إغلاق التوثيق)**: **736a** (542730b): chain/acp/{protocol,connection}.py — تأطير JSON-RPC 2.0 fail-closed (parse_line لا يرفع أبدًا؛ TypeGuard لتضييق mypy) + AcpConnection فوق Transport مُحقَن (خريطة pending لكل معرّف — نمط TSK-615؛ EOF يوقظ المنتظرين؛ أخطاء المعالج باسم النوع فقط)؛ 40 اختبار FakeTransport. **736b** (كود أنقذه الرافع 13cf256؛ اختبارات 45cd376): governed_fs.py (GovernedFsHandler — fs/read عبر resolve_workspace_path + is_secret_file برسالة عامة موحّدة «مسار محظور»؛ fs/write كـ ProposedAction بنوع acp_write عبر **نفس** ApprovalGate — لا بوابة ⇒ رفض سابقة T-012؛ request_permission بنوع acp_permission يعيد outcome بلا رفع؛ سقف 512KB) + agent_process.py (Popen بـ noqa S603 أمر المالك من config؛ stderr→DEVNULL؛ initialize بمهلة 20s؛ stop: terminate→kill)؛ +36 اختبارًا ببوابات حقيقية auto/deny وكناري سر. **736c** (69b67bb): _acp_agents_config fail-closed (بلا قسم = صفر تغيير سلوك) + GET /api/acp/agents (🤝، **عقد عدم-الكشف: command/args لا يدخلان REST**) + _ws_acp_prompt/_run_acp_prompt (خيط عامل؛ session/update→acp_update؛ تذكرة run؛ stop في finally) + نوع WS acp_prompt (تجميد 33→34) + مسار REST (تجميد 35→36 — تغيير عقد مقصود D-19-8) + مثال config معلَّق + وكيل دمية tests/fixtures/acp_echo_agent.py + 8 اختبارات تكامل (subprocess الحقيقي الوحيد — الكناري لا يصل الوكيل؛ الكتابة المرفوضة لا تلمس القرص؛ المعتمدة تهبط). **استمرارية CP-15**: قلقاه حُلّا تصميميًا (الأسطول المحكوم عبر البوابة نفسها؛ صفر مساس بـ providers/ ⇒ لا تعديل SECTION 0.8). إغلاق التوثيق: CHANGELOG §TSK-736 (أنقذه الرافع 3859f3f) + هذا القيد. البيئة: تصفيرات #65–#70؛ إنقاذات الرافع 13cf256/5357711/3859f3f. البوابة النهائية: **ALL GREEN rc=0 — 2813P/34S/0F** (+84 فوق أساس 735). **التالي: القرار 9 (network exposure — الأخير)**.
- **2026-08-04 — Session 112 (تكملة 7) — القرار 8 من تسلسل D-19: التخطيط مُنجَز (مواصفة TSK-736 — ACP)**: إجراء D-7 الدائم (تخطيط أولًا). **استمرارية حوكمية**: حكم MASTER_REVIEW CP-15 كان «REJECT… يرفعه المالك كقرار نطاق جديد» — D-19(8) هو ذلك القرار الرافِع؛ قلقا CP-15 يُحلان تصميميًا: (أ) كسر governed-fleet ⇐ كل fs/write_text_file وsession/request_permission من الوكيل الخارجي يمر عبر **نفس** ApprovalGate (نقطة القرار الوحيدة — لا YOLO)، وكل fs/read_text_file عبر path_policy (حدود workspace + denylist الأسرار — الوكيل الخارجي لا يقرأ provider_keys.json/.env أبدًا)؛ (ب) مسّ الطبقة المستثناة ⇐ الكود في `chain/acp/` — صفر مساس بـ providers/، فلا تعديل SECTION 0.8 جديد (الوكيل الخارجي عملية governed لا «مزود»). **مواصفة TSK-736** (DEVELOPMENT_TASKS EOF): المحرر **عميل** ACP فقط (خادم ACP REJECT — R0.1 + نموذج تهديد القرار 9)؛ JSON-RPC 2.0 عبر stdio (initialize → session/new → session/prompt + إشعارات session/update)؛ opt-in عبر `acp.agents` في config (id/name/command/args — بلا قسم = صفر تغيير سلوك؛ أمر المالك من config سابقة hooks TSK-728، لكن العملية لا ترث صلاحية كتابة)؛ صفر subprocess/شبكة في اختبارات الوحدة (FakeTransport مُحقَن؛ التكامل بوكيل دمية بايثون محلي)؛ مهلات fail-closed (terminate→kill سابقة agent_tools). 3 شرائح: 736a (نواة البروتوكول النقية protocol/connection فوق transport مُحقَن) → 736b (agent_process دورة الحياة + governed_fs الجسر المُبوَّب) → 736c (توصيل server: GET /api/acp/agents بلا كشف args + بث session/update للـ WS + بادئة 🤝 في القائمة — نمط 🔑). استطلاع مُسنَد: core/approval.py:152 (ApprovalGate — نقطة القرار الوحيدة + interactive_override)، chain/agent_loop.py:24 (سابقة لا-بوابة⇒لا-تنفيذ)، chain/path_policy.py:18/:89/:158 (denylist + is_secret_file)، core/hooks.py:149 (سابقة subprocess بأمر المالك من config)، chain/agent_tools.py:56 (سماحية المهلة)، MASTER_REVIEW:1254 (CP-15 حرفيًا). التالي: تنفيذ 736a.
- **2026-08-04 — Session 112 (تكملة 6) — القرار 7 من تسلسل D-19 مُغلق 🏁: TSK-735 مزودو API-key القياسيون (بموجب D-20)**: تنفيذ الشرائح الثلاث بعد التخطيط (تكملة 5). (1) **735a** (71b5f8e): `core/provider_keys.py` نقي — read_provider_keys fail-closed (OSError/JSON فاسد/جذر غير dict ⇒ {}؛ مدخل غير نصي/فارغ يُسقَط بصمت) + key_for؛ **لا دالة كتابة** (تحرير المفاتيح من الواجهة مؤجَّل لما بعد القرار 9)؛ الحجب الثلاثي: `provider_keys.json` في SECRETS_DENYLIST_NAMES (path_policy) + .gitignore + توثيق safe_reader — اختبار الحجب البارامتري غطّى الاسم تلقائيًا بمتغيرات التهرب (CEV-117)؛ 20 اختبار وحدة. (2) **735b** (أنقذه الرافع a645b4e؛ الإكمال e7875b0): `providers/openai_compat.py` — مزود عام واحد /chat/completions + بث SSE (نمط shelby)، **المفتاح لا يُردَّد أبدًا** (أخطاء من status_code فقط؛ get_info/__repr__ براية key_configured لا المفتاح؛ RequestException ⇒ type(exc).__name__ فقط)؛ 19 اختبارًا ممسرَحًا صفر-شبكة (كناري "sk-CANARY-735-do-not-echo")؛ إصلاح SyntaxError في ملف الرافع (بايتات بأحرف عربية ⇒ .encode)؛ تسجيل في عقد T-010. (3) **735c** (أنقذه الرافع 037175f؛ إصلاح mypy 11aa183): `_api_providers_config()` fail-closed + `_build_api_provider()` بـ**قراءة مفتاح طازجة** (key_for عند كل تبديل — سابقة TSK-734: تحرير الملف يسري بلا إعادة تشغيل) + إلحاق ديناميكي في /api/models (🔑 + key_configured — opt-in: بلا قسم providers.api_providers = صفر تغيير سلوك) + فرع تبديل عام (400 برسالة تذكر provider_keys.json)؛ config.yaml (متتبَّع — تعليقات فقط): أمثلة api_key المعلَّقة استُبدلت بكتلة تحذير D-20؛ 11 اختبار تكامل (كناري ثانٍ؛ القراءة الطازجة مثبتة؛ providers ما زال مستبعدًا من /api/settings حسب TSK-722a)؛ إصلاح mypy dict-item بتعنوين `providers_list: list[dict]` (سابقة TSK-614). **ملاحظة بيئة**: تصفيرات #61–#64؛ الرافع أنقذ 735b و735c — أُكمل الناقص فقط. البوابة تصاعديًا: 2687P → 2718P → **2729P/34S/0F ALL GREEN rc=0** (+74 فوق أساس TSK-734). التوثيق: CHANGELOG §TSK-735 + هذا القيد. **حدود D-20 عادت**: التكاملات القديمة opaque؛ كود TSK-735 في النطاق الأساسي دائمًا. **التالي: القرار 8 (ACP) — تخطيط أولًا**؛ تذكير: القرار 9 يعيد فحص مسارَي permissions_overrides.json وprovider_keys.json.
- **2026-08-04 — Session 112 (تكملة 5) — القرار 7 من تسلسل D-19: التخطيط مُنجَز (تعديل SECTION 0.8 مُسجَّل قيد D-20 + مواصفة TSK-735)**: إجراء D-7 الدائم (تخطيط أولًا). (1) **قيد D-20 في DECISION_LOG** — تفعيل استثناء SECTION 0.8 بموجب تفويض D-19 المسبق («يُسجَّل صراحة عند بلوغه»)، إجراء V3 §10 بأركانه الأربعة: تفويض مالك (نص D-19 حرفيًا) + تعليل عدم-كفاية (الاستبعاد ثنائي-الاتجاه CONSTITUTION_V3:37 يمنع أي TSK يستهدف providers/) + أثر هجرة غير هدّام (Grandfathering — نص SECTION 0.8 التاريخي لا يُحرَّر) + قيد واحد append-only. النطاق موضعي مُقيَّد (سابقة D-18): providers/ يُفتح لأغراض TSK-735 حصرًا؛ التكاملات القديمة تبقى opaque ويعود الاستبعاد بعد إغلاق القرار 7. **اكتشاف حاكم**: config.yaml متتبَّع في git (ليس في .gitignore) ⇒ نمط `api_key: ""` المعلَّق (config.yaml:215/:220) مُلغى — السر في ملف جانبي مُتجاهَل حصرًا (V3 §0 قيدا 5+6). (2) **مواصفة TSK-735** (مزود API-key عام OpenAI-متوافق): 5 قرارات واعية (provider_keys.json جانبي مُتجاهَل + denylist؛ المفتاح لا يُردَّد في أي endpoint/log — اختبار عقد؛ مزود عام واحد `providers/openai_compat.py` لا فرع لكل بائع؛ opt-in عبر `providers.api_providers` — بلا قسم = صفر تغيير سلوك؛ صفر شبكة في الاختبارات) + 3 شرائح: 735a (core/provider_keys.py + denylist) → 735b (المزود mocked) → 735c (توصيل server + /api/models براية key_configured). استطلاع مُسنَد: registry/base العقد كاملًا، meta.py:249 (سابقة تطهير providers)، path_policy.py:17-23، server.py:1001-1049/:880-960. البوابة على الوثائق: ALL GREEN. التالي: تنفيذ 735a.
- **2026-08-04 — Session 112 (تكملة 4) — القرار 6 من تسلسل D-19 مُغلق 🏁 (TSK-734 تحرير الأذونات من الواجهة)**: تنفيذ كامل بإجراء D-7 (مواصفة أولًا 24fad3b — 5 قرارات واعية + 4 شرائح). (a) `core/permissions_overrides.py` وحدة نقية (whitelist صارم fail-closed: force_command_approval + agent.command_allowlist فقط؛ كتابة ذرية NF-19؛ config.yaml لا يُكتب أبدًا) + 22 اختبار وحدة (b5caa13). (b) `_effective_config()` في server.py + تحويل `_force_command_approval()` وربط الإقلاع إليها + POST `/api/permissions` بإعادة ربط حية لـ `agent_tools.command_policy` + توسيع سادس موثَّق للسطح المجمّد GET→GET+POST بتعليق D-19-6 (أنقذها الرافع التلقائي 9062024). (c) 15 اختبار تكامل: قلب force حي، إعادة ربط policy حية، 400 بصفر تغيير حالة، config.yaml سليم بايتًا-ببايت، null يمسح، POST=GET شكلًا (824d1f7). (d) نموذج تحرير صريح في اللوحة بزر حفظ واحد data-perm-action + إعادة رسم من الحقيقة المعادة + CSS بتوكنز فقط (أنقذها الرافع 535962a؛ +7 اختبارات node a69abea). حد أمني موثَّق: localhost-only — القرار 9 يعيد فحص المسار. تصفيرات بيئة #58–#59 أثناء التنفيذ. البوابة: **ALL GREEN rc=0 — 2655P/34S/0F**. التالي: القرار 7 (مزودو API-key — تعديل SECTION 0.8).
- **2026-08-04 — Session 112 (تكملة 3) — القرار 5 من تسلسل D-19 مُغلق 🏁: TSK-733 لوحة طابور التفويض (يستهلك FI-13، يكمل القرار 4)**:
  - **مواصفة D-7 أولًا** (commit 4c416ed): ملاحظة نطاق واعية — MASTER_REVIEW رفض CP-12 multi-session وأجاز إعادة التقييم بعد FI-15؛ التفسير المنضبط = لوحة مهام الطابور فوق DelegateQueue (TSK-CEV-112) — لا multi-session مخترع.
  - **733a** (3b8ba9c + إنقاذ 491f01e): حقل `delegate_queue` + 4 مقابض WS (queue_delegate_start/status/land/reject) + غلاف `_queue_event_wrapper` يدير التذكرة (completed/failed — لا خانة معلقة؛ DelegateQueue لا يستقبل ticket بحدود CEV-112)؛ start/land_current متزامنان ⇒ خيوط daemon.
  - **733b** (3b8ba9c): ORIGINAL_MSG_TYPES 29 → 33 بتعليق D-19-5.
  - **733c** (3b8ba9c): 12 اختبار تكامل حتميًّا — التتابع الصارم مثبَّت (3 نداءات مزود فقط قبل land)؛ الاعتماد → done+actions golden ثم انطلاق التالية؛ الاكتمال/الرفض يحرران التذكرة؛ بديل wait() الغائبة: حلقة استقصاء بمهلة.
  - **733d** (إنقاذ 8d724d4): queue_panel.js UMD-lite (smoke node 21/21) + لوحة #queue-panel (⏸/⏳/✋/✅/❌ + halt + زرّا data-queue-action) + زر «📋 طابور مهام» (سطر = مهمة) + onopen queue_status + 7 حالات queue_* + CSS بتوكنز فقط.
  - **الثوابت محفوظة**: صفر تعديل على delegate_queue.py/delegate.py/background_delegate.py؛ الكتابة خلف queue_land الصريح ثم أزرار Apply (طبقتا موافقة)؛ رفض = halt كامل (stop-and-ask).
  - **البوابة**: check.sh ALL GREEN rc=0 — **2609P/34S/0F** + mypy نجاح (بعد كل شريحة). تصفيرات بيئة #54–#57 أثناء التنفيذ — الرافع التلقائي أنقذ 733a جزئيًّا و733d كاملًا.
  - **التالي بموجب D-19**: القرار 6 (صلاحيات write-UI) — تخطيط أولًا.
- **2026-08-04 — Session 112 (تكملة 2) — القرار 4 من تسلسل D-19 مُغلق 🏁: TSK-732 مؤشر واجهة المهام الخلفية (يستهلك FI-15)**:
  - **المواصفة أولًا (إجراء D-7)**: TSK-732 كُتبت في DEVELOPMENT_TASKS.md بأربع شرائح (a توصيل خلفي → b تثبيتات → c اختبارات → d واجهة) قبل أي سطر كود.
  - **732a**: حقل `background_task` في SessionContext + KNOWN_CONVERSATION_STATE + استخراج `_gather_delegate_context` (نقل حرفي) + 4 مقابض WS جديدة فوق BackgroundDelegateTask (TSK-CEV-113 — صفر تعديل عليه). **قرار واعٍ**: المهمة الخلفية تحجز خانة المشروع (تذكرة `_begin_run_ticket`) حتى الحسم. **الثابت الصلب**: لا land تلقائي — approve صريح ثم أزرار Apply (طبقتا موافقة).
  - **732b**: ORIGINAL_MSG_TYPES في test_ws_router.py 25 → 29 (تعليق D-19-4).
  - **732c**: 12 اختبار تكامل حتميًّا في test_background_delegate_handlers.py (نمط FakeProvider + `_handle_ws_message`) — تغطي المعايير السبعة كلها (hand-off فوري، لا auto-land، snapshot، golden actions، تحرير الخانة، رفض الإطلاق الثاني، busy).
  - **732d**: background_tasks.js (UMD-lite، smoke 14 تأكيدًا في node) + شارة الهيدر + زر الإطلاق + onopen resync + 4 حالات handleWSMessage + CSS بتوكنز.
  - **بيئة**: تصفيران (#52، #53) أثناء التنفيذ؛ الرافع التلقائي أنقذ 732a+b (6222e17 + a2bb858) — أُعيد ملف الواجهة فقط. بوابتان كاملتان ALL GREEN rc=0 (2598P/34S/0F). Commits: e2e5a92 (732c) + cedb1e1 (732d) مدفوعان.

- **2026-08-04 — Session 112 (تكملة) — القرار 3 من تسلسل D-19 مُغلق 🏁: تغطية mypy 100% بلا استثناءات**:
  (1) تشخيص الخطأ الموثق `providers/openai_shelby.py:166` بتشغيل mypy
  مباشرة: خطأ وحيد union-attr — `data.get("v").get("message")` بعد
  `isinstance(data.get("v"), dict)`؛ mypy لا يضيّق نوع استدعاء `.get()`
  ثانٍ عبر isinstance على استدعاء أول. (2) الإصلاح الأدنى: ربط
  `v_obj = data.get("v")` محليًا ثم `isinstance(v_obj, dict)` —
  **صفر تغيير سلوك** (نفس الدلالات؛ اختبار shelby القائم يمر). (3) رفع
  آخر `--exclude` من بوابة mypy في check.sh + تحديث تعليقات المبررات
  (:14-21) — **mypy Success على 95 ملفًا** (كامل النطاق). (4) تحديث حارس
  البوابة `test_mypy_gate_614.py::test_documented_excludes_only`: كان
  يثبّت وجود استبعاد shelby حرفيًا (فشل مكشوف بالبوابة الأولى — 2585P/1F)؛
  الآن يمنع **أي** `--exclude` ويصون رفع الأربعة (shelby + الثلاثة
  المرفوعة في D-18). (5) البوابة الكاملة: **ALL GREEN rc=0 —
  2586 passed / 34 skipped / 0 failed** (90.1s). commits: 218cc13 + هذا.
  التالي: القرار 4 (مؤشر واجهة المهام الخلفية — تخطيط أولًا وفق D-7).
- **2026-08-04 — Session 112 — قرار مالك D-19 (ترتيب التنفيذ 2→3→4→5→6→7→8→9) + القرار 2 مُغلق 🏁: v1.0.0 النهائي موسوم ومدفوع**:
  بعد إغلاق CEV وتسليم قائمة القرارات الـ11، **اعتمد المالك ترتيب التنفيذ
  حرفيًا**: «2 → 3 → 4 → 5 → 6 → 7 → 8 → 9» والقراران 10/11 مستقلان —
  مُسجَّل **D-19** في DECISION_LOG (يشمل إلغاء شرط rc-حتى-تحقق-Windows
  صراحةً). **القرار 2 (v1.0.0 نهائي) نُفِّذ وأُغلق**: (1) استطلاع كامل
  لمواقع الإصدار (version.py:14 / server.py:82 APP_VERSION / README:617 /
  USER_GUIDE:4 / update_check docstring)؛ التحقق أن اختبارات الإصدار
  (test_version/test_diagnostics/test_update_endpoint) ديناميكية ضد
  `__version__` وأن test_update_check.py بسلاسل حرفية مستقلة — لا اختبار
  ينكسر بالرفع. (2) الرفع: `__version__ = "1.0.0"` + تحديث README
  §سياسة الإصدارات + USER_GUIDE + docstring update_check (سلوك
  `_VERSION_RE` بلا مساس). (3) **تصفير بيئة #49** قطع إلحاق قيد CHANGELOG —
  الاستئناف وجد كل التعديلات + D-19 على origin عبر 0787619 (Auto-Uploader)؛
  أُعيد إلحاق قيد CHANGELOG §RELEASE-v1.0.0 فقط (3790c8e). (4) البوابة:
  check.sh **ALL GREEN rc=0 — 2586 passed / 34 skipped / 0 failed** (94.2s).
  (5) وسم annotated **v1.0.0** + دفع main+tag على origin (تفويض D-8-ج —
  سابقة وسم rc.1، CHANGELOG:1197؛ Auto-Uploader لا يحمل الوسوم). **صفر
  تغيير سلوك — Baseline مرجعي مثبَّت**. التالي: القرار 3 (mypy 100% —
  openai_shelby).
- **2026-08-04 — Sessions 110-111 — 🏁 دفعة BATCH-CLOSEOUT (قرار مالك D-18) مُسلَّمة بالكامل — صفر بنود مفتوحة**:
  **تفويض المالك D-18** (DECISION_LOG): (أ) FI-02 (تقسيم server.py)
  **WAIVED BY OWNER** — لا يُنفَّذ أبدًا؛ (ب) إقفال **كل** البنود
  المفتوحة من تقرير استئناف S110. الجلستان عبرتا **مسوح بيئة
  متعددة (~5)** — §3.1 كل مرة (استنساخ → هوية git → تحقق HEAD)؛
  Auto-Uploader التقط أعمالًا وسيطة @ 4a2b234/4184f9b/12aca86/3b5f4bf —
  **صفر عمل ضائع**؛ الانضباط: كوميت+push فوري لكل وحدة تسليم.
  **المُسلَّمات (7 كود + وثائق)**: (1) **TSK-CEV-118** (CEV-F-017/FI-17):
  توسيع `_COMPLEX_REQUEST_PATTERNS` في `chain/orchestrator.py` —
  فئة `[أاتني]` (ألف الأمر + بادئات المضارع ت/ي/ن) + جذور مبتورة
  هيكل/كتاب/تصميم تلتقط الضمائر المتصلة («وتعيد هيكلته» ⇒
  full_chain)؛ تحقق حي: 8 مجسات موجبة + 3 ضوابط سالبة كلها PASS +
  صنف `TestLexiconGapF017` (5 اختبارات) في test_routing_matrix.
  (2) **TSK-CEV-119** (CEV-F-006): تقسية `test_search_perf.py` عبر
  `_best_of(3, ...)` — الانحدار الخوارزمي الحقيقي يفشل 3/3 بينما رجفة
  جدولة 2-vCPU تسقط؛ **العتبة <1.0s لم تُمَس، لا xfail، لا حذف**
  (التزام حرفي بقيد D-18). (3) **حارس المزودات**: نمط
  genspark.py:58-59 (`if spec is None or spec.loader is None: raise
  ImportError`) في blackbox/perplexity/you_com ⇒ رفع استثناءات mypy
  الثلاثة الموروثة (TSK-CEV-102) من check.sh — **openai_shelby وحده
  باقٍ**؛ `mypy providers/` = Success 13 ملفًا؛ حارس البوابة
  test_mypy_gate_614 حُدِّث للعقد الجديد (مضاد انحدار: الأسماء
  المرفوعة لا تعود للاستثناء) + اختبار قبول مادي للحارس ×4 ملفات.
  (4) **TSK-CEV-120** (CEV-F-011/FI-08): إزالة **43** تشخيصًا ميتًا
  (استيرادات/متغيرات F-rules) عبر 16 ملفًا (chain/ ×10 + context/ ×3 +
  runners/delegate + actions/command_runner + server.py) بعد تحقق
  grep صفر مستهلكين لكل مرشح؛ إيجابيتان كاذبتان صينتا بـnoqa
  (router.py TYPE_CHECKING) أو تُركتا (engine.py re-export مقصود)؛
  **بوابة دائمة**: `flake8 --select=F` في check.sh بعد mypy +
  `flake8>=7,<8` في requirements-dev. (5) **TSK-CEV-121** (CEV-F-009):
  عقد `_err_status()` في routes/files.py — PermissionError⇒403 /
  FileNotFoundError⇒404 / ValueError⇒400 / غيره⇒500، مُطبَّق على 7
  معالجات كانت 500 شاملة؛ **fail-closed بلا تغيير** (اجتياز المسار
  `..%2f` يُرفض 403 والملف لا يُكتب)؛ صنف TestErrStatusContractF009
  (4 اختبارات). (6) **TSK-CEV-122** (CEV-F-008): ترميز style.css —
  كل `border-radius: 8px/12px` الخام ⇒ `var(--radius)`/`var(--radius-lg)`
  وكل `0.15s` (×10) ⇒ `var(--duration-fast)` الجديد في tokens.css.
  (7) **TSK-CEV-123** (CEV-F-007): `static/icons/favicon.svg` (∞ داكن
  32×32، XML مُتحقَّق) + `<link rel="icon">` في index.html.
  **إصلاح جانبي**: حارس PM-01 (test_instrumentation_609) كان يفحص
  server.py لاستيراد صار ميتًا شرعًا ⇒ وُجِّه إلى `core/chat_dispatch.py`
  (مالك المنطق الفعلي). **الوثائق**: FI-02 موسومة ✖ WAIVED BY OWNER +
  FI-08/FI-17 موسومتان ✅ CLOSED في FUTURE_IMPROVEMENTS؛ قسم إغلاق
  «دفعة الإقفال الشامل» مُلحَق بـNEW_FINDINGS (يشمل تصحيح العدد 43 لا
  42)؛ ترويسة PROGRESS مُحدَّثة + **تدوير §6.4 دفعة رابعة**
  (S106–S108، 513 سطرًا ⇒ PROGRESS_ARCHIVE_2). **ملاحظة نطاق**: EOP-1
  كان مُقفلًا سلفًا 🏁 — لم يُكرَّر. **PROGRESS §6.4 rotation** (بند
  التقرير الأخير) = هذا التدوير ذاته ⇒ مُقفل. **البوابة الختامية:
  `bash scripts/check.sh` كاملة (mypy الموسَّع + flake8 -F الجديدة +
  الحُرّاس + pytest) — النتيجة في سطر الكوميت الختامي. commits:
  4a2b234 → 4184f9b → 31e4c8c → 12aca86 → 025b7b7 → 3b5f4bf →
  d7f88de + كوميت الوثائق الختامي. الموقع: صفر بنود مفتوحة —
  بانتظار توجيه مالك جديد.**
- **2026-08-04 — Session 109 (تكملة 15) — 🏁 برنامج CEV مُغلق: TSK-CEV-117 (إصلاح CEV-F-018) + المحور 10 = 9/10 + بطاقة 99/100 + RRR نهائي GO + إقرار CEV-R12 صادر**:
  **تفويض المالك D-17 (المسار «أ»)** بأربعة مُخرَجات متسلسلة حصرًا،
  وقيد «فقط» ملزم. الجلسة عبرت **مسحَي بيئة (#67 و#68)** — §3.1 في كل
  مرة (استنساخ → **تعقيم remote فورًا** → هوية git → تحقق HEAD)؛
  **صفر عمل ضائع** في المرتين (البوت التقط `624b73b` ثم `cb70032`
  حاملًا 315 سطرًا من مُخرَجات هذه التكملة قبل المسح الثاني)؛ الـfixture
  `.env` لم تُحتَج (تُولَّد وقت الاختبار — TSK-CEV-111).
  **(1) TSK-CEV-117 ✅** — الجذر (CEV-R4): `is_secret_file` تقارن
  `path.name.lower()` **حرفيًا**، فالعلّة **غياب طبقة تطبيع** لا نقص
  مدخل في القوائم ⇒ الإصلاح **تطبيع مركزي واحد** في
  `chain/path_policy.py` (إزالة 7 محارف خفية + قصّ **NTFS ADS** عند أول
  `:` + تقليم **بالتناوب** بيضاء↔نقاط حتى نقطة الثبات + `lower()`)،
  بمبدأ اتجاه واحد مُعلَن: **تُشدِّد الحجب ولا تُرخّيه ولا تُستخدم لفتح
  الملفات**. الفحص يُطبَّق على **أجزاء المسار** لا الاسم وحده ⇒ أُغلقت
  بالمناسبة فجوة **سابقة** (جزء مجلد ببادئة مسافة `' .ssh/…'`) بعد
  التحقق أنها ليست انحدارًا من التغيير. النتيجة: 33/33 محجوبًا، 11/11
  مسموحًا، **صفر إيجاب كاذب**، استثناء `.env.example` محفوظ.
  **(1-ب) اختبار الانحدار لكل فئة** (نص أمر المالك):
  `tests/unit/test_path_policy_secret_normalization.py` — **290 اختبارًا
  خضراء، 7 فئات** (`.env` + استثناؤه · NAMES × 14 تحويرًا · EXTENSIONS ×
  التحويرات · DIRS كأجزاء مسار · صفر إيجاب كاذب · تكامل عبر
  `resolve_workspace_path` · خصائص التطبيع مع حارس اتجاه). **تحقُّق
  طَفَري**: إعادة الكود للمطابقة الحرفية ⇒ **4 فشل مُسمّى** ثم استعادة
  ⇒ أخضر (الحزمة ليست عقيمة). **نطاق الأثر**: 692 ملفًا بالنسختين ⇒
  **صفر انجراف تصنيف**.
  **نزاهة (CEV-R3) — ثلاثة تصحيحات ضد المصلحة**: (أ) **سُحب** ادعاء
  «تسريب فعلي» من تقرير G7 — على POSIX لا يتحقق (`.env ` ملف مختلف غير
  موجود)؛ التسريب حقيقي على **Win32/NTFS** (والمشروع Windows-first
  TSK-727)؛ (ب) **صُحِّح خطأ وقائعي**: `'.env.'` كان **محجوبًا سلفًا**؛
  (ج) اكتُشف **ناقل جديد أغفلته جولة G7**: NTFS ADS (`.env::$DATA`)
  وZWSP/BOM (`str.strip` لا يقصّهما — تحقُّق حي).
  **(1-ج) الأداء — بلا مُسكِّنات**: فشل عتبة 1s ظهر بعد التغيير، فرُفض
  رفع العتبة/`xfail`/الحذف. تحسين مرحلي **مقيس كل مرحلة** (ساذج 22.9ms
  → مسار سريع أول **60.4ms أسوأ!** → `frozenset.isdisjoint` 18.4ms →
  فحص مسبق 16.5ms → `lru_cache` + تضمين سطري)؛ التنميط أظهر أن الفائض
  **كلفة نداء الدوال** لا المنطق؛ الأثر الحقيقي على مسار الاختبار
  0.120s→**0.131s (+11ms، أقل من العتبة 7×)**. **A/B حاسم تحت حمل
  الحزمة** (بعد تصحيح ذراع باطلة بـ`--ignore`): **خط الأساس يفشل 3/3**
  مقابل **2/3 مع الإصلاح** ⇒ الرجفة **سابقة وأسوأ بدون الإصلاح**،
  والتغيير **مُبرَّأ بالقياس**. ⇒ **رُفعت** شدة **CEV-F-006 من S4 إلى
  S3** (التوصيف الأصلي «مرة واحدة غير متكررة» خالف القياس)؛ **تقسية
  العتبة لم تُنفَّذ ذاتيًّا** (تغيير عقد أداء خارج D-17).
  **(2) المحور 10 ✅ 9/10** — الشرط الحاجب «§6 بلا S1/S2 مفتوحة» استُوفي
  بتدقيق موثَّق: **صفر S1** في تاريخ المشروع، وكل S2 التاريخية مُغلقة
  بدليل (NF-13/BUG-01، NF-15، NF-18، NF-25/27/28، CEV-F-001/002/003،
  وF-012 بتحقُّق حي: **صفر** إرث `AI_PROVIDERS|curl_cffi|accounts_*.json`
  في `prompts/`)، وF-018 أُغلقت. الدرجة بمنهج **معلَن قبلها**: +5 دفاعات
  من 6 صمدت كاملة (ZIP 12/12، احتواء 11/11، symlink 2/2، موافقة 9/9،
  سياج 12/12) + المحور 4 دقيق 4/4 + انضباط CEV-R3 (homoglyph و`%2e%2e%2f`
  **لم تُقيَّد** كثغرات)؛ **−1** لأن دفاعًا كاملًا **انكسر فعليًا** ولم
  تغطّه الحُرّاس قبل G7، وF-017 (S4) وF-006 (S3) باقيان. **10/10 مرفوضة
  كمبالغة** و**≤8 لا يسندها دليل**.
  **(3) الحسم ✅** — **90/90 + 9/10 = 99/100 ≥ 95** ⇒ العتبة مُحقَّقة ⇒
  **RRR النهائي: GO** ضمن عقد **localhost أحادي المستخدم حصرًا**
  (`127.0.0.1:5000` بلا auth/TLS = حدّ موثَّق)، و**NO-GO صريح** لأي
  تعريض شبكي/تعدد مستخدمين. النسخة المشروطة السابقة حُفظت للأثر.
  **(4) إقرار CEV-R12 ✅ صادر + G12 🏁 PASS** — 12/12 بوابة، بحدود
  معلَنة: `providers/` خارج النطاق (§0.8) ولا يشمله الإقرار؛ المفتوح
  غير الحاجب مُدرَج صراحةً. صُحِّح كذلك جدول «المحجوب بقرارات مالك
  أخرى» (5 من 6 بنوده أُغلقت فعليًا بطابور D-16 وTSK-CEV-116).
  **البوابة الختامية**: `bash scripts/check.sh` = **2576 passed / 34
  skipped / 0 failed — ALL GREEN rc=0** (91.80s). **كوميت محلي فقط — لا
  push ولا branch ولا tag ولا PR** (محظور دون أمر مالك صريح، §7).
  **البنود الختامية المتبقية للمالك**: EOP-1 (حذف
  `docs/engineering_constitution/` قبل الوسم — D-8-أ) · تقسية F-006 ·
  توسيع معجم F-017 · FI-17 · تدوير سجل PROGRESS §6.4.
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
> **تدوير §6.4 (2026-08-04, S110-111/D-18 — دفعة رابعة)**: قيود Sessions
> 106–108 (برنامج CEV كاملًا حتى تكملة 12) رُحِّلت إلى
> `PROGRESS_ARCHIVE_2.md` — أدناه المقاطع الختامية المرجعية فقط.
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
- **[مؤشر أرشيف — تدوير §6.4 دفعة رابعة (2026-08-04, S110-111/D-18)]** قيود Sessions
  106–108 (برنامج CEV: فتح D-12 → بوابات G1..G12 → AIA — 513 سطرًا) رُحِّلت إلى
  `docs/engineering/PROGRESS_ARCHIVE_2.md` (append-only، لا يُعدَّل).
- **[مؤشر أرشيف]** كل ما قبل S84 (بما فيه برنامج v4.1 Sessions 1–23):
  انظر `docs/engineering/PROGRESS_ARCHIVE_1.md` (append-only، لا يُعدَّل).
