"""Wrapper around the TinyFish Web Agent SDK."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, Generator, Literal, Optional, cast

from langchain_core.utils import secret_from_env
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from tinyfish import (
    AsyncTinyFish,
    BrowserProfile,
    EventType,
    ProxyConfig,
    ProxyCountryCode,
    RunStatus,
    TinyFish,
)

_NO_RESULT = {"status": "completed", "message": "No result data"}
_INTEGRATION_NAME = "langchain"
FetchFormat = Literal["markdown", "html", "json"]


class TinyFishAPIWrapper(BaseModel):
    """Wrapper around TinyFish Web Agent SDK.

    Provides sync and async methods to run web automations via
    the TinyFish Python SDK.

    Setup:
        Set the ``TINYFISH_API_KEY`` environment variable, or pass ``api_key``
        directly.

        .. code-block:: bash

            export TINYFISH_API_KEY="sk-mino-..."

    Example:
        .. code-block:: python

            from langchain_tinyfish import TinyFishAPIWrapper

            wrapper = TinyFishAPIWrapper()
            result = wrapper.run(
                url="https://example.com",
                goal="Extract the page title",
            )
    """

    api_key: SecretStr = Field(
        default_factory=secret_from_env(["TINYFISH_API_KEY"]),
    )
    browser_profile: str = Field(
        default="lite",
        description="Browser profile: 'lite' (fast) or 'stealth' (anti-detection)",
    )
    proxy_enabled: bool = Field(default=False)
    proxy_country_code: str = Field(
        default="US",
        description="Proxy country code: US, GB, CA, DE, FR, JP, AU",
    )
    timeout: int = Field(
        default=300,
        ge=1,
        description="Request timeout in seconds",
    )
    poll_interval: float = Field(
        default=2.0,
        gt=0,
        description="Seconds between polls when using async run",
    )

    model_config = ConfigDict(extra="forbid")

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _ensure_integration_tag() -> None:
        """Set the default TinyFish integration tag for request attribution."""
        os.environ.setdefault("TF_API_INTEGRATION", _INTEGRATION_NAME)

    def _get_browser_profile(self) -> BrowserProfile:
        """Convert string browser profile to SDK enum."""
        try:
            return BrowserProfile(self.browser_profile)
        except ValueError:
            return cast(BrowserProfile, BrowserProfile.LITE)

    def _get_proxy_config(self) -> Optional[ProxyConfig]:
        """Build SDK proxy config if enabled."""
        if not self.proxy_enabled:
            return None
        return ProxyConfig(
            enabled=True,
            country_code=ProxyCountryCode(self.proxy_country_code),
        )

    def _run_kwargs(self) -> Dict[str, Any]:
        """Common kwargs for SDK agent.run/stream/queue calls."""
        kwargs: Dict[str, Any] = {
            "browser_profile": self._get_browser_profile(),
        }
        proxy = self._get_proxy_config()
        if proxy is not None:
            kwargs["proxy_config"] = proxy
        return kwargs

    def _make_client(self) -> TinyFish:
        """Create a sync TinyFish SDK client."""
        self._ensure_integration_tag()
        return TinyFish(api_key=self.api_key.get_secret_value())

    def _make_async_client(self) -> AsyncTinyFish:
        """Create an async TinyFish SDK client."""
        self._ensure_integration_tag()
        return AsyncTinyFish(api_key=self.api_key.get_secret_value())

    @staticmethod
    def _normalize_event(event: Any) -> Dict[str, Any]:
        """Convert an SDK stream event to a normalized dict."""
        etype = event.type
        d: Dict[str, Any] = {
            "type": etype.value if isinstance(etype, EventType) else str(etype),
        }
        status = getattr(event, "status", None)
        if status is not None:
            d["status"] = status.value if isinstance(status, RunStatus) else str(status)
        for sdk_attr, key in [
            ("streaming_url", "streamingUrl"),
            ("purpose", "purpose"),
            ("result_json", "resultJson"),
            ("run_id", "runId"),
        ]:
            val = getattr(event, sdk_attr, None)
            if val is not None:
                d[key] = val
        return d

    @staticmethod
    def _handle_run_result(run: Any) -> str:
        """Process an SDK run/result object and return a JSON string.

        Handles both RunResult (from agent.run) and Run (from runs.get)
        which share the same status/result/error pattern.
        """
        status = getattr(run, "status", None)
        if status == RunStatus.COMPLETED:
            result = getattr(run, "result", None)
            if result is not None:
                return json.dumps(result)
            return json.dumps(_NO_RESULT)
        elif status == RunStatus.FAILED:
            error = getattr(run, "error", None)
            if error is not None:
                message = (
                    error.get("message", str(error))
                    if isinstance(error, dict)
                    else str(error)
                )
            else:
                message = "Unknown error"
            raise RuntimeError(f"TinyFish automation failed: {message}")
        elif status == RunStatus.CANCELLED:
            raise RuntimeError("TinyFish automation was cancelled")
        else:
            return json.dumps({"status": str(status), "run": str(run)})

    @staticmethod
    def _dump_json(value: Any) -> str:
        """Serialize SDK response models to a JSON string."""
        if hasattr(value, "model_dump_json"):
            return str(value.model_dump_json())
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump())
        return json.dumps(value)

    @staticmethod
    def handle_complete_event(event: Dict[str, Any]) -> str:
        """Extract result from a COMPLETE SSE event dict.

        Used by the tool layer to process the final streaming event.
        """
        status = event.get("status")
        if status == "COMPLETED":
            data = event.get("resultJson")
            if data is not None:
                return json.dumps(data)
            return json.dumps(_NO_RESULT)
        elif status == "FAILED":
            raise RuntimeError(f"TinyFish automation failed: {event}")
        elif status == "CANCELLED":
            raise RuntimeError("TinyFish automation was cancelled")
        return json.dumps(event)

    # ── sync: run ────────────────────────────────────────────────────

    def run(self, url: str, goal: str) -> str:
        """Run a web automation task synchronously.

        Args:
            url: The target URL to automate.
            goal: Natural language description of what to do.

        Returns:
            JSON string with the automation result.

        Raises:
            RuntimeError: If the automation fails.
        """
        client = self._make_client()
        result = client.agent.run(url=url, goal=goal, **self._run_kwargs())
        return self._handle_run_result(result)

    # ── sync: SSE streaming ──────────────────────────────────────────

    def run_sse(self, url: str, goal: str) -> Generator[Dict[str, Any], None, None]:
        """Run a web automation task with SSE streaming.

        Yields each SSE event as a dict with ``type``, and type-specific
        fields like ``streamingUrl``, ``purpose``, ``status``, ``resultJson``.

        Args:
            url: The target URL to automate.
            goal: Natural language description of what to do.

        Yields:
            Dict with the parsed event data.
        """
        client = self._make_client()
        with client.agent.stream(url=url, goal=goal, **self._run_kwargs()) as stream:
            for event in stream:
                yield self._normalize_event(event)

    # ── async: run ───────────────────────────────────────────────────

    async def arun(self, url: str, goal: str) -> str:
        """Run a web automation task asynchronously using queue + poll.

        Args:
            url: The target URL to automate.
            goal: Natural language description of what to do.

        Returns:
            JSON string with the automation result.

        Raises:
            RuntimeError: If the automation fails or is cancelled.
        """
        client = self._make_async_client()
        queue_result = await client.agent.queue(
            url=url, goal=goal, **self._run_kwargs()
        )

        deadline = time.monotonic() + self.timeout
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Polling timed out after {self.timeout}s "
                    f"for run {queue_result.run_id}"
                )
            await asyncio.sleep(self.poll_interval)
            run_id = queue_result.run_id
            if run_id is None:
                raise RuntimeError("TinyFish async run did not return a run ID")
            run = await client.runs.get(run_id)
            status = getattr(run, "status", None)
            if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                return self._handle_run_result(run)

    # ── async: SSE streaming ─────────────────────────────────────────

    async def arun_sse(
        self, url: str, goal: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a web automation task with async SSE streaming.

        Yields each event as a dict (same format as ``run_sse``).

        Args:
            url: The target URL to automate.
            goal: Natural language description of what to do.

        Yields:
            Dict with the parsed event data.
        """
        client = self._make_async_client()
        async with client.agent.stream(
            url=url, goal=goal, **self._run_kwargs()
        ) as stream:
            async for event in stream:
                yield self._normalize_event(event)

    # ── run management ───────────────────────────────────────────────

    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get details of a specific automation run.

        Args:
            run_id: The run ID to look up.

        Returns:
            Dict with run details including status, result, error.
        """
        client = self._make_async_client()
        run = await client.runs.get(run_id)
        st = run.status
        return {
            "run_id": getattr(run, "run_id", run_id),
            "status": st.value if isinstance(st, RunStatus) else str(st),
            "result": getattr(run, "result", None),
            "error": getattr(run, "error", None),
            "streaming_url": getattr(run, "streaming_url", None),
        }

    async def list_runs(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List automation runs with optional filtering.

        Args:
            status: Filter by status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED).
            limit: Results per page, 1-100 (default: 20).

        Returns:
            Dict with run data.
        """
        client = self._make_async_client()
        kwargs: Dict[str, Any] = {}
        if limit is not None:
            kwargs["limit"] = limit
        if status is not None:
            kwargs["status"] = RunStatus(status)
        response = await client.runs.list(**kwargs)
        runs = getattr(response, "runs", [])
        return {
            "data": [
                {
                    "run_id": getattr(r, "run_id", None),
                    "status": (
                        r.status.value
                        if isinstance(r.status, RunStatus)
                        else str(r.status)
                    ),
                    "url": getattr(r, "url", None),
                    "goal": getattr(r, "goal", None),
                }
                for r in runs
            ]
        }

    # -- web search --------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        location: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """Search the web using the TinyFish SDK."""
        client = self._make_client()
        response = client.search.query(
            query=query,
            location=location,
            language=language,
        )
        return self._dump_json(response)

    async def asearch(
        self,
        query: str,
        *,
        location: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """Async search the web using the TinyFish SDK."""
        client = self._make_async_client()
        response = await client.search.query(
            query=query,
            location=location,
            language=language,
        )
        return self._dump_json(response)

    # -- content fetch -----------------------------------------------------

    def fetch(
        self,
        urls: list[str],
        *,
        format: FetchFormat = "markdown",
        links: Optional[bool] = None,
        image_links: Optional[bool] = None,
    ) -> str:
        """Fetch clean page content using the TinyFish SDK."""
        client = self._make_client()
        response = client.fetch.get_contents(
            urls=urls,
            format=format,
            links=links,
            image_links=image_links,
        )
        return self._dump_json(response)

    async def afetch(
        self,
        urls: list[str],
        *,
        format: FetchFormat = "markdown",
        links: Optional[bool] = None,
        image_links: Optional[bool] = None,
    ) -> str:
        """Async fetch clean page content using the TinyFish SDK."""
        client = self._make_async_client()
        response = await client.fetch.get_contents(
            urls=urls,
            format=format,
            links=links,
            image_links=image_links,
        )
        return self._dump_json(response)

    # -- browser sessions -------------------------------------------------

    def create_browser_session(
        self,
        *,
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """Create a remote browser session using the TinyFish SDK."""
        client = self._make_client()
        response = client.browser.sessions.create(
            url=url,
            timeout_seconds=timeout_seconds,
        )
        return self._dump_json(response)

    async def acreate_browser_session(
        self,
        *,
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """Async create a remote browser session using the TinyFish SDK."""
        client = self._make_async_client()
        response = await client.browser.sessions.create(
            url=url,
            timeout_seconds=timeout_seconds,
        )
        return self._dump_json(response)
