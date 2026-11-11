"""Live checks run by e2e.sh with Hermes' own Python, after the plugin is installed."""

from __future__ import annotations

import asyncio
import json
import sys

from hermes_cli.plugins import discover_plugins


def web() -> None:
    from tools.web_tools import web_extract_tool, web_search_tool

    search = json.loads(web_search_tool("TinyFish web agent", limit=2))
    assert search["success"] and search["data"]["web"], search
    extract = json.loads(
        asyncio.run(web_extract_tool(["https://example.com"], "markdown"))
    )
    page = extract["results"][0]
    assert not page.get("error") and "Example Domain" in page["title"], page
    print("search + extract OK")


def products() -> None:
    from tools.registry import registry
    from tools.skills_tool import skills_list

    monitors = json.loads(registry.dispatch("tinyfish_list_monitors", {}))
    assert "error" not in monitors, monitors
    # Datasets and Research are flag-gated per account; a clean refusal also passes.
    for tool in ("tinyfish_list_datasets", "tinyfish_list_deep_research"):
        out = json.loads(registry.dispatch(tool, {}))
        refused = "isn't enabled" in out.get("next_action", "")
        assert "error" not in out or refused, (tool, out)
    names = {s["name"] for s in json.loads(skills_list())["skills"]}
    for skill in ("tinyfish-monitor", "tinyfish-datasets", "tinyfish-websearch"):
        assert f"tinyfish:{skill}" in names, (skill, sorted(names))
    print("product tools + skills OK")


if __name__ == "__main__":
    discover_plugins()
    {"web": web, "products": products}[sys.argv[1]]()
