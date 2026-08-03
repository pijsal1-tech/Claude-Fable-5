# RELEASE_READINESS_REPORT.md — editor_v4 (P8 Output, CORE-ONLY SCOPE v4.1)

> Final planning-stage gate assessment. Verdict is on the CURRENT codebase
> (nothing from M1–M5 executed yet — execution 0/19 TSK). Status fields live
> ONLY in PROGRESS.md. Scope bound by SECTION 0.8: Provider Layer excluded and
> never assessed here.

---

## 1. Gate Assessment (G1–G5)

### G1 — Core Correctness: ⚠️ CONDITIONAL FAIL
- **Blocking evidence**: BUG-01 (Confirmed C4/S2) — mode-agnostic parse
  (response_parser.py:parse:L107 takes no mode param; fallback L131–169
  synthesizes actions) → chat done-frame carries actions
  (server.py:L1698–1711) → frontend shows actions bar unconditionally
  (app.js:L1016–1020). Chat mode can surface executable actions, including
  destructive commands, from conversational replies.
- **Contributing**: NF-13 (bash fallback promotes prose code blocks to
  `commands`, parser L153–161).
- **What lifts the gate**: M1 (TSK-201 → TSK-101 → TSK-102) + QA-T05 green
  (3 fake replies incl. the `rm -rf` example produce zero actions in chat).

### G2 — Security: ⚠️ CONDITIONAL FAIL
- **Blocking evidence**:
  - NF-15 Zip-Slip: restore path uses `extractall` without member-path
    validation (server.py:L947–960) — `../evil.txt`, absolute paths, symlink
    members can escape the project root.
  - NF-18 raw prompt injection: file content interpolated into prompts
    without fencing (prompts/templates.py:build_prompt:L104–135).
- **Non-blocking noted**: NF-16; client-side render surface tracked as FI-10.
- **What lifts the gate**: TSK-105 (path_policy guard) + TSK-404 (fencing) +
  QA-T07 (4 malicious ZIPs → 400 + disk untouched) + QA-T12 green.
- **Threat-model context**: product posture is a local dev tool
  (localhost-bound); severity ratings already reflect this. Any exposure
  beyond localhost is out of contract until FI-12/TSK-502 land.

### G3 — Stability / Resource Safety: ⚠️ CONDITIONAL FAIL
- **Blocking evidence**:
  - BUG-03 (mechanism Confirmed C4/S2): context-budget bypass paths — file
    inject L1332–1339, attach path L1782–1791 (15×2000), full history L1654 —
    circumvent ContextBudget.pack (context/budget.py:L131).
  - NF-06: `ExecutionRegistry._tickets` never purged (core/execution.py —
    no deletion site exists).
  - NF-07: unbounded in-memory history growth.
  - NF-01: pending-cleanup executed outside the lock (server.py L106–114 vs
    L146–148) — race window.
  - NF-04: apply blocks the WS loop (L2213–2229 + L1862–1925) — long batches
    freeze streaming and cancel handling.
- **What lifts the gate**: TSK-103/TSK-104 + M3 (TSK-301…305) + QA-T06 and
  QA-T10 green.

### G4 — Maintainability: ⚠️ FAIL (NON-BLOCKING for release)
- **Evidence**: g1 server.py god-module (2,613 lines); NF-23 duplication
  bundle; BUG-04 three divergent ignore lists (file_manager L27–31 vs bridge
  L655–662 vs agent_tools L300–302); NF-14 41× broad `except Exception`.
- **What lifts the gate**: M2 (TSK-202/203) + TSK-305; longer-term FI-02/FI-08.
- **Rationale for non-blocking**: no user-facing correctness/security impact
  by itself; it raises regression risk, which QA-T08/T09/T14 mitigate.

### G5 — QA Coverage & Traceability: ✅ PASS
- QA_MASTER_PLAN.md defines QA-T03R + QA-T05…T14 with stubbed boundary and
  zero external AI calls; all 19 TSKs have "Validated by" links; 5
  traceability chains verified in both directions
  (BUG/NF → TSK → QA-T and QA-T → TSK → BUG/NF); positive findings NF-19
  (atomic writes) and NF-24 (zero import cycles) are pinned by regression
  tests in QA-T14.

---

## 2. Verdict

| Question | Verdict |
|---|---|
| Public / production release of current codebase | **NO-GO** (G1, G2, G3 conditional-fail) |
| Continue as local single-user dev tool meanwhile | Acceptable at operator's risk (threat model above) |
| Transition to **MODE B** (execute the roadmap) | **GO — immediately** |

**Shortest path to lifting the release block**:
M1 (TSK-201 → TSK-101 → TSK-102, TSK-103 → TSK-104, TSK-105) →
QA-T05/T06/T07 green → M2 (TSK-202/203) → QA-T08/T09 green →
re-assess G1–G3 (expected: all ✅) → release re-vote.
M3/M4/M5 harden further but are not on the minimal release-critical path
except TSK-301/304 which QA-T10 requires.

---

## 3. Program Reconciliation (v4.1 closure checklist)

| Item | State |
|---|---|
| Planning checkpoints | 40/40 (100%) — P1…P8 all complete |
| Execution tasks | 0/19 TSK (MODE B not started; awaiting user gate) |
| Documents produced | 9: PROGRESS, ARCHITECTURE_REVIEW, VERIFIED_BUGS, NEW_FINDINGS, MASTER_ROADMAP, IMPLEMENTATION_TASKS, QA_MASTER_PLAN, FUTURE_IMPROVEMENTS, RELEASE_READINESS_REPORT |
| BUG-02 | EXCLUDED per SECTION 0.8 — recorded once, never analyzed |
| providers/ | Never read, never cited, never tasked |
| Secrets | Zero secrets quoted in any document |
| Citations | All findings anchored file:function:line |
| Writes | docs/engineering/** only (MODE A respected) |

---

## 4. Handover — MODE B entry point

Awaiting explicit user approval to enter MODE B. Upon approval:

**نقطة البدء التنفيذية: TSK-201 ثم TSK-101 (مسار M1).**

Order rationale: TSK-201 (merge apply paths into `_apply_batch`) is a
dependency of TSK-101 (mode-aware parser + drop actions from chat done-frame),
which is a dependency of TSK-102 (bash fallback CMD: tag). First QA gate after
that trio: QA-T05.

---

## 5. Re-vote — Session 83 (2026-07-29) — TSK-622 / Owner decision D-4

> Post-execution re-assessment of G1–G5 on the CURRENT codebase
> (Stage 3: 24/26 TSK done; M1–M8 closed, M6 closed 5/5 in S83).
> Original §1–§4 preserved verbatim above — this section appends only.
> Scope unchanged: SECTION 0.8 still excludes providers/ from assessment.

### G1 — Core Correctness: ✅ PASS
- BUG-01 lifted: parser is mode-aware — `actions/response_parser.py:107`
  `parse(self, response, mode=None)`; chat mode disables the speculative
  fallback; chat done-frame carries `actions: []` (MASTER_REVIEW R-migration
  :203, VERIFIED). NF-13 closed with it (TSK-102, CMD: tag).
- Beyond the original blockers: RP-01 (delegate approval dead-end, found
  post-planning) fixed by TSK-601; TF-03 (broken panels) fixed by TSK-604.
- Live proof: QA-T05 + full regression **0 failed** (S83).

### G2 — Security: ✅ PASS (localhost threat model, unchanged)
- NF-15 lifted: `server.py:753` `_zip_member_violations` validates members
  before extraction (TSK-105; MASTER_REVIEW:304 VERIFIED-FIXED; QA-T07).
- NF-18 lifted on BOTH paths: `fence_attached` used in templates (TSK-404)
  AND now in the agent loop + knowledge path — `chain/agent_loop.py:230/:274`,
  `chain/knowledge.py:54/:204/:207` (TSK-602 closed ASF-01).
- Structural approval gate: TSK-603 moved enforcement into the tool layer
  (ASF-02 closed; `chain/agent_tools.py:535` correct-by-construction note).
- NF-16/ASF-04 resolved by owner decision D-1 (TSK-617, S83): code-defaults
  are now fail-closed — missing `force_command_approval` ⇒ True
  (`server.py:195`), missing/garbage allowlist section ⇒
  `enforce=True, allowlist={}` (`chain/agent_tools.py:68/:100`).
- Residual (documented, accepted): REST/WS without auth for 127.0.0.1-only
  posture — unchanged product contract (config.yaml + README deployment
  limits).

### G3 — Stability / Resource Safety: ✅ PASS
- BUG-03 lifted: both injection paths unified under ContextBudget via
  `context/facade.py:113` `gather_message_context` (TSK-103); the last
  pocket (delegate context, RP-03) closed by TSK-607.
- NF-06 lifted: `core/execution.py:351` `purge_terminal(keep_last=50)` +
  call site `server.py:434` (MASTER_REVIEW:367 VERIFIED-FIXED).
- NF-07 lifted: `select_history(..., _history_payload_policy(cfg))` —
  named policy gate (`server.py:46/:1004`; MASTER_REVIEW:368).
- NF-01 lifted: pending cleanup inside the lock (TSK-301;
  MASTER_REVIEW:362 VERIFIED-FIXED).
- NF-04 fully lifted: cancel fixed by TSK-304; the remaining WS-loop
  blocking (RF-01) resolved by threading `_apply_batch` + direct runner
  (TSK-606, S43).
- Live proof: QA-T06/T10 + regression 0F.

### G4 — Maintainability: ✅ PASS (was FAIL non-blocking)
- g1 god-module decomposed by M8: server.py now **2,141 lines** (was 2,613)
  with WS router (TSK-611), dispatch extraction (TSK-612), REST blueprints
  in `routes/` — 8 modules (TSK-613); mypy gate covers server.py + extracted
  units: **Success, 81 files** (TSK-614).
- NF-23.1–.4 all VERIFIED-FIXED (MASTER_REVIEW:506–509); BUG-04 closed via
  unified `core/ignore_rules.py` (MASTER_REVIEW:194); NF-14 remains partial
  by design — every intentional swallow tagged "NF-14 §N" in place, and
  TSK-618 narrowed path_policy's except.
- Note: G4's original "what lifts" (M2 + TSK-305) landed AND the
  longer-term decomposition (FI-02 equivalent) landed too — exceeding the
  original lifting condition.

### G5 — QA Coverage & Traceability: ✅ PASS (strengthened)
- Regression suite grew to **1,900 tests = 0 failed / 1,866 passed /
  34 skipped** (S83 — first-ever 0-failed run); `scripts/check.sh`
  ALL GREEN exit 0 for the first time (M6 closed 5/5).
- Traceability maintained through Stage 3: every TSK carries Evidence /
  pre-checks / Close-out blocks with file:line anchors; CHANGELOG and
  status table current.

### Re-vote Verdict

| Question | Original (§2) | Re-vote (S83) |
|---|---|---|
| Public / production release of current codebase | NO-GO | **GO** — within the documented localhost-single-user contract; no blocking gate remains |
| Continue as local single-user dev tool | Acceptable at risk | **Fully supported** — fail-closed defaults now protect misconfiguration |
| MODE B (execute roadmap) | GO | **Near-complete** — 24/26 TSK; remaining: TSK-622 (this document) + TSK-623 (hygiene archive, non-code) |

**Conditions attached to GO**: the localhost-only threat model in §1/G2
remains the product contract; any exposure beyond 127.0.0.1 requires the
documented config hardening (force_command_approval + allowlist — now also
the code-default per D-1). No open blocking findings; no undocumented
technical debt at time of vote (TECHNICAL_DEBT.md intentionally absent —
no debt exists to record, per D-2 close-out of TSK-605).

---

## CEV Program Addendum (D-12 / D-15) — Scorecard §5 + Conditional Re-vote — S108 تكملة 11

> يُلحق هذا المقطع بموجب D-12 («البطاقة → مقطع CEV في RRR») وD-15
> (تفويض المالك بتنفيذ كل ما لا يعتمد على G7). بوابات CEV المقفلة:
> G1–G6، G8، G8.5، G9، G10، G11 — كلها 🏁 PASS (أحد عشر تقريرًا
> مؤرخًا في MASTER_REVIEW). **G7 (Red Team) = DEFERRED BY OWNER
> (D-15)** — لذا هذه البطاقة **جزئية بحكم التعريف**: المحاور 1–9
> مُقيَّمة موضوعيًا بالأدلة؛ المحور 10 دليله النصي «§6 بلا S1/S2
> مفتوحة» يعتمد حصرًا على تنفيذ G7 ⇒ يُسجَّل DEFERRED بلا درجة.

### بطاقة الدرجات (Scorecard §5) — محاور 1–9 مُقيَّمة، المحور 10 مؤجَّل

| # | المحور | الدرجة | الدليل (طازج على الشجرة الحالية ddd84b4+) |
|---|--------|--------|--------------------------------------------|
| 1 | الصحة الوظيفية | **10/10** | `check.sh` ALL GREEN rc=0 — **2231 passed / 34 skipped / 0 failed** (86.48s)؛ 17 قسمًا مسمى كلها خضراء؛ goldens الثلاثة (chain 6 + prompts 9 سيناريو/24 خطوة + routing 30) replay خضراء ضمن التشغيلة |
| 2 | سلامة الأنواع | **10/10** | بوابة mypy فاشلة-عند-الخطأ في check.sh منذ T-010 بـ`--check-untyped-defs` (check.sh:12,21) على providers/ + chain/ + core/ + context/ + sessions/ + routes/ + server.py + desktop.py — خضراء في التشغيلة أعلاه؛ لا إضعاف (استثناء وحيد موثق بقرار مالك D-13 خيار 2 / TSK-CEV-102) |
| 3 | الأمان (حقن/أسرار/مسارات) | **10/10** | حُرّاس TSK-404 قائمة ومُحرَّسة دائمًا: `check_injection_guard.py` **4 طبقات** (templates حية + قاعدة «بيانات لا أوامر» 21/21 دورًا + أسوار DATA ONLY + الطبقة السلوكية الجديدة TSK-CEV-110: probe عدائي عبر build_prompt/to_prompt_block يخرج مسيَّجًا)؛ zip-slip مغلق (path_policy/TSK-105)؛ صفر credentials (scan_har_auth + فحص F-010 التاريخي)؛ CEV-F-013 محسومة هذه التكملة وCEV-F-016 محسومة (109a) |
| 4 | العقد التشغيلي | **10/10** | localhost أحادي المستخدم = العقد الموثق (§1/G2 أعلاه + fail-closed defaults per D-1)؛ سطح REST **مجمَّد عند 35 قاعدة بالضبط** — مثبَّت باختبار حي (tests/unit/test_rest_blueprints.py:83 `assert len(_current_rules()) == 35`، أخضر) |
| 5 | التوثيق الحاكم | **10/10** | PROGRESS.md محدَّث حتى تكملة 11 (رؤوس حية + سجل append-only)؛ الترويسة الراكدة §0.5 أُصلحت (S~95 — موثقة PROGRESS:944)؛ حالة المهام في PROGRESS حصرًا (SECTION 0.7)؛ DECISION_LOG حتى D-15؛ NEW_FINDINGS كل بنوده محسومة أو مُحالة FI/قرار مالك |
| 6 | الديون والتحسينات | **10/10** | G11 🏁 PASS: صفر دين خفي (مسح 6 وسوم +5 طوعية + «مؤقت»)؛ **كل مؤجَّل له بند FI مُسعَّر**: FI-01..FI-16 (FUTURE_IMPROVEMENTS.md — 16 بندًا بكلفة/فائدة/شروط)؛ ادعاء «صفر دين غير مُدار» أُعيد التحقق منه بالدليل (@03c7eab يصمد) |
| 7 | قابلية الاستئناف | **10/10** | دليل حي غير قابل للطعن: هذه الجلسة نفسها (S108) عبرت **51 تصفير بيئة** واستأنفت كل مرة من PROGRESS + آخر التقاط بوت حرفيًا — بما فيها استعادة عمل غير ملتزم مرة واحدة فقط (Wipe #48) بفضل انضباط الالتزام المبكر؛ V3_RESUME_SESSION.md + بروتوكول الاستعادة مجرَّبان ×51 |
| 8 | التغليف | **10/10** | desktop.spec موجود ويُفسَّر سليمًا (ast.parse OK)؛ desktop.py ضمن بوابة mypy؛ لا مسارات مكسورة (حارس manifest 105 + حارس اليتامى 106 يغطيان أصول agents_rules؛ فحص T-034/goldens يغطي مسارات fixtures) |
| 9 | ذكاء الوكلاء (Agent Intelligence) | **10/10** | AIA-C كاملة ومقفلة (G8.5 🏁 PASS تكملة 6): AIA-1..7 مغلقة ببواباتها (MASTER_REVIEW:1110–1166 — جرد 226 أصلًا 100% + مصفوفة توجيه 19 صفًا + 20 اختبارًا دائمًا + corpus 30 + 5 حراس دائمين) + خطوط إثبات AIA-R1..R13 مستوفاة |
| 10 | صمود الفريق الأحمر | **DEFERRED BY OWNER (D-15)** | الدليل المطلوب نصيًا: «§6 بلا S1/S2 مفتوحة» — يستلزم تنفيذ جولة G7 الهجومية (قراءة-فقط) التي أجّلها المالك صراحة؛ لا يمكن تقييمه موضوعيًا بدونها ولا يُخمَّن |

**المجموع الموضوعي (محاور 1–9): 90/90.** المحور 10 غير مُقيَّم
(DEFERRED) ⇒ **المجموع الكلي من 100 غير قابل للحسم** حتى تنفيذ G7؛
عتبة الإطلاق ≥95 تبقى **غير محسومة رياضيًا** (المدى الممكن بعد G7:
90–100 — أي أن العتبة قابلة للتحقق فقط إن حقق المحور 10 ≥5/10،
لكن الحسم قرار بوابة لا استقراء).

### إعادة تصويت RRR — نسخة مشروطة (لا نهائية)

| السؤال | تصويت S83 | إعادة التصويت المشروطة (S108 CEV) |
|---|---|---|
| إطلاق عام/إنتاجي للكود الحالي | GO (ضمن عقد localhost) | **GO-conditional**: كل الأدلة الموضوعية تحسّنت منذ S83 (1900→2231 اختبارًا، 5 حراس دائمين جدد، تسييج NF-18 اكتمل بمساراته الثلاثة، صفر دين خفي مُعاد التحقق) — **الشرط المعلَّق الوحيد: G7** (بأمر مالك D-15). لا يُرقَّى لـGO نهائي إلا بعد G7 + بطاقة ≥95 |
| الاستمرار كأداة تطوير محلية أحادية المستخدم | Fully supported | **Fully supported — أقوى من S83** (نفس العقد + أسيجة أعمق) |
| برنامج CEV (D-12) | — | **مكتمل جزئيًا بحدود D-15**: 11/12 بوابة 🏁 PASS؛ G7 DEFERRED؛ G12 هذه = جزئية بحكم التعريف |

**إقرار CEV-R12: لا يُصدَر** — الإقرار الرسمي وإغلاق G12 الكامل
محجوبان حصرًا بتنفيذ G7 ثم إكمال المحور 10 وإعادة التصويت النهائية.

### المحجوب حصرًا بقرار تأجيل G7 (المطلوب رابعًا في D-15)
1. **المحور 10** من بطاقة الدرجات (صمود الفريق الأحمر).
2. **حسم المجموع الكلي ≥95** (عتبة الإطلاق) — رياضيًا غير قابل للحسم بلا المحور 10.
3. **إعادة تصويت RRR النهائية** (ترقية GO-conditional إلى GO/NO-GO نهائي).
4. **إقرار CEV-R12 وإغلاق G12 رسميًا**.

### المحجوب بقرارات مالك أخرى (خارج نطاق D-15 — للتمييز لا للخلط)
- **F-003**: مصير fixture `.env` (أُعيد يدويًا ×34 عبر المسحات).
- **F-010**: مصير `chain/hh.har` (مفحوص: صفر أسرار — إبقاء/حذف).
- **F-014**: 15 دورًا في manifest لا يصل إليها توجيه (إسناد أو شطب).
- **STALE-175**: أرشفة الوثيقة الراكدة.
- **FI-13..FI-16**: قرار تنفيذ بنود التحسين (V3: التنفيذ حصري للمالك).
- **توحيد حارس NF-18 في system السلاسل** (الحد الموثق في TSK-CEV-110 — يغيّر 21 لقطة sha256).
