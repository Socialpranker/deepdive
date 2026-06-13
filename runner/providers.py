#!/usr/bin/env python3
"""
LLM provider interface for the model-agnostic runner (SCAFFOLD).

One interface, swappable backends. The methodology never references a model name —
it asks for a `model_tier` (strong/mid/cheap) and the provider maps it. That mapping
is the only thing that changes between Claude, OpenAI, and a local model.

Only DryRunProvider is implemented (no network) so the pipeline is testable today.
The real adapters are stubs with the integration point marked TODO.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
from typing import Callable, Protocol, runtime_checkable

TIERS = ("strong", "mid", "cheap")

MAX_TOKENS = 4096


def run_parallel(thunks: list[Callable[[], str]], *, limit: int = 5) -> list[str]:
    """Run N thunks concurrently. Result order == input order.
    Any exception propagates (fail-loud)."""
    if not thunks:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(limit, len(thunks))) as ex:
        futures = [ex.submit(fn) for fn in thunks]
        return [f.result() for f in futures]


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        """Single completion at the given tier."""
        ...

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        """Run N independent tasks (the Phase-4 search fan-out)."""
        ...


class DryRunProvider:
    """Deterministic, no-network provider. Produces stable placeholder text so the
    orchestrator can run end-to-end in CI and the output validates structurally."""

    name = "dryrun"

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        assert model_tier in TIERS, f"unknown tier {model_tier}"
        h = hashlib.sha1((system + prompt).encode()).hexdigest()[:8]
        first_line = next(iter(prompt.strip().splitlines()), "")
        return f"[dryrun:{model_tier}:{h}] " + first_line[:80]

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        # local thread pool mirrors real sub-agent parallelism without any model
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(tasks) or 1)) as ex:
            return list(ex.map(lambda t: self.complete(t, model_tier=model_tier), tasks))


class ClaudeProvider:
    """Adapter for Claude via the anthropic SDK. fanout = N parallel complete()
    calls (ThreadPoolExecutor); complete() maps tiers to Opus/Sonnet/Haiku."""

    name = "claude"
    TIER_MODEL = {"strong": "claude-opus-4-8", "mid": "claude-sonnet-4-6", "cheap": "claude-haiku-4-5"}

    def __init__(self, client=None, *, model_override: str | None = None, max_concurrency: int = 5):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.client = client
        self.model_override = model_override
        self.max_concurrency = max_concurrency

    def _model_for(self, tier: str) -> str:
        assert tier in TIERS, f"unknown tier {tier}"
        return self.model_override or self.TIER_MODEL[tier]

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        import anthropic
        msg = self.client.messages.create(
            model=self._model_for(model_tier),
            max_tokens=MAX_TOKENS,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if b.type == "text")

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        raise NotImplementedError("TODO Task 3")


class OpenAIProvider:
    """Adapter for OpenAI-style APIs. fanout() falls back to a thread pool of
    complete() calls — the methodology doesn't require native sub-agents."""

    name = "openai"
    TIER_MODEL = {"strong": "o-series", "mid": "4-class", "cheap": "mini"}

    def __init__(self, client=None):
        self.client = client

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        raise NotImplementedError("TODO: call OpenAI chat API with TIER_MODEL[model_tier]")

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(tasks) or 1)) as ex:
            return list(ex.map(lambda t: self.complete(t, model_tier=model_tier), tasks))


def get_provider(name: str) -> LLMProvider:
    return {"dryrun": DryRunProvider, "claude": ClaudeProvider, "openai": OpenAIProvider}[name]()
