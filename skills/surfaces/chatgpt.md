Slot values for the ChatGPT plugin (chatgpt/skills), vendored into ux-labs `chatgpt-plugin/skills/`. It reaches TinyFish through `https://agent.tinyfish.ai/mcp/chatgpt`, has no subagents, and ships only tinyfish-monitor and tinyfish-research; the other skills render only so the build stays total.

<!-- slot: automation-batch -->
The MCP tools do not start
batches themselves; kick off runs with `run_web_automation_async` and collect their `run_id`s.

<!-- slot: browser-caveat -->


<!-- slot: host-conversation -->
ChatGPT

<!-- slot: profiles-cli -->


<!-- slot: research-auth -->
The TinyFish tools come from this plugin's connector, signed in with OAuth. On an auth error, tell the
user to reconnect TinyFish from ChatGPT's apps settings. Never ask for an API key in chat. On a
wallet-balance or rate-limit error, say so plainly.

<!-- slot: research-broad-search -->
The bulk of the work.

<!-- slot: research-dispatch -->
## Step 2: Work the passes

Each pass takes one angle and ends with distilled findings, not raw output. Read
`references/fan-out.md` before splitting a question — it covers decomposing into angles that don't
overlap. Where it talks about subagents, read that as your own passes.

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

This host has no subagents: run every pass yourself, in order.

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, work it in
passes, then compile and deliver.

<!-- slot: research-on-host -->
## Context is the budget

Every `search` and `fetch_content` result lands straight in your context. **Summarise an angle to its
findings before starting the next, and never carry raw result lists forward.** If the question needs
more passes than your context will hold, say so and size it down honestly — don't silently truncate,
and don't claim to have fanned out when you didn't.

<!-- slot: research-report-open -->
**Format.** Open with: "I used TinyFish to review {X} sources across {Y} passes." X is the size of
the single running `sources_reviewed` set — not a sum of per-pass numbers, which would double-count
URLs that appeared in more than one pass.

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | One or two `search` calls, or a direct `fetch_content`. Answer. |
| Moderate | A focused question with one clear angle | One pass: 3–5 searches, fetch the best hits, compile. |
| Deep | A clear topic with a few independent angles | 3–4 passes, one per angle, compiling after each. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Repeated rounds of the above, compiling between rounds and re-scoping from what you found. |

<!-- slot: security-doc -->
<https://raw.githubusercontent.com/tinyfish-io/tinyfish-web-agent-integrations/main/pi/rules/security.md>

<!-- slot: setup -->
## Setup and auth

All of this runs through this plugin's TinyFish connector, signed in with OAuth.

On an auth error, tell the user to reconnect TinyFish from ChatGPT's apps settings. Never ask for an
API key in chat. On a wallet-balance or rate-limit error, say so plainly.
