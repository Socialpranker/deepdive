#!/usr/bin/env python3
"""
One finish-up command for a completed run. Replaces six hand-typed invocations
(each with a flag the gate depends on — `--out` under .verify/, `--strict`, the
wiki receipt) whose omission was where phases got silently skipped.

Runs, in order, never stopping early so one report shows everything:
  1. build_sources_csv      sources/NN.md  -> sources.csv
  2. check_citations        liveness       -> .verify/citations.json   (skip: --offline)
  3. wiki_ingest            run -> cross-run wiki, receipt .verify/wiki_ingest.json
  4. check_number_provenance --strict
  5. check_number_arithmetic --strict
  6. validate_phases --strict   the gate — last, so it sees everything above

Exit 1 if any step failed. Usage:
    python scripts/finish.py --research-dir <root>/<slug> [--mode medium] [--offline]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


@dataclass
class Step:
    name: str
    script: Path
    extra: Callable[[Path, str | None, Path | None], list[str]]
    network: bool = False


@dataclass
class StepResult:
    name: str
    rc: int
    output: str
    skipped: bool = False
    argv: list[str] = field(default_factory=list)


def _mode(m: str | None) -> list[str]:
    return ["--mode", m] if m else []


STEPS: list[Step] = [
    Step("sources_csv", REPO / "scripts/build_sources_csv.py", lambda d, m, w: []),
    Step(
        "citations",
        REPO / "eval/check_citations.py",
        lambda d, m, w: ["--json", "--out", str(d / ".verify" / "citations")],
        network=True,
    ),
    Step(
        "wiki_ingest",
        REPO / "scripts/wiki_ingest.py",
        lambda d, m, w: ["--wiki-root", str(w)] if w else [],
    ),
    Step("number_provenance", REPO / "scripts/check_number_provenance.py", lambda d, m, w: ["--strict"]),
    Step("number_arithmetic", REPO / "scripts/check_number_arithmetic.py", lambda d, m, w: ["--strict"]),
    Step("phase_gate", REPO / "scripts/validate_phases.py", lambda d, m, w: ["--strict", *_mode(m)]),
]

Runner = Callable[[str, list[str]], StepResult]


def subprocess_runner(name: str, argv: list[str]) -> StepResult:
    proc = subprocess.run(argv, capture_output=True, text=True)
    return StepResult(name, proc.returncode, proc.stdout + proc.stderr, argv=argv)


def run_finish(
    d: Path,
    *,
    mode: str | None,
    offline: bool,
    wiki_root: Path | None,
    runner: Runner = subprocess_runner,
) -> list[StepResult]:
    (d / ".verify").mkdir(exist_ok=True)
    results: list[StepResult] = []
    for step in STEPS:
        if step.network and offline:
            results.append(StepResult(step.name, 0, "skipped (--offline)", skipped=True))
            continue
        argv = [PY, str(step.script), "--research-dir", str(d), *step.extra(d, mode, wiki_root)]
        res = runner(step.name, argv)
        res.argv = res.argv or argv
        results.append(res)
    return results


def exit_code(results: list[StepResult]) -> int:
    return 1 if any(r.rc != 0 and not r.skipped for r in results) else 0


def render(results: list[StepResult], verbose: bool) -> str:
    lines = []
    for r in results:
        status = "skip" if r.skipped else ("ok" if r.rc == 0 else "FAIL")
        lines.append(f"  {status:<5} {r.name}")
        if verbose or (r.rc != 0 and not r.skipped):
            out = r.output.strip().splitlines()
            # Errors first: a failing gate can bury its one error under a page of warnings.
            errs = [t for t in out if "ERROR" in t or "FAIL" in t]
            shown = (errs or out)[-12:] if not verbose else out
            lines.extend(f"        {t}" for t in shown)
    code = exit_code(results)
    lines.append("")
    lines.append(
        "Finish: green — the run is complete." if code == 0
        else "Finish: RED — fix the failing step(s) above and re-run. Do not report done."
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--mode", choices=("shallow", "medium", "deep"))
    ap.add_argument("--offline", action="store_true", help="skip the network liveness check")
    ap.add_argument("--wiki-root", type=Path, default=None, help="override ~/.claude (tests)")
    ap.add_argument("--verbose", action="store_true", help="print every step's output")
    args = ap.parse_args()
    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2
    print(f"Finish-up: {d}")
    results = run_finish(d, mode=args.mode, offline=args.offline, wiki_root=args.wiki_root)
    print(render(results, args.verbose))
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
