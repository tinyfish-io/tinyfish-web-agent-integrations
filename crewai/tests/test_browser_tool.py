import json

import pytest
from conftest import inject_client, ns

MODULE = "crewai_tinyfish.tinyfish_browser_tool"


def test_requires_api_key(monkeypatch, no_sdk_check):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    from crewai_tinyfish import TinyFishBrowserSessionTool

    with pytest.raises(ValueError):
        TinyFishBrowserSessionTool()


def test_happy_path(monkeypatch, api_key_env, no_sdk_check):
    captured = {}

    class FakeSessions:
        def create(self, **params):
            captured.update(params)
            return ns(
                session_id="br-123",
                cdp_url="wss://example.tinyfish.io/cdp",
                base_url="https://example.tinyfish.io",
            )

    inject_client(monkeypatch, MODULE, ns(browser=ns(sessions=FakeSessions())))

    from crewai_tinyfish import TinyFishBrowserSessionTool

    tool = TinyFishBrowserSessionTool()
    out = tool.run(url="https://scrapeme.live/shop", timeout_seconds=300)
    data = json.loads(out)

    assert captured["url"] == "https://scrapeme.live/shop"
    assert captured["timeout_seconds"] == 300
    assert data["cdp_url"] == "wss://example.tinyfish.io/cdp"
    assert data["session_id"] == "br-123"
