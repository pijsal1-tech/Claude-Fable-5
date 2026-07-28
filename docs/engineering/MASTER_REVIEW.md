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

## R0 — Strategic Architecture Assessment
*(TODO — المرحلة التالية. Session 25.)*

---

## R1 — Repository Understanding (Delta)
*(TODO — دلتا فقط فوق ARCHITECTURE_REVIEW.md: أثر TSK-101→502 على التدفقات.)*

---

## R2 — Strengths Register
*(TODO)*

---

## R3 — Subsystem Map + Architecture Scorecard
*(TODO)*

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
