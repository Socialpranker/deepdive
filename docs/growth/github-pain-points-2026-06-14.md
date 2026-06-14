# GitHub pain-points research — Deep Research growth

**Дата:** 2026-06-14
**Цель:** найти живые боли юзеров (Claude-экосистема + соседние AI-research тулы), которые закрывает Deep Research, и подготовить helpful-first драфты.
**Граница:** ничего не публикуется/не подаётся без явного OK Ивана. Решено: только безопасные площадки (НЕ писать на трекере Anthropic).

---

## Главный вывод

Самый сильный сигнал спроса — **не** feature-requests «хочу research-скилл», а **волна баг-репортов на встроенный `/deep-research` от Anthropic**: люди жгут 2–3.5M токенов и получают ноль (бесконечный retry на 429, fatal abort при одном упавшем субагенте, рекурсивный fan-out, `[verified]`-теги без проверки первоисточника, потеря прогресса на Synthesize).

→ Позиционирование Deep Research: **лёгкая, прозрачная, fault-tolerant, token-дешёвая** альтернатива штатному воркфлоу.
→ Но писать саморекламу под этими баг-репортами = риск ярлыка спамера → **решено туда НЕ лезть**.

Фоновый факт для убедительности: arxiv-2026 — hallucination rate **36–61%** цитат в deep-research агентах; NousResearch документирует «~40% error rate» для AI-цитат.

---

## Верифицированные находки (после adversarial-фильтрации спама)

🟢 можно · 🟡 рискованно · 🔴 мимо

| # | Issue | Боль | Fit | Вердикт |
|---|---|---|---|---|
| 1 | anthropics/claude-code#10124 — /research slash command | гоняет ресёрч в web UI, руками копирует в репо, контекст теряется | High | 🟡 Anthropic-трекер |
| 2 | assafelovic/gpt-researcher#1572 — Hallucinates Sources | при пустом `self.context` модель выдумывает источники | High | 🟢 OSS, живой разраб, open |
| 3 | anthropics/claude-code#65500 — aborts on subagent fail | один субагент → весь run FATAL, 3.5M токенов | High | 🟡 Anthropic-трекер |
| 4 | anthropics/claude-code#66375 — `[verified]` tags fake | verified = голосование моделей по вторичке | High (методологически в точку) | 🟡 свежак, 0 комментов |
| 5 | anthropics/claude-code#65731 — rate limit kills 7/10 | ~3/10 доходят, инвертирует reliable↔unreliable | High | 🟡 |
| 6 | anthropics/claude-code#68110 — recursive agents | «research X» → 48+ агентов, дубли | Med-High | 🟡 |
| 7 | anthropics/claude-code#65729 — can't resume stalled | завис на Synthesize → прогресс потерян | High | 🟡 |

**🔴 Зарублено верификатором (НЕ трогать):**
- awesome-claude-code #1900/#1218/#1769/#1807 — resource-submissions чужих продуктов, не дискуссии; #1218 closed
- gpt-researcher#1727 — СПАМ-ПРОМО от LinkedIn-инфлюенсера (rehan243), нулевая аудитория
- gpt-researcher#939, VoltAgent#257 — closed год+ назад / отклонён
- claude-code#50647 (WebFetch) — реальный баг, но про summarizer, не про ресёрч-флоу

**Не нашли (честно):**
- Прямых «хочу deep-research скилл» feature-requests почти нет — спрос косвенный.
- Боли «обновить старый ресёрч» (refresh protocol) и «atomic findings переиспользование» никто не формулирует как issue → либо опережаешь рынок, либо не больно.
- Discussions в anthropics/claude-code через gh не вытащились (GraphQL EOF) — пласт не покрыт.

---

## ДРАФТ 1 — комментарий в gpt-researcher#1572 (🟢 safe, OSS)

**Контекст issue (проверено):** автор `y8ymfx8zqb-creator` — самостоятельный разраб, сам копает. Issue OPEN, последняя активность 16 дек 2025, **мейнтейнеры не ответили ни разу** (монолог из 6 комментов). Нашёл 3 бага:
1. пустой `self.context` → выдуманные источники (workaround: вернуть `NO_RESULTS_FOUND`)
2. `ReportGenerator.__init__` не передаёт `prompt_family` в `research_params` → кастомный PromptFamily игнорируется
3. `process_research_results` хардкодит PromptFamily вместо `self.researcher.prompt_family`

**Чего НЕ делать:** не предлагать его же workaround, не «проверь промпт» в общем виде, не хвалить впустую.
**На что опереться:** подтвердить его диагноз про prompt-side root cause + поделиться, как структурно решается «модель не должна выдумывать URL» (source-grounding: цитаты привязаны к сохранённым источникам, regex-фильтр URL по факту присутствия в контексте).

### Текст драфта (EN — репо англоязычное):

> Ran into the same class of failure and landed on the same root cause you flagged in the `PromptFamily` path — the fabrication is prompt-side, not retrieval-side. When `context` is empty the writer has no grounding and the model happily fills the gap with plausible-looking URLs (homepages + dead links mixed with real ones, which is the dangerous part — you can't eyeball which is which).
>
> Two things that worked well for me beyond the `NO_RESULTS_FOUND` guard:
>
> 1. **Post-hoc URL allowlist.** After generation, regex-extract every URL in the draft and drop any that doesn't literally appear in the retrieved context. The model can still *phrase* freely, but it can't introduce a source that wasn't actually fetched. Cheap, deterministic, catches the "invented homepage" case your screenshots show.
> 2. **Quote-first sourcing.** Instead of letting the writer cite by URL, bind each claim to a verbatim quote that was saved at fetch time. If there's no quote, there's no citation — so an empty `context` produces an empty claim, not a hallucinated one.
>
> I ended up building this discipline into a separate Claude Code research skill ([source-grounded, every claim → saved quote](https://github.com/Socialpranker/claude-deep-research)) so I'm coming at it from a different stack, but the failure mode is identical and the prompt-level fix you found generalizes. Happy to share the exact guard/regex if useful.

**Тон-чек:** коллега-разраб, не реклама. Ссылка одна, в скобках, как «откуда я это знаю». Заканчивается предложением помощи, не CTA.

**Риск:** низкий. Не Anthropic-трекер, OSS-комьюнити, тема ровно по делу. Единственный минус — issue полугодовой давности, мейнтейнеры молчат → охват скромный.

---

## ДРАФТ 2 — submission в awesome-claude-code (📥 руками, через веб-форму)

**⚠️ БЛОКЕР:** порог каталога — **5 звёзд**, у репо сейчас **4**. Бот зарубит. Сначала набрать 5-ю звезду.
**⚠️ Подать можно ТОЛЬКО руками** через https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml — gh CLI и PR запрещены явно.
**✅ Числа выверены (2026-06-14):** README прав (авто-ген через `scripts/stamp_docs.py`), GitHub-description устарел и **исправлен** на корректные. Реальные числа: **9 фаз, 103 блока, 29 каналов, 460+ stat sources, 39 API**. Расхождения больше нет.

### Поля формы (готово к копипасту):

- **Display Name:** `Deep Research`
- **Category:** `Agent Skills`
- **Sub-Category:** `General`
- **Primary Link:** `https://github.com/Socialpranker/claude-deep-research`
- **Author Name:** `Socialpranker`
- **Author Link:** `https://github.com/Socialpranker`
- **License:** `MIT`
- **Description** (1–3 предл., без emoji, не рекламно):
  > A structured meta-research skill that turns "research this topic" into a 9-phase pipeline: hypothesis framing, parallel sub-agent search across 29 curated channels, source triangulation with verbatim quotes saved to disk, and a mandatory adversarial review pass. Output is a reusable folder where every claim traces to a specific source file.
- **Validate Claims** (как проверить заявленное):
  > Clone into `~/.claude/skills/deep-research`, then invoke `/deep-research <question>`. The skill writes `plan.md` (documenting every choice), saves each source to `sources/NN.md` with verbatim quotes, requires ≥3 independent sources per thesis, and runs an adversarial pass with counter-arguments before producing the final report. All artifacts are inspectable markdown — no black box.
- **Specific Task(s):**
  > "Investigate the trade-offs between Postgres logical replication and CDC tooling for a decision."
- **Specific Prompt(s):**
  > `deep research: compare Postgres logical replication vs CDC tooling — which to pick for low-latency analytics, with sources`

### Чеклист перед подачей:
- [ ] репо ≥5 звёзд (сейчас 4 — НЕ хватает)
- [ ] числа в README/description выверены и совпадают
- [ ] README написан человеком (не raw-AI)
- [ ] нет открытого другого issue в этом репо одновременно
- [ ] подаётся руками в браузере, не CLI

---

## Альтернативные каталоги (если захочешь шире)

| Каталог | ★ | Механизм | Фит |
|---|---|---|---|
| alirezarezvani/claude-skills | 18k | **PR в ветку `dev`** (в `main` — авто-close), читать CONVENTIONS.md | хороший — это про skills |
| VoltAgent/awesome-claude-code-subagents | 21.7k | PR напрямую (`.md` агента + README) | слабый — это про субагентов, не скиллы |

---

## Статус исполнения (2026-06-14)

- [x] ✅ GitHub-description репо исправлен на верные числа (9/103/29/460/39).
- [x] ✅ Цифры выверены — README прав (авто-ген), description устарел и поправлен.
- [x] ✅ ДРАФТ 1 опубликован в gpt-researcher#1572: https://github.com/assafelovic/gpt-researcher/issues/1572#issuecomment-4700801937
- [x] ✅ PR в alirezarezvani/claude-skills открыт: **https://github.com/alirezarezvani/claude-skills/pull/851** (base: dev, mergeable, бот не зарубил). Ждёт ревью мейнтейнера. Риск: возможный дубль с `research/research` — спозиционирован как «тяжёлый методичный vs быстрый роутер».
- [ ] ⏸️ Submission в awesome-claude-code — БЛОКЕР: нужно 5★ (сейчас 4). Подаётся руками через веб-форму (CLI/бот запрещены). Текст готов выше.

## Остаётся на Ивана (вручную)

1. **Набрать 5-ю звезду** на репо → разблокировать submission в awesome-claude-code, затем подать руками через форму.
2. **Мониторить PR #851** — ответить мейнтейнеру если попросят правки.
