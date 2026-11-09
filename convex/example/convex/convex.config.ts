import { defineApp } from "convex/server";
import { v } from "convex/values";
import tinyfish from "@tiny-fish/convex/convex.config";

const app = defineApp({
  env: {
    TINYFISH_API_KEY: v.string(),
    // Point at a mock or proxy in tests. Default to the public endpoints.
    TINYFISH_SEARCH_URL: v.optional(v.string()),
    TINYFISH_FETCH_URL: v.optional(v.string()),
  },
});

app.use(tinyfish, {
  env: {
    TINYFISH_API_KEY: app.env.TINYFISH_API_KEY,
    TINYFISH_SEARCH_URL: app.env.TINYFISH_SEARCH_URL,
    TINYFISH_FETCH_URL: app.env.TINYFISH_FETCH_URL,
  },
});

export default app;
