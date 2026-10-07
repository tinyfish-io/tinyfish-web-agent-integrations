"""Once-per-context TinyFish tool-routing guidance for Hermes turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from .config import browser_cloud_provider, load_config, routing_context_enabled
from .provider import API_KEY_URL, _api_key

ROUTING_CONTEXT_MARKER = '<tinyfish-routing-context version="1">'
ROUTING_GUIDANCE = f"""{ROUTING_CONTEXT_MARKER}
TinyFish tool-routing guidance:
- For ordinary web discovery or reading a page, use Hermes `web_search` or `web_extract`; the `tinyfish` provider serves both directly over the TinyFish REST APIs.
- When the request needs TinyFish-specific controls the generic schemas cannot express—domain/date/language/location/purpose/pagination filters, output formats, link or image extraction, cache TTL, or per-URL timeouts—use the native `search` or `fetch_content` tool registered by the `tinyfish` MCP server, commonly exposed as `mcp__tinyfish__search` and `mcp__tinyfish__fetch_content`.
- Infer the choice from the user's plain language. Do not ask them to choose MCP versus the provider, and do not persist per-request controls as configuration. If a required native tool is unavailable, use the generic provider only when it can preserve the requested constraints; otherwise explain which control is unavailable rather than silently dropping it."""


SETUP_CONTEXT_MARKER = '<tinyfish-setup-context version="1">'
SETUP_GUIDANCE = f"""{SETUP_CONTEXT_MARKER}
TinyFish is installed but has no API key, so its web search, fetch, and browser tools are unavailable. If the user needs web access, tell them to create a free key at {API_KEY_URL} and run `hermes tinyfish setup`."""


def tinyfish_backend_configured(config: dict[str, Any]) -> bool:
    web = config.get("web") or {}
    web_keys = ("search_backend", "extract_backend", "backend")
    routed = isinstance(web, dict) and "tinyfish" in {web.get(k) for k in web_keys}
    return routed or browser_cloud_provider(config) == "tinyfish"


def tinyfish_mcp_configured(config: dict[str, Any]) -> bool:
    servers = config.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return False
    tinyfish = servers.get("tinyfish") or {}
    if not isinstance(tinyfish, dict):
        return False
    # Any auth mode counts: the first-party MCP entry uses an API-key header, not OAuth.
    parsed = urlparse(str(tinyfish.get("url") or ""))
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == "agent.tinyfish.ai"
        and parsed.path.rstrip("/") == "/mcp"
    )


def _contains_marker(value: object, marker: str) -> bool:
    if isinstance(value, str):
        return marker in value
    if isinstance(value, Mapping):
        return any(_contains_marker(item, marker) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_marker(item, marker) for item in value)
    return False


def routing_guidance_present(
    conversation_history: object, marker: str = ROUTING_CONTEXT_MARKER
) -> bool:
    """Return whether Hermes already carries this marker version in context."""

    if not isinstance(conversation_history, Sequence) or isinstance(
        conversation_history, (str, bytes, bytearray)
    ):
        return False
    for message in conversation_history:
        if not isinstance(message, Mapping):
            continue
        if _contains_marker(message.get("api_content"), marker):
            return True
        if _contains_marker(message.get("content"), marker):
            return True
    return False


def routing_context_hook(**kwargs: Any) -> dict[str, str] | None:
    """Hermes ``pre_llm_call`` hook injecting versioned routing guidance once."""

    history = kwargs.get("conversation_history")
    config = load_config()
    if not routing_context_enabled(config):
        return None
    if not _api_key():
        if not tinyfish_backend_configured(config):
            return None
        if routing_guidance_present(history, SETUP_CONTEXT_MARKER):
            return None
        return {"context": SETUP_GUIDANCE}
    if not tinyfish_mcp_configured(config):
        return None
    if routing_guidance_present(history):
        return None
    return {"context": ROUTING_GUIDANCE}
