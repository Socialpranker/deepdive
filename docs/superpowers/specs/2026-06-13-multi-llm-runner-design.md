# Multi-LLM Runner — Phase 2 Design

**Date:** 2026-06-13
**Status:** Approved (brainstorm) → ready for implementation plan
**Scope owner:** runner/ (the model-agnostic orchestrator)

## Goal

Take the runner from a Claude-only scaffold to a **working multi-LLM engine**: the
`complete()` and `fanout()` methods of the real providers actually call live models,
and the 9-phase methodology runs end-to-end on **at least two** providers (Claude via
the Anthropic SDK, plus any OpenAI-compatible endpoint).

**Finish line of this phase:** `ClaudeProvider` and `OpenAICompatProvider` no longer
raise `NotImplementedError` — they make real API calls. The orchestrator drives them
through the existing `LLMProvider` interface unchanged.

**Explicitly the NEXT phase, not this one:** real web search / retrieval. Source URLs
remain placeholders (`example.com`) for now. This phase wires the *brains*, not the
*eyes*.

## Background: where the code is today

- `runner/providers.py` — `LLMProvider` Protocol + a working `DryRunProvider`
  (deterministic, no network). `ClaudeProvider` / `OpenAIProvider` are stubs whose
  `complete()` and `fanout()` raise `NotImplementedError`.
- `runner/orchestrator.py` — drives 5 wired phases (reframe → genre → plan → search →
  synthesize) through the provider interface. Produces a run directory that validates
  clean against `eval/validate_structure.py`. Source URLs are hardcoded placeholders.
- `scripts/requirements.txt` — only `requests` + `pytest`. No `anthropic`, no `openai`.
- `runner/` has **zero** tests today. Clean territory.
- `references/model_routing.md` defines tier→model semantics (strong/mid/cheap).

## Decisions (from brainstorm)

| Decision | Choice |
|---|---|
| Phase scope | Real LLM calls now; web-search is a later phase |
| Adapters | `ClaudeProvider` (native SDK) + `OpenAICompatProvider` (one class, configurable `base_url`, covers OpenAI / OpenRouter / Ollama / Groq / vLLM / …) |
| `fanout` mechanism | N parallel `complete()` calls via `ThreadPoolExecutor` — uniform across all providers; runner stays standalone (NOT harness sub-agents) |
| HTTP layer | Official SDKs: `anthropic` + `openai` (retries/backoff/timeouts from the box) |
| Config & secrets | ENV for keys + CLI flags for selection; **fail-fast** with a clear error when a required key is missing |
| Tests | Mock the SDK clients for the main suite; one opt-in live smoke test behind `@pytest.mark.live` |
| Code structure | Approach A — fill the stubs in place in `providers.py`; no new modules |

## Architecture

No interface change. `LLMProvider` stays:

```python
class LLMProvider(Protocol):
    name: str
    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str: ...
    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]: ...
```

### Provider contract (enforced for every real implementation)

1. **`model_tier` ∈ `{"strong","mid","cheap"}`** — asserted on entry. Each provider
   maps tier→model via its own `TIER_MODEL` dict. A CLI `--model` override collapses
   all tiers to one explicitly-named model.
2. **`complete` returns plain text.** API errors after the SDK's own retries propagate
   as exceptions — fail loud, never swallow.
3. **`fanout(tasks)` returns a list of the same length and order as `tasks`.** Order is
   load-bearing (the orchestrator may map result[i] to subtopic[i]). If any task raises,
   the whole `fanout` raises — no silent partial results.
4. **`fanout` bounds concurrency** with a worker cap (default 5) — rate-limit and cost
   safety. Implemented via a shared `run_parallel` helper.

### Tier → model mapping (verified model IDs, 2026-06-13)

| tier | Claude (`ClaudeProvider`) | OpenAI default (`OpenAICompatProvider`) |
|---|---|---|
| strong | `claude-opus-4-8` | `gpt-5` |
| mid | `claude-sonnet-4-6` | `gpt-4o` |
| cheap | `claude-haiku-4-5` | `gpt-4o-mini` |

Claude IDs are authoritative bare aliases (no date suffix). OpenAI defaults apply only
to the vanilla OpenAI endpoint; with `--base-url` + `--model` the caller names whatever
the target endpoint serves (e.g. `anthropic/claude-...` via OpenRouter, a local tag via
Ollama). The OpenAI default IDs are best-effort and re-verified at implementation time.

## Components

### `run_parallel` (module-level helper in `providers.py`)

```python
def run_parallel(thunks: list[Callable[[], str]], *, limit: int = 5) -> list[str]:
    """Run N thunks concurrently. Result order == input order.
    Any exception propagates (fail-loud per contract §3)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(limit, len(thunks) or 1)) as ex:
        futures = [ex.submit(fn) for fn in thunks]
        return [f.result() for f in futures]   # .result() re-raises; order preserved
```

Shared by both real providers' `fanout`. Thread-pool (not asyncio) because SDK calls
are blocking and release the GIL on I/O — simplest correct option, and it mirrors the
existing DryRun/OpenAI pattern in the repo.

### `ClaudeProvider`

- `__init__(self, client=None, *, model_override=None, max_concurrency=5)` — `client`
  injectable for tests; otherwise `anthropic.Anthropic()` (reads `ANTHROPIC_API_KEY`).
- `TIER_MODEL = {"strong": "claude-opus-4-8", "mid": "claude-sonnet-4-6", "cheap": "claude-haiku-4-5"}`.
- `complete`: `client.messages.create(model=_model_for(tier), max_tokens=MAX_TOKENS,
  system=system or NOT_GIVEN, messages=[{"role":"user","content":prompt}])`; return the
  joined text of `type=="text"` content blocks.
- `fanout`: `run_parallel([lambda t=t: self.complete(t, model_tier=tier) for t in tasks], limit=...)`.
- `MAX_TOKENS` constant, default 4096 (Anthropic requires `max_tokens`).
- Retries/backoff/timeouts: delegated to the SDK. No hand-rolled retry.

### `OpenAICompatProvider` (replaces `OpenAIProvider`)

- `__init__(self, client=None, *, base_url=None, model_override=None, max_concurrency=5)` —
  otherwise `openai.OpenAI(base_url=base_url)` (reads `OPENAI_API_KEY`; `base_url=None`
  → `api.openai.com`).
- `TIER_MODEL = {"strong": "gpt-5", "mid": "gpt-4o", "cheap": "gpt-4o-mini"}`.
- `complete`: build `messages` = optional system + user; `client.chat.completions.create(...)`;
  return `resp.choices[0].message.content or ""` (some endpoints return `None`).
- `fanout`: same `run_parallel` shape.

### `build_provider` (extends the existing `get_provider`)

```python
def build_provider(name, *, model=None, base_url=None) -> LLMProvider:
    if name == "dryrun":  return DryRunProvider()
    if name == "claude":  _require_env("ANTHROPIC_API_KEY"); return ClaudeProvider(model_override=model)
    if name == "openai":  _require_env("OPENAI_API_KEY");
                          return OpenAICompatProvider(base_url=base_url or os.getenv("OPENAI_BASE_URL"),
                                                      model_override=model)
    raise ValueError(f"unknown provider {name!r} (expected: dryrun|claude|openai)")
```

- `_require_env(name)` → raises `RuntimeError` with a clear message if the env var is
  absent/empty. **DryRun never requires a key** (keeps the CI/E2E path alive).
- `get_provider` stays for backward-compat with any caller/test that uses it.

## Data flow

Unchanged from today. `Orchestrator.run()` calls `self.p.complete(...)` /
`self.p.fanout(...)`; swapping the model = swapping the provider instance. The only
orchestrator edit is plumbing two new CLI flags into `build_provider`.

## CLI surface (orchestrator `main()`)

- Existing: `question`, `--depth`, `--provider`, `--out`.
- New: `--model` (override the tier mapping — collapses all tiers to one model),
  `--base-url` (OpenAI-compatible endpoint base URL).
- Wiring: `build_provider(args.provider, model=args.model, base_url=args.base_url)`.

Keys come from the environment: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`OPENAI_BASE_URL` (optional). Missing required key → fail-fast at startup, not mid-run.

## Error handling

- **Missing key** → `RuntimeError` from `_require_env` before any network call.
- **Unknown provider / tier** → `ValueError` / `AssertionError` (fail loud).
- **API failure** → SDK retries (429/5xx) exhausted → exception propagates out of
  `complete`/`fanout`. No catch-and-continue, no placeholder substitution.
- **`fanout` partial failure** → whole call raises (contract §3).

## Testing

New `tests/test_providers.py` (mock SDK clients, no network):

| Check | Mechanism |
|---|---|
| tier → model mapping | mock client; assert `model=` arg per tier |
| `--model` override collapses tiers | `model_override="x"` → all tiers send `model="x"` |
| invalid tier → assert | `complete(model_tier="bogus")` raises `AssertionError` |
| system passed / empty omitted | inspect mock call args |
| Claude text joined from blocks | mock returns `[TextBlock,...]` → joined string |
| OpenAI `None` content → `""` | mock `message.content=None` → no crash |
| `fanout` preserves order | mock with varied/delayed returns → input order out |
| `fanout` fail-loud | one thunk raises → exception propagates |
| `build_provider` fail-fast | no env → `RuntimeError`; with env → provider object |
| `run_parallel` is parallel | N×T-second tasks finish in ~T, not ~N·T |

New `tests/test_providers_live.py` behind `@pytest.mark.live` (registered in pytest
config): real `complete("ping")` to Claude and to OpenAI; **skips when the key is
absent**. Run manually with `pytest -m live`. Never runs in default CI.

`DryRunProvider` stays as the orchestrator E2E provider.

## Dependencies

Add to `scripts/requirements.txt`: `anthropic`, `openai` (pin `>=` minor with a major
upper bound; exact bounds verified at implementation time). `requests` + `pytest`
remain.

## Verification (before "done")

1. `python -m pytest -q` — 22 existing + new provider tests green.
2. `python -m pytest -m live` — manual, with keys, to confirm real calls (smoke).
3. `ruff check` — clean.
4. E2E dry-run unbroken:
   `python runner/orchestrator.py "test q" --provider dryrun --out /tmp/r` then
   `python eval/validate_structure.py --research-dir /tmp/r/<slug> --strict` passes.
5. Re-read this spec line by line; tick done/not-done.

## Out of scope (named, so scope can't creep)

Real web search / retrieval (URLs stay placeholders); splitting `phases.py` /
`state.py` out of the orchestrator; per-tier model granularity; streaming; prompt
caching; the local-model adapter as a separate class (OpenAI-compat covers Ollama via
`base_url`).

## DESIGN.md reconciliation

`runner/DESIGN.md` is edited as part of this work to match reality:
- fanout description: "real Explore sub-agents" → "N parallel API calls via
  ThreadPoolExecutor, uniform across providers; runner is standalone".
- Status: `ClaudeProvider` / `OpenAICompatProvider` marked implemented (not stub).
- Tier table: OpenAI column → real IDs; note OpenRouter/Ollama coverage via `base_url`.
- `OpenAIProvider` → `OpenAICompatProvider` rename reflected.
