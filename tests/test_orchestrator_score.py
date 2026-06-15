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
