from pathlib import Path

from scripts.collect_observations import (
    channel_of,
    collect,
    parse_frontmatter,
    rewarded_sources,
)

RUN = Path(__file__).parent / "fixtures" / "run_mini"


def test_channel_extracted_from_discovery_path():
    assert channel_of({"discovery_path": "academic|запрос|en"}) == "academic"


def test_parse_frontmatter_skips_nested_block():
    text = (
        "---\n"
        "id: s1\n"
        "discovery_path: academic|vertical farming yield|en\n"
        "hypothesis_evidence:\n"
        "  H1: supports\n"
        "  H2: contradicts\n"
        "chain_len: 0\n"
        "---\n"
        "Текст источника.\n"
    )
    fm = parse_frontmatter(text)
    assert fm["id"] == "s1"
    assert fm["discovery_path"] == "academic|vertical farming yield|en"
    assert fm["chain_len"] == "0"
    assert "H1" not in fm
    assert "H2" not in fm


def test_channel_of_missing_discovery_path_is_empty():
    assert channel_of({}) == ""


def test_source_in_sources_is_rewarded():
    rows = [
        {"claim_id": "c1", "sources": "s1", "roots": "study-smith-2024", "dissent": ""}
    ]
    assert "s1" in rewarded_sources(rows)


def test_root_only_match_is_not_rewarded():
    # "s1" здесь совпадает с id источника только случайно, находясь в колонке
    # roots другого claim — roots хранит id корней ("study-smith-2024" и т.п.),
    # а не id источников, поэтому такое совпадение не должно давать награду.
    rows = [{"claim_id": "c9", "sources": "s3", "roots": "s1", "dissent": ""}]
    assert "s1" not in rewarded_sources(rows)


def test_unpaid_dissent_is_rewarded_equally():
    rows = [{"claim_id": "c2", "sources": "s2", "roots": "own", "dissent": "s2"}]
    assert "s2" in rewarded_sources(rows)


def test_collect_marks_used_source_as_win():
    obs = collect(
        RUN,
        "r1",
        requested={"academic": "scientific-claim", "web-general": "market-size"},
    )
    by_channel = {o.channel: o for o in obs}
    assert by_channel["academic"].reward == 1


def test_collect_marks_empty_channel_as_loss():
    obs = collect(
        RUN,
        "r1",
        requested={"academic": "scientific-claim", "forum-discussion": "sentiment"},
    )
    by_channel = {o.channel: o for o in obs}
    assert (
        by_channel["forum-discussion"].reward == 0
    )  # канал отработал впустую — след остаётся


def test_collect_emits_one_observation_per_requested_channel():
    requested = {
        "academic": "scientific-claim",
        "web-general": "market-size",
        "forum-discussion": "sentiment",
    }
    obs = collect(RUN, "r1", requested=requested)
    assert len(obs) == 3


def test_collect_does_not_modify_the_run_directory():
    before = sorted(p.name for p in RUN.rglob("*"))
    collect(RUN, "r1", requested={"academic": "scientific-claim"})
    assert sorted(p.name for p in RUN.rglob("*")) == before
