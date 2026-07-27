# PROGRESS.md — editor_v4 Engineering Program (CORE-ONLY SCOPE v4.1)

> هذا الملف هو المصدر الوحيد لحالة المهام والمراحل (SECTION 0.7).
> جميع الوثائق الأخرى تُشير إلى المعرّفات فقط ولا تحتوي حقول حالة.
> النطاق محكوم بـ SECTION 0.8: النظام الأساسي فقط — Provider Layer خارج النطاق كليًا.

---

## HEADER

| Field | Value |
|---|---|
| last-updated | 2026-07-27 (Session 3 — P2 complete) |
| stage | PLANNING (MODE A) |
| current-phase | P3 — New Findings |
| current-task | P3(a) Race conditions & threading |
| completion % (planning) | 32.5% (13 / 40 in-scope phase-checkpoints) |
| completion % (execution) | N/A (task table empty until P5) |
| repository | pijsal1-tech/Claude-Fable-5 (branch: genspark_ai_developer) |
| governing prompt | MASTER ENGINEERING PROMPT v4.1 (CORE-ONLY SCOPE) |

### Completion formula
- Planning stage: completed IN-SCOPE phase-checkpoints ÷ total in-scope checkpoints (= 40).
- Execution stage: completed TSK ÷ total TSK (after P5 fills the task table).

---

## SCOPE POLICY (per SECTION 0.8 — binding on every row below)

OUT OF SCOPE — never reviewed, analyzed, planned, or tasked:
- `providers/` (entire directory, 11 files — listed once in repo map only)
- provider architecture / registry / base classes / fallback / retry logic
- budget & capacity handling / provider-side streaming / provider authentication
- account management / provider routing / any specific vendor integration
- server.py endpoints `api_models` + `api_switch_model` (provider-routing — existence recorded only)
- BUG-02 (Provider fallback) — recorded once as EXCLUDED, no verification

IN SCOPE (analysis focus):
- `server.py` (core pipeline; outbound provider calls = opaque boundary)
- `core/`, `chain/`, `actions/`, `context/` (excluding provider-selection branches), `runners/`, `static/`, `src/`, `tests/`
- WebSocket lifecycle, session management, in-app streaming (server→frontend),
  parsers, file/workspace management, build system, performance, memory,
  security, error handling, QA, maintainability, scalability, technical debt,
  dependency graph, documentation, roadmap, task planning.

---

## CONTEXT DRIFT NOTES (Section 0.2 — verified this session against actual code)

| CONTEXT hint | Actual (verified) | Note |
|---|---|---|
| server.py ~2,614 lines | 2,613 lines | match |
| static/app.js ~2,708 lines | 3,723 lines | DRIFT — all app.js line hints unreliable |
| ws_handler ~L983 | server.py:L2213 | DRIFT (major) |
| _process_ai_chat ~L599 | function name NOT FOUND in server.py — closest core dispatch: `_dispatch_chat_message` L1285, `_handle_ws_message` L1714 | potential Stale-Context — settle in P1b |
| _safe_ws_send ~L590 | function name NOT FOUND — nearest send helpers: `_json_sender` L331, `WsFrameSink._send` L233 | potential Stale-Context — settle in P1b |
| initWebSocket ~L53 | static/app.js:L143 | drift |
| handleWSMessage ~L81 | static/app.js:L179 | drift |
| sendMessage ~L449 | static/app.js:L785 | drift |
| appendStreamChunk ~L581 | static/app.js:L928 | drift |
| accounts_use_ai.json [SECRETS] | NOT in repo (gitignored — .gitignore:L18) | out-of-scope file; exclusion confirmed |
| actions/ = 4 modules | 5 files (incl. __init__.py), 1,021 LOC total | match |
| test---results/ exists | exists at repo root; sibling `test-results/` also exists | BUG-04 must distinguish BOTH names |

EARLY EVIDENCE (pre-P2, recorded for P2 pickup — not yet classified):
- `actions/file_manager.py:L27-31` `IGNORE_DIRS` contains `"test-results"` but
  NOT `"test---results"` (triple-dash). Both directories exist at repo root.
  → BUG-04 claim ("block exists and works") is at risk. Full verification in P2.

---

## PHASE TABLE (P1–P8, in-scope checkpoints per Section 6 — total 40)

### P1 — ARCHITECTURE_REVIEW.md (7 checkpoints) — budget 25%
| # | Checkpoint | Status |
|---|---|---|
| P1a | Repo map & module responsibilities (providers/ listed as OUT OF SCOPE, vendored libs listed only) | ✅ |
| P1b | Runtime flows: WebSocket lifecycle, AI request lifecycle up to out-of-scope boundary, in-app streaming (server→frontend), session lifecycle | ✅ |
| P1c | Context builder & context engine (provider-selection branches marked out of scope) | ✅ |
| P1d | Parser + edit/plan/build pipelines | ✅ |
| P1e | Security boundaries, backup, config loading, error handling | ✅ |
| P1f | Dependency map — Mermaid graph + adjacency table (Provider Layer = single collapsed external node) | ✅ |
| P1g | Risks: bottlenecks, duplication, debt, coupling, scalability | ✅ |

### P2 — VERIFIED_BUGS.md (6 checkpoints) — budget 15%
| # | Checkpoint | Status |
|---|---|---|
| P2a | BUG-01 Mode Confusion — verify & classify | ✅ Confirmed C4/S2 |
| P2b | BUG-02 — record EXCLUDED (out of scope) once, no verification | ✅ EXCLUDED recorded |
| P2c | BUG-03 Context Payload Overflow — verify context engine & payload size only | ✅ Partially-Confirmed (mechanism C4/S2) |
| P2d | BUG-04 test---results/ contamination block — verify block exists AND works (note: early evidence above) | ✅ (a) Partial / (b) Refuted C4/S3 |
| P2e | Sweep all other IN-SCOPE claims in test---results/ archive; out-of-scope claims → "not assessed" table | ✅ A1–A7 + X1–X4 |
| P2f | DoD check: every C4 has spawned TSK; zero secrets quoted | ✅ |

### P3 — NEW_FINDINGS.md (13 checkpoints = categories) — budget 15%
| # | Category | Status |
|---|---|---|
| P3a | Race conditions & threading (ws_handler / recv workers / queues) | ⬜ |
| P3b | Async issues | ⬜ |
| P3c | Memory leaks | ⬜ |
| P3d | Large-context handling | ⬜ |
| P3e | In-app streaming (server→frontend) | ⬜ |
| P3f | Parser ambiguity & mode handling | ⬜ |
| P3g | Error handling | ⬜ |
| P3h | Path traversal & security | ⬜ |
| P3i | Prompt injection | ⬜ |
| P3j | File corruption | ⬜ |
| P3k | Performance | ⬜ |
| P3l | Dead/duplicate code | ⬜ |
| P3m | Circular dependencies | ⬜ |

### P4 — MASTER_ROADMAP.md (3 checkpoints) — budget 10%
| # | Checkpoint | Status |
|---|---|---|
| P4a | Milestones drafted with full fields (no milestone touches out-of-scope code) | ⬜ |
| P4b | M1 RULE applied & justified from actual P2/P3 output | ⬜ |
| P4c | DoD verified | ⬜ |

### P5 — IMPLEMENTATION_TASKS.md (4 checkpoints) — budget 15%
| # | Checkpoint | Status |
|---|---|---|
| P5a | Atomic tasks for every Confirmed in-scope issue + every C4 | ⬜ |
| P5b | Bidirectional traceability fields filled (Fixes / Validated-by) | ⬜ |
| P5c | Dependency graph acyclic | ⬜ |
| P5d | Task table copied into PROGRESS.md (status column here only) | ⬜ |

### P6 — QA_MASTER_PLAN.md (5 checkpoints) — budget 10%
| # | Checkpoint | Status |
|---|---|---|
| P6a | QA-T01–T04 inherited as historical baseline; provider-substance tests retired | ⬜ |
| P6b | QA-T03R redesigned | ⬜ |
| P6c | QA-T05–T10 fully specified (out-of-scope boundary STUBBED — zero external AI calls) | ⬜ |
| P6d | QA-T11+ coverage added per Section 6 list | ⬜ |
| P6e | Traceability spot-check: 5 chains BUG→TSK→QA-T both directions | ⬜ |

### P7 — FUTURE_IMPROVEMENTS.md (1 checkpoint) — budget 5%
| # | Checkpoint | Status |
|---|---|---|
| P7a | All categories covered with benefit/cost/prerequisite + SHORT/MID/LONG tags (provider abstraction excluded) | ⬜ |

### P8 — RELEASE_READINESS_REPORT.md (1 checkpoint) — budget 5%
| # | Checkpoint | Status |
|---|---|---|
| P8a | Gates G1–G5 assessed; Go/No-Go verdict stated (CORE SYSTEM only); PROGRESS.md reconciled | ⬜ |

---

## TASK TABLE

> فارغ حتى تكتمل P5 (per SECTION 5 STEP 0).

| TSK-ID | Type | Title | Milestone | Status |
|---|---|---|---|---|
| — | — | (populated by P5) | — | — |

---

## SESSION LOG

### Session 1 — 2026-07-27 (v4.1 CORE-ONLY bootstrap)
- **Governing change**: program restarted under MASTER PROMPT v4.1 (CORE-ONLY SCOPE).
  Previous docs/engineering/ was deleted upstream (commit `1ec7006`); prior
  PROGRESS content treated as historical evidence only (readable via
  `git show d5dd3ec:docs/engineering/PROGRESS.md`).
- **Checkpoints touched**: none yet (STEP 0 only).
- **TIER A actions**: repo cloned; directory map taken; function-location grep on
  server.py + static/app.js + actions/file_manager.py; .gitignore checked;
  context-drift table above populated.
- **TIER B actions**: none.
- **Decisions**:
  1. `_process_ai_chat` and `_safe_ws_send` not found by name in server.py —
     candidates `_dispatch_chat_message` (L1285) / `_handle_ws_message` (L1714) /
     `_json_sender` (L331); resolve as Stale-Context or renamed in P1b.
  2. Early BUG-04 evidence logged (IGNORE_DIRS lacks `test---results`) — NOT
     classified yet; P2d will do the full static/runtime verification.
  3. Checkpoint total fixed at 40 (7+6+13+3+4+5+1+1).
- **EXACT RESUME POINT (superseded by Session 2)**: P1a — begin repo map.

### Session 2 — 2026-07-27 (P1 complete → ARCHITECTURE_REVIEW.md)
- **Checkpoints completed**: P1a–P1g (all 7) → `docs/engineering/ARCHITECTURE_REVIEW.md`.
- **TIER A actions** (sandbox reset → repo re-cloned first):
  - server.py read ~95% (skipped only out-of-scope `api_models`/`api_switch_model`
    L968–1075 per SCOPE POLICY). Key anchors: `ws_handler` L2213,
    `_handle_ws_message` L1714, `_dispatch_chat_message` L1285,
    `_build_session_context` L1253, `_WSAdapter` L210–238, `_json_sender` L331,
    `RUNNERS` L305–311, `_apply_single_action` L2243–2280, `main()` L2326–2609,
    provider boundary points L1657 + L1524–1528 (opaque, not entered).
  - Full reads: actions/file_manager.py, actions/response_parser.py,
    chain/path_policy.py; interface reads: context/{facade,engine,budget,
    safe_reader}.py, core/{app_context,execution,session_context}.py,
    chain/{bridge,executor,agent_loop}.py, runners/*, worker.py,
    sessions/{store,retention}.py, prompts/templates.py, config.yaml keys,
    static/app.js key flows, tests/ inventory (103 files).
- **TIER B actions**: none.
- **Decisions**:
  1. Stale-Context candidates settled at evidence level: `_process_ai_chat` /
     `_safe_ws_send` do NOT exist by name; actual equivalents are
     `_dispatch_chat_message` L1285 / `_handle_ws_message` L1714 /
     `_WSAdapter._send` + `_json_sender` L331. Formal classification
     (Stale-Context) to be recorded in P2 alongside the bug sweep.
  2. P1 risk handoffs g1–g12 recorded in ARCHITECTURE_REVIEW.md §(g);
     g11 feeds P2d (BUG-04), g2/g3/g4 feed P3l, g6 feeds P3a, g7 feeds P3k,
     g8 feeds P3h, g10 feeds P3e/P3g, g9 feeds P7.
  3. Pre-classified evidence held for P2: BUG-01 (parser mode-agnostic —
     response_parser.py:`parse()` L107 takes no mode param; aggressive fallback
     L131–169; chat-mode done frame ships actions server.py:L1698–1711);
     BUG-03 (ContextBudget.pack budget.py:L131 exists but direct-injection
     paths server.py:L1332–1339 / L1786–1791 bypass it); BUG-04 (IGNORE_DIRS
     file_manager.py:L27–31 lacks `test---results`).
- **EXACT RESUME POINT**: P2a — BUG-01 verification: start from evidence
  response_parser.py:L107 (mode-agnostic parse) + server.py:L1698–1711
  (chat done frame with actions); next 3 items → (1) read test---results/
  archive claims for BUG-01/03/04 (QA-evidence read only), (2) classify
  BUG-01 then BUG-03/BUG-04 with confidence ladder + severity, (3) record
  BUG-02 as EXCLUDED (P2b) and build the not-assessed table (P2e);
  output file: docs/engineering/VERIFIED_BUGS.md.

### Session 3 — 2026-07-27 (P2 complete → VERIFIED_BUGS.md)
- **Checkpoints completed**: P2a–P2f (all 6) → `docs/engineering/VERIFIED_BUGS.md`.
- **TIER A actions** (sandbox reset → repo re-cloned; pushed P1 commit `2150c6d` first):
  - Read full historical QA archive: `test---results/` (00_QA_PLAN, T01–T04
    results, 5 prompt files) + `test-results/` inventory (T01–T03 subdirs).
  - Re-verified code evidence: response_parser.py L107/L131–169 (mode-agnostic
    parse + aggressive fallback); server.py L1698–1711 (done frame carries
    actions in chat), L1332–1339 + L1782–1791 (budget-bypass injection paths),
    L1654 (full history passed); app.js L193–196 + L1016–1020 (actions bar
    shown regardless of mode); three independent ignore-lists compared:
    file_manager.py L27–31 vs chain/bridge.py L655–662 vs agent_tools.py
    L300–302 — none blocks `test---results`; grep: zero `scan_start` frames.
- **TIER B actions**: none.
- **Decisions / verdicts**:
  1. BUG-01 Confirmed C4/S2 — full 3-layer static chain (parser → server → UI).
  2. BUG-02 recorded once as EXCLUDED (0.8) — no verification performed.
  3. BUG-03 Partially-Confirmed — in-scope mechanism (budget bypass) C4/S2;
     provider timeout symptom Not-Assessed (out of scope).
  4. BUG-04 — claim (a) block exists: Partially-Confirmed (only old name, only
     file_manager path); claim (b) block works: **Refuted** C4/S3.
  5. Archive sweep: A1(C2→P3k), A2(not-assessed/LLM), A3 scan_start absent
     Confirmed C3/S4, A4+A7 Stale-Context, A5 folded into BUG-04,
     A6 backend-subpath claim deferred to P3h as fresh investigation;
     X1–X4 out-of-scope not-assessed table.
- **EXACT RESUME POINT**: P3a — Race conditions & threading: start from
  ws_handler synchronous loop server.py:L2217–2225 + g5 (REST globals vs WS
  SessionContext dual-state) + g6 (unthreaded apply_all_actions in WS loop);
  next 3 items → (1) read core/execution.py cancel/ticket race surface fully,
  (2) EventBus/_WSAdapter lock discipline server.py:L210–238 + L331,
  (3) chat_history/session_mgr concurrent append paths; then proceed P3b–P3m;
  output file: docs/engineering/NEW_FINDINGS.md (13 categories, single doc).
