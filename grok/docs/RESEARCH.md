# Research: shipping TinyFish as a Grok Build plugin

Date: 2026-07-26. Sources: `xai-org/plugin-marketplace` (README, CONTRIBUTING, scripts),
`exa-labs/exa-grok-plugin` @ `7d1f8407`, `xai-org/plugin-marketplace#56` (merged),
`docs.tinyfish.ai` (`llms.txt`, MCP integration, Search/Fetch API references), live probes of
`agent.tinyfish.ai`.

---

## 1. How the marketplace works

`xai-org/plugin-marketplace` is an **index, not a host**. A submission is one entry appended to
`.grok-plugin/marketplace.json` plus a regenerated `.grok-plugin/plugin-index.json`. PR #56 (Exa)
touched exactly those two files — 13 + 18 added lines, nothing else.

| Fact | Detail |
|---|---|
| Catalog | `.grok-plugin/marketplace.json` — the only source of truth |
| Component index | `.grok-plugin/plugin-index.json` — generated, never hand-edited |
| Third-party source | `source: {source: "url", url, sha}` — plugin files stay in our repo, cloned at install |
| SHA pinning | Full 40-char lowercase commit SHA. Branches, tags, short SHAs rejected by `validate-catalog.py`. Grok Build re-verifies `git rev-parse HEAD == sha` after clone |
| CI | `validate-catalog.py` + `generate-plugin-index.py --check`; code-owner review required |
| Manifest | `.grok-plugin/plugin.json` (or `.claude-plugin/plugin.json`) |

Components the indexer actually scans (`scripts/plugin_catalog.py:308-313`): `skills/`,
`commands/`, `agents/`, `.mcp.json`, `hooks/hooks.json`, `.lsp.json`. **Nothing else is indexed** —
Exa's `rules/security.md` is invisible to the index. It's shipped for the reviewer and for the
agent to read, not as a registered component.

### Review criteria worth pre-empting

CONTRIBUTING names the things that send PRs back. Three matter for us:

1. **Personal-account source for a branded plugin** — "reads as a possible impersonation and *will*
   be questioned." Publishing under the official org is called out as "the single biggest thing that
   speeds up review."
2. **Generic `keywords`/`domains`** — these power Grok Build's proactive plugin CTA. `web search`,
   `scraping`, `browser`, `automation` would mis-fire the CTA on unrelated prompts and get pushed
   back. Must be brand-scoped.
3. **Parallel/duplicate entries** for one product — updates go through a `sha` bump, not a second
   entry.

Security bar: no `curl | bash`, no remote code fetch-and-exec, no reading `.env`/`~/.ssh`/env vars,
least-privilege MCP scope, no obfuscated blobs, no prompt injection in `SKILL.md`. Declaring network
endpoints and credentials in the README is explicitly requested and speeds review.

---

## 2. What Exa ships (our competitor's shape)

16 files, zero executable code:

```
.grok-plugin/plugin.json     manifest: name, version, description, author, repository, license, keywords
.mcp.json                    one hosted HTTP MCP server + a `note` field describing auth and tools
README.md                    install walkthrough, tool table, skill table, resource links
rules/security.md            prompt-injection / untrusted-content guidance
skills/exa-search/SKILL.md   205-line research orchestrator
skills/exa-search/references/*.md   11 files, 437 lines: searching, filtering, extraction,
                             synthesis, source-quality, and 6 domain pattern files
```

`.mcp.json` is four lines of substance:

```json
{ "mcpServers": { "exa": { "type": "http", "url": "https://mcp.exa.ai/mcp/oauth",
  "note": "…OAuth on first connection… Tools: web_search_exa, web_fetch_exa." } } }
```

Two MCP tools. One skill. **The plugin's entire value-add over "just add the MCP server" is the
skill** — a progressive-disclosure orchestrator that classifies query complexity (Extremely Simple
→ Complex), fans out subagents so raw search output never enters the main context, points each
subagent at the right reference file, then dedupes, validates coverage, and formats to one screen.

The pattern is worth copying wholesale:

- **Thin `SKILL.md`, fat `references/`.** The skill is loaded always; references are read
  just-in-time by the subagent that needs them. Keeps the always-on token cost low.
- **Token isolation as an explicit rule.** "Never run bulk searches in your main context."
- **A complexity gate with a confirm-when-ambiguous branch.** Prevents spinning up 5 subagents to
  answer "what year was X founded."
- **`sources_reviewed: N`** — each subagent reports how many results it saw, and the orchestrator
  opens with "I used Exa to review {X} sources across {Y} subagents." Cheap, effective attribution
  that puts the brand in every answer.
- **Anti-fallback instruction.** On auth/rate-limit errors, surface the fix — do *not* silently fall
  back to generic web search. Protects the integration from looking useless when auth lapses.

PR #56's framing is also instructive: it led with third-party benchmark numbers (RAG groundedness,
people-search recall, code-extraction ROUGE-L, each against named competitors), then adoption proof
(native Claude connector, Cursor, Codex, Windsurf, Zed, Gemini CLI), then contents. It cleared review
and merged as `efcdd0c`-adjacent history alongside Tavily.

Tavily is in the catalog with the same architecture (hosted MCP + OAuth + official skills). Firecrawl
too. **Search-and-extract is a crowded shelf in this marketplace: exa, tavily, firecrawl.**

---

## 3. What TinyFish has

TinyFish already runs a hosted MCP server. Verified live:

| Probe | Result |
|---|---|
| `POST https://agent.tinyfish.ai/mcp` | `401` + `WWW-Authenticate: Bearer resource_metadata=…` — spec-correct MCP OAuth challenge |
| `/.well-known/oauth-protected-resource/mcp` | Present; authorization server `agent.tinyfish.ai`, JWKS at `clerk.tinyfish.ai` |
| `/.well-known/oauth-authorization-server` | `registration_endpoint` present → **dynamic client registration works**; `authorization_code` + `refresh_token`; PKCE S256 |

That means the Exa install path works identically for us: install plugin → `/mcp` → press `i` →
browser OAuth → ready. **No API key is pasted anywhere, so the plugin repo contains no secrets by
construction.**

### Tool surface (17 tools, one server)

| Group | Tools | In scope? |
|---|---|---|
| Web automation | `run_web_automation`, `run_web_automation_async`, `get_run`, `cancel_run` | yes |
| | `list_runs` | no — telemetry |
| Batch | `batch_create`, `batch_status`, `batch_cancel` (up to 8) | yes |
| Search | `search` | yes |
| | `run_big_search`, `get_search_result` | **no — experimental** |
| | `get_search_usage` | no — telemetry |
| Fetch | `fetch_content` | yes |
| | `list_fetch_usage` | no — telemetry |
| Browser | `create_browser_session` | yes |
| | `list_browser_sessions` | no — telemetry |

Capability detail that matters for skill design:

- **`search`** — `recency_minutes`, `after_date`/`before_date`, `include_domains`/`exclude_domains`,
  `domain_type` ∈ {`web`, `news`, `research_paper`}, `pub_year_min`/`pub_year_max` (research only),
  `location`/`language` with auto-resolution, `page` 0–10. Research results carry `authors`,
  `venue`, `year`, `cited_by_count`, `pdf_url`. Plus **`purpose`** — a free-text statement of *why*
  you're searching, used as extra intent signal. Exa has no equivalent; it's a natural fit for an
  agent that always knows its own task.
- **`fetch_content`** — up to 10 URLs/request, renders JS, `markdown`/`html`/`json`,
  `include_selectors`/`exclude_selectors` (CSS-scoped extraction, 1–20 entries, with
  `unmatched_selectors` + `candidate_selectors` retry hints), conditional requests via
  `if_none_match`/`if_modified_since`, `ttl` cache control, per-URL `errors[]` that don't fail the
  batch. Also takes `purpose`.
- **`run_web_automation`** — natural-language `goal` + `url`, multi-step click/navigate/fill/login,
  `output_schema` for structured output, `browser_profile: "lite" | "stealth"`, live streaming URL,
  step screenshots and HTML snapshots.
- **Browser Context Profiles** — persist logged-in cookies/localStorage/sessionStorage; pass
  `use_profile: true` (+ optional `profile_id`) to reuse. **Vault** (`use_vault: true`) pulls
  credentials from a connected password manager to repair stale sessions mid-run.
- **`create_browser_session`** — remote stealth Chrome, CDP WebSocket URL for
  Playwright/Puppeteer/Selenium.

### `run_big_search` is excluded

It's an experimental tool, and shipping it next to `search` creates a routing ambiguity the agent has
to resolve on every query — "is this big enough for big search?" — with a 2-to-15-minute penalty for
guessing wrong. Deep research is handled the way Exa does it: client-side subagent fan-out over
`search` and `fetch_content`, both free, with progress visible the whole time.

Corroborating signal that it isn't production surface: **`run_big_search` appears nowhere in the
OpenAPI specs.** `openapi/search.json` exposes exactly two operations, `GET /` and `GET /usage`.
There is no REST equivalent — it exists only at the MCP layer.

`get_search_result` goes with it: its only purpose is polling a `run_big_search` session.

**What "excluding" can and cannot do.** Grok Build has no per-tool allowlist for MCP servers — a
plugin ships skills, agents, hooks, MCP servers, and LSP servers, and tools arrive namespaced
`<server>__<tool>`. Tool-level `deny` rules exist under `[permission] rules` with the `MCPTool`
filter, but that's *user* config, not something a plugin can ship. So the tool will still appear in
the list. Exclusion means three things we actually control:

1. It is absent from the README tool table and from every skill — no discovery path.
2. The router skill carries an explicit negative: use `search`; do not call `run_big_search`.
3. **Ask TinyFish to gate it server-side.** This is the only real fix, and worth raising internally —
   an experimental tool on the default MCP endpoint is a problem for every client, not just this
   plugin.

### What `batch` covers: the web agent only

Not search, not fetch. The REST surface settles it:

| API | Operations | Batch? |
|---|---|---|
| `openapi/main.json` (agent) | `POST /v1/automation/run-batch` (max 100, atomic all-or-nothing), `POST /v1/runs/batch`, `POST /v1/runs/batch/cancel` | yes, automation only |
| `openapi/search.json` | `GET /`, `GET /usage` | no |
| `openapi/fetch.json` | `POST /`, `GET /usage` | no |

The MCP `batch_*` tools are the automation batch and nothing else — `batch_create` is documented as
"start multiple web automations simultaneously (up to 8); each run opens its own browser session,"
and `batch_status` polls *runs*.

So the parallelism story differs per capability, and the skills should say so plainly:

- **Automation** → `batch_create`, up to 8 concurrent. Note the **MCP cap is 8 while REST allows
  100** — MCP users get the lower limit. Poll `batch_status` every 30–60s until `all_terminal`.
- **Fetch** → no batch tool needed; `fetch_content` already takes up to **10 URLs per request**, with
  per-URL `errors[]` so one bad URL doesn't fail the batch. That *is* its batch form.
- **Search** → no batch at any layer. Parallelism is just multiple `search` calls, which is exactly
  what subagent fan-out does.

Pricing signal for the README/PR: `search` and `fetch_content` are **free for all users**;
automation is 1 credit per step; browser sessions 1 credit = 4 browser-minutes.

---

## 4. Should agent + browser go in the same plugin as search/fetch?

**Yes — one plugin.** Three reasons, in order of weight.

**It's one MCP server and one OAuth grant.** All 17 tools live behind `agent.tinyfish.ai/mcp`.
Splitting the plugin would not split the tool list — both halves would still load all 17 tools —
unless TinyFish first ships scoped endpoints (there is precedent: `/mcp/chatgpt` exists). So a split
today buys nothing technical and costs a second OAuth connection plus a duplicate-entry argument
with reviewers. CONTRIBUTING explicitly pushes back on "a parallel entry for an existing plugin."

**Search-only is a losing position.** exa, tavily, and firecrawl are already in the catalog doing
search-and-extract, and Exa arrived with benchmark tables. Entering as the fourth semantic-search
plugin invites a direct benchmark comparison on the one axis where the shelf is most contested. The
capability no one else in the catalog has is **multi-step interactive automation on
authenticated sites** — Browser Context Profiles + Vault + goal-driven runs. That is the reason for
a reviewer to merge a fourth web plugin, and it only exists in the combined plugin.

**The capabilities compose within a single task.** "Find our competitors' pricing, log into our
dashboard, and compare" is search → fetch → authenticated automation in one turn. A skill that owns
the whole chain can route to the cheapest sufficient tool — and there's real routing value here:
`fetch_content` is free and should always be preferred over a 1-credit-per-step automation run when
the task is only *reading* a page. Split plugins can't enforce that; the docs already state the
preference, so a skill can.

**The cost, stated honestly:** 17 tool definitions in every conversation is a large always-on
context tax, roughly 8× Exa's two tools. Mitigations, in the plan below: skills that name the
correct tool for each job so the model doesn't scan the whole list; a decision table at the top of
the routing skill; and a follow-up ask to TinyFish for a scoped MCP endpoint if tool-count pressure
shows up in practice. This is a real tradeoff, not a free lunch — but it's the right side of it,
because the agent tools *are* the differentiator.

**Excluded from skills despite being on the server:** `run_big_search` and `get_search_result`
(experimental — see above), plus `get_search_usage`, `list_fetch_usage`, `list_browser_sessions`, and
`list_runs`, which are billing/telemetry surface rather than task surface. All stay reachable as
tools; no skill teaches them.

---

## 5. Open items

- **Repo ownership.** Building at `shuhaodo/tinyfish-grok-plugin` for now; **must move to
  `tinyfish-io/` before the marketplace PR** or review will question it. This is the single
  highest-leverage item.
- **No benchmarks to cite.** Exa's PR led with numbers. We have none published. Either produce
  head-to-head numbers on search/fetch quality, or lead the PR with the capability gap (authenticated
  multi-step automation) instead of quality claims. Recommend the latter — it's true and unarguable.
- **Expired local API key.** `tinyfish search`/`fetch` CLI returned `401 Invalid or expired API key`
  during this research (the key configured in `~/.tinyfish/config.json`). Doesn't block the
  plugin — the plugin uses OAuth, not keys — but blocks live end-to-end verification of tool
  behaviour. Needs a fresh key to validate the skills against real responses.
- **Ask TinyFish to gate `run_big_search` server-side.** Keeping an experimental tool on the default
  `/mcp` endpoint pushes a routing ambiguity onto every MCP client. A scoped endpoint (precedent:
  `/mcp/chatgpt`) or a flag would fix it properly; the plugin can only decline to document it.
- **Tool count.** With the experimental and telemetry tools excluded from the skills, 9 tools are
  actually taught, but all 17 still load. If context pressure shows up in practice, a scoped endpoint
  is the same fix.
