# Block Library — INDEX

76 блоков в 10 категориях. Композируемые секции для финального отчёта.

## Как использовать

1. Скилл определяет жанр (см. `../genres.md`) или собирает custom.
2. Скилл загружает только нужные категории `blocks/<category>.md` (progressive loading).
3. В каждом файле категории — Markdown-шаблон каждого блока готовый для копирования.
4. В финальном отчёте блоки идут в порядке из `plan.md` → `blocks:` списка.

## Категории

| Cat | Файл | Блоки | Назначение |
|---|---|---|---|
| FRAME | [frame.md](frame.md) | F1-F8 | Рамка отчёта: TL;DR, scope, claim, metadata |
| EXPLAIN | [explain.md](explain.md) | E1-E14 | Объяснение устройства: mental model, glossary, mechanism |
| COMPARE | [compare.md](compare.md) | C1-C13 | Сравнение и выбор: matrices, scoring, trade-offs |
| MAP | [map.md](map.md) | M1-M12 | Картография: profiles, positioning, trends |
| VALIDATE | [validate.md](validate.md) | V1-V10 | Проверка истинности: falsification, evidence grades |
| ANALYZE | [analyze.md](analyze.md) | A1-A13 | Структурированный анализ: SWOT, timeline, root cause |
| CLOSE | [close.md](close.md) | Z1-Z11 | Закрытие: counter-args, open Q, next research |
| PEOPLE | [people.md](people.md) | P1-P7 | Люди, команды, поведение: persona, journey, incentives |
| NUMBERS | [numbers.md](numbers.md) | N1-N8 | Количественные: метрики, market sizing, forecasts |
| CONTEXT | [context.md](context.md) | X1-X7 | Внешний контекст: регуляторика, гео, культура |

## Полная таблица всех 76 блоков

### FRAME

| ID | Slug | Что | Когда |
|---|---|---|---|
| F1 | `tldr` | TL;DR 2-4 строки с confidence | Всегда |
| F2 | `decision-context` | Что решаем, варианты, constraints, stakes | Decision, custom-decision |
| F3 | `scope` | Что входит/НЕ входит, срез на дату | Landscape, validation, любой границы |
| F4 | `claim-precise` | Точная формулировка проверяемого утверждения | Validation |
| F5 | `metadata` | Author/date/depth/version/status footer | Всегда |
| F6 | `key-finding-callout` | Главный single insight выделенный | Длинные отчёты |
| F7 | `executive-summary` | 1-страничный TL;DR для стейкхолдеров | Decision/landscape для не-технических |
| F8 | `glossary-link` | Ссылка на внешний/общий глоссарий | Если есть проектный glossary |

### EXPLAIN

| ID | Slug | Что | Когда |
|---|---|---|---|
| E1 | `mental-model` | ASCII-схема устройства + 3-5 сущностей | Explainer, технические |
| E2 | `glossary-mini` | 5-10 терминов с определениями | Explainer всегда, сложная лексика |
| E3 | `glossary-full` | Развёрнутый глоссарий с примерами | Custom если терминология критична |
| E4 | `stepwise` | Пошаговый механизм (1, 2, 3...) | Explainer, sequential процессы |
| E5 | `variants` | Варианты реализации + где встречаются | Explainer |
| E6 | `worked-example` | Реальный кейс с проходом сценария | Explainer, education |
| E7 | `common-confusions` | Что НЕ означает X, с чем путают | Explainer, validation |
| E8 | `prerequisites` | Что нужно знать до чтения | Технические со сложным background |
| E9 | `analogy` | Аналогия из знакомой области | Сложные технические темы |
| E10 | `failure-modes` | Как и почему ломается | Technical explainer, debugging |
| E11 | `edge-cases` | Граничные случаи и обработка | Технические explainer |
| E12 | `design-rationale` | Почему так спроектировано, alternatives дизайна | Architecture explainer |
| E13 | `flow-diagram` | Поток данных/процесса (ASCII или Mermaid) | Process explainer |
| E14 | `state-machine` | States + transitions + triggers | Технические системы со state |

### COMPARE

| ID | Slug | Что | Когда |
|---|---|---|---|
| C1 | `options-matrix` | Таблица опций × критерии (без весов) | Decision |
| C2 | `weighted-score` | Опции × критерии с весами + total | Decision когда неравнозначные критерии |
| C3 | `best-fit-when` | Для каждой опции — «бери если X» | Decision всегда |
| C4 | `reversibility-stakes` | One-way vs two-way door + stakes | Decision |
| C5 | `trade-offs` | Что теряешь выбирая каждый вариант | Decision всегда |
| C6 | `recommendation-conditional` | «Бери X если Y, иначе Z» | Decision финальный |
| C7 | `pre-mortem` | «Через год X провалился, почему» | Decision high-stakes |
| C8 | `cost-benefit` | Cost vs benefit структурированно | Custom для финансовых |
| C9 | `pros-cons-each` | Pro/Con списки для каждой опции | Quick decision, light-weight |
| C10 | `feature-matrix` | Features × Options (есть/нет/частично) | Product comparison |
| C11 | `migration-path` | Как делать миграцию A→B | Decision с обратимостью |
| C12 | `decision-tree` | Дерево «если X — Y, иначе W» | Сложные мультиусловные |
| C13 | `kill-criteria` | Когда отказаться от каждой опции | Decision рискованные |

### MAP

| ID | Slug | Что | Когда |
|---|---|---|---|
| M1 | `categories` | Деление области на категории с определениями | Landscape |
| M2 | `profile-card` | Карточка игрока: founded/scale/strength/weakness | Landscape ×N, конкурент-анализ |
| M3 | `positioning-map` | 2×2 ASCII карта с обоснованием осей | Landscape |
| M4 | `trends` | Что растёт/умирает/появляется | Landscape, market analysis |
| M5 | `white-spaces` | Где пустые ниши | Landscape для product strategy |
| M6 | `genealogy` | Кто откуда вышел, кто кого fork | Custom для academic/tech |
| M7 | `ranked-list` | Топ-N с обоснованием | Custom для «топ X» |
| M8 | `value-chain` | Цепочка ценности: кто на каком звене | Industry analysis |
| M9 | `network-graph` | Кто с кем связан | Relationships in field |
| M10 | `funding-tree` | Инвестиционные связи, ownership | Startup ecosystem |
| M11 | `geographic-distribution` | Где игроки расположены | Geo-distributed |
| M12 | `lifecycle-stage` | Кто на какой стадии (early/growth/mature/decline) | Industry maturity |

### VALIDATE

| ID | Slug | Что | Когда |
|---|---|---|---|
| V1 | `falsification-criteria` | Что заставит признать ложным (заранее) | Validation всегда |
| V2 | `evidence-graded` | Evidence FOR/AGAINST с quality A/B/C | Validation |
| V3 | `conflicting-evidence` | Противоречивые данные + почему расходятся | Validation, любой с conflicts |
| V4 | `base-rates` | Apriori probability / prior | Validation медицинских/научных |
| V5 | `verdict-conditional` | «Правда при X, ложь при Y» | Validation всегда |
| V6 | `what-would-change-verdict` | Какие данные сдвинули бы verdict | Validation |
| V7 | `replication-status` | Воспроизведено ли, кем, сколько раз | Научный validation |
| V8 | `sample-size-analysis` | Размер выборки, statistical power | Quantitative validation |
| V9 | `methodology-critique` | Критика методологии источника | Validation научных |
| V10 | `bayesian-update` | Prior + evidence → posterior | Probabilistic validation |

### ANALYZE

| ID | Slug | Что | Когда |
|---|---|---|---|
| A1 | `data-table` | Параметрическая таблица объект × показатель | Custom «по показателям» |
| A2 | `timeline` | Хронология событий с датами | Custom историческое / sequential |
| A3 | `qa-list` | Q→A атомарные пары с confidence + sources | Q&A всегда |
| A4 | `hypotheses-outcome` | Таблица гипотез: confirmed / partial / contradicted | Q&A, validation |
| A5 | `swot` | Strengths/Weaknesses/Opportunities/Threats | Business/product analysis |
| A6 | `risk-register` | Список рисков: probability × impact | Custom рискованные |
| A7 | `dependency-graph` | Что от чего зависит, critical path | Project planning, system |
| A8 | `bottleneck-analysis` | Где узкие места и почему | Performance, ops |
| A9 | `force-field` | Forces FOR vs AGAINST change | Change analysis, Lewin |
| A10 | `5-whys` | Цепочка «почему» до root cause | Root cause |
| A11 | `swot-extended` | SWOT + actionable из каждого квадранта | Strategic analysis |
| A12 | `pestle` | Political/Economic/Social/Tech/Legal/Environmental | Macro analysis |
| A13 | `before-after` | До и после изменения с метриками | Impact analysis |

### CLOSE

| ID | Slug | Что | Когда |
|---|---|---|---|
| Z1 | `counter-arguments` | Steel-man контр-аргументы | Medium/deep всегда |
| Z2 | `open-questions` | Что не закрыто, что копать | Всегда |
| Z3 | `next-research` | 2-3 следующих ресёрча | Всегда |
| Z4 | `actionable-next-steps` | Что делать СЕЙЧАС (первые 3 действия) | Decision, validation |
| Z5 | `map-of-sources` | Источники по типам + opposition voices | Всегда |
| Z6 | `findings-index` | Ссылки на findings/FN.md | Если есть крупные findings |
| Z7 | `confidence-summary` | Сводка confidence по всем findings | Длинные отчёты |
| Z8 | `assumptions-log` | Список допущений | Любой ресёрч с допущениями |
| Z9 | `glossary-final` | Финальный глоссарий из отчёта | Длинные с обильной терминологией |
| Z10 | `update-triggers` | Что должно произойти для update | Все ресёрчи (life cycle) |
| Z11 | `refresh-targets` (отдельный файл) | Что конкретно проверять при update — entities, numbers, hypotheses | Medium/deep — обязательно |

### PEOPLE

| ID | Slug | Что | Когда |
|---|---|---|---|
| P1 | `persona` | Профили пользователей: needs/behaviors/pain | UX, product |
| P2 | `team-org` | Структура команды/организации, роли | Конкурент-анализ, due diligence |
| P3 | `key-people` | Карточки ключевых людей (founder, lead) | Конкуренты, индустрия |
| P4 | `user-journey` | Сценарий пути: steps + emotions + friction | UX, product design |
| P5 | `behavioral-patterns` | Паттерны поведения участников | Behavioral analysis |
| P6 | `incentive-structure` | Кто что получает, какие стимулы | Game theory, market design |
| P7 | `expert-opinion` | Карточка мнения эксперта с конфликтом интересов | Expert-driven validation |

### NUMBERS

| ID | Slug | Что | Когда |
|---|---|---|---|
| N1 | `metric-tracker` | Конкретные метрики с цифрами | «по метрикам», «по KPI» |
| N2 | `market-sizing` | TAM/SAM/SOM | Market research |
| N3 | `growth-rates` | YoY/CAGR с источниками | Growth analysis |
| N4 | `unit-economics` | CAC, LTV, payback period, margin | SaaS/business analysis |
| N5 | `cost-breakdown` | Структура затрат | Финансовый анализ, due diligence |
| N6 | `benchmark-numbers` | Industry benchmarks для сравнения | Performance analysis |
| N7 | `forecast` | Прогнозы будущих значений с диапазонами | Прогнозирование, planning |
| N8 | `historical-data` | Временной ряд исторических значений | Data analysis, trend |

### CONTEXT

| ID | Slug | Что | Когда |
|---|---|---|---|
| X1 | `regulatory` | Регуляторный контекст: законы, compliance | Финтех, медтех, regulated |
| X2 | `geo-context` | Различия по странам/регионам | Глобальные рынки, юрисдикции |
| X3 | `cultural-context` | Культурные особенности | Кросс-культурные темы |
| X4 | `historical-context` | Что было до и почему важно сейчас | Historical, deep explainer |
| X5 | `political-context` | Политические факторы | Geopolitics, sanctions |
| X6 | `tech-stack-context` | Технологии в основе, dependencies | Tech research |
| X7 | `ecosystem` | Экосистема вокруг темы: соседи | Platform analysis |

## Progressive loading discipline

При 76 блоках критично не загружать всё в контекст.

```
Главный поток:
1. Читает SKILL.md (рамка)
2. После reframing → читает references/genres.md
3. Определяет жанр или сборку
4. Читает blocks/INDEX.md (только индекс — это файл)
5. Для standard жанра → читает 2-4 файла категорий
6. Для custom → выбор блоков эвристикой, читает только их категории
```

Не грузи INDEX.md и категорийный файл одновременно — INDEX.md содержит достаточно для принятия решения о том, какие блоки взять.

## Композиция блоков

Каждый категорийный файл содержит для каждого блока секцию **Композиция** — с какими блоками работает хорошо, с какими дублирует, какие исключают друг друга.

Базовые правила:
- `tldr` пишется ПОСЛЕДНИМ (после остальных блоков).
- `counter-arguments` идёт после основного содержимого, перед closing.
- `metadata` всегда в самом конце как footer.
- `map-of-sources` всегда есть, даже если короткий.
- Дублирующиеся блоки исключают друг друга: `glossary-mini` ИЛИ `glossary-full`, не оба.
