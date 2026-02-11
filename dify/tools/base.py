from typing import Any

import httpx

from tools.constants import API_BASE_URL


class TinyfishMixin:
    """Mixin for TinyFish tools with shared API request logic."""

    @property
    def _api_headers(self) -> dict[str, str]:
        return {"X-API-Key": self.runtime.credentials["api_key"]}

    def _tf_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Make an authenticated request to the TinyFish API."""
        response = httpx.request(
            method,
            f"{API_BASE_URL}{path}",
            headers=self._api_headers,
            params=params,
            json=json,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def _build_automation_payload(
        self, tool_parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Build the common payload for automation run endpoints."""
        payload: dict[str, Any] = {
            "url": tool_parameters["url"],
            "goal": tool_parameters["goal"],
            "browser_profile": tool_parameters.get("browser_profile", "lite"),
        }

        if tool_parameters.get("proxy_enabled"):
            proxy_config: dict[str, Any] = {"enabled": True}
            if tool_parameters.get("proxy_country_code"):
                proxy_config["country_code"] = tool_parameters["proxy_country_code"]
            payload["proxy_config"] = proxy_config

        return payload
