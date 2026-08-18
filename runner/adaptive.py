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
import os
import random
from dataclasses import dataclass, field
from pathlib import Path

from runner.qclass import normalize_qclass

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
            log.warning(
                "signals block is not a dict (%r) — treating as no-flag", type(block)
            )
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


# depth -> (cheap_budget, expensive_budget, depth_limit)
BUDGET_BY_DEPTH = {
    "shallow": (2, 0, 1),
    "medium": (4, 1, 1),
    "deep": (8, 3, 2),
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
            raise ValueError(
                f"{klass} budget exhausted — caller must check can_spend first"
            )
        setattr(self, klass, getattr(self, klass) - 1)

    def depth_ok(self, current_depth: int) -> bool:
        """True if a round at current_depth may spawn a (deeper) deviation round."""
        return current_depth < self.depth_limit

    def allocate(
        self, qclass, free_slots, candidates, priors, groups, rng, *, fallback_hint=None
    ):
        """Thompson-sample `free_slots` distinct channels; report whether priors were usable.

        The fallback flag is not decoration: a silently uniform allocator looks
        identical to a working one from outside, and the tests stay green while the
        behaviour is gone. The caller writes the flag into the run report.

        `candidates` here is exclusively the free-eligible pool — the mandatory part
        (primary + secondary of different types, from source_dispatch.md) is spent by
        the caller before this call and never appears in `candidates`; that is what
        keeps triangulation intact and what stops the prior from confirming itself.

        `priors` is what sampling reads from (may be a SessionBandit's live view,
        overlaid with in-run observations). `fallback_hint`, when given, overrides
        the fallback flag instead of deriving it from `priors`: a bandit view seeded
        from an empty base is non-empty by construction (it materializes group/uniform
        defaults on first observe()), so judging fallback off the view would report
        "no fallback" even when the run never had real evidence. Callers that pass a
        bandit view should pass `fallback_hint` computed off the *base* priors instead.
        """
        from runner.priors import (
            effective_prior,
        )  # локальный импорт: не тянет runner.priors/state в модули, использующие
        # adaptive без приоров (например DryRun-тесты)

        if free_slots <= 0 or not candidates:
            return [], False
        fallback = (not priors) if fallback_hint is None else fallback_hint
        if fallback:
            log.warning(
                "priors empty or unreadable — allocating uniform for qclass=%s", qclass
            )
        draws = []
        for ch in candidates:
            p = effective_prior(priors, ch, qclass, groups)
            draws.append((rng.betavariate(p.alpha, p.beta), ch))
        draws.sort(reverse=True)
        return [ch for _, ch in draws[:free_slots]], fallback


@dataclass
class Deviation:
    """One considered trigger (pursued or not_pursued) for the deviations.md log."""

    subquestion: str
    round_from: int
    round_to: int | None  # the round this deviation spawned, or None if not pursued
    trigger: str
    klass: str  # "cheap" | "expensive"
    status: str  # "pursued" | "not_pursued"
    rationale: str
    action: str | None
    depth: int | None
    budget_after: dict[str, int]
    outcome: str | None
    new_source_ids: list[str] = field(default_factory=list)
    carry_forward: str | None = None

    def render(self) -> str:
        round_str = (
            f"{self.round_from}"
            if self.round_to is None
            else f"{self.round_from} → {self.round_to}"
        )
        ids = "[" + ", ".join(self.new_source_ids) + "]"
        ba = "{ cheap: %d, expensive: %d }" % (
            self.budget_after.get("cheap", 0),
            self.budget_after.get("expensive", 0),
        )
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
        f"{a.get('subquestion_id', '?')}: "
        + "; ".join(str(s.get("claim", s.get("url", ""))) for s in a.get("sources", []))
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
            findings.append(
                {"trigger": "contradiction", "detail": line.split(":", 1)[1].strip()}
            )
    return findings


@dataclass
class Candidate:
    """A fired trigger awaiting the orchestrator's justification verdict."""

    subquestion: str
    trigger: str
    detail: str
    rationale: str = ""  # filled in when justified


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


def _allocate_for_round(
    budget: "Budget",
    *,
    swarm_enabled: bool,
    qclass: str,
    channel_candidates: list[str] | None,
    priors: dict | None,
    mandatory_slots: int,
    bandit,
    groups: dict[str, str] | None,
    rng: random.Random,
) -> dict | None:
    """Build this round's `directives` dict, or None when swarm isn't in use.

    Swarm is "in use" only when the caller actually supplied `channel_candidates` —
    the scaffold orchestrator does not yet, so that call site is byte-for-byte
    unaffected (directives stays None, exactly as before this function existed).

    `channel_candidates` is exclusively the free-eligible pool: per commit 0cdb1d8,
    the caller spends the mandatory part (primary + secondary from source_dispatch.md)
    itself and never includes those channels here. `mandatory_slots` is therefore NOT
    used to slice the pool — it is forwarded into `directives` purely as an audit-trail
    count for the run report.

    `free_slots` — how many of the free-eligible candidates actually get drawn — comes
    from the run's own deviation budget (`budget.cheap + budget.expensive`, see
    docs/specs/2026-08-18-bayesian-swarm-design.md §5: "остаток плюс deviation-бюджет"),
    capped at the number of candidates on offer. Using `len(channel_candidates)` alone
    here would make `free_slots` track pool size instead of the run's budget, which is
    the bug this replaced: with a pool the same size as (or smaller than) the budget,
    every candidate would be "selected" and Thompson sampling would only reorder them.

    DEEPDIVE_SWARM=off is the measurement's control-group switch (see
    docs/specs/2026-08-18-bayesian-swarm-measurement.md §1): it takes the candidate
    list in its given order instead of calling Budget.allocate, and fallback_used is
    always False there — this is a deliberate static baseline, not a degraded prior.
    """
    if not channel_candidates:
        return None

    free_slots = min(len(channel_candidates), budget.cheap + budget.expensive)

    if not swarm_enabled:
        return {
            "channels": channel_candidates[:free_slots],
            "fallback_used": False,
            "mandatory_slots": mandatory_slots,
        }

    if bandit is not None:
        # bandit.view() overlays in-run observations on top of its own base priors
        # and always wins over the raw `priors` arg when both are given — `priors`
        # is not read again here once a bandit is supplied.
        view = bandit.view()
    else:
        view = priors or {}
    allocated, fallback_used = budget.allocate(
        qclass,
        free_slots,
        channel_candidates,
        view,
        groups or {},
        rng,
        # fallback must reflect whether *this run* had real evidence, not whether
        # the bandit's view happens to be non-empty: a bandit seeded from an empty
        # base still produces a non-empty view after its first observe() (it
        # materializes group/uniform defaults), which would otherwise silently
        # report fallback_used=False for a run that never had a real prior.
        fallback_hint=not priors,
    )
    return {
        "channels": allocated,
        "fallback_used": fallback_used,
        "mandatory_slots": mandatory_slots,
    }


def run_search_loop(
    provider,
    depth: str,
    run_round,
    *,
    qclass: str = "qualitative",
    channel_candidates: list[str] | None = None,
    priors: dict | None = None,
    groups: dict[str, str] | None = None,
    mandatory_slots: int = 0,
    session_bandit=None,
    rng: random.Random | None = None,
    swarm_log: list[dict] | None = None,
) -> tuple[list[Deviation], int]:
    """Drive Phase 4 as a loop. Returns (deviations, total_rounds_run).

    `run_round(round_index, depth, directives)` runs one search round and returns a
    list of sub-agent output dicts. Termination is guaranteed: each spawned round either
    spends budget or is blocked by the depth limit; with no justified trigger the loop
    exits immediately.

    Swarm allocation (opt-in, additive — see docs/specs/2026-08-18-bayesian-swarm-design.md
    §5-6): when `channel_candidates` is given, it must already be the free-eligible pool
    only — the caller spends the mandatory part (primary + secondary from
    source_dispatch.md) itself and never includes those channels here; this loop never
    sees them and cannot drop them. The number of free candidates actually drawn is
    capped by the run's own deviation budget (`Budget.cheap + Budget.expensive` for the
    depth), not by pool size, and handed to `run_round` as `directives["channels"]` via
    Thompson sampling (`Budget.allocate`). `mandatory_slots` is not used to slice
    anything — it only rides along into `directives`/`swarm_log` as a report count.
    `directives["fallback_used"]` mirrors `Budget.allocate`'s fallback flag so a
    silently-uniform allocator can't hide behind a green test suite; pass `swarm_log`
    to also collect one record per round from the outside.

    The fast in-run signal lives in `session_bandit` (a `SessionBandit`, memory-only,
    never written to `priors.json` — see `runner/session_bandit.py`). Pass one in to
    seed `Budget.allocate`'s view from priors already updated by earlier rounds in this
    same run; omit it to allocate straight off the base `priors`. The slow signal
    (`priors.json` itself) is collected post-hoc by `scripts/collect_observations.py`
    and is out of this loop's scope by design.

    `DEEPDIVE_SWARM=off` disables the allocator and falls back to the previous static
    behaviour (candidates taken in given order) — the control group for
    docs/specs/2026-08-18-bayesian-swarm-measurement.md. Unset (default) means on.
    """
    budget = Budget.for_depth(depth)
    qclass = normalize_qclass(
        qclass
    )  # см. runner/qclass.py — raw input не пропускаем в приоры
    deviations: list[Deviation] = []
    round_index = 1
    current_depth = 0

    swarm_enabled = os.environ.get("DEEPDIVE_SWARM", "on").strip().lower() != "off"
    _rng = rng if rng is not None else random.Random()

    while True:
        directives = _allocate_for_round(
            budget,
            swarm_enabled=swarm_enabled,
            qclass=qclass,
            channel_candidates=channel_candidates,
            priors=priors,
            mandatory_slots=mandatory_slots,
            bandit=session_bandit,
            groups=groups,
            rng=_rng,
        )
        if directives is not None and swarm_log is not None:
            swarm_log.append({"round": round_index, "qclass": qclass, **directives})

        outputs = run_round(round_index, current_depth, directives=directives)

        # collect fired triggers from sub-agent signals (recall)
        trigger_candidates: list[Candidate] = []
        for blob in outputs:
            fired, details = parse_signals(blob)
            qid = blob.get("subquestion_id", "?")
            for trig in fired:
                trigger_candidates.append(
                    Candidate(
                        subquestion=qid, trigger=trig, detail=details.get(trig, "")
                    )
                )

        # cross-agent contradictions the sub-agents can't see
        for f in cross_agent_contradiction_scan(provider, outputs):
            trigger_candidates.append(
                Candidate(
                    subquestion="(cross-agent)",
                    trigger="contradiction",
                    detail=f["detail"],
                )
            )

        if not trigger_candidates:
            break  # nothing flagged -> done

        # Opus precision filter
        justified = decide_deviations(provider, trigger_candidates)
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
                # outcome/new_source_ids are placeholders here; Phase 5
                # (Orchestrator.score) backfills them after scoring lands.
                deviations.append(
                    Deviation(
                        subquestion=c.subquestion,
                        round_from=round_index,
                        round_to=next_round,
                        trigger=c.trigger,
                        klass=klass,
                        status="pursued",
                        rationale=c.rationale,
                        action=f"launched round {next_round}",
                        depth=current_depth + 1,
                        budget_after=ba,
                        outcome="(pending scoring)",
                        new_source_ids=[],
                    )
                )
                spawned = True
            else:
                reason = (
                    "depth_limit"
                    if not budget.depth_ok(current_depth)
                    else "budget_exhausted"
                )
                deviations.append(
                    Deviation(
                        subquestion=c.subquestion,
                        round_from=round_index,
                        round_to=None,
                        trigger=c.trigger,
                        klass=klass,
                        status="not_pursued",
                        rationale=f"{c.rationale or 'justified'} (not pursued: {reason})",
                        action=None,
                        depth=None,
                        budget_after=ba,
                        outcome=None,
                        new_source_ids=[],
                        carry_forward="Phase 7 refresh-target",
                    )
                )

        if not spawned:
            break  # every justified candidate was blocked -> done (records kept)
        round_index += 1
        current_depth += 1

    return deviations, round_index
