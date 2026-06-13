import time
from unittest.mock import MagicMock

import pytest

from runner.providers import ClaudeProvider, run_parallel


def test_run_parallel_preserves_order():
    thunks = [(lambda i=i: f"r{i}") for i in range(5)]
    assert run_parallel(thunks) == ["r0", "r1", "r2", "r3", "r4"]


def test_run_parallel_is_concurrent():
    def slow(i):
        time.sleep(0.2)
        return i
    thunks = [(lambda i=i: slow(i)) for i in range(5)]
    start = time.monotonic()
    out = run_parallel(thunks, limit=5)
    elapsed = time.monotonic() - start
    assert out == [0, 1, 2, 3, 4]
    assert elapsed < 0.8  # parallel ~0.2s (4x headroom); serial would be ~1.0s — still discriminates


def test_run_parallel_fails_loud():
    def boom():
        raise ValueError("boom")
    thunks = [lambda: "ok", boom]
    with pytest.raises(ValueError, match="boom"):
        run_parallel(thunks)


def test_run_parallel_empty():
    assert run_parallel([]) == []


def _text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _claude_response(text):
    resp = MagicMock()
    resp.content = [_text_block(text)]
    return resp


def test_claude_complete_returns_text():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("hello world")
    p = ClaudeProvider(client=client)
    assert p.complete("hi", model_tier="mid") == "hello world"


def test_claude_complete_maps_tier_to_model():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.complete("hi", model_tier="strong")
    assert client.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"
    p.complete("hi", model_tier="cheap")
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"


def test_claude_complete_invalid_tier_raises():
    p = ClaudeProvider(client=MagicMock())
    with pytest.raises(AssertionError):
        p.complete("hi", model_tier="bogus")


def test_claude_complete_joins_multiple_text_blocks():
    resp = MagicMock()
    resp.content = [_text_block("foo"), _text_block("bar")]
    client = MagicMock()
    client.messages.create.return_value = resp
    p = ClaudeProvider(client=client)
    assert p.complete("hi") == "foobar"


def test_claude_complete_model_override_collapses_tiers():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client, model_override="claude-sonnet-4-6")
    p.complete("hi", model_tier="strong")
    assert client.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_claude_complete_empty_system_uses_not_given():
    import anthropic
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.complete("hi")
    assert client.messages.create.call_args.kwargs["system"] is anthropic.NOT_GIVEN


def test_claude_complete_nonempty_system_is_forwarded():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.complete("hi", system="Be terse.")
    assert client.messages.create.call_args.kwargs["system"] == "Be terse."


def test_claude_fanout_runs_each_task_in_order():
    client = MagicMock()
    client.messages.create.side_effect = lambda **kw: _claude_response(
        kw["messages"][0]["content"].upper()
    )
    p = ClaudeProvider(client=client)
    out = p.fanout(["a", "b", "c"], model_tier="cheap")
    assert out == ["A", "B", "C"]


def test_claude_fanout_uses_cheap_tier_by_default():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.fanout(["a"])
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"
