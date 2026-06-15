# Phase 7 — Refresh targets generation — Design

**Дата:** 2026-06-15
**Ветка:** `feat/phase7-refresh`
**Статус:** design approved, готов к writing-plans

## Цель

Финальная фаза прогона генерирует `<slug>/refresh_targets.md` — точку входа для
будущего дельта-ресёрча `update <slug>`. Файл описывает что перепроверять при
обновлении: гипотезы, entities, numbers, topic markers, carry-forward кандидаты.

Спека: `references/refresh_protocol.md`, `references/workflow.md:542-565`,
шаблон Z11 в `references/blocks/close.md:396-514`.

## Ключевой контекст (проверено в коде)

`synthesize()` (orchestrator.py:284-298) сейчас — **scaffold**: пишет только
`# {question}` + TL;DR-плейсхолдер + Counter-arguments. Блоков M2/M5/N1-N8/
C1-C5/A4, по которым спека Z11 предлагает извлекать entities/numbers/гипотезы,
в отчёте **физически нет** (block-render отчёта не реализован).

**Вывод:** источник данных Phase 7 — не парсинг финального отчёта, а `RunState`
(то, что реально живёт после фаз 1-6.5):
- `s.hypotheses: list[str]` — H1-H4 (Phase 1)
- `s.sources: list[dict]` — url/claim/id/score (Phase 4-5)
- `s.triangulation: list[dict]` — статус гипотез (Phase 5)
- `<slug>/deviations.md` — `not_pursued` записи с `carry_forward`
  (формат подтверждён: adaptive.py:115,137,277 — `- carry_forward: <текст>`)

Чего в `RunState` структурно нет (pricing/careers URL split, sha256-hash,
FRED series id, last_value, OpenAlex concept IDs, GitHub topics) — в выводе
помечается явным `<!-- TODO: ... -->`, **не выдумывается**. Эти секции
заполнятся, когда будет реализован block-render отчёта (M-/N-блоки) и discovery-
метаданные в `RunState`.

## Архитектура

Паттерн фазы, устоявшийся за 3 предыдущие (scoring/capabilities/verify):
чистый модуль `runner/refresh.py` (pure, без сети, без I/O) + метод
`Orchestrator.refresh(s)` в `orchestrator.py` (читает `s`, пишет файл).

**Сеть: ноль. Subprocess: ноль.** Значит run()-тесты остаются оффлайн by
design — нечего делать opt-in (урок `phase65-verify` соблюдён: там сеть в
check_citations пришлось прятать за `verify_live`; здесь сети нет вообще).

### `runner/refresh.py` (новый, pure)

| Функция | Вход | Выход | Данные |
|---|---|---|---|
| `extract_hypotheses(hypotheses, triangulation)` | `list[str]`, `list[dict]` | `list[dict]` (id, text, status, supporting_types) | реальные |
| `extract_entities(sources)` | `list[dict]` | `list[dict]` (domain, url, why) дедуп по домену | реальные (частичные) |
| `extract_numbers(sources)` | `list[dict]` | `list[dict]` (url, phrase) | эвристика |
| `extract_carry_forward(deviations_text)` | `str` | `list[dict]` (subquestion, carry_forward) | реальные |
| `render_refresh_targets(topic, depth, hyps, entities, numbers, carry, *, today)` | всё выше + дата | `str` markdown Z11 | — |

`today` прокидывается параметром (не `dt.date.today()` внутри) — render остаётся
детерминированным в юнит-тесте. Парсинг `Hn:` переиспользует
`scoring.hypothesis_ids()` — не дублировать regex.

### `Orchestrator.refresh(s)` (orchestrator.py)

```python
def refresh(self, s: RunState) -> None:
    if s.depth == "shallow":
        return  # гейт, как Phase 3.5 capability discovery
    try:
        devs_text = (s.dir / "deviations.md").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        devs_text = ""  # graceful, как verify()
    hyps = extract_hypotheses(s.hypotheses, s.triangulation)
    entities = extract_entities(s.sources)
    numbers = extract_numbers(s.sources)
    carry = extract_carry_forward(devs_text)
    content = render_refresh_targets(
        s.slug, s.depth, hyps, entities, numbers, carry,
        today=dt.date.today().isoformat())
    (s.dir / "refresh_targets.md").write_text(content, encoding="utf-8")
```

В `run()`: `self.refresh(s)` после `self.verify(s)`, перед `return s.dir`.

## Поведение extract-функций

**`extract_hypotheses`** — данные реальные:
- `s.hypotheses` → id+text через `hypothesis_ids()`.
- статус из `s.triangulation`: supporting types и не under_triangulated →
  `supported`; under_triangulated → `inconclusive`; нет записи → `inconclusive`.
- watch-паттерны генерим шаблонно из текста (`"<phrase> failed replication"`,
  RetractionWatch) — детерминированно, не сеть.

**`extract_entities`** — частичные:
- из `s.sources`: url + claim + id; дедуп по домену url.
- TODO-маркер про pricing/careers split + hash.

**`extract_numbers`** — эвристика:
- source «numeric» если в `claim` есть число (`\d`) ИЛИ домен из
  {fred, worldbank, statista, oecd}; иначе пропуск.
- TODO-маркер про series id + last_value + API.

**`extract_carry_forward`** — реальные:
- парсинг `- carry_forward: <текст>` + subquestion записи. Пусто → `[]`.

**topic markers** — отдельной функции нет; секция 3 Z11 = заголовок +
TODO-маркер (OpenAlex/GitHub не хранятся в `RunState`).

## Формат `refresh_targets.md`

Frontmatter + 5 секций Z11:

```markdown
---
slug: <slug>
last_research_date: <YYYY-MM-DD>
depth: <medium|deep>
parent_report: <YYYY-MM-DD>_<genre>.md
update_cadence: <90 days for medium / 30 days for deep>
---

# Refresh targets — <topic>

## 1. Entities to track
### <domain>
- **Source URL:** <url>
- **Why in scope:** <claim>
<!-- TODO: pricing/careers/crunchbase split + sha256 hash — требуют M2/M5 block-render -->

## 2. Numbers to refresh
### <metric phrase>
- **Source:** <url>
<!-- TODO: series id + last_value + API access — требуют N-block render -->

## 3. Topic markers (discovery)
<!-- TODO: OpenAlex concept IDs / GitHub topics / news keywords — требуют Phase 4 discovery-метаданных в RunState -->

## 4. Hypotheses to re-test
### H1: "<text>"
- **Status at last research:** <supported|inconclusive>
- **Supporting source types:** <N> (<types>)
- **Watch for:** "<phrase> failed replication"; retractions (RetractionWatch); counter-evidence

## 5. Refresh candidates (carry-forward)
- **<subquestion>** — <carry_forward text>
```

`update_cadence`: medium → 90 дней, deep → 30 дней (константа из depth;
anti-pattern Z11 «без update_cadence»).

TODO-маркеры машинно-видимы — будущий block-render просто грепнет `<!-- TODO`.

## Edge-cases (все graceful, не падать — урок verify())

| Случай | Поведение |
|---|---|
| `s.depth == "shallow"` | ранний `return`, файл не создаётся |
| `deviations.md` отсутствует | секция 5 = `_none_`, не падать |
| `s.hypotheses` пуст | секция 4 = `_no hypotheses recorded_` |
| `s.sources` пуст | секции 1-2 = `_none_` |
| `s.triangulation` пуст | статус гипотез → `inconclusive` |

Идемпотентность: повторный `run()` перезаписывает файл целиком
(как `triangulation.md`/`plan.md`, не аппендит).

## Тесты

`tests/test_refresh.py` — юнит (голые dict/строки, детерминированно):

1. `test_extract_hypotheses_maps_status`
2. `test_extract_entities_dedups_by_domain`
3. `test_extract_numbers_filters_numeric`
4. `test_extract_carry_forward_parses_deviations`
5. `test_render_is_deterministic` (фикс `today` → байт-в-байт)
6. `test_render_emits_todo_markers`
7. `test_render_handles_empty`

Оффлайн через `run()` (DryRunProvider, как test_orchestrator_verify.py):

8. `test_run_generates_refresh_targets` (medium → файл + 5 заголовков + frontmatter)
9. `test_refresh_skipped_for_shallow` (shallow → файла нет)
10. `test_refresh_offline_no_network` (файл создан без `verify_live`, suite ~1s)

## Урок схем (проверен, неприменим)

JSON-схемы в Phase 7 **нет** — extract из `RunState`, рендер строковый.
Guard-тест `test_signals_schema_is_structured_output_safe` расширять **не нужно**,
риск HTTP 400 не возникает (урок `anthropic-structured-output-schema-limits`
проверен и неприменим к этой фазе).

## Верификация перед мерджем

- `pytest` (ожидаем ~152 зелёных: 142 + 10)
- `ruff check`
- финальный code-review субагентом (как 3 предыдущие фазы)

Мердж в main — по явному подтверждению пользователя. Push/PR не делаем.
