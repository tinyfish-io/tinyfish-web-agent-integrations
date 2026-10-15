# TinyFish Web Agent Tools for AG2

[TinyFish Web Agent](https://docs.tinyfish.ai) toolkit for [AG2](https://github.com/ag2ai/ag2) — automate any website using natural language.

This toolkit lets AG2 agents search the web, fetch page contents, open remote browser sessions, navigate real websites, extract structured data, fill forms, click buttons, and execute multi-step workflows described in plain English.

## Installation

```bash
pip install ag2[tinyfish]
```

## Setup

Get your API key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys) and set it as an environment variable:

```bash
export TINYFISH_API_KEY=sk-tinyfish-...
```

## Quick Start

```python
from autogen import ConversableAgent, LLMConfig
from autogen.tools.experimental import TinyFishToolkit

llm_config = LLMConfig(config_list=[{"model": "gpt-4o", "api_key": "..."}])

toolkit = TinyFishToolkit()

assistant = ConversableAgent(
    name="assistant",
    llm_config=llm_config,
    system_message="You can browse the web using the TinyFish tools.",
)

user_proxy = ConversableAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    llm_config=False,
)

# Register all tools at once
toolkit.register_for_llm(assistant)
toolkit.register_for_execution(user_proxy)

user_proxy.initiate_chat(
    assistant,
    message="Extract the top 3 product names and prices from https://scrapeme.live/shop/",
    max_turns=4,
)
```

## Tools

The toolkit provides 7 tools:

| Tool | Endpoint | Description |
|------|----------|-------------|
| `tinyfish_web_agent` | `POST /v1/automation/run` | Run automation synchronously, wait for result |
| `tinyfish_web_agent_async` | `POST /v1/automation/run-async` | Queue automation, return run ID immediately |
| `tinyfish_get_run` | `GET /v1/runs/{id}` | Check status and get result of a run |
| `tinyfish_list_runs` | `GET /v1/runs` | List recent runs with optional filtering |
| `tinyfish_search` | `POST /v1/search` | Search the web and return ranked results |
| `tinyfish_fetch` | `POST /v1/fetch` | Fetch readable page contents from one or more URLs |
| `tinyfish_create_browser_session` | `POST /v1/browser/sessions` | Create a remote browser session |

### When to Use Which

- **`tinyfish_search`** — Discover relevant URLs before deciding which pages to inspect.
- **`tinyfish_fetch`** — Extract readable content from known URLs or search results.
- **`tinyfish_web_agent`** — Quick tasks under 60 seconds. Simplest option.
- **`tinyfish_web_agent_async`** + **`tinyfish_get_run`** — Long-running tasks, batch processing, or when you want the agent to do other work while waiting.
- **`tinyfish_list_runs`** — Review past automations, check what's running.
- **`tinyfish_create_browser_session`** — Start a browser session when direct browser control is needed.

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `None` | TinyFish API key. Reads from `TINYFISH_API_KEY` env var if not provided. |
| `browser_profile` | `str` | `"lite"` | `"lite"` for standard sites, `"stealth"` for bot-protected sites. |
| `proxy_country` | `str` | `None` | Route through a country: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU`. |

### Stealth Mode + Proxy

For sites with Cloudflare, CAPTCHAs, or other bot protection:

```python
toolkit = TinyFishToolkit(browser_profile="stealth", proxy_country="US")
```

## Writing Good Goals

```python
# Specific extraction
"Extract all product names, prices, and stock status. Return as JSON array."

# Multi-step workflow
"1. Click 'Load More' 3 times  2. Extract all product cards  3. Return as JSON"

# Form filling
"Fill the contact form with name 'John Doe' and email 'john@example.com', then click Submit"
```

## Example Prompts

```text
Search for the TinyFish Web Agent docs and fetch the most relevant result.

Extract the top 3 product names and prices from https://scrapeme.live/shop/

Scrape the first 5 headlines from https://news.ycombinator.com

Go to https://books.toscrape.com and extract all books with their titles and prices
```

## Contributing to AG2

This tool is intended to be contributed to the AG2 repository at [`autogen/tools/experimental/tinyfish/`](https://github.com/ag2ai/ag2). The dependency would be added to AG2's `pyproject.toml`:

```toml
[project.optional-dependencies]
tinyfish = ["tinyfish>=0.2.5,<1"]
```

## Resources

- [TinyFish Docs](https://docs.tinyfish.ai)
- [AG2 Docs](https://docs.ag2.ai)
- [AG2 Tool Contributor Guide](https://docs.ag2.ai/docs/contributor-guide/building/creating-a-tool)
- [API Keys](https://agent.tinyfish.ai/api-keys)
