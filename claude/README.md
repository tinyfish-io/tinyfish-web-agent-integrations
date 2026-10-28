# TinyFish

The complete web toolkit for your agent — search, fetch, browser automation, headless browser control, and website monitoring.

## Skills

The six `tinyfish-*` skills are built on TinyFish's hosted MCP server (bundled via `.mcp.json`). No install, no CLI needed — first use triggers an OAuth sign-in to your TinyFish account, or set an API key (see Authentication). Search and fetch are free; automation, browser sessions, and monitor checks are billed to your TinyFish wallet, and new users get $8 in sign-up credits. They work in any environment, including sandboxed surfaces without terminal access, except `tinyfish-browser`, which needs code execution to drive the browser.

- **`/tinyfish:tinyfish-web`** — picks the right TinyFish tool when a web task could go several ways
- **`/tinyfish:tinyfish-research`** — free web search with recency/date, domain, and news/research-paper filters, free page fetching as clean markdown from up to 10 URLs at once, and deep research runs when you ask for them
- **`/tinyfish:tinyfish-automation`** — browser automation billed to your wallet: natural-language goals that click, fill forms, and extract data in a live cloud browser
- **`/tinyfish:tinyfish-authenticated`** — automation on sites you're signed into, with saved Browser Context Profiles and Vault credentials
- **`/tinyfish:tinyfish-browser`** — a remote stealth Chrome session over CDP for Playwright, Puppeteer, or Selenium
- **`/tinyfish:tinyfish-monitor`** — recurring checks on a page or a search topic: $0.005 per completed check, failed checks are free

These skills are generated from the shared source in [`skills/`](../skills); edit there and run `make skills`, not here.

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
