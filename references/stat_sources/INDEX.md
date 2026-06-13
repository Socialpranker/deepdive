# Stat sources catalog — INDEX

База знаний по статистическим и информационным источникам для deep-research. Прогрессивная подгрузка — загружай только нужные файлы.

## Как пользоваться

1. Прочитай этот INDEX (всегда первым).
2. Определи нужные категории — `core/*` или `industries/*`.
3. Загружай только нужные файлы — не весь каталог.
4. В `plan.md` Information sourcing strategy указывай конкретные источники.

## Структура

```
stat_sources/
├── INDEX.md                  ← ты здесь
├── README.md                 ← как добавлять/обновлять источники
├── core/                     ← cross-industry источники
│   ├── gov_macro.md          government statistics, macro, sentiment, trade, tax
│   ├── companies_public.md   SEC filings, public company data
│   ├── companies_private.md  Crunchbase, startups, local registries
│   ├── consulting_industry.md McKinsey, BCG, Gartner, trade associations
│   ├── consumer_digital.md   apps, web/SaaS, social/creator
│   ├── crypto.md             on-chain, DeFi, crypto markets
│   ├── data_aggregators.md   open data portals
│   ├── media_entertainment.md gaming, film, music
│   ├── health.md             medical, pharma data, public health
│   ├── education.md          schools, rankings, edutech
│   ├── climate_env.md        climate, emissions, env data
│   ├── science.md            citation databases, retractions
│   ├── transport_travel.md   flights, ships, tourism
│   └── sports_fitness.md     sports stats, fitness, esports
└── industries/               ← industry-specific deep dives
    ├── energy.md             EIA, IEA, OPEC, BP
    ├── auto.md               OICA, ACEA, EV sales
    ├── pharma.md             FDA, EMA, clinical trials
    ├── retail.md             NRF, Marketplace Pulse, e-commerce
    ├── manufacturing.md      ISM, NAM, UNIDO
    ├── real_estate.md        CBRE, Zillow, MSCI
    ├── insurance.md          NAIC, EIOPA, Swiss Re Sigma
    ├── banking.md            FDIC, ECB, BIS
    ├── telecom.md            ITU, GSMA, Cloudflare Radar
    ├── logistics.md          WTO Trade, Drewry, FreightWaves
    ├── agriculture.md        FAOSTAT, USDA
    ├── defense.md            SIPRI, Janes
    ├── it_services.md        NASSCOM, ISG, outsourcing
    ├── cybersecurity.md      Verizon DBIR, ENISA, CISA
    ├── advertising.md        IAB, eMarketer, ad spend
    ├── hr_workforce.md       LinkedIn Workforce, BLS, Indeed Hiring Lab
    ├── gig_economy.md        platform work, Online Labour Index
    ├── esg_sustainability.md CDP, SBTi, Climate TRACE
    └── infrastructure.md     public infra, OECD
```

## Когда какой файл читать

### Если ресёрч про macro / strana / GDP / inflation
→ `core/gov_macro.md`

### Если ресёрч про конкретную public company
→ `core/companies_public.md` (SEC filings, financials)

### Если ресёрч про startup / privately held
→ `core/companies_private.md` (Crunchbase, registries)

### Если ресёрч про industry-wide trends, market size
→ `core/consulting_industry.md` + соответствующий `industries/<industry>.md`

### Если ресёрч про apps / SaaS / digital products
→ `core/consumer_digital.md`

### Если ресёрч про конкретную индустрию
→ `industries/<industry>.md` (точечно)

### Если ресёрч про крипто/web3
→ `core/crypto.md`

### Если ресёрч про здоровье/медицину
→ `core/health.md` + (если pharma) `industries/pharma.md`

### Если ресёрч про образование
→ `core/education.md`

### Если ресёрч про климат/окружающую среду
→ `core/climate_env.md` + (если sustainability) `industries/esg_sustainability.md`

### Если ресёрч про науку / citations / replication
→ `core/science.md`

### Если ресёрч про транспорт / путешествия
→ `core/transport_travel.md` + (если logistics) `industries/logistics.md`

### Если ресёрч про спорт / фитнес
→ `core/sports_fitness.md`

### Если ресёрч про медиа (фильмы, музыка, gaming)
→ `core/media_entertainment.md`

### Если ищем raw datasets для analysis
→ `core/data_aggregators.md`

## Template записи источника

Каждая запись следует этой структуре:

```markdown
### <Source Name>

**URL:** <main URL>
**Type:** Government | Intergovernmental | Industry Body | Consulting | Vendor | Community | Academic | Self-reported
**Access:** OPEN | PARTIAL (preview free) | PAYWALL with summary | PAYWALL closed

**What's inside:**
- <bullet>

**When to use:**
- Use case 1
- Use case 2

**How to use:**
- Direct: <how to navigate>
- Search pattern: `<query template>`
- Download: <if bulk available>
- API: <if has API>

**Data quality:**
- Credibility: A | B | C
- Freshness: real-time | weekly | monthly | quarterly | annual | irregular
- Lag: <typical delay>
- Methodology: <link or note>

**Limitations:**
- <weakness>
- <bias>

**Combine with:**
- <related complementary sources>

**Fallback if blocked:**
- <alternative>
```

## Statistics

- Categories in core: 14
- Industries: 19
- Total source entries: <!--gen:count:stat_sources-->461<!--/gen-->+
- Sources distribution by access:
  - OPEN: ~190 (68%)
  - PARTIAL: ~70 (25%)
  - PAYWALL with summary: ~20 (7%)

## Когда добавлять новый источник в каталог

Не каждое использование требует добавления. Добавляй только если:
- Источник будет реально полезен в ≥2 будущих ресёрчах
- Покрывает gap в текущем каталоге
- Имеет известный URL и data quality assessment

Если используешь one-off источник для текущего ресёрча — записывай в `sources/NN.md` ресёрча, не в каталог.
