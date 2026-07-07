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

TASK:
1. Search using the channels above. For 5-10 sources total across all channels.
   Different source types: Primary, Academic, Industry-media, General-media,
   Expert-blog, Forum, Opposition.
2. For each source — read it (WebFetch) and extract:
   - 2-4 key direct quotes (verbatim, with location/page if possible)
   - Author, publication date, source type
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
      "primary_source": true
    }
  ],
  "opposition_found": true,
  "opposition_summary": "<if true: what the opposition argues, otherwise null>",
  "gaps": ["<what you searched for but did not find>"]
}

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

2. **Дедупликация по URL.** Если два суб-агента нашли один и тот же URL под разными id (не должно случиться при непересекающихся диапазонах, но проверяй) — это ОДИН источник, оставить файл с лучшим scoring, вторую запись пометить дублем в `sources.csv`.

3. **Мёрж `sources.csv`** из всех `source_index` — файлы уже на диске (агенты сами их записали в своих диапазонах), главный поток здесь только сводит индекс, не переписывает `sources/NN.md`.

4. **Заполнение `claims.csv`** из всех `claim_candidates` (Phase 5 — см. `source_scoring.md` раздел claims-ledger). Смёржить дублирующиеся claim'ы от разных агентов (если тезис один и тот же — объединить sources/source_types в одну строку).

5. **Проверка покрытия:**
   - Сколько типов источников? (нужно ≥4)
   - Найдена ли оппозиция? (нужна минимум одна)
   - Все ли гипотезы получили evidence? (нужно ≥3 источника на гипотезу)
   - Сколько строк `claims.csv` НЕ triangulated? → это вход в gap-волну (Phase 4.5, см. `workflow.md`).

## Антипаттерны

- ❌ Запустить 1 суб-агента в medium — не даёт параллелизма, добавляет overhead. Делай в основном потоке.
- ❌ Дать слишком общий промпт «ищи про X» — вернётся жидкая выжимка. Подтема должна быть УЗКОЙ.
- ❌ Запустить суб-агентов последовательно (Agent call → ждать → следующий). Только параллельно в одном сообщении.
- ❌ Принимать выжимку суб-агента как финал без проверки. Дедуплицируй URLs и проверь scoring.
- ❌ Использовать `Explore` когда агенту нужно писать `sources/NN.md` — Explore read-only, не сохранит файл. Для fetch+save всегда `general-purpose`.
- ❌ Не назначить агенту диапазон номеров ПЕРЕД launch — без этого параллельная запись рискует коллизией id.
- ❌ Просить суб-агента вернуть полные тексты/цитаты источников в JSON-ответе — раздувает контекст главного потока. Полный текст живёт в файле, в главный поток идёт только index-строка.
- ❌ Пропустить требование «найди оппозицию» — суб-агенты по умолчанию ищут confirmation, не contradiction.

## Когда НЕ запускать суб-агентов

- **shallow** режим — 5-7 источников быстрее собрать в основном диалоге.
- **Узкая тема** — если не дробится на 2+ подтемы, нет смысла.
- **Тема в проектном контексте, требующая чтения многих файлов проекта** — суб-агент не видит локальные файлы так же легко; основной диалог справится быстрее.
- **Update-режим с маленькой дельтой** — если нужно докопать 3-5 источников, основной поток справится.
