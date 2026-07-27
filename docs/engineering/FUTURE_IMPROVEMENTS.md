# FUTURE_IMPROVEMENTS.md — editor_v4 (P7 Output, CORE-ONLY SCOPE v4.1)

> Non-blocking improvements beyond the M1–M5 roadmap. Each item: benefit / cost /
> prerequisite + horizon tag (SHORT ≤1 sprint, MID 2–4 sprints, LONG >4 sprints).
> Status lives ONLY in PROGRESS.md. Scope bound by SECTION 0.8.

## Scope exclusion (binding)

Provider abstraction, fallback/retry/budget-routing, vendor adapters, and any
`providers/` refactor are **EXCLUDED** per SECTION 0.8. No FI item below touches
that layer, and none may be reinterpreted to do so.

---

## Architecture

### FI-01 — Unify REST/WS session state [MID]
- **Source**: NF-03 (dual-state), risk g5 (ARCHITECTURE_REVIEW).
- **Benefit**: eliminates the REST-globals vs WS `SessionContext` split
  (server.py REST endpoints mutate module globals while WS paths use
  per-connection `SessionContext`), removing an entire class of stale-state
  bugs and making NF-01/NF-02 style races structurally impossible to reintroduce.
- **Cost**: medium — touch every REST endpoint; needs a session-resolution
  shim (token/project_id → SessionContext) and regression pass over QA-T10.
- **Prerequisite**: TSK-302 (project_id registration policy) merged first, so
  the unified state has a well-defined keying rule.

### FI-02 — Split server.py god-module [MID]
- **Source**: risk g1 (2,613 lines, routes + WS + orchestration + config in one file).
- **Benefit**: reviewability, testability, smaller blast radius per change;
  unblocks parallel work on M3/M4.
- **Cost**: medium-high — mechanical extraction (routes/, ws/, orchestration/)
  but every import site and the RUNNERS dict (L305–311) must be re-anchored;
  all citation-based docs need a line-anchor refresh afterward.
- **Prerequisite**: M1 + M2 complete (don't refactor under confirmed-S2 bugs).

### FI-03 — Graceful shutdown discipline [SHORT]
- **Source**: NF-05 (daemon-only threads at L1469/L1619/L2127; no join/drain on exit).
- **Benefit**: no truncated writes or half-applied batches on process exit;
  clean CI teardown.
- **Cost**: low — signal handler that calls `ExecutionRegistry` cooperative
  cancel for all live tickets, then bounded join.
- **Prerequisite**: TSK-304 (cancel checkpoints in batch) so cancel is honored
  mid-apply.

## Scalability

### FI-04 — Activate the redis/worker seam [LONG]
- **Source**: risk g9 (single-process, in-memory registry/history).
- **Benefit**: horizontal scale-out; run isolation per worker; survives restarts.
- **Cost**: high — externalize ticket state + history; WS affinity or pub/sub
  fan-out for stream frames.
- **Prerequisite**: FI-01 (single state model) + TSK-303 (ticket purge) so the
  externalized store isn't seeded with an unbounded structure.

### FI-05 — Incremental ProjectIndex persistence [MID]
- **Source**: NF-20/21 (sequential scans), builds on TSK-501's shared index.
- **Benefit**: cold-start search latency drops from full-rescan to
  load+delta; large projects (5k+ files, QA-T13 target) open instantly.
- **Cost**: medium — on-disk index format + invalidation via the existing
  write-through hooks; atomic write pattern already established (NF-19).
- **Prerequisite**: TSK-501 merged.

## Maintainability

### FI-06 — Structured logging [SHORT]
- **Source**: NF-14 (41× `except Exception`, many silent), TSK-305 follow-on.
- **Benefit**: every swallowed exception becomes a structured, greppable event;
  QA failures become diagnosable without reproduction.
- **Cost**: low — stdlib `logging` with JSON formatter; no new dependency.
- **Prerequisite**: TSK-305 (narrowed excepts) so logging isn't wired to
  handlers that are about to change shape.

### FI-07 — Split static/app.js into ES modules [MID]
- **Source**: 3,723-line single file; NF-10/NF-11 fixes land here.
- **Benefit**: isolates stream-rendering (L928–962), WS lifecycle (L154–201),
  and markdown/actions UI (L964–1030, L2281–2295) into testable units.
- **Cost**: medium — no bundler today; either native ES modules or a minimal
  build step; manual smoke of every mode (chat/plan/build/edit).
- **Prerequisite**: M4 complete (don't split while stream renderer is being rewritten).

### FI-08 — Quality guards in check.sh [SHORT]
- **Source**: NF-23 (duplication bundle), NF-24 (zero import cycles — keep it that way).
- **Benefit**: regression tripwires: AST import-cycle check, grep-guards for
  re-introduced duplicate constants (e.g. the L128/L2240 dup) and for direct
  `ws.send` outside `_WSAdapter`.
- **Cost**: low — extend existing script; runs in CI in seconds.
- **Prerequisite**: M2 (consolidation) merged so guards assert the new single
  sources of truth.

## Developer Experience / Frontend

### FI-09 — Virtual scrolling for long transcripts [MID]
- **Source**: NF-10 (O(n²) re-render), beyond TSK-401's throttled incremental fix.
- **Benefit**: constant-memory DOM for 1,000+ message sessions; smooth scroll
  under QA-T11-class load.
- **Cost**: medium — windowed renderer; interacts with code-block copy buttons
  and actions bars.
- **Prerequisite**: TSK-401 merged (incremental streaming is the foundation).

### FI-10 — Sanitize markdown rendering (DOMPurify) [SHORT]
- **Source**: renderMarkdown app.js:L2281–2295 assigns model-derived HTML via
  `innerHTML` with no sanitizer — XSS surface if any injected file content or
  model output carries markup (adjacent to NF-18/TSK-404 but client-side).
- **Benefit**: closes the client-side injection half that TSK-404's server-side
  fencing does not cover.
- **Cost**: low — one vendored dependency, wrap the single render site.
- **Prerequisite**: none — independent; can ship any time.

## Documentation

### FI-11 — WS frame protocol specification [SHORT]
- **Source**: frame shapes currently implicit across `_WSAdapter._send` (L233),
  `_json_sender` (L331), done-frame (L1698–1711), and app.js `onmessage` (L154–169).
- **Benefit**: single reference doc (frame types, required fields, ordering,
  error frames incl. TSK-305's warning frame and TSK-403's scan_start);
  prevents silent contract drift between server.py and app.js.
- **Cost**: low — documentation only.
- **Prerequisite**: none (update after TSK-403/305 add frames).

### FI-12 — Deployment & threat-model guide [SHORT]
- **Source**: G2 posture (local dev tool assumption), extends TSK-502.
- **Benefit**: explicit statement of trust boundaries (localhost-only default,
  `force_command_approval` flag, ZIP-restore hardening from TSK-105), so any
  future exposure beyond localhost is a conscious, documented decision.
- **Cost**: low — documentation only.
- **Prerequisite**: TSK-502 merged.

---

## Definition of Done (P7)

- [x] Architecture covered (FI-01, FI-02, FI-03 — from NF-03/NF-05/g1/g5)
- [x] Scalability covered (FI-04, FI-05 — from g9/NF-20/21)
- [x] Maintainability covered (FI-06, FI-07, FI-08 — from NF-14/NF-23/NF-24)
- [x] DX/Frontend covered (FI-09, FI-10 — from NF-10 + renderMarkdown finding)
- [x] Documentation covered (FI-11, FI-12)
- [x] Every item has benefit / cost / prerequisite + horizon tag
- [x] Provider abstraction explicitly excluded per SECTION 0.8
- [x] No status fields here — status lives only in PROGRESS.md
