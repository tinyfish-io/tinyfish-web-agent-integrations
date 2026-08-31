# tinyfish-adk

[![PyPI version](https://img.shields.io/pypi/v/tinyfish-adk)](https://pypi.org/project/tinyfish-adk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[TinyFish](https://tinyfish.ai) gives AI agents every level of web access through one platform. Four primitives, each built for a different layer:

- **Search**: live web results, structured and ready for LLM consumption. Free.
- **Fetch**: renders pages in a real browser, returns clean markdown, HTML, or JSON. Token-efficient for LLM pipelines. Free.
- **Web Agent**: autonomous agents that navigate, authenticate, and extract from real websites. Uses credits.
- **Browser**: remote Chromium sessions with full CDP access. Bring your own Playwright or Puppeteer scripts. Uses credits.

This package wraps all four as function tools for [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). ADK auto-discovers tool schemas from function signatures and docstrings. [Get your API key ->](https://agent.tinyfish.ai/api-keys)

## Installation

```bash
pip install tinyfish-adk
```

```bash
export TINYFISH_API_KEY="your-api-key"
export GOOGLE_API_KEY="your-google-api-key"
```

`tinyfish-adk` automatically tags SDK requests with `TF_API_INTEGRATION=google-adk`. You do not need to set this yourself.

## Tools

All seven tools can be imported and passed directly to an ADK `Agent`:

```python
from tinyfish_adk import (
    tinyfish_search,
    tinyfish_fetch,
    tinyfish_web_agent,
    tinyfish_queue_run,
    tinyfish_get_run,
    tinyfish_list_runs,
    tinyfish_create_browser_session,
)
```

Search, Fetch, and Browser Session return JSON strings produced from TinyFish SDK responses. Web Agent returns a JSON string for completed results, or a human-readable status/error message. Run-management tools return formatted status text for agent consumption.

### Search

Search the web and get structured results with titles, snippets, and URLs. Free, no credits required.

```python
from tinyfish_adk import tinyfish_search

result = tinyfish_search(
    query="latest LLM benchmarks 2025",
    location="US",
)
print(result)
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
from tinyfish_adk import tinyfish_fetch

result = tinyfish_fetch(
    urls=["https://docs.tinyfish.ai"],
    format="markdown",
    links=True,
)
print(result)
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
from tinyfish_adk import tinyfish_web_agent

result = tinyfish_web_agent(
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
| `browser_profile` | No | `"lite"` (default, fast) or `"stealth"` (anti-detection for bot-protected sites) |
| `proxy_country` | No | Route through a proxy: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU`. Empty for no proxy |

### Queue Run

Start an automation asynchronously and get a `run_id` back. Best for long-running tasks. Uses credits.

```python
from tinyfish_adk import tinyfish_queue_run

result = tinyfish_queue_run(
    url="https://example.com/products",
    goal="Extract all product names, prices, and ratings as JSON",
)
print(result)
# Returns: "Automation started. run_id: <run_id>"
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes | Target website URL |
| `goal` | Yes | Natural-language instructions for what to do |
| `browser_profile` | No | `"lite"` (default) or `"stealth"` |
| `proxy_country` | No | Optional proxy country code |

### Get Run

Check status and retrieve results of a run by `run_id`.

```python
from tinyfish_adk import tinyfish_get_run

result = tinyfish_get_run(run_id="your-run-id")
print(result)
# Returns status, live view URL, result data, and/or error details
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `run_id` | Yes | The unique run ID to look up |

### List Runs

List recent automation runs, optionally filtered by status.

```python
from tinyfish_adk import tinyfish_list_runs

result = tinyfish_list_runs(status="COMPLETED", limit=10)
print(result)
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `status` | No | Filter by status: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, or `CANCELLED`. Empty for all |
| `limit` | No | Maximum number of runs to return; 1-100, default 20 |

### Browser Session

Launch a remote Chromium browser and get a CDP (Chrome DevTools Protocol) URL to connect with Playwright or Puppeteer. Sessions include remote browser infrastructure for direct CDP control. Uses credits.

```python
from tinyfish_adk import tinyfish_create_browser_session

result = tinyfish_create_browser_session(
    url="https://example.com",
    timeout_seconds=300,
)
print(result)
# Returns a JSON string with: {"session_id": "...", "cdp_url": "wss://...", "base_url": "https://..."}
```

Supported inputs:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | No | Optional URL to open when the session starts |
| `timeout_seconds` | No | Optional inactivity timeout in seconds. Use 0 for plan default |

## With an ADK Agent

Give your agent access to TinyFish tools. The agent decides which primitive to use based on the task.

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from tinyfish_adk import tinyfish_search, tinyfish_fetch, tinyfish_web_agent

agent = LlmAgent(
    name="web_researcher",
    model="gemini-flash-latest",
    instruction="Use TinyFish tools to search the web, fetch page content, and automate websites.",
    tools=[tinyfish_search, tinyfish_fetch, tinyfish_web_agent],
)

APP_NAME = "tinyfish_app"
USER_ID = "user1"
SESSION_ID = "session1"

session_service = InMemorySessionService()
session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
)
runner = Runner(
    agent=agent,
    app_name=APP_NAME,
    session_service=session_service,
)

content = types.Content(
    role="user",
    parts=[
        types.Part(
            text="Find the top 3 results for 'best open source LLMs' and fetch the full content of the first result"
        )
    ],
)
events = runner.run(
    user_id=USER_ID,
    session_id=SESSION_ID,
    new_message=content,
)

for event in events:
    if event.is_final_response() and event.content:
        print(event.content.parts[0].text)
```

### Async Workflow Agent

For long-running tasks, give the agent queue and poll tools so it can start automations and check back for results:

```python
from google.adk.agents import LlmAgent
from tinyfish_adk import tinyfish_queue_run, tinyfish_get_run, tinyfish_list_runs

agent = LlmAgent(
    name="async_scraper",
    model="gemini-flash-latest",
    instruction="Queue long-running scrapes with tinyfish_queue_run and poll for results with tinyfish_get_run.",
    tools=[tinyfish_queue_run, tinyfish_get_run, tinyfish_list_runs],
)
```

### All Tools

```python
from google.adk.agents import LlmAgent
from tinyfish_adk import (
    tinyfish_search,
    tinyfish_fetch,
    tinyfish_web_agent,
    tinyfish_queue_run,
    tinyfish_get_run,
    tinyfish_list_runs,
    tinyfish_create_browser_session,
)

agent = LlmAgent(
    name="web_automation_agent",
    model="gemini-flash-latest",
    instruction="Use TinyFish tools to search, fetch, automate, and control browsers.",
    tools=[
        tinyfish_search,
        tinyfish_fetch,
        tinyfish_web_agent,
        tinyfish_queue_run,
        tinyfish_get_run,
        tinyfish_list_runs,
        tinyfish_create_browser_session,
    ],
)
```

## Stealth Mode and Proxies

For Web Agent runs on sites with bot protection (Cloudflare, CAPTCHAs, etc.), pass stealth and proxy options directly to the tool:

```python
from tinyfish_adk import tinyfish_web_agent

result = tinyfish_web_agent(
    url="https://protected-site.com/data",
    goal="Extract all pricing tiers as JSON",
    browser_profile="stealth",
    proxy_country="US",  # Also: GB, CA, DE, FR, JP, AU
)
```

`browser_profile` and `proxy_country` are accepted by `tinyfish_web_agent` and `tinyfish_queue_run`. Search, Fetch, Get Run, List Runs, and Browser Session tools do not use these parameters.

## Configuration

All tools read `TINYFISH_API_KEY` from the environment. Web Agent tools accept additional parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `browser_profile` | `"lite"` | Web Agent browser profile: `"lite"` or `"stealth"` |
| `proxy_country` | `""` (disabled) | Proxy exit country for Web Agent runs: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU` |

## Development

```bash
# Install package + dev dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run tests
make test

# Run linter
make lint

# Format code
make format
```

## Resources

- [TinyFish Documentation](https://docs.tinyfish.ai)
- [TinyFish Website](https://tinyfish.ai)
- [API Keys](https://agent.tinyfish.ai/api-keys)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Discord Community](https://discord.com/invite/tinyfish)

## Support

Questions or issues? Reach out at [support@tinyfish.ai](mailto:support@tinyfish.ai) or join our [Discord](https://discord.com/invite/tinyfish).
