# langchain-tinyfish

[![PyPI version](https://img.shields.io/pypi/v/langchain-tinyfish)](https://pypi.org/project/langchain-tinyfish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[TinyFish](https://tinyfish.ai) gives AI agents every level of web access through one platform. Four primitives, each built for a different layer:

- **Search**: live web results, structured and ready for LLM consumption. Free.
- **Fetch**: renders pages in a real browser, returns clean markdown, HTML, or JSON. Token-efficient for LLM pipelines. Free.
- **Web Agent**: autonomous agents that navigate, authenticate, and extract from real websites. Uses credits.
- **Browser**: remote Chromium sessions with full CDP access. Bring your own Playwright or Puppeteer scripts. Uses credits.

This package wraps all four as LangChain tools. [Get your API key ->](https://agent.tinyfish.ai/api-keys)

## Installation

```bash
pip install langchain-tinyfish
```

```bash
export TINYFISH_API_KEY="your-api-key"
```

## Tools

All four tools can be used standalone or passed to a LangChain agent:

```python
from langchain_tinyfish import (
    TinyFishSearch,
    TinyFishFetch,
    TinyFishWebAutomation,
    TinyFishBrowserSession,
)
```

Tool calls return strings. Successful responses are JSON strings produced from the TinyFish SDK response.

### Search

Search the web and get structured results with titles, snippets, and URLs. Free, no credits required.

```python
from langchain_tinyfish import TinyFishSearch

search = TinyFishSearch()
results = search.invoke({
    "query": "latest LLM benchmarks 2025",
    "location": "US",
})
print(results)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `query` | Yes | Search query |
| `location` | No | Optional location/country scope, such as `"US"` |
| `language` | No | Optional language code, such as `"en"` |

### Fetch

Extract clean content from up to 10 URLs at once. Returns markdown, HTML, or JSON. Free, no credits required.

```python
from langchain_tinyfish import TinyFishFetch

fetch = TinyFishFetch()
content = fetch.invoke({
    "urls": ["https://docs.tinyfish.ai"],
    "format": "markdown",
    "links": True,
})
print(content)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `urls` | Yes | List of 1-10 URLs |
| `format` | No | `"markdown"`, `"html"`, or `"json"`; defaults to `"markdown"` |
| `links` | No | Include extracted page links |
| `image_links` | No | Include extracted image links |

### Web Agent

Run complex, goal-oriented tasks on live websites. TinyFish handles navigation, anti-bot protection, and returns structured JSON. Uses credits.

```python
from langchain_tinyfish import TinyFishWebAutomation

agent_tool = TinyFishWebAutomation()
result = agent_tool.invoke({
    "url": "https://finance.yahoo.com/quote/NVDA/",
    "goal": "Extract the current stock price of NVIDIA",
})
print(result)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes | Starting URL for the automation |
| `goal` | Yes | Natural-language instructions for what to do and what to return |

When `TinyFishWebAutomation` runs inside a LangGraph execution context, it uses TinyFish's streaming endpoint and emits progress events through LangGraph's stream writer. Outside LangGraph, it falls back to a blocking TinyFish run.

### Browser Session

Launch a remote Chromium browser and get a CDP (Chrome DevTools Protocol) URL to connect with Playwright or Puppeteer. Sessions include remote browser infrastructure for direct CDP control. Uses credits.

```python
from langchain_tinyfish import TinyFishBrowserSession

browser = TinyFishBrowserSession()
session = browser.invoke({
    "url": "https://example.com",
    "timeout_seconds": 300,
})
print(session)
# Returns a JSON string with: {"session_id": "...", "cdp_url": "wss://...", "base_url": "https://..."}
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | No | Optional target URL to open when the browser session starts |
| `timeout_seconds` | No | Optional inactivity timeout for the browser session |

## With a LangChain Agent

Give your agent access to multiple TinyFish tools. The agent decides which primitive to use based on the task.

Install the optional agent dependencies:

```bash
pip install langchain langchain-openai langgraph
```

```python
from langchain.agents import create_agent
from langchain_tinyfish import (
    TinyFishSearch,
    TinyFishFetch,
    TinyFishWebAutomation,
)

tools = [TinyFishSearch(), TinyFishFetch(), TinyFishWebAutomation()]
agent = create_agent(
    model="openai:gpt-5.5",
    tools=tools,
)

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Find the top 3 results for 'best open source LLMs' and extract the full content of the first result",
        }
    ]
})

for message in result["messages"]:
    print(message.content)
```

You can also pass the TinyFish tools to LangGraph's prebuilt agents, including `langgraph.prebuilt.create_react_agent`, if your application already uses LangGraph directly.

## Stealth Mode and Proxies

For Web Agent runs on sites with bot protection (Cloudflare, CAPTCHAs, etc.), configure stealth browsing and geo-targeted proxies:

```python
from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

wrapper = TinyFishAPIWrapper(
    browser_profile="stealth",
    proxy_enabled=True,
    proxy_country_code="US",  # Also: GB, CA, DE, FR, JP, AU
)

agent_tool = TinyFishWebAutomation(api_wrapper=wrapper)
```

`browser_profile` and proxy settings are currently applied by `TinyFishWebAutomation`. Search, Fetch, and Browser Session tools can share the same wrapper for API key and timeout configuration, but they do not pass Web Agent browser profile or proxy options.

## Configuration

All tools share a `TinyFishAPIWrapper` for API key and timeout configuration:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | `$TINYFISH_API_KEY` | Your TinyFish API key |
| `browser_profile` | `"lite"` | Web Agent browser profile: `"lite"` or `"stealth"` |
| `proxy_enabled` | `False` | Enable proxy routing for Web Agent runs |
| `proxy_country_code` | `"US"` | Proxy exit country for Web Agent runs: US, GB, CA, DE, FR, JP, AU |
| `timeout` | `300` | Request/poll timeout in seconds |

```python
from langchain_tinyfish import TinyFishAPIWrapper, TinyFishWebAutomation

wrapper = TinyFishAPIWrapper(
    browser_profile="stealth",
    timeout=600,
)
tool = TinyFishWebAutomation(api_wrapper=wrapper)
```

## Parallel Web Agents

Every Web Agent run gets its own isolated remote browser. Run multiple agents concurrently with `asyncio.gather`:

```python
import asyncio
from langchain_tinyfish import TinyFishWebAutomation

async def main():
    agent = TinyFishWebAutomation()

    tasks = [
        agent.ainvoke({"url": "https://example.com/page-1", "goal": "Extract the main heading"}),
        agent.ainvoke({"url": "https://example.com/page-2", "goal": "Extract the main heading"}),
        agent.ainvoke({"url": "https://example.com/page-3", "goal": "Extract the main heading"}),
    ]

    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)

asyncio.run(main())
```

## Async Usage

All tools support async with `ainvoke`:

```python
import asyncio
from langchain_tinyfish import TinyFishSearch, TinyFishFetch

async def main():
    search = TinyFishSearch()
    fetch = TinyFishFetch()

    results = await search.ainvoke({"query": "TinyFish web agent"})
    content = await fetch.ainvoke({
        "urls": ["https://tinyfish.ai"],
        "format": "markdown",
    })

    print(results)
    print(content)

asyncio.run(main())
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

## Resources

- [TinyFish Documentation](https://docs.tinyfish.ai)
- [TinyFish Website](https://tinyfish.ai)
- [API Keys](https://agent.tinyfish.ai/api-keys)
- [Discord Community](https://discord.com/invite/tinyfish)

## Support

Questions or issues? Reach out at [support@tinyfish.ai](mailto:support@tinyfish.ai) or join our [Discord](https://discord.com/invite/tinyfish).
