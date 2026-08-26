from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest

from tinyfish_hermes import rest_client
from tinyfish_hermes.browser_provider import TinyFishBrowserProvider


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    monkeypatch.delenv("MCP_TINYFISH_API_KEY", raising=False)
    yield


def test_browser_provider_unavailable_without_api_key() -> None:
    assert TinyFishBrowserProvider().is_available() is False


def test_browser_provider_available_by_default_with_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # First-party default policy is 'request', so a key alone enables the provider.
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    assert TinyFishBrowserProvider().is_available() is True


def test_browser_provider_accepts_cli_seeded_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_TINYFISH_API_KEY", "tf_cli")

    assert TinyFishBrowserProvider().is_available() is True


def test_browser_provider_unavailable_when_policy_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        "tinyfish_hermes.browser_provider.credit_policy", lambda feature: "deny"
    )

    assert TinyFishBrowserProvider().is_available() is False


def test_browser_provider_create_session_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        "tinyfish_hermes.browser_provider.credit_policy", lambda feature: "allow"
    )
    monkeypatch.setattr(
        rest_client,
        "create_browser_session",
        lambda **kwargs: {
            "session_id": "sess_123",
            "cdp_url": "wss://example.com/devtools",
            "base_url": "https://example.com",
        },
    )

    result = TinyFishBrowserProvider().create_session("task")

    assert result["bb_session_id"] == "sess_123"
    assert result["cdp_url"] == "wss://example.com/devtools"
    features: Any = result["features"]
    assert features["tinyfish"] is True
    assert features["credit_policy"] == "allow"
    assert str(result["session_name"]).startswith("tinyfish_task_")


def test_browser_provider_create_session_requires_key() -> None:
    with pytest.raises(ValueError, match="TINYFISH_API_KEY"):
        TinyFishBrowserProvider().create_session("task")


def test_browser_provider_create_session_blocked_when_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        "tinyfish_hermes.browser_provider.credit_policy", lambda feature: "deny"
    )

    with pytest.raises(ValueError, match="tinyfish.credit_policy.browser"):
        TinyFishBrowserProvider().create_session("task")


def test_browser_provider_create_session_rejects_incomplete_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "create_browser_session",
        lambda **kwargs: {"session_id": "sess_123"},
    )

    with pytest.raises(RuntimeError, match="session_id and cdp_url"):
        TinyFishBrowserProvider().create_session("task")


def test_browser_provider_passes_configured_session_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        "tinyfish_hermes.browser_provider.tinyfish_config",
        lambda: {"browser": {"timeout_seconds": "120"}},
    )
    seen: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return {"session_id": "sess_123", "cdp_url": "wss://example.com/devtools"}

    monkeypatch.setattr(rest_client, "create_browser_session", fake_create)

    TinyFishBrowserProvider().create_session("task")

    assert seen == {"api_key": "tf_test", "timeout_seconds": 120}


def test_browser_provider_close_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen: dict[str, Any] = {}

    def fake_close(session_id: str, *, api_key: str) -> bool:
        seen["session_id"] = session_id
        seen["api_key"] = api_key
        return True

    monkeypatch.setattr(rest_client, "close_browser_session", fake_close)

    assert TinyFishBrowserProvider().close_session("sess_123") is True
    assert seen == {"session_id": "sess_123", "api_key": "tf_test"}


def test_browser_provider_close_session_never_raises(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    def raise_unexpected(session_id: str, *, api_key: str) -> bool:
        raise RuntimeError(f"unexpected close failure for {session_id}")

    monkeypatch.setattr(rest_client, "close_browser_session", raise_unexpected)

    with caplog.at_level(logging.DEBUG):
        assert TinyFishBrowserProvider().close_session("sess_secret") is False

    assert "sess_secret" not in caplog.text


def test_browser_provider_cleanup_logs_do_not_expose_session_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    provider = TinyFishBrowserProvider()

    with caplog.at_level(logging.DEBUG):
        assert provider.close_session("sess_secret") is False

        def fail_close(session_id: str) -> bool:
            raise RuntimeError(f"failed to close {session_id}")

        monkeypatch.setattr(provider, "close_session", fail_close)
        provider.emergency_cleanup("sess_secret")

    assert "sess_secret" not in caplog.text
    assert "failed to close" not in caplog.text


def test_browser_setup_schema_mentions_credits_without_disclaimers() -> None:
    schema = TinyFishBrowserProvider().get_setup_schema()

    assert "consumes TinyFish credits" in schema["tag"]
    assert "independent" not in schema["tag"].lower()
    assert schema["env_vars"][0]["key"] == "TINYFISH_API_KEY"
