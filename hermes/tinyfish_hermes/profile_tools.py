"""Browser Context Profile tools: saved website sign-ins for ``tinyfish_agent``."""

from __future__ import annotations

import json

from . import rest_client

PROFILE_TERM = (
    "A TinyFish Browser Context Profile is a saved website sign-in "
    "(not a Hermes profile, and unrelated to browser_profile)."
)


def error_next_step(exc: rest_client.TinyFishRestError) -> str | None:
    message = str(exc).lower()
    if "no default browser context profile" in message:
        return (
            "Call tinyfish_list_profiles and pass a profile_id; if there are none, "
            "call tinyfish_create_profile and give the user setup_url."
        )
    if "not found" in message and "profile" in message:
        return "Call tinyfish_list_profiles and use an exact profile_id from it."
    if exc.status == 409:
        return "Retry in a few seconds."
    return None


def error_json(exc: rest_client.TinyFishRestError) -> str:
    payload = {"error": str(exc)}
    next_step = error_next_step(exc)
    if next_step:
        payload["next_step"] = next_step
    return json.dumps(payload)
