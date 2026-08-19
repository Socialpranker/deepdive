# Source Dispatch — как выбирать каналы и источники под подвопрос

**Когда используется:** в начале Phase 4 (Search). После того как `plan.md` готов и подвопросы декомпозированы — для **каждого подвопроса** прогоняешь его через этот файл и записываешь dispatch-решение в plan.md секцию 12 «Information sourcing strategy».

**Что делает:** превращает подвопрос («какова доля рынка X в EU») в **упорядоченный список каналов и конкретных источников**: primary → secondary → fallback. Без этого Claude каждый раз заново угадывает «откуда брать данные».

---

## Принципы

1. **Источник выбирается под подвопрос, не под тему целиком.** Тема «vertical farming market in EU» декомпозируется на 5-8 подвопросов, и каждый получает свой dispatch.
2. **Каждый подвопрос → минимум 2 канала разных типов** (требование триангуляции из Phase 5). Если один канал — это уже флаг к адверсариал-пассу.
3. **Primary = ожидаемо самый сильный по credibility/recency.** Secondary = независимая проверка. Fallback = если primary недоступен.
4. **Открытые API > HTML scraping.** Если для подвопроса есть API из `api_sources/` — он primary. HTML только если API нет.
5. **Awesome-lists и репозитории — это discovery, а не finite-каталог.** Используй их когда твой каталог не покрывает тему (см. секцию «Discovery patterns» ниже).

---

## Matrix: типовой подвопрос → каналы

Сигналы в подвопросе → primary/secondary/fallback каналы. Каналы из `channels.md`, конкретные API из `api_sources/`, статы из `stat_sources/`.

| Сигнал в подвопросе | Primary channel | Secondary | Fallback |
|---|---|---|---|
| «размер рынка X», «market size» | `industry-reports` (Statista alt, IBISWorld free, McKinsey/BCG/Bain public reports) | `data-statistical-gov` (FRED, World Bank, Eurostat industry codes) | `web-general` + `competitive-signals` (top players' annual reports) |
| «тренд X по времени», «time series» | `api-direct` (FRED, World Bank, OECD, Eurostat) | `data-statistical-gov` (национальные стат-сайты) | `news-current` (GDELT для качественной хронологии) |
| «правда ли X с научной точки зрения» | `academic` (OpenAlex, Semantic Scholar) + `preprint-servers` (arXiv, bioRxiv, medRxiv, SSRN) | Cochrane reviews + Crossref для цитирований | `web-general` для научпопа |
| «кто игроки в X пространстве» | `competitive-signals` (Crunchbase, OpenCorporates, Companies House) | `code-github` (для tech) + `industry-reports` | `forum-discussion` (Reddit, HN — community knowledge о игроках) |
| «X в стране Y» | `data-statistical-gov` страны Y (нац-стат, центробанк) | `api-direct` (World Bank, IMF, OECD по country code) | `news-current` + локальная пресса |
| «как работает X технически» | `code-github` (reference implementations) + `academic` (foundational papers) | `forum-discussion` (Stack Exchange, technical blogs) | `web-general` (docs официальных продуктов) |
| «свежие изменения в X», «recent» | `news-current` (NewsAPI, GDELT, Currents) + `industry-reports` | `forum-discussion` (Reddit, HN — обсуждения новостей) | `api-direct` regulatory feeds |
| «регулирование X в юрисдикции Y» | `regulatory-legal` (регулятор страны Y, EUR-Lex для EU, CFR для US) | `news-current` (юр-пресса, Law360, Reuters Legal) | `academic` (legal scholarship) |
| «производительность X», «benchmark» | `code-github` (paperswithcode, lmarena, leaderboards) + `academic` | `forum-discussion` (HN threads, Reddit r/MachineLearning, ML twitter) | `news-current` |
| «sentiment / общественное мнение» | `forum-discussion` (Reddit, HN Algolia, Twitter API) | `news-current` + `competitive-signals` (reviews aggregators) | Survey-данные через `data-statistical-gov` (Pew, Eurobarometer) |
| «adoption / usage data» | `product-analytics` (SimilarWeb, App Annie, Sensor Tower public data) | `code-github` (для open-source — stars/downloads via PyPI/npm stats) | `industry-reports` |
| «цена / стоимость X», pricing | официальные сайты + `web-general` | `competitive-signals` (price comparison sites) | `forum-discussion` (reddit threads about pricing) |
| «крипто/DeFi проект X» | `crypto-analytics` (DefiLlama, Etherscan, Dune) + `api-direct` (CoinGecko) | `code-github` (репо проекта + аудиты) | `forum-discussion` (Crypto Twitter, r/cryptocurrency, governance forums) |
| «health/clinical X» | `domain-specific` (PubMed, ClinicalTrials.gov, EMA) | `academic` (Cochrane, OpenAlex) | `news-current` (медицинская пресса, STAT, Endpoints) |
| «environmental / climate X» | `data-statistical-gov` (NASA, NOAA, ESA, Copernicus, IEA) | `academic` (Nature, Science) + `api-direct` (OpenWeather) | `news-current` (climate journalism) |
| «job market / hiring X» | `data-statistical-gov` (BLS, Eurostat labor) | `competitive-signals` (LinkedIn — HTML, Glassdoor) | `industry-reports` (HR firms — Korn Ferry, Mercer) |
| «philosophical / qualitative / framework» | `academic` + `web-general` (long-form essays — substack, blogs, books online) | `forum-discussion` (LessWrong, Marginal Revolution, philosopher's stone) | own community archives |

**Если подвопрос не матчится** ни одну строку — действуй по умолчанию: `web-general` + `academic` + `news-current` минимум. И **сразу же запиши в plan.md секцию 12, что dispatch был ad-hoc** — это сигнал для Phase 6 (adversarial) что покрытие могло быть слабым.

---

## Registry-first: за числами не ходят в веб

**Правило.** Подвопрос количественный (ответ — число: размер, доля, цена, темп, срок)
⇒ **primary-канал обязан быть `api-direct` или `data-statistical-gov`**, то есть
реестр, датасет, отчётность. Веб-статья с цифрой не может быть корнем числа — она
указатель на корень.

Обрати внимание: две строки матрицы выше сейчас противоречат этому правилу —
«размер рынка X» ведёт в `industry-reports`, «цена / стоимость X» в `web-general`.
Для количественной формулировки правило перекрывает матрицу: сначала ищется реестр,
отраслевой отчёт идёт вторым.

**Зачем.** Дешевле не порождать мусор на входе, чем фильтровать на выходе. Веб-поиск
отдаёт SEO-топ, и цифры там живут своей жизнью: market-sizing от контор, торгующих
отчётами; «74% компаний...» из презентации 2011 года, чей первоисточник мёртв;
vendor-бенчмарк, пересказанный четырьмя изданиями. Ни `recency`, ни `bias` их не
ловят — у свежей перепечатки честные оценки по обеим шкалам.

**Как исполнять на шаге 4.0:**

1. Разметь каждый подвопрос: количественный / качественный.
2. Для количественного — проверь покрытие в `stat_sources/INDEX.md` и
   `api_sources/INDEX.md` ДО назначения каналов. Нашёл endpoint — он primary, веб
   уходит в fallback.
3. Запиши в `plan.md` §12 конкретный endpoint (не «FRED», а серию), чтобы суб-агент
   не искал его заново.
4. Покрытия нет — так и напиши: «метрика M реестром не покрыта, берём из вторичных,
   `origin_kind: secondary`». Это честный результат, он должен быть виден, а не
   замаскирован уверенной цифрой.

**Проверяется машинно.** Число, попавшее в выводы из веб-источника при наличии
покрывающего endpoint, — дефект дисциплины, а не вкусовщина:
`scripts/check_number_provenance.py` пометит источник по `origin_kind`/`chain_len`, а
fail-closed правило не пустит такое число в `memo.md`.

**Анти-паттерн:** взять цифру из статьи, потом «подтвердить» её тремя другими
статьями. Это не триангуляция, а тираж одного корня — правило `≥2 корней` и детектор
циркуляции ловят ровно этот случай.

---

## Registry — проверенные адреса под сигнал

`references/registry/` — 1072 адреса с пометкой доступа (free / ключ / User-Agent) по типу сигнала: science, regulatory (парламентские API), markets, technology, security, climate_health, society, registries, open_source_releases. Нужен свежий поток или прямой эндпоинт, которого нет в `api_sources/` — открой ОДИН файл по теме, не INDEX. Достоверность в таблице — метка разведки, не результат Фазы 5.5; срок годности списка — месяцы, мёртвый адрес лечится обычным fallback.

## Discovery patterns — когда каталога не хватает

Каталог `stat_sources/` + `api_sources/` + `registry/` покрывает базовые domains, но **редкие темы** (niche industries, esoteric academic fields, region-specific topics) требуют поиска *новых источников* в runtime. Алгоритм:

### 1. GitHub topic search
```
https://github.com/topics/<keyword>
https://github.com/search?q=topic:<keyword>+sort:stars
```
**Зачем:** Найти:
- `awesome-<keyword>` репозитории — кураторские списки источников
- Open-source datasets под темой
- Tools/libraries (значит есть API или ETL pipeline)

**Пример:** Тема «satellite imagery» → `github.com/topics/satellite-imagery` → `awesome-satellite-imagery-datasets` → 30+ dataset ссылок которые не в нашем каталоге.

### 2. Awesome-lists registry
`references/awesome_lists_registry.md` уже содержит 25+ кураторских списков. **В Phase 4 первым делом** проверь его на тему:
- Tier 1: `public-apis`, `awesome-public-datasets` (универсальные)
- Tier 2: специализированные по domain (finance, science, crypto, health)
- Tier 3-4: niche и aggregators

### 3. HuggingFace + Kaggle datasets
```
https://huggingface.co/datasets?search=<topic>
https://www.kaggle.com/datasets?search=<topic>
```
**Зачем:** Готовые датасеты для ML/анализа. Часто содержат уже очищенные данные + метаданные источника.

### 4. PyPI / npm / crates search
```
https://pypi.org/search/?q=<topic>
https://www.npmjs.com/search?q=<topic>
```
**Зачем:** Библиотеки часто:
- Оборачивают чужой API → значит есть API
- Включают bundled datasets
- Документируют где брать данные

**Пример:** тема «satellite imagery» → PyPI search `satellite` → `sentinelsat` → Copernicus Open Access Hub API.

### 5. Data portals (government / EU)
- `data.gov` — US federal datasets
- `data.europa.eu` — EU open data portal
- `data.gouv.fr`, `data.gov.uk` и др. национальные
- `data.worldbank.org/data-catalog` — WB полный каталог

**Зачем:** Авторитетные источники для гос-стат, регуляторных данных, демографии.

### 6. Academic dataset registries
- `datadryad.org` — research datasets
- `zenodo.org` — multi-domain научные датасеты
- `figshare.com` — supplementary data к статьям
- `re3data.org` — registry of research data repositories

**Зачем:** Если тема академическая и нужны исходные данные за статьями.

### 7. Industry-specific registries
По мере необходимости — секторные:
- Healthcare: NIH BioLINCC, GHDx, IHME
- Finance: BIS, IMF datamapper, FSB
- Climate: NASA NEX, NOAA Climate Data Online, IEA datasets
- Crypto: Dune dashboards, Messari, Glassnode (paid)

Если тема узкая — спроси USER нет ли у него подсказки.

---

## Decomposition recipes — типовые декомпозиции тем

Не каждый подвопрос виден из формулировки. Эти рецепты — **типовые разбиения больших тем**, чтобы получить полный набор подвопросов перед dispatch'ем.

### «Market analysis of X»
1. **Size & growth** → industry-reports + gov_macro
2. **Segmentation** → industry-reports + competitive-signals
3. **Top players** → competitive-signals (Crunchbase/OpenCorporates) + code-github если tech
4. **Recent news / events** → news-current (NewsAPI/GDELT last 6mo)
5. **Academic context** → academic on underlying tech/practice
6. **Consumer sentiment** → forum-discussion (Reddit, HN) если consumer-facing
7. **Regulatory landscape** → regulatory-legal per relevant jurisdictions
8. **Forecasts** → industry-reports + osebene mention каких analyst houses cover это (Gartner, IDC, Forrester)

### «Is X true / does X work»
1. **Foundational claim** → academic (peer-reviewed)
2. **Systematic reviews / meta-analyses** → Cochrane, PROSPERO
3. **Counter-evidence / replication failures** → preprint-servers, retraction-watch
4. **Real-world adoption / case studies** → industry-reports, code-github если tool
5. **Critics / sceptics** → academic critiques + forum-discussion (LessWrong, EA forum)
6. **Mechanism / how it would work** → academic + technical blogs

### «How does X work»
1. **Reference paper / original source** → academic
2. **Implementations / code** → code-github (paperswithcode, official repos)
3. **Tutorials & explanations** → web-general (long-form blogs) + forum-discussion
4. **Variations / extensions** → academic + preprint-servers (recent papers cite original)
5. **Limitations / failure modes** → forum-discussion + adversarial paper search
6. **Benchmarks / performance** → code-github (leaderboards) + academic

### «Should I do X» (decision genre)
1. **What does X actually involve** → web-general (vendor docs) + academic если есть
2. **Cost / ROI** → industry-reports + forum-discussion (real practitioners)
3. **Risk factors** → academic on failure modes + news-current (recent failures)
4. **Alternatives** → competitive-signals + academic comparisons
5. **Who's done it (case studies)** → industry-reports + competitive-signals
6. **What experts say** → academic + people-focused (specific authorities)
7. **Counter-arguments** → critical sources, forum-discussion (skeptics)

### «Landscape: who's in X space»
1. **Top by market share / revenue** → industry-reports + competitive-signals
2. **Top by funding / valuation** → competitive-signals (Crunchbase)
3. **Top by tech / academic citations** → academic + code-github
4. **Recent entrants** → competitive-signals (Crunchbase recent) + news-current
5. **Dying / exiting** → news-current (acquisitions, shutdowns) + competitive-signals
6. **Open-source ecosystem** → code-github (topics, awesome-lists)
7. **Geographic distribution** → industry-reports + national stat sources per region

### «Validation: правда ли что [claim]»
1. **Original source of claim** → найти первоисточник в news/academic/blogs
2. **Primary evidence** → academic + data-statistical-gov
3. **Counter-evidence** → academic critiques + retracted-papers DB
4. **Independent replication** → preprint-servers + academic
5. **Who else makes this claim** → web-general (citation chain)
6. **Who disputes it and why** → forum-discussion + academic adversarial
7. **What it would take to falsify** → reasoning + academic methodology

---

## Когда лезть в репозитории явно

Источник `code-github` через `WebFetch` или GitHub API (`GITHUB_TOKEN` если есть) — primary в этих случаях:

1. **Тема упоминает технический инструмент:** «open source», «library», «framework», «protocol», «standard»
2. **«Как работает X» где X — алгоритм/практика:** велика вероятность что есть reference implementation
3. **Поиск датасетов:** `topic:dataset`, `topic:open-data`, `topic:public-data`
4. **Поиск кураторских списков:** `awesome-<topic>` repo naming convention
5. **Бенчмарки:** `topic:benchmark`, `topic:leaderboard`
6. **Реализации academic papers:** добавь `paperswithcode` или ищи repo с названием статьи

Что искать в репозитории:
- **README** — описание, цель, datasets used, methodology
- **stars + recent commits** — proxy качества и активности (Phase 5 scoring)
- **issues** — known problems, edge cases, что не работает (опционально для adversarial)
- **discussions / wiki** — best practices, FAQ
- **CITATION.cff** или `papers/` — формальные ссылки на работы

**Не лазь в репо просто чтобы было.** Только если ожидаешь там данные или код, релевантный подвопросу.

---

## Output: что записать в plan.md

После того как все подвопросы прогнаны через этот файл — заполни секцию 12 plan.md в таком формате:

### Поле `qclass`

Каждый подвопрос получает `qclass` — класс, по которому накапливается статистика
отдачи каналов. Ставится вместе с dispatch-решением, пишется в §12 рядом с каналами:

`market-size` · `time-series` · `scientific-claim` · `players` · `country-stat` ·
`how-it-works` · `recent-change` · `regulation` · `benchmark` · `sentiment` ·
`adoption` · `pricing` · `crypto` · `health` · `climate` · `jobs` · `qualitative`

Класс соответствует строке матрицы выше. Подвопрос, не попавший ни в одну строку,
получает `qclass: qualitative` и помечается как ad-hoc — как и сейчас.

Формат строки в §12:

- **qclass:** `market-size`

```markdown
## 12. Information sourcing strategy

### Подвопрос Q1: «What's the EU vertical farming market size and growth rate?»
- **Primary:** industry-reports → search "EU vertical farming market" agri-tech analyst houses (AgFunder, Plenty/Infarm public summaries)
- **Secondary:** data-statistical-gov → Eurostat agricultural production NACE codes A.01 for greenhouse/protected cultivation
- **Fallback:** web-general → top EU vertical farming company annual reports (Infarm, Jungle, Nordic Harvest)
- **Decomposition note:** classic «market analysis» recipe — adding Q1b «top EU players» and Q1c «forecast 2025-2030»

### Подвопрос Q2: «Is vertical farming economically viable at scale?»
- **Primary:** academic → OpenAlex + Semantic Scholar with API key, "controlled environment agriculture" reviews
- **Secondary:** industry-reports → unit economics analyses from AgFunder Network, McKinsey AgTech
- **Fallback:** forum-discussion → r/verticalfarming, AgTech Twitter, conference proceedings (Indoor Ag-Con)
- **Adversarial pre-flag:** bankruptcies (Infarm 2024 restructuring, AeroFarms Chapter 11), failure-mode papers

### Подвопрос Q3: «What's the regulatory status of vertical farming across EU member states?»
- **Primary:** regulatory-legal → EUR-Lex CAP (Common Agricultural Policy) on controlled environment, EFSA food safety guidance
- **Secondary:** per-country → national agriculture ministries (BMEL Germany, MASAF Italy, DEFRA UK для post-Brexit context)
- **Fallback:** news-current → Reuters Sustainability, Politico EU on AgTech policy

### Discovery executed:
- ✓ Checked awesome_lists_registry → found `awesome-agtech` and `awesome-agriculture` (Tier 2)
- ✓ GitHub topic search `topic:vertical-farming` → 8 datasets, 2 with EU focus
- ✓ HuggingFace datasets search → 1 controlled-environment-agriculture dataset

### Gaps noted:
- No EU-wide vertical-farming production tracker — accepting industry-report estimates with caveat
- No real-time regulatory feed — manual check per member state needed
```

**Это и есть deliverable** Source Dispatch шага. Без него Phase 4 — это хаотичный поиск.

---

## Приор при выборе канала сверх обязательного минимума

Primary и Secondary из матрицы выше — обязательная часть покрытия. Она держит
триангуляцию (≥2 разнотипных канала) и приором не двигается никогда: игнорировать
матрицу в пользу «канала с лучшей статистикой» — способ тихо сломать независимость
источников.

**Когда встаёт вопрос о дополнительном канале** — а не о замене Primary/Secondary:
depth=deep требует более широкого покрытия подвопроса · сработал deviation-триггер
(`unexpected_finding`/`contradiction`, см. Фазу 4 в `SKILL.md`) и нужен ещё один
раунд · Fallback из матрицы выглядит слабым вариантом для конкретной темы.

**Как решать:**

```
python3 scripts/update_priors.py --qclass <qclass текущего подвопроса>
```

Печатает все известные каналы этого `qclass`, ранжированные по posterior mean
(0..1, выше — лучше отдавал улики в прошлых прогонах), без обрезки топ-20 — обрезка
там уместна для общего обзора, а не для одного класса, где выборка и так мала.
Взять канал с наибольшим значением среди ещё не использованных в этом подвопросе.
Пустой вывод — приора по этому `qclass` ещё нет, действовать по матрице как обычно.

**Не заменяй Primary/Secondary этим шагом.** Он решает только про добавочный канал
сверх обязательного минимума. Матрица и registry-first правило (выше) сильнее любой
накопленной статистики — они закрывают систематическую ошибку (веб как источник
чисел), а приор всего лишь ранжирует эмпирическую отдачу.

**Как эта статистика вообще появляется** — `SKILL.md`, раздел «Постобработка
прогона — сбор наблюдений байесовского роя»: после Фазы 7 каждый прогон пишет
наблюдения по фактически использованным каналам, а найденные здесь через Discovery
patterns ad-hoc источники, ставшие `root`/`dissent` claim'а, регистрируются как
кандидаты на промоушен в каталог тем же шагом.

---

## Anti-patterns

**❌ «Просто гуглить»** — `web-general` это всегда **fallback**, не primary. Если он primary — ты не прогнал тему через dispatch.

**❌ Один канал на подвопрос** — нарушает требование триангуляции в Phase 5. Минимум 2 разнотипных канала.

**❌ Игнорировать awesome-lists registry** — он там для того чтобы каталог не был finite. Всегда проверяй его если тема узкая.

**❌ Лезть в репозитории без причины** — `code-github` это primary только когда подвопрос про код/инструмент/датасет. Не для «найти что-нибудь по теме».

**❌ Не записывать dispatch в plan.md** — без записи Phase 6 adversarial не сможет проверить покрытие.

**❌ Использовать paid-источники когда есть free** — если у user нет ключа Statista/Crunchbase/Bloomberg, не строй стратегию вокруг них. Сначала free, потом paid если free не хватает.

**❌ Приором подменять Primary/Secondary** — приор ранжирует только добавочный канал сверх обязательного минимума (см. выше). Обязательная часть матрицы приором не двигается никогда — иначе рой обучится ходить туда, где уже сильно, и точки роста никогда не проверятся заново.
