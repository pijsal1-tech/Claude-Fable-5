# MASTER DEVELOPMENT ROADMAP reviwe

> **Prepared by:** Principal AI Systems Architect review — unified edition
> **Scope:** Context Management · Memory · Task Flow · Agent Orchestration · Chain Execution · Session Lifecycle · Planning · State Management · Scalability · Maintainability · Extensibility · **Edit Safety (checkpoint/rollback)** · **Code-structural Context** · **Semantic Recall (seeded early)** · **Agent Feedback Loops**
> **Out of scope (engineering track):** AI provider/model internals, auth, billing, streaming transport, prompt wording. **Diff-review UI/UX and general product design are explicitly out of this engineering roadmap's scope but are flagged at the end as a required parallel track** — no amount of backend correctness substitutes for a trustworthy review surface.
> **Structure:** 8 phases, items R-101 → R-805 (26 items total: 22 original + 4 new). Every item carries priority, complexity (1–5), estimate, dependencies, breaking-change flag, affected modules, problem, root cause, current design, target design, justification, benefits, risks, required tests, acceptance criteria, and future expansion. Each phase closes with a Definition of Done.
>
> **What changed vs. the prior draft:** four items were added and pulled forward rather than parked in Phase 8, because they are the difference between "clean architecture" and "an editor people trust the way they trust Antigravity/Cursor/Windsurf": **R-106** (checkpoint/rollback — undo after the fact, not just consent before), **R-205** (structural/symbol code understanding), **R-206** (semantic retrieval seeded early as a small opt-in source, with the full layered version still landing in Phase 8 as R-802), and **R-504** (agent runs tests/commands and iterates on real feedback instead of guessing).

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
                    │  SafeReader,   │   │ live run       │  │  per-run FIFO   │
                    │  CheckpointLog)│   └────────┬───────┘  └──┬──────────────┘
                    └───────┬────────┘            │             │
                            │            ┌────────▼───────────┐ │  ┌───────────────┐
              ┌─────────────▼───────┐    │  Runner protocol   │ │  │ WS Adapter    │
              │   ContextEngine     │    │ Direct │ Chain     │ └─▶│ (only place   │
              │  Mention/Keyword/   │    │ Agent  │ Delegate  │    │  ws.send is   │
              │  Structure/History/ │    └────────┬───────────┘    │  allowed)     │
              │  Symbol/Semantic    │             │                └───────────────┘
              │  sources → Bundle   │    ┌────────▼───────────┐
              │  → ContextBudget    │    │  ApprovalGate      │
              └─────────────┬───────┘    │ auto/interactive/  │
                            │            │ deny               │
              ┌─────────────▼───────┐    └────────┬───────────┘
              │ ConversationMemory  │             │
              │ JSONL store + meta  │    ┌────────▼───────────┐
              │ window() + summary  │    │ CheckpointManager  │
              └─────────────────────┘    │ snapshot / diff /  │
                                          │ rollback(run_id)   │
                                          └────────────────────┘
```

**Key shifts from the original codebase:**
1. Module-level mutable state → `AppContext` + per-connection `SessionContext`.
2. Inline 200-line context block in `server.py` → `ContextEngine` with pluggable sources (mention, keyword, structure, history, **symbol, semantic**).
3. Silent auto-apply in `finally` → explicit `ApprovalGate` (consent *before* write) **plus `CheckpointManager` (undo *after* write)** — consent and reversibility are two different guarantees and the system needs both.
4. One dead `_active_chain_run` guard → `ExecutionRegistry` with cancellable `RunTicket`s.
5. Four ad-hoc dispatch paths → one `Runner` protocol.
6. Monolithic JSON session files (O(n²) append) → JSONL + meta sidecar.
7. Two conflicting strategy vocabularies → `RoutingTier` × `ExecutionStrategy` with a `STRATEGY_TABLE`.
8. Secrets (`.env`) readable by context → `SafeReader` boundary.
9. **New:** name-only file matching → symbol-aware structural index (R-205).
10. **New:** zero relevance-based recall → a small, budgeted, opt-in semantic source seeded in Phase 2 (R-206), matured into full layered memory in Phase 8 (R-802).
11. **New:** agents write code blind to whether it runs → agents can execute project commands/tests and read the result before finishing (R-504).

---

# PHASE 1 — Stop the Bleeding: Correctness & Safety (Week 1–2)

Goal: eliminate defects that corrupt state, violate contracts, or apply changes without consent — **and make every applied change reversible.** No new product features yet.

---

## R-101 — Remove the Dead `_active_chain_run` Guard; Introduce ActiveRunHolder

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none · **Affected:** `server.py`
- **Problem:** `_active_chain_run` (L82) is set at L403 but the guard at L470 checks it *after* the branch that would have needed it — it never blocks a concurrent run. Two chains can interleave file writes.
- **Root cause:** Guard added post-hoc without tracing dispatch order; no tests exist to catch it.
- **Target design:** `ActiveRunHolder` — lock-protected `acquire(run_id)/release(run_id)/current()`, checked *before* dispatch. Superseded later by R-105.
- **Benefits:** Deterministic single-run invariant; testable seam.
- **Required tests:** acquire/release/double-acquire unit; two WS `run_chain` frames → second gets `busy`.
- **Acceptance criteria:** guard flag deleted; concurrent-run test green.
- **Future expansion:** replaced by ExecutionRegistry (R-105).

## R-102 — AppContext Composition Root; Kill Stale-Reference Project Switching

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101 · **Affected:** `server.py`, `chain/bridge.py`, `actions/*`
- **Problem:** `api_switch_project` rebuilds only some globals; five consumers hold stale references to the old project's managers; `api_switch_model` pokes private attributes on three objects.
- **Target design:** `AppContext` dataclass owning `ProjectHandle` (path, FileManager, SafeReader, index slot); all consumers resolve `ctx.project.fm` at call time, never cache it. Switch becomes one atomic pointer swap.
- **Benefits:** Switch is one-line correct; components become unit-testable with a fake context.
- **Required tests:** switch E2E (create file in A, switch to B, mention resolution sees only B); id()-asserted swap atomicity.
- **Acceptance criteria:** zero module-level component globals; private-attribute pokes deleted.
- **Future expansion:** enables per-connection `SessionContext` (R-701).

## R-103 — Fix the DelegateBridge ↔ Provider Contract Violation

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** none (parallel with R-101) · **Affected:** `chain/delegate.py`, `providers/base.py`
- **Problem:** `delegate.py` passes `list[Message]` into `send(prompt: str, ...)`; works only because one provider duck-types it — latent crash on any strict provider in the fallback chain.
- **Target design:** convert at call sites (last message → `prompt`, rest → `history`); `ProviderContractTest` mixin every provider must pass; mypy gate on `chain/` and `providers/`.
- **Required tests:** contract mixin against `FakeProvider`; delegate E2E.
- **Acceptance criteria:** mypy clean; contract suite green for every registered provider.
- **Future expansion:** contract harness reused by R-501 Runner protocol.

## R-104 — ApprovalGate: End Silent Auto-Apply (Consent *Before* the Write)

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Yes, intentionally
- **Dependencies:** R-102 · **Affected:** `chain/bridge.py` (finally-block), `chain/agent_loop.py`, `server.py`, `config.yaml`
- **Problem:** `ChainBridge`'s `finally` block applies edits unconditionally, even on failed/partial runs, while `config.yaml` says `auto_execute: false`. Agent mode has a separate, inconsistent approval mechanism. One of the two paths has effectively no consent.
- **Target design:** single `ApprovalGate` service — modes `auto | interactive | deny`; every write becomes an `ApprovalRequest` (diff, paths, run_id); `interactive` blocks on a WS verdict with timeout→deny; `finally` may only *stage*, never apply.
- **Required tests:** matrix (auto/interactive-accept/interactive-reject/deny × chain/agent); crash-mid-chain leaves zero partial writes.
- **Acceptance criteria:** no `apply` reachable from any failure path; `auto_execute:false` provably blocks writes.
- **Future expansion:** per-path policies (auto-approve formatting, gate deletes) — layers on top of R-106's rollback as the second safety net.

## R-105 — ExecutionRegistry + RunTicket (Cancellation That Works)

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** Internal only
- **Dependencies:** R-101, R-102 · **Affected:** `server.py`, `chain/executor.py`, `chain/delegate.py`
- **Problem:** No way to cancel a running chain/agent/delegate; disconnecting the client orphans the work; delegate has zero cancellation support at all.
- **Target design:** `ExecutionRegistry` maps `run_id -> RunTicket` (`cancel()`, `is_cancelled`, `mode`); executors poll at step/iteration boundaries; WS gains `list_runs`/`cancel_run`.
- **Required tests:** cancel mid-chain/mid-agent-iteration/mid-delegate-stage; registry reflects reality after reconnect.
- **Acceptance criteria:** every dispatch path allocates a ticket; cancel E2E green for all modes.
- **Future expansion:** tickets carry lease metadata for the worker pool (R-804).

## R-106 — Checkpoint & Rollback: Consent *After* the Write, Too — **[NEW]**

- **Priority:** Critical · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No (additive; changes nothing that already worked)
- **Dependencies:** R-102, R-104 (rollback needs a stable project handle and a gate to know what actually got applied) · **Affected:** new `core/checkpoint.py`, `chain/action_applier.py`, `server.py`, WS protocol
- **Problem:** Even with `ApprovalGate` gating consent *before* a write, there is no way to undo a change once it lands — not a partial-run write, not even a fully-approved multi-file edit that turns out to be wrong five minutes later. Every competing AI editor treats "undo the agent's last edit" as table stakes; this system has no equivalent at any layer (git is not a substitute — most target repos aren't guaranteed to be clean git working trees when the agent runs, and users should not need to know git to recover from an agent mistake).
- **Root cause:** The team scoped "safety" as pre-write consent only; post-write reversibility was never treated as a separate requirement.
- **Current design:** No checkpoint concept exists; a bad multi-file agent edit can only be manually reverted file-by-file by the user.
- **Target design:** `CheckpointManager` — before any `ApprovalGate`-approved batch is applied, snapshot the pre-write content of every touched path (content-addressed, deduplicated against unchanged files) into a `CheckpointLog` keyed by `run_id`; after apply, the checkpoint records the full before/after diff. WS gains `rollback_run(run_id)` (restores every touched file to its pre-run content, refusing — with a clear conflict report — if a file was independently modified since) and `rollback_file(run_id, path)` for partial undo. Checkpoints follow the same `RetentionPolicy` as run artifacts (R-305) so they don't grow unbounded.
- **Justification:** This is the single highest product-trust item in the whole roadmap — it is what lets a user say "let the agent touch five files" without fear, because a bad outcome is one click from gone.
- **Benefits:** Turns every agentic edit into a reversible experiment instead of a one-way door; makes `ApprovalGate`'s `auto` mode genuinely safe to enable, because mistakes are recoverable even without a human in the loop beforehand.
- **Risks:** Storage growth from snapshots — content-addressed dedup plus retention policy bounds it; conflicting external edits during rollback — detected via hash comparison and reported, never silently overwritten.
- **Required tests:** rollback restores exact pre-run byte content across a 5-file batch; partial `rollback_file` leaves siblings untouched; rollback refuses cleanly on independent external modification; retention sweep bounds checkpoint storage across 50 fixture runs.
- **Acceptance criteria:** every `ApprovalGate`-applied batch has a corresponding checkpoint; `rollback_run` and `rollback_file` both pass their integration tests; UI-facing WS frame documents the rollback affordance.
- **Future expansion:** named/pinned checkpoints ("save point before refactor"); checkpoint diff viewer as part of the (out-of-scope) review UI track.

---

## Phase 1 — Definition of Done
- [ ] No module-level mutable run/project state in `server.py`.
- [ ] Project switch E2E green; stale-reference consumers migrated.
- [ ] Provider contract enforced by mypy + shared test mixin.
- [ ] All writes flow through ApprovalGate; `auto_execute: false` blocks writes in every mode.
- [ ] Every run has a ticket; cancellation works for chain, agent, and delegate.
- [ ] **Every applied batch has a checkpoint; rollback (full and per-file) is tested and reachable from the WS API.**
- [ ] pytest bootstrap + FakeProvider fixture exist and run in CI-equivalent script.

---

# PHASE 2 — Context Engine (Week 3–4)

Goal: extract the inline 200-line context block into a real subsystem with deduplication, budgeting, a secret boundary — **and give it structural and semantic awareness from the start, not as a Phase 8 afterthought.**

---

## R-201 — Extract ContextEngine with Pluggable Sources

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** Internal only
- **Dependencies:** R-102 · **Affected:** `server.py` (L606–758), new `context/` package
- **Problem:** ~200 lines of inline context collection in the WS handler; per-word `rglob` scans; a constant that lies about itself (`MAX_MENTIONED = 100 # حد أقصى 10 ملفات`); three divergent re-implementations across direct/chain/agent paths.
- **Target design:** `ContextEngine.gather(request) -> ContextBundle` orchestrating `ContextSource` implementations (`MentionSource`, `KeywordSource`, `StructureSource`, `HistorySource`, and — new — `SymbolSource` R-205, `SemanticSource` R-206). Single tree scan per request, cached.
- **Required tests:** goldens for 6 representative messages match legacy output; one-scan-per-request assertion.
- **Acceptance criteria:** inline block deleted; misleading constant fixed; goldens green.
- **Future expansion:** every later context feature is a new source, never a handler edit.

## R-202 — ContextBundle: Hash-Dedup + Provenance

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-201 · **Affected:** `context/`, `chain/executor.py`
- **Problem:** The same file content is injected 2–3× per prompt across mention/keyword/prefetch paths; map_reduce duplicates wholesale.
- **Target design:** `ContextBundle` keyed by content hash; repeat insertion becomes a reference note, not a copy; items carry provenance (`source`, `reason`, `tier`).
- **Required tests:** dedup unit; map_reduce prompt size ≥40% smaller on fixture.
- **Acceptance criteria:** no identical content body appears twice in any generated prompt.

## R-203 — ContextBudget with Priority Tiers

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** No
- **Dependencies:** R-202 · **Affected:** `context/`, three hardcoded char-limit sites
- **Problem:** Truncation is raw character count at three inconsistent limits; a critical mentioned file can be cut while boilerplate survives.
- **Target design:** `ContextBudget(token_limit)` packs by tier: `must_have` → `high` → `normal` → `opportunistic`; overflow drops opportunistic first; must_have overflow triggers summarization, never truncation.
- **Required tests:** property test — must_have never dropped while opportunistic present.
- **Acceptance criteria:** all char limits deleted; budget applied in every prompt path.

## R-204 — SafeReader: The Secret Boundary

- **Priority:** Critical · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral, intended
- **Dependencies:** R-102 · **Affected:** file reading paths, `_TEXT_EXTENSIONS`
- **Problem:** `.env` is in `_TEXT_EXTENSIONS`; a keyword scan or mention can inject live API keys into a third-party model prompt.
- **Target design:** `SafeReader` wraps every context-bound read; denylist + entropy sniff; denied reads return a redaction stub; per-file user override required to bypass.
- **Required tests:** `.env` mention → redaction stub; CI grep — no `open()`/`read_text()` on context paths outside `SafeReader`.
- **Acceptance criteria:** `.env` unreachable from any prompt in E2E.

## R-205 — Symbol-Aware Context (Structural Understanding) — **[NEW]**

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Breaking:** No
- **Dependencies:** R-201, R-702 (benefits from but does not strictly require the index; can start on a smaller in-memory structure) · **Affected:** new `context/symbol_index.py`, `ContextEngine`
- **Problem:** Every context source in the original design matches on **filenames and keywords only**. There is no notion of "this function calls that function" or "this class is defined here and used in these twelve places" — the system cannot answer "who else uses this" without a keyword grep that returns noise. This is the single biggest quality gap versus structural-aware competitors.
- **Root cause:** The codebase was never asked to parse code as code — only as text.
- **Current design:** Regex/keyword matching over raw file text.
- **Target design:** `SymbolIndex` built with `tree-sitter` grammars for the project's dominant languages (start with the 3–4 most common in target repos; add more incrementally): extracts function/class/symbol definitions, references, and import graphs per file; refreshed by the same write-hooks as `ProjectIndex` (R-702). `SymbolSource` (a `ContextSource`) resolves "definition of X", "callers of X", and "file imports" as `high`-tier context items — a strict quality upgrade over keyword matching for the same budget cost.
- **Justification:** This is what separates "reads nearby files" from "understands the codebase" — directly determines whether generated edits respect existing call patterns instead of guessing.
- **Benefits:** Mentions of a function name resolve to its actual definition and call sites, not every file that happens to contain the string; agent edits are less likely to break unseen call sites.
- **Risks:** Parser coverage gaps for less-common languages — `SymbolSource` degrades gracefully to `KeywordSource` behavior for unparsed files, never blocks the request.
- **Required tests:** golden — "who calls function X" on a fixture project returns the exact call-site set; graceful degradation test on an unsupported file extension; perf — index build stays under a defined ceiling on a 2k-file fixture.
- **Acceptance criteria:** `SymbolSource` live in `ContextEngine`; degrade-gracefully test green; measurable precision improvement over keyword-only on a "find usages" golden set.
- **Future expansion:** cross-file refactor-impact analysis; feeds a future "safe rename" agent tool.

## R-206 — Semantic Retrieval, Seeded Early — **[NEW, moved forward from Phase 8]**

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-201, R-203 · **Affected:** new `context/semantic_source.py`, `ContextEngine`
- **Problem:** Without any relevance-based recall, context quality is capped by exact-match mentions and keywords; a message like "how did we handle auth last time" has no path to the relevant code or decision at all if the words don't literally match. Parking this capability until Phase 8 (as the original draft did) means the product ships an entire development cycle without a core quality lever competitors already have.
- **Root cause:** No embedding infrastructure exists; it was scoped as a "nice to have, later" item.
- **Current design:** None.
- **Target design:** a deliberately **small, seeded** version — not the full layered memory system (that is still R-802 in Phase 8, which builds on this foundation): embed file chunks and recent conversation turns using a single pluggable embedding call; `SemanticSource` retrieves top-k relevant items and injects them at `opportunistic` tier only (never displaces `must_have`/`high` content, per R-203's tier rules); retrieval is skipped (not blocking) if the embedding call is slow or fails. This is intentionally the minimum viable version — full episodic/semantic layering with provenance and staleness tracking is deferred to R-802.
- **Justification:** Relevance-based recall is a top-3 quality lever; shipping a minimal version early is far better than shipping none until Phase 8, and the architecture (ContextSource + tiered budget) already supports it with almost no new machinery.
- **Benefits:** "How did we do X" style questions get a real answer path from turn 1 of the project, not after 14+ weeks.
- **Risks:** Embedding cost/latency — async with a hard timeout and skip-on-timeout; retrieval noise — strict `opportunistic` tier keeps it cheap to be wrong.
- **Required tests:** retrieval precision on a small fixture (query about an early decision resolves the right chunk); timeout-skip does not block the response; budget-tier compliance (never displaces must_have).
- **Acceptance criteria:** `SemanticSource` live behind a config flag (default on, cheap to disable); skip-on-timeout test green.
- **Future expansion:** R-802 (Phase 8) upgrades this into the full working/episodic/semantic layered system with provenance and cross-session persistence (R-805).

---

## Phase 2 — Definition of Done
- [ ] Inline context block deleted from `server.py`; goldens prove parity.
- [ ] No duplicate content bodies in any prompt; provenance recorded.
- [ ] Char-limit truncation replaced by tiered token budget everywhere.
- [ ] Secrets unreachable by any context path; CI guard in place.
- [ ] **Symbol-aware "find definition / find usages" resolves correctly on the fixture project, with graceful degradation for unparsed languages.**
- [ ] **A minimal semantic source is live, budget-compliant, and skip-safe on timeout.**

---

# PHASE 3 — Memory & Session Lifecycle (Week 5–6)

Goal: replace monolithic JSON sessions with an append-friendly store, give conversation memory a real API, and bind sessions to projects.

---

## R-301 — JSONL Session Store + Meta Sidecar

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Storage format (migration provided)
- **Problem:** `append_message` rewrites the entire session JSON per message — O(n²) over a session's lifetime; a crash mid-rewrite corrupts the whole file.
- **Target design:** `sessions/<id>.jsonl` (O(1) append) + `sessions/<id>.meta.json` sidecar; migration script; sessions gitignored.
- **Required tests:** benchmark (1k appends p95 <5ms); torn-write recovery; migration round-trip fidelity.
- **Acceptance criteria:** append is O(1); migration lossless; sessions untracked in git.

## R-302 — ConversationMemory Facade

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days · **Breaking:** Internal only
- **Dependencies:** R-301 · **Problem:** three call sites slice raw message lists with different ad-hoc rules.
- **Target design:** `ConversationMemory` owning the store: `append`, `window(policy)`, `summary()`, `search()` stub for R-802. All consumers migrate to `window()`.
- **Required tests:** window policy units; consumer goldens.
- **Acceptance criteria:** zero raw-slice history access outside the facade.

## R-303 — Session ↔ Project Binding

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** Behavioral, guarded
- **Dependencies:** R-301, R-102 · **Problem:** a session started on project A keeps accumulating after switching to B; history contaminates future context.
- **Target design:** `project_id` stamped in session meta; switch triggers `warn`/`fork`/`block` policy (default `warn_only`).
- **Required tests:** switch-mid-session E2E per policy.
- **Acceptance criteria:** every new session records binding; policy enforced.

## R-304 — Tiered Windowing + Async Summarization

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-302, R-203 · **Problem:** long conversations either overflow or amnesia abruptly.
- **Target design:** recent window verbatim → rolling async summary of the middle band → drop; summary regenerated off the hot path.
- **Required tests:** 100-turn simulation stays under budget and retains a fact from turn 5.
- **Acceptance criteria:** summarization never blocks the hot path. **Fact-retention gate: a fact stated at turn 5 remains represented (verbatim or in summary) and answerable at turn 100** — this is the acceptance bar, not just a nice-to-have test.

## R-305 — Truthful Snapshots + Retention GC

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 1 day · **Breaking:** No
- **Dependencies:** R-105 · **Problem:** `ProjectSnapshot` records empty file-hash maps; sessions and (from R-106) checkpoints accumulate forever.
- **Target design:** real content hashes at snapshot time; `RetentionPolicy` (age/count/pinned) sweeps sessions, run artifacts, **and checkpoints** on startup and daily.
- **Required tests:** hash correctness; GC policy matrix; pinned survives GC.
- **Acceptance criteria:** no empty hash maps; GC runs and logs; sessions out of git.

---

## Phase 3 — Definition of Done
- [ ] All sessions on JSONL + meta; O(1) append verified.
- [ ] Single memory facade; zero raw slicing at consumers.
- [ ] Sessions bound to projects; mismatch policy live.
- [ ] 100-turn session coherent within budget; summarizer off hot path.
- [ ] Real snapshot hashes; retention GC covers sessions, artifacts, and checkpoints.

---

# PHASE 4 — Routing & Planning Honesty (Week 7–8)

Goal: one strategy vocabulary, explainable routing, and a capacity model that tells the truth.

---

## R-401 — Unify the Two Strategy Vocabularies

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 2 days
- **Problem:** orchestrator speaks 6 strategy names, router speaks 4; the mapping is implicit and mismatches silently misroute.
- **Target design:** `RoutingTier` × `ExecutionStrategy` enums joined by an explicit `STRATEGY_TABLE`; `assert_never` on gaps.
- **Required tests:** table completeness; 30-decision golden parity — 30 real routing decisions recorded pre-refactor (covering all 6 orchestrator + 4 router strategies) must reproduce identically post-refactor.
- **Acceptance criteria:** zero free-string strategy comparisons; **the 30-decision golden corpus is green** (not just "run", but a hard gate on the PR).

## R-402 — Explainable Routing: RoutingDecision Record

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-401
- **Problem:** routing outcomes are unexplainable; thresholds are inline magic numbers.
- **Target design:** `RoutingDecision` record (scores, thresholds, matched signals) emitted per run; thresholds move to config.
- **Required tests:** monotonicity property (higher complexity never routes lighter absent a budget downgrade).
- **Acceptance criteria:** every routed request has a persisted decision record.

## R-403 — Honest CapacityModel + Circuit Breaker

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-401
- **Problem:** `reset_failures()` has zero callers — a failed provider stays dead until restart; capacity math is fictional account-counting.
- **Target design:** per-provider circuit breaker (closed→open→half-open→closed); `CapacityModel` replaces account-count fiction.
- **Required tests:** breaker state-machine; recovery integration.
- **Acceptance criteria:** providers self-heal without restart.

---

## Phase 4 — Definition of Done
- [ ] One strategy registry; parity verified against 30 recorded decisions.
- [ ] Every routing decision recorded and explainable.
- [ ] Circuit breaker live; sticky-failure code deleted.

---

# PHASE 5 — Agent Orchestration (Week 9–10)

Goal: one Runner protocol for all execution modes, a declarative agent fleet, knowledge that stops re-paying for itself — **and agents that can check their own work.**

---

## R-501 — Runner Protocol: One Dispatch Path

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days
- **Dependencies:** R-102, R-103, R-104, R-105 · **Problem:** four hand-rolled dispatch paths with divergent error handling; the agent path polls the WS as a workaround.
- **Target design:** `Runner` protocol (`DirectRunner`/`ChainRunner`/`AgentRunner`/`DelegateRunner`) with a shared contract test harness; dispatch becomes one line.
- **Required tests:** contract harness; per-mode parity E2E; cancellation matrix.
- **Acceptance criteria:** polling loop deleted; all runners pass the contract suite.

## R-502 — Declarative Agent Manifest

- **Priority:** Medium · **Complexity:** 2/5 · **Estimate:** 2 days · **Dependencies:** R-501
- **Problem:** 21 agents hardcoded to file paths in Python source; no hot reload.
- **Target design:** `agents/manifest.yaml`, schema-validated, mtime hot-reload; `ROLE_MAP` deleted.
- **Required tests:** schema validation; hot-reload integration; 21-agent parity.
- **Acceptance criteria:** manifest is the single source of truth. **Parity gate: all 21 legacy `ROLE_MAP` agents resolve identically through the manifest** — a diff in any of the 21 blocks the migration.

## R-503 — Knowledge Accumulator: Dedup + Delta Prompts

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-202, R-203
- **Problem:** the accumulator re-injects the entire knowledge blob every iteration — quadratic token cost.
- **Target design:** knowledge becomes a `ContextBundle` view; per-iteration prompt is the delta plus a summary of the stable core.
- **Required tests:** token-cost curve flat within 15% across 8 iterations.
- **Acceptance criteria:** no full re-injection after the first send.

## R-504 — Terminal/Test Feedback Loop for Agents — **[NEW]**

- **Priority:** High · **Complexity:** 3/5 · **Estimate:** 3 days · **Breaking:** No
- **Dependencies:** R-105 (needs a cancellable ticket for long-running commands), R-501 (needs the Runner protocol so this is one capability, not four bespoke ones), R-106 (a command that mutates the workspace, e.g. a codemod script, must be checkpointable too) · **Affected:** `chain/agent_tools.py`, `AgentRunner`, agent prompt templates
- **Problem:** Agents propose code changes without any way to verify them. There is no tool for "run the test suite", "run the linter", or "execute this script and read stdout/stderr" — an agent finishes a task believing it succeeded purely because generation completed, not because anything was checked. This is the gap between "writes code" and "writes code that works."
- **Root cause:** `cmd_runner` exists in the codebase for direct user-invoked commands but was never exposed as an agent tool with a feedback path back into the loop.
- **Current design:** `AgentTools` exposes file read/write/search but no execute-and-observe primitive; the agent loop has no "did it actually work" checkpoint.
- **Target design:** a `run_command` agent tool (allowlisted commands per project — test runners, linters, type checkers, build scripts — configurable, never arbitrary shell by default) that executes via the existing `cmd_runner`, captures stdout/stderr/exit code, and feeds the result back into the next agent iteration as a `high`-tier context item. The agent's system prompt is updated so verification is a normal step, not an afterthought: for code-editing tasks where a test command is configured, the loop is expected to run it before declaring success. Long-running commands get a `RunTicket`-linked cancellation checkpoint (R-105) and a timeout. Any file changes a command makes (e.g. an autoformatter) route through the same `ApprovalGate`/`CheckpointManager` path as any other agent write (R-104/R-106) — there is no separate, ungated way for a command to mutate the workspace.
- **Justification:** Verification loops are what make autonomous multi-file agent edits trustworthy enough to actually rely on; without this, every "done" claim from the agent is an unfalsifiable guess.
- **Benefits:** Measurable reduction in agent-reported-success-but-actually-broken outcomes on a fixture project with a real test suite; agents that self-correct within a run instead of shipping a broken first attempt.
- **Risks:** Arbitrary command execution is a security surface — mitigated by a project-level allowlist (configured, not agent-chosen) and by routing any resulting writes through the existing approval/checkpoint machinery; runaway processes — bounded by ticket-linked timeout and cancellation.
- **Required tests:** allowlist enforcement (non-allowlisted command rejected with a clear error, never silently run); fixture project where an agent's first attempt fails a test and the second iteration, informed by the failure output, passes it; timeout/cancellation of a hung command; command-triggered file writes are gated and checkpointed identically to direct agent writes.
- **Acceptance criteria:** `run_command` tool live and allowlist-enforced; the fail-then-fix fixture test is green; no command-triggered write bypasses `ApprovalGate`/`CheckpointManager`.
- **Future expansion:** structured test-result parsing (pass/fail counts, specific failing assertions) as a richer context item; auto-retry budget tied to `ExecutionRegistry`.

---

## Phase 5 — Definition of Done
- [ ] Four runners behind one protocol; polling loop gone.
- [ ] Agent fleet defined in manifest; hot-reload works.
- [ ] Agent iteration token cost flat.
- [ ] **Agents can execute allowlisted project commands and use the real output to self-correct within a run; all resulting writes remain gated and checkpointed.**

---

# PHASE 6 — Chain Engine Maturity (Week 10–11)

Goal: make the executor's promises real — resume, context policy, parallelism — and give the system a nervous system.

---

## R-601 — Wire Crash Resume or Delete It

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-105, R-305
- **Problem:** `can_resume()`/`load_state()` have zero callers — dead machinery that costs I/O and delivers nothing.
- **Target design:** wire it end-to-end (startup scan, `resume_run`/`discard_run`, hash-drift refusal via R-305) **or delete it entirely** — no fictional middle ground.
- **Required tests:** kill-after-step-2-of-5 → resume completes 3–5 exactly once; hash-mismatch refusal.
- **Acceptance criteria:** resume reachable from WS, or machinery fully deleted.

## R-602 — Enforce ChainStep Context Policy

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-202, R-203
- **Problem:** `context_policy` is parsed and stored but never enforced — every step gets full ancestor output regardless.
- **Target design:** `build_prompt` honors `full`/`summary`/`minimal` render modes.
- **Required tests:** step-5 prompt ≥50% smaller under `summary` on a 5-step fixture.
- **Acceptance criteria:** policy provably alters rendered prompts.

## R-603 — Bounded Parallel Step Execution

- **Priority:** Medium · **Complexity:** 4/5 · **Estimate:** 3 days · **Dependencies:** R-105, R-403, R-602
- **Problem:** the scheduler computes the full ready set but executes `ready[0]` only — strictly sequential despite an advertised `max_parallel_steps`.
- **Target design:** `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)`; state mutation funneled through one guarded `apply_step_result()`.
- **Required tests:** `parallel=1` legacy-identical; ≥3× speedup benchmark at `parallel=4`; stress test with injected failures.
- **Acceptance criteria:** ready set fully utilized up to the cap.

## R-604 — EventBus: Typed Events, Per-Run FIFO

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 2 days · **Dependencies:** R-501
- **Problem:** `ws.send` sprinkled everywhere with inconsistent frame shapes; the agent approval flow abuses a polling receive-loop.
- **Target design:** in-process `EventBus` with typed events; a single WS Adapter is the only socket writer.
- **Required tests:** per-run FIFO ordering; adapter frame-parity snapshots vs. legacy.
- **Acceptance criteria:** zero `ws.send` outside the adapter (CI grep).

---

## Phase 6 — Definition of Done
- [ ] Resume works end-to-end, or is deliberately deleted.
- [ ] Context policy provably shapes prompts.
- [ ] Parallel execution real, benchmarked, and legacy-identical at `parallel=1`.
- [ ] All events flow through EventBus; frame parity verified.

---

# PHASE 7 — Platform Hardening (Week 12–13)

Goal: multi-client correctness, fast project awareness, a repository that tells the truth.

---

## R-701 — Session-Scoped State: SessionContext per WS Connection

- **Priority:** High · **Complexity:** 4/5 · **Estimate:** 4 days · **Dependencies:** R-102, R-105, R-604 + Phases 1–3 complete
- **Problem:** a second browser tab silently shares and clobbers the first tab's project/model/session.
- **Target design:** `SessionContext` per connection layered over shared `AppContext`; lint rule bans module-level mutable handler state.
- **Required tests:** two-tab isolation E2E.
- **Acceptance criteria:** zero conversation-scoped globals remain.

## R-702 — ProjectIndex: Replace rglob Storms

- **Priority:** Medium · **Complexity:** 3/5 · **Estimate:** 3 days · **Dependencies:** R-201
- **Problem:** every mention/keyword lookup walks the tree with `rglob` — O(files) per message.
- **Target design:** in-memory inverted index (stems/extensions/path-trie), write-hook invalidated; feeds R-205's symbol index build too.
- **Required tests:** <10ms mention resolution on a 5k-file fixture.
- **Acceptance criteria:** zero `rglob` in any per-message path.

## R-703 — Repo Hygiene & Real Test Infrastructure

- **Priority:** High · **Complexity:** 2/5 · **Estimate:** 2 days
- **Problem:** README claims "125/125 tests passing" with no `tests/` directory; 43 session files committed to git; config and code disagree on defaults.
- **Target design:** real pytest + CI with a coverage ratchet from 40%; sessions purged from git history; config wins over hardcoded defaults.
- **Required tests:** CI pipeline itself is the test.
- **Acceptance criteria:** README contains zero unverifiable claims.

---

## Phase 7 — Definition of Done
- [ ] Two simultaneous clients fully isolated.
- [ ] Mention/keyword resolution index-backed; zero hot-path `rglob`.
- [ ] History purged of session data; README truthful; CI enforced.

---

# PHASE 8 — Extensibility Horizon (Week 14+)

Goal: open the architecture — plugins, the full layered memory system, pluggable planners, horizontal workers, persistent project memory. Every item here assumes the seams built in Phases 1–7, **including the semantic seed planted early in R-206.**

---

## R-801 — Strategy Plugin Registry

- **Priority:** Low · **Complexity:** 3/5 · **Estimate:** 3 days · **Dependencies:** R-401, R-501
- **Target design:** entry-point plugin discovery for strategies/runners/context sources; broken plugins quarantined, never fatal; capability-scoped API (never raw FileManager).
- **Acceptance criteria:** demo plugin ships a working strategy; quarantine test green.

## R-802 — Layered Memory: Working / Episodic / Semantic (Full Version)

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Dependencies:** R-302, R-304, **R-206**
- **Problem:** R-206 shipped a minimal, budget-safe semantic seed in Phase 2; it has no episodic layer, no provenance tracking, and no cross-session persistence.
- **Target design:** upgrade R-206's `SemanticSource` into three full layers — working (R-302's window), episodic (turn summaries with range provenance), semantic (the R-206 index, now with provenance and staleness tracking) — behind the same `ConversationMemory` facade.
- **Required tests:** causal-value test — a decision from turn 10 is retrieved and cited when re-queried at turn 80.
- **Acceptance criteria:** three layers live behind an unchanged facade.

## R-803 — Pluggable Planners

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 4 days · **Dependencies:** R-402, R-501
- **Target design:** `Planner` protocol — `HeuristicPlanner` (extracted current logic), `LLMPlanner` (schema-validated), `HybridPlanner`; malformed LLM output always falls back to heuristic.
- **Acceptance criteria:** planner swappable via config; fallback path proven.

## R-804 — Worker Pool: Horizontal Execution

- **Priority:** Low · **Complexity:** 5/5 · **Estimate:** 8 days · **Dependencies:** R-501, R-603, R-604, R-701
- **Target design:** Redis-backed registry/bus; per-project TTL leases; byte-identical WS frame parity between worker and in-process execution is the release gate.
- **Acceptance criteria:** runs execute on workers with zero client-visible difference.

## R-805 — Persistent Project Memory

- **Priority:** Low · **Complexity:** 4/5 · **Estimate:** 5 days · **Dependencies:** R-303, R-702, R-802
- **Target design:** per-project fact store (explicit `remember_fact` tool + post-run distillation), provenance-tracked, staleness-flagged via `ProjectIndex` drift, user-editable.
- **Acceptance criteria:** a second session on a fixture project answers a conventions question without re-reading files.

---

## Phase 8 — Definition of Done
- [ ] Demo plugin installs and runs; quarantine proven.
- [ ] Full layered memory upgrades the Phase-2 seed with provenance and cross-session persistence.
- [ ] Planner swappable via config; LLM planner fallback-safe.
- [ ] Worker-mode parity suite green.
- [ ] Project memory inspectable, provenance-tracked, staleness-aware.

---

# Explicitly Deferred: The Review/Diff UI Track

This roadmap is an engineering-correctness track and deliberately excludes UI/UX. That said: **R-104 (ApprovalGate) and R-106 (Checkpoint/Rollback) are only as trustworthy as the surface a user reviews them through.** A backend that computes perfect diffs and perfect rollback points still needs:
- a diff-review panel that renders `ApprovalRequest` payloads clearly, per file, with accept/reject at both the batch and per-file granularity;
- a visible, one-click path to `rollback_run`/`rollback_file` from R-106, not just an API;
- a way to see `RoutingDecision` (R-402) and `CapacityModel` (R-403) state so the "why did it do that" question has a UI answer, not just a log line.

None of this is scoped into R-101…R-805 above. It should be tracked as a parallel design/frontend workstream starting no later than Phase 1, since R-104 and R-106 are shipping consent and reversibility primitives in Week 1–2 that are inert without a surface to use them.

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
```

**Reading order for a new engineer:** Phase 1 in order (R-101→R-106) → R-201/R-204/R-205 → R-301/R-302 → then by team assignment.

**Totals:** 26 R-items · Critical: 6 · High: 12 · Medium: 12 · Low: 5.
