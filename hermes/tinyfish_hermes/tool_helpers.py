"""Building blocks shared by the plugin's ``tinyfish_*`` tools."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeVar

from . import rest_client
from .provider import MISSING_KEY_ERROR, _api_key, _is_interrupted

T = TypeVar("T")
ErrorHandler = Callable[[rest_client.TinyFishRestError], dict[str, Any]]


def schema(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def required(args: dict[str, Any], key: str) -> str:
    value = str(args.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required.")
    return value


def given(args: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: args[k] for k in keys if args.get(k) not in (None, "")}


def _feature_not_enabled(exc: rest_client.TinyFishRestError) -> bool:
    # Research start refuses an unflagged account with a bare 403 FORBIDDEN.
    return exc.code == "FEATURE_NOT_AVAILABLE" or (
        exc.status == HTTPStatus.FORBIDDEN and str(exc).endswith("API is not available")
    )


def error_payload(exc: rest_client.TinyFishRestError) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": str(exc)}
    if exc.code:
        payload["code"] = exc.code
    if exc.retry_after:
        # Retry-After may be an HTTP date; only a seconds count becomes a number.
        r = exc.retry_after.strip()
        payload["retry_after_seconds"] = int(r) if r.isdigit() else r
    if exc.details:
        payload["details"] = exc.details
    if _feature_not_enabled(exc):
        product = (exc.service or "").removeprefix("TinyFish ") or "This product"
        payload["next_action"] = (
            f"{product} isn't enabled for this TinyFish account yet; tell the user, "
            "don't retry."
        )
    return payload


def with_key(
    handler: Callable[[dict[str, Any], str], dict[str, Any]],
    on_error: ErrorHandler = error_payload,
) -> Callable[..., str]:
    def run(args: dict[str, Any], **_: Any) -> str:
        api_key = _api_key()
        if not api_key:
            return json.dumps({"error": MISSING_KEY_ERROR})
        try:
            result = handler(args or {}, api_key)
        except ValueError as exc:
            result = {"error": str(exc)}
        except rest_client.TinyFishRestError as exc:
            result = on_error(exc)
        return json.dumps(result, ensure_ascii=False)

    return run


def wait_until(
    read: Callable[[float], T],
    done: Callable[[T], bool],
    budget_s: float = 25.0,
    interval_s: float = 3.0,
) -> T:
    """Re-read until ``done`` or the budget runs out; returns the last read."""

    deadline = time.monotonic() + budget_s

    def remaining() -> float:
        # Each read's timeout is what's left, so a slow read can't overrun the budget.
        return max(1.0, deadline - time.monotonic())

    current = read(remaining())
    while not done(current) and time.monotonic() + interval_s < deadline:
        if _is_interrupted():
            break
        time.sleep(interval_s)
        current = read(remaining())
    return current
