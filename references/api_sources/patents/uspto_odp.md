# USPTO Open Data Portal (ODP)

## Overview

- **Endpoint base:** `https://api.uspto.gov/api/v1/`
- **Auth:** API key (`X-API-KEY` header) — требует зарегистрированный USPTO.gov аккаунт с привязанным и верифицированным ID.me аккаунтом (identity verification, не просто email-регистрация)
- **Free tier:** бесплатно, но с недельными квотами (см. Rate limit) и заметным onboarding-порогом из-за ID.me
- **Rate limit:** burst = 1 (без параллельных запросов на один ключ), rate 4–15 req/sec в зависимости от типа вызова; отдельно — недельные квоты: 5,000,000 calls/week на все metadata-retrieval API суммарно, 1,200,000 calls/week на Patent File Wrapper Documents API, 20 downloads/год на файл через Bulk Datasets Downloads API (кроме XML — там лимит выше), не более 5 файлов за 10 сек с одного IP. Квота сбрасывается в воскресенье в полночь UTC
- **Docs:** https://data.uspto.gov/apis/getting-started , https://data.uspto.gov/apis/api-rate-limits , https://data.uspto.gov/apis/api-syntax-examples
- **Status page:** не найдена отдельная status-страница; см. https://data.uspto.gov/support (FAQ/support)
- **Verified:** 2026-08-17

⚠️ Внешняя разведка перед этим ресёрчем предполагала лимит «45 req/min» — это не подтвердилось. Реальная модель лимитов другая: burst=1 + per-endpoint rate 4–15 req/sec + отдельные недельные квоты на три категории API (см. выше). Не используй цифру 45 req/min.

Live-проверка 2026-08-17: `curl https://api.uspto.gov/api/v1/patent/applications/search?q=Utility` без ключа → `HTTP 401` (endpoint живой, требует auth).

## What it returns

JSON. Патентные заявки и данные Patent File Wrapper — метаданные заявки, continuity data, transactions, patent term adjustment, foreign priority, assignments, документы (PDF/XML/DOC), а также Bulk Datasets, PTAB Trials/Appeals/Interferences, Office Action тексты и citations.

```json
{
  "patentFileWrapperDataBag": [
    {
      "applicationNumberText": "16123456",
      "applicationMetaData": {
        "inventionTitle": "Example Title",
        "filingDate": "2021-05-01",
        "applicationTypeLabelName": "Utility",
        "applicationStatusDescriptionText": "Patented Case"
      }
    }
  ]
}
```

## When to use

- Поиск и метаданные патентных заявок США (включая pre-grant publications) по заголовку, дате подачи, статусу, заявителю
- Continuity data — связи между родительскими/дочерними заявками
- Office Action тексты и citations (основания отказа, цитируемый prior art)
- PTAB proceedings (trials, appeals, interferences)
- Bulk-скачивание документов Patent File Wrapper (PDF/XML/Word)

## When not to use

- Быстрый разовый lookup без готовности проходить регистрацию USPTO.gov + ID.me verification (процесс минимум на несколько минут, для non-US пользователей — видеозвонок с ID.me)
- Полнотекстовый поиск по выданным патентам с текстом claims/description как основная задача — для этого больше подходит Google Patents / Espacenet (см. Combine with), ODP фокусируется на file wrapper и метаданных
- Когда не готов частично раскрыть личность через ID.me — для организации это может быть блокером

## Auth setup

1. Завести USPTO.gov аккаунт: https://account.uspto.gov (email + подтверждение по коду, код истекает за 48 часов)
2. Завести ID.me аккаунт и пройти identity verification (self-service или live video call; для пользователей вне США — обязательно video call + документы на английском)
3. Связать USPTO.gov и ID.me аккаунты через "Manage API Key" в ODP, получить API key
4. В env: `export USPTO_ODP_API_KEY="..."`
5. Ключ не истекает, если используется минимум раз в год; при неиспользовании 90 дней — удаляется автоматически

Запрос: `-H 'X-API-KEY: <USPTO_ODP_API_KEY>'`

## Query patterns

### Simplified search (GET, query string)

```
GET /api/v1/patent/applications/search?q=Utility
GET /api/v1/patent/applications/search?q=applicationMetaData.inventionTitle:Apple*%20AND%20applicationMetaData.filingDate:[2021-01-01%20TO%202022-12-01]&offset=0&limit=25
```

### Advanced search (POST, JSON body, powered by OpenSearch)

```
POST /api/v1/patent/applications/search
{
  "q": "Nanobody",
  "filters": [
    {"name": "applicationMetaData.applicationTypeLabelName", "value": ["Utility"]}
  ],
  "rangeFilters": [
    {"field": "applicationMetaData.filingDate", "valueFrom": "2022-01-01", "valueTo": "2023-12-31"}
  ],
  "pagination": {"offset": 0, "limit": 25},
  "sort": [{"field": "applicationMetaData.filingDate", "order": "Desc"}]
}
```

### Documents for a given application

```
GET /api/v1/patent/applications/{applicationNumber}/documents
GET /api/v1/download/applications/{applicationNumber}/{documentId}.pdf
```

## Example queries

Реальный, официально документированный (не проверялся live с ключом — нужен API key):

```
GET https://api.uspto.gov/api/v1/patent/applications/search?q=applicationMetaData.inventionTitle:Apple*%20AND%20applicationMetaData.filingDate:[2021-01-01%20TO%202022-12-01]&offset=0&limit=25
```

Live без ключа подтверждает, что endpoint отвечает (401, не 404/timeout):

```
curl "https://api.uspto.gov/api/v1/patent/applications/search?q=Utility"
→ HTTP 401
```

## Limitations

- Только US-заявки/патенты (USPTO), нет международного покрытия (для этого EPO/WIPO)
- Onboarding тяжёлый: ID.me verification — это не просто «получить ключ», а полноценная проверка личности
- Bulk document downloads жёстко квотированы (20/год на файл) — для больших объёмов используй Bulk Datasets Downloads API отдельно, а не Documents API
- Крупные файлы (>100 МБ) стримятся с задержкой до 60 сек, файлы >250 МБ иногда таймаутятся даже за 10 минут
- API key привязан к одному аккаунту, шарить нельзя, параллельные запросы одним ключом блокируются

## Combine with

- **EPO OPS** (`epo_ops.md`) — для европейских эквивалентов и patent family
- **EPO Linked Open Data** (`epo_lod.md`) — для SPARQL-запросов по связям европейских патентов
- **Google Patents / Espacenet** (через WebFetch) — для полнотекстового поиска claims/description по выданным патентам, если ODP file-wrapper фокус не подходит

## Fallback if API down or rate-limited

1. Подождать `Retry-After`/до сброса недельной квоты (сброс — воскресенье 00:00 UTC)
2. Данные без ключа: https://data.uspto.gov предоставляет прямое скачивание bulk data products без API key (медленнее, без программного поиска)
3. ⚠️ **PatentsView (`search.patentsview.org`) мёртв** — домен не резолвится (DNS failure, проверено 2026-08-17), а не просто 410. PatentsView официально закрылся 20 марта 2026 и мигрировал данные в USPTO ODP bulk datasets. Не пытайся использовать PatentsView как fallback или альтернативу — это тот же ODP, только под старым URL.
4. WebFetch на https://ppubs.uspto.gov/pubwebapp/ (Patent Public Search UI) как последний вариант для ручного поиска
