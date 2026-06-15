# Phase 7 — Refresh targets generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Финальная фаза прогона пишет `<slug>/refresh_targets.md` — точку входа для будущего `update <slug>`, извлекая данные из `RunState` (не из scaffold-отчёта).

**Architecture:** Чистый модуль `runner/refresh.py` (pure extract + render, без сети/I/O) + метод `Orchestrator.refresh(s)` (читает `s`, пишет файл) после `verify()` в `run()`. Зеркалит паттерн scoring/capabilities/verify.

**Tech Stack:** Python 3, stdlib only (`re`, `datetime`, `urllib.parse`); pytest + DryRunProvider для оффлайн-тестов.

**Design doc:** `docs/superpowers/specs/2026-06-15-phase7-refresh-design.md`

---

## Контекст для имплементера (прочитать до старта)

Проект — оркестратор deep-research. Прогон (`Orchestrator.run()` в `runner/orchestrator.py`) идёт по фазам: reframe → genre → plan → capabilities → search → score → synthesize → verify → **(сюда встаёт refresh)** → return. Состояние пропагируется через `RunState` (dataclass).

**Точные факты, на которые опирается план (проверены в коде):**

`s.sources[i]` после Phase 5 — dict с ключами:
```python
{"id": "s01", "url": "https://...", "title": "...", "claim": "...",
 "type": "Primary|Academic|...", "credibility": 3, "recency": 4,
 "bias": 5, "total": 12, "hypothesis_evidence": {"H1": "supports"}}
```
Внимание: `total` может быть `None`. `url`/`claim` могут быть `""`.

`s.triangulation[i]` (из `scoring.triangulate()`) — dict:
```python
{"id": "H1", "distinct_types_supporting": 2,
 "distinct_types_contradicting": 1, "under_triangulated": True, "note": ""}
```

`s.hypotheses` — `["H1: claim text", "H2: ...", ...]`. Парсинг id делает
`runner.scoring.hypothesis_ids(hypotheses) -> ["H1", "H2", ...]` (ПЕРЕИСПОЛЬЗОВАТЬ, не дублировать regex).

`deviations.md` формат (из `adaptive.Deviation.render()`), записи разделены `## D1`, `## D2`:
```markdown
## D2
- subquestion: Q5
- round: 1
- trigger: unexpected_finding
- class: expensive
- status: not_pursued
- decision_by: orchestrator (opus)
- rationale: expensive budget exhausted
- action: none
- depth: —
- budget_after: { cheap: 3, expensive: 0 }
- outcome: —
- new_source_ids: []
- carry_forward: Phase 7 refresh-target
```
Строка carry_forward присутствует ТОЛЬКО если задана: `- carry_forward: <text>`.

`RunState`: поля `slug`, `depth`, `genre`, `hypotheses`, `sources`, `triangulation`; `s.dir == s.root / s.slug` (property).

`orchestrator.py` уже импортирует `import datetime as dt`, `import re`. Паттерн импорта модуля фазы — try/except (`.verify` / `verify`).

**Тесты:** нет `conftest.py`, нет `pyproject.toml`. Импорт в тестах прямой: `from runner.refresh import ...`. Запуск: `python -m pytest` из корня проекта. Ruff — без конфига (defaults, E501=88).

**Дисциплина:** TDD (red → green), коммит после каждой задачи на ветке `feat/phase7-refresh`. Субагент НЕ пушит и НЕ мержит.

---

## File Structure

- **Create:** `runner/refresh.py` — pure extract-функции + render (одна ответственность: генерация содержимого refresh_targets).
- **Modify:** `runner/orchestrator.py` — import блок (+1 try/except), новый метод `refresh()`, вызов в `run()`.
- **Create:** `tests/test_refresh.py` — юнит-тесты extract/render (голые dict/строки) + оффлайн-тесты через `run()`.

---

## Task 0: Ветка

- [ ] **Step 1: Создать ветку от main**

```bash
git checkout main
git checkout -b feat/phase7-refresh
git status -sb
```
Expected: `## feat/phase7-refresh`

---

## Task 1: `extract_hypotheses` — гипотезы со статусом

**Files:**
- Create: `runner/refresh.py`
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_refresh.py`:
```python
from runner.refresh import extract_hypotheses


def test_extract_hypotheses_maps_status():
    hypotheses = ["H1: coffee boosts focus", "H2: tea is calming"]
    triangulation = [
        {"id": "H1", "distinct_types_supporting": 3, "under_triangulated": False,
         "distinct_types_contradicting": 0, "note": ""},
        {"id": "H2", "distinct_types_supporting": 1, "under_triangulated": True,
         "distinct_types_contradicting": 0, "note": ""},
    ]
    out = extract_hypotheses(hypotheses, triangulation)
    assert out[0] == {"id": "H1", "text": "coffee boosts focus",
                      "status": "supported", "supporting_types": 3}
    assert out[1]["status"] == "inconclusive"


def test_extract_hypotheses_no_triangulation_is_inconclusive():
    out = extract_hypotheses(["H1: a claim"], [])
    assert out[0]["status"] == "inconclusive"
    assert out[0]["supporting_types"] == 0


def test_extract_hypotheses_empty():
    assert extract_hypotheses([], []) == []
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner.refresh'`

- [ ] **Step 3: Минимальная реализация**

Создать `runner/refresh.py`:
```python
"""Phase 7 — refresh targets generation.

Pure extraction + rendering for <slug>/refresh_targets.md (the entry point for a
future `update <slug>` delta-research run). No network, no I/O — the orchestrator
reads RunState and writes the file. Mirrors scoring.py / verify.py.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

try:
    from .scoring import hypothesis_ids
except ImportError:  # run as a script
    from scoring import hypothesis_ids


def extract_hypotheses(hypotheses: list[str], triangulation: list[dict]) -> list[dict]:
    """Pair each hypothesis with its triangulation status.

    supported   = has supporting types and not under_triangulated
    inconclusive = under_triangulated, or no triangulation record
    """
    by_id = {row.get("id"): row for row in triangulation}
    ids = hypothesis_ids(hypotheses)
    out = []
    for hid, raw in zip(ids, hypotheses):
        text = raw.split(":", 1)[1].strip() if ":" in raw else raw.strip()
        row = by_id.get(hid)
        n_sup = row.get("distinct_types_supporting", 0) if row else 0
        under = row.get("under_triangulated", True) if row else True
        status = "supported" if (n_sup > 0 and not under) else "inconclusive"
        out.append({"id": hid, "text": text, "status": status,
                    "supporting_types": n_sup})
    return out
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (3 теста)

- [ ] **Step 5: Коммит**

```bash
git add runner/refresh.py tests/test_refresh.py
git commit -m "feat(refresh): extract_hypotheses со статусом из triangulation"
```

---

## Task 2: `extract_entities` — entities из sources, дедуп по домену

**Files:**
- Modify: `runner/refresh.py`
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_refresh.py`:
```python
from runner.refresh import extract_entities


def test_extract_entities_dedups_by_domain():
    sources = [
        {"id": "s01", "url": "https://acme.com/pricing", "claim": "Acme raised $5M"},
        {"id": "s02", "url": "https://acme.com/blog/post", "claim": "Acme ships v2"},
        {"id": "s03", "url": "https://beta.io/about", "claim": "Beta is new"},
    ]
    out = extract_entities(sources)
    domains = [e["domain"] for e in out]
    assert domains == ["acme.com", "beta.io"]
    assert out[0]["url"] == "https://acme.com/pricing"  # first wins
    assert out[0]["why"] == "Acme raised $5M"


def test_extract_entities_skips_empty_url():
    out = extract_entities([{"id": "s01", "url": "", "claim": "x"}])
    assert out == []


def test_extract_entities_empty():
    assert extract_entities([]) == []
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -k entities -v`
Expected: FAIL — `ImportError: cannot import name 'extract_entities'`

- [ ] **Step 3: Реализация**

Добавить в `runner/refresh.py`:
```python
def extract_entities(sources: list[dict]) -> list[dict]:
    """One entity per distinct URL domain, first source wins. Skips empty URLs."""
    seen: set[str] = set()
    out = []
    for src in sources:
        url = (src.get("url") or "").strip()
        if not url:
            continue
        domain = urlsplit(url).netloc
        if not domain or domain in seen:
            continue
        seen.add(domain)
        out.append({"domain": domain, "url": url,
                    "why": (src.get("claim") or "").strip()})
    return out
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (6 тестов)

- [ ] **Step 5: Коммит**

```bash
git add runner/refresh.py tests/test_refresh.py
git commit -m "feat(refresh): extract_entities с дедупом по домену"
```

---

## Task 3: `extract_numbers` — numeric sources по эвристике

**Files:**
- Modify: `runner/refresh.py`
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_refresh.py`:
```python
from runner.refresh import extract_numbers


def test_extract_numbers_keeps_numeric_claim():
    sources = [
        {"id": "s01", "url": "https://x.com/a", "claim": "GDP grew 3.2% in 2025"},
        {"id": "s02", "url": "https://x.com/b", "claim": "no digits here"},
    ]
    out = extract_numbers(sources)
    assert len(out) == 1
    assert out[0]["phrase"] == "GDP grew 3.2% in 2025"
    assert out[0]["url"] == "https://x.com/a"


def test_extract_numbers_keeps_data_domain_even_without_digit():
    sources = [{"id": "s01", "url": "https://fred.stlouisfed.org/series/CPI",
                "claim": "consumer prices"}]
    out = extract_numbers(sources)
    assert len(out) == 1


def test_extract_numbers_empty():
    assert extract_numbers([]) == []
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -k numbers -v`
Expected: FAIL — `ImportError: cannot import name 'extract_numbers'`

- [ ] **Step 3: Реализация**

Добавить в `runner/refresh.py` (константа — наверх модуля, под импорты):
```python
DATA_DOMAINS = ("fred", "worldbank", "statista", "oecd", "data.gov", "stlouisfed")
```
```python
def extract_numbers(sources: list[dict]) -> list[dict]:
    """Sources whose claim contains a digit, or whose URL is a known data domain."""
    out = []
    for src in sources:
        claim = (src.get("claim") or "").strip()
        url = (src.get("url") or "").strip()
        is_data_domain = any(d in url.lower() for d in DATA_DOMAINS)
        if not (re.search(r"\d", claim) or is_data_domain):
            continue
        out.append({"phrase": claim or url, "url": url})
    return out
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (9 тестов)

- [ ] **Step 5: Коммит**

```bash
git add runner/refresh.py tests/test_refresh.py
git commit -m "feat(refresh): extract_numbers по эвристике (digit | data-домен)"
```

---

## Task 4: `extract_carry_forward` — carry-forward из deviations.md

**Files:**
- Modify: `runner/refresh.py`
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_refresh.py`:
```python
from runner.refresh import extract_carry_forward


DEVIATIONS_SAMPLE = """# Deviations — my topic

## D1
- subquestion: Q3
- status: pursued
- new_source_ids: [S11]

## D2
- subquestion: Q5
- status: not_pursued
- carry_forward: Phase 7 refresh-target
"""


def test_extract_carry_forward_parses_records():
    out = extract_carry_forward(DEVIATIONS_SAMPLE)
    assert out == [{"subquestion": "Q5", "carry_forward": "Phase 7 refresh-target"}]


def test_extract_carry_forward_empty_text():
    assert extract_carry_forward("") == []


def test_extract_carry_forward_no_carry_lines():
    text = "# Deviations\n\n## D1\n- subquestion: Q1\n- status: pursued\n"
    assert extract_carry_forward(text) == []
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -k carry -v`
Expected: FAIL — `ImportError: cannot import name 'extract_carry_forward'`

- [ ] **Step 3: Реализация**

Добавить в `runner/refresh.py`:
```python
def extract_carry_forward(deviations_text: str) -> list[dict]:
    """Parse deviations.md: each '## D*' block with a carry_forward line becomes a
    refresh candidate. subquestion defaults to '?' if the block lacks one."""
    out = []
    blocks = re.split(r"^## D\d+\s*$", deviations_text, flags=re.MULTILINE)
    for block in blocks:
        cf = re.search(r"^- carry_forward:\s*(.+)$", block, flags=re.MULTILINE)
        if not cf:
            continue
        sq = re.search(r"^- subquestion:\s*(.+)$", block, flags=re.MULTILINE)
        out.append({"subquestion": sq.group(1).strip() if sq else "?",
                    "carry_forward": cf.group(1).strip()})
    return out
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (12 тестов)

- [ ] **Step 5: Коммит**

```bash
git add runner/refresh.py tests/test_refresh.py
git commit -m "feat(refresh): extract_carry_forward из deviations.md"
```

---

## Task 5: `render_refresh_targets` — сборка markdown по Z11

**Files:**
- Modify: `runner/refresh.py`
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_refresh.py`:
```python
from runner.refresh import render_refresh_targets


def _render_sample():
    hyps = [{"id": "H1", "text": "coffee boosts focus",
             "status": "supported", "supporting_types": 3}]
    entities = [{"domain": "acme.com", "url": "https://acme.com/pricing",
                 "why": "Acme raised $5M"}]
    numbers = [{"phrase": "GDP grew 3.2%", "url": "https://x.com/a"}]
    carry = [{"subquestion": "Q5", "carry_forward": "deep-dive on pricing"}]
    return render_refresh_targets("coffee-focus", "medium", hyps, entities,
                                  numbers, carry, today="2026-06-15")


def test_render_has_all_sections():
    md = _render_sample()
    assert "# Refresh targets — coffee-focus" in md
    assert "## 1. Entities to track" in md
    assert "## 2. Numbers to refresh" in md
    assert "## 3. Topic markers" in md
    assert "## 4. Hypotheses to re-test" in md
    assert "## 5. Refresh candidates" in md


def test_render_frontmatter_and_cadence():
    md = _render_sample()
    assert "slug: coffee-focus" in md
    assert "last_research_date: 2026-06-15" in md
    assert "update_cadence: 90 days" in md  # medium
    deep = render_refresh_targets("s", "deep", [], [], [], [], today="2026-06-15")
    assert "update_cadence: 30 days" in deep


def test_render_emits_todo_markers():
    md = _render_sample()
    assert md.count("<!-- TODO") >= 3  # entities, numbers, topic markers


def test_render_is_deterministic():
    assert _render_sample() == _render_sample()


def test_render_handles_empty():
    md = render_refresh_targets("s", "medium", [], [], [], [], today="2026-06-15")
    assert "_none_" in md
    assert "_no hypotheses recorded_" in md
    assert "# Refresh targets — s" in md  # не падает
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -k render -v`
Expected: FAIL — `ImportError: cannot import name 'render_refresh_targets'`

- [ ] **Step 3: Реализация**

Добавить в `runner/refresh.py`:
```python
_TODO_ENTITY = ("<!-- TODO: pricing/careers/crunchbase split + sha256 hash"
                " — требуют M2/M5 block-render -->")
_TODO_NUMBER = ("<!-- TODO: series id + last_value + API access"
                " — требуют N-block render -->")
_TODO_TOPIC = ("<!-- TODO: OpenAlex concept IDs / GitHub topics / news keywords"
               " — требуют Phase 4 discovery-метаданных в RunState -->")


def render_refresh_targets(slug: str, depth: str, hypotheses: list[dict],
                           entities: list[dict], numbers: list[dict],
                           carry: list[dict], *, today: str) -> str:
    """Render <slug>/refresh_targets.md per the Z11 template. Pure: `today` is
    passed in so the output is deterministic in tests."""
    cadence = "30 days" if depth == "deep" else "90 days"
    out = [
        "---",
        f"slug: {slug}",
        f"last_research_date: {today}",
        f"depth: {depth}",
        f"update_cadence: {cadence}",
        "---",
        "",
        f"# Refresh targets — {slug}",
        "",
        "## 1. Entities to track",
    ]
    if entities:
        for e in entities:
            out += [f"### {e['domain']}",
                    f"- **Source URL:** {e['url']}",
                    f"- **Why in scope:** {e['why'] or '—'}", ""]
    else:
        out += ["_none_", ""]
    out.append(_TODO_ENTITY)

    out += ["", "## 2. Numbers to refresh"]
    if numbers:
        for n in numbers:
            out += [f"### {n['phrase']}", f"- **Source:** {n['url'] or '—'}", ""]
    else:
        out += ["_none_", ""]
    out.append(_TODO_NUMBER)

    out += ["", "## 3. Topic markers (discovery)", _TODO_TOPIC]

    out += ["", "## 4. Hypotheses to re-test"]
    if hypotheses:
        for h in hypotheses:
            out += [
                f'### {h["id"]}: "{h["text"]}"',
                f"- **Status at last research:** {h['status']}",
                f"- **Supporting source types:** {h['supporting_types']}",
                f'- **Watch for:** "{h["text"]} failed replication"; '
                "retractions (RetractionWatch); counter-evidence", ""]
    else:
        out += ["_no hypotheses recorded_", ""]

    out += ["## 5. Refresh candidates (carry-forward)"]
    if carry:
        for c in carry:
            out.append(f"- **{c['subquestion']}** — {c['carry_forward']}")
    else:
        out.append("_none_")
    out.append("")
    return "\n".join(out)
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (17 тестов)

- [ ] **Step 5: Коммит**

```bash
git add runner/refresh.py tests/test_refresh.py
git commit -m "feat(refresh): render_refresh_targets по шаблону Z11 + TODO-маркеры"
```

---

## Task 6: `Orchestrator.refresh()` + интеграция в run()

**Files:**
- Modify: `runner/orchestrator.py` (import блок ~строка 50; новый метод после `verify()` ~строка 337; вызов в `run()` ~строка 349)
- Test: `tests/test_refresh.py`

- [ ] **Step 1: Написать падающий тест (оффлайн через run())**

Добавить в `tests/test_refresh.py`:
```python
from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider


def test_run_generates_refresh_targets(tmp_path):
    o = Orchestrator(DryRunProvider())
    out_dir = o.run("does coffee boost focus", "medium", tmp_path)
    rt = out_dir / "refresh_targets.md"
    assert rt.exists()
    text = rt.read_text(encoding="utf-8")
    assert "# Refresh targets" in text
    assert "## 4. Hypotheses to re-test" in text
    assert "slug:" in text


def test_refresh_skipped_for_shallow(tmp_path):
    o = Orchestrator(DryRunProvider())
    out_dir = o.run("q", "shallow", tmp_path)
    assert not (out_dir / "refresh_targets.md").exists()


def test_refresh_survives_missing_deviations(tmp_path):
    # call refresh() directly on a state with no deviations.md written
    o = Orchestrator(DryRunProvider())
    s = RunState(question="q about x", depth="medium", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    s.dir.mkdir(parents=True, exist_ok=True)
    o.refresh(s)  # must NOT raise
    assert (s.dir / "refresh_targets.md").exists()
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python -m pytest tests/test_refresh.py -k "run_generates or shallow or survives_missing" -v`
Expected: FAIL — `refresh_targets.md` не существует / `AttributeError: 'Orchestrator' object has no attribute 'refresh'`

- [ ] **Step 3a: Добавить импорт модуля в orchestrator.py**

В `runner/orchestrator.py`, после блока импорта `verify` (паттерн try/except), добавить:
```python
try:
    from .refresh import (extract_carry_forward, extract_entities,
                          extract_hypotheses, extract_numbers,
                          render_refresh_targets)
except ImportError:  # run as a script
    from refresh import (extract_carry_forward, extract_entities,
                         extract_hypotheses, extract_numbers,
                         render_refresh_targets)
```

- [ ] **Step 3b: Добавить метод `refresh()` после `verify()`**

В `runner/orchestrator.py`, сразу после метода `verify()` (перед `def run`), добавить:
```python
    # --- Phase 7: refresh targets generation -------------------------------
    def refresh(self, s: RunState) -> None:
        if s.depth == "shallow":
            return  # refresh targets are for medium/deep only
        try:
            devs_text = (s.dir / "deviations.md").read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            devs_text = ""
        content = render_refresh_targets(
            s.slug, s.depth,
            extract_hypotheses(s.hypotheses, s.triangulation),
            extract_entities(s.sources),
            extract_numbers(s.sources),
            extract_carry_forward(devs_text),
            today=dt.date.today().isoformat(),
        )
        (s.dir / "refresh_targets.md").write_text(content, encoding="utf-8")
```

- [ ] **Step 3c: Вызвать в run()**

В `runner/orchestrator.py`, в методе `run()`, между `self.verify(s)` и `return s.dir`, вставить строку:
```python
        self.verify(s)
        self.refresh(s)
        return s.dir
```

- [ ] **Step 4: Запустить — убедиться, что зелёный**

Run: `python -m pytest tests/test_refresh.py -v`
Expected: PASS (20 тестов)

- [ ] **Step 5: Коммит**

```bash
git add runner/orchestrator.py tests/test_refresh.py
git commit -m "feat(orchestrator): Phase 7 refresh() после verify() в run()"
```

---

## Task 7: Полная верификация перед мерджем

**Files:** none (только проверки)

- [ ] **Step 1: Весь suite зелёный**

Run: `python -m pytest -q`
Expected: PASS, ~162 теста (было 142 + ~20 новых), без сетевых вызовов (≈1-2s)

- [ ] **Step 2: Линт чист**

Run: `ruff check runner/refresh.py runner/orchestrator.py tests/test_refresh.py`
Expected: `All checks passed!`

- [ ] **Step 3: Дымовой прогон оффлайн end-to-end**

Run:
```bash
python runner/orchestrator.py "does remote work increase productivity" --provider dryrun --out /tmp/p7smoke
cat /tmp/p7smoke/*/refresh_targets.md | head -40
```
Expected: файл существует, есть frontmatter + 5 секций + хотя бы один `<!-- TODO`. (Если флаги CLI отличаются — свериться с `python runner/orchestrator.py --help`; не менять CLI, только проверить.)

- [ ] **Step 4: Сверка с требованиями спеки**

Перечитать `docs/superpowers/specs/2026-06-15-phase7-refresh-design.md` построчно, отметить: источник=RunState ✓, shallow-гейт ✓, TODO-маркеры ✓, graceful edge-cases ✓, сети нет ✓, JSON-схемы нет (guard-тест не трогали) ✓.

- [ ] **Step 5: Финальный code-review субагентом**

Запустить `pr-review-toolkit:code-reviewer` (или `feature-dev:code-reviewer`) на `git diff main...feat/phase7-refresh`. Передать границы: только `runner/refresh.py`, `runner/orchestrator.py` (refresh-часть), `tests/test_refresh.py`. Исправить находки high-confidence, отчитаться о решениях по остальным.

**ОСТАНОВ:** не пушить, не открывать PR, не мержить в main. Доложить результат пользователю — мердж по его явному подтверждению.

---

## Self-Review (заполнено автором плана)

**Spec coverage:**
- Источник=RunState → Tasks 1-4 (extract из s.hypotheses/sources/triangulation/deviations) ✓
- Z11 формат + frontmatter + cadence → Task 5 ✓
- 5 секций + TODO-маркеры → Task 5 (`test_render_emits_todo_markers`) ✓
- shallow-гейт → Task 6 (`test_refresh_skipped_for_shallow`) ✓
- graceful edge-cases (нет deviations, пусто) → Task 4 (`test_extract_carry_forward_empty_text`), Task 5 (`test_render_handles_empty`), Task 6 (`test_refresh_survives_missing_deviations`) ✓
- интеграция после verify() → Task 6 ✓
- сеть/subprocess нет → by design (нет вызовов provider/subprocess в refresh) ✓
- JSON-схемы нет → guard-тест не трогаем (отмечено в Task 7 step 4) ✓

**Placeholder scan:** все шаги с кодом содержат полный код; команды с ожидаемым выводом; нет TBD/"handle edge cases". ✓

**Type consistency:** ключи dict согласованы между tasks — `extract_hypotheses` отдаёт `{id,text,status,supporting_types}`, `render` читает ровно их; `extract_entities` → `{domain,url,why}` ↔ render; `extract_numbers` → `{phrase,url}` ↔ render; `extract_carry_forward` → `{subquestion,carry_forward}` ↔ render. Сигнатура `render_refresh_targets(slug, depth, hypotheses, entities, numbers, carry, *, today)` одинакова в Task 5 и вызове Task 6. ✓
