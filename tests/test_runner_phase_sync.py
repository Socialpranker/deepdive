"""Canary: does the runner scaffold still match the methodology's phase list?

The runner (`runner/orchestrator.py`) is a deliberately smaller, UNSYNCED subset of the
skill methodology — see `runner/DESIGN.md` "Scope & sync boundary". `phases.yaml` is the
single source of truth (currently 11 phases); the runner implements 8.

This test is a CANARY, not a gate: it WARNS when the gap changes so it stays visible in
CI output, but it does NOT fail. Parity with the skill is explicitly not a goal without a
driving use case. If you close the gap (grow the runner) or widen it (add a skill phase),
update `Orchestrator.IMPLEMENTED_PHASE_IDS` and this test's `KNOWN_MISSING` so the canary
reflects the intended state.
"""
import sys
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "runner"))

import phases_manifest  # noqa: E402
from orchestrator import Orchestrator  # noqa: E402

# Phases intentionally absent from the runner scaffold, as of 2026-07-16.
# Update this set when the intended gap changes (see DESIGN.md).
KNOWN_MISSING = {"3.7", "5.5"}


def test_runner_phase_sync():
    all_ids = {p["id"] for p in phases_manifest.load_phases(REPO / "phases.yaml")}
    implemented = set(Orchestrator.IMPLEMENTED_PHASE_IDS)

    # Sanity: the runner must not claim phases that don't exist in the source of truth.
    assert implemented <= all_ids, (
        f"runner claims phases absent from phases.yaml: {implemented - all_ids}"
    )

    missing = all_ids - implemented
    if missing != KNOWN_MISSING:
        warnings.warn(
            "Runner/skill phase gap CHANGED — this is a canary, not a failure.\n"
            f"  phases.yaml has {len(all_ids)} phases; runner implements {len(implemented)}.\n"
            f"  Missing from runner now: {sorted(missing)}\n"
            f"  Previously known-missing: {sorted(KNOWN_MISSING)}\n"
            "  Update Orchestrator.IMPLEMENTED_PHASE_IDS and KNOWN_MISSING if this is intended.\n"
            "  See runner/DESIGN.md 'Scope & sync boundary'.",
            stacklevel=2,
        )
    # No assertion on `missing`: parity is not required (runner is an experiment).
