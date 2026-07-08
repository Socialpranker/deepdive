# Quickstart

Get your first documented research run in ~5 minutes.

## 1. Install the skill

This is a Claude Code skill — a folder of methodology Claude reads, not a binary.

```bash
git clone https://github.com/Socialpranker/deepdive.git \
  ~/.claude/skills/deepdive
```

No build, no dependencies for *using* the skill — Claude runs it with its own
WebSearch / WebFetch / sub-agent tools. (Python is only for the maintainer-side
catalog/eval checks; you don't need it to run research.)

## 2. Invoke it

In a Claude Code session, just ask in natural language — any of these trigger it:

> «проведи ресёрч: <your question>»  ·  "deep research <your question>"  ·  "deep dive <your question>"

Claude will: restate your question, pick a report genre, write a `plan.md`, search
across <!--gen:count:channels-->29<!--/gen--> channels and <!--gen:count:stat_sources-->460<!--/gen-->
curated stat sources (+ <!--gen:count:api-->39<!--/gen-->+ APIs), score and triangulate every
source via a claims-ledger, synthesize with a multi-angle red team, and verify citations.

## 3. What you get

A folder (default `~/deep-research/<slug>/`) you can return to months later:

```
<slug>/
├── plan.md              # the research plan: question, hypotheses, acceptance criteria
├── sources/             # one file per source — verbatim quotes + credibility scoring
│   ├── 01_<slug>.md
│   └── ...
├── <date>_<genre>.md    # the final report — every claim traces to a source file
└── refresh_targets.md   # entities/numbers to re-check later via `update <slug>`
```

Every claim cites a source file; every source carries Credibility / Recency / Bias
scores. That's the point: not an answer you have to trust, but an investigation you
can audit.

## Next steps

- Full methodology: [`SKILL.md`](SKILL.md) — the <!--gen:count:phases-->9<!--/gen-->-phase workflow.
- The catalog: [`references/`](references/) — <!--gen:count:blocks-->105<!--/gen--> report
  blocks, <!--gen:count:genres-->6<!--/gen--> genres.
- Want to add sources or APIs? [`CONTRIBUTING.md`](CONTRIBUTING.md).
