import type { EventName } from "./charging.js";
import {
  InvalidInput,
  MAX_URLS_PER_REQUEST,
  MAX_URLS_PER_RUN,
  parseFetch,
  parseSearch,
} from "./options.js";
import type { fetchPages, search } from "./tinyfish.js";

export const MODES = ["search", "fetch"] as const;

/** What a run calls out to. Passed in so tests can replace it. */
export interface RunDeps {
  search: typeof search;
  fetchPages: typeof fetchPages;
  /** Store items in the run's dataset, charging `eventName` once per item. */
  pushData: (
    items: Record<string, unknown>[],
    eventName?: EventName,
  ) => Promise<unknown>;
  charge: (eventName: EventName) => Promise<unknown>;
  /** How many more of this event fit in the user's spending limit for the run. */
  chargeable: (eventName: EventName) => number;
}

const OVER_LIMIT =
  "The run's maximum cost is too low for this request. Raise it and run again.";

async function runSearch(
  input: Record<string, unknown>,
  deps: RunDeps,
): Promise<string> {
  const options = parseSearch(input, { source: "json", ignoreUnknown: true });
  if (deps.chargeable("search") < 1) throw new InvalidInput(OVER_LIMIT);

  const body = await deps.search(options);
  const results = Array.isArray(body.results) ? body.results : [];
  if (results.length === 0) return `No results for "${options.query}".`;

  // Stored before charging: nobody pays for results they cannot read.
  await deps.pushData(
    results.map((result: Record<string, unknown>) => ({
      query: options.query,
      ...result,
    })),
  );
  await deps.charge("search");
  return `${results.length} results for "${options.query}".`;
}

async function runFetch(
  input: Record<string, unknown>,
  deps: RunDeps,
): Promise<string> {
  const { urls, ...options } = parseFetch(input, {
    source: "json",
    ignoreUnknown: true,
    maxItems: { urls: MAX_URLS_PER_RUN },
  });
  let fetched = 0;
  let failed = 0;
  let next = 0;

  while (next < urls.length) {
    // Never fetch a page the user's spending limit would not let them keep.
    const batch = urls.slice(
      next,
      next + Math.min(MAX_URLS_PER_REQUEST, deps.chargeable("fetch")),
    );
    if (batch.length === 0) break;
    next += batch.length;

    const body = await deps.fetchPages({ ...options, urls: batch });
    // Each batch is stored and charged as it lands, so a later failure
    // leaves the earlier pages in place and never fetches them again.
    if (body.results.length > 0) await deps.pushData(body.results, "fetch");
    if (body.errors.length > 0) await deps.pushData(body.errors);
    fetched += body.results.length;
    failed += body.errors.length;
  }

  const skipped = urls.length - next;
  return [
    `Fetched ${fetched} of ${urls.length} pages`,
    failed > 0 ? `, ${failed} failed` : "",
    skipped > 0
      ? `, ${skipped} skipped because the run's maximum cost was reached`
      : "",
    ".",
  ].join("");
}

/**
 * Do the work of a run started through the input interface: one search, or
 * up to 100 URLs fetched in batches. Results go to the run's dataset. Returns
 * the status message to finish the run with.
 */
export async function runFromInput(
  input: unknown,
  deps: RunDeps,
): Promise<string> {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new InvalidInput("The input must be a JSON object.");
  }
  const record = input as Record<string, unknown>;
  const mode = record.mode ?? "search";
  if (mode === "search") {
    if (!record.query && record.urls) {
      throw new InvalidInput(
        '`query` is required in "search" mode. To read URLs, set `mode` to "fetch".',
      );
    }
    return await runSearch(record, deps);
  }
  if (mode === "fetch") return await runFetch(record, deps);
  throw new InvalidInput('`mode` must be "search" or "fetch".');
}
