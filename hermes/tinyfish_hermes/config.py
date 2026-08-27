"""Read the ``tinyfish`` section of Hermes' user configuration."""

from __future__ import annotations

from typing import Any, Literal

CreditFeature = Literal["browser"]
CreditPolicy = Literal["deny", "request", "allow"]

CREDIT_FEATURES: tuple[CreditFeature, ...] = ("browser",)
CREDIT_POLICIES: tuple[CreditPolicy, ...] = ("deny", "request", "allow")
# 'request' is inert until browser.cloud_provider is tinyfish, and still
# routes each session through Hermes approval once it is.
DEFAULT_CREDIT_POLICY: CreditPolicy = "request"

SearchOptions = dict[str, Any]
FetchOptions = dict[str, Any]


def load_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config as _load_config

        return dict(_load_config() or {})
    except Exception:  # config layer is optional outside Hermes
        return {}


def save_config(config: dict[str, Any]) -> None:
    from hermes_cli.config import save_config as _save_config

    _save_config(config)


def tinyfish_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config() if config is None else config
    section = cfg.get("tinyfish") or {}
    return section if isinstance(section, dict) else {}


def normalize_feature(value: str) -> CreditFeature:
    if value.strip().lower().replace("_", "-") == "browser":
        return "browser"
    raise ValueError(
        f"Unknown TinyFish credit feature '{value}'. Valid features: browser"
    )


def normalize_policy(value: Any) -> CreditPolicy:
    policy = str(value or DEFAULT_CREDIT_POLICY).strip().lower()
    if policy not in CREDIT_POLICIES:
        valid = ", ".join(CREDIT_POLICIES)
        raise ValueError(
            f"Unknown TinyFish credit policy '{value}'. Valid policies: {valid}"
        )
    return policy


def credit_policy(
    feature: CreditFeature | str, config: dict[str, Any] | None = None
) -> CreditPolicy:
    normalized = normalize_feature(str(feature))
    policies = tinyfish_config(config).get("credit_policy") or {}
    if not isinstance(policies, dict):
        return DEFAULT_CREDIT_POLICY
    return normalize_policy(policies.get(normalized, DEFAULT_CREDIT_POLICY))


def set_credit_policy(
    config: dict[str, Any], feature: CreditFeature | str, policy: CreditPolicy | str
) -> None:
    normalized_feature = normalize_feature(str(feature))
    normalized_policy = normalize_policy(policy)
    section = config.setdefault("tinyfish", {})
    if not isinstance(section, dict):
        section = {}
        config["tinyfish"] = section
    policies = section.setdefault("credit_policy", {})
    if not isinstance(policies, dict):
        policies = {}
        section["credit_policy"] = policies
    policies[normalized_feature] = normalized_policy


def credit_policy_summary(
    config: dict[str, Any] | None = None,
) -> dict[CreditFeature, CreditPolicy]:
    return {feature: credit_policy(feature, config) for feature in CREDIT_FEATURES}


def routing_context_enabled(config: dict[str, Any] | None = None) -> bool:
    value = _bool_option(tinyfish_config(config).get("routing_context"))
    return True if value is None else value


def browser_cloud_provider(config: dict[str, Any] | None = None) -> str:
    cfg = load_config() if config is None else config
    section = cfg.get("browser") or {}
    if not isinstance(section, dict):
        return ""
    return str(section.get("cloud_provider") or "").strip().lower()


def _int_option(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_option(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def search_options(config: dict[str, Any] | None = None) -> SearchOptions:
    section = tinyfish_config(config).get("search") or {}
    if not isinstance(section, dict):
        return {}
    options: SearchOptions = {}
    for key in (
        "location",
        "language",
        "after_date",
        "before_date",
        "domain_type",
        "purpose",
    ):
        value = section.get(key)
        if value not in (None, ""):
            options[key] = str(value)
    for key in ("recency_minutes", "page"):
        value = _int_option(section.get(key))
        if value is not None:
            options[key] = value
    return options


def fetch_options(config: dict[str, Any] | None = None) -> FetchOptions:
    section = tinyfish_config(config).get("fetch") or {}
    if not isinstance(section, dict):
        return {}
    options: FetchOptions = {}
    for key in ("ttl", "per_url_timeout_ms"):
        value = _int_option(section.get(key))
        if value is not None:
            options[key] = value
    for key in ("links", "image_links"):
        value = _bool_option(section.get(key))
        if value is not None:
            options[key] = value
    return options


def default_fetch_format(config: dict[str, Any] | None = None) -> str:
    section = tinyfish_config(config).get("fetch") or {}
    if isinstance(section, dict) and section.get("format"):
        return str(section["format"])
    return "markdown"
