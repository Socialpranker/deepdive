"""run_search_loop <-> Budget.allocate / SessionBandit wiring (Task 11).

Covers:
  - allocator on (default): free slots get distributed via Thompson sampling,
    the result reaches run_round as `directives`.
  - DEEPDIVE_SWARM=off: static behaviour, candidates taken in order, no allocate().
  - fallback_used is visible from outside the call (swarm_log), never swallowed.
  - SessionBandit powers the in-run view but never touches disk (no priors.json write).
  - backward compat: old 3-positional-arg call site still returns a 2-tuple.
"""

from __future__ import annotations

import random
from pathlib import Path

from runner.adaptive import Budget, run_search_loop
from runner.priors import load_channel_groups
from runner.session_bandit import SessionBandit
from runner.state import Prior

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"
CANDIDATES = ["academic", "web-general", "api-direct"]


def groups():
    return load_channel_groups(FIXTURE)


class _CalmProvider:
    """No contradictions, nothing ever gets justified past round 1 -> loop exits fast."""

    name = "mock"

    def complete(self, prompt, *, system="", model_tier="mid"):
        return "NONE"

    def fanout(self, tasks, *, model_tier="cheap"):
        return ["" for _ in tasks]


def _calm_round_factory(record: list):
    """run_round that records the directives it received and reports no signals."""

    def run_round(round_index, depth, directives):
        record.append(directives)
        return [{"subquestion_id": "Q1", "sources": [], "signals": {}}]

    return run_round


def test_allocator_on_distributes_free_slots_via_directives(monkeypatch):
    monkeypatch.delenv("DEEPDIVE_SWARM", raising=False)  # default = on
    record: list = []
    run_round = _calm_round_factory(record)
    priors = {"academic|pricing": Prior(6.0, 4.0, 10, "t")}

    devs, rounds = run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors=priors,
        groups=groups(),
        rng=random.Random(1),
    )

    assert rounds == 1
    assert devs == []
    assert record[0] is not None
    assert set(record[0]["channels"]).issubset(set(CANDIDATES))
    assert len(record[0]["channels"]) > 0


def test_swarm_off_env_gives_static_uniform_allocation(monkeypatch):
    monkeypatch.setenv("DEEPDIVE_SWARM", "off")
    record: list = []
    run_round = _calm_round_factory(record)

    devs, rounds = run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors={},  # would normally trigger fallback=True if allocate() ran
        groups=groups(),
        rng=random.Random(1),
    )

    assert rounds == 1
    assert record[0]["channels"] == CANDIDATES[: len(record[0]["channels"])]
    assert record[0]["fallback_used"] is False


def test_swarm_off_never_calls_allocate(monkeypatch):
    monkeypatch.setenv("DEEPDIVE_SWARM", "off")
    record: list = []
    run_round = _calm_round_factory(record)

    called = {"n": 0}
    orig_allocate = Budget.allocate

    def spy(self, *a, **kw):
        called["n"] += 1
        return orig_allocate(self, *a, **kw)

    monkeypatch.setattr(Budget, "allocate", spy)

    run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors={},
        groups=groups(),
        rng=random.Random(1),
    )
    assert called["n"] == 0


def test_fallback_used_is_visible_via_swarm_log(monkeypatch):
    monkeypatch.delenv("DEEPDIVE_SWARM", raising=False)
    record: list = []
    run_round = _calm_round_factory(record)
    swarm_log: list = []

    run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors={},  # empty priors -> allocate() must report fallback
        groups=groups(),
        rng=random.Random(1),
        swarm_log=swarm_log,
    )

    assert len(swarm_log) == 1
    assert swarm_log[0]["fallback_used"] is True
    # also visible on the directives handed to run_round, not just the log
    assert record[0]["fallback_used"] is True


def test_populated_priors_report_no_fallback_in_log(monkeypatch):
    monkeypatch.delenv("DEEPDIVE_SWARM", raising=False)
    record: list = []
    run_round = _calm_round_factory(record)
    swarm_log: list = []
    priors = {"academic|pricing": Prior(6.0, 4.0, 10, "t")}

    run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors=priors,
        groups=groups(),
        rng=random.Random(1),
        swarm_log=swarm_log,
    )

    assert swarm_log[0]["fallback_used"] is False


def test_session_bandit_view_feeds_allocate_and_never_writes_priors_json(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("DEEPDIVE_SWARM", raising=False)
    priors_path = tmp_path / "priors.json"
    assert not priors_path.exists()

    bandit = SessionBandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")}, groups())
    # a strong within-run signal for academic, purely in memory
    for _ in range(20):
        bandit.observe("academic", "pricing", passed_filter=True)

    record: list = []
    run_round = _calm_round_factory(record)

    run_search_loop(
        _CalmProvider(),
        "shallow",
        run_round,
        qclass="pricing",
        channel_candidates=CANDIDATES,
        priors={"academic|pricing": Prior(1.0, 1.0, 0, "t")},
        groups=groups(),
        rng=random.Random(1),
        session_bandit=bandit,
    )

    # the bandit accumulated a strong posterior for academic entirely in memory
    assert bandit.view()["academic|pricing"].alpha > 1.0
    # nothing was ever written to disk by the loop or the bandit
    assert not priors_path.exists()
    assert bandit.persisted_delta() == {}


def test_default_call_without_swarm_params_is_unaffected(monkeypatch):
    """Old 3-positional-arg call site (orchestrator.py today) must behave exactly
    as before: no candidates supplied -> no allocation, directives stays None."""
    monkeypatch.delenv("DEEPDIVE_SWARM", raising=False)
    record: list = []
    run_round = _calm_round_factory(record)

    devs, rounds = run_search_loop(_CalmProvider(), "shallow", run_round)

    assert rounds == 1
    assert devs == []
    assert record[0] is None
