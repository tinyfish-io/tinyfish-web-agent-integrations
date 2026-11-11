/// <reference types="vite/client" />
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { convexTest } from "convex-test";
import tinyfish from "@tiny-fish/convex/test";
import { api } from "./_generated/api.js";
import schema from "./schema.js";

const modules = import.meta.glob("./**/*.*s");

/**
 * Apps that install the component register it in their tests with the helper
 * exported from `@tiny-fish/convex/test`, then stub `fetch` for TinyFish.
 */
function initConvexTest() {
  process.env.TINYFISH_API_KEY = "sk-tinyfish-test";
  const t = convexTest(schema, modules);
  tinyfish.register(t);
  return t;
}

function mockTinyFish(bodies: unknown[]) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      calls.push(String(url));
      return new Response(JSON.stringify(bodies.shift() ?? {}), {
        status: 200,
      });
    }),
  );
  return calls;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("one-shot calls require a signed-in user", async () => {
  const t = initConvexTest();
  const calls = mockTinyFish([]);

  await expect(
    t.action(api.example.searchWeb, { query: "convex" }),
  ).rejects.toThrow(/Sign in/);
  expect(calls).toHaveLength(0);
});

test("searchWeb returns cited results", async () => {
  const t = initConvexTest();
  mockTinyFish([
    {
      query: "convex",
      results: [
        {
          position: 1,
          site_name: "convex.dev",
          title: "Convex",
          snippet: "The backend platform that keeps your app in sync",
          url: "https://www.convex.dev",
        },
      ],
      total_results: 1,
      page: 0,
    },
  ]);

  const results = await t
    .withIdentity({ subject: "user-1" })
    .action(api.example.searchWeb, { query: "convex" });

  expect(results).toEqual([
    {
      title: "Convex",
      snippet: "The backend platform that keeps your app in sync",
      url: "https://www.convex.dev",
    },
  ]);
});

test("research runs a job and saves a brief with sources and failures", async () => {
  const t = initConvexTest();
  const asUser = t.withIdentity({ subject: "user-1" });
  mockTinyFish([
    {
      query: "acme loop",
      results: [
        {
          position: 1,
          title: "Acme Loop",
          snippet: "Workflow automation for support teams",
          url: "https://acmeloop.dev/",
        },
        {
          position: 2,
          title: "Acme Loop on X",
          snippet: "Posts from Acme Loop",
          url: "https://x.com/acmeloop",
        },
      ],
    },
    {
      results: [
        {
          url: "https://acmeloop.dev/",
          final_url: "https://acmeloop.dev/",
          title: "Acme Loop",
          text: "# Acme Loop",
          format: "markdown",
        },
      ],
      errors: [{ url: "https://x.com/acmeloop", error: "login_required" }],
    },
  ]);

  const jobId = await asUser.mutation(api.example.research, {
    query: "acme loop",
  });
  expect(await asUser.query(api.example.job, { jobId })).toMatchObject({
    status: "queued",
  });

  await t.finishAllScheduledFunctions(() => vi.advanceTimersByTime(10_000));

  expect(await asUser.query(api.example.job, { jobId })).toMatchObject({
    status: "completed",
    total: 2,
    completed: 1,
    failed: 1,
  });
  expect(await asUser.query(api.example.brief, { jobId })).toMatchObject({
    query: "acme loop",
    status: "completed",
    sources: [
      {
        url: "https://acmeloop.dev/",
        title: "Acme Loop",
        snippet: "Workflow automation for support teams",
      },
    ],
    failures: [{ url: "https://x.com/acmeloop", error: "login_required" }],
  });
});

test("a job is only visible to the user who started it", async () => {
  const t = initConvexTest();
  mockTinyFish([]);
  const jobId = await t
    .withIdentity({ subject: "user-1" })
    .mutation(api.example.readMany, { urls: ["https://a.com/"] });

  await expect(
    t.withIdentity({ subject: "user-2" }).query(api.example.job, { jobId }),
  ).rejects.toThrow(/No such job/);

  expect(
    await t
      .withIdentity({ subject: "user-1" })
      .mutation(api.example.cancel, { jobId }),
  ).toBe(true);
});

test("removing a job removes its brief, and a running job leaves none behind", async () => {
  const t = initConvexTest();
  const asUser = t.withIdentity({ subject: "user-1" });
  const hop = () => vi.advanceTimersByTime(10_000);
  const search = {
    query: "acme",
    results: [{ position: 1, title: "Acme", snippet: "", url: "https://a.com/" }],
  };
  const fetch = {
    results: [{ url: "https://a.com/", final_url: "https://a.com/", text: "# A" }],
    errors: [],
  };
  mockTinyFish([search, fetch]);
  const countBriefs = () =>
    t.run(async (ctx) => (await ctx.db.query("briefs").collect()).length);

  // A finished job: its brief goes when the job does.
  const finished = await asUser.mutation(api.example.research, { query: "acme" });
  await t.finishAllScheduledFunctions(hop);
  expect(await countBriefs()).toBe(1);
  await asUser.mutation(api.example.remove, { jobId: finished });
  await t.finishAllScheduledFunctions(hop);
  expect(await countBriefs()).toBe(0);

  // A job removed before it ran: its completion callback saves nothing.
  const running = await asUser.mutation(api.example.research, { query: "acme" });
  await asUser.mutation(api.example.remove, { jobId: running });
  await t.finishAllScheduledFunctions(hop);
  expect(await countBriefs()).toBe(0);
});
