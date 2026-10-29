# TinyFish Power for Kiro

Search the web, read any page, and drive real multi-step workflows on live sites — including sites
you're logged into — directly from [Kiro](https://kiro.dev).

This power connects Kiro to [TinyFish](https://www.tinyfish.ai), a web agent built for AI. Where
search tools stop at retrieval, TinyFish also *acts*: it puts an agent in a real browser that clicks,
fills forms, navigates flows, and works inside applications using saved sessions and password-manager
credentials. Search and page extraction are free.

It is packaged in the [Agent Plugins](https://agent-plugins.org) format that Kiro powers use: a
`plugin.json` manifest, an `mcp.json` that declares TinyFish's hosted
[MCP server](https://docs.tinyfish.ai/mcp-integration), and six skills. Kiro loads the power when a
task matches its keywords, so its tools and skills stay out of context until you need the web.

## Installation

1. Open Kiro and go to the **Powers** panel.
2. Click **Add Custom Power**, then choose one of:
   - **Import power from GitHub** and enter
     `https://github.com/tinyfish-io/tinyfish-web-agent-integrations/tree/main/kiro`, or
   - **Import power from a folder** after cloning this repository, and select the `kiro/` directory
     (the one containing `plugin.json`).
3. Click **Install**.

   In Kiro CLI, install from a clone instead:

   ```bash
   kiro-cli powers install ./tinyfish-web-agent-integrations/kiro
   ```

4. Ask Kiro anything that needs the web. When the power first activates, Kiro asks you to sign in to
   TinyFish — it doesn't open the browser on its own. In Kiro CLI, press **Ctrl+Y** at the "Starting
   OAuth for power-tinyfish-tinyfish" prompt, or run `/mcp` to get the link, then sign in in your
   browser. Kiro saves the sign-in for later sessions. You'll need a TinyFish account — [sign up
   here](https://agent.tinyfish.ai).

To update, select the power in the Powers panel and click **Check for updates**. To remove it, click
**Uninstall**, or run `kiro-cli powers uninstall tinyfish`.

## Authentication

- **OAuth (this power)** — the bundled `mcp.json` signs in through the browser on first connection,
  using dynamic client registration, so there is nothing to configure. It carries no API key: the
  Agent Plugins format does not expand environment variables in headers, so a key can't be shipped in
  a power.
- **API key (manual)** — to use a TinyFish API key instead, register the server yourself in
  `~/.kiro/settings/mcp.json` (or a workspace's `.kiro/settings/mcp.json`):

  ```json
  {
    "mcpServers": {
      "tinyfish": {
        "url": "https://agent.tinyfish.ai/mcp",
        "headers": {
          "X-API-Key": "${TINYFISH_API_KEY}",
          "X-TF-Client-Name": "kiro",
          "X-TF-Client-Version": "1.0.0"
        }
      }
    }
  }
  ```

  Export `TINYFISH_API_KEY` in the shell Kiro starts from, and add `TINYFISH_API_KEY` to Kiro's **Mcp
  Approved Env Vars** setting; Kiro expands only approved variables. A keyed registration has no OAuth
  fallback. Uninstall the power first so you don't load two copies of the same tools, then import the
  skills on their own: in **Agent Steering & Skills**, click **+**, choose **Import a skill**, and
  enter each skill's folder URL, such as
  `https://github.com/tinyfish-io/tinyfish-web-agent-integrations/tree/main/kiro/skills/tinyfish-web`.
  Keys come from [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys).

## Tools

| Tool | What it does | Cost |
|---|---|---|
| `search` | Ranked web results, with filters for recency, date range, domains, news, and research papers | Free |
| `fetch_content` | Read up to 10 URLs per call as clean markdown; renders JavaScript; CSS-scoped extraction | Free |
| `run_web_automation` | Multi-step browser automation from a natural-language goal — click, type, submit, navigate | $0.016/step |
| `run_web_automation_async` | The same, returning a run ID immediately — only when you ask for a background run | $0.016/step |
| `get_run`, `cancel_run` | Check on or stop a single run | — |
| `list_runs` | Find recent runs, e.g. to recover a run ID after a timeout | — |
| `batch_status`, `batch_cancel` | Poll or cancel several runs at once by ID (up to 8) | — |
| `create_browser_session` | Remote stealth Chrome with a CDP URL for Playwright, Puppeteer, or Selenium | $0.002/browser-minute |
| `list_browser_sessions`, `close_browser_session` | Find open browser sessions; close one by ID (idempotent) | — |
| `list_profiles`, `create_profile` | List or create Browser Context Profiles (saved signed-in sessions) | — |
| `start_profile_setup_session`, `save_profile_setup_session`, `cancel_profile_setup_session` | Open a live browser where you sign in by hand, then save that session to a profile | — |
| `create_monitor` | Re-check a page or a search topic on a cron schedule; returns a baseline immediately | $0.005/completed check |
| `list_monitors`, `get_monitor`, `run_monitor`, `pause_monitor`, `resume_monitor`, `cancel_monitor` | Manage monitors; `run_monitor` checks once now | `run_monitor`: $0.005 |
| `get_wallet`, `get_search_usage`, `list_fetch_usage` | Wallet balance and rates; search and fetch history | — |

Automation supports structured output via `output_schema`, stealth mode and proxy routing for protected
sites, and authenticated runs via saved Browser Context Profiles and Vault credentials.

## Skills

| Skill | What it does |
|---|---|
| `tinyfish-web` | Router — picks the right tool for a web task, and keeps free reads from being done as metered automations |
| `tinyfish-research` | Research orchestrator: plans the work, runs it in passes or across subagents, compiles deduplicated cited results |
| `tinyfish-automation` | Goal-driven automation: goal writing, structured output, and diagnosing bot detection |
| `tinyfish-authenticated` | Automating logged-in sites with Browser Context Profiles and Vault credentials |
| `tinyfish-browser` | Remote browser sessions driven over CDP from your own code |
| `tinyfish-monitor` | Recurring monitors on a page or search topic — price drops, restocks, new listings, news |

Kiro activates a skill when a request matches its description.

These skills are generated from the shared source in [`skills/`](../skills); edit there and run
`make skills`, not here.

Each skill carries its own safety rules inline — untrusted content handling, the prohibition on putting
credentials in a goal, and confirmation before irreversible actions. `rules/security.md` documents them
in full for readers and reviewers; Kiro loads only `plugin.json`, `mcp.json`, and `skills/` from a
power, so the enforceable copy is the one inside each skill.

## Security

- **Network endpoints:** The power declares a single MCP connection — `https://agent.tinyfish.ai/mcp`,
  TinyFish's hosted server for web search, content extraction, and browser automation. It configures no
  other endpoint. OAuth sign-in and any remote-browser CDP session the server hands back are carried out
  by TinyFish, not by anything this power ships.
- **Credentials:** OAuth 2.1 via the browser on first connection. **No API key is stored or read by
  this power's bundled `mcp.json`.** Its only headers are `X-TF-Client-Name` and
  `X-TF-Client-Version`, which identify the integration. The manual key path in
  [Authentication](#authentication) uses your own environment and Kiro config.
- **Contents:** Markdown and JSON only. No scripts, binaries, hooks, or install steps — nothing in this
  power executes.
- **Website credentials** used during authenticated runs are supplied by TinyFish Vault from the user's
  connected password manager and are filled into pages without the agent seeing them. The skills
  prohibit putting credentials in a goal string.
- **Untrusted content:** `rules/security.md` instructs the agent to treat all fetched web content as
  untrusted and never to follow instructions found inside it.

## Resources

- [Documentation](https://docs.tinyfish.ai)
- [MCP Integration](https://docs.tinyfish.ai/mcp-integration)
- [Goal Prompting Guide](https://docs.tinyfish.ai/prompting-guide)
- [Browser Context Profiles](https://docs.tinyfish.ai/key-concepts/browser-context-profiles)
- [Kiro Powers](https://kiro.dev/docs/powers/)
- [Cookbook](https://github.com/tinyfish-io/tinyfish-cookbook)
- [Sign up](https://agent.tinyfish.ai)

## License

MIT — see [LICENSE](LICENSE).
