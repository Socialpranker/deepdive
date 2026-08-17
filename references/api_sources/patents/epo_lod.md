# EPO Linked Open Data

## Overview

- **Endpoint base:** `https://data.epo.org/linked-data/query` (SPARQL endpoint, Apache Jena Fuseki)
- **Auth:** None
- **Free tier:** Unlimited (публично заявленной квоты/лимита не найдено — сервис описан EPO как открытый для occasional use через query interface, для heavy use рекомендован bulk download)
- **Rate limit:** не задокументировано и не подтверждено на 2026-08-17 — отдельной страницы про rate limits для data.epo.org (в отличие от OPS, у которого есть fair-use charter) найти не удалось
- **Docs:** https://www.epo.org/en/searching-for-patents/data/linked-open-data
- **Status page:** отдельной status-страницы для data.epo.org не найдено; см. общий https://www.epo.org/en/service-support/status-online-services
- **Verified:** 2026-08-17

Live-проверка 2026-08-17 — реальный SPARQL-запрос без auth, полный успешный ответ:
```
curl -G "https://data.epo.org/linked-data/query" \
  --data-urlencode "query=SELECT DISTINCT * WHERE { <http://data.epo.org/linked-data/id/application/EP/01903571> ?p ?o . } LIMIT 5" \
  -H "Accept: application/sparql-results+json"
→ HTTP 200, вернул applicationAuthority, applicationNumber, filingDate, grantDate и т.д.
```

## What it returns

RDF-триплы. Через SPARQL endpoint — JSON (`application/sparql-results+json`), XML или HTML (в зависимости от `Accept`). Данные — библиографика EP-заявок и публикаций: номера, даты подачи/выдачи, applicant/inventor, классификации, связи между заявкой и публикацией и т.д., линкуемые через URI вида `http://data.epo.org/linked-data/id/...`.

```json
{
  "head": {"vars": ["p", "o"]},
  "results": {
    "bindings": [
      {"p": {"type": "uri", "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"},
       "o": {"type": "uri", "value": "http://data.epo.org/linked-data/def/patent/Application"}},
      {"p": {"type": "uri", "value": "http://data.epo.org/linked-data/def/patent/filingDate"},
       "o": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#date", "value": "2001-01-20"}}
    ]
  }
}
```

## When to use

- Нужен произвольный граф-запрос по связям патентных данных (SPARQL) без OAuth-обвязки OPS
- Быстрый bibliographic lookup по известному номеру заявки/публикации без регистрации
- Связывание патентных данных с другими linked-data источниками (общий web of data подход через URI)
- Прототипирование/исследование данных без квот и авторизации

## When not to use

- Нужен full-text (claims/description) — LOD покрывает в первую очередь библиографику, не полный текст (для этого OPS `/fulltext` или Espacenet)
- Не знаком со SPARQL и нет времени разбираться в синтаксисе — тогда проще OPS REST или Espacenet UI
- Нужны гарантии по SLA/rate limit — у LOD, в отличие от OPS, нет опубликованной fair-use политики, что означает и отсутствие официальных гарантий доступности при больших нагрузках

## Auth setup

Не требуется. Публичный SPARQL endpoint, ключ/токен не нужен.

## Query patterns

### Получить все свойства ресурса по URI

```
GET /linked-data/query?query=SELECT DISTINCT * WHERE { <{URI}> ?p ?o . } LIMIT 100
Accept: application/sparql-results+json
```

### Найти заявку по номеру (пример конкретного URI-паттерна)

```
URI: http://data.epo.org/linked-data/id/application/{authority}/{number}
# authority = ST.3 код ведомства, например EP
```

### POST-запрос (для длинных SPARQL-запросов)

```
POST /linked-data/query
Content-Type: application/x-www-form-urlencoded
Body: query=SELECT ... (urlencoded)
```

## Example queries

Реальный, проверенный live 2026-08-17 запрос и подтверждённый ответ:

```bash
curl -G "https://data.epo.org/linked-data/query" \
  --data-urlencode "query=SELECT DISTINCT * WHERE { <http://data.epo.org/linked-data/id/application/EP/01903571> ?p ?o . } LIMIT 5" \
  -H "Accept: application/sparql-results+json"
```

Ответ (сокращённо):
```json
{"p": ".../applicationNumber", "o": {"value": "01903571"}}
{"p": ".../filingDate", "o": {"value": "2001-01-20"}}
{"p": ".../grantDate", "o": {"value": "2006-08-16"}}
```

## Limitations

- URI-схема данных немного путаная в документации: старые URI шли под `http://data.epo.org/linkeddata/...` (без дефиса), актуальный endpoint — `linked-data` (с дефисом); при построении запросов сверяться с реальными URI из ответов, а не собирать их вручную по догадке
- Нет опубликованного SLA/rate limit — при интенсивном использовании нет формальной гарантии, в отличие от OPS с явной fair-use политикой
- Покрытие — в первую очередь EP (европейские) заявки/публикации, не замена OPS по глубине данных (legal status, family, full-text представлены слабее)
- Формат ответа зависит от `Accept`-заголовка — если не указать, можно получить HTML вместо JSON

## Combine with

- **EPO OPS** (`epo_ops.md`) — для full-text, legal status, patent family — того, что LOD не покрывает
- **USPTO ODP** (`uspto_odp.md`) — для симметричных US-данных
- **CrossRef / OpenAlex** (`academic/`) — если патент цитирует или цитируется научной литературой, для triangulation

## Fallback if API down or rate-limited

1. Bulk download полного датасета (упоминается на странице EPO как опция для heavy use, детали — на epo.org/en/searching-for-patents/data/linked-open-data)
2. EPO OPS (`epo_ops.md`) — REST/XML вместо SPARQL, для тех же bibliographic данных
3. WebFetch на Espacenet UI для ручного разового поиска
