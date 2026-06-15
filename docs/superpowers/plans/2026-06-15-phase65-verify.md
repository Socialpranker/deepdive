# Phase 6.5 — Verify (citation checking) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Подключить существующий `eval/check_citations.py` к оркестратору как Phase 6.5 — после `synthesize()` запустить проверку цитат (subprocess, best-effort) и заменить плейсхолдер в отчёте реальной метрикой.

**Architecture:** Чистый `runner/verify.py` (`render_verification(citations|None) -> str`) — без сети, тестируется инъекцией dict. Тонкий `Orchestrator.verify(s)` зовёт `check_citations.py` как subprocess (`check=False`, best-effort), читает `.verify/citations.json`, заменяет уникальный плейсхолдер в `<date>_<genre>.md`. eval-код не трогаем (CI/score_run.py зовут его как CLI). Без блокировки по порогам и red-flag-действий.

**Tech Stack:** Python 3 (subprocess, json, sys), pytest (monkeypatch subprocess.run для оффлайн-тестов), ruff.

**Spec:** [docs/superpowers/specs/2026-06-15-phase65-verify-design.md](../specs/2026-06-15-phase65-verify-design.md)

**Факты из кода (выписаны дословно):**
- `check_citations.py` JSON: `{"research_dir", "origin", "citation_integrity": float, "results": [{"sid","url","access","status","alive","checkable","title_match","red_flag"}]}`. Готового count нет — рендер считает сам.
- CLI: `--research-dir` (required), `--out` (базовый путь БЕЗ расширения → пишет `<out>.json`), `--json`, `--strict`.
- Плейсхолдер в `synthesize()`: `> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**`. Отчёт: `<date>_<genre>.md`, `date = dt.date.today().isoformat()`.
- subprocess-прецедент: `eval/score_run.py:56` — `[sys.executable, str(EVAL_DIR/"check_citations.py"), "--research-dir", ..., "--out", ..., "--json"]`, читает `out_base.with_suffix(".json")`.
- `import subprocess/sys/json` в orchestrator.py ОТСУТСТВУЮТ — добавить. try/except ImportError для `runner.*` — существующий паттерн.

---

## File Structure

- **`runner/verify.py`** (create) — чистая `PLACEHOLDER` const + `render_verification(citations: dict | None) -> str`. Без сети/subprocess. Паттерн `scoring.py`.
- **`runner/orchestrator.py`** (modify) — `import subprocess, sys, json`; try/except import `render_verification`/`PLACEHOLDER`; новый метод `verify(s)`; `run()` зовёт `verify()` после `synthesize()`.
- **`tests/test_verify.py`** (create) — юнит-тесты `render_verification` (инъекция dict / None).
- **`tests/test_orchestrator_verify.py`** (create) — интеграция с monkeypatch'нутым `subprocess.run` (оффлайн).

---

### Task 1: `runner/verify.py` — `render_verification` + `PLACEHOLDER`

**Files:**
- Create: `runner/verify.py`
- Test: `tests/test_verify.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verify.py
from runner.verify import render_verification, PLACEHOLDER

def test_placeholder_matches_synthesize_string():
    # the constant must equal the exact line synthesize() writes, or replace() misses
    assert PLACEHOLDER == "> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**"

def test_render_none_is_unavailable():
    out = render_verification(None)
    assert "verification unavailable" in out

def test_render_counts_verified_and_red_flags():
    citations = {
        "citation_integrity": 0.8,
        "results": [
            {"sid": "s01", "alive": True, "red_flag": False},
            {"sid": "s02", "alive": True, "red_flag": False},
            {"sid": "s03", "alive": False, "red_flag": True},
        ],
    }
    out = render_verification(citations)
    assert "2/3 verified" in out      # 2 alive of 3 total
    assert "1 red flag" in out
    assert "Citation integrity" in out

def test_render_zero_red_flags_plural():
    citations = {"citation_integrity": 1.0,
                 "results": [{"sid": "s01", "alive": True, "red_flag": False}]}
    out = render_verification(citations)
    assert "1/1 verified" in out
    assert "0 red flags" in out

def test_render_empty_results():
    citations = {"citation_integrity": 0.0, "results": []}
    out = render_verification(citations)
    assert "0/0 verified" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_verify.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner.verify'`

- [ ] **Step 3: Write minimal implementation**

```python
# runner/verify.py
"""Phase 6.5 — pure verification-rendering logic (no network, no subprocess).

The actual citation check runs in eval/check_citations.py (invoked as a subprocess
by Orchestrator.verify). This module only turns that check's JSON output into the
metric line that replaces the synthesize() placeholder. Mirrors runner.scoring:
deterministic rendering separate from the side-effecting caller.
"""
from __future__ import annotations

import datetime as dt

# Must match the exact line written by Orchestrator.synthesize(); replace() depends on it.
PLACEHOLDER = "> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**"


def render_verification(citations: dict | None) -> str:
    """Turn check_citations.py JSON (or None on failure) into the report metric block.
    None -> 'verification unavailable' (best-effort: offline / checker error)."""
    if citations is None:
        return (
            "> **Citation integrity: verification unavailable — "
            "check_citations.py did not produce a report (offline or error).**"
        )
    results = citations.get("results", [])
    total = len(results)
    verified = sum(1 for r in results if r.get("alive"))
    red_flags = sum(1 for r in results if r.get("red_flag"))
    flag_word = "red flag" if red_flags == 1 else "red flags"
    date = dt.date.today().isoformat()
    return (
        f"> **Citation integrity: {verified}/{total} verified · {red_flags} {flag_word}**\n"
        f"> Verified {date} via check_citations.py · detail: .verify/citations.md"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_verify.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add runner/verify.py tests/test_verify.py
git commit -m "feat(verify): чистый render_verification + PLACEHOLDER (Phase 6.5)"
```

---

### Task 2: `Orchestrator.verify()` — subprocess + замена плейсхолдера

**Files:**
- Modify: `runner/orchestrator.py` (imports; new method `verify`)
- Test: `tests/test_orchestrator_verify.py`

**Context:** `check_citations.py` lives at `<repo>/eval/check_citations.py`. The orchestrator file is at `<repo>/runner/orchestrator.py`, so the eval dir is `Path(__file__).parent.parent / "eval"`. `--out` is a base path without extension → pass `s.dir / ".verify" / "citations"`, read back `....with_suffix(".json")`. The `.verify/` dir may not exist — create it before the subprocess. The subprocess must be `check=False` (best-effort) and wrapped to catch `FileNotFoundError`/`OSError`. Tests monkeypatch `subprocess.run` so NO real HTTP happens.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_verify.py
import json
import subprocess
from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider

def _prep(tmp_path, depth="medium"):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="does X cause Y", depth=depth, root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    o.search(s)
    o.score(s)
    o.synthesize(s)
    return o, s

def _report_path(s):
    import datetime as dt
    return s.dir / f"{dt.date.today().isoformat()}_{s.genre}.md"

def test_verify_replaces_placeholder_with_metric(tmp_path, monkeypatch):
    o, s = _prep(tmp_path)
    # fake the checker: write a citations.json instead of doing HTTP
    def fake_run(cmd, **kwargs):
        out_idx = cmd.index("--out") + 1
        base = cmd[out_idx]
        from pathlib import Path
        jp = Path(base).with_suffix(".json")
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps({
            "citation_integrity": 1.0,
            "results": [{"sid": "s01", "alive": True, "red_flag": False}],
        }), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)

    o.verify(s)
    report = _report_path(s).read_text(encoding="utf-8")
    assert "1/1 verified" in report
    assert "pending — run eval/check_citations.py" not in report  # placeholder gone

def test_verify_unavailable_when_no_json(tmp_path, monkeypatch):
    o, s = _prep(tmp_path)
    # checker "runs" but produces no json
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    o.verify(s)
    report = _report_path(s).read_text(encoding="utf-8")
    assert "verification unavailable" in report

def test_verify_survives_subprocess_oserror(tmp_path, monkeypatch):
    o, s = _prep(tmp_path)
    def boom(cmd, **kw):
        raise OSError("no python")
    monkeypatch.setattr(subprocess, "run", boom)
    o.verify(s)  # must NOT raise
    report = _report_path(s).read_text(encoding="utf-8")
    assert "verification unavailable" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_orchestrator_verify.py::test_verify_replaces_placeholder_with_metric -q`
Expected: FAIL — `AttributeError: 'Orchestrator' object has no attribute 'verify'`

- [ ] **Step 3: Write minimal implementation**

(a) Add stdlib imports to `runner/orchestrator.py` (with `import argparse`/`import os`/`import re`):

```python
import json
import subprocess
import sys
```

(b) Add the verify import following the existing try/except ImportError pattern:

```python
try:
    from .verify import PLACEHOLDER, render_verification
except ImportError:  # run as a script
    from verify import PLACEHOLDER, render_verification
```

(c) Add the method to `Orchestrator`, AFTER `synthesize()` and BEFORE `run()`:

```python
    # --- Phase 6.5: verify (citation checking) -----------------------------
    def verify(self, s: RunState) -> None:
        verify_dir = s.dir / ".verify"
        verify_dir.mkdir(exist_ok=True)
        out_base = verify_dir / "citations"
        checker = Path(__file__).parent.parent / "eval" / "check_citations.py"
        citations = None
        try:
            subprocess.run(
                [sys.executable, str(checker),
                 "--research-dir", str(s.dir), "--out", str(out_base), "--json"],
                check=False,
            )
        except (FileNotFoundError, OSError):
            citations = None
        json_path = out_base.with_suffix(".json")
        if json_path.exists():
            try:
                citations = json.loads(json_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                citations = None
        block = render_verification(citations)

        date = dt.date.today().isoformat()
        report_path = s.dir / f"{date}_{s.genre}.md"
        text = report_path.read_text(encoding="utf-8")
        if PLACEHOLDER in text:
            text = text.replace(PLACEHOLDER, block)
        else:
            text = text.rstrip() + "\n\n" + block + "\n"
        report_path.write_text(text, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_orchestrator_verify.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py tests/test_orchestrator_verify.py
git commit -m "feat(orchestrator): Phase 6.5 verify() — subprocess check_citations + замена плейсхолдера"
```

---

### Task 3: подключить `verify()` в `run()`

**Files:**
- Modify: `runner/orchestrator.py` (`run()`)
- Test: `tests/test_orchestrator_verify.py`

**Context:** Current `run()` ends with `self.synthesize(s)` then `return s.dir`. Insert `self.verify(s)` between them. Phase 6.5 runs on all depths (no gate). Since `run()` calls the REAL subprocess (which does HTTP), the run-level test must monkeypatch `subprocess.run` to stay offline/deterministic.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_orchestrator_verify.py
def test_run_invokes_verify_offline(tmp_path, monkeypatch):
    # keep it offline: checker is a no-op producing no json -> 'unavailable'
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    o = Orchestrator(DryRunProvider())
    out_dir = o.run("does X cause Y", "medium", tmp_path)
    import datetime as dt
    # find the report file
    reports = list(out_dir.glob("*_*.md"))
    report = next(p for p in reports if dt.date.today().isoformat() in p.name)
    text = report.read_text(encoding="utf-8")
    assert "pending — run eval/check_citations.py" not in text  # placeholder replaced
    assert "Citation integrity" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_orchestrator_verify.py::test_run_invokes_verify_offline -q`
Expected: FAIL — placeholder still present (run() doesn't call verify yet)

- [ ] **Step 3: Write minimal implementation**

In `run()`, insert `self.verify(s)` between `self.synthesize(s)` and `return s.dir`:

```python
        self.synthesize(s)
        self.verify(s)
        return s.dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_orchestrator_verify.py -q`
Expected: PASS (4 passed)

Also confirm no regression:

Run: `python3 -m pytest tests/ -m "not live" -q`
Expected: PASS (all green)

- [ ] **Step 5: Commit**

```bash
git add runner/orchestrator.py tests/test_orchestrator_verify.py
git commit -m "feat(orchestrator): run() зовёт Phase 6.5 verify() после synthesize()"
```

---

### Task 4: финальная верификация

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -m "not live" -q`
Expected: PASS (all green, live deselected)

- [ ] **Step 2: Run ruff (CI gate)**

Run: `ruff check runner/ tests/`
Expected: no violations

- [ ] **Step 3: Re-read the spec line by line**

Open `docs/superpowers/specs/2026-06-15-phase65-verify-design.md` and confirm each requirement maps to a shipped change. Note any gap explicitly.

- [ ] **Step 4: (optional) live smoke — real checker on a run**

```bash
python3 -c "
import tempfile, pathlib
from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider
d = pathlib.Path(tempfile.mkdtemp())
out = Orchestrator(DryRunProvider()).run('impact of remote work', 'medium', d)
import datetime as dt
rep = next(p for p in out.glob('*_*.md') if dt.date.today().isoformat() in p.name)
print(rep.read_text())
print('--- .verify/ ---', list((out/'.verify').glob('*')) if (out/'.verify').exists() else 'none')
"
```
Expected: report shows a Citation integrity line (real metric if network up, else "unavailable"); `.verify/citations.{json,md}` may exist. Note: DryRun sources point at `example.com/source-...` URLs — checker resolves them live; result depends on network.

---

## Self-Review notes

- **Spec coverage:** subprocess invocation (T2) ✓; best-effort check=False + OSError catch (T2, T2 test `boom`) ✓; render None→unavailable (T1) ✓; counts verified/red flags from results (T1, render sums alive/red_flag) ✓; replace placeholder / append fallback (T2) ✓; pure module split (T1 verify.py) ✓; no gate / all depths (T3) ✓; eval-code untouched (no task modifies check_citations.py) ✓; offline tests via monkeypatch subprocess (T2/T3) ✓.
- **Narrow boundary:** no threshold blocking, no red-flag actions — neither appears in any task. ✓
- **Type consistency:** `render_verification(citations: dict | None) -> str` signature consistent T1↔T2; `PLACEHOLDER` const referenced identically in T1 (definition), T2 (replace); JSON keys (`results`, `alive`, `red_flag`, `citation_integrity`) match the dataclass `CiteResult` fields verified from check_citations.py.
- **Known network caveat:** `--out` base-path → `.json` suffix confirmed; `.verify/` created with `mkdir(exist_ok=True)` before subprocess (T2). DryRun URLs are live-resolved by the real checker — that's why run-level tests monkeypatch subprocess (noted in T3 context).
