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
from typing import Protocol, runtime_checkable

TIERS = ("strong", "mid", "cheap")


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
    """Adapter for Claude. fanout() should use real Explore sub-agents; complete()
    maps tiers to Opus/Sonnet/Haiku per references/model_routing.md."""

    name = "claude"
    TIER_MODEL = {"strong": "opus", "mid": "sonnet", "cheap": "haiku"}

    def __init__(self, client=None):
        self.client = client  # anthropic client injected by caller

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        raise NotImplementedError("TODO: call Anthropic API with TIER_MODEL[model_tier]")

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        raise NotImplementedError("TODO: dispatch parallel Explore sub-agents")


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
