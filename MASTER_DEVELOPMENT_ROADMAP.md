# MASTER DEVELOPMENT ROADMAP — WebDev AI Editor

> **Scope:** Architectural refactoring of the Flask+WebSocket AI coding assistant (context, memory, chains, agents, sessions, state, scalability).
> **Out of scope:** AI providers/models internals, auth, billing, streaming transport, prompt wording.
> **Source of truth:** Every item below references verified evidence (file + line ranges) from the architectural review.
> **Numbering:** `R-<phase><nn>`. Complexity scale 1–5. Time estimates assume one senior engineer.

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

## Phase 1 — Definition of Done
- [ ] Concurrent chain start rejected with structured error (R-101 → R-105).
- [ ] Project switch leaves **zero** stale references (id()-asserted test).
- [ ] Model switch touches no private attributes.
- [ ] Delegate passes `str` prompts; provider contract test in CI.
- [ ] No file write occurs without ApprovalGate consent; failed runs write nothing.
- [ ] `ExecutionRegistry` tracks and cancels all three execution modes.
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

## Phase 2 — Definition of Done
- [ ] One `ContextEngine`; server inline block deleted; three call paths converge.
- [ ] `ContextBundle` hash-dedup live; map_reduce token reduction ≥40% on fixtures.
- [ ] `ContextBudget` governs every assembled prompt; overflow impossible in tests.
- [ ] `SafeReader` is the sole model-bound read path; `.env` provably redacted.
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

**Acceptance Criteria:** 100-turn session prompt stays within budget with summary present; hot path never awaits summarization.

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

**Target Design:** `RetentionPolicy` (keep last N runs per project + max age + max bytes) executed by a sweep on registry `finish()` and on startup. Snapshot creation fixed to record actual file hashes (prerequisite for R-601) or skipped entirely when resume is disabled.

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

**Required Tests:** Unit: exhaustiveness (every enum member has builder), tier→strategy mapping matrix. Parity: 30 recorded requests route identically pre/post.

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

**Acceptance Criteria:** ROLE_MAP deleted; startup fails fast on broken manifest; hot-reload test green.

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

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; shared contract suite green; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works; ROLE_MAP deleted.
- [ ] Agent iteration token cost flat; knowledge is a bundle view.
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
| **Dependencies** | R-302, R-304 |
| **Breaking Changes** | None (additive recall source) |
| **Affected Modules** | `memory/` |

**Problem Statement:** After R-304, memory is recency-tiered but has no *relevance* recall — a decision made 80 turns ago about architecture X is invisible unless recent.

**Target Design:** Three layers over the JSONL stream: working (R-302 window), episodic (per-run/task summaries, queryable by time/task), semantic (embedding index over turns+summaries; retrieval injected as a budgeted `ContextBundle` source). Retrieval is a ContextEngine source (R-201 seam), nothing else changes.

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

# Dependency Graph

```
R-101 ─┐
R-103  ├─→ R-102 ─→ R-104, R-105 ─→ R-501 ─→ R-604, R-801
       │      └──→ R-201 ─→ R-202 ─→ R-203 ─→ R-304, R-602, R-503
R-301 ─→ R-302 ─→ R-303, R-304, R-802
R-401 ─→ R-402, R-403 ─→ R-603
R-601 (independent after Phase 1)
Phase 7 requires Phases 1–3 complete.
```

















# MASTER DEVELOPMENT ROADMAP — WebDev AI Editor

> **Scope:** Architectural refactoring of the Flask+WebSocket AI coding assistant (context, memory, chains, agents, sessions, state, scalability).
> **Out of scope:** AI providers/models internals, auth, billing, streaming transport, prompt wording.
> **Source of truth:** Every item below references verified evidence (file + line ranges) from the architectural review.
> **Numbering:** `R-<phase><nn>`. Complexity scale 1–5. Time estimates assume one senior engineer.

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

## Phase 1 — Definition of Done
- [ ] Concurrent chain start rejected with structured error (R-101 → R-105).
- [ ] Project switch leaves **zero** stale references (id()-asserted test).
- [ ] Model switch touches no private attributes.
- [ ] Delegate passes `str` prompts; provider contract test in CI.
- [ ] No file write occurs without ApprovalGate consent; failed runs write nothing.
- [ ] `ExecutionRegistry` tracks and cancels all three execution modes.
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

## Phase 2 — Definition of Done
- [ ] One `ContextEngine`; server inline block deleted; three call paths converge.
- [ ] `ContextBundle` hash-dedup live; map_reduce token reduction ≥40% on fixtures.
- [ ] `ContextBudget` governs every assembled prompt; overflow impossible in tests.
- [ ] `SafeReader` is the sole model-bound read path; `.env` provably redacted.
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

**Acceptance Criteria:** 100-turn session prompt stays within budget with summary present; hot path never awaits summarization.

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

**Target Design:** `RetentionPolicy` (keep last N runs per project + max age + max bytes) executed by a sweep on registry `finish()` and on startup. Snapshot creation fixed to record actual file hashes (prerequisite for R-601) or skipped entirely when resume is disabled.

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

**Required Tests:** Unit: exhaustiveness (every enum member has builder), tier→strategy mapping matrix. Parity: 30 recorded requests route identically pre/post.

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

**Target Design:** `Runner` protocol: `run(request: RunRequest, ticket: RunTicket, events: EventSink) -> RunResult`. `RunRequest` carries mode, message, `ContextBundle`, memory window, policy. All four modes become `Runner` implementations; WS handler becomes: route → build request → `registry.execute(runner, request)` → stream events. Approval and cancellation flow through ticket/gate uniformly.

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

**Acceptance Criteria:** ROLE_MAP deleted; startup fails fast on broken manifest; hot-reload test green.

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

**Target Design:** Accumulator becomes a view over the run's `ContextBundle`: tool results register items (hash-deduped); per-iteration prompt = budget-admitted delta (new items verbatim, previously-sent items as one-line references) — the model's own conversation history preserves earlier content.

**Justification:** Directly multiplies agent-loop cost; also the last remaining private context store after Phase 2.

**Benefits:** Iteration cost flat instead of linear-growing; consistent with global budget/dedup; observable per-iteration token metrics.

**Risks:** Model losing track of referenced-not-repeated content — recent-k items always verbatim; reference format tested for recall on fixtures.

**Required Tests:** Unit: delta computation, reference rendering, recent-k floor. Regression: 6-iteration fixture — per-iteration tokens flat within 15%; task success parity.

**Acceptance Criteria:** No full-content re-injection after first send; token flatness test green; `_files_read` raw store removed.

**Future Expansion:** Cross-run knowledge reuse through project memory (R-805).

---

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; shared contract suite green; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works; ROLE_MAP deleted.
- [ ] Agent iteration token cost flat; knowledge is a bundle view.
- [ ] Per-mode parity E2E recorded and green.


















# MASTER DEVELOPMENT ROADMAP — WebDev AI Editor

> **Prepared by:** Principal AI Systems Architect review
> **Scope:** Context Management · Memory · Task Flow · Agent Orchestration · Chain Execution · Session Lifecycle · Planning · State Management · Scalability · Maintainability · Extensibility
> **Out of scope:** AI provider/model internals, auth, billing, streaming transport, prompt wording.
> **Structure:** 8 phases, items R-101 → R-805. Every item carries priority, complexity (1–5), estimate, dependencies, breaking-change flag, affected modules, problem, root cause, current design, target design, justification, benefits, risks, required tests, acceptance criteria, and future expansion. Each phase closes with a Definition of Done.

---

## Global Architecture Target

```
                          ┌─────────────────────────────────────────────┐
                          │                 AppContext                  │
                          │        (composition root, no globals)       │
                          └───────┬───────────────┬─────────────┬───────┘
                                  │               │             │
                    ┌─────────────▼──┐   ┌────────▼───────┐  ┌──▼──────────────┐
                    │ ProjectHandle  │   │ ExecutionReg.  │  │  EventBus       │
                    │ (path, index,  │   │ RunTicket per  │  │  typed events,  │
                    │  SafeReader)   │   │ live run       │  │  per-run FIFO   │
                    └───────┬────────┘   └────────┬───────┘  └──┬──────────────┘
                            │                     │             │
              ┌─────────────▼───────┐    ┌────────▼───────────┐ │  ┌───────────────┐
              │   ContextEngine     │    │  Runner protocol   │ │  │ WS Adapter    │
              │  Mention/Keyword/   │    │ Direct │ Chain     │ └─▶│ (only place   │
              │  Structure/History  │    │ Agent  │ Delegate  │    │  ws.send is   │
              │  sources → Bundle   │    └────────┬───────────┘    │  allowed)     │
              │  → ContextBudget    │             │                └───────────────┘
              └─────────────┬───────┘    ┌────────▼───────────┐
                            │            │  ApprovalGate      │
              ┌─────────────▼───────┐    │ auto/interactive/  │
              │ ConversationMemory  │    │ deny               │
              │ JSONL store + meta  │    └────────────────────┘
              │ window() + summary  │
              └─────────────────────┘
```

**Key shifts:**
1. Module-level mutable state → `AppContext` + per-connection `SessionContext`.
2. Inline 200-line context block in `server.py` → `ContextEngine` with pluggable sources.
3. Silent auto-apply in `finally` → explicit `ApprovalGate` with three modes.
4. One dead `_active_chain_run` guard → `ExecutionRegistry` with cancellable `RunTicket`s.
5. Four ad-hoc dispatch paths → one `Runner` protocol.
6. Monolithic JSON session files (O(n²) append) → JSONL + meta sidecar.
7. Two conflicting strategy vocabularies → `RoutingTier` × `ExecutionStrategy` with a `STRATEGY_TABLE`.
8. Secrets (`.env`) readable by context → `SafeReader` boundary.

---

# PHASE 1 — Stop the Bleeding: Correctness & Safety (Week 1–2)

Goal: eliminate defects that corrupt state, violate contracts, or apply changes without consent. No new features.

---

## R-101 — Remove the Dead `_active_chain_run` Guard; Introduce ActiveRunHolder

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none · **Affected:** `server.py`
- **Problem:** `_active_chain_run` (server.py L82) is set at L403 but the guard at L470 checks it *after* the branch that would have needed it; it can never block a concurrent run. Two chains can interleave file writes.
- **Root cause:** Guard added post-hoc without tracing the dispatch order; no test could catch it because there are no tests.
- **Current design:** Module-level `Optional[str]` flag mutated from two handlers.
- **Target design:** `ActiveRunHolder` — tiny class with `acquire(run_id) -> bool`, `release(run_id)`, `current()`; injected, lock-protected; checked *before* dispatch. (Superseded by R-105's registry later; holder is the minimal safe stopgap.)
- **Justification:** Cheapest possible fix for a real interleaving hazard; unblocks everything else.
- **Benefits:** Deterministic single-run invariant; testable seam.
- **Risks:** Low; behavior change only when a second run is attempted (now correctly rejected).
- **Required tests:** unit — acquire/release/double-acquire; integration — second WS `run_chain` while first active gets `busy` frame.
- **Acceptance criteria:** guard flag deleted; concurrent-run integration test green; no module-level run state remains for chains.
- **Future expansion:** replaced by ExecutionRegistry (R-105) which allows N concurrent runs with per-project leases.

## R-102 — AppContext Composition Root; Kill Stale References After Project Switch

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101 · **Affected:** `server.py`, `chain/bridge.py`, `actions/*`
- **Problem:** `api_switch_project` (server.py L463–504) rebuilds `file_manager`/`context_builder` but five consumers captured the old objects at import/init time; after a switch they silently operate on the previous project.
- **Root cause:** Object graph wired at module import; identity, not indirection, shared.
- **Current design:** Globals reassigned; consumers hold stale pointers.
- **Target design:** `AppContext` built in `main()`; holds a mutable `ProjectHandle` (path, FileManager, SafeReader, index slot). Consumers receive `ctx` and resolve `ctx.project.fm` at call time, never at construction.
- **Justification:** Every stale-state bug in the review traces to this wiring pattern.
- **Benefits:** Project switch is one atomic pointer swap; test isolation becomes trivial (fresh ctx per test).
- **Risks:** Wide but mechanical diff; mitigated by phased consumer migration (T-005..T-008).
- **Required tests:** switch-project E2E: create file in A, switch to B, mention resolution must see only B; unit — handle swap atomicity.
- **Acceptance criteria:** zero module-level references to FileManager/ContextBuilder; switch E2E green; `switch_model`'s private-attribute pokes (L435–450) deleted.
- **Future expansion:** SessionContext (R-701) nests under AppContext for per-connection state.

## R-103 — Fix the Delegate Provider Contract Violation

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none · **Affected:** `chain/delegate.py`, `providers/base.py`
- **Problem:** `delegate.py` L260/289/327 passes `list[Message]` into `send(prompt: str, ...)` (contract at providers/base.py L254). Works only because one provider duck-types; any conforming provider crashes or mis-serializes.
- **Root cause:** Contract never enforced; no type checking in CI.
- **Current design:** Three call sites hand structured history to a string parameter.
- **Target design:** `_to_prompt_history(messages) -> str` helper (explicit rendering with role tags); all three sites converted; `ProviderContractTest` mixin that every provider test class inherits; mypy gate on `chain/` and `providers/`.
- **Justification:** Latent crash on provider swap; blocks R-501 (runners must trust the contract).
- **Benefits:** Providers become genuinely interchangeable.
- **Risks:** Prompt rendering slightly changes delegate outputs; snapshot the new rendering as golden.
- **Required tests:** contract mixin (send receives str, kwargs schema); delegate integration against FakeProvider.
- **Acceptance criteria:** mypy clean on both packages; contract suite green for all registered providers.
- **Future expansion:** contract becomes the seam for streaming/tool-call capabilities negotiation.

## R-104 — ApprovalGate: No More Silent Auto-Apply in `finally`

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Yes (behavioral — and that is the point)
- **Dependencies:** R-102 · **Affected:** `chain/bridge.py`, `server.py`, agent flow
- **Problem:** ChainBridge applies generated file edits inside `finally` (bridge.py L264–276) even when the user set `auto_execute: false`; failures mid-chain still flush partial writes. Consent is fiction.
- **Root cause:** Apply logic placed in cleanup path "so results are never lost"; config flag consulted in one path but not the cleanup.
- **Current design:** `finally: self._apply_pending()` unconditionally.
- **Target design:** `ApprovalGate` service with modes `auto | interactive | deny`; every write proposal becomes an `ApprovalRequest` (diff, paths, run_id); `interactive` emits a WS frame and blocks on user verdict with timeout→deny; `finally` may only *stage*, never apply.
- **Justification:** Applying edits without consent is the most trust-destroying defect in the system.
- **Benefits:** Auditable consent trail; one gate serves chains, agents, delegate alike.
- **Risks:** Users accustomed to silent apply see a new prompt — document loudly in changelog.
- **Required tests:** E2E matrix (auto/interactive-accept/interactive-reject/deny × chain/agent); crash-mid-chain leaves zero partial writes.
- **Acceptance criteria:** no `apply` call reachable from any `finally`; `auto_execute: false` provably blocks writes; gate audit log records every verdict.
- **Future expansion:** per-path policies (e.g. `tests/**` auto, `src/**` interactive).

## R-105 — ExecutionRegistry + RunTicket (Cancellation That Works)

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101, R-102 · **Affected:** `server.py`, `chain/executor.py`, `chain/delegate.py`
- **Problem:** There is no way to cancel a running chain/agent; the only "control" was the dead guard (R-101). Long delegate loops run to completion even after the client disconnects.
- **Root cause:** Runs are bare function calls with no identity or control surface.
- **Current design:** Fire-and-forget dispatch; WS disconnect orphanes the work.
- **Target design:** `ExecutionRegistry` maps `run_id -> RunTicket`; ticket exposes `cancel()`, `is_cancelled`, `mode` (chain/agent/delegate); executors poll `ticket.is_cancelled` at step boundaries; delegate loop checks at each iteration checkpoint; WS gains `list_runs` / `cancel_run`.
- **Justification:** Prerequisite for parallelism (R-603), workers (R-804), and honest UX.
- **Benefits:** Users can stop runaway loops; registry is the single source of "what is executing".
- **Risks:** Cancellation checkpoints must be placed at every loop head — enforce via review checklist.
- **Required tests:** cancel mid-chain stops before next step; cancel delegate mid-iteration; registry survives WS reconnect; `list_runs` reflects reality.
- **Acceptance criteria:** ActiveRunHolder deleted; every dispatch path allocates a ticket; cancel E2E green for all three modes.
- **Future expansion:** tickets carry priority/lease metadata for the worker pool (R-804).

---

## Phase 1 — Definition of Done
- [ ] No module-level mutable run/project state in `server.py`.
- [ ] Project switch E2E green; stale-reference consumers migrated.
- [ ] Provider contract enforced by mypy + shared test mixin.
- [ ] All writes flow through ApprovalGate; `auto_execute: false` blocks writes in every mode.
- [ ] Every run has a ticket; cancellation works for chain, agent, and delegate.
- [ ] pytest bootstrap + FakeProvider fixture exist and run in CI-equivalent script.

---

# PHASE 2 — Context Engine (Week 3–4)

Goal: extract the inline 200-line context block into a real subsystem with deduplication, budgeting, and a secret boundary.

---

## R-201 — Extract ContextEngine with Pluggable Sources

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102 · **Affected:** `server.py` (L606–758), new `context/` package
- **Problem:** Context assembly is a 200-line inline block in the WS handler mixing mention parsing, keyword scans, directory listings, and history slicing; it re-scans the tree per message and contains the lying constant `MAX_MENTIONED = 100  # حد أقصى 10 ملفات`.
- **Root cause:** Feature accretion in the handler; no abstraction ever introduced.
- **Current design:** One block, three duplicated file-reading paths, per-message `rglob`.
- **Target design:** `ContextEngine.gather(request) -> ContextBundle` orchestrating `ContextSource` implementations: `MentionSource`, `KeywordSource`, `StructureSource`, `HistorySource`. Each source declares a priority tier and yields `ContextItem`s. Single tree scan per request, cached.
- **Justification:** The block is the single largest maintainability liability in the codebase.
- **Benefits:** Each source unit-testable; new sources (index, memory) plug in without touching the handler.
- **Risks:** Behavior drift vs. legacy block — pin legacy output as goldens first (T-017).
- **Required tests:** goldens for 6 representative messages match legacy output; per-source units; one-scan-per-request assertion.
- **Acceptance criteria:** inline block deleted; handler calls `engine.gather()`; lying constant fixed with the real limit; goldens green.
- **Future expansion:** ProjectIndex source (R-702), semantic memory source (R-802), plugin sources (R-801).

## R-202 — ContextBundle: Hash-Dedup + Provenance

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-201 · **Affected:** `context/`, `chain/executor.py` (map_reduce)
- **Problem:** The same file content can be injected 2–3× per prompt (mention + keyword + chain-step prefetch); map_reduce steps duplicate wholesale.
- **Root cause:** No shared container; each path reads and concatenates independently.
- **Current design:** Ad-hoc string concatenation.
- **Target design:** `ContextBundle` keyed by `sha256(path + content_hash)`; second insertion of identical content becomes a reference note, not a copy. Each item carries provenance (`source`, `reason`, `tier`).
- **Justification:** Direct token waste; measured ≥40% duplicate content in map_reduce prompts.
- **Benefits:** Smaller prompts, explainable context ("why is this file here?").
- **Risks:** Reference notes must be understandable to the model — golden-test the rendering.
- **Required tests:** dedup unit (same file via two sources → one body); map_reduce prompt size regression ≥40% smaller on fixture.
- **Acceptance criteria:** no identical content body appears twice in any generated prompt; provenance visible in debug dump.
- **Future expansion:** bundle diffing for delta prompts (R-503).

## R-203 — ContextBudget with Priority Tiers

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202 · **Affected:** `context/`, 3 files with hardcoded char limits
- **Problem:** Truncation is by raw character count at three inconsistent hardcoded limits; a critical mentioned file can be cut while boilerplate directory listing survives.
- **Root cause:** No notion of importance; limits added locally as each overflow was hit.
- **Current design:** `content[:N]` at three sites with three different N.
- **Target design:** `ContextBudget(token_limit)` packs items by tier: `must_have` (explicit mentions) → `high` (active file, error traces) → `normal` (keyword hits) → `opportunistic` (structure, memory). Within tier: score order. Overflow drops opportunistic first; must_have overflow triggers per-item summarization rather than truncation.
- **Justification:** Predictable, importance-ordered context is the core promise of the product.
- **Benefits:** Mentions never silently vanish; budget is one config knob.
- **Risks:** Token estimation accuracy — use provider tokenizer where available, chars/4 fallback.
- **Required tests:** property test — must_have never dropped while opportunistic present; overflow-summarization unit.
- **Acceptance criteria:** all three char limits deleted; budget applied in every prompt path.
- **Future expansion:** per-model budget profiles; adaptive budget from CapacityModel (R-403).

## R-204 — SafeReader: The Secret Boundary

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral (intended)
- **Dependencies:** R-102 · **Affected:** file reading paths, `_TEXT_EXTENSIONS` (L333–344)
- **Problem:** `.env` is listed in `_TEXT_EXTENSIONS`; keyword scan or mention can inject live API keys into prompts sent to third-party providers.
- **Root cause:** Extension list built for "what is text", not "what is safe".
- **Current design:** Any text-extension file is readable by every context path.
- **Target design:** `SafeReader` wraps all context-bound reads; denylist (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`) + content sniff for high-entropy assignments; denied reads return a redaction stub `[REDACTED: secret file]`; explicit user override requires per-file confirmation.
- **Justification:** Secret exfiltration to model providers is a security incident, not a bug.
- **Benefits:** One auditable choke point; CI can grep that no read bypasses it.
- **Risks:** False positives on entropy sniff — stub explains and offers override.
- **Required tests:** `.env` mention → redaction stub; entropy sniff unit; CI grep — no `open(`/`read_text` on context paths outside SafeReader.
- **Acceptance criteria:** `.env` removed from `_TEXT_EXTENSIONS`; all context reads routed through SafeReader; redaction E2E green.
- **Future expansion:** org-level policy packs; secret-scan report command.

---

## Phase 2 — Definition of Done
- [ ] Inline context block deleted from `server.py`; goldens prove parity.
- [ ] No duplicate content bodies in any prompt; provenance recorded.
- [ ] Char-limit truncation replaced by tiered token budget everywhere.
- [ ] Secrets unreachable by any context path; CI guard in place.

---

# PHASE 3 — Memory & Session Lifecycle (Week 5–6)

Goal: replace monolithic JSON sessions with an append-friendly store, give conversation memory a real API, and bind sessions to projects.

---

## R-301 — JSONL Session Store + Meta Sidecar

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Storage format (migration provided)
- **Dependencies:** none · **Affected:** session persistence module
- **Problem:** Each `append_message` deserializes the whole session JSON, appends, and rewrites the file — O(n²) over a conversation; long sessions visibly lag; a crash mid-rewrite corrupts the whole session.
- **Root cause:** "One JSON file per session" chosen for simplicity; growth never revisited.
- **Current design:** `json.load → list.append → json.dump` per message.
- **Target design:** `sessions/<id>.jsonl` — one message per line, O(1) append with `flush+fsync` option; `sessions/<id>.meta.json` sidecar (title, project binding, counts, summary refs) rewritten only on meta change; tail-read for recent window.
- **Justification:** Directly measurable latency and a real corruption vector.
- **Benefits:** p95 append <5ms at 1k messages; crash loses at most one line; streaming-friendly.
- **Risks:** Partial trailing line after crash — reader skips malformed final line and logs.
- **Required tests:** benchmark (1k appends p95 <5ms); torn-write recovery; migration round-trip fidelity.
- **Acceptance criteria:** all session I/O on JSONL; migration script converts existing sessions losslessly; corrupted-tail recovery test green.
- **Future expansion:** segment rotation + compaction; remote object-store backend.

## R-302 — ConversationMemory Facade

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** R-301 · **Affected:** all history consumers (3 sites)
- **Problem:** Three call sites slice raw message lists with different ad-hoc rules (`[-10:]`, `[-6:]`, full history), producing inconsistent model views of the same conversation.
- **Root cause:** No owner for "what does the model get to remember".
- **Current design:** Raw list slicing at each consumer.
- **Target design:** `ConversationMemory` owning the store; API: `append(msg)`, `window(policy) -> list[Message]`, `summary()`, `search(q)` (stub until R-802). All consumers migrate to `window()`.
- **Justification:** One memory policy instead of three accidental ones.
- **Benefits:** Windowing rules become config; consumers stop knowing storage shape.
- **Risks:** Subtle behavior change at consumers — capture current slices as goldens first.
- **Required tests:** window policy units; consumer goldens; append/window integration on JSONL.
- **Acceptance criteria:** zero raw-slice history access outside ConversationMemory.
- **Future expansion:** layered memory (R-802) slots behind the same facade.

## R-303 — Session ↔ Project Binding

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral (guarded)
- **Dependencies:** R-301, R-102 · **Affected:** session meta, switch handlers
- **Problem:** A session started on project A continues seamlessly after switching to project B; history references files that no longer exist in scope, and the model confidently hallucinates about the wrong codebase.
- **Root cause:** Sessions and projects are unrelated concepts in the code.
- **Current design:** No linkage whatsoever.
- **Target design:** meta sidecar stores `project_path` + `project_fingerprint`; on switch, mismatch triggers policy: `warn` (banner injected into context) / `fork` (new session pre-linked to B) / `block`; default `warn_only: true` in config.
- **Justification:** Cross-project contamination silently degrades answer quality.
- **Benefits:** Model always told which project the history belongs to.
- **Risks:** Users who intentionally cross projects — warn (not block) default preserves their flow.
- **Required tests:** switch-mid-session E2E per policy; fingerprint mismatch unit.
- **Acceptance criteria:** every new session records binding; mismatch policy enforced; config documented.
- **Future expansion:** per-project session listing UI; auto-fork suggestion.

## R-304 — Tiered Windowing + Async Summarization

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-302, R-203 · **Affected:** ConversationMemory
- **Problem:** Long conversations either overflow the prompt or lose everything before the last N messages; no middle ground.
- **Root cause:** Window = fixed slice; no summarization machinery.
- **Current design:** Hard cutoff; older turns simply vanish.
- **Target design:** three tiers: verbatim recent window → rolling summary of the middle band (produced asynchronously off the hot path, stored in meta) → drop. `window()` returns `[summary_msg] + recent`. Summaries budgeted via ContextBudget as `high` tier.
- **Justification:** Conversation continuity is a core UX expectation for an AI pair-programmer.
- **Benefits:** 100-turn sessions stay coherent within budget.
- **Risks:** Summary drift — include turn-range provenance in the summary block; regenerate on demand.
- **Required tests:** long-session simulation (100 turns) stays under budget and retains a fact from turn 5; async summarizer failure degrades to plain cutoff.
- **Acceptance criteria:** summarization runs off hot path; degradation path tested; fact-retention test green.
- **Future expansion:** semantic retrieval replaces middle band (R-802).

## R-305 — Truthful Snapshots + Retention GC

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** R-301 · **Affected:** ProjectSnapshot (L226–235), session store
- **Problem:** `ProjectSnapshot` records empty file-hash maps (L226–235) — resume validation (R-601) would always pass vacuously; sessions accumulate forever (43 were even committed to git).
- **Root cause:** Snapshot hashing stubbed and forgotten; no retention policy ever written.
- **Current design:** Empty hashes; unbounded session directory.
- **Target design:** snapshot computes real content hashes for files touched by the run; `RetentionPolicy` (max age / max count / pinned) with GC pass on startup and daily; sessions directory gitignored.
- **Justification:** Vacuous validation is worse than none; disk and repo hygiene.
- **Benefits:** Resume can actually refuse on drift; bounded storage.
- **Risks:** GC deleting a wanted session — pinning + dry-run log first release.
- **Required tests:** hash correctness unit; GC policy matrix; pinned survives GC.
- **Acceptance criteria:** no empty hash maps in new snapshots; GC runs with logs; `.gitignore` covers sessions.
- **Future expansion:** export/archive command before GC.

---

## Phase 3 — Definition of Done
- [ ] All sessions on JSONL + meta; migration complete; O(1) append verified.
- [ ] Single memory facade; zero raw history slicing at consumers.
- [ ] Sessions bound to projects; mismatch policy live.
- [ ] 100-turn session coherent within budget; summarizer off hot path.
- [ ] Real snapshot hashes; retention GC active; sessions out of git.

---

# PHASE 4 — Routing & Planning Honesty (Week 7–8)

Goal: one strategy vocabulary, explainable routing decisions, and a capacity model that tells the truth.

---

## R-401 — Unify the Two Strategy Vocabularies

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** none · **Affected:** orchestrator (6 strategies), router (4 strategies)
- **Problem:** The orchestrator speaks 6 strategy names, the router speaks 4; the mapping between them lives in developers' heads; two of the orchestrator strategies silently collapse into the same router path.
- **Root cause:** Two modules evolved vocabularies independently; no shared type.
- **Current design:** Free strings compared with `if/elif` ladders in both modules.
- **Target design:** two orthogonal enums — `RoutingTier` (which model class: fast/balanced/heavy/delegate) × `ExecutionStrategy` (how: direct/chain/agent/delegate) — joined by an explicit `STRATEGY_TABLE: dict[tuple[RoutingTier, ExecutionStrategy], StrategySpec]` registry; `assert_never` on unhandled combinations.
- **Justification:** Vocabulary drift is already producing silent mis-routing.
- **Benefits:** Exhaustiveness checked by mypy; table is documentation.
- **Risks:** Mapping decisions must be made explicit — capture current behavior first (T-034 records 30 real decisions).
- **Required tests:** table completeness (every enum pair resolved or explicitly rejected); goldens — 30 recorded decisions reproduce identically.
- **Acceptance criteria:** zero free-string strategy comparisons; both modules import the shared enums.
- **Future expansion:** plugin strategies register table rows (R-801).

## R-402 — Explainable Routing: RoutingDecision Record

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-401 · **Affected:** router, planner
- **Problem:** Routing outcomes are unexplainable; thresholds are magic numbers inline; when routing misbehaves nobody can say why without a debugger.
- **Root cause:** Decision logic returns only the answer, never the reasoning.
- **Current design:** Opaque return value from nested conditionals with inline constants.
- **Target design:** `RoutingDecision` dataclass (tier, strategy, score breakdown, thresholds applied, matched signals, config version) attached to the run and emitted as a `RoutingDecided` event; thresholds move to config with schema validation; property test — increasing task complexity never decreases the routed tier (monotonicity).
- **Justification:** Debuggability of the planner is a precondition for trusting automation.
- **Benefits:** Every run answers "why this model/strategy?"; thresholds tunable without deploys.
- **Risks:** none material — additive.
- **Required tests:** decision record completeness; monotonicity property; config schema rejection of nonsense thresholds.
- **Acceptance criteria:** all routing paths produce a decision record; magic numbers gone from code.
- **Future expansion:** decision log feeds offline tuning; LLM planner (R-803) emits the same record shape.

## R-403 — Honest CapacityModel + Circuit Breaker

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-401 · **Affected:** provider pool, router
- **Problem:** `reset_failures()` exists but is never called — a provider marked failing stays failing until process restart; capacity math hardcodes `MIN_ACCOUNTS` assumptions that no longer hold; budget numbers reported to the UI are fictional.
- **Root cause:** Failure tracking half-built; capacity constants copied from an earlier deployment shape.
- **Current design:** Sticky failure flags; hardcoded pool arithmetic.
- **Target design:** per-provider circuit breaker (closed → open on N consecutive failures → half-open probe after cooldown → closed on success); `CapacityModel` computes availability from live pool state, no `MIN_ACCOUNTS`; UI budget numbers derived from the model, flagged `estimated` where uncertain.
- **Justification:** Self-healing beats restart-to-heal; lying capacity numbers erode trust.
- **Benefits:** Transient provider outages recover automatically; honest UX.
- **Risks:** Half-open probe hammering a dead provider — exponential cooldown cap.
- **Required tests:** breaker state-machine unit (all transitions); recovery integration with FakeProvider scripted failures; capacity math property tests.
- **Acceptance criteria:** `reset_failures()` deleted (breaker owns lifecycle); `MIN_ACCOUNTS` removed; breaker metrics visible in `list_runs`/status.
- **Future expansion:** adaptive rate limiting per breaker health.

---

## Phase 4 — Definition of Done
- [ ] One shared strategy type system; table-driven dispatch; exhaustiveness enforced.
- [ ] Every routing outcome carries a full decision record; thresholds in config.
- [ ] Circuit breaker live for all providers; sticky-failure code deleted.
- [ ] 30-decision golden corpus green after refactor.

---

# PHASE 5 — Agent Orchestration (Week 9–10)

Goal: one Runner protocol for all four execution modes, a declarative agent fleet, and knowledge accumulation that stops re-paying for itself.

---

## R-501 — Runner Protocol: One Dispatch Path

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102, R-103, R-104, R-105 · **Affected:** `server.py` dispatch, `chain/*`
- **Problem:** Four execution modes (direct, chain, agent, delegate) are four hand-rolled dispatch paths in the WS handler with divergent error handling, approval behavior, and event emission; the agent path even *polls* the WS for results (server.py L920–965) as a workaround.
- **Root cause:** Each mode bolted on independently; no shared abstraction.
- **Current design:** if/elif ladder; copy-pasted error frames; agent polling loop.
- **Target design:** `Runner` protocol — `run(request, ticket, ctx) -> RunResult` with events via EventBus; `DirectRunner`, `ChainRunner`, `AgentRunner`, `DelegateRunner`; shared contract test harness every runner must pass (cancellation honored, approval gated, events well-formed); dispatch = `RUNNERS[strategy].run(...)`. Rollout behind `LEGACY_DISPATCH` flag, then flag deleted.
- **Justification:** The dispatch ladder is where every cross-cutting concern is currently inconsistent.
- **Benefits:** New modes = new runner class; polling loop deleted; uniform semantics.
- **Risks:** Behavioral parity — per-mode E2E recordings before/after.
- **Required tests:** contract harness (incl. `EchoRunner` reference impl); per-mode parity E2E; cancellation matrix.
- **Acceptance criteria:** polling loop (L920–965) deleted; single dispatch line; all runners pass contract suite; flag removed.
- **Future expansion:** runners execute in worker pool (R-804); plugin runners (R-801).

## R-502 — Declarative Agent Manifest

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-501 · **Affected:** ROLE_MAP (21 hardcoded Arabic-named agent paths)
- **Problem:** `ROLE_MAP` hardcodes 21 agent definitions with Arabic-named file paths inline in code; adding an agent means editing source; typos surface at runtime.
- **Root cause:** Fastest path taken at the time; never externalized.
- **Current design:** dict literal in code.
- **Target design:** `agents/manifest.yaml` — id, display name, prompt path, capabilities, default tier; loaded with schema validation at startup, mtime-based hot reload; `ROLE_MAP` deleted.
- **Justification:** Fleet configuration is data, not code.
- **Benefits:** Non-developers can edit the fleet; validation catches broken entries at load, not mid-run.
- **Risks:** Hot reload racing an active run — reload swaps the registry pointer atomically; running agents keep their snapshot.
- **Required tests:** schema validation (bad manifest rejected with line numbers); hot-reload integration; parity — all 21 legacy agents resolve identically.
- **Acceptance criteria:** ROLE_MAP gone; manifest is single source; reload works without restart.
- **Future expansion:** per-project manifest overlays; marketplace-style agent packs.

## R-503 — Knowledge Accumulator: Dedup + Delta Prompts

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202, R-203 · **Affected:** agent loop knowledge handling
- **Problem:** `KnowledgeAccumulator` re-injects the *entire* accumulated knowledge blob into every iteration's prompt; token cost grows quadratically with iterations; identical findings are appended repeatedly.
- **Root cause:** Accumulator is a string concatenator, not a set.
- **Current design:** `knowledge += new_finding; prompt = base + knowledge` every loop.
- **Target design:** knowledge becomes a `ContextBundle` view — findings hash-deduped on insert; per-iteration prompt carries only the delta since last iteration plus a budgeted summary of the stable core; full knowledge available on demand via reference.
- **Justification:** Quadratic token burn on the most expensive execution mode.
- **Benefits:** Iteration cost flat within 15%; dedup kills repeated findings.
- **Risks:** Model losing sight of early findings — stable-core summary tier guards this; fact-retention test.
- **Required tests:** token-cost curve test (8 iterations, flat within 15%); dedup unit; retention of iteration-1 finding at iteration 8.
- **Acceptance criteria:** no full re-injection; cost curve test green; knowledge visible in bundle debug dump.
- **Future expansion:** knowledge persisted per project (R-805).

---

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; shared contract suite green; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works; ROLE_MAP deleted.
- [ ] Agent iteration token cost flat; knowledge is a bundle view.
- [ ] Per-mode parity E2E recorded and green.

---

# PHASE 6 — Chain Engine Maturity (Week 10–11)

Goal: make the executor's promises real — resume, context policy, parallelism — and give the system a nervous system.

---

## R-601 — Wire Crash Resume or Delete It

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-105, R-305 · **Affected:** `chain/executor.py` (L459–480)
- **Problem:** `can_resume()` / `load_state()` (executor.py L459–480) have **zero callers** — the entire resume machinery is dead code that ships, rots, and misleads readers into believing the feature exists.
- **Root cause:** Machinery built speculatively; the WS entry point to invoke it was never written.
- **Current design:** State is saved per step, but no code path ever loads it after a crash.
- **Target design:** startup scan finds interrupted runs (ticket persisted, no terminal state); WS gains `resume_run` / `discard_run`; resume validates the R-305 real snapshot hashes and **refuses on hash mismatch** with an explicit drift report. If the team decides against resume, the alternative is compliant too: delete L459–480 and the per-step state writes entirely — but pick one; dead machinery is not an option.
- **Justification:** Dead code with persistence side effects is the worst kind — it costs I/O every run and delivers nothing.
- **Benefits:** Long chains survive process restarts; or, in the delete branch, less code and less I/O.
- **Risks:** Resuming against a drifted tree corrupts outputs — hash refusal is mandatory, not optional.
- **Required tests:** kill-after-step-2-of-5 → resume completes steps 3–5 exactly once; hash-mismatch refusal test; discard cleans state.
- **Acceptance criteria:** resume reachable from WS (or machinery fully deleted); kill/resume E2E green; drift refusal green.
- **Future expansion:** resumable runs migrate naturally onto worker leases (R-804).

## R-602 — Enforce ChainStep Context Policy

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202, R-203 · **Affected:** `chain/executor.py` prompt build
- **Problem:** ChainStep declares a `context_policy` field but `build_prompt` ignores it — every step receives the full accumulated context regardless; later steps in long chains pay for everything earlier steps produced.
- **Root cause:** Field added to the schema before the rendering code was written; never finished.
- **Current design:** Policy parsed, stored, never read.
- **Target design:** three render modes honored in `build_prompt`: `full` (bundle as-is), `summary` (budgeted summaries of prior step outputs), `minimal` (only declared inputs of this step). Default per chain type; overridable per step.
- **Justification:** A declared-but-ignored config field is a silent lie to chain authors.
- **Benefits:** ≥50% prompt reduction at step 5 of a 5-step fixture chain (golden-verified); chain authors regain control.
- **Risks:** `minimal` starving a step that implicitly relied on ambient context — parity goldens catch this before rollout.
- **Required tests:** per-mode render goldens; step-5 prompt size ≥50% smaller under `summary` vs legacy; declared-inputs completeness check for `minimal`.
- **Acceptance criteria:** policy field actually changes rendered prompts; size regression test green; docs describe the three modes.
- **Future expansion:** automatic policy suggestion from step dependency analysis.

## R-603 — Bounded Parallel Step Execution

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-105, R-403, R-602 · **Affected:** `chain/executor.py` (L204–206)
- **Problem:** The scheduler computes the full ready set, then executes `ready[0]` only (L204–206) — strictly sequential — while config advertises `max_parallel_steps`. Another lying knob: map steps over 8 files run 8× slower than they need to.
- **Root cause:** Parallel loop stubbed with the sequential base case; never upgraded.
- **Current design:** `ready = compute_ready(); run(ready[0])`.
- **Target design:** `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)` executes the whole ready set; results merge through a guarded `apply_step_result()` (single lock — state mutation stays serialized); each parallel task polls its RunTicket cancellation checkpoint; provider concurrency capped by CapacityModel (R-403).
- **Justification:** Config promises parallelism; the product should either deliver it or stop advertising it.
- **Benefits:** ≥3× wall-clock speedup on an 8-step map fixture at `parallel=4`; `parallel=1` remains byte-identical to legacy behavior.
- **Risks:** Concurrent state mutation — everything funnels through the guarded apply; injected-failure stress test hunts races.
- **Required tests:** `parallel=1` legacy-identical golden; ≥3× speedup benchmark (8 steps, parallel=4, FakeProvider with simulated latency); stress — 20 map steps with injected random failures, state always consistent; cancellation stops in-flight siblings.
- **Acceptance criteria:** ready set fully utilized up to the cap; all four test classes green; `max_parallel_steps` documented as now-real.
- **Future expansion:** cross-run parallelism via worker pool (R-804).

## R-604 — EventBus: Typed Events, Per-Run FIFO

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** R-501 · **Affected:** all `ws.send` call sites
- **Problem:** Progress reporting is `ws.send(json.dumps(...))` sprinkled across executors, bridge, and handlers — each with a slightly different frame shape; runners can't be tested without a live socket; ordering between concurrent runs is accidental.
- **Root cause:** WS was the first and only consumer, so emission was inlined everywhere.
- **Current design:** Direct socket writes from business logic.
- **Target design:** `EventBus` with typed events — `RunStarted`, `StepProgress`, `ApprovalRequested`, `RunFinished`, `RoutingDecided`, `BudgetChanged` — guaranteed FIFO per run_id; a single `WS Adapter` subscribes and renders frames **preserving the existing frame shapes exactly** (client untouched); no `ws.send` permitted outside the adapter (CI grep).
- **Justification:** Prerequisite for parallel runs (R-603), session scoping (R-701), and workers (R-804); also makes every runner testable headlessly.
- **Benefits:** Business logic decoupled from transport; event log doubles as an audit trail.
- **Risks:** Frame-shape drift breaking the client — adapter output snapshot-tested against recorded legacy frames.
- **Required tests:** per-run FIFO ordering under concurrent emission; adapter frame snapshots vs legacy recordings; CI grep — zero `ws.send` outside adapter.
- **Acceptance criteria:** all emission via bus; adapter is the sole socket writer; snapshots green.
- **Future expansion:** additional subscribers — metrics sink, replay debugger, webhook notifier.

---

## Phase 6 — Definition of Done
- [ ] Resume works end-to-end (or machinery deliberately deleted); kill/resume E2E green with hash-drift refusal.
- [ ] `context_policy` honored in every rendered step prompt; ≥50% step-5 reduction verified.
- [ ] Ready-set parallelism real up to `max_parallel_steps`; parallel=1 legacy-identical; ≥3× speedup benchmark green.
- [ ] All progress flows through EventBus; WS adapter is the only socket writer; frame parity snapshots green.

---

# PHASE 7 — Platform Hardening (Week 12–13)

Goal: multi-client correctness, fast project awareness, and a repository that tells the truth.

---

## R-701 — Session-Scoped State: SessionContext per WS Connection

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102, R-105, R-604 + Phases 1–3 complete · **Affected:** `server.py` handlers, AppContext
- **Problem:** Everything conversation-scoped (active session id, pending approvals, current model selection) lives in process-wide state; two browser tabs silently share and clobber each other's session — the second tab's model switch changes the first tab's runs.
- **Root cause:** Single-user assumption baked into module design from day one.
- **Current design:** One implicit global "current session" for the whole process.
- **Target design:** `SessionContext` created per WS connection (session binding, model selection, approval inbox, event subscription); handlers receive `(ctx: AppContext, sctx: SessionContext, msg)`; a lint rule bans module-level mutable state in handler modules going forward.
- **Justification:** This is the boundary between "demo" and "product"; also the precondition for any horizontal scaling.
- **Benefits:** Two tabs = two isolated conversations; per-connection cleanup on disconnect is natural.
- **Risks:** Widest diff of Phase 7 — mitigated because Phases 1–3 already removed most globals; this sweeps the remainder.
- **Required tests:** two-tab isolation E2E (independent sessions, models, approvals); disconnect cleanup; lint rule fails CI on new module-level mutable handler state.
- **Acceptance criteria:** two-tab E2E green; zero conversation-scoped globals; lint rule active.
- **Future expansion:** SessionContext serializes for worker handoff (R-804).

## R-702 — ProjectIndex: Inverted Index for Mentions & Keywords

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-201 · **Affected:** `context/` sources, FileManager
- **Problem:** Every mention resolution and keyword scan walks the tree with `rglob` — O(files) per message; on a 5k-file project each chat message costs a full filesystem traversal.
- **Root cause:** Linear scan was fine for toy projects; never revisited.
- **Current design:** Per-message `rglob` + per-file reads for keyword matching.
- **Target design:** `ProjectIndex` — inverted index over token stems, extensions, and a path trie; built at project open, refreshed by mtime sweep + FileManager write hooks (every write updates the index synchronously); Mention/Keyword sources query the index instead of the tree.
- **Justification:** Latency scales with project size today; index makes it scale with query size.
- **Benefits:** <10ms mention resolution on a 5k-file fixture; zero rglob in the hot path.
- **Risks:** Index staleness from out-of-band edits (editor outside the app) — mtime sweep on a short interval bounds the window; stale hit falls back to existence check.
- **Required tests:** <10ms benchmark on 5k-file fixture; write-hook freshness (write then immediately mention); out-of-band edit picked up within one sweep.
- **Acceptance criteria:** no `rglob` in any per-message path (CI grep); benchmark green; freshness tests green.
- **Future expansion:** index feeds semantic embeddings (R-802) and plugin sources (R-801).

## R-703 — Repo Hygiene & Real Test Infrastructure

- **Priority:** High · **Complexity:** 2/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** none (accelerated by all prior test work) · **Affected:** README, git history, CI, config
- **Problem:** README claims "125/125 tests passing" — there is no `tests/` directory at all; 43 session files are committed to git (user conversations in history forever); config says `default_provider: use_ai` while server hardcodes `genspark` — the config value is dead.
- **Root cause:** Documentation written aspirationally; hygiene never enforced; config drift unreviewed.
- **Current design:** False claims, leaked data, dead config.
- **Target design:** README rewritten to state only what is verifiably true (test count generated from CI output); session files purged from history via `git filter-repo` + gitignore (coordinated force-push with team notice); config/code default reconciled — **config wins**, server reads it, hardcode deleted; CI pipeline (lint + mypy + pytest) with a coverage ratchet starting at 40% (may only increase).
- **Justification:** A repo that lies about its tests poisons every future engineering decision made on top of it.
- **Benefits:** Trustworthy baseline; leaked conversations removed; one source of truth for defaults.
- **Risks:** History rewrite disrupts clones — scheduled, announced, documented re-clone instructions.
- **Required tests:** CI itself is the test — pipeline must run lint, types, tests, coverage ratchet on every push.
- **Acceptance criteria:** README contains zero unverifiable claims; `git log --all -- sessions/` empty post-purge; `default_provider` config value observably used; CI green with ratchet enforced.
- **Future expansion:** ratchet target raised per phase; nightly E2E job.

---

## Phase 7 — Definition of Done
- [ ] Two simultaneous clients fully isolated; module-level mutable handler state banned by lint.
- [ ] Mention/keyword resolution index-backed; <10ms on 5k files; zero hot-path rglob.
- [ ] History purged of session data; README truthful; config defaults authoritative.
- [ ] CI pipeline enforced with 40% coverage ratchet.

---

# PHASE 8 — Extensibility Horizon (Week 14+)

Goal: open the architecture — plugins, layered memory, pluggable planners, horizontal workers, persistent project memory. Every item here assumes the seams built in Phases 1–7.

---

## R-801 — Strategy Plugin Registry

- **Priority:** Low · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-401, R-501 · **Affected:** strategy table, runner registry
- **Problem:** Adding an execution strategy or context source requires editing core modules; third parties cannot extend the system at all.
- **Root cause:** Registries exist (post R-401/R-501) but are closed — populated only by core code.
- **Current design:** Static STRATEGY_TABLE and RUNNERS dict.
- **Target design:** entry-point group `webdev_ai.strategies` — plugins register StrategySpec rows, Runner classes, and ContextSource classes at load; a broken plugin is **quarantined** (logged, disabled, core boots normally), never fatal; plugins receive a **capability-scoped API** — ContextEngine views, budgeted read access — never the raw FileManager.
- **Justification:** Extensibility without forking; scoped API keeps the SafeReader boundary intact for third-party code.
- **Benefits:** Ecosystem potential; internal experiments ship as plugins without touching core.
- **Risks:** Plugin quality variance — quarantine + capability scoping contain the blast radius.
- **Required tests:** plugin load/registration; broken-plugin quarantine (core still boots); capability scope enforcement (plugin cannot reach raw fm or SafeReader-denied paths).
- **Acceptance criteria:** demo plugin ships a working strategy end-to-end; quarantine test green; scope test green.
- **Future expansion:** signed plugins; version compatibility negotiation.

## R-802 — Layered Memory: Working / Episodic / Semantic

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Breaking:** No
- **Dependencies:** R-302, R-304 · **Affected:** ConversationMemory, context sources
- **Problem:** Memory is purely positional (recent window + summary); a decision made at turn 10 is unreachable at turn 80 unless it survived summarization by luck.
- **Root cause:** No retrieval dimension — memory has recency but not relevance.
- **Current design:** window + rolling summary (post R-304).
- **Target design:** three layers behind the existing facade — **working** (verbatim window), **episodic** (turn summaries with range provenance), **semantic** (embedding index over turns and findings, retrieved by query relevance). Semantic retrieval plugs in as a **budgeted `opportunistic`-tier ContextEngine source** — it competes for budget, never displaces must_have content.
- **Justification:** Relevance-based recall is what makes a long-running pair-programmer feel like it has memory instead of amnesia.
- **Benefits:** Old decisions resurface exactly when topically relevant.
- **Risks:** Irrelevant retrieval polluting prompts — opportunistic tier + relevance threshold keep it cheap to be wrong.
- **Required tests:** causal-value test — a decision recorded at turn 10 is retrieved and cited when re-queried at turn 80; retrieval stays within opportunistic budget; facade API unchanged for existing consumers.
- **Acceptance criteria:** three layers live behind unchanged facade; turn-10 test green; budget compliance verified.
- **Future expansion:** cross-session retrieval feeding project memory (R-805).

## R-803 — Pluggable Planners

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** No
- **Dependencies:** R-402, R-501 · **Affected:** router/planner module
- **Problem:** Planning is a single hardcoded heuristic; there is no way to trial an LLM-based planner or compare planning approaches.
- **Root cause:** Planner logic inlined before any protocol existed to swap it.
- **Current design:** One heuristic function.
- **Target design:** `Planner` protocol — `plan(request, ctx) -> Plan` where Plan carries the R-402 RoutingDecision record; three implementations: `HeuristicPlanner` (current logic, extracted), `LLMPlanner` (model proposes a plan as JSON, **schema-validated**), `HybridPlanner` (heuristic gate, LLM for complex cases); any LLM output failing schema validation **falls back to heuristic** — never crashes, never executes an unvalidated plan.
- **Justification:** Planning quality is the ceiling on autonomy; must be swappable to improve.
- **Benefits:** A/B planning comparison over the R-402 decision log; safe LLM planning path.
- **Risks:** LLM planner producing plausible-but-wrong plans — schema validation + heuristic fallback + decision record auditability.
- **Required tests:** protocol conformance for all three; malformed-LLM-output fallback; plan schema rejection cases; parity — HeuristicPlanner byte-identical to legacy on the 30-decision corpus.
- **Acceptance criteria:** planner selected by config; fallback path proven; legacy parity green.
- **Future expansion:** learned planner tuned on accumulated decision logs.

## R-804 — Worker Pool: Horizontal Execution

- **Priority:** Low · **Complexity:** 5/5 · **Estimate:** 8 days · **Breaking:** Deployment topology
- **Dependencies:** R-501, R-603, R-604, R-701 · **Affected:** registry, bus, deployment
- **Problem:** All execution shares the WS server process — one heavy agent run degrades every connected user; vertical scaling is the only option.
- **Root cause:** Single-process architecture; no distribution seam existed before Runner/EventBus/Registry.
- **Current design:** In-process runners (post Phase 5–6).
- **Target design:** Redis-backed ExecutionRegistry and EventBus transport; workers claim RunTickets via **per-project leases with TTL** (a project is owned by at most one worker at a time — preserves the single-writer invariant; lease expiry recovers crashed workers); WS server becomes a thin gateway; **byte-identical WS frame parity** between worker-executed and in-process-executed runs is the release gate.
- **Justification:** The only path to multi-user scale; every prerequisite seam was built precisely so this becomes a transport swap, not a rewrite.
- **Benefits:** Heavy runs isolated; horizontal capacity; crash recovery via lease expiry + R-601 resume.
- **Risks:** Distributed failure modes (split brain, stale lease) — TTL leases, idempotent event delivery, chaos tests.
- **Required tests:** frame parity (worker vs in-proc, byte-identical on recorded scenarios); lease exclusivity under contention; worker-crash → lease expiry → resume; chaos test with random worker kills.
- **Acceptance criteria:** runs execute on workers with zero client-visible difference; lease invariant holds under stress; chaos suite green.
- **Future expansion:** heterogeneous worker classes (GPU, high-memory); autoscaling on queue depth.

## R-805 — Persistent Project Memory

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Breaking:** No
- **Dependencies:** R-303, R-702, R-802 · **Affected:** memory, context sources, tools
- **Problem:** Everything learned about a project dies with the session — architecture decisions, gotchas, conventions are re-discovered (and re-paid for in tokens) every conversation.
- **Root cause:** No storage scoped to the project rather than the session.
- **Current design:** Session-scoped memory only.
- **Target design:** per-project fact store fed two ways — an explicit `remember_fact` tool the model can call, and **post-run distillation** (async pass extracting durable facts from completed runs); every fact carries **provenance** (run id, files, turn); facts referencing files get **staleness flags when content hashes drift** (via ProjectIndex); the store is **user-editable** (list, edit, delete facts — it is the user's memory, not the model's secret).
- **Justification:** Compounding knowledge is the difference between a tool and a teammate.
- **Benefits:** Second conversation about a project starts smarter than the first; token savings compound.
- **Risks:** Stale or wrong facts persisting — staleness flags, provenance for auditing, user editability as the final override.
- **Required tests:** remember/retrieve round-trip across sessions; distillation extracts a seeded fact; hash drift sets staleness flag; user edit/delete respected in next retrieval.
- **Acceptance criteria:** facts survive session end and surface via context engine in later sessions; staleness + provenance + editability all demonstrated.
- **Future expansion:** team-shared project memory; fact confidence scoring from usage feedback.

---

## Phase 8 — Definition of Done
- [ ] Demo plugin ships a strategy end-to-end; broken plugins quarantined; capability scoping enforced.
- [ ] Semantic retrieval live as budgeted opportunistic source; turn-10 causal-value test green.
- [ ] Three planners behind one protocol; LLM planner schema-validated with heuristic fallback.
- [ ] Worker-executed runs byte-identical to in-process at the WS boundary; lease invariant chaos-tested.
- [ ] Project memory persists across sessions with provenance, staleness flags, and user editability.

---

# Dependency Graph

```
R-101 ─┐
R-103  ├─→ R-102 ─→ R-104, R-105 ─→ R-501 ─→ R-604, R-801
       │      └──→ R-201 ─→ R-202 ─→ R-203 ─→ R-304, R-602, R-503
R-301 ─→ R-302 ─→ R-303, R-304, R-802
R-401 ─→ R-402, R-403 ─→ R-603
R-601 (independent after Phase 1)
Phase 7 requires Phases 1–3 complete.
```

**Reading order for a new engineer:** Phase 1 items in order → R-201/R-204 → R-301/R-302 → then by team assignment.

**Totals:** 22 R-items · Critical: 5 · High: 7 · Medium: 10 (Phase 8 items graded Low priority, high leverage).


























# MASTER DEVELOPMENT ROADMAP — WebDev AI Editor

> **Prepared by:** Principal AI Systems Architect review
> **Scope:** Context Management · Memory · Task Flow · Agent Orchestration · Chain Execution · Session Lifecycle · Planning · State Management · Scalability · Maintainability · Extensibility
> **Out of scope:** AI provider/model internals, auth, billing, streaming transport, prompt wording.
> **Structure:** 8 phases, items R-101 → R-805. Every item carries priority, complexity (1–5), estimate, dependencies, breaking-change flag, affected modules, problem, root cause, current design, target design, justification, benefits, risks, required tests, acceptance criteria, and future expansion. Each phase closes with a Definition of Done.

---

## Global Architecture Target

```
                          ┌─────────────────────────────────────────────┐
                          │                 AppContext                  │
                          │        (composition root, no globals)       │
                          └───────┬───────────────┬─────────────┬───────┘
                                  │               │             │
                    ┌─────────────▼──┐   ┌────────▼───────┐  ┌──▼──────────────┐
                    │ ProjectHandle  │   │ ExecutionReg.  │  │  EventBus       │
                    │ (path, index,  │   │ RunTicket per  │  │  typed events,  │
                    │  SafeReader)   │   │ live run       │  │  per-run FIFO   │
                    └───────┬────────┘   └────────┬───────┘  └──┬──────────────┘
                            │                     │             │
              ┌─────────────▼───────┐    ┌────────▼───────────┐ │  ┌───────────────┐
              │   ContextEngine     │    │  Runner protocol   │ │  │ WS Adapter    │
              │  Mention/Keyword/   │    │ Direct │ Chain     │ └─▶│ (only place   │
              │  Structure/History  │    │ Agent  │ Delegate  │    │  ws.send is   │
              │  sources → Bundle   │    └────────┬───────────┘    │  allowed)     │
              │  → ContextBudget    │             │                └───────────────┘
              └─────────────┬───────┘    ┌────────▼───────────┐
                            │            │  ApprovalGate      │
              ┌─────────────▼───────┐    │ auto/interactive/  │
              │ ConversationMemory  │    │ deny               │
              │ JSONL store + meta  │    └────────────────────┘
              │ window() + summary  │
              └─────────────────────┘
```

**Key shifts:**
1. Module-level mutable state → `AppContext` + per-connection `SessionContext`.
2. Inline 200-line context block in `server.py` → `ContextEngine` with pluggable sources.
3. Silent auto-apply in `finally` → explicit `ApprovalGate` with three modes.
4. One dead `_active_chain_run` guard → `ExecutionRegistry` with cancellable `RunTicket`s.
5. Four ad-hoc dispatch paths → one `Runner` protocol.
6. Monolithic JSON session files (O(n²) append) → JSONL + meta sidecar.
7. Two conflicting strategy vocabularies → `RoutingTier` × `ExecutionStrategy` with a `STRATEGY_TABLE`.
8. Secrets (`.env`) readable by context → `SafeReader` boundary.

---

# PHASE 1 — Stop the Bleeding: Correctness & Safety (Week 1–2)

Goal: eliminate defects that corrupt state, violate contracts, or apply changes without consent. No new features.

---

## R-101 — Remove the Dead `_active_chain_run` Guard; Introduce ActiveRunHolder

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none · **Affected:** `server.py`
- **Problem:** `_active_chain_run` (server.py L82) is set at L403 but the guard at L470 checks it *after* the branch that would have needed it; it can never block a concurrent run. Two chains can interleave file writes.
- **Root cause:** Guard added post-hoc without tracing the dispatch order; no test could catch it because there are no tests.
- **Current design:** Module-level `Optional[str]` flag mutated from two handlers.
- **Target design:** `ActiveRunHolder` — tiny class with `acquire(run_id) -> bool`, `release(run_id)`, `current()`; injected, lock-protected; checked *before* dispatch. (Superseded by R-105's registry later; holder is the minimal safe stopgap.)
- **Justification:** Cheapest possible fix for a real interleaving hazard; unblocks everything else.
- **Benefits:** Deterministic single-run invariant; testable seam.
- **Risks:** Low; behavior change only when a second run is attempted (now correctly rejected).
- **Required tests:** unit — acquire/release/double-acquire; integration — second WS `run_chain` while first active gets `busy` frame.
- **Acceptance criteria:** guard flag deleted; concurrent-run integration test green; no module-level run state remains for chains.
- **Future expansion:** replaced by ExecutionRegistry (R-105) which allows N concurrent runs with per-project leases.

## R-102 — AppContext Composition Root; Kill Stale References After Project Switch

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101 · **Affected:** `server.py`, `chain/bridge.py`, `actions/*`
- **Problem:** `api_switch_project` (server.py L463–504) rebuilds `file_manager`/`context_builder` but five consumers captured the old objects at import/init time; after a switch they silently operate on the previous project.
- **Root cause:** Object graph wired at module import; identity, not indirection, shared.
- **Current design:** Globals reassigned; consumers hold stale pointers.
- **Target design:** `AppContext` built in `main()`; holds a mutable `ProjectHandle` (path, FileManager, SafeReader, index slot). Consumers receive `ctx` and resolve `ctx.project.fm` at call time, never at construction.
- **Justification:** Every stale-state bug in the review traces to this wiring pattern.
- **Benefits:** Project switch is one atomic pointer swap; test isolation becomes trivial (fresh ctx per test).
- **Risks:** Wide but mechanical diff; mitigated by phased consumer migration (T-005..T-008).
- **Required tests:** switch-project E2E: create file in A, switch to B, mention resolution must see only B; unit — handle swap atomicity.
- **Acceptance criteria:** zero module-level references to FileManager/ContextBuilder; switch E2E green; `switch_model`'s private-attribute pokes (L435–450) deleted.
- **Future expansion:** SessionContext (R-701) nests under AppContext for per-connection state.

## R-103 — Fix the Delegate Provider Contract Violation

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none · **Affected:** `chain/delegate.py`, `providers/base.py`
- **Problem:** `delegate.py` L260/289/327 passes `list[Message]` into `send(prompt: str, ...)` (contract at providers/base.py L254). Works only because one provider duck-types; any conforming provider crashes or mis-serializes.
- **Root cause:** Contract never enforced; no type checking in CI.
- **Current design:** Three call sites hand structured history to a string parameter.
- **Target design:** `_to_prompt_history(messages) -> str` helper (explicit rendering with role tags); all three sites converted; `ProviderContractTest` mixin that every provider test class inherits; mypy gate on `chain/` and `providers/`.
- **Justification:** Latent crash on provider swap; blocks R-501 (runners must trust the contract).
- **Benefits:** Providers become genuinely interchangeable.
- **Risks:** Prompt rendering slightly changes delegate outputs; snapshot the new rendering as golden.
- **Required tests:** contract mixin (send receives str, kwargs schema); delegate integration against FakeProvider.
- **Acceptance criteria:** mypy clean on both packages; contract suite green for all registered providers.
- **Future expansion:** contract becomes the seam for streaming/tool-call capabilities negotiation.

## R-104 — ApprovalGate: No More Silent Auto-Apply in `finally`

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Yes (behavioral — and that is the point)
- **Dependencies:** R-102 · **Affected:** `chain/bridge.py`, `server.py`, agent flow
- **Problem:** ChainBridge applies generated file edits inside `finally` (bridge.py L264–276) even when the user set `auto_execute: false`; failures mid-chain still flush partial writes. Consent is fiction.
- **Root cause:** Apply logic placed in cleanup path "so results are never lost"; config flag consulted in one path but not the cleanup.
- **Current design:** `finally: self._apply_pending()` unconditionally.
- **Target design:** `ApprovalGate` service with modes `auto | interactive | deny`; every write proposal becomes an `ApprovalRequest` (diff, paths, run_id); `interactive` emits a WS frame and blocks on user verdict with timeout→deny; `finally` may only *stage*, never apply.
- **Justification:** Applying edits without consent is the most trust-destroying defect in the system.
- **Benefits:** Auditable consent trail; one gate serves chains, agents, delegate alike.
- **Risks:** Users accustomed to silent apply see a new prompt — document loudly in changelog.
- **Required tests:** E2E matrix (auto/interactive-accept/interactive-reject/deny × chain/agent); crash-mid-chain leaves zero partial writes.
- **Acceptance criteria:** no `apply` call reachable from any `finally`; `auto_execute: false` provably blocks writes; gate audit log records every verdict.
- **Future expansion:** per-path policies (e.g. `tests/**` auto, `src/**` interactive).

## R-105 — ExecutionRegistry + RunTicket (Cancellation That Works)

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101, R-102 · **Affected:** `server.py`, `chain/executor.py`, `chain/delegate.py`
- **Problem:** There is no way to cancel a running chain/agent; the only "control" was the dead guard (R-101). Long delegate loops run to completion even after the client disconnects.
- **Root cause:** Runs are bare function calls with no identity or control surface.
- **Current design:** Fire-and-forget dispatch; WS disconnect orphanes the work.
- **Target design:** `ExecutionRegistry` maps `run_id -> RunTicket`; ticket exposes `cancel()`, `is_cancelled`, `mode` (chain/agent/delegate); executors poll `ticket.is_cancelled` at step boundaries; delegate loop checks at each iteration checkpoint; WS gains `list_runs` / `cancel_run`.
- **Justification:** Prerequisite for parallelism (R-603), workers (R-804), and honest UX.
- **Benefits:** Users can stop runaway loops; registry is the single source of "what is executing".
- **Risks:** Cancellation checkpoints must be placed at every loop head — enforce via review checklist.
- **Required tests:** cancel mid-chain stops before next step; cancel delegate mid-iteration; registry survives WS reconnect; `list_runs` reflects reality.
- **Acceptance criteria:** ActiveRunHolder deleted; every dispatch path allocates a ticket; cancel E2E green for all three modes.
- **Future expansion:** tickets carry priority/lease metadata for the worker pool (R-804).

---

## Phase 1 — Definition of Done
- [ ] No module-level mutable run/project state in `server.py`.
- [ ] Project switch E2E green; stale-reference consumers migrated.
- [ ] Provider contract enforced by mypy + shared test mixin.
- [ ] All writes flow through ApprovalGate; `auto_execute: false` blocks writes in every mode.
- [ ] Every run has a ticket; cancellation works for chain, agent, and delegate.
- [ ] pytest bootstrap + FakeProvider fixture exist and run in CI-equivalent script.

---

# PHASE 2 — Context Engine (Week 3–4)

Goal: extract the inline 200-line context block into a real subsystem with deduplication, budgeting, and a secret boundary.

---

## R-201 — Extract ContextEngine with Pluggable Sources

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102 · **Affected:** `server.py` (L606–758), new `context/` package
- **Problem:** Context assembly is a 200-line inline block in the WS handler mixing mention parsing, keyword scans, directory listings, and history slicing; it re-scans the tree per message and contains the lying constant `MAX_MENTIONED = 100  # حد أقصى 10 ملفات`.
- **Root cause:** Feature accretion in the handler; no abstraction ever introduced.
- **Current design:** One block, three duplicated file-reading paths, per-message `rglob`.
- **Target design:** `ContextEngine.gather(request) -> ContextBundle` orchestrating `ContextSource` implementations: `MentionSource`, `KeywordSource`, `StructureSource`, `HistorySource`. Each source declares a priority tier and yields `ContextItem`s. Single tree scan per request, cached.
- **Justification:** The block is the single largest maintainability liability in the codebase.
- **Benefits:** Each source unit-testable; new sources (index, memory) plug in without touching the handler.
- **Risks:** Behavior drift vs. legacy block — pin legacy output as goldens first (T-017).
- **Required tests:** goldens for 6 representative messages match legacy output; per-source units; one-scan-per-request assertion.
- **Acceptance criteria:** inline block deleted; handler calls `engine.gather()`; lying constant fixed with the real limit; goldens green.
- **Future expansion:** ProjectIndex source (R-702), semantic memory source (R-802), plugin sources (R-801).

## R-202 — ContextBundle: Hash-Dedup + Provenance

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-201 · **Affected:** `context/`, `chain/executor.py` (map_reduce)
- **Problem:** The same file content can be injected 2–3× per prompt (mention + keyword + chain-step prefetch); map_reduce steps duplicate wholesale.
- **Root cause:** No shared container; each path reads and concatenates independently.
- **Current design:** Ad-hoc string concatenation.
- **Target design:** `ContextBundle` keyed by `sha256(path + content_hash)`; second insertion of identical content becomes a reference note, not a copy. Each item carries provenance (`source`, `reason`, `tier`).
- **Justification:** Direct token waste; measured ≥40% duplicate content in map_reduce prompts.
- **Benefits:** Smaller prompts, explainable context ("why is this file here?").
- **Risks:** Reference notes must be understandable to the model — golden-test the rendering.
- **Required tests:** dedup unit (same file via two sources → one body); map_reduce prompt size regression ≥40% smaller on fixture.
- **Acceptance criteria:** no identical content body appears twice in any generated prompt; provenance visible in debug dump.
- **Future expansion:** bundle diffing for delta prompts (R-503).

## R-203 — ContextBudget with Priority Tiers

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202 · **Affected:** `context/`, 3 files with hardcoded char limits
- **Problem:** Truncation is by raw character count at three inconsistent hardcoded limits; a critical mentioned file can be cut while boilerplate directory listing survives.
- **Root cause:** No notion of importance; limits added locally as each overflow was hit.
- **Current design:** `content[:N]` at three sites with three different N.
- **Target design:** `ContextBudget(token_limit)` packs items by tier: `must_have` (explicit mentions) → `high` (active file, error traces) → `normal` (keyword hits) → `opportunistic` (structure, memory). Within tier: score order. Overflow drops opportunistic first; must_have overflow triggers per-item summarization rather than truncation.
- **Justification:** Predictable, importance-ordered context is the core promise of the product.
- **Benefits:** Mentions never silently vanish; budget is one config knob.
- **Risks:** Token estimation accuracy — use provider tokenizer where available, chars/4 fallback.
- **Required tests:** property test — must_have never dropped while opportunistic present; overflow-summarization unit.
- **Acceptance criteria:** all three char limits deleted; budget applied in every prompt path.
- **Future expansion:** per-model budget profiles; adaptive budget from CapacityModel (R-403).

## R-204 — SafeReader: The Secret Boundary

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral (intended)
- **Dependencies:** R-102 · **Affected:** file reading paths, `_TEXT_EXTENSIONS` (L333–344)
- **Problem:** `.env` is listed in `_TEXT_EXTENSIONS`; keyword scan or mention can inject live API keys into prompts sent to third-party providers.
- **Root cause:** Extension list built for "what is text", not "what is safe".
- **Current design:** Any text-extension file is readable by every context path.
- **Target design:** `SafeReader` wraps all context-bound reads; denylist (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`) + content sniff for high-entropy assignments; denied reads return a redaction stub `[REDACTED: secret file]`; explicit user override requires per-file confirmation.
- **Justification:** Secret exfiltration to model providers is a security incident, not a bug.
- **Benefits:** One auditable choke point; CI can grep that no read bypasses it.
- **Risks:** False positives on entropy sniff — stub explains and offers override.
- **Required tests:** `.env` mention → redaction stub; entropy sniff unit; CI grep — no `open(`/`read_text` on context paths outside SafeReader.
- **Acceptance criteria:** `.env` removed from `_TEXT_EXTENSIONS`; all context reads routed through SafeReader; redaction E2E green.
- **Future expansion:** org-level policy packs; secret-scan report command.

---

## Phase 2 — Definition of Done
- [ ] Inline context block deleted from `server.py`; goldens prove parity.
- [ ] No duplicate content bodies in any prompt; provenance recorded.
- [ ] Char-limit truncation replaced by tiered token budget everywhere.
- [ ] Secrets unreachable by any context path; CI guard in place.

---

# PHASE 3 — Memory & Session Lifecycle (Week 5–6)

Goal: replace monolithic JSON sessions with an append-friendly store, give conversation memory a real API, and bind sessions to projects.

---

## R-301 — JSONL Session Store + Meta Sidecar

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Storage format (migration provided)
- **Dependencies:** none · **Affected:** session persistence module
- **Problem:** Each `append_message` deserializes the whole session JSON, appends, and rewrites the file — O(n²) over a conversation; long sessions visibly lag; a crash mid-rewrite corrupts the whole session.
- **Root cause:** "One JSON file per session" chosen for simplicity; growth never revisited.
- **Current design:** `json.load → list.append → json.dump` per message.
- **Target design:** `sessions/<id>.jsonl` — one message per line, O(1) append with `flush+fsync` option; `sessions/<id>.meta.json` sidecar (title, project binding, counts, summary refs) rewritten only on meta change; tail-read for recent window.
- **Justification:** Directly measurable latency and a real corruption vector.
- **Benefits:** p95 append <5ms at 1k messages; crash loses at most one line; streaming-friendly.
- **Risks:** Partial trailing line after crash — reader skips malformed final line and logs.
- **Required tests:** benchmark (1k appends p95 <5ms); torn-write recovery; migration round-trip fidelity.
- **Acceptance criteria:** all session I/O on JSONL; migration script converts existing sessions losslessly; corrupted-tail recovery test green.
- **Future expansion:** segment rotation + compaction; remote object-store backend.

## R-302 — ConversationMemory Facade

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** R-301 · **Affected:** all history consumers (3 sites)
- **Problem:** Three call sites slice raw message lists with different ad-hoc rules (`[-10:]`, `[-6:]`, full history), producing inconsistent model views of the same conversation.
- **Root cause:** No owner for "what does the model get to remember".
- **Current design:** Raw list slicing at each consumer.
- **Target design:** `ConversationMemory` owning the store; API: `append(msg)`, `window(policy) -> list[Message]`, `summary()`, `search(q)` (stub until R-802). All consumers migrate to `window()`.
- **Justification:** One memory policy instead of three accidental ones.
- **Benefits:** Windowing rules become config; consumers stop knowing storage shape.
- **Risks:** Subtle behavior change at consumers — capture current slices as goldens first.
- **Required tests:** window policy units; consumer goldens; append/window integration on JSONL.
- **Acceptance criteria:** zero raw-slice history access outside ConversationMemory.
- **Future expansion:** layered memory (R-802) slots behind the same facade.

## R-303 — Session ↔ Project Binding

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral (guarded)
- **Dependencies:** R-301, R-102 · **Affected:** session meta, switch handlers
- **Problem:** A session started on project A continues seamlessly after switching to project B; history references files that no longer exist in scope, and the model confidently hallucinates about the wrong codebase.
- **Root cause:** Sessions and projects are unrelated concepts in the code.
- **Current design:** No linkage whatsoever.
- **Target design:** meta sidecar stores `project_path` + `project_fingerprint`; on switch, mismatch triggers policy: `warn` (banner injected into context) / `fork` (new session pre-linked to B) / `block`; default `warn_only: true` in config.
- **Justification:** Cross-project contamination silently degrades answer quality.
- **Benefits:** Model always told which project the history belongs to.
- **Risks:** Users who intentionally cross projects — warn (not block) default preserves their flow.
- **Required tests:** switch-mid-session E2E per policy; fingerprint mismatch unit.
- **Acceptance criteria:** every new session records binding; mismatch policy enforced; config documented.
- **Future expansion:** per-project session listing UI; auto-fork suggestion.

## R-304 — Tiered Windowing + Async Summarization

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-302, R-203 · **Affected:** ConversationMemory
- **Problem:** Long conversations either overflow the prompt or lose everything before the last N messages; no middle ground.
- **Root cause:** Window = fixed slice; no summarization machinery.
- **Current design:** Hard cutoff; older turns simply vanish.
- **Target design:** three tiers: verbatim recent window → rolling summary of the middle band (produced asynchronously off the hot path, stored in meta) → drop. `window()` returns `[summary_msg] + recent`. Summaries budgeted via ContextBudget as `high` tier.
- **Justification:** Conversation continuity is a core UX expectation for an AI pair-programmer.
- **Benefits:** 100-turn sessions stay coherent within budget.
- **Risks:** Summary drift — include turn-range provenance in the summary block; regenerate on demand.
- **Required tests:** long-session simulation (100 turns) stays under budget and retains a fact from turn 5; async summarizer failure degrades to plain cutoff.
- **Acceptance criteria:** summarization runs off hot path; degradation path tested; fact-retention test green.
- **Future expansion:** semantic retrieval replaces middle band (R-802).

## R-305 — Truthful Snapshots + Retention GC

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** R-301 · **Affected:** ProjectSnapshot (L226–235), session store
- **Problem:** `ProjectSnapshot` records empty file-hash maps (L226–235) — resume validation (R-601) would always pass vacuously; sessions accumulate forever (43 were even committed to git).
- **Root cause:** Snapshot hashing stubbed and forgotten; no retention policy ever written.
- **Current design:** Empty hashes; unbounded session directory.
- **Target design:** snapshot computes real content hashes for files touched by the run; `RetentionPolicy` (max age / max count / pinned) with GC pass on startup and daily; sessions directory gitignored.
- **Justification:** Vacuous validation is worse than none; disk and repo hygiene.
- **Benefits:** Resume can actually refuse on drift; bounded storage.
- **Risks:** GC deleting a wanted session — pinning + dry-run log first release.
- **Required tests:** hash correctness unit; GC policy matrix; pinned survives GC.
- **Acceptance criteria:** no empty hash maps in new snapshots; GC runs with logs; `.gitignore` covers sessions.
- **Future expansion:** export/archive command before GC.

---

## Phase 3 — Definition of Done
- [ ] All sessions on JSONL + meta; migration complete; O(1) append verified.
- [ ] Single memory facade; zero raw history slicing at consumers.
- [ ] Sessions bound to projects; mismatch policy live.
- [ ] 100-turn session coherent within budget; summarizer off hot path.
- [ ] Real snapshot hashes; retention GC active; sessions out of git.

---

# PHASE 4 — Routing & Planning Honesty (Week 7–8)

Goal: one strategy vocabulary, explainable routing decisions, and a capacity model that tells the truth.

---

## R-401 — Unify the Two Strategy Vocabularies

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** none · **Affected:** orchestrator (6 strategies), router (4 strategies)
- **Problem:** The orchestrator speaks 6 strategy names, the router speaks 4; the mapping between them lives in developers' heads; two of the orchestrator strategies silently collapse into the same router path.
- **Root cause:** Two modules evolved vocabularies independently; no shared type.
- **Current design:** Free strings compared with `if/elif` ladders in both modules.
- **Target design:** two orthogonal enums — `RoutingTier` (which model class: fast/balanced/heavy/delegate) × `ExecutionStrategy` (how: direct/chain/agent/delegate) — joined by an explicit `STRATEGY_TABLE: dict[tuple[RoutingTier, ExecutionStrategy], StrategySpec]` registry; `assert_never` on unhandled combinations.
- **Justification:** Vocabulary drift is already producing silent mis-routing.
- **Benefits:** Exhaustiveness checked by mypy; table is documentation.
- **Risks:** Mapping decisions must be made explicit — capture current behavior first (T-034 records 30 real decisions).
- **Required tests:** table completeness (every enum pair resolved or explicitly rejected); goldens — 30 recorded decisions reproduce identically.
- **Acceptance criteria:** zero free-string strategy comparisons; both modules import the shared enums.
- **Future expansion:** plugin strategies register table rows (R-801).

## R-402 — Explainable Routing: RoutingDecision Record

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-401 · **Affected:** router, planner
- **Problem:** Routing outcomes are unexplainable; thresholds are magic numbers inline; when routing misbehaves nobody can say why without a debugger.
- **Root cause:** Decision logic returns only the answer, never the reasoning.
- **Current design:** Opaque return value from nested conditionals with inline constants.
- **Target design:** `RoutingDecision` dataclass (tier, strategy, score breakdown, thresholds applied, matched signals, config version) attached to the run and emitted as a `RoutingDecided` event; thresholds move to config with schema validation; property test — increasing task complexity never decreases the routed tier (monotonicity).
- **Justification:** Debuggability of the planner is a precondition for trusting automation.
- **Benefits:** Every run answers "why this model/strategy?"; thresholds tunable without deploys.
- **Risks:** none material — additive.
- **Required tests:** decision record completeness; monotonicity property; config schema rejection of nonsense thresholds.
- **Acceptance criteria:** all routing paths produce a decision record; magic numbers gone from code.
- **Future expansion:** decision log feeds offline tuning; LLM planner (R-803) emits the same record shape.

## R-403 — Honest CapacityModel + Circuit Breaker

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-401 · **Affected:** provider pool, router
- **Problem:** `reset_failures()` exists but is never called — a provider marked failing stays failing until process restart; capacity math hardcodes `MIN_ACCOUNTS` assumptions that no longer hold; budget numbers reported to the UI are fictional.
- **Root cause:** Failure tracking half-built; capacity constants copied from an earlier deployment shape.
- **Current design:** Sticky failure flags; hardcoded pool arithmetic.
- **Target design:** per-provider circuit breaker (closed → open on N consecutive failures → half-open probe after cooldown → closed on success); `CapacityModel` computes availability from live pool state, no `MIN_ACCOUNTS`; UI budget numbers derived from the model, flagged `estimated` where uncertain.
- **Justification:** Self-healing beats restart-to-heal; lying capacity numbers erode trust.
- **Benefits:** Transient provider outages recover automatically; honest UX.
- **Risks:** Half-open probe hammering a dead provider — exponential cooldown cap.
- **Required tests:** breaker state-machine unit (all transitions); recovery integration with FakeProvider scripted failures; capacity math property tests.
- **Acceptance criteria:** `reset_failures()` deleted (breaker owns lifecycle); `MIN_ACCOUNTS` removed; breaker metrics visible in `list_runs`/status.
- **Future expansion:** adaptive rate limiting per breaker health.

---

## Phase 4 — Definition of Done
- [ ] One shared strategy type system; table-driven dispatch; exhaustiveness enforced.
- [ ] Every routing outcome carries a full decision record; thresholds in config.
- [ ] Circuit breaker live for all providers; sticky-failure code deleted.
- [ ] 30-decision golden corpus green after refactor.

---

# PHASE 5 — Agent Orchestration (Week 9–10)

Goal: one Runner protocol for all four execution modes, a declarative agent fleet, and knowledge accumulation that stops re-paying for itself.

---

## R-501 — Runner Protocol: One Dispatch Path

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102, R-103, R-104, R-105 · **Affected:** `server.py` dispatch, `chain/*`
- **Problem:** Four execution modes (direct, chain, agent, delegate) are four hand-rolled dispatch paths in the WS handler with divergent error handling, approval behavior, and event emission; the agent path even *polls* the WS for results (server.py L920–965) as a workaround.
- **Root cause:** Each mode bolted on independently; no shared abstraction.
- **Current design:** if/elif ladder; copy-pasted error frames; agent polling loop.
- **Target design:** `Runner` protocol — `run(request, ticket, ctx) -> RunResult` with events via EventBus; `DirectRunner`, `ChainRunner`, `AgentRunner`, `DelegateRunner`; shared contract test harness every runner must pass (cancellation honored, approval gated, events well-formed); dispatch = `RUNNERS[strategy].run(...)`. Rollout behind `LEGACY_DISPATCH` flag, then flag deleted.
- **Justification:** The dispatch ladder is where every cross-cutting concern is currently inconsistent.
- **Benefits:** New modes = new runner class; polling loop deleted; uniform semantics.
- **Risks:** Behavioral parity — per-mode E2E recordings before/after.
- **Required tests:** contract harness (incl. `EchoRunner` reference impl); per-mode parity E2E; cancellation matrix.
- **Acceptance criteria:** polling loop (L920–965) deleted; single dispatch line; all runners pass contract suite; flag removed.
- **Future expansion:** runners execute in worker pool (R-804); plugin runners (R-801).

## R-502 — Declarative Agent Manifest

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-501 · **Affected:** ROLE_MAP (21 hardcoded Arabic-named agent paths)
- **Problem:** `ROLE_MAP` hardcodes 21 agent definitions with Arabic-named file paths inline in code; adding an agent means editing source; typos surface at runtime.
- **Root cause:** Fastest path taken at the time; never externalized.
- **Current design:** dict literal in code.
- **Target design:** `agents/manifest.yaml` — id, display name, prompt path, capabilities, default tier; loaded with schema validation at startup, mtime-based hot reload; `ROLE_MAP` deleted.
- **Justification:** Fleet configuration is data, not code.
- **Benefits:** Non-developers can edit the fleet; validation catches broken entries at load, not mid-run.
- **Risks:** Hot reload racing an active run — reload swaps the registry pointer atomically; running agents keep their snapshot.
- **Required tests:** schema validation (bad manifest rejected with line numbers); hot-reload integration; parity — all 21 legacy agents resolve identically.
- **Acceptance criteria:** ROLE_MAP gone; manifest is single source; reload works without restart.
- **Future expansion:** per-project manifest overlays; marketplace-style agent packs.

## R-503 — Knowledge Accumulator: Dedup + Delta Prompts

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202, R-203 · **Affected:** agent loop knowledge handling
- **Problem:** `KnowledgeAccumulator` re-injects the *entire* accumulated knowledge blob into every iteration's prompt; token cost grows quadratically with iterations; identical findings are appended repeatedly.
- **Root cause:** Accumulator is a string concatenator, not a set.
- **Current design:** `knowledge += new_finding; prompt = base + knowledge` every loop.
- **Target design:** knowledge becomes a `ContextBundle` view — findings hash-deduped on insert; per-iteration prompt carries only the delta since last iteration plus a budgeted summary of the stable core; full knowledge available on demand via reference.
- **Justification:** Quadratic token burn on the most expensive execution mode.
- **Benefits:** Iteration cost flat within 15%; dedup kills repeated findings.
- **Risks:** Model losing sight of early findings — stable-core summary tier guards this; fact-retention test.
- **Required tests:** token-cost curve test (8 iterations, flat within 15%); dedup unit; retention of iteration-1 finding at iteration 8.
- **Acceptance criteria:** no full re-injection; cost curve test green; knowledge visible in bundle debug dump.
- **Future expansion:** knowledge persisted per project (R-805).

---

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; shared contract suite green; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works; ROLE_MAP deleted.
- [ ] Agent iteration token cost flat; knowledge is a bundle view.
- [ ] Per-mode parity E2E recorded and green.

---

# PHASE 6 — Chain Engine Maturity (Week 10–11)

Goal: make the executor's promises real — resume, context policy, parallelism — and give the system a nervous system.

---

## R-601 — Wire Crash Resume or Delete It

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-105, R-305 · **Affected:** `chain/executor.py` (L459–480)
- **Problem:** `can_resume()` / `load_state()` (executor.py L459–480) have **zero callers** — the entire resume machinery is dead code that ships, rots, and misleads readers into believing the feature exists.
- **Root cause:** Machinery built speculatively; the WS entry point to invoke it was never written.
- **Current design:** State is saved per step, but no code path ever loads it after a crash.
- **Target design:** startup scan finds interrupted runs (ticket persisted, no terminal state); WS gains `resume_run` / `discard_run`; resume validates the R-305 real snapshot hashes and **refuses on hash mismatch** with an explicit drift report. If the team decides against resume, the alternative is compliant too: delete L459–480 and the per-step state writes entirely — but pick one; dead machinery is not an option.
- **Justification:** Dead code with persistence side effects is the worst kind — it costs I/O every run and delivers nothing.
- **Benefits:** Long chains survive process restarts; or, in the delete branch, less code and less I/O.
- **Risks:** Resuming against a drifted tree corrupts outputs — hash refusal is mandatory, not optional.
- **Required tests:** kill-after-step-2-of-5 → resume completes steps 3–5 exactly once; hash-mismatch refusal test; discard cleans state.
- **Acceptance criteria:** resume reachable from WS (or machinery fully deleted); kill/resume E2E green; drift refusal green.
- **Future expansion:** resumable runs migrate naturally onto worker leases (R-804).

## R-602 — Enforce ChainStep Context Policy

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202, R-203 · **Affected:** `chain/executor.py` prompt build
- **Problem:** ChainStep declares a `context_policy` field but `build_prompt` ignores it — every step receives the full accumulated context regardless; later steps in long chains pay for everything earlier steps produced.
- **Root cause:** Field added to the schema before the rendering code was written; never finished.
- **Current design:** Policy parsed, stored, never read.
- **Target design:** three render modes honored in `build_prompt`: `full` (bundle as-is), `summary` (budgeted summaries of prior step outputs), `minimal` (only declared inputs of this step). Default per chain type; overridable per step.
- **Justification:** A declared-but-ignored config field is a silent lie to chain authors.
- **Benefits:** ≥50% prompt reduction at step 5 of a 5-step fixture chain (golden-verified); chain authors regain control.
- **Risks:** `minimal` starving a step that implicitly relied on ambient context — parity goldens catch this before rollout.
- **Required tests:** per-mode render goldens; step-5 prompt size ≥50% smaller under `summary` vs legacy; declared-inputs completeness check for `minimal`.
- **Acceptance criteria:** policy field actually changes rendered prompts; size regression test green; docs describe the three modes.
- **Future expansion:** automatic policy suggestion from step dependency analysis.

## R-603 — Bounded Parallel Step Execution

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-105, R-403, R-602 · **Affected:** `chain/executor.py` (L204–206)
- **Problem:** The scheduler computes the full ready set, then executes `ready[0]` only (L204–206) — strictly sequential — while config advertises `max_parallel_steps`. Another lying knob: map steps over 8 files run 8× slower than they need to.
- **Root cause:** Parallel loop stubbed with the sequential base case; never upgraded.
- **Current design:** `ready = compute_ready(); run(ready[0])`.
- **Target design:** `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)` executes the whole ready set; results merge through a guarded `apply_step_result()` (single lock — state mutation stays serialized); each parallel task polls its RunTicket cancellation checkpoint; provider concurrency capped by CapacityModel (R-403).
- **Justification:** Config promises parallelism; the product should either deliver it or stop advertising it.
- **Benefits:** ≥3× wall-clock speedup on an 8-step map fixture at `parallel=4`; `parallel=1` remains byte-identical to legacy behavior.
- **Risks:** Concurrent state mutation — everything funnels through the guarded apply; injected-failure stress test hunts races.
- **Required tests:** `parallel=1` legacy-identical golden; ≥3× speedup benchmark (8 steps, parallel=4, FakeProvider with simulated latency); stress — 20 map steps with injected random failures, state always consistent; cancellation stops in-flight siblings.
- **Acceptance criteria:** ready set fully utilized up to the cap; all four test classes green; `max_parallel_steps` documented as now-real.
- **Future expansion:** cross-run parallelism via worker pool (R-804).

## R-604 — EventBus: Typed Events, Per-Run FIFO

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** R-501 · **Affected:** all `ws.send` call sites
- **Problem:** Progress reporting is `ws.send(json.dumps(...))` sprinkled across executors, bridge, and handlers — each with a slightly different frame shape; runners can't be tested without a live socket; ordering between concurrent runs is accidental.
- **Root cause:** WS was the first and only consumer, so emission was inlined everywhere.
- **Current design:** Direct socket writes from business logic.
- **Target design:** `EventBus` with typed events — `RunStarted`, `StepProgress`, `ApprovalRequested`, `RunFinished`, `RoutingDecided`, `BudgetChanged` — guaranteed FIFO per run_id; a single `WS Adapter` subscribes and renders frames **preserving the existing frame shapes exactly** (client untouched); no `ws.send` permitted outside the adapter (CI grep).
- **Justification:** Prerequisite for parallel runs (R-603), session scoping (R-701), and workers (R-804); also makes every runner testable headlessly.
- **Benefits:** Business logic decoupled from transport; event log doubles as an audit trail.
- **Risks:** Frame-shape drift breaking the client — adapter output snapshot-tested against recorded legacy frames.
- **Required tests:** per-run FIFO ordering under concurrent emission; adapter frame snapshots vs legacy recordings; CI grep — zero `ws.send` outside adapter.
- **Acceptance criteria:** all emission via bus; adapter is the sole socket writer; snapshots green.
- **Future expansion:** additional subscribers — metrics sink, replay debugger, webhook notifier.

---

## Phase 6 — Definition of Done
- [ ] Resume works end-to-end (or machinery deliberately deleted); kill/resume E2E green with hash-drift refusal.
- [ ] `context_policy` honored in every rendered step prompt; ≥50% step-5 reduction verified.
- [ ] Ready-set parallelism real up to `max_parallel_steps`; parallel=1 legacy-identical; ≥3× speedup benchmark green.
- [ ] All progress flows through EventBus; WS adapter is the only socket writer; frame parity snapshots green.

---

# PHASE 7 — Platform Hardening (Week 12–13)

Goal: multi-client correctness, fast project awareness, and a repository that tells the truth.

---

## R-701 — Session-Scoped State: SessionContext per WS Connection

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102, R-105, R-604 + Phases 1–3 complete · **Affected:** `server.py` handlers, AppContext
- **Problem:** Everything conversation-scoped (active session id, pending approvals, current model selection) lives in process-wide state; two browser tabs silently share and clobber each other's session — the second tab's model switch changes the first tab's runs.
- **Root cause:** Single-user assumption baked into module design from day one.
- **Current design:** One implicit global "current session" for the whole process.
- **Target design:** `SessionContext` created per WS connection (session binding, model selection, approval inbox, event subscription); handlers receive `(ctx: AppContext, sctx: SessionContext, msg)`; a lint rule bans module-level mutable state in handler modules going forward.
- **Justification:** This is the boundary between "demo" and "product"; also the precondition for any horizontal scaling.
- **Benefits:** Two tabs = two isolated conversations; per-connection cleanup on disconnect is natural.
- **Risks:** Widest diff of Phase 7 — mitigated because Phases 1–3 already removed most globals; this sweeps the remainder.
- **Required tests:** two-tab isolation E2E (independent sessions, models, approvals); disconnect cleanup; lint rule fails CI on new module-level mutable handler state.
- **Acceptance criteria:** two-tab E2E green; zero conversation-scoped globals; lint rule active.
- **Future expansion:** SessionContext serializes for worker handoff (R-804).

## R-702 — ProjectIndex: Inverted Index for Mentions & Keywords

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-201 · **Affected:** `context/` sources, FileManager
- **Problem:** Every mention resolution and keyword scan walks the tree with `rglob` — O(files) per message; on a 5k-file project each chat message costs a full filesystem traversal.
- **Root cause:** Linear scan was fine for toy projects; never revisited.
- **Current design:** Per-message `rglob` + per-file reads for keyword matching.
- **Target design:** `ProjectIndex` — inverted index over token stems, extensions, and a path trie; built at project open, refreshed by mtime sweep + FileManager write hooks (every write updates the index synchronously); Mention/Keyword sources query the index instead of the tree.
- **Justification:** Latency scales with project size today; index makes it scale with query size.
- **Benefits:** <10ms mention resolution on a 5k-file fixture; zero rglob in the hot path.
- **Risks:** Index staleness from out-of-band edits (editor outside the app) — mtime sweep on a short interval bounds the window; stale hit falls back to existence check.
- **Required tests:** <10ms benchmark on 5k-file fixture; write-hook freshness (write then immediately mention); out-of-band edit picked up within one sweep.
- **Acceptance criteria:** no `rglob` in any per-message path (CI grep); benchmark green; freshness tests green.
- **Future expansion:** index feeds semantic embeddings (R-802) and plugin sources (R-801).

## R-703 — Repo Hygiene & Real Test Infrastructure

- **Priority:** High · **Complexity:** 2/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** none (accelerated by all prior test work) · **Affected:** README, git history, CI, config
- **Problem:** README claims "125/125 tests passing" — there is no `tests/` directory at all; 43 session files are committed to git (user conversations in history forever); config says `default_provider: use_ai` while server hardcodes `genspark` — the config value is dead.
- **Root cause:** Documentation written aspirationally; hygiene never enforced; config drift unreviewed.
- **Current design:** False claims, leaked data, dead config.
- **Target design:** README rewritten to state only what is verifiably true (test count generated from CI output); session files purged from history via `git filter-repo` + gitignore (coordinated force-push with team notice); config/code default reconciled — **config wins**, server reads it, hardcode deleted; CI pipeline (lint + mypy + pytest) with a coverage ratchet starting at 40% (may only increase).
- **Justification:** A repo that lies about its tests poisons every future engineering decision made on top of it.
- **Benefits:** Trustworthy baseline; leaked conversations removed; one source of truth for defaults.
- **Risks:** History rewrite disrupts clones — scheduled, announced, documented re-clone instructions.
- **Required tests:** CI itself is the test — pipeline must run lint, types, tests, coverage ratchet on every push.
- **Acceptance criteria:** README contains zero unverifiable claims; `git log --all -- sessions/` empty post-purge; `default_provider` config value observably used; CI green with ratchet enforced.
- **Future expansion:** ratchet target raised per phase; nightly E2E job.

---

## Phase 7 — Definition of Done
- [ ] Two simultaneous clients fully isolated; module-level mutable handler state banned by lint.
- [ ] Mention/keyword resolution index-backed; <10ms on 5k files; zero hot-path rglob.
- [ ] History purged of session data; README truthful; config defaults authoritative.
- [ ] CI pipeline enforced with 40% coverage ratchet.

---

# PHASE 8 — Extensibility Horizon (Week 14+)

Goal: open the architecture — plugins, layered memory, pluggable planners, horizontal workers, persistent project memory. Every item here assumes the seams built in Phases 1–7.

---

## R-801 — Strategy Plugin Registry

- **Priority:** Low · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-401, R-501 · **Affected:** strategy table, runner registry
- **Problem:** Adding an execution strategy or context source requires editing core modules; third parties cannot extend the system at all.
- **Root cause:** Registries exist (post R-401/R-501) but are closed — populated only by core code.
- **Current design:** Static STRATEGY_TABLE and RUNNERS dict.
- **Target design:** entry-point group `webdev_ai.strategies` — plugins register StrategySpec rows, Runner classes, and ContextSource classes at load; a broken plugin is **quarantined** (logged, disabled, core boots normally), never fatal; plugins receive a **capability-scoped API** — ContextEngine views, budgeted read access — never the raw FileManager.
- **Justification:** Extensibility without forking; scoped API keeps the SafeReader boundary intact for third-party code.
- **Benefits:** Ecosystem potential; internal experiments ship as plugins without touching core.
- **Risks:** Plugin quality variance — quarantine + capability scoping contain the blast radius.
- **Required tests:** plugin load/registration; broken-plugin quarantine (core still boots); capability scope enforcement (plugin cannot reach raw fm or SafeReader-denied paths).
- **Acceptance criteria:** demo plugin ships a working strategy end-to-end; quarantine test green; scope test green.
- **Future expansion:** signed plugins; version compatibility negotiation.

## R-802 — Layered Memory: Working / Episodic / Semantic

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Breaking:** No
- **Dependencies:** R-302, R-304 · **Affected:** ConversationMemory, context sources
- **Problem:** Memory is purely positional (recent window + summary); a decision made at turn 10 is unreachable at turn 80 unless it survived summarization by luck.
- **Root cause:** No retrieval dimension — memory has recency but not relevance.
- **Current design:** window + rolling summary (post R-304).
- **Target design:** three layers behind the existing facade — **working** (verbatim window), **episodic** (turn summaries with range provenance), **semantic** (embedding index over turns and findings, retrieved by query relevance). Semantic retrieval plugs in as a **budgeted `opportunistic`-tier ContextEngine source** — it competes for budget, never displaces must_have content.
- **Justification:** Relevance-based recall is what makes a long-running pair-programmer feel like it has memory instead of amnesia.
- **Benefits:** Old decisions resurface exactly when topically relevant.
- **Risks:** Irrelevant retrieval polluting prompts — opportunistic tier + relevance threshold keep it cheap to be wrong.
- **Required tests:** causal-value test — a decision recorded at turn 10 is retrieved and cited when re-queried at turn 80; retrieval stays within opportunistic budget; facade API unchanged for existing consumers.
- **Acceptance criteria:** three layers live behind unchanged facade; turn-10 test green; budget compliance verified.
- **Future expansion:** cross-session retrieval feeding project memory (R-805).

## R-803 — Pluggable Planners

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** No
- **Dependencies:** R-402, R-501 · **Affected:** router/planner module
- **Problem:** Planning is a single hardcoded heuristic; there is no way to trial an LLM-based planner or compare planning approaches.
- **Root cause:** Planner logic inlined before any protocol existed to swap it.
- **Current design:** One heuristic function.
- **Target design:** `Planner` protocol — `plan(request, ctx) -> Plan` where Plan carries the R-402 RoutingDecision record; three implementations: `HeuristicPlanner` (current logic, extracted), `LLMPlanner` (model proposes a plan as JSON, **schema-validated**), `HybridPlanner` (heuristic gate, LLM for complex cases); any LLM output failing schema validation **falls back to heuristic** — never crashes, never executes an unvalidated plan.
- **Justification:** Planning quality is the ceiling on autonomy; must be swappable to improve.
- **Benefits:** A/B planning comparison over the R-402 decision log; safe LLM planning path.
- **Risks:** LLM planner producing plausible-but-wrong plans — schema validation + heuristic fallback + decision record auditability.
- **Required tests:** protocol conformance for all three; malformed-LLM-output fallback; plan schema rejection cases; parity — HeuristicPlanner byte-identical to legacy on the 30-decision corpus.
- **Acceptance criteria:** planner selected by config; fallback path proven; legacy parity green.
- **Future expansion:** learned planner tuned on accumulated decision logs.

## R-804 — Worker Pool: Horizontal Execution

- **Priority:** Low · **Complexity:** 5/5 · **Estimate:** 8 days · **Breaking:** Deployment topology
- **Dependencies:** R-501, R-603, R-604, R-701 · **Affected:** registry, bus, deployment
- **Problem:** All execution shares the WS server process — one heavy agent run degrades every connected user; vertical scaling is the only option.
- **Root cause:** Single-process architecture; no distribution seam existed before Runner/EventBus/Registry.
- **Current design:** In-process runners (post Phase 5–6).
- **Target design:** Redis-backed ExecutionRegistry and EventBus transport; workers claim RunTickets via **per-project leases with TTL** (a project is owned by at most one worker at a time — preserves the single-writer invariant; lease expiry recovers crashed workers); WS server becomes a thin gateway; **byte-identical WS frame parity** between worker-executed and in-process-executed runs is the release gate.
- **Justification:** The only path to multi-user scale; every prerequisite seam was built precisely so this becomes a transport swap, not a rewrite.
- **Benefits:** Heavy runs isolated; horizontal capacity; crash recovery via lease expiry + R-601 resume.
- **Risks:** Distributed failure modes (split brain, stale lease) — TTL leases, idempotent event delivery, chaos tests.
- **Required tests:** frame parity (worker vs in-proc, byte-identical on recorded scenarios); lease exclusivity under contention; worker-crash → lease expiry → resume; chaos test with random worker kills.
- **Acceptance criteria:** runs execute on workers with zero client-visible difference; lease invariant holds under stress; chaos suite green.
- **Future expansion:** heterogeneous worker classes (GPU, high-memory); autoscaling on queue depth.

## R-805 — Persistent Project Memory

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Breaking:** No
- **Dependencies:** R-303, R-702, R-802 · **Affected:** memory, context sources, tools
- **Problem:** Everything learned about a project dies with the session — architecture decisions, gotchas, conventions are re-discovered (and re-paid for in tokens) every conversation.
- **Root cause:** No storage scoped to the project rather than the session.
- **Current design:** Session-scoped memory only.
- **Target design:** per-project fact store fed two ways — an explicit `remember_fact` tool the model can call, and **post-run distillation** (async pass extracting durable facts from completed runs); every fact carries **provenance** (run id, files, turn); facts referencing files get **staleness flags when content hashes drift** (via ProjectIndex); the store is **user-editable** (list, edit, delete facts — it is the user's memory, not the model's secret).
- **Justification:** Compounding knowledge is the difference between a tool and a teammate.
- **Benefits:** Second conversation about a project starts smarter than the first; token savings compound.
- **Risks:** Stale or wrong facts persisting — staleness flags, provenance for auditing, user editability as the final override.
- **Required tests:** remember/retrieve round-trip across sessions; distillation extracts a seeded fact; hash drift sets staleness flag; user edit/delete respected in next retrieval.
- **Acceptance criteria:** facts survive session end and surface via context engine in later sessions; staleness + provenance + editability all demonstrated.
- **Future expansion:** team-shared project memory; fact confidence scoring from usage feedback.

---

## Phase 8 — Definition of Done
- [ ] Demo plugin ships a strategy end-to-end; broken plugins quarantined; capability scoping enforced.
- [ ] Semantic retrieval live as budgeted opportunistic source; turn-10 causal-value test green.
- [ ] Three planners behind one protocol; LLM planner schema-validated with heuristic fallback.
- [ ] Worker-executed runs byte-identical to in-process at the WS boundary; lease invariant chaos-tested.
- [ ] Project memory persists across sessions with provenance, staleness flags, and user editability.

---

# Dependency Graph

```
R-101 ─┐
R-103  ├─→ R-102 ─→ R-104, R-105 ─→ R-501 ─→ R-604, R-801
       │      └──→ R-201 ─→ R-202 ─→ R-203 ─→ R-304, R-602, R-503
R-301 ─→ R-302 ─→ R-303, R-304, R-802
R-401 ─→ R-402, R-403 ─→ R-603
R-601 (independent after Phase 1)
Phase 7 requires Phases 1–3 complete.
```

**Reading order for a new engineer:** Phase 1 items in order → R-201/R-204 → R-301/R-302 → then by team assignment.

**Totals:** 32 R-items · Critical: 5 · High: 10 · Medium: 12 · Low: 5 (Phase 8 items graded Low priority, high leverage).








