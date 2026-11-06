"""TinyFish Deep Research tools: cited multi-source reports, run asynchronously."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar
from urllib.parse import quote

from . import rest_client
from .profile_tools import _required, _schema, _with_key, plain_error
from .provider import _is_interrupted

T = TypeVar("T")

ACTIVE_STATUSES = frozenset({"QUEUED", "RUNNING"})
_LISTED_QUERY_CHARS = 200
_POLL_AGAIN = (
    "Call tinyfish_get_deep_research again with the same research_run_id; research "
    "usually takes several minutes. Do not start a new run or cancel because it is "
    "slow."
)


def wait_until(
    read: Callable[[], T],
    done: Callable[[T], bool],
    budget_s: float = 25.0,
    interval_s: float = 3.0,
) -> T:
    """Re-read until ``done`` or the budget runs out; returns the last read."""

    deadline = time.monotonic() + budget_s
    current = read()
    while not done(current) and time.monotonic() + interval_s < deadline:
        if _is_interrupted():
            break
        time.sleep(interval_s)
        current = read()
    return current


def report_url(research_run_id: str) -> str:
    return f"{rest_client.AGENT_URL}/research/{quote(research_run_id, safe='')}"


_CONCURRENCY = (
    "By default at most 5 runs go at once per user (some accounts allow a "
    "different number; a refusal states the actual limit); for more questions, "
    "start the rest only after earlier runs finish (poll them with "
    "tinyfish_get_deep_research)."
)
_MODE = (
    "max: deeper research with a larger budget, only when the user asks for "
    "maximum depth or an exhaustive report; slower and costs more. deep (default) "
    "for everything else."
)
_RUN_ID = {
    "research_run_id": {
        "type": "string",
        "description": "Id returned by tinyfish_start_deep_research.",
    }
}

START_SCHEMA = _schema(
    "tinyfish_start_deep_research",
    "Slow (several minutes) and billed per run. Only use when the user explicitly "
    "asks for deep research, or a cited report, literature review, survey, or "
    "landscape, or the question needs synthesis across many sources that a few "
    "web_search and web_extract calls cannot cover (market or competitor "
    "landscapes, literature reviews, multi-factor comparisons across many "
    'options). Not for single facts, definitions, current news, docs lookups, "what '
    'is"/"compare X vs Y" questions, or reading known URLs: use web_search and '
    "web_extract for those. Starts an async run and returns research_run_id; then "
    f"call tinyfish_get_deep_research. {_CONCURRENCY} Mode {_MODE} Follow-ups "
    "accept prior_run_id for an earlier report or session_id for an existing owned "
    "session, mutually exclusively. domain_filter prioritizes or restricts sources "
    "and can block domains.",
    {
        "query": {
            "type": "string",
            "description": (
                "The research question, with any scope or constraints the user gave."
            ),
        },
        "mode": {"type": "string", "enum": ["deep", "max"], "description": _MODE},
        "prior_run_id": {
            "type": "string",
            "description": "Seed this run with a completed report and its evidence.",
        },
        "session_id": {
            "type": "string",
            "description": (
                "Continue a research session. Mutually exclusive with prior_run_id."
            ),
        },
        "domain_filter": {
            "type": "object",
            "description": "Domain preferences. Each list accepts at most 150 entries.",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["include", "exclusive"],
                    "description": (
                        "include prioritizes the domains; exclusive restricts "
                        "results to them."
                    ),
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to prefer or require.",
                },
                "block": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to always remove.",
                },
            },
            "required": ["mode"],
        },
    },
    ["query"],
)
GET_SCHEMA = _schema(
    "tinyfish_get_deep_research",
    "Waits up to about 25 seconds for a run started by "
    "tinyfish_start_deep_research, then returns its status. When output_ready is "
    "true, the result has the cited report. While the run is still going, call "
    "tinyfish_get_deep_research again with the same research_run_id; research "
    "usually takes several minutes. Do not start a new run or cancel because it is "
    "slow. If the user asks about an earlier report, call "
    "tinyfish_list_deep_research. Completed reports may include freshness_report "
    "and termination_reason; synthesis_failed means the report contains interim "
    "findings.",
    _RUN_ID,
    ["research_run_id"],
)
LIST_SCHEMA = _schema(
    "tinyfish_list_deep_research",
    "Lists the user's deep research runs, newest first, with status and "
    "report_url. Filter by status, query text or created_after/created_before; "
    "page with cursor from pagination.next_cursor. Use when the user asks about an "
    "earlier report, or before starting a run that may repeat one; then call "
    "tinyfish_get_deep_research with its research_run_id.",
    {
        "status": {
            "type": "string",
            "enum": ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"],
            "description": "Filter by research run status.",
        },
        "query": {
            "type": "string",
            "description": "Filter by query text (case-insensitive partial match).",
        },
        "created_after": {
            "type": "string",
            "description": "Runs created after this ISO 8601 timestamp.",
        },
        "created_before": {
            "type": "string",
            "description": "Runs created before this ISO 8601 timestamp.",
        },
        "sort_direction": {
            "type": "string",
            "enum": ["asc", "desc"],
            "description": "Sort by created_at; defaults to desc.",
        },
        "cursor": {
            "type": "string",
            "description": (
                "pagination.next_cursor from the previous page, with the same "
                "sort_direction."
            ),
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Runs per page, 1 to 100; defaults to 20.",
        },
    },
    [],
)
CANCEL_SCHEMA = _schema(
    "tinyfish_cancel_deep_research",
    "Only use when the user explicitly asks to stop a deep research run. Never "
    "cancel because research is slow or tinyfish_get_deep_research returned "
    "without a report; keep polling instead. Idempotent: finished runs return "
    "their current status.",
    _RUN_ID,
    ["research_run_id"],
)


def research_error_json(exc: rest_client.TinyFishRestError) -> str:
    payload = plain_error(exc)
    active = (exc.details or {}).get("active_research_run_ids")
    if isinstance(active, list) and active:
        payload["next_action"] = (
            f"Running now: {', '.join(map(str, active))}. Call "
            "tinyfish_get_deep_research on these, then start this question once one "
            "finishes. Do not retry it right away."
        )
    return json.dumps(payload)


def _start(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    fields: dict[str, Any] = {"query": _required(args, "query")}
    for key in ("mode", "prior_run_id", "session_id", "domain_filter"):
        if args.get(key) not in (None, ""):
            fields[key] = args[key]
    started = rest_client.start_research(fields, api_key=api_key)
    run_id = str(started.get("research_run_id") or "")
    if not run_id:
        raise rest_client.TinyFishRestError(
            "TinyFish Research did not return a research_run_id."
        )
    url = report_url(run_id)
    return {
        "research_run_id": run_id,
        "status": "QUEUED",
        "output_ready": False,
        "report_url": url,
        "next_action": (
            "Tell the user the report takes about 10 minutes, they can leave, and it "
            f"will be at [their report]({url}); show that markdown link. Then call "
            f"tinyfish_get_deep_research with research_run_id={run_id} to wait for "
            "the report; do not start another run."
        ),
    }


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        # Python 3.10's fromisoformat rejects a trailing Z.
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _elapsed_s(run: dict[str, Any]) -> int:
    started = _parse_time(run.get("created_at"))
    if started is None:
        return 0
    end = _parse_time(run.get("completed_at")) or datetime.now(timezone.utc)
    return max(0, round((end - started).total_seconds()))


def _progress(run: dict[str, Any]) -> str | None:
    evidence = run.get("evidence")
    if isinstance(evidence, list) and evidence:
        return f"Reading sources ({len(evidence)} so far)"
    return "Searching for sources" if run.get("research_plan") else None


def research_status(run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run.get("research_run_id") or "")
    base: dict[str, Any] = {
        "research_run_id": run_id,
        "status": run.get("status"),
        "elapsed_s": _elapsed_s(run),
        "report_url": report_url(run_id),
    }
    if run.get("status") == "COMPLETED":
        deep = run.get("deep_result") or {}
        out = {
            **base,
            "output_ready": True,
            "report": deep.get("result"),
            "citations": deep.get("citations") or [],
        }
        for key in ("freshness_report", "termination_reason"):
            if deep.get(key):
                out[key] = deep[key]
        return out
    if run.get("error"):
        return {**base, "output_ready": False, "error": run["error"]}
    out = {**base, "output_ready": False, "next_action": _POLL_AGAIN}
    progress = _progress(run)
    if progress:
        out["progress"] = progress
    return out


def _get(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    run_id = _required(args, "research_run_id")
    # ponytail: full-run polls log ~9 fetch events/call; use a status endpoint later.
    run = wait_until(
        lambda: rest_client.get_research(run_id, api_key=api_key),
        lambda r: r.get("status") not in ACTIVE_STATUSES,
    )
    return research_status(run)


def _list(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    params = {
        key: args[key]
        for key in (
            "status",
            "query",
            "created_after",
            "created_before",
            "sort_direction",
            "cursor",
            "limit",
        )
        if args.get(key) not in (None, "")
    }
    page = rest_client.list_research(params, api_key=api_key)
    runs = [r for r in page.get("data") or [] if isinstance(r, dict)]
    return {
        "data": [
            {
                "research_run_id": r.get("research_run_id"),
                "query": str(r.get("query") or "")[:_LISTED_QUERY_CHARS],
                "status": r.get("status"),
                "created_at": r.get("created_at"),
                "completed_at": r.get("completed_at"),
                "report_url": report_url(str(r.get("research_run_id") or "")),
            }
            for r in runs
        ],
        "pagination": page.get("pagination"),
        "next_action": (
            "Call tinyfish_get_deep_research with a research_run_id to read that "
            "report."
        ),
    }


def _cancel(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    return rest_client.cancel_research(
        _required(args, "research_run_id"), api_key=api_key
    )


RESEARCH_TOOLS: tuple[tuple[dict[str, Any], Callable[..., str]], ...] = (
    (START_SCHEMA, _with_key(_start, research_error_json)),
    (GET_SCHEMA, _with_key(_get, research_error_json)),
    (LIST_SCHEMA, _with_key(_list, research_error_json)),
    (CANCEL_SCHEMA, _with_key(_cancel, research_error_json)),
)
