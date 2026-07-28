# MASTER_REVIEW.md — Agentic IDE (Constitution FINAL-GOVERNED)

> الوثيقة المركزية لمراحل المراجعة R-1 → R10 بموجب
> **MASTER ENGINEERING CONSTITUTION — FINAL-GOVERNED** (المعتمد Session 24).
> الحالة تُدار في PROGRESS.md فقط. هذه الوثيقة **لا تُعيد** أي عمل سابق —
> بل تُشير إليه وتُكمل الفجوات فقط (Continuity Rules §2.1–2.3).

---

## 0. CONTINUITY MAP — تعيين مخرجات البرنامج السابق (v4.1) على مراحل الدستور الجديد

البرنامج السابق (P1–P8 + تنفيذ M1–M5، 19/19 TSK) أُقفل بالكامل في Session 23.
مخرجاته **مصدر حقيقة مُعتمد** ولا تُعاد قراءة الكود لما غطّته، إلا عند دليل تقادم.

| مرحلة الدستور الجديد | التغطية من الوثائق السابقة | الفجوة المتبقية |
|---|---|---|
| **R-1 Repository Inventory** | ARCHITECTURE_REVIEW.md §Repo-map (P1a) — أرقام ما قبل التنفيذ | ✅ أُنجز تحديثها هذه الجلسة (§R-1 أدناه) |
| **R0 Strategic Assessment** | لا تغطية سابقة (v4.1 لم يتضمن بعدًا استراتيجيًا/تنافسيًا) | **كاملة — أولوية تالية** |
| **R1 Repository Understanding** | ARCHITECTURE_REVIEW.md P1a–P1g (خريطة، تدفقات، تبعيات، مخاطر) | تحديث دلتا فقط: ما غيّرته TSK-101→502 في التدفقات |
| **R2 Strengths Register** | مبعثر ضمنيًا في ARCHITECTURE_REVIEW/PROGRESS | **جدول Strengths رسمي مطلوب** |
| **R3 Subsystem Map + Scorecard** | P1g (مخاطر) + VERIFIED_BUGS + NEW_FINDINGS | **Scorecard 0–10 لكل subsystem مطلوب** |
| **R4 Security + Agent Safety** | NEW_FINDINGS (NF-16 وأقرانه) + TSK-502 (force_approval) + README §حدود النشر | مراجعة Agent-Safety مُهيكلة (tool boundaries, goal drift, poisoning) — جزئية |
| **R5 Reliability** | NEW_FINDINGS P3a–P3c (سباقات/async/تسريبات) + إصلاحات M1–M5 | دلتا: ما بقي OPEN بعد التنفيذ |
| **R6 Performance + Baselines** | TSK-501 (فهرس بحث مشترك) + QA-T13 | **جدول Baseline Metrics + AI-Runtime metrics (أغلبها NOT INSTRUMENTED)** |
| **R7 Runtime Pipeline** | ARCHITECTURE_REVIEW P1b (تدفقات WS/جلسات/بث) | مخطط Pipeline موحّد Request→…→Completion |
| **R8 Engineering Quality** | NEW_FINDINGS (تكرار/اقتران) + FUTURE_IMPROVEMENTS | دلتا بعد التنفيذ |
| **R9 UX & Agentic Capability Matrix** | جزئي (FUTURE_IMPROVEMENTS DX items) | **مصفوفة القدرات الوكيلية مطلوبة** |
| **R10 Testing & Docs** | QA_MASTER_PLAN (P6) + RELEASE_READINESS_REPORT (P8) | دلتا: حالة البوابات بعد إغلاق M1–M5 |

**قاعدة ملزمة**: أي نتيجة سابقة تُذكر هنا تُشار بمعرّفها (BUG-xx / NF-xx / TSK-xxx /
FI-xx) ولا تُنسخ. حالات النتائج تُهاجَر كسولًا إلى دورة الحياة الجديدة
(OPEN→…→VERIFIED) عند أول لمسة (Constitution §8.1).

---

## R-1 — Repository Inventory ✅ (متحقق منه فعليًا — Session 24, 2026-07-28)

### الهوية
- **Repo**: `pijsal1-tech/Claude-Fable-5` (خاص) — clone نظيف على `main @ 35c05d7`.
- **الفروع**: `main` (يضم كل تنفيذ M1–M5) · `origin/genspark_ai_developer @ ac43f6c` (متأخر — توقف عند P8 التوثيقي).
- **الشجرة**: نظيفة (لا dirty files).

### اللغات والأحجام
| نوع | عدد الملفات | ملاحظة |
|---|---|---|
| Python | 216 | النواة: 26,615 سطرًا (خارج tests/providers) |
| Markdown | 287 | يشمل agents_rules/ (201 ملفًا — أصول برومبتات، ليست كودًا) |
| JS | 16 | الواجهة: `static/app.js` = 3,798 سطرًا |
| CSS / HTML / YAML / JSON | 10 / 4 / 4 / 20 | config.yaml = التهيئة المركزية |

### أكبر الوحدات (بالسطور، داخل النطاق)
| ملف | سطور | دور |
|---|---|---|
| `server.py` | 2,823 | النواة: Flask + WS lifecycle + REST + dispatch (نما من 2,613 بعد M1–M5) |
| `chain/bridge.py` | 782 | جسر سلسلة الوكلاء |
| `chain/agent_tools.py` | 768 | أدوات الوكيل (تشمل tool_search_code بعد TSK-501) |
| `chain/delegate.py` | 751 | تفويض المهام |
| `chain/context_builder.py` | 622 | بناء السياق |
| `chain/agent_loader.py` / `executor.py` / `agent_loop.py` | 610/599/585 | تحميل/تنفيذ/حلقة الوكيل |
| `sessions/store.py` | 602 | مخزن الجلسات |
| `static/app.js` | 3,798 | واجهة كاملة أحادية الملف |

### المجلدات (ملفات / سطور Python)
core 14/3,019 · chain 29/8,892 · actions 5/1,044 · context 22/3,604 ·
runners 5/688 · sessions 4/1,285 · tests **147/22,727** ·
providers 11/3,034 **[OUT OF SCOPE — عقدة خارجية مطوية]** ·
improvements 40/3,315 (أرشيف نسخ قديمة — ليست كودًا حيًا) ·
agents_rules 201 ملفًا (أصول محتوى) · newskells 17 · scripts 6/548.

### أنظمة البناء والاختبار
- **Runtime**: Python 3.13 · Flask + flask-sock (WS) · PyYAML · aiohttp.
- **Test**: pytest 9 (`pytest.ini`: testpaths=tests, timeout=30) —
  147 ملف اختبار (unit/integration/contracts/fakes/goldens/fixtures).
- **Gates**: `scripts/check.sh` (بوابات بنيوية: rglob ban، SafeReader routing…).
- لا CI مُفعّل ظاهرًا سوى `.github/` (يُفحص في R10-delta).

### الحالة التنفيذية المتحقق منها (Baseline هذه الجلسة)
| قياس | قيمة | طريقة القياس |
|---|---|---|
| `python -c "import server"` | ✅ سليم | تشغيل مباشر (بعد تثبيت flask/flask-sock) |
| الحزمة الكاملة | **1709 اختبارًا: 4 فاشلة / 1671 ناجحة / 34 متخطاة** | pytest --junitxml، تشغيل كامل ~82s |
| زمن الحزمة الكاملة | ~82 ثانية | timing مباشر |

**الفشل الأربعة (موروثة، خارج نطاق الخطة المُقفلة — تُرحَّل كمرشحين للخطة الجديدة):**
1. `test_file_icons::test_license_note_present`
2. `test_history_consumers::test_no_raw_history_slices_outside_sessions`
3. `test_rollback_ui::test_index_wiring_and_load_order`
4. `test_theme_tokens::test_no_raw_colors_outside_themes`

**[SUPERSEDED — 2026-07-28 — Session 24]**: الفشل الخامس المسجل سابقًا
(`test_symbol_index::test_missing_file_empty_table_with_reason`) **ينجح الآن**
(تحقق مباشر في هذه البيئة؛ فارق skips 63→34 يشير لتوفر tree-sitter grammars
التي كانت غائبة في بيئة الجلسات السابقة). السجل التاريخي في PROGRESS.md يبقى كما هو.

### مواضع مرشحة للقراءة العميقة في R0/R2–R9 (قرار ميزانية القراءة)
- **R0**: لا قراءة كود — مصادر خارجية موثقة فقط + PRODUCT_VISION.md في `docs/engineering_constitution/`.
- **R2/R3**: `chain/*` (8,892 سطرًا — أكبر subsystem لم يُشرَّح كاملًا في v4.1 لأن تركيزها كان server.py) + `core/` + `sessions/store.py`.
- **R4 Agent-Safety**: `chain/agent_tools.py` + `chain/agent_loop.py` + `actions/command_runner.py` (بعد TSK-502).
- **R6**: instrumentation gaps — متوقع NOT INSTRUMENTED لأغلب AI-runtime metrics.

---

## R0 — Strategic Architecture Assessment ✅ (Session 25 — 2026-07-28)

> المصدر الداخلي الحاكم: `docs/engineering_constitution/PRODUCT_VISION.md` v1.0
> (فصل دستوري مُلزم — قُرئ كاملًا هذه الجلسة). المصادر الخارجية: وثائق رسمية فقط
> (cursor.com/docs، code.claude.com/docs، zed.dev/docs، docs.github.com، docs.devin.ai).
> ملاحظة: §10 في PRODUCT_VISION كانت ACCESS-LIMITED — هذا القسم يرفع الحالة جزئيًا
> عبر فحص وثائق رسمية حي (2026-07-28)، وهو Amendment Trigger مسجّل في §16 هناك
> (تسجيل التحديث الفعلي لـ PRODUCT_VISION نفسه = قرار مالك، خارج صلاحية REVIEW).

### R0.1 — رؤية 1–2 سنة (Vision Statement)

**North Star (معتمد من PRODUCT_VISION §2):**
> «بيئة البرمجة بالذكاء الاصطناعي التي يثق بها المطور فعلًا: كل فعل AI قابل
> للمعاينة والموافقة والإسناد والتراجع — بلغته، وعلى جهازه.»

خلال 1–2 سنة يجب أن يكون المنتج:
1. **Trust-visible**: حلقة الثقة الموجودة (ApprovalGate → Checkpoint → Rollback)
   ظاهرة في الواجهة (diff panel، run narratives) لا مدفونة في المحرك — Pillar 1 + Doctrine §13.1.
2. **Glass-box context**: المستخدم يرى «ما الذي رآه الـ AI» لكل تشغيل — Pillar 2.
3. **Governed autonomy أعمق**: خطط متعددة الخطوات لا تخرج أبدًا من الحوكمة
   (allowlist + verify-step) — Pillar 3، بلا "YOLO mode" (Non-Goal §15.1).
4. **Source-sovereign**: تفعيل مزودي API-key من الـ stubs الموجودة — تحوّط FINDING-12
   (خارج نطاق هذه المراجعة تنفيذيًا لكن مسجل كرهان استراتيجي).
5. **Arabic-first كتوقيع حِرفي** لا كترجمة — Filter F5.

### R0.2 — Competitive Pattern Table (مصادر رسمية فقط — فُحصت 2026-07-28)

| # | Pattern | Who uses it | Source (official) | Relevant? | Fits philosophy? | Verdict |
|---|---|---|---|---|---|---|
| CP-1 | **Plan Mode** — الوكيل يكتب خطة قابلة للتحرير التفاعلي قبل التنفيذ | Cursor | cursor.com/blog/plan-mode + cursor.com/docs | نعم — عندنا planner (heuristic/llm/hybrid) لكن الخطة ليست artifact تفاعليًا للمستخدم | نعم (يقوّي F1/F2: موافقة قبل تنفيذ) | **ADOPT-CANDIDATE** → يُقيَّم في R9 |
| CP-2 | **Checkpoints/Restore** لكل رسالة agent | Cursor | cursor.com/docs (agent) | نعم — عندنا CheckpointManager + run-history UI أصلًا | نعم | **ALREADY-HAVE** — الفجوة في الإظهار لا الآلية (Doctrine §13.1) |
| CP-3 | **Rules ملفية معيارية** (AGENTS.md + project/user rules) | Cursor + الصناعة | cursor.com/docs/rules | نعم — عندنا agents_rules/ + manifest.yaml (fleet-as-data) | نعم | **ALREADY-HAVE (أقوى)** — نظامنا governed بـ allowlist؛ يُفحص توافق AGENTS.md كمعيار تشغيل بيني في R9 |
| CP-4 | **Hooks lifecycle حتمية** — أوامر مستخدم تعترض كل حدث في دورة حياة الوكيل (tighten-only: لا تُضعف الأذونات أبدًا) | Claude Code | code.claude.com/docs/en/hooks + /hooks-guide | نعم جدًا — يطابق فلسفة «Determinism before cleverness» (F2) | نعم | **ADOPT-CANDIDATE** → R9 (كامتداد لآلية verify-step القائمة) |
| CP-5 | **Declarative permission rules** (allow/deny/ask patterns + `/permissions` UI) | Claude Code | code.claude.com/docs/en/permissions | نعم — عندنا allowlist + SAFE/DANGEROUS_COMMANDS + force_approval (TSK-502) | نعم | **PARTIAL** — نمط الـ UI الاستعراضي للأذونات فجوة محتملة → R4/R9 |
| CP-6 | **Subagents بسياقات معزولة** لكل مهمة | Claude Code | code.claude.com/docs (subagents) | جزئي — عندنا 21-agent fleet لكن العزل السياقي يُتحقق منه في R9 | نعم إن بقي governed | **EVALUATE** → R9 |
| CP-7 | **Follow-agent + Review Changes مجمّعة** (Shift+Ctrl+R) | Zed | zed.dev/docs/ai/agent-panel + zed.dev/ai | نعم — نمط مراجعة الدفعة بعد الحقيقة | **جزئيًا** — فلسفتنا consent-قبل-الكتابة لا مراجعة-بعدها؛ Zed نفسها تتلقى طلبات مجتمعية لمعاينة قبل الموافقة (discussion #47695) | **REJECT الترتيب / ADOPT الإظهار** — تأكيد خارجي أن معمارية consent-first عندنا هي الاتجاه الصحيح |
| CP-8 | **Session logs كسرد كامل + draft PR تدريجي** | GitHub Copilot coding agent | docs.github.com (cloud-agent) | نعم — يطابق «run-history narratives» في Pillar 1 Direction | نعم (محليًا، بلا cloud pivot — Non-Goal §15.2) | **ADOPT-CANDIDATE (السرد فقط)** → R9 |
| CP-9 | **Auto-generated Memories أثناء المحادثة** | Windsurf Cascade | docs.devin.ai/desktop/cascade/memories | نعم — عندنا provenance-tracked JSONL memory + Memory Panel | نعم — بشرط بقاء الذاكرة مملوكة/قابلة للحذف (glass box) | **PARTIAL** — التوليد التلقائي المقترَح يُقيَّم ضد honesty §11.4 في R9 |

**خلاصة تنافسية**: لا حاجة لأي انعطاف معماري. الأنماط الخارجية الجديرة كلها
(خطة-كـartifact، hooks حتمية، سرد الجلسة) **امتدادات** لآليات قائمة عندنا —
تتوافق مع سلّم Preserve → Wrap → Extend. النمط الوحيد المرفوض جوهريًا (CP-7:
mutation-then-review) يؤكد صحة معماريتنا consent-first.

### R0.3 — Architecture Fitness Dimensions (المرجع الملزم لكل تغيير قادم)

| # | Dimension | Baseline الحالي | كيف يُقاس عند كل تغيير |
|---|---|---|---|
| FD-1 | Complexity | server.py=2,823 سطرًا؛ chain/=8,892 | ΔLOC للملفات المحورية + عدد المسارات الجديدة |
| FD-2 | Testability | 1709 اختبارًا (4F موروثة)/~82s + goldens + grep gates | كل سلوك جديد له بوابة قابلة للفحص آليًا |
| FD-3 | Coupling | صفر دورات استيراد (NF-24، AST-verified) | إعادة فحص AST بعد كل milestone |
| FD-4 | Memory | UNKNOWN — غير مُقاس (يُرصد في R6) | RSS تحت حمل مرجعي (طريقة تُثبَّت في R6) |
| FD-5 | Startup time | UNKNOWN — يُقاس في R6 | زمن import server + جاهزية أول طلب |
| FD-6 | Plugin API stability | capability-limited context + grep gates (VERIFIED — PRODUCT_VISION §3.4) | لا توسيع سطح إلا عبر allowlist |
| FD-7 | Extension/frontend impact | app.js=3,798 سطرًا أحادي الملف | أي تغيير واجهة يذكر أثره على البنية الأحادية |
| FD-8 | Resume capability | sessions/store.py + checkpoints + run history | اختبارات استئناف قائمة تبقى خضراء |
| FD-9 | Agent-runtime impact | verify-step contract + timeout/output caps | كل تغيير agent يمر بعقد verify-step |

### R0.4 — الرهانات طويلة المدى والمخاطر

**رهانات (مصدرها PRODUCT_VISION، مثبتة هنا كمرجع مراجعة):**
- **BET-1**: مع تسليع الـ autonomy تصبح *الثقة والقابلية للتفسير والمحلية* هي
  النُدرة (§10 trend) — يدعمه خارجيًا طلب مجتمع Zed لمعاينة-قبل-موافقة (CP-7).
- **BET-2**: العربية-أولًا wedge سوقي لا يخدمه أي منافس (§4) — `STRATEGIC_HYPOTHESIS`.
- **BET-3**: model-source independence عبر العقد الموجود لا امتلاك نماذج (§12) —
  طبقة المزودين نفسها OUT OF SCOPE هنا.

**مخاطر استراتيجية (تُغذّي RISKS.md لاحقًا في Stage 2):**
- **SR-1**: فجوة «الإظهار» — المحرك موثوق لكن السطح لا يُظهره (FINDING-11)؛
  المنافسون يُظهرون خططهم وسردهم بشكل لامع → خطر إدراكي لا هندسي.
- **SR-2**: هشاشة المزودين المجانيين تجاريًا (FINDING-12) — خارج نطاق المراجعة،
  داخل نطاق الوعي الاستراتيجي.
- **SR-3**: نمو server.py (2,613→2,823 خلال M1–M5) — اتجاه تمركز يُقيَّم في R3/R8.
- **SR-4**: قياس النتائج المنتَجية غائب كليًا (§14) — observability فجوة مزدوجة
  (منتَج + AI-runtime metrics) → R6.

**Long-term Technical Vision line**: كل توصيات هذه المراجعة ستُختبر بسؤال
«هل تبقى صحيحة خلال 1–2 سنة؟» ضد BET-1..3 وFD-1..9 — لا تبنّي أنماط لمجرد رواجها.

---

## R1 — Repository Understanding (Delta) ✅ (Session 25 — 2026-07-28)

> الأساس المعتمد: ARCHITECTURE_REVIEW.md (P1a–P1g) — يصف الكود **قبل** تنفيذ M1–M5.
> هذا القسم دلتا فقط: ما غيّرته TSK-101→502 في التدفقات الموثقة هناك.
> كل موضع أدناه **تحقق منه ساكنًا هذه الجلسة** (grep/ls مباشر على HEAD `2e586b0`).

### R1.1 — الوحدات الجديدة (لم تكن موجودة وقت P1)

| وحدة | مصدر | دور في التدفق |
|---|---|---|
| `core/ignore_rules.py` (1.9KB, leaf بلا imports) | TSK-202 | `IGNORED_DIRS` frozenset موحّدة (23 اسمًا تشمل `test---results`) — حلّت محل قائمتي file_manager/bridge المنفصلتين (BUG-04 مُغلق) |
| `context/search.py` (15.2KB — SearchService + `shared_search(index)`) | TSK-501 | خدمة بحث واحدة فوق ProjectIndex الحي؛ أزالت `fm.scan_project(10000)` لكل ضغطة و`rglob` لكل نداء (NF-20/21) |
| `static/js/stream_render.js` (5.1KB) | TSK-401 | بث تدريجي — أنهى إعادة `marked.parse`+`innerHTML` الكاملة لكل chunk (NF-10) |
| `prompts/templates.py::fence_attached` | TSK-404 | تسييج المحتوى المحقون في البرومبت (NF-18 — مقاومة prompt-injection) |

### R1.2 — تغيّرات التدفقات الموثقة في P1b/P1d/P1e

| تدفق (مرجع P1) | كان (وقت P1) | صار (بعد M1–M5) | موضع متحقق |
|---|---|---|---|
| **Parser pipeline** (P1d) | `parse(response)` mode-agnostic + fallback تخميني يصنع actions في chat (BUG-01) | `parse(response, mode=None)` — وضع chat يعطّل الـ fallback؛ إطار chat done يحمل `actions: []` دائمًا | `actions/response_parser.py:107` |
| **Apply pipeline** (P1d) | بلوكان متطابقان apply_all_actions/execute_plan | دالة واحدة `_apply_batch` مقفولة بـ golden + ticket تسجيل + نقطة تفتيش إلغاء (TSK-201/304) | `server.py:2415` |
| **Context injection** (P1c) | مساران بلا سقف موحّد (BUG-03) | موحّدان تحت ContextBudget عبر `gather_message_context` (TSK-103) | `context/facade.py` |
| **History payload** (P1b) | تاريخ كامل في الحمولة | `history.payload_last_n: 40` قابل للضبط (TSK-104) | config.yaml |
| **Backup restore** (P1e) | `extractall` بلا فحص | `_zip_member_violations` — Zip-Slip/symlink guard قبل الاستخراج (TSK-105) | `server.py:1030` |
| **Command approval** (P1e) | `need_approval=False` في 3 مواضع بلا بديل | راية `force_command_approval` تُلزم البوابة على المواضع الثلاثة (TSK-502) | `server.py:172` + `command_runner.py:57,107` |
| **WS reconnect** (P1b frontend) | `setTimeout(...,3000)` ثابت + `JSON.parse` عارٍ | backoff+jitter + try/catch حول onmessage (TSK-402) | static/app.js |
| **First feedback** (P1b) | صمت حتى إطار start بعد بناء السياق | إطار `scan_start` فوري (TSK-403) | server.py `_dispatch_chat_message` |
| **Registry hygiene** (P1b) | `_tickets` ينمو بلا سقف؛ خانة run عالمية `""` | تقليم tickets المنتهية + خانة per-project (TSK-303/302) | ExecutionRegistry |
| **Locking** (P1g race) | تنظيف pending خارج القفل (NF-01) | التنظيف داخل `_pending_path_lock` (TSK-301) | server.py |
| **Error visibility** (P1e) | `except: pass` صامت في قراءة الملف المكتشف | إطار `warning` للواجهة + log (TSK-305) | `_dispatch_chat_message` |

### R1.3 — أثر حجمي وهيكلي

- `server.py`: 2,613 → **2,823** سطرًا (+210 عبر M1–M5) — الاتجاه التمركزي مستمر (SR-3 → يُقيَّم في R3/R8).
- `static/app.js`: 3,723 → **3,798** — أول تفكيك جزئي بدأ (`static/js/stream_render.js` وحدة مستقلة).
- بنية التبعيات: لا دورات جديدة (الوحدات الجديدة إما leaf أو تعتمد نزولًا فقط) — NF-24 يبقى صالحًا.
- **خلاصة R1-delta**: كل تغييرات M1–M5 من نوع Wrap/Extend — لا انحراف عن خريطة P1f؛
  ARCHITECTURE_REVIEW.md يبقى مرجعًا صالحًا مع هذا الملحق.

---

## R2 — Strengths Register ✅ (Session 25 — 2026-07-28)

> المصادر: PRODUCT_VISION §3 (Verified Foundation) + NEW_FINDINGS (الإيجابيات المسجلة)
> + مكاسب M1–M5 المتحققة في R1-delta. كل صف يحمل «لماذا يبقى» — هذه مكونات
> **محمية**: أي مهمة مستقبلية تمسها تُعامل كـ Replace وتتطلب Engineering Alternatives.

| # | Component | Location | Why it stays (الدليل) |
|---|---|---|---|
| S-01 | **ApprovalGate — نقطة الطفر الوحيدة** | حلقة consent→preview→apply (PRODUCT_VISION §3.1, FINDING-2) | جوهر هوية المنتج (Filter F1)؛ mutation بلا مراجعة *مستحيل معماريًا* لا مجرد UI؛ مدعوم بـ grep gate على ws.send الواحد |
| S-02 | **CheckpointManager + rollback frames + run-history** | `core/checkpoint.py` (كتابة ذرية L401) | ضمانة undo — الركن الثاني للثقة؛ CP-2 أكد أن المنافسين اعتمدوا النمط ذاته |
| S-03 | **محرك سياق حتمي بسبع مصادر وميزانية بايتية** | `context/` + goldens byte-exact (PRODUCT_VISION §3.2) | Determinism قبل الذكاء (F2)؛ الـ goldens عقد الصدق — أي تحسين سياق يمر عبرها |
| S-04 | **SafeReader — بوابة قراءة وحيدة لسياق الموديل** | `context/safe_reader.py:L2–12` + كشف entropy L86–120 | حاجز تسرب أسرار مركزي؛ مفروض ببوابة test_safe_reader_routing |
| S-05 | **حواجز path traversal** | `resolve_workspace_path(allow_symlinks=False)` — `chain/path_policy.py:L51` + denylists L14–23 + `server.py:L2243–2280` | إيجابي مسجل C4 (NF-positives)؛ لا كود قصّ مقاطع — تطبيع وتصديق صحيح |
| S-06 | **الكتابة الذرية الموحدة** | tmp+fsync+`os.replace` في كل مواضع الكتابة (NF-19: executor.py:L555، checkpoint.py:L401…) | إيجابي C4 — يمنع فساد الملفات عند الانقطاع؛ نمط يُحتذى لأي كتابة جديدة |
| S-07 | **صفر دورات استيراد + انضباط الطبقات** | 82 موديول، AST-verified (NF-24)؛ `core/execution.py:L37` «core stays dependency-free of chain» | يبقى FD-3 baseline؛ الوحدات الجديدة (M1–M5) حافظت عليه |
| S-08 | **أسطول 21 وكيلًا كبيانات محكومة** | `manifest.yaml` + allowlist + verify-step + timeout/output caps (PRODUCT_VISION §3.4) | Governed autonomy (F3)؛ يتفوق بنيويًا على rules-as-text عند المنافسين (CP-3) |
| S-09 | **سطح plugins محدود القدرات** | capability-limited context مفروض بـ grep gates في CI (FINDING-6) | يمنع أي escape hatch؛ شرط FD-6 |
| S-10 | **ذاكرة مشروع بمنشأ وملكية** | JSONL + provenance + staleness + Memory Panel (PRODUCT_VISION §3.3) | glass-box (§11.3) — نقطة تفوق على ذاكرة المنافسين المعتمة (CP-9) |
| S-11 | **نظام جودة check.sh متعدد الطبقات** | mypy → grep gates → AST lints → color lint → 1709 اختبارًا + goldens | البنية التي سمحت بتنفيذ 19 TSK بلا كسر سلوك واحد (سجلات S7–S23) |
| S-12 | **عقد مزود typed + config-switched scale** | provider contract/pool/budget (حدوده OUT OF SCOPE لكن وجوده أصل) + planner/backend/dispatch كمفاتيح config | model-source independence (BET-3)؛ single-process-first (F4) |
| S-13 | **مكاسب M1–M5 الجديدة** | mode-aware parser (S-قفل BUG-01)، `_apply_batch` golden-locked، ContextBudget موحّد، Zip-Slip guard، `IGNORED_DIRS` موحّدة، SearchService، stream_render.js، fence_attached، force_approval | كلها مقفولة ببوابات اختبار خاصة (QA-T05→T13 + بوابة TSK-502) — التراجع عنها ينكشف آليًا |
| S-14 | **Arabic-first + local-first** | واجهة وسجلات ونسخ عربية أصيلة؛ ملفات وجلسات على جهاز المستخدم | الهوية السوقية (BET-2, F5)؛ لا يمس بأي refactor واجهة |

**قاعدة الحماية**: المهام في Stage 3 تُفحص ضد هذا الجدول في Behavior-preservation
pre-check؛ أي مساس بـ S-01…S-14 يستوجب بديلًا موثقًا وخطة rollback.

---

## R3 — Subsystem Map + Architecture Scorecard ✅ (Session 25 — 2026-07-28)

> الأساس: خريطة P1a + مخاطر P1g (g1–g12) مُحدّثة بأثر M1–M5 (R1-delta) —
> مستوى المؤشرات فقط؛ الغوص العميق مفوَّض لـ R4–R10 حسب الأعلام.
> **حالة مخاطر P1g بعد التنفيذ**: g2 ✅(TSK-201) · g3+g4 ✅(TSK-203) · g7 ✅(TSK-501) ·
> g8 ✅جزئيًا (Zip-Slip TSK-105 + راية TSK-502؛ REST بلا auth باقٍ موثقًا) ·
> g10 ✅(TSK-402) · g11 ✅(TSK-202) · **الباقي مفتوحًا: g1 (تفاقم)، g5، g6 (جزئي)، g9 (بالتصميم)**.

### Subsystem Map + Scorecard

| Subsystem | Location | Health / Flags | → Delegated | Score /10 |
|---|---|---|---|---|
| Core runtime (AppContext/Registry/EventBus/Checkpoint) | `core/` | سليم — typed، صفر دورات، تقليم tickets بعد TSK-303 | R5 (تحقق delta) | **8.5** |
| Server composition (routes+WS+frames) | `server.py` | **g1 مفتوح ومتفاقم** (2,613→2,823)؛ god-module = أكبر سطح تغيير مشترك؛ g5 dual-state REST-globals vs WS-SessionContext | R8 (خطة تفكيك تدريجي) | **5.5** |
| WS lifecycle & dispatch | server.py ws_handler + SessionContext | حلقة متزامنة (g6) — المسارات الثقيلة مُخيَّطة و_apply_batch تحت ticket بعد TSK-304؛ يبقى أي handler جديد غير مخيَّط خطرًا نمطيًا | R5/R7 | **7** |
| Chain system (bridge/executor/agent_loop/router) | `chain/` (8,892 سطرًا) | أكبر subsystem؛ لم يُشرَّح دقيقًا في v4.1 (تركيزها server.py)؛ allowlist+verify-step قائمان | **R4-AgentSafety + R7** (أولوية الغوص) | **7 (ثقة أدلة أدنى)** |
| Context engine | `context/` | قوي — goldens + budget + SafeReader + SearchService الجديدة | R6 (زمن retrieval) | **8.5** |
| Actions (parser/file/cmd/session) | `actions/` | mode-aware بعد TSK-101؛ ذرية الكتابة C4؛ force_approval بعد TSK-502 | R4 (سطح الأوامر) | **8** |
| Runners contract | `runners/` | عقد موحّد run(request,ticket,sink) + contracts tests | R7 | **8** |
| Sessions & retention | `sessions/` | append-only + بصمة مشروع + GC | R5 | **8** |
| Frontend | `static/` (app.js 3,798) | أحادية الملف (FD-7)؛ تحسّنت (stream_render, backoff)؛ لا diff panel (فجوة Phase 9 — FINDING-11) | R9 | **6** |
| Prompts & injection surface | `prompts/` + fence_attached | مسيَّج بعد TSK-404؛ يبقى سطحًا حساسًا بطبيعته | R4 | **7.5** |
| Security posture (in-scope) | path_policy/SafeReader/approval/zip-guard | حواجز C4 إيجابية + إصلاحات M1/M5؛ **REST/WS بلا auth (موثق NF-16/README)** — مقبول لـ 127.0.0.1 فقط | R4 | **7** |
| Testing infra | `tests/` (1709) + check.sh | أقوى أصل هندسي؛ 4 فشل موروث خارج الخطط السابقة | R10 (تصفية الموروث) | **8.5** |
| Observability (AI-runtime) | — | **شبه غائبة**: لا قياس prompt-tokens/latency/steps-per-task (SR-4) | **R6 (فجوة رئيسية)** | **3** |
| Workspace/git integration | server.py endpoints | موجود وظيفيًا؛ لم يُعمَّق في v4.1 | R5/R8 | **UNKNOWN → يُثبَّت في R5/R8** |

### أعلام موجَّهة للمراحل التالية (مرتبة بالمخاطرة)
1. **R6**: observability فجوة بنيوية (score 3) — «الغياب نفسه finding».
2. **R8**: خطة g1 — تفكيك server.py تدريجي (Wrap→Extend، لا rewrite — F6).
3. **R4**: مصفوفة Agent-Safety على chain/ (أدنى كثافة أدلة تاريخية).
4. **R9**: فجوة الإظهار (SR-1) — diff panel/plan-artifact/سرد الجلسة (CP-1/CP-8).
5. **R5**: g5 dual-state + g6 النمطي — سيناريوهات فشل ملموسة.

*(نسخة الـ Scorecard مثبتة في PROGRESS.md — تُعاد الحسبة بعد كل milestone.)*

---

## R4 — Security Findings + Agent Safety Findings
*(TODO — يبدأ من NF-16/TSK-502 كحالة VERIFIED ويكمل مصفوفة Agent-Safety.)*

---

## R5 — Reliability Findings (Delta)
*(TODO)*

---

## R6 — Performance Findings + Baseline Metrics
*(TODO — Baseline الاختبارات مسجل في R-1؛ AI-runtime metrics تُقيَّم هنا.)*

---

## R7 — Runtime Pipeline
*(TODO)*

---

## R8 — Code Quality Findings (Delta)
*(TODO)*

---

## R9 — UX Findings + Agentic Capability Matrix
*(TODO)*

---

## R10 — Testing Gaps + Documentation Gaps (Delta)
*(TODO — يبدأ من QA_MASTER_PLAN + RELEASE_READINESS_REPORT.)*
