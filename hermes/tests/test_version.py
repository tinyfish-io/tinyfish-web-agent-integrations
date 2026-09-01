from __future__ import annotations

from importlib import metadata
from pathlib import Path

import pytest
import tomllib

import tinyfish_hermes as plugin


def test_version_prefers_installed_distribution_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = tmp_path / "plugin.yaml"
    manifest.write_text("version: 1.2.3\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "_PLUGIN_MANIFEST", manifest)
    monkeypatch.setattr(plugin.metadata, "version", lambda name: "9.8.7")

    assert plugin._resolve_version() == "9.8.7"


def test_version_falls_back_to_directory_plugin_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = tmp_path / "plugin.yaml"
    manifest.write_text(
        'name: tinyfish\nversion: "1.2.3" # release\n', encoding="utf-8"
    )
    monkeypatch.setattr(plugin, "_PLUGIN_MANIFEST", manifest)

    def missing_distribution(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(plugin.metadata, "version", missing_distribution)

    assert plugin._resolve_version() == "1.2.3"


def test_version_falls_back_to_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(plugin, "_PLUGIN_MANIFEST", tmp_path / "missing.yaml")
    monkeypatch.setattr(
        plugin.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(metadata.PackageNotFoundError(name)),
    )

    assert plugin._resolve_version() == "0+unknown"


def test_public_version_is_exported() -> None:
    assert isinstance(plugin.__version__, str)
    assert plugin.__version__
    assert "__version__" in plugin.__all__


def test_plugin_manifest_version_matches_the_distribution_version() -> None:
    """Both feed `plugin_version`; drift makes one install report two versions."""
    hermes_root = Path(plugin.__file__).resolve().parents[1]
    pyproject = tomllib.loads(
        (hermes_root / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert plugin._version_from_plugin_manifest() == pyproject["project"]["version"]
