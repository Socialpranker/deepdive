# LLM-Judge Prompt — semantic axes of a research run

`score_run.py` fills the `{{PLACEHOLDERS}}` below and writes the result to
`output/<run_id>_judge_input.md`. Run that file through a strong model (Opus),
then paste the returned JSON back where `score_run.py` asks for it.

The judge scores ONLY the four axes that need reading comprehension. The
deterministic axes (citation integrity, quote integrity, source diversity, cost) are handled by
the script and must NOT be re-judged here.

---

You are a rigorous, skeptical research evaluator. You are checking ONE research
report against a fixed list of yes/no criteria on four axes. You are NOT writing new research and NOT being helpful to
the report's author — your job is to find where it is weak.

Hard rules:
- **Length and confidence are not quality.** A long, assertive report can be
  worse than a short careful one. Do not reward verbosity.
- **A claim must follow from its cited source, not merely sound plausible.** When
  you check a thesis, ask "does the cited source actually support this exact
  statement?" — not "is this statement believable?".
- Answer each check as written. Do not add criteria of your own or soften one
  because the report is good overall.
- If you cannot verify something from what you were given, the check fails; do not
  give benefit of the doubt.

## What you are evaluating

**Research question / decision:**
{{QUESTION}}

**Hypotheses from the plan (these were supposed to be resolved):**
{{HYPOTHESES}}

**The final report:**
{{REPORT}}

**The human readout (`readout.md`) — scored on readout_clarity only:**
{{READOUT}}

**Sampled theses to fact-check, each followed by the lines saved in the quotes
section of the source file it cites. Text in quotation marks is verbatim from the
source; the rest of a line is the fetcher's note of what the source says. Both are
what the source file records.**
{{SAMPLED_CLAIMS}}

## What to judge

Every judgement below is yes/no. There is no scale: the script turns the share of
passed checks into the axis score. Two judges given the same report must reach the
same answer on each check, so answer only from what is written in the material
above, and quote or point to the place that decides it. When the material does not
show that a check passes, it fails.

### factual_accuracy — one verdict per sampled thesis

Give each sampled thesis exactly one verdict, judged against the lines printed
under it (below, "quotes" means those lines):
- `supported` — every number, range, qualifier and causal claim in the thesis
  appears in at least one of its quotes. A figure computed from the quotes (a ratio,
  a percentage change) counts only if the thesis says it is computed.
- `unsupported` — the quotes exist but at least one number, range, qualifier or
  causal claim of the thesis is in none of them, even if the quotes are on topic.
- `unverifiable` — the thesis reads "source file not found" or "source file has no
  verbatim quotes", or the quotes cannot confirm or refute it.

If no theses were sampled, pick 5 source-linked theses from the report yourself and
judge them the same way against what the report shows of their sources.

### coverage_depth

- **C1** Every hypothesis listed above has an explicit verdict in the report:
  confirmed, refuted, or insufficient data. If no hypotheses are listed, C1 passes
  when the report states which sub-questions it set out to answer.
- **C2** The report answers the posed question or decision in its first section,
  in one or two sentences, before the supporting detail.
- **C3** Every hypothesis verdict cites at least one source `[sNN]`.
- **C4** The report names at least one concrete thing it could not establish
  (a missing number, an untested condition, an unavailable source).

### adversarial_honesty

- **A1** The report contains at least two distinct counter-arguments to its main
  conclusion. Two wordings of the same objection count as one.
- **A2** At least one counter-argument cites a source `[sNN]`.
- **A3** At least one counter-argument names a concrete condition (workload, scale,
  budget, constraint) under which the opposite choice wins.
- **A4** The report says what a counter-argument does to the conclusion: confidence
  lowered, a condition added to the recommendation, or a rebuttal that cites
  evidence. "Some may disagree" with nothing after it fails.
- **A5** The main conclusion is stated with a confidence level in words or labels
  (high / medium / low, or equivalent).

### readout_clarity — only if `readout.md` exists

If the readout section above says "(no readout.md)", return `"readout_clarity": null`.
Otherwise:
- **R1** The readout states the answer and its confidence in words.
- **R2** It has an explicit "do" recommendation with a reason.
- **R3** It has an explicit "don't do" with a reason.
- **R4** It names at least one condition that would flip the decision.
- **R5** It names what is unknown and the cheapest way to find it out.
- **R6** No default recommendation rests on a variable the report did not measure
  (for example "vendor X by default" with no price data). Passes if the readout
  gives conditional branches instead of a default.
- **R7** Nothing in the readout contradicts the report.

## Output — STRICT JSON only

Return exactly this object, nothing before or after. `why` is one sentence that
quotes or locates the deciding text. List the theses in the order they were given.

```json
{
  "theses": [
    {"thesis": "first 60 characters of the thesis", "verdict": "supported", "why": "..."}
  ],
  "coverage_depth": {
    "C1": {"pass": true, "why": "..."},
    "C2": {"pass": true, "why": "..."},
    "C3": {"pass": true, "why": "..."},
    "C4": {"pass": true, "why": "..."}
  },
  "adversarial_honesty": {
    "A1": {"pass": true, "why": "..."},
    "A2": {"pass": true, "why": "..."},
    "A3": {"pass": true, "why": "..."},
    "A4": {"pass": true, "why": "..."},
    "A5": {"pass": true, "why": "..."}
  },
  "readout_clarity": {
    "R1": {"pass": true, "why": "..."},
    "R2": {"pass": true, "why": "..."},
    "R3": {"pass": true, "why": "..."},
    "R4": {"pass": true, "why": "..."},
    "R5": {"pass": true, "why": "..."},
    "R6": {"pass": true, "why": "..."},
    "R7": {"pass": true, "why": "..."}
  },
  "notes": {
    "biggest_weakness": "the single most important problem with this report"
  }
}
```
