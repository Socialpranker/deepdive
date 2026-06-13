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

2. Read back `<run-dir>/.verify/citations.json`. Extract `citation_integrity`,
   the count of `red_flag: true` results, and their source ids/urls.

3. **Insert a verification header** at the top of the final report, right under the
   title (block F9 below).

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

## Block F9 — Verification header (add to `references/blocks/frame.md`)

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

Add to the "Workflow — 9 фаз" list, after Phase 6:

```
6.5. **Verify** [`haiku`/low, deterministic] — прогнать `check_citations.py` на готовом
     run-dir, вставить verification-header (блок F9) в отчёт, отработать red flags
     (re-search или demote claim). medium: integrity < 0.70 блокирует finish.
     deep: ноль нерешённых red flags. См. `references/runtime_verification.md`.
```

And to "Что НЕ делать":

```
- Не финишировать medium/deep без verification-прохода — висящая мёртвая OPEN-ссылка
  это либо галлюцинация, либо протухший источник; чини или понижай тезис.
```
