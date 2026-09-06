# Brave Search API

## Overview

- **Endpoint base:** `https://api.search.brave.com/res/v1/`
- **Auth:** API key (header `X-Subscription-Token`)
- **Free tier:** 2000 queries/month, 1 query/sec
- **Paid:** $3-$5 per 1000 queries
- **Docs:** https://api.search.brave.com/app/documentation
- **Independent index** (не Google rebrand)

## What it returns

JSON с organic results, news, videos, infobox.

```json
{
  "web": {
    "results": [
      {
        "title": "...",
        "url": "...",
        "description": "...",
        "age": "2 days ago",
        "language": "en",
        "family_friendly": true
      }
    ]
  },
  "news": {...},
  "infobox": {...}
}
```

## When to use

- Нужен Google-quality search без Google bias
- Privacy-respecting alternative
- Bulk programmatic search

## When not to use

- Бесплатных запросов > 2000/month
- Нужен Google specifically (SerpAPI для этого)

## Auth setup

1. https://api.search.brave.com → sign up
2. Получи API key
3. В env: `export BRAVE_API_KEY="BSA..."`

## Query patterns

### Web search

```
GET https://api.search.brave.com/res/v1/web/search?q={query}&count=20
Headers: X-Subscription-Token: {BRAVE_API_KEY}
```

### News search

```
GET https://api.search.brave.com/res/v1/news/search?q={query}&count=20&freshness=pw
```

`freshness`: `pd` (past day), `pw` (past week), `pm` (past month), `py` (past year)

### Goggle (custom rankings)

Brave Goggles позволяют создать custom ranker:

```
GET https://api.search.brave.com/res/v1/web/search?q={query}&goggles_id={GOGGLE_ID}
```

## Example queries для deepdive

**Phase 4 — landscape research:**

```
GET /web/search?q=eu%20ai%20act%20compliance%20timeline%202026&count=20&freshness=py
```

**Phase 4 — recent news:**

```
GET /news/search?q=duckdb%20release&count=10&freshness=pm
```

## Limitations

- 2000 free queries/month — для deep ресёрчей с активными sub-agents этого мало
- Меньше "rich features" чем Google (no instant answers для всего)
- Index не такой широкий как Google для нишевых тем

## Combine with

- **Tavily** — для готовых answers с sources
- **SerpAPI** — если нужен именно Google
- **Exa** — для семантического поиска

## Fallback if API down or rate-limited

1. Tavily API (свой free tier)
2. Standard WebSearch tool в Claude Code
3. DuckDuckGo through Brave alternative (но менее качественный)
