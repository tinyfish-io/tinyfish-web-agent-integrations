# TinyFish

The complete web toolkit for your agent — search, fetch, browser automation, headless browser control, and website monitoring.

## Skills

`search`, `fetch`, `agent`, and `monitor` are built on TinyFish's hosted MCP server (bundled via `.mcp.json`). No install, no CLI needed — first use triggers an OAuth sign-in to your TinyFish account, or set an API key (see Authentication). Search and fetch are free; automation and monitor checks are billed to your TinyFish wallet, and new users get $8 in sign-up credits. They work in any environment, including sandboxed surfaces without terminal access.

- **`/tinyfish:search`** — free, token-efficient web search with flexible recency/date filtering and news/research-paper scoping
- **`/tinyfish:fetch`** — free, clean content extraction from up to 10 URLs in parallel, including JS-heavy pages
- **`/tinyfish:agent`** — browser automation billed to your wallet: natural-language goals, saved logged-in browser profiles, and raw CDP browser sessions
- **`/tinyfish:monitor`** — recurring checks on a page or a search topic, with results sent to a webhook: $0.005 per completed check, failed checks are free

The remaining two are setup tools rather than web tools, and both use your terminal:

- **`/tinyfish:doctor`** — diagnose and repair your TinyFish setup. Runs the TinyFish CLI (`npx @tiny-fish/cli doctor`) for the config checks, then calls a TinyFish tool to prove this agent can actually reach the service. Without a terminal it still runs that second half.
- **`/tinyfish:feedback`** — file a bug report or a doctor diagnostic as a GitHub issue on the public `tinyfish-io/tinyfish-cookbook` repo, via `gh`. Nothing is sent until you approve the exact text.

## Authentication

Two ways in, no configuration to choose between:

- **API key** — grab a key at https://agent.tinyfish.ai/api-keys and `export TINYFISH_API_KEY="sk-tinyfish-…"`; the plugin sends it as `X-API-Key`. No browser sign-in.
- **OAuth** — with no key set, or a key the server rejects, the connection falls back to the OAuth sign-in prompt.

## Desktop setup note

In Claude Desktop, installing this plugin enables its skills but the bundled `tinyfish` MCP connector still needs one manual step: open the plugin's **Connectors** tab and click **Install** on `tinyfish` before the skills can actually call it.

## Privacy

TinyFish's privacy policy: https://www.tinyfish.ai/privacy-policy

## Local file access

`search`, `fetch`, `agent`, and `monitor` read no local files — every operation goes through the TinyFish MCP server.

The two setup skills do touch your machine:

- **`/tinyfish:doctor`** runs the TinyFish CLI, which reads your agent config directories (`~/.claude`, `~/.codex`, `~/.cursor`, `~/.grok`, `~/.hermes`, `~/.openclaw`, `~/.config/opencode`) and the CLI credential store (`~/.tinyfish/config.json`) to find where TinyFish is registered. Diagnosis reads those files and makes authenticated calls to TinyFish to test what it found; the repair step rewrites the registrations, and only commands the CLI itself proposes. `doctor` reports its own run to TinyFish — set `TINYFISH_NO_TELEMETRY` to suppress that and the `tinyfish connect` a repair re-runs.
- **`/tinyfish:feedback`** shells out to `gh issue create` against a public repo, after showing you the exact issue text and waiting for your approval.
