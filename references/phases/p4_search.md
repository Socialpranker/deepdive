## Фаза 4. Поиск

**Model:** главный поток `sonnet` / `medium`. Sub-agents — **разные модели** по типу подзадачи (см. `model_routing.md` секция «Routing для sub-agents»): web/news/api-direct → `haiku`, academic/long-source → `sonnet`, heavy reasoning subtask → `opus`.

**Phase 4 is an orchestrator-driven loop, not a single salvo.** Round 1 executes the
approved plan (Phase 4.0 dispatch). After *every* round the orchestrator evaluates the
aggregated results and may spend a bounded *deviation* to launch another round. The
plan stays authoritative as the starting point; deviations are bounded and recorded.

**Phase 4 = 4 шага в строгом порядке (Round 1):** Dispatch → Кандидаты и отбор → Fetch → Save. Не пропускай Dispatch — без него Launch будет хаотичным.

### 4.0 Source Dispatch (НОВЫЙ обязательный шаг)

**До запуска суб-агентов** прогони каждый подвопрос из plan.md секции 11 (Подтемы ↔ Блоки mapping) через `source_dispatch.md`:

1. Открой `source_dispatch.md` → найди в Matrix строку под сигнал подвопроса
2. Запиши **primary / secondary / fallback каналы** в `plan.md` секцию 12 в формате который указан в конце `source_dispatch.md`
3. Если тема узкая или не матчится — выполни Discovery patterns (GitHub topics, awesome-lists registry, HuggingFace, PyPI/npm, data portals) и **запиши что нашёл** в секцию «Discovery executed»
4. Если decomposition recipe из `source_dispatch.md` добавляет подвопросы которых нет в plan.md — **верни в Phase 3** и расширь декомпозицию, потом продолжай

**Output 4.0:** заполненная секция 12 plan.md с per-subquestion sourcing strategy. Без этого 4.1 не запускается.

### 4.1 Кандидаты → отбор → чтение (medium/deep)

Широко и дёшево отбираем, узко и глубоко читаем. Бенчмарк 2026-10-28: 6 из 6 прогонов прочитали 16–19 источников первых запросов, Academic 0, 3–4 типа.

1. **Матрица запросов** до поиска: строки — сферы (academic, primary, media, expert, practice), столбцы — позиция к ведущей гипотезе (за / против / нейтрально). Запросы на EN и на языке рынка пользователя. Одна клетка — 1–2 запроса.
2. **Пул кандидатов** — `explore-haiku`, только WebSearch и API, без WebFetch: 60–100 строк (deep ≥100) в `candidates.csv`, колонки `url,title,snippet,channel,sphere,stance,vendor,round,target,selected`. Обязателен ≥1 вызов академического API (`api_sources/academic/`: openalex, semantic_scholar, arxiv, crossref; `channel` = имя API). Сюда же snowball: ссылки и «cited by» 2–3 лучших кандидатов через OpenAlex/Semantic Scholar.
3. **Отбор на чтение** — главный поток по таблице, не по текстам: medium 25–30, deep 35–45, `selected=Y`. Квоты прочитанного (гейт `validate_phases.py`):

   | Сфера | `type` источника | Минимум |
   |---|---|---|
   | наука | Academic | 2 |
   | первичка (доки, стандарты, регуляторы) | Primary | 3 |
   | медиа | Industry-media / General-media | 2 |
   | экспертные статьи и блоги | Expert-blog | 2 |
   | практики (инциденты, форумы, issues) | Forum | 2 |
   | против гипотезы | `hypothesis_evidence: contradicts` | 3 |
   | вендор (`caveat: vendor`, в т.ч. маркетинг конкурента) | — | не больше половины |

   Пересказы одного `root:` при квотах считаются одним источником. Квоту не закрыть честно (по теме нет науки) — `quota_waiver: <ключ> — <почему>` в `plan.md`, дописанный **после** отбора: причина ссылается на то, чего нет в `candidates.csv`. Бюджет — не причина. `count`, `candidates`, `round2` не снимаются вовсе; остальные ключи печатает валидатор. Гейт тогда предупреждает, а не блокирует, оговорка уходит в «Чего не знаем».
4. **Чтение** — `deepdive-fetcher` (haiku) получает список отобранных URL и диапазон id, а не тему: ищет он только на замену мёртвому URL. Затем `sonnet`/low батчами по 5–8 файлов дописывает в каждый `## Разбор` (`source_scoring.md`, шаблон файла); без карточки валидатор предупреждает.
5. **Второй раунд обязателен**: после первого чтения назови переменную, от которой зависит решение (из вилок Decision Spec: цена при нашем объёме, задержка, число людей), и добери ≥5 кандидатов `round=2`, `target=<переменная>`. Нашлось измерение — читай его вне квот.

Shallow: главный поток сам делает WebSearch+WebFetch и пишет `sources/NN.md`, без `candidates.csv` и квот.

### 4.2 Fetch & Dedup

- Используй встроенные WebFetch и WebSearch.
- Для API из `api_sources/` — Bash + curl + jq если ответ большой, иначе WebFetch.
- Если WebFetch вернул «unable to fetch from …» — это чаще всего robots.txt-исключение для AI-агентов, а не мёртвая страница. Прежде чем списать источник в `gaps`, прогони его через fetch ladder — `references/fetch_ladder.md` (двухтирный `fetch_source.py`, коды выхода, фид-фолбэк, PDF-обработка).
- Если источник за paywall — paywall fallback protocol в `channels.md` (preprint → archive → researchgate → …; пиратские зеркала не используются).
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

1. **Round 1 = the plan.** Run Phase 4.0 (Source Dispatch) → Phase 4.1 (candidate pool,
   selection by quotas, fetchers on the selected URLs) → 4.2 (dedup) → 4.3 (save sources). This always runs.
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
