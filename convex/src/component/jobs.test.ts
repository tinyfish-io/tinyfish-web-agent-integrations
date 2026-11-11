/// <reference types="vite/client" />
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { api, internal } from "./_generated/api.js";
import { fetched, initConvexTest, mockFetch } from "./setup.test.js";
import {
  matchResponse,
  searchResultForStorage,
  storable,
  toFailedPage,
  toPage,
  truncateToBytes,
} from "./jobs.js";

const firstPage = { numItems: 100, cursor: null };

function urlsOf(count: number): string[] {
  return Array.from({ length: count }, (_, i) => `https://a.com/${i}`);
}

function searchResult(position: number, url: string) {
  return {
    position,
    site_name: new URL(url).hostname,
    title: `Result ${position}`,
    snippet: `Snippet ${position}`,
    url,
  };
}

/**
 * Run scheduled work to completion. Time moves in small hops rather than all
 * at once, so a step gets to report back before its watchdog comes due, as it
 * would in production.
 */
async function finish(t: ReturnType<typeof initConvexTest>) {
  await t.finishAllScheduledFunctions(() => vi.advanceTimersByTime(10_000));
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("startFetch", () => {
  test("is queued until its first step runs", async () => {
    const t = initConvexTest();
    mockFetch([]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });

    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      kind: "fetch",
      status: "queued",
      total: 1,
      completed: 0,
      failed: 0,
      finalized: false,
    });
  });

  test("fetches every URL and stores the pages", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      {
        body: {
          results: [fetched("https://a.com"), fetched("https://b.com")],
          errors: [],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com", "https://b.com"],
      options: { format: "markdown", ttl: 0 },
    });
    await finish(t);

    expect(calls).toHaveLength(1);
    expect(calls[0].body).toEqual({
      urls: ["https://a.com", "https://b.com"],
      format: "markdown",
      ttl: 0,
    });
    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({
      status: "completed",
      finalized: true,
      total: 2,
      completed: 2,
      failed: 0,
    });
    expect(job?.completedAt).toBeTypeOf("number");

    const { page } = await t.query(api.jobs.listPages, {
      jobId,
      paginationOpts: firstPage,
    });
    expect(page.map((p: any) => p.url)).toEqual([
      "https://a.com",
      "https://b.com",
    ]);
    expect(page[0]).toMatchObject({
      status: "completed",
      final_url: "https://a.com",
      title: "Title of https://a.com",
      text: "# https://a.com",
      format: "markdown",
      truncated: false,
    });
    // `null` fields from TinyFish are left out rather than stored.
    expect(page[0]).not.toHaveProperty("author");
  });

  test("keeps the pages that worked when some URLs fail", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        body: {
          results: [fetched("https://a.com")],
          errors: [
            { url: "https://b.com", error: "bot_blocked" },
            { url: "https://c.com", error: "target_http_error", status: 500 },
          ],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com", "https://b.com", "https://c.com"],
    });
    await finish(t);

    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      total: 3,
      completed: 1,
      failed: 2,
    });
    const failed = await t.query(api.jobs.listPages, {
      jobId,
      status: "failed",
      paginationOpts: firstPage,
    });
    expect(
      failed.page.map((p: any) => [p.url, p.error, p.error_status]),
    ).toEqual([
      ["https://b.com", "bot_blocked", undefined],
      ["https://c.com", "target_http_error", 500],
    ]);
    expect(
      await t.query(api.jobs.getPage, { jobId, url: "https://a.com" }),
    ).toMatchObject({ status: "completed" });
  });

  test("fails the job when no URL could be fetched", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        body: {
          results: [],
          errors: [{ url: "https://a.com", error: "timeout" }],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });
    await finish(t);

    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({ status: "failed", completed: 0, failed: 1 });
    expect(job?.error).toMatch(/None of the 1 URLs/);
  });

  test("splits more than 10 URLs across requests", async () => {
    const t = initConvexTest();
    const urls = urlsOf(23);
    const calls = mockFetch(
      [urls.slice(0, 10), urls.slice(10, 20), urls.slice(20)].map((batch) => ({
        body: { results: batch.map((url) => fetched(url)), errors: [] },
      })),
    );

    const jobId = await t.mutation(api.jobs.startFetch, { urls });
    await finish(t);

    expect(calls.map((call) => call.body.urls.length)).toEqual([10, 10, 3]);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      total: 23,
      completed: 23,
    });
  });

  test("fetches a repeated URL once", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { body: { results: [fetched("https://a.com")], errors: [] } },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com", " https://a.com "],
    });
    await finish(t);

    expect(calls[0].body.urls).toEqual(["https://a.com"]);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({ total: 1 });
  });

  test("rejects URLs that TinyFish could never fetch", async () => {
    const t = initConvexTest();
    for (const urls of [[], ["not a url"], ["ftp://a.com/file"], urlsOf(501)]) {
      await expect(
        t.mutation(api.jobs.startFetch, { urls }),
      ).rejects.toThrow();
    }
  });

  test("records metadata only when storeContent is false", async () => {
    const t = initConvexTest();
    mockFetch([{ body: { results: [fetched("https://a.com")], errors: [] } }]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
      storeContent: false,
    });
    await finish(t);

    const page = await t.query(api.jobs.getPage, {
      jobId,
      url: "https://a.com",
    });
    expect(page).toMatchObject({ title: "Title of https://a.com" });
    expect(page).not.toHaveProperty("text");
  });

  test("caps stored text at maxCharacters and counts it", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        body: {
          results: [fetched("https://a.com", "x".repeat(500))],
          errors: [],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
      options: { maxCharacters: 100 },
    });
    await finish(t);

    const page = await t.query(api.jobs.getPage, {
      jobId,
      url: "https://a.com",
    });
    expect(page?.text).toHaveLength(100);
    expect(page?.truncated).toBe(true);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      truncated: 1,
    });
  });
});

describe("recovery", () => {
  test("retries a batch TinyFish rejected, then completes", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      // One step: the request and its in-request retry both fail.
      { status: 503, text: "unavailable" },
      { status: 503, text: "unavailable" },
      // The step is retried later and succeeds.
      { body: { results: [fetched("https://a.com")], errors: [] } },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });
    await finish(t);

    expect(calls).toHaveLength(3);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      completed: 1,
      failed: 0,
    });
  });

  test("records a batch as failed once retries run out, and carries on", async () => {
    const t = initConvexTest();
    const urls = urlsOf(11);
    const down = { status: 503, text: "unavailable" };
    const calls = mockFetch([
      // First batch: three steps of two requests each, all failing.
      ...Array.from({ length: 6 }, () => down),
      // Second batch works.
      { body: { results: [fetched(urls[10])], errors: [] } },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, { urls });
    await finish(t);

    expect(calls).toHaveLength(7);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      total: 11,
      completed: 1,
      failed: 10,
    });
    expect(
      await t.query(api.jobs.getPage, { jobId, url: urls[0] }),
    ).toMatchObject({
      status: "failed",
      error: "request_failed",
      error_status: 503,
    });
  });

  test("stops at once on an error that would repeat", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      {
        status: 401,
        body: { error: { code: "UNAUTHORIZED", message: "Invalid API key" } },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, { urls: urlsOf(25) });
    await finish(t);

    expect(calls).toHaveLength(1);
    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({ status: "failed", completed: 0, failed: 0 });
    expect(job?.error).toMatch(/401.*Invalid API key/);
  });

  test("stops at once when the API key is missing", async () => {
    const t = initConvexTest();
    delete process.env.TINYFISH_API_KEY;
    const calls = mockFetch([]);

    const jobId = await t.mutation(api.jobs.startFetch, { urls: urlsOf(25) });
    await finish(t);

    expect(calls).toHaveLength(0);
    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({ status: "failed", completed: 0, failed: 0 });
    expect(job?.error).toMatch(/TINYFISH_API_KEY is not set/);
  });

  test("the watchdog re-runs a step whose action never reported back", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { body: { results: [fetched("https://a.com")], errors: [] } },
    ]);
    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });

    // Simulate the scheduled action being lost: only the watchdog fires.
    await t.mutation(internal.jobs.watchdog, { jobId, step: 0 });
    await finish(t);

    // The lost step's own run is now stale and does nothing.
    expect(calls).toHaveLength(1);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      completed: 1,
    });
  });

  test("a stale step cannot record its results twice", async () => {
    const t = initConvexTest();
    mockFetch([{ body: { results: [fetched("https://a.com")], errors: [] } }]);
    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });
    await finish(t);

    await t.mutation(internal.jobs.recordBatch, {
      jobId,
      step: 0,
      pages: [toPage(fetched("https://a.com"), { storeContent: true })],
    });

    const { page } = await t.query(api.jobs.listPages, {
      jobId,
      paginationOpts: firstPage,
    });
    expect(page).toHaveLength(1);
  });
});

describe("storing results", () => {
  test("a page with fields Convex rejects is stored, not re-fetched", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      {
        body: {
          results: [
            { ...fetched("https://a.com"), schema_org: { $ref: "x" } },
            fetched("https://b.com"),
          ],
          errors: [],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com", "https://b.com"],
    });
    await finish(t);

    expect(calls).toHaveLength(1);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      completed: 2,
      failed: 0,
    });
  });

  test("matches a result whose URL came back in normalized form", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        body: {
          // Requested without the trailing slash and with an uppercase host.
          results: [fetched("https://a.com/")],
          errors: [{ url: "https://b.com/", error: "timeout" }],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startFetch, {
      urls: ["https://A.com", "https://b.com"],
    });
    await finish(t);

    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      completed: 1,
      failed: 1,
    });
    // Pages are stored under the URL the app asked for.
    expect(
      await t.query(api.jobs.getPage, { jobId, url: "https://A.com" }),
    ).toMatchObject({ status: "completed", final_url: "https://a.com/" });
    expect(
      await t.query(api.jobs.getPage, { jobId, url: "https://b.com" }),
    ).toMatchObject({ status: "failed", error: "timeout" });
  });

  test("a search result Convex rejects keeps its plain fields", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        body: {
          results: [
            {
              position: 1,
              title: "A",
              snippet: "s",
              url: "https://a.com",
              $meta: { x: 1 },
            },
          ],
        },
      },
      { body: { results: [fetched("https://a.com")], errors: [] } },
    ]);

    const jobId = await t.mutation(api.jobs.startSearchAndFetch, {
      query: "acme",
    });
    await finish(t);

    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({ status: "completed", completed: 1 });
    expect(job?.searchResults).toEqual([
      { position: 1, title: "A", snippet: "s", url: "https://a.com" },
    ]);
  });
});

describe("startSearchAndFetch", () => {
  test("searches, fetches the top results, and keeps the sources", async () => {
    const t = initConvexTest();
    const results = [
      searchResult(1, "https://a.com"),
      searchResult(2, "https://b.com"),
      searchResult(3, "https://c.com"),
    ];
    const calls = mockFetch([
      { body: { query: "acme", results, total_results: 3, page: 0 } },
      {
        body: {
          results: [fetched("https://a.com")],
          errors: [{ url: "https://b.com", error: "login_required" }],
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startSearchAndFetch, {
      query: "acme",
      searchOptions: { domain_type: "news" },
      maxResults: 2,
      fetchOptions: { maxCharacters: 1000 },
    });
    await finish(t);

    expect(new URL(calls[0].url).searchParams.get("domain_type")).toBe("news");
    expect(calls[1].body).toEqual({ urls: ["https://a.com", "https://b.com"] });

    const job = await t.query(api.jobs.get, { jobId });
    expect(job).toMatchObject({
      kind: "search_and_fetch",
      status: "completed",
      query: "acme",
      urls: ["https://a.com", "https://b.com"],
      total: 2,
      completed: 1,
      failed: 1,
    });
    expect(job?.searchResults).toEqual(results.slice(0, 2));

    const { page } = await t.query(api.jobs.listPages, {
      jobId,
      paginationOpts: firstPage,
    });
    expect(page[0]).toMatchObject({
      url: "https://a.com",
      status: "completed",
      position: 1,
      snippet: "Snippet 1",
    });
    expect(page[1]).toMatchObject({
      url: "https://b.com",
      status: "failed",
      error: "login_required",
      position: 2,
      snippet: "Snippet 2",
    });
  });

  test("completes with no pages when the search finds nothing", async () => {
    const t = initConvexTest();
    const calls = mockFetch([{ body: { query: "zzz", results: [] } }]);

    const jobId = await t.mutation(api.jobs.startSearchAndFetch, {
      query: "zzz",
    });
    await finish(t);

    expect(calls).toHaveLength(1);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "completed",
      total: 0,
      searchResults: [],
    });
  });

  test("fails the job when the search cannot run", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        status: 402,
        body: {
          error: { code: "INSUFFICIENT_CREDITS", message: "Add funds" },
        },
      },
    ]);

    const jobId = await t.mutation(api.jobs.startSearchAndFetch, {
      query: "acme",
    });
    await finish(t);

    const job = await t.query(api.jobs.get, { jobId });
    expect(job?.status).toBe("failed");
    expect(job?.error).toMatch(/402.*Add funds/);
  });

  test("validates maxResults", async () => {
    const t = initConvexTest();
    for (const maxResults of [0, 11, 2.5]) {
      await expect(
        t.mutation(api.jobs.startSearchAndFetch, { query: "acme", maxResults }),
      ).rejects.toThrow(/maxResults/);
    }
  });
});

describe("cancel, list and delete", () => {
  test("cancel stops a job before it fetches anything", async () => {
    const t = initConvexTest();
    const calls = mockFetch([]);
    const jobId = await t.mutation(api.jobs.startFetch, { urls: urlsOf(15) });

    expect(await t.mutation(api.jobs.cancel, { jobId })).toBe(true);
    await finish(t);

    expect(calls).toHaveLength(0);
    expect(await t.query(api.jobs.get, { jobId })).toMatchObject({
      status: "cancelled",
      finalized: true,
    });
    // Cancelling again is a no-op.
    expect(await t.mutation(api.jobs.cancel, { jobId })).toBe(false);
  });

  test("list returns recent jobs, optionally by status", async () => {
    const t = initConvexTest();
    mockFetch([{ body: { results: [fetched("https://a.com")], errors: [] } }]);
    const done = await t.mutation(api.jobs.startFetch, {
      urls: ["https://a.com"],
    });
    await finish(t);
    const cancelled = await t.mutation(api.jobs.startFetch, {
      urls: ["https://b.com"],
    });
    await t.mutation(api.jobs.cancel, { jobId: cancelled });

    const all = await t.query(api.jobs.list, {});
    expect(all.map((job) => job._id)).toEqual([cancelled, done]);
    const completed = await t.query(api.jobs.list, { status: "completed" });
    expect(completed.map((job) => job._id)).toEqual([done]);
    // Internal bookkeeping stays internal.
    expect(all[0]).not.toHaveProperty("step");
    expect(all[0]).not.toHaveProperty("onComplete");
  });

  test("deleteJob removes the job and all of its pages", async () => {
    const t = initConvexTest();
    const urls = urlsOf(20);
    mockFetch(
      [urls.slice(0, 10), urls.slice(10)].map((batch) => ({
        body: { results: batch.map((url) => fetched(url)), errors: [] },
      })),
    );
    const jobId = await t.mutation(api.jobs.startFetch, { urls });
    await finish(t);

    await t.mutation(api.jobs.deleteJob, { jobId });
    await finish(t);

    expect(await t.query(api.jobs.get, { jobId })).toBeNull();
    const remaining = await t.run(async (ctx) => {
      return await ctx.db.query("pages").collect();
    });
    expect(remaining).toHaveLength(0);
  });
});

describe("shaping pages", () => {
  test("truncateToBytes never splits a character", () => {
    expect(truncateToBytes("héllo", 100)).toBe("héllo");
    // "é" is two bytes: cutting at 2 bytes would split it.
    expect(truncateToBytes("héllo", 2)).toBe("h");
    expect(truncateToBytes("日本語", 4)).toBe("日");
  });

  test("clamps oversized text to fit a Convex document", () => {
    const page = toPage(fetched("https://a.com", "x".repeat(2_000_000)), {
      storeContent: true,
    });
    expect((page.text as string).length).toBe(800_000);
    expect(page.truncated).toBe(true);
  });

  test("drops an oversized json document tree instead of corrupting it", () => {
    const tree = { children: Array.from({ length: 100_000 }, () => "node!!") };
    const page = toPage(
      { ...fetched("https://a.com"), text: tree, format: "json" },
      { storeContent: true },
    );
    expect(page.text).toBeUndefined();
    expect(page.truncated).toBe(true);
  });

  test("keeps unmodelled result fields in extra", () => {
    const page = toPage(
      { ...fetched("https://a.com"), etag: '"abc"', links: ["https://a.com/x"] },
      { storeContent: true },
    );
    expect(page.extra).toEqual({ etag: '"abc"' });
    expect(page.links).toEqual(["https://a.com/x"]);
  });

  test("leaves out free-form fields Convex would reject", () => {
    const bad = { $ref: "#/definitions/x" };
    expect(storable(bad)).toBe(false);

    const page = toPage(
      {
        ...fetched("https://a.com"),
        text: { children: [bad] },
        format: "json",
        highlights: [{ text: "ok", rank: 1, meta: bad }],
        schema_org: bad,
      },
      { storeContent: true },
    );

    expect(page.text).toBeUndefined();
    expect(page.truncated).toBe(true);
    expect(page.highlights).toBeUndefined();
    expect(page.extra).toBeUndefined();
    expect(storable(page)).toBe(true);
    // The rest of the page survives.
    expect(page).toMatchObject({ status: "completed", title: "Title of https://a.com" });
  });

  test("never gives one response entry to two requested URLs", () => {
    const result = fetched("https://a.com/");
    const error = { url: "https://A.com", error: "timeout" };

    // Both URLs normalize to the same thing, but each has its own outcome.
    expect(
      matchResponse(["https://A.com", "https://a.com/"], {
        results: [result],
        errors: [error],
      }),
    ).toEqual([{ error }, { result }]);

    // With only one entry to go round, the second URL is left unmatched.
    expect(
      matchResponse(["https://A.com", "https://a.com"], { results: [result] }),
    ).toEqual([{ result }, {}]);
  });

  test("keeps stored search results small", () => {
    const small = { position: 1, title: "A", snippet: "s", url: "https://a.com" };
    expect(searchResultForStorage(small)).toEqual(small);

    const huge = searchResultForStorage({
      ...small,
      snippet: "x".repeat(120_000),
      raw_html: "y".repeat(50_000),
    });
    expect(huge).toEqual({
      position: 1,
      title: "A",
      snippet: "x".repeat(2_000),
      url: "https://a.com",
    });
    expect(searchResultForStorage("not an object")).toEqual({});
  });

  test("keeps retry hints on a failed page", () => {
    const page = toFailedPage("https://a.com", {
      url: "https://a.com",
      error: "selector_not_matched",
      candidate_selectors: ["main", "article"],
    });
    expect(page).toMatchObject({
      status: "failed",
      error: "selector_not_matched",
      extra: { candidate_selectors: ["main", "article"] },
    });
  });
});
