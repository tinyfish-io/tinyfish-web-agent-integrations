import { ConvexError, convexToJson, v, type Infer } from "convex/values";
import { paginationOptsValidator, type FunctionHandle } from "convex/server";
import { paginator } from "convex-helpers/server/pagination";
import {
  internalAction,
  internalMutation,
  mutation,
  query,
  type MutationCtx,
} from "./_generated/server.js";
import { internal } from "./_generated/api.js";
import type { Doc, Id } from "./_generated/dataModel.js";
import schema, { jobKind, jobStatus, pageStatus } from "./schema.js";
import { requestFailure, tinyfishRequest } from "./api.js";
import {
  capText,
  fetchBody,
  invalid,
  MAX_URLS_PER_REQUEST,
  searchParams,
} from "./lib.js";
import {
  jobFetchOptionsValidator,
  searchOptionsValidator,
} from "./validators.js";

/** Most URLs one job may fetch. */
export const MAX_URLS = 500;
/** Search returns about ten results a page, and a job runs one search. */
export const MAX_SEARCH_RESULTS = 10;
const DEFAULT_SEARCH_RESULTS = 5;
const MAX_URL_LENGTH = 2_000;

/**
 * Content limits, in UTF-8 bytes, to stay inside Convex's 1MB per-document
 * limit with room to spare for the other fields.
 */
const MAX_TEXT_BYTES = 800_000;
const MAX_LIST_BYTES = 30_000;
const MAX_EXTRA_BYTES = 20_000;
/** Per stored search result; a job keeps at most ten. */
const MAX_SEARCH_RESULT_BYTES = 8_000;

/**
 * How a step that did not finish is retried. A step is one search or one fetch
 * request; both are read-only, so running one twice is safe.
 */
export const RECOVERY = {
  /** Retries of a step before its URLs are recorded as failed. */
  maxAttempts: 2,
  /** Wait before retrying a step that TinyFish rejected or timed out. */
  baseDelayMs: 15_000,
  /**
   * How long a step may run before it is presumed lost. Must exceed the
   * longest a step can take: two 150s fetch attempts plus backoff.
   */
  watchdogMs: 390_000,
};

/** Pages deleted per transaction by `deleteJob`. Pages can approach 1MB each. */
const DELETE_BATCH = 8;

const pageInput = schema.tables.pages.validator.omit("jobId", "fetchedAt");
type PageInput = Infer<typeof pageInput>;

const pageDoc = schema.tables.pages.validator.extend({
  _id: v.id("pages"),
  _creationTime: v.number(),
});

/**
 * What the app sees. Bookkeeping the app has no use for (the callback handle
 * and the step counters) stays inside.
 */
const publicJob = v.object({
  _id: v.id("jobs"),
  _creationTime: v.number(),
  kind: jobKind,
  status: jobStatus,
  query: v.optional(v.string()),
  searchResults: v.optional(v.array(v.any())),
  urls: v.array(v.string()),
  storeContent: v.boolean(),
  total: v.number(),
  completed: v.number(),
  failed: v.number(),
  truncated: v.number(),
  error: v.optional(v.string()),
  context: v.optional(v.any()),
  finalized: v.boolean(),
  startedAt: v.number(),
  updatedAt: v.number(),
  completedAt: v.optional(v.number()),
});

function toPublicJob(job: Doc<"jobs">): Infer<typeof publicJob> {
  return {
    _id: job._id,
    _creationTime: job._creationTime,
    kind: job.kind,
    status: job.status,
    query: job.query,
    searchResults: job.searchResults,
    urls: job.urls,
    storeContent: job.storeContent,
    total: job.total,
    completed: job.completed,
    failed: job.failed,
    truncated: job.truncated,
    error: job.error,
    context: job.context,
    finalized: job.finalized,
    startedAt: job.startedAt,
    updatedAt: job.updatedAt,
    completedAt: job.completedAt,
  };
}

/** Argument shape of the mutation an app passes as `onComplete`. */
export type JobCompletePayload = {
  jobId: string;
  kind: "fetch" | "search_and_fetch";
  status: "completed" | "failed" | "cancelled";
  total: number;
  completed: number;
  failed: number;
  error?: string;
  context?: any;
};

// ---------------------------------------------------------------------------
// Shaping pages for storage
// ---------------------------------------------------------------------------

const encoder = new TextEncoder();
const decoder = new TextDecoder();

function byteLength(value: unknown): number {
  return encoder.encode(
    typeof value === "string" ? value : (JSON.stringify(value) ?? ""),
  ).length;
}

/**
 * Whether Convex will accept a value TinyFish sent. Free-form values (a JSON
 * document tree, highlights, unmodelled fields) can carry object keys Convex
 * rejects, such as ones starting with `$`. Checking here means a page is
 * stored without the offending field instead of failing the whole batch.
 */
export function storable(value: unknown): boolean {
  try {
    convexToJson(value as any);
    return true;
  } catch {
    return false;
  }
}

/** The plainly named scalar fields of an object, which Convex always accepts. */
function plainFields(value: unknown): Record<string, string | number | boolean> {
  const plain: Record<string, string | number | boolean> = {};
  if (!value || typeof value !== "object") return plain;
  for (const [key, field] of Object.entries(value)) {
    if (
      /^[A-Za-z][A-Za-z0-9_]*$/.test(key) &&
      (typeof field === "string" ||
        typeof field === "boolean" ||
        (typeof field === "number" && Number.isFinite(field)))
    ) {
      plain[key] = field;
    }
  }
  return plain;
}

/**
 * A search result as it is kept on the job. Results are small in practice and
 * are kept whole. One that Convex can't hold keeps its plain fields, and one
 * that is unusually large keeps only the fields a citation needs, so ten
 * results always fit in the job document.
 */
export function searchResultForStorage(result: unknown): Record<string, unknown> {
  const kept: Record<string, unknown> =
    result && typeof result === "object" && storable(result)
      ? (result as Record<string, unknown>)
      : plainFields(result);
  if (byteLength(kept) <= MAX_SEARCH_RESULT_BYTES) return kept;
  const source = kept as Record<string, any>;
  const core: Record<string, unknown> = {};
  if (typeof source.position === "number") core.position = source.position;
  for (const [key, maxBytes] of [
    ["site_name", 200],
    ["title", 500],
    ["snippet", 2_000],
    ["url", MAX_URL_LENGTH],
    ["date", 100],
  ] as const) {
    if (typeof source[key] === "string") {
      core[key] = truncateToBytes(source[key], maxBytes);
    }
  }
  return core;
}

/** Cut a string to at most `maxBytes` of UTF-8 without splitting a character. */
export function truncateToBytes(text: string, maxBytes: number): string {
  // A UTF-16 code unit is at most 3 bytes of UTF-8.
  if (text.length * 3 <= maxBytes) return text;
  const bytes = encoder.encode(text);
  if (bytes.length <= maxBytes) return text;
  return decoder.decode(bytes.slice(0, maxBytes)).replace(/�+$/, "");
}

/** Keep leading strings of a list while they fit the byte budget. */
function clampList(
  value: unknown,
  page: { truncated: boolean },
): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const kept: string[] = [];
  let used = 0;
  for (const item of value) {
    if (typeof item !== "string") continue;
    used += byteLength(item) + 3;
    if (used > MAX_LIST_BYTES) {
      page.truncated = true;
      break;
    }
    kept.push(item);
  }
  return kept;
}

const KNOWN_RESULT_FIELDS = new Set([
  "url",
  "final_url",
  "title",
  "description",
  "language",
  "author",
  "published_date",
  "format",
  "text",
  "links",
  "image_links",
  "iframe_links",
  "highlights",
  "latency_ms",
  "truncated",
]);

type SearchMeta = { position?: number; snippet?: string };

function str(value: unknown, maxBytes = 4_000): string | undefined {
  return typeof value === "string" ? truncateToBytes(value, maxBytes) : undefined;
}

/** A successful Fetch result, shaped and clamped to fit one Convex document. */
export function toPage(
  result: Record<string, any>,
  options: { storeContent: boolean; maxCharacters?: number },
  meta: SearchMeta = {},
): PageInput {
  const capped = capText(result, options.maxCharacters);
  const page: PageInput = {
    url: String(result.url),
    status: "completed",
    truncated: capped.truncated === true,
  };
  const set = <K extends keyof PageInput>(key: K, value: PageInput[K]) => {
    if (value !== undefined) page[key] = value;
  };
  set("final_url", str(result.final_url));
  set("title", str(result.title));
  set("description", str(result.description));
  set("language", str(result.language, 100));
  set("author", str(result.author));
  set("published_date", str(result.published_date, 100));
  set("format", str(result.format, 100));
  if (typeof result.latency_ms === "number") page.latency_ms = result.latency_ms;
  set("position", meta.position);
  set("snippet", str(meta.snippet));

  if (options.storeContent && capped.text !== null && capped.text !== undefined) {
    if (typeof capped.text === "string") {
      const text = truncateToBytes(capped.text, MAX_TEXT_BYTES);
      if (text.length < capped.text.length) page.truncated = true;
      page.text = text;
    } else if (
      storable(capped.text) &&
      byteLength(capped.text) <= MAX_TEXT_BYTES
    ) {
      page.text = capped.text;
    } else {
      // A document tree can't be cut cleanly, so one that is too large or
      // that Convex can't hold is dropped whole.
      page.truncated = true;
    }
  }

  set("links", clampList(result.links, page));
  set("image_links", clampList(result.image_links, page));
  set("iframe_links", clampList(result.iframe_links, page));
  if (Array.isArray(result.highlights)) {
    if (
      storable(result.highlights) &&
      byteLength(result.highlights) <= MAX_LIST_BYTES
    ) {
      page.highlights = result.highlights;
    } else {
      page.truncated = true;
    }
  }

  const extra: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(result)) {
    if (!KNOWN_RESULT_FIELDS.has(key) && value !== null) extra[key] = value;
  }
  if (
    Object.keys(extra).length > 0 &&
    storable(extra) &&
    byteLength(extra) <= MAX_EXTRA_BYTES
  ) {
    page.extra = extra;
  }
  return page;
}

/** A URL that could not be fetched, with TinyFish's per-URL error code. */
export function toFailedPage(
  url: string,
  error: Record<string, any>,
  meta: SearchMeta = {},
): PageInput {
  const page: PageInput = {
    url,
    status: "failed",
    error: str(error.error, 500) ?? "unknown_error",
    truncated: false,
  };
  if (typeof error.status === "number") page.error_status = error.status;
  if (meta.position !== undefined) page.position = meta.position;
  const snippet = str(meta.snippet);
  if (snippet !== undefined) page.snippet = snippet;
  const { url: _url, error: _error, status: _status, ...rest } = error;
  if (
    Object.keys(rest).length > 0 &&
    storable(rest) &&
    byteLength(rest) <= MAX_EXTRA_BYTES
  ) {
    page.extra = rest;
  }
  return page;
}

// ---------------------------------------------------------------------------
// Starting jobs
// ---------------------------------------------------------------------------

function normalizeUrls(urls: string[]): string[] {
  const seen = new Set<string>();
  for (const raw of urls) {
    const url = raw.trim();
    if (url.length > MAX_URL_LENGTH) {
      invalid(`URLs may be at most ${MAX_URL_LENGTH} characters.`);
    }
    let parsed: URL;
    try {
      parsed = new URL(url);
    } catch {
      invalid(`Not a valid URL: ${url.slice(0, 200)}`);
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      invalid(`URLs must use http or https: ${url.slice(0, 200)}`);
    }
    seen.add(url);
  }
  return [...seen];
}

async function scheduleStep(
  ctx: MutationCtx,
  jobId: Id<"jobs">,
  step: number,
  delayMs = 0,
): Promise<void> {
  await ctx.scheduler.runAfter(delayMs, internal.jobs.run, { jobId, step });
  await ctx.scheduler.runAfter(
    delayMs + RECOVERY.watchdogMs,
    internal.jobs.watchdog,
    { jobId, step },
  );
}

const jobCallbackArgs = {
  /** Keep page content, not just URLs and metadata. Defaults to true. */
  storeContent: v.optional(v.boolean()),
  /** Function handle of an app mutation to run once the job is terminal. */
  onComplete: v.optional(v.string()),
  /** Opaque data handed back to `onComplete`. */
  context: v.optional(v.any()),
};

/**
 * Fetch a list of URLs as a durable job and return its id right away.
 * Subscribe to `get` for progress and `listPages` for pages as they land.
 */
export const startFetch = mutation({
  args: {
    urls: v.array(v.string()),
    options: v.optional(jobFetchOptionsValidator),
    ...jobCallbackArgs,
  },
  returns: v.id("jobs"),
  handler: async (ctx, args) => {
    const urls = normalizeUrls(args.urls);
    if (urls.length === 0) invalid("`urls` must not be empty.");
    if (urls.length > MAX_URLS) {
      invalid(`A job fetches at most ${MAX_URLS} URLs (got ${urls.length}).`);
    }
    const now = Date.now();
    const jobId = await ctx.db.insert("jobs", {
      kind: "fetch",
      status: "queued",
      searched: true,
      urls,
      cursor: 0,
      fetchOptions: args.options,
      storeContent: args.storeContent ?? true,
      total: urls.length,
      completed: 0,
      failed: 0,
      truncated: 0,
      onComplete: args.onComplete,
      context: args.context,
      finalized: false,
      step: 0,
      attempt: 0,
      startedAt: now,
      updatedAt: now,
    });
    await scheduleStep(ctx, jobId, 0);
    return jobId;
  },
});

/**
 * Search, then fetch the top results, as a durable job. The search results
 * land on the job as `searchResults`; each fetched page keeps its search
 * `position` and `snippet` next to its content.
 */
export const startSearchAndFetch = mutation({
  args: {
    query: v.string(),
    searchOptions: v.optional(searchOptionsValidator),
    /** How many top results to fetch, 1 to 10. Defaults to 5. */
    maxResults: v.optional(v.number()),
    fetchOptions: v.optional(jobFetchOptionsValidator),
    ...jobCallbackArgs,
  },
  returns: v.id("jobs"),
  handler: async (ctx, args) => {
    if (!args.query.trim()) invalid("`query` must not be empty.");
    const maxResults = args.maxResults ?? DEFAULT_SEARCH_RESULTS;
    if (
      !Number.isInteger(maxResults) ||
      maxResults < 1 ||
      maxResults > MAX_SEARCH_RESULTS
    ) {
      invalid(
        `\`maxResults\` must be an integer from 1 to ${MAX_SEARCH_RESULTS}.`,
      );
    }
    const now = Date.now();
    const jobId = await ctx.db.insert("jobs", {
      kind: "search_and_fetch",
      status: "queued",
      query: args.query,
      searchOptions: args.searchOptions,
      maxResults,
      searched: false,
      urls: [],
      cursor: 0,
      fetchOptions: args.fetchOptions,
      storeContent: args.storeContent ?? true,
      total: 0,
      completed: 0,
      failed: 0,
      truncated: 0,
      onComplete: args.onComplete,
      context: args.context,
      finalized: false,
      step: 0,
      attempt: 0,
      startedAt: now,
      updatedAt: now,
    });
    await scheduleStep(ctx, jobId, 0);
    return jobId;
  },
});

// ---------------------------------------------------------------------------
// Reading jobs and pages
// ---------------------------------------------------------------------------

/** Status and progress of a job. Reactive: subscribe to it from a query. */
export const get = query({
  args: { jobId: v.id("jobs") },
  returns: v.union(publicJob, v.null()),
  handler: async (ctx, args) => {
    const job = await ctx.db.get(args.jobId);
    return job ? toPublicJob(job) : null;
  },
});

/** Recent jobs, newest first. */
export const list = query({
  args: {
    status: v.optional(jobStatus),
    limit: v.optional(v.number()),
  },
  returns: v.array(publicJob),
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(args.limit ?? 50, 1), 200);
    const status = args.status;
    const jobs = status
      ? await ctx.db
          .query("jobs")
          .withIndex("status", (q) => q.eq("status", status))
          .order("desc")
          .take(limit)
      : await ctx.db.query("jobs").order("desc").take(limit);
    return jobs.map(toPublicJob);
  },
});

/**
 * Pages of a job, in the order they were fetched. Works with React's
 * `usePaginatedQuery`. Pages can be large, so keep `numItems` small when
 * content is stored.
 */
export const listPages = query({
  args: {
    jobId: v.id("jobs"),
    /** Only pages that were fetched (`completed`) or only those that failed. */
    status: v.optional(pageStatus),
    paginationOpts: paginationOptsValidator,
  },
  returns: v.any(),
  handler: async (ctx, args) => {
    const pages = paginator(ctx.db, schema).query("pages");
    const status = args.status;
    const indexed = status
      ? pages.withIndex("jobId_status", (q) =>
          q.eq("jobId", args.jobId).eq("status", status),
        )
      : pages.withIndex("jobId", (q) => q.eq("jobId", args.jobId));
    return await indexed.paginate(args.paginationOpts);
  },
});

/** One page of a job by its requested URL. */
export const getPage = query({
  args: { jobId: v.id("jobs"), url: v.string() },
  returns: v.union(pageDoc, v.null()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("pages")
      .withIndex("jobId_url", (q) =>
        q.eq("jobId", args.jobId).eq("url", args.url),
      )
      .first();
  },
});

// ---------------------------------------------------------------------------
// Cancelling and deleting
// ---------------------------------------------------------------------------

/** Stop a job. Pages already fetched are kept. Returns false if it had ended. */
export const cancel = mutation({
  args: { jobId: v.id("jobs") },
  returns: v.boolean(),
  handler: async (ctx, args) => {
    const job = await ctx.db.get(args.jobId);
    if (!job || job.finalized) return false;
    await finalize(ctx, job, "cancelled");
    return true;
  },
});

/** Delete up to one batch of a job's pages. Returns true when none remain. */
async function purgePages(ctx: MutationCtx, jobId: Id<"jobs">): Promise<boolean> {
  const pages = await ctx.db
    .query("pages")
    .withIndex("jobId", (q) => q.eq("jobId", jobId))
    .take(DELETE_BATCH);
  for (const page of pages) await ctx.db.delete(page._id);
  return pages.length < DELETE_BATCH;
}

/**
 * Delete a job and its pages. A running job is cancelled first. Large jobs
 * finish deleting in the background.
 */
export const deleteJob = mutation({
  args: { jobId: v.id("jobs") },
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await ctx.db.get(args.jobId);
    if (!job) return null;
    if (!job.finalized) await finalize(ctx, job, "cancelled");
    if (await purgePages(ctx, args.jobId)) {
      await ctx.db.delete(args.jobId);
    } else {
      await ctx.scheduler.runAfter(0, internal.jobs.purge, args);
    }
    return null;
  },
});

export const purge = internalMutation({
  args: { jobId: v.id("jobs") },
  returns: v.null(),
  handler: async (ctx, args) => {
    if (await purgePages(ctx, args.jobId)) {
      const job = await ctx.db.get(args.jobId);
      if (job) await ctx.db.delete(args.jobId);
    } else {
      await ctx.scheduler.runAfter(0, internal.jobs.purge, args);
    }
    return null;
  },
});

// ---------------------------------------------------------------------------
// Running a job, one step at a time
// ---------------------------------------------------------------------------

const stepArgs = { jobId: v.id("jobs"), step: v.number() };

/** The job, if `step` is still the step it is waiting on. */
async function currentJob(
  ctx: MutationCtx,
  args: { jobId: Id<"jobs">; step: number },
): Promise<Doc<"jobs"> | null> {
  const job = await ctx.db.get(args.jobId);
  if (!job || job.finalized || job.step !== args.step) return null;
  return job;
}

function batchOf(job: Doc<"jobs">): string[] {
  return job.urls.slice(job.cursor, job.cursor + MAX_URLS_PER_REQUEST);
}

/** Search rank and snippet for a URL, from the job's search step. */
function searchMeta(job: Doc<"jobs">, url: string): SearchMeta {
  const result = job.searchResults?.find((entry) => entry?.url === url);
  if (!result) return {};
  return {
    position: typeof result.position === "number" ? result.position : undefined,
    snippet: typeof result.snippet === "string" ? result.snippet : undefined,
  };
}

/** Claim a step: mark the job running and hand the action what it needs. */
export const begin = internalMutation({
  args: stepArgs,
  handler: async (ctx, args) => {
    const job = await currentJob(ctx, args);
    if (!job) return null;
    if (job.status === "queued") {
      await ctx.db.patch(job._id, { status: "running", updatedAt: Date.now() });
    }
    const batch = batchOf(job);
    return {
      searched: job.searched,
      query: job.query,
      searchOptions: job.searchOptions,
      maxResults: job.maxResults,
      batch,
      meta: batch.map((url) => searchMeta(job, url)),
      fetchOptions: job.fetchOptions,
      storeContent: job.storeContent,
    };
  },
});

/** Client errors that would repeat on every request, so the job stops. */
function isFatal(status: number): boolean {
  return (
    status >= 400 && status < 500 && ![408, 425, 429].includes(status)
  );
}

/**
 * The component's own errors that no retry can fix: a missing API key, or
 * arguments that are invalid before any request is made.
 */
function configError(error: unknown): string | null {
  if (!(error instanceof ConvexError)) return null;
  const data = error.data as { code?: unknown; message?: unknown } | undefined;
  if (
    data?.code !== "tinyfish_missing_api_key" &&
    data?.code !== "tinyfish_invalid_argument"
  ) {
    return null;
  }
  return typeof data.message === "string" ? data.message : String(data.code);
}

function errorMessage(error: unknown): string {
  const failure = requestFailure(error);
  if (failure) return failure.message;
  const config = configError(error);
  if (config) return config;
  return error instanceof Error ? error.message : String(error);
}

type Matched = { result?: Record<string, any>; error?: Record<string, any> };

/**
 * Match a Fetch response back to the URLs that were requested, one outcome
 * per URL. Fetch documents `results[].url` and `errors[].url` as the URL
 * exactly as requested, so exact matches are the normal case and are settled
 * first. A URL still unmatched may then claim an unclaimed entry whose
 * normalized form (host lowercased, default port dropped, bare origin given
 * its slash) is the same, so a fetched page is never recorded as missing over
 * a spelling difference. Each response entry is given to at most one URL.
 */
export function matchResponse(
  batch: string[],
  body: { results?: unknown; errors?: unknown },
): Matched[] {
  const entriesOf = (value: unknown): Record<string, any>[] =>
    (Array.isArray(value) ? value : []).filter(
      (entry) => typeof entry?.url === "string",
    );
  const results = entriesOf(body.results);
  const errors = entriesOf(body.errors);
  const claimed = new Set<Record<string, any>>();
  const claim = (
    entries: Record<string, any>[],
    matches: (entryUrl: string) => boolean,
  ) => {
    const entry = entries.find((e) => !claimed.has(e) && matches(e.url));
    if (entry) claimed.add(entry);
    return entry;
  };

  const matched: Matched[] = batch.map((url) => {
    const result = claim(results, (entryUrl) => entryUrl === url);
    if (result) return { result };
    const error = claim(errors, (entryUrl) => entryUrl === url);
    return error ? { error } : {};
  });
  batch.forEach((url, index) => {
    if (matched[index].result || matched[index].error) return;
    const normalized = normalizeUrl(url);
    const same = (entryUrl: string) => normalizeUrl(entryUrl) === normalized;
    const result = claim(results, same);
    if (result) matched[index] = { result };
    else {
      const error = claim(errors, same);
      if (error) matched[index] = { error };
    }
  });
  return matched;
}

function normalizeUrl(url: string): string {
  try {
    return new URL(url).href;
  } catch {
    return url;
  }
}

export const run = internalAction({
  args: stepArgs,
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await ctx.runMutation(internal.jobs.begin, args);
    if (!job) return null;

    // 1. Ask TinyFish. A failure here means nothing was returned, so the step
    //    can be retried.
    let searchResults: unknown[] | undefined;
    let pages: PageInput[] | undefined;
    try {
      if (!job.searched) {
        const body = await tinyfishRequest("search", {
          params: searchParams(job.query ?? "", job.searchOptions),
          retries: 1,
        });
        const results: unknown[] = Array.isArray(body.results)
          ? body.results
          : [];
        searchResults = results
          .slice(0, job.maxResults ?? DEFAULT_SEARCH_RESULTS)
          .map(searchResultForStorage);
      } else {
        const body = await tinyfishRequest("fetch", {
          body: fetchBody(job.batch, job.fetchOptions),
          retries: 1,
        });
        const matched = matchResponse(job.batch, body);
        pages = job.batch.map((url, index) => {
          const { result, error } = matched[index];
          if (result) {
            return toPage(
              // Store the page under the URL the app asked for.
              { ...result, url },
              {
                storeContent: job.storeContent,
                maxCharacters: job.fetchOptions?.maxCharacters,
              },
              job.meta[index],
            );
          }
          return toFailedPage(
            url,
            error ?? { error: "missing_from_response" },
            job.meta[index],
          );
        });
      }
    } catch (error) {
      const failure = requestFailure(error);
      await ctx.runMutation(internal.jobs.stepFailed, {
        ...args,
        error: errorMessage(error).slice(0, 1_000),
        status: failure?.status,
        fatal: failure
          ? isFatal(failure.status)
          : configError(error) !== null,
      });
      return null;
    }

    // 2. Store what came back. A failure here is not TinyFish's: the request
    //    succeeded and counted against the allowance, so asking again would
    //    only bill it twice. Stop the job and say why.
    try {
      if (searchResults) {
        await ctx.runMutation(internal.jobs.recordSearch, {
          ...args,
          results: searchResults,
        });
      } else if (pages) {
        await ctx.runMutation(internal.jobs.recordBatch, { ...args, pages });
      }
    } catch (error) {
      await ctx.runMutation(internal.jobs.stepFailed, {
        ...args,
        error: `TinyFish responded, but the results could not be stored: ${errorMessage(error)}`.slice(
          0,
          1_000,
        ),
        fatal: true,
      });
    }
    return null;
  },
});

/** Store the search step's results and move on to fetching them. */
export const recordSearch = internalMutation({
  args: { ...stepArgs, results: v.array(v.any()) },
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await currentJob(ctx, args);
    if (!job || job.searched) return null;
    const urls: string[] = [];
    for (const result of args.results) {
      const url = result?.url;
      if (
        typeof url === "string" &&
        url.length <= MAX_URL_LENGTH &&
        !urls.includes(url)
      ) {
        urls.push(url);
      }
    }
    const next = {
      searched: true,
      searchResults: args.results,
      urls,
      total: urls.length,
      step: job.step + 1,
      attempt: 0,
      updatedAt: Date.now(),
    };
    await ctx.db.patch(job._id, next);
    if (urls.length === 0) {
      await finalize(ctx, { ...job, ...next }, "completed");
    } else {
      await scheduleStep(ctx, job._id, next.step);
    }
    return null;
  },
});

/** Insert a batch of pages, advance the cursor, and continue or finish. */
async function commitBatch(
  ctx: MutationCtx,
  job: Doc<"jobs">,
  pages: PageInput[],
): Promise<void> {
  const now = Date.now();
  let completed = 0;
  let failed = 0;
  let truncated = 0;
  for (const page of pages) {
    await ctx.db.insert("pages", { ...page, jobId: job._id, fetchedAt: now });
    if (page.status === "completed") completed++;
    else failed++;
    if (page.truncated) truncated++;
  }
  const next = {
    cursor: job.cursor + batchOf(job).length,
    completed: job.completed + completed,
    failed: job.failed + failed,
    truncated: job.truncated + truncated,
    step: job.step + 1,
    attempt: 0,
    updatedAt: now,
  };
  await ctx.db.patch(job._id, next);
  const updated = { ...job, ...next };
  if (updated.cursor < updated.total) {
    await scheduleStep(ctx, job._id, updated.step);
  } else if (updated.completed === 0 && updated.total > 0) {
    await finalize(
      ctx,
      updated,
      "failed",
      `None of the ${updated.total} URLs could be fetched. Each page's \`error\` says why.`,
    );
  } else {
    await finalize(ctx, updated, "completed");
  }
}

export const recordBatch = internalMutation({
  args: { ...stepArgs, pages: v.array(pageInput) },
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await currentJob(ctx, args);
    if (job) await commitBatch(ctx, job, args.pages);
    return null;
  },
});

/**
 * Retry the current step, or give up on it once it has been retried enough:
 * a search that can't run fails the job, while a batch that can't be fetched
 * is recorded as failed pages so the rest of the job still completes.
 */
async function recover(
  ctx: MutationCtx,
  job: Doc<"jobs">,
  reason: { error: string; status?: number },
): Promise<void> {
  if (job.attempt < RECOVERY.maxAttempts) {
    const step = job.step + 1;
    await ctx.db.patch(job._id, {
      step,
      attempt: job.attempt + 1,
      updatedAt: Date.now(),
    });
    await scheduleStep(
      ctx,
      job._id,
      step,
      RECOVERY.baseDelayMs * 2 ** job.attempt,
    );
    return;
  }
  if (!job.searched) {
    await finalize(ctx, job, "failed", reason.error);
    return;
  }
  await commitBatch(
    ctx,
    job,
    batchOf(job).map((url) =>
      toFailedPage(
        url,
        { error: "request_failed", status: reason.status || undefined },
        searchMeta(job, url),
      ),
    ),
  );
}

export const stepFailed = internalMutation({
  args: {
    ...stepArgs,
    error: v.string(),
    status: v.optional(v.number()),
    fatal: v.boolean(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await currentJob(ctx, args);
    if (!job) return null;
    if (args.fatal) await finalize(ctx, job, "failed", args.error);
    else await recover(ctx, job, args);
    return null;
  },
});

/** Catches a step whose action never reported back, e.g. across a deploy. */
export const watchdog = internalMutation({
  args: stepArgs,
  returns: v.null(),
  handler: async (ctx, args) => {
    const job = await currentJob(ctx, args);
    if (job) {
      await recover(ctx, job, {
        error: "A step did not finish in time and its retries ran out.",
      });
    }
    return null;
  },
});

/** Terminal transition, exactly once, then the app's `onComplete` callback. */
async function finalize(
  ctx: MutationCtx,
  job: Doc<"jobs">,
  status: "completed" | "failed" | "cancelled",
  error?: string,
): Promise<void> {
  if (job.finalized) return;
  const now = Date.now();
  await ctx.db.patch(job._id, {
    status,
    finalized: true,
    completedAt: now,
    updatedAt: now,
    ...(error ? { error } : {}),
  });
  if (!job.onComplete) return;
  const handle = job.onComplete as FunctionHandle<"mutation", JobCompletePayload>;
  await ctx.scheduler.runAfter(0, handle, {
    jobId: job._id as string,
    kind: job.kind,
    status,
    total: job.total,
    completed: job.completed,
    failed: job.failed,
    error: error ?? job.error,
    context: job.context,
  });
}
