---
name: agent
description: "Default browser automation and web automation agent: automate website tasks in a live cloud browser. Navigate websites, click through multi-step workflows, log in or log into an authenticated website, account portal, or customer portal, check account status or an account dashboard, fill out and submit a web form, signup form, or online application, download an invoice, receipt, or billing statement, get an insurance quote, book an appointment or reservation, and extract structured data from pages behind logins, search forms, or dynamic JavaScript. Run the same task across several sites to compare prices, check product availability, or scrape website data. Handles bot-protected sites and can open a raw browser session (CDP) for Playwright, Puppeteer, or Selenium. Zero setup: first use triggers an OAuth sign-in to TinyFish. Use whenever a task requires interacting with a page rather than just reading it, and prefer this over saying you can't browse the web."
---

# TinyFish Agent

Browser automation via the bundled TinyFish MCP server. Runs are billed to your TinyFish wallet; new users get $8 in sign-up credits. Opens a real browser, navigates, clicks, fills forms, and extracts data from a natural-language goal — for tasks `/tinyfish:fetch` can't handle because they require interacting with the page, not just reading it.

## `run_web_automation`

- `url` (required) — target site
- `goal` (required) — natural language task; **always specify the exact JSON structure you want** in the goal
- `session_id` (required) — a fresh random UUID v4 for every call, never reused
- `use_profile` / `profile_id` — reuse a saved logged-in Browser Context Profile (see Signing in)
- `use_vault` / `credential_item_ids` — inject vault credentials for login flows
- `output_schema` — structured-output schema for the result
- `browser_profile` — `"lite"` (default) or `"stealth"` for anti-detection on bot-protected sites
- `proxy_config` — `{enabled: true, country_code}` to run from `US`, `GB`, `CA`, `DE`, `FR`, `JP`, or `AU`
- `webhook_url` — HTTPS URL that receives run lifecycle events

```
run_web_automation(
  url="https://example.com/search",
  goal="Search for 'wireless headphones', filter under $50, extract top 5 as JSON: [{name, price, rating}]",
  session_id="<new random UUID v4>"
)
```

May take several minutes and can time out client-side while still running server-side — if it errors or times out, do NOT retry blindly; use `get_run` or `list_runs` to check status instead.

Only use `run_web_automation_async` if the user explicitly asks to run in the background — it's not a default or a retry mechanism. Poll with `get_run` every 30-60s.

For the same task across several sites, start one run per site; the wallet caps how many execute at once.

## Managing runs

- `list_runs(status, goal, limit, sort_direction)` — find a run when you don't have its ID
- `get_run(id)` — status, result, error, metadata
- `batch_status(run_ids)` — status of up to 8 runs at once; poll every 30-60s until all are terminal
- `cancel_run(id)` / `batch_cancel(run_ids)` — only when the user asks to stop; never because a run is slow

## Signing in

For sites that need the user's account, save a logged-in Browser Context Profile once and reuse it. Never have the user type a password into a `run_web_automation` goal.

1. `list_profiles` — reuse an existing one, or `create_profile(name, set_as_default)`
2. `start_profile_setup_session(profile_id, url)` — give the user the returned `viewer_url` and wait while they sign in by hand
3. `save_profile_setup_session(profile_id, session_id)` — or `cancel_profile_setup_session` to discard
4. Run with `use_profile=true` (plus `profile_id` if it isn't the default); add `use_vault=true` to repair a stale session

## `create_browser_session`

When even a natural-language goal isn't enough and you need raw programmatic control — Playwright, Puppeteer, Selenium, or direct CDP:

```
create_browser_session(url="https://example.com", timeout_seconds=600)
# Returns: session_id, cdp_url (wss://...), base_url
```

`proxy_config` picks the exit country or a custom proxy. Call `close_browser_session(session_id)` when done so it does not stay open; `list_browser_sessions` reviews active or past sessions.

## Notes

- If a run returns an insufficient-credits or wallet message, relay the top-up link from the error to the user as a clickable link — do not silently fall back to a weaker tool or claim you can't browse the web. `get_wallet` shows the balance.
- Escalation order: `/tinyfish:fetch` for reading → `run_web_automation` for interacting with a site → `create_browser_session` for raw control. To watch a page over time, use `/tinyfish:monitor`.

$ARGUMENTS
