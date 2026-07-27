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
