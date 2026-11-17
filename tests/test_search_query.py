import pytest

from scripts import search_query as sq


class FakeResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


def test_missing_key_exits_2():
    with pytest.raises(SystemExit) as exc:
        sq.run_query("brave", "q", 5, {})
    assert exc.value.code == 2


def test_brave_request_shape(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured["method"] = method
        captured.update(kwargs)
        return FakeResponse(
            {
                "web": {
                    "results": [{"title": "T", "url": "https://x", "description": "S"}]
                }
            }
        )

    monkeypatch.setattr(sq.requests, "request", fake_request)
    hits = sq.run_query("brave", "hello", 5, {"BRAVE_SEARCH_API_KEY": "key123"})

    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.search.brave.com/res/v1/web/search"
    assert captured["headers"]["X-Subscription-Token"] == "key123"
    assert captured["params"]["q"] == "hello"
    assert hits[0]["title"] == "T"
    assert hits[0]["url"] == "https://x"
    assert hits[0]["engine"] == "brave"
    assert hits[0]["rank"] == 1
    assert "fetched_at" in hits[0]


def test_tavily_request_shape(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured["method"] = method
        captured.update(kwargs)
        return FakeResponse(
            {"results": [{"title": "T2", "url": "https://y", "content": "C"}]}
        )

    monkeypatch.setattr(sq.requests, "request", fake_request)
    hits = sq.run_query("tavily", "world", 3, {"TAVILY_API_KEY": "tvly-abc"})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["json"]["api_key"] == "tvly-abc"
    assert captured["json"]["query"] == "world"
    assert captured["json"]["max_results"] == 3
    assert hits[0]["title"] == "T2"
    assert hits[0]["snippet"] == "C"


def test_exa_request_shape(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured["method"] = method
        captured.update(kwargs)
        return FakeResponse(
            {"results": [{"title": "T3", "url": "https://z", "text": "X"}]}
        )

    monkeypatch.setattr(sq.requests, "request", fake_request)
    hits = sq.run_query("exa", "concept", 7, {"EXA_API_KEY": "exa-key"})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.exa.ai/search"
    assert captured["headers"]["x-api-key"] == "exa-key"
    assert captured["json"]["query"] == "concept"
    assert captured["json"]["numResults"] == 7
    assert hits[0]["title"] == "T3"


def test_firecrawl_request_shape(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured["method"] = method
        captured.update(kwargs)
        return FakeResponse(
            {
                "success": True,
                "data": {
                    "web": [
                        {"title": "T4", "url": "https://w", "description": "D"},
                        {"title": "T5", "url": "https://v", "description": "x" * 5000},
                    ]
                },
            }
        )

    monkeypatch.setattr(sq.requests, "request", fake_request)
    hits = sq.run_query("firecrawl", "research", 4, {"FIRECRAWL_API_KEY": "fc-key"})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.firecrawl.dev/v2/search"
    assert captured["headers"]["Authorization"] == "Bearer fc-key"
    assert captured["json"]["query"] == "research"
    assert captured["json"]["limit"] == 4
    assert captured["json"]["origin"] == "deepdive"
    assert hits[0]["title"] == "T4"
    assert hits[0]["url"] == "https://w"
    assert hits[0]["snippet"] == "D"
    assert hits[0]["engine"] == "firecrawl"
    assert len(hits[1]["snippet"]) == sq.FIRECRAWL_SNIPPET_MAX_CHARS


def test_http_error_exits_1(monkeypatch):
    def fake_request(method, timeout=None, **kwargs):
        return FakeResponse({}, status=500)

    monkeypatch.setattr(sq.requests, "request", fake_request)
    with pytest.raises(SystemExit) as exc:
        sq.run_query("brave", "q", 5, {"BRAVE_SEARCH_API_KEY": "k"})
    assert exc.value.code == 1


def test_transport_error_retries_once_then_raises(monkeypatch):
    import requests

    calls = {"n": 0}

    def fake_request(method, timeout=None, **kwargs):
        calls["n"] += 1
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(sq.requests, "request", fake_request)
    with pytest.raises(SystemExit) as exc:
        sq.run_query("brave", "q", 5, {"BRAVE_SEARCH_API_KEY": "k"})
    assert exc.value.code == 1
    assert calls["n"] == 2


def test_normalize_empty_results():
    assert sq.normalize("tavily", {"results": []}) == []


def test_main_missing_key_prints_env_var_name(capsys, monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    rc = sq.main(["--engine", "exa", "--query", "q"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "EXA_API_KEY" in captured.err


def test_engine_routes_cover_every_qclass_with_every_engine():
    from runner.qclass import QCLASSES

    assert set(sq.ENGINE_ROUTES) == set(QCLASSES)
    for qclass, route in sq.ENGINE_ROUTES.items():
        assert sorted(route) == sorted(sq.ENV_VARS), qclass


def test_resolve_engine_follows_qclass_route():
    env = {k: "x" for k in sq.ENV_VARS.values()}
    assert sq.resolve_engine("scientific-claim", env)[0] == "exa"
    assert sq.resolve_engine("recent-change", env)[0] == "tavily"


def test_resolve_engine_skips_engines_without_key():
    env = {"BRAVE_SEARCH_API_KEY": "b", "FIRECRAWL_API_KEY": "f"}
    assert sq.resolve_engine("scientific-claim", env)[0] == "brave"
    assert sq.resolve_engine("pricing", {"FIRECRAWL_API_KEY": "f"})[0] == "firecrawl"


def test_resolve_engine_unknown_qclass_uses_default_route():
    env = {"EXA_API_KEY": "e", "TAVILY_API_KEY": "t"}
    assert sq.resolve_engine("nonsense", env)[0] == sq.ENGINE_ROUTES["qualitative"][0]
    assert sq.resolve_engine(None, env)[0] == sq.ENGINE_ROUTES["qualitative"][0]


def test_resolve_engine_no_keys_exits_2_naming_all_vars(capsys):
    with pytest.raises(SystemExit) as exc:
        sq.resolve_engine("pricing", {})
    assert exc.value.code == 2
    err = capsys.readouterr().err
    for var in sq.ENV_VARS.values():
        assert var in err


def test_main_auto_queries_routed_engine(capsys, monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"results": [{"title": "T", "url": "https://u", "text": "s"}]})

    monkeypatch.setattr(sq.requests, "request", fake_request)
    monkeypatch.setenv("EXA_API_KEY", "e")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "b")
    for var in ("TAVILY_API_KEY", "FIRECRAWL_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setattr(sq, "load_priors", lambda: {})
    rc = sq.main(["--engine", "auto", "--qclass", "how-it-works", "--query", "q"])

    assert rc == 0
    assert captured["url"].startswith("https://api.exa.ai")
    err = capsys.readouterr().err
    assert "engine: exa (qclass how-it-works, by route)" in err
    assert "search-engine-2/exa" in err


def _prior(alpha, beta, n=10):
    from runner.state import Prior

    return Prior(alpha=alpha, beta=beta, n=n, last_seen="")


def test_resolve_engine_uses_priors_once_a_cell_exists():
    import random

    env = {"EXA_API_KEY": "e", "BRAVE_SEARCH_API_KEY": "b"}
    priors = {"search-engine-2/brave|scientific-claim": _prior(50.0, 1.0)}
    picks = [
        sq.resolve_engine("scientific-claim", env, priors, random.Random(seed))
        for seed in range(50)
    ]
    assert all(how == "priors" for _, how in picks)
    # brave's cell is strong, exa has none and draws from Beta(1, 1):
    # brave wins most draws, exa still gets explored sometimes.
    engines = [e for e, _ in picks]
    assert engines.count("brave") > 40 and "exa" in engines


def test_resolve_engine_ignores_priors_of_other_qclass_and_single_key():
    env = {"EXA_API_KEY": "e", "BRAVE_SEARCH_API_KEY": "b"}
    other = {"search-engine-2/brave|pricing": _prior(50.0, 1.0)}
    assert sq.resolve_engine("scientific-claim", env, other) == ("exa", "route")
    only_exa = {"EXA_API_KEY": "e"}
    strong = {"search-engine-2/brave|scientific-claim": _prior(50.0, 1.0)}
    assert sq.resolve_engine("scientific-claim", only_exa, strong) == ("exa", "route")


def test_hits_carry_the_priors_channel():
    hits = sq.normalize("exa", {"results": [{"title": "T", "url": "https://u", "text": "s"}]})
    assert hits[0]["channel"] == "search-engine-2/exa"


def test_engine_channel_is_scored_by_collect_observations(tmp_path):
    from scripts import collect_observations as co

    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "01_x.md").write_text(
        "---\nid: s1\ndiscovery_path: search-engine-2/exa|query|en\n---\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "claims.csv").write_text("claim_id,sources,dissent\nCL1,s1,-\n", encoding="utf-8")
    obs = co.collect(tmp_path, "run1", {"search-engine-2/exa": "scientific-claim"})
    assert [(o.channel, o.qclass, o.reward) for o in obs] == [
        ("search-engine-2/exa", "scientific-claim", 1)
    ]
