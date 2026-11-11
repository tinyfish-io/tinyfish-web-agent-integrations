/* eslint-disable */
/**
 * Generated `ComponentApi` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type { FunctionReference } from "convex/server";

/**
 * A utility for referencing a Convex component's exposed API.
 *
 * Useful when expecting a parameter like `components.myComponent`.
 * Usage:
 * ```ts
 * async function myFunction(ctx: QueryCtx, component: ComponentApi) {
 *   return ctx.runQuery(component.someFile.someQuery, { ...args });
 * }
 * ```
 */
export type ComponentApi<Name extends string | undefined = string | undefined> =
  {
    jobs: {
      cancel: FunctionReference<
        "mutation",
        "internal",
        { jobId: string },
        boolean,
        Name
      >;
      deleteJob: FunctionReference<
        "mutation",
        "internal",
        { jobId: string },
        null,
        Name
      >;
      get: FunctionReference<
        "query",
        "internal",
        { jobId: string },
        {
          _creationTime: number;
          _id: string;
          completed: number;
          completedAt?: number;
          context?: any;
          error?: string;
          failed: number;
          finalized: boolean;
          kind: "fetch" | "search_and_fetch";
          query?: string;
          searchResults?: Array<any>;
          startedAt: number;
          status: "queued" | "running" | "completed" | "failed" | "cancelled";
          storeContent: boolean;
          total: number;
          truncated: number;
          updatedAt: number;
          urls: Array<string>;
        } | null,
        Name
      >;
      getPage: FunctionReference<
        "query",
        "internal",
        { jobId: string; url: string },
        {
          _creationTime: number;
          _id: string;
          author?: string;
          description?: string;
          error?: string;
          error_status?: number;
          extra?: any;
          fetchedAt: number;
          final_url?: string;
          format?: string;
          highlights?: Array<any>;
          iframe_links?: Array<string>;
          image_links?: Array<string>;
          jobId: string;
          language?: string;
          latency_ms?: number;
          links?: Array<string>;
          position?: number;
          published_date?: string;
          snippet?: string;
          status: "completed" | "failed";
          text?: any;
          title?: string;
          truncated: boolean;
          url: string;
        } | null,
        Name
      >;
      list: FunctionReference<
        "query",
        "internal",
        {
          limit?: number;
          status?: "queued" | "running" | "completed" | "failed" | "cancelled";
        },
        Array<{
          _creationTime: number;
          _id: string;
          completed: number;
          completedAt?: number;
          context?: any;
          error?: string;
          failed: number;
          finalized: boolean;
          kind: "fetch" | "search_and_fetch";
          query?: string;
          searchResults?: Array<any>;
          startedAt: number;
          status: "queued" | "running" | "completed" | "failed" | "cancelled";
          storeContent: boolean;
          total: number;
          truncated: number;
          updatedAt: number;
          urls: Array<string>;
        }>,
        Name
      >;
      listPages: FunctionReference<
        "query",
        "internal",
        {
          jobId: string;
          paginationOpts: {
            cursor: string | null;
            endCursor?: string | null;
            id?: number;
            maximumBytesRead?: number;
            maximumRowsRead?: number;
            numItems: number;
          };
          status?: "completed" | "failed";
        },
        any,
        Name
      >;
      startFetch: FunctionReference<
        "mutation",
        "internal",
        {
          context?: any;
          onComplete?: string;
          options?: {
            exclude_selectors?: Array<string>;
            extra?: Record<string, any>;
            format?: "markdown" | "html" | "json";
            highlights?: {
              include_full_page_text?: boolean;
              max_characters?: number;
              max_snippets?: number;
              query: string;
            };
            iframe_links?: boolean;
            image_links?: boolean;
            include_etag_and_last_modified?: boolean;
            include_selectors?: Array<string>;
            links?: boolean;
            maxCharacters?: number;
            per_url_timeout_ms?: number;
            purpose?: string;
            ttl?: number;
          };
          storeContent?: boolean;
          urls: Array<string>;
        },
        string,
        Name
      >;
      startSearchAndFetch: FunctionReference<
        "mutation",
        "internal",
        {
          context?: any;
          fetchOptions?: {
            exclude_selectors?: Array<string>;
            extra?: Record<string, any>;
            format?: "markdown" | "html" | "json";
            highlights?: {
              include_full_page_text?: boolean;
              max_characters?: number;
              max_snippets?: number;
              query: string;
            };
            iframe_links?: boolean;
            image_links?: boolean;
            include_etag_and_last_modified?: boolean;
            include_selectors?: Array<string>;
            links?: boolean;
            maxCharacters?: number;
            per_url_timeout_ms?: number;
            purpose?: string;
            ttl?: number;
          };
          maxResults?: number;
          onComplete?: string;
          query: string;
          searchOptions?: {
            after_date?: string;
            before_date?: string;
            domain_type?: "web" | "news" | "research_paper";
            exclude_domains?: string | Array<string>;
            extra?: Record<string, any>;
            include_domains?: string | Array<string>;
            language?: string;
            location?: string;
            page?: number;
            pub_year_max?: number;
            pub_year_min?: number;
            purpose?: string;
            recency_minutes?: number;
          };
          storeContent?: boolean;
        },
        string,
        Name
      >;
    };
    lib: {
      fetch: FunctionReference<
        "action",
        "internal",
        {
          options?: {
            exclude_selectors?: Array<string>;
            extra?: Record<string, any>;
            format?: "markdown" | "html" | "json";
            highlights?: {
              include_full_page_text?: boolean;
              max_characters?: number;
              max_snippets?: number;
              query: string;
            };
            if_modified_since?: string;
            if_none_match?: string;
            iframe_links?: boolean;
            image_links?: boolean;
            include_etag_and_last_modified?: boolean;
            include_selectors?: Array<string>;
            links?: boolean;
            maxCharacters?: number;
            per_url_timeout_ms?: number;
            purpose?: string;
            ttl?: number;
          };
          urls: Array<string>;
        },
        any,
        Name
      >;
      search: FunctionReference<
        "action",
        "internal",
        {
          options?: {
            after_date?: string;
            before_date?: string;
            domain_type?: "web" | "news" | "research_paper";
            exclude_domains?: string | Array<string>;
            extra?: Record<string, any>;
            include_domains?: string | Array<string>;
            language?: string;
            location?: string;
            page?: number;
            pub_year_max?: number;
            pub_year_min?: number;
            purpose?: string;
            recency_minutes?: number;
          };
          query: string;
        },
        any,
        Name
      >;
    };
  };
