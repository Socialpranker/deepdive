import json
import types

import pytest

from runner.adaptive import TRIGGERS as ADAPTIVE_TRIGGERS
from runner.providers import (
    ClaudeProvider,
    DryRunProvider,
    OpenAICompatProvider,
    SEARCH_TRIGGERS,
    SIGNALS_SCHEMA,
    SCORE_SCHEMA,
)


def _block(**kw):
    # a content block as a simple attribute bag (mimics the SDK's block objects)
    return types.SimpleNamespace(**kw)


def _resp(content, stop_reason="end_turn"):
    return types.SimpleNamespace(content=content, stop_reason=stop_reason)


_UNSUPPORTED_KEYWORDS = {"minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems"}


def _walk_schema_safe(node):
    """Walk a JSON schema node and assert it is Anthropic structured-output safe:
    every object node must have additionalProperties:false, and no unsupported
    keywords (minLength/maxLength/minimum/maximum/minItems/maxItems) appear."""
    if not isinstance(node, dict):
        return
    if node.get("type") == "object":
        assert node.get("additionalProperties") is False, f"missing additionalProperties:false in {node}"
    assert _UNSUPPORTED_KEYWORDS.isdisjoint(node), f"unsupported keyword in {node}"
    for v in node.get("properties", {}).values():
        _walk_schema_safe(v)
    if "items" in node:
        _walk_schema_safe(node["items"])


def test_signals_schema_is_structured_output_safe():
    # Every object in the schema must forbid extra props and use no unsupported
    # keywords (minLength/maxLength/minimum/maximum/minItems) — structured outputs
    # reject those. Walk the schema and assert.
    _walk_schema_safe(SIGNALS_SCHEMA)
    # signals object lists exactly the 4 triggers, all required
    sig = SIGNALS_SCHEMA["properties"]["signals"]
    assert set(sig["properties"]) == set(SEARCH_TRIGGERS)
    assert set(sig["required"]) == set(SEARCH_TRIGGERS)
    # each trigger entry allows null detail
    entry = sig["properties"][SEARCH_TRIGGERS[0]]
    assert entry["properties"]["detail"]["type"] == ["string", "null"]


def test_score_schema_is_structured_output_safe():
    # SCORE_SCHEMA (and its nested _SCORE_ITEM_SCHEMA) must also pass the same
    # structured-output safety checks — the prior guard only covered SIGNALS_SCHEMA.
    _walk_schema_safe(SCORE_SCHEMA)


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


def test_openai_search_not_implemented_yet():
    p = OpenAICompatProvider(client=object())
    with pytest.raises(NotImplementedError):
        p.search("x")


def test_claude_search_model_is_mid_not_cheap():
    # Haiku (cheap) is not in the web_search_20260209 support list; search() must
    # resolve to mid (sonnet) regardless of the tier the orchestrator passes.
    p = ClaudeProvider(client=object())
    assert p._search_model("cheap") == "claude-sonnet-4-6"
    assert p._search_model("strong") == "claude-sonnet-4-6"


def test_claude_search_model_override_wins():
    p = ClaudeProvider(client=object(), model_override="claude-opus-4-8")
    assert p._search_model("cheap") == "claude-opus-4-8"


def test_collect_call1_pulls_text_and_sources():
    from runner.providers import _collect_call1
    resp = _resp([
        _block(type="text", text="Widgets market is ~$5B. "),
        _block(type="web_search_tool_result", content=[
            _block(type="web_search_result", url="https://acme.example/report", title="Acme Report"),
            _block(type="web_search_result", url="https://data.example/widgets", title="Widget Data"),
        ]),
        _block(type="text", text="Growth is 4%/yr."),
    ])
    text, sources = _collect_call1(resp)
    assert text == "Widgets market is ~$5B. Growth is 4%/yr."
    assert sources == [
        {"url": "https://acme.example/report", "title": "Acme Report"},
        {"url": "https://data.example/widgets", "title": "Widget Data"},
    ]


def test_collect_call1_handles_no_search():
    # model answered without searching -> empty sources, still returns text
    from runner.providers import _collect_call1
    resp = _resp([_block(type="text", text="No search needed.")])
    text, sources = _collect_call1(resp)
    assert text == "No search needed."
    assert sources == []


def test_parse_call2_happy_path():
    from runner.providers import _parse_call2
    payload = {
        "sources": [{"id": "s1", "url": "https://x.example", "title": "X", "claim": "c"}],
        "signals": {
            "empty_result": {"fired": False, "detail": None},
            "citation_lead": {"fired": True, "detail": "found a lead"},
            "unexpected_finding": {"fired": False, "detail": None},
            "contradiction": {"fired": False, "detail": None},
        },
    }
    resp = _resp([_block(type="text", text=json.dumps(payload))])
    blob = _parse_call2(resp, "Q2")
    assert blob["subquestion_id"] == "Q2"
    assert blob["sources"] == payload["sources"]
    assert blob["signals"]["citation_lead"] == {"fired": True, "detail": "found a lead"}


def test_parse_call2_failsafe_on_garbage():
    from runner.providers import _parse_call2
    from runner.providers import SEARCH_TRIGGERS
    resp = _resp([_block(type="text", text="I cannot help with that.")], stop_reason="refusal")
    blob = _parse_call2(resp, "Q0")
    assert blob["subquestion_id"] == "Q0"
    assert blob["sources"] == []
    # all triggers present, none fired
    assert set(blob["signals"]) == set(SEARCH_TRIGGERS)
    assert all(v == {"fired": False, "detail": None} for v in blob["signals"].values())


class _FakeClient:
    """Records each messages.create call and returns scripted responses in order."""
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = self  # so client.messages.create works

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _call1_resp():
    return _resp([
        _block(type="text", text="Answer text. "),
        _block(type="web_search_tool_result", content=[
            _block(type="web_search_result", url="https://r.example", title="R"),
        ]),
    ])


def _call2_resp():
    payload = {
        "sources": [{"id": "s1", "url": "https://r.example", "title": "R", "claim": "c"}],
        "signals": {
            "empty_result": {"fired": False, "detail": None},
            "citation_lead": {"fired": True, "detail": "lead"},
            "unexpected_finding": {"fired": False, "detail": None},
            "contradiction": {"fired": False, "detail": None},
        },
    }
    return _resp([_block(type="text", text=json.dumps(payload))])


def test_claude_search_makes_two_calls_with_right_shapes():
    client = _FakeClient([_call1_resp(), _call2_resp()])
    p = ClaudeProvider(client=client)
    blob = p.search("widget market size", subquestion_id="Q4", model_tier="cheap")

    # exactly two create calls
    assert len(client.calls) == 2
    call1, call2 = client.calls

    # call 1: web_search tool, NO output_config; model is sonnet (mid)
    assert call1["model"] == "claude-sonnet-4-6"
    assert call1["tools"][0]["type"] == "web_search_20260209"
    assert "output_config" not in call1

    # call 2: structured output, NO tools
    assert call2["model"] == "claude-sonnet-4-6"
    assert call2["output_config"]["format"]["schema"] == SIGNALS_SCHEMA
    assert "tools" not in call2

    # blob shape + caller-owned subquestion_id
    assert blob["subquestion_id"] == "Q4"
    assert blob["sources"][0]["url"] == "https://r.example"
    assert set(blob["signals"]) == set(SEARCH_TRIGGERS)
    assert blob["signals"]["citation_lead"]["fired"] is True


def test_claude_search_call2_user_text_is_plain_not_tool_blocks():
    # The whole point of two calls: call 2 must NOT carry call-1's
    # web_search_tool_result blocks (citations + format = 400). Its messages
    # must be plain user text only.
    client = _FakeClient([_call1_resp(), _call2_resp()])
    p = ClaudeProvider(client=client)
    p.search("q", subquestion_id="Q0")
    call2 = client.calls[1]
    for msg in call2["messages"]:
        content = msg["content"]
        if isinstance(content, list):
            for block in content:
                assert block.get("type") != "web_search_tool_result"


def test_claude_search_blob_feeds_parse_signals():
    # Prove the returned blob actually mates with the loop's signal reader.
    from runner.adaptive import parse_signals
    client = _FakeClient([_call1_resp(), _call2_resp()])
    blob = ClaudeProvider(client=client).search("q", subquestion_id="Q1")
    fired, details = parse_signals(blob)
    assert "citation_lead" in fired
    assert details["citation_lead"] == "lead"
