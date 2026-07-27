# PROGRESS.md — editor_v4 Engineering Program (Single Source of Truth for Status)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-07-27 (Session 1) |
| stage | PLANNING (MODE A) |
| current-phase | P1 — Architecture Review |
| current-task | P1(a) repo map & module responsibilities |
| completion % (planning) | 0% (0 / 40 phase-checkpoints) |
| completion % (execution) | N/A (task table empty until P5) |
| repository | pijsal1-tech/Claude-Fable-5 (branch: genspark_ai_developer) |

### Completion formula
- Planning stage: completed phase-checkpoints ÷ total checkpoints (= 40).
- Execution stage: completed TSK ÷ total TSK (after P5 fills the task table).

### Context drift notes (Section 0.2)
- CONTEXT hint said `static/app.js ~2,708 lines` — actual: **3,723 lines** (drift, verify function line hints).
- CONTEXT hint said `server.py ~2,614 lines` — actual: **2,613 lines** (match).
- `accounts_use_ai.json` is **NOT present in the repository** (likely gitignored — verify in P1e; secrets policy still applies to config.yaml).
- `providers/` contains **11 files** including `pool.py`, `capacity.py`, `budget.py`, `genspark.py`, `alle_ai.py` not mentioned in CONTEXT — must be covered in P1c.
- `test---results/` exists at repo root (flat files, no subdirs) — matches CONTEXT policy scope.

---

## PHASE TABLE (P1–P8, checkpoints per Section 6)

### P1 — ARCHITECTURE_REVIEW.md (7 checkpoints) — budget 25%
| # | Checkpoint | Status |
|---|---|---|
| P1a | Repo map & module responsibilities (major dirs = executed code/config) | ⬜ |
| P1b | Runtime flows: WebSocket lifecycle, AI request lifecycle, streaming, session lifecycle | ⬜ |
| P1c | Provider architecture & context builder (all 11 provider files: full-read base/registry + 2 most-used; skim rest, declare skimmed) | ⬜ |
| P1d | Parser + edit/plan/build pipelines | ⬜ |
| P1e | Security boundaries, backup, config loading, error handling | ⬜ |
| P1f | Dependency map — Mermaid graph + adjacency table (both) | ⬜ |
| P1g | Risks: bottlenecks, duplication, debt, coupling, scalability | ⬜ |

### P2 — VERIFIED_BUGS.md (6 checkpoints) — budget 15%
| # | Checkpoint | Status |
|---|---|---|
| P2a | BUG-01 Mode Confusion — verify & classify | ⬜ |
| P2b | BUG-02 No Provider Fallback — verify & classify | ⬜ |
| P2c | BUG-03 Context Payload Overflow — verify & classify | ⬜ |
| P2d | BUG-04 test---results/ contamination block in file_manager.py — verify | ⬜ |
| P2e | All other claims in test---results/ archive classified | ⬜ |
| P2f | Every C4 item has a spawned TSK reference; zero secrets quoted | ⬜ |

### P3 — NEW_FINDINGS.md (6 checkpoints) — budget 15%
| # | Checkpoint | Status |
|---|---|---|
| P3a | Race conditions & threading (ws_handler / _recv_worker / chunk_queue) + async issues | ⬜ |
| P3b | Memory leaks, large-context, streaming issues | ⬜ |
| P3c | Provider/retry/fallback + parser ambiguity & mode handling | ⬜ |
| P3d | Error handling, path traversal & security, prompt injection | ⬜ |
| P3e | File corruption, performance, dead/duplicate code, circular deps | ⬜ |
| P3f | Every category has findings or explicit "none found" line | ⬜ |

### P4 — MASTER_ROADMAP.md (4 checkpoints) — budget 10%
| # | Checkpoint | Status |
|---|---|---|
| P4a | Milestone list with all mandatory fields | ⬜ |
| P4b | M1 rule applied (S1-Confirmed set from P2+P3, ordered by risk; else verification infra) | ⬜ |
| P4c | Dependencies & rollback strategy per milestone | ⬜ |
| P4d | DoD satisfied & justified from actual P2/P3 output | ⬜ |

### P5 — IMPLEMENTATION_TASKS.md (4 checkpoints) — budget 15%
| # | Checkpoint | Status |
|---|---|---|
| P5a | Atomic tasks for every Confirmed issue & every C4 item | ⬜ |
| P5b | Full task fields (type, files, LOC, risk, deps, Fixes, Validated-by) | ⬜ |
| P5c | Dependency graph acyclic | ⬜ |
| P5d | Task table copied into PROGRESS.md (status lives here only) | ⬜ |

### P6 — QA_MASTER_PLAN.md (5 checkpoints) — budget 10%
| # | Checkpoint | Status |
|---|---|---|
| P6a | QA-T01–T04 inherited as historical baseline (re-run after M1) | ⬜ |
| P6b | QA-T03R redesigned | ⬜ |
| P6c | QA-T05–T10 fully specified | ⬜ |
| P6d | QA-T11+ new coverage (mocked providers, sandboxed security) | ⬜ |
| P6e | Bidirectional traceability spot-check (5 chains both directions) | ⬜ |

### P7 — FUTURE_IMPROVEMENTS.md (4 checkpoints) — budget 5%
| # | Checkpoint | Status |
|---|---|---|
| P7a | Architecture / performance / security / DX items | ⬜ |
| P7b | Observability / caching / queueing / plugin / provider abstraction | ⬜ |
| P7c | Testing / docs / scalability items | ⬜ |
| P7d | Each item: benefit + cost + prerequisite + SHORT/MID/LONG tag | ⬜ |

### P8 — RELEASE_READINESS_REPORT.md (4 checkpoints) — budget 5%
| # | Checkpoint | Status |
|---|---|---|
| P8a | Gates G1–G5 evaluated with evidence links | ⬜ |
| P8b | Go/No-Go verdict stated | ⬜ |
| P8c | Blocking TSK list if No-Go | ⬜ |
| P8d | PROGRESS.md reconciliation; stage → EXECUTION with M1 tasks ⬜ | ⬜ |

**Total checkpoints: 40**

---

## TASK TABLE

> فارغ حتى تكتمل P5 (يُنسخ جدول المهام هنا مع عمود الحالة — الحالة تعيش هنا فقط).

| TSK | Type | Title | Milestone | Status |
|---|---|---|---|---|
| — | — | (populated by P5) | — | — |

---

## SESSION LOG

### Session 1 — 2026-07-27
- **Actions:**
  - Cloned repo `pijsal1-tech/Claude-Fable-5` → `/home/user/webapp`, created branch `genspark_ai_developer`.
  - TIER A: verified file inventory & line counts (server.py=2613, app.js=3723, worker.py=433, providers=11 files, actions=5 files, config.yaml=191).
  - Confirmed `accounts_use_ai.json` absent from repo; `test---results/` present at root.
  - STEP 0: created this PROGRESS.md with full phase/checkpoint tables.
- **TIER B actions:** none.
- **Decisions:**
  - Repo `Claude-Fable-5` identified as the editor_v4 project (contains all CONTEXT-listed files); other repos (Zizo = older copy, 27-07 = QA archive mirror) treated as external evidence only, not part of this workspace.
  - Context drift on app.js line count logged (see header).
- **RESUME POINT:** `P1a — begin repo map: full read of server.py from L1; then actions/, providers/base.py+registry.py, config.yaml structure (redact values).`

---

## STATUS LEGEND
⬜ Pending | 🟨 In-Progress | ✅ Done | 🔴 Blocked | ⏭️ Skipped(justify)
