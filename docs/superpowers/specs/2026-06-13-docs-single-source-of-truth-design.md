# Design — Docs single-source-of-truth & onboarding (phase 1 of "scale & convenience")

**Date:** 2026-06-13
**Repo:** `Socialpranker/claude-deep-research`
**Status:** design approved section-by-section in brainstorming; awaiting written-spec review

## Context

`/deep-research` is a prompt-driven Claude Code skill: the model reads `SKILL.md`
(~6.3k tokens), progressively loads `references/*.md`, and does the research with its
own tools (WebSearch/WebFetch/Explore sub-agents/file writes). Python is confined to
CI catalog/structure validation and the eval harness. The value mass is the 776K
`references/` tree (methodology + ~250 curated catalog entries + an upstream
awesome-list discovery layer).

The user wants to make the skill **more scalable and more convenient**, prioritising
(in order): (1) convenience for a **newcomer who just installed the skill**, then later
a multi-LLM `runner/`. This spec covers **only phase 1 — newcomer convenience**. The
runner is explicitly out of scope here.

### The problem this spec solves

An audit (regex-verified against the files) found the docs **systematically lie**, and
there is **no machine-readable source** for any headline fact — every number and every
phase list is hand-typed prose that has drifted:

| Fact | Docs claim | Ground truth | How counted |
|---|---|---|---|
| Blocks | 75 / 76 | **103** | `grep -hE '^## [A-Z][0-9]+ —' references/blocks/*.md` (INDEX table agrees: 103 rows) |
| Channels | 28 (3 files) / 29 | **29** | `grep -cE '^#### [0-9]+\.' references/channels.md` |
| Stat sources | 280+ | **461** | `grep -rE '^\s*\*\*URL:\*\*' references/stat_sources/` |
| API endpoints | 30+ | **39** files / 10 dirs | `find references/api_sources -name '*.md' ! -name INDEX.md ! -name README.md` |
| Genres | 6 | **6** ✓ | `references/genres.md` H2 sections |
| Phases | "7" (most docs) / "6" (workflow.md title, eval/README) | **8 steps** in the canonical list (incl. 3.5); a **6.5** is bolted on in `runtime_verification.md` → effectively **9** | see below |

Phase-specific drift: `SKILL.md:107` says "7 фаз" but its own numbered list (L111–118)
has 8 steps (1, 2, 3, 3.5, 4, 5, 6, 7). `references/workflow.md:1` is titled "детали 6
фаз". `references/runtime_verification.md:89` injects a **Phase 6.5 "Verify"** (+ an
orphan Block F9) not merged into the numbered list. `README.md:133` says "7 phases" but
its table silently **drops Phase 7 (Refresh targets)**. `eval/README.md:20` says "6 фаз".

### Goal

Make headline facts **impossible to drift**: the truth lives in the files (counts) and
in one manifest (phases); docs are **generated** from that truth; CI **fails** when docs
diverge. Plus a short **quickstart** so a newcomer goes install → invoke → see output in
~5 minutes. No human ever hand-types a count or a phase name again.

### Non-goals (YAGNI)

- The `runner/` (multi-LLM engine) — that's phase 2, a separate spec.
- Rewriting the methodology or phase prose.
- Reorganising the `references/` tree or the catalog format.
- A committed full example run (`eval/output/`) — the user deprioritised it.
- A web UI over the manifest; auto-editing the catalog; semantic checks of prose.

## Decisions locked during brainstorming

1. **Audience:** the newcomer installing the skill (top-of-funnel).
2. **Scope of fixes:** clean counters + quickstart/onboarding + reconcile phase
   declarations. (Live example run explicitly *not* in scope.)
3. **Depth:** auto-generation + CI gate (not a one-off manual fix).
4. **Generator model: STAMP** — the generator *writes* the numbers/phases into the docs
   (between markers); CI runs it in `--check` mode and fails if "run it and the diff is
   non-empty".
5. **Gate behaviour:** `--check` just **fails red with a diff**; the human runs `--write`
   locally and commits. CI never writes to the repo.
6. **First release scope:** counters + phases + gate + quickstart together (one plan;
   staged with checkpoints because `docs/index.html` alone has ~30 marker sites and the
   full diff will exceed the user's ~400-line PR guideline — splitting/commit-shaping
   decided at plan time).
7. **First stamp landed as its own commit** ("впечатать правду"), separate from the
   generator-logic commit, so review sees logic apart from the mass number-replacement.

## Architecture

Three kinds of "source of truth", chosen by the nature of the data:

| What | Source of truth | Why |
|---|---|---|
| Counters (blocks, channels, stat sources, API, genres) | the **catalog files themselves**, counted by verified regexes | the data already lives in the files; a separate number registry would duplicate it |
| Phases (id, name_ru, name_en, model, effort, optional, order) | a **new `phases.yaml`** | a phase is structure (N phases × ~7 fields), not a number you can count from files; one place to edit the workflow skeleton |
| Phase *descriptions* (prose paragraphs) | stay as prose in `workflow.md` | meaning can't be generated; the gate guards only the skeleton (id/name/count), never the prose |

### Data flow

```
   references/blocks/*.md ──┐
   references/channels.md   ├─► catalog_counts.py (regex) ─┐
   references/**/*.md ───────┘                             │
                                                           ▼
   phases.yaml ─────────────────────────────────► stamp_docs.py
   (id,name_ru,name_en,model,effort,optional,order)        │
                                                           ▼
       rewrites only the text between markers in the target docs:
   README.md · SKILL.md · docs/index.html · docs/_config.yml ·
   blocks/INDEX.md · channels.md · stat_sources/INDEX.md · DESIGN.md · CONTRIBUTING.md
                                                           │
                                                           ▼
                  CI: `stamp_docs.py --check` → run generator,
              git diff empty? green : red (+ print the diff)
```

### Marker mechanism

Targeted HTML-comment anchors; the generator rewrites only the span between them, leaving
surrounding prose untouched. Works in markdown, in Jekyll `docs/index.html`, and does not
touch i18n wrappers.

```markdown
The block library has <!--gen:count:blocks-->103<!--/gen--> blocks across 10 categories.
```

Two key families:
- counters: `gen:count:blocks`, `gen:count:channels`, `gen:count:stat_sources`,
  `gen:count:api`, `gen:count:genres`, `gen:count:phases`
- phase blocks: `gen:phases:list:ru`, `gen:phases:list:en`, `gen:phases:table:en`
  (the README table — including the currently-dropped Phase 7)

## Components

Each is one file with one purpose, testable in isolation. Names/language finalised at
plan time to match repo conventions.

### 1. `phases.yaml` (new; repo root or `references/`)
The single structural source for phases. Declares all steps (1, 2, 3, 3.5, 4, 5, 6, 6.5,
7) with `id`, `name_ru`, `name_en`, `model`, `effort`, `optional`, and order = list order.
Lifts the list from `SKILL.md:111–118`, folds in 3.5 (optional) and 6.5/Verify from
`runtime_verification.md`, reconciles workflow.md's "6" title and README's missing Phase 7.
Depends on nothing. Read by the generator; `workflow.md`/`SKILL.md` reference it as canon.

```yaml
phases:
  - id: "1"    name_ru: "Переформулировка"        name_en: "Reframing"
    model: opus    effort: high    optional: false
  - id: "2"    name_ru: "Жанр и блоки"            name_en: "Genre & blocks"
    model: sonnet  effort: medium  optional: false
  - id: "3"    name_ru: "План"                    name_en: "Plan"
    model: opus    effort: medium  optional: false
  - id: "3.5"  name_ru: "Discovery возможностей"  name_en: "Capability Discovery"
    model: sonnet  effort: low     optional: true
  - id: "4"    name_ru: "Поиск"                   name_en: "Search"
    model: sonnet  effort: medium  optional: false
  - id: "5"    name_ru: "Скоринг и триангуляция"  name_en: "Score & triangulate"
    model: sonnet  effort: medium  optional: false
  - id: "6"    name_ru: "Синтез + adversarial"    name_en: "Synthesize + adversarial"
    model: opus    effort: high    optional: false
  - id: "6.5"  name_ru: "Верификация цитат"       name_en: "Verify"
    model: opus    effort: high    optional: false
  - id: "7"    name_ru: "Refresh targets"         name_en: "Refresh targets"
    model: sonnet  effort: medium  optional: false
```
(Field values above are the starting reconciliation — confirmed against the source docs
during implementation, not invented.)

### 2. `scripts/catalog_counts.py` (new)
Ground-truth extractor. One function `counts() -> dict` encapsulating the verified regexes
(`blocks`, `channels`, `stat_sources`, `api`, `genres`). Returns `{"blocks": 103, ...}`.
Depends only on the `references/` tree. Pure read, no side effects — callable from both the
gate and the tests.

### 3. `scripts/stamp_docs.py` (new; the core)
The stamper. Reads `phases.yaml` + calls `catalog_counts.py`. Finds `<!--gen:KEY-->...<!--/gen-->`
markers across the target docs and rewrites the span. Two modes:
- `--write` — stamp the values into the files.
- `--check` — run in memory, compare to disk, exit 1 + print diff on divergence.
The only component that writes to docs. Depends on #1 and #2.

### 4. Markers in existing docs (edit, not a new file)
Place `<!--gen:...-->` anchors at the locations the audit pinned by line:
`blocks/INDEX.md:3,27,184`, `channels.md:1,12`, `stat_sources/INDEX.md:147`,
`SKILL.md:107,221–224`, `README.md` (counters + phase table, **add the dropped Phase 7**),
`docs/index.html` (~30 sites, EN+RU), `docs/_config.yml`, `runner/DESIGN.md`, `CONTRIBUTING.md`.

### 5. `quickstart` (new section or `QUICKSTART.md`)
Newcomer onboarding: install → invoke `/deep-research <question>` → here's the result
folder. Form (top-of-README block vs standalone file) decided at plan time. Any counts in
it are stamped too.

### 6. CI integration (edit `.github/workflows/validate.yml`)
New step in the `structure-and-budget` job: `python scripts/stamp_docs.py --check`.
Red if docs drifted from truth. No network, no tokens — same shape as the existing gates.

## Data flow / modes

**A — dev edits the catalog (main case):** add a block → `stamp_docs.py --write` →
`catalog_counts()` recomputes 103→104 → every `gen:count:blocks` rewritten → diff shows
only the changed numbers → commit → push → CI `--check` → empty diff → green.

**B — someone hand-edits a number (the thing we cure):** contributor types "104 blocks"
without adding the block → push → CI `--check` runs the generator in memory → real count
103 ≠ 104 → non-empty diff → red + prints "expected 103, doc says 104" → fixed with `--write`.

**C — workflow changes (phases):** edit only `phases.yaml` (e.g. 6.5 becomes mandatory, or
a phase is added) → `--write` re-stamps the count, RU/EN lists, README table (incl. Phase 7)
→ `workflow.md` prose edited by hand (gate doesn't watch it) → CI `--check` guards the
skeleton: count + names match `phases.yaml` everywhere.

### Error handling (generator refuses bad input — it never stamps garbage)

| Situation | Behaviour |
|---|---|
| Marker `<!--gen:KEY-->` with no closing `<!--/gen-->` | fail with "unbalanced marker at file:line" — never guess |
| Unknown `KEY` in a doc (no such generator key) | fail: "unknown key KEY" — guards against typos |
| A generator key never appears in any doc | warn (not fail): "KEY stamped nowhere" — likely a forgotten marker |
| `phases.yaml` won't parse / missing required field | fail naming the field (like `db.ts` without ENCRYPTION_KEY) |
| A catalog regex returns 0 (file structure broken) | fail: "blocks=0, suspicious" — never silently stamp zero |

The last row is a direct lesson from the prior code review (where `--ci` silently
under-counted the floor on missing files; not repeated here).

## Testing

Python, in CI, no network. The generator edits 9 docs, so it must be guarded — one bug
would smear correct text across the repo.

**Unit — `catalog_counts.py`:** returns the verified numbers on the current tree
(`blocks==103, channels==29, stat_sources==461, api==39, genres==6`) — golden test, catches
regex/structure breakage. On a tiny fixture (2 blocks, 1 channel) returns 2 and 1 — tests
the counting logic independent of live numbers.

**Unit — `stamp_docs.py`, on temp files:** stamps between markers, surrounding text
untouched; `--check` exits 0 on synced doc, 1 + diff on diverged; idempotent (`--write`
twice → second diff empty); all 5 error situations → expected fail/warn.

**Unit — `phases.yaml`:** parses; every phase has required fields; `id`s unique; `order`
has no gaps.

**Integration (doubles as the CI gate):** `stamp_docs.py --check` on the **real repo**
after `--write` → exit 0. Both a test and the guard guaranteeing `main` stays synced.

**Not tested (YAGNI):** prose meaningfulness, Jekyll rendering, landing visuals.

## Implementation staging (for the plan)

1. **Generator logic + manifest + markers + tests** (no doc-content change yet beyond
   inserting markers around the *existing* numbers) — commit 1.
2. **First `--write` stamp** — rewrites the lying numbers to truth (75→103, 280+→461,
   28→29, phases reconciled, README Phase 7 restored) — commit 2 ("впечатать правду"),
   reviewable as a pure number/skeleton replacement.
3. **CI `--check` step** in `validate.yml` — commit 3.
4. **Quickstart** — commit 4 (pure prose).

PR-shaping (one PR vs two) decided at plan time given the ~400-line guideline and the
`docs/index.html` marker volume.

## Open items to resolve in the plan

- Exact `phases.yaml` field values for 3.5/6.5 confirmed against `runtime_verification.md`
  and `model_routing.md` (not from memory).
- Whether `references/workflow.md`'s "6 фаз" title and `eval/README.md`'s "6 фаз" become
  stamped (`gen:count:phases`) or are reworded to reference the manifest.
- `quickstart` form: top-of-README block vs standalone `QUICKSTART.md`.
- Final marker language/key naming to match repo conventions.
