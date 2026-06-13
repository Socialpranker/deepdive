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
