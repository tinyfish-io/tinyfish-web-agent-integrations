/// <reference types="vite/client" />
import { test, vi } from "vitest";
import { convexTest } from "convex-test";
import schema from "./schema.js";
import { RETRY } from "./api.js";

export const modules = import.meta.glob("./**/*.*s");

export const TEST_API_KEY = "sk-tinyfish-test";

export function initConvexTest() {
  process.env.TINYFISH_API_KEY = TEST_API_KEY;
  delete process.env.TINYFISH_SEARCH_URL;
  delete process.env.TINYFISH_FETCH_URL;
  // Keep retries instant so tests don't wait on backoff.
  RETRY.baseDelayMs = 0;
  RETRY.maxDelayMs = 0;
  return convexTest(schema, modules);
}

export type FetchCall = {
  url: string;
  method: string;
  body: any;
  headers: Record<string, string>;
};

export type CannedResponse = {
  status?: number;
  body?: unknown;
  /** Raw body, for non-JSON responses. */
  text?: string;
  headers?: Record<string, string>;
  /** Reject instead of responding, like a network failure. */
  throws?: string;
};

/** Queue of canned responses, matched in order, for the mocked `fetch`. */
export function mockFetch(responses: CannedResponse[]) {
  const calls: FetchCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async (
        url: string | URL,
        init?: {
          method?: string;
          body?: string;
          headers?: Record<string, string>;
        },
      ) => {
        calls.push({
          url: String(url),
          method: init?.method ?? "GET",
          body: init?.body ? JSON.parse(init.body) : undefined,
          headers: init?.headers ?? {},
        });
        const next = responses.shift() ?? { body: {} };
        if (next.throws) throw new Error(next.throws);
        return new Response(next.text ?? JSON.stringify(next.body ?? {}), {
          status: next.status ?? 200,
          headers: next.headers,
        });
      },
    ),
  );
  return calls;
}

/** A Fetch API result for `url`, as TinyFish would return it. */
export function fetched(url: string, text = `# ${url}`) {
  return {
    url,
    final_url: url,
    title: `Title of ${url}`,
    description: null,
    language: "en",
    author: null,
    published_date: null,
    text,
    format: "markdown",
    latency_ms: 120,
  };
}

test("setup", () => {});
