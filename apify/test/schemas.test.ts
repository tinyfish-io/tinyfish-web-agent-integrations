import { readFileSync } from "node:fs";
import { expect, test } from "vitest";
import { GENERATED } from "../scripts/generate-schemas.js";
import { FETCH_FIELDS, SEARCH_FIELDS } from "../src/options.js";

const read = (path: string) =>
  JSON.parse(readFileSync(new URL(`../${path}`, import.meta.url), "utf8"));

test.each(Object.entries(GENERATED))(
  "%s is up to date (run `npm run build:schemas`)",
  (path, build) => {
    expect(read(path)).toEqual(JSON.parse(JSON.stringify(build())));
  },
);

test("the Actor version is the package's major.minor", () => {
  const [major, minor] = read("package.json").version.split(".");
  expect(read(".actor/actor.json").version).toBe(`${major}.${minor}`);
});

test("the dataset schema describes every field without rejecting others", () => {
  const { fields, views } = read(".actor/dataset_schema.json");
  // A dataset that refused an item would lose a page that was already fetched.
  expect(fields.required).toEqual([]);
  expect(fields.additionalProperties).toBe(true);
  for (const [name, field] of Object.entries<Record<string, unknown>>(
    fields.properties,
  )) {
    expect(field, name).toMatchObject({ nullable: true });
    expect(field, name).toHaveProperty("description");
    expect(field, name).toHaveProperty("example");
  }
  for (const view of Object.values<any>(views)) {
    for (const name of view.transformation.fields) {
      expect(fields.properties, name).toHaveProperty(name);
    }
  }
});

test("a field shared by both modes has one definition", () => {
  const purpose = (fields: readonly { name: string }[]) =>
    fields.find((f) => f.name === "purpose");
  expect(purpose(SEARCH_FIELDS)).toBe(purpose(FETCH_FIELDS));
});
