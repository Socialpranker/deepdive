# Model-agnostic runner — design (SCAFFOLD, not finished)

## Why this exists

Today the skill is Claude-only in practice. "Works with other LLMs" means *paste the
markdown into the context yourself* — which is not adoption, it's a disclaimer. The
two genuinely Claude-specific pieces are:

1. **Sub-agent fan-out** — Phase 4 launches parallel `Explore` sub-agents.
2. **Source-file management** — the skill relies on the agent writing `sources/NN.md`.

Everything else (the <!--gen:count:phases-->9<!--/gen-->-phase methodology, <!--gen:count:blocks-->103<!--/gen--> blocks, <!--gen:count:channels-->29<!--/gen--> channels, <!--gen:count:stat_sources-->460<!--/gen-->+ sources, the
scoring rubric) is model-agnostic markdown. If a thin runner owns the fan-out and the
file I/O and talks to *any* model through one interface, the skill becomes
infrastructure instead of a Claude add-on. That is the difference between "a skill"
and "something the ecosystem depends on" — which is also the bar the OSS program cares
about.

## Architecture

```
runner/
  orchestrator.py   # drives the 9 phases; owns source-file I/O and fan-out
  providers.py      # LLMProvider protocol + adapters (Claude, OpenAI-compat, DryRun) + build_provider
  phases.py         # one function per phase; pure-ish, takes provider + state  (TODO)
  state.py          # RunState: paths, plan, sources, findings                  (TODO)
```

The orchestrator is the only place that knows about parallelism and the filesystem.
Phases receive a `provider` and a `RunState`, return updated state. Swapping models is
swapping one `LLMProvider` instance — no methodology change.

### LLMProvider protocol

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system: str = "", model_tier: str = "default") -> str: ...
    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]: ...
```

- `complete` — single completion. `model_tier` maps to the provider's own model names
  via `references/model_routing.md` semantics (opus/sonnet/haiku → strong/mid/cheap).
- `fanout` — run N independent search/extract tasks. **All** adapters run N parallel
  `complete()` calls via a `ThreadPoolExecutor` (`run_parallel`). The runner is
  standalone — it does NOT depend on Claude Code harness sub-agents. A uniform
  mechanism across providers is the whole point.

### Tier mapping (from model_routing.md)

| skill tier | Claude | OpenAI | local |
|---|---|---|---|
| strong (P1/3/6) | Opus | gpt-5 | biggest local |
| mid (synth) | Sonnet | gpt-4o | mid local |
| cheap (fan-out) | Haiku | gpt-4o-mini | small local |

`OpenAICompatProvider` covers OpenRouter / Ollama / Groq / vLLM / LM Studio through
`--base-url` + `--model` — no separate adapter per backend.

## Status

- `providers.py` — protocol + `DryRunProvider` (no network, deterministic) + the real
  `ClaudeProvider` (anthropic SDK) and `OpenAICompatProvider` (openai SDK; any
  OpenAI-compatible endpoint via `base_url`). `build_provider` resolves provider + keys
  from ENV/CLI with fail-fast. The real adapters are **implemented**, not stubbed.
- `orchestrator.py` — phase loop, source-file I/O, fan-out dispatch, all wired to the
  provider interface. Runs a full dry-run that produces a valid run directory
  (validates clean against `eval/validate_structure.py`).
- `phases.py` / `state.py` — not split out yet; logic currently lives inline in
  `orchestrator.py` to keep the scaffold readable. Split when phases grow.

## What's deliberately NOT here

Real web search, real model calls, retrieval, and the per-phase prompt assembly from
`references/*` are TODO. This scaffold proves the *shape* — that the methodology can be
driven by a provider interface and produce schema-valid output without Claude-specific
calls. Filling the adapters is the next milestone, not this PR.

**Update:** Real model calls are now wired (Claude + OpenAI-compat, this milestone).
Still TODO: real web search / retrieval (source URLs remain placeholders) and the
per-phase prompt assembly from `references/*`.
