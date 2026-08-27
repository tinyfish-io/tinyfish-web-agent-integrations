"""Credit policy gating for TinyFish features that consume credits."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .config import (
    CreditFeature,
    CreditPolicy,
    browser_cloud_provider,
    credit_policy,
    load_config,
    normalize_feature,
)

FEATURE_LABELS: dict[CreditFeature, str] = {
    "browser": "TinyFish Browser",
}


def target_domain(target: str | None) -> str:
    if not target:
        return ""
    parsed = urlparse(target)
    if parsed.netloc:
        return parsed.netloc
    return target[:120]


def policy_message(
    feature: CreditFeature | str, policy: CreditPolicy | None = None
) -> str:
    normalized = normalize_feature(str(feature))
    resolved = policy or credit_policy(normalized)
    return (
        f"{FEATURE_LABELS[normalized]} sessions consume TinyFish credits. "
        f"Current policy is '{resolved}'."
    )


def block_message(feature: CreditFeature | str) -> str:
    normalized = normalize_feature(str(feature))
    return (
        f"BLOCKED: {policy_message(normalized, 'deny')} "
        f"Set `tinyfish.credit_policy.{normalized}` to `request` (per-session "
        "approval) or `allow` in Hermes config; `hermes tinyfish browser` "
        "manages this setting."
    )


def approval_reason(
    feature: CreditFeature | str, operation: str, target: str | None = None
) -> str:
    normalized = normalize_feature(str(feature))
    domain = target_domain(target)
    target_text = f" Target: {domain}." if domain else ""
    return (
        f"{FEATURE_LABELS[normalized]} operation '{operation}' consumes "
        f"TinyFish credits.{target_text}"
    )


def request_credit_approval(
    feature: CreditFeature | str, operation: str, target: str | None = None
) -> tuple[bool, str]:
    normalized = normalize_feature(str(feature))
    policy = credit_policy(normalized)
    if policy == "deny":
        return False, block_message(normalized)
    if policy == "allow":
        return True, ""

    reason = approval_reason(normalized, operation, target)
    try:
        from tools.approval import request_tool_approval

        # Domain-grained key: one [a]lways covers the browse; new domains still prompt.
        result = request_tool_approval(
            f"tinyfish_{normalized}",
            reason,
            rule_key=f"tinyfish:{normalized}:{target_domain(target)}",
        )
    except Exception as exc:
        return False, (
            f"BLOCKED: {FEATURE_LABELS[normalized]} requires approval, but Hermes' "
            f"approval gate is unavailable ({exc})."
        )
    if result.get("approved"):
        return True, ""
    return False, str(
        result.get("message")
        or f"BLOCKED: approval required for {FEATURE_LABELS[normalized]}"
    )


def _directive_for_feature(
    feature: CreditFeature,
    operation: str,
    target: str | None,
    config: dict[str, Any] | None = None,
) -> dict[str, str] | None:
    policy = credit_policy(feature, config)
    if policy == "deny":
        return {"action": "block", "message": block_message(feature)}
    if policy == "request":
        return {
            "action": "approve",
            "message": approval_reason(feature, operation, target),
            "rule_key": f"tinyfish:{feature}:{target_domain(target)}",
        }
    return None


def pre_tool_call_policy(
    tool_name: str, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, str] | None:
    """Hermes plugin hook for policy-gating TinyFish credit-consuming tools."""

    params = args or {}

    if not tool_name.startswith("browser_"):
        return None
    config = load_config()
    if browser_cloud_provider(config) != "tinyfish":
        return None
    target = str(params.get("url") or params.get("target") or "")
    return _directive_for_feature("browser", tool_name, target, config)
