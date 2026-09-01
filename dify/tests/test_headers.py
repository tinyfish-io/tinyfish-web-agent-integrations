from types import SimpleNamespace

from tools.base import TinyfishMixin
from tools.constants import PLUGIN_VERSION


def _tool() -> TinyfishMixin:
    tool = TinyfishMixin()
    tool.runtime = SimpleNamespace(credentials={"api_key": "tf_test"})  # type: ignore[attr-defined]
    return tool


def test_headers_identify_the_plugin() -> None:
    headers = _tool()._api_headers
    assert headers["X-API-Key"] == "tf_test"
    assert headers["X-TF-Client-Name"] == "tinyfish-dify"
    assert headers["X-TF-Client-Version"] == PLUGIN_VERSION
    assert "X-TF-Request-Origin" not in headers


def test_plugin_version_matches_manifest() -> None:
    with open("manifest.yaml", encoding="utf-8") as fh:
        manifest_version = next(
            line.split(":", 1)[1].strip() for line in fh if line.startswith("version:")
        )
    assert PLUGIN_VERSION == manifest_version
