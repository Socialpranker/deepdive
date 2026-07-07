"""Tests for scripts/catalog_counts.py — the ground-truth extractor."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import catalog_counts  # noqa: E402


def test_counts_match_verified_ground_truth():
    """Golden numbers re-verified by regex on 2026-07-07 (blocks: +F9 background,
    +Z12 so-what-for-you). If the catalog grows, update these intentionally — a
    mismatch here means either the catalog changed or a regex broke."""
    c = catalog_counts.counts(REPO)
    assert c["blocks"] == 105
    assert c["channels"] == 29
    assert c["stat_sources"] == 460
    assert c["api"] == 39
    assert c["genres"] == 6


def test_counts_returns_all_keys():
    c = catalog_counts.counts(REPO)
    assert set(c) == {"blocks", "channels", "stat_sources", "api", "genres"}
