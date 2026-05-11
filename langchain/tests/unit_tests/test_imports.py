"""Test that all expected symbols are exported from the package."""

from langchain_tinyfish import __all__

EXPECTED_ALL = [
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


def test_all_imports() -> None:
    assert sorted(EXPECTED_ALL) == sorted(__all__)
