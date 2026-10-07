from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from tinyfish_hermes import agent_tool, rest_client
from tinyfish_hermes import browser_provider as browser_mod


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"runs": [], "cancelled": [], "started": {}}
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(agent_tool.time, "sleep", lambda seconds: None)

    def start_run(url: str, goal: str, **kwargs: Any) -> dict[str, Any]:
        state["started"] = {"url": url, "goal": goal, **kwargs}
        return {"run_id": "run_1"}

    def get_run(run_id: str, **kwargs: Any) -> dict[str, Any]:
        next_run = state["runs"].pop(0)
        if isinstance(next_run, Exception):
            raise next_run
        return next_run

    monkeypatch.setattr(rest_client, "start_run", start_run)
    monkeypatch.setattr(rest_client, "get_run", get_run)
    monkeypatch.setattr(
        rest_client,
        "cancel_run",
        lambda run_id, **kwargs: state["cancelled"].append(run_id) or {},
    )
    return state


def test_tf_agent_polls_until_completed(api: dict[str, Any]) -> None:
    api["runs"] = [
        {"run_id": "run_1", "status": "RUNNING"},
        rest_client.TinyFishRestError("blip"),
        {"run_id": "run_1", "status": "COMPLETED", "result": {"title": "Example"}},
    ]

    out = json.loads(
        agent_tool.tf_agent(
            {"url": "https://example.com", "goal": "title", "proxy_country_code": "US"}
        )
    )

    assert out == {
        "run_id": "run_1",
        "status": "COMPLETED",
        "result": {"title": "Example"},
    }
    assert api["started"]["browser_profile"] == "lite"
    assert api["started"]["proxy_country_code"] == "US"


def test_tf_agent_cancels_run_on_interrupt(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_tool, "_is_interrupted", lambda: True)

    out = json.loads(agent_tool.tf_agent({"url": "https://example.com", "goal": "x"}))

    assert out["status"] == "CANCELLED"
    assert api["cancelled"] == ["run_1"]


def test_tf_agent_returns_run_id_when_budget_runs_out(
    api: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_tool, "POLL_BUDGET_SECONDS", 0.0)

    out = json.loads(agent_tool.tf_agent({"url": "https://example.com", "goal": "x"}))

    assert out["run_id"] == "run_1"
    assert "run_id" in out["note"]


def test_tf_agent_truncates_large_results(api: dict[str, Any]) -> None:
    api["runs"] = [{"run_id": "run_1", "status": "COMPLETED", "result": "x" * 50_000}]

    text = agent_tool.tf_agent({"url": "https://example.com", "goal": "x"})

    assert len(text) < agent_tool.MAX_RESULT_CHARS + 200
    assert json.loads(text)["truncated"] is True


def test_tf_agent_requires_key_and_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    monkeypatch.delenv("MCP_TINYFISH_API_KEY", raising=False)
    assert "hermes tinyfish setup" in agent_tool.tf_agent({"url": "u", "goal": "g"})

    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    assert "url and goal" in agent_tool.tf_agent({"url": "https://example.com"})


def test_start_run_sends_dify_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class Response:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"run_id": "run_1"}

    def fake_request(method: str, url: str, **kwargs: Any) -> Response:
        captured.update(method=method, url=url, **kwargs)
        return Response()

    monkeypatch.setattr(rest_client.httpx, "request", fake_request)

    rest_client.start_run(
        "https://example.com", "goal", api_key="tf_test", proxy_country_code="GB"
    )

    assert captured["url"] == "https://agent.tinyfish.ai/v1/automation/run-async"
    assert captured["json"] == {
        "url": "https://example.com",
        "goal": "goal",
        "browser_profile": "lite",
        "api_integration": "hermes",
        "proxy_config": {"enabled": True, "country_code": "GB"},
    }


@pytest.mark.parametrize(
    ("reason", "provider", "expected"),
    [
        ("shutdown", "tinyfish", 1),
        ("new_session", "tinyfish", 0),
        ("shutdown", "browserbase", 0),
    ],
)
def test_shutdown_cleanup_only_on_process_shutdown(
    monkeypatch: pytest.MonkeyPatch, reason: str, provider: str, expected: int
) -> None:
    calls: list[str] = []
    lifecycle = types.ModuleType("tools.browser_tool_lifecycle")
    lifecycle.cleanup_all_browsers = lambda: calls.append("all")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tools.browser_tool_lifecycle", lifecycle)
    monkeypatch.setattr(browser_mod, "browser_cloud_provider", lambda: provider)

    browser_mod.shutdown_cleanup(session_id="s", reason=reason)

    assert len(calls) == expected
