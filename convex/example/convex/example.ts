import { v } from "convex/values";
import { paginationOptsValidator } from "convex/server";
import { TinyFish, jobCompleteArgs } from "@tiny-fish/convex";
import {
  action,
  internalMutation,
  mutation,
  query,
  type QueryCtx,
} from "./_generated/server.js";
import { components, internal } from "./_generated/api.js";
import { requireUser } from "./auth.js";

const tinyfish = new TinyFish(components.tinyfish);

/**
 * Job-scoped operations go through this. Without it, anyone could read,
 * cancel, or delete anyone else's job by guessing an id.
 */
async function requireOwnedJob(ctx: QueryCtx, jobId: string): Promise<string> {
  const userId = await requireUser(ctx);
  const owner = await ctx.db
    .query("jobOwners")
    .withIndex("jobId", (q) => q.eq("jobId", jobId))
    .first();
  if (!owner || owner.userId !== userId) throw new Error("No such job.");
  return userId;
}

// ---------------------------------------------------------------------------
// One-shot calls. A production app should also rate-limit these, e.g. with
// @convex-dev/rate-limiter.
// ---------------------------------------------------------------------------

export const searchWeb = action({
  args: { query: v.string() },
  handler: async (ctx, args) => {
    await requireUser(ctx);
    const { results } = await tinyfish.search(ctx, args.query, {
      purpose: "Answer a user's question with cited sources",
    });
    return results.map(({ title, snippet, url }) => ({ title, snippet, url }));
  },
});

export const readPage = action({
  args: { url: v.string() },
  handler: async (ctx, args) => {
    await requireUser(ctx);
    const { results, errors } = await tinyfish.fetch(ctx, args.url, {
      // Keep the page small enough to hand to a model.
      maxCharacters: 20_000,
    });
    if (errors.length > 0) return { ok: false as const, error: errors[0].error };
    return { ok: true as const, page: results[0] };
  },
});

// ---------------------------------------------------------------------------
// Durable jobs: these return right away and the UI subscribes to the result.
// ---------------------------------------------------------------------------

/** Research a topic: search, read the top results, then save a brief. */
export const research = mutation({
  args: { query: v.string() },
  handler: async (ctx, args) => {
    const userId = await requireUser(ctx);
    const jobId = await tinyfish.startSearchAndFetch(ctx, {
      query: args.query,
      maxResults: 5,
      fetchOptions: { maxCharacters: 20_000 },
      onComplete: internal.example.saveBrief,
      context: { userId, query: args.query },
    });
    await ctx.db.insert("jobOwners", { jobId, userId });
    return jobId;
  },
});

/** Read a list of URLs in the background, e.g. to index them. */
export const readMany = mutation({
  args: { urls: v.array(v.string()) },
  handler: async (ctx, args) => {
    const userId = await requireUser(ctx);
    const jobId = await tinyfish.startFetch(ctx, { urls: args.urls });
    await ctx.db.insert("jobOwners", { jobId, userId });
    return jobId;
  },
});

/** Runs once when a research job ends, in the same transaction as its data. */
export const saveBrief = internalMutation({
  args: jobCompleteArgs,
  handler: async (ctx, args) => {
    // `context` is whatever the job was started with; don't assume its shape.
    if (!args.context?.userId) return null;
    // One read is enough here: `research` asks for 5 results and a search job
    // fetches at most 10. Paginate if you reuse this for larger `startFetch` jobs.
    const { page } = await tinyfish.listPages(ctx, {
      jobId: args.jobId,
      paginationOpts: { numItems: 10, cursor: null },
    });
    await ctx.db.insert("briefs", {
      jobId: args.jobId,
      userId: args.context.userId,
      query: args.context.query,
      status: args.status,
      sources: page
        .filter((p) => p.status === "completed")
        .map((p) => ({
          url: p.final_url ?? p.url,
          title: p.title,
          snippet: p.snippet,
        })),
      failures: page
        .filter((p) => p.status === "failed")
        .map((p) => ({ url: p.url, error: p.error ?? "unknown_error" })),
    });
    return null;
  },
});

/** Live job progress. Subscribe with `useQuery`. */
export const job = query({
  args: { jobId: v.string() },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    return await tinyfish.getJob(ctx, args.jobId);
  },
});

/** Pages as they land. Subscribe with `usePaginatedQuery`. */
export const pages = query({
  args: { jobId: v.string(), paginationOpts: paginationOptsValidator },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    return await tinyfish.listPages(ctx, args);
  },
});

export const brief = query({
  args: { jobId: v.string() },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    return await ctx.db
      .query("briefs")
      .withIndex("jobId", (q) => q.eq("jobId", args.jobId))
      .first();
  },
});

export const cancel = mutation({
  args: { jobId: v.string() },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    return await tinyfish.cancelJob(ctx, args.jobId);
  },
});

export const remove = mutation({
  args: { jobId: v.string() },
  handler: async (ctx, args) => {
    await requireOwnedJob(ctx, args.jobId);
    const owner = await ctx.db
      .query("jobOwners")
      .withIndex("jobId", (q) => q.eq("jobId", args.jobId))
      .first();
    if (owner) await ctx.db.delete(owner._id);
    return await tinyfish.deleteJob(ctx, args.jobId);
  },
});
