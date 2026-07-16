<div align="center">

# Deepdive

### A structured meta-research skill for Claude Code

**Stop ad-hoc Googling. Start documented investigation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-d97757?style=flat-square)](https://claude.com/claude-code)
[![Skills](https://img.shields.io/badge/Anthropic-Agent%20Skills-d97757?style=flat-square)](https://docs.anthropic.com/claude/docs/skills)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
[![Auto-Validated](https://img.shields.io/badge/APIs-Auto--Validated%20Weekly-blueviolet?style=flat-square)](.github/workflows/catalog-sync.yml)
[![Stars](https://img.shields.io/github/stars/Socialpranker/deepdive?style=flat-square&logo=github)](https://github.com/Socialpranker/deepdive/stargazers)

<br>

**[Docs](https://socialpranker.github.io/deepdive/)** · **[Install](#install-in-30-seconds)** · **[How it works](#how-it-works)** · **[Contribute](CONTRIBUTING.md)**

<br>

```
You: investigate the trade-offs between Postgres logical replication and CDC tooling

Claude:  ✓ Reframed your question (3 hypotheses)
         ✓ Picked genre: decision (comparison + validation)
         ✓ Wrote plan.md (17 sections)
         ✓ Checked your env: 4 APIs available, 2 fallback to HTML
         ✓ Launched 4 sub-agents across 12 channels
         ✓ Saved 23 sources to sources/ with quotes
         ✓ Ran adversarial pass (3 counter-arguments)
         ✓ Report ready: research/postgres-replication-vs-cdc/2026-05-21_decision.md
```

</div>

---

## What this is

A [Claude Code skill](https://docs.anthropic.com/claude/docs/skills) that turns **"research this topic"** into a **<!--gen:count:phases-->11<!--/gen-->-phase pipeline** with hypothesis testing, parallel sub-agent search, source triangulation, and adversarial review.

The output is a folder you can return to in a month. Every claim traces to a specific source file. The plan documents *why* you made every choice. No re-research needed.

> **New here?** Start with the [Quickstart](QUICKSTART.md) — install → invoke → first result in ~5 min.

<table>
<tr>
<th width="50%">Without this</th>
<th width="50%">With this</th>
</tr>
<tr>
<td>

One-shot prompt → wall of text

Sources lost in chat history

No way to detect bias

No reuse next time

Generic Google results

Sources include... *(vague)*

</td>
<td>

17-section `plan.md` documents every choice

Each source = file with verbatim quotes

Mandatory adversarial pass + opposition queries

Atomic theses in `findings/FN.md` reusable

<!--gen:count:channels-->29<!--/gen--> named channels + <!--gen:count:stat_sources-->460<!--/gen-->+ stat sources

Every claim → `[s12]` link → specific quote

</td>
</tr>
</table>

---

## Install in 30 seconds

<details open>
<summary><b>For Claude Code (CLI)</b></summary>

```bash
git clone https://github.com/Socialpranker/deepdive.git \
  ~/.claude/skills/deepdive
```

That's it. Now type any of these in a Claude Code session:
- "Investigate X"
- "Изучи тему"
- "Validate this hypothesis"

</details>

<details>
<summary><b>For Claude Desktop (Skills enabled)</b></summary>

```bash
# Clone
git clone https://github.com/Socialpranker/deepdive.git
cd deepdive

# Package as .skill bundle
zip -r ../deepdive.skill . -x ".*" -x "*.zip"

# Upload via Claude.app → Settings → Skills → Add Skill
```

</details>

<details>
<summary><b>For other LLMs (Codex, Gemini, local)</b></summary>

The <!--gen:count:phases-->11<!--/gen-->-phase methodology is portable. Load `SKILL.md` + `references/*.md` into the LLM's context manually. Skip the sub-agent parts and use separate chat sessions per subtopic.

[Full instructions →](#use-with-other-llms-codex-gemini-etc)

</details>

---

## How it works

The skill runs **<!--gen:count:phases-->11<!--/gen--> phases** in order:

| Phase | Name | What happens |
|:---:|:---|:---|
<!--gen:phases:table:en-->
| **1** | **Reframing** | opus / high |
| **2** | **Genre & block selection** | sonnet / medium |
| **3** | **Plan** | opus / medium |
| **3.5** | **Capability Discovery** | sonnet / low |
| **3.7** | **Plan-review gate** | sonnet / low |
| **4** | **Search** | sonnet / medium |
| **5** | **Claims-ledger + triangulation** | haiku / low |
| **5.5** | **Evidence filter** | sonnet / low |
| **6** | **Synthesis + multi-angle red team** | opus / high |
| **6.5** | **Verify** | haiku / low |
| **7** | **Refresh targets** | sonnet / medium |
<!--/gen-->

Each phase runs on a model matched to its task — Opus where reasoning multiplies (1/3/6), Haiku for the parallel fan-out (4). The skill announces the routing and an estimated cost up front, once.

Every phase is **transparent**: you see what's happening, you confirm key decisions, and you get a folder you can return to. Before any search fires, the **plan-review gate** (3.7) shows you the reframing, hypotheses, genre, and channels and lets you approve or edit them — strictness scales with mode (deep waits for an explicit go-ahead, medium is a soft check, shallow skips it). Editing the plan before execution is the single highest-leverage step in the whole pipeline — Gemini Deep Research calls plan review its "biggest lever over output quality," and a wrong plan executed perfectly still produces a wrong report.

Reframing (1) doesn't just restate the question — a **router** classifies its profile (factual / multi-step / relational / comparative / landscape) and that classification picks the decomposition method: factual questions get flat independent subquestions, multi-step ones ("X given Y") get least-to-most leveling, comparative ones get a shared axis matrix with mandatory opposition queries per candidate. Picking the wrong decomposition for a question's shape is a silent failure mode — the router makes the choice explicit instead of defaulting to "flat parallel" for everything.

Phase 4 (Search) isn't a single pass — it's a bounded loop with three cheap safeguards so it doesn't quietly waste budget or silently give up:
- **Cheap goal-check** — after each round, a Haiku pass tags every subquestion `met` / `partial` / `unmet` with a one-line reason. This is what the expensive Opus evaluation reads instead of re-deriving the gap from scratch, and it's what targets the next round's dispatch.
- **No-progress circuit breaker** — two consecutive rounds that add nothing new to the source pool stop the loop immediately, regardless of remaining budget. The unresolved thread goes to Open Questions instead of burning tokens chasing a dead end.
- **Least-to-most decomposition** — for layered questions ("X given Y"), subquestions are leveled `L1 → L2` instead of dispatched flat in parallel: L1 rounds run first, concrete facts they surface get carried forward, and L2 queries are launched already sharpened by that context. Independent subquestions still run flat.

Scoring (5) doesn't stop at the usual Credibility/Recency/Bias rating — it also flags **input-level skepticism**: a source that measures its own product, self-reports a benchmark, or is directly disputed by another collected source gets a strict `caveat:` marker (`vendor` / `self-reported` / `disputed:sNN`) *before* the claim reaches `claims.csv`, not after synthesis has already built on it. A claim whose key number carries that marker is capped at `confidence: medium` (or `low` for an unresolved dispute) — the same rule shape as primary-first sourcing. Vendor benchmarks are the numbers that most often get quietly repeated as fact; catching them on the way in, not in the red team pass at the end, is the point.

For medium/deep depth, the pipeline runs two more machine-checked passes most one-shot research skips entirely:
- **Evidence filter (5.5)** — a CRAG-style relevance classifier runs on every (claim, source) pair *before* synthesis and keeps only the quotes that actually support that specific claim. Dumping every found source into synthesis measurably hurts quality (Search-o1 dropped 33%→24% doing exactly that); this is the fix, not a nice-to-have.
- **Faithfulness verification (6.5)** — beyond checking that a cited link is alive, the skill checks that the source *entails* the claim it's attached to (RAGAS/ALCE-style claim⊨quote), and writes `SUPPORTED` / `PARTIAL` / `UNSUPPORTED` verdicts to `.verify/faithfulness.json`. Citation fabrication is common enough industry-wide — the Tow Center found a >60% error rate in AI-generated citations — that checking for it, not just for dead links, is a real differentiator.

None of this is enforced by discipline alone: `scripts/validate_phases.py` reads a finished run's `mode:` and checks that every phase mandatory for that mode actually left its file artifact (`plan.md`, `claims.csv`, `evidence/`, `.verify/*.json`, the dated report, ...). A skipped phase fails the check instead of silently passing — the model can't just claim "done." As of finish-up, this check is a **blocker, not a suggestion**: the skill won't report a research as done on a red gate, symmetrically to how a report isn't "done" without its verification header. `sources.csv` itself is now built the same deterministic way — `scripts/build_sources_csv.py` generates it from `sources/NN.md` frontmatter (with a `--check` mode for CI) instead of being assembled by hand each run.

Want to compare models head-to-head? The [eval harness](eval/README.md) scores any run on 6 axes.

---

## What's inside

<table>
<tr>
<td width="33%" valign="top">

### <!--gen:count:blocks-->105<!--/gen--> Report Blocks

10 categories: **FRAME** · **EXPLAIN** · **COMPARE** · **MAP** · **VALIDATE** · **ANALYZE** · **CLOSE** · **PEOPLE** · **NUMBERS** · **CONTEXT**

Each block has its own template, anti-patterns, and composition rules.

[Block library →](references/blocks/INDEX.md)

</td>
<td width="33%" valign="top">

### <!--gen:count:channels-->29<!--/gen--> Search Channels

Named strategies with query patterns + paywall fallbacks:

`web-general` · `academic` · `preprint-servers` · `code-github` · `forum-discussion` · `news-current` · `industry-reports` · `regulatory-legal` · `competitive-signals` · `data-statistical-gov` · `product-analytics` · `crypto-analytics` · `api-direct` · *and more*

[Channels catalog →](references/channels.md)

</td>
<td width="33%" valign="top">

### <!--gen:count:stat_sources-->460<!--/gen-->+ Stat Sources

14 cross-industry + 19 industry categories. Each entry: URL · Type · Access · Quality · Limitations · Combine-with · Fallback.

Categories: `gov_macro` · `companies_public` · `crypto` · `health` · `education` · `climate_env` · `science` · 19 industries

[Sources catalog →](references/stat_sources/INDEX.md)

</td>
</tr>
<tr>
<td valign="top">

### 6 Report Genres

| Genre | When |
|:---|:---|
| `qa` | Open meta-research |
| `explainer` | "How does X work" |
| `decision` | "X or Y" |
| `landscape` | "Who's in this space" |
| `validation` | "Is X true" |
| `custom` | Hybrid, assembled per question |

[Genres →](references/genres.md)

</td>
<td valign="top">

### <!--gen:count:api-->39<!--/gen-->+ API Endpoints

Free no-auth APIs prioritized:

`Semantic Scholar` · `OpenAlex` · `CrossRef` · `arXiv` · `DefiLlama` · `CoinGecko` · `Reddit JSON` · `HN Algolia` · `World Bank` · `SEC EDGAR` · `ClinicalTrials.gov` · `PubMed` · `GDELT`

Auth via env vars only — skill never asks for keys inline.

[API catalog →](references/api_sources/INDEX.md)

</td>
<td valign="top">

### Weekly Auto-Sync

GitHub Actions cron validates all endpoints + discovers upstream additions:

- HEAD-check <!--gen:count:api-->39<!--/gen-->+ APIs weekly
- Scan public-apis & awesome-public-datasets
- Auto-PR for dead endpoints
- Reports committed to `reports/` branch

[Workflow →](.github/workflows/catalog-sync.yml)

</td>
</tr>
<tr>
<td valign="top">

### Model Routing

Per-phase model selection — quality where it multiplies, cheap where it parallelizes:

- Reframing / plan / adversarial → **Opus**
- Sub-agent fan-out (search) → **Haiku** (cheap × N)
- Synthesis → **Sonnet/high**

~$2 instead of ~$8 on a deep run, *and* higher quality on critical phases. Override with `with all on opus` / `with cheap mode`.

[Routing →](references/model_routing.md)

</td>
<td valign="top">

### Eval Harness

Compare research quality across models. Same question, different configs, scored on 6 axes:

- Deterministic (script): citation integrity, source diversity, cost
- Semantic (LLM-judge): accuracy, coverage, adversarial honesty

Weighted sum with a **citation floor** — hallucinated sources can't win on depth. Verdict = quality per dollar.

[Eval →](eval/README.md)

</td>
<td valign="top">

### Citation Check

`check_citations.py` resolves every source URL — dead `OPEN` links flagged as likely hallucinations; transport flaps marked `UNKNOWN`, not penalized.

Ignores env proxies (`trust_env=False`). `--strict` for CI.

Verification runs two layers: **liveness** (does the source exist) and **faithfulness** (does it actually entail the claim it's cited for). Faithfulness verdicts — `SUPPORTED` / `PARTIAL` / `UNSUPPORTED` — land in `.verify/faithfulness.json`.

[Check →](eval/check_citations.py)

</td>
<td valign="top">

### Phase-gate Validator

`scripts/validate_phases.py` reads a finished run's `mode:` frontmatter and checks that every phase mandatory for that depth left its file artifact — `plan.md`, `claims.csv`, `evidence/`, `.verify/*.json`, the dated report.

A skipped phase fails the check (`--strict` for CI) instead of the model just asserting "done" — it's a **finish-up blocker**, not advice. Machine insurance against the one failure mode a markdown methodology can't fix by discipline alone.

Its own inputs are machine-built too: `scripts/build_sources_csv.py` generates `sources.csv` deterministically from `sources/NN.md` frontmatter (`--check` for CI drift), and `eval/validate_structure.py` enforces the `caveat:` field as a strict enum (`-` / `vendor` / `self-reported` / `disputed:sNN`) instead of free text, so it stays greppable.

[Validator →](scripts/README.md)

</td>
</tr>
</table>

---

## Example folder

Sample output for a typical `decision`-genre research:

```
research/<topic-slug>/
├── plan.md                              # 17-section plan
├── sources.csv                          # Index with C/R/B scoring
├── sources/                             # One file per source
│   ├── 01_vendor-docs.md                # Primary, total=14
│   ├── 02_benchmark-paper.md            # Academic, total=12
│   ├── 03_industry-report.md            # Industry, total=13
│   ├── 04_forum-thread.md               # Forum, total=9 (opposition)
│   └── ... (19 more)
├── findings/
│   ├── F1_<atomic-thesis>.md            # confidence: high
│   └── F2_<atomic-thesis>.md            # confidence: medium
└── 2026-05-21_decision.md               # Final report
```

Final report structure (assembled from the blocks chosen in plan.md):

```markdown
## TL;DR
- Claim A holds under condition X [confidence: high]
- Claim B holds conditionally on threshold Y [confidence: medium]
- Claim C is disputed by opposition sources [confidence: low]

## Mental model
[How the underlying mechanism works...]

## Falsification criteria
What would disprove H1, H2, H3...

## Verdict conditional
Recommendation IF: <conditions met>
Different recommendation OTHERWISE: <conditions broken>

## Counter-arguments (steel-man)
CA1: "<the strongest opposing claim>" [source: s09]
     → Our answer: <conditions under which CA1 fails>
CA2: ...
```

Every claim is clickable to its source. A month later, you don't re-research — you read.

---

## Contribute

The catalog is most valuable when **it grows**. Easy contributions:

| Time | Type | Example |
|:---:|:---|:---|
| 15 min | Add a stat source | `Add SimilarWeb Pro to consumer_digital` |
| 15 min | Improve a query pattern | `Better arxiv channel queries for biology` |
| 30 min | New search channel | `Add patent-search with USPTO+EPO fallback` |
| 1-2h | New industry category | `Add industries/aerospace.md` |
| 2-4h | New report block | `Add decision-tree to compare.md` |
| Half-day | LLM adapter | `Add codex/ folder with adapted protocols` |

[Full contributing guide →](CONTRIBUTING.md)

[![Contributors](https://contrib.rocks/image?repo=Socialpranker/deepdive)](https://github.com/Socialpranker/deepdive/graphs/contributors)

---

## FAQ

<details>
<summary><b>How is this different from ChatGPT Deep Research / Perplexity?</b></summary>

Those are **products** — closed UI, fixed flow, opaque source selection. This is **open methodology** — you control every step, the protocol is markdown you can fork, the source catalog is yours to extend.

They also don't separate sources into files, don't do explicit triangulation, don't run adversarial passes, and don't produce reusable atomic theses. Nor do they filter evidence for relevance before synthesis (feeding a model everything you found measurably hurts quality — Search-o1 dropped from 33% to 24% accuracy doing that) or verify that a cited source actually *supports* the claim it's attached to, rather than just existing (faithfulness, not just liveness). Citation fabrication is common enough industry-wide — the Tow Center found a >60% error rate in AI-generated citations — that checking for it is a real differentiator, not a nice-to-have.

Honesty about sources goes further than checking they exist: scoring flags a source that's measuring its own product, self-reporting a benchmark, or directly disputed by another collected source, and caps the confidence of any claim resting on that number — *before* it ever reaches the report. Vendor benchmarks getting quietly repeated as fact is a market-wide problem; catching it on input, not as an afterthought, is the same honesty principle as faithfulness applied one step earlier.

</details>

<details>
<summary><b>Does it work without Claude Code CLI?</b></summary>

Yes — on Claude Desktop with Skills enabled. Also works manually with any LLM by loading the markdown files into context (see ["Use with other LLMs"](#use-with-other-llms-codex-gemini-etc) below).

</details>

<details>
<summary><b>What's a research output look like?</b></summary>

See the [example folder](#example-folder) above. TL;DR: a folder with `plan.md` + `sources/NN.md` per source + `findings/FN.md` atomic theses + final `<date>_<genre>.md` report.

Every claim in the final report links to a specific `sources/NN.md` file.

</details>

<details>
<summary><b>Why so many files? Isn't this overkill?</b></summary>

For a 5-minute "what's the latest X" question — yes. That's why `shallow` mode exists (5-7 sources, no sub-agents, ~15 min). The full machinery is for `medium` (1 hour) and `deep` (3 hours) when you need to actually use the output for a decision.

The file-per-source structure is the key **reuse** mechanism. A single research often informs 3-5 future researches because you can cite individual `sources/NN.md` directly.

</details>

<details>
<summary><b>Is this just prompt engineering?</b></summary>

It's **structured methodology + curated catalog + reusable templates + automation**.

- The <!--gen:count:phases-->11<!--/gen-->-phase workflow forces discipline
- <!--gen:count:stat_sources-->460<!--/gen-->+ stat sources catalog is curated knowledge
- <!--gen:count:blocks-->105<!--/gen--> reusable blocks compose any report shape
- `scripts/validate_phases.py` machine-checks phase completeness, not just style
- Weekly auto-validation keeps the catalog alive
- 25+ upstream awesome-lists give infinite discovery layer

Prompts are an implementation detail, not the value.

</details>

<details>
<summary><b>Can I use this commercially?</b></summary>

Yes — MIT licensed. Use it, modify it, integrate it into products. Attribution appreciated but not required.

</details>

---

### Use with other LLMs (Codex, Gemini, etc.)

The methodology is portable. ~70% of content is LLM-agnostic markdown templates.

| Component | Claude-specific | Universal |
|:---|:---:|:---:|
| `SKILL.md` frontmatter | ✓ | — |
| Sub-agent `Explore` type | ✓ | — |
| <!--gen:count:phases-->11<!--/gen-->-phase workflow | — | ✓ |
| <!--gen:count:blocks-->105<!--/gen--> report blocks | — | ✓ |
| <!--gen:count:channels-->29<!--/gen--> search channels | — | ✓ |
| <!--gen:count:stat_sources-->460<!--/gen-->+ stat sources | — | ✓ |

**To adapt:**
1. Load `SKILL.md` + relevant `references/*.md` into the LLM's context
2. Replace sub-agent parallelism with separate chat sessions per subtopic
3. Manage source files (`sources/NN.md`) externally — LLM produces content
4. PRs welcome for `codex/`, `gemini/`, `local/` adapters

---

<div align="center">

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Socialpranker/deepdive&type=Date)](https://star-history.com/#Socialpranker/deepdive&Date)

</div>

---

<details>
<summary><h2>На русском</h2></summary>

**Deepdive** — скилл для [Claude Code](https://claude.com/claude-code), превращающий «загугли это» в дисциплинированный <!--gen:count:phases-->11<!--/gen-->-фазный процесс.

### Что внутри

- **<!--gen:count:phases-->11<!--/gen--> фаз workflow**: <!--gen:phases:list:ru-->Reframing → Genre & block selection → Plan → Capability Discovery → Plan-review gate → Поиск → Claims-ledger + триангуляция → Evidence-фильтр → Синтез + multi-angle red team → Verify → Refresh targets<!--/gen-->
- **<!--gen:count:genres-->6<!--/gen--> жанров отчёта**: qa / explainer / decision / landscape / validation / custom
- **<!--gen:count:blocks-->105<!--/gen--> блоков** в 10 категориях — переиспользуемые секции с шаблонами и анти-паттернами
- **<!--gen:count:channels-->29<!--/gen--> каналов поиска** с paywall fallback протоколом (включая api-direct)
- **<!--gen:count:stat_sources-->460<!--/gen-->+ статистических источников** в 14 cross-industry + 19 отраслевых категориях
- **<!--gen:count:api-->39<!--/gen-->+ API endpoints** для programmatic доступа (free no-auth приоритетны)
- **plan.md** с 17 секциями для прозрачности
- **Plan-review gate** (фаза 3.7) — единственная human-in-the-loop точка перед дорогой Фазой 4: план (гипотезы, жанр, каналы) показывается и утверждается ДО поиска; жёсткость по режиму (deep — ждать «Ок», medium — soft, shallow — skip)
- **Multi-angle red team** из враждебных ролей (Skeptic/Contrarian/Gap-hunter) с триажем severity (обязателен для medium/deep)
- **Evidence-фильтр** (фаза 5.5) — CRAG-классификатор keep/drop по паре (тезис, источник) перед синтезом: наивная подача всего найденного снижает качество (Search-o1 33%→24%), в синтез идут только relevant-цитаты из `evidence/`
- **Faithfulness-верификация** (фаза 6.5, второй слой) — помимо liveness (жива ли ссылка) проверяется entailment «источник ⊨ тезис» (RAGAS-декомпозиция + ALCE), вердикты SUPPORTED/PARTIAL/UNSUPPORTED в `.verify/faithfulness.json`
- **No-progress circuit breaker** (фаза 4) — 2 раунда подряд без новой информации → стоп, нерешённое уходит в Open Questions вместо сжигания бюджета
- **Дешёвый goal-check** (фаза 4) — Haiku между раундами помечает каждый подвопрос met/partial/unmet, направляя следующий раунд и удешевляя дорогую Opus-оценку
- **Least-to-most декомпозиция** (фаза 4) — многошаговые подвопросы («X учитывая Y») раскладываются по уровням L1→L2 с накоплением контекста между ними вместо плоского параллельного запуска
- **Phase-gate валидатор** (`scripts/validate_phases.py`) — машинная проверка, что каждая обязательная для режима фаза оставила артефакт; пропущенная фаза не проходит проверку
- **Weekly auto-validation** через GitHub Actions

### Установка

```bash
git clone https://github.com/Socialpranker/deepdive.git ~/.claude/skills/deepdive
```

Триггеры: «проведи ресёрч», «изучи тему», «копни глубоко», «deep dive»

### Вклад

Каталог растёт через PRs. Самые ценные — новые источники в `stat_sources/` и `api_sources/`. См. [CONTRIBUTING.md](CONTRIBUTING.md).

</details>

---

<div align="center">

### Built by [Socialpranker](https://github.com/Socialpranker) · [MIT License](LICENSE) · [Roadmap](https://github.com/Socialpranker/deepdive/discussions)

**If this skill saves you time, [give it a star](https://github.com/Socialpranker/deepdive)** — it's the only metric I check.

</div>
