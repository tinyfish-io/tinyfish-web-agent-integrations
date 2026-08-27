from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tinyfish_hermes import rest_client


def _response(
    method: str,
    url: str,
    *,
    status: int = 200,
    payload: dict[str, Any] | None = None,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request(method, url)
    if content is not None:
        return httpx.Response(status, content=content, headers=headers, request=request)
    return httpx.Response(status, json=payload or {}, headers=headers, request=request)


def test_search_sends_supported_query_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return _response("GET", url, payload={"results": [{"title": "Result"}]})

    monkeypatch.setattr(rest_client.httpx, "get", fake_get)

    result = rest_client.search(
        "tiny fish",
        api_key="tf_test",
        timeout=12.5,
        location="US",
        language="en",
        recency_minutes=60,
        after_date="2026-01-01",
        before_date="2026-02-01",
        domain_type="news",
        page=2,
        purpose="research",
    )

    assert result == {"results": [{"title": "Result"}]}
    assert captured == {
        "url": rest_client.SEARCH_URL,
        "params": {
            "query": "tiny fish",
            "location": "US",
            "language": "en",
            "recency_minutes": 60,
            "after_date": "2026-01-01",
            "before_date": "2026-02-01",
            "domain_type": "news",
            "page": 2,
            "purpose": "research",
        },
        "headers": {"X-API-Key": "tf_test", "Accept": "application/json"},
        "timeout": 12.5,
    }


def test_search_omits_empty_optional_query_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return _response("GET", url)

    monkeypatch.setattr(rest_client.httpx, "get", fake_get)

    rest_client.search("query", api_key="tf_test", location="", page=None)

    assert captured["params"] == {"query": "query"}


def test_fetch_sends_supported_body_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return _response(
            "POST", url, payload={"data": [{"url": "https://example.com"}]}
        )

    monkeypatch.setattr(rest_client.httpx, "post", fake_post)

    result = rest_client.fetch(
        ["https://example.com"],
        api_key="tf_test",
        output_format="html",
        links=False,
        image_links=True,
        ttl=300,
        per_url_timeout_ms=2500,
        timeout=22.0,
    )

    assert result == {"data": [{"url": "https://example.com"}]}
    assert captured == {
        "url": rest_client.FETCH_URL,
        "json": {
            "urls": ["https://example.com"],
            "format": "html",
            "links": False,
            "image_links": True,
            "ttl": 300,
            "per_url_timeout_ms": 2500,
        },
        "headers": {
            "X-API-Key": "tf_test",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "timeout": 22.0,
    }


def test_fetch_omits_unset_optional_body_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return _response("POST", url)

    monkeypatch.setattr(rest_client.httpx, "post", fake_post)

    rest_client.fetch(["https://example.com"], api_key="tf_test")

    assert captured["json"] == {"urls": ["https://example.com"], "format": "markdown"}


RestCall = Callable[[], dict[str, Any]]

REST_CALLS = [
    ("get", lambda: rest_client.search("query", api_key="tf_test"), "TinyFish Search"),
    (
        "post",
        lambda: rest_client.fetch(["https://example.com"], api_key="tf_test"),
        "TinyFish Fetch",
    ),
]


@pytest.mark.parametrize(("method_name", "call", "service"), REST_CALLS)
@pytest.mark.parametrize("status", [402, 500])
def test_rest_methods_report_http_failures(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    call: RestCall,
    service: str,
    status: int,
) -> None:
    def fake_request(url: str, **kwargs: Any) -> httpx.Response:
        return _response(
            method_name.upper(), url, status=status, payload={"error": "redacted"}
        )

    monkeypatch.setattr(rest_client.httpx, method_name, fake_request)

    expected = "credits or billing may be required" if status == 402 else "HTTP 500"
    with pytest.raises(rest_client.TinyFishRestError, match=expected) as exc_info:
        call()

    assert service in str(exc_info.value)


@pytest.mark.parametrize(("method_name", "call", "service"), REST_CALLS)
def test_rest_methods_report_transport_failures(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    call: RestCall,
    service: str,
) -> None:
    def fake_request(url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError(
            "network unavailable", request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(rest_client.httpx, method_name, fake_request)

    with pytest.raises(
        rest_client.TinyFishRestError, match=f"Could not reach {service}"
    ):
        call()


@pytest.mark.parametrize(("method_name", "call", "service"), REST_CALLS)
def test_rest_methods_report_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    call: RestCall,
    service: str,
) -> None:
    def fake_request(url: str, **kwargs: Any) -> httpx.Response:
        return _response(method_name.upper(), url, content=b"{")

    monkeypatch.setattr(rest_client.httpx, method_name, fake_request)

    with pytest.raises(
        rest_client.TinyFishRestError, match=f"{service} returned invalid JSON"
    ):
        call()
