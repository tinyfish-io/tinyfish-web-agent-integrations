"""TinyFish Agent tool for CrewAI.

Wraps the TinyFish Agent API (``POST https://agent.tinyfish.ai/v1/automation/run``),
which takes a natural-language goal and autonomously drives a real browser on a
target site to complete it and return structured results.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Type

from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, PrivateAttr

from ._client import TINYFISH_API_KEY_ENV, build_client, ensure_api_key, ensure_sdk_installed
from ._serde import attr, supported_kwargs


class TinyFishAgentToolInput(BaseModel):
    """Input schema for TinyFishAgentTool."""

    url: str = Field(..., description="Target website URL the agent should operate on.")
    goal: str = Field(
        ...,
        description=(
            "Natural-language instruction. Be specific about the exact fields to extract and "
            "the desired output format, e.g. 'Extract the first 5 product names and prices. "
            "Return JSON.'"
        ),
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional JSON Schema (object) constraining the structured result.",
    )
    browser_profile: Optional[str] = Field(
        None,
        description="Browser runtime mode: 'lite' (default) or 'stealth' for bot-protected sites.",
    )
    use_proxy: bool = Field(
        False,
        description=(
            "Route the run through TinyFish proxy infrastructure (helps with geo/anti-bot)."
        ),
    )
    proxy_country: Optional[str] = Field(
        None,
        description="Proxy country when use_proxy is true: US, GB, CA, DE, FR, JP, or AU.",
    )
    use_profile: bool = Field(
        False,
        description=(
            "Reuse the default saved Browser Context Profile (logged-in state) for this run."
        ),
    )
    profile_id: Optional[str] = Field(
        None,
        description="Specific Browser Context Profile id. Requires use_profile=true.",
    )
    use_vault: bool = Field(
        False,
        description="Allow TinyFish to log in using your connected password-manager credentials.",
    )
    credential_item_ids: Optional[List[str]] = Field(
        None,
        description="Scope the run to specific vault credential URIs. Requires use_vault=true.",
    )


class TinyFishAgentTool(BaseTool):
    """Run a goal-based web automation on a live site via TinyFish's web agent."""

    name: str = "TinyFish Web Agent"
    description: str = (
        "Give TinyFish a natural-language goal and a target URL, and it autonomously drives a real "
        "browser to complete the task (navigate, click, fill forms, extract data) and returns a "
        "structured result. Use this for multi-step workflows that plain search/fetch can't do, "
        "such as logging in, filling forms, or extracting data behind interactions."
    )
    args_schema: Type[BaseModel] = TinyFishAgentToolInput
    package_dependencies: List[str] = ["tinyfish"]
    env_vars: List[EnvVar] = [
        EnvVar(
            name=TINYFISH_API_KEY_ENV,
            description="TinyFish API key from https://agent.tinyfish.ai/api-keys",
            required=True,
        ),
    ]

    _api_key: Optional[str] = PrivateAttr(default=None)
    _client: Any = PrivateAttr(default=None)

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        ensure_sdk_installed()
        ensure_api_key(api_key)
        self._api_key = api_key

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = build_client(self._api_key)
        return self._client

    def _build_kwargs(
        self,
        url: str,
        goal: str,
        output_schema: Optional[Dict[str, Any]],
        browser_profile: Optional[str],
        use_proxy: bool,
        proxy_country: Optional[str],
        use_profile: bool,
        profile_id: Optional[str],
        use_vault: bool,
        credential_item_ids: Optional[List[str]],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"url": url, "goal": goal}
        if output_schema is not None:
            kwargs["output_schema"] = output_schema

        if browser_profile is not None:
            kwargs["browser_profile"] = _coerce_browser_profile(browser_profile)

        if use_proxy:
            kwargs["proxy_config"] = _coerce_proxy_config(proxy_country)

        if use_profile:
            kwargs["use_profile"] = True
            if profile_id is not None:
                kwargs["profile_id"] = profile_id
        if use_vault:
            kwargs["use_vault"] = True
            if credential_item_ids:
                kwargs["credential_item_ids"] = credential_item_ids

        return kwargs

    def _run(
        self,
        url: str,
        goal: str,
        output_schema: Optional[Dict[str, Any]] = None,
        browser_profile: Optional[str] = None,
        use_proxy: bool = False,
        proxy_country: Optional[str] = None,
        use_profile: bool = False,
        profile_id: Optional[str] = None,
        use_vault: bool = False,
        credential_item_ids: Optional[List[str]] = None,
        **_: Any,
    ) -> str:
        kwargs = self._build_kwargs(
            url,
            goal,
            output_schema,
            browser_profile,
            use_proxy,
            proxy_country,
            use_profile,
            profile_id,
            use_vault,
            credential_item_ids,
        )

        client = self._get_client()
        try:
            run = client.agent.run(**supported_kwargs(client.agent.run, kwargs))
        except Exception as exc:  # noqa: BLE001 - surface a clear message to the agent
            return f"TinyFish Agent run failed: {exc}"

        status = _status_str(attr(run, "status"))
        payload: Dict[str, Any] = {
            "run_id": attr(run, "run_id"),
            "status": status,
            "num_of_steps": attr(run, "num_of_steps"),
            "result": attr(run, "result"),
        }
        error = attr(run, "error")
        if error is not None:
            payload["error"] = {
                "code": attr(error, "code"),
                "message": attr(error, "message"),
                "category": attr(error, "category"),
            }
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return await asyncio.to_thread(self._run, *args, **kwargs)


def _coerce_browser_profile(value: str) -> Any:
    """Return the SDK BrowserProfile enum when available, else the raw string."""
    try:
        from tinyfish import BrowserProfile  # type: ignore

        return BrowserProfile(value.lower())
    except Exception:  # noqa: BLE001 - SDK may accept plain strings
        return value


def _coerce_proxy_config(country: Optional[str]) -> Any:
    """Build a ProxyConfig via the SDK when available, else a plain dict."""
    try:
        from tinyfish import ProxyConfig, ProxyCountryCode  # type: ignore

        if country:
            return ProxyConfig(enabled=True, country_code=ProxyCountryCode(country.upper()))
        return ProxyConfig(enabled=True)
    except Exception:  # noqa: BLE001 - fall back to documented JSON body
        config: Dict[str, Any] = {"enabled": True, "type": "tetra"}
        if country:
            config["country_code"] = country.upper()
        return config


def _status_str(status: Any) -> Any:
    """Normalize a RunStatus enum (or string) into a plain string."""
    if status is None:
        return None
    return getattr(status, "value", status)
