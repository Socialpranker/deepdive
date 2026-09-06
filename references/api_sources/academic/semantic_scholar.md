# Semantic Scholar API

## Overview

- **Endpoint base:** `https://api.semanticscholar.org/graph/v1`
- **Auth:** None required (optional API key для higher rate limits)
- **Free tier:** Unlimited, rate-limited to ~100 req/min unauthenticated
- **With key:** Higher limits (request at https://www.semanticscholar.org/product/api)
- **Docs:** https://api.semanticscholar.org
- **Coverage:** 200M+ papers across all academic disciplines

## What it returns

JSON с paper metadata, abstracts, citations, references, fields of study, embeddings.

```json
{
  "paperId": "...",
  "title": "...",
  "abstract": "...",
  "authors": [{"name": "...", "authorId": "..."}],
  "year": 2024,
  "venue": "...",
  "citationCount": 142,
  "referenceCount": 56,
  "fieldsOfStudy": ["Computer Science", "Economics"],
  "openAccessPdf": {"url": "https://..."}
}
```

## When to use

- **Academic search** — primary tool for scholarly research
- Citation graph — найти что цитировало paper X
- Reference list — найти что paper X цитирует
- Field-of-study filter — найти papers только в economics, ML, etc.

## When not to use

- Не-академические темы (новости, blogs, products)
- Нужны только preprints без peer-review (используй arXiv напрямую)

## Auth setup

Без ключа работает. Если нужны высокие rate limits:

1. https://www.semanticscholar.org/product/api → request key
2. В env: `export SEMANTIC_SCHOLAR_API_KEY="..."`
3. Header: `x-api-key: {key}`

## Query patterns

### Search papers

```
GET /paper/search?query={query}&limit=20&fields=title,abstract,authors,year,citationCount,openAccessPdf
```

### Paper details by ID

```
GET /paper/{paperId}?fields=title,abstract,authors,citations,references
```

### Get citations of paper

```
GET /paper/{paperId}/citations?fields=title,authors,year,abstract
```

### Get references of paper

```
GET /paper/{paperId}/references?fields=title,authors,year
```

### Author lookup

```
GET /author/search?query={name}&fields=name,affiliations,papers
```

### Batch lookup (up to 500 IDs)

```
POST /paper/batch
{
  "ids": ["paperId1", "paperId2", ...],
  "fields": "title,abstract,authors"
}
```

## Example queries для deepdive

**Phase 4 — literature scan:**

```
GET /paper/search?query=prediction+markets+market+microstructure&limit=30&fieldsOfStudy=Economics,Computer+Science&fields=title,abstract,year,citationCount,openAccessPdf&year=2020-2026
```

**Phase 4 — find citing papers (validation):**

```
GET /paper/{seminal-paper-id}/citations?limit=50&fields=title,abstract,year,citationCount
```

**Phase 4 — find references (build context):**

```
GET /paper/{recent-paper-id}/references?limit=100&fields=title,authors,year
```

## Limitations

- Coverage слабее в social sciences и humanities чем в CS/biology
- Abstract не всегда доступен для старых papers
- `openAccessPdf` не всегда есть (paywalled)

## Combine with

- **OpenAlex** — для citation network analysis (более полный граф)
- **arXiv** — для recent CS/physics preprints без paywall
- **CrossRef** — для DOI lookup
- **PubMed** — для биомедицины

## Fallback if API down or rate-limited

1. OpenAlex (similar coverage, free, no key)
2. CrossRef для DOI metadata
3. Google Scholar через SerpAPI
4. Direct arXiv API для CS/math/physics

## Notes

- Самый удобный академический API — структурированный, free, no key
- Поле `openAccessPdf` критично — даёт ссылки на free full-text копии (часто preprint versions paywalled статей)
- Idiomatic для deepdive workflow
