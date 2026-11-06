from __future__ import annotations

import json
from typing import Any

import pytest

from tinyfish_hermes import config, monitor_tools, rest_client
from tinyfish_hermes.credit_policy import pre_tool_call_policy

TOOLS = {schema["name"]: handler for schema, handler in monitor_tools.MONITOR_TOOLS}
MONITORS = f"{rest_client.AGENT_URL}/v1/monitors"


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return json.loads(TOOLS[name](args))


def test_create_sends_the_monitor_and_waits_for_the_baseline(http: Any) -> None:
    http.reply(201, {"id": "m1", "run": {"status": "completed"}})

    out = call(
        "tinyfish_create_monitor",
        {
            "type": "fetch",
            "config": {"url": "https://example.com", "format": None},
            "schedule_cron": "0 9 * * *",
            "purpose": "the price drops",
            "webhook_url": "",
        },
    )

    assert out["id"] == "m1"
    assert http.sent[0]["method"] == "POST"
    assert http.sent[0]["url"] == MONITORS
    assert http.sent[0]["json"] == {
        "type": "fetch",
        "config": {"url": "https://example.com"},
        "schedule_cron": "0 9 * * *",
        "purpose": "the price drops",
    }
    assert http.sent[0]["timeout"] == 60.0


@pytest.mark.parametrize(
    ("tool", "status"),
    [("tinyfish_pause_monitor", "paused"), ("tinyfish_resume_monitor", "active")],
)
def test_pause_and_resume_send_only_status(http: Any, tool: str, status: str) -> None:
    call(tool, {"monitor_id": "m1"})

    assert http.sent[0]["method"] == "PATCH"
    assert http.sent[0]["url"] == f"{MONITORS}/m1"
    assert http.sent[0]["json"] == {"status": status}


def test_update_clears_webhook_and_purpose_with_null(http: Any) -> None:
    call(
        "tinyfish_update_monitor",
        {"monitor_id": "m1", "webhook_url": "", "purpose": "", "name": "Prices"},
    )

    assert http.sent[0]["json"] == {
        "name": "Prices",
        "webhook_url": None,
        "purpose": None,
    }


def test_update_with_nothing_fails_without_calling_the_api(http: Any) -> None:
    out = call("tinyfish_update_monitor", {"monitor_id": "m1"})

    assert "Nothing to update" in out["error"]
    assert http.sent == []


def test_run_waits_for_the_check(http: Any) -> None:
    call("tinyfish_run_monitor", {"monitor_id": "m1"})

    assert http.sent[0]["url"] == f"{MONITORS}/m1/runs"
    assert http.sent[0]["timeout"] == 60.0


def test_cancel_deletes_the_monitor(http: Any) -> None:
    http.reply(200, {"deleted": True, "id": "m1"})

    assert call("tinyfish_cancel_monitor", {"monitor_id": "m1"}) == {
        "deleted": True,
        "id": "m1",
    }
    assert http.sent[0]["method"] == "DELETE"


def test_list_reports_server_errors_as_json(http: Any) -> None:
    http.reply(403, {"error": {"message": "Team keys cannot use Monitors"}})

    out = call("tinyfish_list_monitors", {})

    assert "Team keys cannot use Monitors" in out["error"]


@pytest.mark.parametrize(
    "tool",
    ["tinyfish_create_monitor", "tinyfish_run_monitor", "tinyfish_resume_monitor"],
)
def test_billed_monitor_tools_follow_the_monitor_policy(
    monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    policy = {"tinyfish": {"credit_policy": {"monitor": "deny"}}}
    monkeypatch.setattr(config, "load_config", lambda: policy)

    assert pre_tool_call_policy(tool, {})["action"] == "block"  # type: ignore[index]

    policy["tinyfish"]["credit_policy"]["monitor"] = "request"
    directive = pre_tool_call_policy(tool, {})
    assert directive == {
        "action": "approve",
        "message": directive["message"],  # type: ignore[index]
        "rule_key": "tinyfish:monitor",
    }


def test_free_monitor_tools_are_not_gated() -> None:
    for tool in ("tinyfish_list_monitors", "tinyfish_update_monitor"):
        assert pre_tool_call_policy(tool, {"monitor_id": "m1"}) is None


def test_cancel_always_asks_and_names_the_monitor(http: Any) -> None:
    http.reply(200, {"id": "m1", "name": "Prices"})

    directive = pre_tool_call_policy("tinyfish_cancel_monitor", {"monitor_id": "m1"})

    assert directive == {
        "action": "approve",
        "message": "Permanently delete TinyFish monitor 'Prices' (m1)?",
        "rule_key": "tinyfish:monitor_delete:m1",
    }
    assert http.sent[0]["timeout"] == 5.0


def test_create_approval_names_the_target_and_recurring_schedule() -> None:
    directive = pre_tool_call_policy(
        "tinyfish_create_monitor",
        {"config": {"url": "https://example.com/p"}, "schedule_cron": "0 9 * * *"},
    )

    assert directive is not None
    assert "https://example.com/p" in directive["message"]
    assert "'0 9 * * *'" in directive["message"]
    assert "until paused or cancelled" in directive["message"]


def test_schedule_change_follows_the_monitor_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = {"tinyfish": {"credit_policy": {"monitor": "deny"}}}
    monkeypatch.setattr(config, "load_config", lambda: policy)
    args = {"monitor_id": "m1", "schedule_cron": "* * * * *"}

    assert pre_tool_call_policy("tinyfish_update_monitor", args)["action"] == "block"  # type: ignore[index]
    policy["tinyfish"]["credit_policy"]["monitor"] = "request"
    directive = pre_tool_call_policy("tinyfish_update_monitor", args)
    assert directive is not None and "'* * * * *'" in directive["message"]
    assert pre_tool_call_policy("tinyfish_update_monitor", {"name": "x"}) is None
