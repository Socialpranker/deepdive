# Workflow — детали <!--gen:count:phases-->13<!--/gen--> фаз

Дополнение к SKILL.md. Здесь — пошаговые инструкции и шаблоны. Читать в начале medium/deep ресёрча.

## Фаза 1. Reframing

**Model:** `opus` / `high` (см. `model_routing.md`). Качество reframing'а определяет весь ресёрч — не экономить.

Цель: убедиться, что ищем правильное. Большая часть плохих ресёрчей — плохие вопросы, не плохой поиск.

**Шаги:**
1. Перепиши вопрос своими словами: «Я понимаю задачу так: …». Это проверка совпадения картин.
2. Собери **Decision Spec** (3 обязательных поля: решение глагол+объект+срок / потребитель→его следующий шаг / ≥1 if-then вилка «покажет X → делаю A»). Ни одной вилки ⇒ честный даунгрейд в shallow «любопытство». Проверь `~/.claude/research/applications_ledger.csv` на паттерн непримененных прогонов. Детали — `question_reframing.md` п.2.
3. Сформулируй 2–4 опровергаемые гипотезы. Не «изучить тему» (это не гипотеза), а «X лучше Y по Z» (опровергаемо).
4. Сформулируй критерии остановки. Без них ресёрч уходит в бесконечность.
5. Если есть мутность — задай ≤3 уточняющих вопроса (пятый критерий триажа — вопрос «что ты сделаешь иначе в зависимости от ответа?» — обязателен, если вилки не выводятся). Если пользователь отвечает «не знаю» — двигайся с явным допущением.

См. `question_reframing.md` для шаблонов и push-back сценариев.

## Фаза 2. Genre & block selection

**Model:** `sonnet` / `medium`.

После reframing, до plan'а — определяем какой тип отчёта собираем.

**Шаги:**

1. Прочитай `genres.md` — там эвристика выбора жанра по сигналам в вопросе.
2. Применяй эвристику:
   - «как устроен» → explainer
   - «что выбрать X или Y» → decision
   - «карта», «кто делает» → landscape
   - «правда ли», «работает ли» → validation
   - открытый, серия вопросов → qa
   - «по показателям», смесь, нестандартное → custom

3. Для standard жанра — возьми пресет блоков из `genres.md`.

4. Для custom — собери список блоков:
   - Базовая обвязка: `tldr`, `scope` (если границы важны), `counter-arguments`, `open-questions`, `next-research`, `map-of-sources`, `metadata`.
   - Эвристика по сигналам в вопросе (см. `genres.md` таблицу «Эвристика подбора блоков»).
   - Если вопрос гибридный (e.g. «как устроен + что выбрать») — комбинируй блоки из обоих жанров.

5. Объяви пользователю ОДНОЙ строкой:
   ```
   "Жанр: <genre>. Блоки: <list>. Ок?"
   ```
   Например:
   ```
   "Жанр: custom (конкуренты по показателям). Блоки: tldr, scope, data-table,
    profile-card×N, trends, counter-args, open-q, next-research, sources, metadata. Ок?"
   ```

6. Если пользователь правит — обнови набор.

7. Зафиксируй финальный набор в `plan.md` (см. Фаза 3).

**Не загружай все категорийные файлы `blocks/*.md` сразу.** Только те что нужны для выбранных блоков — после фазы plan.

## Фаза 3. Plan

**Model:** `opus` / `medium`. Архитектурное решение, документирует все будущие выборы.

Записывай в файл `<root>/<slug>/plan.md`. План — документ, не разговор. Если в чате — потом потеряется.

**Структура plan.md** — 5 секций: HEADER → SCOPE → STRUCTURE → EXECUTION → TRACKING.

**Шаблон plan.md** (frontmatter + все секции 0–16, дословно) — `references/plan_template.md`. Читать при входе в Фазу 3, не раньше.

**Заметки по использованию шаблона:**

1. **Frontmatter critical** — машинно-читаемый. Не сокращай поля.
2. **User context (секция 0)** — заполни ДО reframing'а или сразу после. Без него остальное в воздухе.
3. **Acceptance criteria (секция 4)** — самое важное. Если не можешь сформулировать что считается готово — не начинай ресёрч.
4. **Подтемы ↔ блоки mapping (секция 11)** — без него агенты собирают вслепую.
5. **Notes during research (секция 15)** — обновляй в процессе, не в конце. Это документация решений.
6. **Update changelog (секция 16)** — заполнить ТОЛЬКО для update.

**Минимальный plan.md** (если shallow и тема маленькая) — можно опустить секции:
- 0 (если очевидно)
- 5 (если нет existing)
- 10 (если нет obvious risks)
- 11 (если одна подтема)
- 16 (если initial)

Но **обязательны:** 2, 3, 4, 7, 8, 9, 12, 13, 14.

## Фаза 3.5. Capability Discovery

**Model:** `sonnet` / `low`. Механический проход по env vars и таблицам.

**Опциональна** для shallow. **Рекомендуется** для medium. **Обязательна** для deep.

Между планированием и запуском поиска — sanity check: что у нас реально доступно?

См. `capability_discovery.md` для детального workflow. Краткая version:

### Step 1: Audit env vars

Проверь существование env vars для API ключей запланированных в plan.md секции 12:

```
$FRED_API_KEY, $GITHUB_TOKEN, $NEWSAPI_KEY, ...
```

Полный список — `capability_discovery.md` секция "Step 1".

### Step 2: Map subtopics to capabilities

Для каждой подтемы → таблица: planned source × status (`authenticated` / `open-no-auth` / `fallback` / `unavailable`).

### Step 3: Discover unknown gaps

Если планы покрывают не всю тему — fall back на `awesome_lists_registry.md` для discovery:

```
для подтемы X:
  если не нашёл в моём каталоге → найти upstream awesome-list
  → WebFetch его README
  → identify 1-3 candidates → add as ad-hoc в plan.md
```

### Step 4: Report to user

Сводный отчёт:
- ✅ Available: [list]
- ⚠ Fallback: [list]
- ❌ Unavailable: [list]
- ❓ Ad-hoc from upstream: [list]
- Suggest env vars: [list]

User confirms continue.

### Step 5: Update plan.md

Дополнить `plan.md` секцию 12 (Information sourcing strategy) per-subtopic блоком "Capabilities check":

```markdown
**Capabilities check (Phase 3.5):**
- ✅ FRED API: authenticated, will use directly
- ⚠ Brave Search: no key → fallback to standard WebSearch
- ❓ Niche topic — using ad-hoc API from public-apis registry
```

## Фаза 4. Поиск

**Model:** главный поток `sonnet` / `medium`. Sub-agents — **разные модели** по типу подзадачи (см. `model_routing.md` секция «Routing для sub-agents»): web/news/api-direct → `haiku`, academic/long-source → `sonnet`, heavy reasoning subtask → `opus`.

**Phase 4 is an orchestrator-driven loop, not a single salvo.** Round 1 executes the
approved plan (Phase 4.0 dispatch). After *every* round the orchestrator evaluates the
aggregated results and may spend a bounded *deviation* to launch another round. The
plan stays authoritative as the starting point; deviations are bounded and recorded.

**Phase 4 = 4 шага в строгом порядке (Round 1):** Dispatch → Launch → Fetch → Save. Не пропускай Dispatch — без него Launch будет хаотичным.

### 4.0 Source Dispatch (НОВЫЙ обязательный шаг)

**До запуска суб-агентов** прогони каждый подвопрос из plan.md секции 11 (Подтемы ↔ Блоки mapping) через `source_dispatch.md`:

1. Открой `source_dispatch.md` → найди в Matrix строку под сигнал подвопроса
2. Запиши **primary / secondary / fallback каналы** в `plan.md` секцию 12 в формате который указан в конце `source_dispatch.md`
3. Если тема узкая или не матчится — выполни Discovery patterns (GitHub topics, awesome-lists registry, HuggingFace, PyPI/npm, data portals) и **запиши что нашёл** в секцию «Discovery executed»
4. Если decomposition recipe из `source_dispatch.md` добавляет подвопросы которых нет в plan.md — **верни в Phase 3** и расширь декомпозицию, потом продолжай

**Output 4.0:** заполненная секция 12 plan.md с per-subquestion sourcing strategy. Без этого 4.1 не запускается.

### 4.1 Launch sub-agents

Используй каналы из `channels.md` (29 каналов) и stat-источники из `stat_sources/` (категории по теме). Конкретные API endpoints из `api_sources/`. Стратегия уже зафиксирована в `plan.md` секция 12 на шаге 4.0.

См. `subagents_v2.md` — паттерн суб-агентов для medium/deep.

Для **shallow** — главный поток сам делает WebSearch+WebFetch и пишет файлы `sources/NN.md` (без суб-агентов).

Каждый суб-агент получает из plan.md:
- `subquestion_id` (Q1, Q2, ...)
- `primary_channel`, `secondary_channel`, `fallback_channel` — из dispatch шага
- Конкретные `stat_sources_files: [...]` и `api_endpoints: [...]` для своего подвопроса
- Конкретные queries (из dispatch)
- Минимум 2 разнотипных канала на подвопрос (триангуляция)

### 4.2 Fetch & Dedup

- Используй встроенные WebFetch и WebSearch.
- Для API из `api_sources/` — Bash + curl + jq если ответ большой, иначе WebFetch.
- Если WebFetch вернул «unable to fetch from …» — это чаще всего robots.txt-исключение для AI-агентов, а не мёртвая страница. Прежде чем списать источник в `gaps`, прогони его через fetch ladder — `references/fetch_ladder.md` (двухтирный `fetch_source.py`, коды выхода, фид-фолбэк, PDF-обработка).
- Если источник за paywall — paywall fallback protocol в `channels.md` (preprint → archive → researchgate → … → Sci-Hub как last resort с disclaimer).
- Покрывай ≥3 канала разных типов для diversity of methodology (требование Phase 5 триангуляции).
- Dedup по URL и по содержанию (если две ссылки ведут на один и тот же отчёт — оставь одну с лучшим scoring).

#### Fetch ladder — когда WebFetch не достаёт

Двухтирный `fetch_source.py` (http → browser), коды выхода, фид-фолбэк вместо мёртвого
HTML, PDF-обработка, `main_content_only` как санитайзер prompt injection — полностью
`references/fetch_ladder.md`. Читать, когда WebFetch реально не отдал контент, не заранее.

### 4.3 Save sources

- Каждый найденный источник → отдельный файл в `sources/SNN_<slug>.md` с заполненным frontmatter: `channel:`, `access:`, `subquestion_ids: [Q1, Q3]`, `credibility/recency/bias`.
- Никаких «соберём в конце» — пиши сразу после dedup.
- Если источник покрывает несколько подвопросов — указывай в frontmatter все через `subquestion_ids:`, а не дублируй файл.

**Output Phase 4 (Round 1):** заполненная папка `sources/` + обновлённый `sources.csv` + flags «open gaps» в plan.md для подвопросов где не удалось набрать ≥3 разнотипных источников.

### Round structure

1. **Round 1 = the plan.** Run Phase 4.0 (Source Dispatch) → Phase 4.1 (N sub-agents
   following the fixed dispatch) → 4.2 (dedup) → 4.3 (save sources). This always runs.
2. **Each sub-agent emits a `signals` block** in its JSON (in addition to sources):

   ```json
   {
     "subquestion_id": "Q3",
     "round": 1,
     "sources": [ ... ],
     "signals": {
       "empty_result":       { "fired": true,  "detail": "0 relevant hits on `academic`" },
       "unexpected_finding": { "fired": false, "detail": null },
       "contradiction":      { "fired": false, "detail": null },
       "citation_lead":      { "fired": true,  "detail": "S07 cites Gartner 2024, no link" }
     }
   }
   ```

   Sub-agents signal **generously** (high recall). They report observations; they do
   NOT decide to deviate.

3. **Cheap goal-check (after every round, `haiku` / low — before the Opus pass):** a
   non-thinking evaluator scores each subquestion against its *goal*, not its sources.
   For every `subquestion_id` it emits a one-line `goal_status`:

   ```json
   { "subquestion_id": "Q3", "goal_status": "partial",
     "missing": "have the 2024 figure, no primary source and no pre-2020 baseline to compare" }
   ```

   `goal_status ∈ {met, partial, unmet}`; `missing` is a concrete gap phrase when not
   `met`. This is deer-flow's non-thinking evaluator: a Haiku pass that *names the gap*
   so the expensive Opus evaluation below works from a diagnosis instead of deriving one
   from scratch, and so the next round's dispatch targets the named gap rather than
   re-searching the whole subquestion. It decides nothing — it only labels. The Opus
   pass and the circuit breaker read these labels; a round where every subquestion is
   `met` and no trigger is justified ends the loop.

4. **Orchestrator evaluation (after every round, `strong` tier / Opus):**
   - Aggregate all sub-agent JSON for the round.
   - **Cross-agent contradiction scan** (cheap tier): scan the whole pool for sources
     that conflict — this catches contradictions no single sub-agent can see (each
     sees only its own subquestion).
   - Opus reviews flags + scan + aggregated output and selects which triggers are
     *justified* (strict precision — a sub-agent's `unexpected_finding` is a candidate,
     not an automatic spend).
   - **Trajectory sanity-check (cheap tier):** before pursuing an `unexpected_finding`
     or `citation_lead`, verify the *intermediate claim* that triggered it is itself
     backed by a real source. A round seeded by an unsupported intermediate claim
     compounds hallucination downstream (trajectory error) — drop the trigger and flag
     the originating source instead of spawning a search on a phantom.
   - **Query mutation (cheap tier):** aggregate the sub-agents' `query_performance`
     rows (see `subagents_v2.md`). For subquestions whose queries came back
     noise/empty, the next round's dispatch mutates the wording deliberately —
     RU↔EN language switch (Russian-relevant topics are invisible to English-only
     queries and vice versa), operators (`site:`, `filetype:pdf` for reports, quoted
     exact phrases, date ranges), practitioner vs academic terminology — instead of
     re-running the wording that already failed.
   - **Novelty rate (saturation signal):** share of the round's take that is
     genuinely new to the pool — new URL AND new `root:` AND new claim. Record the
     number in `deviations.md`. Novelty below ~20% is saturation: prefer ending the
     loop over spawning another round even if a justified trigger remains (record it
     as `not_pursued: saturation`). This is the graded companion to the binary
     no-progress circuit breaker below.
   - For each justified trigger, if budget for its class remains AND depth < limit:
     classify cheap/expensive, debit the counter, write a `deviations.md` record,
     and launch the next round. Otherwise write a `not_pursued` record.
5. **The loop ends** when no justified trigger remains, OR both budgets are exhausted,
   OR the depth limit is reached, OR the novelty rate signals saturation (step 4),
   OR the **no-progress circuit breaker** fires (see below). Then proceed to Phase 5.

### Round workspace — пересборка, а не накопление (`state.md`, medium/deep)

Суб-агенты пишут в файлы, в главный поток идут только index-строки — но оркестратор
между раундами продолжает тащить всю историю (JSON агентов, goal-check, триггеры,
скан противоречий) и к третьему раунду решает «куда дальше» в окне, где прошлые
раунды вытеснили текущую инструкцию.

**Правило:** перед каждым следующим раундом главный поток ПЕРЕЗАПИСЫВАЕТ (не
дописывает) `state.md` — `## Known` (статусы подвопросов ссылками на
`claim_id`/`[sNN]`) · `## Gaps` · `## Next`, бюджет ≤6 КБ — и планирует раунд по
нему, а не по транскрипту. Архив никуда не исчезает: `sources/`, `deviations.md`,
`plan.md` §15. Не отменяет запрет на обмен находками: агент следующего раунда
получает свою дыру из `Gaps`, не чужие `Known`. Шаблон и анти-паттерны —
`subagents_v2.md` («Round workspace»).

### Snowball pass (medium/deep — после Round 1, до deviation-раундов)

Keyword-поиск находит то, что хорошо индексируется, а не то, что канонично. Цепочки
цитирований достают источники, которые не отдаст никакой запрос. После 4.3 Round 1:

1. Возьми топ-K источников по `total` (K=2 medium, K=3 deep), приоритет типам
   Academic/Primary.
2. Один `haiku`/low суб-агент на источник (параллельно, в одном сообщении):
   - **backward** — список литературы/ссылки источника → канонические primary,
     которых ещё нет в пуле (то самое исследование, которое все пересказывают);
   - **forward** — кто цитирует источник (OpenAlex `cited_by`, Semantic Scholar
     citations — см. `api_sources/academic/`, free no-key) → более свежие
     репликации, развития, опровержения.
3. Кандидаты проходят обычные 4.2 dedup → 4.3 save. У backward-находок `root:` часто
   `own` — они и есть корень, к которому сводятся пересказы из Round 1.

Это **плановый шаг цикла, не deviation** — бюджет триггеров не дебетуется. Триггер
`citation_lead` остаётся для цепочек, вскрывающихся позже: snowball систематизирует
то, что citation_lead ловит от случая к случаю. Shallow — скип.

### Triggers (4) and their classes

| Trigger | Class | Meaning |
|---|---|---|
| `empty_result` | cheap (self-correction) | a planned channel returned nothing relevant |
| `citation_lead` | cheap (self-correction) | a source cites an unreachable primary source |
| `unexpected_finding` | expensive (scope-expansion) | an important angle outside the plan surfaced |
| `contradiction` | expensive (scope-expansion) | sources conflict |

*Self-correction finishes already-planned work (doesn't change scope) → generous
budget. Scope-expansion departs from the approved plan → hard ceiling.*

### Budget & depth (by research depth)

| Depth | cheap | expensive | depth (nesting) limit |
|---|---|---|---|
| shallow | 2 | 0 | 1 |
| medium | 4 | 1 | 1 |
| deep | 8 | 3 | 2 |

- `shallow expensive = 0`: a shallow `unexpected_finding`/`contradiction` is recorded
  `not_pursued: budget_exhausted`, never run. Self-correction still works on shallow.
- **Depth** = how many deviation-spawned rounds deep the current round is (Round 1 =
  depth 0). A deviation from a depth-limit round cannot spawn another.
- Debit is atomic, orchestrator-only, before launching the next round.

### No-progress circuit breaker

Budget/depth bound *how much* the loop may spend; the circuit breaker bounds *spinning
in place*. A deviation round can fire a trigger, cost budget, and return nothing the
pool didn't already have — two of those in a row means the loop is stuck, not
progressing. Stop before it drains the rest of the budget on a phantom.

**Rule:** after each deviation round the orchestrator (cheap tier) computes that round's
**progress delta**. A round makes progress if it added ≥1 *new* source (a URL not
already in `sources.csv`) OR resolved a triggering signal (an `empty_result` that now
has hits, a `citation_lead` whose primary was reached, a `contradiction` now
adjudicated). A round that adds only duplicate/near-duplicate sources and resolves
nothing is a **no-progress round**. **Two consecutive no-progress rounds → break the
loop immediately**, regardless of remaining budget or depth.

On break: record it in `deviations.md` (`type: circuit_breaker`, which rounds stalled,
which triggers were left unpursued) and carry the unresolved triggers into **Open
Questions** in the report (they are genuine gaps, not silent skips). Do not keep
re-launching the same starved subquestion hoping for a different result — one honest
"could not resolve within budget" beats three identical empty rounds.

Round 1 never counts toward the breaker (it *is* the plan, always executed). The
counter resets on any progress round, so alternating progress/no-progress does not
trip it — only a genuine two-round stall does.

### `deviations.md`

Written beside `plan.md` / `sources/`. One record per *considered* trigger (both
`pursued` and `not_pursued` — **exhausted budget/depth still leaves a record; never a
silent skip**), plus a `type: circuit_breaker` record if the no-progress breaker fired.
Phase 6 audits it; Phase 7 reads `not_pursued`/`carry_forward`.

### Dynamic outline revision (ScaffoldAgent)

The plan's block/outline (Phase 2 genre + `plan.md` §8) is the *starting* structure,
not a cage. If a round's aggregated evidence shows the planned outline no longer fits —
a whole dimension surfaced that no block covers, or a planned subtopic came back empty
across rounds — the orchestrator may spend **one expensive-class** deviation to revise
the outline: add/drop/reorder blocks, update `plan.md` §8 + §11, and record it in
`deviations.md` (`type: outline_revision`, before/after, reason). Gate: medium ≤1,
deep ≤2, shallow never (fixed outline). Don't silently rewrite structure — every
revision is a recorded, budgeted decision, same as any deviation. This keeps the report
shape adaptive to what the evidence actually is, not what we guessed at Phase 2.

## Фаза 5. Claims-ledger и триангуляция

**Model:** сборка `claims.csv` из index-строк — `haiku` / `low` (механическая работа). Triangulation check — `haiku` / `low` (правило механическое, см. ниже — не требует "понимания" содержания, только подсчёта источников/типов по строке).

**Скоринг источников больше не отдельный шаг.** Каждый источник в `sources/NN.md` уже имеет заполненный frontmatter со scoring — его проставил fetch sub-agent на шаге 4.1, в момент когда читал источник (H7-правило: скорит тот, кто читал). Здесь, в Фазе 5, шкала подробно описана в `source_scoring.md` для справки, но повторного прохода по всем источникам не требуется.

**Claims-ledger (`claims.csv`)** — новый артефакт-ledger рядом с `sources.csv`. Схема:

```
claim_id, claim, hypothesis, sources, source_types, roots, paths, status, confidence, primary_source, source_caveat, dissent, as_of
```

- `claim` — тезис одной строкой.
- `hypothesis` — H1-H4 или `-` если не привязан к гипотезе.
- `sources` — список id (`s01;s07;s12`).
- `source_types` — типы источников через `;` (`primary;academic;industry`).
- `roots` — корни через `;`, тот же порядок что `sources` (`own;study-smith-2024;own`); из `root:` во frontmatter каждого источника. Без этой колонки третье условие триангуляции нечем проверить.
- `paths` — пути обнаружения через `;`, тот же порядок; из `discovery_path:`. Без неё нечем проверить четвёртое условие (независимость поиска, а не только источников).
- `status` — `triangulated | contested | weak | single-type | single-root | single-path | contradicted | data-insufficient`.
- `confidence` — `high | medium | low`.
- `primary_source` — `Y | N`.
- `source_caveat` — `- | vendor | self-reported | disputed:sNN`.
- `dissent` — id источников, ПРОТИВОРЕЧАЩИХ тезису (`s12;s19`), или `-`. Берётся из полей `dissent`/`contradictions` в JSON суб-агентов. Пустое поле в спорной теме — сигнал, что оппозицию не искали, а не что её нет.
- `as_of` — для волатильных чисел (цена, доля рынка, версия, курс): дата ЗАМЕРА `YYYY-MM`/`YYYY-QN` из поля `data_as_of` источника; `unknown` — число есть, даты нет; `-` для нечисловых. **Источник значения — `data_as_of` во frontmatter, а не дата публикации статьи и не догадка главного потока** (он источников не читал). Число без даты замера — не факт, а мина для будущего `update`, и по fail-closed правилу оно не попадает в `memo.md`.

**Заполнение:** главный поток собирает `claims.csv` из `claim_candidates`, которые вернул каждый fetch sub-agent (см. `subagents_v2.md`), плюс из явного чтения claims в уже записанных `sources/NN.md`. Дублирующиеся claim'ы от разных агентов — смёржить в одну строку (объединить `sources`/`source_types`).

**Triangulation rule (механическая):** строка получает `status: triangulated`, если ≥3 источника **И** ≥2 разных типа **И** ≥2 различных корней (`root:`) **И** ≥2 различных пути обнаружения (`discovery_path:`) — см. `source_scoring.md` «Provenance» и «Четвёртое условие». Иначе:
- < 3 источников → `status: weak`, confidence: low
- ≥3 источника, но один тип → `status: single-type`, confidence: medium (max)
- ≥3 источника и ≥2 типов, но все сводятся к одному `root:` → `status: single-root`, confidence: medium (max) — десять пересказов одного пресс-релиза это один голос; правило считает корни, не URL
- ≥3 источника, ≥2 типов, ≥2 корней, но все найдены одним `discovery_path` → `status: single-path`, confidence: medium (max) — одна формулировка в одном канале даёт одну выборку из одного индекса, а не три независимых голоса
- Есть непогашенный `dissent` от источника с `type: Primary` или `credibility ≥ 4` → `status: contested`, confidence: medium (max) — **правило большинства здесь не действует**; в отчёт идут обе позиции с явным основанием выбора (см. «Правило dissent» в `source_scoring.md`)
- Явное противоречие между источниками без выраженного меньшинства → `status: contradicted` — отдельный counter-argument (Z1)
- После gap-волны (см. выше) всё ещё не закрыто → `status: data-insufficient` (честный результат, не скрывать)

**Primary-first правило:** ключевое число/факт без хотя бы одного primary-источника (`primary_source: N`) не может получить `confidence` выше `medium`, даже если формально triangulated по количеству/разнотипности. Primary здесь — filing, официальная дока, датасет, оригинальное исследование (см. Credibility=5 в `source_scoring.md`).

**После сборки** — обнови `sources.csv` (индекс источников, как раньше) и новый `claims.csv`:

```csv
№,URL,Title,Type,Author,Date,Credibility,Recency,Bias,Total,Used,File,Note
1,https://...,Postgres logical replication docs,Primary,Postgres team,2024-09,5,4,4,13,Y,sources/01_pg-docs-logical.md,Primary source
2,https://...,Industry benchmark,Industry-media,J. Smith,2026-02,4,5,4,13,Y,sources/02_industry.md,Supports H1
```

```csv
claim_id,claim,hypothesis,sources,source_types,roots,paths,status,confidence,primary_source,source_caveat,dissent,as_of
CL1,"Logical replication scales to N nodes without external tooling",H1,s01;s07;s12,primary;industry;academic,own;study-smith-2024;own,academic|logical replication N nodes|en;web-general|postgres multi-master 2026|en;forum-discussion|pgsql-hackers|en,triangulated,high,Y,-,-,-
CL2,"CDC adds >200ms p99 latency at scale",H2,s09;s14,industry;industry,own;own,web-general|CDC latency benchmark|en;web-general|CDC latency benchmark|en,single-type,medium,N,-,-,2026-02
```

### Gap-волна (Фаза 5 продолжается — не новая фаза, аналогично loop-конвенции Фазы 4)

**Model:** `haiku` / `low`. Узкая точечная задача на конкретную дыру — дорогая модель не нужна.

После первого заполнения `claims.csv` собери список дыр — строки со `status ≠ triangulated`.

**Точечная вторая волна:** по одному агенту на дыру (или пачкой, параллельно), промпт = конкретный claim + чего конкретно не хватает:
- «нужен primary-источник для CL2»
- «нужен 3-й тип источника, сейчас только industry×2»
- «противоречие между s09 и s14 — найти причину или дополнительный арбитр»

**Максимум 2 круга.** Если после второго круга дыра не закрылась — строка помечается `status: data-insufficient`. Это честный результат отчёта, не провал: попадает в Open Questions (Z2), а не маскируется.

**Выход:** обновлённый `claims.csv`, обновлённые `sources/NN.md` (новые источники в свежем диапазоне номеров — следующий свободный блок после уже занятых).

## Фаза 6. Синтез + multi-angle red team

**Вход из 5.7:** вердикты `same-claim-conflict` — это расхождение с ПРОШЛЫМ ресёрчем, и оно обязано попасть в отчёт: обе позиции с их `as_of` и корнями, `confidence` не выше `medium`, без арбитра — `contested`. Механика та же, что у `dissent` в Фазе 5, только сторона-оппонент лежит в вики, а не в этом прогоне. Сработавший срез по `MAX_ADJUDICATED` — строкой в `Урезано:` меморандума. См. `wiki.md`.

**Model:** red-team суб-агенты — `opus` / `high` **(обязательно для deep)**, `sonnet` / `high` для medium. Synthesis assembly — `sonnet` / `high` (длинный контекст). Не экономить на red team — это где Haiku/Sonnet делают soft-pushback без реальной атаки на гипотезы.

**Порядок:**
1. Перечитай ВСЕ `sources/NN.md` с `used: Y`. Не делай синтез из памяти. Для **deep**: `findings/` слой обязателен — синтез идёт из `findings/` + `claims.csv`, точечная сверка `sources/NN.md` только по спорным местам. Для shallow/medium — как раньше, перечитать used sources целиком.
2. Перечитай `plan.md` (жанр, blocks, гипотезы, секция 0 User context) и `claims.csv` (статус/confidence каждого тезиса).
3. Загрузи нужные категорийные файлы `blocks/*.md` (только те что нужны для выбранных blocks). Прогрессивно — не сразу все.
4. Для каждой гипотезы — собери поддерживающие/опровергающие цитаты. Опционально вынеси крупные в `findings/FN.md` (см. `blocks/close.md` блок Z6).
4.5. **Зафиксируй `outline.md`** (medium/deep) — таблицу `| section | block | claims |` из `plan.md` §8/§11 плюс фактического `claims.csv`, то есть из того, что реально нашлось. Она же — индекс адресной выборки на шаге 5 и вход трёх машинных проверок (`validate_phases.py`: секция без claim, несуществующий `claim_id`, **claim `triangulated`/`contested` вне отчёта** = synthesis gap). Шаблон и правила — `synthesis_outline.md`.
5. Собери черновик `<date>_<genre>.md` **секция за секцией по `outline.md`**: под каждую секцию подтягивай только её `claim_id` из `claims.csv` и её `evidence/CN.md`, а не весь пул (точность цитирования падает там, где контекста больше всего — тот же принцип, по которому 5.5 не отдаёт синтезу нерелевантные цитаты, но на уровне секции). Каждый блок — по шаблону из своего категорийного файла. Три сквозных правила синтеза (применяй ко всем блокам, не только TL;DR):
   - **Числа с якорем сравнения.** Ключевое число без базы сравнения запрещено: «Рынок $4.5B» — недостаточно. «Рынок $4.5B — втрое меньше соседнего сегмента X, растёт втрое быстрее среднего по индустрии» — годится. Якорь: vs база / vs сосед / vs динамика во времени.
   - **Условия применимости.** Каждый вывод — с явным «когда верен, когда нет», не голое утверждение.
   - **Одиночный прогон — не различие.** Число из одного прогона собственного замера не докладывается как установленное различие («в 60 раз дороже») без доверительного интервала или явной пометки «одиночный прогон, без CI». Собственный замер, вошедший в выводы, несёт `caveat: self-reported` (потолок confidence — `medium`, см. `source_scoring.md`), а все его файлы — один общий `root` (одно измерение = один голос, не три).
   - **Confidence из claims.csv.** Каждый пункт TL;DR (F1) несёт свой `confidence` (high/medium/low), взятый из соответствующей строки `claims.csv` — не придуманный на глаз при синтезе.
   - **Запрет финала «it depends».** Ресёрч, кончающийся «зависит от обстоятельств», бесполезен по определению. Если однозначная рекомендация невозможна — обязана быть условная, замапленная на вилки Decision Spec: «приоритет — стоимость → X; скорость → Y». «It depends» без разрешённых условий = незакрытый acceptance criterion, не финал.
   - Блок Z12 `so-what-for-you` (см. `blocks/close.md`) собирается на этом же шаге из `plan.md` секции 0 (Decision Spec + User context) + `claims.csv` — ключевые claims мапятся на вилки решения, считается applicability ratio; проекция выводов на кейс пользователя, до `actionable-next-steps`.
6. **Multi-angle red team** (см. `adversarial_pass.md`) — draft → claim ledger (внутренний список falsifiable-тезисов для red team, не путать с файлом `claims.csv`) → N враждебных ролей (Skeptic/Contrarian/Gap-hunter/Исполнитель) как `general-purpose` суб-агенты → триаж severity → ОДИН раунд ремедиации HIGH → финал. Гейт глубины: shallow=R1 инлайн, medium=R1+R2+R4, deep=R1+R2+R3+R4. Дефекты → counter-arguments (`Z1`) + Open Questions; лог в `findings/redteam_<date>.md`. Не маскируй несогласие. 5-й adversarial-вопрос (см. `adversarial_pass.md`): есть ли числа без якоря сравнения, выводы без Z12-проекции, рекомендации без trade-off/kill-criteria?
7. **Собери `memo.md` — decision-меморандум на одну страницу.** В процесс потребителя входит не 40-страничный отчёт, а одна страница; отчёт — доказательная база под ней. Состав: рекомендация (однозначная или условная по вилкам), разрешение if-then вилок Decision Spec, 3 ключевых числа с [sNN] и `as_of`, главный риск, next actions, **строка «что урезали»**.

   **Строка «что урезали» — обязательна, если прогон сузил сам себя.** У ресёрча есть два легальных способа тихо уменьшить задачу: даунгрейд в shallow (нет ни одной if-then вилки) и no-progress circuit breaker (2 раунда без новой информации). Оба правильные — и оба обязаны быть громкими, иначе пользователь получает более лёгкую версию своего вопроса, не зная об этом. Формат — одна строка:

   ```
   Урезано: circuit breaker на раунде 3 (Q4 «стоимость перехода» без данных) · режим остался medium.
   ```

   Ничего не урезали — так и напиши `Урезано: —`. Метрика, которую можно улучшить, перестав делать работу, — не метрика: доля `triangulated` растёт, если трудные claim сбросить в Open Questions, поэтому она читается только в паре с покрытием, а сужение объявляется вслух.

   Числа в memo подчиняются fail-closed правилу провенанса: число с `origin_kind: unknown`, `chain_len ≥ 2` или без `data_as_of` сюда не попадает (см. `source_scoring.md` «Provenance числа»); `check_number_provenance.py` проверяет это машинно. Пишется ПОСЛЕ red team (ремедиация HIGH уже учтена). Обязателен всегда; в shallow — крошечный (5–10 строк). Артефакт Фазы 6, проверяется phase-gate.
8. Если в системе есть `anthropic-skills:humanizer-ru` — прогони финальный отчёт через него.
9. Сохрани финальный отчёт.

## Фаза 6.9. Экспорт отчёта

**Model:** `haiku` / `low`. Механическая сборка, содержательных решений нет.

```bash
uv run scripts/build_report.py <run>
```

Собирает `<date>_<genre>.md` в HTML, PDF и DOCX из одного источника. Полностью —
`references/report_export.md`. Здесь — что фаза обязана оставить и на чём падает.

**Оставляет:** `<date>_<genre>.html`, `.pdf`, `.docx` в папке прогона; SVG фигур в `.build/`.

**Падает на:**
- ссылке `[sNN]`, которой нет в `sources.csv` — в 20 страницах битую ссылку глазами не находят;
- фигуре, ссылающейся на `num_id` вне `numbers.csv` — график не вправе утверждать больше ledger'а;
- расхождении «сносок N, перенесено M» — молча потерянная сноска неотличима от её отсутствия.

`--no-strict` снимает первые два отказа, но не третий.

**Регистр — 15–20 страниц под одно решение.** `memo.md` остаётся отдельной страницей:
одна страница, которую точно прочтут, не растворяется в двадцати.

## Фаза 7. Refresh targets generation (medium/deep — обязательно)

**Model:** `sonnet` / `medium`. Механический проход по финальному отчёту с экстракцией entities, numbers, hypotheses.

**Зачем:** этот файл — **точка входа для будущих `update <slug>`**. Без него каждый update тратит время на повторное discovery «что вообще отслеживать в этой теме».

**Шаги:**
1. Прочитай финальный `<date>_<genre>.md` + `plan.md`.
2. Извлеки **entities** из блоков M2 (profile-cards), M5 (white-spaces), C1-C5 (compare matrices): конкретные компании/проекты с URL.
3. Извлеки **numbers** из блоков N1-N8: конкретные FRED series IDs, World Bank indicators, industry estimate refs.
4. Извлеки **topic markers** из плана: GitHub topics из awesome_lists_registry discovery, OpenAlex concept IDs.
5. Извлеки **гипотезы H1-H4** из plan.md с финальным статусом из A4 (hypotheses-outcome).
6. Запиши в `<root>/<slug>/refresh_targets.md` по шаблону **Z11** из `blocks/close.md`.

**Refresh candidates — дополнительный источник:**

- **Carry-forward deviations.** Read `deviations.md` for `not_pursued` records with a
  `carry_forward` field; each is a first-class refresh-target candidate (an angle the
  search loop identified but could not pursue within budget/depth).

**Output:** файл `refresh_targets.md` рядом с `plan.md`. Используется при последующих `update <slug>` — см. `refresh_protocol.md`.

**Anti-patterns:** см. блок Z11 в `blocks/close.md`.

## Фаза 8. Decision walkthrough (обязательна всегда, включая shallow)

**Model:** главный поток, `opus` / `high` — качество вопросов критично, как в Фазе 1.

Отчёт не «обсуждается», а исполняется: агент показывает `memo.md` и ведёт
пользователя по if-then вилкам Decision Spec по одной — «ресёрч показал X [s03][s11]
— вилка A срабатывает? твоё решение?». Исходы на вилку: **принято** (решение + next
action с датой) / **заблокировано данными** (одна целевая gap-волна, max 1 круг →
повторный заход, не закрылось — честно `blocked`) / **отложено** (`deferred`, без
дожима). Полная механика, шаблон `application.md`, глобальный ledger и анти-паттерны
— `references/decision_walkthrough.md`.

**Output:** `<slug>/application.md` (любой status — gate требует файл, не принятое
решение) + строка в `~/.claude/research/applications_ledger.csv`.

## Чек-лист после Фазы 8

- [ ] **Acceptance criteria из plan.md (секция 4) ВСЕ выполнены** — перепроверь каждый чек-бокс
- [ ] Все `sources/NN.md` имеют корректный frontmatter (scoring, channel, access заполнены)
- [ ] `sources.csv` обновлён, total пересчитан
- [ ] `claims.csv` заполнен — каждая строка имеет status; строки не triangulated прошли gap-волну (см. Фаза 5, max 2 круга) и честно помечены `data-insufficient` если не закрылись
- [ ] Ни один тезис с `confidence: high` не нарушает primary-first правило (без primary-источника confidence ≤ medium)
- [ ] `plan.md` имеет `status: completed`
- [ ] `plan.md` секция 15 (notes) финализирована — все важные observations документированы
- [ ] `<date>_<genre>.md` собран из всех блоков из `plan.md` → `blocks:`
- [ ] Все required блоки для жанра присутствуют (см. `genres.md`)
- [ ] Каждое утверждение имеет ссылку на конкретный [sNN] или помечено `[без подтверждения]`
- [ ] Каналы coverage ≥3 разных типов (см. plan.md секция 14)
- [ ] Multi-angle red team выполнен (роли по гейту глубины), Z1 counter-arguments записаны, лог `findings/redteam_<date>.md` создан
- [ ] Hypotheses outcome таблица заполнена — все H1-H4 имеют status
- [ ] Risk register из plan.md (секция 10) проверен — risks которые реализовались отмечены, mitigation работала?
- [ ] Open questions перечислены (Z2)
- [ ] Next research suggestions — 2–3 штуки (Z3)
- [ ] Если update-режим: changelog (plan.md секция 16) финализирован
- [ ] Если есть `memory/` — предложены memory candidates
- [ ] **`refresh_targets.md` сгенерирован** (Phase 7, для medium/deep) — entities/numbers/hypotheses/topic markers заполнены по шаблону Z11
- [ ] **`memo.md` собран** (Phase 6, всегда) — рекомендация без «it depends», вилки, 3 числа с [sNN]+as_of, риск, next actions
- [ ] **Decision walkthrough проведён** (Phase 8, всегда) — вилки разрешены (принято/blocked/deferred), `application.md` записан со status и applicability_ratio
- [ ] Строка добавлена в `~/.claude/research/applications_ledger.csv`
- [ ] Файлы сохранены, путь показан пользователю markdown-ссылкой
