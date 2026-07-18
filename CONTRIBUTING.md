# Contributing

## Cancellation Checkpoint Placement Rule (R-105 / T-015)

Cancellation in this codebase is **cooperative**. A `RunTicket.cancel()` only
raises a flag; nothing is interrupted mid-flight. The run honestly stays
`running` (and visible in `ExecutionRegistry.list_active()`) until the
executing loop *observes* the flag at a **checkpoint** and finishes the
ticket itself. This section is the contract every executor must follow.

### Where checkpoints go

Checkpoints are placed **only at natural boundaries** — never inside a
provider request, file write, or command execution:

| Mode | Checkpoint locations |
|---|---|
| **chain** (`chain/executor.py`) | `_check_cancelled(run)` at the **head of every step iteration** and **before every retry** of a failed step. |
| **agent** (`chain/agent_loop.py`) | `_is_cancelled()` at the **head of every loop iteration** and **before executing each tool call**. |
| **delegate** (`chain/delegate.py`) | `_checkpoint(ticket)` at **every stage boundary**: before Brief, before Implement, before Review, and before **each** rework dispatch. |

Consequences of this rule:

- A cancel issued **during** a hung provider call takes effect at the *next*
  boundary — the in-flight request is allowed to return (or time out), but
  **no further step/tool/stage ever starts**.
- There is **no mid-request abort** and no thread killing. Ever.

### Rules for new executors

If you add a new execution mode (a new `kind` in `core/execution.py`):

1. Accept an optional `ticket: RunTicket | None = None` parameter — the
   no-ticket path must behave **identically** to before (regression rule).
2. Call your checkpoint at **every loop head** and **before every retry**.
3. On observing cancellation, raise your mode's dedicated exception
   (`ChainCancelled` / `DelegateCancelled` / loop-exit flag) — do not
   `return` silently from deep inside the loop.
4. **The executing bridge owns the ticket lifecycle**: `ticket.finish(...)`
   must happen in the bridge's `finally` block, mapping the run's terminal
   status to exactly one of `completed | failed | cancelled`. The server
   never sniffs frames to finish tickets.
5. A run parked in a non-terminal wait state (e.g. delegate
   `waiting_approval`) keeps its ticket **alive**; the resuming call
   (`land()` / `reject()`) finishes it.
6. Terminal ticket states are **immutable** — never call `finish` twice.

### Single-run policy

`ExecutionRegistry` enforces **cross-kind mutual exclusion per project**:
while any chain/agent/delegate run is active, a second dispatch of *any*
kind receives `RunBusyError` and the client gets a `busy` frame carrying
the active run id. Do not add per-mode guards; the registry is the single
source of truth.
