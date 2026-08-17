# Реестр источников — Рынки и макро

Макрориски, цены, финансовое состояние, раунды и объёмы производства.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 130, из них 14 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| FAO FAOSTAT — Forestry Production and Trade Bulk Data | <https://bulks-faostat.fao.org/production/Forestry_E_All_Data.zip> | commodity-production-volume-signal | free | high |
| SEC EDGAR Full-Text Search API — 10-Q Financial Distress Search ("going concern") | <https://efts.sec.gov/LATEST/search-index?q=%22going+concern%22&forms=10-Q> | financial-distress-signal | free | high |
| US Treasury Fiscal Data API — Debt to the Penny | <https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny> | financial-distress-signal | free | high |
| CNRS (Centre national de la recherche scientifique) RSS | <https://www.cnrs.fr/en/rss.xml> | funding-signal | free | high |
| Chan Zuckerberg Initiative RSS (частный научный фонд) | <https://chanzuckerberg.com/feed/> | funding-signal | free | high |
| CoinGecko API — cryptocurrency market data | <https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=3> | funding-signal | free | high |
| Finyear — RSS Feed | <https://finyear.com/feed> | funding-signal | free | medium |
| FrenchWeb (FW.MEDIA) — RSS Feed | <https://www.frenchweb.fr/feed> | funding-signal | free | medium |
| MamStartup — RSS Feed | <https://mamstartup.pl/feed> | funding-signal | free | medium |
| NASDAQ IPO Calendar API — priced and upcoming IPOs | <https://api.nasdaq.com/api/ipo/calendar?date=2026-08> | funding-signal | free | high |
| Payment & Banking — RSS Feed | <https://paymentandbanking.com/payment/rss/> | funding-signal | free | medium |
| Private Equity Wire RSS | <https://www.privateequitywire.co.uk/feed> | funding-signal | free | high |
| Yahoo Finance — Chart API (real-time/historical stock quotes) | <https://query1.finance.yahoo.com/v8/finance/chart/AAPL> | funding-signal | free | medium |
| deutsche-startups.de — RSS Feed | <https://www.deutsche-startups.de/feed/> | funding-signal | free | medium |
| ABC News Australia — Just In RSS Feed | <https://www.abc.net.au/news/feed/51120/rss.xml> | macro-risk | free | high |
| African Union — RSS Feed | <https://au.int/en/rss.xml> | macro-risk | free | high |
| Argentina datos.gob.ar Series API (INDEC/Ministerio de Economía time series) | <https://apis.datos.gob.ar/series/api/series/?ids=168.1_I2NG_2016_M_22:percent_change_a_year_ago> | macro-risk | free | high |
| Australian Bureau of Statistics — SDMX Data API (CPI) | <https://data.api.abs.gov.au/rest/data/ABS,CPI/all?startPeriod=2025&format=jsondata> | macro-risk | free | high |
| BTS Port Performance Freight Statistics — Monthly TEU Data API | <https://data.bts.gov/resource/rd72-aq8r.json> | macro-risk | free | high |
| Banco Central de Reserva del Perú — Series Estadísticas API | <https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01288PM/json> | macro-risk | free | high |
| Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS) API | <https://api.bcb.gov.br/dados/serie/bcdata.sgs.4/dados?formato=json&dataInicial=01/01/2024&dataFinal=01/06/2024> | macro-risk | free | high |
| Bank for International Settlements — Statistics API (dataflow catalog) | <https://stats.bis.org/api/v2/structure/dataflow/BIS/all/latest> | macro-risk | free | high |
| Bank of Japan — What's New RSS | <https://www.boj.or.jp/en/rss/whatsnew.xml> | macro-risk | free | high |
| Bellona International — RSS Feed | <https://bellona.org/feed> | macro-risk | free | high |
| Brazil — IBGE Agregados API (national statistics) | <https://servicodados.ibge.gov.br/api/v3/agregados> | macro-risk | free | high |
| CBS Netherlands OData API — Statistics Netherlands | <https://opendata.cbs.nl/ODataApi/odata/83913NED> | macro-risk | free | high |
| CMU Delphi Epidata API — влa-surveillance (FluView/ILINet) + историческое зеркало JHU CSSE COVID-19 | <https://api.delphi.cmu.edu/epidata/fluview/?regions=nat&epiweeks=202301> | macro-risk | free | high |
| CSIS (Center for Strategic and International Studies) — RSS | <https://www.csis.org/rss.xml> | macro-risk | free | high |
| CSO Ireland PxStat API — Central Statistics Office | <https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/PEA01/JSON-stat/2.0/en> | macro-risk | free | high |
| Canada Open Data CKAN API — Economy Datasets | <https://open.canada.ca/data/en/api/3/action/package_search?q=economy&rows=20> | macro-risk | free | high |
| Celestrak — General Perturbations (GP) Satellite Element Sets API | <https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json> | macro-risk | free | high |
| China Meteorological Administration — 中央气象台/国家气象中心 (NMC) Weather Alerts API | <http://www.nmc.cn/rest/findAlarm> | macro-risk | free | high |
| Cochilco (Chilean Copper Commission) — Historical Refined Copper Price Series, Monthly XLSX | <https://www.cochilco.cl/web/download/887/cobre/12537/precios-del-cobre-refinado-mensual-2.xlsx> | macro-risk | free | high |
| Colombia datos.gov.co (Socrata Open Data) — DANE/Banco de la República TRM series | <https://www.datos.gov.co/resource/32sa-8pi3.json?$limit=3> | macro-risk | free | high |
| Daily Maverick — RSS Feed | <https://www.dailymaverick.co.za/dmrss/> | macro-risk | free | high |
| Dawn (Pakistan) — Home RSS Feed | <https://www.dawn.com/feeds/home> | macro-risk | free | high |
| Dhaka Tribune (Bangladesh) — RSS Feed | <https://www.dhakatribune.com/feed/> | macro-risk | free | medium |
| ECB Statistical Data Warehouse API — exchange rates and monetary statistics | <https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=jsondata&lastNObservations=5> | macro-risk | free | high |
| ECDC Surveillance Atlas of Infectious Diseases — Atlas Service REST API | <https://atlas.ecdc.europa.eu/public/AtlasService/rest/GetHealthTopics> | macro-risk | free | high |
| EPA AirNow API — качество воздуха США | <https://www.airnowapi.org/aq/observation/zipCode/current/> | macro-risk | нужен ключ | high |
| European Hydrogen Observatory — Datasets (EU hydrogen strategy tracking) | <https://observatory.clean-hydrogen.europa.eu/tools-reports/datasets> | macro-risk | free | high |
| Eurostat API — Complete Energy Balances | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_bal_c?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — Cow's Milk Production by NUTS 2 Region | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/agr_r_milkpr?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — GDP and main components (national accounts) | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — Gini Coefficient of Equivalised Disposable Income by Age | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_di12?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — Government Deficit/Surplus, Debt (EDP) | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10dd_edpt1?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — HICP Inflation, Monthly Annual Rate of Change | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — Health Care Expenditure by Financing Scheme | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hlth_sha11_hf?format=JSON&lang=EN> | macro-risk | free | high |
| Eurostat API — International Trade by SITC Product Group | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ext_lt_intertrd?format=JSON&lang=EN> | macro-risk | free | high |
| FAO GIEWS — Food Price Monitoring and Analysis (FPMA) API | <https://fpma.fao.org/giews/v4/global/price_module/api/v1/FpmaSerieInternational/> | macro-risk | free | high |
| FDIC BankFind API — Failed Bank List | <https://banks.data.fdic.gov/api/failures?limit=5> | macro-risk | free | high |
| FMCSA QCMobile API — Motor Carrier Safety & Registration Data | <https://mobile.fmcsa.dot.gov/qc/services/carriers/name/{name}?webKey=YOUR_KEY> | macro-risk | нужен ключ | high |
| GAO (Government Accountability Office) — Reports RSS Feed | <https://www.gao.gov/rss/reports.xml> | macro-risk | free | high |
| GDACS — Global Disaster Alert and Coordination System (GeoJSON Events API) | <https://www.gdacs.org/gdacsapi/api/Events/geteventlist/EVENTS4APP> | macro-risk | free | high |
| Global Forest Watch Data API — NASA VIIRS Active Fire Alerts (375m, daily) | <https://data-api.globalforestwatch.org/dataset/nasa_viirs_fire_alerts> | macro-risk | free | high |
| Global Voices — RSS Feed | <https://globalvoices.org/feed/> | macro-risk | free | medium |
| IAEA — Media Advisories RSS Feed | <https://www.iaea.org/feeds/pressalerts> | macro-risk | free | high |
| ILOSTAT SDMX API — Labour Force Participation Rate by Sex and Age | <https://sdmx.ilo.org/rest/data/ILO,DF_EAP_DWAP_SEX_AGE_RT,1.0/all?startPeriod=2024&format=jsondata> | macro-risk | free | high |
| IMF DataMapper API — макроэкономические индикаторы по странам | <https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH> | macro-risk | free | high |
| IMF Primary Commodity Prices — Monthly XLSX | <https://www.imf.org/-/media/files/research/commodityprices/monthly/external-data.xlsx> | macro-risk | free | high |
| INE Spain (Tempus3) — Instituto Nacional de Estadística REST API | <https://servicios.ine.es/wstempus/js/EN/DATOS_TABLA/50902> | macro-risk | free | high |
| INSEE (France) — Base de Données Macroéconomiques API | <https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/001688527> | macro-risk | free | high |
| ISTAT SDMX REST API — Italian National Institute of Statistics | <https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_289/ALL/ALL> | macro-risk | free | high |
| International Centre for Defence and Security (Estonia) — RSS Feed | <https://icds.ee/en/feed/> | macro-risk | free | high |
| Investing.com — Commodities Analysis & Opinion RSS | <https://www.investing.com/rss/commodities.rss> | macro-risk | free | medium |
| Israel Central Bureau of Statistics — Price Index API | <https://api.cbs.gov.il/index/data/price?id=120010> | macro-risk | free | high |
| Jamestown Foundation — RSS Feed | <https://jamestown.org/feed/> | macro-risk | free | high |
| Japan Meteorological Agency (JMA) — Forecast Data API (JSON) | <https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json> | macro-risk | free | high |
| KAPSARC Data Portal — IEA Hydrogen Projects Database (Opendatasoft API mirror) | <https://datasource.kapsarc.org/api/records/1.0/search/?dataset=iea-hydrogen-projects-database-2021-revised&rows=2> | macro-risk | free | high |
| KOSIS (Korean Statistical Information Service) OpenAPI — statistics list | <https://kosis.kr/openapi/statisticsList.do?method=getList&apiKey=YOUR_KEY&format=json&vwCd=MT_ZTITLE&parentListId=A> | macro-risk | нужен ключ | high |
| Lowy Institute — The Interpreter RSS Feed | <https://www.lowyinstitute.org/the-interpreter/rss.xml> | macro-risk | free | high |
| Malaysia DOSM OpenDOSM API — Consumer Price Index | <https://api.data.gov.my/data-catalogue?id=cpi_headline> | macro-risk | free | high |
| Mexico — INEGI Banco de Indicadores API (national statistics) | <https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/1002000001/es/00/false/BISE/2.0/{TOKEN}> | macro-risk | нужен ключ | high |
| NASA Earthdata Common Metadata Repository (CMR) — Collections Search API | <https://cmr.earthdata.nasa.gov/search/collections.json> | macro-risk | free | high |
| NASA GISS Surface Temperature Analysis (GISTEMP) — глобальная температурная аномалия CSV | <https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv> | macro-risk | free | high |
| NOAA CPC Degree Days — Population-Weighted Heating/Cooling Degree Days (CONUS) | <https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/2026/StatesCONUS.Cooling.txt> | macro-risk | free | high |
| NOAA Climate Data Online (CDO) API — исторические климатические наблюдения (требует бесплатный токен) | <https://www.ncdc.noaa.gov/cdo-web/api/v2/datasets> | macro-risk | нужен ключ | high |
| NOAA Climate Prediction Center — ONI (Oceanic Niño Index) El Niño/La Niña | <https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt> | macro-risk | free | high |
| NOAA Space Weather Prediction Center — Alerts API | <https://services.swpc.noaa.gov/products/alerts.json> | macro-risk | free | high |
| NOAA Storm Events Database — Bulk CSV (property/crop damage by event) | <https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/> | macro-risk | free | high |
| Narodowy Bank Polski (Poland) — Exchange Rates API | <https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json> | macro-risk | free | high |
| Norges Bank SDMX API — Central Bank of Norway (exchange rates) | <https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=sdmx-json&lastNObservations=1> | macro-risk | free | high |
| OECD SDMX Data API — Air Emissions, Greenhouse Gas Inventories | <https://sdmx.oecd.org/public/rest/data/OECD.ENV.EPI,DSD_AIR_GHG@DF_AIR_GHG,1.0/all?format=jsondata> | macro-risk | free | high |
| OECD SDMX Data API — FDI Flows Main Aggregates (BMD4) | <https://sdmx.oecd.org/public/rest/data/OECD.DAF.INV,DSD_FDI@DF_FDI_FLOW_AGGR,1.0/all?format=jsondata> | macro-risk | free | high |
| OECD SDMX Data API — GHG Footprints Embodied in Bilateral Trade (2025 Edition) | <https://sdmx.oecd.org/public/rest/data/OECD.STI.PIE,DSD_ICIO_GHG_TRADE_2025@DF_ICIO_GHG_TRADE_2025,1.0/all?format=jsondata> | macro-risk | free | high |
| OECD SDMX Data API — Life Expectancy | <https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_STAT@DF_LE,1.1/all?format=jsondata> | macro-risk | free | high |
| OECD SDMX Data API — Quarterly National Accounts | <https://sdmx.oecd.org/public/rest/data/OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.1/all?startPeriod=2025&format=jsondata> | macro-risk | free | high |
| Ocean Conservancy — RSS | <https://oceanconservancy.org/feed/> | macro-risk | free | high |
| Open-Meteo — Global Weather Forecast API | <https://api.open-meteo.com/v1/forecast> | macro-risk | free | high |
| Pacific Islands News Association (PINA) — RSS Feed | <https://pina.com.fj/feed/> | macro-risk | free | medium |
| Portugal INE — Indicador JSON API | <https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0008273&Dim1=S1T1&Lang=EN> | macro-risk | free | high |
| Premium Times Nigeria — RSS Feed | <https://www.premiumtimesng.com/feed> | macro-risk | free | high |
| RAND Corporation — New Publications Atom Feed | <https://www.rand.org/pubs/new.xml> | macro-risk | free | high |
| RNZ (Radio New Zealand) — National Headlines RSS Feed | <https://www.rnz.co.nz/rss/national.xml> | macro-risk | free | high |
| Reserve Bank of India — Press Releases RSS | <https://rbi.org.in/pressreleases_rss.xml> | macro-risk | free | high |
| SCB Sweden API — Statistics Sweden (Doris API) | <https://api.scb.se/OV0104/v1/doris/en/ssd> | macro-risk | free | high |
| SSB Norway API — Statistics Norway (Consumer Price Index) | <https://data.ssb.no/api/v0/en/table/03013> | macro-risk | free | high |
| SingStat Table Builder API — Singapore GDP (chained dollars) | <https://tablebuilder.singstat.gov.sg/api/table/tabledata/M014911> | macro-risk | free | high |
| South African Institute of International Affairs — RSS Feed | <https://saiia.org.za/feed/> | macro-risk | free | high |
| South African Reserve Bank — Web API (market rates) | <https://custom.resbank.co.za/SarbWebApi/WebIndicators/CurrentMarketRates> | macro-risk | free | high |
| Statbel Bestat API — Belgian Statistical Office | <https://bestat.statbel.fgov.be/bestat/api/views> | macro-risk | free | high |
| Statistics Canada — Web Data Service (WDS) API | <https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods> | macro-risk | free | high |
| Sveriges Riksbank SWEA API — Central Bank of Sweden | <https://api.riksbank.se/swea/v1/Groups> | macro-risk | free | high |
| Swiss National Bank — Data Portal API (exchange rates) | <https://data.snb.ch/api/cube/devkua/data/json/en> | macro-risk | free | high |
| The Hindu — Latest News (National RSS Feed) | <https://www.thehindu.com/feeder/default.rss> | macro-risk | free | high |
| The Times of India — India News RSS Feed | <https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms> | macro-risk | free | medium |
| UK Office for National Statistics — Beta API v2 (datasets) | <https://api.beta.ons.gov.uk/v1/datasets> | macro-risk | free | high |
| UK data.gov.uk CKAN API — Crime Datasets | <https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=crime&rows=20> | macro-risk | free | high |
| UK data.gov.uk CKAN API — Environment Datasets | <https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=environment&rows=20> | macro-risk | free | high |
| UN Comtrade API — Preview Trade Data (No-Key Public Endpoint) | <https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=842&period=2023&partnerCode=0&cmdCode=TOTAL&flowCode=X> | macro-risk | free | high |
| UN Security Council Consolidated Sanctions List — XML export | <https://scsanctions.un.org/resources/xml/en/consolidated.xml> | macro-risk | free | high |
| UNHCR — Population Statistics API | <https://api.unhcr.org/population/v1/population/?limit=5> | macro-risk | free | high |
| US Bureau of Labor Statistics — Public Data API (unemployment rate) | <https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000> | macro-risk | free | high |
| US DOE Alternative Fuels Data Center — Alt Fuel Stations API (NREL) | <https://developer.nlr.gov/api/alt-fuel-stations/v1.json?api_key=DEMO_KEY&limit=2> | macro-risk | нужен ключ | high |
| US Energy Information Administration — API v2 (energy/commodity data) | <https://api.eia.gov/v2/?api_key=DEMO_KEY> | macro-risk | нужен ключ | high |
| US National Park Service — Developer API (parks, alerts, air quality by park) | <https://developer.nps.gov/api/v1/parks> | macro-risk | нужен ключ | high |
| USDA Agricultural Marketing Service — Market News API (public) | <https://marsapi.ams.usda.gov/services/v3.1/public/listPublishedReports?format=json> | macro-risk | free | high |
| USGS LandsatLook STAC API — Landsat Collection 2 Surface Reflectance | <https://landsatlook.usgs.gov/stac-server/search?collections=landsat-c2l2-sr&limit=1> | macro-risk | free | high |
| USGS Mineral Commodity Summaries — ScienceBase Data Release API | <https://www.sciencebase.gov/catalog/item/696a75d5d4be0228872d3bf8?format=json> | macro-risk | free | high |
| USGS Mineral Resources Data System — WFS API (global deposit-level registry) | <https://mrdata.usgs.gov/services/wfs/mrds?service=WFS&version=2.0.0&request=GetFeature&typeNames=mrds> | macro-risk | free | high |
| USGS Volcano Hazards Program — HANS API (real-time уровни вулканической опасности США) | <https://volcanoes.usgs.gov/hans-public/api/volcano/getElevatedVolcanoes> | macro-risk | free | high |
| Venezuelanalysis — RSS Feed | <https://venezuelanalysis.com/feed> | macro-risk | free | medium |
| World Bank Commodity Price Data (Pink Sheet) — Monthly XLSX | <https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx> | macro-risk | free | high |
| data.gov.au CKAN API — Water Resources Datasets | <https://data.gov.au/data/api/3/action/package_search?q=water&rows=20> | macro-risk | free | high |
| e-Stat Japan — Portal Site of Official Statistics of Japan API | <https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList?appId=YOUR_APP_ID&lang=E> | macro-risk | нужен ключ | high |
| ČSÚ (CZSO) Katalog API — Czech Statistical Office | <https://data.czso.cz/api/katalog/v1/sady> | macro-risk | free | high |
| AISstream.io — Real-time AIS Vessel Tracking WebSocket API | <https://aisstream.io/documentation> | market-price-signal | нужен ключ | medium |
| DefiLlama API — DeFi Total Value Locked (TVL) | <https://api.llama.fi/protocols> | market-price-signal | free | high |
| Etherscan API V2 — Ethereum on-chain explorer data | <https://api.etherscan.io/v2/api?chainid=1&module=stats&action=ethsupply> | market-price-signal | нужен ключ | high |
| UNCTADstat — Liner Shipping Connectivity Index + Container Port Throughput | <https://unctadstat.unctad.org/datacentre/dataviewer/US.LSCI> | market-price-signal | free | high |
