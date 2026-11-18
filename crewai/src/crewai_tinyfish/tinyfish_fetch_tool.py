"""TinyFish Fetch tool for CrewAI.

Wraps the TinyFish Fetch API (``POST https://api.fetch.tinyfish.ai``), which
renders pages in a real browser (JS-heavy sites included) and returns clean
extracted content. Up to 10 URLs per call, each processed independently.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, List, Optional, Type

from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, PrivateAttr

from ._client import TINYFISH_API_KEY_ENV, build_client, ensure_api_key, ensure_sdk_installed
from ._serde import as_list, attr, supported_kwargs


class TinyFishFetchToolInput(BaseModel):
    """Input schema for TinyFishFetchTool."""

    urls: List[str] = Field(
        ...,
        max_length=10,
        description="1-10 http(s) URLs to fetch and extract. Each URL is processed independently.",
    )
    format: str = Field(
        "markdown",
        description="Output format for extracted text: 'markdown' (default), 'html', or 'json'.",
    )
    links: bool = Field(
        False,
        description="When true, also return all <a href> links found on each page.",
    )
    image_links: bool = Field(
        False,
        description="When true, also return all <img src> URLs found on each page.",
    )
    ttl: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Cache freshness tolerance in seconds. Omit to accept any cached entry, 0 to force a "
            "live fetch, or N to accept entries younger than N seconds."
        ),
    )
    max_chars_per_url: Optional[int] = Field(
        None,
        ge=1,
        description="Optionally truncate each page's extracted text to this many characters.",
    )


class TinyFishFetchTool(BaseTool):
    """Fetch one or more URLs via TinyFish and return clean extracted content."""

    name: str = "TinyFish Web Fetch"
    description: str = (
        "Fetch and extract clean content from one or more URLs (up to 10) using TinyFish. "
        "Renders JavaScript-heavy pages in a real browser and returns markdown/html/json. "
        "Use this when you already have URLs and need their page content."
    )
    args_schema: Type[BaseModel] = TinyFishFetchToolInput
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
        urls: List[str],
        format: str = "markdown",
        links: bool = False,
        image_links: bool = False,
        ttl: Optional[int] = None,
        max_chars_per_url: Optional[int] = None,
        **_: Any,
    ) -> str:
        if not urls:
            return "TinyFish Fetch failed: at least one URL is required."

        params: dict[str, Any] = {"urls": urls, "format": format}
        if links:
            params["links"] = links
        if image_links:
            params["image_links"] = image_links
        if ttl is not None:
            params["ttl"] = ttl

        client = self._get_client()
        try:
            response = client.fetch.get_contents(
                **supported_kwargs(client.fetch.get_contents, params)
            )
        except Exception as exc:  # noqa: BLE001 - surface a clear message to the agent
            return f"TinyFish Fetch failed: {exc}"

        pages = []
        for page in as_list(attr(response, "results")):
            text = attr(page, "text")
            if isinstance(text, str) and max_chars_per_url and len(text) > max_chars_per_url:
                text = text[:max_chars_per_url] + "…[truncated]"
            pages.append(
                {
                    "url": attr(page, "url"),
                    "final_url": attr(page, "final_url"),
                    "title": attr(page, "title"),
                    "description": attr(page, "description"),
                    "language": attr(page, "language"),
                    "format": attr(page, "format"),
                    "text": text,
                    "links": attr(page, "links") if links else None,
                    "image_links": attr(page, "image_links") if image_links else None,
                }
            )

        errors = []
        for err in as_list(attr(response, "errors")):
            errors.append(
                {
                    "url": attr(err, "url"),
                    "error": attr(err, "error"),
                    "status": attr(err, "status"),
                }
            )

        return json.dumps({"results": pages, "errors": errors}, ensure_ascii=False, indent=2)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return await asyncio.to_thread(self._run, *args, **kwargs)
