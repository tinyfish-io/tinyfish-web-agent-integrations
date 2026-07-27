# Diagnosing failed runs and bot detection

A run came back `COMPLETED` but the result is empty or wrong — or it outright `FAILED`. **Don't start
rewriting the goal.** Bot detection is the most common cause of silent failure, and it needs the
opposite fix from a bad goal. Diagnose first.

## Step 1: Confirm the cause

Every run produces a `streaming_url` — a live browser preview. Open it while the run is happening, or
retrieve it from `get_run` afterwards. It's the fastest way to see what the browser actually hit.

| What you see | Cause |
|---|---|
| Cloudflare challenge / "Checking your browser" | Cloudflare bot detection |
| DataDome popup or redirect | DataDome protection |
| Blank page or infinite spinner | IP block or JS fingerprinting |
| CAPTCHA (reCAPTCHA, hCaptcha) | CAPTCHA gate — **cannot be solved automatically** |
| "Access Denied" or 403 | IP or User-Agent block |
| Login page when you expected content | Session-based detection, or the content genuinely needs auth |
| The right page, but the agent stopped early or clicked the wrong thing | **Goal problem, not anti-bot** — see `goals.md` |

If you can't watch the run, enable `capture_config.screenshots` and `capture_config.snapshots` and
re-run; step screenshots and HTML snapshots tell you the same story after the fact.

**Anti-bot signatures in the result:** every field `null` or every array empty *while* the streaming
view shows the target content never loaded; or `result.reason` mentioning "access denied", "blocked", or
"could not find".

The distinction that matters: **a bot wall means the agent never saw the content. A bad goal means it
saw the content and did the wrong thing with it.** Screenshots settle which.

## Step 2: Stealth and proxy together

Apply both. Stealth changes the browser fingerprint; the proxy changes the IP. Anti-bot services
correlate both signals, so changing only one often isn't enough.

```json
{
  "url": "https://protected.example/search",
  "goal": "...",
  "browser_profile": "stealth",
  "proxy_config": { "enabled": true, "type": "tetra", "country_code": "US" }
}
```

`browser_profile` is `lite` (default, standard browser) or `stealth` (anti-detection). Supported
`country_code` values: `US`, `GB`, `CA`, `DE`, `FR`, `JP`, `AU`.

Don't reach for `stealth` by default — start with `lite` and escalate when you've confirmed a block.

Set `country_code` to match the content you want when a site is geo-sensitive, not just to evade
blocking: a US proxy gets US pricing and US inventory.

## Step 3: Make the goal behave more like a human

Once you're past the fingerprint check, the run can still trip behavioral detection. Adjust the goal:

- Tell it to dismiss cookie banners and consent dialogs before doing anything else — those overlays
  also block clicks.
- Avoid instructing rapid-fire iteration over many items on protected sites. Sequential, purposeful
  steps read as human; scraping 200 rows as fast as possible does not.
- Land on a real entry point. Deep-linking straight to a results URL with no referrer is itself a
  signal on some sites.

## What can't be fixed

**CAPTCHAs cannot be solved automatically.** If the run hits reCAPTCHA or hCaptcha, stealth and proxies
won't help. The options are a Browser Context Profile whose saved session is already past the gate (see
the `tinyfish-authenticated` skill), or telling the user the site can't be automated. Say so plainly
rather than burning credits on retries.

Also don't keep retrying:

- The same configuration after two failures. Change something or stop.
- A site that blocked `stealth` + proxy. Escalation is exhausted; report it.

## Escalation order

1. Confirm via `streaming_url` or screenshots that content never loaded.
2. `browser_profile: "stealth"` + `proxy_config`.
3. Goal adjustments for banners and pacing.
4. If a login gets past it: Browser Context Profile, per `tinyfish-authenticated`.
5. Report the site as not automatable, with what you observed.

Tell the user which step you're on and what you saw. "This site is behind DataDome and returned a
challenge page under stealth with a US proxy" is a useful answer; "the automation failed" isn't.
