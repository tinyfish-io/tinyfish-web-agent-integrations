"""TinyFish CrewAI tool — synchronous browser-automation agent.

Single-tool package. Talks to the TinyFish agent endpoint via raw HTTP
so it installs cleanly on Python 3.10+ in any Crew Studio sandbox.
"""

from __future__ import annotations

import json
import os
from typing import Any, List, Literal, Optional, Type

import requests
from crewai.tools import BaseTool, EnvVar
from pydantic import BaseModel, Field, field_validator

_BASE_URL = "https://agent.tinyfish.ai"
_AGENT_PATH = "/v1/automation/run"
_TIMEOUT_SECONDS = 300  # automation runs can take minutes
_INTEGRATION_NAME = "crew-ai"

_VALID_PROXY_COUNTRIES = {"US", "GB", "CA", "DE", "FR", "JP", "AU"}


class TinyfishWebAgentInput(BaseModel):
    """Input schema for a synchronous TinyFish browser automation."""

    url: str = Field(..., description="Target website URL to automate.")
    goal: str = Field(
        ...,
        description=(
            "Natural language description of what to accomplish on the website "
            "(e.g., 'extract product names and prices', 'fill the contact form')."
        ),
    )
    browser_profile: Literal["lite", "stealth"] = Field(
        default="lite",
        description=(
            'Browser execution mode. "lite" is fast for standard sites; '
            '"stealth" enables anti-detection for sites with bot protection.'
        ),
    )

    @field_validator("url")
    @classmethod
    def _check_url_scheme(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


_ENV_VARS: List[EnvVar] = [
    EnvVar(
        name="TINYFISH_API_KEY",
        description=(
            "TinyFish Web Agent API key. "
            "Get one at https://agent.tinyfish.ai/api-keys"
        ),
        required=True,
    ),
]


class TinyfishWebAgent(BaseTool):
    """Run a TinyFish browser automation synchronously and return the result."""

    name: str = "Tinyfish Web Agent"
    description: str = (
        "Automate any website using natural language. Provide a URL and a "
        "goal describing what to accomplish — extract data, fill forms, click "
        "buttons, navigate pages, and more. Waits for completion and returns "
        "the structured JSON result, including status, run_id, and any "
        "extracted data."
    )
    args_schema: Type[BaseModel] = TinyfishWebAgentInput
    package_dependencies: List[str] = ["requests"]
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("TINYFISH_API_KEY"),
        description="TinyFish API key (overrides env var if provided).",
        json_schema_extra={"required": False},
    )
    proxy_country: Optional[str] = Field(
        default=None,
        description=(
            "ISO country code for proxy routing (US, GB, CA, DE, FR, JP, AU)."
        ),
        json_schema_extra={"required": False},
    )
    env_vars: List[EnvVar] = _ENV_VARS

    def _run(
        self,
        url: str,
        goal: str,
        browser_profile: str = "lite",
    ) -> str:
        key = self.api_key or os.environ.get("TINYFISH_API_KEY")
        if not key:
            return (
                "Error: TINYFISH_API_KEY is not set. "
                "Pass api_key when instantiating the tool or set the "
                "TINYFISH_API_KEY environment variable. "
                "Get a key at https://agent.tinyfish.ai/api-keys"
            )

        body: dict[str, Any] = {
            "url": url,
            "goal": goal,
            "browser_profile": browser_profile,
        }
        if self.proxy_country:
            if self.proxy_country not in _VALID_PROXY_COUNTRIES:
                return f"Error: Invalid proxy country: {self.proxy_country!r}"
            body["proxy_config"] = {
                "enabled": True,
                "country_code": self.proxy_country,
            }

        headers = {
            "X-API-Key": key,
            "Content-Type": "application/json",
            "X-TF-Integration": _INTEGRATION_NAME,
        }

        try:
            response = requests.post(
                _BASE_URL + _AGENT_PATH,
                headers=headers,
                json=body,
                timeout=_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            return f"Error: HTTP request failed — {exc}"

        if response.status_code == 401:
            return "Error: Invalid or missing API key."
        if response.status_code == 403:
            return "Error: Insufficient credits or no active subscription."
        if response.status_code == 429:
            return "Error: Rate limit exceeded — retry after a moment."
        if response.status_code >= 400:
            snippet = (response.text or "No body")[:200]
            return f"Error: HTTP {response.status_code} — {snippet}"

        try:
            return json.dumps(response.json())
        except ValueError:
            return response.text or "Empty response from TinyFish."
