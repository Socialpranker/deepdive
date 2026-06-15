from runner.verify import render_verification, PLACEHOLDER


def test_placeholder_matches_synthesize_string():
    assert PLACEHOLDER == "> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**"


def test_render_none_is_unavailable():
    out = render_verification(None)
    assert "verification unavailable" in out


def test_render_counts_verified_and_red_flags():
    citations = {
        "citation_integrity": 0.8,
        "results": [
            {"sid": "s01", "alive": True, "red_flag": False},
            {"sid": "s02", "alive": True, "red_flag": False},
            {"sid": "s03", "alive": False, "red_flag": True},
        ],
    }
    out = render_verification(citations)
    assert "2/3 verified" in out
    assert "1 red flag" in out
    assert "Citation integrity" in out


def test_render_zero_red_flags_plural():
    citations = {"citation_integrity": 1.0,
                 "results": [{"sid": "s01", "alive": True, "red_flag": False}]}
    out = render_verification(citations)
    assert "1/1 verified" in out
    assert "0 red flags" in out


def test_render_empty_results():
    citations = {"citation_integrity": 0.0, "results": []}
    out = render_verification(citations)
    assert "0/0 verified" in out
