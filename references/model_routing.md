# Model Routing — какую модель Claude брать на каждый шаг

## Содержание

- Принципы
- Matrix: фаза × подзадача → исполнитель + effort
- Routing для sub-agents (Phase 4.1)
- Cost economics
- Effort: чем управляем, а чем нет
- Как передать модель в `Agent`-tool
- Как сообщать пользователю
- Override-механика
- Anti-patterns

**Когда используется:** в начале каждой фазы выбираешь исполнителя и effort под характер задачи. Простую работу (поиск, чтение, извлечение, классификация) — суб-агентам на Haiku 5.5 (дёшево, быстро). Сложное рассуждение и архитектурные решения — `main` (Opus) или `sub: deepdive-redteam`.

**Зачем:** без явного routing'а суб-агент наследует модель главной (сейчас Opus 5.5); забытый параметр `model` = дорогой вызов. Это **дорого для массовой простой работы** (поиск URL, скоринг, dedupe) и **слабовато для критичных моментов** (reframing, adversarial pass).

---

## Принципы

1. **Дороже не значит лучше.** Простая задача на Opus = пустая трата токенов. Сложная на Haiku = слабый результат.
2. **Effort важнее модели.** На той же модели разные `effort` дают разный результат: Sonnet/high может быть лучше чем Opus/low для middle-сложности задачи.
3. **Параллелизм — повод для дешёвой модели.** Если запускаем 5 sub-agents в Phase 4, они должны быть `sub: deepdive-fetcher` (Haiku), не на Opus. Иначе цена ресёрча умножается на 5.
4. **Финальные deliverables — повод для дорогой модели.** Phase 1 reframing, Phase 6 red team и синтез — это где качество мультиплицируется на весь ресёрч. Не экономить.
5. **Главный поток vs sub-agent.** Главный поток (`main`, где живёт пользователь) — Opus. Sub-agents можно сильно дешевле — у них узкая задача с фиксированным output.
6. **Экономика: Opus многократно дороже Haiku 5.5** (множители — в Cost economics ниже и в NOTES.md). Не экономь на критических одиночных вызовах (reframing, adversarial) — экономь на fan-out (N параллельных sub-agents в Phase 4 и в gap-волне).

---

## Matrix: фаза × подзадача → исполнитель + effort

> **Главная сессия — Opus 5.5 (effort `medium`; дата перехода — `NOTES_dated.md`).** Исполнитель `main` — это модель главной сессии (Opus 5.5); отдельной модели для него не выбирают. Если сессию явно подняли на Fable 5.1 — **не переключаться вниз**, Fable покрывает клетки `main`. Исполнители `sub: …` — суб-агенты через `Agent`, от модели сессии не зависят. У агентов из `~/.claude/agents/` (`deepdive-*`, `explore-haiku`) модель и effort записаны во frontmatter, и вызов их не передаёт: per-call значение перебивает frontmatter, и тогда настройку агента меняют в двух местах, а расходятся они молча. `model` и `effort` per-call получают только встроенные типы (`general-purpose`). Fable в суб-агентах не использовать никогда (цену см. в NOTES.md, а нарезка уже сделана главной).
>
> **Кибер- и био-темы.** Переносится только модель главной: её при необходимости уводят на `claude-opus-5` (явным ID); у Opus 5.5 и Fable фильтры `bio`/`cyber` одного уровня, оба могут вернуть `stop_reason: refusal`. На суб-агентов это не распространяется: у Haiku 5.5 свой cyber-классификатор и фоллбэка нет (NOTES.md, «Оркестрация», блок Security). Fetch по таким темам идёт через `sub: deepdive-fetcher` (Haiku из frontmatter), и Haiku может отказать (`stop_reason: refusal`). Повтор того же запроса снова откажет, поэтому при отказе подзадачу забирает `sub: general-purpose` с `model: "sonnet"`, `effort: "high"`: тот же бриф плюс строка «формат и правила — прочитай `~/.claude/agents/deepdive-fetcher.md`».

Словарь исполнителей: `main` (модель главной, Opus); `sub: deepdive-scout` (Haiku); `sub: deepdive-fetcher` (Haiku); `sub: deepdive-redteam` (Opus, high); `sub: deepdive-synthesizer` (Opus, high, пишет отчёт); `sub: explore-haiku` (Haiku, read-only); `sub: general-purpose` (только пишущие задачи вне перечисленных).

| Фаза | Подзадача | Исполнитель | Effort | Обоснование |
|---|---|---|---|---|
| **Pre-discover** | Чтение CLAUDE.md, проверка существующих ресёрчей | `main` | inherit | Главный поток, не нужно переключать |
| **Phase 1** | Reframing — переформулировка вопроса, формулировка гипотез | `main` | inherit (medium) | Opus 5.5 на medium не хуже Opus 5 на high. xhigh — только если замер показал выигрыш |
| **Phase 2** | Genre selection, выбор блоков | `main` | medium | Решение на основе таблицы пресетов из genres.md |
| **Phase 3** | Plan composition (17 секций) | `main` | medium | Архитектурное решение, документирует все будущие выборы |
| **Phase 3.5** | Capability discovery — env vars audit, mapping | `sub: explore-haiku` | medium | Haiku 5.5 на low пропускает поиск и проверки |
| **Phase 4.0** | Source Dispatch — прогон подвопросов через matrix | `main` | medium | Lookup в `source_dispatch.md` + запись в plan.md |
| **Phase 4.1** | Launch sub-agents (web search, simple lookups) | `sub: deepdive-fetcher` | medium | Узкая задача и JSON output. Дёшево × N агентов. Скорит сам, см. Phase 5 |
| **Phase 4.1** | Launch sub-agents (чтение длинных источников, извлечение цитат) | `sub: deepdive-fetcher` | medium | Окно Haiku 5.5 — 1M (NOTES.md), длинные источники помещаются |
| **Phase 4.1** | Launch sub-agents (api-direct: curl + jq + parse) | `sub: deepdive-fetcher` | medium | Bash работа + механический парсинг JSON |
| **Phase 4.1** | Launch sub-agents (анализ кода в репозитории) | `sub: deepdive-fetcher` | medium | Факты и пути собирает fetcher; выводы о причинах делает `main` |
| **Phase 4.2** | Fetch + dedup (главный поток) | `main` | medium | Управляет sub-agents, агрегирует результаты |
| **Phase 4** | Goal-check между раундами — per-subquestion `goal_status` met/partial/unmet + gap | `main` | low | Называет дыру, чтобы evaluation работал по диагнозу, а не выводил его с нуля. Только labels, решений не принимает |
| **Phase 4.3** | Save sources to files | `sub: deepdive-fetcher` | medium | Пишет сам fetch-агент в свой диапазон номеров, см. `subagents_v2.md` |
| **Phase 4.5** | Gap-волна — точечные агенты на дыры в `claims.csv` (status ≠ triangulated), максимум 2 круга | `sub: deepdive-fetcher` | medium | Узкая задача «найди ещё один источник типа X на claim Y» — не нужна дорогая модель |
| **Phase 5** | Scoring (credibility/recency/bias по rubric) | *(встроено в Phase 4.1, см. выше)* | — | Отдельный проход не запускается — скорит тот агент, который читал источник |
| **Phase 4** | Пул кандидатов `candidates.csv` (title+snippet, академические API, snowball) — без чтения (medium/deep) | `sub: explore-haiku` | medium (frontmatter) | Отбор по сниппетам не требует рассуждения, но пул собирается поиском по API, а на low Haiku 5.5 пропускает поиски; дорогое — чтение, оно у fetcher'ов |
| **Phase 5** | Triangulation check по `claims.csv` (механическая: ≥3 источника И ≥2 типа И ≥2 корней `root:` → triangulated) | `main`: `score_claims.py --write` | — | Правило механическое, его считает скрипт; агент не нужен |
| **Phase 3.7** | Скаут-пасс внутри план-гейта — «какие подвопросы мы не задали» | `sub: deepdive-scout` | medium (frontmatter) | Короткая разведка без записи источников, отдельной фазы не заводит. Дёшево ×3-4 агента, см. `plan_gate.md` шаг 1.5 |
| **Phase 5.5** | Evidence-фильтр: relevance × authority по несущим парам | `sub: explore-haiku` | medium | Две парные классификации по дословным цитатам; на low Haiku пропускает проверки |
| **Phase 6** | Multi-angle red team — N враждебных ролей как суб-агенты (deep: R1–R5; medium: R1+R2+R4, +R5 при dissent) | `sub: deepdive-redteam` | high | **Сильная модель здесь обязательна.** Атака на гипотезы (Skeptic/Contrarian/Gap-hunter/Исполнитель/Адвокат меньшинства) требует настоящего рассуждения, не паттерн-матчинга. Ценность даёт РАЗНОСТЬ РОЛЕЙ и изоляция контекстов, не класс модели — не «поднять всех на opus», а развести роли |
| **Phase 6.5** | Verify — liveness + faithfulness цитат | `sub: explore-haiku` | medium | Entailment claim⊨quote — суждение; на low Haiku пропускает проверки |
| **Phase 6** | Synthesis — сборка отчёта из блоков | `sub: deepdive-synthesizer` | high | Длинный контекст всех источников + блоков + плана держит субагент, в главный поток он не попадает |
| **Phase 6** | Final report write-up (язык, стиль, чистка) | `main` | medium | Качественное письмо |
| **Phase 8** | Decision walkthrough — исполнение отчёта по вилкам Decision Spec с пользователем | `main` | high | Главный поток, не суб-агент. Качество вопросов мультиплицируется на применимость всего ресёрча — как в Phase 1, не экономить |

Phase 6 red-team: deep → `sub: deepdive-redteam` (все пять ролей R1–R5); medium → `sub: deepdive-redteam` (R1+R2+R4, +R5 при dissent); shallow → R1 инлайн, выполняется на `main` (без суб-агента). Synthesis/chairman → `sub: deepdive-synthesizer` (medium/deep), `main` на shallow. Cost: +4–5 суб-агентов на deep-отчёт (≈ дёшево относительно поиска).

---

## Routing для sub-agents (Phase 4.1)

В Phase 4.1 запускается N (2-5) sub-agents параллельно. Каждый получает узкую подзадачу. Все fetch- и gap-агенты — `sub: deepdive-fetcher` (модель `haiku`, effort `medium`, оба из frontmatter агента; в вызове `Agent` их не передавать). Отклонение от дефолта — по типу подзадачи:

| Тип подзадачи sub-agent'а | Сигналы | Исполнитель | Model / Effort |
|---|---|---|---|
| Web search + extract metadata (URL/title/date/snippet) | primary channel = `web-general`, `news-current`, `forum-discussion` | `sub: deepdive-fetcher` | haiku / medium |
| Read long source + extract pinned quotes | подзадача требует чтения 5-10 длинных страниц | `sub: deepdive-fetcher` | haiku / medium (окно 1M) |
| Academic paper search + abstracts | primary channel = `academic`, `preprint-servers` | `sub: deepdive-fetcher` | haiku / medium |
| API-direct request + parse JSON | primary channel = `api-direct` (FRED, World Bank, etc.) | `sub: deepdive-fetcher` | haiku / medium |
| Gap-волна (точечный поиск под claim) | status ≠ triangulated в `claims.csv` | `sub: deepdive-fetcher` | haiku / medium |
| Code analysis (clone + grep + understand) | primary channel = `code-github` + impl-question | `sub: deepdive-fetcher` собирает факты и пути; выводы о причинах — `main` | haiku / medium |
| Scraping site с pagination/state | primary channel = `competitive-signals` + scraping | `sub: deepdive-fetcher`; при провале — `sub: general-purpose` с `model: "sonnet"`, `effort: "high"` и инструкцией fetcher'а в брифе (Haiku слабее в агентных задачах, см. NOTES.md) | haiku / medium |
| Heavy reasoning sub-task (rare) | подвопрос «оцени trade-offs между X и Y», не просто факт-сбор | `main` | — |

**Default для sub-agent** если не уверен → `sub: deepdive-fetcher` (haiku / medium).

> **Качество Haiku 5.5 на fetch не измерено.** Выбор Haiku опирается на цены и NOTES.md, а не на замер по этому скиллу. Проверка — на первом реальном прогоне: доля дословных цитат, прошедших `check_number_provenance` и verify-ось faithfulness. Если доля заметно ниже, чем у Sonnet на той же подтеме, менять `model` во frontmatter `deepdive-fetcher`, а не передавать `sonnet` в каждом вызове.

**Скоринг встроен.** Каждый fetch sub-agent сам скорит источник тем же вызовом (читает → проставляет credibility/recency/bias → пишет `sources/NN.md` в свой диапазон номеров; fetch-агенту нужен `Write`, поэтому `sub: deepdive-fetcher`, а не `explore-haiku` — см. `subagents_v2.md`). Отдельного scoring pass нет.

---

## Cost economics

Цены на модели меняются быстрее, чем этот файл переписывается — проверяй актуальное через
скилл `claude-api` (он автосинкается), не по памяти. Срез цен датирован в `NOTES_dated.md`:

| Модель | Model ID | Алиас в `Agent` | Input $/1M | Output $/1M | Контекст | Ratio vs Haiku |
|---|---|---|---|---|---|---|
| Haiku 5.5 | `claude-haiku-5-5` | `haiku` | $0.10 (≤100k промпта; выше $0.50) | $0.50 (≤100k; выше $2.50) | 1M | 1× |
| Sonnet 5.5 | `claude-sonnet-5-5` | `sonnet` | $2.00 | $10.00 | 1M | 20× |
| Opus 5.5 | `claude-opus-5-5` | `opus` | $4.00 | $20.00 | 1M | 40× |
| Opus 5 | `claude-opus-5` | — (только явным ID) | $5.00 | $25.00 | 1M | 50× |
| Fable 5.1 | `claude-fable-5-1` | `fable` | $10.00 | $50.00 | 1M | 100× номинально, **эффективно меньше** |

Ratio считан от Haiku 5.5 по ставке ≤100k промпта (цены — NOTES.md). Haiku 5.5: effort принимает (дефолт `medium`), 128K выхода, токенайзер даёт ~+30% токенов к 4.5; точные характеристики — NOTES.md.

**Главный сдвиг: Haiku 5.5 в десятки раз дешевле Opus.** Держать Opus на Phase 1/Phase 6 — всё равно копейки на фоне поиска; экономить нужно на fan-out (N sub-agents в Phase 4), не на этих фазах.

**Fable 5.1: номинальная ставка завышает цену.** Кэш-чтение $0.25/MTok (−75% против Fable 5) даёт ~25% экономии на типовых нагрузках и до 45% на агентных — там, где кэш переиспользуется. Множитель в таблице считать по номиналу нельзя. При этом на суб-агентов это не влияет: Fable в них всё равно не пускаем, а `subagentPromptCacheTtl: 1h` в settings.json работает на всех.

**Effort в матрице ниже читать как желаемую глубину, а не как политику сессии.** Политика (`CLAUDE.md` § Модели; дата — `NOTES_dated.md`): дефолт `medium`, `xhigh` только на необратимом. Клетки `high`/`xhigh` в матрице оправданы там, где ошибка фазы переезжает на весь ресёрч (Phase 1 reframing, Phase 6 red-team) — это ровно класс «необратимое внутри задачи». Остальные клетки при сомнении опускать, а не поднимать.

**Окно больше не повод для Sonnet.** У Haiku 5.5 контекст 1M, как у остальных (NOTES.md), поэтому подзадача «прочитать 5-10 длинных страниц» остаётся у `sub: deepdive-fetcher`. Sonnet — только там, где Haiku не тянет по качеству (агентный код, многокритериальные гейты).

**Fable 5.1 главным оркестратором не ставить.** Только по явному запросу пользователя и только на многодневные прогоны; в deepdive его цена не окупается ни на одной фазе.

## Effort: чем управляем, а чем нет

С Claude Code v2.1.292 `Agent` tool принимает **`model` и `effort`**. Управляемые рычаги:

- **главный поток** — `/effort` в сессии (`low`/`medium`/`high`/`xhigh`/`max`);
- **суб-агенты `deepdive-*` и `explore-haiku`** — модель и effort во frontmatter файла агента; колонка Effort матрицы для них повторяет frontmatter, вызовом не передаётся. Расходятся — правь frontmatter, не вызов;
- **встроенные суб-агенты** (`general-purpose`) — `model` + `effort` per-call; без них наследуют модель и effort сессии;
- **`Workflow`-скрипты** — `agent()` с `opts.effort`, как и раньше.

Уровни `xhigh` и `max` появились после первой редакции этого файла. `xhigh` — рабочий максимум для кодинга и агентных задач; `max` прожорлив и склонен к overthinking. Для deepdive: `xhigh` — только на фазе, где замер показал выигрыш (Opus 5.5 на xhigh думает заметно дольше Opus 5), `max` — не уместен нигде (ресёрч упирается в качество источников, не в глубину рассуждения одной модели).

**Иллюстрация (deep, ~5 sub-agents):** цифры прежней редакции (Haiku 4.5 $1/$5) устарели и не пересчитаны; Phase 4 на 5×`deepdive-fetcher` (Haiku 5.5) стоит копейки против Opus (цены — NOTES.md). Правило архитектурное (узкая задача = дешёвая модель, Phase 1/6 не экономить), не ценовое.

(Проверяй актуальные цены.)

---

## Как передать модель в `Agent`-tool

Агенты deepdive берут модель и effort из своего frontmatter, вызов называет только тип:

```
Agent({
  subagent_type: "deepdive-fetcher",   // haiku / medium из frontmatter; fetch+save нужен Write
  description: "...",
  prompt: "..."
})
```

Встроенному типу модель и effort передаются явно (пример — эскалация fetch после отказа или провала Haiku):

```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  effort: "high",
  description: "...",
  prompt: "... формат и правила — прочитай ~/.claude/agents/deepdive-fetcher.md ..."
})
```

Встроенный тип без `model` наследует модель главной (сейчас Opus 5.5); забытый параметр `model` = дорогой вызов.

---

## Как сообщать пользователю

В начале medium/deep ресёрча, после Phase 3 (plan готов), один раз:

```
Запускаю medium ресёрч. Routing:
- Phase 1, 3, 6 (synthesis): main (Opus)
- Phase 6 red team: deepdive-redteam (Opus/high)
- Phase 4: 4 deepdive-fetcher (Haiku/medium)
- Phase 3.5, 5, 5.5, 6.5: explore-haiku

Estimated cost: ~$2 (vs ~$8 если бы всё на Opus)
```

Это не маркетинг — это **прозрачность**, у пользователя должна быть возможность сказать «нет, мне нужно качество, гони всё на Opus».

---

## Override-механика

Пользователь может явно перебить:

```
> deepdive X with all on opus
```

Тогда router игнорируется, и **все** фазы и sub-agents идут на Opus. Цена выше, для high-stakes решений ОК.

Аналогично:
- `... with cheap mode` → всё на Haiku где возможно, Sonnet только на Phase 1/6
- `... with default routing` (или ничего) → matrix выше

---

## Anti-patterns

**❌ Запускать Phase 6 adversarial на Haiku.** Adversarial — это критическое мышление. Haiku тут будет soft-pushback'ом без реальной атаки на гипотезы. Только `sub: deepdive-redteam` (Opus/high).

**❌ Запускать 5 параллельных sub-agents все на Opus.** Это умножение цены на 5 без оправдания. Sub-agents с узкой задачей — `deepdive-fetcher` (Haiku).

**❌ Поднимать fetch-агентов Phase 4.1 на Opus «для качества».** Дело не только в цене. Способность модели ортогональна её «просоциальности» в многоагентной конфигурации (Anthropic Frontier Red Team, 13.08.2026): более сильная модель не координируется лучше — она увереннее и быстрее делает по-своему. У fetch-агента есть `Write` и изолированный контекст, то есть право действовать без надзора; на сильной модели растёт не качество поиска, а цена ошибки — увереннее выбранная не та трактовка подтемы, увереннее проставленный `root`, увереннее отброшенный источник. Границы (диапазон id, зафиксированный dispatch, обязательные поля) держат качество лучше, чем класс модели.

**❌ Считать `xhigh`/`max` бесплатным улучшением.** Выше effort — длиннее траектория и больше склонность к overthinking. На Phase 4 это прямо вредно: агенту нужно собрать источники по зафиксированной стратегии, а не переизобрести её.

**❌ Не сообщать пользователю про routing.** Прозрачность экономии — это **фича**, не пасхалка. Один раз вначале сказать какой routing и estimated cost.

**❌ Игнорировать override.** Если пользователь сказал «всё на Opus» — слушайся, не «оптимизируй за спиной».

**❌ Hardcoded routing «всегда одна модель везде».** Это потеря преимуществ Haiku на простой работе и Opus на критической.
