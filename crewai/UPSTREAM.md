# Contributing this integration upstream to `crewai-tools`

This package is intentionally built to match the official
[`crewai-tools` BUILDING_TOOLS.md](https://github.com/crewAIInc/crewai-tools/blob/main/BUILDING_TOOLS.md)
conventions, so it can be contributed into the main repository with minimal changes.

## Conventions already followed

- Each tool subclasses `crewai.tools.BaseTool` with a Pydantic `args_schema`.
- `name` / `description` are agent-facing and explain *when* to use the tool.
- Optional SDK dependency declared via `package_dependencies = ["tinyfish"]` and
  **lazy-imported** so the base install stays light.
- `env_vars = [EnvVar(name="TINYFISH_API_KEY", required=True)]`.
- Clear, graceful error strings instead of raised exceptions inside `_run`.
- `_arun` provided, delegating to `_run`.
- Tests in `tests/` mock the client (no network, no key required in CI).
- SDK calls are version-skew tolerant (`supported_kwargs`) so a param the
  installed SDK doesn't accept is dropped instead of crashing the agent.

## Mapping into the crewai-tools tree

In `crewai-tools`, tools live at `crewai_tools/tools/<tool_name>/`. Suggested layout:

```
crewai_tools/tools/tinyfish_search_tool/
    __init__.py
    tinyfish_search_tool.py      # from src/crewai_tinyfish/tinyfish_search_tool.py
    README.md
crewai_tools/tools/tinyfish_fetch_tool/
    ...
crewai_tools/tools/tinyfish_agent_tool/
    ...
crewai_tools/tools/tinyfish_browser_tool/
    ...
```

Steps:

1. Copy each `tinyfish_*_tool.py` into its own folder under `crewai_tools/tools/`.
2. Inline the helpers from `_client.py` / `_serde.py` into each tool (the upstream
   repo prefers self-contained tool modules), or add them as a small shared
   `crewai_tools/tools/tinyfish_*/_shared.py`.
3. Export the classes from `crewai_tools/tools/__init__.py` and
   `crewai_tools/__init__.py`.
4. Register the optional dependency in the repo's `pyproject.toml` under
   `[project.optional-dependencies]`:
   ```toml
   tinyfish = ["tinyfish>=0.2.6"]
   ```
5. Add a short `README.md` per tool (the sections in this repo's README can be split).
6. `uv run pytest` and run the repo's lint/type checks before opening the PR.

## Standalone distribution

Until/unless merged upstream, this repo publishes as `crewai-tinyfish` on PyPI and
is used via `from crewai_tinyfish import TinyFishSearchTool`. The import path is the
only difference from the upstream `from crewai_tools import TinyFishSearchTool`.
