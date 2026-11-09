import { ConvexError } from "convex/values";
import { env } from "./_generated/server.js";
import { VERSION } from "./version.js";

const DEFAULT_SEARCH_URL = "https://api.search.tinyfish.ai";
const DEFAULT_FETCH_URL = "https://api.fetch.tinyfish.ai";

/**
 * Sent on every request so TinyFish can attribute traffic to this component.
 * See `X-TF-Client-Name` in the other integrations in this repository.
 */
export const CLIENT_HEADERS = {
  "X-TF-Client-Name": "convex",
  "X-TF-Client-Version": VERSION,
};

/**
 * Client-side deadlines. Fetch allows each URL 110s and the batch 120s, and
 * the docs ask clients to wait at least 150s to receive timeouts cleanly.
 */
export const TIMEOUT_MS = { search: 60_000, fetch: 150_000 };

/**
 * Retry policy for transient TinyFish failures. Exported as a mutable object
 * so tests can zero out the delays.
 */
export const RETRY = { attempts: 2, baseDelayMs: 500, maxDelayMs: 8_000 };

const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

export type Endpoint = "search" | "fetch";

export function endpointUrl(endpoint: Endpoint): string {
  const url =
    endpoint === "search"
      ? (env.TINYFISH_SEARCH_URL ?? DEFAULT_SEARCH_URL)
      : (env.TINYFISH_FETCH_URL ?? DEFAULT_FETCH_URL);
  return url.replace(/\/+$/, "");
}

function apiKey(): string {
  const key = env.TINYFISH_API_KEY;
  if (!key) {
    throw new ConvexError({
      code: "tinyfish_missing_api_key",
      message:
        "TINYFISH_API_KEY is not set for the TinyFish component. Pass it in `app.use(tinyfish, { env: { TINYFISH_API_KEY: ... } })`.",
    });
  }
  return key;
}

export type RequestFailure = {
  code: "tinyfish_request_failed";
  /** HTTP status, or 0 for a network failure or timeout. */
  status: number;
  endpoint: Endpoint;
  /** TinyFish error code, e.g. `INSUFFICIENT_CREDITS`, when the API sent one. */
  apiCode?: string;
  requestId?: string;
  message: string;
};

function fail(
  endpoint: Endpoint,
  status: number,
  message: string,
  details: { apiCode?: string; requestId?: string } = {},
): never {
  const data: RequestFailure = {
    code: "tinyfish_request_failed",
    status,
    endpoint,
    message: `TinyFish ${endpoint} failed (${status}): ${message}`,
    ...(details.apiCode ? { apiCode: details.apiCode } : {}),
    ...(details.requestId ? { requestId: details.requestId } : {}),
  };
  throw new ConvexError(data);
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
  if (typeof record.request_id === "string") details.requestId = record.request_id;
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

export type TinyfishRequest = {
  /** Query string parameters (Search). */
  params?: Record<string, string>;
  /** JSON body (Fetch). */
  body?: Record<string, unknown>;
  /** Extra tries after the first. Defaults to `RETRY.attempts`. */
  retries?: number;
};

/**
 * Call a TinyFish endpoint, retrying transient failures, and return the parsed
 * JSON response. Failures throw a `ConvexError` carrying a `RequestFailure`.
 */
export async function tinyfishRequest(
  endpoint: Endpoint,
  init: TinyfishRequest = {},
): Promise<Record<string, any>> {
  const url = new URL(endpointUrl(endpoint));
  for (const [key, value] of Object.entries(init.params ?? {})) {
    url.searchParams.set(key, value);
  }
  const headers: Record<string, string> = {
    "X-API-Key": apiKey(),
    Accept: "application/json",
    ...CLIENT_HEADERS,
  };
  let payload: string | undefined;
  if (init.body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(init.body);
  }
  const method = init.body ? "POST" : "GET";
  const retries = init.retries ?? RETRY.attempts;

  for (let attempt = 0; ; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS[endpoint]);
    let response: Response;
    let text: string;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: payload,
        signal: controller.signal,
      });
      text = await response.text();
    } catch (error) {
      // Network failure or timeout: worth another attempt.
      const message = controller.signal.aborted
        ? `no response within ${TIMEOUT_MS[endpoint] / 1000}s`
        : error instanceof Error
          ? error.message
          : String(error);
      if (attempt >= retries) fail(endpoint, 0, message);
      await sleep(retryDelayMs(attempt, null));
      continue;
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

    if (response.ok && body && typeof body === "object") {
      return body as Record<string, any>;
    }

    const details = errorDetails(
      body,
      response.ok
        ? "response was not JSON"
        : text.slice(0, 300) || response.statusText,
    );
    details.requestId ??= response.headers.get("x-request-id") ?? undefined;
    if (!RETRYABLE_STATUS.has(response.status) || attempt >= retries) {
      fail(endpoint, response.status, details.message, details);
    }
    await sleep(retryDelayMs(attempt, response.headers.get("retry-after")));
  }
}

/** The `RequestFailure` inside an error thrown by `tinyfishRequest`, if any. */
export function requestFailure(error: unknown): RequestFailure | null {
  if (error instanceof ConvexError) {
    const data = error.data as Partial<RequestFailure> | undefined;
    if (data && data.code === "tinyfish_request_failed") {
      return data as RequestFailure;
    }
  }
  return null;
}

export const _test = { retryDelayMs, errorDetails };
