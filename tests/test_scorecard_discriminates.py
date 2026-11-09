"""Negative control for the rubric itself.

A scoring formula that ranks a booster report above a careful one is worse than
no scoring at all. These cases pin the ordering and the citation floor without
touching the network — live URL checks belong to the manual benchmark run.

Inputs mirror the fixtures in eval/questions/_control/, measured 2026-09-20:
strong = citation 1.000 / diversity 0.925, weak = citation 0.500 / diversity 0.475.
"""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "score_run", Path(__file__).resolve().parent.parent / "eval" / "score_run.py"
)
sr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sr)

STRONG = dict(cite={"citation_integrity": 1.0}, diversity=0.925, tokens=548)
WEAK = dict(cite={"citation_integrity": 0.5}, diversity=0.475, tokens=238)
GOOD_JUDGE = {
    "factual_accuracy": 5,
    "coverage_depth": 4,
    "adversarial_honesty": 4,
    "notes": {},
}
BAD_JUDGE = {
    "factual_accuracy": 1,
    "coverage_depth": 1,
    "adversarial_honesty": 0,
    "notes": {},
}
BLIND_JUDGE = {
    "factual_accuracy": 5,
    "coverage_depth": 5,
    "adversarial_honesty": 5,
    "notes": {},
}


def score(fixture: dict, judge: dict) -> float:
    _, metrics = sr.build_scorecard(
        "t",
        Path("."),
        sr.load_weights(),
        fixture["cite"],
        fixture["diversity"],
        "control",
        fixture["tokens"],
        None,
        judge,
    )
    return metrics["quality"]


def test_strong_outscores_weak():
    assert score(STRONG, GOOD_JUDGE) > score(WEAK, BAD_JUDGE)


def test_ordering_survives_a_blind_judge():
    # Worst case: the judge misses everything on the weak report and is harsh on
    # the strong one. The deterministic axes must still keep the ordering.
    assert score(WEAK, BLIND_JUDGE) < score(STRONG, BAD_JUDGE)


def test_citation_floor_halves_the_weak_report():
    w = sr.load_weights()
    assert WEAK["cite"]["citation_integrity"] < w["citation_floor"]
    unfloored = score(
        dict(WEAK, cite={"citation_integrity": w["citation_floor"]}), BAD_JUDGE
    )
    assert score(WEAK, BAD_JUDGE) < unfloored * 0.75
