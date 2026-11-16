# Maintainer notes

This file is for repository maintainers. Do not copy release-process notes into an integration package `README.md`: package READMEs are used as PyPI project descriptions.

## Python integration releases

Python integration publish workflows do not bump package versions automatically. Each workflow reads the package name and version from that integration's `pyproject.toml`, checks PyPI for that exact version, and publishes only when the version does not already exist.

To publish a new version:

1. Update the package version in the relevant `pyproject.toml`.
2. Commit the version bump with the code change.
3. Merge to `main`.
4. Let the push-to-`main` publish workflow run.

Current Python package version files:

| Integration | Package | Version file |
| --- | --- | --- |
| Google ADK | `tinyfish-adk` | `google-adk/pyproject.toml` |
| LangChain | `langchain-tinyfish` | `langchain/pyproject.toml` |

PyPI versions are immutable. If a version has already been published, bump to a new version such as a patch release before merging.

The publish workflows use the repository `PYPI_API_TOKEN` Actions secret provisioned through `github-control`; never commit token values or package credentials.

## npm integration releases

npm publish workflows follow the same rule as the Python ones: no automatic version bumps. Each workflow reads the name and version from the package's `package.json`, checks npm for that exact version, and publishes only when it does not exist yet. Publishing uses npm Trusted Publisher (OIDC), so there is no token secret. A new package needs one manual first publish, because a trusted publisher cannot be configured on a package that does not exist yet:

1. In the package folder, run `npm ci`, the package's verify script (`npm run verify` for Convex), then `npm publish --access public`.
2. On npmjs.com, open the package's Settings → Trusted Publisher → GitHub Actions and name this repository and the package's publish workflow (for Convex, `convex-publish.yml`). If the form asks which publish methods to allow, allow `npm publish`: these workflows publish directly rather than through staged publishing.
3. Every release after that is the publish workflow, on a version bump.

| Integration | Package | Version files |
| --- | --- | --- |
| Convex | `@tiny-fish/convex` | `convex/package.json` and `convex/src/component/version.ts` |
| Pi | `@tiny-fish/pi` | `pi/package.json` |

For Convex, bump both version files together: `version.ts` is what the component sends as `X-TF-Client-Version`, and a test fails if the two differ. After changing anything under `convex/src/component`, run `npm run build:codegen` in `convex/` and commit the regenerated `_generated` files; CI builds from the committed copies and has no Convex deployment.

## Kiro power

`kiro/tinyfish/plugin.json`'s `description` names the TinyFish MCP tools and their required arguments on purpose. Kiro cuts a power's activation output at 30,000 characters and shows the agent only the first and last 500, and the hosted server's tool list is about 38,000, so without those names the agent guesses tool names such as `fetch`. Kiro always shows the `description` in full. When a tool used there is renamed or gains a required argument on the server, update the description and bump `version` in `kiro/tinyfish/plugin.json` and `X-TF-Client-Version` in `kiro/tinyfish/mcp.json` together; CI checks that the two versions match. The power lives in `kiro/tinyfish/`, not `kiro/`, because the Kiro IDE names an imported power after its folder (`kiro` would name the server `power-kiro-tinyfish`); Kiro CLI uses `plugin.json`'s `name`.

## Apify Actor

`apify/` is the source of the `search-and-fetch` Actor in the `tinyfish` organization on Apify. `apify/README.md` is the Actor's Apify Store page, so keep maintainer notes here.

The Actor has two interfaces that share one set of fields. The server interface (a Server Actor, formerly Standby mode) answers `GET|POST /search` and `/fetch`; the input interface does one search or one batch of fetches per run and writes to the dataset. `src/options.ts` is the single definition of those fields. `.actor/input_schema.json` and `.actor/openapi.json` are generated from it: after changing a field, run `npm run build:schemas` in `apify/` and commit the result. Do not edit the two files by hand; a test fails when they are out of date.

### Deploying

Deploys are manual for now. Log the Apify CLI in with the `tinyfish` organization's API token (Console → switch to the organization → Settings → API & Integrations), not a personal one, then in `apify/` run `npm run verify` and `apify push`. Pushing with a personal login creates the Actor under that person instead.

### One-time setup in Apify Console

- **API key.** Add `TINYFISH_API_KEY` under the Actor's Source → Environment variables with **Secret** enabled. It is deliberately not in `.actor/actor.json`: variables listed there replace the ones set in Console on every push, and would need the key in each pusher's local secret store.
- **Pricing.** Pay per event, with two events named exactly `search` and `fetch` (see `src/charging.ts` for when each is charged). Remove the synthetic `apify-default-dataset-item` event, or every search result row of a regular run is charged on top of the `search` event.
- **Tenancy.** Settings → Server → **Multi-tenant**, once pricing is set. The switch reaches every user within two minutes. Runs then happen in the `tinyfish` account, and each request is charged to its sender through the `X-Actor-Request-ID` header.

While the Actor has no pay-per-event pricing, charging is skipped, so a private copy can be tested unpriced. Requests from the owner's account are never charged, so test charging from a second account.

### Versions

Bump `version` in `apify/package.json`, set `version` in `apify/.actor/actor.json` to its major.minor, and run `npm run build:schemas` (the OpenAPI document carries the version). Tests fail if any of the three disagree. `X-TF-Client-Version` is read from `package.json` at runtime.

### Running locally

`apify run` starts a regular run from `storage/key_value_stores/default/INPUT.json`. `APIFY_META_ORIGIN=STANDBY apify run` starts the server on port 4321. Both need `TINYFISH_API_KEY` in the environment.
