import json

import pytest
from conftest import inject_client, ns

MODULE = "crewai_tinyfish.tinyfish_agent_tool"


def test_requires_api_key(monkeypatch, no_sdk_check):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    from crewai_tinyfish import TinyFishAgentTool

    with pytest.raises(ValueError):
        TinyFishAgentTool()


def test_happy_path_builds_expected_kwargs(monkeypatch, api_key_env, no_sdk_check):
    captured = {}

    class FakeAgent:
        def run(self, **kwargs):
            captured.update(kwargs)
            return ns(
                run_id="run_123",
                status="COMPLETED",
                num_of_steps=3,
                result={"price": "$799"},
                error=None,
            )

    inject_client(monkeypatch, MODULE, ns(agent=FakeAgent()))

    from crewai_tinyfish import TinyFishAgentTool

    tool = TinyFishAgentTool()
    out = tool.run(
        url="https://scrapeme.live/shop",
        goal="Extract first product price. Return JSON.",
        use_proxy=True,
        proxy_country="us",
        use_profile=True,
        profile_id="prof_abc",
    )
    data = json.loads(out)

    assert captured["url"] == "https://scrapeme.live/shop"
    assert captured["use_profile"] is True
    assert captured["profile_id"] == "prof_abc"
    # proxy_config is a real tinyfish ProxyConfig when the SDK is installed, or the
    # documented dict fallback otherwise. Read fields tolerantly for both shapes.
    proxy = captured["proxy_config"]
    enabled = proxy["enabled"] if isinstance(proxy, dict) else getattr(proxy, "enabled")
    country = proxy["country_code"] if isinstance(proxy, dict) else getattr(proxy, "country_code")
    assert enabled is True
    assert str(getattr(country, "value", country)).upper() == "US"
    assert data["status"] == "COMPLETED"
    assert data["result"]["price"] == "$799"


def test_failed_run_surfaces_error(monkeypatch, api_key_env, no_sdk_check):
    class FakeAgent:
        def run(self, **kwargs):
            return ns(
                run_id="run_x",
                status="FAILED",
                num_of_steps=1,
                result=None,
                error={"code": "SITE_BLOCKED", "message": "blocked", "category": "AGENT_FAILURE"},
            )

    inject_client(monkeypatch, MODULE, ns(agent=FakeAgent()))

    from crewai_tinyfish import TinyFishAgentTool

    out = TinyFishAgentTool().run(url="https://x.com", goal="do it")
    data = json.loads(out)
    assert data["status"] == "FAILED"
    assert data["error"]["code"] == "SITE_BLOCKED"
