# Docs Single-Source-of-Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every headline count and phase declaration in the deep-research docs generated from a single source of truth, with a CI gate that fails when docs drift.

**Architecture:** Counts come from regexes over `references/` (no separate registry); phases come from a new `phases.yaml`; a stamper (`scripts/stamp_docs.py`) rewrites doc spans between `<!--gen:KEY-->...<!--/gen-->` markers; CI runs `stamp_docs.py --check` and fails on a non-empty diff. The human runs `--write` locally and commits.

**Tech Stack:** Python 3.11 (CI) / 3.14 (local), pytest 8.4.2, stdlib only (no PyYAML — `phases.yaml` parsed by a tiny stdlib parser for the flat schema we control).

**Verified ground truth (regex-checked 2026-06-13):** blocks=103, channels=29, stat_sources=461, api=39, genres=6, phases=9 steps (1,2,3,3.5,4,5,6,6.5,7).

**Branch:** `docs/single-source-of-truth` (already created; spec committed at `9b051f3`).

---

## File Structure

| File | Responsibility |
|---|---|
| `phases.yaml` (new, repo root) | Single structural source for the 9 phases (id, names, model, effort, depth_gate, order). |
| `scripts/catalog_counts.py` (new) | Ground-truth extractor: `counts() -> dict` via verified regexes. Pure read. |
| `scripts/phases_manifest.py` (new) | Loads + validates `phases.yaml` via a stdlib parser. `load_phases() -> list[dict]`. |
| `scripts/stamp_docs.py` (new) | The stamper. Reads counts + phases, rewrites marker spans. `--write` / `--check`. |
| `scripts/requirements.txt` (modify) | Add `pytest` for CI test step. |
| `tests/` (new dir) | pytest suite for the three scripts. |
| `.github/workflows/validate.yml` (modify) | Add `pytest tests/ -q` and `python scripts/stamp_docs.py --check` steps. |
| Doc files (modify) | Insert `<!--gen:...-->` markers, then first `--write` stamps truth. |
| `QUICKSTART.md` (new) | Newcomer onboarding (install → invoke → output). |

---

## Decisions locked (from spec + fact-finding)

- **`optional` boolean replaced by `depth_gate`** — three phases (3.5, 6.5, 7) gate by depth, not a flat optional. Schema: `depth_gate: shallow|medium|deep` = the *minimum* depth at which the phase is mandatory (shallow = always mandatory).
- **Phase 6.5 = `haiku`/low** (from `runtime_verification.md:92`), not opus. Spec's earlier guess corrected.
- **Phase 7 = Refresh targets** (SKILL.md/workflow.md canon); `model_routing.md`'s tail numbering drifts and is NOT the source.
- **English names for phases 4,5,6,7 are translations** (Russian-only in source) — recorded as such, not as quotes.
- **`genres.md` gotcha:** genres are H2 `## <slug> — ...`; count by matching against the known slug set, not blind H2 count (11 H2s total, only 6 are genres).
- **`blocks` regex:** `^## [A-Z][0-9]+ —` over `references/blocks/*.md`; `INDEX.md` has 0 such lines but is excluded explicitly anyway.
- **INDEX.md says 76, everything else 75** for blocks — the stamper replaces whatever is between markers, so this is irrelevant once markers are placed (the marker content becomes 103 regardless of prior value).

---

## Note on staging

This plan has many tasks. They land in 4 logical groups, each its own commit (per spec staging):
- **Group A (Tasks 1–4):** generator logic + manifest + tests. No doc *content* change.
- **Group B (Tasks 5–7):** insert markers, then first `--write` ("впечатать правду").
- **Group C (Task 8):** CI gate.
- **Group D (Task 9):** quickstart.

The plan body below covers **Group A** in full detail. Groups B–D are specified at the same granularity in a continuation section appended after Group A is reviewed (kept separate to stay reviewable). Each task is self-contained.

---

## Group A — Generator logic + manifest + tests

### Task 1: Test scaffolding + `catalog_counts.py`

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_catalog_counts.py`
- Create: `scripts/catalog_counts.py`

- [ ] **Step 1: Create the empty test package marker**

Create `tests/__init__.py` with no content (empty file). This lets pytest import the package cleanly.

- [ ] **Step 2: Write the failing golden test**

Create `tests/test_catalog_counts.py`:

```python
"""Tests for scripts/catalog_counts.py — the ground-truth extractor."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import catalog_counts  # noqa: E402


def test_counts_match_verified_ground_truth():
    """Golden numbers re-verified by regex on 2026-06-13. If the catalog grows,
    update these intentionally — a mismatch here means either the catalog changed
    or a regex broke."""
    c = catalog_counts.counts(REPO)
    assert c["blocks"] == 103
    assert c["channels"] == 29
    assert c["stat_sources"] == 461
    assert c["api"] == 39
    assert c["genres"] == 6


def test_counts_returns_all_keys():
    c = catalog_counts.counts(REPO)
    assert set(c) == {"blocks", "channels", "stat_sources", "api", "genres"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_catalog_counts.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'catalog_counts'`

- [ ] **Step 4: Write `catalog_counts.py`**

Create `scripts/catalog_counts.py`:

```python
#!/usr/bin/env python3
"""Ground-truth counts for the deep-research catalog.

Counts are derived directly from the files — there is no separate number registry.
These regexes were verified against the tree on 2026-06-13:
  blocks=103, channels=29, stat_sources=461, api=39, genres=6.

Pure read, no side effects. Callable from the stamper and from tests.
"""
from __future__ import annotations

import re
from pathlib import Path

# The six report genres (H2 `## <slug> — ...` in references/genres.md).
# Counted against this known set, not a blind H2 count (genres.md has other H2s).
GENRE_SLUGS = ("qa", "explainer", "decision", "landscape", "validation", "custom")

_BLOCK_RE = re.compile(r"^## [A-Z][0-9]+ —", re.MULTILINE)
_CHANNEL_RE = re.compile(r"^#### [0-9]+\.", re.MULTILINE)
_URL_RE = re.compile(r"^\s*\*\*URL:\*\*", re.MULTILINE)


def _count_blocks(repo: Path) -> int:
    total = 0
    for p in sorted((repo / "references" / "blocks").glob("*.md")):
        if p.name == "INDEX.md":
            continue
        total += len(_BLOCK_RE.findall(p.read_text(encoding="utf-8")))
    return total


def _count_channels(repo: Path) -> int:
    text = (repo / "references" / "channels.md").read_text(encoding="utf-8")
    return len(_CHANNEL_RE.findall(text))


def _count_stat_sources(repo: Path) -> int:
    total = 0
    for p in (repo / "references" / "stat_sources").rglob("*.md"):
        total += len(_URL_RE.findall(p.read_text(encoding="utf-8")))
    return total


def _count_api(repo: Path) -> int:
    root = repo / "references" / "api_sources"
    return sum(
        1
        for p in root.rglob("*.md")
        if p.name not in ("INDEX.md", "README.md")
    )


def _count_genres(repo: Path) -> int:
    text = (repo / "references" / "genres.md").read_text(encoding="utf-8")
    found = {
        slug
        for slug in GENRE_SLUGS
        if re.search(rf"^## {re.escape(slug)} —", text, re.MULTILINE)
    }
    return len(found)


def counts(repo: Path) -> dict[str, int]:
    return {
        "blocks": _count_blocks(repo),
        "channels": _count_channels(repo),
        "stat_sources": _count_stat_sources(repo),
        "api": _count_api(repo),
        "genres": _count_genres(repo),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(counts(Path(__file__).resolve().parents[1]), indent=2))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_catalog_counts.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Sanity-run the module directly**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/catalog_counts.py`
Expected: JSON `{"blocks": 103, "channels": 29, "stat_sources": 461, "api": 39, "genres": 6}`

- [ ] **Step 7: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add tests/__init__.py tests/test_catalog_counts.py scripts/catalog_counts.py
git commit -m "feat(docs-ssot): извлекатель ground-truth счётчиков каталога

catalog_counts.counts() считает blocks/channels/stat_sources/api/genres
выверенными regex прямо из references/. Pure read. Golden-тест на 103/29/461/39/6."
```

---

### Task 2: Fixture-based counting test (logic, not live numbers)

**Files:**
- Create: `tests/test_catalog_counts_fixture.py`
- Create: `tests/fixtures/mini_catalog/references/blocks/frame.md`
- Create: `tests/fixtures/mini_catalog/references/blocks/INDEX.md`
- Create: `tests/fixtures/mini_catalog/references/channels.md`

- [ ] **Step 1: Write the failing fixture test**

Create `tests/test_catalog_counts_fixture.py`:

```python
"""Counting logic verified on a tiny known fixture — independent of live numbers."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import catalog_counts  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "mini_catalog"


def test_blocks_counts_two_and_excludes_index():
    # fixture has 2 real blocks in frame.md and a decoy line in INDEX.md
    assert catalog_counts._count_blocks(FIX) == 2


def test_channels_counts_one():
    assert catalog_counts._count_channels(FIX) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_catalog_counts_fixture.py -q`
Expected: FAIL (fixture files don't exist → FileNotFoundError)

- [ ] **Step 3: Create the fixture files**

Create `tests/fixtures/mini_catalog/references/blocks/frame.md`:

```markdown
# Frame blocks

## F1 — `opening`
Some text.

## F2 — `context-setter`
More text.
```

Create `tests/fixtures/mini_catalog/references/blocks/INDEX.md` (decoy — must NOT be counted):

```markdown
# Index

## F1 — `opening`
This line looks like a block but lives in INDEX and must be excluded.
```

Create `tests/fixtures/mini_catalog/references/channels.md`:

```markdown
# Channels

## Каталог

#### 1. `web-general`
One channel.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_catalog_counts_fixture.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add tests/test_catalog_counts_fixture.py tests/fixtures/
git commit -m "test(docs-ssot): фикстура подтверждает логику счёта (2 блока, INDEX исключён, 1 канал)"
```

---

### Task 3: `phases.yaml` + stdlib parser `phases_manifest.py`

**Files:**
- Create: `phases.yaml` (repo root)
- Create: `scripts/phases_manifest.py`
- Create: `tests/test_phases_manifest.py`

- [ ] **Step 1: Create `phases.yaml`** — field values from SKILL.md:111-118 + runtime_verification.md:92.

> IMPLEMENTER NOTE: `name_ru` for phases 4/5/6 are the verbatim Russian names from
> SKILL.md:115-117. `name_en` for those three are translations (no English source
> name exists in the docs). Phases 1/2/3/3.5/6.5 are already English in the source.

```yaml
# Single source of truth for the deep-research workflow phases.
# Counts and phase lists in README/SKILL/docs are stamped FROM this file by
# scripts/stamp_docs.py. Edit phases here, then: python scripts/stamp_docs.py --write
#
# depth_gate = the MINIMUM depth at which the phase is mandatory.
#   shallow -> always mandatory.  medium -> mandatory for medium+deep.
#   deep    -> mandatory only for deep.
# model/effort = the MAIN-THREAD model. Phase 4/5 sub-agents use per-task routing.
phases:
  - id: "1"
    name_ru: "Reframing"
    name_en: "Reframing"
    model: opus
    effort: high
    depth_gate: shallow
  - id: "2"
    name_ru: "Genre & block selection"
    name_en: "Genre & block selection"
    model: sonnet
    effort: medium
    depth_gate: shallow
  - id: "3"
    name_ru: "Plan"
    name_en: "Plan"
    model: opus
    effort: medium
    depth_gate: shallow
  - id: "3.5"
    name_ru: "Capability Discovery"
    name_en: "Capability Discovery"
    model: sonnet
    effort: low
    depth_gate: deep
  - id: "4"
    name_ru: "Поиск"
    name_en: "Search"
    model: sonnet
    effort: medium
    depth_gate: shallow
  - id: "5"
    name_ru: "Скоринг + триангуляция"
    name_en: "Scoring + triangulation"
    model: sonnet
    effort: medium
    depth_gate: shallow
  - id: "6"
    name_ru: "Синтез + adversarial pass"
    name_en: "Synthesis + adversarial pass"
    model: opus
    effort: high
    depth_gate: shallow
  - id: "6.5"
    name_ru: "Verify"
    name_en: "Verify"
    model: haiku
    effort: low
    depth_gate: medium
  - id: "7"
    name_ru: "Refresh targets"
    name_en: "Refresh targets"
    model: sonnet
    effort: medium
    depth_gate: medium
```

- [ ] **Step 2: Write the failing manifest test** — create `tests/test_phases_manifest.py`:

```python
"""Tests for scripts/phases_manifest.py — loader + validator for phases.yaml."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import phases_manifest  # noqa: E402


def test_loads_nine_phases_in_order():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    assert [p["id"] for p in phases] == ["1", "2", "3", "3.5", "4", "5", "6", "6.5", "7"]


def test_every_phase_has_required_fields():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    required = {"id", "name_ru", "name_en", "model", "effort", "depth_gate"}
    for p in phases:
        assert required <= set(p), f"phase {p.get('id')} missing fields"


def test_ids_are_unique():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    ids = [p["id"] for p in phases]
    assert len(ids) == len(set(ids))


def test_models_and_efforts_are_valid():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    for p in phases:
        assert p["model"] in {"opus", "sonnet", "haiku"}
        assert p["effort"] in {"high", "medium", "low"}
        assert p["depth_gate"] in {"shallow", "medium", "deep"}


def test_missing_field_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text('phases:\n  - id: "1"\n    name_ru: x\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        phases_manifest.load_phases(bad)


def test_unparseable_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not a phases doc\n", encoding="utf-8")
    with pytest.raises(ValueError):
        phases_manifest.load_phases(bad)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_phases_manifest.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'phases_manifest'`

- [ ] **Step 4: Write `phases_manifest.py`** (stdlib-only parser; no PyYAML) — create `scripts/phases_manifest.py`:

```python
#!/usr/bin/env python3
"""Loader + validator for phases.yaml — single source of truth for workflow phases.

A tiny hand-rolled parser for the flat list-of-dicts schema we own, so the CI gate
needs no PyYAML dependency. Only this exact shape is supported:

    phases:
      - id: "1"
        name_ru: Reframing
        ...

Anything else raises ValueError.
"""
from __future__ import annotations

from pathlib import Path

REQUIRED = ("id", "name_ru", "name_en", "model", "effort", "depth_gate")


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if v and v[0] not in "\"'" and "#" in v:
        v = v.split("#", 1)[0].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def load_phases(path: Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not body or body[0].strip() != "phases:":
        raise ValueError(f"{path}: expected top-level 'phases:' key")

    phases: list[dict] = []
    current: dict | None = None
    for ln in body[1:]:
        stripped = ln.strip()
        if stripped.startswith("- "):
            if current is not None:
                phases.append(current)
            current = {}
            stripped = stripped[2:].strip()
        if current is None:
            raise ValueError(f"{path}: list item expected, got: {ln!r}")
        if ":" not in stripped:
            raise ValueError(f"{path}: expected 'key: value', got: {ln!r}")
        key, _, val = stripped.partition(":")
        current[key.strip()] = _strip_quotes(val)
    if current is not None:
        phases.append(current)

    if not phases:
        raise ValueError(f"{path}: no phases found")
    for p in phases:
        missing = [f for f in REQUIRED if f not in p]
        if missing:
            raise ValueError(f"{path}: phase {p.get('id', '?')} missing {missing}")
    return phases


if __name__ == "__main__":
    import json

    print(json.dumps(load_phases(Path(__file__).resolve().parents[1] / "phases.yaml"), indent=2))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_phases_manifest.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Sanity-run**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/phases_manifest.py`
Expected: JSON array of 9 phase objects, ids "1" … "7".

- [ ] **Step 7: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add phases.yaml scripts/phases_manifest.py tests/test_phases_manifest.py
git commit -m "feat(docs-ssot): phases.yaml + stdlib-parser (9 phases, depth_gate)"
```

---

### Task 4: Wire `pytest` into requirements + full-suite green

**Files:**
- Modify: `scripts/requirements.txt`

- [ ] **Step 1: Read current requirements**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && cat scripts/requirements.txt`
Expected: a single line `requests>=2.31.0` (or similar).

- [ ] **Step 2: Append pytest** (Edit, preserving the existing line). Add to `scripts/requirements.txt`:

```
pytest>=8.0
```

- [ ] **Step 3: Run the whole suite green**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/ -q`
Expected: PASS (10 passed — 2 golden + 2 fixture + 6 manifest)

- [ ] **Step 4: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add scripts/requirements.txt
git commit -m "chore(docs-ssot): pytest in requirements for CI test step"
```

---

**Group A complete.** Ground-truth extractor + phases manifest exist, 10 tests green, zero doc content changed.

## Group B — The stamper, markers, and first stamp

### Task 5: `stamp_docs.py` core + unit tests (on temp files)

The stamper is the heart. It is developed and tested entirely against temp files in
this task — NO real doc is touched until Task 6. It exposes:
- `render_values(repo) -> dict[str,str]` — maps every `gen:KEY` to its rendered string.
- `stamp_text(text, values, *, path) -> str` — rewrites all marker spans in one string.
- `run(repo, targets, *, write) -> int` — orchestrates; returns exit code (0 ok, 1 drift).

**Marker grammar:** `<!--gen:KEY-->...anything...<!--/gen-->`. KEY is one of the keys in
`render_values`. The span between the open and the matching `<!--/gen-->` is replaced.

**Keys (the full set):**
- `count:blocks`, `count:channels`, `count:stat_sources`, `count:api`, `count:genres`,
  `count:phases` → the integer as a string.
- `count:phases` = number of phases in the manifest (9).
- `phases:list:ru`, `phases:list:en` → `Reframing → Genre & block selection → … → Refresh targets`
  (names joined by ` → `, in manifest order).
- `phases:table:en` → the full README markdown table rows (one row per phase).

**Files:**
- Create: `scripts/stamp_docs.py`
- Create: `tests/test_stamp_docs.py`

- [ ] **Step 1: Write the failing stamper unit tests**

Create `tests/test_stamp_docs.py`:

```python
"""Tests for scripts/stamp_docs.py — the marker stamper. All on temp files."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import stamp_docs  # noqa: E402

VALUES = {"count:blocks": "103", "count:phases": "9"}


def test_stamps_between_markers_only():
    src = "Library has <!--gen:count:blocks-->75<!--/gen--> blocks. Keep this."
    out = stamp_docs.stamp_text(src, VALUES, path="x")
    assert out == "Library has <!--gen:count:blocks-->103<!--/gen--> blocks. Keep this."


def test_idempotent():
    src = "n=<!--gen:count:blocks-->103<!--/gen-->"
    once = stamp_docs.stamp_text(src, VALUES, path="x")
    twice = stamp_docs.stamp_text(once, VALUES, path="x")
    assert once == twice == "n=<!--gen:count:blocks-->103<!--/gen-->"


def test_multiple_markers_same_text():
    src = "<!--gen:count:blocks-->0<!--/gen--> and <!--gen:count:phases-->0<!--/gen-->"
    out = stamp_docs.stamp_text(src, VALUES, path="x")
    assert out == "<!--gen:count:blocks-->103<!--/gen--> and <!--gen:count:phases-->9<!--/gen-->"


def test_unbalanced_marker_raises():
    src = "open <!--gen:count:blocks-->75 but no close"
    with pytest.raises(ValueError, match="unbalanced|unclosed"):
        stamp_docs.stamp_text(src, VALUES, path="x")


def test_unknown_key_raises():
    src = "<!--gen:count:bogus-->x<!--/gen-->"
    with pytest.raises(ValueError, match="unknown key"):
        stamp_docs.stamp_text(src, VALUES, path="x")


def test_render_values_has_all_keys():
    v = stamp_docs.render_values(REPO)
    for k in ("count:blocks", "count:channels", "count:stat_sources", "count:api",
              "count:genres", "count:phases", "phases:list:ru", "phases:list:en",
              "phases:table:en"):
        assert k in v
    assert v["count:blocks"] == "103"
    assert v["count:phases"] == "9"


def test_check_mode_detects_drift(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->75<!--/gen-->", encoding="utf-8")
    rc = stamp_docs.run(REPO, [f], write=False)
    assert rc == 1  # 75 != 103 → drift


def test_write_mode_fixes_and_check_passes(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->75<!--/gen-->", encoding="utf-8")
    assert stamp_docs.run(REPO, [f], write=True) == 0
    assert "103" in f.read_text(encoding="utf-8")
    assert stamp_docs.run(REPO, [f], write=False) == 0  # now synced


def test_zero_count_refused(monkeypatch, tmp_path):
    # if a regex returns 0, render_values must refuse (never stamp zero silently)
    monkeypatch.setattr(stamp_docs.catalog_counts, "counts", lambda repo: {
        "blocks": 0, "channels": 29, "stat_sources": 461, "api": 39, "genres": 6})
    with pytest.raises(ValueError, match="suspicious|zero"):
        stamp_docs.render_values(REPO)


def test_unused_key_warns_not_fails(tmp_path, capsys):
    # a doc using only ONE key → the other keys are "stamped nowhere" → WARNING, rc 0
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->103<!--/gen-->", encoding="utf-8")
    rc = stamp_docs.run(REPO, [f], write=False)
    out = capsys.readouterr().out
    assert rc == 0  # warning, not drift
    assert "stamped nowhere" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_stamp_docs.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'stamp_docs'`

- [ ] **Step 3: Write `stamp_docs.py`**

Create `scripts/stamp_docs.py`:

```python
#!/usr/bin/env python3
"""Stamp generated values into doc marker spans, or check for drift.

Truth sources: catalog_counts.counts() (numbers) + phases_manifest (phases).
Docs carry markers:  <!--gen:KEY-->...<!--/gen-->  — the span is rewritten.

Usage:
    python scripts/stamp_docs.py --write    # rewrite all target docs in place
    python scripts/stamp_docs.py --check    # exit 1 + diff if any doc is stale

The human runs --write and commits; CI runs --check.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

import catalog_counts
import phases_manifest

OPEN_RE = re.compile(r"<!--gen:([a-z0-9:_]+)-->")
CLOSE = "<!--/gen-->"

# Target docs, relative to repo root. (Marker placement happens in Task 6.)
TARGETS = [
    "README.md",
    "SKILL.md",
    "CONTRIBUTING.md",
    "docs/index.html",
    "docs/_config.yml",
    "runner/DESIGN.md",
    "references/blocks/INDEX.md",
    "references/channels.md",
    "references/stat_sources/INDEX.md",
    "references/workflow.md",
    "eval/README.md",
    "QUICKSTART.md",
]


def render_values(repo: Path) -> dict[str, str]:
    c = catalog_counts.counts(repo)
    for k, v in c.items():
        if v <= 0:
            raise ValueError(f"count {k}={v} is suspicious (zero) — refusing to stamp")
    phases = phases_manifest.load_phases(repo / "phases.yaml")
    if not phases:
        raise ValueError("no phases — refusing to stamp")

    list_ru = " → ".join(p["name_ru"] for p in phases)
    list_en = " → ".join(p["name_en"] for p in phases)
    table_rows = "\n".join(
        f"| **{p['id']}** | **{p['name_en']}** | {p['model']} / {p['effort']} |"
        for p in phases
    )

    return {
        "count:blocks": str(c["blocks"]),
        "count:channels": str(c["channels"]),
        "count:stat_sources": str(c["stat_sources"]),
        "count:api": str(c["api"]),
        "count:genres": str(c["genres"]),
        "count:phases": str(len(phases)),
        "phases:list:ru": list_ru,
        "phases:list:en": list_en,
        "phases:table:en": table_rows,
    }


def stamp_text(text: str, values: dict[str, str], *, path: str) -> str:
    out = []
    pos = 0
    for m in OPEN_RE.finditer(text):
        key = m.group(1)
        if key not in values:
            raise ValueError(f"{path}: unknown key 'gen:{key}'")
        close_at = text.find(CLOSE, m.end())
        if close_at == -1:
            raise ValueError(f"{path}: unbalanced marker 'gen:{key}' (no {CLOSE})")
        out.append(text[pos:m.end()])
        out.append(values[key])
        pos = close_at  # CLOSE itself re-emitted on next slice
    out.append(text[pos:])
    return "".join(out)


def run(repo: Path, targets: list[Path], *, write: bool) -> int:
    values = render_values(repo)
    seen_keys: set[str] = set()
    drift = 0
    for path in targets:
        p = Path(path)
        if not p.is_absolute():
            p = repo / p
        if not p.exists():
            continue  # a target may not exist yet (e.g. QUICKSTART before Task 9)
        original = p.read_text(encoding="utf-8")
        seen_keys.update(OPEN_RE.findall(original))
        stamped = stamp_text(original, values, path=str(p))
        if stamped != original:
            if write:
                p.write_text(stamped, encoding="utf-8")
            else:
                drift = 1
                print(f"DRIFT: {p}")
                diff = difflib.unified_diff(
                    original.splitlines(), stamped.splitlines(),
                    fromfile=f"{p} (committed)", tofile=f"{p} (generated)", lineterm="")
                print("\n".join(diff))
    # Spec: a generator key that appears in NO doc is a likely-forgotten marker → warn (not fail).
    unused = sorted(set(values) - seen_keys)
    for key in unused:
        print(f"WARNING: key 'gen:{key}' is stamped nowhere (forgotten marker?)")
    return drift


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="rewrite docs in place")
    g.add_argument("--check", action="store_true", help="exit 1 on drift")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    rc = run(args.root, [args.root / t for t in TARGETS], write=args.write)
    if args.check and rc:
        print("\nDocs are stale. Run: python scripts/stamp_docs.py --write")
    elif args.write:
        print("Stamped.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/test_stamp_docs.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add scripts/stamp_docs.py tests/test_stamp_docs.py
git commit -m "feat(docs-ssot): stamp_docs.py — штамповщик маркеров (--write/--check), на temp-тестах"
```

### Task 6: Place markers around every count + phase site

This task inserts `<!--gen:KEY-->VALUE<!--/gen-->` around each existing number/phrase.
The VALUE you wrap is the *current* text (even if wrong) — the stamp in Task 7 corrects
it. Wrapping current text first keeps each Edit a pure insertion, easy to verify.

**The authoritative site list** (verified by line on 2026-06-13; line numbers drift as
you edit, so match on surrounding text, not line number). Work file-by-file, top-to-bottom
within a file so earlier edits don't shift later matches.

**Critical gotchas (from fact-finding):**
- `references/blocks/INDEX.md` says **76** (not 75) at 3 sites — wrap the `76`.
- `docs/index.html` has ~9 lines bundling several counts (75 + 280+ + 30+ + 29 + 7-phase)
  in ONE string (meta.description EN/RU, faq.a5 EN/RU, inside.intro EN/RU). Wrap each
  number independently within the line — multiple markers per line is fine.
- `docs/index.html` lines 10-11 badge URLs containing `75` are NOT count sites — skip.
- README.md lines 10-11 `75` inside badge URLs (`d97757`) — skip.
- `docs/index.html` pairs: `280+` with `33 categories` (1167/1432/1575) and `75` with
  `/ 10 categories` (1139/1424/1567) — wrap only the catalog count, leave `33`/`10`.
- Channels: only `references/channels.md:1,12` and `references/genres.md:14` say **28** —
  wrap the `28`. README/docs already say 29 correctly — wrap those too (they become
  `gen:count:channels`, value already 29, so Task 7 leaves them unchanged).

- [ ] **Step 1: Blocks sites** — wrap each with `<!--gen:count:blocks-->N<!--/gen-->`:
  - `references/blocks/INDEX.md`: "76 блоков" (line ~3), "всех 76 блоков" (~27), "При 76 блоках" (~184) → wrap the `76`
  - `SKILL.md:~221` "индекс 75 блоков" → wrap `75`
  - `README.md`: "### 75 Report Blocks" (~157), "75 reusable blocks" (~390), "| 75 report blocks |" (~416), "**75 блоков**" (~447)
  - `runner/DESIGN.md:~12` "75 blocks"
  - `docs/_config.yml:~6` "75 report blocks"
  - `CONTRIBUTING.md:~42` "has 75 blocks"
  - `docs/index.html`: the kpi-num `<div class="kpi-num">75</div>` (~1005), `inside.f1.num` "75 / 10 categories" (~1139 EN, ~1567 RU → wrap only `75`), and each of "75 report blocks"/"75 reusable blocks"/"75 блоков"/"75 блоков отчёта" inside meta/intro/faq strings (lines ~7, 1132, 1306, 1350, 1423, 1477, 1493, 1566, 1620)

- [ ] **Step 2: Channels sites** — wrap with `<!--gen:count:channels-->N<!--/gen-->`:
  - `references/channels.md`: "каталог 28 каналов" (~1), "## Каталог 28 каналов" (~12) → wrap `28`
  - `references/genres.md:~14` "каталог 28 каналов" → wrap `28`
  - `README.md`: "29 named channels" (~76), "29 channels" (~141, ~417); `docs/index.html` "29 channels"/"29 именованных каналов"/"29 named channels" (~1107, 1132, 1413, 1423, 1556, 1566) → wrap `29`

- [ ] **Step 3: Stat-source sites** — wrap with `<!--gen:count:stat_sources-->N<!--/gen-->`:
  - `references/stat_sources/INDEX.md:~147` "Total source entries: 280+" → wrap `280+`
  - `README.md`: "280+ stat sources" (~76), "### 280+ Stat Sources" (~179), "280+ stat sources catalog" (~389), "| 280+ stat sources |" (~418), "**280+ статистических источников**" (~449), "280+ stat sources" (~141)
  - `docs/_config.yml:~6`, `runner/DESIGN.md:~12` "280+ sources"
  - `docs/index.html`: kpi-num `280+` (~1009), `inside.f3.num` "280+ sources · 33 categories" (~1167 EN, ~1575 RU → wrap only `280+`), and each "280+" in how.p4.desc/meta/intro/faq strings (~1107, 1132, 1306, 1350, 1413, 1423, 1477, 1493, 1556, 1566, 1620)

- [ ] **Step 4: API sites** — wrap with `<!--gen:count:api-->N<!--/gen-->`. NOTE the value
  form: docs say "30+" but truth is 39. Decide the rendered form NOW: wrap the numeric part
  and keep any "+". Since the stamp writes `39`, wrap "30" → becomes "39" (drop the "+", or
  keep "+" by wrapping only "30" and leaving "+" outside the marker: `<!--gen:count:api-->30<!--/gen-->+`).
  **Decision: wrap only the digits, leave the trailing `+` outside the marker** so "30+" → "39+".
  - `README.md`: "### 30+ API Endpoints" (~208 → `<!--gen:count:api-->30<!--/gen-->+ API Endpoints`), "30+ APIs weekly" (~225), "**30+ API endpoints**" (~450)
  - `SKILL.md:~224` "30+ API endpoints"
  - `docs/index.html`: kpi-num `30+` (~1013), `inside.f5.num` "30+ endpoints" (~1196, 1439, 1582), and "30+ APIs"/"30+ API endpoints"/"30+ API" in meta/intro/faq strings (~7, 1132, 1350, 1423, 1493, 1566)

- [ ] **Step 5: Genre sites** — wrap with `<!--gen:count:genres-->6<!--/gen-->` (already correct, so a no-op stamp; wrap for future protection):
  - `README.md:~446` "**6 жанров отчёта**", `SKILL.md:~220` "пресеты блоков 6 жанров", `eval/BENCHMARK.md:~14` "all 6 genres"

- [ ] **Step 6: Phase-count sites** — wrap with `<!--gen:count:phases-->N<!--/gen-->`. Truth=9 but most say "7"/"6". Wrap the number; Task 7 makes them all `9`:
  - `SKILL.md:~107` "Workflow — 7 фаз", `~218` "детали 7 фаз" → wrap `7`
  - `references/workflow.md:~1` "детали 6 фаз" → wrap `6`
  - `README.md:~133` "**7 phases**" → wrap `7`
  - `eval/README.md:~20` "все 6 фаз" → wrap `6`
  - `docs/_config.yml:~6` "7-phase" → wrap `7`
  - `docs/index.html`: "7-phase"/"7 фаз"/"из 7 фаз" everywhere (~7, 11, 983, 1306, 1350, 1360, 1477, 1493, 1503, 1620) → wrap `7`
  - **CAUTION** `SKILL.md:107` header reads "7 фаз (включая опциональную 3.5)" — after stamping to 9 the parenthetical is stale. Reword the prose around the marker to "(1–7, включая 3.5 и 6.5)" so it stays truthful. Same for README:133 intro if it implies a specific count in prose.

- [ ] **Step 7: Phase-list + table sites**:
  - `README.md:~445` "**7 фаз workflow**: Reframing → Genre → … → Synthesis" → replace the name chain with `<!--gen:phases:list:ru-->...<!--/gen-->` (wrap the existing chain)
  - `README.md` phases table (~135-143): it currently has 6 rows and DROPS Phase 7. Wrap the table-body rows region in `<!--gen:phases:table:en-->`...`<!--/gen-->`. After Task 7's stamp it will contain all 9 rows incl. Phase 7. Keep the header row (`| Phase | Name | ... |`) and separator OUTSIDE the markers; wrap only the data rows.

- [ ] **Step 8: Verify all markers are well-formed and keys are known** (dry `--check`; it will report DRIFT because numbers are still wrong, but it must NOT raise a marker/key error):

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/stamp_docs.py --check; echo "rc=$?"`
Expected: prints `DRIFT:` lines with diffs (75→103, 280+→461, etc.), `rc=1`. **No** `ValueError`/`unknown key`/`unbalanced` traceback. If you see a traceback, fix the offending marker before proceeding.

- [ ] **Step 9: Commit the markers (still showing old numbers)**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add -A
git commit -m "chore(docs-ssot): расставить gen-маркеры вокруг счётчиков и фаз (числа ещё старые)"
```

---

### Task 7: First stamp — впечатать правду

- [ ] **Step 1: Run the stamp**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/stamp_docs.py --write`
Expected: prints `Stamped.`

- [ ] **Step 2: Verify check is now clean**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/stamp_docs.py --check; echo "rc=$?"`
Expected: no DRIFT lines, `rc=0`.

- [ ] **Step 3: Eyeball the diff** — confirm only numbers/phase-lists changed, prose intact

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && git --no-pager diff --stat && git --no-pager diff README.md | head -60`
Expected: 75→103, 76→103, 280+→461 (i.e. `280` inside marker → `461`), 28→29, 30→39, phase counts →9, README table gains a Phase 7 row. No prose sentences mangled.

- [ ] **Step 4: Run full suite + build-style sanity**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/ -q`
Expected: PASS (20 passed — 10 from Group A + 10 stamper).

- [ ] **Step 5: Commit the truth**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add -A
git commit -m "docs(docs-ssot): впечатать ground-truth (блоки 75→103, источники 280+→461, каналы 28→29, API 30+→39, фазы→9, вернуть Phase 7 в таблицу README)"
```

---

## Group C — CI gate

### Task 8: Add test + stamp-check steps to `validate.yml`

**Files:**
- Modify: `.github/workflows/validate.yml`

- [ ] **Step 1: Read the current `structure-and-budget` job**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && sed -n '1,35p' .github/workflows/validate.yml`
Expected: see the `structure-and-budget` job with steps `setup-python`, `pip install -r scripts/requirements.txt`, `context_budget.py --ci`, `validate_structure.py ... || true`.

- [ ] **Step 2: Add two steps after the existing python steps** (Edit). Insert after the `context_budget.py --ci` step, matching its indentation:

```yaml
      - name: Run unit tests
        run: python -m pytest tests/ -q
      - name: Check docs are in sync with sources
        run: python scripts/stamp_docs.py --check
```

- [ ] **Step 3: Validate the workflow YAML locally**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -c "import sys; print('PyYAML' if __import__('importlib').util.find_spec('yaml') else 'no-yaml')"`
If `no-yaml`: skip strict YAML parse, instead eyeball indentation with `sed -n '15,40p' .github/workflows/validate.yml` and confirm the two new steps align with sibling `- name:` entries.
Expected: the two new steps sit at the same indent as the existing steps under `steps:`.

- [ ] **Step 4: Dry-run both commands exactly as CI will**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/ -q && python scripts/stamp_docs.py --check && echo "CI-OK"`
Expected: tests pass, no drift, prints `CI-OK`.

- [ ] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add .github/workflows/validate.yml
git commit -m "ci(docs-ssot): pytest + stamp_docs.py --check на каждый PR (гейт от рассинхрона)"
```

---

## Group D — Quickstart

### Task 9: `QUICKSTART.md` for the newcomer

**Files:**
- Create: `QUICKSTART.md`
- Modify: `README.md` (add a link near the top)

- [ ] **Step 1: Write `QUICKSTART.md`** (counts use markers so they stay honest)

Create `QUICKSTART.md`:

```markdown
# Quickstart

Get your first documented research run in ~5 minutes.

## 1. Install the skill

This is a Claude Code skill — a folder of methodology Claude reads, not a binary.

```bash
git clone https://github.com/Socialpranker/claude-deep-research.git
# point your Claude Code skills at this folder (see your skills config),
# or copy it into your skills directory.
```

No build, no dependencies for *using* the skill — Claude runs it with its own
WebSearch / WebFetch / sub-agent tools. (Python is only for the maintainer-side
catalog/eval checks; you don't need it to run research.)

## 2. Invoke it

In a Claude Code session, just ask in natural language — any of these trigger it:

> «проведи ресёрч: <your question>»  ·  "deep research <your question>"  ·  `/deep-research`

Claude will: restate your question, pick a report genre, write a `plan.md`, search
across <!--gen:count:channels-->29<!--/gen--> channels and <!--gen:count:stat_sources-->461<!--/gen-->
curated stat sources (+ <!--gen:count:api-->39<!--/gen-->+ APIs), score and triangulate every
source, synthesize with an adversarial self-critique, and verify citations.

## 3. What you get

A folder (default `~/deep-research/<slug>/`) you can return to months later:

```
<slug>/
├── plan.md              # the research plan: question, hypotheses, acceptance criteria
├── sources/             # one file per source — verbatim quotes + credibility scoring
│   ├── 01_<slug>.md
│   └── ...
├── <date>_<genre>.md    # the final report — every claim traces to a source file
└── refresh_targets.md   # entities/numbers to re-check later via `update <slug>`
```

Every claim cites a source file; every source carries Credibility / Recency / Bias
scores. That's the point: not an answer you have to trust, but an investigation you
can audit.

## Next steps

- Full methodology: [`SKILL.md`](SKILL.md) — the <!--gen:count:phases-->9<!--/gen-->-phase workflow.
- The catalog: [`references/`](references/) — <!--gen:count:blocks-->103<!--/gen--> report
  blocks, <!--gen:count:genres-->6<!--/gen--> genres.
- Want to add sources or APIs? [`CONTRIBUTING.md`](CONTRIBUTING.md).
```

- [ ] **Step 2: Add a Quickstart link near the top of README.md** (Edit). Find the first heading/badges block and insert, adapting to the exact surrounding text:

```markdown
> **New here?** Start with the [Quickstart](QUICKSTART.md) — install → invoke → first result in ~5 min.
```

- [ ] **Step 3: Stamp the new file + verify clean**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python scripts/stamp_docs.py --write && python scripts/stamp_docs.py --check; echo "rc=$?"`
Expected: `Stamped.` then no drift, `rc=0` (QUICKSTART markers already hold the right numbers, so --write is a no-op there; the point is to prove the new file passes the gate).

- [ ] **Step 4: Full suite green**

Run: `cd /Users/ivanteresenko/Downloads/claude-deep-research && python -m pytest tests/ -q`
Expected: PASS (20 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/ivanteresenko/Downloads/claude-deep-research
git add QUICKSTART.md README.md
git commit -m "docs(docs-ssot): QUICKSTART — установка→вызов→результат за 5 минут (счётчики под маркерами)"
```

---

## Done criteria (verify before opening a PR)

- [ ] `python -m pytest tests/ -q` → all green (19 tests).
- [ ] `python scripts/stamp_docs.py --check` → `rc=0`, no DRIFT.
- [ ] Hand-edit any count in a doc (e.g. change a `103` to `104`), run `--check` → it
      goes red and prints the diff; revert.
- [ ] README phases table shows all 9 phases including Phase 7 (Refresh targets).
- [ ] No prose sentence was mangled by the stamp (skim `git diff` of the truth commit).
- [ ] `QUICKSTART.md` exists and is linked from README.

## PR shaping

The truth-stamp commit (Task 7) touches `docs/index.html` heavily (~30 sites) — the
total diff will exceed the ~400-line guideline. Two acceptable options, decide at PR time:
- **One PR** with all 4 commit-groups (logic / markers+truth / CI / quickstart), noting in
  the PR body that the large diff is mechanical number-stamping (point reviewers at the
  generator commit + the marker commit, not the stamp).
- **Two PRs:** PR1 = Groups A+B+C (the machinery + first stamp + gate), PR2 = Group D
  (quickstart). PR1 is the one that's large-but-mechanical.

Do NOT push or open the PR without the user's go-ahead.

