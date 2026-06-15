"""Phase 7 — refresh targets generation.

Pure extraction + rendering for <slug>/refresh_targets.md (the entry point for a
future `update <slug>` delta-research run). No network, no I/O — the orchestrator
reads RunState and writes the file. Mirrors scoring.py / verify.py.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

try:
    from .scoring import hypothesis_ids
except ImportError:  # run as a script
    from scoring import hypothesis_ids

DATA_DOMAINS = ("fred", "worldbank", "statista", "oecd", "data.gov", "stlouisfed")


def extract_hypotheses(hypotheses: list[str], triangulation: list[dict]) -> list[dict]:
    """Pair each hypothesis with its triangulation status.

    supported   = has supporting types and not under_triangulated
    inconclusive = under_triangulated, or no triangulation record
    """
    by_id = {row.get("id"): row for row in triangulation}
    ids = hypothesis_ids(hypotheses)
    out = []
    for hid, raw in zip(ids, hypotheses):
        text = raw.split(":", 1)[1].strip() if ":" in raw else raw.strip()
        row = by_id.get(hid)
        n_sup = row.get("distinct_types_supporting", 0) if row else 0
        under = row.get("under_triangulated", True) if row else True
        status = "supported" if (n_sup > 0 and not under) else "inconclusive"
        out.append({"id": hid, "text": text, "status": status,
                    "supporting_types": n_sup})
    return out


def extract_entities(sources: list[dict]) -> list[dict]:
    """One entity per distinct URL domain, first source wins. Skips empty URLs."""
    seen: set[str] = set()
    out = []
    for src in sources:
        url = (src.get("url") or "").strip()
        if not url:
            continue
        domain = urlsplit(url).netloc
        if not domain or domain in seen:
            continue
        seen.add(domain)
        out.append({"domain": domain, "url": url,
                    "why": (src.get("claim") or "").strip()})
    return out


def extract_numbers(sources: list[dict]) -> list[dict]:
    """Sources whose claim contains a digit, or whose URL is a known data domain."""
    out = []
    for src in sources:
        claim = (src.get("claim") or "").strip()
        url = (src.get("url") or "").strip()
        is_data_domain = any(d in url.lower() for d in DATA_DOMAINS)
        if not (re.search(r"\d", claim) or is_data_domain):
            continue
        out.append({"phrase": claim or url, "url": url})
    return out
