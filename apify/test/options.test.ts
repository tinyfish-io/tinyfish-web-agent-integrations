import { describe, expect, test } from "vitest";
import { InvalidInput, parseFetch, parseSearch } from "../src/options.js";

describe("query strings", () => {
  test("values are converted to each field's type", () => {
    expect(
      parseSearch(
        {
          query: "convex components",
          recency_minutes: "60",
          include_domains: "convex.dev, github.com",
          domain_type: "news",
        },
        { source: "query" },
      ),
    ).toEqual({
      query: "convex components",
      recency_minutes: 60,
      include_domains: ["convex.dev", "github.com"],
      domain_type: "news",
    });
    expect(
      parseFetch(
        { urls: "https://a.com", links: "true", image_links: "0", ttl: "0" },
        { source: "query" },
      ),
    ).toEqual({
      urls: ["https://a.com"],
      links: true,
      image_links: false,
      ttl: 0,
    });
  });

  test("a repeated parameter is a list, and a blank one is not set", () => {
    expect(
      parseFetch(
        {
          urls: ["https://a.com/x,y", "https://b.com"],
          // A CSS selector can hold a comma, so selectors are never split.
          include_selectors: "main, footer",
          format: "",
        },
        { source: "query" },
      ),
    ).toEqual({
      urls: ["https://a.com/x,y", "https://b.com"],
      include_selectors: ["main, footer"],
    });
  });

  test("a single-value parameter cannot be repeated", () => {
    expect(() =>
      parseSearch({ query: ["a", "b"] }, { source: "query" }),
    ).toThrow("`query` must be given once.");
  });
});

describe("validation", () => {
  test.each([
    [{ query: "x", page: "1.5" }, "`page` must be an integer."],
    [{ query: "x", page: "NaN" }, "`page` must be an integer."],
    [{ query: "x", page: "-1" }, "`page` must be at least 0."],
    [{ query: "x", page: "11" }, "`page` must be at most 10."],
    [{ query: "x", domain_type: "images" }, "`domain_type` must be one of"],
    [{ query: "   " }, "`query` is required."],
    [{}, "`query` is required."],
    [{ query: "x", formats: "markdown" }, "Unknown parameter `formats`."],
  ])("search rejects %j", (raw, message) => {
    expect(() => parseSearch(raw, { source: "query" })).toThrow(message);
  });

  test("a JSON body must already use the right types", () => {
    expect(() =>
      parseSearch({ query: "x", page: "1" }, { source: "json" }),
    ).toThrow("`page` must be an integer.");
    expect(() =>
      parseFetch({ urls: ["https://a.com"], links: "true" }, { source: "json" }),
    ).toThrow("`links` must be true or false.");
    expect(() =>
      parseFetch({ urls: ["https://a.com", 5] }, { source: "json" }),
    ).toThrow("`urls` must be a list of strings.");
    expect(() => parseSearch({ query: 5 }, { source: "json" })).toThrow(
      InvalidInput,
    );
  });

  test("urls are required, trimmed, and capped", () => {
    expect(() => parseFetch({ urls: [] }, { source: "json" })).toThrow(
      "`urls` is required.",
    );
    expect(() => parseFetch({ urls: ["  "] }, { source: "json" })).toThrow(
      "`urls` is required.",
    );
    const urls = Array.from({ length: 11 }, (_, i) => `https://a.com/${i}`);
    expect(() => parseFetch({ urls }, { source: "json" })).toThrow(
      "`urls` takes at most 10 items (got 11).",
    );
    expect(
      parseFetch({ urls }, { source: "json", maxItems: { urls: 100 } }).urls,
    ).toHaveLength(11);
  });

  test("a repeated URL is fetched, and charged, once", () => {
    expect(
      parseFetch(
        { urls: ["https://a.com", " https://a.com ", "https://b.com"] },
        { source: "json" },
      ).urls,
    ).toEqual(["https://a.com", "https://b.com"]);
  });

  test("blank, null, and unknown keys can be skipped for the Actor input", () => {
    expect(
      parseSearch(
        {
          mode: "search",
          query: "x",
          urls: ["https://a.com"],
          page: null,
          location: "",
        },
        { source: "json", ignoreUnknown: true },
      ),
    ).toEqual({ query: "x" });
  });
});
