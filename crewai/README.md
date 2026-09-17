# crewai-tinyfish

[![PyPI version](https://img.shields.io/pypi/v/crewai-tinyfish)](https://pypi.org/project/crewai-tinyfish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[TinyFish](https://tinyfish.ai) gives AI agents every level of web access through one platform. Four primitives, each built for a different layer:

- **Search**: live web results, structured and ready for LLM consumption.
- **Fetch**: renders pages in a real browser, returns clean markdown, HTML, or JSON. Token-efficient for LLM pipelines.
- **Web Agent**: autonomous agents that navigate, authenticate, and extract from real websites.
- **Browser**: remote Chromium sessions with full CDP access. Bring your own Playwright or Puppeteer scripts.

This package wraps all four as CrewAI tools (`BaseTool`). [Get your API key ->](https://agent.tinyfish.ai/api-keys)

## Installation

```bash
pip install "crewai-tinyfish[tinyfish]"
```

```bash
export TINYFISH_API_KEY="your-api-key"
```

The `tinyfish` extra pulls in the official TinyFish Python SDK. It is kept optional so the base install stays light — the tools lazy-import it and raise a clear error if it is missing.

## Tools

All four tools can be used standalone or passed to a CrewAI agent:

```python
from crewai_tinyfish import (
    TinyFishSearchTool,
    TinyFishFetchTool,
    TinyFishAgentTool,
    TinyFishBrowserSessionTool,
)
```

Tool calls return strings. Successful responses are JSON strings produced from the TinyFish SDK response.

### Search

Search the web and get structured results with titles, snippets, and URLs.

```python
from crewai_tinyfish import TinyFishSearchTool

search = TinyFishSearchTool()
results = search.run(query="latest LLM benchmarks 2025", location="US")
print(results)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `query` | Yes | Search query |
| `location` | No | Optional location/country scope, such as `"US"` |
| `language` | No | Optional language code, such as `"en"` |
| `page` | No | Zero-indexed result page for pagination (0-10) |
| `max_results` | No | Maximum number of results to return; 1-50, default 10 |

### Fetch

Extract clean content from up to 10 URLs at once. Returns markdown, HTML, or JSON.

```python
from crewai_tinyfish import TinyFishFetchTool

fetch = TinyFishFetchTool()
content = fetch.run(urls=["https://docs.tinyfish.ai"], format="markdown", links=True)
print(content)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `urls` | Yes | List of 1-10 URLs |
| `format` | No | `"markdown"`, `"html"`, or `"json"`; defaults to `"markdown"` |
| `links` | No | Include extracted page links |
| `image_links` | No | Include extracted image links |
| `ttl` | No | Cache freshness tolerance in seconds; `0` forces a live fetch |
| `max_chars_per_url` | No | Truncate each page's extracted text to N characters |

### Web Agent

Run complex, goal-oriented tasks on live websites. TinyFish handles navigation, anti-bot protection, and returns structured JSON.

```python
from crewai_tinyfish import TinyFishAgentTool

agent_tool = TinyFishAgentTool()
result = agent_tool.run(
    url="https://finance.yahoo.com/quote/NVDA/",
    goal="Extract the current stock price of NVIDIA",
)
print(result)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes | Target website URL; use `http://` or `https://` |
| `goal` | Yes | Natural-language instructions for what to do and what to return |
| `output_schema` | No | Optional JSON Schema constraining the structured result |
| `browser_profile` | No | `"lite"` (default, fast) or `"stealth"` (anti-detection for bot-protected sites) |
| `use_proxy` | No | Route the run through TinyFish proxy infrastructure |
| `proxy_country` | No | Proxy exit country when `use_proxy` is set: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU` |
| `use_profile` | No | Reuse a saved Browser Context Profile (logged-in state) |
| `profile_id` | No | Specific Browser Context Profile id; requires `use_profile` |
| `use_vault` | No | Allow TinyFish to log in using connected credentials |
| `credential_item_ids` | No | Scope the run to specific vault credentials; requires `use_vault` |

### Browser Session

Launch a remote Chromium browser and get a CDP (Chrome DevTools Protocol) URL to connect with Playwright or Puppeteer. Sessions include remote browser infrastructure for direct CDP control.

```python
from crewai_tinyfish import TinyFishBrowserSessionTool

browser = TinyFishBrowserSessionTool()
session = browser.run(url="https://example.com", timeout_seconds=300)
print(session)
# Returns a JSON string with: {"session_id": "...", "cdp_url": "wss://...", "base_url": "https://..."}
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | No | Optional URL to open when the session starts |
| `timeout_seconds` | No | Optional inactivity timeout in seconds (5-86400) |

## With a CrewAI Crew

Give your agent access to multiple TinyFish tools. The agent decides which primitive to use based on the task.

```python
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tinyfish import TinyFishSearchTool, TinyFishFetchTool, TinyFishAgentTool

llm = LLM(model="gpt-5.5")

researcher = Agent(
    role="Web Researcher",
    goal="Find and summarize current information from the web",
    backstory="An analyst who grounds every answer in live sources.",
    tools=[TinyFishSearchTool(), TinyFishFetchTool(), TinyFishAgentTool()],
    llm=llm,
)

task = Task(
    description=(
        "Find the top 3 results for 'best open source LLMs' and extract the "
        "full content of the first result."
    ),
    expected_output="A 3-bullet summary, each with a source URL.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential)
print(crew.kickoff())
```

CrewAI resolves an LLM from your environment by default (for example, `OPENAI_API_KEY`). Pass an explicit `LLM(...)` to choose a specific model or provider — CrewAI uses LiteLLM, so any supported provider works (OpenAI, Anthropic, Google, OpenRouter, local models, and more).

## Stealth Mode and Proxies

For Web Agent runs on sites with bot protection (Cloudflare, CAPTCHAs, etc.), pass stealth and proxy options directly to the tool:

```python
from crewai_tinyfish import TinyFishAgentTool

result = TinyFishAgentTool().run(
    url="https://protected-site.com/data",
    goal="Extract all pricing tiers as JSON",
    browser_profile="stealth",
    use_proxy=True,
    proxy_country="US",  # Also: GB, CA, DE, FR, JP, AU
)
```

`browser_profile`, `use_proxy`, and `proxy_country` are used by `TinyFishAgentTool`. Search, Fetch, and Browser Session tools do not use these parameters.

## Development

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

Tests run fully offline — the TinyFish client is faked, so no API key or network is required.

## Resources

- [TinyFish Documentation](https://docs.tinyfish.ai)
- [TinyFish Website](https://tinyfish.ai)
- [API Keys](https://agent.tinyfish.ai/api-keys)
- [CrewAI Documentation](https://docs.crewai.com)
- [Discord Community](https://discord.com/invite/tinyfish)

## Support

Questions or issues? Reach out at [support@tinyfish.ai](mailto:support@tinyfish.ai) or join our [Discord](https://discord.com/invite/tinyfish).
