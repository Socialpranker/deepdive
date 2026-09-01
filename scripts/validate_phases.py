#!/usr/bin/env python3
"""
Phase-gate validator for a completed deep-research run directory.

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
    "4": {"any_of": ["sources", "sources.csv"], "medium_of": ["state.md"]},
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
    "6": {
        "report": [],
        "all_of": ["memo.md"],
        "medium_of": ["outline.md", "numbers.csv"],
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
# Columns the triangulation / dissent / provenance rules read. Warn (not error) so
# runs made before those rules existed stay validatable.
LEDGER_COLUMNS = ("roots", "paths", "dissent", "as_of")


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


def check_ledger_columns(d: Path, r: Report) -> None:
    """A missing ledger column is not a formatting nit: the rule that reads it
    silently never fires — the 'green check, no behavior' failure mode."""
    ledger = d / "claims.csv"
    if not ledger.is_file():
        return
    lines = ledger.read_text(encoding="utf-8").splitlines()
    if not lines:
        r.err("claims.csv is empty")
        return
    cols = {c.strip() for c in lines[0].split(",")}
    missing = [c for c in LEDGER_COLUMNS if c not in cols]
    if missing:
        r.warn(
            f"claims.csv is missing column(s) {', '.join(missing)} — the rules reading "
            f"them (triangulation by root/path, dissent protection, number provenance) "
            f"cannot fire; see references/source_scoring.md"
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
    check_ledger_columns(d, r)
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
        help="run depth; auto-detected from frontmatter if omitted",
    )
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any error")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    mode = args.mode or detect_mode(d)
    if mode is None:
        print(
            "ERROR: could not determine run mode — pass --mode {shallow,medium,deep} "
            "(no 'mode:' frontmatter found in report or plan.md)"
        )
        return 2

    phases = phases_manifest.load_phases(
        Path(__file__).resolve().parents[1] / "phases.yaml"
    )
    r = Report()
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
        for m in r.errors:
            print(f"  ERROR   {m}")
        for m in r.warnings:
            print(f"  warn    {m}")
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
