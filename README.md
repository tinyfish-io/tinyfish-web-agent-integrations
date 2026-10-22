# TinyFish Web Agent Integrations

Bring TinyFish's web tools into your AI agents and automated workflows.

These integrations let your agents search the web, read pages, and complete tasks in a real browser. TinyFish handles the web work and returns results to your agent or workflow, where you can use them to answer questions, update records, or trigger the next step.

Choose your platform below, or follow the [API quick start](https://docs.tinyfish.ai/quick-start) to build your own connection.

![High-level diagram: agents and workflows call the integrations in this repository, which connect to TinyFish's hosted web tools. Results return to the calling agent or workflow.](./docs/assets/tinyfish-integrations.svg)

## Choose an integration

### AI assistants and coding agents

| Integration | What it adds |
|---|---|
| [Claude](./claude) | Hosted MCP tools and skills for Claude Code, Claude.ai, Claude Desktop, and Cowork. Covers search, page extraction, automation, browser control, and monitoring. |
| [Grok](./grok) | Grok Build plugin with hosted MCP tools and skills for web research, automation, authenticated sites, browser control, and monitoring. |
| [Hermes](./hermes) | Search and Fetch providers, a cloud browser provider, and the `tinyfish_agent` tool for goal-based web automation. |
| [Pi](./pi) | `@tiny-fish/pi`: six skills that use TinyFish through an MCP adapter or the TinyFish CLI. |

### Agent frameworks

| Integration | What it adds |
|---|---|
| [LangChain](./langchain) | `langchain-tinyfish`: Search, Fetch, Web Agent, and Browser tools, with async support and progress streaming inside LangGraph. |
| [Google ADK](./google-adk) | `tinyfish-adk`: seven function tools for search, extraction, browser sessions, automation, and run management. |

### Workflow platforms

| Integration | What it adds |
|---|---|
| [Dify](./dify) | Plugin for Dify workflows and agents. Start synchronous, asynchronous, or streamed automations, then check or list runs. |
| [n8n](./n8n) | `n8n-nodes-tinyfish`: community node for browser automation and run management. Works in workflows and as an n8n AI Agent tool. |

## What you can do

Available tools vary by integration:

- **Search:** Find live web results with titles, snippets, and source URLs.
- **Fetch:** Read page content as Markdown, HTML, or JSON, including pages rendered with JavaScript.
- **Web Agent:** Give TinyFish a URL and a goal. It navigates pages, clicks buttons, fills forms, and returns results.
- **Browser:** Create a remote browser session for direct control through Playwright, Puppeteer, or another CDP client.
- **Monitoring:** Check a page or search topic on a schedule and send results to a webhook through supported MCP integrations.

The MCP tools also support saved browser profiles for tasks on sites you have signed into.

Search and Fetch are free within daily allowances. Automation, browser sessions, and monitor checks draw from your TinyFish wallet. See the [documentation](https://docs.tinyfish.ai/) for current usage details.

## Get started

1. Open the guide for your integration above.
2. Install the package, plugin, or workflow node.
3. Connect your TinyFish account using the guide's authentication steps. Some integrations use browser sign-in; others require an [API key](https://agent.tinyfish.ai/api-keys).
4. Run an example from the integration guide.

For another MCP-compatible client, follow the [MCP setup guide](https://docs.tinyfish.ai/mcp-integration).

## Example: collect product prices in n8n

Add a TinyFish Web Agent node to your workflow and provide a starting URL and a goal:

```text
URL: https://scrapeme.live/shop

Goal: Extract the first 2 product names and prices.
Return JSON with a products array containing name and price.
```

TinyFish runs the browser task and returns the result to n8n. Use downstream nodes to save the products to Google Sheets or send an update to Slack.

Follow the [n8n tutorial](https://docs.tinyfish.ai/integrations/n8n) for setup and a complete workflow.

## Documentation and examples

- [Developer documentation](https://docs.tinyfish.ai/)
- [API quick start](https://docs.tinyfish.ai/quick-start)
- [Agent API reference](https://docs.tinyfish.ai/agent-api/reference)
- [MCP setup](https://docs.tinyfish.ai/mcp-integration)
- [Dify guide](https://docs.tinyfish.ai/integrations/dify)
- [TinyFish Cookbook](https://github.com/tinyfish-io/tinyfish-cookbook)

## Contributing

To improve an integration or add support for another platform, follow the development instructions in the relevant integration directory and open a pull request. Repository maintainers can find release instructions in [Maintainer notes](./.github/MAINTAINERS.md).

Integrations that call the REST API directly must send these headers on every request:

| Header | Value |
|---|---|
| `X-TF-Client-Name` | The bare integration token, matching `api_integration` where one exists, such as `dify`, `hermes`, or `n8n`. |
| `X-TF-Client-Version` | The integration's published version. |

Python SDK integrations use `TF_API_INTEGRATION` for attribution. With `tinyfish>=0.5.0`, `TF_CLIENT_NAME` and `TF_CLIENT_VERSION` set the corresponding headers; older SDK versions ignore these two variables. LangChain and Google ADK currently set only `TF_API_INTEGRATION`.

Do not set `X-TF-Request-Origin` manually; TinyFish derives the REST transport origin, and the SDK sets its own value.

For questions or bugs, [open an issue](https://github.com/tinyfish-io/tinyfish-web-agent-integrations/issues).

## License

[MIT](./LICENSE).
