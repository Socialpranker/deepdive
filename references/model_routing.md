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
| **Phase 4.1** | Launch sub-agents (web search, simple lookups) | **Haiku** | low | Sub-agents с узкой задачей и JSON output. Дёшево × N агентов |
| **Phase 4.1** | Launch sub-agents (чтение длинных источников, извлечение цитат) | **Sonnet** | low | Когда нужен длинный контекст под цитаты |
| **Phase 4.1** | Launch sub-agents (api-direct: curl + jq + parse) | **Haiku** | low | Bash работа + механический парсинг JSON |
| **Phase 4.1** | Launch sub-agents (анализ кода в репозитории) | **Sonnet** | medium | Code understanding требует средней модели |
| **Phase 4.2** | Fetch + dedup (главный поток) | **Sonnet** | medium | Управляет sub-agents, агрегирует результаты |
| **Phase 4.3** | Save sources to files | **Haiku** | low | Механическая запись по шаблону |
| **Phase 5** | Scoring (credibility/recency/bias по rubric) | **Haiku** | low | Простой паттерн оценки. Sonnet излишен |
| **Phase 5** | Triangulation check (3 источника на claim) | **Sonnet** | medium | Понимание содержания, не только URL |
| **Phase 6** | Multi-angle red team — N враждебных ролей как суб-агенты | **Opus** | high | **Самая дорогая модель здесь обязательна.** Атака на гипотезы (Skeptic/Contrarian/Gap-hunter) требует настоящего рассуждения, не паттерн-матчинга. Medium → sonnet/high |
| **Phase 7** | Synthesis — сборка отчёта из блоков | **Sonnet** | high | Длинный контекст всех источников + блоков + плана. Sonnet/high лучше чем Opus/medium здесь |
| **Phase 7** | Final report write-up (язык, стиль, чистка) | **Sonnet** | medium | Качественное письмо |

Phase 6 red-team суб-агенты: deep → opus/high; medium → sonnet/high; shallow → R1 инлайн (sonnet/high, без суб-агента). Synthesis/chairman → sonnet/high. Cost: +3 суб-агента на deep-отчёт (≈ дёшево относительно поиска).

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

---

## Cost economics

Опираясь на pricing на момент написания (проверь актуальное в Anthropic Pricing):

| Модель | Input $/1M | Output $/1M | Относительная цена |
|---|---|---|---|
| Haiku | $0.80 | $4.00 | 1x |
| Sonnet | $3.00 | $15.00 | ~3.75x |
| Opus | $15.00 | $75.00 | ~18.75x |

**Иллюстрация для deep ресёрча (~5 sub-agents):**

Если всё на Opus: 5 × ~50k input + 5 × ~10k output = 250k input + 50k output = **$7.50** только на Phase 4.

То же на правильном routing:
- Phase 1 (reframing) Opus/high: 5k in + 2k out = **$0.23**
- Phase 3 (plan) Opus/medium: 8k in + 3k out = **$0.35**
- Phase 4 (5 sub-agents Haiku/low): 5 × (15k in + 3k out) = **$0.12**
- Phase 6 (adversarial) Opus/high: 30k in + 5k out = **$0.83**
- Phase 7 (synthesis) Sonnet/high: 60k in + 15k out = **$0.40**

**Total ~$1.93** против $7.50 — **в 4× дешевле**, а на критичных фазах (Phase 1, 6) даже **качество выше** потому что Opus/high действительно нужен.

(Цифры приблизительные — суть в порядке величин, не точных значениях.)

---

## Как передать модель в `Agent`-tool

В Claude Code SDK `Agent` принимает параметр `model`:

```
Agent({
  subagent_type: "Explore",
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

**❌ Не сообщать пользователю про routing.** Прозрачность экономии — это **фича**, не пасхалка. Один раз вначале сказать какой routing и estimated cost.

**❌ Игнорировать override.** Если пользователь сказал «всё на Opus» — слушайся, не «оптимизируй за спиной».

**❌ Hardcoded routing «всегда Sonnet везде».** Это потеря преимуществ Haiku на простой работе и Opus на критической.
