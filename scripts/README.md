# Scripts

Automation для catalog maintenance — плюс run-time инструменты прогона (`build_sources_csv.py`, `validate_phases.py`).

## finish.py

One finish-up command: `python scripts/finish.py --research-dir research/<slug> [--mode medium] [--offline]`.
Runs build_sources_csv → check_citations (into `.verify/citations.json`) → wiki_ingest →
check_number_provenance --strict → check_number_arithmetic --strict → validate_phases --strict,
never stopping early; exit 1 if any step failed. `--offline` skips the liveness check.

## search_query.py

Прямой вызов одного из трёх поисковых движков с free tier — второй, независимой от
харнесс-WebSearch поисковой траектории (см. `references/capability_discovery.md`,
`references/source_dispatch.md`):

```bash
python3 scripts/search_query.py --engine {brave,tavily,exa} --query "..." [--n 10] [--json]
```

Ключ читается из env: `BRAVE_SEARCH_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`. Без
ключа — exit 2 с именем переменной. HTTP-ошибка — exit 1. Один ретрай при обрыве
транспорта, timeout 20s. Без `--json` печатает `NN  title — url` построчно;
`--json` — нормализованный список `{rank, title, url, snippet, engine, fetched_at}`.

## build_sources_csv.py

Собирает `sources.csv` прогона из `sources/NN.md` frontmatter — детерминированно, вместо
ручного grep|sed. `sources/NN.md` — источник истины; CSV — индекс, который читают
`check_citations.py`, `validate_structure.py`, `score_run.py`. Колонки в нижнем регистре
под контракт этих читателей (REQUIRED `url,title`; RECOMMENDED `type,channel`).

```bash
python scripts/build_sources_csv.py --research-dir research/<slug>
python scripts/build_sources_csv.py --research-dir research/<slug> --check   # exit 1 если stale (CI)
```

Прогонять как шаг 0 finish-up (см. `SKILL.md`), перед `validate_phases.py`.

## validate_phases.py

Phase-gate для завершённого прогона: проверяет, что каждая обязательная для режима
фаза оставила свой артефакт. Ловит «модель пропустила фазу» — главный failure mode
скилла (методология исполняется только дисциплиной модели). Не форматный валидатор
(`eval/validate_structure.py`) и не оценка качества (`eval/score_run.py`) — проверяет
именно полноту фаз. Читает `phases.yaml` через `phases_manifest` (без своего YAML-парсера).

```bash
python scripts/validate_phases.py --research-dir research/<slug>            # авто-детект mode из frontmatter
python scripts/validate_phases.py --research-dir research/<slug> --mode deep
python scripts/validate_phases.py --research-dir research/<slug> --strict   # exit 1 при ошибке (для CI)
python scripts/validate_phases.py --research-dir research/<slug> --json
```

Обязательный набор по режимам: shallow — `plan.md`, `sources/` или `sources.csv`,
`claims.csv`, финальный отчёт; medium/deep — плюс `evidence/`, `.verify/*.json`,
`refresh_targets.md`. Прогонять как шаг 1 finish-up (см. `SKILL.md`).

## validate_endpoints.py

Health-check all API endpoints in `references/api_sources/`.

```bash
pip install -r scripts/requirements.txt
python scripts/validate_endpoints.py
```

Output: `scripts/output/endpoints_report.md`

Flags:
- `--json` — also write JSON report
- `--strict` — exit code 1 if any endpoint dead (for CI)

## sync_catalog.py

Discover potential additions from upstream awesome-lists.

```bash
python scripts/sync_catalog.py
python scripts/sync_catalog.py --upstream public-apis  # specific upstream
python scripts/sync_catalog.py --limit 50  # show more per upstream
```

Output: `scripts/output/sync_report.md`

## Manual workflow

```bash
# Weekly maintenance ritual:
python scripts/validate_endpoints.py
python scripts/sync_catalog.py

# Review outputs in scripts/output/
# Fix dead endpoints, propose additions via PR
```

## Automated via GitHub Actions

See `.github/workflows/catalog-sync.yml` — runs every Sunday at 03:00 UTC.

On schedule:
1. Validate all endpoints
2. Discover upstream additions
3. If dead endpoints found OR significant new additions → open PR with reports
4. Otherwise: just commit reports to `scripts/output/`

## Output directory

`scripts/output/` is `.gitignored` for local runs. GitHub Actions commits reports to a dedicated `reports/` branch.
