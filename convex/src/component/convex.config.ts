import { defineComponent } from "convex/server";
import { v } from "convex/values";

export default defineComponent("tinyfish", {
  env: {
    /** TinyFish API key. Create one at https://agent.tinyfish.ai/api-keys. */
    TINYFISH_API_KEY: v.string(),
    /** Override the Search endpoint. Defaults to https://api.search.tinyfish.ai. */
    TINYFISH_SEARCH_URL: v.optional(v.string()),
    /** Override the Fetch endpoint. Defaults to https://api.fetch.tinyfish.ai. */
    TINYFISH_FETCH_URL: v.optional(v.string()),
  },
});
