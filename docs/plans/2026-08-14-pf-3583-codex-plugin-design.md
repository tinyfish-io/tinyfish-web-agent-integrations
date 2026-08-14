# PF-3583 Codex Plugin Design

## Goal

Make Codex a first-class TinyFish installation target so a user can install one plugin and use TinyFish search, fetch, and browser automation with either an existing API key or OAuth.

## Scope

Create a native `codex/` plugin package containing:

- `.codex-plugin/plugin.json` for Codex discovery and presentation.
- `.mcp.json` for the hosted TinyFish MCP server.
- Focused search, fetch, and browser-automation skills.
- A README covering installation, API-key authentication, OAuth fallback, capabilities, privacy, and local-file access.
- A root README entry for Codex.

The plugin will reuse the established Claude skill content for the three core capabilities and adapt only the client-specific wording needed by Codex. It will not port Grok's advanced research orchestration, authenticated-automation, or raw-browser workflow skills because those are not required for the onboarding experiment's install-and-use outcome.

## Authentication

The MCP server configuration will map `TINYFISH_API_KEY` to the `X-API-Key` request header through Codex's `env_http_headers` support. OAuth remains the fallback when that environment variable is absent.

The package will never contain a literal API key, acquire a key, inspect local secrets, or write credentials. Key acquisition and propagation belong to the surrounding onboarding flow.

## User Flow

1. The user installs and enables the TinyFish plugin in Codex.
2. Codex loads the plugin's skills and TinyFish MCP server in a new session.
3. If `TINYFISH_API_KEY` is available, Codex sends it as `X-API-Key`.
4. Otherwise, the TinyFish MCP server uses its OAuth flow.
5. The user can ask Codex to search, fetch a URL, or automate a website.

## Validation

- Validate the Codex manifest with the bundled plugin validator.
- Parse all new JSON files.
- Verify every skill directory contains a valid `SKILL.md`.
- Assert the MCP configuration maps only `TINYFISH_API_KEY` to `X-API-Key` and retains OAuth fallback.
- Check the new package for stale Claude- or Grok-specific setup instructions.
- Install from a temporary local marketplace and confirm Codex discovers the plugin when supported by the local CLI.

## Explicit Non-goals

- Creating or discovering a TinyFish API key.
- Adding custom UI, hooks, binaries, scripts, or dependencies.
- Refactoring Claude and Grok packages into shared generated sources.
- Porting advanced Grok workflows that the initial Codex onboarding path does not require.
