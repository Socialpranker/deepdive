import json
import pytest
from runner.scoring import compute_total, render_triangulation, triangulate
from runner.providers import DryRunProvider

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


def test_render_triangulation_has_header_and_row_per_hypothesis():
    rows = [
        {"id": "H1", "distinct_types_supporting": 3, "distinct_types_contradicting": 0,
         "under_triangulated": False, "note": "well supported"},
        {"id": "H2", "distinct_types_supporting": 1, "distinct_types_contradicting": 2,
         "under_triangulated": True, "note": "single voice"},
    ]
    md = render_triangulation("my topic", rows)
    assert "# Triangulation — my topic" in md
    assert "| H1 |" in md and "| H2 |" in md
    assert "⚠️" in md
    assert md.count("⚠️") == 1


def test_render_triangulation_empty_still_has_header():
    md = render_triangulation("topic", [])
    assert "# Triangulation — topic" in md


def test_dryrun_score_returns_deterministic_scores():
    p = DryRunProvider()
    srcs = [{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}]
    out = p.score(srcs, ["H1: a", "H2: b"], model_tier="cheap")
    assert out["sources"][0]["id"] == "s01"
    for axis in ("credibility", "recency", "bias"):
        assert 1 <= out["sources"][0][axis] <= 5
    assert out["sources"][0]["type"] in (
        "Primary", "Academic", "Industry-media", "General-media",
        "Expert-blog", "Forum", "Other")
    assert set(out["sources"][0]["hypothesis_evidence"]) == {"H1", "H2"}

def test_dryrun_score_is_stable_across_calls():
    p = DryRunProvider()
    srcs = [{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}]
    a = p.score(srcs, ["H1: a"], model_tier="cheap")
    b = p.score(srcs, ["H1: a"], model_tier="cheap")
    assert a == b


class _FakeMsg:
    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]

class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.messages = type("M", (), {"create": self._create})()
    def _create(self, **kw):
        return _FakeMsg(json.dumps(self._payload))

def test_claude_score_parses_structured_json():
    from runner.providers import ClaudeProvider
    payload = {"sources": [{"id": "s01", "credibility": 5, "recency": 4, "bias": 3,
                            "type": "Primary", "hypothesis_evidence": {"H1": "supports"}}]}
    p = ClaudeProvider(client=_FakeClient(payload))
    out = p.score([{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}],
                  ["H1: a"], model_tier="cheap")
    assert out["sources"][0]["credibility"] == 5
    assert out["sources"][0]["type"] == "Primary"

@pytest.mark.live
def test_claude_score_live():
    from runner.providers import build_provider
    p = build_provider("claude")
    out = p.score([{"id": "s01", "url": "https://www.bls.gov/", "title": "BLS", "claim": "official labor stats"}],
                  ["H1: official sources are authoritative"], model_tier="cheap")
    s = out["sources"][0]
    assert 1 <= s["credibility"] <= 5
    assert "H1" in s["hypothesis_evidence"]
