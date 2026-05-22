# Refresh Protocol — как делать дельта-ресёрч

**Когда используется:** пользователь вызывает `update <slug>` или «обнови ресёрч про X». Скилл **не повторяет весь ресёрч** — он находит **только что изменилось** с последнего раза и пишет diff-файл.

**Зачем:** полный re-research дорогой, медленный и теряет историю. Дельта-подход:
- Новые игроки в индустрии → добавить в landscape (M2)
- Свежие данные по фактам/цифрам → перепроверить N-блоки
- Новые публикации → проверить не опровергают ли H1-H3
- Старые тезисы что **не изменились** → сохранить как `verified: still valid`

---

## Принципы

1. **Дельта, не replay.** Не запускать Phase 4 с нуля. Только targeted поиск с date filters от `last_research_date`.
2. **Источник истины — `refresh_targets.md`.** Этот файл генерируется в Phase 7 предыдущего ресёрча. Он говорит «вот что важно отслеживать в этом домене».
3. **Output — diff-файл, не новый отчёт.** Старый отчёт остаётся. `diffs/<YYYY-MM-DD>_delta.md` — компактный список изменений.
4. **Verified-как-найденное.** Если перепроверили факт и он не изменился — это **результат**, а не пустота. Зафиксировать «still valid».
5. **Adversarial trigger.** Новая публикация которая опровергает гипотезу — это сигнал «нужно перезапустить Phase 6 на обновлённом контексте», не молчаливо проигнорировать.

---

## Когда запускать update

**Триггеры:**
- Пользователь явно сказал «обнови ресёрч про X»
- Прошло >3 месяцев с `last_research_date` и пользователь снова интересуется темой → предложить
- В чате упомянуто событие из домена ресёрча («Polymarket подняла раунд» — а ресёрч про prediction markets) → предложить

**НЕ запускать update:**
- Без явного запроса пользователя или подтверждения предложения
- Если `last_research_date` < 30 дней (вряд ли что-то существенное изменилось)
- На shallow-ресёрче (там нечего обновлять — старый дешевле перезапустить полностью)

---

## Pre-flight check

Перед началом update:

```
1. Read research/<slug>/plan.md
   ├── last_research_date (из секции 0 HEADER)
   ├── гипотезы H1-H4 (секция 9)
   └── подвопросы/подтемы (секция 11)

2. Read research/<slug>/refresh_targets.md
   ├── companies/entities to re-check
   ├── numbers/series to re-verify
   ├── new-publication watch terms
   └── new-entrant search patterns

3. Read research/<slug>/<last>_<genre>.md final report
   └── Понять что было сказано — чтобы видеть что изменилось
```

Если `refresh_targets.md` нет (старый ресёрч до этого протокола) — **сгенерируй его в процессе** на основе чтения final report + plan.md. Это первый шаг update.

---

## 4 категории дельты (что искать)

### 1. Новые игроки (new entrants)

**Триггер:** ресёрч имеет landscape-блок (M2 profiles, M5 market map) или хоть один subquestion вида «кто игроки в X».

**Что искать:**
- **Crunchbase** (если есть `CRUNCHBASE_API_KEY`): запросы по category-tags из refresh_targets с `founded_after: <last_research_date>` и `total_funding > $1M` (фильтр от шума)
- **GitHub topics** (из `topic:<keyword>` в refresh_targets): репозитории `created:>YYYY-MM-DD` с `stars>50`
- **HuggingFace datasets/models** (если ML-тема): `sort=Recent` с фильтром даты
- **News** через GDELT или NewsAPI: запросы «launched», «out of stealth», «raised seed», в комбо с industry keyword
- **Industry-specific** registries из refresh_targets (например, BloombergNEF для energy)

**Output формат:**
```markdown
## New entrants since 2026-05-22

### Company X — Seed $5M (2026-07-15)
- Source: Crunchbase + TC article
- Category: <same category as existing players in M2>
- Why it matters: <fills gap of existing players / direct competitor>
- Update target: add to landscape M2 profile

### Company Y — out of stealth (2026-08-01)
- Source: company blog + HN thread (s12)
- Why it matters: alternative approach to <H2 thesis>
- Update target: profile + reconsider H2 in adversarial
```

### 2. Изменения у конкретных компаний (entity diff)

**Триггер:** в refresh_targets перечислены конкретные компании которые надо отслеживать.

**Что отслеживать:**
- **Pricing page** — сравнить с тем что было (если есть archive в `sources/`)
- **Job postings** — `/careers` страница, рост хедкаунта = сигнал направления
- **Leadership** — Crunchbase или LinkedIn (если доступ есть) на смену CEO/CTO
- **Product pages** — новые фичи появились?
- **Funding** — Crunchbase api: новый раунд?
- **Press releases** — компания blog + Google News с `site:<company>.com`

**Тактика fingerprinting:**
1. **WebFetch** на page → hash content (markdown-only, без CSS/JS)
2. Сравнить hash с тем что было в `sources/SN_<company>_<page>.md` (если есть)
3. Если изменился → сохранить новую версию рядом, написать diff в delta файл
4. Если не изменился → пометить `verified-no-change: <today>` в old source

**Output формат:**
```markdown
## Entity diff: Company X

### Pricing page (changed 2026-07-15)
- Was: Starter $29/mo, Pro $99/mo (snapshot in s05)
- Now: Starter $39/mo (+34%), Pro $129/mo (+30%), new "Enterprise" tier
- Implication: shift upmarket — supports adversarial counter-arg CA2

### Careers page (no change since 2026-04)
- 12 open roles, mostly Eng (was 11)
- Verified-no-change confirms hiring pace stable
```

### 3. Свежесть фактов и цифр (numbers refresh)

**Триггер:** ресёрч содержит numerical claims из N-блоков (N1 metrics, N3 market sizing, N5 forecasts).

**Что перепроверять:**
- **FRED series IDs** из refresh_targets — пересчитать `latest_value`, `YoY change`, отметить если изменилась тенденция
- **World Bank indicators** по country codes — то же самое
- **Industry estimates** (если фиксировался диапазон с named источниками) — Statista alt, IBISWorld:
  - Поиск той же фразы что в orig source
  - Сравнить число; если разошлось на >20% — высокий interest delta
- **Pricing / unit economics** компаний — см. категорию 2

**Output формат:**
```markdown
## Numbers refresh

### FRED CPIAUCSL
- Was: 312.5 (2026-04, anchor in original)
- Now: 314.2 (2026-08)
- Change: +0.5% over 4mo (~1.5% annualized — slowing)
- Implication: macro assumption «inflation moderating» still valid

### Industry market size estimate
- Was: $5.0B (Statista 2026 estimate, anchor for N3 block)
- Now: $6.2B (Statista 2026-Q3 update)
- Change: +24% — exceeds expected growth from N5 forecast
- Implication: revise N5 forecast in Phase 7 synthesis update
```

### 4. Новые публикации / opposition (adversarial trigger)

**Триггер:** есть гипотеза H1-H4 и периодически появляются новые статьи/посты по теме.

**Что искать:**
- **OpenAlex / Semantic Scholar** — поиск по `concepts.id:<concept>` с `publication_year:<YYYY>` (после last_research_date)
- **arXiv / bioRxiv / SSRN** — фильтр по дате, ключевые слова из refresh_targets
- **Retraction Watch** — проверить не отозвали ли цитированные источники
- **News-current** — события которые могли опровергнуть факты в ресёрче
- **Forum-discussion** — пост-мортемы, фейлы, баги в подходах которые описывал ресёрч

**Если найдено опровержение → adversarial trigger:**
```markdown
## Adversarial trigger

### New paper contradicts H2
- Title: "<paper title>"
- Authors / venue / date
- Source: arXiv 2026.12345 (2026-07-23)
- Key claim: «<verbatim quote of contradicting claim>»
- Original H2 in our report: «<our H2 verbatim>»
- Severity: HIGH — directly opposes H2 with new dataset
- Recommendation: **re-run Phase 6 adversarial pass** with this paper as input;
  may require updating verdict in original report

### Retraction alert
- Source: s07 (Smith et al. 2024) — retracted on 2026-06-15
- Reason: data fabrication (per RetractionWatch)
- Severity: MEDIUM — was supporting H1 along with 2 others
- Recommendation: H1 still supported by 2 sources; mark s07 as `retracted`,
  re-evaluate confidence label (was: high → propose: medium)
```

---

## Verified-no-change (что НЕ изменилось)

Это **тоже результат**. После прогона всех 4 категорий — финальная секция:

```markdown
## Verified (still valid, no change)

### H1: «X scales linearly with Y»
- Re-checked 3 original supporting sources: all still accessible, no contradicting recent publications
- Verdict: H1 confidence remains «high»

### Regulatory landscape (X4 block)
- EUR-Lex Regulation 2015/2283: no amendments since last research
- Per-country status: re-checked Germany, Italy — no changes

### Market structure (M5 block)
- Top 5 players still same; market shares roughly stable per Statista 2026-Q3
```

Без этого секции пользователь думает «может пропустили?» — а тут явное «нет, проверено, всё то же».

---

## Output: структура delta-файла

`research/<slug>/diffs/<YYYY-MM-DD>_delta.md`:

```markdown
---
slug: <slug>
update_date: <YYYY-MM-DD>
previous_research_date: <YYYY-MM-DD>
parent_report: <YYYY-MM-DD_genre.md>
refresh_targets_version: <YYYY-MM-DD>
trigger: <"manual" | "scheduled" | "<user-request-text>">
severity: <HIGH | MEDIUM | LOW>  # max severity among findings
---

# Delta: <topic> · <YYYY-MM-DD> vs <previous date>

## Summary (3-5 bullets)
- <main finding 1>
- <main finding 2>
- ...

## 1. New entrants since <date>
<либо список найденных, либо «None found in <X> sources checked»>

## 2. Entity diff
<per-company changes, или «No changes detected in <N> tracked entities»>

## 3. Numbers refresh
<per-metric changes>

## 4. Adversarial trigger
<new opposition, retractions, или «No opposing publications found»>

## 5. Verified (still valid)
<what was re-checked and stayed the same>

## Recommended actions
- [ ] Update M2 profile to include <new company>
- [ ] Re-run Phase 6 adversarial with <new paper> as input
- [ ] Revise N5 forecast given +24% revision in market size estimate
- [ ] (etc.)

## Sources added in this delta
- <list of new sources/SN_*.md files added with this update>

## Cost
- Model routing: Haiku/Sonnet for fetch, Opus only if Phase 6 re-run triggered
- Estimated: ~$0.40 (vs full re-research ~$2.00)
```

---

## Что **НЕ** делать

**❌ Не делать полный Phase 4 заново.** Это update, не replay.

**❌ Не игнорировать adversarial trigger.** Если нашёл опровержение — fix в Phase 6 update, не оставляй в delta-файле как notice.

**❌ Не пропускать «verified» секцию.** Что не изменилось — это тоже сигнал, его надо явно зафиксировать.

**❌ Не перезаписывать старый отчёт.** Старый `<YYYY-MM-DD>_<genre>.md` остаётся. Delta — отдельный файл. Если изменения существенны → может появиться **новый** `<YYYY-MM-DD>_<genre>.md` рядом (update-режим из SKILL.md) — но это решение пользователя после прочтения delta.

**❌ Не запускать update без refresh_targets.md.** Если файла нет (старый ресёрч до протокола) — сначала сгенерируй его, потом действуй.

**❌ Не делать update на shallow.** Shallow ресёрч — это <8 источников, дешевле повторить полностью. Update имеет смысл от medium и выше.

---

## Model routing для update

| Шаг update | Модель | Effort |
|---|---|---|
| Pre-flight (чтение plan.md + refresh_targets.md + last report) | `sonnet` | low |
| Generate refresh_targets.md (если отсутствует) | `sonnet` | medium |
| 1. New entrants search (sub-agents) | `haiku` | low (web/news/Crunchbase) |
| 2. Entity diff (fetch + compare) | `haiku` | low (fingerprinting механический) |
| 3. Numbers refresh (api-direct) | `haiku` | low (FRED/WB/etc) |
| 4. Adversarial trigger search | `sonnet` | low (academic) |
| Synthesis delta file | `sonnet` | medium |
| **If adversarial trigger HIGH → re-run Phase 6 partial** | `opus` | high (только эта часть) |

**Total estimated cost для типового update без adversarial re-run: ~$0.40** (vs ~$2 за полный medium ресёрч).

---

## Что должно быть в `refresh_targets.md` (отдельный файл рядом с plan.md)

Этот файл генерируется автоматически в Phase 7 первоначального ресёрча. Шаблон — в `blocks/close.md` (блок Z11). Содержит:

1. **Entities to track** — конкретные компании/продукты/проекты (с URL `/pricing`, `/careers`, `/blog`)
2. **Numbers to refresh** — конкретные FRED series IDs, WB indicators, industry estimate references
3. **Topic markers** — `topic:<keyword>` для GitHub, академические концепты OpenAlex, news keywords
4. **Hypotheses to re-test** — H1-H4 из оригинального ресёрча, как формулировки для поиска опровержений
5. **Update cadence suggestion** — «monthly / quarterly / event-driven»

Без этого файла update не работает оптимально — приходится re-discover targets каждый раз.
