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


def test_score_backfills_pursued_deviation_injected(tmp_path):
    from runner.adaptive import Deviation
    o = Orchestrator(DryRunProvider())
    s = RunState(question="q", depth="medium", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    sid = "sABC"
    s.sources = [{"id": sid, "url": "https://x.example", "title": "T", "claim": "c"}]
    s.round_source_ids = {2: [sid]}
    (s.dir / "sources").mkdir(parents=True, exist_ok=True)
    dev = Deviation(
        subquestion="Q1", round_from=1, round_to=2,
        trigger="empty_result", klass="cheap", status="pursued",
        rationale="test", action="launched round 2",
        depth=1, budget_after={"cheap": 3, "expensive": 1},
        outcome="(pending scoring)", new_source_ids=[],
    )
    s.deviations = [dev]
    o.score(s)
    assert dev.outcome != "(pending scoring)"
    assert sid in dev.new_source_ids
    assert "pending scoring" not in (s.dir / "deviations.md").read_text()


def test_run_invokes_score_phase(tmp_path):
    o = Orchestrator(DryRunProvider())
    out_dir = o.run("does X cause Y", "medium", tmp_path)
    assert (out_dir / "triangulation.md").exists()
    csv = (out_dir / "sources.csv").read_text(encoding="utf-8")
    assert "credibility" in csv.splitlines()[0]
