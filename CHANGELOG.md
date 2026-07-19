# Changelog

## [Unreleased]

### ⚠️ BEHAVIOR CHANGE
- **R-104 (T-012): chain results no longer auto-write files.**
  Previously `ChainBridge._run_chain` applied chain output in a `finally`
  block with **no approval — even on partially-failed runs** — while
  `config.yaml` claimed `auto_execute: false`. Now:
  - Apply moved out of `finally` into the **success path only**
    (`run.status == "completed"`); a crashed/failed/cancelled chain writes
    **nothing** (`finally` only clears the active-run slot).
  - Every apply goes through `ApprovalGate` (T-011). With
    `auto_execute: false` (the default) the gate runs in **interactive**
    mode: the client receives a `chain_approval_request` WS frame listing
    the proposed actions and must reply with `chain_approval_response`
    `{request_id, approved, payload_hash}` within 120s, else **deny**.
    A `chain_approval_verdict` frame reports the decision either way;
    `chain_apply_result` follows only on approval.
  - **Migration:** users who relied on implicit auto-apply must set
    `auto_execute: true` in `config.yaml` — the gate then runs in `auto`
    mode whitelisting chain action kinds (`write`/`edit`/`command`),
    restoring one-shot behavior but from the success path only and with
    every verdict audit-logged.
  - A bridge constructed **without** a gate stages only (emits
    `chain_actions_staged`) and never writes — there is no silent
    fallback path left.

### Added
- **R-203 (T-023): `ContextBudget` — token-accounted, importance-ordered
  context packing (built unwired; wiring lands in T-024).**
  New `context/budget.py`: four tiers
  (`must_have`/`high`/`normal`/`opportunistic`), pluggable `TokenEstimator`
  protocol with `CharsPerTokenEstimator` (chars/4) default, deterministic
  packing that drops lowest tier first / largest item first (tie → latest
  inserted first) with an explicit `dropped[]` report
  (`DroppedItem(key, tier, tokens, reason)`), a 10% safety margin on
  `budget_tokens = (model_window − reserved_output) × (1 − margin)`
  (R-203 risk clause), and must_have overflow handling via a per-item
  `SummarizeHook` — must_have items are **never dropped**; if they still
  exceed the budget after summarization the result is kept and flagged
  `overflowed=True`. `PackResult.to_dict()` gives a JSON-serializable log
  summary; kept items preserve insertion order. Tier semantics table lives
  in the module docstring. Tests: `tests/unit/test_context_budget.py`
  (63 tests) — seeded property test (must_have never in `dropped[]`, lower
  tiers fully exhausted before higher ones are touched), packing
  determinism across repeated calls and fresh instances, admission/drop
  ordering incl. tie-breaks, margin math (floor, custom margins,
  constructor validation), estimator behavior, all summarize-hook paths,
  and the R-203 oversized-fixture integration (fits window, `dropped[]`
  non-empty, must_have retained). Suite: **302 passed** (239 + 63).
- **R-202 (T-022): map_reduce execute-step routed through ContextBundle —
  measured 76.4% prompt-size reduction on the duplication fixture.**
  `build_map_reduce`'s `mr_execute` files-block is now built via
  `ContextBundle` (`source_kind="map_input"`): each unique body renders
  once with the verbatim legacy fencing (`START/END OF SOURCE CODE`),
  duplicate-content files become one-line `📎 … لم يُكرَّر` references
  naming the body owner — no file disappears, no body repeats. Map steps
  keep their full per-file bodies and dependency results are never elided
  (R-202 risk clause). `metadata["dedupe_refs"]` exposes the reference
  count for observability. Regression suite
  `tests/unit/test_map_reduce_dedup.py` (7 tests): the literal ≥40%
  assertion vs. the reconstructed legacy prompt (actual: 76.4%,
  15,387 → 3,635 chars on a 5-file/4-duplicate fixture), unique body
  exactly-once, every path still mentioned (4 references), differing
  contents produce zero dedupe, map steps untouched, metadata count, and
  a full ChainExecutor E2E over FakeProvider asserting the *sent*
  mr_execute prompt contains one body + 4 reference notes.
- **R-202 (T-021): ContextBundle with sha256 content-dedupe, provenance,
  and a reference-aware renderer — same file body can never render twice.**
  New `context/bundle.py`: `ContextBundle` gains a second dedupe layer —
  the T-018 identity key `(source_kind, path)` still rejects duplicates
  (first-wins, unchanged), while a content key (`sha256`) accepts new
  identities carrying an already-seen body as a **reference**
  (`BundleEntry.is_reference=True` + `duplicate_of=<owner path>`).
  `render_prompt_block()` emits each body exactly once and an
  "already attached above" note for references (None-content/huge-file
  items skipped, never hashed — quirk preserved); `debug_dump()` returns
  JSON-serializable provenance rows (index/source_kind/path/content_hash/
  chars/is_reference/duplicate_of) answering "why did the model see X".
  `context/engine.py` re-exports `ContextItem`/`ContextBundle` from the
  new module so every existing import path (sources, facade, tests) is
  untouched; facade surface (`items`/`paths`/`len`) shows references as
  full items — only the renderer elides, so T-017/T-019 goldens stay
  byte-exact. 13 new unit tests in `tests/unit/test_context_bundle.py`
  (acceptance: two sources + same file → one body + one reference;
  same-content different-paths; renderer golden; provenance dump;
  engine-integration; frozen entries).
- **R-201 (T-020): ContextBuilder converged onto ContextEngine — chain
  prefetch now shares the single-scan reading path.**
  `ContextBuilder.gather()` builds **one `ProjectScan`** per request and
  threads it through all four phases; the duplicated reading paths are
  deleted (`rglob(basename)` fallback per missing file, `rglob("*")` full
  scan per code search, per-dir `iterdir` reads → all in-memory filters
  over `scan.files`). `AgentLoop._auto_prefetch` delegates to the adapter
  with identical WS frames and Knowledge transfer. Acceptance grep: zero
  `.rglob(` in `chain/context_builder.py` (only walk left in the chain is
  `agent_tools.tool_search_files`, a user-invoked tool — out of R-201
  scope). Behavior pinned **before** the refactor by new chain-prompt
  goldens (`tests/goldens/chain/`: 6 scenarios × items/progress-events/
  summary/prompt-section, `<ROOT>`-normalized, deterministic capture) plus
  structural+behavioral enforcement in
  `tests/unit/test_context_builder_convergence.py` (no-rglob grep test,
  exactly-one-scan counter for `gather()`/`gather_context()`, fallback
  parity). Deprecation note added on the module and class: new context
  features belong in `context/sources/`, not here.
- **R-201 (T-019): Keyword + Structure sources; inline context block deleted
  from `server.py` — the WS handler now calls one engine method.**
  - `context/sources/keyword.py` — `KeywordSource` (`kind="keyword"`): the
    flexible stem-match half of the legacy block (`stem in p.name`,
    ≡ `rglob(f"*{stem}*")`), in-memory over the shared scan.
    `MentionSource` narrowed to **exact-name only**; shared read logic
    extracted to `build_items()` (read failure ⇒ `content=None`).
  - `context/sources/structure.py` — `StructureSource`
    (`kind="structure"`): one `<project_structure>` item =
    `FileManager.get_project_context()` verbatim (failure ⇒ `""`,
    legacy tolerance).
  - `context/facade.py` — `gather_message_context(project_root,
    user_text) -> MessageContext(mentioned_files, user_text_with_files,
    project_context)`: composes [Mention → Keyword → Structure], merges
    file items with path-dedupe (mention wins) + the honest total limit,
    renders the byte-exact legacy injection. This is the **single call**
    the WS handler makes.
  - **`server.py`: the ~70-line inline block deleted** (mention regex,
    per-word `rglob` storms, injection loop, `get_project_context`) —
    replaced by one `gather_message_context()` call with a safe fallback;
    the lying `MAX_MENTIONED = 100` constant is gone from production.
    Downstream consumers (`mentioned_files` routing, `user_text_with_files`
    prompts, `project_context`) untouched.
  - `context/ARCHITECTURE.md` — context-flow doc (diagram, parity
    contracts, perf comparison, extraction status).
  - Tests (`tests/unit/test_context_engine.py` → 20): goldens now replayed
    **through the facade** for all 3 fields (acceptance), mention=exact-only
    / keyword=stem-only split, structure parity vs `get_project_context()`,
    facade dedupe (mention wins over keyword), structural
    inline-block-deleted check (no `.rglob(`/`MAX_MENTIONED = 100`/
    `stems_to_search`/`target_files_content` in server.py code lines +
    facade import & call present). Suite: **194 passed**.
- **R-201 (T-018): `ContextEngine` skeleton + `MentionSource` — first source
  out of the monolith (unwired yet).** New `context/` package:
  - `context/engine.py` — `ContextRequest` / `ContextItem` (provenance via
    `source_kind`; `content=None` = mentioned-without-content, the pinned
    huge-file quirk) / `ContextBundle` (ordered, first-wins dedupe on
    `(source_kind, path)`) / `ContextSource` runtime protocol /
    `ContextEngine.gather()` — builds **one `ProjectScan` per request**
    (single sorted `rglob("*")` walk) shared by all sources; a broken
    source is isolated (legacy tolerance), injectable `scan_factory`.
  - `context/sources/mention.py` — `MentionSource`: legacy mention behavior
    (exact-name then stem matching, verbatim regexes & stopwords) as
    in-memory filtering over `scan.files` — **zero per-word `rglob`
    storms** (legacy was O(files × words) tree walks per message).
    Equivalence: `rglob(X)` matches file *names*, so filtering the
    globally-sorted list reproduces `sorted(rglob(X))` exactly — the
    T-017 golden order. `render_legacy_injection()` reproduces the legacy
    `user_text_with_files` byte-for-byte for the future wiring.
  - **Lying constant fixed**: legacy `MAX_MENTIONED = 100  # حد أقصى 10
    ملفات` → `MAX_MENTIONED_FILES = 10` with an honest comment (all T-017
    goldens include ≤2 files — no golden affected).
  - `context/AUTHORING.md` — source-authoring guide stub (no tree walks,
    provenance, None-content, determinism, honest limits).
  - `scripts/check.sh` mypy gate extended to `core/ context/`.
  - Tests: `tests/unit/test_context_engine.py` (15) — all 6 T-017 goldens
    replayed **byte-exact through the new source**, huge-file None-content,
    **single-scan-per-gather assertion** (counting factory + 2 sources),
    no-tree-walk enforcement (rglob monkeypatched to raise), constant
    fixed + limit enforced, bundle dedupe, broken-source isolation,
    protocol conformance, legacy term-extraction rules. Suite: **189
    passed**. Nothing wired into server/chain/agent yet — behavior
    unchanged everywhere.
- **R-201 (T-017): legacy context-collection goldens pinned.**
  Parity net before extracting `server.py`'s inline context block into a
  `ContextEngine` (R-201). New `tests/goldens/context/`:
  - `harness.py` — verbatim port of the legacy block (mention regex →
    exact-name + stem `rglob` searches → numbered-content injection →
    `get_project_context()`), with two order-only determinism fixes
    (sorted `rglob` results, sorted set iteration — the legacy *order* is
    process-random; the included-file *set* is unchanged). All quirks
    preserved deliberately: the lying `MAX_MENTIONED = 100  # حد أقصى 10
    ملفات` constant, no secret/size filtering at mention stage, huge
    files "read" in the header with silently-empty content.
  - 6 goldens against `tests/fixtures/sample_project/`: `mention_only`,
    `keyword_only`, `mixed`, `no_context`, `huge_file` (>500KB setup
    file), `arabic_filename` (Arabic-named setup file). Absolute paths
    normalized to `<ROOT>` — goldens are machine-portable.
  - `capture_goldens.py` regenerator (`python3 -m
    tests.goldens.context.capture_goldens`) + `test_replay_goldens.py`
    (10: 6 parametrized byte-exact replays + 4 quirk pins). Regeneration
    verified deterministic (double-capture diff-clean).
  Suite: **174 passed**. Read-only capture — zero production changes.
- **R-105 (T-016): WS control surface — `list_runs` / `cancel_run`.**
  Two additive WS message types backed by the `ExecutionRegistry`:
  - `list_runs {}` → `runs_list {runs: [{id, mode, state, started_at,
    is_cancelled, cancel_reason, finished_at}]}` — every run the registry
    knows, active **and** terminal (honest history for the UI).
  - `cancel_run {run_id, reason?}` → `cancel_run_result {run_id,
    acknowledged, error?}` — raises the **cooperative** cancel flag on the
    target ticket (observed at the run's next T-015 checkpoint; no
    mid-request abort). `acknowledged=false` + `error="not_found"` for
    unknown/terminal runs; `error="missing_run_id"` for an empty id.
  - Implementation: pure frame-builder helpers `_list_runs_frame()` /
    `_cancel_run_frame()` in `server.py` + two handler branches after
    `chain_status`. Existing frames untouched (additive protocol change).
  - Tests: `tests/integration/test_ws_run_control.py` (8) — list empty /
    active / terminal; cancel acknowledged (flag up, state honestly
    `running`), not_found (unknown + terminal), missing_run_id; **E2E
    acceptance**: start pipeline run → list shows `running` → `cancel_run`
    → stops before next step (1 provider call) → list shows `cancelled`.
    Suite: **164 passed**. README WS protocol tables updated.
- **R-105 (T-015): tickets wired through all three execution modes; `ActiveRunHolder` deleted.**
  Every dispatch (chain / agent / delegate) now allocates a `RunTicket` from
  the global `ExecutionRegistry` and cancellation finally *reaches the loops*:
  - **chain** — `ChainExecutor._check_cancelled(run)` at every step-loop head
    and before every retry; a cancelled ticket propagates into the run's
    `CancellationToken` → `ChainCancelled` → run `cancelled`, zero applies.
  - **agent** — `AgentLoop._is_cancelled()` (local stop flag OR ticket) at
    every iteration head and before each tool call; `run()` is now a
    lifecycle wrapper that finishes the ticket (`completed|failed|cancelled`).
  - **delegate** — **newly cancellable**: `DelegateCancelled` +
    `_checkpoint(ticket)` at all 4 stage boundaries (before Brief /
    Implement / Review / each rework); emits a `delegate_cancelled` frame;
    `waiting_approval` keeps the ticket alive and `land()`/`reject()`
    finish it.
  - **Ticket lifecycle is owned by the executing bridges** (`finally`
    blocks) — the server no longer sniffs terminal WS frames.
  - ⚠️ **Behavior change:** `core/active_run.py` (`ActiveRunHolder`) is
    **deleted**; the registry now enforces the single-run policy
    **across kinds** (an active agent run blocks a chain start and vice
    versa — previously only chain runs were guarded). The `busy` WS frame
    now carries `active_run` from the registry; switch-model /
    switch-project 409 guards use `execution_registry.list_active()`.
  - Checkpoint placement contract documented in **CONTRIBUTING.md** (new).
  - Tests: `tests/integration/test_ticket_cancellation.py` (9 — cancel
    matrix for all 3 modes + uncancelled regressions + structural
    holder-deletion check); `test_concurrent_run_guard.py` rewritten
    against the registry (5). Suite: **156 passed**.
- **R-105 (T-014):** `ExecutionRegistry` + `RunTicket` (`core/execution.py`) —
  the authoritative run-lifecycle record, shipped standalone (unit-tested,
  unwired; all three execution modes adopt tickets in T-015, which then
  deletes the interim `ActiveRunHolder`). `register(kind, project_id) ->
  RunTicket` (kinds: chain/agent/delegate) with **per-project mutual
  exclusion** (configurable; a busy project raises `RunBusyError`, exactly
  one winner under a concurrent thundering-herd — proven by a 16-thread
  barrier test); `lookup`/`list_active`/`list_all`; `finish(status)` with
  terminal states `completed|failed|cancelled` that are **immutable** (no
  double-finish, no cancel-after-finish, late heartbeats can't revive) and
  atomically free the project slot; **cooperative** `cancel(reason)` — the
  flag is raised but the run honestly stays `running` (and listed) until the
  executor observes it at a checkpoint and finishes itself (mirrors
  `CancellationToken` semantics so T-015 adapts without behavior change,
  while `core` stays free of `chain` imports); `heartbeat()` + optional
  `ttl_seconds` with `reap_stale()` force-failing silent runs so a crashed
  worker never holds a project slot forever. Single-lock protected,
  injectable clock, full state diagram in the module docstring,
  `to_dict()` snapshot ready for the future `list_runs` WS command.
  22 unit tests (`tests/unit/test_execution.py`).
- **R-104 (T-013): unified consent — agent mode now goes through the same
  `ApprovalGate` instance as chain mode.** `AgentLoop` accepts an
  `approval_gate` constructor parameter (wired in `server.py` from the same
  global gate that serves `ChainBridge`), so `auto_execute: false` means
  interactive approval for **both** paths and a single audit log records
  `source="agent"` and `source="chain"` requests side by side. The agent
  path's separate ad-hoc approval machinery (its own `threading.Event`,
  manual payload-hash computation, and private 60s timeout) was **deleted**;
  `_request_approval` builds an `ApprovalRequest` and blocks on
  `gate.request(...)`, `approve_command` is a thin `gate.resolve` wrapper
  (with SHA-256 payload-hash verification against stale/forged approvals),
  and `cancel()` resolves any pending request as a denial so a cancelled run
  unblocks immediately. Without a gate, commands are safely auto-rejected —
  no silent execution fallback. Legacy `agent_step`/`awaiting_approval` WS
  frame shape preserved (ids/hashes now sourced from the gate). Covered by
  10 integration tests (`tests/integration/test_agent_gated_approvals.py`):
  approve/reject/timeout matrix, deny-mode, auto-whitelist, no-gate
  rejection, forged-hash, cancel-unblock, shared-gate audit, and a
  structural test asserting the ad-hoc machinery is gone.
- **R-104 (T-011):** `ApprovalGate` service (`core/approval.py`) — the single
  consent checkpoint for workspace mutations, shipped standalone (wired into
  the chain path in T-012). `request(ApprovalRequest) -> Verdict` with three
  modes: `auto` (approve only whitelisted action kinds — default whitelist is
  read/format only; non-whitelisted kinds fall back to interactive when a
  callback is wired, else deny), `interactive` (emits the request via
  `on_request` callback and blocks until `resolve(request_id, approved,
  payload_hash)` or `timeout_seconds` → deny), `deny` (kill-switch).
  `resolve` requires both a matching `request_id` **and** SHA-256
  `payload_hash` — same anti-stale/forged mechanics as the agent loop.
  Every verdict (approve/deny/timeout, all paths) lands in an in-memory
  audit log with source, run_id, action kinds/count, mode, reason,
  timestamp. 19 unit tests (`tests/unit/test_approval.py`) cover the full
  mode matrix, timeout→deny, forged-hash rejection, callback-crash safety,
  and audit completeness.

- **R-103 (T-010):** Provider contract enforcement, two layers:
  1. `tests/contracts/provider_contract.py` — `ProviderContractMixin` with 8
     signature-level checks (subclasses `BaseProvider`; `send`/`stream`
     accept `(prompt: str, history=None, system_prompt="")`; `send` returns
     `str`; `stream` is a generator; `is_available(self)`; non-empty
     `name`/`description`). Applied to all 6 providers (Genspark, DeepSeek,
     UseAI, AlleAI, MockProvider, FakeProvider) — 48 contract tests, no
     provider instantiation needed. Adding a provider = add one 3-line class.
  2. mypy is now a **gate** in `scripts/check.sh`
     (`mypy --ignore-missing-imports --follow-imports=silent providers/ chain/`,
     no `|| true`). Fixed all 95 revealed errors across 13 files — notable:
     `DelegateRun.get_phase` now raises `KeyError` instead of returning
     `None` (killed 17 union-attr errors); `ChainRun.budget` is non-Optional
     (always built in `__post_init__`, killed 7); `genspark.py` dynamic
     module typed `Any` + spec/loader None guard (killed 40).

### Fixed
- **R-101 (T-004):** Deleted the dead `_active_chain_run` module guard in
  `server.py` (it was read at the switch handlers but never assigned, so it
  never blocked anything). Chain dispatch (both the smart-router path and
  `chain_message`) now goes through a thread-safe `ActiveRunHolder`
  (`core/active_run.py`): a second concurrent chain start is rejected with a
  structured `busy` WS frame; the slot is released on `chain_finished`,
  `chain_error`, failed start, and successful `chain_cancel`.
  Model/project switching during an active chain still returns HTTP 409,
  now backed by a guard that actually works.

### Fixed
- **R-103 (T-009):** Fixed the DelegateBridge ↔ provider contract violation:
  the three delegate call sites (write_brief / dispatch / review) passed
  `list[Message]` to `send(prompt: str, ...)` — a latent crash on any
  conforming provider. New `DelegateBridge._to_prompt_history(messages)`
  renders the list to a string (single user message → verbatim; multiple →
  role-tagged `[USER]:` / `[ASSISTANT]:` blocks); all three sites now send
  rendered strings. Proven by a strict-typed FakeProvider (TypeError on
  non-str prompt) with the rendering pinned as a golden test.

- **R-102 (T-008):** Rewrote the switch handlers; deleted all private-attribute
  pokes. `api_switch_project` now IS `ctx.switch_project(path)` (one atomic
  swap; old handle invalidated; legacy `fm`/`cmd_runner` globals re-pointed at
  the ctx-owned objects). `api_switch_model` publishes once via
  `ctx.switch_model(provider)`: `ChainBridge._provider` and
  `DelegateBridge._provider` are now call-time properties reading
  `ctx.active_provider`; `RequestRouter` gained a public
  `active_provider_name` property (the `_active_provider_name` poke is gone —
  grep outside its owner returns nothing). New `server._active_provider()`
  resolves the live provider for the remaining direct readers
  (/api/providers, agent send fallback, stream worker, delegate lazy init).
  The dead `global provider` re-pointing in the switch handler was removed.
  The WS `detected_dir` project switch goes through `ctx.switch_project` too.

- **R-102 (T-007):** Killed the stale-reference consumers. `AgentTools`
  (`fm`/`cmd`/`project_root`), `ActionApplier` (`_fm`/`_cmd`) and
  `ChainBridge` (`_project_root`/`_runs_dir`) now accept `ctx` and resolve
  `ctx.project.*` **at call time** via properties — never caching — so a
  project switch is observed immediately by agents, chain apply, and run
  storage. `AgentLoop._auto_prefetch` inherits the fix (it reads
  `tools.project_root` per call). `main()` builds `ctx` BEFORE consumers and
  injects it; `api_switch_project` calls `ctx.switch_project()` to keep the
  composition root in sync (full handler rewrite lands in T-008). Static
  constructor args remain a fallback for ctx-less construction (tests).

### Added
- **R-102 (T-005/T-006):** `core/app_context.py` — `AppContext` composition
  root + `ProjectHandle` (atomic swap, stale-handle invalidation via
  `StaleHandleError`). `main()` now builds `ctx` (`server._build_ctx`) after
  wiring; during migration the legacy module globals remain one-way aliases
  of the ctx fields so both paths see identical objects. `ws_handler` is now
  registered explicitly (`sock.route("/ws")(ws_handler)`) so it stays a
  testable module-level callable; `pong` frames carry a `ctx` reachability
  flag (ignored by the frontend).
- **T-001/T-002/T-003:** pytest infrastructure (`tests/`, `scripts/check.sh`,
  `requirements-dev.txt`), `FakeProvider` + 12-file fixture project
  (`tests/fixtures/sample_project/`), and `core/active_run.py`.
