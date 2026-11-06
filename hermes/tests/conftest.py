from __future__ import annotations

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

tools_pkg = types.ModuleType("tools")
interrupt_mod = types.ModuleType("tools.interrupt")
interrupt_mod.is_interrupted = lambda: False  # type: ignore[attr-defined]
sys.modules.setdefault("tools", tools_pkg)
sys.modules["tools.interrupt"] = interrupt_mod


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    from tinyfish_hermes import rest_client

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
