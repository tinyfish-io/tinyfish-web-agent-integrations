Slot values for the Grok plugin (grok/skills), which reaches TinyFish through the hosted MCP server.

<!-- slot: browser-caveat -->


<!-- slot: host-conversation -->
plugin

<!-- slot: profiles-cli -->


<!-- slot: research-auth -->
The server is `https://agent.tinyfish.ai/mcp`, configured by this plugin, authenticated by OAuth on
first connection. On an auth error, tell the user to re-authenticate the `tinyfish` MCP server (in
Grok Build: `/mcps`, select `tinyfish`, press `i`). On a wallet-balance or rate-limit error, say so plainly.

<!-- slot: research-broad-search -->
Most of the subagent work.

<!-- slot: research-dispatch -->
## Step 2: Dispatch subagents

Subagents exist to keep raw search and page content out of your context. Each one reads the reference
files you point it at, runs its assigned work, and returns only distilled output.

Reference paths below are relative to the directory this file was loaded from — always give
subagents the **absolute** path.

**Always point a subagent at `references/searching.md`.** Add others as they apply:

| File | Point a subagent here when it needs to... |
|---|---|
| `references/searching.md` | Write good `search` calls — always |
| `references/fetching.md` | Read pages: batching, formats, CSS scoping, failure handling |
| `references/synthesis.md` | Produce prose rather than structured rows |

You read `references/fan-out.md` yourself before splitting work — it covers how to decompose a
question into angles that don't overlap.

**Prompt template:**

```
Read the file at <absolute path>/references/searching.md for how to query TinyFish search.
[Also read <absolute path>/references/fetching.md — you will be reading pages.]

Your sub-question: [the specific angle, stated as a question]

[specific queries to run, if you are prescribing them]
[what qualifies as a valid result, so you filter before returning]

Return: [exact output format — e.g. "compact JSON with name, url, one-line evidence, per result"]

End with EXACTLY: `sources_reviewed: N` where N = the number of **unique** source URLs you reviewed —
every distinct URL you saw in `search` results (across all calls and retries) or fetched. Count a URL
once even if you both saw it in search and then fetched it.
```

Pass the `sources_reviewed` line to every subagent verbatim. Don't paraphrase it.

**Sizing:** aim for 3–5 searches per subagent. Launch all subagents for a pass in a single message so
they run concurrently. For per-seed enrichment, batch 3–5 seeds per subagent.

**Never run bulk searching in your own context.** That defeats the purpose.

<!-- slot: research-intro -->
You are the orchestrator. Understand the question, decide how much work it deserves, dispatch
subagents when the volume warrants it, then compile and deliver.

<!-- slot: research-on-host -->


<!-- slot: research-report-open -->
**Format.** If you used subagents, open with: "I used TinyFish to review {X} sources across {Y}
subagents." X is the sum of `sources_reviewed` across every subagent and pass, plus anything you
searched directly.

<!-- slot: research-sizing -->
| Trivial | One fact, one entity, or "read this page for me" | Handle it yourself. One or two `search` calls, or a direct `fetch_content`. Answer. No subagents. |
| Moderate | A focused question with one clear angle | One subagent, to keep raw results out of your context. |
| Deep | A clear topic with a few independent angles | One round of 3–4 parallel subagents, then compile. |
| Exhaustive | Cross-referencing entity types, multi-hop chains, "find everything", explicit counts | Multiple passes of parallel subagents, compiling between passes. |

<!-- slot: security-doc -->
this plugin's `rules/security.md`

<!-- slot: setup -->
## Setup and auth

All of this runs through the `tinyfish` MCP server (`https://agent.tinyfish.ai/mcp`). Configured by this
plugin, it authenticates by OAuth on first use and carries no API key. Registered instead by `tinyfish
connect grok --api-key`, it sends a `${TINYFISH_API_KEY}` Bearer header and has no OAuth fallback.

On an auth error, check which setup this is. Plugin: tell the user to re-authenticate — in Grok Build,
`/mcps`, select `tinyfish`, press `i`. Keyed: signing in there fixes nothing — the key is unset in the
shell Grok was started from, or revoked; tell the user to re-run `npx -y @tiny-fish/cli@latest connect
grok --api-key <key>` and start Grok from a new terminal. On a wallet-balance or rate-limit error, say so
plainly.

<!-- slot: this-install -->
plugin

