# Benchmark protocol

The point of this suite is to replace claims with numbers. Right now the README
asserts the skill verifies sources, triangulates, and runs adversarial passes — but
ships zero evidence (`eval/output/` empty, `runs.csv` empty, no example runs). One
published benchmark closes that gap and is the single highest-credibility artifact
the project can have.

**Nothing here fabricates results.** You run the skill on a fixed question set on
your own machine; the scripts score what the runs produced.

## The suite

8 questions in `eval/questions/benchmark/`, one per file, spanning all 6 genres and
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
/deep-research <paste the Question block>
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

## What "good" looks like

The headline metric is **quality-per-dollar**, not raw quality — a $8 all-opus run
that scores 0.88 can lose to a $2 default run that scores 0.82. That comparison is
the whole reason model routing exists, and publishing it is the proof the routing
claim is real.
