"""Tests for the TinyFish web-agent CrewAI tool."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tinyfish_web_agent import TinyfishWebAgent, __all__
from tinyfish_web_agent.tool import TinyfishWebAgentInput


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)


def _mock_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text if text is not None else json.dumps(json_data or {})
    if json_data is None and text is None:
        resp.json.side_effect = ValueError("no body")
    return resp


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------


def test_public_exports() -> None:
    assert sorted(__all__) == ["TinyfishWebAgent"]


def test_tool_metadata() -> None:
    tool = TinyfishWebAgent()
    assert tool.name == "Tinyfish Web Agent"
    assert tool.package_dependencies == ["requests"]
    assert [e.name for e in tool.env_vars] == ["TINYFISH_API_KEY"]
    assert tool.env_vars[0].required is True


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_input_rejects_non_http_url() -> None:
    with pytest.raises(ValueError, match="http"):
        TinyfishWebAgentInput(url="ftp://example.com", goal="x")


def test_input_accepts_https() -> None:
    payload = TinyfishWebAgentInput(url="https://example.com", goal="x")
    assert payload.browser_profile == "lite"


# ---------------------------------------------------------------------------
# Runtime error paths
# ---------------------------------------------------------------------------


def test_missing_api_key_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    result = TinyfishWebAgent()._run(url="https://example.com", goal="x")
    assert result.startswith("Error: TINYFISH_API_KEY is not set")


def test_invalid_proxy_country_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    tool = TinyfishWebAgent(proxy_country="ZZ")
    result = tool._run(url="https://example.com", goal="x")
    assert result == "Error: Invalid proxy country: 'ZZ'"


def test_http_error_returns_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    with patch(
        "tinyfish_web_agent.tool.requests.post",
        return_value=_mock_response(status_code=401),
    ):
        result = TinyfishWebAgent()._run(url="https://example.com", goal="x")
    assert "Invalid or missing API key" in result


def test_network_exception_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests as requests_lib

    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    with patch(
        "tinyfish_web_agent.tool.requests.post",
        side_effect=requests_lib.ConnectTimeout("timed out"),
    ):
        result = TinyfishWebAgent()._run(url="https://example.com", goal="x")
    assert result.startswith("Error: HTTP request failed")


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    payload = {"status": "COMPLETED", "result": {"title": "Example"}, "run_id": "abc"}

    with patch(
        "tinyfish_web_agent.tool.requests.post",
        return_value=_mock_response(status_code=200, json_data=payload),
    ) as mock_post:
        result = TinyfishWebAgent()._run(
            url="https://example.com",
            goal="Get the title",
            browser_profile="lite",
        )

    assert json.loads(result) == payload
    sent = mock_post.call_args
    assert sent.kwargs["json"] == {
        "url": "https://example.com",
        "goal": "Get the title",
        "browser_profile": "lite",
    }
    assert sent.kwargs["headers"]["X-API-Key"] == "sk-test"
    assert sent.kwargs["headers"]["X-TF-Integration"] == "crew-ai"


def test_proxy_country_included_in_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-test")
    with patch(
        "tinyfish_web_agent.tool.requests.post",
        return_value=_mock_response(status_code=200, json_data={"status": "COMPLETED"}),
    ) as mock_post:
        TinyfishWebAgent(proxy_country="GB")._run(
            url="https://example.com",
            goal="x",
            browser_profile="stealth",
        )

    body = mock_post.call_args.kwargs["json"]
    assert body["browser_profile"] == "stealth"
    assert body["proxy_config"] == {"enabled": True, "country_code": "GB"}


def test_explicit_api_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-env")
    with patch(
        "tinyfish_web_agent.tool.requests.post",
        return_value=_mock_response(status_code=200, json_data={"status": "COMPLETED"}),
    ) as mock_post:
        TinyfishWebAgent(api_key="sk-explicit")._run(
            url="https://example.com", goal="x"
        )
    assert mock_post.call_args.kwargs["headers"]["X-API-Key"] == "sk-explicit"
