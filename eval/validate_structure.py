#!/usr/bin/env python3
"""
Structural validator for a deep-research run directory.

This is the schema guard the eval scripts implicitly depend on. check_citations.py
and score_run.py both parse the run's files by convention (frontmatter keys, CSV
columns, report filename pattern). When a run — or a contributor's PR that touches
templates — drifts from that convention, those tools fail silently or score wrong.
This script makes the contract explicit and machine-checkable.

It validates the ARTIFACT FORMAT, not the research quality (that's score_run.py).

Checks (errors fail --strict; warnings never do):
  - exactly one final report  <YYYY-MM-DD>_<genre>.md  with a known genre suffix
  - plan.md present
  - sources present as either sources/NN_*.md (frontmatter) or sources.csv
  - each sources/NN_*.md frontmatter has: id, url, title, access (access in vocab)
  - sources.csv header has at least url+title; type/channel recommended for diversity
  - findings/FN_*.md (if any) match the F<n>_<slug>.md pattern
  - report's source refs (sNN / [N]) don't dangle past the source count (warning)

Usage:
    python eval/validate_structure.py --research-dir research/<slug>
    python eval/validate_structure.py --research-dir research/<slug> --strict   # exit 1 on errors
    python eval/validate_structure.py --research-dir research/<slug> --json
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

GENRES = {"qa", "explainer", "decision", "landscape", "validation", "custom"}
ACCESS_VOCAB = {
    "OPEN", "PAYWALLED", "PAYWALLED-ABSTRACT-ONLY", "CLOSED",
    "ARCHIVE-RESTORED", "GRAY-AREA-SOURCE",
}
# Source `type` vocab from rubric.md axis 2 (diversity). Lowercased for comparison.
TYPE_VOCAB = {"primary", "academic", "industry-media", "general-media", "expert-blog", "forum", "other"}
# Source `caveat` vocab (F14 input-skepticism marker). A strict enum: bare `-`, `vendor`,
# `self-reported`, or `disputed:sNN` (NN = an integer id). Free text here breaks machine
# handling — the explanation belongs in the file body, not the field.
CAVEAT_FIXED = {"-", "", "vendor", "self-reported"}
CAVEAT_DISPUTED_RE = re.compile(r"^disputed:s?\d+$")
REPORT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([a-z]+)\.md$")
FINDING_RE = re.compile(r"^F\d+_[a-z0-9][a-z0-9-]*\.md$")
SOURCE_FILE_RE = re.compile(r"^\d{2,}_[a-z0-9][a-z0-9-]*\.md$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def err(self, m: str) -> None: self.errors.append(m)
    def warn(self, m: str) -> None: self.warnings.append(m)
    def note(self, m: str) -> None: self.info.append(m)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return dict(re.findall(r"^(\w[\w-]*):\s*(.+?)\s*$", parts[1], re.MULTILINE))


def check_report(d: Path, r: Report) -> int:
    candidates = [p for p in d.glob("*.md") if p.name != "plan.md"]
    dated = [p for p in candidates if REPORT_RE.match(p.name)]
    if not dated:
        r.err("no final report matching <YYYY-MM-DD>_<genre>.md at run root")
        return 0
    for p in dated:
        genre = REPORT_RE.match(p.name).group(2)
        if genre not in GENRES:
            r.err(f"{p.name}: unknown genre suffix '{genre}' (allowed: {', '.join(sorted(GENRES))})")
    if len(dated) > 1:
        r.warn(f"{len(dated)} dated reports found; score_run.py picks the lexically-latest")
    return len(dated)


def check_plan(d: Path, r: Report) -> None:
    if not (d / "plan.md").is_file():
        r.err("plan.md missing (coverage scoring + judge input read it)")


def check_sources_dir(d: Path, r: Report) -> int:
    sd = d / "sources"
    if not sd.is_dir():
        return 0
    files = sorted(sd.glob("*.md"))
    n = 0
    for f in files:
        if not SOURCE_FILE_RE.match(f.name):
            r.warn(f"sources/{f.name}: name should be NN_slug.md")
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fm:
            r.err(f"sources/{f.name}: missing/ø frontmatter block")
            continue
        n += 1
        if not fm.get("url"):
            r.err(f"sources/{f.name}: frontmatter has no 'url'")
        for k in ("id", "title", "access"):
            if not fm.get(k):
                r.warn(f"sources/{f.name}: frontmatter missing '{k}'")
        acc = (fm.get("access") or "OPEN").strip().upper()
        if acc not in ACCESS_VOCAB:
            r.warn(f"sources/{f.name}: access '{acc}' not in vocab {sorted(ACCESS_VOCAB)}")
        cav = (fm.get("caveat") or "-").strip().strip("\"'").strip()
        if cav.lower() not in CAVEAT_FIXED and not CAVEAT_DISPUTED_RE.match(cav.lower()):
            r.warn(f"sources/{f.name}: caveat '{cav}' not a valid marker "
                   f"(use -, vendor, self-reported, or disputed:sNN — put explanation in the body)")
    return n


def check_sources_csv(d: Path, r: Report) -> int:
    cp = d / "sources.csv"
    if not cp.is_file():
        return 0
    with cp.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        r.err("sources.csv is empty")
        return 0
    cols = set(rows[0].keys())
    for required in ("url", "title"):
        if required not in cols:
            r.err(f"sources.csv: missing required column '{required}'")
    if not ({"type", "channel"} & cols):
        r.warn("sources.csv: no 'type' or 'channel' column — diversity axis unscorable")
    # validate type vocab where present
    if "type" in cols:
        for i, row in enumerate(rows, 1):
            t = (row.get("type") or "").strip().lower()
            if t and t not in TYPE_VOCAB:
                r.warn(f"sources.csv row {i}: type '{t}' not in vocab")
    miss_url = sum(1 for row in rows if not (row.get("url") or "").strip())
    if miss_url:
        r.err(f"sources.csv: {miss_url} row(s) with empty url")
    return len(rows)


def check_findings(d: Path, r: Report) -> None:
    fd = d / "findings"
    if not fd.is_dir():
        return
    for f in fd.glob("*.md"):
        if not FINDING_RE.match(f.name):
            r.warn(f"findings/{f.name}: should match F<n>_<slug>.md")


def check_dangling_refs(d: Path, r: Report, n_sources: int) -> None:
    if n_sources == 0:
        return
    dated = [p for p in d.glob("*.md") if REPORT_RE.match(p.name)]
    if not dated:
        return
    text = max(dated, key=lambda p: p.name).read_text(encoding="utf-8")
    refs = {int(m) for m in re.findall(r"\bs(\d{1,3})\b", text)}
    over = {x for x in refs if x > n_sources}
    if over:
        r.warn(f"report cites source ids {sorted(over)} but only {n_sources} sources exist (dangling?)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any error")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    r = Report()
    check_report(d, r)
    check_plan(d, r)
    n_fm = check_sources_dir(d, r)
    n_csv = check_sources_csv(d, r)
    if n_fm == 0 and n_csv == 0:
        r.err("no sources found (need sources/*.md or sources.csv)")
    n_sources = n_fm or n_csv
    check_findings(d, r)
    check_dangling_refs(d, r, n_sources)

    if args.json:
        print(json.dumps({"research_dir": str(d), "n_sources": n_sources,
                          "errors": r.errors, "warnings": r.warnings}, indent=2))
    else:
        print(f"Validating run: {d}   ({n_sources} sources)")
        for m in r.errors:
            print(f"  ERROR   {m}")
        for m in r.warnings:
            print(f"  warn    {m}")
        if not r.errors and not r.warnings:
            print("  OK — structure valid, no warnings")
        elif not r.errors:
            print(f"\n{len(r.warnings)} warning(s), 0 errors.")
        else:
            print(f"\n{len(r.errors)} error(s), {len(r.warnings)} warning(s).")

    if args.strict and r.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
