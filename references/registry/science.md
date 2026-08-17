# Реестр источников — Наука

Фронтир исследований, датасеты, индексы цитирования, репликации, бенчмарки.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 98, из них 8 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| Hugging Face Open LLM Leaderboard results (datasets-server API) | <https://datasets-server.huggingface.co/rows?dataset=open-llm-leaderboard%2Fcontents&config=default&split=train&offset=0&length=2> | benchmark-shift | free | high |
| JetBrains State of Developer Ecosystem — Raw Data export | <https://resources.jetbrains.com/storage/products/research/DevEco2025/RawData.zip> | benchmark-shift | free | high |
| NIST FRVT (Face Recognition Technology Evaluation) — 1:1 Verification Leaderboard | <https://pages.nist.gov/frvt/html/frvt11.html> | benchmark-shift | free | high |
| CORE API v3 — Search Works (Global Open Access Aggregator) | <https://api.core.ac.uk/v3/search/works/?q=climate+policy&limit=5> | citation-index-signal | free, rate-limited | high |
| DataCite DOIs API | <https://api.datacite.org/dois?query=climate&page[size]=1> | citation-index-signal | free | high |
| OpenAlex Works API | <https://api.openalex.org/works?search=hypothesis&per-page=3> | citation-index-signal | free | high |
| Scite.ai Tallies API — Supporting/Contradicting Citation Context | <https://api.scite.ai/tallies/10.1038/nature12373> | citation-index-signal | free | high |
| Unpaywall API — open access status by DOI | <https://api.unpaywall.org/v2/10.1038/nature12373?email=unpaywall_test@example.org> | citation-index-signal | free | high |
| dblp Computer Science Bibliography — Search API | <https://dblp.org/search/publ/api?q=machine+learning&format=json> | citation-index-signal | free | high |
| ORCID Public API — Researcher Identity Search | <https://pub.orcid.org/v3.0/search?q=family-name:Smith> | publishing-infrastructure-signal | free | high |
| ClinicalTrials.gov API v2 — Study Registrations | <https://clinicaltrials.gov/api/v2/studies?pageSize=2> | replication-signal | free | high |
| F1000Research — Indexed Articles RSS (Open Post-Publication Review) | <https://f1000research.com/indexed/rss> | replication-signal | free | high |
| OSF Preprints API — MetaArXiv (Meta-Research, Research Methodology) | <https://api.osf.io/v2/preprints/?filter[provider]=metaarxiv&page[size]=3> | replication-signal | free | high |
| Retraction Watch RSS | <https://retractionwatch.com/feed/> | replication-signal | free | high |
| CDC PLACES — Short Sleep Duration Prevalence by US County (Socrata API) | <https://data.cdc.gov/resource/swc5-untb.json?measureid=SLEEP> | research-data-signal | free | high |
| DANS SSH Data Stations Search API (Netherlands social sciences/humanities data archive) | <https://ssh.datastations.nl/api/search?q=survey> | research-data-signal | free | high |
| Dryad Data Search API | <https://datadryad.org/api/v2/search?q=climate> | research-data-signal | free | high |
| ENERGY STAR API — Certified Products Data (Socrata/SODA) | <https://data.energystar.gov/resource/qbg3-d468.json> | research-data-signal | free | high |
| EPA CompTox Chemicals Dashboard — CTX Chemical + Bioactivity API (CCTE) | <https://comptox.epa.gov/ctx-api/chemical/detail/search/by-dtxsid/DTXSID7020182> | research-data-signal | нужен ключ | high |
| ESA Gaia Archive TAP+ API | <https://gea.esac.esa.int/tap-server/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=SELECT+TOP+50+source_id,ra,dec,parallax+FROM+gaiadr3.gaia_source> | research-data-signal | free | high |
| FAO Fisheries and Aquaculture Department — GeoServer WFS (Global Capture Production) | <https://www.fao.org/fishery/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=stats_capture:global_capture_production&outputFormat=application/json&count=2> | research-data-signal | free | high |
| GBIF Occurrence API (Global Biodiversity Information Facility) | <https://api.gbif.org/v1/occurrence/search?limit=1> | research-data-signal | free | high |
| Genesys PGR API — Global Plant Genetic Resources & Seed Bank Accessions | <https://api.genesys-pgr.org/api/v1/accessions/filters/countries> | research-data-signal | нужен ключ | high |
| IPUMS API — Historical Census & Survey Microdata (NHGIS/IPUMS-USA/International) | <https://api.ipums.org/metadata/nhgis/data_tables?collection=nhgis&version=v2> | research-data-signal | нужен ключ | high |
| MAST (Mikulski Archive for Space Telescopes) — CAOM Search API | <https://mast.stsci.edu/api/v0/invoke> | research-data-signal | free | high |
| NASA Exoplanet Archive TAP API | <https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+top+50+pl_name,hostname,disc_year,discoverymethod+from+ps&format=json> | research-data-signal | free | high |
| NOAA NCEI — Global Marine Data API (ICOADS ship/buoy observations) | <https://www.ncei.noaa.gov/access/services/data/v1?dataset=global-marine&format=json&startDate=2020-01-01&endDate=2020-01-02&boundingBox=60,-180,-60,180&limit=2> | research-data-signal | free | high |
| NSIDC — Sea Ice Index (daily extent, G02135) | <https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv> | research-data-signal | free | high |
| OBIS (Ocean Biodiversity Information System) — Occurrence API | <https://api.obis.org/v3/occurrence?scientificname=Orcinus%20orca&size=3> | research-data-signal | free | high |
| OSF Preprints API — Thesis Commons (Graduate Theses/Dissertations) | <https://api.osf.io/v2/preprints/?filter[provider]=thesiscommons&page[size]=3> | research-data-signal | free | medium |
| Paleobiology Database API (PBDB) | <https://paleobiodb.org/data1.2/occs/list.json?base_name=Tyrannosaurus&limit=2> | research-data-signal | free | high |
| PhysioNet — Published Sleep/Polysomnography Research Databases (API + raw EDF signals) | <https://physionet.org/api/v1/project/published/> | research-data-signal | free | high |
| PubChem PUG REST API (NIH) | <https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/MolecularFormula,MolecularWeight/JSON> | research-data-signal | free | high |
| RCSB Protein Data Bank — Data API | <https://data.rcsb.org/rest/v1/core/entry/4HHB> | research-data-signal | free | high |
| Research Data Australia (ARDC) — OAI-PMH Registry API | <https://researchdata.edu.au/registry/services/oai?verb=ListRecords&metadataPrefix=oai_dc> | research-data-signal | free | high |
| Software Heritage Archive API — Origin Visits | <https://archive.softwareheritage.org/api/1/origin/https://github.com/torvalds/linux/visits/> | research-data-signal | free | high |
| UCI Machine Learning Repository — Datasets List API | <https://archive.ics.uci.edu/api/datasets/list> | research-data-signal | free | high |
| USDA Economic Research Service — ARMS Data API | <https://api.ers.usda.gov/data/arms/year?api_key=YOUR_API_KEY> | research-data-signal | free | high |
| USDA National Agricultural Statistics Service — QuickStats API | <https://quickstats.nass.usda.gov/api/api_GET/?key=YOUR_API_KEY&commodity_desc=CORN&year=2023> | research-data-signal | нужен ключ | high |
| World Bank Climate Change Knowledge Portal (CCKP) — Climate Data API | <https://cckpapi.worldbank.org/cckp/v1> | research-data-signal | free | high |
| World Bank What a Waste 3.0 — Global Solid Waste Management Dataset (Country Level) | <https://datacatalogfiles.worldbank.org/ddh-published/0039597/DR0095901/What_a_Waste_3.0_COUNTRY_Dataset_%26_Codebook.xlsx> | research-data-signal | free | high |
| Zenodo Records API | <https://zenodo.org/api/records?q=hypothesis&size=1> | research-data-signal | free | high |
| openFDA — Animal & Veterinary Adverse Event Reports API | <https://api.fda.gov/animalandveterinary/event.json> | research-data-signal | free | high |
| re3data.org API (Registry of Research Data Repositories) | <https://www.re3data.org/api/beta/repositories> | research-data-signal | free | high |
| ACM Transactions on Graphics RSS (SIGGRAPH) | <https://dl.acm.org/action/showFeed?type=etoc&feed=rss&jc=tog> | research-frontier | free | high |
| African Journals Online OAI-PMH (per-journal, example — African Journal of Biotechnology) | <https://www.ajol.info/index.php/ajb/oai?verb=ListRecords&metadataPrefix=oai_dc> | research-frontier | free | high |
| American Psychologist RSS | <https://psycnet.apa.org/journals/amp.rss> | research-frontier | free | high |
| Amstat News — American Statistical Association Membership Magazine RSS | <https://magazine.amstat.org/feed/> | research-frontier | free | high |
| Angewandte Chemie International Edition RSS (Wiley) | <https://onlinelibrary.wiley.com/action/showFeed?type=etoc&feed=rss&jc=15213773> | research-frontier | free | high |
| British Journal of Management RSS (Wiley) | <https://onlinelibrary.wiley.com/action/showFeed?type=etoc&feed=rss&jc=14678551> | research-frontier | free | high |
| Caltech News RSS | <https://www.caltech.edu/about/news/rss> | research-frontier | free | high |
| Canadian Journal of Philosophy RSS (Taylor & Francis) | <https://www.tandfonline.com/action/showFeed?type=etoc&feed=rss&jc=rcjp20> | research-frontier | free | high |
| Cell Reports RSS | <https://www.cell.com/cell-reports/current.rss> | research-frontier | free | high |
| ClinicalTrials.gov API v2 | <https://clinicaltrials.gov/api/v2/studies?pageSize=3> | research-frontier | free | high |
| Computational Economics RSS (Springer) | <https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=10614&channel-name=Computational+Economics> | research-frontier | free | high |
| DOAJ Search API (Directory of Open Access Journals) | <https://doaj.org/api/search/articles/> | research-frontier | free | high |
| Eurostat API — R&D Expenditure (GERD) by Sector of Performance | <https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/rd_e_gerdtot?format=JSON&lang=EN> | research-frontier | free | high |
| Evolutionary Ecology RSS (Springer) | <https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=10682&channel-name=Evolutionary+Ecology> | research-frontier | free | high |
| Frontiers in Psychology RSS | <https://www.frontiersin.org/journals/psychology/rss> | research-frontier | free | high |
| HAL (Hyper Articles en Ligne) — Search API | <https://api.archives-ouvertes.fr/search/?q=*:*&rows=20&wt=json> | research-frontier | free | high |
| Harvard Business Review — RSS | <http://feeds.hbr.org/harvardbusiness> | research-frontier | free | high |
| IOP Publishing — Europhysics Letters RSS | <https://iopscience.iop.org/journal/rss/0295-5075> | research-frontier | free | high |
| IRIS/EarthScope FDSN Station Web Service (метаданные глобальной сейсмической сети) | <https://service.earthscope.org/fdsnws/station/1/query?net=IU&sta=ANMO&format=text&level=station> | research-frontier | free | high |
| JAMA Current Issue RSS | <https://jamanetwork.com/rss/site_3/67.xml> | research-frontier | нужен User-Agent | high |
| Journal of Applied Sport Psychology RSS (Taylor & Francis) | <https://www.tandfonline.com/action/showFeed?type=etoc&feed=rss&jc=uasp20> | research-frontier | free | high |
| Journal of Consumer Research RSS (Oxford University Press) | <https://academic.oup.com/rss/site_5397/3258.xml> | research-frontier | free | high |
| Journal of Political Economy RSS | <https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jpe> | research-frontier | free | high |
| Knowledge at Wharton — RSS | <https://knowledge.wharton.upenn.edu/feed/> | research-frontier | free | high |
| Max Planck Society — Research News RSS | <https://www.mpg.de/en/research.rss> | research-frontier | free | high |
| NASA Technical Reports Server (NTRS) API | <https://ntrs.nasa.gov/api/citations/search?q=climate> | research-frontier | free | high |
| NBER Working Papers RSS | <https://www.nber.org/rss/new.xml> | research-frontier | free | high |
| Natural Hazards RSS (Springer) | <https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=11069&channel-name=Natural+Hazards> | research-frontier | free | high |
| New England Journal of Medicine RSS (Table of Contents) | <https://www.nejm.org/action/showFeed?type=etoc&feed=rss&jc=nejm> | research-frontier | free | high |
| OSF Preprints API — AfricArXiv (Pan-African Research) | <https://api.osf.io/v2/preprints/?filter[provider]=africarxiv&page[size]=3> | research-frontier | free | high |
| OSF Preprints API — BodoArXiv (Business and Economics, Indonesia) | <https://api.osf.io/v2/preprints/?filter[provider]=bodoarxiv&page[size]=3> | research-frontier | free | high |
| OSF Preprints API — FrenXiv (French-language Research) | <https://api.osf.io/v2/preprints/?filter[provider]=frenxiv&page[size]=3> | research-frontier | free | high |
| OSF Registrations API (Preregistered Studies, all disciplines) | <https://api.osf.io/v2/registrations/?page[size]=3> | research-frontier | free | high |
| Personality and Social Psychology Bulletin RSS | <https://journals.sagepub.com/action/showFeed?type=etoc&feed=rss&jc=pssa> | research-frontier | free | high |
| RePEc NEP — Big Data | <https://nep.repec.org/rss/nep-big.rss.xml> | research-frontier | free | high |
| SciELO ArticleMeta API (Scientific Electronic Library Online, Brazil collection) | <https://articlemeta.scielo.org/api/v1/article/identifiers/?collection=scl> | research-frontier | free | high |
| SciPost RSS (открытая community-driven peer review, физика) | <https://scipost.org/rss/publications/> | research-frontier | free | high |
| ScienceDaily RSS (агрегатор научной журналистики) | <https://www.sciencedaily.com/rss/all.xml> | research-frontier | free | medium |
| Smithsonian Global Volcanism Program — GeoServer WFS (реестр вулканов мира, Volcanoes of the World) | <https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=json> | research-frontier | free | high |
| SocArXiv (OSF Preprints — социология) | <https://api.osf.io/v2/preprints/?filter[provider]=socarxiv&page[size]=3> | research-frontier | free | high |
| SpringerLink search RSS | <https://link.springer.com/search.rss?query=hypothesis> | research-frontier | free | medium |
| The Lancet Infectious Diseases RSS | <https://www.thelancet.com/rssfeed/laninf_current.xml> | research-frontier | free | high |
| USGS Earthquake Catalog API (сейсмическая активность) | <https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1> | research-frontier | free | high |
| University of Toronto News RSS | <https://www.utoronto.ca/rss.xml> | research-frontier | free | high |
| War on the Rocks — RSS Feed | <https://warontherocks.com/feed/> | research-frontier | free | high |
| Waves in Random and Complex Media RSS (Taylor & Francis) | <https://www.tandfonline.com/action/showFeed?type=etoc&feed=rss&jc=twrm20> | research-frontier | free | high |
| World Weather Attribution — RSS | <https://www.worldweatherattribution.org/feed/> | research-frontier | free | high |
| Yale Environment 360 (e360) — RSS Feed | <https://e360.yale.edu/feed.xml> | research-frontier | free | high |
| arXiv RSS — astro-ph.CO (Cosmology and Nongalactic Astrophysics) | <https://export.arxiv.org/rss/astro-ph.CO> | research-frontier | free | high |
| arXiv RSS — cond-mat.mtrl-sci (Materials Science) | <https://export.arxiv.org/rss/cond-mat.mtrl-sci> | research-frontier | free | high |
| arXiv RSS — math.NT (Number Theory) | <https://export.arxiv.org/rss/math.NT> | research-frontier | free | high |
| arXiv cs.AI RSS | <http://export.arxiv.org/rss/cs.AI> | research-frontier | free | high |
| Érudit RSS (franco-canadian scholarly journals, Quebec) | <https://www.erudit.org/en/rss.xml> | research-frontier | free | high |
| КиберЛенинка — OAI-PMH репозиторий | <https://cyberleninka.ru/oai?verb=ListRecords&metadataPrefix=oai_dc> | research-frontier | free | high |
