# Tinyfish — CrewAI Tool

Automate any website using natural language with [TinyFish Web Agent](https://tinyfish.ai). Extract data, fill forms, click buttons, navigate pages, and more — all described in plain English.

## Installation

Clone the repo and install the tool locally:

```bash
git clone https://github.com/tinyfish-io/tinyfish-web-agent-integrations.git
cd tinyfish-web-agent-integrations/crew-ai
pip install -e .
```

## Setup

Get your API key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys), then set it as an environment variable:

```bash
export TINYFISH_API_KEY="your-api-key"
```

Or add it to your `.env` file:

```dotenv
TINYFISH_API_KEY=your-api-key
```

`tinyfish-web-agent` automatically tags TinyFish SDK requests as originating
from `crew-ai`. You do not need to set `TF_API_INTEGRATION` yourself.

## Tools

| Tool | Description |
|------|-------------|
| `TinyfishRun` | Run a browser automation synchronously. Best for quick tasks (<30s). |
| `TinyfishRunAsync` | Start an automation asynchronously. Returns a `run_id` immediately. |
| `TinyfishGetRun` | Check status and get results of a run by its `run_id`. |
| `TinyfishListRuns` | List recent automation runs, optionally filtered by status. |
| `TinyfishSearch` | Search the web and return structured results. |
| `TinyfishFetch` | Fetch clean content from one or more URLs. |
| `TinyfishBrowserSession` | Create a remote browser session and return connection URLs. |

`Tinyfish` is an alias for `TinyfishRun`.

## Usage

### Basic — synchronous run

```python
from crewai import Agent
from tinyfish_web_agent import TinyfishRun

agent = Agent(
    role="Web Researcher",
    goal="Find and extract information from websites",
    tools=[TinyfishRun()],
)
```

### Async workflow — start and check

```python
from tinyfish_web_agent import TinyfishRunAsync, TinyfishGetRun

agent = Agent(
    role="Data Collector",
    goal="Collect data from multiple sources efficiently",
    tools=[TinyfishRunAsync(), TinyfishGetRun()],
)
```

### Search and fetch

```python
from tinyfish_web_agent import TinyfishSearch, TinyfishFetch

agent = Agent(
    role="Web Researcher",
    goal="Search the web and read relevant pages",
    tools=[TinyfishSearch(), TinyfishFetch()],
)
```

### All tools at once

```python
from tinyfish_web_agent import (
    TinyfishRun,
    TinyfishRunAsync,
    TinyfishGetRun,
    TinyfishListRuns,
    TinyfishSearch,
    TinyfishFetch,
    TinyfishBrowserSession,
)

agent = Agent(
    role="Web Automation Specialist",
    goal="Automate any web task",
    tools=[
        TinyfishRun(),
        TinyfishRunAsync(),
        TinyfishGetRun(),
        TinyfishListRuns(),
        TinyfishSearch(),
        TinyfishFetch(),
        TinyfishBrowserSession(),
    ],
)
```

## Configuration

All tools accept these optional constructor parameters:

| Parameter | Description |
|-----------|-------------|
| `api_key` | TinyFish API key. Falls back to `TINYFISH_API_KEY` env var. |
| `proxy_country` | Route through a proxy in this country (`US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU`). |

The package also sets `TF_API_INTEGRATION=crew-ai` internally so requests are
attributed automatically.

```python
tool = TinyfishRun(api_key="sk-...", proxy_country="US")
```

## Example goals

```text
"Extract all product names, prices, and ratings from this page"
"Fill the contact form with name 'Jane Doe' and email 'jane@example.com', then submit"
"Click 'Next Page' 3 times, extracting all listings from each page"
"Log in with the provided credentials, then extract the dashboard data"
```

## Support

- [TinyFish Docs](https://docs.tinyfish.ai)
- [CrewAI Docs](https://docs.crewai.com)
- [Discord](https://discord.gg/agentql)
