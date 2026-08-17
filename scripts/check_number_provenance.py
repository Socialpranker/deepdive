#!/usr/bin/env python3
"""
Number-provenance checker for a completed deep-research run directory.

Phases 6.5 verify that a source *said* what it is quoted as saying. Nothing checks
where the source got a NUMBER from — so a content farm with a verbatim quote passes
faithfulness perfectly. This script is the mechanical half of that gap:

  1. fail-closed rule  — a number whose provenance is unknown (origin_kind unknown,
     chain_len >= 2, or no data_as_of) must not appear in memo.md / the report's
     TL;DR, and must not back a `confidence: high` claim.
  2. circulation       — the same value appearing in sources that declare DIFFERENT
     roots is the signature of a zombie figure: either `root` is wrong, or one
     number is being laundered into apparent independence.

Both checks are deterministic — no model in the loop. Neither judges whether a
number is TRUE; they judge whether the run can say where it came from.

Usage:
    python scripts/check_number_provenance.py --research-dir research/<slug>
    python scripts/check_number_provenance.py --research-dir research/<slug> --strict
    python scripts/check_number_provenance.py --research-dir research/<slug> --json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# A number worth tracking: at least 2 significant digits, optional decimals,
# optional thousands separators, optional %/x/unit suffix handled by the caller.
NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:[ ,]\d{3})+|\d+(?:\.\d+)?)(?![\w])")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
CITATION_RE = re.compile(r"\[s\d+\]")

# Values that are almost never a research finding: years, small counts, round
# ordinals. Tracking them produces noise, not circulation signal.
YEAR_RANGE = range(1900, 2101)

UNKNOWN_ORIGIN = {"", "-", "unknown"}
QUARANTINE_ORIGIN = {"secondary", "model-estimate"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-ish frontmatter reader: flat `key: value` pairs only.

    Deliberately not a YAML parser — source frontmatter is flat by contract
    (source_scoring.md), and a real parser would be a dependency for nothing.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():  # nested block (hypothesis_evidence) — not needed here
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        out[key.strip()] = value.split("#", 1)[0].strip()
    return out


def significant(value: str) -> str | None:
    """Normalize a numeric token to its first 3 significant digits.

    `34.2%`, `0.342`, and `342 000` all normalize to `342` — that is the point:
    the same figure re-scaled or re-formatted still collides.
    """
    digits = value.replace(",", "").replace(" ", "").replace(".", "").lstrip("0")
    if len(digits) < 2:
        return None
    return digits[:3]


def numbers_in(text: str) -> set[str]:
    found: set[str] = set()
    for raw in NUMBER_RE.findall(text):
        cleaned = raw.replace(",", "").replace(" ", "")
        try:
            as_float = float(cleaned)
        except ValueError:
            continue
        if as_float.is_integer() and int(as_float) in YEAR_RANGE:
            continue
        sig = significant(cleaned)
        if sig:
            found.add(sig)
    return found


def load_sources(d: Path) -> dict[str, dict[str, str]]:
    src = d / "sources"
    if not src.is_dir():
        return {}
    out: dict[str, dict[str, str]] = {}
    for p in sorted(src.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        sid = fm.get("id") or p.name.split("_", 1)[0]
        fm["_file"] = p.name
        fm["_body"] = (
            text[FRONTMATTER_RE.match(text).end() :]
            if FRONTMATTER_RE.match(text)
            else text
        )
        out[sid] = fm
    return out


def check_fail_closed(d: Path, sources: dict[str, dict[str, str]], r: Report) -> dict:
    """A number without traceable provenance may not carry weight."""
    quarantined: list[str] = []
    for sid, fm in sources.items():
        origin = fm.get("origin_kind", "-").lower()
        chain = fm.get("chain_len", "0")
        as_of = fm.get("data_as_of", "-").lower()
        body_numbers = numbers_in(fm.get("_body", ""))
        if not body_numbers:
            continue  # no numbers to vouch for
        reasons = []
        if origin in UNKNOWN_ORIGIN:
            reasons.append("origin_kind unknown")
        elif origin in QUARANTINE_ORIGIN:
            reasons.append(f"origin_kind={origin}")
        try:
            if int(chain) >= 2:
                reasons.append(f"chain_len={chain}")
        except ValueError:
            reasons.append("chain_len unparseable")
        if as_of in {"", "-", "unknown"}:
            reasons.append("no data_as_of")
        if reasons:
            quarantined.append(sid)
            r.warn(
                f"{sid} ({fm['_file']}): number provenance incomplete — {', '.join(reasons)}"
            )

    memo = d / "memo.md"
    if memo.is_file() and quarantined:
        memo_text = memo.read_text(encoding="utf-8")
        for sid in quarantined:
            if f"[{sid}]" in memo_text:
                r.err(
                    f"memo.md cites {sid}, whose number provenance is incomplete — "
                    f"a quarantined number must not appear in the memo (fail-closed rule, "
                    f"see source_scoring.md 'Provenance числа')"
                )
    return {"quarantined": quarantined}


def check_circulation(sources: dict[str, dict[str, str]], r: Report) -> dict:
    """Same value, different declared roots => one of the two is wrong."""
    by_number: dict[str, list[tuple[str, str]]] = {}
    for sid, fm in sources.items():
        root = fm.get("root", "unclear")
        for sig in numbers_in(fm.get("_body", "")):
            by_number.setdefault(sig, []).append((sid, root))

    flags: list[dict] = []
    for sig, holders in sorted(by_number.items()):
        roots = {root for _, root in holders}
        # `own` is a class, not an id: two sources both claiming `own` for the SAME
        # value is exactly the suspicious case, so it is not treated as distinct here.
        if len(holders) >= 2 and len(roots) >= 2:
            flags.append(
                {
                    "value_sig": sig,
                    "sources": [s for s, _ in holders],
                    "roots": sorted(roots),
                }
            )
            r.warn(
                f"value ~{sig} appears in {', '.join(s for s, _ in holders)} with different "
                f"roots ({', '.join(sorted(roots))}) — either a root is misattributed or the "
                f"same figure is circulating as if independently sourced"
            )
    return {"circulation_flags": flags}


def check_ledger(d: Path, r: Report) -> dict:
    """Quantitative claims must carry as_of and may not be `high` without it."""
    ledger = d / "claims.csv"
    if not ledger.is_file():
        return {"numeric_claims": 0}
    rows = list(csv.DictReader(ledger.read_text(encoding="utf-8").splitlines()))
    numeric = 0
    for row in rows:
        claim = row.get("claim", "")
        if not numbers_in(claim):
            continue
        numeric += 1
        as_of = (row.get("as_of") or "-").strip().lower()
        cid = row.get("claim_id", "?")
        if as_of in {"", "-", "unknown"}:
            r.warn(
                f"{cid}: quantitative claim without data date (as_of={as_of or 'empty'})"
            )
            if (row.get("confidence") or "").strip().lower() == "high":
                r.err(
                    f"{cid}: confidence=high on a number with no data date — "
                    f"cap at medium or establish data_as_of"
                )
    return {"numeric_claims": numeric}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any error")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    r = Report()
    sources = load_sources(d)
    if not sources:
        print(f"No sources/ in {d} — nothing to check")
        return 0

    result: dict = {"research_dir": str(d), "sources_scanned": len(sources)}
    result |= check_fail_closed(d, sources, r)
    result |= check_circulation(sources, r)
    result |= check_ledger(d, r)
    result["errors"] = r.errors
    result["warnings"] = r.warnings

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Number provenance: {d}   ({len(sources)} sources)")
        for m in r.errors:
            print(f"  ERROR   {m}")
        for m in r.warnings:
            print(f"  warn    {m}")
        if not r.errors and not r.warnings:
            print(
                "  OK — every number is traceable and no value circulates across roots"
            )

    if args.strict and r.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
