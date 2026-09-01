from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tinyfish_hermes import __version__, rest_client

_AUTH_HEADERS = {
    "X-API-Key": "tf_test",
    "Accept": "application/json",
    "X-TF-Client-Name": "tinyfish-hermes",
    "X-TF-Client-Version": __version__,
}


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
        "headers": _AUTH_HEADERS,
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
        "headers": {**_AUTH_HEADERS, "Content-Type": "application/json"},
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
    (
        "post",
        lambda: rest_client.create_browser_session(api_key="tf_test"),
        "TinyFish Browser",
    ),
    (
        "get",
        lambda: rest_client.search_usage(api_key="tf_test"),
        "TinyFish Search usage",
    ),
    ("get", lambda: rest_client.fetch_usage(api_key="tf_test"), "TinyFish Fetch usage"),
    ("get", lambda: rest_client.wallet(api_key="tf_test"), "TinyFish Wallet"),
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


def test_create_browser_session_sends_only_configured_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return _response("POST", url, payload={"session_id": "sess_123"})

    monkeypatch.setattr(rest_client.httpx, "post", fake_post)

    result = rest_client.create_browser_session(
        api_key="tf_test",
        url="https://example.com",
        timeout_seconds=120,
        timeout=8.0,
    )

    assert result == {"session_id": "sess_123"}
    assert captured["url"] == rest_client.BROWSER_URL
    assert captured["json"] == {"url": "https://example.com", "timeout_seconds": 120}
    assert captured["timeout"] == 8.0
    assert captured["headers"]["X-API-Key"] == "tf_test"


def test_create_browser_session_omits_unset_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return _response("POST", url, payload={"session_id": "sess_123"})

    monkeypatch.setattr(rest_client.httpx, "post", fake_post)

    rest_client.create_browser_session(api_key="tf_test")

    assert captured["json"] == {}


@pytest.mark.parametrize("status", [200, 201, 202, 204, 299])
def test_close_browser_session_accepts_any_success_status(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    captured: dict[str, Any] = {}

    def fake_delete(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return _response("DELETE", url, status=status)

    monkeypatch.setattr(rest_client.httpx, "delete", fake_delete)

    assert (
        rest_client.close_browser_session("sess_123", api_key="tf_test", timeout=9.0)
        is True
    )
    assert captured["url"] == f"{rest_client.BROWSER_URL}/sess_123"
    assert captured["headers"] == {
        "X-API-Key": "tf_test",
        "Accept": "application/json",
        "X-TF-Client-Name": "tinyfish-hermes",
        "X-TF-Client-Version": __version__,
    }
    assert captured["timeout"] == 9.0


def test_close_browser_session_rejects_404_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_delete(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response("DELETE", url, status=404)

    monkeypatch.setattr(rest_client.httpx, "delete", fake_delete)
    monkeypatch.setattr(
        rest_client.time, "sleep", lambda delay: pytest.fail("must not retry")
    )

    assert rest_client.close_browser_session("sess_123", api_key="tf_test") is False
    assert calls == 1


@pytest.mark.parametrize("status", [409, 429, 500, 503, 504])
def test_close_browser_session_retries_documented_transient_statuses(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    statuses = iter([status, 204])
    sleeps: list[float] = []
    monkeypatch.setattr(
        rest_client.httpx,
        "delete",
        lambda url, **kwargs: _response("DELETE", url, status=next(statuses)),
    )
    monkeypatch.setattr(rest_client.time, "sleep", sleeps.append)

    assert rest_client.close_browser_session("sess_123", api_key="tf_test") is True
    assert sleeps == [0.25]


def test_close_browser_session_honors_bounded_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            _response(
                "DELETE",
                rest_client.BROWSER_URL,
                status=429,
                headers={"Retry-After": "60"},
            ),
            _response("DELETE", rest_client.BROWSER_URL, status=204),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(
        rest_client.httpx, "delete", lambda url, **kwargs: next(responses)
    )
    monkeypatch.setattr(rest_client.time, "sleep", sleeps.append)

    assert rest_client.close_browser_session("sess_123", api_key="tf_test") is True
    assert sleeps == [5.0]


def test_close_browser_session_retries_transport_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def flaky_delete(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError(
                "network unavailable", request=httpx.Request("DELETE", url)
            )
        return _response("DELETE", url, status=204)

    monkeypatch.setattr(rest_client.httpx, "delete", flaky_delete)
    monkeypatch.setattr(rest_client.time, "sleep", sleeps.append)

    assert rest_client.close_browser_session("sess_123", api_key="tf_test") is True
    assert calls == 2
    assert sleeps == [0.25]


def test_close_browser_session_returns_false_after_bounded_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def fail(url: str, **kwargs: Any) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response("DELETE", url, status=503)

    monkeypatch.setattr(rest_client.httpx, "delete", fail)
    monkeypatch.setattr(rest_client.time, "sleep", sleeps.append)

    assert rest_client.close_browser_session("sess_123", api_key="tf_test") is False
    assert calls == 3
    assert sleeps == [0.25, 0.5]


@pytest.mark.parametrize(
    ("call", "expected_url"),
    [
        (
            lambda: rest_client.search_usage(api_key="tf_test", timeout=11.0),
            "https://api.search.tinyfish.ai/usage",
        ),
        (
            lambda: rest_client.fetch_usage(api_key="tf_test", timeout=11.0),
            "https://api.fetch.tinyfish.ai/usage",
        ),
        (
            lambda: rest_client.wallet(api_key="tf_test", timeout=11.0),
            "https://agent.tinyfish.ai/v1/wallet",
        ),
    ],
    ids=["search_usage", "fetch_usage", "wallet"],
)
def test_wallet_and_usage_use_documented_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    call: RestCall,
    expected_url: str,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        captured.update(url=url, **kwargs)
        return _response("GET", url, payload={"items": []})

    monkeypatch.setattr(rest_client.httpx, "get", fake_get)

    assert call() == {"items": []}
    assert captured == {
        "url": expected_url,
        "headers": _AUTH_HEADERS,
        "timeout": 11.0,
    }


def test_wallet_reports_documented_not_found_account_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        return _response(
            "GET",
            url,
            status=404,
            payload={"error": {"code": "NOT_FOUND", "message": "Wallet not found"}},
        )

    monkeypatch.setattr(rest_client.httpx, "get", fake_get)

    with pytest.raises(
        rest_client.TinyFishWalletNotFound,
        match="legacy billing or no Metronome customer yet",
    ):
        rest_client.wallet(api_key="tf_test")
