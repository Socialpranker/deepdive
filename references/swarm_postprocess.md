# Постобработка прогона — сбор наблюдений байесовского роя

Читать в конце medium/deep прогона (после Фазы 7, до Фазы 8 или сразу после неё).

Работает по уже готовым артефактам прогона, руками ничего писать не нужно. `run_id` = `<slug>` прогона, один и тот же во всех четырёх вызовах. Механика — `docs/specs/2026-08-18-bayesian-swarm-design.md`.

**1. Наблюдения — отдельный вызов на КАЖДЫЙ подвопрос** из `plan.md` §12, с его `qclass` и реально запрошенными каналами (primary + secondary + fallback, если fallback понадобился):

```
python3 scripts/collect_observations.py --research-dir <root>/<slug> --run-id <slug> \
  --requested academic=scientific-claim,data-statistical-gov=scientific-claim
```

Общим списком на весь прогон — нельзя: `--requested` парсится в словарь по ключу-каналу, и один канал с разным `qclass` в одной строке молча затрёт первую пару. Раздельные вызовы аппендят независимо.

**2. Приоры:** `python3 scripts/update_priors.py`. Доли секунды, звать после каждого прогона: без этого наблюдения не попадут в `priors.json` и следующий прогон не увидит статистику.

**3. Ad-hoc источники** — найденные через Discovery patterns (`source_dispatch.md`), а не из каталога (`api_sources/`, `stat_sources/`, `registry/`), и ставшие `root` или непогашенным `dissent` хотя бы одного claim. `url` и первый сегмент `discovery_path` (это канал) — из `sources/NN.md`, `qclass` — из §12. Мёртвый на момент прогона — тот же вызов с `--dead`.

```
python3 scripts/promote_candidates.py --track https://api.example.org/v1 \
  --channel api-direct --qclass market-size --run-id <slug>
```

**4. Раз в несколько прогонов:** `python3 scripts/promote_candidates.py --write` — печатает промоушен (≥3 улики в ≥3 разных прогонах, живой endpoint, приор канала не деградировал) и демоушен (≥3 прогона подряд мёртв). Без `--write` только печать; с `--write` пишет в `references/api_sources/promoted/` — **посмотреть `git diff`, закоммитить вручную**, скрипт не коммитит никогда.

Аллокатор свободного бюджета сверх обязательного минимума — `update_priors.py --qclass <qclass подвопроса>` при выборе канала сверх Primary/Secondary; оговорки — `source_dispatch.md` §«Приор при выборе канала сверх обязательного минимума».

