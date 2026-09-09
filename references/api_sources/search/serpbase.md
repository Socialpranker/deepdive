# SerpBase (Google SERP API)

## Overview

- **Endpoint base:** `https://api.serpbase.dev`
- **Auth:** API key (header `X-API-Key`)
- **Free tier:** 100 free searches на регистрацию, без кредитной карты
- **Paid:** pay-as-you-go, ~$0.30/1000 queries, без подписки
- **Docs:** https://serpbase.dev
- **Unique:** **реальный Google organic** через REST — без HTML-парсинга и CAPTCHA-армс-рейса (в отличие от SerpAPI — платного, без free tier)

## What it returns

JSON с парсированными Google SERP — organic results. Бизнес-ошибки приходят как HTTP 200 с ненулевым `status` + `message`.

```json
{
  "status": 0,
  "organic": [
    {
      "position": 1,
      "title": "...",
      "link": "https://...",
      "snippet": "...",
      "display_link": "..."
    }
  ],
  "related_searches": ["...", "..."],
  "knowledge_graph": { "title": "..." }
}
```

## When to use

- Нужен **реальный Google** ranking — SEO research, competitive intel, GEO/AEO
- Google-specific features (knowledge graph, related searches, AI Overviews)
- Когда WebSearch харнесса не даёт Google organic (или даёт через HTML, который ломается)
- Локальные Google (hl/gl) — региональная выдача

## When not to use

- General research — Tavily/Brave дешевле для простых фактов
- Semantic «similar to this article» — Exa лучше
- Когда Google-специфика не нужна

## Auth setup

1. https://serpbase.dev → sign up
2. 100 free searches, ключ из dashboard
3. В env: `export SERPBASE_API_KEY="..."`

## Query patterns

Прямой вызов из скилла: `python3 scripts/search_query.py --engine serpbase --query "..." [--n 10] [--json]`
(читает `SERPBASE_API_KEY` из env, exit 2 если ключа нет). Ниже — сырой HTTP-контракт,
который скрипт реализует.

### Google organic search

```
GET https://api.serpbase.dev/google/search
Headers: X-API-Key: {SERPBASE_API_KEY}
Accept: application/json

Params: q={query}&num=10   # опционально: hl, gl — локаль выдачи
```

Нормализация в скилле: `organic[]` → `{rank, title, url: link, snippet, engine: "serpbase", fetched_at}` — тот же контракт, что у brave/tavily/exa.

## Example queries для deepdive

**Phase 4 — текущий Google-рейтинг по теме отчёта:**

```
GET /google/search?q=market+microstructure+prediction+markets&num=10&hl=en
Headers: X-API-Key: {SERPBASE_API_KEY}
```

**Phase 4 — competitive intel (что Google реально ранжирует сейчас):**

```
GET /google/search?q=postgres+logical+replication+vs+cdc&num=10
```

## Limitations

- Google organic без «own index» — это снимок реальной выдачи Google, а не независимый от Google индекс (для триангуляции это отдельная траектория: другой канал, чем WebSearch харнесса)
- Платный сверх free tier — но pay-as-you-go без подписки
- Не семантический поиск — keyword-based

## Combine with

- **Brave/Tavily** — для broader coverage / answers с sources
- **Exa** — для semantic «find similar»
- **WebSearch харнесса** — как вторая Google-траектория для overlap_rate (search-engine-2 ось)

## Fallback if API down or rate-limited

1. Brave Search
2. Tavily с `search_depth: advanced`
3. Standard WebSearch через харнесс
