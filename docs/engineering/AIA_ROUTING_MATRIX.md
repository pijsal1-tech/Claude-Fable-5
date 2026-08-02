# AIA-6 — مصفوفة التوجيه (Routing Matrix)

| البند | القيمة |
|---|---|
| المهمة | AIA-6 (CEV-G8.5 §4-B) — قلب «كل طلب يصل للبرومبت الصحيح» |
| التاريخ | 2026-08-02 (Session 108) |
| المبدأ | `chain/router.py` حتمي (Python خالص) → قابل للـCI بلا نموذج حقيقي (P-11) |
| الإثبات التنفيذي | `tests/unit/test_routing_matrix.py` (20 اختبارًا دائمًا، نمط T-034) + corpus T-034 القديم (30 قرارًا) |
| القياس | كل «قرار الراوتر الفعلي» أدناه قيس **حيًّا** على الكود الحقيقي (S108) بميزانية ثابتة PLENTY |

---

## 1) المصفوفة — النوايا الست الإلزامية

الوجهة = (strategy السلك → chain_strategy → تسلسل agent_role من strategies.py).

| # | فئة النية | المدخل (مقتطف) | السياق | الوجهة المتوقعة | قرار الراوتر الفعلي | RoutingRecord التفسيري | ✅/❌ |
|---|---|---|---|---|---|---|---|
| 1a | مصرية صريحة | «عايزك تظبطلي الفورم دي، الزرار مش شغال…» | بلا ملف | direct→executor | direct (0.0) | matched_signals={} — لا أنماط، إصلاح صغير | ✅ |
| 1b | مصرية صريحة | نفسه | ملف 600 سطر | direct→executor | direct (2.0 = حد direct_max) | size_score=2.0 فقط | ✅ |
| 1c | حياد اللهجة | نفس النية فصحى («أريد إصلاح هذا النموذج…») | ملف 600 سطر | نفس وجهة 1b | direct (2.0) — تطابق تام | حياد لهجة مُثبت للدرجة البنيوية | ✅ |
| 2a | مختلط عربي/EN | «اعمل refactor للـ authentication module وخلي الـ tokens في env» | بلا ملف | direct | direct (1.5) | request_complexity=['refactor'] — النمط EN التُقط داخل الجملة العربية | ✅ |
| 2b | مختلط عربي/EN | نفسه | 4 ملفات ×700 | delegate→pipeline→(deep_debugger,architect,executor) | delegate (9.5) | ideal=delegate، downgrade_path=[] | ✅ |
| 3a | غير-ويب CLI | «اكتب سكربت CLI بايثون يقرأ CSV ويطلع إحصائيات» | بلا ملف | direct→executor | direct (0.0) | matched_signals={} | ✅ |
| 3b | غير-ويب توثيق | «أضف docstrings لكل الدوال في الملف ده» | بلا ملف | direct→executor | direct (0.0) | — | ✅ |
| 3c | غير-ويب بيانات | «اكتب pipeline معالجة بيانات…» | 7 ملفات ×900 | full_chain/delegate بنيويًا | delegate (≥8.0) | الحياد المجالي: الحجم يحكم لا المجال | ✅ |
| 4a | أمني | «راجع الكود ده — احتمال SQL injection في دالة login وعايز تقرير أمان» | بلا ملف | إشارات risk تُلتقط | direct (1.5) | risk=['\\blogin\\b','أمان'] | ✅ |
| 4b | أمني | نفسه | ملف فيه login+SQL مبني نصيًا | auto_chain→context_window→(code_analyzer,executor) | auto_chain (3.5) | risk من الطلب+الملف معًا | ✅ |
| 5a | غامض متعدد النوايا | «الموقع بطيء وفي bug في تسجيل الدخول وكمان عايز أضيف صفحة» | بلا ملف | direct | direct (0.0) | «تسجيل الدخول» خارج أنماط المخاطر العربية (مصادقة/أمان/تشفير فقط) — انظر F-015 | ✅ |
| 5b | غامض متعدد النوايا | نفسه | مشروع 7 ملفات ×900 | delegate→pipeline (قرار مبرر) | delegate (9.0) | **مبرر لا تخمين**: size=5.0 + file_count=4.0، matched_signals={}، ideal=delegate، path=[] — التفسير بنيوي كامل في السجل | ✅ |
| 6a | ×3 صياغات (فصحى) | «أعد هيكلة وحدة المصادقة بالكامل ونقل الرموز إلى ملف البيئة» | ملف 2500 | full_chain→chunk_chain | full_chain (6.0) | ['نقل']+['مصادقة'] | ✅ |
| 6b | ×3 صياغات (مصري) | «اعملي إعادة هيكلة لموديول المصادقة كله وانقل التوكنز لملف الـ env» | ملف 2500 | **نفس 6a** | full_chain (6.0) | ['إعادة.*هيكلة','نقل']+['مصادقة'] | ✅ |
| 6c | ×3 صياغات (EN) | «refactor the whole authentication module and migrate tokens…» | ملف 2500 | **نفس 6a** | full_chain (6.0) | ['refactor','migrate']+['\\bmigrat\\w+\\b'] | ✅ |
| 6d | اتساق الأدوار | الصياغات الثلاث عبر select_strategy | ملف 2500 | تسلسل أدوار واحد | (code_analyzer, code_analyzer, planner, executor) ×3 | R12 (الجزء القابل للـCI) مُثبت | ✅ |
| 7a | فجوة معجم | «**أعد هيكلة** هذا الكود بالكامل…» (فعل أمر بلا مصدر) | ملف 2500 | full_chain (نية 6a نفسها) | **auto_chain (4.0)** | matched_signals={} — r"إعادة.*هيكلة" لا يطابق «أعد هيكلة» | **❌→ CEV-F-015 + TSK-CEV-104** |
| 7b | فجوة معجم | «اعمل **ريفاكتور** شامل…» (معرَّبة صوتيًا) | ملف 2500 | full_chain | **auto_chain (4.0)** | matched_signals={} — refactor بحروف عربية غير ملتقطة | **❌→ CEV-F-015 + TSK-CEV-104** |
| 7c | خط مرجعي مقابل | «اعملي **إعادة هيكلة** للكود ده كله…» | ملف 2500 | full_chain | full_chain — النمط التُقط | الفارق بين 7a/7c = نص الفجوة حرفيًّا | ✅ |

**المحصلة:** 17 ✅ + 2 ❌ محوَّلان بالكامل (Finding **CEV-F-015** + مهمة **TSK-CEV-104**) — **صفر ❌ غير مُحوَّل**. الحالتان مثبَّتتان stub كما هما (توثيق لا موافقة)؛ تُعكسان عند تنفيذ TSK-CEV-104.

---

## 2) إثبات R9 جدوليًا — التغطية ثنائية الاتجاه

**الاتجاه الأول (كل نية → وجهة):** الجدول أعلاه — كل فئات النوايا الست تصل لوجهة حتمية مفسَّرة بـRoutingRecord.

**الاتجاه الثاني (كل برومبت ACTIVE → نية تصله):**

| الدور (manifest) | مسار الوصول (استشهاد strategies.py) | حالة corpus التي تصله |
|---|---|---|
| executor | كل الاستراتيجيات (direct:59، cw:119، cc:191، mr:298، pl:366، dlg:482,498) | 1a/1b/3a/3b + كل الطبقات |
| code_analyzer | cw:112، cc:160، mr:239 | 4b (auto_chain) + 6a-c (full_chain) |
| planner | cc:176، mr:256، dlg:475 | 6a-c + corpus T-034 delegate |
| deep_debugger | pl:343 | 2b/5b (pipeline) |
| architect | pl:354 | 2b/5b (pipeline) |
| code_reviewer | pl:381، dlg:490 | 2b/5b + corpus T-034 delegate |
| **الأدوار الـ15 الباقية** | **لا مسار كود** (bug_analyzer, api_analyzer, security_analyzer, perf_analyzer, request_analyzer, quality_guard, backend_dev, frontend_dev, quality_reviewer, vibe_reviewer, evidence_reviewer, compat_reviewer, orchestrator, review_manager, team_manager) | **CEV-F-014 — قرار مالك: إسناد أو شطب** (لا نخترع إسنادًا بلا أمر) |

اتجاه R9 الثاني **مكتمل للأدوار الستة المسندة** (اختبار `test_assigned_roles_reachable_via_strategies` يثبته تنفيذيًا). الأدوار الـ15 فجوة **موثقة مُسعَّرة** في F-014 بانتظار قرار المالك — لا ادعاء تغطية زائفة.

## 3) إثبات R10 جدوليًا — القدرات المعلنة ↔ corpus

مفردات السلك الأربع (direct/auto_chain/full_chain/delegate) + مفردات الأوركستريتور الست: كلها مغطاة —
`test_all_wire_strategies_covered_here` (هذا الملف) يثبت الأربع، ومصفوفة تغطية corpus T-034 (`test_routing_corpus.py`) تثبت الست بما فيها المفردة السادسة عبر `build_delegate` المباشر والـmisroute-ين الصامتين الموثَّقين.

حقول التوجيه ADR-007 المملوءة (when_to_use/when_not_to_use/languages/domains) **وصفية للبشر والمراجعة** حاليًا — استهلاكها الآلي في router.py مؤجل بنص ADR-007 نفسه («الاستهلاك مؤجل»)، فلا capability معلنة تدّعي سلوكًا آليًا غير موجود.

## 4) depends_on / conflicts_with — الملء بالأدلة (تكليف AIA-4 المؤجل)

قرار مُدلَّل: **اعتماديات الأدوار في editor_v4 هي اعتماديات خطوات داخل استراتيجية** (ChainStep.depends_on — استشهادات: cw:121، cc:183,197، mr:262,305، pl:360,372,390، dlg:484,492,500) وليست اعتماديات على مستوى تعريف الدور: نفس الدور يسبق ويلحق أدوارًا مختلفة باختلاف الاستراتيجية (executor يتبع code_analyzer في cw لكنه يتبع planner في cc). لذا:

- `depends_on` على مستوى manifest **تبقى فارغة عمدًا** — ملؤها كان سيكذب على البنية (الاعتمادية سياقية بالاستراتيجية، مصدرها الوحيد strategies.py). هذا هو «الملء بالأدلة»: الدليل أثبت أن القيمة الصحيحة = فارغة.
- `conflicts_with` تبقى فارغة كذلك — لا يوجد أي دليل تعارض runtime بين الأدوار الستة المسندة (تتعايش في pipeline/delegate ذاتهما).
- إعادة النظر مشروطة بحسم F-014: إن أسند المالك أدوارًا من الـ15، تُملأ الحقول حينها بأدلة الإسناد الجديدة.

## 5) بوابة الإغلاق

- [x] المصفوفة كاملة (19 صفًا: النوايا الست + الاتساق الثلاثي + الفجوتان + الخط المرجعي)
- [x] صفر ❌ غير مُحوَّل (2 ❌ → CEV-F-015 + TSK-CEV-104)
- [x] R9 مُثبت جدوليًا (§2) وتنفيذيًا؛ فجوة الـ15 دورًا = F-014 قرار مالك مُسعَّر
- [x] R10 مُثبت جدوليًا (§3) وتنفيذيًا
- [x] الاختبارات دائمة في check.sh (pytest يلتقط tests/unit/test_routing_matrix.py تلقائيًا — check.sh:154)
- [x] corpus T-034 القديم أخضر بلا تعديل (79 passed)
