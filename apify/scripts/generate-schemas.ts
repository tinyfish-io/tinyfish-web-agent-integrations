/**
 * Writes `.actor/input_schema.json` and `.actor/openapi.json` from the field
 * tables in `src/options.ts`. Run `npm run build:schemas` after changing a
 * field or the package version, and commit the result: Apify builds from the
 * committed files, and a test fails when they are out of date.
 */
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  FETCH_FIELDS,
  MAX_URLS_PER_REQUEST,
  MAX_URLS_PER_RUN,
  SEARCH_FIELDS,
  type Field,
} from "../src/options.js";
import { MODES } from "../src/run.js";
import { VERSION } from "../src/version.js";

type Json = Record<string, unknown>;

/** The limits and choices of a field, in the JSON Schema both documents share. */
function constraints(field: Field): Json {
  if (field.type === "list") {
    return {
      type: "array",
      items: { type: "string" },
      ...(field.maxItems !== undefined ? { maxItems: field.maxItems } : {}),
    };
  }
  return {
    type: field.type,
    ...(field.enum ? { enum: field.enum } : {}),
    ...(field.minimum !== undefined ? { minimum: field.minimum } : {}),
    ...(field.maximum !== undefined ? { maximum: field.maximum } : {}),
  };
}

function inputProperty(field: Field): Json {
  const editor =
    field.type === "list"
      ? "stringList"
      : field.type === "string"
        ? field.enum
          ? "select"
          : "textfield"
        : undefined;
  return {
    title: field.title,
    description: field.description,
    ...constraints(field),
    ...(editor ? { editor } : {}),
    example: field.example,
  };
}

/** The Actor input: a mode, then the fields of Search and of Fetch. */
export function buildInputSchema(): Json {
  const properties: Record<string, Json> = {
    mode: {
      title: "Mode",
      type: "string",
      description:
        'What to do: "search" finds pages for a query, "fetch" reads the pages at the URLs you give.',
      editor: "select",
      enum: MODES,
      enumTitles: ["Search the web", "Fetch URLs"],
      default: "search",
    },
  };
  const add = (field: Field, extra: Json = {}) => {
    properties[field.name] ??= { ...inputProperty(field), ...extra };
  };

  // What to search for or read first, then each mode's options in a section.
  const [query] = SEARCH_FIELDS;
  const [urls, purpose] = FETCH_FIELDS;
  add(query, {
    description: `${query.description} Used in "search" mode.`,
    prefill: query.example,
  });
  add(urls, {
    description: `${urls.description} Used in "fetch" mode. Up to ${MAX_URLS_PER_RUN} per run.`,
    maxItems: MAX_URLS_PER_RUN,
  });
  add(purpose);
  for (const [caption, fields] of [
    ["Search options", SEARCH_FIELDS],
    ["Fetch options", FETCH_FIELDS],
  ] as const) {
    let first = true;
    for (const field of fields) {
      if (field.name in properties) continue;
      add(field, first ? { sectionCaption: caption } : {});
      first = false;
    }
  }

  return {
    $schema: "https://apify.com/schemas/v1/input.ide.json",
    title: "TinyFish Search & Fetch input",
    description:
      "Search the web, or read pages as clean Markdown, HTML, or JSON. Field names match the TinyFish Search and Fetch APIs.",
    type: "object",
    schemaVersion: 1,
    properties,
    required: [],
  };
}

function operation(
  name: "search" | "fetch",
  summary: string,
  description: string,
  fields: readonly Field[],
): Json {
  const responses = {
    "200": {
      description: "The TinyFish response.",
      content: {
        "application/json": {
          schema: { $ref: `#/components/schemas/${name}Response` },
        },
      },
    },
    ...Object.fromEntries(
      Object.entries({
        "400": "A parameter is missing or invalid. Nothing is charged.",
        "429": "Too many requests. Retry after a few seconds.",
        "502": "TinyFish could not complete the request. Nothing is charged.",
        "504": "TinyFish did not answer in time. Nothing is charged.",
      }).map(([status, text]) => [
        status,
        {
          description: text,
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/Error" },
            },
          },
        },
      ]),
    ),
  };
  return {
    get: {
      operationId: `${name}Get`,
      summary,
      description,
      parameters: fields.map((field) => ({
        name: field.name,
        in: "query",
        required: field.required === true,
        description: field.description,
        schema: constraints(field),
        // A list is sent by repeating the parameter. Domains may also be
        // sent as one comma-separated value.
        ...(field.type === "list" ? { explode: !field.commaSeparated } : {}),
        example: field.example,
      })),
      responses,
    },
    post: {
      operationId: `${name}Post`,
      summary,
      description,
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: { $ref: `#/components/schemas/${name}Request` },
          },
        },
      },
      responses,
    },
  };
}

function requestSchema(fields: readonly Field[]): Json {
  return {
    type: "object",
    required: fields.filter((f) => f.required).map((f) => f.name),
    properties: Object.fromEntries(
      fields.map((field) => [
        field.name,
        {
          description: field.description,
          ...constraints(field),
          example: field.example,
        },
      ]),
    ),
    additionalProperties: false,
  };
}

const nullableString = { type: "string", nullable: true };
const stringList = { type: "array", items: { type: "string" } };

/** The OpenAPI document Apify renders in the Actor's Server tab. */
export function buildOpenApi(): Json {
  return {
    openapi: "3.0.3",
    info: {
      title: "TinyFish Search & Fetch",
      version: VERSION,
      description:
        "Search the web and read pages as clean Markdown, HTML, or JSON. Each endpoint takes the same fields as a GET query string or a POST JSON body. Authenticate with your Apify API token.",
    },
    paths: {
      "/search": operation(
        "search",
        "Search the web",
        "Returns ranked results with titles, snippets, and source URLs. Charged as one `search` event when at least one result comes back.",
        SEARCH_FIELDS,
      ),
      "/fetch": operation(
        "fetch",
        "Read pages",
        `Returns the content of up to ${MAX_URLS_PER_REQUEST} URLs. A URL that could not be fetched is listed in \`errors\`; the others still come back in \`results\`. Charged as one \`fetch\` event per page in \`results\`.`,
        FETCH_FIELDS,
      ),
    },
    components: {
      schemas: {
        searchRequest: requestSchema(SEARCH_FIELDS),
        fetchRequest: requestSchema(FETCH_FIELDS),
        searchResponse: {
          type: "object",
          properties: {
            query: { type: "string" },
            results: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  position: {
                    type: "integer",
                    description: "Rank of the result, starting from 1.",
                  },
                  site_name: { type: "string" },
                  title: { type: "string" },
                  snippet: { type: "string" },
                  url: { type: "string" },
                  date: {
                    type: "string",
                    description: "Present for news and some web results.",
                  },
                },
                additionalProperties: true,
              },
            },
            total_results: { type: "integer" },
            page: { type: "integer" },
          },
        },
        fetchResponse: {
          type: "object",
          properties: {
            results: {
              type: "array",
              description: "One entry per page that was fetched.",
              items: {
                type: "object",
                properties: {
                  url: { type: "string", description: "The URL you asked for." },
                  final_url: {
                    type: "string",
                    description: "The URL after any redirects.",
                  },
                  title: nullableString,
                  description: nullableString,
                  language: nullableString,
                  author: nullableString,
                  published_date: nullableString,
                  text: {
                    description:
                      'The page content: a string for "markdown" and "html", a document tree for "json".',
                  },
                  links: stringList,
                  image_links: stringList,
                  iframe_links: stringList,
                  format: { type: "string" },
                  latency_ms: { type: "number", nullable: true },
                },
                additionalProperties: true,
              },
            },
            errors: {
              type: "array",
              description: "One entry per URL that could not be fetched.",
              items: {
                type: "object",
                properties: {
                  url: { type: "string" },
                  error: {
                    type: "string",
                    description:
                      "Why the fetch failed, such as `page_not_found`, `timeout` or `bot_blocked`.",
                  },
                  status: {
                    type: "integer",
                    description: "HTTP status of the target, when it sent one.",
                  },
                },
                additionalProperties: true,
              },
            },
          },
        },
        Error: {
          type: "object",
          properties: {
            error: {
              type: "object",
              properties: {
                code: { type: "string", example: "invalid_input" },
                message: { type: "string", example: "`query` is required." },
              },
            },
          },
        },
      },
    },
  };
}

export const GENERATED = {
  ".actor/input_schema.json": buildInputSchema,
  ".actor/openapi.json": buildOpenApi,
};

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  for (const [path, build] of Object.entries(GENERATED)) {
    writeFileSync(
      new URL(`../${path}`, import.meta.url),
      `${JSON.stringify(build(), null, 2)}\n`,
    );
    console.log(`Wrote ${path}`);
  }
}
