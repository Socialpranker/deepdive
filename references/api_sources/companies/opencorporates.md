# OpenCorporates API

## Overview

- **Endpoint base:** `https://api.opencorporates.com/v0.4/`
- **Auth:** ⚠️ Токен обязателен — анонимного доступа больше нет. Live-проверено 2026-08-17: `GET /companies/search?...` и `GET /companies/{jurisdiction}/{number}` без токена → HTTP 401, тело `{"error":{"message":"Invalid Api Token. Please check your OpenCorporates account"}}`
- **Free tier:** Self-serve бесплатного тарифа нет. Официальная pricing-страница (opencorporates.com/pricing/, проверена 2026-08-17) начинается с платного плана. Отдельно есть безвозмездная программа для investigative journalists, NGO, университетов и anti-corruption research groups — но по заявке вручную, не self-serve и не автоматическая
- **Paid:** Essentials £2 250/год (£225/мес, до 500 вызовов/мес, 200/день), Starter £6 600/год (2 500/мес, 500/день), Basic £12 000/год (5 000/мес, 1 000/день), Enterprise — custom price
- **Docs:** https://api.opencorporates.com
- **Coverage:** 200M+ companies из company registries 130+ countries
- **Verified:** 2026-08-17

## What it returns

JSON с данные из официальных company registries — incorporation date, officers, addresses, filings.

```json
{
  "results": {
    "company": {
      "name": "Apple Inc.",
      "company_number": "C0806592",
      "jurisdiction_code": "us_ca",
      "incorporation_date": "1977-01-03",
      "officers": [...],
      "registered_address": {...}
    }
  }
}
```

## Auth setup

1. https://opencorporates.com/pricing/ → платный план (Essentials — от £2250/год) ИЛИ заявка на бесплатный доступ для journalists/NGO/researchers/anti-corruption groups через контакты OpenCorporates (рассматривается вручную, не мгновенно)
2. `export OPENCORPORATES_API_KEY="..."`
3. Передавать как `api_token={key}` query-параметр (актуальный формат не перепроверялся live — тестового токена нет; сверяться с текущей докой на api.opencorporates.com)

## Query patterns

### Search companies

```
GET /companies/search?q={query}&country_code=US&per_page=20
```

### Company details

```
GET /companies/{jurisdiction}/{company_number}
# Example: /companies/us_ca/C0806592 (Apple)
```

### Officer search

```
GET /officers/search?q={name}&per_page=20
```

## Use cases

- Find official company existence (vs marketing claims)
- Track officer/director relationships
- Verify incorporation dates
- Find parent companies, subsidiaries

## Limitations

- ⚠️ Больше не бесплатный API (live-подтверждено 2026-08-17) — платный тариф от £2250/год, либо заявка на грант для journalists/NGO/anti-corruption groups. Не использовать как "бесплатный fallback" по умолчанию
- Не финансовые данные — только registry facts
- Coverage uneven — UK/EU strong, US weaker (state-level)
- Some jurisdictions lag

## Combine with

- **Crunchbase** — для funding history
- **Companies House** (UK) — больше деталей для UK
- **SEC EDGAR** — для US public companies

## Fallback

- Direct national registries (Companies House, Bundesanzeiger, etc.)
- HTML scraping company official pages
