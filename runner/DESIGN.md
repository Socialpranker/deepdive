# Model-agnostic runner — design (SCAFFOLD, not finished)

## Why this exists

Today the skill is Claude-only in practice. "Works with other LLMs" means *paste the
markdown into the context yourself* — which is not adoption, it's a disclaimer. The
two genuinely Claude-specific pieces are:

1. **Sub-agent fan-out** — Phase 4 launches parallel `Explore` sub-agents.
2. **Source-file management** — the skill relies on the agent writing `sources/NN.md`.

Everything else (the 7-phase methodology, 75 blocks, 29 channels, 280+ sources, the
scoring rubric) is model-agnostic markdown. If a thin runner owns the fan-out and the
file I/O and talks to *any* model through one interface, the skill becomes
infrastructure instead of a Claude add-on. That is the difference between "a skill"
and "something the ecosystem depends on" — which is also the bar the OSS program cares
about.

## Architecture

```
runner/
  orchestrator.py   # drives the 7 phases; owns source-file I/O and fan-out
  providers.py      # LLMProvider protocol + adapters (Claude, OpenAI, local/Ollama)
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
- `fanout` — run N independent search/extract tasks. The Claude adapter uses real
  sub-agents; other adapters fall back to a thread pool of `complete` calls. The
  methodology doesn't care which — that's the whole point.

### Tier mapping (from model_routing.md)

| skill tier | Claude | OpenAI | local |
|---|---|---|---|
| strong (P1/3/6) | Opus | o-series | biggest local |
| mid (synth) | Sonnet | 4-class | mid local |
| cheap (fan-out) | Haiku | mini | small local |

## Status

- `providers.py` — protocol + a `DryRunProvider` (no network, deterministic) so the
  pipeline runs end-to-end in tests today. Real `ClaudeProvider` / `OpenAIProvider`
  are stubbed with the integration point marked `# TODO`.
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
