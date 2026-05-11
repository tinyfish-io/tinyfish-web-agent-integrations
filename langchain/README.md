# TinyFish Web Agent for LangChain

![Powered by TinyFish](https://img.shields.io/badge/Powered%20by-TinyFish-blue)

This package provides a LangChain Tool to run the TinyFish Web Agent directly within your LangChain Agents and Workflows.

TinyFish is a platform for executing complex, goal-oriented tasks on the live web. Unlike traditional scrapers or local browser automation, TinyFish uses a fleet of remote, AI-powered web agents that can navigate complex sites, handle anti-bot protection, and return clean, structured JSON data.

## Installation

```bash
pip install langchain-tinyfish
```

## Configuration

1. Get your TinyFish API key from [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys).
2. Set it as an environment variable:

```bash
export TINYFISH_API_KEY="YOUR_API_KEY"
```

## Quick Start

Here is a simple example of how to use the TinyFish Web Agent to extract the current stock price of NVIDIA from Yahoo Finance.

```python
from langchain_tinyfish import TinyFishWebAutomation

tool = TinyFishWebAutomation()

result = tool.invoke({
    "url": "https://finance.yahoo.com/quote/NVDA/",
    "goal": "Extract the current stock price of NVIDIA",
})

print(result)
# Output: {"stock_price": 950.02}
```

### Search, Fetch, and Browser Sessions

The package also exposes SDK-backed tools for TinyFish Search, Fetch, and Browser sessions:

```python
from langchain_tinyfish import (
    TinyFishBrowserSession,
    TinyFishFetch,
    TinyFishSearch,
)

search = TinyFishSearch()
fetch = TinyFishFetch()
browser = TinyFishBrowserSession()

search_results = search.invoke({"query": "TinyFish Web Agent docs"})
page_content = fetch.invoke({"urls": ["https://docs.tinyfish.ai"], "format": "markdown"})
session = browser.invoke({"url": "https://example.com"})
```

### With a LangChain Agent

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_tinyfish import TinyFishFetch, TinyFishSearch, TinyFishWebAutomation

llm = ChatOpenAI(model="gpt-4o")
tools = [
    TinyFishWebAutomation(),
    TinyFishSearch(),
    TinyFishFetch(),
]
agent = create_react_agent(llm, tools)

result = agent.invoke({
    "messages": [("user", "Go to scrapeme.live/shop and extract the first 5 product names and prices")]
})

for message in result["messages"]:
    print(message.content)
```

### Stealth Mode + Proxy

For sites with bot protection (Cloudflare, CAPTCHAs, etc.):

```python
from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

tool = TinyFishWebAutomation(
    api_wrapper=TinyFishAPIWrapper(
        browser_profile="stealth",
        proxy_enabled=True,
        proxy_country_code="US",  # Also: GB, CA, DE, FR, JP, AU
    )
)
```

### Async Usage

```python
import asyncio
from langchain_tinyfish import TinyFishWebAutomation

async def main():
    tool = TinyFishWebAutomation()
    result = await tool.ainvoke({
        "url": "https://example.com",
        "goal": "Extract the page title",
    })
    print(result)

asyncio.run(main())
```

## Use Cases

- **AI Agent Enablement:** Give your AI agent the ability to perform deep research on the web.
- **Workflow Automation:** Monitor a competitor's pricing page and get a Slack notification when it changes.
- **Data Extraction:** Extract job postings, product details, or contact information into a structured format.

## Configuration Options

All parameters are set on the `TinyFishAPIWrapper`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | `$TINYFISH_API_KEY` | Your TinyFish API key |
| `browser_profile` | `"lite"` | `"lite"` (fast) or `"stealth"` (anti-detection) |
| `proxy_enabled` | `False` | Enable proxy routing |
| `proxy_country_code` | `"US"` | Proxy country: US, GB, CA, DE, FR, JP, AU |
| `timeout` | `300` | Request timeout in seconds |

```python
from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

wrapper = TinyFishAPIWrapper(
    api_key="sk-mino-...",
    browser_profile="stealth",
    timeout=600,
)
tool = TinyFishWebAutomation(api_wrapper=wrapper)
```

## Development

```bash
# Install package + dev dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run unit tests
make test

# Run linter
make lint

# Run integration tests (requires TINYFISH_API_KEY)
make integration_test
```

## Support

If you have any questions or need help, please reach out to [support@tinyfish.ai](mailto:support@tinyfish.ai) or join our [Discord community](https://discord.gg/agentql).
