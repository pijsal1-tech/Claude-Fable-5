# Phase 8 Plan — Extensibility (R-801 … R-805)

> **Produced by:** T-052 Phase 8 Scoping Spike · 2026-07-20
> **Output:** this plan + task entries **T-100 … T-114** appended to `DEVELOPMENT_TASKS.md`
> (numbered from T-100 because T-053 … T-066 are already taken by the
> Review-Merge Additions and the Phase 9 UI track).
> **No production code was produced by this spike** — all experiments were throwaway.

---

## 1. Spike Finding — Entry-Point Plugin Loading (R-801)

**Question:** does `importlib.metadata.entry_points` give us safe discovery,
validation, and quarantine for third-party strategy plugins?

**Experiment (throwaway, executed and then deleted):** built a toy package
`demo-strategy` declaring two entry points in the `webdev_ai.strategies` group —
one valid (`DemoStrategyBuilder` with `build()` + `routing_hints`) and one whose
module raises `ImportError` at import time. Loader loop:

```python
from importlib.metadata import entry_points
for ep in entry_points(group="webdev_ai.strategies"):
    try:
        obj = ep.load()                       # import happens HERE, per-plugin
        assert callable(getattr(obj, "build", None))
        assert isinstance(getattr(obj, "routing_hints", None), dict)
        loaded[ep.name] = obj
    except Exception as e:
        quarantined[ep.name] = f"{type(e).__name__}: {e}"
```

**Results (verified on Python 3.13.13):**

| Check | Result |
|---|---|
| Discovery finds plugins from a *separate* installed package | ✅ both `demo` and `broken` discovered |
| Broken module import is contained to `ep.load()` | ✅ `ImportError` caught, host unaffected |
| Good plugin loads while broken one is quarantined | ✅ `loaded=['demo']`, `quarantined={'broken': ImportError}` |
| Dry-run `build()` on fixture request works | ✅ returned a plan dict |

**Design conclusions locked in for R-801:**
1. **Discovery is lazy-import-safe:** `entry_points(group=...)` itself never
   imports plugin code; the import is isolated inside `ep.load()`, so a
   per-plugin `try/except` gives exactly the "failures quarantine the plugin,
   never the host" behavior the roadmap requires. No subprocess sandboxing
   needed for load-time safety.
2. **Validation gate = shape check + dry-run:** after load, verify the object is
   a class exposing `build()` and a `dict` `routing_hints`, then instantiate and
   dry-run `plan` on a canned fixture request; any exception → quarantine with a
   structured reason (surfaced in logs/UI, never a crash).
3. **Capability scoping is an API-design problem, not a loading problem:**
   plugins receive a narrow `PluginContext` (ContextEngine *views* + emit hooks),
   never `fm` or raw session state. This is enforced by constructor signature,
   not by import machinery.
4. **Python 3.13 note:** use the keyword form `entry_points(group=...)`
   (the ≥3.10 selectable API); no `importlib_metadata` backport needed.

---

## 2. Decision — Embedding Backend for R-802 (Layered Memory, semantic layer)

**Chosen: provider-backed embeddings** — call an OpenAI-compatible
`/embeddings` endpoint through the existing `providers/` HTTP layer, store
vectors in a per-session JSONL sidecar (`sessions/<id>.embidx.jsonl`), score
with pure-Python cosine (lists of floats; no numpy).

**Why this fits the project:**
- **Zero new heavy dependencies.** The dependency set stays
  `flask flask-sock requests websockets pyyaml` + test tools; CI stays fast.
- **Matches R-802's own escape hatch:** retrieval is *async with
  fallback-to-skip* — if the provider is down/unconfigured, the semantic layer
  degrades to working+episodic layers only. A remote backend is acceptable
  precisely because absence is already a designed-for state.
- **Scale sanity:** per-project memory is hundreds-to-low-thousands of chunks;
  brute-force cosine over ≤5k vectors in pure Python is well under the
  `opportunistic`-tier latency budget. No vector DB needed.

**Alternatives considered and rejected:**

| Option | Rejected because |
|---|---|
| `sentence-transformers` (local) | pulls torch (~2 GB), slow cold start, breaks the lightweight CI/deps posture |
| `faiss` / `chromadb` / `qdrant` | native deps + a service to run; overkill for ≤5k vectors per project |
| TF-IDF / BM25 (lexical only) | not semantic; fails the R-802 acceptance ("turn-10 decision answered *with retrieval on*, fails without") for paraphrased queries. May be revisited as an *offline* fallback later — explicitly out of scope for the first cut. |

**Interface guard:** hide the choice behind an `Embedder` protocol
(`embed(texts) -> list[list[float]]`) so a local backend can be swapped in
later without touching the index or the ContextEngine source.

### 2.1 Retrieval flow (T-105 — as built)

```
user message
     │
     ▼
ContextEngine.gather(request)
     │  sources: [Mention, Keyword, Symbol, Semantic(R-206),
     │            MemorySource(T-105)*, Structure]
     │  (*) optional — injected per session; absent = legacy composition
     ▼
MemorySource.collect(request, scan)          tier: opportunistic ONLY
     │
     │  worker thread ── future.result(timeout=1.0s)
     │  timeout / any failure ⇒ []  (bundle build proceeds without us)
     ▼
  ┌──────────────────────────────┬──────────────────────────────────┐
  │ semantic layer (T-104)       │ episodic layer (T-103)           │
  │ SemanticIndex.search(msg)    │ word-overlap over episode        │
  │  → cosine top-k              │  goal/outcome/decisions          │
  │  provider down ⇒ available=  │  → best MAX_EPISODES, newest-    │
  │  False ⇒ contributes nothing │  first tie-break                 │
  │ items: <memory:sem:chunk_id> │ items: <memory:episode:run_id>   │
  └──────────────────────────────┴──────────────────────────────────┘
     │
     ▼
ContextItems (kind="memory", symbolic paths — never enter
mentioned_files; budgeted at "opportunistic" so must_have/high
are never displaced)
```

---

## 3. Decision — Redis Client + Deployment Shape for R-804 (Worker Pool)

**Client: `redis-py` (`redis>=5.0`)** — the official client;
`aioredis` was merged into it and is deprecated, and `redis.asyncio` ships in
the same package if the event-streaming path ever needs async. Installed as an
**optional extra** — the in-memory backends remain the default and
single-process stays first-class (no Redis import at module top level;
lazy import inside the Redis backend classes only).

**Deployment shape: one standalone Redis instance via `REDIS_URL`**
(no Cluster, no Sentinel for v1 — a single host serving a handful of workers
does not justify them; the config key leaves room to add them later).

**Primitive mapping (grounded in existing architecture):**

| Concern | Redis primitive | Notes |
|---|---|---|
| Work queue (Runner dispatch) | Redis **Stream** `wq:runs` + consumer group `workers` | `XADD`/`XREADGROUP`/`XACK` gives at-least-once delivery + `XAUTOCLAIM` reclaim of crashed-worker entries — strictly better than `LPUSH/BRPOP` (which loses in-flight jobs) |
| EventBus backend | Redis **Stream** per run `ev:<run_id>` | ordered, replayable — required for the "byte-identical WS frame sequence" acceptance; Pub/Sub rejected (fire-and-forget, drops frames on slow consumers) |
| Per-project lease | `SET lease:<project_id> <worker_id> NX PX <ttl_ms>` | renew by ownership-checked script; expiry = automatic failover |
| Registry backend | Redis hashes `reg:*` | mirrors the in-mem dict backend 1:1 |

**Parity requirement drives the test plan:** the R-804 acceptance ("chain run
on worker = byte-identical WS frame sequence vs in-proc") is testable because
both EventBus backends deliver ordered frames; T-111 builds the recording
harness before any latency tuning.

---

## 4. Task Breakdown — T-100 … T-114

Slicing follows the file's established granularity (~90–120 min per task).
Roadmap day-estimates map as: R-801 3d→3 tasks, R-802 5d→3, R-803 4d→2,
R-804 8d→4, R-805 5d→3. Dependencies are resolved to **real task numbers**:

| Req | Tasks | Depends on (tasks) |
|---|---|---|
| R-801 Strategy Plugin Registry | T-100 → T-101 → T-102 | T-035, T-041 |
| R-802 Layered Memory | T-103 → T-104 → T-105 | T-032, T-057 |
| R-803 Pluggable Planners | T-106 → T-107 | T-036, T-041 |
| R-804 Worker Pool | T-108 → T-109 → T-110 → T-111 | T-041, T-046, T-047, T-048 |
| R-805 Persistent Project Memory | T-112 → T-113 → T-114 | T-031, T-049, T-105 |

Suggested execution order inside Phase 8: **R-801 → R-803 → R-802 → R-805 → R-804**
(worker pool last: highest complexity, most dependencies, and parity harness
benefits from everything else being stable). Note R-802 requires T-057
(Minimal SemanticSource, Review-Merge Phase 2) to land first.

**Phase 8 Definition of Done (from the roadmap, unchanged):** plugin demo +
quarantine proven · semantic recall shows causal value · planner swappable via
config · worker parity green · project memory inspectable / provenance /
staleness-aware.

Full task entries (format-identical to the rest of the file, with checkboxes
and acceptance criteria) live in `DEVELOPMENT_TASKS.md` under
"Phase 8 Breakdown — T-100 … T-114".
