# SerpAPI

## Overview

- **Endpoint base:** `https://serpapi.com/search.json`
- **Auth:** API key (query param `api_key`)
- **Free tier:** 100 searches/month
- **Paid:** $50/mo для 5000 searches, scales up
- **Docs:** https://serpapi.com/search-api
- **Unique:** Real Google results (also Bing, DuckDuckGo, Yandex, Baidu)

## What it returns

JSON с парсированными SERP (Search Engine Results Pages) — organic results, ads, knowledge panels, related searches.

```json
{
  "organic_results": [
    {
      "position": 1,
      "title": "...",
      "link": "...",
      "snippet": "...",
      "displayed_link": "...",
      "rich_snippet": {...}
    }
  ],
  "related_searches": [...],
  "knowledge_graph": {...},
  "answer_box": {...}
}
```

## When to use

- Нужен **реальный Google** ranking — для SEO research, competitive intel
- Поиск в специфичных regional Google (google.de, google.fr)
- Scrape Google features (knowledge graph, answer box, related searches)
- Multi-engine (Bing/DuckDuckGo) одним API

## When not to use

- General research — Tavily/Brave дешевле
- Когда не нужны именно Google-specific results

## Auth setup

1. https://serpapi.com → sign up
2. Free 100 searches/month
3. В env: `export SERPAPI_KEY="..."`

## Query patterns

### Google search

```
GET https://serpapi.com/search.json?q={query}&engine=google&num=20&api_key={SERPAPI_KEY}
```

### Google with location

```
GET https://serpapi.com/search.json?q={query}&engine=google&location=Russia&hl=ru&gl=ru&api_key={SERPAPI_KEY}
```

### Bing

```
GET https://serpapi.com/search.json?q={query}&engine=bing&api_key={SERPAPI_KEY}
```

### Google Scholar

```
GET https://serpapi.com/search.json?q={query}&engine=google_scholar&api_key={SERPAPI_KEY}
```

### Google News

```
GET https://serpapi.com/search.json?q={query}&engine=google_news&api_key={SERPAPI_KEY}
```

### Google Trends

```
GET https://serpapi.com/search.json?q={query}&engine=google_trends&data_type=TIMESERIES&api_key={SERPAPI_KEY}
```

## Example queries для deepdive

**Phase 4 — localized search (e.g. German):**

```
GET /search.json?q=Datenresidenz+DSGVO+2026&engine=google&gl=de&hl=de
```

**Phase 4 — Scholar:**

```
GET /search.json?q=vector+database+benchmarking&engine=google_scholar&num=20
```

**Phase 4 — News trend over time:**

```
GET /search.json?q=postgres+18&engine=google_news&tbs=qdr:m
```

## Engines available

Major ones: `google`, `google_scholar`, `google_news`, `google_images`, `google_videos`, `google_maps`, `google_trends`, `bing`, `bing_news`, `duckduckgo`, `yandex`, `baidu`, `naver`, `yahoo`, `youtube`, `walmart`, `ebay`, `amazon`, `home_depot`, `apple_app_store`, `google_play`.

## Limitations

- $50/mo plan = ~$0.01 per search — для deepdive с 100+ queries дорого
- Free tier 100/mo съедается быстро
- Не parsing custom — структура задана SerpAPI

## Combine with

- **Tavily** — для answers с sources
- **Brave Search** — независимый альтернативный index
- **Exa.ai** — для semantic search

## Fallback if API down or rate-limited

1. Brave Search (paid alternative)
2. Tavily (свой free tier)
3. Standard WebSearch в Claude Code
4. DuckDuckGo HTML scraping (не recommended но рабочий)
