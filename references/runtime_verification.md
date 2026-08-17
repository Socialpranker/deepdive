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

## Layer 3 — Qualifier preservation (does the REPORT still say what the claim said?)

Layers 1 and 2 both stop at `claims.csv`. Neither looks at what synthesis then WROTE.
That is where the dominant class of errors actually happens: the ledger row is correct,
and the qualifier is dropped on the way into the TL;DR.

Two real examples, both from a run that passed Layers 1-2 cleanly:

| In `claims.csv` (correct) | In the TL;DR (broken) | Defect |
|---|---|---|
| "F1 = 1.000 **on fixtures with embedded structured state**" | "F1 = 1.000 everywhere" | scope qualifier dropped — the real SPA figure was 0.014 |
| "54% **of pages** contain ≥1 dead link" | "54% of links are dead" | per-page prevalence silently became per-link rate |

Both would pass Layer 2: the source genuinely backs the ledger row. The distortion is
downstream of the pair Layer 2 judges. **This is a different question, so it needs a
different pass** — not a stricter version of Layer 2.

Run AFTER Layer 2, on the written report. No re-fetch, no source reading: this pass
compares two artifacts you already have on disk.

**Scope — the highest-risk short texts, not the whole report.** Distortion costs most
where the text is read first and quoted onward, and short texts are cheap to check:
- block F1 (TL;DR),
- `memo.md`,
- block Z12 (`so-what-for-you`).

Everything else is out of scope for this layer — the adversarial pass (Phase 6) covers
the body. Checking the full report here would swap a cheap mechanical pass for an
expensive one and duplicate red team.

1. **Pair each statement with its ledger row.** `claim_id` is the join key (see "I/O
   contract" below — synthesis is already required to keep it on each thesis). A
   statement in F1/`memo.md`/Z12 carrying a number, a comparison, or a hypothesis
   verdict but NO resolvable `claim_id` is itself a finding: `UNTRACEABLE`. It means
   synthesis asserted something the ledger does not carry.

2. **Judge each (ledger claim, report statement) pair.** The question is NOT "is it
   true" (Layer 2) and NOT "is it shorter" — compression is legitimate and expected.
   The question is whether a limit on scope was removed.

   Judge prompt (per pair):
   > Ledger claim: "<claim text from claims.csv>"
   > Report statement: "<statement as written in the report>"
   >
   > Does the report statement stay within the scope of the ledger claim?
   > List every qualifier in the ledger claim — conditions ("on fixtures with X"),
   > units of measure ("of pages" vs "of links"), populations ("in the EU"), time
   > bounds ("as of 2026-02"), hedges ("up to", "in our single run").
   > For each: is it preserved, or dropped/widened in the report statement?
   > Shortening is NOT a defect. Removing a limit IS.
   > Answer PRESERVED only if every qualifier survives or the statement is narrower.
   > Output: {verdict, dropped_qualifiers: [...], reason: "<one line>"}.

   - `PRESERVED` — every scope limit survives, or the statement is narrower than the claim.
   - `BROADENED` — a hedge, bound, or condition was removed; the statement now asserts
     more than the ledger supports (the "F1 = 1.000 everywhere" case).
   - `SCOPE-DROPPED` — unit, population, or measured entity silently changed (the
     "54% of pages" → "54% of links" case). Worse than BROADENED: the statement is not
     an overreach of the claim, it is a different claim.
   - `UNTRACEABLE` — no resolvable `claim_id` for a load-bearing statement.

3. **Default to PRESERVED when unsure.** Symmetric to Layer 2's default-to-PARTIAL:
   this pass must not punish normal editing. A false BROADENED on every compressed
   sentence makes the layer noise and it will be switched off. Judge the removal of a
   LIMIT, not the loss of words.

4. Model: `haiku`/low — comparing two short texts. Escalate `BROADENED` and
   `SCOPE-DROPPED` to `sonnet`/medium on deep.

5. **Act, don't just score** (same discipline as Layers 1-2):
   - `BROADENED` → restore the qualifier in the report. Do NOT weaken the ledger row to
     match the report — the ledger is upstream and was verified; the report is what drifted.
   - `SCOPE-DROPPED` → rewrite the statement to the claim's actual unit/population.
   - `UNTRACEABLE` → either point the statement at a real `claim_id`, or delete it. An
     assertion with no ledger row behind it did not pass Layers 1-2 at all.

6. **Write `.verify/qualifiers.json`** (mirrors `faithfulness.json`):
   ```json
   {
     "qualifier_integrity": 0.91,
     "results": [
       {"claim_id": "CL2", "location": "F1", "verdict": "PRESERVED", "model": "haiku",
        "dropped_qualifiers": [], "reason": "statement narrower than claim"},
       {"claim_id": "CL7", "location": "memo.md", "verdict": "BROADENED", "model": "haiku",
        "dropped_qualifiers": ["\"on fixtures with embedded structured state\""],
        "reason": "claim scoped to fixtures, statement says everywhere"},
       {"claim_id": "CL9", "location": "F1", "verdict": "SCOPE-DROPPED", "model": "haiku",
        "dropped_qualifiers": ["\"of pages\""],
        "reason": "per-page prevalence restated as per-link rate"}
     ]
   }
   ```
   `qualifier_integrity = PRESERVED / total`. Also render `.verify/qualifiers.md` for the
   header link. **Single source of truth for this axis** — the F10 header READS it.

7. Depth gate:
   - `shallow` — optional; if run, informational (F1 is tiny, `memo.md` is 5-10 lines).
   - `medium` — required; any `SCOPE-DROPPED`, or `BROADENED` on a hypothesis-bearing
     claim, blocks finish.
   - `deep` — required; zero `SCOPE-DROPPED`, zero `UNTRACEABLE`; every `BROADENED`
     restored.

**Why a separate pass and not a synthesis instruction.** Phase 6 already tells synthesis
to carry conditions of applicability and to take `confidence` from `claims.csv`. That
instruction did not prevent either example above — because it asks the writing model to
audit its own text, which is the one thing the red team lesson says does not work
("не ловятся перечитыванием черновика"). Layer 3 is an external mechanical comparison of
two artifacts, by a different model, after the fact. That is the class of check that does.

## Layer 4 — Construct provenance (does the NAME in the report exist outside it?)

Layers 1-3 all join on `claim_id`: they verify statements that have a ledger row. A
report says more than its claims. It says *"по фреймворку RACE"*, *"это классический
trade-off Хофштадтера"*, *"в литературе это называют cold-start decay"* — named
frameworks, taxonomies, laws, effects, metrics, patterns. Such a name has no
`claim_id`, carries no number, quotes no source, and therefore passes every layer
above untouched — including when nothing by that name exists.

This is the single most frequent generation failure measured on deep-research agents:
**strategic content fabrication — 18.95% of all errors** (FINDER/DEFT taxonomy,
[arXiv 2512.01948](https://arxiv.org/abs/2512.01948); generation failures 38.76%
total, the largest of the three groups). It is not a hallucinated citation — the
citations may all resolve. It is a plausible construct presented as established.

**Procedure** (`haiku`/low; medium/deep required, shallow optional):

1. **Collect candidates from the final report + `memo.md`.** A candidate is any
   *named* abstraction: capitalized multi-word names (`Research-Synthesis
   framework`), quoted terms introduced as known (`«эффект храповика»`), acronyms
   (`RACE`, `FACT`, `DEFT`), «правило/закон/эффект/паттерн/индекс <имя>», «методология
   <имя>». NOT candidates: numbers (Layer 4 does not duplicate arithmetic), product
   and organization names present in `sources.csv`, common domain vocabulary.
2. **For each candidate, look for the name in `evidence/` and `sources/NN.md`** —
   the same body of quotes Layer 2 works over. Verdict:
   - `sourced` — a source uses this name for this thing; record the `[sNN]`.
   - `author-construct` — it is OUR generalization (we coined it to organize the
     report). Legal, but the report must mark it as ours in the text: «назовём это
     …», «наша рамка», «в этом отчёте — …».
   - `unsourced` — presented as if established in the field, no source uses it.
3. **Act:** `unsourced` is not softened, it is resolved — find the source, restate it
   as `author-construct` with an explicit marker, or delete it. An `unsourced`
   construct in `memo.md` / F1 / F9 **blocks finish** (medium/deep): the memo is what
   the consumer's process ingests, and an invented framework there travels further
   than any single wrong number.
4. **Write `.verify/constructs.json`:**
   ```json
   {
     "construct_integrity": 0.86,
     "results": [
       {"name": "IterResearch", "status": "sourced", "sources": ["s07"],
        "locations": ["E3"], "reason": "s07 uses the name for this paradigm"},
       {"name": "провенанс-разрыв", "status": "author-construct", "sources": [],
        "locations": ["memo.md"], "reason": "our label; marked «назовём это» in text"},
       {"name": "закон Кэмпбелла для агентов", "status": "unsourced", "sources": [],
        "locations": ["F1"], "reason": "no source names this; presented as established"}
     ]
   }
   ```
   `construct_integrity = (sourced + author-construct) / total`. An
   `author-construct` counts as integrity ONLY if the text marks it — an unmarked one
   is `unsourced` by definition, since the reader cannot tell them apart.

**Why not the red team.** R1 attacks whether an argument holds, R3 whether coverage
has holes, R5 whether the minority was crushed. None of them checks that a *name*
refers to something outside this document — they argue with the content as given.
Layer 4 is the same species of check as Layer 3: mechanical comparison of the report
against a corpus, by a model that did not write it.

## Block F10 — Verification header (add to `references/blocks/frame.md`)

> Renumbered from F9 to F10 (2026-07-07): F9 was claimed by the `background` block
> (see `references/blocks/frame.md`) merged from the deepdive-v2 design doc before this
> header was actually implemented in `frame.md`. No functional change — same header,
> same content, next free slot.

Rendered at the very top of the final report. **Carries ALL FOUR axes** (liveness ×
faithfulness × qualifiers × constructs) — the chain is source → claim → report, and a
break anywhere in it means the statement is not verified:

```markdown
> **Citation integrity: 21/23 live · faithfulness 20/22 supported · qualifiers 22/22 preserved · constructs 7/7 sourced · 0 red flags · 2 paywalled**
> Verified <YYYY-MM-DD>: liveness via check_citations.py (every OPEN source resolved live);
> faithfulness via Layer 2 judge over evidence/ (2 PARTIAL softened); qualifiers via Layer 3
> over F1/memo.md/Z12 (no scope drift); constructs via Layer 4 (1 marked as ours).
> [liveness detail](.verify/citations.md) · [faithfulness detail](.verify/faithfulness.md) · [qualifier detail](.verify/qualifiers.md) · [construct detail](.verify/constructs.md)
```

When flags were found and resolved (any axis):

```markdown
> **Citation integrity: 23/23 live · faithfulness 23/23 supported · qualifiers 21/23 preserved · 1 red flag + 1 overclaim + 2 qualifiers restored**
> s14 (dead URL → replaced <date>); C4 (PARTIAL → claim softened to match source);
> CL7 (BROADENED → "on fixtures with embedded state" restored in TL;DR).
```

When an axis is below floor and the user chose to ship anyway (medium only):

```markdown
> ⚠ **Citation integrity: liveness 0.64 · faithfulness 0.71 · qualifiers 0.88 — liveness below floor (0.70).**
> s07, s11 (transport UNKNOWN), s19 (OPEN dead → claim demoted); C9 (UNSUPPORTED → Open Questions).
```

(shallow: faithfulness line omitted — Layer 2 optional, no `evidence/`. Qualifier and
construct lines omitted unless Layers 3-4 were run.)

### Second line — source independence (medium/deep)

The three axes above answer "did the source say this, and does the report still say
what the ledger said". They say nothing about **who the sources are and whether their
agreement is real**. That is a separate line, computed from `.verify/authority.json`,
`claims.csv` and the round notes in `plan.md` §15 — never recomputed by hand:

```markdown
> **Source independence: authority 12/14 qualified (2 quarantined) · numbers 9/9 dated ·
> overlap 0.12 · 0 circulation flags · 1 contested claim**
> s11, s23 quarantined (no author, origin unknown) — neither is a sole support.
> CL6 contested: minority s60 (regulator filing) vs 3 secondary — both positions in §4.
```

Read each figure as a failure signal, not a score:

| Figure | Source | What a bad value means |
|---|---|---|
| `authority N/M qualified` | `.verify/authority.json` | несущие пары, прошедшие чек-лист; низкая доля = выводы стоят на источниках, чьё право утверждать не подтверждено |
| `quarantined` | там же | `unknown`-вердикты; каждый обязан иметь второй источник под claim |
| `numbers N/N dated` | `claims.csv` `as_of` | числа без даты замера; неполнота = fail-closed, число не идёт в memo |
| `overlap` | `plan.md` §15, `overlap_rate` | > 0.3 = агенты искали одинаково, разнообразие источников фиктивное |
| `circulation flags` | `check_number_provenance.py` | одно значение при разных корнях = ложная независимость или неверный `root` |
| `contested claims` | `claims.csv` status | claim, где меньшинство не погашено; **ноль в спорной теме подозрителен**, а не хорош |

Последняя строка таблицы — важнейшая: отчёт без единого `contested` по конфликтной
теме обычно означает не согласие источников, а то, что несогласных не искали.
Метрика, которую можно улучшить, перестав делать работу, — не метрика; поэтому
`contested` читается в паре с покрытием, а не как «чем меньше, тем лучше».

## I/O contract — who writes, who reads (no circular reference)

Faithfulness has ONE producer and several consumers. Before this contract, both the F10
header and `rubric.md` axis 3 *referred* to faithfulness verdicts as a ready input, but
nothing produced them — a circular reference to a missing artifact. The contract fixes it:

| Artifact | Producer | Consumers |
|---|---|---|
| `.verify/citations.json` | Phase 6.5 Layer 1 (`check_citations.py`) | F10 header, `rubric.md` axis "citation" |
| `.verify/faithfulness.json` | Phase 6.5 Layer 2 (this file, step 4) | F10 header (2nd axis), `rubric.md` axis 3 "Factual accuracy" |
| `.verify/qualifiers.json` | Phase 6.5 Layer 3 (this file, step 6) | F10 header (3rd axis) |
| `.verify/constructs.json` | Phase 6.5 Layer 4 (this file, step 4) | F10 header (4th axis), phase-gate. Absent ⇒ axis never ran, NOT "nothing fabricated" |
| `numbers.csv` | Phase 6 (synthesis, `source_scoring.md`) | `check_number_arithmetic.py`, F10 second line (`numbers dated`) |
| `evidence/CN.md` | **Phase 5.5** (`evidence_filter.md`) | Phase 6.5 Layer 2 INPUT (claim↔quote pairs) |
| `.verify/authority.json` | **Phase 5.5** authority axis (`evidence_filter.md`) | F10 second line, phase-gate. Absent ⇒ axis never ran (fail-closed), NOT "all qualified" |
| `claims.csv` + written report | Phase 5 / Phase 6 | Phase 6.5 Layer 3 INPUT (claim↔statement pairs) |

Rules:
- Layer 2 **produces** `.verify/faithfulness.json`; it is the single source of truth.
- Layer 3 **produces** `.verify/qualifiers.json`; likewise. The F10 header reads it and
  does not recompute. Absent (shallow, or Layer 3 skipped) → "not run", not zero.
- The F10 header and `rubric.md` axis 3 **read** it — neither recomputes verdicts. If the
  file is absent (shallow, or Layer 2 skipped), axis 3 records "not run", not zero.
- Layer 2 **reads** `evidence/CN.md` for pairs — it does not re-derive claim↔quote from
  raw `sources/NN.md` (that is Phase 5.5's job; redoing it duplicates 5.5).
- Layer 3 **reads** `claims.csv` and the written report — never `sources/`. Whether the
  source backs the claim is Layer 2's question, already answered upstream.
- `claim_id` is the join key across all artifacts. If synthesis (Phase 6) rephrased
  or merged claims, keep the originating `claim_id` on each thesis so the join holds.
  **Layer 3 depends on this directly**: a statement whose `claim_id` was dropped in
  synthesis is not "unchecked", it is `UNTRACEABLE` and blocks finish on deep.

**Four axes, one chain:** source → claim → report → its own vocabulary. Layer 1 proves
the source resolves, Layer 2 that it backs the claim, Layer 3 that the report still says
what the claim said, Layer 4 that the names the report uses exist outside it. A statement
is verified only if all four hold — and each layer is checked by a different pass over
different inputs, so a defect that hides from one is visible to another.

Layers 1-3 all join on `claim_id`, which is exactly why Layer 4 is needed: everything
a report asserts *without* a ledger row — a framework, a taxonomy, a named effect —
is invisible to a join-based check, and that is the largest measured class of
generation defect.

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
