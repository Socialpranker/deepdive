"""Phase 5 — pure scoring/triangulation logic (no network).

Mirrors the project split: runner.adaptive holds the pure search-loop logic,
runner.providers holds the network calls. Here, the LLM-facing scoring call lives
in runner.providers.*.score(); this module holds the deterministic arithmetic and
triangulation that consume that call's output.
"""
from __future__ import annotations

# H1..H4 hypothesis ids are derived from the "Hn: ..." prefix produced in Phase 1.
AXES = ("credibility", "recency", "bias")


def compute_total(scores: dict) -> int | None:
    """Sum the three rubric axes. Returns None if any axis is missing — an unscored
    source is an honest skip signal, not a silent zero."""
    if not all(axis in scores for axis in AXES):
        return None
    return sum(int(scores[axis]) for axis in AXES)


def hypothesis_ids(hypotheses: list[str]) -> list[str]:
    """Extract H-ids ('H1', 'H2', ...) from 'H1: claim' strings; fall back to Hn index."""
    ids = []
    for i, h in enumerate(hypotheses, start=1):
        head = h.split(":", 1)[0].strip()
        ids.append(head if head.startswith("H") and head[1:].isdigit() else f"H{i}")
    return ids


def triangulate(scored: list[dict], hypotheses: list[str]) -> list[dict]:
    """For each hypothesis, count DISTINCT source types that support / contradict it.
    A hypothesis backed by < 3 distinct supporting types is under_triangulated."""
    result = []
    for hid in hypothesis_ids(hypotheses):
        supporting_types: set[str] = set()
        contradicting_types: set[str] = set()
        for src in scored:
            stance = (src.get("hypothesis_evidence") or {}).get(hid)
            stype = src.get("type", "Other")
            if stance == "supports":
                supporting_types.add(stype)
            elif stance == "contradicts":
                contradicting_types.add(stype)
        n_sup = len(supporting_types)
        result.append({
            "id": hid,
            "distinct_types_supporting": n_sup,
            "distinct_types_contradicting": len(contradicting_types),
            "under_triangulated": n_sup < 3,
            "note": "",
        })
    return result
