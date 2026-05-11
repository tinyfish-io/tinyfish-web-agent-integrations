"""Build the multi-tool ReAct agent."""

import logging

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import SecretStr

from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

from .config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful AI research assistant with access to two tools:\n\n"
    "1. **tinyfish_web_automation** — Browse a specific URL and interact with it: "
    "extract data, fill forms, click buttons, scrape content. "
    "Requires a URL and a goal describing what to do.\n"
    "2. **duckduckgo_search** — Search the web for current information. "
    "Pass a search query string.\n\n"
    "Strategy:\n"
    "- Use duckduckgo_search when you need to find URLs, look up facts, "
    "or discover what's available on the web.\n"
    "- Use tinyfish_web_automation when you have a specific URL and need to "
    "extract structured data or perform actions on the page.\n"
    "- You can chain tools: search first to find the right page, "
    "then use TinyFish to extract detailed data from it.\n"
    "- Always provide a clear, specific goal to TinyFish — describe exactly "
    "what data you want or what actions to perform."
)


def build_agent(settings: Settings):
    """Create a ReAct agent with TinyFish and DuckDuckGo tools."""
    llm = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
        streaming=True,
    )

    tinyfish = TinyFishWebAutomation(
        api_wrapper=TinyFishAPIWrapper(
            api_key=SecretStr(settings.tinyfish_api_key),
        )
    )
    search = DuckDuckGoSearchRun()

    return create_react_agent(
        model=llm,
        tools=[tinyfish, search],
        prompt=SYSTEM_PROMPT,
    )
