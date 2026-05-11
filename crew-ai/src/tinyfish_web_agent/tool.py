import json
import logging
import os
from typing import Any, List, Literal, Optional, Type

from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, field_validator
from tinyfish import (
    BrowserProfile,
    ProxyConfig,
    ProxyCountryCode,
    RunStatus,
    TinyFish,
)

logger = logging.getLogger(__name__)

_INTEGRATION_NAME = "crew-ai"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class TinyfishRunInput(BaseModel):
    """Input schema for running a browser automation."""

    url: str = Field(..., description="Target website URL to automate.")
    goal: str = Field(
        ...,
        description=(
            "Natural language description of what to accomplish on the website."
        ),
    )
    browser_profile: Literal["lite", "stealth"] = Field(
        default="lite",
        description=(
            'Browser execution mode. "lite" (default) is fast for '
            'standard sites. "stealth" enables anti-detection for '
            "sites with bot protection."
        ),
    )

    @field_validator("url")
    @classmethod
    def _check_url_scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class TinyfishGetRunInput(BaseModel):
    """Input schema for getting a run by ID."""

    run_id: str = Field(..., description="The unique run ID to look up.")


class TinyfishListRunsInput(BaseModel):
    """Input schema for listing runs."""

    status: Optional[
        Literal[
            "PENDING",
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        ]
    ] = Field(default=None, description="Filter runs by status.")
    goal: Optional[str] = Field(
        default=None,
        description=("Search runs by goal text (case-insensitive partial match)."),
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of runs to return (1-100).",
    )
    cursor: Optional[str] = Field(
        default=None,
        description=(
            "Pagination cursor from a previous response to get the next page."
        ),
    )
    created_after: Optional[str] = Field(
        default=None,
        description=("Only return runs created after this ISO 8601 timestamp."),
    )
    created_before: Optional[str] = Field(
        default=None,
        description=("Only return runs created before this ISO 8601 timestamp."),
    )
    sort_direction: Optional[Literal["asc", "desc"]] = Field(
        default=None,
        description=('Sort order by creation date: "asc" or "desc" (default: desc).'),
    )


class TinyfishSearchInput(BaseModel):
    """Input schema for searching the web."""

    query: str = Field(..., description="Search query.")
    location: Optional[str] = Field(
        default=None,
        description="Optional location to scope results, such as 'United States'.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional language code, such as 'en'.",
    )


class TinyfishFetchInput(BaseModel):
    """Input schema for fetching clean page content."""

    urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="One to ten URLs to fetch and extract clean content from.",
    )
    format: Literal["markdown", "html", "json"] = Field(
        default="markdown",
        description="Output format for extracted content.",
    )
    links: bool = Field(default=False, description="Whether to include page links.")
    image_links: bool = Field(
        default=False,
        description="Whether to include image links.",
    )


class TinyfishBrowserSessionInput(BaseModel):
    """Input schema for creating a remote browser session."""

    url: Optional[str] = Field(
        default=None,
        description="Optional URL to open when the browser session starts.",
    )
    timeout_seconds: int = Field(
        default=0,
        ge=0,
        description=(
            "Optional inactivity timeout in seconds. "
            "Use 0 to let TinyFish apply the plan default."
        ),
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _format_status(status: Any) -> str:
    """Convert a RunStatus enum (or any value) to a string."""
    if isinstance(status, RunStatus):
        return status.value
    return str(status)


def _format_error(error: Any) -> str:
    """Extract a human-readable message from an error object."""
    if isinstance(error, dict):
        return error.get("message", str(error))
    return str(error)


def _ensure_integration_tag() -> None:
    """Set the default TinyFish integration tag for request attribution."""
    os.environ.setdefault("TF_API_INTEGRATION", _INTEGRATION_NAME)


def _dump_json(value: Any) -> str:
    """Serialize SDK response models to a JSON string."""
    if hasattr(value, "model_dump_json"):
        return str(value.model_dump_json())
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump())
    return json.dumps(value)


# ---------------------------------------------------------------------------
# Base tool
# ---------------------------------------------------------------------------


class _TinyfishBaseTool(BaseTool):
    """Shared configuration and helpers for all Tinyfish tools."""

    api_key: Optional[str] = None
    proxy_country: Optional[str] = None

    env_vars: List[EnvVar] = [
        EnvVar(
            name="TINYFISH_API_KEY",
            description=(
                "TinyFish Web Agent API key. "
                "Get one at https://agent.tinyfish.ai/api-keys"
            ),
            required=True,
        ),
    ]

    # Cached per-instance to avoid re-creating on every call.
    _client: Optional[TinyFish] = None

    def _get_client(self) -> tuple[Optional[TinyFish], Optional[str]]:
        """Return (client, None) or (None, error_string)."""
        if self._client is not None:
            return self._client, None
        _ensure_integration_tag()
        key = self.api_key or os.environ.get("TINYFISH_API_KEY")
        if not key:
            return None, (
                "Error: TINYFISH_API_KEY is not set. "
                "Set it as an environment variable or pass "
                "api_key when creating the tool. "
                "Get your key at "
                "https://agent.tinyfish.ai/api-keys"
            )
        self._client = TinyFish(api_key=key)
        return self._client, None

    def _run_kwargs(self, browser_profile: str) -> dict[str, Any]:
        """Common kwargs for SDK agent calls."""
        try:
            bp = BrowserProfile(browser_profile)
        except ValueError:
            bp = BrowserProfile.LITE
        kwargs: dict[str, Any] = {"browser_profile": bp}
        if self.proxy_country:
            try:
                country = ProxyCountryCode(self.proxy_country)
            except ValueError:
                return {"_error": f"Invalid proxy country: {self.proxy_country!r}"}
            kwargs["proxy_config"] = ProxyConfig(enabled=True, country_code=country)
        return kwargs

    def _safe_call(
        self, fn: Any, *args: Any, **kwargs: Any
    ) -> tuple[Any, Optional[str]]:
        """Call fn and return (result, None) or (None, error).

        Logs the traceback at DEBUG level for diagnostics.
        """
        try:
            return fn(*args, **kwargs), None
        except Exception as exc:
            logger.debug("SDK call failed", exc_info=True)
            return None, f"Error: {exc}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class TinyfishRun(_TinyfishBaseTool):
    """Run a browser automation synchronously and return the
    result.

    Best for quick tasks that complete in under 30 seconds.
    """

    name: str = "Tinyfish Web Agent"
    description: str = (
        "Automate any website using natural language. "
        "Provide a URL and describe what you want to "
        "accomplish — extract data, fill forms, click "
        "buttons, navigate pages, and more. "
        "Waits for completion and returns structured "
        "JSON results."
    )
    args_schema: Type[BaseModel] = TinyfishRunInput

    def _run(
        self,
        url: str,
        goal: str,
        browser_profile: str = "lite",
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        kwargs = self._run_kwargs(browser_profile)
        if "_error" in kwargs:
            return f"Error: {kwargs['_error']}"

        result, err = self._safe_call(
            client.agent.run,
            url=url,
            goal=goal,
            **kwargs,
        )
        if err:
            return err

        if result.status == RunStatus.COMPLETED:
            if result.result is not None:
                return json.dumps(result.result)
            return "Completed with no result data."

        error = getattr(result, "error", None)
        if error:
            return f"Automation failed: {_format_error(error)}"
        return f"Automation ended with status: {_format_status(result.status)}"


class TinyfishRunAsync(_TinyfishBaseTool):
    """Start a browser automation asynchronously and return
    the run ID.

    Use TinyfishGetRun to poll for results.
    Best for long-running tasks.
    """

    name: str = "Tinyfish Web Agent (Async)"
    description: str = (
        "Start a browser automation asynchronously. "
        "Returns a run_id immediately without waiting "
        "for completion. "
        "Use the 'Tinyfish Get Run' tool to check status "
        "and get results."
    )
    args_schema: Type[BaseModel] = TinyfishRunInput

    def _run(
        self,
        url: str,
        goal: str,
        browser_profile: str = "lite",
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        kwargs = self._run_kwargs(browser_profile)
        if "_error" in kwargs:
            return f"Error: {kwargs['_error']}"

        result, err = self._safe_call(
            client.agent.queue,
            url=url,
            goal=goal,
            **kwargs,
        )
        if err:
            return err

        return f"Automation started. run_id: {result.run_id}"


class TinyfishGetRun(_TinyfishBaseTool):
    """Get the status and result of a TinyFish automation
    run."""

    name: str = "Tinyfish Get Run"
    description: str = (
        "Check the status and get results of a TinyFish "
        "automation run by its run_id. Returns status "
        "(PENDING, RUNNING, COMPLETED, FAILED, CANCELLED) "
        "and result data."
    )
    args_schema: Type[BaseModel] = TinyfishGetRunInput

    def _run(self, run_id: str) -> str:
        client, err = self._get_client()
        if err:
            return err

        run, err = self._safe_call(client.runs.get, run_id)
        if err:
            return err

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


class TinyfishListRuns(_TinyfishBaseTool):
    """List recent TinyFish automation runs."""

    name: str = "Tinyfish List Runs"
    description: str = (
        "List recent TinyFish automation runs. "
        "Optionally filter by status (PENDING, RUNNING, "
        "COMPLETED, FAILED, CANCELLED)."
    )
    args_schema: Type[BaseModel] = TinyfishListRunsInput

    def _run(
        self,
        status: Optional[str] = None,
        goal: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        sort_direction: Optional[str] = None,
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        kwargs: dict[str, Any] = {"limit": limit}
        if status:
            kwargs["status"] = RunStatus(status)
        if goal:
            kwargs["goal"] = goal
        if cursor:
            kwargs["cursor"] = cursor
        if created_after:
            kwargs["created_after"] = created_after
        if created_before:
            kwargs["created_before"] = created_before
        if sort_direction:
            kwargs["sort_direction"] = sort_direction

        response, err = self._safe_call(client.runs.list, **kwargs)
        if err:
            return err

        runs = getattr(response, "data", None) or getattr(response, "runs", [])
        if not runs:
            return "No runs found."

        lines = []
        for run in runs:
            rid = getattr(run, "run_id", "?")
            st = _format_status(getattr(run, "status", "?"))
            url = getattr(run, "url", "?")
            lines.append(f"- {rid} | {st} | {url}")

        return f"Found {len(runs)} runs:\n" + "\n".join(lines)


class TinyfishSearch(_TinyfishBaseTool):
    """Search the web using TinyFish."""

    name: str = "Tinyfish Search"
    description: str = (
        "Search the web using TinyFish and return structured search results. "
        "Use this to discover relevant URLs or current web pages before "
        "fetching content or running browser automation."
    )
    args_schema: Type[BaseModel] = TinyfishSearchInput

    def _run(
        self,
        query: str,
        location: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        kwargs: dict[str, Any] = {}
        if location:
            kwargs["location"] = location
        if language:
            kwargs["language"] = language

        response, err = self._safe_call(
            client.search.query,
            query=query,
            **kwargs,
        )
        if err:
            return err
        return _dump_json(response)


class TinyfishFetch(_TinyfishBaseTool):
    """Fetch clean content from one or more URLs using TinyFish."""

    name: str = "Tinyfish Fetch"
    description: str = (
        "Fetch clean readable content from one or more URLs using TinyFish. "
        "Use this when the URL is already known and the agent needs page text, "
        "metadata, links, or image links without controlling a browser."
    )
    args_schema: Type[BaseModel] = TinyfishFetchInput

    def _run(
        self,
        urls: list[str],
        format: Literal["markdown", "html", "json"] = "markdown",
        links: bool = False,
        image_links: bool = False,
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        response, err = self._safe_call(
            client.fetch.get_contents,
            urls=urls,
            format=format,
            links=links,
            image_links=image_links,
        )
        if err:
            return err
        return _dump_json(response)


class TinyfishBrowserSession(_TinyfishBaseTool):
    """Create a TinyFish remote browser session."""

    name: str = "Tinyfish Browser Session"
    description: str = (
        "Create a TinyFish remote browser session and return its session ID, "
        "CDP WebSocket URL, and base URL. Use this for low-level browser "
        "control from external browser automation clients."
    )
    args_schema: Type[BaseModel] = TinyfishBrowserSessionInput

    def _run(
        self,
        url: Optional[str] = None,
        timeout_seconds: int = 0,
    ) -> str:
        client, err = self._get_client()
        if err:
            return err

        response, err = self._safe_call(
            client.browser.sessions.create,
            url=url,
            timeout_seconds=timeout_seconds or None,
        )
        if err:
            return err
        return _dump_json(response)


# Backwards-compatible alias
Tinyfish = TinyfishRun
