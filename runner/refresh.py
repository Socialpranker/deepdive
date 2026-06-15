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

_TODO_ENTITY = ("<!-- TODO: pricing/careers/crunchbase split + sha256 hash"
                " — требуют M2/M5 block-render -->")
_TODO_NUMBER = ("<!-- TODO: series id + last_value + API access"
                " — требуют N-block render -->")
_TODO_TOPIC = ("<!-- TODO: OpenAlex concept IDs / GitHub topics / news keywords"
               " — требуют Phase 4 discovery-метаданных в RunState -->")


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


def render_refresh_targets(slug: str, depth: str, hypotheses: list[dict],
                           entities: list[dict], numbers: list[dict],
                           carry: list[dict], *, today: str) -> str:
    """Render <slug>/refresh_targets.md per the Z11 template. Pure: `today` is
    passed in so the output is deterministic in tests."""
    cadence = "30 days" if depth == "deep" else "90 days"
    out = [
        "---",
        f"slug: {slug}",
        f"last_research_date: {today}",
        f"depth: {depth}",
        f"update_cadence: {cadence}",
        "---",
        "",
        f"# Refresh targets — {slug}",
        "",
        "## 1. Entities to track",
    ]
    if entities:
        for e in entities:
            out += [f"### {e['domain']}",
                    f"- **Source URL:** {e['url']}",
                    f"- **Why in scope:** {e['why'] or '—'}", ""]
    else:
        out += ["_none_", ""]
    out.append(_TODO_ENTITY)

    out += ["", "## 2. Numbers to refresh"]
    if numbers:
        for n in numbers:
            out += [f"### {n['phrase']}", f"- **Source:** {n['url'] or '—'}", ""]
    else:
        out += ["_none_", ""]
    out.append(_TODO_NUMBER)

    out += ["", "## 3. Topic markers (discovery)", _TODO_TOPIC]

    out += ["", "## 4. Hypotheses to re-test"]
    if hypotheses:
        for h in hypotheses:
            out += [
                f'### {h["id"]}: "{h["text"]}"',
                f"- **Status at last research:** {h['status']}",
                f"- **Supporting source types:** {h['supporting_types']}",
                f'- **Watch for:** "{h["text"]} failed replication"; '
                "retractions (RetractionWatch); counter-evidence", ""]
    else:
        out += ["_no hypotheses recorded_", ""]

    out += ["", "## 5. Refresh candidates (carry-forward)"]
    if carry:
        for c in carry:
            out.append(f"- **{c['subquestion']}** — {c['carry_forward']}")
    else:
        out.append("_none_")
    out.append("")
    return "\n".join(out)
