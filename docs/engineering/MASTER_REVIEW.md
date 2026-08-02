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

## R4 — Security Findings + Agent Safety Findings ✅ (Session 26 — 2026-07-28)

**منهجية:** (أ) ترحيل حالات الأمن الكلاسيكي NF-15..18 لدورة الحياة الجديدة بعد
إصلاحات M1/M4/M5؛ (ب) Agent Safety Review مُهيكل — أول تشريح كامل لطبقة
الوكيل: قراءة كاملة لـ `chain/agent_tools.py` (768 سطر)، `chain/agent_loop.py`
(585)، `chain/path_policy.py` (120)، `chain/plugin_registry.py` (180)،
`core/approval.py` §ApprovalGate (L139–286)، `chain/bridge.py` §`_gated_apply`
(L502–588)، `chain/knowledge.py` §ToolResult/render (L25–70, L160–215).

### R4.1 — ترحيل حالة الأمن الكلاسيكي (NF-15..18)

| # | الاكتشاف | الحالة الجديدة | الدليل |
|---|---|---|---|
| NF-15 | Zip-Slip في استعادة الباك-أب | **VERIFIED-FIXED** (TSK-105) | `server.py:1030` `_zip_member_violations` — فحص الأعضاء قبل الفك موجود ومُختبر (M1) |
| NF-16 | REST بلا auth + `need_approval=False` | **MITIGATED** (TSK-502) — خطر متبقٍ مقبول | `server.py:172` `_force_command_approval` + `config.yaml:25` `force_command_approval: false` (افتراضي localhost) — التفعيل إلزامي عند أي ربط خارج 127.0.0.1 (موثق في config.yaml:19–24). القرار المتبقي منتجي: هل يُفعَّل افتراضيًا؟ → يُرحَّل لـ PLANNING |
| NF-17 | ادعاء A6 قصّ المسارات | **CLOSED** (غير مُعاد إنتاجه) | تتبّع ساكن كامل في NF-17 نفسه؛ لا دليل runtime جديد |
| NF-18 | حقن خام في البرومبت | **[SUPERSEDED → مُقسَّم]**: مسار templates **VERIFIED-FIXED** (TSK-404)؛ مسار حلقة الوكيل **مفتوح** → ASF-01 أدناه | `prompts/templates.py:39` `fence_attached` موجود ويُستخدم في مسار build_prompt فقط؛ grep مؤكد: **صفر** استخدام في `chain/agent_loop.py` / `chain/knowledge.py` / `chain/context_builder.py` |

**إيجابيات مؤكدة بقراءة كاملة هذه الجلسة** (ترقية من spot-check إلى VERIFIED):
- `chain/path_policy.py` سليم بنيويًا: احتواء قاطع (`relative_to` L88–95 + فرع
  Windows case-insensitive L80–87)، denylist أسرار متعدد الطبقات (أسماء L14–17،
  امتدادات L18–20، مجلدات L21–23 مع فحص كل مقاطع المسار L41–47، واستثناء
  `.env.example` الوحيد L30–31)، فحص symlink تصاعدي L98–109.
- `ApprovalGate` fail-closed بالكامل: timeout ⇒ deny (`approval.py:261–262`)،
  deny mode ⇒ رفض فوري (L190–191)، `resolve()` يشترط تطابق request_id
  **و** payload_hash معًا (L214–221) — لا قبول ردود قديمة/مزوّرة، وفشل قناة
  الإشعار لا يعلّق البوابة (L250–254) بل ينتهي برفض المهلة.

### R4.2 — Agent Safety Findings (ASF)

| ID | المحور | الخطورة | الوصف | الدليل |
|---|---|---|---|---|
| ASF-01 | Context poisoning | **C3/S3 — الأعلى في R4** | نتائج الأدوات (محتوى ملفات/مخرجات أوامر/نتائج بحث) تُحقن في برومبت المتابعة **بلا تسييج**: `[نتيجة {tool}...]:\n{نص خام}` — ملف بالمشروع يحوي تعليمات عدائية يقودها الموديل في التكرار التالي. نفس النمط في knowledge: `to_summary()` و`_render_body()` يركّبان المحتوى الخام حرفيًا. إصلاح NF-18 (fence_attached) غطّى مسار templates فقط | `agent_loop.py:224–226, 256–259, 350–381`؛ `knowledge.py:41–49, 191–205`؛ `templates.py:39` (الدالة موجودة وغير مستدعاة من هذه المسارات) |
| ASF-02 | Approval bypassability | C3/S3 | بوابة الموافقة على `run_command` **موضعية لا بنيوية**: `tool_run_command` ينفّذ داخليًا بـ `need_approval=False` (agent_tools.py:485) — الفرض يقع في AgentLoop فوقه (L466–522). أي مسار مستقبلي ينادي `AgentTools.tool_run_command` مباشرة (REST جديد، plugin، اختبار مدمج بالخطأ) يتجاوز الموافقة كليًا. TSK-502 خفّف مسارات REST الحالية لكن الثغرة البنيوية باقية | `agent_tools.py:432–538`؛ `agent_loop.py:466–479` (بلا gate ⇒ رفض آمن — لكن فقط لمن يمر عبر الحلقة) |
| ASF-03 | Rollback coverage | C4/S3 | سقف snapshot ما-قبل-الأمر: `_CKPT_MAX_FILES=400` و512KB/ملف — أمر معتمد يلمس >400 ملف أو ملفات أكبر لا يُلتقط أثره كاملًا ⇒ rollback جزئي صامت بعد موافقة المستخدم (المستخدم وافق على الأمر، لا على فقدان قابلية التراجع) | `agent_tools.py:464–537` (caps + snapshot/seal T-059) |
| ASF-04 | Dangerous command detection | C4/S4 (إيجابي غالبًا) | `CommandPolicy.resolve()` تطابق **حرفي تام** — لا prefix matching ولا حقن معاملات؛ لكن `enforce=False` هو الافتراضي البرمجي (وضع legacy عند حذف allowlist من config) ⇒ الحماية config-dependent لا code-default. config الحالي يفعّلها (allowlist بأربعة أوامر ثابتة) | `agent_tools.py:51–119`؛ `config.yaml:36–37, 57–62` |
| ASF-05 | ApprovalGate concurrency | C4/S4 | نموذج طلب-معلّق-واحد: طلبان تفاعليان متزامنان (chain + agent مثلًا) — الثاني يكتب فوق `_pending_id` للأول (L242–247)، فيستحيل حلّ الأول ⇒ يموت بمهلة 60s. fail-closed (لا موافقة خاطئة) لكنه استنزاف موافقات صامت | `approval.py:170–175, 238–247` |
| ASF-06 | Parsing robustness | C4/S4 | `_parse_args_body` تفكيك key:value ساذج — قيمة تحوي `\n` أو سطر يشبه مفتاحًا تُفسَّر خطأ؛ مدخله مخرج موديل عدائي محتمل (يتقاطع مع ASF-01: حقن بالسياق → توليد TOOL block مشوّه). `parse_tool_calls` نفسها fence-aware (تتجاهل بلوكات داخل ```) — جيد | `agent_tools.py` §parse (fence-awareness مؤكد بالقراءة الكاملة) |
| ASF-07 | path_policy edge | C4/S4 | حلقة فحص symlink تبتلع كل الاستثناءات (`except Exception: pass` L107–108) — خطأ FS أثناء `is_symlink()` ⇒ تخطٍّ صامت للفحص؛ ونافذة TOCTOU نظرية بين resolve والفحص. الاحتواء النهائي (`relative_to` على المسار المحلول) يبقى الخط الصلب | `path_policy.py:98–109` |
| ASF-08 | Plugin capability scope | C4/S4 (مقبول موثَّق) | `discover()` ينفّذ كود الإضافة فعليًا (import + `build()` dry-run) وقت الاكتشاف — تثبيت حزمة = ثقة كاملة بها (نموذج Python القياسي). التعويضات قوية: PluginContext حصري (لا file_manager/جلسات/خادم)، بوابة 3 مراحل مع حجر صحي، وأول-اسم-يفوز ضد التبديل الصامت | `plugin_registry.py:115–157, 163–175`؛ `plugin_api.fixture_context` |

### R4.3 — حكم المحاور الستة

| المحور | الحكم | الأساس |
|---|---|---|
| Tool permission boundaries | **قوي** | فصل صريح SAFE/APPROVAL (`agent_tools.py:37–40`)؛ كل مسارات الملفات عبر `resolve_workspace_path(allow_symlinks=False)` (L603–613)؛ plugins معزولة بـ PluginContext |
| Autonomous action limits | **قوي** | MAX_ITERATIONS=8، TOOL_RESULT_MAX_LEN=3000، سقف مخرجات 8000، timeout 60s، retries=0، إلغاء تعاوني 0.05s polling — كل الحدود ثابتة بالكود |
| Approval bypassability | **متوسط** | البوابة نفسها fail-closed ومحصّنة بـ payload_hash، لكن الفرض موضعي (ASF-02) وأحادي-الطلب (ASF-05) |
| Dangerous command detection | **جيد مشروط** | allowlist تطابق-تام ممتاز، لكنه config-dependent (ASF-04) + `force_command_approval:false` افتراضيًا (NF-16 المتبقي) |
| Context/memory poisoning resistance | **ضعيف — الفجوة الرئيسية** | ASF-01: مسار حقن غير مسيَّج كامل في قلب الحلقة؛ `remember_fact` يسجّل provenance (run_id/index_hash/fingerprint) لكن نص الحقيقة نفسه يدخل البرومبت خامًا |
| Goal drift | **مقبول** | سقف 8 تكرارات + `_verification_instruction` عند توفر أوامر تحقق بالـ allowlist؛ لا إعادة-تثبيت هدف لكل تكرار (تحسين محتمل، ليس خطرًا) |

**خلاصة R4:** الأمن الكلاسيكي ما-بعد M1/M4/M5 في حالة جيدة (NF-15 مُصلح،
NF-16 مخفَّف بقرار منتجي مؤجل، NF-17 مغلق). فجوة الوكيل الأهم هي **ASF-01**
(تسييج نتائج الأدوات — امتداد مباشر لعلاج NF-18 على المسار الثاني)، تليها
**ASF-02** (نقل فرض الموافقة لطبقة الأداة نفسها). كلاهما مرشح P1 في PLANNING.

---

## R5 — Reliability Findings (Delta) ✅ (Session 26 — 2026-07-28)

**منهجية:** ترحيل حالات NF-01..14 (فئات a–g القديمة) بعد M1–M4، ثم دلتا كود
موجَّهة حيث تغيّر السلوك فقط: `server.py` (§pending_path L108–123، §_apply_batch
L2415–2462، مواقع التخييط L1662/L1818/L2294، دفعة L2081)، `core/execution.py`
(§purge_terminal L351+، §reap_stale L322)، `chain/bridge.py` (§حالة الركض
L236/294–299/364/403/512). لا إعادة قراءة لما غطّته R4.

### R5.1 — ترحيل حالات الاعتمادية (NF-01..14)

| # | الاكتشاف | الحالة الجديدة | الدليل |
|---|---|---|---|
| NF-01 | تنظيف pending_path خارج القفل | **VERIFIED-FIXED** (TSK-301) | `server.py:108–123` — الطوفان والحذف داخل القفل، موثّق بالعقد في docstring |
| NF-02 | خانة run عالمية (project_id="") | **FIXED** (TSK-302, S14) | أرشيف PROGRESS §TASK TABLE |
| NF-03 | ازدواجية REST-globals/WS-SessionContext (g5) | **مفتوح — مقبول موثَّق** | globals قائمة (`server.py:128–133`)؛ g5 open في R3؛ قرار توحيد → PLANNING (P4 قديمًا) |
| NF-04 | apply يحجب حلقة WS (g6) | **[SUPERSEDED → مُقسَّم]**: الإلغاء **FIXED** (TSK-304)؛ الحجب **باقٍ** → RF-01 | `server.py:2430–2462` (ticket + checkpoint) لكن L2081 نداء مباشر داخل الحلقة |
| NF-05 | خيوط daemon بلا join عند الإيقاف | **مفتوح — ملاحظة معمارية** (P7) | التخييط قائم L1662/1818/2294 `daemon=True`؛ الكتابة الذرية (NF-19) تخفف أثر الملف الواحد |
| NF-06 | `_tickets` نمو غير محدود | **VERIFIED-FIXED** (TSK-303) | `core/execution.py:351` `purge_terminal(keep_last=50)` + استدعاء `server.py:406` |
| NF-07 | chat_history بلا حد | **VERIFIED-FIXED** (TSK-104) | `server.py:1436` `select_history(..., _history_payload_policy(cfg))` — بوابة سياسة مسماة لا قصّ خام |
| NF-08 | TTL يعمل عند الإضافة فقط | **مفتوح — أثر ضئيل مقبول** | `_clean_expired_pending_requests` لا يزال يُستدعى من store فقط (docstring L110–111) |
| NF-10 | O(n²) rendering | FIXED (TSK-401) — يُتحقق تفصيلًا في R6/R9 | أرشيف S18 |
| NF-11 | WS reconnect بلا backoff + JSON.parse | FIXED (TSK-402) — يُتحقق في R9 | أرشيف S19 |
| NF-12 | لا scan_start | FIXED (TSK-403) | أرشيف S20 |
| NF-13 | fallback أوامر bash التوضيحية | FIXED (TSK-102 مع BUG-01/TSK-101) | أرشيف S7 |
| NF-14 | ابتلاع استثناءات واسع | **جزئي** (TSK-305 ضيّق الحرجة + log) — المتبقي مواضع مقصودة مُعلَّمة | `server.py:2271–2284` نمط "NF-14 §N (ابتلاع مقصود)" موثّق موضعًا-بموضع |

### R5.2 — اكتشافات دلتا جديدة (RF)

| ID | الخطورة | الوصف | الدليل |
|---|---|---|---|
| RF-01 | **C4/S3** | **بقية g6**: `_apply_batch` يعمل داخل حلقة `ws_handler` مباشرة (النداء الوحيد غير المُخيَّط بين الـ runs الأربعة) — نقاط تفتيش الإلغاء (TSK-304) تعمل، لكن `cancel_run` **من نفس الاتصال** لا يمكن أن يصل أصلًا لأن `ws.receive()` محجوب حتى نهاية الدفعة؛ الإلغاء الفعّال ممكن فقط من تبويب/اتصال آخر. تخييط الدفعة (كما chain/agent/delegate) يكمل العلاج | `server.py:2081` (نداء مباشر) مقابل L1662/L1818/L2294 (`threading.Thread`)؛ checkpoint L2442 |
| RF-02 | C4/S4 | `reap_stale()` **بلا أي مستدعٍ إنتاجي** — آلية TTL/heartbeat للتذاكر اليتيمة (خيط مات بلا `finish`) موجودة ومُختبرة لكنها ميتة تشغيليًا؛ خانة المشروع الحصرية تبقى محجوزة للأبد لو انهار خيط run دون finally (المسارات الحالية كلها finally — الخطر كامن لا فعلي) | `core/execution.py:322–348` (التعريف)؛ grep إنتاجي: الموضع الوحيد `core/backends.py:81` (إعلان بروتوكول) |
| RF-03 | C4/S4 | حالة ركض مزدوجة داخل الجسر: `_active_run` (bridge) موازٍ لتذاكر `ExecutionRegistry` — نسخة مصغّرة من نمط g5 داخل طبقة واحدة. مُخفَّف فعليًا: القراءة النهائية من frozen snapshot لا من `_active_run` (تعليق صريح بالكود)، والتنظيف في finally (L403) | `chain/bridge.py:236, 294–299, 364, 403, 512` |

### خلاصة R5
حصاد M3 (الاعتمادية) صامد: 4/5 إصلاحات VERIFIED بالكود الحالي (NF-01/06/07
+ إلغاء NF-04)، وNF-14 جزئي بنمط توثيق-الابتلاع-المقصود المنضبط. الفجوات
الحية: **RF-01** (تخييط `_apply_batch` — يُكمل TSK-304 فعليًا) مرشح P2،
**RF-02** (تشغيل reap_stale دوريًا — سطر واحد تقريبًا) مرشح P3، g5/NF-03
قرار توحيد معماري يُحسم في PLANNING مع g1 (تفكيك server.py).

---

## R6 — Performance Findings + Baseline Metrics ✅ (Session 27 — 2026-07-28)

**منهجية:** (أ) ترحيل NF-20/21/22 بعد M4/M5 بتحقق كودي مباشر؛ (ب) تسجيل
baseline metrics قابلة للإعادة؛ (ج) جرد أجهزة القياس (instrumentation) للأداء
التشغيلي وأداء الـ AI-runtime — تسجيل الفجوات NOT INSTRUMENTED صراحةً.

### R6.1 — ترحيل حالات الأداء (NF-20/21/22)

| # | الاكتشاف | الحالة الجديدة | الدليل |
|---|---|---|---|
| NF-20 | api_search مسح تسلسلي كامل لكل استعلام | **VERIFIED-FIXED** (TSK-501) | `server.py:696–713` `_search_service` فوق `ctx.project.index` (طازج بخطافات write-through + refresh_if_stale) مع مسار ctx-less مُكاش على fm؛ `context/search.py:1–40` — تعداد المرشحين من الفهرس (صفر مشيات شجرية) + كاش محتوى بمفتاح (mtime_ns,size)؛ معيار قبول QA-T13: <1s على 5k ملف |
| NF-21 | tool_search_code بنفس النمط داخل حلقة الوكيل (A1) | **VERIFIED-FIXED** (TSK-501 — نفس الخدمة) | `chain/agent_tools.py:277–298` `_search_service` — فهرس المقبض الحي أو fallback مُكاش على الأداة نفسها؛ تكافؤ ذهبي موثَّق (نفس صيغة `rel:i: line` + نفس السقوف؛ الفارق الوحيد الموثّق: ترتيب حتمي) |
| NF-22 | O(n²) rendering أثناء البث (=NF-10) | **VERIFIED-FIXED** (TSK-401) | `static/app.js:967–1037` — throttler واحد + memo مقطعي لكل رسالة بدل parse+innerHTML للرد كاملًا مع كل chunk؛ `static/js/stream_render.js` (112 سطرًا) وحدة مستقلة |

### R6.2 — Baseline Metrics (Session 24–27، قابلة للإعادة)

| المقياس | القيمة | طريقة القياس |
|---|---|---|
| مجموعة الاختبارات الكاملة | 1709 اختبارًا: 4 فشل موروث / 1671 نجاح / 34 تخطٍّ، **~82s** | Session 24، `pytest --junitxml` (بيئة sandbox قياسية) |
| زمن استيراد `server` (بارد) | **~949ms** | `python3 -c "t=monotonic(); import server; ..."` — Session 27؛ يشمل سلسلة الاستيراد الكاملة (chain/context/core/actions) |
| حجم الكود المُنتِج (بلا tests/providers-؟ لا — الكل عدا tests) | **29,649 سطر py** خارج tests/؛ الأكبر: server.py 2,823 (g1)، bridge.py 782، agent_tools.py 768، delegate.py 751 | `find -name "*.py" -not -path tests | wc -l` — Session 27 |
| حجم الواجهة | app.js 3,798 + وحدات static/js (\u2248 5,306 سطر إجمالي js) | `wc -l` — Session 27 |
| ملاحظة بيئية | مجلد `improvements/شامل/` يحوي نسخ server.py تاريخية (1670+1100 سطر) — **ليست كودًا حيًّا**؛ تُستثنى من أي قياس (مرشح تنظيف في R8) | جرد Session 27 |

### R6.3 — جرد أجهزة القياس + فجوات NOT INSTRUMENTED

**موجود (تشغيلي):**
- زمن كل خطوة chain: `duration_ms` يُحسب بـ `time.monotonic` ويُبث للواجهة
  (`chain/executor.py:352, 386–425`؛ `chain/bridge.py:107–109`).
- ميزانية الركض: `successful_calls` + `elapsed_seconds` في إطار نهاية الـ chain
  (`chain/bridge.py:153–162, 609`).
- تقدير توكنز السياق **قبل الإرسال**: `ContextBudget` بمقدّر قابل للاستبدال
  (chars/4 افتراضيًا) (`context/budget.py:51–64, 93–116`).

**NOT INSTRUMENTED (فجوات مؤكدة بـ grep شامل على server/bridge/agent_loop/runners):**

| ID | الفجوة | الأثر |
|---|---|---|
| PM-01 | **لا قياس لتوكنز الاستجابة الفعلية** — لا التقاط لـ usage من المزود (الحد الفاصل مبهم per scope)، ولا تقدير محلي للمخرج؛ ContextBudget يقيس المدخل المُرسل فقط | استحالة معرفة كلفة رسالة/جلسة فعليًا؛ أي تحسين ميزانية يبقى بلا حلقة تغذية راجعة |
| PM-02 | **لا قياس لزمن الاستجابة (latency) للطلب المفرد خارج chain** — المسار المباشر (direct) وحلقة الوكيل بلا أي توقيت (grep: صفر monotonic في runners/ وagent_loop عدا expires_at) | أبطأ مسار استخدامًا (chat/agent) هو الأعمى قياسيًا |
| PM-03 | **لا تجميع (aggregation) عبر الزمن** — القياسات الموجودة لحظية تُبث وتُنسى؛ لا سجل runs بمقاييسه، لا p50/p95، لا عدّادات | لا أساس لرصد تدهور الأداء بين الإصدارات |
| PM-04 | **لا قياس لأداء بناء السياق** — الجامع الحتمي ذو الـ 7 مصادر (ContextBuilder) بلا توقيت لكل مصدر | فجوة R6 تتقاطع مع A3 التاريخية (انطباع "تجمّد" قبل أول إطار) |

**حكم:** الأداء التفاعلي المُصلَح في M4/M5 (بحث مفهرس + بث تدريجي) **صامد
بالكود الحالي**. الفجوة البنيوية ليست في سرعة الكود بل في **العمى القياسي**
(Observability=3 في الـ Scorecard): PM-01..04 مرشحة مهمة واحدة مركّبة في
PLANNING («طبقة metrics خفيفة») — منخفضة الخطورة، عالية القيمة التمكينية
(unlocking) لأنها شرط أي تحسين أداء لاحق قابل للإثبات.

---

## R7 — Runtime Pipeline ✅ (Session 28 — 2026-07-28)

**منهجية:** تتبّع رحلة الرسالة end-to-end للمسارات الأربعة. قراءة كاملة:
`runners/direct.py` (128)، `runners/agent.py` (169)، `runners/chain.py` (188)،
`runners/delegate.py` (رأس + عقد الحالة). مقاطع server.py: التوجيه والإرسال
(L1560–1900)، معالجات delegate_approve/reject (L2312–2368)، ws_handler
(L2385–2403)؛ الواجهة: معالجات delegate (app.js:615–637, 3279+). المزود نفسه
حد مبهم (out of scope) — يُتتبع حتى `stream_fn`/`send_fn` فقط.

### R7.1 — خريطة المسارات الأربعة

| المرحلة | direct | chain | agent | delegate |
|---|---|---|---|---|
| السياق | `gather_message_context` (ContextBudget — TSK-103) | نفسه + file_content/files للراوتر | نفسه + `_payload_history` (TSK-104) | **جمع خاص**: scan + قراءة أول 10 ملفات كاملة (L2265–2284) — خارج ContextBudget → RP-03 |
| التذكرة | `_begin_run_ticket("direct")` | "chain" | "agent" | "delegate" |
| التخييط | **داخل حلقة WS** (L1846–1858، بلا Thread) → RP-02 | Thread (L1662) | Thread (L1818) | Thread (L2294) |
| العمل | `stream_fn` قطعًا مع فحص إلغاء بين كل قطعة | `bridge.start_chain` + join(600s) | `AgentLoop.run` (أدوات + بوابة) | Brief→Implement→Review + checkpoints إلغاء |
| الحسم | parse(mode) → إطار `plan`/`done` — التطبيق يدويًا عبر `_apply_batch` | `_gated_apply` عبر ApprovalGate (R4) | نفس direct بعد الحلقة (L1786–1815) + بوابة run_command داخل الحلقة | review → `waiting_approval` → `delegate_approve` → **RP-01 (مكسور)** |
| التذكرة تُنهى | Runner._finish | الجسر (finally) + Runner (لا-عملية) | AgentLoop + Runner (لا-عملية) | land()/reject() حصريًا (waiting_approval يُبقيها حية) |

**إيجابي بنيوي (يُضاف للـ Strengths):** عقد Runner موحّد حرفيًا عبر الأربعة —
`started → [إلغاء] → بوابة إن وُجدت proposed_actions → [إلغاء] → عمل →
finished + ticket.finish` مع "لا استثناءات للخارج" (بند 4) وإنهاء تذكرة
لا-عملية آمن عند التكرار. تناظر الكود بين الملفات الأربعة شبه حرفي.

### R7.2 — Runtime Pipeline Findings (RP)

| ID | الخطورة | الوصف | الدليل |
|---|---|---|---|
| RP-01 | **C4/S2 — مكسور مؤكد** | `delegate_approve` ينادي `parser.extract_actions(...)`/`extract_options(...)` — **الدالتان غير موجودتين** على ResponseParser (تحقق runtime: `hasattr` = False؛ grep: لا تعريف في أي وحدة حية — الاستدعاءان الوحيدان هما هذان). AttributeError يُبتلع في `except Exception` (NF-14 §15) → **كل اعتماد تفويض يسقط للـ fallback**: `done` بـ actions=[] دائمًا. رد المنفّذ يُعرض كنص لكن أفعاله لا تتحول أبدًا لعناصر قابلة للتطبيق — دورة delegate كاملة بلا مخرج عملي. الإصلاح الظاهر: `parser.parse(response, mode=...)` ثم التحويل كما في مسار agent L1791–1800 | `server.py:2337–2338`؛ `actions/response_parser.py:65–107` (parse فقط)؛ فحص hasattr مباشر Session 28 |
| RP-02 | C4/S3 | direct هو المسار **الوحيد غير المُخيَّط** — `runner.run()` يعمل داخل حلقة `ws.receive()` نفسها: طوال البث لا تُستقبل أي رسالة (cancel_run من نفس التبويب مستحيل — نفس عائلة RF-01، والمسارات الثلاثة الأخرى مُخيَّطة) | `server.py:1846–1858` (نداء متزامن) مقابل L1662/L1818/L2294 |
| RP-03 | C4/S4 | جمع سياق delegate يتجاوز ContextBudget: قراءة كاملة لأول 10 ملفات من scan (بلا سقف حجم للملف الواحد ولا ميزانية إجمالية) — الجيب الوحيد الباقي خارج توحيد TSK-103 (BUG-03) | `server.py:2265–2284` |
| RP-04 | C4/S4 | فرع `proposed_actions` في الـ runners الأربعة (موافقة مسبقة قبل العمل) **خامل إنتاجيًا** — كل مواقع بناء RunRequest في server.py لا تمرر proposed_actions؛ الفرع مغطى اختباريًا فقط (RunnerContractMixin). ليس عيبًا — لكنه سطح عقد يُصان بلا مستهلك، ويجب ألا يُحسب كطبقة أمان فعلية عند تقييم المسارات | `runners/*.py` (كتلة الموافقة المتناظرة)؛ مواقع RunRequest: `server.py:1652, 1754, 1849, 2297` تقريبًا — كلها بلا proposed_actions |

### R7.3 — نقاط التسليم الحرجة (خلاصة تقاطعية)

1. **التسليم للموديل**: direct/agent عبر `build_prompt`/`_build_*_prompt` —
   المسار المسيَّج (TSK-404) هو templates فقط؛ حقن حلقة الوكيل غير مسيَّج
   (ASF-01، مثبّت في R4).
2. **التسليم من الموديل**: ثلاثة محلّلات مختلفة فعليًا — `parser.parse(mode)`
   (direct/agent، مضبوط بـ TSK-101)، `get_parsed_actions` (chain داخل
   `_gated_apply`)، والمسار المكسور (delegate — RP-01). توحيد نقطة parse
   مرشح طبيعي ضمن تفكيك g1.
3. **التسليم للكتابة**: موحّد فعليًا — `_apply_batch` (يدوي) و`apply_step`
   (chain) كلاهما فوق checkpoint (T-054/T-059)؛ لا مسار كتابة ثالث ظهر.

**خلاصة R7:** البنية التحتية للمسارات (عقد Runner + تذاكر + بوابة) متينة
ومتناظرة؛ العيوب المكتشفة كلها في **حواف التسليم**: RP-01 عطل وظيفي صريح
(مرشح P1 — إصلاح صغير عالي الأثر)، RP-02 يكمل عائلة RF-01 (مهمة تخييط
واحدة تغلق الاثنين)، RP-03 يغلق آخر جيب خارج ميزانية السياق.

---

## R8 — Code Quality Findings (Delta) ✅ (Session 28 — 2026-07-28)

**منهجية:** (أ) ترحيل NF-23/24 بإعادة فحص آلي؛ (ب) تشخيص g1 (server.py)
بنيويًا + خطة تفكيك لـ PLANNING (لا تنفيذ)؛ (ج) حالة بوابات الجودة الفعلية.

### R8.1 — ترحيل حالات الجودة

| # | الاكتشاف | الحالة الجديدة | الدليل |
|---|---|---|---|
| NF-23.1 | بلوكا apply متطابقان | **VERIFIED-FIXED** (TSK-201) | `server.py:2076–2081` — مسار واحد `_apply_batch` مقفول بـ golden |
| NF-23.2 | MAX_SMART_FILE_SIZE مكرر | **VERIFIED-FIXED** (TSK-203) | `server.py:137–139` — تعريف وحيد + تعليق يوثق الإزالة |
| NF-23.3 | قراءة config في 6 مواضع | **VERIFIED-FIXED** (TSK-203) | `server.py:142–150` — قارئ موحّد مُكاش |
| NF-23.4 | ثلاث قوائم تجاهل غير متزامنة (BUG-04) | FIXED (TSK-202) | أرشيف S11 — `core/ignore_rules.py` موجود (تحقق R1) |
| NF-24 | صفر دورات استيراد | **VERIFIED — أُعيد الفحص Session 28** | فحص AST آلي: 81 موديول (استبعاد tests/providers/static/improvements) — **0 دورات** |

### R8.2 — بوابات الجودة الفعلية (scripts/check.sh)

11 بوابة فعّالة: mypy (providers+chain+core+context+sessions — **خضراء الآن**:
"no issues in 59 files"، تحقق Session 28)، SafeReader boundary، strategy
vocabulary، routing thresholds، ws.send boundary، handler state lint، rglob
ban، color tokens، plugin capability، pytest، بوابة إضافية. الملاحظ: البوابات
grep-مبنية هشة اسميًا لكنها موثقة بأرقام مهام — نمط منضبط. **فجوة**: server.py
وactions/ وrunners/ **خارج بوابة mypy** (`scripts/check.sh:12`) — أكبر ملف في
المشروع بلا فحص types.

### R8.3 — تشخيص g1: server.py (2,823 سطرًا) — خطة تفكيك (لـ PLANNING)

**قياس بنيوي (Session 28):** 27 REST route، 16 فرع `elif msg_type`، وكتلتان
عملاقتان تحملان ثلث الملف:
- `_dispatch_chat_message` — **~477 سطرًا** (L1439–1915): كشف مسار + جمع سياق
  + توجيه ذكي + 3 مسارات إرسال (chain/delegate/agent) + مسار direct كامل.
- `_handle_ws_message` — **~469 سطرًا** (L1916–2384): راوتر 16 نوع رسالة.
- `main()` — ~281 سطرًا (L2542+): تجميع الحقن.

**البذور الموجودة أصلًا (تخفض مخاطرة التفكيك):** وسطاء الإطارات الوحدويون
النقيون (`_list_runs_frame`/`_cancel_run_frame`/`_memory_*_frame` — نمط T-016
المعلن)، عقد Runner الموحّد، `_config()` الموحّد، SessionContext يحمل حالة
الاتصال. **الالتصاق الباقي:** globals (`fm`/`cmd_runner`/`chat_history` —
NF-03/g5) هي ما يمنع اقتطاع REST blueprints نظيفًا.

**خطة مقترحة (تسلسل يحترم الأمان السلوكي):**
1. **QG-01**: اقتطاع راوتر WS — جدول `msg_type → handler(ctx, sctx, msg)`
   (mechanical: كل فرع elif دالة) — لا تغيير سلوكي، goldens تحمي الإطارات.
2. **QG-02**: اقتطاع مسارات الإرسال الأربعة من `_dispatch_chat_message` إلى
   وحدة `dispatch/` (كل مسار دالة بواجهة sctx+RunRequest) — يتقاطع مع علاج
   RP-02 (تخييط direct) فيُنفَّذان معًا.
3. **QG-03**: REST blueprints — **مؤجل بعد قرار g5** (توحيد globals مقابل
   SessionContext) لأن الاقتطاع قبله يجمّد الازدواجية في الواجهات.
4. **QG-04**: ضم server.py (بعد 1+2) وactions/ وrunners/ لبوابة mypy.

### R8.4 — اكتشافات جديدة (QF)

| ID | الخطورة | الوصف | الدليل |
|---|---|---|---|
| QF-01 | C4/S4 | `improvements/` (892KB) داخل الشجرة: نسخ server.py تاريخية (1670+1100 سطر) + تقارير نصية — تلوث نتائج grep/wc وتربك أي أداة تحليل؛ ليست كودًا حيًّا (صفر imports إليها) | جرد Session 27–28؛ `du -sh` = 892K |
| QF-02 | C4/S4 | فجوة بوابة mypy: server.py/actions/runners خارج الفحص — الأخطاء البنائية مثل RP-01 (نداء دالة غير موجودة) كانت ستُلتقط لو شملت البوابة server.py (`parser.extract_actions` على كائن معلوم النوع) | `scripts/check.sh:12`؛ RP-01 كدليل حي على الكلفة |

**خلاصة R8:** ديون M2 (الاتساق) مسددة بالكامل ومُتحقَّقة؛ صفر دورات استيراد
صامد. الدين الأكبر الباقي هو g1 نفسه، وخطته أعلاه جاهزة للـ PLANNING بترتيب
مخاطرة صريح (QG-01→04). QF-02 يعطي مبررًا قياسيًا قويًا لـ QG-04: عيب
runtime-مكسور (RP-01) كان قابلًا للالتقاط الساكن.

---

## R9 — UX Findings + Agentic Capability Matrix ✅ (Session 29 — 2026-07-28)

> **المنهج**: استهلاك أحكام CP-1..9 من §R0 ومقاطعتها مع الواقع المؤكد من
> R4–R8 (بلا إعادة قراءة واسعة — greps مصوَّبة فقط لمواقع الربط UI/plan/memory).
> مدخلات: PRODUCT_VISION Pillars/Filters (R0)، RP-01..04 (R7)، NF-10/11/12
> المُرحّلة (R5/R6)، علم R3 السطر 284 (فجوة الإظهار SR-1).

### R9.0 — تصحيح نطاق SR-1 (فجوة الإظهار) — أضيق مما سُجّل

علم R3 (§R3، سطر 284) ذكر الفجوة كـ«diff panel/plan-artifact/سرد الجلسة».
التحقق المباشر هذه الجلسة يُظهر أن **لوحة diff موجودة فعلًا**:
- `static/app.js:428` — T-065 (R-901): «لوحة مراجعة الـ diff لطلبات الموافقة».
- `static/app.js:1689–1717` — DOM glue فوق وحدة نقية `static/js/diff_panel.js`
  (`diffPanelState = DiffPanel.openState(frame, oldContents)`)، مع حساب diff
  حقيقي من المحتوى القديم لكل write/delete.

⇒ فجوة SR-1 الفعلية تنحصر في عنصرين: **(1) الخطة-كـartifact تفاعلي** و
**(2) سرد الجلسة** — لوحة diff لكل طلب موافقة **ALREADY-HAVE**. لا يُحذف نص
R3؛ هذا تضييق مُثبت بالدليل.

### R9.1 — استهلاك أحكام CP-1..9 × الواقع المؤكد (R4–R8)

| CP | حكم R0 | الواقع المؤكد الآن | حكم R9 النهائي |
|---|---|---|---|
| CP-1 Plan Mode | ADOPT-CANDIDATE | الخطة تُبث كإطار `plan` (`server.py:1898–1904` للمسار المُوجَّه؛ `server.py:1804–1810` لمسار agent) وتُعرض بطاقة `showPlanCard` (`static/app.js:3099–3128`) — لكن البطاقة **قائمة قراءة فقط** بأربعة أزرار (نفّذ/حدّث/راجع/إلغاء): لا تحرير لخطوة، لا تعطيل خطوة، لا إعادة ترتيب | **ADOPT** — مهمة PLANNING: ترقية بطاقة الخطة إلى artifact تفاعلي (per-step toggle/edit) فوق الآلية القائمة؛ امتداد Extend لا انعطاف |
| CP-2 Checkpoints | ALREADY-HAVE | مؤكد: RunHistory UI (`static/app.js:3391–3420`) فوق `/api/rollback/history` + أمرا WS `rollback_run/rollback_file` (T-054) | **ALREADY-HAVE — مُغلق** (فجوة الإظهار المتبقية = سرد الجلسة CP-8، لا الآلية) |
| CP-3 Rules ملفية | ALREADY-HAVE (أقوى) | مؤكد: `agents_rules/AGENTS.md` موجود فعلًا (توافق المعيار البيني حاصل) + manifest.yaml governed-allowlist (R4: ASF سياق الأسطول) | **ALREADY-HAVE — مُغلق** |
| CP-4 Hooks حتمية | ADOPT-CANDIDATE | لدينا نقطتا اعتراض حتميتان فقط: ApprovalGate (fail-closed، payload_hash — R4) + verify-step في agent_loop (`chain/agent_loop.py:343–408`: تعليمة تحقق من مفاتيح test/lint/typecheck/build) — لا آلية hooks يعرّفها المستخدم لأحداث دورة الحياة | **ADOPT-CANDIDATE يبقى** → PLANNING: تقييم hooks tighten-only كامتداد لـ verify-step؛ ليست P0/P1 |
| CP-5 Permissions UI | PARTIAL | مؤكد: allowlist + SAFE/DANGEROUS_COMMANDS + `force_command_approval` (TSK-502، config.yaml) — **لا واجهة استعراض/تحرير للأذونات**؛ المستخدم لا يرى سياسة الأمان إلا بفتح config.yaml | **PARTIAL يبقى** → UXF-04 أدناه |
| CP-6 Subagents معزولة | EVALUATE | أسطول 21-agent هو **fleet-as-data** (ملفات prompts/rules في `agents_rules/` — 14 دورًا + manifest) لا سياقات تشغيل معزولة؛ المسار التشغيلي الوحيد شبيه-subagent هو delegate runner (سياق مستقل + بوابة land) — وهو **مكسور الاعتماد حاليًا** (RP-01, `server.py:2337–2338`) | **EVALUATE محسوم**: لا حاجة لعزل سياقي جديد الآن؛ الأولوية إصلاح RP-01 ليعمل subagent-path الوحيد الموجود أصلًا |
| CP-7 Review-after | REJECT الترتيب / ADOPT الإظهار | مؤكد أن الإظهار موجود جزئيًا: diff panel لكل موافقة (T-065) — يتبقى إظهار مُجمّع بعد الدفعة (batch summary) | **مُغلق كما هو**: consent-first صامد؛ إظهار الدفعة يُدمج في مهمة سرد الجلسة (CP-8) |
| CP-8 سرد الجلسة | ADOPT-CANDIDATE (السرد فقط) | RunHistory قائمة rollback لكل run — **ليست سردًا**: لا timeline يجمع (طلب → خطة → موافقات → تنفيذ → نتائج) في عرض واحد | **ADOPT** → مهمة PLANNING (محليًا، بلا cloud — Non-Goal §15.2)؛ UXF-05 |
| CP-9 Auto-memories | PARTIAL | مؤكد: الذاكرة provenance-tracked — الكتابة إما يدوية أو عبر أداة `remember_fact` ضمن SAFE set (`chain/agent_tools.py:38`) بقرار صريح من الوكيل داخل الحلقة؛ Memory Panel كامل CRUD (`static/app.js:3492–3546` فوق `static/js/memory_panel.js`) | **REJECT التوليد التلقائي الصامت** — يخالف honesty §11.4 (الوكيل يكتب فقط عبر أداة مُعلنة تظهر في السجل)؛ الوضع الحالي هو النموذج الصحيح. مُغلق |

**خلاصة CP**: من 9 أنماط — 4 مُغلقة (CP-2/3/7/9)، 2 ADOPT إلى PLANNING
(CP-1 خطة-تفاعلية، CP-8 سرد)، 1 ADOPT-CANDIDATE مؤجل (CP-4 hooks)،
1 محسوم بإصلاح قائم (CP-6 ⇒ RP-01)، 1 فجوة UI (CP-5 ⇒ UXF-04).
لا انعطاف معماري — كل المقبول امتدادات Extend.

### R9.2 — Agentic Capability Matrix

| القدرة | الحالة | الدليل | الفجوة |
|---|---|---|---|
| **Plan** | ⚠️ موجودة غير تفاعلية | planner heuristic/llm/hybrid (`config.yaml:132`، `server.py:2654–2664`)؛ إطار `plan` يصل الواجهة (`server.py:1898`، `app.js:219–223`) | البطاقة قراءة-فقط — لا تحرير/تعطيل خطوة (CP-1 → PLANNING) |
| **Execute** | ⚠️ تعمل مع عيوب خيوط | 4 مسارات موثقة (R7)؛ `_apply_batch` بنقاط ticket+cancel (`server.py:2415–2462`) | direct غير مُخيَّط داخل حلقة ws (`server.py:1846–1858` — RP-02)؛ التطبيق in-loop (RF-01) |
| **Verify** | ⚠️ جزئية | verify-step في حلقة الوكيل: تعليمة من مفاتيح test/lint/typecheck/build (`chain/agent_loop.py:343–408`) | تحقق نصّي-إرشادي (تعليمة للنموذج) لا بوابة حتمية بعد التنفيذ؛ hooks حتمية = CP-4 مؤجل |
| **Memory** | ✅ | `remember_fact` SAFE (`chain/agent_tools.py:38`)؛ ProjectMemoryStore + provenance (`server.py:2786–2797`)؛ Memory Panel CRUD (`app.js:3492–3546`) | لا فجوة بنيوية — التوليد التلقائي مرفوض عمدًا (CP-9) |
| **Multi-file** | ✅ | `_apply_batch` يمر على دفعة إجراءات بملفات متعددة مع checkpoint لكل خطوة (`server.py:2415–2462`)؛ diff panel لكل موافقة (T-065) | عرض مُجمّع بعد الدفعة ضمن سرد الجلسة (CP-8) |
| **Cancel** | ⚠️ | عقد Runner بنقطتي cancel (started→cancel→gate→cancel→work — R7)؛ UI يرسل `chain_cancel` (`app.js:1153`) ويعالج `chain_cancelled/chain_cancel_result` (404/424) | مسار direct غير مُخيَّط ⇒ الإلغاء غير مستجيب أثناء نداء المزود المباشر (RP-02) → UXF-03 |
| **Approve** | ⚠️ مسار واحد مكسور | ApprovalGate fail-closed + payload_hash (R4)؛ diff panel قبل الموافقة (T-065)؛ force_command_approval (TSK-502) | **delegate approve مكسور وظيفيًا** (RP-01، `server.py:2337–2338`) → UXF-02؛ لا Permissions UI (CP-5) → UXF-04 |
| **Rollback** | ✅ | CheckpointManager + RunHistory UI + `rollback_run/rollback_file` (T-054، `app.js:3391–3420`) | لا فجوة آلية؛ الإظهار السردي = CP-8 |

**قراءة المصفوفة**: 3 قدرات خضراء (memory/multi-file/rollback)، 5 صفراء —
وكلها ترجع إلى **ثلاثة جذور** معروفة: RP-01 (اعتماد delegate)،
RP-02+RF-01 (نموذج الخيوط)، فجوة الإظهار CP-1/CP-8. لا قدرة حمراء/غائبة.

### R9.3 — UX Findings (من الواقع المؤكد فقط)

| ID | الخطورة | الوصف | الدليل |
|---|---|---|---|
| UXF-01 | C3/S3 | بطاقة الخطة غير تفاعلية: كل-أو-لا-شيء (نفّذ/إلغاء) — لا تعديل أو استبعاد خطوة قبل الموافقة؛ يُضعف قيمة consent-first عمليًا لأن رفض خطوة واحدة يعني إلغاء الخطة كلها | `static/app.js:3099–3128` (أزرار فقط، `state.planActions` تُنفَّذ كتلة واحدة) |
| UXF-02 | C2/S1 | طريق مسدود للمستخدم: واجهة مراجعة التفويض ترسل `delegate_approve` وتبدو الموافقة مقبولة، لكن الخادم يسقط إلى `actions=[]` بصمت (RP-01) — المستخدم يوافق ولا يحدث شيء بلا رسالة خطأ | `app.js:3347/3359` + `server.py:2337–2338` + بلع الاستثناء (NF-14 §15) |
| UXF-03 | C3/S2 | زر الإلغاء غير مستجيب أثناء المسار المباشر: `chain_cancel` يُرسَل لكن حلقة ws محجوزة بنداء المزود غير المُخيَّط — انطباع «تجمّد» | `server.py:1846–1858` (RP-02) × `app.js:1153` |
| UXF-04 | C4/S3 | لا واجهة استعراض للأذونات: سياسة SAFE/DANGEROUS/force_approval غير مرئية إلا في config.yaml — يخالف مبدأ glass box لأهم عقد أمان بين المستخدم والوكيل (CP-5) | `config.yaml` (TSK-502)؛ صفر عناصر UI للأذونات في app.js |
| UXF-05 | C4/S3 | لا سرد جلسة: RunHistory قائمة rollback تقنية لا timeline يحكي (طلب→خطة→موافقة→تنفيذ→نتيجة)؛ هذه بقية SR-1 الحقيقية بعد تضييق R9.0 (CP-8) | `app.js:3391–3420` (بنية القائمة) |

**خلاصة R9:** المحرك الوكيلي شبه مكتمل القدرات (لا قدرة غائبة) والفلسفة
consent-first مؤكدة خارجيًا (CP-7). الفجوات الخمس المسجلة تتركز في **السطح
لا المحرك** — ثلاثة جذور فقط تغذيها كلها، واثنان منها (RP-01، RP-02/RF-01)
مسجلان أصلًا كعيوب runtime من R7؛ الجديد الصافي لـ PLANNING هو حزمة الإظهار:
خطة-تفاعلية (UXF-01/CP-1) + سرد الجلسة (UXF-05/CP-8) + Permissions UI
(UXF-04/CP-5)، وإصلاح صمت UXF-02 يجب أن يُضم لمهمة RP-01 نفسها.

---

## R10 — Testing Gaps + Documentation Gaps (Delta) ✅ (Session 30 — 2026-07-28)

> **المنهج**: دلتا فوق QA_MASTER_PLAN + RELEASE_READINESS_REPORT (P6/P8 من
> أرشيف v4.1). تشغيل كامل جديد للعدة + فرز الإخفاقات الأربعة الموروثة
> بالدليل + فحص فجوة تغطية RP-01 + فحص طزاجة الوثائق.

### R10.0 — خط الأساس المعاد قياسه (هذه الجلسة)

`python -m pytest tests` (سقف timeout=30 لكل اختبار من pytest.ini):
**1709 اختبارًا — 4 فشل / 1671 نجاح / 34 تخطٍّ — ~70s**.
مجموعة الفشل **مطابقة تمامًا** لتشغيل Session 24 ⇒ الإخفاقات حتمية مستقرة
(ليست flaky) وموروثة من قبل بدء هذا البرنامج.

### R10.1 — فرز الإخفاقات الأربعة الموروثة (TF-01..04)

القاسم المشترك: ثلاثة من أربعة كسرها **إعادة تصميم الواجهة v25** (وسم
`?v=25` في index.html:32/516؛ sprite «v25 Modern Edition») التي جرت خارج
حوكمة البرنامج — الاختبارات الحارسة عملت كما صُممت والتُقطت الانجراف.

| ID | الاختبار | التشخيص (بالدليل) | التصنيف |
|---|---|---|---|
| TF-01 | `test_file_icons::test_license_note_present` | إعادة كتابة `static/icons/sprite.svg` (v25) أسقطت عبارة «رخصة المشروع» التي يثبّتها الاختبار (`tests/unit/test_file_icons.py:143`)؛ عبارة «الترخيص» في الموديول ما زالت موجودة | انجراف أصل-مقابل-اختبار؛ إصلاح C4: إعادة سطر الترخيص للـ sprite |
| TF-02 | `test_history_consumers::test_no_raw_history_slices_outside_sessions` | الانتهاك الوحيد في `providers/openai_shelby.py:105` (`history[-6:]`) — الاختبار يمسح `providers/` وهي **خارج النطاق كليًا** (§0.8)؛ لا يمكن إصلاح المصدر ضمن هذا البرنامج | تسرّب نطاق: الحل داخل-النطاق = استثناء `providers/` من مسح الاختبار (الاختبار حارس core، والمزود له عقده الخاص) |
| TF-03 | `test_rollback_ui::test_index_wiring_and_load_order` | **عيب تشغيلي حقيقي لا اختبار قديم**: v25 حذفت عنصرَي `id="run-history-btn"` و`id="memory-panel-btn"` من index.html (grep = 0 نتائج كعناصر؛ يبقيان فقط كأهداف `.click()` في index.html:212/220) بينما app.js:3639–3640 يربطهما في DOMContentLoaded ⇒ `getElementById(...)=null` → TypeError يقطع المعالج فلا يُربط status-chip (3641) ولا يبدأ refreshCapacity/الاستطلاع الدوري (3642–3643)؛ وأزرار Activity Bar ترمي عند النقر | **عيب C3/S2 حي**: لوحتا Run-History وMemory وشريحة الحالة معطلة الفتح من الواجهة — يقوّي UXF (R9) ويجب ضمه لمهام PLANNING |
| TF-04 | `test_theme_tokens::test_no_raw_colors_outside_themes` | v25 أدخلت مئات الألوان الخام في style.css (976–3633+) وindex.html:83–84 متجاوزةً بوابة color-tokens (check.sh gate) | دين تصميم واسع؛ قرار PLANNING: إمّا trans-tokenization لمقاطع v25 أو baseline-allowlist مؤقت مؤرَّخ |

**أثر جانبي حرج (TF-05)**: بوابة `scripts/check.sh:122–123` تشغّل pytest
كاملة ⇒ البوابة **حمراء دائمًا** ما دامت TF-01..04 قائمة — أي انحدار جديد
يذوب في نفس الفشل ولا يُميَّز على مستوى البوابة. رفع الأربعة شرطٌ لاستعادة
دلالة البوابة (C3/S3).

### R10.2 — فجوات التغطية (دلتا)

| ID | الوصف | الدليل |
|---|---|---|
| TD-01 | **صفر تغطية لمسار delegate_approve في server.py** — `grep -rln delegate_approve tests/` = لا شيء؛ عقود DelegateRunner تثبّت دورة bridge (brief→dispatch→review، `tests/contracts/test_runner_contracts.py:104–123`) ومسار waiting_approval مثبت كتذكرة فقط (test_ticket_cancellation/test_dispatch_parity) — لكن **مقبض WS نفسه** (المستهلك الفعلي، حيث يعيش RP-01 بـ`extract_actions` غير الموجودة) بلا أي اختبار؛ لهذا عاش RP-01 غير مكتشف رغم 1709 اختبارًا | يقاطع QF-02 (mypy لا يشمل server.py): العيب أفلت من **الطبقتين** — البند الاختباري لمهمة RP-01 في PLANNING يجب أن يغطي المقبض end-to-end بمزود مزيف |
| TD-02 | خطة QA مُنفَّذة فعليًا: 17 ملف اختبار يستشهد بـ QA-T (zip-slip/fencing/purge/apply-cancel/…) — لا فجوة بين المواصفة (P6) والتجسيد؛ الفجوة الوحيدة الباقية: QA-T11 جزؤه اليدوي (DevTools long-task) غير مؤتمت — مقبول كما وُثّق | جرد grep -rl "QA-T" tests/ = 17 |

### R10.3 — فجوات التوثيق (دلتا)

| ID | الوصف | الدليل |
|---|---|---|
| TD-03 | **RELEASE_READINESS_REPORT.md متجمد قبل التنفيذ**: يعلن G1–G3 CONDITIONAL FAIL و«execution 0/19 TSK / MODE B not started» (سطرا 4 و93) بينما الأرشيف يثبت 19/19 TSK ✅ وM1–M5 منفَّذة ومتحقَّقة (R5/R6: NF-20/21/22 VERIFIED-FIXED) — الوثيقة الرسمية الوحيدة لحكم الإطلاق تناقض الواقع؛ **لم تُجرَ إعادة التصويت (release re-vote) التي اشترطتها الوثيقة نفسها** | إعادة تقييم G1–G5 على الكود الحالي = مخرج طبيعي لنهاية PLANNING أو أول EXECUTION، مع مدخل جديد لم يكن موجودًا وقت P8: RP-01 (كسر runtime حي) وTF-03 |
| TD-04 | لا توثيق لإعادة تصميم v25 في أي وثيقة هندسية: التغيير لمس index.html/style.css/sprite وكسر 3 بوابات حارسة بلا سجل قرار أو تحديث للاختبارات | git log لـ static/ (8235147/2ed794f/0d74dad) لا يقابله أي قيد في docs/engineering/ |

**خلاصة R10:** البنية الاختبارية تبقى أقوى أصل (1709 اختبارًا، عقود، goldens،
17 ملفًا يجسد خطة QA) لكن بها ثقبان مُثبتان: (1) البوابة حمراء دائمًا بأربعة
إخفاقات موروثة أحدها عيب تشغيلي حي (TF-03) — رفعها ربح سريع يعيد دلالة
check.sh؛ (2) المستهلكون داخل server.py (مقابض WS) خارج شبكتي الأمان معًا
(اختبار + mypy) — وهو نفس الجذر الذي أنتج RP-01. وثيقة جاهزية الإطلاق
تحتاج إعادة تصويت رسمية بعد إدخال RP-01/TF-03 كمدخلات جديدة.

---

## 🏁 Stage 1 — REVIEW: مكتمل (R-1..R10 ✅)

كل مراحل المراجعة أُنجزت بمعيار الدليل. عائلات النتائج الجاهزة لـ PLANNING:
ASF-01..08 · RF-01..03 · PM-01..04 · RP-01..04 · QG-01..04 + QF-01/02 ·
UXF-01..05 · TF-01..05 + TD-01..04 — مع الأحكام الاستراتيجية (CP/FD/BET/SR)
وسجل القوة S-01..S-14 كموجّهات Preserve.

---

# STAGE 2 — PLANNING (Session 31 — 2026-07-28)

## P.1 — التصنيف الكامل P0–P3 (الدستور §10.1)

**حكم P0**: لا نتيجة تبلغ عتبة Critical — لا فقدان بيانات فعليًا، لا ثغرة
قابلة للاستغلال خارج نموذج التهديد المحلي (localhost-bound، RRR §G2)،
لا انهيار للنظام. أعلى الموجود: قدرة مكسورة بصمت (RP-01) وحقن سياق نظري
(ASF-01) — كلاهما P1.

| Finding | P | مبرر الموضع | المهمة |
|---|---|---|---|
| RP-01 + UXF-02 + TD-01 | **P1** | قدرة delegate مكسورة وظيفيًا (C4/S2) + فشل صامت للمستخدم (C2) + صفر تغطية للمقبض — سبب جذري واحد، مهمة واحدة | TSK-601 |
| ASF-01 | **P1** | أعلى نتيجة أمان وكيلي (C3/S3): حقن نتائج الأدوات بلا تسييج | TSK-602 |
| ASF-02 | **P1** | بوابة الموافقة موضعية لا بنيوية (C3/S3) | TSK-603 |
| TF-01, TF-03, TF-05 | **P1** | TF-03 عيب حي (3 لوحات معطلة)؛ البوابة الحمراء الدائمة (TF-05) تعمي كل انحدار قادم — رفعها risk-reducing يسبق كل تنفيذ آخر | TSK-604 |
| TF-02 | **P1** | ضمن استعادة البوابة (تسرّب نطاق اختباري — إصلاح scope فقط) | TSK-605 |
| TF-04 | **P1-blocked** | يمنع خضرة البوابة؛ ينتظر قرار منتج (tokenization كاملة أم baseline مؤقت) — التوصية الهندسية: baseline مؤرَّخ الآن + مهمة tokenization لاحقة P3 | TSK-605 |
| RF-01 + RP-02 + UXF-03 | **P2** | عائلة خيوط واحدة: apply/direct داخل حلقة ws — الإلغاء غير مستجيب؛ ليست P1 لأن العمل يصح (البطء/الاستجابة هي الأثر) | TSK-606 |
| RP-03 | P2 | آخر جيب خارج ContextBudget | TSK-607 |
| RF-02 | P2 | reap_stale ميت تشغيليًا — خطر كامن | TSK-608 |
| PM-01..04 | P2 | instrumentation — يفتح حلقة تغذية راجعة لكل تحسين لاحق (unlocking) | TSK-609/610 |
| QG-01..04 + QF-02 | P2 | تفكيك g1 بترتيب المخاطرة المتفق (R8)؛ QF-02 يُغلق ضمن QG-04 (ضم server.py لبوابة mypy) | TSK-611..614 |
| ASF-05 | P2 | استنزاف موافقات صامت عند التزامن | TSK-615 |
| ASF-03 | P2 | rollback جزئي صامت فوق السقف — الإصلاح: إظهار لا رفع سقف | TSK-616 |
| ASF-04 | P2-decision | قلب enforce الافتراضي البرمجي إلى True — تغيير سلوك يحتاج موافقة المستخدم (مع NF-16) | TSK-617 |
| ASF-07 | P2 | تضييق except الابتلاعي في path_policy | TSK-618 |
| UXF-01 (CP-1) | P2 | بطاقة الخطة التفاعلية — أول حزمة الإظهار | TSK-619 |
| UXF-05 (CP-8) | P2 | سرد الجلسة | TSK-620 |
| UXF-04 (CP-5) | P2 | Permissions UI (قراءة أولًا) | TSK-621 |
| TD-03 | P2 | إعادة تصويت RRR — بعد إغلاق M6 (مدخلاه RP-01/TF-03 يكونان مُصلحين) | TSK-622 |
| QF-01 | P3 | تلوث improvements/ — نقل/أرشفة (عملية حذف من الشجرة ⇒ تُعرض على المستخدم قبل التنفيذ) | TSK-623 |
| TD-04 | P3 | retro-ADR لإعادة تصميم v25 | TSK-624 |
| ASF-06 | P3 | صلابة _parse_args_body | TSK-625 |
| RP-04 | P3 | قرار توثيقي: فرع proposed_actions يُعلَّم test-only أو يُوصَل | TSK-626 |
| ASF-08, RF-03, TD-02 | P3-accepted | مقبولة موثَّقة — لا مهمة؛ تبقى في السجل | — |
| CP-4 hooks, CP-6 | P3-future | امتدادات مؤجلة بعد حزمة الإظهار | — |

## P.2 — Engineering Alternatives (إلزامي لكل P1 — الدستور §10.2–10.4)

### ALT-601 — إصلاح اعتماد التفويض (RP-01)
- **Current Design**: `delegate_approve` ينادي `parser.extract_actions/extract_options`
  غير الموجودتين (server.py:2337–2338) → AttributeError مبتلع → fallback صامت.
- **Alternative A** — استخدام `parser.parse(response, mode=...)` + تحويل
  ParsedResponse إلى actions كما في مسار agent (server.py:1791–1800).
  Pros: يوحّد مساري التحويل؛ صفر API جديد؛ يرث إصلاحات TSK-101 (mode-aware).
  Cons: ازدواج كود التحويل إن لم يُستخرج لدالة مشتركة.
- **Alternative B** — إضافة `extract_actions/extract_options` فعليًا إلى
  ResponseParser. Pros: يطابق النية الأصلية للنداء. Cons: يوسّع سطح API
  لمستهلك واحد؛ يخلق مسارَي تحويل متوازيين — عكس درس TSK-201 (توحيد apply).
- **Competitive check**: لا نمط خارجي ذو صلة — مسألة داخلية. لا بديل أفضل.
- **Recommended**: **A** مع استخراج دالة تحويل مشتركة واحدة (`_parsed_to_actions`)
  يستهلكها المساران | Migration risk: منخفض (المسار مكسور أصلًا — لا سلوك
  عامل يُفقد) | Rollback: revert commit واحد.
- **Vision 1–2y**: صحيح — التوحيد يخدم QG-02 (استخراج مسارات الإرسال) لاحقًا.

### ALT-602 — تسييج نتائج الأدوات (ASF-01)
- **Current Design**: حقن خام `[نتيجة {tool}...]:\n{نص}` (agent_loop.py:224–259)
  و`to_summary/_render_body` خام في knowledge.py:41–49/191–205؛
  `fence_attached` موجودة (templates.py:39) وغير مستدعاة من هذه المسارات.
- **Alternative A** — استدعاء `fence_attached` عند مواضع الحقن الأربعة.
  Pros: يعيد استخدام الآلية المُختبرة (TSK-404)؛ تغيير موضعي. Cons: يبقى
  «تذكُّر الاستدعاء» عبئًا على كل موضع مستقبلي.
- **Alternative B** — طبقة ContextSanitizer مركزية تمر بها كل نصوص السياق.
  Pros: بنيوي — لا نسيان ممكن. Cons: طبقة جديدة + إعادة توجيه كل المسارات؛
  يخالف سلّم Preserve→Wrap→Extend لمشكلة تُحل بالتفاف.
- **Alternative C (تنافسي)** — نمط Claude Code hooks (CP-4): اعتراض حتمي لكل
  tool-result. مصدر: code.claude.com/docs/en/hooks. Pros: أعم. Cons: يقدّم
  نظام hooks كاملًا لحاجة تسييج فقط — مؤجل عمدًا (R9: CP-4 candidate).
- **Recommended**: **A** الآن + بند اختبار يفرض التسييج (grep-assert على
  مواضع الحقن) يقوم مقام الضمان البنيوي | Migration risk: منخفض — التسييج
  يغيّر نص البرومبت (سلوك موديل قد يتأثر هامشيًا؛ يُسجل في سجل الحفظ) |
  Rollback: revert.
- **Vision 1–2y**: صحيح — وإن تبنينا hooks لاحقًا (CP-4) يصبح A حالة خاصة منها.

### ALT-603 — بوابة موافقة بنيوية (ASF-02)
- **Current Design**: `tool_run_command(need_approval=False)` داخليًا
  (agent_tools.py:485)؛ الفرض في AgentLoop فوقه فقط.
- **Alternative A** — قلب الافتراضي: `need_approval=True` في التوقيع، والحلقة
  تمرر قرارها صراحة. Pros: fail-closed لأي مستدعٍ جديد؛ سطر واحد + تحديث
  المستدعين. Cons: مستدعٍ قديم لم يُحدَّث سيطلب موافقة زائدة (أمان زائد، لا كسر).
- **Alternative B** — جعل ApprovalGate معاملًا إلزاميًا في مُنشئ AgentTools
  والفرض داخل الأداة نفسها. Pros: الأقوى بنيويًا. Cons: يعيد توزيع مسؤولية
  الحلقة/الأداة (تصميم متعمد وثّقته R4)؛ أوسع أثرًا.
- **Competitive check**: Claude Code permissions افتراضها deny-by-default
  للأوامر (code.claude.com/docs/en/permissions) — يدعم اتجاه A.
- **Recommended**: **A** | Migration risk: منخفض (مستدعو الإنتاج محصورون
  بالحلقة — grep يؤكد) | Rollback: revert.
- **Vision 1–2y**: صحيح — deny-by-default هو المعيار الصناعي المستقر.

### ALT-604 — استعادة دلالة البوابة (TF-01/03/05 + TF-02/04)
- **Current Design**: check.sh حمراء دائمًا بأربعة إخفاقات موروثة من v25.
- **Alternative A** — إصلاح الأصول لتطابق الحرّاس: إعادة عنصرَي الأزرار إلى
  index.html (TF-03)، سطر الترخيص إلى sprite (TF-01)، استثناء providers/ من
  مسح history (TF-02)، baseline-allowlist مؤرَّخ لألوان v25 (TF-04).
  Pros: يعيد البوابة خضراء في مهمتين صغيرتين؛ TF-03 يصلح عيبًا حيًّا.
  Cons: baseline الألوان دين مؤجل (يُسجل في TECHNICAL_DEBT).
- **Alternative B** — تعديل الاختبارات لتقبل واقع v25 (إضعاف الحرّاس).
  Pros: أسرع. Cons: مرفوض مبدئيًا — الحرّاس عملوا كما صُمموا؛ إضعافهم يخفي
  العيب الحي TF-03 ويشرعن الانجراف.
- **Competitive check**: نمط "ratchet/baseline lint" ممارسة موثقة قياسية
  (مثل ESLint suppressions المؤرخة) — يدعم baseline المؤقت في A.
- **Recommended**: **A** | Migration risk: TF-03 يعيد تفعيل 3 لوحات كانت
  معطلة (تغيير سلوك مرئي للمستخدم — للأفضل، يُوثَّق) | Rollback: revert لكل
  ملف على حدة.
- **Vision 1–2y**: صحيح — بوابة ذات دلالة شرط لكل ما بعدها.

## P.3 — قرارات منتج معلّقة (تُعرض على المالك — لا تُنفَّذ قبل رد)

| # | القرار | التوصية الهندسية | يمس |
|---|---|---|---|
| D-1 | NF-16 + ASF-04: قلب `force_command_approval` و`enforce` إلى افتراض آمن code-default | نعم — قلبهما (أمان زائد لا كسر) | TSK-617 |
| D-2 | TF-04: tokenization كاملة لألوان v25 أم baseline مؤقت؟ | baseline مؤرَّخ الآن + مهمة tokenization P3 | TSK-605 |
| D-3 | QF-01: نقل/حذف improvements/ (892KB) من الشجرة | نقل إلى أرشيف خارج جذر الفحص | TSK-623 |
| D-4 | TD-03: إعادة تصويت RRR بعد M6 | إجراؤها تلقائيًا كوثيقة | TSK-622 |

## CEV-G1 — تقرير بوابة البنية 🏁 PASS (2026-08-02 — S106د؛ برنامج CEV/D-12، دفعة D-13)

> أول بوابة CEV. المنهج: أدلة `file:line @ commit` حصرًا؛ الاكتشافات
> التفصيلية في NEW_FINDINGS §CEV-F-001..006؛ الحالة في PROGRESS.md.

**1. سلامة سلسلة الأدوات (كانت حمراء — أُصلحت):**
- الجذر الحقيقي لانكسار البوابة = كود مالك وارد خارج الحوكمة
  (c9ab00c: مزودات you_com/perplexity/blackbox — 9 أخطاء
  module_from_spec على `ModuleSpec|None`)؛ فرضية «انجراف إصدار mypy»
  **فُنِّدت تجريبيًا** (mypy 1.10.0 = نفس الأخطاء) — CEV-F-001.
- المعالجة (BATCH-CEV-G1، قرار D-13): سقف `mypy>=1.10,<2` + stubs +
  CI من requirements-dev (TSK-CEV-101)؛ استثناء موسَّع بسابقة ADR-004
  (TSK-CEV-102) — **قابل للرفع** يوم يُصلح المالك النمط.
**2. dead code:** إزالة الميت المؤكد (TSK-CEV-103): executor.py ×5
استيرادات، server.py ×2، delegate.py معامل ميت — بعد فرز vulture يدوي
شامل (إيجابية كاذبة مستبعدة: BudgetSnapshot تحت TYPE_CHECKING).
**3. دورات الاستيراد:** صفر (حارس NF-24 AST-based أخضر).
**4. تضخم الملفات:** app.js=712<800 (FI-07 صامد بحارس test_app_split)؛
أكبر وحدات النطاق: server.py 2357 (منها +92 وارد مالك 8dd9e8a —
تدقيقه محال G6/G8)، agent_tools 897، bridge 789 — كلها دون عتبة
انفجار، ولا melting-pot جديد.
**5. التكرار:** مسح AST ×58 تصادم اسم عبر الملفات — الغالب تعددية
أشكال مشروعة (واجهة backends/backends_redis/events؛ نمط register
للـ blueprints؛ to_dict على dataclasses). المؤكد: `_search_service`
ازدواج **مقصود موثَّق** (TSK-501/NF-20/NF-21 — كلاهما يفوّض
`shared_search`)؛ `_now_iso` سطران ×3 ملفات (تافه — لا يبرر اقترانًا
جديدًا بين طبقات context/sessions؛ يُلمّ إن فُتح ملف utils يومًا).
**6. فصل الاهتمامات:** server.py يحوي 3 routes فقط (`/`,
`/api/models`, `/api/switch-model`) — بقية الـ REST في routes/ (7
blueprints، ADR-003)؛ WS في core/ws_router؛ dispatch في
core/chat_dispatch — القرار القائم «مقبول موثَّق» يصمد.
**الحكم: G1 PASS** — بوابة الإقفال: **check.sh ALL GREEN RC=0 —
2189P/34S/0F** (مؤكدة ×2 بيئتين؛ flaky بيئي موثَّق CEV-F-006).
**التالي: G2.**

## CEV-G2 — تقرير بوابة الواجهة 🏁 PASS (2026-08-02 — S106هـ؛ CEV/D-12)

**جرد السطح:** 15 وحدة UMD-lite نقية (plan_card/memory_panel/
run_history/permissions_panel/settings_panel/diff_panel/status_chip/
trust_banner/command_palette/…) + 6 وحدات غراء app/NN + مودالان
(quick-open، command-palette) + 4 ثيمات فوق tokens.css.
**1. الثيمات:** تكافؤ رباعي مثالي — **105 tokens متطابقة بالمجموعة**
عبر dark/light/high-contrast/monokai (فحص فرق مجموعات: ∅ ناقص،
∅ زائد)؛ bootstrap قبل أول paint (لا FOUC — T-060)؛ حارس
test_theme_tokens.py قائم + color-token lint في check.sh أخضر.
**2. RTL/LTR:** القشرة IDE ثابتة `dir="ltr"` (نمط VSCode المتعمد)
والمحتوى ديناميكي لكل رسالة (`msg-content[dir]` — app.js:515،
10_chat_ws_stream:793+) مع أنماط CSS مزدوجة rtl/ltr (style.css:1352+)
— **سليم بالتصميم**، لا احتكاك مثبت.
**3. حالات العرض:** empty-state في 6/6 لوحات نقية؛ error عبر toast
موحَّد (app.js:579) + catch في الغراء (40_panels ×13، app.js ×16،
10_chat ×5)؛ مؤشرات loading في مسارات الغراء (40_panels ×10،
10_chat ×11). لا لوحة بلا معالجة.
**4. فحص حي (Playwright على الخادم الفعلي):** تحميل كامل، صفر أخطاء
JS؛ 404 وحيد = `favicon.ico` — **تجميلي C4** (لا favicon بالمشروع؛
يُسجَّل بلا إصلاح فوري — إضافة أصل بصري قرار مالك per CEV-R11).
**5. Premium (CEV-R11):** بنية palette/quick-open/status-chip/
trust-banner/virtual-list تضاهي أنماط VSCode/Cursor وظيفيًا؛ لا تقليد
أعمى — RTL محتوى عربي أصيل.
**الحكم: G2 PASS** (اكتشاف واحد C4 مؤجَّل: favicon). **التالي: G3
(تمشية مستخدم أول مرة).**

## CEV-G3 — تقرير بوابة تجربة الاستخدام 🏁 PASS (2026-08-02 — S106و؛ CEV/D-12)

> المنهج: تمشية مستخدم أول مرة **على خادم حي** (port 5000، مشروع
> تجريبي نظيف /tmp/g3_user_project) — 17 خطوة عبر REST/WS، صفر نداء
> AI حقيقي (P-11). الأدلة: استجابات حية مقتبسة في سجل S106و.

**التدفق والنتائج (17/17 ✅):**
1. فتح مجلد (`/api/switch-project`) ⇒ ok + **بانر ربط الجلسة** ينبّه
   أن الجلسة بدأت على مشروع آخر — حارس UX سليم.
2. حالة الثقة الافتراضية ⇒ `trusted:false` — **fail-closed** (TSK-725).
3. أمر قبل الثقة (`/api/run` echo) ⇒ **مرفوض** («رفض المستخدم»،
   code=-1) — الإنفاذ حقيقي لا شكلي.
4. منح الثقة ⇒ ok. 5/6. قراءة/حفظ ملف ⇒ ok (+content_numbered).
7. الأمر بعد الثقة ⇒ success, output=hello.
8. بحث `/api/search?q=console` ⇒ يجد **المحتوى المحفوظ للتو**
   (write-through index طازج — NF-20 يعمل عمليًا).
9. جلسة جديدة + قائمة الجلسات ⇒ ok (ids/عدّادات سليمة).
10. تشخيص + سعة ⇒ dependencies كلها true؛ 7 مزودين healthy،
    breaker closed.
11. WS handshake + ping ⇒ `{"type":"pong","ctx":true}` — قناة حية.
12. rollback/history + backups ⇒ ok (فارغة كما يُتوقع لمشروع جديد).
13. desktop.py ⇒ استيراد headless سليم (main موجودة؛ نافذة GUI بيد
    المالك D-8-ب).
14. chat-history ⇒ ok. 15. new-file/new-folder ⇒ ok.
16. **عزل الثقة**: تبديل لمشروع ثانٍ ⇒ `trusted:false` فورًا.
17. العودة للأول ⇒ القرار محفوظ (`decided_at/decided_by`) — ذاكرة
    ثقة لكل-مشروع صحيحة.
**نقاط احتكاك مثبتة: صفر حاجز.** ملاحظات ثانوية: favicon 404
(CEV-F-007 قائمة)؛ سطح `/api/open-project` غير موجود (الاسم الفعلي
switch-project — الواجهة تستخدم الصحيح؛ لا احتكاك مستخدم).
**حادث موازٍ (خارج البوابة):** البوت حذف fixture `.env` مرة ثانية
@ 37a371f — استعادة فورية + تحديث CEV-F-003 (نمط يحتاج قرار مالك).
**الحكم: G3 PASS. التالي: G4 (البصريات).**

---

## CEV-G4 — تقرير بوابة البصريات 🏁 PASS
**التاريخ: 2026-08-02 (S106و) — الشجرة: 2e1d273 — المنهج: مسح ثابت كمّي (grep/awk على 4557 سطر CSS) + حراس آليون + تحميل حي**

### 1) عقد الألوان — T-060/R-905 (المحور المفروض CI)
- **صفر ألوان خام (hex/rgb/hsl) خارج `static/themes/`** — مسح كامل
  css/js/html: 0 انتهاك (`scripts/check.sh:106-118` بوابة دائمة).
- الظلال السبعة غير التوكنية كلها `color-mix(in srgb, var(--token) N%, transparent)`
  — theme-aware بالبناء (style.css:226, 2966, 3182, 3230, 3423, 3455, 3585).
- **28/28 اختبار حارس يمر** (`test_theme_tokens.py`): تكافؤ 105 توكن
  رباعي (dark/light/high-contrast/monokai) + تباين WCAG AA ≥4.5.

### 2) الأيقونات — R-903
- مقادة توكنيًا بالكامل: `file_icons.js` سجل `colorToken: "--icon-*"`
  → `<svg style="color: var(--icon-py)">` + sprite.svg؛ شارات الملفات
  `.file-badge.{py,js,ts,html,css,json,md}` كلها `var(--icon-*)`
  (style.css:2109-2115). صفر لون أيقونة صلب في JS.

### 3) radius / ظلال / transitions / خط / spacing (كمّي)
- radius: سلّم ضمني متسق (2/3/4/6/8/10/12/16/20px/50%) لكن 19 إعلانًا
  خام يكرر توكنَي `--radius`/`--radius-lg` حرفيًا ⇒ **CEV-F-008 (C3)**.
- transitions: 29 توكني مقابل 22 خام — الخام أغلبه property-specific
  (لا يعبَّر عنه بتوكن `all`)؛ 9×0.15s طبقة سرعة ثالثة بلا توكن (F-008).
- font-weight: 600 مهيمن (×36) — تسلسل بصري واضح؛ `bold`×2 خلط C4.
- font-size: سلّم 9–14px متماسك (59×12px قمة)؛ شواذ 11.5/12.5px ×6 (C4).
- padding: توزيع متقارب حول أزواج 8-16px — لا فوضى spacing.
- `!important` ×125: 25 hljs (تجاوز مكتبة مبرر) + 64 v25 (طبقة موثقة
  TF-04) + 36 قلب — رائحة specificity، ليست انتهاك توكنات.

### 4) تحميل حي
- خادم فعلي (port 5000): كل أصول CSS الستة 200؛ Playwright: **صفر
  أخطاء JS** — الـ404 الوحيد favicon.ico (F-007 المسجل، C4).

### الحكم
المحور المُقانَن CI (الألوان) **سليم 100%** ورباعية الثيمات محروسة
آليًا؛ الأيقونات توكنية بالكامل؛ الانحرافات البنيوية (radius/مدد)
اتساقية لا وظيفية، مصنفة C3/C4 في **CEV-F-008** مع TSK اختياري —
لا حاجز. **الحكم: G4 PASS. التالي: G5 (الأداء — أرقام قبل/بعد إلزامية).**

---

## CEV-G5 — تقرير بوابة الأداء 🏁 PASS
**التاريخ: 2026-08-02 (S106ح) — الشجرة: 0e959cd — المنهج: قياسات مباشرة في بيئة التقرير نفسها (أرقام قبل/بعد إلزامية) + 71 حارس أداء**

### الأرقام (كلها في بيئة واحدة @ 0e959cd)
| المحور | القياس | النتيجة | السقف/المرجع |
|---|---|---|---|
| استيراد بارد | `import server` | **357ms** | — |
| إقلاع | إطلاق → أول استجابة 200 | **635ms** | — |
| ذاكرة خاملة | RSS بعد الإقلاع | **52.4 MiB** | — |
| ذاكرة تحت حمل | RSS بعد 200 طلب متتابع | **52.7 MiB (Δ+0.3)** — لا تسريب | — |
| زمن الطلب | متوسط 200 طلب index | **3.2ms/طلب** | — |
| DOM windowing (TSK-724) | computeWindow ×1000 على 5000 عنصر | **0.036ms/نداء؛ يُصيَّر 18 من 5000** | ثابت padTop+Σ+padBottom محروس |
| بث 100KB | حارس test_stream_render (1600 chunk ×64B بأُطر 16ms) | **يمر — رندرات مقيّدة بالأُطر** | لا مهام >100ms |
| بحث 5k (QA-T13) | api_search / tool_search_code (حالة مستقرة) | **156ms / 129ms** | **<1000ms** (هامش ×6-7) |
| ProjectIndex persistence (TSK-719) | بارد (مسح+حفظ) → دافئ (بذر snapshot) | **164ms → 125ms؛ rebuilds 1→0؛ snapshot 97KB** | حفظ فقط عند التغيّر |

### الحراس
- **71/71 يمر** في تشغيل نظيف واحد: `test_virtual_list` + `test_stream_render`
  + `test_search_perf` (يشمل TestPerf5k + التكافؤ الذهبي) +
  `test_index_snapshot` + `test_index_snapshot_wiring`.
- تكرار متقلب CEV-F-006 ظهر مرة واحدة في أول تشغيل بعد تثبيت البيئة
  (`test_no_save_churn_when_list_unchanged` — mtime granularity) ثم مرّ
  معزولًا ×3 وفي التشغيل النظيف الكامل — مطابق تمامًا للتوثيق القائم؛
  لا تحديث جديد مطلوب.

### الحكم
كل الأرقام تحت السقوف بهوامش واسعة (البحث ×6-7، الذاكرة مستقرة بلا
تسريب، النافذة الافتراضية تحدّ DOM عند ~18 عنصرًا مهما بلغ الحمل)،
والسقف الوحيد المُقانَن (QA-T13 <1s) محروس باختبار دائم.
**الحكم: G5 PASS. التالي: G6 (الخلفية — blueprints السبعة + server.py + worker seam).**

---

## CEV-G6 — تقرير بوابة الخلفية 🏁 PASS
**التاريخ: 2026-08-02 (S106ط) — الشجرة: 7365752 — المنهج: جرد ثابت + 268 حارس + تحقيق حي (مجسات REST خبيثة + ذرّية تحت SIGKILL)**

### 1) السطح المجمد
- 7 blueprints (backups 2، files 8، meta 8، project 1، rollback 2،
  run 3، sessions 6) + 3 مسارات في server.py (ADR-003) —
  **حارس FROZEN_RULES يثبّت 31 قاعدة url_map حرفيًا**
  (test_rest_blueprints.py:35 — أي توسّع = فشل بوابة). 21/21 يمر.

### 2) validation ومعالجة الأخطاء (تحقيق حي)
- JSON فاسد ⇒ 400؛ حمولة ناقصة ⇒ 400 برسالة عربية واضحة.
- اجتياز مسار قراءةً (`..%2f` مرمّز وخام) ⇒ **رفض fail-closed**
  «Access denied … outside project root» [404].
- اجتياز كتابةً (POST `..%2fpwned.txt`) ⇒ **رفض fail-closed مؤكد**
  (لا ملف كُتب خارج الجذر) لكن بالرمز 500 ⇒ **CEV-F-009 (C4)** —
  تفاوت عقد رقمي لا ثغرة.

### 3) ذرّية الكتابة (NF-19)
- النمط الحرفي (tmp بجوار الملف → fsync → os.replace) في:
  index_snapshot.py:82، workspace_trust.py:74، project_memory.py:367،
  checkpoint.py:285/404/556، run_metrics.py:85 (تدوير).
- استثناء موثَّق بالتصميم: sessions/store.py meta بلا fsync
  (مشتق ورخيص — store.py:43) + إصلاح السطر الممزق wb مع fsync
  (project_memory.py:411-415) — كلاهما سليم.
- **اختبار حي**: عملية تكتب snapshots في حلقة قُتلت SIGKILL ×5 في
  توقيتات مختلفة ⇒ **5/5 الملف سليم كامل، صفر تمزّق**.

### 4) التزامن والأقفال
- 31 قفل/RLock عبر server.py وcore/ (approval، app_context،
  backends_redis لكل-run، chat_dispatch WS، pending_path).
- invariants سجل التنفيذ + الموافقات المتزامنة محروسة:
  test_execution + test_checkpoint + test_approval(+concurrent) +
  test_parallel_execution + test_force_approval — ضمن **268/268
  حارس خلفية يمر** في تشغيل واحد (rest_blueprints، ws_router،
  retention، run_metrics(+rotation)، workspace_trust(+enforcement)،
  rest_ws_state_parity، ws_run_control، agent_gated_approvals،
  ws_backoff، trust_banner).

### الحكم
السطح مجمّد ومحروس آليًا؛ الرفض fail-closed في كل المجسات الخبيثة؛
الذرّية صمدت تحت SIGKILL فعليًا؛ التزامن محروس بطبقة اختبارات كثيفة.
الاكتشاف الوحيد (F-009) تجميلي C4 بلا أثر أمني.
**الحكم: G6 PASS. التالي: G7 (الأمان — Red Team داخل عقد localhost).**

---

## CEV-G8 — تقرير بوابة طبقة تنفيذ AI 🏁 PASS
**التاريخ: 2026-08-02 (S107) — الشجرة: 5d083d5 — المنهج: جرد ثابت (9112 سطر/23 وحدة) + 394 حارس مركّز + فحص عزل providers — كل الفحص بـ Stubs (P-11)؛ G7 مؤجلة بقرار مالك D-14**

### 1) عزل providers (P-11)
- الاستيرادات من `providers.*` في chain/ محصورة في **العقد المجرد
  حصريًا** `providers.base` (bridge.py:27 + executor.py:38 +
  router.py:28 تحت TYPE_CHECKING) — **صفر إشارة لأي مزود ملموس**
  (grep على openai_shelby/you_com/perplexity/blackbox/use_ai في
  chain/ = 0).

### 2) agent loop (حدود + إلغاء + fail-safe)
- سقف صلب مزدوج: `MAX_ITERATIONS = 8` + `min(max_iterations, MAX)`
  (agent_loop.py:44,64) — لا حلقة مفتوحة ممكنة بالبناء.
- الإلغاء T-015 (R-105) ثنائي المصدر: علم محلي + تذكرة السجل
  (`_is_cancelled` :78-83)، يُفحص عند رأس كل iteration (:132) وقبل
  كل أداة (:192)؛ `cancel()` يفك أي موافقة معلّقة برفضها عبر البوابة
  (:306-309) — لا انتظار يتيم. حارس حي: test_ticket_cancellation.
- إنهاء التذكرة مضمون في كل المسارات (try/except/finally :105-115:
  completed/cancelled/failed).
- تدهور رشيق: بلوغ الحد ⇒ محاولة إجابة أخيرة بالمعرفة المجمعة؛
  فشلها ⇒ رد صريح بالنتائج الجزئية (:298-304) — لا انهيار صامت.

### 3) executor (retry + ميزانية + بث)
- retry محكوم بميزانية: `run.budget.reserve_call(is_retry=…)` قبل
  كل محاولة (:331-337)؛ فحص إلغاء قبل كل retry (:332-336)؛ تصنيف
  أخطاء المزود بهرمية ProviderError/RateLimit/Timeout/Transient
  (:359).
- البث: ChainEvent موحّد ⇒ callback + events.jsonl معًا (`_emit`
  :529-530) — مسار حدث واحد لا ازدواج.

### 4) context builder (ميزانية السياق)
- `ContextBudget.pack` من config هو المسار الوحيد (context_builder
  :126-148) مع fallback مشتق من model_window — لا بتر اعتباطي؛
  حارس التقارب test_context_builder_convergence يمر.

### 5) التزامن والابتلاع المنضبط
- bridge: RLock معلَّل بتعليق (:239) + خيط daemon واحد (:410).
- 29 موضع ابتلاع في chain/ كلها عبر `structured_log.swallowed`
  الموحّد (FI-06)؛ الاستثناءان العريضان في agent_loop (:108 يعيد
  الرفع بعد إنهاء التذكرة؛ :302 تدهور رشيق معلَن) — سليمان.

### 6) الحرّاس الحية والنظافة الثابتة
- **394/394 يمر** في تشغيل واحد @ 5d083d5 (22.8s): goldens
  (chain+routing bit-identical) + ticket_cancellation +
  dispatch_parity + agent_feedback + agent_gated_approvals +
  chain_gated_apply + crash_resume + parallel_execution +
  agent_manifest + context_builder_convergence + llm_planner +
  planner + contracts (113 عقد/تكافؤ).
- صفر TODO/FIXME/HACK في chain/.
- الخط الأحمر NF-18 قائم: `INJECTION_GUARD_INSTRUCTION` مضموم
  للـ SYSTEM_PROMPT (templates.py:29,51) + تسييج attached-content
  (:26-27) — تدقيقه الكامل موضوع G8.5.

### الاكتشافات
- **CEV-F-010 (C3)**: `chain/hh.har` — HAR دخيل 7.2MB (رفعة d15deb1
  قبل الحوكمة)، صفر اعتمادات، صفر مراجع، خارج التغليف — التوصية
  حذف بقرار مالك.
- **CEV-F-011 (C3)**: 42 استيرادًا/متغيرًا ميتًا عبر النطاق (21 منها
  في chain/) — pyflakes خارج بوابة check.sh فلا يلتقطها أحد؛ TSK
  مقترحة: إزالة + ضم pyflakes للبوابة. لا أثر سلوكي — لا يحجز G8.
- ملاحظة C4 (لا قيد): حقنة `sys.path.insert` في bridge.py:22-25 —
  خاملة تحت التشغيل العادي ومغطاة بالبوابات — لا فعل.

### الحكم
عزل المزودات تام بالبناء، الحلقة محدودة بسقف صلب، الإلغاء مزدوج
المصدر ومفحوص عند كل حد، retry محكوم بميزانية، البث أحادي المسار،
والابتلاع منضبط عبر structured_log. الاكتشافان (F-010/F-011) نظافة
C3 بلا أثر سلوكي.
**الحكم: G8 PASS. التالي بالترتيب المعدل (D-14): G8.5 (AIA — حوكمة طبقة الذكاء).**

---

## CEV-G8.5 — تقرير بوابة حوكمة طبقة الذكاء (AIA) 🏁 PASS
**التاريخ: 2026-08-02 (S108 تكملة 6) — الشجرة: 497cc99 — المنهج: 8 مراحل AIA-0..7 كلها ببوابات مقفلة في PROGRESS.md + قياس حي قبل كل تثبيت (نمط T-034) — صفر نداءات AI حقيقية (P-11)**

### ملخص المراحل (كلها ✅ ببوابة مسجلة)
| مرحلة | الناتج | القيد |
|---|---|---|
| AIA-0 | ميثاق + خريطة أصول أولية | PROGRESS S108 |
| AIA-1 | جرد 226 أصلًا مصنَّفة 100% (`AIA_INVENTORY.md`) | S108 |
| AIA-2 | تدقيق ثنائي الاتجاه → F-012/F-013/F-014 | S108 تكملة |
| AIA-3 | إعادة كتابة: 27/27 برومبتًا Score≥70 (22=100/100) + نواة/overlay + corpus R8 ذهبي | S108 تكملة |
| AIA-4 | حقول توجيه ADR-007 في manifest (رجعية التوافق) | S108 تكملة 2 |
| AIA-5 | دورة حياة المهارات: 17/17 بطاقة + FI-13/14 (`AIA_SKILLS_LIFECYCLE.md`) | S108 تكملة 3 |
| AIA-6 | مصفوفة التوجيه: 19 صفًا + 20 اختبارًا دائمًا + F-015/TSK-104 (`AIA_ROUTING_MATRIX.md`) | S108 تكملة 4 |
| AIA-7 | 5 حراس دائمين في check.sh (TSK-105..109) + F-016 مُصلحة | S108 تكملة 5 |

### خطوط إثبات AIA-R1..R13 (معيار AIA-C)
- **R1 (التوجيه قبل التنفيذ)**: كل قرار مفسَّر عبر `RoutingRecord`
  (routing_config.py:138 — scores/matched_signals/ideal/final/
  downgrade_path) ومُثبت في 30 golden T-034 + 20 اختبار مصفوفة. ✅
- **R2 (عالمية المجال)**: نواة عامة + overlay ويب اختياري (شق
  AIA-3: prompts/web_system.md ← core)؛ حياد مجالي مُختبر
  (TestIntentNonWeb: CLI/data/docs). ✅
- **R3 (عالمية اللغة)**: قاعدة مرآة اللغة في البرومبتات المعاد
  كتابتها (AIA-3)؛ حياد اللهجة مُقاس (TestIntentEgyptianDialect +
  TestIntentMixedArabicEnglish). ✅
- **R4 (حياد النموذج)**: بند «حياد الأسلوب» في ملفات الأدوار
  (مثل MICRO_WORKER:24-25)؛ بنية مخرجات صريحة؛ صفر اعتماد على
  سلوك نموذج بعينه في نصوص البرومبتات (تدقيق AIA-3). ✅
- **R5 (اقتصاد الرموز)**: قياسات قبل/بعد في AIA-3 مع إثبات ثبات
  السلوك عبر corpus R8 (snapshots خضراء بعد إعادة الكتابة). ✅
- **R6 (صلابة الحقن تتوسع)**: حارس دائم `check_injection_guard.py`
  بثلاث طبقات + إصلاح F-016 (21/21 ملف دور يحمل «بيانات لا أوامر»)؛
  **حد موثق**: تسييج نتائج التبعيات = F-013 مفتوحة مُسعَّرة C2/S3
  (توسيع NF-18 مرشح TSK). ✅ (مع Finding مُسعَّر)
- **R7 (لا أصل بلا تصنيف)**: 226/226 مصنَّفة (ACTIVE 29 /
  REFERENCE 17 / STALE 175 / DUMP 5) + حارس اليتامى الدائم يمنع
  العودة؛ أرشفة STALE-175 = قرار مالك معلَّق (لا يحجب البوابة —
  التصنيف كامل والحذف قرار مالك حصري R7). ✅
- **R8 (انحدار البرومبتات)**: corpus ذهبي `prompt_corpus.golden.json`
  (12 اختبار إعادة حية dict-equality) + حارس snapshots دائم في
  check.sh (TSK-108). ✅
- **R9 (تغطية ثنائية الاتجاه)**: الاتجاه صنف⇒برومبت مُثبت جدوليًا
  (AIA_ROUTING_MATRIX §2: 6 أدوار مسندة باستشهادات strategies.py)؛
  الاتجاه العكسي: 15 دورًا لا يصل إليها التوجيه = **F-014 مفتوحة
  مُسعَّرة C3/S4 بانتظار قرار مالك (إسناد أو شطب)**. ✅ (مع Finding)
- **R10 (إثبات القدرات)**: مفردات الاستراتيجيات مثبتة (حارس T-035)
  + TestR10CapabilityCorpusLink يربط القدرات المسندة بالـcorpus؛
  حقول ADR-007 وصفية-فقط حسب نص الـADR. ✅
- **R11 (مقاومة الهلوسة)**: «UNKNOWN فوق الاختراع» منزَّلة نصًا في
  البرومبتات المعاد كتابتها (AIA-3 — بند صريح في كل دور مُرقّى). ✅
- **R12 (اتساق النية عبر اللغات)**: مُثبت آليًا
  (TestTriplePhrasingConsistency: فصحى/مصري/إنجليزي ⇒ نفس
  الاستراتيجية والأدوار)؛ الفجوة المعجمية المقيسة = **F-015 مفتوحة
  مُسعَّرة C3/S3 → TSK-CEV-104 جاهزة**؛ سلوك النموذج الفعلي عبر
  اللغات = سيناريو يدوي موثَّق (QA_MASTER_PLAN §P6f) بلا ادعاء
  أتمتة. ✅ (مع Finding مُسعَّر)
- **R13 (الأفضل لا أول المتوافق)**: عتبات config حتمية مُختبرة
  (T-036) + downgrade_path مفسَّر في RoutingRecord + حالة الغموض
  المتعدد مبررة بنيويًا (TestIntentAmbiguousMultiIntent)؛ تحسين
  المحرك يمر حصرًا عبر TSK+ADR (AIA-X يرفض الاختيار الديناميكي
  بنموذج). ✅

### معايير AIA-C (كلها مستوفاة)
- [x] AIA-1..7 مغلقة ببواباتها في PROGRESS.md (الجدول أعلاه).
- [x] صفر ملف غير مصنَّف في agents_rules/ وnewskells/ وprompts/
  (226/226 — `AIA_INVENTORY.md` §الأرقام) + حارس دائم يمنع العودة.
- [x] كل برومبت ACTIVE: Score≥70 (27/27، منها 22=100/100 —
  `scripts/prompt_quality_score.py`) + تغطية corpus + snapshot ذهبي
  (goldens/prompts — 5 استراتيجيات × 6 أدوار قابلة للوصول).
- [x] مصفوفة توجيه خضراء: النوايا الست الإلزامية + اتساق ثلاثي
  الصياغات (20/20 اختبارًا — test_routing_matrix.py).
- [x] R1..R13 لكل منها سطر إثبات أعلاه (المفتوح منها Findings
  مُسعَّرة: F-013/F-014/F-015 — كلها C2-C3 بمسار حسم محدد).
- [x] غير المُختبر في CI موثَّق كسيناريوهات فحص يدوي
  (QA_MASTER_PLAN.md §P6f — 3 سيناريوهات، بلا ادعاء زائف).
- [x] `bash scripts/check.sh` ALL GREEN rc=0 (2231P/34S/0F) عند خط
  النهاية — شامل الحراس الخمسة الجدد.

**الحكم: G8.5 PASS. التالي بالترتيب المعدل (D-14): G9 (الانحدار) — G7 تبقى DEFERRED بقرار مالك وتسبق G12 وجوبًا.**
