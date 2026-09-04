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


def _version_from_metadata() -> str | None:
    try:
        return metadata.version(_DISTRIBUTION_NAME)
    except Exception:  # directory installs must not depend on package metadata
        return None


def _resolve_version() -> str:
    # Wheels omit plugin.yaml: an adjacent manifest beats stale dist metadata.
    # httpx sends headers as ASCII, so one stray byte fails every request; a
    # garbled source degrades to the next candidate, not straight to the fallback.
    for candidate in (_version_from_plugin_manifest(), _version_from_metadata()):
        if candidate and candidate.isascii():
            return candidate
    return "0+unknown"


__version__ = _resolve_version()


def register(ctx: Any) -> None:
    """Register TinyFish providers, lifecycle hooks, and CLI commands with Hermes."""

    from .browser_provider import TinyFishBrowserProvider
    from .credit_policy import pre_tool_call_policy
    from .provider import TinyFishWebSearchProvider
    from .routing_context import routing_context_hook
    from .setup_cli import (
        dispatch_tinyfish_cli,
        setup_tinyfish_cli,
        tinyfish_status_command,
    )

    provider = TinyFishWebSearchProvider()
    ctx.register_web_search_provider(provider)
    if hasattr(ctx, "register_hook"):
        # Only offer the browser provider where the pre_tool_call credit gate lands.
        if hasattr(ctx, "register_browser_provider"):
            ctx.register_browser_provider(TinyFishBrowserProvider())
        ctx.register_hook("pre_tool_call", pre_tool_call_policy)
        ctx.register_hook("pre_llm_call", routing_context_hook)

    if hasattr(ctx, "register_cli_command"):

        def _dispatch_cli(args: Any) -> int:
            # Hermes' CLI main() propagates a nonzero int return to sys.exit.
            return dispatch_tinyfish_cli(args, provider=provider)

        ctx.register_cli_command(
            name="tinyfish",
            help="Configure and diagnose the TinyFish web provider",
            setup_fn=setup_tinyfish_cli,
            handler_fn=_dispatch_cli,
            description=(
                "Route Hermes web tools to TinyFish and manage the API key, "
                "credit policies, and browser sessions."
            ),
        )
    if hasattr(ctx, "register_command"):
        ctx.register_command(
            name="tinyfish-status",
            handler=lambda raw_args: tinyfish_status_command(
                raw_args, provider=provider
            ),
            description=(
                "Show TinyFish provider status; pass 'live' to test Search and Fetch."
            ),
            args_hint="[live]",
        )


def __getattr__(name: str) -> Any:
    if name == "TinyFishWebSearchProvider":
        from .provider import TinyFishWebSearchProvider

        return TinyFishWebSearchProvider
    if name == "TinyFishBrowserProvider":
        from .browser_provider import TinyFishBrowserProvider

        return TinyFishBrowserProvider
    raise AttributeError(name)


__all__ = [
    "TinyFishBrowserProvider",
    "TinyFishWebSearchProvider",
    "__version__",
    "register",
]
