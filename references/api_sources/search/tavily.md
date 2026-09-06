# Tavily API

## Overview

- **Endpoint base:** `https://api.tavily.com`
- **Auth:** API key (header `api_key` or body field)
- **Free tier:** 1000 requests / month
- **Rate limit:** flexible на free plan
- **Docs:** https://docs.tavily.com
- **Status page:** https://status.tavily.com

## What it returns

JSON с готовыми **answers + sources**. Tavily — это search API, специально построенный для LLM агентов.

```json
{
  "query": "what is meta research methodology",
  "answer": "Meta-research is the study of research itself...",
  "results": [
    {
      "title": "Meta-research - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Meta-research",
      "content": "Truncated content of the page...",
      "score": 0.95,
      "raw_content": "Full content if include_raw_content=true"
    }
  ]
}
```

## When to use

- Нужен **готовый answer** не только список ссылок
- Search для LLM/agent контекста (Tavily filters out spam, ads)
- Когда WebSearch + ручной WebFetch слишком много шагов

## When not to use

- Нужен максимальный охват — Brave/SerpAPI лучше
- Нужны только URLs без summaries — слишком тяжёлый response

## Auth setup

1. Регистрация: https://tavily.com
2. API key из dashboard
3. В env: `export TAVILY_API_KEY="tvly-..."`

## Query patterns

Прямой вызов из скилла: `python3 scripts/search_query.py --engine tavily --query "..." [--n 10] [--json]`
(читает `TAVILY_API_KEY` из env, exit 2 если ключа нет). Ниже — сырой HTTP-контракт,
который скрипт реализует (basic search, без `include_answer`/`include_domains`).

### Basic search

```
POST https://api.tavily.com/search
Content-Type: application/json

{
  "api_key": "{TAVILY_API_KEY}",
  "query": "{your query}",
  "search_depth": "basic",
  "max_results": 5
}
```

### Advanced search (deeper, slower)

```
POST https://api.tavily.com/search
{
  "api_key": "{TAVILY_API_KEY}",
  "query": "{your query}",
  "search_depth": "advanced",
  "include_answer": true,
  "include_raw_content": true,
  "max_results": 10,
  "include_domains": ["arxiv.org", "scholar.google.com"],
  "exclude_domains": ["pinterest.com"]
}
```

### Get content from specific URL

```
POST https://api.tavily.com/extract
{
  "api_key": "{TAVILY_API_KEY}",
  "urls": ["https://example.com/article"]
}
```

## Example queries для deepdive

**Phase 4 — academic search:**

```
POST /search
{
  "query": "postgres logical replication performance trade-offs",
  "search_depth": "advanced",
  "include_answer": true,
  "include_domains": ["arxiv.org", "ssrn.com", "researchgate.net"],
  "max_results": 8
}
```

**Phase 4 — opposition search:**

```
POST /search
{
  "query": "kubernetes migration regrets postmortem",
  "search_depth": "advanced",
  "include_answer": false,
  "include_domains": ["reddit.com", "twitter.com", "medium.com"]
}
```

## Limitations

- Free tier 1000 req/month — для deep ресёрчей с 5 sub-agents может выйти за месяц если активно используешь
- `include_raw_content` берёт больше токенов в response
- Качество answer зависит от темы — на технических темах слабее чем на mainstream

## Combine with

- **Brave Search** — если нужно больше охвата
- **Exa.ai** — для семантического поиска по похожим документам
- **SerpAPI** — если нужны конкретно Google results

## Fallback if API down or rate-limited

1. Brave Search API (paid alternative)
2. Exa.ai (semantic alternative, free tier)
3. Standard WebSearch through Claude Code WebSearch tool
4. Manual WebFetch на конкретные доменные источники

## Notes

- Tavily — favorite среди AI агентов из-за `include_answer` field, который возвращает synthesized answer наряду с sources
- Хорошо работает с `include_domains` фильтрами для targeted search
- В отличие от Google Search API, Tavily не требует Custom Search Engine setup
