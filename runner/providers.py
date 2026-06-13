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
import os
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
        return run_parallel(
            [lambda t=t: self.complete(t, model_tier=model_tier) for t in tasks],
            limit=self.max_concurrency,
        )


class OpenAICompatProvider:
    """Adapter for any OpenAI-compatible endpoint: OpenAI itself, OpenRouter,
    Ollama, Groq, vLLM, LM Studio. They differ only by base_url + model names."""

    name = "openai"
    TIER_MODEL = {"strong": "gpt-5", "mid": "gpt-4o", "cheap": "gpt-4o-mini"}

    def __init__(self, client=None, *, base_url: str | None = None,
                 model_override: str | None = None, max_concurrency: int = 5):
        if client is None:
            import openai
            client = openai.OpenAI(base_url=base_url)  # reads OPENAI_API_KEY
        self.client = client
        self.base_url = base_url
        self.model_override = model_override
        self.max_concurrency = max_concurrency

    def _model_for(self, tier: str) -> str:
        assert tier in TIERS, f"unknown tier {tier}"
        return self.model_override or self.TIER_MODEL[tier]

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        model = self._model_for(model_tier)
        resp = self.client.chat.completions.create(model=model, messages=messages)
        if not resp.choices:
            raise ValueError(f"OpenAI API returned no choices (model={model})")
        return resp.choices[0].message.content or ""

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        return run_parallel(
            [lambda t=t: self.complete(t, model_tier=model_tier) for t in tasks],
            limit=self.max_concurrency,
        )


def _require_env(name: str) -> None:
    if not os.environ.get(name):
        raise RuntimeError(f"{name} is not set — required for this provider. "
                           f"Export it or use --provider dryrun.")


def build_provider(name: str, *, model: str | None = None, base_url: str | None = None) -> LLMProvider:
    if name == "dryrun":
        return DryRunProvider()
    if name == "claude":
        _require_env("ANTHROPIC_API_KEY")
        return ClaudeProvider(model_override=model)
    if name == "openai":
        _require_env("OPENAI_API_KEY")
        return OpenAICompatProvider(base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
                                    model_override=model)
    raise ValueError(f"unknown provider {name!r} (expected: dryrun|claude|openai)")
