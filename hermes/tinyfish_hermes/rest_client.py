"""TinyFish Search and Fetch REST client."""

from __future__ import annotations

from typing import Any, NoReturn, cast

import httpx

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
FETCH_MAX_URLS = 10


class TinyFishRestError(RuntimeError):
    """Raised for TinyFish REST transport or HTTP failures."""


def _headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "Accept": "application/json"}


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
