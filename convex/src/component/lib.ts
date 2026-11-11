import { ConvexError, v } from "convex/values";
import { action } from "./_generated/server.js";
import { tinyfishRequest } from "./api.js";
import { fetchOptionsValidator, searchOptionsValidator } from "./validators.js";

/** The Fetch API accepts at most this many URLs per request. */
export const MAX_URLS_PER_REQUEST = 10;

export function invalid(message: string): never {
  throw new ConvexError({ code: "tinyfish_invalid_argument", message });
}

/** Search options as query string parameters. `extra` is merged in. */
export function searchParams(
  query: string,
  options?: Record<string, any>,
): Record<string, string> {
  if (!query.trim()) invalid("`query` must not be empty.");
  const { extra, ...rest } = options ?? {};
  const params: Record<string, string> = { query };
  for (const [key, value] of Object.entries({ ...rest, ...(extra ?? {}) })) {
    if (value === undefined || value === null) continue;
    params[key] = Array.isArray(value) ? value.join(",") : String(value);
  }
  return params;
}

/** Fetch options as a request body. Component-only options are left out. */
export function fetchBody(
  urls: string[],
  options?: Record<string, any>,
): Record<string, unknown> {
  const { extra, maxCharacters: _maxCharacters, ...rest } = options ?? {};
  return { urls, ...rest, ...(extra ?? {}) };
}

/** Reject a `maxCharacters` that would silently empty every page. */
export function validateMaxCharacters(options?: { maxCharacters?: number }) {
  const max = options?.maxCharacters;
  if (max !== undefined && (!Number.isInteger(max) || max < 0)) {
    invalid("`maxCharacters` must be an integer of 0 or more.");
  }
}

/** Cut a page's `text` to `maxCharacters`, flagging it when anything was cut. */
export function capText<T extends Record<string, any>>(
  result: T,
  maxCharacters?: number,
): T {
  if (
    maxCharacters === undefined ||
    typeof result.text !== "string" ||
    result.text.length <= maxCharacters
  ) {
    return result;
  }
  let end = maxCharacters;
  // Don't leave half of a surrogate pair (an emoji, say) at the cut.
  const last = result.text.charCodeAt(end - 1);
  if (end > 0 && last >= 0xd800 && last <= 0xdbff) end--;
  return { ...result, text: result.text.slice(0, end), truncated: true };
}

/**
 * Search the web and get ranked results with titles, snippets, and source
 * URLs. Use it to find pages when you don't have the URL yet. Returns the
 * TinyFish response unchanged: `{ query, results, total_results, page }`.
 */
export const search = action({
  args: {
    query: v.string(),
    options: v.optional(searchOptionsValidator),
  },
  returns: v.any(),
  handler: async (_ctx, args) => {
    return await tinyfishRequest("search", {
      params: searchParams(args.query, args.options),
    });
  },
});

/**
 * Read up to 10 known URLs and return their content: `{ results, errors }`.
 * Pages that need JavaScript are rendered.
 *
 * A URL that could not be fetched lands in `errors` with a code such as
 * `bot_blocked` or `timeout`; the other URLs still come back in `results`.
 * For more than 10 URLs, or to keep the pages in your database, start a job.
 */
export const fetch = action({
  args: {
    urls: v.array(v.string()),
    options: v.optional(fetchOptionsValidator),
  },
  returns: v.any(),
  handler: async (_ctx, args) => {
    if (args.urls.length === 0) invalid("`urls` must not be empty.");
    if (args.urls.length > MAX_URLS_PER_REQUEST) {
      invalid(
        `fetch takes at most ${MAX_URLS_PER_REQUEST} URLs per call (got ${args.urls.length}). Use startFetch to fetch more as a durable job.`,
      );
    }
    validateMaxCharacters(args.options);
    const body = await tinyfishRequest("fetch", {
      body: fetchBody(args.urls, args.options),
    });
    const results = Array.isArray(body.results) ? body.results : [];
    return {
      ...body,
      results: results.map((result: Record<string, any>) =>
        capText(result, args.options?.maxCharacters),
      ),
      errors: Array.isArray(body.errors) ? body.errors : [],
    };
  },
});
