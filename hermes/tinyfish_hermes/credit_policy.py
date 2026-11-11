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
    "agent": "TinyFish Agent",
    "monitor": "TinyFish Monitors",
    "research": "TinyFish Deep Research",
    "dataset": "TinyFish Datasets",
}


def rule_key(feature: CreditFeature) -> str:
    # Domain-free so one [s]ession answer covers every step of the session.
    return f"tinyfish:{feature}"


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
        f"{FEATURE_LABELS[normalized]} consumes TinyFish credits. "
        f"Current policy is '{resolved}'."
    )


def block_message(feature: CreditFeature | str) -> str:
    normalized = normalize_feature(str(feature))
    return (
        f"BLOCKED: {policy_message(normalized, 'deny')} "
        f"Set `tinyfish.credit_policy.{normalized}` to `request` (per-session "
        f"approval) or `allow` with `hermes tinyfish credits set {normalized}`."
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

        result = request_tool_approval(
            f"tinyfish_{normalized}", reason, rule_key=rule_key(normalized)
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
            "rule_key": rule_key(feature),
        }
    return None


def _fetch_label(collection: str, item_id: str) -> str:
    from . import rest_client
    from .provider import _api_key

    # The approver needs the real name, not the agent's claim; the id alone still works.
    try:
        path = f"/v1/{collection}/{rest_client.quote_id(item_id)}"
        name = rest_client.agent_request(
            "GET", path, api_key=_api_key(), timeout=5.0
        ).get("name")
    except Exception:
        return item_id
    return f"'{name}' ({item_id})" if name else item_id


_CREDIT_FEATURE_BY_TOOL: dict[str, CreditFeature] = {
    "tinyfish_agent": "agent",
    "tinyfish_create_monitor": "monitor",
    "tinyfish_run_monitor": "monitor",
    "tinyfish_resume_monitor": "monitor",
    "tinyfish_start_deep_research": "research",
    "tinyfish_create_dataset": "dataset",
    "tinyfish_populate_dataset": "dataset",
}


def _charge_scope(tool_name: str, params: dict[str, Any]) -> str:
    rows = params.get("target_rows")
    match tool_name:
        case "tinyfish_create_monitor":
            config = params.get("config")
            config = config if isinstance(config, dict) else {}
            watched = str(config.get("url") or config.get("query") or "?")[:120]
            return (
                f" Watches {watched} on schedule '{params.get('schedule_cron')}', "
                "billing every check until paused or cancelled."
            )
        case "tinyfish_resume_monitor":
            return " Its scheduled checks bill again until paused or cancelled."
        case "tinyfish_create_dataset":
            return f" Fills up to {rows or 100} rows, $0.10 per complete row."
        case "tinyfish_populate_dataset":
            # Populate has no fixed default target, so an omitted one stays unnamed.
            target = f"up to {rows} rows" if rows else "an unspecified number of rows"
            return f" Fills {target}, $0.10 per complete row."
    return ""


def _delete_approval(kind: str, collection: str, item_id: str) -> dict[str, str]:
    # Keyed per item so one approval never covers deleting a different one.
    label = _fetch_label(collection, item_id)
    return {
        "action": "approve",
        "message": f"Permanently delete TinyFish {kind} {label}?",
        "rule_key": f"tinyfish:{kind}_delete:{item_id}",
    }


_DELETES: dict[str, tuple[str, str, str]] = {
    "tinyfish_delete_profile": ("profile", "profiles", "profile_id"),
    "tinyfish_cancel_monitor": ("monitor", "monitors", "monitor_id"),
    "tinyfish_delete_dataset": ("dataset", "datasets", "dataset_id"),
}


def _reset_approval(params: dict[str, Any]) -> dict[str, str]:
    dataset_id = str(params.get("dataset_id") or "")
    label = _fetch_label("datasets", dataset_id)
    # Reset deletes rows, so it asks even under `allow`, once per dataset.
    return {
        "action": "approve",
        "message": f"Empty TinyFish dataset {label} and refill it? Its current rows "
        "are deleted, and refilling consumes TinyFish credits."
        + _charge_scope("tinyfish_populate_dataset", params),
        "rule_key": f"tinyfish:dataset_reset:{dataset_id}",
    }


def _billed_directive(
    tool_name: str, params: dict[str, Any], target: str
) -> dict[str, str] | None:
    feature = _CREDIT_FEATURE_BY_TOOL[tool_name]
    directive = _directive_for_feature(feature, tool_name, target)
    blocked = directive is not None and directive["action"] == "block"
    if tool_name == "tinyfish_populate_dataset" and params.get("reset") and not blocked:
        return _reset_approval(params)
    if directive and not blocked:
        directive["message"] += _charge_scope(tool_name, params)
    return directive


def _schedule_change_directive(
    params: dict[str, Any], target: str
) -> dict[str, str] | None:
    # A new schedule is a new spend decision; fetch monitors have no floor.
    directive = _directive_for_feature("monitor", "tinyfish_update_monitor", target)
    if directive and directive["action"] == "approve":
        directive["message"] += (
            f" Changes the schedule to '{params['schedule_cron']}'; every check "
            "bills until paused or cancelled."
        )
    return directive


def pre_tool_call_policy(
    tool_name: str, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, str] | None:
    """Hermes plugin hook for policy-gating TinyFish credit-consuming tools."""

    params = args or {}
    target = str(params.get("url") or params.get("target") or "")
    if tool_name in _CREDIT_FEATURE_BY_TOOL:
        return _billed_directive(tool_name, params, target)
    if tool_name == "tinyfish_update_monitor" and params.get("schedule_cron"):
        return _schedule_change_directive(params, target)
    if tool_name in _DELETES:
        kind, collection, id_key = _DELETES[tool_name]
        return _delete_approval(kind, collection, str(params.get(id_key) or ""))
    if not tool_name.startswith("browser_"):
        return None
    config = load_config()
    if browser_cloud_provider(config) != "tinyfish":
        return None
    # Any browser_* call can open a billed session (first call, or after inactivity).
    return _directive_for_feature("browser", tool_name, target, config)
