# NSF Awards API

## Overview

- **Endpoint base:** `https://api.nsf.gov/services/v1/`
- **Auth:** None
- **Free tier:** Unlimited, no registration
- **Rate limit:** Не задокументирован официально. Community courtesy guideline — ~1 req/sec (не подтверждено NSF документацией). 8 запросов подряд без паузы в ходе проверки прошли без 429.
- **Docs:** https://resources.research.gov/common/webapi/awardapisearch-v1.htm (общие dev resources — https://www.nsf.gov/digital/developer)
- **Status page:** Выделенной status page нет. Плановые/внеплановые простои анонсируются на https://www.research.gov
- **Coverage:** Все выданные NSF гранты, данные минимум с 1959–1969 (проверено запросом — 0 результатов на 1959, 414 на 1969)
- **Verified:** 2026-08-17

## What it returns

JSON (или XML/JSONP) со структурированными данными по award: получатель, PI, сумма, программа, даты, abstract.

```json
{
  "response": {
    "award": [{
      "id": "7001483",
      "title": "...",
      "awardeeName": "Entomological Society of America",
      "pdPIName": "DATA NOT AVAILABLE",
      "startDate": "01/01/1970",
      "expDate": "12/31/1972",
      "estimatedTotalAmt": "11000",
      "fundsObligatedAmt": "11000",
      "orgLongName": "Directorate for Computer and Information Science and Engineering",
      "fundProgramName": "",
      "abstractText": "..."
    }],
    "metadata": {"offset": 0, "rpp": 1, "totalCount": 414}
  }
}
```

## When to use

- Найти кто и сколько получил NSF-финансирования по теме/организации/штату
- Проверить funding acknowledgment из paper (NSF award number → детали гранта)
- Landscape-анализ: сколько денег NSF вложил в область за период
- Найти PI, работающих в конкретной области (для outreach/collaboration research)

## When not to use

- Гранты других агентств (NIH, DOE, DOD) — NSF Awards API покрывает только NSF
- Будущие/открытые конкурсы — это база УЖЕ ВЫДАННЫХ наград, не opportunities (для этого нужен Grants.gov)
- Массовый bulk-экспорт всей базы одним запросом — `rpp` ограничен 25 записями на страницу, для полного дампа нужна пагинация через `offset`

## Auth setup

Не нужен. Ключ/регистрация отсутствуют, лимита в 25 записей на страницу достаточно обходить через `offset`.

## Query patterns

### Keyword search

```
GET /awards.json?keyword={query}&rpp=25
```

### By awardee / PI

```
GET /awards.json?awardeeName={org}&rpp=25
GET /awards.json?pdPIName={name}&rpp=25
```

### Date range

```
GET /awards.json?dateStart={mm/dd/yyyy}&dateEnd={mm/dd/yyyy}&rpp=25
```

### Amount range

```
GET /awards.json?estimatedTotalAmtFrom={n}&estimatedTotalAmtTo={n}&rpp=25
```

### Select specific fields

```
GET /awards.json?keyword={query}&printFields=id,title,awardeeName,pdPIName,startDate,estimatedTotalAmt&rpp=25
```

### Pagination

```
GET /awards.json?keyword={query}&rpp=25&offset=26
```

## Example queries

**Проверено 2026-08-17, ответ 200:**

```
GET https://api.nsf.gov/services/v1/awards.json?keyword=quantum&rpp=2
```

Вернул 2 award записи с полным abstract, awardee, PI, суммами.

**Funding landscape по теме за год:**

```
GET https://api.nsf.gov/services/v1/awards.json?keyword=vertical+farming&dateStart=01/01/2024&dateEnd=12/31/2024&printFields=id,title,awardeeName,estimatedTotalAmt&rpp=25
```

## Limitations

- `rpp` (results per page) максимум 25 — для больших выгрузок нужна пагинация через `offset`
- Только US federal awards от NSF — нет данных по другим агентствам
- Старые записи (1960-70е) часто содержат `"DATA NOT AVAILABLE"` в полях PI/performance location
- Нет explicit rate limit в документации — риск неожиданного throttling при агрессивном polling
- `http://` эндпоинт делает 301 redirect на `https://` — используй https сразу

## Combine with

- **NIH RePORTER** (`grants/nih_reporter.md`) — та же логика для медицинских грантов
- **CrossRef** (`academic/crossref.md`) — funder-lookup `filter=funder:10.13039/100000001` (NSF funder ID) для papers, зафинансированных NSF
- **OpenAlex** (`academic/openalex.md`) — обратная связь grant → publications через funder ID
- **Grants.gov** (`grants/grants_gov.md`) — если нужны будущие/открытые конкурсы NSF, а не выданные награды

## Fallback if API down or rate-limited

1. Пауза и retry — публичного Retry-After нет, ждать вручную ~5-10 сек
2. HTML-поиск через https://www.nsf.gov/awardsearch/ (тот же датасет, ручной парсинг)
3. CrossRef funder-lookup (`academic/crossref.md`) для papers, где funder — NSF, как косвенный источник
