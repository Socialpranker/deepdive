# Model Routing — какую модель Claude брать на каждый шаг

**Когда используется:** в начале каждой фазы выбираешь модель и effort под характер задачи. Простую работу — на Haiku (дёшево, быстро). Длинный контекст и понимание текстов — Sonnet. Сложное рассуждение и архитектурные решения — Opus.

**Зачем:** без явного routing'а скилл по умолчанию работает на той модели что запустил пользователь — обычно Sonnet. Это **дорого для массовой простой работы** (поиск URL, скоринг, dedupe) и **слабовато для критичных моментов** (reframing, adversarial pass).

---

## Принципы

1. **Дороже не значит лучше.** Простая задача на Opus = пустая трата токенов. Сложная на Haiku = слабый результат.
2. **Effort важнее модели.** На той же модели разные `effort` дают разный результат: Sonnet/high может быть лучше чем Opus/low для middle-сложности задачи.
3. **Параллелизм — повод для дешёвой модели.** Если запускаем 5 sub-agents в Phase 4, они должны быть на Haiku/Sonnet, не на Opus. Иначе цена ресёрча умножается на 5.
4. **Финальные deliverables — повод для дорогой модели.** Phase 1 reframing, Phase 6 adversarial, Phase 7 synthesis — это где качество мультиплицируется на весь ресёрч. Не экономить.
5. **Главный поток vs sub-agent.** Главный поток (где живёт пользователь) обычно требует Sonnet+ для диалога. Sub-agents можно сильно дешевле — у них узкая задача с фиксированным output.
6. **Экономика сместилась: Opus всего 5× от Haiku** (см. Cost economics ниже). Не экономь на критических одиночных вызовах (reframing, adversarial) — экономь на fan-out (N параллельных sub-agents в Phase 4 и в gap-волне внутри Phase 5).

---

## Matrix: фаза × подзадача → модель + effort

| Фаза | Подзадача | Модель | Effort | Обоснование |
|---|---|---|---|---|
| **Pre-discover** | Чтение CLAUDE.md, проверка существующих ресёрчей | inherit | inherit | Главный поток, не нужно переключать |
| **Phase 1** | Reframing — переформулировка вопроса, формулировка гипотез | **Opus** | high | Качество reframing'а определяет весь ресёрч на часы вперёд. Не экономить. |
| **Phase 2** | Genre selection, выбор блоков | **Sonnet** | medium | Решение на основе таблицы пресетов из genres.md — не нужен Opus |
| **Phase 3** | Plan composition (17 секций) | **Opus** | medium | Архитектурное решение, документирует все будущие выборы |
| **Phase 3.5** | Capability discovery — env vars audit, mapping | **Sonnet** | low | Механический проход, простые таблицы |
| **Phase 4.0** | Source Dispatch — прогон подвопросов через matrix | **Sonnet** | medium | Lookup в `source_dispatch.md` + запись в plan.md |
| **Phase 4.1** | Launch sub-agents (web search, simple lookups) | **Haiku** | low | Sub-agents с узкой задачей и JSON output. Дёшево × N агентов. Скорит сам, см. Phase 5 |
| **Phase 4.1** | Launch sub-agents (чтение длинных источников, извлечение цитат) | **Sonnet** | low | Когда нужен длинный контекст под цитаты |
| **Phase 4.1** | Launch sub-agents (api-direct: curl + jq + parse) | **Haiku** | low | Bash работа + механический парсинг JSON |
| **Phase 4.1** | Launch sub-agents (анализ кода в репозитории) | **Sonnet** | medium | Code understanding требует средней модели |
| **Phase 4.2** | Fetch + dedup (главный поток) | **Sonnet** | medium | Управляет sub-agents, агрегирует результаты |
| **Phase 4** | Goal-check между раундами — per-subquestion `goal_status` met/partial/unmet + gap | **Haiku** | low | Non-thinking evaluator (deer-flow): называет дыру, чтобы Opus-evaluation работал по диагнозу, а не выводил его с нуля. Только labels, решений не принимает |
| **Phase 4.3** | Save sources to files | **Haiku** | low | Пишет сам fetch-агент в свой диапазон номеров, см. `subagents_v2.md` |
| **Phase 4.5** | Gap-волна — точечные агенты на дыры в `claims.csv` (status ≠ triangulated), максимум 2 круга | **Haiku** | low | Узкая задача «найди ещё один источник типа X на claim Y» — не нужна дорогая модель |
| **Phase 5** | Scoring (credibility/recency/bias по rubric) | *(встроено в Phase 4.1, см. выше)* | — | Отдельный проход не запускается — скорит тот агент, который читал источник |
| **Phase 4** | Snowball-пасс — backward/forward цепочки цитирований топ-K источников (medium/deep) | **Haiku** | low | Механическая работа с citation-API (OpenAlex/S2) + списками литературы, по суб-агенту на источник |
| **Phase 5** | Triangulation check по `claims.csv` (механическая: ≥3 источника И ≥2 типа И ≥2 корней `root:` → triangulated) | **Haiku** | low | Правило механическое — подсчёт источников/типов/корней по строке, не нужна дорогая модель |
| **Phase 3.7** | Скаут-пасс внутри план-гейта — «какие подвопросы мы не задали» | **Haiku** | low | Короткая разведка `Explore` без записи источников, отдельной фазы не заводит. Дёшево ×3-4 агента, см. `plan_gate.md` шаг 1.5 |
| **Phase 5.5** | Evidence-фильтр: relevance × authority по несущим парам | **Sonnet** | low | Две парные классификации по дословным цитатам; `haiku` не тянет authority-чек-лист, `opus` — переплата |
| **Phase 6** | Multi-angle red team — N враждебных ролей как суб-агенты | **Opus** | high/xhigh | **Самая дорогая модель здесь обязательна.** Атака на гипотезы (Skeptic/Contrarian/Gap-hunter/Исполнитель/Адвокат меньшинства) требует настоящего рассуждения, не паттерн-матчинга. Medium → sonnet/high. Ценность даёт РАЗНОСТЬ РОЛЕЙ и изоляция контекстов, не класс модели — не «поднять всех на opus», а развести роли |
| **Phase 6.5** | Verify — liveness + faithfulness цитат | **Haiku** | low | Механическая проверка + entailment на коротких парах claim⊨quote |
| **Phase 7** | Synthesis — сборка отчёта из блоков | **Sonnet** | high | Длинный контекст всех источников + блоков + плана. Sonnet/high лучше чем Opus/medium здесь |
| **Phase 7** | Final report write-up (язык, стиль, чистка) | **Sonnet** | medium | Качественное письмо |
| **Phase 8** | Decision walkthrough — исполнение отчёта по вилкам Decision Spec с пользователем | **Opus** | high | Главный поток, не суб-агент. Качество вопросов мультиплицируется на применимость всего ресёрча — как в Phase 1, не экономить |

Phase 6 red-team суб-агенты: deep → opus/high (R1+R2+R3+R4); medium → sonnet/high (R1+R2+R4); shallow → R1 инлайн (sonnet/high, без суб-агента). Synthesis/chairman → sonnet/high. Cost: +4 суб-агента на deep-отчёт (≈ дёшево относительно поиска).

---

## Routing для sub-agents (Phase 4.1)

В Phase 4.1 запускается N (2-5) sub-agents параллельно. Каждый получает узкую подзадачу. Модель **не одна на всех** — она зависит от **типа подзадачи**:

| Тип подзадачи sub-agent'а | Сигналы | Модель | Effort |
|---|---|---|---|
| Web search + extract metadata (URL/title/date/snippet) | primary channel = `web-general`, `news-current`, `forum-discussion` | **Haiku** | low |
| Read long source + extract pinned quotes | подзадача требует чтения 5-10 длинных страниц | **Sonnet** | low |
| Academic paper search + abstracts | primary channel = `academic`, `preprint-servers` | **Sonnet** | low (long abstracts) |
| API-direct request + parse JSON | primary channel = `api-direct` (FRED, World Bank, etc.) | **Haiku** | low |
| Code analysis (clone + grep + understand) | primary channel = `code-github` + impl-question | **Sonnet** | medium |
| Scraping site с pagination/state | primary channel = `competitive-signals` + scraping | **Sonnet** | medium |
| Heavy reasoning sub-task (rare) | подвопрос «оцени trade-offs между X и Y», не просто факт-сбор | **Opus** | medium |

**Default для sub-agent** если не уверен → **Sonnet / low**. Это safe middle ground.

**Скоринг встроен.** Каждый fetch sub-agent сам скорит источник тем же вызовом (читает → проставляет credibility/recency/bias → пишет `sources/NN.md` в свой диапазон номеров, `general-purpose` а не `Explore` — см. `subagents_v2.md`). Отдельного scoring pass нет.

---

## Cost economics

Цены на модели меняются быстрее, чем этот файл переписывается — проверяй актуальное через
скилл `claude-api` (он автосинкается), не по памяти. Срез на 2026-08-16:

| Модель | Model ID | Алиас в `Agent` | Input $/1M | Output $/1M | Контекст | Ratio vs Haiku |
|---|---|---|---|---|---|---|
| Haiku 4.5 | `claude-haiku-4-5` | `haiku` | $1.00 | $5.00 | **200K** | 1× |
| Sonnet 5 | `claude-sonnet-5` | `sonnet` | $3.00 (интро $2.00 до 2026-08-31) | $15.00 (интро $10.00) | 1M | 3× |
| Opus 5 | `claude-opus-5` | `opus` | $5.00 | $25.00 | 1M | 5× |
| Fable 5 | `claude-fable-5` | `fable` | $10.00 | $50.00 | 1M | 10× |

**Главный сдвиг: Opus всего 5× от Haiku** (было 18.75× при $15/$75). Держать Opus на Phase 1/Phase 6 — почти бесплатно. Экономить нужно на fan-out (N sub-agents в Phase 4), не на этих фазах.

**Haiku — единственная модель с 200K контекстом, остальные 1M.** Отсюда правило Phase 4.1: подзадача «прочитать 5-10 длинных страниц» идёт на `sonnet`, не на `haiku`, — не из-за качества, а из-за окна.

**Fable 5 главным оркестратором не ставить.** Только по явному запросу пользователя и только на многодневные прогоны; в deep-research его цена не окупается ни на одной фазе.

## Effort: чем управляем, а чем нет

`Agent` tool принимает **только `model`** — параметра `effort` у него нет. Effort суб-агента наследуется от сессии; колонка Effort в матрице ниже описывает **желаемую глубину**, а не то, что можно передать вызовом. Управляемые рычаги:

- **главный поток** — `/effort` в сессии (`low`/`medium`/`high`/`xhigh`/`max`);
- **суб-агенты** — только выбор модели; хочешь мельче — бери модель дешевле, а не «effort ниже»;
- **`Workflow`-скрипты** — там `agent()` принимает `opts.effort`, это единственное место, где per-call effort реален.

Уровни `xhigh` и `max` появились после первой редакции этого файла. `xhigh` — рабочий максимум для кодинга и агентных задач; `max` прожорлив и склонен к overthinking. Для deep-research: `xhigh` уместен на Phase 6 (red team) и Phase 1 (reframing), `max` — не уместен нигде (ресёрч упирается в качество источников, не в глубину рассуждения одной модели).

**Иллюстрация (deep, ~5 sub-agents):** всё на Opus = 250k in + 50k out ≈ **$1.62** только на Phase 4. Правильный routing: Phase 1 Opus/high $0.075 + Phase 3 Opus/medium $0.115 + Phase 4 5×Haiku/low $0.15 + Phase 6 Opus/high $0.275 + Phase 7 Sonnet/high $0.405 = **~$1.02** total. Разница уже не в разах — но не экономить на Phase 1/6 остаётся правилом архитектурным (узкая задача = дешёвая модель), не ценовым.

(Порядок величин, не точный прогноз — проверяй актуальные цены.)

---

## Как передать модель в `Agent`-tool

В Claude Code SDK `Agent` принимает параметр `model`:

```
Agent({
  subagent_type: "general-purpose",   // fetch+save нужен Write; Explore — только для read-only разведки
  model: "haiku",  // или "sonnet" / "opus"
  description: "...",
  prompt: "..."
})
```

Если параметр не передан — sub-agent наследует модель родительского контекста (обычно Sonnet).

**В шаблонах промптов Phase 4.1** в `subagents_v2.md` каждый sub-agent явно проставляет `model:` на основе своего типа задачи.

---

## Как сообщать пользователю

В начале medium/deep ресёрча, после Phase 3 (plan готов), один раз:

```
Запускаю medium ресёрч. Routing:
- Phase 1, 3, 6: Opus/high (reframing, plan, adversarial)
- Phase 4: 3 sub-agents на Haiku (web/news/forum), 1 на Sonnet (academic)
- Phase 5, 7: Sonnet/medium

Estimated cost: ~$2 (vs ~$8 если бы всё на Opus)
```

Это не маркетинг — это **прозрачность**, у пользователя должна быть возможность сказать «нет, мне нужно качество, гони всё на Opus».

---

## Override-механика

Пользователь может явно перебить:

```
> deep research X with all on opus
```

Тогда router игнорируется, и **все** фазы и sub-agents идут на Opus. Цена выше, для high-stakes решений ОК.

Аналогично:
- `... with cheap mode` → всё на Haiku где возможно, Sonnet только на Phase 1/6/7
- `... with default routing` (или ничего) → matrix выше

---

## Anti-patterns

**❌ Запускать Phase 6 adversarial на Haiku.** Adversarial — это критическое мышление. Haiku тут будет soft-pushback'ом без реальной atak на гипотезы. Только Opus/high.

**❌ Запускать 5 параллельных sub-agents все на Opus.** Это умножение цены на 5 без оправдания. Sub-agents с узкой задачей — Haiku/Sonnet.

**❌ Поднимать fetch-агентов Phase 4.1 на Opus «для качества».** Дело не только в цене. Способность модели ортогональна её «просоциальности» в многоагентной конфигурации (Anthropic Frontier Red Team, 13.08.2026): более сильная модель не координируется лучше — она увереннее и быстрее делает по-своему. У fetch-агента есть `Write` и изолированный контекст, то есть право действовать без надзора; на сильной модели растёт не качество поиска, а цена ошибки — увереннее выбранная не та трактовка подтемы, увереннее проставленный `root`, увереннее отброшенный источник. Границы (диапазон id, зафиксированный dispatch, обязательные поля) держат качество лучше, чем класс модели.

**❌ Считать `xhigh`/`max` бесплатным улучшением.** Выше effort — длиннее траектория и больше склонность к overthinking. На Phase 4 это прямо вредно: агенту нужно собрать источники по зафиксированной стратегии, а не переизобрести её.

**❌ Не сообщать пользователю про routing.** Прозрачность экономии — это **фича**, не пасхалка. Один раз вначале сказать какой routing и estimated cost.

**❌ Игнорировать override.** Если пользователь сказал «всё на Opus» — слушайся, не «оптимизируй за спиной».

**❌ Hardcoded routing «всегда Sonnet везде».** Это потеря преимуществ Haiku на простой работе и Opus на критической.
