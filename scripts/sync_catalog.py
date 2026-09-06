#!/usr/bin/env python3
"""
Sync catalog with upstream awesome-lists — discover potential additions.

Checks upstream awesome-lists from references/awesome_lists_registry.md
and identifies APIs/datasets that might be worth adding to our catalog.

This script does NOT modify catalog files automatically — it produces a
discovery report that maintainers review before creating PRs.

Output: scripts/output/sync_report.md

Usage:
    python scripts/sync_catalog.py
    python scripts/sync_catalog.py --upstream public-apis  # check specific upstream

Designed for GitHub Actions weekly cron.
"""

import argparse
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
OUTPUT_DIR = Path(__file__).parent / "output"

USER_AGENT = "deepdive-sync/1.0"
TIMEOUT_SECONDS = 15

# Upstream awesome-lists to check
UPSTREAMS = {
    "public-apis": {
        "url": "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
        "category_regex": r"^### (\w[\w &-]+)",
        "entry_regex": r"\| \[([^\]]+)\]\(([^)]+)\) \|",
    },
    "awesome-public-datasets": {
        "url": "https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/master/README.rst",
        "category_regex": r"^([A-Z][A-Za-z+]+)$",
        "entry_regex": r"\* \[([^\]]+)\]\(([^)]+)\)",
    },
}


def fetch_upstream(name: str, config: dict) -> str | None:
    """Fetch upstream README content."""
    print(f"Fetching upstream: {name}")
    try:
        response = requests.get(
            config["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.text
        print(f"  ⚠  HTTP {response.status_code} for {config['url']}")
    except requests.exceptions.RequestException as e:
        print(f"  ❌  {type(e).__name__}: {e}")
    return None


def extract_my_known_urls() -> set[str]:
    """Extract all URLs already documented in our catalog."""
    known = set()

    # Check api_sources
    api_dir = REPO_ROOT / "references" / "api_sources"
    if api_dir.exists():
        for f in api_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8")
            # Find URLs in backticks or markdown links
            urls = re.findall(r"`(https?://[^`]+)`|\]\((https?://[^)]+)\)", content)
            for url_pair in urls:
                url = url_pair[0] or url_pair[1]
                if url:
                    # Normalize: keep only domain for comparison
                    domain = urlparse(url).netloc.replace("www.", "")
                    if domain:
                        known.add(domain)

    # Check stat_sources
    stat_dir = REPO_ROOT / "references" / "stat_sources"
    if stat_dir.exists():
        for f in stat_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8")
            urls = re.findall(r"`(https?://[^`]+)`|\]\((https?://[^)]+)\)", content)
            for url_pair in urls:
                url = url_pair[0] or url_pair[1]
                if url:
                    domain = urlparse(url).netloc.replace("www.", "")
                    if domain:
                        known.add(domain)

    return known


def find_new_entries(upstream_content: str, config: dict, known_domains: set[str]) -> list[dict]:
    """Find entries in upstream that aren't in our catalog."""
    new = []

    # Try to parse table-format (public-apis style)
    table_pattern = r"\| \[([^\]]+)\]\(([^)]+)\) \|([^\|]*)\|"
    matches = re.findall(table_pattern, upstream_content)

    for name, url, description in matches:
        domain = urlparse(url).netloc.replace("www.", "")
        if domain and domain not in known_domains:
            new.append({
                "name": name.strip(),
                "url": url.strip(),
                "domain": domain,
                "description": description.strip()[:200],
            })

    return new


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", help="Check specific upstream only")
    parser.add_argument("--limit", type=int, default=30, help="Max entries per upstream in report")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    known = extract_my_known_urls()
    print(f"My catalog covers {len(known)} unique domains")

    upstreams_to_check = {args.upstream: UPSTREAMS[args.upstream]} if args.upstream else UPSTREAMS

    all_results = {}
    for name, config in upstreams_to_check.items():
        content = fetch_upstream(name, config)
        if not content:
            all_results[name] = {"error": "fetch_failed"}
            continue

        new_entries = find_new_entries(content, config, known)
        all_results[name] = {
            "total_in_upstream": "many",  # rough estimate
            "new_in_catalog": new_entries[:args.limit],
            "total_new": len(new_entries),
        }
        print(f"  {name}: {len(new_entries)} potential additions")
        time.sleep(1)

    # Write report
    report_path = OUTPUT_DIR / "sync_report.md"
    write_sync_report(report_path, all_results, args.limit)
    print(f"\nReport saved: {report_path}")

    # Summary
    total_new = sum(r.get("total_new", 0) for r in all_results.values())
    print(f"Total potential additions across upstreams: {total_new}")

    return 0


def write_sync_report(path: Path, results: dict, limit: int) -> None:
    """Write Markdown sync report."""
    lines = [
        "# Catalog Sync Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "Potential additions discovered in upstream awesome-lists.",
        "Maintainers should review and PR worthwhile entries into our catalog.",
        "",
        "## Summary",
        "",
    ]

    for name, data in results.items():
        if "error" in data:
            lines.append(f"- ❌ **{name}**: {data['error']}")
        else:
            total = data.get("total_new", 0)
            shown = min(total, limit)
            lines.append(f"- ✅ **{name}**: {total} new entries (showing top {shown})")

    lines.append("")

    for name, data in results.items():
        if "error" in data or not data.get("new_in_catalog"):
            continue

        lines += [
            f"## {name}",
            "",
            "| Name | URL | Description |",
            "|---|---|---|",
        ]

        for entry in data["new_in_catalog"]:
            desc = entry["description"][:80].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {entry['name']} | {entry['url']} | {desc} |")

        lines.append("")

    lines += [
        "## Next steps",
        "",
        "For each entry worth adding:",
        "1. Verify the API/source is still live",
        "2. Identify the right category folder (api_sources/<cat>/ or stat_sources/<cat>/)",
        "3. Fill the entry template (see CONTRIBUTING.md)",
        "4. Submit a PR with the new file",
        "",
        "Entries NOT to add automatically — review needed:",
        "- Quality varies in upstreams (predatory APIs, deprecated, low usage)",
        "- Some are duplicates we already document under different domain",
        "- License/auth requirements may not fit our criteria",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
