# Capability Discovery — Phase 3.5

Фаза между Plan (3) и Search (4). Опциональная для shallow, **рекомендуется** для medium, **обязательна** для deep.

## Зачем фаза существует

После того как plan.md написан с Information sourcing strategy (секция 12), скилл знает:
- Какие channels будут использоваться
- Какие stat sources и API endpoints запланированы

**Но не знает:**
- Какие API keys реально доступны в окружении (env vars)
- Какие APIs живы / deprecated / rate-limited прямо сейчас
- Покрывают ли запланированные источники все нужные подтемы

Capability Discovery закрывает этот gap. **Прозрачность для пользователя:** что используется, что пропускается, что бы стоило настроить.

## Workflow фазы

### Step 1: Audit env vars

Скилл проверяет существование env vars для API ключей запланированных API:

```bash
# Check known env vars
if env $FRED_API_KEY exists → mark FRED as 'authenticated'
if env $GITHUB_TOKEN exists → mark GitHub as 'authenticated'
if env $BRAVE_API_KEY exists → mark Brave as 'authenticated'
# ...
```

Поддерживаемые env vars (см. полный список в `api_sources/README.md`):

| Env var | API | Required? |
|---|---|---|
| `FRED_API_KEY` | FRED economic data | optional (HTML fallback есть) |
| `GITHUB_TOKEN` | GitHub Search | optional (60/h без, 5000/h с) |
| `BRAVE_API_KEY` | Brave Search | **не используется** — скилл ходит через WebSearch харнесса |
| `TAVILY_API_KEY` | Tavily | **не используется** — оставлено для внешних раннеров |
| `EXA_API_KEY` | Exa.ai | **не используется** — оставлено для внешних раннеров |
| `SERPAPI_KEY` | SerpAPI | **не используется** — оставлено для внешних раннеров |
| `NEWSAPI_KEY` | NewsAPI | для news |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | для stock prices |
| `CRUNCHBASE_API_KEY` | Crunchbase | для company data |
| `OPENWEATHER_KEY` | OpenWeather | для weather |
| `ETHERSCAN_KEY` | Etherscan | для on-chain |
| `STACKEXCHANGE_KEY` | Stack Exchange | для programming Q&A |
| `CENSUS_API_KEY` | US Census | для US demographics |
| `COMPANIES_HOUSE_API_KEY` | Companies House UK | для UK registry |
| `NCBI_API_KEY` | PubMed | optional (повышает rate limit) |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | optional |
| `DUNE_API_KEY` | Dune Analytics | для custom on-chain SQL |
| `NASA_API_KEY` | NASA APIs | (DEMO_KEY работает) |

### Step 2: Map subtopics to capabilities

Для каждой подтемы из plan.md → таблица capabilities:

```markdown
### ST1: <название подтемы>

| Planned source | Status | Notes |
|---|---|---|
| FRED API (macro context) | ✅ authenticated | $FRED_API_KEY есть |
| Semantic Scholar (academic) | ✅ open-no-auth | работает без ключа |
| Brave Search (search) | ⚠ fallback | $BRAVE_API_KEY нет → standard WebSearch |
| Crunchbase (companies) | ❌ unavailable | paid, нет ключа → competitive-signals HTML |
| Industry-specific (X) | ❓ to discover | искать в upstream awesome-lists |
```

### Step 3: Discovery for unknown gaps

Если запланированная подтема не покрывается известными источниками — скилл идёт в **awesome_lists_registry.md** и ищет purpose-fit upstream.

Алгоритм:
1. Извлечь keywords из подтемы (e.g., "fashion industry market data")
2. Перечислить релевантные awesome-lists из registry (например, `public-apis`, `awesome-public-datasets`)
3. WebFetch на их README.md или специфичной категории
4. Найти 1-3 candidate APIs/datasets
5. Извлечь base URL и docs URL
6. Добавить в plan.md как `ad-hoc:` источники (не сохраняются в каталог автоматически)

Пример:

```markdown
ST3: fashion industry market sizing

Не нашёл fit в моём каталоге → searched upstream:
- public-apis/Books → нет
- public-apis/Business → Lyst API (limited docs), ShopStyle Collective
- awesome-public-datasets/Economics → нет специфики fashion

Choose: Lyst API (для market activity), Vogue Business RSS (для trend signals)
Mark as ad-hoc, not in catalog — contributor может добавить в `api_sources/fashion/` через PR.
```

### Step 4: Report to user

Финальная output фазы 3.5 — компактный сводный отчёт пользователю:

```
Capability Discovery complete:

✅ Available (with auth):
  FRED, GitHub, Semantic Scholar, OpenAlex, DefiLlama, Reddit JSON, PubMed, ClinicalTrials.gov

⚠ Fallback to HTML (no key):
  Brave Search → standard WebSearch
  Crunchbase → competitive-signals (LinkedIn/Glassdoor scraping)

❌ Not available:
  Tavily, Exa, Alpha Vantage — paid only

❓ Ad-hoc (from upstream awesome-lists):
  Lyst API, Vogue Business RSS — для fashion industry subtopic

To improve coverage next time, configure these env vars:
  export ALPHA_VANTAGE_KEY=... (25 free/day)

Continue with current capabilities? [Y/n]
```

User может:
- Согласиться → переход к Search (Phase 4)
- Отказаться → пауза для настройки ключей → re-run discovery
- Указать дополнительные источники вручную

## Когда фаза опциональна / обязательна

| Depth | Phase 3.5 | Notes |
|---|---|---|
| shallow | optional | если простая тема, agent сам fall back |
| medium | recommended | значимое повышение прозрачности |
| deep | mandatory | без discovery риск пропустить ключевые источники |

## Output фазы

Capability Discovery дополняет `plan.md` секцию 12 (Information sourcing strategy) новым sub-блоком per subtopic:

```markdown
## 12. Information sourcing strategy

### ST1: <subtopic>

**Channels:** web-general, academic, api-direct
**Stat sources:** core/gov_macro.md, core/science.md

**Capabilities check (Phase 3.5):**
- ✅ FRED API: authenticated, will use directly
- ✅ Semantic Scholar API: open access, will use directly
- ⚠ Brave Search: no key → fallback to standard WebSearch
- ❓ Niche topic — searching upstream...

**Decision:** proceed with available; ad-hoc add Lyst API for ST3.
```

## Антипаттерны

- ❌ Запрашивать API ключи у пользователя inline — попросить добавить в env и перезапустить
- ❌ Сохранять чужие keys в файлы каталога
- ❌ Использовать paid API без проверки на доступность ключа
- ❌ Использовать ad-hoc upstream APIs как single source (нужна триангуляция как обычно)
- ❌ Делать фазу 3.5 в shallow режиме когда тема простая — overkill

## Связь с другими фазами

- **Фаза 3 (Plan):** задаёт plan.md → секцию 12 sourcing strategy
- **Фаза 3.5 (Capability Discovery):** дополняет секцию 12 capabilities check
- **Фаза 4 (Search):** использует только confirmed capabilities + ad-hoc upstream finds
- **Фаза 5 (Score):** `sources/NN.md` фиксирует `access:` поле с реальным методом (api-direct / html-fallback / ad-hoc-upstream)

## Чек-лист фазы 3.5

- [ ] Env vars проверены для всех planned APIs
- [ ] Status каждой APIs зафиксирован (authenticated / fallback / unavailable)
- [ ] Gaps в каталоге выявлены — discovery через upstream awesome-lists проведён
- [ ] Сводный отчёт показан пользователю
- [ ] Plan.md секция 12 дополнена Capabilities check блоком
- [ ] User confirmation получен (или явное согласие "продолжай")
