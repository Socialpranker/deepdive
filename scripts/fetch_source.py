#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "scrapling[fetchers]>=0.4.14,<0.5",
#   "markdownify>=0.13",
#   "protego>=0.5",
#   "pyyaml>=6.0",
#   "tld>=0.13",
# ]
# ///
"""Escalating fetcher for Phase 4, used only when WebFetch cannot reach a source.

WebFetch honours robots.txt AI-agent directives, so a growing share of otherwise
public pages come back as "unable to fetch" rather than as content. This script is
the sanctioned second attempt: it fetches with a real browser stack and reports
exactly which tier succeeded, so the provenance lands in the source frontmatter
instead of being silently laundered.

Tiers (tried in order, stops at the first that yields real content):
    http     Fetcher.get with Chrome TLS/header impersonation
    browser  DynamicFetcher — real headless Chromium, runs the page's JS

Deliberately NOT implemented — these are out of scope, not "not yet":
    * Cloudflare / CAPTCHA challenge solving (StealthyFetcher solve_cloudflare)
    * cookies, credentials, or auth headers of any kind
    * paywall or login-wall circumvention

An auth wall or an anti-bot challenge is a terminal result here. The caller falls
back to the existing protocol in channels.md (preprint -> archive -> author copy ->
alternative source) or to a documented endpoint in api_sources/ — a site that
blocks bots almost always has an API that does not.

Content is always extracted with main_content_only=True, which runs scrapling's
prompt-injection sanitiser (drops CSS-hidden and aria-hidden nodes, <template>,
HTML comments, zero-width characters). Fetched pages are untrusted input; a
sub-agent reads this output, so the sanitiser is mandatory, not cosmetic.

Exit codes: 0 ok · 3 robots-disallowed · 4 blocked (auth wall / anti-bot) · 5 error
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timezone, datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

DEFAULT_UA_TOKEN = "deepdive-research"

# Tokens the major AI crawlers answer to. We never send these as our UA; we read
# their robots.txt verdict so the operator sees what the site actually asked for.
AI_CRAWLER_TOKENS = (
    "GPTBot",
    "ClaudeBot",
    "anthropic-ai",
    "CCBot",
    "Google-Extended",
    "PerplexityBot",
    "Bytespider",
)

# A page that returns 200 but is really a wall. Matched against the first 2 KB of
# extracted text, case-insensitively.
BLOCK_MARKERS = (
    "enable js and disable any ad blocker",
    "please enable javascript",
    "you've been blocked by network security",
    "verify you are human",
    "checking your browser before accessing",
    "just a moment...",
    "attention required!",
    "access denied",
    "request unsuccessful",
    "are you a robot",
)

PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscribers only",
    "create a free account to continue",
    "log in to your",
    "sign in to read",
    "this article is for subscribers",
    "developer token",
)

# Below this, "content" is a stub even if the status was 200.
MIN_CONTENT_CHARS = 500


class FetchOutcome:
    """Result of one tier attempt, or of the whole ladder."""

    def __init__(
        self,
        tier: str,
        status: int | None,
        markdown: str,
        verdict: str,
        note: str = "",
        kind: str = "html",
        raw: bytes | None = None,
    ) -> None:
        self.tier = tier
        self.status = status
        self.markdown = markdown
        self.verdict = verdict  # ok | antibot | auth-wall | thin | error
        self.note = note
        self.kind = kind  # html | pdf | feed | text | binary
        self.raw = raw  # populated for every kind except html

    @property
    def ok(self) -> bool:
        return self.verdict == "ok"

    @property
    def size(self) -> int:
        """Comparable payload size regardless of kind — used to rank failures."""
        return len(self.markdown) if self.kind == "html" else len(self.raw or b"")


def _robots_url(url: str) -> str:
    parts = urlparse(url)
    return urlunparse((parts.scheme, parts.netloc, "/robots.txt", "", "", ""))


def decode_robots(body) -> str:
    """Decode a robots.txt body to text.

    scrapling hands back `bytes`. Passing those through str() yields the literal
    "b'User-agent: ...'" repr, which Protego parses as a single junk line and then
    reports zero rules — i.e. "everything is allowed". The failure is silent and
    fail-open, so it stays a named function with a test rather than an inline cast.
    """
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)


def _default_robots_fetch(robots_url: str, timeout: int):
    from scrapling.fetchers import Fetcher

    resp = Fetcher.get(robots_url, timeout=timeout, stealthy_headers=True)
    return resp.status, resp.body


def check_robots(url: str, ua_token: str, timeout: int, fetch=None) -> dict:
    """Return the robots.txt verdict for our UA and, separately, for AI crawlers.

    Two verdicts because they are two different questions. `allowed` is whether a
    generic client may fetch this path — that is the rule we honour by default.
    `ai_disallowed` records whether the site specifically excluded AI crawlers,
    which is information the operator is entitled to see before overriding.

    `fetch` is injectable so the parsing path can be tested against a robots.txt
    that is known to be restrictive.
    """
    from protego import Protego

    fetch = fetch or _default_robots_fetch
    verdict = {
        "robots_url": _robots_url(url),
        "allowed": True,
        "ai_disallowed": [],
        "crawl_delay": None,
        "fetched": False,
        "error": "",
    }
    try:
        status, body = fetch(verdict["robots_url"], timeout)
        if status != 200 or not body:
            # No robots.txt (or unreadable) means no restriction was expressed.
            verdict["error"] = f"robots.txt status {status}"
            return verdict
        parser = Protego.parse(decode_robots(body))
        verdict["fetched"] = True
        verdict["allowed"] = bool(parser.can_fetch(url, ua_token))
        verdict["crawl_delay"] = parser.crawl_delay(ua_token)
        verdict["ai_disallowed"] = [
            token for token in AI_CRAWLER_TOKENS if not parser.can_fetch(url, token)
        ]
    except Exception as exc:  # noqa: BLE001 - robots failure must not abort the fetch
        verdict["error"] = f"{type(exc).__name__}: {exc}"
    return verdict


def sniff_kind(resp) -> str:
    """Classify the payload before anything tries to parse it as a document.

    Feeding a PDF to the HTML parser is not a slow path, it is a crash: lxml
    rejects the NULL bytes with "All strings must be XML compatible" and the whole
    run dies on what is a perfectly good source. Academic channels are mostly PDFs,
    so this check guards the most valuable source type in the skill.

    Feeds are separated for a different reason: markdownifying XML destroys the
    structure that makes a feed worth fetching. The fallback routes point at feeds,
    so this path gets used.
    """
    body = resp.body or b""
    ctype = ""
    headers = getattr(resp, "headers", None)
    if headers:
        try:
            ctype = str(headers.get("content-type") or "").lower()
        except Exception:  # noqa: BLE001 - header access varies by fetcher
            ctype = ""

    if body[:5] == b"%PDF-" or "application/pdf" in ctype:
        return "pdf"

    head = body[:512].lstrip().lower()
    if (
        any(m in head for m in (b"<rss", b"<feed", b"<rdf:rdf"))
        or "rss+xml" in ctype
        or "atom+xml" in ctype
    ):
        return "feed"
    if "html" in ctype or head[:9] == b"<!doctype" or head[:5] == b"<html":
        return "html"
    if "json" in ctype or "xml" in ctype or ctype.startswith("text/"):
        return "text"
    if not ctype and b"<" in head:
        return "html"
    return "binary"


def _to_markdown(page) -> str:
    """Extract main content as markdown, with the prompt-injection sanitiser on."""
    from scrapling.core.shell import Convertor

    chunks = list(
        Convertor._extract_content(
            page,
            extraction_type="markdown",
            css_selector=None,
            main_content_only=True,
        )
    )
    return "\n\n".join(c for c in chunks if c).strip()


MIN_BINARY_BYTES = 1024

# Some sites publish a Crawl-delay measured in minutes. We make at most seven
# probe requests, so cap it rather than stall a research round.
MAX_CRAWL_DELAY = 2.0

SUFFIX_BY_KIND = {"pdf": ".pdf", "feed": ".xml", "text": ".txt", "binary": ".bin"}


def classify_binary(status: int | None, size: int, kind: str) -> tuple[str, str]:
    """Status-only verdict for payloads there is no point reading as text."""
    if status in (401, 402, 407):
        return "auth-wall", f"HTTP {status}"
    if status == 403:
        return "antibot", "HTTP 403"
    if status is None or status >= 400:
        return "error", f"HTTP {status}"
    if size < MIN_BINARY_BYTES:
        return "thin", f"{size} B below {MIN_BINARY_BYTES} threshold for {kind}"
    return "ok", ""


def classify(status: int | None, markdown: str) -> tuple[str, str]:
    """Map (status, content) onto a verdict. Never trust the status alone.

    scrapling returns a populated response object and a zero exit code for a 401
    or a 403 challenge page, so a caller that only checks "did it write a file"
    records a block page as a source.
    """
    head = markdown[:2000].lower()

    for marker in BLOCK_MARKERS:
        if marker in head:
            return "antibot", f"block page matched {marker!r}"
    for marker in PAYWALL_MARKERS:
        if marker in head:
            return "auth-wall", f"paywall page matched {marker!r}"

    if status in (401, 402, 407):
        return "auth-wall", f"HTTP {status}"
    if status == 403:
        return "antibot", "HTTP 403"
    if status == 429:
        return "error", "HTTP 429 rate limited"
    if status is None or status >= 500:
        return "error", f"HTTP {status}"
    if status >= 400:
        return "error", f"HTTP {status}"

    if len(markdown) < MIN_CONTENT_CHARS:
        return "thin", f"{len(markdown)} chars below {MIN_CONTENT_CHARS} threshold"

    return "ok", ""


def build_outcome(tier: str, resp) -> FetchOutcome:
    """Turn a fetcher response into an outcome, routed by payload kind."""
    kind = sniff_kind(resp)
    raw = resp.body or b""

    if kind == "html":
        try:
            markdown = _to_markdown(resp)
        except Exception as exc:  # noqa: BLE001 - a mis-sniffed payload must not crash
            return FetchOutcome(
                tier,
                resp.status,
                "",
                "error",
                f"parse failed: {type(exc).__name__}",
                kind="binary",
                raw=raw,
            )
        verdict, note = classify(resp.status, markdown)
        return FetchOutcome(tier, resp.status, markdown, verdict, note, kind="html")

    if kind in ("feed", "text"):
        # Kept verbatim: markdownifying XML/JSON destroys the structure that is the
        # whole reason for fetching it. Still classified on the decoded text so a
        # block page served as text/plain does not sail through.
        text = raw.decode("utf-8", errors="replace")
        verdict, note = classify(resp.status, text)
        if verdict == "thin" and len(raw) >= MIN_BINARY_BYTES:
            verdict, note = "ok", ""
        return FetchOutcome(tier, resp.status, "", verdict, note, kind=kind, raw=raw)

    verdict, note = classify_binary(resp.status, len(raw), kind)
    return FetchOutcome(tier, resp.status, "", verdict, note, kind=kind, raw=raw)


def tier_http(url: str, timeout: int) -> FetchOutcome:
    from scrapling.fetchers import Fetcher

    try:
        resp = Fetcher.get(
            url,
            timeout=timeout,
            impersonate="chrome",
            stealthy_headers=True,
            follow_redirects=True,
        )
    except Exception as exc:  # noqa: BLE001
        return FetchOutcome("http", None, "", "error", f"{type(exc).__name__}: {exc}")
    return build_outcome("http", resp)


def tier_browser(url: str, timeout: int) -> FetchOutcome:
    from scrapling.fetchers import DynamicFetcher

    try:
        resp = DynamicFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=timeout * 1000,
            disable_resources=False,
        )
    except Exception as exc:  # noqa: BLE001
        return FetchOutcome(
            "browser", None, "", "error", f"{type(exc).__name__}: {exc}"
        )
    return build_outcome("browser", resp)


TIERS = {"http": tier_http, "browser": tier_browser}


def run_ladder(
    url: str, timeout: int, only: str | None
) -> tuple[FetchOutcome, list[dict]]:
    """Walk the tiers until one returns real content. Return (best, trail)."""
    order = [only] if only else ["http", "browser"]
    trail: list[dict] = []
    best: FetchOutcome | None = None

    for name in order:
        outcome = TIERS[name](url, timeout)
        trail.append(
            {
                "tier": name,
                "status": outcome.status,
                "verdict": outcome.verdict,
                "chars": outcome.size,
                "kind": outcome.kind,
                "note": outcome.note,
            }
        )
        if outcome.ok:
            return outcome, trail
        # Keep the most informative failure: real content beats an empty error.
        if best is None or outcome.size > best.size:
            best = outcome
        # An auth wall is a property of the site, not of our client. Escalating to
        # a heavier browser cannot change it and only wastes ~15s.
        if outcome.verdict == "auth-wall":
            break

    return best, trail  # type: ignore[return-value]


ACCESS_BY_VERDICT = {
    "ok": "OPEN",
    "thin": "PARTIAL",
    "auth-wall": "closed",
    "antibot": "closed",
    "error": "closed",
}


def build_meta(
    url: str, outcome: FetchOutcome, robots: dict, trail: list[dict], overridden: bool
) -> dict:
    return {
        "url": url,
        "access": ACCESS_BY_VERDICT[outcome.verdict],
        "fetch_tier": outcome.tier if outcome.ok else "-",
        "http_status": outcome.status,
        "verdict": outcome.verdict,
        "note": outcome.note,
        "chars": outcome.size,
        "content_kind": outcome.kind,
        "fetched": date.today().isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "robots_allowed": robots["allowed"],
        "robots_ai_disallowed": robots["ai_disallowed"],
        "robots_overridden": overridden,
        "trail": trail,
    }


def frontmatter_lines(meta: dict) -> str:
    """The subset a sub-agent pastes straight into sources/NN_slug.md."""
    lines = [
        f"access: {meta['access']}",
        f"fetched: {meta['fetched']}",
        f"fetch_tier: {meta['fetch_tier']}",
    ]
    if meta.get("content_kind") not in (None, "html"):
        lines.append(f"content_kind: {meta['content_kind']}")
    if meta["robots_overridden"]:
        lines.append("fetch_note: robots-disallowed, operator-overridden")
    elif meta["robots_ai_disallowed"]:
        blocked = ",".join(meta["robots_ai_disallowed"])
        lines.append(
            f"fetch_note: site excludes AI crawlers ({blocked}); generic access permitted"
        )
    return "\n".join(lines)


ROUTES_FILE = (
    Path(__file__).resolve().parents[1] / "references" / "fallback_routes.yaml"
)

FEED_MARKERS = ("<rss", "<feed", "<?xml", "<rdf:rdf")


def load_routes(path: Path | None = None) -> dict:
    """Load the curated domain -> route map. A missing file is not fatal."""
    import yaml

    path = path or ROUTES_FILE
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    return data if isinstance(data, dict) else {}


def registrable_domain(url: str) -> str:
    """example.co.uk from https://feeds.example.co.uk/x — public-suffix aware."""
    host = (urlparse(url).hostname or "").lower()
    try:
        from tld import get_fld

        return get_fld(url, fail_silently=True) or host.removeprefix("www.")
    except ImportError:
        return host.removeprefix("www.")


def resolve_routes(url: str, routes: dict) -> tuple[str, dict]:
    """Match the URL's domain against the curated map. Returns (key, entry)."""
    domains = routes.get("domains") or {}
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    fld = registrable_domain(url)
    for candidate in (host, fld):
        if candidate in domains:
            return candidate, domains[candidate]
    # Longest suffix wins: feeds.bbci.co.uk should not shadow a bbc.co.uk entry.
    for key in sorted(domains, key=len, reverse=True):
        if host == key or host.endswith("." + key):
            return key, domains[key]
    return "", {}


def probe_wellknown_feeds(
    url: str, routes: dict, timeout: int, crawl_delay: float | None = None
) -> list[str]:
    """Try the generic feed paths for a domain with no curated entry.

    Feeds are usually generated by a separate pipeline and escape the anti-bot
    layer that guards the HTML, so this is cheap and lands more often than it
    has any right to.

    This is the only place the tool sends several requests to one host in a row,
    so it is the only place a robots.txt Crawl-delay means anything. Honour it —
    capped, because some sites publish delays measured in minutes and we are
    making at most seven requests.
    """
    import time

    from scrapling.fetchers import Fetcher

    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    pause = min(float(crawl_delay or 0), MAX_CRAWL_DELAY)
    found = []
    for i, suffix in enumerate(routes.get("wellknown_feeds") or []):
        if i and pause:
            time.sleep(pause)
        try:
            resp = Fetcher.get(
                base + suffix,
                timeout=timeout,
                impersonate="chrome",
                follow_redirects=True,
            )
        except Exception:  # noqa: BLE001 - probing, failures are expected
            continue
        if resp.status != 200 or not resp.body:
            continue
        head = decode_robots(resp.body)[:400].lstrip().lower()
        if any(marker in head for marker in FEED_MARKERS):
            # First hit is enough: /feed, /feed/ and /rss usually redirect to one
            # another, and three identical entries is noise, not three options.
            found.append(f"{base + suffix}  ({len(resp.body)} B)")
            break
    return found


def format_fallback_report(url: str, routes: dict, probed: list[str] | None) -> str:
    """What to try instead, once the HTML door is confirmed shut."""
    key, entry = resolve_routes(url, routes)
    out: list[str] = []

    if entry:
        out.append(f"Known routes for {key}:")
        if entry.get("note"):
            out.append(f"  note: {' '.join(str(entry['note']).split())}")
        for route in entry.get("routes") or []:
            auth = route.get("auth", "?")
            line = f"  [{route.get('type', '?')}] {route.get('url', '')}"
            out.append(line)
            detail = f"        auth: {auth}"
            if route.get("catalog"):
                detail += f"  ·  api_sources/{route['catalog']}"
            if route.get("verified"):
                detail += f"  ·  verified: {route['verified']}"
            out.append(detail)
    else:
        out.append(f"No curated route for {registrable_domain(url) or url}.")

    if probed:
        out.append("Live feed probe found:")
        out.extend(f"  [feed] {f}" for f in probed)
    elif probed is not None and not entry:
        out.append("Live feed probe found nothing at the well-known paths.")

    archive = (routes.get("archive") or {}).get("availability")
    if archive:
        out.append(f"Archive snapshot: {archive.format(url=url)}")
        out.append(
            "  (a snapshot answers 'what was there', not 'what is there' — record as_of)"
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="fetch_source.py",
        description="Phase 4 fallback fetcher. Use only after WebFetch has failed.",
    )
    ap.add_argument("url")
    ap.add_argument(
        "-o", "--out", type=Path, help="write markdown here (default: stdout)"
    )
    ap.add_argument("--meta", type=Path, help="write the full JSON metadata here")
    ap.add_argument("--timeout", type=int, default=30, help="per-tier timeout, seconds")
    ap.add_argument(
        "--tier", choices=sorted(TIERS), help="force one tier instead of the ladder"
    )
    ap.add_argument(
        "--ua-token", default=DEFAULT_UA_TOKEN, help="robots.txt identity to honour"
    )
    ap.add_argument(
        "--ignore-robots",
        action="store_true",
        help="fetch even when robots.txt disallows this path (recorded in the metadata)",
    )
    ap.add_argument(
        "--no-probe",
        action="store_true",
        help="on a block, do not live-probe the well-known feed paths",
    )
    args = ap.parse_args(argv)

    robots = check_robots(args.url, args.ua_token, args.timeout)
    overridden = False
    if not robots["allowed"]:
        if not args.ignore_robots:
            print(
                f"robots.txt disallows this path for a generic client: {robots['robots_url']}\n"
                "This is a site-wide exclusion, not an AI-specific one.\n"
                "Pass --ignore-robots to override; the override is stamped into the source file.",
                file=sys.stderr,
            )
            return 3
        overridden = True

    outcome, trail = run_ladder(args.url, args.timeout, args.tier)
    meta = build_meta(args.url, outcome, robots, trail, overridden)

    if args.meta:
        args.meta.parent.mkdir(parents=True, exist_ok=True)
        args.meta.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if outcome.ok:
        if args.out:
            out = args.out
            if outcome.kind != "html":
                out = out.with_suffix(SUFFIX_BY_KIND.get(outcome.kind, out.suffix))
            out.parent.mkdir(parents=True, exist_ok=True)
            if outcome.kind == "html":
                out.write_text(outcome.markdown, encoding="utf-8")
            else:
                out.write_bytes(outcome.raw or b"")
            meta["out"] = str(out)
            print(
                f"ok  tier={outcome.tier}  kind={outcome.kind}  status={outcome.status}  "
                f"size={outcome.size}  -> {out}",
                file=sys.stderr,
            )
            if outcome.kind == "pdf":
                print(
                    "  PDF saved as-is — read it with the Read tool (it takes a `pages` "
                    "range); do not try to markdown it.",
                    file=sys.stderr,
                )
            elif outcome.kind == "feed":
                print(
                    "  Feed saved verbatim. It gives title/date/summary/URL per item — "
                    "not full article text. Quote a summary as a summary.",
                    file=sys.stderr,
                )
            if args.meta:
                args.meta.write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        elif outcome.kind == "html":
            sys.stdout.write(outcome.markdown)
        else:
            sys.stdout.buffer.write(outcome.raw or b"")
        print(frontmatter_lines(meta), file=sys.stderr)
        return 0

    print(
        f"blocked  verdict={outcome.verdict}  tier={outcome.tier}  status={outcome.status}  {outcome.note}",
        file=sys.stderr,
    )
    if outcome.verdict in ("auth-wall", "antibot"):
        print(
            "The HTML door is shut and stays shut — this tool does not force it.\n"
            "The same content is usually served through a door the site keeps open:",
            file=sys.stderr,
        )
        routes = load_routes()
        key, _ = resolve_routes(args.url, routes)
        probed = (
            None
            if args.no_probe
            else probe_wellknown_feeds(
                args.url, routes, 10, robots.get("crawl_delay")
            )
        )
        if not key or probed:
            meta["fallback_probed_feeds"] = probed or []
        report = format_fallback_report(args.url, routes, probed)
        print(report, file=sys.stderr)
        print(
            "Nothing here either? channels.md fallback chain, then access: closed.",
            file=sys.stderr,
        )
        meta["fallback_domain"] = key
        if args.meta:
            args.meta.write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return 4
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
