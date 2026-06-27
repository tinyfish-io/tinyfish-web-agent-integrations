"""Small helpers to read fields off TinyFish SDK responses or plain dicts.

The TinyFish SDK returns typed objects, but tests (and older/newer SDK builds)
may hand back dicts. These accessors tolerate both so the tools stay robust.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict


def attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def supported_kwargs(func: Callable[..., Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Drop kwargs the target callable doesn't accept (guards against SDK version skew).

    If the callable accepts ``**kwargs`` we pass everything through; otherwise we keep
    only the names present in its signature. If the signature can't be read, pass through.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return dict(params)

    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return dict(params)

    allowed = set(sig.parameters)
    return {k: v for k, v in params.items() if k in allowed}


def as_list(value: Any) -> list:
    """Coerce ``value`` into a list (None -> [])."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return [value]
