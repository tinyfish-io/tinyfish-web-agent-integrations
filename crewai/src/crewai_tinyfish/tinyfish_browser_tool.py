"""TinyFish Browser session tool for CrewAI.

Wraps the TinyFish Browser API (``POST https://api.browser.tinyfish.ai``), which
provisions a remote, isolated browser session and returns a CDP WebSocket URL
you can drive directly with Playwright/Puppeteer. Use this when an agent needs
direct, programmatic browser control rather than goal-based automation.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, Type

from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, PrivateAttr

from ._client import TINYFISH_API_KEY_ENV, build_client, ensure_api_key, ensure_sdk_installed
from ._serde import attr, supported_kwargs


class TinyFishBrowserSessionToolInput(BaseModel):
    """Input schema for TinyFishBrowserSessionTool."""

    url: Optional[str] = Field(
        None,
        description="URL to navigate to on startup. Omit to start at about:blank.",
    )
    timeout_seconds: Optional[int] = Field(
        None,
        ge=5,
        le=86_400,
        description="Inactivity timeout in seconds (5-86400). Defaults to your plan maximum.",
    )


class TinyFishBrowserSessionTool(BaseTool):
    """Create a remote browser session and return its CDP connection details."""

    name: str = "TinyFish Browser Session"
    description: str = (
        "Create a remote, isolated browser session via TinyFish and get back a CDP WebSocket "
        "URL (cdp_url), session_id, and base_url. Connect to cdp_url with Playwright/Puppeteer "
        "to drive the browser directly. Use when you need low-level browser control instead of "
        "goal-based "
        "automation. Session creation can take 10-30s."
    )
    args_schema: Type[BaseModel] = TinyFishBrowserSessionToolInput
    package_dependencies: List[str] = ["tinyfish"]
    env_vars: List[EnvVar] = [
        EnvVar(
            name=TINYFISH_API_KEY_ENV,
            description="TinyFish API key from https://agent.tinyfish.ai/api-keys",
            required=True,
        ),
    ]

    _api_key: Optional[str] = PrivateAttr(default=None)
    _client: Any = PrivateAttr(default=None)

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        ensure_sdk_installed()
        ensure_api_key(api_key)
        self._api_key = api_key

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = build_client(self._api_key)
        return self._client

    def _run(
        self,
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        **_: Any,
    ) -> str:
        params: dict[str, Any] = {}
        if url is not None:
            params["url"] = url
        if timeout_seconds is not None:
            params["timeout_seconds"] = timeout_seconds

        client = self._get_client()
        try:
            session = client.browser.sessions.create(
                **supported_kwargs(client.browser.sessions.create, params)
            )
        except Exception as exc:  # noqa: BLE001 - surface a clear message to the agent
            return f"TinyFish Browser session creation failed: {exc}"

        return json.dumps(
            {
                "session_id": attr(session, "session_id"),
                "cdp_url": attr(session, "cdp_url"),
                "base_url": attr(session, "base_url"),
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)
