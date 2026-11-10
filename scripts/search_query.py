#!/usr/bin/env python3
"""Query a real search-engine API directly (Brave / Tavily / Exa / SerpBase),
bypassing the harness's own WebSearch. Purpose: a second, independent search
trajectory — see references/capability_discovery.md and references/source_dispatch.md
for when Phase 4 must use this instead of (or alongside) WebSearch.

Usage:
    python3 scripts/search_query.py --engine brave --query "..." [--n 10] [--json]
    python3 scripts/search_query.py --engine tavily --query "..."
    python3 scripts/search_query.py --engine exa --query "..."
    python3 scripts/search_query.py --engine serpbase --query "..." [--n 10] [--json]

Reads the API key from env: BRAVE_SEARCH_API_KEY, TAVILY_API_KEY, EXA_API_KEY,
SERPBASE_API_KEY.
Exit codes: 0 ok, 1 request/HTTP error, 2 missing API key, 3 bad arguments.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import requests

ENV_VARS = {
    "brave": "BRAVE_SEARCH_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "serpbase": "SERPBASE_API_KEY",
}

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


def _request_serpbase(query: str, n: int, api_key: str) -> dict:
    return {
        "method": "GET",
        "url": "https://api.serpbase.dev/google/search",
        "headers": {
            "Accept": "application/json",
            "X-API-Key": api_key,
        },
        "params": {"q": query, "num": n},
    }


BUILDERS = {
    "brave": _request_brave,
    "tavily": _request_tavily,
    "exa": _request_exa,
    "serpbase": _request_serpbase,
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


def _normalize_serpbase(payload: dict) -> list[dict]:
    results = payload.get("organic", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", ""),
        }
        for r in results
    ]


NORMALIZERS = {
    "brave": _normalize_brave,
    "tavily": _normalize_tavily,
    "exa": _normalize_exa,
    "serpbase": _normalize_serpbase,
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
    parser.add_argument("--engine", required=True, choices=sorted(ENV_VARS))
    parser.add_argument("--query", required=True)
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        hits = run_query(args.engine, args.query, args.n, dict(os.environ))
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
