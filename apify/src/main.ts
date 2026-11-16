import { Actor, log } from "apify";
import { chargeRequest } from "./charging.js";
import { InvalidInput } from "./options.js";
import { runFromInput } from "./run.js";
import { createServer } from "./server.js";
import {
  fetchPages,
  publicFailure,
  search,
  TinyFishError,
} from "./tinyfish.js";

await Actor.init();

if (!process.env.TINYFISH_API_KEY) {
  // Nothing works without the key, so stop instead of failing every request.
  await Actor.fail(
    "TINYFISH_API_KEY is not set. Add it as a secret environment variable of the Actor.",
  );
}

if (Actor.config.get("metaOrigin") === "STANDBY") {
  // Server interface: stay up and answer HTTP requests until Apify stops the run.
  const server = createServer({ search, fetchPages, charge: chargeRequest });
  // Let requests in flight finish, and be charged, before the run is stopped.
  Actor.on("aborting", async () => {
    await new Promise((resolve) => server.close(resolve));
  });
  const port = Actor.config.get("containerPort");
  server.listen(port, () => log.info(`Listening on port ${port}`));
} else {
  // Input interface: do one job, store the results in the dataset, and exit.
  const charging = Actor.getChargingManager();
  try {
    const message = await runFromInput(await Actor.getInput(), {
      search,
      fetchPages,
      pushData: (items, eventName) =>
        eventName ? Actor.pushData(items, eventName) : Actor.pushData(items),
      charge: (eventName) => Actor.charge({ eventName }),
      chargeable: (eventName) =>
        charging.calculateMaxEventChargeCountWithinLimit(eventName),
    });
    await Actor.exit(message);
  } catch (error) {
    if (error instanceof InvalidInput) await Actor.fail(error.message);
    if (error instanceof TinyFishError) {
      log.error(error.message, { apiCode: error.apiCode });
      await Actor.fail(publicFailure(error).message);
    }
    throw error;
  }
}
