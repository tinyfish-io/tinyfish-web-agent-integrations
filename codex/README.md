# TinyFish for Codex

Search the web, fetch clean content from pages, and automate multi-step browser workflows with TinyFish's hosted MCP server.

## Installation

1. Start Codex and open the plugin browser:

   ```text
   codex
   /plugins
   ```

2. Find **TinyFish** and install it. If it is installed but turned off, select it and press Space to enable it.
3. Start a new Codex session so the plugin's skills and tools are available.

## Authentication

If you already have a TinyFish API key, set `TINYFISH_API_KEY` before starting Codex:

```bash
export TINYFISH_API_KEY="your-api-key"
codex
```

The plugin sends that value to the TinyFish MCP server only as the `X-API-Key` HTTP header. It does not bundle an API key, search local files or settings to discover one, or write the key anywhere.

If `TINYFISH_API_KEY` is not set, the plugin falls back to OAuth. If Codex prompts you to connect TinyFish, run:

```bash
codex mcp login tinyfish
```

## Privacy

TinyFish's privacy policy: https://www.tinyfish.ai/privacy-policy

## Local file access

None of these skills read local files. All operations go through the TinyFish MCP server.
