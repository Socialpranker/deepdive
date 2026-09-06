"""Phase 3.5 — pure capability-discovery logic (no network).

Mirrors runner.scoring: deterministic helpers live here; the LLM-facing mapping
call lives in the orchestrator method discover_capabilities(). audit_env takes the
environment explicitly so it is testable by injection (never reads os.environ here).
"""

from __future__ import annotations

# 17 known API-key env vars from references/capability_discovery.md.
# BRAVE_SEARCH_API_KEY / TAVILY_API_KEY / EXA_API_KEY are included: each is a
# second, independent search engine (own index / own ranking), not a rebrand of
# harness WebSearch — a second trajectory makes overlap_rate between engines
# measurable (see references/capability_discovery.md, references/source_dispatch.md).
# SERPAPI_KEY stays excluded: no free tier, so auditing it would advertise
# coverage most users can't actually use.
KNOWN_KEYS: tuple[str, ...] = (
    "BRAVE_SEARCH_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "FRED_API_KEY",
    "GITHUB_TOKEN",
    "NEWSAPI_KEY",
    "ALPHA_VANTAGE_KEY",
    "CRUNCHBASE_API_KEY",
    "OPENWEATHER_KEY",
    "ETHERSCAN_KEY",
    "STACKEXCHANGE_KEY",
    "CENSUS_API_KEY",
    "COMPANIES_HOUSE_API_KEY",
    "NCBI_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "DUNE_API_KEY",
    "NASA_API_KEY",
)


def audit_env(env: dict) -> list[dict]:
    """For each known key, whether it is present (non-empty) in `env`.
    Pure: takes env explicitly, never raises."""
    return [{"key": k, "present": bool(env.get(k))} for k in KNOWN_KEYS]


def render_capabilities(audit: list[dict], mapping_text: str) -> str:
    """Markdown block appended to plan.md. Leads with a blank line so it separates
    cleanly from the existing plan body."""
    lines = ["", "## Capabilities check (Phase 3.5)", "", "**API keys:**"]
    for a in audit:
        if a["present"]:
            lines.append(f"- ✅ {a['key']} — authenticated")
        else:
            lines.append(f"- ❌ {a['key']} — not set (fallback to standard web search)")
    lines += ["", "**Subtopic → source mapping:**", "", mapping_text, ""]
    return "\n".join(lines)
