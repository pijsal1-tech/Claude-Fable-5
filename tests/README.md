# Test Suite

## Layout
- `tests/unit/` — fast, isolated tests
- `tests/integration/` — multi-module / filesystem tests (`-m integration`)
- `tests/fakes/` — test doubles (`FakeProvider`)
- `tests/fixtures/sample_project/` — 12-file multi-language fixture project
  (JS import graph, Python def/caller graph, `.env` with **FAKE** keys for
  SafeReader R-204 tests)

## Key fixtures (conftest.py)
- `sample_project` — isolated tmp copy of the fixture project per test
- `fake_provider` — fresh `FakeProvider` per test

## FakeProvider quick reference
```python
fp = FakeProvider(responses=["r1", "r2"])   # scripted queue
fp = FakeProvider(responder=lambda p, h, s: f"echo:{p}")
fp.fail_next(TimeoutError("boom"))          # one-shot failure
fp.fail_always = ValueError("dead")         # permanent failure
fp.latency_s = 0.05                         # simulated latency
fp.calls / fp.call_count / fp.last_call     # assertions
```

## Frame-Parity Harness (T-111, R-804)
`tests/frame_harness.py` records the **full WS frame sequence** of a
fixture chain run — through the production `server._RunnerWSAdapter` —
and compares two recordings **byte-for-byte** (canonical sorted-key
JSON), after normalizing only the inherently nondeterministic fields
(`duration_ms` / `elapsed_seconds` / `budget` / `run_id` — the same
list as `test_dispatch_parity`).

```python
from tests.frame_harness import (record_inproc_chain_frames,
                                 record_worker_chain_frames,
                                 assert_frame_parity)

inproc = record_inproc_chain_frames(tmp_path, provider_factory, REQ)
worker = record_worker_chain_frames(tmp_path, provider_factory, REQ,
                                    redis_client)  # real Redis, uuid keys
assert_frame_parity(inproc.frames, worker.frames)  # loud diff on mismatch
```

- Consumers: `tests/integration/test_worker_parity.py` — the R-804
  acceptance ("byte-identical WS frame sequence vs in-proc"), harness
  sensitivity proofs (mutated value / extra field / type change /
  dropped frame / reorder all caught), and the WS latency guard
  (rerun-once-before-failing, like the other benches).
- Worker-side recordings need a running Redis (skipif otherwise);
  sensitivity tests run without it (in-proc baseline + mutation).

## Running
```bash
./scripts/check.sh        # types + full suite
python -m pytest          # tests only
```
