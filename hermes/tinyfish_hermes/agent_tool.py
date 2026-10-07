"""``tf_agent``: goal-based TinyFish web automation as a Hermes tool."""

from __future__ import annotations

import json
import time
from typing import Any

from . import rest_client
from .provider import MISSING_KEY_ERROR, _api_key, _is_interrupted

TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
# Hermes' tool batch deadline is 420s; stop polling well before it.
POLL_BUDGET_SECONDS = 300.0
POLL_INTERVAL_SECONDS = 3.0
# Hermes' context pruner targets results above ~8k chars.
MAX_RESULT_CHARS = 12_000

TF_AGENT_SCHEMA: dict[str, Any] = {
    "name": "tf_agent",
    "description": (
        "Run a TinyFish web agent on a real website to complete a goal: navigate, "
        "click, fill forms, and extract data across multiple pages. Use for "
        "multi-step site tasks that web_search/web_extract cannot do. Consumes "
        "TinyFish credits. Returns the agent's result as JSON."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Website URL to start on."},
            "goal": {
                "type": "string",
                "description": (
                    "Plain-language task, including what data to return and its "
                    "shape, e.g. 'Return the first 5 product names and prices as JSON'."
                ),
            },
            "browser_profile": {
                "type": "string",
                "enum": ["lite", "stealth"],
                "description": "Use 'stealth' for sites with bot protection.",
            },
            "proxy_country_code": {
                "type": "string",
                "enum": ["US", "GB", "CA", "DE", "FR", "JP", "AU"],
                "description": "Route through a proxy in this country.",
            },
        },
        "required": ["url", "goal"],
    },
}


def _result(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) <= MAX_RESULT_CHARS:
        return text
    result = json.dumps(payload.get("result"), ensure_ascii=False)
    payload = {**payload, "result": result[:MAX_RESULT_CHARS], "truncated": True}
    return json.dumps(payload, ensure_ascii=False)


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    keys = ("run_id", "status", "result", "error", "streaming_url")
    return {key: run[key] for key in keys if run.get(key) is not None}


def tf_agent(args: dict[str, Any], **_: Any) -> str:
    api_key = _api_key()
    if not api_key:
        return json.dumps({"error": MISSING_KEY_ERROR})
    url = str(args.get("url") or "").strip()
    goal = str(args.get("goal") or "").strip()
    if not url or not goal:
        return json.dumps({"error": "tf_agent needs both url and goal."})

    try:
        started = rest_client.start_run(
            url,
            goal,
            api_key=api_key,
            browser_profile=str(args.get("browser_profile") or "lite"),
            proxy_country_code=args.get("proxy_country_code") or None,
        )
    except rest_client.TinyFishRestError as exc:
        return json.dumps({"error": str(exc)})
    run_id = str(started.get("run_id") or "")
    if not run_id:
        return json.dumps({"error": "TinyFish Agent did not return a run_id."})

    deadline = time.monotonic() + POLL_BUDGET_SECONDS
    run: dict[str, Any] = {"run_id": run_id, "status": "PENDING"}
    while time.monotonic() < deadline:
        if _is_interrupted():
            try:
                rest_client.cancel_run(run_id, api_key=api_key)
            except rest_client.TinyFishRestError:
                pass
            return json.dumps({"run_id": run_id, "status": "CANCELLED"})
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            run = rest_client.get_run(run_id, api_key=api_key)
        except rest_client.TinyFishRestError:
            continue  # a transient poll failure must not abandon a billed run
        if str(run.get("status") or "").upper() in TERMINAL_STATUSES:
            return _result(_summary(run))

    pending = _summary(run)
    pending["note"] = "Still running on TinyFish after 300s; give the user the run_id."
    return _result(pending)
