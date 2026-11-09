#!/usr/bin/env python3
"""
Phase-gate validator for a completed deepdive run directory.

The methodology in references/ is executed only by the model's discipline inside a
Claude Code session — nothing forces a phase to actually run. This script closes
that gap: it checks that a finished run's output folder contains the file artifact
of every phase that is MANDATORY for the run's depth mode. It catches "the model
skipped a phase" — the failure mode the whole skill is most exposed to (H3).

Depth mode drives which phases are mandatory. The source of truth for that is the
`depth_gate` field in phases.yaml (loaded via phases_manifest — no second YAML
parser). This script owns only the phase->artifact mapping, because not every phase
emits a file and some emit an either/or or a set of files, which does not fit a
scalar YAML field.

It validates PHASE COMPLETENESS, not artifact format (that's eval/validate_structure.py)
and not research quality (that's eval/score_run.py). The two structural validators
are complementary: run both.

Checks (errors fail --strict; warnings never do):
  - every phase mandatory for the mode emitted its artifact(s)
  - medium/deep: read-set size and sphere quotas, candidates.csv breadth
  - mode is known explicitly (--mode) or read from the report/plan frontmatter
  - the phase->artifact table still covers every file-emitting phase in phases.yaml
    (a self-check: adding such a phase without updating this table warns loudly)

Usage:
    python scripts/validate_phases.py --research-dir research/<slug>
    python scripts/validate_phases.py --research-dir research/<slug> --mode deep
    python scripts/validate_phases.py --research-dir research/<slug> --strict   # exit 1 on errors
    python scripts/validate_phases.py --research-dir research/<slug> --json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phases_manifest  # noqa: E402
from quiet import CAP_ERRORS, CAP_WARNINGS, capped  # noqa: E402

MODES = ("shallow", "medium", "deep")
# depth_gate = the MINIMUM mode at which a phase is mandatory. A phase applies to a
# run when the run's mode is at least its gate. Ranked so we can compare.
GATE_RANK = {"shallow": 0, "medium": 1, "deep": 2}

# Phase id -> what a completed run must contain when that phase is mandatory.
# `any_of`: at least one of these paths must exist (relative to the run dir).
# `all_of`: every one of these paths must exist.
# `medium_of`: required from medium up — for artifacts of a phase that itself runs at
#              every depth but whose bookkeeping is not worth it on a shallow run.
# A directory entry (trailing kind="dir") must be a non-empty directory.
# Phases with no file output (reframing/genre/capability/plan-gate) are absent here
# on purpose; the self-check below knows they are intentionally artifact-less.
PHASE_ARTIFACTS: dict[str, dict[str, list[str]]] = {
    "3": {"all_of": ["plan.md"]},
    # state.md is the round workspace, rewritten (not appended) each round — the
    # orchestrator plans the next round from it instead of from the transcript.
    # candidates.csv is the wide, unread pool (title+snippet) that the read set is
    # picked from by sphere quotas — without it breadth is whatever search returned.
    "4": {"any_of": ["sources", "sources.csv"], "medium_of": ["state.md", "candidates.csv"]},
    "5": {"all_of": ["claims.csv"]},
    # 5.5 filters the INPUT to synthesis on two axes: relevance (evidence/) and
    # authority (.verify/authority.json). The authority verdicts are fail-closed —
    # an absent file means the axis never ran, not that everything qualified.
    "5.5": {"all_of": ["evidence", ".verify/authority.json"]},
    # 5.7 leaves the candidate pairs it built against the cross-run wiki. Fail-closed
    # for the same reason as authority.json: an absent file means the run never
    # confronted what earlier researches established, not that nothing conflicted.
    "5.7": {"all_of": [".verify/wiki_pairs.json"]},
    # Phase 6 emits the dated <YYYY-MM-DD>_<genre>.md report (matched by pattern)
    # AND the one-page decision memo the consumer's process actually ingests.
    # outline.md (section -> block -> claim_id) and numbers.csv (every figure the
    # report stands on) are the machine-checkable half of synthesis; both are
    # bookkeeping a shallow run is not asked to keep.
    # readout.md is the human version (page + full PDF): written after verify,
    # passed through humanizer-ru. Without it the run hands a reader the ledger.
    "6": {
        "report": [],
        "all_of": ["memo.md"],
        "medium_of": ["outline.md", "numbers.csv", "readout.md"],
    },
    # Layer 1 (liveness) / Layer 2 (faithfulness) / Layer 3 (qualifier preservation) /
    # Layer 4 (construct provenance). All four are required from medium up — 6.5's own
    # depth_gate is medium, so a shallow run never reaches this entry at all.
    "6.5": {
        "all_of": [
            ".verify/citations.json",
            ".verify/faithfulness.json",
            ".verify/qualifiers.json",
            ".verify/constructs.json",
        ]
    },
    "7": {"all_of": ["refresh_targets.md"]},
    # Phase 8 (decision walkthrough) must leave application.md with ANY status —
    # incl. `deferred`. The gate requires the file, not a made decision, so
    # unattended runs are never blocked on a human.
    "8": {"all_of": ["application.md"]},
}
# Phases that legitimately produce no file artifact — used only by the self-check so
# it does not flag them as an un-mapped file-emitting phase.
NO_FILE_PHASES = {"1", "2", "3.5", "3.7"}

REPORT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z]+\.md$")
MODE_RE = re.compile(r"^mode:\s*(\w+)", re.MULTILINE)
DIR_ARTIFACTS = {"sources", "evidence"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def detect_mode(d: Path) -> str | None:
    """Read `mode:` from the report frontmatter, falling back to plan.md."""
    dated = sorted(p for p in d.glob("*.md") if REPORT_RE.match(p.name))
    for candidate in (*dated, d / "plan.md"):
        if candidate.is_file():
            m = MODE_RE.search(candidate.read_text(encoding="utf-8"))
            if m and m.group(1).lower() in MODES:
                return m.group(1).lower()
    return None


def artifact_present(d: Path, rel: str) -> bool:
    p = d / rel
    if rel in DIR_ARTIFACTS:
        return p.is_dir() and any(p.iterdir())
    return p.is_file()


def has_report(d: Path) -> bool:
    return any(REPORT_RE.match(p.name) for p in d.glob("*.md"))


def check_phase(
    d: Path, phase_id: str, spec: dict[str, list[str]], mode: str, r: Report
) -> None:
    if "report" in spec:
        if not has_report(d):
            r.err(f"phase {phase_id}: no final report <YYYY-MM-DD>_<genre>.md")
        # no return: a phase may require the report AND fixed-name artifacts (6: memo.md)
    if "all_of" in spec:
        for rel in spec["all_of"]:
            if not artifact_present(d, rel):
                r.err(f"phase {phase_id}: missing required artifact '{rel}'")
    if "medium_of" in spec and GATE_RANK[mode] >= GATE_RANK["medium"]:
        for rel in spec["medium_of"]:
            if not artifact_present(d, rel):
                r.err(
                    f"phase {phase_id}: missing required artifact '{rel}' "
                    f"(required from medium up)"
                )
    if "any_of" in spec:
        if not any(artifact_present(d, rel) for rel in spec["any_of"]):
            joined = "' or '".join(spec["any_of"])
            r.err(f"phase {phase_id}: missing artifact (need '{joined}')")


SOURCE_FILE_RE = re.compile(r"^(\d+)_.+\.md$")
# Schema contract (references/source_scoring.md). Audit of 70 real runs found 26
# header variants of numbers.csv alone: every reader guessed columns by substring and
# the rules reading a missed column silently never fired. The header is now fixed at
# write time: core columns in this exact order, then only the listed optional tail.
CLAIMS_CORE = (
    "claim_id",
    "claim",
    "hypothesis",
    "sources",
    "source_types",
    "roots",
    "paths",
    "status",
    "confidence",
    "primary_source",
    "source_caveat",
    "dissent",
    "as_of",
)
CLAIMS_OPTIONAL = ("claim_class", "evidence_kind", "plain", "detail")
NUMBERS_CORE = (
    "num_id",
    "value",
    "unit",
    "kind",
    "formula",
    "inputs",
    "group",
    "claim_id",
    "sources",
    "as_of",
)
NUMBERS_OPTIONAL = ("label",)
# LLM-judge verdict files: one shape, so faithfulness is comparable across runs
# (audit: 0.26–1.0 across runs was not comparable — each run invented its own form).
VERDICT_FILES = {
    ".verify/faithfulness.json": {"SUPPORTED", "PARTIAL", "UNSUPPORTED"},
    ".verify/qualifiers.json": {
        "PRESERVED",
        "BROADENED",
        "SCOPE-DROPPED",
        "UNTRACEABLE",
    },
}
VERDICT_KEYS = ("claim_id", "verdict", "model")
# Artifacts that only a medium/deep run produces — used to infer the mode when the
# run never wrote a `mode:` frontmatter (2 of 12 real runs had one).
MEDIUM_MARKERS = (
    "state.md",
    "outline.md",
    "numbers.csv",
    "evidence",
    "refresh_targets.md",
    ".verify/authority.json",
    ".verify/wiki_pairs.json",
)
# SKILL.md depth table: shallow is 5–7 sources, medium starts at 12.
MEDIUM_SOURCE_COUNT = 10


def check_source_perimeter(d: Path, r: Report) -> None:
    """Each fetch sub-agent owns a disjoint id range, enforced only by prompt text.
    One number claimed by two files means an agent wrote outside its range (or two
    collided): a source file was silently overwritten, so sources.csv no longer
    describes what is on disk."""
    src = d / "sources"
    if not src.is_dir():
        return
    by_id: dict[str, list[str]] = {}
    for p in sorted(src.glob("*.md")):
        m = SOURCE_FILE_RE.match(p.name)
        if not m:
            r.warn(f"sources/{p.name}: name is not NN_slug.md — not indexable by id")
            continue
        by_id.setdefault(m.group(1).lstrip("0") or "0", []).append(p.name)
    for num, names in sorted(by_id.items()):
        if len(names) > 1:
            r.err(
                f"source id {num} claimed by {len(names)} files ({', '.join(names)}) — "
                f"a sub-agent wrote outside its assigned range; that agent's results "
                f"are not trustworthy, re-run it with a narrowed task"
            )


def infer_mode(d: Path) -> tuple[str, str]:
    """Best-effort depth from what the run left on disk. Never returns deep: on disk
    deep and medium are the same set of files, and guessing the stricter one would
    fail a run for a phase (3.5) that leaves no artifact."""
    present = [m for m in MEDIUM_MARKERS if artifact_present(d, m)]
    if present:
        return "medium", f"medium-only artifacts present: {', '.join(present)}"
    src = d / "sources"
    n = len(list(src.glob("*.md"))) if src.is_dir() else 0
    if n >= MEDIUM_SOURCE_COUNT:
        return "medium", f"{n} sources (shallow is 5–7)"
    return "shallow", f"no medium artifacts, {n} sources"


def resolve_mode(d: Path, explicit: str | None, r: Report) -> str:
    """Explicit flag > frontmatter > inference. A run with no `mode:` is validated
    anyway — refusing would let the least disciplined runs skip the gate entirely."""
    if explicit:
        return explicit
    found = detect_mode(d)
    if found:
        return found
    mode, why = infer_mode(d)
    r.warn(
        f"no 'mode:' frontmatter in report or plan.md — inferred '{mode}' ({why}); "
        f"add `mode: {mode}` to plan.md or pass --mode"
    )
    return mode


def header_violation(
    header: list[str], core: tuple[str, ...], optional: tuple[str, ...]
) -> str | None:
    """-> why `header` is not canonical, or None."""
    head = [c.strip() for c in header]
    if tuple(head[: len(core)]) != core:
        missing = [c for c in core if c not in head]
        if missing:
            return f"missing column(s) {', '.join(missing)}"
        return f"core columns out of order (expected {','.join(core)})"
    unknown = [c for c in head[len(core) :] if c not in optional]
    if unknown:
        return (
            f"unknown column(s) {', '.join(unknown)} after the core "
            f"(allowed: {', '.join(optional)})"
        )
    return None


def check_schema_contract(d: Path, r: Report) -> None:
    """A non-canonical ledger is not a formatting nit: the rule that reads a column
    it cannot find silently never fires — the 'green check, no behavior' failure."""
    for name, core, optional in (
        ("claims.csv", CLAIMS_CORE, CLAIMS_OPTIONAL),
        ("numbers.csv", NUMBERS_CORE, NUMBERS_OPTIONAL),
    ):
        path = d / name
        if not path.is_file():
            continue
        header = next(csv.reader(path.read_text(encoding="utf-8").splitlines()), None)
        if not header:
            r.err(f"{name} is empty")
            continue
        why = header_violation(header, core, optional)
        if why:
            r.err(
                f"{name}: {why} — the header is fixed by references/source_scoring.md; "
                f"rename/reorder the columns, do not invent new ones"
            )
    for rel, verdicts in VERDICT_FILES.items():
        path = d / rel
        if not path.is_file():
            continue  # presence is the phase-gate's business (6.5)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            r.err(f"{rel} is not valid JSON ({exc.msg})")
            continue
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list) or not results:
            r.err(f"{rel}: no non-empty `results` list — the layer left no verdicts")
            continue
        bad = []
        for i, item in enumerate(results):
            if not isinstance(item, dict):
                bad.append(f"#{i} not an object")
                continue
            empty = [k for k in VERDICT_KEYS if not str(item.get(k) or "").strip()]
            if empty:
                bad.append(f"#{i} lacks {'/'.join(empty)}")
            elif str(item["verdict"]).strip() not in verdicts:
                bad.append(f"#{i} verdict '{item['verdict']}'")
        if bad:
            r.err(
                f"{rel}: {len(bad)} result(s) off-contract ({'; '.join(bad[:5])}) — "
                f"each needs {', '.join(VERDICT_KEYS)} with verdict in {sorted(verdicts)}"
            )


# --- source quality ------------------------------------------------------------
# A source that carries fewer than 2 verbatim quotes, or that was written off a
# paywall/consent/abstract stub, is not evidence: it is a URL with a title. It
# happens when WebFetch returned a thin page and the fetch ladder
# (scripts/fetch_source.py) was never run. Such a source must not be a
# triangulation leg — otherwise `triangulated` is backed by nothing.
MIN_QUOTES = 2
THIN_ACCESS_PREFIXES = ("partial", "closed", "paywalled", "abstract-only")
THIN_SHARE_WARN = 0.25
ACCESS_RE = re.compile(r"^access:\s*(.+?)\s*$", re.MULTILINE)
SOURCE_ID_COLUMNS = ("sources", "source_ids", "source", "source_id")
SOURCE_ID_SPLIT_RE = re.compile(r"[;,|\s\[\]()]+")
# Real runs use both `NN_slug.md` and `sNN_slug.md`; the id is the same either way.
SOURCE_ID_FILE_RE = re.compile(r"^s?(\d+)_.+\.md$")


def _norm_source_id(token: str) -> str | None:
    """`s01`, `[s01]`, `01`, `1` -> canonical `1`. Anything else -> None."""
    tok = token.strip().strip("[]()").lower()
    if tok.startswith("s"):
        tok = tok[1:]
    if not tok.isdigit():
        return None
    return tok.lstrip("0") or "0"


def _split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return "", text


def source_is_thin(text: str) -> bool:
    front, body = _split_frontmatter(text)
    m = ACCESS_RE.search(front)
    if m:
        access = m.group(1).strip().strip("\"'").lower()
        if access.startswith(THIN_ACCESS_PREFIXES):
            return True
    quotes = sum(1 for line in body.splitlines() if line.lstrip().startswith(">"))
    return quotes < MIN_QUOTES


def collect_thin_sources(d: Path) -> tuple[dict[str, str], set[str]]:
    """-> ({normalized id: label}, {normalized id of every source file})."""
    src = d / "sources"
    thin: dict[str, str] = {}
    seen: set[str] = set()
    if not src.is_dir():
        return thin, seen
    for p in sorted(src.glob("*.md")):
        m = SOURCE_ID_FILE_RE.match(p.name)
        if not m:
            continue
        num = m.group(1)
        key = num.lstrip("0") or "0"
        seen.add(key)
        if source_is_thin(p.read_text(encoding="utf-8")):
            thin[key] = f"s{num}"
    return thin, seen


# Breadth of the read set (references/phases/p4_search.md «Квоты»). Benchmark
# 2026-10-28: 6 of 6 runs had 16–19 sources, 0 Academic, 3–4 types — the search
# stopped at whatever the first queries returned.
MIN_READ = {"medium": 25, "deep": 35}
MIN_CANDIDATES = {"medium": 60, "deep": 100}
TYPE_QUOTAS = {
    "academic": ({"academic"}, 2),
    "primary": ({"primary"}, 3),
    "media": ({"industry-media", "general-media"}, 2),
    "expert": ({"expert-blog"}, 2),
    "practice": ({"forum"}, 2),
}
MIN_CONTRADICTING = 3
CANDIDATE_COLUMNS = ("url", "title", "snippet", "channel", "sphere", "stance", "vendor",
                     "round", "target", "selected")
ACADEMIC_CHANNELS = {"openalex", "semantic_scholar", "arxiv", "crossref"}
MIN_TARGETED_ROUND = 5
WAIVER_RE = re.compile(r"^quota_waiver:\s*(\w+)\s*[—-]\s*(\S.*)$", re.MULTILINE)
# Depth and pool size are what the skill is for; N2 (2026-10-28) waived them in
# plan.md before searching, citing the run budget.
NON_WAIVABLE = {"count", "candidates", "round2"}
BUDGET_REASON_RE = re.compile(r"бюджет|budget|\$\s?\d|деньг|дорог", re.IGNORECASE)
FIELD_RE = re.compile(r"^(type|caveat):\s*(.+?)\s*$", re.MULTILINE)


VERDICT_TABLE_RE = re.compile(r"^\|[^\n]*гипотез[^\n]*\|[^\n]*вердикт", re.IGNORECASE | re.MULTILINE)


def check_verdict_table(d: Path, r: Report) -> None:
    """Benchmark 2026-10-28: explicit hypothesis verdicts in 2 of 6 reports."""
    dated = sorted(p for p in d.glob("*.md") if REPORT_RE.match(p.name))
    if dated and not VERDICT_TABLE_RE.search(dated[-1].read_text(encoding="utf-8")):
        r.err(f"{dated[-1].name}: no `| Гипотеза | Вердикт | Опора |` table — every "
              f"plan hypothesis needs an explicit verdict (phases/p6_synthesis.md)")


# An unconditional pick: "по умолчанию", or an imperative with no "если" in the sentence.
DEFAULT_RE = re.compile(r"(?<![«\w])(по умолчанию|берите|выбирайте|начинать стоит|начните с|рекомендуем)(?![»\w])",
                        re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n")


def _default_sentences(text: str) -> list[str]:
    """Unconditional picks in «Ответ» / «Рекомендация» with no [sNN] behind them."""
    sections = re.split(r"^## ", text, flags=re.MULTILINE)
    scope = [sec for sec in sections if sec.lower().startswith("ответ")]
    scope += re.findall(r"^\**Рекомендаци[яи][^\n]*", text, re.MULTILINE)
    hits = []
    for chunk in scope:
        for sent in SENTENCE_SPLIT_RE.split(chunk):
            if DEFAULT_RE.search(sent) and not re.search(r"\bне\b[^.]*по умолчанию", sent, re.IGNORECASE) \
                    and not re.search(r"\bесли\b", sent, re.IGNORECASE) \
                    and not re.search(r"\[s\d{2,3}\]", sent):
                hits.append(sent.strip())
    return hits


def check_unmeasured_default(d: Path, r: Report) -> None:
    """Benchmark 2026-10-28: 7 of 8 runs said 'Fivetran по умолчанию' with no price found."""
    dated = sorted(p for p in d.glob("*.md") if REPORT_RE.match(p.name))
    targets = [p for p in [d / "readout.md", *dated[-1:]] if p.is_file()]
    for p in targets:
        for sent in _default_sentences(p.read_text(encoding="utf-8")):
            r.err(f"{p.name}: default recommendation without a measured source — «{sent[:90]}». "
                  f"Give conditional branches + the cheapest way to measure (phases/p6_synthesis.md, Антибиас)")


PRE_REMEDIATION = "findings/draft_pre_remediation.md"
HIGH_ID_RE = re.compile(r"^\W*(?:HIGH|H)-(\d+)\b", re.MULTILINE)
REVIEW_HEADING_RE = re.compile(r"adversarial review|ремедиац|red team", re.IGNORECASE)
# N4/N6 (2026-10-28): fixes were appended after the body, TL;DR kept the refuted claims.
APPENDIX_RE = re.compile(r"приоритет над текстом|заменяется на|поправки ниже|см\. ремедиац", re.IGNORECASE)
# "- HIGH-1 → §Ответ (TL;DR), §Ветки: что изменено" — a target ends at ":", "§", "|" or ", §".
FIX_TARGET_RE = re.compile(r"§\s*([^§|:\n]+?)\s*(?=,\s*§|[§|:\n]|$)")


def _sections(text: str) -> dict[str, str]:
    parts = re.split(r"^(#{2,3} .+)$", text, flags=re.MULTILINE)
    return {h.lstrip("# ").strip().casefold(): body for h, body in zip(parts[1::2], parts[2::2])}


def _same(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and a.split() == b.split()


def _find_section(sections: dict[str, str], target: str) -> str | None:
    t = target.strip(" *`").casefold()
    return next((h for h in sections if h == t or h.startswith(t)), None)


def check_remediation_in_body(d: Path, mode: str, r: Report) -> None:
    """Each HIGH from the red-team log is fixed in the body section it names, not in an appendix."""
    logs = sorted((d / "findings").glob("redteam_*.md")) if (d / "findings").is_dir() else []
    dated = sorted(p for p in d.glob("*.md") if REPORT_RE.match(p.name))
    if GATE_RANK[mode] < GATE_RANK["medium"] or not dated:
        return
    if not logs:
        # N6 (2026-10-28) kept no log, so nothing below could check its remediation.
        r.err("findings/redteam_<date>.md missing — red team triage log (adversarial_pass.md)")
        return
    highs = sorted(set(HIGH_ID_RE.findall(logs[-1].read_text(encoding="utf-8"))), key=int)
    if not highs:
        return
    report = dated[-1]
    text = report.read_text(encoding="utf-8")
    for m in APPENDIX_RE.finditer(text):
        r.err(f"{report.name}: «{m.group(0)}» — remediation overrides the body from an appendix; "
              f"edit the section itself (phases/p6_synthesis.md, шаг 6)")
    snap = d / PRE_REMEDIATION
    if not snap.is_file():
        r.err(f"{PRE_REMEDIATION} missing — copy the draft there before `remediate`, "
              f"otherwise body fixes cannot be told from an appended postscript")
        return
    now, before = _sections(text), _sections(snap.read_text(encoding="utf-8"))
    review = next((body for h, body in now.items() if REVIEW_HEADING_RE.search(h)), "")
    changed_any = False
    for hid in highs:
        line = next((ln for ln in review.splitlines() if re.search(rf"\b(?:HIGH|H)-{hid}\b", ln)), None)
        if line is None:
            r.err(f"HIGH-{hid} from {logs[-1].name} not listed in `## Adversarial review` "
                  f"with `→ §<section>` or `→ Open Questions`")
            continue
        if "open questions" in line.casefold():
            continue
        targets = FIX_TARGET_RE.findall(line)
        if not targets:
            r.err(f"HIGH-{hid}: no `§<section>` it was fixed in — «{line.strip()[:90]}»")
        for t in targets:
            h = _find_section(now, t)
            if h is None:
                r.err(f"HIGH-{hid}: section «§{t}» not found in {report.name}")
            elif _same(now[h], before.get(h)):
                r.err(f"HIGH-{hid}: «§{t}» unchanged vs {PRE_REMEDIATION} — the fix is not in the body")
            else:
                changed_any = True
    head = next((h for h in now if h.startswith(("ответ", "tl;dr"))), None)
    if changed_any and head and _same(now[head], before.get(head)):
        r.warn(f"{report.name}: body fixed after red team but «{head}» unchanged — "
               f"check it no longer states the refuted claims")


def check_source_breadth(d: Path, mode: str, r: Report) -> None:
    if GATE_RANK[mode] < GATE_RANK["medium"]:
        return
    plan = d / "plan.md"
    waived: set[str] = set()
    for key, reason in WAIVER_RE.findall(plan.read_text(encoding="utf-8")) if plan.is_file() else []:
        if key in NON_WAIVABLE:
            r.err(f"quota_waiver: {key} — not waivable: depth and candidate pool are the point of medium/deep")
        elif BUDGET_REASON_RE.search(reason):
            r.err(f"quota_waiver: {key} — budget is not a reason; waive only what the search "
                  f"did not find (cite candidates.csv)")
        else:
            waived.add(key)

    def gate(key: str, msg: str) -> None:
        hint = "" if key in waived or key in NON_WAIVABLE else f" — or add `quota_waiver: {key} — <why>` to plan.md"
        (r.warn if key in waived else r.err)(msg + hint)

    files = sorted((d / "sources").glob("*.md")) if (d / "sources").is_dir() else []
    if len(files) < MIN_READ[mode]:
        gate("count", f"{len(files)} sources read, {mode} needs ≥{MIN_READ[mode]}")
    types: list[str] = []
    vendor = contradicting = 0
    for p in files:
        front, _ = _split_frontmatter(p.read_text(encoding="utf-8"))
        fields = dict(FIELD_RE.findall(front))
        types.append(fields.get("type", "").strip("\"'").lower())
        vendor += fields.get("caveat", "").strip("\"'").lower() == "vendor"
        contradicting += bool(re.search(r"^\s+H\d+:\s*contradicts\b", front, re.MULTILINE))
    for key, (kinds, need) in TYPE_QUOTAS.items():
        have = sum(t in kinds for t in types)
        if have < need:
            gate(key, f"{have} {key} sources (type {'/'.join(sorted(kinds))}), quota ≥{need}")
    if contradicting < MIN_CONTRADICTING:
        gate("against", f"{contradicting} sources contradict a hypothesis "
                        f"(hypothesis_evidence: contradicts), quota ≥{MIN_CONTRADICTING}")
    if files and vendor * 2 > len(files):
        gate("vendor", f"{vendor} of {len(files)} sources are vendor material — "
                       f"at most half; the rest must be vendor-independent")

    no_card = [p.name for p in files if "\n## Разбор" not in p.read_text(encoding="utf-8")]
    if no_card:
        r.warn(f"{len(no_card)} of {len(files)} sources have no `## Разбор` card "
               f"(claim type, method, scope, modality) — e.g. {', '.join(no_card[:3])}")

    check_verdict_table(d, r)
    check_unmeasured_default(d, r)

    cand = d / "candidates.csv"
    if not cand.is_file():
        return  # absence is reported by the phase-4 artifact check
    with cand.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in CANDIDATE_COLUMNS if c not in (reader.fieldnames or [])]
        rows = list(reader)
    if missing:
        r.err(f"candidates.csv: missing columns {', '.join(missing)}")
        return
    if len(rows) < MIN_CANDIDATES[mode]:
        gate("candidates", f"candidates.csv has {len(rows)} rows, {mode} needs ≥{MIN_CANDIDATES[mode]}")
    if not any(row["channel"].strip().lower() in ACADEMIC_CHANNELS for row in rows):
        gate("academic", "no candidate came from an academic API "
                         f"({', '.join(sorted(ACADEMIC_CHANNELS))})")
    targeted = [row for row in rows if row["round"].strip() == "2" and row["target"].strip()]
    if len(targeted) < MIN_TARGETED_ROUND:
        gate("round2", f"{len(targeted)} round-2 candidates with a `target` — the second "
                       f"round must aim at the decision variable, ≥{MIN_TARGETED_ROUND}")
    selected = sum(row["selected"].strip().upper() == "Y" for row in rows)
    if files and selected and selected != len(files):
        r.warn(f"candidates.csv marks {selected} selected, sources/ has {len(files)}")


def check_source_quality(d: Path, mode: str, r: Report) -> None:
    """Thin sources silently backing `triangulated` claims.

    Measured on 12 real runs: 27% of source files carry <2 quotes and every one
    of them reports `fetch_tier: webfetch` — the ladder was never used. A claim
    standing only on such sources is not triangulated, it is one bad fetch.
    """
    thin, seen = collect_thin_sources(d)
    if not seen:
        return

    for row in load_claim_rows(d):
        if (row.get("status") or "").strip().lower() != "triangulated":
            continue
        cid = (row.get("claim_id") or "").strip() or "?"
        cell = next(
            (row[c] for c in SOURCE_ID_COLUMNS if (row.get(c) or "").strip()), ""
        )
        cited = []
        for tok in SOURCE_ID_SPLIT_RE.split(cell):
            key = _norm_source_id(tok)
            if key is not None and key in seen and key not in cited:
                cited.append(key)
        if not cited:
            continue
        bad = [thin[k] for k in cited if k in thin]
        if not bad:
            continue
        listed = ", ".join(bad)
        if len(bad) == len(cited):
            msg = (
                f"claim {cid} is triangulated on thin sources only ({listed}) — "
                f"thin = <{MIN_QUOTES} quotes or access PARTIAL/closed; refetch via "
                f"scripts/fetch_source.py or downgrade"
            )
            (r.err if GATE_RANK[mode] >= GATE_RANK["medium"] else r.warn)(msg)
        else:
            r.warn(
                f"claim {cid} is triangulated partly on thin sources ({listed}) — "
                f"refetch them via scripts/fetch_source.py or drop them as legs"
            )

    share = len(thin) / len(seen)
    if share > THIN_SHARE_WARN:
        r.warn(
            f"{len(thin)} of {len(seen)} sources are thin ({share * 100:.0f}%) — "
            f"the fetch ladder was not used; see subagents_v2.md §fetch"
        )


OUTLINE_ROW_RE = re.compile(r"^\|(?P<cells>.+)\|\s*$")
CLAIM_CELL_SPLIT_RE = re.compile(r"[;,\s]+")
# Claims this strong are the run's product: reaching one and leaving it out of the
# report is work thrown away silently, not an editorial choice.
CARRYING_STATUSES = {"triangulated", "contested"}
STATE_SECTIONS = ("## Known", "## Gaps", "## Next")
STATE_SOFT_LIMIT = 6 * 1024
STATE_HARD_LIMIT = 12 * 1024


def parse_outline(text: str) -> dict[str, list[str]]:
    """Read the `| section | block | claims |` table -> {section: [claim_id, ...]}.

    The claims cell is tokenized rather than pattern-matched: claim ids are whatever
    claims.csv calls them, and a validator that hard-codes `CL\\d+` silently reads
    zero claims from a run that numbered them differently.
    """
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = OUTLINE_ROW_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group("cells").split("|")]
        if len(cells) < 3:
            continue
        section = cells[0]
        if not section or section.lower() == "section" or set(section) <= set("-: "):
            continue  # header or separator row
        tokens = [
            t for t in CLAIM_CELL_SPLIT_RE.split(cells[2]) if t and t not in {"-", "—"}
        ]
        out[section] = tokens
    return out


def load_claim_rows(d: Path) -> list[dict[str, str]]:
    ledger = d / "claims.csv"
    if not ledger.is_file():
        return []
    return list(csv.DictReader(ledger.read_text(encoding="utf-8").splitlines()))


def check_outline_coverage(d: Path, mode: str, r: Report) -> None:
    """The outline is the join between what was found and what got written.

    Three failures live here: a section with no claims (prose with no ledger behind
    it), a claim_id that resolves to nothing, and — the expensive one — a carrying
    claim that never reached any section. The last is the synthesis gap: retrieval
    worked, organization dropped it.
    """
    outline = d / "outline.md"
    if not outline.is_file():
        return  # presence is the phase-gate's business, above
    sections = parse_outline(outline.read_text(encoding="utf-8"))
    if not sections:
        r.err(
            "outline.md has no `| section | block | claims |` table rows — "
            "the section->claim map is what makes per-section synthesis checkable"
        )
        return
    rows = load_claim_rows(d)
    known = {(row.get("claim_id") or "").strip() for row in rows} - {""}

    mapped: set[str] = set()
    for section, claims in sections.items():
        if not claims:
            r.err(f"outline.md: section '{section}' maps to no claim_id")
            continue
        for cid in claims:
            if known and cid not in known:
                r.err(
                    f"outline.md: section '{section}' cites {cid}, absent from claims.csv"
                )
            mapped.add(cid)

    if not rows:
        return
    orphans = []
    for row in rows:
        status = (row.get("status") or "").strip().lower()
        cid = (row.get("claim_id") or "").strip()
        if status in CARRYING_STATUSES and cid and cid not in mapped:
            orphans.append(f"{cid} ({status})")
    if orphans:
        message = (
            f"claims reached but never placed in the report: {', '.join(orphans)} — "
            f"triangulated/contested work dropped at synthesis, not at search "
            f"(map it to a section or say in Open Questions why it is out)"
        )
        # On deep this is a blocker; on medium a loud warning — a medium run may
        # legitimately carry more than its outline holds.
        (r.err if mode == "deep" else r.warn)(message)


def check_constructs(d: Path, r: Report) -> None:
    """Layer 4: an unsourced named construct in the memo/TL;DR blocks finish."""
    path = d / ".verify/constructs.json"
    if not path.is_file():
        return  # presence is enforced by PHASE_ARTIFACTS for 6.5
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        r.err(
            f".verify/constructs.json is not valid JSON ({exc.msg}) — Layer 4 cannot be read"
        )
        return
    results = data.get("results")
    if not isinstance(results, list):
        r.err(
            ".verify/constructs.json has no `results` list — Layer 4 produced nothing"
        )
        return
    for item in results:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        name = item.get("name", "?")
        locations = [str(loc) for loc in item.get("locations", [])]
        if status == "unsourced":
            carried = [loc for loc in locations if loc in {"memo.md", "F1", "F9"}]
            if carried:
                r.err(
                    f"construct '{name}' is unsourced and appears in {', '.join(carried)} — "
                    f"source it, mark it as ours, or remove it (Layer 4 fail-closed)"
                )
            else:
                r.warn(
                    f"construct '{name}' is unsourced (in {', '.join(locations) or '?'})"
                )
        elif status not in {"sourced", "author-construct"}:
            r.warn(
                f"construct '{name}': status '{status or 'empty'}' is not one of "
                f"sourced/author-construct/unsourced"
            )


def check_state_window(d: Path, r: Report) -> None:
    """state.md is a rebuilt window, not a second transcript."""
    state = d / "state.md"
    if not state.is_file():
        return  # presence is enforced by PHASE_ARTIFACTS for phase 4
    text = state.read_text(encoding="utf-8")
    missing = [s for s in STATE_SECTIONS if s not in text]
    if missing:
        r.err(
            f"state.md is missing section(s) {', '.join(missing)} — the next round is "
            f"planned from Known/Gaps/Next, so a missing one is a silently empty input"
        )
    size = len(text.encode("utf-8"))
    if size > STATE_HARD_LIMIT:
        r.err(
            f"state.md is {size // 1024} KB (limit {STATE_HARD_LIMIT // 1024} KB) — "
            f"it is being appended to, not rebuilt; the archive belongs in "
            f"sources/, deviations.md and plan.md §15"
        )
    elif size > STATE_SOFT_LIMIT:
        r.warn(
            f"state.md is {size // 1024} KB (soft limit {STATE_SOFT_LIMIT // 1024} KB) — "
            f"compress Known to subquestion statuses with claim_id/[sNN] references"
        )


def self_check(phases: list[dict], r: Report) -> None:
    """Warn if phases.yaml gained a file-emitting phase this table does not cover."""
    known = set(PHASE_ARTIFACTS) | NO_FILE_PHASES
    for p in phases:
        if p["id"] not in known:
            r.warn(
                f"phase {p['id']} ({p['name_en']}) is in phases.yaml but not in this "
                f"validator's artifact table — add it to PHASE_ARTIFACTS or NO_FILE_PHASES"
            )


def check_wiki_ingest(d: Path, r: Report) -> None:
    """The run must have been compiled into the cross-run wiki (finish-up step 0).

    Not in PHASE_ARTIFACTS because it belongs to no phase: ingest runs at finish-up, at
    every depth, and its real output lives outside the run directory. The receipt is
    what makes it checkable here at all — without a gate this is precisely the kind of
    step that keeps being declared and quietly stops running.
    """
    receipt = d / ".verify" / "wiki_ingest.json"
    if not receipt.is_file():
        r.err(
            "finish-up: нет .verify/wiki_ingest.json — прогон не попал в кросс-прогонную "
            "вики (python scripts/wiki_ingest.py --research-dir <dir>)"
        )
        return
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        r.err(f"wiki_ingest.json нечитаем ({exc}) — перезапусти wiki_ingest.py")
        return
    if data.get("run") != d.name:
        r.err(
            f"wiki_ingest.json от прогона '{data.get('run')}', а папка '{d.name}' — "
            "квитанция скопирована из чужого ресёрча"
        )


def validate(d: Path, mode: str, phases: list[dict], r: Report) -> None:
    self_check(phases, r)
    check_source_perimeter(d, r)
    check_schema_contract(d, r)
    check_source_quality(d, mode, r)
    check_source_breadth(d, mode, r)
    check_remediation_in_body(d, mode, r)
    check_state_window(d, r)
    check_outline_coverage(d, mode, r)
    check_constructs(d, r)
    check_wiki_ingest(d, r)
    gate_of = {p["id"]: p["depth_gate"] for p in phases}
    run_rank = GATE_RANK[mode]
    for phase_id, spec in PHASE_ARTIFACTS.items():
        gate = gate_of.get(phase_id)
        if gate is None:
            r.warn(f"phase {phase_id} is mapped here but not present in phases.yaml")
            continue
        if GATE_RANK[gate] <= run_rank:  # mandatory for this mode
            check_phase(d, phase_id, spec, mode, r)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument(
        "--mode",
        choices=MODES,
        help="run depth; frontmatter, else inferred from artifacts, if omitted",
    )
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any error")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="print every warning, not the first few")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    r = Report()
    mode = resolve_mode(d, args.mode, r)

    phases = phases_manifest.load_phases(
        Path(__file__).resolve().parents[1] / "phases.yaml"
    )
    validate(d, mode, phases, r)

    if args.json:
        print(
            json.dumps(
                {
                    "research_dir": str(d),
                    "mode": mode,
                    "errors": r.errors,
                    "warnings": r.warnings,
                },
                indent=2,
            )
        )
    else:
        print(f"Validating phases: {d}   (mode: {mode})")
        for line in capped((f"  ERROR   {m}" for m in r.errors), CAP_ERRORS, args.verbose):
            print(line)
        for line in capped((f"  warn    {m}" for m in r.warnings), CAP_WARNINGS, args.verbose):
            print(line)
        if not r.errors and not r.warnings:
            print("  OK — all mandatory phases produced their artifacts")
        elif not r.errors:
            print(f"\n{len(r.warnings)} warning(s), 0 errors.")
        else:
            print(f"\n{len(r.errors)} error(s), {len(r.warnings)} warning(s).")

    if args.strict and r.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
