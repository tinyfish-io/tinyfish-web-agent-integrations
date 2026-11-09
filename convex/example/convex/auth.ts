import type { Auth } from "convex/server";

/**
 * Every endpoint that spends TinyFish allowance or reads a job goes through
 * this. Swap it for your auth provider's check; the point is that the gate
 * lives in the app, because components can't see `ctx.auth`.
 */
export async function requireUser(ctx: { auth: Auth }): Promise<string> {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Sign in to use this.");
  return identity.subject;
}
