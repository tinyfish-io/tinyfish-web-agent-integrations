from __future__ import annotations

from typing import Any

import pytest

from tinyfish_hermes import routing_context as routing
from tinyfish_hermes.config import routing_context_enabled


def _mcp_config(**tinyfish: Any) -> dict[str, Any]:
    section = {"url": "https://agent.tinyfish.ai/mcp", **tinyfish}
    return {"mcp_servers": {"tinyfish": section}}


def test_routing_context_injected_when_tinyfish_mcp_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)

    result = routing.routing_context_hook(
        user_message="ordinary search", conversation_history=[]
    )

    assert result is not None
    assert routing.ROUTING_CONTEXT_MARKER in result["context"]
    assert "`web_search` or `web_extract`" in result["context"]
    assert "`search` or `fetch_content`" in result["context"]
    assert "plain language" in result["context"]
    assert "silently dropping" in result["context"]


@pytest.mark.parametrize(
    "auth",
    [None, "oauth", "bearer", "header"],
    ids=["absent", "oauth", "bearer", "header"],
)
def test_routing_context_gates_on_url_not_auth_mode(
    monkeypatch: pytest.MonkeyPatch, auth: str | None
) -> None:
    # The first-party MCP entry authenticates with an API-key header, not OAuth.
    config = _mcp_config() if auth is None else _mcp_config(auth=auth)
    monkeypatch.setattr(routing, "load_config", lambda: config)

    assert routing.routing_context_hook(conversation_history=[]) is not None


@pytest.mark.parametrize(
    "url",
    [
        "https://agent.tinyfish.ai/mcp",
        "https://agent.tinyfish.ai/mcp/",
        "https://AGENT.TINYFISH.AI/mcp",
    ],
    ids=["exact", "trailing-slash", "uppercase-host"],
)
def test_tinyfish_mcp_configured_normalizes_url_variants(url: str) -> None:
    assert routing.tinyfish_mcp_configured({"mcp_servers": {"tinyfish": {"url": url}}})


@pytest.mark.parametrize(
    "url",
    [
        "http://agent.tinyfish.ai/mcp",
        "https://agent.tinyfish.ai/mcp/extra",
        "https://agent.tinyfish.ai.evil.example/mcp",
        "",
    ],
    ids=["http-scheme", "wrong-path", "lookalike-host", "empty"],
)
def test_tinyfish_mcp_configured_rejects_non_matching_urls(url: str) -> None:
    assert not routing.tinyfish_mcp_configured(
        {"mcp_servers": {"tinyfish": {"url": url}}}
    )


@pytest.mark.parametrize(
    "message",
    [
        {"role": "user", "content": "search", "api_content": routing.ROUTING_GUIDANCE},
        {"role": "user", "content": routing.ROUTING_GUIDANCE},
        {
            "role": "user",
            "content": [{"type": "text", "text": routing.ROUTING_GUIDANCE}],
        },
    ],
)
def test_existing_marker_suppresses_duplicate_routing_guidance(
    monkeypatch: pytest.MonkeyPatch,
    message: dict[str, Any],
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)

    assert routing.routing_context_hook(conversation_history=[message]) is None


def test_routing_guidance_returns_after_compression_removes_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)

    result = routing.routing_context_hook(
        conversation_history=[
            {"role": "user", "content": "compacted user turn"},
            {"role": "assistant", "content": "compacted answer"},
        ]
    )

    assert result is not None
    assert result["context"].count(routing.ROUTING_CONTEXT_MARKER) == 1


def test_other_marker_versions_do_not_suppress_current_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)

    result = routing.routing_context_hook(
        conversation_history=[
            {
                "role": "user",
                "content": "search",
                "api_content": '<tinyfish-routing-context version="0">old guidance',
            }
        ]
    )

    assert result is not None
    assert routing.ROUTING_CONTEXT_MARKER in result["context"]


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"tinyfish": {"routing_context": False}, **_mcp_config()},
        {"mcp_servers": {"tinyfish": {"url": "https://example.com"}}},
        {"mcp_servers": {"tinyfish": {}}},
        {"mcp_servers": "tinyfish"},
    ],
)
def test_routing_context_absent_when_disabled_or_mcp_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, Any],
) -> None:
    monkeypatch.setattr(routing, "load_config", lambda: config)

    assert routing.routing_context_hook() is None


def test_routing_context_config_switch_defaults_true() -> None:
    assert routing_context_enabled({}) is True
    assert routing_context_enabled({"tinyfish": {"routing_context": False}}) is False
    assert routing_context_enabled({"tinyfish": {"routing_context": "off"}}) is False
