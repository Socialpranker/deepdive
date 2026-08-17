# CORDIS (EU-funded research projects)

## Overview

- **Endpoint base:** Официального REST/JSON search API у CORDIS нет. Реальные варианты доступа:
  - Bulk-датасеты: `https://cordis.europa.eu/data/cordis-{programme}projects-{format}.zip`
  - SPARQL: `https://cordis.europa.eu/datalab/sparql-endpoint`
  - Search UI с экспортом: `https://cordis.europa.eu/search/en?q={query}&format={json|csv|xml}` — **не задокументирован официально**, но публичный и рабочий (used by cordis.europa.eu сайтом же)
- **Auth:** None ни для одного из вариантов
- **Free tier:** Unlimited
- **Rate limit:** Не задокументирован ни для одного метода (не подтверждено на 2026-08-17)
- **Docs:** https://cordis.europa.eu/about/services (официальный обзор способов доступа). Search-JSON endpoint нигде не описан как публичный API — обнаружен и проверен вручную, использовать с осторожностью
- **Status page:** Выделенной status page нет
- **Coverage:** Проекты FP1–FP7, H2020, Euratom, Horizon Europe (2021–2027). Bulk-файл HORIZON обновлён 2026-08-06 (актуально), FP7-файл — статичен с 2025-01-02 (программа закрыта)
- **Verified:** 2026-08-17

## What it returns

- **Bulk (CSV/XML/JSON zip):** полные датасеты по программе — projects, organizations, deliverables, publications, topics, legal basis, EuroSciVoc-классификация
- **SPARQL:** linked-data триплеты, гибкий произвольный запрос по RDF-графу CORDIS
- **Search-JSON (недокументированный):** структура вида

```json
{
  "result": {"header": {"search": {"properties": {"query": {...}}}, "numHits": "2", "totalHits": "25598"}},
  "hits": {"hit": [{
    "@attributes": {"score": "8.31"},
    "project": {
      "contenttype": "project",
      "rcn": "253870",
      "id": "101108476",
      "acronym": "HyNNet NISQ",
      "teaser": "...",
      "objective": "..."
    }
  }]}
}
```

## When to use

- Найти EU-финансируемые проекты по теме (Horizon Europe, H2020, FP7 и раньше)
- Получить участвующие организации и их роли (coordinator/participant) по гранту
- Массовый анализ EU R&I funding landscape за framework programme (через bulk CSV)
- Cross-check funding acknowledgment европейской статьи с реальным грантом (Grant Agreement Number)

## When not to use

- Нужен live programmatic search с гарантией стабильности контракта — используй bulk-датасеты, а не search-JSON endpoint (он не публичный API, может измениться без анонса)
- US federal гранты — не покрывает (см. `grants/nsf_awards.md`, `grants/nih_reporter.md`)
- Нужны данные в реальном времени по свежеподанным заявкам — CORDIS публикует уже одобренные/подписанные проекты, а не заявки на рассмотрении

## Auth setup

Не нужен ни для одного из методов доступа.

## Query patterns

### Bulk download по программе (актуальный zip)

```
GET https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip
GET https://cordis.europa.eu/data/cordis-HORIZONprojects-json.zip
GET https://cordis.europa.eu/data/cordis-h2020projects-csv.zip
GET https://cordis.europa.eu/data/cordis-fp7projects-csv.zip
```

### Search-JSON (недокументированный, но рабочий)

```
GET https://cordis.europa.eu/search/en?q={query}&format=json&num=10
```

### Фильтр по типу контента (только проекты)

```
GET https://cordis.europa.eu/search/en?q=contenttype='project' AND {query}&format=json&num=10
```

### CSV-экспорт результатов поиска

```
GET https://cordis.europa.eu/search?q=contenttype='project'&format=csv
```

### SPARQL (для сложных linked-data запросов)

```
POST https://cordis.europa.eu/datalab/sparql-endpoint
Content-Type: application/sparql-query
```

## Example queries

**Проверено 2026-08-17, ответ 200, totalHits 25598:**

```
GET https://cordis.europa.eu/search/en?q=quantum&format=json&num=2
```

**Проверено 2026-08-17, ответ 200, totalHits 3324 (только проекты):**

```
GET https://cordis.europa.eu/search/en?q=contenttype='project' AND quantum&format=json&num=1
```

**Проверено 2026-08-17, HEAD 200, content-length 36 672 015 bytes:**

```
HEAD https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip
```

## Limitations

- Нет официального REST API с гарантированным контрактом — search-JSON endpoint не документирован CORDIS, использовать с пониманием, что он может измениться
- Bulk-датасеты обновляются раз в месяц, не real-time
- Данные — только про уже одобренные/подписанные проекты, не про conkурсы в процессе рассмотрения
- CSV-структура с semicolon-разделителем, требует парсинга (не запятая)
- SPARQL требует знания RDF/SPARQL синтаксиса — высокий порог входа

## Combine with

- **CrossRef** (`academic/crossref.md`) — funder-lookup `filter=funder:10.13039/501100000780` (EU Commission funder ID) для papers, зафинансированных Horizon Europe/H2020
- **OpenAlex** (`academic/openalex.md`) — обратная связь EU grant → publications
- **NSF Awards API** (`grants/nsf_awards.md`) / **NIH RePORTER** (`grants/nih_reporter.md`) — аналоги для US federal funding

## Fallback if API down or rate-limited

1. Bulk zip-датасет вместо search-JSON — стабильнее, не зависит от недокументированного endpoint
2. CORDIS Data Extraction Tool (требует регистрации): https://cordis.europa.eu/user/dataextractions
3. WebFetch страницы `https://cordis.europa.eu/search?q={query}` (HTML-версия того же поиска)
