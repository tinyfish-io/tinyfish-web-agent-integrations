# `output_schema`

Pass `output_schema` when the result feeds anything other than a human reading prose. The same
validator applies across the REST API, SDKs, CLI, Playground, and MCP.

## The schema is the contract

**When the schema and the goal text disagree, the schema wins.** A schema describing a single object
returns a single object even if the goal says "find all 10". This is the single most common mistake.

To return a list, the schema must say so — the top level is always an object, so the list goes in an
array field:

```json
{
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "url": { "type": "string" }
          },
          "required": ["name", "url"]
        }
      }
    },
    "required": ["results"]
  }
}
```

Without the array field, "list 10 tools" returns only the first match.

## Top-level constraints

| Constraint | Rule |
|---|---|
| Shape | Must be a JSON object. If `type` is present it must be `object` |
| Top-level `anyOf` | Not supported — put composition inside object fields |
| Size | Serialized schema ≤ 64KB |
| Nesting depth | Max 10 |
| Boolean schema nodes | A node that is literally `true` or `false` is not supported |
| Nullable | Use `nullable: true`, never `type: ["string", "null"]` |

`type: "boolean"` is fine as a *field* type. What's unsupported is a schema node that is itself the
boolean `true`/`false`.

## Supported types and keywords

| Type | Supports |
|---|---|
| `object` | `properties`, `required`, `propertyOrdering` |
| `array` | `items`, `minItems`, `maxItems` |
| `string` | `enum`, `format` |
| `number` / `integer` | `minimum`, `maximum` |
| `boolean` | as a field type |

The keyword allowlist — anything outside it is **rejected**: `anyOf`, `enum`, `format`, `items`,
`maxItems`, `maximum`, `minItems`, `minimum`, `nullable`, `properties`, `propertyOrdering`, `required`,
`type`.

Rules: `enum` requires `type: "string"` and all values must be strings. `format` requires
`type: "string"`; supported formats are `date`, `date-time`, `duration`, `time`. `items`/`minItems`/
`maxItems` require `type: "array"`. `minimum`/`maximum` require `number` or `integer`.
`propertyOrdering` requires `properties`, values must be unique, and every name must exist in
`properties`. `required` names must exist in `properties`, unless expressed inside an `anyOf` branch.

## Rewrites

| Instead of | Use |
|---|---|
| `oneOf` | `anyOf` |
| `const: "ready"` | `type: "string", enum: ["ready"]` |
| `type: ["string", "null"]` | `type: "string", nullable: true` |
| `type: ["number", "null"]` | `type: "number", nullable: true` |
| `type: ["integer", "null"]` | `type: "integer", nullable: true` |

Commonly rejected: `additionalProperties`, `const`, `example`, `examples`, `oneOf`.

## Errors

Invalid schemas fail with `400` **before execution**, so a bad schema costs nothing but a round trip.
Typical messages:

- `output_schema field "oneOf" is not supported at #. Use "anyOf" instead.`
- `output_schema top-level "anyOf" is not supported at #. Top-level schema must declare "type": "object".`
- `output_schema type arrays are not supported at #/properties/title. Use 'type: "string", nullable: true' instead.`
- `output_schema field "additionalProperties" is not supported at #.`
- `output_schema exceeds the maximum nesting depth of 10.`

These are precise about the path — read the `#/properties/...` pointer and fix that node rather than
rewriting the schema.

## Practical advice

- **Mark optional fields `nullable: true` rather than omitting them from `required`.** An explicit
  `null` tells you the agent looked and found nothing; a missing key is ambiguous between "absent" and
  "never checked".
- **Keep schemas flat.** Depth costs reliability well before it hits the limit of 10.
- **`propertyOrdering`** is worth setting when a human reads the output or you're diffing runs.
- Stored runs include the schema as `output_schema` on `get_run`, so you can confirm what a past run
  was asked for.
