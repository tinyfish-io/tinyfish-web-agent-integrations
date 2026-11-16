import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  fetchPages,
  publicFailure,
  RETRY,
  search,
  TIMEOUT_MS,
  TinyFishError,
} from "../src/tinyfish.js";
import { VERSION } from "../src/version.js";

interface Reply {
  status?: number;
  body?: unknown;
  headers?: Record<string, string>;
}

/** Answer `fetch` with these replies in order, recording each request. */
function mockFetch(replies: (Reply | Error)[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: URL, init: RequestInit) => {
      calls.push({ url: String(url), init });
      const reply = replies[calls.length - 1];
      if (!reply) throw new Error("unexpected request");
      if (reply instanceof Error) throw reply;
      return new Response(
        typeof reply.body === "string"
          ? reply.body
          : JSON.stringify(reply.body ?? {}),
        { status: reply.status ?? 200, headers: reply.headers },
      );
    }),
  );
  return calls;
}

beforeEach(() => {
  vi.stubEnv("TINYFISH_API_KEY", "sk-test");
  RETRY.baseDelayMs = 0;
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

test("VERSION is the package.json version", () => {
  const pkg = JSON.parse(
    readFileSync(new URL("../package.json", import.meta.url), "utf8"),
  );
  expect(VERSION).toBe(pkg.version);
});

describe("search", () => {
  test("sends options as query parameters, with the key and attribution", async () => {
    const response = { query: "q", results: [], total_results: 0, page: 0 };
    const calls = mockFetch([{ body: response }]);

    expect(
      await search({
        query: "q",
        include_domains: ["a.com", "b.com"],
        recency_minutes: 60,
      }),
    ).toEqual(response);

    const url = new URL(calls[0].url);
    expect(url.origin).toBe("https://api.search.tinyfish.ai");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      query: "q",
      include_domains: "a.com,b.com",
      recency_minutes: "60",
    });
    expect(calls[0].init.method).toBe("GET");
    expect(calls[0].init.headers).toMatchObject({
      "X-API-Key": "sk-test",
      "X-TF-Client-Name": "apify",
      "X-TF-Client-Version": VERSION,
    });
  });
});

describe("fetchPages", () => {
  test("posts the options and always returns both lists", async () => {
    const calls = mockFetch([{ body: { results: [{ url: "https://a.com" }] } }]);

    expect(
      await fetchPages({ urls: ["https://a.com"], format: "markdown" }),
    ).toEqual({ results: [{ url: "https://a.com" }], errors: [] });

    expect(calls[0].url).toBe("https://api.fetch.tinyfish.ai/");
    expect(calls[0].init.method).toBe("POST");
    expect(JSON.parse(String(calls[0].init.body))).toEqual({
      urls: ["https://a.com"],
      format: "markdown",
    });
  });
});

describe("failures", () => {
  test("a transient failure is retried", async () => {
    const calls = mockFetch([
      { status: 503 },
      new TypeError("fetch failed"),
      { body: { results: [] } },
    ]);
    await expect(search({ query: "q" })).resolves.toEqual({ results: [] });
    expect(calls).toHaveLength(3);
  });

  test("retries stop after the configured attempts", async () => {
    const calls = mockFetch([{ status: 500 }, { status: 500 }, { status: 500 }]);
    await expect(search({ query: "q" })).rejects.toMatchObject({ status: 500 });
    expect(calls).toHaveLength(1 + RETRY.attempts);
  });

  test("a retry that would pass the deadline is not started", async () => {
    const { total } = TIMEOUT_MS.search;
    TIMEOUT_MS.search.total = 1000;
    RETRY.baseDelayMs = 10_000;
    try {
      const calls = mockFetch([{ status: 503 }]);
      await expect(search({ query: "q" })).rejects.toMatchObject({
        status: 503,
      });
      expect(calls).toHaveLength(1);
    } finally {
      TIMEOUT_MS.search.total = total;
    }
  });

  test("an invalid request is not retried, and its message is kept", async () => {
    const calls = mockFetch([
      {
        status: 400,
        body: {
          error: { code: "INVALID_INPUT", message: "after_date is invalid" },
          request_id: "req_1",
        },
      },
    ]);
    const error = await search({ query: "q" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(TinyFishError);
    expect(error).toMatchObject({
      endpoint: "search",
      status: 400,
      detail: "after_date is invalid",
      apiCode: "INVALID_INPUT",
      requestId: "req_1",
    });
    expect(calls).toHaveLength(1);
  });

  test("a 200 that is not JSON is a failure", async () => {
    mockFetch([{ body: "<html>" }]);
    await expect(search({ query: "q" })).rejects.toMatchObject({
      detail: "response was not JSON",
    });
  });
});

describe("publicFailure", () => {
  const failure = (status: number, detail = "x", code?: string) =>
    publicFailure(new TinyFishError("search", status, detail, code));

  test("an invalid request passes TinyFish's message on", () => {
    expect(failure(400, "after_date is invalid")).toEqual({
      status: 400,
      code: "invalid_input",
      message: "after_date is invalid",
    });
    expect(failure(422, "bad selector").status).toBe(400);
  });

  test("our own problems are reported without the details", () => {
    for (const status of [401, 402, 403, 500]) {
      const result = failure(status, "wallet is empty", "INSUFFICIENT_CREDITS");
      expect(result.status).toBe(502);
      expect(result.message).not.toContain("wallet");
    }
    expect(failure(429).status).toBe(429);
    expect(failure(0).status).toBe(504);
  });
});
