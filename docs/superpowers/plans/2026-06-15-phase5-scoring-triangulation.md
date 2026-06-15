# Phase 5 — Scoring + Triangulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить Phase 5 (`Orchestrator.score`) — живая LLM-оценка источников (credibility/recency/bias/total + type + hypothesis_evidence), триангуляция по гипотезам H1–H4, и backfill `Deviation.outcome`/`new_source_ids`.

**Architecture:** Один метод `Orchestrator.score(s)` между `search()` и `synthesize()`. Три шага: per-source scoring (`model_tier="cheap"`) → triangulation (`model_tier="mid"`) → persist + backfill. Scoring через structured JSON output провайдера (паттерн `ClaudeProvider.search()` Call 2 / `SIGNALS_SCHEMA`). `DryRunProvider` даёт детерминированные баллы для CI. Граница фазы узкая: только выводимое из `url+title+claim`; мета-поля (author/date/channel/language/fetched) вне фазы.

**Tech Stack:** Python 3, pytest, ruff. Провайдеры — `runner/providers.py`. Оркестратор — `runner/orchestrator.py`. Адаптивный цикл — `runner/adaptive.py`.

**Spec:** [docs/superpowers/specs/2026-06-15-phase5-scoring-triangulation-design.md](../specs/2026-06-15-phase5-scoring-triangulation-design.md)

---

## File Structure

- **`runner/providers.py`** (modify) — добавить `score()` в `LLMProvider` Protocol, `DryRunProvider`, `ClaudeProvider`, `OpenAICompatProvider`. Добавить `SCORE_SCHEMA` + `_SCORE_PROMPT`. Это слой LLM-вызова scoring.
- **`runner/scoring.py`** (create) — чистые функции БЕЗ сети: `compute_total()`, `triangulate()`, рендер `triangulation.md`, агрегация round→ids. Сюда выносим всю детерминированную логику, чтобы тестировать без провайдера и держать `score()` тонким.
- **`runner/orchestrator.py`** (modify) — `RunState` получает поля под scoring; `search()` учитывает round→ids; новый метод `score()`; `run()` зовёт `score()`.
- **`runner/adaptive.py`** (modify) — снять `TODO(Phase 5)` (backfill теперь делает `score()`, комментарий обновить).
- **`tests/test_scoring.py`** (create) — юнит-тесты scoring/triangulation на `DryRunProvider` + чистых функциях.
- **`tests/test_orchestrator_score.py`** (create) — интеграция `score()` end-to-end на `DryRunProvider`.

Разделение `scoring.py` (чистая логика) vs `providers.py` (LLM-вызов) повторяет уже принятый в проекте паттерн `adaptive.py` (чистый цикл) vs `providers.py` (сеть).

---

### Task 1: `runner/scoring.py` — чистые функции `compute_total` и `triangulate`

**Files:**
- Create: `runner/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scoring.py
from runner.scoring import compute_total, triangulate

def test_compute_total_sums_three_axes():
    assert compute_total({"credibility": 5, "recency": 4, "bias": 3}) == 12

def test_compute_total_none_when_axis_missing():
    # missing axis => unscored source => total is None (visible skip, not silent 0)
    assert compute_total({"credibility": 5, "recency": 4}) is None

def test_triangulate_flags_under_when_fewer_than_three_distinct_types():
    # H1 supported by 2 sources but only 1 distinct type => under_triangulated
    scored = [
        {"id": "s01", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s02", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
    ]
    result = triangulate(scored, ["H1: claim"])
    h1 = next(h for h in result if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 1
    assert h1["under_triangulated"] is True

def test_triangulate_not_under_with_three_distinct_types():
    scored = [
        {"id": "s01", "type": "Primary", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s02", "type": "Academic", "hypothesis_evidence": {"H1": "supports"}},
        {"id": "s03", "type": "Forum", "hypothesis_evidence": {"H1": "supports"}},
    ]
    h1 = next(h for h in triangulate(scored, ["H1: claim"]) if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 3
    assert h1["under_triangulated"] is False

def test_triangulate_counts_contradicting_separately():
    scored = [
        {"id": "s01", "type": "Primary", "hypothesis_evidence": {"H1": "contradicts"}},
        {"id": "s02", "type": "Academic", "hypothesis_evidence": {"H1": "supports"}},
    ]
    h1 = next(h for h in triangulate(scored, ["H1: claim"]) if h["id"] == "H1")
    assert h1["distinct_types_supporting"] == 1
    assert h1["distinct_types_contradicting"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner.scoring'`

- [ ] **Step 3: Write minimal implementation**

```python
# runner/scoring.py
"""Phase 5 — pure scoring/triangulation logic (no network).

Mirrors the project split: runner.adaptive holds the pure search-loop logic,
runner.providers holds the network calls. Here, the LLM-facing scoring call lives
in runner.providers.*.score(); this module holds the deterministic arithmetic and
triangulation that consume that call's output.
"""
from __future__ import annotations

# H1..H4 hypothesis ids are derived from the "Hn: ..." prefix produced in Phase 1.
AXES = ("credibility", "recency", "bias")


def compute_total(scores: dict) -> int | None:
    """Sum the three rubric axes. Returns None if any axis is missing — an unscored
    source is an honest skip signal, not a silent zero."""
    if not all(axis in scores for axis in AXES):
        return None
    return sum(int(scores[axis]) for axis in AXES)


def hypothesis_ids(hypotheses: list[str]) -> list[str]:
    """Extract H-ids ('H1', 'H2', ...) from 'H1: claim' strings; fall back to Hn index."""
    ids = []
    for i, h in enumerate(hypotheses, start=1):
        head = h.split(":", 1)[0].strip()
        ids.append(head if head.startswith("H") and head[1:].isdigit() else f"H{i}")
    return ids


def triangulate(scored: list[dict], hypotheses: list[str]) -> list[dict]:
    """For each hypothesis, count DISTINCT source types that support / contradict it.
    A hypothesis backed by < 3 distinct supporting types is under_triangulated."""
    result = []
    for hid in hypothesis_ids(hypotheses):
        supporting_types: set[str] = set()
        contradicting_types: set[str] = set()
        for src in scored:
            stance = (src.get("hypothesis_evidence") or {}).get(hid)
            stype = src.get("type", "Other")
            if stance == "supports":
                supporting_types.add(stype)
            elif stance == "contradicts":
                contradicting_types.add(stype)
        n_sup = len(supporting_types)
        result.append({
            "id": hid,
            "distinct_types_supporting": n_sup,
            "distinct_types_contradicting": len(contradicting_types),
            "under_triangulated": n_sup < 3,
            "note": "",
        })
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add runner/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): чистые compute_total + triangulate (Phase 5)"
```

---

### Task 2: `runner/scoring.py` — рендер `triangulation.md`

**Files:**
- Modify: `runner/scoring.py` (добавить `render_triangulation`)
- Test: `tests/test_scoring.py` (добавить тесты)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_scoring.py
from runner.scoring import render_triangulation

def test_render_triangulation_has_header_and_row_per_hypothesis():
    rows = [
        {"id": "H1", "distinct_types_supporting": 3, "distinct_types_contradicting": 0,
         "under_triangulated": False, "note": "well supported"},
        {"id": "H2", "distinct_types_supporting": 1, "distinct_types_contradicting": 2,
         "under_triangulated": True, "note": "single voice"},
    ]
    md = render_triangulation("my topic", rows)
    assert "# Triangulation — my topic" in md
    assert "| H1 |" in md and "| H2 |" in md
    # under_triangulated rendered as a visible flag
    assert "⚠️" in md  # H2 is flagged
    assert md.count("⚠️") == 1  # only H2

def test_render_triangulation_empty_still_has_header():
    md = render_triangulation("topic", [])
    assert "# Triangulation — topic" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -k render_triangulation -q`
Expected: FAIL — `ImportError: cannot import name 'render_triangulation'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to runner/scoring.py
def render_triangulation(topic: str, rows: list[dict]) -> str:
    """Render the H1..H4 triangulation table for Phase 6 to consume. Under-triangulated
    hypotheses carry a visible ⚠️ flag so synthesis lowers their confidence."""
    out = [
        f"# Triangulation — {topic}",
        "",
        "| H | supporting types | contradicting types | flag | note |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        flag = "⚠️" if r["under_triangulated"] else "—"
        out.append(
            f"| {r['id']} | {r['distinct_types_supporting']} | "
            f"{r['distinct_types_contradicting']} | {flag} | {r.get('note', '')} |"
        )
    return "\n".join(out) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add runner/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): рендер triangulation.md (Phase 5)"
```

---

### Task 3: `score()` в `LLMProvider` Protocol + `DryRunProvider`

**Files:**
- Modify: `runner/providers.py` (Protocol ~90–109; `DryRunProvider` ~112–139; добавить `SCORE_SCHEMA` рядом с `SIGNALS_SCHEMA` ~49)
- Test: `tests/test_scoring.py`

Контракт `score()`: принимает список источников `[{id, url, title, claim}]` + список гипотез, возвращает `{"sources": [{id, credibility, recency, bias, type, hypothesis_evidence}]}`. НЕ считает `total` (это делает `compute_total` в Python).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_scoring.py
from runner.providers import DryRunProvider

def test_dryrun_score_returns_deterministic_scores():
    p = DryRunProvider()
    srcs = [{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}]
    out = p.score(srcs, ["H1: a", "H2: b"], model_tier="cheap")
    assert out["sources"][0]["id"] == "s01"
    for axis in ("credibility", "recency", "bias"):
        assert 1 <= out["sources"][0][axis] <= 5
    assert out["sources"][0]["type"] in (
        "Primary", "Academic", "Industry-media", "General-media",
        "Expert-blog", "Forum", "Other")
    # every hypothesis gets a stance
    assert set(out["sources"][0]["hypothesis_evidence"]) == {"H1", "H2"}

def test_dryrun_score_is_stable_across_calls():
    p = DryRunProvider()
    srcs = [{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}]
    a = p.score(srcs, ["H1: a"], model_tier="cheap")
    b = p.score(srcs, ["H1: a"], model_tier="cheap")
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -k dryrun_score -q`
Expected: FAIL — `AttributeError: 'DryRunProvider' object has no attribute 'score'`

- [ ] **Step 3: Write minimal implementation**

Add `SCORE_SCHEMA` near `SIGNALS_SCHEMA` (after line ~62 in `runner/providers.py`):

```python
SOURCE_TYPES = ("Primary", "Academic", "Industry-media", "General-media",
                "Expert-blog", "Forum", "Other")
STANCES = ("supports", "contradicts", "partial", "neutral")

_SCORE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "credibility": {"type": "integer", "minimum": 1, "maximum": 5},
        "recency": {"type": "integer", "minimum": 1, "maximum": 5},
        "bias": {"type": "integer", "minimum": 1, "maximum": 5},
        "type": {"type": "string", "enum": list(SOURCE_TYPES)},
        "hypothesis_evidence": {
            "type": "object",
            "additionalProperties": {"type": "string", "enum": list(STANCES)},
        },
    },
    "required": ["id", "credibility", "recency", "bias", "type", "hypothesis_evidence"],
    "additionalProperties": False,
}
SCORE_SCHEMA = {
    "type": "object",
    "properties": {"sources": {"type": "array", "items": _SCORE_ITEM_SCHEMA}},
    "required": ["sources"],
    "additionalProperties": False,
}
```

Add `score()` to the `LLMProvider` Protocol (after `search()`, ~line 109):

```python
    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        """Phase 5 per-source scoring. Returns
            {"sources": [{"id", "credibility", "recency", "bias", "type",
                          "hypothesis_evidence": {Hn: stance}}, ...]}.
        Does NOT compute `total` — that is summed in Python (runner.scoring.compute_total)."""
        ...
```

Add `score()` to `DryRunProvider` (after its `search()`, ~line 139):

```python
    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        assert model_tier in TIERS, f"unknown tier {model_tier}"
        from runner.scoring import hypothesis_ids
        hids = hypothesis_ids(hypotheses)
        scored = []
        for src in sources:
            h = hashlib.sha1(src["id"].encode()).hexdigest()
            # deterministic axes in 1..5 derived from the id hash
            cred = int(h[0], 16) % 5 + 1
            rec = int(h[1], 16) % 5 + 1
            bias = int(h[2], 16) % 5 + 1
            stype = SOURCE_TYPES[int(h[3], 16) % len(SOURCE_TYPES)]
            evidence = {hid: STANCES[int(h[4 + i % 4], 16) % len(STANCES)]
                        for i, hid in enumerate(hids)}
            scored.append({"id": src["id"], "credibility": cred, "recency": rec,
                           "bias": bias, "type": stype, "hypothesis_evidence": evidence})
        return {"sources": scored}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add runner/providers.py tests/test_scoring.py
git commit -m "feat(providers): score() в Protocol + DryRunProvider + SCORE_SCHEMA (Phase 5)"
```

---

### Task 4: живой `ClaudeProvider.score()` + `OpenAICompatProvider.score()`

**Files:**
- Modify: `runner/providers.py` (`ClaudeProvider` ~195; `OpenAICompatProvider` ~280; добавить `_SCORE_PROMPT` рядом с `_SIGNALS_PROMPT` ~68)
- Test: `tests/test_scoring.py` (live + fake-client unit)

`ClaudeProvider.score()` — один structured-JSON call (паттерн Call 2 из `search()`): `output_config={"format": {"type": "json_schema", "schema": SCORE_SCHEMA}}`, без web_search. Использует `_model_for(model_tier)` (НЕ `_search_model` — web_search тут не нужен, haiku справится с rubric).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_scoring.py
import json
import pytest

class _FakeMsg:
    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]

class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.messages = type("M", (), {"create": self._create})()
    def _create(self, **kw):
        return _FakeMsg(json.dumps(self._payload))

def test_claude_score_parses_structured_json():
    from runner.providers import ClaudeProvider
    payload = {"sources": [{"id": "s01", "credibility": 5, "recency": 4, "bias": 3,
                            "type": "Primary", "hypothesis_evidence": {"H1": "supports"}}]}
    p = ClaudeProvider(client=_FakeClient(payload))
    out = p.score([{"id": "s01", "url": "https://x", "title": "T", "claim": "c"}],
                  ["H1: a"], model_tier="cheap")
    assert out["sources"][0]["credibility"] == 5
    assert out["sources"][0]["type"] == "Primary"

@pytest.mark.live
def test_claude_score_live():
    from runner.providers import build_provider
    p = build_provider("claude")
    out = p.score([{"id": "s01", "url": "https://www.bls.gov/", "title": "BLS", "claim": "official labor stats"}],
                  ["H1: official sources are authoritative"], model_tier="cheap")
    s = out["sources"][0]
    assert 1 <= s["credibility"] <= 5
    assert "H1" in s["hypothesis_evidence"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring.py -k claude_score_parses -q`
Expected: FAIL — `AttributeError: 'ClaudeProvider' object has no attribute 'score'`

- [ ] **Step 3: Write minimal implementation**

Add `_SCORE_PROMPT` near `_SIGNALS_PROMPT` (~line 68 in `runner/providers.py`):

```python
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
```

Add `score()` to `ClaudeProvider` (after `search()`):

```python
    def score(self, sources: list[dict], hypotheses: list[str],
              *, model_tier: str = "cheap") -> dict:
        rendered_sources = "\n".join(
            f"- [{s['id']}] {s.get('title', '')}: {s.get('url', '')} — {s.get('claim', '')}"
            for s in sources
        ) or "(no sources)"
        rendered_hyps = "\n".join(f"- {h}" for h in hypotheses) or "(none)"
        prompt = _SCORE_PROMPT.format(hypotheses=rendered_hyps, sources=rendered_sources)
        resp = self.client.messages.create(
            model=self._model_for(model_tier),
            max_tokens=MAX_TOKENS,
            output_config={"format": {"type": "json_schema", "schema": SCORE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return json.loads(text)
```

Add `score()` to `OpenAICompatProvider` (after its `search()`, ~line 280+) — same shape via its JSON path. If `OpenAICompatProvider` has no structured-output helper yet, mirror its existing `search()` JSON-parsing approach:

```python
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
```

NOTE for the implementing engineer: check `OpenAICompatProvider`'s existing `search()` / `_model_for` to match its real method names and client shape before pasting — adapt the call to whatever pattern that class already uses. The Claude path is the source of truth for behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring.py -m "not live" -q`
Expected: PASS (all non-live pass)

- [ ] **Step 5: Commit**

```bash
git add runner/providers.py tests/test_scoring.py
git commit -m "feat(providers): живой score() для Claude + OpenAI-compat (Phase 5)"
```

---

### Task 5: `RunState` + `search()` запоминают round→source_ids

**Files:**
- Modify: `runner/orchestrator.py` (`RunState` ~60–74; `search()` ~112–156)
- Test: `tests/test_orchestrator_score.py`

Цель — собрать `round_source_ids: dict[int, list[str]]`, чтобы Phase 5 заполнила `Deviation.new_source_ids`. `run_round(round_index, ...)` уже знает `round_index`; источники из его блобов помечаем этим индексом при записи.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_score.py
from pathlib import Path
from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider

def test_search_records_round_source_ids(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="medium", root=tmp_path)
    o.reframe(s); o.choose_genre(s); o.plan(s); o.search(s)
    # round->ids map is populated and every recorded id appears in s.sources
    assert s.round_source_ids  # non-empty
    all_ids = {x["id"] for x in s.sources}
    for ids in s.round_source_ids.values():
        for sid in ids:
            assert sid in all_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator_score.py::test_search_records_round_source_ids -q`
Expected: FAIL — `AttributeError: 'RunState' object has no attribute 'round_source_ids'`

- [ ] **Step 3: Write minimal implementation**

In `RunState` (after the `deviations` field, ~line 68) add:

```python
    round_source_ids: dict = field(default_factory=dict)  # round_index -> [source_id]
    triangulation: list = field(default_factory=list)     # Phase 5 output
```

In `search()`, change the blob collection to remember which round each blob came from. Replace the `run_round` body and the source-writing loop so each written source's id is appended to `s.round_source_ids[round_index]`. Concretely, track round on each blob:

```python
        def run_round(round_index, _round_depth, directives):
            blobs = [
                self.p.search(f"[r{round_index}] subtopic {i} for: {s.question}",
                              subquestion_id=f"Q{i}", model_tier="cheap")
                for i in range(max(1, k))
            ]
            for b in blobs:
                b["_round"] = round_index           # tag blob with its round
            collected.extend(blobs)
            return blobs
```

Then in the writing loop, when a source is written, record it under its blob's round. Change `flat` to carry the round:

```python
        flat = [(blob.get("_round", 1), src)
                for blob in collected for src in blob.get("sources", [])]
        written = 0
        for round_index, src in flat:
            if written >= n or src["url"] in seen:
                continue
            seen.add(src["url"])
            written += 1
            sid = src.get("id", f"s{written:02d}")
            url = src["url"]
            stype = "Primary" if written % 2 else "Academic"  # scaffold: type is placeholder, not derived from the source
            s.sources.append({"id": sid, "url": url, "type": stype})
            s.round_source_ids.setdefault(round_index, []).append(sid)
            fm = (f"---\nid: {sid}\nurl: {url}\ntitle: {src.get('title', 'Source')}\n"
                  f"access: OPEN\ntype: {stype}\n---\n{src.get('claim', '')}\n")
            (srcdir / f"{written:02d}_{sid}.md").write_text(fm, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator_score.py::test_search_records_round_source_ids -q`
Expected: PASS

Also run the existing search test to confirm no regression:

Run: `python -m pytest tests/test_orchestrator_search.py -q`
Expected: PASS (unchanged)

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py tests/test_orchestrator_score.py
git commit -m "feat(orchestrator): search() запоминает round→source_ids под backfill (Phase 5)"
```

---

### Task 6: `Orchestrator.score()` — scoring + перезапись sources + triangulation.md

**Files:**
- Modify: `runner/orchestrator.py` (новый метод `score()`; импорт из `runner.scoring`)
- Test: `tests/test_orchestrator_score.py`

`score()` после `search()`: зовёт `self.p.score(...)`, считает `total` в Python, перезаписывает `sources/NN.md` frontmatter и `sources.csv` с новыми полями, пишет `triangulation.md`. Backfill deviations — отдельной Task 7 (этот метод её вызовет позже).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_orchestrator_score.py
def test_score_enriches_sources_and_writes_triangulation(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="medium", root=tmp_path)
    o.reframe(s); o.choose_genre(s); o.plan(s); o.search(s); o.score(s)

    # sources.csv gained the scoring columns
    csv = (s.dir / "sources.csv").read_text(encoding="utf-8")
    header = csv.splitlines()[0]
    assert header == "id,title,url,type,credibility,recency,bias,total,used"

    # each source markdown has the scoring frontmatter
    md_files = list((s.dir / "sources").glob("*.md"))
    assert md_files
    text = md_files[0].read_text(encoding="utf-8")
    assert "credibility:" in text and "total:" in text and "hypothesis_evidence:" in text

    # triangulation.md exists with a header
    tri = (s.dir / "triangulation.md").read_text(encoding="utf-8")
    assert tri.startswith("# Triangulation —")

    # total in s.sources equals the Python sum of the three axes
    src0 = s.sources[0]
    assert src0["total"] == src0["credibility"] + src0["recency"] + src0["bias"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator_score.py::test_score_enriches_sources_and_writes_triangulation -q`
Expected: FAIL — `AttributeError: 'Orchestrator' object has no attribute 'score'`

- [ ] **Step 3: Write minimal implementation**

At the top of `runner/orchestrator.py`, add the import (near other `from runner...` imports):

```python
from runner.scoring import compute_total, triangulate, render_triangulation
```

Add the `score()` method to `Orchestrator` (after `search()`, before `synthesize()`):

```python
    # --- Phase 5: scoring + triangulation ---------------------------------
    def score(self, s: RunState) -> None:
        if not s.sources:
            (s.dir / "triangulation.md").write_text(
                f"# Triangulation — {s.slug}\n\n(no sources)\n", encoding="utf-8")
            return

        # step 1: per-source scoring (cheap tier).
        lookup = {x["id"]: x for x in s.sources}
        payload = [{"id": x["id"], "url": x["url"], "title": x.get("title", ""),
                    "claim": x.get("claim", "")} for x in s.sources]
        result = self.p.score(payload, s.hypotheses, model_tier="cheap")

        for item in result.get("sources", []):
            tgt = lookup.get(item.get("id"))
            if tgt is None:  # provider returned an id we never sent — ignore
                continue
            tgt["credibility"] = item["credibility"]
            tgt["recency"] = item["recency"]
            tgt["bias"] = item["bias"]
            tgt["type"] = item["type"]
            tgt["hypothesis_evidence"] = item.get("hypothesis_evidence", {})
            tgt["total"] = compute_total(item)

        # step 2: triangulation (mid tier is the LLM tier in the spec, but the
        # distinct-type counting itself is deterministic — done in Python here).
        s.triangulation = triangulate(
            [x for x in s.sources if x.get("total") is not None], s.hypotheses)

        # step 3: persist.
        self._rewrite_sources(s)
        (s.dir / "triangulation.md").write_text(
            render_triangulation(s.slug, s.triangulation), encoding="utf-8")

    def _rewrite_sources(self, s: RunState) -> None:
        srcdir = s.dir / "sources"
        srcdir.mkdir(exist_ok=True)
        for i, x in enumerate(s.sources, start=1):
            ev = x.get("hypothesis_evidence", {})
            ev_lines = "".join(f"  {h}: {v}\n" for h, v in ev.items())
            total = x.get("total")
            fm = (
                f"---\nid: {x['id']}\nurl: {x['url']}\n"
                f"title: {x.get('title', 'Source')}\naccess: OPEN\n"
                f"type: {x.get('type', 'Other')}\n"
                f"credibility: {x.get('credibility', '')}\n"
                f"recency: {x.get('recency', '')}\n"
                f"bias: {x.get('bias', '')}\n"
                f"total: {total if total is not None else 'null'}\n"
                f"used: Y\nhypothesis_evidence:\n{ev_lines}"
                f"---\n{x.get('claim', '')}\n"
            )
            (srcdir / f"{i:02d}_{x['id']}.md").write_text(fm, encoding="utf-8")

        rows = ["id,title,url,type,credibility,recency,bias,total,used"]
        for x in s.sources:
            total = x.get("total")
            rows.append(
                f"{x['id']},Source {x['id']},{x['url']},{x.get('type', 'Other')},"
                f"{x.get('credibility', '')},{x.get('recency', '')},{x.get('bias', '')},"
                f"{total if total is not None else ''},Y")
        (s.dir / "sources.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
```

NOTE: `search()` currently does NOT store `title`/`claim` in `s.sources` (only `id/url/type`). For `score()` to pass real `title`/`claim` to the provider, Task 5's `s.sources.append(...)` must also carry them. Update that append in `search()` to:

```python
            s.sources.append({"id": sid, "url": url, "type": stype,
                              "title": src.get("title", "Source"),
                              "claim": src.get("claim", "")})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator_score.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py tests/test_orchestrator_score.py
git commit -m "feat(orchestrator): Phase 5 score() — scoring + triangulation.md + перезапись sources"
```

---

### Task 7: backfill `Deviation.outcome` / `new_source_ids` в `score()`

**Files:**
- Modify: `runner/orchestrator.py` (`score()` — добавить backfill-шаг; вызвать `write_deviations` повторно)
- Test: `tests/test_orchestrator_score.py`

После scoring заполняем pursued-deviations: `new_source_ids` = `s.round_source_ids[round_to]` (источники того round, что deviation спавнила), `outcome` = краткий агрегат. Перезаписываем `deviations.md`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_orchestrator_score.py
def test_score_backfills_pursued_deviations(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth="deep", root=tmp_path)
    o.reframe(s); o.choose_genre(s); o.plan(s); o.search(s); o.score(s)

    pursued = [d for d in s.deviations if d.status == "pursued"]
    # if any deviation was pursued, its placeholder outcome must be replaced
    for d in pursued:
        assert d.outcome != "(pending scoring)"
        # new_source_ids reflects the round it spawned (may be empty only if that
        # round produced no unique sources, but the placeholder must be gone)
    # deviations.md on disk no longer contains the placeholder
    text = (s.dir / "deviations.md").read_text(encoding="utf-8")
    assert "(pending scoring)" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator_score.py::test_score_backfills_pursued_deviations -q`
Expected: FAIL — `assert "(pending scoring)" not in text` (placeholder still present)

NOTE: `depth="deep"` is used to make pursued deviations likely. If `DryRunProvider` never fires triggers (all signals `fired: False`), there may be zero pursued deviations — then the loop body is vacuously true and the on-disk assertion still holds (no placeholder because no pursued record). The test passes either way; it specifically guards that IF pursued records exist, they are backfilled.

- [ ] **Step 3: Write minimal implementation**

Add the import at the top of `runner/orchestrator.py` if not already present:

```python
from runner.adaptive import write_deviations
```

(`run_search_loop` / `write_deviations` are already imported for `search()` — reuse the same import line.)

Add a backfill block at the end of `score()` (after writing `triangulation.md`):

```python
        # step 4: backfill deviations now that sources are scored (closes the
        # TODO(Phase 5) in adaptive.py). For each pursued deviation, attach the
        # source ids produced by the round it spawned.
        for d in s.deviations:
            if d.status != "pursued":
                continue
            ids = s.round_source_ids.get(d.round_to, [])
            d.new_source_ids = list(ids)
            if ids:
                totals = [lookup[i]["total"] for i in ids
                          if i in lookup and lookup[i].get("total") is not None]
                avg = round(sum(totals) / len(totals), 1) if totals else "n/a"
                d.outcome = f"{len(ids)} sources, avg total {avg}"
            else:
                d.outcome = "no unique sources"
        write_deviations(s.dir, s.slug, s.deviations)
```

NOTE: `lookup` is the `{id: source}` dict built in step 1 of `score()` — it is in scope. If you refactored it away, rebuild it: `lookup = {x["id"]: x for x in s.sources}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator_score.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py tests/test_orchestrator_score.py
git commit -m "feat(orchestrator): backfill outcome/new_source_ids в score() (закрывает TODO adaptive.py)"
```

---

### Task 8: подключить `score()` в `run()` + снять `TODO(Phase 5)` в adaptive.py

**Files:**
- Modify: `runner/orchestrator.py` (`run()` ~175–182)
- Modify: `runner/adaptive.py` (комментарий ~262)
- Test: `tests/test_orchestrator_score.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_orchestrator_score.py
def test_run_invokes_score_phase(tmp_path):
    o = Orchestrator(DryRunProvider())
    out_dir = o.run("does X cause Y", "medium", tmp_path)
    # Phase 5 artifacts exist after a full run()
    assert (out_dir / "triangulation.md").exists()
    csv = (out_dir / "sources.csv").read_text(encoding="utf-8")
    assert "credibility" in csv.splitlines()[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator_score.py::test_run_invokes_score_phase -q`
Expected: FAIL — `triangulation.md` not found (run() doesn't call score() yet)

- [ ] **Step 3: Write minimal implementation**

In `run()` insert `self.score(s)` between `self.search(s)` and `self.synthesize(s)`:

```python
    def run(self, question: str, depth: str, root: Path) -> Path:
        s = RunState(question=question, depth=depth, root=root)
        self.reframe(s)
        self.choose_genre(s)
        self.plan(s)
        self.search(s)
        self.score(s)
        self.synthesize(s)
        return s.dir
```

In `runner/adaptive.py`, replace the stale TODO comment (line ~262) — the backfill now happens in Phase 5:

```python
                # outcome/new_source_ids are placeholders here; Phase 5
                # (Orchestrator.score) backfills them after scoring lands.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator_score.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py runner/adaptive.py tests/test_orchestrator_score.py
git commit -m "feat(orchestrator): run() зовёт Phase 5 score(); снять TODO в adaptive.py"
```

---

### Task 9: финальная верификация

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: PASS (all green, live tests skipped)

- [ ] **Step 2: Run ruff (CI gate)**

Run: `ruff check runner/ tests/`
Expected: no violations

- [ ] **Step 3: Re-read the spec line by line**

Open `docs/superpowers/specs/2026-06-15-phase5-scoring-triangulation-design.md` and confirm each requirement maps to a shipped change. Note any gap explicitly.

- [ ] **Step 4: (optional) live smoke test**

Run: `ANTHROPIC_API_KEY=... python -m pytest tests/test_scoring.py -m live -q`
Expected: PASS (real haiku scoring returns valid axes)

---

## Self-Review notes

- **Spec coverage:** scoring (T3/T4/T6) ✓; triangulation by H1–H4 (T1/T2/T6) ✓; backfill adaptive.py:262 (T5/T7/T8) ✓; DryRun determinism (T3) ✓; error-tolerance — unknown id ignored (T6 `lookup.get` guard), unscored → `total: null` (T6 frontmatter) ✓; narrow boundary — no author/date/channel (T6 frontmatter omits them) ✓; 9-column CSV (T6) ✓.
- **Type consistency:** `compute_total` returns `int | None`; `score()` reads `item["credibility"]` (provider guarantees via schema); `triangulate` input keys (`type`, `hypothesis_evidence`) match what `score()` writes into `s.sources`.
- **Known intentional narrowing:** CSV is 9 cols not 14; frontmatter omits meta-fields — documented in spec as Phase 4-fetch's job.
