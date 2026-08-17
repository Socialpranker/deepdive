#!/usr/bin/env python3
"""Arithmetic checker for the numbers a run puts its name under.

`check_number_provenance.py` answers "where did this number come from". Nothing
answers "does it add up". A derived figure — a percentage, a share, a growth rate,
a ratio — is computed by the model in prose, and a computation done in prose is
never re-done: the report states 34.2% and every later layer verifies that the
SOURCE was quoted correctly, not that 1710/5000 is 34.2%.

This script closes that gap for the numbers that carry weight. The run declares
them in `numbers.csv`; the script recomputes each derived value from its own
declared inputs and compares. Deterministic, no model in the loop.

Checks:
  1. derived     — `formula` recomputed from `inputs`, compared to `value` within
                   tolerance. A mismatch is an error, with both numbers shown.
  2. share       — values sharing a `group` must sum to 100 (unit `%`).
  3. fail-closed — a figure that LOOKS derived (%, ×, п.п.) in memo.md must have a
                   row in numbers.csv. An unregistered derived number was never
                   recomputed by anything.
  4. hygiene     — kind/unit/inputs consistency, claim_id resolvable, sources present.

Usage:
    python scripts/check_number_arithmetic.py --research-dir research/<slug>
    python scripts/check_number_arithmetic.py --research-dir research/<slug> --strict
    python scripts/check_number_arithmetic.py --research-dir research/<slug> --json
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from pathlib import Path

KINDS = {"verbatim", "derived", "share"}
REQUIRED_COLUMNS = ("num_id", "value", "kind")
EMPTY = {"", "-", "—"}

# Relative tolerance, and an absolute floor so that small values (a 0.4 pp delta)
# are not held to an unreachable relative bar.
REL_TOLERANCE = 0.01
ABS_TOLERANCE = 0.05
SHARE_TOLERANCE = 0.5

# A number written in one of these shapes is derived by construction: someone
# divided, compared or scaled to produce it.
DERIVED_SHAPES = (
    re.compile(r"(\d+(?:[.,]\d+)?)\s*%"),
    re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:п\.\s?п\.|pp\b|percentage points)"),
    # `×` is not a word character, so a trailing \b would never match after it.
    re.compile(r"(\d+(?:[.,]\d+)?)\s*×"),
    re.compile(r"(\d+(?:[.,]\d+)?)\s*x\b"),
    re.compile(r"в\s+(\d+(?:[.,]\d+)?)\s*раз"),
)
INPUT_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([-+]?[\d.,\s]+)(\[s\d+\])?$")
CITATION_RE = re.compile(r"\[s\d+\]")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def to_float(raw: str) -> float | None:
    """Parse a human-written number: `1 710`, `1,710`, `34.2`, `34,2`."""
    text = raw.strip().replace(" ", "").replace(" ", "")
    if not text or text in EMPTY:
        return None
    # A comma is a decimal separator only when it is the sole separator and is
    # followed by 1-2 digits; otherwise it groups thousands.
    if text.count(",") == 1 and re.search(r",\d{1,2}$", text):
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
}
# Formulas come from a research run's own numbers.csv, but the interpreter below
# walks the AST itself instead of calling eval(): the set of reachable operations
# is the four arithmetic ops plus power, and nothing else exists to reach for.
POW_LIMIT = 64


def safe_eval(formula: str, env: dict[str, float]) -> float | None:
    """Evaluate an arithmetic formula over named inputs, by walking the AST."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError:
        return None
    try:
        return float(_eval_node(tree.body, env))
    except (_BadFormula, ZeroDivisionError, TypeError, ValueError, OverflowError):
        return None


class _BadFormula(Exception):
    """The expression contains something that is not arithmetic."""


def _eval_node(node: ast.AST, env: dict[str, float]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _BadFormula(f"non-numeric constant {node.value!r}")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise _BadFormula(f"undeclared input {node.id}")
        return float(env[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval_node(node.operand, env)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval_node(node.left, env)
        right = _eval_node(node.right, env)
        if isinstance(node.op, ast.Pow) and abs(right) > POW_LIMIT:
            raise _BadFormula("exponent out of range")
        return _BINOPS[type(node.op)](left, right)
    raise _BadFormula(f"unsupported expression {type(node).__name__}")


def parse_inputs(raw: str, num_id: str, r: Report) -> dict[str, float]:
    """`a=1710[s03]; b=5000[s03]` -> {"a": 1710.0, "b": 5000.0}."""
    env: dict[str, float] = {}
    if raw.strip() in EMPTY:
        return env
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        m = INPUT_RE.match(part)
        if not m:
            r.err(
                f"{num_id}: input '{part}' is not `name=value[sNN]` — "
                f"the formula cannot be recomputed from it"
            )
            continue
        name, value_raw, citation = m.groups()
        value = to_float(value_raw)
        if value is None:
            r.err(f"{num_id}: input '{name}' has no parseable value ({value_raw!r})")
            continue
        if not citation:
            r.warn(
                f"{num_id}: input '{name}' carries no [sNN] — its own source is unstated"
            )
        env[name] = value
    return env


def tolerance_for(value: float) -> float:
    return max(abs(value) * REL_TOLERANCE, ABS_TOLERANCE)


def check_rows(rows: list[dict[str, str]], claim_ids: set[str], r: Report) -> dict:
    """Row-level checks: recompute derived values, validate kind/unit hygiene."""
    recomputed = 0
    mismatches: list[dict] = []
    shares: dict[str, list[tuple[str, float]]] = {}
    seen: set[str] = set()

    for row in rows:
        num_id = (row.get("num_id") or "?").strip()
        if num_id in seen:
            r.err(f"{num_id}: duplicate num_id — one id must name one number")
        seen.add(num_id)

        kind = (row.get("kind") or "").strip().lower()
        if kind not in KINDS:
            r.err(
                f"{num_id}: kind={kind or 'empty'} is not one of {'/'.join(sorted(KINDS))}"
            )
            continue

        value = to_float(row.get("value") or "")
        if value is None:
            r.err(f"{num_id}: value {row.get('value')!r} is not a number")
            continue

        formula = (row.get("formula") or "-").strip()
        inputs_raw = row.get("inputs") or "-"
        unit = (row.get("unit") or "-").strip()
        claim_id = (row.get("claim_id") or "-").strip()
        sources = (row.get("sources") or "-").strip()

        if sources in EMPTY:
            r.err(
                f"{num_id}: no sources — a number in the report answers to at least one [sNN]"
            )
        if claim_ids and claim_id not in EMPTY and claim_id not in claim_ids:
            r.warn(f"{num_id}: claim_id {claim_id} is not in claims.csv")

        if kind == "verbatim":
            if formula not in EMPTY or inputs_raw.strip() not in EMPTY:
                r.warn(
                    f"{num_id}: kind=verbatim but a formula/inputs is declared — "
                    f"if it was computed, it is `derived`"
                )
            continue

        if kind == "share":
            group = (row.get("group") or "-").strip()
            if group in EMPTY:
                r.err(f"{num_id}: kind=share without a group — nothing to sum against")
            else:
                shares.setdefault(group, []).append((num_id, value))
            if unit != "%":
                r.warn(
                    f"{num_id}: kind=share with unit={unit or 'empty'} — shares are percentages"
                )
            continue

        # kind == derived
        if formula in EMPTY:
            r.err(f"{num_id}: kind=derived without a formula — nothing to recompute")
            continue
        env = parse_inputs(inputs_raw, num_id, r)
        if not env:
            r.err(
                f"{num_id}: kind=derived without usable inputs — nothing to recompute"
            )
            continue
        calc = safe_eval(formula, env)
        if calc is None:
            r.err(
                f"{num_id}: formula '{formula}' could not be evaluated over "
                f"inputs {sorted(env)} (arithmetic only: + - * / ** and the declared names)"
            )
            continue
        recomputed += 1
        if abs(calc - value) > tolerance_for(value):
            mismatches.append(
                {
                    "num_id": num_id,
                    "stated": value,
                    "recomputed": round(calc, 6),
                    "formula": formula,
                }
            )
            r.err(
                f"{num_id}: stated {value}, recomputed {calc:.6g} from '{formula}' — "
                f"the report's own inputs do not produce the number it prints"
            )

    share_flags: list[dict] = []
    for group, members in sorted(shares.items()):
        total = sum(v for _, v in members)
        if abs(total - 100.0) > SHARE_TOLERANCE:
            share_flags.append(
                {
                    "group": group,
                    "sum": round(total, 4),
                    "members": [m for m, _ in members],
                }
            )
            r.err(
                f"group '{group}': shares sum to {total:.4g}, not 100 "
                f"({', '.join(m for m, _ in members)}) — parts that do not make a whole"
            )

    return {
        "rows": len(rows),
        "recomputed": recomputed,
        "mismatches": mismatches,
        "share_groups": len(shares),
        "share_flags": share_flags,
    }


def derived_shaped_numbers(text: str) -> set[str]:
    """Figures written in a shape only arithmetic produces."""
    out: set[str] = set()
    stripped = CITATION_RE.sub(" ", text)
    for pattern in DERIVED_SHAPES:
        for raw in pattern.findall(stripped):
            value = to_float(raw)
            if value is not None:
                out.add(f"{value:g}")
    return out


def check_memo(d: Path, rows: list[dict[str, str]], r: Report) -> dict:
    """Fail-closed: a derived-looking figure in the memo must be registered."""
    memo = d / "memo.md"
    if not memo.is_file():
        return {"memo_unregistered": []}
    registered = set()
    for row in rows:
        value = to_float(row.get("value") or "")
        if value is not None:
            registered.add(f"{value:g}")
    unregistered = sorted(
        derived_shaped_numbers(memo.read_text(encoding="utf-8")) - registered
    )
    for value in unregistered:
        r.err(
            f"memo.md prints derived figure {value} with no row in numbers.csv — "
            f"nothing recomputed it (register it as derived with its formula, or as "
            f"verbatim if the source states it directly)"
        )
    return {"memo_unregistered": unregistered}


def load_claim_ids(d: Path) -> set[str]:
    ledger = d / "claims.csv"
    if not ledger.is_file():
        return set()
    rows = csv.DictReader(ledger.read_text(encoding="utf-8").splitlines())
    return {(row.get("claim_id") or "").strip() for row in rows} - {""}


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
    numbers = d / "numbers.csv"
    if not numbers.is_file():
        # Absent file is "not run", not "clean" — the phase gate owns whether this
        # run was required to produce one.
        print(f"No numbers.csv in {d} — arithmetic axis not run")
        return 0

    lines = numbers.read_text(encoding="utf-8").splitlines()
    rows = list(csv.DictReader(lines))
    header = {c.strip() for c in (lines[0].split(",") if lines else [])}
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        print(f"ERROR: numbers.csv is missing column(s): {', '.join(missing)}")
        return 2

    result: dict = {"research_dir": str(d)}
    result |= check_rows(rows, load_claim_ids(d), r)
    result |= check_memo(d, rows, r)
    result["errors"] = r.errors
    result["warnings"] = r.warnings

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"Number arithmetic: {d}   ({result['rows']} rows, {result['recomputed']} recomputed)"
        )
        for m in r.errors:
            print(f"  ERROR   {m}")
        for m in r.warnings:
            print(f"  warn    {m}")
        if not r.errors and not r.warnings:
            print("  OK — every derived number reproduces from its own declared inputs")

    if args.strict and r.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
