"""Read the ``tinyfish`` section of Hermes' user configuration."""

from __future__ import annotations

from typing import Any

SearchOptions = dict[str, Any]
FetchOptions = dict[str, Any]


def load_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config as _load_config

        return dict(_load_config() or {})
    except Exception:  # config layer is optional outside Hermes
        return {}


def tinyfish_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config() if config is None else config
    section = cfg.get("tinyfish") or {}
    return section if isinstance(section, dict) else {}


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
