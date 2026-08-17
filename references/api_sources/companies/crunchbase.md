# Crunchbase Basic API

## Overview

- **Endpoint base:** `https://api.crunchbase.com/api/v4/`
- **Auth:** API key (`user_key` query-параметр или `X-cb-user-key` заголовок — оба подтверждены официальной докой data.crunchbase.com/docs/using-the-api)
- **Free tier:** Self-serve бесплатной покупки/trial на 2026-08-17 не найдено. Официальная дока прямо отправляет на "Contact us to explore API pricing" — Full API только по Enterprise/Applications лицензии, custom price. Упоминается план "Crunchbase Basic", ограниченный подмножеством "Basic APIs" — его цена нигде не публикуется
- **Paid:** не подтверждено на 2026-08-17. Ни "$99/mo Basic" (наша старая цифра), ни "$49/мес" (из внешней разведки) не встретились на официальных страницах about.crunchbase.com/products/data-licensing и data.crunchbase.com/docs/using-the-api — обе отправляют на sales-конверсацию без цифр. Похоже, оба числа на самом деле про подписку **Crunchbase Pro** (веб-платформа поиска/экспорта) — это другой продукт, не Data API
- **Docs:** https://data.crunchbase.com/docs/getting-started
- **Coverage:** Startup data — funding rounds, founders, acquisitions, valuations
- **Verified:** 2026-08-17

## What it returns

JSON с organization data, funding events, people, news.

## Auth setup

1. https://about.crunchbase.com/products/data-licensing → "Contact us" (self-serve на 2026-08-17 не найден; `www.crunchbase.com/api` из старой версии этого файла сейчас блокирует прямой curl-запрос — 403)
2. `export CRUNCHBASE_API_KEY="..."`

## Query patterns

### Organization details

```
GET /entities/organizations/{uuid}?field_ids=name,short_description,founded_on,total_funding_amount&user_key={key}
```

### Search organizations

```
POST /searches/organizations
Body: {
  "query": [{"type": "predicate", "field_id": "industries", "operator_id": "includes", "values": ["fintech"]}],
  "field_ids": ["name", "short_description", "total_funding_amount"],
  "limit": 50
}
```

### Funding rounds

```
GET /entities/funding_rounds/{uuid}
```

## Example queries для deep-research

**Phase 4 — competitive landscape:**

```
POST /searches/organizations
{
  "query": [
    {"type": "predicate", "field_id": "industries", "operator_id": "includes", "values": ["prediction markets"]},
    {"type": "predicate", "field_id": "founded_on", "operator_id": "gte", "values": ["2018-01-01"]}
  ],
  "field_ids": ["name", "total_funding_amount", "investor_identifiers", "founded_on"],
  "limit": 50
}
```

## Limitations

- **Paid** для серьёзного использования, цена — по запросу в sales (custom, не публикуется)
- Free trial в текущей публичной доке не упомянут (не подтверждено на 2026-08-17, было в старой версии этого файла)
- Data quality лучше для US/EU startups, слабее для Asia

## Combine with

- **OpenCorporates** — для company registry data (⚠️ больше не free — с 2026 платный, от £2250/год, либо заявка на грант для journalists/NGO; см. `opencorporates.md`)
- **PitchBook** — alternative (paid, comprehensive)
- **AngelList/Wellfound** — для startup jobs

## Fallback

- HTML scrape Crunchbase profiles
- Latka SaaS revenue database
- Company's own about page + LinkedIn
