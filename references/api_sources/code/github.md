# GitHub Search API

## Overview

- **Endpoint base:** `https://api.github.com`
- **Auth:** Personal access token (Bearer)
- **Free tier:** 60 req/h unauthenticated, **5000 req/h** with token
- **Rate limit:** 30 search req/min с auth
- **Docs:** https://docs.github.com/en/rest
- **Coverage:** Все public GitHub repos, issues, code, users

## Auth setup

1. https://github.com/settings/tokens → Generate new token
2. Scope: public_repo (read-only достаточно)
3. `export GITHUB_TOKEN="ghp_..."`

## Query patterns

### Search repositories

```
GET /search/repositories?q={query}+language:python+stars:>1000
Headers: Authorization: Bearer {GITHUB_TOKEN}
```

### Search code

```
GET /search/code?q={query}+in:file+language:typescript
```

### Search issues

```
GET /search/issues?q={query}+type:issue+is:open+label:bug
```

### Repo content

```
GET /repos/{owner}/{repo}/readme
GET /repos/{owner}/{repo}/contents/{path}
```

### Get file

```
GET /repos/{owner}/{repo}/contents/{path}?ref={branch}
```

### Trending (via 3rd party — no official trending API)

Используй GitHub Trending pages через WebFetch + scraping.

## Example queries для deepdive

**Phase 4 — find implementations:**

```
GET /search/repositories?q=vector+database+language:rust+stars:>100&sort=stars
```

**Phase 4 — find discussions/issues:**

```
GET /search/issues?q=postgres+logical+replication+is:issue
```

**Phase 4 — read implementation source:**

```
GET /repos/duckdb/duckdb/contents/README.md
```

## Useful qualifiers

- `language:python`
- `stars:>1000`
- `forks:>50`
- `created:>2023-01-01`
- `topic:llm` (если у repo есть topic)
- `in:name` / `in:description` / `in:readme`
- `pushed:>2024-01-01` (recently active)

## Limitations

- 30 search req/min — для bulk research можно упереться
- Code search has stricter limits и фильтрация
- Не indexes private repos (нужны соответствующие токены)

## Combine with

- **Stack Exchange** — для programming Q&A
- **PyPI/npm** — для package metadata
- **GitHub Trending** scraping для discovery

## Fallback

- Direct HTML scraping github.com search
- GitHub Code Search UI: https://github.com/search
