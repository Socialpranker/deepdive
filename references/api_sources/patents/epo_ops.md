# EPO Open Patent Services (OPS)

## Overview

- **Endpoint base:** `https://ops.epo.org/3.2/rest-services/`
- **Auth:** OAuth 2.0 (`client_credentials` grant) — нужны Consumer Key + Consumer Secret с бесплатной регистрации на developers.epo.org
- **Free tier:** до 4 GB трафика в неделю бесплатно ("free threshold"); неделя = календарная, пн 00:00 – вс 24:00 GMT. Свыше — платная годовая подписка (точные цены — в брошюре "EPO Patent Information - Price list", на самой fair-use странице цена не указана)
- **Rate limit:** максимальная скорость трафика ≈ 1 Мбит/сек как для OPS, так и для European Publication Server REST API. Официально задокументирован только этот троттлинг по скорости и недельная квота по объёму (4 GB); более гранулярные цифры вида "N req/min" в официальной документации EPO не найдены — сторонние клиентские библиотеки (python-epo-ops-client, Go epo-ops) упоминают отдельно per-hour throttling с скользящим окном в 1 минуту, но точное число req/hour **не подтверждено на 2026-08-17**
- **Docs:** https://www.epo.org/en/searching-for-patents/data/web-services/ops , https://developers.epo.org/
- **Status page:** https://www.epo.org/en/service-support/status-online-services (Availability of online services, упоминается в fair-use charter как источник инфо о плановых работах OPS)
- **Verified:** 2026-08-17

Live-проверка 2026-08-17:
```
curl -X POST https://ops.epo.org/3.2/auth/accesstoken -d "grant_type=client_credentials"
→ HTTP 401 {"message":"Client identifier is required"}

curl https://ops.epo.org/3.2/rest-services/published-data/search?q=ti=plastic
→ HTTP 403 {"code":403,"message":"This request has been rejected due to the violation of Fair Use policy","moreInfo":"https://www.epo.org/service-support/ordering/fair-use.html"}
```
Оба endpoint'а живые и отвечают ожидаемо (auth и rest-services без токена не проходят).

Официальный текст fair-use policy (epo.org/service-support/ordering/fair-use.html, проверено live 2026-08-17): *«Downloading data via OPS is free of charge up to a maximum data volume of 4 GB per week ("free threshold")»*, а также *«the maximum traffic volume allowed is approximately 1 Mbit per second»*.

## What it returns

Стандартизированный XML-интерфейс (RESTful) поверх тех же баз, что Espacenet и European Patent Register: библиографика, worldwide legal status, full-text, изображения. JSON доступен через `Accept: application/json` (подтверждено сторонними клиентскими библиотеками OPS v3.2, официальную страницу со спецификацией Accept-заголовков получить не удалось — страницы EPO с этим уровнем детализации не отдают статический HTML для WebFetch).

## When to use

- Патентные данные по 100M+ документам из EPO баз, включая worldwide legal status
- Patent family — связи между патентами разных юрисдикций по одному изобретению
- Bibliographic + full-text + images одним API, без необходимости комбинировать несколько источников
- Интеграция EPO-данных в собственное приложение/базу данных

## When not to use

- Разовый ручной поиск одного патента — проще WebFetch на Espacenet UI (`worldwide.espacenet.com`), не требует OAuth setup
- Приложения с непредсказуемо большим объёмом трафика без готовности платить за подписку сверх 4 GB/неделю
- Нужен готовый JSON без парсинга XML как основной сценарий — OPS исторически XML-first, JSON поддержан, но менее задокументирован

## Auth setup

1. Регистрация на https://developers.epo.org/user/register (бесплатно, ~5 минут)
2. Войти, создать test app в Developer's Console → получить Consumer Key и Consumer Secret
3. В env:
   ```
   export EPO_OPS_CONSUMER_KEY="..."
   export EPO_OPS_CONSUMER_SECRET="..."
   ```
4. Получить access token (OAuth2 client_credentials, Basic Auth заголовок с key:secret в base64):
   ```
   POST https://ops.epo.org/3.2/auth/accesstoken
   Authorization: Basic base64(EPO_OPS_CONSUMER_KEY:EPO_OPS_CONSUMER_SECRET)
   Content-Type: application/x-www-form-urlencoded
   Body: grant_type=client_credentials
   ```
   Возвращает `access_token`, использовать как `Authorization: Bearer <token>` в последующих запросах.

## Query patterns

### Published data search

```
GET /3.2/rest-services/published-data/search?q={CQL query}
```

### Bibliographic data by publication number

```
GET /3.2/rest-services/published-data/publication/epodoc/{number}/biblio
```

### Full-text (description/claims)

```
GET /3.2/rest-services/published-data/publication/epodoc/{number}/fulltext
```

### Patent family

```
GET /3.2/rest-services/family/publication/epodoc/{number}
```

### Legal status

```
GET /3.2/rest-services/legal/publication/epodoc/{number}
```

## Example queries

CQL search по названию (структура запроса подтверждена документацией OPS; для получения ответа нужен OAuth токен — недоступен без регистрации, поэтому итоговый response не воспроизведён живьём):

```
GET https://ops.epo.org/3.2/rest-services/published-data/search?q=ti=plastic
Authorization: Bearer {access_token}
```

Live-проверка без токена (подтверждает, что endpoint существует и требует auth, см. Overview):
```
curl https://ops.epo.org/3.2/rest-services/published-data/search?q=ti=plastic
→ HTTP 403 (Fair Use policy — на деле это стандартный ответ на запрос без валидного токена)
```

## Limitations

- XML-first дизайн, JSON — вторичный формат
- OAuth токен нужно обновлять (стандартный client_credentials, срок жизни токена не проверялся отдельно — обычно ограничен по времени, как во всех OAuth2 client_credentials реализациях)
- 4 GB/неделю может быть тесно для bulk-сценариев — тогда нужен платный тариф или прямой контакт patentdata@epo.org для больших объёмов
- Официальная документация EPO плохо отдаётся статическим HTML-парсерам (много контента подгружается динамически) — точные числовые пороги троттлинга по req/min не удалось перепроверить напрямую, только через fair-use charter (GB/неделю + Мбит/сек) и через независимые клиентские библиотеки

## Combine with

- **EPO Linked Open Data** (`epo_lod.md`) — SPARQL по тем же данным, без OAuth, для более лёгких/структурных запросов
- **USPTO ODP** (`uspto_odp.md`) — для US-заявок и file wrapper
- **Google Patents** (через WebFetch) — быстрый ручной кросс-чек без квот

## Fallback if API down or rate-limited

1. При 403 Fair Use policy — подождать до сброса недельного окна (понедельник 00:00 GMT) либо снизить объём трафика
2. EPO Linked Open Data (`epo_lod.md`) — SPARQL endpoint без OAuth и без объявленной недельной квоты, покрывает подмножество тех же библиографических данных
3. WebFetch на Espacenet (`worldwide.espacenet.com`) для ручного поиска отдельных патентов без квот вообще
