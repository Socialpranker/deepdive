# Subagents v2 — параллельный поиск через Agent tool

Применяется в режимах **medium** (2–3 суб-агента) и **deep** (4–5).

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

Суб-агент (subagent_type=general-purpose, свой диапазон NN):
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

- **`general-purpose`** — дефолт для fetch+save (Phase 4.1). Нужен `Write`, чтобы агент сам сохранял `sources/NN.md` в своём диапазоне номеров, а не передавал полные тексты обратно в главный поток. Каждому агенту — явный диапазон: агент №1 → `s01-s09`, №2 → `s10-s19`, и т.д. (см. промпт-шаблон ниже, поле `SOURCE ID RANGE`).
- **`Explore`** — только для чистой discovery-разведки БЕЗ сохранения файлов (например, Phase 3.5 capability discovery или предварительная разведка «сколько вообще есть материала» до того как решили дробить на подтемы). Как только агенту нужно писать `sources/NN.md` — это `general-purpose`, не `Explore`.
- **`Plan`** — НЕ для поиска. В deep-research не использовать.

## Какую модель выбрать (model routing)

**Обязательно читай `model_routing.md`** перед launch sub-agents — там matrix фаза × подзадача → модель.

Краткая выдержка для Phase 4.1 (launch sub-agents):

| Тип подзадачи sub-agent'а | Модель | Effort |
|---|---|---|
| Web search + metadata (web-general/news/forum) | `haiku` | low |
| Read long source + extract quotes | `sonnet` | low |
| Academic / preprint-servers | `sonnet` | low |
| API-direct (curl + jq) | `haiku` | low |
| Code analysis (clone + grep) | `sonnet` | medium |
| Heavy reasoning subtask | `opus` | medium |

**Default если не уверен** → `sonnet` / `low`. Это safe middle ground.

**Параметр `model`** передаётся прямо в `Agent` tool:

```
Agent({
  subagent_type: "general-purpose",   // fetch+save нужен Write, см. выше
  model: "haiku",    // ← важно: явный выбор
  description: "...",
  prompt: "..."
})
```

Если `model:` не передан — sub-agent наследует модель родителя (обычно Sonnet) — для дешёвых задач это переплата.

## Параллелизм

В одном сообщении ассистента — ВСЕ Agent calls одновременно.

Если суб-агентов 4+ — запускай с `run_in_background: true`:
- Реальный параллелизм, не очередь.
- Уведомления при завершении каждого — не нужно polling.
- Можно начинать сборку результатов по мере поступления.

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
CONTEXT: We are researching <main_question>. This is the deep-research workflow,
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

See channels.md for query patterns, paywall fallback protocols, limitations.

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
4. CRITICAL: include at least 1-2 sources representing OPPOSITION or CRITICISM
   of the dominant view in this subtopic. If you cannot find any — say so explicitly.
5. WRITE the full source file yourself: `sources/<id>_<short-slug>.md` using the
   template in `source_scoring.md`, with complete frontmatter (channel, access,
   scores, subquestion_ids) and verbatim quotes. Use ONLY ids from your assigned
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

OUTPUT FORMAT — return ONLY compact index rows to the main thread, NOT full source
text (full text already lives in the files you wrote in step 5). Strict JSON, no
commentary outside JSON:

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
- Quotes must be VERBATIM. Do not paraphrase.
- If a source is paywalled / inaccessible — note it in `gaps` and try alternative.
- Do not use bash/curl to bypass WebFetch restrictions.
- If WebFetch fails for a URL — try alternative source, don't insist.
- Do NOT return full source text/quotes in your final JSON reply — they belong in
  the files you wrote. Returning them again bloats the main thread's context.
```

### RU template

```
КОНТЕКСТ: Исследуем <главный вопрос>. Workflow — deep-research, режим medium/deep,
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
   `source_scoring.md`), используя только номера из своего диапазона.
   Обязательно заполнить: `root:` (первоисточник материала), `discovery_path:`
   (`<канал>|<точный запрос>|<язык>` — как ты дошёл до источника), `caveat:`.
   Для источников с ЧИСЛАМИ — ещё `origin_kind:` / `origin_url:` / `data_as_of:`
   (дата ДАННЫХ, не публикации) / `chain_len:`. Не выдумывай значения ради
   заполненности: `unknown` и `-` — валидные ответы, они уводят число в карантин,
   а придуманный `origin_url` отравляет весь вывод.
6. Для каждого тезиса, который подтверждает эта подтема, — кандидат-строка для
   `claims.csv` (текст тезиса, гипотеза, какие sources подтверждают, их типы,
   есть ли среди них primary source).

ФОРМАТ ВЫВОДА — вернуть в главный поток ТОЛЬКО компактные index-строки, НЕ полные
тексты источников (полный текст уже в файле из шага 5). Строгий JSON:

[см. EN шаблон выше — структура `source_index` + `claim_candidates` та же]

ОГРАНИЧЕНИЯ:
- Максимум 10 источников. Качество важнее количества.
- Цитаты ДОСЛОВНЫЕ. Не пересказ.
- Если источник за paywall — в `gaps`, искать альтернативу.
- НЕ использовать bash/curl для обхода ограничений WebFetch.
- НЕ возвращать полные цитаты/тексты источников в финальном JSON — они уже в
  записанных файлах, повторный возврат раздувает контекст главного потока.
```

## После возврата суб-агентов — что делает главный поток

1. **Парсинг JSON.** Если суб-агент вернул мусор — попроси переслать в JSON, не интерпретируй сам. Ожидай `source_index` (компактные строки) + `claim_candidates` — НЕ полные тексты источников (их агент уже записал сам, см. выше).

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
   - Сколько строк `claims.csv` НЕ triangulated? → это вход в gap-волну (Phase 4.5, см. `workflow.md`).

7. **Пересборка окна раунда — `state.md`** (medium/deep; правило в `workflow.md`,
   «Round workspace»). Всё выше главный поток проделал в контексте, где уже лежат
   JSON всех агентов этого раунда — а решение о следующем раунде принимается в том же
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
- ❌ Использовать `Explore` когда агенту нужно писать `sources/NN.md` — Explore read-only, не сохранит файл. Для fetch+save всегда `general-purpose`.
- ❌ Не назначить агенту диапазон номеров ПЕРЕД launch — без этого параллельная запись рискует коллизией id.
- ❌ Просить суб-агента вернуть полные тексты/цитаты источников в JSON-ответе — раздувает контекст главного потока. Полный текст живёт в файле, в главный поток идёт только index-строка.
- ❌ Пропустить требование «найди оппозицию» — суб-агенты по умолчанию ищут confirmation, не contradiction.
- ❌ **Разводить агентов ТОЛЬКО по подтемам.** Одинаковый шаблон + одна модель + один язык = одна поисковая траектория, и триангуляция получает коррелированные голоса. Разводи ещё и по оси поиска: агент A — англоязычная академия и препринты, B — RU-сегмент, локальные регуляторы и отраслевые ассоциации, C — практики (форумы, issue-трекеры, обсуждения), D — первичные реестры и отчётность. Тогда пересечение находок — сигнал настоящей независимости, а не артефакт одинакового промпта.
- ❌ **Передавать во второй раунд находки соседей.** Соблазн понятен, но наблюдаемость чужих действий сама по себе канал координации: в эксперименте Anthropic агенты продолжили сговор после удаления всех каналов связи, синхронизируясь через публичную доску. Дать агентам видеть находки друг друга — построить такую доску своими руками и добить остатки независимости. Делись только ДЫРАМИ: «подвопросы Q3, Q7 не закрыты; по Q5 не найдено ни одной оппозиции».
- ❌ Молча выбрасывать дубликаты URL между агентами (см. `overlap_rate` ниже) — это стирает единственный прямой замер конформизма.

## Когда НЕ запускать суб-агентов

- **shallow** режим — 5-7 источников быстрее собрать в основном диалоге.
- **Узкая тема** — если не дробится на 2+ подтемы, нет смысла.
- **Тема в проектном контексте, требующая чтения многих файлов проекта** — суб-агент не видит локальные файлы так же легко; основной диалог справится быстрее.
- **Update-режим с маленькой дельтой** — если нужно докопать 3-5 источников, основной поток справится.
