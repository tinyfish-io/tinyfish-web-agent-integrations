"""Once-per-context TinyFish tool-routing guidance for Hermes turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .config import TINYFISH_MCP_URL, load_config, routing_context_enabled

ROUTING_CONTEXT_MARKER = '<tinyfish-routing-context version="1">'
ROUTING_GUIDANCE = f"""{ROUTING_CONTEXT_MARKER}
TinyFish tool-routing guidance:
- For ordinary web discovery or reading a page, use Hermes `web_search` or `web_extract`; the `tinyfish` provider serves both directly over the TinyFish REST APIs.
- When the request needs TinyFish-specific controls the generic schemas cannot express—domain/date/language/location/purpose/pagination filters, output formats, link or image extraction, cache TTL, or per-URL timeouts—use the native `search` or `fetch_content` tool registered by the `tinyfish` MCP server, commonly exposed as `mcp__tinyfish__search` and `mcp__tinyfish__fetch_content`.
- Infer the choice from the user's plain language. Do not ask them to choose MCP versus the provider, and do not persist per-request controls as configuration. If a required native tool is unavailable, use the generic provider only when it can preserve the requested constraints; otherwise explain which control is unavailable rather than silently dropping it."""


def tinyfish_mcp_configured(config: dict[str, Any]) -> bool:
    servers = config.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return False
    tinyfish = servers.get("tinyfish") or {}
    # Any auth mode counts: the first-party MCP entry uses an API-key header, not OAuth.
    return bool(isinstance(tinyfish, dict) and tinyfish.get("url") == TINYFISH_MCP_URL)


def _contains_routing_marker(value: object) -> bool:
    if isinstance(value, str):
        return ROUTING_CONTEXT_MARKER in value
    if isinstance(value, Mapping):
        return any(_contains_routing_marker(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_routing_marker(item) for item in value)
    return False


def routing_guidance_present(conversation_history: object) -> bool:
    """Return whether Hermes already carries this routing version in context."""

    if not isinstance(conversation_history, Sequence) or isinstance(
        conversation_history, (str, bytes, bytearray)
    ):
        return False
    for message in conversation_history:
        if not isinstance(message, Mapping):
            continue
        if _contains_routing_marker(message.get("api_content")):
            return True
        if _contains_routing_marker(message.get("content")):
            return True
    return False


def routing_context_hook(**kwargs: Any) -> dict[str, str] | None:
    """Hermes ``pre_llm_call`` hook injecting versioned routing guidance once."""

    config = load_config()
    if not routing_context_enabled(config) or not tinyfish_mcp_configured(config):
        return None
    if routing_guidance_present(kwargs.get("conversation_history")):
        return None
    return {"context": ROUTING_GUIDANCE}
