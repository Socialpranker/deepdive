# Workflow — детали <!--gen:count:phases-->11<!--/gen--> фаз

Дополнение к SKILL.md. Здесь — пошаговые инструкции и шаблоны. Читать в начале medium/deep ресёрча.

## Фаза 1. Reframing

**Model:** `opus` / `high` (см. `model_routing.md`). Качество reframing'а определяет весь ресёрч — не экономить.

Цель: убедиться, что ищем правильное. Большая часть плохих ресёрчей — плохие вопросы, не плохой поиск.

**Шаги:**
1. Перепиши вопрос своими словами: «Я понимаю задачу так: …». Это проверка совпадения картин.
2. Зафиксируй решение, которое поддерживает ресёрч. Если ничего не меняется от ответа — это любопытство, не ресёрч. Спроси пользователя, нужен ли вообще.
3. Сформулируй 2–4 опровергаемые гипотезы. Не «изучить тему» (это не гипотеза), а «X лучше Y по Z» (опровергаемо).
4. Сформулируй критерии остановки. Без них ресёрч уходит в бесконечность.
5. Если есть мутность — задай ≤3 уточняющих вопроса. Если пользователь отвечает «не знаю» — двигайся с явным допущением.

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

**Шаблон plan.md:**

```markdown
---
slug: <slug>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
depth: shallow | medium | deep
report_type: qa | explainer | decision | landscape | validation | custom
blocks: [tldr, scope, mental-model, stepwise, counter-arguments, sources, metadata]
status: planning | searching | synthesizing | completed | superseded
version: initial | update-1 | update-2
parent: <YYYY-MM-DD>_<genre>.md   # null if initial
time_box_target: ~<X hours>
time_box_hard: <Y hours>
---

# Plan — <Тема>

## 0. User context

- **Кто спрашивает / для кого:** <user role, audience for report, ...>
- **Зачем (бизнес/личный мотив):** <real underlying motivation>
- **Что уже знает:** <baseline knowledge level — beginner / informed / expert>
- **Как будет использовать отчёт:** <принять решение к <date> / включить в pitch / поделиться с командой / личное понимание>
- **Constraints на отчёт:** <язык, формат, длина, конфиденциальность>

## 1. Time-box

- **Target completion:** ~<N часов> (соответствует depth `<level>`)
- **Hard deadline:** <YYYY-MM-DD HH:MM или N часов от старта>
- **Если превысили hard deadline:** синтезировать с тем что есть, пометить confidence: low по нерешённым тезисам

---

# SCOPE

## 2. Главный вопрос
<после reframing — переписано своими словами>

## 3. Решение, которое поддерживает
- **Что решаем:** <конкретное решение>
- **Что меняется от ответа:** <какие варианты действий вытекают>
- **Если ничего не меняется:** это не ресёрч, это любопытство — снизить до shallow или отказаться

## 4. Acceptance criteria (что считается «готово»)

Конкретно что должно быть на выходе чтобы ресёрч считался завершённым:

- [ ] `<date>_<genre>.md` содержит все required блоки жанра
- [ ] Каждая гипотеза H1-H4 получила status (confirmed / contradicted / partial / insufficient)
- [ ] `<specific deliverable 1>` (e.g. список 5+ конкурентов с profile cards)
- [ ] `<specific deliverable 2>` (e.g. ответы на 4 конкретных Q пользователя)
- [ ] `<specific deliverable 3>`
- [ ] Counter-arguments ≥2 для medium / ≥3 для deep
- [ ] Multi-angle red team пройден (для medium/deep)
- [ ] Все sources/NN.md имеют channel + access поля

## 5. Discovered existing

Что уже есть по теме в проекте — найдено в фазе discover.

**Существующие research-папки:**
- `<existing slug>` от <date> — <relation: same topic? adjacent? update target?>
- (или: «ничего нет, ресёрч initial»)

**Memory entries:**
- `<memory file>` упоминает <fact> — <принимаем / пересматриваем / not relevant>
- (или: «memory пуст или не релевантен»)

**CLAUDE.md project context:**
- <relevant project info from CLAUDE.md / CLAUDE.local.md>
- (или: «CLAUDE.md не упоминает тему»)

**Решение:** initial research | update of `<slug>` | re-investigation (with reason)

## 6. Глоссарий ресёрча (термины и определения)

Термины, которые будут использоваться в ходе ресёрча и отчёта. Согласованы между скиллом и пользователем ДО старта поиска.

- **<Термин 1>** — <определение, как мы его используем здесь>
- **<Термин 2>** — <определение>
- **<Термин 3>** — НЕ путать с <similar term>, важное отличие <X>

Если в процессе поиска обнаружится, что термин нужно уточнить — обновить здесь и зафиксировать в `notes` (секция 17).

---

# STRUCTURE

## 7. Жанр отчёта
**<genre>** — почему этот: <обоснование выбора эвристикой / пользовательским вводом>

## 8. Блоки отчёта с rationale

Для standard жанра — пресет из `genres.md`. Для custom — обязательно объясни КАЖДЫЙ block.

| Порядок | Блок [ID] | Зачем здесь |
|---|---|---|
| 1 | tldr [F1] | (всегда) |
| 2 | scope [F3] | (всегда) |
| 3 | mental-model [E1] | <под H1, объясняет устройство X> |
| 4 | data-table [A1] | <собираем <metric>×<entity> для answering Q2> |
| 5 | counter-arguments [Z1] | (всегда medium/deep) |
| 6 | ... | ... |

## 9. Гипотезы

- **H1:** <опровергаемое утверждение>
- **H2:** ...
- **H3:** ...
- **H4:** ... (опционально)

## 10. Risk register (pre-mortem перед стартом)

Где может пойти не так до того как начали:

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Тема плохо документирована (мало sources total≥12) | medium | high | заранее plan для interviews fallback, понизить confidence ceiling |
| R2 | Closed info (private financials) — большая часть claim не verifiable | high | medium | признать честно, использовать indirect signals |
| R3 | Politically charged — bias в источниках | medium | high | целенаправленно triangulate из multiple political perspectives |

---

# EXECUTION

## 11. Подтемы ↔ Блоки mapping

Какая подтема собирает evidence для каких блоков. Без этого агенты не знают для чего работают.

| Subtopic | Под какие блоки | Кому (agent # + source range / main thread) |
|---|---|---|
| ST1: <название> | F3, E1, E4 | Agent #1 (`general-purpose`, s01-s09) |
| ST2: <название> | A1 (data-table rows), M2 (profile cards) | Agent #2 (`general-purpose`, s10-s19) |
| ST3: <название> | V2 (evidence FOR/AGAINST), Z1 (counter-args) | Agent #3 (`general-purpose`, s20-s29) |
| ST4: <название> | E10 (failure modes), Z2 (open questions) | main thread |

## 12. Information sourcing strategy

**Заполняется на шаге Phase 4.0 Source Dispatch** через `source_dispatch.md` — каждый подвопрос/подтема прогоняется через matrix «сигнал → primary/secondary/fallback каналы». **Прозрачность: пользователь видит куда смотрим и зачем.**

### ST1: <название>

**Под блоки:** F3, E1, E4 (см. mapping выше)

**Dispatch (primary / secondary / fallback):**

- **Primary** — `<channel-name>` (из `source_dispatch.md` matrix, строка под сигнал «...»)
  - Specific queries: `<query template 1>`, `<query template 2>`
  - Что ищем: <конкретный тип evidence>
  - Конкретные источники: `stat_sources/<path>.md` или `api_sources/<category>/<api>.md`

- **Secondary** — `<channel-name>` (независимая проверка primary)
  - Specific queries: `<...>`
  - Конкретные источники: `<path>`

- **Fallback** — `<channel-name>` (только если primary/secondary недоступны)
  - Queries: `<...>`

**API endpoints (если api-direct primary или secondary):**
1. **`api_sources/<category>/<api>.md`** → конкретный API
   - Endpoint: `<url>`
   - Auth: `<env var name>` / no-auth
   - Query template: `<sample query>`

**Capabilities check (Phase 3.5):**
- ✅/⚠/❌/❓ FRED API: authenticated / fallback / unavailable / to-discover
- ✅ Semantic Scholar: open-no-auth, will use directly
- ⚠ Brave Search: no key → fallback to standard WebSearch

**Discovery executed (Phase 4.0):**
- Awesome-lists registry: <какой Tier чекнули + что нашли>
- GitHub topic search: <topic:keyword найдено N репо/awesome-list>
- HuggingFace / Kaggle / PyPI / data portals: <если применимо>
- Если ничего не понадобилось — write «N/A — каталога хватило»

**Critical gaps to address:**
- Opposition voice → `forum-discussion` channel + `<source>` industry
- Recent data → `news-current` за последние <N месяцев>

### ST2: <название>
(тот же шаблон — primary / secondary / fallback из `source_dispatch.md`)

### ST3, ST4, ...

**Acceptance для секции 12:** Заполнена для **каждого** подвопроса из секции 11. Если хотя бы один подвопрос без dispatch — Phase 4.1 (launch sub-agents) не запускать, вернуться к шагу 4.0.

## 13. Critical opposition queries

Целевые queries специально для нахождения contrarian voice:
- `<topic> criticism`
- `<topic> "doesn't work" OR "failed"`
- `<topic> "myth" OR "misconception"`
- `against <topic> / counter-evidence`

Один dedicated round этих queries — обязательно. Если ничего не найдено — попробуй с другой формулировкой или признай «consensus very strong, no opposition found».

## 14. Stop-criteria (поиска)

- Все H1-H4 покрыты ≥3 источниками каждая
- Покрыты ≥4 типа источников
- Покрыты ≥3 канала (см. channels.md) — diversity of methodology
- Целевой поиск оппозиции выполнен
- НЕТ новой информации в последних 3-5 источниках
- Все acceptance criteria (секция 4) могут быть выполнены с собранным material

**Не путать с acceptance criteria (секция 4) — те про отчёт, эти про поиск.**

---

# TRACKING

## 15. Notes during research

Место для заметок в процессе поиска. Обновляется по ходу work, не в конце.

- **<YYYY-MM-DD HH:MM>** — нашёл что <observation>, relevant для ST2
- **<date>** — opposition нашёл в [s09], confidence H2 понижена до medium
- **<date>** — gap: data до 2022 only, recent — нет; см. risk R1
- ...

## 16. Update changelog (только для update-режима)

Заполнять только если `version: update-N`.

**Контекст обновления:** <почему понадобился update>

**Дельта vs предыдущая версия:**
- Что добавилось: <новые подтемы, новые блоки, новые гипотезы>
- Что устарело: <какие H/блоки больше не релевантны>
- Что проверяем заново: <findings которые надо валидировать в свете new evidence>

**Не повторяем:**
- <areas уже глубоко покрытые в parent, на которые опираемся>

---

## Slug
<slug>
```

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
$FRED_API_KEY, $GITHUB_TOKEN, $TAVILY_API_KEY, $BRAVE_API_KEY, $NEWSAPI_KEY, ...
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
- Если WebFetch блокирован — следуй paywall fallback protocol в `channels.md` (preprint → archive → researchgate → … → Sci-Hub как last resort с disclaimer).
- Покрывай ≥3 канала разных типов для diversity of methodology (требование Phase 5 триангуляции).
- Dedup по URL и по содержанию (если две ссылки ведут на один и тот же отчёт — оставь одну с лучшим scoring).

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

3. **Orchestrator evaluation (after every round, `strong` tier / Opus):**
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
   - For each justified trigger, if budget for its class remains AND depth < limit:
     classify cheap/expensive, debit the counter, write a `deviations.md` record,
     and launch the next round. Otherwise write a `not_pursued` record.
4. **The loop ends** when no justified trigger remains, OR both budgets are exhausted,
   OR the depth limit is reached, OR the **no-progress circuit breaker** fires (see
   below). Then proceed to Phase 5.

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
claim_id, claim, hypothesis, sources, source_types, status, confidence, primary_source
```

- `claim` — тезис одной строкой.
- `hypothesis` — H1-H4 или `-` если не привязан к гипотезе.
- `sources` — список id (`s01;s07;s12`).
- `source_types` — типы источников через `;` (`primary;academic;industry`).
- `status` — `triangulated | weak | single-type | contradicted | data-insufficient`.
- `confidence` — `high | medium | low`.
- `primary_source` — `Y | N`.

**Заполнение:** главный поток собирает `claims.csv` из `claim_candidates`, которые вернул каждый fetch sub-agent (см. `subagents_v2.md`), плюс из явного чтения claims в уже записанных `sources/NN.md`. Дублирующиеся claim'ы от разных агентов — смёржить в одну строку (объединить `sources`/`source_types`).

**Triangulation rule (механическая):** строка получает `status: triangulated`, если ≥3 источника **И** ≥2 разных типа. Иначе:
- < 3 источников → `status: weak`, confidence: low
- ≥3 источника, но один тип → `status: single-type`, confidence: medium (max)
- Явное противоречие между источниками → `status: contradicted` — отдельный counter-argument (Z1)
- После gap-волны (см. выше) всё ещё не закрыто → `status: data-insufficient` (честный результат, не скрывать)

**Primary-first правило:** ключевое число/факт без хотя бы одного primary-источника (`primary_source: N`) не может получить `confidence` выше `medium`, даже если формально triangulated по количеству/разнотипности. Primary здесь — filing, официальная дока, датасет, оригинальное исследование (см. Credibility=5 в `source_scoring.md`).

**После сборки** — обнови `sources.csv` (индекс источников, как раньше) и новый `claims.csv`:

```csv
№,URL,Title,Type,Author,Date,Credibility,Recency,Bias,Total,Used,File,Note
1,https://...,Postgres logical replication docs,Primary,Postgres team,2024-09,5,4,4,13,Y,sources/01_pg-docs-logical.md,Primary source
2,https://...,Industry benchmark,Industry-media,J. Smith,2026-02,4,5,4,13,Y,sources/02_industry.md,Supports H1
```

```csv
claim_id,claim,hypothesis,sources,source_types,status,confidence,primary_source
CL1,"Logical replication scales to N nodes without external tooling",H1,s01;s07;s12,primary;industry;academic,triangulated,high,Y
CL2,"CDC adds >200ms p99 latency at scale",H2,s09;s14,industry;industry,single-type,medium,N
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

**Model:** red-team суб-агенты — `opus` / `high` **(обязательно для deep)**, `sonnet` / `high` для medium. Synthesis assembly — `sonnet` / `high` (длинный контекст). Не экономить на red team — это где Haiku/Sonnet делают soft-pushback без реальной атаки на гипотезы.

**Порядок:**
1. Перечитай ВСЕ `sources/NN.md` с `used: Y`. Не делай синтез из памяти. Для **deep**: `findings/` слой обязателен — синтез идёт из `findings/` + `claims.csv`, точечная сверка `sources/NN.md` только по спорным местам. Для shallow/medium — как раньше, перечитать used sources целиком.
2. Перечитай `plan.md` (жанр, blocks, гипотезы, секция 0 User context) и `claims.csv` (статус/confidence каждого тезиса).
3. Загрузи нужные категорийные файлы `blocks/*.md` (только те что нужны для выбранных blocks). Прогрессивно — не сразу все.
4. Для каждой гипотезы — собери поддерживающие/опровергающие цитаты. Опционально вынеси крупные в `findings/FN.md` (см. `blocks/close.md` блок Z6).
5. Собери черновик `<date>_<genre>.md` из выбранных блоков по порядку из `plan.md`. Каждый блок — по шаблону из своего категорийного файла. Три сквозных правила синтеза (применяй ко всем блокам, не только TL;DR):
   - **Числа с якорем сравнения.** Ключевое число без базы сравнения запрещено: «Рынок $4.5B» — недостаточно. «Рынок $4.5B — втрое меньше соседнего сегмента X, растёт втрое быстрее среднего по индустрии» — годится. Якорь: vs база / vs сосед / vs динамика во времени.
   - **Условия применимости.** Каждый вывод — с явным «когда верен, когда нет», не голое утверждение.
   - **Confidence из claims.csv.** Каждый пункт TL;DR (F1) несёт свой `confidence` (high/medium/low), взятый из соответствующей строки `claims.csv` — не придуманный на глаз при синтезе.
   - Блок Z12 `so-what-for-you` (см. `blocks/close.md`) собирается на этом же шаге из `plan.md` секции 0 (User context) + `claims.csv` — проекция выводов на кейс пользователя, до `actionable-next-steps`.
6. **Multi-angle red team** (см. `adversarial_pass.md`) — draft → claim ledger (внутренний список falsifiable-тезисов для red team, не путать с файлом `claims.csv`) → N враждебных ролей (Skeptic/Contrarian/Gap-hunter) как `general-purpose` суб-агенты → триаж severity → ОДИН раунд ремедиации HIGH → финал. Гейт глубины: shallow=R1 инлайн, medium=R1+R2, deep=R1+R2+R3. Дефекты → counter-arguments (`Z1`) + Open Questions; лог в `findings/redteam_<date>.md`. Не маскируй несогласие. 5-й adversarial-вопрос (см. `adversarial_pass.md`): есть ли числа без якоря сравнения, выводы без Z12-проекции, рекомендации без trade-off/kill-criteria?
7. Если в системе есть `anthropic-skills:humanizer-ru` — прогони финальный отчёт через него.
8. Сохрани финальный отчёт.

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

## Чек-лист после Фазы 7

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
- [ ] Файлы сохранены, путь показан пользователю markdown-ссылкой
