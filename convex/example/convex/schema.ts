import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  /**
   * Who started which job. The component has no notion of ownership, so the
   * app records it and checks it before any job is read, cancelled, or deleted.
   */
  jobOwners: defineTable({
    jobId: v.string(),
    userId: v.string(),
  })
    .index("jobId", ["jobId"])
    .index("userId", ["userId"]),

  /** A finished research job, summarized for the app by `onComplete`. */
  briefs: defineTable({
    jobId: v.string(),
    userId: v.string(),
    query: v.string(),
    status: v.string(),
    /** One entry per page that was read, so every claim can cite a link. */
    sources: v.array(
      v.object({
        url: v.string(),
        title: v.optional(v.string()),
        snippet: v.optional(v.string()),
      }),
    ),
    /** URLs that could not be read, and why. */
    failures: v.array(v.object({ url: v.string(), error: v.string() })),
  }).index("jobId", ["jobId"]),
});
