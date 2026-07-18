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
