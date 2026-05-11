"""Tests for TinyFish CrewAI tools."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tinyfish import BrowserProfile, ProxyCountryCode, RunStatus

from tinyfish_web_agent import (
    Tinyfish,
    TinyfishBrowserSession,
    TinyfishFetch,
    TinyfishGetRun,
    TinyfishListRuns,
    TinyfishRun,
    TinyfishRunAsync,
    TinyfishSearch,
    __all__,
)


def _response(payload: dict):
    return SimpleNamespace(model_dump=lambda: payload)


def test_public_exports() -> None:
    assert sorted(__all__) == sorted(
        [
            "Tinyfish",
            "TinyfishRun",
            "TinyfishRunAsync",
            "TinyfishGetRun",
            "TinyfishListRuns",
            "TinyfishSearch",
            "TinyfishFetch",
            "TinyfishBrowserSession",
        ]
    )
    assert Tinyfish is TinyfishRun


def test_get_client_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)

    result = TinyfishRun()._run("https://example.com", "Extract title")

    assert result.startswith("Error: TINYFISH_API_KEY is not set")


def test_get_client_sets_integration_tag(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    monkeypatch.delenv("TF_API_INTEGRATION", raising=False)

    with patch("tinyfish_web_agent.tool.TinyFish") as tinyfish:
        TinyfishRun()._get_client()

    assert os.environ["TF_API_INTEGRATION"] == "crew-ai"
    tinyfish.assert_called_once_with(api_key="sk-test")


def test_run_kwargs_defaults_invalid_profile_to_lite() -> None:
    kwargs = TinyfishRun()._run_kwargs("bad-profile")

    assert kwargs["browser_profile"] == BrowserProfile.LITE


def test_run_kwargs_adds_proxy_config() -> None:
    kwargs = TinyfishRun(proxy_country="GB")._run_kwargs("stealth")

    assert kwargs["browser_profile"] == BrowserProfile.STEALTH
    assert kwargs["proxy_config"].enabled is True
    assert kwargs["proxy_config"].country_code == ProxyCountryCode("GB")


def test_run_rejects_invalid_proxy_country() -> None:
    client = MagicMock()

    with patch.object(TinyfishRun, "_get_client", return_value=(client, None)):
        result = TinyfishRun(proxy_country="XX")._run(
            "https://example.com",
            "Extract title",
        )

    assert result == "Error: Invalid proxy country: 'XX'"
    client.agent.run.assert_not_called()


def test_run_completed_result() -> None:
    client = MagicMock()
    client.agent.run.return_value = SimpleNamespace(
        status=RunStatus.COMPLETED,
        result={"title": "Example"},
    )

    with patch.object(TinyfishRun, "_get_client", return_value=(client, None)):
        result = TinyfishRun()._run("https://example.com", "Extract title")

    assert json.loads(result) == {"title": "Example"}
    client.agent.run.assert_called_once()


def test_run_failed_result() -> None:
    client = MagicMock()
    client.agent.run.return_value = SimpleNamespace(
        status=RunStatus.FAILED,
        result=None,
        error={"message": "Failed"},
    )

    with patch.object(TinyfishRun, "_get_client", return_value=(client, None)):
        result = TinyfishRun()._run("https://example.com", "Extract title")

    assert result == "Automation failed: Failed"


def test_async_run() -> None:
    client = MagicMock()
    client.agent.queue.return_value = SimpleNamespace(run_id="run-123")

    with patch.object(TinyfishRunAsync, "_get_client", return_value=(client, None)):
        result = TinyfishRunAsync()._run("https://example.com", "Extract title")

    assert result == "Automation started. run_id: run-123"


def test_get_run_formats_details() -> None:
    client = MagicMock()
    client.runs.get.return_value = SimpleNamespace(
        status=RunStatus.COMPLETED,
        result={"ok": True},
        error=None,
        streaming_url="https://stream.example.com",
    )

    with patch.object(TinyfishGetRun, "_get_client", return_value=(client, None)):
        result = TinyfishGetRun()._run("run-123")

    assert "Status: COMPLETED" in result
    assert "Live view: https://stream.example.com" in result
    assert 'Result: {"ok": true}' in result


def test_list_runs_with_status_filter() -> None:
    client = MagicMock()
    client.runs.list.return_value = SimpleNamespace(
        runs=[
            SimpleNamespace(
                run_id="run-123",
                status=RunStatus.COMPLETED,
                url="https://example.com",
            )
        ]
    )

    with patch.object(TinyfishListRuns, "_get_client", return_value=(client, None)):
        result = TinyfishListRuns()._run(status="COMPLETED", limit=5)

    assert "Found 1 runs" in result
    client.runs.list.assert_called_once_with(limit=5, status=RunStatus.COMPLETED)


def test_list_runs_uses_sdk_data_field() -> None:
    client = MagicMock()
    client.runs.list.return_value = SimpleNamespace(
        data=[
            SimpleNamespace(
                run_id="run-123",
                status=RunStatus.COMPLETED,
                url="https://example.com",
            )
        ]
    )

    with patch.object(TinyfishListRuns, "_get_client", return_value=(client, None)):
        result = TinyfishListRuns()._run(limit=5)

    assert "Found 1 runs" in result
    assert "run-123" in result


def test_search_uses_sdk_resource() -> None:
    client = MagicMock()
    client.search.query.return_value = _response(
        {
            "query": "tinyfish",
            "results": [{"title": "TinyFish", "url": "https://tinyfish.ai"}],
            "total_results": 1,
        }
    )

    with patch.object(TinyfishSearch, "_get_client", return_value=(client, None)):
        result = TinyfishSearch()._run(
            "tinyfish",
            location="United States",
            language="en",
        )

    assert json.loads(result)["total_results"] == 1
    client.search.query.assert_called_once_with(
        query="tinyfish",
        location="United States",
        language="en",
    )


def test_fetch_uses_sdk_resource() -> None:
    client = MagicMock()
    client.fetch.get_contents.return_value = _response(
        {
            "results": [{"url": "https://example.com", "text": "Example"}],
            "errors": [],
        }
    )

    with patch.object(TinyfishFetch, "_get_client", return_value=(client, None)):
        result = TinyfishFetch()._run(
            ["https://example.com"],
            format="markdown",
            links=True,
            image_links=False,
        )

    assert json.loads(result)["results"][0]["text"] == "Example"
    client.fetch.get_contents.assert_called_once_with(
        urls=["https://example.com"],
        format="markdown",
        links=True,
        image_links=False,
    )


def test_create_browser_session_uses_sdk_resource() -> None:
    client = MagicMock()
    client.browser.sessions.create.return_value = _response(
        {
            "session_id": "tf-session",
            "cdp_url": "wss://example.test",
            "base_url": "https://example.test",
        }
    )

    with patch.object(
        TinyfishBrowserSession,
        "_get_client",
        return_value=(client, None),
    ):
        result = TinyfishBrowserSession()._run(
            url="https://example.com",
            timeout_seconds=120,
        )

    assert json.loads(result)["session_id"] == "tf-session"
    client.browser.sessions.create.assert_called_once_with(
        url="https://example.com",
        timeout_seconds=120,
    )
