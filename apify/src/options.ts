/**
 * The one definition of what Search and Fetch accept.
 *
 * Request parsing, the Actor input schema, and the OpenAPI document are all
 * built from these tables (see `scripts/generate-schemas.ts`), so a field's
 * name, type, limits, and description cannot drift between them.
 *
 * Field names match the TinyFish REST APIs exactly (snake_case), so the
 * TinyFish docs are the reference for behavior:
 * https://docs.tinyfish.ai/search-api/reference and
 * https://docs.tinyfish.ai/fetch-api/reference. Rules that span several
 * fields (date bounds, `research_paper` filters) are left to the API, whose
 * 400 message is passed through.
 */

/** The Fetch API accepts at most this many URLs per request. */
export const MAX_URLS_PER_REQUEST = 10;

/** A run started through the input interface fetches at most this many URLs. */
export const MAX_URLS_PER_RUN = 100;

export interface Field {
  name: string;
  type: "string" | "integer" | "boolean" | "list";
  title: string;
  description: string;
  required?: boolean;
  enum?: readonly string[];
  /** Integers only. */
  minimum?: number;
  /** Integers only. */
  maximum?: number;
  /** Lists only. */
  maxItems?: number;
  /**
   * A list TinyFish takes as one comma-separated string. A query string or
   * JSON body may send it that way too.
   */
  commaSeparated?: boolean;
  example: string | number | boolean | readonly string[];
}

const purpose = {
  name: "purpose",
  type: "string",
  title: "Purpose",
  description:
    "Why you are making this request: the goal the results will be used for. Optional, and improves result quality.",
  example: "Compare pricing tiers across vendors for a procurement report",
} as const satisfies Field;

export const SEARCH_FIELDS = [
  {
    name: "query",
    type: "string",
    title: "Search query",
    description: "What to search the web for.",
    required: true,
    example: "web automation tools",
  },
  purpose,
  {
    name: "location",
    type: "string",
    title: "Location",
    description:
      'Country code for geo-targeted results, such as "US", "GB" or "DE". Resolved from `language` when omitted.',
    example: "US",
  },
  {
    name: "language",
    type: "string",
    title: "Language",
    description:
      'Language code for results, such as "en", "fr" or "de". Resolved from `location` when omitted.',
    example: "en",
  },
  {
    name: "include_domains",
    type: "list",
    title: "Include domains",
    description: "Only return results from these domains.",
    commaSeparated: true,
    example: ["github.com", "arxiv.org"],
  },
  {
    name: "exclude_domains",
    type: "list",
    title: "Exclude domains",
    description: "Never return results from these domains.",
    commaSeparated: true,
    example: ["pinterest.com", "quora.com"],
  },
  {
    name: "domain_type",
    type: "string",
    title: "Search type",
    description:
      '"web" for standard results, "news" for news articles with publisher and date, "research_paper" for academic papers with authors, venue and citation count. Defaults to "web".',
    enum: ["web", "news", "research_paper"],
    example: "web",
  },
  {
    name: "recency_minutes",
    type: "integer",
    title: "Recency (minutes)",
    description:
      "Only return results from the past N minutes, such as 60 for the last hour. Cannot be combined with `after_date` or `before_date`.",
    minimum: 1,
    maximum: 5_256_000,
    example: 1440,
  },
  {
    name: "after_date",
    type: "string",
    title: "After date",
    description: "Only return results after this date, as YYYY-MM-DD.",
    example: "2026-06-01",
  },
  {
    name: "before_date",
    type: "string",
    title: "Before date",
    description: "Only return results before this date, as YYYY-MM-DD.",
    example: "2026-06-18",
  },
  {
    name: "pub_year_min",
    type: "integer",
    title: "Earliest publication year",
    description:
      'Only return papers published in or after this year. Only for the "research_paper" search type.',
    minimum: 0,
    maximum: 9999,
    example: 2019,
  },
  {
    name: "pub_year_max",
    type: "integer",
    title: "Latest publication year",
    description:
      'Only return papers published in or before this year. Only for the "research_paper" search type.',
    minimum: 0,
    maximum: 9999,
    example: 2022,
  },
  {
    name: "page",
    type: "integer",
    title: "Page",
    description: "Page of results to return, starting from 0.",
    minimum: 0,
    maximum: 10,
    example: 0,
  },
] as const satisfies readonly Field[];

export const FETCH_FIELDS = [
  {
    name: "urls",
    type: "list",
    title: "URLs",
    description:
      "Pages to read. Each must be an http or https URL. Pages that need JavaScript are rendered.",
    required: true,
    maxItems: MAX_URLS_PER_REQUEST,
    example: ["https://www.tinyfish.ai/"],
  },
  purpose,
  {
    name: "format",
    type: "string",
    title: "Format",
    description:
      'Format of each page\'s `text`: "markdown" (recommended for LLMs), "html" for cleaned semantic HTML, or "json" for a structured document tree. Defaults to "markdown".',
    enum: ["markdown", "html", "json"],
    example: "markdown",
  },
  {
    name: "links",
    type: "boolean",
    title: "Include links",
    description: "Also return every link (`<a href>`) found on each page.",
    example: false,
  },
  {
    name: "image_links",
    type: "boolean",
    title: "Include image links",
    description: "Also return every image URL (`<img src>`) found on each page.",
    example: false,
  },
  {
    name: "iframe_links",
    type: "boolean",
    title: "Include iframe links",
    description:
      "Also return the `src` of every `<iframe>` on each page. Useful when a page embeds its main content in a frame: fetch the returned URL to read it.",
    example: false,
  },
  {
    name: "ttl",
    type: "integer",
    title: "Cache tolerance (seconds)",
    description:
      "Accept a cached copy of a page younger than this many seconds. 0 forces a live fetch. Omit to accept any cached copy.",
    minimum: 0,
    example: 3600,
  },
  {
    name: "per_url_timeout_ms",
    type: "integer",
    title: "Timeout per URL (ms)",
    description:
      "Time allowed for each URL, in milliseconds. A URL that takes longer comes back as a `timeout` error while the others still complete.",
    minimum: 1,
    maximum: 110_000,
    example: 45_000,
  },
  {
    name: "include_selectors",
    type: "list",
    title: "Include selectors",
    description:
      'CSS selectors: only content inside matching elements is returned, such as "article" or "main".',
    maxItems: 20,
    example: ["article"],
  },
  {
    name: "exclude_selectors",
    type: "list",
    title: "Exclude selectors",
    description:
      'CSS selectors: matching elements are removed before the content is extracted, such as ".comments".',
    maxItems: 20,
    example: [".comments", ".newsletter-signup"],
  },
] as const satisfies readonly Field[];

type ValueOf<F extends Field> = F["type"] extends "integer"
  ? number
  : F["type"] extends "boolean"
    ? boolean
    : F["type"] extends "list"
      ? string[]
      : string;

type Values<T extends readonly Field[]> = {
  [F in T[number] as F["name"]]?: ValueOf<F>;
};

export type SearchOptions = Values<typeof SEARCH_FIELDS> & { query: string };
export type FetchOptions = Values<typeof FETCH_FIELDS> & { urls: string[] };

/** A request the caller got wrong. Its message is safe to send back to them. */
export class InvalidInput extends Error {
  override name = "InvalidInput";
}

function invalid(message: string): never {
  throw new InvalidInput(message);
}

/**
 * Where the raw values came from. A query string carries everything as
 * strings, which are converted to each field's type; a JSON body or an Actor
 * input must already use the right types.
 */
export type Source = "query" | "json";

function parseInteger(field: Field, value: unknown, source: Source): number {
  const number =
    source === "query" && typeof value === "string" && /^-?\d+$/.test(value)
      ? Number(value)
      : value;
  if (typeof number !== "number" || !Number.isSafeInteger(number)) {
    invalid(`\`${field.name}\` must be an integer.`);
  }
  if (field.minimum !== undefined && number < field.minimum) {
    invalid(`\`${field.name}\` must be at least ${field.minimum}.`);
  }
  if (field.maximum !== undefined && number > field.maximum) {
    invalid(`\`${field.name}\` must be at most ${field.maximum}.`);
  }
  return number;
}

function parseBoolean(field: Field, value: unknown, source: Source): boolean {
  if (typeof value === "boolean") return value;
  if (source === "query" && typeof value === "string") {
    const text = value.toLowerCase();
    if (text === "true" || text === "1") return true;
    if (text === "false" || text === "0") return false;
  }
  invalid(`\`${field.name}\` must be true or false.`);
}

function parseString(field: Field, value: unknown): string {
  if (typeof value !== "string") invalid(`\`${field.name}\` must be a string.`);
  if (field.enum && !field.enum.includes(value)) {
    invalid(
      `\`${field.name}\` must be one of: ${field.enum.map((v) => `"${v}"`).join(", ")}.`,
    );
  }
  return value;
}

function parseList(field: Field, value: unknown): string[] {
  const raw = Array.isArray(value) ? value : [value];
  if (!raw.every((item) => typeof item === "string")) {
    invalid(
      field.commaSeparated
        ? `\`${field.name}\` must be a list of strings or one comma-separated string.`
        : `\`${field.name}\` must be a list of strings.`,
    );
  }
  const parts = field.commaSeparated
    ? (raw as string[]).flatMap((item) => item.split(","))
    : (raw as string[]);
  // Trimmed, without blanks or repeats: a repeated URL would be fetched, and
  // charged, twice.
  const items = [...new Set(parts.map((item) => item.trim()).filter(Boolean))];
  if (field.maxItems !== undefined && items.length > field.maxItems) {
    invalid(
      `\`${field.name}\` takes at most ${field.maxItems} items (got ${items.length}).`,
    );
  }
  return items;
}

interface ParseSettings {
  source: Source;
  /**
   * Skip keys that are not in `fields` instead of rejecting them. For the
   * Actor input, which carries the fields of both modes at once.
   */
  ignoreUnknown?: boolean;
  /** Replace a field's `maxItems`, by field name. */
  maxItems?: Record<string, number>;
}

function parse<T extends readonly Field[]>(
  fields: T,
  raw: Record<string, unknown>,
  settings: ParseSettings,
): Values<T> {
  const byName = new Map<string, Field>(fields.map((f) => [f.name, f]));
  const values: Record<string, unknown> = {};

  for (const [name, value] of Object.entries(raw)) {
    const base = byName.get(name);
    if (!base) {
      if (settings.ignoreUnknown) continue;
      invalid(
        `Unknown parameter \`${name}\`. Accepted: ${[...byName.keys()].join(", ")}.`,
      );
    }
    if (value === undefined || value === null) continue;
    const maxItems = settings.maxItems?.[name];
    const field = maxItems === undefined ? base : { ...base, maxItems };

    if (field.type === "list") {
      // A query string can only say "empty" by sending a blank value.
      const items = parseList(field, value);
      if (items.length > 0) values[name] = items;
      continue;
    }
    // A repeated query parameter arrives as an array.
    if (Array.isArray(value)) {
      invalid(`\`${name}\` must be given once.`);
    }
    // A blank value (`?page=`, or a cleared field of the input form) is not set.
    if (value === "") continue;
    values[name] =
      field.type === "integer"
        ? parseInteger(field, value, settings.source)
        : field.type === "boolean"
          ? parseBoolean(field, value, settings.source)
          : parseString(field, value);
  }

  for (const field of fields) {
    if (!field.required) continue;
    const value = values[field.name];
    if (value === undefined || (typeof value === "string" && !value.trim())) {
      invalid(`\`${field.name}\` is required.`);
    }
  }
  return values as Values<T>;
}

export function parseSearch(
  raw: Record<string, unknown>,
  settings: ParseSettings,
): SearchOptions {
  return parse(SEARCH_FIELDS, raw, settings) as SearchOptions;
}

export function parseFetch(
  raw: Record<string, unknown>,
  settings: ParseSettings,
): FetchOptions {
  return parse(FETCH_FIELDS, raw, settings) as FetchOptions;
}
