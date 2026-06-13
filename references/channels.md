# Search channels — каталог <!--gen:count:channels-->29<!--/gen--> каналов поиска

Каналы — это **именованные search strategies** под разные типы источников. Каждый канал имеет известные query patterns, ожидаемый формат результатов, и known limitations.

## Как использовать

1. После Фазы 2 (genre & block selection) — определи какие каналы релевантны для каждой подтемы.
2. В `plan.md` секция Information sourcing strategy указывает каналы per subtopic.
3. В промпт суб-агента передаётся `channels: [список]` — агент знает где искать.
4. В `sources/NN.md` фиксируется `channel:` поле — какой канал дал источник.

## Каталог <!--gen:count:channels-->29<!--/gen--> каналов

### Часть A — Web и discovery

#### 1. `web-general`
**Что:** Широкий WebSearch без specific сайтов.
**Query pattern:** `<topic> <keyword>` — broad.
**Возвращает:** mainstream media, blogs, general references.
**Когда:** первый round для понимания темы, common knowledge.
**Limitations:** SEO-перекошено, recent dominate, мало academic.
**По жанрам:** baseline везде.

#### 2. `wikipedia-references`
**Что:** Wikipedia как **навигационный hub** к первичным источникам.
**Query patterns:**
- `site:en.wikipedia.org <topic>` (английская)
- `site:ru.wikipedia.org <topic>` (русская)
- Find specific articles, then follow References/Bibliography
**Возвращает:** ссылки на primary sources через bibliography.
**Когда:** в начале любого ресёрча для quick framing.
**Quality:** Wikipedia сама C-grade. Use only for navigation, never as citation.

#### 3. `archive-historical`
**Что:** archive.org Wayback Machine, archive.today для paywalled/deleted.
**Query patterns:**
- `https://web.archive.org/web/*/<url>` — для конкретного URL
- `archive.today/<url>` — newer mirror
**Возвращает:** старые версии страниц, removed content, paywalled через cached.
**Когда:** fallback когда live source блокирован; проверка изменений со временем.
**Limitations:** не всё в архиве; recent dynamic content часто отсутствует.

---

### Часть B — Academic / Scholarly

#### 4. `academic`
**Что:** Поиск в academic sources.
**Query patterns:**
- `site:scholar.google.com <topic>` — broad scholarly
- `site:semanticscholar.org <topic>` — AI-powered
- `site:ncbi.nlm.nih.gov <topic>` (PubMed)
- `<topic> "meta-analysis"`
- `<topic> "systematic review"`
- `<topic> filetype:pdf` (preprints, white papers)

**Paywall fallback sequence:**
1. Try `preprint-servers` channel
2. `"<paper title>" researchgate OR academia.edu`
3. `"<paper title>" filetype:pdf` — institutional copy
4. `site:edu "<paper title>"` — university hosting
5. Unpaywall search
6. Last resort (user-elected, with legal acknowledgement): Sci-Hub mirror — пометить `access: gray-area-source` в frontmatter источника
7. Если ничего — fetch abstract, отметить `access: paywalled-abstract-only`

**Когда:** validation научных claims, deep explainer, любой scientific topic.

#### 5. `preprint-servers`
**Что:** Legal open access scholarly preprints — **первый стоп для recent academic**.
**Query patterns:**
- `site:arxiv.org <topic>` — CS, physics, math
- `site:biorxiv.org <topic>` — biology
- `site:medrxiv.org <topic>` — medicine
- `site:ssrn.com <topic>` — economics, social science, law
- `site:osf.io/preprints <topic>` — general
- `site:psyarxiv.com <topic>` — psychology
- `site:chemrxiv.org <topic>` — chemistry
- `site:engrxiv.org <topic>` — engineering

**Возвращает:** open access scholarly papers full text.
**Когда:** validation, любой recent scientific claim.
**Advantage:** free, legal, full text. Often preprint = final version.
**Limitations:** некоторые preprints not peer-reviewed eventually; check «later published».

#### 6. `conference-proceedings`
**Что:** Conference papers from major academic venues.
**Query patterns:**
- `site:acm.org <topic>`
- `site:ieee.org <topic>`
- `<topic> "ICML"` / `"NeurIPS"` / `"USENIX"` / `"VLDB"` / `"SIGGRAPH"` etc.
- `<topic> conference proceedings filetype:pdf`
- `<topic> "workshop"`

**Возвращает:** cutting-edge research, peer-reviewed conference papers.
**Когда:** academic-deep validation, tech research где конференции главные.
**Limitations:** часто paywalled — fallback на preprint-servers.

---

### Часть C — Code

#### 7. `code-github`
**Что:** Public GitHub repositories.
**Query patterns:**
- `site:github.com <topic>`
- `site:github.com <topic> stars:>1000` — only popular
- `<topic> issue site:github.com`
- `<topic> "lessons learned" site:github.com`
- `<topic> ADR site:github.com` — architecture decision records
- `<topic> filetype:md site:github.com` — READMEs/docs

**Возвращает:** real implementations, READMEs, issue discussions, ADRs.
**Когда:** tech explainer, decision (как X решается на практике), validation tech claims.
**Limitations:** только public; код требует understanding.

#### 8. `code-other`
**Что:** GitLab, Bitbucket, sourcehut, прочие code hosts.
**Query patterns:**
- `site:gitlab.com <topic>`
- `site:bitbucket.org <topic>`
- `site:sr.ht <topic>`

**Когда:** проекты которые сознательно не на GitHub (некоторые EU/government/privacy-focused).

---

### Часть D — Community / Discussion

#### 9. `forum-discussion`
**Что:** Targeted поиск в discussion-сайтах.
**Query patterns:**
- `site:reddit.com <topic>` (или subreddit-specific: `site:reddit.com/r/<sub>`)
- `site:news.ycombinator.com <topic>`
- `site:stackexchange.com <topic>` / `site:stackoverflow.com`
- `site:lobste.rs <topic>`
- `<topic> "my experience" reddit`
- `<topic> "regret" reddit` — для validation/decision

**Возвращает:** real-user experiences, anecdotes, community sentiment, contrarian voices.
**Когда:** validation («работает ли X на практике»), landscape (community signals), decision (regret stories).
**Quality:** anecdotal — C по нашей шкале. Use для signal, not proof. Хорош для opposition voice.

#### 10. `social-twitter`
**Что:** Twitter/X public posts.
**Query patterns:**
- `site:twitter.com <topic>` / `site:x.com <topic>`
- `<person> twitter <topic>`
- `<topic> "viral"` recent
- `<topic> "controversial"`

**Возвращает:** real-time discourse, hot takes.
**Когда:** landscape (current discourse), validation contrarian voices.
**Limitations:** WebSearch плохо индексирует Twitter с 2023+ (API closure); часто только cached/embedded. Weak signal source.

---

### Часть E — News and Industry

#### 11. `news-current`
**Что:** News sources + date filters.
**Query patterns:**
- `<topic>` + filter «last year/month»
- `site:reuters.com <topic>`
- `site:bloomberg.com <topic>`
- `site:techcrunch.com <topic>` (tech)
- `site:ft.com <topic>` (financial)
- `<topic> "announced"` recent

**Возвращает:** current events, announcements, recent changes.
**Когда:** landscape current state, trends, recent context.
**Limitations:** sensationalism, churn, устаревает.

#### 12. `industry-reports`
**Что:** Consulting firms, analyst houses.
**Query patterns:**
- `site:mckinsey.com <topic>`
- `site:bcg.com <topic>`
- `site:bain.com <topic>`
- `site:gartner.com <topic>` (часто paywalled — ищи press releases)
- `site:cbinsights.com <topic>`
- `<topic> "market size" <year>`
- `<topic> "industry report" filetype:pdf`

**Возвращает:** market sizing, trend analyses, expert commentary.
**Когда:** landscape, market sizing, decision context.
**Limitations:** конфликт интересов (selling services), часто paywalled — ищи summaries.
**See also:** stat_sources/core/consulting_industry.md

---

### Часть F — Multimedia

#### 13. `video-talks`
**Что:** Conference talks и видео-лекции.
**Query patterns:**
- `<topic> transcript`
- `<topic> conference talk PDF` (slides доступны чаще transcript)
- `<speaker> talk <topic>`
- `<conference> <year> <topic>` (e.g., AWS re:Invent, RustConf)
- `site:youtube.com <topic>` — найти видео, потом искать transcript

**Возвращает:** conference talks (slides+transcripts), interviews, lectures.
**Когда:** explainer deep, expert opinion, cutting-edge topics без формальной литературы.
**Limitations:** transcripts inconsistent. Найди summary blog by speaker как proxy.

#### 14. `podcasts`
**Что:** Podcast episodes with notes/transcripts.
**Query patterns:**
- `<topic> "show notes"`
- `<topic> transcript podcast`
- `<topic> podcast site:lexfridman.com` (или другие топ-podcasts)
- `<topic> "deep dive" podcast`

**Возвращает:** глубокие интервью, длинные дискуссии.
**Когда:** expert-opinion, deep explainer, thought leader landscape.
**Limitations:** transcripts uneven; time investment большой.

---

### Часть G — People

#### 15. `expert-individual`
**Что:** Конкретные эксперты, авторы, founders.
**Query patterns:**
- `"<Person Name>" <topic>` — что говорил
- `<Person> blog`
- `<Person> interview <topic>`
- `<Person> "I think"` / `<Person> "predict"`
- `site:linkedin.com/in/<person>` — bio

**Возвращает:** мнения экспертов, их blogs, интервью.
**Когда:** validation (expert opinion), landscape (key people), understanding конкретных школ мысли.
**Limitations:** один голос — нужна триангуляция. Conflict of interest всегда возможен.

#### 16. `books-literature`
**Что:** Books, длинные тексты, summaries.
**Query patterns:**
- `site:books.google.com <topic>` — preview
- `site:openlibrary.org <topic>`
- `<book title> "table of contents"`
- `<book title> "summary"`
- `<topic> "in his book"`

**Возвращает:** ссылки на книги, fragments через preview, summaries.
**Когда:** explainer глубокие, historical-context, expert-individual (книги автора).
**Limitations:** full text часто недоступен; preview ограниченный.

---

### Часть H — Official / Legal

#### 17. `regulatory-legal`
**Что:** Government sites, regulators, official documents.
**Query patterns:**
- `site:sec.gov <company>` — SEC filings
- `site:eur-lex.europa.eu <topic>` — EU regulations
- `site:fda.gov <topic>`
- `<topic> "regulation" site:gov`
- `<company> 10-K` — annual reports
- `<topic> "directive" site:europa.eu`

**Возвращает:** официальные документы, регуляторные тексты, financial filings.
**Когда:** regulatory context, validation legal claims, financial due diligence.
**Limitations:** длинные документы; нужна навигация по конкретным секциям.
**See also:** stat_sources/core/gov_macro.md, stat_sources/core/companies_public.md

#### 18. `patents`
**Что:** Patent databases.
**Query patterns:**
- `site:patents.google.com <topic>`
- `inventor:"<Name>" site:patents.google.com`
- `assignee:"<Company>" site:patents.google.com`
- `<topic> patent USPTO`

**Возвращает:** patent filings, inventors, prior art.
**Когда:** tech history, competitive analysis (что patented), validation tech claims.
**Limitations:** patents legal language, не technical clarity. Patent ≠ working tech.

---

### Часть I — Quantitative

#### 19. `data-statistical-gov`
**Что:** Government и intergovernmental статистические агентства.
**Query patterns:**
- `site:data.gov <topic>`
- `site:eurostat.ec.europa.eu <topic>`
- `site:ourworldindata.org <topic>`
- `site:bls.gov <topic>` (US labor)
- `site:fred.stlouisfed.org <topic>` (US macro)
- `<country> "statistics" <topic>`

**Возвращает:** official statistics, time series.
**Когда:** numbers blocks (metric-tracker, historical-data), validation quantitative claims.
**See also:** stat_sources/core/gov_macro.md

#### 20. `product-analytics`
**Что:** Open stat-сайты для apps, SaaS, web products.
**Query patterns:**
- `site:sensortower.com/blog <app>` — mobile
- `site:similarweb.com/website/<domain>`
- `site:crunchbase.com/organization/<co>`
- `site:builtwith.com/<domain>` — tech stack
- `site:g2.com/products/<product>` — SaaS reviews
- `site:producthunt.com/products/<product>`
- `<company> "MAU" OR "DAU" OR "ARR"` — leaked stats

**Возвращает:** product analytics, traffic, tech stacks, user reviews.
**Когда:** competitive-signals, profile-card в landscape, market sizing apps/SaaS, validation популярности.
**See also:** stat_sources/core/consumer_digital.md

#### 21. `crypto-analytics`
**Что:** On-chain data, crypto market analytics.
**Query patterns:**
- `site:coingecko.com/en/coins/<coin>`
- `site:defillama.com <protocol>`
- `site:dune.com <topic>` — community dashboards
- `site:etherscan.io <address>` — on-chain Ethereum
- `<protocol> "TVL"` / `<token> "market cap"`

**Возвращает:** market data, TVL, on-chain analytics.
**Когда:** crypto/web3 ресёрчи.
**Quality:** high — данные верифицируемы on-chain.
**See also:** stat_sources/core/crypto.md

#### 22. `social-creator-stats`
**Что:** Stats для social media creators.
**Query patterns:**
- `site:socialblade.com/<platform>/user/<name>`
- `site:twitchtracker.com <streamer>`
- `<creator> "subscribers"` / `<creator> "growth"`

**Возвращает:** YouTube/Twitter/Twitch/etc creator stats.
**Когда:** influence analysis, content creator landscape.

#### 23. `industry-benchmarks`
**Что:** Industry surveys и benchmark reports.
**Query patterns:**
- `<industry> "developer survey" <year>` (Stack Overflow, JetBrains)
- `<topic> "State of <industry>" report`
- `<topic> survey <year>`
- `<topic> "industry report"`

**Возвращает:** quantitative opinion + benchmarks.
**Когда:** validation popular claims, benchmark-numbers block, persona research.
**See also:** stat_sources/core/consulting_industry.md

#### 24. `surveys-polls`
**Что:** Surveys, polls.
**Query patterns:**
- `<topic> survey <year>`
- `site:pewresearch.org <topic>`
- `site:gallup.com <topic>`
- `<topic> "n=" survey`

**Возвращает:** public opinion data with sample sizes.
**Когда:** persona research, behavioral-patterns, validation popular sentiment.
**Limitations:** sampling bias, методология variable.

---

### Часть J — Indirect signals

#### 25. `competitive-signals`
**Что:** Indirect signals про компании.
**Query patterns:**
- `site:linkedin.com/jobs <company>` — что нанимает
- `<company> "raised"` / `<company> "funding"`
- `<company> crunchbase`
- `<company> linkedin company size`
- `<company> "leaked"` (deck leaks etc)
- `<company> "founders" interview`

**Возвращает:** indirect signals about company state.
**Когда:** landscape, profile-card, due diligence без direct access.
**Limitations:** indirect — outdated, sample-biased; нужна триангуляция.
**See also:** stat_sources/core/companies_private.md

---

### Часть K — Local context

#### 26. `local-project`
**Что:** Local files in current project. Используется только когда `subagent_type=general-purpose` или главный поток сам читает.
**НЕ WebSearch — это file system access.**

**Targets:**
- `CLAUDE.md`, `CLAUDE.local.md` — project context
- `docs/`, `README.md`
- `research/<other-slug>/<date>_*.md` — предыдущие ресёрчи
- Source code (если relevant)
- `memory/MEMORY.md`

**Когда:** project-specific ресёрчи; гибридные (внешнее + внутреннее).
**Limitations:** `subagent_type=Explore` НЕ может писать файлы и не имеет полного file access. Либо main thread, либо general-purpose subagent.

---

### Часть L — Trade associations / Industry-specific

#### 27. `trade-associations`
**Что:** Trade associations specific to industries.
**Pattern для поиска:**
- `"<industry> association" stats`
- `"<industry> trade association" report`
- `"<industry> federation" data`

Примеры (см. stat_sources/industries/<industry>.md):
- Software: BSA, SIIA
- Auto: OICA, ACEA
- Aviation: IATA
- Tourism: WTTC
- Construction: AGC, NAHB
- Hotels: AHLA, STR
- Pharma: PhRMA, EFPIA
- Steel: worldsteel.org

**Возвращает:** industry-specific data, ассоциации часто public reports.
**Когда:** landscape индустрии, market sizing, regulatory landscape.

#### 28. `industry-specific`
**Что:** Catch-all для industry-specific data sources.
**Использовать через каталог:** `references/stat_sources/industries/<industry>.md`

Each industry file has its own curated source list. Use the catalog как map: какая индустрия — какие источники.

---

### Часть M — API-direct (программный access)

#### 29. `api-direct`

**Что:** Прямой запрос к API endpoint (JSON/XML) вместо парсинга HTML страницы. Полный каталог в `api_sources/INDEX.md`.

**Когда использовать:**
- Нужны структурированные данные (JSON), не HTML
- Bulk queries — «дай 100 papers одним запросом»
- Server-side filtering (`?industry=fintech&min_funding=10M`)
- Real-time data (prices, on-chain metrics)
- Programmatic search (Brave/Tavily/Exa)

**Когда НЕ использовать:**
- WebFetch HTML работает и данных хватает
- API требует ключа, у тебя его нет → fallback на HTML
- Free tier исчерпан → fallback или alternative API
- Простой однократный lookup → WebSearch быстрее

**Главные free no-auth APIs (приоритет для агентов):**

- `Semantic Scholar` — 200M papers, academic search
- `OpenAlex` — 250M scholarly works, citation graph
- `CrossRef` — 130M DOIs, metadata
- `arXiv` — preprints, free full-text
- `DefiLlama` — DeFi TVL/protocols
- `CoinGecko` — crypto markets
- `Reddit JSON` — добавь `.json` к любому Reddit URL
- `HN Algolia` — Hacker News search
- `World Bank` — global development
- `SEC EDGAR` — US public filings (нужен User-Agent header)
- `ClinicalTrials.gov` — trial registry
- `PubMed E-utilities` — biomedical literature
- `GDELT` — global news events
- `PyPI / npm` — package metadata

**APIs с key (one-time setup, environment variable):**

- `FRED` — US economic data (instant key)
- `GitHub` — 5000 req/h authenticated
- `Stack Exchange` — 10k req/day с key
- `NewsAPI` — 100 req/day free
- `Etherscan` — 100k req/day

**Paid (когда стоит платить):**

- `Brave Search` — Google-quality search, $3/1k
- `Tavily` — AI-optimized search with built-in answers
- `Exa.ai` — semantic neural search
- `SerpAPI` — unified Google/Bing/DuckDuckGo
- `Crunchbase Basic` — startup funding data
- `Dune Analytics` — custom on-chain SQL queries

**Auth dispatch для агента:**

```
если нужен API:
  → проверить env var для ключа (FRED_API_KEY, GITHUB_TOKEN, ...)
  → если есть → использовать API
  → если нет:
     → есть free no-key tier? → использовать
     → нет → fallback на HTML версию через WebFetch
     → пометить в sources/NN.md: access: html-fallback (api blocked)
```

**Rate limit handling:**

При 429 (rate limit):
1. Подождать время из `Retry-After` header
2. Если ждать > 30 сек → fallback на HTML или alternative API
3. Пометить в `sources/NN.md` notes: `rate-limited at <ts>, fell back to <source>`

**Метки в sources/NN.md frontmatter:**

```yaml
channel: api-direct
access: api-free-no-key   # | api-free-with-key | api-paid | api-fallback-html
```

**Caveats:**
- Скилл НЕ хранит API ключи — только через environment variables
- Никогда не запрашивать ключ inline — попросить добавить в shell config
- Free tiers быстро заканчиваются на active research — спланируй budget

**Where to find docs:**

См. `api_sources/` каталог. Файлы организованы по 10 категориям:
- `search/` — Brave, Tavily, Exa, SerpAPI, You.com
- `academic/` — Semantic Scholar, OpenAlex, CrossRef, arXiv
- `financial/` — FRED, World Bank, SEC EDGAR, OECD, Alpha Vantage
- `companies/` — Crunchbase, OpenCorporates, Companies House
- `crypto/` — CoinGecko, DefiLlama, Etherscan, Dune
- `code/` — GitHub, Stack Exchange, PyPI, npm
- `social/` — Reddit, HN Algolia, Lemmy
- `news/` — NewsAPI, GDELT, Currents
- `stats/` — Eurostat, Census US, UN Data
- `domain_specific/` — PubMed, ClinicalTrials, EMA, NASA, OpenWeather

Каждый файл API имеет: endpoint, auth, free tier, rate limits, query templates, example queries для deep-research, limitations, combine-with рекомендации, fallback strategy.

---

## Channel selection — по жанрам

| Жанр | Primary channels | Secondary | Use sparingly |
|---|---|---|---|
| **explainer** | web-general, academic, wikipedia-references, code-github | books-literature, video-talks, expert-individual, api-direct (Semantic Scholar/arXiv) | social-twitter |
| **decision** | web-general, forum-discussion, industry-reports, code-github (tech) | expert-individual, surveys-polls, podcasts, api-direct (CoinGecko/SEC EDGAR для данных) | conference-proceedings |
| **landscape** | competitive-signals, news-current, industry-reports, product-analytics | patents, forum-discussion, trade-associations, industry-specific, api-direct (Crunchbase/OpenCorporates) | social-twitter, books-literature |
| **validation** | academic, preprint-servers, conference-proceedings | forum-discussion (opposition), expert-individual, surveys-polls, archive-historical (retractions), api-direct (PubMed/Semantic Scholar для bulk literature scan) | patents |
| **qa** | web-general + 2-3 channels по подтемам | api-direct если есть relevant API | varies |
| **custom** | под выбранные blocks | varies | — |

## Channel selection — по типам данных в вопросе

| Что ищем | Канал |
|---|---|
| Научный consensus | academic + preprint-servers + conference-proceedings |
| Real-user experiences | forum-discussion + surveys-polls |
| Current state (recent events) | news-current + social-twitter |
| Market size | industry-reports + data-statistical-gov + industry-benchmarks |
| Конкретная компания (public) | regulatory-legal (filings) + news-current + competitive-signals |
| Конкретная компания (private) | competitive-signals + crunchbase via product-analytics |
| Mobile apps данные | product-analytics + industry-reports |
| Crypto/DeFi | crypto-analytics + forum-discussion |
| Industry-specific KPI | industry-specific (через каталог) + trade-associations |
| Legal precedents | regulatory-legal + academic (law) |
| Historical context | archive-historical + books-literature + academic |
| Expert opinions | expert-individual + podcasts + video-talks |
| Code examples | code-github + code-other |

---

## Paywall fallback protocol (универсальный)

Когда натыкаемся на paywall — следовать sequence:

```
1. Try preprint-servers (для academic)
2. Try archive-historical (Wayback / archive.today)
3. Try author's personal site / institutional repo
4. Try alternative source с тем же контентом (summary, news article, blog)
5. Try ResearchGate / Academia.edu (для academic)
6. Try Google Cache
7. Last resort — Sci-Hub / LibGen mirrors (user-elected, legal grey area)
   - Если используешь — пометить `access: gray-area-source` в frontmatter
   - Disclaimer note про legal status в `notes` поле
8. Если ничего не работает:
   - `access: paywalled-abstract-only` (если abstract есть)
   - `access: closed` (если совсем недоступно)
   - Записать в `gaps` источника в JSON суб-агента
```

## Forbidden patterns (не использовать)

Эти подходы НЕ применять, даже как fallback:
- Bypass через bot-protection (Cloudflare CAPTCHA, etc) — не работает в WebFetch, не пытайся
- Credential reuse / login bypass — НИКОГДА
- Scraping с violation robots.txt — этическое нарушение

## Когда канал «не работает»

Если канал должен был дать результаты, но не даёт — варианты:
1. Query too narrow — пробуй более broad
2. Topic not covered этим каналом — попробуй другой
3. Источник заблокирован — fallback sequence (paywall protocol)
4. Тема слишком новая — нет ещё данных, переходи в news-current/social-twitter

В `sources/NN.md` JSON суб-агента secrets поле `channel:` показывает откуда брали — если несколько channels вернули нулевые — фиксируй в `gaps`.

## Future channels (TODO когда появятся возможности)

Эти каналы пока недоступны через стандартный WebSearch+WebFetch — отмечаю на будущее:
- Twitter Streaming API (требует API key)
- LinkedIn data (login required)
- Specific paywalled databases (Bloomberg, Refinitiv) — требует subscriptions
- YouTube transcripts API
- Spotify API для music
