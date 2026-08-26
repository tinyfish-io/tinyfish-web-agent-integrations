from __future__ import annotations

from typing import Any

import pytest

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
        self.cli_commands: list[dict[str, Any]] = []
        self.commands: list[dict[str, Any]] = []

    def register_browser_provider(self, provider: Any) -> None:
        self.browser_providers.append(provider)

    def register_hook(self, name: str, handler: Any) -> None:
        self.hooks.append((name, handler))

    def register_cli_command(self, **kwargs: Any) -> None:
        self.cli_commands.append(kwargs)

    def register_command(self, **kwargs: Any) -> None:
        self.commands.append(kwargs)


def test_register_with_minimal_context_adds_only_web_provider() -> None:
    ctx = MinimalContext()

    tinyfish_hermes.register(ctx)

    assert len(ctx.providers) == 1
    assert ctx.providers[0].name == "tinyfish"
    assert isinstance(ctx.providers[0], tinyfish_hermes.TinyFishWebSearchProvider)


def test_register_skips_browser_provider_when_host_has_no_hooks() -> None:
    # Without pre_tool_call there is no credit gate, so the provider must not land.
    class HooklessContext(MinimalContext):
        def __init__(self) -> None:
            super().__init__()
            self.browser_providers: list[Any] = []

        def register_browser_provider(self, provider: Any) -> None:
            self.browser_providers.append(provider)

    ctx = HooklessContext()

    tinyfish_hermes.register(ctx)

    assert ctx.browser_providers == []
    assert len(ctx.providers) == 1


def test_register_with_full_context_adds_browser_provider_and_hooks() -> None:
    ctx = FullContext()

    tinyfish_hermes.register(ctx)

    assert ctx.providers[0].name == "tinyfish"
    assert len(ctx.browser_providers) == 1
    assert ctx.browser_providers[0].name == "tinyfish"
    assert isinstance(ctx.browser_providers[0], tinyfish_hermes.TinyFishBrowserProvider)
    assert [name for name, _ in ctx.hooks] == ["pre_tool_call", "pre_llm_call"]
    assert all(callable(handler) for _, handler in ctx.hooks)


def test_register_wires_cli_and_in_session_commands() -> None:
    ctx = FullContext()

    tinyfish_hermes.register(ctx)

    assert ctx.cli_commands[0]["name"] == "tinyfish"
    assert callable(ctx.cli_commands[0]["setup_fn"])
    assert callable(ctx.cli_commands[0]["handler_fn"])
    assert ctx.commands[0]["name"] == "tinyfish-status"
    assert ctx.commands[0]["args_hint"] == "[live]"
    assert ctx.commands[0]["handler"]("unexpected") == "Usage: /tinyfish-status [live]"


def test_registered_cli_handler_propagates_nonzero_exit_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tinyfish_hermes import setup_cli

    monkeypatch.setattr(
        setup_cli, "dispatch_tinyfish_cli", lambda args, provider=None: 7
    )
    ctx = FullContext()
    tinyfish_hermes.register(ctx)

    with pytest.raises(SystemExit) as exc_info:
        ctx.cli_commands[0]["handler_fn"](object())

    assert exc_info.value.code == 7
