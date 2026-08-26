from __future__ import annotations

from typing import Any

import tinyfish_hermes


class MinimalContext:
    def __init__(self) -> None:
        self.providers: list[Any] = []

    def register_web_search_provider(self, provider: Any) -> None:
        self.providers.append(provider)


class FullContext(MinimalContext):
    def __init__(self) -> None:
        super().__init__()
        self.browser_providers: list[Any] = []
        self.hooks: list[tuple[str, Any]] = []

    def register_browser_provider(self, provider: Any) -> None:
        self.browser_providers.append(provider)

    def register_hook(self, name: str, handler: Any) -> None:
        self.hooks.append((name, handler))


def test_register_with_minimal_context_adds_only_web_provider() -> None:
    ctx = MinimalContext()

    tinyfish_hermes.register(ctx)

    assert len(ctx.providers) == 1
    assert ctx.providers[0].name == "tinyfish"
    assert isinstance(ctx.providers[0], tinyfish_hermes.TinyFishWebSearchProvider)


def test_register_with_full_context_adds_browser_provider_and_hooks() -> None:
    ctx = FullContext()

    tinyfish_hermes.register(ctx)

    assert ctx.providers[0].name == "tinyfish"
    assert len(ctx.browser_providers) == 1
    assert ctx.browser_providers[0].name == "tinyfish"
    assert isinstance(ctx.browser_providers[0], tinyfish_hermes.TinyFishBrowserProvider)
    assert [name for name, _ in ctx.hooks] == ["pre_tool_call", "pre_llm_call"]
    assert all(callable(handler) for _, handler in ctx.hooks)
