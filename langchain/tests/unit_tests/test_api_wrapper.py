"""Unit tests for TinyFishAPIWrapper."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr
from tinyfish import BrowserProfile, ProxyCountryCode, RunStatus

from langchain_tinyfish._api_wrapper import TinyFishAPIWrapper


def _run_result(status=RunStatus.COMPLETED, result=None, error=None):
    """Create a mock run result object."""
    return SimpleNamespace(status=status, result=result, error=error)


def _queue_result(run_id="run-abc"):
    """Create a mock queue result."""
    return SimpleNamespace(run_id=run_id)


class TestAPIKeyHandling:
    """Tests for API key configuration."""

    def test_explicit_api_key(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test-123"))
        assert wrapper.api_key.get_secret_value() == "sk-test-123"

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TINYFISH_API_KEY", "sk-env-key")
        wrapper = TinyFishAPIWrapper()
        assert wrapper.api_key.get_secret_value() == "sk-env-key"

    def test_api_key_not_in_repr(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-secret-key"))
        assert "sk-secret-key" not in repr(wrapper)
        assert "sk-secret-key" not in str(wrapper)

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
        with pytest.raises(ValueError):
            TinyFishAPIWrapper()


class TestIntegrationTag:
    """Tests for automatic integration attribution."""

    def test_make_client_sets_default_integration_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TF_API_INTEGRATION", raising=False)
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))

        with patch("langchain_tinyfish._api_wrapper.TinyFish") as mock_tinyfish:
            wrapper._make_client()

        assert os.environ["TF_API_INTEGRATION"] == "langchain"
        mock_tinyfish.assert_called_once_with(api_key="sk-test")

    def test_make_client_preserves_existing_integration_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TF_API_INTEGRATION", "custom-tag")
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))

        with patch("langchain_tinyfish._api_wrapper.TinyFish"):
            wrapper._make_client()

        assert os.environ["TF_API_INTEGRATION"] == "custom-tag"


class TestBrowserProfileAndProxy:
    """Tests for SDK config helpers."""

    def test_default_browser_profile(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        assert wrapper._get_browser_profile() == BrowserProfile.LITE

    def test_stealth_browser_profile(self) -> None:
        wrapper = TinyFishAPIWrapper(
            api_key=SecretStr("sk-test"), browser_profile="stealth"
        )
        assert wrapper._get_browser_profile() == BrowserProfile.STEALTH

    def test_no_proxy_by_default(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        assert wrapper._get_proxy_config() is None

    def test_proxy_config(self) -> None:
        wrapper = TinyFishAPIWrapper(
            api_key=SecretStr("sk-test"),
            proxy_enabled=True,
            proxy_country_code="GB",
        )
        proxy = wrapper._get_proxy_config()
        assert proxy is not None
        assert proxy.enabled is True
        assert proxy.country_code == ProxyCountryCode("GB")


class TestHandleRunResult:
    """Tests for _handle_run_result."""

    def test_completed_with_result(self) -> None:
        result = TinyFishAPIWrapper._handle_run_result(
            _run_result(result={"title": "Example"})
        )
        assert json.loads(result) == {"title": "Example"}

    def test_completed_no_result(self) -> None:
        result = TinyFishAPIWrapper._handle_run_result(_run_result(result=None))
        parsed = json.loads(result)
        assert parsed["status"] == "completed"

    def test_failed_with_error_dict(self) -> None:
        with pytest.raises(RuntimeError, match="Page not found"):
            TinyFishAPIWrapper._handle_run_result(
                _run_result(
                    status=RunStatus.FAILED,
                    error={"message": "Page not found"},
                )
            )

    def test_failed_with_error_string(self) -> None:
        with pytest.raises(RuntimeError, match="Something went wrong"):
            TinyFishAPIWrapper._handle_run_result(
                _run_result(
                    status=RunStatus.FAILED,
                    error="Something went wrong",
                )
            )

    def test_cancelled_raises(self) -> None:
        with pytest.raises(RuntimeError, match="cancelled"):
            TinyFishAPIWrapper._handle_run_result(
                _run_result(status=RunStatus.CANCELLED)
            )


class TestRunSync:
    """Tests for the synchronous run method."""

    def test_successful_run(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = MagicMock()
        mock_client.agent.run.return_value = _run_result(
            result={"products": [{"name": "Widget", "price": "$9.99"}]}
        )

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            result = wrapper.run("https://example.com/products", "Extract products")

        parsed = json.loads(result)
        assert parsed["products"][0]["name"] == "Widget"
        mock_client.agent.run.assert_called_once()

    def test_failed_run(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = MagicMock()
        mock_client.agent.run.return_value = _run_result(
            status=RunStatus.FAILED,
            error={"message": "Timeout"},
        )

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Timeout"):
                wrapper.run("https://example.com", "Do something")

    def test_stealth_with_proxy(self) -> None:
        wrapper = TinyFishAPIWrapper(
            api_key=SecretStr("sk-test"),
            browser_profile="stealth",
            proxy_enabled=True,
            proxy_country_code="JP",
        )
        mock_client = MagicMock()
        mock_client.agent.run.return_value = _run_result(result={"data": "ok"})

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            wrapper.run("https://example.com", "Extract")

        call_kwargs = mock_client.agent.run.call_args.kwargs
        assert call_kwargs["browser_profile"] == BrowserProfile.STEALTH
        assert call_kwargs["proxy_config"].enabled is True
        assert call_kwargs["proxy_config"].country_code == ProxyCountryCode("JP")


class TestModelConfig:
    """Tests for Pydantic model config."""

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(Exception):
            TinyFishAPIWrapper(api_key=SecretStr("sk-test"), unknown_field="value")

    def test_default_values(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        assert wrapper.browser_profile == "lite"
        assert wrapper.proxy_enabled is False
        assert wrapper.proxy_country_code == "US"
        assert wrapper.timeout == 300
        assert wrapper.poll_interval == 2.0


class TestArun:
    """Tests for the async arun method (queue + polling)."""

    @pytest.mark.asyncio
    async def test_arun_polls_until_complete(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"), timeout=10)
        mock_client = AsyncMock()
        mock_client.agent.queue = AsyncMock(return_value=_queue_result("run-abc"))

        poll_pending = SimpleNamespace(
            status=RunStatus.RUNNING, result=None, error=None
        )
        poll_done = SimpleNamespace(
            status=RunStatus.COMPLETED, result={"title": "Hello"}, error=None
        )
        mock_client.runs.get = AsyncMock(
            side_effect=[poll_pending, poll_pending, poll_done]
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await wrapper.arun("https://example.com", "Get title")

        assert json.loads(result) == {"title": "Hello"}
        assert mock_client.runs.get.call_count == 3

    @pytest.mark.asyncio
    async def test_arun_failed_run(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"), timeout=10)
        mock_client = AsyncMock()
        mock_client.agent.queue = AsyncMock(return_value=_queue_result("run-fail"))
        mock_client.runs.get = AsyncMock(
            return_value=SimpleNamespace(
                status=RunStatus.FAILED,
                result=None,
                error={"message": "Element not found"},
            )
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Element not found"):
                    await wrapper.arun("https://example.com", "Click button")


class TestGetRun:
    """Tests for get_run."""

    @pytest.mark.asyncio
    async def test_get_run(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = AsyncMock()
        mock_client.runs.get = AsyncMock(
            return_value=SimpleNamespace(
                run_id="run-123",
                status=RunStatus.COMPLETED,
                result={"x": 1},
                error=None,
                streaming_url=None,
            )
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            result = await wrapper.get_run("run-123")

        assert result["run_id"] == "run-123"
        assert result["status"] == "COMPLETED"
        assert result["result"] == {"x": 1}


class TestListRuns:
    """Tests for list_runs."""

    @pytest.mark.asyncio
    async def test_list_runs_with_filters(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = AsyncMock()
        mock_run = SimpleNamespace(
            run_id="r1", status=RunStatus.COMPLETED, url="https://a.com", goal="Get A"
        )
        mock_client.runs.list = AsyncMock(return_value=SimpleNamespace(runs=[mock_run]))

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            result = await wrapper.list_runs(status="COMPLETED", limit=10)

        assert len(result["data"]) == 1
        assert result["data"][0]["run_id"] == "r1"
        mock_client.runs.list.assert_called_once_with(
            limit=10, status=RunStatus("COMPLETED")
        )


class TestSearchFetchAndBrowser:
    """Tests for SDK-backed search, fetch, and browser helpers."""

    def test_search_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = MagicMock()
        mock_client.search.query.return_value = SimpleNamespace(
            model_dump=lambda: {
                "query": "tinyfish",
                "results": [{"title": "TinyFish", "url": "https://tinyfish.ai"}],
                "total_results": 1,
            }
        )

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            result = wrapper.search("tinyfish", location="United States", language="en")

        assert json.loads(result)["total_results"] == 1
        mock_client.search.query.assert_called_once_with(
            query="tinyfish",
            location="United States",
            language="en",
        )

    @pytest.mark.asyncio
    async def test_asearch_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = AsyncMock()
        mock_client.search.query = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {
                    "query": "tinyfish",
                    "results": [],
                    "total_results": 0,
                }
            )
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            result = await wrapper.asearch("tinyfish")

        assert json.loads(result)["query"] == "tinyfish"
        mock_client.search.query.assert_called_once_with(
            query="tinyfish",
            location=None,
            language=None,
        )

    def test_fetch_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = MagicMock()
        mock_client.fetch.get_contents.return_value = SimpleNamespace(
            model_dump=lambda: {
                "results": [{"url": "https://example.com", "text": "Example"}],
                "errors": [],
            }
        )

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            result = wrapper.fetch(
                ["https://example.com"],
                format="markdown",
                links=True,
                image_links=False,
            )

        assert json.loads(result)["results"][0]["text"] == "Example"
        mock_client.fetch.get_contents.assert_called_once_with(
            urls=["https://example.com"],
            format="markdown",
            links=True,
            image_links=False,
        )

    @pytest.mark.asyncio
    async def test_afetch_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = AsyncMock()
        mock_client.fetch.get_contents = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {"results": [], "errors": []}
            )
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            result = await wrapper.afetch(["https://example.com"])

        assert json.loads(result) == {"results": [], "errors": []}
        mock_client.fetch.get_contents.assert_called_once_with(
            urls=["https://example.com"],
            format="markdown",
            links=None,
            image_links=None,
        )

    def test_create_browser_session_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = MagicMock()
        mock_client.browser.sessions.create.return_value = SimpleNamespace(
            model_dump=lambda: {
                "session_id": "tf-session",
                "cdp_url": "wss://example.test",
                "base_url": "https://example.test",
            }
        )

        with patch.object(wrapper, "_make_client", return_value=mock_client):
            result = wrapper.create_browser_session(
                url="https://example.com",
                timeout_seconds=120,
            )

        assert json.loads(result)["session_id"] == "tf-session"
        mock_client.browser.sessions.create.assert_called_once_with(
            url="https://example.com",
            timeout_seconds=120,
        )

    @pytest.mark.asyncio
    async def test_acreate_browser_session_uses_sdk_resource(self) -> None:
        wrapper = TinyFishAPIWrapper(api_key=SecretStr("sk-test"))
        mock_client = AsyncMock()
        mock_client.browser.sessions.create = AsyncMock(
            return_value=SimpleNamespace(
                model_dump=lambda: {
                    "session_id": "tf-session",
                    "cdp_url": "wss://example.test",
                    "base_url": "https://example.test",
                }
            )
        )

        with patch.object(wrapper, "_make_async_client", return_value=mock_client):
            result = await wrapper.acreate_browser_session()

        assert json.loads(result)["base_url"] == "https://example.test"
        mock_client.browser.sessions.create.assert_called_once_with(
            url=None,
            timeout_seconds=None,
        )
