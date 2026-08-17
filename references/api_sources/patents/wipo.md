# WIPO PATENTSCOPE

## Overview

- **Endpoint base:** нет публичного бесплатного API. PATENTSCOPE — веб-поисковик (`https://patentscope.wipo.int/search/en/search.jsf`) плюс платный SOAP/WSDL web service для программного доступа
- **Auth:** для веб-интерфейса — нет (публичный, но с anti-bot защитой, включая CAPTCHA); для программного SOAP API — платная подписка с выданными credentials
- **Free tier:** **бесплатного программного API нет.** Есть бесплатный веб-поиск (для людей, не для автоматизации) и три платных продукта: SOAP web service (поиск) — 600 CHF/год, SOAP web service (полный, batch download + IASR) — 2000 CHF/год, PCT-Bibliographic bulk feed (SFTP, метаданные) — от 400 CHF/год, PCT-Text bulk (full-text + images) — 3900–19500 CHF/год в зависимости от объёма
- **Rate limit:** для бесплатного веб-интерфейса ToS ограничивает "более 10 search-related actions в минуту с одного IP" как excessive use; автоматизированные запросы, bulk-скачивание, bulk-copying и web scraping явно запрещены условиями использования. Для платного SOAP API числовой rate limit не найден в открытых источниках
- **Docs:** https://www.wipo.int/en/web/patentscope/data/index (PCT Data Products and Services), https://www.wipo.int/en/web/patentscope/data/terms_patentscope (Terms of Use)
- **Status page:** не найдена
- **Verified:** 2026-08-17

Live-проверка 2026-08-17: открытие `patentscope.wipo.int` в браузере сразу отдаёт капчу ("Please select the picture with stars") — заходить и решать капчу запрещено (bot-detection bypass — prohibited action), поэтому веб-интерфейс live не протестирован дальше загрузки страницы. Terms of Use (`.../data/terms_patentscope`) и PCT Data Products страница (`.../data/index`) загружаются нормально и являются официальным источником для цифр выше (проверено live).

## What it returns

Веб-интерфейс: HTML со страницами результатов поиска (заявки PCT + национальные/региональные коллекции, если участвует ведомство). Платный SOAP API: XML по WSDL-схеме — библиографика, статус (IASR — International Application Status Report), full-text и изображения (для full-access тарифа). Bulk SFTP: XML + TIFF-изображения пакетами.

## When to use

- Нужен обзорный поиск по международным (PCT) заявкам вручную, эпизодически, без автоматизации — веб-интерфейс бесплатен для этого
- Организация готова платить 400–19500 CHF/год за структурированный программный доступ к PCT-данным и это оправдано объёмом задач
- Нужен официальный международный статус заявки (IASR) программно — только через платный SOAP API

## When not to use

- **Не пытайся построить агентный/автоматизированный workflow поверх бесплатного PATENTSCOPE** — ToS прямо запрещает automated queries, bulk acquisition, bulk downloading, bulk storing, bulk copying, web scraping и "любое иное abusive use". Это не серая зона: при превышении WIPO явно оставляет за собой право блокировать доступ по IP
- Нет бюджета на платную подписку — тогда WIPO как programmatic source не подходит вообще; используй USPTO ODP + EPO OPS/LOD, которые вместе покрывают большую часть того же самого международного patent landscape бесплатно (EPO family data включает PCT-заявки)
- Нужен быстрый bulk-объём (сотни+ запросов) прямо сейчас — веб-интерфейс отдаёт капчу и режет по threshold 10 действий/мин на IP

## Auth setup

Для платного SOAP API: подписка оформляется напрямую через WIPO (contact/order process, детали — https://www.wipo.int/en/web/patentscope/data/index), выдаются персональные credentials для WSDL-эндпоинта. Единого API-ключа в стиле "получил токен за 5 минут" не существует — это коммерческий контракт, поэтому под него нет смысла заводить env var в стиле `FRED_API_KEY`: если организация оформит подписку, credentials выдаются индивидуально и хранятся так же, как остальные секреты (`WIPO_PATENTSCOPE_CREDENTIALS` — как ориентир имени, если решите завести).

Для бесплатного веб-интерфейса — auth не нужен, но и автоматизация запрещена ToS (см. When not to use).

## Query patterns

Программных query patterns для бесплатного доступа нет — API как такового нет. Единственный легитимный паттерн для агента: единичный ручной WebFetch/просмотр страницы результатов поиска человеком, без цикла запросов.

Для платного SOAP API (по документации, без доступа для live-проверки — нет подписки):

```
SOAP/WSDL вызов на публикационные документы PATENTSCOPE
(IASR retrieval, batch document download — согласно WIPO PCT Patentscope Web-services for Offices)
```

## Example queries

Нет бесплатного programmatic query, который можно было бы честно продемонстрировать как рабочий пример. Единственный проверяемый без CAPTCHA пример — прямая ссылка на карточку заявки (для WebFetch человеком/агентом одноразово, не в цикле):

```
https://patentscope.wipo.int/search/en/detail.jsf?docId={WO_DOCUMENT_ID}
```
(URL-паттерн подтверждён публичной документацией WIPO; сам live fetch не пройден из-за bot-detection на входной странице поиска — см. Overview)

## Limitations

- Нет бесплатного программного доступа — это единственный из четырёх патентных источников в каталоге, где нет free tier для API вообще
- Веб-интерфейс активно защищён от automated access (CAPTCHA уже на входной странице поиска)
- OCR-based full text (claims/description) — WIPO сам предупреждает в ToS, что OCR подвержен ошибкам
- Платный SOAP/WSDL — устаревший протокол, нет современного REST/JSON эквивалента по состоянию на 2026-08-17; WIPO не анонсировал дату миграции на REST

## Combine with

- **EPO OPS** (`epo_ops.md`) и **EPO Linked Open Data** (`epo_lod.md`) — EPO покрывает PCT-заявки как часть patent family бесплатно, это основная бесплатная альтернатива WIPO для международных данных
- **USPTO ODP** (`uspto_odp.md`) — для US national phase той же PCT-заявки

## Fallback if API down or rate-limited

Since there is no free API, "down or rate-limited" применимо только к веб-интерфейсу:

1. При капче/блокировке — не пытаться обходить (bypass CAPTCHA запрещён); подождать и повторить как единичный ручной запрос позже
2. EPO OPS/LOD (`epo_ops.md`, `epo_lod.md`) — покрывают PCT-заявки как international phase внутри EPO family data, без CAPTCHA и без платной подписки
3. Google Patents (через WebFetch) — часто индексирует те же PCT-публикации (WO-номера) без anti-bot защиты уровня PATENTSCOPE
