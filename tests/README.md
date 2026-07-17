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

## Running
```bash
./scripts/check.sh        # types + full suite
python -m pytest          # tests only
```
