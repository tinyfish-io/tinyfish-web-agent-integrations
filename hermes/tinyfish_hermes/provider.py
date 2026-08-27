"""Hermes WebSearchProvider implementation for TinyFish, REST-only."""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    from agent.web_search_provider import WebSearchProvider as _HermesWebSearchProvider
except Exception:  # pragma: no cover - lets the package import outside Hermes

    class _HermesWebSearchProvider:  # type: ignore[no-redef]
        pass


from . import rest_client
from .config import default_fetch_format, fetch_options, search_options
from .normalize import normalize_fetch_documents, normalize_search_response

logger = logging.getLogger(__name__)

API_KEY_ENV_VARS = ("TINYFISH_API_KEY", "MCP_TINYFISH_API_KEY")
API_KEY_URL = "https://agent.tinyfish.ai/api-keys"
MISSING_KEY_ERROR = (
    "TinyFish API key not found. Set TINYFISH_API_KEY or MCP_TINYFISH_API_KEY; "
    f"create a key at {API_KEY_URL}."
)


def _provider_env(name: str) -> str:
    """Read Hermes config-aware environment values when available."""

    try:
        from agent.web_search_provider import get_provider_env

        return str(get_provider_env(name) or "").strip()
    except Exception:
        return str(os.getenv(name, "") or "").strip()


def _api_key() -> str:
    for name in API_KEY_ENV_VARS:
        value = _provider_env(name)
        if value:
            return value
    return ""


def _is_interrupted() -> bool:
    try:
        from tools.interrupt import is_interrupted

        return bool(is_interrupted())
    except Exception:
        return False


def _safe_rest_failure(operation: str, exc: Exception) -> str:
    """Keep controlled REST diagnostics while suppressing arbitrary exceptions."""

    if isinstance(exc, rest_client.TinyFishRestError):
        return f"TinyFish REST {operation} failed: {exc}"
    return f"TinyFish REST {operation} failed ({type(exc).__name__})."


def _error_document(url: str, error: str) -> dict[str, Any]:
    return {
        "url": url,
        "title": "",
        "content": "",
        "raw_content": "",
        "error": error,
        "metadata": {"sourceURL": url},
    }


class TinyFishWebSearchProvider(_HermesWebSearchProvider):  # type: ignore[misc]
    """TinyFish Search and Fetch provider using API-key REST calls."""

    @property
    def name(self) -> str:
        return "tinyfish"

    @property
    def display_name(self) -> str:
        return "TinyFish"

    def is_available(self) -> bool:
        return bool(_api_key())

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def supports_crawl(self) -> bool:
        return False

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": "TinyFish",
            "badge": "free search/fetch",
            "tag": "TinyFish Search and Fetch via API key.",
            "env_vars": [
                {
                    "key": "TINYFISH_API_KEY",
                    "prompt": "TinyFish API key",
                    "url": API_KEY_URL,
                }
            ],
        }

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        if _is_interrupted():
            return {"success": False, "error": "Interrupted"}
        api_key = _api_key()
        if not api_key:
            return {"success": False, "error": MISSING_KEY_ERROR}
        try:
            raw = rest_client.search(query, api_key=api_key, **search_options())
            return normalize_search_response(raw, limit=limit)
        except Exception as exc:  # noqa: BLE001 - controlled failure envelope
            logger.warning("TinyFish REST search failed (%s)", type(exc).__name__)
            return {"success": False, "error": _safe_rest_failure("search", exc)}

    def extract(self, urls: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        if _is_interrupted():
            return [_error_document(url, "Interrupted") for url in urls]
        api_key = _api_key()
        if not api_key:
            return [_error_document(url, MISSING_KEY_ERROR) for url in urls]
        output_format = str(
            kwargs.get("format")
            or kwargs.get("output_format")
            or default_fetch_format()
        )
        options = fetch_options()
        documents: list[dict[str, Any]] = []
        # The Fetch API caps a request at 10 URLs; oversized batches 400.
        for start in range(0, len(urls), rest_client.FETCH_MAX_URLS):
            chunk = urls[start : start + rest_client.FETCH_MAX_URLS]
            try:
                raw = rest_client.fetch(
                    chunk,
                    api_key=api_key,
                    output_format=output_format,
                    **options,
                )
                documents.extend(normalize_fetch_documents(raw, fallback_urls=chunk))
            except Exception as exc:  # noqa: BLE001 - controlled failure envelope
                logger.warning("TinyFish REST fetch failed (%s)", type(exc).__name__)
                documents.extend(
                    _error_document(url, _safe_rest_failure("fetch", exc))
                    for url in chunk
                )
        return documents
