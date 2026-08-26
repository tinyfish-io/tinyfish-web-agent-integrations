"""Hermes BrowserProvider implementation for TinyFish Browser sessions."""

from __future__ import annotations

import logging
import uuid
from typing import Any

try:
    from agent.browser_provider import BrowserProvider as _HermesBrowserProvider
except Exception:  # pragma: no cover - lets the package import outside Hermes

    class _HermesBrowserProvider:  # type: ignore[no-redef]
        pass


from . import rest_client
from .config import credit_policy, tinyfish_config
from .credit_policy import block_message
from .provider import API_KEY_URL, MISSING_KEY_ERROR, _api_key

logger = logging.getLogger(__name__)


class TinyFishBrowserProvider(_HermesBrowserProvider):  # type: ignore[misc]
    """TinyFish cloud browser backend for Hermes browser tools."""

    @property
    def name(self) -> str:
        return "tinyfish"

    @property
    def display_name(self) -> str:
        return "TinyFish"

    def is_available(self) -> bool:
        return bool(credit_policy("browser") in {"request", "allow"} and _api_key())

    def create_session(self, task_id: str) -> dict[str, object]:
        api_key = _api_key()
        if not api_key:
            raise ValueError(MISSING_KEY_ERROR)
        if credit_policy("browser") == "deny":
            raise ValueError(block_message("browser"))
        browser_cfg = tinyfish_config().get("browser") or {}
        timeout_seconds = None
        if isinstance(browser_cfg, dict) and browser_cfg.get("timeout_seconds") not in (
            None,
            "",
        ):
            try:
                timeout_seconds = int(browser_cfg["timeout_seconds"])
            except (TypeError, ValueError):
                timeout_seconds = None

        data = rest_client.create_browser_session(
            api_key=api_key, timeout_seconds=timeout_seconds
        )
        session_id = str(data.get("session_id") or data.get("id") or "")
        cdp_url = str(data.get("cdp_url") or data.get("cdpUrl") or "")
        if not session_id or not cdp_url:
            raise RuntimeError(
                "TinyFish Browser did not return session_id and cdp_url."
            )
        session_name = f"tinyfish_{task_id}_{uuid.uuid4().hex[:8]}"
        logger.info("Created TinyFish browser session")
        return {
            "session_name": session_name,
            "bb_session_id": session_id,
            "cdp_url": cdp_url,
            "features": {
                "tinyfish": True,
                "credit_policy": credit_policy("browser"),
                "base_url": str(data.get("base_url") or ""),
            },
        }

    def close_session(self, session_id: str) -> bool:
        # Hermes' BrowserProvider contract: close_session must never raise.
        try:
            api_key = _api_key()
            if not api_key:
                logger.warning("Cannot close TinyFish browser session: missing API key")
                return False
            return rest_client.close_browser_session(session_id, api_key=api_key)
        except Exception as exc:
            logger.debug("TinyFish browser close failed (%s)", type(exc).__name__)
            return False

    def emergency_cleanup(self, session_id: str) -> None:
        try:
            self.close_session(session_id)
        except Exception as exc:
            logger.debug(
                "TinyFish browser emergency cleanup failed (%s)", type(exc).__name__
            )

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": "TinyFish",
            "badge": "credit-gated",
            "tag": (
                "Remote browser sessions; each session consumes TinyFish credits. "
                "Default policy 'request' asks for approval per session."
            ),
            "env_vars": [
                {
                    "key": "TINYFISH_API_KEY",
                    "prompt": "TinyFish API key",
                    "url": API_KEY_URL,
                }
            ],
            "post_setup": "agent_browser",
        }
