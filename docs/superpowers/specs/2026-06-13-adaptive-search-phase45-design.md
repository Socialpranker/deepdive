# Adaptive Search (Phase 4.5) + Deviation Log — Design

**Date:** 2026-06-13
**Status:** Approved (brainstorm) → ready for implementation plan
**Scope owner:** `references/workflow.md`, `phases.yaml`, `references/source_dispatch.md` (read-only), `runner/orchestrator.py` (engine, when wired)

## Goal

Give the deep-research workflow **bounded runtime adaptivity** in its search stage.
Today search is a single planned salvo: the LLM designs the channel strategy in
Phase 3 / 4.0, sub-agents execute it in Phase 4.1, and they **cannot react** to what
they find — an unexpected lead, an empty channel, a contradiction between sources, or a
citation pointing at an unreachable primary source all go unaddressed until the much
later adversarial/refresh phases (or never).

This design adds a **new, conditional Phase 4.5 "Adaptive sweep"** that sits between
Phase 4 (Search) and Phase 5 (Scoring). It lets the orchestrator (Opus) react to
in-flight findings by spending a **bounded budget of "deviations"** — re-runs of the
search machinery that depart from the approved plan — while preserving the system's
core property: **transparency**. Every deviation (taken or declined) is recorded in a
structured `deviations.md`, which the adversarial pass (Phase 6) is then obligated to
audit.

**Finish line of this design:** Phase 4.5 is specified end-to-end — trigger contract,
budget economics, depth limit, the `deviations.md` artifact, and how Phases 4/5/6/7
change around it — at the methodology level (`workflow.md` / `phases.yaml`), with a
clear note of what the `runner/` engine must implement when it reaches search.

**Explicitly NOT in this design:**
- The `runner/` does not yet do real web search (source URLs are placeholders — see
  the multi-llm-runner spec). This design describes the *methodology* and the engine
  contract; wiring it into live retrieval is downstream work.
- The `source_dispatch.md` matrix is **not modified**. Deviations reuse the existing
  channels — adaptivity changes *when/whether* a channel is queried, not *what
  channels exist*.

## Background: where the code is today

- **Phase 3 (Plan, Opus/medium)** decomposes the question into subquestions
  (`plan.md` section 11) and, at Phase 4.0 (Source Dispatch, Sonnet/medium), runs each
  subquestion through the deterministic matrix in `references/source_dispatch.md` to
  fix primary/secondary/fallback channels into `plan.md` section 12 **before** search.
- **Phase 4.1** launches N parallel `Explore`-type sub-agents (medium: 2–3, deep: 4–5)
  that **follow the fixed dispatch** — they do not choose channels. Each returns JSON
  (sources, quotes, scoring). This gives reproducibility and a user-approvable plan.
- **Phase 4.2/4.3** dedup by URL, apply paywall fallback (`channels.md`), and write
  `sources/SNN_<slug>.md` + `sources.csv`.
- **Phase 5** scores every source (credibility/recency/bias). **Phase 6** runs an
  adversarial pass (4 questions, Opus/high). **Phase 7** generates refresh targets.
- **`runner/`** is a model-agnostic engine scaffold: `orchestrator.py` drives the
  phases through an `LLMProvider` interface (`complete()` + `fanout()`); real web
  search is a TODO (URLs are placeholders). `DryRunProvider` gives deterministic,
  network-free runs — the natural test substrate for orchestration logic.

The current search philosophy is **LLM-as-planner, not LLM-as-router-in-the-loop**.
This design keeps that as the default and adds adaptivity as a bounded, conditional,
auditable exception — not a replacement.

## Decisions (from brainstorm)

| Decision | Choice |
|---|---|
| Core tension | Adaptivity vs. predictability — resolved as a **hybrid with a deviation budget**, not free-form runtime routing |
| Where adaptivity lives | A **new, separate Phase 4.5** (not a modification of Phase 4 internals) — clean phase boundary, independently testable, toggleable |
| Who decides to deviate | The **orchestrator (Opus)** with the full cross-agent picture — **not** the cheap sub-agents. Judgment is expensive-model work; execution stays cheap. |
| When 4.5 runs | **Conditionally, at any depth** (variant B): 4.5 is eligible regardless of depth, but runs only if the gate fires. The gate = "at least one trigger flag is raised." Crucially, a flag can be raised by **either** a sub-agent **or** the always-on cross-agent scan (next row), so "conditional B" and "always-on scan A" are complementary, not conflicting: A is one of the two ways the B-gate can fire. No flag from either source → 4.5 is skipped entirely. |
| Trigger set | Four triggers: `empty_result`, `citation_lead` (self-correction), `unexpected_finding`, `contradiction` (scope-expansion) |
| Detection model | **Two-tier**: sub-agents signal generously on **all four** flags (high recall); Opus filters strictly **and** independently re-checks cross-agent contradictions the sub-agents structurally cannot see (high precision) |
| Deviation classes | **cheap** (self-correction: doesn't change scope) vs **expensive** (scope-expansion: departs from the approved plan) — different budgets |
| Budget by depth | shallow `2 cheap / 0 expensive`, medium `4 / 1`, deep `8 / 3` (starting calibration) |
| Depth (nesting) limit | shallow/medium = 1, deep = 2 — a deviation may spawn a sub-round, but nesting is capped independently of budget (rabbit-hole guard) |
| Exhausted budget/depth | Remaining candidates are **not executed but still recorded** in `deviations.md` as `not_pursued` + reason — never a silent skip |
| Deviation log | Structured `deviations.md` (one record per considered trigger), owned solely by the orchestrator |
| Consumer | **Phase 6 (adversarial) must read it** — a 5th adversarial question audits *both* sides: `pursued` (did the agent stray?) and `not_pursued` (is it a coverage hole?) |
| Contradiction gap fix | Variant **A** (feeds the B-gate, doesn't compete with it): a sub-agent sees only its own half and can miss a cross-agent contradiction, so before evaluating the gate the orchestrator does **one cheap (Haiku/Sonnet) cross-agent scan for contradictions** on every run; a hit raises a synthetic flag so the B-gate fires and 4.5 starts even when every sub-agent was silent |

## Architecture

### Flow

```
Phase 4 (Search) — UNCHANGED in behavior, one planned salvo
   └─ sub-agents follow Phase 4.0 dispatch
   └─ NEW: each sub-agent emits a `signals` block in its JSON (all 4 flags)
   ↓
[Orchestrator gate]
   ├─ cheap cross-agent contradiction scan (Haiku/Sonnet) over all JSON   ← variant A
   ├─ any sub-agent flag fired  OR  scan found a contradiction?
   │     ├─ no  → Phase 4.5 SKIPPED → straight to Phase 5
   │     └─ yes → run Phase 4.5
   ↓
Phase 4.5 (Adaptive sweep) — loop owned by the orchestrator (Opus):
   while (budget remains for the relevant class) AND (depth < depth_limit):
     1. Opus reviews aggregated output + flags + contradiction-scan result
     2. selects which triggers are JUSTIFIED → which deviations to run
     3. classifies each: cheap (self-correction) | expensive (scope-expansion)
     4. debits the matching budget counter; writes a `deviations.md` record
     5. launches a sub-round of sub-agents (same Phase 4.1 machinery)
     6. new results merge into the shared pool; depth++
   (every considered-but-skipped trigger → `not_pursued` record)
   ↓
Phase 5 (Scoring) — scores ALL sources (planned + deviation-sourced) identically
   ↓
Phase 6 (Adversarial) — NEW obligation: read deviations.md (5th question)
   ↓
Phase 7 (Refresh) — reads not_pursued/carry_forward as refresh-target candidates
```

### Component 1 — Trigger contract (sub-agent → orchestrator)

Each Phase 4.1 sub-agent adds a `signals` block to its existing JSON. It **reports
observations; it does not decide to deviate.**

```json
{
  "subquestion_id": "Q3",
  "sources": [ ... ],
  "signals": {
    "empty_result":       { "fired": true,  "detail": "0 relevant hits on channel `academic`; all 4 results off-topic" },
    "unexpected_finding": { "fired": true,  "detail": "sources point to EU AI Act as the cause of the market collapse — not in the plan" },
    "contradiction":      { "fired": false, "detail": null },
    "citation_lead":      { "fired": true,  "detail": "S07 cites a primary Gartner 2024 report; no direct link present" }
  }
}
```

| Trigger | Nature | Meaning | Reliable detector |
|---|---|---|---|
| `empty_result` | self-correction (cheap) | a planned channel returned nothing relevant | the sub-agent (sees its own output) |
| `citation_lead` | self-correction (cheap) | a source references an unreachable primary source | the sub-agent |
| `unexpected_finding` | scope-expansion (expensive) | an important angle outside the plan surfaced | sub-agent *signals a candidate*; **Opus confirms** |
| `contradiction` | scope-expansion (expensive) | sources conflict | **often only Opus** (a sub-agent sees only its half) → backed by the always-on cross-agent scan |

**Principle:** sub-agents signal generously (recall), Opus filters strictly
(precision). Cheap model = recall, expensive model = judgment. A sub-agent's
`unexpected_finding`/`contradiction` flag is a *candidate*, never an automatic spend.

**Gate logic:** "run 4.5?" = `OR` over all `fired` across all sub-agents **OR**
contradiction-scan hit. One signal is enough to *enter* 4.5; Opus then decides what is
actually worth a deviation.

### Component 2 — Budget, classes, depth limit (orchestrator-owned)

| Class | Triggers | Limit rationale |
|---|---|---|
| **cheap** (self-correction) | `empty_result`, `citation_lead` | finishes already-planned work; doesn't change scope → generous |
| **expensive** (scope-expansion) | `unexpected_finding`, `contradiction` | departs from the approved plan → hard ceiling |

| Depth | cheap | expensive | depth (nesting) limit |
|---|---|---|---|
| shallow | 2 | 0 | 1 |
| medium | 4 | 1 | 1 |
| deep | 8 | 3 | 2 |

- **shallow expensive = 0** — the only hard cut, and it's *by class*, not by entering
  4.5: a shallow run with `empty_result` still self-corrects; a shallow
  `unexpected_finding` is recorded `not_pursued: budget_exhausted` and not run.
- **expensive grows slowly** (0→1→3) — the costliest, scope-changing class.
- **cheap grows generously** (2→4→8) — self-correction is cheap and usually useful.
- **Depth limit** is independent of budget: a deviation may spawn a sub-round, but at
  the depth limit that sub-round cannot spawn its own. deep=2 lets a citation chain go
  two levels (S07 → Gartner report → primary source inside it), then stop.
- **Numbers are starting calibration**, expected to be tuned against real runs.
- **Debit is atomic, orchestrator-only**, performed *before* launching a sub-round.
  One counter per run; no distributed state.

### Component 3 — `deviations.md` (the audit artifact)

Lives beside `plan.md` / `sources/` in the run directory. One record per **considered**
trigger (both `pursued` and `not_pursued`).

```markdown
# Deviations — <research topic>

## D1
- subquestion: Q3
- trigger: empty_result
- class: cheap
- status: pursued
- decision_by: orchestrator (opus)
- rationale: channel `academic` returned 0 relevant; reformulated query + added fallback `preprint-servers`
- action: re-ran sub-round on `preprint-servers`, query "..."
- depth: 1
- budget_after: { cheap: 3, expensive: 1 }
- outcome: +2 sources (S11, S12), both relevant
- new_source_ids: [S11, S12]

## D2
- subquestion: Q5
- trigger: unexpected_finding
- class: expensive
- status: not_pursued
- decision_by: orchestrator (opus)
- rationale: EU AI Act angle is relevant but the expensive budget is exhausted (deep=3 spent on D-…)
- action: none
- depth: —
- budget_after: { cheap: 5, expensive: 0 }
- outcome: —
- carry_forward: recommended as a Phase 7 refresh-target
```

| Field | Purpose |
|---|---|
| `trigger` + `class` | which of the 4 triggers; cheap/expensive |
| `status` | `pursued` / `not_pursued` — **the honesty field** |
| `decision_by` | always the orchestrator (Opus) — records that judgment ran on the expensive model |
| `rationale` | **why** Opus decided as it did — the thing Phase 6 will challenge |
| `action` | concrete sub-round launched (channel + query), or `none` |
| `depth` | nesting level of this deviation |
| `budget_after` | spend traceability |
| `outcome` + `new_source_ids` | what the deviation actually yielded; links to `sources/` |
| `carry_forward` | for `not_pursued`: where it goes (usually a Phase 7 refresh-target) |

**Data flow:** Phase 4.5 (orchestrator/Opus) **writes** every decision. Phase 5 does
**not** touch the log — it scores `new_source_ids` like any other source (deviation-
sourced material is indistinguishable in quality; only its provenance differs, and that
provenance is in `deviations.md`). Phase 6 **reads** it (mandatory input). Phase 7
**reads** `not_pursued`/`carry_forward` for refresh candidates.

### Component 4 — Phase 6 obligation (the consumer)

A **5th adversarial question** is added to the existing four:

> Review `deviations.md`. For each `pursued` deviation: was it justified, and did it
> pull the research away from the approved plan? For each `not_pursued`: is the skipped
> angle critical to the final answer — is this a hole in coverage?

This audits **both** failure modes: over-adaptation (the agent chased a tangent) and
under-coverage (a real gap was left unexplored because of budget/depth).

## Changes to existing files

| File | Change |
|---|---|
| `phases.yaml` | New entry `4.5` "Adaptive sweep" (model: opus, effort: high, depth_gate: shallow — *runs conditionally on a flag at any depth, not by depth_gate*; see note below) |
| `references/workflow.md` | New Phase 4.5 section; Phase 4.1 sub-agent JSON gains the `signals` block; Phase 4 gains the orchestrator gate + cross-agent contradiction scan; Phase 6 gains the 5th adversarial question; Phase 7 reads `carry_forward` |
| `scripts/stamp_docs.py` consumers (README/SKILL/workflow counts) | Re-stamped from `phases.yaml` so phase counts/lists stay in sync (existing `--check` gate) |
| `runner/orchestrator.py` | (engine, when wired) the 4.5 loop: gate, budget/depth counters, `deviations.md` writer, sub-round dispatch via existing `fanout()` |

**Note on `phases.yaml` `depth_gate`:** the existing `depth_gate` field means "minimum
depth at which the phase is *mandatory*." Phase 4.5 doesn't fit that axis cleanly — it's
*conditional on a runtime flag*, not on depth. The spec models this as: 4.5 is
**eligible at all depths** but **gated by trigger presence**, with the per-depth budget
table controlling how much it may do. Implementation note: represent 4.5 as eligible
from `shallow` with a `conditional: flag` marker rather than overloading `depth_gate`,
so `stamp_docs.py`/`phases_manifest.py` don't mis-describe it as always-mandatory.

## Testing strategy

Built on the existing contour: `tests/`, `pytest.ini`, `stamp_docs.py --check`, CI per PR.

1. **Doc consistency (existing gate).** `phases.yaml` gains `4.5` → `stamp_docs.py
   --check` green; phase counts/lists in README/SKILL/workflow.md re-stamped. Catches
   "added a phase in code, forgot the docs."
2. **Budget/depth logic (unit, on `DryRunProvider`).** Tests the *orchestration of
   decisions*, not search quality:
   - cheap/expensive debited correctly, never below zero (independent counters);
   - `expensive=0` on shallow → scope deviation not run, `not_pursued: budget_exhausted` written;
   - depth limit: a sub-round at the limit does not spawn another deviation;
   - no flags **and** no contradiction-scan hit → 4.5 skipped entirely (straight to Phase 5);
   - **honesty test:** exhausted budget/depth still writes a `not_pursued` record (never a silent skip).
3. **Signal contract (unit).** sub-agent JSON `signals` parses; `OR` gate decides
   correctly; Opus filter (mocked on DryRun) can mark a sub-agent's `unexpected_finding`
   as unjustified; cross-agent contradiction scan raises a synthetic flag when sub-agents
   were silent.
4. **End-to-end (integration, opt-in behind `-m live`).** Mirrors the existing live
   smoke test: one small real run with a deliberate trigger (a query whose planned
   channel is knowingly empty) → assert `deviations.md` created, deviation executed,
   source added.

### Edge cases (must be covered)

| Edge case | Expected behavior |
|---|---|
| All sub-agents flag, but the deep budget is exhausted on the first few | the rest → `not_pursued`; run does not hang; Phase 5 proceeds |
| A deviation itself returns nothing | record `outcome: 0 sources`; budget **still** debited (an attempt costs money); no loop |
| Sub-agent sends malformed/partial `signals` | treated as "no flag" (fail-safe: never block the run on a cheap model); log a warning |
| Contradiction visible only to Opus (sub-agents silent) | the always-on cross-agent scan (variant A) raises it; 4.5 runs even with zero sub-agent flags |

## Open questions / future work

- **Budget calibration.** The 2/0/1 · 4/1/1 · 8/3/2 table is a first guess; tune against
  real runs (track in `deviations.md` how often budgets are hit vs. wasted).
- **Cross-agent scan cost.** Variant A adds a small per-run cost (one cheap scan). If it
  proves wasteful on flag-less runs, revisit B (4.5 unconditional only on deep). This is
  a one-line change in the gate and was explicitly the closest alternative.
- **Runner integration.** This spec is methodology-first; the `runner/` engine
  implements the loop only once real web search lands (see multi-llm-runner spec).
