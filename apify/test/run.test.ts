import { describe, expect, test, vi } from "vitest";
import { runFromInput, type RunDeps } from "../src/run.js";
import { TinyFishError } from "../src/tinyfish.js";

/** Fake TinyFish calls, dataset, and charging. Every URL with "bad" fails. */
function deps() {
  return {
    search: vi.fn<RunDeps["search"]>(async () => ({
      query: "q",
      results: [
        { position: 1, title: "A", url: "https://a.com" },
        { position: 2, title: "B", url: "https://b.com" },
      ],
    })),
    fetchPages: vi.fn<RunDeps["fetchPages"]>(async ({ urls }) => ({
      results: urls
        .filter((url) => !url.includes("bad"))
        .map((url) => ({ url, text: "# page" })),
      errors: urls
        .filter((url) => url.includes("bad"))
        .map((url) => ({ url, error: "page_not_found" })),
    })),
    pushData: vi.fn<RunDeps["pushData"]>(async () => {}),
    charge: vi.fn<RunDeps["charge"]>(async () => {}),
    chargeable: vi.fn<RunDeps["chargeable"]>(() => Infinity),
  };
}

const urls = (count: number) =>
  Array.from({ length: count }, (_, i) => `https://a.com/${i}`);

describe("search mode", () => {
  test("stores one item per result, then charges one search", async () => {
    const d = deps();
    const message = await runFromInput(
      // The Console form sends the fields of both modes at once.
      { query: "q", page: 1, urls: ["https://ignored.com"], format: "html" },
      d,
    );
    expect(d.search).toHaveBeenCalledWith({ query: "q", page: 1 });
    expect(d.pushData).toHaveBeenCalledWith([
      { query: "q", position: 1, title: "A", url: "https://a.com" },
      { query: "q", position: 2, title: "B", url: "https://b.com" },
    ]);
    expect(d.charge).toHaveBeenCalledExactlyOnceWith("search");
    expect(d.pushData.mock.invocationCallOrder[0]).toBeLessThan(
      d.charge.mock.invocationCallOrder[0],
    );
    expect(message).toBe('2 results for "q".');
  });

  test("no results: nothing stored, nothing charged", async () => {
    const d = deps();
    d.search.mockResolvedValue({ results: [] });
    expect(await runFromInput({ query: "q" }, d)).toBe('No results for "q".');
    expect(d.pushData).not.toHaveBeenCalled();
    expect(d.charge).not.toHaveBeenCalled();
  });

  test("does not search when the spending limit cannot cover it", async () => {
    const d = deps();
    d.chargeable.mockReturnValue(0);
    await expect(runFromInput({ query: "q" }, d)).rejects.toThrow(
      "maximum cost is too low",
    );
    expect(d.search).not.toHaveBeenCalled();
  });
});

describe("fetch mode", () => {
  test("fetches in batches of 10 and charges pages, not failures", async () => {
    const d = deps();
    const input = [...urls(11), "https://a.com/bad"];
    const message = await runFromInput({ mode: "fetch", urls: input }, d);

    expect(d.fetchPages.mock.calls.map(([o]) => o.urls.length)).toEqual([10, 2]);
    expect(d.pushData.mock.calls.map(([items, event]) => [items.length, event]))
      .toEqual([
        [10, "fetch"],
        [1, "fetch"],
        [1, undefined],
      ]);
    expect(message).toBe("Fetched 11 of 12 pages, 1 failed.");
  });

  test("passes the fetch options on and ignores search fields", async () => {
    const d = deps();
    await runFromInput(
      { mode: "fetch", urls: urls(1), format: "html", query: "prefilled" },
      d,
    );
    expect(d.fetchPages).toHaveBeenCalledWith({ urls: urls(1), format: "html" });
  });

  test("never fetches more pages than the spending limit allows", async () => {
    let budget = 3;
    const d = deps();
    d.chargeable.mockImplementation(() => budget);
    d.pushData.mockImplementation(async (items, event) => {
      if (event) budget -= items.length;
    });
    const message = await runFromInput({ mode: "fetch", urls: urls(5) }, d);
    expect(d.fetchPages.mock.calls.map(([o]) => o.urls.length)).toEqual([3]);
    expect(message).toBe(
      "Fetched 3 of 5 pages, 2 skipped because the run's maximum cost was reached.",
    );
  });

  test("a failed batch keeps the earlier pages and is not fetched again", async () => {
    const d = deps();
    d.fetchPages.mockImplementationOnce(async ({ urls }) => ({
      results: urls.map((url) => ({ url })),
      errors: [],
    }));
    d.fetchPages.mockImplementationOnce(async () => {
      throw new TinyFishError("fetch", 503, "down");
    });
    await expect(
      runFromInput({ mode: "fetch", urls: urls(15) }, d),
    ).rejects.toBeInstanceOf(TinyFishError);
    expect(d.fetchPages).toHaveBeenCalledTimes(2);
    expect(d.pushData).toHaveBeenCalledExactlyOnceWith(expect.any(Array), "fetch");
  });

  test("a page that cannot be stored stops the run without re-fetching", async () => {
    const d = deps();
    d.pushData.mockRejectedValue(new Error("dataset rejected the item"));
    await expect(
      runFromInput({ mode: "fetch", urls: urls(15) }, d),
    ).rejects.toThrow("dataset rejected the item");
    expect(d.fetchPages).toHaveBeenCalledTimes(1);
  });

  test("takes up to 100 URLs", async () => {
    await expect(
      runFromInput({ mode: "fetch", urls: urls(101) }, deps()),
    ).rejects.toThrow("`urls` takes at most 100 items (got 101).");
  });
});

describe("input", () => {
  test.each([
    [null, "The input must be a JSON object."],
    [{ mode: "crawl" }, '`mode` must be "search" or "fetch".'],
    [{ urls: ["https://a.com"] }, 'set `mode` to "fetch"'],
    [{}, "`query` is required."],
    [{ mode: "fetch" }, "`urls` is required."],
  ])("%j is rejected", async (input, message) => {
    await expect(runFromInput(input, deps())).rejects.toThrow(message);
  });
});
