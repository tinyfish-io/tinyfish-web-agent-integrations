import http from "node:http";
import { log } from "apify";
import type { EventName } from "./charging.js";
import { InvalidInput, parseFetch, parseSearch, type Source } from "./options.js";
import {
  publicFailure,
  TinyFishError,
  type fetchPages,
  type search,
} from "./tinyfish.js";
import { VERSION } from "./version.js";

/** What the server calls out to. Passed in so tests can replace it. */
export interface ServerDeps {
  search: typeof search;
  fetchPages: typeof fetchPages;
  charge: (
    eventName: EventName,
    count: number,
    requestId: string | undefined,
  ) => Promise<void>;
}

/** Largest request body accepted, in bytes. */
const MAX_BODY_BYTES = 256 * 1024;

/** A failure with a status and a message that are safe to send to the caller. */
class HttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly headers: Record<string, string> = {},
  ) {
    super(message);
  }
}

function send(
  res: http.ServerResponse,
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
): void {
  res.writeHead(status, { "Content-Type": "application/json", ...headers });
  res.end(JSON.stringify(body));
}

/** Query parameters as a record. A repeated parameter becomes an array. */
function queryValues(params: URLSearchParams): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const key of new Set(params.keys())) {
    const all = params.getAll(key);
    values[key] = all.length === 1 ? all[0] : all;
  }
  return values;
}

async function jsonBody(
  req: http.IncomingMessage,
): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) {
      throw new HttpError(
        413,
        "body_too_large",
        `The request body must be at most ${MAX_BODY_BYTES} bytes.`,
      );
    }
    chunks.push(chunk as Buffer);
  }
  let body: unknown;
  try {
    body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new InvalidInput("The request body must be valid JSON.");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new InvalidInput("The request body must be a JSON object.");
  }
  return body as Record<string, unknown>;
}

type Route = (
  raw: Record<string, unknown>,
  source: Source,
  requestId: string | undefined,
  deps: ServerDeps,
) => Promise<{ body: unknown; charged: number }>;

const ROUTES: Record<string, Route> = {
  "/search": async (raw, source, requestId, deps) => {
    const body = await deps.search(parseSearch(raw, { source }));
    // A search that found nothing is not charged.
    const found = Array.isArray(body.results) && body.results.length > 0;
    const charged = found ? 1 : 0;
    await deps.charge("search", charged, requestId);
    return { body, charged };
  },
  "/fetch": async (raw, source, requestId, deps) => {
    const body = await deps.fetchPages(parseFetch(raw, { source }));
    // One event per page that came back. URLs in `errors` are not charged.
    const charged = body.results.length;
    await deps.charge("fetch", charged, requestId);
    return { body, charged };
  },
};

const INFO = {
  name: "TinyFish Search & Fetch",
  version: VERSION,
  endpoints: {
    "GET|POST /search": "Search the web and get ranked results.",
    "GET|POST /fetch": "Read up to 10 URLs as Markdown, HTML, or JSON.",
  },
  docs: "https://docs.tinyfish.ai",
};

async function handle(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  deps: ServerDeps,
): Promise<void> {
  // Apify checks that the server is up before it routes requests to this run.
  if (req.headers["x-apify-container-server-readiness-probe"]) {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("ok");
    return;
  }

  const started = Date.now();
  const requestId = req.headers["x-actor-request-id"]?.toString();
  // The ID of the Apify user who sent the request. Never their name or token.
  const userId = req.headers["x-apify-user-id"]?.toString();
  let status = 200;
  let charged = 0;
  let path = req.url ?? "/";

  try {
    // `URL.parse` returns null for a path it cannot read, such as "//".
    const url = URL.parse(path, "http://localhost");
    path = url?.pathname ?? path;
    if (url?.pathname === "/" && req.method === "GET") {
      send(res, 200, INFO);
      return;
    }
    const route = url && ROUTES[url.pathname];
    if (!route) {
      throw new HttpError(
        404,
        "not_found",
        "No such endpoint. Use /search or /fetch.",
      );
    }
    if (req.method !== "GET" && req.method !== "POST") {
      throw new HttpError(405, "method_not_allowed", "Use GET or POST.", {
        Allow: "GET, POST",
      });
    }
    const result =
      req.method === "GET"
        ? await route(queryValues(url.searchParams), "query", requestId, deps)
        : await route(await jsonBody(req), "json", requestId, deps);
    charged = result.charged;
    send(res, 200, result.body);
  } catch (error) {
    let failure: HttpError;
    if (error instanceof HttpError) {
      failure = error;
    } else if (error instanceof InvalidInput) {
      failure = new HttpError(400, "invalid_input", error.message);
    } else if (error instanceof TinyFishError) {
      const shown = publicFailure(error);
      failure = new HttpError(
        shown.status,
        shown.code,
        shown.message,
        shown.status === 429 ? { "Retry-After": "5" } : {},
      );
      // A request TinyFish rejected is the caller's mistake, not an incident.
      const level = shown.status === 400 ? "warning" : "error";
      log[level]("TinyFish request failed", {
        endpoint: error.endpoint,
        status: error.status,
        apiCode: error.apiCode,
        tinyfishRequestId: error.requestId,
        detail: error.detail,
      });
    } else {
      // Includes a charge that failed: the result is withheld, because
      // sending it would hand out work nobody paid for.
      failure = new HttpError(
        500,
        "internal_error",
        "The request could not be completed. Try again.",
      );
      log.exception(error as Error, "Request failed");
    }
    status = failure.status;
    send(
      res,
      failure.status,
      { error: { code: failure.code, message: failure.message } },
      failure.headers,
    );
  } finally {
    // Never the query or the URLs: they can hold personal data.
    log.info("Request", {
      method: req.method,
      path,
      status,
      charged,
      ms: Date.now() - started,
      userId,
      requestId,
    });
  }
}

/** The HTTP server behind the Actor's server interface. */
export function createServer(deps: ServerDeps): http.Server {
  return http.createServer((req, res) => {
    // This run serves many users: a request that breaks in a way `handle`
    // did not expect is dropped, not allowed to take the others down.
    handle(req, res, deps).catch((error: unknown) => {
      log.exception(error as Error, "Request handler failed");
      res.destroy();
    });
  });
}
