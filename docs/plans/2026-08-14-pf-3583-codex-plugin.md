# PF-3583 Codex Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an installable TinyFish plugin for Codex that exposes the core web skills and authenticates with `TINYFISH_API_KEY` or OAuth.

**Architecture:** Create a self-contained `codex/` package using Codex's native manifest and bundled MCP configuration. Reuse the three proven Claude skills as the minimal capability surface, adapting only client-specific references and authentication guidance.

**Tech Stack:** Codex plugin manifests, MCP JSON configuration, Markdown skills, Python JSON assertions, bundled Codex plugin validator.

---

## Task 1: Create the native Codex package and dual-auth MCP configuration

**Files:**
- Create: `codex/.codex-plugin/plugin.json`
- Create: `codex/.mcp.json`

**Step 1: Verify the package does not exist yet**

Run:

```bash
python3 "${CODEX_PLUGIN_VALIDATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py}" codex
```

Expected: FAIL because `codex/.codex-plugin/plugin.json` does not exist.

**Step 2: Create the manifest**

Create `codex/.codex-plugin/plugin.json` with:

```json
{
  "name": "tinyfish",
  "version": "1.0.0",
  "description": "Search, fetch, and automate the web with TinyFish.",
  "author": {
    "name": "TinyFish",
    "email": "support@tinyfish.io",
    "url": "https://tinyfish.ai"
  },
  "homepage": "https://docs.tinyfish.ai",
  "repository": "https://github.com/tinyfish-io/tinyfish-web-agent-integrations",
  "license": "MIT",
  "keywords": [
    "web-automation",
    "web-agent",
    "browser-automation",
    "web-scraping",
    "data-extraction",
    "search",
    "fetch"
  ],
  "skills": "./skills/",
  "mcpServers": "./.mcp.json",
  "interface": {
    "displayName": "TinyFish",
    "shortDescription": "Search, fetch, and automate the web",
    "longDescription": "Use TinyFish for live web search, clean page extraction, and browser automation from Codex.",
    "developerName": "TinyFish",
    "category": "Developer Tools",
    "capabilities": ["Interactive", "Read", "Write"],
    "websiteURL": "https://tinyfish.ai",
    "privacyPolicyURL": "https://www.tinyfish.ai/privacy-policy",
    "defaultPrompt": "Use TinyFish to research the web or automate a website."
  }
}
```

**Step 3: Create the MCP configuration**

Create `codex/.mcp.json` with:

```json
{
  "mcpServers": {
    "tinyfish": {
      "type": "http",
      "url": "https://agent.tinyfish.ai/mcp",
      "auth": "oauth",
      "env_http_headers": {
        "X-API-Key": "TINYFISH_API_KEY"
      }
    }
  }
}
```

**Step 4: Validate structure and auth semantics**

Run:

```bash
python3 "${CODEX_PLUGIN_VALIDATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py}" codex
python3 -m json.tool codex/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool codex/.mcp.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("codex/.codex-plugin/plugin.json").read_text())
mcp = json.loads(Path("codex/.mcp.json").read_text())["mcpServers"]["tinyfish"]
assert manifest["mcpServers"] == "./.mcp.json"
assert mcp["url"] == "https://agent.tinyfish.ai/mcp"
assert mcp["auth"] == "oauth"
assert mcp["env_http_headers"] == {"X-API-Key": "TINYFISH_API_KEY"}
PY
```

Expected: all commands pass.

**Step 5: Commit**

```bash
git add codex/.codex-plugin/plugin.json codex/.mcp.json
git commit -m "feat(codex): add TinyFish plugin manifest"
```

## Task 2: Port the three core TinyFish skills to Codex

**Files:**
- Create: `codex/skills/search/SKILL.md`
- Create: `codex/skills/fetch/SKILL.md`
- Create: `codex/skills/agent/SKILL.md`

**Step 1: Copy the established core skills**

Copy these files without changing their capability or tool guidance:

```text
claude/skills/search/SKILL.md -> codex/skills/search/SKILL.md
claude/skills/fetch/SKILL.md  -> codex/skills/fetch/SKILL.md
claude/skills/agent/SKILL.md  -> codex/skills/agent/SKILL.md
```

**Step 2: Run the client-language check and observe the expected failures**

Run:

```bash
rg -n 'Claude|/tinyfish:|first use triggers an OAuth sign-in' codex/skills
```

Expected: matches showing the Claude-oriented invocation and OAuth-only wording that must be adapted.

**Step 3: Make the minimal Codex adaptations**

- Replace OAuth-only setup claims with: `Uses TINYFISH_API_KEY when available; otherwise authenticate the TinyFish MCP server with OAuth.`
- Replace `/tinyfish:search`, `/tinyfish:fetch`, and `/tinyfish:agent` cross-references with plain `TinyFish search skill`, `TinyFish fetch skill`, and `TinyFish agent skill` wording.
- Remove the Claude-only `$ARGUMENTS` placeholder.
- Preserve tool names, parameters, cost guidance, and escalation rules.

**Step 4: Validate the skills**

Run:

```bash
test "$(find codex/skills -name SKILL.md | wc -l | tr -d ' ')" = "3"
! rg -n 'Claude|/tinyfish:|\$ARGUMENTS|first use triggers an OAuth sign-in' codex/skills
python3 "${CODEX_PLUGIN_VALIDATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py}" codex
```

Expected: exactly three skills, no stale client-specific wording, validator passes.

**Step 5: Commit**

```bash
git add codex/skills/search/SKILL.md codex/skills/fetch/SKILL.md codex/skills/agent/SKILL.md
git commit -m "feat(codex): add TinyFish web skills"
```

## Task 3: Document installation and expose Codex in the repository index

**Files:**
- Create: `codex/README.md`
- Modify: `README.md`

**Step 1: Write the Codex README**

Document:

1. What the plugin provides: search, fetch, and browser automation.
2. Install and enable the plugin, then start a new Codex session.
3. Existing-key path: set `TINYFISH_API_KEY` before starting Codex; the plugin sends it only as `X-API-Key`.
4. OAuth fallback: when no key is set, authenticate the bundled server with `codex mcp login tinyfish` if Codex prompts for connection.
5. The API key is not bundled, discovered, or written by this plugin.
6. Privacy-policy and local-file-access statements matching the existing integrations.

**Step 2: Add Codex to the root integration table**

Add:

```markdown
| [Codex](./codex) | Plugin for [Codex](https://openai.com/codex/) — search, fetch, and browser automation with API-key or OAuth authentication |
```

**Step 3: Validate documentation and package integrity**

Run:

```bash
rg -n 'TINYFISH_API_KEY|X-API-Key|OAuth|codex mcp login tinyfish' codex/README.md
rg -n '\[Codex\]\(\./codex\)' README.md
! rg -n 'Claude Code|Grok Build|/tinyfish:' codex
python3 "${CODEX_PLUGIN_VALIDATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py}" codex
git diff --check
```

Expected: required auth/install language is present, no stale client instructions remain, validator and diff check pass.

**Step 4: Run final repository checks**

Run:

```bash
python3 -m json.tool codex/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool codex/.mcp.json >/dev/null
git status --short
git diff --stat origin/main...HEAD
```

Expected: only the approved design/plan documents, `codex/`, and root `README.md` differ from `origin/main`.

**Step 5: Commit**

```bash
git add codex/README.md README.md
git commit -m "docs(codex): add TinyFish plugin setup"
```

## Task 4: Prove Codex can discover and install the completed package

**Files:**
- No repository files changed.
- Temporary marketplace under the system temporary directory only.

**Step 1: Create an isolated local marketplace around the completed package**

Run in one shell session:

```bash
PF3583_MARKETPLACE_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/pf3583-marketplace.XXXXXX")
trap 'find "$PF3583_MARKETPLACE_ROOT" -depth -delete' EXIT
python3 "${CODEX_PLUGIN_CREATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py}" tinyfish \
  --path "$PF3583_MARKETPLACE_ROOT/plugins" \
  --marketplace-path "$PF3583_MARKETPLACE_ROOT/.agents/plugins/marketplace.json" \
  --with-marketplace \
  --marketplace-name pf-3583-local
cp -R codex/. "$PF3583_MARKETPLACE_ROOT/plugins/tinyfish/"
python3 "${CODEX_PLUGIN_VALIDATOR:-${HOME}/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py}" \
  "$PF3583_MARKETPLACE_ROOT/plugins/tinyfish"
printf '%s\n' "$PF3583_MARKETPLACE_ROOT"
```

Expected: the copied plugin validates and the final line prints the temporary marketplace root.

**Step 2: Install and inspect the plugin**

Using the printed path, run:

```bash
codex plugin marketplace add <temporary-marketplace-root>
codex plugin add tinyfish@pf-3583-local
codex plugin list
```

Expected: `tinyfish@pf-3583-local` is installed and enabled with its skills and MCP server discoverable.

**Step 3: Remove the temporary Codex configuration**

Run:

```bash
codex plugin remove tinyfish@pf-3583-local
codex plugin marketplace remove pf-3583-local
find "$PF3583_MARKETPLACE_ROOT" -depth -delete
trap - EXIT
```

Expected: both commands succeed, the temporary marketplace is removed, and no repository files changed.

**Step 4: Run the final task gate**

Run:

```bash
git status --short
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
```

Expected: only the approved design/plan documents, `codex/`, and root `README.md` differ from `origin/main`.
