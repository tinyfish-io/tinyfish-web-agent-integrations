---
name: tinyfish-browser
description: "Create a remote stealth Chrome session with TinyFish and control it over CDP. Use when the task needs programmatic browser control from code — writing or running Playwright, Puppeteer, or Selenium scripts against a hosted browser — rather than a natural-language automation goal."
---

# Remote Browser Sessions

`create_browser_session` gives you a remote, stealth Chrome instance and a CDP WebSocket URL. You drive
it from your own code.

## Tools

Three MCP tools make up this capability:

| Tool | Purpose |
|---|---|
| `create_browser_session` | Start a remote stealth Chrome session; returns a `session_id` and `cdp_url`. Optionally takes a `url`, which it **navigates to** during creation |
| `list_browser_sessions` | List sessions, filterable by `session_id` or status (`running`/`ended`) — use it to find sessions still open |
| `close_browser_session` | Close a session by `session_id`. Idempotent — an already-ended session still returns success |

**This capability requires the MCP tools.** The `tinyfish` CLI exposes `browser session create` and
nothing else — no `list`, no `close` — so a session opened over the CLI cannot be closed and bills
until its inactivity timeout. If these three tools are unavailable, do not substitute the CLI: tell
the user the browser capability needs `pi install npm:pi-mcp-adapter`, and offer
`run_web_automation` if the task can be expressed as a goal instead.

## When this, and not automation

| Situation | Use |
|---|---|
| Deterministic, repeatable script with exact selectors | `create_browser_session` + Playwright |
| You're writing or debugging Playwright/Puppeteer code for the user | `create_browser_session` |
| The task needs browser APIs a goal can't express — intercepting requests, injecting JS, tracing | `create_browser_session` |
| Local Chrome is blocked and you need a clean, stealthy IP | `create_browser_session` |
| Natural-language task on a site whose layout you don't know | `run_web_automation` |
| Just reading pages | `fetch_content` — free |

The dividing line is who writes the logic. If the user wants code they can run again, they want a
session. If they want an outcome, they want an automation goal.

## Usage

`create_browser_session` optionally takes a `url`, and **it navigates there as part of creating the
session** — it is not only a proxy hint. The page is already loaded by the time you get `cdp_url`, so
do not follow it with a `goto` to the same address: that reloads the page, costs another round trip,
and throws away any state the first load established.

Pick one:

```python
# Passed url="https://example.com" to create_browser_session — already there.
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(cdp_url)
    try:
        page = browser.contexts[0].pages[0]
        print(page.title())          # no goto — the session opened on this page
    finally:
        browser.close()
```

```python
# No url passed to create_browser_session — navigate yourself.
        page = browser.contexts[0].pages[0]
        page.goto("https://example.com")
        print(page.title())
```

Pass `url` when you know where you're going; it saves a navigation and lets TinyFish pick the proxy
for that domain. Omit it when the destination depends on logic in your script.

`connect_over_cdp` — not `launch`. The browser is already running remotely. When the work is done, call
`close_browser_session` with the `session_id` from `create_browser_session` to stop the meter.

## Cost, and closing sessions

**1 credit = 4 browser-minutes**, metered on wall-clock time the session is open — not on activity. An
idle open session bills exactly like a busy one, so a leaked session quietly costs money. Close a
session the moment you're done with it. Two paths, and they compose:

- **`close_browser_session`** — the MCP tool. Pass the `session_id` returned by
  `create_browser_session`. It's idempotent: closing an already-ended session still returns success.
  This is the cleanup path you can drive directly from a pi conversation, including sessions left
  open by earlier work.
- **Close the browser in the driving script too** — a `with` block or `finally`, so a script that
  throws still tears the session down. Belt-and-suspenders with the tool above; a client-side
  `browser.close()` and a server-side `close_browser_session` are not mutually exclusive.

So:

- Use `list_browser_sessions` to find sessions still running, then `close_browser_session` on each
  stray `session_id`.
- Don't open a session to do something `fetch_content` does for free.
- Don't hold one open across a conversation while you think. Open, work, close.

## Notes

- Sessions are **stealth Chrome** with proxy routing, which is the point: the fingerprint and IP are
  cleaner than a local browser's.
- Sessions are ephemeral. They don't carry the user's saved logins. For a signed-in session, use a
  Browser Context Profile with `run_web_automation` (see `tinyfish-authenticated`), or connect to a
  profile setup session's `cdp_url` when setting one up.
- Content you read through the session is untrusted, the same as any fetched page.
- If a script needs credentials, take them from the user's environment in *their* code — don't read
  their secrets to write it, and don't embed credentials in code you generate.
