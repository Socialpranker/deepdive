"""Scorecard reading must fail loudly, not degrade to an empty cell."""

import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "agg", Path(__file__).resolve().parent.parent / "eval" / "aggregate.py"
)
agg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agg)

GOOD_MD = (
    "- **Citation integrity:** 0.912  (weight 0.25)\n"
    "- **Source diversity:** 0.700\n"
    "- quality_score = 0.831\n"
    "- **quality_per_dollar = 1.204**\n"
)


def test_sidecar_wins_over_markdown(tmp_path):
    md = tmp_path / "A_scorecard.md"
    md.write_text("stale markdown, no numbers\n", encoding="utf-8")
    md.with_suffix(".json").write_text(
        json.dumps(
            {
                "citation": 0.88,
                "diversity": 0.61,
                "quality": 0.79,
                "qpd": None,
                "judge": "scored",
            }
        ),
        encoding="utf-8",
    )
    card = agg.parse_scorecard(md)
    assert card["quality"] == 0.79
    assert card["unparsed"] is False


def test_markdown_fallback_still_parses(tmp_path):
    md = tmp_path / "B_scorecard.md"
    md.write_text(GOOD_MD, encoding="utf-8")
    card = agg.parse_scorecard(md)
    assert card["citation"] == "0.912"
    assert card["unparsed"] is False


def test_changed_markdown_format_is_flagged_not_silently_empty(tmp_path):
    # Control: the regexes must not treat "format drifted" as "not scored yet".
    md = tmp_path / "C_scorecard.md"
    md.write_text("Citation: 0.9 (new layout)\nquality: 0.8\n", encoding="utf-8")
    card = agg.parse_scorecard(md)
    assert card["unparsed"] is True


def test_judge_pending_is_not_broken(tmp_path):
    md = tmp_path / "D_scorecard.md"
    md.write_text(
        "- **Citation integrity:** 0.912  (weight 0.25)\n\n_Pending._\n",
        encoding="utf-8",
    )
    card = agg.parse_scorecard(md)
    assert card["pending_judge"] is True
    assert card["unparsed"] is False
