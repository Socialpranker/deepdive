# MAP blocks — картография

Блоки для landscape-жанра и любых ресёрчей про карту области, игроков, связи.

---

## M1 — `categories`

**Когда:** Landscape. Деление области на категории до перечисления игроков.

**Что внутри:** Категории с определениями и количеством игроков.

**Антипаттерн:** Слишком много категорий (>6) — теряется польза. Перекрывающиеся категории — невозможно классифицировать.

**Композиция:** После `scope`. До `profile-card`.

**Шаблон:**

```markdown
## Categories

### Категория A: <название>
**Определение:** <что входит, по каким признакам>
**Игроков:** N
**Лидеры:** P1, P2

### Категория B: <название>
**Определение:** ...
**Игроков:** M
**Лидеры:** ...

### Категория C: пограничные / новые
**Что это:** игроки которые не вписываются в A/B чётко

**Принцип классификации:** <по чему делим — по бизнес-модели / технологии / target audience>
```

---

## M2 — `profile-card`

**Когда:** Landscape (по 1 на игрока). Конкурент-анализ.

**Что внутри:** Структурированная карточка игрока: origin, scale, ниша, strengths/weaknesses, link.

**Антипаттерн:** Разный шаблон для разных игроков — не сравнить. Один шаблон для всех в landscape.

**Композиция:** После `categories`. По одной карточке на игрока, группированы по категориям.

**Шаблон:**

```markdown
## Player profiles

### Категория A

#### P1: <название>
- **Origin:** founded YYYY, <country>
- **Funding / scale:** $XM <round>, ~N employees, ARR ~$Y
- **Что делает:** <одна фраза>
- **Ниша / unique:** <чем выделяется>
- **Strengths:** ... [s03]
- **Weaknesses / critique:** ... [s07]
- **Tech / approach:** <stack или ключевой подход>
- **Customers / users:** <ICP, известные кейсы>
- **Links:** [website](url) · [docs](url) · [blog](url)
- **Status:** active | growing | declining | acquired by X (date)

#### P2: <название>
(same structure)

### Категория B

#### P3: ...
```

---

## M3 — `positioning-map`

**Когда:** Landscape когда есть 2 осмысленные оси для позиционирования.

**Что внутри:** 2×2 ASCII карта + обоснование осей.

**Антипаттерн:** Оси без обоснования — кажется arbitrary. Каждая ось должна быть осмысленной для области.

**Композиция:** После `profile-card`. До `trends`.

**Шаблон:**

```markdown
## Positioning map

Axes:
- **X axis: Niche ↔ Mainstream** — широта целевой аудитории
- **Y axis: Low capability ↔ High capability** — глубина продукта по core feature

```
              High capability
                    │
       P1 ●         │         ● P3
                    │
                    │   ● P5
   Niche ───────────┼─────────── Mainstream
                    │
       P2 ●         │         ● P4
                    │
              Low capability
```

**Обоснование размещения:**
- P1 (high/niche): сильные продукты, узкая аудитория [s03]
- P3 (high/mainstream): лидер по всем фронтам [s07]
- P2 (low/niche): нишевая утилитка
- P4 (low/mainstream): bottom of market
- P5 (mid/mainstream): emerging

**Movement (за последний год):**
- P5 движется к high-cap
- P2 в стагнации
```

---

## M4 — `trends`

**Когда:** Landscape, market analysis. Что происходит со временем.

**Что внутри:** Что растёт / умирает / появляется / консолидация vs фрагментация.

**Антипаттерн:** Trends на ощущениях. Каждый trend — конкретный observable signal или цифра.

**Композиция:** После `positioning-map`. До `white-spaces`.

**Шаблон:**

```markdown
## Trends

### Что растёт
- **<trend>** — signal: <конкретное наблюдение>, источник [s03]
- **<trend>** — ...

### Что умирает
- **<trend>** — signal: ..., [s07]
- ...

### Что появляется (emerging)
- **<trend>** — signal: <маркер появления>, [s11]
- ...

### Консолидация vs фрагментация
- **Консолидация:** N acquisitions за последний год — кто кого
- **Новые entrants:** M новых компаний — где
- **Direction:** консолидация / фрагментация / нейтрально

### Что НЕ движется (несмотря на ожидания)
- <thing> — ожидали что вырастет, не растёт. Почему: ...
```

---

## M5 — `white-spaces`

**Когда:** Landscape для product strategy. Где никого нет — возможности.

**Что внутри:** Пустые ниши с обоснованием почему пустые.

**Антипаттерн:** White space без объяснения почему он пустой — может быть «никому не нужно», а не возможность.

**Композиция:** После `trends`. Логически вытекает из карты.

**Шаблон:**

```markdown
## White spaces

### WS1: <ниша>
**Где никого:** <описание ниши>
**Почему пустая (наши гипотезы):**
- A: рынок маленький → no opportunity
- B: технически сложно → opportunity для тех кто решит
- C: никто не пробовал → opportunity для first mover
**Самая вероятная причина:** <одна из A/B/C> [s05]

### WS2: <ниша>
...

### Sanity check
Спросили ли мы людей в индустрии, точно ли пустая ниша? Если нет — пометка «may be incomplete».
```

---

## M6 — `genealogy`

**Когда:** Custom для academic/tech областей. Кто откуда вышел.

**Что внутри:** Деревья происхождения: компании из компаний, идеи из идей, fork'и.

**Антипаттерн:** Линейная история без ветвлений — упрощение. Реальная genealogy всегда дерево.

**Композиция:** Дополнение к `categories` или `network-graph`. Для глубокого понимания области.

**Шаблон:**

```markdown
## Genealogy

```
                ┌─────────────┐
                │ FoundationCo│ (2010)
                │  (parent)   │
                └──────┬──────┘
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
     ┌────────┐   ┌────────┐    ┌────────┐
     │ Spin A │   │ Spin B │    │ Spin C │
     │ (2015) │   │ (2017) │    │ (2019) │
     └───┬────┘   └────────┘    └───┬────┘
         │                          │
    ┌────┴────┐                 ┌───┴────┐
    ▼         ▼                 ▼        ▼
  Fork A1  Fork A2          Sub C1   Sub C2
```

**Лица:**
- FoundationCo основан <X, Y, Z>. Многие алюмни — founders современных игроков.
- Spin A — основан <ex-FoundationCo> в 2015. См. карточку выше.
- ...

**Что это даёт понять:** <напр.: «вся область выросла из 3 школ мысли»>
```

---

## M7 — `ranked-list`

**Когда:** Custom для «топ-N» вопросов. Когда нужно отранжировать.

**Что внутри:** Ранжированный список с критериями ранжирования и обоснованием.

**Антипаттерн:** Ранжирование без критериев — сразу спорно. Прозрачно покажи критерии.

**Композиция:** Альтернатива `profile-card` для landscape когда ранжирование важнее категоризации.

**Шаблон:**

```markdown
## Top N

**Критерий ранжирования:** <по чему ранжируем> (по убыванию).

| Rank | Player | Score | Key reason | Source |
|---|---|---|---|---|
| 1 | A | 92 | <одна фраза> | [s03] |
| 2 | B | 85 | <одна фраза> | [s07] |
| 3 | C | 80 | <одна фраза> | [s11] |
| 4 | D | 72 | <одна фраза> | [s15] |
| 5 | E | 68 | <одна фраза> | [s19] |

**Что НЕ вошло (close to making list):** F, G.

**Caveats:**
- Ранжирование зависит от критерия — при другом критерии порядок другой
- Confidence в ранжировании: high для 1-2, medium для 3-5
```

---

## M8 — `value-chain`

**Когда:** Industry analysis. Цепочка создания ценности по звеньям.

**Что внутри:** Звенья цепи + игроки на каждом + где value capture.

**Антипаттерн:** Цепочка из 2 звеньев — почти всегда оверсимплификация.

**Композиция:** Дополнение к `categories`. Альтернативное измерение для landscape.

**Шаблон:**

```markdown
## Value chain

```
[Sources of raw data] → [Aggregation] → [Processing/ML] → [APIs] → [Apps] → [End users]
       ↑                      ↑                ↑              ↑          ↑
   Players:                Players:         Players:       Players:   Players:
   - Origin1               - Aggr1          - ML1          - API1     - App1
   - Origin2               - Aggr2          - ML2          - API2     - App2
```

**На каком звене захватывается ценность:**
- Sources of raw data: low margin, commoditized
- Aggregation: medium margin, network effects
- **Processing/ML: highest margin** ← где деньги
- APIs: medium margin, lock-in
- Apps: variable

**Vertical integration:**
- Кто owns несколько звеньев: <player X owns aggregation + processing + API>
- Pure-play на одном звене: <player Y, Z>
```

---

## M9 — `network-graph`

**Когда:** Relationships in field. Кто с кем связан.

**Что внутри:** Mermaid `graph LR` — основная форма. ASCII или таблица отношений — фолбэк без сборки документа.

**Антипаттерн:** Граф, где связи не типизированы, — картинка «все со всеми». Каждое ребро несёт тип (`partners`/`competes`/`integrates`/`acquired`) и расшифровывается в легенде под схемой.

**Композиция:** Дополнение к `categories`. Когда связи между игроками важнее категоризации.

**Шаблон:**

````markdown
## Network

```mermaid
%% caption: связи игроков рынка на <дата>
graph LR
  A -- partners --> B
  A -- partners --> C
  D -- competes --> E
  D -- integrates --> A
```

**Типы связей:**
- **partners:** формальное партнёрство, есть public announcement
- **competes:** прямой конкурент по >50% продукта
- **integrates:** один использует другого как dependency
- **acquired:** owned

**Ключевые наблюдения:**
- A — central hub, partners с большинством
- D и E — бывшие competitors, теперь integrates after pivot
- ...
````

**Рендер:** см. E13 — тот же конвейер `build_report.py` → `mmdc` → «Схема N».

---

## M10 — `funding-tree`

**Когда:** Startup ecosystem. Инвестиционные связи.

**Что внутри:** Кто кого инвестировал, ownership chains, последние rounds.

**Антипаттерн:** Только sizes без даты — funding устаревает быстро.

**Композиция:** Дополнение к `profile-card` для landscape стартапов.

**Шаблон:**

```markdown
## Funding tree

### Investors (top)
- **VC A:** портфель: P1, P3, P5. Total deployed: $50M.
- **VC B:** портфель: P2, P4. Specializes in <stage/sector>.
- **Strategic Z:** инвестирует только в <профиль>, владеет P6.

### Latest rounds
| Player | Round | Date | Amount | Lead investor | Valuation |
|---|---|---|---|---|---|
| P1 | Series B | 2025-09 | $30M | VC A | $200M |
| P3 | Seed | 2025-04 | $3M | VC C | $20M |
| P5 | Series A | 2024-11 | $12M | VC A | $60M |

### Ownership patterns
- VC A — biggest player, ~30% индустрии в портфеле
- Cross-holdings: VC A и VC B участвовали вместе в P5
- M&A pattern: <если есть>

### Total capital in space
~$<X>M за последние 24 месяца. Тренд: <ускорение / замедление>.
```

---

## M11 — `geographic-distribution`

**Когда:** Geo-distributed теме (global market analysis).

**Что внутри:** Где игроки/события расположены, plus гео-различия.

**Антипаттерн:** Только список стран без объяснения почему важно.

**Композиция:** Дополнение для landscape с географической дифференциацией.

**Шаблон:**

```markdown
## Geographic distribution

### По регионам

| Region | N players | Top examples | Specific характер |
|---|---|---|---|
| North America | 12 | A, B, C | enterprise-focused |
| EU | 7 | D, E, F | compliance-driven |
| Asia | 5 | G, H | mobile-first |
| Rest | 3 | I | emerging |

### Hot spots (где плотность)
- San Francisco Bay Area: 6 players
- London: 3 players
- Singapore: 2 players

### Regional specialization
- **NA:** enterprise integration, B2B
- **EU:** GDPR-native, data sovereignty
- **Asia:** consumer apps, mobile UX

### Cross-region patterns
- Multi-region: <кто>
- Single-region only: <кто>
- Expanding: <кто, куда>
```

---

## M12 — `lifecycle-stage`

**Когда:** Industry maturity analysis. Где каждый игрок на S-curve.

**Что внутри:** Игроки распределены по стадиям lifecycle.

**Антипаттерн:** Считать что все на одной стадии. Реально — разные.

**Композиция:** Альтернативное измерение для landscape. Дополнение к `categories`.

**Шаблон:**

```markdown
## Lifecycle stages

### Early / experimental (pre-product-market-fit)
- P5 — pilot users, no clear ICP yet
- P8 — recent launch, traction TBD
- P9 — still in beta

### Growth (PMF + scaling)
- P1 — 10x YoY, hiring rapidly
- P3 — Series B, expanding geo
- P7 — strong product, expanding to enterprise

### Mature (stable, generating profit)
- P2 — predictable revenue, stable team
- P6 — slow growth but profitable

### Decline / sunset
- P10 — losing customers, no recent updates
- P4 — acquired and absorbed (effectively sunset)

### Industry overall stage
- **Stage:** growth phase
- **Indicators:** N new entrants/year, M acquisitions, increasing total funding
- **Likely next:** consolidation in 18-24 months
```
