"""TinyFish Search tool for CrewAI.

Wraps the TinyFish Search API (``GET https://api.search.tinyfish.ai``), which
returns structured, ranked web results (title, snippet, url) ready for LLM
consumption.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, Type

from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, PrivateAttr

from ._client import TINYFISH_API_KEY_ENV, build_client, ensure_api_key, ensure_sdk_installed
from ._serde import as_list, attr, supported_kwargs


class TinyFishSearchToolInput(BaseModel):
    """Input schema for TinyFishSearchTool."""

    query: str = Field(
        ...,
        description=(
            "Search query string. Supports operators, e.g. "
            "'python tutorial site:docs.python.org' or 'recipes -site:youtube.com'."
        ),
    )
    location: Optional[str] = Field(
        None,
        description=(
            "Country code for geo-targeted results (e.g. 'US', 'GB', 'FR'). Defaults to US."
        ),
    )
    language: Optional[str] = Field(
        None,
        description="Language code for result language (e.g. 'en', 'fr', 'de'). Defaults to en.",
    )
    page: Optional[int] = Field(
        None,
        ge=0,
        le=10,
        description="Zero-indexed result page for pagination (0-10).",
    )
    max_results: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of results to return to the agent.",
    )


class TinyFishSearchTool(BaseTool):
    """Run a web search via TinyFish and return structured ranked results."""

    name: str = "TinyFish Web Search"
    description: str = (
        "Search the web with TinyFish and get back structured, ranked results "
        "(title, url, snippet, source). Use this when you need to discover URLs or "
        "get current information for a query."
    )
    args_schema: Type[BaseModel] = TinyFishSearchToolInput
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
        query: str,
        location: Optional[str] = None,
        language: Optional[str] = None,
        page: Optional[int] = None,
        max_results: int = 10,
        **_: Any,
    ) -> str:
        params: dict[str, Any] = {"query": query}
        if location is not None:
            params["location"] = location
        if language is not None:
            params["language"] = language
        if page is not None:
            params["page"] = page

        client = self._get_client()
        try:
            response = client.search.query(**supported_kwargs(client.search.query, params))
        except Exception as exc:  # noqa: BLE001 - surface a clear message to the agent
            return f"TinyFish Search failed: {exc}"

        results = as_list(attr(response, "results"))
        trimmed = []
        for item in results[:max_results]:
            trimmed.append(
                {
                    "position": attr(item, "position"),
                    "title": attr(item, "title"),
                    "url": attr(item, "url"),
                    "snippet": attr(item, "snippet"),
                    "site_name": attr(item, "site_name"),
                }
            )

        return json.dumps(
            {
                "query": query,
                "total_results": attr(response, "total_results"),
                "results": trimmed,
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)
