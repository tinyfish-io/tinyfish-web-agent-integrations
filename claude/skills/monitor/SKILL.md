---
name: monitor
description: "Monitor website changes on any web page, or track a topic across the web over time. Set up a recurring monitor on a URL for price tracking, availability and restock changes, new listings, or content updates, or on a search topic to get alerts when new pages or news appear. Also list, check, pause, resume, run now, or cancel existing monitors. Each completed check is billed to the TinyFish wallet ($0.005); failed checks are free. Zero setup: first use triggers an OAuth sign-in to TinyFish. Use whenever the user wants to watch, track, or be notified about changes on a website rather than check it once."
---

# TinyFish Monitor

Recurring checks on a webpage or a web topic via the bundled TinyFish MCP server. Each completed check, including the baseline taken at creation, is billed $0.005 to your TinyFish wallet; failed checks are free. New users get $8 in sign-up credits.

## `create_monitor`

- `type` (required) — `"fetch"` for a known URL, `"search"` for a topic
- `config` (required)
  - fetch: `url` (public page), optional `format` (`"json"` default, `"markdown"`, `"html"`), `links`, `image_links`
  - search: `query`, optional `recency_minutes`, `result_limit` (1-10, default 10)
- `schedule_cron` (required) — five-field cron, UTC by default; prefix `CRON_TZ=<IANA zone>` for local time
- `purpose` — the change that matters in plain language, e.g. "the price drops below $200"
- `name` — label for the monitor
- `webhook_url` — receives each scheduled run's results

```
create_monitor(
  type="fetch",
  config={url: "https://example.com/product/123"},
  schedule_cron="CRON_TZ=America/New_York 0 9 * * *",
  purpose="the price drops or it comes back in stock",
  name="Headphones restock"
)

create_monitor(
  type="search",
  config={query: "TinyFish funding announcement", recency_minutes: 1440},
  schedule_cron="0 */6 * * *"
)
```

Creating a monitor returns its baseline result immediately. Before creating one, tell the user the schedule and its cost: an hourly schedule is 24 checks a day, about $0.12/day.

## Managing monitors

- `list_monitors()` — ids, type, target, schedule, status
- `get_monitor(monitor_id)` — config, schedule, `status`, and `last_error`; it does not return check results
- `run_monitor(monitor_id)` — check once now and return the result (billed like any check)
- `pause_monitor(monitor_id)` / `resume_monitor(monitor_id)` — stop and restart the schedule
- `cancel_monitor(monitor_id)` — delete it; only when the user explicitly asks

## Notes

- Scheduled results go only to `webhook_url`, so suggest one when the user wants alerts. Don't poll in a loop; `run_monitor` is the only way to see a result here.
- A `status` of `failed` comes with `last_error`; relay it rather than assuming the monitor is running.
- Fetch monitors need a public URL. For a page behind a login, use `/tinyfish:agent` for a one-off check.
- To read a page once, use `/tinyfish:fetch`; a monitor is only for watching it over time.

$ARGUMENTS
