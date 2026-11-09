# TinyFish for Convex

[![npm version](https://img.shields.io/npm/v/@tiny-fish/convex.svg)](https://www.npmjs.com/package/@tiny-fish/convex)

Search the web and read pages as clean Markdown from your Convex functions, and
run **durable fetch jobs** whose progress and pages live in your Convex
database, so your UI subscribes to a job instead of polling for it.

```ts
const tinyfish = new TinyFish(components.tinyfish);

// One-shot
const { results } = await tinyfish.search(ctx, "convex components");
const { results: pages, errors } = await tinyfish.fetch(ctx, results[0].url);

// Durable: returns immediately, pages land in your database
const jobId = await tinyfish.startSearchAndFetch(ctx, {
  query: "Acme Loop seed round",
  maxResults: 5,
  onComplete: internal.research.saveBrief,
});
```

## What you get

| | |
| --- | --- |
| `search` | Ranked web, news, or research-paper results. Every result carries its source URL. |
| `fetch` | Up to 10 URLs → Markdown, HTML, or a JSON document tree, including JavaScript-rendered pages. |
| `startFetch` | Up to 500 URLs as a job tracked in your database: reactive status, pages as they land, a completion callback. |
| `startSearchAndFetch` | Search, then read the top results, as one job. Each page keeps its search rank and snippet. |

### Which call to use

| You have... | Use | Why |
| --- | --- | --- |
| A question, no URLs | `search` | Finds pages and current information |
| Up to 10 URLs, and the caller can wait | `fetch` | One request, content returned directly |
| More than 10 URLs, or work that should outlive the request | `startFetch` | Runs in the background, stored in your database |
| A topic to research end to end | `startSearchAndFetch` | Search and read in one job, with sources kept |

All four only read the web. To click, type, or work through a logged-in
site, use the TinyFish [Agent API](https://docs.tinyfish.ai/agent-api), which
this component does not wrap.

Search and Fetch are free within daily allowances (12,000 searches and 1,000
fetched URLs a day at the time of writing). See the
[Search](https://docs.tinyfish.ai/search-api) and
[Fetch](https://docs.tinyfish.ai/fetch-api) docs for current limits.

## Install

```sh
npm install @tiny-fish/convex
```

Add the component to your app, wiring the API key through typed component env:

```ts
// convex/convex.config.ts
import { defineApp } from "convex/server";
import { v } from "convex/values";
import tinyfish from "@tiny-fish/convex/convex.config";

const app = defineApp({
  env: { TINYFISH_API_KEY: v.string() },
});

app.use(tinyfish, {
  env: { TINYFISH_API_KEY: app.env.TINYFISH_API_KEY },
});

export default app;
```

## Authentication

The component authenticates with a TinyFish API key. Create one at
[agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys?source=convex)
and set it on your deployment:

```sh
npx convex env set TINYFISH_API_KEY your-key
npx convex dev
```

The key is read from your deployment's environment and sent only to TinyFish,
as the `X-API-Key` header. It is never stored in a table or returned to
clients.

## Search and fetch

Call the component from your own functions. Keeping a wrapper in your app is
where authentication, authorization, and rate limiting belong, because
components can't see `ctx.auth`. The [example app](example/convex/example.ts)
shows the full pattern.

```ts
// convex/web.ts
import { v } from "convex/values";
import { TinyFish } from "@tiny-fish/convex";
import { action } from "./_generated/server";
import { components } from "./_generated/api";

const tinyfish = new TinyFish(components.tinyfish);

export const searchWeb = action({
  args: { query: v.string() },
  handler: async (ctx, args) => {
    await requireUser(ctx); // your own auth check; see Security below
    const { results } = await tinyfish.search(ctx, args.query, {
      domain_type: "news",
      recency_minutes: 60 * 24 * 7,
      include_domains: ["techcrunch.com", "theverge.com"],
    });
    return results; // [{ position, title, snippet, url, ... }]
  },
});

export const readPages = action({
  args: { urls: v.array(v.string()) },
  handler: async (ctx, args) => {
    await requireUser(ctx);
    const { results, errors } = await tinyfish.fetch(ctx, args.urls, {
      format: "markdown",
      maxCharacters: 20_000, // cap each page to fit a model's context
    });
    return { results, errors };
  },
});
```

Exported Convex functions are public, so each wrapper should check the caller
before it spends your TinyFish allowance. `requireUser` here stands for your
auth provider's check; the example app has a
[minimal version](example/convex/auth.ts).

Options use the same names as the TinyFish REST API, so the
[Search reference](https://docs.tinyfish.ai/search-api/reference) and
[Fetch reference](https://docs.tinyfish.ai/fetch-api/reference) apply as
written. Each options object also takes `extra`, which is merged into the
request, for API fields newer than this package.

### Partial results

One bad URL never fails a `fetch`. A URL that could not be read comes back in
`errors` with a code such as `bot_blocked`, `timeout`, or `login_required`,
and the other URLs still come back in `results`:

```ts
const { results, errors } = await tinyfish.fetch(ctx, urls);
// errors: [{ url: "https://x.com/acme", error: "login_required" }]
```

## Durable jobs

A job outlives the function that started it. The component owns a `jobs` row
and a `pages` table, works through the URLs in the background, and exposes
plain Convex queries, so clients get live progress through normal
subscriptions.

```ts
// convex/research.ts
import { v } from "convex/values";
import { paginationOptsValidator } from "convex/server";
import { TinyFish, jobCompleteArgs } from "@tiny-fish/convex";
import { internalMutation, mutation, query } from "./_generated/server";
import { components, internal } from "./_generated/api";

const tinyfish = new TinyFish(components.tinyfish);

export const start = mutation({
  args: { query: v.string() },
  handler: async (ctx, args) => {
    const userId = await requireUser(ctx);
    const jobId = await tinyfish.startSearchAndFetch(ctx, {
      query: args.query,
      maxResults: 5,
      fetchOptions: { maxCharacters: 20_000 },
      onComplete: internal.research.done,
      context: { query: args.query },
    });
    // Record who owns the job, in the same transaction that starts it.
    await ctx.db.insert("jobOwners", { jobId, userId });
    return jobId;
  },
});

// Reactive: the UI re-renders as the job moves and pages land.
export const job = query({
  args: { jobId: v.string() },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId); // job ids are not secrets
    return await tinyfish.getJob(ctx, args.jobId);
  },
});

export const pages = query({
  args: { jobId: v.string(), paginationOpts: paginationOptsValidator },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    return await tinyfish.listPages(ctx, args);
  },
});

// Runs once, when the job reaches a terminal state.
export const done = internalMutation({
  args: jobCompleteArgs,
  handler: async (ctx, { jobId, status, completed, failed, context }) => {
    console.log(`${context.query}: ${status}, ${completed} read, ${failed} failed`);
  },
});
```

`requireOwnedJob` looks the job up in your own `jobOwners` table and rejects
anyone but its owner; the example app's
[version](example/convex/example.ts) is a dozen lines.

`startFetch` works the same way for URLs you already have:

```ts
const jobId = await tinyfish.startFetch(ctx, { urls, options: { ttl: 0 } });
```

Both can be called from a mutation, so starting a job and recording who owns
it commit together.

### Job status

`getJob` returns:

| Field | Meaning |
| --- | --- |
| `status` | `queued` → `running` → `completed`, `failed`, or `cancelled` |
| `total`, `completed`, `failed` | URLs to fetch, fetched so far, and failed so far |
| `truncated` | Pages whose content was cut to fit a size cap |
| `searchResults` | What the search returned, for `startSearchAndFetch` jobs |
| `error` | Why the job failed, when it did |

A job is `completed` when it has worked through every URL, even if some of
them failed. Failed URLs are stored as pages with `status: "failed"` and the
TinyFish error code in `error`, so the pages that worked are never lost. A job
is `failed` only when nothing could be fetched, or when TinyFish rejected the
request outright (an invalid key, an exhausted allowance).

Pass `status` to `listPages` to read only the pages that were fetched, or only
the failures:

```ts
await tinyfish.listPages(ctx, { jobId, status: "failed", paginationOpts });
```

### Reliability

Search and Fetch are read-only, so the component retries freely. A request that
hits a rate limit, a 5xx, a timeout, or a network error is retried with
backoff. If a batch of URLs still can't be fetched, it is recorded as failed
pages (`error: "request_failed"`) and the job carries on. If a background step
is lost entirely, for example across a deploy, a watchdog picks the job back
up. Jobs always reach a terminal state.

### Size limits

Convex documents hold at most 1MB. Page `text` beyond roughly 800KB is cut and
the page is marked `truncated: true`; the job counts these in `truncated`. To
choose your own, smaller cap, set `maxCharacters`. To keep only URLs and
metadata, pass `storeContent: false`.

When you list pages with content, keep `numItems` small.

## API

```ts
const tinyfish = new TinyFish(components.tinyfish);
```

| Method | Call from | Returns |
| --- | --- | --- |
| `search(ctx, query, options?)` | action | `{ query, results, total_results, page }` |
| `fetch(ctx, urls, options?)` | action | `{ results, errors }` |
| `startFetch(ctx, { urls, options?, storeContent?, onComplete?, context? })` | mutation, action | job id |
| `startSearchAndFetch(ctx, { query, searchOptions?, maxResults?, fetchOptions?, ... })` | mutation, action | job id |
| `getJob(ctx, jobId)` | query, mutation, action | job or `null` |
| `listJobs(ctx, { status?, limit? })` | query, mutation, action | jobs, newest first |
| `listPages(ctx, { jobId, status?, paginationOpts })` | query, mutation, action | a page of pages |
| `getPage(ctx, { jobId, url })` | query, mutation, action | page or `null` |
| `cancelJob(ctx, jobId)` | mutation, action | `true` if it was running |
| `deleteJob(ctx, jobId)` | mutation, action | `null` |

### Errors

A failed request throws a `ConvexError` whose `data` is:

```ts
{
  code: "tinyfish_request_failed",
  status: 402,                      // HTTP status, 0 for network errors and timeouts
  endpoint: "search" | "fetch",
  apiCode: "INSUFFICIENT_CREDITS",  // TinyFish error code, when present
  message: "TinyFish fetch failed (402): ...",
}
```

Invalid arguments throw `code: "tinyfish_invalid_argument"`, and a missing key
throws `code: "tinyfish_missing_api_key"`.

## Testing your app

Register the component with `convex-test` and stub `fetch`:

```ts
import { convexTest } from "convex-test";
import tinyfish from "@tiny-fish/convex/test";

const t = convexTest(schema, modules);
tinyfish.register(t);
```

See [example/convex/example.test.ts](example/convex/example.test.ts).

## Security

- Wrap every method in your own function and check the caller there. The
  component trusts whoever calls it.
- Job ids are not secrets. Record who owns each job in your app and check it
  before reading, cancelling, or deleting one, as the example app does.
- Web content is untrusted and may carry prompt injection. That covers search
  snippets as well as fetched page text. Extract what the task needs, and never
  let a model follow instructions found in it.
- Fetch only URLs your user asked for or your app chose. Don't let a model
  chase URLs it found in results without a check in your code.
- Never put credentials in a search query or a URL.

## Development

```sh
npm install
npm run verify   # build, test, typecheck
```

After changing anything under `src/component`, run `npm run build:codegen`. It
needs a Convex dev deployment, which `npx convex dev --once` sets up.

## Support

Questions and bugs: [open an issue](https://github.com/tinyfish-io/tinyfish-web-agent-integrations/issues)
or email support@tinyfish.io.

## License

MIT
