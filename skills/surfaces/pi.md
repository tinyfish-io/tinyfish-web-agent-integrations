Slot values for the pi package (pi/skills), which reaches TinyFish through pi-mcp-adapter or the tinyfish CLI.

<!-- slot: automation-batch -->
This package does not start
batches itself; kick off runs with `run_web_automation_async` and collect their `run_id`s.

<!-- slot: browser-caveat -->
**Prefer the MCP tools.** Without them, `tinyfish` CLI 0.49 or later has all three:
`tinyfish browser session create`, `tinyfish browser session list` and `tinyfish browser session close
<session_id>`. Run `tinyfish browser session --help` before first use, and close every session you open
— an open session bills until its inactivity timeout.

<!-- slot: host-conversation -->
pi

<!-- slot: profiles-cli -->
Without the MCP tools, the CLI does the same: `tinyfish profile list`, `tinyfish profile create --name <name>`
(prints a link where the user signs in and saves), and `tinyfish profile sign-in <profile_id>` to add
or refresh a site. 

<!-- slot: research-auth -->
The server is `https://agent.tinyfish.ai/mcp`, configured by this package, authenticated by the
`TINYFISH_API_KEY` API key. On an auth error, tell the user to `export
TINYFISH_API_KEY=sk-tinyfish-...` and restart pi, or to run `npx -y @tiny-fish/cli@latest connect pi
--api-key <key>`. On a wallet-balance or rate-limit error, say so plainly.

If no TinyFish tools are available at all, both tools below have CLI equivalents —
`tinyfish search query "<q>"` and `tinyfish fetch content get <url>`. See `tinyfish-web` for the full mapping.

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
three passes is one source, not three. Never sum per-pass counts: that double-counts overlap, and
overlap between passes is expected. You need the set's size at compile time.

For prose-heavy answers rather than structured rows, `references/synthesis.md` covers the shape.

### Fanning out

If you have a `subagent` tool, the passes above can run as parallel children instead — one angle
each, same search budget. Delegation buys context, not capability: the work is identical.

Pi ships none. [`pi-subagents`](https://pi.dev/packages/pi-subagents) adds one, and a child needs
two things before it can do TinyFish research: `pi-mcp-adapter` installed, and the TinyFish server
named in that agent's own `tools:` frontmatter as an `mcp:` entry. A child does not otherwise
inherit your TinyFish tools — a stock one has `read`, `grep`, `find`, `ls`, `bash`, `edit`, `write`
and nothing else, so it would fail at the first search. The bundled `researcher` agent is not a
substitute either; it expects `pi-web-access`, a different provider.

Unless all of that is already set up, **stay sequential.** It is the working path, not a degraded
one. Do not have children shell out to the `tinyfish` CLI as a workaround: it spends the context
delegation exists to save.

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, work it in
passes, then compile and deliver. Pi runs this in your own context by default; if you have a
subagent tool, see "Fanning out" for when to delegate instead.

<!-- slot: research-on-host -->
## How this runs on pi

**Default: you do the work yourself, in passes, compressing as you go.** Pi ships no subagent tool —
its docs say it "intentionally does not include built-in MCP, sub-agents, permission popups, plan
mode, to-dos, or background bash" — so unless something added one, there is nobody to delegate to.
That is fine. The discipline a subagent budget would have enforced, you enforce by hand:

| Rule | Why |
|---|---|
| One angle at a time, in a deliberate order | keeps each pass scoped and reviewable |
| 3–5 searches per angle, then stop | the same budget a subagent would have had |
| **Summarise an angle to its findings before starting the next** | this is the one that matters — never carry raw result lists forward |
| Compile between passes, not at the end | so a long run degrades gracefully instead of falling off a cliff |

The cost is context, not correctness. **Do not refuse solely because no subagent tool is available**
— every normal reason to decline or check in still applies, unchanged. Equally, do not claim to have
fanned out when you did not, and do not silently truncate: if the question needs more passes than
your context will hold, say so and size it down honestly.

**Never hold bulk raw results in context.** Compress as you go. That rule replaces the
"never search in your own context" advice you will find in fan-out-shaped guidance elsewhere.

<!-- slot: research-report-open -->
**Format.** Open with: "I used TinyFish to review {X} sources across {Y} passes." X is the size of
the single running `sources_reviewed` set — not a sum of per-pass numbers, which would double-count
URLs that appeared in more than one pass. If you delegated, union the children's URL lists into that
same set and say "subagents" instead of "passes".

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | One or two `search` calls, or a direct `fetch_content`. Answer. |
| Moderate | A focused question with one clear angle | One pass: 3–5 searches, fetch the best hits, compile. |
| Deep | A clear topic with a few independent angles | 3–4 passes, one per angle, compiling after each. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Repeated rounds of the above, compiling between rounds and re-scoping from what you found. |

With a subagent tool, each pass above becomes a delegated child instead — same budgets, same order.

<!-- slot: security-doc -->
this package's `../../rules/security.md`

<!-- slot: setup -->
## Finding the tools

Pi ships no MCP client of its own, so how these tools appear depends on how TinyFish was installed.
**The suffix is the tool; the prefix only names the install.** Match on the suffix.

| What you see | Call it as |
|---|---|
| `tiny-fish_pi__tinyfish_search` | this package, with `pi-mcp-adapter` installed |
| `tinyfish_search` | registered by `tinyfish connect pi` |
| no TinyFish tools at all | the `tinyfish` CLI over bash — see below |

If a tool named `mcp` exists but no TinyFish tools do, they may be behind the adapter's proxy.
`mcp({ search: "tinyfish" })` lists them. **Call each one by the exact name that search returned**
— never a name from this document. The prefix differs per install, so a hardcoded
`tiny-fish_pi__tinyfish_search` is wrong under CLI registration, where the same tool is
`tinyfish_search`:

```
mcp({ search: "tinyfish" })                          → returns the names available here
mcp({ tool: "<exact name from that result>", args: { ... } })
```

**If that search returns nothing, check for a connection error before concluding anything.** A
TinyFish server that cannot authenticate never finishes connecting, so its tools are absent in the
same way they are absent when no adapter is installed:

| Symptom | Cause | Fix |
|---|---|---|
| No `mcp` tool at all | no MCP adapter installed | use the CLI below, or `pi install npm:pi-mcp-adapter` |
| `MCP: Failed to connect to …Unauthorized` at startup or on `/mcp status` | `TINYFISH_API_KEY` unset or invalid | set the key (see Auth) and restart pi |
| `mcp` exists, search finds nothing, no error shown | older adapters fail silently — still almost always the key | set the key and restart pi |

Never report "TinyFish is not installed" on the strength of missing tools alone — check which of
these it is first.

### No MCP tools: use the CLI

Most pi users have no MCP adapter, and that is fine — the same capabilities are a terminal command
away. **The CLI grammar is two-level and does not match the tool names in these skills**, so run
`tinyfish <group> --help` before your first use of a group and follow the syntax it prints.

| These skills say | CLI equivalent (verified against CLI 0.49) |
|---|---|
| `search` | `tinyfish search query "<query>"` |
| `fetch_content` | `tinyfish fetch content get <url>...` |
| `run_web_automation` | `tinyfish agent run "<goal>" --url <url> --sync` (without `--sync` it streams every step) |
| `run_web_automation_async`, `get_run`, `list_runs`, `cancel_run` | `tinyfish agent run ... --async`, then `tinyfish agent run list`, `get <run_id>`, `cancel <run_id>` |
| `use_profile: true` | `tinyfish agent run ... --use-profile` |
| `profile_id` | `tinyfish agent run ... --use-profile --profile-id <id>` |
| `use_vault: true` | `tinyfish agent run ... --use-vault` |
| `credential_item_ids` | `tinyfish agent run ... --use-vault --credential-item-id <id>` (repeat per item; IDs from `tinyfish vault item list`) |
| `list_profiles`, `create_profile`, profile sign-in | `tinyfish profile list`, `profile create --name <name>`, `profile sign-in <profile_id>` |
| `create_monitor` | `tinyfish monitor create --schedule "<cron>"` with `--url <url>` or `--query "<query>"` |
| `list_monitors`, `get_monitor`, `run_monitor`, `pause_monitor`, `resume_monitor`, `cancel_monitor` | `tinyfish monitor list`, `monitor <get\|run\|pause\|resume\|cancel> <monitor_id>` |
| `create_browser_session`, `list_browser_sessions`, `close_browser_session` | `tinyfish browser session create`, `list`, `close <session_id>` |
| `get_wallet`, `get_search_usage`, `list_fetch_usage` | `tinyfish wallet status`, `search usage`, `fetch usage` |

These are **flags on `agent run`**, not separate command groups. `tinyfish profile` and
`tinyfish vault` manage profiles and credentials; they do not run automations.

Monitors and browser sessions need CLI 0.49 or later. On an older CLI, tell the user to run
`npm i -g @tiny-fish/cli@latest`; never open a browser session you cannot close.

If `tinyfish` is not installed, say so and give the user the fix rather than stopping:
`npm i -g @tiny-fish/cli` (or prefix a single call with `npx -y @tiny-fish/cli@latest`), then
`tinyfish auth login`.

## Auth

**Both pi routes require an API key. Never tell the user to sign in** — nothing will prompt them.
The two differ only in where the key lives:

| Route | Key source |
|---|---|
| this package | `X-API-Key` interpolated from `TINYFISH_API_KEY` in pi's environment |
| `tinyfish connect pi` | a literal key the CLI writes into pi's own `mcp.json` |

A failure shows up on the connection, not on the tool call — the tool itself just never registers.
Recent adapters print `Unauthorized: Valid OAuth Bearer token required`; read it as "bad or missing
API key" regardless of its wording.

Whenever auth is the problem, give the user both fixes: `export TINYFISH_API_KEY=sk-tinyfish-...`
then restart pi, or run `npx -y @tiny-fish/cli@latest connect pi --api-key <key>`. Keys come from
https://agent.tinyfish.ai/api-keys. On a wallet-balance or rate-limit error, say so plainly.
