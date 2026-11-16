import { createRequire } from "node:module";

/**
 * Read from package.json, so the version sent as `X-TF-Client-Version` is
 * always the version of the package that is running.
 */
export const VERSION: string = createRequire(import.meta.url)(
  "../package.json",
).version;
