# TinyFish for Hermes Agent

`tinyfish-hermes` is the first-party TinyFish plugin for [Hermes Agent](https://github.com/NousResearch/Hermes-Agent). It registers a `tinyfish` web provider that serves Hermes' web search and extract tools through the TinyFish Search and Fetch REST APIs, plus a `tinyfish` cloud browser provider for credit-gated remote browser sessions.

## Install

```bash
hermes plugins install tinyfish-io/tinyfish-web-agent-integrations/hermes --enable
```

## Authentication

The plugin authenticates with a TinyFish API key — create one at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys). Keys are resolved in order:

| Env var | Source |
| ------- | ------ |
| `TINYFISH_API_KEY` | Set it yourself (shell env, or Hermes' env file) |
| `MCP_TINYFISH_API_KEY` | Seeded by the TinyFish npm CLI during `tinyfish connect hermes` |

## Configuration

Route Hermes' web tools to TinyFish in Hermes' configuration:

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
    format: markdown      # default output format for extract
    ttl: 300              # also: per_url_timeout_ms, links, image_links
```

## Browser sessions

Setting `browser.cloud_provider: tinyfish` routes Hermes' browser tools through TinyFish remote browser sessions. Each session consumes TinyFish credits, so sessions are policy-gated via `tinyfish.credit_policy.browser`:

| Policy | Behavior |
| ------ | -------- |
| `request` (default) | Every session goes through Hermes' approval gate |
| `allow` | Sessions start without per-session approval |
| `deny` | Browser tools are blocked while routed to TinyFish |

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
```

## Credits

The provider architecture is ported from [gabeosx/hermes-plugin-tinyfish](https://github.com/gabeosx/hermes-plugin-tinyfish) (MIT), an independent community plugin. Both plugins register a web provider named `tinyfish`, so install only one of them.

## License

MIT
