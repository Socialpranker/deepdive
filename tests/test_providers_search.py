import pytest

from runner.adaptive import TRIGGERS as ADAPTIVE_TRIGGERS
from runner.providers import (
    ClaudeProvider,
    DryRunProvider,
    OpenAICompatProvider,
    SEARCH_TRIGGERS,
    SIGNALS_SCHEMA,
)


def test_signals_schema_is_structured_output_safe():
    # Every object in the schema must forbid extra props and use no unsupported
    # keywords (minLength/maxLength/minimum/maximum/minItems) — structured outputs
    # reject those. Walk the schema and assert.
    UNSUPPORTED = {"minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems"}

    def walk(node):
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, f"missing additionalProperties:false in {node}"
        assert UNSUPPORTED.isdisjoint(node), f"unsupported keyword in {node}"
        for v in node.get("properties", {}).values():
            walk(v)
        if "items" in node:
            walk(node["items"])

    walk(SIGNALS_SCHEMA)
    # signals object lists exactly the 4 triggers, all required
    sig = SIGNALS_SCHEMA["properties"]["signals"]
    assert set(sig["properties"]) == set(SEARCH_TRIGGERS)
    assert set(sig["required"]) == set(SEARCH_TRIGGERS)
    # each trigger entry allows null detail
    entry = sig["properties"][SEARCH_TRIGGERS[0]]
    assert entry["properties"]["detail"]["type"] == ["string", "null"]


def test_search_triggers_match_adaptive_taxonomy():
    # providers.SEARCH_TRIGGERS and adaptive.TRIGGERS are defined independently;
    # pin them together so a Stage-2 edit to one module can't silently desync the
    # DryRun fixture from the loop's signal reader (parse_signals).
    assert SEARCH_TRIGGERS == ADAPTIVE_TRIGGERS


def test_dryrun_search_returns_expected_shape():
    p = DryRunProvider()
    blob = p.search("market size of widgets", subquestion_id="Q3")
    assert blob["subquestion_id"] == "Q3"
    # sources: non-empty, each with required fields
    assert blob["sources"], "expected at least one fixture source"
    for s in blob["sources"]:
        assert set(("id", "url", "title", "claim")) <= set(s)
    # signals: all four triggers present, none fired
    assert set(blob["signals"]) == set(SEARCH_TRIGGERS)
    for trig, entry in blob["signals"].items():
        assert entry == {"fired": False, "detail": None}


def test_dryrun_search_is_deterministic():
    p = DryRunProvider()
    a = p.search("same query", subquestion_id="Q1")
    b = p.search("same query", subquestion_id="Q1")
    assert a == b


def test_dryrun_search_varies_by_subquery():
    p = DryRunProvider()
    a = p.search("query alpha", subquestion_id="Q1")
    b = p.search("query beta", subquestion_id="Q1")
    # different subqueries -> different source ids/urls (hash-derived)
    assert a["sources"] != b["sources"]


def test_claude_search_not_implemented_yet():
    # construct without touching the network: pass a dummy client
    p = ClaudeProvider(client=object())
    with pytest.raises(NotImplementedError):
        p.search("x")


def test_openai_search_not_implemented_yet():
    p = OpenAICompatProvider(client=object())
    with pytest.raises(NotImplementedError):
        p.search("x")
