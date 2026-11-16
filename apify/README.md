## What does TinyFish Search & Fetch do?

**TinyFish Search & Fetch** gives your AI agent the live web through two calls:

- **Search** the web and get ranked results with titles, snippets, and source URLs.
- **Fetch** any page and get its content as clean **Markdown**, HTML, or JSON. Pages that need JavaScript are rendered in a real browser.

It is a real-time API: send an HTTP request and the answer comes back in the response, with no run to start and nothing to poll. It runs on [TinyFish](https://www.tinyfish.ai), the web infrastructure built for AI agents.

## Why use TinyFish Search & Fetch?

- **Ground an LLM in current information.** Search for sources, then read the best ones as Markdown, which costs far fewer tokens than raw HTML.
- **Build RAG pipelines and research agents** without running browsers, proxies, or a scraping stack.
- **Read JavaScript-heavy pages.** Content that only appears after scripts run is still returned.
- **Pay only for what works.** A page that could not be fetched, or a search with no results, costs nothing.
- **Use it anywhere Apify runs.** Call it over HTTP, from the Apify API clients, on a schedule, or from Make, Zapier, and n8n through Apify's integrations.

## How much does TinyFish Search & Fetch cost?

Pricing is pay per event. There are two events:

| Event | Charged when |
| --- | --- |
| `search` | A search returns at least one result. |
| `fetch` | A page is fetched. Charged once per page. |

You are never charged for a URL that fails, a search with no results, or a request that returns an error. Current prices are on the **Pricing** tab.

## How to search the web and read pages

Authenticate with your [Apify API token](https://console.apify.com/settings/integrations), as an `Authorization: Bearer <token>` header. Copy the Actor's URL from its **Server** tab.

### Search

```bash
curl 'https://tinyfish--tinyfish.apify.actor/search?query=best+vector+databases&recency_minutes=43200' \
  -H 'Authorization: Bearer <YOUR_APIFY_TOKEN>'
```

```json
{
  "query": "best vector databases",
  "results": [
    {
      "position": 1,
      "site_name": "example.com",
      "title": "Vector databases compared",
      "snippet": "A comparison of the most used vector databases...",
      "url": "https://example.com/vector-databases"
    }
  ],
  "total_results": 10,
  "page": 0
}
```

### Fetch

```bash
curl -X POST 'https://tinyfish--tinyfish.apify.actor/fetch' \
  -H 'Authorization: Bearer <YOUR_APIFY_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{ "urls": ["https://example.com/vector-databases"], "format": "markdown" }'
```

```json
{
  "results": [
    {
      "url": "https://example.com/vector-databases",
      "final_url": "https://example.com/vector-databases",
      "title": "Vector databases compared",
      "language": "en",
      "text": "# Vector databases compared\n\n...",
      "format": "markdown"
    }
  ],
  "errors": []
}
```

One request reads up to 10 URLs. A URL that cannot be fetched is listed in `errors` with a code such as `page_not_found`, `timeout`, or `bot_blocked`, and the other URLs still come back in `results`.

Both endpoints accept the same fields as a `GET` query string or a `POST` JSON body. In a query string, repeat a parameter to send a list: `?urls=https://a.com&urls=https://b.com`.

## Input

The **Server** tab lists every field of both endpoints and lets you try them from the browser. The fields have the same names as the TinyFish APIs, so the [Search](https://docs.tinyfish.ai/search-api/reference) and [Fetch](https://docs.tinyfish.ai/fetch-api/reference) references describe them in full. The most used:

| Endpoint | Field | What it does |
| --- | --- | --- |
| `/search` | `query` | What to search for. Required. |
| `/search` | `include_domains`, `exclude_domains` | Keep results to, or away from, certain sites. |
| `/search` | `recency_minutes`, `after_date`, `before_date` | Limit results by freshness or date. |
| `/search` | `domain_type` | `web`, `news`, or `research_paper`. |
| `/fetch` | `urls` | Pages to read. Required. |
| `/fetch` | `format` | `markdown` (default), `html`, or `json`. |
| `/fetch` | `links`, `image_links` | Also return the links or images on each page. |
| `/fetch` | `include_selectors`, `exclude_selectors` | Keep or drop parts of the page by CSS selector. |

### Run it as a regular Actor

For bulk work, use the **Input** tab instead: choose **Search the web** or **Fetch URLs**, fill in the same fields, and select **Start**. A run reads up to 100 URLs and saves its results to a dataset, so you can schedule it, chain it with other Actors, and connect it to Apify's integrations.

## Output

A request to the server returns the JSON shown above. A regular run saves one dataset item per search result or per page, with the same fields. A URL that failed is saved with its `error` code and is not charged. You can download the dataset in various formats such as JSON, HTML, CSV, or Excel.

## Errors

A request that fails returns a JSON body with a `code` and a `message`, and is not charged:

```json
{ "error": { "code": "invalid_input", "message": "`query` is required." } }
```

| Status | `code` | Meaning |
| --- | --- | --- |
| 400 | `invalid_input` | A field is missing or invalid. The message says which. |
| 429 | `rate_limited` | Too many requests. Retry after the `Retry-After` header. |
| 502 | `upstream_error` | TinyFish could not complete the request. Retry. |
| 504 | `upstream_timeout` | TinyFish did not answer in time. Retry. |

## FAQ and support

**Is it legal to read web pages this way?** This Actor reads pages that are publicly available. The results can still contain personal data, which is protected by the GDPR in the European Union and by other regulations around the world. Do not collect personal data unless you have a legitimate reason to. If you are unsure, consult your lawyers.

**Can TinyFish do more than search and fetch?** Yes. TinyFish also runs web agents that navigate sites, fill in forms, and work inside signed-in accounts. See the [TinyFish documentation](https://docs.tinyfish.ai).

**Where do I report a problem?** Open an issue on the **Issues** tab, or write to [support@tinyfish.io](mailto:support@tinyfish.io).
