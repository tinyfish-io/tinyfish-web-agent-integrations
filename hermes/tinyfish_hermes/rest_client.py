"""TinyFish Search and Fetch REST client."""

from __future__ import annotations

import math
import time
from typing import Any, NoReturn, cast

import httpx

from . import __version__

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
FETCH_MAX_URLS = 10
BROWSER_URL = "https://api.browser.tinyfish.ai"
WALLET_URL = "https://agent.tinyfish.ai/v1/wallet"
SEARCH_USAGE_URL = f"{SEARCH_URL}/usage"
FETCH_USAGE_URL = f"{FETCH_URL}/usage"

_BROWSER_CLOSE_MAX_ATTEMPTS = 3
_BROWSER_CLOSE_RETRYABLE_STATUSES = frozenset({409, 429, 500, 503, 504})
_BROWSER_CLOSE_RETRY_AFTER_CAP_SECONDS = 5.0
_BROWSER_CLOSE_RETRY_BASE_SECONDS = 0.25


class TinyFishRestError(RuntimeError):
    """Raised for TinyFish REST transport or HTTP failures."""


class TinyFishWalletNotFound(TinyFishRestError):
    """Raised when an account uses legacy billing or has no wallet yet."""


def _headers(api_key: str) -> dict[str, str]:
    # Without these the server files every call as untagged `api`.
    return {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "X-TF-Client-Name": "tinyfish-hermes",
        "X-TF-Client-Version": __version__,
    }


def _json_headers(api_key: str) -> dict[str, str]:
    headers = _headers(api_key)
    headers["Content-Type"] = "application/json"
    return headers


def _raise_http_error(service: str, exc: httpx.HTTPStatusError) -> NoReturn:
    status = exc.response.status_code
    if status == 402:
        raise TinyFishRestError(
            f"{service} returned HTTP 402. TinyFish credits or billing may be required."
        ) from exc
    raise TinyFishRestError(f"{service} returned HTTP {status}") from exc


def search(
    query: str,
    *,
    api_key: str,
    timeout: float = 30.0,
    location: str | None = None,
    language: str | None = None,
    recency_minutes: int | None = None,
    after_date: str | None = None,
    before_date: str | None = None,
    domain_type: str | None = None,
    page: int | None = None,
    purpose: str | None = None,
) -> dict[str, Any]:
    """Run a TinyFish Search API query."""

    params: dict[str, Any] = {"query": query}
    for key, value in {
        "location": location,
        "language": language,
        "recency_minutes": recency_minutes,
        "after_date": after_date,
        "before_date": before_date,
        "domain_type": domain_type,
        "page": page,
        "purpose": purpose,
    }.items():
        if value is not None and value != "":
            params[key] = value

    try:
        response = httpx.get(
            SEARCH_URL,
            params=params,
            headers=_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        _raise_http_error("TinyFish Search", exc)
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Search: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Search returned invalid JSON") from exc


def fetch(
    urls: list[str],
    *,
    api_key: str,
    output_format: str = "markdown",
    links: bool | None = None,
    image_links: bool | None = None,
    ttl: int | None = None,
    per_url_timeout_ms: int | None = None,
    # Batches can run ~120s server-side; docs recommend a client timeout >= 150s.
    timeout: float = 150.0,
) -> dict[str, Any]:
    """Run the TinyFish Fetch API for one or more URLs."""

    body: dict[str, Any] = {"urls": urls, "format": output_format}
    for key, value in {
        "links": links,
        "image_links": image_links,
        "ttl": ttl,
        "per_url_timeout_ms": per_url_timeout_ms,
    }.items():
        if value is not None:
            body[key] = value

    try:
        response = httpx.post(
            FETCH_URL,
            json=body,
            headers=_json_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        _raise_http_error("TinyFish Fetch", exc)
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Fetch: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Fetch returned invalid JSON") from exc


def create_browser_session(
    *,
    api_key: str,
    url: str | None = None,
    timeout_seconds: int | None = None,
    timeout: float = 90.0,
) -> dict[str, Any]:
    """Create a TinyFish Browser session."""

    body: dict[str, Any] = {}
    if url:
        body["url"] = url
    if timeout_seconds is not None:
        body["timeout_seconds"] = timeout_seconds
    try:
        response = httpx.post(
            BROWSER_URL,
            json=body,
            headers=_json_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        _raise_http_error("TinyFish Browser", exc)
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Browser: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Browser returned invalid JSON") from exc


def _browser_close_retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = str(response.headers.get("Retry-After", "") or "").strip()
        if retry_after:
            try:
                seconds = float(retry_after)
            except ValueError:
                seconds = -1.0
            if math.isfinite(seconds) and seconds >= 0:
                return min(seconds, _BROWSER_CLOSE_RETRY_AFTER_CAP_SECONDS)
    return _BROWSER_CLOSE_RETRY_BASE_SECONDS * (2.0**attempt)


def close_browser_session(
    session_id: str, *, api_key: str, timeout: float = 15.0
) -> bool:
    """Terminate a Browser session with bounded transient-failure retries."""

    # A 404 is not success: it can also mean the session belongs to another key.
    url = f"{BROWSER_URL}/{session_id}"
    for attempt in range(_BROWSER_CLOSE_MAX_ATTEMPTS):
        response: httpx.Response | None = None
        try:
            response = httpx.delete(url, headers=_headers(api_key), timeout=timeout)
        except httpx.RequestError:
            retry = True
        else:
            if 200 <= response.status_code < 300:
                return True
            retry = response.status_code in _BROWSER_CLOSE_RETRYABLE_STATUSES

        if not retry or attempt + 1 >= _BROWSER_CLOSE_MAX_ATTEMPTS:
            return False
        delay = _browser_close_retry_delay(response, attempt)
        if delay > 0:
            time.sleep(delay)
    return False


def _read_usage(
    url: str,
    *,
    service: str,
    api_key: str,
    timeout: float,
) -> dict[str, Any]:
    try:
        response = httpx.get(url, headers=_headers(api_key), timeout=timeout)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        _raise_http_error(service, exc)
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach {service}: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError(f"{service} returned invalid JSON") from exc


def search_usage(*, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
    """Return TinyFish Search operation history."""

    return _read_usage(
        SEARCH_USAGE_URL,
        service="TinyFish Search usage",
        api_key=api_key,
        timeout=timeout,
    )


def fetch_usage(*, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
    """Return TinyFish Fetch operation history."""

    return _read_usage(
        FETCH_USAGE_URL,
        service="TinyFish Fetch usage",
        api_key=api_key,
        timeout=timeout,
    )


def wallet(*, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
    """Return the caller's TinyFish wallet balance and billing rates."""

    try:
        response = httpx.get(WALLET_URL, headers=_headers(api_key), timeout=timeout)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise TinyFishWalletNotFound(
                "TinyFish has no wallet for this account "
                "(legacy billing or no Metronome customer yet)."
            ) from exc
        _raise_http_error("TinyFish Wallet", exc)
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach TinyFish Wallet: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError("TinyFish Wallet returned invalid JSON") from exc
