---
name: deepdive
description: Meta-research под вопрос или решение. Веб-поиск, академические источники, Q&A отчёт; каждый источник — отдельный файл с цитатами и метаданными для повторного использования. Использовать когда нужна основа под решение, для деск-ресёрча, валидации гипотезы или чтобы понять как устроен X. Триггеры — "deep research", "глубокое исследование", "проведи ресёрч", "сделай ресёрч", "изучи тему", "разбери тему", "исследуй", "копни глубоко", "deep dive", "ресёрчни".
---

# Deepdive — meta-research с дисциплиной

Многошаговое исследование под вопрос или решение. Каждый источник = файл, отчёт построен как Q&A, тезисы атомарны и пере-используемы.

## Когда применять

Прямая просьба о ресёрче; сравнение N институций/продуктов/методологий/рынков; материал под стратегию, доклад, статью; проверка гипотезы внешними данными; «как устроен X», «карта области Y».

**НЕ применять:** быстрая фактоверка → отвечай напрямую · N конкурентов по фиксированной матрице → `competitive-teardown` · Anthropic SDK / Claude API → `claude-api` · брейншторм без данных → `brainstorming`/`grill-me` · ответ уже в проекте → сначала grep.

## Глубина — по теме, жёсткого дефолта нет

| Режим | Источников | Суб-агентов | Когда |
|---|---|---|---|
| shallow | 5–7 | 0 | первичная навигация, тема знакома, low-stakes |
| medium | 12–18 | 2–3 | нетривиальная тема, среднее решение |
| deep | 25–35+ | 4–5 | high-stakes решение, стратегия |

Объяви режим в начале с обоснованием. После Genre+Plan объяви **model routing** одной строкой (какие фазы на какой модели + estimated cost + как перебить: «всё на opus» / «cheap mode»). Детали — `references/model_routing.md`.

## Перед стартом — discover existing

До reframing (опционально — нет файлов, иди дальше): определи целевую папку → если она есть, перечисли содержимое, похожий slug ⇒ спроси «это update?» → прочитай `CLAUDE.md`/`CLAUDE.local.md` и `memory/MEMORY.md`, учти в reframing. Цель: не дублировать сделанное.

**Куда сохранять** (не хардкодь): (1) research-папка из CLAUDE.md или существующая `research/` · `06_Деск-ресёрч/` · `docs/research/` · `notes/research/`; (2) иначе по типу проекта — есть манифест (`pyproject.toml`/`package.json`/`Cargo.toml`/`go.mod`) → `research/`, только документы → `06_Деск-ресёрч/`; (3) не git-репо или пусто → `~/deep-research/<slug>/`. Путь покажи ОДИН раз, дальше пиши молча.

**Slug:** латиница, цифры, дефисы («Postgres logical replication vs CDC» → `postgres-replication-vs-cdc`). Неочевиден — покажи в начале фазы 2.

## Workflow — <!--gen:count:phases-->12<!--/gen--> фаз (1–8, включая 3.5, 3.7, 5.5 и 6.5)

Детали фаз — `references/workflow.md`, модель на фазу — `references/model_routing.md`. Здесь — что фаза обязана оставить после себя.

1. **Reframing** [`opus`/high] — переписать вопрос; собрать **Decision Spec** (решение глагол+объект+срок / потребитель→его следующий шаг / ≥1 if-then вилка «покажет X → делаю A»; ни одной вилки ⇒ честный даунгрейд в shallow); 2–4 опровергаемые гипотезы; для medium/deep — персоны охвата (STORM) и router по типу вопроса (фактологический→плоско / многошаговый→least-to-most / реляционный→графы / сравнительный→матрица). См. `question_reframing.md`.
2. **Genre & blocks** [`sonnet`/medium] — жанр (qa/explainer/decision/landscape/validation/custom) + набор блоков, подтвердить одной строкой. См. `genres.md`, `blocks/INDEX.md`.
3. **Plan** [`opus`/medium] — `plan.md`: HEADER → SCOPE → STRUCTURE → EXECUTION → TRACKING (user context, time-box, acceptance criteria, discovered existing, glossary, жанр+блоки, гипотезы, risk register, subtopic↔blocks mapping с least-to-most уровнями для многошаговых вопросов, sourcing strategy, opposition queries, stop-criteria, notes).
3.5. **Capability Discovery** [`sonnet`/low] (deep — обязательна) — audit env vars, подтемы → доступные API, fallback на awesome-lists. См. `capability_discovery.md`.
3.7. **Plan-review gate** [`sonnet`/low] (shallow — skip) — единственная human-in-the-loop точка ПЕРЕД дорогой Фазой 4: показать сжатый план (вопрос, решение, жанр, гипотезы, каналы, стоп-критерий, routing). **deep — ЖДАТЬ явного «Ок»; medium — soft.** Включает **скаут-пасс** (deep — рекомендуется): 3–4 `Explore`-агента на `haiku` ищут не источники, а непокрытые подвопросы; выход — правки `plan.md`, ноль записей в `sources/`. См. `plan_gate.md`.
4. **Поиск** [main `sonnet`/medium; sub-agents: `haiku` web/api, `sonnet` academic/long-source] — (4.0) Source Dispatch по матрице → `plan.md` §12; количественный подвопрос ⇒ primary-канал registry/API. (4.1) Launch: medium/deep — `general-purpose` суб-агенты параллельно, каждому свой диапазон id (`s01-s09`, `s10-s19`…) и своя ось поиска, не только подтема; shallow — главный поток. (4.2) Fetch, дедуп с замером `overlap_rate`. (4.3) Агент сам пишет `sources/NN_slug.md`, в главный поток — только index-строки. После раунда 1 — snowball (backward/forward цитирования). Loop: goal-check (haiku) → bounded deviation с query-мутациями → circuit breaker (2 раунда без нового ⇒ стоп, остаток в Open Questions). См. `source_dispatch.md`, `subagents_v2.md`.
5. **Claims-ledger + триангуляция** [`haiku`/low] — `claims.csv` (claim_id, sources, source_types, roots, paths, status, confidence, primary_source, source_caveat, dissent, as_of). `triangulated` ⟺ ≥3 источника И ≥2 типа И ≥2 корня (`root:`) И ≥2 пути (`discovery_path:`); иначе `single-type`/`single-root`/`single-path`, потолок medium. Primary-first: без primary — потолок medium. Caveat (`vendor`/`self-reported`/`disputed:sNN`) — потолок medium, `disputed` без арбитра → low. **Защита меньшинства:** непогашенный `dissent` от `Primary`/`credibility ≥ 4` ⇒ `contested` независимо от большинства, обе позиции в отчёт с основанием выбора. Loop: gap-волна на не-triangulated, max 2 круга, иначе `data-insufficient`. См. `source_scoring.md`.
5.5. **Evidence-фильтр: relevance × authority** [`sonnet`/low] (medium/deep — обязательно) — фильтр на ВХОДЕ синтеза. **Relevance:** по паре (claim, source) классификатор Correct/Ambiguous/Incorrect по дословным цитатам → relevant-only цитаты в `evidence/CN.md`; claim без единого relevant-источника → `data-insufficient` или до-поиск. **Authority** (несущие пары: claim в memo/F1/F9, ИЛИ с числом, ИЛИ источник единственный корень, ИЛИ `caveat` ≠ `-`): «вправе ли ЭТОТ источник утверждать ЭТО» по чек-листу признаков → `qualified`/`unqualified-for-this-claim`/`unknown` → `.verify/authority.json`. **`unknown` — карантин:** не единственная опора, не `high`. `sources/NN.md` не трогаются. См. `evidence_filter.md`.
6. **Синтез + multi-angle red team** [red team `opus`/high для deep, `sonnet`/high для medium] — собрать `<date>_<genre>.md` из блоков (финал «it depends» запрещён: рекомендация однозначная или условная по вилкам) → claim ledger → параллельные враждебные роли как `general-purpose`: R1 Skeptic, R2 Contrarian, R3 Gap-hunter, R4 Исполнитель (исполняет решение только по отчёту + hedge-линт), R5 Адвокат меньшинства (защищает одинокий источник, директива «консенсус не аргумент») → триаж severity → ОДИН раунд ремедиации HIGH → **`memo.md`** (рекомендация, вилки, 3 числа с [sNN]+`as_of`, риск, next actions, строка `Урезано:` — сработавший circuit breaker или даунгрейд объявляется вслух; иначе `Урезано: —`) → финал. Finder ≠ fixer. Гейт: shallow=R1 инлайн, medium=R1+R2+R4 (+R5 при `dissent`), deep=все пять. Ценность даёт разность ролей и изоляция контекстов, не класс модели. См. `adversarial_pass.md`.
6.5. **Verify** [`haiku`/low] (medium/deep — обязательно) — три оси: **liveness** (`check_citations.py` → `.verify/citations.json`); **faithfulness** (entailment claim⊨цитата по парам из `evidence/CN.md` → SUPPORTED/PARTIAL/UNSUPPORTED → `.verify/faithfulness.json`); **qualifier preservation** (утверждения F1/`memo.md`/Z12 против строк `claims.csv` → PRESERVED/BROADENED/SCOPE-DROPPED/UNTRACEABLE → `.verify/qualifiers.json`). Битое чинится re-search'ем, overclaim смягчается, неподтверждённое уходит в Open Questions, снятая оговорка возвращается — дрейфует отчёт, не ledger. Header F10 несёт все три оси плюс строку независимости источников; без него отчёт не «готов». См. `runtime_verification.md`.
7. **Refresh targets** [`sonnet`/medium] (medium/deep) — entities/numbers/hypotheses/topic-markers из отчёта в `refresh_targets.md`: точка входа для будущих `update`. Блок Z11 в `blocks/close.md`.
8. **Decision walkthrough** [`opus`/high, главный поток] (**всегда**, в shallow — 1 вилка) — отчёт не обсуждается, а исполняется: показать `memo.md` и провести пользователя по вилкам по одной. Исходы: принято (решение + next action + дата) / `blocked` (после 1 целевой gap-волны) / `deferred`. Артефакт `application.md` (любой status) + строка в `~/.claude/research/applications_ledger.csv`. См. `decision_walkthrough.md`.

## Stop-criteria — по содержанию, не по бюджету

Лимита на WebSearch/WebFetch нет.

**Стоп когда:** все гипотезы подтверждены/опровергнуты ≥3 разнотипными источниками либо помечены «данных мало» · прошёл ≥1 целевой поиск оппозиции («X criticism / counter-evidence / problems with X») и разобран · покрыты 4+ типа источников · последние 3–5 источников не дают нового.

**Не стоп когда:** источники противоречат (копай за причиной) · все одного типа · есть сильный контр-аргумент без разбора · оппозицию не искали.

**Тупик:** третий подряд поиск даёт источники `total < 8` ⇒ стоп, в Open Questions «литература слабая», предложи интервью/эксперимент.

## Output structure

```
<slug>/
├── plan.md              # Фаза 3 (+ changelog §16, notes §15)
├── sources.csv          # индекс источников с оценками
├── claims.csv           # Фаза 5 — claim-ledger
├── sources/NN_slug.md   # один файл = один источник (метаданные + дословные цитаты)
├── evidence/CN.md       # Фаза 5.5 — relevant-only цитаты под claim (medium/deep)
├── findings/FN_*.md     # атомарные тезисы (опц., для крупных)
├── refresh_targets.md   # Фаза 7 (medium/deep)
├── memo.md              # Фаза 6 — decision-меморандум (всегда)
├── application.md       # Фаза 8 — вердикт по вилкам + status (всегда)
├── .verify/             # I/O-контракт: один producer, много consumers
│   ├── authority.json   #   Фаза 5.5 — qualified/unqualified/unknown + карантины
│   ├── citations.json   #   Фаза 6.5 liveness
│   ├── faithfulness.json#   Фаза 6.5 faithfulness
│   └── qualifiers.json  #   Фаза 6.5 qualifier preservation
├── diffs/<date>_delta.md# дельты режима update
└── <YYYY-MM-DD>_<genre>.md   # финал: qa|explainer|decision|landscape|validation|custom
```

Отдельный `_changelog.md` не создаётся — он в `plan.md` §16. Шаблоны: `sources/NN.md` и `claims.csv` — `source_scoring.md`; отчёт — `genres.md` + `blocks/`; `findings/FN.md` — блок Z6 в `blocks/close.md`.

## После завершения — finish-up

0. **Детерминированные артефакты, не руками:** `python scripts/build_sources_csv.py --research-dir <root>/<slug>` (единый источник колонок) · `python eval/check_citations.py --research-dir <root>/<slug> --json --out <root>/<slug>/.verify/citations` (без `--out` файл уйдёт в `eval/output/` и gate его не найдёт).
0.5. **Провенанс чисел:** `python scripts/check_number_provenance.py --research-dir <root>/<slug> --strict` — ловит число без прослеживаемого производителя и одно значение у источников с разными корнями (ложная независимость).
1. **Phase-gate — БЛОКЕР:** `python scripts/validate_phases.py --research-dir <root>/<slug> --strict`. Красный ⇒ фаза пропущена ⇒ вернись, доделай, перезапусти. Не показывать путь, не писать резюме, не рапортовать «готово» с красным gate.
2. Пути markdown-ссылками: сначала `memo.md` (вход потребителя), затем отчёт.
3. Резюме в чат 5–8 строк: 3 ключевых ответа + главный контр-аргумент + чего не нашли + итог walkthrough из `application.md`.
4. Предложи 2–3 следующих ресёрча.
5. Есть `memory/` — предложи 1–3 кандидата (тезис + confidence + источники; авторитетный источник как `[reference]`).
6. Есть `anthropic-skills:humanizer-ru` — прогони им финальный отчёт (опционально).

## Что НЕ делать

- Не пропускать `discover existing` и reframing.
- Не запускать medium/deep без единой if-then вилки Decision Spec — честный shallow дешевле мёртвого deep-отчёта.
- Не пропускать Фазу 8 «потому что и так ясно» и не отвечать на вилки ЗА пользователя.
- Не пропускать Plan-review gate в medium/deep; для deep гейт без ожидания ответа = не гейт.
- Не завершать синтез финалом «it depends» без разрешённых условий.
- Не оставлять `root:` пустым и не копировать `discovery_path:` между источниками — это 3-е и 4-е условия триангуляции.
- Не разводить fetch-агентов только по подтемам — ещё и по осям поиска (EN-академия / RU + регуляторы / практики / реестры): один шаблон + одна модель + один язык = одна траектория и коррелированные голоса.
- Не выбрасывать дубли URL между агентами молча — считать `overlap_rate` в `plan.md` §15: совпадение это замер конформизма, а не подтверждение.
- Не передавать во второй раунд находки соседей — только дыры.
- Не давать `triangulated` строке с непогашенным `dissent` от Primary/`credibility ≥ 4` (это `contested`) и не гасить dissent понижением credibility несогласного.
- Не трактовать `unknown` в authority как «сойдёт» — карантин.
- Не выдавать числу трибуну без производителя: `origin_kind: unknown` / `chain_len ≥ 2` / нет `data_as_of` ⇒ не в `memo.md`/TL;DR/F9 и не `high`.
- Не искать числа в вебе при наличии покрывающего endpoint в `stat_sources/`/`api_sources/`.
- Не поднимать fetch-агентов Фазы 4 на opus «для качества»: у них Write и изолированный контекст, растёт не качество поиска, а уверенность ошибки.
- Не пропускать gap-волну и не давать confidence выше `medium` без primary-источника.
- Не пропускать multi-angle red team и Фазу 5.5 в medium/deep.
- Фаза 5.5: не переписывать `sources/NN.md` (архив), не фильтровать по `total` вместо релевантности фрагмента к claim.
- Фаза 6.5: не доверять наличию ссылки — проверять entailment по дословной цитате; вердикты писать в `.verify/*.json` и не пересчитывать в rubric/F10; пары брать из `evidence/`, не пересканировать `sources/`. Layer 3 судит снятие ОГРАНИЧИТЕЛЯ, не сокращение текста; при сомнении PRESERVED; чинить отчёт, а не ledger; потерянный `claim_id` ⇒ `UNTRACEABLE`.
- Не использовать источники с `total < 8` как основу выводов и не оставлять утверждений без ссылки на `sources/NN.md`.
- Для fetch+save и red team — `general-purpose` с явным диапазоном номеров, не `Explore` (read-only, только разведка).
- Не запускать суб-агентов последовательно — только параллельно в одном сообщении.
- Не сжимать `sources/` в один файл, не выводить результат только в чат, не обходить WebFetch через bash/curl.
- Не рапортовать «готово» с красным phase-gate.

## Режим update

`update <slug>` / «обнови ресёрч X» — **дельта, не replay**. Pre-flight: `plan.md`, `refresh_targets.md`, последний отчёт (нет `refresh_targets.md` — сгенерируй по Z11). Четыре категории дельты с date-фильтром от last_research_date: new entrants · entity diff · numbers refresh · adversarial trigger. Verified-no-change — тоже результат. Выход: `diffs/<date>_delta.md`; новый отчёт — только если дельта существенна (решает пользователь), старый получает `status: superseded by …`. Adversarial trigger HIGH ⇒ повторить только Фазу 6 на opus. Типовой update ~$0.40 против ~$2 за medium. Протокол — `references/refresh_protocol.md`.

## References — когда читать

Прогрессивная подгрузка: файл читается когда дошёл до фазы, не превентивно.

**Базовые:** `workflow.md` (детали <!--gen:count:phases-->12<!--/gen--> фаз) · `question_reframing.md` (Фаза 1 + clarification-триаж) · `plan_gate.md` (Фаза 3.7 + скаут) · `genres.md` (<!--gen:count:genres-->6<!--/gen--> жанров) · `blocks/INDEX.md` (<!--gen:count:blocks-->105<!--/gen--> блоков) · `channels.md` (<!--gen:count:channels-->29<!--/gen--> каналов, query patterns, paywall fallbacks) · `stat_sources/INDEX.md` (33 категории) · `api_sources/INDEX.md` (<!--gen:count:api-->39<!--/gen-->+ endpoints) · `capability_discovery.md` · `awesome_lists_registry.md` · `source_dispatch.md` (обязательно перед launch суб-агентов) · `model_routing.md` · `refresh_protocol.md`.

**По фазам:** `source_scoring.md` (шкалы, provenance, claims-ledger, dissent — Фаза 5) · `evidence_filter.md` (relevance × authority — 5.5) · `subagents_v2.md` (промпты и периметр суб-агентов — 4) · `adversarial_pass.md` (роли R1–R5 — 6) · `runtime_verification.md` (три оси + F10 — 6.5) · `decision_walkthrough.md` (Фаза 8).

**Блоки (по выбранному жанру):** `frame.md` F1-F10 (TL;DR, scope, claim, verification header) · `explain.md` E1-E14 · `compare.md` C1-C13 · `map.md` M1-M12 · `validate.md` V1-V10 · `analyze.md` A1-A13 · `close.md` Z1-Z12 (counter-args, open questions, so-what-for-you) · `people.md` P1-P7 · `numbers.md` N1-N8 · `context.md` X1-X7.

**Stat/API источники (Фаза 4, точечно):** `stat_sources/core/*.md` — 14 cross-industry категорий; `stat_sources/industries/*.md` — 19 отраслевых; `api_sources/` — search, academic (free, no key), financial, companies, crypto, code, social, news, stats, domain_specific. Читай INDEX, потом нужную категорию. Auth через env vars, ключи скилл не хранит; приоритет — free no-key API.
