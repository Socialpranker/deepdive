#!/usr/bin/env python3
"""
Citation integrity check for a deepdive run.

Reads the sources of one research run and verifies each URL actually resolves —
the deterministic guard against hallucinated citations. A source whose access is
OPEN but whose URL 404s is a red flag; a paywalled/closed source that returns
401/403 is expected and not penalised.

Source of URLs, in order of preference:
  1. sources/NN_*.md  — frontmatter `url` / `title` / `access` (current template)
  2. sources.csv      — `url`,`title` columns (older runs have no access/type)
The CSV fallback is required: real runs exist with a populated sources.csv but an
empty sources/ directory.

Output: <research-dir>/../eval_output is NOT used — reports go where --out points,
default ./citation_report.{md,json} next to the script's output dir.

Usage:
    python eval/check_citations.py --research-dir path/to/run
    python eval/check_citations.py --research-dir path/to/run --json
    python eval/check_citations.py --research-dir path/to/run --strict   # exit 1 if any OPEN source dead
"""

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' required. Run: pip install -r scripts/requirements.txt")
    sys.exit(1)

USER_AGENT = "deepdive-citecheck/1.0 (+https://github.com/Socialpranker/deepdive)"
TIMEOUT_SECONDS = 12
DELAY_BETWEEN_REQUESTS = 0.4
# access values that make a non-200 expected rather than a failure
EXPECTED_NON_OPEN = {"paywalled", "paywalled-abstract-only", "closed", "archive-restored", "gray-area-source"}


def make_session() -> requests.Session:
    # trust_env=False: ignore HTTP(S)_PROXY from the environment. Source URLs are
    # public; a local VPN/proxy in env (e.g. 127.0.0.1:1082) returning 503 would
    # otherwise make every check fail with ProxyError. Verified on this machine.
    s = requests.Session()
    s.trust_env = False
    s.headers["User-Agent"] = USER_AGENT
    return s


@dataclass
class Source:
    sid: str
    url: str
    title: str
    access: str  # "OPEN" when unknown — treated as must-resolve


@dataclass
class CiteResult:
    sid: str
    url: str
    access: str
    status: str          # HTTP code or error label
    alive: bool          # got an HTTP response indicating the page exists
    checkable: bool      # we actually reached the server (got any HTTP status)
    title_match: bool | None  # None when not checked (non-OPEN or no body)
    red_flag: bool       # OPEN source confirmed dead (404/5xx) — likely hallucinated

    # Transport failures (DNS/SSL/timeout) are checkable=False: counted as UNKNOWN,
    # excluded from the integrity denominator so a flaky host doesn't sink the score.


def parse_frontmatter_sources(sources_dir: Path) -> list[Source]:
    """Read url/title/access from each sources/NN_*.md frontmatter block."""
    out: list[Source] = []
    for f in sorted(sources_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        block = text.split("---", 2)[1]
        fields = dict(re.findall(r"^(\w+):\s*(.+?)\s*$", block, re.MULTILINE))
        url = fields.get("url", "").strip()
        if not url:
            continue
        out.append(Source(
            sid=fields.get("id", f.stem),
            url=url,
            title=fields.get("title", "").strip(),
            access=fields.get("access", "OPEN").strip().upper() if fields.get("access") else "OPEN",
        ))
    return out


def parse_csv_sources(csv_path: Path) -> list[Source]:
    """Fallback: url/title from sources.csv. Older schema has no access column."""
    out: list[Source] = []
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            url = (row.get("url") or "").strip()
            if not url:
                continue
            access = (row.get("access") or "").strip().upper() or "OPEN"
            out.append(Source(sid=row.get("id", ""), url=url, title=(row.get("title") or "").strip(), access=access))
    return out


def load_sources(research_dir: Path) -> tuple[list[Source], str]:
    """Prefer per-file frontmatter; fall back to sources.csv. Returns (sources, origin)."""
    sources_dir = research_dir / "sources"
    if sources_dir.is_dir():
        fm = parse_frontmatter_sources(sources_dir)
        if fm:
            return fm, "sources/*.md"
    csv_path = research_dir / "sources.csv"
    if csv_path.is_file():
        return parse_csv_sources(csv_path), "sources.csv"
    return [], "none"


def check_url(session: requests.Session, src: Source) -> CiteResult:
    parsed = urlparse(src.url)
    if not parsed.scheme or not parsed.netloc:
        return CiteResult(src.sid, src.url, src.access, "INVALID_URL", False, True, None, src.access == "OPEN")

    is_open = src.access not in {a.upper() for a in EXPECTED_NON_OPEN}

    # One retry on transport errors (SSL/DNS/timeout): hosts like arxiv.org flap,
    # and a single failure shouldn't be read as "page does not exist".
    resp = None
    transport_err = ""
    for attempt in (1, 2):
        try:
            resp = session.get(src.url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            break
        except requests.exceptions.SSLError:
            transport_err = "SSL_ERROR"
        except requests.exceptions.Timeout:
            transport_err = "TIMEOUT"
        except requests.exceptions.ConnectionError:
            transport_err = "CONNECTION_ERROR"
        if attempt == 1:
            time.sleep(1.0)

    if resp is None:
        # Transport failure → UNKNOWN, not a confirmed death. checkable=False, no red flag.
        return CiteResult(src.sid, src.url, src.access, transport_err, False, False, None, False)

    code = resp.status_code
    # 401/403 = alive but auth-gated; <400 = alive. 404/5xx = confirmed dead.
    alive = code < 400 or code in (401, 403)
    title_match = None
    if is_open and alive and src.title and resp.text:
        # crude content match: do the first few title words appear in the page?
        words = [w for w in re.findall(r"\w+", src.title.lower()) if len(w) > 3][:4]
        if words:
            body = resp.text.lower()
            title_match = sum(w in body for w in words) >= max(1, len(words) // 2)

    red_flag = is_open and not alive
    return CiteResult(src.sid, src.url, src.access, str(code), alive, True, title_match, red_flag)


def score(results: list[CiteResult]) -> float:
    """Citation integrity 0..1: alive / checkable. UNKNOWN (transport) excluded from denominator."""
    checkable = [r for r in results if r.checkable]
    if not checkable:
        return 0.0
    return sum(r.alive for r in checkable) / len(checkable)


def write_reports(out_base: Path, research_dir: Path, origin: str, results: list[CiteResult], integrity: float, write_json: bool) -> None:
    red = [r for r in results if r.red_flag]
    mismatched = [r for r in results if r.title_match is False]
    unknown = [r for r in results if not r.checkable]
    checkable_n = len(results) - len(unknown)
    lines = [
        "# Citation Integrity Report",
        "",
        f"Run: `{research_dir}`",
        f"Sources from: `{origin}`",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "## Score",
        "",
        f"- **Citation integrity:** {integrity:.3f}  ({sum(r.alive for r in results)}/{checkable_n} checkable resolved)",
        f"- **Red flags (OPEN but confirmed dead):** {len(red)}",
        f"- **Unknown (transport error, excluded from score):** {len(unknown)}",
        f"- **Title mismatch (live but maybe off-topic):** {len(mismatched)}",
        "",
        "## Details",
        "",
        "| id | access | status | alive | title_match | flag | url |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: (r.alive, not r.red_flag)):
        tm = "—" if r.title_match is None else ("✅" if r.title_match else "⚠")
        flag = "🚩" if r.red_flag else ""
        url = r.url if len(r.url) <= 60 else r.url[:57] + "..."
        lines.append(f"| {r.sid} | {r.access} | {r.status} | {'✅' if r.alive else '❌'} | {tm} | {flag} | `{url}` |")

    if red:
        lines += ["", "## 🚩 Red flags — likely hallucinated or stale citations", ""]
        lines += [f"- `{r.sid}` [{r.status}] {r.url}" for r in red]

    out_base.parent.mkdir(parents=True, exist_ok=True)
    md_path = out_base.with_suffix(".md")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {md_path}")
    if write_json:
        payload = {"research_dir": str(research_dir), "origin": origin, "citation_integrity": integrity,
                   "results": [asdict(r) for r in results]}
        json_path = out_base.with_suffix(".json")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"JSON:   {json_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-dir", required=True, type=Path, help="Folder of one research run")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output" / "citation_report",
                        help="Output base path (without extension)")
    parser.add_argument("--json", action="store_true", help="Also write JSON report")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any OPEN source is dead")
    args = parser.parse_args()

    if not args.research_dir.is_dir():
        print(f"ERROR: not a directory: {args.research_dir}")
        return 2

    sources, origin = load_sources(args.research_dir)
    if not sources:
        print(f"ERROR: no sources found in {args.research_dir} (looked for sources/*.md and sources.csv)")
        return 2

    print(f"Checking {len(sources)} sources from {origin} ...")
    session = make_session()
    results: list[CiteResult] = []
    for src in sources:
        r = check_url(session, src)
        results.append(r)
        icon = "✅" if r.alive else "❌"
        flag = " 🚩" if r.red_flag else ""
        print(f"  {icon} [{r.status}] {src.url}{flag}")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    integrity = score(results)
    print(f"\nCitation integrity: {integrity:.3f}")
    write_reports(args.out, args.research_dir, origin, results, integrity, args.json)

    if args.strict and any(r.red_flag for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
