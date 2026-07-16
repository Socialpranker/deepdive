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

Run this AFTER liveness, reusing what `sources/NN.md` already stores — the supporting
quote(s) per source. No re-fetch in the common case.

1. For each thesis↔citation pair, take the claim and the stored quote from
   `sources/NN.md`. Ask: **does the quote entail the claim?**
   - SUPPORTED — quote directly backs the claim.
   - PARTIAL — quote is related but weaker/narrower (overclaim).
   - UNSUPPORTED — quote does not back the claim (citation misuse / hallucination).
2. Model: `haiku`/low (runs on every pair); escalate disputed pairs to `sonnet`/medium
   on deep. NOTE: this is an LLM judge with its own error rate — calibrate the prompt
   on a small labelled set; treat one UNSUPPORTED verdict as a flag to re-check, not
   as ground truth.
3. Act, don't just score:
   - PARTIAL → soften the claim to match the source, or find a stronger source.
   - UNSUPPORTED → re-search for real support; if none, demote the thesis to Open
     Questions. A claim with no entailing source is not a finding.
4. Output a second integrity axis — `faithfulness_integrity = SUPPORTED / total` —
   separate from liveness. The F10 header carries both.
5. Depth gate:
   - `shallow` — optional.
   - `medium` — required; any UNSUPPORTED on a hypothesis-bearing claim blocks finish.
   - `deep` — required; zero UNSUPPORTED; every PARTIAL softened or re-sourced.

**Two axes, one verdict:** liveness (URL alive) × faithfulness (source backs claim).
A citation counts as verified only if it passes BOTH.

## Block F10 — Verification header (add to `references/blocks/frame.md`)

> Renumbered from F9 to F10 (2026-07-07): F9 was claimed by the `background` block
> (see `references/blocks/frame.md`) merged from the deepdive-v2 design doc before this
> header was actually implemented in `frame.md`. No functional change — same header,
> same content, next free slot.

Rendered at the very top of the final report:

```markdown
> **Citation integrity: 21/23 verified · 0 red flags · 2 paywalled (expected)**
> Verified <YYYY-MM-DD> via check_citations.py. Every OPEN source resolved live.
> [verification detail](.verify/citations.md)
```

When red flags were found and resolved:

```markdown
> **Citation integrity: 23/23 verified · 1 red flag resolved**
> s14 (original URL dead → replaced with live source on <date>).
```

When integrity is below floor and the user chose to ship anyway (medium only):

```markdown
> ⚠ **Citation integrity: 0.64 — below floor (0.70).** 3 sources unverifiable:
> s07, s11 (transport UNKNOWN), s19 (OPEN dead, claim demoted to Open Questions).
```

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
     (2) **faithfulness** — entailment claim ⊨ цитата из `sources/NN.md` (источник реально
     подтверждает тезис?). Вставить verification-header (F10), отработать флаги: re-search /
     demote claim / смягчить overclaim. medium: integrity < 0.70 ИЛИ UNSUPPORTED на гипотезе
     блокирует finish; deep: ноль red flags и ноль UNSUPPORTED. См. `references/runtime_verification.md`.
```

And to "Что НЕ делать":

```
- Не финишировать medium/deep без verification-прохода — висящая мёртвая OPEN-ссылка
  это либо галлюцинация, либо протухший источник; чини или понижай тезис.
```
