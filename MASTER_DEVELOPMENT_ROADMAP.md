# MASTER DEVELOPMENT ROADMAP — WebDev AI Editor

> **Scope:** Architectural refactoring of the Flask+WebSocket AI coding assistant (context, memory, chains, agents, sessions, state, scalability).
> **Out of scope:** AI providers/models internals, auth, billing, streaming transport, prompt wording.
> **Source of truth:** Every item below references verified evidence (file + line ranges) from the architectural review.
> **Numbering:** `R-<phase><nn>`. Complexity scale 1–5. Time estimates assume one senior engineer.
> **Scope additions (2026-07 review merge):** Edit Safety (checkpoint/rollback) · Code-structural Context (symbol awareness) · Semantic Recall (seeded early) · Agent Feedback Loops · **UI/UX Professional Track (Phase 9)**.
> **Provenance:** Unified plan — consolidated from four draft plans (2026-07). Base: the most detailed draft (field-table format, full evidence line-refs); enriched with the measurable acceptance gates unique to the later drafts (30-decision routing corpus, 21-agent parity, turn-5 fact retention). Truncated/duplicate drafts discarded.

---

## Global Architecture Target

```
+------------------------------------------------------------------+
|                        AppContext (composition root)             |
|  +------------+ +--------------+ +----------------+              |
|  | Providers  | | ContextEngine| | ExecutionReg.  |              |
|  | Pool/Budget| | +ContextBudget| | (runs/agents) |              |
|  +-----+------+ +------+-------+ +------+---------+              |
|        |               |                |                        |
|  +-----v---------------v----------------v--------+               |
|  |              Runner Protocol                   |               |
|  |  DirectRunner | ChainRunner | AgentRunner |    |               |
|  |  DelegateRunner                                |               |
|  +-----+------------------------------------------+              |
|        | events                                                  |
|  +-----v------+  +--------------+  +--------------+              |
|  |  EventBus  |->| ApprovalGate |->| ActionApplier|              |
|  +-----+------+  +--------------+  +--------------+              |
|        |                                                         |
|  +-----v---------------+   +---------------------+               |
|  | SessionContext      |   | ConversationMemory  |               |
|  | (per WS connection) |   | + JSONL SessionStore|               |
|  +---------------------+   +---------------------+               |
+------------------------------------------------------------------+
```

Key shifts from current design:
1. **13 module-level globals in `server.py` → one `AppContext`** injected everywhere.
2. **Inline 200-line context block in `server.py` → `ContextEngine`** shared by direct mode, agent loop, and chain strategies.
3. **Silent auto-apply in `ChainBridge` finally-block → `ApprovalGate`** as the single mutation checkpoint.
4. **Dead `_active_chain_run` guard → `ExecutionRegistry`** with real lifecycle tracking.
5. **Full-file JSON rewrite per message → append-only JSONL** session store.

---

# PHASE 1 — Critical Correctness & Safety (Week 1–2)

Goal: eliminate defects that corrupt state, mutate the workspace without consent, or break the provider contract. Nothing in later phases is safe to build on top of the current foundations.

---

### R-101 — Remove/Repair the Dead Concurrency Guard

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 2/5 |
| **Time Estimate** | 4h |
| **Dependencies** | None |
| **Breaking Changes** | None |
| **Affected Modules** | `server.py` (L82, L403, L470) |

**Problem Statement:** `_active_chain_run = None` (server.py L82) is assigned exactly once — at initialization — and never updated when a chain actually starts. The guards at L403 and L470 that check it are permanently dead: two chains can run concurrently against the same `FileManager`, interleaving writes.

**Root Cause:** The guard was scaffolded but the assignment inside the chain-start path was never written; no test exists to catch it (`tests/` does not exist).

**Current Design:** Global sentinel checked but never set. Concurrency protection is fictional.

**Target Design:** Interim fix (before R-105): a `threading.Lock`-protected `ActiveRunHolder` with `acquire(run_id) / release(run_id)` called from `ChainBridge.run()` entry/finally. WS handler rejects a second `start_chain` with a structured `run_busy` error frame.

**Justification:** Cheapest possible fix for a data-corruption-class bug; unblocks safe testing of everything else.

**Benefits:** Deterministic single-run invariant; honest error to the client instead of silent interleaving.

**Risks:** A crash path that skips `finally` could leave the holder stuck — mitigate with a TTL + `force_release` admin command.

**Required Tests:** Unit: acquire/release/second-acquire-rejected/TTL expiry. Integration: two WS `start_chain` frames → second gets `run_busy`.

**Acceptance Criteria:** Guard is set on run start, cleared on all exit paths (success/error/cancel); concurrent start is provably rejected; grep shows ≥3 assignment sites.

**Future Expansion:** Superseded by R-105 `ExecutionRegistry` (multi-run with per-project locks).

---

### R-102 — Introduce AppContext & Kill Stale-Reference Project Switching

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 4/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-101 |
| **Breaking Changes** | Internal constructor signatures change (all wiring in `main()`) |
| **Affected Modules** | `server.py` (L71–96, L435–450, L463–504, L1475–1614), `chain/bridge.py`, `chain/agent_tools.py`, `chain/agent_loop.py`, `chain/delegate.py`, `chain/router.py` |

**Problem Statement:** `api_switch_project` (server.py L463–504) rebuilds only `fm` and `cmd_runner` globals. `AgentTools` (holds `self.fm`, `self.cmd`, `self.project_root`), `ChainBridge`, `ContextBuilder`, and `DelegateBridge` keep references to the **old** project's managers. After a switch, agents read/write the previous project. Similarly `api_switch_model` (L435–450) pokes private attributes (`request_router._active_provider_name`, `delegate_bridge._provider`, `chain_bridge._provider`) on three objects — any new consumer silently misses the update.

**Root Cause:** Object graph is wired once in `main()` from 13 module globals; there is no ownership model, so "switch" mutates some leaves and misses others.

**Current Design:** Global mutable singletons + partial rebuild + private-attribute pokes.

**Target Design:** `AppContext` dataclass owning: `provider_pool`, `active_provider` (property), `project` (a `ProjectHandle` bundling `fm`, `cmd_runner`, `root`), `session_manager`, `budget`, `registry`. All components receive `ctx: AppContext` and resolve `ctx.project.fm` **at call time**, never caching. `switch_project()` and `switch_model()` become single atomic assignments on the context.

**Justification:** This is the root defect enabling half the smell list (stale refs, private pokes, untestability). Every later phase depends on injectable composition.

**Benefits:** Project/model switch becomes one-line correct; components become unit-testable with a fake context; deletes ~150 lines of wiring.

**Risks:** Wide mechanical change; regressions in rarely-hit WS handlers. Mitigate with a wiring smoke test that exercises every WS message type against a temp project.

**Required Tests:** Unit: `ctx.switch_project()` → all consumers observe new `fm` (assert via id()). Unit: `switch_model` updates router/delegate/bridge without touching privates. Integration: agent tool `read_file` after switch reads the **new** project.

**Acceptance Criteria:** Zero module-level mutable component globals in `server.py` (constants allowed); grep for `_active_provider_name` outside its owner returns nothing; switch-then-act test passes.

**Future Expansion:** Enables R-701 per-connection `SessionContext` (context becomes per-session scoped view over shared services).

---

### R-103 — Fix the DelegateBridge ↔ Provider Contract Violation

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 2/5 |
| **Time Estimate** | 4h |
| **Dependencies** | None (parallel with R-101) |
| **Breaking Changes** | None externally |
| **Affected Modules** | `chain/delegate.py` (L260, L289, L327), `providers/base.py` |

**Problem Statement:** `delegate.py` calls `self._provider.send(messages, system_prompt=system)` passing `list[Message]`, but `BaseProvider.send` (providers/base.py L254) is typed `send(prompt: str, history=None, system_prompt=None)`. The Brief→Implement→Review→Land flow works only if a concrete provider happens to tolerate a list — a latent runtime failure on any strict provider in the pool's fallback chain.

**Root Cause:** Delegate was written against an imagined chat-style API; no type checking or tests enforce the base contract.

**Current Design:** Duck-typed accident.

**Target Design:** Convert at the call sites: last message → `prompt`, preceding messages → `history`. Add `mypy`-checkable type hints and a `ProviderContractTest` (shared test class run against a `FakeProvider` and each concrete provider adapter).

**Justification:** Delegate is one of only four execution modes; it currently rests on undefined behavior across the fallback chain.

**Benefits:** Delegate works with **every** provider in the pool, including fallbacks; contract becomes machine-enforced.

**Risks:** Minimal — behavior-preserving for the currently-tolerant provider.

**Required Tests:** Unit: delegate stage calls with a strict `FakeProvider` asserting `isinstance(prompt, str)`. Contract test suite in CI.

**Acceptance Criteria:** All three call sites pass `str`; `mypy chain/delegate.py providers/base.py` clean; delegate E2E (fake provider) green.

**Future Expansion:** Contract test harness reused for R-501 Runner protocol.

---

### R-104 — ApprovalGate: End Silent Auto-Apply

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-102 (injection point) |
| **Breaking Changes** | Behavior: chain results no longer auto-write files (config-gated) |
| **Affected Modules** | `chain/bridge.py` (L264–276 finally-block), `chain/action_applier.py`, `chain/agent_loop.py` (approval flow), `server.py`, `config.yaml` |

**Problem Statement:** `ChainBridge._run_chain`'s `finally` block calls `action_applier.apply_step(step_id="mr_execute", ai_response=result_text, dry_run=False)` — chain output mutates the workspace with **no approval**, even on partially-failed runs (it is in `finally`), while `config.yaml` says `auto_execute: false`. Meanwhile `AgentLoop` has a *separate* approval mechanism (threading.Event + payload hash, 60s timeout). Two inconsistent consent models; one of them is "none".

**Root Cause:** ActionApplier was bolted onto the chain path after the agent approval flow existed; the config flag was never plumbed into the chain path.

**Current Design:** Chain path: unconditional apply in `finally`. Agent path: hash-verified approval. Direct mode: no apply.

**Target Design:** Single `ApprovalGate` service: `request(actions: list[ProposedAction]) -> Decision`. Policies: `auto` (config/user opt-in, whitelist of action kinds), `interactive` (WS approval frame, payload-hash verified — reuse agent loop mechanics), `deny`. `ChainBridge` and `AgentLoop` both route through it. Apply moves **out of `finally`** into the success path only.

**Justification:** Unconsented file mutation on failed runs is the single worst trust violation in the system.

**Benefits:** One consent model; failed runs never write; config flag becomes truthful; UI gets a uniform approval frame.

**Risks:** Users relying on implicit auto-apply see a new prompt — provide `approval.mode: auto` migration setting and changelog note.

**Required Tests:** Unit: gate policies (auto/interactive/deny/timeout). Integration: failed chain run → zero file writes; successful run with `interactive` → write only after approval frame; hash-mismatch → rejected.

**Acceptance Criteria:** No `apply_step` call reachable from a failure path; both chain and agent flows use `ApprovalGate`; `auto_execute:false` provably blocks writes.

**Future Expansion:** Per-action-kind policies (e.g., auto-approve reads/formatting, gate deletes) in Phase 8.

---

### R-105 — ExecutionRegistry: Real Run Lifecycle Tracking

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-101, R-102 |
| **Breaking Changes** | Replaces R-101 interim holder |
| **Affected Modules** | new `core/registry.py`, `server.py`, `chain/bridge.py`, `chain/agent_loop.py`, `chain/delegate.py` |

**Problem Statement:** There is no authoritative record of what is executing: chain runs, agent loops, and delegate flows each manage their own ad-hoc state; cancellation (`CancellationToken`) reaches chains but delegate has **no cancellation support at all**; the WS layer cannot enumerate or cancel work it started.

**Root Cause:** Each execution mode grew independently; no shared lifecycle abstraction.

**Current Design:** Per-mode ad-hoc state + dead global sentinel.

**Target Design:** `ExecutionRegistry`: `register(kind, project_id) -> RunTicket(run_id, cancel_token)`, `heartbeat()`, `finish(status)`, `list_active()`, `cancel(run_id)`. Per-project mutual exclusion (configurable). All three execution modes acquire a ticket; delegate threads its ticket's cancel token through Brief/Implement/Review/Land stage boundaries.

**Justification:** Prerequisite for parallelism (R-603), multi-session (R-701), and honest UI state.

**Benefits:** `list_runs`/`cancel_run` WS commands become trivial; delegate becomes cancellable; per-project locking replaces the global bottleneck.

**Risks:** Cancellation semantics in delegate mid-stage — define stage boundaries as cancellation checkpoints only (no mid-request abort in Phase 1).

**Required Tests:** Unit: register/finish/cancel/exclusion/TTL. Integration: cancel delegate between stages → run ends `cancelled`, no Land executed.

**Acceptance Criteria:** All execution entry points registry-ticketed; delegate honors cancel at ≥3 checkpoints; `list_active()` reflects reality in an E2E test.

**Future Expansion:** Backing store swap (in-mem → Redis) for R-804 worker pool.

---

### R-106 — Checkpoint & Rollback: Consent *After* the Write, Too

| Field | Value |
|---|---|
| **Priority** | Critical |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-102, R-104 |
| **Breaking Changes** | None (additive) |
| **Affected Modules** | `core/checkpoint.py` (new), `chain/action_applier.py`, `server.py`, WS protocol |

**Problem Statement:** Even with `ApprovalGate` gating consent *before* a write, there is no way to undo a change once it lands — not a partial-run write, not a fully-approved multi-file edit that turns out wrong five minutes later. Competing AI editors treat "undo the agent's last edit" as table stakes; git is not a substitute (target repos aren't guaranteed clean working trees, and users shouldn't need git to recover from an agent mistake).

**Root Cause:** "Safety" was scoped as pre-write consent only; post-write reversibility was never a separate requirement.

**Current Design:** No checkpoint concept; a bad multi-file edit is reverted manually, file by file.

**Target Design:** `CheckpointManager` — before any gate-approved batch applies, snapshot pre-write content of every touched path (content-addressed, deduplicated) into a `CheckpointLog` keyed by `run_id`; record the full before/after diff post-apply. WS gains `rollback_run(run_id)` (refuses with a conflict report if a file was independently modified since — never silently overwrites) and `rollback_file(run_id, path)` for partial undo. Checkpoints follow R-305's `RetentionPolicy`.

**Justification:** The single highest product-trust item in the roadmap — it lets a user say "let the agent touch five files" without fear.

**Benefits:** Every agentic edit becomes a reversible experiment; makes `ApprovalGate`'s `auto` mode genuinely safe because mistakes are recoverable.

**Risks:** Snapshot storage growth — content-addressed dedup + retention bounds it; conflicting external edits — hash-detected and reported.

**Required Tests:** Rollback restores exact pre-run bytes across a 5-file batch; partial `rollback_file` leaves siblings untouched; refusal on independent external modification; retention sweep bounds storage across 50 fixture runs.

**Acceptance Criteria:** Every applied batch has a checkpoint; `rollback_run`/`rollback_file` integration tests green; rollback affordance documented in the WS frame.

**Future Expansion:** Named/pinned checkpoints ("save point before refactor"); checkpoint diff viewer in the Phase 9 UI track (R-902).

---

## Phase 1 — Definition of Done
- [ ] Concurrent chain start rejected with structured error (R-101 → R-105).
- [ ] Project switch leaves **zero** stale references (id()-asserted test).
- [ ] Model switch touches no private attributes.
- [ ] Delegate passes `str` prompts; provider contract test in CI.
- [ ] No file write occurs without ApprovalGate consent; failed runs write nothing.
- [ ] `ExecutionRegistry` tracks and cancels all three execution modes.
- [ ] **Every applied batch has a checkpoint; rollback (full and per-file) tested and reachable from the WS API.**
- [ ] New `tests/` directory exists with all Phase-1 tests green in CI.

---

# PHASE 2 — Context Engine (Week 3–4)

Goal: extract the three duplicated context-gathering implementations (server inline block, `ContextBuilder`, `KnowledgeAccumulator` prefetch) into one budgeted, deduplicated engine.

---

### R-201 — Extract Inline Context Collection into ContextEngine

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 4/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-102 |
| **Breaking Changes** | None externally (behavior-preserving extraction first) |
| **Affected Modules** | `server.py` (L606–758), new `context/engine.py`, `chain/context_builder.py`, `chain/agent_loop.py` (`_auto_prefetch`) |

**Problem Statement:** `server.py` L606–758 contains ~200 lines of inline context collection: regex mention-extraction, per-word `fm.root.rglob(f"*{stem}*")` scans (O(files × words) filesystem walks per message), and a constant that lies about itself (`MAX_MENTIONED = 100  # حد أقصى 10 ملفات`). `ContextBuilder` and `AgentLoop._auto_prefetch` reimplement overlapping logic with different keyword tables and truncation rules. Three sources of truth for "what does the model see".

**Root Cause:** Direct mode grew inline in the WS handler; chain/agent paths were written later without extracting the shared concern.

**Current Design:** Copy-paste triplication with divergent limits.

**Target Design:** `ContextEngine.gather(request: ContextRequest) -> ContextBundle`. Sources as pluggable providers: `MentionSource`, `KeywordSource`, `ProjectStructureSource`, `HistorySource`. Server handler shrinks to `bundle = ctx.context_engine.gather(...)`. `ContextBuilder` becomes a thin adapter over the engine; `_auto_prefetch` delegates to it.

**Justification:** Context quality is the #1 driver of output quality; today it is unowned, untested, and O(n·m) on every message.

**Benefits:** One tested implementation; single tuning surface; server handler drops ~200 lines; rglob storms replaced by indexed lookup (full fix in R-702, interim: single cached file-list scan per message).

**Risks:** Behavior drift in what gets included — snapshot-test current inclusion behavior on a fixture project before extraction, assert parity after.

**Required Tests:** Golden tests: fixture project + message → expected `ContextBundle` item set. Perf test: one message triggers ≤1 filesystem walk. Parity test vs. legacy inline output.

**Acceptance Criteria:** `server.py` contains no context-gathering logic; all three call paths use `ContextEngine`; misleading constant removed; parity snapshots green.

**Future Expansion:** Embedding/semantic source slots into the same provider interface (Phase 8).

---

### R-202 — ContextBundle: Deduplicated, Provenance-Tagged Context

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-201 |
| **Breaking Changes** | Internal prompt assembly changes |
| **Affected Modules** | `context/bundle.py` (new), `chain/knowledge.py`, `chain/models.py` (`ChainStep.build_prompt`), `chain/strategies.py` |

**Problem Statement:** The same file content is injected multiple times per request: `KnowledgeAccumulator._files_read` re-injects full contents every agent iteration; map_reduce's `mr_execute` step re-embeds **all** file contents already present in per-file map steps; `ChainStep.build_prompt` concatenates full dependency results verbatim. Token waste is multiplicative and unobservable.

**Root Cause:** No shared container with identity — every layer stores raw strings.

**Current Design:** Raw string concatenation at every layer.

**Target Design:** `ContextBundle`: ordered `ContextItem`s keyed by `(source_kind, path, content_hash)`; `add()` dedupes by hash; items carry provenance + token estimate; `render(budget)` emits once. Knowledge accumulator stores item **references**, not copies. Strategy builders pass bundle refs between steps; `build_prompt` renders references with an "already in context above" elision.

**Justification:** Directly reduces cost and context-window pressure; makes R-203 budgeting possible.

**Benefits:** Measured token reduction (target ≥40% on map_reduce fixtures); provenance enables debugging "why did the model see X".

**Risks:** Over-aggressive elision can starve steps of needed content — dependency results are never elided, only duplicate file bodies.

**Required Tests:** Unit: hash dedup, ordering stability, provenance. Golden: map_reduce fixture prompt contains each file body exactly once. Regression: agent 3-iteration run token count strictly decreasing vs. baseline.

**Acceptance Criteria:** No code path stores a second full copy of file content; map_reduce duplication eliminated; token metrics logged per run.

**Future Expansion:** Cross-run bundle caching keyed by content hash (Phase 8 project memory).

---

### R-203 — ContextBudget: Token-Accounted Assembly

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-202 |
| **Breaking Changes** | Prompts may shrink for oversized contexts (intended) |
| **Affected Modules** | `context/budget.py` (new), `context/engine.py`, `chain/orchestrator.py` (`_split_content`), `chain/context_builder.py` |

**Problem Statement:** Every truncation decision uses ad-hoc character limits (`chars/4` token guess in orchestrator, per-item char caps in ContextBuilder, char-based truncation in knowledge). Nothing accounts for the **sum**; an assembled prompt can exceed the model window and fail at the provider, or silently truncate the most relevant item.

**Root Cause:** No central accounting; each component guesses locally.

**Current Design:** Distributed char-based guessing.

**Target Design:** `ContextBudget(model_window, reserved_output)`: priority-ordered admission (`must_have` → `high` → `normal` → `opportunistic`); per-item token estimate via a single pluggable tokenizer-estimator; deterministic drop order (lowest priority, largest item first) with an explicit `dropped[]` report attached to the bundle.

**Justification:** Converts silent quality degradation into observable, prioritized decisions.

**Benefits:** No provider-side window overflows; relevance-ranked retention; `dropped[]` surfaces to logs/UI.

**Risks:** Estimator inaccuracy — keep 10% safety margin, log estimate-vs-actual when providers report usage.

**Required Tests:** Unit: admission ordering, drop determinism, margin math. Integration: oversized fixture → bundle fits window, `dropped[]` non-empty, must_have items always retained.

**Acceptance Criteria:** All prompt assembly flows through `ContextBudget`; zero raw char-limit truncations remain (grep for magic char constants); overflow test green.

**Future Expansion:** Feeds R-304 history windowing and R-602 chain context policy with the same admission engine.

---

### R-204 — SafeReader: Enforce Secret-File Policy at the Read Boundary

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 2/5 |
| **Time Estimate** | 1d |
| **Dependencies** | R-201 |
| **Breaking Changes** | `.env` and secret files stop appearing in model context (intended) |
| **Affected Modules** | `chain/path_policy.py`, `chain/bridge.py` (`scan_folder_for_chain` — `.env` in `_TEXT_EXTENSIONS` L333–344), `context/engine.py`, `chain/agent_tools.py` |

**Problem Statement:** `path_policy.is_secret_file` exists, but `scan_folder_for_chain` includes `.env` in its `_TEXT_EXTENSIONS` and reads it into chain context; other read paths (agent tools, context builder) apply the policy inconsistently. Secrets can be shipped to third-party model APIs.

**Root Cause:** Policy is a library function callers must remember, not a boundary.

**Current Design:** Opt-in policy, forgotten in at least one scanner.

**Target Design:** `SafeReader` — the **only** sanctioned file-read gateway for model-bound content: resolves via `resolve_workspace_path`, rejects `is_secret_file` matches (returns redaction stub `«redacted: secret file»`), enforces size caps. All context sources, agent `read_file` tool, and folder scanners route through it. Remove `.env` from `_TEXT_EXTENSIONS`.

**Justification:** Secret exfiltration to model providers is a security defect, not a smell.

**Benefits:** Single choke point; auditable; denylist extensible via config.

**Risks:** Legit workflows reading `.env.example` — policy matches exact secret patterns, not `*.example`.

**Required Tests:** Unit: denylist matrix (`.env`, `.env.local`, `id_rsa`, `*.pem` vs `.env.example`). Integration: chain over fixture with `.env` → prompt contains redaction stub, never the value; agent `read_file .env` → policy error.

**Acceptance Criteria:** grep confirms no `open()`/`read_text()` on model-bound paths outside `SafeReader`; `.env` unreachable from any prompt in E2E.

**Future Expansion:** Content-level secret scanning (entropy/API-key regex) as a second-pass redactor.

---

### R-205 — SymbolIndex: Symbol-Aware Context (Structural Understanding)

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 4/5 |
| **Time Estimate** | 4d |
| **Dependencies** | R-201 (benefits from R-702's index but can start on a smaller in-memory structure) |
| **Breaking Changes** | None (additive source) |
| **Affected Modules** | `context/symbol_index.py` (new), `ContextEngine` |

**Problem Statement:** Every context source matches on **filenames and keywords only**. There is no notion of "this function calls that function" or "this class is defined here and used in these twelve places" — the system cannot answer "who else uses this" without a keyword grep that returns noise. This is the single biggest quality gap versus structural-aware competitors.

**Root Cause:** The codebase was never asked to parse code as code — only as text.

**Current Design:** Regex/keyword matching over raw file text.

**Target Design:** `SymbolIndex` built with `tree-sitter` grammars for the project's dominant languages (start with the 3–4 most common in target repos; add more incrementally): extracts function/class/symbol definitions, references, and import graphs per file; refreshed by the same write-hooks as `ProjectIndex` (R-702). `SymbolSource` (a `ContextSource`) resolves "definition of X", "callers of X", and "file imports" as `high`-tier context items — a strict quality upgrade over keyword matching for the same budget cost.

**Justification:** This is what separates "reads nearby files" from "understands the codebase" — directly determines whether generated edits respect existing call patterns instead of guessing.

**Benefits:** Mentions of a function name resolve to its actual definition and call sites, not every file that happens to contain the string; agent edits are less likely to break unseen call sites.

**Risks:** Parser coverage gaps for less-common languages — `SymbolSource` degrades gracefully to `KeywordSource` behavior for unparsed files, never blocks the request.

**Required Tests:** Golden — "who calls function X" on a fixture project returns the exact call-site set; graceful-degradation test on an unsupported file extension; perf — index build stays under a defined ceiling on a 2k-file fixture.

**Acceptance Criteria:** `SymbolSource` live in `ContextEngine`; degrade-gracefully test green; measurable precision improvement over keyword-only on a "find usages" golden set.

**Future Expansion:** Cross-file refactor-impact analysis; feeds a future "safe rename" agent tool.

---

### R-206 — SemanticSource: Semantic Retrieval, Seeded Early

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-201, R-203 |
| **Breaking Changes** | None (additive, behind config flag) |
| **Affected Modules** | `context/semantic_source.py` (new), `ContextEngine` |

**Problem Statement:** Without any relevance-based recall, context quality is capped by exact-match mentions and keywords; a message like "how did we handle auth last time" has no path to the relevant code or decision at all if the words don't literally match. Parking this capability until Phase 8 means the product ships an entire development cycle without a core quality lever competitors already have.

**Root Cause:** No embedding infrastructure exists; it was scoped as a "nice to have, later" item.

**Current Design:** None.

**Target Design:** A deliberately **small, seeded** version — not the full layered memory system (that remains R-802 in Phase 8, which builds on this foundation): embed file chunks and recent conversation turns via a single pluggable embedding call; `SemanticSource` retrieves top-k relevant items and injects them at `opportunistic` tier only (never displaces `must_have`/`high` content, per R-203's tier rules); retrieval is skipped (not blocking) if the embedding call is slow or fails.

**Justification:** Relevance-based recall is a top-3 quality lever; shipping a minimal version early is far better than shipping none until Phase 8, and the architecture (ContextSource + tiered budget) already supports it with almost no new machinery.

**Benefits:** "How did we do X" style questions get a real answer path from turn 1 of the project, not after 14+ weeks.

**Risks:** Embedding cost/latency — async with a hard timeout and skip-on-timeout; retrieval noise — strict `opportunistic` tier keeps it cheap to be wrong.

**Required Tests:** Retrieval precision on a small fixture (query about an early decision resolves the right chunk); timeout-skip does not block the response; budget-tier compliance (never displaces `must_have`).

**Acceptance Criteria:** `SemanticSource` live behind a config flag (default on, cheap to disable); skip-on-timeout test green.

**Future Expansion:** R-802 (Phase 8) upgrades this seed into the full working/episodic/semantic layered system with provenance and cross-session persistence (R-805).

---

## Phase 2 — Definition of Done
- [ ] One `ContextEngine`; server inline block deleted; three call paths converge.
- [ ] `ContextBundle` hash-dedup live; map_reduce token reduction ≥40% on fixtures.
- [ ] `ContextBudget` governs every assembled prompt; overflow impossible in tests.
- [ ] `SafeReader` is the sole model-bound read path; `.env` provably redacted.
- [ ] **Symbol-aware "find definition / find usages" green on golden fixtures; graceful degradation to keyword matching on unparsed files.**
- [ ] **Minimal `SemanticSource` live at `opportunistic` tier behind a config flag; skip-on-timeout and budget-compliance tests green.**
- [ ] Context golden-test suite (fixture project) in CI.

---

# PHASE 3 — Memory & Session Architecture (Week 5–6)

Goal: replace O(n²) session persistence, give conversation memory an owner, and stop unbounded history growth.

---

### R-301 — Append-Only JSONL Session Store

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | None (parallel with Phase 2) |
| **Breaking Changes** | Session file format (migration tool provided) |
| **Affected Modules** | `actions/session_manager.py` (`append_message`, `_save_full`, `_cleanup_old`) |

**Problem Statement:** `append_message` does load-entire-JSON → append → `_save_full` (full serialize + fsync + atomic replace) on **every message**. Cost per message grows linearly with history → O(n²) per session lifetime; long sessions cause visible write stalls and fsync churn.

**Root Cause:** Single-document JSON chosen for simplicity; append semantics never revisited.

**Current Design:** Full-file rewrite per message; 30-day TTL cleanup; 43 session JSONs committed to git.

**Target Design:** `session_<id>.jsonl` — one JSON object per line, O(1) append with per-line fsync policy (configurable batching); sidecar `session_<id>.meta.json` for mutable header (title, project binding, counters) rewritten only on meta change. `migrate_sessions.py` converts legacy files. Sessions dir added to `.gitignore` (with `git rm --cached`).

**Justification:** The dominant hot-path write; blocks nothing but degrades everything.

**Benefits:** Constant-time appends; crash-safe (partial last line detectable/skippable); tail-read for recent-window loads (R-304).

**Risks:** Two-file consistency (data vs meta) — meta is derivable; rebuildable from JSONL on mismatch.

**Required Tests:** Unit: append/replay/corrupt-tail recovery/meta rebuild. Migration: legacy fixture → identical message sequence. Perf: 1k appends p95 < 5ms.

**Acceptance Criteria:** `append_message` is O(1) (perf test); migration round-trips fixtures; sessions untracked in git.

**Future Expansion:** Same log format backs R-802 layered memory and event sourcing.

---

### R-302 — ConversationMemory as an Owned Component

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-301 |
| **Breaking Changes** | Internal — history access API changes |
| **Affected Modules** | new `memory/conversation.py`, `server.py`, `chain/agent_loop.py`, `prompts/templates.py` |

**Problem Statement:** "What history does the model see" is decided ad-hoc at each call site: the WS handler slices raw session messages, the agent loop keeps its own `KnowledgeAccumulator` run-memory, templates interpolate history via `str.replace`. No component owns conversation memory semantics (roles, truncation, tool-result folding).

**Root Cause:** Sessions were built as a persistence feature, not a memory subsystem; consumers improvised.

**Current Design:** Each consumer slices raw message lists differently.

**Target Design:** `ConversationMemory(session_store, budget)`: `record(turn)`, `window(token_budget) -> list[Turn]`, `pin(turn_id)`, folding rules for tool-call/result pairs. All model-bound history flows through `window()`; the agent loop records tool turns into the same stream (tagged `visibility=agent`).

**Justification:** Memory is a named review dimension currently implemented as "whatever each call site does".

**Benefits:** One truncation policy; tool turns replayable; pinned instructions survive windowing.

**Risks:** Behavior change in what history reaches prompts — parity snapshot on fixtures first.

**Required Tests:** Unit: window budget math, pinning, folding. Golden: fixture session → expected window at 3 budget levels.

**Acceptance Criteria:** No call site slices session messages directly (grep); all history reaches prompts via `window()`.

**Future Expansion:** R-304 summarization plugs in as a window strategy; R-802 adds semantic recall layer.

---

### R-303 — Session ↔ Project Binding

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 2/5 |
| **Time Estimate** | 1d |
| **Dependencies** | R-301, R-102 |
| **Breaking Changes** | Sessions opened under wrong project now warn/block |
| **Affected Modules** | `actions/session_manager.py`, `server.py` (switch_project path) |

**Problem Statement:** Sessions carry no project identity. After `api_switch_project`, the active session continues accumulating messages that reference files from a different project; history becomes cross-project noise injected into future context.

**Root Cause:** Sessions and projects evolved as unrelated features.

**Current Design:** Ambient association only.

**Target Design:** `project_id` (root-path hash) stamped in session meta at creation. On project switch: active session auto-closes and a new bound session opens (configurable: `warn_only`). `ConversationMemory.window()` filters/flags foreign-project turns during migration period.

**Justification:** Cross-project contamination silently poisons context quality — cheap to fix, hard to notice.

**Benefits:** Honest history; per-project session listing becomes possible.

**Risks:** Users who intentionally span projects — `warn_only` mode preserves old behavior explicitly.

**Required Tests:** Unit: binding stamp, switch behavior in both modes. Integration: switch project → new session created, old session closed with reason recorded.

**Acceptance Criteria:** Every new session has `project_id`; switch behavior matches config; foreign-turn flagging covered by test.

**Future Expansion:** Project memory (R-805) keys off the same `project_id`.

---

### R-304 — History Windowing & Summarization

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 4/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-302, R-203 |
| **Breaking Changes** | None (additive strategy) |
| **Affected Modules** | `memory/conversation.py`, `memory/summarizer.py` (new) |

**Problem Statement:** History injection is bounded only by ad-hoc slicing; long sessions either overflow (pre-R-203) or lose all early context abruptly. There is no graceful degradation between "full history" and "amnesia".

**Root Cause:** No summarization layer; windowing = truncation.

**Current Design:** Hard slice.

**Target Design:** Tiered window under `ContextBudget`: recent turns verbatim → older turns as running summary (LLM-generated, stored as memory artifacts in the JSONL stream, incrementally updated every N turns) → pinned items always verbatim. Summaries regenerated asynchronously, never blocking the hot path; fallback to hard slice if summary unavailable.

**Justification:** Long-session quality is the product's core loop; abrupt amnesia is a top user-visible failure.

**Benefits:** Bounded tokens with preserved long-range coherence; summaries auditable in the session log.

**Risks:** Summary drift/hallucination — summaries are labeled as summaries in the prompt; verbatim recent window never shrinks below a floor.

**Required Tests:** Unit: tier assembly math, floor enforcement, async fallback. Golden: 60-turn fixture → window contains summary block + last-k verbatim within budget.

**Acceptance Criteria:** 100-turn session prompt stays within budget with summary present; hot path never awaits summarization. Fact-retention gate: a fact stated at turn 5 remains represented (verbatim or in summary) and answerable at turn 100.

**Future Expansion:** Summary quality scoring; per-topic summary threads (Phase 8).

---

### R-305 — Run Artifact Retention & GC

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 2/5 |
| **Time Estimate** | 1d |
| **Dependencies** | R-105 |
| **Breaking Changes** | Old artifacts deleted per policy (intended) |
| **Affected Modules** | `chain/bridge.py` (ProjectSnapshot), `core/registry.py`, new `core/retention.py` |

**Problem Statement:** Chain runs persist state/snapshots with no retention policy; `ProjectSnapshot` is created with **empty** `relevant_file_hashes` (bridge.py L226–235) — an artifact that costs storage and provides no resume value (resume itself is dead, see R-601). Session TTL exists (30d) but run artifacts accumulate forever.

**Root Cause:** Persistence written for a resume feature that was never wired.

**Current Design:** Write-only artifact graveyard.

**Target Design:** `RetentionPolicy` (keep last N runs per project + max age + max bytes) executed by a sweep on registry `finish()` and on startup; the same policy governs R-106 checkpoint storage. Snapshot creation fixed to record actual file hashes (prerequisite for R-601) or skipped entirely when resume is disabled.

**Justification:** Honest storage lifecycle; removes a lying artifact.

**Benefits:** Bounded disk; snapshots become meaningful; startup sweep self-heals crashed-run debris.

**Risks:** Deleting artifacts a user wanted — policy is config-visible with dry-run logging first release.

**Required Tests:** Unit: policy matrix (N/age/bytes), sweep idempotence. Integration: snapshot contains real hashes for touched files.

**Acceptance Criteria:** Artifact count bounded across 20 fixture runs; snapshots non-empty or absent — never empty-but-present.

**Future Expansion:** Artifact export/import for debugging (Phase 8).

---

## Phase 3 — Definition of Done
- [ ] `append_message` O(1); perf test in CI; legacy sessions migrated.
- [ ] All model-bound history flows through `ConversationMemory.window()`.
- [ ] Sessions bound to projects; switch behavior config-verified.
- [ ] 100-turn session stays in budget via summarization tiers.
- [ ] Run artifacts under retention policy; snapshots truthful.
- [ ] Session/memory test suite green; sessions dir gitignored.

---

# PHASE 4 — Routing & Budget Semantics (Week 7)

Goal: one strategy vocabulary, deterministic routing, budget numbers that mean what they say.

---

### R-401 — Unify the Two Strategy Vocabularies

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-102 |
| **Breaking Changes** | Internal enum consolidation; WS strategy names normalized |
| **Affected Modules** | `chain/orchestrator.py`, `chain/router.py`, `chain/strategies.py`, `server.py` |

**Problem Statement:** `SmartOrchestrator` speaks {direct, context_window, chunk_chain, map_reduce, pipeline, delegate}; `RequestRouter` speaks {direct, auto_chain, full_chain, delegate}. The mapping between the two is implicit in scattered conditionals; adding a strategy requires touching both vocabularies plus the translation points, and mismatches route silently to wrong builders.

**Root Cause:** Router was added after orchestrator with its own abstraction level (routing tier vs execution strategy) but the levels were never formalized.

**Current Design:** Two overlapping enums + implicit mapping.

**Target Design:** Two **explicit** layers: `RoutingTier` (direct/chained/delegate) decided by router, and `ExecutionStrategy` (the six builders) decided by orchestrator **within** a tier. A single `STRATEGY_TABLE: dict[ExecutionStrategy, StrategyBuilder]` registry; conversion functions live in one module with exhaustiveness checks (`assert_never`).

**Justification:** Routing is the system's dispatch spine; two vocabularies is a standing invitation for silent misroutes.

**Benefits:** Adding a strategy = one registry entry; exhaustiveness enforced at import time; router/orchestrator responsibilities finally distinct.

**Risks:** Subtle tier-mapping changes — table-driven parity test against recorded current decisions.

**Required Tests:** Unit: exhaustiveness (every enum member has builder), tier→strategy mapping matrix. Parity: 30 recorded requests route identically pre/post. Golden corpus: 30 recorded real routing decisions (captured pre-refactor, covering all 6 orchestrator + 4 router strategies) reproduce identically post-refactor.

**Acceptance Criteria:** grep finds each strategy name defined exactly once; misroute test class green; registry-driven dispatch only.

**Future Expansion:** Registry becomes the plugin surface for R-801.

---

### R-402 — Deterministic, Explainable Routing

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-401 |
| **Breaking Changes** | Routing decisions may shift at threshold edges (logged) |
| **Affected Modules** | `chain/orchestrator.py` (5D scoring), `chain/router.py` (thresholds 2.0/5.0/8.0, downgrade cascade) |

**Problem Statement:** Complexity scoring is regex-keyword-driven across 5 dimensions with magic thresholds (orchestrator: ≤2/≤4/≤7; router: 2.0/5.0/8.0 — different scales, unrelated constants), plus a budget-downgrade cascade. Decisions are neither explainable to the user nor reproducible in tests without replicating the full regex tables.

**Root Cause:** Heuristics accreted; no decision record.

**Current Design:** Opaque score → threshold → maybe downgraded, unlogged.

**Target Design:** `RoutingDecision` record: input features (each dimension's raw score + matched signals), thresholds applied, tier chosen, downgrades applied with reasons — emitted on the EventBus (R-604) and logged. Thresholds move to config with documented semantics. Scoring functions become pure (features in → score out) for table-driven tests.

**Justification:** "Why did it pick full_chain?" is currently unanswerable — for users and for regression tests alike.

**Benefits:** Reproducible routing tests; user-visible explanation frame; threshold tuning without code changes.

**Risks:** None functional — purely additive observability plus config extraction.

**Required Tests:** Table-driven: 25 feature vectors → expected decisions. Property: monotonicity (higher complexity never routes to a *lighter* tier absent budget downgrade).

**Acceptance Criteria:** Every routed request has a persisted `RoutingDecision`; thresholds config-sourced; monotonicity property green.

**Future Expansion:** Learned/statistical scorer can replace regex scorer behind the same pure interface (Phase 8).

---

### R-403 — Honest Budget Semantics

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-401 |
| **Breaking Changes** | Admission decisions change where old logic was wrong (intended) |
| **Affected Modules** | `providers/budget.py` (AccountAwareBudget), `providers/pool.py` (`_failed_names` never reset), `chain/router.py` (MIN_ACCOUNTS) |

**Problem Statement:** `AccountAwareBudget` conflates **account count** with **affordable steps** (an account ≠ a unit of work); router's MIN_ACCOUNTS gates strategies on this fiction. Separately, `ProviderPool._failed_names` is never auto-reset (`reset_failures()` has zero callers) — a provider that fails once is dead until process restart, silently shrinking capacity and triggering spurious budget downgrades.

**Root Cause:** Budget model built from what was countable (accounts) rather than what matters (estimated step cost vs available capacity); failure tracking shipped without recovery.

**Current Design:** Accounts-as-steps + permanent provider blacklisting.

**Target Design:** `CapacityModel`: per-provider health (half-open circuit breaker: failed → cooldown → probe) replacing the permanent set; budget admission = estimated run cost (steps × cost rank) vs current healthy capacity. Router downgrade consumes `CapacityReport`, not account counts. `BudgetTracker` reserve/commit/release stays (it is sound) and binds to the same model.

**Justification:** Two lies compound: fake step math over fake capacity numbers. Downgrades fire wrongly in both directions.

**Benefits:** Providers self-heal; downgrades correlate with real capacity; budget snapshot becomes debuggable truth.

**Risks:** Circuit-breaker flapping — cooldown with exponential backoff and jitter.

**Required Tests:** Unit: breaker state machine (fail→cooldown→probe→recover/re-fail), admission math. Integration: provider failure then recovery → pool reuses it without restart.

**Acceptance Criteria:** `reset_failures` deleted or invoked by the breaker; no admission decision reads raw account counts; recovery E2E green.

**Future Expansion:** Real token-cost accounting from provider usage callbacks feeds the same model.

---

## Phase 4 — Definition of Done
- [ ] One strategy registry; enums exhaustiveness-checked; parity verified.
- [ ] Every routing decision recorded and explainable; thresholds in config.
- [ ] Provider failures self-heal via circuit breaker; capacity model replaces account-count fiction.
- [ ] Routing/budget table-driven test suites in CI.

---

# PHASE 5 — Agent Architecture (Week 8–9)

Goal: unify execution behind one interface, make agent definitions data, and stop knowledge re-injection.

---

### R-501 — Runner Protocol: One Interface for Four Execution Modes

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 4/5 |
| **Time Estimate** | 4d |
| **Dependencies** | R-102, R-104, R-105 |
| **Breaking Changes** | Internal — server dispatch rewritten |
| **Affected Modules** | new `core/runner.py`, `server.py`, `chain/bridge.py`, `chain/agent_loop.py`, `chain/delegate.py` |

**Problem Statement:** Direct mode, ChainBridge, AgentLoop, and DelegateBridge each expose bespoke entry points with different signatures, different result shapes, different cancellation/approval/error handling. The WS handler contains four divergent dispatch branches (including the agent-loop polling workaround: `ws.receive` timeout 0.3s inside a thread-join loop, server.py L920–965). Adding a fifth mode means a fifth snowflake.

**Root Cause:** Modes accreted; no one extracted the common lifecycle.

**Current Design:** Four bespoke pipelines sharing nothing but globals.

**Target Design:** `Runner` protocol: `run(request: RunRequest, ticket: RunTicket, events: EventSink) -> RunResult`. `RunRequest` carries mode, message, `ContextBundle`, memory window, policy. All four modes become `Runner` implementations; WS handler becomes: route → build request → `registry.execute(runner, request)` → stream events. Approval and cancellation flow through ticket/gate uniformly (fixes delegate's missing cancellation interface-level, building on R-105).

**Justification:** The single highest-leverage maintainability refactor: it collapses the server's dispatch complexity and makes every later feature (parallelism, workers, plugins) mode-agnostic.

**Benefits:** WS handler shrinks to a thin router; new modes = new class + registry entry; uniform error taxonomy across modes; polling workaround replaced by event-driven approval waits.

**Risks:** Largest behavioral surface in the roadmap — migrate one mode at a time (direct → chain → agent → delegate), keeping legacy paths behind a flag until parity per mode is proven.

**Required Tests:** Contract suite run against all four runners (start/succeed/fail/cancel/approve). Parity E2E per mode vs recorded legacy transcripts.

**Acceptance Criteria:** `server.py` contains one dispatch path; four runners pass the shared contract suite; polling loop deleted.

**Future Expansion:** R-804 remote workers implement the same protocol over a queue.

---

### R-502 — Agent Manifest: Definitions as Data

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 2/5 |
| **Time Estimate** | 1.5d |
| **Dependencies** | None (parallel) |
| **Breaking Changes** | `agents_rules/` layout gains manifest (legacy fallback retained one release) |
| **Affected Modules** | `chain/agent_loader.py` (ROLE_MAP), `agents_rules/manifest.yaml` (new) |

**Problem Statement:** `AgentLoader.ROLE_MAP` hardcodes 21 roles to Arabic-named markdown paths (e.g., `"code_analyzer": "سيستم/أنت محلل جودة.md"`) in Python source; renaming a file requires a code change; the prompt cache has no mtime invalidation, so editing an agent file mid-process serves stale prompts until restart.

**Root Cause:** Quickest wiring won; filenames became API.

**Current Design:** Code-embedded path map + stale cache; 3-level fallback masks missing files.

**Target Design:** `agents_rules/manifest.yaml`: role → {file, description, tools_allowed, model_hints}. Loader reads manifest; cache keyed by (path, mtime); missing role = loud structured error (fallback only for explicitly-declared `fallback:` chains). Frozen `AgentPrompt` + content hash retained.

**Justification:** Agent definitions are content, not code; hot-editing agents is a core authoring workflow currently broken by the cache.

**Benefits:** Rename/add agents without deploys; mid-session prompt edits take effect; manifest documents the fleet.

**Risks:** Manifest/file drift — startup validation asserts every manifest entry resolves.

**Required Tests:** Unit: manifest parse/validate, mtime invalidation, declared-fallback vs missing-role error. Integration: edit agent file → next run uses new content.

**Acceptance Criteria:** ROLE_MAP deleted; startup fails fast on broken manifest; hot-reload test green. Parity gate: all 21 legacy ROLE_MAP agents resolve identically through the manifest.

**Future Expansion:** Per-project agent overrides (project manifest shadows global) in Phase 8.

---

### R-503 — Knowledge Deduplication via ContextBundle

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-202, R-501 |
| **Breaking Changes** | Agent prompt assembly changes (token-reducing) |
| **Affected Modules** | `chain/knowledge.py`, `chain/agent_loop.py` |

**Problem Statement:** `KnowledgeAccumulator` stores full file contents in `_files_read` and `build_context` re-injects **everything** on **every** iteration (max 8) — an O(iterations × corpus) token bill; char-based truncation then randomly amputates whatever exceeded the cap, regardless of relevance or recency.

**Root Cause:** Accumulator predates any shared context container.

**Current Design:** Grow-only dict of raw strings, replayed wholesale per iteration.

**Target Design:** Accumulator becomes a view over the run's `ContextBundle`: tool results register items (hash-deduped); per-iteration prompt = budget-admitted delta (new items verbatim, previously-sent items as one-line references: `file X already read (hash…)`) — the model's own conversation history preserves earlier content.

**Justification:** Directly multiplies agent-loop cost; also the last remaining private context store after Phase 2.

**Benefits:** Iteration cost flat instead of linear-growing; consistent with global budget/dedup; observable per-iteration token metrics.

**Risks:** Model losing track of referenced-not-repeated content — recent-k items always verbatim; reference format tested for recall on fixtures.

**Required Tests:** Unit: delta computation, reference rendering, recent-k floor. Regression: 6-iteration fixture — per-iteration tokens flat within 15%; task success parity.

**Acceptance Criteria:** No full-content re-injection after first send; token flatness test green; `_files_read` raw store removed.

**Future Expansion:** Cross-run knowledge reuse through project memory (R-805).

---

### R-504 — run_command: Terminal/Test Feedback Loop for Agents

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-105 (cancellable ticket for long commands), R-501 (Runner protocol), R-106 (mutating commands must be checkpointable) |
| **Breaking Changes** | None (additive tool) |
| **Affected Modules** | `chain/agent_tools.py`, `AgentRunner`, agent prompt templates |

**Problem Statement:** Agents propose code changes without any way to verify them. There is no tool for "run the test suite", "run the linter", or "execute this script and read stdout/stderr" — an agent finishes a task believing it succeeded purely because generation completed, not because anything was checked. This is the gap between "writes code" and "writes code that works."

**Root Cause:** `cmd_runner` exists in the codebase for direct user-invoked commands but was never exposed as an agent tool with a feedback path back into the loop.

**Current Design:** `AgentTools` exposes file read/write/search but no execute-and-observe primitive; the agent loop has no "did it actually work" checkpoint.

**Target Design:** A `run_command` agent tool (allowlisted commands per project — test runners, linters, type checkers, build scripts — configurable, never arbitrary shell by default) executing via the existing `cmd_runner`, capturing stdout/stderr/exit code and feeding the result into the next agent iteration as a `high`-tier context item. The agent system prompt makes verification a normal step: for code-editing tasks where a test command is configured, the loop runs it before declaring success. Long-running commands get a `RunTicket`-linked cancellation checkpoint (R-105) and a timeout. Any file changes a command makes (e.g. an autoformatter) route through the same `ApprovalGate`/`CheckpointManager` path as any other agent write (R-104/R-106) — no separate, ungated way for a command to mutate the workspace.

**Justification:** Verification loops are what make autonomous multi-file agent edits trustworthy enough to rely on; without this, every "done" claim from the agent is an unfalsifiable guess.

**Benefits:** Measurable reduction in agent-reported-success-but-actually-broken outcomes; agents self-correct within a run instead of shipping a broken first attempt.

**Risks:** Command execution is a security surface — mitigated by a project-level allowlist (configured, not agent-chosen) and by routing resulting writes through the existing approval/checkpoint machinery; runaway processes — bounded by ticket-linked timeout and cancellation.

**Required Tests:** Allowlist enforcement (non-allowlisted command rejected with a clear error, never silently run); fixture project where an agent's first attempt fails a test and the second iteration, informed by the failure output, passes it; timeout/cancellation of a hung command; command-triggered file writes gated and checkpointed identically to direct agent writes.

**Acceptance Criteria:** `run_command` tool live and allowlist-enforced; fail-then-fix fixture test green; no command-triggered write bypasses `ApprovalGate`/`CheckpointManager`.

**Future Expansion:** Structured test-result parsing (pass/fail counts, failing assertions) as a richer context item; auto-retry budget tied to `ExecutionRegistry`.

---

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; shared contract suite green; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works; ROLE_MAP deleted.
- [ ] Agent iteration token cost flat; knowledge is a bundle view.
- [ ] **Agents execute allowlisted commands via `run_command` and self-correct from failure output; command-triggered writes remain gated and checkpointed.**
- [ ] Per-mode parity E2E recorded and green.

---

# PHASE 6 — Chain Engine Maturity (Week 10–11)

Goal: make the executor's promises real — resume, context policy, parallelism — and give the system a nervous system.

---

### R-601 — Wire Crash Resume (or Delete It)

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | Phase 1 (R-105), R-305 (truthful snapshots) |
| **Breaking Changes** | None |
| **Affected Modules** | `chain/executor.py` (`can_resume`/`load_state` L459–480 — zero callers), `chain/bridge.py`, `server.py` |

**Problem Statement:** `ChainExecutor.can_resume`/`load_state` are fully implemented classmethods with **zero callers** (grep-verified) — crash recovery is fictional. Combined with empty snapshots (R-305), a mid-run crash loses all completed step work and budget commitments.

**Root Cause:** Feature built bottom-up; the top (startup/WS wiring) never arrived.

**Current Design:** Dead code advertising a capability the system lacks.

**Target Design:** Decision point — **wire it**: on startup and on `start_chain`, registry checks for resumable runs (validating snapshot hashes against current files); WS offers `resume_run`/`discard_run`; executor `load_state` path covered by kill-and-resume tests. If product decides resume is not wanted: delete both methods and the persistence that feeds them (do not keep fiction). Roadmap assumes **wire it**.

**Justification:** Dead code that *looks* like a safety feature is worse than absence — reviewers and users assume protection that doesn't exist.

**Benefits:** Long chain runs survive restarts; committed budget not re-spent; honest capability surface.

**Risks:** Resuming against changed files — hash validation refuses and falls back to discard-with-report.

**Required Tests:** Integration: kill executor after step 2 of 5 → resume completes 3–5 only; hash-mismatch → refusal path. Unit: state round-trip.

**Acceptance Criteria:** `can_resume` has production callers (grep); kill-resume E2E green; or (delete branch) methods and dead persistence removed.

**Future Expansion:** Resume across worker processes (R-804).

---

### R-602 — Enforce ChainStep Context Policy

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-202, R-203 |
| **Breaking Changes** | Step prompts shrink where policy says so (intended) |
| **Affected Modules** | `chain/executor.py` (context_policy — currently ignored), `chain/models.py` (`build_prompt`) |

**Problem Statement:** `ExecutionPolicy`/step-level `context_policy` exists in the model but the executor **never enforces it**; `ChainStep.build_prompt` concatenates full dependency results unconditionally. Policy fields are decorative.

**Root Cause:** Model-first design; enforcement deferred and forgotten.

**Current Design:** Policy stored, ignored; unconditional concatenation.

**Target Design:** `build_prompt` consumes policy via `ContextBudget`: `full` → verbatim deps; `summary` → dep-result summaries (cached per step output); `minimal` → titles + status only. Executor validates policy at plan time (unknown values fail fast).

**Justification:** Pipeline strategies on large repos are unusable while every step inherits every ancestor's full output.

**Benefits:** Deep chains stay in budget; policy fields become real levers for strategy builders.

**Risks:** Summary-starved steps — strategy builders explicitly mark data-dependent edges `full`.

**Required Tests:** Unit: three policy modes render matrix. Golden: 5-step pipeline fixture — step-5 prompt token count under policy vs unbounded baseline (≥50% reduction).

**Acceptance Criteria:** Policy provably alters prompts (golden diffs); no unconditional dep concatenation remains.

**Future Expansion:** Adaptive policy (executor tightens policy when budget pressure rises).

---

### R-603 — Bounded Parallel Step Execution

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 4/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-105, R-403, R-602 |
| **Breaking Changes** | Step completion order becomes nondeterministic (results remain deterministic) |
| **Affected Modules** | `chain/executor.py` (sequential `ready[0]` L204–206), `chain/models.py` (BudgetTracker — already thread-safe) |

**Problem Statement:** The executor computes the full ready-set from the DAG, then executes `ready[0]` — strictly sequential despite `policy.max_parallel_steps` existing in `ExecutionPolicy`. Map-reduce's independent map steps (the *point* of the strategy) serialize; wall-clock time is O(steps) always.

**Root Cause:** Sequential first cut; the policy knob shipped before the engine honored it.

**Current Design:** DAG-aware scheduler, single-lane execution.

**Target Design:** `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)` over the ready set; `BudgetTracker` reservations (already lock-protected) gate submissions; cancellation token checked pre-submit and step results merged under a run lock; failure policy (fail-fast vs continue-independent-branches) explicit in `ExecutionPolicy`.

**Justification:** Map-reduce exists to parallelize; the current engine defeats its own headline strategy.

**Benefits:** Map-phase wall-clock ≈ longest step, not sum; policy knob becomes real; provider pool utilization improves.

**Risks:** Concurrency bugs in state merge — all `ChainRun` mutations funneled through one guarded `apply_step_result()`; stress test with fault injection.

**Required Tests:** Unit: scheduler respects max_parallel; fail-fast vs continue semantics; cancel drains pool. Stress: 20-map fixture, injected failures/cancels, state always consistent. Perf: 8 independent steps at parallel=4 → ≥3× speedup.

**Acceptance Criteria:** `max_parallel_steps=1` reproduces legacy behavior exactly; speedup benchmark green; zero state races under stress.

**Future Expansion:** Distribution across worker processes (R-804) reuses the same scheduler contract.

---

### R-604 — EventBus: Unified Internal Event Flow

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-501 |
| **Breaking Changes** | None (WS frame shapes preserved by adapter) |
| **Affected Modules** | new `core/events.py`, `server.py`, all runners |

**Problem Statement:** Progress/status/approval events reach the client through mode-specific ad-hoc `ws.send` calls scattered across bridge/agent-loop/delegate; internal consumers (logging, metrics, R-402 routing records) have no subscription point; the agent approval flow abuses a polling receive-loop for lack of an event channel.

**Root Cause:** WebSocket was the only consumer, so emission was welded to it.

**Current Design:** Direct `ws.send` from execution internals.

**Target Design:** In-process `EventBus` (typed events: `RunStarted/StepProgress/ApprovalRequested/RunFinished/RoutingDecided/BudgetChanged`); WS layer subscribes and adapts to existing frame shapes (wire compatibility preserved); logging/metrics subscribe independently; approval becomes request-event + response-correlation instead of polling.

**Justification:** Decouples execution from transport — prerequisite for multi-connection (R-701) and workers (R-804), and the fix that finally deletes the polling workaround's root cause.

**Benefits:** Runners lose all `ws` knowledge; event history per run persists for debugging; new consumers subscribe without touching execution code.

**Risks:** Event-order guarantees — per-run FIFO delivery contract, tested.

**Required Tests:** Unit: pub/sub, per-run ordering, slow-subscriber isolation. Integration: full chain run → WS client receives identical frame sequence as legacy recording.

**Acceptance Criteria:** grep: no `ws.send` outside the WS adapter; frame-parity recording green; runners import zero transport modules.

**Future Expansion:** Bus interface backed by Redis streams for multi-process (R-804).

---

## Phase 6 — Definition of Done
- [ ] Resume wired end-to-end (kill-resume E2E) or deleted with its persistence.
- [ ] Context policy provably shapes step prompts; golden diffs recorded.
- [ ] Parallel map phase ≥3× speedup; `parallel=1` byte-identical to legacy.
- [ ] All events flow through EventBus; WS frame parity verified; polling deleted.

---

# PHASE 7 — Platform Hardening (Week 12–13)

Goal: multi-connection correctness, indexed project awareness, and a repo that tells the truth.

---

### R-701 — Session-Scoped State: Multi-Connection Correctness

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 4/5 |
| **Time Estimate** | 4d |
| **Dependencies** | R-102, R-105, R-604; Phases 1–3 complete |
| **Breaking Changes** | None for single client; defines semantics for multi-client |
| **Affected Modules** | `server.py`, `core/registry.py`, new `core/session_context.py` |

**Problem Statement:** All state is process-global: two WS connections share the active project, active model, active session, and (pre-R-105) the run slot. A second browser tab switching projects hijacks the first tab's agents mid-run. Single-user assumption is baked into every handler.

**Root Cause:** Global-singleton architecture (see R-102) plus no connection identity.

**Current Design:** One implicit global "user".

**Target Design:** `SessionContext` per WS connection: own active project handle, model selection, conversation session, subscribed event streams — layered over shared `AppContext` services (pool, registry, engines). Project mutation conflicts governed by registry per-project locks (R-105); event delivery filtered by connection subscription (R-604).

**Justification:** Even a single user opens two tabs; today that corrupts runs. Also the gateway to any multi-user future.

**Benefits:** Tabs are isolated; per-connection model/project choices; groundwork for auth-attached identity later (out of scope itself).

**Risks:** Hidden global reads remaining — audit via a lint rule banning module-level state imports in handlers.

**Required Tests:** Integration: two WS clients — B switches project; A's running agent still reads A's project (id()-asserted); events routed to correct client only.

**Acceptance Criteria:** Two-tab E2E green; no handler reads module-level mutable state (lint enforced).

**Future Expansion:** Real multi-user with authenticated identity mapping (explicitly out of current scope).

---

### R-702 — ProjectIndex: Replace rglob Storms

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-201 |
| **Breaking Changes** | None |
| **Affected Modules** | new `context/project_index.py`, `context/engine.py`, `actions/file_manager.py` (`get_project_context`) |

**Problem Statement:** Context gathering executes per-word `fm.root.rglob(f"*{stem}*")` filesystem walks per message (pre-R-201 interim only caches per message); `get_project_context` returns a flat unranked file list. Every lookup is a cold O(files) scan; large repos make every message pay a directory-walk tax.

**Root Cause:** No index; filesystem used as the query engine.

**Current Design:** Repeated recursive globs.

**Target Design:** `ProjectIndex`: in-memory inverted index (name-stems → paths, ext → paths, path-trie) built at project open, refreshed by mtime-scan on demand + invalidated by FileManager write hooks; ranked lookup (exact > prefix > substring) serving `MentionSource` and structure summaries.

**Justification:** Context latency scales with repo size today; index makes it O(1)-ish per query.

**Benefits:** Millisecond mention resolution on large repos; ranked (not arbitrary-first) matches; foundation for symbol-level indexing later.

**Risks:** Staleness after external file changes — mtime-scan on gather when index older than N seconds; write-through hooks from FileManager.

**Required Tests:** Unit: index build/lookup/ranking/invalidation. Perf: 5k-file fixture — mention resolution <10ms, zero rglob calls (patched-assert).

**Acceptance Criteria:** grep: no `rglob` in context paths; perf test green; FileManager writes update index.

**Future Expansion:** ctags/tree-sitter symbol layer; embedding index slot (Phase 8).

---

### R-703 — Repo Hygiene & Real Test Infrastructure

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 2/5 |
| **Time Estimate** | 2d (infra) — suites accrue throughout phases |
| **Dependencies** | None (start immediately; listed here as completion gate) |
| **Breaking Changes** | None |
| **Affected Modules** | `README.md`, `.gitignore`, `tests/` (new), CI config (new), `config.yaml` |

**Problem Statement:** README claims "125/125 tests passing" — `tests/` **does not exist**. 43 session JSON files are git-tracked. `config.yaml` sets `default_provider: use_ai` while the server defaults to `genspark` — config and code disagree about a basic default. The repo actively misinforms its maintainers.

**Root Cause:** Documentation written aspirationally; hygiene never enforced.

**Current Design:** Fictional test claim, leaked user data in VCS, contradictory defaults.

**Target Design:** `tests/` with pytest + fixtures (fixture project, FakeProvider, WS test client); CI running on every PR with coverage gate (start 40%, ratchet per phase); sessions/artifacts gitignored and purged from history (`git filter-repo` — sessions may contain user content); README claims regenerated from CI truth; single source for defaults (config wins; server reads it).

**Justification:** Every other roadmap item's acceptance criteria presume a test harness; and shipping user sessions in git is a privacy defect.

**Benefits:** Trustworthy repo; regression safety for the entire roadmap; onboarding honesty.

**Risks:** History rewrite disrupts clones — coordinate; tag pre-rewrite ref.

**Required Tests:** Meta: CI badge reflects real runs; coverage gate enforced; a canary test proving fixtures load.

**Acceptance Criteria:** README contains zero unverifiable claims; sessions absent from history; CI green with ratcheting coverage; config/code defaults agree (test-asserted).

**Future Expansion:** Nightly E2E against live providers (opt-in, keyed).

---

## Phase 7 — Definition of Done
- [ ] Two concurrent WS clients fully isolated (project/model/session/events).
- [ ] Zero rglob in context paths; 5k-file perf budget met.
- [ ] CI + coverage ratchet live; README truthful; sessions purged from VCS history.
- [ ] Lint rule bans module-level mutable state in handlers.

---

# PHASE 8 — Extensibility Horizon (Week 14+)

Goal: turn the now-clean seams into extension points. Items here are directional; re-scope at phase entry.

---

### R-801 — Strategy Plugin Registry

| Field | Value |
|---|---|
| **Priority** | Low |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-401, R-501 |
| **Breaking Changes** | None |
| **Affected Modules** | `chain/strategies.py`, `core/plugins.py` (new) |

**Problem Statement:** Adding an execution strategy still requires editing core modules even after R-401's registry.

**Root Cause / Current Design:** Static registry populated in-tree.

**Target Design:** Entry-point-based plugin discovery (`webdev_ai.strategies` group): a plugin ships a `StrategyBuilder` + routing hints; validated at load (schema + dry-run plan on a fixture); failures quarantine the plugin, never the host.

**Justification / Benefits:** Third-party/experimental strategies without forking; core stays closed for modification, open for extension.

**Risks:** Malicious/broken plugins — capability-scoped API surface (plugins receive `ContextEngine` views, never raw `fm`).

**Required Tests:** Plugin load/validate/quarantine matrix; sample plugin E2E.

**Acceptance Criteria:** Demo strategy installed from a separate package routes and executes; broken plugin cannot crash startup.

**Future Expansion:** Signed plugin manifests.

---

### R-802 — Layered Memory (Working / Episodic / Semantic)

| Field | Value |
|---|---|
| **Priority** | Low |
| **Complexity** | 4/5 |
| **Time Estimate** | 5d |
| **Dependencies** | R-302, R-304, R-206 |
| **Breaking Changes** | None (additive recall source) |
| **Affected Modules** | `memory/` |

**Problem Statement:** After R-304, memory is recency-tiered but has no *relevance* recall — a decision made 80 turns ago about architecture X is invisible unless recent.

**Target Design:** Builds on and upgrades the minimal `SemanticSource` seeded in R-206. Three layers over the JSONL stream: working (R-302 window), episodic (per-run/task summaries, queryable by time/task), semantic (embedding index over turns+summaries; retrieval injected as a budgeted `ContextBundle` source). Retrieval is a ContextEngine source (R-201 seam), nothing else changes.

**Justification / Benefits:** Long-horizon coherence; "as we decided earlier" actually resolves.

**Risks:** Retrieval noise — strict budget priority (`opportunistic`), provenance-labeled.

**Required Tests:** Retrieval precision fixtures; budget interaction; latency cap (async with fallback-to-skip).

**Acceptance Criteria:** 100-turn fixture: question about turn-10 decision answered correctly with retrieval on, fails without — demonstrating causal value.

**Future Expansion:** Cross-session semantic recall via project memory (R-805).

---

### R-803 — Pluggable Planners

| Field | Value |
|---|---|
| **Priority** | Low |
| **Complexity** | 4/5 |
| **Time Estimate** | 4d |
| **Dependencies** | R-402, R-501 |
| **Breaking Changes** | None |
| **Affected Modules** | `chain/orchestrator.py`, `core/planner.py` (new) |

**Problem Statement:** Planning = regex-scored heuristics; no path to LLM-driven or hybrid planning without rewriting the orchestrator.

**Target Design:** `Planner` protocol: `plan(request, context, capacity) -> ExecutionPlan` (tier + strategy + step graph + policies). Current heuristic becomes `HeuristicPlanner`; add `LLMPlanner` (model proposes plan, schema-validated, capacity-checked) and `HybridPlanner` (heuristic gate → LLM refine). Selection per-request via config; every plan emits R-402 decision records.

**Justification / Benefits:** Planning quality becomes competitive/iterable; A/B-able via decision records.

**Risks:** LLM plans that violate constraints — hard schema validation + capacity re-check; fallback to heuristic on rejection.

**Required Tests:** Protocol contract suite; LLM planner with recorded responses; fallback path.

**Acceptance Criteria:** Planner swap via config with zero core edits; invalid LLM plan falls back cleanly.

**Future Expansion:** Plan-quality feedback loop from run outcomes.

---

### R-804 — Worker Pool / Horizontal Execution

| Field | Value |
|---|---|
| **Priority** | Low |
| **Complexity** | 5/5 |
| **Time Estimate** | 8d |
| **Dependencies** | R-501, R-603, R-604, R-701 |
| **Breaking Changes** | Deployment topology (single-process mode remains default) |
| **Affected Modules** | `core/registry.py`, `core/events.py`, new `workers/` |

**Problem Statement:** Single Flask process is the hard ceiling: one heavy chain run starves the WS loop; no scale-out path.

**Target Design:** Registry + EventBus grow pluggable backends (in-mem default → Redis); `Runner` executions dispatchable to worker processes consuming a queue, streaming events back over the bus; workspace access via per-project lease from the registry. Single-process remains a first-class configuration (same interfaces, in-proc backends).

**Justification / Benefits:** Wall-clock isolation of heavy runs; horizontal capacity; zero interface change thanks to Phases 5–6 seams.

**Risks:** Distributed-state complexity — leases with TTL, idempotent event replay, chaos tests.

**Required Tests:** In-proc vs worker parity suite (same contract tests, both backends); kill-worker mid-run → registry recovers lease; event replay idempotence.

**Acceptance Criteria:** A chain run executes on a worker with byte-identical WS frame sequence vs in-proc; WS latency unaffected by heavy runs (measured).

**Future Expansion:** Autoscaling policies; per-tenant worker pools.

---

### R-805 — Persistent Project Memory

| Field | Value |
|---|---|
| **Priority** | Low |
| **Complexity** | 4/5 |
| **Time Estimate** | 5d |
| **Dependencies** | R-303, R-702, R-802 |
| **Breaking Changes** | None |
| **Affected Modules** | new `memory/project_memory.py`, `context/engine.py` |

**Problem Statement:** Every session starts amnesiac about the project: conventions discovered, decisions made, and past run outcomes are relearned (and re-paid-for) every time.

**Target Design:** Per-`project_id` durable store: architectural facts, conventions, decision log, run outcome summaries — written via explicit agent tool (`remember_fact`) and post-run distillation; served as a budgeted ContextEngine source; user-inspectable/editable (it is *their* project's memory); hash-linked to ProjectIndex state for staleness detection.

**Justification / Benefits:** Compounding assistant quality per project; fewer re-discovery tool calls; user trust via inspectability.

**Risks:** Stale/wrong facts persisting — staleness flags on index drift; user CRUD over entries; facts carry provenance (which run asserted them).

**Required Tests:** CRUD + provenance; staleness flagging on file-hash drift; retrieval budget interaction; distillation golden tests.

**Acceptance Criteria:** Second session on a fixture project answers a conventions question without re-reading files (tool-call count asserted); memory panel lists/edits entries.

**Future Expansion:** Team-shared project memory with merge semantics.

---

## Phase 8 — Definition of Done
- [ ] External strategy plugin demo installs and runs; quarantine proven.
- [ ] Semantic recall demonstrates causal value on long-session fixtures.
- [ ] Planner swappable via config; LLM planner validated + fallback-safe.
- [ ] Worker-mode parity suite green; single-process mode untouched.
- [ ] Project memory inspectable, provenance-tracked, staleness-aware.

---

# PHASE 9 — UI/UX Professional Track (parallel, Week 1 onward)

Goal: a professional editor surface worthy of the backend — trustworthy review/rollback surfaces, first-class code presentation (file-type icons, syntax highlighting), and a proper multi-theme system. This is a **parallel frontend workstream**, not a sequential phase: R-905/R-903/R-904 have no backend dependencies and start Week 1; R-901/R-902/R-906 land as their backend counterparts (R-104, R-106, R-402/R-403) ship. Frontend lives in `public/` and `static/`.

---

### R-901 — Diff-Review Panel for ApprovalRequests

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 4d |
| **Dependencies** | R-104 (ApprovalRequest payload), R-904 (diff highlighting) |
| **Breaking Changes** | None (new UI surface) |
| **Affected Modules** | `public/` (new diff panel component), `static/`, WS message handlers |

**Problem Statement:** `ApprovalGate` (R-104) ships consent as a backend primitive, but the user currently has no readable surface to review what they are consenting to — a wall of raw payload is not informed consent. A gate nobody can read gets clicked through blindly, which defeats its purpose.

**Root Cause:** The original roadmap deliberately scoped UI out; the review correctly flags that R-104's trust value is inert without a review surface.

**Current Design:** Approval decisions (where surfaced at all) render as unformatted text; no per-file granularity.

**Target Design:** A diff-review panel that renders each `ApprovalRequest` as a per-file, side-by-side or unified diff (user-switchable) with syntax highlighting (R-904), file-type icons (R-903), added/removed line counts, and collapse/expand per file. Accept/reject at **both** batch and per-file granularity, mapping 1:1 to the gate's WS protocol. Keyboard shortcuts for accept/reject/next-file.

**Justification:** Informed consent requires readable diffs; this is the surface that makes R-104 real to the user.

**Benefits:** Users approve with confidence; per-file rejection avoids all-or-nothing decisions; review friction drops enough that `interactive` mode stays usable.

**Risks:** Very large diffs freeze the DOM — virtualized rendering + per-file lazy expand; payload/UI drift — a contract test pins the ApprovalRequest schema the panel consumes.

**Required Tests:** Component tests — batch and per-file accept/reject emit the exact WS frames R-104 expects; golden render of a 5-file mixed (add/modify/delete) request; virtualization keeps a 3k-line diff interactive.

**Acceptance Criteria:** Every ApprovalRequest renders as a readable per-file diff; per-file and batch decisions round-trip to the gate correctly in E2E.

**Future Expansion:** Inline comments on diff lines feeding back into the next agent iteration; checkpoint-diff viewing (R-902) reuses this panel.

---

### R-902 — One-Click Rollback UI

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 2/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-106 (rollback_run/rollback_file WS commands), R-901 (diff panel reuse) |
| **Breaking Changes** | None (new UI surface) |
| **Affected Modules** | `public/` (run history + rollback controls), `static/` |

**Problem Statement:** R-106 makes every agent edit reversible at the API level, but reversibility a user cannot see or reach is functionally absent. An undo that requires crafting a WS frame by hand protects nobody.

**Root Cause:** Same UI-out-of-scope decision as R-901.

**Current Design:** No run history surface; no undo affordance anywhere in the UI.

**Target Design:** A run-history strip/panel listing recent applied batches (run id, timestamp, touched files, status). Each entry offers **one-click "Rollback run"** and per-file "Rollback file", confirming with a checkpoint diff (rendered via R-901's panel) before executing. R-106's hash-conflict refusal renders as a clear, human-readable conflict report — never a silent failure. Rollback results (success/partial/refused) surface as toasts plus a persistent entry state.

**Justification:** Completes the trust loop: consent before the write (R-104/R-901), recovery after it (R-106/R-902).

**Benefits:** "Undo the agent's last edit" becomes a visible, obvious action — the table-stakes feature competing editors already have.

**Risks:** Users rolling back the wrong run — the confirmation diff and explicit touched-file list mitigate; stale history after retention sweeps (R-305) — history reflects live checkpoint availability.

**Required Tests:** E2E — apply a 3-file batch, one-click rollback restores bytes; per-file rollback leaves siblings; conflict refusal renders the report; swept checkpoints show as expired, not clickable.

**Acceptance Criteria:** Rollback reachable in ≤2 clicks from the main view; conflict refusals human-readable; E2E green.

**Future Expansion:** Named/pinned checkpoints surfaced as "save points"; timeline scrubbing across multiple runs.

---

### R-903 — File-Type Icon System (All Common Languages)

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 2/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-905 (theme tokens for icon colors) |
| **Breaking Changes** | None (visual upgrade) |
| **Affected Modules** | `public/` (file tree, tabs, mention chips, diff panel headers), `static/icons/` (new) |

**Problem Statement:** Files render with generic or no icons; at a glance nothing distinguishes `server.py` from `config.yaml` from `index.html`. Every professional editor signals file type instantly; its absence marks the product as a prototype.

**Root Cause:** Frontend built for function only; no asset pipeline for icons was ever added.

**Current Design:** Plain text file names (or a single generic document glyph) in tree, tabs, and mentions.

**Target Design:** A single `getFileIcon(path)` extension→icon mapping used **everywhere a filename renders** — file tree, editor tabs, `@mention` chips, diff panel headers (R-901), run-history touched-file lists (R-902). Coverage for the most common languages and formats at minimum: JavaScript, TypeScript (+JSX/TSX), Python, HTML, CSS/SCSS, JSON, YAML/TOML, Markdown, Java, C, C++, C#, Go, Rust, PHP, Ruby, SQL, Shell/Bash, Dockerfile, `.env`/config, images, and lock files — with a clean fallback glyph for unknown extensions. Delivered as an SVG sprite or icon-font (no per-icon HTTP requests); colors driven by theme tokens (R-905) so icons remain legible in every theme.

**Justification:** Highest visible-polish-per-effort item in the track; directly requested.

**Benefits:** Instant file-type recognition across the whole UI; consistent identity between tree, tabs, and diffs.

**Risks:** Icon sprawl/inconsistency — one mapping module is the only source of truth; licensing — use an open-licensed icon set (e.g. MIT-licensed dev-icon sets) documented in the repo.

**Required Tests:** Unit — mapping returns the right icon for every listed extension and the fallback for unknowns; visual regression snapshot of the file tree on a fixture project containing all covered types.

**Acceptance Criteria:** All listed languages/formats have distinct icons; identical icon for the same file everywhere it appears; fallback never renders broken.

**Future Expansion:** Per-folder icons (e.g. `tests/`, `node_modules/`); user-overridable icon packs.

---

### R-904 — Syntax Highlighting Everywhere Code Renders

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | R-905 (highlight palettes are theme tokens) |
| **Breaking Changes** | None (visual upgrade) |
| **Affected Modules** | `public/` (chat code blocks, editor/viewer, diff panel), `static/` |

**Problem Statement:** Code renders as monochrome text in chat responses, file views, and diffs. Line-level coloring is the baseline expectation of any code tool; without it, reading a 40-line generated function or a multi-file diff is materially slower and more error-prone.

**Root Cause:** No highlighting library was ever integrated; output was treated as plain text.

**Current Design:** Unstyled `<pre>`/plain text for all code surfaces.

**Target Design:** One highlighting engine (e.g. `highlight.js` or Shiki — chosen once, used everywhere) applied consistently to: (1) fenced code blocks in AI chat responses with language auto-detection + fence-tag override; (2) file content views; (3) the diff panel (R-901) with syntax coloring **layered under** add/remove backgrounds; (4) streaming AI output, highlighted incrementally without flicker. Language grammar coverage matches the R-903 icon list (JS/TS, Python, HTML, CSS, JSON, YAML, Markdown, Java, C/C++, C#, Go, Rust, PHP, Ruby, SQL, Shell, etc.). Highlight color palettes are defined as theme tokens (R-905) so every theme ships light- and dark-correct code colors. Line numbers on file views and diffs.

**Justification:** Directly requested ("line coloring"); largest single readability upgrade in the product.

**Benefits:** Faster code review in chat and diffs; professional presentation; consistent colors across every surface.

**Risks:** Highlighting large files blocks the main thread — highlight visible viewport lazily / use a worker; streaming re-highlight flicker — incremental highlighting of only the appended chunk.

**Required Tests:** Snapshot renders per language on fixture snippets (all covered grammars); streaming test — no flicker/detached nodes while tokens append; perf — 5k-line file highlights without blocking interaction; diff panel shows syntax + add/remove layers simultaneously.

**Acceptance Criteria:** All code surfaces highlighted with the same engine and palette; language coverage list green; streaming highlight stable.

**Future Expansion:** Semantic (symbol-aware) highlighting fed by R-205's SymbolIndex; bracket-pair colorization.

---

### R-905 — Multi-Theme System (Design Tokens + Live Switching)

| Field | Value |
|---|---|
| **Priority** | High |
| **Complexity** | 3/5 |
| **Time Estimate** | 3d |
| **Dependencies** | None (foundation item — build first) |
| **Breaking Changes** | Existing hard-coded colors migrated to tokens (visual-only) |
| **Affected Modules** | `static/` (token stylesheet, theme definitions), `public/` (theme switcher, persistence) |

**Problem Statement:** The UI ships a single hard-coded appearance. No dark/light choice, no user preference, and every color is scattered through the stylesheets — meaning any future visual work (icons, highlighting, diff colors) would hard-code against one palette and make theming impossible later. This is the foundation item the rest of the track builds on.

**Root Cause:** Styling grew ad hoc; no design-token layer was ever introduced.

**Current Design:** Fixed colors inline/scattered across CSS; no `prefers-color-scheme` handling.

**Target Design:** A design-token layer of CSS custom properties (`--bg-primary`, `--text-primary`, `--accent`, `--diff-add-bg`, `--syntax-keyword`, `--icon-*`, etc.) with **every** color in the app consuming tokens — zero hard-coded colors after migration (CI-lintable). Ship at minimum: dark (default), light, plus at least two variants (e.g. high-contrast and a popular editor palette such as monokai/solarized). Theme switching is instant (swap a `data-theme` attribute, no reload), respects `prefers-color-scheme` on first visit, and persists the user's choice (`localStorage`). Syntax palettes (R-904) and icon colors (R-903) are part of each theme definition, so switching restyles code and icons coherently. Themes defined as data (one file per theme) so adding a theme requires no component changes.

**Justification:** Directly requested ("multiple themes"); must land first because icons and highlighting consume its tokens — building them against hard-coded colors would create rework.

**Benefits:** Dark/light parity from day one; adding themes becomes a data-file exercise; all later UI work automatically theme-correct.

**Risks:** Migration misses hard-coded colors — a stylelint/CI grep forbidding raw hex/rgb outside token definitions; FOUC on load — theme attribute set synchronously before first paint.

**Required Tests:** CI lint — no raw color values outside theme files; switch test — toggling `data-theme` restyles code blocks, icons, and diffs with no reload; persistence across reload; `prefers-color-scheme` respected on first visit; contrast audit (WCAG AA) per shipped theme.

**Acceptance Criteria:** ≥4 themes shipped; live switch with persistence; zero hard-coded colors; AA contrast on all themes.

**Future Expansion:** User-defined custom themes (import/export JSON); per-project theme override.

---

### R-906 — Routing & Capacity Observability Panel

| Field | Value |
|---|---|
| **Priority** | Medium |
| **Complexity** | 2/5 |
| **Time Estimate** | 2d |
| **Dependencies** | R-402 (RoutingDecision), R-403 (CapacityModel) |
| **Breaking Changes** | None (new UI surface) |
| **Affected Modules** | `public/` (status/inspector panel), EventBus WS frames |

**Problem Statement:** When the system routes a request to a given tier/strategy or a circuit breaker trips, the user sees only the *consequence* (slow, degraded, or refused) with no explanation. "Why did it do that" currently has only a log-line answer, invisible to users.

**Root Cause:** RoutingDecision and CapacityModel were designed as internal records with no presentation path.

**Current Design:** No visibility; failures and degradations are silent or generic.

**Target Design:** A compact, collapsible status panel: current `RoutingDecision` per request (tier, strategy, reason — rendered from the structured record R-402 already produces), live `CapacityModel` state (per-provider load, breaker open/closed with reason and retry countdown), fed by existing EventBus events over the single WS adapter — **read-only presentation; no new backend logic**. Non-intrusive: a status chip that expands on click.

**Justification:** Trust also means explainability; this closes the review's "why did it do that" gap with UI, not log-diving.

**Benefits:** Degraded modes become understandable instead of alarming; support/debug conversations get a shared reference surface.

**Risks:** Information overload — collapsed-by-default chip with progressive disclosure; event spam re-renders — throttled updates.

**Required Tests:** Given a synthetic RoutingDecision/CapacityModel event stream, panel renders tier/strategy/reason and breaker states correctly; throttling keeps render count bounded under event bursts; panel absent/inert when features are disabled.

**Acceptance Criteria:** Routing reason and breaker state visible within one click during any run; zero new backend endpoints (EventBus only).

**Future Expansion:** Per-run cost/token telemetry in the same panel; exportable "run report".

---

## Phase 9 — Definition of Done
- [ ] Theme system live: ≥4 themes (dark, light, high-contrast, +1 variant), instant switch, persisted preference, zero hard-coded colors (CI-enforced), WCAG AA contrast.
- [ ] File-type icons render for all listed common languages in tree, tabs, mentions, and diff headers; unknown types fall back cleanly.
- [ ] Syntax highlighting live on chat code blocks, file views, diffs, and streaming output; palettes theme-aware; large-file perf test green.
- [ ] ApprovalRequest diff-review panel supports batch and per-file accept/reject, round-tripping correctly to ApprovalGate.
- [ ] One-click rollback (run and per-file) reachable in ≤2 clicks; conflict refusals render human-readable.
- [ ] Routing/capacity status panel answers "why did it do that" without log access.

---

# Dependency Graph

```
R-101 ─┐
R-103  ├─→ R-102 ─→ R-104 ─→ R-106 ─┐
       │                R-105 ──────┼─→ R-501 ─→ R-604, R-801, R-504
       │      └──→ R-201 ─→ R-202 ─→ R-203 ─→ R-304, R-602, R-503
       │                       ├──→ R-205
       │                       └──→ R-206 ─→ R-802
R-301 ─→ R-302 ─→ R-303, R-304, R-802
R-401 ─→ R-402, R-403 ─→ R-603
R-601 (independent after Phase 1)
Phase 7 requires Phases 1–3 complete.
Phase 5's R-504 requires R-105, R-501, R-106.
Phase 9 (UI/UX) runs in parallel from Week 1:
  R-905 (themes) ─→ R-903 (icons) · R-904 (highlighting) ─→ R-901 (diff panel)
  R-104 ─→ R-901 · R-106 ─→ R-902 (rollback UI) · R-402/R-403 ─→ R-906 (observability)
```

**Reading order for a new engineer:** Phase 1 items in order (R-101→R-106) → R-201/R-204/R-205 → R-301/R-302 → then by team assignment. Frontend engineers start Phase 9 in parallel from Week 1 (R-905 theme foundation → R-903/R-904 → R-901/R-902 as their backend items land).

**Totals:** 42 R-items across 9 phases · Critical: 6 · High: 16 · Medium: 15 · Low: 5 (Phase 8 items graded Low priority, high leverage; Phase 9 is a parallel frontend track).
