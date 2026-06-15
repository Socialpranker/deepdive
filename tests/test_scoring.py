from runner.scoring import compute_total, triangulate

def test_compute_total_sums_three_axes():
    assert compute_total({"credibility": 5, "recency": 4, "bias": 3}) == 12

def test_compute_total_none_when_axis_missing():
    assert compute_total({"credibility": 5, "recency": 4}) is None

def test_triangulate_flags_under_when_fewer_than_three_distinct_types():
    scored = [
        {"id": "s01", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s02", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
    ]
    result = triangulate(scored, ["H1: claim"])
    h1 = next(h for h in result if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 1
    assert h1["under_triangulated"] is True

def test_triangulate_not_under_with_three_distinct_types():
    scored = [
        {"id": "s01", "type": "Primary", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s02", "type": "Academic", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s03", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
    ]
    h1 = next(h for h in triangulate(scored, ["H1: claim"]) if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 3
    assert h1["under_triangulated"] is False

def test_triangulate_counts_contradicting_separately():
    scored = [
        {"id": "s01", "type": "Primary", "hypothesis_evidence": {"H1": "contradicts"}},
        {"id": "s02", "type": "Academic", "hypothesis_evidence": {"H1": "supports"}},
    ]
    h1 = next(h for h in triangulate(scored, ["H1: claim"]) if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 1
    assert h1["distinct_types_contradicting"] == 1
