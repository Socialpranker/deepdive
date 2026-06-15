#!/usr/bin/env python3
"""
LLM provider interface for the model-agnostic runner (SCAFFOLD).

One interface, swappable backends. The methodology never references a model name —
it asks for a `model_tier` (strong/mid/cheap) and the provider maps it. That mapping
is the only thing that changes between Claude, OpenAI, and a local model.

DryRunProvider needs no network (deterministic, for CI). ClaudeProvider and
OpenAICompatProvider call their real SDKs; build_provider resolves provider + keys.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from typing import Callable, Protocol, runtime_checkable

TIERS = ("strong", "mid", "cheap")
SEARCH_TRIGGERS = ("empty_result", "citation_lead", "unexpected_finding", "contradiction")

MAX_TOKENS = 4096

# --- Stage 2: structured-output schema for the web_search signals call ---
# Constraints (Anthropic structured outputs): every object needs
# additionalProperties:false; no min/max length, no minItems, no recursion.
_SIGNAL_SCHEMA = {
    "type": "object",
    "properties": {
        "fired": {"type": "boolean"},
        "detail": {"type": ["string", "null"]},
    },
    "required": ["fired", "detail"],
    "additionalProperties": False,
}
_SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "url": {"type": "string"},
        "title": {"type": "string"},
        "claim": {"type": "string"},
    },
    "required": ["id", "url", "title", "claim"],
    "additionalProperties": False,
}
SIGNALS_SCHEMA = {
    "type": "object",
    "properties": {
        "sources": {"type": "array", "items": _SOURCE_SCHEMA},
        "signals": {
            "type": "object",
            "properties": {t: _SIGNAL_SCHEMA for t in SEARCH_TRIGGERS},
            "required": list(SEARCH_TRIGGERS),
            "additionalProperties": False,
        },
    },
    "required": ["sources", "signals"],
    "additionalProperties": False,
}

SOURCE_TYPES = ("Primary", "Academic", "Industry-media", "General-media",
                "Expert-blog", "Forum", "Other")
STANCES = ("supports", "contradicts", "partial", "neutral")

_SCORE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "credibility": {"type": "integer"},
        "recency": {"type": "integer"},
        "bias": {"type": "integer"},
        "type": {"type": "string", "enum": list(SOURCE_TYPES)},
    },
    "required": ["id", "credibility", "recency", "bias", "type"],
    "additionalProperties": False,
}
SCORE_SCHEMA = {
    "type": "object",
    "properties": {"sources": {"type": "array", "items": _SCORE_ITEM_SCHEMA}},
    "required": ["sources"],
    "additionalProperties": False,
}

_SEARCH_PROMPT = (
    "Search the web to answer this sub-question for a research report. "
    "Cite concrete sources.\n\nSub-question: {subquery}"
)
_SCORE_PROMPT = (
    "Score each source on three axes (integers 1-5) using this rubric:\n"
    "- credibility: 5=peer-reviewed/official/primary, 3=quality edited media, 1=anonymous forum.\n"
    "- recency: 5=current, 1=clearly outdated for the question.\n"
    "- bias: 5=neutral/balanced, 1=strongly partisan or promotional.\n"
    "Classify `type` as one of: Primary, Academic, Industry-media, General-media, "
    "Expert-blog, Forum, Other.\n"
    "For `hypothesis_evidence`, judge each hypothesis id against the source: "
    "supports | contradicts | partial | neutral.\n\n"
    "Hypotheses:\n{hypotheses}\n\nSources:\n{sources}\n"
)
_SIGNALS_PROMPT = (
    "You just researched a sub-question. Return JSON matching the schema: a list "
    "of `sources` (id, url, title, claim) and a `signals` object. For each signal, "
    "set fired=true with a short detail only if it genuinely applies:\n"
    "- empty_result: the search found nothing useful\n"
    "- citation_lead: a source points to another worth chasing\n"
    "- unexpected_finding: a result contradicts the premise or surprises\n"
    "- contradiction: two sources disagree\n\n"
    "Sub-question: {subquery}\n\nYour findings:\n{answer}\n\nSources:\n{sources}"
)


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

    def search(self, subquery: str, *, subquestion_id: str = "Q0", model_tier: str = "cheap") -> dict:
        """One sub-agent search round. Returns an agent-output blob:
            {"subquestion_id": str,
             "sources": [{"id": str, "url": str, "title": str, "claim": str}, ...],
             "signals": {trigger: {"fired": bool, "detail": str | None}}}
        where trigger in ("empty_result", "citation_lead", "unexpected_finding", "contradiction").
        The shape matches what runner.adaptive.parse_signals consumes."""
        ...

    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        """Phase 5 per-source scoring. Returns
            {"sources": [{"id", "credibility", "recency", "bias", "type",
                          "hypothesis_evidence": {Hn: stance}}, ...]}.
        Does NOT compute `total` — that is summed in Python (runner.scoring.compute_total)."""
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

    def search(self, subquery: str, *, subquestion_id: str = "Q0", model_tier: str = "cheap") -> dict:
        assert model_tier in TIERS, f"unknown tier {model_tier}"
        h = hashlib.sha1(subquery.encode()).hexdigest()[:8]
        sources = [
            {"id": f"s{h[:4]}{i}", "url": f"https://example.com/source-{h}-{i}",
             "title": f"Fixture source {i} for {subquery[:40]}",
             "claim": f"(dryrun claim {i})"}
            for i in range(1, 3)
        ]
        signals = {t: {"fired": False, "detail": None} for t in SEARCH_TRIGGERS}
        return {"subquestion_id": subquestion_id, "sources": sources, "signals": signals}

    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        assert model_tier in TIERS, f"unknown tier {model_tier}"
        from runner.scoring import hypothesis_ids
        hids = hypothesis_ids(hypotheses)
        scored = []
        for src in sources:
            h = hashlib.sha1(src["id"].encode()).hexdigest()
            cred = int(h[0], 16) % 5 + 1
            rec = int(h[1], 16) % 5 + 1
            bias = int(h[2], 16) % 5 + 1
            stype = SOURCE_TYPES[int(h[3], 16) % len(SOURCE_TYPES)]
            evidence = {hid: STANCES[int(h[4 + i % 4], 16) % len(STANCES)]
                        for i, hid in enumerate(hids)}
            scored.append({"id": src["id"], "credibility": cred, "recency": rec,
                           "bias": bias, "type": stype, "hypothesis_evidence": evidence})
        return {"sources": scored}


def _empty_signals() -> dict:
    return {t: {"fired": False, "detail": None} for t in SEARCH_TRIGGERS}


def _parse_call2(resp, subquestion_id: str) -> dict:
    """Parse the structured-output call-2 response into a contract blob.

    Fail-safe: malformed JSON, a refusal, or a missing signals block yields a
    valid blob with empty sources and all-fired:false signals — never raises,
    so one bad cheap-model turn can't break the loop (mirrors parse_signals).
    subquestion_id is always the caller's value, never the model's.
    """
    text = "".join(
        getattr(b, "text", "") for b in (getattr(resp, "content", []) or [])
        if getattr(b, "type", None) == "text"
    )
    try:
        data = json.loads(text)
        assert isinstance(data, dict)
    except (ValueError, AssertionError):
        return {"subquestion_id": subquestion_id, "sources": [], "signals": _empty_signals()}

    sources = data.get("sources")
    if not isinstance(sources, list):
        sources = []
    signals = data.get("signals")
    if not isinstance(signals, dict):
        signals = _empty_signals()
    return {"subquestion_id": subquestion_id, "sources": sources, "signals": signals}


def _collect_call1(resp) -> tuple[str, list[dict]]:
    """From a web_search call-1 response, return (answer_text, raw_sources).

    raw_sources are {url, title} dicts harvested from web_search_tool_result
    blocks. Defensive: tolerate blocks missing url/title (skip), and a
    tool-result block whose .content is not a list.
    """
    texts: list[str] = []
    sources: list[dict] = []
    for block in getattr(resp, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "text":
            texts.append(getattr(block, "text", ""))
        elif btype == "web_search_tool_result":
            for item in getattr(block, "content", []) or []:
                url = getattr(item, "url", None)
                if not url:
                    continue
                sources.append({"url": url, "title": getattr(item, "title", "") or ""})
    return "".join(texts), sources


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

    def _search_model(self, tier: str) -> str:
        # web_search_20260209 is documented for opus/sonnet/fable, NOT haiku.
        # The orchestrator passes tier="cheap" (= haiku) for search; override to
        # mid (sonnet) which supports the tool. model_override still wins.
        return self.model_override or self.TIER_MODEL["mid"]

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

    def search(self, subquery: str, *, subquestion_id: str = "Q0", model_tier: str = "cheap") -> dict:
        model = self._search_model(model_tier)

        # --- call 1: web_search, no structured output ---
        messages = [{"role": "user", "content": _SEARCH_PROMPT.format(subquery=subquery)}]
        resp = self.client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )
        # server-side tool loop may pause after N iterations; resume until terminal
        guard = 0
        while getattr(resp, "stop_reason", None) == "pause_turn" and guard < 5:
            guard += 1
            messages = [
                {"role": "user", "content": _SEARCH_PROMPT.format(subquery=subquery)},
                {"role": "assistant", "content": resp.content},
            ]
            resp = self.client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                tools=[{"type": "web_search_20260209", "name": "web_search"}],
                messages=messages,
            )
        answer_text, raw_sources = _collect_call1(resp)

        # --- call 2: structured output, NO web_search (citations + format = 400) ---
        # call-1 sources/text passed as PLAIN user text, never the tool-result blocks.
        rendered_sources = "\n".join(
            f"- {s['title']}: {s['url']}" for s in raw_sources
        ) or "(no sources found)"
        call2_prompt = _SIGNALS_PROMPT.format(
            subquery=subquery, answer=answer_text, sources=rendered_sources
        )
        resp2 = self.client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            output_config={"format": {"type": "json_schema", "schema": SIGNALS_SCHEMA}},
            messages=[{"role": "user", "content": call2_prompt}],
        )
        return _parse_call2(resp2, subquestion_id)

    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        from runner.scoring import hypothesis_ids
        hids = hypothesis_ids(hypotheses)
        ev_props = {hid: {"type": "string", "enum": list(STANCES)} for hid in hids}
        score_item = {
            "type": "object",
            "properties": {
                **_SCORE_ITEM_SCHEMA["properties"],
                "hypothesis_evidence": {
                    "type": "object",
                    "properties": ev_props,
                    "required": hids,
                    "additionalProperties": False,
                },
            },
            "required": [*_SCORE_ITEM_SCHEMA["required"], "hypothesis_evidence"],
            "additionalProperties": False,
        }
        schema = {
            "type": "object",
            "properties": {"sources": {"type": "array", "items": score_item}},
            "required": ["sources"],
            "additionalProperties": False,
        }
        rendered_sources = "\n".join(
            f"- [{s['id']}] {s.get('title', '')}: {s.get('url', '')} — {s.get('claim', '')}"
            for s in sources
        ) or "(no sources)"
        rendered_hyps = "\n".join(f"- {h}" for h in hypotheses) or "(none)"
        prompt = _SCORE_PROMPT.format(hypotheses=rendered_hyps, sources=rendered_sources)
        resp = self.client.messages.create(
            model=self._model_for(model_tier),
            max_tokens=MAX_TOKENS,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return json.loads(text)


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

    def search(self, subquery: str, *, subquestion_id: str = "Q0", model_tier: str = "cheap") -> dict:
        raise NotImplementedError(
            "web_search is Anthropic-specific; OpenAICompatProvider has no search backend")

    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        rendered_sources = "\n".join(
            f"- [{s['id']}] {s.get('title', '')}: {s.get('url', '')} — {s.get('claim', '')}"
            for s in sources
        ) or "(no sources)"
        rendered_hyps = "\n".join(f"- {h}" for h in hypotheses) or "(none)"
        prompt = _SCORE_PROMPT.format(hypotheses=rendered_hyps, sources=rendered_sources)
        resp = self.client.chat.completions.create(
            model=self._model_for(model_tier),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)


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
