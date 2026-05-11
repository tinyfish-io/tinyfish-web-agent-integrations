"""Standard integration tests for TinyFish tool using langchain-tests."""

from __future__ import annotations

from typing import Any

from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_tinyfish import TinyFishWebAutomation


class TestTinyFishToolIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[TinyFishWebAutomation]:
        return TinyFishWebAutomation

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {
            "url": "https://scrapeme.live/shop/",
            "goal": "Extract the first product name on the page",
        }
