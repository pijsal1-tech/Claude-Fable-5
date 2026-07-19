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
- **R-305 (T-033): truthful snapshots + run-artifact retention —
  vacuous validation and the write-only artifact graveyard both
  closed.** `chain/bridge.py`: `ProjectSnapshot` was created with an
  **always-empty** `relevant_file_hashes` map — an artifact that
  claimed to capture project state and captured nothing. New
  `_build_project_snapshot(project_root, files, file_path,
  file_content)` computes real `sha256` content hashes for the files
  the run actually touches (the ones passed into `start_chain` —
  already in memory, so no extra disk reads and no race with later
  edits), and enforces the R-305 acceptance contract: **snapshots are
  non-empty or absent — never empty-but-present** (no touched files ⇒
  `project_snapshot = None`). New `sessions/retention.py`:
  `RetentionPolicy(max_count, max_age_days, pinned, dry_run=True)`
  with a pure decision core `plan_sweep(entries, policy) → (kept,
  deleted)` (matrix-testable, no I/O) and `sweep(runs_dir, policy)`
  executing it against `.ai_runs/run-*`. Keep semantics: **pinned
  always survives** (above both limits, and doesn't consume the count
  budget), newest `max_count` unpinned entries stay, anything older
  than `max_age_days` drops even within count; a limit of `None` is
  disabled and the all-defaults policy is a full no-op (pre-T-033
  behavior). The sweep is idempotent, tolerates entries vanishing
  mid-scan, and reports honestly (a failed delete goes back to
  `kept`). First release ships **dry-run by default** (R-305 risk
  clause): the startup GC pass wired into `server.py` boot logs what
  *would* be deleted and touches nothing until the user sets
  `retention.dry_run: false` in the new `config.yaml` `retention`
  section (`max_count` / `max_age_days` / `pinned` / `dry_run`,
  documented inline; `policy_from_config` is loud on a malformed
  section, defaults safely on a missing one). Tests
  (`tests/unit/test_retention.py`, 22): real-hash snapshot assertions
  incl. the never-empty-but-present contract and files-over-file_path
  precedence; the policy matrix (no-limits no-op, count keeps newest,
  count=0, age-within-count, combined limits, pinned above both,
  pinned outside count budget); on-disk sweeps (dry-run logs and
  deletes nothing, live delete with pinned survival, idempotence,
  missing dir, default-policy regression no-op); config parsing
  (safe defaults, full parse, null limits, loud failure).
- **R-304 (T-032): tiered windowing + async summarizer — graceful
  degradation between "full history" and "amnesia".**
  `sessions/memory.py` gains `tiered_window(TieredPolicy) →
  TieredWindow`: a budget-bound window assembled as **pinned turns
  (deducted first, never evicted) → a contiguous verbatim strip of the
  most recent turns (stops at the first turn that doesn't fit — no
  gaps in front of the summary) → a stored summary of the older slice**,
  entering the window only when it actually covers dropped turns (short
  sessions are byte-identical to before — regression-pinned). The
  verbatim strip never shrinks below `recent_floor` even at
  `token_budget=0` (R-304 risk clause), and `TieredWindow.degraded` is
  truthful: turns dropped without summary coverage = explicit hard
  cutoff. Summaries are **artifacts in the JSONL stream itself**
  (`kind="summary"` records with `text`/`covers_until` exclusive/`ts`) —
  the log stays the single source of truth (T-029 principle), summaries
  are auditable in the session log, and the effective summary is the
  last such record on replay (unknown-kind skipping from T-029 keeps
  old readers safe). `update_summary(summarizer, upto)` is the
  synchronous core — incremental: it summarizes only the yet-uncovered
  slice, passing the previous summary text for merging, and fails
  loudly for direct callers. `maybe_update_summary_async(summarizer,
  every_n=10)` is the hot-path hook: fires a daemon thread only when
  the uncovered slice has grown ≥ `every_n` turns and no run is
  inflight (single-inflight dedup under a lock), **returns immediately
  and never raises** — a summarizer crash is recorded in
  `last_summary_error` and the window degrades to a plain cutoff;
  `wait_for_summary(timeout)` exists for tests/clean shutdown. The
  `summary()` stub from T-029 is now wired (last stored summary text or
  `None`); prompts must label summaries via `TieredWindow.
  summary_block()` which prefixes `SUMMARY_LABEL` (drift/hallucination
  risk answered by labeling, not hiding). Tests
  (`tests/unit/test_tiered_window.py`, 22): tier-assembly math
  (pinned-first deduction, contiguous strip, summary admission/
  exclusion rules), floor enforcement at zero budget, incremental
  summarization + no-op on empty slice + replay survival, async
  immediacy with a slow summarizer (timing assert < 0.2s vs 0.5s
  sleep), single-inflight dedup, not-ripe skip, failure degradation
  (error captured, no fake artifact, hard-cutoff window), loud sync
  failure, and the R-304 acceptance gate: a **100-turn simulation**
  where a fact stated at turn 5 is no longer verbatim but remains
  represented in the summary, with all verbatim turns within budget
  and `degraded=False`.
- **R-303 (T-031): Session ↔ Project binding — sessions are stamped
  with a project fingerprint and project switches are policy-checked.**
  `sessions/store.py` gains `project_fingerprint(path)` (`sha256` of the
  **resolved** root path, first 12 hex chars; empty path = unbound) and
  every `SessionMeta` now carries `project_id`, stamped at `create()` and
  re-stamped by `set_project_path()`; `rebuild_meta()` preserves it and
  legacy sidecars without the field read back as unbound (compat, no
  migration needed). The pure decision function
  `check_project_binding(bound_id, new_path, policy) → BindingCheck`
  returns `action="none"` for unbound-or-matching sessions (silent
  switch) and the policy name on mismatch; an unknown policy raises a
  loud `ValueError` (config typos must not fail silent). `server.py`
  wires it into `/api/switch-project` under three policies read from the
  new `config.yaml` `session_binding` section — `warn_only: true`
  (default) forces **warn**: the switch succeeds and a context banner is
  injected into `project_context` on every subsequent message until a
  new session starts (`/api/clear` and `/api/session/new` reset it);
  `warn_only: false` activates `session_binding.policy`: **fork** clears
  `chat_history` and opens a fresh session bound to the new project
  (response carries `binding.new_session_id`), **block** refuses the
  switch with 409 and leaves the current project untouched. Corrupt or
  missing legacy session state degrades to unbound (tolerant), while a
  bad policy string in config surfaces as a 500. Tests: unit matrix in
  `tests/unit/test_project_binding.py` (fingerprint stability +
  resolve-normalization, full bound/match×policy matrix, ValueError,
  meta stamping on create/set/rebuild, legacy-meta compat) and
  per-policy Flask E2E in `tests/integration/test_session_binding.py`
  (warn banner in response + module state + reset paths; fork clears
  history and binds; block 409 project-untouched; regressions:
  same-project switch and unbound legacy session are silent, and a
  `session_mgr`-less boot keeps the old switch path intact).
- **R-302 (T-030): the three raw-history consumers migrated to named
  window policies — behavior byte-identical, ownership centralized.**
  The actual consumer sites (pinned during migration; the initial T-029
  guess had chat/delegate swapped): (1) the history **fold** inside the
  three prompt-building providers (`alle_ai`/`deepseek`/`genspark`) was
  `history[-6:]` → `POLICY_PROVIDER_HISTORY_FOLD`; (2)
  `chain/knowledge.py::build_context` was `self._observations[-10:]` →
  `POLICY_KNOWLEDGE_OBSERVATIONS`; (3)
  `chain/delegate.py::_to_prompt_history` implicitly rendered the full
  list → explicit `POLICY_DELEGATE_RENDER` (full window). The precise
  names are aliases of the same `POLICY_DELEGATE`/`POLICY_CHAT`/
  `POLICY_FULL` objects (asserted `is`-identical), so T-029's frozen
  surface is untouched. New bridge `sessions.memory.select_history(items,
  policy)` applies `last_n` semantics to in-memory lists for consumers
  that still carry raw `list[Message]` (full `ConversationMemory` wiring
  = T-031+); `token_budget` is explicitly rejected there (whole-turn
  accounting needs `window()`). **Goldens captured pre-migration by
  running the legacy slices verbatim** (provider fold on 9 messages,
  `build_context` on 13 observations, delegate multi/single/empty
  renders) and committed as literal expected strings — post-migration
  output matches byte-exact, plus property tests
  `select_history(xs, last_n=n) == xs[-n:]` across sizes 0..30.
  **Acceptance grep is now a test**
  (`TestNoRawHistorySlicing`): no `history[-N:]` /
  `_observations[-N:]` / `chat_history[-N:]` anywhere in production
  code outside `sessions/`. Scope note: `chat_history[:-1]` in
  `server.py` is structural exclusion of the just-appended current
  message (not a window slice) — stays, documented in the policy map.
  Evidence: `tests/unit/test_history_consumers.py` — 41 tests. Full
  suite **489 passed** (448 + 41); mypy gate clean;
  `./scripts/check.sh` ALL GREEN.
- **R-302 (T-029): `sessions/memory.py` — `ConversationMemory` facade,
  the single owner of history access on top of the JSONL store.**
  API: `append(role, content, visibility="user", **extra) -> turn_id`
  (sequential ids derived from the log; a cached counter keeps append
  O(1)), `turns()`, `window(WindowPolicy)`, `pin(turn_id)` /
  `unpin(turn_id)`, plus frozen stubs `summary() -> None` (R-304) and
  `search() -> []` (R-802). **Pinning is append-only**: pins are
  `kind="pin"` marker records in the same log — no rewrite, no sidecar
  state; effective pin state = last marker per turn at replay, so it
  survives crashes exactly like messages do. **Window pipeline is a
  fixed order**: visibility filter → pinned turns set aside (they
  survive trimming) → `last_n` applied to unpinned only →
  `token_budget` charges pinned first then admits unpinned
  newest-first, whole-turn-or-drop (never mid-truncates a turn; uses
  the central `CharsPerTokenEstimator` from `context/budget.py`);
  output is always in log order. Named policies ship for the T-030
  migration: `POLICY_FULL`, `POLICY_CHAT` (value-exact `[-10:]`
  equivalence), `POLICY_DELEGATE` (value-exact `[-6:]` equivalence).
  **Backward compatible:** kind-less T-027/T-028 records are read as
  visible user-facing message turns. Evidence:
  `tests/unit/test_conversation_memory.py` — 31 tests (append/turn-id
  stability across instances, policy slice equivalence, token budget
  incl. pinned-charged-first and never-mid-truncate, pin/unpin
  replay, stubs, on-disk JSONL round-trip + torn-tail). Full suite
  **448 passed**; mypy gate clean; `./scripts/check.sh` ALL GREEN.
  *Also fixed in this task:* the T-027 growth benchmark compared
  **means** of first/last 100 append durations — one scheduler spike
  in a shared sandbox flipped it (a transient failure was actually
  observed); it now compares **medians** (outlier-robust, still
  cleanly separates O(1) from linear growth) — verified stable across
  5 consecutive runs.
- **R-301/R-305 (T-028): `scripts/migrate_sessions.py` — lossless,
  idempotent JSON→JSONL migration; session data untracked from git.**
  Each legacy `<id>.json` (single document with embedded `messages`)
  becomes the T-027 pair: `session_<id>.jsonl` (one line per message,
  legacy `timestamp` carried verbatim as `ts`) +
  `session_<id>.meta.json` (header carried verbatim — title /
  project_path / created_at / updated_at — plus `message_count`).
  **Self-verifying:** after writing, each session is replayed through
  `SessionStore.replay` and compared value-exact against the legacy
  document (count + role/content/ts) before being reported migrated.
  **Idempotent:** an existing `session_<id>.jsonl` means "already
  migrated" → skipped; a re-run is a no-op (mtime-pinned by tests) and
  — the dangerous case — never clobbers messages appended *after*
  migration while the legacy file still exists. Corrupt legacy files
  are skipped and reported without failing the batch, and are **never**
  deleted even under `--remove-legacy` (forensic evidence); legacy
  files are kept by default (deletion is an explicit user decision
  after verification). **R-305:** `.gitignore` now ignores session
  *data* only (`sessions/*.json|*.jsonl|*.meta.json|*.tmp` — not the
  package: `store.py`/`__init__.py` stay tracked); the 43 tracked
  session JSONs are `git rm --cached`-ed (index only, files stay on
  disk; history purge is T-050). Migration runbook (migrate → verify →
  `git rm --cached` → optional `--remove-legacy`) lives in the script's
  module docstring. Evidence: `tests/unit/test_migrate_sessions.py` —
  14 tests incl. migrating a copy of the repo's real 43 sessions
  value-exact. Full suite **417 passed** (403 + 14); mypy clean;
  `./scripts/check.sh` ALL GREEN.
- **R-301 (T-027): `sessions/store.py` — append-only JSONL session
  store; kills the O(n²) rewrite-per-message.**
  On-disk format (spec in the module docstring): `session_<id>.jsonl`
  (one JSON object per line, append-only, **the source of truth**) +
  `session_<id>.meta.json` sidecar (mutable header: title / project
  binding / counters — **derived, rebuildable**, written only on header
  change, never per message). `append_record`/`append_message` are O(1):
  open-append-write one line, no read, no rewrite; configurable
  `fsync="always"|"never"` per store (meta replaces atomically without
  fsync — it is derived and cheap to rebuild). **Torn-write recovery:**
  a crash produces at most one torn final line — reads (`replay`/`tail`)
  skip it and report `torn_tail=True`; the first append on an existing
  file truncates back to the last intact `\n` before appending, so two
  records can never fuse. Corruption **mid**-log is not a crash pattern
  and raises `CorruptLogError` loudly. `tail(n)` reads backwards in 64KB
  blocks — the recent-window load for R-304 never scans the whole file.
  `rebuild_meta()` heals any data/meta drift from the log (the R-301
  risk clause); a missing or corrupt sidecar rebuilds automatically on
  first `read_meta`. `sessions/` added to the mypy gate. Nothing is
  wired yet — `actions/session_manager.py` untouched; migration +
  gitignore land in T-028. Acceptance evidence: benchmark 1k appends
  p95 < 5ms (with `fsync="never"` — fsync latency belongs to the disk,
  the claim under test is constant-cost appends) plus a growth test
  (mean of last 100 appends ≤ 3× first 100 at 10× history). Evidence:
  `tests/unit/test_session_store.py` — 26 tests. Full suite
  **403 passed** (377 + 26); mypy clean (40 files);
  `./scripts/check.sh` ALL GREEN.
- **R-204 (T-026): every context-bound file read routed through
  `SafeReader` + CI boundary grep.**
  `context/sources/mention.py::build_items` (the single read helper
  shared by Mention/Keyword — Structure delegates to `FileManager`'s
  scan, which already skips `is_secret_file` paths and never reads
  content into the summary) no longer calls `FileManager.read_file`; it
  constructs `SafeReader(scan.root, max_file_size=MAX_FILE_SIZE)` —
  keeping legacy's exact 500KB cap so the pinned huge-file quirk stays
  byte-identical — and maps `SafeReadResult`: redacted → the stub
  passes through **verbatim, un-line-numbered**; `ok=False`
  (missing/huge/policy) → `content=None`, legacy's silent-skip;
  normal → line-numbered via `_number_lines`, a byte-exact clone of
  `FileManager.read_file`'s numbering (T-017 goldens replay green
  without regeneration). **Boundary enforcement:** `scripts/check.sh`
  gains a grep gate — any `open(`/`.read_text(`/`.read_bytes(` in
  `context/` outside `safe_reader.py` fails CI; mirrored as a pytest
  (`TestBoundaryGrep`) so plain `pytest` catches it too. Boundary rule
  documented in `CONTRIBUTING.md` (how a new source must consume
  `SafeReadResult`; no read-anyway flag exists). Acceptance: `.env`
  value unreachable via all three paths — mention (exact-name),
  keyword (stem), structure (never listed) — plus bare-`.env`
  unreachability. Evidence: `tests/unit/test_safe_reader_routing.py` —
  9 tests. Full suite **377 passed** (368 + 9); mypy clean; boundary
  grep green; `./scripts/check.sh` ALL GREEN.
- **R-204 (T-025): `context/safe_reader.py` — the sanctioned file-read
  gateway for model-bound content.**
  Pipeline: denylist (path-based, decided **before** touching disk) →
  `resolve_workspace_path` containment/symlink check → size cap
  (whole-file reject at 200KB, never a partial read) → read → entropy
  sniff. Denylist = `chain/path_policy.is_secret_file` **plus** a
  `*.env`-suffix rule (`production.env` was uncovered by the shared
  policy — `.env.example` stays allowed) plus extensible
  `extra_deny_names`/`extra_deny_extensions` (widen-only, no narrowing
  hook by design). Sniff = 6 known-key regexes (private-key block, AWS
  `AKIA…`, GitHub `gh?_…`, OpenAI `sk-…`, Slack `xox…`, Google `AIza…`)
  then a secret-assignment heuristic gated on Shannon entropy ≥ 3.5,
  with a maximal-token lookahead guard so quantifier backtracking can't
  flag function calls (`get_password_from_vault()` is not a secret).
  Any denial or sniff hit yields the fixed stub
  `«redacted: secret file»` via `SafeReadResult.prompt_text` — the
  secret value never enters a prompt. Scanner boundary hardened in
  `chain/bridge.py`: `.env` removed from `_TEXT_EXTENSIONS` and
  `_collect_files` now skips `is_secret_file` paths, so `server.pem` /
  `id_rsa` are excluded even where extension logic would admit them.
  Security note + override procedure (rename to `.env.example` / move
  the value / widen-only extras) documented in the module docstring.
  Routing *all* context reads through SafeReader is T-026.
  Evidence: `tests/unit/test_safe_reader.py` — 42 tests (denylist
  matrix, redaction incl. deny-without-disk-touch and no-partial-read,
  entropy sniff units, scanner-boundary E2E). Full suite **368 passed**
  (326 + 42); mypy clean; `./scripts/check.sh` ALL GREEN.
- **R-203 (T-024): all prompt paths pack via `ContextBudget` — the three
  ad-hoc char limits are gone.**
  Site 1 `chain/context_builder.py`: `build_prompt_section` no longer
  slices items (`per_item_max`) nor stops at a char wall (`max_total`
  break) — items are packed whole-or-dropped by tier
  (`TIER_BY_KIND`: mentioned files = high; dirs/search/deps = normal;
  tree/info = opportunistic) with an observable
  `... (أُسقط N عنصر سياق — ميزانية التوكنز: …)` note; `max_total` stays
  as a legacy-compatible knob (chars → tokens via the central chars/4
  estimator) and an explicit `budget=` override is accepted.
  Site 2 `chain/knowledge.py`: `build_context` drops `content[:2000]`,
  `[:500]`, `[:300]` and the final `max_tokens*4` cut — sections become
  `BudgetItem`s (read files & observations/errors = high, dirs/search/
  commands = normal), packed within `max_tokens`; no mid-content cuts.
  Site 3 `chain/orchestrator.py`: `_split_content`'s scattered `len//4`
  guesses now go through the single pluggable `CharsPerTokenEstimator`
  (splitting keeps all content, so it stays outside `pack()` by design).
  Bonus: `build_delegate` (`chain/strategies.py`) `content[:2000]` per
  file → whole-file packing at high tier with a named-drops note.
  Config knob: new `context_budget:` section in `config.yaml`
  (`model_window`/`reserved_output`/`safety_margin`) read by the new
  `ContextBudget.from_config()` (defaults 128k/8k/0.10 when absent).
  Deliberately out of scope (documented): `agent_tools.py` read-size cap
  (SafeReader territory, R-204/T-025), `orchestrator.py` risk-regex
  scan slices (analysis-only, never prompt-bound), and the
  `context/bundle.py` renderer cap (T-021 goldens contract).
  Tests: `tests/unit/test_budget_wiring.py` (24) — per-site no-mid-cut +
  tier-drop-order + explicit-budget override, delegate whole-file /
  drop-note behavior, `from_config` incl. parsing the repo's real
  `config.yaml`, and the oversized-project E2E (mentioned file intact,
  packed section within token budget, drop observed). Chain goldens
  replay byte-exact unchanged (fixtures fit the budget — verified, no
  golden bytes touched). Suite: **326 passed** (302 + 24).
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
