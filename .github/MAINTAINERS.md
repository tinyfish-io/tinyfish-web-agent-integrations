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

## Kiro power

`kiro/tinyfish/plugin.json`'s `description` names the TinyFish MCP tools and their required arguments on purpose. Kiro cuts a power's activation output at 30,000 characters and shows the agent only the first and last 500, and the hosted server's tool list is about 38,000, so without those names the agent guesses tool names such as `fetch`. Kiro always shows the `description` in full. When a tool used there is renamed or gains a required argument on the server, update the description and bump `version` in `kiro/tinyfish/plugin.json` and `X-TF-Client-Version` in `kiro/tinyfish/mcp.json` together; CI checks that the two versions match. The power lives in `kiro/tinyfish/`, not `kiro/`, because the Kiro IDE names an imported power after its folder (`kiro` would name the server `power-kiro-tinyfish`); Kiro CLI uses `plugin.json`'s `name`.
