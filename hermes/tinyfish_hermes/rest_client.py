"""TinyFish Search and Fetch REST client."""

from __future__ import annotations

import hashlib
import math
import os
import sys
import time
import uuid
from typing import Any, NoReturn, cast
from urllib.parse import quote

import httpx

from . import __version__

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
BROWSER_URL = "https://api.browser.tinyfish.ai"
AGENT_URL = "https://agent.tinyfish.ai"
WALLET_URL = f"{AGENT_URL}/v1/wallet"
SEARCH_USAGE_URL = f"{SEARCH_URL}/usage"
FETCH_USAGE_URL = f"{FETCH_URL}/usage"
TELEMETRY_URL = f"{AGENT_URL}/api/cli/connect-event"

_BROWSER_CLOSE_MAX_ATTEMPTS = 3
_BROWSER_CLOSE_RETRYABLE_STATUSES = frozenset({409, 429, 500, 503, 504})
_BROWSER_CLOSE_RETRY_AFTER_CAP_SECONDS = 5.0
_BROWSER_CLOSE_RETRY_BASE_SECONDS = 0.25


class TinyFishRestError(RuntimeError):
    """Raised for TinyFish REST transport or HTTP failures."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details
        self.retry_after = retry_after


class TinyFishWalletNotFound(TinyFishRestError):
    """Raised when an account uses legacy billing or has no wallet yet."""


def _headers(api_key: str) -> dict[str, str]:
    # Without these, telemetry cannot tell the plugin from raw curl.
    return {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "X-TF-Client-Name": "hermes",
        "X-TF-Client-Version": __version__,
    }


def _json_headers(api_key: str) -> dict[str, str]:
    headers = _headers(api_key)
    headers["Content-Type"] = "application/json"
    return headers


def _server_error(response: httpx.Response) -> dict[str, Any]:
    try:
        error = response.json().get("error")
    except Exception:
        return {}
    return error if isinstance(error, dict) else {}


def _server_message(response: httpx.Response) -> str:
    message = _server_error(response).get("message")
    return message[:500] if isinstance(message, str) else ""


def _raise_http_error(service: str, exc: httpx.HTTPStatusError) -> NoReturn:
    status = exc.response.status_code
    error = _server_error(exc.response)
    code, details = error.get("code"), error.get("details")
    # Datasets names an already-created dataset in details on any refusal status.
    extra: dict[str, Any] = {
        "code": code if isinstance(code, str) else None,
        "details": details if isinstance(details, dict) else None,
        "retry_after": exc.response.headers.get("Retry-After"),
    }
    if status == 402:
        raise TinyFishRestError(
            f"{service} returned HTTP 402. "
            "TinyFish credits or billing may be required.",
            status,
            **extra,
        ) from exc
    # 4xx text is TinyFish's own validation message and tells the agent what to fix.
    detail = _server_message(exc.response) if 400 <= status < 500 else ""
    suffix = f": {detail}" if detail else ""
    raise TinyFishRestError(
        f"{service} returned HTTP {status}{suffix}", status, **extra
    ) from exc


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
    # Hermes abandons an extract at 120s, so return our own error before that.
    timeout: float = 110.0,
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


def _agent_request(
    method: str,
    path: str,
    *,
    api_key: str,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
    service: str = "TinyFish Agent",
) -> dict[str, Any]:
    try:
        response = httpx.request(
            method,
            f"{AGENT_URL}{path}",
            json=json_body,
            params=params,
            headers=_json_headers(api_key),
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        _raise_http_error(service, exc)
    except httpx.ReadTimeout as exc:
        # An unanswered POST may still have landed; a blind retry duplicates it.
        if method == "POST":
            raise TinyFishRestError(
                f"{service} did not answer in time, so the request may have gone "
                "through. List existing items before retrying."
            ) from exc
        raise TinyFishRestError(f"Could not reach {service}: {exc}") from exc
    except httpx.RequestError as exc:
        raise TinyFishRestError(f"Could not reach {service}: {exc}") from exc
    except ValueError as exc:
        raise TinyFishRestError(f"{service} returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise TinyFishRestError(f"{service} returned an unexpected response")
    return data


def start_run(
    url: str,
    goal: str,
    *,
    api_key: str,
    browser_profile: str = "lite",
    proxy_country_code: str | None = None,
    use_profile: bool = False,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Enqueue a TinyFish Agent run; returns immediately with ``run_id``."""

    body: dict[str, Any] = {
        "url": url,
        "goal": goal,
        "browser_profile": browser_profile,
        "api_integration": "hermes",
    }
    if proxy_country_code:
        body["proxy_config"] = {"enabled": True, "country_code": proxy_country_code}
    # The API rejects profile_id without use_profile, so an id implies it.
    if use_profile or profile_id:
        body["use_profile"] = True
    if profile_id:
        body["profile_id"] = profile_id
    return _agent_request(
        "POST", "/v1/automation/run-async", api_key=api_key, json_body=body
    )


def telemetry_disabled(value: str | None = None) -> bool:
    # Matches the TinyFish CLI: anything but empty, 0 or false opts out.
    if value is None:
        value = os.environ.get("TINYFISH_NO_TELEMETRY", "")
    return value.strip().lower() not in ("", "0", "false")


def report_setup(outcome: str, *, key_source: str, api_key: str = "") -> None:
    """Record a ``hermes tinyfish setup`` outcome; never raises."""

    if telemetry_disabled():
        return
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key-lookup"] = hashlib.sha256(api_key.encode()).hexdigest()
    body = {
        "event": "harness_plugin_setup",
        "harness": "hermes",
        "plugin_version": __version__,
        "outcome": outcome,
        "key_source": key_source,
        "runtime_platform": sys.platform,
        "setup_id": str(uuid.uuid4()),
    }
    try:
        httpx.post(TELEMETRY_URL, headers=headers, json=body, timeout=2.0)
    except Exception:
        pass


def get_run(run_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request("GET", f"/v1/runs/{run_id}", api_key=api_key)


def cancel_run(run_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request("POST", f"/v1/runs/{run_id}/cancel", api_key=api_key)


def _profile_request(
    method: str,
    path: str,
    *,
    api_key: str,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _agent_request(
        method,
        f"/v1/profiles{path}",
        api_key=api_key,
        json_body=json_body,
        timeout=timeout,
        service="TinyFish Profiles",
    )


def _profile_path(profile_id: str) -> str:
    return "/" + quote(profile_id, safe="")


def list_profiles(*, api_key: str) -> dict[str, Any]:
    return _profile_request("GET", "", api_key=api_key)


def create_profile(fields: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    return _profile_request("POST", "", api_key=api_key, json_body=fields)


def get_profile(
    profile_id: str, *, api_key: str, timeout: float = 30.0
) -> dict[str, Any]:
    return _profile_request(
        "GET", _profile_path(profile_id), api_key=api_key, timeout=timeout
    )


def update_profile(
    profile_id: str, fields: dict[str, Any], *, api_key: str
) -> dict[str, Any]:
    return _profile_request(
        "PATCH", _profile_path(profile_id), api_key=api_key, json_body=fields
    )


def delete_profile(profile_id: str, *, api_key: str) -> dict[str, Any]:
    return _profile_request("DELETE", _profile_path(profile_id), api_key=api_key)


def _id(value: str) -> str:
    return quote(value, safe="")


_MONITORS = "TinyFish Monitors"
_RESEARCH = "TinyFish Research"
_DATASETS = "TinyFish Datasets"


def create_monitor(fields: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    # The baseline check runs inside the request.
    return _agent_request(
        "POST",
        "/v1/monitors",
        api_key=api_key,
        json_body=fields,
        timeout=60.0,
        service=_MONITORS,
    )


def list_monitors(*, api_key: str) -> dict[str, Any]:
    return _agent_request("GET", "/v1/monitors", api_key=api_key, service=_MONITORS)


def get_monitor(
    monitor_id: str, *, api_key: str, timeout: float = 30.0
) -> dict[str, Any]:
    return _agent_request(
        "GET",
        f"/v1/monitors/{_id(monitor_id)}",
        api_key=api_key,
        timeout=timeout,
        service=_MONITORS,
    )


def update_monitor(
    monitor_id: str, fields: dict[str, Any], *, api_key: str
) -> dict[str, Any]:
    return _agent_request(
        "PATCH",
        f"/v1/monitors/{_id(monitor_id)}",
        api_key=api_key,
        json_body=fields,
        service=_MONITORS,
    )


def delete_monitor(monitor_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "DELETE", f"/v1/monitors/{_id(monitor_id)}", api_key=api_key, service=_MONITORS
    )


def run_monitor(monitor_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        f"/v1/monitors/{_id(monitor_id)}/runs",
        api_key=api_key,
        timeout=60.0,
        service=_MONITORS,
    )


def start_research(fields: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        "/v1/automation/run-research-async",
        api_key=api_key,
        json_body=fields,
        service=_RESEARCH,
    )


def list_research(params: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "GET", "/v1/research-run", api_key=api_key, params=params, service=_RESEARCH
    )


def get_research(research_run_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "GET",
        f"/v1/research-run/{_id(research_run_id)}",
        api_key=api_key,
        service=_RESEARCH,
    )


def cancel_research(research_run_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        f"/v1/research-run/{_id(research_run_id)}/cancel",
        api_key=api_key,
        service=_RESEARCH,
    )


# Plan and prompt-based create run the spec agent in-request (server maxDuration 90s).
def plan_dataset(prompt: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        "/v1/datasets/plan",
        api_key=api_key,
        json_body={"prompt": prompt},
        timeout=95.0,
        service=_DATASETS,
    )


def create_dataset(fields: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        "/v1/datasets",
        api_key=api_key,
        json_body=fields,
        timeout=95.0,
        service=_DATASETS,
    )


def list_datasets(params: dict[str, Any], *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "GET", "/v1/datasets", api_key=api_key, params=params, service=_DATASETS
    )


def get_dataset(
    dataset_id: str, *, api_key: str, timeout: float = 30.0
) -> dict[str, Any]:
    return _agent_request(
        "GET",
        f"/v1/datasets/{_id(dataset_id)}",
        api_key=api_key,
        timeout=timeout,
        service=_DATASETS,
    )


def get_dataset_rows(
    dataset_id: str, params: dict[str, Any], *, api_key: str
) -> dict[str, Any]:
    return _agent_request(
        "GET",
        f"/v1/datasets/{_id(dataset_id)}/rows",
        api_key=api_key,
        params=params,
        service=_DATASETS,
    )


def populate_dataset(
    dataset_id: str, fields: dict[str, Any], *, api_key: str
) -> dict[str, Any]:
    return _agent_request(
        "POST",
        f"/v1/datasets/{_id(dataset_id)}/populate",
        api_key=api_key,
        json_body=fields,
        service=_DATASETS,
    )


def cancel_dataset_run(dataset_id: str, run_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "POST",
        f"/v1/datasets/{_id(dataset_id)}/runs/{_id(run_id)}/cancel",
        api_key=api_key,
        service=_DATASETS,
    )


def delete_dataset(dataset_id: str, *, api_key: str) -> dict[str, Any]:
    return _agent_request(
        "DELETE", f"/v1/datasets/{_id(dataset_id)}", api_key=api_key, service=_DATASETS
    )
