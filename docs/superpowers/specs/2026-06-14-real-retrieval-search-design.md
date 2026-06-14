# Real Retrieval — `search()` provider contract for the adaptive loop (Phase 5) — Design

**Date:** 2026-06-14
**Status:** Approved (brainstorm) → ready for implementation plan
**Scope owner:** `runner/providers.py` (new `search()` method), `runner/orchestrator.py` (wire into `run_round`), `tests/` (contract tests). Read-only context: `runner/adaptive.py`, `references/workflow.md`.

## Goal

Give the system the *capability* to do real web search, by introducing a `search()` method on the provider protocol that returns sub-agent output in the exact shape the adaptive loop already consumes (`{subquestion_id, sources, signals}`). After this stage the engine no longer fabricates empty `signals: {}` — it asks the provider, and the provider decides what fired.

This is **Stage 1 of Phase 5**: the contract, the `DryRunProvider` fixture implementation, and the orchestrator wiring. The real `ClaudeProvider.search()` (which calls the Anthropic `web_search` server tool) is **Stage 2** and is explicitly out of scope here — it lands as a single, well-bounded follow-up against this same contract.

The motivating fact: today the whole adaptive loop runs only on placeholders (`orchestrator.py:116-124` returns `signals: {}`; `:134` writes `example.com` URLs), so in production the loop always exits after round 1 because no trigger ever fires. Stage 1 puts the seam in place; Stage 2 lights it up.

## Background: where the code is today

- **`runner/providers.py`** — `LLMProvider` Protocol (`providers.py:35-45`) has two methods: `complete(prompt) -> str` and `fanout(tasks) -> list[str]`. Both are pure LLM text generation; neither passes `tools`, so there is **no web access** today. Three implementations: `DryRunProvider` (deterministic, no-network), `ClaudeProvider` (real `messages.create`), `OpenAICompatProvider`.
- **`runner/orchestrator.py`** — `search()` (`orchestrator.py:112-143`) builds a `run_round` closure (`:116-124`) that calls `self.p.fanout(...)`, **discards the result** (`:122`), and returns hardcoded `[{"subquestion_id": f"Q{i}", "sources": [], "signals": {}}]`. Sources are written as `example.com` placeholders (`:130-143`).
- **`runner/adaptive.py`** — `run_search_loop` (`:230-283`) drives rounds; `parse_signals` (`:27-52`) reads `blob["signals"]` expecting `{trigger: {"fired": bool, "detail": str|None}}`. **The engine is already provider-agnostic** — `tests/test_adaptive.py` constructs `run_round` closures directly with scripted blobs; it never touches a provider's retrieval path.

The seam is therefore clean: Stage 1 changes only *how `orchestrator.search()` builds its `run_round`*, not the loop engine.

## Decisions (from brainstorm)

| Decision | Choice | Why |
|---|---|---|
| Where retrieval lives | `search()` method on the `LLMProvider` protocol | Orchestrator stays ignorant of `web_search`; future backends (Tavily) get their own `search()`. Keeps the existing provider↔orchestrator boundary. |
| One call or two (Stage 2 shape) | **Two calls** per sub-agent: (1) `web_search` *without* `output_config.format` → sources; (2) same content + `format` → `{sources, signals}` | `web_search` always emits citations, and citations + structured outputs in one call return **400** (verified against docs). Two calls is the only way the model both searches and returns strict JSON. |
| Who decides signals | The model (Stage 2), via structured output on call 2 | Matches the methodology's "sub-agents signal generously (recall), Opus filters strictly (precision)". |
| `DryRunProvider.search()` | Deterministic fixture: N fake sources (real fields, `example.com` URL) + all `signals` `fired:false` | Keeps CI green and scaffold byte-stable; loop exits after round 1 exactly as today. Adaptive behaviour is exercised by existing mocks, not by DryRun. |
| `OpenAICompatProvider.search()` | `raise NotImplementedError` | `web_search` is Anthropic-specific; failing loudly beats a silent wrong path. |
| This session's scope | **Stage 1 only**: contract + DryRun + wiring + tests | Small, safe increment. Live `ClaudeProvider.search()` is Stage 2 (needs a live key + smoke). |

## Architecture

### The contract

A third method on the `LLMProvider` Protocol:

```python
def search(self, subquery: str, *, subquestion_id: str = "Q0", model_tier: str = "cheap") -> dict:
    """Run one sub-agent search round for `subquery`. Returns one agent-output blob:
        {"subquestion_id": str,
         "sources": [ {"id": str, "url": str, "title": str, "claim": str, ...}, ... ],
         "signals": {trigger: {"fired": bool, "detail": str | None}}}
    where trigger ∈ ("empty_result", "citation_lead", "unexpected_finding", "contradiction").
    """
```

The return value is **byte-for-byte what `parse_signals` already expects** — no change to `adaptive.py`. `subquestion_id` is threaded in by the caller (orchestrator), not invented by the provider, so the loop can correlate candidates.

### Flow (Stage 1, DryRun)

```
orchestrator.search(s)
  builds run_round(round_index, depth, directives):
      for i in range(max(1, k)):           # k = DEPTH_FANOUT[depth]
          blob = self.p.search(subquery_i, subquestion_id=f"Q{i}", model_tier="cheap")
      return [blob, ...]                    # real shape, real (fixture) sources, fired:false signals
   ↓
run_search_loop(provider, depth, run_round)   # UNCHANGED engine
   parse_signals(blob) → no triggers fire (DryRun) → loop exits after round 1
   ↓
sources written from the blobs' "sources" (no more example.com hardcode in the loop body —
   the URLs still resolve to example.com because DryRun's fixture provides them)
```

### Flow (Stage 2 preview, ClaudeProvider — NOT built this session)

```
ClaudeProvider.search(subquery):
   call 1: messages.create(tools=[{type:"web_search_20260209", name:"web_search"}], NO format)
           → model searches; collect web_search_tool_result blocks → raw sources + answer text
   call 2: messages.create(prior text + sources, output_config.format=SIGNALS_SCHEMA, NO web_search)
           → strict JSON {sources, signals}
   merge → return blob
```

### Component 1 — `DryRunProvider.search()` (the fixture)

Deterministic, no network. For a given `subquery` + `subquestion_id`, returns a stable blob:
- `sources`: a small list (e.g. 2) of `{"id": "s01", "url": "https://example.com/...", "title": ..., "claim": ...}` derived from a hash of the subquery (stable across runs).
- `signals`: every trigger present with `{"fired": False, "detail": None}`.

This reproduces today's "loop exits after round 1" behaviour while flowing through the *real* contract, so the wiring is exercised end-to-end in CI without a key.

### Component 2 — orchestrator wiring

`orchestrator.search()` (`:112-143`) changes so its `run_round` closure calls `self.p.search(...)` per sub-agent and returns the blobs verbatim (instead of `fanout()`-and-discard + hardcoded empty blobs). The source-writing block (`:130-143`) reads `sources` from the collected blobs rather than fabricating `example.com` rows. `DEPTH_SOURCES`/`DEPTH_FANOUT` semantics unchanged.

`fanout()` is **not removed** — it stays on the protocol for any non-search parallel use; this stage simply stops routing Phase-4 search through it.

## Changes to existing files

- **`runner/providers.py`** — add `search()` to the `LLMProvider` Protocol; implement `DryRunProvider.search()` (fixture); add `ClaudeProvider.search()` and `OpenAICompatProvider.search()` as `raise NotImplementedError("…Phase 5 stage 2")`. Consider bumping `MAX_TOKENS` (currently 4096) — deferred to Stage 2 where it matters for web_search.
- **`runner/orchestrator.py`** — rewrite the `run_round` closure and source-writing block in `search()` to use `provider.search()`.
- **`tests/`** — new contract tests (below). No change to `adaptive.py` or its tests.

## Testing strategy

- **`search()` contract (DryRun):** returned blob has the exact keys; all 4 triggers present with `fired:false`; sources non-empty with required fields; output is **deterministic** for a fixed `(subquery, subquestion_id)`.
- **orchestrator integration (DryRun):** a full `Orchestrator.search()` run produces a `deviations.md` and `sources.csv`, the loop exits after round 1 (no triggers), and the run still validates against `eval/validate_structure.py --strict`.
- **NotImplementedError:** `OpenAICompatProvider().search(...)` and `ClaudeProvider().search(...)` raise (Stage-1 guard so the placeholder can't be mistaken for a working path).
- **Regression:** existing `pytest -q` stays green (82 passed / 4 skipped baseline); `scripts/stamp_docs.py --check` exit 0 (no doc-gen spans or phase count touched).

### Edge cases (must be covered)
- `k == 0` (shallow depth, `DEPTH_FANOUT["shallow"]=0`) — `max(1, k)` already guarantees one blob; confirm `search()` is still called once and the run is well-formed.
- Empty/garbage subquery — `search()` returns a valid blob (no crash), signals `fired:false`.

## Explicitly NOT in this design (Stage 2 / later)

- **`ClaudeProvider.search()` real implementation** — the two-call `web_search` flow. Needs a live `ANTHROPIC_API_KEY` and an opt-in `-m live` smoke test. This is the next session.
- **Live signals semantics** — actually firing `empty_result`/`citation_lead`/`unexpected_finding`/`contradiction` from real results. Defined by the schema here, produced in Stage 2.
- **`backfill outcome/new_source_ids`** in `deviations.md` (`adaptive.py:262` TODO) — couples to Phase 5 *Scoring*, not retrieval.
- **Channels/stat-sources from `references/`** into `plan.md` (`orchestrator.py:107`) — separate, not blocking the loop.
- **`MAX_TOKENS` tuning, `pause_turn` handling, `max_uses`** — all Stage-2 concerns of the live `web_search` call.

## Open questions / future work

- Stage 2: exact `SIGNALS_SCHEMA` (json_schema) shape for the structured-output call — drafted then, validated against a live response.
- Stage 2: whether call 1 and call 2 should reuse the same `messages` prefix for prompt-cache benefit, or run independently.
- Whether `DryRunProvider.search()` should *optionally* fire signals by seed (rejected for Stage 1 — would change scaffold output and force `validate_structure` edits; revisit if an end-to-end "loop deviates without a key" demo is wanted).
