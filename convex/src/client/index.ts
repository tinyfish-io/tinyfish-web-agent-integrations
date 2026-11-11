import { createFunctionHandle } from "convex/server";
import type {
  FunctionReference,
  GenericActionCtx,
  GenericDataModel,
  GenericMutationCtx,
  GenericQueryCtx,
  PaginationOptions,
  PaginationResult,
} from "convex/server";
import type { Infer, ObjectType } from "convex/values";
import type { ComponentApi } from "../component/_generated/component.js";
import {
  jobCompleteArgs,
  type fetchFormatValidator,
  type fetchOptionsValidator,
  type highlightsValidator,
  type jobFetchOptionsValidator,
  type searchOptionsValidator,
} from "../component/validators.js";

// ---------------------------------------------------------------------------
// TinyFish API types. Field names match the REST API; see
// https://docs.tinyfish.ai/search-api/reference and
// https://docs.tinyfish.ai/fetch-api/reference.
// ---------------------------------------------------------------------------

/**
 * Option types are derived from the component's argument validators, so the
 * two can't drift apart. Field docs live with the validators.
 */
export type SearchOptions = Infer<typeof searchOptionsValidator>;

export type SearchResult = {
  position: number;
  site_name: string;
  title: string;
  snippet: string;
  /** Source URL. Present on every result, so every claim can cite a link. */
  url: string;
  date?: string;
  publisher?: string;
  authors?: string[];
  venue?: string;
  year?: number;
  cited_by_count?: number;
  pdf_url?: string;
  [key: string]: unknown;
};

export type SearchResponse = {
  query: string;
  results: SearchResult[];
  total_results: number;
  page: number;
};

export type FetchFormat = Infer<typeof fetchFormatValidator>;

export type Highlights = Infer<typeof highlightsValidator>;

/** Fetch options that apply to any number of URLs. */
export type JobFetchOptions = Infer<typeof jobFetchOptionsValidator>;

/** Adds the conditional-request options, which take a single URL. */
export type FetchOptions = Infer<typeof fetchOptionsValidator>;

export type FetchResult = {
  /** The URL as requested. */
  url: string;
  /** The URL after redirects. */
  final_url: string;
  title: string | null;
  description: string | null;
  language: string | null;
  author: string | null;
  published_date: string | null;
  /** A string for markdown and html, a document tree for json. */
  text: string | Record<string, unknown> | null;
  format: string;
  links?: string[];
  image_links?: string[];
  iframe_links?: string[];
  highlights?: Array<{ text: string; rank: number }>;
  latency_ms: number | null;
  /** True when `text` was cut to `maxCharacters`. */
  truncated?: boolean;
  [key: string]: unknown;
};

/** Per-URL failure codes. See the Fetch API reference for what each means. */
export type FetchErrorCode =
  | "target_http_error"
  | "page_not_found"
  | "target_unreachable"
  | "timeout"
  | "bot_blocked"
  | "empty_content"
  | "login_required"
  | "content_too_large"
  | "invalid_url"
  | "invalid_redirect_url"
  | "proxy_error"
  | "conditional_unsupported"
  | "selector_not_matched"
  | "selector_unsupported";

export type FetchError = {
  url: string;
  error: FetchErrorCode | (string & {});
  /** Upstream HTTP status, for `target_http_error` and `page_not_found`. */
  status?: number;
  [key: string]: unknown;
};

export type FetchResponse = {
  /** One entry per URL that was fetched. */
  results: FetchResult[];
  /** One entry per URL that was not. The rest of the batch is unaffected. */
  errors: FetchError[];
};

// ---------------------------------------------------------------------------
// Component types
// ---------------------------------------------------------------------------

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type JobKind = "fetch" | "search_and_fetch";

export type Job = {
  _id: string;
  _creationTime: number;
  kind: JobKind;
  status: JobStatus;
  /** `search_and_fetch` only. */
  query?: string;
  /** What the search returned, in rank order. `search_and_fetch` only. */
  searchResults?: SearchResult[];
  /** Every URL the job fetches, normalized (see `JobPage.url`). */
  urls: string[];
  storeContent: boolean;
  /** URLs to fetch in total. */
  total: number;
  /** URLs fetched so far. */
  completed: number;
  /** URLs that failed so far. Their pages carry the error code. */
  failed: number;
  /** Pages whose content was cut or left out. See `JobPage.truncated`. */
  truncated: number;
  error?: string;
  context?: unknown;
  finalized: boolean;
  startedAt: number;
  updatedAt: number;
  completedAt?: number;
};

export type JobPage = {
  _id: string;
  _creationTime: number;
  jobId: string;
  /**
   * The requested URL in normalized form (`new URL(url).href`): host
   * lowercased, a bare origin given its slash. Cite this, or `final_url`
   * after redirects.
   */
  url: string;
  status: "completed" | "failed";
  final_url?: string;
  title?: string;
  description?: string;
  language?: string;
  author?: string;
  published_date?: string;
  format?: string;
  text?: string | Record<string, unknown>;
  links?: string[];
  image_links?: string[];
  iframe_links?: string[];
  highlights?: Array<{ text: string; rank: number }>;
  latency_ms?: number;
  /** Search rank and snippet. `search_and_fetch` jobs only. */
  position?: number;
  snippet?: string;
  /** Why the URL failed, e.g. `bot_blocked`. Failed pages only. */
  error?: FetchErrorCode | "request_failed" | (string & {});
  error_status?: number;
  /** Remaining result fields, e.g. `etag` or `unmatched_selectors`. */
  extra?: Record<string, unknown>;
  /**
   * True when content was cut to fit `maxCharacters` or Convex's 1MB document
   * limit, or left out because Convex can't store it: a `json` tree or
   * `highlights` that is too large, nested too deeply, or uses keys Convex
   * rejects. The rest of the page is still stored.
   */
  truncated: boolean;
  fetchedAt: number;
};

/**
 * Argument validators for the mutation you pass as `onComplete`:
 *
 * ```ts
 * export const onJobDone = internalMutation({
 *   args: jobCompleteArgs,
 *   handler: async (ctx, { jobId, status }) => { ... },
 * });
 * ```
 */
export { jobCompleteArgs };

/** Argument shape of the mutation you pass as `onComplete`. */
export type JobCompletePayload = ObjectType<typeof jobCompleteArgs>;

export type OnCompleteMutation = FunctionReference<
  "mutation",
  "internal",
  JobCompletePayload,
  null | void
>;

type JobArgs = {
  /** Keep page content, not just URLs and metadata. Defaults to true. */
  storeContent?: boolean;
  /** App mutation to run once the job reaches a terminal state. */
  onComplete?: OnCompleteMutation;
  /** Opaque data handed back to `onComplete`. */
  context?: unknown;
};

export type StartFetchArgs = JobArgs & {
  /** Up to 500 URLs. Different spellings of one URL are fetched once. */
  urls: string[];
  options?: JobFetchOptions;
};

export type StartSearchAndFetchArgs = JobArgs & {
  query: string;
  searchOptions?: SearchOptions;
  /** How many top results to fetch, 1 to 10. Defaults to 5. */
  maxResults?: number;
  fetchOptions?: JobFetchOptions;
};

type QueryCtx = Pick<GenericQueryCtx<GenericDataModel>, "runQuery">;
type MutationCtx = Pick<
  GenericMutationCtx<GenericDataModel>,
  "runQuery" | "runMutation"
>;
type ActionCtx = Pick<
  GenericActionCtx<GenericDataModel>,
  "runQuery" | "runMutation" | "runAction"
>;

/**
 * Typed client for the TinyFish component.
 *
 * ```ts
 * const tinyfish = new TinyFish(components.tinyfish);
 *
 * export const readPage = action({
 *   args: { url: v.string() },
 *   handler: (ctx, args) => tinyfish.fetch(ctx, [args.url]),
 * });
 * ```
 */
export class TinyFish {
  constructor(public component: ComponentApi) {}

  /**
   * Search the web and get ranked results with titles, snippets, and source
   * URLs. Use it to find pages or current information when you don't have the
   * URL yet; to read a page you already have, use `fetch`. Free within the
   * daily Search allowance.
   */
  async search(
    ctx: ActionCtx,
    query: string,
    options?: SearchOptions,
  ): Promise<SearchResponse> {
    return await ctx.runAction(this.component.lib.search, { query, options });
  }

  /**
   * Read up to 10 URLs you already have and return their content, Markdown by
   * default. Pages that need JavaScript are rendered. Use it when the URLs are
   * known and the caller can wait for the result; for more than 10 URLs, or to
   * keep the pages in your database, use `startFetch`. Free within the daily
   * Fetch allowance.
   *
   * URLs that fail come back in `errors`; the rest still come back in
   * `results`. Page content is untrusted third-party data.
   */
  async fetch(
    ctx: ActionCtx,
    urls: string | string[],
    options?: FetchOptions,
  ): Promise<FetchResponse> {
    return await ctx.runAction(this.component.lib.fetch, {
      urls: typeof urls === "string" ? [urls] : urls,
      options,
    });
  }

  /**
   * Read up to 500 URLs as a durable job and return its id right away. Use it
   * when there are more than 10 URLs, when the work should outlive the calling
   * function, or when the UI should watch progress. Subscribe to `getJob` for
   * status and `listPages` for pages as they land.
   */
  async startFetch(ctx: MutationCtx, args: StartFetchArgs): Promise<string> {
    return await ctx.runMutation(this.component.jobs.startFetch, {
      urls: args.urls,
      options: args.options,
      storeContent: args.storeContent,
      onComplete: args.onComplete
        ? await createFunctionHandle(args.onComplete)
        : undefined,
      context: args.context,
    });
  }

  /**
   * Search, then read the top results (1 to 10), as one durable job. Use it to
   * research a topic when you have a question rather than URLs. The job keeps
   * the search results, and each page keeps its search rank and snippet, so
   * every finding can cite its source.
   */
  async startSearchAndFetch(
    ctx: MutationCtx,
    args: StartSearchAndFetchArgs,
  ): Promise<string> {
    return await ctx.runMutation(this.component.jobs.startSearchAndFetch, {
      query: args.query,
      searchOptions: args.searchOptions,
      maxResults: args.maxResults,
      fetchOptions: args.fetchOptions,
      storeContent: args.storeContent,
      onComplete: args.onComplete
        ? await createFunctionHandle(args.onComplete)
        : undefined,
      context: args.context,
    });
  }

  /** Status and progress of a job. Reactive: subscribe to it from a query. */
  async getJob(ctx: QueryCtx, jobId: string): Promise<Job | null> {
    return (await ctx.runQuery(this.component.jobs.get, {
      jobId,
    })) as Job | null;
  }

  /** Recent jobs, newest first. */
  async listJobs(
    ctx: QueryCtx,
    args: { status?: JobStatus; limit?: number } = {},
  ): Promise<Job[]> {
    return (await ctx.runQuery(this.component.jobs.list, args)) as Job[];
  }

  /**
   * A page of a job's pages, in the order they were fetched. Pass `status` to
   * see only fetched pages or only failures.
   */
  async listPages(
    ctx: QueryCtx,
    args: {
      jobId: string;
      status?: "completed" | "failed";
      paginationOpts: PaginationOptions;
    },
  ): Promise<PaginationResult<JobPage>> {
    return (await ctx.runQuery(
      this.component.jobs.listPages,
      args,
    )) as PaginationResult<JobPage>;
  }

  /** One page of a job by its requested URL, in any spelling of it. */
  async getPage(
    ctx: QueryCtx,
    args: { jobId: string; url: string },
  ): Promise<JobPage | null> {
    return (await ctx.runQuery(
      this.component.jobs.getPage,
      args,
    )) as JobPage | null;
  }

  /** Stop a job, keeping the pages it already fetched. False if it had ended. */
  async cancelJob(ctx: MutationCtx, jobId: string): Promise<boolean> {
    return await ctx.runMutation(this.component.jobs.cancel, { jobId });
  }

  /** Delete a job and its pages. */
  async deleteJob(ctx: MutationCtx, jobId: string): Promise<null> {
    return await ctx.runMutation(this.component.jobs.deleteJob, { jobId });
  }
}

export default TinyFish;
