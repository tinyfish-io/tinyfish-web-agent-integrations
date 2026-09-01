import re
from pathlib import Path
from types import SimpleNamespace

from tools.base import TinyfishMixin
from tools.constants import PLUGIN_VERSION

MANIFEST = Path(__file__).resolve().parents[1] / "manifest.yaml"


def _tool() -> TinyfishMixin:
    tool = TinyfishMixin()
    tool.runtime = SimpleNamespace(credentials={"api_key": "tf_test"})  # type: ignore[attr-defined]
    return tool


def test_headers_identify_the_plugin() -> None:
    headers = _tool()._api_headers
    assert headers["X-API-Key"] == "tf_test"
    assert headers["X-TF-Client-Name"] == "tinyfish-dify"
    assert headers["X-TF-Client-Version"] == PLUGIN_VERSION


def test_plugin_version_is_a_real_release_version() -> None:
    # The publish workflow greps `^version:` — same anchor the constant uses.
    assert re.fullmatch(r"\d+\.\d+\.\d+", PLUGIN_VERSION), PLUGIN_VERSION
    # Column 0 only: meta.version is indented and is the manifest-format version.
    assert re.search(
        rf"^version: {re.escape(PLUGIN_VERSION)}$",
        MANIFEST.read_text(encoding="utf-8"),
        re.M,
    )
