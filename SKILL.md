---
name: deepdive
description: "Meta-research под вопрос или решение: веб-поиск, источники, Q&A отчёт с цитатами по файлам для повторного использования. Использовать для деск-ресёрча, валидации гипотезы, «как устроен X». Триггеры: «deep research», «сделай ресёрч», «исследуй», «копни глубоко», «ресёрчни»."
---

# Deepdive — meta-research с дисциплиной

Многошаговое исследование под вопрос или решение. Источник = файл, отчёт как Q&A, тезисы атомарны и пере-используемы.

## Когда применять

Прямая просьба о ресёрче; сравнение N институций/продуктов/методологий/рынков; материал под стратегию, доклад, статью; проверка гипотезы внешними данными; «как устроен X», «карта области Y».

**НЕ применять:** быстрая фактоверка → отвечай напрямую · N конкурентов по фиксированной матрице → `competitive-teardown` · Anthropic SDK / Claude API → `claude-api` · брейншторм без данных → `brainstorming`/`grill-me` · ответ уже в проекте → сначала grep.

## Глубина — по теме, жёсткого дефолта нет

| Режим | Источников | Суб-агентов | Когда |
|---|---|---|---|
| shallow | 5–7 | 0 | первичная навигация, тема знакома, low-stakes |
| medium | 12–18 | 2–3 | нетривиальная тема, среднее решение |
| deep | 25–35+ | 4–5 | high-stakes решение, стратегия |

Объяви режим в начале с обоснованием. После Genre+Plan объяви **model routing** одной строкой (фазы по моделям + estimated cost + как перебить: «всё на opus» / «cheap mode»). Детали — `model_routing.md`.

## Перед стартом — discover existing

До reframing (опционально — нет файлов, иди дальше): определи целевую папку → есть — перечисли содержимое, похожий slug ⇒ спроси «это update?» → прочитай `CLAUDE.md`/`CLAUDE.local.md` и `memory/MEMORY.md`, учти в reframing. Цель: не дублировать сделанное.

**Плюс кросс-прогонная вики** — `python scripts/wiki_query.py --topic "<вопрос>"`. Папка отвечает только про ТОТ ЖЕ ресёрч; вики — про всё, что накопили остальные: сущности с прошлыми утверждениями, источники с готовой оценкой (credibility не считать заново) и **открытые противоречия между прогонами**. Непогашенное противоречие по теме идёт в `plan.md` исследовательским вопросом. См. `wiki.md`.

**Куда сохранять** (не хардкодь): (1) research-папка из CLAUDE.md или существующая `research/` · `06_Деск-ресёрч/` · `docs/research/` · `notes/research/`; (2) иначе по типу проекта — манифест (`pyproject.toml`/`package.json`/`Cargo.toml`/`go.mod`) → `research/`, только документы → `06_Деск-ресёрч/`; (3) не git-репо или пусто → `~/deep-research/<slug>/`. Путь покажи ОДИН раз, дальше пиши молча.

**Slug:** латиница, цифры, дефисы («Postgres logical replication vs CDC» → `postgres-replication-vs-cdc`). Неочевиден — покажи в начале фазы 2.

## Workflow — <!--gen:count:phases-->13<!--/gen--> фаз (1–8, включая 3.5, 3.7, 5.5, 5.7, 6.5)

Детали фаз — `workflow.md`, модель на фазу — `model_routing.md`. Здесь — что фаза обязана оставить после себя.

1. **Reframing** [`opus`/high] — переписать вопрос; **Decision Spec** (решение глагол+объект+срок / потребитель→его следующий шаг / ≥1 if-then вилка «покажет X → делаю A»; ни одной вилки ⇒ честный даунгрейд в shallow); 2–4 опровергаемые гипотезы; medium/deep — персоны охвата (STORM) и router по типу вопроса (фактологический→плоско / многошаговый→least-to-most / реляционный→графы / сравнительный→матрица). См. `question_reframing.md`.
2. **Genre & blocks** [`sonnet`/medium] — жанр (qa/explainer/decision/landscape/validation/custom) + набор блоков, подтвердить одной строкой. См. `genres.md`, `blocks/INDEX.md`.
3. **Plan** [`opus`/medium] — `plan.md` по шаблону §0–16 из `workflow.md`: HEADER → SCOPE → STRUCTURE → EXECUTION → TRACKING. Несущее: acceptance criteria, гипотезы, risk register, subtopic↔blocks mapping (least-to-most для многошаговых вопросов), sourcing strategy §12, opposition queries, stop-criteria.
3.5. **Capability Discovery** [`sonnet`/low] (deep — обязательна) — audit env vars, подтемы → доступные API, fallback на awesome-lists. См. `capability_discovery.md`.
3.7. **Plan-review gate** [`sonnet`/low] (shallow — skip) — единственная human-in-the-loop точка ПЕРЕД дорогой Фазой 4: показать сжатый план (вопрос, решение, жанр, гипотезы, каналы, стоп-критерий, routing). **deep — ЖДАТЬ явного «Ок»; medium — soft.** Плюс **скаут-пасс** (deep — рекомендуется): 3–4 `Explore` на `haiku` ищут не источники, а непокрытые подвопросы; выход — правки `plan.md`, ноль записей в `sources/`. См. `plan_gate.md`.
4. **Поиск** [main `sonnet`/medium; sub-agents: `haiku` web/api, `sonnet` academic/long-source] — (4.0) Source Dispatch по матрице → `plan.md` §12; количественный подвопрос ⇒ primary-канал registry/API. (4.1) medium/deep — `general-purpose` суб-агенты параллельно, каждому свой диапазон id (`s01-s09`, `s10-s19`…) и своя ось поиска, не только подтема; shallow — главный поток. (4.2) Fetch, дедуп с замером `overlap_rate`. (4.3) Агент сам пишет `sources/NN_slug.md`, в главный поток — только index-строки. После раунда 1 — snowball. Loop: goal-check → bounded deviation → circuit breaker (2 раунда без нового ⇒ стоп, остаток в Open Questions). **Окно раунда пересобирается, не накапливается** (medium/deep): `state.md` ПЕРЕЗАПИСЫВАЕТСЯ перед каждым раундом (`## Known` статусами со ссылками · `## Gaps` · `## Next`, ≤6 КБ), планирование по нему, а не по транскрипту; агенту идёт только его дыра. См. `source_dispatch.md`, `subagents_v2.md`.
5. **Claims-ledger + триангуляция** [`haiku`/low] — `claims.csv` (claim_id, sources, source_types, roots, paths, status, confidence, primary_source, source_caveat, dissent, as_of). `triangulated` ⟺ ≥3 источника И ≥2 типа И ≥2 корня (`root:`) И ≥2 пути (`discovery_path:`); иначе `single-type`/`single-root`/`single-path`, потолок medium. Без primary — потолок medium; caveat (`vendor`/`self-reported`/`disputed:sNN`) — потолок medium, `disputed` без арбитра → low. **Защита меньшинства:** непогашенный `dissent` от `Primary`/`credibility ≥ 4` ⇒ `contested` независимо от большинства, обе позиции в отчёт с основанием выбора. Gap-волна на не-triangulated, max 2 круга, иначе `data-insufficient`. См. `source_scoring.md`.
5.5. **Evidence-фильтр: relevance × authority** [`sonnet`/low] (medium/deep — обязательно) — фильтр на ВХОДЕ синтеза. **Relevance:** пара (claim, source) → Correct/Ambiguous/Incorrect по дословным цитатам → relevant-only цитаты в `evidence/CN.md`; claim без relevant-источника → `data-insufficient` или до-поиск. **Authority** (несущие пары: claim в memo/F1/F9, ИЛИ с числом, ИЛИ источник единственный корень, ИЛИ `caveat` ≠ `-`): «вправе ли ЭТОТ источник утверждать ЭТО» → `qualified`/`unqualified-for-this-claim`/`unknown` → `.verify/authority.json`. **`unknown` — карантин:** не единственная опора, не `high`. `sources/NN.md` не трогаются. См. `evidence_filter.md`.
5.7. **Сверка с вики** [`sonnet`/low] (medium/deep — обязательно) — `claims.csv` прогона против кросс-прогонной вики, **до синтеза**: расхождение с прошлым ресёрчем обязано попасть в отчёт, заметить его в Фазе 7 значит заметить поздно. `wiki_pair.py build` даёт пары только при общей сущности И сопоставимом слоте (совпавшая единица либо Jaccard ≥ 0.34), затем **сам закрывает всё, что не требует суждения**: `as_of` разошлись > 180 дней при числах с обеих сторон → `superseded`; единицы не пересекаются → `different-claim`; разошёлся скоуп (США/ЕС, медиана/среднее, enterprise/free, год) → `different-claim`. До модели доходит только остаток → `.verify/wiki_pairs.json` → вердикт из четырёх (`same-claim-agree`/`same-claim-conflict`/`different-claim`/`unknown`) → `wiki_pair.py record`. **`unknown` — карантин**, не конфликт. `record` отклоняет ВСЮ пачку при одностороннем конфликте: без второго `as_of` он неотличим от устаревшей цифры, без вторых корней — от одного источника, процитированного дважды. Подтверждённый конфликт = обе позиции в отчёт, потолок `medium`, без арбитра `contested`. Срез по `MAX_ADJUDICATED = 40` называть вслух. См. `wiki.md`.
6. **Синтез + multi-angle red team** [red team `opus`/high для deep, `sonnet`/high для medium] — `outline.md` (таблица `section | block | claims` из `plan.md` §8/§11 + фактического `claims.csv`) → собрать `<date>_<genre>.md` **секция за секцией по outline**, под каждую только её `claim_id` и её `evidence/CN.md`, не весь пул → числа в `numbers.csv` (`verbatim`/`derived`/`share`; у `derived` — `formula`+`inputs`) → финал «it depends» запрещён (рекомендация однозначная или условная по вилкам) → claim ledger → враждебные роли параллельно как `general-purpose`: R1 Skeptic, R2 Contrarian, R3 Gap-hunter, R4 Исполнитель (исполняет решение только по отчёту + hedge-линт), R5 Адвокат меньшинства («консенсус не аргумент») → триаж severity → ОДИН раунд ремедиации HIGH → **`memo.md`** (рекомендация, вилки, 3 числа с [sNN]+`as_of`, риск, next actions, строка `Урезано:` — сработавший circuit breaker или даунгрейд вслух; иначе `Урезано: —`) → финал. Finder ≠ fixer. Гейт: shallow=R1 инлайн, medium=R1+R2+R4 (+R5 при `dissent`), deep=все пять. Ценность даёт разность ролей и изоляция контекстов, не класс модели. См. `adversarial_pass.md`, `synthesis_outline.md`, `source_scoring.md` (`numbers.csv`).
6.5. **Verify** [`haiku`/low] (medium/deep — обязательно) — четыре оси, вердикты в `.verify/<ось>.json`: **liveness** (`check_citations.py`); **faithfulness** (entailment claim⊨цитата по парам из `evidence/CN.md` → SUPPORTED/PARTIAL/UNSUPPORTED); **qualifier preservation** (F1/`memo.md`/Z12 против строк `claims.csv` → PRESERVED/BROADENED/SCOPE-DROPPED/UNTRACEABLE); **construct provenance** (именованные фреймворки/«законы»/термины против `evidence/`+`sources/` → `sourced`/`author-construct`/`unsourced`; `unsourced` в `memo.md`/F1/F9 блокирует finish — у выдуманного имени нет `claim_id`, поэтому три первых оси его не видят). Чинится отчёт, не ledger: битое — re-search'ем, overclaim смягчается, неподтверждённое уходит в Open Questions, снятая оговорка возвращается, выдуманное имя получает источник либо метку «наша рамка». Header F10 несёт все четыре оси плюс строку независимости источников; без него отчёт не «готов». См. `runtime_verification.md`.
6.9. **Экспорт отчёта** [`haiku`/low] (medium/deep) — `uv run scripts/build_report.py <run>`: HTML + PDF + DOCX из одного источника. Фигуры рисуются из `numbers.csv` (числа без строки в ledger'е не рисуются), ```` ```mermaid ```` из E13/M9 — в «Схема N» через `mmdc`, markdown-сноски уезжают на поля, `[sNN]` резолвятся в приложение из `sources.csv`. Битая ссылка или потерянная сноска роняют сборку. `memo.md` остаётся отдельной страницей и в документ не сливается. См. `references/report_export.md`.
7. **Refresh targets + постобработка роя** [`sonnet`/medium] (medium/deep) — entities/numbers/hypotheses/topic-markers из отчёта в `refresh_targets.md`: точка входа для будущих `update`. Блок Z11 в `blocks/close.md`. Затем — четыре шага сбора наблюдений роя (`collect_observations.py` по подвопросам → `update_priors.py` → `promote_candidates.py --track` → изредка `promote_candidates.py --write`): порядок, флаги и ловушки — `references/swarm_postprocess.md`, читать перед первым вызовом.
8. **Decision walkthrough** [`opus`/high, главный поток] (**всегда**, в shallow — 1 вилка) — отчёт не обсуждается, а исполняется: показать `memo.md` и провести пользователя по вилкам по одной. Исходы: принято (решение + next action + дата) / `blocked` (после 1 целевой gap-волны) / `deferred`. Артефакт `application.md` (любой status) + строка в `~/.claude/research/applications_ledger.csv`. См. `decision_walkthrough.md`.

## Stop-criteria — по содержанию, не по бюджету

Лимита на WebSearch/WebFetch нет.

**Стоп когда:** все гипотезы подтверждены/опровергнуты ≥3 разнотипными источниками либо помечены «данных мало» · прошёл и разобран ≥1 целевой поиск оппозиции («X criticism / counter-evidence / problems with X») · покрыты 4+ типа источников · последние 3–5 источников не дают нового.

**Не стоп когда:** источники противоречат (копай за причиной) · все одного типа · есть сильный контр-аргумент без разбора · оппозицию не искали.

**Тупик:** третий подряд поиск даёт источники `total < 8` ⇒ стоп, в Open Questions «литература слабая», предложи интервью/эксперимент.

## Output structure

```
<slug>/
├── plan.md              # Фаза 3 (+ changelog §16, notes §15)
├── state.md             # Фаза 4 — окно раунда, ПЕРЕЗАПИСЫВАЕТСЯ каждый раунд (medium/deep)
├── sources.csv          # индекс источников с оценками
├── claims.csv           # Фаза 5 — claim-ledger
├── numbers.csv          # Фаза 6 — реестр чисел отчёта, derived пересчитываются (medium/deep)
├── outline.md           # Фаза 6 — карта section → block → claim_id (medium/deep)
├── figures.csv          # Фаза 6.9 — фигуры отчёта, только по num_id из numbers.csv (medium/deep)
├── sources/NN_slug.md   # один файл = один источник (метаданные + дословные цитаты)
├── evidence/CN.md       # Фаза 5.5 — relevant-only цитаты под claim (medium/deep)
├── findings/FN_*.md     # атомарные тезисы (опц., для крупных)
├── refresh_targets.md   # Фаза 7 (medium/deep)
├── memo.md              # Фаза 6 — decision-меморандум (всегда)
├── application.md       # Фаза 8 — вердикт по вилкам + status (всегда)
├── .verify/             # I/O-контракт: один producer, много consumers
│   ├── authority.json   #   5.5 — qualified/unqualified/unknown + карантины
│   ├── wiki_pairs.json  #   5.7 — пары на адъюдикацию (medium/deep)
│   ├── wiki_ingest.json #   finish-up — квитанция записи в вики (всегда)
│   └── citations|faithfulness|qualifiers|constructs.json  # 6.5, по оси на файл
├── diffs/<date>_delta.md# дельты режима update
├── <YYYY-MM-DD>_<genre>.{html,pdf,docx}  # Фаза 6.9 — собранный документ
└── <YYYY-MM-DD>_<genre>.md   # финал: qa|explainer|decision|landscape|validation|custom
```

Кросс-прогонный слой лежит ВНЕ прогона — `~/.claude/research/wiki/` (источники, сущности, утверждения, `pairs.jsonl`). Он один на все ресёрчи и переживает отклонение отчёта. См. `wiki.md`.

Отдельный `_changelog.md` не создаётся — он в `plan.md` §16. Шаблоны: `sources/NN.md`, `claims.csv` — `source_scoring.md`; отчёт — `genres.md` + `blocks/`; `findings/FN.md` — Z6 в `blocks/close.md`.

## После завершения — finish-up

0. **Детерминированные артефакты, не руками:** `python scripts/build_sources_csv.py --research-dir <root>/<slug>` (единый источник колонок) · `python eval/check_citations.py --research-dir <root>/<slug> --json --out <root>/<slug>/.verify/citations` (без `--out` файл уйдёт в `eval/output/` и gate его не найдёт).
0.2. **Компиляция в вики — `python scripts/wiki_ingest.py --research-dir <root>/<slug>`.** Детерминированно, без модели, **на любой глубине**: shallow стоит ноль, а его источники переиспользуемы не хуже deep'овских. Пишет квитанцию `.verify/wiki_ingest.json`, без неё phase-gate красный. Изредка `python scripts/wiki_lint.py`.
0.5. **Числа — два прохода, `--research-dir <root>/<slug> --strict`:** `check_number_provenance.py` (число без производителя; одно значение при разных корнях = ложная независимость) · `check_number_arithmetic.py` (пересчёт `derived`, доли к 100, производное число в memo без строки в `numbers.csv`).
1. **Phase-gate — БЛОКЕР:** `python scripts/validate_phases.py --research-dir <root>/<slug> --strict`. Красный ⇒ фаза пропущена ⇒ вернись, доделай, перезапусти: не показывать путь, не писать резюме, не рапортовать «готово».
2. Пути markdown-ссылками: сначала `memo.md` (вход потребителя), затем отчёт.
3. Резюме в чат 5–8 строк: 3 ответа + главный контр-аргумент + чего не нашли + итог walkthrough из `application.md`.
4. Предложи 2–3 следующих ресёрча.
5. Есть `memory/` — предложи 1–3 кандидата (тезис + confidence + источники; авторитетный источник как `[reference]`).
6. Есть `anthropic-skills:humanizer-ru` — прогони им финальный отчёт (опционально).

## Что НЕ делать

- **Не пропускать:** `discover existing` и reframing · Plan-review gate в medium/deep (для deep гейт без ожидания ответа = не гейт) · Фазы 5.5 и 5.7 и multi-angle red team в medium/deep · gap-волну · Фазу 8 «потому что и так ясно» — и не отвечать на вилки ЗА пользователя.
- Фаза 5.7: не объявлять конфликт, не показав обе стороны с их `as_of` и корнями — односторонний конфликт неотличим от устаревшей цифры и от одного источника, процитированного дважды. Не трактовать `unknown` как «сойдёт» (карантин, как в authority). Не молчать про срез по `MAX_ADJUDICATED`: непроверенные пары ≠ отсутствие противоречий. Не чинить противоречие выбором «более свежего» — расхождение после прескрина уже не про свежесть.
- Не редактировать страницы вики руками (переживёт до следующего ingest) и не заводить вики внутри проекта: смысл слоя в том, что он один на все ресёрчи. Не гейтить `wiki_ingest` по глубине.
- Не запускать medium/deep без единой if-then вилки Decision Spec — честный shallow дешевле мёртвого deep-отчёта.
- Не завершать синтез финалом «it depends» без разрешённых условий.
- Не оставлять `root:` пустым и не копировать `discovery_path:` между источниками — это 3-е и 4-е условия триангуляции.
- Не разводить fetch-агентов только по подтемам — ещё и по осям поиска (EN-академия / RU + регуляторы / практики / реестры): один шаблон + одна модель + один язык = одна траектория и коррелированные голоса.
- Не выбрасывать дубли URL между агентами молча — считать `overlap_rate` в `plan.md` §15: совпадение это замер конформизма, а не подтверждение.
- Не передавать во второй раунд находки соседей — только дыры. Не дописывать `state.md`: он перезаписывается, растущий по раундам файл это второй транскрипт, а не окно.
- Не давать `triangulated` строке с непогашенным `dissent` от Primary/`credibility ≥ 4` (это `contested`) и не гасить dissent понижением credibility несогласного.
- Не трактовать `unknown` в authority как «сойдёт» — карантин. Не давать confidence выше `medium` без primary-источника. Не строить выводы на источниках с `total < 8` и не оставлять утверждений без ссылки на `sources/NN.md`.
- Не выдавать числу трибуну без производителя: `origin_kind: unknown` / `chain_len ≥ 2` / нет `data_as_of` ⇒ не в `memo.md`/TL;DR/F9 и не `high`.
- Не считать процент/долю/рост прозой: производное число живёт в `numbers.csv` с `formula`+`inputs`. Вычисление в тексте не повторяет никто — оси 6.5 арифметику не проверяют.
- Не писать отчёт одним проходом по пулу и не оставлять `triangulated`/`contested` claim вне `outline.md`: собранное и не внесённое — выброшенная работа, а не редакторский выбор.
- Не вводить именованный фреймворк/«закон» без `[sNN]` или пометки «наша рамка» — выдуманное имя проходит всё, что джойнится по `claim_id`.
- Не искать числа в вебе при наличии покрывающего endpoint в `stat_sources/`/`api_sources/`.
- Не поднимать fetch-агентов Фазы 4 на opus «для качества»: у них Write и изолированный контекст, растёт не качество поиска, а уверенность ошибки.
- Фаза 5.5: не переписывать `sources/NN.md` (архив), не фильтровать по `total` вместо релевантности фрагмента к claim.
- Фаза 6.5: не доверять наличию ссылки — проверять entailment по дословной цитате; вердикты писать в `.verify/*.json` и не пересчитывать в rubric/F10; пары брать из `evidence/`, не пересканировать `sources/`. Layer 3 судит снятие ОГРАНИЧИТЕЛЯ, не сокращение текста; при сомнении PRESERVED; чинить отчёт, а не ledger; потерянный `claim_id` ⇒ `UNTRACEABLE`.
- Для fetch+save и red team — `general-purpose` с явным диапазоном номеров, не `Explore` (read-only, только разведка). Не запускать суб-агентов последовательно — только параллельно в одном сообщении.
- Не сжимать `sources/` в один файл, не выводить результат только в чат.
- Не обходить WebFetch произвольным `bash`/`curl`. Единственный санкционированный fallback — `scripts/fetch_source.py` (Фаза 4.2): он читает robots.txt, санитайзит страницу от prompt injection и проставляет `fetch_tier`. Ручной `curl -A` не делает ничего из этого, и его вывод в `sources/` не кладётся.
- Не принимать `fetch_source.py` за средство против paywall и анти-бот-защиты: `auth-wall` и `antibot` для него — терминальный вердикт, а не задача посложнее. Дальше — fallback-протокол `channels.md` или endpoint из `api_sources/`.
- Не рисовать в отчёте число, которого нет в `numbers.csv`, и не подбирать палитру фигур на глаз — она валидируется скриптом (первая попытка провалила 2 проверки из 6).
- Не сливать `memo.md` в большой документ: одна страница, которую точно прочтут, растворяется в двадцати, которые прочтут не все. Не считать DOCX форматом для чтения — боковых полей в Word нет, сноски там остаются сносками; читают PDF и HTML.

## Режим update

`update <slug>` / «обнови ресёрч X» — **дельта, не replay**. Pre-flight: `plan.md`, `refresh_targets.md` (нет — сгенерируй по Z11), последний отчёт. Четыре категории дельты с date-фильтром от last_research_date: new entrants · entity diff · numbers refresh · adversarial trigger. Verified-no-change — тоже результат. Выход: `diffs/<date>_delta.md`; новый отчёт — только если дельта существенна (решает пользователь), старый получает `status: superseded by …`. Adversarial trigger HIGH ⇒ повторить только Фазу 6 на opus. Типовой update ~$0.40 против ~$2 за medium. Протокол — `refresh_protocol.md`.

Update тоже идёт в вики: `wiki_ingest.py` после дельты (квитанция обязательна), и `wiki_pair.py build` — свежая цифра против старой закроется как `superseded` автоматически, а вот расхождение НЕ по свежести и есть настоящая находка update'а.

## References — когда читать

Прогрессивная подгрузка: файл читается когда дошёл до фазы, не превентивно.

**Базовые (читает любой medium/deep прогон):** `workflow.md` (детали <!--gen:count:phases-->13<!--/gen--> фаз) · `question_reframing.md` (Фаза 1 + clarification-триаж) · `plan_gate.md` (Фаза 3.7 + скаут) · `genres.md` (<!--gen:count:genres-->6<!--/gen--> жанров) · `blocks/INDEX.md` (<!--gen:count:blocks-->106<!--/gen--> блоков) · `channels.md` (<!--gen:count:channels-->29<!--/gen--> каналов, query patterns, paywall fallbacks) · `source_dispatch.md` (обязательно перед launch суб-агентов) · `model_routing.md` · `wiki.md` (кросс-прогонный слой: чтение в `discover existing`, Фаза 5.7, запись в finish-up).

**Условные — грузить, когда прогон дошёл до условия, а не заранее:** `capability_discovery.md` и `awesome_lists_registry.md` — Фаза 3.5 (обязательна только на deep) · `stat_sources/INDEX.md` (33 категории) и `api_sources/INDEX.md` (<!--gen:count:api-->47<!--/gen-->+ endpoints) — Фаза 4, когда подвопрос количественный или Source Dispatch ведёт в registry/API · `refresh_protocol.md` — только режим `update`.

**По фазам:** `fetch_source.py` + `channels.md` §«Bot-block ≠ paywall» (лестница `http`→`browser`, только когда WebFetch ответил «unable to fetch from …» — 4.2) · `report_export.md` (`figures.csv`, выбор формы графика, сноски, вёрстка e-ink — 6.9) · `swarm_postprocess.md` (четыре шага роя — после 7) · `source_scoring.md` (шкалы, provenance, claims-ledger, dissent, `numbers.csv` — Фаза 5–6) · `evidence_filter.md` (relevance × authority — 5.5) · `subagents_v2.md` (промпты, периметр, `state.md` — 4) · `synthesis_outline.md` (outline + письмо по секциям — 6) · `adversarial_pass.md` (роли R1–R5 — 6) · `runtime_verification.md` (четыре оси + F10 — 6.5) · `decision_walkthrough.md` (Фаза 8).

**Блоки (по выбранному жанру):** `frame.md` F1-F10 (TL;DR, scope, claim, verification header) · `explain.md` E1-E14 · `compare.md` C1-C13 · `map.md` M1-M12 · `validate.md` V1-V10 · `analyze.md` A1-A13 · `close.md` Z1-Z12 (counter-args, open questions, so-what-for-you) · `people.md` P1-P7 · `numbers.md` N1-N8 · `context.md` X1-X7.

**Stat/API источники (Фаза 4, точечно):** `stat_sources/core/*.md` — 14 cross-industry категорий; `stat_sources/industries/*.md` — 19 отраслевых; `api_sources/` — search, academic (free, no key), financial, companies, crypto, code, social, news, stats, domain_specific. Читай INDEX, потом нужную категорию. Auth через env vars, ключи скилл не хранит; приоритет — free no-key API.
