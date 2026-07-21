# ENGINEERING_WORKSPACE.md — Persistent Recovery & Analysis Record

> **Role:** Persistent working memory for the Engineering Constitution program.
> This file is the ONLY mutable artifact before Phase 4. During Phases 4–5,
> `PRODUCT_VISION.md` is also writable. No other repository file may be modified.
> **Environment hazard:** the sandbox is wiped between turns; an "Auto-update" bot
> *sometimes* captures sandbox work to remote. Always grep-audit remote after re-clone.
> **Recovery note (2026-07-22):** the first write of this file (51,460 chars) was LOST
> (bot did not capture it; remote stayed at d4b8562 with 0-byte constitution files).
> This is a faithful reconstruction from the documented analysis record.

---

## 1. CURRENT MISSION

- **Assignment:** Author `docs/engineering_constitution/PRODUCT_VISION.md` as a permanent
  Engineering Constitution chapter, acting as CPO / Principal Architect.
- **Mandatory phases:** 0 Bootstrap → 1 Repository Analysis → 2 Critique →
  3 Strategic Improvements → 4 Author document → 5 Validation.
- **Truth model:** every claim labeled with one of:
  `VERIFIED_CURRENT_STATE` / `DOCUMENTED_INTENT` / `PROPOSED_DIRECTION` /
  `STRATEGIC_HYPOTHESIS` / `UNVERIFIED` / `CONTRADICTED`.
- **North Star question:** "What would make developers choose this product instead of
  Cursor / Windsurf / VS Code / JetBrains / Antigravity / Claude Code?"
- **Constraints:** no imitation, no rewrites without evidence, preserve verified strengths,
  never modify source/tests/config/README/roadmap/other docs, no git commit/push (user pushes).
- **Final reply format:** concise 7-item execution summary (assignment §20), not the document.

**Phase status:** 0 ✅ · 1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 5 ✅ — **PROGRAM COMPLETE**

---

## 2. REPOSITORY INVENTORY (Phase 1) — VERIFIED_CURRENT_STATE

Product: **"WebDev AI Editor"** — Flask + flask-sock browser AI coding assistant,
Arabic-first UI, vanilla-JS frontend, free multi-account AI providers (no API keys).

| Area | Contents | Evidence |
|---|---|---|
| `server.py` | 2,515 lines; Flask app, WS endpoint, frame protocol, composition via AppContext | read |
| `core/` | 13 modules: AppContext, EventBus (typed BusEvent dataclasses), ApprovalGate, CheckpointManager, ExecutionRegistry, ProjectMemoryStore (JSONL, provenance, staleness, edit/delete), config loader | read |
| `context/` | 19 modules + 7 sub; ContextEngine: 7 sources, tiered budget (must_have/high/opportunistic), byte-exact goldens, tree-sitter symbol index, hashing-BoW semantic seed; `context/ARCHITECTURE.md` matches code | read |
| `chain/` | 21 modules; Runner protocol (Direct/Chain/Agent/Delegate), planner (heuristic/llm/hybrid via config), plugin API with capability-limited PluginContext | read |
| `providers/` | 10 modules; typed contract (`providers/base.py`: Message, ProviderRequest/Response/Capabilities, typed errors RateLimit/Timeout/Transient/ContextTooLarge), pool, account budget, capacity model | read |
| `runners/` | 5 modules | listed |
| `sessions/` | 4 modules; SessionContext per WS connection, session binding | listed |
| `actions/` | 5 modules; allowlist-only agent commands + verify-step contract | listed |
| `static/` | 9 JS files + index.html + style.css — the actually-served frontend | read |
| `tests/` | 79 files / 1,154 test functions; goldens for context/routing/chain; last full gate: **1543 passed, 1 skipped (ALL GREEN)**, mypy clean (67 files), coverage baseline 68.4% | run (turn 3) |
| `agents_rules/` | 201 files; `manifest.yaml` = **21 agents** (analyze 8, plan 2, execute 3, review 5, meta 3), fleet-as-data, hot-reload atomic swap | yaml-parsed |
| `config.yaml` | read end-to-end: default_provider use_ai; command_allowlist; context_budget 128k/8k reserved/0.10 margin; semantic on (2.0s, top_k 3); planner "heuristic"; backend "memory"; dispatch "in-proc"; routing thresholds + tuning guide; provider stubs gemini/openai | read |
| `docs/` | worker_runbook.md (dispatch:worker ops, Redis, in-proc first-class default); `engineering_constitution/` = 13 chapters, all 0 bytes at d4b8562 | read |
| Roadmap/Tasks | `MASTER_DEVELOPMENT_ROADMAP.md` 1,566 lines, phases 1–9 (Phase 9 = UI/UX Professional Track); `DEVELOPMENT_TASKS.md` **81 ✅ / 0 ☐** | grep-verified |
| `README.md` | 472 lines; positioning: "مستوحى من Antigravity", free/no API keys, 21 agents, 4 providers, real file access, backups, sessions | read |

### Exclusions (with reasons)
- `static/vendor/` — third-party bundles, not product code.
- `newskells/` — unrelated skill payloads.
- `src/index.tsx` — Hono/JSX demo page remnant, NOT the served product (hygiene note).
- `public/` — stub files; **`static/` is the real frontend** (see CONTRADICTION-1).
- `agents_rules/memory/PROJECT_VISION.md` + legacy docs — predecessor-project residue (see CONTRADICTION-2).
- `data/` — runtime artifacts.

### Analysis checklist (17/17 complete)
[x] server composition root · [x] WS frame protocol & single-send boundary (`_WSAdapter`) ·
[x] EventBus typed events · [x] ApprovalGate mutation checkpoint · [x] CheckpointManager +
rollback frames + run-history UI · [x] ExecutionRegistry cooperative cancel ·
[x] ContextEngine pipeline & goldens · [x] symbol index (tree-sitter) · [x] semantic seed ·
[x] ProjectMemoryStore + Memory Panel · [x] agent fleet manifest · [x] allowlist/verify-step ·
[x] provider contract/pool/budget/capacity · [x] planner/backend/dispatch config switches +
frame-parity harness + per-project leases · [x] plugin capability surface (grep-gated) ·
[x] quality regime (`scripts/check.sh`: mypy → grep gates → AST lints → color-token lint → pytest) ·
[x] frontend inventory & Phase-9 UX spec (R-901 diff panel).

---

## 3. COMPLETED WORK LOG

1. **Phase 0 Bootstrap** — located `docs/engineering_constitution/` (13 empty chapters @ d4b8562);
   confirmed no duplicate workspace; worktree clean; legacy vision files identified & excluded.
2. **Phase 1 Analysis** — full inventory above; 14 findings; 3 contradictions; exclusions justified.
3. **Phase 2–3** — critique (6 implicit principles, gaps), 6 improvement candidates (1 rejected),
   5-pillar vision architecture, section plan = assignment §16.
4. **(2026-07-22) Workspace reconstruction** after loss of first write; content restored.

---

## 4. FINDINGS (Phase 1)

- **FINDING-1 (VERIFIED_CURRENT_STATE) — Disciplined layered architecture.** AppContext
  composition root; SessionContext per connection; Runner protocol; single ws.send site
  (`_WSAdapter`) enforced by grep gate; typed EventBus. Architecture doc matches code.
- **FINDING-2 (VERIFIED_CURRENT_STATE) — A complete "trust loop" exists.** ApprovalGate is the
  single mutation checkpoint; CheckpointManager + rollback frames + run-history UI; cooperative
  cancel via ExecutionRegistry. Consent → preview → apply → rollback is end-to-end real.
- **FINDING-3 (VERIFIED_CURRENT_STATE) — Deterministic context engine.** 7 sources, tiered
  byte-budget (must_have/high/opportunistic), byte-exact goldens, 1 ProjectScan per message
  (vs legacy O(files×words)), tree-sitter symbol index, hashing-BoW semantic seed with timeout.
- **FINDING-4 (VERIFIED_CURRENT_STATE) — Project memory with provenance & user control.**
  JSONL store, provenance per entry, staleness via index fingerprints, user edit/delete,
  Memory Panel UI (T-114). Memory is inspectable and owned by the user.
- **FINDING-5 (VERIFIED_CURRENT_STATE) — 21-agent fleet-as-data.** manifest.yaml schema,
  hot-reload atomic swap, fallback to base semantics; agents are content, not code.
- **FINDING-6 (VERIFIED_CURRENT_STATE) — Governed execution.** Allowlist-only agent commands,
  timeout/output caps, verify-step contract; plugin API exposes a capability-limited
  PluginContext (no fm/sessions/server/providers) enforced by grep gate.
- **FINDING-7 (VERIFIED_CURRENT_STATE) — Scale-out is config-switched, not forked.** planner
  heuristic/llm/hybrid; backend memory/redis; dispatch in-proc/worker with frame-parity harness
  + per-project leases; in-proc is a first-class default (worker_runbook.md).
- **FINDING-8 (VERIFIED_CURRENT_STATE) — Typed provider contract.** ProviderRequest/Response,
  capabilities, typed error taxonomy; pool + per-account budget + capacity model.
- **FINDING-9 (VERIFIED_CURRENT_STATE) — No product vision exists.** PRODUCT_VISION.md is
  0 bytes; the only "vision" files describe a predecessor project (CONTRADICTED as inputs).
- **FINDING-10 (VERIFIED_CURRENT_STATE) — Strong quality regime.** `scripts/check.sh`:
  mypy (67 files) → grep gates (ws.send boundary, SafeReader, plugin capability, tier
  quarantine) → handler-state AST lint → color-token lint → pytest. 1543 passed / 1 skipped;
  coverage baseline 68.4%; goldens for context/routing/chain.
- **FINDING-11 (VERIFIED_CURRENT_STATE) — Frontend breadth gap.** Vanilla-JS, 9 files;
  functional but far from "premium editor" surface (no diff panel yet — Phase 9 R-901 spec
  exists as DOCUMENTED_INTENT).
- **FINDING-12 (STRATEGIC_HYPOTHESIS) — Commercial risk of free-provider identity.**
  Free multi-account providers are a fragile ToS/durability foundation for a premium product.
- **FINDING-13 (VERIFIED_CURRENT_STATE) — Local-first + Arabic-first are real differentiators.**
  Real file access, local sessions/backups, Arabic-first UI copy throughout.
- **FINDING-14 (VERIFIED_CURRENT_STATE) — Roadmap execution is complete.** 81/81 tasks ✅;
  phases 1–8 done; Phase 9 (UX professional track) specified but not started.

---

## 5. CONTRADICTIONS

- **CONTRADICTION-1:** `public/` stubs vs `static/` — **resolution: `static/` is the served
  product**; `public/` and `src/index.tsx` are scaffold remnants (docs-hygiene note).
- **CONTRADICTION-2:** `agents_rules/memory/PROJECT_VISION.md` describes a predecessor
  project (AI account automation, 14 providers, "no web UI" non-goal) — **stale residue;
  excluded from vision inputs.**
- **CONTRADICTION-3:** Free-provider identity (README) vs premium ambition (assignment) —
  **resolution adopted for the vision: reframe as "model-source independence"**
  (IMPROVEMENT-3): the provider abstraction is the asset; free pools are one interchangeable
  source, not the identity.

---

## 6. IMPROVEMENT CANDIDATES (Phase 3)

- **IMPROVEMENT-1 (adopt):** Elevate the trust loop (approval/checkpoint/rollback/run history)
  to the primary product identity — "the AI editor you can audit and undo."
- **IMPROVEMENT-2 (adopt):** Position deterministic context + provenance-tracked memory as
  "Context & Memory Intelligence" pillar; goldens = testable honesty.
- **IMPROVEMENT-3 (adopt):** Reframe free providers → **model-source independence** (typed
  contract + pool + budget/capacity as the durable asset; paid API keys = config stubs exist).
- **IMPROVEMENT-4 (adopt):** Governed autonomy as differentiation vs "auto-run" competitors:
  allowlist + verify-step + capability-limited plugins.
- **IMPROVEMENT-5 (adopt):** Premium experience program = execute Phase 9 UX track (diff panel
  R-901 first) + Arabic-first as an underserved-market wedge.
- **IMPROVEMENT-6 (REJECTED):** Framework rewrite (e.g., React/Hono SSR migration) — no
  evidence of need; violates "no rewrites without evidence"; vanilla stack is tested & gated.

---

## 7. COMPETITIVE RESEARCH — ACCESS-LIMITED (access date 2026-07-22)

No live web research was performed this program (environment/time constraints). Entries below
are labeled **UNVERIFIED (ACCESS-LIMITED)** general-knowledge sketches; the vision confines
volatile competitor details and anchors on durable structural contrasts.

| Competitor | Sketch (UNVERIFIED) | Durable contrast we can claim (VERIFIED on our side) |
|---|---|---|
| Cursor | AI-native VS Code fork, paid API-centric | Our consent-first mutation gate + byte-exact context goldens |
| Windsurf | Agentic flows ("Cascade") | Our governed autonomy: allowlist + verify-step, no silent writes |
| VS Code + Copilot | Ubiquitous, extension-based AI | Our AI-native single trust loop vs bolted-on assist |
| JetBrains AI | IDE-deep, paid | Our local-first, zero-API-key onboarding |
| Antigravity | Inspiration per README | Our provenance-tracked project memory + rollback |
| Claude Code | Terminal agent, powerful, paid API | Our browser UI, Arabic-first, approval/rollback UX |

---

## 8. PHASE 2 CRITIQUE — IMPLICIT PRINCIPLES & GAPS

**Six implicit principles extracted from verified code (VERIFIED_CURRENT_STATE as behavior):**
1. **Consent-first agency** — no mutation without ApprovalGate.
2. **Honesty over magic** — provenance, staleness marking, typed errors, no fake certainty.
3. **Determinism as identity** — goldens, byte budgets, frame-parity harness.
4. **User ownership** — local files, editable/deletable memory, backups, rollback.
5. **Single-process-first** — in-proc default; scale-out is opt-in config, not architecture debt.
6. **Arabic-first craftsmanship** — first-class Arabic UX, not translation afterthought.

**Gaps:** free-vs-premium tension unresolved (→ CONTRADICTION-3); frontend breadth below
premium bar (FINDING-11); no commercial layer at all; no written mission/vision (FINDING-9);
no measurement infrastructure for product outcomes.

---

## 9. PHASE 3 — VISION ARCHITECTURE (5 pillars)

1. **Trust Loop** — approval, checkpoints, rollback, run history, cancel. (FINDING-2)
2. **Context & Memory Intelligence** — deterministic context engine + provenance memory. (F-3, F-4)
3. **Governed Autonomy** — 21-agent fleet-as-data under allowlist/verify-step/capability limits. (F-5, F-6)
4. **Predictable Platform** — typed contracts, config-switched scale, quality gates, goldens. (F-7, F-8, F-10)
5. **Premium Experience** — Phase-9 UX track, Arabic-first, local-first ownership. (F-11, F-13)

Document structure = assignment §16 verbatim (16 sections). Decision filters and non-goals
derive from the 6 implicit principles; commercial principles resolve CONTRADICTION-3.

---

## 10. LIMITATIONS

- No live competitive web research (ACCESS-LIMITED labels used).
- No runtime provider benchmarking; no market/user data.
- Sandbox volatility: work can be lost between turns (this file was lost once and reconstructed).
- Coverage 68.4% is a baseline, not a product metric.

---

## 11. FUTURE CONSTITUTION NOTES (for later chapters, NOT this one)

- Docs hygiene: remove `src/index.tsx`, `public/` remnants; retire predecessor vision files.
- Security chapter: threat model for command allowlist & plugin surface.
- Measurement infrastructure: product outcome metrics beyond CI green.
- UX design system chapter feeding Phase 9.

---

## 12. PHASE 5 — VALIDATION RECORD (2026-07-22)

Validation performed against assignment §15 checklist, with live repo spot-checks @ d4b8562:

- **Repository accuracy:** 21 agents (yaml-parsed ✓); 79 test files ✓; server.py 2,515 lines ✓;
  coverage baseline 68.4 ✓; gemini/openai provider stubs in config.yaml lines 184–192 ✓;
  ApprovalGate/CheckpointManager/ProjectMemoryStore present in `core/` ✓; roadmap tasks:
  84 ✅ markers, **zero** unchecked task rows (the single ☐ is the status-legend line) ✓.
  Every `VERIFIED_CURRENT_STATE` claim in PRODUCT_VISION.md traces to these checks or to
  the Phase 1 findings (FINDING-1..14).
- **Strategic quality:** North Star answers the "why choose us" question; 6 ordered decision
  filters; 5 pillars each cite verified foundation + direction; prioritization doctrine and
  measures included; no imitation strategy; IMPROVEMENT-6 rewrite formally rejected (Non-Goal 4).
- **Commercial quality:** CONTRADICTION-3 resolved via model-source independence (§12 of
  vision); "never sell what we don't control" principle; value ladder labeled
  STRATEGIC_HYPOTHESIS pending market validation.
- **Competitive quality:** §10 explicitly marked ACCESS-LIMITED (no live research);
  volatile claims avoided; refresh is a standing amendment trigger (§16).
- **Constitution quality:** binding status, precedence vs roadmap, amendment triggers +
  procedure, standing review of truth-state labels, revision log v1.0.
- **Repository safety:** `git status` confirms ONLY ENGINEERING_WORKSPACE.md and
  PRODUCT_VISION.md modified. No source/tests/config/README/roadmap touched. No git
  commit/push performed (user pushes manually).
- **Document sizes:** PRODUCT_VISION.md 22,418 chars (16 sections); workspace 15,398 chars.

## 13. RESUME CHECKPOINT

```
NEXT_DOCUMENT=NONE
NEXT_PHASE=COMPLETE
NEXT_SECTION=NONE
NEXT_SUBSYSTEM=NONE
NEXT_FILE=NONE
NEXT_ACTION=NONE — program complete; awaiting user push and any amendment triggers
LAST_COMPLETED_ACTION=Validated PRODUCT_VISION.md and persistent workspace (Phase 5 record above)
BLOCKER=NONE
WORKTREE_STATUS=modified: docs/engineering_constitution/ENGINEERING_WORKSPACE.md + docs/engineering_constitution/PRODUCT_VISION.md (only these two files)
UPDATED_AT=2026-07-22T06:40:00Z
```
