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


def test_keenable_works_without_key(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured["method"] = method
        captured.update(kwargs)
        return FakeResponse(
            {
                "results": [
                    {"title": "T", "url": "https://x", "description": "D", "snippet": "S"},
                    {"title": "no url", "description": "dropped"},
                    {"title": "U", "url": "https://y", "snippet": "z" * 2000},
                ]
            }
        )

    monkeypatch.setattr(sq.requests, "request", fake_request)
    hits = sq.run_query("keenable", "hello", 5, {})

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.keenable.ai/v1/search/public"
    assert captured["headers"]["X-Keenable-Title"] == "deepdive"
    assert "X-API-Key" not in captured["headers"]
    assert captured["json"] == {"query": "hello", "max_results": 5}
    assert [h["url"] for h in hits] == ["https://x", "https://y"]
    assert hits[0]["snippet"] == "D"
    assert len(hits[1]["snippet"]) == sq.KEENABLE_SNIPPET_MAX_CHARS
    assert hits[0]["engine"] == "keenable"


def test_keenable_uses_keyed_endpoint_with_key(monkeypatch):
    captured = {}

    def fake_request(method, timeout=None, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"results": []})

    monkeypatch.setattr(sq.requests, "request", fake_request)
    sq.run_query("keenable", "hello", 5, {"KEENABLE_API_KEY": "kn"})

    assert captured["url"] == "https://api.keenable.ai/v1/search"
    assert captured["headers"]["X-API-Key"] == "kn"
