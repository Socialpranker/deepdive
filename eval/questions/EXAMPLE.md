# Eval question template

Copy this file to `eval/questions/<your-slug>.md` and fill it in. Keep one
question per file. The point is that every model config runs the *same*
question, so the comparison is apples-to-apples.

---

## Question

<The exact research question or decision, as you'd type it after `/deepdive`.
Be specific — an underspecified question makes runs incomparable.>

## Depth

<shallow | medium | deep — pin it so every config runs the same depth.
Different depth = different source budget = unfair comparison.>

## Why this question (for the judge)

<One or two lines of context: what decision this supports, what "good" looks
like. The judge reads this to score coverage.>

## Configs to compare

<Which model setups you'll run. Examples:
- A: default routing (Opus on phase 1/3/6, Haiku on fan-out, Sonnet/high synth)
- B: all-opus  (`deepdive <q> with all on opus`)
- C: cheap-mode (`... with cheap mode`)
Give each a run_id you'll use in runs.csv.>
