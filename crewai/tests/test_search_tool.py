import json

import pytest
from conftest import inject_client, ns

MODULE = "crewai_tinyfish.tinyfish_search_tool"


def test_requires_api_key(monkeypatch, no_sdk_check):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    from crewai_tinyfish import TinyFishSearchTool

    with pytest.raises(ValueError):
        TinyFishSearchTool()


def test_happy_path(monkeypatch, api_key_env, no_sdk_check):
    captured = {}

    class FakeSearch:
        def query(self, **params):
            captured.update(params)
            return ns(
                query=params["query"],
                total_results=1,
                results=[
                    {
                        "position": 1,
                        "title": "TinyFish",
                        "url": "https://tinyfish.ai",
                        "snippet": "web agent infra",
                        "site_name": "tinyfish.ai",
                    }
                ],
            )

    inject_client(monkeypatch, MODULE, ns(search=FakeSearch()))

    from crewai_tinyfish import TinyFishSearchTool

    tool = TinyFishSearchTool()
    out = tool.run(query="web automation tools", location="US", max_results=5)
    data = json.loads(out)

    assert captured["query"] == "web automation tools"
    assert captured["location"] == "US"
    assert data["results"][0]["url"] == "https://tinyfish.ai"


def test_errors_are_returned_as_strings(monkeypatch, api_key_env, no_sdk_check):
    class FakeSearch:
        def query(self, **params):
            raise RuntimeError("boom")

    inject_client(monkeypatch, MODULE, ns(search=FakeSearch()))

    from crewai_tinyfish import TinyFishSearchTool

    out = TinyFishSearchTool().run(query="x")
    assert "TinyFish Search failed" in out
