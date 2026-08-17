# Реестр источников — Реестры

Корпоративные, сетевые, тендерные и некоммерческие реестры — вход для вопроса «кто это и чем владеет». Патентных ведомств здесь нет: в разведке их не оказалось, дыра закрывается вручную через api_sources/.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 12, из них 1 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| OECD SDMX Data API — Patents Indicators | <https://sdmx.oecd.org/public/rest/data/OECD.ENV.EPI,DSD_PAT_IND@DF_PAT_IND,1.0/all?format=jsondata> | ip-activity-signal | free | high |
| AFRINIC RDAP — Regional Internet Registry (Африка) | <https://rdap.afrinic.net/rdap/ip/196.216.2.0/24> | market-registry-signal | free | high |
| Artemis.bm Catastrophe Bond & ILS News RSS | <https://www.artemis.bm/feed/> | market-registry-signal | free | high |
| Candid (GuideStar) — Essentials API v4 (nonprofit profile/financial/taxonomy data) | <https://developer.candid.org/reference/essentials_v4> | market-registry-signal | нужен ключ | high |
| EU VIES — VAT Information Exchange System (REST/SOAP validation API) | <https://ec.europa.eu/taxation_customs/vies/rest-api/ms/DE/vat/811569869> | market-registry-signal | free | high |
| IRS Exempt Organizations Business Master File (EO BMF) — bulk CSV per state | <https://www.irs.gov/pub/irs-soi/eo_dc.csv> | market-registry-signal | free | high |
| International Franchise Association — Franchise Directory (WP REST API) | <https://www.franchise.org/wp-json/wp/v2/franchise?per_page=3> | market-registry-signal | free | high |
| Open Banking Tracker — API Aggregators Registry (PSD2/Open Banking TPP Directory) | <https://api.github.com/repos/not-a-bank/open-banking-tracker-data/contents/data/api-aggregators> | market-registry-signal | free | high |
| PeeringDB API — Network Operator / Internet Exchange Registry | <https://www.peeringdb.com/api/net?limit=2> | market-registry-signal | free | high |
| Prozorro / OpenProcurement — Live Public Tenders API | <https://public.api.openprocurement.org/api/2.5/tenders?descending=1&limit=3> | market-registry-signal | free | high |
| RIPE NCC Stat API — Regional Internet Registry (Европа/Ближний Восток/Центральная Азия) | <https://stat.ripe.net/data/network-info/data.json?resource=8.8.8.8> | market-registry-signal | free | high |
| UNESCO Institute for Statistics (UIS) Data API — Education Indicators | <https://api.uis.unesco.org/api/public/data/indicators?indicator=CR.1&geoUnit=USA> | market-registry-signal | free | high |
