"""crewai-tinyfish: official TinyFish tools for CrewAI agents.

Exposes one CrewAI ``BaseTool`` per TinyFish API surface:

- :class:`TinyFishSearchTool`   — Search API: structured ranked web results.
- :class:`TinyFishFetchTool`    — Fetch API: clean extracted page content.
- :class:`TinyFishAgentTool`    — Agent API: goal-based web automation on live sites.
- :class:`TinyFishBrowserSessionTool` — Browser API: remote CDP browser sessions.

All tools read the ``TINYFISH_API_KEY`` environment variable (get one at
https://agent.tinyfish.ai/api-keys).
"""

from .tinyfish_agent_tool import TinyFishAgentTool, TinyFishAgentToolInput
from .tinyfish_browser_tool import TinyFishBrowserSessionTool, TinyFishBrowserSessionToolInput
from .tinyfish_fetch_tool import TinyFishFetchTool, TinyFishFetchToolInput
from .tinyfish_search_tool import TinyFishSearchTool, TinyFishSearchToolInput

__version__ = "0.1.0"

__all__ = [
    "TinyFishSearchTool",
    "TinyFishSearchToolInput",
    "TinyFishFetchTool",
    "TinyFishFetchToolInput",
    "TinyFishAgentTool",
    "TinyFishAgentToolInput",
    "TinyFishBrowserSessionTool",
    "TinyFishBrowserSessionToolInput",
]
