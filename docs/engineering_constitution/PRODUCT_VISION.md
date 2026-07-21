# PRODUCT_VISION.md — Engineering Constitution, Chapter: Product Vision

> **Product:** WebDev AI Editor — a browser-based, Arabic-first, local-first AI coding
> environment (Flask + WebSocket backend, vanilla-JS frontend, provider-abstracted models).
>
> **Truth-state labels used throughout:**
> `VERIFIED_CURRENT_STATE` (observed in code/tests) · `DOCUMENTED_INTENT` (in roadmap/docs,
> not yet built) · `PROPOSED_DIRECTION` (this chapter's strategic proposal) ·
> `STRATEGIC_HYPOTHESIS` (belief requiring market validation) · `UNVERIFIED` (could not be
> confirmed) · `CONTRADICTED` (conflicting evidence, resolution stated).

---

## 1. Constitutional Status

This chapter is a **binding part of the Engineering Constitution**. It governs product
decisions the way the architecture chapters govern code decisions.

- **Authority:** Any feature, refactor, or roadmap item that conflicts with the Decision
  Filters (§7), Strategic Pillars (§8), or Non-Goals (§15) requires an explicit amendment
  to this chapter *before* implementation.
- **Precedence:** `MASTER_DEVELOPMENT_ROADMAP.md` remains the execution plan; this chapter
  defines *why* and *what for*. Where they conflict, this chapter wins on intent, the
  roadmap wins on sequencing — and the conflict must be recorded in the workspace.
- **Evidence discipline:** every claim herein carries a truth-state label. Claims labeled
  `VERIFIED_CURRENT_STATE` were confirmed against the repository at commit `d4b8562`
  (81/81 roadmap tasks complete; test gate 1543 passed / 1 skipped; mypy clean over 67 files).
- **Amendment process:** see §16.

## 2. North Star

**"The AI coding environment developers can actually trust: every AI action is previewable,
approvable, attributable, and undoable — in their own language, on their own machine."**
`PROPOSED_DIRECTION`

The governing question for every product decision:

> *What would make a developer choose this product instead of Cursor, Windsurf, VS Code +
> Copilot, JetBrains AI, Antigravity, or Claude Code?*

Our answer is **not** "cheaper model access" and **not** "more autonomous agents." It is
**verifiable trust plus governed autonomy plus first-class Arabic/local-first experience** —
a combination none of the incumbents structurally offers (see §6, §9).

## 3. Verified Foundation

What already exists and works — the strengths this vision is built on and must preserve.
All items `VERIFIED_CURRENT_STATE` unless noted.

1. **A complete trust loop.** ApprovalGate is the *single* mutation checkpoint; every
   file-changing action flows through consent → preview → apply. CheckpointManager provides
   rollback frames surfaced in a run-history UI; ExecutionRegistry provides cooperative
   cancel. (FINDING-2)
2. **Deterministic context engine.** Seven context sources composed under a tiered byte
   budget (must_have / high / opportunistic), protected by byte-exact golden tests; one
   ProjectScan per message; tree-sitter symbol index; bounded semantic seed (2.0s timeout).
   (FINDING-3)
3. **Provenance-tracked project memory.** JSONL store with per-entry provenance, staleness
   detection via index fingerprints, and full user edit/delete through a Memory Panel.
   Memory is inspectable and owned by the user, never a black box. (FINDING-4)
4. **Governed 21-agent fleet-as-data.** Agents defined in `manifest.yaml` (analyze 8 /
   plan 2 / execute 3 / review 5 / meta 3), hot-reloaded atomically, executing only through
   an allowlist with timeout/output caps and a verify-step contract. Plugins receive a
   capability-limited context (no filesystem/session/server/provider access), enforced by
   grep gates in CI. (FINDING-5, FINDING-6)
5. **Typed, swappable model layer.** Provider contract with typed requests/responses,
   capabilities, and error taxonomy (RateLimit/Timeout/Transient/ContextTooLarge); provider
   pool, per-account budgets, capacity model. Config stubs for API-key providers
   (gemini/openai) already exist. (FINDING-8)
6. **Config-switched scale, single-process-first.** Planner (heuristic/llm/hybrid), backend
   (memory/redis), dispatch (in-proc/worker) are configuration choices verified by a
   frame-parity harness and per-project leases — not architecture forks. (FINDING-7)
7. **A real quality regime.** `scripts/check.sh`: mypy → grep gates (single ws.send
   boundary, SafeReader, plugin capability, tier quarantine) → AST lints → color-token
   lint → 1,154 test functions across 79 files, with goldens for context/routing/chain.
   (FINDING-10)
8. **Local-first + Arabic-first.** Real file access on the user's machine, local sessions
   and backups, Arabic-first UI copy throughout. (FINDING-13)

**Known weak points (also verified):** frontend breadth is below a premium editor bar
(vanilla JS, 9 files; no diff panel yet — Phase 9 spec is `DOCUMENTED_INTENT`, FINDING-11);
free-provider dependence is commercially fragile (FINDING-12, resolved in §12); no product
outcome measurement exists beyond CI green.

## 4. Target Users & Jobs-To-Be-Done

`STRATEGIC_HYPOTHESIS` unless noted.

**Primary persona — the "Sovereign Developer":** a professional or serious hobbyist web
developer who wants AI acceleration but refuses to surrender control: they want to see,
approve, and be able to undo every change; they distrust editors that silently rewrite
their code or upload their project wholesale.

**Second persona — the Arabic-speaking developer** (`VERIFIED_CURRENT_STATE` that the
product serves them today): tens of millions of Arabic-first developers and learners are
served by incumbents only through English-first UIs. Arabic-first is a wedge, not a
translation checkbox.

**Third persona — the constrained-budget developer:** students, freelancers, and teams in
markets where $20+/month AI subscriptions are prohibitive. Served today via free provider
pools (`VERIFIED_CURRENT_STATE`), served tomorrow via model-source independence (§12).

**Jobs-to-be-done:**
- *"Make AI changes to my real project without fear"* → Trust Loop (Pillar 1).
- *"Have the AI actually understand my codebase, predictably"* → Context & Memory (Pillar 2).
- *"Delegate multi-step work but stay in command"* → Governed Autonomy (Pillar 3).
- *"Work in my language, on my machine, keep my code mine"* → Premium Experience (Pillar 5).

## 5. Operational Definition of "Premium AI-Native"

"Premium" here is defined operationally, not aspirationally. A capability qualifies as
premium AI-native **only if** it satisfies all five tests: `PROPOSED_DIRECTION`

1. **Accountable:** every AI-originated change is attributable (which agent, which model,
   which context) and reversible (checkpoint/rollback). — *Already true:* `VERIFIED_CURRENT_STATE`.
2. **Deterministic where it matters:** context assembly, routing, and frame protocol are
   golden-tested; the same input yields the same envelope. — *Already true.*
3. **Consent-boundaried:** no mutation, no command, no plugin capability without an explicit,
   auditable gate. — *Already true.*
4. **Honest:** staleness is marked, provenance is shown, errors are typed and surfaced —
   the product never fakes certainty. — *Already true.*
5. **Crafted:** the surface (diff views, run history, memory panel, Arabic typography and
   RTL) feels like a professional tool, not a demo. — *Partially true; the gap Phase 9
   must close.* `DOCUMENTED_INTENT`

Tests 1–4 are our existing engineering identity restated as product promises. Test 5 is
the primary investment frontier.

## 6. Core Differentiation

`PROPOSED_DIRECTION`, grounded in `VERIFIED_CURRENT_STATE` mechanisms.

Incumbents compete on **model quality and autonomy depth** — dimensions where they hold
structural advantages (capital, proprietary models). We do not fight there. We compete on
three dimensions they structurally under-serve:

1. **Verifiable trust as a product feature.** Not "you can review the diff if you want,"
   but an architecture where unreviewed mutation is *impossible* (single ApprovalGate,
   grep-gated single ws.send boundary) and undo is *guaranteed* (checkpoint frames).
   Incumbents bolt review onto autonomy; we built autonomy inside review.
2. **Explainable context, ownable memory.** Deterministic, budget-tiered, golden-tested
   context assembly + provenance-tracked memory the user can read, edit, and delete.
   Competitors' context/memory is opaque; ours is a glass box.
3. **Arabic-first, local-first sovereignty.** A professional AI editor whose primary
   language is Arabic and whose data plane is the user's own machine. No incumbent treats
   either as identity.

**What we deliberately do not claim:** superior raw model intelligence (we are
model-source independent, §12); the deepest autonomous agent (we cap autonomy with
governance by design, §8 Pillar 3).

## 7. Product Decision Filters

Ordered; earlier filters veto later ones. Every proposed feature must pass all applicable
filters or be rejected/amended. `PROPOSED_DIRECTION`

- **F1 — Trust is inviolable.** If a feature bypasses ApprovalGate, weakens rollback,
  hides provenance, or creates a second mutation path, it is rejected regardless of value.
- **F2 — Determinism before cleverness.** New context/routing/agent behavior must be
  golden-testable or explicitly quarantined behind a tier/flag. No un-testable magic.
- **F3 — Governed autonomy only.** Agent/plugin capabilities expand solely through the
  allowlist + verify-step + capability-surface mechanisms — never through ad-hoc escapes.
- **F4 — Single-process-first.** Features must work in the in-proc/memory default; scale
  paths (redis/worker) remain config switches with parity harnesses, never prerequisites.
- **F5 — Arabic-first, not Arabic-translated.** User-facing surfaces ship with Arabic as
  the design language (RTL, copy, typography) at parity or better than English.
- **F6 — Evidence before rewrite.** No framework migrations or rewrites without documented
  evidence of need (this filter formally rejects IMPROVEMENT-6-class proposals).

## 8. Strategic Pillars

Five pillars; each names its verified foundation and its investment direction.

### Pillar 1 — Trust Loop *(identity pillar)*
- **Foundation (`VERIFIED_CURRENT_STATE`):** ApprovalGate, CheckpointManager + rollback
  frames, run-history UI, cooperative cancel.
- **Direction (`PROPOSED_DIRECTION`):** make trust *visible*: first-class diff panel
  (roadmap R-901), richer run-history narratives (what/why/which-agent), one-click restore
  points. Marketing identity: **"the AI editor you can audit and undo."**

### Pillar 2 — Context & Memory Intelligence
- **Foundation:** 7-source deterministic context engine with byte budgets and goldens;
  provenance memory with staleness + user edit/delete.
- **Direction:** surface the glass box — show the user *what context the AI saw* per run;
  memory quality curation; keep goldens as the honesty contract for every enhancement.

### Pillar 3 — Governed Autonomy
- **Foundation:** 21-agent fleet-as-data, hot-reload, allowlist + verify-step, capability-
  limited plugin surface.
- **Direction:** deeper delegation (multi-step plans) that *never* exits governance;
  user-authorable agents as data (manifest extensions), not code; verify-step results as
  first-class UI artifacts.

### Pillar 4 — Predictable Platform
- **Foundation:** typed provider contract/pool/budget/capacity; config-switched
  planner/backend/dispatch with frame-parity harness; the check.sh quality regime.
- **Direction:** model-source independence in practice (activate API-key providers from
  existing stubs, §12); publish reliability behavior (typed-error UX); keep in-proc the
  first-class default.

### Pillar 5 — Premium Experience
- **Foundation:** working Arabic-first vanilla-JS frontend; Memory Panel; run history;
  local-first files/sessions/backups.
- **Direction:** execute the Phase 9 UX professional track (`DOCUMENTED_INTENT`) — diff
  panel first, then editor-surface polish — under filter F6 (no framework rewrite without
  evidence). Arabic typography/RTL as a craft signature, not a checkbox.

## 9. "Why Not Them?" — Defensibility

`PROPOSED_DIRECTION` built on `VERIFIED_CURRENT_STATE` mechanisms; competitor
characterizations are `UNVERIFIED (ACCESS-LIMITED)` structural sketches (§10).

**Why a developer picks us over each incumbent:**
- **vs Cursor / Windsurf:** their power flows from proprietary model access and deep
  autonomy; their review is a layer *on top of* mutation. Ours is the inverse: mutation
  exists only *inside* consent, with guaranteed rollback and golden-tested context. A
  developer who has been burned by a silent AI rewrite has no equivalent home there.
- **vs VS Code + Copilot:** AI is an extension in a general editor; trust, memory, and
  agent governance are not architectural concepts. We are AI-native around one trust loop.
- **vs JetBrains AI:** heavyweight, paid, English-first, cloud-entangled. We are
  local-first, zero-API-key to start, Arabic-first.
- **vs Claude Code:** terminal-centric, powerful but expert-oriented, paid API. We offer a
  browser UI with visual approval/rollback and Arabic-first accessibility.
- **vs Antigravity:** our acknowledged inspiration (README) — we differentiate through the
  trust loop, provenance memory, and Arabic-first identity rather than imitation.

**What is defensible vs copyable:** any single feature (a diff panel, an approval dialog)
is copyable. What is hard to copy is the *architecture-level commitment*: incumbents would
have to make unreviewed mutation impossible and context deterministic — reversals of their
autonomy-first identities and economics. Our defensibility is coherence, plus the
Arabic-first market position where no incumbent has identity or intent. `STRATEGIC_HYPOTHESIS`

## 10. Competitive Landscape

**Research status: ACCESS-LIMITED (as of 2026-07-22).** No live competitive web research
was performed for this chapter; all competitor entries are general-knowledge structural
sketches labeled `UNVERIFIED`. This chapter therefore anchors on durable structural
contrasts (our verified mechanisms vs their category-level designs) and deliberately avoids
volatile claims (pricing, model names, feature lists). A refresh with live research is a
standing amendment trigger (§16).

| Competitor | Category posture (UNVERIFIED) | Our structural contrast (VERIFIED on our side) |
|---|---|---|
| Cursor | AI-native VS Code fork; autonomy + proprietary model access | Consent-gated mutation; byte-exact context goldens |
| Windsurf | Agentic multi-step flows | Governed autonomy: allowlist + verify-step; no silent writes |
| VS Code + Copilot | General editor + AI extension | Single AI-native trust loop, not a bolted-on assistant |
| JetBrains AI | Deep-IDE, paid, cloud-linked | Local-first, zero-key onboarding, lightweight browser UI |
| Antigravity | Agent-first environment (our inspiration) | Provenance memory + rollback + Arabic-first |
| Claude Code | Terminal agent on paid API | Visual approval/rollback UX; Arabic-first browser surface |

**Category trend we bet on (`STRATEGIC_HYPOTHESIS`):** as AI autonomy commoditizes, the
scarce differentiators become *trust, explainability, and locality* — exactly our pillars.

## 11. Experience Principles

`PROPOSED_DIRECTION`, codifying behavior already present in the product (§3) plus Phase 9
direction. These bind all UI/UX work:

1. **Nothing happens without you.** Every mutation shows a preview and waits for consent;
   the approve/reject moment is the emotional center of the product.
2. **Everything can be undone.** Restore points are always visible; undo is one action away.
3. **Show your work.** Runs narrate which agent, which steps, which verifications; context
   and memory are inspectable (glass box, never black box).
4. **Honest states only.** Stale memory is marked stale; provider failures surface as
   typed, human-readable conditions — never fake progress or silent retry theater.
5. **Arabic is the first language.** RTL layout, Arabic microcopy, and Arabic typography
   are designed first; English is the parity locale.
6. **Calm professionalism.** Dense information, quiet chrome, no gamification; color usage
   governed by the token lint (`VERIFIED_CURRENT_STATE` gate).

## 12. Commercial Principles

Resolves CONTRADICTION-3 (free-provider identity vs premium ambition). `PROPOSED_DIRECTION`
except where labeled.

1. **Model-source independence is the asset — not free accounts.** The typed provider
   contract, pool, per-account budgets, and capacity model (`VERIFIED_CURRENT_STATE`) make
   model sources interchangeable. Free pools are *one* source class (the zero-friction
   on-ramp); user-owned API keys are another (stubs for gemini/openai already exist in
   `config.yaml`, `VERIFIED_CURRENT_STATE`). The product's identity must migrate from
   "free" to "source-sovereign."
2. **Never sell what we don't control.** Free third-party provider pools are a fragile
   ToS/durability foundation (FINDING-12) and must never back a paid promise. Paid value
   attaches only to what we own: the trust loop, context/memory intelligence, governance,
   and experience.
3. **Local-first is a commercial stance.** The user's code never becomes our inventory;
   monetization must never require code exfiltration. `STRATEGIC_HYPOTHESIS`: this is a
   selling point precisely because incumbents cannot easily match it.
4. **Candidate value ladder (`STRATEGIC_HYPOTHESIS`, requires market validation):**
   free source-sovereign core → paid craft tier (premium UX capabilities, advanced
   run-history/verification analytics) → team tier (shared agent manifests, shared
   memory governance). No tier may violate Filters F1–F6.
5. **Arabic market wedge:** pricing and packaging designed for MENA purchasing power
   first. `STRATEGIC_HYPOTHESIS`.

## 13. Prioritization Doctrine

`PROPOSED_DIRECTION`. When choosing among valid work items:

1. **Trust-visible before trust-internal.** The trust loop exists (§3) but is under-shown;
   work that makes trust *perceivable* (diff panel R-901, run narratives) outranks new
   internal capability.
2. **Close the experience gap before widening the capability gap.** Phase 9 UX
   (`DOCUMENTED_INTENT`) outranks new agent/planner sophistication: FINDING-11 says the
   surface, not the engine, is the bottleneck to "premium."
3. **Deepen before broaden.** Improve the 21 existing agents' verify-step quality before
   adding agent #22.
4. **Commercial de-risking is scheduled, not deferred.** Activating API-key provider stubs
   (model-source independence in practice) enters the next planning cycle — it is the
   hedge against FINDING-12.
5. **Tie-breaker:** the option that strengthens more pillars (§8) with less new
   ungoverned surface wins.

## 14. Measures of Progress

Current state: no product outcome measurement exists beyond CI (`VERIFIED_CURRENT_STATE`).
Proposed measures — all `PROPOSED_DIRECTION`, instrumentation itself is future work and
must respect local-first (opt-in, local-computable where possible):

- **Trust behavior:** % of AI-proposed changes reviewed via diff before approval; rollback
  usage rate (healthy non-zero = users trust undo); approval-to-regret ratio.
- **Context honesty:** context-golden suite kept green (already enforced); user "context
  was wrong" reports per 100 runs.
- **Governed autonomy:** verify-step pass rate per agent; zero ungoverned-mutation
  incidents (constitutional invariant — target is absolute).
- **Experience:** Phase-9 milestone completion (diff panel shipped, etc.); Arabic-UX parity
  audits.
- **Platform reliability:** typed-error rates by provider source; capacity-model accuracy.
- **Engineering floor (already measured, `VERIFIED_CURRENT_STATE`):** check.sh fully green;
  coverage does not regress below the 68.4% baseline.

## 15. Non-Goals

Explicit refusals; each requires a constitutional amendment to reverse. `PROPOSED_DIRECTION`
(items 5–7 restate roadmap scope exclusions, `DOCUMENTED_INTENT`):

1. **No ungoverned autonomy.** No "YOLO mode" that bypasses ApprovalGate — not even as an
   opt-in flag.
2. **No cloud-first pivot.** No architecture where the user's code must leave their
   machine to get core value.
3. **No model ownership ambitions.** We do not train or host foundation models; we remain
   source-sovereign consumers.
4. **No framework rewrite without evidence** (Filter F6; IMPROVEMENT-6 formally rejected).
5. **No auth/multi-tenant billing platform** inside the current product scope (roadmap
   exclusion).
6. **No streaming-token UX or prompt-wording micro-optimization tracks** (roadmap
   exclusions).
7. **No general-purpose IDE parity race.** We do not chase every VS Code feature; we win
   on the pillars, not on breadth.
8. **No dark-pattern engagement mechanics.** No streaks, no gamified nudges toward
   accepting AI changes.

## 16. Evolution & Governance of This Chapter

- **Custodian:** the acting CPO/Principal Architect role; changes land via the same
  review discipline as code.
- **Amendment triggers (any of):** completion of Phase 9 UX track; activation of API-key
  providers; first commercial packaging decision; a live competitive research pass
  (upgrading §10 from ACCESS-LIMITED); any violation or forced exception to Filters F1–F6;
  contradiction discovered between this chapter and verified repository state.
- **Amendment procedure:** (1) record the trigger and evidence in
  `ENGINEERING_WORKSPACE.md`; (2) propose the edit with truth-state labels; (3) re-run the
  validation checklist (repository accuracy, strategic coherence, filter consistency);
  (4) update this section's revision log.
- **Standing review:** at each roadmap phase boundary, re-verify every
  `VERIFIED_CURRENT_STATE` claim against the codebase; downgrade or annotate anything no
  longer accurate. Stale vision text is a constitutional defect.
- **Relationship to other chapters:** architecture/security/quality chapters (when
  authored) must cite this chapter's filters; conflicts resolve per §1.

**Revision log:**
- 2026-07-22 — v1.0 — Initial authoring (Phases 0–5 of the vision program). Evidence base:
  repository @ `d4b8562`, 81/81 tasks complete, gate 1543 passed / 1 skipped. Known
  limitation: competitive research ACCESS-LIMITED.

