"""``tinyfish_agent``: goal-based TinyFish web automation as a Hermes tool."""

from __future__ import annotations

import json
import time
from typing import Any

from . import rest_client
from .profile_tools import PROFILE_TERM, error_json
from .provider import MISSING_KEY_ERROR, _api_key, _is_interrupted

TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
# Hermes' tool batch deadline is 420s; stop polling well before it.
POLL_BUDGET_SECONDS = 300.0
POLL_INTERVAL_SECONDS = 3.0
# Hermes' context pruner targets results above ~8k chars.
MAX_RESULT_CHARS = 12_000

TINYFISH_AGENT_SCHEMA: dict[str, Any] = {
    "name": "tinyfish_agent",
    "description": (
        "Run a TinyFish web agent on a real website to complete a goal: navigate, "
        "click, fill forms, and extract data across multiple pages. Use for "
        "multi-step site tasks that web_search/web_extract cannot do. If the site "
        "needs sign-in, call tinyfish_list_profiles and pass the profile_id that "
        "covers it. Ask the user before buying, posting, sending, or changing "
        "account settings. Consumes TinyFish credits. Returns the agent's result "
        "as JSON."
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
                "description": (
                    "Route through a proxy in this country. A profile's own proxy "
                    "country overrides this."
                ),
            },
            "use_profile": {
                "type": "boolean",
                "description": (
                    f"Run signed in with the user's default profile. {PROFILE_TERM}"
                ),
            },
            "profile_id": {
                "type": "string",
                "description": (
                    "Run signed in with this profile from tinyfish_list_profiles."
                ),
            },
        },
        "required": ["url", "goal"],
    },
}


def _result(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) <= MAX_RESULT_CHARS:
        return text
    # Partial JSON text, not the original structure, under a key that says so.
    full = json.dumps(payload.pop("result", None), ensure_ascii=False)
    payload["truncated"] = True
    cut = MAX_RESULT_CHARS - len(json.dumps({**payload, "result_preview": ""}))
    while cut > 0:
        text = json.dumps({**payload, "result_preview": full[:cut]}, ensure_ascii=False)
        if len(text) <= MAX_RESULT_CHARS:
            return text
        cut -= len(text) - MAX_RESULT_CHARS
    return json.dumps(payload, ensure_ascii=False)


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    keys = ("run_id", "status", "result", "error", "streaming_url", "profile_hint")
    summary = {key: run[key] for key in keys if run.get(key) is not None}
    # Failed runs nest the hint under error, and its relative link opens outside Hermes.
    for holder in (summary, summary.get("error")):
        if not isinstance(holder, dict):
            continue
        hint = holder.get("profile_hint")
        if isinstance(hint, dict) and str(hint.get("setup_url") or "").startswith("/"):
            holder["profile_hint"] = {
                **hint,
                "setup_url": rest_client.AGENT_URL + hint["setup_url"],
            }
    return summary


def tinyfish_agent(args: dict[str, Any], **_: Any) -> str:
    api_key = _api_key()
    if not api_key:
        return json.dumps({"error": MISSING_KEY_ERROR})
    url = str(args.get("url") or "").strip()
    goal = str(args.get("goal") or "").strip()
    if not url or not goal:
        return json.dumps({"error": "tinyfish_agent needs both url and goal."})

    try:
        started = rest_client.start_run(
            url,
            goal,
            api_key=api_key,
            browser_profile=str(args.get("browser_profile") or "lite"),
            proxy_country_code=args.get("proxy_country_code") or None,
            use_profile=args.get("use_profile") is True,
            profile_id=str(args.get("profile_id") or "").strip() or None,
        )
    except rest_client.TinyFishRestError as exc:
        return error_json(exc)
    run_id = str(started.get("run_id") or "")
    if not run_id:
        return json.dumps({"error": "TinyFish Agent did not return a run_id."})

    deadline = time.monotonic() + POLL_BUDGET_SECONDS
    run: dict[str, Any] = {"run_id": run_id, "status": "PENDING"}
    while time.monotonic() < deadline:
        if _is_interrupted():
            try:
                rest_client.cancel_run(run_id, api_key=api_key)
            except rest_client.TinyFishRestError as exc:
                # The run may still be billing; never claim it stopped.
                error = f"Cancel failed, run may still be active: {exc}"
                return json.dumps(
                    {"run_id": run_id, "status": "UNKNOWN", "error": error}
                )
            return json.dumps({"run_id": run_id, "status": "CANCELLED"})
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            run = rest_client.get_run(run_id, api_key=api_key)
        except rest_client.TinyFishRestError as exc:
            # Retry transient failures; a 4xx (bar 429) will not fix itself.
            if exc.status and 400 <= exc.status < 500 and exc.status != 429:
                return json.dumps({"run_id": run_id, "error": str(exc)})
            continue
        if str(run.get("status") or "").upper() in TERMINAL_STATUSES:
            return _result(_summary(run))

    pending = _summary(run)
    pending["note"] = "Still running on TinyFish after 300s; give the user the run_id."
    return _result(pending)
