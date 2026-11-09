/// <reference types="vite/client" />
import type { TestConvex } from "convex-test";
import type { GenericSchema, SchemaDefinition } from "convex/server";
import schema from "./component/schema.js";

const modules = import.meta.glob("./component/**/*.ts");

/**
 * Register the TinyFish component with a `convexTest` instance, so app tests
 * can exercise code that calls it.
 *
 * ```ts
 * import tinyfish from "@tiny-fish/convex/test";
 *
 * const t = convexTest(schema, modules);
 * tinyfish.register(t);
 * ```
 */
export function register(
  t: TestConvex<SchemaDefinition<GenericSchema, boolean>>,
  name: string = "tinyfish",
) {
  t.registerComponent(name, schema, modules);
}

export default { register, schema, modules };
