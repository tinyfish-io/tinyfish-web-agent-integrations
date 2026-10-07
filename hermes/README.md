# TinyFish for Hermes Agent

`tinyfish-hermes` is the first-party TinyFish plugin for [Hermes Agent](https://github.com/NousResearch/Hermes-Agent). It gives Hermes:

| Capability | How |
| ---------- | --- |
| Search, Fetch (free) | `tinyfish` web provider behind Hermes' `web_search` / `web_extract` |
| Browser (credits) | `tinyfish` cloud browser provider behind Hermes' browser tools |
| Agent (credits) | `tf_agent` tool: goal-based automation on a real site |

## Install

The supported path is the TinyFish CLI, which installs the plugin from npm
(`@tiny-fish/hermes@latest`), seeds the API key, and points Hermes' web backends at it:

```bash
tinyfish connect hermes
```

To install just the plugin straight from this repo (no key seeding, no backend wiring):

```bash
hermes plugins install tinyfish-io/tinyfish-web-agent-integrations/hermes --enable
```

## Authentication

The plugin authenticates with a TinyFish API key — create one at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys?source=hermes). `hermes plugins install` and `hermes tinyfish setup` both prompt for it (hidden input); `setup` also verifies it with one free search. Keys are resolved in order:

| Env var | Source |
| ------- | ------ |
| `TINYFISH_API_KEY` | Set it yourself (shell env, or `hermes tinyfish setup --api-key`) |
| `MCP_TINYFISH_API_KEY` | Seeded by the TinyFish npm CLI during `tinyfish connect hermes` |

## CLI

The plugin registers a `hermes tinyfish` command and an in-session `/tinyfish-status [live]` command:

| Subcommand | Purpose |
| ---------- | ------- |
| `setup [--yes] [--api-key KEY] [--no-web-backend] [--live]` | Route web tools to TinyFish and save the API key |
| `status [--json]` | Non-secret configuration status |
| `doctor [--json] [--live] [--live-paid]` | Diagnostics; `--live` runs one real search+fetch, `--live-paid` a browser session per credit policy |
| `credits {status,set,reset}` | Inspect or change `tinyfish.credit_policy.{browser,agent}` |
| `browser {enable,disable,status}` | Toggle `browser.cloud_provider: tinyfish` |
| `usage [--json]` | Wallet balance, auto-reload, and billing rates |

## Configuration

`hermes tinyfish setup` routes Hermes' web tools to TinyFish; the equivalent Hermes configuration is:

```yaml
web:
  search_backend: tinyfish
  extract_backend: tinyfish
```

Optional request tuning under a `tinyfish` section:

```yaml
tinyfish:
  search:
    location: US          # also: language, recency_minutes, after_date,
    domain_type: news     # before_date, page, purpose
  fetch:
    ttl: 300              # also: per_url_timeout_ms (default 90000), links, image_links
```

## Browser sessions

Setting `browser.cloud_provider: tinyfish` routes Hermes' browser tools — the default Browser Use `browser_exec`, or the built-in `browser_*` tools with `browser.backend: off` — through TinyFish remote browser sessions. Sessions consume TinyFish credits, so they are policy-gated via `tinyfish.credit_policy.browser`; `tf_agent` runs use `tinyfish.credit_policy.agent`:

| Policy | Behavior |
| ------ | -------- |
| `request` (default) | Opening a session (or starting an agent run) goes through Hermes' approval gate; answer `[s]ession` to approve the rest of the session |
| `allow` | No approval prompt |
| `deny` | Blocked |

On shutdown the plugin closes any TinyFish browser sessions Hermes still holds.

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
  browser:
    timeout_seconds: 300  # optional session timeout
```

## Tool-routing guidance

When the `tinyfish` MCP server is also configured in Hermes (`mcp_servers.tinyfish.url: https://agent.tinyfish.ai/mcp`), the plugin injects once-per-context guidance steering the model between the generic web tools and the native MCP tools. Disable with `tinyfish.routing_context: false`.

## Development

```bash
python -m pip install -e . -r requirements-dev.txt  # dev deps are version-bounded in requirements-dev.txt
make lint
make test
hermes plugins validate . && hermes plugins doctor . --ci  # against a real Hermes
```

## License

MIT
