# API sources catalog — INDEX

Каталог API endpoints для прямого programmatic доступа к данным. Дополняет `stat_sources/` (HTML/web) и `channels.md` (search strategies).

## Зачем API когда есть WebFetch?

WebFetch достаёт HTML-страницу, агент её парсит. API возвращает структурированный JSON — это:

- **Структурированный output** — JSON вместо парсинга HTML
- **Bulk queries** — «дай 100 результатов» одним запросом, не 100 страниц
- **Filtering на стороне сервера** — `?industry=fintech&country=US&min_funding=10M`
- **Real-time data** — котировки, on-chain метрики, live feeds
- **Меньше токенов** — JSON компактнее HTML-страницы

## Когда **не** использовать API

- WebFetch HTML уже работает и данных хватает
- Нужен ключ + у тебя его нет → используй HTML вариант источника
- Free tier исчерпан → fallback на HTML или альтернативный источник
- Простой однократный lookup → проще WebSearch

## Структура каталога

```
api_sources/
├── INDEX.md                    ← навигация (этот файл)
├── README.md                   ← auth, free tiers, fallback protocol
├── search/                     ← AI/web search APIs
│   ├── brave_search.md         Brave Search API
│   ├── tavily.md               Tavily (AI-first)
│   ├── exa.md                  Exa.ai (semantic)
│   ├── serpapi.md              SerpAPI (Google/Bing/etc)
│   └── you_com.md              You.com Search API
├── academic/                   ← scholarly research
│   ├── semantic_scholar.md     200M papers, no auth
│   ├── openalex.md             250M works, no auth
│   ├── crossref.md             130M DOIs, no auth
│   └── arxiv.md                preprints, no auth
├── financial/                  ← economic / macro
│   ├── fred.md                 FRED (Fed economic data)
│   ├── world_bank.md           World Bank Indicators
│   ├── sec_edgar.md            SEC EDGAR filings
│   ├── oecd.md                 OECD SDMX
│   └── alpha_vantage.md        Stocks/forex/crypto prices
├── companies/                  ← company data
│   ├── crunchbase.md           Crunchbase Data API (⚠️ платный, цена не публикуется)
│   ├── opencorporates.md       OpenCorporates (⚠️ платный от £2250/год)
│   └── companies_house.md      UK Companies House
├── crypto/                     ← on-chain & markets
│   ├── coingecko.md            CoinGecko Public API
│   ├── defillama.md            DefiLlama (no auth)
│   ├── etherscan.md            Etherscan API
│   └── dune.md                 Dune Analytics
├── code/                       ← code / packages
│   ├── github.md               GitHub Search API
│   ├── stackexchange.md        Stack Exchange API
│   ├── pypi.md                 PyPI JSON API
│   └── npm.md                  npm Registry API
├── social/                     ← community signals
│   ├── reddit.md               Reddit JSON (⚠️ OAuth обязателен с 2026, не free — см. файл)
│   ├── hn_algolia.md           HN Algolia (no auth)
│   └── lemmy.md                Lemmy ActivityPub
├── news/                       ← current events
│   ├── newsapi.md              NewsAPI.org
│   ├── gdelt.md                GDELT 2.0 (no auth)
│   └── currents.md             Currents API
├── stats/                      ← statistics
│   ├── eurostat.md             Eurostat REST API
│   ├── census_us.md            US Census API
│   └── un_data.md              UN Data API
├── patents/                    ← patent offices
│   ├── uspto_odp.md            USPTO Open Data Portal (key + ID.me)
│   ├── epo_ops.md              EPO OPS (OAuth2, 4 GB/week free)
│   ├── epo_lod.md              EPO Linked Open Data (SPARQL, no auth)
│   └── wipo.md                 WIPO — платный, программного free API нет
├── grants/                     ← research funding
│   ├── nsf_awards.md           NSF Awards (no auth)
│   ├── nih_reporter.md         NIH RePORTER v2 (no auth, POST-only)
│   ├── cordis.md               CORDIS EU projects (bulk + SPARQL)
│   └── grants_gov.md           Grants.gov search2 (no auth)
└── domain_specific/            ← specialized
    ├── pubmed.md               PubMed E-utilities
    ├── clinicaltrials.md       ClinicalTrials.gov
    ├── ema.md                  European Medicines Agency
    ├── nasa.md                 NASA APIs
    └── openweather.md          OpenWeather
```

## Quick reference

### Free, no key required (priority sources for agents)

Этим API не нужны ключи — агент может использовать сразу:

| API | What | When |
|---|---|---|
| **Semantic Scholar** | 200M papers, citations | academic search |
| **OpenAlex** | 250M scholarly works (ключ опционален, но рекомендован — 10× бюджет; см. `academic/openalex.md`) | citation graph |
| **CrossRef** | 130M DOIs | DOI metadata |
| **arXiv** | preprints | physics/CS/math papers |
| **DefiLlama** | DeFi TVL/protocols | crypto research |
| **CoinGecko** | crypto prices/markets | crypto data (rate-limited) |
| **HN Algolia** | Hacker News search | tech discussions |
| **World Bank** | global development | macro stats |
| **SEC EDGAR** | US public filings | company financials |
| **ClinicalTrials.gov** | trial registry | medical research |
| **PubMed E-utilities** | biomedical literature | medical search |
| **GDELT** | global events | news/sentiment |
| **PyPI / npm** | package metadata | tech stack research |
| **NSF Awards** | US research grants с 1969 | кто финансирует тему, суммы |
| **NIH RePORTER** | биомед-гранты NIH с FY1985 | финансирование медицинских тем |
| **Grants.gov** | открытые конкурсы US federal | будущие возможности, не выданное |
| **EPO Linked Open Data** | патентные публикации, SPARQL | патентная активность без ключа |

### Free with key (one-time setup, then automatic)

| API | Free tier | Setup |
|---|---|---|
| **FRED** | unlimited | https://fred.stlouisfed.org/docs/api/api_key.html |
| **USPTO ODP** | 5M calls/week metadata, 1.2M documents | https://developer.uspto.gov (нужен ID.me-верифицированный аккаунт) |
| **EPO OPS** | 4 GB/week, ~1 Мбит/сек | https://developers.epo.org (OAuth2 client_credentials) |
| **GitHub** | 5000 req/h authenticated | https://github.com/settings/tokens |
| **Stack Exchange** | 10000 req/day | https://stackapps.com/apps/oauth/register |
| **NewsAPI** | 100 req/day | https://newsapi.org/register |
| **Alpha Vantage** | 25 req/day | https://www.alphavantage.co/support/#api-key |
| **Etherscan** | 5 req/sec | https://etherscan.io/myapikey |
| **Reddit JSON (OAuth)** | не подтверждено на 2026-08-17 — анонимный `.json` закрыт (403, live-проверено ~05.2026); выдача новых OAuth script-приложений сузилась, реальный лимит для personal use не подтверждён | https://www.reddit.com/prefs/apps → `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, см. `social/reddit.md` |

### Paid (powerful but cost money)

| API | Cost | Why pay |
|---|---|---|
| **Brave Search** | $3/1k queries | Google-quality, no bias toward Google products |
| **Tavily** | $0/1k free, then paid | Built for AI agents, returns answers |
| **Exa.ai** | $5/1k searches | Semantic search, neural |
| **SerpAPI** | $50/mo | Google/Bing/DuckDuckGo unified |
| **Crunchbase** | цена не публикуется, custom/contact-sales (старая цифра "$99/mo" не подтвердилась на 2026-08-17, см. `companies/crunchbase.md`) | Company data, funding rounds |
| **OpenCorporates** | от £2250/год (Essentials); free-доступ по заявке для journalists/NGO/anti-corruption groups | Company registry data, 130+ countries |
| **WIPO** | 600–2000 CHF/год SOAP, 400–19500 CHF/год bulk | программного бесплатного доступа нет вообще; веб-UI отдаёт CAPTCHA |

**Мёртвое, не тратить время:** `search.patentsview.org` — сервис закрылся 20.03.2026, домен не резолвится; данные ушли в USPTO ODP bulk. Подробности — `patents/uspto_odp.md`, раздел Fallback.

## How to navigate this catalog

1. **Identify your need:** what kind of data — papers, prices, filings, social signals?
2. **Pick category folder** (search/academic/financial/...)
3. **Read the relevant API file** — each has full reference: endpoint, auth, free tier, query examples
4. **Use the example queries** as templates in your research
5. **Document API call** in your `sources/NN.md` frontmatter (`channel: api-direct`, `access: api-free-no-key`)

## See also

- `channels.md` → channel **`api-direct`** — стратегия использования APIs в workflow
- `stat_sources/` → HTML/web версия тех же источников (для fallback когда API не работает)
- `subagents_v2.md` → как давать суб-агентам инструкции по API queries
