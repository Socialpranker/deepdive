# Benchmark protocol

The point of this suite is to replace claims with numbers. Right now the README
asserts the skill verifies sources, triangulates, and runs adversarial passes — but
ships zero evidence (`eval/output/` empty, `runs.csv` empty, no example runs). One
published benchmark closes that gap and is the single highest-credibility artifact
the project can have.

**Nothing here fabricates results.** You run the skill on a fixed question set on
your own machine; the scripts score what the runs produced.

## The suite

8 questions in `eval/questions/benchmark/`, one per file, spanning all <!--gen:count:genres-->6<!--/gen--> genres and
all 3 depths:

| slug | genre | depth |
|---|---|---|
| sqlite-vs-duckdb-analytics | decision | shallow |
| postgres-replication-vs-cdc | decision | medium |
| rag-chunking-strategies-2026 | qa | medium |
| open-source-ai-licensing | qa | medium |
| wasm-component-model | explainer | medium |
| edge-inference-cost-model | explainer | medium |
| vector-db-landscape-2026 | landscape | deep |
| llms-plateau-claim | validation | deep |

Genres/depths are spread on purpose: a benchmark that's all-medium-decision hides
where the skill is weak.

## Run it

For each question, in a Claude Code session at the repo root:

```
/deepdive <paste the Question block>
```

Pin the depth stated in the file. To compare configs, run the same question under:
- **A** — default routing
- **B** — `... with all on opus`
- **C** — `... with cheap mode`

After each run, record the real cost (`/cost` in the session) into
`eval/runs/runs.csv` under the matching `run_id` (`<slug>-A` etc.).

## Score it

```bash
# deterministic axes + render the judge input
python eval/score_run.py --research-dir research/<slug> --run-id <slug>-A

# run eval/output/<slug>-A_judge_input.md through Opus, save JSON to
# eval/output/<slug>-A_judge.json, then:
python eval/score_run.py --research-dir research/<slug> --run-id <slug>-A \
  --judge-json eval/output/<slug>-A_judge.json
```

Citation integrity is computed live by `check_citations.py` (it resolves every
source URL). The judge handles the semantic axes. Floor rule: integrity < 0.70
halves the final quality score.

## Publish it

```bash
python eval/aggregate.py --out eval/BENCHMARK_RESULTS.md
```

Paste the resulting table into the README under a "Benchmarks" section, with a one-
line method note and a link to `eval/rubric.md`. Re-run after catalog changes so the
numbers stay honest.

## Is the instrument itself any good? (measured 2026-09-20)

Before spending money on eight live runs, check that the rubric can tell a careful
report from a booster one. `eval/questions/_control/` holds two hand-built runs on
the same question — `strong/` (quotes match sources, both hypotheses resolved, three
real counters, one dead-link-free source set) and `weak/` (universal claims, no
dates, one 404 source, no counters).

| run | citation | diversity | quality |
|---|---|---|---|
| strong (judge 5/4/4) | 1.000 | 0.925 | **0.922** |
| weak (judge 1/1/0) | 0.500 | 0.475 | **0.156** |
| weak + deliberately blind judge (5/5/5) | 0.500 | 0.475 | 0.411 |
| strong + deliberately harsh judge (1/1/1) | 1.000 | 0.925 | 0.512 |

Two readings. The rubric separates the fixtures by 5.9×. And the ordering survives
the worst case where the judge is useless in both directions (0.411 < 0.512) — the
citation floor carries it — though the margin drops to 1.24×, so a judge that
systematically over-scores still degrades the benchmark badly.

Caveat, on the record: the fixtures were written and judged inside one Claude
session, so this measures the scoring formula, not real research quality, and it
does not validate the judge against an independent opinion. `tests/test_scorecard_
discriminates.py` pins the ordering offline; the live-URL part is exercised only by
a manual run.

## Run-to-run spread — measure it before comparing versions (2026-09-20)

The same question (`sqlite-vs-duckdb-analytics`, shallow, default routing) was run three
times by three independent executors who could not see each other's directories. Every
run was gated by `finish.py` and judged in a separate session by a judge that did not
know the author.

| run | citation | diversity | quality |
|---|---|---|---|
| A | 1.000 | 0.825 | 0.799 |
| B | 1.000 | 0.967 | 0.899 |
| C | 1.000 | 1.000 | 0.849 |

**Spread 0.099, sd 0.050, mean 0.849.** A single run therefore cannot support a claim
that version X beats version Y: the noise between identical runs is as large as any
plausible improvement. Compare versions on at least 3 runs per question, and report the
spread alongside the mean.

**Judge inputs changed on 2026-11-07.** Before that date the judge saw the first 8
source-linked lines of the report and no source text, so `factual_accuracy` measured
internal consistency (N4–N6 judges said so and stopped at 3). Now `score_run.py` samples
8 lines with a seed taken from the run id and prints the saved quotes of each cited source
under the thesis. Scores from before and after are not comparable: re-render and re-judge
old runs before putting them next to new ones.

Re-judged the same day (12 runs, Opus high, one fresh judge per run, files `output/*-q_*`;
sqlite runs scored without readout, as shallow has none):

| series | old mean (sd) | new mean (sd) |
|---|---|---|
| pg-cdc A | 0.805 (0.045) | 0.751 (0.017) |
| pg-cdc D | 0.721 (0.037) | 0.783 (0.016) |
| pg-cdc N | 0.777 (0.014) | 0.803 (0.019) |
| sqlite | 0.849 (0.050) | 0.744 (0.079) |

The ranking of A/D/N flipped, and within-series spread on pg-cdc fell about 2.5x. The
adversarial axis, whose input did not change, dropped 5→4 on all three sqlite runs: two
judges on the same text disagree by about one point per axis.

**Binary checks from 2026-11-07 (later the same day).** Because of that disagreement the
judge no longer scores 0–5. It answers fixed yes/no checks (C1–C4, A1–A5, R1–R7 in
`judge_prompt.md`) and gives each sampled thesis a supported / unsupported / unverifiable
verdict; the axis score is the share passed. The `-q` scores above came from the 0–5
judge and are not comparable with binary-check scores.

Agreement, measured the same day: the three sqlite runs, two fresh Opus-high judges each,
same input file (`output/sqlite-{A,B,C}-b{1,2}_judge.json`). The judges agreed on 51 of 51
items (24 thesis verdicts, 27 checks); the 0–5 judges had differed by a point on the same
text. Both judges were the same model with the same prompt, so this is repeatability, not
cross-model agreement.

Agreement does not mean the input is right. Supported theses came out at 2/8, 1/8 and 0/8,
and a spot check of the sources shows two kinds of "unsupported". Some numbers are in no
source file at all (sqlite-A "124×", sqlite-C "+69% bundle"): real report defects. Others
are in the source file but in a prose line with an inline quote, not in a `> ` line, and
`source_quotes()` reads only `> ` lines (sqlite-B s05 "750 kB … 20MB binary" on line 26,
sqlite-C s09 "3-5 times faster" on line 26).

Fixed the same evening: `source_quotes()` now also passes every line of a section whose
heading mentions quotes or numbers ("Key quotes", "Дословные цитаты", "Числа"), and the
prompt counts a computed figure only when the thesis says it is computed. Same theses, six
new judges (`output/sqlite-*-c{1,2}_judge.json`):

| run | supported theses (judge 1 / 2) | coverage | adversarial |
|---|---|---|---|
| sqlite-A | 2/8 / 2/8 | 2/4 / 2/4 | 3/5 / 3/5 |
| sqlite-B | 2/8 / 1/8 | 4/4 / 3/4 | 4/5 / 4/5 |
| sqlite-C | 2/8 / 1/8 | 3/4 / 3/4 | 4/5 / 4/5 |

Agreement 48 of 51. The three splits are the cases the judges themselves flagged as
borderline: an "order of magnitude smaller" derived from 750 kB vs 20 MB, "point operations"
read as "single-row operations", and hypotheses resolved in prose without the words
"confirmed". Supported theses stay low because most failures are real: a SQLite timing that
is DuckDB's in s07, "two orders of magnitude" where s07 says 14.7x, "three sources" citing
one.

**Number integrity from 2026-11-07 (night).** The judge's most common failure, a number
absent from the cited source, is now caught without a model by `check_numbers.py`, a
deterministic axis with weight 0.10 (taken 0.05 from factual accuracy, which samples only
8 theses, and 0.05 from source diversity). It searches the same lines the judge sees under a
thesis, so a number kept only in a fetcher's summary counts as missing. Controls: sqlite-A
0.286 («124×», «14», «938», versions 3.41.2 and 0.9.1 missing), sqlite-B 1.0 («750 kB»
found in a prose line of the quotes section), sqlite-C 0.696 («+69%» missing; it is
26→44 MB computed and cited as `[N12]`, the 44 MB row), `_control/strong` 1.0. On the 15
pg-cdc runs with a report the axis spans 0.0–0.89. In samples from N6, A3 and N10 the
missing numbers sit almost all in `## Summary` or «Что это» of the source file rather than
in its quotes. That is too frequent for a blocker, so `finish.py` runs it as an advisory step
(`warn`, finish stays green) until the fetcher keeps numbers in quotes.

**Every judge input before 2026-11-07 (night) carried a wrong question.** `_question_from_plan`
returned the first plain line of `plan.md`, which on all bench runs was a frontmatter field
(«mode: medium», «slug: …»). Judges answered C1 («does the report answer the question»)
from the report and hypotheses alone. It now reads `question:`, then a «вопрос/question»
section, then the plan title. The agreement numbers above were measured on the old inputs;
re-render `*_judge_input.md` before the next judging round, and do not mix old and new
coverage scores.

Two other things this exercise measured:

- **Self-judging inflates.** Run A was first judged by its own author (4/3/4 → 0.819),
  then by an independent judge (3/3/5 → 0.799), which caught two figures the report
  attributed to sources that do not contain them. Keep `*_selfjudge.json` out of scoring.
- **The gate earns its keep.** Two of three runs were rejected by `finish.py` on first
  submission — one for a quarantined number in `memo.md`, one for memo figures missing
  from `numbers.csv`. Both were real defects, not false alarms.

## What "good" looks like

The headline metric is **quality-per-dollar**, not raw quality — a $8 all-opus run
that scores 0.88 can lose to a $2 default run that scores 0.82. That comparison is
the whole reason model routing exists, and publishing it is the proof the routing
claim is real.
