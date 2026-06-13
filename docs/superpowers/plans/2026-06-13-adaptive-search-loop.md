# Adaptive Search Loop (Phase 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Turn Phase 4 (Search) from a single planned salvo into an orchestrator-driven loop (round → Opus evaluation → optional bounded deviation round), with a deviation budget, depth limit, and an audited `deviations.md` log.

**Architecture:** Two layers. **Layer A (methodology):** rewrite `references/workflow.md` + annotate `phases.yaml` so the documented workflow describes the loop (no new phase id — phase count stays the same). **Layer B (engine):** add a focused `runner/adaptive.py` module holding the loop's logic (signals contract, budget counters, depth tracking, `deviations.md` writer, the cross-agent contradiction scan, and the Opus deviation decision), and wire it into `Orchestrator.search()`. Layer B is built and tested entirely on `DryRunProvider` + mocks — real web search is out of scope (source URLs stay placeholders, per the spec).

**Tech Stack:** Python 3.12, pytest (flat `tests/` dir, `from runner.* import ...`), the existing `LLMProvider` interface (`complete()`/`fanout()`, tiers `strong`/`mid`/`cheap`), the hand-rolled `phases_manifest.py` + `stamp_docs.py` doc gate.

**Spec:** `docs/superpowers/specs/2026-06-13-adaptive-search-loop-design.md`

**Out of scope (per spec):** real web search/retrieval (URLs remain `example.com`); `source_dispatch.md` matrix changes; live API calls in the main test suite (one opt-in `-m live` smoke is noted but not required to pass CI).

---

## File Structure

**Layer A — methodology / docs:**
- Modify: `phases.yaml` — annotate Phase 4 as a loop (a comment + an optional non-REQUIRED key; do NOT add a new phase row).
- Modify: `references/workflow.md` — rewrite the Phase 4 section as a round loop; add the `signals` block to the Phase 4.1 sub-agent JSON; add the 5th adversarial question to Phase 6; add `carry_forward` reading to Phase 7.

**Layer B — engine (`runner/`):**
- Create: `runner/adaptive.py` — all adaptive-loop logic in one focused module:
  - `Signals` / signal parsing (`parse_signals`, fail-safe)
  - `Budget` dataclass (cheap/expensive counters + depth)
  - `Deviation` dataclass + `write_deviations` (the `deviations.md` writer)
  - `cross_agent_contradiction_scan(provider, agent_outputs)` (cheap scan)
  - `decide_deviations(provider, round_state)` (the Opus decision: filter + classify)
  - `run_search_loop(provider, ...)` (the round → eval → round driver with termination)
- Modify: `runner/orchestrator.py` — `search()` calls `run_search_loop`; `RunState` gains a `deviations` list and `depth` budget seeds.
- Create: `tests/test_adaptive.py` — unit tests for everything in `adaptive.py` (on `DryRunProvider` + mock providers).
- Create: `tests/test_adaptive_integration.py` — one DryRun end-to-end loop test; one `-m live` smoke (skipped by default).

**Budget constants (from spec, starting calibration):**

```python
# depth -> (cheap_budget, expensive_budget, depth_limit)
BUDGET_BY_DEPTH = {
    "shallow": (2, 0, 1),
    "medium":  (4, 1, 1),
    "deep":    (8, 3, 2),
}
```

---

## Layer A — Methodology

### Task 1: Annotate Phase 4 as a loop in `phases.yaml`

**Files:**
- Modify: `phases.yaml` (Phase 4 entry)
- Test: `tests/test_phases_manifest.py` (existing — must still pass)

**Context:** `phases_manifest.load_phases` requires exactly `REQUIRED = (id, name_ru, name_en, model, effort, depth_gate)` per phase and reads *all* `key: value` lines. Extra keys are preserved, not rejected. `stamp_docs` only consumes `id/name_en/model/effort/name_ru` + `len(phases)`. So we may add a comment and/or a non-required key to Phase 4 WITHOUT changing the phase count or breaking the gate. We must NOT add a new phase row (that would bump `count:phases` and require re-stamping every doc with a new row).

- [x] **Step 1: Verify the current gate is green (baseline)**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_phases_manifest.py -v`
Expected: PASS (establishes baseline before edits).

- [x] **Step 2: Add the loop annotation to Phase 4**

In `phases.yaml`, find the Phase 4 entry:

```yaml
  - id: "4"
    name_ru: "Поиск"
    name_en: "Search"
    model: sonnet
    effort: medium
    depth_gate: shallow
```

Replace it with (adds a clarifying comment + a non-REQUIRED `loop` marker key — the per-round search work stays `sonnet`; the between-rounds evaluation is `strong`/Opus and is documented in workflow.md prose, NOT as a new phase):

```yaml
  # Phase 4 is an orchestrator-driven LOOP (round -> Opus eval -> optional
  # bounded deviation round). The per-round search fan-out is sonnet/medium;
  # the between-rounds evaluation runs at the strong tier. This is ONE phase
  # whose internal behavior is a loop — no new phase id is introduced, so the
  # phase count is unchanged. See references/workflow.md "Phase 4" for the loop.
  - id: "4"
    name_ru: "Поиск"
    name_en: "Search"
    model: sonnet
    effort: medium
    depth_gate: shallow
    loop: "true"
```

- [x] **Step 3: Verify the manifest still parses and the gate stays green**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_phases_manifest.py -v && python3 scripts/phases_manifest.py | python3 -c "import json,sys; p=json.load(sys.stdin); assert len(p)==9, len(p); assert p[4]['id']=='4' and p[4].get('loop')=='true'; print('OK: 9 phases, Phase 4 loop-annotated')"`
Expected: PASS, then `OK: 9 phases, Phase 4 loop-annotated` (confirms count unchanged at 9 and the marker is readable).

- [x] **Step 4: Verify the doc-stamp gate still passes (count unchanged)**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --check`
Expected: exit 0 (no drift — because the phase count and per-phase stamped fields are unchanged). If it reports drift, STOP: it means `loop:` leaked into a stamped field — revisit Step 2.

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add phases.yaml
git commit -m "docs(phases): пометить фазу 4 как loop (без новой фазы-id)"
```

---

### Task 2: Rewrite the Phase 4 section in `references/workflow.md`

**Files:**
- Modify: `references/workflow.md` (the Phase 4 / "Поиск" section, currently around lines 385–431)
- Test: `cd ... && python3 scripts/stamp_docs.py --check` (workflow.md is a stamp target — must stay green)

**Context:** `workflow.md` is in `stamp_docs.TARGETS`. Editing prose is safe as long as we don't touch `<!--gen:...-->` marker spans. The rewrite documents: Round 1 = the approved plan; an orchestrator evaluation after every round (cross-agent contradiction scan + Opus deviation decision); the `signals` block in the sub-agent JSON; budget/depth/`deviations.md` mechanics; termination conditions.

- [x] **Step 1: Read the current Phase 4 section to get exact surrounding anchors**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && grep -n "Phase 4\|## 4\|Поиск\|4.0\|4.1\|4.2\|4.3" references/workflow.md | head -40`
Expected: line numbers for the Phase 4 sub-sections (4.0 Source Dispatch, 4.1 Launch sub-agents, 4.2 Fetch & Dedup, 4.3 Save). Note them; the rewrite replaces the body of this section, preserving any `<!--gen-->` markers and the surrounding Phase 3 / Phase 5 headers.

- [x] **Step 2: Replace the Phase 4 body with the loop description**

Within the Phase 4 section (between the Phase 3 end and the Phase 5 header), keep the existing 4.0/4.1/4.2/4.3 step descriptions but reframe them as **Round 1** and insert the loop. Insert this block (adapt heading levels to match the file's existing style — use the same `##`/`###` depth as the neighbouring phases):

````markdown
**Phase 4 is an orchestrator-driven loop, not a single salvo.** Round 1 executes the
approved plan (Phase 4.0 dispatch). After *every* round the orchestrator evaluates the
aggregated results and may spend a bounded *deviation* to launch another round. The
plan stays authoritative as the starting point; deviations are bounded and recorded.

#### Round structure

1. **Round 1 = the plan.** Run Phase 4.0 (Source Dispatch) → Phase 4.1 (N sub-agents
   following the fixed dispatch) → 4.2 (dedup) → 4.3 (save sources). This always runs.
2. **Each sub-agent emits a `signals` block** in its JSON (in addition to sources):

   ```json
   {
     "subquestion_id": "Q3",
     "round": 1,
     "sources": [ ... ],
     "signals": {
       "empty_result":       { "fired": true,  "detail": "0 relevant hits on `academic`" },
       "unexpected_finding": { "fired": false, "detail": null },
       "contradiction":      { "fired": false, "detail": null },
       "citation_lead":      { "fired": true,  "detail": "S07 cites Gartner 2024, no link" }
     }
   }
   ```

   Sub-agents signal **generously** (high recall). They report observations; they do
   NOT decide to deviate.

3. **Orchestrator evaluation (after every round, `strong` tier / Opus):**
   - Aggregate all sub-agent JSON for the round.
   - **Cross-agent contradiction scan** (cheap tier): scan the whole pool for sources
     that conflict — this catches contradictions no single sub-agent can see (each
     sees only its own subquestion).
   - Opus reviews flags + scan + aggregated output and selects which triggers are
     *justified* (strict precision — a sub-agent's `unexpected_finding` is a candidate,
     not an automatic spend).
   - For each justified trigger, if budget for its class remains AND depth < limit:
     classify cheap/expensive, debit the counter, write a `deviations.md` record,
     and launch the next round. Otherwise write a `not_pursued` record.
4. **The loop ends** when no justified trigger remains, OR both budgets are exhausted,
   OR the depth limit is reached. Then proceed to Phase 5.

#### Triggers (4) and their classes

| Trigger | Class | Meaning |
|---|---|---|
| `empty_result` | cheap (self-correction) | a planned channel returned nothing relevant |
| `citation_lead` | cheap (self-correction) | a source cites an unreachable primary source |
| `unexpected_finding` | expensive (scope-expansion) | an important angle outside the plan surfaced |
| `contradiction` | expensive (scope-expansion) | sources conflict |

*Self-correction finishes already-planned work (doesn't change scope) → generous
budget. Scope-expansion departs from the approved plan → hard ceiling.*

#### Budget & depth (by research depth)

| Depth | cheap | expensive | depth (nesting) limit |
|---|---|---|---|
| shallow | 2 | 0 | 1 |
| medium | 4 | 1 | 1 |
| deep | 8 | 3 | 2 |

- `shallow expensive = 0`: a shallow `unexpected_finding`/`contradiction` is recorded
  `not_pursued: budget_exhausted`, never run. Self-correction still works on shallow.
- **Depth** = how many deviation-spawned rounds deep the current round is (Round 1 =
  depth 0). A deviation from a depth-limit round cannot spawn another.
- Debit is atomic, orchestrator-only, before launching the next round.

#### `deviations.md`

Written beside `plan.md` / `sources/`. One record per *considered* trigger (both
`pursued` and `not_pursued` — **exhausted budget/depth still leaves a record; never a
silent skip**). Phase 6 audits it; Phase 7 reads `not_pursued`/`carry_forward`.
````

- [x] **Step 3: Verify the stamp gate stays green (markers untouched)**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --check`
Expected: exit 0. If drift is reported on `workflow.md`, you edited inside a `<!--gen-->` span — undo that part.

- [x] **Step 4: Sanity-check the prose references nothing undefined**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && grep -n "deviations.md\|signals\|cross-agent\|not_pursued\|depth limit" references/workflow.md | head`
Expected: the new terms appear in the Phase 4 section (confirms the block landed).

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add references/workflow.md
git commit -m "docs(workflow): фаза 4 как цикл раундов (signals/бюджет/deviations.md)"
```

---

### Task 3: Add the 5th adversarial question (Phase 6) and `carry_forward` (Phase 7) to `workflow.md`

**Files:**
- Modify: `references/workflow.md` (Phase 6 adversarial section; Phase 7 refresh section)
- Test: `cd ... && python3 scripts/stamp_docs.py --check`

**Context:** Phase 6 currently lists 4 adversarial questions. The spec adds a 5th that audits `deviations.md` on both sides. Phase 7 generates refresh targets; the spec routes `not_pursued`/`carry_forward` deviations into that candidate set.

- [x] **Step 1: Locate the Phase 6 adversarial questions and Phase 7 refresh section**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && grep -n "adversarial\|Phase 6\|Phase 7\|refresh\|steel-man\|counter-argument" references/workflow.md | head -30`
Expected: line anchors for the 4-question adversarial list and the refresh-targets section.

- [x] **Step 2: Append the 5th adversarial question**

After the existing 4th adversarial question in the Phase 6 section, add:

```markdown
5. **Deviation audit.** Review `deviations.md`. For each `pursued` deviation: was it
   justified, and did it pull the research away from the approved plan (over-adaptation)?
   For each `not_pursued`: is the skipped angle critical to the final answer — is this a
   hole in coverage (under-coverage)? Flag both failure modes explicitly.
```

- [x] **Step 3: Add `carry_forward` reading to Phase 7**

In the Phase 7 (refresh targets) section, add a bullet:

```markdown
- **Carry-forward deviations.** Read `deviations.md` for `not_pursued` records with a
  `carry_forward` field; each is a first-class refresh-target candidate (an angle the
  search loop identified but could not pursue within budget/depth).
```

- [x] **Step 4: Verify the stamp gate stays green**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --check`
Expected: exit 0.

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add references/workflow.md
git commit -m "docs(workflow): 5-й adversarial-вопрос (аудит deviations) + carry_forward в фазе 7"
```

---

### Task 4: Re-stamp docs and verify Layer A consistency

**Files:**
- Modify: (potentially) any `stamp_docs` target, via `--write`
- Test: `cd ... && python3 scripts/stamp_docs.py --check`

**Context:** Layer A added no new phase, so counts shouldn't change — but run `--write` to be certain the docs are byte-identical to what the gate expects, then confirm `--check` is clean. This guards against any stray marker drift introduced while editing prose.

- [x] **Step 1: Run the stamper in write mode**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --write`
Expected: either "no changes" or a small rewrite. Inspect with `git diff --stat`.

- [x] **Step 2: Confirm no semantic phase-count change leaked in**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && git diff` 
Expected: if anything changed, it is NOT a phase count or a new table row (those would signal Task 1 went wrong). If you see `count:phases` change from 9, STOP and fix Task 1.

- [x] **Step 3: Final gate check**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --check && python3 -m pytest tests/test_stamp_docs.py tests/test_phases_manifest.py -v`
Expected: exit 0 and PASS.

- [x] **Step 4: Commit (only if Step 1 produced changes)**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add -A
git commit -m "docs: ре-штамп после правок методологии фазы 4 (counts без изменений)"
```

If Step 1 produced no changes, skip this commit.

---

## Layer B — Engine (`runner/adaptive.py`, on DryRun + mocks)

> All Layer B tasks use TDD: write the failing test, run it red, implement minimally,
> run it green, commit. Tests live flat in `tests/`; import as `from runner.adaptive
> import ...`. The package already has `tests/__init__.py` and `runner/` is importable
> as a package (orchestrator uses `from .providers import ...`).

### Task 5: Signals contract + fail-safe parsing

**Files:**
- Create: `runner/adaptive.py`
- Test: `tests/test_adaptive.py`

**Context:** A sub-agent returns JSON with a `signals` block (4 triggers, each
`{fired: bool, detail: str|null}`). The orchestrator must parse it defensively: a
malformed/partial `signals` block is treated as "no flag fired" (fail-safe — never
block the run on a cheap model's bad output), with a warning. We model a parsed signal
set as a frozenset of fired trigger names plus the raw details.

- [x] **Step 1: Write the failing test**

Create `tests/test_adaptive.py`:

```python
from runner.adaptive import parse_signals, TRIGGERS, CHEAP_TRIGGERS, EXPENSIVE_TRIGGERS


def test_trigger_taxonomy_is_fixed():
    assert TRIGGERS == ("empty_result", "citation_lead", "unexpected_finding", "contradiction")
    assert CHEAP_TRIGGERS == ("empty_result", "citation_lead")
    assert EXPENSIVE_TRIGGERS == ("unexpected_finding", "contradiction")


def test_parse_signals_extracts_fired_triggers():
    blob = {
        "signals": {
            "empty_result": {"fired": True, "detail": "0 hits"},
            "citation_lead": {"fired": True, "detail": "S07 cites Gartner"},
            "unexpected_finding": {"fired": False, "detail": None},
            "contradiction": {"fired": False, "detail": None},
        }
    }
    fired, details = parse_signals(blob)
    assert fired == {"empty_result", "citation_lead"}
    assert details["empty_result"] == "0 hits"


def test_parse_signals_missing_block_is_no_flag():
    fired, details = parse_signals({"sources": []})
    assert fired == set()
    assert details == {}


def test_parse_signals_malformed_is_fail_safe():
    # signals present but not a dict, unknown keys, missing 'fired' -> ignored, no crash
    for bad in [{"signals": "oops"}, {"signals": {"weird": {"fired": True}}},
                {"signals": {"empty_result": {"detail": "x"}}}, {"signals": None}]:
        fired, details = parse_signals(bad)
        assert fired == set(), bad
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'runner.adaptive'`.

- [x] **Step 3: Write minimal implementation**

Create `runner/adaptive.py`:

```python
#!/usr/bin/env python3
"""Adaptive search loop for Phase 4 (round -> Opus eval -> optional deviation round).

This module owns the loop's *logic* so the orchestrator stays a thin driver:
  - the sub-agent `signals` contract (parse_signals)
  - the deviation budget + depth tracking (Budget)
  - the deviations.md audit artifact (Deviation, write_deviations)
  - the cross-agent contradiction scan + the Opus deviation decision
  - the round loop itself (run_search_loop)

Everything is provider-agnostic (LLMProvider) and runs on DryRunProvider for tests.
Real web search is out of scope here — sources stay placeholders.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

TRIGGERS = ("empty_result", "citation_lead", "unexpected_finding", "contradiction")
CHEAP_TRIGGERS = ("empty_result", "citation_lead")
EXPENSIVE_TRIGGERS = ("unexpected_finding", "contradiction")


def parse_signals(agent_blob: dict) -> tuple[set[str], dict[str, str]]:
    """Extract the set of fired trigger names + their details from one sub-agent's JSON.

    Fail-safe: any malformed/partial signals block yields an empty set (no flag) and a
    logged warning — a cheap model's bad output must never block the run.
    """
    fired: set[str] = set()
    details: dict[str, str] = {}
    block = agent_blob.get("signals")
    if not isinstance(block, dict):
        if block is not None:
            log.warning("signals block is not a dict (%r) — treating as no-flag", type(block))
        return fired, details
    for name in TRIGGERS:
        entry = block.get(name)
        if not isinstance(entry, dict):
            continue
        if entry.get("fired") is True:
            fired.add(name)
            d = entry.get("detail")
            if isinstance(d, str):
                details[name] = d
    unknown = set(block) - set(TRIGGERS)
    if unknown:
        log.warning("signals block has unknown triggers %s — ignored", sorted(unknown))
    return fired, details
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS (4 tests).

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): signals-контракт + fail-safe парсинг сигналов сабагента"
```

---

### Task 6: Budget + depth counters

**Files:**
- Modify: `runner/adaptive.py` (add `Budget`, `BUDGET_BY_DEPTH`, `class_of`)
- Test: `tests/test_adaptive.py` (append)

**Context:** The orchestrator owns one `Budget` per run: separate cheap/expensive
counters plus a depth limit. Debit is atomic and must never go below zero. `class_of`
maps a trigger to its class. `can_spend`/`spend` gate and decrement. Depth is tracked
per round (Round 1 = depth 0).

- [x] **Step 1: Write the failing test**

Append to `tests/test_adaptive.py`:

```python
from runner.adaptive import Budget, BUDGET_BY_DEPTH, class_of


def test_budget_by_depth_matches_spec():
    assert BUDGET_BY_DEPTH["shallow"] == (2, 0, 1)
    assert BUDGET_BY_DEPTH["medium"] == (4, 1, 1)
    assert BUDGET_BY_DEPTH["deep"] == (8, 3, 2)


def test_class_of_maps_triggers():
    assert class_of("empty_result") == "cheap"
    assert class_of("citation_lead") == "cheap"
    assert class_of("unexpected_finding") == "expensive"
    assert class_of("contradiction") == "expensive"


def test_budget_for_depth_seeds_counters():
    b = Budget.for_depth("medium")
    assert b.cheap == 4 and b.expensive == 1 and b.depth_limit == 1


def test_budget_spend_decrements_and_floors_at_zero():
    b = Budget.for_depth("deep")  # 8 / 3 / 2
    assert b.can_spend("cheap") is True
    b.spend("cheap")
    assert b.cheap == 7
    # drain expensive to zero
    b.spend("expensive"); b.spend("expensive"); b.spend("expensive")
    assert b.expensive == 0
    assert b.can_spend("expensive") is False
    # spending past zero is a programming error -> raises, never goes negative
    import pytest
    with pytest.raises(ValueError):
        b.spend("expensive")


def test_budget_shallow_has_no_expensive():
    b = Budget.for_depth("shallow")  # 2 / 0 / 1
    assert b.can_spend("expensive") is False
    assert b.can_spend("cheap") is True


def test_budget_depth_limit_gate():
    b = Budget.for_depth("medium")  # depth_limit 1
    assert b.depth_ok(0) is True   # round 1 -> spawning a depth-1 round is allowed
    assert b.depth_ok(1) is False  # at the limit, no further spawn
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -k budget -v`
Expected: FAIL with `ImportError: cannot import name 'Budget'`.

- [x] **Step 3: Write minimal implementation**

Append to `runner/adaptive.py`:

```python
# depth -> (cheap_budget, expensive_budget, depth_limit)
BUDGET_BY_DEPTH = {
    "shallow": (2, 0, 1),
    "medium":  (4, 1, 1),
    "deep":    (8, 3, 2),
}


def class_of(trigger: str) -> str:
    """Map a trigger name to its deviation class."""
    if trigger in CHEAP_TRIGGERS:
        return "cheap"
    if trigger in EXPENSIVE_TRIGGERS:
        return "expensive"
    raise ValueError(f"unknown trigger {trigger!r}")


@dataclass
class Budget:
    """Per-run deviation budget. Orchestrator-owned; debit is atomic, never negative."""
    cheap: int
    expensive: int
    depth_limit: int

    @classmethod
    def for_depth(cls, depth: str) -> "Budget":
        try:
            c, e, d = BUDGET_BY_DEPTH[depth]
        except KeyError:
            raise ValueError(f"unknown depth {depth!r} (expected shallow|medium|deep)")
        return cls(cheap=c, expensive=e, depth_limit=d)

    def can_spend(self, klass: str) -> bool:
        return getattr(self, klass) > 0

    def spend(self, klass: str) -> None:
        if not self.can_spend(klass):
            raise ValueError(f"{klass} budget exhausted — caller must check can_spend first")
        setattr(self, klass, getattr(self, klass) - 1)

    def depth_ok(self, current_depth: int) -> bool:
        """True if a round at current_depth may spawn a (deeper) deviation round."""
        return current_depth < self.depth_limit
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS (all signals + budget tests).

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): бюджет cheap/expensive + depth-лимит (atomic debit, не уходит ниже нуля)"
```

---

### Task 7: `Deviation` record + `deviations.md` writer

**Files:**
- Modify: `runner/adaptive.py` (add `Deviation`, `write_deviations`)
- Test: `tests/test_adaptive.py` (append)

**Context:** Every considered trigger becomes a `Deviation` record (pursued or
not_pursued). `write_deviations` renders them to a markdown file beside `plan.md`. The
`not_pursued` path is the honesty guarantee — exhausted budget/depth still produces a
record. Field set matches the spec's `deviations.md` example.

- [x] **Step 1: Write the failing test**

Append to `tests/test_adaptive.py`:

```python
from runner.adaptive import Deviation, write_deviations


def test_deviation_pursued_record_renders_all_fields():
    d = Deviation(
        subquestion="Q3", round_from=1, round_to=2, trigger="empty_result",
        klass="cheap", status="pursued", rationale="academic empty; added preprint",
        action="round 2 on preprint-servers", depth=1,
        budget_after={"cheap": 3, "expensive": 1},
        outcome="+2 sources", new_source_ids=["S11", "S12"], carry_forward=None,
    )
    md = d.render()
    assert "trigger: empty_result" in md
    assert "status: pursued" in md
    assert "decision_by: orchestrator (opus)" in md  # constant, always Opus
    assert "new_source_ids: [S11, S12]" in md


def test_deviation_not_pursued_has_carry_forward_and_no_action():
    d = Deviation(
        subquestion="Q5", round_from=1, round_to=None, trigger="unexpected_finding",
        klass="expensive", status="not_pursued", rationale="expensive budget exhausted",
        action=None, depth=None, budget_after={"cheap": 5, "expensive": 0},
        outcome=None, new_source_ids=[], carry_forward="Phase 7 refresh-target",
    )
    md = d.render()
    assert "status: not_pursued" in md
    assert "action: none" in md
    assert "carry_forward: Phase 7 refresh-target" in md


def test_write_deviations_creates_file_with_all_records(tmp_path):
    devs = [
        Deviation(subquestion="Q3", round_from=1, round_to=2, trigger="empty_result",
                  klass="cheap", status="pursued", rationale="r", action="a", depth=1,
                  budget_after={"cheap": 3, "expensive": 1}, outcome="+1",
                  new_source_ids=["S11"], carry_forward=None),
        Deviation(subquestion="Q5", round_from=1, round_to=None, trigger="contradiction",
                  klass="expensive", status="not_pursued", rationale="budget out",
                  action=None, depth=None, budget_after={"cheap": 3, "expensive": 0},
                  outcome=None, new_source_ids=[], carry_forward="refresh"),
    ]
    path = write_deviations(tmp_path, "my topic", devs)
    assert path.name == "deviations.md"
    text = path.read_text(encoding="utf-8")
    assert "# Deviations — my topic" in text
    assert "## D1" in text and "## D2" in text
    assert text.count("decision_by: orchestrator (opus)") == 2


def test_write_deviations_empty_list_still_writes_header(tmp_path):
    path = write_deviations(tmp_path, "topic", [])
    assert path.exists()
    assert "# Deviations — topic" in path.read_text(encoding="utf-8")
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -k deviation -v`
Expected: FAIL with `ImportError: cannot import name 'Deviation'`.

- [x] **Step 3: Write minimal implementation**

Append to `runner/adaptive.py` (add `from pathlib import Path` to the imports at the top of the file):

```python
@dataclass
class Deviation:
    """One considered trigger (pursued or not_pursued) for the deviations.md log."""
    subquestion: str
    round_from: int
    round_to: int | None        # the round this deviation spawned, or None if not pursued
    trigger: str
    klass: str                  # "cheap" | "expensive"
    status: str                 # "pursued" | "not_pursued"
    rationale: str
    action: str | None
    depth: int | None
    budget_after: dict[str, int]
    outcome: str | None
    new_source_ids: list[str] = field(default_factory=list)
    carry_forward: str | None = None

    def render(self) -> str:
        round_str = f"{self.round_from}" if self.round_to is None else f"{self.round_from} → {self.round_to}"
        ids = "[" + ", ".join(self.new_source_ids) + "]"
        ba = "{ cheap: %d, expensive: %d }" % (self.budget_after.get("cheap", 0),
                                               self.budget_after.get("expensive", 0))
        lines = [
            f"- subquestion: {self.subquestion}",
            f"- round: {round_str}",
            f"- trigger: {self.trigger}",
            f"- class: {self.klass}",
            f"- status: {self.status}",
            "- decision_by: orchestrator (opus)",
            f"- rationale: {self.rationale}",
            f"- action: {self.action if self.action else 'none'}",
            f"- depth: {self.depth if self.depth is not None else '—'}",
            f"- budget_after: {ba}",
            f"- outcome: {self.outcome if self.outcome else '—'}",
            f"- new_source_ids: {ids}",
        ]
        if self.carry_forward:
            lines.append(f"- carry_forward: {self.carry_forward}")
        return "\n".join(lines)


def write_deviations(run_dir: Path, topic: str, deviations: list[Deviation]) -> Path:
    """Render all deviation records to <run_dir>/deviations.md. Always writes a header,
    even for an empty list (an empty file is itself an honest signal: nothing deviated)."""
    out = [f"# Deviations — {topic}", ""]
    for i, d in enumerate(deviations, start=1):
        out.append(f"## D{i}")
        out.append(d.render())
        out.append("")
    path = run_dir / "deviations.md"
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return path
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS (all tests so far).

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): Deviation-запись + writer deviations.md (pursued/not_pursued)"
```

---

### Task 8: Cross-agent contradiction scan

**Files:**
- Modify: `runner/adaptive.py` (add `cross_agent_contradiction_scan`)
- Test: `tests/test_adaptive.py` (append)

**Context:** A single sub-agent sees only its own subquestion, so a contradiction
*between* agents is invisible to all of them. The orchestrator runs a cheap scan over
the whole round's pool. It asks the provider (cheap tier) to report conflicting claims
and returns a list of synthetic contradiction findings (subquestion pair + detail).
We test against a **mock provider** whose `complete` returns a canned verdict, so the
logic is deterministic and model-free.

- [x] **Step 1: Write the failing test**

Append to `tests/test_adaptive.py`:

```python
from runner.adaptive import cross_agent_contradiction_scan


class _ScanProvider:
    """Mock provider: complete() returns whatever verdict we seed."""
    name = "mock"
    def __init__(self, verdict: str):
        self._verdict = verdict
        self.calls = []
    def complete(self, prompt, *, system="", model_tier="mid"):
        self.calls.append((prompt, model_tier))
        return self._verdict
    def fanout(self, tasks, *, model_tier="cheap"):
        return [self.complete(t, model_tier=model_tier) for t in tasks]


def _agent(qid, claim):
    return {"subquestion_id": qid, "sources": [{"id": "S1", "claim": claim}], "signals": {}}


def test_scan_uses_cheap_tier():
    prov = _ScanProvider("NONE")
    cross_agent_contradiction_scan(prov, [_agent("Q1", "x"), _agent("Q2", "y")])
    assert prov.calls and prov.calls[0][1] == "cheap"


def test_scan_no_contradiction_returns_empty():
    prov = _ScanProvider("NONE")  # convention: "NONE" => no contradictions
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "a"), _agent("Q2", "b")])
    assert found == []


def test_scan_reports_contradiction():
    prov = _ScanProvider("CONTRADICTION: Q1 vs Q2 — market size disagree")
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "10B"), _agent("Q2", "2B")])
    assert len(found) == 1
    assert found[0]["trigger"] == "contradiction"
    assert "Q1" in found[0]["detail"] and "Q2" in found[0]["detail"]


def test_scan_skips_when_fewer_than_two_agents():
    prov = _ScanProvider("CONTRADICTION: anything")
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "only one")])
    assert found == []          # nothing to compare against
    assert prov.calls == []     # and we didn't waste a call
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -k scan -v`
Expected: FAIL with `ImportError: cannot import name 'cross_agent_contradiction_scan'`.

- [x] **Step 3: Write minimal implementation**

Append to `runner/adaptive.py`:

```python
def cross_agent_contradiction_scan(provider, agent_outputs: list[dict]) -> list[dict]:
    """Cheap scan over the whole round's pool for cross-agent contradictions.

    Returns a list of synthetic contradiction findings (each a dict with
    trigger="contradiction" + detail). Catches conflicts no single sub-agent can see.
    Convention for the provider's reply: a line starting with "CONTRADICTION:" reports
    one; the literal "NONE" (or no such line) means none found.
    """
    if len(agent_outputs) < 2:
        return []  # nothing to compare; don't spend a call
    summary = "\n".join(
        f"{a.get('subquestion_id', '?')}: " +
        "; ".join(str(s.get("claim", s.get("url", ""))) for s in a.get("sources", []))
        for a in agent_outputs
    )
    prompt = (
        "Below are claims from independent search agents, one line per subquestion.\n"
        "Report any DIRECT contradictions between subquestions. For each, output a line:\n"
        "  CONTRADICTION: <Qa> vs <Qb> — <what conflicts>\n"
        "If there are none, output exactly: NONE\n\n" + summary
    )
    reply = provider.complete(prompt, model_tier="cheap")
    findings = []
    for line in reply.splitlines():
        line = line.strip()
        if line.upper().startswith("CONTRADICTION:"):
            findings.append({"trigger": "contradiction", "detail": line.split(":", 1)[1].strip()})
    return findings
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): cross-agent скан противоречий (дешёвый тир, ловит то, что сабагент не видит)"
```

---

### Task 9: Opus deviation decision (filter + classify)

**Files:**
- Modify: `runner/adaptive.py` (add `decide_deviations`)
- Test: `tests/test_adaptive.py` (append)

**Context:** Given a round's fired triggers (from sub-agent signals + the scan), the
orchestrator (strong/Opus tier) decides which are *justified* and therefore worth a
deviation. To keep this deterministic and testable without a real model, the decision
function is structured so the provider returns a verdict per candidate ("JUSTIFIED" /
"REJECT") at the `strong` tier; `decide_deviations` filters on that. We test with a
mock provider that returns canned verdicts. This is the precision half of the two-tier
detection (sub-agents = recall).

- [x] **Step 1: Write the failing test**

Append to `tests/test_adaptive.py`:

```python
from runner.adaptive import decide_deviations, Candidate


class _VerdictProvider:
    """Mock: returns a verdict string keyed by which trigger appears in the prompt."""
    name = "mock"
    def __init__(self, verdicts: dict[str, str]):
        self.verdicts = verdicts
        self.calls = []
    def complete(self, prompt, *, system="", model_tier="mid"):
        self.calls.append((prompt, model_tier))
        for trig, verdict in self.verdicts.items():
            if trig in prompt:
                return verdict
        return "REJECT"
    def fanout(self, tasks, *, model_tier="cheap"):
        return [self.complete(t) for t in tasks]


def test_decide_uses_strong_tier():
    prov = _VerdictProvider({"empty_result": "JUSTIFIED: reformulate"})
    cands = [Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits")]
    decide_deviations(prov, cands)
    assert prov.calls and prov.calls[0][1] == "strong"


def test_decide_keeps_justified_drops_rejected():
    prov = _VerdictProvider({
        "empty_result": "JUSTIFIED: add fallback channel",
        "unexpected_finding": "REJECT: already covered by the plan",
    })
    cands = [
        Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits"),
        Candidate(subquestion="Q2", trigger="unexpected_finding", detail="tangent"),
    ]
    kept = decide_deviations(prov, cands)
    assert len(kept) == 1
    assert kept[0].trigger == "empty_result"
    assert kept[0].rationale  # the JUSTIFIED reason is captured


def test_decide_empty_candidates_returns_empty():
    prov = _VerdictProvider({})
    assert decide_deviations(prov, []) == []
    assert prov.calls == []  # no candidates -> no model calls
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -k decide -v`
Expected: FAIL with `ImportError: cannot import name 'decide_deviations'`.

- [x] **Step 3: Write minimal implementation**

Append to `runner/adaptive.py`:

```python
@dataclass
class Candidate:
    """A fired trigger awaiting the orchestrator's justification verdict."""
    subquestion: str
    trigger: str
    detail: str
    rationale: str = ""   # filled in when justified


def decide_deviations(provider, candidates: list[Candidate]) -> list[Candidate]:
    """Strong-tier (Opus) filter: keep only justified candidates, attach the rationale.

    Provider convention: reply begins with "JUSTIFIED" (keep, the rest is the reason)
    or "REJECT" (drop). Anything not starting with JUSTIFIED is treated as a reject —
    the expensive, scope-changing default is to NOT deviate.
    """
    kept: list[Candidate] = []
    for c in candidates:
        prompt = (
            f"A search agent flagged a `{c.trigger}` signal on subquestion "
            f"{c.subquestion}: {c.detail}\n"
            "Is deviating from the approved plan JUSTIFIED here? Reply with one line:\n"
            "  JUSTIFIED: <why>   — if the deviation is warranted\n"
            "  REJECT: <why>      — if the plan already covers it or it's a tangent"
        )
        reply = provider.complete(prompt, model_tier="strong").strip()
        if reply.upper().startswith("JUSTIFIED"):
            _, _, reason = reply.partition(":")
            c.rationale = reason.strip() or "justified by orchestrator"
            kept.append(c)
    return kept
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): Opus-решение об отклонении (фильтр justified/reject + классификация)"
```

---

### Task 10: The round loop (`run_search_loop`) with termination

**Files:**
- Modify: `runner/adaptive.py` (add `run_search_loop`)
- Test: `tests/test_adaptive.py` (append)

> **Implementation note (post-review):** a `RoundResult` dataclass was originally listed
> here, but code review found it was never consumed (the loop returns `(deviations, int)`),
> so it was dropped as dead code rather than shipped unused. If a later phase needs a
> per-round record type, reintroduce it *with a consumer*.

**Context:** This is the driver. It ties together: run a round (delegated via an
injected `run_round` callable so tests don't need real search), parse signals, run the
contradiction scan, build candidates, decide (Opus filter), then for each justified
candidate spend budget + record a `Deviation` and spawn the next round — until a
termination condition. Termination: no justified trigger, OR no budget for any
justified candidate's class, OR depth limit reached. **A bounded loop must provably
terminate** — every path decrements budget or hits the depth cap.

`run_round(round_index, depth, directives)` is injected: it returns a list of
sub-agent output dicts (each with `subquestion_id`/`sources`/`signals`). In production
the orchestrator passes a closure over `provider.fanout`; in tests we pass a fake that
returns scripted rounds.

- [x] **Step 1: Write the failing test**

Append to `tests/test_adaptive.py`:

```python
from runner.adaptive import run_search_loop


class _LoopProvider:
    """Mock provider for the loop: scan says NONE; decisions all JUSTIFIED."""
    name = "mock"
    def complete(self, prompt, *, system="", model_tier="mid"):
        if "CONTRADICTION:" in prompt:   # this is the scan prompt
            return "NONE"
        return "JUSTIFIED: go"           # this is a decision prompt
    def fanout(self, tasks, *, model_tier="cheap"):
        return ["" for _ in tasks]


def _round_factory(scripts):
    """scripts: list of per-round agent-output lists. Extra rounds -> no signals."""
    def run_round(round_index, depth, directives):
        idx = round_index - 1
        return scripts[idx] if idx < len(scripts) else [{"subquestion_id": "Qx", "sources": [], "signals": {}}]
    return run_round


def _sig(trigger):
    return {"subquestion_id": "Q1", "sources": [],
            "signals": {trigger: {"fired": True, "detail": "d"}}}


def test_loop_calm_run_exits_after_one_round(tmp_path):
    # round 1 fires nothing -> one round, no deviations, loop exits
    run_round = _round_factory([[{"subquestion_id": "Q1", "sources": [], "signals": {}}]])
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds == 1
    assert devs == []


def test_loop_cheap_trigger_spawns_one_more_round(tmp_path):
    # round 1 fires empty_result (cheap); round 2 fires nothing -> 2 rounds, 1 pursued
    run_round = _round_factory([[_sig("empty_result")], [{"subquestion_id": "Q1", "sources": [], "signals": {}}]])
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds == 2
    assert len(devs) == 1 and devs[0].status == "pursued" and devs[0].trigger == "empty_result"


def test_loop_shallow_expensive_is_not_pursued():
    # shallow expensive budget = 0; an unexpected_finding must be recorded not_pursued
    run_round = _round_factory([[_sig("unexpected_finding")]])
    devs, rounds = run_search_loop(_LoopProvider(), "shallow", run_round)
    assert rounds == 1  # no spawn (budget 0)
    assert len(devs) == 1 and devs[0].status == "not_pursued"
    assert devs[0].carry_forward  # routed to refresh


def test_loop_respects_depth_limit():
    # every round fires a cheap trigger; deep depth_limit=2 caps the nesting
    run_round = _round_factory([[_sig("empty_result")]] * 10)  # always fires
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    # Round 1 (depth0) -> spawn R2 (depth1) -> spawn R3 (depth2) -> depth_ok(2)=False, stop
    assert rounds == 3
    pursued = [d for d in devs if d.status == "pursued"]
    assert len(pursued) == 2  # two spawns allowed before the cap


def test_loop_terminates_when_cheap_budget_drained():
    # deep cheap budget = 8; force many cheap triggers but depth allows only 2 anyway,
    # so verify the loop never exceeds min(budget, depth-bounded spawns) and stops.
    run_round = _round_factory([[_sig("empty_result")]] * 50)
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds <= 3  # depth cap bites first; loop provably stops
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -k loop -v`
Expected: FAIL with `ImportError: cannot import name 'run_search_loop'`.

- [x] **Step 3: Write minimal implementation**

Append to `runner/adaptive.py`:

```python
def run_search_loop(provider, depth: str, run_round) -> tuple[list[Deviation], int]:
    """Drive Phase 4 as a loop. Returns (deviations, total_rounds_run).

    `run_round(round_index, depth, directives)` runs one search round and returns a
    list of sub-agent output dicts. Termination is guaranteed: each spawned round either
    spends budget or is blocked by the depth limit; with no justified trigger the loop
    exits immediately.
    """
    budget = Budget.for_depth(depth)
    deviations: list[Deviation] = []
    round_index = 1
    current_depth = 0

    while True:
        outputs = run_round(round_index, current_depth, directives=None)

        # collect fired triggers from sub-agent signals (recall)
        candidates: list[Candidate] = []
        for blob in outputs:
            fired, details = parse_signals(blob)
            qid = blob.get("subquestion_id", "?")
            for trig in fired:
                candidates.append(Candidate(subquestion=qid, trigger=trig, detail=details.get(trig, "")))

        # cross-agent contradictions the sub-agents can't see
        for f in cross_agent_contradiction_scan(provider, outputs):
            candidates.append(Candidate(subquestion="(cross-agent)", trigger="contradiction", detail=f["detail"]))

        if not candidates:
            break  # nothing flagged -> done

        # Opus precision filter
        justified = decide_deviations(provider, candidates)
        if not justified:
            break  # flags existed but none survived judgment -> done

        spawned = False
        for c in justified:
            klass = class_of(c.trigger)
            ba = {"cheap": budget.cheap, "expensive": budget.expensive}
            can = budget.can_spend(klass) and budget.depth_ok(current_depth)
            if can:
                budget.spend(klass)
                ba = {"cheap": budget.cheap, "expensive": budget.expensive}
                next_round = round_index + 1
                deviations.append(Deviation(
                    subquestion=c.subquestion, round_from=round_index, round_to=next_round,
                    trigger=c.trigger, klass=klass, status="pursued", rationale=c.rationale,
                    action=f"launched round {next_round}", depth=current_depth + 1,
                    budget_after=ba, outcome="(pending scoring)", new_source_ids=[]))
                spawned = True
            else:
                reason = "depth_limit" if not budget.depth_ok(current_depth) else "budget_exhausted"
                deviations.append(Deviation(
                    subquestion=c.subquestion, round_from=round_index, round_to=None,
                    trigger=c.trigger, klass=klass, status="not_pursued",
                    rationale=f"{c.rationale or 'justified'} (not pursued: {reason})",
                    action=None, depth=None, budget_after=ba, outcome=None,
                    new_source_ids=[], carry_forward="Phase 7 refresh-target"))

        if not spawned:
            break  # every justified candidate was blocked -> done (records kept)
        round_index += 1
        current_depth += 1

    return deviations, round_index
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive.py -v`
Expected: PASS (all adaptive unit tests, including the termination/depth tests).

- [x] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/adaptive.py tests/test_adaptive.py
git commit -m "feat(adaptive): цикл раундов run_search_loop с гарантированной терминацией (бюджет/depth)"
```

---

### Task 11: Wire the loop into `Orchestrator.search()` + integration test

**Files:**
- Modify: `runner/orchestrator.py` (`RunState` gains `deviations`; `search()` runs the loop and writes `deviations.md`)
- Test: `tests/test_adaptive_integration.py` (create)

**Context:** The scaffold `search()` does a one-shot fan-out and discards results. Wire
it to `run_search_loop` with a `run_round` closure over `provider.fanout`, then write
`deviations.md` into the run dir. Because real retrieval is out of scope, `run_round`
still produces placeholder sources; the point is that the *loop machinery* runs end-to-
end on DryRun and the artifact appears. Keep the existing scaffold source-writing so
`eval/validate_structure.py` stays green.

- [x] **Step 1: Write the failing integration test**

Create `tests/test_adaptive_integration.py`:

```python
import pytest
from pathlib import Path
from runner.orchestrator import Orchestrator
from runner.providers import DryRunProvider


def test_orchestrator_writes_deviations_file(tmp_path):
    orch = Orchestrator(DryRunProvider())
    run_dir = orch.run("Is approach X better than Y?", "medium", tmp_path)
    dev = run_dir / "deviations.md"
    assert dev.exists(), "search() must write deviations.md"
    assert "# Deviations —" in dev.read_text(encoding="utf-8")


def test_orchestrator_run_still_validates_structure(tmp_path):
    # the existing scaffold contract: plan.md, sources/, a report all still produced
    orch = Orchestrator(DryRunProvider())
    run_dir = orch.run("How does X work?", "shallow", tmp_path)
    assert (run_dir / "plan.md").exists()
    assert (run_dir / "sources").is_dir()
    assert list(run_dir.glob("*_*.md"))  # the dated report


@pytest.mark.live
def test_live_loop_smoke(tmp_path):
    """Opt-in (-m live): a real provider run that exercises the loop end-to-end.
    Skipped by default; needs ANTHROPIC_API_KEY. Not required for CI to pass."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("no ANTHROPIC_API_KEY")
    from runner.providers import build_provider
    orch = Orchestrator(build_provider("claude"))
    run_dir = orch.run("What caused the 2023 SVB collapse?", "shallow", tmp_path)
    assert (run_dir / "deviations.md").exists()
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive_integration.py -v`
Expected: FAIL on `test_orchestrator_writes_deviations_file` — `deviations.md` does not exist yet (the live test is skipped).

- [x] **Step 3: Wire the loop into `search()`**

In `runner/orchestrator.py`:

(a) Add the import near the top (after the providers import block):

```python
try:
    from .adaptive import run_search_loop, write_deviations
except ImportError:  # run as a script
    from adaptive import run_search_loop, write_deviations
```

(b) Add a field to `RunState` (in the dataclass body, alongside `sources`):

```python
    deviations: list = field(default_factory=list)
```

(c) Replace the body of `search()` with a version that runs the loop, then keeps the
existing placeholder source-writing. Replace:

```python
    def search(self, s: RunState) -> None:
        n = DEPTH_SOURCES[s.depth]
        k = DEPTH_FANOUT[s.depth]
        tasks = [f"Search subtopic {i} for: {s.question}" for i in range(max(1, k))]
        self.p.fanout(tasks, model_tier="cheap")  # results discarded in scaffold
        srcdir = s.dir / "sources"
```

with:

```python
    def search(self, s: RunState) -> None:
        n = DEPTH_SOURCES[s.depth]
        k = DEPTH_FANOUT[s.depth]

        def run_round(round_index, depth, directives):
            # scaffold: fan out, return placeholder agent outputs with empty signals.
            # Real retrieval + real signals are downstream work; the loop machinery is
            # what we exercise here. Round 1 carries the planned fan-out.
            tasks = [f"[r{round_index}] Search subtopic {i} for: {s.question}"
                     for i in range(max(1, k))]
            self.p.fanout(tasks, model_tier="cheap")
            return [{"subquestion_id": f"Q{i}", "sources": [], "signals": {}}
                    for i in range(max(1, k))]

        deviations, _rounds = run_search_loop(self.p, s.depth, run_round)
        s.deviations = deviations
        write_deviations(s.dir, s.slug, deviations)

        srcdir = s.dir / "sources"
```

(The rest of `search()` — the `for i in range(1, n + 1)` source-writing and the
`sources.csv` block — stays exactly as is.)

- [x] **Step 4: Run the integration test + the full suite**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest tests/test_adaptive_integration.py tests/test_adaptive.py -v`
Expected: PASS (live test shows as SKIPPED).

- [x] **Step 5: Run the entire test suite to confirm nothing regressed**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest -v && python3 eval/validate_structure.py --help >/dev/null 2>&1; echo "exit: $?"`
Expected: all PASS (live SKIPPED). Then verify a real scaffold run still validates:

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 runner/orchestrator.py "test question" --depth medium --provider dryrun --out /tmp/ic_run && python3 eval/validate_structure.py --research-dir /tmp/ic_run/test-question --strict; echo "validate exit: $?"`
Expected: the run writes, validation exits 0, and `/tmp/ic_run/test-question/deviations.md` exists.

- [x] **Step 6: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add runner/orchestrator.py tests/test_adaptive_integration.py
git commit -m "feat(adaptive): встроить цикл в Orchestrator.search() + интеграционный тест (DryRun + live-smoke)"
```

---

## Final Verification

After all tasks, run the complete gate to confirm Layers A and B are consistent:

- [x] **Full test suite green (live skipped):**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 -m pytest -v`
Expected: all PASS, `test_live_loop_smoke` SKIPPED.

- [x] **Doc gate green (phase count unchanged at 9):**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 scripts/stamp_docs.py --check`
Expected: exit 0.

- [x] **Scaffold run still validates structurally and emits the new artifact:**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python3 runner/orchestrator.py "does X cause Y?" --depth deep --provider dryrun --out /tmp/ic_final && python3 eval/validate_structure.py --research-dir /tmp/ic_final/does-x-cause-y --strict && ls /tmp/ic_final/does-x-cause-y/deviations.md`
Expected: validation exit 0, `deviations.md` listed.

- [x] **Spec coverage confirmed:** every spec section maps to a task (see the plan's self-review notes). No open placeholders remain.
