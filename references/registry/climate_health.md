# Реестр источников — Климат, ESG и здравоохранение

Раскрытия ESG, климатические реконструкции, дефицит лекарств, ЧС и гуманитарные кризисы.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 25, из них 3 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| FEMA OpenFEMA API — Housing Assistance Owners (Individual Assistance operational data) | <https://www.fema.gov/api/open/v2/HousingAssistanceOwners> | disaster-response-operations-signal | free | high |
| IFRC GO Platform — Emergency Response Units (ERU) Deployment & Readiness API | <https://goadmin.ifrc.org/api/v2/deployed_eru_by_event/> | disaster-response-operations-signal | free | high |
| openFDA — Drug Shortages API | <https://api.fda.gov/drug/shortages.json?limit=5> | drug-shortage-signal | free | high |
| ADEME (Agence de la transition écologique, Франция) — RSS | <https://www.ademe.fr/feed/> | esg-disclosure-signal | free | high |
| CAISO OASIS API — California grid operator public market/load data | <http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=SLD_FCST&version=1&market_run_id=ACTUAL> | esg-disclosure-signal | free | high |
| CDP Open Data Portal — Cities/States/Regions Climate Disclosure (Socrata API) | <https://data.cdp.net/resource/cbdf-w4g3.json> | esg-disclosure-signal | free | high |
| CarbonPlan OffsetsDB — сводный датасет кредитов/проектов Verra, Gold Standard, ACR, CAR и других реестров | <https://carbonplan-offsets-db.s3.us-west-2.amazonaws.com/production/latest/offsets-db.csv.zip> | esg-disclosure-signal | free | high |
| Climate TRACE API — asset-level спутниковый мониторинг выбросов парниковых газов | <https://api.climatetrace.org/v6/assets> | esg-disclosure-signal | free | high |
| Copernicus Climate Data Store (CDS) API — реанализ и спутниковые климатические датасеты EU | <https://cds.climate.copernicus.eu/api> | esg-disclosure-signal | нужен ключ | high |
| ENTSO-E Transparency Platform API — European grid operator association data | <https://web-api.tp.entsoe.eu/api> | esg-disclosure-signal | нужен ключ | high |
| EPA Envirofacts — Toxics Release Inventory (TRI) API | <https://data.epa.gov/dmapservice/tri.tri_facility/state_abbr/equals/CA/json> | esg-disclosure-signal | free | high |
| Ember (Energy Think Tank) — RSS | <https://ember-energy.org/feed/> | esg-disclosure-signal | free | high |
| FAO AQUASTAT — глобальная система водных ресурсов (BigQuery-API) | <https://api.data.apps.fao.org/api/v2/bigquery?sql_url=https://data.apps.fao.org/catalog/dataset/945666e6-7803-4621-b8ef-cfd885a84596/resource/4a000a1b-24f0-4328-aab6-b9b525892090/download/query_en.sql&area=World&variable=4188&type=all&year=2020> | esg-disclosure-signal | free | high |
| Global Power Plant Database (World Resources Institute) — plant-level generator CSV | <https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv> | esg-disclosure-signal | free | high |
| ICLEI — Local Governments for Sustainability RSS | <https://iclei.org/feed/> | esg-disclosure-signal | free | high |
| NOAA National Water Prediction Service (NWPS) API — гидрологическое прогнозирование | <https://api.water.noaa.gov/nwps/v1/gauges/PTSA1> | esg-disclosure-signal | free | high |
| OpenStreetMap Overpass API — power=* renewable energy facility tags (query API) | <https://overpass-api.de/api/interpreter> | esg-disclosure-signal | free | medium |
| Our World in Data — Grapher CSV API (climate/energy datasets) | <https://ourworldindata.org/grapher/co2-emissions-per-capita.csv> | esg-disclosure-signal | free | high |
| RGGI (Regional Greenhouse Gas Initiative) — NY State Auction Results (Socrata API) | <https://data.ny.gov/resource/vxtc-b4mv.json> | esg-disclosure-signal | free | high |
| UN SDG API — Goal 6 (Clean Water and Sanitation) indicators | <https://unstats.un.org/sdgapi/v1/sdg/Indicator/List> | esg-disclosure-signal | free | high |
| USGS Water Data API (waterservices.usgs.gov) — real-time речные данные | <https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00060> | esg-disclosure-signal | free | high |
| WRI Aqueduct (via Resource Watch API) — водные риски и стресс-датасеты | <https://api.resourcewatch.org/v1/dataset?app=aqueduct> | esg-disclosure-signal | free | high |
| NOAA Paleoclimatology Data Search API | <https://www.ncei.noaa.gov/access/paleo-search/study/search.json?dataTypeId=17> | historical-climate-reconstruction-signal | free | high |
| IOM DTM — Displacement Tracking Matrix API (internally displaced persons) | <https://dtm.iom.int/data-and-analysis/dtm-api> | humanitarian-crisis-signal | нужен ключ | high |
| UN OCHA HDX — Humanitarian Data Exchange (CKAN API) | <https://data.humdata.org/api/3/action/package_search?q=conflict&rows=2> | humanitarian-crisis-signal | free | high |
