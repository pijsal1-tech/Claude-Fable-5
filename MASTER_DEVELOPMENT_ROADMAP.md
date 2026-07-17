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
