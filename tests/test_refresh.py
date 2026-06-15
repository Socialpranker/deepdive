from runner.refresh import extract_hypotheses


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


def test_extract_hypotheses_no_triangulation_is_inconclusive():
    out = extract_hypotheses(["H1: a claim"], [])
    assert out[0]["status"] == "inconclusive"
    assert out[0]["supporting_types"] == 0


def test_extract_hypotheses_empty():
    assert extract_hypotheses([], []) == []
