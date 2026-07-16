# Runtime citation verification — Phase 6.5

> Drop-in addition to the workflow. Moves citation integrity from an *eval-only*
> afterthought into the live pipeline, so **every** medium/deep run self-verifies
> its sources before the report is declared done. This is the skill's one defensible
> moat — closed products (ChatGPT DR, Perplexity) cannot show per-source resolution.
> Make it run every time, not once in the repo.

## Where it slots in

Insert between Phase 6 (Synthesis + adversarial) and the finish-up step. The report
is written but not yet "done" until it carries a verification header.

```
... Phase 6 synthesis writes <date>_<genre>.md
→ Phase 6.5 VERIFY (this file)
→ finish-up (show path, summary)
```

## Procedure (the skill runs this itself)

1. After the report and `sources/` (or `sources.csv`) are written, run the existing
   deterministic checker against the run directory:

   ```bash
   python eval/check_citations.py --research-dir <run-dir> --json \
     --out <run-dir>/.verify/citations
   ```

   (The script ignores env proxies and retries transport flaps once — a dead OPEN
   source is a confirmed red flag, a timeout is UNKNOWN and not penalised.)

   **Standalone fallback (no `eval/` shipped).** When the skill is installed on its own
   (only `SKILL.md` + `references/`), `eval/check_citations.py` is absent — do liveness
   manually, no script needed:
   - For each source with `access: OPEN`, WebFetch its URL:
     - 2xx/3xx (or 401/403 = alive-but-auth) → live.
     - 404 / dead / DNS-fail → **red flag** (likely hallucinated or stale URL).
     - timeout / transport error → UNKNOWN; retry once, then leave UNKNOWN (no penalty).
   - `access: paywalled / closed / archive-restored` + non-200 → expected, **not** a flag.
   - Compute `liveness_integrity = live / checkable` by hand; apply the same depth gate
     and floor (0.70) below. Identical result to the script, just slower.

2. Read back `<run-dir>/.verify/citations.json`. Extract `citation_integrity`,
   the count of `red_flag: true` results, and their source ids/urls.

3. **Insert a verification header** at the top of the final report, right under the
   title (block F10 below).

4. **Act on red flags — do not just report them.** For each OPEN source confirmed
   dead (likely hallucinated or stale URL):
   - Re-search for the claim it supported.
   - Either replace the URL with a live source, or, if no source can be found,
     **demote every thesis that depended on it** (lower confidence, or move to Open
     Questions). A claim whose only support is a dead link is not a finding.
   - Re-run step 1 after fixes. Loop until red flags are resolved or explicitly
     accepted with a written reason.

5. **Gate by depth** (mirrors the adversarial-pass minimums):
   - `shallow` — verification optional; if run, header is informational.
   - `medium` — required; integrity **< 0.70 blocks finish** until red flags fixed
     or each is justified in writing. 0.70 is the rubric's `citation_floor`.
   - `deep` — required; **zero unresolved red flags** allowed. Every OPEN source must
     resolve or be replaced.

## Layer 2 — Faithfulness (does the source actually support the claim?)

Liveness (above) only proves the URL resolves. The dominant failure mode in the
literature is different: the link is live but the source **does not support** the
claim attached to it (citation ≠ entailment; CiteGuard / CiteCheck). A live URL can
still back a fabricated or overstated claim.

Run this AFTER liveness, reusing quotes already on disk. **No re-fetch in the common case.**

**Where the (claim, quote) pairs come from — use `evidence/` from Phase 5.5, don't rebuild it.**
Phase 5.5 (Evidence filter) already wrote `evidence/CN.md` grouping the relevant-only
quotes under each `claim_id`. That IS the input for faithfulness — one pass over each
`evidence/CN.md` yields exactly the (claim, source, quote) tuples to judge, no need to
re-scan `sources/NN.md` deciding which quote belongs to which claim (that would redo 5.5).
- medium/deep — `evidence/` exists → read pairs from there.
- shallow — 5.5 is skipped, no `evidence/`; faithfulness is optional. If run, pull the
  supporting quote directly from `sources/NN.md` per the claim it backs.

1. **Judge each (claim, quote) pair — does the quote entail the claim?** Decompose the
   claim into its atomic assertions (RAGAS-style) and check the quote supports each; a
   claim is only SUPPORTED if ALL its atomic parts are backed (ALCE citation recall).
   - SUPPORTED — quote directly backs every atomic part of the claim.
   - PARTIAL — quote backs the topic but is weaker/narrower than the claim (overclaim),
     or backs some atomic parts but not all.
   - UNSUPPORTED — quote does not back the claim (citation misuse / hallucination).

   Judge prompt (per pair):
   > Claim: "<claim text>"
   > Source quote: "<verbatim quote from evidence/CN.md>"
   > Does the quote support the claim? Decompose the claim into atomic assertions.
   > Answer SUPPORTED only if the quote backs ALL of them; PARTIAL if it backs the topic
   > but is narrower/weaker or backs only some; UNSUPPORTED if it does not back the claim.
   > Output: {verdict, unsupported_parts: [...], reason: "<one line>"}.

2. Model: `haiku`/low (runs on every pair); escalate disputed/UNSUPPORTED pairs to
   `sonnet`/medium on deep. NOTE: this is an LLM judge with its own error rate — judge
   against the verbatim quote (not the summary), default to PARTIAL when unsure, and
   treat one UNSUPPORTED verdict as a flag to re-check, not as ground truth.
3. Act, don't just score:
   - PARTIAL → soften the claim to match the source, or find a stronger source.
   - UNSUPPORTED → re-search for real support; if none, demote the thesis to Open
     Questions. A claim with no entailing source is not a finding.
4. **Write verdicts to a machine-readable artifact** — `.verify/faithfulness.json` (the
   I/O contract, mirrors `.verify/citations.json` for liveness):
   ```json
   {
     "faithfulness_integrity": 0.87,
     "results": [
       {"claim_id": "C1", "source_id": "07", "verdict": "SUPPORTED", "model": "haiku",
        "unsupported_parts": [], "reason": "quote states the figure directly"},
       {"claim_id": "C4", "source_id": "12", "verdict": "PARTIAL", "model": "haiku",
        "unsupported_parts": ["\"fastest-growing\""], "reason": "quote shows growth, not rank"}
     ]
   }
   ```
   `faithfulness_integrity = SUPPORTED / total` — a SECOND integrity axis, separate from
   liveness. Also render a human-readable `.verify/faithfulness.md` for the header link.
   **This artifact is the single source of truth for faithfulness** — `rubric.md` axis 3
   and the F10 header both READ it, neither recomputes it (see "I/O contract" below).
5. Depth gate:
   - `shallow` — optional (no `evidence/` to read from).
   - `medium` — required; any UNSUPPORTED on a hypothesis-bearing claim blocks finish.
   - `deep` — required; zero UNSUPPORTED; every PARTIAL softened or re-sourced.

**Two axes, one verdict:** liveness (URL alive) × faithfulness (source backs claim).
A citation counts as verified only if it passes BOTH.

## Block F10 — Verification header (add to `references/blocks/frame.md`)

> Renumbered from F9 to F10 (2026-07-07): F9 was claimed by the `background` block
> (see `references/blocks/frame.md`) merged from the deepdive-v2 design doc before this
> header was actually implemented in `frame.md`. No functional change — same header,
> same content, next free slot.

Rendered at the very top of the final report. **Carries BOTH axes** (liveness ×
faithfulness) — a citation is verified only if it passes both:

```markdown
> **Citation integrity: 21/23 live · faithfulness 20/22 supported · 0 red flags · 2 paywalled**
> Verified <YYYY-MM-DD>: liveness via check_citations.py (every OPEN source resolved live);
> faithfulness via Layer 2 judge over evidence/ (2 PARTIAL softened).
> [liveness detail](.verify/citations.md) · [faithfulness detail](.verify/faithfulness.md)
```

When flags were found and resolved (either axis):

```markdown
> **Citation integrity: 23/23 live · faithfulness 23/23 supported · 1 red flag + 1 overclaim resolved**
> s14 (dead URL → replaced <date>); C4 (PARTIAL → claim softened to match source).
```

When an axis is below floor and the user chose to ship anyway (medium only):

```markdown
> ⚠ **Citation integrity: liveness 0.64 · faithfulness 0.71 — liveness below floor (0.70).**
> s07, s11 (transport UNKNOWN), s19 (OPEN dead → claim demoted); C9 (UNSUPPORTED → Open Questions).
```

(shallow: faithfulness line omitted — Layer 2 optional, no `evidence/`.)

## I/O contract — who writes, who reads (no circular reference)

Faithfulness has ONE producer and several consumers. Before this contract, both the F10
header and `rubric.md` axis 3 *referred* to faithfulness verdicts as a ready input, but
nothing produced them — a circular reference to a missing artifact. The contract fixes it:

| Artifact | Producer | Consumers |
|---|---|---|
| `.verify/citations.json` | Phase 6.5 Layer 1 (`check_citations.py`) | F10 header, `rubric.md` axis "citation" |
| `.verify/faithfulness.json` | Phase 6.5 Layer 2 (this file, step 4) | F10 header (2nd axis), `rubric.md` axis 3 "Factual accuracy" |
| `evidence/CN.md` | **Phase 5.5** (`evidence_filter.md`) | Phase 6.5 Layer 2 INPUT (claim↔quote pairs) |

Rules:
- Layer 2 **produces** `.verify/faithfulness.json`; it is the single source of truth.
- The F10 header and `rubric.md` axis 3 **read** it — neither recomputes verdicts. If the
  file is absent (shallow, or Layer 2 skipped), axis 3 records "not run", not zero.
- Layer 2 **reads** `evidence/CN.md` for pairs — it does not re-derive claim↔quote from
  raw `sources/NN.md` (that is Phase 5.5's job; redoing it duplicates 5.5).
- `claim_id` is the join key across all three artifacts. If synthesis (Phase 6) rephrased
  or merged claims, keep the originating `claim_id` on each thesis so the join holds.

## Why act, not just measure

The eval harness *scores* integrity after the fact. Runtime verification *changes the
report*: a dead OPEN link doesn't lower a number — it forces a re-search or a demoted
claim. That difference is the entire value proposition. A research tool that quietly
keeps a hallucinated citation is worse than no tool; one that catches and repairs it
in the same run is something no closed product offers.

## SKILL.md insert

Add to the "Workflow — 11 фаз" list, after Phase 6:

```
6.5. **Verify** [`haiku`/low] — две оси: (1) **liveness** — `check_citations.py` (URL жив?),
     (2) **faithfulness** — entailment claim ⊨ цитата (пары берутся из `evidence/CN.md` Фазы 5.5;
     источник реально подтверждает тезис?). Вердикты → `.verify/faithfulness.json` (I/O-контракт),
     verification-header F10 несёт ОБЕ оси. Флаги: re-search / demote claim / смягчить overclaim.
     medium: integrity < 0.70 ИЛИ UNSUPPORTED на гипотезе блокирует finish; deep: ноль red flags
     и ноль UNSUPPORTED. См. `references/runtime_verification.md`.
```

And to "Что НЕ делать":

```
- Не финишировать medium/deep без verification-прохода — висящая мёртвая OPEN-ссылка
  это либо галлюцинация, либо протухший источник; чини или понижай тезис.
```
