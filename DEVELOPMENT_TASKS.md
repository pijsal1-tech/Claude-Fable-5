# DEVELOPMENT TASKS — WebDev AI Editor

> Granular execution tasks (15–90 min each) derived from `MASTER_DEVELOPMENT_ROADMAP.md` items (R-xxx → T-xxx).
> Work tasks **strictly in dependency order**. One task = one commit.

---

## Verification Protocol (applies to EVERY task)

1. **Before starting:** confirm all dependency tasks are marked `✅ Done`; pull latest; run full test suite — must be green before you touch anything.
2. **During:** implement ONLY what the task scope says. Discovered extra work → file a new task, do not expand scope.
3. **Before marking done:** every checklist box checked; acceptance criteria demonstrated (paste evidence — test output / grep output — into Reviewer Notes); full suite green; no new lint errors.
4. **Never** mark a task done with failing tests, partial implementation, or unverified acceptance criteria.
5. **Commit format:** `type(scope): T-xxx description` (e.g., `fix(server): T-004 wire ActiveRunHolder into chain start`).
6. **Regression rule:** if a task breaks any previously-green test, fix or revert within the same task before proceeding.

**Status legend:** ☐ Not Started · 🔄 In Progress · ✅ Done · ⛔ Blocked

---

# PHASE 1 — Critical Correctness & Safety

### T-001 — Bootstrap test infrastructure (pytest + layout)
- **Description:** Create `tests/` with `conftest.py`, `pytest.ini`, install pytest + pytest-cov; add a canary test that imports `server`, `chain.models`, `actions.session_manager` successfully.
- **Reason:** Zero tests exist (README's "125/125" claim is false); every subsequent task requires a harness. (R-703 infra, pulled forward)
- **Priority:** Critical | **Complexity:** 1/5 | **Time:** 45 min
- **Dependencies:** None
- **Files to Modify:** `tests/__init__.py`, `tests/conftest.py`, `pytest.ini`, `requirements-dev.txt` (new)
- **Affected Modules:** none (additive)
- **Acceptance Criteria:** `pytest -q` runs and passes the canary; imports succeed without starting the server.
- **Implementation Checklist:** ☐ dirs/files created ☐ pytest configured ☐ canary imports pass
- **Testing Checklist:** ☐ `pytest -q` green locally
- **Regression Checklist:** ☐ server still starts manually
- **Documentation Checklist:** ☐ README test section corrected to reflect reality
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-002

### T-002 — FakeProvider + fixture project
- **Description:** Build `tests/fakes.py` `FakeProvider(BaseProvider)` (scripted responses, strict `send(prompt: str, ...)` type assertions) and `tests/fixtures/sample_project/` (~10 files incl. a `.env` with a dummy secret, nested dirs, one large file).
- **Reason:** All integration tests need a deterministic provider and a known workspace; the strict FakeProvider is also the trap that proves the R-103 delegate bug.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-001
- **Files to Modify:** `tests/fakes.py`, `tests/fixtures/sample_project/*`
- **Affected Modules:** none (additive)
- **Acceptance Criteria:** FakeProvider passes an initial provider-contract smoke test; fixture project loads via `FileManager`.
- **Implementation Checklist:** ☐ FakeProvider with type asserts ☐ scripted response queue ☐ fixture project committed
- **Testing Checklist:** ☐ contract smoke test green
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ fakes usage documented in tests/README.md
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-003

### T-003 — ActiveRunHolder class + unit tests (R-101)
- **Description:** Create `core/run_holder.py`: `ActiveRunHolder` with `threading.Lock`, `acquire(run_id) -> bool`, `release(run_id)`, TTL auto-expiry, `force_release()`.
- **Reason:** The `_active_chain_run` guard (server.py L82) is dead — assigned once, never updated; concurrent chains can interleave writes.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-001
- **Files to Modify:** `core/__init__.py`, `core/run_holder.py`, `tests/test_run_holder.py`
- **Affected Modules:** new `core/`
- **Acceptance Criteria:** Unit tests: acquire, double-acquire rejected, release, TTL expiry, force_release — all green.
- **Implementation Checklist:** ☐ lock-protected state ☐ TTL ☐ force_release
- **Testing Checklist:** ☐ 5 unit cases green ☐ thread-safety test (2 threads race acquire)
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ docstrings
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-004

### T-004 — Wire ActiveRunHolder into chain start path (R-101)
- **Description:** Acquire in `ChainBridge.run()` entry, release in `finally`; WS `start_chain` returns structured `{"type":"error","code":"run_busy"}` on rejection. Delete dead `_active_chain_run` global and its two dead guards (server.py L82/L403/L470).
- **Reason:** Makes the single-run invariant real; removes the lying guard.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-003
- **Files to Modify:** `server.py`, `chain/bridge.py`, `tests/test_run_exclusion.py`
- **Affected Modules:** server, chain
- **Acceptance Criteria:** Integration test: two concurrent `start_chain` → second receives `run_busy`; grep shows `_active_chain_run` gone.
- **Implementation Checklist:** ☐ acquire/release wired ☐ run_busy frame ☐ dead global deleted
- **Testing Checklist:** ☐ concurrency integration test green
- **Regression Checklist:** ☐ single chain run still completes on fixture
- **Documentation Checklist:** ☐ WS protocol doc gains `run_busy`
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-005

### T-005 — Define AppContext + ProjectHandle (R-102)
- **Description:** Create `core/app_context.py`: `ProjectHandle` (fm, cmd_runner, root, project_id) and `AppContext` (provider_pool, active_provider property, project, session_manager, budget) with `switch_project(path)` / `switch_model(name)` atomic setters. No consumers migrated yet.
- **Reason:** Foundation for killing 13 module globals and stale-reference switching.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-001
- **Files to Modify:** `core/app_context.py`, `tests/test_app_context.py`
- **Affected Modules:** new core
- **Acceptance Criteria:** Unit: switch_project swaps ProjectHandle atomically (id() differs); switch_model updates active_provider property.
- **Implementation Checklist:** ☐ dataclasses ☐ atomic setters ☐ project_id = root-path hash
- **Testing Checklist:** ☐ unit tests green
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ module docstring with ownership rules ("resolve at call time, never cache")
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-006

### T-006 — Migrate main() wiring to AppContext (R-102)
- **Description:** Replace the 13 module-level component globals (server.py L71–96) and main() wiring (L1475–1614) with a single `ctx = AppContext(...)` built at startup; pass `ctx` into WS handler closure. Components still receive individual deps for now (adapter shims).
- **Reason:** Single composition root; prerequisite for consumer migration.
- **Priority:** Critical | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-005
- **Files to Modify:** `server.py`, `tests/test_wiring_smoke.py`
- **Affected Modules:** server
- **Acceptance Criteria:** Zero mutable component globals remain in server.py (grep); wiring smoke test exercises every WS message type against fixture project without error.
- **Implementation Checklist:** ☐ globals removed ☐ ctx built in main ☐ handlers read via ctx
- **Testing Checklist:** ☐ smoke test covers all WS message types
- **Regression Checklist:** ☐ manual server start + one chat round-trip
- **Documentation Checklist:** ☐ architecture note in README
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-007

### T-007 — Migrate stale-ref consumers to call-time resolution (R-102)
- **Description:** `AgentTools`, `ChainBridge`, `ContextBuilder`, `DelegateBridge`, `RequestRouter` stop caching `fm`/`cmd`/`provider` in `__init__`; they hold `ctx` and resolve `ctx.project.fm` / `ctx.active_provider` at call time.
- **Reason:** These cached refs are why `api_switch_project` leaves agents operating on the OLD project.
- **Priority:** Critical | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-006
- **Files to Modify:** `chain/agent_tools.py`, `chain/bridge.py`, `chain/context_builder.py`, `chain/delegate.py`, `chain/router.py`, `tests/test_stale_refs.py`
- **Affected Modules:** chain
- **Acceptance Criteria:** Test: switch project → agent `read_file` reads NEW project (id()-asserted on fm).
- **Implementation Checklist:** ☐ all five consumers migrated ☐ no `self.fm =` caching remains (grep)
- **Testing Checklist:** ☐ switch-then-act integration test green
- **Regression Checklist:** ☐ agent loop E2E on fixture still passes
- **Documentation Checklist:** ☐ "never cache handles" rule in CONTRIBUTING notes
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-008

### T-008 — Rewrite switch_project / switch_model handlers (R-102)
- **Description:** `api_switch_project` → `ctx.switch_project(path)` (one line + validation); `api_switch_model` → `ctx.switch_model(name)`; delete all private-attribute pokes (`request_router._active_provider_name`, `delegate_bridge._provider`, `chain_bridge._provider`).
- **Reason:** Private pokes silently miss new consumers; partial rebuild is the stale-ref root cause.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-007
- **Files to Modify:** `server.py`, `tests/test_switching.py`
- **Affected Modules:** server
- **Acceptance Criteria:** grep for `._active_provider_name`/`._provider =` outside owners → empty; switch tests green.
- **Implementation Checklist:** ☐ handlers rewritten ☐ pokes deleted
- **Testing Checklist:** ☐ model switch observed by router/delegate/bridge via ctx
- **Regression Checklist:** ☐ chat works after both switches
- **Documentation Checklist:** ☐ changelog entry
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-009

### T-009 — Fix delegate provider contract call sites (R-103)
- **Description:** In `chain/delegate.py` L260/289/327, convert `send(messages, system_prompt=...)` to `send(prompt=last_message_text, history=prior_messages, system_prompt=...)` matching `BaseProvider.send(prompt: str, ...)`.
- **Reason:** Passing `list[Message]` where `str` is typed is a latent crash on any strict provider in the fallback chain.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-002
- **Files to Modify:** `chain/delegate.py`, `tests/test_delegate_contract.py`
- **Affected Modules:** chain
- **Acceptance Criteria:** Delegate E2E against strict FakeProvider (type-asserting) completes Brief→Implement→Review→Land.
- **Implementation Checklist:** ☐ 3 call sites converted ☐ helper `_to_prompt_history()` added
- **Testing Checklist:** ☐ strict-provider E2E green
- **Regression Checklist:** ☐ delegate output parity vs recorded transcript
- **Documentation Checklist:** ☐ contract note in providers/base.py docstring
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-010

### T-010 — Provider contract test suite + mypy gate (R-103)
- **Description:** Shared `ProviderContractTest` mixin (signature types, history handling, error taxonomy) run against FakeProvider; add `mypy` config covering `chain/delegate.py`, `providers/base.py`.
- **Reason:** Machine-enforce the contract so R-103's bug class can't return.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-009
- **Files to Modify:** `tests/test_provider_contract.py`, `mypy.ini`, `requirements-dev.txt`
- **Affected Modules:** tests
- **Acceptance Criteria:** `mypy` clean on covered modules; contract suite green.
- **Implementation Checklist:** ☐ mixin ☐ mypy config
- **Testing Checklist:** ☐ suite green ☐ mypy exit 0
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ CI doc updated
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-011

### T-011 — ApprovalGate service + policies (R-104)
- **Description:** Create `core/approval.py`: `ProposedAction`, `Decision`, `ApprovalGate.request(actions) -> Decision` with policies `auto` (kind whitelist), `interactive` (callback + payload hash + timeout — mechanics ported from agent loop), `deny`.
- **Reason:** Two consent models exist (chain = none, agent = ad-hoc); one gate must own consent.
- **Priority:** Critical | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-005
- **Files to Modify:** `core/approval.py`, `tests/test_approval_gate.py`
- **Affected Modules:** new core
- **Acceptance Criteria:** Unit: auto/interactive/deny/timeout/hash-mismatch matrix green.
- **Implementation Checklist:** ☐ dataclasses ☐ 3 policies ☐ hash verification ☐ timeout
- **Testing Checklist:** ☐ 5-case matrix green
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ policy semantics documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-012

### T-012 — Move chain apply out of finally, through gate (R-104)
- **Description:** In `chain/bridge.py` (L264–276) relocate `action_applier.apply_step(...)` from `finally` to the success-only path, wrapped in `gate.request(...)`; honor `config.yaml` `auto_execute` as the gate's `auto` switch.
- **Reason:** Chain output currently mutates the workspace unconditionally — even after partially-FAILED runs — while config says `auto_execute: false`.
- **Priority:** Critical | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-011
- **Files to Modify:** `chain/bridge.py`, `server.py` (approval frame), `config.yaml`, `tests/test_chain_apply_gate.py`
- **Affected Modules:** chain, server
- **Acceptance Criteria:** Failed chain run → ZERO file writes (fixture-asserted); success + interactive → write only after approval frame.
- **Implementation Checklist:** ☐ apply out of finally ☐ gated ☐ config plumbed
- **Testing Checklist:** ☐ failed-run-no-writes test ☐ interactive approve/reject tests
- **Regression Checklist:** ☐ auto mode still applies on success
- **Documentation Checklist:** ☐ changelog: behavior change + `approval.mode` migration note
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-013

### T-013 — Route agent-loop approval through ApprovalGate (R-104)
- **Description:** Replace `AgentLoop`'s bespoke threading.Event approval with `gate.request(...)` (interactive policy); keep WS frame shape identical.
- **Reason:** One consent model everywhere; deletes duplicated approval mechanics.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-012
- **Files to Modify:** `chain/agent_loop.py`, `tests/test_agent_approval.py`
- **Affected Modules:** chain
- **Acceptance Criteria:** Agent approval E2E (approve, reject, timeout, hash-mismatch) green with unchanged WS frames.
- **Implementation Checklist:** ☐ bespoke mechanism removed ☐ gate wired
- **Testing Checklist:** ☐ 4-case E2E green
- **Regression Checklist:** ☐ frame parity vs recording
- **Documentation Checklist:** ☐ internal doc updated
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-014

### T-014 — ExecutionRegistry + RunTicket (R-105)
- **Description:** Create `core/registry.py`: `register(kind, project_id) -> RunTicket(run_id, cancel_token)`, `heartbeat`, `finish(status)`, `list_active`, `cancel(run_id)`, per-project mutual exclusion; supersedes ActiveRunHolder.
- **Reason:** No authoritative record of executing work exists; delegate has no cancellation at all.
- **Priority:** Critical | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-004, T-006
- **Files to Modify:** `core/registry.py`, `tests/test_registry.py`
- **Affected Modules:** core
- **Acceptance Criteria:** Unit: register/finish/cancel/per-project-exclusion/TTL matrix green.
- **Implementation Checklist:** ☐ ticket model ☐ exclusion ☐ cancel tokens ☐ TTL sweep
- **Testing Checklist:** ☐ matrix green ☐ thread-safety race test
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ lifecycle diagram in docstring
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-015

### T-015 — Ticket all three execution modes + delegate cancel checkpoints (R-105)
- **Description:** ChainBridge, AgentLoop, DelegateBridge acquire tickets; delegate checks `cancel_token` at Brief/Implement/Review/Land boundaries; ActiveRunHolder deleted (registry replaces it).
- **Reason:** Uniform lifecycle; delegate becomes cancellable for the first time.
- **Priority:** Critical | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-014
- **Files to Modify:** `chain/bridge.py`, `chain/agent_loop.py`, `chain/delegate.py`, `core/run_holder.py` (delete), `tests/test_registry_integration.py`
- **Affected Modules:** chain, core
- **Acceptance Criteria:** Cancel delegate between stages → status `cancelled`, Land never executes; all modes appear in `list_active()` while running.
- **Implementation Checklist:** ☐ 3 modes ticketed ☐ ≥3 delegate checkpoints ☐ holder deleted
- **Testing Checklist:** ☐ cancel tests per mode green
- **Regression Checklist:** ☐ T-004 exclusion test still green (via registry)
- **Documentation Checklist:** ☐ cancellation semantics doc
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-016

### T-016 — WS list_runs / cancel_run commands (R-105)
- **Description:** Add WS message types `list_runs` and `cancel_run {run_id}` backed by the registry; structured responses.
- **Reason:** UI can finally see and stop what it started.
- **Priority:** High | **Complexity:** 1/5 | **Time:** 45 min
- **Dependencies:** T-015
- **Files to Modify:** `server.py`, `tests/test_ws_run_commands.py`
- **Affected Modules:** server
- **Acceptance Criteria:** E2E: start chain → `list_runs` shows it → `cancel_run` → run ends cancelled.
- **Implementation Checklist:** ☐ 2 handlers ☐ error cases (unknown run_id)
- **Testing Checklist:** ☐ E2E green
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ WS protocol doc updated
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-017

---

# PHASE 2 — Context Engine

### T-017 — Snapshot legacy context behavior (R-201 pre-work)
- **Description:** Golden tests capturing what the CURRENT inline block (server.py L606–758) includes for 6 representative messages against the fixture project (mentions, keywords, structure).
- **Reason:** Extraction must be parity-proven; without snapshots, drift is invisible.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-006
- **Files to Modify:** `tests/test_context_golden.py`, `tests/golden/context_*.json`
- **Affected Modules:** tests
- **Acceptance Criteria:** 6 golden snapshots recorded and re-runnable deterministically.
- **Implementation Checklist:** ☐ harness invokes legacy path in isolation ☐ snapshots committed
- **Testing Checklist:** ☐ re-run stability (2 consecutive runs identical)
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ golden-update procedure documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-018

### T-018 — ContextEngine skeleton + MentionSource (R-201)
- **Description:** Create `context/engine.py` (`ContextEngine.gather(ContextRequest) -> ContextResult`) and `MentionSource` porting mention-extraction; replace per-word `rglob` with ONE cached file-list scan per gather. Fix the lying constant (`MAX_MENTIONED = 100 # حد أقصى 10 ملفات`).
- **Reason:** Begin dismantling the 200-line inline block; kill the O(files×words) walk.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-017
- **Files to Modify:** `context/__init__.py`, `context/engine.py`, `context/sources.py`, `tests/test_context_engine.py`
- **Affected Modules:** new context/
- **Acceptance Criteria:** MentionSource output matches golden snapshots for mention cases; ≤1 filesystem walk per gather (patched-assert).
- **Implementation Checklist:** ☐ engine skeleton ☐ MentionSource ☐ single-scan cache ☐ constant fixed
- **Testing Checklist:** ☐ parity vs goldens ☐ walk-count test
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ source-plugin interface documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-019

### T-019 — Port KeywordSource + StructureSource; server uses engine (R-201)
- **Description:** Port keyword and project-structure gathering into sources; replace server.py L606–758 with `ctx.context_engine.gather(...)`; delete the inline block.
- **Reason:** Completes extraction; server handler drops ~200 lines.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-018
- **Files to Modify:** `context/sources.py`, `server.py`, `tests/test_context_parity.py`
- **Affected Modules:** context, server
- **Acceptance Criteria:** All 6 goldens pass through the engine; grep: no context-gathering logic in server.py.
- **Implementation Checklist:** ☐ 2 sources ported ☐ inline block deleted
- **Testing Checklist:** ☐ full golden parity
- **Regression Checklist:** ☐ chat E2E includes expected context
- **Documentation Checklist:** ☐ README architecture updated
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-020

### T-020 — Converge ContextBuilder & agent prefetch onto engine (R-201)
- **Description:** `ContextBuilder` becomes a thin adapter over `ContextEngine`; `AgentLoop._auto_prefetch` delegates to the engine; divergent keyword tables merged.
- **Reason:** Three context implementations → one.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-019
- **Files to Modify:** `chain/context_builder.py`, `chain/agent_loop.py`, `tests/test_context_convergence.py`
- **Affected Modules:** chain, context
- **Acceptance Criteria:** grep: no independent gathering logic in context_builder/agent_loop; agent prefetch parity on fixture.
- **Implementation Checklist:** ☐ adapter ☐ prefetch delegation ☐ tables merged
- **Testing Checklist:** ☐ convergence tests green
- **Regression Checklist:** ☐ chain + agent E2E green
- **Documentation Checklist:** ☐ deprecation note on ContextBuilder
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-021

### T-021 — ContextBundle with hash dedup + provenance (R-202)
- **Description:** Create `context/bundle.py`: `ContextItem(source_kind, path, content, content_hash, priority, token_estimate)`, `ContextBundle.add()` dedupes by hash, `render()` emits each item once; engine returns bundles.
- **Reason:** Same file content is injected multiple times per request today; no identity = no dedup.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-020
- **Files to Modify:** `context/bundle.py`, `context/engine.py`, `tests/test_bundle.py`
- **Affected Modules:** context
- **Acceptance Criteria:** Unit: dedup, ordering stability, provenance retention green.
- **Implementation Checklist:** ☐ item model ☐ hash dedup ☐ ordered render
- **Testing Checklist:** ☐ unit matrix green
- **Regression Checklist:** ☐ goldens still pass (render parity)
- **Documentation Checklist:** ☐ bundle semantics doc
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-022

### T-022 — Kill map_reduce duplicate embedding (R-202)
- **Description:** `strategies.py` map_reduce: `mr_execute` step stops re-embedding all file contents (already in map steps); pass bundle references; `ChainStep.build_prompt` renders "already in context" elision for duplicate file bodies (dependency RESULTS never elided).
- **Reason:** Token waste is multiplicative — every file shipped twice per map_reduce run.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-021
- **Files to Modify:** `chain/strategies.py`, `chain/models.py`, `tests/test_mapreduce_dedup.py`
- **Affected Modules:** chain
- **Acceptance Criteria:** Golden: map_reduce fixture prompt contains each file body exactly once; ≥40% token reduction vs baseline (logged metric).
- **Implementation Checklist:** ☐ mr_execute refs ☐ elision render ☐ results-never-elided guard
- **Testing Checklist:** ☐ exactly-once golden ☐ reduction metric asserted
- **Regression Checklist:** ☐ map_reduce E2E output quality parity
- **Documentation Checklist:** ☐ strategy doc updated
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-023

### T-023 — ContextBudget admission engine (R-203)
- **Description:** Create `context/budget.py`: priority tiers (must_have/high/normal/opportunistic), pluggable token estimator, deterministic drop order (lowest priority, largest first), `dropped[]` report; `ContextBundle.render(budget)`.
- **Reason:** All truncation today is ad-hoc char guessing; sums are unaccounted; overflows reach the provider.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-021
- **Files to Modify:** `context/budget.py`, `context/bundle.py`, `tests/test_context_budget.py`
- **Affected Modules:** context
- **Acceptance Criteria:** Unit: admission order, drop determinism, must_have always retained, 10% margin math — green.
- **Implementation Checklist:** ☐ tiers ☐ estimator interface ☐ drop order ☐ dropped[] report
- **Testing Checklist:** ☐ oversized-fixture test: fits window, dropped[] non-empty
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ budget semantics doc
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-024

### T-024 — Replace char-limit truncations with budget (R-203)
- **Description:** Route orchestrator `_split_content` (chars/4 guess), ContextBuilder per-item caps, and knowledge truncation through the shared estimator/budget; delete magic char constants.
- **Reason:** One accounting model; silent worst-item truncation becomes prioritized dropping.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-023
- **Files to Modify:** `chain/orchestrator.py`, `chain/context_builder.py`, `chain/knowledge.py`, `tests/test_budget_integration.py`
- **Affected Modules:** chain, context
- **Acceptance Criteria:** grep: zero raw char-limit truncations in the three files; overflow test green.
- **Implementation Checklist:** ☐ 3 call paths migrated ☐ constants deleted
- **Testing Checklist:** ☐ integration test green
- **Regression Checklist:** ☐ chain strategies E2E green
- **Documentation Checklist:** ☐ changelog
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-025

### T-025 — SafeReader gateway (R-204)
- **Description:** Create `context/safe_reader.py`: single read gateway — `resolve_workspace_path` + `is_secret_file` rejection (redaction stub) + size caps; remove `.env` from `_TEXT_EXTENSIONS` in `scan_folder_for_chain` (bridge.py L333–344).
- **Reason:** `.env` is currently read into chain context and shipped to model APIs — a security defect.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-018
- **Files to Modify:** `context/safe_reader.py`, `chain/bridge.py`, `tests/test_safe_reader.py`
- **Affected Modules:** context, chain
- **Acceptance Criteria:** Denylist matrix (.env/.env.local/id_rsa/*.pem vs .env.example) green; fixture `.env` value never appears in any built prompt.
- **Implementation Checklist:** ☐ gateway ☐ redaction stub ☐ .env removed from extensions
- **Testing Checklist:** ☐ matrix ☐ chain-prompt-never-contains-secret E2E
- **Regression Checklist:** ☐ folder scan still includes legit files
- **Documentation Checklist:** ☐ security note in README
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-026

### T-026 — Route all model-bound reads through SafeReader (R-204)
- **Description:** Context sources, agent `read_file` tool, and folder scanners call SafeReader exclusively; add lint/grep CI check for stray `read_text()` on model-bound paths.
- **Reason:** A policy that callers must remember is a policy that gets forgotten (it already was, once).
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-025
- **Files to Modify:** `context/sources.py`, `chain/agent_tools.py`, `tests/test_read_boundary.py`
- **Affected Modules:** context, chain
- **Acceptance Criteria:** Agent `read_file .env` → policy error; grep check passes in CI.
- **Implementation Checklist:** ☐ all read paths migrated ☐ CI grep check
- **Testing Checklist:** ☐ boundary tests green
- **Regression Checklist:** ☐ agent tools E2E green
- **Documentation Checklist:** ☐ boundary rule documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-027

---

# PHASE 3 — Memory & Sessions

### T-027 — JSONL session store (R-301)
- **Description:** Rewrite `SessionManager` persistence: `session_<id>.jsonl` O(1) append + `session_<id>.meta.json` sidecar; corrupt-tail detection; keep public API.
- **Reason:** `append_message` rewrites the whole JSON with fsync per message — O(n²) session lifetime.
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-001
- **Files to Modify:** `actions/session_manager.py`, `tests/test_session_store.py`
- **Affected Modules:** actions
- **Acceptance Criteria:** Perf: 1k appends p95 < 5ms; corrupt-tail replay recovers all complete lines; meta rebuildable from JSONL.
- **Implementation Checklist:** ☐ append path ☐ meta sidecar ☐ tail recovery ☐ rebuild
- **Testing Checklist:** ☐ perf test ☐ recovery tests
- **Regression Checklist:** ☐ session list/load APIs unchanged
- **Documentation Checklist:** ☐ format spec in module docstring
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-028

### T-028 — Legacy session migration + gitignore (R-301)
- **Description:** `scripts/migrate_sessions.py` (legacy JSON → JSONL, idempotent); add sessions dir to `.gitignore`; `git rm --cached` the 43 tracked session files.
- **Reason:** Tracked user sessions in VCS are a privacy leak; migration preserves history.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 60 min
- **Dependencies:** T-027
- **Files to Modify:** `scripts/migrate_sessions.py`, `.gitignore`, `tests/test_migration.py`
- **Affected Modules:** scripts
- **Acceptance Criteria:** Legacy fixture → identical message sequence post-migration; `git status` shows sessions untracked.
- **Implementation Checklist:** ☐ migrator ☐ idempotence ☐ untracked
- **Testing Checklist:** ☐ round-trip test green
- **Regression Checklist:** ☐ old sessions loadable after migration
- **Documentation Checklist:** ☐ migration guide
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-029

### T-029 — ConversationMemory component (R-302)
- **Description:** Create `memory/conversation.py`: `record(turn)`, `window(token_budget)`, `pin(turn_id)`, tool-turn folding; server + agent loop record through it.
- **Reason:** History semantics are currently "whatever each call site slices".
- **Priority:** High | **Complexity:** 3/5 | **Time:** 90 min
- **Dependencies:** T-027, T-023
- **Files to Modify:** `memory/__init__.py`, `memory/conversation.py`, `tests/test_conversation_memory.py`
- **Affected Modules:** new memory/
- **Acceptance Criteria:** Golden: fixture session → expected windows at 3 budget levels; pinning + folding unit tests green.
- **Implementation Checklist:** ☐ record/window/pin ☐ folding rules
- **Testing Checklist:** ☐ goldens + units green
- **Regression Checklist:** ☐ suite green
- **Documentation Checklist:** ☐ memory semantics doc
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-030

### T-030 — Migrate all history consumers to window() (R-302)
- **Description:** WS handler, agent loop, and `prompts/templates.py` stop slicing raw messages; all history reaches prompts via `ConversationMemory.window()`.
- **Reason:** One truncation policy; kills divergent ad-hoc slicing.
- **Priority:** High | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-029
- **Files to Modify:** `server.py`, `chain/agent_loop.py`, `prompts/templates.py`, `tests/test_history_flow.py`
- **Affected Modules:** server, chain, prompts
- **Acceptance Criteria:** grep: no direct session-message slicing outside memory module; prompt-history parity on fixtures.
- **Implementation Checklist:** ☐ 3 consumers migrated
- **Testing Checklist:** ☐ parity snapshots green
- **Regression Checklist:** ☐ chat E2E green
- **Documentation Checklist:** ☐ changelog
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-031

### T-031 — Session-project binding (R-303)
- **Description:** Stamp `project_id` in session meta at creation; on project switch auto-close + open bound session (config `warn_only` preserves old behavior); flag foreign-project turns in window().
- **Reason:** Cross-project history contamination silently poisons context.
- **Priority:** Medium | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-028, T-008
- **Files to Modify:** `actions/session_manager.py`, `server.py`, `memory/conversation.py`, `tests/test_session_binding.py`
- **Affected Modules:** actions, server, memory
- **Acceptance Criteria:** Switch project → new bound session (both modes tested); every new session has project_id.
- **Implementation Checklist:** ☐ stamp ☐ switch behavior ☐ config flag ☐ foreign-turn flag
- **Testing Checklist:** ☐ both modes green
- **Regression Checklist:** ☐ session listing unaffected
- **Documentation Checklist:** ☐ config option documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-032

### T-032 — Tiered windowing + async summarizer (R-304)
- **Description:** `memory/summarizer.py`: recent-verbatim floor → running summary of older turns (stored as JSONL artifacts, refreshed async every N turns) → pinned always verbatim; hard-slice fallback when summary absent.
- **Reason:** Long sessions currently face abrupt amnesia or overflow; no graceful middle.
- **Priority:** Medium | **Complexity:** 4/5 | **Time:** 90 min
- **Dependencies:** T-030
- **Files to Modify:** `memory/summarizer.py`, `memory/conversation.py`, `tests/test_summarization.py`
- **Affected Modules:** memory
- **Acceptance Criteria:** 100-turn fixture stays in budget with labeled summary block + last-k verbatim; hot path never blocks on summarization.
- **Implementation Checklist:** ☐ tiers ☐ async refresh ☐ fallback ☐ floor
- **Testing Checklist:** ☐ 60-turn golden ☐ non-blocking assert
- **Regression Checklist:** ☐ short sessions unchanged (no summary)
- **Documentation Checklist:** ☐ summarization design note
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-033

### T-033 — Truthful snapshots + retention GC (R-305)
- **Description:** Fix `ProjectSnapshot` creation (bridge.py L226–235) to record actual `relevant_file_hashes`; add `core/retention.py` `RetentionPolicy` (last N runs / max age / max bytes) swept on registry finish + startup; dry-run logging mode.
- **Reason:** Snapshots are currently empty lies; run artifacts accumulate forever.
- **Priority:** Medium | **Complexity:** 2/5 | **Time:** 75 min
- **Dependencies:** T-015
- **Files to Modify:** `chain/bridge.py`, `core/retention.py`, `core/registry.py`, `tests/test_retention.py`
- **Affected Modules:** chain, core
- **Acceptance Criteria:** Snapshot contains real hashes for touched files; artifact count bounded across 20 fixture runs.
- **Implementation Checklist:** ☐ real hashes ☐ policy matrix ☐ sweeps ☐ dry-run
- **Testing Checklist:** ☐ policy + idempotence tests green
- **Regression Checklist:** ☐ chain runs unaffected
- **Documentation Checklist:** ☐ retention config documented
- **Completion Status:** ☐ Not Started
- **Reviewer Notes:** —
- **Next Task:** T-034






















































# DEVELOPMENT TASKS — WebDev AI Editor

> Granular execution tasks (15–90 min each) derived from `MASTER_DEVELOPMENT_ROADMAP.md`.
> **One task = one commit.** Tasks are ordered; dependencies are explicit.
> Total: **52 tasks** (T-001 → T-052).

---

## Verification Protocol (applies to every task)

1. **Dependencies first** — a task may not start until every listed dependency is ✅.
2. **No scope expansion** — implement exactly what the task says; discoveries become new tasks.
3. **Evidence required** — Reviewer Notes must contain concrete evidence (test output, grep result, benchmark number).
4. **Never done with failing tests** — a task cannot be marked ✅ while any test in the suite is red.
5. **Commit format** — `type(scope): T-xxx description` (e.g. `fix(server): T-004 wire ActiveRunHolder, delete dead guard`).
6. **Regression rule** — if a task breaks an existing test: fix within the task or revert the task; never commit red.

**Status legend:** ☐ not started · 🔄 in progress · ✅ done · ⛔ blocked

---

# Phase 1 — Correctness & Safety (T-001 … T-016)

---

## T-001 — Bootstrap pytest Infrastructure
- **Description:** Add `pytest`, `pytest-timeout`, `mypy` to dev requirements; create `tests/` with `conftest.py`, `tests/unit/`, `tests/integration/`; add `scripts/check.sh` running lint+types+tests; one trivial smoke test proving the harness runs.
- **Reason:** No tests exist despite README claims; every later task requires this.
- **Priority:** Critical · **Complexity:** 1/5 · **Time:** 45 min · **Dependencies:** none
- **Files to Modify:** `requirements-dev.txt` (new), `tests/conftest.py` (new), `scripts/check.sh` (new)
- **Affected Modules:** none (additive)
- **Acceptance Criteria:** `./scripts/check.sh` exits 0; smoke test collected and green.
- **Implementation:** [ ] dev deps · [ ] tree · [ ] check.sh · [ ] smoke test
- **Testing:** [ ] check.sh runs green locally
- **Regression:** [ ] n/a (additive)
- **Documentation:** [ ] README dev-setup section
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-002

## T-002 — FakeProvider + Fixture Project
- **Description:** Implement `tests/fakes/fake_provider.py` (scriptable responses, call recording, injectable failures/latency) conforming to `providers/base.py`; create `tests/fixtures/sample_project/` (~12 files incl. a dummy `.env` with fake keys for R-204 tests) and a `sample_project` pytest fixture that copies it to tmp.
- **Reason:** Deterministic provider + realistic project needed by nearly every test after this.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-001
- **Files to Modify:** `tests/fakes/fake_provider.py`, `tests/fixtures/sample_project/*`, `tests/conftest.py`
- **Affected Modules:** none (test-only)
- **Acceptance Criteria:** FakeProvider passes a basic send/response test; fixture yields isolated tmp copy per test.
- **Implementation:** [ ] FakeProvider · [ ] fixture project incl. dummy .env · [ ] conftest fixtures
- **Testing:** [ ] provider unit · [ ] fixture isolation test
- **Regression:** [ ] n/a
- **Documentation:** [ ] tests/README.md fixture usage
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-003

## T-003 — ActiveRunHolder Class (R-101)
- **Description:** New `core/active_run.py` — `ActiveRunHolder` with `acquire(run_id) -> bool`, `release(run_id)`, `current()`, thread-lock protected. Unit tests only; no wiring yet.
- **Reason:** Safe replacement for the dead `_active_chain_run` guard.
- **Priority:** Critical · **Complexity:** 1/5 · **Time:** 30 min · **Dependencies:** T-001
- **Files to Modify:** `core/active_run.py` (new), `tests/unit/test_active_run.py`
- **Affected Modules:** none yet
- **Acceptance Criteria:** acquire/release/double-acquire/foreign-release tests green.
- **Implementation:** [ ] class · [ ] lock semantics
- **Testing:** [ ] 4 unit cases green
- **Regression:** [ ] full suite green
- **Documentation:** [ ] docstring notes R-105 supersession
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-004

## T-004 — Wire Holder, Delete Dead Guard (R-101)
- **Description:** Instantiate holder at startup; check `acquire()` **before** chain dispatch; `release()` in run completion path; **delete** `_active_chain_run` (server.py L82, L403, L470). Reject concurrent run with a `busy` WS frame.
- **Reason:** The existing guard provably never blocks anything.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-003
- **Files to Modify:** `server.py`
- **Affected Modules:** chain dispatch path
- **Acceptance Criteria:** grep for `_active_chain_run` returns nothing; concurrent-run integration test gets `busy`.
- **Implementation:** [ ] wire · [ ] delete guard · [ ] busy frame
- **Testing:** [ ] concurrent-run integration test
- **Regression:** [ ] single-run E2E unchanged
- **Documentation:** [ ] changelog entry
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-005

## T-005 — AppContext + ProjectHandle Skeleton (R-102)
- **Description:** New `core/app_context.py` — `ProjectHandle` (path, fm, safe_reader slot, index slot) and `AppContext` (project handle, provider registry, config). `switch_project(path)` swaps the handle atomically. No consumers yet.
- **Reason:** Composition root that ends stale-reference bugs.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-001
- **Files to Modify:** `core/app_context.py` (new), `tests/unit/test_app_context.py`
- **Affected Modules:** none yet
- **Acceptance Criteria:** handle-swap atomicity test green; old handle unusable after swap (flag check).
- **Implementation:** [ ] dataclasses · [ ] atomic swap · [ ] invalidation flag
- **Testing:** [ ] swap unit tests
- **Regression:** [ ] suite green
- **Documentation:** [ ] module docstring w/ wiring diagram
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-006

## T-006 — Build AppContext in main() (R-102)
- **Description:** Construct `AppContext` in `main()`; thread `ctx` into WS handler entry; keep legacy globals temporarily **aliased to ctx fields** (one-way) so both paths see identical objects during migration.
- **Reason:** Incremental migration without a big-bang diff.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 45 min · **Dependencies:** T-005
- **Files to Modify:** `server.py`
- **Affected Modules:** startup
- **Acceptance Criteria:** server boots; legacy paths still function; ctx reachable in handlers.
- **Implementation:** [ ] construct · [ ] thread ctx · [ ] alias globals
- **Testing:** [ ] boot smoke test · [ ] handler receives ctx
- **Regression:** [ ] chat E2E unchanged
- **Documentation:** [ ] migration note in code
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-007

## T-007 — Migrate Five Stale-Ref Consumers (R-102)
- **Description:** Convert the five consumers that captured `file_manager`/`context_builder` at init to resolve `ctx.project.fm` **at call time**. One consumer per commit is acceptable; this task tracks all five.
- **Reason:** These are the concrete stale-pointer sites after `api_switch_project` (L463–504).
- **Priority:** Critical · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-006
- **Files to Modify:** `chain/bridge.py`, `actions/*` (the five sites)
- **Affected Modules:** bridge, actions
- **Acceptance Criteria:** switch-project E2E: file created in A invisible after switch to B; grep — no constructor-captured fm remains.
- **Implementation:** [ ] site 1 · [ ] site 2 · [ ] site 3 · [ ] site 4 · [ ] site 5
- **Testing:** [ ] switch E2E green
- **Regression:** [ ] all action paths E2E
- **Documentation:** [ ] pattern note: "resolve at call time"
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-008

## T-008 — Rewrite Switch Handlers, Delete Private Pokes (R-102)
- **Description:** `api_switch_project` becomes `ctx.switch_project(path)` + confirmation frame; `switch_model` uses provider registry API — **delete** the private-attribute pokes (server.py L435–450); remove now-dead legacy global aliases from T-006.
- **Reason:** Handlers currently reach into internals; aliases were scaffolding.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-007
- **Files to Modify:** `server.py`
- **Affected Modules:** switch handlers
- **Acceptance Criteria:** no `_underscore` attribute access from handlers (grep); switch E2E green; aliases gone.
- **Implementation:** [ ] switch_project rewrite · [ ] switch_model rewrite · [ ] delete aliases
- **Testing:** [ ] both switch E2Es
- **Regression:** [ ] full suite
- **Documentation:** [ ] changelog
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-009

## T-009 — Fix Delegate Contract Violation (R-103)
- **Description:** Add `_to_prompt_history(messages) -> str` in `chain/delegate.py` (role-tagged rendering); convert the three offending call sites (L260, L289, L327) to pass rendered strings to `send()`.
- **Reason:** `send(prompt: str)` receives `list[Message]` today — latent crash on any conforming provider.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-002
- **Files to Modify:** `chain/delegate.py`
- **Affected Modules:** delegate loop
- **Acceptance Criteria:** FakeProvider (strict types) passes delegate integration; rendering snapshot pinned as golden.
- **Implementation:** [ ] helper · [ ] site L260 · [ ] site L289 · [ ] site L327
- **Testing:** [ ] delegate integration vs FakeProvider · [ ] rendering golden
- **Regression:** [ ] delegate E2E output sane
- **Documentation:** [ ] helper docstring w/ format spec
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-010

## T-010 — ProviderContractTest + mypy Gate (R-103)
- **Description:** `tests/contracts/provider_contract.py` mixin asserting `send` signature/behavior for any provider; apply to all registered providers; add mypy to `scripts/check.sh` scoped to `chain/` + `providers/`, fix revealed annotations.
- **Reason:** Prevent the T-009 class of bug permanently.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-009
- **Files to Modify:** `tests/contracts/`, `scripts/check.sh`, annotation fixes in both packages
- **Affected Modules:** providers, chain (annotations only)
- **Acceptance Criteria:** mypy clean on both packages; contract suite green for every provider.
- **Implementation:** [ ] mixin · [ ] apply to providers · [ ] mypy in check.sh · [ ] fix annotations
- **Testing:** [ ] contract suite green
- **Regression:** [ ] suite green
- **Documentation:** [ ] "adding a provider" doc references mixin
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-011

## T-011 — ApprovalGate Service (R-104)
- **Description:** New `core/approval.py` — `ApprovalGate` with modes `auto|interactive|deny`; `request(ApprovalRequest) -> Verdict`; interactive mode emits callback (WS wiring later) and blocks with timeout→deny; audit log of every verdict. Unit-tested standalone.
- **Reason:** Consent machinery must exist before touching the `finally` bug.
- **Priority:** Critical · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-005
- **Files to Modify:** `core/approval.py` (new), `tests/unit/test_approval.py`
- **Affected Modules:** none yet
- **Acceptance Criteria:** all three modes unit-tested incl. timeout→deny; audit entries complete.
- **Implementation:** [ ] gate · [ ] three modes · [ ] timeout · [ ] audit log
- **Testing:** [ ] mode matrix units
- **Regression:** [ ] suite green
- **Documentation:** [ ] mode semantics table
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-012

## T-012 — Chain Apply Through the Gate (R-104)
- **Description:** In `chain/bridge.py`: `finally` block (L264–276) may only **stage** results; apply happens post-run through `ApprovalGate` respecting `auto_execute`; wire interactive verdict frames into WS; crash mid-chain ⇒ zero partial writes.
- **Reason:** The silent auto-apply defect itself.
- **Priority:** Critical · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-011
- **Files to Modify:** `chain/bridge.py`, `server.py` (verdict frames)
- **Affected Modules:** bridge, WS protocol (additive frame)
- **Acceptance Criteria:** `auto_execute:false` E2E shows no writes without accept; crash test leaves tree untouched; no apply reachable from `finally` (grep + test).
- **Implementation:** [ ] stage-only finally · [ ] gate wiring · [ ] verdict frames
- **Testing:** [ ] approval matrix E2E (auto/accept/reject/deny) · [ ] crash test
- **Regression:** [ ] auto mode output identical to legacy
- **Documentation:** [ ] loud changelog: behavior change
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-013

## T-013 — Agent Approvals Through the Gate (R-104)
- **Description:** Route agent-mode file writes through the same `ApprovalGate` instance; remove the agent path's separate ad-hoc apply logic.
- **Reason:** One consent mechanism for all modes.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-012
- **Files to Modify:** agent flow in `server.py` / agent module
- **Affected Modules:** agent execution
- **Acceptance Criteria:** approval matrix E2E green for agent mode; single gate instance serves both modes (assert same audit log).
- **Implementation:** [ ] route agent writes · [ ] delete ad-hoc apply
- **Testing:** [ ] agent approval matrix
- **Regression:** [ ] agent E2E
- **Documentation:** [ ] docs: unified consent
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-014

## T-014 — ExecutionRegistry + RunTicket (R-105)
- **Description:** New `core/execution.py` — `RunTicket` (run_id, mode, cancel(), is_cancelled, state) and `ExecutionRegistry` (register/lookup/list/finish), lock-protected. Standalone + units.
- **Reason:** Identity and control surface for every run.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 75 min · **Dependencies:** T-005
- **Files to Modify:** `core/execution.py` (new), `tests/unit/test_execution.py`
- **Affected Modules:** none yet
- **Acceptance Criteria:** register/cancel/finish lifecycle units green; list reflects live state.
- **Implementation:** [ ] ticket · [ ] registry · [ ] locking
- **Testing:** [ ] lifecycle units · [ ] concurrent registration
- **Regression:** [ ] suite green
- **Documentation:** [ ] state diagram in docstring
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-015

## T-015 — Tickets in All Three Modes; Delete Holder (R-105)
- **Description:** Every dispatch (chain/agent/delegate) allocates a ticket; executor polls `is_cancelled` at step boundaries; delegate loop checks per iteration; **delete ActiveRunHolder** (registry enforces the single-run policy now, configurably).
- **Reason:** Cancellation must reach the loops to be real.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-014, T-004
- **Files to Modify:** `server.py`, `chain/executor.py`, `chain/delegate.py`, delete `core/active_run.py`
- **Affected Modules:** all execution paths
- **Acceptance Criteria:** cancel-mid-chain stops before next step; cancel-delegate stops next iteration; holder file deleted; suite green.
- **Implementation:** [ ] chain checkpoints · [ ] agent checkpoints · [ ] delegate checkpoints · [ ] delete holder
- **Testing:** [ ] cancel matrix (3 modes)
- **Regression:** [ ] uncancelled runs identical
- **Documentation:** [ ] checkpoint placement rule in CONTRIBUTING
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-016

## T-016 — WS list_runs / cancel_run (R-105)
- **Description:** Two new WS message types backed by the registry; `cancel_run` returns acknowledged/not-found; `list_runs` returns id/mode/state/started_at.
- **Reason:** User-facing control surface.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 45 min · **Dependencies:** T-015
- **Files to Modify:** `server.py`
- **Affected Modules:** WS protocol (additive)
- **Acceptance Criteria:** integration test — start run, list shows it, cancel stops it, list shows terminal state.
- **Implementation:** [ ] list handler · [ ] cancel handler
- **Testing:** [ ] list/cancel integration
- **Regression:** [ ] existing frames unchanged
- **Documentation:** [ ] WS protocol doc updated
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-017

---

# Phase 2 — Context Engine (T-017 … T-026)

---

## T-017 — Pin Legacy Context Goldens (R-201)
- **Description:** Record the exact context output of the legacy inline block for 6 representative messages (mention-only, keyword-only, mixed, no-context, huge-file, Arabic filename) against the fixture project; store as golden files.
- **Reason:** Parity net before any extraction.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-002
- **Files to Modify:** `tests/goldens/context/*`, capture harness
- **Affected Modules:** none (read-only capture)
- **Acceptance Criteria:** 6 goldens stored; harness replays them green against legacy code.
- **Implementation:** [ ] harness · [ ] 6 scenarios · [ ] goldens committed
- **Testing:** [ ] replay green on legacy
- **Regression:** [ ] n/a
- **Documentation:** [ ] scenario descriptions in goldens dir
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-018

## T-018 — ContextEngine + MentionSource (R-201)
- **Description:** New `context/` package: `ContextEngine`, `ContextItem`, `ContextSource` protocol; implement `MentionSource` with a **single-scan cached** file list per request; **fix the lying constant** (`MAX_MENTIONED = 100 # حد أقصى 10 ملفات`) — set the real intended limit with an honest comment.
- **Reason:** First source out of the monolith; kills per-message rglob for mentions.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-017
- **Files to Modify:** `context/engine.py`, `context/sources/mention.py`, units
- **Affected Modules:** none wired yet
- **Acceptance Criteria:** mention goldens green through the new source; one scan per request asserted.
- **Implementation:** [ ] engine skeleton · [ ] MentionSource · [ ] scan cache · [ ] constant fixed
- **Testing:** [ ] mention goldens · [ ] scan-count assertion
- **Regression:** [ ] suite green
- **Documentation:** [ ] source-authoring guide stub
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-019

## T-019 — Keyword + Structure Sources; Delete Inline Block (R-201)
- **Description:** Implement `KeywordSource` and `StructureSource`; wire `engine.gather()` into the WS handler; **delete the inline context block (server.py L606–758)**.
- **Reason:** Completes the extraction.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-018
- **Files to Modify:** `context/sources/keyword.py`, `context/sources/structure.py`, `server.py`
- **Affected Modules:** WS message handler
- **Acceptance Criteria:** all 6 goldens green via engine; L606–758 gone; handler calls one engine method.
- **Implementation:** [ ] KeywordSource · [ ] StructureSource · [ ] wire · [ ] delete block
- **Testing:** [ ] full golden suite
- **Regression:** [ ] chat E2E
- **Documentation:** [ ] architecture doc: context flow
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-020

## T-020 — Converge ContextBuilder + Chain Prefetch (R-201)
- **Description:** Point the chain executor's context prefetch and the legacy `ContextBuilder` consumers at `ContextEngine`; delete the duplicated file-reading paths.
- **Reason:** Three reading paths must become one.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 75 min · **Dependencies:** T-019
- **Files to Modify:** `chain/executor.py`, context_builder call sites
- **Affected Modules:** chain prompts
- **Acceptance Criteria:** grep shows one context-reading path; chain E2E prompts equivalent to legacy.
- **Implementation:** [ ] prefetch migration · [ ] builder consumers · [ ] delete dupes
- **Testing:** [ ] chain prompt goldens
- **Regression:** [ ] chain E2E
- **Documentation:** [ ] deprecation note on ContextBuilder
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-021

## T-021 — ContextBundle Dedup (R-202)
- **Description:** Implement `ContextBundle` (sha256 content-keying, reference note on duplicate insert, provenance fields); engine returns a bundle; renderer produces the prompt block.
- **Reason:** Same file must never appear twice in a prompt.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 75 min · **Dependencies:** T-020
- **Files to Modify:** `context/bundle.py`, `context/engine.py`, renderer
- **Affected Modules:** prompt assembly
- **Acceptance Criteria:** dedup unit (two sources, same file → one body + one reference); goldens updated deliberately and reviewed.
- **Implementation:** [ ] bundle · [ ] reference rendering · [ ] provenance
- **Testing:** [ ] dedup units · [ ] renderer golden
- **Regression:** [ ] chat/chain E2E
- **Documentation:** [ ] bundle debug-dump usage
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-022

## T-022 — Map-Reduce Dedup ≥40% (R-202)
- **Description:** Route map_reduce step context through the bundle; add a prompt-size regression test proving ≥40% reduction on the duplication fixture.
- **Reason:** The worst measured duplication site.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-021
- **Files to Modify:** `chain/executor.py` (map_reduce path)
- **Affected Modules:** map_reduce chains
- **Acceptance Criteria:** size regression test asserts ≥40% smaller; output quality parity on fixture.
- **Implementation:** [ ] route through bundle · [ ] size test
- **Testing:** [ ] ≥40% assertion · [ ] output parity
- **Regression:** [ ] map_reduce E2E
- **Documentation:** [ ] measured numbers in Reviewer Notes
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-023

## T-023 — ContextBudget with Tiers (R-203)
- **Description:** Implement `ContextBudget` — tiers must_have/high/normal/opportunistic, token estimation (provider tokenizer or chars/4), drop-lowest-first packing, must_have overflow → per-item summarization hook.
- **Reason:** Replace character truncation with importance-ordered packing.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-021
- **Files to Modify:** `context/budget.py`, units
- **Affected Modules:** none wired yet
- **Acceptance Criteria:** property test — must_have never dropped while opportunistic present; packing determinism test.
- **Implementation:** [ ] tiers · [ ] estimator · [ ] packer · [ ] overflow hook
- **Testing:** [ ] property test · [ ] determinism
- **Regression:** [ ] suite green
- **Documentation:** [ ] tier semantics table
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-024

## T-024 — Replace the Three Char Limits (R-203)
- **Description:** Delete the three hardcoded `content[:N]` truncations; every prompt path packs via `ContextBudget`; budget limit in config.
- **Reason:** The limits are inconsistent and importance-blind.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-023
- **Files to Modify:** the 3 files with char limits, config
- **Affected Modules:** all prompt paths
- **Acceptance Criteria:** grep — zero `[:N]` content truncation remains; oversized-project E2E stays under budget with mentions intact.
- **Implementation:** [ ] site 1 · [ ] site 2 · [ ] site 3 · [ ] config knob
- **Testing:** [ ] oversize E2E
- **Regression:** [ ] goldens updated deliberately
- **Documentation:** [ ] config doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-025

## T-025 — SafeReader + Remove `.env` Extension (R-204)
- **Description:** Implement `context/safe_reader.py` — denylist (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`), entropy sniff, redaction stub; **remove `.env` from `_TEXT_EXTENSIONS` (L333–344)**.
- **Reason:** Live keys currently injectable into third-party prompts.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-002
- **Files to Modify:** `context/safe_reader.py` (new), `_TEXT_EXTENSIONS` site
- **Affected Modules:** file classification
- **Acceptance Criteria:** fixture `.env` mention returns redaction stub; entropy sniff units green.
- **Implementation:** [ ] denylist · [ ] sniff · [ ] stub · [ ] extension removal
- **Testing:** [ ] redaction E2E · [ ] sniff units
- **Regression:** [ ] normal files unaffected
- **Documentation:** [ ] security note + override procedure
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-026

## T-026 — Route All Context Reads Through SafeReader (R-204)
- **Description:** Every context-bound file read goes through SafeReader; add CI grep check — no `open(`/`.read_text(` in `context/` outside `safe_reader.py`.
- **Reason:** A boundary bypassed anywhere is not a boundary.
- **Priority:** Critical · **Complexity:** 2/5 · **Time:** 45 min · **Dependencies:** T-025, T-019
- **Files to Modify:** `context/sources/*`, `scripts/check.sh`
- **Affected Modules:** context sources
- **Acceptance Criteria:** CI grep green; `.env` unreachable via mention, keyword, and structure paths (3 tests).
- **Implementation:** [ ] route sources · [ ] CI grep
- **Testing:** [ ] 3-path redaction tests
- **Regression:** [ ] golden suite
- **Documentation:** [ ] boundary rule in CONTRIBUTING
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-027

---

# Phase 3 — Memory & Sessions (T-027 … T-033)

---

## T-027 — JSONL Session Store (R-301)
- **Description:** Implement `sessions/store.py` — JSONL append (O(1), optional fsync), meta sidecar, tail-read window, malformed-final-line recovery. Include benchmark test: 1k appends p95 <5ms.
- **Reason:** Kill the O(n²) rewrite-per-message.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-001
- **Files to Modify:** `sessions/store.py` (new), units + benchmark
- **Affected Modules:** none wired yet
- **Acceptance Criteria:** benchmark green; torn-write recovery test green.
- **Implementation:** [ ] append · [ ] meta · [ ] tail-read · [ ] recovery
- **Testing:** [ ] benchmark · [ ] recovery · [ ] round-trip
- **Regression:** [ ] suite green
- **Documentation:** [ ] on-disk format spec
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-028

## T-028 — Migration Script + Session Gitignore (R-301/R-305)
- **Description:** `scripts/migrate_sessions.py` (JSON→JSONL, lossless, idempotent); add `sessions/` to `.gitignore`; `git rm --cached` the 43 tracked session files (history purge is T-050).
- **Reason:** Existing data must survive; leaks must stop growing.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-027
- **Files to Modify:** `scripts/migrate_sessions.py`, `.gitignore`
- **Affected Modules:** session storage
- **Acceptance Criteria:** round-trip fidelity test; `git status` shows sessions untracked; re-run of script is a no-op.
- **Implementation:** [ ] migrator · [ ] idempotency · [ ] gitignore · [ ] rm --cached
- **Testing:** [ ] fidelity · [ ] idempotency
- **Regression:** [ ] old sessions loadable post-migration
- **Documentation:** [ ] migration runbook
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-029

## T-029 — ConversationMemory Facade (R-302)
- **Description:** Implement `sessions/memory.py` — `append`, `window(policy)`, `summary()` (stub), `search()` (stub); backed by the JSONL store; window policies configurable.
- **Reason:** One owner for history access.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-027
- **Files to Modify:** `sessions/memory.py` (new), units
- **Affected Modules:** none wired yet
- **Acceptance Criteria:** window policy units green; append/window integration on JSONL green.
- **Implementation:** [ ] facade · [ ] policies · [ ] stubs
- **Testing:** [ ] policy units · [ ] integration
- **Regression:** [ ] suite green
- **Documentation:** [ ] API doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-030

## T-030 — Migrate Three History Consumers (R-302)
- **Description:** Capture the current slices (`[-10:]`, `[-6:]`, full) as goldens, then convert all three consumers to `memory.window(policy)` with policies reproducing today's behavior exactly.
- **Reason:** Consumers must stop touching raw lists — without behavior change yet.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-029
- **Files to Modify:** the 3 consumer sites
- **Affected Modules:** chat, chain, delegate history
- **Acceptance Criteria:** goldens identical pre/post; grep — no raw history slicing outside `sessions/`.
- **Implementation:** [ ] goldens · [ ] consumer 1 · [ ] consumer 2 · [ ] consumer 3
- **Testing:** [ ] slice goldens
- **Regression:** [ ] chat/chain/delegate E2E
- **Documentation:** [ ] policy mapping table
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-031

## T-031 — Session ↔ Project Binding (R-303)
- **Description:** Meta stores `project_path` + fingerprint; on project switch check binding; implement `warn` policy (context banner) with `warn_only: true` default in config; `fork`/`block` behind config.
- **Reason:** Stop silent cross-project contamination.
- **Priority:** Medium · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-029, T-008
- **Files to Modify:** `sessions/store.py` meta, switch handler, config
- **Affected Modules:** switch flow
- **Acceptance Criteria:** switch-mid-session E2E shows banner under warn; fork creates bound session; block refuses.
- **Implementation:** [ ] binding write · [ ] mismatch check · [ ] 3 policies
- **Testing:** [ ] per-policy E2E
- **Regression:** [ ] same-project switch silent
- **Documentation:** [ ] config doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-032

## T-032 — Tiered Windowing + Async Summarizer (R-304)
- **Description:** `window()` returns `[summary] + recent`; middle band summarized **off the hot path** (background task, stored in meta); summarizer failure degrades to plain cutoff.
- **Reason:** Long-session coherence within budget.
- **Priority:** Medium · **Complexity:** 4/5 · **Time:** 90 min · **Dependencies:** T-030, T-023
- **Files to Modify:** `sessions/memory.py`, background task wiring
- **Affected Modules:** memory
- **Acceptance Criteria:** 100-turn simulation under budget retaining a turn-5 fact; degradation test green; no summarization latency on message path (timing assert).
- **Implementation:** [ ] tiers · [ ] async summarizer · [ ] degradation
- **Testing:** [ ] 100-turn sim · [ ] degradation · [ ] timing
- **Regression:** [ ] short sessions unchanged
- **Documentation:** [ ] tier diagram
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-033

## T-033 — Truthful Snapshots + RetentionPolicy (R-305)
- **Description:** `ProjectSnapshot` computes real content hashes for run-touched files (fix empty maps L226–235); implement `RetentionPolicy` (max age/count/pinned) with startup GC pass + dry-run logging.
- **Reason:** Vacuous validation + unbounded storage.
- **Priority:** Medium · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-027
- **Files to Modify:** snapshot module, `sessions/retention.py` (new)
- **Affected Modules:** snapshots, session storage
- **Acceptance Criteria:** new snapshots contain real hashes (unit); GC matrix tests; pinned survives.
- **Implementation:** [ ] hashing · [ ] policy · [ ] GC pass · [ ] pinning
- **Testing:** [ ] hash unit · [ ] GC matrix
- **Regression:** [ ] suite green
- **Documentation:** [ ] retention config doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-034

---

# Phase 4 — Routing & Planning (T-034 … T-038)

---

## T-034 — Record 30 Real Routing Decisions (R-401)
- **Description:** Instrument the current router/orchestrator (temporary logging) and capture 30 real decisions across task types; store as the golden corpus for the vocabulary refactor.
- **Reason:** Cannot unify vocabularies safely without knowing current behavior.
- **Priority:** High · **Complexity:** 1/5 · **Time:** 45 min · **Dependencies:** T-002
- **Files to Modify:** temp instrumentation, `tests/goldens/routing/*`
- **Affected Modules:** none (instrumentation removed after capture)
- **Acceptance Criteria:** 30 decisions covering all 6 orchestrator + 4 router strategies; instrumentation removed.
- **Implementation:** [ ] instrument · [ ] capture 30 · [ ] remove instrumentation
- **Testing:** [ ] corpus replays on legacy
- **Regression:** [ ] n/a
- **Documentation:** [ ] corpus coverage matrix
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-035

## T-035 — RoutingTier / ExecutionStrategy Enums + STRATEGY_TABLE (R-401)
- **Description:** New `core/strategy.py` — the two enums, `StrategySpec`, `STRATEGY_TABLE` registry; replace every free-string strategy comparison in orchestrator and router; `assert_never` on unhandled pairs.
- **Reason:** End the 6-vs-4 vocabulary drift.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-034
- **Files to Modify:** `core/strategy.py` (new), orchestrator, router
- **Affected Modules:** routing, orchestration
- **Acceptance Criteria:** grep — zero string strategy comparisons; 30-decision corpus reproduces identically; table completeness test.
- **Implementation:** [ ] enums · [ ] table · [ ] orchestrator swap · [ ] router swap
- **Testing:** [ ] corpus goldens · [ ] completeness · [ ] assert_never
- **Regression:** [ ] routing E2E
- **Documentation:** [ ] table as docs
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-036

## T-036 — RoutingDecision Record + Config Thresholds (R-402)
- **Description:** `RoutingDecision` dataclass (tier, strategy, scores, thresholds, signals, config version) produced by every routing path; move magic-number thresholds to config with schema validation; add monotonicity property test.
- **Reason:** Explainability + tunability.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 75 min · **Dependencies:** T-035
- **Files to Modify:** router, config, schema
- **Affected Modules:** routing
- **Acceptance Criteria:** every decision carries a complete record; no inline thresholds (grep); monotonicity property green.
- **Implementation:** [ ] record · [ ] config move · [ ] schema · [ ] property test
- **Testing:** [ ] record completeness · [ ] monotonicity · [ ] schema rejection
- **Regression:** [ ] corpus goldens
- **Documentation:** [ ] threshold tuning guide
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-037

## T-037 — Circuit Breaker per Provider (R-403)
- **Description:** Implement closed→open→half-open breaker per provider (N failures, cooldown with exponential cap, probe); **delete the never-called `reset_failures()`** — the breaker owns failure lifecycle now.
- **Reason:** Sticky failures currently require a process restart to clear.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-035, T-002
- **Files to Modify:** provider pool module
- **Affected Modules:** provider selection
- **Acceptance Criteria:** state-machine unit covers all transitions; FakeProvider scripted-failure recovery integration green; `reset_failures` gone (grep).
- **Implementation:** [ ] breaker · [ ] transitions · [ ] cooldown cap · [ ] delete reset_failures
- **Testing:** [ ] transition matrix · [ ] recovery integration
- **Regression:** [ ] healthy-provider path unchanged
- **Documentation:** [ ] breaker states diagram
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-038

## T-038 — CapacityModel; Remove MIN_ACCOUNTS (R-403)
- **Description:** `CapacityModel` computes availability from live pool + breaker states; **remove hardcoded `MIN_ACCOUNTS` arithmetic**; UI budget numbers derive from the model with `estimated` flags.
- **Reason:** Capacity numbers shown today are fictional.
- **Priority:** Medium · **Complexity:** 2/5 · **Time:** 60 min · **Dependencies:** T-037
- **Files to Modify:** capacity module, status frames
- **Affected Modules:** capacity reporting
- **Acceptance Criteria:** `MIN_ACCOUNTS` gone (grep); capacity property tests; status frame numbers traceable to model state.
- **Implementation:** [ ] model · [ ] remove constant · [ ] estimated flags
- **Testing:** [ ] property tests · [ ] status frame integration
- **Regression:** [ ] status E2E
- **Documentation:** [ ] capacity semantics doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-039

---

# Phase 5 — Agent Orchestration (T-039 … T-043)

---

## T-039 — Runner Protocol + Contract Harness + EchoRunner (R-501)
- **Description:** Define `Runner` protocol (`run(request, ticket, ctx) -> RunResult`); build the shared contract test harness (cancellation honored, approval gated, events well-formed); implement `EchoRunner` reference passing the harness.
- **Reason:** The contract must exist and be provably testable before real runners.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-015, T-013
- **Files to Modify:** `core/runner.py` (new), `tests/contracts/runner_contract.py`, `tests/fakes/echo_runner.py`
- **Affected Modules:** none wired yet
- **Acceptance Criteria:** EchoRunner passes full harness; harness reusable via mixin.
- **Implementation:** [ ] protocol · [ ] harness · [ ] EchoRunner
- **Testing:** [ ] harness green on Echo
- **Regression:** [ ] suite green
- **Documentation:** [ ] runner-authoring guide
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-040

## T-040 — Direct + Chain Runners Behind LEGACY_DISPATCH Flag (R-501)
- **Description:** Implement `DirectRunner` and `ChainRunner` wrapping existing logic; dispatch selects runner path when `LEGACY_DISPATCH=0`; record per-mode parity E2E (legacy vs runner output).
- **Reason:** Incremental, revertible migration of the dispatch ladder.
- **Priority:** High · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-039
- **Files to Modify:** `runners/direct.py`, `runners/chain.py`, `server.py` dispatch
- **Affected Modules:** dispatch (flagged)
- **Acceptance Criteria:** both pass contract harness; parity E2E identical outputs both flag values.
- **Implementation:** [ ] DirectRunner · [ ] ChainRunner · [ ] flag dispatch
- **Testing:** [ ] harness ×2 · [ ] parity E2E
- **Regression:** [ ] flag=1 byte-identical to legacy
- **Documentation:** [ ] flag lifecycle note
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-041

## T-041 — Agent + Delegate Runners; Delete Polling Loop + Flag (R-501)
- **Description:** Implement `AgentRunner` and `DelegateRunner`; **delete the agent WS polling workaround (server.py L920–965)**; remove `LEGACY_DISPATCH` and the legacy ladder — dispatch is `RUNNERS[strategy].run(...)`.
- **Reason:** Completes unification; the polling loop is the ugliest artifact of the old design.
- **Priority:** High · **Complexity:** 4/5 · **Time:** 90 min · **Dependencies:** T-040
- **Files to Modify:** `runners/agent.py`, `runners/delegate.py`, `server.py`
- **Affected Modules:** dispatch, agent flow
- **Acceptance Criteria:** L920–965 gone; flag gone; all four runners pass harness; all-mode parity E2E green.
- **Implementation:** [ ] AgentRunner · [ ] DelegateRunner · [ ] delete polling · [ ] delete flag+ladder
- **Testing:** [ ] harness ×4 · [ ] parity all modes
- **Regression:** [ ] cancel matrix still green
- **Documentation:** [ ] dispatch architecture doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-042

## T-042 — Agent Manifest; Delete ROLE_MAP (R-502)
- **Description:** Create `agents/manifest.yaml` describing all 21 agents (id, name, prompt path, capabilities, tier); loader with schema validation + mtime hot-reload (atomic registry swap); **delete ROLE_MAP**.
- **Reason:** Fleet config is data; 21 hardcoded Arabic-named paths are a runtime-typo minefield.
- **Priority:** Medium · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-041
- **Files to Modify:** `agents/manifest.yaml` (new), loader module, ROLE_MAP site
- **Affected Modules:** agent resolution
- **Acceptance Criteria:** all 21 legacy agents resolve identically (parity test); bad manifest rejected with line numbers; hot-reload integration green; ROLE_MAP gone.
- **Implementation:** [ ] manifest · [ ] loader+schema · [ ] hot-reload · [ ] delete ROLE_MAP
- **Testing:** [ ] 21-agent parity · [ ] schema rejection · [ ] reload
- **Regression:** [ ] agent E2E
- **Documentation:** [ ] manifest schema doc
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-043

## T-043 — Knowledge as Bundle View; Delta Prompts (R-503)
- **Description:** Rebuild `KnowledgeAccumulator` on `ContextBundle` (hash-dedup on insert); per-iteration prompts carry delta + budgeted stable-core summary instead of full re-injection; add token-cost curve test (8 iterations, flat within 15%).
- **Reason:** Quadratic token burn in agent loops.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-041, T-023
- **Files to Modify:** knowledge module, agent loop prompt build
- **Affected Modules:** agent iterations
- **Acceptance Criteria:** cost curve flat within 15%; iteration-1 finding retained at iteration 8; dedup unit green.
- **Implementation:** [ ] bundle-backed · [ ] delta render · [ ] core summary
- **Testing:** [ ] cost curve · [ ] retention · [ ] dedup
- **Regression:** [ ] agent output quality parity on fixture
- **Documentation:** [ ] measured curve in Reviewer Notes
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-044

---

# Phase 6 — Chain Engine Maturity (T-044 … T-047)

---

## T-044 — Wire Crash Resume (R-601)
- **Description:** Startup scan for interrupted runs (persisted ticket, non-terminal); WS `resume_run` / `discard_run`; resume validates real snapshot hashes and refuses with a drift report on mismatch — giving `can_resume`/`load_state` (executor.py L459–480) their first callers.
- **Reason:** Dead resume machinery must be wired or deleted; team chose wire.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-033, T-016
- **Files to Modify:** `chain/executor.py`, `server.py`, startup
- **Affected Modules:** chain lifecycle
- **Acceptance Criteria:** kill-after-step-2-of-5 E2E — resume runs steps 3–5 exactly once; hash-mismatch refusal; discard cleans state.
- **Implementation:** [ ] startup scan · [ ] resume handler · [ ] discard handler · [ ] drift refusal
- **Testing:** [ ] kill/resume E2E · [ ] drift test · [ ] discard test
- **Regression:** [ ] normal runs untouched
- **Documentation:** [ ] resume runbook
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-045

## T-045 — Enforce context_policy in build_prompt (R-602)
- **Description:** Honor the declared-but-ignored `context_policy` in `build_prompt`: `full` / `summary` (budgeted prior-step summaries) / `minimal` (declared inputs only); per-mode render goldens.
- **Reason:** A config field that does nothing is a lie to chain authors.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-024, T-022
- **Files to Modify:** `chain/executor.py` prompt build
- **Affected Modules:** chain prompts
- **Acceptance Criteria:** step-5 prompt ≥50% smaller under `summary` on the 5-step fixture; three-mode goldens green; `minimal` completeness check.
- **Implementation:** [ ] full · [ ] summary · [ ] minimal · [ ] defaults
- **Testing:** [ ] mode goldens · [ ] ≥50% size test
- **Regression:** [ ] default-mode parity with legacy
- **Documentation:** [ ] chain-authoring doc: three modes
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-046

## T-046 — Parallel Ready-Set Execution (R-603)
- **Description:** Replace `ready[0]` (executor.py L204–206) with `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)` over the full ready set; results merge through a lock-guarded `apply_step_result()`; per-task ticket cancellation checkpoints; stress test — 20 map steps with injected random failures.
- **Reason:** `max_parallel_steps` is advertised but sequential execution is hardcoded.
- **Priority:** Medium · **Complexity:** 4/5 · **Time:** 90 min · **Dependencies:** T-044, T-038, T-045
- **Files to Modify:** `chain/executor.py`
- **Affected Modules:** chain scheduling
- **Acceptance Criteria:** parallel=1 byte-identical to legacy; ≥3× speedup on 8-step map at parallel=4 (FakeProvider latency); stress consistent; cancellation stops siblings.
- **Implementation:** [ ] pool · [ ] guarded apply · [ ] checkpoints · [ ] capacity cap
- **Testing:** [ ] parallel=1 golden · [ ] speedup bench · [ ] stress · [ ] cancel
- **Regression:** [ ] all chain E2Es
- **Documentation:** [ ] max_parallel_steps now-real note
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-047

## T-047 — EventBus + WS Adapter (R-604)
- **Description:** Implement typed EventBus (RunStarted/StepProgress/ApprovalRequested/RunFinished/RoutingDecided/BudgetChanged, per-run FIFO); single WS Adapter renders legacy-identical frames; migrate all `ws.send` sites; CI grep bans `ws.send` outside the adapter.
- **Reason:** Business logic must stop writing to sockets.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-041
- **Files to Modify:** `core/events.py` (new), `server.py` adapter, all emit sites
- **Affected Modules:** every progress-reporting path
- **Acceptance Criteria:** frame snapshots vs legacy recordings identical; FIFO test under concurrent emission; CI grep green.
- **Implementation:** [ ] bus · [ ] event types · [ ] adapter · [ ] migrate sites · [ ] CI grep
- **Testing:** [ ] snapshots · [ ] FIFO · [ ] grep
- **Regression:** [ ] client works unmodified
- **Documentation:** [ ] event catalog
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-048

---

# Phase 7 — Platform Hardening (T-048 … T-051)

---

## T-048 — SessionContext per WS Connection (R-701)
- **Description:** Create `SessionContext` on connect (session binding, model selection, approval inbox, event subscription); handlers take `(ctx, sctx, msg)`; sweep remaining conversation-scoped globals; lint rule banning module-level mutable state in handler modules.
- **Reason:** Two tabs currently clobber each other's state.
- **Priority:** High · **Complexity:** 4/5 · **Time:** 90 min · **Dependencies:** T-047, T-031
- **Files to Modify:** `server.py`, `core/session_context.py` (new), lint config
- **Affected Modules:** all handlers
- **Acceptance Criteria:** two-tab isolation E2E (independent sessions/models/approvals); disconnect cleanup test; lint rule fails on violation fixture.
- **Implementation:** [ ] SessionContext · [ ] handler signatures · [ ] global sweep · [ ] lint rule
- **Testing:** [ ] two-tab E2E · [ ] cleanup · [ ] lint fixture
- **Regression:** [ ] single-tab E2E unchanged
- **Documentation:** [ ] state-scoping rules
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-049

## T-049 — ProjectIndex (R-702)
- **Description:** Inverted index (token stems, extensions, path trie) built at project open; mtime sweep + FileManager write hooks keep it fresh; Mention/Keyword sources query the index; CI grep bans `rglob` in per-message paths.
- **Reason:** O(files) traversal per chat message.
- **Priority:** Medium · **Complexity:** 3/5 · **Time:** 90 min · **Dependencies:** T-048
- **Files to Modify:** `context/index.py` (new), sources, FileManager hooks
- **Affected Modules:** context resolution
- **Acceptance Criteria:** <10ms mention resolution on 5k-file fixture; write-then-mention freshness; out-of-band edit within one sweep; grep green.
- **Implementation:** [ ] index · [ ] hooks · [ ] sweep · [ ] source migration
- **Testing:** [ ] 10ms bench · [ ] freshness ×2 · [ ] grep
- **Regression:** [ ] context goldens
- **Documentation:** [ ] index design note
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-050

## T-050 — CI Pipeline + Coverage Ratchet + History Purge (R-703)
- **Description:** CI workflow (lint + mypy + pytest + coverage ratchet at 40%, increase-only); purge session files from git history via `git filter-repo` (announced, coordinated force-push).
- **Reason:** Enforcement infrastructure + leaked-conversation cleanup.
- **Priority:** High · **Complexity:** 2/5 · **Time:** 75 min · **Dependencies:** T-028 (and benefits from all test tasks)
- **Files to Modify:** CI workflow file, ratchet script
- **Affected Modules:** none (infra)
- **Acceptance Criteria:** CI green on push; ratchet blocks a coverage-lowering test PR (verified once); `git log --all -- sessions/` empty.
- **Implementation:** [ ] workflow · [ ] ratchet · [ ] filter-repo · [ ] team notice
- **Testing:** [ ] CI run itself · [ ] ratchet block test
- **Regression:** [ ] repo clonable, suite green post-purge
- **Documentation:** [ ] re-clone instructions
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-051

## T-051 — Truthful README + Config Default Reconciliation (R-703)
- **Description:** Rewrite README removing the false "125/125 tests" claim (test count generated from CI); reconcile `default_provider` — **config wins**: server reads `config.default_provider`, hardcoded `genspark` deleted.
- **Reason:** The repo must stop lying about itself.
- **Priority:** High · **Complexity:** 1/5 · **Time:** 45 min · **Dependencies:** T-050
- **Files to Modify:** `README.md`, `server.py`, config
- **Affected Modules:** startup defaults
- **Acceptance Criteria:** README claims all verifiable; changing config default observably changes startup provider (test); hardcode gone (grep).
- **Implementation:** [ ] README rewrite · [ ] config read · [ ] delete hardcode
- **Testing:** [ ] default-provider test
- **Regression:** [ ] boot smoke
- **Documentation:** [ ] this IS documentation
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-052

---

# Phase 8 — Extensibility (T-052)

---

## T-052 — Phase 8 Scoping Spike
- **Description:** Time-boxed spike producing the granular task breakdown (T-053+) for R-801..R-805: validate entry-point plugin loading, pick the embedding backend for R-802, pick Redis client/deployment shape for R-804; output is a written plan + new task entries, **no production code**.
- **Reason:** Phase 8 items are too large and too dependent on Phase 1–7 outcomes to pre-slice honestly now.
- **Priority:** Low · **Complexity:** 2/5 · **Time:** 90 min · **Dependencies:** Phases 1–7 complete
- **Files to Modify:** `docs/phase8_plan.md` (new), this file (T-053+ appended)
- **Affected Modules:** none
- **Acceptance Criteria:** plan reviewed; T-053+ entries follow this file's format with real estimates.
- **Implementation:** [ ] plugin spike · [ ] embedding choice · [ ] redis shape · [ ] write plan
- **Testing:** [ ] n/a (spike)
- **Regression:** [ ] n/a
- **Documentation:** [ ] the plan itself
- **Completion Status:** ☐ · **Reviewer Notes:** — · **Next Task:** T-053 (created by this task)

---

# Task Dependency Quick Map

```
T-001 → T-002 → {T-009, T-017, T-025, T-034, T-037}
T-001 → {T-003 → T-004, T-005 → T-006 → T-007 → T-008, T-027}
T-005 → {T-011 → T-012 → T-013, T-014 → T-015(+T-004) → T-016}
T-009 → T-010
T-017 → T-018 → T-019 → T-020 → T-021 → {T-022, T-023 → T-024}
T-025 → T-026(+T-019)
T-027 → {T-028, T-029 → T-030 → T-032(+T-023), T-033}
T-029 + T-008 → T-031
T-034 → T-035 → {T-036, T-037 → T-038}
T-015 + T-013 → T-039 → T-040 → T-041 → {T-042, T-047}
T-041 + T-023 → T-043
T-033 + T-016 → T-044 ;  T-024 + T-022 → T-045 ;  T-044+T-038+T-045 → T-046
T-047 + T-031 → T-048 → T-049
T-028 → T-050 → T-051
Phases 1–7 → T-052
```

**Totals:** 52 tasks · Phase 1: 16 · Phase 2: 10 · Phase 3: 7 · Phase 4: 5 · Phase 5: 5 · Phase 6: 4 · Phase 7: 4 · Phase 8: 1 (spike)











