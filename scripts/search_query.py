#!/usr/bin/env python3
"""Query a real search-engine API directly (Brave / Tavily / Exa / Firecrawl),
bypassing the harness's own WebSearch. Purpose: a second, independent search
trajectory — see references/capability_discovery.md and references/source_dispatch.md
for when Phase 4 must use this instead of (or alongside) WebSearch.

Usage:
    python3 scripts/search_query.py --engine auto --qclass scientific-claim --query "..."
    python3 scripts/search_query.py --engine brave --query "..." [--n 10] [--json]
    python3 scripts/search_query.py --engine tavily --query "..."
    python3 scripts/search_query.py --engine exa --query "..."
    python3 scripts/search_query.py --engine firecrawl --query "..."

`--engine auto` picks the first engine in ENGINE_ROUTES[qclass] whose key is set
and prints the choice to stderr; unknown or missing --qclass falls back to the
default class (runner.qclass.normalize_qclass).

Reads the API key from env: BRAVE_SEARCH_API_KEY, TAVILY_API_KEY, EXA_API_KEY,
FIRECRAWL_API_KEY.
Exit codes: 0 ok, 1 request/HTTP error, 2 missing API key, 3 bad arguments.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.qclass import normalize_qclass  # noqa: E402

ENV_VARS = {
    "brave": "BRAVE_SEARCH_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "firecrawl": "FIRECRAWL_API_KEY",
}

# Engine order per sub-question class for --engine auto. Every route lists all
# engines, so any single key still yields a second trajectory.
# - exa first where the answer lives in papers and long-form text: its semantic
#   index is the furthest from a keyword engine.
# - brave moves up only where freshness matters; otherwise it sits low because it
#   is a classic keyword index, the kind of trajectory harness WebSearch already
#   gives, and the axis exists to diverge from it.
# - firecrawl is last: the normalizer keeps only its description, so the
#   full-page content that distinguishes it is not used here.
# The order is a starting hypothesis; overlap_rate in plan.md §15 is what should
# move it.
_SEMANTIC = ("exa", "tavily", "brave", "firecrawl")
_FRESH = ("tavily", "brave", "exa", "firecrawl")
_FACTUAL = ("tavily", "exa", "brave", "firecrawl")

ENGINE_ROUTES: dict[str, tuple[str, ...]] = {
    "scientific-claim": _SEMANTIC,
    "how-it-works": _SEMANTIC,
    "benchmark": _SEMANTIC,
    "health": _SEMANTIC,
    "climate": _SEMANTIC,
    "qualitative": _SEMANTIC,
    "players": _SEMANTIC,
    "recent-change": _FRESH,
    "sentiment": _FRESH,
    "crypto": _FRESH,
    "market-size": _FACTUAL,
    "time-series": _FACTUAL,
    "country-stat": _FACTUAL,
    "regulation": _FACTUAL,
    "adoption": _FACTUAL,
    "pricing": _FACTUAL,
    "jobs": _FACTUAL,
}


def resolve_engine(qclass: str | None, env: dict) -> str:
    """First engine of the qclass route with a key set; SystemExit(2) if none."""
    route = ENGINE_ROUTES[normalize_qclass(qclass or "")]
    for engine in route:
        if _get_key(engine, env):
            return engine
    names = ", ".join(ENV_VARS[e] for e in route)
    print(f"error: no search API key set — set one of {names}", file=sys.stderr)
    raise SystemExit(2)

FIRECRAWL_SNIPPET_MAX_CHARS = 1000

TIMEOUT = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_key(engine: str, env: dict) -> str | None:
    return env.get(ENV_VARS[engine]) or None


def _request_brave(query: str, n: int, api_key: str) -> dict:
    return {
        "method": "GET",
        "url": "https://api.search.brave.com/res/v1/web/search",
        "headers": {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
        "params": {"q": query, "count": n},
    }


def _request_tavily(query: str, n: int, api_key: str) -> dict:
    return {
        "method": "POST",
        "url": "https://api.tavily.com/search",
        "headers": {"Content-Type": "application/json"},
        "json": {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": n,
        },
    }


def _request_exa(query: str, n: int, api_key: str) -> dict:
    return {
        "method": "POST",
        "url": "https://api.exa.ai/search",
        "headers": {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
        "json": {
            "query": query,
            "type": "neural",
            "useAutoprompt": True,
            "numResults": n,
        },
    }


def _request_firecrawl(query: str, n: int, api_key: str) -> dict:
    return {
        "method": "POST",
        "url": "https://api.firecrawl.dev/v2/search",
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "json": {
            "query": query,
            "limit": n,
            "origin": "deepdive",
        },
    }


BUILDERS = {
    "brave": _request_brave,
    "tavily": _request_tavily,
    "exa": _request_exa,
    "firecrawl": _request_firecrawl,
}


def build_request(engine: str, query: str, n: int, api_key: str) -> dict:
    return BUILDERS[engine](query, n, api_key)


def _normalize_brave(payload: dict) -> list[dict]:
    results = payload.get("web", {}).get("results", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
        }
        for r in results
    ]


def _normalize_tavily(payload: dict) -> list[dict]:
    results = payload.get("results", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in results
    ]


def _normalize_exa(payload: dict) -> list[dict]:
    results = payload.get("results", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("text", "") or "",
        }
        for r in results
    ]


def _normalize_firecrawl(payload: dict) -> list[dict]:
    results = (payload.get("data") or {}).get("web", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": (r.get("description") or "")[:FIRECRAWL_SNIPPET_MAX_CHARS],
        }
        for r in results
    ]


NORMALIZERS = {
    "brave": _normalize_brave,
    "tavily": _normalize_tavily,
    "exa": _normalize_exa,
    "firecrawl": _normalize_firecrawl,
}


def normalize(engine: str, payload: dict) -> list[dict]:
    fetched_at = _now()
    hits = NORMALIZERS[engine](payload)
    out = []
    for i, h in enumerate(hits, start=1):
        out.append(
            {
                "rank": i,
                "title": h["title"],
                "url": h["url"],
                "snippet": h["snippet"],
                "engine": engine,
                "fetched_at": fetched_at,
            }
        )
    return out


def run_query(engine: str, query: str, n: int, env: dict) -> list[dict]:
    """Raises SystemExit(2) if the key is missing, SystemExit(1) on transport/HTTP error."""
    api_key = _get_key(engine, env)
    if not api_key:
        print(f"error: missing API key — set {ENV_VARS[engine]}", file=sys.stderr)
        raise SystemExit(2)

    req = build_request(engine, query, n, api_key)
    method = req.pop("method")
    try:
        try:
            resp = requests.request(method, timeout=TIMEOUT, **req)
        except requests.RequestException:
            # one retry on transport error
            resp = requests.request(method, timeout=TIMEOUT, **req)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"error: request to {engine} failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    payload = resp.json()
    return normalize(engine, payload)


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=["auto", *sorted(ENV_VARS)])
    parser.add_argument("--qclass", help="sub-question class, used by --engine auto")
    parser.add_argument("--query", required=True)
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    env = dict(os.environ)
    try:
        engine = args.engine
        if engine == "auto":
            engine = resolve_engine(args.qclass, env)
            qclass = normalize_qclass(args.qclass or "")
            print(f"engine: {engine} (qclass {qclass})", file=sys.stderr)
        hits = run_query(engine, args.query, args.n, env)
    except SystemExit as exc:
        return exc.code

    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            print(f"{h['rank']:>2}  {h['title']} — {h['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
