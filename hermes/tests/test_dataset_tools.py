from __future__ import annotations

import json
from typing import Any

import pytest

from tinyfish_hermes import config, dataset_tools, research_tools, rest_client
from tinyfish_hermes.credit_policy import pre_tool_call_policy

TOOLS = {schema["name"]: handler for schema, handler in dataset_tools.DATASET_TOOLS}
DATASETS = f"{rest_client.AGENT_URL}/v1/datasets"
SPEC = {
    "name": "Coffee",
    "description": "Oakland coffee shops",
    "columns": [
        {
            "name": "shop",
            "type": "string",
            "is_primary_key": True,
            "retrieval_hint": "x",
        },
        {
            "name": "site",
            "label": "Website",
            "type": "url",
            "is_primary_key": False,
            "is_unique": True,
        },
    ],
}


def dataset(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": "d1",
        "name": "Coffee",
        "spec": SPEC,
        "status": status,
        "target_rows": 10,
        "row_count": 0,
        "run": {"id": "r1", "status": "running"},
        "created_at": "2026-01-01T00:00:00Z",
        **extra,
    }


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return json.loads(TOOLS[name](args))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    monkeypatch.setattr(research_tools.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(research_tools.time, "sleep", sleep)
    return now


@pytest.mark.parametrize("args", [{}, {"prompt": "coffee shops", "spec": SPEC}])
def test_create_needs_exactly_one_of_prompt_or_spec(
    http: Any, args: dict[str, Any]
) -> None:
    out = call("tinyfish_create_dataset", args)

    assert out["error"] == "Send exactly one of prompt or spec."
    assert http.sent == []


def test_create_starts_and_points_at_get(http: Any) -> None:
    http.reply(202, dataset("populating"))

    out = call("tinyfish_create_dataset", {"prompt": "coffee shops", "target_rows": 10})

    assert http.sent[0]["url"] == DATASETS
    assert http.sent[0]["json"] == {"prompt": "coffee shops", "target_rows": 10}
    assert http.sent[0]["timeout"] == 95.0
    assert out == {
        "dataset_id": "d1",
        "run_id": "r1",
        "status": "populating",
        "target_rows": 10,
        "output_ready": False,
        "next_action": out["next_action"],
    }
    assert "tinyfish_get_dataset again with dataset_id=d1" in out["next_action"]


def test_plan_waits_for_the_spec_agent(http: Any) -> None:
    http.reply(200, {"spec": SPEC})

    assert call("tinyfish_plan_dataset", {"prompt": "coffee"}) == {"spec": SPEC}
    assert http.sent[0]["url"] == f"{DATASETS}/plan"
    assert http.sent[0]["timeout"] == 95.0


def test_refused_start_after_create_says_populate_not_create(http: Any) -> None:
    http.reply(
        402,
        {"error": {"message": "Insufficient balance", "details": {"dataset_id": "d1"}}},
    )

    out = call("tinyfish_create_dataset", {"prompt": "coffee shops"})

    assert out["dataset_id"] == "d1"
    assert "tinyfish_populate_dataset with that id" in out["next_action"]
    assert "do not call tinyfish_create_dataset again" in out["next_action"]


def test_run_limit_says_wait_then_populate(http: Any) -> None:
    http.reply(
        429,
        {"error": {"message": "Too many runs", "details": {"dataset_id": "d1"}}},
        **{"Retry-After": "60"},
    )

    out = call("tinyfish_create_dataset", {"prompt": "coffee shops"})

    assert out["next_action"].startswith("Run limit reached")
    assert "tinyfish_populate_dataset with dataset_id=d1" in out["next_action"]
    assert out["retry_after_seconds"] == "60"


def test_flag_off_says_not_enabled(http: Any) -> None:
    http.reply(
        403,
        {
            "error": {
                "code": "FEATURE_NOT_AVAILABLE",
                "message": "Datasets API is not available",
            }
        },
    )

    out = call("tinyfish_list_datasets", {})

    assert out["next_action"].startswith("Datasets isn't enabled")


def test_get_ready_previews_fifty_rows(http: Any, clock: list[float]) -> None:
    http.reply(200, dataset("ready", row_count=2))
    http.reply(200, {"rows": [{"_id": "x", "data": {}}], "next_cursor": "c2"})

    out = call("tinyfish_get_dataset", {"dataset_id": "d1"})

    assert http.sent[1]["url"] == f"{DATASETS}/d1/rows"
    assert http.sent[1]["params"] == {"limit": 50}
    assert out["output_ready"] is True
    assert out["rows"] == [{"_id": "x", "data": {}}]
    assert out["next_cursor"] == "c2"
    assert out["columns"] == [
        {"name": "shop", "type": "string", "is_primary_key": True},
        {
            "name": "site",
            "label": "Website",
            "type": "url",
            "is_primary_key": False,
            "is_unique": True,
        },
    ]


def test_get_polls_then_says_poll_again(http: Any, clock: list[float]) -> None:
    for _ in range(20):
        http.reply(200, dataset("populating"))

    out = call("tinyfish_get_dataset", {"dataset_id": "d1"})

    assert len(http.sent) == 9
    assert out["output_ready"] is False
    assert "tinyfish_get_dataset again" in out["next_action"]


def test_get_without_wait_reads_once(http: Any, clock: list[float]) -> None:
    http.reply(200, dataset("populating"))

    call("tinyfish_get_dataset", {"dataset_id": "d1", "wait": False})

    assert len(http.sent) == 1


def test_list_projects_datasets(http: Any) -> None:
    http.reply(
        200,
        {
            "data": [dataset("ready")],
            "pagination": {"next_cursor": "c2", "has_more": True},
        },
    )

    out = call("tinyfish_list_datasets", {"limit": 5})

    assert http.sent[0]["params"] == {"limit": 5}
    assert out["next_cursor"] == "c2"
    assert out["has_more"] is True
    assert out["datasets"][0]["dataset_id"] == "d1"
    assert "spec" not in out["datasets"][0]


@pytest.mark.parametrize(
    ("args", "params"),
    [
        ({}, {"limit": 100}),
        ({"limit": 2000, "after": "c"}, {"limit": 500, "after": "c"}),
    ],
)
def test_rows_default_and_cap(
    http: Any, args: dict[str, Any], params: dict[str, Any]
) -> None:
    call("tinyfish_get_dataset_rows", {"dataset_id": "d1", **args})

    assert http.sent[0]["params"] == params


def test_cancel_targets_the_run(http: Any) -> None:
    http.reply(200, {"cancelled": True})

    out = call("tinyfish_cancel_dataset_run", {"dataset_id": "d1", "run_id": "r1"})

    assert http.sent[0]["url"] == f"{DATASETS}/d1/runs/r1/cancel"
    assert out == {"dataset_id": "d1", "cancelled": True}


def test_delete_returns_the_id(http: Any) -> None:
    out = call("tinyfish_delete_dataset", {"dataset_id": "d1"})

    assert http.sent[0]["method"] == "DELETE"
    assert out == {"dataset_id": "d1", "deleted": True}


@pytest.mark.parametrize(
    "tool", ["tinyfish_create_dataset", "tinyfish_populate_dataset"]
)
def test_billed_dataset_tools_follow_the_datasets_policy(
    monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    policy = {"tinyfish": {"credit_policy": {"datasets": "deny"}}}
    monkeypatch.setattr(config, "load_config", lambda: policy)

    assert pre_tool_call_policy(tool, {})["action"] == "block"  # type: ignore[index]
    policy["tinyfish"]["credit_policy"]["datasets"] = "request"
    assert pre_tool_call_policy(tool, {})["rule_key"] == "tinyfish:datasets"  # type: ignore[index]


def test_delete_always_asks_and_names_the_dataset(http: Any) -> None:
    http.reply(200, dataset("ready"))

    directive = pre_tool_call_policy("tinyfish_delete_dataset", {"dataset_id": "d1"})

    assert directive == {
        "action": "approve",
        "message": "Permanently delete TinyFish dataset 'Coffee' (d1)?",
        "rule_key": "tinyfish:dataset_delete:d1",
    }


def test_reset_always_asks_and_names_the_dataset(
    http: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = {"tinyfish": {"credit_policy": {"datasets": "allow"}}}
    monkeypatch.setattr(config, "load_config", lambda: policy)
    http.reply(200, dataset("ready"))
    args = {"dataset_id": "d1", "reset": True}

    directive = pre_tool_call_policy("tinyfish_populate_dataset", args)

    assert directive is not None
    assert directive["rule_key"] == "tinyfish:dataset_reset:d1"
    assert "'Coffee' (d1)" in directive["message"]
    assert (
        pre_tool_call_policy("tinyfish_populate_dataset", {"dataset_id": "d1"}) is None
    )
    policy["tinyfish"]["credit_policy"]["datasets"] = "deny"
    assert pre_tool_call_policy("tinyfish_populate_dataset", args)["action"] == "block"  # type: ignore[index]
