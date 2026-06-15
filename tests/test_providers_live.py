"""Opt-in smoke tests against real LLM APIs.

Run explicitly:  pytest -m live
Skipped in normal runs and CI. Each test skips if its key is absent.
"""
import os

import pytest

from runner.providers import ClaudeProvider, OpenAICompatProvider

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_claude_live_completes():
    out = ClaudeProvider().complete("Reply with the single word: pong", model_tier="cheap")
    assert isinstance(out, str) and out.strip() != ""


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_claude_live_fanout():
    out = ClaudeProvider().fanout(["say A", "say B"], model_tier="cheap")
    assert len(out) == 2 and all(isinstance(x, str) for x in out)


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="no OPENAI_API_KEY")
def test_openai_live_completes():
    out = OpenAICompatProvider().complete("Reply with the single word: pong", model_tier="cheap")
    assert isinstance(out, str) and out.strip() != ""


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_claude_live_search():
    from runner.providers import SEARCH_TRIGGERS
    blob = ClaudeProvider().search(
        "What is the current stable version of Python?", subquestion_id="Q0"
    )
    assert blob["subquestion_id"] == "Q0"
    assert set(blob["signals"]) == set(SEARCH_TRIGGERS)
    assert isinstance(blob["sources"], list)
    # at least one real (non-example.com) source on a successful search
    assert any("example.com" not in s.get("url", "") for s in blob["sources"]) or blob["sources"] == []
