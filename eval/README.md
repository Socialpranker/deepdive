# Eval — на какой модели гонять research и как это мерить

Отвечает на два вопроса о deep-research скилле:

1. **На какой модели запускать ради экономии?** — короткий ответ: не на одной.
   Скилл гетерогенный, и роутинг (`references/model_routing.md`) уже раскидывает
   фазы по моделям сам: Opus на reframing/plan/adversarial (там качество
   мультиплицируется на весь ресёрч), Haiku на параллельный фан-аут субагентов
   (дёшево × N), Sonnet/high на синтез. Это ~$2 вместо ~$8 на deep — **и качество
   на критичных фазах выше**, потому что Opus там реально нужен. Гнать всё на одной
   модели — либо переплата (фан-аут на Opus), либо просадка (adversarial на Haiku).
   Перебить можно вручную: `... with all on opus` / `... with cheap mode`.

2. **Как мерить, если research делают разные модели?** — этот харнесс. Гоняешь
   один и тот же вопрос на разных конфигах, скорятся артефакты по 6-осевой рубрике
   (`rubric.md`), сравниваешь **quality на доллар**.

## Почему скоринг артефактов, а не API-скрипт

Скрипт меряет то, что скилл реально произвёл (все <!--gen:count:phases-->10<!--/gen--> фаз, роутинг, субагенты,
файлы `sources/`), а не воспроизведение его логики в коде. Цена этого — один
ручной шаг: точные токены прогона живут в харнессе Claude Code, скрипт их не
видит, поэтому `real_cost_usd` ты вписываешь руками из `/cost`.

## Как устроена оценка

Две группы осей (детали и веса — `rubric.md`):

- **Детерминированные (скрипт, не врут):** citation integrity (живы ли URL —
  ловит выдуманные ссылки), source diversity, cost proxy.
- **Смысловые (LLM-judge, нужно чтение):** factual accuracy, coverage/depth,
  adversarial honesty.

Итог — взвешенная сумма с **floor**: если citation integrity ниже порога (0.70),
quality режется вдвое. Иначе отчёт с галлюцинированными источниками победил бы за
счёт глубины. Победитель сравнения — лучший `quality_score / real_cost`.

## Workflow

```bash
# 0. (один раз) зависимости
pip install -r ../scripts/requirements.txt

# 1. положи вопрос
cp questions/EXAMPLE.md questions/my-q.md      # заполни

# 2. прогони ОДИН И ТОТ ЖЕ вопрос на разных конфигах, в Claude Code:
#    /model sonnet → /deep-research <вопрос>          → research/<slug>/
#    /deep research <вопрос> with all on opus         → research/<slug>-opus/
#    после каждого прогона запиши цену из /cost

# 3. зарегистрируй прогоны в runs/runs.csv (run_id, slug, config, real_cost_usd)

# 4. детерминированный проход + рендер judge-инпута
python score_run.py --research-dir ../research/<slug> --run-id A
#    → output/A_citations.{md,json}, output/A_judge_input.md, output/A_scorecard.md (partial)

# 5. прогони output/A_judge_input.md через Opus (отдельная сессия/Task),
#    сохрани вернувшийся JSON в output/A_judge.json

# 6. финальный scorecard со смысловыми осями + verdict
python score_run.py --research-dir ../research/<slug> --run-id A --judge-json output/A_judge.json

# 7. повтори 4-6 для каждого конфига, сравни quality_per_dollar в scorecard'ах
```

## Скрипты

| Файл | Что делает |
|---|---|
| `check_citations.py` | Проверяет, живы ли URL источников (sources/*.md → fallback sources.csv). Помечает OPEN+404 как 🚩 (вероятная галлюцинация). Транспортные сбои (SSL/DNS) → UNKNOWN, исключены из знаменателя. `--strict` для CI. |
| `score_run.py` | Оркестратор: citations + diversity + cost-прокси, рендерит judge-инпут, с `--judge-json` собирает финальный взвешенный scorecard. Веса читает из `rubric.md`. |
| `judge_prompt.md` | Промпт для LLM-judge (оси 3/4/5), строгий JSON на выходе, анти-gaming инструкции. |
| `rubric.md` | SSoT: 6 осей, шкалы, веса, floor. Меняешь веса — здесь. |

## Заметки

- **Прокси в окружении.** `check_citations.py` ходит с `trust_env=False` — игнорит
  `HTTP(S)_PROXY` из env. Если у тебя поднят локальный VPN/прокси (видел
  `127.0.0.1:1082`), без этого все проверки падали бы с ProxyError.
- **Вариативность citation integrity** ±0.03 между прогонами — это SSL-флап
  некоторых хостов, не код. На сравнении в рамках одного прогона не сказывается.
- **Повторы для дисперсии.** Если два конфига близки по `quality_per_dollar`
  (в пределах ~10%) — прогони каждый 2-3 раза и усредни. На старте не нужно.
- **Old-schema CSV.** Прогоны до текущего шаблона имеют `sources.csv` без колонок
  `type`/`used` — diversity тогда считается по `channel` (fallback). Если и его
  нет — ось помечается `n/a`, а не зануляется.
