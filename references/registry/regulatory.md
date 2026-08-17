# Реестр источников — Регуляторика и право

Регуляторные риски и возможности, законодательный процесс, стандарты, права на ресурсы.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 137, из них 11 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| Australia Consumer Data Right (CDR) Register — Data Holders Brands API | <https://api.cdr.gov.au/cdr-register/v1/all/data-holders/brands/summary> | identity-standard-signal | free | high |
| Brazil Open Finance (Banco Central) — Directory Participants API | <https://data.directory.openbankingbrasil.org.br/participants> | identity-standard-signal | free | high |
| Hong Kong Monetary Authority — Open API Framework for the Banking Sector | <https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity?lang=en> | identity-standard-signal | free | high |
| Bayerischer Landtag — Drucksachen von Gesetzentwürfen RSS | <https://www.bayern.landtag.de/webangebot3/views/rssfeed/rssfeed.xhtml?art=GESETZ&titel=Drucksachen+von+Gesetzentw%C3%BCrfen> | legislative-process-signal | free | high |
| Brazil — Câmara dos Deputados Open Data API (Proposições) | <https://dadosabertos.camara.leg.br/api/v2/proposicoes?ano=2026&itens=3> | legislative-process-signal | free | high |
| Canada Parliament — LEGISinfo Bills JSON API | <https://www.parl.ca/legisinfo/en/bills/json> | legislative-process-signal | free | high |
| European Parliament — Open Data Portal, Legislative Procedures API | <https://data.europarl.europa.eu/api/v2/procedures?format=application%2Fld%2Bjson&offset=0&limit=20> | legislative-process-signal | free | high |
| Finland — Eduskunta Avoindata API (VaskiData) | <https://avoindata.eduskunta.fi/api/v1/tables/VaskiData/rows?perPage=3> | legislative-process-signal | free | high |
| France — Assemblée Nationale Open Data (Dossiers Législatifs) | <https://data.assemblee-nationale.fr/static/openData/repository/17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip> | legislative-process-signal | free | high |
| GovTrack.us — US Congress Bill API | <https://www.govtrack.us/api/v2/bill> | legislative-process-signal | free | high |
| Ireland — Oireachtas Open Data API (Legislation) | <https://api.oireachtas.ie/v1/legislation?limit=3> | legislative-process-signal | free | high |
| Israel — Knesset OData API (KNS_Bill legislative collection) | <https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill> | legislative-process-signal | free | high |
| Italy — Camera dei Deputati Open Data (dati.camera.it SPARQL) | <https://dati.camera.it/sparql> | legislative-process-signal | free | high |
| Netherlands — Tweede Kamer Open Data Portal (OData API) | <https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/Zaak?%24top=3> | legislative-process-signal | free | high |
| Poland — Sejm API (legislative prints, term 10) | <https://api.sejm.gov.pl/sejm/term10/prints> | legislative-process-signal | free | high |
| South Africa — Parliamentary Monitoring Group Bill API | <https://api.pmg.org.za/bill/?format=json&limit=3> | legislative-process-signal | free | high |
| Spain — Congreso de los Diputados Open Data (Votaciones) | <https://www.congreso.es/webpublica/opendata/votaciones/Leg15/Sesion193/20260723/Votacion001/VOT_20260723211929.json> | legislative-process-signal | free | high |
| Sweden — Riksdagen Open Data (Dokumentlista API) | <https://data.riksdagen.se/dokumentlista/?doktyp=prop&utformat=json&sz=3> | legislative-process-signal | free | high |
| Sénat — Derniers textes RSS | <https://www.senat.fr/rss/textes.rss> | legislative-process-signal | free | high |
| UK Parliament — Bills API | <https://bills-api.parliament.uk/api/v1/Bills> | legislative-process-signal | free | high |
| US Boston City Council — Legistar Matters API | <https://webapi.legistar.com/v1/boston/matters> | legislative-process-signal | free | high |
| US Florida Senate — Daily Calendar of Events RSS | <https://www.flsenate.gov/Tracker/RSS/DailyCalendar> | legislative-process-signal | free | high |
| US Ohio General Assembly — Legislative Information System API | <https://search-prod.lis.state.oh.us/api/v2/general_assembly_134/legislation/> | legislative-process-signal | free | high |
| Washington State Legislature — Legislation Web Service (SOAP) | <https://wslwebservices.leg.wa.gov/LegislationService.asmx?WSDL> | legislative-process-signal | free | high |
| ABET — Accreditation Board for Engineering and Technology, RSS | <https://www.abet.org/feed/> | regulatory-opportunity | free | high |
| American Water Works Association (AWWA) — RSS Feed | <https://www.awwa.org/feed/> | regulatory-opportunity | free | high |
| Australia ATO (Australian Taxation Office) — open data via data.gov.au CKAN | <https://data.gov.au/data/api/3/action/package_search?q=organization:australiantaxationoffice> | regulatory-opportunity | free | high |
| BIP Urząd Marszałkowski Województwa Lubuskiego — Komunikaty RSS | <https://bip.lubuskie.pl/rss/kanal/1/> | regulatory-opportunity | free | medium |
| CMS Medicare Part D Spending by Drug API | <https://data.cms.gov/data-api/v1/dataset/7e0b4365-fd63-4a29-8f5e-e0ac9f66a81b/data> | regulatory-opportunity | free | high |
| California data.ca.gov — state CKAN open data portal (healthcare licensing) | <https://data.ca.gov/api/3/action/package_search?q=business+license&rows=3> | regulatory-opportunity | free | high |
| Canada Revenue Agency (CRA) — open data через open.canada.ca CKAN | <https://open.canada.ca/data/api/action/package_search?fq=organization:cra-arc&rows=331> | regulatory-opportunity | free | high |
| City of Buffalo Open Data (Socrata API) — Business Licenses | <https://data.buffalony.gov/resource/qcyy-feh8.json?$limit=3> | regulatory-opportunity | free, rate-limited | high |
| D@tARA (Auvergne-Rhône-Alpes) — Atom Feed | <https://catalogue.open-datara.fr/rss/atomfeed/topatom> | regulatory-opportunity | free | medium |
| EFMD Global — European Foundation for Management Development, RSS | <https://www.efmdglobal.org/feed/> | regulatory-opportunity | free | high |
| EUR-Lex / Publications Office CELEX Content-Negotiation API — European Accessibility Act (Directive 2019/882) | <http://publications.europa.eu/resource/celex/32019L0882> | regulatory-opportunity | free | high |
| Eurostat API — Share of Renewable Energy (Main Indicators) | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_ind_ren?format=JSON&lang=EN> | regulatory-opportunity | free | high |
| FCC National Broadband Map — Broadband Data Collection (BDC) Public API | <https://broadbandmap.fcc.gov/api/public/map/downloads/listAsOfDates> | regulatory-opportunity | нужен ключ | high |
| France — data.gouv.fr Datasets API | <https://www.data.gouv.fr/api/1/datasets/?page_size=3> | regulatory-opportunity | free | high |
| Google Political Ads Transparency Report — Bulk CSV Bundle | <https://storage.googleapis.com/political-csv/google-political-ads-transparency-bundle.zip> | regulatory-opportunity | free | high |
| Google Transparency Report — EU DSA Compliance Reports (bulk XLSX) | <https://storage.googleapis.com/transparencyreport/dsa/> | regulatory-opportunity | free | high |
| Helsingin kaupunki Open Data (WFS via HRI CKAN) — Ympäristölupakohteet | <https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=wfs&version=2.0.0&request=getfeature&typeNames=avoindata:Ymparistolupakohteet&count=2&outputFormat=json> | regulatory-opportunity | free | high |
| Illinois Gaming Board — Casino Monthly Reports discovery API (AEM data table JSON) | <https://igb.illinois.gov/content/soi/igb/en/casino-gambling/casino-reports/jcr:content/responsivegrid/container/container_293684588/container/container_copy/container_1711859025/data_table_assets.datatableassets.json> | regulatory-opportunity | free | high |
| International Seabed Authority — Deep-Sea Mining Governance & Exploration Contracts Feed | <https://isa.org.jm/feed/> | regulatory-opportunity | free | high |
| Japan — data.go.jp (e-Gov) CKAN Open Data API | <https://data.e-gov.go.jp/data/api/action/package_search?rows=3> | regulatory-opportunity | free | high |
| Microsoft Airband Initiative — US Broadband Usage Percentages dataset | <https://raw.githubusercontent.com/microsoft/USBroadbandUsagePercentages/master/dataset/broadband_data_2020October.csv> | regulatory-opportunity | free | high |
| NGO Shipbreaking Platform — Vessel Recycling & Shipbreaking Industry Oversight | <https://shipbreakingplatform.org/feed/> | regulatory-opportunity | free | high |
| Nashville/Davidson County TN — Open Data ArcGIS DCAT-US feed | <https://data.nashville.gov/api/feed/dcat-us/1.1.json> | regulatory-opportunity | free | high |
| National Zoning Atlas — Mercatus Urbanity structured zoning geojson (Montana) | <https://raw.githubusercontent.com/MercatusUrbanity/ZoningAtlas/main/MT_zoning.geojson> | regulatory-opportunity | free | medium |
| OECD SDMX Data API — Shares of CO2 Emissions from Energy Priced (Effective Carbon Rates) | <https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_ECR@DF_SEP,1.0/all?format=jsondata> | regulatory-opportunity | free | high |
| OECD — SDMX Data API (National Accounts, макроэкономика) | <https://sdmx.oecd.org/public/rest/data/OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.0/all> | regulatory-opportunity | free | high |
| OpenDataPhilly — Philadelphia CKAN open data portal | <https://opendataphilly.org/api/3/action/package_search?rows=3> | regulatory-opportunity | free | high |
| UK Certification Officer — Official List of Trade Unions (GOV.UK Content API) | <https://www.gov.uk/api/content/government/publications/official-list-of-trade-unions/current-trade-unions> | regulatory-opportunity | free | high |
| UK Gender Pay Gap Service — Employer Reporting Bulk CSV Download | <https://gender-pay-gap.service.gov.uk/viewing/download-data/2023> | regulatory-opportunity | free | high |
| UK data.gov.uk CKAN API — Planning Datasets | <https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=planning&rows=20> | regulatory-opportunity | free | high |
| UN Comtrade — публичный preview API таможенно-торговой статистики | <https://comtradeapi.un.org/public/v1/preview/C/A/HS> | regulatory-opportunity | free | high |
| UN SDG Indicators API — Series Data (Sustainable Development Goals global monitoring) | <https://unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=SI_POV_DAY1&pageSize=3> | regulatory-opportunity | free | high |
| US Department of Energy — Newsroom RSS | <https://www.energy.gov/rss.xml> | regulatory-opportunity | free | high |
| US HMDA (Home Mortgage Disclosure Act) — FFIEC Data Browser API | <https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations?states=MD&years=2018&races=White> | regulatory-opportunity | free | high |
| US NRC — Power Reactor Status Report RSS | <https://www.nrc.gov/public-involve/rss?feed=plant-status> | regulatory-opportunity | free | high |
| WHO Global Health Observatory (GHO) OData API — Life Expectancy at Birth | <https://ghoapi.azureedge.net/api/WHOSIS_000001?$top=3> | regulatory-opportunity | free | high |
| WIPO — Press Releases RSS | <https://www.wipo.int/pressroom/en/rss.xml> | regulatory-opportunity | free | high |
| Western PA Regional Data Center (WPRDC) — City of Pittsburgh PLI Permits (CKAN DataStore API) | <https://data.wprdc.org/api/3/action/datastore_search?resource_id=f4d1177a-f597-4c32-8cbf-7885f56253f6&limit=3> | regulatory-opportunity | free | high |
| World Nuclear Association — Reactor Database API | <https://world-nuclear.org/nuclear-reactor-database/getreactordata?pageSize=12&searchString=&pageNumber=1&location=&status=&process=&owner=&operators=&construction=&gridconnections=&shutdown=&referenceunitpower=> | regulatory-opportunity | free | high |
| data.europa.eu Hub Search API — Public Procurement Datasets | <https://data.europa.eu/api/hub/search/search?q=public%20procurement&limit=20> | regulatory-opportunity | free | high |
| data.gov.au — CKAN package_search API | <https://data.gov.au/data/api/3/action/package_search> | regulatory-opportunity | free | high |
| data.gov.sg v2 API — Registered Entities (UEN registry, регуляторная коллекция) | <https://api-production.data.gov.sg/v2/public/api/collections/1/metadata> | regulatory-opportunity | free | high |
| data.gov.uk — CKAN Open Data API (UK government datasets) | <https://data.gov.uk/api/3/action/package_search?q=GDP&rows=3> | regulatory-opportunity | free | high |
| openFDA — Drug@FDA Approval Records API | <https://api.fda.gov/drug/drugsfda.json> | regulatory-opportunity | free, rate-limited | high |
| ACMA (Australia telecom regulator) — датасеты через data.gov.au CKAN | <https://data.gov.au/data/api/3/action/package_search?fq=organization:australiancommunicationsandmediaauthority> | regulatory-risk | free | high |
| AEMPS (Spain) — Agencia Española de Medicamentos y Productos Sanitarios — RSS Feed | <https://www.aemps.gob.es/feed/> | regulatory-risk | free | high |
| AGCOM (Italy) — Autorità per le Garanzie nelle Comunicazioni, RSS | <https://www.agcom.it/rss.xml> | regulatory-risk | free | high |
| ANVISA (Brazil) — Agência Nacional de Vigilância Sanitária — Notícias RSS | <https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/RSS> | regulatory-risk | free | high |
| APRA (Australia banking/insurance regulator) — датасеты через data.gov.au CKAN | <https://data.gov.au/data/api/3/action/package_search?fq=organization:australianprudentialregulationauthority> | regulatory-risk | free | high |
| Ajuntament de Barcelona Open Data (CKAN) — Detall de denúncies i sancions de trànsit | <https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_show?id=denuncies_sancions_transit_bcn_detall> | regulatory-risk | free | high |
| Australia OAIC — Media RSS (Office of the Australian Information Commissioner) | <https://www.oaic.gov.au/rss> | regulatory-risk | free | high |
| BEREC — Body of European Regulators for Electronic Communications, RSS | <https://www.berec.europa.eu/en/rss.xml> | regulatory-risk | free | high |
| Belgium — data.gov.be Open Data API/RSS hub | <https://data.gov.be/fr/api-rss> | regulatory-risk | free | high |
| Brazil ANPD — Notícias (Autoridade Nacional de Proteção de Dados) | <https://www.gov.br/anpd/pt-br> | regulatory-risk | free | high |
| Brazil CADE — Notícias (Conselho Administrativo de Defesa Econômica) | <https://www.gov.br/cade/pt-br> | regulatory-risk | free | high |
| Bundesnetzagentur (Germany) — Telekommunikation, RSS | <https://www.bundesnetzagentur.de/rss/Telekommunikation.xml> | regulatory-risk | free | high |
| CRTC (Canada) — Canadian Radio-television and Telecommunications Commission, Atom | <https://crtc.gc.ca/eng/rss/news.atom.xml> | regulatory-risk | free | high |
| Canada OPC — Newsroom RSS (Office of the Privacy Commissioner) | <https://www.priv.gc.ca/en/rss/news/> | regulatory-risk | free | high |
| Caselaw Access Project (Harvard Law School) — структурированный дамп судебной практики США | <https://static.case.law/ReportersMetadata.json> | regulatory-risk | free | high |
| Central Bank of Kenya — RSS | <https://www.centralbank.go.ke/feed/> | regulatory-risk | free | high |
| City of Oakland Open Data (Socrata API) — Public Ethics Commission Enforcement Actions | <https://data.oaklandca.gov/resource/djbd-zes9.json?$limit=3> | regulatory-risk | free, rate-limited | high |
| Comune di Milano Open Data (CKAN) — Edilizia: nuovi fabbricati con destinazione d'uso non residenziale | <https://dati.comune.milano.it/api/3/action/package_show?id=ds2984-edilizia-nuovi-fabbricati-con-destinazione-uso-non-residenziale> | regulatory-risk | free | high |
| Denmark — Retsinformation høsteservice REST API (Swagger UI живой, dataset-endpoint не подтверждён) | <https://api.retsinformation.dk/index.html> | regulatory-risk | free-with-restriction | high |
| ECB Banking Supervision — Press releases RSS | <https://www.bankingsupervision.europa.eu/rss/press.xml> | regulatory-risk | free | high |
| EUR-Lex CELLAR SPARQL — Court of Justice of the EU case-law (resource-type JUDG) | <https://publications.europa.eu/webapi/rdf/sparql?query=PREFIX%20cdm%3A%20%3Chttp%3A%2F%2Fpublications.europa.eu%2Fontology%2Fcdm%23%3E%20SELECT%20%3Fwork%20WHERE%20%7B%20%3Fwork%20cdm%3Awork_has_resource-type%20%3Chttp%3A%2F%2Fpublications.europa.eu%2Fresource%2Fauthority%2Fresource-type%2FJUDG%3E%20%7D%20LIMIT%203&format=application%2Fsparql-results%2Bjson> | regulatory-risk | free | high |
| European Medicines Agency (EMA) — Medicines Data Table (Excel, daily-updated) | <https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx> | regulatory-risk | free | high |
| European Securities and Markets Authority — RSS | <https://www.esma.europa.eu/rss.xml> | regulatory-risk | free | high |
| Eurostat API — Generation of Waste by Category and Economic Activity | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/env_wasgen?format=JSON&lang=EN> | regulatory-risk | free | high |
| Food Standards Australia New Zealand (FSANZ) — RSS Feed | <https://www.foodstandards.gov.au/rss.xml> | regulatory-risk | free | high |
| France Autorité de la concurrence — RSS (competition authority) | <https://www.autoritedelaconcurrence.fr/fr/rss.xml> | regulatory-risk | free | high |
| France CNIL — Commission Nationale de l'Informatique et des Libertés RSS | <https://www.cnil.fr/fr/rss.xml> | regulatory-risk | free | high |
| Gemeente Amsterdam Open Data (Datapunt API) — Vergunningen (Bed & Breakfast) | <https://api.data.amsterdam.nl/v1/vergunningen/bedandbreakfast/?_pageSize=3> | regulatory-risk | free | high |
| Germany BfDI — RSS-Newsfeed (federal data protection authority) | <https://www.bfdi.bund.de/SiteGlobals/Functions/RSSFeed/Allgemein/rssnewsfeed.xml?nn=251944> | regulatory-risk | free | high |
| Germany Bundeskartellamt — RSS-Newsfeed (federal antitrust authority) | <https://www.bundeskartellamt.de/DE/Service/RSS/_documents/rssnewsfeed.xml> | regulatory-risk | free | high |
| Health Canada — Drug Product Database (DPD) API | <https://health-products.canada.ca/api/drug/drugproduct/?lang=en&type=json> | regulatory-risk | free | high |
| Health Canada — Recalls and Safety Alerts API | <https://healthycanadians.gc.ca/recall-alert-rappel-avis/api/recent/en> | regulatory-risk | free | high |
| India CCI — Press Releases & Whats New (Competition Commission of India) | <https://www.cci.gov.in/> | regulatory-risk | free | high |
| Ireland DPC — Press Releases (Data Protection Commission) | <https://www.dataprotection.ie/en/news-media/press-releases> | regulatory-risk | free | high |
| Italy Garante per la protezione dei dati personali — RSS news | <https://www.garanteprivacy.it/o/gpdp-rss/rss?t=news> | regulatory-risk | free | high |
| Japan PPC — 報道発表資料 (Personal Information Protection Commission press releases) | <https://www.ppc.go.jp/news/press/> | regulatory-risk | free | high |
| Japan e-Gov — Laws Search API v2 | <https://laws.e-gov.go.jp/api/2/laws?law_title=個人情報> | regulatory-risk | free | high |
| Københavns Kommune Open Data (WFS via opendata.dk) — Parkeringszoner | <https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:p_zoner_kbh&srsname=EPSG:4326&outputFormat=application%2Fjson> | regulatory-risk | free | high |
| MFDS (South Korea) — 식품의약품안전처 — 입법/행정예고 (Legislative/Administrative Notices) RSS | <https://www.mfds.go.kr/www/rss/brd.do?brdId=data0009> | regulatory-risk | free | high |
| Netherlands AP — RSS Nieuwsberichten (Autoriteit Persoonsgegevens) | <https://autoriteitpersoonsgegevens.nl/feed/article/rss.xml> | regulatory-risk | free | high |
| Netherlands — BWB (Basis Wetten Bestand) SRU search API | <https://repository.overheid.nl/sru> | regulatory-risk | free-with-restriction | high |
| Norway — Lovdata "Siste nyheter" RSS | <https://lovdata.no/feed?data=newArticles&type=RSS> | regulatory-risk | free | high |
| Ofqual (UK) — Office of Qualifications and Examinations Regulation, Atom | <https://www.gov.uk/government/organisations/ofqual.atom> | regulatory-risk | free | high |
| Regulation & Governance RSS (Wiley) | <https://onlinelibrary.wiley.com/action/showFeed?type=etoc&feed=rss&jc=17485991> | regulatory-risk | free | high |
| Reserve Bank of Australia — Media Releases RSS | <https://www.rba.gov.au/rss/rss-cb-media-releases.xml> | regulatory-risk | free | high |
| Reserve Bank of India — Press Releases RSS | <https://www.rbi.org.in/pressreleases_rss.xml> | regulatory-risk | free | high |
| Seoul Open Data Plaza (열린데이터광장) — LOCALDATA Local Business Licence Registry | <http://openapi.seoul.go.kr:8088/sample/json/LOCALDATA_072404/1/5/> | regulatory-risk | free | medium |
| South Africa — Government Acts listing (SA Government) | <https://www.gov.za/documents/acts> | regulatory-risk | free | high |
| South Korea KFTC — 보도자료/공지 목록 (Fair Trade Commission press & notices list) | <https://www.ftc.go.kr/www/selectBbsNttList.do?bordCd=3&key=10> | regulatory-risk | free | high |
| South Korea PIPC — 보도자료 목록 (Personal Information Protection Commission press list) | <https://www.pipc.go.kr/np/cop/bbs/selectBoardList.do?bbsId=BS074&mCode=D010030000> | regulatory-risk | free | high |
| South Korea — Ministry of Government Legislation (law.go.kr) DRF Search API | <https://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=개인정보> | regulatory-risk | нужен ключ | high |
| Spain AEPD — Notas de prensa (Agencia Española de Protección de Datos) | <https://www.aepd.es/es/prensa-y-comunicacion/notas-de-prensa> | regulatory-risk | free | high |
| Spain — Boletín Oficial del Estado (BOE) daily RSS | <https://www.boe.es/rss/boe.php> | regulatory-risk | free | high |
| Species+/CITES Checklist API — Wildlife Trade Regulatory Status by Taxon | <https://api.speciesplus.net/api/v1/taxon_concepts> | regulatory-risk | нужен ключ | high |
| Sweden — Riksdagen Open Data API (SFS законодательство) | <https://data.riksdagen.se/dokumentlista/?doktyp=sfs&utformat=json&sz=5> | regulatory-risk | free | high |
| Switzerland — Fedlex ELI Linked Data (RDF/XML) | <https://fedlex.data.admin.ch/eli/oc/2026/1> | regulatory-risk | free | high |
| TRAI (Telecom Regulatory Authority of India) — RSS | <https://www.trai.gov.in/rss.xml> | regulatory-risk | free | high |
| Tokyo Metropolitan Open Data Catalog (CKAN) — Minato City Food Business Permit List | <https://opendata.city.minato.tokyo.jp/dataset/54d8c582-00e2-4730-a23f-4a5befec9ae5/resource/c9d0299e-8e05-4317-877f-83055709e41f/download/food_business_all.csv> | regulatory-risk | free | high |
| UK Find Case Law (The National Archives) — Atom Feed | <https://caselaw.nationalarchives.gov.uk/atom.xml> | regulatory-risk | free | high |
| UK Health and Safety Executive (HSE) — Media Centre Press Releases RSS | <https://press.hse.gov.uk/feed/> | regulatory-risk | free | high |
| UK Health and Safety Executive — Injury/Illness/Cancer Statistics Tables (XLSX bulk) | <https://www.hse.gov.uk/statistics/tables/index.htm> | regulatory-risk | free | high |
| UK ICO — Media Centre (Information Commissioner's Office) | <https://ico.org.uk/about-the-ico/media-centre/> | regulatory-risk | free | high |
| UK Trade Tariff API (gov.uk) — коды товаров, пошлины, меры экспортного/импортного контроля | <https://www.trade-tariff.service.gov.uk/api/v2/commodities/0101210000> | regulatory-risk | free | high |
| US FAA — Airport Status Web Service (ASWS) | <https://external-api.faa.gov/asws/api/airport/status/JFK> | regulatory-risk | free | high |
| US FRA — Rail Equipment Accident/Incident Data (Form 54) | <https://data.transportation.gov/resource/jm8x-ccxs.json> | regulatory-risk | free | high |
| US FTC — Press Releases RSS (antitrust enforcement) | <https://www.ftc.gov/feeds/press-release.xml> | regulatory-risk | free-with-restriction | high |
| Washington State Legislature — Web Services API (SOAP/XML) | <https://wslwebservices.leg.wa.gov/legislationservice.asmx/GetLegislationByYear?year=2026> | regulatory-risk | free | high |
| data.gov.au CKAN API — Biodiversity Datasets | <https://data.gov.au/data/api/3/action/package_search?q=biodiversity&rows=20> | regulatory-risk | free | high |
| Colorado DWR HydroBase — Water Rights Net Amounts REST API | <https://dwr.state.co.us/Rest/GET/api/v2/waterrights/netamount/?format=json&county=BOULDER> | resource-rights-registry-signal | free | high |
