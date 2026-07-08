#!/usr/bin/env python3
"""Stamp generated values into doc marker spans, or check for drift.

Truth sources: catalog_counts.counts() (numbers) + phases_manifest (phases).
Docs carry markers:  <!--gen:KEY-->...<!--/gen-->  — the span is rewritten.

Usage:
    python scripts/stamp_docs.py --write    # rewrite all target docs in place
    python scripts/stamp_docs.py --check    # exit 1 + diff if any doc is stale

The human runs --write and commits; CI runs --check.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

import catalog_counts
import phases_manifest

OPEN_RE = re.compile(r"<!--gen:([a-z0-9:_]+)-->")
CLOSE = "<!--/gen-->"

# Target docs, relative to repo root. (Marker placement happens in Task 6.)
TARGETS = [
    "README.md",
    "SKILL.md",
    "CONTRIBUTING.md",
    "docs/index.html",
    "docs/_config.yml",
    "runner/DESIGN.md",
    "references/blocks/INDEX.md",
    "references/channels.md",
    "references/stat_sources/INDEX.md",
    "references/workflow.md",
    "eval/README.md",
    "QUICKSTART.md",
]


def render_values(repo: Path) -> dict[str, str]:
    c = catalog_counts.counts(repo)
    for k, v in c.items():
        if v <= 0:
            raise ValueError(f"count {k}={v} is suspicious (zero) — refusing to stamp")
    phases = phases_manifest.load_phases(repo / "phases.yaml")
    if not phases:
        raise ValueError("no phases — refusing to stamp")

    list_ru = " → ".join(p["name_ru"] for p in phases)
    table_rows = "\n" + "\n".join(
        f"| **{p['id']}** | **{p['name_en']}** | {p['model']} / {p['effort']} |"
        for p in phases
    ) + "\n"

    return {
        "count:blocks": str(c["blocks"]),
        "count:channels": str(c["channels"]),
        "count:stat_sources": str(c["stat_sources"]),
        "count:api": str(c["api"]),
        "count:genres": str(c["genres"]),
        "count:phases": str(len(phases)),
        "phases:list:ru": list_ru,
        "phases:table:en": table_rows,
    }


def stamp_text(text: str, values: dict[str, str], *, path: str) -> str:
    out = []
    pos = 0
    while True:
        m = OPEN_RE.search(text, pos)
        if not m:
            break
        key = m.group(1)
        if key not in values:
            raise ValueError(f"{path}: unknown key 'gen:{key}'")
        close_at = text.find(CLOSE, m.end())
        if close_at == -1:
            raise ValueError(f"{path}: unbalanced marker 'gen:{key}' (no {CLOSE})")
        # Markers must not nest: another open before this one's close = malformed.
        inner = OPEN_RE.search(text, m.end())
        if inner and inner.start() < close_at:
            raise ValueError(
                f"{path}: nested marker 'gen:{inner.group(1)}' inside 'gen:{key}' "
                f"(markers cannot overlap)")
        out.append(text[pos:m.end()])
        out.append(values[key])
        out.append(CLOSE)
        pos = close_at + len(CLOSE)
    out.append(text[pos:])
    return "".join(out)


def run(repo: Path, targets: list[Path], *, write: bool) -> int:
    values = render_values(repo)
    seen_keys: set[str] = set()
    drift = 0
    for path in targets:
        p = Path(path)
        if not p.is_absolute():
            p = repo / p
        if not p.exists():
            continue  # a target may not exist yet (e.g. QUICKSTART before Task 9)
        original = p.read_text(encoding="utf-8")
        seen_keys.update(OPEN_RE.findall(original))
        stamped = stamp_text(original, values, path=str(p))
        if stamped != original:
            if write:
                p.write_text(stamped, encoding="utf-8")
            else:
                drift = 1
                print(f"DRIFT: {p}")
                diff = difflib.unified_diff(
                    original.splitlines(), stamped.splitlines(),
                    fromfile=f"{p} (committed)", tofile=f"{p} (generated)", lineterm="")
                print("\n".join(diff))
    # Spec: a generator key that appears in NO doc is a likely-forgotten marker → warn (not fail).
    unused = sorted(set(values) - seen_keys)
    for key in unused:
        print(f"WARNING: key 'gen:{key}' is stamped nowhere (forgotten marker?)")
    return drift


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="rewrite docs in place")
    g.add_argument("--check", action="store_true", help="exit 1 on drift")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    rc = run(args.root, [args.root / t for t in TARGETS], write=args.write)
    if args.check and rc:
        print("\nDocs are stale. Run: python scripts/stamp_docs.py --write")
    elif args.write:
        print("Stamped.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
