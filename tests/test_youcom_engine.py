"""Tests for the optional You.com search engine.

All HTTP traffic is mocked -- no network access is required to run these.

Run with:
    pip install -e ".[dev]"
    pytest
"""

from unittest.mock import patch

import pytest

from agent_search.core.multi_search import (
    YOUCOM_KEYED_URL,
    YOUCOM_KEYLESS_URL,
    MultiEngineSearch,
    youcom_enabled,
    youcom_search,
)


SAMPLE_RESPONSE = {
    "results": {
        "web": [
            {
                "title": "Asyncio documentation",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "snippets": ["Coroutines and tasks", "Event loops"],
            },
            {
                "title": "No snippets here",
                "url": "https://example.com/no-snippets",
                "snippets": [],
            },
        ]
    }
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture
def clean_engine_env(monkeypatch):
    monkeypatch.delenv("YDC_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_SEARCH_YOUCOM", raising=False)


@pytest.fixture
def keyless_env(clean_engine_env, monkeypatch):
    monkeypatch.setenv("AGENT_SEARCH_YOUCOM", "1")


@pytest.fixture
def keyed_env(clean_engine_env, monkeypatch):
    monkeypatch.setenv("YDC_API_KEY", "test-key")


def test_engine_is_off_by_default(clean_engine_env):
    assert youcom_enabled() is False


def test_engine_on_with_api_key(keyed_env):
    assert youcom_enabled() is True


def test_engine_on_with_keyless_opt_in(keyless_env):
    assert youcom_enabled() is True


def test_keyless_opt_in_requires_explicit_truthy_value(clean_engine_env, monkeypatch):
    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("AGENT_SEARCH_YOUCOM", value)
        assert youcom_enabled() is False, value


def test_disabled_engine_makes_no_requests(clean_engine_env):
    searcher = MultiEngineSearch()
    with patch("requests.Session.get") as fake_get:
        assert searcher._search_youcom("anything") == []
    fake_get.assert_not_called()


def test_keyed_uses_keyed_endpoint(keyed_env):
    searcher = MultiEngineSearch()
    with patch(
        "requests.Session.get", return_value=FakeResponse(SAMPLE_RESPONSE)
    ) as fake_get:
        results = searcher._search_youcom("asyncio docs", max_results=5)

    args, kwargs = fake_get.call_args
    assert args[0] == YOUCOM_KEYED_URL
    assert kwargs["headers"]["X-API-Key"] == "test-key"
    assert kwargs["params"] == {"query": "asyncio docs", "count": 5, "safesearch": "strict"}
    assert len(results) == 2


def test_keyless_uses_keyless_endpoint_without_key_header(keyless_env):
    searcher = MultiEngineSearch()
    with patch(
        "requests.Session.get", return_value=FakeResponse(SAMPLE_RESPONSE)
    ) as fake_get:
        searcher._search_youcom("asyncio docs")

    args, kwargs = fake_get.call_args
    assert args[0] == YOUCOM_KEYLESS_URL
    assert "X-API-Key" not in kwargs["headers"]
    assert "User-Agent" in kwargs["headers"]


def test_parses_documented_response_shape(keyless_env):
    searcher = MultiEngineSearch()
    with patch("requests.Session.get", return_value=FakeResponse(SAMPLE_RESPONSE)):
        results = searcher._search_youcom("asyncio docs")

    assert len(results) == 2
    first, second = results
    assert first["title"] == "Asyncio documentation"
    assert first["url"] == "https://docs.python.org/3/library/asyncio.html"
    assert first["snippet"] == "Coroutines and tasks Event loops"
    assert first["source"] == "youcom"
    assert first["score"] == 0.85
    # empty snippets fall back to an empty string instead of raising
    assert second["snippet"] == ""


def test_aggregator_includes_youcom(keyless_env):
    searcher = MultiEngineSearch()
    with patch(
        "requests.Session.get", return_value=FakeResponse(SAMPLE_RESPONSE)
    ), patch.object(
        MultiEngineSearch, "_search_whoogle", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_duckduckgo", return_value=[]
    ):
        summary = searcher.search("asyncio docs")

    assert "youcom" in summary["engines_used"]
    assert summary["total_results"] == 2
    assert all(r["source"] == "youcom" for r in summary["results"])


def test_aggregator_skips_youcom_when_disabled(clean_engine_env):
    searcher = MultiEngineSearch()
    with patch.object(
        MultiEngineSearch, "_search_whoogle", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_duckduckgo", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_wikipedia", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_youcom"
    ) as fake_engine:
        summary = searcher.search("asyncio docs")

    fake_engine.assert_not_called()
    assert summary["total_results"] == 0


def test_youcom_error_does_not_break_the_aggregate(keyless_env):
    searcher = MultiEngineSearch()
    with patch.object(
        MultiEngineSearch, "_search_whoogle", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_duckduckgo", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_wikipedia", return_value=[]
    ), patch.object(
        MultiEngineSearch, "_search_youcom", side_effect=RuntimeError("boom")
    ):
        summary = searcher.search("asyncio docs")

    assert "youcom" not in summary["engines_used"]
    assert summary["errors"] and any("You.com" in e for e in summary["errors"])
    assert summary["total_results"] == 0


def test_youcom_search_helper_returns_cli_shape(keyless_env):
    with patch("requests.Session.get", return_value=FakeResponse(SAMPLE_RESPONSE)):
        data = youcom_search("asyncio docs")

    assert data["query"] == "asyncio docs"
    assert data["total_results"] == 2
    assert "youcom" in data["engines_used"]
    first = data["results"][0]
    for key in ("title", "url", "href", "content", "text", "snippet"):
        assert key in first
    assert first["url"] == first["href"]
    assert first["content"] == first["text"] == first["snippet"]