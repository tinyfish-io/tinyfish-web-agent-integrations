from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WebSearchProvider:
    pass


agent_pkg = types.ModuleType("agent")
web_provider_mod = types.ModuleType("agent.web_search_provider")
web_provider_mod.WebSearchProvider = WebSearchProvider  # type: ignore[attr-defined]
sys.modules.setdefault("agent", agent_pkg)
sys.modules["agent.web_search_provider"] = web_provider_mod


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    # Hermes parses YAML; rendered descriptions are JSON-style quoted strings.
    head, _, body = content.removeprefix("---\n").partition("\n---\n")
    pairs = (line.split(": ", 1) for line in head.splitlines() if ": " in line)
    return {k: json.loads(v) if v.startswith('"') else v for k, v in pairs}, body


skill_utils_mod = types.ModuleType("agent.skill_utils")
skill_utils_mod.parse_frontmatter = _parse_frontmatter  # type: ignore[attr-defined]
sys.modules["agent.skill_utils"] = skill_utils_mod

tools_pkg = types.ModuleType("tools")
interrupt_mod = types.ModuleType("tools.interrupt")
interrupt_mod.is_interrupted = lambda: False  # type: ignore[attr-defined]
sys.modules.setdefault("tools", tools_pkg)
sys.modules["tools.interrupt"] = interrupt_mod


# Imported after the stubs above, which it needs at import time.
from tinyfish_hermes import rest_client, tool_helpers  # noqa: E402


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    # time_machine leaves monotonic and sleep real, so poll loops would really wait.
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    monkeypatch.setattr(tool_helpers.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(tool_helpers.time, "sleep", sleep)
    return now


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    sent: list[dict[str, Any]] = []
    replies: list[httpx.Response] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        sent.append(
            {
                "method": method,
                "url": url,
                "json": kwargs.get("json"),
                "params": kwargs.get("params"),
                "timeout": kwargs.get("timeout"),
            }
        )
        reply = replies.pop(0) if replies else httpx.Response(200, json={})
        reply.request = httpx.Request(method, url)
        return reply

    def reply(status: int, payload: Any, **headers: str) -> None:
        replies.append(httpx.Response(status, json=payload, headers=headers))

    monkeypatch.setattr(rest_client.httpx, "request", fake_request)
    return SimpleNamespace(sent=sent, replies=replies, reply=reply)
