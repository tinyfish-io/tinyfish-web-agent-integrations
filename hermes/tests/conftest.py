from __future__ import annotations

import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WebSearchProvider:
    pass


def get_provider_env(name: str) -> str:
    return os.getenv(name, "")


agent_pkg = types.ModuleType("agent")
web_provider_mod = types.ModuleType("agent.web_search_provider")
web_provider_mod.WebSearchProvider = WebSearchProvider  # type: ignore[attr-defined]
web_provider_mod.get_provider_env = get_provider_env  # type: ignore[attr-defined]
sys.modules.setdefault("agent", agent_pkg)
sys.modules["agent.web_search_provider"] = web_provider_mod

tools_pkg = types.ModuleType("tools")
interrupt_mod = types.ModuleType("tools.interrupt")
interrupt_mod.is_interrupted = lambda: False  # type: ignore[attr-defined]
sys.modules.setdefault("tools", tools_pkg)
sys.modules["tools.interrupt"] = interrupt_mod
