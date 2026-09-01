"""Tests for scripts/fetch_source.py — Phase 4 escalating fetcher.

The load-bearing tests here are the robots.txt ones. That check fails open: when
parsing breaks, every verdict silently becomes "allowed", which reads identically
to a site that never restricted anything. So the fixture is a *positive control* —
a robots.txt known to disallow AI crawlers — and the test asserts the detector
sees the restriction, not merely that it returns without raising.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import fetch_source as fs  # noqa: E402

# Shaped after the real nytimes.com/robots.txt: a permissive `*` section plus
# targeted AI-crawler exclusions. This is the case the tool exists to report on.
ROBOTS_AI_BLOCKED = b"""# Content is made available for personal, non-commercial use.
User-agent: *
Allow: /
Disallow: /search

User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: CCBot
Disallow: /
"""

ROBOTS_BLOCKS_EVERYONE = b"""User-agent: *
Disallow: /
"""

ROBOTS_OPEN = b"""User-agent: *
Allow: /
"""

URL = "https://example.com/section/technology"


def robots_source(body, status=200):
    """Injectable fetch stub returning a robots.txt body as scrapling would: bytes."""

    def _fetch(robots_url, timeout):
        return status, body

    return _fetch


# --- decode ---------------------------------------------------------------


def test_decode_robots_accepts_bytes():
    """str(bytes) yields "b'...'" — a junk single line that parses to zero rules."""
    decoded = fs.decode_robots(ROBOTS_OPEN)
    assert decoded.startswith("User-agent: *")
    assert not decoded.startswith("b'")


def test_decode_robots_passes_through_str():
    assert fs.decode_robots("User-agent: *\n").startswith("User-agent")


def test_decode_robots_survives_bad_encoding():
    assert "User-agent" in fs.decode_robots(b"User-agent: *\n# caf\xe9\n")


# --- robots verdicts ------------------------------------------------------


def test_ai_exclusion_is_reported():
    """Positive control: this robots.txt definitely blocks GPTBot/ClaudeBot/CCBot."""
    v = fs.check_robots(
        URL, "deepdive-research", 10, fetch=robots_source(ROBOTS_AI_BLOCKED)
    )
    assert v["fetched"] is True
    assert v["error"] == ""
    assert set(v["ai_disallowed"]) >= {"GPTBot", "ClaudeBot", "CCBot"}


def test_generic_client_still_allowed_when_only_ai_is_excluded():
    """The two verdicts are independent: `*` permits us, AI tokens are excluded."""
    v = fs.check_robots(
        URL, "deepdive-research", 10, fetch=robots_source(ROBOTS_AI_BLOCKED)
    )
    assert v["allowed"] is True
    assert v["ai_disallowed"]


def test_site_wide_exclusion_blocks_us():
    v = fs.check_robots(
        URL, "deepdive-research", 10, fetch=robots_source(ROBOTS_BLOCKS_EVERYONE)
    )
    assert v["allowed"] is False


def test_open_robots_reports_nothing_blocked():
    """Negative control — proves the detector is not simply always reporting a block."""
    v = fs.check_robots(URL, "deepdive-research", 10, fetch=robots_source(ROBOTS_OPEN))
    assert v["allowed"] is True
    assert v["ai_disallowed"] == []


def test_missing_robots_is_not_a_restriction():
    v = fs.check_robots(
        URL, "deepdive-research", 10, fetch=robots_source(b"", status=404)
    )
    assert v["allowed"] is True
    assert v["fetched"] is False
    assert "404" in v["error"]


def test_robots_fetch_failure_does_not_raise():
    def boom(robots_url, timeout):
        raise TimeoutError("nope")

    v = fs.check_robots(URL, "deepdive-research", 10, fetch=boom)
    assert v["allowed"] is True
    assert "TimeoutError" in v["error"]


# --- classification -------------------------------------------------------

GOOD = "x" * (fs.MIN_CONTENT_CHARS + 1)


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (200, GOOD, "ok"),
        (200, "short", "thin"),
        (401, GOOD, "auth-wall"),
        (402, GOOD, "auth-wall"),
        (403, GOOD, "antibot"),
        (429, GOOD, "error"),
        (500, GOOD, "error"),
        (404, GOOD, "error"),
        (None, "", "error"),
    ],
)
def test_classify_status_table(status, body, expected):
    assert fs.classify(status, body)[0] == expected


def test_block_page_beats_a_200():
    """The failure that motivates this function: a wall served with status 200."""
    verdict, note = fs.classify(200, "Just a moment..." + GOOD)
    assert verdict == "antibot"
    assert "just a moment" in note.lower()


def test_paywall_marker_classified_as_auth_wall():
    verdict, _ = fs.classify(200, "Sign in to read the full story. " + GOOD)
    assert verdict == "auth-wall"


def test_reuters_shaped_stub_is_not_content():
    """Real capture: reuters.com serves this 43-byte body under a 401."""
    verdict, _ = fs.classify(401, "Please enable JS and disable any ad blocker")
    assert verdict == "antibot"


# --- ladder ---------------------------------------------------------------


def make_tier(name, outcome):
    return lambda url, timeout: outcome


def test_ladder_stops_at_first_success(monkeypatch):
    calls = []

    def http(url, timeout):
        calls.append("http")
        return fs.FetchOutcome("http", 200, GOOD, "ok")

    def browser(url, timeout):
        calls.append("browser")
        return fs.FetchOutcome("browser", 200, GOOD, "ok")

    monkeypatch.setitem(fs.TIERS, "http", http)
    monkeypatch.setitem(fs.TIERS, "browser", browser)
    best, trail = fs.run_ladder(URL, 10, None)
    assert best.tier == "http"
    assert calls == ["http"]
    assert len(trail) == 1


def test_ladder_escalates_past_antibot(monkeypatch):
    monkeypatch.setitem(
        fs.TIERS, "http", make_tier("http", fs.FetchOutcome("http", 403, "", "antibot"))
    )
    monkeypatch.setitem(
        fs.TIERS,
        "browser",
        make_tier("browser", fs.FetchOutcome("browser", 200, GOOD, "ok")),
    )
    best, trail = fs.run_ladder(URL, 10, None)
    assert best.ok and best.tier == "browser"
    assert [t["tier"] for t in trail] == ["http", "browser"]


def test_ladder_does_not_escalate_past_an_auth_wall(monkeypatch):
    """A login wall is a property of the site; a heavier browser cannot change it."""
    seen = []

    def http(url, timeout):
        seen.append("http")
        return fs.FetchOutcome("http", 401, "", "auth-wall")

    def browser(url, timeout):
        seen.append("browser")
        return fs.FetchOutcome("browser", 200, GOOD, "ok")

    monkeypatch.setitem(fs.TIERS, "http", http)
    monkeypatch.setitem(fs.TIERS, "browser", browser)
    best, _ = fs.run_ladder(URL, 10, None)
    assert seen == ["http"]
    assert best.verdict == "auth-wall"


def test_forced_tier_skips_the_ladder(monkeypatch):
    monkeypatch.setitem(
        fs.TIERS,
        "browser",
        make_tier("browser", fs.FetchOutcome("browser", 200, GOOD, "ok")),
    )
    _, trail = fs.run_ladder(URL, 10, "browser")
    assert [t["tier"] for t in trail] == ["browser"]


# --- metadata handed to the source file -----------------------------------


def test_blocked_fetch_never_reports_open_access():
    for verdict in ("auth-wall", "antibot", "error"):
        outcome = fs.FetchOutcome("http", 403, "", verdict)
        meta = fs.build_meta(
            URL,
            outcome,
            fs.check_robots(URL, "u", 1, robots_source(ROBOTS_OPEN)),
            [],
            False,
        )
        assert meta["access"] == "closed"
        assert meta["fetch_tier"] == "-"


def test_frontmatter_records_ai_exclusion():
    outcome = fs.FetchOutcome("http", 200, GOOD, "ok")
    robots = fs.check_robots(URL, "u", 1, robots_source(ROBOTS_AI_BLOCKED))
    lines = fs.frontmatter_lines(fs.build_meta(URL, outcome, robots, [], False))
    assert "access: OPEN" in lines
    assert "fetch_tier: http" in lines
    assert "GPTBot" in lines


def test_frontmatter_records_a_robots_override():
    outcome = fs.FetchOutcome("http", 200, GOOD, "ok")
    robots = fs.check_robots(URL, "u", 1, robots_source(ROBOTS_BLOCKS_EVERYONE))
    lines = fs.frontmatter_lines(fs.build_meta(URL, outcome, robots, [], True))
    assert "operator-overridden" in lines


def test_clean_fetch_adds_no_fetch_note():
    outcome = fs.FetchOutcome("http", 200, GOOD, "ok")
    robots = fs.check_robots(URL, "u", 1, robots_source(ROBOTS_OPEN))
    lines = fs.frontmatter_lines(fs.build_meta(URL, outcome, robots, [], False))
    assert "fetch_note" not in lines


# --- refusals are structural, not configurable ----------------------------


def test_no_cloudflare_or_captcha_solving_is_wired_up():
    """StealthyFetcher/solve_cloudflare is out of scope; keep it out of the source."""
    src = (REPO / "scripts" / "fetch_source.py").read_text(encoding="utf-8")
    code = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith(("#", "*"))
    )
    assert "solve_cloudflare" not in code
    assert "StealthyFetcher" not in code


def test_only_the_two_declared_tiers_exist():
    assert sorted(fs.TIERS) == ["browser", "http"]


# --- fallback route resolution ------------------------------------------


ROUTES = fs.load_routes()


def test_routes_file_loads_and_is_populated():
    """A silently-empty map would make every block report 'no route known'."""
    assert ROUTES.get("version") == 1
    assert len(ROUTES.get("domains") or {}) >= 15
    assert ROUTES.get("wellknown_feeds")


def test_every_route_has_type_url_and_auth():
    for domain, entry in ROUTES["domains"].items():
        assert entry.get("routes"), f"{domain} has no routes"
        for route in entry["routes"]:
            assert route.get("type") in ("api", "feed"), f"{domain}: bad type"
            assert route.get("url", "").startswith("http"), f"{domain}: bad url"
            assert route.get("auth"), f"{domain}: auth not stated"


def test_kind_is_declared_and_valid():
    for domain, entry in ROUTES["domains"].items():
        assert entry.get("kind") in ("self", "proxy"), f"{domain}: bad kind"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://stackoverflow.com/questions/tagged/python", "stackoverflow.com"),
        ("https://www.stackoverflow.com/q/1", "stackoverflow.com"),
        ("https://www.nytimes.com/section/technology", "nytimes.com"),
        ("https://www.reuters.com/technology/", "reuters.com"),
        ("https://old.reddit.com/r/MachineLearning/", "reddit.com"),
        ("https://news.ycombinator.com/item?id=1", "news.ycombinator.com"),
    ],
)
def test_resolve_matches_domain_and_subdomains(url, expected):
    key, entry = fs.resolve_routes(url, ROUTES)
    assert key == expected
    assert entry


def test_unlisted_domain_resolves_to_nothing():
    key, entry = fs.resolve_routes("https://example.invalid/page", ROUTES)
    assert key == ""
    assert entry == {}


def test_stackoverflow_route_is_keyless():
    """The measured case: HTML 403, API 200 without a key."""
    _, entry = fs.resolve_routes("https://stackoverflow.com/questions", ROUTES)
    api = [r for r in entry["routes"] if r["type"] == "api"]
    assert api and api[0]["auth"] == "none"
    assert "api.stackexchange.com" in api[0]["url"]


def test_reddit_has_no_feed_route():
    """Measured 403 across three UA strategies — must not be advertised as working."""
    _, entry = fs.resolve_routes("https://www.reddit.com/r/x/", ROUTES)
    assert all(r["type"] != "feed" for r in entry["routes"])


def test_report_names_routes_for_a_known_domain():
    out = fs.format_fallback_report(
        "https://stackoverflow.com/questions/tagged/python", ROUTES, None
    )
    assert "stackoverflow.com" in out
    assert "api.stackexchange.com" in out
    assert "archive.org/wayback" in out


def test_report_is_honest_about_an_unknown_domain():
    out = fs.format_fallback_report("https://example.invalid/x", ROUTES, [])
    assert "No curated route" in out
    assert "probe found nothing" in out


def test_report_includes_live_probe_hits():
    out = fs.format_fallback_report(
        "https://example.invalid/x", ROUTES, ["https://example.invalid/feed  (900 B)"]
    )
    assert "/feed" in out


def test_missing_routes_file_is_not_fatal():
    assert fs.load_routes(Path("/nonexistent/routes.yaml")) == {}


def test_catalog_refs_point_at_real_files():
    """A dangling api_sources/ reference sends a sub-agent to a file that isn't there."""
    for domain, entry in ROUTES["domains"].items():
        for route in entry["routes"]:
            ref = route.get("catalog")
            if ref:
                p = REPO / "references" / "api_sources" / ref
                assert p.exists(), f"{domain}: missing {p}"


# --- payload kinds --------------------------------------------------------


class FakeResp:
    def __init__(self, body, status=200, ctype=None):
        self.body = body
        self.status = status
        self.headers = {"content-type": ctype} if ctype else {}


PDF_BODY = b"%PDF-1.7\n" + b"\x00binary\xff" * 300


@pytest.mark.parametrize(
    "resp,expected",
    [
        (FakeResp(PDF_BODY), "pdf"),
        (FakeResp(b"noise", ctype="application/pdf"), "pdf"),
        (FakeResp(b'<?xml version="1.0"?><rss><channel/></rss>'), "feed"),
        (FakeResp(b'<?xml version="1.0"?><feed xmlns="..."/>'), "feed"),
        (FakeResp(b"{}", ctype="application/rss+xml"), "feed"),
        (FakeResp(b"<!DOCTYPE html><html></html>"), "html"),
        (FakeResp(b"<html><body>x</body></html>"), "html"),
        (FakeResp(b"anything", ctype="text/html; charset=utf-8"), "html"),
        (FakeResp(b'{"a":1}', ctype="application/json"), "text"),
        (FakeResp(b"\x89PNG\r\n", ctype="image/png"), "binary"),
    ],
)
def test_sniff_kind(resp, expected):
    assert fs.sniff_kind(resp) == expected


def test_pdf_does_not_reach_the_html_parser():
    """The crash this guards: lxml rejects NULL bytes and killed the whole run."""
    outcome = fs.build_outcome("http", FakeResp(PDF_BODY, ctype="application/pdf"))
    assert outcome.kind == "pdf"
    assert outcome.ok
    assert outcome.raw == PDF_BODY
    assert outcome.markdown == ""


def test_pdf_keeps_bytes_intact():
    outcome = fs.build_outcome("http", FakeResp(PDF_BODY))
    assert outcome.raw.startswith(b"%PDF-")
    assert len(outcome.raw) == len(PDF_BODY)


def test_tiny_pdf_is_thin_not_ok():
    outcome = fs.build_outcome("http", FakeResp(b"%PDF-1.7\nstub"))
    assert outcome.verdict == "thin"


def test_blocked_pdf_url_is_still_blocked():
    outcome = fs.build_outcome("http", FakeResp(PDF_BODY, status=403))
    assert outcome.verdict == "antibot"


def test_feed_is_kept_verbatim_not_markdownified():
    body = b'<?xml version="1.0"?><rss><channel><title>x</title></channel></rss>' + b" " * 2000
    outcome = fs.build_outcome("http", FakeResp(body))
    assert outcome.kind == "feed"
    assert outcome.ok
    assert outcome.raw == body
    assert outcome.markdown == ""


def test_block_page_served_as_text_is_still_caught():
    """A wall does not stop being a wall because the content-type says text."""
    body = b"Just a moment..." + b"x" * 3000
    outcome = fs.build_outcome("http", FakeResp(body, ctype="text/plain"))
    assert outcome.verdict == "antibot"


def test_size_is_comparable_across_kinds():
    html = fs.FetchOutcome("http", 200, "abc", "ok", kind="html")
    pdf = fs.FetchOutcome("http", 200, "", "ok", kind="pdf", raw=b"12345")
    assert html.size == 3 and pdf.size == 5


def test_suffix_map_covers_every_non_html_kind():
    for kind in ("pdf", "feed", "text", "binary"):
        assert kind in fs.SUFFIX_BY_KIND


def test_frontmatter_declares_non_html_kind():
    outcome = fs.FetchOutcome("http", 200, "", "ok", kind="pdf", raw=b"x" * 2000)
    robots = fs.check_robots(URL, "u", 1, robots_source(ROBOTS_OPEN))
    lines = fs.frontmatter_lines(fs.build_meta(URL, outcome, robots, [], False))
    assert "content_kind: pdf" in lines


def test_frontmatter_stays_quiet_for_html():
    outcome = fs.FetchOutcome("http", 200, GOOD, "ok", kind="html")
    robots = fs.check_robots(URL, "u", 1, robots_source(ROBOTS_OPEN))
    lines = fs.frontmatter_lines(fs.build_meta(URL, outcome, robots, [], False))
    assert "content_kind" not in lines


def test_crawl_delay_is_capped():
    """Some sites publish delays in minutes; seven probes must not stall a round."""
    assert fs.MAX_CRAWL_DELAY <= 5


def test_wikipedia_route_exists():
    _, entry = fs.resolve_routes("https://en.wikipedia.org/wiki/LLM", ROUTES)
    assert entry and entry["routes"][0]["auth"] == "none"
