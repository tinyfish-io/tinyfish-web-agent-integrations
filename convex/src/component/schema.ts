import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";
import {
  jobFetchOptionsValidator,
  searchOptionsValidator,
} from "./validators.js";

export const jobStatus = v.union(
  v.literal("queued"),
  v.literal("running"),
  v.literal("completed"),
  v.literal("failed"),
  v.literal("cancelled"),
);

export const jobKind = v.union(
  /** Fetch a list of URLs the app supplied. */
  v.literal("fetch"),
  /** Run a search, then fetch the top results. */
  v.literal("search_and_fetch"),
);

export const pageStatus = v.union(v.literal("completed"), v.literal("failed"));

export default defineSchema({
  jobs: defineTable({
    kind: jobKind,
    status: jobStatus,
    /** `search_and_fetch` only. */
    query: v.optional(v.string()),
    searchOptions: v.optional(searchOptionsValidator),
    /** `search_and_fetch` only: how many top results to fetch. */
    maxResults: v.optional(v.number()),
    /** True once the search step has run (always true for `fetch` jobs). */
    searched: v.boolean(),
    /** What the search returned, in rank order. `search_and_fetch` only. */
    searchResults: v.optional(v.array(v.any())),
    /** Every URL this job fetches, deduplicated, in order. */
    urls: v.array(v.string()),
    /** Index into `urls` of the next batch to fetch. */
    cursor: v.number(),
    fetchOptions: v.optional(jobFetchOptionsValidator),
    /** When false, pages are recorded without `text`. */
    storeContent: v.boolean(),
    /** URLs to fetch in total. */
    total: v.number(),
    /** URLs fetched successfully so far. */
    completed: v.number(),
    /** URLs that failed so far. Their pages carry the error code. */
    failed: v.number(),
    /** Pages whose content was cut to fit a size cap. */
    truncated: v.number(),
    error: v.optional(v.string()),
    /** App mutation to call once the job reaches a terminal state. */
    onComplete: v.optional(v.string()),
    /** Opaque app data handed back to `onComplete`. */
    context: v.optional(v.any()),
    /** Set once the terminal transition has been handled, so it happens exactly once. */
    finalized: v.boolean(),
    /**
     * Bumped on every transition. A scheduled step carries the value it was
     * scheduled with and is ignored if the job has since moved on.
     */
    step: v.number(),
    /** Times the current step has been retried. */
    attempt: v.number(),
    startedAt: v.number(),
    updatedAt: v.number(),
    completedAt: v.optional(v.number()),
  }).index("status", ["status"]),

  pages: defineTable({
    jobId: v.id("jobs"),
    /** The URL as requested. Cite this, or `final_url` after redirects. */
    url: v.string(),
    status: pageStatus,
    final_url: v.optional(v.string()),
    title: v.optional(v.string()),
    description: v.optional(v.string()),
    language: v.optional(v.string()),
    author: v.optional(v.string()),
    published_date: v.optional(v.string()),
    format: v.optional(v.string()),
    /** A string for markdown and html, a document tree for json. */
    text: v.optional(v.any()),
    links: v.optional(v.array(v.string())),
    image_links: v.optional(v.array(v.string())),
    iframe_links: v.optional(v.array(v.string())),
    highlights: v.optional(v.array(v.any())),
    latency_ms: v.optional(v.number()),
    /** Rank and snippet from the search step. `search_and_fetch` only. */
    position: v.optional(v.number()),
    snippet: v.optional(v.string()),
    /** TinyFish per-URL error code, e.g. `bot_blocked`. Failed pages only. */
    error: v.optional(v.string()),
    /** Upstream HTTP status, when the error carries one. */
    error_status: v.optional(v.number()),
    /** Remaining result fields (etag, unmatched_selectors, ...). */
    extra: v.optional(v.any()),
    /** True when content was cut to fit `maxCharacters` or Convex's 1MB document limit. */
    truncated: v.boolean(),
    fetchedAt: v.number(),
  })
    .index("jobId", ["jobId"])
    .index("jobId_url", ["jobId", "url"])
    .index("jobId_status", ["jobId", "status"]),
});
