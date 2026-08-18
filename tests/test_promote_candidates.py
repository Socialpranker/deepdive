from pathlib import Path

from runner.priors import load_channel_groups
from runner.state import Prior
from scripts.promote_candidates import (
    Candidate,
    MIN_WINS,
    eligible_for_promotion,
    eligible_for_demotion,
    read_candidates,
    write_candidates,
    render_source_file,
)

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"
STRONG = {"api-direct|market-size": Prior(9.0, 1.0, 10, "t")}


def c(**kw):
    base = dict(
        url="https://api.example.org/v1",
        channel="api-direct",
        qclass="market-size",
        wins=3,
        runs=["r1", "r2", "r3"],
        first_seen="2026-07-01",
        last_probe="2026-08-18",
        alive=True,
    )
    base.update(kw)
    return Candidate(**base)


def test_promotion_requires_wins_across_distinct_runs():
    assert eligible_for_promotion(c(), STRONG, load_channel_groups(FIXTURE))


def test_three_wins_in_one_run_do_not_promote():
    assert not eligible_for_promotion(
        c(runs=["r1", "r1", "r1"]), STRONG, load_channel_groups(FIXTURE)
    )


def test_promotion_requires_live_endpoint():
    assert not eligible_for_promotion(
        c(alive=False), STRONG, load_channel_groups(FIXTURE)
    )


def test_promotion_blocked_when_parent_channel_degraded():
    weak = {"api-direct|market-size": Prior(1.0, 20.0, 21, "t")}
    assert not eligible_for_promotion(c(), weak, load_channel_groups(FIXTURE))


def test_below_min_wins_does_not_promote():
    assert not eligible_for_promotion(
        c(wins=MIN_WINS - 1, runs=["r1", "r2"]), STRONG, load_channel_groups(FIXTURE)
    )


def test_dead_endpoint_after_three_strikes_is_demoted():
    assert eligible_for_demotion(c(alive=False, wins=0, runs=["r1", "r2", "r3"]))


def test_live_endpoint_is_never_demoted():
    assert not eligible_for_demotion(c(alive=True))


def test_candidates_roundtrip(tmp_path):
    write_candidates([c()], root=tmp_path)
    got = read_candidates(root=tmp_path)
    assert got[0].url == "https://api.example.org/v1"


def test_rendered_file_carries_required_frontmatter_keys():
    text = render_source_file(c())
    for key in ("access:", "channel:", "url:"):
        assert key in text
