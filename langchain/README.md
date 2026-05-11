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

## Demo App

A full-stack demo showing a multi-tool ReAct agent that combines TinyFish web automation with DuckDuckGo search. The agent can search the web to find URLs, then use TinyFish to extract structured data from those pages.

**Stack:** React + Tailwind + shadcn/ui frontend, FastAPI + LangGraph backend, SSE streaming. The demo uses [OpenRouter](https://openrouter.ai) to route LLM requests, so you can use any supported model (Claude, GPT-4o, etc.).

### Setup

```bash
cd demo-app

# Install frontend dependencies
npm install

# Install backend dependencies
pip install -e ../           # langchain-tinyfish
pip install -e ../demo-backend  # demo backend

# Configure environment
cp ../demo-backend/.env.example ../demo-backend/.env
# Edit .env with your actual keys:
#   OPENROUTER_API_KEY=sk-or-v1-...
#   TINYFISH_API_KEY=sk-mino-...
#   OPENROUTER_MODEL=anthropic/claude-haiku-4.5  (optional, defaults to openai/gpt-4o)
```

### Run

```bash
npm run dev
```

This starts both the backend (port 8000) and frontend (port 5173) concurrently. The backend logs color-coded tool calls and results to the terminal.

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
