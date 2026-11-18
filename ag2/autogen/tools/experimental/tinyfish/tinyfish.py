# Copyright (c) 2023 - 2025, AG2ai, Inc., AG2ai open-source projects maintainers and core contributors
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Annotated, Any, Optional

from autogen.doc_utils import export_module
from autogen.import_utils import optional_import_block, require_optional_import
from autogen.tools import Tool

logger = logging.getLogger(__name__)

with optional_import_block():
    from tinyfish import (
        BrowserProfile,
        ProxyConfig,
        ProxyCountryCode,
        RunStatus,
        SortDirection,
        TinyFish,
    )

__all__ = ["TinyFishToolkit"]

_INTEGRATION_NAME = "ag2"


def _ensure_integration_tag() -> None:
    """Set the default TinyFish integration tag for request attribution."""
    os.environ.setdefault("TF_API_INTEGRATION", _INTEGRATION_NAME)


def _json_dumps(value: Any) -> str:
    """Serialize SDK responses and plain Python values for agent-friendly output."""
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"))

    if isinstance(value, dict):
        return json.dumps(value)

    if isinstance(value, list):
        return json.dumps(value)

    return json.dumps(value, default=str)


@require_optional_import(["tinyfish"], "tinyfish")
@export_module("autogen.tools.experimental")
class TinyFishToolkit:
    """A toolkit providing multiple TinyFish Web Agent tools for AG2 agents.

    TinyFish Web Agent navigates real websites, extracts structured data,
    fills forms, clicks buttons, and executes multi-step workflows — all
    described in plain English. No CSS selectors or XPath needed.

    This toolkit provides seven tools:

    - **tinyfish_web_agent**: Run a web automation synchronously and return results.
    - **tinyfish_web_agent_async**: Queue an automation and return a run ID immediately.
    - **tinyfish_get_run**: Check the status and result of a run by ID.
    - **tinyfish_list_runs**: List recent automation runs with optional filtering.
    - **tinyfish_search**: Search the web and return ranked results.
    - **tinyfish_fetch**: Fetch readable page contents from one or more URLs.
    - **tinyfish_create_browser_session**: Create a remote browser session.

    Install the optional dependency with: ``pip install ag2[tinyfish]``

    Args:
        api_key: TinyFish API key. If not provided, reads from the
            ``TINYFISH_API_KEY`` environment variable.
        browser_profile: Browser execution mode. ``"lite"`` (default) is
            fast for standard sites. ``"stealth"`` enables anti-detection
            for sites with bot protection (Cloudflare, CAPTCHAs, etc.).
        proxy_country: Optional proxy country code (``"US"``, ``"GB"``,
            ``"CA"``, ``"DE"``, ``"FR"``, ``"JP"``, ``"AU"``). When set,
            requests are routed through the specified country.

    Example:
        .. code-block:: python

            from autogen import ConversableAgent, LLMConfig
            from autogen.tools.experimental import TinyFishToolkit

            toolkit = TinyFishToolkit()

            assistant = ConversableAgent(
                name="assistant",
                llm_config=llm_config,
            )
            user_proxy = ConversableAgent(
                name="user_proxy",
                human_input_mode="NEVER",
            )

            toolkit.register_for_llm(assistant)
            toolkit.register_for_execution(user_proxy)

            user_proxy.initiate_chat(
                assistant,
                message="Extract product names and prices from https://scrapeme.live/shop/",
            )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        browser_profile: str = "lite",
        proxy_country: Optional[str] = None,
    ) -> None:
        try:
            bp = BrowserProfile(browser_profile)
        except ValueError:
            raise ValueError(
                f"Invalid browser_profile '{browser_profile}'. Use 'lite' or 'stealth'."
            )

        proxy_config = None
        if proxy_country:
            try:
                proxy_config = ProxyConfig(
                    enabled=True,
                    country_code=ProxyCountryCode(proxy_country),
                )
            except ValueError:
                raise ValueError(
                    f"Invalid proxy_country '{proxy_country}'. "
                    f"Use one of: US, GB, CA, DE, FR, JP, AU."
                )

        _ensure_integration_tag()
        client = TinyFish(api_key=api_key) if api_key else TinyFish()

        # --- Tool: Run (sync) ---

        def run_web_automation(
            url: Annotated[
                str,
                "The target website URL to automate (must start with http:// or https://).",
            ],
            goal: Annotated[
                str,
                "Natural language description of what to accomplish on the website. "
                "Be specific: e.g. 'Extract all product names and prices as JSON' or "
                "'Fill the contact form with name John Doe and email john@example.com, then click Submit'.",
            ],
        ) -> str:
            """Run a web automation synchronously and return the result."""
            try:
                if not url.startswith(("http://", "https://")):
                    return "Invalid url. Must start with http:// or https://."
                kwargs: dict = {"url": url, "goal": goal, "browser_profile": bp}
                if proxy_config:
                    kwargs["proxy_config"] = proxy_config

                result = client.agent.run(**kwargs)

                if result.status == RunStatus.COMPLETED:
                    if result.result is not None:
                        return json.dumps(result.result)
                    return "Automation completed successfully with no result data."

                error_msg = getattr(result, "error", None) or "Unknown error"
                return f"Automation failed: {error_msg}"
            except Exception as e:
                logger.error("Error running web automation", exc_info=True)
                return f"Error running web automation: {e}"

        # --- Tool: Queue (async) ---

        def queue_web_automation(
            url: Annotated[
                str,
                "The target website URL to automate (must start with http:// or https://).",
            ],
            goal: Annotated[
                str,
                "Natural language description of what to accomplish on the website.",
            ],
        ) -> str:
            """Start a web automation asynchronously and return the run ID."""
            try:
                if not url.startswith(("http://", "https://")):
                    return "Invalid url. Must start with http:// or https://."
                kwargs: dict = {"url": url, "goal": goal, "browser_profile": bp}
                if proxy_config:
                    kwargs["proxy_config"] = proxy_config

                result = client.agent.queue(**kwargs)
                run_id = result.run_id
                return f"Automation queued. run_id: {run_id}. Use tinyfish_get_run to check status and get results."
            except Exception as e:
                logger.error("Error queuing web automation", exc_info=True)
                return f"Error queuing web automation: {e}"

        # --- Tool: Get Run ---

        def get_run(
            run_id: Annotated[str, "The unique run ID to look up."],
        ) -> str:
            """Get the status and result of a TinyFish automation run."""
            try:
                run = client.runs.get(run_id)

                parts = [f"Status: {run.status}"]

                streaming_url = getattr(run, "streaming_url", None) or getattr(run, "streamingUrl", None)
                if streaming_url:
                    parts.append(f"Live view: {streaming_url}")

                result = getattr(run, "result", None)
                if result is not None:
                    parts.append(f"Result: {json.dumps(result)}")

                error = getattr(run, "error", None)
                if error:
                    error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                    parts.append(f"Error: {error_msg}")

                return "\n".join(parts)
            except Exception as e:
                logger.error("Error getting run", exc_info=True)
                return f"Error getting run: {e}"

        # --- Tool: List Runs ---

        def list_runs(
            status: Annotated[
                Optional[str],
                "Filter by status: PENDING, RUNNING, COMPLETED, FAILED, or CANCELLED. Leave empty for all.",
            ] = None,
            limit: Annotated[
                int,
                "Maximum number of runs to return (1-100).",
            ] = 20,
        ) -> str:
            """List recent TinyFish automation runs."""
            try:
                kwargs: dict = {"limit": max(1, min(limit, 100))}
                if status:
                    kwargs["status"] = RunStatus(status)

                response = client.runs.list(**kwargs)
                runs = response.runs if hasattr(response, "runs") else []

                if not runs:
                    return "No runs found."

                lines = []
                for run in runs:
                    run_id = getattr(run, "run_id", "?")
                    run_status = getattr(run, "status", "?")
                    run_url = getattr(run, "url", "?")
                    run_goal = str(getattr(run, "goal", "") or "")
                    goal_preview = (run_goal[:60] + "...") if len(run_goal) > 60 else run_goal
                    lines.append(f"- {run_id} | {run_status} | {run_url} | {goal_preview}")

                return f"Found {len(runs)} runs:\n" + "\n".join(lines)
            except Exception as e:
                logger.error("Error listing runs", exc_info=True)
                return f"Error listing runs: {e}"

        # --- Tool: Search ---

        def search_web(
            query: Annotated[str, "The web search query to run."],
            location: Annotated[
                Optional[str],
                'Optional search location, such as "United States", "Singapore", or "London".',
            ] = None,
            language: Annotated[
                Optional[str],
                'Optional language code, such as "en", "es", or "fr".',
            ] = None,
        ) -> str:
            """Search the web with TinyFish and return ranked results."""
            try:
                response = client.search.query(query, location=location, language=language)
                return _json_dumps(response)
            except Exception as e:
                logger.error("Error searching web", exc_info=True)
                return f"Error searching web: {e}"

        # --- Tool: Fetch ---

        def fetch_web_pages(
            urls: Annotated[list[str], "One to ten URLs to fetch and extract content from."],
            format: Annotated[
                str,
                'Output format: "markdown", "html", or "json".',
            ] = "markdown",
            links: Annotated[
                bool,
                "Whether to include extracted links in the response.",
            ] = False,
            image_links: Annotated[
                bool,
                "Whether to include extracted image links in the response.",
            ] = False,
        ) -> str:
            """Fetch readable content from web pages."""
            try:
                if not 1 <= len(urls) <= 10:
                    return "Invalid urls. Provide between 1 and 10 URLs."
                if format not in {"markdown", "html", "json"}:
                    return 'Invalid format. Use "markdown", "html", or "json".'

                response = client.fetch.get_contents(
                    urls,
                    format=format,
                    links=links,
                    image_links=image_links,
                )
                return _json_dumps(response)
            except Exception as e:
                logger.error("Error fetching web pages", exc_info=True)
                return f"Error fetching web pages: {e}"

        # --- Tool: Create Browser Session ---

        def create_browser_session(
            url: Annotated[
                Optional[str],
                "Optional URL to open when the remote browser session starts.",
            ] = None,
            timeout_seconds: Annotated[
                Optional[int],
                "Optional inactivity timeout in seconds.",
            ] = None,
        ) -> str:
            """Create a remote browser session and return connection details."""
            try:
                response = client.browser.sessions.create(url=url, timeout_seconds=timeout_seconds)
                return _json_dumps(response)
            except Exception as e:
                logger.error("Error creating browser session", exc_info=True)
                return f"Error creating browser session: {e}"

        # --- Build Tool instances ---

        self._tools = [
            Tool(
                name="tinyfish_web_agent",
                description=(
                    "Automate any website using natural language. Provide a URL and describe "
                    "what you want to accomplish — extract data, fill forms, click buttons, "
                    "navigate pages, and more. Waits for completion and returns structured "
                    "JSON results. Best for tasks that complete in under 60 seconds."
                ),
                func_or_tool=run_web_automation,
            ),
            Tool(
                name="tinyfish_web_agent_async",
                description=(
                    "Start a web automation asynchronously without waiting for completion. "
                    "Returns a run_id immediately. Use tinyfish_get_run to poll for status "
                    "and results. Best for long-running tasks or batch processing."
                ),
                func_or_tool=queue_web_automation,
            ),
            Tool(
                name="tinyfish_get_run",
                description=(
                    "Get the status and result of a TinyFish automation run by its run_id. "
                    "Returns status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED) and "
                    "result data when available. Use after tinyfish_web_agent_async."
                ),
                func_or_tool=get_run,
            ),
            Tool(
                name="tinyfish_list_runs",
                description=(
                    "List recent TinyFish automation runs. Optionally filter by status. "
                    "Returns run IDs, statuses, URLs, and goal previews."
                ),
                func_or_tool=list_runs,
            ),
            Tool(
                name="tinyfish_search",
                description=(
                    "Search the web using TinyFish and return ranked results with titles, "
                    "URLs, snippets, and metadata. Best when you need to discover relevant pages."
                ),
                func_or_tool=search_web,
            ),
            Tool(
                name="tinyfish_fetch",
                description=(
                    "Fetch and extract readable content from one or more URLs. Supports markdown, "
                    "HTML, or JSON output and optional link extraction. Best after search when you "
                    "need page contents."
                ),
                func_or_tool=fetch_web_pages,
            ),
            Tool(
                name="tinyfish_create_browser_session",
                description=(
                    "Create a remote browser session and return the session ID, CDP URL, and base URL. "
                    "Best when a workflow needs direct browser control."
                ),
                func_or_tool=create_browser_session,
            ),
        ]

    @property
    def tools(self) -> list[Tool]:
        """Return all tools in this toolkit."""
        return list(self._tools)

    def register_for_llm(self, agent: "ConversableAgent") -> None:
        """Register all tools for LLM recommendation with the given agent."""
        for tool in self._tools:
            tool.register_for_llm(agent)

    def register_for_execution(self, agent: "ConversableAgent") -> None:
        """Register all tools for execution with the given agent."""
        for tool in self._tools:
            tool.register_for_execution(agent)
