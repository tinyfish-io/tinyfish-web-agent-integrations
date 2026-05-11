"""TinyFish Web Agent function tools for Google ADK.

ADK auto-wraps plain Python functions as FunctionTools.
Just pass them in an Agent's ``tools`` list.
"""

import json
import logging
import os
from typing import Any, Literal, Optional, Union

from tinyfish import (
    BrowserProfile,
    ProxyConfig,
    ProxyCountryCode,
    RunStatus,
    TinyFish,
)

logger = logging.getLogger(__name__)

_INTEGRATION_NAME = "google-adk"

# Module-level client — created lazily on first use.
_client: Optional[TinyFish] = None


def _ensure_integration_tag() -> None:
    """Set a default integration tag for all TinyFish SDK requests."""
    os.environ.setdefault("TF_API_INTEGRATION", _INTEGRATION_NAME)


def _get_client() -> TinyFish:
    """Return a cached TinyFish SDK client."""
    global _client
    _ensure_integration_tag()
    if _client is None:
        key = os.environ.get("TINYFISH_API_KEY")
        if not key:
            raise RuntimeError(
                "TINYFISH_API_KEY is not set. "
                "Get your key at "
                "https://agent.tinyfish.ai/api-keys"
            )
        _client = TinyFish(api_key=key)
    return _client


def _run_kwargs(browser_profile: str, proxy_country: str) -> dict[str, Any]:
    """Build common kwargs for SDK agent.run / agent.queue."""
    try:
        bp = BrowserProfile(browser_profile)
    except ValueError:
        bp = BrowserProfile.LITE
    kwargs: dict[str, Any] = {"browser_profile": bp}
    if proxy_country:
        try:
            country = ProxyCountryCode(proxy_country)
        except ValueError:
            return {"_error": f"Invalid proxy country: {proxy_country!r}"}
        kwargs["proxy_config"] = ProxyConfig(enabled=True, country_code=country)
    return kwargs


def _safe_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Call fn, converting exceptions to error strings.

    Returns the result on success, or a string starting with
    "Error:" on failure.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("SDK call failed", exc_info=True)
        return f"Error: {exc}"


def _format_status(status: Union[RunStatus, str]) -> str:
    """Safely convert a RunStatus to string."""
    if isinstance(status, RunStatus):
        return status.value
    return str(status)


def _format_error(error: Union[dict, str, object]) -> str:
    """Extract a human-readable message from an error."""
    if isinstance(error, dict):
        return error.get("message", str(error))
    return str(error)


def _dump_json(value: Any) -> str:
    """Serialize SDK response models to a JSON string."""
    if hasattr(value, "model_dump_json"):
        return str(value.model_dump_json())
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump())
    return json.dumps(value)


# ------------------------------------------------------------------
# Tools — ADK auto-discovers these from function signatures
# ------------------------------------------------------------------


def tinyfish_web_agent(
    url: str,
    goal: str,
    browser_profile: str = "lite",
    proxy_country: str = "",
) -> str:
    """Automate any website using natural language.

    Navigate pages, extract structured data, fill forms, click
    buttons, and perform multi-step workflows on any website.
    Returns structured JSON results.

    Args:
        url: Target website URL (must start with http:// or
            https://).
        goal: Natural language description of what to do on the
            page. Be specific — include field names, button
            labels, and expected output format.
        browser_profile: "lite" (default, fast) or "stealth"
            (anti-detection for bot-protected sites).
        proxy_country: Optional country code to route through
            a proxy (US, GB, CA, DE, FR, JP, AU). Leave empty
            for no proxy.

    Returns:
        JSON string with the automation result, or an error
        message.
    """
    client = _get_client()
    rk = _run_kwargs(browser_profile, proxy_country)
    if "_error" in rk:
        return f"Error: {rk['_error']}"
    result = _safe_call(
        client.agent.run,
        url=url,
        goal=goal,
        **rk,
    )
    if isinstance(result, str):
        return result

    if result.status == RunStatus.COMPLETED:
        if result.result is not None:
            return json.dumps(result.result)
        return "Completed with no result data."

    error = getattr(result, "error", None)
    if error:
        return f"Automation failed: {_format_error(error)}"
    return f"Automation ended with status: {_format_status(result.status)}"


def tinyfish_queue_run(
    url: str,
    goal: str,
    browser_profile: str = "lite",
    proxy_country: str = "",
) -> str:
    """Start a browser automation asynchronously and return a
    run_id.

    Use ``tinyfish_get_run`` to check status and retrieve
    results. Best for long-running tasks.

    Args:
        url: Target website URL.
        goal: Natural language description of what to do.
        browser_profile: "lite" (default) or "stealth".
        proxy_country: Optional proxy country code.

    Returns:
        A message containing the run_id.
    """
    client = _get_client()
    rk = _run_kwargs(browser_profile, proxy_country)
    if "_error" in rk:
        return f"Error: {rk['_error']}"
    result = _safe_call(
        client.agent.queue,
        url=url,
        goal=goal,
        **rk,
    )
    if isinstance(result, str):
        return result

    return f"Automation started. run_id: {result.run_id}"


def tinyfish_get_run(run_id: str) -> str:
    """Get the status and result of a TinyFish automation run.

    Args:
        run_id: The unique run ID to look up.

    Returns:
        Status, result data, streaming URL, and/or error
        details.
    """
    run = _safe_call(_get_client().runs.get, run_id)
    if isinstance(run, str):
        return run

    parts = [f"Status: {_format_status(run.status)}"]
    streaming_url = getattr(run, "streaming_url", None)
    if streaming_url:
        parts.append(f"Live view: {streaming_url}")
    result = getattr(run, "result", None)
    if result is not None:
        parts.append(f"Result: {json.dumps(result)}")
    error = getattr(run, "error", None)
    if error:
        parts.append(f"Error: {_format_error(error)}")

    return "\n".join(parts)


def tinyfish_list_runs(
    status: str = "",
    limit: int = 20,
) -> str:
    """List recent TinyFish automation runs.

    Args:
        status: Optional filter — PENDING, RUNNING, COMPLETED,
            FAILED, or CANCELLED. Leave empty for all.
        limit: Maximum number of runs to return (1-100,
            default 20).

    Returns:
        A formatted list of runs with IDs, statuses, and URLs.
    """
    kwargs: dict[str, Any] = {"limit": limit}
    if status:
        try:
            kwargs["status"] = RunStatus(status)
        except ValueError:
            return f"Error: Invalid status filter: {status!r}"

    response = _safe_call(_get_client().runs.list, **kwargs)
    if isinstance(response, str):
        return response

    runs = getattr(response, "runs", [])
    if not runs:
        return "No runs found."

    lines = []
    for run in runs:
        rid = getattr(run, "run_id", "?")
        st = _format_status(getattr(run, "status", "?"))
        url = getattr(run, "url", "?")
        lines.append(f"- {rid} | {st} | {url}")

    return f"Found {len(runs)} runs:\n" + "\n".join(lines)


def tinyfish_search(
    query: str,
    location: str = "",
    language: str = "",
) -> str:
    """Search the web using TinyFish.

    Args:
        query: Search query.
        location: Optional location to scope results, such as
            "United States".
        language: Optional language code, such as "en".

    Returns:
        JSON string with search query, results, and total result
        count, or an error message.
    """
    kwargs: dict[str, Any] = {}
    if location:
        kwargs["location"] = location
    if language:
        kwargs["language"] = language

    response = _safe_call(_get_client().search.query, query=query, **kwargs)
    if isinstance(response, str):
        return response
    return _dump_json(response)


def tinyfish_fetch(
    urls: list[str],
    format: Literal["markdown", "html", "json"] = "markdown",
    links: bool = False,
    image_links: bool = False,
) -> str:
    """Fetch clean content from one or more URLs using TinyFish.

    Args:
        urls: One to ten URLs to fetch.
        format: Output format: "markdown", "html", or "json".
        links: Whether to include extracted links.
        image_links: Whether to include extracted image links.

    Returns:
        JSON string with fetched results and errors, or an error
        message.
    """
    response = _safe_call(
        _get_client().fetch.get_contents,
        urls=urls,
        format=format,
        links=links,
        image_links=image_links,
    )
    if isinstance(response, str):
        return response
    return _dump_json(response)


def tinyfish_create_browser_session(
    url: str = "",
    timeout_seconds: int = 0,
) -> str:
    """Create a TinyFish remote browser session.

    Args:
        url: Optional URL to open when the session starts.
        timeout_seconds: Optional inactivity timeout in seconds.
            Use 0 to let TinyFish apply the plan default.

    Returns:
        JSON string with session_id, cdp_url, and base_url, or an
        error message.
    """
    response = _safe_call(
        _get_client().browser.sessions.create,
        url=url or None,
        timeout_seconds=timeout_seconds or None,
    )
    if isinstance(response, str):
        return response
    return _dump_json(response)
