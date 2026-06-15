from runner.refresh import extract_entities, extract_hypotheses


def test_extract_hypotheses_maps_status():
    hypotheses = ["H1: coffee boosts focus", "H2: tea is calming"]
    triangulation = [
        {"id": "H1", "distinct_types_supporting": 3, "under_triangulated": False,
         "distinct_types_contradicting": 0, "note": ""},
        {"id": "H2", "distinct_types_supporting": 1, "under_triangulated": True,
         "distinct_types_contradicting": 0, "note": ""},
    ]
    out = extract_hypotheses(hypotheses, triangulation)
    assert out[0] == {"id": "H1", "text": "coffee boosts focus",
                      "status": "supported", "supporting_types": 3}
    assert out[1]["status"] == "inconclusive"
    assert out[1]["supporting_types"] == 1


def test_extract_hypotheses_no_triangulation_is_inconclusive():
    out = extract_hypotheses(["H1: a claim"], [])
    assert out[0]["status"] == "inconclusive"
    assert out[0]["supporting_types"] == 0


def test_extract_hypotheses_empty():
    assert extract_hypotheses([], []) == []


def test_extract_entities_dedups_by_domain():
    sources = [
        {"id": "s01", "url": "https://acme.com/pricing", "claim": "Acme raised $5M"},
        {"id": "s02", "url": "https://acme.com/blog/post", "claim": "Acme ships v2"},
        {"id": "s03", "url": "https://beta.io/about", "claim": "Beta is new"},
    ]
    out = extract_entities(sources)
    domains = [e["domain"] for e in out]
    assert domains == ["acme.com", "beta.io"]
    assert out[0]["url"] == "https://acme.com/pricing"  # first wins
    assert out[0]["why"] == "Acme raised $5M"


def test_extract_entities_skips_empty_url():
    out = extract_entities([{"id": "s01", "url": "", "claim": "x"}])
    assert out == []


def test_extract_entities_empty():
    assert extract_entities([]) == []
