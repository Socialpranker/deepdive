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

DATA_DOMAINS = ("worldbank", "statista", "oecd", "data.gov", "stlouisfed")


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
        host = urlsplit(url).netloc.lower()
        is_data_domain = any(d in host for d in DATA_DOMAINS)
        if not (re.search(r"\d", claim) or is_data_domain):
            continue
        out.append({"phrase": claim or url, "url": url})
    return out


def extract_carry_forward(deviations_text: str) -> list[dict]:
    """Parse deviations.md: each '## D*' block with a carry_forward line becomes a
    refresh candidate. subquestion defaults to '?' if the block lacks one."""
    out = []
    blocks = re.split(r"^## D\d+\b.*$", deviations_text, flags=re.MULTILINE)
    for block in blocks:
        cf = re.search(r"^- carry_forward:\s*(.+)$", block, flags=re.MULTILINE)
        if not cf:
            continue
        sq = re.search(r"^- subquestion:\s*(.+)$", block, flags=re.MULTILINE)
        subq = sq.group(1).strip() if sq else "?"
        out.append({"subquestion": subq, "carry_forward": cf.group(1).strip()})
    return out
