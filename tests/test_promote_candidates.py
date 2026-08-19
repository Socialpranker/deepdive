from pathlib import Path

from runner.priors import load_channel_groups
from runner.state import Prior, save_priors
from scripts.promote_candidates import (
    Candidate,
    MIN_WINS,
    MIN_DISTINCT_RUNS,
    eligible_for_promotion,
    eligible_for_demotion,
    main,
    read_candidates,
    write_candidates,
    render_source_file,
    track_candidate,
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


def test_main_without_write_creates_no_files(tmp_path):
    save_priors(STRONG, root=tmp_path)
    write_candidates([c()], root=tmp_path)
    out_root = tmp_path / "out"
    main([], root=tmp_path, output_root=out_root, channels_md=FIXTURE)
    assert not (out_root / "references" / "api_sources" / "promoted").exists()


def test_main_with_write_creates_promoted_file(tmp_path):
    save_priors(STRONG, root=tmp_path)
    write_candidates([c()], root=tmp_path)
    out_root = tmp_path / "out"
    main(["--write"], root=tmp_path, output_root=out_root, channels_md=FIXTURE)
    promoted = out_root / "references" / "api_sources" / "promoted"
    assert promoted.exists()
    assert list(promoted.glob("*.md"))


def test_track_candidate_creates_new_entry_on_first_sighting(tmp_path):
    track_candidate(
        "https://api.new.org/v1", "api-direct", "market-size", "run-a", root=tmp_path
    )
    got = read_candidates(root=tmp_path)
    assert len(got) == 1
    assert got[0].wins == 1
    assert got[0].runs == ["run-a"]


def test_track_candidate_accumulates_wins_across_distinct_runs(tmp_path):
    url = "https://api.new.org/v1"
    for run_id in ("run-a", "run-b", "run-c"):
        track_candidate(url, "api-direct", "market-size", run_id, root=tmp_path)
    got = read_candidates(root=tmp_path)
    assert len(got) == 1  # upsert, не три отдельные строки
    assert got[0].wins == 3
    assert len(set(got[0].runs)) == MIN_DISTINCT_RUNS


def test_track_candidate_same_run_twice_does_not_inflate_distinct_runs(tmp_path):
    url = "https://api.new.org/v1"
    track_candidate(url, "api-direct", "market-size", "run-a", root=tmp_path)
    track_candidate(url, "api-direct", "market-size", "run-a", root=tmp_path)
    got = read_candidates(root=tmp_path)
    assert got[0].wins == 2  # каждая улика считается
    assert got[0].runs == ["run-a"]  # но прогон один — не задваивается


def test_track_candidate_marks_dead_endpoint(tmp_path):
    track_candidate(
        "https://api.new.org/v1",
        "api-direct",
        "market-size",
        "run-a",
        alive=False,
        root=tmp_path,
    )
    got = read_candidates(root=tmp_path)
    assert got[0].alive is False


def test_track_candidate_does_not_touch_other_candidates(tmp_path):
    write_candidates([c(url="https://other.org")], root=tmp_path)
    track_candidate(
        "https://api.new.org/v1", "api-direct", "market-size", "run-a", root=tmp_path
    )
    got = {cand.url for cand in read_candidates(root=tmp_path)}
    assert got == {"https://other.org", "https://api.new.org/v1"}


def test_track_via_cli_flag(tmp_path):
    main(
        [
            "--track",
            "https://api.new.org/v1",
            "--channel",
            "api-direct",
            "--qclass",
            "market-size",
            "--run-id",
            "run-a",
        ],
        root=tmp_path,
    )
    got = read_candidates(root=tmp_path)
    assert len(got) == 1
    assert got[0].wins == 1
