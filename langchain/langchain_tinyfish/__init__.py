"""LangChain integration for TinyFish Web Agent."""

from importlib import metadata

from langchain_tinyfish._api_wrapper import TinyFishAPIWrapper
from langchain_tinyfish.tool import (
    TinyFishBrowserSession,
    TinyFishBrowserSessionInput,
    TinyFishFetch,
    TinyFishFetchInput,
    TinyFishInput,
    TinyFishSearch,
    TinyFishSearchInput,
    TinyFishWebAutomation,
)

try:
    __version__: str = metadata.version(__package__ or __name__)
except metadata.PackageNotFoundError:
    __version__ = ""

__all__ = [
    "TinyFishAPIWrapper",
    "TinyFishBrowserSession",
    "TinyFishBrowserSessionInput",
    "TinyFishFetch",
    "TinyFishFetchInput",
    "TinyFishInput",
    "TinyFishSearch",
    "TinyFishSearchInput",
    "TinyFishWebAutomation",
    "__version__",
]
