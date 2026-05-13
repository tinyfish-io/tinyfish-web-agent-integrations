"""Integration tests for TinyFish LangChain tool.

These tests make real API calls and require TINYFISH_API_KEY to be set.
They are skipped automatically if the key is not available.
"""

from __future__ import annotations

import json
import os

import pytest

from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

skip_no_key = pytest.mark.skipif(
    not os.environ.get("TINYFISH_API_KEY"),
    reason="TINYFISH_API_KEY not set",
)


@skip_no_key
class TestAPIWrapperIntegration:
    """Integration tests for TinyFishAPIWrapper."""

    def test_sync_extraction(self) -> None:
        wrapper = TinyFishAPIWrapper()
        result = wrapper.run(
            url="https://scrapeme.live/shop/",
            goal="Extract the first 2 product names and prices. Return as JSON.",
        )
        parsed = json.loads(result)
        assert parsed is not None

    @pytest.mark.asyncio
    async def test_async_extraction(self) -> None:
        wrapper = TinyFishAPIWrapper()
        result = await wrapper.arun(
            url="https://scrapeme.live/shop/",
            goal="Extract the first 2 product names and prices. Return as JSON.",
        )
        parsed = json.loads(result)
        assert parsed is not None


@skip_no_key
class TestToolIntegration:
    """Integration tests for the TinyFishWebAutomation tool."""

    def test_tool_invoke(self) -> None:
        tool = TinyFishWebAutomation()
        result = tool.invoke(
            {
                "url": "https://scrapeme.live/shop/",
                "goal": "Extract the first product name on the page.",
            }
        )
        assert isinstance(result, str)
        assert len(result) > 0
