"""TinyFish Monitor tools: watch a page or topic on a schedule."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from . import rest_client
from .tool_helpers import given, required, schema, with_key

_request = partial(rest_client.agent_request, service="TinyFish Monitors")

_MONITOR_ID = {
    "type": "string",
    "description": "Id returned by tinyfish_list_monitors or tinyfish_create_monitor.",
}
_ID_ONLY = {"monitor_id": _MONITOR_ID}
_CRON = {
    "type": "string",
    "description": (
        "Five-field cron expression, evaluated in UTC by default. Prefix with "
        "`CRON_TZ=<IANA zone>` (e.g. `CRON_TZ=America/New_York 0 9 * * 1-5`) to run "
        "in a timezone. Search Monitors run at most every 30 minutes."
    ),
}
_NAME = {"type": "string", "description": "Optional name for this Monitor."}
_WEBHOOK = {
    "type": "string",
    "description": "Optional URL that receives each scheduled run's results.",
}
_PURPOSE = {
    "type": "string",
    "description": (
        "Optional plain-language description of the change that matters, "
        'e.g. "the price drops".'
    ),
}

CREATE_SCHEMA = schema(
    "tinyfish_create_monitor",
    "Use when the user asks to monitor a webpage for changes or subscribe to "
    "updates about a web topic. Set type to fetch for a known URL or search for a "
    "topic. Creates the recurring Monitor and immediately returns its baseline "
    "result. Each completed run, including the baseline, is billed $0.005 to the "
    "wallet plus its one Search or Fetch, billed like a direct call; failed runs "
    "are free. For a one-time read, use web_extract instead.",
    {
        "type": {
            "type": "string",
            "enum": ["search", "fetch"],
            "description": "Use search for a topic or fetch for a known webpage URL.",
        },
        "config": {
            "type": "object",
            "description": "Set query for a search Monitor or url for a fetch Monitor.",
            "properties": {
                "query": {"type": "string", "description": "Topic to monitor."},
                "recency_minutes": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional Search freshness window in minutes.",
                },
                "result_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Results per run (1-10). Defaults to 10.",
                },
                "url": {
                    "type": "string",
                    "description": "Public webpage URL to monitor.",
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "html", "json"],
                    "description": "Fetch output format.",
                },
                "links": {
                    "type": "boolean",
                    "description": "Include links from the webpage.",
                },
                "image_links": {
                    "type": "boolean",
                    "description": "Include image links from the webpage.",
                },
            },
        },
        "schedule_cron": _CRON,
        "name": _NAME,
        "webhook_url": _WEBHOOK,
        "purpose": _PURPOSE,
    },
    ["type", "config", "schedule_cron"],
)
LIST_SCHEMA = schema(
    "tinyfish_list_monitors",
    "Only use when the user asks which Monitors they have. Returns each Monitor "
    "id, type, target, schedule, and status.",
    {},
    [],
)
GET_SCHEMA = schema(
    "tinyfish_get_monitor",
    "Only use when the user asks for one Monitor. Requires monitor_id from "
    "tinyfish_list_monitors or tinyfish_create_monitor.",
    _ID_ONLY,
    ["monitor_id"],
)
UPDATE_SCHEMA = schema(
    "tinyfish_update_monitor",
    "Only use when the user asks to change a Monitor's schedule, name, webhook, or "
    'purpose. Send only the fields to change; "" clears webhook_url or purpose. '
    "The query or URL cannot change: create a new Monitor instead.",
    {
        "monitor_id": _MONITOR_ID,
        "schedule_cron": _CRON,
        "name": {"type": "string", "description": "New name."},
        "webhook_url": _WEBHOOK,
        "purpose": _PURPOSE,
    },
    ["monitor_id"],
)
PAUSE_SCHEMA = schema(
    "tinyfish_pause_monitor",
    "Only use when the user asks to pause a Monitor. Stops its schedule until "
    "tinyfish_resume_monitor.",
    _ID_ONLY,
    ["monitor_id"],
)
RESUME_SCHEMA = schema(
    "tinyfish_resume_monitor",
    "Only use when the user asks to resume a paused Monitor and start its "
    "schedule again.",
    _ID_ONLY,
    ["monitor_id"],
)
RUN_SCHEMA = schema(
    "tinyfish_run_monitor",
    "Only use when the user asks to check a Monitor immediately. Runs once and "
    "returns that result.",
    _ID_ONLY,
    ["monitor_id"],
)
CANCEL_SCHEMA = schema(
    "tinyfish_cancel_monitor",
    "Only use when the user explicitly asks to delete or cancel a Monitor. "
    "Removes it and its schedule.",
    _ID_ONLY,
    ["monitor_id"],
)

_CREATE_FIELDS = ("name", "schedule_cron", "webhook_url", "purpose")
_CLEARABLE = ("webhook_url", "purpose")


def _path(args: dict[str, Any]) -> str:
    return f"/v1/monitors/{rest_client.quote_id(required(args, 'monitor_id'))}"


def _create(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    config = args.get("config")
    if not isinstance(config, dict):
        raise ValueError("config is required.")
    fields: dict[str, Any] = {
        "type": required(args, "type"),
        "config": {k: v for k, v in config.items() if v is not None},
        **given(args, _CREATE_FIELDS),
    }
    # The baseline check runs inside the request.
    return _request(
        "POST", "/v1/monitors", api_key=api_key, json_body=fields, timeout=60.0
    )


def _list(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return _request("GET", "/v1/monitors", api_key=api_key)


def _get(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return _request("GET", _path(args), api_key=api_key)


def _update(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    path = _path(args)
    fields: dict[str, Any] = {}
    for key in ("schedule_cron", "name"):
        if args.get(key):
            fields[key] = args[key]
    for key in _CLEARABLE:
        if key in args and args[key] is not None:
            # The API clears these with null and rejects "".
            fields[key] = args[key] or None
    if not fields:
        raise ValueError(
            "Nothing to update: pass schedule_cron, name, webhook_url, or purpose."
        )
    return _request("PATCH", path, api_key=api_key, json_body=fields)


def _status(status: str) -> Callable[[dict[str, Any], str], dict[str, Any]]:
    def run(args: dict[str, Any], api_key: str) -> dict[str, Any]:
        return _request(
            "PATCH", _path(args), api_key=api_key, json_body={"status": status}
        )

    return run


def _run(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return _request("POST", f"{_path(args)}/runs", api_key=api_key, timeout=60.0)


def _cancel(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return _request("DELETE", _path(args), api_key=api_key)


MONITOR_TOOLS: tuple[tuple[dict[str, Any], Callable[..., str]], ...] = tuple(
    (tool, with_key(handler))
    for tool, handler in (
        (CREATE_SCHEMA, _create),
        (LIST_SCHEMA, _list),
        (GET_SCHEMA, _get),
        (UPDATE_SCHEMA, _update),
        (PAUSE_SCHEMA, _status("paused")),
        (RESUME_SCHEMA, _status("active")),
        (RUN_SCHEMA, _run),
        (CANCEL_SCHEMA, _cancel),
    )
)
