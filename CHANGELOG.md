# Changelog

## [Unreleased]

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
