from runner.adaptive import parse_signals, TRIGGERS, CHEAP_TRIGGERS, EXPENSIVE_TRIGGERS


def test_trigger_taxonomy_is_fixed():
    assert TRIGGERS == ("empty_result", "citation_lead", "unexpected_finding", "contradiction")
    assert CHEAP_TRIGGERS == ("empty_result", "citation_lead")
    assert EXPENSIVE_TRIGGERS == ("unexpected_finding", "contradiction")


def test_parse_signals_extracts_fired_triggers():
    blob = {
        "signals": {
            "empty_result": {"fired": True, "detail": "0 hits"},
            "citation_lead": {"fired": True, "detail": "S07 cites Gartner"},
            "unexpected_finding": {"fired": False, "detail": None},
            "contradiction": {"fired": False, "detail": None},
        }
    }
    fired, details = parse_signals(blob)
    assert fired == {"empty_result", "citation_lead"}
    assert details["empty_result"] == "0 hits"


def test_parse_signals_missing_block_is_no_flag():
    fired, details = parse_signals({"sources": []})
    assert fired == set()
    assert details == {}


def test_parse_signals_malformed_is_fail_safe():
    # signals present but not a dict, unknown keys, missing 'fired' -> ignored, no crash
    for bad in [{"signals": "oops"}, {"signals": {"weird": {"fired": True}}},
                {"signals": {"empty_result": {"detail": "x"}}}, {"signals": None}]:
        fired, details = parse_signals(bad)
        assert fired == set(), bad


from runner.adaptive import Budget, BUDGET_BY_DEPTH, class_of


def test_budget_by_depth_matches_spec():
    assert BUDGET_BY_DEPTH["shallow"] == (2, 0, 1)
    assert BUDGET_BY_DEPTH["medium"] == (4, 1, 1)
    assert BUDGET_BY_DEPTH["deep"] == (8, 3, 2)


def test_class_of_maps_triggers():
    assert class_of("empty_result") == "cheap"
    assert class_of("citation_lead") == "cheap"
    assert class_of("unexpected_finding") == "expensive"
    assert class_of("contradiction") == "expensive"


def test_budget_for_depth_seeds_counters():
    b = Budget.for_depth("medium")
    assert b.cheap == 4 and b.expensive == 1 and b.depth_limit == 1


def test_budget_spend_decrements_and_floors_at_zero():
    b = Budget.for_depth("deep")  # 8 / 3 / 2
    assert b.can_spend("cheap") is True
    b.spend("cheap")
    assert b.cheap == 7
    # drain expensive to zero
    b.spend("expensive"); b.spend("expensive"); b.spend("expensive")
    assert b.expensive == 0
    assert b.can_spend("expensive") is False
    # spending past zero is a programming error -> raises, never goes negative
    import pytest
    with pytest.raises(ValueError):
        b.spend("expensive")


def test_budget_shallow_has_no_expensive():
    b = Budget.for_depth("shallow")  # 2 / 0 / 1
    assert b.can_spend("expensive") is False
    assert b.can_spend("cheap") is True


def test_budget_depth_limit_gate():
    b = Budget.for_depth("medium")  # depth_limit 1
    assert b.depth_ok(0) is True   # round 1 -> spawning a depth-1 round is allowed
    assert b.depth_ok(1) is False  # at the limit, no further spawn


from runner.adaptive import Deviation, write_deviations


def test_deviation_pursued_record_renders_all_fields():
    d = Deviation(
        subquestion="Q3", round_from=1, round_to=2, trigger="empty_result",
        klass="cheap", status="pursued", rationale="academic empty; added preprint",
        action="round 2 on preprint-servers", depth=1,
        budget_after={"cheap": 3, "expensive": 1},
        outcome="+2 sources", new_source_ids=["S11", "S12"], carry_forward=None,
    )
    md = d.render()
    assert "trigger: empty_result" in md
    assert "status: pursued" in md
    assert "decision_by: orchestrator (opus)" in md  # constant, always Opus
    assert "new_source_ids: [S11, S12]" in md


def test_deviation_not_pursued_has_carry_forward_and_no_action():
    d = Deviation(
        subquestion="Q5", round_from=1, round_to=None, trigger="unexpected_finding",
        klass="expensive", status="not_pursued", rationale="expensive budget exhausted",
        action=None, depth=None, budget_after={"cheap": 5, "expensive": 0},
        outcome=None, new_source_ids=[], carry_forward="Phase 7 refresh-target",
    )
    md = d.render()
    assert "status: not_pursued" in md
    assert "action: none" in md
    assert "carry_forward: Phase 7 refresh-target" in md


def test_write_deviations_creates_file_with_all_records(tmp_path):
    devs = [
        Deviation(subquestion="Q3", round_from=1, round_to=2, trigger="empty_result",
                  klass="cheap", status="pursued", rationale="r", action="a", depth=1,
                  budget_after={"cheap": 3, "expensive": 1}, outcome="+1",
                  new_source_ids=["S11"], carry_forward=None),
        Deviation(subquestion="Q5", round_from=1, round_to=None, trigger="contradiction",
                  klass="expensive", status="not_pursued", rationale="budget out",
                  action=None, depth=None, budget_after={"cheap": 3, "expensive": 0},
                  outcome=None, new_source_ids=[], carry_forward="refresh"),
    ]
    path = write_deviations(tmp_path, "my topic", devs)
    assert path.name == "deviations.md"
    text = path.read_text(encoding="utf-8")
    assert "# Deviations — my topic" in text
    assert "## D1" in text and "## D2" in text
    assert text.count("decision_by: orchestrator (opus)") == 2


def test_write_deviations_empty_list_still_writes_header(tmp_path):
    path = write_deviations(tmp_path, "topic", [])
    assert path.exists()
    assert "# Deviations — topic" in path.read_text(encoding="utf-8")


from runner.adaptive import cross_agent_contradiction_scan


class _ScanProvider:
    """Mock provider: complete() returns whatever verdict we seed."""
    name = "mock"
    def __init__(self, verdict: str):
        self._verdict = verdict
        self.calls = []
    def complete(self, prompt, *, system="", model_tier="mid"):
        self.calls.append((prompt, model_tier))
        return self._verdict
    def fanout(self, tasks, *, model_tier="cheap"):
        return [self.complete(t, model_tier=model_tier) for t in tasks]


def _agent(qid, claim):
    return {"subquestion_id": qid, "sources": [{"id": "S1", "claim": claim}], "signals": {}}


def test_scan_uses_cheap_tier():
    prov = _ScanProvider("NONE")
    cross_agent_contradiction_scan(prov, [_agent("Q1", "x"), _agent("Q2", "y")])
    assert prov.calls and prov.calls[0][1] == "cheap"


def test_scan_no_contradiction_returns_empty():
    prov = _ScanProvider("NONE")  # convention: "NONE" => no contradictions
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "a"), _agent("Q2", "b")])
    assert found == []


def test_scan_reports_contradiction():
    prov = _ScanProvider("CONTRADICTION: Q1 vs Q2 — market size disagree")
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "10B"), _agent("Q2", "2B")])
    assert len(found) == 1
    assert found[0]["trigger"] == "contradiction"
    assert "Q1" in found[0]["detail"] and "Q2" in found[0]["detail"]


def test_scan_skips_when_fewer_than_two_agents():
    prov = _ScanProvider("CONTRADICTION: anything")
    found = cross_agent_contradiction_scan(prov, [_agent("Q1", "only one")])
    assert found == []          # nothing to compare against
    assert prov.calls == []     # and we didn't waste a call


from runner.adaptive import decide_deviations, Candidate


class _VerdictProvider:
    """Mock: returns a verdict string keyed by which trigger appears in the prompt."""
    name = "mock"
    def __init__(self, verdicts: dict[str, str]):
        self.verdicts = verdicts
        self.calls = []
    def complete(self, prompt, *, system="", model_tier="mid"):
        self.calls.append((prompt, model_tier))
        for trig, verdict in self.verdicts.items():
            if trig in prompt:
                return verdict
        return "REJECT"
    def fanout(self, tasks, *, model_tier="cheap"):
        return [self.complete(t) for t in tasks]


def test_decide_uses_strong_tier():
    prov = _VerdictProvider({"empty_result": "JUSTIFIED: reformulate"})
    cands = [Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits")]
    decide_deviations(prov, cands)
    assert prov.calls and prov.calls[0][1] == "strong"


def test_decide_keeps_justified_drops_rejected():
    prov = _VerdictProvider({
        "empty_result": "JUSTIFIED: add fallback channel",
        "unexpected_finding": "REJECT: already covered by the plan",
    })
    cands = [
        Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits"),
        Candidate(subquestion="Q2", trigger="unexpected_finding", detail="tangent"),
    ]
    kept = decide_deviations(prov, cands)
    assert len(kept) == 1
    assert kept[0].trigger == "empty_result"
    assert kept[0].rationale  # the JUSTIFIED reason is captured


def test_decide_empty_candidates_returns_empty():
    prov = _VerdictProvider({})
    assert decide_deviations(prov, []) == []
    assert prov.calls == []  # no candidates -> no model calls


def test_decide_unrecognized_reply_is_dropped():
    prov = _VerdictProvider({"empty_result": "MAYBE: not sure"})
    cands = [Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits")]
    assert decide_deviations(prov, cands) == []   # default-to-reject


def test_decide_justified_without_reason_gets_fallback():
    prov = _VerdictProvider({"empty_result": "JUSTIFIED"})  # no colon, no reason
    cands = [Candidate(subquestion="Q1", trigger="empty_result", detail="0 hits")]
    kept = decide_deviations(prov, cands)
    assert kept[0].rationale == "justified by orchestrator"


from runner.adaptive import run_search_loop


class _LoopProvider:
    """Mock provider for the loop: scan says NONE; decisions all JUSTIFIED."""
    name = "mock"
    def complete(self, prompt, *, system="", model_tier="mid"):
        if "CONTRADICTION:" in prompt:   # this is the scan prompt
            return "NONE"
        return "JUSTIFIED: go"           # this is a decision prompt
    def fanout(self, tasks, *, model_tier="cheap"):
        return ["" for _ in tasks]


def _round_factory(scripts):
    """scripts: list of per-round agent-output lists. Extra rounds -> no signals."""
    def run_round(round_index, depth, directives):
        idx = round_index - 1
        return scripts[idx] if idx < len(scripts) else [{"subquestion_id": "Qx", "sources": [], "signals": {}}]
    return run_round


def _sig(trigger):
    return {"subquestion_id": "Q1", "sources": [],
            "signals": {trigger: {"fired": True, "detail": "d"}}}


def test_loop_calm_run_exits_after_one_round():
    # round 1 fires nothing -> one round, no deviations, loop exits
    run_round = _round_factory([[{"subquestion_id": "Q1", "sources": [], "signals": {}}]])
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds == 1
    assert devs == []


def test_loop_cheap_trigger_spawns_one_more_round():
    # round 1 fires empty_result (cheap); round 2 fires nothing -> 2 rounds, 1 pursued
    run_round = _round_factory([[_sig("empty_result")], [{"subquestion_id": "Q1", "sources": [], "signals": {}}]])
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds == 2
    assert len(devs) == 1 and devs[0].status == "pursued" and devs[0].trigger == "empty_result"


def test_loop_shallow_expensive_is_not_pursued():
    # shallow expensive budget = 0; an unexpected_finding must be recorded not_pursued
    run_round = _round_factory([[_sig("unexpected_finding")]])
    devs, rounds = run_search_loop(_LoopProvider(), "shallow", run_round)
    assert rounds == 1  # no spawn (budget 0)
    assert len(devs) == 1 and devs[0].status == "not_pursued"
    assert devs[0].carry_forward  # routed to refresh


def test_loop_respects_depth_limit():
    # every round fires a cheap trigger; deep depth_limit=2 caps the nesting
    run_round = _round_factory([[_sig("empty_result")]] * 10)  # always fires
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    # Round 1 (depth0) -> spawn R2 (depth1) -> spawn R3 (depth2) -> depth_ok(2)=False, stop
    assert rounds == 3
    pursued = [d for d in devs if d.status == "pursued"]
    assert len(pursued) == 2  # two spawns allowed before the cap
    nots = [d for d in devs if d.status == "not_pursued"]
    assert len(nots) == 1 and "depth_limit" in nots[0].rationale


def test_loop_terminates_when_cheap_budget_drained():
    # deep cheap budget = 8; force many cheap triggers but depth allows only 2 anyway,
    # so verify the loop never exceeds min(budget, depth-bounded spawns) and stops.
    run_round = _round_factory([[_sig("empty_result")]] * 50)
    devs, rounds = run_search_loop(_LoopProvider(), "deep", run_round)
    assert rounds <= 3  # depth cap bites first; loop provably stops


def test_loop_cross_agent_contradiction_becomes_deviation():
    # scan reports a contradiction the sub-agents can't see; it must become a
    # (cross-agent) candidate, survive the Opus filter, and be recorded as a deviation.
    class _ContradictionProvider:
        name = "mock"
        def complete(self, prompt, *, system="", model_tier="mid"):
            if "CONTRADICTION:" in prompt:          # scan prompt
                return "CONTRADICTION: Q1 vs Q2 — figures disagree"
            return "JUSTIFIED: investigate the conflict"   # decision prompt
        def fanout(self, tasks, *, model_tier="cheap"):
            return ["" for _ in tasks]

    # two agents, no per-agent signals -> the only candidate comes from the scan.
    # round 2 onward: the factory's default rows also have 2 agents, but to stop the
    # loop we need a round whose scan finds nothing; give round 2 a provider-independent
    # calm by scripting a single-agent round (scan skipped when <2 agents).
    scripts = [
        [{"subquestion_id": "Q1", "sources": [], "signals": {}},
         {"subquestion_id": "Q2", "sources": [], "signals": {}}],
        [{"subquestion_id": "Q1", "sources": [], "signals": {}}],  # <2 agents -> scan skipped -> calm -> stop
    ]
    run_round = _round_factory(scripts)
    devs, rounds = run_search_loop(_ContradictionProvider(), "deep", run_round)
    cross = [d for d in devs if d.subquestion == "(cross-agent)"]
    assert len(cross) == 1
    assert cross[0].trigger == "contradiction"
    assert cross[0].status == "pursued"


def test_loop_budget_exhausted_midround_is_not_pursued():
    # medium: expensive budget = 1, depth_limit = 1. Two expensive candidates in ONE
    # round: the first spends the single expensive unit (pursued); the second hits
    # can_spend("expensive") == False while depth still allows a spawn -> it must be
    # recorded not_pursued with reason budget_exhausted (NOT depth_limit).
    two_expensive = [
        {"subquestion_id": "Q1", "sources": [],
         "signals": {"unexpected_finding": {"fired": True, "detail": "a"}}},
        {"subquestion_id": "Q2", "sources": [],
         "signals": {"unexpected_finding": {"fired": True, "detail": "b"}}},
    ]
    # round 2 must be calm so the loop stops: single agent, no signals.
    run_round = _round_factory([two_expensive,
                                [{"subquestion_id": "Q1", "sources": [], "signals": {}}]])
    devs, rounds = run_search_loop(_LoopProvider(), "medium", run_round)
    pursued = [d for d in devs if d.status == "pursued"]
    not_pursued = [d for d in devs if d.status == "not_pursued"]
    assert len(pursued) == 1
    assert len(not_pursued) == 1
    assert "budget_exhausted" in not_pursued[0].rationale
    assert not_pursued[0].budget_after["expensive"] == 0
