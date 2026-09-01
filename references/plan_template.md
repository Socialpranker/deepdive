# Шаблон plan.md

Дополнение к `workflow.md` Фаза 3. Читать **при входе в Фазу 3**, не заранее — до
этого момента прогону нужна только структура (5 секций HEADER → SCOPE → STRUCTURE →
EXECUTION → TRACKING), а не буквальный текст шаблона.

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

## 3. Решение, которое поддерживает (Decision Spec)
- **Что решаем:** <глагол + объект + срок>
- **Потребитель → следующий шаг:** <кто читает отчёт и что физически делает после>
- **If-then вилки:** если <X> → <A>; если <Y> → <B>  (≥1, опровергаемая)
- **Если ни одной вилки:** это не ресёрч, это любопытство — снизить до shallow с явной пометкой или отказаться

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

| Subtopic | Под какие блоки | Level (depends on) | Кому (agent # + source range / main thread) |
|---|---|---|---|
| ST1: <название> | F3, E1, E4 | L1 (—) | Agent #1 (`general-purpose`, s01-s09) |
| ST2: <название> | A1 (data-table rows), M2 (profile cards) | L1 (—) | Agent #2 (`general-purpose`, s10-s19) |
| ST3: <название> | V2 (evidence FOR/AGAINST), Z1 (counter-args) | L2 (ST1) | Agent #3 (`general-purpose`, s20-s29) |
| ST4: <название> | E10 (failure modes), Z2 (open questions) | L2 (ST1, ST2) | main thread |

### Least-to-most: когда подвопросы образуют цепочку

Большинство подвопросов **независимы** — все `L1`, все ищутся параллельно в Round 1.
Не навязывай цепочку там, где её нет: если ответ на ST-B не меняется от того, что́ ты
узнал в ST-A, они оба L1. Плоская декомпозиция — норма, не дефект.

Но **многошаговые** вопросы (форма «как X повлияет на Y, **учитывая** Z», «что следует
из A для B») содержат подвопросы, которые нельзя осмысленно искать, пока не отвечён
предшествующий — ответ раннего есть **вход** в формулировку/queries позднего. Для них
плоский параллельный fan-out ищет вслепую: поздний агент не знает конкретики, которую
дал бы ранний. Least-to-most решает это гигантский прирост на многошаговых (SCAN 99% vs
16%): раскладываешь подвопросы по **уровням** и накапливаешь контекст между ними.

**Механика (только для вопросов с реальной зависимостью):**
1. Проставь `Level` в таблице выше. `L1` — независимые (стартуют сразу). `L2` зависит от
   одного/нескольких L1; `L3` — от L2. Держи глубину малой (обычно ≤2 уровня) — глубокая
   цепочка = либо вопрос действительно каскадный, либо ты передробил.
2. **Round 1 = все L1** параллельно (обычный fan-out по диапазонам). Уровень не ломает
   параллелизм — внутри уровня всё так же параллельно.
3. После L1 зафиксируй **carried context** — 2-4 конкретных факта/числа/сущности из
   ответов L1, которые нужны следующему уровню (не весь дамп — именно то, что питает
   зависимый подвопрос). Впиши их в dispatch (секция 12) зависимых ST.
4. **Запусти L2** с уже конкретизированными queries. Повтори для L3, если есть.
5. Циклы (accumulation) идут **до** deviation-loop раунда, не вместо него: сначала
   отрабатывает плановая цепочка уровней, затем — orchestrator-evaluation/deviations на
   агрегированном результате.

Если после L1 выясняется, что зависимость была мнимой (carried context не понадобился) —
сверни цепочку, гони остаток параллельно, запиши в `deviations.md`
(`type: decomposition_flatten`). Честнее плоско, чем изображать каскад.

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
