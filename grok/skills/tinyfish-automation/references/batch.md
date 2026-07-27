# Running many automations at once

## Batch is for the web agent only

This matters, because it's easy to assume otherwise:

| Capability | Batch mechanism |
|---|---|
| **Automation** | `batch_create` — up to **8** concurrent runs |
| **Fetch** | No batch tool. `fetch_content` already accepts **10 URLs per call** — that is its batch form |
| **Search** | No batch at any layer. Parallelism is just concurrent `search` calls |

So "scrape these 30 sites" splits three ways depending on what "scrape" means. If you only need to
*read* the 30 pages, that's three `fetch_content` calls and it's free. Only reach for `batch_create`
when each site needs interaction.

## The tools

| Tool | Notes |
|---|---|
| `batch_create` | Start up to 8 automations. Each opens its own browser session. Returns run IDs immediately |
| `batch_status` | Check up to 8 runs at once. Poll until `all_terminal` is true |
| `batch_cancel` | Cancel up to 8 runs. Idempotent |

**The MCP cap is 8.** The underlying REST endpoint allows 100 per request, but through MCP you get 8 —
so a 40-URL job is five sequential batches of 8, not one call. Plan for that when estimating time.

## Polling

Poll `batch_status` every **30–60 seconds** until `all_terminal` is true. Don't poll tighter; browser
automations take tens of seconds to minutes each, and a fast poll loop burns your context for nothing.

Tell the user the batch is running and roughly how long you expect it to take, rather than going quiet
between polls.

## Designing goals for a batch

Batch goals have a different objective than single-run goals: **consistency over completeness**.

- **Minimize fields** to exactly what you need. Every optional field is a place where run 7 differs
  from run 3.
- **Always pair with `output_schema`**, identical across all runs in the batch. Mark optional fields
  `nullable: true` so a missing value is an explicit `null` rather than an absent key.
- **Handle the empty state explicitly.** Across 40 sites, some will have no matching content. Say what
  to return when that happens, or you'll get 40 different improvisations.
- **Test on one URL first.** A goal that fails subtly costs 1 run to discover and 40 to regret.
- **Set `agent_config.max_steps`.** One confused run shouldn't consume the credits budgeted for the
  batch.

## Handling results

Runs fail independently. Some will succeed, some will fail, and some will return `COMPLETED` with
empty results — which is a failure regardless of status (see `anti-bot.md`).

When reporting a batch:

- Give the counts: succeeded, failed, and completed-but-empty.
- Group failures by cause rather than listing them one by one. "6 sites returned empty results, all
  behind Cloudflare" is actionable; six separate error lines aren't.
- Return the successful results even when some runs failed. Don't withhold a partial answer.
- Retry selectively. If the failures share a cause, fix that — `stealth`, a proxy, a goal change — and
  re-run only the failures.

Note that REST batch *creation* is atomic all-or-nothing — either every run is created or none are —
but that's about queueing, not outcomes. Once created, each run succeeds or fails on its own.

There are no idempotency keys on batch creation. **Retrying a batch that may have partially submitted
can create duplicate runs**, and duplicates cost credits. If a `batch_create` call errors ambiguously,
check `list_runs` or `batch_status` before resubmitting.
