# TinyFish Web Agent — Google ADK Integration

Automate any website using natural language with [TinyFish Web Agent](https://tinyfish.ai), integrated as function tools for [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/).

## Installation

```bash
pip install tinyfish-adk
```

Or install from source:

```bash
git clone https://github.com/tinyfish-io/tinyfish-web-agent-integrations.git
cd tinyfish-web-agent-integrations/google-adk
pip install -e .
```

## Setup

Get your API key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys):

```bash
export TINYFISH_API_KEY="your-api-key"
export GOOGLE_API_KEY="your-gemini-key"
```

`tinyfish-adk` automatically tags TinyFish SDK requests as originating from
`google-adk`. You do not need to set `TF_API_INTEGRATION` yourself.

## Tools

| Tool | Description |
|------|-------------|
| `tinyfish_web_agent` | Run a browser automation synchronously. Best for quick tasks. |
| `tinyfish_queue_run` | Start an automation asynchronously. Returns a `run_id`. |
| `tinyfish_get_run` | Check status and get results of a run by `run_id`. |
| `tinyfish_list_runs` | List recent automation runs, optionally filtered by status. |
| `tinyfish_search` | Search the web and return structured results. |
| `tinyfish_fetch` | Fetch clean content from one or more URLs. |
| `tinyfish_create_browser_session` | Create a remote browser session and return connection URLs. |

## Usage

### Basic agent

```python
from google.adk import Agent
from tinyfish_adk import tinyfish_web_agent

agent = Agent(
    name="web_researcher",
    model="gemini-2.5-flash",
    instruction="Use tinyfish_web_agent to browse and extract data from websites.",
    tools=[tinyfish_web_agent],
)
```

### Async workflow

```python
from google.adk import Agent
from tinyfish_adk import tinyfish_queue_run, tinyfish_get_run

agent = Agent(
    name="async_scraper",
    model="gemini-2.5-flash",
    instruction="Queue long-running scrapes and poll for results.",
    tools=[tinyfish_queue_run, tinyfish_get_run],
)
```

### All tools

```python
from tinyfish_adk import (
    tinyfish_web_agent,
    tinyfish_queue_run,
    tinyfish_get_run,
    tinyfish_list_runs,
    tinyfish_search,
    tinyfish_fetch,
    tinyfish_create_browser_session,
)

agent = Agent(
    name="web_automation_agent",
    model="gemini-2.5-flash",
    tools=[
        tinyfish_web_agent,
        tinyfish_queue_run,
        tinyfish_get_run,
        tinyfish_list_runs,
        tinyfish_search,
        tinyfish_fetch,
        tinyfish_create_browser_session,
    ],
)
```

## Configuration

All tools read `TINYFISH_API_KEY` from the environment. The package also sets
`TF_API_INTEGRATION=google-adk` internally so requests are attributed
automatically. Each tool also accepts optional parameters:

| Parameter | Description |
|-----------|-------------|
| `browser_profile` | `"lite"` (default, fast) or `"stealth"` (anti-detection) |
| `proxy_country` | Route through a proxy: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU` |

## Example goals

```text
"Extract all product names, prices, and ratings from this page"
"Fill the contact form with name 'Jane Doe' and email 'jane@example.com', then submit"
"Click 'Next Page' 3 times, extracting all listings from each page"
```

## Support

- [TinyFish Docs](https://docs.tinyfish.ai)
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [Discord](https://discord.gg/agentql)
