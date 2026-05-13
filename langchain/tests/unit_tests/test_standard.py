"""Standard unit tests for TinyFish tool using langchain-tests."""

from __future__ import annotations

from typing import Any

from langchain_tests.unit_tests import ToolsUnitTests
from pydantic import SecretStr

from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation


class TestTinyFishToolStandard(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[TinyFishWebAutomation]:
        return TinyFishWebAutomation

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {
            "api_wrapper": TinyFishAPIWrapper(api_key=SecretStr("sk-fake-key")),
        }

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {
            "url": "https://example.com",
            "goal": "Extract the page title",
        }

    @property
    def init_from_env_params(
        self,
    ) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
        return (
            {"TINYFISH_API_KEY": "sk-test-from-env"},
            {},
            {},
        )
