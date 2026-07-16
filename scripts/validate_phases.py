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
# A directory entry (trailing kind="dir") must be a non-empty directory.
# Phases with no file output (reframing/genre/capability/plan-gate) are absent here
# on purpose; the self-check below knows they are intentionally artifact-less.
PHASE_ARTIFACTS: dict[str, dict[str, list[str]]] = {
    "3": {"all_of": ["plan.md"]},
    "4": {"any_of": ["sources", "sources.csv"]},
    "5": {"all_of": ["claims.csv"]},
    "5.5": {"all_of": ["evidence"]},
    "6": {"report": []},  # the dated <YYYY-MM-DD>_<genre>.md report — matched by pattern
    "6.5": {"all_of": [".verify/citations.json", ".verify/faithfulness.json"]},
    "7": {"all_of": ["refresh_targets.md"]},
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

    def err(self, m: str) -> None: self.errors.append(m)
    def warn(self, m: str) -> None: self.warnings.append(m)


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


def check_phase(d: Path, phase_id: str, spec: dict[str, list[str]], r: Report) -> None:
    if "report" in spec:
        if not has_report(d):
            r.err(f"phase {phase_id}: no final report <YYYY-MM-DD>_<genre>.md")
        return
    if "all_of" in spec:
        for rel in spec["all_of"]:
            if not artifact_present(d, rel):
                r.err(f"phase {phase_id}: missing required artifact '{rel}'")
    if "any_of" in spec:
        if not any(artifact_present(d, rel) for rel in spec["any_of"]):
            joined = "' or '".join(spec["any_of"])
            r.err(f"phase {phase_id}: missing artifact (need '{joined}')")


def self_check(phases: list[dict], r: Report) -> None:
    """Warn if phases.yaml gained a file-emitting phase this table does not cover."""
    known = set(PHASE_ARTIFACTS) | NO_FILE_PHASES
    for p in phases:
        if p["id"] not in known:
            r.warn(
                f"phase {p['id']} ({p['name_en']}) is in phases.yaml but not in this "
                f"validator's artifact table — add it to PHASE_ARTIFACTS or NO_FILE_PHASES"
            )


def validate(d: Path, mode: str, phases: list[dict], r: Report) -> None:
    self_check(phases, r)
    gate_of = {p["id"]: p["depth_gate"] for p in phases}
    run_rank = GATE_RANK[mode]
    for phase_id, spec in PHASE_ARTIFACTS.items():
        gate = gate_of.get(phase_id)
        if gate is None:
            r.warn(f"phase {phase_id} is mapped here but not present in phases.yaml")
            continue
        if GATE_RANK[gate] <= run_rank:  # mandatory for this mode
            check_phase(d, phase_id, spec, r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--mode", choices=MODES, help="run depth; auto-detected from frontmatter if omitted")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any error")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    mode = args.mode or detect_mode(d)
    if mode is None:
        print("ERROR: could not determine run mode — pass --mode {shallow,medium,deep} "
              "(no 'mode:' frontmatter found in report or plan.md)")
        return 2

    phases = phases_manifest.load_phases(Path(__file__).resolve().parents[1] / "phases.yaml")
    r = Report()
    validate(d, mode, phases, r)

    if args.json:
        print(json.dumps({"research_dir": str(d), "mode": mode,
                          "errors": r.errors, "warnings": r.warnings}, indent=2))
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
