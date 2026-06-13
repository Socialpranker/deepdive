import time
from unittest.mock import MagicMock

import pytest

from runner.providers import ClaudeProvider, DryRunProvider, OpenAICompatProvider, build_provider, run_parallel


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


def _openai_response(text):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    return resp


def test_openai_complete_returns_text():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("hi there")
    p = OpenAICompatProvider(client=client)
    assert p.complete("q", model_tier="mid") == "hi there"


def test_openai_complete_none_content_becomes_empty():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response(None)
    p = OpenAICompatProvider(client=client)
    assert p.complete("q") == ""


def test_openai_complete_maps_tier_to_model():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q", model_tier="strong")
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-5"


def test_openai_complete_system_prepended():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q", system="be terse")
    msgs = client.chat.completions.create.call_args.kwargs["messages"]
    assert msgs[0] == {"role": "system", "content": "be terse"}
    assert msgs[-1] == {"role": "user", "content": "q"}


def test_openai_complete_no_system_omits_system_message():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q")
    msgs = client.chat.completions.create.call_args.kwargs["messages"]
    assert all(m["role"] != "system" for m in msgs)


def test_openai_fanout_preserves_order():
    client = MagicMock()
    client.chat.completions.create.side_effect = lambda **kw: _openai_response(
        kw["messages"][-1]["content"].upper()
    )
    p = OpenAICompatProvider(client=client)
    assert p.fanout(["a", "b"]) == ["A", "B"]


def test_openai_complete_model_override_collapses_tiers():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client, model_override="gpt-4o")
    p.complete("q", model_tier="strong")
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"


def test_openai_complete_empty_choices_raises():
    client = MagicMock()
    resp = MagicMock()
    resp.choices = []
    client.chat.completions.create.return_value = resp
    p = OpenAICompatProvider(client=client)
    with pytest.raises(ValueError, match="no choices"):
        p.complete("q")


def test_build_provider_dryrun_needs_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(build_provider("dryrun"), DryRunProvider)


def test_build_provider_claude_fails_fast_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        build_provider("claude")


def test_build_provider_openai_fails_fast_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_provider("openai")


def test_build_provider_unknown_raises(monkeypatch):
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider("gpt9000")


def test_build_provider_claude_with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    p = build_provider("claude", model="claude-opus-4-8")
    assert isinstance(p, ClaudeProvider)
    assert p.model_override == "claude-opus-4-8"


def test_build_provider_openai_passes_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = build_provider("openai", base_url="http://localhost:11434/v1")
    assert isinstance(p, OpenAICompatProvider)
    assert p.base_url == "http://localhost:11434/v1"


def test_orchestrator_main_uses_build_provider(monkeypatch, tmp_path):
    import runner.orchestrator as orch
    captured = {}

    def fake_build(name, *, model=None, base_url=None):
        captured["name"] = name
        captured["model"] = model
        captured["base_url"] = base_url
        return DryRunProvider()

    monkeypatch.setattr(orch, "build_provider", fake_build)
    monkeypatch.setattr(
        "sys.argv",
        ["orchestrator", "test q", "--provider", "openai",
         "--model", "gpt-4o", "--base-url", "http://x/v1", "--out", str(tmp_path)],
    )
    orch.main()
    assert captured == {"name": "openai", "model": "gpt-4o", "base_url": "http://x/v1"}
