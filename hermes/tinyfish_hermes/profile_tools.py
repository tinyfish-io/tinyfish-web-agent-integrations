"""Browser Context Profile tools: saved website sign-ins for ``tinyfish_agent``."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Any
from urllib.parse import urlencode, urlparse

from . import rest_client
from .tool_helpers import required, schema, with_key

PROFILE_TERM = (
    "A TinyFish Browser Context Profile is a saved website sign-in "
    "(not a Hermes profile, and unrelated to browser_profile)."
)
_SUMMARY_KEYS = ("id", "name", "is_default", "proxy_country_code", "domain_count")

_PROFILE_ID = {
    "type": "string",
    "description": "Profile id from tinyfish_list_profiles.",
}
_SITE = {
    "type": "string",
    "description": "Site the user will sign in to, e.g. amazon.com or a URL on it.",
}
_PROXY = {
    "type": "string",
    "description": (
        "Proxy country for both sign-in and runs on this profile, as an ISO 3166-1 "
        "alpha-2 code such as US; 'none' connects directly. Set one when a site "
        "blocks the sign-in page or needs a local IP. Overrides tinyfish_agent's "
        "proxy_country_code."
    ),
}
_NO_PROXY = frozenset({"none", "off", "direct"})


LIST_SCHEMA = schema(
    "tinyfish_list_profiles",
    f"List the user's TinyFish Browser Context Profiles. {PROFILE_TERM} For a site "
    "that needs sign-in, pass the profile_id whose signed_in_sites covers it (an "
    "entry covers its subdomains) to tinyfish_agent; if signed_in_sites is absent, "
    "match by name and ask the user. Free.",
    {},
    [],
)
CREATE_SCHEMA = schema(
    "tinyfish_create_profile",
    "Create a TinyFish Browser Context Profile and get the link where the user "
    f"signs in. {PROFILE_TERM} Name one per account, e.g. 'Amazon Personal'. Free "
    "until the user opens the link.",
    {
        "name": {"type": "string", "description": "Profile name, 1-100 characters."},
        "site": _SITE,
        "set_as_default": {
            "type": "boolean",
            "description": "Make this the profile use_profile picks by default.",
        },
        "proxy_country_code": _PROXY,
    },
    ["name"],
)
SIGN_IN_SCHEMA = schema(
    "tinyfish_profile_sign_in",
    "Get a link where the user signs in to a site on an existing TinyFish Browser "
    "Context Profile, to add a site or refresh an expired sign-in. Free until the "
    "user opens it.",
    {"profile_id": _PROFILE_ID, "site": _SITE},
    ["profile_id"],
)
UPDATE_SCHEMA = schema(
    "tinyfish_update_profile",
    "Rename a TinyFish Browser Context Profile, make it the default, or change "
    "its proxy country (e.g. when a site blocks the sign-in link).",
    {
        "profile_id": _PROFILE_ID,
        "name": {"type": "string", "description": "New name, 1-100 characters."},
        "set_as_default": {
            "type": "boolean",
            "description": "true makes this the default profile; false is ignored.",
        },
        "proxy_country_code": _PROXY,
    },
    ["profile_id"],
)
DELETE_SCHEMA = schema(
    "tinyfish_delete_profile",
    "Permanently delete a TinyFish Browser Context Profile and its saved sign-ins. "
    "Only when the user asks; name the profile to them first. It cannot be undone. "
    "Deletes one profile per call: to delete several, call once per profile, one "
    "after another, never in parallel or batched.",
    {"profile_id": _PROFILE_ID},
    ["profile_id"],
)


def setup_url(profile_id: str, site: str = "") -> str:
    query = {"domain": site} if site else {}
    query["source"] = "hermes"
    path = f"/profiles/{rest_client.quote_id(profile_id)}/setup"
    return f"{rest_client.AGENT_URL}{path}?{urlencode(query)}"


def site_host(site: str) -> str:
    # The setup page ignores anything but a bare hostname.
    value = site.strip()
    if not value:
        return ""
    host = urlparse(value if "://" in value else f"https://{value}").hostname or ""
    if "." not in host:
        raise ValueError(f"'{site}' is not a site; pass a domain such as amazon.com.")
    return host


def sign_in_next_step(profile_id: str) -> str:
    return (
        "Give the user setup_url. They may be asked to sign in to TinyFish first; "
        "that is expected. They then sign in to the site and click Save profile; "
        "never ask for their password. Wait until they say they are done, check "
        "tinyfish_list_profiles (if signed_in_sites is absent, take their word), "
        f'then run tinyfish_agent with profile_id "{profile_id}". If the site blocks '
        "the sign-in page, set proxy_country_code with tinyfish_update_profile and "
        "send the same link again."
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
    if exc.status == HTTPStatus.CONFLICT:
        return "Wait for the previous call on this profile to finish, then retry."
    return None


def profile_error(exc: rest_client.TinyFishRestError) -> dict[str, Any]:
    payload = {"error": str(exc)}
    next_step = error_next_step(exc)
    if next_step:
        payload["next_step"] = next_step
    return payload


def _summary(profile: dict[str, Any]) -> dict[str, Any]:
    out = {key: profile.get(key) for key in _SUMMARY_KEYS}
    sites = profile.get("signed_in_sites")
    if isinstance(sites, list):
        out["signed_in_sites"] = [s.get("site") for s in sites if isinstance(s, dict)]
    return out


def _list(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    profiles = rest_client.list_profiles(api_key=api_key).get("profiles") or []
    return {"profiles": [_summary(p) for p in profiles if isinstance(p, dict)]}


def _proxy_fields(args: dict[str, Any]) -> dict[str, Any]:
    value = str(args.get("proxy_country_code") or "").strip()
    if not value:
        return {}
    if value.lower() in _NO_PROXY:
        return {"proxy_country_code": None}
    if len(value) != 2 or not value.isalpha():
        raise ValueError(
            f"proxy_country_code '{value}' must be a 2-letter country code or 'none'."
        )
    return {"proxy_country_code": value.upper()}


def _create(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    fields: dict[str, Any] = {"name": required(args, "name")}
    site = site_host(str(args.get("site") or ""))
    if args.get("set_as_default") is not None:
        fields["set_as_default"] = bool(args["set_as_default"])
    fields.update(_proxy_fields(args))
    profile = rest_client.create_profile(fields, api_key=api_key)
    profile_id = str(profile.get("id") or "")
    if not profile_id:
        raise rest_client.TinyFishRestError(
            "TinyFish Profiles did not return a profile id."
        )
    return {
        **_summary(profile),
        "setup_url": setup_url(profile_id, site),
        "next_step": sign_in_next_step(profile_id),
    }


def _sign_in(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    profile_id = required(args, "profile_id")
    site = site_host(str(args.get("site") or ""))
    return {
        "profile_id": profile_id,
        "setup_url": setup_url(profile_id, site),
        "next_step": sign_in_next_step(profile_id),
    }


def _update(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    profile_id = required(args, "profile_id")
    fields: dict[str, Any] = {}
    name = str(args.get("name") or "").strip()
    if name:
        fields["name"] = name
    if args.get("set_as_default") is True:
        fields["set_as_default"] = True
    fields.update(_proxy_fields(args))
    if not fields:
        raise ValueError(
            "Nothing to update: pass name, proxy_country_code, or set_as_default true."
        )
    return _summary(rest_client.update_profile(profile_id, fields, api_key=api_key))


def _delete(args: dict[str, Any], api_key: str) -> dict[str, Any]:
    profile_id = required(args, "profile_id")
    rest_client.delete_profile(profile_id, api_key=api_key)
    return {"profile_id": profile_id, "deleted": True}


PROFILE_TOOLS: tuple[tuple[dict[str, Any], Callable[..., str]], ...] = (
    (LIST_SCHEMA, with_key(_list, profile_error)),
    (CREATE_SCHEMA, with_key(_create, profile_error)),
    (SIGN_IN_SCHEMA, with_key(_sign_in, profile_error)),
    (UPDATE_SCHEMA, with_key(_update, profile_error)),
    (DELETE_SCHEMA, with_key(_delete, profile_error)),
)
