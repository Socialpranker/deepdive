---
name: deepdive
description: Meta-research под вопрос или решение. Веб-поиск, академические источники, Q&A отчёт; каждый источник — отдельный файл с цитатами и метаданными для повторного использования. Использовать когда нужна основа под решение, для деск-ресёрча, валидации гипотезы или чтобы понять как устроен X. Триггеры — "deep research", "глубокое исследование", "проведи ресёрч", "сделай ресёрч", "изучи тему", "разбери тему", "исследуй", "копни глубоко", "deep dive", "ресёрчни".
---

# Deepdive — meta-research с дисциплиной

Серьёзное многошаговое исследование под вопрос или решение. Каждый источник = файл, отчёт построен как Q&A, тезисы атомарны и пере-используемы.

## Когда применять

- Прямо просит «deep research / глубокое исследование / проведи ресёрч / изучи тему / разбери».
- Сравнить N институций, продуктов, методологий, рынков (НО: если N конкурентов по фиксированной матрице — это competitive-teardown, не сюда).
- Подготовить материал для стратегии, бизнес-плана, доклада, статьи.
- Проверить гипотезу или валидировать решение через внешние данные.
- Meta-research — «понять как устроен X», «карта области Y», ответить на серию вопросов.

## Когда НЕ применять

- Быстрая фактоверка («когда родился Моцарт») — отвечай напрямую, без скилла.
- Сравнение N конкурентов по структурированной 12-dimension матрице → `competitive-teardown`.
- Research под Anthropic SDK / Claude API → `claude-api`.
- Brainstorm без поиска данных → `brainstorming` / `grill-me`.
- Ответ уже в проекте — сначала grep/чтение, потом решай нужен ли веб-поиск.

## Глубина — определяется по теме

**Жёсткого дефолта нет.** Выбирай каждый раз по сложности вопроса и стоимости решения, которое поддерживаешь.

| Режим | Источников | Суб-агентов | Когда |
|---|---|---|---|
| shallow | 5–7 | 0 | первичная навигация, тема знакома, low-stakes решение |
| medium | 12–18 | 2–3 | нетривиальная тема, среднее решение |
| deep | 25–35+ | 4–5 | high-stakes решение, стратегия, серьёзный анализ |

Объяви выбранный режим в начале и обоснуй: «делаю medium — тема нетривиальна, решение middle-stakes».

**Заодно объяви model routing** (один раз, после Genre+Plan): какие фазы на какой модели, estimated cost. Пример:

```
Routing: Phase 1/3/6 на Opus/high (reframing+plan+adversarial),
Phase 4 sub-agents на Haiku/Sonnet, Phase 7 synthesis на Sonnet/high.
Estimated ~$2 (vs ~$8 если бы всё на Opus). Скажи если нужно по-другому —
"всё на opus" / "cheap mode" / "default".
```

Детали — `references/model_routing.md`.

## Перед стартом — discover existing

ДО фазы reframing проверь что уже есть в проекте. Опциональное — если файлов/папок нет, иди дальше.

1. **Куда сохранять** (см. секцию ниже) — определи целевую папку.
2. **Существующие ресёрчи**: если целевая папка уже есть, перечисли содержимое. Если есть похожий slug → спроси «это update?». Если да — режим update (см. ниже).
3. **CLAUDE.md / CLAUDE.local.md**: если есть — прочитай, учти в reframing (терминология проекта, workflow, кросс-референсы).
4. **memory/MEMORY.md**: если есть — прочитай индекс, поищи упоминания темы. Учти в reframing («в памяти X зафиксировано — мы это подтверждаем или пересматриваем?»).

Цель: не дублировать сделанное. Не из любопытства, не «на всякий случай ещё раз».

## Куда сохранять — 3-уровневая логика

Папка-цель определяется автоматически. Не хардкодь.

```
Уровень 1 — явный сигнал:
  CLAUDE.md / CLAUDE.local.md упоминают research-папку → используй её
  Существует одна из: research/, 06_Деск-ресёрч/, docs/research/, notes/research/
  → используй существующую

Уровень 2 — автодетекция типа проекта:
  pyproject.toml / package.json / Cargo.toml / go.mod / mix.exs → tech → research/
  Только .md / .pdf / .docx без манифестов → notes/гуманитарный → 06_Деск-ресёрч/

Уровень 3 — фоллбэк:
  Не git-репо или пустая папка → ~/deep-research/<slug>/ (глобальная домашняя)
```

Покажи выбранный путь ОДИН раз: «Сохраню в `research/<slug>/`. Ок?» Дальше пиши молча.

## Режим update

Если пользователь говорит `update <slug>` или «обнови ресёрч <тема>»:

**Цель update:** **дельта**, не replay. Найти что изменилось с last_research_date, написать diff-файл. Старый отчёт остаётся как есть; новый создаётся **только если** изменения существенные (после прочтения diff'а — решение пользователя).

**Детальный протокол:** `references/refresh_protocol.md`. Ниже — high-level порядок:

1. **Pre-flight check** — прочитай:
   - `<targetfolder>/<slug>/plan.md` (last_research_date, гипотезы, подвопросы)
   - `<targetfolder>/<slug>/refresh_targets.md` (что отслеживать — entities, numbers, hypotheses)
   - Последний `<date>_<genre>.md` (что было сказано — чтобы видеть что изменилось)
2. **Если `refresh_targets.md` нет** (старый ресёрч до этого протокола) — сначала сгенерируй его из final report + plan.md, используя шаблон Z11 (см. `blocks/close.md`).
3. **4 категории дельты** в targeted поиске (date filters от last_research_date):
   - **New entrants** — Crunchbase, GitHub topics, HuggingFace, news (новые компании/проекты)
   - **Entity diff** — fingerprinting tracked entities (pricing, careers, funding)
   - **Numbers refresh** — re-fetch FRED/WB/industry numbers, compare
   - **Adversarial trigger** — OpenAlex/arXiv/Retraction Watch на новые публикации
4. **Verified-no-change секция** — что перепроверили и ничего не изменилось. Это **тоже результат**.
5. **Output: `diffs/<YYYY-MM-DD>_delta.md`** — компактный список изменений + recommended actions (см. шаблон в `refresh_protocol.md`).
6. **Adversarial trigger HIGH** → re-run Phase 6 (только эту часть) на Opus с новой публикацией как input.
7. **Новый отчёт `<новая_дата>_<genre>.md`** — **только если** delta существенный (HIGH severity или несколько MEDIUM). Решает пользователь после прочтения delta. Старый отчёт в frontmatter получает `status: superseded by <новая_дата>_<genre>.md`. Старый `plan.md` копируется как `plan.md` (новая версия), `version: update-N`, `parent: <дата>_<genre>.md`, секция 16 changelog заполнена.

**Cost для типового update:** ~$0.40 (vs ~$2 за полный medium ресёрч).

**Model routing для update:** Pre-flight `sonnet`/low, search-этапы (1-4) `haiku`/low с `sonnet` для academic, synthesis delta — `sonnet`/medium, adversarial re-run — `opus`/high.

## Workflow — <!--gen:count:phases-->11<!--/gen--> фаз (1–7, включая 3.5, 3.7, 5.5 и 6.5)

Детали каждой фазы — в `references/workflow.md`. **Модель и effort на каждую фазу** — в `references/model_routing.md` (Opus/Sonnet/Haiku matrix). Здесь high-level.

1. **Reframing** [`opus`/high] — переписать вопрос, зафиксировать решение, сформулировать 2–4 опровергаемые гипотезы + (medium/deep) multi-perspective персоны для охвата (STORM) + **router по профилю вопроса** (классифицировать тип: фактологический→плоско / многошаговый→least-to-most L1→L2 / реляционный→графы / сравнительный→матрица — тип направляет декомпозицию и подсказывает режим глубины). См. `references/question_reframing.md`.
2. **Genre & block selection** [`sonnet`/medium] — определить жанр отчёта (qa/explainer/decision/landscape/validation/custom) и набор блоков. Подтвердить пользователю одной строкой. См. `references/genres.md` и `references/blocks/INDEX.md`.
3. **Plan** [`opus`/medium] — записать `plan.md` (5 секций: HEADER → SCOPE → STRUCTURE → EXECUTION → TRACKING). Включает: user context, time-box, acceptance criteria, discovered existing, glossary, жанр + blocks + rationale, гипотезы, risk register, subtopic↔blocks mapping (+ **least-to-most level** — для многошаговых вопросов «X учитывая Y»: подвопросы по уровням L1→L2 с накоплением контекста между ними, а не плоский параллельный список; для независимых подвопросов остаётся плоско), information sourcing strategy (каналы + stat-источники + API endpoints), opposition queries, stop-criteria, notes для tracking. См. `workflow.md` → Фаза 3 для полного шаблона.
3.5. **Capability Discovery** [`sonnet`/low] (опциональная для shallow, рекомендуется для medium, обязательна для deep) — audit env vars для API ключей, map подтемы → доступные APIs, fallback на upstream awesome-lists для unknown gaps, сводный отчёт пользователю. См. `references/capability_discovery.md`.
3.7. **Plan-review gate** [`sonnet`/low] (shallow — skip; medium — обязательна) — единственная human-in-the-loop контрольная точка ПЕРЕД дорогой Фазой 4. Показать сжатый план (вопрос как понял + решение + жанр + гипотезы + персоны + каналы + стоп-критерий + routing) и дать утвердить/поправить. Жёсткость по режиму: **deep — показать и ЖДАТЬ явного «Ок»** перед запуском суб-агентов; **medium — soft** (показать, продолжить если нет возражений); **shallow — skip**. Правка плана ДО исполнения — самый дешёвый рычаг качества (Gemini: «biggest lever over output quality»). Заодно enforcement-точка: пустой план-блок = пропущенная фаза. Clarification-триаж (нужны ли уточняющие вопросы) наследуется из Фазы 1. См. `references/plan_gate.md`.
4. **Поиск** [main `sonnet`/medium; sub-agents per-task: `haiku` для web/api, `sonnet` для academic/long-source, `opus` для heavy reasoning subtask] — 4 шага: (4.0) **Source Dispatch** — прогнать каждый подвопрос через `source_dispatch.md` matrix, заполнить plan.md секцию 12. (4.1) Launch — для medium/deep: суб-агенты `subagent_type=general-purpose` (нужен Write) в параллель, каждому свой диапазон номеров источников (`s01-s09`, `s10-s19`, ...); для shallow — главный поток сам. (4.2) Fetch & dedup. (4.3) Save в `sources/NN_slug.md` — пишет сам агент, в главный поток возвращаются только index-строки. Loop: **cheap goal-check** (Haiku после раунда — per-subquestion `goal_status` met/partial/unmet + чего не хватает, направляет следующий раунд и удешевляет Opus-evaluation) → bounded deviation между раундами (trajectory-чек claims, ревизия outline) + **no-progress circuit breaker** (2 раунда подряд без новой информации → стоп, нерешённое в Open Questions — не жечь бюджет на фантом). См. `references/source_dispatch.md`, `references/subagents_v2.md`, `references/workflow.md` → Фаза 4.
5. **Claims-ledger + триангуляция** [`haiku`/low] — из index-строк собирается `claims.csv` (claim_id, sources, status, confidence, primary_source, **source_caveat**). Механическая триангуляция: ≥3 источника И ≥2 типа → `triangulated`; primary-first — confidence не выше `medium` без primary-источника. **Скепсис на входе**: помечай источник `vendor`/`self-reported`/`disputed:sNN` при скоринге — тезис на такой цифре не получает `high` (симметрично primary-first), чтобы синтез не доверял величине vendor-бенчмарка (red team ловит это поздно). Loop: gap-волна на строки не-triangulated, максимум 2 круга, иначе `data-insufficient`. См. `references/source_scoring.md` и `references/workflow.md` → Фаза 5.
5.5. **Evidence-фильтр** [`sonnet`/low] (shallow — skip; medium/deep — обязательно) — relevance-фильтр на ВХОДЕ синтеза (симметрично 6.5, что проверяет выход). По каждой паре (claim, source): CRAG-классификатор Correct/Ambiguous/Incorrect по дословным цитатам → drop нерелевантных под этот claim → извлечь relevant-only цитаты в отдельный слой `evidence/CN.md`. `sources/NN.md` НЕ трогаются (архив). Наивная подача всего найденного в синтез *снижает* качество (Search-o1 33%→24%). Claim без единого relevant-источника → `data-insufficient` или до-поиск. Синтез (Фаза 6) читает `evidence/`, а не весь пул. См. `references/evidence_filter.md`.
6. **Синтез + multi-angle red team** [red-team суб-агенты `opus`/high **обязательно** для deep, `sonnet`/high для medium; synthesis `sonnet`/high] — собрать `<date>_<genre>.md` из блоков, затем: draft → claim ledger → N параллельных враждебных ролей (Skeptic / Contrarian / Gap-hunter) как `general-purpose` суб-агенты → триаж по severity → ОДИН раунд ремедиации HIGH (точечный до-поиск или caveat) → финал. Finder ≠ fixer. Гейт: shallow=R1 инлайн, medium=R1+R2, deep=R1+R2+R3 обязательно. См. `references/adversarial_pass.md` и `references/blocks/`.
6.5. **Verify** [`haiku`/low] (medium/deep — обязательно) — runtime-проверка цитат по двум осям: (1) **liveness** — ссылка жива (`check_citations.py` → `.verify/citations.json`); (2) **faithfulness** — источник реально подтверждает тезис (entailment claim ⊨ цитата; пары берутся из `evidence/CN.md` Фазы 5.5, RAGAS-декомпозиция + ALCE claim⊨quote → SUPPORTED/PARTIAL/UNSUPPORTED). Вердикты пишутся в `.verify/faithfulness.json` (I/O-контракт — единый источник истины, его читают F10-header и rubric axis 3, никто не пересчитывает). Битые/неподтверждающие источники чинятся (re-search), смягчаются (overclaim → слабее) или тезис уходит в Open Questions. Verification-header F10 несёт ОБЕ оси; отчёт не «готов» без него. Per-source faithfulness — defensible-фича против закрытых DR-продуктов (рынок массово врёт цитатами: Tow Center >60% error rate). См. `references/runtime_verification.md`.
7. **Refresh targets** [`sonnet`/medium] (medium/deep — обязательно) — извлечь entities/numbers/hypotheses/topic-markers из финального отчёта в `refresh_targets.md`. Это точка входа для будущих `update <slug>` — без неё каждый update тратит время на re-discovery «что отслеживать». См. блок Z11 в `references/blocks/close.md` и `references/refresh_protocol.md`.

## Stop-criteria — по содержанию, не по бюджету

Бюджета на количество WebSearch/WebFetch **нет**. Качество > скорость.

**Останавливайся когда:**
- Все 2–4 гипотезы либо подтверждены ≥3 разнотипными источниками, либо опровергнуты ≥3, либо явно отмечены как «данных мало».
- Прошёл целевой поиск противоположной позиции (≥1 запрос вида «X criticism / counter-evidence / against X / problems with X») и проанализировал результаты.
- Покрыты 4+ типа источников: первичные / академические / отраслевые медиа / обсуждения или противники.
- НЕТ роста новой информации — последние 3–5 источников повторяют то же, что уже есть.

**Не останавливайся:**
- Источники друг другу противоречат → копай за причиной противоречия.
- Все источники одного типа → добей разнообразие целевым поиском.
- Есть сильный контр-аргумент без своего опровержения/подтверждения → найди.
- Не было ни одного целевого поиска оппозиции → сделай.

**Тупик:**
- Третий подряд поиск возвращает источники total < 8 → тема плохо исследована или плохо ищем. Останавливайся, фиксируй в Open Questions «литература слабая», предлагай альтернативные пути (интервью, эксперимент).

## Output structure

Целевая папка `<root>/<slug>/`:

```
<slug>/
├── plan.md                          # Фаза 3 — план + changelog (секция 16) + notes (секция 15)
├── sources.csv                      # индекс всех источников с оценками
├── claims.csv                       # Фаза 5 — claim-ledger (claim/sources/status/confidence)
├── sources/                         # один файл = один источник (с метаданными + цитаты)
│   ├── 01_<short-slug>.md
│   ├── 02_<short-slug>.md
│   └── ...
├── evidence/                        # Фаза 5.5 — relevant-only цитаты под claim (medium/deep); sources/ не трогаются
│   ├── C1.md
│   └── ...
├── findings/                        # атомарные тезисы (опционально, для крупных)
│   ├── F1_<short>.md
│   └── ...
├── refresh_targets.md               # Фаза 7 — что отслеживать при будущих update (medium/deep)
├── .verify/                         # Фаза 6.5 — артефакты верификации (I/O-контракт)
│   ├── citations.json               #   liveness (check_citations.py)
│   └── faithfulness.json            #   faithfulness-вердикты SUPPORTED/PARTIAL/UNSUPPORTED
├── diffs/                           # дельта-файлы от update <slug> (если были update'ы)
│   ├── 2026-08-15_delta.md
│   └── 2026-11-20_delta.md
└── <YYYY-MM-DD>_<genre>.md          # финальный отчёт — суффикс по жанру
```

**Note:** отдельный `_changelog.md` не создаётся — changelog встроен в `plan.md` секцию 16 (заполняется только для update-режима).

**Имя финального отчёта:** суффикс по жанру
- Q&A: `<date>_qa.md`
- Explainer: `<date>_explainer.md`
- Decision: `<date>_decision.md`
- Landscape: `<date>_landscape.md`
- Validation: `<date>_validation.md`
- Custom: `<date>_custom.md`

**Шаблоны:**
- `sources/NN.md` — см. `references/source_scoring.md`
- `claims.csv` — claim-ledger, см. `references/source_scoring.md` (раздел «Claims-ledger»)
- `<date>_<genre>.md` — собирается из блоков, см. `references/genres.md` (пресеты) и `references/blocks/` (шаблоны блоков)
- `findings/FN.md` — атомарный тезис, см. `references/blocks/close.md` (блок Z6)

## После завершения — finish-up

0. **Собери детерминированные артефакты** (не руками):
   - `sources.csv` из `sources/NN.md`: `python scripts/build_sources_csv.py --research-dir <root>/<slug>`. Это единый источник колонок (`url,title,type,channel,...`) — не собирай CSV вручную grep'ом, схема разъедется.
   - Liveness-верификация Фазы 6.5 пишется **прямо в `.verify/`** (не в `eval/output/`): `python eval/check_citations.py --research-dir <root>/<slug> --json --out <root>/<slug>/.verify/citations`. Без `--out` файл уйдёт в `eval/output/` и phase-gate его не найдёт. Faithfulness (`.verify/faithfulness.json`) пишется на шаге Фазы 6.5 Layer 2.
1. **Phase-gate — БЛОКЕР, не совет.** Прогони `python scripts/validate_phases.py --research-dir <root>/<slug> --strict`. Он читает `mode:` из frontmatter и проверяет, что каждая обязательная для режима фаза оставила свой артефакт (`plan.md`, `sources/` или `sources.csv`, `claims.csv`, для medium/deep — `evidence/`, `.verify/*.json`, `refresh_targets.md`, финальный отчёт). **Ресёрч НЕ «готов», пока gate красный** — ровно как отчёт не «готов» без verification-header F10 (см. `runtime_verification.md`). Красный exit ⇒ фаза пропущена ⇒ **вернись к пропущенной фазе, доделай, перезапусти gate — и только после зелёного переходи к шагу 2**. Не показывай путь, не пиши резюме, не рапортуй «готово» с красным gate. Это машинная страховка против «методология исполняется только дисциплиной модели» — сам enforcement тоже должен быть enforced, иначе gate — просто ещё один неисполняемый абзац.
2. Покажи путь markdown-ссылкой: `[research/<slug>/2026-XX-XX_<genre>.md](research/<slug>/2026-XX-XX_<genre>.md)`.
3. Краткое резюме в чат: 3 ключевых ответа + 1 главный контр-аргумент + что не нашли (5–7 строк).
4. Предложи 2–3 следующих ресёрча, которые логически следуют.
5. **Если в проекте есть `memory/`** — предложи 1–3 memory candidates:
   ```
   По итогам — кандидаты в memory:
   - [project] Тезис X (confidence: high, 3 источника) → файл memory/<topic>.md
   - [reference] Авторитетный источник Y по теме Z

   Сохранить?
   ```
6. **Humanizer.** Если в системе есть `anthropic-skills:humanizer-ru` — вызови его на финальный `<date>_<genre>.md` для чистки канцелярита. Опциональное.

## Что НЕ делать

- Не пропускать `discover existing` — рискуешь дублировать готовый ресёрч.
- Не пропускать reframing — даже если запрос «вроде понятен».
- Не пропускать Plan-review gate (Фаза 3.7) в medium/deep; для deep — не запускать суб-агентов Фазы 4, пока пользователь не подтвердил план. Гейт без ожидания ответа (для deep) = не гейт.
- Не выводить только в чат — всегда сохраняй файлы.
- Не обходить ограничения WebFetch через bash/curl.
- Не использовать источники с total < 8 как основу для выводов.
- Не пропускать multi-angle red team в medium/deep.
- Для fetch+save (Фаза 4.1) и red team (Фаза 6) — `general-purpose` с явным диапазоном номеров, не `Explore` (read-only, только для разведки).
- Не пропускать gap-волну (нетриангулированные строки `claims.csv`, max 2 круга) и не давать confidence выше `medium` без primary-источника.
- Не оставлять «висящие» утверждения без ссылки на конкретный `sources/NN.md`.
- **Не рапортовать «готово» с красным phase-gate.** `validate_phases.py --strict` красный ⇒ фаза пропущена ⇒ доделать и перезапустить, а не показывать результат. Gate — блокер finish, как verification-header F10, а не необязательная проверка.
- Не запускать суб-агентов последовательно — только параллельно в одном сообщении.
- Не сжимать sources/ в один файл — теряется поиск и переиспользование между ресёрчами.
- Фаза 5.5: не переписывать/обрезать `sources/NN.md` (архив) — фильтр пишет только в `evidence/`. Не пропускать 5.5 в medium/deep и не фильтровать по credibility/`total` вместо релевантности фрагмента к claim.
- Фаза 6.5 faithfulness: не доверять факту наличия ссылки — проверять entailment claim⊨quote явно (даже сильные системы врут цитатами в ~50% случаев). Вердикты писать в `.verify/faithfulness.json` (единый источник) и не пересчитывать их в rubric/F10. Пары брать из `evidence/CN.md`, не пересканировать `sources/` (дублирует 5.5). Судить по дословной цитате, не по summary.

## Slug format

URL-friendly: латиница, цифры, дефисы. Пример:
- «Postgres logical replication vs CDC tooling» → `postgres-replication-vs-cdc`
- «What's the market for vertical farming in EU» → `vertical-farming-eu-market`
- «How does WebAssembly work under the hood» → `webassembly-under-the-hood`

Если slug не очевиден — сгенерируй и покажи в начале фазы 2 для подтверждения.

## References — когда читать

Прогрессивная подгрузка: загружай файл когда дошёл до фазы — не превентивно. При большой block library это критично для контекста.

**Базовые (всегда):**
- `references/workflow.md` — детали <!--gen:count:phases-->11<!--/gen--> фаз (включая опц. 3.5) (читать в начале medium/deep).
- `references/question_reframing.md` — шаблоны Фазы 1 + clarification-триаж.
- `references/plan_gate.md` — **Plan-review gate** (Фаза 3.7): единый checkpoint перед поиском, жёсткость по режиму (deep — ждать «Ок», medium — soft, shallow — skip), шаблон план-блока.
- `references/genres.md` — пресеты блоков <!--gen:count:genres-->6<!--/gen--> жанров + эвристика выбора (Фаза 2) + каналы по жанрам.
- `references/blocks/INDEX.md` — индекс <!--gen:count:blocks-->105<!--/gen--> блоков по 10 категориям (после выбора жанра).
- `references/channels.md` — <!--gen:count:channels-->29<!--/gen--> каналов поиска (включая api-direct) с query patterns, paywall fallbacks (Фаза 3-4).
- `references/stat_sources/INDEX.md` — навигационная карта 33 категорий статистических источников (Фаза 3-4).
- `references/api_sources/INDEX.md` — каталог <!--gen:count:api-->39<!--/gen-->+ API endpoints (10 категорий) для programmatic доступа (Фаза 3-4).
- `references/capability_discovery.md` — workflow фазы 3.5: env vars audit + capability mapping + discovery (medium/deep).
- `references/awesome_lists_registry.md` — upstream awesome-lists для discovery когда мой каталог не покрыл (Фаза 3.5).
- `references/source_dispatch.md` — **recommendation engine** для Phase 4.0: matrix «сигнал в подвопросе → primary/secondary/fallback каналы», decomposition recipes для типовых тем, discovery patterns когда каталог не покрыл. Обязательное чтение перед launch sub-agents.
- `references/model_routing.md` — **выбор модели и effort** (Opus/Sonnet/Haiku × low/medium/high) на каждую фазу и тип sub-agent'а. Matrix экономики и качества: где не экономить (Phase 1/6), где наоборот не переплачивать (Phase 4.1 sub-agents). Override-механики для пользователя.
- `references/refresh_protocol.md` — **протокол update**: 4 категории дельты (new entrants, entity diff, numbers refresh, adversarial trigger), шаблон `diffs/<date>_delta.md`. Используется в режиме `update <slug>`. Дополняется блоком Z11 `refresh-targets` из `blocks/close.md`.

**Категорийные файлы (только нужные для выбранного жанра/blocks):**
- `references/blocks/frame.md` — F1-F10: TL;DR, scope, background, claim, metadata, verification header.
- `references/blocks/explain.md` — E1-E14: mental-model, glossary, mechanism.
- `references/blocks/compare.md` — C1-C13: matrices, scoring, trade-offs.
- `references/blocks/map.md` — M1-M12: profiles, positioning, trends.
- `references/blocks/validate.md` — V1-V10: falsification, evidence grades.
- `references/blocks/analyze.md` — A1-A13: data tables, SWOT, root cause.
- `references/blocks/close.md` — Z1-Z12: counter-args, open Q, next research, so-what-for-you.
- `references/blocks/people.md` — P1-P7: persona, journey, incentives.
- `references/blocks/numbers.md` — N1-N8: metrics, market sizing, forecasts.
- `references/blocks/context.md` — X1-X7: regulatory, geo, culture.

**По фазам:**
- `references/source_scoring.md` — оценка источников + шаблон `sources/NN.md` с `channel:` и `access:`; claims-ledger (`claims.csv`) и правило primary-first (Фаза 5).
- `references/evidence_filter.md` — **Evidence-фильтр** (Фаза 5.5): CRAG-relevance по паре (claim, source), relevant-only цитаты в слой `evidence/`, correction-триггер (medium/deep).
- `references/subagents_v2.md` — паттерн суб-агентов с CHANNELS TO USE (Фаза 4, medium/deep).
- `references/adversarial_pass.md` — multi-angle red team: роли, триаж severity, ограниченный цикл ремедиации (Фаза 6, medium/deep).
- `references/runtime_verification.md` — runtime-проверка цитат: резолв тезисов к sources/NN.md, verification-header (Фаза 6.5, medium/deep).

**Stat sources (Фаза 4 — точечно по теме):**
- `references/stat_sources/core/*.md` — 14 cross-industry категорий (gov_macro, companies_public/private, consulting_industry, consumer_digital, crypto, data_aggregators, media_entertainment, health, education, climate_env, science, transport_travel, sports_fitness).
- `references/stat_sources/industries/*.md` — 19 отраслевых файлов (energy, auto, pharma, retail, manufacturing, real_estate, insurance, banking, telecom, logistics, agriculture, defense, it_services, cybersecurity, advertising, hr_workforce, gig_economy, esg_sustainability, infrastructure).
- Progressive loading: читай INDEX.md, потом только нужные категории под подтему.

**API sources (Фаза 4 — для programmatic data access):**
- `references/api_sources/search/` — Brave, Tavily, Exa, SerpAPI, You.com (поисковые APIs).
- `references/api_sources/academic/` — Semantic Scholar, OpenAlex, CrossRef, arXiv (free, no key).
- `references/api_sources/financial/` — FRED, World Bank, SEC EDGAR, OECD, Alpha Vantage.
- `references/api_sources/companies/` — Crunchbase, OpenCorporates, Companies House.
- `references/api_sources/crypto/` — CoinGecko, DefiLlama, Etherscan, Dune.
- `references/api_sources/code/` — GitHub, Stack Exchange, PyPI, npm.
- `references/api_sources/social/` — Reddit JSON, HN Algolia, Lemmy.
- `references/api_sources/news/` — NewsAPI, GDELT, Currents.
- `references/api_sources/stats/` — Eurostat, Census US, UN Data.
- `references/api_sources/domain_specific/` — PubMed, ClinicalTrials, EMA, NASA, OpenWeather.
- Auth через environment variables — скилл сам не хранит ключи. Free no-key APIs приоритетны.
