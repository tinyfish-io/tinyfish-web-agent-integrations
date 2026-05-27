"""Standard integration tests for TinyFish tool using langchain-tests."""

from __future__ import annotations

import os
from typing import Any

import pytest
from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_tinyfish import TinyFishWebAutomation

skip_no_key = pytest.mark.skipif(
    not os.environ.get("TINYFISH_API_KEY"),
    reason="TINYFISH_API_KEY not set",
)


@skip_no_key
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
