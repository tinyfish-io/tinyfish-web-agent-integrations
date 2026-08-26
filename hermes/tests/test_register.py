from __future__ import annotations

from typing import Any

import tinyfish_hermes


class MinimalContext:
    def __init__(self) -> None:
        self.providers: list[Any] = []

    def register_web_search_provider(self, provider: Any) -> None:
        self.providers.append(provider)


def test_register_with_minimal_context_adds_only_web_provider() -> None:
    ctx = MinimalContext()

    tinyfish_hermes.register(ctx)

    assert len(ctx.providers) == 1
    assert ctx.providers[0].name == "tinyfish"
    assert isinstance(ctx.providers[0], tinyfish_hermes.TinyFishWebSearchProvider)
