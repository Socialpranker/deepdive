# Байесовский рой deepdive — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Рой суб-агентов распределяет свободный бюджет по накопленной статистике отдачи канала, статистика переживает прогоны, найденные источники промотируются в каталог, мёртвые — вычищаются.

**Architecture:** Beta-Bernoulli posterior на паре `канал × qclass`, хранится вне скилла в `~/.claude/deepdive-state/`. Thompson sampling распределяет только свободную часть бюджета — обязательная часть держит триангуляцию. Наблюдения извлекаются постфактум из уже существующих артефактов прогона (`sources/NN.md`, `claims.csv`), новой инструментовки в прогоне нет.

**Tech Stack:** Python 3, только stdlib (`random.betavariate`, `csv`, `json`, `pathlib`). pytest. Никаких numpy/scipy — проект держит зависимости минимальными (`scripts/requirements.txt`).

**Spec:** `docs/specs/2026-08-18-bayesian-swarm-design.md`

## Global Constraints

- Только stdlib в `runner/` и `scripts/`; новые зависимости в `scripts/requirements.txt` не добавляются.
- Состояние пишется **только** в `~/.claude/deepdive-state/`; ничего не пишется в каталог скилла в рантайме.
- Все функции чтения состояния принимают `root: Path | None` — тесты работают на `tmp_path`, никогда на реальном состоянии.
- Ключ приора — строка `f"{channel}|{qclass}"`.
- `λ = 0.95`, floor `alpha >= 1.0` и `beta >= 1.0`, порог промоушена `posterior_mean >= 0.3`.
- Скрипты в `scripts/` read-only по отношению к артефактам прогона.
- После правок `runner/adaptive.py` — `ruff check --select F821 runner/`.
- Тесты: `python -m pytest tests/ -q` из корня скилла.

---

### Task 1: Хранилище состояния

**Files:**
- Create: `runner/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: ничего
- Produces: `Observation(run_id: str, channel: str, qclass: str, reward: int, ts: str)`, `Prior(alpha: float, beta: float, n: int, last_seen: str)`, `state_dir(root=None) -> Path`, `prior_key(channel, qclass) -> str`, `append_observation(obs, root=None) -> None`, `read_observations(root=None) -> list[Observation]`, `load_priors(root=None) -> dict[str, Prior]`, `save_priors(priors, root=None) -> None`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_state.py
import json
from runner.state import (
    Observation, Prior, prior_key, state_dir,
    append_observation, read_observations, load_priors, save_priors,
)


def test_prior_key_joins_channel_and_qclass():
    assert prior_key("academic", "scientific-claim") == "academic|scientific-claim"


def test_append_and_read_observations_roundtrip(tmp_path):
    obs = Observation(run_id="r1", channel="academic", qclass="scientific-claim",
                      reward=1, ts="2026-08-18T10:00:00Z")
    append_observation(obs, root=tmp_path)
    append_observation(Observation("r1", "web-general", "pricing", 0, "2026-08-18T10:01:00Z"),
                       root=tmp_path)
    got = read_observations(root=tmp_path)
    assert [o.channel for o in got] == ["academic", "web-general"]
    assert got[0].reward == 1


def test_read_observations_skips_malformed_lines(tmp_path):
    p = state_dir(tmp_path) / "observations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"run_id":"r1","channel":"academic","qclass":"pricing","reward":1,"ts":"t"}\n'
                 'not json at all\n'
                 '{"run_id":"r2"}\n', encoding="utf-8")
    got = read_observations(root=tmp_path)
    assert len(got) == 1  # битые строки не роняют чтение


def test_save_and_load_priors_roundtrip(tmp_path):
    priors = {"academic|pricing": Prior(alpha=2.0, beta=3.0, n=5, last_seen="2026-08-18")}
    save_priors(priors, root=tmp_path)
    got = load_priors(root=tmp_path)
    assert got["academic|pricing"].alpha == 2.0
    assert got["academic|pricing"].n == 5


def test_load_priors_returns_empty_on_missing_file(tmp_path):
    assert load_priors(root=tmp_path) == {}


def test_load_priors_returns_empty_on_corrupt_file(tmp_path):
    d = state_dir(tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "priors.json").write_text("{ broken", encoding="utf-8")
    assert load_priors(root=tmp_path) == {}


def test_save_priors_is_atomic_no_tmp_left(tmp_path):
    save_priors({"a|b": Prior(1.0, 1.0, 0, "2026-08-18")}, root=tmp_path)
    leftovers = list(state_dir(tmp_path).glob("*.tmp"))
    assert leftovers == []
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_state.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'runner.state'`

- [ ] **Step 3: Реализовать**

```python
# runner/state.py
#!/usr/bin/env python3
"""Persistent state for the Bayesian swarm: observations log + priors + candidates.

Lives OUTSIDE the skill directory on purpose: the skill dir is not under version
control, so a reinstall would wipe everything accumulated. observations.jsonl is
the primary record; priors.json is a derived rollup that can be rebuilt from it.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_ROOT = Path.home() / ".claude"
STATE_DIRNAME = "deepdive-state"


@dataclass
class Observation:
    run_id: str
    channel: str
    qclass: str
    reward: int
    ts: str


@dataclass
class Prior:
    alpha: float
    beta: float
    n: int
    last_seen: str


def state_dir(root: Path | None = None) -> Path:
    return (Path(root) if root is not None else DEFAULT_ROOT) / STATE_DIRNAME


def prior_key(channel: str, qclass: str) -> str:
    return f"{channel}|{qclass}"


def append_observation(obs: Observation, root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "observations.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(obs), ensure_ascii=False) + "\n")


def read_observations(root: Path | None = None) -> list[Observation]:
    p = state_dir(root) / "observations.jsonl"
    if not p.exists():
        return []
    out: list[Observation] = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Observation(**json.loads(line)))
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("observations.jsonl:%d unreadable (%s) — skipped", lineno, exc)
    return out


def load_priors(root: Path | None = None) -> dict[str, Prior]:
    """Missing or corrupt priors are NOT fatal — caller falls back to uniform.

    Returning {} here is what makes the allocator degrade loudly instead of dying;
    the caller is responsible for logging the fallback.
    """
    p = state_dir(root) / "priors.json"
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {k: Prior(**v) for k, v in raw.items()}
    except (json.JSONDecodeError, TypeError) as exc:
        log.warning("priors.json unreadable (%s) — falling back to uniform", exc)
        return {}


def save_priors(priors: dict[str, Prior], root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    target = d / "priors.json"
    tmp = d / "priors.json.tmp"
    tmp.write_text(
        json.dumps({k: asdict(v) for k, v in priors.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, target)
```

- [ ] **Step 4: Прогнать тест, убедиться что проходит**

Run: `python -m pytest tests/test_state.py -q`
Expected: PASS, 7 passed

- [ ] **Step 5: Коммит**

```bash
git add runner/state.py tests/test_state.py
git commit -m "feat(swarm): хранилище наблюдений и приоров вне каталога скилла"
```

---

### Task 2: Классы подвопросов

**Files:**
- Create: `runner/qclass.py`
- Test: `tests/test_qclass.py`

**Interfaces:**
- Consumes: ничего
- Produces: `QCLASSES: tuple[str, ...]`, `DEFAULT_QCLASS = "qualitative"`, `normalize_qclass(raw: str) -> str`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_qclass.py
import pytest
from runner.qclass import QCLASSES, DEFAULT_QCLASS, normalize_qclass


def test_seventeen_classes_match_dispatch_matrix():
    assert len(QCLASSES) == 17
    assert "market-size" in QCLASSES
    assert "scientific-claim" in QCLASSES
    assert DEFAULT_QCLASS in QCLASSES


def test_normalize_accepts_known_class():
    assert normalize_qclass("pricing") == "pricing"


def test_normalize_is_case_and_space_insensitive():
    assert normalize_qclass("  Market-Size ") == "market-size"


def test_unknown_class_falls_back_to_default_not_crash():
    assert normalize_qclass("шапито") == DEFAULT_QCLASS


def test_empty_falls_back_to_default():
    assert normalize_qclass("") == DEFAULT_QCLASS
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_qclass.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'runner.qclass'`

- [ ] **Step 3: Реализовать**

```python
# runner/qclass.py
#!/usr/bin/env python3
"""Sub-question classes — the second axis of the prior (channel x qclass).

Mirrors the rows of the dispatch matrix in references/source_dispatch.md. Without
this axis a prior averages incomparable things: `academic` is excellent for
scientific-claim and useless for pricing.
"""
from __future__ import annotations

QCLASSES: tuple[str, ...] = (
    "market-size", "time-series", "scientific-claim", "players", "country-stat",
    "how-it-works", "recent-change", "regulation", "benchmark", "sentiment",
    "adoption", "pricing", "crypto", "health", "climate", "jobs", "qualitative",
)

DEFAULT_QCLASS = "qualitative"


def normalize_qclass(raw: str) -> str:
    """Unknown input degrades to the default instead of raising.

    A sub-question that matches no matrix row is already handled by source_dispatch
    as ad-hoc; crashing the allocator over it would be worse than a weaker prior.
    """
    cleaned = (raw or "").strip().lower()
    return cleaned if cleaned in QCLASSES else DEFAULT_QCLASS
```

- [ ] **Step 4: Прогнать тест, убедиться что проходит**

Run: `python -m pytest tests/test_qclass.py -q`
Expected: PASS, 5 passed

- [ ] **Step 5: Коммит**

```bash
git add runner/qclass.py tests/test_qclass.py
git commit -m "feat(swarm): enum классов подвопроса под ось приора"
```

---

### Task 3: Байесовская модель — decay, floor, partial pooling

**Files:**
- Create: `runner/priors.py`
- Test: `tests/test_priors.py`
- Create: `tests/fixtures/channels_mini.md`

**Interfaces:**
- Consumes: `runner.state.Prior`, `runner.state.prior_key`
- Produces: `LAMBDA = 0.95`, `FLOOR = 1.0`, `posterior_mean(p: Prior) -> float`, `apply_decay(p: Prior, wins: int, losses: int, lam: float = LAMBDA) -> Prior`, `load_channel_groups(channels_md: Path) -> dict[str, str]`, `rebuild_priors(observations: list[Observation], lam: float = LAMBDA) -> dict[str, Prior]`, `effective_prior(priors: dict[str, Prior], channel: str, qclass: str, groups: dict[str, str]) -> Prior`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_priors.py
from pathlib import Path

from runner.state import Observation, Prior
from runner.priors import (
    LAMBDA, FLOOR, posterior_mean, apply_decay,
    load_channel_groups, rebuild_priors, effective_prior,
)

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"


def test_posterior_mean_is_alpha_over_total():
    assert posterior_mean(Prior(3.0, 1.0, 4, "t")) == 0.75


def test_decay_discounts_history_and_adds_new_evidence():
    p = apply_decay(Prior(10.0, 10.0, 20, "t"), wins=1, losses=0, lam=0.5)
    assert p.alpha == 6.0   # 10*0.5 + 1
    assert p.beta == 5.0    # 10*0.5 + 0
    assert p.n == 21


def test_floor_keeps_channel_samplable_after_long_failure():
    p = Prior(1.0, 40.0, 41, "t")
    for _ in range(50):
        p = apply_decay(p, wins=0, losses=1)
    assert p.alpha >= FLOOR  # канал не умирает навсегда
    assert posterior_mean(p) > 0.0


def test_channel_groups_parsed_from_channels_md():
    groups = load_channel_groups(FIXTURE)
    assert groups["academic"] == "B"
    assert groups["web-general"] == "A"
    assert groups["api-direct"] == "M"


def test_rebuild_aggregates_observations_per_key():
    obs = [
        Observation("r1", "academic", "scientific-claim", 1, "2026-08-01"),
        Observation("r1", "academic", "scientific-claim", 1, "2026-08-01"),
        Observation("r2", "academic", "scientific-claim", 0, "2026-08-02"),
        Observation("r2", "web-general", "pricing", 1, "2026-08-02"),
    ]
    priors = rebuild_priors(obs)
    assert priors["academic|scientific-claim"].n == 3
    assert priors["web-general|pricing"].n == 1
    assert posterior_mean(priors["academic|scientific-claim"]) > 0.5


def test_rebuild_is_deterministic_from_the_same_log():
    obs = [Observation("r1", "academic", "pricing", 1, "2026-08-01")]
    assert rebuild_priors(obs) == rebuild_priors(obs)


def test_effective_prior_pools_from_group_when_cell_is_empty():
    groups = load_channel_groups(FIXTURE)
    priors = {"academic|scientific-claim": Prior(9.0, 1.0, 10, "t")}
    # preprint-servers в группе B, своей ячейки нет -> наследует репутацию группы
    got = effective_prior(priors, "preprint-servers", "scientific-claim", groups)
    assert posterior_mean(got) > 0.5
    assert got.n == 0  # пулинг даёт форму, но не выдаёт себя за собственные наблюдения


def test_effective_prior_is_uniform_when_group_is_empty_too():
    groups = load_channel_groups(FIXTURE)
    got = effective_prior({}, "academic", "pricing", groups)
    assert got.alpha == FLOOR and got.beta == FLOOR


def test_registry_channels_start_above_web_general():
    groups = load_channel_groups(FIXTURE)
    api = effective_prior({}, "api-direct", "market-size", groups)
    web = effective_prior({}, "web-general", "market-size", groups)
    assert posterior_mean(api) > posterior_mean(web)  # registry-first закодирован в приоре
```

- [ ] **Step 2: Создать фикстуру и прогнать тест**

```markdown
<!-- tests/fixtures/channels_mini.md -->
# Channels (mini fixture)

### Часть A — Web и discovery

| id | note |
|---|---|
| `web-general` | обычный веб |
| `wikipedia-references` | ссылки из вики |

### Часть B — Academic / Scholarly

| id | note |
|---|---|
| `academic` | OpenAlex, Semantic Scholar |
| `preprint-servers` | arXiv, bioRxiv |

### Часть M — API-direct (программный access)

| id | note |
|---|---|
| `api-direct` | прямые эндпоинты |
```

Run: `python -m pytest tests/test_priors.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'runner.priors'`

- [ ] **Step 3: Реализовать**

```python
# runner/priors.py
#!/usr/bin/env python3
"""Beta-Bernoulli model over (channel x qclass).

Three properties matter more than the math:
  - decay: sources rot (APIs die, paywalls appear); a two-year-old prior lies
    more confidently than no prior at all.
  - floor: a channel whose alpha hits zero is never sampled again and can never
    recover once its API is fixed.
  - pooling: a cell with no observations inherits its channel group's shape,
    so a new source starts with its type's reputation instead of a coin flip.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from runner.state import Observation, Prior, prior_key

LAMBDA = 0.95
FLOOR = 1.0

# Стартовое смещение по группам: registry-каналы начинают выше веба.
# Это кодирует registry-first правило source_dispatch.md, а не вкусовщину.
GROUP_HEAD_START: dict[str, tuple[float, float]] = {
    "I": (2.0, 1.0),   # Quantitative — data-statistical-gov, surveys
    "M": (2.0, 1.0),   # API-direct
    "H": (1.5, 1.0),   # Official / Legal
    "B": (1.5, 1.0),   # Academic
}

PART_RE = re.compile(r"^###\s+Часть\s+([A-Z])\b")
CHANNEL_RE = re.compile(r"`([a-z][a-z0-9-]{3,})`")


def posterior_mean(p: Prior) -> float:
    total = p.alpha + p.beta
    return p.alpha / total if total else 0.0


def apply_decay(p: Prior, wins: int, losses: int, lam: float = LAMBDA) -> Prior:
    alpha = max(FLOOR, p.alpha * lam + wins)
    beta = max(FLOOR, p.beta * lam + losses)
    return Prior(alpha=alpha, beta=beta, n=p.n + wins + losses, last_seen=p.last_seen)


@lru_cache(maxsize=8)
def _groups_cached(path_str: str, mtime: float) -> tuple[tuple[str, str], ...]:
    text = Path(path_str).read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    current = ""
    for line in text.splitlines():
        m = PART_RE.match(line)
        if m:
            current = m.group(1)
            continue
        if not current:
            continue
        for cid in CHANNEL_RE.findall(line):
            out.append((cid, current))
    return tuple(out)


def load_channel_groups(channels_md: Path) -> dict[str, str]:
    """Parse channel id -> group letter straight from channels.md.

    Parsed rather than hand-copied: a hand-written table drifts silently the first
    time someone adds a channel.
    """
    p = Path(channels_md)
    return dict(_groups_cached(str(p), p.stat().st_mtime))


def rebuild_priors(observations: list[Observation], lam: float = LAMBDA) -> dict[str, Prior]:
    """Fold the whole observation log into priors, oldest first.

    Rebuilt from scratch every time — that is the point of keeping the log primary:
    a fix to this formula re-derives history instead of losing it.
    """
    priors: dict[str, Prior] = {}
    for obs in observations:
        key = prior_key(obs.channel, obs.qclass)
        cur = priors.get(key, Prior(FLOOR, FLOOR, 0, obs.ts))
        updated = apply_decay(cur, wins=1 if obs.reward else 0,
                              losses=0 if obs.reward else 1, lam=lam)
        updated.last_seen = obs.ts
        priors[key] = updated
    return priors


def effective_prior(priors: dict[str, Prior], channel: str, qclass: str,
                    groups: dict[str, str]) -> Prior:
    """Own cell if it exists; otherwise the group's pooled shape; otherwise uniform."""
    own = priors.get(prior_key(channel, qclass))
    if own is not None:
        return own

    group = groups.get(channel, "")
    siblings = [v for k, v in priors.items()
                if k.endswith(f"|{qclass}") and groups.get(k.split("|", 1)[0], "") == group and group]
    if siblings:
        alpha = sum(s.alpha for s in siblings) / len(siblings)
        beta = sum(s.beta for s in siblings) / len(siblings)
        return Prior(alpha=max(FLOOR, alpha), beta=max(FLOOR, beta), n=0, last_seen="")

    head_a, head_b = GROUP_HEAD_START.get(group, (FLOOR, FLOOR))
    return Prior(alpha=head_a, beta=head_b, n=0, last_seen="")
```

- [ ] **Step 4: Прогнать тесты и линтер**

Run: `python -m pytest tests/test_priors.py -q && ruff check --select F821 runner/`
Expected: PASS, 9 passed; ruff — без замечаний

- [ ] **Step 5: Коммит**

```bash
git add runner/priors.py tests/test_priors.py tests/fixtures/channels_mini.md
git commit -m "feat(swarm): Beta-модель с забыванием, полом и пулингом по группам каналов"
```

---

### Task 4: Аллокатор роя на Thompson sampling

**Files:**
- Modify: `runner/adaptive.py:73-99` (класс `Budget`)
- Test: `tests/test_allocate.py`

**Interfaces:**
- Consumes: `runner.priors.effective_prior`, `runner.priors.posterior_mean`, `runner.state.Prior`
- Produces: `Budget.allocate(qclass: str, free_slots: int, candidates: list[str], priors: dict[str, Prior], groups: dict[str, str], rng: random.Random) -> tuple[list[str], bool]` — второй элемент `fallback_used`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_allocate.py
import random
from pathlib import Path

from runner.adaptive import Budget
from runner.priors import load_channel_groups
from runner.state import Prior

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"
CANDIDATES = ["academic", "web-general", "api-direct"]


def groups():
    return load_channel_groups(FIXTURE)


def test_allocate_returns_requested_number_of_slots():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(1))
    assert len(got) == 2


def test_missing_priors_report_fallback_flag():
    b = Budget.for_depth("deep")
    channels, fallback = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(1))
    assert len(channels) == 2
    assert fallback is True  # пустые приоры — это фолбэк, и он виден снаружи


def test_populated_priors_report_no_fallback():
    b = Budget.for_depth("deep")
    priors = {"academic|pricing": Prior(3.0, 1.0, 4, "t")}
    _, fallback = b.allocate("pricing", 1, CANDIDATES, priors, groups(), random.Random(1))
    assert fallback is False


def test_fallback_is_logged_not_silent(caplog):
    import logging
    b = Budget.for_depth("deep")
    with caplog.at_level(logging.WARNING):
        b.allocate("pricing", 1, CANDIDATES, {}, groups(), random.Random(1))
    assert any("uniform" in r.message.lower() for r in caplog.records)


def test_allocate_never_repeats_a_channel():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 3, CANDIDATES, {}, groups(), random.Random(1))
    assert len(set(got)) == len(got)


def test_allocate_caps_at_candidate_count():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 99, CANDIDATES, {}, groups(), random.Random(1))
    assert len(got) == 3


def test_allocate_is_deterministic_under_a_fixed_seed():
    b = Budget.for_depth("deep")
    a, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(42))
    c, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(42))
    assert a == c


def test_strong_channel_wins_the_majority_of_draws():
    priors = {
        "academic|pricing": Prior(30.0, 1.0, 31, "t"),
        "web-general|pricing": Prior(1.0, 30.0, 31, "t"),
        "api-direct|pricing": Prior(1.0, 30.0, 31, "t"),
    }
    b = Budget.for_depth("deep")
    picks = [b.allocate("pricing", 1, CANDIDATES, priors, groups(), random.Random(s))[0][0]
             for s in range(100)]
    assert picks.count("academic") > 80


def test_weak_channel_still_gets_explored():
    priors = {
        "academic|pricing": Prior(30.0, 1.0, 31, "t"),
        "web-general|pricing": Prior(1.0, 30.0, 31, "t"),
        "api-direct|pricing": Prior(1.0, 30.0, 31, "t"),
    }
    b = Budget.for_depth("deep")
    picks = [b.allocate("pricing", 1, CANDIDATES, priors, groups(), random.Random(s))[0][0]
             for s in range(200)]
    assert picks.count("web-general") >= 1  # Thompson не запирает слабый канал навсегда


def test_zero_free_slots_yields_nothing():
    b = Budget.for_depth("shallow")
    assert b.allocate("pricing", 0, CANDIDATES, {}, groups(), random.Random(1)) == ([], False)
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_allocate.py -q`
Expected: FAIL, `AttributeError: 'Budget' object has no attribute 'allocate'`

- [ ] **Step 3: Реализовать — добавить метод в существующий класс `Budget`**

Вставить после `depth_ok` (`runner/adaptive.py:95-98`), не трогая остальной класс:

```python
    def allocate(self, qclass, free_slots, candidates, priors, groups, rng):
        """Thompson-sample `free_slots` distinct channels; report whether priors were usable.

        The fallback flag is not decoration: a silently uniform allocator looks
        identical to a working one from outside, and the tests stay green while the
        behaviour is gone. The caller writes the flag into the run report.

        Only the FREE part of the budget goes through here. The mandatory part
        (primary + secondary of different types, from source_dispatch.md) is spent
        regardless of the prior — that is what keeps triangulation intact and what
        stops the prior from confirming itself.
        """
        from runner.priors import effective_prior  # локальный импорт: adaptive не тянет state в тестах DryRun

        if free_slots <= 0 or not candidates:
            return [], False
        fallback = not priors
        if fallback:
            log.warning("priors empty or unreadable — allocating uniform for qclass=%s", qclass)
        draws = []
        for ch in candidates:
            p = effective_prior(priors, ch, qclass, groups)
            draws.append((rng.betavariate(p.alpha, p.beta), ch))
        draws.sort(reverse=True)
        return [ch for _, ch in draws[:free_slots]], fallback
```

Добавить в шапку `runner/adaptive.py` строку импорта не требуется — `random.Random` приходит от вызывающего, что и делает функцию тестируемой.

- [ ] **Step 4: Прогнать тесты, линтер и регресс по существующим**

Run: `python -m pytest tests/test_allocate.py tests/test_adaptive.py tests/test_adaptive_integration.py -q && ruff check --select F821 runner/`
Expected: PASS, 10 новых passed, существующие тесты adaptive без изменений

- [ ] **Step 5: Коммит**

```bash
git add runner/adaptive.py tests/test_allocate.py
git commit -m "feat(swarm): аллокация свободного бюджета роя через Thompson sampling"
```

---

### Task 5: Сбор наблюдений из завершённого прогона

**Files:**
- Create: `scripts/collect_observations.py`
- Test: `tests/test_collect_observations.py`
- Create: `tests/fixtures/run_mini/` (см. Step 1)

**Interfaces:**
- Consumes: `runner.state.Observation`, `runner.state.append_observation`, `runner.qclass.normalize_qclass`
- Produces: `channel_of(source_frontmatter: dict) -> str`, `rewarded_sources(claims_rows: list[dict]) -> set[str]`, `collect(research_dir: Path, run_id: str, requested: dict[str, str]) -> list[Observation]`

`requested` — отображение `channel -> qclass` для каналов, которые прогон **запрашивал**. Наблюдения строятся по нему, а не по найденным источникам: иначе канал, вернувший пустоту, не оставляет следа и не наказывается.

- [ ] **Step 1: Создать фикстуру прогона и написать падающий тест**

```bash
mkdir -p tests/fixtures/run_mini/sources
cat > tests/fixtures/run_mini/sources/01.md <<'EOF'
---
id: s1
credibility: 5
recency: 4
root: study-smith-2024
discovery_path: academic|vertical farming yield|en
origin_kind: measurement
chain_len: 0
---
Текст источника.
EOF
cat > tests/fixtures/run_mini/sources/02.md <<'EOF'
---
id: s2
credibility: 2
recency: 3
root: own
discovery_path: web-general|vertical farming market size|en
origin_kind: secondary
chain_len: 2
---
Текст источника.
EOF
cat > tests/fixtures/run_mini/claims.csv <<'EOF'
claim_id,sources,source_types,roots,paths,status,confidence,primary_source,source_caveat,dissent,as_of
c1,s1,academic,study-smith-2024,academic,triangulated,high,s1,,,2026-08-18
c2,s2,web,own,web-general,single-root,low,,,s2,2026-08-18
EOF
```

```python
# tests/test_collect_observations.py
from pathlib import Path

from scripts.collect_observations import channel_of, rewarded_sources, collect

RUN = Path(__file__).parent / "fixtures" / "run_mini"


def test_channel_extracted_from_discovery_path():
    assert channel_of({"discovery_path": "academic|запрос|en"}) == "academic"


def test_channel_of_missing_discovery_path_is_empty():
    assert channel_of({}) == ""


def test_source_in_roots_is_rewarded():
    rows = [{"claim_id": "c1", "sources": "s1", "roots": "study-smith-2024", "dissent": ""}]
    assert "s1" in rewarded_sources(rows)


def test_unpaid_dissent_is_rewarded_equally():
    rows = [{"claim_id": "c2", "sources": "s2", "roots": "own", "dissent": "s2"}]
    assert "s2" in rewarded_sources(rows)


def test_collect_marks_used_source_as_win():
    obs = collect(RUN, "r1", requested={"academic": "scientific-claim",
                                        "web-general": "market-size"})
    by_channel = {o.channel: o for o in obs}
    assert by_channel["academic"].reward == 1


def test_collect_marks_empty_channel_as_loss():
    obs = collect(RUN, "r1", requested={"academic": "scientific-claim",
                                        "forum-discussion": "sentiment"})
    by_channel = {o.channel: o for o in obs}
    assert by_channel["forum-discussion"].reward == 0  # канал отработал впустую — след остаётся


def test_collect_emits_one_observation_per_requested_channel():
    requested = {"academic": "scientific-claim", "web-general": "market-size",
                 "forum-discussion": "sentiment"}
    obs = collect(RUN, "r1", requested=requested)
    assert len(obs) == 3


def test_collect_does_not_modify_the_run_directory():
    before = sorted(p.name for p in RUN.rglob("*"))
    collect(RUN, "r1", requested={"academic": "scientific-claim"})
    assert sorted(p.name for p in RUN.rglob("*")) == before
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_collect_observations.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.collect_observations'`

- [ ] **Step 3: Реализовать**

```python
# scripts/collect_observations.py
#!/usr/bin/env python3
"""Derive swarm observations from a finished run. Read-only w.r.t. the run.

No new instrumentation is needed inside the run: sources/NN.md already carries
`discovery_path: <channel>|<query>|<lang>` and claims.csv already carries roots +
dissent. This script only folds what is already written.

Usage:
    python scripts/collect_observations.py --research-dir research/<slug> \
        --run-id <uuid> --requested academic=scientific-claim,web-general=market-size
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.qclass import normalize_qclass       # noqa: E402
from runner.state import Observation, append_observation  # noqa: E402

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Flat `key: value` reader — same contract as check_number_provenance.py."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.split("#", 1)[0].strip()
    return out


def channel_of(fm: dict[str, str]) -> str:
    """discovery_path is `<channel>|<query>|<lang>`; the channel is the first field."""
    return (fm.get("discovery_path", "") or "").split("|", 1)[0].strip()


def rewarded_sources(rows: list[dict]) -> set[str]:
    """A source earns a reward by grounding a claim OR by dissenting unrefuted.

    Dissent counts equally on purpose: reward only for confirmation teaches the
    swarm to stop looking for counter-evidence, which is Phase 6's whole job.
    """
    out: set[str] = set()
    for row in rows:
        for field in ("sources", "roots", "dissent"):
            for token in (row.get(field) or "").split(";"):
                token = token.strip()
                if token and token not in {"-", "own"}:
                    out.add(token)
    return out


def collect(research_dir: Path, run_id: str, requested: dict[str, str]) -> list[Observation]:
    research_dir = Path(research_dir)
    ledger = research_dir / "claims.csv"
    rows = list(csv.DictReader(ledger.read_text(encoding="utf-8").splitlines())) if ledger.exists() else []
    rewarded = rewarded_sources(rows)

    winning_channels: set[str] = set()
    for src in sorted((research_dir / "sources").glob("*.md")):
        fm = parse_frontmatter(src.read_text(encoding="utf-8"))
        sid = fm.get("id", "")
        ch = channel_of(fm)
        if ch and sid and sid in rewarded:
            winning_channels.add(ch)

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return [
        Observation(run_id=run_id, channel=ch, qclass=normalize_qclass(qc),
                    reward=1 if ch in winning_channels else 0, ts=ts)
        for ch, qc in sorted(requested.items())
    ]


def parse_requested(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        ch, _, qc = pair.partition("=")
        out[ch.strip()] = qc.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--requested", required=True,
                    help="channel=qclass через запятую — каналы, которые прогон запрашивал")
    ap.add_argument("--dry-run", action="store_true", help="напечатать, ничего не записывать")
    args = ap.parse_args()

    obs = collect(args.research_dir, args.run_id, parse_requested(args.requested))
    for o in obs:
        if args.dry_run:
            print(json.dumps(o.__dict__, ensure_ascii=False))
        else:
            append_observation(o)
    print(f"наблюдений: {len(obs)}, наград: {sum(o.reward for o in obs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Прогнать тесты**

Run: `python -m pytest tests/test_collect_observations.py -q`
Expected: PASS, 8 passed

- [ ] **Step 5: Коммит**

```bash
git add scripts/collect_observations.py tests/test_collect_observations.py tests/fixtures/run_mini/
git commit -m "feat(swarm): сбор наблюдений из артефактов завершённого прогона"
```

---

### Task 6: Пересчёт приоров

**Files:**
- Create: `scripts/update_priors.py`
- Test: `tests/test_update_priors.py`

**Interfaces:**
- Consumes: `runner.state.read_observations`, `runner.state.save_priors`, `runner.priors.rebuild_priors`
- Produces: `update(root: Path | None = None, lam: float = LAMBDA) -> dict[str, Prior]`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_update_priors.py
from runner.state import Observation, append_observation, load_priors
from scripts.update_priors import update


def test_update_writes_priors_from_observations(tmp_path):
    append_observation(Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path)
    append_observation(Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path)
    update(root=tmp_path)
    got = load_priors(root=tmp_path)
    assert got["academic|pricing"].n == 2


def test_update_on_empty_log_writes_empty_priors(tmp_path):
    update(root=tmp_path)
    assert load_priors(root=tmp_path) == {}


def test_update_is_idempotent_rebuild_not_accumulate(tmp_path):
    append_observation(Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path)
    first = update(root=tmp_path)
    second = update(root=tmp_path)
    assert first == second  # пересчёт из лога, а не инкремент поверх записанного
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_update_priors.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.update_priors'`

- [ ] **Step 3: Реализовать**

```python
# scripts/update_priors.py
#!/usr/bin/env python3
"""Rebuild priors.json from the observation log.

Deliberately a full rebuild, never an in-place increment: the log is primary, so a
fix to the decay formula re-derives all history instead of destroying it.

Usage:
    python scripts/update_priors.py
    python scripts/update_priors.py --lambda 0.9
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.priors import LAMBDA, rebuild_priors, posterior_mean  # noqa: E402
from runner.state import Prior, load_priors, read_observations, save_priors  # noqa: E402


def update(root: Path | None = None, lam: float = LAMBDA) -> dict[str, Prior]:
    priors = rebuild_priors(read_observations(root=root), lam=lam)
    save_priors(priors, root=root)
    return priors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lambda", dest="lam", type=float, default=LAMBDA)
    ap.add_argument("--show", action="store_true", help="напечатать топ ячеек по posterior mean")
    args = ap.parse_args()

    priors = update(lam=args.lam)
    print(f"ячеек: {len(priors)}")
    if args.show:
        ranked = sorted(priors.items(), key=lambda kv: posterior_mean(kv[1]), reverse=True)
        for key, p in ranked[:20]:
            print(f"  {posterior_mean(p):.2f}  n={p.n:<4} {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Прогнать тесты**

Run: `python -m pytest tests/test_update_priors.py -q`
Expected: PASS, 3 passed

- [ ] **Step 5: Коммит**

```bash
git add scripts/update_priors.py tests/test_update_priors.py
git commit -m "feat(swarm): пересчёт приоров из журнала наблюдений"
```

---

### Task 7: Промоушен и демоушен каталога

**Files:**
- Create: `scripts/promote_candidates.py`
- Test: `tests/test_promote_candidates.py`

**Interfaces:**
- Consumes: `runner.state.state_dir`, `runner.priors.posterior_mean`, `runner.priors.effective_prior`
- Produces: `PROMOTE_THRESHOLD = 0.3`, `MIN_WINS = 3`, `DEAD_STRIKES = 3`, `Candidate(url, channel, qclass, wins, runs, first_seen, last_probe, alive)`, `read_candidates(root=None) -> list[Candidate]`, `write_candidates(cands, root=None) -> None`, `eligible_for_promotion(c, priors, groups) -> bool`, `eligible_for_demotion(c) -> bool`, `render_source_file(c) -> str`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_promote_candidates.py
from pathlib import Path

from runner.priors import load_channel_groups
from runner.state import Prior
from scripts.promote_candidates import (
    Candidate, MIN_WINS, eligible_for_promotion, eligible_for_demotion,
    read_candidates, write_candidates, render_source_file,
)

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"
STRONG = {"api-direct|market-size": Prior(9.0, 1.0, 10, "t")}


def c(**kw):
    base = dict(url="https://api.example.org/v1", channel="api-direct", qclass="market-size",
                wins=3, runs=["r1", "r2", "r3"], first_seen="2026-07-01",
                last_probe="2026-08-18", alive=True)
    base.update(kw)
    return Candidate(**base)


def test_promotion_requires_wins_across_distinct_runs():
    assert eligible_for_promotion(c(), STRONG, load_channel_groups(FIXTURE))


def test_three_wins_in_one_run_do_not_promote():
    assert not eligible_for_promotion(c(runs=["r1", "r1", "r1"]), STRONG,
                                      load_channel_groups(FIXTURE))


def test_promotion_requires_live_endpoint():
    assert not eligible_for_promotion(c(alive=False), STRONG, load_channel_groups(FIXTURE))


def test_promotion_blocked_when_parent_channel_degraded():
    weak = {"api-direct|market-size": Prior(1.0, 20.0, 21, "t")}
    assert not eligible_for_promotion(c(), weak, load_channel_groups(FIXTURE))


def test_below_min_wins_does_not_promote():
    assert not eligible_for_promotion(c(wins=MIN_WINS - 1, runs=["r1", "r2"]), STRONG,
                                      load_channel_groups(FIXTURE))


def test_dead_endpoint_after_three_strikes_is_demoted():
    assert eligible_for_demotion(c(alive=False, wins=0, runs=["r1", "r2", "r3"]))


def test_live_endpoint_is_never_demoted():
    assert not eligible_for_demotion(c(alive=True))


def test_candidates_roundtrip(tmp_path):
    write_candidates([c()], root=tmp_path)
    got = read_candidates(root=tmp_path)
    assert got[0].url == "https://api.example.org/v1"


def test_rendered_file_carries_required_frontmatter_keys():
    text = render_source_file(c())
    for key in ("access:", "channel:", "url:"):
        assert key in text
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_promote_candidates.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.promote_candidates'`

- [ ] **Step 3: Реализовать**

```python
# scripts/promote_candidates.py
#!/usr/bin/env python3
"""Promote proven runtime sources into the catalog; flag dead ones for removal.

Promotion needs three independent facts at once, because any one of them alone is
gameable by a single lucky run: repeated wins across DISTINCT runs, a parent channel
that has not degraded, and an endpoint that answers right now.

Demotion is the other half. Without it the catalog only ever grows and its share of
dead addresses climbs silently.

Usage:
    python scripts/promote_candidates.py --dry-run
    python scripts/promote_candidates.py --write   # печатает дифф, файлы не коммитит
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.priors import effective_prior, load_channel_groups, posterior_mean  # noqa: E402
from runner.state import Prior, load_priors, state_dir  # noqa: E402

PROMOTE_THRESHOLD = 0.3
MIN_WINS = 3
MIN_DISTINCT_RUNS = 3
DEAD_STRIKES = 3

SKILL_ROOT = Path(__file__).resolve().parent.parent
CHANNELS_MD = SKILL_ROOT / "references" / "channels.md"


@dataclass
class Candidate:
    url: str
    channel: str
    qclass: str
    wins: int
    runs: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_probe: str = ""
    alive: bool = True


def read_candidates(root: Path | None = None) -> list[Candidate]:
    p = state_dir(root) / "candidates.jsonl"
    if not p.exists():
        return []
    out: list[Candidate] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Candidate(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


def write_candidates(cands: list[Candidate], root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidates.jsonl").write_text(
        "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in cands) + "\n",
        encoding="utf-8",
    )


def eligible_for_promotion(c: Candidate, priors: dict[str, Prior],
                           groups: dict[str, str]) -> bool:
    if not c.alive or c.wins < MIN_WINS:
        return False
    if len(set(c.runs)) < MIN_DISTINCT_RUNS:
        return False
    parent = effective_prior(priors, c.channel, c.qclass, groups)
    return posterior_mean(parent) >= PROMOTE_THRESHOLD


def eligible_for_demotion(c: Candidate) -> bool:
    return not c.alive and len(set(c.runs)) >= DEAD_STRIKES


def render_source_file(c: Candidate) -> str:
    return (
        "---\n"
        f"url: {c.url}\n"
        f"channel: {c.channel}\n"
        "access: api-free-no-key\n"
        f"qclass: {c.qclass}\n"
        f"first_seen: {c.first_seen}\n"
        f"promoted_after_runs: {len(set(c.runs))}\n"
        "---\n\n"
        f"# {c.url}\n\n"
        f"Промотирован автоматически: {c.wins} улик в {len(set(c.runs))} прогонах.\n"
        "Достоверность — метка разведки, не результат Фазы 5.5.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="создать файлы в api_sources/")
    ap.add_argument("--dry-run", action="store_true", default=True)
    args = ap.parse_args()

    priors = load_priors()
    groups = load_channel_groups(CHANNELS_MD)
    cands = read_candidates()

    promote = [c for c in cands if eligible_for_promotion(c, priors, groups)]
    demote = [c for c in cands if eligible_for_demotion(c)]

    for c in promote:
        target = SKILL_ROOT / "references" / "api_sources" / "promoted" / (
            c.url.replace("https://", "").replace("/", "_") + ".md")
        print(f"[promote] {c.url} -> {target.relative_to(SKILL_ROOT)}")
        print(render_source_file(c))
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_source_file(c), encoding="utf-8")

    for c in demote:
        print(f"[demote]  {c.url} — мёртв в {len(set(c.runs))} прогонах, предлагается к удалению")

    print(f"\nк промоушену: {len(promote)}, к удалению: {len(demote)}")
    if args.write:
        print("Файлы созданы. Коммит — вручную, после просмотра диффа.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Прогнать тесты**

Run: `python -m pytest tests/test_promote_candidates.py -q`
Expected: PASS, 9 passed

- [ ] **Step 5: Коммит**

```bash
git add scripts/promote_candidates.py tests/test_promote_candidates.py
git commit -m "feat(swarm): промоушен проверенных источников и вычистка мёртвых"
```

---

### Task 8: Внутрипрогонный быстрый сигнал

**Files:**
- Create: `runner/session_bandit.py`
- Test: `tests/test_session_bandit.py`

**Interfaces:**
- Consumes: `runner.state.Prior`, `runner.priors.effective_prior`, `runner.priors.FLOOR`
- Produces: `SessionBandit(priors, groups)`, `SessionBandit.observe(channel: str, qclass: str, passed_filter: bool) -> None`, `SessionBandit.view() -> dict[str, Prior]`, `SessionBandit.persisted_delta() -> dict`

Закрывает §6 спеки: рой учится **внутри** прогона на быстром сигнале (источник прошёл
`evidence_filter`), но этот сигнал живёт только в памяти. В `priors.json` уезжает
исключительно медленный сигнал из `claims.csv` (Task 5). Иначе два уровня дают две
конкурирующие истины, и расхождение нечем разрешить.

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_session_bandit.py
from pathlib import Path

from runner.priors import load_channel_groups
from runner.session_bandit import SessionBandit
from runner.state import Prior

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"


def bandit(priors=None):
    return SessionBandit(priors or {}, load_channel_groups(FIXTURE))


def test_view_starts_equal_to_base_priors():
    base = {"academic|pricing": Prior(3.0, 1.0, 4, "t")}
    assert bandit(base).view()["academic|pricing"].alpha == 3.0


def test_passing_filter_raises_channel_within_session():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    before = b.view()["academic|pricing"].alpha
    b.observe("academic", "pricing", passed_filter=True)
    assert b.view()["academic|pricing"].alpha > before


def test_failing_filter_lowers_channel_within_session():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    b.observe("academic", "pricing", passed_filter=False)
    assert b.view()["academic|pricing"].beta > 1.0


def test_unknown_cell_is_seeded_from_pooled_prior():
    b = bandit({})
    b.observe("api-direct", "market-size", passed_filter=True)
    assert "api-direct|market-size" in b.view()


def test_session_learning_is_never_persisted():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    for _ in range(10):
        b.observe("academic", "pricing", passed_filter=True)
    assert b.persisted_delta() == {}  # быстрый сигнал не уезжает в priors.json


def test_base_priors_are_not_mutated():
    base = {"academic|pricing": Prior(1.0, 1.0, 0, "t")}
    b = SessionBandit(base, load_channel_groups(FIXTURE))
    b.observe("academic", "pricing", passed_filter=True)
    assert base["academic|pricing"].alpha == 1.0  # прогон не портит межпрогонное состояние
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_session_bandit.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'runner.session_bandit'`

- [ ] **Step 3: Реализовать**

```python
# runner/session_bandit.py
#!/usr/bin/env python3
"""Within-run bandit state: fast signal, memory only.

Two learning rates, one persisted. The fast signal (a source cleared
evidence_filter) steers allocation inside the current run; the slow signal (a source
grounded a claim in the final report) is the only one that reaches priors.json.

Mixing them would give the system two competing accounts of the same channel with
no way to adjudicate between them — so this class deliberately has no writer.
"""
from __future__ import annotations

from dataclasses import replace

from runner.priors import effective_prior
from runner.state import Prior, prior_key

SESSION_WEIGHT = 0.5  # быстрый сигнал слабее медленного: фильтр судит правдоподобие, не пользу


class SessionBandit:
    def __init__(self, priors: dict[str, Prior], groups: dict[str, str]) -> None:
        self._base = priors
        self._groups = groups
        self._session: dict[str, Prior] = {}

    def observe(self, channel: str, qclass: str, passed_filter: bool) -> None:
        key = prior_key(channel, qclass)
        cur = self._session.get(key)
        if cur is None:
            seed = self._base.get(key) or effective_prior(self._base, channel, qclass, self._groups)
            cur = replace(seed)  # копия: базовые приоры прогоном не портятся
        if passed_filter:
            cur.alpha += SESSION_WEIGHT
        else:
            cur.beta += SESSION_WEIGHT
        self._session[key] = cur

    def view(self) -> dict[str, Prior]:
        """Priors as the allocator should see them right now: base overlaid with session."""
        merged = dict(self._base)
        merged.update(self._session)
        return merged

    def persisted_delta(self) -> dict:
        """Always empty. Present so the contract is visible and testable, not implied."""
        return {}
```

- [ ] **Step 4: Прогнать тесты и линтер**

Run: `python -m pytest tests/test_session_bandit.py -q && ruff check --select F821 runner/`
Expected: PASS, 6 passed

- [ ] **Step 5: Коммит**

```bash
git add runner/session_bandit.py tests/test_session_bandit.py
git commit -m "feat(swarm): внутрипрогонный быстрый сигнал без записи в межпрогонное состояние"
```

---

### Task 9: Документация — qclass в диспатче, петля в SKILL.md, мёртвые ключи

**Files:**
- Modify: `references/source_dispatch.md` (секция «Output: что записать в plan.md»)
- Modify: `references/capability_discovery.md:38-41` (таблица env)
- Modify: `references/workflow.md:375`
- Modify: `runner/capabilities.py:11-12`
- Modify: `SKILL.md` (список фаз, ~строка 41)
- Test: `tests/test_docs_swarm.py`

**Interfaces:**
- Consumes: `runner.qclass.QCLASSES`
- Produces: ничего (документация)

- [ ] **Step 1: Написать падающий тест**

```python
# tests/test_docs_swarm.py
from pathlib import Path

from runner.qclass import QCLASSES

ROOT = Path(__file__).resolve().parent.parent
DISPATCH = ROOT / "references" / "source_dispatch.md"
CAPS_MD = ROOT / "references" / "capability_discovery.md"
CAPS_PY = ROOT / "runner" / "capabilities.py"

DEAD_SEARCH_KEYS = ("TAVILY_API_KEY", "BRAVE_API_KEY", "EXA_API_KEY", "SERPAPI_KEY")


def test_dispatch_documents_qclass_field():
    text = DISPATCH.read_text(encoding="utf-8")
    assert "qclass" in text
    assert "market-size" in text


def test_every_qclass_appears_in_dispatch_doc():
    text = DISPATCH.read_text(encoding="utf-8")
    missing = [q for q in QCLASSES if q not in text]
    assert missing == [], f"классы без описания в диспатче: {missing}"


def test_dead_search_keys_are_not_advertised_as_configurable():
    text = CAPS_MD.read_text(encoding="utf-8")
    for key in DEAD_SEARCH_KEYS:
        if key in text:
            idx = text.index(key)
            window = text[max(0, idx - 400): idx + 400]
            assert "не используется" in window, (
                f"{key} упомянут без пометки о том, что скилл его не вызывает")


def test_capabilities_py_does_not_audit_unused_search_keys():
    text = CAPS_PY.read_text(encoding="utf-8")
    for key in DEAD_SEARCH_KEYS:
        assert key not in text, f"{key} аудируется, но нигде не вызывается"
```

- [ ] **Step 2: Прогнать тест, убедиться что падает**

Run: `python -m pytest tests/test_docs_swarm.py -q`
Expected: FAIL, 4 failed — `qclass` в диспатче нет, ключи аудируются

- [ ] **Step 3: Внести правки в документацию**

В `references/source_dispatch.md`, в секцию «Output: что записать в plan.md», добавить перед примером:

```markdown
### Поле `qclass`

Каждый подвопрос получает `qclass` — класс, по которому накапливается статистика
отдачи каналов. Ставится вместе с dispatch-решением, пишется в §12 рядом с каналами:

`market-size` · `time-series` · `scientific-claim` · `players` · `country-stat` ·
`how-it-works` · `recent-change` · `regulation` · `benchmark` · `sentiment` ·
`adoption` · `pricing` · `crypto` · `health` · `climate` · `jobs` · `qualitative`

Класс соответствует строке матрицы выше. Подвопрос, не попавший ни в одну строку,
получает `qclass: qualitative` и помечается как ad-hoc — как и сейчас.

Формат строки в §12:

- **qclass:** `market-size`
```

В `references/capability_discovery.md` заменить четыре строки таблицы env (38-41) на:

```markdown
| `BRAVE_API_KEY` | Brave Search | **не используется** — скилл ходит через WebSearch харнесса |
| `TAVILY_API_KEY` | Tavily | **не используется** — оставлено для внешних раннеров |
| `EXA_API_KEY` | Exa.ai | **не используется** — оставлено для внешних раннеров |
| `SERPAPI_KEY` | SerpAPI | **не используется** — оставлено для внешних раннеров |
```

и убрать `export TAVILY_API_KEY=... (1000 free/mo)` из образца отчёта (строка ~118) — фаза не должна предлагать настроить то, чего не вызывает.

В `runner/capabilities.py:11-12` убрать `"BRAVE_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "SERPAPI_KEY"` из списка аудита, оставив остальные ключи нетронутыми.

В `references/workflow.md:375` убрать `$TAVILY_API_KEY, $BRAVE_API_KEY` из перечисления.

В `SKILL.md`, в список фаз после строки про Фазу 3.5, добавить:

```markdown
7.5. **Сбор наблюдений** [без модели] — `scripts/collect_observations.py` сводит `sources/NN.md` и `claims.csv` в наблюдения роя, `scripts/update_priors.py` пересчитывает приоры. Аллокатор свободного бюджета — `Budget.allocate`, обязательная часть покрытия из `source_dispatch.md` приором не управляется. См. `docs/specs/2026-08-18-bayesian-swarm-design.md`.
```

- [ ] **Step 4: Прогнать весь набор тестов**

Run: `python -m pytest tests/ -q`
Expected: PASS, все тесты, включая существовавшие до этого плана

- [ ] **Step 5: Коммит**

```bash
git add references/source_dispatch.md references/capability_discovery.md references/workflow.md runner/capabilities.py SKILL.md tests/test_docs_swarm.py
git commit -m "docs(swarm): qclass в диспатче, петля в SKILL.md, снятие мёртвых поисковых ключей"
```

---

### Task 10: Контрольный замер

**Files:**
- Create: `docs/specs/2026-08-18-bayesian-swarm-measurement.md`

**Interfaces:**
- Consumes: всё предыдущее
- Produces: заполненная таблица результатов

Замер ручной и занимает несколько прогонов. Без него утверждение «стало лучше» — вера: аллокатор может исправно сэмплить и при этом не менять ни одного исхода.

- [ ] **Step 1: Записать протокол замера**

Создать файл со следующей таблицей и заполнять по мере прогонов:

```markdown
# Замер байесовского роя — контрольная группа

5 тем, по одной на жанр из `genres.md`. Каждая прогоняется дважды: с аллокатором
и без (переменная `DEEPDIVE_SWARM=off`). Вопрос и depth идентичны.

| Тема | Жанр | Режим | triangulated / всего claims | пустых суб-агентов | стоимость |
|---|---|---|---|---|---|
| | | on | | | |
| | | off | | | |

**Критерий успеха:** доля `triangulated` не упала И число пустых суб-агентов
снизилось. Рост доли triangulated — бонус, не требование: аллокатор экономит
бюджет, а не повышает достоверность.

**Критерий отката:** доля `triangulated` упала хотя бы на одной теме — значит
свободная часть бюджета съела покрытие, и граница между обязательной и свободной
частью проведена неверно.
```

- [ ] **Step 2: Прогнать первую пару (одна тема, on/off), заполнить строку**

- [ ] **Step 3: Прогнать оставшиеся четыре пары**

- [ ] **Step 4: Свести результат, записать вывод в конец файла**

- [ ] **Step 5: Коммит**

```bash
git add docs/specs/2026-08-18-bayesian-swarm-measurement.md
git commit -m "test(swarm): контрольный замер аллокатора против статического распределения"
```
