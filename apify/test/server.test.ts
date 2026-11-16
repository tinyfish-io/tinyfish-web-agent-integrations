import type { AddressInfo } from "node:net";
import { afterEach, describe, expect, test, vi } from "vitest";
import { createServer, type ServerDeps } from "../src/server.js";
import { TinyFishError } from "../src/tinyfish.js";

const SEARCH = {
  query: "q",
  results: [{ position: 1, title: "A", url: "https://a.com" }],
  total_results: 1,
  page: 0,
};

let close: (() => void) | undefined;
afterEach(() => close?.());

/** Start the server on a free port with fake TinyFish calls and charging. */
async function start(overrides: Partial<ServerDeps> = {}) {
  const deps = {
    search: vi.fn(async () => SEARCH as Record<string, unknown>),
    fetchPages: vi.fn(async () => ({
      results: [{ url: "https://a.com", text: "# A" }],
      errors: [{ url: "https://b.com", error: "page_not_found", status: 404 }],
    })),
    charge: vi.fn(async () => {}),
    ...overrides,
  };
  const server = createServer(deps);
  await new Promise<void>((resolve) => server.listen(0, resolve));
  close = () => server.close();
  const origin = `http://localhost:${(server.address() as AddressInfo).port}`;
  const call = async (path: string, init: RequestInit = {}) => {
    const response = await fetch(origin + path, {
      ...init,
      headers: { "X-Actor-Request-ID": "req_1", ...init.headers },
    });
    const body: any = await response.json().catch(() => null);
    return { response, body };
  };
  const post = (path: string, body: unknown) =>
    call(path, { method: "POST", body: JSON.stringify(body) });
  return { deps, call, post };
}

test("the readiness probe is answered on any path", async () => {
  const { deps, call } = await start();
  const { response } = await call("/search", {
    headers: { "x-apify-container-server-readiness-probe": "1" },
  });
  expect(response.status).toBe(200);
  expect(deps.search).not.toHaveBeenCalled();
});

describe("/search", () => {
  test("GET searches and charges the request once", async () => {
    const { deps, call } = await start();
    const { response, body } = await call(
      "/search?query=q&recency_minutes=60&include_domains=a.com,b.com",
    );
    expect(response.status).toBe(200);
    expect(body).toEqual(SEARCH);
    expect(deps.search).toHaveBeenCalledWith({
      query: "q",
      recency_minutes: 60,
      include_domains: ["a.com", "b.com"],
    });
    expect(deps.charge).toHaveBeenCalledWith("search", 1, "req_1");
  });

  test("POST takes the same fields as JSON", async () => {
    const { deps, post } = await start();
    const { response } = await post("/search", { query: "q", page: 2 });
    expect(response.status).toBe(200);
    expect(deps.search).toHaveBeenCalledWith({ query: "q", page: 2 });
  });

  test("a search with no results is not charged", async () => {
    const { deps, call } = await start({
      search: vi.fn(async () => ({ query: "q", results: [] })),
    });
    const { response } = await call("/search?query=q");
    expect(response.status).toBe(200);
    expect(deps.charge).toHaveBeenCalledWith("search", 0, "req_1");
  });
});

describe("/fetch", () => {
  test("charges one event per page that came back, not per URL", async () => {
    const { deps, post } = await start();
    const { response, body } = await post("/fetch", {
      urls: ["https://a.com", "https://b.com"],
      format: "markdown",
    });
    expect(response.status).toBe(200);
    expect(body.results).toHaveLength(1);
    expect(body.errors).toHaveLength(1);
    expect(deps.fetchPages).toHaveBeenCalledWith({
      urls: ["https://a.com", "https://b.com"],
      format: "markdown",
    });
    expect(deps.charge).toHaveBeenCalledWith("fetch", 1, "req_1");
  });

  test("GET takes urls as a repeated parameter", async () => {
    const { deps, call } = await start();
    await call("/fetch?urls=https://a.com/x,y&urls=https://b.com&links=true");
    expect(deps.fetchPages).toHaveBeenCalledWith({
      urls: ["https://a.com/x,y", "https://b.com"],
      links: true,
    });
  });

  test("more than 10 URLs is rejected before anything is fetched", async () => {
    const { deps, post } = await start();
    const urls = Array.from({ length: 11 }, (_, i) => `https://a.com/${i}`);
    const { response, body } = await post("/fetch", { urls });
    expect(response.status).toBe(400);
    expect(body.error.code).toBe("invalid_input");
    expect(deps.fetchPages).not.toHaveBeenCalled();
  });
});

describe("failures", () => {
  test("invalid input is a 400 that names the problem, uncharged", async () => {
    const { deps, call, post } = await start();
    const missing = await call("/search");
    expect(missing.response.status).toBe(400);
    expect(missing.body).toEqual({
      error: { code: "invalid_input", message: "`query` is required." },
    });
    expect((await call("/search?query=q&page=x")).response.status).toBe(400);
    expect((await post("/search", [1])).response.status).toBe(400);
    const notJson = await call("/search", { method: "POST", body: "{" });
    expect(notJson.body.error.message).toBe(
      "The request body must be valid JSON.",
    );
    expect(deps.search).not.toHaveBeenCalled();
    expect(deps.charge).not.toHaveBeenCalled();
  });

  test("a TinyFish failure is mapped and never charged", async () => {
    const { deps, call } = await start({
      search: vi.fn(async () => {
        throw new TinyFishError(
          "search",
          402,
          "wallet is empty",
          "INSUFFICIENT_CREDITS",
        );
      }),
    });
    const { response, body } = await call("/search?query=q");
    expect(response.status).toBe(502);
    expect(body.error.code).toBe("upstream_error");
    expect(JSON.stringify(body)).not.toContain("wallet");
    expect(deps.charge).not.toHaveBeenCalled();
  });

  test("a rate limit says when to retry", async () => {
    const { call } = await start({
      search: vi.fn(async () => {
        throw new TinyFishError("search", 429, "slow down");
      }),
    });
    const { response } = await call("/search?query=q");
    expect(response.status).toBe(429);
    expect(response.headers.get("retry-after")).toBe("5");
  });

  test("results are withheld when the charge fails", async () => {
    const { call } = await start({
      charge: vi.fn(async () => {
        throw new Error("charge rejected");
      }),
    });
    const { response, body } = await call("/search?query=q");
    expect(response.status).toBe(500);
    expect(body).toEqual({
      error: {
        code: "internal_error",
        message: "The request could not be completed. Try again.",
      },
    });
  });

  test("unknown paths, methods, and oversized bodies", async () => {
    const { deps, call } = await start();
    expect((await call("/nope")).response.status).toBe(404);
    // A path that is not a valid URL must not crash a run other users share.
    expect((await call("//")).response.status).toBe(404);
    const wrongMethod = await call("/search", { method: "DELETE" });
    expect(wrongMethod.response.status).toBe(405);
    expect(wrongMethod.response.headers.get("allow")).toBe("GET, POST");
    const tooBig = await call("/fetch", {
      method: "POST",
      body: JSON.stringify({ urls: ["https://a.com"], purpose: "x".repeat(300_000) }),
    });
    expect(tooBig.response.status).toBe(413);
    expect(deps.fetchPages).not.toHaveBeenCalled();
  });

  test("GET / describes the endpoints", async () => {
    const { call } = await start();
    const { response, body } = await call("/");
    expect(response.status).toBe(200);
    expect(Object.keys(body.endpoints)).toHaveLength(2);
  });
});
