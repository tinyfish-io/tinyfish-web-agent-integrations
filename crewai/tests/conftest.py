"""Shared pytest fixtures for the crewai-tinyfish tools.

Tests run without the real ``tinyfish`` SDK or network access: we stub out the
SDK install check and inject a fake client into each tool module.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

TOOL_MODULES = [
    "crewai_tinyfish.tinyfish_search_tool",
    "crewai_tinyfish.tinyfish_fetch_tool",
    "crewai_tinyfish.tinyfish_agent_tool",
    "crewai_tinyfish.tinyfish_browser_tool",
]


@pytest.fixture
def api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")


@pytest.fixture
def no_sdk_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every tool module's SDK-install check a no-op."""
    import importlib

    for mod_name in TOOL_MODULES:
        mod = importlib.import_module(mod_name)
        monkeypatch.setattr(mod, "ensure_sdk_installed", lambda *a, **k: None)


def inject_client(monkeypatch: pytest.MonkeyPatch, module_name: str, client: Any) -> None:
    """Replace ``build_client`` in a tool module so it returns ``client``."""
    import importlib

    mod = importlib.import_module(module_name)
    monkeypatch.setattr(mod, "build_client", lambda *a, **k: client)


def ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)
