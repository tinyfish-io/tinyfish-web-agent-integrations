"""Packaging metadata tests."""

from __future__ import annotations

from pathlib import Path

import tomllib


def test_tinyfish_dependency_floor() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())

    dependencies = pyproject["project"]["dependencies"]

    tinyfish_dep = next(
        (dep for dep in dependencies if dep.startswith("tinyfish")),
        None,
    )
    assert tinyfish_dep is not None
    assert ">=0.2.5" in tinyfish_dep
