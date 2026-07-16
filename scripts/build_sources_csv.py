#!/usr/bin/env python3
"""
Build a run's sources.csv from the sources/NN_*.md frontmatter — deterministically.

sources/NN.md is the source of truth (one file per source, hand-written with quotes).
sources.csv is an index that check_citations.py, validate_structure.py and score_run.py
all read. Before this script, that index was assembled by hand each run — a grep|sed
hack that reinvents the column schema every time and drifts from what the readers
expect. This makes it one reproducible command.

Columns are emitted lowercase to match the CONTRACT the readers actually enforce
(validate_structure.py requires `url`,`title`; recommends `type`/`channel`;
check_citations.py reads `url`/`title`/`access`/`id`). The capitalized template in
references/source_scoring.md ("№,URL,Title,...") predates that contract — this script
is the one that reconciles them.

Usage:
    python scripts/build_sources_csv.py --research-dir research/<slug>
    python scripts/build_sources_csv.py --research-dir research/<slug> --check   # CI: fail if stale
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

# Order matters: url,title first (validate_structure REQUIRED), then the recommended
# and scoring columns. `file` lets a reader map a row back to its sources/NN.md.
COLUMNS = [
    "id", "url", "title", "type", "channel", "access",
    "author", "date", "credibility", "recency", "bias", "total", "caveat", "used", "file",
]
SOURCE_FILE_RE = re.compile(r"^\d{2,}_.+\.md$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    # single-line `key: value` pairs only — nested blocks (hypothesis_evidence:) are skipped
    return dict(re.findall(r"^([a-z][a-z_]*):[ \t]*(.+?)[ \t]*$", parts[1], re.MULTILINE))


def collect_rows(research_dir: Path) -> list[dict[str, str]]:
    sd = research_dir / "sources"
    rows: list[dict[str, str]] = []
    if not sd.is_dir():
        return rows
    for f in sorted(sd.glob("*.md")):
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fm.get("url"):
            continue  # no url → not a real source row (mirrors the readers)
        row = {c: fm.get(c, "") for c in COLUMNS}
        row["id"] = fm.get("id", f.stem)
        row["file"] = f"sources/{f.name}"
        rows.append(row)
    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--check", action="store_true", help="Exit 1 if sources.csv is stale (CI); do not write")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    rows = collect_rows(d)
    if not rows:
        print(f"ERROR: no sources with a 'url' found under {d}/sources/")
        return 2

    content = render_csv(rows)
    out = d / "sources.csv"

    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else ""
        if current != content:
            print(f"sources.csv is stale — run: python scripts/build_sources_csv.py --research-dir {d}")
            return 1
        print(f"OK — sources.csv up to date ({len(rows)} sources)")
        return 0

    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out}  ({len(rows)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
