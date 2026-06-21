# CLOSE blocks — закрытие отчёта

Блоки финала отчёта: counter-arguments, open questions, next steps, источники.

---

## Z1 — `counter-arguments`

**Когда:** Medium/deep всех жанров. Обязательно.

**Что внутри:** Steel-man контр-аргументы с силой и нашим ответом.

Источник входных данных: лог red team из Фазы 6 (`findings/redteam_<date>.md`). HIGH-дефекты без закрытия → Open Questions.

**Антипаттерн:** Straw-man (слабые контр-аргументы). Должен быть самый сильный аргумент против — даже если убеждает.

**Композиция:** После основного содержимого, до closing. Минимум 2-3 в medium/deep.

**Шаблон:**

```markdown
## Counter-arguments (steel-man)

### CA1: <короткое название контр-аргумента>
**Против чего:** Q1 / F2 / TL;DR-1 / recommendation
**Кто говорит:** [s09](sources/09_*.md) (или «hypothetical steel-man» если нет source)
**Аргумент:** <как формулирует оппонент, дословно или близко>
**Сила:** низкая | средняя | высокая
**Наш ответ:**
- <почему мы всё-таки утверждаем что утверждаем>
- ИЛИ <принимаем, понижаем confidence до medium>
- ИЛИ <это open question, нужно ещё research>
**Что меняет в выводах:** <конкретное изменение или "ничего, выдерживаем"

### CA2: <название>
...

### CA3: <название>
...

### Поиск ещё противоположной позиции
- Намеренно искали ли контр-аргументы (≥1 целевой запрос)? <да/нет>
- Если не нашли сильного — это сигнал что либо тема трivial либо плохо искали
```

---

## Z2 — `open-questions`

**Когда:** Всегда. Что не закрыто и что копать дальше.

**Что внутри:** Список открытых вопросов с типом.

Источник входных данных: лог red team из Фазы 6 (`findings/redteam_<date>.md`). HIGH-дефекты без закрытия → Open Questions.

**Антипаттерн:** «Многое осталось неясным» без конкретики. Open Q должен быть actionable для next research.

**Композиция:** После `counter-arguments`. До `next-research`.

**Шаблон:**

```markdown
## Open questions

- **OQ1.** <конкретный вопрос>
  - Тип: «нет данных» | «противоречивые источники» | «нужен другой эксперт» | «методологически сложно»
  - Что бы помогло: <тип источника или approach>

- **OQ2.** <вопрос>
  - Тип: ...
  - Что бы помогло: ...

- **OQ3.** <вопрос>
  - Тип: ...

### Известные unknown unknowns
- Областью N мы не покрыли вообще — может скрывать relevant info
- Источники только на <язык>, могли пропустить <другой язык>
```

---

## Z3 — `next-research`

**Когда:** Всегда. Что копать дальше после этого ресёрча.

**Что внутри:** 2-3 темы для следующих ресёрчей с slug.

**Антипаттерн:** «Ещё много чего можно исследовать» — каждый next research должен быть конкретной темой с slug.

**Композиция:** После `open-questions`.

**Шаблон:**

```markdown
## Next research

- **Next 1:** <Тема>
  - Slug: `<slug-name>`
  - Почему именно эту: <логически вытекает из open questions / приоритетная>
  - Жанр: <предполагаемый — explainer/decision/etc>

- **Next 2:** <Тема>
  - Slug: `<slug-name>`
  - Почему: ...
  - Жанр: ...

- **Next 3:** <Тема>
  - Slug: `<slug-name>`
  - Почему: ...
```

---

## Z4 — `actionable-next-steps`

**Когда:** Decision, validation. Когда ресёрч должен переходить в действие.

**Что внутри:** Первые 3 действия после ресёрча.

**Антипаттерн:** Расплывчатые actions («подумать про X»). Каждый — конкретный act с владельцем и сроком.

**Композиция:** После `recommendation-conditional` в decision. После `verdict-conditional` в validation.

**Шаблон:**

```markdown
## Actionable next steps

### Action 1 — <короткое название>
**Что делать:** <конкретное действие>
**Owner:** <кто> (или «I» если solo)
**Когда:** <срок, по возможности абсолютная дата>
**Output:** <что должно появиться>
**Зависит от:** <предусловия если есть>

### Action 2 — ...
### Action 3 — ...

### Если что-то изменится (triggers)
- Если <X> произойдёт → пересмотри Action 1
- Если <Y> → запусти update этого ресёрча
- Если <Z> → re-evaluate recommendation
```

---

## Z5 — `map-of-sources`

**Когда:** Всегда. Группировка источников по типам.

**Что внутри:** Источники по типам с явным выделением opposition voices.

**Антипаттерн:** Скрывать excluded источники (low quality). Покажи что было excluded и почему.

**Композиция:** Всегда. До `metadata`.

**Шаблон:**

```markdown
## Map of sources

- **Primary (N):** [s01](sources/01_*.md), [s07](sources/07_*.md), [s12](sources/12_*.md)
- **Academic (N):** [s02](sources/02_*.md), [s05](sources/05_*.md), [s08](sources/08_*.md)
- **Industry-media (N):** [s04](sources/04_*.md), [s10](sources/10_*.md), [s13](sources/13_*.md)
- **Expert blogs (N):** [s06](sources/06_*.md), [s14](sources/14_*.md)
- **Opposition voices (N):** [s09](sources/09_*.md), [s11](sources/11_*.md), [s15](sources/15_*.md)
- **Excluded (low quality, N):** [s24], [s25] — total < 8, не использовались в выводах

### Покрытие
- Типов источников: N (из 7 возможных)
- A-grade quality (total ≥ 12): N
- B-grade (9-11): N
- Excluded (< 9): N

### Что отсутствует
- <тип источника которого не хватает> — почему

Полный список: [sources.csv](sources.csv).
```

---

## Z6 — `findings-index`

**Когда:** Если есть крупные findings вынесенные в отдельные `findings/FN.md` файлы.

**Что внутри:** Ссылки на findings с confidence.

**Антипаттерн:** Использовать когда findings нет — пропусти блок.

**Композиция:** После Q&A или основного содержимого. Перед `closing`.

**Шаблон секции в отчёте:**

```markdown
## Findings index

Атомарные тезисы вынесены отдельно для переиспользования в других ресёрчах:

- [F1: <тезис>](findings/F1.md) — confidence: high, базируется на s01, s07, s12
- [F2: <тезис>](findings/F2.md) — confidence: medium
- [F3: <тезис>](findings/F3.md) — confidence: high

Каждый findings можно цитировать из других ресёрчей по ID.
```

### Шаблон отдельного `findings/FN.md` файла

Используй для тезисов, которые:
- Сложнее одного блока в основном отчёте.
- Будут переиспользоваться в других ресёрчах.
- Заслуживают отдельной защиты со steel-man.

```markdown
---
id: F1
thesis: <тезис в одном предложении>
confidence: high | medium | low
sources: [s01, s07, s12, s15]
created: <YYYY-MM-DD>
status: active | superseded
---

# F1: <название тезиса>

## Тезис

<1-2 предложения, как формулируем>

## Поддерживающие факты

1. **<Факт A>** — из [s01](../sources/01_*.md):
   > «дословная цитата»

2. **<Факт B>** — из [s07](../sources/07_*.md):
   > «дословная цитата»

3. **<Факт C>** — из [s12](../sources/12_*.md):
   > «дословная цитата»

## Сильнейший контр-аргумент (steel-man)

<Самый сильный аргумент ПРОТИВ этого тезиса, который смог найти>

**Откуда:** [s09](../sources/09_*.md)
**Что говорит:** ...
**Почему всё-таки держимся тезиса:** ...
**Или: почему понижаем confidence:** ...

## Что это значит для decision

<Что меняется в зависимости от того, верен этот тезис или нет>

## Связанные тезисы / ресёрчи

- F2 — поддерживает
- F4 (из ресёрча `<slug>`) — конкурирует
```

---

## Z7 — `confidence-summary`

**Когда:** Длинные отчёты (deep) с многими findings. Когда читателю нужна сводка confidence.

**Что внутри:** Таблица всех claims с confidence.

**Антипаттерн:** Дублировать confidence из основного текста без новой инфы. Делай только если sumary value.

**Композиция:** Перед `map-of-sources`.

**Шаблон:**

```markdown
## Confidence summary

| Claim | Confidence | Why | Where in report |
|---|---|---|---|
| <claim 1> | high | 3 primary sources, replicated | Q1, F1 |
| <claim 2> | medium | 2 sources of mixed quality | Q3 |
| <claim 3> | low | single source, contested | Q5, CA2 |
| <claim 4> | high | direct primary source | F2 |

### Reading
- **High-confidence claims (N):** действуй на них без оглядки
- **Medium (N):** учитывай в planning, но валидируй ещё
- **Low (N):** не принимай решения только на них

### Если хочешь поднять confidence medium → high
- См. Open Questions OQ1, OQ3
- Или next research <slug>
```

---

## Z8 — `assumptions-log`

**Когда:** Любой ресёрч где есть явные допущения. Особенно forecast/projection.

**Что внутри:** Список допущений с описанием sensitivity.

**Антипаттерн:** Скрывать допущения. Если допущение неверно — verdict рушится.

**Композиция:** Перед `closing`. Может быть в `metadata` для коротких отчётов.

**Шаблон:**

```markdown
## Assumptions

Допущения на которых построен ресёрч. Если они неверны — verdict меняется.

### A1: <допущение>
**Почему предположил:** <reasoning>
**Доказательство (если есть):** [s05]
**Sensitivity:** high — если неверно, <что меняется в выводах>
**Confidence в допущении:** medium

### A2: <допущение>
**Почему:** ...
**Sensitivity:** low — даже если неверно, мало меняется
**Confidence:** high

### A3: <допущение>
**Почему:** "не нашёл противоположных данных"
**Sensitivity:** medium
**Confidence:** low — это weak assumption, worth testing

### Если несколько допущений рушатся одновременно
- Самые катастрофические комбинации: A1 + A3 → <что было бы>
- Robust к: failure of A2 alone, A4 alone
```

---

## Z9 — `glossary-final`

**Когда:** Длинные отчёты с обильной терминологией. Когда читатель может потеряться.

**Что внутри:** Финальный alphabetical glossary всех терминов из отчёта.

**Антипаттерн:** Дублировать `glossary-mini` или `glossary-full`. Использовать ОДИН тип glossary, не несколько.

**Композиция:** Перед `metadata`. Только если в начале не было полного glossary.

**Шаблон:**

```markdown
## Glossary (final)

В алфавитном порядке. Если термин определялся в тексте — короткая отсылка.

- **A** — <определение>. Введён в Q1.
- **B** — <определение>. См. mental-model.
- **C** — <определение>. Из [s07].
- **D** — <определение>.
- ...
```

---

## Z10 — `update-triggers`

**Когда:** Все ресёрчи. Что должно произойти, чтобы понадобился update.

**Что внутри:** Условия которые сделают ресёрч устаревшим.

**Антипаттерн:** «Когда что-то изменится» без конкретики. Должны быть observable triggers.

**Композиция:** Перед `metadata`. Помогает решить когда переоткрывать ресёрч.

**Шаблон:**

```markdown
## Update triggers

Этот ресёрч устареет если:

- **Time-based:** через <X месяцев>, потому что <area changes fast>
- **Event-based:**
  - <event 1> произойдёт (e.g., new regulation, key player exits market)
  - <event 2>
  - Появится contrary RCT (для validation)
- **Threshold-based:**
  - Если <metric X> превысит Y
  - Если появится >N новых entrants в landscape

### Watch list
- Подпись на <feed/newsletter>
- Quarterly check on <metric>
- Notify if <key person> publishes

### What an update would look like
- Запуск с `update <slug>` (см. update mode)
- Дельта-исследование: проверить только что изменилось
- Не повторять scoping и methodology — только обновить evidence
```

## Z11 — `refresh-targets` (отдельный файл)

**Когда:** все medium/deep ресёрчи. Z10 говорит **когда** обновлять, Z11 — **что конкретно проверять** при update. Без Z11 update теряет много времени на re-discovery.

**Где живёт:** не внутри финального отчёта, а **отдельным файлом** `research/<slug>/refresh_targets.md`. Это позволяет `update` mode сразу прочитать его и пойти проверять.

**Что внутри:** список конкретных entities, метрик, тематических маркеров, гипотез — всё что update будет реверифицировать.

**Композиция:** генерируется в Phase 7 (synthesis), после написания финального отчёта. Шаблон ниже — заполняй на основе того что реально использовалось в M-, N-, V-блоках.

**См. также:** `references/refresh_protocol.md` — как именно `update` использует этот файл.

**Шаблон `refresh_targets.md`:**

```markdown
---
slug: <slug>
generated_at: <YYYY-MM-DD>
parent_research: <YYYY-MM-DD_genre.md>
update_cadence: <"monthly" | "quarterly" | "event-driven" | "yearly">
---

# Refresh targets — <topic>

## 1. Entities to track

Companies/projects/products that the original research profiled in landscape blocks (M2, M5) or analyzed in compare blocks (C1-C5). Update will re-check these.

### <Company / Project Name>
- **Type:** <company | open-source project | research group | regulator>
- **Why in scope:** <e.g. «leader in segment X», «active competitor to focus company Y»>
- **Pages to monitor:**
  - Pricing: `<url>` (last hash: `<sha256 from sources/SN.md if available>`)
  - Careers: `<url>`
  - Blog/changelog: `<url>` (RSS if available: `<rss-url>`)
  - Crunchbase: `<crunchbase-permalink>` (if funded company)
- **Specific fields to watch:**
  - Pricing tier changes (especially «X added new tier» events)
  - CEO/CTO changes
  - Total funding raised
  - <other entity-specific>

### <Company 2>
(same template)

## 2. Numbers to refresh

Specific metrics anchored in original report's N-blocks. Update will re-fetch these and compare.

### <Metric name>
- **Source:** <FRED CPIAUCSL | World Bank SP.POP.TOTL | Statista 2026 industry report «...» | etc.>
- **API access:** <FRED API / World Bank API / manual fetch>
- **Last value:** <X.Y on YYYY-MM-DD>
- **What change matters:**
  - Direction reversal (e.g., growth → decline)
  - Magnitude > <X%> change from current
  - New methodology revision (Statista often revises previous-year estimates)
- **Anchored in:** <which blocks/claims in the report depend on this number>

### <Metric 2>
(same template)

## 3. Topic markers (for discovering NEW things)

Patterns that update will use to find new entrants, new publications, new datasets.

### GitHub topics
- `topic:<keyword-1>` — for finding new repos in domain
- `topic:<keyword-2>`
- Filter: `stars:>50 created:>last_research_date` (адаптировать дату при update)

### Academic concepts
- **OpenAlex concept ID:** `<C-XXXXXXX>` («<concept name>»)
- **Semantic Scholar paper IDs to cite-trace:** `<S2-paper-id>` («<paper title>»)
- **arXiv categories:** `<cs.LG, q-fin.TR, etc>`

### News keywords
- Primary: `<keyword combination>`
- Opposition / failure mode keywords: `<«X doesn't work», «X bankruptcy», etc>`

### Industry-specific
- Newsletter/feed: `<URL>` (manual check or RSS)
- Conference proceedings: `<conference name>` (annual; check post-event for new papers)

## 4. Hypotheses to re-test

Original report's H1-H4 (from plan.md section 9). Update will search for new opposing evidence to each.

### H1: «<verbatim hypothesis>»
- **Status at last research:** <supported | contradicted | inconclusive> (confidence: <H/M/L>)
- **Supporting sources (count):** <N> sources of types <Academic, Industry-media, ...>
- **Watch for:**
  - Replication failures: `«<H1 phrase> failed replication»`, `«<H1 phrase> doesn't generalize»`
  - Retractions: search RetractionWatch for cited papers
  - Counter-RCTs / new datasets that test the same claim

### H2: «<verbatim hypothesis>»
(same template)

## 5. Sources requiring re-verification (high-stakes only)

If specific sources are critical to the report's conclusions, they get extra re-check on update.

### sources/SN_<critical-source>.md
- **Why critical:** <«primary source for H1», «only source on regulatory status», etc.>
- **Re-check action:**
  - Verify URL still accessible (not 404)
  - If author/venue: check if retracted
  - If gov data: check for revised version
  - If company page: refetch and diff
```

**Anti-patterns:**

- ❌ Заполнять Z11 «from memory» — каждое поле должно ссылаться на блок из финального отчёта где оно использовалось
- ❌ Перечислять «все возможные источники» — это refresh_targets, а не bibliographic database. Только critical-path
- ❌ Без update_cadence — пользователь не поймёт когда возвращаться
- ❌ Без сохранённых hash/snapshot для entity pages — fingerprinting не работает
