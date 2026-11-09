import { v } from "convex/values";

/**
 * Argument validators mirroring the TinyFish Search and Fetch APIs.
 *
 * Field names match the REST API exactly (snake_case), so the TinyFish docs are
 * the reference for behavior: https://docs.tinyfish.ai/search-api/reference and
 * https://docs.tinyfish.ai/fetch-api/reference. Each options object also
 * accepts `extra`, an escape hatch for API fields that ship before this
 * component knows about them.
 */

const extra = v.optional(v.record(v.string(), v.any()));

export const searchOptionsValidator = v.object({
  /** Why you are searching. Improves result quality. Max 2000 characters. */
  purpose: v.optional(v.string()),
  /** Country code, e.g. "US". */
  location: v.optional(v.string()),
  /** Language code, e.g. "en". */
  language: v.optional(v.string()),
  /** Domains to restrict results to. An array is joined with commas. */
  include_domains: v.optional(v.union(v.string(), v.array(v.string()))),
  /** Domains to drop from results. An array is joined with commas. */
  exclude_domains: v.optional(v.union(v.string(), v.array(v.string()))),
  recency_minutes: v.optional(v.number()),
  /** YYYY-MM-DD */
  after_date: v.optional(v.string()),
  /** YYYY-MM-DD */
  before_date: v.optional(v.string()),
  domain_type: v.optional(
    v.union(
      v.literal("web"),
      v.literal("news"),
      v.literal("research_paper"),
    ),
  ),
  pub_year_min: v.optional(v.number()),
  pub_year_max: v.optional(v.number()),
  /** Zero-based page, up to 10. */
  page: v.optional(v.number()),
  extra,
});

export const fetchFormatValidator = v.union(
  v.literal("markdown"),
  v.literal("html"),
  v.literal("json"),
);

export const highlightsValidator = v.object({
  query: v.string(),
  max_snippets: v.optional(v.number()),
  max_characters: v.optional(v.number()),
  include_full_page_text: v.optional(v.boolean()),
});

/** Fetch options that are safe for any number of URLs. */
const fetchFields = {
  /** Why you are fetching. Improves result quality. Max 2000 characters. */
  purpose: v.optional(v.string()),
  format: v.optional(fetchFormatValidator),
  links: v.optional(v.boolean()),
  image_links: v.optional(v.boolean()),
  iframe_links: v.optional(v.boolean()),
  /** Cache tolerance in seconds. 0 forces a live fetch. */
  ttl: v.optional(v.number()),
  per_url_timeout_ms: v.optional(v.number()),
  include_etag_and_last_modified: v.optional(v.boolean()),
  include_selectors: v.optional(v.array(v.string())),
  exclude_selectors: v.optional(v.array(v.string())),
  /** Beta: enabled per account. Requires `format: "markdown"`. */
  highlights: v.optional(highlightsValidator),
  /**
   * Component option, not sent to TinyFish: cap each page's `text` at this
   * many characters. Capped pages come back with `truncated: true`.
   */
  maxCharacters: v.optional(v.number()),
  extra,
};

export const fetchOptionsValidator = v.object({
  ...fetchFields,
  /** Single URL only. */
  if_none_match: v.optional(v.string()),
  /** Single URL only. */
  if_modified_since: v.optional(v.string()),
});

/** Options for durable jobs, which fetch many URLs across several requests. */
export const jobFetchOptionsValidator = v.object(fetchFields);
