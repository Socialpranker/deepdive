---
name: deepdive
description: "Веб-ресёрч под решение: отчёт с источником и цитатой под каждый факт, контраргументы, рекомендация. Вызывать: «deepdive», «сделай ресёрч», «исследуй», «копни глубоко», «обоснуй данными». НЕ для: одного факта, брейншторма, ответа из проекта, аудита репо (zodchiy), API Claude (claude-api)."
---

# Deepdive — meta-research с дисциплиной

Источник = файл с дословными цитатами, отчёт = Q&A. Скрипты запускать из `~/.claude/skills/deepdive`: `uv run scripts/X.py`. Проверки печатают первые 15 ошибок и 5 предупреждений; `--verbose` — только когда чинишь конкретную. N конкурентов по фиксированной матрице — обычная таблица, не deepdive.

## Глубина

По умолчанию **medium**; shallow или deep — только если тема явно тривиальна или решение high-stakes. Объяви режим с обоснованием, после Genre+Plan — одной строкой model routing (фазы по моделям, цена, как перебить: «всё на opus» / «cheap mode»); `model_routing.md`.

| Режим | Источников | Fetcher-агентов | Всего суб-агентов за прогон |
|---|---|---|---|
| shallow | 5–7 | 0 | 0 |
| medium | 25–30 (из 60–100 кандидатов) | 3–4 | ≈14–17 (scout, пул кандидатов, Haiku-проходы, синтезатор, red team) |
| deep | 35–45 (из ≥100 кандидатов) | 5–6 | ≈22–27 |

Суб-агент не запускается на то, что главный поток закроет за несколько вызовов или что считает скрипт.

## Перед стартом

1. Найди целевую папку и перечисли содержимое; похожий slug — спроси «это update?»; прочитай `CLAUDE.md` и `memory/MEMORY.md`: не дублируй сделанное.
2. Вики прошлых прогонов: `uv run scripts/wiki_query.py --topic "<вопрос>"`; непогашенное противоречие идёт в `plan.md` вопросом. `wiki.md`.
3. Папка: research-папка из CLAUDE.md или `research/`, `06_Деск-ресёрч/`, `docs/research/`; иначе `research/` (есть манифест), `06_Деск-ресёрч/` (только документы), `~/deepdive/<slug>/` (не git-репо). Slug — латиница, дефисы. Путь покажи один раз.

## Workflow — <!--gen:count:phases-->13<!--/gen--> фаз

Состав и гейты — `phases.yaml` (шаг 6.9 не фаза гейта: проверяется артефакт `readout.md`). Детали фазы — свой файл `references/phases/`, оглавление в `workflow.md`; при входе в фазу читай только её файл. Исполнитель: `main` — главный поток, `sub` — субагент.

1. **Reframing** [`main`] — Decision Spec: решение, потребитель→следующий шаг, ≥1 вилка «покажет X → делаю A» (нет вилки ⇒ даунгрейд в shallow вслух); 2–4 опровергаемые гипотезы. `question_reframing.md`
2. **Genre & blocks** [`main`] — жанр и блоки, подтвердить строкой. `genres.md`, `blocks/INDEX.md`
3. **Plan** [`main`] — `plan.md` §0–16. `plan_template.md`
3.5. **Capability Discovery** [`sub: explore-haiku`] (deep) — ключи, API, fallback. `capability_discovery.md`
3.7. **Plan-review gate** [`main`] (shallow пропуск) — показать план до дорогой Фазы 4; deep ждёт «Ок», потому что это единственная точка человека, а субагент спросить не может. `plan_gate.md`
4. **Поиск** [`main` + `sub: explore-haiku` + `sub: deepdive-fetcher`] — каналы по Source Dispatch; пул кандидатов `candidates.csv` по матрице «сфера × позиция» и ≥1 академическому API, отбор на чтение по квотам сфер, второй раунд по переменной решения (гейт `validate_phases.py`, `phases/p4_search.md` 4.1); числа сначала через registry/API; fetcher'ам непересекающиеся диапазоны id и разные оси поиска; тонкий ответ WebFetch (<500 знаков, нет цитаты) ⇒ `fetch_source.py`; `state.md` перезаписывается перед каждым раундом (≤6 КБ), иначе контекст копит транскрипт. `source_dispatch.md`, `subagents_v2.md`
5. **Claims-ledger** [`sub: explore-haiku`] — `claims.csv`; статус и потолок уверенности считает `score_claims.py --write`, не модель (она завышает). `source_scoring.md`
5.5. **Evidence-фильтр** [`sub: explore-haiku`] (medium/deep) — relevance×authority; `unknown` — карантин. `evidence_filter.md`
5.7. **Сверка с вики** [`sub: explore-haiku`] (medium/deep) — до синтеза; конфликт с прошлым ресёрчем = обе позиции в отчёт. `wiki.md`
6. **Синтез + red team** [`sub: deepdive-synthesizer` + `sub: deepdive-redteam`; shallow — `main`] — `outline.md` → отчёт по секциям → `numbers.csv` → враждебные роли → один раунд ремедиации HIGH → `memo.md`. Источники и блоки читает синтезатор, главный поток — только его сводку и `memo.md`. Finder ≠ fixer. `phases/p6_synthesis.md` «Оркестрация», `adversarial_pass.md`
6.5. **Verify** [`sub: explore-haiku`, effort medium] (medium/deep) — четыре оси → `.verify/*.json`; чинится отчёт, не ledger. `runtime_verification.md`
6.9. **Человеческая версия** [`main`] (medium/deep) — `readout.md`, затем `humanizer-ru`, затем `uv run scripts/build_report.py <run>`. `report_export.md`
7. **Refresh targets + роевая постобработка** [`main`] (medium/deep) — `refresh_targets.md`, затем `collect_observations.py` → `update_priors.py` → `promote_candidates.py --track`; порядок и флаги в `swarm_postprocess.md`, читать перед первым вызовом.
8. **Decision walkthrough** [`main`] (всегда) — пройти с пользователем по вилкам `memo.md`; на вилки за него не отвечать. Исход → `application.md`. `decision_walkthrough.md`

## Stop-criteria — по содержанию, не по бюджету

**Стоп**: гипотезы подтверждены или опровергнуты ≥3 разнотипными источниками либо помечены «данных мало»; разобран ≥1 поиск оппозиции («X criticism / problems with X»); 4+ типа источников; насыщение — 5 источников подряд без нового `claim_id` и нового `root:` (считать по файлам).
**Не стоп**: источники противоречат (копай причину), все одного типа, контраргумент без разбора.
**Бюджет**: на medium/deep red team (6), Verify (6.5), `readout.md` (6.9) и `finish.py` не пропускаются и не сливаются в одного агента. Задан лимит денег (`--max-budget-usd`) — до Фазы 4 отложи ~40% на фазы 6–Finish и урезай раунды поиска и число фетчеров, а не поздние фазы; урезание — строкой в `Урезано:` меморандума. N9 (2026-10-28) потратил бюджет на поиск и остановился до red team с `Урезано: —`.
**Тупик**: третий поиск подряд даёт источники с `total < 8` ⇒ стоп, в Open Questions «литература слабая», предложи интервью или эксперимент.

## Finish-up

0. **Запусти `uv run scripts/finish.py --research-dir <root>/<slug>`** (`--offline` без сети): он сам строит `sources.csv`, сверяет леджер, гоняет liveness, пишет в вики и последним прогоняет `validate_phases.py --strict`. Красный ⇒ фаза пропущена: доделай, перезапусти, до зелёного не рапортуй «готово». Шаги по одному не гонять — пропуск флага и есть пропуск фазы.
1. Человеку — одна ссылка на `<date>_<slug>.html` (desktop: `SendUserFile`), ниже PDF и папка прогона; `memo.md` и технический отчёт в чат не выносить.
2. Резюме 5–8 строк языком `readout.md`, без кодов леджера: ответ · что поменяет решение · главный контраргумент · чего не нашли · итог walkthrough.
3. Предложи 2–3 следующих ресёрча; есть `memory/` — 1–3 кандидата в память.

## Что не делать

Полные формулировки и артефакты прогона — `phases/rules.md`.
- Не пропускать 5.5, 5.7, red team (medium/deep) и Фазу 8; не запускать medium/deep без if-then вилки; не писать финал «it depends».
- Не выдавать уверенность выше, чем даёт `score_claims.py`: без primary — не выше `medium`, непогашенный `dissent` от сильного источника = `contested`, `root:`/`discovery_path:` не копировать.
- Число без производителя и `data_as_of` в `memo.md` не идёт; проценты и доли — только в `numbers.csv` с `formula`: оси 6.5 арифметику не проверяют.
- WebFetch обходить только через `fetch_source.py`, не `curl`: он читает robots.txt и чистит страницу от prompt injection.
- Fetch-агентов не поднимать на opus «для качества» (растёт уверенность ошибки, не качество); во второй раунд — только дыры, не находки соседей.
- Из одного источника не цитировать дословно >25 слов; факт из памяти берётся без веб-сверки, только если шанс, что он изменился, <10%.
- `humanizer-ru` по `readout.md` не пропускать, технический отчёт им не чистить; `memo.md` вместо страницы человеку не отдавать.

## Режим update

`update <slug>` / «обнови ресёрч X» — дельта, не replay: `diffs/<date>_delta.md`, новый отчёт только если дельта существенна (решает пользователь), после дельты `wiki_ingest.py` и `wiki_pair.py build`. `refresh_protocol.md`

## References — читать при входе в фазу, не заранее

Выше названы файлы по фазам. Базовые для medium/deep: файл текущей фазы из `phases/`, `question_reframing.md`, `plan_gate.md`, `genres.md` (<!--gen:count:genres-->6<!--/gen--> жанров), `blocks/INDEX.md` (<!--gen:count:blocks-->106<!--/gen--> блоков), `channels.md` (<!--gen:count:channels-->29<!--/gen--> каналов), `source_dispatch.md`, `model_routing.md`, `wiki.md`. По условию: `awesome_lists_registry.md` (3.5), `stat_sources/INDEX.md` и `api_sources/INDEX.md` (<!--gen:count:api-->47<!--/gen-->+ endpoints; когда подвопрос количественный, ключи — через env vars), `fetch_ladder.md` (4.2), `NOTES_dated.md` (датированные факты).
