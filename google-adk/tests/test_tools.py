"""Tests for TinyFish Google ADK tools."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from tinyfish import BrowserProfile, ProxyCountryCode, RunStatus

from tinyfish_adk import (
    __all__,
    tinyfish_create_browser_session,
    tinyfish_fetch,
    tinyfish_get_run,
    tinyfish_list_runs,
    tinyfish_queue_run,
    tinyfish_search,
    tinyfish_web_agent,
)
from tinyfish_adk.tools import _get_client, _run_kwargs


def _response(payload: dict):
    return SimpleNamespace(model_dump=lambda: payload)


def test_public_exports() -> None:
    assert sorted(__all__) == sorted(
        [
            "tinyfish_web_agent",
            "tinyfish_queue_run",
            "tinyfish_get_run",
            "tinyfish_list_runs",
            "tinyfish_search",
            "tinyfish_fetch",
            "tinyfish_create_browser_session",
        ]
    )


def test_get_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    with patch("tinyfish_adk.tools._client", None):
        with pytest.raises(RuntimeError, match="TINYFISH_API_KEY"):
            _get_client()


def test_get_client_sets_integration_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    monkeypatch.delenv("TF_API_INTEGRATION", raising=False)

    with patch("tinyfish_adk.tools._client", None):
        with patch("tinyfish_adk.tools.TinyFish") as tinyfish:
            _get_client()

    assert os.environ["TF_API_INTEGRATION"] == "google-adk"
    tinyfish.assert_called_once_with(api_key="sk-test")


def test_run_kwargs_defaults_invalid_profile_to_lite() -> None:
    kwargs = _run_kwargs("bad-profile", "")

    assert kwargs["browser_profile"] == BrowserProfile.LITE


def test_run_kwargs_adds_proxy_config() -> None:
    kwargs = _run_kwargs("stealth", "GB")

    assert kwargs["browser_profile"] == BrowserProfile.STEALTH
    assert kwargs["proxy_config"].enabled is True
    assert kwargs["proxy_config"].country_code == ProxyCountryCode("GB")


def test_run_kwargs_rejects_invalid_proxy_country() -> None:
    kwargs = _run_kwargs("lite", "XX")

    assert kwargs["_error"] == "Invalid proxy country: 'XX'"


def test_web_agent_completed_result() -> None:
    client = MagicMock()
    client.agent.run.return_value = SimpleNamespace(
        status=RunStatus.COMPLETED,
        result={"title": "Example"},
    )

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_web_agent("https://example.com", "Extract title")

    assert json.loads(result) == {"title": "Example"}
    client.agent.run.assert_called_once()


def test_web_agent_failed_result() -> None:
    client = MagicMock()
    client.agent.run.return_value = SimpleNamespace(
        status=RunStatus.FAILED,
        result=None,
        error={"message": "Failed"},
    )

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_web_agent("https://example.com", "Extract title")

    assert result == "Automation failed: Failed"


def test_queue_run() -> None:
    client = MagicMock()
    client.agent.queue.return_value = SimpleNamespace(run_id="run-123")

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_queue_run("https://example.com", "Extract title")

    assert result == "Automation started. run_id: run-123"


def test_get_run_formats_details() -> None:
    client = MagicMock()
    client.runs.get.return_value = SimpleNamespace(
        status=RunStatus.COMPLETED,
        result={"ok": True},
        error=None,
        streaming_url="https://stream.example.com",
    )

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_get_run("run-123")

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

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_list_runs(status="COMPLETED", limit=5)

    assert "Found 1 runs" in result
    client.runs.list.assert_called_once_with(limit=5, status=RunStatus.COMPLETED)


def test_search_uses_sdk_resource() -> None:
    client = MagicMock()
    client.search.query.return_value = _response(
        {
            "query": "tinyfish",
            "results": [{"title": "TinyFish", "url": "https://tinyfish.ai"}],
            "total_results": 1,
        }
    )

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_search("tinyfish", location="United States", language="en")

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

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_fetch(
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

    with patch("tinyfish_adk.tools._get_client", return_value=client):
        result = tinyfish_create_browser_session(
            url="https://example.com",
            timeout_seconds=120,
        )

    assert json.loads(result)["session_id"] == "tf-session"
    client.browser.sessions.create.assert_called_once_with(
        url="https://example.com",
        timeout_seconds=120,
    )
