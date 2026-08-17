# Private companies & startups

Источники для приватных компаний, стартапов, funding data. У приватных нет SEC filings — приходится работать с indirect signals + специализированными vendors.

## Tier 1 — Full entries

### Crunchbase

**URL:** https://www.crunchbase.com/
**Type:** Vendor
**Access:** PARTIAL (profile basics free, deep data paywalled)

**What's inside:**
- Company profiles (founders, founded date, location, brief)
- Funding rounds (date, amount, lead investor, valuation if disclosed)
- Acquisitions
- People profiles (founders, executives)
- Investor profiles

**When to use:**
- Profile-card block для startup landscape
- Funding history claims
- Investor portfolio analysis
- Acquisition history

**How to use:**
- Company URL: `crunchbase.com/organization/<slug>`
- Investor URL: `crunchbase.com/organization/<vc-slug>/recent_investments`
- Search pattern: `<company> crunchbase`
- Partial data visible without account

**Data quality:**
- Credibility: B (vendor, depends on submissions)
- Coverage bias toward English-speaking, recent
- Funding amounts often estimated

**Limitations:**
- Many fields paywalled
- Self-reported by companies (over-claim possible)
- Older data may be stale
- Misses non-VC-funded businesses

**Combine with:**
- LinkedIn (company size, hiring)
- TechCrunch (funding announcements with detail)
- Company website (verify claims)

**Fallback if blocked:**
- TechCrunch / VentureBeat для funding announcements
- AngelList для startup basic info
- SEC EDGAR S-1 если pre-IPO

---

### Wellfound (AngelList Talent)

**URL:** https://wellfound.com/ (formerly AngelList)
**Type:** Vendor
**Access:** PARTIAL — homepage и `/jobs` листинг отдают HTTP 200 (маркетинговый шелл), но `/company/<slug>` возвращает HTTP 403 "Security Check" (Cloudflare bot-challenge, заголовок `cf-mitigated: challenge`). На `/jobs` реальные вакансии подгружаются клиентским GraphQL-запросом за тем же Cloudflare Turnstile — в исходном HTML `apolloState` пуст, без прохождения JS-челленджа данных нет.

**What's inside:**
- Startup company pages (mostly tech)
- Job postings (hiring signal!)
- Founders/team
- Some funding info

**When to use:**
- Startup tech landscape
- Hiring signal (what skills companies need)
- Early-stage startup discovery

**How to use:**
- Company: `wellfound.com/company/<slug>`
- Jobs: `wellfound.com/jobs`
- Search pattern: `<company> angellist OR wellfound`

**Data quality:**
- Credibility: B
- Tech-startup focus

**Limitations:**
- Основные данные (company pages, реальный список вакансий) закрыты Cloudflare bot-challenge — программный доступ без прохождения JS-челленджа получает только маркетинговый шелл или 403
- Официального публичного API нет; в вебе есть только неофициальные scraper-сервисы (Apify и т.п.), их ToS-статус и надёжность не проверялись
- Даже при ручном браузерном доступе покрытие смещено в tech-стартапы

**Combine with:**
- LinkedIn для broader hiring
- Crunchbase для funding

**Fallback if blocked:**
- Y Combinator's own job board `workatastartup.com/jobs` — проверено живым запросом 2026-08-17, HTTP 200, реальные листинги вакансий (без челленджа). Покрывает только YC-портфель (уже, чем весь Wellfound), но closes тот же use case — hiring signal для early-stage стартапов
- Для funding/company basics — Crunchbase (см. выше) или SEC EDGAR при pre-IPO

**Verified:** 2026-08-17

---

### Latka SaaS Database

**URL:** https://getlatka.com/saas-companies
**Type:** Vendor (founded by Nathan Latka)
**Access:** OPEN (self-reported)

**What's inside:**
- 4000+ SaaS companies with self-reported MRR, ARR, churn, CAC
- Founder interviews (long-form)
- Growth journey data

**When to use:**
- SaaS benchmark research
- Specific SaaS company revenue (if self-reported)
- Unit economics comparison

**How to use:**
- Browse `getlatka.com/saas-companies`
- Founder interviews on Latka's site
- Search pattern: `<company> latka saas`

**Data quality:**
- Credibility: C (self-reported, no verification)
- BUT: useful as starting point + reality check

**Limitations:**
- Only companies that opted in
- Self-reported numbers могут быть inflated
- Cross-check critical claims

---

### Indie Hackers

**URL:** https://www.indiehackers.com/products
**Type:** Community
**Access:** OPEN

**What's inside:**
- Indie founder products + self-reported revenue
- Founder interviews and milestones
- Community Q&A

**When to use:**
- Indie/small business landscape
- Bootstrap success stories
- Niche tools landscape

**How to use:**
- Product pages: `indiehackers.com/product/<slug>`
- Interviews: `indiehackers.com/interviews`

**Data quality:**
- Credibility: C (self-reported but transparent)
- Authenticity: high (small community, founders honest)

---

## Tier 2 — Brief entries

### PitchBook
**URL:** pitchbook.com — **PAYWALL** (но summaries в press releases часто). Workaround: search `<topic> pitchbook` для articles citing.

### CB Insights Research
**URL:** cbinsights.com/research — **PARTIAL** (research reports free, full data paywall). Annual State of Venture report — OPEN.

### Tracxn
**URL:** tracxn.com — **PARTIAL** (basic profiles free). Sector taxonomies.

### Y Combinator Companies
**URL:** ycombinator.com/companies — **OPEN**. YC portfolio с funding, status. `<YC batch>` filter available.

### Sifted (European startups)
**URL:** sifted.eu — **OPEN** articles. European startup ecosystem coverage.

### TechCrunch (funding announcements)
**URL:** techcrunch.com/category/startups — **OPEN**. Major funding rounds announced here first. Search: `<company> techcrunch funding`.

### Failory (failed startups)
**URL:** failory.com/failed-startups — **OPEN**. Database of startup failures with reasons. Useful для pre-mortem block.

### StartupBlink
**URL:** startupblink.com — **OPEN**. Global startup ecosystem rankings by city/country.

---

## Local / Regional registries (для приватных)

Большое преимущество — многие страны требуют от частных компаний публикации отчётности.

### EU registries
- **UK Companies House** (см. companies_public.md) — uniquely requires private filings — OPEN
- **Germany Bundesanzeiger** (см. companies_public.md) — OPEN
- **France BODACC** — `bodacc.fr` — OPEN, business announcements
- **Italy Registro Imprese** — `registroimprese.it` — PARTIAL
- **Spain Registro Mercantil** — `rmc.es` — PARTIAL

### Russia / CIS
- **EGRUL** — `egrul.nalog.ru` — OPEN, basic registry
- **СПАРК-Интерфакс** — `spark-interfax.ru` — PARTIAL (deep data paywall)
- **Контур.Фокус** — `focus.kontur.ru` — PARTIAL
- **Rusprofile** — `rusprofile.ru` — OPEN partial

### Asia
- **Japan Corporate Number** — `houjin-bangou.nta.go.jp` — OPEN
- **Singapore ACRA** — `acra.gov.sg/data-services` — OPEN
- **India MCA21** — `mca.gov.in` — PARTIAL
- **HK Companies Registry** — `cr.gov.hk` — PARTIAL

### Americas
- **Brazil Receita Federal** (CNPJ) — `solucoes.receita.fazenda.gov.br` — OPEN basic
- **Mexico** — varies by state

---

## VC funds and investors

### Y Combinator Top Companies
**URL:** `ycombinator.com/topcompanies` — OPEN. Top YC alumni companies.

### National Venture Capital Association
**URL:** `nvca.org/research` — OPEN annual reports.

### Invest Europe (EU VC)
**URL:** `investeurope.eu` — OPEN reports.

### Pitchbook NVCA Venture Monitor (US quarterly VC report)
**URL:** Search `<quarter> NVCA Venture Monitor` — OPEN PDF released quarterly.

---

## Self-reported revenue / SaaS databases

### Microconf
**URL:** microconf.com/state-of-independent-saas — annual state of independent SaaS — OPEN

### OpenView SaaS Benchmarks
**URL:** openviewpartners.com/blog — OPEN. Annual SaaS benchmarks report.

### Bessemer State of the Cloud
**URL:** bvp.com/insights/state-of-the-cloud-<year> — OPEN annual.

---

## Quick reference

| Что ищем | Источник |
|---|---|
| Startup funding history | Crunchbase + TechCrunch |
| UK private company financials | Companies House |
| EU private company financials | National registry |
| SaaS self-reported numbers | Latka + Indie Hackers + OpenView benchmarks |
| Hiring signal | LinkedIn + Wellfound |
| Failed startups причины | Failory |
| YC portfolio | YC companies page |
| EU startup ecosystem | Sifted + Invest Europe |
| Global startup ecosystem ranking | StartupBlink |
| Specific founder | LinkedIn + Crunchbase person + Latka/Indie Hackers interview |

## Combining patterns

**Startup due diligence (no SEC equivalent):**
Crunchbase (funding) + LinkedIn (hiring/team) + TechCrunch (announcements) + national registry (если EU) + founder interviews (Latka/IndieHackers if SaaS)

**Startup landscape:**
Crunchbase + CB Insights research + Sifted (если EU) + StartupBlink (ecosystem) + Failory (death rate context)

**SaaS benchmarks:**
OpenView + Bessemer State of the Cloud + Latka self-reports + Microconf

## Что НЕЛЬЗЯ найти про приватные

Признавай ограничения честно:
- Точная revenue для большинства приватных (только estimates)
- Profit margins (не публикуются)
- Customer concentration
- Internal financials (cost structure)
- Real cap table (если не leaked)

Для этих — `access: closed` в sources, признать в `gaps`.
