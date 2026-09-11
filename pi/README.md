# TinyFish for Pi

Search the web, read any page, and drive real multi-step workflows on live sites — including sites
you're logged into — from the [Pi coding agent](https://pi.dev).

This package connects Pi to [TinyFish](https://www.tinyfish.ai), a web agent built for AI. Where
search tools stop at retrieval, TinyFish also *acts*: it puts an agent in a real browser that clicks,
fills forms, navigates flows, and works inside applications using saved sessions and password-manager
credentials. Search and page extraction are free.

## Install

```bash
pi install npm:@tiny-fish/pi
```

That installs the five TinyFish skills, which work immediately. They call TinyFish either through the
MCP server this package declares, or through the `tinyfish` CLI — whichever you have.

**Pi ships no MCP client of its own.** To use the bundled MCP server, also install the community
adapter:

```bash
pi install npm:pi-mcp-adapter
```

Without it, the MCP declaration stays dormant and the skills fall back to the CLI:

```bash
npm i -g @tiny-fish/cli && tinyfish auth login
```

Either path works. Pick one — you don't need both.

## Skills

| Skill | What it does |
|---|---|
| `tinyfish-web` | Router — picks the right tool for a web task, and keeps free reads from being done as metered automations |
| `tinyfish-research` | Research orchestrator: plans the work, runs it in passes, compiles deduplicated cited results |
| `tinyfish-automation` | Goal-driven automation: goal writing, structured output, and diagnosing bot detection |
| `tinyfish-authenticated` | Automating logged-in sites with Browser Context Profiles and Vault credentials |
| `tinyfish-browser` | Remote browser sessions driven over CDP from your own code |

Each is also available on demand as `/skill:tinyfish-web`, and so on.

Each skill carries its own safety rules inline — untrusted content handling, the prohibition on
putting credentials in a goal, and confirmation before irreversible actions. `rules/security.md`
ships with the package and documents them in full for readers and reviewers, but the manifest
declares only `./skills`, so pi never loads it as a component. The enforceable copy is the one
inside each skill.

## Authentication

**This package's MCP registration is API-key only.** It sends `X-API-Key` from `TINYFISH_API_KEY`:

```bash
export TINYFISH_API_KEY="sk-tinyfish-..."
```

Keys come from [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys).

**A key is required.** Nothing will prompt you to sign in, on either pi route — the two differ only
in where the key lives:

| Route | Where the key comes from |
|---|---|
| this package | `X-API-Key`, interpolated from `TINYFISH_API_KEY` in the environment pi was started in |
| `tinyfish connect pi` | a literal key the CLI writes into pi's own `mcp.json` |

```bash
npx -y @tiny-fish/cli@latest connect pi --api-key sk-tinyfish-...
```

Use that if you would rather not manage the environment variable — it writes its own entry into your
Pi agent config. Note it stores the key in plain text there, and it does **not** replace this
package's entry; both can coexist, which is why you may see two TinyFish servers.

**When the key is missing or wrong**, the connection fails and the tools never register — so they
are simply absent from pi's tool list rather than erroring when called. Recent adapters print
`Unauthorized: Valid OAuth Bearer token required` on the connection; older ones say nothing at all.
Read that message as "bad or missing API key" regardless of its wording. If the TinyFish tools are
missing, check the key before assuming anything else.

## Tool names

The same tools are named differently depending on how you installed TinyFish. The suffix is the tool;
the prefix only names the install.

| Install | A tool looks like |
|---|---|
| this package + `pi-mcp-adapter` | `tiny-fish_pi__tinyfish_search` |
| `tinyfish connect pi` + `pi-mcp-adapter` | `tinyfish_search` |
| no adapter | `tinyfish search query "..."` (the CLI) |

The long prefix is derived by the adapter from the npm package name — it is not a different product.
This package registers twelve tools directly — search, fetch, the automation, run-management and
batch tools, and the three browser-session tools. The rest of TinyFish's surface stays reachable through the
adapter's `mcp` proxy tool; ask it for a name with `mcp({ search: "tinyfish" })` rather than
guessing one, since the prefix depends on how you installed.

## Privacy

TinyFish's privacy policy: https://www.tinyfish.ai/privacy-policy

## Local file access

The skills themselves read no local files — search, fetch, and automation all go through TinyFish.
Two things on this integration do touch your machine:

- **The CLI fallback.** When no MCP tools are present the skills shell out to `tinyfish`, which reads
  its credential store at `~/.tinyfish/config.json` and reports its own runs to TinyFish. Set
  `TINYFISH_NO_TELEMETRY` to suppress that.
- **Authenticated runs.** `use_profile` and `use_vault` draw on Browser Context Profiles and Vault
  credentials stored with your TinyFish account, not on local files. Website credentials are filled
  into pages by TinyFish without the agent seeing them; the skills prohibit putting a credential in a
  goal string.

The MCP registration reads one environment variable, `TINYFISH_API_KEY`. It reads no `.env` files and
no other local secret.

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
