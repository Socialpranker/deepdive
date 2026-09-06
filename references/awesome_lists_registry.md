# Awesome Lists Registry — upstream discovery

Каталог upstream awesome-lists на GitHub, к которым агент обращается когда в моём каталоге нет purpose-fit источника для конкретной подтемы.

## Зачем это нужно

Мой каталог (`api_sources/` + `stat_sources/`) — это curated subset. Awesome-lists содержат **тысячи** APIs и datasets — невозможно curate всё. Этот registry — навигационный layer:

```
Не нашёл в моём каталоге → проверь registry → найди upstream awesome-list →
  WebFetch их README/категории → identify 1-3 candidates → use ad-hoc
```

Это превращает скилл из **closed catalog** в **discovery hub**.

## Tier 1 — Universal APIs/Datasets

Использовать в первую очередь когда не уверен где искать.

### public-apis/public-apis
**URL:** https://github.com/public-apis/public-apis
**What:** 1500+ free public APIs in 48 categories
**Stars:** 418k+ (самый известный API list)
**Categories:** Animals, Anime, Art & Design, Authentication, Books, Business, Calendar, Cloud Storage & File Sharing, Continuous Integration, Currency Exchange, Data Validation, Development, Dictionaries, Documents & Productivity, Email, Entertainment, Environment, Events, Finance, Food & Drink, Games & Comics, Geocoding, Government, Health, Jobs, Machine Learning, Music, News, Open Data, Open Source Projects, Patent, Personality, Phone, Photography, Programming, Science & Math, Security, Shopping, Social, Sports & Fitness, Test Data, Text Analysis, Tracking, Transportation, URL Shorteners, Vehicle, Video, Weather
**When to fetch:** любая ниша где не знаешь existing APIs
**How:** WebFetch README.md или specific category section

### awesomedata/awesome-public-datasets
**URL:** https://github.com/awesomedata/awesome-public-datasets
**What:** Curated open datasets across 38 topics
**Stars:** 65k+
**Categories:** Agriculture, Architecture, Biology, Chemistry, Climate+Weather, ComplexNetworks, ComputerNetworks, CyberSecurity, DataChallenges, EarthScience, Economics, Education, Energy, Entertainment, Finance, GIS, Government, Healthcare, ImageProcessing, MachineLearning, Museums, NaturalLanguage, Neuroscience, Physics, ProstateCancer, Psychology+Cognition, PublicDomains, SearchEngines, SocialNetworks, SocialSciences, Software, Sports, TimeSeries, Transportation, eSports
**When to fetch:** нужны raw datasets для own analysis, а не API queries
**How:** WebFetch README.md или specific topic

### jnv/lists — list of lists
**URL:** https://github.com/jnv/lists
**What:** Meta-list — список curated lists на GitHub
**Stars:** 25k+
**When to fetch:** когда не знаешь даже какой awesome-list искать
**How:** WebFetch README.md и поиск ключевых слов

## Tier 2 — Specialized

Узкоспециализированные lists для конкретных доменов.

### Government / Open Data

- **inveniosoftware/awesome-research-data-management** — research data infrastructure
- **r-spatial/awesome-spatial** — geospatial data
- **scienceopen/open-data** — academic open data
- **eligrey/list-of-lists** — datasets meta-list

### Finance / Economics

- **wilsonfreitas/awesome-quant** — quant finance libraries + data
- **dvgodoy/finance-economics-resources** — open finance APIs
- **economagic/data-sources** — economic data

### Science / Academia

- **shaily99/awesome-research** — academic resources
- **openMINDS-projects** — neuroscience-specific
- **inveniosoftware/awesome-research-data-management** — research data tools

### Crypto / Web3

- **bcoin-org/awesome-bitcoin** — Bitcoin specifically
- **crypti/awesome-crypto-papers** — crypto research papers
- **OffcierCia/Crypto-OpSec-SelfGuard-RoadMap** — security focus

### Health / Medical

- **kakoni/awesome-healthcare** — healthcare data and APIs
- **vinta/awesome-python** → Medical section
- **datacarpentry/biology-lesson-collections** — biology

### Tech / Developer

- **sindresorhus/awesome** — meta awesome-of-awesome
- **avelino/awesome-go** — Go ecosystem
- **vinta/awesome-python** — Python ecosystem
- **enaqx/awesome-react** — React ecosystem

### MCP / Agent infrastructure

- **appcypher/awesome-mcp-servers** — MCP servers catalog
- **wong2/awesome-mcp-servers** — alternative MCP list
- **abordage/awesome-mcp** — daily-updated MCP list
- **win4r/Awesome-Claude-MCP-Servers** — Claude-optimized MCP

### Claude ecosystem

- **travisvn/awesome-claude-skills** — Claude Skills (для распространения нашего скилла!)
- **JSONbored/awesome-claude** — Claude registry
- **ComposioHQ/awesome-claude-plugins** — Claude Code plugins
- **rohitg00/awesome-claude-code-toolkit** — toolkit overview

## Tier 3 — Niche / Domain-specific

Узкие но качественные.

### Geospatial / Maps

- **sacridini/Awesome-Geospatial** — GIS tools
- **rspatial/awesome-spatial** — spatial analysis

### NLP / Linguistic

- **keon/awesome-nlp** — NLP datasets and tools
- **brianspiering/awesome-dl4nlp** — deep learning NLP

### Machine Learning

- **josephmisiti/awesome-machine-learning** — ML resources
- **EthicalML/awesome-production-machine-learning** — ML in production

### Cybersecurity

- **sbilly/awesome-security** — security resources
- **paragonie/awesome-appsec** — application security

### Climate

- **protontypes/open-sustainable-technology** — climate tech
- **mwouts/awesome-jupyter** → climate science section

## Tier 4 — Niche aggregators

Lists которые сами aggregate другие lists.

### sindresorhus/awesome
**URL:** https://github.com/sindresorhus/awesome
**What:** Корень всех awesome-lists. Master index.
**Stars:** 350k+
**When to fetch:** когда нужно найти любую категорию awesome-list, не уверен какая существует
**How:** WebFetch README.md, поиск ключевых слов

### awesomelistsio/awesome-apis
**URL:** https://github.com/awesomelistsio/awesome-apis
**What:** Curated list of high-quality APIs, SDKs, dev tools
**When:** для broad search across multiple domains

### whizkydee/Awesome-APIs
**URL:** https://github.com/whizkydee/Awesome-APIs
**What:** Curated APIs round the web
**When:** alternative взгляд на public-apis (less broad)

## Discovery workflow для агента

```
если в моём каталоге (api_sources/ + stat_sources/) нет нужной категории:

  1. Определи domain (finance / health / science / crypto / etc.)
  2. Найди в этом registry соответствующий Tier 1-3 awesome-list
  3. WebFetch его README.md
  4. Поиск keywords из подтемы
  5. Извлеки 2-3 candidate APIs/sources
  6. Для каждого: проверить URL живой (HEAD request)
  7. Для тех что живые: добавить в plan.md как ad-hoc:
     - URL
     - tier (open / partial / paywall если ясно)
     - source upstream awesome-list (для credit)
     - note: ad-hoc, not in main catalog yet

  Если кандидат окажется ценным после использования →
     Suggest contributor добавить через PR в правильную категорию api_sources/ или stat_sources/
```

## Limitations awesome-lists

- **Stale data:** многие entries deprecated, не работают. Always validate URL перед использованием.
- **No standardization:** каждый list со своим форматом — нужно парсить individually.
- **Quality varies:** в `public-apis` есть и top-tier и хобби APIs.
- **Discovery cost:** WebFetch + parsing + validation = время. Use только когда мой каталог не покрыл.

## Future contributions

Когда контрибьютор находит ценный источник в upstream awesome-list, в его PR должно быть:

```markdown
## Source discovered in upstream

- Original found in: [public-apis/Business](https://github.com/public-apis/public-apis#business)
- Added to my catalog as: api_sources/companies/example.md
- Reason: stable, free tier, fits gap in my coverage
```

Это даёт **credit** original awesome-list maintainer + поощряет ecosystem growth.

## Notes на специфический case — Claude ecosystem

Lists в категории "Claude ecosystem" критичны для **распространения этого скилла**:

- Submit deepdive в [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) после первого release
- Submit в [JSONbored/awesome-claude](https://github.com/JSONbored/awesome-claude)
- Submit в [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit)

См. PUBLISH.md → Step 6: "Submit to awesome lists" для процедуры.
