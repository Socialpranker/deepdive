# Grants.gov Search2 API

## Overview

- **Endpoint base:** `https://api.grants.gov/v1/api/`
- **Auth:** None для `search2` и `fetchOpportunity`. Отдельные endpoints (submission, applicant-only) требуют API key через Help Desk ticket — не относится к поиску
- **Free tier:** Unlimited, без регистрации
- **Rate limit:** Не задокументирован для `search2`/`fetchOpportunity` (10 запросов подряд без паузы в ходе проверки прошли без 429). **Не путать** с отдельным, более новым бета-API `api.simpler.grants.gov` — там официально заявлено 60 req/min / 10 000 req/day на ключ, но это другой сервис с другим auth (`X-API-Key`), не search2
- **Docs:** https://grants.gov/api/api-guide, https://grants.gov/api/common/search2
- **Status page:** Выделенной status page нет. Анонсы плановых работ — https://grants-gov.blogspot.com
- **Coverage:** Текущие/будущие федеральные US funding opportunities (posted, forecasted) + closed/archived. Archived-статус подтверждён вглубь минимум до 2004 года (72 887 hits по пустому запросу с фильтром archived, старейшие найденные — 2004)
- **Verified:** 2026-08-17

## What it returns

JSON со списком funding opportunities (не выданных грантов — это конкурсы/объявления).

```json
{
  "errorcode": 0,
  "msg": "Webservice Succeeds",
  "data": {
    "hitCount": 67,
    "oppHits": [{
      "id": "103313",
      "number": "NOAA-OAR-CPO-2012-2003041",
      "title": "Climate Program Office for FY 2012",
      "agencyCode": "DOC",
      "agency": "Department of Commerce",
      "openDate": "07/06/2011",
      "closeDate": "",
      "oppStatus": "posted",
      "docType": "synopsis",
      "cfdaList": ["11.431"]
    }]
  }
}
```

## When to use

- Найти открытые/предстоящие конкурсы на федеральные US гранты по теме, агентству, eligibility
- Мониторинг новых funding opportunities для конкретной организации/области
- Проверить статус конкретного opportunity number
- В отличие от NSF Awards / NIH RePORTER — это **будущие возможности**, а не история выданных денег

## When not to use

- Нужны уже выданные гранты (кто получил, сколько) — это Grants.gov НЕ даёт, используй `grants/nsf_awards.md` или `grants/nih_reporter.md`
- Нужен высокий throughput с гарантированным SLA/лимитами — рассмотри бета `api.simpler.grants.gov` с ключом (в разработке на 2026-08-17, схема может измениться)
- EU/non-US гранты — не покрывает, см. `grants/cordis.md`

## Auth setup

Не нужен для `search2`. Ключ не требуется, env var не нужен.

## Query patterns

### Keyword search (POST)

```
POST /v1/api/search2
Content-Type: application/json

{"keyword": "climate", "rows": 25}
```

### Фильтр по статусу конкурса

```json
{"keyword": "", "oppStatuses": "forecasted|posted", "rows": 25}
```

### Фильтр по агентству и категории финансирования

```json
{"keyword": "research", "agencies": "NSF", "fundingCategories": "ST", "rows": 25}
```

### Пагинация

```json
{"keyword": "climate", "rows": 25, "startRecordNum": 25}
```

### Получить конкретный opportunity (fetchOpportunity)

```
POST /v1/api/fetchOpportunity
{"opportunityId": "103313"}
```

## Example queries

**Проверено 2026-08-17, ответ 200, hitCount 67:**

```
POST https://api.grants.gov/v1/api/search2
{"keyword": "climate", "rows": 2}
```

**Проверено 2026-08-17, ответ 200, hitCount 72887 (archived-фильтр без keyword):**

```
POST https://api.grants.gov/v1/api/search2
{"keyword": "", "oppStatuses": "archived", "rows": 3, "sortBy": "openDate|asc"}
```

## Limitations

- Только US federal opportunities — не покрывает state/local/private гранты
- Даёт объявления о конкурсах, НЕ данные о выданных грантах — для этого нужны NSF/NIH-специфичные API
- Официального rate limit нет — риск неожиданного throttling при агрессивном использовании; для serious production integration Grants.gov рекомендует отдельный ключевой gateway
- Схема ответа местами напоминает legacy SOAP-обёртку в JSON (`errorcode`/`msg`/`token`) — не чистый REST-дизайн

## Combine with

- **NSF Awards API** (`grants/nsf_awards.md`) — после того как конкурс закрылся и гранты выданы, ищи их здесь
- **NIH RePORTER** (`grants/nih_reporter.md`) — то же для NIH funding opportunities → выданных грантов
- **CORDIS** (`grants/cordis.md`) — EU-эквивалент для розыска уже профинансированных проектов после конкурса
- **SEC EDGAR** (`financial/sec_edgar.md`) — если получатель гранта public company, для financial context

## Fallback if API down or rate-limited

1. Retry с паузой — публичного Retry-After не обнаружено, ждать вручную
2. HTML-поиск через https://grants.gov/search-grants (тот же датасет UI)
3. RSS/email alerts через https://grants.gov (подписка на конкретные категории — не для агента, но пригодится пользователю)
