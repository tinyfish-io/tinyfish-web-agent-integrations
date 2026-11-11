from __future__ import annotations

import json
from typing import Any

import pytest

from tinyfish_hermes import config, research_tools, rest_client
from tinyfish_hermes.credit_policy import pre_tool_call_policy

TOOLS = {schema["name"]: handler for schema, handler in research_tools.RESEARCH_TOOLS}
RUN_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
REPORT_URL = f"{rest_client.AGENT_URL}/research/{RUN_ID}"


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return json.loads(TOOLS[name](args))


def test_start_returns_the_run_and_report_link(http: Any) -> None:
    http.reply(200, {"research_run_id": RUN_ID, "error": None})

    out = call("tinyfish_start_deep_research", {"query": "LDES landscape", "mode": ""})

    assert http.sent[0]["url"] == (
        f"{rest_client.AGENT_URL}/v1/automation/run-research-async"
    )
    assert http.sent[0]["json"] == {"query": "LDES landscape"}
    assert out["research_run_id"] == RUN_ID
    assert out["status"] == "QUEUED"
    assert out["output_ready"] is False
    assert out["report_url"] == REPORT_URL
    assert f"research_run_id={RUN_ID}" in out["next_action"]


def test_start_refusal_points_at_running_reports(http: Any) -> None:
    http.reply(
        429,
        {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "5 research runs are already running",
                "details": {"active_research_run_ids": ["r1", "r2"]},
            }
        },
        **{"Retry-After": "30"},
    )

    out = call("tinyfish_start_deep_research", {"query": "q"})

    assert "5 research runs" in out["error"]
    assert out["retry_after_seconds"] == 30
    assert out["details"] == {"active_research_run_ids": ["r1", "r2"]}
    assert out["next_action"].startswith("Running now: r1, r2.")


def test_start_refusal_when_research_is_off(http: Any) -> None:
    http.reply(
        403,
        {"error": {"code": "FORBIDDEN", "message": "Research API is not available"}},
    )

    out = call("tinyfish_start_deep_research", {"query": "q"})

    assert out["next_action"].startswith("Research isn't enabled")


def test_get_returns_a_completed_report_at_once(http: Any, clock: list[float]) -> None:
    http.reply(
        200,
        {
            "research_run_id": RUN_ID,
            "status": "COMPLETED",
            "created_at": "2026-01-01T12:00:00Z",
            "completed_at": "2026-01-01T12:05:00Z",
            "deep_result": {
                "result": "# Report",
                "citations": ["https://a"],
                "termination_reason": "planner_done",
            },
        },
    )

    out = call("tinyfish_get_deep_research", {"research_run_id": RUN_ID})

    assert len(http.sent) == 1
    assert out == {
        "research_run_id": RUN_ID,
        "status": "COMPLETED",
        "elapsed_s": 300,
        "report_url": REPORT_URL,
        "output_ready": True,
        "report": "# Report",
        "citations": ["https://a"],
        "termination_reason": "planner_done",
    }


def test_get_polls_until_done(http: Any, clock: list[float]) -> None:
    running = {"research_run_id": RUN_ID, "status": "RUNNING"}
    http.reply(200, running)
    http.reply(200, {**running, "research_plan": {"q": []}})
    http.reply(200, {**running, "status": "FAILED", "error": {"message": "x"}})

    out = call("tinyfish_get_deep_research", {"research_run_id": RUN_ID})

    assert len(http.sent) == 3
    assert out["output_ready"] is False
    assert out["error"] == {"message": "x"}


def test_get_stops_at_budget_and_says_poll_again(http: Any, clock: list[float]) -> None:
    for _ in range(20):
        http.reply(
            200,
            {"research_run_id": RUN_ID, "status": "RUNNING", "evidence": [{}, {}]},
        )

    out = call("tinyfish_get_deep_research", {"research_run_id": RUN_ID})

    assert clock[0] < 25.0
    assert len(http.sent) == 9
    timeouts = [sent["timeout"] for sent in http.sent]
    assert timeouts[0] == 25.0 and timeouts == sorted(timeouts, reverse=True)
    assert out["output_ready"] is False
    assert out["progress"] == "Reading sources (2 so far)"
    assert "tinyfish_get_deep_research again" in out["next_action"]


def test_elapsed_handles_z_timestamps_without_completion() -> None:
    out = research_tools.research_status(
        {
            "research_run_id": RUN_ID,
            "status": "QUEUED",
            "created_at": "2000-01-01T00:00:00Z",
        }
    )

    assert out["elapsed_s"] > 0


def test_list_projects_rows_and_drops_reports(http: Any) -> None:
    http.reply(
        200,
        {
            "data": [
                {
                    "research_run_id": RUN_ID,
                    "query": "q" * 300,
                    "status": "COMPLETED",
                    "created_at": "2026-01-01T12:00:00Z",
                    "completed_at": None,
                    "deep_result": {"result": "huge"},
                    "quick_result": {"answer": "huge"},
                }
            ],
            "pagination": {"total": 1, "next_cursor": None, "has_more": False},
        },
    )

    out = call("tinyfish_list_deep_research", {"status": "COMPLETED", "limit": 5})

    assert http.sent[0]["params"] == {"status": "COMPLETED", "limit": 5}
    assert out["data"] == [
        {
            "research_run_id": RUN_ID,
            "query": "q" * 200,
            "status": "COMPLETED",
            "created_at": "2026-01-01T12:00:00Z",
            "completed_at": None,
            "report_url": REPORT_URL,
        }
    ]
    assert out["pagination"]["has_more"] is False


def test_cancel_posts_to_the_run(http: Any) -> None:
    call("tinyfish_cancel_deep_research", {"research_run_id": RUN_ID})

    assert http.sent[0]["method"] == "POST"
    assert (
        http.sent[0]["url"]
        == f"{rest_client.AGENT_URL}/v1/research-run/{RUN_ID}/cancel"
    )


def test_start_follows_the_research_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = {"tinyfish": {"credit_policy": {"research": "deny"}}}
    monkeypatch.setattr(config, "load_config", lambda: policy)
    tool = "tinyfish_start_deep_research"

    assert pre_tool_call_policy(tool, {})["action"] == "block"  # type: ignore[index]
    policy["tinyfish"]["credit_policy"]["research"] = "request"
    assert pre_tool_call_policy(tool, {})["rule_key"] == "tinyfish:research"  # type: ignore[index]
    assert pre_tool_call_policy("tinyfish_get_deep_research", {}) is None


@pytest.mark.parametrize("status", ["CANCELLED", "FAILED"])
def test_a_finished_run_without_error_never_says_poll_again(status: str) -> None:
    out = research_tools.research_status({"research_run_id": RUN_ID, "status": status})

    assert out["error"] == f"The run ended {status}"
    assert "next_action" not in out


def test_list_can_filter_timed_out_runs() -> None:
    lister = next(
        schema
        for schema, _ in research_tools.RESEARCH_TOOLS
        if schema["name"] == "tinyfish_list_deep_research"
    )

    assert "TIMED_OUT" in lister["parameters"]["properties"]["status"]["enum"]
