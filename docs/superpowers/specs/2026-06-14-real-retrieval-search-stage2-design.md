# Real Retrieval — Stage 2: live `ClaudeProvider.search()` via `web_search` — Design

**Date:** 2026-06-14
**Status:** Approved (brainstorm) → ready for implementation plan
**Scope owner:** `runner/providers.py` (`ClaudeProvider.search()` real implementation, `SIGNALS_SCHEMA`), `tests/test_providers_search.py` (rewrite the Stage-1 `NotImplementedError` guard), `tests/test_providers_live.py` (opt-in `-m live` smoke). Read-only context: `runner/adaptive.py` (`parse_signals`, `TRIGGERS`), `runner/orchestrator.py` (`run_round` call site).
**Builds on:** [Stage 1 design](2026-06-14-real-retrieval-search-design.md) — the `search()` contract, `DryRunProvider` fixture, and orchestrator wiring already shipped. This stage lights up the live path against that same contract.

## Goal

Replace the Stage-1 `NotImplementedError` in `ClaudeProvider.search()` (`providers.py:123`) with a real two-call `web_search` flow that returns a blob in the exact shape `runner.adaptive.parse_signals` consumes. After this stage the adaptive loop can actually fire `empty_result`/`citation_lead`/`unexpected_finding`/`contradiction` from real web results instead of always exiting after round 1.

Out of scope: `OpenAICompatProvider.search()` stays `NotImplementedError` (`web_search` is Anthropic-specific). No change to `adaptive.py`, the loop engine, or the Stage-1 `DryRunProvider` fixture.

## Decisions (from brainstorm 2026-06-14)

These resolve the two open questions left by the Stage-1 design, plus one risk found during context review.

| Decision | Choice | Why |
|---|---|---|
| **Search model** (risk: `cheap`-tier = `claude-haiku-4-5`) | `search()` uses **`mid` = `claude-sonnet-4-6`**, ignoring the `model_tier="cheap"` the orchestrator passes for this call. | The `claude-api` skill docs list dynamic-filtering `web_search_20260209` for Fable 5 / Opus 4.8 / 4.7 / 4.6 / Sonnet 4.6 — **Haiku 4.5 is not in that list**. `cheap` (Haiku) may not support the tool version the whole design rests on; `mid` (Sonnet 4.6) is confirmed supported. Resolved to `mid` in `_model_for`-style logic local to `search()`, not by changing the tier the orchestrator sends. |
| **`SIGNALS_SCHEMA` shape** (call 2 structured output) | Call 2 returns the **whole blob**: `{sources: [{id,url,title,claim}], signals: {<4 triggers>: {fired, detail}}}`. The model normalizes call-1 sources into clean JSON. | One pass; the model already has the sources in context. Avoids a second client-side parse of `web_search_tool_result` citation blocks. |
| **Prompt-cache between call 1 and call 2** | **Independent calls, no shared `messages` prefix, no `cache_control`.** Call 2 receives call-1's answer text + sources as **fresh user-turn text**, not a replay of call-1's `messages` (which contain `web_search_tool_result` blocks). | Simpler and more deterministic to mock. **Also load-bearing for correctness** — see "Why call 2 must not replay call-1 messages" below. Cache optimization deferred. |
| **Testing** | Mock-only this session (a fake `anthropic` client). Live `-m live` smoke is written but **off by default** — the user runs it. | No tokens/network spent in CI or development. |

## Architecture

### The two-call flow

`ClaudeProvider.search(subquery, *, subquestion_id="Q0", model_tier="cheap")`:

```
model = self.model_override or "claude-sonnet-4-6"   # mid; NOT TIER_MODEL["cheap"]

call 1 — SEARCH (no structured output):
    self.client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        messages=[{"role": "user", "content": <search prompt for subquery>}],
    )
    handle stop_reason == "pause_turn": re-send (user msg + assistant content) until terminal
    → collect answer text + raw sources from web_search_tool_result blocks

call 2 — SIGNALS (structured output, NO web_search):
    self.client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        output_config={"format": {"type": "json_schema", "schema": SIGNALS_SCHEMA}},
        messages=[{"role": "user", "content": <call-1 answer text + sources, as plain text>
                                              + <instructions: emit sources + signals JSON>}],
    )
    → strict JSON {sources, signals}

merge: ensure subquestion_id is set on the returned blob (threaded from the caller, not the model)
return {"subquestion_id": subquestion_id, "sources": [...], "signals": {...}}
```

### Why call 2 must NOT replay call-1 messages

`web_search` always emits **citations**, and `output_config.format` (structured outputs) is **incompatible with citations → HTTP 400** (confirmed in the `claude-api` skill docs: *"Structured outputs … Incompatible with: Citations (returns 400 error)"*). The 400 is triggered by citations being present in the same request as `format`.

Call-1's `messages` history contains `web_search_tool_result` blocks (which carry citations). If call 2 naively reused that history as its `messages` prefix (the prompt-cache idea), the citations would ride along and call 2 would 400 even though it declares no `web_search` tool. Therefore call 2 takes the call-1 answer text + sources rendered as **plain user text**, never the raw tool-result blocks. This is why "independent calls" is a correctness decision, not just a simplicity one.

### `SIGNALS_SCHEMA` (json_schema for call 2)

Structured-outputs constraints (from `claude-api` docs): every object needs `additionalProperties: false`; **no** `minLength`/`maxLength`/`minimum`/`maximum`/`minItems`; no recursion. Draft shape:

```python
_SIGNAL = {
    "type": "object",
    "properties": {
        "fired": {"type": "boolean"},
        "detail": {"type": ["string", "null"]},
    },
    "required": ["fired", "detail"],
    "additionalProperties": False,
}
_SOURCE = {
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
        "sources": {"type": "array", "items": _SOURCE},
        "signals": {
            "type": "object",
            "properties": {t: _SIGNAL for t in SEARCH_TRIGGERS},
            "required": list(SEARCH_TRIGGERS),
            "additionalProperties": False,
        },
    },
    "required": ["sources", "signals"],
    "additionalProperties": False,
}
```

Notes:
- `detail` is `["string", "null"]` so the model can return `null` — matches `parse_signals`, which reads `detail` only when it `isinstance(str)` and ignores `None`.
- All 4 triggers are `required`, so call 2 always returns the full signals block — `parse_signals`' fail-safe (empty set on a malformed block) stays a backstop, not the normal path.
- **`minItems` is unavailable**, so the schema cannot guarantee `sources` is non-empty. "Non-empty sources on a successful search" is asserted in tests and (defensively) in code, not by the schema. An empty `sources` is a valid blob (no crash) — consistent with Stage 1's empty/garbage-subquery edge case.

### `subquestion_id` ownership

Threaded in by the caller (orchestrator passes `subquestion_id=f"Q{i}"`), **not** invented by the model. `search()` overwrites whatever the model might put there with the passed `subquestion_id` before returning, so the loop can always correlate candidates.

## Changes to existing files

- **`runner/providers.py`** — replace `ClaudeProvider.search()` body (`:123-125`) with the two-call flow; add module-level `SIGNALS_SCHEMA`. Resolve the search model to `mid` locally. `OpenAICompatProvider.search()` unchanged (`NotImplementedError`). Consider whether `MAX_TOKENS` (4096) is enough headroom for a web_search turn — bump only if the live smoke shows truncation (`stop_reason == "max_tokens"`).
- **`tests/test_providers_search.py`** — `test_claude_search_not_implemented_yet` **will start failing** once the guard is gone; rewrite it as a mock-based test of the two-call flow (fake client returns scripted call-1 / call-2 responses, assert the merged blob shape + that `subquestion_id` is the passed value). Keep `test_search_triggers_match_adaptive_taxonomy` and all `DryRunProvider` tests green untouched.
- **`tests/test_providers_live.py`** — add an opt-in `@pytest.mark.live` smoke that hits the real API once with a tiny query and asserts the blob validates against the contract. Skipped in normal runs.

## Testing strategy

- **Two-call mock (no network):** a fake `anthropic` client whose `messages.create` returns (a) a call-1 response carrying `web_search_tool_result` + answer text, then (b) a call-2 response whose text is `SIGNALS_SCHEMA`-shaped JSON. Assert: `search()` makes exactly two `create` calls; call 1 passes `tools=[web_search…]` and **no** `output_config`; call 2 passes `output_config.format` and **no** `tools`; the returned blob has the contract keys; `subquestion_id` equals the passed value; all 4 triggers present.
- **Model selection:** assert call 1 and call 2 use `claude-sonnet-4-6` (mid), **not** `claude-haiku-4-5`, when `model_tier="cheap"` is passed. Assert `model_override` still wins if set.
- **`pause_turn`:** a fake call-1 response with `stop_reason="pause_turn"` is re-sent and the loop terminates (bounded retries).
- **`parse_signals` round-trip:** feed a `search()` mock blob straight into `adaptive.parse_signals` and assert the fired set / details come out as expected — proves the shapes actually mate.
- **Regression:** `pytest tests/test_providers_search.py -q` and the full `pytest -q` stay green; `scripts/stamp_docs.py --check` exit 0.
- **Live smoke (`-m live`, opt-in):** one real `search("…")` returns a contract-valid blob with ≥1 real (non-`example.com`) source. Run by the user with a key — not in CI.

### Edge cases (must be covered)
- Call 1 returns **no** `web_search_tool_result` (model answered without searching) → `sources` may be empty; blob still valid; `empty_result` is the trigger the model is expected to fire (mock asserts the shape, not the model's judgement).
- Call 2 returns malformed JSON despite the schema (e.g. a refusal, `stop_reason="refusal"`) → `search()` returns a well-formed blob with empty/`fired:false` signals rather than raising, so a bad cheap-model turn never blocks the run (mirrors `parse_signals`' fail-safe philosophy). Exact behaviour pinned by a test.

## Explicitly NOT in this stage

- `OpenAICompatProvider.search()` — stays `NotImplementedError`.
- Prompt-cache reuse across the two calls — deferred (and, per above, can't be a naive `messages` replay).
- `max_uses` / multi-round `web_search` tuning, `MAX_TOKENS` re-tuning beyond a truncation fix.
- Routing `model_tier="cheap"` to a search-capable cheap model if one becomes available — revisit if Haiku (or a new cheap tier) gains `web_search_20260209` support.
- `backfill outcome/new_source_ids` (`adaptive.py:262`) — Phase 5 *Scoring*, not retrieval.

## Open questions / future work

- Whether to add a dedicated `SEARCH_MODEL` config (decouple search model from the `complete`/`fanout` tier ladder entirely) — deferred; `mid` hard-resolved in `search()` is enough for now.
- Live-response validation of `SIGNALS_SCHEMA` — the `-m live` smoke is the vehicle; tighten the schema if the real model's output reveals a field mismatch.
