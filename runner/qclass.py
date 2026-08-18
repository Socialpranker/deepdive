#!/usr/bin/env python3
"""Sub-question classes — the second axis of the prior (channel x qclass).

Mirrors the rows of the dispatch matrix in references/source_dispatch.md. Without
this axis a prior averages incomparable things: `academic` is excellent for
scientific-claim and useless for pricing.
"""

from __future__ import annotations

QCLASSES: tuple[str, ...] = (
    "market-size",
    "time-series",
    "scientific-claim",
    "players",
    "country-stat",
    "how-it-works",
    "recent-change",
    "regulation",
    "benchmark",
    "sentiment",
    "adoption",
    "pricing",
    "crypto",
    "health",
    "climate",
    "jobs",
    "qualitative",
)

DEFAULT_QCLASS = "qualitative"


def normalize_qclass(raw: str) -> str:
    """Unknown input degrades to the default instead of raising.

    A sub-question that matches no matrix row is already handled by source_dispatch
    as ad-hoc; crashing the allocator over it would be worse than a weaker prior.
    """
    cleaned = (raw or "").strip().lower()
    return cleaned if cleaned in QCLASSES else DEFAULT_QCLASS
