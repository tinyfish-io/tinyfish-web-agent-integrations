"""Shared helpers for the TinyFish CrewAI tools.

Centralizes the optional-dependency handling, environment-variable checks, and
SDK client construction so every tool stays small and consistent. TinyFish is
kept an *optional* dependency (lazy import) per the crewai-tools conventions, so
the base install stays light and the error message is actionable.
"""

from __future__ import annotations

import os
from typing import Any, Optional

#: Environment variable the TinyFish SDK reads automatically.
TINYFISH_API_KEY_ENV = "TINYFISH_API_KEY"

#: Integration tag the TinyFish SDK forwards for request attribution.
TF_API_INTEGRATION_ENV = "TF_API_INTEGRATION"
_INTEGRATION_NAME = "crewai"

_INSTALL_HINT = (
    "Missing optional dependency 'tinyfish'. Install it with:\n"
    "  uv add crewai-tinyfish --extra tinyfish\n"
    "or\n"
    "  pip install tinyfish\n"
)

_MISSING_KEY_HINT = (
    f"Environment variable {TINYFISH_API_KEY_ENV} is required. "
    "Create a key at https://agent.tinyfish.ai/api-keys and export it:\n"
    f'  export {TINYFISH_API_KEY_ENV}="your_api_key_here"'
)


def ensure_integration_tag() -> None:
    """Tag SDK requests as originating from this integration (for attribution).

    Uses ``setdefault`` so an explicit ``TF_API_INTEGRATION`` set by the caller
    always wins.
    """
    os.environ.setdefault(TF_API_INTEGRATION_ENV, _INTEGRATION_NAME)


def ensure_sdk_installed() -> None:
    """Raise an actionable ImportError if the ``tinyfish`` SDK is missing."""
    try:
        import tinyfish  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised via install hint
        raise ImportError(_INSTALL_HINT) from exc


def ensure_api_key(api_key: Optional[str] = None) -> None:
    """Raise a clear ValueError if no API key is available.

    A key is considered available if it is passed explicitly (``api_key``) or
    present in the ``TINYFISH_API_KEY`` environment variable.
    """
    if api_key:
        return
    if not os.environ.get(TINYFISH_API_KEY_ENV):
        raise ValueError(_MISSING_KEY_HINT)


def build_client(api_key: Optional[str] = None) -> Any:
    """Construct an authenticated ``tinyfish.TinyFish`` client.

    The SDK reads ``TINYFISH_API_KEY`` from the environment automatically; an
    explicit ``api_key`` takes precedence when provided.
    """
    ensure_sdk_installed()
    ensure_api_key(api_key)
    ensure_integration_tag()

    from tinyfish import TinyFish  # local import keeps base install light

    if api_key:
        return TinyFish(api_key=api_key)
    return TinyFish()
