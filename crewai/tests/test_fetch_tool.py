import json

import pytest
from conftest import inject_client, ns

MODULE = "crewai_tinyfish.tinyfish_fetch_tool"


def test_requires_api_key(monkeypatch, no_sdk_check):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    from crewai_tinyfish import TinyFishFetchTool

    with pytest.raises(ValueError):
        TinyFishFetchTool()


def test_happy_path_and_truncation(monkeypatch, api_key_env, no_sdk_check):
    captured = {}

    class FakeFetch:
        def get_contents(self, **params):
            captured.update(params)
            return ns(
                results=[
                    {
                        "url": "https://tinyfish.ai",
                        "final_url": "https://tinyfish.ai",
                        "title": "TinyFish",
                        "description": "infra",
                        "language": "en",
                        "format": "markdown",
                        "text": "x" * 100,
                    }
                ],
                errors=[],
            )

    inject_client(monkeypatch, MODULE, ns(fetch=FakeFetch()))

    from crewai_tinyfish import TinyFishFetchTool

    tool = TinyFishFetchTool()
    out = tool.run(urls=["https://tinyfish.ai"], max_chars_per_url=10)
    data = json.loads(out)

    assert captured["urls"] == ["https://tinyfish.ai"]
    assert captured["format"] == "markdown"
    assert data["results"][0]["text"].endswith("…[truncated]")
    assert data["errors"] == []


def test_per_url_errors_passthrough(monkeypatch, api_key_env, no_sdk_check):
    class FakeFetch:
        def get_contents(self, **params):
            return ns(
                results=[],
                errors=[{"url": "https://bad.example", "error": "bot_blocked", "status": None}],
            )

    inject_client(monkeypatch, MODULE, ns(fetch=FakeFetch()))

    from crewai_tinyfish import TinyFishFetchTool

    out = TinyFishFetchTool().run(urls=["https://bad.example"])
    data = json.loads(out)
    assert data["errors"][0]["error"] == "bot_blocked"
