# Changelog

## 1.3.0 (2026-08-17)

### Added
- Skill: `/tinyfish:doctor` — runs the CLI's `doctor` for the config checks, then proves this harness can actually reach TinyFish, which the CLI cannot do (it has no way to borrow the harness's OAuth token). Degrades to the reach check alone on surfaces with no shell.
- Skill: `/tinyfish:feedback` — files a structured GitHub issue, with a preview the user has to approve before anything is sent.

The `doctor` skill reads doctor's `schema_version` `3` (CLI 0.22+): two verdicts (`ok_harnesses`, `ok_cli`), `scope` on each check, and an exit code driven by the harness scope alone.

Both skills were previously published only through the `tinyfish-cookbook` marketplace copy of this plugin. This version supersedes that copy's 1.2.3 — the plugin cache is keyed by version, so anything lower would keep serving the stale copy.

## 1.2.0 (2026-08-14)

### Added
- API-key auth alongside OAuth: the bundled MCP server sends `TINYFISH_API_KEY` as `X-API-Key` when it is set in the environment. An unset, empty, or rejected key falls back to the OAuth sign-in, so nothing changes for users who never set one.

## 1.1.0 (2026-07-21)

### Added
- Bundled remote MCP server (`https://agent.tinyfish.ai/mcp`) via `.mcp.json`, loaded automatically by the plugin system — works in sandboxed surfaces (Claude.ai, Desktop, Cowork) where the CLI can't be installed. In Claude Desktop this still requires one manual "Install" click on the plugin's Connectors tab.
- Skill: `/tinyfish:search` — free, token-efficient web search with recency/date filtering and news/research-paper scoping
- Skill: `/tinyfish:fetch` — free, clean content extraction from up to 10 URLs in parallel
- Skill: `/tinyfish:agent` — browser automation (600 free automation credits for new users, then plan credits), batch runs, and raw CDP browser sessions
- Plugin-level `README.md` with a privacy-policy link and a note on local file access by skills

### Removed
- Skill: `/tinyfish:tunneling` — expose local ports via tinyfi.sh SSH tunnels
- Skill: `/tinyfish:use-tinyfish` — the CLI-based toolkit, replaced entirely by `search`/`fetch`/`agent` so this plugin is MCP-only and works without a local CLI install

## 1.0.0 (2026-04-15)

### Added
- Initial release of the TinyFish CLI plugin for Claude Code
- Skill: `/tinyfish:use-tinyfish` — complete CLI toolkit with 4-tool escalation ladder
  - `tinyfish search query` — web search with ranked results
  - `tinyfish fetch content get` — clean markdown extraction from URLs
  - `tinyfish agent run` — browser automation via natural language goals
  - `tinyfish browser session create` — headless browser with CDP control
- Skill: `/tinyfish:tunneling` — expose local ports via tinyfi.sh SSH tunnels
- Pre-flight checks for CLI installation and authentication
- Marketplace manifest for plugin discovery via `tinyfish-io/tinyfish-cookbook`
