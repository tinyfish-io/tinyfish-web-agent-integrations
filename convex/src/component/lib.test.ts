/// <reference types="vite/client" />
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, test, vi } from "vitest";
import { api } from "./_generated/api.js";
import {
  fetched,
  initConvexTest,
  mockFetch,
  TEST_API_KEY,
} from "./setup.test.js";
import { VERSION } from "./version.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("VERSION matches package.json", () => {
  const pkg = JSON.parse(
    readFileSync(new URL("../../package.json", import.meta.url), "utf8"),
  );
  expect(VERSION).toBe(pkg.version);
});

describe("search", () => {
  test("sends the query and options as query parameters", async () => {
    const t = initConvexTest();
    const response = {
      query: "convex components",
      results: [
        {
          position: 1,
          site_name: "convex.dev",
          title: "Components",
          snippet: "Reusable backend modules",
          url: "https://www.convex.dev/components",
        },
      ],
      total_results: 1,
      page: 0,
    };
    const calls = mockFetch([{ body: response }]);

    const result = await t.action(api.lib.search, {
      query: "convex components",
      options: {
        location: "US",
        include_domains: ["convex.dev", "github.com"],
        recency_minutes: 60,
        extra: { future_param: "x" },
      },
    });

    expect(result).toEqual(response);
    const url = new URL(calls[0].url);
    expect(url.origin).toBe("https://api.search.tinyfish.ai");
    expect(calls[0].method).toBe("GET");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      query: "convex components",
      location: "US",
      include_domains: "convex.dev,github.com",
      recency_minutes: "60",
      future_param: "x",
    });
  });

  test("authenticates and tags the request as coming from Convex", async () => {
    const t = initConvexTest();
    const calls = mockFetch([{ body: { results: [] } }]);

    await t.action(api.lib.search, { query: "anything" });

    expect(calls[0].headers).toMatchObject({
      "X-API-Key": TEST_API_KEY,
      "X-TF-Client-Name": "convex",
      "X-TF-Client-Version": VERSION,
    });
  });

  test("rejects an empty query without calling TinyFish", async () => {
    const t = initConvexTest();
    const calls = mockFetch([]);

    await expect(t.action(api.lib.search, { query: "  " })).rejects.toThrow(
      /query/,
    );
    expect(calls).toHaveLength(0);
  });

  test("surfaces API errors with status, code and message", async () => {
    const t = initConvexTest();
    mockFetch([
      {
        status: 402,
        body: {
          error: {
            code: "INSUFFICIENT_CREDITS",
            message: "Daily allowance used and wallet is empty",
          },
        },
      },
    ]);

    await expect(
      t.action(api.lib.search, { query: "anything" }),
    ).rejects.toThrow(
      /TinyFish search failed \(402\): Daily allowance used and wallet is empty/,
    );
  });

  test("retries a 429 and succeeds", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { status: 429, body: { error: { message: "rate limited" } } },
      { body: { results: [] } },
    ]);

    const result = await t.action(api.lib.search, { query: "anything" });

    expect(result).toEqual({ results: [] });
    expect(calls).toHaveLength(2);
  });

  test("retries a network failure", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { throws: "socket hang up" },
      { body: { results: [] } },
    ]);

    await t.action(api.lib.search, { query: "anything" });

    expect(calls).toHaveLength(2);
  });

  test("does not retry a 400", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { status: 400, body: { error: { message: "bad page" } } },
    ]);

    await expect(
      t.action(api.lib.search, { query: "anything", options: { page: 99 } }),
    ).rejects.toThrow(/bad page/);
    expect(calls).toHaveLength(1);
  });

  test("gives up after the retries run out", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      { status: 503, text: "upstream unavailable" },
      { status: 503, text: "upstream unavailable" },
      { status: 503, text: "upstream unavailable" },
    ]);

    await expect(
      t.action(api.lib.search, { query: "anything" }),
    ).rejects.toThrow(/TinyFish search failed \(503\): upstream unavailable/);
    expect(calls).toHaveLength(3);
  });

  test("honors endpoint overrides", async () => {
    const t = initConvexTest();
    process.env.TINYFISH_SEARCH_URL = "http://localhost:4010/search/";
    const calls = mockFetch([{ body: { results: [] } }]);

    await t.action(api.lib.search, { query: "anything" });

    expect(calls[0].url).toBe("http://localhost:4010/search?query=anything");
  });
});

describe("fetch", () => {
  test("posts the URLs and options, and returns results and errors", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      {
        body: {
          results: [fetched("https://a.com")],
          errors: [{ url: "https://b.com", error: "bot_blocked" }],
        },
      },
    ]);

    const response = await t.action(api.lib.fetch, {
      urls: ["https://a.com", "https://b.com"],
      options: { format: "markdown", links: true, ttl: 0 },
    });

    expect(calls[0].url).toBe("https://api.fetch.tinyfish.ai/");
    expect(calls[0].method).toBe("POST");
    expect(calls[0].body).toEqual({
      urls: ["https://a.com", "https://b.com"],
      format: "markdown",
      links: true,
      ttl: 0,
    });
    expect(response.results).toHaveLength(1);
    expect(response.results[0].url).toBe("https://a.com");
    expect(response.errors).toEqual([
      { url: "https://b.com", error: "bot_blocked" },
    ]);
  });

  test("caps text at maxCharacters without sending it to TinyFish", async () => {
    const t = initConvexTest();
    const calls = mockFetch([
      {
        body: {
          results: [
            fetched("https://a.com", "x".repeat(50)),
            fetched("https://b.com", "short"),
          ],
          errors: [],
        },
      },
    ]);

    const response = await t.action(api.lib.fetch, {
      urls: ["https://a.com", "https://b.com"],
      options: { maxCharacters: 10 },
    });

    expect(calls[0].body).toEqual({ urls: ["https://a.com", "https://b.com"] });
    expect(response.results[0].text).toBe("x".repeat(10));
    expect(response.results[0].truncated).toBe(true);
    expect(response.results[1].text).toBe("short");
    expect(response.results[1].truncated).toBeUndefined();
  });

  test("rejects more than 10 URLs and points at startFetch", async () => {
    const t = initConvexTest();
    const calls = mockFetch([]);
    const urls = Array.from({ length: 11 }, (_, i) => `https://a.com/${i}`);

    await expect(t.action(api.lib.fetch, { urls })).rejects.toThrow(
      /startFetch/,
    );
    expect(calls).toHaveLength(0);
  });

  test("fails clearly when the API key is missing", async () => {
    const t = initConvexTest();
    delete process.env.TINYFISH_API_KEY;
    mockFetch([]);

    await expect(
      t.action(api.lib.fetch, { urls: ["https://a.com"] }),
    ).rejects.toThrow(/TINYFISH_API_KEY/);
  });
});
