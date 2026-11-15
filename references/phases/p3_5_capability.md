## Фаза 3.5. Capability Discovery

**Model:** `sonnet` / `low`. Механический проход по env vars и таблицам.

**Опциональна** для shallow. **Рекомендуется** для medium. **Обязательна** для deep.

Между планированием и запуском поиска — sanity check: что у нас реально доступно?

См. `capability_discovery.md` для детального workflow. Краткая version:

### Step 1: Audit env vars

Проверь существование env vars для API ключей запланированных в plan.md секции 12:

```
$FRED_API_KEY, $GITHUB_TOKEN, $NEWSAPI_KEY, ...
```

Полный список — `capability_discovery.md` секция "Step 1".

### Step 2: Map subtopics to capabilities

Для каждой подтемы → таблица: planned source × status (`authenticated` / `open-no-auth` / `fallback` / `unavailable`).

### Step 3: Discover unknown gaps

Если планы покрывают не всю тему — fall back на `awesome_lists_registry.md` для discovery:

```
для подтемы X:
  если не нашёл в моём каталоге → найти upstream awesome-list
  → WebFetch его README
  → identify 1-3 candidates → add as ad-hoc в plan.md
```

### Step 4: Report to user

Сводный отчёт:
- ✅ Available: [list]
- ⚠ Fallback: [list]
- ❌ Unavailable: [list]
- ❓ Ad-hoc from upstream: [list]
- Suggest env vars: [list]

User confirms continue.

### Step 5: Update plan.md

Дополнить `plan.md` секцию 12 (Information sourcing strategy) per-subtopic блоком "Capabilities check":

```markdown
**Capabilities check (Phase 3.5):**
- ✅ FRED API: authenticated, will use directly
- ⚠ Brave Search: no key → fallback to standard WebSearch
- ❓ Niche topic — using ad-hoc API from public-apis registry
```
