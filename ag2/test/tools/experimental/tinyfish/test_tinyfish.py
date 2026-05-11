# Copyright (c) 2023 - 2025, AG2ai, Inc., AG2ai open-source projects maintainers and core contributors
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _schema_parameters(tool):
    """Return the parameters block from either AG2 schema shape."""
    schema = tool.function_schema
    if "function" in schema:
        return schema["function"]["parameters"]
    return schema["parameters"]


@pytest.fixture
def mock_tinyfish():
    """Patch TinyFish client and related imports."""
    with (
        patch("autogen.tools.experimental.tinyfish.tinyfish.TinyFish") as mock_cls,
        patch("autogen.tools.experimental.tinyfish.tinyfish.RunStatus") as mock_status,
        patch("autogen.tools.experimental.tinyfish.tinyfish.BrowserProfile") as mock_bp,
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_bp.return_value = "lite"
        yield {
            "cls": mock_cls,
            "client": mock_client,
            "RunStatus": mock_status,
        }


class TestTinyFishToolkitInit:
    """Test TinyFishToolkit initialization."""

    def test_creates_seven_tools(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        assert len(toolkit.tools) == 7

    def test_tool_names(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        names = [t.name for t in toolkit.tools]
        assert "tinyfish_web_agent" in names
        assert "tinyfish_web_agent_async" in names
        assert "tinyfish_get_run" in names
        assert "tinyfish_list_runs" in names
        assert "tinyfish_search" in names
        assert "tinyfish_fetch" in names
        assert "tinyfish_create_browser_session" in names

    def test_custom_api_key(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        TinyFishToolkit(api_key="sk-test-key")
        mock_tinyfish["cls"].assert_called_once_with(api_key="sk-test-key")

    def test_default_api_key_from_env(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        TinyFishToolkit()
        mock_tinyfish["cls"].assert_called_once_with()

    def test_sets_default_integration_tag(self, mock_tinyfish, monkeypatch):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        monkeypatch.delenv("TF_API_INTEGRATION", raising=False)

        TinyFishToolkit()

        assert os.environ["TF_API_INTEGRATION"] == "ag2"
        mock_tinyfish["cls"].assert_called_once_with()

    def test_preserves_existing_integration_tag(self, mock_tinyfish, monkeypatch):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        monkeypatch.setenv("TF_API_INTEGRATION", "custom-tag")

        TinyFishToolkit()

        assert os.environ["TF_API_INTEGRATION"] == "custom-tag"
        mock_tinyfish["cls"].assert_called_once_with()

    def test_tools_are_callable(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        for tool in toolkit.tools:
            assert callable(tool.func)

    def test_invalid_browser_profile_raises(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["cls"].side_effect = None
        with patch(
            "autogen.tools.experimental.tinyfish.tinyfish.BrowserProfile",
            side_effect=ValueError("bad"),
        ):
            with pytest.raises(ValueError, match="Invalid browser_profile"):
                TinyFishToolkit(browser_profile="invalid_profile")

    def test_invalid_proxy_country_raises(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        with patch(
            "autogen.tools.experimental.tinyfish.tinyfish.ProxyCountryCode",
            side_effect=ValueError("bad"),
        ):
            with pytest.raises(ValueError, match="Invalid proxy_country"):
                TinyFishToolkit(proxy_country="ZZZ")


class TestTinyFishToolSchemas:
    """Test tool function schemas."""

    def test_run_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        run_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent")
        params = _schema_parameters(run_tool)
        assert "url" in params["properties"]
        assert "goal" in params["properties"]
        assert "url" in params["required"]
        assert "goal" in params["required"]

    def test_async_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        async_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent_async")
        params = _schema_parameters(async_tool)
        assert "url" in params["properties"]
        assert "goal" in params["properties"]

    def test_get_run_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        get_tool = next(t for t in toolkit.tools if t.name == "tinyfish_get_run")
        params = _schema_parameters(get_tool)
        assert "run_id" in params["properties"]
        assert "run_id" in params["required"]

    def test_list_runs_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        list_tool = next(t for t in toolkit.tools if t.name == "tinyfish_list_runs")
        params = _schema_parameters(list_tool)
        assert "status" in params["properties"]
        assert "limit" in params["properties"]

    def test_search_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        search_tool = next(t for t in toolkit.tools if t.name == "tinyfish_search")
        params = _schema_parameters(search_tool)
        assert "query" in params["properties"]
        assert "location" in params["properties"]
        assert "language" in params["properties"]
        assert "query" in params["required"]

    def test_fetch_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        fetch_tool = next(t for t in toolkit.tools if t.name == "tinyfish_fetch")
        params = _schema_parameters(fetch_tool)
        assert "urls" in params["properties"]
        assert "format" in params["properties"]
        assert "links" in params["properties"]
        assert "image_links" in params["properties"]
        assert "urls" in params["required"]

    def test_create_browser_session_tool_schema(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        browser_tool = next(t for t in toolkit.tools if t.name == "tinyfish_create_browser_session")
        params = _schema_parameters(browser_tool)
        assert "url" in params["properties"]
        assert "timeout_seconds" in params["properties"]


class TestRunTool:
    """Test the sync run tool execution."""

    def test_successful_run(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_result = MagicMock()
        mock_result.status = mock_tinyfish["RunStatus"].COMPLETED
        mock_result.result = {"title": "Example", "price": "$9.99"}
        mock_tinyfish["client"].agent.run.return_value = mock_result

        toolkit = TinyFishToolkit()
        run_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent")
        output = run_tool.func(url="https://example.com", goal="Extract title and price")

        parsed = json.loads(output)
        assert parsed["title"] == "Example"
        assert parsed["price"] == "$9.99"

    def test_failed_run(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_result = MagicMock()
        mock_result.status = MagicMock()  # Not COMPLETED
        mock_result.error = "Page not found"
        mock_tinyfish["client"].agent.run.return_value = mock_result

        toolkit = TinyFishToolkit()
        run_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent")
        output = run_tool.func(url="https://example.com", goal="Extract data")

        assert "failed" in output.lower()

    def test_exception_returns_error_string(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["client"].agent.run.side_effect = ConnectionError("Network error")

        toolkit = TinyFishToolkit()
        run_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent")
        output = run_tool.func(url="https://example.com", goal="Extract data")

        assert "Error" in output
        assert "Network error" in output


class TestQueueTool:
    """Test the async queue tool execution."""

    def test_successful_queue(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_result = MagicMock()
        mock_result.run_id = "run_abc123"
        mock_tinyfish["client"].agent.queue.return_value = mock_result

        toolkit = TinyFishToolkit()
        queue_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent_async")
        output = queue_tool.func(url="https://example.com", goal="Extract data")

        assert "run_abc123" in output
        assert "tinyfish_get_run" in output

    def test_queue_exception(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["client"].agent.queue.side_effect = Exception("Auth failed")

        toolkit = TinyFishToolkit()
        queue_tool = next(t for t in toolkit.tools if t.name == "tinyfish_web_agent_async")
        output = queue_tool.func(url="https://example.com", goal="Extract data")

        assert "Error" in output


class TestGetRunTool:
    """Test the get run tool execution."""

    def test_completed_run(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_run = MagicMock()
        mock_run.status = "COMPLETED"
        mock_run.result = {"data": "test"}
        mock_run.error = None
        mock_tinyfish["client"].runs.get.return_value = mock_run

        toolkit = TinyFishToolkit()
        get_tool = next(t for t in toolkit.tools if t.name == "tinyfish_get_run")
        output = get_tool.func(run_id="run_abc123")

        assert "COMPLETED" in output
        assert "test" in output

    def test_pending_run(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_run = MagicMock()
        mock_run.status = "PENDING"
        mock_run.result = None
        mock_run.error = None
        del mock_run.streaming_url
        del mock_run.streamingUrl
        mock_tinyfish["client"].runs.get.return_value = mock_run

        toolkit = TinyFishToolkit()
        get_tool = next(t for t in toolkit.tools if t.name == "tinyfish_get_run")
        output = get_tool.func(run_id="run_abc123")

        assert "PENDING" in output


class TestListRunsTool:
    """Test the list runs tool execution."""

    def test_list_with_results(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_run = MagicMock()
        mock_run.run_id = "run_abc123"
        mock_run.status = "COMPLETED"
        mock_run.url = "https://example.com"
        mock_run.goal = "Extract product data"

        mock_response = MagicMock()
        mock_response.runs = [mock_run]
        mock_tinyfish["client"].runs.list.return_value = mock_response

        toolkit = TinyFishToolkit()
        list_tool = next(t for t in toolkit.tools if t.name == "tinyfish_list_runs")
        output = list_tool.func()

        assert "run_abc123" in output
        assert "COMPLETED" in output

    def test_list_empty(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_response = MagicMock()
        mock_response.runs = []
        mock_tinyfish["client"].runs.list.return_value = mock_response

        toolkit = TinyFishToolkit()
        list_tool = next(t for t in toolkit.tools if t.name == "tinyfish_list_runs")
        output = list_tool.func()

        assert "No runs found" in output


class TestSearchTool:
    """Test the search tool execution."""

    def test_successful_search(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_response = SimpleNamespace(
            model_dump=lambda mode="json": {
                "query": "tinyfish docs",
                "total_results": 1,
                "results": [{"title": "TinyFish Docs", "url": "https://docs.tinyfish.ai"}],
            }
        )
        mock_tinyfish["client"].search.query.return_value = mock_response

        toolkit = TinyFishToolkit()
        search_tool = next(t for t in toolkit.tools if t.name == "tinyfish_search")
        output = search_tool.func(query="tinyfish docs", location="United States", language="en")

        parsed = json.loads(output)
        assert parsed["query"] == "tinyfish docs"
        assert parsed["results"][0]["title"] == "TinyFish Docs"
        mock_tinyfish["client"].search.query.assert_called_once_with(
            "tinyfish docs",
            location="United States",
            language="en",
        )

    def test_search_exception(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["client"].search.query.side_effect = Exception("Search failed")

        toolkit = TinyFishToolkit()
        search_tool = next(t for t in toolkit.tools if t.name == "tinyfish_search")
        output = search_tool.func(query="tinyfish docs")

        assert "Error" in output
        assert "Search failed" in output


class TestFetchTool:
    """Test the fetch tool execution."""

    def test_successful_fetch(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_response = SimpleNamespace(
            model_dump=lambda mode="json": {
                "results": [{"url": "https://docs.tinyfish.ai", "content": "# TinyFish"}],
                "errors": [],
            }
        )
        mock_tinyfish["client"].fetch.get_contents.return_value = mock_response

        toolkit = TinyFishToolkit()
        fetch_tool = next(t for t in toolkit.tools if t.name == "tinyfish_fetch")
        output = fetch_tool.func(
            urls=["https://docs.tinyfish.ai"],
            format="markdown",
            links=True,
            image_links=False,
        )

        parsed = json.loads(output)
        assert parsed["results"][0]["content"] == "# TinyFish"
        mock_tinyfish["client"].fetch.get_contents.assert_called_once_with(
            ["https://docs.tinyfish.ai"],
            format="markdown",
            links=True,
            image_links=False,
        )

    def test_invalid_fetch_format(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        toolkit = TinyFishToolkit()
        fetch_tool = next(t for t in toolkit.tools if t.name == "tinyfish_fetch")
        output = fetch_tool.func(urls=["https://docs.tinyfish.ai"], format="xml")

        assert "Invalid format" in output
        mock_tinyfish["client"].fetch.get_contents.assert_not_called()

    def test_fetch_exception(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["client"].fetch.get_contents.side_effect = Exception("Fetch failed")

        toolkit = TinyFishToolkit()
        fetch_tool = next(t for t in toolkit.tools if t.name == "tinyfish_fetch")
        output = fetch_tool.func(urls=["https://docs.tinyfish.ai"])

        assert "Error" in output
        assert "Fetch failed" in output


class TestCreateBrowserSessionTool:
    """Test the browser session tool execution."""

    def test_successful_create_browser_session(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_response = SimpleNamespace(
            model_dump=lambda mode="json": {
                "session_id": "session_123",
                "cdp_url": "wss://example.com/cdp",
                "base_url": "https://browser.tinyfish.ai/session_123",
            }
        )
        mock_tinyfish["client"].browser.sessions.create.return_value = mock_response

        toolkit = TinyFishToolkit()
        browser_tool = next(t for t in toolkit.tools if t.name == "tinyfish_create_browser_session")
        output = browser_tool.func(url="https://docs.tinyfish.ai", timeout_seconds=300)

        parsed = json.loads(output)
        assert parsed["session_id"] == "session_123"
        mock_tinyfish["client"].browser.sessions.create.assert_called_once_with(
            url="https://docs.tinyfish.ai",
            timeout_seconds=300,
        )

    def test_create_browser_session_exception(self, mock_tinyfish):
        from autogen.tools.experimental.tinyfish import TinyFishToolkit

        mock_tinyfish["client"].browser.sessions.create.side_effect = Exception("Browser failed")

        toolkit = TinyFishToolkit()
        browser_tool = next(t for t in toolkit.tools if t.name == "tinyfish_create_browser_session")
        output = browser_tool.func(url="https://docs.tinyfish.ai")

        assert "Error" in output
        assert "Browser failed" in output
