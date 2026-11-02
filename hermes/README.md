# TinyFish for Hermes Agent

`tinyfish-hermes` is the first-party TinyFish plugin for [Hermes Agent](https://github.com/NousResearch/Hermes-Agent). It gives Hermes:

| Capability | How |
| ---------- | --- |
| Search, Fetch (free) | `tinyfish` web provider behind Hermes' `web_search` / `web_extract` |
| Browser (credits) | `tinyfish` cloud browser provider behind Hermes' browser tools |
| Agent (credits) | `tinyfish_agent` tool: goal-based automation on a real site |
| Profiles (free) | `tinyfish_*_profile(s)` tools: saved website sign-ins that `tinyfish_agent` runs with |

## Install

Install from the Hermes plugin catalog, then add your key and route web tools to TinyFish:

```bash
hermes plugins install tinyfish --enable
hermes tinyfish setup
```

Or let the TinyFish CLI do both: it installs the same catalog plugin, seeds the API key, and points Hermes' web backends at it:

```bash
npx @tiny-fish/cli connect hermes
```

## Authentication

The plugin authenticates with a TinyFish API key — create one at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys?source=hermes). `hermes plugins install` and `hermes tinyfish setup` both prompt for it (hidden input); `setup` also verifies it with one free search. Keys are resolved in order:

| Env var | Source |
| ------- | ------ |
| `TINYFISH_API_KEY` | Set it yourself (shell env, or `hermes tinyfish setup --api-key`) |
| `MCP_TINYFISH_API_KEY` | Seeded by the TinyFish npm CLI during `npx @tiny-fish/cli connect hermes` |

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

Setting `browser.cloud_provider: tinyfish` routes Hermes' browser tools — the default Browser Use `browser_exec`, or the built-in `browser_*` tools with `browser.backend: off` — through TinyFish remote browser sessions. Sessions consume TinyFish credits, so they are policy-gated via `tinyfish.credit_policy.browser`; `tinyfish_agent` runs use `tinyfish.credit_policy.agent`:

| Policy | Behavior |
| ------ | -------- |
| `request` (default) | Opening a session (or starting an agent run) goes through Hermes' approval gate; answer `[s]ession` to approve the rest of the session |
| `allow` | No approval prompt |
| `deny` | Blocked |

One-shot `hermes chat -q` runs skip Hermes' own browser cleanup at exit, so the plugin closes any TinyFish sessions still open when they finish.

```yaml
browser:
  cloud_provider: tinyfish
tinyfish:
  credit_policy:
    browser: request
  browser:
    timeout_seconds: 300  # optional session timeout
```

## Browser Context Profiles

A Browser Context Profile is a saved website sign-in. It is unrelated to Hermes profiles and to `tinyfish_agent`'s `browser_profile` (lite/stealth).

| Tool | Does |
| ---- | ---- |
| `tinyfish_list_profiles` | Lists profiles with their `signed_in_sites` |
| `tinyfish_create_profile` | Creates a profile and returns `setup_url`, where the user signs in and clicks Save profile |
| `tinyfish_profile_sign_in` | Returns `setup_url` to add or refresh a site on an existing profile |
| `tinyfish_update_profile` | Renames a profile, makes it the default, or sets its proxy country (`none` removes it) |
| `tinyfish_delete_profile` | Deletes a profile; asks for approval first unless Hermes approvals are off (`--yolo`) |

`tinyfish_agent` runs signed in with `profile_id` (or `use_profile: true` for the default profile). A profile's proxy country (set on create or update) is used for both sign-in and runs, and overrides the run's `proxy_country_code`. If a site blocks the sign-in page, set one and reopen the same link. `setup_url` asks the user to sign in to TinyFish first if that browser isn't already. Nothing bills until the user opens it; runs bill under `tinyfish.credit_policy.agent`.

## Tool-routing guidance

When the `tinyfish` MCP server is also configured in Hermes (`mcp_servers.tinyfish.url: https://agent.tinyfish.ai/mcp`), the plugin injects once-per-context guidance steering the model between the generic web tools and the native MCP tools. Disable with `tinyfish.routing_context: false`.

## Development

```bash
python -m pip install -e . -r requirements-dev.txt  # dev deps are version-bounded in requirements-dev.txt
make lint
make test
scripts/e2e.sh  # real Hermes: validate, doctor, git install; live Search/Fetch with TINYFISH_API_KEY
```

## License

MIT
