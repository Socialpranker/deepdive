#!/usr/bin/env python3
"""
Validate API endpoints in references/api_sources/.

Reads all api_sources/**/*.md files, extracts URLs from the "Endpoint base:" field,
performs HEAD requests, reports which endpoints are alive vs dead.

Output: scripts/output/endpoints_report.md

Usage:
    python scripts/validate_endpoints.py
    python scripts/validate_endpoints.py --json     # also write endpoints_report.json
    python scripts/validate_endpoints.py --strict   # exit 1 if any dead

Designed to be run by GitHub Actions cron (weekly).
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
    print("ERROR: 'requests' library required. Run: pip install requests")
    sys.exit(1)


REPO_ROOT = Path(__file__).parent.parent
API_SOURCES_DIR = REPO_ROOT / "references" / "api_sources"
OUTPUT_DIR = Path(__file__).parent / "output"

USER_AGENT = "claude-deep-research-validator/1.0 (https://github.com/your-username/claude-deep-research)"
TIMEOUT_SECONDS = 10
DELAY_BETWEEN_REQUESTS = 0.5  # politeness


def find_api_files() -> list[Path]:
    """Find all API documentation files."""
    if not API_SOURCES_DIR.exists():
        print(f"ERROR: {API_SOURCES_DIR} does not exist")
        sys.exit(1)
    return sorted(API_SOURCES_DIR.rglob("*.md"))


def extract_endpoint(file_path: Path) -> str | None:
    """Extract Endpoint base URL from API doc."""
    content = file_path.read_text(encoding="utf-8")
    # Pattern: "- **Endpoint base:** `https://...`"
    match = re.search(
        r"\*\*Endpoint base:\*\*\s*`([^`]+)`",
        content,
    )
    if match:
        return match.group(1).strip()
    return None


def check_endpoint(url: str) -> tuple[bool, int | str, float]:
    """
    HEAD request to endpoint. Returns (alive, status_code_or_error, response_time_ms).

    Falls back to GET if HEAD not supported (some APIs reject HEAD).
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "INVALID_URL", 0.0

    headers = {"User-Agent": USER_AGENT}

    try:
        start = time.time()
        response = requests.head(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        elapsed_ms = (time.time() - start) * 1000

        # Some APIs return 405 for HEAD; try GET
        if response.status_code == 405:
            start = time.time()
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            elapsed_ms = (time.time() - start) * 1000

        # 2xx, 3xx, 401, 403 considered alive (alive but requires auth)
        alive = response.status_code < 500 and response.status_code != 404
        return alive, response.status_code, elapsed_ms

    except requests.exceptions.Timeout:
        return False, "TIMEOUT", 0.0
    except requests.exceptions.ConnectionError:
        return False, "CONNECTION_ERROR", 0.0
    except requests.exceptions.RequestException as e:
        return False, f"ERROR: {type(e).__name__}", 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Also write JSON report")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any endpoint dead")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    files = find_api_files()
    # Skip INDEX.md and README.md
    files = [f for f in files if f.name not in ("INDEX.md", "README.md")]

    print(f"Validating {len(files)} API endpoint files...")

    results = []
    for f in files:
        rel_path = f.relative_to(REPO_ROOT)
        url = extract_endpoint(f)

        if not url:
            results.append({
                "file": str(rel_path),
                "url": None,
                "alive": None,
                "status": "NO_ENDPOINT_IN_FILE",
                "ms": 0,
            })
            print(f"  ⚠  {rel_path}: no endpoint found")
            continue

        alive, status, ms = check_endpoint(url)
        results.append({
            "file": str(rel_path),
            "url": url,
            "alive": alive,
            "status": status,
            "ms": round(ms, 1),
        })

        icon = "✅" if alive else "❌"
        print(f"  {icon}  {rel_path}: {status} ({ms:.0f}ms)")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Write Markdown report
    md_path = OUTPUT_DIR / "endpoints_report.md"
    write_markdown_report(md_path, results)
    print(f"\nReport saved: {md_path}")

    # Optional JSON
    if args.json:
        json_path = OUTPUT_DIR / "endpoints_report.json"
        json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON saved: {json_path}")

    # Summary
    total = len(results)
    alive = sum(1 for r in results if r["alive"] is True)
    dead = sum(1 for r in results if r["alive"] is False)
    no_endpoint = sum(1 for r in results if r["alive"] is None)
    print(f"\nSummary: {alive} alive, {dead} dead, {no_endpoint} no endpoint of {total} files")

    if args.strict and dead > 0:
        return 1
    return 0


def write_markdown_report(path: Path, results: list[dict]) -> None:
    """Write human-readable Markdown report."""
    lines = [
        "# API Endpoints Validation Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
    ]

    total = len(results)
    alive = sum(1 for r in results if r["alive"] is True)
    dead = sum(1 for r in results if r["alive"] is False)
    no_endpoint = sum(1 for r in results if r["alive"] is None)

    lines += [
        "## Summary",
        "",
        f"- **Total files:** {total}",
        f"- ✅ **Alive:** {alive}",
        f"- ❌ **Dead:** {dead}",
        f"- ⚠ **No endpoint extracted:** {no_endpoint}",
        "",
        "## Details",
        "",
        "| File | URL | Status | Response (ms) |",
        "|---|---|---|---|",
    ]

    # Sort: dead first (so they catch eye), then alive
    def sort_key(r):
        return (r["alive"] is True, r["alive"] is None, r["file"])
    for r in sorted(results, key=sort_key):
        icon = "✅" if r["alive"] is True else ("❌" if r["alive"] is False else "⚠")
        url = r["url"] or "—"
        if len(url) > 50:
            url = url[:47] + "..."
        lines.append(
            f"| `{r['file']}` | `{url}` | {icon} {r['status']} | {r['ms']} |"
        )

    if dead > 0:
        lines += [
            "",
            "## Action items",
            "",
            "Dead endpoints need investigation:",
        ]
        for r in results:
            if r["alive"] is False:
                lines.append(f"- `{r['file']}`: {r['status']} for `{r['url']}`")

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
