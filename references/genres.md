# Genres — пресеты блоков

Шесть жанров финального отчёта. Пять стандартных — пресеты блоков. Шестой — custom (собирается под вопрос).

## Как использовать

1. После reframing (Фаза 1) скилл определяет жанр по формулировке вопроса.
2. Скилл объявляет ОДНОЙ строкой: «Жанр: <genre>. Блоки: <list>. Ок?».
3. Пользователь подтверждает / правит набор.
4. Финальный `<date>_<genre>.md` строится из блоков в указанном порядке.

## Каналы поиска по жанрам

См. `channels.md` за полный каталог <!--gen:count:channels-->28<!--/gen--> каналов. Здесь — рекомендованный mix per genre.

| Жанр | Primary channels | Secondary | Use sparingly |
|---|---|---|---|
| **explainer** | web-general, academic, wikipedia-references, code-github | books-literature, video-talks, expert-individual | social-twitter |
| **decision** | web-general, forum-discussion, industry-reports, code-github (tech) | expert-individual, surveys-polls, podcasts | conference-proceedings |
| **landscape** | competitive-signals, news-current, industry-reports, product-analytics | patents, forum-discussion, trade-associations, industry-specific | social-twitter |
| **validation** | academic, preprint-servers, conference-proceedings | forum-discussion (opposition), expert-individual, surveys-polls, archive-historical | patents |
| **qa** | web-general + 2-3 по подтемам | varies | — |
| **custom** | под выбранные blocks | varies | — |

## Stat-источники по жанрам

См. `stat_sources/INDEX.md`. Релевантные категории:

| Жанр | Релевантные категории stat_sources |
|---|---|
| **explainer** | core/science.md, core/gov_macro.md (если macro), industries/<industry>.md (если industry) |
| **decision** | core/consulting_industry.md, core/consumer_digital.md (для tech), industries/<industry>.md, core/companies_public.md (для evaluating public co) |
| **landscape** | core/companies_private.md, core/companies_public.md, core/consulting_industry.md, industries/<industry>.md |
| **validation** | core/science.md (retractions, replications), core/health.md (если medical), core/gov_macro.md (для quantitative claims) |
| **qa** | varies by subtopic |
| **custom** | под выбранные blocks (`data-table` → numbers categories, `risk-register` → relevant industry, etc.) |

## Эвристика выбора жанра

Скилл смотрит на формулировку вопроса. Сигналы:

| Сигналы в вопросе | Жанр |
|---|---|
| «как устроен», «как работает», «что такое», «расскажи про устройство», «mental model» | **explainer** |
| «что выбрать», «X или Y», «какой лучше», «брать ли», «куда вложить», «какую купить» | **decision** |
| «карта», «кто делает», «игроки в», «landscape», «competitive», «кто пишет про» | **landscape** |
| «правда ли», «работает ли», «эффективен ли», «вредно ли», «действительно ли», «миф или факт» | **validation** |
| «изучи», «разбери», «копни», открытый вопрос без явного жанра, серия связанных Q | **qa** |
| «по показателям», «по метрикам», «по критериям», смесь жанров, нестандартное | **custom** |

Если эвристика даёт несколько жанров — выбери доминирующий + предложи custom как альтернативу.

---

## qa — открытое исследование

**Когда:** Серия связанных вопросов, meta-research, тема без явного жанра.

**Required blocks:** `tldr`, `qa-list`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `actionable-next-steps` [Z4], `confidence-summary` [Z7].

**Recommended order:**
```
1.  tldr                      [F1]
2.  background                [F9]
3.  decision-context          [F2]   (если есть decision)
4.  qa-list                   [A3]   ← главная секция
5.  hypotheses-outcome        [A4]   (если в plan были hypotheses)
6.  counter-arguments         [Z1]   (medium/deep)
7.  open-questions            [Z2]
8.  next-research             [Z3]
9.  confidence-summary        [Z7]
10. so-what-for-you           [Z12]  (перед Z4)
11. actionable-next-steps     [Z4]
12. map-of-sources            [Z5]
13. findings-index            [Z6]   (если есть)
14. metadata                  [F5]
```

**Опциональные additions:**
- `key-finding-callout` [F6] если есть один доминирующий insight

---

## explainer — «как устроен X»

**Когда:** Понять устройство темы, mental model, не decision.

**Required blocks:** `tldr`, `mental-model`, `stepwise`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `actionable-next-steps` [Z4], `confidence-summary` [Z7].

**Recommended order:**
```
1.  tldr                      [F1]
2.  background                [F9]
3.  prerequisites             [E8]   (если нужно читателю)
4.  glossary-mini             [E2]   ← термины перед схемой
5.  mental-model              [E1]   ← схема устройства
6.  stepwise                  [E4]   ← как работает
7.  variants                  [E5]   (если есть варианты реализации)
8.  worked-example            [E6]   (для education-style)
9.  common-confusions         [E7]
10. failure-modes             [E10]  (для технических тем)
11. edge-cases                [E11]  (опционально)
12. design-rationale          [E12]  (для architecture explainer)
13. counter-arguments         [Z1]
14. open-questions            [Z2]
15. next-research             [Z3]
16. confidence-summary        [Z7]
17. so-what-for-you           [Z12]  (перед Z4)
18. actionable-next-steps     [Z4]
19. map-of-sources            [Z5]
20. metadata                  [F5]
```

**Подмножество для глубокого technical:**
- + `flow-diagram` [E13] или `state-machine` [E14] вместо stepwise
- + `analogy` [E9] для совсем сложных тем
- + `tech-stack-context` [X6] для tech foundation

**Опциональные additions:**
- `historical-context` [X4] если «как мы здесь оказались» важно

---

## decision — «что выбрать X или Y»

**Когда:** Сравнение опций для принятия решения. С явной рекомендацией.

**Required blocks:** `tldr`, `decision-context`, `options-matrix`, `recommendation-conditional`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `confidence-summary` [Z7].

**Recommended order:**
```
1.  tldr                      [F1]
2.  background                [F9]
3.  executive-summary         [F7]   (опционально, для стейкхолдеров)
4.  decision-context          [F2]   ← рамка решения
5.  options-matrix            [C1]
6.  weighted-score            [C2]   (если критерии неравнозначны)
7.  feature-matrix            [C10]  (для product decisions)
8.  pros-cons-each            [C9]   (alternative to matrix для quick)
9.  best-fit-when             [C3]
10. trade-offs                [C5]
11. reversibility-stakes      [C4]
12. cost-benefit              [C8]   (для финансовых)
13. risk-register             [A6]   (для рискованных)
14. pre-mortem                [C7]   (high-stakes)
15. migration-path            [C11]  (если обратимо)
16. decision-tree             [C12]  (для сложных мультиусловных)
17. kill-criteria             [C13]
18. counter-arguments         [Z1]
19. recommendation-conditional [C6]  ← финальная рекомендация
20. confidence-summary        [Z7]
21. so-what-for-you           [Z12]  (перед Z4)
22. actionable-next-steps     [Z4]
23. assumptions-log           [Z8]
24. open-questions            [Z2]
25. next-research             [Z3]
26. map-of-sources            [Z5]
27. metadata                  [F5]
```

**Подмножества:**
- **Quick decision (shallow):** tldr + decision-context + pros-cons-each + best-fit-when + recommendation-conditional + sources + metadata
- **High-stakes (deep):** все блоки + pre-mortem + kill-criteria

---

## landscape — «карта области»

**Когда:** Игроки/решения в области, без приоритета выбора.

**Required blocks:** `tldr`, `scope`, `categories`, `profile-card`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `actionable-next-steps` [Z4], `confidence-summary` [Z7].

**Recommended order:**
```
1.  tldr                      [F1]
2.  background                [F9]
3.  scope                     [F3]   ← границы карты
4.  categories                [M1]   ← деление области
5.  profile-card × N          [M2]   ← карточки игроков по категориям
6.  key-people                [P3]   (для глубоких landscape)
7.  positioning-map           [M3]
8.  value-chain               [M8]   (industry analysis)
9.  network-graph             [M9]   (relationships)
10. funding-tree              [M10]  (startup ecosystem)
11. geographic-distribution   [M11]  (geo-distributed)
12. lifecycle-stage           [M12]
13. trends                    [M4]
14. white-spaces              [M5]   (для product strategy)
15. ecosystem                 [X7]   (broader context)
16. counter-arguments         [Z1]
17. open-questions            [Z2]
18. next-research             [Z3]
19. update-triggers           [Z10]  ← landscape устаревает быстро
20. confidence-summary        [Z7]
21. so-what-for-you           [Z12]  (перед Z4)
22. actionable-next-steps     [Z4]
23. map-of-sources            [Z5]
24. metadata                  [F5]
```

**Подмножества:**
- **Minimal landscape:** tldr + scope + categories + profile-cards + trends + sources + metadata
- **Investment-focused:** + funding-tree + key-people + lifecycle-stage + white-spaces

---

## validation — «правда ли X»

**Когда:** Проверка claim. С verdict.

**Required blocks:** `tldr`, `claim-precise`, `falsification-criteria`, `evidence-graded`, `verdict-conditional`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `confidence-summary` [Z7].

**Recommended order:**
```
1.  tldr                      [F1]
2.  background                [F9]
3.  claim-precise             [F4]   ← точная формулировка
4.  scope                     [F3]   ← где применимо
5.  base-rates                [V4]   (для probabilistic claims)
6.  falsification-criteria    [V1]   ← ДО evidence
7.  evidence-graded           [V2]   ← FOR/AGAINST
8.  conflicting-evidence      [V3]   (если есть)
9.  replication-status        [V7]   (для научных claims)
10. sample-size-analysis      [V8]   (для quantitative)
11. methodology-critique      [V9]   (deep)
12. expert-opinion            [P7]   (если expert-driven)
13. bayesian-update           [V10]  (для probabilistic)
14. verdict-conditional       [V5]   ← главный verdict
15. what-would-change-verdict [V6]
16. common-confusions         [E7]   (часто claim путают с X)
17. counter-arguments         [Z1]
18. confidence-summary        [Z7]
19. so-what-for-you           [Z12]  (перед Z4)
20. actionable-next-steps     [Z4]   (что делать с этим verdict)
21. assumptions-log           [Z8]
22. open-questions            [Z2]
23. next-research             [Z3]
24. map-of-sources            [Z5]
25. metadata                  [F5]
```

**Подмножества:**
- **Quick validation:** tldr + claim-precise + falsification-criteria + evidence-graded + verdict-conditional + sources + metadata
- **Научный validation:** все + methodology-critique + replication-status + sample-size

---

## custom — собирается под вопрос

**Когда:** Вопрос не подходит ни под один стандартный жанр. Гибридные вопросы. Специфические аналитические задачи.

**Required (всегда):** `tldr`, `map-of-sources`, `metadata`. Для medium/deep — обязательно ещё: `background` [F9], `so-what-for-you` [Z12], `actionable-next-steps` [Z4], `confidence-summary` [Z7].

**Эвристика подбора блоков:**

Скилл смотрит на сигналы в вопросе:

| Сигнал | Добавь блок |
|---|---|
| «по показателям / метрикам / KPI» | `data-table` [A1], `metric-tracker` [N1] |
| «топ N», «лучшие», «ранжируй» | `ranked-list` [M7] |
| «как X эволюционировал», «история X» | `timeline` [A2], `historical-context` [X4], `genealogy` [M6] |
| «риски X», «опасности» | `risk-register` [A6], `failure-modes` [E10] |
| «SWOT X», «strengths/weaknesses» | `swot` [A5] или `swot-extended` [A11] |
| «макро среда», «среда» | `pestle` [A12] |
| «стоит ли инвестировать», «cost / benefit» | `cost-benefit` [C8], `unit-economics` [N4] |
| «конкуренты + показатели» (как у меня) | `data-table` + `profile-card` + `trends` + `competitors` mix |
| «команда», «кто работает», «структура» | `team-org` [P2], `key-people` [P3] |
| «пользователи / клиенты» | `persona` [P1], `user-journey` [P4] |
| «почему так / root cause» | `5-whys` [A10], `dependency-graph` [A7] |
| «узкие места», «bottleneck» | `bottleneck-analysis` [A8] |
| «силы за и против изменения» | `force-field` [A9] |
| «до и после» | `before-after` [A13] |
| «forecast / прогноз» | `forecast` [N7] + `historical-data` [N8] |
| «market size / TAM» | `market-sizing` [N2] |
| «regulatory / законы» | `regulatory` [X1] |
| «culturally / по культурам» | `cultural-context` [X3] + `geo-context` [X2] |
| «политика / sanctions / geopolitics» | `political-context` [X5] |
| «экосистема» | `ecosystem` [X7] |
| «mental model / устройство» (как часть гибрида) | + `mental-model` [E1] + `glossary-mini` [E2] |
| «выбор» (как часть гибрида) | + `options-matrix` [C1] + `recommendation-conditional` [C6] |

**Базовая обвязка для custom:**
```
1. tldr [F1]
2. background [F9]
3. scope [F3] (если границы важны)
4. <выбранные блоки по эвристике>
5. counter-arguments [Z1]
6. open-questions [Z2]
7. next-research [Z3]
8. confidence-summary [Z7]
9. so-what-for-you [Z12] (перед actionable-next-steps)
10. actionable-next-steps [Z4]
11. map-of-sources [Z5]
12. metadata [F5]
```

**Подтверждение пользователя:** скилл выводит одной строкой:
```
"Custom-отчёт. Блоки: tldr, scope, data-table, profile-card×N, trends,
counter-args, open-q, sources. Ок? (yes / убрать X / добавить Y)"
```

### Примеры готовых custom-наборов

**Конкуренты по показателям:**
```
[tldr, scope, data-table, profile-card×N, trends, counter-args, open-q, next-research, sources, metadata]
```

**Hybrid explainer + decision (типа «как работают X и что выбрать»):**
```
[tldr, mental-model, glossary-mini, stepwise, options-matrix, best-fit-when,
recommendation-conditional, counter-args, sources, metadata]
```

**Risk analysis под решение:**
```
[tldr, decision-context, risk-register, failure-modes, force-field, pre-mortem,
actionable-next-steps, sources, metadata]
```

**Cost-benefit personal decision:**
```
[tldr, scope, cost-benefit, pros-cons-each, decision-tree, recommendation-conditional,
actionable-next-steps, sources, metadata]
```

**Historical deep-dive:**
```
[tldr, scope, timeline, historical-context, genealogy, key-people, mental-model,
counter-args, open-q, sources, metadata]
```

**Behavioral analysis:**
```
[tldr, scope, persona, user-journey, behavioral-patterns, incentive-structure,
counter-args, open-q, sources, metadata]
```

---

## Правила композиции

### Что всегда есть
- `tldr` [F1] — первый блок (но пишется ПОСЛЕДНИМ)
- `map-of-sources` [Z5] — обязательно
- `metadata` [F5] — последний (footer)
- Для medium/deep во ВСЕХ жанрах — обязательно: `background` [F9], `so-what-for-you` [Z12], `actionable-next-steps` [Z4], `confidence-summary` [Z7] (см. секции жанров выше).

### Mutually exclusive (не использовать вместе)
- `glossary-mini` ИЛИ `glossary-full` ИЛИ `glossary-link` — выбирай ОДИН
- `swot` ИЛИ `swot-extended` — не оба
- `options-matrix` без весов ИЛИ `weighted-score` — обычно один (но допустимо оба для full decision)
- `mental-model` ИЛИ `flow-diagram` ИЛИ `state-machine` — выбирай по типу системы

### Порядок зависимостей
- `glossary-*` идёт ПЕРЕД `mental-model` (термины перед схемой)
- `background` [F9] идёт СРАЗУ ПОСЛЕ `tldr`/перед `scope` — контекст «почему вопрос» перед рамкой и содержимым
- `scope` ПЕРЕД основными блоками (рамка перед содержимым)
- `claim-precise` ПЕРЕД `falsification-criteria` ПЕРЕД `evidence-graded`
- `base-rates` ПЕРЕД `evidence-graded` (prior перед update)
- `counter-arguments` ПОСЛЕ основного содержимого, ПЕРЕД closing
- `recommendation-conditional` ПОСЛЕ всех comparison-блоков
- `so-what-for-you` [Z12] ПОСЛЕ `confidence-summary`/`map-of-sources` секций, но ПЕРЕД `actionable-next-steps` [Z4] — сначала проекция на кейс, потом конкретные действия

### Density rules
- Shallow отчёт: 5-9 блоков
- Medium отчёт: 9-15 блоков
- Deep отчёт: 15-25 блоков
- Не плоди блоки для plumage. Только если каждый отвечает на конкретную часть вопроса.
