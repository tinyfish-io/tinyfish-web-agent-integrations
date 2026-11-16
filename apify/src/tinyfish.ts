import type { FetchOptions, SearchOptions } from "./options.js";
import { VERSION } from "./version.js";

const DEFAULT_SEARCH_URL = "https://api.search.tinyfish.ai";
const DEFAULT_FETCH_URL = "https://api.fetch.tinyfish.ai";

/**
 * Sent on every request so TinyFish can attribute traffic to this Actor.
 * See `X-TF-Client-Name` in the other integrations in this repository.
 */
export const CLIENT_HEADERS = {
  "X-TF-Client-Name": "apify",
  "X-TF-Client-Version": VERSION,
};

export type Endpoint = "search" | "fetch";

/**
 * Deadlines, in milliseconds. `attempt` bounds one HTTP request: Fetch allows
 * each URL 110s and the batch 120s, and the docs ask clients to wait at least
 * 150s to receive timeouts cleanly. `total` bounds a call across its retries,
 * and stays under the 5 minutes Apify gives a Server Actor to start answering.
 */
export const TIMEOUT_MS: Record<Endpoint, { attempt: number; total: number }> =
  {
    search: { attempt: 60_000, total: 90_000 },
    fetch: { attempt: 150_000, total: 270_000 },
  };

/**
 * Retry policy for transient TinyFish failures. Exported as a mutable object
 * so tests can zero out the delays.
 */
export const RETRY = { attempts: 2, baseDelayMs: 500, maxDelayMs: 8_000 };

const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

/** A TinyFish request that failed after any retries. */
export class TinyFishError extends Error {
  override name = "TinyFishError";

  constructor(
    readonly endpoint: Endpoint,
    /** HTTP status, or 0 for a network failure or timeout. */
    readonly status: number,
    /** What TinyFish said went wrong. */
    readonly detail: string,
    /** TinyFish error code, e.g. `INSUFFICIENT_CREDITS`, when the API sent one. */
    readonly apiCode?: string,
    readonly requestId?: string,
  ) {
    super(`TinyFish ${endpoint} failed (${status}): ${detail}`);
  }
}

/**
 * What the caller is told about a failed call: an HTTP status, a stable code,
 * and a message. A request TinyFish rejected as invalid is the caller's to
 * fix, so its message is passed on. Everything else is ours (the API key,
 * credits, an outage) and is reported without the details.
 */
export function publicFailure(error: TinyFishError): {
  status: number;
  code: string;
  message: string;
} {
  if (error.status === 400 || error.status === 422) {
    return { status: 400, code: "invalid_input", message: error.detail };
  }
  if (error.status === 429) {
    return {
      status: 429,
      code: "rate_limited",
      message:
        "TinyFish is handling too many requests right now. Try again in a few seconds.",
    };
  }
  if (error.status === 0) {
    return {
      status: 504,
      code: "upstream_timeout",
      message: "TinyFish did not answer in time. Try again.",
    };
  }
  return {
    status: 502,
    code: "upstream_error",
    message: "TinyFish could not complete the request. Try again.",
  };
}

function endpointUrl(endpoint: Endpoint): string {
  const url =
    endpoint === "search"
      ? (process.env.TINYFISH_SEARCH_URL ?? DEFAULT_SEARCH_URL)
      : (process.env.TINYFISH_FETCH_URL ?? DEFAULT_FETCH_URL);
  return url.replace(/\/+$/, "");
}

async function sleep(ms: number): Promise<void> {
  if (ms <= 0) return;
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function retryDelayMs(attempt: number, retryAfter: string | null): number {
  if (retryAfter) {
    const seconds = Number(retryAfter);
    if (Number.isFinite(seconds) && seconds >= 0) {
      return Math.min(seconds * 1000, RETRY.maxDelayMs);
    }
  }
  return Math.min(RETRY.baseDelayMs * 2 ** attempt, RETRY.maxDelayMs);
}

/** Pull a code and message out of a TinyFish error body, whatever its shape. */
function errorDetails(
  body: unknown,
  fallback: string,
): { message: string; apiCode?: string; requestId?: string } {
  const details: { message: string; apiCode?: string; requestId?: string } = {
    message: fallback,
  };
  if (!body || typeof body !== "object") return details;
  const record = body as Record<string, unknown>;
  if (typeof record.request_id === "string") {
    details.requestId = record.request_id;
  }
  const nested =
    record.error && typeof record.error === "object"
      ? (record.error as Record<string, unknown>)
      : undefined;
  const code = nested?.code ?? record.code;
  if (typeof code === "string") details.apiCode = code;
  for (const value of [
    nested?.message,
    record.error,
    record.message,
    record.detail,
  ]) {
    if (typeof value === "string" && value.length > 0) {
      details.message = value.slice(0, 500);
      break;
    }
  }
  return details;
}

interface TinyFishRequest {
  /** Query string parameters (Search). */
  params?: Record<string, string>;
  /** JSON body (Fetch). */
  body?: Record<string, unknown>;
}

/**
 * Call a TinyFish endpoint, retrying transient failures while time remains,
 * and return the parsed JSON response. Failures throw a `TinyFishError`.
 * Both APIs are read-only, so sending a request again is safe.
 */
async function request(
  endpoint: Endpoint,
  init: TinyFishRequest,
): Promise<Record<string, unknown>> {
  const url = new URL(endpointUrl(endpoint));
  for (const [key, value] of Object.entries(init.params ?? {})) {
    url.searchParams.set(key, value);
  }
  const headers: Record<string, string> = {
    // main.ts refuses to start without the key.
    "X-API-Key": process.env.TINYFISH_API_KEY ?? "",
    Accept: "application/json",
    ...CLIENT_HEADERS,
  };
  let payload: string | undefined;
  if (init.body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(init.body);
  }
  const method = init.body ? "POST" : "GET";
  const limits = TIMEOUT_MS[endpoint];
  const deadline = Date.now() + limits.total;

  for (let attempt = 0; ; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(
      () => controller.abort(),
      Math.min(limits.attempt, deadline - Date.now()),
    );
    let response: Response | undefined;
    let text = "";
    let failure = "";
    try {
      response = await fetch(url, {
        method,
        headers,
        body: payload,
        signal: controller.signal,
      });
      text = await response.text();
    } catch (error) {
      failure = controller.signal.aborted
        ? "no response in time"
        : error instanceof Error
          ? error.message
          : String(error);
    } finally {
      clearTimeout(timer);
    }

    let body: unknown = null;
    if (text.length > 0) {
      try {
        body = JSON.parse(text);
      } catch {
        body = null;
      }
    }
    if (response?.ok && body && typeof body === "object") {
      return body as Record<string, unknown>;
    }

    const status = failure ? 0 : (response?.status ?? 0);
    const details = failure
      ? { message: failure }
      : errorDetails(
          body,
          response?.ok
            ? "response was not JSON"
            : text.slice(0, 300) || (response?.statusText ?? ""),
        );
    const delay = retryDelayMs(
      attempt,
      response?.headers.get("retry-after") ?? null,
    );
    const retryable = status === 0 || RETRYABLE_STATUS.has(status);
    if (
      !retryable ||
      attempt >= RETRY.attempts ||
      Date.now() + delay >= deadline
    ) {
      throw new TinyFishError(
        endpoint,
        status,
        details.message,
        details.apiCode,
        details.requestId ?? response?.headers.get("x-request-id") ?? undefined,
      );
    }
    await sleep(delay);
  }
}

/**
 * Search the web. Returns the TinyFish response unchanged:
 * `{ query, results, total_results, page }`.
 */
export async function search(
  options: SearchOptions,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  for (const [key, value] of Object.entries(options)) {
    params[key] = Array.isArray(value) ? value.join(",") : String(value);
  }
  return await request("search", { params });
}

/** A Fetch response with `results` and `errors` always present as arrays. */
export interface FetchResponse extends Record<string, unknown> {
  results: Record<string, unknown>[];
  errors: Record<string, unknown>[];
}

/**
 * Read up to 10 URLs. A URL that could not be fetched lands in `errors` with
 * a code such as `bot_blocked` or `timeout`; the others still come back in
 * `results`.
 */
export async function fetchPages(options: FetchOptions): Promise<FetchResponse> {
  const body = await request("fetch", { body: { ...options } });
  return {
    ...body,
    results: Array.isArray(body.results) ? body.results : [],
    errors: Array.isArray(body.errors) ? body.errors : [],
  };
}
