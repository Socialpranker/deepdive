# OpenAlex API

## Overview

- **Endpoint base:** `https://api.openalex.org`
- **Auth:** Ключ не обязателен для базовых запросов — live-проверено 2026-08-17: `GET /works?per-page=1` без ключа → HTTP 200. С начала 2026 официально появился опциональный бесплатный API-ключ (даёт 10× бюджет + приоритет), без ключа — более узкий "keyless"-бюджет
- **Free tier:** НЕ unlimited — с 2026 введена credit-based система. Без ключа: live-заголовки 2026-08-17 показали `x-ratelimit-limit: 1000` кредитов с суточным сбросом (~полночь UTC), список-запрос стоит 1 кредит по наблюдению (точная цифра нигде официально не задокументирована — это прямое наблюдение, не заявленный лимит). С бесплатным ключом: официально "$1 API-бюджета в день" на аккаунт, карта не нужна (help.openalex.org/hc/en-us/articles/24397762024087-Pricing, страница обновлена 2026-08-11)
- **Rate limit:** 100 req/sec — жёсткий потолок для всех тарифов, задокументировано официально (help.openalex.org/api/authentication). Старая цифра "10 req/sec, 100k/day" не подтвердилась ни в доке, ни в live-заголовках
- **Docs:** https://docs.openalex.org (редиректит на https://help.openalex.org)
- **Coverage:** 250M+ scholarly works (replaced Microsoft Academic) — live-запрос 2026-08-17 вернул `"count": 324389590` в `meta`
- **Verified:** 2026-08-17

## What it returns

JSON с metadata + citations graph + author networks + institutional affiliations.

```json
{
  "id": "https://openalex.org/W...",
  "doi": "https://doi.org/10.1234/...",
  "title": "...",
  "authorships": [{"author": {...}, "institutions": [...]}],
  "publication_year": 2024,
  "cited_by_count": 142,
  "referenced_works": ["W...", "W..."],
  "concepts": [{"display_name": "...", "level": 2, "score": 0.85}],
  "open_access": {"is_oa": true, "oa_url": "..."}
}
```

## When to use

- Citation graph analysis на массовом scale (10k+ papers)
- Найти institutional collaborations (университеты, страны)
- Concept-based discovery (OpenAlex добавляет concept tags ML-derived)
- Research metrics — find most-cited in field

## When not to use

- Простой paper lookup — Semantic Scholar чище API
- Нужны abstracts — OpenAlex имеет inverted_index abstracts (нужна реконструкция)

## Auth setup

Ключ не обязателен для базовых/некоммерческих запросов (live-подтверждено 2026-08-17), но с 2026 официально рекомендован — 10× дневной бюджет вместо узкого keyless-лимита:

1. https://openalex.org/settings/api → создать аккаунт (~30 сек), скопировать ключ
2. `export OPENALEX_API_KEY="..."`
3. Точный формат передачи ключа (query-параметр vs заголовок) в этой сессии live не перепроверялся — тестового ключа нет, см. текущую доку на help.openalex.org

Без ключа работает politeness pool:

```
GET /works?search={query}&mailto=your@email.com
```

Это по-прежнему даёт priority доступ внутри keyless-бюджета, но не заменяет ключ по объёму.

## Query patterns

### Search works

```
GET /works?search={query}&per-page=50
```

### Filter by year, OA, type

```
GET /works?search={query}&filter=publication_year:2020-2026,is_oa:true,type:journal-article&per-page=50
```

### Get work by DOI

```
GET /works/doi:10.1234/example
```

### Citation network

```
GET /works/{work-id}?select=referenced_works,cited_by_count
```

### Author papers + h-index

```
GET /authors/{author-id}?select=works_count,cited_by_count,summary_stats
GET /works?filter=author.id:{author-id}&per-page=200
```

### Institution analysis

```
GET /works?filter=institutions.id:{institution-id}&group_by=publication_year
```

### Concept hierarchy

```
GET /concepts/{concept-id}
GET /works?filter=concepts.id:{concept-id}&per-page=200
```

## Example queries для deep-research

**Phase 4 — get all recent papers in a niche concept:**

```
GET /works?filter=concepts.display_name.search:vertical+farming,publication_year:2022-2026,is_oa:true&per-page=100&mailto=research@example.com
```

**Phase 4 — citation graph of seminal work:**

```
GET /works/W{id}?select=referenced_works
# Then for each referenced work:
GET /works/W{ref_id}?select=title,authors,publication_year
```

## Cursor pagination

For large result sets:

```
GET /works?search={query}&per-page=200&cursor=*
# Response includes next_cursor
GET /works?search={query}&per-page=200&cursor={next_cursor}
```

## Abstracts (inverted_index format)

OpenAlex stores abstracts as inverted index (token positions). Reconstruct:

```python
# pseudo-code
abstract_words = {}
for word, positions in inverted_index.items():
    for pos in positions:
        abstract_words[pos] = word
abstract = " ".join(abstract_words[i] for i in sorted(abstract_words))
```

Или используй `mailto=` parameter — некоторые ответы include reconstructed abstract.

## Limitations

- Abstract inverted_index format awkward для агента
- ML-derived concepts иногда noisy
- Smaller community than Semantic Scholar (меньше maintenance attention)
- Free tier больше не unlimited (с 2026) — при интенсивном использовании без ключа можно упереться в суточный keyless-лимит (точная цифра не задокументирована официально, live-наблюдение 2026-08-17 — см. Overview); для серьёзного объёма нужен бесплатный ключ

## Combine with

- **Semantic Scholar** — cleaner API, similar coverage
- **CrossRef** — для DOI lookup
- **OurResearch Unpaywall** — для extra OA URLs

## Fallback if API down or rate-limited

1. Semantic Scholar API (similar coverage)
2. CrossRef для DOI metadata
3. Direct DOI lookup через doi.org redirects

## Notes

- OpenAlex — самый полный citation graph в open data
- Великолепно для research network analysis
- Без ключа доступен базовый объём (live-наблюдение 2026-08-17: порядка 1000 кредитов/сутки); для существенного объёма — бесплатный ключ с $1/день бюджета, карта не нужна
- Уникален возможностью filter по institutions / countries / concepts на массовом scale
