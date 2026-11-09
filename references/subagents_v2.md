# Subagents v2 — параллельный поиск через Agent tool

## Содержание

- Архитектура
- Какой subagent_type
- Какую модель выбрать (model routing)
- Параллелизм
- Промпт суб-агенту — шаблон
- После возврата суб-агентов — что делает главный поток
- Антипаттерны
- Когда НЕ запускать суб-агентов

Применяется в режимах **medium** (2–3 суб-агента) и **deep** (4–5).

`<SKILL_DIR>` = абсолютный путь к скиллу, обычно `$HOME/.claude/skills/deepdive` (главная раскрывает `$HOME` и подставляет при вызове). Пути к файлам скилла в брифах агентов пишутся как `<SKILL_DIR>/…`.

## Архитектура

```
Главный поток (assistant):
  - формирует план, разбивает тему на подтемы
  - назначает каждому агенту диапазон номеров источников (s01-s09, s10-s19, ...)
  - запускает суб-агентов в ОДНОМ сообщении (параллель)
  - получает ТОЛЬКО индекс-строки для sources.csv (URL/title/type/date/scores/
    subquestion_ids/файл) — не полные тексты
  - мёржит sources.csv, дедуплицирует по URL между диапазонами
  - заполняет claims.csv из индекс-строк + заявленных claim'ов
  - триангулирует по claims.csv, синтезирует

Суб-агент (subagent_type=deepdive-fetcher, свой диапазон NN):
  - читает свой промпт (включая закреплённый диапазон номеров)
  - делает WebSearch + WebFetch
  - оценивает каждый источник по шкале сам (не отдельный scoring pass — H7)
  - ПИШЕТ полные файлы sources/NN_slug.md в своём диапазоне (Write — параллельно,
    без конфликтов, т.к. диапазоны не пересекаются)
  - возвращает в главный поток ТОЛЬКО индекс-строки (компактно — полные тексты
    источников через главный контекст не проходят)
```

Так главный поток не раздувается сырыми текстами источников (только компактные индекс-строки), а параллельная запись `sources/NN.md` не конфликтует, потому что у каждого агента свой непересекающийся диапазон номеров.

## Какой subagent_type

- **`deepdive-fetcher`** — дефолт для fetch+save (Phase 4.1; Haiku, tools WebSearch/WebFetch/Read/Write/Bash/Glob/Grep, maxTurns 40). Нужен `Write`, чтобы агент сам сохранял `sources/NN.md` в своём диапазоне номеров, а не передавал полные тексты обратно в главный поток. Каждому агенту — явный диапазон: агент №1 → `s01-s09`, №2 → `s10-s19`, и т.д. (см. промпт-шаблон ниже, поле `SOURCE ID RANGE`).
- **`explore-haiku`** (read-only, Haiku) — только для чистой discovery-разведки БЕЗ сохранения файлов (например, Phase 3.5 capability discovery или предварительная разведка «сколько вообще есть материала» до того как решили дробить на подтемы). `Explore`/`explore-haiku` не пишет файлы; как только агенту нужно писать `sources/NN.md` — это `deepdive-fetcher`.
- **`deepdive-scout`** (Haiku) и **`deepdive-redteam`** (Opus, high, read-only) — специализированные агенты deepdive; red team запускать только как `subagent_type: deepdive-redteam`.
- **`Plan`** — НЕ для поиска. В deepdive не использовать.

## Какую модель выбрать (model routing)

Перед запуском суб-агентов читай `model_routing.md`: там матрица фаза × подзадача → исполнитель, а эта выдержка без неё неполна.

Краткая выдержка для Phase 4.1 (launch sub-agents):

| Тип подзадачи sub-agent'а | Исполнитель | Модель / Effort |
|---|---|---|
| Web search + metadata (web-general/news/forum) | `deepdive-fetcher` | haiku / medium (frontmatter) |
| Read long source + extract quotes | `deepdive-fetcher` | haiku / medium (окно 1M) |
| Academic / preprint-servers | `deepdive-fetcher` | haiku / medium |
| API-direct (curl + jq) | `deepdive-fetcher` | haiku / medium |
| Code analysis (clone + grep) | `deepdive-fetcher` собирает факты и пути, выводы — `main` | haiku / medium |
| Heavy reasoning subtask | `main` | — |

**Default если не уверен** → `deepdive-fetcher`.

Модель и effort `deepdive-fetcher` записаны в его frontmatter; вызов их не передаёт, чтобы настройка жила в одном месте. Эскалация после отказа или провала Haiku — `general-purpose` с явными `model: "sonnet"`, `effort: "high"`, см. `model_routing.md` «Как передать модель».

```
Agent({
  subagent_type: "deepdive-fetcher",   // fetch+save нужен Write, см. выше
  description: "...",
  prompt: "..."
})
```

## Параллелизм

В одном сообщении ассистента — ВСЕ Agent calls одновременно.

Если суб-агентов 4+ — запускай с `run_in_background: true`:
- Реальный параллелизм, не очередь.
- Уведомления при завершении каждого — не нужно polling.
- Можно начинать сборку результатов по мере поступления.
- Оговорка: фоновые субагенты получают урезанный набор инструментов — перед запуском fetch в фоне проверить, что нужные Write/WebFetch доступны; если не проверено — запускать на переднем плане.

Если 2 суб-агента — можно без background (быстрее на круг).

## Промпт суб-агенту — шаблон

**Источник содержимого промпта.** Промпт суб-агента **НЕ пишется с нуля** — он собирается из готового `plan.md`:

- `SUBTOPIC` ← плановая подтема (из `plan.md` секция 11 — таблица «Подтемы ↔ Блоки mapping»)
- `BLOCKS THIS SUBTOPIC FEEDS` ← из той же таблицы (под какие блоки собираем)
- `HYPOTHESES TO TEST` ← из `plan.md` секция 9 (только релевантные для подтемы)
- `CHANNELS TO USE` ← из `plan.md` секция 12 после Phase 4.0 Source Dispatch: уже разложено на **primary / secondary / fallback** через `source_dispatch.md` matrix. Суб-агент НЕ выбирает каналы сам — следует уже зафиксированной dispatch-стратегии.
- `STAT-SOURCES TO USE` ← из той же секции 12 → stat-источники (конкретные файлы из `stat_sources/`)
- `API ENDPOINTS TO USE` ← из той же секции 12 → конкретные API из `api_sources/` (с пометкой какие auth-env-vars нужны)
- `DISCOVERY EXECUTED` ← из секции 12: что уже было найдено через awesome-lists registry / GitHub topics / HuggingFace на шаге 4.0 — суб-агент может на это опираться, не повторять discovery впустую
- `CRITICAL GAPS` ← из секции 12 → critical gaps to address для этой подтемы
- `SOURCE ID RANGE` ← закреплённый за этим агентом диапазон номеров источников, назначает главный поток ПЕРЕД launch: агент №1 → `s01-s09`, №2 → `s10-s19`, №3 → `s20-s29`, и т.д. (шаг по 9-10 номеров с запасом). Диапазоны не пересекаются — это устраняет конфликты при параллельной записи `sources/NN.md`.

Так главный поток не дублирует работу плана и обеспечивает прозрачность: пользователь в plan.md видит точно тот же brief что и агент.

Каждый промпт **самодостаточный** — суб-агент не видит контекста основного диалога.

**Язык промпта.** Если подтема — англоязычные источники (международные институции, tech, академические) — пиши на английском. Если рус-сегмент — на русском. Качество ответов суб-агента лучше при совпадении языка промпта и языка источников.

### EN template

```
CONTEXT: We are researching <main_question>. This is the deepdive workflow,
medium/deep depth, with structured JSON output requested.

YOUR SUBTOPIC: <narrow subtopic — what THIS agent looks for, not the whole theme>

YOUR SOURCE ID RANGE: s<NN>-s<MM> (e.g. s10-s19). Use ONLY these numbers for the
files you write. Do not reuse a number outside your range — other agents are
writing in parallel with their own ranges.

BLOCKS THIS SUBTOPIC FEEDS:
- <block-id>: <what data the block needs>
- <block-id>: <what data the block needs>
(from plan.md section 11 — subtopic↔blocks mapping)

HYPOTHESES TO TEST:
- H1: <falsifiable statement>
- H2: ...
- (only the hypotheses relevant to THIS subtopic)

SOURCING STRATEGY (already dispatched via source_dispatch.md — DO NOT re-pick):
- Primary channel: <channel-name> — <what specifically>
  Query template: `<...>`
  Specific endpoints: <api_sources/.../X.md> if api-direct
- Secondary channel: <channel-name> — <what>
  Query template: `<...>`
- Fallback channel: <channel-name> — only if primary/secondary fail

See <SKILL_DIR>/references/channels.md for query patterns, paywall fallback protocols, limitations.

DISCOVERY ALREADY EXECUTED (from plan.md section 12):
- <awesome-list or repo found at dispatch step — start there, don't rediscover>
- <huggingface/kaggle dataset already identified>
- <github topic search result>
(if none — discovery wasn't run for this subquestion; you may run it but flag it)

STAT-SOURCES TO USE (if relevant):
- `stat_sources/<path>.md` → <source name> for <metric>
- `stat_sources/<path>.md` → <source name> for <metric>

Direct these sources for quantitative claims. Use the URLs/queries from those files.

STANCE (read before you start):
A source can be unreliable, and every source has interests of its own. Popularity
is not evidence and agreement between sources is not evidence either — ten pages
can agree because they copied one press release. As you read, actively look for
CONTRADICTIONS between sources and ask of each: who produced this material, who
paid for it, and would they publish the opposite finding? Record what you find in
the fields below; do not silently pick a winner.

TASK:
1. Search using the channels above. For 5-10 sources total across all channels.
   Different source types: Primary, Academic, Industry-media, General-media,
   Expert-blog, Forum, Opposition.
2. For each source — read it (WebFetch) and extract:
   - If WebFetch comes back THIN — under ~500 chars of main text, no quotable
     passage, or a block/consent/paywall page — run the ladder RIGHT THEN, as a
     standard step, not as an exception:
     `uv run <SKILL_DIR>/scripts/fetch_source.py <URL> -o <run>/.fetch/NN.md --meta <run>/.fetch/NN.json`
     Record `fetch_tier:` from the metadata in the source frontmatter.
   - 2-4 key direct quotes (verbatim, with location/page if possible)
   - Author, publication date, source type. `type` is a STRICT enum — copy ONE
     of these seven verbatim, never invent a label or a variant spelling:
     Primary | Academic | Industry-media | General-media | Expert-blog | Forum | Other.
     Triangulation counts DISTINCT types, so a free-form label silently inflates
     type diversity and turns a one-type claim into a "triangulated" one.
   - How it relates to each hypothesis (supports / contradicts / neutral)
3. Score each source YOURSELF on three axes 1-5 (no separate scoring pass follows —
   you are the one who read it, you score it):
   - Credibility: 5=primary/peer-review, 4=industry-authority, 3=quality general media,
     2=expert blog, 1=forum/anon
   - Recency: 5=<1yr, 4=1-3yr, 3=3-5yr, 2=5-10yr, 1=>10yr (unless historical topic)
   - Bias: 5=neutral/scientific, 4=industry-neutral, 3=mainstream with known slant,
     2=lobbyist, 1=propaganda
4. Include at least 1-2 sources representing opposition or criticism of the
   dominant view in this subtopic: the stop criteria require an analysed opposition
   search, and red team has nothing to test without it. If you cannot find any,
   say so explicitly.
5. WRITE the full source file yourself: `sources/<id>_<short-slug>.md` using the
   template in `<SKILL_DIR>/references/source_scoring.md`, with complete frontmatter (channel, access,
   scores, subquestion_ids) and verbatim quotes. Never write a source with fewer
   than 2 verbatim quotes: run the ladder first. If the ladder ends in auth-wall /
   anti-bot, write it with `access: closed` and only what the snippet gave — such a
   source cannot be a triangulation leg. Use ONLY ids from your assigned
   range (see YOUR SOURCE ID RANGE above).
   Fill the `root:` field while reading (see source_scoring.md "Provenance"):
   `own` if the source produced its material itself; a short stable id of the
   underlying material it retells (e.g. `press-release-acme-2026-03`,
   `study-smith-2024`) otherwise; `unclear` if you cannot tell where the data
   comes from. Ten articles retelling one press release are ONE voice — the
   triangulation rule counts distinct roots, so this field is not optional.
   If several sources retell the SAME underlying material, they must carry the
   BYTE-IDENTICAL root string — otherwise root dedup silently fails.
   Own measurements (a lab run, benchmark, or experiment you executed) all share
   ONE root `own-lab-<slug>`, however many files the results are split across —
   three slices of one run are one voice, not three.

   Also fill `discovery_path:` — HOW you reached this source: `<channel>|<exact
   query string>|<language>` (e.g. `web-general|EU vertical farming yield 2025|en`,
   or `api-direct|FRED:CPIAUCSL|-` for a registry pull). Two sources found by the
   same query in the same channel are ONE sampling of one index, however different
   they look; triangulation counts distinct discovery paths as its fourth
   condition, so a copy-pasted value here inflates independence.

   For any source carrying a NUMBER you expect to use, also fill:
   - `origin_kind:` — one of `measurement` | `registry` | `filing` | `survey` |
     `model-estimate` | `secondary` | `unknown`. What KIND of act produced the
     number, not who republished it.
   - `origin_url:` — URL of the document that PRODUCED the number (the filing, the
     dataset, the paper with methodology). Not the page you read it on, unless
     that page is itself the producer. `-` if you could not find it.
   - `data_as_of:` — the date of the DATA (`2025-Q3`, `2024-12`), not the
     publication date of the article. A number whose data date you cannot
     establish is a number you must mark `unknown`.
   - `chain_len:` — `0` if this source produced the number itself, `1` if it
     retells the producer directly, `2+` if it retells a retelling.
   Do not guess these to look complete: `unknown` / `-` is a valid, useful answer
   and is treated as a quarantine flag downstream. A fabricated `origin_url` is
   far worse than an honest `-`.
6. For each claim/thesis this subtopic supports, note it as a candidate row for
   `claims.csv` (claim text, hypothesis id if any, which source ids back it, source
   types, whether at least one is Primary — the "primary_source" flag).

OUTPUT FORMAT — write the JSON below to `<run>/agent_reports/<subtopic-id>.json`
(strict JSON, compact index rows, NOT full source text — that already lives in the
files from step 5). Your final chat reply is ≤15 lines: the JSON file path, counts
(sources kept / claim_candidates / systems), top-3 gaps, opposition found yes/no.
Do NOT paste the JSON into the reply — measured: replies with the JSON inline ran
19–24k chars each (~10k tokens of the main thread), replies with a line limit 3–5k.

JSON file content:

{
  "subtopic": "<this subtopic>",
  "summary": "<3-5 sentence summary of what you found>",
  "source_index": [
    {
      "id": "s07",
      "url": "https://...",
      "title": "...",
      "type": "Primary|Academic|Industry-media|General-media|Expert-blog|Forum|Other",
      "channel": "<channel-name-from-channels.md>",
      "date": "YYYY-MM-DD or YYYY",
      "credibility": 5, "recency": 4, "bias": 4, "total": 13,
      "root": "own | <root-id> | unclear",
      "discovery_path": "<channel>|<exact query>|<lang>",
      "caveat": "- | vendor | self-reported | disputed:sNN",
      "origin_kind": "measurement|registry|filing|survey|model-estimate|secondary|unknown",
      "origin_url": "https://... or -",
      "data_as_of": "YYYY-QN or YYYY-MM or -",
      "chain_len": 0,
      "subquestion_ids": ["Q2"],
      "file": "sources/07_<slug>.md"
    }
  ],
  "claim_candidates": [
    {
      "claim": "<one-line thesis>",
      "hypothesis": "H1",
      "sources": ["s07", "s09"],
      "source_types": ["Primary", "Industry-media"],
      "primary_source": true,
      "as_of": "2025-Q3 or -",
      "dissent": ["s12"]
    }
  ],
  "contradictions": [
    {
      "about": "<what the sources disagree on, one line>",
      "sides": {"sNN": "<what this source claims>", "sMM": "<what that one claims>"},
      "resolvable": "yes|no|unclear",
      "note": "<if one side is primary/methodologically stronger, say which and why>"
    }
  ],
  "opposition_found": true,
  "opposition_summary": "<if true: what the opposition argues, otherwise null>",
  "gaps": ["<what you searched for but did not find>"],
  "query_performance": [
    {"query": "<exact query string>", "channel": "<channel>", "yield": "used|noise|empty"}
  ]
}

`query_performance`: one row per distinct query you actually ran. `yield`: "used" —
produced at least one source you kept; "noise" — hits, but nothing worth keeping;
"empty" — no relevant hits. The orchestrator uses this to mutate next round's
queries (language switch, operators, terminology) instead of re-running what failed.

`contradictions`: report every disagreement you found, INCLUDING ones where a single
source contradicts several others. Do NOT resolve a disagreement by majority and
report only the winner — a lone regulatory filing outranks three articles retelling
each other, and the ledger, not you, decides. If you found no contradictions at all
in a contested topic, say so explicitly in `gaps` — it usually means you only read
one side.

`dissent` (inside `claim_candidates`): ids of sources you read that CONTRADICT this
claim. Leave `[]` only if you actually looked for opposing sources under this claim.

CONSTRAINTS:
- Maximum 10 sources. Quality over quantity.
- Do not spawn subagents. Stop rule: 5 queries in a row without a new source → return the list of gaps and stop.
- Quotes must be VERBATIM. Do not paraphrase.
- If a source is paywalled / inaccessible — note it in `gaps` and try alternative.
- Do not use bash/curl to bypass WebFetch. The one sanctioned ladder is
  `uv run <SKILL_DIR>/scripts/fetch_source.py <URL> -o <run>/.fetch/NN.md --meta <run>/.fetch/NN.json`
  — it is the STANDARD second step, not an exception. Run it whenever WebFetch
  answers "unable to fetch from ..." OR returns a thin result (<500 chars of main
  text, no quotable passage, block/consent/paywall page): usually a robots.txt
  AI-agent exclusion or a JS-only page, not a dead one. Copy `access:`, `fetched:`,
  `fetch_tier:` and any `fetch_note:` from the metadata into the source frontmatter.
  A thin source (<2 verbatim quotes, or `access: PARTIAL/closed`) is not a
  triangulation leg — validate_phases.py errors on a `triangulated` claim standing
  only on such sources.
- Exit 4 (auth wall / anti-bot) is terminal for the HTML, not for the source. The
  script prints the open doors of that same site — official API, feed, archive
  snapshot — from `<SKILL_DIR>/references/fallback_routes.yaml`. Work that list top-down before
  giving up. Feeds very often survive when the HTML is blocked (stackoverflow HTML
  403, its Atom feed 200). Do not retry the HTML harder.
- A feed gives title, date, summary and URL — NOT the full article. Quote from a
  summary only as a summary, and never present it as a quote from the article.
- A PDF is saved as `.pdf`, not markdown, and the metadata says `content_kind: pdf`.
  Read it with the Read tool (it takes a `pages` range). Preprints and working
  papers arrive as PDFs, so this is the normal academic path, not an edge case.
- Exit 3 means robots.txt closes the path to every client, not just AI agents. Never
  pass `--ignore-robots` yourself — record the URL in `gaps` and move on.
- If both WebFetch and the ladder fail — try an alternative source, don't insist.
- Do NOT return full source text/quotes in your final JSON reply — they belong in
  the files you wrote. Returning them again bloats the main thread's context.
```

### RU template

```
КОНТЕКСТ: Исследуем <главный вопрос>. Workflow — deepdive, режим medium/deep,
ожидается структурированный JSON.

ТВОЯ ПОДТЕМА: <узкая подтема — что ищет ЭТОТ агент, не вся тема>

ТВОЙ ДИАПАЗОН НОМЕРОВ ИСТОЧНИКОВ: s<NN>-s<MM> (например s10-s19). Используй ТОЛЬКО
эти номера для своих файлов — другие агенты параллельно пишут в своих диапазонах.

ГИПОТЕЗЫ ДЛЯ ТЕСТИРОВАНИЯ:
- H1: <опровергаемое утверждение>
- H2: ...

ПОЗИЦИЯ (прочитай до начала):
Источник может быть недостоверным, и у каждого источника есть свой интерес.
Популярность — не доказательство, согласие источников между собой — тоже: десять
страниц могут совпадать потому, что переписали один пресс-релиз. По ходу чтения
специально ищи ПРОТИВОРЕЧИЯ между источниками и спрашивай о каждом: кто произвёл
этот материал, кто за него платил и опубликовал бы он обратный результат.
Найденное фиксируй в полях ниже; не выбирай молча «правильную» сторону.

ЗАДАЧА:
1. Найти 5-10 источников разных типов: первичные, академические, отраслевая медиа,
   общая пресса, экспертные блоги, обсуждения, противоположная позиция.
2. Каждый источник прочитать (WebFetch) и извлечь:
   - Если WebFetch вернул ТОНКО — меньше ~500 знаков основного текста, ни одной
     цитируемой фразы, страница блокировки/консента/paywall — сразу запускать
     лестницу, это штатный шаг, а не исключение:
     `uv run <SKILL_DIR>/scripts/fetch_source.py <URL> -o <run>/.fetch/NN.md --meta <run>/.fetch/NN.json`
     `fetch_tier:` из метаданных перенести во frontmatter источника.
   - 2-4 прямые цитаты (дословно, с указанием раздела/страницы если есть)
   - Автор, дата публикации, тип источника
   - Отношение к каждой гипотезе (supports / contradicts / neutral)
3. Оценить каждый источник САМОМУ по 3 осям 1-5 (отдельного scoring-прохода не
   будет — кто прочитал, тот и скорит):
   - Credibility: 5=первичный/peer-review, 4=отраслевая медиа, 3=качественная пресса,
     2=экспертный блог, 1=форум/анон
   - Recency: 5=<1г, 4=1-3г, 3=3-5л, 2=5-10л, 1=>10л
   - Bias: 5=нейтральный/научный, 4=отраслевая нейтральная, 3=мейнстрим с уклоном,
     2=лоббист, 1=пропаганда
4. КРИТИЧНО: включить ≥1-2 источника с противоположной позицией / критикой
   доминирующего взгляда. Если не нашёл — сказать прямо.
5. ЗАПИСАТЬ полные файлы `sources/<id>_<slug>.md` самому (шаблон в
   `<SKILL_DIR>/references/source_scoring.md`), используя только номера из своего диапазона.
   Обязательно заполнить: `root:` (первоисточник материала), `discovery_path:`
   (`<канал>|<точный запрос>|<язык>` — как ты дошёл до источника), `caveat:`.
   Для источников с ЧИСЛАМИ — ещё `origin_kind:` / `origin_url:` / `data_as_of:`
   (дата ДАННЫХ, не публикации) / `chain_len:`. Не выдумывай значения ради
   заполненности: `unknown` и `-` — валидные ответы, они уводят число в карантин,
   а придуманный `origin_url` отравляет весь вывод.
6. Для каждого тезиса, который подтверждает эта подтема, — кандидат-строка для
   `claims.csv` (текст тезиса, гипотеза, какие sources подтверждают, их типы,
   есть ли среди них primary source).

ФОРМАТ ВЫВОДА — JSON записать в `<run>/agent_reports/<id-подтемы>.json` (строгий
JSON, компактные index-строки, НЕ полные тексты источников — они уже в файле из
шага 5). Финальный ответ в чат ≤15 строк: путь к JSON, счётчики (источников /
claim_candidates / систем), три главных gaps, оппозиция найдена да/нет. JSON в чат
НЕ вставлять: с JSON в ответе было по 19–24 тыс. символов, с лимитом строк — 3–5 тыс.
Содержимое файла:

[см. EN шаблон выше — структура `source_index` + `claim_candidates` та же]

ОГРАНИЧЕНИЯ:
- Максимум 10 источников. Качество важнее количества.
- Субагентов не спавнить. Стоп-правило: 5 запросов подряд без нового источника → вернуть список gaps и остановиться.
- Цитаты ДОСЛОВНЫЕ. Не пересказ.
- Если источник за paywall — в `gaps`, искать альтернативу.
- НЕ использовать произвольный bash/curl в обход WebFetch. Единственная санкционированная лестница:
  `uv run <SKILL_DIR>/scripts/fetch_source.py <URL> -o <run>/.fetch/NN.md --meta <run>/.fetch/NN.json`
  — это ШТАТНЫЙ второй шаг, не исключение. Запускать и когда WebFetch ответил
  «unable to fetch from …», и когда вернул тонкий результат (<500 знаков основного
  текста, нет цитируемой фразы, страница блокировки/консента/paywall): обычно это
  robots-исключение для AI-агентов или JS-only страница, а не мёртвая. `access:`,
  `fetched:`, `fetch_tier:` и `fetch_note:` из метаданных перенести во frontmatter.
  Источник без 2 дословных цитат не пишется вовсе; если лестница упёрлась в
  auth-волл/анти-бот — писать с `access: closed` и только тем, что дал сниппет, и
  плечом триангуляции он быть не может (validate_phases.py даёт error).
- Код 4 (auth-волл / анти-бот) — терминально для HTML, не для источника. Скрипт сам
  печатает открытые двери того же сайта (API, фид, архив) из `<SKILL_DIR>/references/fallback_routes.yaml` —
  идти по списку сверху вниз. Фид часто жив, когда HTML мёртв: у stackoverflow HTML
  403, а его Atom-фид 200. HTML сильнее не долбить.
- Фид даёт заголовок, дату, аннотацию и URL — НЕ полный текст. Цитату из аннотации
  помечать как аннотацию, не выдавать за цитату из статьи.
- PDF сохраняется как `.pdf`, не как markdown, и в метаданных стоит `content_kind: pdf`.
  Читать штатным `Read` с диапазоном `pages`. Препринты и рабочие бумаги приезжают
  PDF-ами — это основной академический путь, не краевой случай.
- Код 3 — robots закрывает путь всем клиентам, не только AI. `--ignore-robots` самому
  НЕ ставить: URL в `gaps` и дальше.
- НЕ возвращать полные цитаты/тексты источников в финальном JSON — они уже в
  записанных файлах, повторный возврат раздувает контекст главного потока.
```

## После возврата суб-агентов — что делает главный поток

1. **Парсинг JSON.** Читай `agent_reports/<id>.json` python-скриптом (`json.load`), в контекст — только счётчики, не сам файл. Нет файла или мусор — попроси агента перезаписать файл, не интерпретируй сам. Ожидай `source_index` (компактные строки) + `claim_candidates` — НЕ полные тексты источников (их агент уже записал сам, см. выше).

2. **Дедупликация по URL — и замер `overlap_rate` (не выбрасывай дубль молча).** Если два суб-агента нашли один и тот же URL — это ОДИН источник: оставить файл с лучшим scoring, вторую запись пометить дублем в `sources.csv`. Но сам факт совпадения — **самая ценная диагностика раунда, и она пропадает, если дубль просто удалить**.

   Агенты низкодисперсны: их различают только контекст, скаффолд и модель. Совпали все три — совпадут и действия (Anthropic Frontier Red Team, 13.08.2026: 18 из 30 агентов создали ветку с одинаковым именем, ни одному этого не задавали). Твои fetch-агенты получают один шаблон промпта, одну модель и один поисковый индекс — различаются только подтемой. Поэтому:

   ```
   overlap_rate = (URL, найденные >1 агентом) / (уникальные URL раунда)
   ```

   Запиши его в `plan.md` секцию 15 (notes) за каждый раунд и трактуй так:
   - **overlap_rate > 0.3** — агенты искали одинаково, разнообразие источников фиктивное. **Обязательна query-мутация** в следующем раунде (RU↔EN, смена канала, другая терминология) плюс разведение агентов по осям поиска, а не только по подтемам.
   - **overlap_rate < 0.05 при высоком novelty** — здоровое разведение, продолжай как есть.
   - **overlap_rate = 0 на всех раундах** — проверь, что агенты вообще ищут в пересекающихся областях; ноль пересечений при широкой теме чаще означает, что каждый агент нашёл случайную выборку, а не что они хорошо разведены.

   Совпадение URL между агентами — сигнал конформизма, а не «удачная валидация находки».

3. **Мёрж `sources.csv`** из всех `source_index` — файлы уже на диске (агенты сами их записали в своих диапазонах), главный поток здесь только сводит индекс, не переписывает `sources/NN.md`.

4. **Заполнение `claims.csv`** из всех `claim_candidates` (Phase 5 — см. `source_scoring.md` раздел claims-ledger). Смёржить дублирующиеся claim'ы от разных агентов (если тезис один и тот же — объединить sources/source_types в одну строку).

5. **Проверка периметра записи (машинная, не на доверии).** Диапазон номеров держится только текстом промпта — у агента есть `Write` и изолированный контекст. После возврата суб-агентов сверь фактическое содержимое `sources/` с выданными диапазонами:

   ```bash
   ls research/<slug>/sources/ | grep -oE '^[0-9]+' | sort -n | uniq
   ```

   Файл с номером вне всех выданных диапазонов ⇒ агент вышел за периметр ⇒ его результат невалиден: файл не принимается в `sources.csv`, строка помечается в `plan.md` §15, при повторе — агент перезапускается с сужённой задачей. Это проверяется и на finish-up (`validate_phases.py`). Границу должен держать механизм, а не вежливость модели.

6. **Проверка покрытия:**
   - Сколько типов источников? (нужно ≥4)
   - Найдена ли оппозиция? (нужна минимум одна)
   - Все ли гипотезы получили evidence? (нужно ≥3 источника на гипотезу)
   - Сколько строк `claims.csv` НЕ triangulated? → это вход в gap-волну (см. `phases/p5_claims.md` «Gap-волна»).

7. **Пересборка окна раунда — `state.md`** (medium/deep; правило в `phases/p4_search.md`,
   «Round workspace»). Всё выше главный поток проделал в контексте, где уже лежат
   итоги всех агентов этого раунда — а решение о следующем раунде принимается в том же
   окне, ещё и поверх предыдущих. Поэтому перед следующим раундом окно
   **пересобирается**: `state.md` ПЕРЕЗАПИСЫВАЕТСЯ (не дописывается) из итогов, а
   планирование идёт по нему.

   ```markdown
   ---
   round: 3
   mode: medium
   ---
   ## Known
   - Q1 закрыт: ставка 4.2% [s03][s07] (CL2, triangulated)
   - Q2 частично: есть 2024, нет primary (CL5, single-root)
   - Q3 закрыт отрицательно: реестр не ведётся с 2019 [s11]
   ## Gaps
   - Q2: primary-реестр не найден, канал `registry` не отработан
   - Q4: пусто на EN, RU-терминология не пробована
   ## Next
   - раунд 3: 2 агента — registry по Q2 (s20-s24), RU-мутация по Q4 (s25-s29)
   ```

   Правила:
   - **Известное — статусами, не содержанием.** Строка `Known` ссылается на
     `claim_id`/`[sNN]`; содержание живёт в `sources/` и `evidence/`. Как только в
     `state.md` появляются абзацы из источников, он превращается во второй транскрипт
     — ровно то, от чего пересобирается окно. Бюджет ≤6 КБ, машинно проверяется на
     finish-up (`validate_phases.py`: >12 КБ — ошибка).
   - **Отрицательный результат — тоже `Known`.** «Реестр не ведётся» закрывает
     подвопрос; выпав из окна, он вернётся как «надо поискать реестр».
   - **`Gaps` — единственный канал в следующий раунд.** Агент раунда N+1 получает
     свою дыру, НЕ чужие `Known`: запрет на обмен находками (см. Антипаттерны ниже)
     пересборкой окна не отменяется. Экономия контекста оркестратора не должна
     открывать канал конформизма.
   - **`Next` пишется с диапазонами id** — тогда периметр записи (шаг 5) проверяем и
     на следующем раунде.
   - История раундов не теряется: она в `deviations.md` (триггеры, novelty,
     circuit breaker) и `plan.md` §15 (overlap_rate, наблюдения). `state.md` — окно, а
     не журнал.

## Антипаттерны

- ❌ Запустить 1 суб-агента в medium — не даёт параллелизма, добавляет overhead. Делай в основном потоке.
- ❌ Дать слишком общий промпт «ищи про X» — вернётся жидкая выжимка. Подтема должна быть УЗКОЙ.
- ❌ Запустить суб-агентов последовательно (Agent call → ждать → следующий). Только параллельно в одном сообщении.
- ❌ Принимать выжимку суб-агента как финал без проверки. Дедуплицируй URLs и проверь scoring.
- ❌ Использовать `Explore`/`explore-haiku` когда агенту нужно писать `sources/NN.md` — они read-only, не сохранят файл. Для fetch+save всегда `deepdive-fetcher`.
- ❌ Не назначить агенту диапазон номеров ПЕРЕД launch — без этого параллельная запись рискует коллизией id.
- ❌ Просить суб-агента вернуть полные тексты/цитаты источников в JSON-ответе — раздувает контекст главного потока. Полный текст живёт в файле, в главный поток идёт только index-строка.
- ❌ Оставить в промпте агента формат «строгий JSON в ответе» без лимита размера ответа: 4 агента без лимита вернули 19–24 тыс. символов каждый (~41k токенов главного потока). JSON — в файл, в чат ≤15 строк.
- ❌ Пропустить требование «найди оппозицию» — суб-агенты по умолчанию ищут confirmation, не contradiction.
- ❌ **Разводить агентов ТОЛЬКО по подтемам.** Одинаковый шаблон + одна модель + один язык = одна поисковая траектория, и триангуляция получает коррелированные голоса. Разводи ещё и по оси поиска: агент A — англоязычная академия и препринты, B — RU-сегмент, локальные регуляторы и отраслевые ассоциации, C — практики (форумы, issue-трекеры, обсуждения), D — первичные реестры и отчётность. Тогда пересечение находок — сигнал настоящей независимости, а не артефакт одинакового промпта.
- ❌ **Передавать во второй раунд находки соседей.** Соблазн понятен, но наблюдаемость чужих действий сама по себе канал координации: в эксперименте Anthropic агенты продолжили сговор после удаления всех каналов связи, синхронизируясь через публичную доску. Дать агентам видеть находки друг друга — построить такую доску своими руками и добить остатки независимости. Делись только ДЫРАМИ: «подвопросы Q3, Q7 не закрыты; по Q5 не найдено ни одной оппозиции».
- ❌ Молча выбрасывать дубликаты URL между агентами (см. `overlap_rate` ниже) — это стирает единственный прямой замер конформизма.

## Когда НЕ запускать суб-агентов

- **shallow** режим — 5-7 источников быстрее собрать в основном диалоге.
- **Узкая тема** — если не дробится на 2+ подтемы, нет смысла.
- **Тема в проектном контексте, требующая чтения многих файлов проекта** — суб-агент не видит локальные файлы так же легко; основной диалог справится быстрее.
- **Update-режим с маленькой дельтой** — если нужно докопать 3-5 источников, основной поток справится.
