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
- **R-801 (T-100): StrategyPluginRegistry core.**
  - New standalone `chain/plugin_registry.py`: `StrategyPluginRegistry`
    discovers plugins via
    `importlib.metadata.entry_points(group="webdev_ai.strategies")` —
    discovery itself is lazy (never imports plugin code); the import is
    isolated inside per-plugin `ep.load()` (spike T-052 §1 conclusion).
  - **Three-stage validation gate**, any exception → structured
    `QuarantineRecord(name, stage, reason)` (with `to_dict()`), never a
    host crash: `import` (ep.load) → `shape` (object is a **class**
    exposing callable `build()` + dict `routing_hints`) → `dry_run`
    (instantiate + `build()` on a canned fixture request; returning
    `None` also quarantines).
  - Duplicate plugin names: first valid wins, later ones quarantined at
    `shape` with an explicit "duplicate" reason; `discover()` is
    idempotent-by-reset; `loaded` / `quarantined` are defensive copies;
    `entry_points_fn` is constructor-injectable so the full failure
    matrix is testable without installing real packages.
  - Registry is standalone until T-102 (no router / core/strategy.py /
    server.py changes). New `tests/unit/test_plugin_registry.py` =
    13 tests (acceptance matrix, all-fail host safety, empty group,
    gate edge cases, lifecycle). Full gate:
    **1194 passed, 1 skipped — ALL GREEN**.
- **R-902/R-906 (T-066): Rollback UI + observability status chip.**
  - Two new UMD-lite modules (pure logic, node-testable; DOM glue only in
    `static/app.js`): `static/js/run_history.js` (`RunHistory`:
    `buildEntries` / `renderPanelHTML` / `rollbackFrame` / `confirmActions` /
    `applyRollbackResult` / `conflictReportHTML`) and
    `static/js/status_chip.js` (`StatusChip`: `createState` / `noteFrame` /
    `updateCapacity` / `shouldRender` / `renderChipHTML` / `renderPanelHTML`).
  - **Read-only backend**: `CheckpointManager.run_summaries()` (single pass
    over the existing checkpoint log, newest first, seal hashes joined,
    `pre_sha256=null` marks files created by the run) and
    `snapshot_text(run_id, path)` (pre-write text from the blob store), plus
    two GET-only endpoints `/api/rollback/history` and
    `/api/rollback/preview?run_id=&path=`.
  - **Zero new WS frame types**: execution reuses the T-054 commands
    `rollback_run` / `rollback_file` verbatim — frames are built exclusively
    in `RunHistory.rollbackFrame` (a regression test bans manual construction
    in app.js) — and results arrive on the existing `rollback_result` frame
    (`RestoreReport.to_dict()`).
  - **≤2-click rollback with confirmation diff reusing the T-065 panel**:
    click 1 fetches snapshots and opens `DiffPanel.openState` with synthetic
    actions in the same schema (write with snapshot payload to restore,
    delete for run-created files); click 2 (confirm) is intercepted by
    `consumeRollbackDecision` inside `sendDiffDecision` — a local
    confirmation with no `request_id`, so no approval response is ever sent
    to the gate.
  - **Human-readable conflict reports**: `conflictReportHTML` renders
    path + reason as text (a test bans leaking raw JSON such as
    `expected_sha256`); `applyRollbackResult` marks files restored/conflict
    and entries rolled_back/partial/refused (restored entries' buttons are
    disabled). Retention-pruned runs disappear automatically since the
    history source is the checkpoint log itself.
  - **StatusChip (R-906)** consumes only existing data: routing from the
    `routing` field of the existing `chain_started` frame
    (`RoutingDecision.to_dict()`), capacity/breakers from the existing
    `/api/capacity` (polled every 30s), budget from any frame carrying
    `budget` (`BudgetTracker.to_dict()` fields). Renders are throttled to
    one per 500ms with a trailing pending render — a 100-frame burst yields
    ≤3 renders (tested). Collapsed by default; zero new backend for it.
  - Token-only CSS additions (`rh-*` / `sc-*` classes) pass the color-token
    lint; new `tests/unit/test_rollback_ui.py` = 15 tests (real E2E through
    the gate + `server._handle_ws_message` with frames produced by the
    actual node module, conflict refusal rendering, newest-first summaries,
    golden panel render with T-063 icons, T-065 panel reuse with computed
    diff rows, chip rendering from real `RoutingDecision`/`CapacityReport`
    dicts, burst throttling, and consume-only wiring regressions).
    Full gate: **1181 passed, 1 skipped — ALL GREEN**.
- **R-901 (T-065): Diff-review panel for the approval gate.**
  - New `DiffPanel` module (`static/js/diff_panel.js`, UMD-lite, node-testable)
    holding all pure logic; DOM glue lives in `static/app.js`
    (`openDiffPanel` / `closeDiffPanel` / `sendDiffDecision` / `renderDiffPanel`
    plus button and keyboard bindings). Module header **pins the payload
    schema verbatim**: incoming `chain_approval_request`
    (`request_id`/`source`/`run_id`/`payload_hash`/`actions[{kind,target,payload,summary}]`
    as built by `chain/bridge.py`), outgoing `chain_approval_response`
    (`request_id`/`approved`/`payload_hash` — accepted by `gate.resolve` only
    on a verbatim id+hash match), and closing `chain_approval_verdict`.
  - **Gate atomicity respected:** the protocol has no partial approval, so
    per-file accept/reject toggles are review aids — Confirm sends
    `approved:true` only when *every* file is accepted; any rejected file
    ⇒ `approved:false`. The panel closes on `chain_approval_verdict`,
    keeping the gate as the source of truth.
  - **Diff engine:** common prefix/suffix trim + Myers O(ND) with
    `MAX_MYERS_D=1500` and a linear fallback for huge inputs; command-kind
    actions render their raw payload (`rows:null`). Unified **and**
    side-by-side (split) modes with cached split pairs.
  - **Syntax colors layered under add/del backgrounds** via
    `CodeHighlight.highlightCode` per line (LRU makes repeats cheap);
    language derived from `FileIcons.getFileIcon(target).id` — no second
    extension map. File headers use T-063 icons plus ±counts, kind badges,
    collapse and per-file decision buttons.
  - **Virtualized rendering:** `ROW_HEIGHT: 20` matches the CSS
    `.diff-row { height: 20px }` (test-enforced); 80-row window with
    top/bottom spacers preserving scroll height; rAF-throttled re-window.
    A 3k-line diff builds in <2s and renders a window in <200ms.
  - **Keyboard shortcuts:** a=approve all, r/Escape=reject all,
    Enter=confirm, u=toggle unified/split, x=collapse active file,
    j/k=move focus (clamped); ignored while typing in inputs.
  - Panel CSS is token-only (color-lint clean). `tests/unit/test_diff_panel.py`
    adds 21 tests: WS contract against the **real `ApprovalGate`** (batch +
    per-file semantics, tampered-hash rejection, verbatim id echo), golden
    render of a 5-file mixed request, 3k-line perf/virtualization, full
    shortcut map, auto-mode regression (whitelist emits no frame — panel
    never opens), and schema/wiring pinning. Full gate: **1166 passed, 1 skipped**.
- **R-904 (T-064): Syntax highlighting engine + chat/file views.**
  - **Engine decision (documented in module header): highlight.js 11.11.1,
    not Shiki** — Shiki needs WASM + a bundling step; this project is
    UMD-lite with no build step. Engine is **vendored locally**
    (`static/vendor/highlight.min.js`, BSD-3 — the old cdnjs script *and*
    its `github-dark-dimmed` CDN stylesheet were removed) plus a vendored
    `dockerfile` grammar. Covers the full R-903 language list (21 grammars
    asserted by test) and runs in node so tests exercise the real engine.
  - `static/js/code_highlight.js`: the single engine consumption point.
    `highlightCode(code, fenceTag)` (LRU-cached), `highlightContainer(el)`
    for chat blocks (fence-tag override, else auto-detect),
    `buildEditorHTML(text, path, firstLine, visible)` for the editor.
    File language derives from `FileIcons.getFileIcon(path).id` — no second
    extension map (T-063's single-source grep gate covers the new module
    automatically). `app.js` no longer calls `hljs.` directly (test-banned);
    the dead `marked.setOptions({highlight})` hook (removed in marked v5)
    was deleted.
  - **Streaming without flicker:** completed code blocks are served from an
    LRU cache (max 500) returning the **identical string object** — zero
    re-tokenization; only the still-open trailing block re-parses per chunk
    (streaming-simulation test pins missDelta == chunk count).
  - **Editor highlight layer:** `<pre id="editor-highlight">` behind a
    text-transparent `textarea` (visible caret, metrics identical,
    scroll-synced with the existing line numbers). Files >2000 lines use a
    **lazy viewport path**: only ±200 lines around the viewport are
    tokenized (rAF-throttled on scroll), the rest stays escaped plain
    text — 5k-line file <500ms with total line count preserved
    (scroll-height parity, asserted).
  - Palettes are theme tokens: `.hljs-*` rules in `style.css` consume
    `var(--syntax-*)` (defined for all 4 themes since T-060); missing
    rules added (tag/name/selector-*/bullet/strong/emphasis/punctuation/
    symbol/link). Theme switching restyles code instantly.
  - `tests/unit/test_code_highlight.py` (16 tests): pinned per-language
    class snapshots for 21 languages; every snapshot class styled by a
    token rule; cache identity + LRU bound; large-file perf; language
    derivation via FileIcons; script load order engine→icons→module→app;
    unknown/no-language regression.
- **R-903 (T-063): File-type icons rendered everywhere filenames appear.**
  - `static/app.js`: new `fileIconHTML(path)` — the **only** consumer entry
    point; delegates to `FileIcons.getFileIcon` (T-062 module) and renders
    `<svg class="file-icon"><use href="/static/icons/sprite.svg#icon-…">`
    colored via `var(--icon-*)` theme tokens. The old local emoji
    `getFileIcon(ext)` mapping is **deleted** — one import, zero duplicated
    mappings.
  - Three consumption points wired: file tree (`renderTreeNode`), editor
    tabs (`renderTabs`), and `@mention` attachment chips
    (`renderAttachments`, replacing the generic 📄). Diff-panel headers and
    run-history don't exist yet (T-065) — in scope "when they exist".
    `getFileBadgeHTML` (SRC/TREE/DIR chat tool-activity badges) is a
    separate system, intentionally untouched.
  - `static/index.html`: loads `file_icons.js?v=1` before `app.js`
    (order asserted by test). `static/style.css`: `.file-icon`
    sizing rule (14×14, flex-shrink 0) — no raw colors.
  - `tests/unit/test_icon_consumption.py` (11 tests): grep gate over all
    served `.js` proving no second extension→icon mapping outside the
    module; old emoji-literal signatures banned; the three consumption
    points asserted; script load order; and a fixture-tree snapshot of
    25 paths covering every icon class, executed through the **real**
    `fileIconHTML` (extracted from app.js) + real module in node, pinned
    to a literal `#icon-*` expectation table.
  - Note: this implementation was captured at f260b9b, reverted at
    d19f124, then restored verbatim from f260b9b after full re-verification
    (`check.sh` 1129 passed, 1 skipped — ALL GREEN).
- **R-903 (T-062): File-type icon system — module + SVG sprite.**
  - `static/js/file_icons.js`: the single extension→icon mapping.
    `FileIcons.getFileIcon(path)` → `{id, symbol, colorToken, label}`;
    accepts full paths (both separators); special filenames beat
    extensions (`package-lock.json` → lock not json, `Dockerfile` →
    docker, `.env.*` → config, `Makefile` → shell); browser + node.
  - `static/icons/sprite.svg`: one file = one HTTP request
    (`<use href="sprite.svg#icon-<id>">`), 24 original symbols drawn
    for this project (23 categories + fallback `file` glyph) — no
    external icon-set license obligations. All shapes use
    `currentColor` only (test-enforced), so icons recolor with the
    theme.
  - 17 new `--icon-*` tokens added to **all four** themes; a parity
    test proves every colorToken the module emits is defined in every
    shipped theme. Coverage table + license note in the module header.
  - `tests/unit/test_file_icons.py` (10 tests) executes the real
    module via node: 40-path matrix, distinctness, fallback,
    special-name priority, sprite completeness, currentColor-only,
    token parity. (Consuming the module in tree/tabs/mentions is
    T-063's scope.)
- **R-905 (T-061): Theme switcher, persistence + 2 extra themes.**
  - Header theme picker (🎨 dropdown) driven by a single `THEMES`
    registry in `static/app.js` — the one source of truth for shipped
    themes. `setTheme` swaps `data-theme` only: live restyle, no reload;
    unknown stored themes fall back to dark.
  - Persistence via `localStorage("webdev-ai-theme")` — the **same key**
    the T-060 pre-paint bootstrap reads, so the chosen theme survives
    reload with no FOUC (key equality is test-enforced).
  - Two new theme data files: `static/themes/high-contrast.css`
    (pure black/white + bright saturated accents; AAA body text, 21.0)
    and `static/themes/monokai.css` (Monokai Pro-inspired; dim text
    adjusted for AA). Both define the complete dark token set and scope
    strictly to `[data-theme="<id>"]` — a test forbids touching bare
    `:root`, keeping dark the unchanged default for existing users.
  - WCAG AA is now a permanent test, not a manual audit: computed
    contrast for 4 text/bg pairs across all 4 themes (minima: dark 6.80,
    light 5.14, high-contrast 15.91, monokai 7.80 — all ≥ 4.5).
  - "Adding a theme" 5-step guide documented in `tokens.css` header:
    one data file + one registry entry, zero component changes.
  - `tests/unit/test_theme_tokens.py`: 11 → 28 tests.
- **R-905 (T-060): Design-token layer + dark/light themes.**
  - New `static/themes/`: `tokens.css` (structural tokens + role aliases —
    `--accent`, `--syntax-*`, `--icon-*`, `--diff-*-fg`, terminal roles;
    zero raw colors in it), `dark.css` (default palette — applied to
    bare `:root` **and** `[data-theme="dark"]`; values byte-identical to
    the pre-migration palette, locked by a snapshot test), `light.css`
    (Latte-inspired; defines the exact same token set — parity-tested).
  - Migration: `static/style.css` went from 110 raw colors to **zero** —
    every `rgba(...)` became `color-mix(in srgb, var(--token) N%,
    transparent)`; hljs block now consumes `--syntax-*` (ready for
    R-904); file badges consume `--icon-*` (ready for R-903). Found and
    fixed a pre-existing silent fallback: `.copy-btn` consumed undefined
    `--text-base`/`--border`. Legacy unserved `public/static/style.css`
    migrated too.
  - No-FOUC bootstrap inline in `static/index.html` `<head>` — sets
    `data-theme` before the first stylesheet: `localStorage` →
    `prefers-color-scheme` → dark. `color-scheme` declared per theme.
  - New CI gate in `scripts/check.sh`: **color token lint** — raw
    hex/rgb/hsl anywhere under `static/`+`public/` outside
    `static/themes/` fails the build.
  - WCAG AA: computed contrast for 8 text/bg pairs across both themes,
    all ≥ 4.5 (light `--subtext` darkened vs. upstream Latte to pass).
  - `tests/unit/test_theme_tokens.py` (11 tests): lint mirror, dark↔light
    token parity, only-defined-tokens consumption, dark palette snapshot,
    bootstrap-before-styles order, `color-scheme` declarations.
  - Adding a theme = one data file defining `[data-theme="<name>"]` —
    no component changes (consumed by T-061's switcher).
- **R-504 (T-059): Verification feedback loop — the agent runs the test,
  reads the result, and fixes before declaring success.**
  - `chain/knowledge.py`: `run_command` results enter the next iteration
    as **`high`-tier** context items (like file contents) — failure
    output is the fuel for the fix and survives budget pressure; a
    budget test proves the FAIL line outlives a normal-tier dir item at
    a tight token cap.
  - `chain/agent_loop.py`: new `_verification_instruction()` injects a
    mandatory verification step (`[خطوة التحقق — إلزامية لمهام تعديل
    الكود]`) into both the initial and follow-up prompts — run the
    configured test command → read its result → fix on failure → never
    declare a code task done unverified. Injected **only** when the
    command policy is enforced and the allowlist has a
    test/lint/typecheck/build entry; legacy mode injects nothing.
  - **No ungated mutation path:** command-triggered file writes (e.g.
    an autoformatter) are now captured — `chain/agent_tools.py` takes
    pre-command workspace signatures (400-file / 512KB caps, secret
    files and heavy dirs skipped), snapshots changed files, seals them,
    and reports `🧷 [checkpoint]` in the tool output. New
    `CheckpointManager.snapshot_absent()` (`core/checkpoint.py`)
    records command-**created** files as pre-state-absent
    (`sha256=None` ⇒ restore deletes them) — safe because
    `entries_for_run` is first-snapshot-wins. `server.py` wires the
    **same** CheckpointManager used for chain writes (T-054): one
    restore path. Without a gate the command is auto-rejected and no
    side effect ever lands (tested).
  - `tests/integration/test_agent_feedback.py` (10 tests): fail-then-fix
    fixture (1st run exits 1, the 2nd prompt carries the failure output,
    2nd run passes), gated+checkpointed side-effect proof, budget
    compliance, and verification-instruction presence/absence matrix.
  - Verification-step contract documented in the `agent:` section of
    `config.yaml` (T-058 precedent).
- **R-504 (T-058): `run_command` agent tool behind a project-owned allowlist.**
  - `chain/agent_tools.py`: new `CommandPolicy` + `command_policy_from` —
    the allowlist lives in `config.yaml` (`agent.command_allowlist`:
    test/lint/typecheck/build entries) and is **never** agent-chosen.
  - Exact-match enforcement (literal command or logical entry name,
    whitespace-normalized — no prefix/pattern matching): a
    non-allowlisted command gets a structured, logged rejection naming
    the request and the available entries — never silent execution.
  - The allowlist is a layer **on top of** the ApprovalGate (T-013):
    allowed commands still require interactive user approval.
  - `RunTicket`-linked timeout + cancellation: the command runs in a
    worker thread polled every 50ms — ticket cancellation is observed
    *during* a long command; hung commands hit an explicit timeout
    (config `command_timeout_seconds`). `AgentLoop.run` wires its
    ticket into the tools for the duration of the run.
  - stdout/stderr/exit code captured in a structured report; each
    stream size-capped independently (`command_output_max_chars`) with
    an explicit truncation marker.
  - Missing config section = legacy mode (gate-only, pre-T-058
    behavior) — zero migration break. 26 tests in
    `tests/unit/test_run_command.py`.
- **R-206 (T-057): Minimal SemanticSource — relevance-based recall, seeded early.**
  - New `context/semantic_source.py`: pluggable `EmbeddingBackend`
    interface + default local `HashingEmbedder` (md5 bag-of-words,
    128-dim, L2-normalized — zero deps, zero network, deterministic).
  - Corpus = project file chunks (30 lines, via SafeReader — secrets
    excluded) + last 20 user turns; cosine top-k retrieval as
    `<semantic:...>` items at **opportunistic tier only** — never
    displaces `must_have`/`high` (compliance-tested).
  - Hard timeout with skip-on-timeout: whole retrieval runs in a
    worker thread; any slowness/failure ⇒ empty result — a slow
    embedding call can never block the response.
  - Config flag `context.semantic.enabled` in config.yaml (default
    on, cheap to disable); `timeout_seconds` / `top_k` tunable.
  - Standard composition: `[Mention, Keyword, Symbol, Semantic,
    Structure]` — T-017 goldens unaffected (flag on and off).
- **R-205 (T-056): SymbolSource — symbol-aware context in the standard composition.**
  - New `context/sources/symbol.py`: message terms resolve to
    `<symbol:definition:X>` / `<symbol:callers:X>` / `<symbol:imports:rel>`
    items via the T-055 SymbolIndex — syntactically-precise definitions
    and call sites instead of string-match noise.
  - Standard composition is now `[Mention, Keyword, Symbol, Structure]`;
    symbolic paths never enter `mentioned_files`, so T-017 goldens are
    byte-identical.
  - Fallback = literal silence: files without symbol data contribute
    nothing and remain covered by KeywordSource (equality-tested).
  - Budget tier `high` — a compliance test proves `must_have` is never
    displaced by symbol items.
  - Freshness: per-root shared index + stat-guard per collect
    (mtime/size change or deletion invalidates lazily).
- **R-205 (T-055): SymbolIndex — per-file symbol tables via tree-sitter.**
  - New `context/symbol_index.py`: definitions / references / imports
    extracted per file for Python, JS (.js/.mjs/.cjs/.jsx), TS/TSX,
    HTML (id/class attrs) and CSS (class/id selectors + `@import`).
  - **Graceful degradation by design**: tree-sitter is an *optional*
    dependency — missing lib/grammar, unsupported extension, missing
    file, secret-redacted content (SafeReader R-204) or broken syntax
    all yield an empty `FileSymbols` table, never an exception.
  - Freshness follows the T-049 pattern: `attach(fm)` registers
    `notify_write` in `FileManager.add_write_hook` — writes invalidate
    the cache entry, re-parse is lazy on next query.
  - Agreed perf ceiling: 2 000-file index build ≤ 10 s (≈1 s measured).
  - `requirements-dev.txt` + CI pip line gained the six
    `tree-sitter*` packages; tests skip themselves when absent.
- **R-106 (T-054): checkpoints wired into every gated apply + rollback WS commands.**
  - `ActionApplier.apply_step` gained `run_id=` / `checkpoint=` params:
    snapshot of every file path in the batch **before** the first write,
    `seal` **after** the last — the hookup lives inside the applier so no
    apply path can bypass it (structurally asserted in tests).
  - `ChainBridge.checkpoint_manager`: call-time property rooted at
    `<runs_dir>/checkpoints`; `_gated_apply` passes it on every apply.
  - New WS commands `rollback_run(run_id)` / `rollback_file(run_id, path)`
    → `rollback_result` frame (status success/partial/refused + structured
    conflict reports with expected/actual sha256). Additive frames only.
  - Retention hookup: new `CheckpointManager.prune(keep_run_ids)` rewrites
    the checkpoint log and GCs unreferenced blobs; invoked after the live
    R-305 sweep at boot with the sweep's surviving run set (dry-run mode
    prunes nothing — same safety default as the sweep).
  - 9 integration tests (`tests/integration/test_rollback.py`): 3-file
    gated batch → byte-exact rollback (created file deleted), per-file
    restore leaves siblings, external edit → partial + conflict frame,
    no-bypass structural check, 50-run prune bound.
- **R-106 (T-053): CheckpointManager core — content-addressed pre-write snapshots.**
  - New `core/checkpoint.py`: `snapshot(run_id, paths)` stores pre-write
    copies in a content-addressed `objects/<sha256>` store (duplicate
    content stored once, ever) + appends to a `checkpoints.jsonl` log;
    `seal(run_id, paths)` records post-write hashes after the apply.
  - `restore_run(run_id)` / `restore_file(run_id, path)` verify the
    current on-disk hash first: only content provably equal to the run's
    sealed output (or already at snapshot state) is rolled back — an
    external edit, a crash-before-seal, or store corruption **refuses with
    a structured conflict report** and never overwrites unverifiable work.
    `restore_run` still restores clean siblings (partial status).
  - Created-by-the-run files (snapshot records "absent") are deleted on
    rollback; `RestoreReport.to_dict()` is WS-frame-ready for T-054.
  - 19 unit tests in `tests/unit/test_checkpoint.py` (byte-exact 5-file
    batch incl. binary + UTF-8, dedup assertion, per-file restore leaves
    siblings, refusal matrix). Standalone — no server wiring yet (T-054).
- **Phase 8 Scoping (T-052): spike findings + task breakdown — no production code.**
  - New `docs/phase8_plan.md`: (1) entry-point plugin loading for R-801
    **validated by throwaway experiment** on Python 3.13.13 — per-plugin
    `ep.load()` isolation confirmed host-safe quarantine of broken plugins
    while good ones load and dry-run; (2) R-802 embedding backend decision:
    provider-backed `/embeddings` + pure-Python cosine over a JSONL vector
    sidecar (no torch/faiss/vector DB — rationale + rejected alternatives
    documented); (3) R-804 Redis decision: `redis>=5.0` as optional extra,
    standalone instance via `REDIS_URL`, **Streams** for work queue +
    EventBus (replayable ordering needed for frame parity; Pub/Sub rejected),
    `SET NX PX` per-project leases.
  - `DEVELOPMENT_TASKS.md`: Phase 8 breakdown **T-100 … T-114** appended
    (15 tasks covering R-801..R-805 with real estimates and dependencies
    resolved to actual task numbers; numbered from T-100 because T-053+
    was already taken by the Review-Merge and Phase 9 tracks); Dependency
    Quick Map and totals (66 → 81) updated.
- **R-703 (T-051): Truthful README + config default reconciliation.**
  - `README.md`: the false "125/125 tests ✅" claim and the stale
    hand-written per-file test counts are **gone** — replaced by a
    truth-principle note: real counts/results come from CI
    (`.github/workflows/ci.yml`) or `./scripts/check.sh`, coverage
    guarded by the increase-only ratchet. The structure section now
    shows the real `tests/` layout (unit/integration/contracts/goldens/
    fixtures) and the config example shows the real
    `default_provider: "use_ai"` (was showing `"genspark"`).
  - `server.py`: the hardcoded startup default
    `"genspark:claude-sonnet-5"` is **deleted** — **config wins**. New
    `_read_config()` (tolerant) + `_resolve_default_provider(cli, cfg)`
    (pure, testable): precedence `--model prov:model` > `--model model`
    (goes to the *config* provider, not hardcoded genspark) >
    `config.default_provider` + `config.providers.<id>.model` >
    provider-class default (single source per value; model kwarg only
    passed when config supplies one).
  - Tests (`tests/unit/test_default_provider.py`, 10): config-wins ×4
    (changing config observably changes the startup provider),
    CLI precedence ×2, boot smoke against the real config.yaml ×2,
    hardcode-gone structural greps ×2.
- **R-703 (T-050): CI pipeline + coverage ratchet + sessions history purge.**
  - New `.github/workflows/ci.yml`: single job running `scripts/check.sh`
    (mypy + all 7 structural gates + full pytest — the one source of
    truth, not duplicated in YAML), then a production-code coverage
    measurement (`.coveragerc` omits tests/scripts/static), then the
    ratchet gate.
  - New `scripts/coverage_ratchet.py` + tracked `coverage_baseline.txt`:
    increase-only coverage floor. `check` exits 1 if coverage drops
    below the baseline; `update` raises the floor (never lowers it,
    0.5pt safety margin below the measured value). Started at the
    spec's 40%, ratcheted to the real measured floor **68.4%**
    (current coverage 68.9%).
  - New `scripts/purge_sessions_history.sh`: coordinated
    `git filter-repo` runbook purging `sessions/*.json|jsonl|meta.json`
    from **all history** (43 leaked user conversations) while keeping
    the `sessions/` production code; safety pre-purge tag, built-in
    verification (`git log --all -- 'sessions/*.json'` must be empty),
    `DRY_RUN=1` mode, and force-push/re-clone team instructions.
    **Rehearsed on a scratch clone: history empty, code kept, suite
    green post-purge.** Owner runs it manually (history rewrite).
  - `.gitignore`: coverage artifacts (`.coverage`, `coverage.json`,
    `htmlcov/`) untracked; the baseline file stays tracked by design.
  - Tests (`tests/unit/test_coverage_ratchet.py`, 16): pure ratchet
    decision (block-on-regression verified), increase-only `update`,
    CLI exit codes on fixture files, CI wiring assertions
    (workflow gates present, baseline ≥40, coveragerc omits
    non-production, fixtures canary).
- **R-702 (T-049): ProjectIndex — inverted index kills O(files) per message.**
  - New `context/index.py`: `ProjectIndex` built once at project open
    (os.walk, sorted global order preserving T-017 golden order) with
    inverted maps (basename → paths, ext → paths, name pairs) and ranked
    `lookup()` (exact > prefix > substring). Freshness by two mechanisms:
    **write-through hooks** (`attach(fm)` → `FileManager.add_write_hook`;
    every `write_file`/`edit_file` notifies the index with the rel path)
    and an **mtime-age sweep** (`refresh_if_stale()`, default 2.0s) that
    catches out-of-band edits within one sweep. `IndexedScan` is a
    drop-in `ProjectScan` borrowing the live index list — zero tree
    walks at query time.
  - `ProjectScan` gained a uniform query surface (`lookup_name` /
    `lookup_stem`, linear) and its walk switched from `rglob` to
    `os.walk`; `MentionSource`/`KeywordSource` now query via
    `scan.lookup_*` instead of scanning `scan.files` directly (same
    sorted order, WEB_EXTENSIONS filter, dedupe and cap preserved —
    goldens unchanged).
  - Wiring: `server._server_handle_factory` and `_build_ctx` build the
    index into `ProjectHandle.index` and attach it to the FileManager;
    the WS handler passes `index=sctx.project.index` to
    `gather_message_context` (ctx-less/test paths fall back to plain
    `ProjectScan`).
  - New check.sh gate: grep bans `.rglob(` calls anywhere in `context/`.
  - Tests (`tests/unit/test_project_index.py`, 23): build/lookup/
    ranking/invalidation, FileManager hook contract, write-then-mention
    freshness, out-of-band edit within one sweep (fake clock), facade
    parity with/without index, 5k-file perf fixture (<10ms mention
    resolution, zero-rglob patched-assert), grep-gate tests.
- **R-701 (T-048): SessionContext per WS connection — two-tab isolation.**
  🆕 `core/session_context.py`: per-connection `SessionContext` (own
  `ProjectHandle`, independent `chat_history`, per-tab model selection,
  approval inbox — `active_agent_loop`/`delegate_bridge`/`chain_bridge` —
  per-connection EventBus subscription, per-batch backup flag) layered
  over shared `AppContext` services; `switch_project()` swaps **this
  connection's** handle only (shared `ctx.project` untouched, other
  tabs' handles keep identity — id()-asserted); idempotent `close()`
  cancels the active loop + chain bridge and unsubscribes the adapter.
  `server.py`: `ws_handler` split into `_build_session_context(ws)`
  (composition point — the only sanctioned module-global read site) +
  `_handle_ws_message(ctx, sctx, msg)` (the full 19-type dispatch
  ladder, all conversation state via `sctx`); conversation-scoped
  globals swept (`_backup_done_for_batch` and `_active_agent_loop`
  module globals **deleted**; `_apply_single_action(action, sctx)` now
  connection-scoped); disconnect cleanup runs in `finally` via
  `sctx.close()`. 🆕 `scripts/lint_handler_state.py`: AST-based lint
  banning `global` statements and module-level mutable-state reads
  inside handler functions (UPPER_CASE constants exempt; local shadowing
  respected) — wired into `check.sh` as a gate and verified against a
  violation fixture (`tests/fixtures/lint_handler_state_violation.py`).
  State-scoping rules documented in `core/session_context.py`. Tests
  (`tests/integration/test_session_context.py`, 14): two-tab E2E
  (B switches project via a real WS message; A's handle identity,
  validity and scan unaffected; frames routed to the owning client
  only; independent histories/models/approval inboxes), disconnect
  cleanup (loop cancelled, bridge cancelled with the legacy reason,
  `subscriber_count == 0`, idempotent), lint gate pass/fail, and
  single-tab regression (pong/list_runs byte-identical contract).
- **R-604 (T-047): Typed EventBus + single WS Adapter — execution
  decoupled from transport.** 🆕 `core/events.py`: in-process `EventBus`
  (per-run **FIFO** delivery under a per-run lock; subscriber **isolation**
  — a throwing subscriber never affects others or the publisher; bounded
  per-run **history** for debugging, LRU-capped run count;
  `subscribe()` returns an unsubscribe function) + the six typed events
  of the R-604 catalog: `RunStarted` / `StepProgress` /
  `ApprovalRequested` / `RunFinished` / `RoutingDecided` /
  `BudgetChanged` (frozen dataclasses keyed by `run_id`).
  - **Single WS Adapter:** `server.py::_WSAdapter` is now the **only**
    `ws.send` site in the codebase. `_json_sender(ws)` builds the
    per-connection pipeline `frame → _frame_publisher → EventBus →
    _WSAdapter → ws.send` — same signature, same JSON-only /
    swallow-errors / no-ticket-lifecycle contract (T-015), so all 52
    scattered `ws.send(json.dumps(...))` sites in `ws_handler` migrated
    to `_ws_frame(...)` with **zero frame-shape change** (adapter
    renders `{"type": frame_type, **payload}` byte-identically —
    parity-proven against a legacy recording).
  - **Observability lane:** module-level `event_bus` carries the
    non-UI events: `_RunnerWSAdapter` now publishes `RunStarted` /
    `RunFinished` (still **no** UI frame — legacy semantics), the
    router decision site publishes `RoutingDecided` (R-402 hook), and
    any frame carrying a `budget` dict derives a `BudgetChanged`.
    Approval frames publish `ApprovalRequested`; everything else
    `StepProgress`.
  - **CI gate:** `scripts/check.sh` grep bans `ws.send(` outside the
    adapter across `server.py chain/ core/ runners/ actions/ context/
    sessions/` (only `self._ws.send(` inside `_WSAdapter._send`
    allowed; `providers/use_ai.py` exempt — it is an outbound WS
    *client* to the AI provider, not UI transport). Runners import
    zero transport modules (tested).
  - Evidence: 🆕 `tests/unit/test_event_bus.py` (14): pub/sub ×5
    (subscribe/unsubscribe, multi-subscriber, broken-subscriber
    isolation, bounded history, full event catalog); **FIFO under
    concurrent emission ×2** (4 threads × 50 events per run — per-run
    order preserved; history order too); adapter parity ×5 (**legacy
    recording byte-identical**, swallow-errors contract, approval →
    typed event, budget → `BudgetChanged`, runner lifecycle →
    observability events with no UI frame); boundary ×2 (grep clean,
    runners transport-free). check.sh ALL GREEN: **900 passed,
    1 skipped**.
- **R-603 (T-046): Parallel ready-set execution — `max_parallel_steps`
  becomes real.** Previously the executor always ran `ready[0]`
  sequentially while the policy advertised parallelism. Now
  `chain/executor.py::_execute_loop` dispatches the ready set per wave:
  `max_parallel_steps=1` (or a single ready step) takes the **legacy
  lane** — `self._execute_step(run, ready[0], …)` byte-identical to the
  old path, no pool created; otherwise `_execute_batch` runs
  `ready[:max_workers]` (capacity cap) on a
  `ThreadPoolExecutor(max_workers=policy.max_parallel_steps)`.
  - **Guarded merge:** all step-finish mutations funnel exclusively
    through new `_apply_step_result` / `_apply_step_failure` under
    `self._merge_lock`; `events.jsonl` appends serialize under
    `self._events_lock`; `BudgetTracker` reservations were already
    lock-protected and gate submissions unchanged.
  - **Cancellation:** pre-submit `_check_cancelled` checkpoint per task
    stops submissions mid-batch; workers hit the existing retry-boundary
    checkpoint (siblings stop); the pool is fully **drained before**
    `ChainCancelled` propagates — no orphan worker writes state after
    the loop exits. Steps in-flight at cancel time may remain
    `"running"` in the final cancelled run (bounded by batch size ≤
    `max_parallel_steps`); T-044 `rebuild_run` resets them to `pending`
    on resume.
  - ⚠️ **Behavior note:** step *completion order* is now nondeterministic
    at `max_parallel_steps>1` — results themselves stay deterministic.
  - Evidence: 🆕 `tests/integration/test_parallel_execution.py` (11):
    parallel=1 parity ×2 (start order == declaration order; peak
    concurrency == 1); speedup ×2 (**≥3× on 8-step map @ parallel=4**,
    FakeProvider latency 0.15s; capacity-cap peak ≤ 3 with 12 ready);
    stress ×4 (3 seeds × 20 map steps with ~30% injected random
    failures — each step executed exactly once, state consistent;
    critical-failure skip); cancellation ×2 (mid-batch: siblings stop,
    pool drained, mid-flight ≤ batch size; pre-cancelled token ⇒ zero
    provider calls); DAG waves ×1 (reduce completes last). check.sh
    ALL GREEN: **886 passed, 1 skipped**.
- **R-602 (T-045): `context_policy` enforced in `build_prompt` —
  the decorative field becomes a real lever.** `chain/models.py`:
  `canonical_context_policy(value)` — alias map (`full`,
  `selective`→`full` [legacy default, byte-identical parity],
  `summary`, `summaries`→`summary`, `minimal`); unknown value ⇒
  `ValueError` (fail fast). `summarize_for_context(text,
  max_tokens=SUMMARY_TOKENS_PER_DEP=256)` — deterministic
  budgeted extract (70% head + explicit omission marker + 30%
  tail; within-budget passes verbatim; token accounting via the
  central T-024 estimator; `lru_cache` = per-step-output summary
  cache). `ChainStep.build_prompt(dependency_results,
  dependency_meta=None)` now renders per policy: `full` verbatim
  (no unconditional concatenation remains), `summary` budgeted
  per-dep summaries, `minimal` dependency name+status lines with
  **zero result content**; `{previous_context}` placeholder
  respected in all modes. `chain/executor.py`: plan-time
  validation in `execute()` — any step with an unknown policy
  fails the run **before the first provider call** (run_error +
  state saved); `_execute_step` passes `dependency_meta`
  (name/status from the DAG) for `minimal`. Chain-authoring guide
  (when to use each mode + the summary-starvation caveat: mark
  data-dependent edges `full` explicitly) = comment block over
  the policy map in `chain/models.py`. Evidence:
  🆕 `tests/unit/test_context_policy.py` (28): alias/unknown
  matrix ×10; three-mode render goldens ×7 (verbatim strings,
  incl. minimal-completeness: every declared dep named, zero
  content bytes; placeholder in all modes); legacy parity ×2
  (`selective` default byte-identical to the pre-T-045
  concatenation, missing-dep skip); summarizer ×3 (verbatim
  within budget, deterministic truncation, head+tail preserved);
  5-step fixture: step-5 prompt under `summary` **≤50% of the
  unbounded baseline** (acceptance) + minimal<summary<full
  ordering; executor E2E ×4 (unknown policy → failed with zero
  provider calls; provider-received prompt actually shrinks under
  `summary`; `minimal` provider sees no dep content; default
  chain unchanged — regression).
- **R-601 (T-044): Crash resume wired — `can_resume`/`load_state`
  get their first production callers.** 🆕 `chain/resume.py`:
  `scan_resumable(runs_dir)` (startup + on-demand scan for
  interrupted runs — `state.json` in a non-terminal state:
  `running` = mid-run kill, `failed` = retryable stop);
  `check_drift(project_snapshot, project_root)` re-hashes the
  files pinned by the run's real content hashes (T-033/R-305,
  same sha256 as `_build_project_snapshot`) against the current
  disk and returns a `DriftReport` (matched/changed/missing);
  `rebuild_run(state)` reconstructs an executable `ChainRun` —
  `success` steps keep their status + results (never re-executed:
  `get_ready_steps` only schedules the remainder = exactly-once),
  non-success steps reset to `pending`, fresh budget from policy.
  `chain/bridge.py`: launch path factored into `_launch_run`
  (shared by `start_chain` and resume — same events, same gated
  apply, same ticket lifecycle); new `resume_run(run_id, ws_send,
  ticket)` (busy-guard → can_resume → load_state → **drift check:
  any changed/missing file ⇒ refusal frame `chain_resume_refused`
  with the full drift report, zero provider calls, state left
  intact for discard** → rebuild → launch), `discard_run(run_id)`
  (deletes the run dir — `can_resume` false afterwards),
  `list_resumable()`. `chain/models.py`: `to_state_dict` now
  carries `prompt_template` per step (UI-facing `to_dict`
  unchanged) — without it resumed steps would run with empty
  prompts. `server.py`: WS `resume_scan` / `resume_run` /
  `discard_run` handlers (resume goes through `_begin_run_ticket`
  like any chain; refusal releases the ticket) + startup scan
  after bridge construction (informational — decisions stay with
  the user over WS). Resume runbook = `chain/resume.py` module
  docstring. Evidence: `tests/integration/test_crash_resume.py`
  (23): kill-after-step-2-of-5 E2E (resume executes steps 3–5
  **exactly once** — provider call_count == 3, results of 1–2
  preserved verbatim; also the literal-kill variant with state
  stuck on `running`), drift refusal ×4 (changed / missing /
  clean-pass / empty-snapshot), discard ×3, startup scan ×5
  (ignores completed runs + junk), rebuild round-trip ×5,
  ticket-final-state + busy-guard.
- **R-503 (T-043): Knowledge as ContextBundle view; delta prompts —
  agent-loop token burn flattened.** `chain/knowledge.py`: the raw
  stores (`_files_read`/`_dirs_listed`/`_searches`/`_commands`)
  are **deleted** — `KnowledgeAccumulator` is now a view over a
  `ContextBundle`: every tool result registers an item with
  **hash-dedup on insert** (re-reading the same path with unchanged
  content is swallowed entirely; the same body under another path is
  recorded as a reference and rendered once + one referral note; same
  path with *new* content becomes an explicit `@rN` revision so edits
  are visible). Auto-prefetch results (`auto_*` tools), previously
  unclassified and thus invisible to the context, now register like
  everything else. New **`build_iteration_context(max_tokens,
  recent_k=3)`**: per-iteration prompts carry the **delta** — unsent
  items verbatim, previously-sent items as one compressed reference
  line (`path (hash8)`), with a **recent-k floor** (latest k items
  always verbatim) and the stable core (observations/errors — small
  and decisive) attached to every send; items dropped by the token
  budget are *not* marked sent and re-render in full next round.
  `build_context` remains as the **stateless full view** (first-send /
  final user-facing dump) with the exact legacy section shapes —
  the T-024 budget-wiring tests and T-017 goldens pass unchanged.
  `chain/agent_loop.py`: all three prompt builders (initial /
  followup / final) switched to `build_iteration_context` — the
  O(iterations × corpus) full re-injection is gone. **Measured curve**
  (8 iterations, one ~500-token file read per iteration):
  delta `[513, 534, 540, 546, 552, 558, 564, 570]` tokens vs legacy
  full `[513, 1021, …, 4069]` — steady-state flatness **1.067×**
  (gate ≤1.15×), iteration-8 cost **−86%**. Tests:
  `tests/unit/test_knowledge_bundle.py` (21) — insert-dedup ×4, delta
  rendering ×7 (incl. budget-drop re-render + clear reset), retention
  (iteration-1 finding referenced by name+hash at iteration 8;
  observations verbatim throughout), token-cost curve (flat ≤15% +
  executable documentation that the stateless full view grows >4×),
  and full-view parity ×5 (incl. `_files_read` removal pin).
- **R-502 (T-042): Agent manifest — fleet definitions as data; ROLE_MAP
  deleted.** New `agents_rules/manifest.yaml` describes all 21 agents
  (`role → {file, stage, name, description, capabilities, tier,
  fallback}`); the schema is documented in the file header.
  `chain/agent_loader.py`: `ROLE_MAP`/`ROLE_STAGE_MAP` **deleted** — the
  manifest is the single source; strict validation (node-level YAML
  compose, so every error message carries a **line number**:
  `manifest.yaml:<line>: …`) rejects unknown keys, bad stages, non-`base`
  fallbacks, path traversal, duplicate roles, and missing files;
  a broken/missing manifest **fails fast at construction**
  (`ManifestError` aggregates all errors). Resolution is now loud:
  unknown role ⇒ `UnknownAgentRoleError`; a file that vanishes without a
  declared `fallback: base` ⇒ `ManifestError` (the old 3-level silent
  fallback ladder is gone — `base`/synthetic fallback only for
  explicitly-declared chains). **Hot-reload:** the registry rebuilds on
  manifest mtime change (atomic swap; a broken mid-session edit keeps
  the old registry serving and records `last_reload_error`, a later fix
  recovers); the prompt cache is keyed by `(path, mtime)` so editing an
  agent file mid-session takes effect on the next load — the stale-cache
  authoring bug is fixed. `get_definition(role)` exposes manifest
  metadata; `load_by_stage`/security limits (traversal, 50KB, 1000
  lines) and the frozen `AgentPrompt` + content hash are retained.
  Parity gate: `tests/unit/test_agent_manifest.py` pins the deleted
  ROLE_MAP verbatim as baseline and proves all 21 roles resolve
  byte-identically (content hash + stage + source) through the manifest,
  plus schema-rejection (line numbers asserted), loud-failure,
  hot-reload (broken-edit/recovery/monotonic-mtime), and prompt-file
  hot-edit suites — 48 tests.
- **R-501 (T-041): Agent + Delegate runners — legacy dispatch deleted,
  one dispatch path.** `runners/agent.py` (`AgentRunner(loop_factory,
  on_loop)`: builds an `AgentLoop` per run via the factory — which is
  also where a contract-test failure must be planted, since the loop
  swallows provider send errors internally — re-emits loop WS frames as
  free events, streams the final text as `run_output` chunks of 80, and
  reads the terminal status from the ticket because `AgentLoop.run`
  finishes its own ticket) and `runners/delegate.py` (`DelegateRunner
  (bridge)`: wraps `DelegateBridge.run_delegation`; a run parked at
  `waiting_approval` finishes the stream with `handoff="waiting_approval"`
  and returns a completed `RunResult` while the **ticket stays running** —
  `land()`/`reject()` finish it later; decisive outcomes map
  rejected/landed→completed, cancelled→cancelled, failed→failed).
  `server.py`: the agent WS **polling workaround (old L920–965) is
  deleted** — the agent now runs on a worker thread and a new top-level
  `cancel_agent` handler (next to `agent_approval_response`) covers
  mid-run cancellation; `LEGACY_DISPATCH` + `_legacy_dispatch()` and the
  entire legacy ladder (inline direct stream-worker, `start_chain`
  branch, no-ticket delegate thread) are deleted; dispatch is now a
  single `RUNNERS` map (`direct`/`chain`/`agent`/`delegate` → runner
  factories) — `RUNNERS[strategy](**deps).run(request, ticket,
  _RunnerWSAdapter(send))`. `runners/__init__.py` documents the dispatch
  architecture and exports all four runners. Tests: `TestAgentRunnerContract`
  + `TestDelegateRunnerContract` join the shared harness (all four
  runners now pass `RunnerContractMixin`); `test_dispatch_parity.py`
  drops the flag tests (replaced by `test_legacy_dispatch_flag_deleted`
  + `test_runners_map_covers_all_modes`) and adds agent parity
  (success byte-identical frames incl. chunk-80 slicing, cancellation)
  and delegate parity (waiting_approval with both tickets left running
  then landed, provider-failure with identical `delegate_error` frames).
- **R-501 (T-040): Direct + Chain runners behind the `LEGACY_DISPATCH`
  flag.** `runners/direct.py` (`DirectRunner`: one provider stream call
  emitted as `run_output` chunks, cancellation checked between chunks)
  and `runners/chain.py` (`ChainRunner`: wraps the existing `ChainBridge`
  — orchestrator/executor/gated-apply untouched — re-emitting its WS
  frames as free events and translating the terminal state to a
  `RunResult`). Both follow the authoring guide and pass the full
  `RunnerContractMixin` suite. Dispatch: `server.py` gains
  `_legacy_dispatch()` (env `LEGACY_DISPATCH`, default **legacy**;
  `=0` activates the runner path) and `_RunnerWSAdapter` (EventSink →
  legacy WS frames byte-for-byte: `run_output`→`chunk`, chain frames
  pass through under their original names, lifecycle events silent).
  `"direct"` joined `VALID_KINDS` — the direct path now registers a
  ticket like every other mode. Flag lifecycle: after per-mode parity
  is proven for all four modes (T-041) the flag and the legacy paths
  are deleted together — one dispatch path. Parity E2E in
  `tests/integration/test_dispatch_parity.py`: direct success/failure
  frames byte-identical; chain frame sequences identical modulo
  nondeterministic fields (timings/budget/run_id); flag semantics
  pinned (default + `"0"` + other values). 26 new tests
  (734 total, +1 pre-existing skip).
- **R-501 (T-039): Runner protocol + shared contract harness +
  EchoRunner reference — the unified execution contract exists and is
  provably testable before any real runner migrates.** New
  `core/runner.py`: frozen `RunRequest` (mode, message, context,
  `proposed_actions`, per-request `approval_gate` — no globals), frozen
  `RunEvent` (type/run_id/seq/data), frozen `RunResult`
  (completed/failed/cancelled — matching `TERMINAL_STATES`, unknown
  status rejected in `__post_init__`), `EventSink` +
  `runtime_checkable Runner` Protocols, and `EventStream` — a
  well-formedness enforcer that stamps run_id + monotonic seq and makes
  protocol violations loud (`emit` before `started()` / after
  `finished()` / duplicate lifecycle / lifecycle events through the
  free channel all raise RuntimeError — no ghost events). The
  **runner-authoring guide** lives in the module docstring: 5
  obligations (well-formed events, cooperative cancellation via
  `ticket.is_cancelled` checkpoints, approval exclusively through the
  gate with no-gate ⇒ safe reject, no exceptions escape — failures
  become `RunResult(failed)`, ticket finished with the result's status
  before returning). New `tests/contracts/runner_contract.py`:
  `RunnerContractMixin` (subclass + define `make_runner`, same pattern
  as T-010's provider mixin) driving a real runner through a real
  `ExecutionRegistry`: event well-formedness (started first, finished
  last, gapless seq, uniform run_id, finish reason == result status),
  success, planted-crash → failed result not exception, cancellation
  honored via deterministic post-start hook, approval matrix
  (auto-approve applies with request→verdict→applied ordering + gate
  audit; deny ⇒ zero application; no gate ⇒ safe reject), and
  ticket-state == result-status parametrized. New
  `tests/fakes/echo_runner.py`: `EchoRunner` — the smallest runner
  passing the full harness, with `fail_with` / `cancel_after_start`
  test hooks; copy its structure when authoring real runners (T-040+).
  Nothing is wired yet by design — server.py untouched; the real
  runners land behind the LEGACY_DISPATCH flag in T-040. 18 new tests
  in `tests/contracts/test_runner_contracts.py` (9 harness on Echo + 3
  protocol shape + 6 EventStream guarantees).
- **R-403 (T-038): CapacityModel — capacity numbers derived from live
  pool + breaker state instead of account-count fiction.** New
  `providers/capacity.py`: frozen `ProviderCapacity` (name, healthy,
  breaker_state, raw `remaining_calls`, `estimated` flag;
  `effective_calls` property = 0 for unhealthy or unknown) and frozen
  `CapacityReport` (`total_available` = sum of healthy effective
  contributions only; `healthy_count`; report-level `estimated` = any
  *contributing* provider is estimated — an OPEN provider contributes 0
  by definition so its estimate cannot taint the flag).
  `CapacityModel(pool).report()` is pure (no side effects, no external
  calls) and reads only the public `get_pool_status()` — a provider
  whose T-037 breaker is OPEN contributes zero regardless of what its
  raw counter claims; recovery through the breaker restores its
  contribution automatically. **Estimated semantics documented in the
  module docstring** (the capacity-semantics doc): `remaining_calls < 0`
  = the query itself failed (contribute 0, flag estimated);
  `>= UNLIMITED_SENTINEL (999)` = BaseProvider's declared-fiction
  default, flagged as a guess, not a measurement; precise overrides
  stay unflagged. Server: boot banner now prints
  `Capacity: N calls · M healthy providers (تقديري?)` from the model
  (replacing the raw budget sum), and new `GET /api/capacity` returns
  `report().to_dict()` verbatim (503 before boot) so every UI number is
  traceable to model state. Hardcoded `MIN_ACCOUNTS` arithmetic: gone
  since T-036 (config-sourced thresholds) — T-038 pins that with a grep
  gate test so the constants cannot return. 13 new tests in
  `tests/unit/test_capacity_model.py`: capacity property tests
  (healthy-only sum, OPEN→0 with raw number preserved for tracing,
  breaker recovery restores capacity without restart, query failure →
  0 + estimated, sentinel → estimated, unhealthy estimate doesn't taint
  the flag, empty/None pool, purity/value-equality, monotonicity —
  extra failures never increase capacity), `/api/capacity` Flask
  integration (body == `report().to_dict()` byte-for-byte + 503 path),
  and the MIN_ACCOUNTS grep gate.
- **R-403 (T-037): circuit breaker per provider — the permanent
  `_failed_names` blacklist (a provider stayed dead until restart) is
  replaced by a real closed→open→half-open breaker.** New in
  `providers/pool.py`: `BreakerState` StrEnum (with an ASCII transition
  diagram in the docstring) and `CircuitBreaker` — state is computed
  lazily from timestamps (no timers/threads): 3 consecutive failures
  trip it OPEN, the cooldown grows exponentially per trip
  (`min(30s · 2^(trips−1), 600s)`, cap configurable), and once the
  cooldown elapses the breaker turns HALF_OPEN allowing a single probe:
  probe success → CLOSED with the backoff fully healed; probe failure →
  OPEN again immediately with a doubled cooldown. The clock is
  injectable (`clock=time.monotonic` by default) so tests advance time
  deterministically, and an optional `jitter_fn` hook exists for
  production thundering-herd mitigation (deliberately off by default
  for determinism). `ProviderPool` now takes a `breaker_factory`,
  keeps one breaker per provider (created in `add`, dropped in
  `remove`), records success/failure in both `send_with_fallback` and
  `stream_with_fallback`, filters `_get_available()` through
  `breaker.available()`, and enriches `get_pool_status()` with a
  `breaker` snapshot while keeping the legacy `failed_recently` key
  (`True` ⇔ breaker not CLOSED). **The never-called `reset_failures()`
  is deleted** — the breaker owns the failure lifecycle now
  (cooldown → probe → automatic recovery, no restart needed). 29 new
  tests in `tests/unit/test_circuit_breaker.py`: full transition
  matrix with a fake clock, exponential-cap sequence checks,
  FakeProvider recovery integration through the pool (excluded while
  OPEN with zero call attempts, reused after cooldown), healthy-path
  regression (fallback order / get_best / status contract unchanged),
  and a grep gate asserting `reset_failures` / `self._failed_names`
  are gone from production code.
- **R-402 (T-036): explainable routing — every decision now carries a
  complete record, and the magic thresholds moved to config.** New
  `chain/routing_config.py`: frozen `RoutingThresholds` (the three
  score cut-offs 2.0/5.0/8.0 + the three account minimums 2/3/4 +
  `version`) with invariant validation in `__post_init__` (strictly
  ascending thresholds, non-decreasing account minimums ≥ 1);
  `thresholds_from_config` reads the new `config.yaml` `routing:`
  section with strict schema rejection — unknown key, wrong type
  (bools rejected explicitly), broken ordering, or a non-mapping
  section all raise loud `ValueError`s at boot; a missing section
  yields the historical defaults byte-for-byte. `RoutingRecord`
  answers "why did it pick full_chain?": mode, forced string, all 5
  raw dimension scores + total, **matched signals** (which regex
  patterns actually fired — `analyze_complexity` now collects them
  into `ComplexityAnalysis.matched_signals`, additive field outside
  `to_dict`), ideal vs final strategy, tier, step-by-step
  `downgrade_path` (honest where the `downgraded` flag is not — the
  silent delegate→full_chain budget drop now shows as
  `["delegate", "full_chain"]`), budget total, applied thresholds,
  and config version. Router: thresholds are injected
  (`RequestRouter(..., thresholds=)`), the module-level constants are
  **gone** (a new `check.sh` grep gate forbids reintroducing them),
  and every routing path — chat-mode, natural, budget-downgraded,
  forced — funnels through `_attach_record`. Wire contract intact:
  `RoutingDecision.to_dict()` and `ComplexityAnalysis.to_dict()`
  unchanged (the record lives in `decision.record`, `compare=False`)
  — all 30 T-034 golden decisions still replay identically.
  `server.py` boot reads the section and fails loudly on a broken
  one; `config.yaml` documents each knob with a tuning guide
  (semantics, ordering constraints, when to bump `version`).
  23 tests in `tests/unit/test_routing_record.py`: record
  completeness on all four paths + downgrade-path honesty + wire-dict
  purity, schema acceptance/rejection matrix ×11 (defaults, partial
  fill, int→float promotion, unknown keys, type errors, broken
  orderings, thresholds actually rerouting), and the R-402
  **monotonicity property**: on an ascending-complexity input ladder
  with ample budget, a higher score never routes to a lighter tier —
  budget downgrade being the only, always-recorded exception.
- **R-401 (T-035): unified routing vocabulary — the 6-vs-4 strategy
  drift is over.** New `core/strategy.py` is the single source of
  truth: `RoutingTier` (direct/chained/delegate — the router's
  how-much-effort layer), `ExecutionStrategy` (the six builders — the
  orchestrator's which-builder layer), `RouteLabel` (the four
  historical wire strings for `RoutingDecision.strategy`, frozen
  byte-for-byte for the T-034 corpus and WS clients, with a `.tier`
  property replacing server.py's string conditionals), and
  `STRATEGY_TABLE: dict[ExecutionStrategy, StrategySpec]` — one row
  per strategy (tier + builder + one-line doc); adding a strategy is
  now one enum member + one table row, and an import-time
  completeness check plus `assert_never` in every dispatch make a
  missing branch a **loud** mypy/runtime failure instead of a silent
  misroute. Swaps: `ComplexityAnalysis.recommended` returns the enum
  (the old `recommended_strategy` str property delegates to it —
  wire/`to_dict` unchanged); `select_strategy` dispatches on enum
  members via `ExecutionStrategy.parse` (unknown/`"delegate"` force
  strings still fall to direct — the corpus-pinned quirk, now an
  **explicit** branch, not an else-swallow); router's ideal/budget
  cascade and `_forced_route` compare `RouteLabel` members (unknown
  forced strings still pass through verbatim — corpus-pinned);
  `server.py` dispatches on `routing.tier` instead of
  `strategy in ("auto_chain", "full_chain")` / `== "delegate"`.
  `check.sh` gained a vocabulary grep gate: zero free-string strategy
  comparisons in production code (`.value` allowed at wire
  boundaries). Parity proof: all 30 T-034 golden decisions replay
  identically with the golden file untouched; plus 23 new tests in
  `tests/unit/test_strategy_table.py` (table completeness ×5,
  tier↔strategy matrix + `RouteLabel.tier` + decision-tier incl. the
  unknown-string→direct dispatch, `parse` roundtrips/junk ×7,
  exhaustiveness + grep gate ×5).
- **R-401 (T-034): golden corpus of 30 real routing decisions — the
  pre-refactor behavioral baseline for the vocabulary unification.**
  New `tests/goldens/routing/` package: `harness.py` runs 30
  deterministic scenarios against the **real, untouched** production
  code (`RequestRouter.route`, `SmartOrchestrator.select_strategy`,
  `build_delegate`) with fixed budgets and generated file content —
  the "instrumentation" lives entirely inside `tests/`, so the
  acceptance clause *instrumentation removed* holds by construction
  (nothing was ever added to production). `capture_corpus.py`
  (module-runnable) freezes the results into
  `routing_corpus.golden.json` — 16 router + 13 orchestrator +
  1 delegate-builder decisions. Coverage: all **4 router** strategy
  strings (`direct`/`auto_chain`/`full_chain`/`delegate` — natural,
  forced, and budget-downgraded) and all **6 orchestrator** strategy
  strings (5 via `select_strategy`, `delegate` via the builder path).
  The corpus honestly records three current quirks the refactor must
  reckon with: (a) `select_strategy(force_strategy="delegate")` falls
  through `else` into a **silent** direct fallback; (b) an unknown
  `force_strategy` string passes through **verbatim** into
  `RoutingDecision.strategy`; (c) the budget downgrade
  delegate→full_chain does **not** set `downgraded=True` (the flag
  only fires on the final drop to direct). Replay + coverage-matrix
  guard in `tests/unit/test_routing_corpus.py` (38 tests): every
  scenario re-run must dict-equal its golden entry ("corpus replays
  on legacy"), and the vocabulary/downgrade/misroute matrix is
  asserted explicitly — after T-035 this file must stay green with
  the golden untouched, byte for byte.
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
