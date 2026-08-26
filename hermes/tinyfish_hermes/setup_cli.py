"""CLI helpers for ``hermes tinyfish``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import rest_client
from .config import (
    CREDIT_FEATURES,
    CREDIT_POLICIES,
    DEFAULT_CREDIT_POLICY,
    browser_cloud_provider,
    credit_policy_summary,
    normalize_feature,
    normalize_policy,
    routing_context_enabled,
    set_credit_policy,
)
from .credit_policy import request_credit_approval
from .provider import (
    API_KEY_ENV_VARS,
    API_KEY_URL,
    MISSING_KEY_ERROR,
    TinyFishWebSearchProvider,
    _api_key,
)
from .routing_context import tinyfish_mcp_configured


def setup_tinyfish_cli(parser: argparse.ArgumentParser) -> None:
    parser.description = "Configure and diagnose the TinyFish provider plugin."
    sub = parser.add_subparsers(dest="tinyfish_command")

    setup = sub.add_parser("setup", help="Route Hermes web search/extract to TinyFish")
    setup.add_argument(
        "--yes", "-y", action="store_true", help="Accept config changes without prompts"
    )
    setup.add_argument("--api-key", help="Save TINYFISH_API_KEY in Hermes .env")
    setup.add_argument(
        "--no-web-backend",
        action="store_true",
        help="Do not set web.search_backend/extract_backend",
    )
    setup.add_argument(
        "--live", action="store_true", help="Run live doctor checks after setup"
    )

    status = sub.add_parser("status", help="Print non-secret TinyFish status")
    status.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )

    doctor = sub.add_parser("doctor", help="Check TinyFish plugin configuration")
    doctor.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )
    doctor.add_argument(
        "--live", action="store_true", help="Run a live search/fetch check"
    )
    doctor.add_argument(
        "--live-paid",
        action="store_true",
        help="Create and close a TinyFish Browser session per its credit policy",
    )

    credits = sub.add_parser(
        "credits", help="Inspect or update TinyFish credit policies"
    )
    credits_sub = credits.add_subparsers(dest="credits_command")
    credits_status = credits_sub.add_parser(
        "status", help="Show TinyFish credit policies"
    )
    credits_status.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )
    credits_set = credits_sub.add_parser(
        "set", help="Set a feature policy: deny, request, or allow"
    )
    credits_set.add_argument("feature", choices=list(CREDIT_FEATURES))
    credits_set.add_argument("policy", choices=list(CREDIT_POLICIES))
    credits_sub.add_parser(
        "reset", help=f"Restore the default policy ({DEFAULT_CREDIT_POLICY})"
    )

    browser = sub.add_parser("browser", help="Route Hermes browser tools to TinyFish")
    browser_sub = browser.add_subparsers(dest="browser_command")
    browser_sub.add_parser("enable", help="Set browser.cloud_provider to tinyfish")
    browser_sub.add_parser("disable", help="Unset browser.cloud_provider if tinyfish")
    browser_sub.add_parser("status", help="Show browser provider and credit policy")

    usage = sub.add_parser(
        "usage", help="Read TinyFish wallet balance and billing rates"
    )
    usage.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )


def dispatch_tinyfish_cli(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    command = getattr(args, "tinyfish_command", None) or "status"
    if command == "setup":
        return cmd_setup(args, provider=provider)
    if command == "status":
        return cmd_status(args, provider=provider)
    if command == "doctor":
        return cmd_doctor(args, provider=provider)
    if command == "credits":
        return cmd_credits(args)
    if command == "browser":
        return cmd_browser(args)
    if command == "usage":
        return cmd_usage(args)
    print(
        "Usage: hermes tinyfish {setup,status,doctor,credits,browser,usage}",
        file=sys.stderr,
    )
    return 2


def _load_config() -> dict[str, Any]:
    from hermes_cli.config import load_config

    return dict(load_config() or {})


def _save_config(config: dict[str, Any]) -> None:
    from hermes_cli.config import save_config

    save_config(config)


def _get_env(name: str) -> str:
    try:
        from hermes_cli.config import get_env_value

        return str(get_env_value(name) or "").strip()
    except Exception:
        return str(os.getenv(name, "") or "").strip()


def _save_env(name: str, value: str) -> None:
    from hermes_cli.config import save_env_value

    save_env_value(name, value)


def _api_key_env_var() -> str:
    for name in API_KEY_ENV_VARS:
        if _get_env(name):
            return name
    return ""


def _confirm(question: str, *, default: bool = True, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return default
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input(f"{question} [{suffix}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def _prompt_secret(question: str) -> str:
    import getpass

    try:
        return getpass.getpass(question).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _apply_web_backend_config(config: dict[str, Any]) -> None:
    web = config.setdefault("web", {})
    web["search_backend"] = "tinyfish"
    web["extract_backend"] = "tinyfish"
    if not web.get("backend"):
        web["backend"] = "tinyfish"


def cmd_setup(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    config = _load_config()

    if not getattr(args, "no_web_backend", False) and _confirm(
        "Set Hermes web.search_backend and web.extract_backend to tinyfish?",
        default=True,
        assume_yes=bool(getattr(args, "yes", False)),
    ):
        _apply_web_backend_config(config)
        print("Configured Hermes web backends to use TinyFish")
    _save_config(config)

    api_key = (getattr(args, "api_key", None) or "").strip()
    if (
        not api_key
        and not _api_key_env_var()
        and sys.stdin.isatty()
        and _confirm("Add TINYFISH_API_KEY now?", default=True, assume_yes=False)
    ):
        api_key = _prompt_secret(f"TinyFish API key (create at {API_KEY_URL}): ")
    if api_key:
        _save_env("TINYFISH_API_KEY", api_key)
        print("Saved TINYFISH_API_KEY in Hermes .env")

    if getattr(args, "live", False):
        doctor_args = argparse.Namespace(json=False, live=True, live_paid=False)
        return cmd_doctor(doctor_args, provider=provider)

    print("Run `hermes tinyfish doctor --live` to verify the setup.")
    return 0


def collect_status(
    *,
    live: bool = False,
    provider: TinyFishWebSearchProvider | None = None,
) -> dict[str, Any]:
    from . import __version__

    config = _load_config()
    web_cfg = config.get("web") if isinstance(config.get("web"), dict) else {}
    provider = provider or TinyFishWebSearchProvider()
    api_key_env = _api_key_env_var()

    checks: dict[str, Any] = {
        "plugin_version": __version__,
        "provider_available": provider.is_available(),
        "api_key_env_var": api_key_env or None,
        "api_key_configured": bool(api_key_env),
        "web_search_backend": (web_cfg or {}).get("search_backend")
        or (web_cfg or {}).get("backend")
        or "",
        "web_extract_backend": (web_cfg or {}).get("extract_backend")
        or (web_cfg or {}).get("backend")
        or "",
        "browser_cloud_provider": browser_cloud_provider(config),
        "credit_policy": credit_policy_summary(config),
        "routing_context_enabled": routing_context_enabled(config),
        "routing_context_active": bool(
            routing_context_enabled(config) and tinyfish_mcp_configured(config)
        ),
        "mcp_configured": tinyfish_mcp_configured(config),
    }
    checks["web_backend_configured"] = (
        checks["web_search_backend"] == "tinyfish"
        and checks["web_extract_backend"] == "tinyfish"
    )
    configured_ok = bool(
        checks["web_backend_configured"] and checks["api_key_configured"]
    )
    checks["ok"] = configured_ok

    if live:
        try:
            search = provider.search("TinyFish web agent", limit=1)
            checks["live_search_ok"] = bool(
                search.get("success") and search.get("data", {}).get("web")
            )
            if not checks["live_search_ok"]:
                checks["live_search_error"] = str(
                    search.get("error") or "TinyFish Search returned no web results."
                )
        except Exception as exc:  # noqa: BLE001 - diagnostics must not crash
            checks["live_search_ok"] = False
            checks["live_search_error"] = (
                f"TinyFish Search check failed ({type(exc).__name__})."
            )

        try:
            fetch = provider.extract(["https://docs.tinyfish.ai/"], format="markdown")
            content = ""
            if fetch:
                content = str(
                    fetch[0].get("content") or fetch[0].get("raw_content") or ""
                ).strip()
            checks["live_fetch_ok"] = bool(
                fetch and not fetch[0].get("error") and content
            )
            if not checks["live_fetch_ok"]:
                error = fetch[0].get("error") if fetch else None
                checks["live_fetch_error"] = str(
                    error or "TinyFish Fetch returned no extracted content."
                )
        except Exception as exc:  # noqa: BLE001 - diagnostics must not crash
            checks["live_fetch_ok"] = False
            checks["live_fetch_error"] = (
                f"TinyFish Fetch check failed ({type(exc).__name__})."
            )

        checks["ok"] = bool(
            configured_ok and checks["live_search_ok"] and checks["live_fetch_ok"]
        )
    return checks


def _status_lines(status: dict[str, Any]) -> list[str]:
    lines = ["TinyFish Hermes plugin status"]
    for key in sorted(status):
        value = status[key]
        if key == "credit_policy" and isinstance(value, dict):
            lines.append("  credit_policy:")
            for feature in CREDIT_FEATURES:
                lines.append(
                    f"    {feature}: {value.get(feature, DEFAULT_CREDIT_POLICY)}"
                )
            continue
        if isinstance(value, bool):
            value = "yes" if value else "no"
        if value is None:
            value = "none"
        lines.append(f"  {key}: {value}")
    return lines


def _print_status(status: dict[str, Any]) -> None:
    print("\n".join(_status_lines(status)))


def cmd_status(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    status = collect_status(live=False, provider=provider)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
    return 0


def _recommended_next_step(status: dict[str, Any]) -> str:
    configured = bool(
        status.get("web_backend_configured") and status.get("api_key_configured")
    )
    if not configured:
        return "run `hermes tinyfish setup`."
    if not status.get("live_search_ok", True) or not status.get("live_fetch_ok", True):
        return (
            "verify your TinyFish API key and service availability, then retry "
            "`hermes tinyfish doctor --live`."
        )
    return (
        "review the browser credit policy and API key, then retry "
        "`hermes tinyfish doctor --live-paid`."
    )


def cmd_doctor(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    status = collect_status(live=bool(getattr(args, "live", False)), provider=provider)
    if getattr(args, "live_paid", False):
        paid_ok = _run_live_paid_checks(status)
        status["ok"] = bool(status["ok"] and paid_ok)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
        if not status["ok"]:
            print()
            print(f"Recommended next step: {_recommended_next_step(status)}")
    return 0 if status["ok"] else 1


def _run_live_paid_checks(status: dict[str, Any]) -> bool:
    policy_status = status.get("credit_policy") or {}
    browser_policy = (
        policy_status.get("browser", "deny")
        if isinstance(policy_status, dict)
        else "deny"
    )
    if browser_policy == "deny":
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = "TinyFish browser policy is deny."
        return False

    approved, message = request_credit_approval(
        "browser", "doctor-live-paid", "TinyFish Browser session"
    )
    if not approved:
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = message
        return False

    api_key = _api_key()
    if not api_key:
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = (
            "A TinyFish API key is required for paid live checks."
        )
        return False

    session_id = ""
    try:
        session = rest_client.create_browser_session(api_key=api_key)
        session_id = str(session.get("session_id") or session.get("id") or "").strip()
        if not session_id:
            status["live_paid_error"] = (
                "TinyFish Browser did not return a valid session ID."
            )
    except Exception as exc:  # noqa: BLE001 - diagnostics must not crash
        status["live_paid_error"] = (
            f"TinyFish Browser session creation failed ({type(exc).__name__})."
        )

    cleanup_ok = False
    if session_id:
        try:
            cleanup_ok = bool(
                rest_client.close_browser_session(session_id, api_key=api_key)
            )
        except Exception:  # noqa: BLE001 - cleanup result is reported below
            cleanup_ok = False
        if not cleanup_ok:
            status["live_paid_error"] = "TinyFish Browser session cleanup failed."

    status["live_paid_browser_cleanup_ok"] = cleanup_ok
    status["live_paid_browser_ok"] = bool(session_id and cleanup_ok)
    status["live_paid_ok"] = status["live_paid_browser_ok"]
    return bool(status["live_paid_ok"])


def cmd_credits(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "credits_command", None) or "status"
    config = _load_config()
    if subcommand == "status":
        payload = {"credit_policy": credit_policy_summary(config)}
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("TinyFish credit policies")
            for feature in CREDIT_FEATURES:
                print(f"  {feature}: {payload['credit_policy'][feature]}")
        return 0
    if subcommand == "set":
        feature = normalize_feature(args.feature)
        policy = normalize_policy(args.policy)
        set_credit_policy(config, feature, policy)
        _save_config(config)
        print(f"Set TinyFish {feature} credit policy to {policy}.")
        return 0
    if subcommand == "reset":
        set_credit_policy(config, "browser", DEFAULT_CREDIT_POLICY)
        _save_config(config)
        print(
            f"Reset TinyFish browser credit policy to {DEFAULT_CREDIT_POLICY} "
            "(the default)."
        )
        return 0
    print("Usage: hermes tinyfish credits {status,set,reset}", file=sys.stderr)
    return 2


def _policy_effect_line(policy: str) -> str:
    if policy == "allow":
        return "Policy 'allow': sessions start without per-session approval."
    if policy == "deny":
        return "Policy 'deny': TinyFish browser sessions are blocked."
    return "Policy 'request': each TinyFish browser session asks for approval."


def cmd_browser(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "browser_command", None) or "status"
    config = _load_config()
    current = browser_cloud_provider(config)
    policy = credit_policy_summary(config)["browser"]
    if subcommand == "enable":
        if current == "tinyfish":
            print("TinyFish is already Hermes' browser cloud provider.")
        else:
            section = config.setdefault("browser", {})
            if not isinstance(section, dict):
                section = {}
                config["browser"] = section
            section["cloud_provider"] = "tinyfish"
            _save_config(config)
            print("Set browser.cloud_provider to tinyfish.")
        print(_policy_effect_line(policy))
        return 0
    if subcommand == "disable":
        if current != "tinyfish":
            print("TinyFish is not Hermes' browser cloud provider; nothing to change.")
            return 0
        section = config.get("browser")
        if isinstance(section, dict):
            section.pop("cloud_provider", None)
            _save_config(config)
        print("Removed browser.cloud_provider (was tinyfish).")
        return 0
    if subcommand == "status":
        print(f"browser.cloud_provider: {current or 'unset'}")
        print(f"tinyfish.credit_policy.browser: {policy}")
        print(_policy_effect_line(policy))
        return 0
    print("Usage: hermes tinyfish browser {enable,disable,status}", file=sys.stderr)
    return 2


def _api_key_or_error() -> str | None:
    api_key = _api_key()
    if not api_key:
        print(MISSING_KEY_ERROR, file=sys.stderr)
        return None
    return api_key


def _wallet_amount(value: Any, currency: Any) -> str:
    amount = str(value) if value is not None else "unavailable"
    code = str(currency or "").strip()
    if amount == "unavailable":
        return amount
    if code == "USD":
        return f"${amount} USD"
    return f"{amount} {code}".rstrip()


def _wallet_text_lines(wallet: dict[str, Any]) -> list[str]:
    currency = wallet.get("currency")
    balance = _wallet_amount(wallet.get("available_balance"), currency)
    lines = [
        "TinyFish usage",
        f"  Available balance: {balance}",
        f"  As of: {wallet.get('as_of') or 'unavailable'}",
    ]

    auto_reload = wallet.get("auto_reload")
    if auto_reload is None:
        lines.append("  Auto-reload: unavailable")
    elif isinstance(auto_reload, dict):
        state = str(auto_reload.get("state") or "unknown").replace("_", " ")
        if state == "unconfigured":
            lines.append("  Auto-reload: not configured")
        else:
            threshold = _wallet_amount(auto_reload.get("threshold"), currency)
            recharge_to = _wallet_amount(auto_reload.get("recharge_to"), currency)
            lines.append(
                f"  Auto-reload: {state} (at {threshold}, recharge to {recharge_to})"
            )
    else:
        lines.append("  Auto-reload: invalid response")

    pending = wallet.get("pending_top_up")
    if pending is None:
        lines.append("  Pending top-up: none")
    elif isinstance(pending, dict):
        amount = _wallet_amount(pending.get("amount"), currency)
        lines.append(
            f"  Pending top-up: {amount} since {pending.get('started_at') or 'unknown'}"
        )
    else:
        lines.append("  Pending top-up: invalid response")

    rates = wallet.get("rates")
    meters = rates.get("meters") if isinstance(rates, dict) else None
    if isinstance(meters, list) and meters:
        lines.append("  Rates:")
        for meter in meters:
            if not isinstance(meter, dict):
                continue
            label = meter.get("label") or meter.get("product_id") or "Unnamed meter"
            amount = _wallet_amount(meter.get("unit_amount"), meter.get("currency"))
            per = f" per {meter['per']}" if meter.get("per") else ""
            lines.append(f"    {label}: {amount}{per}")
    elif rates is None:
        lines.append("  Rates: unavailable")
    else:
        lines.append("  Rates: none")

    return lines


def cmd_usage(args: argparse.Namespace) -> int:
    api_key = _api_key_or_error()
    if not api_key:
        return 1
    payload: dict[str, Any]
    try:
        wallet = rest_client.wallet(api_key=api_key)
    except rest_client.TinyFishWalletNotFound:
        payload = {
            "success": True,
            "wallet_available": False,
            "reason": "legacy_billing_or_no_metronome_customer",
            "message": (
                "This account uses legacy billing or does not have a Metronome "
                "wallet yet."
            ),
            "billing_url": API_KEY_URL,
        }
        text_lines = [
            "TinyFish usage",
            "  Wallet balance unavailable.",
            f"  {payload['message']}",
            f"  Billing: {API_KEY_URL}",
        ]
    except Exception as exc:  # noqa: BLE001 - CLI reports the failure and exits 1
        payload = {"success": False, "wallet_available": None, "error": str(exc)}
        text_lines = ["TinyFish usage", f"  Error: {exc}"]
    else:
        if not isinstance(wallet, dict):
            payload = {
                "success": False,
                "wallet_available": None,
                "error": "TinyFish Wallet returned an invalid response",
            }
            text_lines = ["TinyFish usage", f"  Error: {payload['error']}"]
        else:
            payload = {"success": True, "wallet_available": True, "wallet": wallet}
            text_lines = _wallet_text_lines(wallet)
    if bool(getattr(args, "json", False)):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("\n".join(text_lines))
    return 0 if payload["success"] else 1


def tinyfish_status_command(
    raw_args: str,
    *,
    provider: TinyFishWebSearchProvider,
) -> str:
    """Serve the in-session ``/tinyfish-status`` command."""

    option = (raw_args or "").strip().lower()
    if option not in {"", "live"}:
        return "Usage: /tinyfish-status [live]"
    status = collect_status(live=option == "live", provider=provider)
    return "\n".join(_status_lines(status))
