from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider


def test_search_records_round_source_ids(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="medium", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    o.search(s)
    assert s.round_source_ids  # non-empty
    all_ids = {x["id"] for x in s.sources}
    for ids in s.round_source_ids.values():
        for sid in ids:
            assert sid in all_ids


def test_score_enriches_sources_and_writes_triangulation(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="medium", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    o.search(s)
    o.score(s)

    csv = (s.dir / "sources.csv").read_text(encoding="utf-8")
    header = csv.splitlines()[0]
    assert header == "id,title,url,type,credibility,recency,bias,total,used"

    md_files = list((s.dir / "sources").glob("*.md"))
    assert md_files
    text = md_files[0].read_text(encoding="utf-8")
    assert "credibility:" in text and "total:" in text and "hypothesis_evidence:" in text

    tri = (s.dir / "triangulation.md").read_text(encoding="utf-8")
    assert tri.startswith("# Triangulation —")

    src0 = s.sources[0]
    assert src0["total"] == src0["credibility"] + src0["recency"] + src0["bias"]


def test_score_backfills_pursued_deviations(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="deep", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    o.search(s)
    o.score(s)

    pursued = [d for d in s.deviations if d.status == "pursued"]
    for d in pursued:
        assert d.outcome != "(pending scoring)"
    text = (s.dir / "deviations.md").read_text(encoding="utf-8")
    assert "(pending scoring)" not in text
