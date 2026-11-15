"""Binary judge checks: the prompt, the parser and the scorecard must agree.

0-5 judges on the same sqlite text disagreed by a point on adversarial_honesty
(re-judge of 2026-11-07), so each axis is now a share of yes/no checks.
"""

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("score_run", ROOT / "eval" / "score_run.py")
sr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sr)

PROMPT = (ROOT / "eval" / "judge_prompt.md").read_text(encoding="utf-8")


def example() -> dict:
    return json.loads(re.search(r"```json\n(.*?)```", PROMPT, re.S).group(1))


def judge(verdicts=("supported",) * 4, fail=(), readout=True) -> dict:
    j = example()
    j["theses"] = [{"thesis": f"t{i}", "verdict": v, "why": ""} for i, v in enumerate(verdicts)]
    for axis in sr.CHECKS:
        for cid in fail:
            if cid in j[axis]:
                j[axis][cid]["pass"] = False
    if not readout:
        j["readout_clarity"] = None
    return j


def test_prompt_lists_every_check_the_parser_expects():
    for ids in sr.CHECKS.values():
        for cid in ids:
            assert f"**{cid}**" in PROMPT
    ex = example()
    for axis, ids in sr.CHECKS.items():
        assert tuple(ex[axis]) == ids


def test_axis_is_share_of_passed_checks():
    axes = sr.judge_axes(judge(("supported", "supported", "unsupported", "unverifiable"), fail=("C2", "A1", "A4")))
    assert axes["factual_accuracy"][0] == 0.5
    assert axes["coverage_depth"] == (0.75, "3/4 checks, failed C2")
    assert axes["adversarial_honesty"][0] == 0.6
    assert axes["readout_clarity"][0] == 1.0


def test_missing_readout_is_na_not_zero():
    assert sr.judge_axes(judge(readout=False))["readout_clarity"] == (None, "n/a")


@pytest.mark.parametrize(
    "break_it",
    [
        lambda j: j["coverage_depth"].pop("C3"),
        lambda j: j["adversarial_honesty"]["A2"].update(passed=True) or j["adversarial_honesty"]["A2"].pop("pass"),
        lambda j: j["adversarial_honesty"]["A2"].update({"pass": "yes"}),
        lambda j: j["theses"][0].update(verdict="mostly"),
        lambda j: j.update(theses=[]),
        lambda j: j.pop("coverage_depth"),
    ],
)
def test_malformed_judge_output_is_rejected(break_it):
    j = copy.deepcopy(judge())
    break_it(j)
    with pytest.raises(ValueError):
        sr.judge_axes(j)


def test_failed_checks_lower_the_quality_score():
    def quality(j):
        _, m = sr.build_scorecard(
            "t", Path("."), sr.load_weights(), {"citation_integrity": 1.0}, 0.9, "x", 500, None, j
        )
        return m["quality"]

    all_ids = [cid for ids in sr.CHECKS.values() for cid in ids]
    assert quality(judge(("unsupported",) * 4, fail=all_ids)) < quality(judge()) - 0.4
