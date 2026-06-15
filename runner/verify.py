"""Phase 6.5 — pure verification-rendering logic (no network, no subprocess).

The actual citation check runs in eval/check_citations.py (invoked as a subprocess
by Orchestrator.verify). This module only turns that check's JSON output into the
metric line that replaces the synthesize() placeholder. Mirrors runner.scoring:
deterministic rendering separate from the side-effecting caller.
"""
from __future__ import annotations

import datetime as dt

# Must match the exact line written by Orchestrator.synthesize(); replace() depends on it.
PLACEHOLDER = "> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**"


def render_verification(citations: dict | None) -> str:
    """Turn check_citations.py JSON (or None on failure) into the report metric block.
    None -> 'verification unavailable' (best-effort: offline / checker error)."""
    if citations is None:
        return (
            "> **Citation integrity: verification unavailable — "
            "check_citations.py did not produce a report (offline or error).**"
        )
    results = citations.get("results", [])
    total = len(results)
    verified = sum(1 for r in results if r.get("alive"))
    red_flags = sum(1 for r in results if r.get("red_flag"))
    flag_word = "red flag" if red_flags == 1 else "red flags"
    date = dt.date.today().isoformat()
    return (
        f"> **Citation integrity: {verified}/{total} verified · {red_flags} {flag_word}**\n"
        f"> Verified {date} via check_citations.py · detail: .verify/citations.md"
    )
