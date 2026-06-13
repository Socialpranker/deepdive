# Multi-LLM Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the runner's real providers (`ClaudeProvider`, `OpenAICompatProvider`) call live models so the 9-phase methodology runs end-to-end on at least two LLMs.

**Architecture:** Fill the existing `NotImplementedError` stubs in `runner/providers.py` in place (Approach A). Both providers map a `model_tier` to a model name and call their official SDK; `fanout` runs N parallel `complete()` calls through a shared `ThreadPoolExecutor` helper. A `build_provider` factory resolves provider + keys from ENV/CLI with fail-fast on missing keys. The orchestrator is unchanged except for two new CLI flags.

**Tech Stack:** Python 3, `anthropic` SDK, `openai` SDK, `pytest`, `concurrent.futures.ThreadPoolExecutor`.

---

## File Structure

- **Modify** `runner/providers.py` — add `run_parallel` helper; implement `ClaudeProvider.complete/fanout`; replace `OpenAIProvider` with `OpenAICompatProvider`; add `build_provider`. Keep `DryRunProvider` and `get_provider` untouched.
- **Modify** `runner/orchestrator.py` — add `--model` / `--base-url` flags; call `build_provider` instead of `get_provider` in `main()`. No phase-logic change.
- **Create** `tests/test_providers.py` — mock-SDK unit tests for both providers + helper + factory.
- **Create** `tests/test_providers_live.py` — opt-in `@pytest.mark.live` smoke tests (skip without keys).
- **Modify** `scripts/requirements.txt` — add `anthropic`, `openai`.
- **Create** `pytest.ini` — register the `live` marker (repo has no pytest config today).
- **Modify** `runner/DESIGN.md` — reconcile fanout description, status, tier table, rename.

**Conventions confirmed from the SDKs (do not deviate):**
- Anthropic: `client.messages.create(model=, max_tokens=, system=, messages=[{"role":"user","content":...}])`. Response `.content` is a **list of blocks**; text lives on blocks where `block.type == "text"`, accessed as `block.text`. Empty system → pass `anthropic.NOT_GIVEN`, not `""`.
- OpenAI: `client.chat.completions.create(model=, messages=[...])`. Text is `resp.choices[0].message.content` (may be `None`).
- `max_tokens` is **required** by Anthropic — use a module constant `MAX_TOKENS = 4096`.

---

## Task 1: `run_parallel` helper

**Files:**
- Modify: `runner/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_providers.py` with:

```python
import time
import pytest
from runner.providers import run_parallel


def test_run_parallel_preserves_order():
    thunks = [(lambda i=i: f"r{i}") for i in range(5)]
    assert run_parallel(thunks) == ["r0", "r1", "r2", "r3", "r4"]


def test_run_parallel_is_concurrent():
    def slow(i):
        time.sleep(0.2)
        return i
    thunks = [(lambda i=i: slow(i)) for i in range(5)]
    start = time.monotonic()
    out = run_parallel(thunks, limit=5)
    elapsed = time.monotonic() - start
    assert out == [0, 1, 2, 3, 4]
    assert elapsed < 0.6  # ~0.2s parallel, not ~1.0s serial


def test_run_parallel_fails_loud():
    def boom():
        raise ValueError("boom")
    thunks = [lambda: "ok", boom]
    with pytest.raises(ValueError, match="boom"):
        run_parallel(thunks)


def test_run_parallel_empty():
    assert run_parallel([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_parallel'`

- [ ] **Step 3: Write minimal implementation**

In `runner/providers.py`, add `from typing import Callable` to the imports (it already imports `concurrent.futures`). Add after the `TIERS` constant:

```python
def run_parallel(thunks: list[Callable[[], str]], *, limit: int = 5) -> list[str]:
    """Run N thunks concurrently. Result order == input order.
    Any exception propagates (fail-loud)."""
    if not thunks:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(limit, len(thunks))) as ex:
        futures = [ex.submit(fn) for fn in thunks]
        return [f.result() for f in futures]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/providers.py tests/test_providers.py
git commit -m "feat(runner): run_parallel — параллельный fanout-хелпер (порядок + fail-loud)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `ClaudeProvider.complete`

**Files:**
- Modify: `runner/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:

```python
from unittest.mock import MagicMock
from runner.providers import ClaudeProvider


def _text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _claude_response(text):
    resp = MagicMock()
    resp.content = [_text_block(text)]
    return resp


def test_claude_complete_returns_text():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("hello world")
    p = ClaudeProvider(client=client)
    assert p.complete("hi", model_tier="mid") == "hello world"


def test_claude_complete_maps_tier_to_model():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.complete("hi", model_tier="strong")
    assert client.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"
    p.complete("hi", model_tier="cheap")
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"


def test_claude_complete_invalid_tier_raises():
    p = ClaudeProvider(client=MagicMock())
    with pytest.raises(AssertionError):
        p.complete("hi", model_tier="bogus")


def test_claude_complete_joins_multiple_text_blocks():
    resp = MagicMock()
    resp.content = [_text_block("foo"), _text_block("bar")]
    client = MagicMock()
    client.messages.create.return_value = resp
    p = ClaudeProvider(client=client)
    assert p.complete("hi") == "foobar"


def test_claude_complete_model_override_collapses_tiers():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client, model_override="claude-sonnet-4-6")
    p.complete("hi", model_tier="strong")
    assert client.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_claude_complete_empty_system_uses_not_given():
    import anthropic
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.complete("hi")
    assert client.messages.create.call_args.kwargs["system"] is anthropic.NOT_GIVEN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k claude -v`
Expected: FAIL — `NotImplementedError` from `ClaudeProvider.complete`. (If `import anthropic` fails, do Task 0-deps first: `pip install anthropic openai` and add them to `scripts/requirements.txt` — see Task 7.)

- [ ] **Step 3: Write minimal implementation**

In `runner/providers.py`, do **not** add a top-level `import anthropic` — import it lazily inside `__init__`/`complete` (shown below) so the module still imports when the package is absent. Add a module constant near `TIERS`:

```python
MAX_TOKENS = 4096
```

Replace the body of `ClaudeProvider`. Update `TIER_MODEL` and implement `complete`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k claude -v`
Expected: PASS (6 claude tests)

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/providers.py tests/test_providers.py
git commit -m "feat(runner): ClaudeProvider.complete — реальный вызов anthropic SDK + tier→model

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `ClaudeProvider.fanout`

**Files:**
- Modify: `runner/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:

```python
def test_claude_fanout_runs_each_task_in_order():
    client = MagicMock()
    client.messages.create.side_effect = lambda **kw: _claude_response(
        kw["messages"][0]["content"].upper()
    )
    p = ClaudeProvider(client=client)
    out = p.fanout(["a", "b", "c"], model_tier="cheap")
    assert out == ["A", "B", "C"]


def test_claude_fanout_uses_cheap_tier_by_default():
    client = MagicMock()
    client.messages.create.return_value = _claude_response("x")
    p = ClaudeProvider(client=client)
    p.fanout(["a"])
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k claude_fanout -v`
Expected: FAIL — `NotImplementedError: TODO Task 3`

- [ ] **Step 3: Write minimal implementation**

In `runner/providers.py`, replace `ClaudeProvider.fanout` body:

```python
    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        return run_parallel(
            [lambda t=t: self.complete(t, model_tier=model_tier) for t in tasks],
            limit=self.max_concurrency,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k claude -v`
Expected: PASS (8 claude tests)

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/providers.py tests/test_providers.py
git commit -m "feat(runner): ClaudeProvider.fanout — N параллельных complete() через run_parallel

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `OpenAICompatProvider`

**Files:**
- Modify: `runner/providers.py` (replace the `OpenAIProvider` stub)
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:

```python
from runner.providers import OpenAICompatProvider


def _openai_response(text):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    return resp


def test_openai_complete_returns_text():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("hi there")
    p = OpenAICompatProvider(client=client)
    assert p.complete("q", model_tier="mid") == "hi there"


def test_openai_complete_none_content_becomes_empty():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response(None)
    p = OpenAICompatProvider(client=client)
    assert p.complete("q") == ""


def test_openai_complete_maps_tier_to_model():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q", model_tier="strong")
    assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-5"


def test_openai_complete_system_prepended():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q", system="be terse")
    msgs = client.chat.completions.create.call_args.kwargs["messages"]
    assert msgs[0] == {"role": "system", "content": "be terse"}
    assert msgs[-1] == {"role": "user", "content": "q"}


def test_openai_complete_no_system_omits_system_message():
    client = MagicMock()
    client.chat.completions.create.return_value = _openai_response("x")
    p = OpenAICompatProvider(client=client)
    p.complete("q")
    msgs = client.chat.completions.create.call_args.kwargs["messages"]
    assert all(m["role"] != "system" for m in msgs)


def test_openai_fanout_preserves_order():
    client = MagicMock()
    client.chat.completions.create.side_effect = lambda **kw: _openai_response(
        kw["messages"][-1]["content"].upper()
    )
    p = OpenAICompatProvider(client=client)
    assert p.fanout(["a", "b"]) == ["A", "B"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k openai -v`
Expected: FAIL — `ImportError: cannot import name 'OpenAICompatProvider'`

- [ ] **Step 3: Write minimal implementation**

In `runner/providers.py`, **delete the entire `OpenAIProvider` class** and replace it with:

```python
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
        self.model_override = model_override
        self.max_concurrency = max_concurrency

    def _model_for(self, tier: str) -> str:
        assert tier in TIERS, f"unknown tier {tier}"
        return self.model_override or self.TIER_MODEL[tier]

    def complete(self, prompt: str, *, system: str = "", model_tier: str = "mid") -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        resp = self.client.chat.completions.create(model=self._model_for(model_tier), messages=messages)
        return resp.choices[0].message.content or ""

    def fanout(self, tasks: list[str], *, model_tier: str = "cheap") -> list[str]:
        return run_parallel(
            [lambda t=t: self.complete(t, model_tier=model_tier) for t in tasks],
            limit=self.max_concurrency,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k openai -v`
Expected: PASS (6 openai tests)

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/providers.py tests/test_providers.py
git commit -m "feat(runner): OpenAICompatProvider — один класс под OpenAI/OpenRouter/Ollama/Groq

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `build_provider` factory with fail-fast

**Files:**
- Modify: `runner/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:

```python
from runner.providers import build_provider, DryRunProvider


def test_build_provider_dryrun_needs_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(build_provider("dryrun"), DryRunProvider)


def test_build_provider_claude_fails_fast_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        build_provider("claude")


def test_build_provider_openai_fails_fast_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_provider("openai")


def test_build_provider_unknown_raises(monkeypatch):
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider("gpt9000")


def test_build_provider_claude_with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    p = build_provider("claude", model="claude-opus-4-8")
    assert isinstance(p, ClaudeProvider)
    assert p.model_override == "claude-opus-4-8"


def test_build_provider_openai_passes_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = build_provider("openai", base_url="http://localhost:11434/v1")
    assert isinstance(p, OpenAICompatProvider)
```

Note: `build_provider("claude", ...)` with a key set must NOT make a network call —
`ClaudeProvider.__init__` only constructs `anthropic.Anthropic()`, which does not call
the API. That is safe in tests.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k build_provider -v`
Expected: FAIL — `ImportError: cannot import name 'build_provider'`

- [ ] **Step 3: Write minimal implementation**

In `runner/providers.py`, ensure `import os` is present at the top (add if missing). Add after `get_provider` (keep `get_provider` as-is):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k build_provider -v`
Expected: PASS (6 build_provider tests)

- [ ] **Step 5: Run the full provider suite**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -v`
Expected: PASS (all: 4 helper + 8 claude + 6 openai + 6 build_provider = 24)

- [ ] **Step 6: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/providers.py tests/test_providers.py
git commit -m "feat(runner): build_provider — выбор провайдера из ENV/CLI + fail-fast без ключа

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Orchestrator CLI flags (`--model`, `--base-url`)

**Files:**
- Modify: `runner/orchestrator.py:153-165` (the `main()` function)
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:

```python
def test_orchestrator_main_uses_build_provider(monkeypatch, tmp_path):
    import runner.orchestrator as orch
    captured = {}

    def fake_build(name, *, model=None, base_url=None):
        captured["name"] = name
        captured["model"] = model
        captured["base_url"] = base_url
        return DryRunProvider()

    monkeypatch.setattr(orch, "build_provider", fake_build)
    monkeypatch.setattr(
        "sys.argv",
        ["orchestrator", "test q", "--provider", "openai",
         "--model", "gpt-4o", "--base-url", "http://x/v1", "--out", str(tmp_path)],
    )
    orch.main()
    assert captured == {"name": "openai", "model": "gpt-4o", "base_url": "http://x/v1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k orchestrator_main -v`
Expected: FAIL — `AttributeError: module 'runner.orchestrator' has no attribute 'build_provider'` (it currently imports `get_provider`).

- [ ] **Step 3: Write minimal implementation**

In `runner/orchestrator.py`, update the import line (currently `from .providers import LLMProvider, get_provider` with a script fallback). Change **both** the package import and the script-fallback import to also bring in `build_provider`:

```python
try:
    from .providers import LLMProvider, build_provider
except ImportError:  # run as a script
    from providers import LLMProvider, build_provider
```

Then in `main()`, add the two arguments after `--provider` and switch the construction call:

```python
    ap.add_argument("--provider", default="dryrun")
    ap.add_argument("--model", default=None, help="override the tier→model mapping (all tiers use this model)")
    ap.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint base URL")
    ap.add_argument("--out", type=Path, default=Path("research"))
    args = ap.parse_args()

    orch = Orchestrator(build_provider(args.provider, model=args.model, base_url=args.base_url))
```

(Remove the old `get_provider(args.provider)` call. `get_provider` stays defined in `providers.py` for backward compat but is no longer imported here.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest tests/test_providers.py -k orchestrator_main -v`
Expected: PASS

- [ ] **Step 5: Verify the dry-run E2E still works**

Run:
```bash
cd ~/Downloads/claude-deep-research
python runner/orchestrator.py "test question" --provider dryrun --out /tmp/runner_check
python eval/validate_structure.py --research-dir /tmp/runner_check/test-question --strict
```
Expected: orchestrator prints "Run written to: ...", validator exits 0 (clean). If the slug differs, use the path the orchestrator printed.

- [ ] **Step 6: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/orchestrator.py tests/test_providers.py
git commit -m "feat(runner): orchestrator — флаги --model/--base-url + build_provider

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Dependencies + live smoke test + pytest marker

**Files:**
- Modify: `scripts/requirements.txt`
- Create: `pytest.ini`
- Create: `tests/test_providers_live.py`

- [ ] **Step 1: Add dependencies**

Edit `scripts/requirements.txt` to read:

```
requests>=2.31.0
pytest>=8.0
anthropic>=0.40
openai>=1.50
```

(Verify the latest minor at install time; the lower bounds above are conservative. If `pip install` resolves something newer, that's fine.)

- [ ] **Step 2: Install**

Run: `cd ~/Downloads/claude-deep-research && pip install -r scripts/requirements.txt`
Expected: `anthropic` and `openai` install successfully.

- [ ] **Step 3: Register the `live` marker**

Create `pytest.ini` at repo root:

```ini
[pytest]
markers =
    live: hits real LLM APIs; needs API keys; skipped by default (run with -m live)
```

- [ ] **Step 4: Write the live smoke test**

Create `tests/test_providers_live.py`:

```python
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
```

- [ ] **Step 5: Verify live tests are skipped by default**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest -q`
Expected: the live tests do NOT run (default run excludes nothing by marker, but each is gated by `skipif` on env keys — with no keys set they report as skipped, not failed). Full suite green: 22 original + 25 provider unit tests, live tests skipped.

If you want to confirm collection: `python -m pytest -m live --collect-only -q` lists the 3 live tests.

- [ ] **Step 6: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add scripts/requirements.txt pytest.ini tests/test_providers_live.py
git commit -m "test(runner): anthropic+openai в deps; opt-in live smoke под -m live

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Reconcile `runner/DESIGN.md` with reality

**Files:**
- Modify: `runner/DESIGN.md`

- [ ] **Step 1: Update the LLMProvider protocol note**

In `runner/DESIGN.md`, find the `fanout` bullet under "### LLMProvider protocol" (currently: "The Claude adapter uses real sub-agents; other adapters fall back to a thread pool…"). Replace it with:

```
- `fanout` — run N independent search/extract tasks. **All** adapters run N parallel
  `complete()` calls via a `ThreadPoolExecutor` (`run_parallel`). The runner is
  standalone — it does NOT depend on Claude Code harness sub-agents. Uniform mechanism
  across providers is the whole point.
```

- [ ] **Step 2: Update the Status section**

In the "## Status" section, replace the `providers.py` bullet with:

```
- `providers.py` — protocol + `DryRunProvider` (no network, deterministic) + the real
  `ClaudeProvider` (anthropic SDK) and `OpenAICompatProvider` (openai SDK; any
  OpenAI-compatible endpoint via `base_url`). `build_provider` resolves provider+keys
  from ENV/CLI with fail-fast. Real adapters are **implemented**, not stubbed.
```

- [ ] **Step 3: Update the tier-mapping table**

In the "### Tier mapping" table, update the OpenAI column to real defaults and add a coverage note under the table:

```
| strong (P1/3/6) | Opus | gpt-5 | biggest local |
| mid (synth) | Sonnet | gpt-4o | mid local |
| cheap (fan-out) | Haiku | gpt-4o-mini | small local |

`OpenAICompatProvider` covers OpenRouter / Ollama / Groq / vLLM / LM Studio through
`--base-url` + `--model` — no separate adapter per backend.
```

- [ ] **Step 4: Fix the architecture file list**

In the "## Architecture" code block, update the `providers.py` comment:

```
  providers.py      # LLMProvider protocol + adapters (Claude, OpenAI-compat, DryRun) + build_provider
```

- [ ] **Step 5: Update "What's deliberately NOT here"**

Append a sentence to that section noting what moved out of scope:

```
Real model calls are now wired (this milestone). Still TODO: real web search /
retrieval (source URLs remain placeholders) and per-phase prompt assembly from
references/*.
```

- [ ] **Step 6: Commit**

```bash
cd ~/Downloads/claude-deep-research
git add runner/DESIGN.md
git commit -m "docs(runner): DESIGN.md — привести в соответствие (fanout=thread-pool, адаптеры реализованы)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] **Full test suite green**

Run: `cd ~/Downloads/claude-deep-research && python -m pytest -q`
Expected: 22 original + 25 provider unit tests pass; 3 live tests skipped (no keys). Zero failures.

- [ ] **Lint clean**

Run: `cd ~/Downloads/claude-deep-research && ruff check runner/ tests/`
Expected: no errors. (If ruff flags the `lambda t=t:` closures or unused imports, fix per its guidance — but the `t=t` default-binding is intentional and correct for the loop-closure capture.)

- [ ] **E2E dry-run unbroken**

Run:
```bash
cd ~/Downloads/claude-deep-research
python runner/orchestrator.py "does the runner still work" --provider dryrun --out /tmp/runner_final
python eval/validate_structure.py --research-dir /tmp/runner_final/does-the-runner-still-work --strict
```
Expected: validator exits 0.

- [ ] **(Optional, manual) Live proof**

With `ANTHROPIC_API_KEY` (and/or `OPENAI_API_KEY`) exported:
Run: `cd ~/Downloads/claude-deep-research && python -m pytest -m live -v`
Expected: the keyed providers' smoke tests PASS — proof the engine talks to real models.

- [ ] **Re-read the spec line by line**

Open `docs/superpowers/specs/2026-06-13-multi-llm-runner-design.md` and tick each
requirement against the implemented code. Confirm: both providers real, fanout
parallel + fail-loud + order-preserving, fail-fast config, mock+live tests, DESIGN
reconciled, web-search correctly left out of scope.
