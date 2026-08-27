from __future__ import annotations

import sys
import types

import pytest

from tinyfish_hermes import credit_policy as policy_mod
from tinyfish_hermes.config import (
    CREDIT_FEATURES,
    credit_policy,
    credit_policy_summary,
    normalize_feature,
    normalize_policy,
    set_credit_policy,
)
from tinyfish_hermes.credit_policy import pre_tool_call_policy, request_credit_approval


def test_browser_is_the_only_credit_feature_and_defaults_to_request() -> None:
    assert CREDIT_FEATURES == ("browser",)
    assert credit_policy("browser", {}) == "request"
    assert credit_policy_summary({}) == {"browser": "request"}


def test_unknown_credit_feature_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown TinyFish credit feature"):
        normalize_feature("agent")


def test_unknown_credit_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown TinyFish credit policy"):
        normalize_policy("maybe")


def test_set_credit_policy_round_trips() -> None:
    config: dict[str, object] = {}

    set_credit_policy(config, "browser", "deny")

    assert credit_policy("browser", config) == "deny"


def test_credit_policy_handles_malformed_section() -> None:
    assert (
        credit_policy("browser", {"tinyfish": {"credit_policy": "deny"}}) == "request"
    )


def _gated_config(policy: str | None = None) -> dict[str, object]:
    config: dict[str, object] = {"browser": {"cloud_provider": "tinyfish"}}
    if policy is not None:
        config["tinyfish"] = {"credit_policy": {"browser": policy}}
    return config


def test_pre_tool_policy_requests_browser_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "load_config", _gated_config)

    directive = pre_tool_call_policy(
        "browser_navigate", {"url": "https://example.com/path"}
    )

    assert directive is not None
    assert directive["action"] == "approve"
    assert "example.com" in directive["message"]
    assert directive["rule_key"] == "tinyfish:browser:example.com"


def test_pre_tool_policy_rule_key_is_domain_grained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # One [a]lways answer must cover every browser_* step on the same domain.
    monkeypatch.setattr(policy_mod, "load_config", _gated_config)

    navigate = pre_tool_call_policy(
        "browser_navigate", {"url": "https://example.com/a"}
    )
    click = pre_tool_call_policy("browser_click", {"url": "https://example.com/b"})
    other = pre_tool_call_policy("browser_navigate", {"url": "https://other.example"})

    assert navigate is not None and click is not None and other is not None
    assert navigate["rule_key"] == click["rule_key"] == "tinyfish:browser:example.com"
    assert other["rule_key"] == "tinyfish:browser:other.example"


def test_pre_tool_policy_reads_config_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def counting_load_config() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return _gated_config()

    monkeypatch.setattr(policy_mod, "load_config", counting_load_config)

    pre_tool_call_policy("browser_navigate", {"url": "https://example.com"})
    assert calls == 1

    pre_tool_call_policy("web_search", {"query": "tinyfish"})
    assert calls == 1


def test_pre_tool_policy_blocks_browser_when_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "load_config", lambda: _gated_config("deny"))

    directive = pre_tool_call_policy("browser_open", {"target": "example.com"})

    assert directive is not None
    assert directive["action"] == "block"
    assert "policy is 'deny'" in directive["message"]
    assert "tinyfish.credit_policy.browser" in directive["message"]


def test_pre_tool_policy_allows_browser_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "load_config", lambda: _gated_config("allow"))

    assert (
        pre_tool_call_policy("browser_navigate", {"url": "https://example.com"}) is None
    )


def test_pre_tool_policy_does_not_gate_other_browser_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        policy_mod, "load_config", lambda: {"browser": {"cloud_provider": "local"}}
    )

    assert (
        pre_tool_call_policy("browser_navigate", {"url": "https://example.com"}) is None
    )


def test_pre_tool_policy_ignores_non_browser_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "load_config", _gated_config)

    assert pre_tool_call_policy("web_search", {"query": "tinyfish"}) is None


def test_request_credit_approval_honors_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "allow")

    assert request_credit_approval("browser", "create") == (True, "")


def test_request_credit_approval_honors_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "deny")

    approved, message = request_credit_approval("browser", "create")

    assert approved is False
    assert message.startswith("BLOCKED:")


def test_request_credit_approval_uses_hermes_gate_with_domain_rule_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")
    seen: dict[str, object] = {}

    def fake_approval(name: str, reason: str, **kwargs: object) -> dict[str, object]:
        seen.update(name=name, reason=reason, **kwargs)
        return {"approved": True}

    approval_mod = types.ModuleType("tools.approval")
    approval_mod.request_tool_approval = fake_approval  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tools.approval", approval_mod)

    assert request_credit_approval("browser", "create", "https://example.com/path") == (
        True,
        "",
    )
    assert seen["rule_key"] == "tinyfish:browser:example.com"


def test_request_credit_approval_reports_gate_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")
    approval_mod = types.ModuleType("tools.approval")
    approval_mod.request_tool_approval = (  # type: ignore[attr-defined]
        lambda *args, **kwargs: {
            "approved": False,
            "message": "Approval denied by user.",
        }
    )
    monkeypatch.setitem(sys.modules, "tools.approval", approval_mod)

    assert request_credit_approval("browser", "create") == (
        False,
        "Approval denied by user.",
    )


def test_request_credit_approval_blocks_when_gate_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")
    monkeypatch.delitem(sys.modules, "tools.approval", raising=False)

    approved, message = request_credit_approval("browser", "create")

    assert approved is False
    assert "approval gate is unavailable" in message
