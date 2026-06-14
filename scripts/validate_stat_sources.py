#!/usr/bin/env python3
"""
Validate the stat_sources catalog — the part the weekly endpoint-sync doesn't cover.

scripts/validate_endpoints.py HEAD-checks the ~30 API endpoints. But the catalog's
real bulk is references/stat_sources/ — ~210 HTML data portals across core/ and
industries/. Those are never checked, so dead/renamed portals rot silently and the
"280+ sources" claim erodes trust the moment someone clicks a 404.

This extracts every URL from the stat_sources markdown, resolves it, and produces a
verified/dead/unknown report. Use it to (a) prune dead entries and (b) split the
catalog into a small VERIFIED core and a larger COMMUNITY tier — honest breadth beats
inflated breadth.

Markdown convention assumed: URLs appear as markdown links [label](http...) or bare
http(s) URLs in the source tables. Both are picked up.

Usage:
    python scripts/validate_stat_sources.py
    python scripts/validate_stat_sources.py --dir references/stat_sources/core
    python scripts/validate_stat_sources.py --json report.json --strict   # exit 1 if dead found
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' required. Run: pip install -r scripts/requirements.txt")
    sys.exit(1)

UA = "claude-deep-research-statcheck/1.0 (+https://github.com/Socialpranker/claude-deep-research)"
TIMEOUT = 12
DELAY = 0.3
URL_RE = re.compile(r"\[(?:[^\]]*)\]\((https?://[^)\s]+)\)|(?<![\w(])(https?://[^\s)\]<>\"']+)")


def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False  # ignore local proxy, same rationale as check_citations.py
    s.headers["User-Agent"] = UA
    return s


def extract_urls(md_dir: Path) -> dict[str, list[str]]:
    """url -> list of files it appears in."""
    found: dict[str, list[str]] = {}
    for f in sorted(md_dir.rglob("*.md")):
        if f.name in {"INDEX.md", "README.md"}:
            continue
        for m in URL_RE.finditer(f.read_text(encoding="utf-8")):
            url = (m.group(1) or m.group(2)).rstrip(".,;")
            host = urlparse(url).netloc
            if not host:
                continue
            found.setdefault(url, []).append(f.relative_to(md_dir).as_posix())
    return found


def check(sess: requests.Session, url: str) -> tuple[str, bool, bool]:
    """Return (status_label, alive, checkable). HEAD first, GET fallback."""
    for method in (sess.head, sess.get):
        try:
            resp = method(url, timeout=TIMEOUT, allow_redirects=True)
            code = resp.status_code
            # many portals reject HEAD with 405 — retry as GET
            if method is sess.head and code in (403, 405, 501):
                continue
            alive = code < 400 or code in (401, 403)
            return str(code), alive, True
        except requests.exceptions.RequestException as e:
            label = type(e).__name__
    return label, False, False  # transport failure → unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=Path("references/stat_sources"))
    ap.add_argument("--json", type=Path)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any URL confirmed dead")
    ap.add_argument("--limit", type=int, default=0, help="Check only first N (smoke test)")
    args = ap.parse_args()

    if not args.dir.is_dir():
        print(f"ERROR: not a directory: {args.dir}")
        return 2

    urls = extract_urls(args.dir)
    items = sorted(urls)
    if args.limit:
        items = items[:args.limit]
    print(f"Found {len(urls)} unique URLs under {args.dir}; checking {len(items)} ...")

    sess = session()
    dead, unknown, alive = [], [], []
    results = []
    for url in items:
        status, is_alive, checkable = check(sess, url)
        rec = {"url": url, "status": status, "alive": is_alive,
               "checkable": checkable, "files": urls[url]}
        results.append(rec)
        if not checkable:
            unknown.append(rec)
            icon = "?"
        elif is_alive:
            alive.append(rec)
            icon = "OK"
        else:
            dead.append(rec)
            icon = "DEAD"
        print(f"  {icon:4} [{status}] {url}")
        time.sleep(DELAY)

    print(f"\nalive {len(alive)} · dead {len(dead)} · unknown {len(unknown)}")
    if dead:
        print("\nDEAD (prune or replace):")
        for r in dead:
            print(f"  [{r['status']}] {r['url']}  — in {', '.join(r['files'])}")

    if args.json:
        args.json.write_text(json.dumps({"checked": len(items), "alive": len(alive),
                                         "dead": len(dead), "unknown": len(unknown),
                                         "results": results}, indent=2), encoding="utf-8")
        print(f"JSON: {args.json}")

    if args.strict and dead:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
