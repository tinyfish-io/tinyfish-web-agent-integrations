from __future__ import annotations

import argparse
import json
from typing import Any

import pytest

from tinyfish_hermes import rest_client
from tinyfish_hermes import setup_cli as cli


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    cli.setup_tinyfish_cli(parser)
    return parser


def _configured_config(**overrides: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "web": {"search_backend": "tinyfish", "extract_backend": "tinyfish"},
    }
    config.update(overrides)
    return config


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.search_result: dict[str, Any] = {
            "success": True,
            "data": {"web": [{"url": "https://example.com"}]},
        }
        self.fetch_result: list[dict[str, Any]] = [{"content": "ok"}]
        self.search_exception: Exception | None = None
        self.fetch_exception: Exception | None = None

    def is_available(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        assert query and limit == 1
        self.calls.append("search")
        if self.search_exception is not None:
            raise self.search_exception
        return self.search_result

    def extract(self, urls: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        assert urls == ["https://docs.tinyfish.ai/"]
        assert kwargs.get("format") == "markdown"
        self.calls.append("fetch")
        if self.fetch_exception is not None:
            raise self.fetch_exception
        return self.fetch_result


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Fake Hermes config/env layer shared by CLI tests."""

    state: dict[str, Any] = {
        "config": _configured_config(),
        "saved_configs": [],
        "env": {"TINYFISH_API_KEY": "tf_test"},
        "saved_env": [],
        "provider": FakeProvider(),
    }
    monkeypatch.setattr(cli, "_load_config", lambda: state["config"])
    monkeypatch.setattr(
        cli, "_save_config", lambda config: state["saved_configs"].append(config)
    )
    monkeypatch.setattr(cli, "_get_env", lambda name: state["env"].get(name, ""))

    def fake_save_env_secure(name: str, value: str) -> dict[str, Any]:
        state["saved_env"].append((name, value))
        return {"success": True, "stored_as": name, "validated": False}

    monkeypatch.setattr(cli, "_save_env_secure", fake_save_env_secure)
    monkeypatch.setattr(
        cli, "_read_saved_env", lambda name: dict(state["saved_env"]).get(name, "")
    )
    monkeypatch.setattr(
        cli, "_api_key", lambda: state["env"].get("TINYFISH_API_KEY", "")
    )
    monkeypatch.setattr(cli, "TinyFishWebSearchProvider", lambda: state["provider"])
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    return state


def test_setup_writes_web_backends(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = {}
    args = _parser().parse_args(["setup", "--yes"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    saved = env["saved_configs"][-1]
    assert saved["web"]["search_backend"] == "tinyfish"
    assert saved["web"]["extract_backend"] == "tinyfish"
    assert saved["web"]["backend"] == "tinyfish"
    assert "doctor --live" in capsys.readouterr().out


def test_setup_preserves_existing_shared_backend(env: dict[str, Any]) -> None:
    env["config"] = {"web": {"backend": "tavily"}}
    args = _parser().parse_args(["setup", "--yes"])

    cli.dispatch_tinyfish_cli(args)

    saved = env["saved_configs"][-1]
    assert saved["web"]["backend"] == "tavily"
    assert saved["web"]["search_backend"] == "tinyfish"


def test_setup_respects_no_web_backend(env: dict[str, Any]) -> None:
    env["config"] = {}
    args = _parser().parse_args(["setup", "--yes", "--no-web-backend"])

    cli.dispatch_tinyfish_cli(args)

    assert env["saved_configs"] == []


def test_setup_non_tty_without_yes_does_not_write_config(env: dict[str, Any]) -> None:
    # A piped setup must not rewrite config without explicit --yes opt-in.
    env["config"] = {}
    args = _parser().parse_args(["setup"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    assert env["saved_configs"] == []


def test_setup_saves_api_key(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["setup", "--yes", "--api-key", "tf_new"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    assert env["saved_env"] == [("TINYFISH_API_KEY", "tf_new")]
    assert "Saved TINYFISH_API_KEY" in capsys.readouterr().out


def test_setup_key_save_refusal_exits_nonzero(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A managed install refuses the write while the secure save still reports success.
    monkeypatch.setattr(cli, "_read_saved_env", lambda name: "")
    args = _parser().parse_args(["setup", "--yes", "--api-key", "tf_new"])

    assert cli.dispatch_tinyfish_cli(args) == 1

    captured = capsys.readouterr()
    assert "Could not save TINYFISH_API_KEY" in captured.err
    assert "Saved TINYFISH_API_KEY" not in captured.out


def test_setup_warns_when_shell_var_shadows_saved_key(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_stale_shell_value")
    args = _parser().parse_args(["setup", "--yes", "--api-key", "tf_new"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    out = capsys.readouterr().out
    assert "Saved TINYFISH_API_KEY" in out
    assert "shadows it at runtime" in out


def test_setup_never_writes_mcp_config(env: dict[str, Any]) -> None:
    env["config"] = {}
    args = _parser().parse_args(["setup", "--yes"])

    cli.dispatch_tinyfish_cli(args)

    assert "mcp_servers" not in env["saved_configs"][-1]


def test_setup_live_runs_doctor(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["setup", "--yes", "--live"])

    exit_code = cli.dispatch_tinyfish_cli(args, provider=env["provider"])

    assert exit_code == 0
    assert env["provider"].calls == ["search", "fetch"]
    assert "live_search_ok: yes" in capsys.readouterr().out


def test_status_reports_non_secret_fields(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["status", "--json"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["api_key_env_var"] == "TINYFISH_API_KEY"
    assert payload["api_key_configured"] is True
    assert payload["web_backend_configured"] is True
    assert payload["credit_policy"] == {"browser": "request"}
    assert payload["routing_context_enabled"] is True
    assert payload["mcp_configured"] is False
    assert payload["plugin_version"]


def test_status_reports_cli_seeded_key_name(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["env"] = {"MCP_TINYFISH_API_KEY": "tf_cli"}
    args = _parser().parse_args(["status", "--json"])

    cli.dispatch_tinyfish_cli(args)

    assert (
        json.loads(capsys.readouterr().out)["api_key_env_var"] == "MCP_TINYFISH_API_KEY"
    )


def test_status_never_prints_key_value(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["env"] = {"TINYFISH_API_KEY": "tf_secret_value"}

    cli.dispatch_tinyfish_cli(_parser().parse_args(["status"]))
    cli.dispatch_tinyfish_cli(_parser().parse_args(["status", "--json"]))

    assert "tf_secret_value" not in capsys.readouterr().out


def test_dispatch_defaults_to_status(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace()

    assert cli.dispatch_tinyfish_cli(args) == 0
    assert "TinyFish Hermes plugin status" in capsys.readouterr().out


def test_doctor_ok_exits_zero(env: dict[str, Any]) -> None:
    args = _parser().parse_args(["doctor"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 0


def test_doctor_unconfigured_recommends_setup(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = {}
    env["env"] = {}
    args = _parser().parse_args(["doctor"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1
    assert (
        "Recommended next step: run `hermes tinyfish setup`." in capsys.readouterr().out
    )


def test_doctor_live_success(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["doctor", "--live", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["live_search_ok"] is True
    assert payload["live_fetch_ok"] is True
    assert env["provider"].calls == ["search", "fetch"]


def test_doctor_live_failure_recommends_key_check(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["provider"].search_result = {
        "success": False,
        "error": "TinyFish REST search failed",
    }
    args = _parser().parse_args(["doctor", "--live"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1

    out = capsys.readouterr().out
    assert "Recommended next step: verify your TinyFish API key" in out


def test_doctor_live_exception_reports_safe_error(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["provider"].search_exception = RuntimeError("tf_secret in exception text")
    env["provider"].fetch_exception = RuntimeError("tf_secret in exception text")
    args = _parser().parse_args(["doctor", "--live", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert (
        payload["live_search_error"] == "TinyFish Search check failed (RuntimeError)."
    )
    assert payload["live_fetch_error"] == "TinyFish Fetch check failed (RuntimeError)."
    assert "tf_secret" not in json.dumps(payload)


def test_doctor_live_fetch_error_document_fails_check(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["provider"].fetch_result = [{"content": "", "error": "fetch blocked"}]
    args = _parser().parse_args(["doctor", "--live", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1
    assert json.loads(capsys.readouterr().out)["live_fetch_error"] == "fetch blocked"


def test_doctor_live_paid_denied_policy_fails(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(tinyfish={"credit_policy": {"browser": "deny"}})
    args = _parser().parse_args(["doctor", "--live-paid", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["live_paid_ok"] is False
    assert payload["live_paid_error"] == "TinyFish browser policy is deny."


def test_doctor_live_paid_success(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env["config"] = _configured_config(tinyfish={"credit_policy": {"browser": "allow"}})
    monkeypatch.setattr(
        cli,
        "request_credit_approval",
        lambda feature, operation, target=None: (True, ""),
    )
    monkeypatch.setattr(
        rest_client, "create_browser_session", lambda **kwargs: {"session_id": "sess_1"}
    )
    monkeypatch.setattr(
        rest_client, "close_browser_session", lambda session_id, *, api_key: True
    )
    args = _parser().parse_args(["doctor", "--live-paid", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["live_paid_ok"] is True
    assert payload["live_paid_browser_cleanup_ok"] is True


def test_doctor_live_paid_missing_session_id_notes_inactivity_expiry(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "request_credit_approval",
        lambda feature, operation, target=None: (True, ""),
    )
    monkeypatch.setattr(rest_client, "create_browser_session", lambda **kwargs: {})
    monkeypatch.setattr(
        rest_client,
        "close_browser_session",
        lambda session_id, *, api_key: pytest.fail("nothing closeable"),
    )
    args = _parser().parse_args(["doctor", "--live-paid", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["live_paid_ok"] is False
    assert "1h inactivity timeout" in payload["live_paid_error"]


def test_doctor_live_paid_cleanup_failure_fails_and_recommends_policy_review(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "request_credit_approval",
        lambda feature, operation, target=None: (True, ""),
    )
    monkeypatch.setattr(
        rest_client, "create_browser_session", lambda **kwargs: {"session_id": "sess_1"}
    )
    monkeypatch.setattr(
        rest_client, "close_browser_session", lambda session_id, *, api_key: False
    )
    args = _parser().parse_args(["doctor", "--live-paid"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1

    out = capsys.readouterr().out
    assert "live_paid_error: TinyFish Browser session cleanup failed." in out
    assert "Recommended next step: review the browser credit policy" in out


def test_doctor_live_paid_approval_denial_fails(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "request_credit_approval",
        lambda feature, operation, target=None: (False, "Approval denied by user."),
    )
    args = _parser().parse_args(["doctor", "--live-paid", "--json"])

    assert cli.dispatch_tinyfish_cli(args, provider=env["provider"]) == 1
    assert (
        json.loads(capsys.readouterr().out)["live_paid_error"]
        == "Approval denied by user."
    )


def test_credits_status_json(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["credits", "status", "--json"])

    assert cli.dispatch_tinyfish_cli(args) == 0
    assert json.loads(capsys.readouterr().out) == {
        "credit_policy": {"browser": "request"}
    }


def test_credits_set_saves_policy(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["credits", "set", "browser", "allow"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    saved = env["saved_configs"][-1]
    assert saved["tinyfish"]["credit_policy"] == {"browser": "allow"}
    assert "Set TinyFish browser credit policy to allow." in capsys.readouterr().out


def test_credits_reset_restores_request_default(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(tinyfish={"credit_policy": {"browser": "deny"}})
    args = _parser().parse_args(["credits", "reset"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    saved = env["saved_configs"][-1]
    assert saved["tinyfish"]["credit_policy"] == {"browser": "request"}
    out = capsys.readouterr().out
    assert "request" in out
    assert "deny" not in out


def test_browser_enable_sets_cloud_provider(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parser().parse_args(["browser", "enable"])

    assert cli.dispatch_tinyfish_cli(args) == 0

    assert env["saved_configs"][-1]["browser"]["cloud_provider"] == "tinyfish"
    out = capsys.readouterr().out
    assert "Set browser.cloud_provider to tinyfish." in out
    assert "Policy 'request'" in out


def test_browser_enable_is_idempotent(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(browser={"cloud_provider": "tinyfish"})

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["browser", "enable"])) == 0

    assert env["saved_configs"] == []
    assert "already" in capsys.readouterr().out


def test_browser_disable_removes_only_tinyfish(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(browser={"cloud_provider": "tinyfish"})

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["browser", "disable"])) == 0

    assert "cloud_provider" not in env["saved_configs"][-1]["browser"]
    assert "Removed browser.cloud_provider" in capsys.readouterr().out


def test_browser_disable_leaves_other_provider_alone(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(browser={"cloud_provider": "browserbase"})

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["browser", "disable"])) == 0

    assert env["saved_configs"] == []
    assert "nothing to change" in capsys.readouterr().out


def test_browser_status_reports_provider_and_policy(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["config"] = _configured_config(browser={"cloud_provider": "tinyfish"})

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["browser", "status"])) == 0

    out = capsys.readouterr().out
    assert "browser.cloud_provider: tinyfish" in out
    assert "tinyfish.credit_policy.browser: request" in out


def test_usage_prints_wallet(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        rest_client,
        "wallet",
        lambda *, api_key, timeout=30.0: {
            "available_balance": "12.34",
            "currency": "USD",
            "as_of": "2026-08-26T00:00:00Z",
            "auto_reload": {"state": "enabled", "threshold": "5", "recharge_to": "25"},
            "pending_top_up": None,
            "rates": {
                "meters": [
                    {
                        "label": "Browser",
                        "unit_amount": "0.01",
                        "currency": "USD",
                        "per": "minute",
                    }
                ]
            },
        },
    )

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["usage"])) == 0

    out = capsys.readouterr().out
    assert "Available balance: $12.34 USD" in out
    assert "Auto-reload: enabled (at $5 USD, recharge to $25 USD)" in out
    assert "Browser: $0.01 USD per minute" in out


def test_usage_wallet_not_found_is_friendly_success(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_not_found(*, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
        raise rest_client.TinyFishWalletNotFound("no wallet")

    monkeypatch.setattr(rest_client, "wallet", raise_not_found)

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["usage"])) == 0

    out = capsys.readouterr().out
    assert "Wallet balance unavailable." in out
    assert cli.API_KEY_URL in out


def test_usage_error_exits_nonzero(
    env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_error(*, api_key: str, timeout: float = 30.0) -> dict[str, Any]:
        raise rest_client.TinyFishRestError("TinyFish Wallet returned HTTP 500")

    monkeypatch.setattr(rest_client, "wallet", raise_error)

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["usage"])) == 1
    assert "Error: TinyFish Wallet returned HTTP 500" in capsys.readouterr().out


def test_usage_requires_api_key(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["env"] = {}

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["usage"])) == 1
    assert "TINYFISH_API_KEY" in capsys.readouterr().err


def test_usage_missing_key_with_json_emits_json_payload(
    env: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    env["env"] = {}

    assert cli.dispatch_tinyfish_cli(_parser().parse_args(["usage", "--json"])) == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["success"] is False
    assert payload["wallet_available"] is None
    assert "TINYFISH_API_KEY" in payload["error"]
    assert captured.err == ""


def test_in_session_status_command(env: dict[str, Any]) -> None:
    provider = env["provider"]

    text = cli.tinyfish_status_command("", provider=provider)
    assert "TinyFish Hermes plugin status" in text
    assert provider.calls == []

    live_text = cli.tinyfish_status_command("live", provider=provider)
    assert "live_search_ok: yes" in live_text
    assert provider.calls == ["search", "fetch"]

    assert cli.tinyfish_status_command("bogus", provider=provider) == (
        "Usage: /tinyfish-status [live]"
    )
