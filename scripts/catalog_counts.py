#!/usr/bin/env python3
"""Ground-truth counts for the deep-research catalog.

Counts are derived directly from the files — there is no separate number registry.
These regexes were verified against the tree on 2026-06-13:
  blocks=103, channels=29, stat_sources=461, api=39, genres=6.

Pure read, no side effects. Callable from the stamper and from tests.
"""
from __future__ import annotations

import re
from pathlib import Path

# The six report genres (H2 `## <slug> — ...` in references/genres.md).
# Counted against this known set, not a blind H2 count (genres.md has other H2s).
GENRE_SLUGS = ("qa", "explainer", "decision", "landscape", "validation", "custom")

_BLOCK_RE = re.compile(r"^## [A-Z][0-9]+ —", re.MULTILINE)
_CHANNEL_RE = re.compile(r"^#### [0-9]+\.", re.MULTILINE)
_URL_RE = re.compile(r"^\s*\*\*URL:\*\*", re.MULTILINE)


def _count_blocks(repo: Path) -> int:
    total = 0
    for p in sorted((repo / "references" / "blocks").glob("*.md")):
        if p.name == "INDEX.md":
            continue
        total += len(_BLOCK_RE.findall(p.read_text(encoding="utf-8")))
    return total


def _count_channels(repo: Path) -> int:
    text = (repo / "references" / "channels.md").read_text(encoding="utf-8")
    return len(_CHANNEL_RE.findall(text))


def _count_stat_sources(repo: Path) -> int:
    total = 0
    for p in (repo / "references" / "stat_sources").rglob("*.md"):
        total += len(_URL_RE.findall(p.read_text(encoding="utf-8")))
    return total


def _count_api(repo: Path) -> int:
    root = repo / "references" / "api_sources"
    return sum(
        1
        for p in root.rglob("*.md")
        if p.name not in ("INDEX.md", "README.md")
    )


def _count_genres(repo: Path) -> int:
    text = (repo / "references" / "genres.md").read_text(encoding="utf-8")
    found = {
        slug
        for slug in GENRE_SLUGS
        if re.search(rf"^## {re.escape(slug)} —", text, re.MULTILINE)
    }
    return len(found)


def counts(repo: Path) -> dict[str, int]:
    return {
        "blocks": _count_blocks(repo),
        "channels": _count_channels(repo),
        "stat_sources": _count_stat_sources(repo),
        "api": _count_api(repo),
        "genres": _count_genres(repo),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(counts(Path(__file__).resolve().parents[1]), indent=2))
