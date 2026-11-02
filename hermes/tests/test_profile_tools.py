from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from tinyfish_hermes import profile_tools, rest_client
from tinyfish_hermes.credit_policy import pre_tool_call_policy

TOOLS = {schema["name"]: handler for schema, handler in profile_tools.PROFILE_TOOLS}


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return json.loads(TOOLS[name](args))


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    sent: list[dict[str, Any]] = []
    replies: list[httpx.Response] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        sent.append({"method": method, "url": url, "json": kwargs.get("json")})
        reply = replies.pop(0) if replies else httpx.Response(200, json={})
        reply.request = httpx.Request(method, url)
        return reply

    monkeypatch.setattr(rest_client.httpx, "request", fake_request)
    return SimpleNamespace(sent=sent, replies=replies)


def reply(http: Any, status: int, payload: dict[str, Any]) -> None:
    http.replies.append(httpx.Response(status, json=payload))


def test_create_returns_setup_url_in_one_call(http: Any) -> None:
    reply(
        http,
        201,
        {"id": "prof_1", "name": "Amazon", "is_default": True, "fingerprint_seed": 9},
    )

    out = call(
        "tinyfish_create_profile",
        {"name": " Amazon ", "site": "https://www.amazon.com/hz/wishlist"},
    )

    assert http.sent[0]["method"] == "POST"
    assert http.sent[0]["url"] == f"{rest_client.AGENT_URL}/v1/profiles"
    assert http.sent[0]["json"] == {"name": "Amazon"}
    assert out["setup_url"] == (
        f"{rest_client.AGENT_URL}/profiles/prof_1/setup?domain=www.amazon.com&source=hermes"
    )
    assert "fingerprint_seed" not in out
    assert '"prof_1"' in out["next_step"]


def test_create_rejects_a_site_that_is_not_a_domain(http: Any) -> None:
    out = call("tinyfish_create_profile", {"name": "x", "site": "localhost"})

    assert "not a site" in out["error"]
    assert http.sent == []


def test_sign_in_builds_link_without_calling_the_api(http: Any) -> None:
    out = call(
        "tinyfish_profile_sign_in", {"profile_id": "prof/1", "site": "amazon.com"}
    )

    assert out["setup_url"].startswith(
        f"{rest_client.AGENT_URL}/profiles/prof%2F1/setup?"
    )
    assert http.sent == []


def test_list_trims_profiles_to_what_the_agent_needs(http: Any) -> None:
    reply(
        http,
        200,
        {
            "profiles": [
                {
                    "id": "prof_1",
                    "name": "A",
                    "is_default": True,
                    "proxy_country_code": "US",
                    "created_at": "t",
                    "signed_in_sites": [{"site": "amazon.com", "claimed_at": "t"}],
                }
            ]
        },
    )

    out = call("tinyfish_list_profiles", {})

    assert out == {
        "profiles": [
            {
                "id": "prof_1",
                "name": "A",
                "is_default": True,
                "proxy_country_code": "US",
                "domain_count": None,
                "signed_in_sites": ["amazon.com"],
            }
        ]
    }


def test_list_without_sign_in_tracking_still_shows_domain_count(http: Any) -> None:
    reply(http, 200, {"profiles": [{"id": "prof_1", "name": "A", "domain_count": 2}]})

    profile = call("tinyfish_list_profiles", {})["profiles"][0]

    assert profile["domain_count"] == 2
    assert "signed_in_sites" not in profile


def test_update_sends_only_requested_fields(http: Any) -> None:
    reply(http, 200, {"id": "prof_1", "name": "New", "is_default": True})

    out = call(
        "tinyfish_update_profile",
        {"profile_id": "prof_1", "name": "New", "set_as_default": True},
    )

    assert http.sent[0]["method"] == "PATCH"
    assert http.sent[0]["json"] == {"name": "New", "set_as_default": True}
    assert out["name"] == "New"


def test_update_with_nothing_to_change_errors_locally(http: Any) -> None:
    out = call(
        "tinyfish_update_profile", {"profile_id": "prof_1", "set_as_default": False}
    )

    assert "Nothing to update" in out["error"]
    assert http.sent == []


def test_delete_surfaces_the_server_reason(http: Any) -> None:
    message = "Cannot delete your only browser profile. Create another profile first."
    reply(http, 400, {"error": {"code": "INVALID_INPUT", "message": message}})

    out = call("tinyfish_delete_profile", {"profile_id": "prof_1"})

    assert http.sent[0]["method"] == "DELETE"
    assert message in out["error"]


def test_not_found_points_back_at_list(http: Any) -> None:
    reply(
        http,
        404,
        {"error": {"code": "NOT_FOUND", "message": "Profile with id 'x' not found"}},
    )

    out = call("tinyfish_update_profile", {"profile_id": "x", "name": "y"})

    assert "tinyfish_list_profiles" in out["next_step"]


def test_missing_key_never_calls_the_api(
    http: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY")

    assert "API key not found" in call("tinyfish_list_profiles", {})["error"]
    assert http.sent == []


def test_delete_always_asks_and_approval_is_per_profile() -> None:
    first = pre_tool_call_policy("tinyfish_delete_profile", {"profile_id": "prof_1"})
    second = pre_tool_call_policy("tinyfish_delete_profile", {"profile_id": "prof_2"})

    assert first and first["action"] == "approve"
    assert second and first["rule_key"] != second["rule_key"]
    for name in (
        "tinyfish_list_profiles",
        "tinyfish_create_profile",
        "tinyfish_update_profile",
    ):
        assert pre_tool_call_policy(name, {}) is None


@pytest.mark.parametrize(
    ("given", "sent"), [("gb", "GB"), ("none", None), ("Direct", None)]
)
def test_update_sets_or_clears_the_profile_proxy(
    http: Any, given: str, sent: str | None
) -> None:
    reply(http, 200, {"id": "prof_1", "proxy_country_code": sent})

    call(
        "tinyfish_update_profile", {"profile_id": "prof_1", "proxy_country_code": given}
    )

    assert http.sent[0]["json"] == {"proxy_country_code": sent}


def test_create_sends_the_proxy_with_the_profile(http: Any) -> None:
    reply(http, 201, {"id": "prof_1", "name": "Amazon", "proxy_country_code": "US"})

    out = call(
        "tinyfish_create_profile", {"name": "Amazon", "proxy_country_code": "us"}
    )

    assert http.sent[0]["json"] == {"name": "Amazon", "proxy_country_code": "US"}
    assert out["proxy_country_code"] == "US"


def test_bad_proxy_code_errors_before_calling_the_api(http: Any) -> None:
    out = call("tinyfish_create_profile", {"name": "x", "proxy_country_code": "USA"})

    assert "2-letter country code" in out["error"]
    assert http.sent == []


def test_delete_in_progress_says_to_wait_before_retrying(http: Any) -> None:
    message = "Profile delete is still in progress. Retry in a moment."
    reply(http, 409, {"error": {"code": "RETRY_REQUIRED", "message": message}})

    out = call("tinyfish_delete_profile", {"profile_id": "prof_1"})

    assert message in out["error"]
    assert "Wait for the previous call" in out["next_step"]
