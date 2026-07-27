# TinyFish Plugin for Grok Build

Search the web, read any page, and drive real multi-step workflows on live sites — including sites
you're logged into — directly from Grok Build.

This plugin connects Grok Build to [TinyFish](https://www.tinyfish.ai), a web agent built for AI.
Where search tools stop at retrieval, TinyFish also *acts*: it puts an agent in a real browser that
clicks, fills forms, navigates flows, and works inside applications using saved sessions and
password-manager credentials. Search and page extraction are free.

It uses TinyFish's hosted [MCP server](https://docs.tinyfish.ai/mcp-integration). Install once, sign in
through the browser, and it works — there is no API key to paste.

## Installation

1. Install Grok Build (see the [Grok Build docs](https://docs.x.ai/build/overview)):

   ```bash
   curl -fsSL https://x.ai/cli/install.sh | bash
   ```

2. Sign in to your xAI account:

   ```bash
   grok login
   ```

3. Start Grok Build by running `grok`, then open the marketplace:

   ```text
   /marketplace
   ```

4. Find **tinyfish** in the list and press `i` to install it.

5. Open the MCP servers tab with `/mcps`, select **tinyfish**, and press `i` to sign in. Your browser
   opens the TinyFish sign-in page. You'll need a TinyFish account — [sign up
   here](https://agent.tinyfish.ai).

6. Once **tinyfish** shows ready, ask Grok anything that needs the web.

## Tools

| Tool | What it does | Cost |
|---|---|---|
| `search` | Ranked web results, with filters for recency, date range, domains, news, and research papers | Free |
| `fetch_content` | Read up to 10 URLs per call as clean markdown; renders JavaScript; CSS-scoped extraction | Free |
| `run_web_automation` | Multi-step browser automation from a natural-language goal — click, type, submit, navigate | 1 credit/step |
| `run_web_automation_async` | The same, returning a run ID immediately for long tasks | 1 credit/step |
| `get_run`, `cancel_run` | Check on or stop a single run | — |
| `batch_status`, `batch_cancel` | Poll or cancel several runs at once by ID (up to 8) | — |
| `create_browser_session` | Remote stealth Chrome with a CDP URL for Playwright, Puppeteer, or Selenium | 1 credit / 4 browser-minutes |
| `close_browser_session` | Close a browser session by ID; idempotent | — |

Automation supports structured output via `output_schema`, stealth mode and proxy routing for protected
sites, and authenticated runs via saved Browser Context Profiles and Vault credentials.

## Skills

| Skill | What it does |
|---|---|
| `tinyfish-web` | Router — picks the right tool for a web task, and keeps free reads from being done as metered automations |
| `tinyfish-research` | Research orchestrator: plans the work, fans searches out across subagents, compiles deduplicated cited results |
| `tinyfish-automation` | Goal-driven automation: goal writing, structured output, and diagnosing bot detection |
| `tinyfish-authenticated` | Automating logged-in sites with Browser Context Profiles and Vault credentials |
| `tinyfish-browser` | Remote browser sessions driven over CDP from your own code |

Each skill carries its own safety rules inline — untrusted content handling, the prohibition on putting
credentials in a goal, and confirmation before irreversible actions. `rules/security.md` documents them
in full for readers and reviewers; note that a plugin's `rules/` directory is **not** a loaded
component, so the enforceable copy is the one inside each skill.

## What makes TinyFish different

Retrieval is table stakes. The distinguishing capability is **working inside authenticated
applications**: set up a Browser Context Profile once by signing in, then every later run starts
already authenticated — with Vault credentials available to repair the session when it goes stale. That
covers the internal dashboards, admin panels, and SaaS apps where most real work actually lives, and it
does it without the agent ever seeing a password.

## Security

- **Network endpoints:** `https://agent.tinyfish.ai/mcp` — TinyFish's hosted MCP server (web search,
  content extraction, browser automation). No other endpoint is contacted.
- **Credentials:** OAuth 2.1 via the browser on first connection. **No API key is stored or read by
  this plugin.** It never reads environment variables, `.env` files, or any local secret.
- **Contents:** Markdown and JSON only. No scripts, binaries, hooks, or install steps — nothing in this
  plugin executes.
- **Website credentials** used during authenticated runs are supplied by TinyFish Vault from the user's
  connected password manager and are filled into pages without the agent seeing them. The skills
  prohibit putting credentials in a goal string.
- **Untrusted content:** `rules/security.md` instructs the agent to treat all fetched web content as
  untrusted and never to follow instructions found inside it.

## Resources

- [Documentation](https://docs.tinyfish.ai)
- [API Reference](https://docs.tinyfish.ai/api-reference)
- [MCP Integration](https://docs.tinyfish.ai/mcp-integration)
- [Goal Prompting Guide](https://docs.tinyfish.ai/prompting-guide)
- [Browser Context Profiles](https://docs.tinyfish.ai/key-concepts/browser-context-profiles)
- [Cookbook](https://github.com/tinyfish-io/tinyfish-cookbook)
- [Sign up](https://agent.tinyfish.ai)

## License

MIT — see [LICENSE](LICENSE).
