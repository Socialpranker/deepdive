## Фаза 5. Claims-ledger и триангуляция

**Исполнитель:** сборка `claims.csv` из index-строк — `sub: explore-haiku` (haiku / medium из frontmatter; на low Haiku 5.5 пропускает проверки). Triangulation check — скрипт `score_claims.py --write`, модель не нужна (правило механическое, см. ниже — только подсчёт источников/типов/корней по строке).

**Скоринг источников больше не отдельный шаг.** Каждый источник в `sources/NN.md` уже имеет заполненный frontmatter со scoring — его проставил fetch sub-agent на шаге 4.1, в момент когда читал источник (H7-правило: скорит тот, кто читал). Здесь, в Фазе 5, шкала подробно описана в `source_scoring.md` для справки, но повторного прохода по всем источникам не требуется.

**Claims-ledger (`claims.csv`)** — новый артефакт-ledger рядом с `sources.csv`. Схема:

```
claim_id, claim, hypothesis, sources, source_types, roots, paths, status, confidence, primary_source, source_caveat, dissent, as_of
```

- `claim` — тезис одной строкой.
- `hypothesis` — H1-H4 или `-` если не привязан к гипотезе.
- `sources` — список id (`s01;s07;s12`).
- `source_types` — типы источников через `;` (`primary;academic;industry`).
- `roots` — корни через `;`, тот же порядок что `sources` (`own;study-smith-2024;own`); из `root:` во frontmatter каждого источника. Без этой колонки третье условие триангуляции нечем проверить.
- `paths` — пути обнаружения через `;`, тот же порядок; из `discovery_path:`. Без неё нечем проверить четвёртое условие (независимость поиска, а не только источников).
- `status` — `triangulated | contested | weak | single-type | single-root | single-path | contradicted | data-insufficient`.
- `confidence` — `high | medium | low`.
- `primary_source` — `Y | N`.
- `source_caveat` — `- | vendor | self-reported | disputed:sNN`.
- `dissent` — id источников, ПРОТИВОРЕЧАЩИХ тезису (`s12;s19`), или `-`. Берётся из полей `dissent`/`contradictions` в JSON суб-агентов. Пустое поле в спорной теме — сигнал, что оппозицию не искали, а не что её нет.
- `claim_class` (опционально, после `as_of`) — `empirical` (по умолчанию: утверждение о мире) | `documentary` («документ X говорит Y» — закон, стандарт, условия продукта; high на одном первичном источнике законен, сам документ и есть доказательство).
- `as_of` — для волатильных чисел (цена, доля рынка, версия, курс): дата ЗАМЕРА `YYYY-MM`/`YYYY-QN` из поля `data_as_of` источника; `unknown` — число есть, даты нет; `-` для нечисловых. **Источник значения — `data_as_of` во frontmatter, а не дата публикации статьи и не догадка главного потока** (он источников не читал). Число без даты замера — не факт, а мина для будущего `update`, и по fail-closed правилу оно не попадает в `memo.md`.

**Одна строка — одно утверждение.** «X вырос на 20%; Y упал на 5%» — две строки: у каждой свои источники и свой статус. `;` или два предложения в `claim` скрипт считает составным тезисом и роняет finish.

**Заполнение:** главный поток собирает `claims.csv` из `claim_candidates`, которые вернул каждый fetch sub-agent (см. `subagents_v2.md`), плюс из явного чтения claims в уже записанных `sources/NN.md`. Дублирующиеся claim'ы от разных агентов — смёржить в одну строку (объединить `sources`/`source_types`).

**Статус и потолок confidence считает скрипт, не модель.** Модель пишет `claim_id`, `claim`, `hypothesis`, `sources`, `source_caveat`, `dissent`, `as_of`, `claim_class`; затем
`python scripts/build_sources_csv.py --research-dir <run> && python scripts/score_claims.py --research-dir <run> --write` — скрипт заполняет `source_types`/`roots`/`paths`/`primary_source` из `sources.csv`, считает `status` и режет `confidence` до потолка. Один URL в двух файлах — одно плечо: во всех ячейках остаётся наименьший id группы, остальные файлы группы слей в него: `--strict` краснеет на любой паре файлов с одним URL; тонкий источник — не плечо. Модель может только понизить: `contradicted`/`data-insufficient` скрипт сохраняет. Аудит 70 прогонов: 18 `triangulated` на <3 источниках и 282 `high` на одном источнике — правила ниже были верны, их применение моделью — нет. `finish.py` гоняет тот же скрипт с `--strict`: расхождение леджера с подсчётом = красный finish.

**Triangulation rule (механическая):** строка получает `status: triangulated`, если ≥3 источника **И** ≥2 разных типа **И** ≥2 различных корней (`root:`) **И** ≥2 различных пути обнаружения (`discovery_path:`) — см. `source_scoring.md` «Provenance» и «Четвёртое условие». Иначе:
- < 3 источников → `status: weak`, confidence: low (исключение — `claim_class: documentary` с первичным источником: high)
- ≥3 источника, но один тип → `status: single-type`, confidence: medium (max)
- ≥3 источника и ≥2 типов, но все сводятся к одному `root:` → `status: single-root`, confidence: medium (max) — десять пересказов одного пресс-релиза это один голос; правило считает корни, не URL
- ≥3 источника, ≥2 типов, ≥2 корней, но все найдены одним `discovery_path` → `status: single-path`, confidence: medium (max) — одна формулировка в одном канале даёт одну выборку из одного индекса, а не три независимых голоса
- Есть непогашенный `dissent` от источника с `type: Primary` или `credibility ≥ 4` → `status: contested`, confidence: medium (max) — **правило большинства здесь не действует**; в отчёт идут обе позиции с явным основанием выбора (см. «Правило dissent» в `source_scoring.md`)
- Явное противоречие между источниками без выраженного меньшинства → `status: contradicted` — отдельный counter-argument (Z1)
- После gap-волны (см. выше) всё ещё не закрыто → `status: data-insufficient` (честный результат, не скрывать)

**Primary-first правило:** ключевое число/факт без хотя бы одного primary-источника (`primary_source: N`) не может получить `confidence` выше `medium`, даже если формально triangulated по количеству/разнотипности. Primary здесь — filing, официальная дока, датасет, оригинальное исследование (см. Credibility=5 в `source_scoring.md`).

**После сборки** — обнови `sources.csv` (индекс источников, как раньше) и новый `claims.csv`:

```csv
№,URL,Title,Type,Author,Date,Credibility,Recency,Bias,Total,Used,File,Note
1,https://...,Postgres logical replication docs,Primary,Postgres team,2024-09,5,4,4,13,Y,sources/01_pg-docs-logical.md,Primary source
2,https://...,Industry benchmark,Industry-media,J. Smith,2026-02,4,5,4,13,Y,sources/02_industry.md,Supports H1
```

```csv
claim_id,claim,hypothesis,sources,source_types,roots,paths,status,confidence,primary_source,source_caveat,dissent,as_of
CL1,"Logical replication scales to N nodes without external tooling",H1,s01;s07;s12,primary;industry;academic,own;study-smith-2024;own,academic|logical replication N nodes|en;web-general|postgres multi-master 2026|en;forum-discussion|pgsql-hackers|en,triangulated,high,Y,-,-,-
CL2,"CDC adds >200ms p99 latency at scale",H2,s09;s14,industry;industry,own;own,web-general|CDC latency benchmark|en;web-general|CDC latency benchmark|en,single-type,medium,N,-,-,2026-02
```

### Gap-волна (Фаза 5 продолжается — не новая фаза, аналогично loop-конвенции Фазы 4)

**Исполнитель:** `sub: deepdive-fetcher` (haiku / medium из frontmatter). Узкая точечная задача на конкретную дыру — дорогая модель не нужна, но это поиск, а на low Haiku 5.5 пропускает поиски.

После первого заполнения `claims.csv` собери список дыр — строки со `status ≠ triangulated`.

**Точечная вторая волна:** по одному агенту на дыру (или пачкой, параллельно), промпт = конкретный claim + чего конкретно не хватает:
- «нужен primary-источник для CL2»
- «нужен 3-й тип источника, сейчас только industry×2»
- «противоречие между s09 и s14 — найти причину или дополнительный арбитр»

**Максимум 2 круга.** Если после второго круга дыра не закрылась — строка помечается `status: data-insufficient`. Это честный результат отчёта, не провал: попадает в Open Questions (Z2), а не маскируется.

**Выход:** обновлённый `claims.csv`, обновлённые `sources/NN.md` (новые источники в свежем диапазоне номеров — следующий свободный блок после уже занятых).
