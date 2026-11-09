"""Capped console output for the scripts a run calls repeatedly.

Every printed line lands in the orchestrator's context, and the gate scripts run
5-8 times per run: an uncapped warning list is re-read on each call.
"""

CAP_ERRORS = 15
CAP_WARNINGS = 5


def capped(lines, cap: int, verbose: bool) -> list[str]:
    lines = list(lines)
    if verbose or len(lines) <= cap:
        return lines
    return lines[:cap] + [f"  … {len(lines) - cap} more, rerun with --verbose for all"]
