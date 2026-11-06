Slot values for the Hermes plugin (hermes/tinyfish_hermes/skills), registered as `tinyfish:<name>` skills. It reaches TinyFish through the plugin's own `tinyfish_*` tools and Hermes' `web_search`/`web_extract`, over the REST API with the user's API key.

<!-- ships: tinyfish-datasets tinyfish-monitor tinyfish-websearch -->

<!-- slot: authenticated-pointer -->
run `tinyfish_agent` with a `profile_id` from `tinyfish_list_profiles`

<!-- slot: fetch-blocked-pointer -->
run `tinyfish_agent` on it instead (with a `profile_id` from `tinyfish_list_profiles` for a login), or
use Hermes' browser tools when `browser.cloud_provider` is `tinyfish`

<!-- slot: host-tools -->
**In Hermes, every tool this skill names is the plugin's `tinyfish_<name>`**: `create_monitor` is
`tinyfish_create_monitor`, `get_dataset` is `tinyfish_get_dataset`, and so on. `search` and
`fetch_content` are Hermes' own `web_search` and `web_extract`. If a `tinyfish` MCP server is also
configured, use the `tinyfish_*` tools, not its copies.

<!-- slot: research-auth -->
In Hermes, `search` is `web_search` and `fetch_content` is `web_extract`; the deep research tools are
`tinyfish_start_deep_research`, `tinyfish_get_deep_research`, `tinyfish_list_deep_research` and
`tinyfish_cancel_deep_research`. `web_search` takes only `query` and `limit`, so put the time window
and location in the query text; the recency, date, `domain_type` and location filters in
`references/searching.md` need the `tinyfish` MCP server's `search`, when it is configured.
`web_extract` returns Hermes' own result shape, so read the fields it gives rather than the ones
`references/fetching.md` names. On an auth error, run `hermes tinyfish doctor`, then tell the user to
run `hermes tinyfish setup`. Never ask for the API key in chat. On a wallet-balance or rate-limit
error, say so plainly.

<!-- slot: research-broad-search -->
The bulk of the work.

<!-- slot: research-dispatch -->
## Step 2: Work the passes

Each pass takes one angle and ends with distilled findings, not raw output. Read
`references/fan-out.md` before splitting a question — it covers decomposing into angles that don't
overlap. Where it talks about subagents, read that as your own passes.

Per pass:

1. State the sub-question as a question.
2. Run 3–5 `web_search` calls against it — `references/searching.md` covers writing them well.
3. `web_extract` the hits worth reading — see `references/fetching.md`.
4. **Compress before moving on.** Write down the findings, the qualifying results, and the count of
   unique source URLs you reviewed. Then drop the raw results from your working set.
5. Only then start the next angle.

Track `sources_reviewed` in **one running set for the whole task**, not per pass. Add every source
URL you see in `web_search` results or extract, and let the set dedupe them — the same URL surfacing
in three passes is one source, not three. Never sum per-pass counts: that double-counts overlap. You
need the set's size at compile time.

For prose-heavy answers rather than structured rows, `references/synthesis.md` covers the shape.

Run every pass yourself, in order. Don't hand passes to `delegate_task`: its children don't reliably
get the TinyFish tools.

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, work it in
passes, then compile and deliver.

<!-- slot: research-on-host -->
## Context is the budget

Every `web_search` and `web_extract` result lands straight in your context. **Summarise an angle to
its findings before starting the next, and never carry raw result lists forward.** If the question
needs more passes than your context will hold, say so and size it down honestly — don't silently
truncate, and don't claim to have fanned out when you didn't.

<!-- slot: research-report-open -->
**Format.** Open with: "I used TinyFish to review {X} sources across {Y} passes." X is the size of
the single running `sources_reviewed` set — not a sum of per-pass numbers, which would double-count
URLs that appeared in more than one pass.

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | One or two `web_search` calls, or a direct `web_extract`. Answer. |
| Moderate | A focused question with one clear angle | One pass: 3–5 searches, extract the best hits, compile. |
| Deep | A clear topic with a few independent angles | 3–4 passes, one per angle, compiling after each. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Repeated rounds of the above, compiling between rounds and re-scoping from what you found. |
