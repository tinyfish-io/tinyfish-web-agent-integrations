Slot values for the Kiro power (kiro/tinyfish/skills), which reaches TinyFish through the hosted MCP server declared in the power's `mcp.json`.

<!-- slot: automation-batch -->
This power does not start
batches itself; kick off runs with `run_web_automation_async` and collect their `run_id`s.

<!-- slot: browser-caveat -->


<!-- slot: host-conversation -->
Kiro

<!-- slot: profiles-cli -->


<!-- slot: research-auth -->
The server is `https://agent.tinyfish.ai/mcp`, declared by this power and authenticated by OAuth on
first connection. On an auth error, or when the server shows no tools, first check which setup this
is. If the user registered the server by hand with an API key instead, there is no OAuth sign-in: the
key is unset, missing from **Mcp Approved Env Vars**, or revoked — see "Setup and auth" in the
`tinyfish-web` skill. For the power's own server, Kiro does not open the sign-in on its own: tell the
user to sign in to the power's `tinyfish` MCP server — in the Kiro IDE, open the Kiro
panel (ghost icon), right-click the TinyFish server under **MCP Servers**, and choose
**Reauthenticate** (if the server isn't listed, trust the workspace first — Kiro may not start a
power's servers in Restricted Mode); in Kiro CLI, press Ctrl+Y at the "requires OAuth" prompt or run `/mcp` for the
link — and finish the browser sign-in. Do not fall back to built-in web search without saying so.
Never ask for an API key in chat. On a wallet-balance or rate-limit error, say so plainly.

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

If you have a subagent tool and its children can call the TinyFish MCP tools, run the passes as
parallel children instead — one angle each, same search budget, launched in a single message so they
run concurrently. A child without those tools cannot search; work that angle yourself. Give each one
the **absolute** path to `references/searching.md` (and `references/fetching.md` if it reads pages),
its sub-question, what qualifies as a result, and the exact output format. End every child prompt
with this line, verbatim:

```
End with a `sources:` list of every **unique** source URL you reviewed, one per line — every distinct
URL you saw in `search` results (across all calls and retries) or fetched — then EXACTLY
`sources_reviewed: N` where N is the length of that list.
```

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, work it in
passes, then compile and deliver. If you have a subagent tool, see "Fanning out" for when to delegate
instead.

<!-- slot: research-on-host -->
## Context is the budget

Every `search` and `fetch_content` result lands straight in your context. **Summarise an angle to its
findings before starting the next, and never carry raw result lists forward.** If the question needs
more passes than your context will hold, say so and size it down honestly — don't silently truncate,
and don't claim to have fanned out when you didn't.

<!-- slot: research-report-open -->
**Format.** Open with: "I used TinyFish to review {X} sources across {Y} passes." X is the size of
the single running `sources_reviewed` set — not a sum of per-pass numbers, which would double-count
URLs that appeared in more than one pass. If you delegated, union each child's `sources:` list into
that same set, never add their counts, and say "subagents" instead of "passes".

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | One or two `search` calls, or a direct `fetch_content`. Answer. |
| Moderate | A focused question with one clear angle | One pass: 3–5 searches, fetch the best hits, compile. |
| Deep | A clear topic with a few independent angles | 3–4 passes, one per angle, compiling after each. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Repeated rounds of the above, compiling between rounds and re-scoping from what you found. |

With a subagent tool, each pass above becomes a delegated child instead — same budgets, same order.

<!-- slot: security-doc -->
this power's `rules/security.md`

<!-- slot: setup -->
## Setup and auth

All of this runs through the `tinyfish` MCP server (`https://agent.tinyfish.ai/mcp`). Declared by this
power, it is managed by Kiro, authenticates by OAuth on first use, and carries no API key. Registered
instead by hand in `~/.kiro/settings/mcp.json` with an `X-API-Key: ${TINYFISH_API_KEY}` header, it
sends that key and has no OAuth fallback. **Call the MCP tools, not the `tinyfish` CLI**: the CLI keeps
its own key, and after an OAuth sign-in it has none.

On an auth error, or when the server lists no tools, check which setup this is. Power: Kiro does not
open the sign-in on its own; tell the user to sign in to the power's `tinyfish` MCP server — in the
Kiro IDE, open the Kiro panel (ghost icon), right-click the TinyFish server under **MCP Servers**,
and choose **Reauthenticate** (if the server isn't listed, trust the workspace first — Kiro may not
start a power's servers in Restricted Mode); in Kiro CLI, press Ctrl+Y at the "requires OAuth"
prompt or run `/mcp` for the link — and finish the browser sign-in.
Do not fall back to built-in web search without saying so. Kiro saves it for later sessions. Keyed:
signing in fixes nothing — `TINYFISH_API_KEY` is unset in the environment Kiro was started from,
missing from Kiro's **Mcp Approved Env Vars** setting, or revoked; tell the user to fix that and
restart Kiro. Never ask for an API key in chat. On a wallet-balance or rate-limit error, say so plainly.
