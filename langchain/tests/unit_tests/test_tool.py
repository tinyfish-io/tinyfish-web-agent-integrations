"""Unit tests for TinyFishWebAutomation tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from langchain_tinyfish import (
    TinyFishAPIWrapper,
    TinyFishBrowserSession,
    TinyFishBrowserSessionInput,
    TinyFishFetch,
    TinyFishFetchInput,
    TinyFishInput,
    TinyFishSearch,
    TinyFishSearchInput,
    TinyFishWebAutomation,
)


def _make_tool(**wrapper_kwargs):
    """Create a tool with an explicit API key wrapper."""
    wrapper_kwargs.setdefault("api_key", SecretStr("sk-test"))
    return TinyFishWebAutomation(api_wrapper=TinyFishAPIWrapper(**wrapper_kwargs))


class TestToolMetadata:
    """Tests for tool class attributes."""

    def test_name(self) -> None:
        assert _make_tool().name == "tinyfish_web_automation"

    def test_description(self) -> None:
        desc = _make_tool().description.lower()
        assert "web automation" in desc
        assert "natural language" in desc

    def test_args_schema(self) -> None:
        assert _make_tool().args_schema is TinyFishInput

    def test_args_schema_fields(self) -> None:
        schema = TinyFishInput.model_json_schema()
        assert "url" in schema["properties"]
        assert "goal" in schema["properties"]
        assert set(schema["required"]) == {"url", "goal"}


class TestToolRunNoWriter:
    """Tests for _run/_arun when no stream writer is available (direct invoke)."""

    def test_run_falls_back_to_sync(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run.return_value = '{"title": "Example"}'

        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=None):
            result = tool._run(url="https://example.com", goal="Extract title")

        mock_wrapper.run.assert_called_once_with(
            url="https://example.com", goal="Extract title"
        )
        assert result == '{"title": "Example"}'

    def test_run_catches_exceptions(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run.side_effect = RuntimeError("API error")

        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=None):
            result = tool._run(url="https://example.com", goal="Do something")

        parsed = json.loads(result)
        assert parsed["error"] is True
        assert parsed["type"] == "RuntimeError"
        assert parsed["message"] == "API error"
        assert "traceback" not in parsed

    @pytest.mark.asyncio
    async def test_arun_falls_back_to_async(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.arun = AsyncMock(return_value='{"data": "async result"}')

        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=None):
            result = await tool._arun(url="https://example.com", goal="Extract data")

        mock_wrapper.arun.assert_called_once_with(
            url="https://example.com", goal="Extract data"
        )
        assert result == '{"data": "async result"}'

    @pytest.mark.asyncio
    async def test_arun_catches_exceptions(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.arun = AsyncMock(side_effect=RuntimeError("async error"))

        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=None):
            result = await tool._arun(url="https://example.com", goal="Do something")

        parsed = json.loads(result)
        assert parsed["error"] is True
        assert parsed["type"] == "RuntimeError"
        assert parsed["message"] == "async error"


def _make_sse_events(
    run_id="run-1",
    streaming_url="https://stream.example.com/run-1",
    progress_messages=None,
    result_json=None,
):
    """Build a standard SSE event sequence for testing."""
    events = [
        {"type": "STARTED", "runId": run_id},
        {"type": "STREAMING_URL", "runId": run_id, "streamingUrl": streaming_url},
    ]
    for msg in progress_messages or ["Working"]:
        events.append({"type": "PROGRESS", "runId": run_id, "purpose": msg})
    events.append(
        {
            "type": "COMPLETE",
            "runId": run_id,
            "status": "COMPLETED",
            "resultJson": result_json or {"ok": True},
        }
    )
    return events


class TestToolRunWithWriter:
    """Tests for _run/_arun when a stream writer IS available (LangGraph)."""

    def test_run_uses_sse_and_emits_events(self) -> None:
        sse_events = _make_sse_events(
            progress_messages=["Visiting the page", "Extracting data"],
            result_json={"items": [1, 2]},
        )

        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run_sse.return_value = iter(sse_events)

        writer = MagicMock()
        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=writer):
            result = tool._run(url="https://example.com", goal="Get items")

        mock_wrapper.run_sse.assert_called_once_with(
            url="https://example.com", goal="Get items"
        )
        mock_wrapper.run.assert_not_called()

        assert writer.call_count == 3  # streaming_url + 2 progress
        calls = [c.args[0] for c in writer.call_args_list]
        assert calls[0] == {
            "type": "streaming_url",
            "url": "https://stream.example.com/run-1",
        }
        assert calls[1] == {"type": "progress", "message": "Visiting the page"}
        assert calls[2] == {"type": "progress", "message": "Extracting data"}

        assert json.loads(result) == {"items": [1, 2]}

    def test_run_sse_error_is_caught(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run_sse.side_effect = ConnectionError("Network error")

        writer = MagicMock()
        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=writer):
            result = tool._run(url="https://example.com", goal="Test")

        parsed = json.loads(result)
        assert parsed["error"] is True
        assert parsed["type"] == "ConnectionError"
        assert parsed["message"] == "Network error"

    def test_run_sse_no_complete_event(self) -> None:
        """SSE stream that ends without a COMPLETE event returns an error."""
        sse_events = [
            {"type": "STARTED", "runId": "run-x"},
            {"type": "PROGRESS", "runId": "run-x", "purpose": "Loading"},
        ]

        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run_sse.return_value = iter(sse_events)

        writer = MagicMock()
        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=writer):
            result = tool._run(url="https://example.com", goal="Test")

        parsed = json.loads(result)
        assert parsed["error"] is True
        assert parsed["type"] == "RuntimeError"
        assert "COMPLETE" in parsed["message"]

    @pytest.mark.asyncio
    async def test_arun_uses_sse_and_emits_events(self) -> None:
        sse_events = _make_sse_events(
            run_id="run-2",
            streaming_url="https://stream.example.com/run-2",
            progress_messages=["Filling form"],
            result_json={"ok": True},
        )

        async def mock_arun_sse(url: str, goal: str):
            for event in sse_events:
                yield event

        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.arun_sse = mock_arun_sse

        writer = MagicMock()
        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=writer):
            result = await tool._arun(url="https://example.com", goal="Fill form")

        mock_wrapper.arun.assert_not_called()

        assert writer.call_count == 2  # streaming_url + 1 progress
        calls = [c.args[0] for c in writer.call_args_list]
        assert calls[0] == {
            "type": "streaming_url",
            "url": "https://stream.example.com/run-2",
        }
        assert calls[1] == {"type": "progress", "message": "Filling form"}

        assert json.loads(result) == {"ok": True}


class TestToolInvoke:
    """Tests for the public invoke interface."""

    def test_invoke_with_dict(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.run.return_value = '{"products": []}'

        tool = TinyFishWebAutomation(api_wrapper=mock_wrapper)
        with patch.object(tool, "_get_stream_writer", return_value=None):
            result = tool.invoke(
                {"url": "https://example.com/shop", "goal": "Get products"}
            )

        mock_wrapper.run.assert_called_once_with(
            url="https://example.com/shop", goal="Get products"
        )
        assert result == '{"products": []}'


class TestToolInstantiation:
    """Tests for different ways to create the tool."""

    def test_with_explicit_wrapper(self) -> None:
        tool = _make_tool(browser_profile="stealth", proxy_enabled=True)
        assert tool.api_wrapper.browser_profile == "stealth"
        assert tool.api_wrapper.proxy_enabled is True


class TestAdditionalTools:
    """Tests for SDK-backed search, fetch, and browser-session tools."""

    def test_search_tool_metadata(self) -> None:
        tool = TinyFishSearch(
            api_wrapper=TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        )

        assert tool.name == "tinyfish_search"
        assert tool.args_schema is TinyFishSearchInput

    def test_search_tool_run(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.search.return_value = '{"results": []}'
        tool = TinyFishSearch(api_wrapper=mock_wrapper)

        result = tool._run(query="tinyfish", location="United States", language="en")

        assert result == '{"results": []}'
        mock_wrapper.search.assert_called_once_with(
            query="tinyfish",
            location="United States",
            language="en",
        )

    @pytest.mark.asyncio
    async def test_search_tool_arun(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.asearch = AsyncMock(return_value='{"results": []}')
        tool = TinyFishSearch(api_wrapper=mock_wrapper)

        result = await tool._arun(query="tinyfish")

        assert result == '{"results": []}'
        mock_wrapper.asearch.assert_called_once_with(
            query="tinyfish",
            location=None,
            language=None,
        )

    def test_fetch_tool_metadata(self) -> None:
        tool = TinyFishFetch(
            api_wrapper=TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        )

        assert tool.name == "tinyfish_fetch"
        assert tool.args_schema is TinyFishFetchInput

    def test_fetch_tool_run(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.fetch.return_value = '{"results": []}'
        tool = TinyFishFetch(api_wrapper=mock_wrapper)

        result = tool._run(
            urls=["https://example.com"],
            format="markdown",
            links=True,
            image_links=False,
        )

        assert result == '{"results": []}'
        mock_wrapper.fetch.assert_called_once_with(
            urls=["https://example.com"],
            format="markdown",
            links=True,
            image_links=False,
        )

    @pytest.mark.asyncio
    async def test_fetch_tool_arun(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.afetch = AsyncMock(return_value='{"results": []}')
        tool = TinyFishFetch(api_wrapper=mock_wrapper)

        result = await tool._arun(urls=["https://example.com"])

        assert result == '{"results": []}'
        mock_wrapper.afetch.assert_called_once_with(
            urls=["https://example.com"],
            format="markdown",
            links=None,
            image_links=None,
        )

    def test_browser_session_tool_metadata(self) -> None:
        tool = TinyFishBrowserSession(
            api_wrapper=TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        )

        assert tool.name == "tinyfish_browser_session"
        assert tool.args_schema is TinyFishBrowserSessionInput

    def test_browser_session_tool_run(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.create_browser_session.return_value = '{"session_id": "tf-1"}'
        tool = TinyFishBrowserSession(api_wrapper=mock_wrapper)

        result = tool._run(url="https://example.com", timeout_seconds=120)

        assert result == '{"session_id": "tf-1"}'
        mock_wrapper.create_browser_session.assert_called_once_with(
            url="https://example.com",
            timeout_seconds=120,
        )

    @pytest.mark.asyncio
    async def test_browser_session_tool_arun(self) -> None:
        mock_wrapper = MagicMock(spec=TinyFishAPIWrapper)
        mock_wrapper.acreate_browser_session = AsyncMock(
            return_value='{"session_id": "tf-1"}'
        )
        tool = TinyFishBrowserSession(api_wrapper=mock_wrapper)

        result = await tool._arun()

        assert result == '{"session_id": "tf-1"}'
        mock_wrapper.acreate_browser_session.assert_called_once_with(
            url=None,
            timeout_seconds=None,
        )

    def test_with_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TINYFISH_API_KEY", "sk-env-test")
        tool = TinyFishWebAutomation()
        assert tool.api_wrapper.api_key.get_secret_value() == "sk-env-test"


class TestGetStreamWriter:
    """Tests for _get_stream_writer helper."""

    def test_returns_none_without_langgraph(self) -> None:
        tool = _make_tool()
        with (
            patch("langchain_tinyfish.tool._stream_writer_checked", False),
            patch("langchain_tinyfish.tool._stream_writer_fn", None),
            patch.dict("sys.modules", {"langgraph": None, "langgraph.config": None}),
        ):
            assert tool._get_stream_writer() is None

    def test_returns_none_when_not_in_context(self) -> None:
        tool = _make_tool()
        assert tool._get_stream_writer() is None
