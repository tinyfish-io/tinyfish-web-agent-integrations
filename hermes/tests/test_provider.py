from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import Any

import pytest

from tinyfish_hermes import provider as provider_mod
from tinyfish_hermes import rest_client
from tinyfish_hermes.provider import TinyFishWebSearchProvider


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    monkeypatch.delenv("MCP_TINYFISH_API_KEY", raising=False)
    yield


def test_is_available_requires_an_api_key() -> None:
    assert TinyFishWebSearchProvider().is_available() is False


def test_is_available_with_primary_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    assert TinyFishWebSearchProvider().is_available() is True


def test_is_available_with_cli_seeded_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TINYFISH_API_KEY", "tf_cli")

    assert TinyFishWebSearchProvider().is_available() is True


def test_primary_key_wins_over_cli_seeded_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_primary")
    monkeypatch.setenv("MCP_TINYFISH_API_KEY", "tf_cli")

    assert provider_mod._api_key() == "tf_primary"


def test_provider_identity_and_capabilities() -> None:
    provider = TinyFishWebSearchProvider()

    assert provider.name == "tinyfish"
    assert provider.display_name == "TinyFish"
    assert provider.supports_search() is True
    assert provider.supports_extract() is True
    assert provider.supports_crawl() is False


def test_setup_schema_advertises_api_key() -> None:
    schema = TinyFishWebSearchProvider().get_setup_schema()

    assert schema["env_vars"][0]["key"] == "TINYFISH_API_KEY"
    assert schema["env_vars"][0]["url"] == "https://agent.tinyfish.ai/api-keys"


def test_search_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen: dict[str, Any] = {}

    def fake_search(query: str, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        seen.update(query=query, api_key=api_key, **kwargs)
        return {"results": [{"title": "REST result", "url": "https://example.com"}]}

    monkeypatch.setattr(rest_client, "search", fake_search)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "REST result"
    assert seen == {"query": "query", "api_key": "tf_test"}


def test_search_applies_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda query, *, api_key, **kwargs: {
            "results": [
                {"title": f"Result {idx}", "url": f"https://example.com/{idx}"}
                for idx in range(10)
            ]
        },
    )

    result = TinyFishWebSearchProvider().search("query", limit=2)

    assert len(result["data"]["web"]) == 2


def test_search_passes_config_options_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        provider_mod,
        "search_options",
        lambda: {"location": "US", "language": "en", "page": 2},
    )
    seen: dict[str, Any] = {}

    def fake_search(query: str, *, api_key: str, **kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return {"results": [{"title": query, "url": "https://example.com"}]}

    monkeypatch.setattr(rest_client, "search", fake_search)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert seen == {"location": "US", "language": "en", "page": 2}


def test_search_missing_key_names_both_env_vars_and_key_url() -> None:
    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is False
    assert "TINYFISH_API_KEY" in result["error"]
    assert "MCP_TINYFISH_API_KEY" in result["error"]
    assert "https://agent.tinyfish.ai/api-keys" in result["error"]


def test_search_preserves_controlled_rest_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    def raise_rest_error(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise rest_client.TinyFishRestError("TinyFish Search returned HTTP 402")

    monkeypatch.setattr(rest_client, "search", raise_rest_error)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is False
    assert "HTTP 402" in result["error"]


def test_search_suppresses_arbitrary_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    def raise_unexpected(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("tf_secret leaked in message")

    monkeypatch.setattr(rest_client, "search", raise_unexpected)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is False
    assert "tf_secret" not in result["error"]
    assert "RuntimeError" in result["error"]


def test_search_honors_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(sys.modules["tools.interrupt"], "is_interrupted", lambda: True)
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda *args, **kwargs: pytest.fail("REST must not run when interrupted"),
    )

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result == {"success": False, "error": "Interrupted"}


def test_extract_success_with_format_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen: dict[str, Any] = {}

    def fake_fetch(
        urls: list[str], *, api_key: str, output_format: str, **kwargs: Any
    ) -> dict[str, Any]:
        seen.update(api_key=api_key, output_format=output_format, **kwargs)
        return {"results": [{"url": urls[0], "title": "Doc", "text": "body"}]}

    monkeypatch.setattr(rest_client, "fetch", fake_fetch)

    docs = TinyFishWebSearchProvider().extract(["https://example.com"], format="html")

    assert docs[0]["title"] == "Doc"
    assert docs[0]["content"] == "body"
    assert seen == {"api_key": "tf_test", "output_format": "html"}


def test_extract_chunks_batches_beyond_the_fetch_url_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    batches: list[list[str]] = []

    def fake_fetch(urls: list[str], **kwargs: Any) -> dict[str, Any]:
        batches.append(list(urls))
        return {"results": [{"url": u, "title": "t", "text": "x"} for u in urls]}

    monkeypatch.setattr(rest_client, "fetch", fake_fetch)
    urls = [f"https://example.com/{i}" for i in range(11)]

    docs = TinyFishWebSearchProvider().extract(urls)

    assert [len(b) for b in batches] == [10, 1]
    assert [d["url"] for d in docs] == urls


def test_extract_chunk_failure_only_errors_that_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    calls = iter([rest_client.TinyFishRestError("boom"), None])

    def fake_fetch(urls: list[str], **kwargs: Any) -> dict[str, Any]:
        exc = next(calls)
        if exc is not None:
            raise exc
        return {"results": [{"url": u, "title": "t", "text": "x"} for u in urls]}

    monkeypatch.setattr(rest_client, "fetch", fake_fetch)
    urls = [f"https://example.com/{i}" for i in range(11)]

    docs = TinyFishWebSearchProvider().extract(urls)

    assert len(docs) == 11
    assert all("boom" in d["error"] for d in docs[:10])
    assert docs[10]["content"] == "x"


def test_extract_defaults_to_configured_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(provider_mod, "default_fetch_format", lambda: "text")
    seen: dict[str, Any] = {}

    def fake_fetch(
        urls: list[str], *, api_key: str, output_format: str, **kwargs: Any
    ) -> dict[str, Any]:
        seen["output_format"] = output_format
        return {"results": [{"url": urls[0], "text": "body"}]}

    monkeypatch.setattr(rest_client, "fetch", fake_fetch)

    TinyFishWebSearchProvider().extract(["https://example.com"])

    assert seen == {"output_format": "text"}


def test_extract_passes_config_options_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        provider_mod, "fetch_options", lambda: {"ttl": 300, "links": True}
    )
    seen: dict[str, Any] = {}

    def fake_fetch(
        urls: list[str], *, api_key: str, output_format: str, **kwargs: Any
    ) -> dict[str, Any]:
        seen.update(kwargs)
        return {"results": [{"url": urls[0], "text": "body"}]}

    monkeypatch.setattr(rest_client, "fetch", fake_fetch)

    TinyFishWebSearchProvider().extract(["https://example.com"])

    assert seen == {"ttl": 300, "links": True}


def test_extract_missing_key_returns_error_document_per_url() -> None:
    urls = ["https://a.example", "https://b.example"]

    docs = TinyFishWebSearchProvider().extract(urls)

    assert [doc["url"] for doc in docs] == urls
    for doc in docs:
        assert "TINYFISH_API_KEY" in doc["error"]
        assert "MCP_TINYFISH_API_KEY" in doc["error"]
        assert doc["content"] == ""


def test_extract_rest_failure_returns_error_document_per_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    def raise_rest_error(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise rest_client.TinyFishRestError("TinyFish Fetch returned HTTP 402")

    monkeypatch.setattr(rest_client, "fetch", raise_rest_error)

    docs = TinyFishWebSearchProvider().extract(["https://example.com"])

    assert docs[0]["url"] == "https://example.com"
    assert "HTTP 402" in docs[0]["error"]


def test_extract_honors_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(sys.modules["tools.interrupt"], "is_interrupted", lambda: True)
    monkeypatch.setattr(
        rest_client,
        "fetch",
        lambda *args, **kwargs: pytest.fail("REST must not run when interrupted"),
    )

    docs = TinyFishWebSearchProvider().extract(["https://example.com"])

    assert docs[0]["error"] == "Interrupted"
