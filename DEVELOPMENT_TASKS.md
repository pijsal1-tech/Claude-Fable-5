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
