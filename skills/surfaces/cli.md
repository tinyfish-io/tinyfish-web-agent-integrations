Slot values for the skills the tinyfish CLI installs (cli/skills), which reach TinyFish through `tinyfish` commands over the shell.

<!-- slot: automation-batch -->
To start many runs at once from a CSV with `url,goal` columns, use `tinyfish agent batch run --input
<file>`; `tinyfish agent batch get <batch_id>` and `agent batch cancel <batch_id>` manage it.

<!-- slot: browser-caveat -->
From the CLI these are `tinyfish browser session create`, `tinyfish browser session list` and `tinyfish
browser session close <session_id>`. Run `tinyfish browser session --help` before first use, and close
every session you open — an open session bills until its inactivity timeout.

<!-- slot: host-conversation -->
coding-agent

<!-- slot: profiles-cli -->
From the CLI, `tinyfish profile create --name <name>` replaces steps 1–3: it prints a link where the
user signs in and saves (`--site <site>` names the site; `--import-cookies` copies Chrome cookies
instead). `tinyfish profile sign-in <profile_id>` adds or refreshes a site on an existing profile, and
`tinyfish profile list` shows each profile's signed-in sites.

<!-- slot: research-auth -->
Both tools run through the `tinyfish` CLI: `search` is `tinyfish search query "<q>"` and
`fetch_content` is `tinyfish fetch content get <url>...`. See `tinyfish-web` for the full mapping.
`search query` has domain, location, language and page filters only; the recency, date-range and
`domain_type` filters in `references/searching.md` are MCP-only, so put the time window in the query. On
an auth error, run `tinyfish auth status`, then tell the user to run `tinyfish auth login` or set
`TINYFISH_API_KEY`. On a wallet-balance or rate-limit error, say so plainly.

<!-- slot: research-broad-search -->
The bulk of the work.

<!-- slot: research-dispatch -->
## Step 2: Work the passes

Each pass takes one angle and ends with distilled findings, not raw output. Read
`references/fan-out.md` before splitting a question — it covers decomposing into angles that don't
overlap, and it applies whether you run the angles yourself or delegate them.

Per pass:

1. State the sub-question as a question.
2. Run 3–5 `search` calls against it — `references/searching.md` covers writing them well.
3. `fetch_content` the hits worth reading, up to 10 URLs per call — see `references/fetching.md`.
4. **Compress before moving on.** Write down the findings, the qualifying results, and the count of
   unique source URLs you reviewed. Then drop the raw results from your working set.
5. Only then start the next angle.

Track `sources_reviewed` in **one running set for the whole task**, not per pass. Add every source
URL you see in `search` results or fetch, and let the set dedupe them — the same URL surfacing in
three passes is one source, not three. Never sum per-pass counts: that double-counts overlap. You need
the set's size at compile time.

For prose-heavy answers rather than structured rows, `references/synthesis.md` covers the shape.

### Fanning out

If you have a subagent tool, run the passes as parallel children instead — one angle each, same search
budget, launched in a single message so they run concurrently. A child with a shell can run `tinyfish`
itself. Give each one the **absolute** path to `references/searching.md` (and `references/fetching.md`
if it reads pages), its sub-question, what qualifies as a result, and the exact output format. End
every child prompt with this line, verbatim:

```
End with EXACTLY: `sources_reviewed: N` where N = the number of **unique** source URLs you reviewed —
every distinct URL you saw in `search` results (across all calls and retries) or fetched. Count a URL
once even if you both saw it in search and then fetched it.
```

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, work it in
passes, then compile and deliver. If you have a subagent tool, see "Fanning out" for when to delegate
instead.

<!-- slot: research-on-host -->
## Context is the budget

Every `tinyfish search` and `tinyfish fetch` prints straight into your context. **Summarise an angle
to its findings before starting the next, and never carry raw result lists forward.** If the question
needs more passes than your context will hold, say so and size it down honestly — don't silently
truncate, and don't claim to have fanned out when you didn't.

<!-- slot: research-report-open -->
**Format.** Open with: "I used TinyFish to review {X} sources across {Y} passes." X is the size of
the single running `sources_reviewed` set — not a sum of per-pass numbers, which would double-count
URLs that appeared in more than one pass. If you delegated, add each child's `sources_reviewed` and
say "subagents" instead of "passes".

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | One or two `search` calls, or a direct `fetch_content`. Answer. |
| Moderate | A focused question with one clear angle | One pass: 3–5 searches, fetch the best hits, compile. |
| Deep | A clear topic with a few independent angles | 3–4 passes, one per angle, compiling after each. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Repeated rounds of the above, compiling between rounds and re-scoping from what you found. |

With a subagent tool, each pass above becomes a delegated child instead — same budgets, same order.

<!-- slot: security-doc -->
<https://raw.githubusercontent.com/tinyfish-io/tinyfish-web-agent-integrations/main/pi/rules/security.md>

<!-- slot: setup -->
## Running these through the CLI

These skills name TinyFish's MCP tools. Here you call each one as a `tinyfish` command over your
shell. **The CLI grammar is two-level and does not match the tool names**, so run `tinyfish <group>
--help` before your first use of a group and follow the syntax it prints. Where this table and the
skill text disagree, the table is right for the CLI.

| These skills say | CLI command (CLI 0.49) |
|---|---|
| `search` | `tinyfish search query "<query>"` |
| `fetch_content` | `tinyfish fetch content get <url>...` (up to 10 URLs) |
| `run_web_automation` | `tinyfish agent run "<goal>" --url <url> --sync` — `--url` is required. Without `--sync` it streams every step into your context |
| `run_web_automation_async` | `tinyfish agent run "<goal>" --url <url> --async` — prints the `run_id` |
| `get_run`, `list_runs`, `cancel_run` | `tinyfish agent run get <run_id>`, `agent run list`, `agent run cancel <run_id>` |
| `batch_status`, `batch_cancel` | `tinyfish agent run get <run_id>` / `agent run cancel <run_id>`, once per run |
| `output_schema` | `--output-schema '<json>'` or `--output-schema-file <path>` on `agent run` |
| `browser_profile` | `--browser-profile lite\|stealth` on `agent run` |
| `session_id` | `--session-id <uuid>` on `agent run`. **Optional on the CLI**; pass a fresh UUID when running several `--sync` runs in parallel |
| `proxy_config` | not available on `agent run` |
| `use_profile: true`, `profile_id` | `--use-profile`, `--use-profile --profile-id <id>` on `agent run` |
| `use_vault: true`, `credential_item_ids` | `--use-vault`, `--use-vault --credential-item-id <id>` (repeat per item; IDs from `tinyfish vault item list`) |
| `list_profiles`, `create_profile`, profile sign-in | `tinyfish profile list`, `profile create --name <name>`, `profile sign-in <profile_id>` |
| `create_monitor` | `tinyfish monitor create --schedule "<cron>"` with `--url <url>` or `--query "<query>"` |
| `list_monitors`, `get_monitor`, `run_monitor`, `pause_monitor`, `resume_monitor`, `cancel_monitor` | `tinyfish monitor list`, `monitor <get\|run\|pause\|resume\|cancel> <monitor_id>` |
| `create_browser_session`, `list_browser_sessions`, `close_browser_session` | `tinyfish browser session create`, `list`, `close <session_id>` |
| `get_wallet`, `get_search_usage`, `list_fetch_usage` | `tinyfish wallet status`, `search usage`, `fetch usage` |

`search query` takes `--include-domains`, `--exclude-domains`, `--location`, `--language` and `--page`
only. The recency, date-range and `domain_type` filters in `tinyfish-research` are MCP-only; put the
time window in the query text instead.

The CLI checks flags itself: where a skill says "the tool schema your client shows you is
authoritative", read that as `tinyfish <group> --help`.

Output is JSON by default, which is what you want; `--pretty` is for humans. Monitors and browser
sessions need CLI 0.49 or later — on an older CLI, tell the user to run `tinyfish upgrade`, and never
open a browser session you cannot close.

**Pick one route per task.** If your harness also has TinyFish MCP tools, you may use them instead,
but CLI runs use your API key and MCP runs use the MCP token: `tinyfish agent run get` returns 404 for
a run started through MCP, and the reverse.

## Auth

The CLI authenticates with an API key. On an auth error, run `tinyfish auth status` to see which key
is active and where it came from, then give the user the fix: `tinyfish auth login`, or `export
TINYFISH_API_KEY=sk-tinyfish-...`. Keys come from https://agent.tinyfish.ai/api-keys. Never ask for
the key in chat. On a wallet-balance or rate-limit error, say so plainly.
