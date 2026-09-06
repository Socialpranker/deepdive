# CrossRef API

## Overview

- **Endpoint base:** `https://api.crossref.org`
- **Auth:** None (mailto param recommended for politeness pool)
- **Free tier:** Unlimited
- **Rate limit:** ~50 req/sec sustained (politely)
- **Docs:** https://api.crossref.org/swagger-ui/index.html
- **Coverage:** 130M+ DOIs across journals, books, conferences

## What it returns

JSON с метаданными по DOIs — bibliographic data, references, funders, licenses.

```json
{
  "DOI": "10.1234/example",
  "title": ["Paper title"],
  "author": [{"given": "John", "family": "Doe", "ORCID": "..."}],
  "container-title": ["Journal Name"],
  "published-print": {"date-parts": [[2024, 3, 15]]},
  "is-referenced-by-count": 42,
  "reference": [{"DOI": "10.1234/ref1"}, ...],
  "URL": "https://doi.org/10.1234/example"
}
```

## When to use

- **DOI resolution** — single source of truth для DOI → metadata
- Citation validation — проверить что paper реально существует
- Reference parsing — получить references из article
- Funding analysis — найти papers funded by specific grant/agency

## When not to use

- Поиск по теме — Semantic Scholar лучше для search UX
- Полные тексты — CrossRef только metadata
- Abstracts — не всегда доступны через CrossRef

## Auth setup

Не нужен. Politeness:

```
GET /works/{DOI}?mailto=your@email.com
```

## Query patterns

### Get work by DOI

```
GET /works/10.1234/example
```

### Search

```
GET /works?query={query}&rows=20
```

### Filter

```
GET /works?query={query}&filter=from-pub-date:2020,until-pub-date:2024,type:journal-article&rows=20
```

### Get journal info

```
GET /journals/{ISSN}
```

### Funding lookup

```
GET /works?filter=funder:10.13039/100000001&rows=20
# (NSF funder ID)
```

## Example queries для deepdive

**Phase 4 — validate DOI from source:**

```
GET /works/10.1093/pq/pqz044
# Returns metadata, check title matches what source claimed
```

**Phase 4 — get references list:**

```
GET /works/10.1093/pq/pqz044?select=reference
```

**Phase 4 — find papers funded by specific source:**

```
GET /works?filter=funder:10.13039/501100000780&rows=100&select=title,author,published-print,DOI
# ID 501100000780 = EU Commission
```

## Useful filters

- `from-pub-date:2020`
- `until-pub-date:2024`
- `type:journal-article` (or `book-chapter`, `proceedings-article`)
- `has-funder:true`
- `has-references:true`
- `has-orcid:true`
- `from-deposit-date:2024-01-01` (recently added to CrossRef)

## Limitations

- Metadata only — нет full text
- Abstracts inconsistent — depends on publisher
- Coverage слабее в social sciences vs STEM

## Combine with

- **Semantic Scholar** — для abstracts + concepts
- **OpenAlex** — для citation graph
- **Unpaywall** — для open access PDF URLs

## Fallback if API down or rate-limited

1. DOI resolution через doi.org redirect
2. OpenAlex `/works/doi:{doi}`
3. Direct WebFetch DOI URL

## Notes

- CrossRef — standard source of truth для DOIs
- Идеально для validation existing references
- Не покрывает arXiv preprints (нет DOI у preprint без journal publication)
- Используется как backbone для других API (Semantic Scholar, OpenAlex enrich CrossRef data)
