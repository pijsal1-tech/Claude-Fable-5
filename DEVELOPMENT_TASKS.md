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
