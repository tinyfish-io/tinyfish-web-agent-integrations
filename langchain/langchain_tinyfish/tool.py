"""TinyFish Web Agent tool for LangChain."""

from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any, Callable, Literal, Optional, Type, cast

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_tinyfish._api_wrapper import TinyFishAPIWrapper

logger = logging.getLogger(__name__)

# Cache the LangGraph import so we don't try/except on every invocation.
_stream_writer_fn: Optional[Callable[[], Any]] = None
_stream_writer_checked = False


def _get_stream_writer_fn() -> Optional[Callable[[], Any]]:
    """Return the ``get_stream_writer`` callable from langgraph, or None."""
    global _stream_writer_fn, _stream_writer_checked
    if not _stream_writer_checked:
        _stream_writer_checked = True
        try:
            from langgraph.config import get_stream_writer

            _stream_writer_fn = get_stream_writer
        except Exception:
            _stream_writer_fn = None
    return _stream_writer_fn


class TinyFishInput(BaseModel):
    """Input schema for the TinyFish Web Agent tool."""

    url: str = Field(description="The URL of the website to automate")
    goal: str = Field(
        description=(
            "Natural language instructions describing what to do on the page. "
            "Be specific: include field names, button labels, "
            "and expected output format."
        )
    )


class TinyFishSearchInput(BaseModel):
    """Input schema for the TinyFish web search tool."""

    query: str = Field(description="The web search query to run")
    location: Optional[str] = Field(
        default=None,
        description="Optional location to scope results, such as 'United States'",
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional language code for results, such as 'en'",
    )


class TinyFishFetchInput(BaseModel):
    """Input schema for the TinyFish content fetch tool."""

    urls: list[str] = Field(
        description="One to ten URLs to fetch and extract clean content from",
    )
    format: Literal["markdown", "html", "json"] = Field(
        default="markdown",
        description="Output format for extracted content",
    )
    links: Optional[bool] = Field(
        default=None,
        description="Whether to include extracted page links",
    )
    image_links: Optional[bool] = Field(
        default=None,
        description="Whether to include extracted image links",
    )


class TinyFishBrowserSessionInput(BaseModel):
    """Input schema for creating a TinyFish remote browser session."""

    url: Optional[str] = Field(
        default=None,
        description="Optional target URL to open when the browser session starts",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Optional inactivity timeout for the browser session",
    )


class TinyFishWebAutomation(BaseTool):
    """AI-powered web automation tool using TinyFish Web Agent.

    Automates any website using natural language instructions. Can navigate
    pages, fill forms, click buttons, extract structured data, and perform
    multi-step workflows.

    Setup:
        Install ``langchain-tinyfish`` and set the ``TINYFISH_API_KEY``
        environment variable.

        .. code-block:: bash

            pip install langchain-tinyfish
            export TINYFISH_API_KEY="sk-mino-..."

    Key init args:
        api_wrapper: TinyFishAPIWrapper instance with configuration options.

    Instantiate:
        .. code-block:: python

            from langchain_tinyfish import TinyFishWebAutomation

            tool = TinyFishWebAutomation()

    Invoke directly:
        .. code-block:: python

            result = tool.invoke({
                "url": "https://example.com/products",
                "goal": "Extract all product names and prices as JSON",
            })

    Use with an agent:
        .. code-block:: python

            from langchain_openai import ChatOpenAI
            from langgraph.prebuilt import create_react_agent

            llm = ChatOpenAI(model="gpt-4o")
            agent = create_react_agent(llm, [TinyFishWebAutomation()])

    With stealth mode and proxy:
        .. code-block:: python

            from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

            tool = TinyFishWebAutomation(
                api_wrapper=TinyFishAPIWrapper(
                    browser_profile="stealth",
                    proxy_enabled=True,
                    proxy_country_code="US",
                )
            )
    """

    name: str = "tinyfish_web_automation"
    description: str = (
        "An AI-powered web automation tool that controls a real browser using "
        "natural language. Use this to navigate websites, extract structured data, "
        "fill forms, click buttons, and perform multi-step workflows on any website. "
        "Input requires a URL and a goal describing what to do on the page. "
        "Returns structured JSON results extracted from the page."
    )
    args_schema: Type[BaseModel] = TinyFishInput
    api_wrapper: TinyFishAPIWrapper = Field(default_factory=TinyFishAPIWrapper)

    def _get_stream_writer(self) -> Optional[Callable[..., Any]]:
        """Try to get LangGraph's stream writer. Returns None outside LangGraph."""
        fn = _get_stream_writer_fn()
        if fn is None:
            return None
        try:
            writer = fn()
            return cast(Callable[..., Any], writer)
        except Exception:
            return None

    @staticmethod
    def _format_error(e: Exception) -> str:
        """Format an exception as a structured JSON string for agent consumption."""
        payload: dict[str, Any] = {
            "error": True,
            "type": type(e).__name__,
            "message": str(e),
        }
        if os.getenv("TINYFISH_DEBUG", "").lower() in ("1", "true"):
            payload["traceback"] = traceback.format_exc()
        return json.dumps(payload)

    @staticmethod
    def _dispatch_event(
        writer: Callable[..., Any], event: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Dispatch a single SSE event to the writer. Returns the event if COMPLETE."""
        etype = event.get("type")
        if etype == "STREAMING_URL":
            writer({"type": "streaming_url", "url": event.get("streamingUrl", "")})
        elif etype == "PROGRESS":
            writer({"type": "progress", "message": event.get("purpose", "")})
        elif etype == "COMPLETE":
            return event
        return None

    def _run(
        self,
        url: str,
        goal: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Run the tool synchronously.

        When invoked inside a LangGraph execution context, uses the SSE
        streaming endpoint and emits progress events via ``get_stream_writer()``.
        Falls back to the simple blocking run when no stream writer is available.
        """
        try:
            writer = self._get_stream_writer()
            if writer is None:
                return self.api_wrapper.run(url=url, goal=goal)

            result = None
            for event in self.api_wrapper.run_sse(url=url, goal=goal):
                complete = self._dispatch_event(writer, event)
                if complete is not None:
                    result = complete
                    break

            if result is None:
                raise RuntimeError("SSE stream ended without a COMPLETE event")
            return TinyFishAPIWrapper.handle_complete_event(result)
        except Exception as e:
            logger.exception("TinyFish tool error during _run")
            return self._format_error(e)

    async def _arun(
        self,
        url: str,
        goal: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Run the tool asynchronously.

        When invoked inside a LangGraph execution context, uses the async SSE
        streaming endpoint and emits progress events via ``get_stream_writer()``.
        Falls back to async queue+poll when no stream writer is available.
        """
        try:
            writer = self._get_stream_writer()
            if writer is None:
                return await self.api_wrapper.arun(url=url, goal=goal)

            result = None
            async for event in self.api_wrapper.arun_sse(url=url, goal=goal):
                complete = self._dispatch_event(writer, event)
                if complete is not None:
                    result = complete
                    break

            if result is None:
                raise RuntimeError("SSE stream ended without a COMPLETE event")
            return TinyFishAPIWrapper.handle_complete_event(result)
        except Exception as e:
            logger.exception("TinyFish tool error during _arun")
            return self._format_error(e)


class TinyFishSearch(BaseTool):
    """LangChain tool for TinyFish web search."""

    name: str = "tinyfish_search"
    description: str = (
        "Search the web using TinyFish and return structured search results. "
        "Use this when an agent needs to discover relevant URLs or current "
        "web pages before fetching content or running browser automation."
    )
    args_schema: Type[BaseModel] = TinyFishSearchInput
    api_wrapper: TinyFishAPIWrapper = Field(default_factory=TinyFishAPIWrapper)

    def _run(
        self,
        query: str,
        location: Optional[str] = None,
        language: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            return self.api_wrapper.search(
                query=query,
                location=location,
                language=language,
            )
        except Exception as e:
            logger.exception("TinyFish search tool error during _run")
            return TinyFishWebAutomation._format_error(e)

    async def _arun(
        self,
        query: str,
        location: Optional[str] = None,
        language: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        try:
            return await self.api_wrapper.asearch(
                query=query,
                location=location,
                language=language,
            )
        except Exception as e:
            logger.exception("TinyFish search tool error during _arun")
            return TinyFishWebAutomation._format_error(e)


class TinyFishFetch(BaseTool):
    """LangChain tool for TinyFish content fetch."""

    name: str = "tinyfish_fetch"
    description: str = (
        "Fetch clean content from one or more URLs using TinyFish. Use this "
        "when an agent already knows the URL and needs readable page content, "
        "metadata, links, or image links without controlling a browser."
    )
    args_schema: Type[BaseModel] = TinyFishFetchInput
    api_wrapper: TinyFishAPIWrapper = Field(default_factory=TinyFishAPIWrapper)

    def _run(
        self,
        urls: list[str],
        format: Literal["markdown", "html", "json"] = "markdown",
        links: Optional[bool] = None,
        image_links: Optional[bool] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            if not 1 <= len(urls) <= 10:
                raise ValueError("urls must contain between 1 and 10 items")
            return self.api_wrapper.fetch(
                urls=urls,
                format=format,
                links=links,
                image_links=image_links,
            )
        except Exception as e:
            logger.exception("TinyFish fetch tool error during _run")
            return TinyFishWebAutomation._format_error(e)

    async def _arun(
        self,
        urls: list[str],
        format: Literal["markdown", "html", "json"] = "markdown",
        links: Optional[bool] = None,
        image_links: Optional[bool] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        try:
            if not 1 <= len(urls) <= 10:
                raise ValueError("urls must contain between 1 and 10 items")
            return await self.api_wrapper.afetch(
                urls=urls,
                format=format,
                links=links,
                image_links=image_links,
            )
        except Exception as e:
            logger.exception("TinyFish fetch tool error during _arun")
            return TinyFishWebAutomation._format_error(e)


class TinyFishBrowserSession(BaseTool):
    """LangChain tool for creating TinyFish remote browser sessions."""

    name: str = "tinyfish_browser_session"
    description: str = (
        "Create a TinyFish remote browser session and return its session ID, "
        "CDP WebSocket URL, and base URL. Use this for low-level browser "
        "control from external browser automation clients."
    )
    args_schema: Type[BaseModel] = TinyFishBrowserSessionInput
    api_wrapper: TinyFishAPIWrapper = Field(default_factory=TinyFishAPIWrapper)

    def _run(
        self,
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            return self.api_wrapper.create_browser_session(
                url=url,
                timeout_seconds=timeout_seconds,
            )
        except Exception as e:
            logger.exception("TinyFish browser session tool error during _run")
            return TinyFishWebAutomation._format_error(e)

    async def _arun(
        self,
        url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        try:
            return await self.api_wrapper.acreate_browser_session(
                url=url,
                timeout_seconds=timeout_seconds,
            )
        except Exception as e:
            logger.exception("TinyFish browser session tool error during _arun")
            return TinyFishWebAutomation._format_error(e)
