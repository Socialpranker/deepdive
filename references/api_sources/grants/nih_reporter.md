# NIH RePORTER API (v2)

## Overview

- **Endpoint base:** `https://api.reporter.nih.gov/v2/`
- **Auth:** None
- **Free tier:** Unlimited, no registration
- **Rate limit:** Официального numeric-лимита нет. NIH просит не более ~1 req/sec и переносить крупные batch-джобы на выходные или будни 21:00–05:00 ET; при нарушении — блокировка IP.
- **Docs:** https://api.reporter.nih.gov/ (Swagger UI, "V2.0")
- **Status page:** Выделенной status page нет. Вопросы — RePORT@mail.nih.gov
- **Coverage:** Гранты NIH и других HHS-агентств. Данные подтверждены минимум с fiscal year 1985 (0 результатов на FY1975/1980, 49 745 на FY1985)
- **Verified:** 2026-08-17

## What it returns

JSON со структурированными project-записями: суммы, PI, организация, agency/institute, fiscal year, linked publications/patents/clinical studies (через отдельные endpoints).

```json
{
  "meta": {"search_id": "...", "total": 76, "offset": 0, "limit": 2},
  "results": [{
    "appl_id": 10548235,
    "project_num": "5U01DK132737-02",
    "fiscal_year": 2023,
    "organization": {"org_name": "EMORY UNIVERSITY", "org_state": "GA"},
    "award_amount": 990010,
    "principal_investigators": [{"full_name": "Mary Beth  Weber", "is_contact_pi": true}],
    "agency_ic_admin": {"code": "DK", "abbreviation": "NIDDK", "name": "National Institute of Diabetes and Digestive and Kidney Diseases"},
    "agency_ic_fundings": [{"fy": 2023, "total_cost": 990010.0}]
  }]
}
```

## When to use

- Найти кто и сколько получил NIH-финансирования по теме/институту/PI
- Проверить funding acknowledgment биомедицинского paper
- Landscape-анализ по конкретному NIH Institute/Center (NIDDK, NCI, NIAID и т.д.)
- Связать грант с публикациями/патентами/клиническими исследованиями (через `publications/search`, `patents/search`, `clinicalstudies/search` того же v2 API)

## When not to use

- Гранты не-HHS агентств (NSF, DOE) — не покрывает
- Данные до FY1985 — не в базе
- Будущие/открытые NIH-конкурсы (funding opportunities) — RePORTER это выданные awards, не opportunities; для форкастов и открытых FOA нужен Grants.gov или grants.nih.gov/funding

## Auth setup

Не нужен. Запросы — POST с JSON body, без ключей и заголовков авторизации.

## Query patterns

### Search projects (POST)

```
POST /v2/projects/search
Content-Type: application/json

{"criteria": {"fiscal_years": [2023], "pi_names": [{"any_name": "Smith"}]}, "limit": 50, "offset": 0}
```

### By organization

```json
{"criteria": {"org_names": ["STANFORD UNIVERSITY"], "fiscal_years": [2024]}, "limit": 50}
```

### By text search (title/abstract/terms)

```json
{"criteria": {"advanced_text_search": {"operator": "and", "search_field": "projecttitle,abstracttext", "search_text": "intermittent fasting"}}, "limit": 50}
```

### By agency/IC and activity code

```json
{"criteria": {"agencies": ["NIDDK"], "activity_codes": ["R01"], "fiscal_years": [2024]}, "limit": 50}
```

### Linked publications

```
POST /v2/publications/search
{"criteria": {"appl_ids": [10548235]}, "limit": 50}
```

## Example queries

**Проверено 2026-08-17, ответ 200 (76 hits):**

```
POST https://api.reporter.nih.gov/v2/projects/search
{"criteria":{"fiscal_years":[2023],"pi_names":[{"any_name":"Collins"}]},"limit":2,"offset":0}
```

**Landscape по теме и году:**

```
POST https://api.reporter.nih.gov/v2/projects/search
{"criteria":{"advanced_text_search":{"operator":"and","search_field":"projecttitle","search_text":"vertical farming"},"fiscal_years":[2024]},"limit":50}
```

## Limitations

- Пагинация ограничена: максимум offset 14 999 для projects, 9 999 для publications; максимум 500 записей за один запрос (default 50)
- Только HHS-агентства (NIH и смежные), нет non-HHS federal grants
- Данные до FY1985 недоступны
- Жёсткая community rate-limit guidance (не формальный лимит, но риск IP-бана при агрессивном polling)
- POST-only API — GET-запросы для поиска не работают, нужен JSON body

## Combine with

- **PubMed E-utilities** (`domain_specific/pubmed.md`) — публикации по тому же PI/теме, cross-check с `agency_ic_fundings`
- **ClinicalTrials.gov** (`domain_specific/clinicaltrials.md`) — клинические испытания, привязанные к NIH-гранту
- **NSF Awards API** (`grants/nsf_awards.md`) — то же для не-медицинского федерального финансирования США
- **Grants.gov** (`grants/grants_gov.md`) — если нужны будущие/открытые NIH funding opportunities, а не выданные awards

## Fallback if API down or rate-limited

1. Пауза ~1 req/sec и повтор — при системном блоке IP нужно ждать снятия блокировки NIH admin
2. HTML-поиск через https://reporter.nih.gov/search (тот же датасет UI)
3. Bulk-выгрузка через NIH ExPORTER (https://reporter.nih.gov/exporter) — годовые CSV/XML дампы того же датасета
