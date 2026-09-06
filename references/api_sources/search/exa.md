# Exa.ai API (formerly Metaphor)

## Overview

- **Endpoint base:** `https://api.exa.ai`
- **Auth:** API key (header `x-api-key`)
- **Free tier:** $10 credit на регистрацию, ~1000 searches
- **Paid:** $5/1000 searches typically
- **Docs:** https://docs.exa.ai
- **Unique:** **semantic search** (neural), не keyword matching

## What it returns

JSON с результатами ranked by semantic similarity to query.

```json
{
  "results": [
    {
      "title": "...",
      "url": "...",
      "publishedDate": "2024-03-15",
      "author": "...",
      "score": 0.89,
      "id": "exa-id-...",
      "text": "Optional full content if requested"
    }
  ]
}
```

## When to use

- Семантический поиск — «similar to this article»
- Concept-based queries вместо keyword
- Когда не знаешь точные термины но знаешь идею
- Поиск «like this URL but newer» / «better version of X»

## When not to use

- Точные lookup queries — keyword search быстрее
- Реал-тайм news (Exa имеет lag)
- Нужны structured data вроде Wikipedia infobox

## Auth setup

1. https://exa.ai → sign up
2. API key из dashboard
3. В env: `export EXA_API_KEY="..."`

## Query patterns

### Neural search

```
POST https://api.exa.ai/search
Headers: x-api-key: {EXA_API_KEY}
Content-Type: application/json

{
  "query": "research methodology for market microstructure",
  "type": "neural",
  "useAutoprompt": true,
  "numResults": 10
}
```

`useAutoprompt: true` — Exa reformulates query under the hood для лучших результатов.

### Find similar

```
POST https://api.exa.ai/findSimilar
{
  "url": "https://example.com/research/paper",
  "numResults": 10
}
```

### Get content of result

```
POST https://api.exa.ai/contents
{
  "ids": ["exa-id-1", "exa-id-2"],
  "text": true,
  "highlights": true
}
```

## Example queries для deepdive

**Phase 4 — find similar to a paper:**

```
POST /findSimilar
{
  "url": "https://arxiv.org/abs/2401.12345",
  "numResults": 15
}
```

**Phase 4 — concept search:**

```
POST /search
{
  "query": "papers explaining how market makers profit from spread in prediction markets",
  "type": "neural",
  "useAutoprompt": true,
  "category": "research paper",
  "numResults": 10
}
```

## Categories filter

Exa умеет фильтровать по типу контента:
- `research paper`
- `news`
- `tweet`
- `pdf`
- `github`
- `personal site`
- `linkedin profile`

## Limitations

- Не replacement для keyword search — для точных queries (specific names, IDs) hurt
- Index меньше чем у Google
- Cost при активном использовании быстро растёт

## Combine with

- **Tavily** — для answers с sources
- **Brave Search** — для broader coverage
- **Semantic Scholar** — для академического но без semantic ranking

## Fallback if API down or rate-limited

1. Tavily с `search_depth: advanced`
2. Brave Search с include_domains фильтром
3. Standard WebSearch через Claude Code
