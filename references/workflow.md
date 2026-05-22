# Workflow — детали 6 фаз

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
- [ ] Adversarial pass пройден (для medium/deep)
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

| Subtopic | Под какие блоки | Кому (Explore # / main thread) |
|---|---|---|
| ST1: <название> | F3, E1, E4 | Explore #1 |
| ST2: <название> | A1 (data-table rows), M2 (profile cards) | Explore #2 |
| ST3: <название> | V2 (evidence FOR/AGAINST), Z1 (counter-args) | Explore #3 |
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

**Phase 4 = 4 шага в строгом порядке:** Dispatch → Launch → Fetch → Save. Не пропускай Dispatch — без него Launch будет хаотичным.

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

**Output Phase 4:** заполненная папка `sources/` + обновлённый `sources.csv` + flags «open gaps» в plan.md для подвопросов где не удалось набрать ≥3 разнотипных источников.

## Фаза 5. Скоринг и триангуляция

**Model:** scoring per source — `haiku` / `low` (простой rubric). Triangulation check — `sonnet` / `medium` (требует понимания содержания).

Каждый источник в `sources/NN.md` имеет frontmatter со scoring (см. `source_scoring.md`).

**Triangulation rule:** каждое утверждение в финальных выводах подтверждено ≥3 независимыми источниками **разного типа**. Не три статьи одного автора, не три новости одного издания.

**Если триангуляция не сходится:**
- < 3 источников → пометь тезис «спорно / требует проверки», confidence: low
- 3 источника, но одного типа → «требует подтверждения первичным источником», confidence: medium
- Нашёл оппозицию → отдельный counter-argument в Фазу 5

**После скоринга** — обнови `sources.csv`:

```csv
№,URL,Title,Type,Author,Date,Credibility,Recency,Bias,Total,Used,File,Note
1,https://...,Postgres logical replication docs,Primary,Postgres team,2024-09,5,4,4,13,Y,sources/01_pg-docs-logical.md,Primary source
2,https://...,Industry benchmark,Industry-media,J. Smith,2026-02,4,5,4,13,Y,sources/02_industry.md,Supports H1
```

## Фаза 6. Синтез + adversarial pass

**Model:** adversarial pass — `opus` / `high` **(обязательно)**. Synthesis assembly — `sonnet` / `high` (длинный контекст). Не экономить на adversarial — это где Haiku/Sonnet делают soft-pushback без реальной атаки на гипотезы.

**Порядок:**
1. Перечитай ВСЕ `sources/NN.md` с `used: Y`. Не делай синтез из памяти.
2. Перечитай `plan.md` — жанр, blocks, гипотезы.
3. Загрузи нужные категорийные файлы `blocks/*.md` (только те что нужны для выбранных blocks). Прогрессивно — не сразу все.
4. Для каждой гипотезы — собери поддерживающие/опровергающие цитаты. Опционально вынеси крупные в `findings/FN.md` (см. `blocks/close.md` блок Z6).
5. Собери черновик `<date>_<genre>.md` из выбранных блоков по порядку из `plan.md`. Каждый блок — по шаблону из своего категорийного файла.
6. **Adversarial pass** (см. `adversarial_pass.md`) — 4 вопроса. Counter-arguments — блок `Z1` в отчёте. Не маскируй несогласие.
7. Если в системе есть `anthropic-skills:humanizer-ru` — прогони финальный отчёт через него.
8. Сохрани.

## Чек-лист после Фазы 6

- [ ] **Acceptance criteria из plan.md (секция 4) ВСЕ выполнены** — перепроверь каждый чек-бокс
- [ ] Все `sources/NN.md` имеют корректный frontmatter (scoring, channel, access заполнены)
- [ ] `sources.csv` обновлён, total пересчитан
- [ ] `plan.md` имеет `status: completed`
- [ ] `plan.md` секция 15 (notes) финализирована — все важные observations документированы
- [ ] `<date>_<genre>.md` собран из всех блоков из `plan.md` → `blocks:`
- [ ] Все required блоки для жанра присутствуют (см. `genres.md`)
- [ ] Каждое утверждение имеет ссылку на конкретный [sNN] или помечено `[без подтверждения]`
- [ ] Каналы coverage ≥3 разных типов (см. plan.md секция 14)
- [ ] Adversarial pass выполнен (4 вопроса), Z1 counter-arguments записаны
- [ ] Hypotheses outcome таблица заполнена — все H1-H4 имеют status
- [ ] Risk register из plan.md (секция 10) проверен — risks которые реализовались отмечены, mitigation работала?
- [ ] Open questions перечислены (Z2)
- [ ] Next research suggestions — 2–3 штуки (Z3)
- [ ] Если update-режим: changelog (plan.md секция 16) финализирован
- [ ] Если есть `memory/` — предложены memory candidates
- [ ] Файлы сохранены, путь показан пользователю markdown-ссылкой
