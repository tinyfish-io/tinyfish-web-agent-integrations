"""First-party TinyFish web provider plugin for Hermes Agent."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any

_DISTRIBUTION_NAME = "tinyfish-hermes"
_PLUGIN_MANIFEST = Path(__file__).resolve().parents[1] / "plugin.yaml"


def _version_from_plugin_manifest(path: Path | None = None) -> str | None:
    path = _PLUGIN_MANIFEST if path is None else path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for line in lines:
        if not line.startswith("version:"):
            continue
        value = line.partition(":")[2].split("#", 1)[0].strip().strip("'\"")
        return value or None
    return None


def _resolve_version() -> str:
    try:
        installed_version = metadata.version(_DISTRIBUTION_NAME)
    except Exception:  # directory installs must not depend on package metadata
        installed_version = ""
    return installed_version or _version_from_plugin_manifest() or "0+unknown"


__version__ = _resolve_version()


def register(ctx: Any) -> None:
    """Register the TinyFish web search provider with Hermes."""

    from .provider import TinyFishWebSearchProvider

    ctx.register_web_search_provider(TinyFishWebSearchProvider())


def __getattr__(name: str) -> Any:
    if name == "TinyFishWebSearchProvider":
        from .provider import TinyFishWebSearchProvider

        return TinyFishWebSearchProvider
    raise AttributeError(name)


__all__ = ["TinyFishWebSearchProvider", "__version__", "register"]
