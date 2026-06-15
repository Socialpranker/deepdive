# Phase 3.5 — Capability Discovery (design)

**Дата:** 2026-06-15
**Статус:** дизайн утверждён, реализация не начата
**Фаза:** Phase 3.5 по нумерации README (Capability Discovery), между Phase 3 (Plan)
и Phase 4 (Search).

## Проблема

`Orchestrator.run()` ([runner/orchestrator.py](../../../runner/orchestrator.py))
после реализации Phase 5 гонит фазы 1→2→3→4→5→6. Phase 3.5 не вызывается.

План (`plan.md`) указывает, какие API/каналы планируется использовать, но не
знает, доступны ли ключи к ним. Capability Discovery закрывает этот разрыв:
аудит env-ключей + связывание подтем с реально доступными источниками, с
прозрачной записью в `plan.md`.

## Решения (резолв развилок брейншторма)

1. **Объём — шаги 1+2 из 4 спеки.** Реализуем: (1) детерминированный аудит
   18 env-ключей, (2) LLM-маппинг подтем→источники в `plan.md`. НЕ реализуем
   шаг 3 (WebFetch awesome-lists для ad-hoc источников) и шаг 4 (интерактивный
   «Continue? [Y/n]») — оркестратор сейчас неинтерактивный (`run()` гонит все
   фазы подряд), Y/n сломал бы автозапуск и не тестировался бы в CI; WebFetch
   awesome-lists — отдельная живая сетевая зависимость, вне текущей стадии.
2. **Аудит — чистая функция в отдельном модуле.** `runner/capabilities.py`,
   `audit_env(env: dict)` принимает env ЯВНО (не читает `os.environ` внутри) →
   тестируется инъекцией fake-словаря, без monkeypatch. Повторяет паттерн
   `runner/scoring.py` / `runner/adaptive.py` (чистая логика отдельно от сети).
3. **Маппинг — живой LLM (sonnet/mid).** Согласуется с `model_routing.md`
   (Phase 3.5 = Sonnet/low) и с тем, как сделана Phase 5 (сразу живой вызов).
   Свободный текст через `self.p.complete(...)`, НЕ structured JSON — для
   дописывания в `plan.md` схема избыточна (YAGNI; помним урок Phase 5 —
   каждая JSON-схема = риск structured-output-бага + новый guard-тест).
4. **Гейт по depth.** `if s.depth != "shallow"` в `run()`. На medium+deep фаза
   идёт, на shallow пропускается (по спеке: shallow — optional). Это первый
   depth-гейт фазы в оркестраторе (раньше depth влиял только на числа
   DEPTH_SOURCES/DEPTH_FANOUT).

## Архитектура

Новый метод `Orchestrator.discover_capabilities(s: RunState) -> None`,
вызывается в `run()` между `plan()` и `search()` за гейтом:

```python
self.plan(s)                          # Phase 3
if s.depth != "shallow":
    self.discover_capabilities(s)     # Phase 3.5 (gate: medium+deep)
self.search(s)                        # Phase 4
```

### Новый модуль `runner/capabilities.py` (чистая логика, без сети)

```python
KNOWN_KEYS: tuple[str, ...]   # 18 имён env-ключей из спеки — источник истины в коде

def audit_env(env: dict) -> list[dict]:
    """Для каждого known key — присутствует ли он в env (непустое значение).
    Принимает env явно (тестируется инъекцией). Не кидает исключений."""
    # -> [{"key": "FRED_API_KEY", "present": True}, ...]  (все 18)

def render_capabilities(audit: list[dict], mapping_text: str) -> str:
    """Собирает markdown-блок 'Capabilities check (Phase 3.5)' для append в plan.md."""
```

`KNOWN_KEYS` (18, из `references/capability_discovery.md`): FRED_API_KEY,
GITHUB_TOKEN, BRAVE_API_KEY, TAVILY_API_KEY, EXA_API_KEY, SERPAPI_KEY,
NEWSAPI_KEY, ALPHA_VANTAGE_KEY, CRUNCHBASE_API_KEY, OPENWEATHER_KEY,
ETHERSCAN_KEY, STACKEXCHANGE_KEY, CENSUS_API_KEY, COMPANIES_HOUSE_API_KEY,
NCBI_API_KEY, SEMANTIC_SCHOLAR_API_KEY, DUNE_API_KEY, NASA_API_KEY.

### Метод `discover_capabilities(s)` — три шага (паттерн `score()`)

1. `audit = audit_env(dict(os.environ))` — детерминированный аудит ключей.
2. `mapping = self.p.complete(prompt, model_tier="mid")` — sonnet связывает
   подтемы (из `s.question` + `s.hypotheses`) с доступными источниками, отмечая,
   где ключа нет → fallback.
3. Persist: `s.capabilities = audit`; дописать (append) блок
   `render_capabilities(audit, mapping)` в `plan.md`.

## Контракт данных

### RunState — новое поле

```python
capabilities: list[dict] = field(default_factory=list)  # Phase 3.5: env-key audit
```

Хранит результат `audit_env` (`[{"key", "present"}]`). Маппинг — текст, живёт
только в `plan.md` (он для человека, состоянию не нужен).

### Блок в plan.md (append в конец)

```markdown

## Capabilities check (Phase 3.5)

**API keys:**
- ✅ FRED_API_KEY — authenticated
- ❌ BRAVE_API_KEY — not set (fallback to standard web search)
- … (все 18: ✅ если present иначе ❌)

**Subtopic → source mapping:**
<LLM-текст из self.p.complete(...)>
```

Аудит-строки детерминированные (из `audit_env`); маппинг-абзац — от LLM.

### Промпт шага 2

Вход: `s.question`, `s.hypotheses`, список доступных (present) ключей из аудита.
Просим связать подтемы с источниками, отметив fallback где ключа нет. На
`DryRunProvider.complete()` вернётся детерминированная заглушка
(`[dryrun:mid:hash] ...`) — достаточно, чтобы блок записался и тест прошёл оффлайн.

## Обработка ошибок

- `audit_env` — чистая, падать нечем (отсутствующий ключ = `present: False`,
  не исключение).
- `discover_capabilities` полагается, что `plan()` отработал раньше (он и
  отрабатывает в `run()` — фаза идёт строго после plan). Сам основу плана не
  создаёт — только дописывает блок.
- LLM-вызов: DryRun даёт заглушку, живой — текст. Кривого ответа быть не может
  (свободный текст, не JSON).

## Тестирование (pytest)

`tests/test_capabilities.py`:
- `audit_env`: инъекция `{"FRED_API_KEY": "x"}` → FRED present=True, остальные
  present=False; все 18 ключей в выводе.
- `audit_env`: пустой env → все 18 present=False.
- `render_capabilities`: ✅/❌ рендерятся по present, маппинг-текст вставлен,
  заголовок `## Capabilities check (Phase 3.5)` есть.

`tests/test_orchestrator_capabilities.py`:
- интеграция: после `plan()` + `discover_capabilities()` — `plan.md` содержит
  блок «Capabilities check», `s.capabilities` непустой (18 записей).
- гейт: `run()` на `depth="shallow"` → блока в `plan.md` НЕТ; на `medium` → есть.

Верификация перед «готово»: `python3 -m pytest tests/ -q` + `ruff check runner/
tests/` + перечитать спеку построчно.

## Явные сужения относительно спеки (сознательные, не недоделки)

- Шаг 3 (discovery via awesome-lists + ad-hoc источники) — НЕ реализуем. Требует
  живого WebFetch и registry awesome-lists. Отдельная задача.
- Шаг 4 (отчёт + интерактивный «Continue? [Y/n]») — НЕ реализуем. Оркестратор
  неинтерактивный; вместо подтверждения пользователя просто пишем прозрачный
  блок в `plan.md`.

## Model routing (references/model_routing.md)

| Подзадача | tier | модель |
|---|---|---|
| Env-аудит | — | детерминированный Python, без LLM |
| Subtopic→source mapping | `mid` | claude-sonnet-4-6 |

## Зависимости

```
Phase 3 (plan) ── plan.md (основа) ──┐
                                     ▼
                      Phase 3.5 (discover_capabilities) ── append block + s.capabilities
                                     │ (gate: depth != shallow)
                                     ▼
                      Phase 4 (search)
```
