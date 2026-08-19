# TinyFish Web Agent — AG2 Integration

[TinyFish](https://tinyfish.ai) Search and Fetch are available to [AG2](https://github.com/ag2ai/ag2) agents through
`TinyFishSearchToolkit`, shipped **inside AG2 itself** — there is no separate adapter package to install.

Requires **AG2 >= 1.0.0**.

## Installation

```bash
pip install "ag2[anthropic]>=1.0.0" "tinyfish>=0.5,<0.6"
```

The toolkit lives in `ag2.extensions.tools.search`. AG2 extensions are not shipped as extras, so the
`tinyfish` SDK is installed directly alongside AG2. Python 3.11+ is required (a constraint of the
`tinyfish` SDK).

The `[anthropic]` extra installs the model provider used in the examples below. Swap it for whichever
provider you run — `ag2[openai]`, `ag2[gemini]`, `ag2[bedrock]`, `ag2[mistral]`, `ag2[ollama]`,
`ag2[xai]` — or combine them: `ag2[anthropic,openai]`. The TinyFish tools themselves are
provider-agnostic.

## Setup

Get your API key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys):

```bash
export TINYFISH_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-anthropic-key"   # or any other AG2-supported provider
```

AG2 sets `TF_API_INTEGRATION=ag2` around every TinyFish SDK call, so requests are attributed to AG2
automatically. Any value you set yourself is restored after the call, so an outer `TF_API_INTEGRATION`
is never clobbered.

## Tools

| Tool | Description |
|------|-------------|
| `tinyfish_search` | Search the web. Returns ranked results with titles, snippets, site names, and URLs. |
| `tinyfish_fetch` | Fetch browser-rendered content for 1–10 URLs. Returns extracted content plus per-URL errors. |

## Usage

### Basic agent

Passing the toolkit registers both tools:

```python
import os

from ag2 import Agent
from ag2.config import AnthropicConfig
from ag2.extensions.tools.search import TinyFishSearchToolkit

agent = Agent(
    "researcher",
    config=AnthropicConfig(model="claude-sonnet-4-6"),
    tools=[TinyFishSearchToolkit(api_key=os.environ["TINYFISH_API_KEY"])],
)

await agent.ask("Find the current pricing tiers on tinyfish.ai and summarise them.")
```

If `api_key` is omitted, the TinyFish SDK reads `TINYFISH_API_KEY` from the environment.

### Picking a subset of tools

Each tool is exposed as a factory method on the toolkit. Call the method to get a ready-to-use tool
and pass only the ones you need:

```python
toolkit = TinyFishSearchToolkit()

agent = Agent(
    "reader",
    config=AnthropicConfig(model="claude-sonnet-4-6"),
    tools=[toolkit.fetch()],
)
```

### Per-tool configuration

Per-call parameters live on the factory methods:

```python
toolkit = TinyFishSearchToolkit()

search_tool = toolkit.search(
    location="US",       # search locale
    language="en",
)

fetch_tool = toolkit.fetch(
    format="markdown",   # "markdown" | "html" | "json"
    links=True,          # include hyperlinks in the extracted content
    image_links=False,
)

agent = Agent("researcher", config=config, tools=[search_tool, fetch_tool])
```

Defaults can also be fixed once on the constructor and are applied to both default tools:

```python
toolkit = TinyFishSearchToolkit(
    location="US",
    language="en",
    format="markdown",
    links=True,
    base_url=None,       # override the API endpoint
    timeout=60.0,
    max_retries=3,
)
```

### Runtime values with `Variable`

Every runtime parameter accepts an AG2 `Variable`, resolved from the run context at execution time
instead of being fixed when the tool is built:

```python
from ag2.annotations import Variable

toolkit = TinyFishSearchToolkit()
search_tool = toolkit.search(location=Variable("user_country"))
```

## Notes

- `tinyfish_fetch` accepts 1–10 URLs per call and rejects any URL that is not `http`/`https`.
- Both tools are async and run natively on AG2's async execution path.

## Support

- [TinyFish Docs](https://docs.tinyfish.ai)
- [AG2 TinyFish tool docs](https://docs.ag2.ai/docs/user-guide/extensions/tools/search/tinyfish/)
- [AG2 repository](https://github.com/ag2ai/ag2)
- [Discord](https://discord.com/invite/tinyfish)
