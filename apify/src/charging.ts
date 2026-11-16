import { randomUUID } from "node:crypto";
import { Actor } from "apify";

/**
 * The pay-per-event events this Actor charges. Each must exist under the same
 * name in the Actor's pricing in Apify Console.
 *
 * - `search`: one search that returned at least one result.
 * - `fetch`: one page that was fetched. A URL that failed is never charged.
 */
export type EventName = "search" | "fetch";

/**
 * Charge the user who sent a request to the server interface.
 *
 * `requestId` is the request's `X-Actor-Request-ID` header. In a multi-tenant
 * Server Actor the run belongs to TinyFish and serves every user, so the ID is
 * what tells Apify whom to charge; `Actor.charge()` cannot carry it. Call this
 * before sending the response: the ID stops working once the request ends.
 *
 * Does nothing outside the platform or while the Actor has no pay-per-event
 * pricing, so local runs and a private Actor under test work unpriced.
 */
export async function chargeRequest(
  eventName: EventName,
  count: number,
  requestId: string | undefined,
): Promise<void> {
  if (count <= 0) return;
  const runId = Actor.config.get("actorRunId");
  const { isPayPerEvent } = Actor.getChargingManager().getPricingInfo();
  if (!Actor.isAtHome() || !runId || !isPayPerEvent) return;
  await Actor.apifyClient.run(runId).charge({
    eventName,
    count,
    requestId,
    // The client retries with this same key, so a retry is never a second charge.
    idempotencyKey: `${requestId ?? randomUUID()}:${eventName}`,
  });
}
